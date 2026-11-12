#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自動フィットを table 以外のタイプへ載せた分（core-4）のテスト。

  - bullets / closing / image_text / two_column: 文字量に応じて縮める・明示値は動かさない・下限で警告・fit:content
  - cards: 本文の高さを内容から決める・配置関数・縮小・あふれ警告・fit:content
  - steps: 見出しの折れ・項目の縮小・警告
  - status_table: 文字サイズの縮小・警告
  - matrix: 象限の文・点ラベルの警告
  - 提案書系（summary / reasons / row_matrix / house / kpi_tree / statement）: 最小サイズでも収まらないときの警告
  - 結論帯・出典: 長い文の縮小と高さの確保
  - schedule: はみ出しの検出
  - density プリセット（read / talk）
  - _check_overflow が自動フィットの結果を警告にする（古い見積もりの枝が無い）

実行: python3 -m unittest plugins/slide-deck/tools/test_autofit_types.py
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import proposal_engine as pe  # noqa: E402
import schedule_engine as se  # noqa: E402

LAYOUT = json.loads((ROOT / "templates" / "layouts" / "default.json").read_text(encoding="utf-8"))
THEME = json.loads((ROOT / "templates" / "themes" / "default.json").read_text(encoding="utf-8"))

KANJI = "設計開発運用保守監視改善分析基盤統合連携移行評価計画実行管理品質"


def jp(n, seed=0):
    return "".join(KANJI[(i * 7 + seed) % len(KANJI)] for i in range(n))


def deck_of(slide, **meta):
    return {"meta": {"title": "t", **meta}, "slides": [slide]}


def resolve(slide, **meta):
    return b.resolve_style(LAYOUT, deck_of(slide, **meta), slide)


def issues(st, level=None):
    return [(lv, code, text) for lv, code, text in (st.get("_fit") or {}).get("issues", []) if level in (None, lv)]


def bullets_slide(n, length, **extra):
    return {"type": "bullets", "title": "t", "bullets": [jp(length, i) for i in range(n)], **extra}


@contextlib.contextmanager
def quiet():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        yield err


class BulletsFitTests(unittest.TestCase):
    def test_short_bullets_keep_layout_defaults(self):
        st = resolve(bullets_slide(4, 20))
        self.assertEqual(st["body"]["size"], 24)
        self.assertEqual(st["body"]["gap"], 15)
        self.assertEqual(issues(st), [])

    def test_dense_bullets_shrink_text_gap_and_child_together(self):
        st = resolve(bullets_slide(11, 40))
        body = st["body"]
        self.assertLess(body["size"], 24)
        self.assertLess(body["gap"], 15)
        self.assertLess(body["child_size"], 19)
        need = autofit.bullets_visible_height(bullets_slide(11, 40)["bullets"], {**body})
        self.assertLessEqual(need, body["h"] + 0.5)

    def test_explicit_size_is_kept_and_overflow_warns_with_style_hint(self):
        slide = bullets_slide(12, 50, style={"body": {"size": 24}})
        st = resolve(slide)
        self.assertEqual(st["body"]["size"], 24)
        warns = issues(st, "warn")
        self.assertEqual(len(warns), 1)
        self.assertIn("style の size=24", warns[0][2])
        self.assertIn("減らす", warns[0][2])

    def test_floor_overflow_warns_with_how_many_items_fit(self):
        st = resolve(bullets_slide(30, 60))
        warns = issues(st, "warn")
        self.assertTrue(warns)
        self.assertIn("個以下に減らす", warns[0][2])
        self.assertEqual(st["body"]["size"], 16)         # 下限（bullets.body.min_size）

    def test_two_step_shrink_gives_note(self):
        st = resolve(bullets_slide(9, 50))
        self.assertLessEqual(st["body"]["size"], 22)
        self.assertTrue(any(code == "body-shrunk" for _, code, _ in issues(st, "note")))

    def test_autofit_false_changes_nothing_but_still_warns(self):
        slide = bullets_slide(12, 50)
        st = resolve(slide, autofit=False)
        self.assertEqual(st["body"]["size"], 24)
        self.assertTrue(issues(st, "warn"))

    def test_closing_and_image_text_are_fitted(self):
        for t in ("closing", "image_text"):
            slide = {"type": t, "title": "t", "bullets": [jp(60, i) for i in range(14)]}
            if t == "image_text":
                slide["path"] = "x.png"
            st = resolve(slide)
            self.assertLess(st["body"]["size"], LAYOUT["types"][t]["body"]["size"], t)

    def test_estimate_bullets_height_is_the_autofit_estimate(self):
        items = ["a" * 30, {"text": jp(40), "children": [jp(30), "b"]}]
        r = LAYOUT["types"]["bullets"]["body"]
        self.assertAlmostEqual(b.estimate_bullets_height(items, r), autofit.bullets_height(items, r))

    def test_density_read_is_denser_and_talk_is_bigger(self):
        slide = bullets_slide(4, 20)
        std, read, talk = resolve(slide), resolve(slide, density="read"), resolve(slide, density="talk")
        self.assertLess(read["body"]["size"], std["body"]["size"])
        self.assertGreater(talk["body"]["size"], std["body"]["size"])
        self.assertEqual(talk["body"]["valign"], "middle")

    def test_talk_shrinks_when_content_is_large(self):
        st = resolve(bullets_slide(10, 40), density="talk")
        self.assertLess(st["body"]["size"], 30)
        self.assertGreaterEqual(st["body"]["size"], 20)

    def test_conclusion_band_lowers_the_available_height(self):
        a = resolve(bullets_slide(9, 30))
        c = resolve(bullets_slide(9, 30, conclusion="結論", source="出典"))
        self.assertLessEqual(c["body"]["size"], a["body"]["size"])


class TwoColumnFitTests(unittest.TestCase):
    def slide(self, n, length, **extra):
        side = {"heading": "見出し", "bullets": [jp(length, i) for i in range(n)]}
        return {"type": "two_column", "title": "t", "left": side, "right": dict(side), **extra}

    def test_short_keeps_defaults(self):
        st = resolve(self.slide(3, 15))
        self.assertEqual(st["col_body"]["size"], 19)
        self.assertEqual(st["left"]["h"], 452)
        self.assertEqual(issues(st), [])

    def test_dense_shrinks_both_body_and_heading(self):
        st = resolve(self.slide(9, 45))
        self.assertLess(st["col_body"]["size"], 19)
        self.assertEqual(st["left"]["h"], 452)

    def test_overflow_warns_at_floor(self):
        st = resolve(self.slide(20, 60))
        self.assertTrue(issues(st, "warn"))
        self.assertEqual(st["col_body"]["size"], 14)

    def test_fit_content_shrinks_boxes_and_moves_them_down(self):
        slide = self.slide(3, 15, style={"left": {"fit": "content"}, "right": {"fit": "content"}})
        st = resolve(slide)
        self.assertLess(st["left"]["h"], 452)
        self.assertEqual(st["left"]["h"], st["right"]["h"])
        self.assertGreater(st["left"]["y"], 192)
        self.assertGreaterEqual(st["left"]["h"], 200)          # min_h

    def test_read_density_shrinks_boxes_by_default(self):
        st = resolve(self.slide(3, 15), density="read")
        self.assertLess(st["left"]["h"], 452)

    def test_explicit_h_is_kept_when_fit_comes_from_density(self):
        slide = self.slide(3, 15, style={"left": {"h": 400}, "right": {"h": 400}})
        st = resolve(slide, density="read")
        self.assertEqual(st["left"]["h"], 400)
        # h を明示したら y も動かさない（箱が下にずれて、結論帯の手前で h が切り詰められるのを防ぐ）
        self.assertEqual(st["left"]["y"], resolve(slide)["left"]["y"])
        self.assertEqual(st["right"]["y"], resolve(slide)["right"]["y"])

    def test_explicit_h_with_conclusion_is_not_moved_or_trimmed_by_read(self):
        slide = self.slide(1, 15, conclusion="結論です", style={"left": {"h": 380}, "right": {"h": 380}})
        std, rd = resolve(slide), resolve(slide, density="read")
        for side in ("left", "right"):
            self.assertEqual((rd[side]["y"], rd[side]["h"]), (std[side]["y"], std[side]["h"]))

    def test_explicit_fit_with_explicit_h_still_shrinks(self):
        slide = self.slide(1, 15, style={"left": {"h": 400, "fit": "content"}, "right": {"h": 400, "fit": "content"}})
        st = resolve(slide)
        self.assertLess(st["left"]["h"], 400)


class CardsTests(unittest.TestCase):
    def cards(self, n, body="本文です", items=2, **extra):
        return {"type": "cards", "title": "t", "cards": [
            {"heading": f"見出し{i}", "body": body, "items": [jp(20, k) for k in range(items)]} for i in range(n)], **extra}

    def test_body_height_follows_content_not_a_fixed_44(self):
        g = LAYOUT["types"]["cards"]["grid"]
        one = autofit.cards_content({"heading": "a", "body": "短い"}, g, 300)
        three = autofit.cards_content({"heading": "a", "body": jp(80)}, g, 300)
        self.assertLess(one["body_h"], 44)
        self.assertGreater(three["body_h"], one["body_h"] * 2)

    def test_content_layout_uses_content_height(self):
        g = LAYOUT["types"]["cards"]["grid"]
        lay = b._cards_content_layout({"heading": "a", "body": "短い", "items": ["x"]}, g, 300, 300, 18, "top")
        self.assertLess(lay["body_h"], 30)
        self.assertAlmostEqual(lay["items_y"], lay["body_y"] + lay["body_h"] + autofit.CARD_BODY_GAP)

    def test_cells_are_shared_with_icons(self):
        g = {**LAYOUT["types"]["cards"]["grid"]}
        geo = pe.cards_cells(7, None, g)
        self.assertEqual((geo["cols"], geo["rows"]), (3, 3))
        self.assertEqual(len(geo["cells"]), 7)
        self.assertAlmostEqual(geo["cells"][4][0], g["x"] + (geo["cw"] + g["gap"]))
        self.assertEqual(pe.cards_cells(4, 2, g)["cols"], 2)
        self.assertEqual(pe.cards_cells(4, 0, g)["cols"], 1)

    def test_three_cards_keep_defaults(self):
        # 薄いときの文字拡大（thin_grow）を止めれば、既定の大きさのまま
        st = resolve(self.cards(3, style={"grid": {"thin_grow": 1}}))
        self.assertEqual(st["grid"]["body_size"], 15)
        self.assertEqual(issues(st), [])

    def test_thin_cards_grow_text_before_shrinking_boxes(self):
        # s3-A-02: 中身が薄い cards は、箱だけ小さくせず文字を大きくして領域を使う（thin_grow 倍まで）
        st = resolve(self.cards(3, items=0))      # S5a: 項目（20 字の漢字列）は文字を大きくすると折り返しが悪くなるので、拡大の対象は短い本文だけの箱
        g = st["grid"]
        self.assertGreater(g["body_size"], 15)
        self.assertLessEqual(g["body_size"], round(15 * LAYOUT["types"]["cards"]["grid"]["thin_grow"]))
        self.assertEqual(issues(st), [])
        # 利用者が文字サイズを書いたときは動かさない
        st2 = resolve(self.cards(3, style={"grid": {"body_size": 15, "heading_size": 19, "item_size": 14}}))
        self.assertEqual(st2["grid"]["body_size"], 15)

    def test_nine_cards_with_long_text_fit_by_shrinking(self):
        slide = self.cards(9, body=jp(40), items=2)
        st = resolve(slide)
        g = st["grid"]
        self.assertLess(g["body_size"], 15)
        geo = pe.cards_cells(9, None, g)
        need = max(autofit.cards_need(c, g, geo["cw"] - 2 * g["pad"], g["pad"]) for c in slide["cards"])
        self.assertLessEqual(need, geo["chh"] + 0.5)
        self.assertFalse(issues(st, "warn"))

    def test_overflow_is_detected_and_says_how_many_cards_fit(self):
        st = resolve(self.cards(18, body=jp(60), items=3))
        warns = issues(st, "warn")
        self.assertTrue(warns)
        self.assertIn("枚以下", warns[0][2])

    def test_explicit_sizes_are_kept_and_warned(self):
        st = resolve(self.cards(9, body=jp(40), items=3, style={"grid": {"body_size": 15, "heading_size": 19, "item_size": 14}}))
        self.assertEqual(st["grid"]["body_size"], 15)
        self.assertTrue(issues(st, "warn"))

    def test_fit_content_shrinks_the_grid(self):
        st = resolve(self.cards(3, body="短い", items=1, style={"grid": {"fit": "content"}}))
        self.assertLess(st["grid"]["h"], 440)
        self.assertGreater(st["grid"]["y"], 196)

    def test_fit_content_by_read_density(self):
        st = resolve(self.cards(3, body="短い", items=1), density="read")
        self.assertLess(st["grid"]["h"], 440)

    def test_large_heading_size_grows_the_heading_box(self):
        g = {**LAYOUT["types"]["cards"]["grid"], "heading_size": 40}
        c = autofit.cards_content({"heading": "見出し見出し見出し見出し見出し見出し"}, g, 300)
        self.assertGreater(c["head_h"], 60)       # 2 行ぶん（以前は 28px 固定）


URL = "https://example.com/" + "Internationalization" * 8      # 途中に折れ目が無い長い語（スラッシュの後ろでは折れる）


class LongWordTests(unittest.TestCase):
    """折り返せない長い文字列（URL・長い英単語）が枠の幅を超えるとき警告する（core-A-02）。"""

    def codes(self, slide, **meta):
        return [code for _, code, _ in issues(resolve(slide, **meta), "warn")]

    def test_bullets_url_warns_and_short_text_does_not(self):
        self.assertIn("long-word", self.codes({"type": "bullets", "title": "t", "bullets": ["参照: " + URL]}))
        self.assertNotIn("long-word", self.codes({"type": "bullets", "title": "t", "bullets": ["https://example.com/a で確認"]}))

    def test_japanese_text_never_triggers(self):
        self.assertNotIn("long-word", self.codes({"type": "bullets", "title": "t", "bullets": [jp(200)]}))

    def test_other_types_warn(self):
        side = {"heading": "h", "bullets": [URL]}
        self.assertIn("long-word", self.codes({"type": "two_column", "title": "t", "left": side, "right": {"heading": "r", "bullets": ["a"]}}))
        self.assertIn("long-word", self.codes({"type": "steps", "title": "t", "steps": [{"label": "a", "items": [URL]}] * 4}))
        quads = [{"heading": f"象限{i}", "body": URL if i == 3 else "文"} for i in range(4)]
        self.assertIn("long-word", self.codes({"type": "matrix", "title": "t", "quadrants": quads,
                                               "x_axis": {"label": "x", "low": "l", "high": "h"},
                                               "y_axis": {"label": "y", "low": "l", "high": "h"}}))
        self.assertIn("long-word", self.codes({"type": "table", "title": "t", "columns": ["A", "B"], "rows": [["x", URL]],
                                               "style": {"table": {"col_widths": [1, 1]}}}))

    def test_message_names_the_word_and_gives_a_fix(self):
        t = issues(resolve({"type": "bullets", "title": "t", "bullets": [URL]}), "warn")[0][2]
        self.assertIn("example.com", t)
        self.assertIn("改行", t)

    def test_html_wraps_long_words(self):
        self.assertIn("overflow-wrap: break-word", Path(b.__file__).read_text(encoding="utf-8"))


class AutofitOffMessageTests(unittest.TestCase):
    """autofit:false のとき、警告は style の指定のせいにせず、autofit を外す案内にする（core-C-04 / A-07）。"""

    def _texts(self, slide, **meta):
        st = resolve(slide, **meta)
        return [t for lv, code, t in issues(st, "warn")]

    def test_table_autofit_off(self):
        rows = [[f"T{i}", "タスク内容" * 3, "詳細"] for i in range(20)]
        slide = {"type": "table", "title": "a", "columns": ["A", "B", "C"], "rows": rows}
        t = self._texts(slide, autofit=False)
        self.assertTrue(t)
        self.assertIn("autofit: false を外すと", t[0])
        self.assertNotIn("指定を消すと", t[0])

    def test_bullets_and_cards_autofit_off(self):
        t = self._texts({"type": "bullets", "title": "b", "bullets": ["項目" * 10] * 20}, autofit=False)
        self.assertIn("autofit が切られているため縮めていません", t[0])
        self.assertNotIn("指定どおり", t[0])
        cards = {"type": "cards", "title": "c", "cards": [{"heading": "h", "body": "本文" * 80, "items": ["x" * 40] * 8}] * 6}
        t = self._texts(cards, autofit=False)
        self.assertIn("autofit が切られているため縮めていません", t[0])

    def test_explicit_size_still_blames_the_style(self):
        t = self._texts({"type": "bullets", "title": "b", "bullets": ["項目" * 10] * 20, "style": {"body": {"size": 24}}})
        self.assertIn("の指定どおり", t[0])
        self.assertIn("指定を消すと", t[0])


class FitEnumTests(unittest.TestCase):
    def test_bad_fit_value_is_rejected(self):
        import deck_schema
        out = deck_schema.check_region_value({"fit": "shrink"}, LAYOUT["types"]["cards"]["grid"], "style.grid")
        self.assertTrue(any(lv == "fail" and "content / fill" in text for lv, text in out))
        self.assertEqual(deck_schema.check_region_value({"fit": "content"}, LAYOUT["types"]["cards"]["grid"], "style.grid"), [])


class StepsTests(unittest.TestCase):
    def steps(self, n, label="ステップ見出し", items=3):
        return {"type": "steps", "title": "t", "steps": [{"label": f"{label}{i}", "items": [jp(15, k) for k in range(items)]}
                                                          for i in range(n)]}

    def test_four_steps_keep_defaults(self):
        st = resolve(self.steps(4, "準備", items=6))      # S5a: 項目が少ない（3〜5 個）と文字を大きくするので、中身が十分な 6 個で既定の維持を見る
        self.assertEqual(st["body"]["header_h"], 60)
        self.assertEqual(st["body"]["label_size"], 18)
        self.assertEqual(issues(st), [])

    def test_step_number_chip_width_covers_two_digit_numbers(self):
        # 「STEP 10」「STEP 11」の札が折れない幅を確保する（core-A-04）
        for n in (10, 11):
            st = resolve(self.steps(n, "手順"))
            b = st["body"]
            card_w = (b["w"] - (n - 1) * b["gap"]) / n
            need = autofit.text_em("STEP %d" % n, True) * 13
            self.assertGreaterEqual(card_w - 2 * b["pad"], need, n)
            self.assertFalse(b.get("_num_short"))

    def test_too_narrow_cards_drop_the_word_step(self):
        st = resolve(self.steps(14, "手順"))
        self.assertTrue(st["body"].get("_num_short"))
        self.assertTrue(any(code == "steps-narrow" for _, code, _ in issues(st, "warn")))

    def test_nine_steps_grow_the_header_instead_of_hiding_the_label(self):
        st = resolve(self.steps(9, "ステップ"))
        b_ = st["body"]
        n_lines = autofit.fitter and st["_fit"]["info"]["steps"]["label_lines"]
        self.assertGreaterEqual(b_["header_h"], 28 + n_lines * b_["label_size"] * 1.15 + 4 - 1)

    def test_label_that_cannot_fit_warns(self):
        st = resolve(self.steps(10, "とても長いステップの見出しですよ"))
        self.assertTrue(any(code == "steps-label" for _, code, _ in issues(st, "warn")))

    def test_many_items_shrink_text(self):
        st = resolve(self.steps(3, "工程", items=16))
        self.assertLess(st["body"]["item_size"], 15)

    def test_items_overflow_warns(self):
        st = resolve(self.steps(6, "工程", items=30))
        self.assertTrue(any(code == "steps-overflow" for _, code, _ in issues(st, "warn")))

    def test_card_height_uses_item_params(self):
        b_ = {**LAYOUT["types"]["steps"]["body"], "item_size": 12, "child_size": 10}
        proto = autofit.steps_item_params(b_, 200)
        self.assertEqual((proto["size"], proto["child_size"]), (12, 10))


class StatusTableTests(unittest.TestCase):
    def slide(self, rows):
        return {"type": "status_table", "title": "t", "columns": ["項目", "状況", "計画", "実績"],
                "rows": [{"label": f"工程{i}", "cells": [[jp(30)] * 3, [jp(30)] * 3], "status": "green"} for i in range(rows)]}

    def test_geometry_matches_autofit_rows(self):
        slide = self.slide(3)
        st = resolve(slide)
        geo = b.status_table_geometry(slide, st)
        ws, rows = autofit.status_table_rows(slide, st["table"])
        self.assertEqual([round(r["need"], 3) for r in geo["rows"]], [round(r["need"], 3) for r in rows])

    def test_few_rows_keep_cell_size(self):
        st = resolve(self.slide(2))
        self.assertEqual(st["table"]["cell_size"], 13)
        self.assertEqual(issues(st), [])

    def test_many_rows_shrink_cell_size(self):
        st = resolve(self.slide(8))
        self.assertLess(st["table"]["cell_size"], 13)

    def test_overflow_warns_with_rows_that_fit(self):
        st = resolve(self.slide(14))
        warns = issues(st, "warn")
        self.assertTrue(warns)
        self.assertIn("行以下に減らして", warns[0][2])
        self.assertEqual(st["table"]["cell_size"], 11)

    def test_talk_density_grows_cell_size(self):
        st = resolve(self.slide(2), density="talk")
        self.assertGreater(st["table"]["cell_size"], 13)


class MatrixTests(unittest.TestCase):
    def slide(self, body, points=None):
        s = {"type": "matrix", "title": "t", "x_axis": {"label": "x", "low": "l", "high": "h"},
             "y_axis": {"label": "y", "low": "l", "high": "h"},
             "quadrants": [{"heading": f"象限{i}", "body": body} for i in range(4)]}
        if points:
            s["points"] = points
        return s

    def test_short_keeps_size(self):
        self.assertEqual(resolve(self.slide("短い説明"))["grid"]["body_size"], 14)

    def test_long_body_shrinks_then_warns(self):
        st = resolve(self.slide(jp(200)))
        self.assertLess(st["grid"]["body_size"], 14)
        st2 = resolve(self.slide(jp(400)))
        self.assertTrue(issues(st2, "warn"))

    def test_long_point_label_warns(self):
        st = resolve(self.slide("a", [{"x": 0.5, "y": 0.5, "label": jp(100)}]))
        self.assertTrue(any(code == "matrix-point-label" for _, code, _ in issues(st, "warn")))

    def test_point_label_box_grows_with_lines(self):
        ctx = pe.Ctx(THEME)
        st = resolve(self.slide("a", [{"x": 0.5, "y": 0.5, "label": jp(60)}]))
        els = pe.matrix_points({"points": [{"x": 0.5, "y": 0.5, "label": jp(60)}]}, st, ctx)
        label = [e for e in els if e.get("name") == "点1の名前"][0]
        self.assertGreater(label["h"], 22)


class ProposalFitTests(unittest.TestCase):
    def test_kpi_tree_long_root_shrinks_then_warns(self):
        # 目標（root）の箱も文字量でフィットする（core-A-03）
        def slide(root):
            return {"type": "kpi_tree", "title": "t", "root": root,
                    "branches": [{"title": "施策", "kpis": [{"title": "KPI", "value": "10%", "note": "測り方"}]}]}
        self.assertEqual(issues(resolve(slide("売上を伸ばす")), "warn"), [])
        mid = issues(resolve(slide("新規顧客からの売上を前年比120%に伸ばし、既存顧客の解約も減らす")))
        self.assertFalse([i for i in mid if i[0] == "warn"])
        long_ = issues(resolve(slide("項目の説明文として四十字程度の日本語が入ります。" * 8)), "warn")
        self.assertTrue(any("目標の文字" in t for _, _, t in long_))

    def test_statement_overflow_reaches_the_floor_even_with_huge_cap(self):
        # cap が 48 を超えても、刻みが floor を通らず 40px などで止まらない（core-C-05）
        msg = "あ" * 400
        for size in (None, 60, 120, 500):
            slide = {"type": "statement", "message": msg}
            if size:
                slide["style"] = {"message": {"size": size}}
            st = resolve(slide)
            warns = issues(st, "warn")
            self.assertTrue(warns, size)
            self.assertIn("最小の文字サイズ（28px）", warns[0][2], size)

    def test_summary_that_fits_has_no_warning(self):
        slide = {"type": "summary", "title": "t", "items": [{"lead": jp(10), "text": jp(30)} for _ in range(4)]}
        self.assertEqual(issues(resolve(slide), "warn"), [])

    def test_summary_twelve_items_warns_instead_of_silently_using_the_smallest(self):
        slide = {"type": "summary", "title": "t", "items": [{"lead": jp(10), "text": jp(60)} for _ in range(12)]}
        warns = issues(resolve(slide), "warn")
        self.assertTrue(warns)
        self.assertIn("最小の文字サイズ", warns[0][2])

    def test_summary_text_with_newlines_is_measured(self):
        slide = {"type": "summary", "title": "t", "items": [{"lead": "a", "text": "\n".join(["行"] * 8)} for _ in range(6)]}
        self.assertTrue(issues(resolve(slide), "warn"))

    def test_reasons_row_matrix_house_kpi_cycle_report(self):
        long = jp(120)
        cases = {
            "reasons": {"issues": [{"title": long, "text": long}] * 5, "strengths": [{"title": long, "text": long}] * 5},
            "row_matrix": {"columns": ["a", "b"], "rows": [{"label": "x", "cells": [long, long]}] * 6},
            "house": {"roof": {"title": "屋根"}, "pillars": [{"title": "柱", "items": [long] * 4}] * 4},
            "kpi_tree": {"root": "目標", "branches": [{"title": "b", "kpis": [{"title": long, "value": "10%"}] * 4}] * 3},
            "cycle": {"stages": [{"title": "段", "text": long * 4}] * 6},
        }
        for t, extra in cases.items():
            slide = {"type": t, "title": "t", **extra}
            self.assertTrue(issues(resolve(slide), "warn"), t)

    def test_kpi_value_that_does_not_fit_the_value_box_is_shrunk_or_reported(self):
        slide = {"type": "kpi_tree", "title": "t", "root": "目標",
                 "branches": [{"title": "b%d" % i, "kpis": [{"title": "k", "value": "10%"}] * 3} for i in range(4)]}
        entries = pe.fit_report(slide, resolve(slide))
        tags = {e["tag"] for e in entries}
        self.assertIn("kpi_tree.value", tags)

    def test_statement_size_is_an_upper_limit_not_a_cliff(self):
        slide = {"type": "statement", "title": "t", "message": "6.5時間から2.1時間へ"}
        st = resolve(slide, )
        st["message"]["size"] = 100
        entries = pe.fit_report(slide, st)
        chosen = [e["chosen"] for e in entries if e["tag"] == "statement"][0]
        self.assertGreater(chosen, 40)          # 以前は 100 が入らないと一気に 28 になった（A5-03）
        self.assertTrue(all(e["ok"] for e in entries))

    def test_statement_overflow_warns(self):
        slide = {"type": "statement", "title": "t", "message": jp(400)}
        self.assertTrue(issues(resolve(slide), "warn"))

    def test_density_sizes_are_passed_to_the_engine(self):
        slide = {"type": "summary", "title": "t", "items": [{"lead": "a", "text": "b"}] * 3}
        self.assertEqual(resolve(slide, density="talk")["body"]["sizes"][0], [26, 20])


class BottomPartsTests(unittest.TestCase):
    def test_short_conclusion_is_unchanged(self):
        st = resolve(bullets_slide(3, 10, conclusion="短い結論"))
        self.assertEqual(st["conclusion"]["size"], 17)
        self.assertEqual(st["conclusion"]["h"], 40)

    def test_long_conclusion_shrinks_or_grows_the_band(self):
        st = resolve(bullets_slide(3, 10, conclusion=jp(70)))
        c = st["conclusion"]
        self.assertTrue(c["size"] < 17 or c["h"] > 40)
        self.assertFalse(issues(st, "warn"))

    def test_conclusion_that_cannot_fit_warns(self):
        st = resolve(bullets_slide(3, 10, conclusion=jp(400)))
        self.assertTrue(any(code == "conclusion-overflow" for _, code, _ in issues(st, "warn")))

    def test_long_conclusion_on_proposal_type(self):
        slide = {"type": "reasons", "title": "t", "issues": [{"title": "a"}], "strengths": [{"title": "b"}],
                 "conclusion": jp(90)}
        st = resolve(slide)
        self.assertTrue(st["conclusion"]["size"] < 17 or st["conclusion"]["h"] > 40)

    def test_three_line_source_reserves_height_and_warns(self):
        st = resolve(bullets_slide(3, 10, source="出典" + jp(240)))
        self.assertGreater(st["source"]["h"], 18)
        self.assertGreater(st["source"]["reserve"], 20)
        self.assertTrue(any(code == "source-long" for _, code, _ in issues(st, "warn")))

    def test_explicit_conclusion_size_is_kept(self):
        st = resolve(bullets_slide(3, 10, conclusion=jp(70), style={"conclusion": {"size": 17, "h": 40}}))
        self.assertEqual((st["conclusion"]["size"], st["conclusion"]["h"]), (17, 40))
        self.assertTrue(issues(st, "warn"))


class ScheduleOverflowTests(unittest.TestCase):
    def slide(self, n, lead=True):
        s = {"type": "schedule", "title": "t",
             "timeline": {"unit": "month", "start": "2026-04", "end": "2026-12"},
             "rows": [{"label": f"工程{i}", "bars": [{"start": "2026-04", "end": "2026-06", "label": "x"}]} for i in range(n)]}
        if lead:
            s["lead"] = "リード"
        return s

    def diags(self, slide):
        st = resolve(slide)
        return se.layout_schedule(slide, st["chart"])["diagnostics"]

    def test_eighteen_rows_with_lead_report_overflow_with_row_count(self):
        d = [x for x in self.diags(self.slide(18)) if x["code"] == "chart-overflow"]
        self.assertEqual(len(d), 1)
        self.assertIn("はみ出し", d[0]["message"])
        self.assertTrue(any("行以下" in f for f in d[0]["fixes"]))

    def test_no_lead_fits_fourteen_rows(self):
        d = [x for x in self.diags(self.slide(14, lead=False)) if x["code"] == "chart-overflow"]
        self.assertEqual(d, [])

    def test_ten_rows_no_overflow(self):
        self.assertEqual([x for x in self.diags(self.slide(10)) if x["code"] == "chart-overflow"], [])


class OldEstimatesGoneTests(unittest.TestCase):
    def test_check_overflow_prints_autofit_issues_with_slide_label(self):
        slide = bullets_slide(30, 60)
        st = resolve(slide)
        b._WARNED.clear() if hasattr(b, "_WARNED") else None
        with quiet() as err:
            b._check_overflow(slide, st, 4, "bullets")
        self.assertIn("5枚目（type=bullets）", err.getvalue())

    def test_check_overflow_has_no_per_type_estimate_branches(self):
        import inspect
        src = inspect.getsource(b._check_overflow)
        for gone in ("estimate_bullets_height", "status_table_geometry", "warn_bullets"):
            self.assertNotIn(gone, src)


class BuildTests(unittest.TestCase):
    def build(self, slides, **meta):
        d = Path(tempfile.mkdtemp())
        (d / "deck.json").write_text(json.dumps({"meta": {"title": "t", "id": d.name, **meta}, "slides": slides},
                                                ensure_ascii=False), encoding="utf-8")
        p = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True)
        return d, p

    def test_build_reports_overflow_for_cards_and_steps_and_status(self):
        slides = [
            {"type": "cards", "title": "c", "cards": [{"heading": "h", "body": jp(60), "items": [jp(40)] * 4}] * 18},
            {"type": "steps", "title": "s", "steps": [{"label": "とても長いステップの見出しですよ", "items": ["x"]}] * 10},
            {"type": "status_table", "title": "st", "columns": ["a", "b", "c", "d"],
             "rows": [{"label": "x", "cells": [[jp(30)] * 3, [jp(30)] * 3], "status": "green"}] * 14},
        ]
        d, p = self.build(slides)
        self.assertEqual(p.returncode, 0, p.stderr)
        for label in ("1枚目（type=cards）", "2枚目（type=steps）", "3枚目（type=status_table）"):
            self.assertIn(label, p.stderr)

    def test_dense_read_deck_builds_html_and_pptx(self):
        slides = [bullets_slide(6, 30), {"type": "two_column", "title": "t",
                                         "left": {"heading": "a", "bullets": ["x", "y"]},
                                         "right": {"heading": "b", "bullets": ["x", "y"]}},
                  {"type": "cards", "title": "c", "cards": [{"heading": "h", "body": "b", "items": ["i"]}] * 3},
                  {"type": "steps", "title": "s", "steps": [{"label": "l", "items": ["i"]}] * 3}]
        for dens in ("read", "talk"):
            d, p = self.build(slides, density=dens)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(list((d / "build").glob("*.pptx")))


if __name__ == "__main__":
    unittest.main()

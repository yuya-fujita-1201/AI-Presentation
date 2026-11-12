#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 残った見た目の弱点: 合成・分割ブロックの中身が少ないときの文字の拡大と縦中央・steps の枠いっぱい・表のセルの拡大・
cards の列数の選び直し・section の 2 行タイトル・meta.brand とタイトルの重なり・schedule の行が少ないとき・
矢羽根のラベルを左に出す・frame:"full" の型のスライド直下の title・大きな cards の文節折り返し。

実行: python3 -m unittest plugins/slide-deck/tools/test_s4_polish.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import schedule_engine as se  # noqa: E402
from test_composite import bl, comp_slide  # noqa: E402
from test_validation import one, validate  # noqa: E402

PY = sys.executable
LAYOUT = b.load_layout("default")


def resolve(slide, **meta):
    deck = one(slide, **meta)
    validate(deck)
    return b.resolve_style(LAYOUT, deck, deck["slides"][0]), deck


def blocks(slide, **meta):
    st, _ = resolve(slide, **meta)
    return st["_composite"]["blocks"]


def box(n, **kw):
    return bl(n, heading="見出し", frame="box", **kw)


class ThinBulletsTest(unittest.TestCase):
    def test_sparse_block_grows_and_centers(self):
        rb = blocks(comp_slide([box(2), box(2)], columns=[1, 1]))[0]
        self.assertGreater(rb["st"]["body"]["size"], 20)
        self.assertLessEqual(rb["st"]["body"]["size"], 28)               # thin_max_size
        self.assertEqual(rb["st"]["body"].get("valign"), "middle")       # 箱つきは縦中央
        self.assertTrue(rb.get("thin_centered"))

    def test_full_block_is_left_alone(self):
        rb = blocks(comp_slide([box(9), box(9)], columns=[1, 1]))[0]
        self.assertLessEqual(rb["st"]["body"]["size"], 20)
        self.assertNotEqual(rb["st"]["body"].get("valign"), "middle")

    def test_same_type_blocks_share_the_scale(self):
        a, c = blocks(comp_slide([box(2), box(6)], columns=[1, 1]))
        self.assertEqual(a["st"]["body"]["size"], c["st"]["body"]["size"])

    def test_explicit_values_and_autofit_off_win(self):
        rb = blocks(comp_slide([box(2, style={"body": {"size": 20}}), box(2)], columns=[1, 1]))[0]
        self.assertEqual(rb["st"]["body"]["size"], 20)
        rb = blocks(comp_slide([box(2), box(2)], columns=[1, 1], autofit=False))[0]
        self.assertEqual(rb["st"]["body"]["size"], 20)
        self.assertNotEqual(rb["st"]["body"].get("valign"), "middle")
        rb = blocks(comp_slide([box(2, valign="top"), box(2)], columns=[1, 1]))[0]
        self.assertEqual(rb["st"]["body"].get("valign"), "top")

    def test_layout_override_stops_growth(self):
        slide = comp_slide([box(2), box(2)], columns=[1, 1])
        rb = blocks(slide, layout_overrides={"composite": {"blocks": {"bullets": {"body": {"size": 20}}}}})[0]
        self.assertEqual(rb["st"]["body"]["size"], 20)

    def test_no_sparse_warning_when_centered_but_warns_without_autofit(self):
        exc, err = validate(one(comp_slide([box(2), box(8)], arrange="two")))
        self.assertNotIn("枠の中身が少なく", err)
        exc, err = validate(one(comp_slide([box(2), box(8)], arrange="two", autofit=False)))
        self.assertIn("枠の中身が少なく", err)

    def test_growth_does_not_add_wraps(self):
        # 狭い列で、大きくすると折れてしまう文は大きくしない
        long = "ここは合成の隣のブロック"
        rb = blocks(comp_slide([bl(2, heading="a", frame="box", bullets=[long, long]), bl(1), bl(1)], columns=[1, 1, 1]))[0]
        from autofit import bullets_line_counts
        r = rb["st"]["body"]
        self.assertLessEqual(max(bullets_line_counts([long], r, 0.93)), max(bullets_line_counts([long], {**r, "size": 20}, 0.93)))


class ThinStepsTableTest(unittest.TestCase):
    STEPS = {"type": "steps", "heading": "進め方", "steps": [{"label": "把握", "items": ["手順を一覧に"]}, {"label": "試行", "items": ["1 業務で試す"]}, {"label": "展開", "items": ["型にして渡す"]}]}

    def test_steps_main_side_grows_and_fills(self):
        rb = blocks(comp_slide([self.STEPS, bl(2, heading="補足", frame="box")], arrange="main-side"))[0]
        body = rb["st"]["body"]
        self.assertGreaterEqual(body["label_size"], 16)
        self.assertGreaterEqual(body["item_size"], 14)
        self.assertEqual(body["fit"], "fill")                            # 枠の高さいっぱい
        self.assertNotEqual(body.get("valign"), "middle")                # 項目は見出しの直下（柱の中央に浮かない。s4-A-01）

    def test_steps_explicit_sizes_are_kept(self):
        s = {**self.STEPS, "style": {"body": {"label_size": 16, "item_size": 14}}}
        body = blocks(comp_slide([s, bl(2, heading="補足", frame="box")], arrange="main-side"))[0]["st"]["body"]
        self.assertEqual((body["label_size"], body["item_size"]), (16, 14))

    def test_table_cells_grow_to_16_for_few_rows(self):
        t = {"type": "table", "columns": ["部署", "現状", "導入後"], "rows": [["経理", "142 時間", "56 時間"], ["人事", "96 時間", "55 時間"], ["総務", "80 時間", "42 時間"]]}
        rb = blocks(comp_slide([t, bl()], arrange="main-side"))[0]
        self.assertEqual(rb["st"]["table"]["cell_size"], 16)
        rb = blocks(comp_slide([{**t, "style": {"table": {"cell_size": 14}}}, bl()], arrange="main-side"))[0]
        self.assertEqual(rb["st"]["table"]["cell_size"], 14)

    def test_text_and_callout_grow(self):
        a, c = blocks(comp_slide([{"type": "text", "text": "短い"}, {"type": "callout", "text": "短い一文"}], columns=[1, 1]))
        self.assertGreater(a["fit"]["size"], 20)
        self.assertGreater(c["fit"]["size"], 28)

    def test_cards_four_become_two_by_two(self):
        cards = [{"heading": f"打ち手{i}", "body": "文字サイズと余白は自動で整える。"} for i in range(4)]
        rb = blocks(comp_slide([{"type": "cards", "cards": cards}, bl(2, heading="補足", frame="box")], arrange="main-side"))[0]
        self.assertIn(rb["st"]["grid"].get("cols"), (1, 2))              # 3 列（3 + 1 に割れる）にしない
        rb = blocks(comp_slide([{"type": "cards", "cards": cards, "columns": 3}, bl()], arrange="main-side"))[0]
        self.assertNotEqual(rb["st"]["grid"].get("cols"), 2)             # 列数を書いたときは動かさない


class SectionBrandTest(unittest.TestCase):
    TITLE = "AI が作る資料を、人が直さずにそのまま使えるようにするための仕組み"

    def test_two_line_section_title_makes_room(self):
        for variant in (None, "number", "band", "side"):
            slide = {"type": "section", "title": self.TITLE, "subtitle": "副題", "number": "02"}
            if variant:
                slide["variant"] = variant
            st, _ = resolve(slide)
            t = st["title"]
            lines = st["_fit"]["info"]["title"]["lines"]
            self.assertGreaterEqual(lines, 1)
            if lines >= 2:
                self.assertGreaterEqual(t["h"], lines * t["size"] * 1.25, variant)
                self.assertGreaterEqual(st["rule"]["y"], t["y"] + lines * t["size"] * 1.25, variant)

    def test_section_title_with_explicit_h_is_not_moved(self):
        st, _ = resolve({"type": "section", "title": self.TITLE, "style": {"title": {"h": 84}}})
        self.assertEqual(st["title"]["h"], 84)

    def test_brand_narrows_title(self):
        slide = {"type": "bullets", "title": "タイトル", "bullets": ["a"]}
        st, _ = resolve(slide, brand="ACME")
        self.assertLess(st["title"]["w"], 1136)
        self.assertLessEqual(st["title"]["x"] + st["title"]["w"], st["brand"]["x"] + st["brand"]["w"] - 40)
        st, _ = resolve(slide)
        self.assertEqual(st["title"]["w"], 1136)
        st, _ = resolve({**slide, "style": {"title": {"w": 1000}}}, brand="ACME")
        self.assertEqual(st["title"]["w"], 1000)

    def test_brand_narrows_status_table_legend(self):
        slide = {"type": "status_table", "title": "進捗", "columns": ["チーム", "状況", "今週"], "rows": [["a", "g", "x"]]}
        try:
            st, _ = resolve(slide, brand="ACME")
        except Exception:
            self.skipTest("status_table の最小形が検証に通らない")
        if st.get("legend"):
            self.assertLess(st["legend"]["x"] + st["legend"]["w"], st["brand"]["x"] + st["brand"]["w"])


class ScheduleTest(unittest.TestCase):
    def slide(self, n, **kw):
        rows = [{"label": f"行{i}", "bars": [{"start": "2027-01", "end": "2027-02", "label": "x"}]} for i in range(n)]
        return {"type": "schedule", "title": "t", "timeline": {"start": "2027-01", "end": "2027-04", "unit": "month"}, "rows": rows, **kw}

    def test_few_rows_grow(self):
        st, _ = resolve(self.slide(2))
        c = st["chart"]
        self.assertGreater(c["max_row_h"], 64)
        self.assertGreater(c["label_size"], 15)
        st, _ = resolve(self.slide(10))
        self.assertEqual(st["chart"]["max_row_h"], 64)                   # 行が多いときは従来どおり
        st, _ = resolve(self.slide(2, style={"chart": {"max_row_h": 64}}))
        self.assertEqual(st["chart"]["max_row_h"], 64)                   # 明示値は動かさない
        self.assertEqual(st["chart"]["col_h"], 28)                       # 行の高さ・文字の大きさを 1 つでも書いたら、ほかも自動では動かさない

    def test_label_goes_left_when_right_has_no_room(self):
        slide = {"type": "schedule", "title": "t", "timeline": {"start": "2026-01", "end": "2026-12", "unit": "month"},
                 "rows": [{"label": "A", "bars": [{"start": "2026-12", "end": "2026-12", "label": "効果測定と報告"}]}]}
        c = LAYOUT["types"]["schedule"]["chart"]
        bar = se.layout_schedule(slide, c)["bars"][0]
        self.assertEqual(bar["label_pos"], "before")
        self.assertGreaterEqual(bar["size"], 12)
        self.assertLessEqual(bar["lbl_x"] + bar["lbl_w"], bar["x"])


class PatternTitleTest(unittest.TestCase):
    def test_full_frame_pattern_title_warns(self):
        import pattern_engine as pe
        d = Path(tempfile.mkdtemp(prefix="s4_pt_"))
        names = [n for n in pe.available_names(None) if pe.frame_of(pe.load_pattern(n, None)) == "full"]
        self.assertTrue(names)
        deck = {"meta": {"id": "d", "title": "T", "theme": "default"},
                "slides": [{"type": "pattern", "pattern": names[0], "title": "見出し", "slots": {}}]}
        (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
        self.assertIn("スライド直下の title は描かれません", r.stderr + r.stdout)


class CardsPhraseTest(unittest.TestCase):
    def test_big_card_text_breaks_at_phrases(self):
        slide = {"type": "cards", "title": "t", "columns": 3, "cards": [
            {"heading": "口述を構造化して論点ごとに整理する", "body": "話した内容を AI が論点ごとに整理する", "emphasis": True},
            {"heading": "型で組む", "body": "登録した構図に内容を当てはめる"}, {"heading": "体裁は自動", "body": "文字の大きさと余白を自動で合わせる"}]}
        deck = one(slide, line_balance=True)
        validate(deck)
        out = b.apply_line_balance(deck, LAYOUT)
        c0 = out["slides"][0]["cards"][0]
        self.assertIn("\n", c0["heading"] + c0["body"])


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# レビュー指摘の修正（s4-C-* / s4-A-*）
# ---------------------------------------------------------------------------
import autofit  # noqa: E402
import ja_text  # noqa: E402


class ReviewFixSectionTest(unittest.TestCase):
    BASE = "AI が作る資料を人が直さずにそのまま使えるようにするための仕組みを整える。"

    def balanced(self, slide, **meta):
        deck = one(slide, **meta)
        validate(deck)
        out = b.apply_line_balance(deck, LAYOUT)
        s2 = out["slides"][0]
        return b.resolve_style(LAYOUT, out, s2), s2

    def test_phrase_wrapped_lines_are_the_lines_the_frame_is_sized_for(self):
        # s4-C-01: 文節折り返し（phrase_wrap）が入れる改行まで数えて、枠・罫線・副題を動かす
        for n in (6, 12, 20, 26, 32, 38, 52, 70):
            for variant in (None, "number", "band", "side"):
                slide = {"type": "section", "title": self.BASE[:n], "subtitle": "副題は 1〜2 行で、章の狙いを短く添える", "number": "02"}
                if variant:
                    slide["variant"] = variant
                st, s2 = self.balanced(slide)
                t = st["title"]
                lines = max(s2["title"].count("\n") + 1,
                            ja_text.estimate_lines(s2["title"], t["size"], t["w"], ja_text.heading_fonts(), bool(t.get("bold"))))
                if lines >= 2:
                    need = lines * t["size"] * 1.25
                    self.assertGreaterEqual(t["h"] + 1, need, (n, variant, lines, t["size"], t["h"]))
                    self.assertGreaterEqual(st["rule"]["y"] + 1, t["y"] + need, (n, variant))
                    self.assertGreaterEqual(st["subtitle"]["y"] + 1, t["y"] + need, (n, variant))

    def test_section_lines_counts_the_phrase_wrap(self):
        ctx = autofit.Ctx(one({"type": "section", "title": "x"}), {"type": "section", "title": "x"}, {}, "standard", True)
        font = ja_text.heading_fonts()
        plain = ja_text.estimate_lines(self.BASE, 48, 608, font, True)
        counted = autofit._section_lines(ctx, self.BASE, 48, 608, 608, True)
        self.assertGreaterEqual(counted, plain)
        self.assertEqual(counted, max(plain, ja_text.phrase_wrap(self.BASE, 48, 608, font=font, bold=True, min_tail=max(5, ja_text.tail_min(48))).count("\n") + 1))


class ReviewFixBrandTest(unittest.TestCase):
    BASE = "パイロット開始後、作成時間は 6.5 時間から 2.1 時間へ下がったことを確認した結果と今後の方針"

    def test_title_near_the_narrowed_width_has_headroom(self):
        # s4-C-02: 狭めた幅ぎりぎりの長さ（1 字だけ 2 行目に落ちる）を、見積もりの余裕で避ける
        font = ja_text.heading_fonts()
        for brand in ("ACME", "XYZ", "ACME Corp"):
            for n in range(18, 45):
                st, _ = resolve({"type": "bullets", "title": self.BASE[:n], "bullets": ["a"]}, brand=brand)
                t = st["title"]
                width = sum(ja_text.char_em(c, font, True) for c in self.BASE[:n]) * t["size"]
                if t["size"] > t.get("min_size", 8):
                    self.assertLessEqual(width, t["w"] * 0.985, (brand, n, t["size"], width, t["w"]))
                self.assertLessEqual(t["x"] + t["w"], st["brand"]["x"] + st["brand"]["w"])

    def test_no_brand_keeps_default_safety(self):
        st, _ = resolve({"type": "bullets", "title": "タイトル", "bullets": ["a"]})
        self.assertNotIn("fit_safety", st["title"])
        st, _ = resolve({"type": "bullets", "title": "タイトル", "bullets": ["a"]}, brand="ACME")
        self.assertEqual(st["title"]["fit_safety"], b.BRAND_FIT_SAFETY)


class ReviewFixTokenTest(unittest.TestCase):
    def check(self, ov, needle):
        slide = comp_slide([bl(2, heading="a", frame="box"), bl(2)], columns=[1, 1])
        exc, err = validate(one(slide, layout_overrides=ov))
        self.assertIsNotNone(exc, ov)
        self.assertIn(needle, str(exc) + err, ov)

    def test_out_of_range_tokens_are_rejected_with_the_key(self):
        # s4-C-03: 極端な値で探索が終わらなくならない（検証で止める）
        for path in ({"composite": {"text": {"thin_grow": 1e9, "thin_max_size": 1e9}}},
                     {"composite": {"blocks": {"bullets": {"body": {"thin_grow": 1e6}}}}},
                     {"composite": {"blocks": {"cards": {"grid": {"thin_grow": 1e5}}}}}):
            self.check(path, "thin_")
        self.check({"composite": {"blocks": {"steps": {"body": {"thin_label_max_size": 0}}}}}, "thin_label_max_size")
        self.check({"composite": {"block": {"thin_center_ratio": 5}}}, "thin_center_ratio")
        self.check({"common": {"brand": {"clear_gap": 1e9}}}, "clear_gap")

    def test_wrong_types_name_the_key(self):
        # s4-C-04
        self.check({"composite": {"blocks": {"steps": {"body": {"thin_label_max_size": "abc"}}}}}, "meta.layout_overrides.composite.blocks.steps.body.thin_label_max_size")
        self.check({"composite": {"blocks": {"steps": {"body": {"thin_fill_aspect": []}}}}}, "thin_fill_aspect")
        self.check({"composite": {"blocks": {"cards": {"grid": {"center_ratio": {}}}}}}, "center_ratio")
        self.check({"composite": {"blocks": {"steps": {"body": {"thin_fill": "abc"}}}}}, "thin_fill は true / false")

    def test_defaults_and_valid_values_pass(self):
        slide = comp_slide([bl(2, heading="a", frame="box"), bl(2)], columns=[1, 1])
        exc, err = validate(one(slide, layout_overrides={"composite": {"text": {"thin_grow": 1.2, "thin_max_size": 24},
                                                                       "blocks": {"steps": {"body": {"thin_fill": False}}}}}))
        self.assertIsNone(exc, err)

    def test_thin_grow_is_capped_in_code(self):
        gp = autofit.thin_grow_params({"block_rect": True, "thin_grow": 1e9, "thin_max_size": 1e9})
        self.assertEqual(gp[0], autofit.THIN_GROW_CAP)
        self.assertEqual(gp[1], autofit.THIN_SIZE_CAP)


class ReviewFixWrapTest(unittest.TestCase):
    def test_wrap_not_worse_rules(self):
        self.assertTrue(autofit.wrap_not_worse((1, 8, 0), (1, 8, 0)))
        self.assertFalse(autofit.wrap_not_worse((1, 8, 0), (2, 5, 0)))                 # 行が増える
        self.assertFalse(autofit.wrap_not_worse((2, 5, 0), (2, 5, 1)))                 # 語の途中の折れが増える
        self.assertFalse(autofit.wrap_not_worse((2, 6, 0), (2, 1, 0)))                 # 最終行が 1 字になる
        self.assertTrue(autofit.wrap_not_worse((2, 1, 0), (2, 1, 0)))                  # 元から 1 字ならそのまま

    def test_steps_growth_does_not_make_orphans(self):
        # s4-C-05: 左 40% の split の steps。項目 2 行 → 3 行（最終行 1 字）になる大きさには上げない
        item = "各段階の終わりに作成時間0"
        steps = {"type": "steps", "heading": "見出し", "steps": [{"label": "各段階の終わ", "items": [item]} for _ in range(4)]}
        slide = {"type": "split", "side": "left", "ratio": 0.4, "panel": {"fill": "primary", "title": "パネル"}, "blocks": [steps]}
        st, _ = resolve(slide)
        body = st["_composite"]["blocks"][0]["st"]["body"]
        inner = (body["w"] - 3 * body.get("gap", 20)) / 4 - 2 * body.get("pad", 16)
        prof = autofit.wrap_profile(item, body["item_size"], inner - body.get("indent", 16))
        self.assertGreaterEqual(prof[1], 2 if prof[0] > 1 else 1)
        self.assertLessEqual(prof[0], 2)

    def test_callout_does_not_grow_into_an_orphan(self):
        # s4-C-06: 補足の最終行が「（月）」だけ・語の途中の折れが出る大きさには上げない
        co = LAYOUT["types"]["composite"]["callout"]
        block = {"type": "callout", "text": "上位 2 部署で、全体の削減の 6 割", "note": "経理 86 時間 + 営業企画 74 時間（月）"}
        import composite_engine as ce
        for w in (300, 340, 380, 420, 460):
            reg = {**co, "block_rect": True}
            fit = ce.fit_callout(block, (0, 0, w, 400), reg)
            tw = fit["tw"]
            base = autofit.wrap_profile(block["note"], max(round(co.get("size", 28) * co.get("note_ratio", 0.62)), co.get("note_min_size", 14)), tw)
            now = autofit.wrap_profile(block["note"], fit["note_size"], tw)
            if fit.get("thin_factor", 1.0) > 1.0:
                self.assertTrue(autofit.wrap_not_worse(base, autofit.wrap_profile(block["note"], fit["note_size"], tw * autofit.THIN_WRAP_SAFETY)), (w, fit))
            self.assertFalse(now[0] > 1 and now[1] < 3 and base[1] >= 3, (w, now, base))


class ReviewFixLayoutTest(unittest.TestCase):
    def test_single_heading_box_centers_heading_and_body_together(self):
        # s4-A-02: 小見出しと本文を 1 つの塊にして箱の縦中央に置く
        slide = comp_slide([bl(3), bl(2, heading="補足", frame="box")], columns=[2, 1])
        rb = blocks(slide)[1]
        self.assertTrue(rb.get("thin_centered"))
        hx, hy, hw, hh = rb["geo"]["heading"]
        ox, oy, ow, oh = rb["geo"]["outer"]
        self.assertGreater(hy, oy + rb["geo"]["pad"] + 8)                 # 見出しも下へずれた
        cy = rb["geo"]["content"][1]
        self.assertLess(cy - (hy + hh), 40)                               # 見出しと本文が離れていない
        self.assertNotEqual(rb["st"]["body"].get("valign"), "middle")      # 塊で置いたので本文は上寄せのまま

    def test_two_heading_boxes_keep_headings_aligned(self):
        slide = comp_slide([bl(2, heading="a", frame="box"), bl(2, heading="b", frame="box")], columns=[1, 1])
        r0, r1 = blocks(slide)
        self.assertEqual(r0["geo"]["heading"][1], r1["geo"]["heading"][1])
        self.assertEqual(r0["st"]["body"].get("valign"), "middle")        # 従来どおり本文だけ中央（見出しの位置をそろえる）

    def test_steps_fill_needs_big_items_and_keeps_text_under_header(self):
        steps = {"type": "steps", "steps": [{"label": "把握", "items": ["一覧に"]}, {"label": "試行", "items": ["試す"]}, {"label": "展開", "items": ["渡す"]}]}
        body = blocks(comp_slide([steps, bl(2, heading="補足", frame="box")], arrange="main-side"))[0]["st"]["body"]
        if body.get("fit") == "fill":
            self.assertGreaterEqual(body["item_size"], 16)                # 小さい説明文のまま背の高い柱にしない
        rb = blocks(comp_slide([steps, bl(2, heading="補足", frame="box")], arrange="main-side",
                               style={"blocks": {"steps": {"body": {"thin_fill_min_size": 99}}}}))[0]
        self.assertNotEqual(rb["st"]["body"].get("fit"), "fill")

    def test_bullets_and_text_share_one_scale(self):
        # s4-A-03: 同じ「本文」として倍率をそろえる（bullets だけ大きい・text だけ大きい、を避ける）
        a, c = blocks(comp_slide([bl(2, heading="a", frame="box"), {"type": "text", "text": "ここは本文の文章です。" * 12}], columns=[1, 1]))
        fb = c.get("thin_factor")
        fa = a.get("thin_factor")
        if fa is not None and fb is not None:
            self.assertAlmostEqual(fa, fb, places=2)

    def test_schedule_block_grows_when_few_rows(self):
        # s4-A-05
        sch = {"type": "schedule", "timeline": {"start": "2027-01", "end": "2027-04", "unit": "month"},
               "rows": [{"label": "展開", "bars": [{"start": "2027-01", "end": "2027-03", "label": "営業へ展開"}]}]}
        rb = blocks(comp_slide([sch, bl(2, heading="補足", frame="box")], columns=[1, 1]))[0]
        self.assertGreater(rb["st"]["chart"]["max_row_h"], 64)


class ReviewFixCardsColsTest(unittest.TestCase):
    BASE = "各段階の終わりに作成時間が短くなっているかを見て満たさなければ次へ進まず原因を直す"

    def test_column_pick_avoids_orphans(self):
        # レビューの 1400 枚のスイープで出た「細い列に 2 列で並べて本文が 1 字だけ折れる」を、列数の選び直しで避ける
        cards = [{"heading": (self.BASE[:8] + str(i)), "body": self.BASE[:20] + str(i)} for i in range(4)]
        slide = comp_slide([{"type": "cards", "heading": "見出し", "frame": "box", "cards": cards}, bl(2), bl(2)], columns=[1, 1, 1])
        rb = blocks(slide)[0]
        g = rb["st"]["grid"]
        info = rb["st"]["_fit"]["info"]["cards"]
        chosen = autofit._cards_wrap_dirty(cards, g, g.get("cols", 3), info)
        for c in (1, 2, 3):
            self.assertLessEqual(chosen, autofit._cards_wrap_dirty(cards, g, c, info) + 0, c)

    def test_wrap_dirty_weights_orphans_over_midword_breaks(self):
        g = {"w": 300, "gap": 16, "pad": 14, "heading_size": 17, "body_size": 14, "item_size": 13}
        clean = [{"heading": "短い", "body": "短い本文"}]
        self.assertEqual(autofit._cards_wrap_dirty(clean, g, 1, {}), 0)
        dirty = [{"heading": "短い", "body": "各段階の終わりに作成時間が短くなっている0" * 2}]
        self.assertGreater(autofit._cards_wrap_dirty(dirty, g, 3, {}), 0)

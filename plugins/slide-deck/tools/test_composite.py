#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2c 合成スライド（type: "composite"）のテスト: 格子の割り付け（自動・明示・span・名前つき）/ 枠と小見出し /
各ブロックタイプの HTML・PPTX / 検証（fail・warn・未知キー・入れ子の拒否）/ 場所つきの警告 / lint・check_diagram・metrics /
editorial の title.min_size のトークン化。

実行: python3 -m unittest plugins/slide-deck/tools/test_composite.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import composite_engine as comp  # noqa: E402
import deck_metrics as dm  # noqa: E402
import lint_deck_text as lint  # noqa: E402
from test_s2a_wiring import make_assets  # noqa: E402
from test_validation import one, validate, write_deck  # noqa: E402

PY = sys.executable


def build(deck_dir, *extra):
    return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir), *extra], capture_output=True, text=True, encoding="utf-8")


def bl(n=3, **kw):
    return dict({"type": "bullets", "bullets": [f"項目{i + 1}" for i in range(n)]}, **kw)


def comp_slide(blocks, **kw):
    return dict({"type": "composite", "title": "合成のテスト", "blocks": blocks}, **kw)


ARCH = {"type": "architecture",
        "nodes": [{"id": "a", "type": "external", "label": "利用者", "row": 0, "col": 0},
                  {"id": "b", "type": "backend", "label": "API", "row": 0, "col": 1}],
        "edges": [{"from": "a", "to": "b"}]}
TABLE = {"type": "table", "columns": ["部署", "時間"], "rows": [["経理", "86"], ["営業", "74"]]}
KPI = {"type": "kpi", "items": [{"value": "2.1", "unit": "時間", "label": "作成時間"}]}
CHART = {"type": "chart", "chart": "bar", "unit": "時間", "categories": ["Q1", "Q2"], "series": [{"name": "x", "values": [3, 2]}]}


class GridPlanTests(unittest.TestCase):
    def cells(self, n, **kw):
        return comp.plan_grid([{"type": "text"} for _ in range(n)], **kw)

    def test_auto_two_blocks_default_two_columns(self):
        p = self.cells(2)
        self.assertEqual(p["columns"], [1.0, 1.0])
        self.assertEqual(p["cells"], [(0, 0, 1, 1), (1, 0, 1, 1)])
        self.assertFalse(p["problems"])

    def test_default_columns_depend_on_block_count(self):
        self.assertEqual(self.cells(1)["columns"], [1.0])
        self.assertEqual(self.cells(3)["columns"], [1.0, 1.0, 1.0])
        p4 = self.cells(4)
        self.assertEqual(p4["columns"], [1.0, 1.0])
        self.assertEqual(p4["cells"][3], (1, 1, 1, 1))          # 2×2 に自動で行が増える
        self.assertEqual(len(self.cells(5)["columns"]), 3)

    def test_wraps_rows_when_rows_unspecified(self):
        p = self.cells(3, columns=[1, 1])
        self.assertEqual(p["cells"][2], (0, 1, 1, 1))
        self.assertEqual(len(p["rows"]), 2)
        self.assertEqual(p["empty"], [(1, 1)])

    def test_rows_given_and_overflow_is_a_problem(self):
        p = self.cells(3, columns=[1, 1], rows=[1])
        self.assertTrue(p["problems"])
        self.assertIn("置ける場所がありません", p["problems"][0])
        self.assertIn("3 つ目のブロック", p["problems"][0])

    def test_explicit_position_and_auto_fill_around_it(self):
        blocks = [{"type": "text"}, {"type": "text", "col": 0, "row": 0}, {"type": "text"}]
        p = comp.plan_grid(blocks, columns=[1, 1], rows=[1, 1])
        self.assertEqual(p["cells"][1], (0, 0, 1, 1))            # 明示が先に置かれる
        self.assertEqual(p["cells"][0], (1, 0, 1, 1))            # 自動は空いている最初の場所
        self.assertEqual(p["cells"][2], (0, 1, 1, 1))

    def test_span(self):
        blocks = [{"type": "text", "col_span": 2}, {"type": "text"}, {"type": "text"}]
        p = comp.plan_grid(blocks, columns=[1, 1], rows=[1, 1])
        self.assertEqual(p["cells"], [(0, 0, 2, 1), (0, 1, 1, 1), (1, 1, 1, 1)])
        rects = comp.grid_rects({"x": 0, "y": 0, "w": 1000, "h": 400}, p, 20, 20)
        self.assertEqual(rects[0], (0.0, 0.0, 1000.0, 190.0))    # 横にまたがる矩形は全幅（間隔を含む）
        self.assertEqual(rects[1], (0.0, 210.0, 490.0, 190.0))

    def test_row_span(self):
        blocks = [{"type": "text", "row_span": 2}, {"type": "text"}, {"type": "text"}]
        p = comp.plan_grid(blocks, columns=[3, 2], rows=[1, 1])
        self.assertEqual(p["cells"], [(0, 0, 1, 2), (1, 0, 1, 1), (1, 1, 1, 1)])

    def test_overlap_and_out_of_range_are_problems(self):
        p = comp.plan_grid([{"type": "text", "col": 0, "row": 0}, {"type": "text", "col": 0, "row": 0}], columns=[1, 1], rows=[1])
        self.assertTrue(any("重なります" in m for m in p["problems"]))
        p = comp.plan_grid([{"type": "text", "col": 2, "row": 0}], columns=[1, 1], rows=[1])
        self.assertTrue(any("列の数" in m for m in p["problems"]))
        p = comp.plan_grid([{"type": "text", "col_span": 3}], columns=[1, 1], rows=[1])
        self.assertTrue(any("col_span" in m for m in p["problems"]))

    def test_named_arrangements(self):
        for name, spec in comp.ARRANGE.items():
            ok = False
            for n in range(1, 9):                      # ちょうど埋まるブロック数がある（空きなし・置けない場所なし）
                p = comp.plan_grid([{"type": "text"} for _ in range(n)], arrange=name)
                if not p["problems"] and not p["empty"]:
                    ok = True
                    break
            self.assertTrue(ok, name)
        p = comp.plan_grid([{"type": "text"}] * 3, arrange="main-side-stack")
        self.assertEqual(p["cells"], [(0, 0, 1, 2), (1, 0, 1, 1), (1, 1, 1, 1)])
        p = comp.plan_grid([{"type": "text"}] * 3, arrange="stack-main")
        self.assertEqual(p["cells"], [(0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 2)])

    def test_columns_rows_override_arrange(self):
        p = comp.plan_grid([{"type": "text"}] * 2, arrange="main-side", columns=[1, 1])
        self.assertEqual(p["columns"], [1.0, 1.0])
        # 名前の cells は格子の大きさが同じときだけ使う（rows を足したら自動配置）
        p = comp.plan_grid([{"type": "text"}] * 3, arrange="main-side-stack", columns=[1, 1, 1])
        self.assertEqual(p["cells"][0], (0, 0, 1, 1))

    def test_unknown_arrange_and_bad_ratios(self):
        p = comp.plan_grid([{"type": "text"}], arrange="main-sid")
        self.assertIn("main-side", p["problems"][0])
        p = comp.plan_grid([{"type": "text"}], columns=[1, 0])
        self.assertTrue(p["problems"])
        p = comp.plan_grid([{"type": "text"}], columns="3:2")
        self.assertTrue(p["problems"])

    def test_ratio_split_has_equal_gaps(self):
        xs = comp.split_axis(1100, [3, 2], 20)
        self.assertAlmostEqual(xs[0][1] / xs[1][1], 1.5)
        self.assertAlmostEqual(xs[1][0] - (xs[0][0] + xs[0][1]), 20)
        self.assertAlmostEqual(xs[1][0] + xs[1][1], 1100)

    def test_empty_cells_reported(self):
        p = comp.plan_grid([{"type": "text"}] * 2, columns=[1, 1, 1])
        self.assertEqual(p["empty"], [(2, 0)])


class FrameTests(unittest.TestCase):
    BK = {"pad": 20, "heading_size": 18, "heading_gap": 12, "rule_gap": 8, "rule_w": 1, "line_w": 3, "line_gap": 14}

    def test_headings_align_across_frames(self):
        ys = []
        for frame in ("none", "line"):
            g = comp.frame_geometry((100, 200, 500, 300), {"heading": "見出し", "frame": frame}, self.BK)
            ys.append(g["heading"][1])
        self.assertEqual(ys[0], ys[1])               # 枠なしと line は小見出しが同じ高さ
        g = comp.frame_geometry((100, 200, 500, 300), {"heading": "見出し", "frame": "box"}, self.BK)
        self.assertEqual(g["heading"][:2], (120, 220))
        self.assertEqual(g["content"][0], 120)

    def test_box_inset_and_no_heading(self):
        g = comp.frame_geometry((0, 0, 400, 300), {"frame": "box"}, self.BK)
        self.assertEqual(g["content"], (20, 20, 360, 260))
        g = comp.frame_geometry((0, 0, 400, 300), {}, self.BK)
        self.assertEqual(g["content"], (0, 0, 400, 300))      # 枠なし・見出しなしは矩形いっぱい（端がそろう）

    def test_line_without_heading_is_left_bar(self):
        g = comp.frame_geometry((0, 0, 400, 300), {"frame": "line"}, self.BK)
        self.assertEqual(g["left_line"], 3)
        self.assertGreater(g["content"][0], 3)

    def test_emphasis_forces_box(self):
        self.assertEqual(comp.frame_of({"emphasis": True}), "box")


class ValidationTests(unittest.TestCase):
    def v(self, slide, **meta):
        exc, err = validate(one(slide, **meta))
        return exc, err

    def test_valid_composite_passes_silently(self):
        exc, err = self.v(comp_slide([bl(heading="a"), ARCH]))
        self.assertIsNone(exc, err)
        self.assertEqual(err, "")

    def test_blocks_required(self):
        exc, _ = self.v(comp_slide([]))
        self.assertIsNotNone(exc)
        self.assertIn("blocks", str(exc))

    def test_nested_composite_rejected_with_fix(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "composite", "blocks": [bl()]}]))
        self.assertIn("入れ子", str(exc))
        self.assertIn("2 つ目のブロック", str(exc))

    def test_unusable_types_rejected(self):
        for t in ("title", "section", "closing", "statement", "quote", "agenda", "canvas", "two_column", "image_text"):
            exc, _ = self.v(comp_slide([bl(), {"type": t}]))
            self.assertIsNotNone(exc, t)
            self.assertIn("合成スライドのブロックにできません", str(exc), t)
            self.assertIn("→", str(exc), t)

    def test_unknown_type_has_candidates(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "bulletz"}]))
        self.assertIn("もしかして bullets", str(exc))

    def test_full_frame_pattern_rejected(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "pattern", "pattern": "pillars", "slots": {}}]))
        self.assertIn("全面", str(exc))

    def test_block_unknown_key_warned_with_location(self):
        exc, err = self.v(comp_slide([bl(bulets=["x"]), bl()]))
        self.assertIsNone(exc)
        self.assertIn("1枚目（type=composite）の 1 つ目のブロック（bullets）", err)
        self.assertIn("bulets", err)

    def test_native_block_unknown_key(self):
        exc, err = self.v(comp_slide([{"type": "callout", "text": "x", "nte": "y"}, bl()]))
        self.assertIn("1 つ目のブロック（callout）", err)
        self.assertIn("nte", err)

    def test_type_errors_fail_with_location(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "bullets", "bullets": "文字列"}]))
        self.assertIsNotNone(exc)
        self.assertIn("2 つ目のブロック（bullets）", str(exc))
        exc, _ = self.v(comp_slide([bl(frame="boks"), bl()]))
        self.assertIn("frame", str(exc))
        self.assertIn("もしかして", str(exc))
        exc, _ = self.v(comp_slide([bl(emphasis="yes"), bl()]))
        self.assertIn("emphasis", str(exc))

    def test_table_cell_count_error_is_located(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "table", "columns": ["a", "b"], "rows": [["1"]]}]))
        self.assertIn("2 つ目のブロック（table）", str(exc))

    def test_emphasis_twice_warns_and_unsupported_type_warns(self):
        exc, err = self.v(comp_slide([bl(emphasis=True), {"type": "callout", "text": "x", "emphasis": True}]))
        self.assertIsNone(exc)
        self.assertIn("1 枚に 1 つまで", err)
        exc, err = self.v(comp_slide([TABLE, dict(ARCH, emphasis=True)]))
        self.assertIn("emphasis は", err)
        self.assertIn("無視", err)

    def test_empty_cell_warning(self):
        exc, err = self.v(comp_slide([bl(), bl()], columns=[1, 1, 1]))
        self.assertIn("格子に空きがあります", err)

    def test_single_block_warns(self):
        exc, err = self.v(comp_slide([bl()]))
        self.assertIn("1 個だけ", err)

    def test_block_title_lead_ignored_warning(self):
        exc, err = self.v(comp_slide([bl(title="x", lead="y"), bl()]))
        self.assertIn("title はブロックでは描かれません", err)
        self.assertIn("lead はブロックでは描かれません", err)

    def test_block_style_geometry_ignored_warning(self):
        exc, err = self.v(comp_slide([bl(style={"body": {"x": 10, "size": 18}}), bl()]))
        self.assertIn("x / y / w / h は無視", err)

    def test_block_style_unknown_region_warned(self):
        exc, err = self.v(comp_slide([bl(style={"bodi": {"size": 18}}), bl()]))
        self.assertIn("bodi", err)

    def test_text_and_callout_required_fields(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "text"}]))
        self.assertIn("text", str(exc))
        exc, _ = self.v(comp_slide([bl(), {"type": "callout", "note": "補足だけ"}]))
        self.assertIn("callout", str(exc))

    def test_image_path_checked(self):
        exc, _ = self.v(comp_slide([bl(), {"type": "image", "path": "../x.png"}]))
        self.assertIsNotNone(exc)

    def test_kpi_tree_needs_width(self):
        tree = {"type": "kpi_tree", "root": "目標", "branches": [{"title": "a", "kpis": [{"name": "k", "target": "1"}]}]}
        # 3 列の細いブロックには、列を半分まで縮めても入らないので fail（文言に「固定」は出ない）
        exc, _ = self.v(comp_slide([bl(), bl(), tree], columns=[1, 1, 1]))
        self.assertIn("kpi_tree", str(exc))
        self.assertIn("幅", str(exc))
        self.assertIn("縮めても", str(exc))
        # 半幅のブロックは、列と間隔を縮めて収める（s3-A-03）ので fail しない
        exc, _ = self.v(comp_slide([bl(), tree]))
        self.assertIsNone(exc)
        exc, _ = self.v(comp_slide([tree], columns=[1]))
        self.assertIsNone(exc)

    def test_code_annotations_and_legend_page_are_dropped_with_warning(self):
        code = {"type": "code", "code": "x = 1", "annotations": [{"line": 1, "title": "a"}]}
        exc, err = self.v(comp_slide([code, dict(ARCH, legend_page=True)]))
        self.assertIsNone(exc)
        self.assertIn("annotations", err)
        self.assertIn("legend_page", err)

    def test_line_balance_reaches_bullets_blocks(self):
        # ブロックの幅で 1 字だけ次の行に落ちる長さの文を探す（フォントに依らないよう、長さを振って最初に改行が入るものを使う）
        layout = b.load_layout("default")
        base = "二重書き込みで差分を確認し、切り替えの当日は夜間に作業を集中させる"
        for n in range(10, len(base) + 1):
            text = base[:n]
            deck = one(comp_slide([bl(1, bullets=[text], style={"body": {"size": 20}}), bl()]))     # S4: size を書いて「中身が少ないとき大きくする」を止める
            validate(deck)
            out = b.apply_line_balance(deck, layout)
            first = out["slides"][0]["blocks"][0]["bullets"][0]
            if "\n" in first:
                self.assertNotIn("\n", deck["slides"][0]["blocks"][0]["bullets"][0])   # 元のデッキは書き換えない
                return
        self.fail("どの長さでも改行が入りませんでした（ブロックの bullets に line_balance が届いていない）")

    def test_composite_top_level_keys(self):
        exc, err = self.v(comp_slide([bl(), bl()], colums=[1, 1]))
        self.assertIn("colums", err)
        exc, _ = self.v(comp_slide([bl(), bl()], columns="3:2"))
        self.assertIsNotNone(exc)
        exc, _ = self.v(comp_slide([bl(), bl()], arrange="nanika"))
        self.assertIn("未知の配置名", str(exc))

    def test_overflow_warning_names_the_block(self):
        long = "あ" * 900
        exc, err = self.v(comp_slide([bl(), {"type": "text", "text": long}]))
        self.assertIn("1枚目（type=composite）の 2 つ目のブロック（text）", err)
        self.assertIn("収まりません", err)

    def test_delegated_fit_warning_names_the_block(self):
        many = bl(30, heading="多い")
        exc, err = self.v(comp_slide([many, bl()], arrange="main-side"))
        self.assertTrue("1 つ目のブロック（bullets）" in err, err)

    def test_message_rewrite_is_scoped(self):
        with b.block_messages(3, 1, "table"):
            self.assertIn("の 2 つ目のブロック（table）", b._rewrite_msg("3枚目（type=table）: x"))
            self.assertEqual(b._rewrite_msg("4枚目（type=table）: x"), "4枚目（type=table）: x")
        self.assertEqual(b._rewrite_msg("3枚目（type=table）: x"), "3枚目（type=table）: x")


class ResolveTests(unittest.TestCase):
    def resolve(self, slide, **meta):
        deck = one(slide, **meta)
        layout = b.load_layout("default")
        validate(deck)
        return b.resolve_style(layout, deck, deck["slides"][0]), deck

    def test_blocks_fill_body_and_gaps_are_equal(self):
        st, _ = self.resolve(comp_slide([bl(), bl(), bl()], arrange="three"))
        rects = [rb["rect"] for rb in st["_composite"]["blocks"]]
        body = st["_composite"]["body"]
        self.assertAlmostEqual(rects[0][0], body["x"])
        self.assertAlmostEqual(rects[-1][0] + rects[-1][2], body["x"] + body["w"], places=1)
        gaps = [rects[i + 1][0] - (rects[i][0] + rects[i][2]) for i in range(2)]
        self.assertAlmostEqual(gaps[0], gaps[1], places=1)
        self.assertEqual({r[1] for r in rects}, {body["y"]})            # 上端がそろう
        self.assertEqual({round(r[3], 1) for r in rects}, {round(body["h"], 1)})   # 下端もそろう

    def test_body_starts_at_y_no_lead_without_lead_and_after_lead_with_it(self):
        st, _ = self.resolve(comp_slide([bl(), bl()]))
        self.assertEqual(st["_composite"]["body"]["y"], 140)
        st, _ = self.resolve(comp_slide([bl(), bl()], lead="リード"))
        self.assertEqual(st["_composite"]["body"]["y"], 192)

    def test_conclusion_shrinks_body_not_overlapping(self):
        st, _ = self.resolve(comp_slide([bl(), bl()], conclusion="結論"))
        body = st["_composite"]["body"]
        self.assertLessEqual(body["y"] + body["h"], 644 - 40)

    def test_block_region_gets_content_rect(self):
        st, _ = self.resolve(comp_slide([bl(heading="見出し", frame="box"), TABLE], arrange="main-side"))
        rb = st["_composite"]["blocks"][0]
        self.assertEqual(rb["st"]["body"]["x"], rb["geo"]["content"][0])
        self.assertEqual(rb["st"]["body"]["w"], round(rb["geo"]["content"][2], 2))
        self.assertNotIn("title", rb["st"])                              # 見出し骨格の領域は持たない
        self.assertTrue(rb["bs"]["_bare"])

    def test_block_defaults_cap_text_sizes(self):
        st, _ = self.resolve(comp_slide([bl(8), TABLE]))          # S4: 中身が少ないブロックは上限より大きくなる（test_s4_polish）。ここは中身が十分あるときの上限
        self.assertLessEqual(st["_composite"]["blocks"][0]["st"]["body"]["size"], 20)
        self.assertLessEqual(st["_composite"]["blocks"][1]["st"]["table"]["cell_size"], 16)     # 表は少ない行だと 14 → 16 まで大きくなる（S4）

    def test_user_block_style_wins_for_size(self):
        st, _ = self.resolve(comp_slide([bl(style={"body": {"size": 17}}), bl()]))
        self.assertEqual(st["_composite"]["blocks"][0]["st"]["body"]["size"], 17)

    def test_density_applies_to_blocks(self):
        st_talk, _ = self.resolve(comp_slide([bl(9), bl(9)]), density="talk")
        st_std, _ = self.resolve(comp_slide([bl(9), bl(9)]))
        self.assertEqual(st_talk["_composite"]["blocks"][0]["bs"]["density"], "talk")
        self.assertGreater(st_talk["_composite"]["blocks"][0]["st"]["body"]["size"],
                           st_std["_composite"]["blocks"][0]["st"]["body"]["size"])
        self.assertGreater(st_talk["_composite"]["blocks"][0]["st"]["body"]["min_size"],
                           st_std["_composite"]["blocks"][0]["st"]["body"]["min_size"])
        # 合成のブロックの中は上寄せのまま（talk の bullets 単体の valign: middle を持ち込まない。小見出しと本文を離さない）
        self.assertNotEqual(st_talk["_composite"]["blocks"][0]["st"]["body"].get("valign"), "middle")

    def test_read_density_applies_to_blocks(self):
        st_read, _ = self.resolve(comp_slide([bl(9), TABLE]), density="read")
        st_std, _ = self.resolve(comp_slide([bl(9), TABLE]))
        self.assertGreater(st_read["_composite"]["blocks"][0]["st"]["body"]["min_size"],
                           st_std["_composite"]["blocks"][0]["st"]["body"]["min_size"])
        self.assertGreater(st_read["_composite"]["blocks"][1]["st"]["table"]["header_size"],
                           st_std["_composite"]["blocks"][1]["st"]["table"]["header_size"])
        self.assertEqual(st_std["_composite"]["blocks"][0]["st"]["body"]["size"], 20)       # standard は変えない

    def test_matrix_and_status_table_make_room(self):
        mx = {"type": "matrix", "x_axis": {"label": "x", "low": "低", "high": "高"}, "y_axis": {"label": "y", "low": "少", "high": "多"},
              "quadrants": [{"heading": "a", "body": "b"}] * 4}
        st, _ = self.resolve(comp_slide([mx, bl()], arrange="main-side"))
        rb = st["_composite"]["blocks"][0]
        cx, cy, cw, ch = rb["geo"]["content"]
        g = rb["st"]["grid"]
        self.assertGreater(g["x"], cx)                                   # 軸ラベルの余白が矩形の中にある
        self.assertLessEqual(g["y"] + g["h"], cy + ch - 50)
        self.assertEqual(rb["st"]["axis"]["x0"], round(cx, 2))

    def test_native_fit_decides_size_and_flags_overflow(self):
        st, _ = self.resolve(comp_slide([bl(), {"type": "text", "text": "短い"}]))
        self.assertEqual(st["_composite"]["blocks"][1]["fit"]["size"], 28)       # S4: 中身が少ないので上限 20 から大きくする（thin_grow 1.4 倍 = 28）
        st, _ = self.resolve(comp_slide([bl(), {"type": "text", "text": "短い", "style": {"text": {"size": 20}}}]))
        self.assertEqual(st["_composite"]["blocks"][1]["fit"]["size"], 20)       # 利用者が size を書いたときは動かさない
        st, _ = self.resolve(comp_slide([bl(), {"type": "text", "text": "長い文章。" * 300}]))
        f = st["_composite"]["blocks"][1]["fit"]
        self.assertFalse(f["fits"])
        self.assertEqual(f["size"], 14)

    def test_callout_fit(self):
        st, _ = self.resolve(comp_slide([bl(), {"type": "callout", "text": "移行は 2 段階で進める", "note": "補足"}]))
        f = st["_composite"]["blocks"][1]["fit"]
        self.assertTrue(f["fits"])
        self.assertLess(f["note_size"], f["size"])

    def test_emphasis_recolors_bullets_only_where_supported(self):
        st, _ = self.resolve(comp_slide([bl(emphasis=True), TABLE]))
        rb = st["_composite"]["blocks"][0]
        self.assertTrue(rb["emph"])
        self.assertEqual(rb["st"]["body"]["color"], "on_primary")
        st, _ = self.resolve(comp_slide([bl(), dict(TABLE, emphasis=True)]))
        self.assertFalse(st["_composite"]["blocks"][1]["emph"])


class BuildTests(unittest.TestCase):
    """HTML と PPTX を実際にビルドして、ブロックが描かれること・グループ化・data 属性を確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def make(self, slide, name="d", **meta):
        d = write_deck(self.dir, one(slide, **meta), name)
        make_assets(d)
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        return d, r

    def html(self, d):
        return next((d / "build").glob("*.html")).read_text(encoding="utf-8")

    def slide_xml(self, d):
        z = zipfile.ZipFile(next((d / "build").glob("*.pptx")))
        return z.read("ppt/slides/slide1.xml").decode("utf-8")

    def test_html_has_block_attributes_and_single_heading(self):
        d, _ = self.make(comp_slide([ARCH, bl(heading="ポイント", frame="box")], arrange="main-side", lead="リード"), "h1")
        h = self.html(d)
        self.assertIn('data-block="1" data-block-type="architecture"', h)
        self.assertIn('data-block="2" data-block-type="bullets"', h)
        self.assertEqual(h.count('role="heading"'), 1)                    # 見出しは 1 つだけ
        self.assertIn("ポイント", h)

    def test_svg_marker_ids_do_not_collide_between_diagram_blocks(self):
        d, _ = self.make(comp_slide([ARCH, dict(ARCH)], arrange="two"), "h2")
        ids = re.findall(r'<marker id="([^"]+)"', self.html(d))
        self.assertTrue(ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_pptx_groups_per_block(self):
        d, _ = self.make(comp_slide([ARCH, bl(heading="ポイント", frame="box"), TABLE], arrange="three"), "p1")
        x = self.slide_xml(d)
        for k, t in ((1, "architecture"), (2, "bullets")):
            self.assertIn(f'name="ブロック{k}（{t}）"', x)
        # 表（graphicFrame）はグループに入れない（PowerPoint は表のグループ化に対応しない）。名前だけ付けて外に置く
        self.assertIn('name="ブロック3（table）の表"', x)
        self.assertGreaterEqual(x.count("<p:grpSp>"), 2)                   # 表以外のブロックは 1 グループ（図解は内側にもグループを持つ）

    def test_table_is_never_inside_a_group_and_keeps_z_order(self):
        """表 + 枠つき（frame: box）のブロック: 枠（グループ）< 表 < 表より後の図形の順を保ち、表は p:grpSp の外。"""
        from xml.etree import ElementTree as ET
        ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        d, _ = self.make(comp_slide([dict(TABLE, heading="表", frame="box"), bl(frame="box")], arrange="two"), "p2")
        root = ET.fromstring(self.slide_xml(d))
        for grp in root.iter(ns + "grpSp"):
            self.assertEqual(list(grp.iter(ns + "graphicFrame")), [])
        tree = root.find(ns + "cSld").find(ns + "spTree")
        order = []
        for el in tree:
            tag = el.tag.replace(ns, "")
            if tag in ("grpSp", "graphicFrame"):
                names = [n.get("name") for n in el.iter(ns + "cNvPr")]
                order.append((tag, names[0] if tag == "graphicFrame" else " ".join(n or "" for n in names)))
        kinds = [k for k, _ in order]
        i_tbl = kinds.index("graphicFrame")
        self.assertIn("ブロック1の枠", order[i_tbl - 1][1])          # 枠は表より下（先）
        self.assertEqual(kinds[i_tbl - 1], "grpSp")
        from verify_pptx import verify
        self.assertEqual([m for m in verify(next((d / "build").glob("*.pptx"))) if "グループ" in m], [])

    def test_all_block_types_build_html_and_pptx(self):
        blocks = {
            "bullets": bl(), "text": {"type": "text", "text": "段落 1\n段落 2"},
            "callout": {"type": "callout", "text": "強調", "note": "補足"}, "table": TABLE,
            "code": {"type": "code", "code": "print(1)"},
            "cards": {"type": "cards", "cards": [{"heading": "a", "body": "b"}, {"heading": "c", "body": "d"}]},
            "steps": {"type": "steps", "steps": [{"label": "a", "items": ["x"]}, {"label": "b", "items": ["y"]}]},
            "image": {"type": "image", "path": "assets/wide.png", "caption": "写真", "fit": "cover"},
            "kpi": KPI, "chart": CHART, "architecture": ARCH,
            "dataflow": {"type": "dataflow", "stages": ["a", "b"], "nodes": [{"id": "x", "label": "X", "col": 0, "row": 0}, {"id": "y", "label": "Y", "col": 1, "row": 0}],
                         "edges": [{"from": "x", "to": "y"}]},
            "pattern": {"type": "pattern", "pattern": "numbered-columns", "slots": {"items": [{"head": "a", "body": "b"}, {"head": "c", "body": "d"}]}},
            "summary": {"type": "summary", "items": [{"lead": "a", "text": "b"}, {"lead": "c", "text": "d"}]},
        }
        for name, blk in blocks.items():
            with self.subTest(block=name):
                d, r = self.make(comp_slide([dict(blk, heading="見出し"), bl()], arrange="main-side"), f"all-{name}")
                self.assertIn(f'data-block-type="{name}"', self.html(d))
                self.assertIn(f"ブロック1（{name}）", self.slide_xml(d))

    def test_diagram_blocks_build(self):
        seq = {"type": "sequence", "participants": [{"id": "u", "label": "U"}, {"id": "w", "label": "W"}], "messages": [{"from": "u", "to": "w", "label": "go"}]}
        sch = {"type": "schedule", "timeline": {"start": "2026-11", "end": "2027-02", "unit": "month"},
               "rows": [{"label": "設計", "bars": [{"start": "2026-11", "end": "2026-12", "label": "設計"}]}]}
        life = {"type": "lifecycle", "nodes": [{"id": "a", "label": "受付", "row": 0, "col": 0, "kind": "start"}, {"id": "b", "label": "完了", "row": 0, "col": 1}],
                "edges": [{"from": "a", "to": "b"}]}
        mx = {"type": "matrix", "x_axis": {"label": "x", "low": "低", "high": "高"}, "y_axis": {"label": "y", "low": "少", "high": "多"},
              "quadrants": [{"heading": "a", "body": "b"}] * 4}
        st = {"type": "status_table", "columns": ["チーム", "状況", "内容"],
              "rows": [{"label": "PMO", "status": "green", "cells": [["進捗"]]}]}
        sw = {"type": "swimlane", "lanes": [{"name": "A"}, {"name": "B"}],
              "nodes": [{"id": "n1", "lane": 0, "col": 0, "text": "開始"}, {"id": "n2", "lane": 1, "col": 1, "text": "終了"}],
              "edges": [{"from": "n1", "to": "n2"}]}
        for name, blk in (("sequence", seq), ("schedule", sch), ("lifecycle", life), ("matrix", mx), ("status_table", st), ("swimlane", sw)):
            with self.subTest(block=name):
                d, r = self.make(comp_slide([blk, bl()], arrange="main-side"), f"dg-{name}")
                self.assertIn(f'data-block-type="{name}"', self.html(d))

    def test_proposal_blocks_build(self):
        blocks = {
            "reasons": {"type": "reasons", "issues": ["課題"], "strengths": ["強み"]},
            "row_matrix": {"type": "row_matrix", "columns": ["a", "b"], "rows": [{"label": "x", "cells": ["1", "2"]}]},
            "house": {"type": "house", "roof": {"title": "屋根"}, "pillars": [{"title": "柱", "items": ["a"]}]},
            "cycle": {"type": "cycle", "center": "中心", "stages": [{"title": "a"}, {"title": "b"}, {"title": "c"}]},
        }
        for name, blk in blocks.items():
            with self.subTest(block=name):
                d, r = self.make(comp_slide([blk, bl()], arrange="main-side"), f"pr-{name}")
                self.assertIn(f'data-block-type="{name}"', self.html(d))

    def test_conclusion_and_source_drawn_once_below_blocks(self):
        d, _ = self.make(comp_slide([bl(), bl()], conclusion="結論の一文", source="出典: テスト"), "cs")
        h = self.html(d)
        self.assertEqual(h.count("結論の一文"), 1)
        self.assertEqual(h.count("出典: テスト"), 1)

    def test_all_shapes_and_themes_build(self):
        slide = comp_slide([ARCH, bl(heading="a", frame="box"), TABLE, {"type": "callout", "text": "x", "emphasis": True}], arrange="2x2")
        for shape in ("classic", "sharp", "soft", "editorial"):
            for theme in ("default", "acn-slide-master"):
                with self.subTest(shape=shape, theme=theme):
                    self.make(slide, f"sh-{shape}-{theme}", shape=shape, theme=theme)

    def test_pptx_text_matches_html_for_native_blocks(self):
        d, _ = self.make(comp_slide([{"type": "text", "heading": "見出し", "text": "本文の段落です"},
                                     {"type": "callout", "text": "強調の一文", "note": "補足の文"}]), "nat")
        x = self.slide_xml(d)
        h = self.html(d)
        for t in ("見出し", "本文の段落です", "強調の一文", "補足の文"):
            self.assertIn(t, x)
            self.assertIn(t, h)

    def test_existing_slides_unchanged_by_composite_hooks(self):
        # 合成を使わないスライドは、ブロック用のキー（_composite / _bare）を持たない
        deck = one({"type": "bullets", "title": "t", "bullets": ["a"]})
        st = b.resolve_style(b.load_layout("default"), deck, deck["slides"][0])
        self.assertNotIn("_composite", st)


class QaToolTests(unittest.TestCase):
    def test_lint_counts_block_text_and_volume_per_block(self):
        deck = one(comp_slide([bl(8, heading="x"), {"type": "text", "text": "ではなく、**強調**です"}]))
        res = lint.lint(deck)
        self.assertTrue(any("blocks[0] bullets 8項目" in w for w in res["warnings"]), res["warnings"])
        self.assertTrue(any("Markdown記法残留" in e and "blocks[1]" in e for e in res["errors"]), res["errors"])

    def test_lint_todo_marker_inside_block(self):
        deck = one(comp_slide([bl(), {"type": "text", "text": "売上は 10 億円【要確認: 出典】"}]))
        res = lint.lint(deck)
        self.assertEqual(len(res["todos"]), 1)
        self.assertIn("blocks[1].text", res["todos"][0]["path"])

    def test_lint_rhythm_uses_block_signature(self):
        same = [comp_slide([bl(), TABLE]) for _ in range(3)]
        diff = [comp_slide([bl(), TABLE]), comp_slide([bl(), ARCH]), comp_slide([bl(), CHART])]
        self.assertTrue(lint.check_rhythm(same))
        self.assertFalse(lint.check_rhythm(diff))

    def test_lint_relation_accepts_block_types(self):
        s = comp_slide([ARCH, bl()], relation="flow")
        self.assertEqual(lint.check_relation("slide-01", s), [])
        s = comp_slide([TABLE, bl()], relation="cycle")
        self.assertTrue(lint.check_relation("slide-01", s))

    def test_lint_volume_limit_is_larger_for_composite(self):
        text = "あ" * 600
        out = lint.check_volume("slide-01", comp_slide([{"type": "text", "text": text}, bl()]), "standard")
        self.assertFalse(any("表示文字数" in m for m in out))
        out = lint.check_volume("slide-01", comp_slide([{"type": "text", "text": "あ" * 800}, bl()]), "standard")
        self.assertTrue(any("表示文字数" in m for m in out))

    def test_metrics_counts_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, one(comp_slide([bl(4), TABLE])))
            m = dm.metrics(d)
        self.assertEqual(m["table_n"], 1)
        self.assertEqual(m["bullets_per_slide"], 4)
        self.assertEqual(m["slides"], 1)

    def test_check_diagram_looks_into_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, one(comp_slide([ARCH, bl()])))
            r = subprocess.run([PY, str(TOOLS / "check_diagram.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
        self.assertIn("図解スライド 1 枚", r.stdout + r.stderr)


class ReviewFixTests(unittest.TestCase):
    """独立レビューの指摘（s2c-C-01〜11 / A-01〜09）の回帰テスト。"""

    def plan(self, blocks, **kw):
        return comp.plan_grid(blocks, **kw)

    # C-01 / A-01: col / row だけを範囲外にしても、止まらずに problems で終わる
    def test_col_only_out_of_range_is_a_problem_not_a_hang(self):
        for cols, col in ((None, 5), ([1, 1], 2), ([1, 1, 1], 3)):
            p = self.plan([{"type": "bullets"}, {"type": "bullets", "col": col}], columns=cols)
            self.assertTrue(p["problems"], (cols, col))
            self.assertIn("列の数", p["problems"][0])
            self.assertIn("2 つ目のブロック", p["problems"][0])

    def test_col_only_with_span_over_edge(self):
        p = self.plan([{"type": "bullets", "col": 2, "col_span": 2}], columns=[1, 1, 1])
        self.assertTrue(p["problems"])
        p = self.plan([{"type": "bullets", "col": 1}, {"type": "bullets"}], columns=[1, 1])
        self.assertEqual(p["problems"], [])

    def test_row_only_is_bounded(self):
        p = self.plan([{"type": "bullets"}, {"type": "bullets", "row": 40}])
        self.assertTrue(p["problems"])
        self.assertIn("大きすぎ", p["problems"][0])
        p = self.plan([{"type": "bullets", "row": 3}], columns=[1], rows=[1, 1])
        self.assertTrue(p["problems"])
        self.assertIn("行の数", p["problems"][0])

    # C-02: 巨大な row / row_span でメモリを使い切らない
    def test_huge_row_and_row_span_fail_fast(self):
        for kw in ({"row_span": 10 ** 9}, {"row": 10 ** 9}, {"row": 10 ** 9, "col": 0}, {"row_span": comp.MAX_AUTO_ROWS + 1}):
            p = self.plan([dict({"type": "bullets"}, **kw), {"type": "bullets"}])
            self.assertTrue(p["problems"], kw)
            self.assertLessEqual(len(p["rows"]), comp.MAX_AUTO_ROWS, kw)
        p = self.plan([{"type": "bullets", "row_span": comp.MAX_AUTO_ROWS}, {"type": "bullets"}])
        self.assertEqual(p["problems"], [])

    def test_plan_grid_always_terminates_on_random_inputs(self):
        import random
        rnd = random.Random(7)
        for _ in range(3000):
            blocks = []
            for _k in range(rnd.randint(1, 6)):
                b_ = {"type": "bullets"}
                for key, hi in (("col", 6), ("row", 15), ("col_span", 4), ("row_span", 15)):
                    if rnd.random() < 0.3:
                        b_[key] = rnd.randint(1 if key.endswith("span") else 0, hi)
                blocks.append(b_)
            cols = rnd.choice([None, [1, 1], [1, 1, 1], [3, 2]])
            rows = rnd.choice([None, [1], [1, 1]])
            p = self.plan(blocks, columns=cols, rows=rows)
            self.assertLessEqual(len(p["rows"]), max(comp.MAX_AUTO_ROWS, len(rows or [])))
            if not p["problems"]:
                seen = set()
                for c in p["cells"]:
                    a = {(c[0] + i, c[1] + j) for i in range(c[2]) for j in range(c[3])}
                    self.assertFalse(a & seen)
                    seen |= a
                    self.assertLessEqual(c[0] + c[2], len(p["columns"]))
                    self.assertLessEqual(c[1] + c[3], len(p["rows"]))

    def test_build_with_col_only_out_of_range_fails_instead_of_hanging(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, one(comp_slide([bl(), bl(col=5)])))
            r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 1)
        self.assertIn("列の数", r.stderr)

    # C-09: NaN / Infinity / 巨大な比率
    def test_non_finite_and_huge_ratios_are_problems(self):
        for bad in (float("nan"), float("inf"), 1e308, 1e7):
            p = self.plan([{"type": "bullets"}], columns=[bad, 1])
            self.assertTrue(p["problems"], bad)
            self.assertIn("columns", p["problems"][0])
        self.assertEqual(self.plan([{"type": "bullets"}] * 2, columns=[3, 2], rows=[1])["problems"], [])

    # C-06: arrange があるときの直し方
    def test_arrange_overflow_message_points_to_arrange_or_rows(self):
        p = self.plan([{"type": "bullets"}] * 3, arrange="main-side")
        self.assertIn("arrange を外す", p["problems"][0])
        self.assertIn("rows", p["problems"][0])
        self.assertNotIn("省略して自動", p["problems"][0])
        p = self.plan([{"type": "bullets"}] * 3, columns=[1, 1], rows=[1])
        self.assertIn("rows を増やす", p["problems"][0])

    # A-07: 5 個・7 個の既定は最後のブロックを広げて空きを作らない
    def test_default_five_and_seven_blocks_leave_no_gap(self):
        for n in (5, 7, 8):
            p = self.plan([{"type": "bullets"}] * n)
            self.assertEqual((p["problems"], p["empty"]), ([], []), n)
        p = self.plan([{"type": "bullets"}] * 5)
        self.assertEqual(p["cells"][-1], (1, 1, 2, 1))
        # 利用者が列・配置・位置を書いたときは動かさない
        self.assertEqual(self.plan([{"type": "bullets"}] * 2, columns=[1, 1, 1])["empty"], [(2, 0)])
        p = self.plan([{"type": "bullets"}] * 5 + [], arrange="three", rows=[1, 1])
        self.assertTrue(p["empty"] or p["problems"])
        p = self.plan([{"type": "bullets"}] * 4 + [{"type": "bullets", "col_span": 1}])
        self.assertEqual(p["cells"][-1][2], 1)

    # C-05: style.blocks の型・範囲
    def test_style_blocks_values_are_validated(self):
        def run(sty):
            return validate(one(comp_slide([bl(), bl()], style=sty)))
        exc, _ = run({"blocks": {"bullets": {"body": {"size": "big"}}}})
        self.assertIn("style.blocks.bullets.body.size", str(exc))
        self.assertIn("数値", str(exc))
        exc, _ = run({"blocks": {"bullets": {"body": {"size": -4}}}})
        self.assertIn("style.blocks.bullets.body.size", str(exc))
        exc, _ = run({"blocks": {"bullets": {"body": "x"}}})
        self.assertIn("style.blocks.bullets.body", str(exc))
        exc, _ = run({"blocks": "x"})
        self.assertIn("style.blocks", str(exc))
        exc, err = run({"blocks": {"bulet": {"body": {"size": 18}}}})
        self.assertIsNone(exc)
        self.assertIn("もしかして \"bullets\"", err)
        exc, err = run({"blocks": {"bullets": {"bdy": {"size": 18}}}})
        self.assertIsNone(exc)
        self.assertIn("領域名ではありません", err)
        exc, err = run({"blocks": {"bullets": {"body": {"size": 18}}, "table": {"table": {"row_h": 50}}}})
        self.assertIsNone(exc, err)
        self.assertEqual(err, "")

    def test_layout_overrides_composite_blocks_are_validated(self):
        exc, _ = validate(one(comp_slide([bl(), bl()]), layout_overrides={"composite": {"blocks": {"bullets": {"body": {"size": "x"}}}}}))
        self.assertIn("meta.layout_overrides.composite.blocks.bullets.body.size", str(exc))

    # C-11: 色・画像 path の場所
    def test_block_color_error_names_the_block(self):
        exc, _ = validate(one(comp_slide([bl(style={"body": {"color": "nocolor"}}), bl()])))
        self.assertIn("1 つ目のブロック（bullets）", str(exc))
        exc, _ = validate(one(comp_slide([{"type": "text", "text": "x", "style": {"text": {"color": "nocolor"}}}, bl()])))
        self.assertIn("1 つ目のブロック（text）", str(exc))

    def test_image_path_must_be_string(self):
        for bad in (["a"], 5):
            exc, _ = validate(one(comp_slide([{"type": "image", "path": bad}, bl()])))
            self.assertIn("path は文字列", str(exc))
            self.assertIn("1 つ目のブロック（image）", str(exc))

    # C-08: emphasis を無視するブロックに強調の箱を付けない
    def test_ignored_emphasis_does_not_draw_a_box(self):
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([dict(TABLE, emphasis=True), bl()]))
        self.assertEqual(st["_composite"]["blocks"][0]["geo"]["frame"], "none")
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([dict(TABLE, emphasis=True, frame="line"), bl()]))
        self.assertEqual(st["_composite"]["blocks"][0]["geo"]["frame"], "line")
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([bl(emphasis=True), bl()]))
        self.assertEqual(st["_composite"]["blocks"][0]["geo"]["frame"], "box")

    # C-07: pattern ブロックの縮小警告
    def test_pattern_block_shrink_warning_is_block_specific(self):
        import pattern_engine as pat_e
        pat = {"design": {"w": 1136, "h": 360}}
        pt = {"name": "wide-test", "frame": "body", "size": [1136, 400]}      # 狭い構図も幅の下限も持たない型（同梱の型はすべて狭い構図を持つ）
        w, m = pat_e.body_rect_problems({}, pt, {"w": 556, "h": 459}, in_block=True)
        self.assertEqual(w, [])
        sw, sh = pat_e.design_size(pt)
        f, warns = pat_e.body_rect_problems({}, pt, {"w": sw * 0.6, "h": sh * 0.6}, in_block=True)
        self.assertTrue(warns and "ブロックを広げる" in warns[0] and "style.body" not in warns[0])
        f, warns = pat_e.body_rect_problems({}, pt, {"w": sw * 0.6, "h": sh * 0.6})
        self.assertEqual(warns, [])                                           # 単独の pattern スライドは従来どおり 0.5 まで無警告
        f, warns = pat_e.body_rect_problems({}, pt, {"w": sw * 0.4, "h": sh * 0.4})
        self.assertTrue(warns and "style.body" in warns[0])

    # C-10: check_diagram は不正な composite でトレースバックを出さない
    def test_check_diagram_survives_malformed_blocks(self):
        for blocks in ([None, bl()], ["x", bl()], [[1], bl()], [{"type": ["bullets"]}, bl()]):
            with tempfile.TemporaryDirectory() as tmp:
                d = write_deck(tmp, one(comp_slide(blocks)))
                r = subprocess.run([PY, str(TOOLS / "check_diagram.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
            self.assertNotIn("Traceback", r.stderr, blocks)

    # A-08: 見出し・x/y/w/h
    def test_empty_heading_and_xywh_warn(self):
        exc, err = validate(one(comp_slide([bl(heading="  "), bl(x=10, w=300)])))
        self.assertIsNone(exc, err)
        self.assertIn("heading が空文字", err)
        self.assertIn("x は書けません", err)
        self.assertNotIn("未知のキー", err)
        exc, _ = validate(one(comp_slide([bl(heading=True), bl()])))
        self.assertIn("heading は文字列", str(exc))

    # A-04: 細い steps
    def test_narrow_steps_block_warns(self):
        steps = {"type": "steps", "steps": [{"label": "a", "items": ["x"]}, {"label": "b", "items": ["y"]}, {"label": "c", "items": ["z"]}]}
        exc, err = validate(one(comp_slide([bl(), steps], arrange="main-side")))
        self.assertIn("steps の 1 段の幅", err)
        self.assertIn("2 つ目のブロック（steps）", err)
        exc, err = validate(one(comp_slide([steps, bl()], arrange="main-side")))
        self.assertNotIn("steps の 1 段の幅", err)

    # A-02: 箱の中身が少ないときの警告 / A-03: 表の行を広げる
    def test_sparse_box_warns_and_table_rows_stretch(self):
        exc, err = validate(one(comp_slide([bl(2, heading="少ない", frame="box"), bl(8)], arrange="two")))
        self.assertNotIn("枠の中身が少なく", err)       # S4: 文字を大きくして縦中央に置くので、自動で整った分は警告しない
        exc, err = validate(one(comp_slide([bl(2, heading="少ない", frame="box"), bl(8)], arrange="two", autofit=False)))
        self.assertIn("枠の中身が少なく", err)          # 自動フィットを切ったときは整えないので警告する
        exc, err = validate(one(comp_slide([bl(8, heading="多い", frame="box"), bl(8)], arrange="two")))
        self.assertNotIn("枠の中身が少なく", err)
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([TABLE, bl()], arrange="two"))
        rh = st["_composite"]["blocks"][0]["st"]["table"]["row_h"]
        self.assertGreater(rh, 46)
        self.assertLessEqual(rh, 64)
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([dict(TABLE, style={"table": {"row_h": 40}}), bl()], arrange="two"))
        self.assertEqual(st["_composite"]["blocks"][0]["st"]["table"]["row_h"], 40)           # 利用者の値は動かさない
        st, _ = ResolveTests.resolve(ResolveTests(), comp_slide([TABLE, bl()], arrange="two",
                                                                 style={"blocks": {"table": {"table": {"row_h": 40}}}}))
        self.assertEqual(st["_composite"]["blocks"][0]["st"]["table"]["row_h"], 40)

    # A-06: callout の最終行に短い切れ端を残さない
    def test_callout_text_is_line_balanced(self):
        slide = comp_slide([{"type": "table", "columns": ["a"], "rows": [["1"]]},
                            {"type": "callout", "text": "上位 2 部署で、全体の削減の 6 割", "note": "補足"}], arrange="main-side")
        deck = one(slide)
        validate(deck)
        out = b.apply_line_balance(deck, b.load_layout("default"))
        text = out["slides"][0]["blocks"][1]["text"]
        tail = text.split("\n")[-1]
        self.assertGreaterEqual(len(tail.strip()), 4, text)


class EditorialTokenTests(unittest.TestCase):
    def test_title_floor_is_a_token_not_an_enumeration(self):
        ed = json.loads((TOOLS.parent / "templates" / "shapes" / "editorial.json").read_text(encoding="utf-8"))
        listed = [t for t, v in ed["layout"]["types"].items() if "title" in v and "min_size" in v["title"]]
        self.assertEqual(listed, [])
        layout = b.load_layout("default")
        self.assertEqual(layout["tokens"]["type"]["h1_min"], 28)
        # classic と同じ下限（36 × 0.78 ≒ 28）なので、見た目は変わらない
        self.assertEqual(round(36 * 0.78), 28)

    def test_composite_title_floor_in_editorial(self):
        deck = one(comp_slide([bl(), bl()]), shape="editorial")
        p = write_deck(tempfile.mkdtemp(), deck)
        _d, _t, layout = b.load_deck(p)
        self.assertEqual(layout["types"]["composite"]["title"]["min_size"], 28)
        self.assertEqual(layout["types"]["composite"]["title"]["size"], 40)


if __name__ == "__main__":
    unittest.main()

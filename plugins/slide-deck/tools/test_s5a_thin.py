#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5a 単独スライドの空きと、合成の図解ブロックの拡大: agenda・steps・cards・status_table・cycle・schedule（単独）、
合成ブロックの図解（architecture / dataflow / lifecycle / sequence / org / kpi_tree）の同じ倍率の拡大、status_table の凡例（PPTX）。

実行: python3 -m unittest plugins/slide-deck/tools/test_s5a_thin.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import diagram_scale as dscale  # noqa: E402
from test_composite import ARCH, bl, comp_slide  # noqa: E402
from test_validation import one, validate  # noqa: E402

LAYOUT = b.load_layout("default")


def resolve(slide, **meta):
    deck = one(slide, **meta)
    b._WARNED.clear()
    validate(deck)
    return b.resolve_style(LAYOUT, deck, deck["slides"][0]), deck


def agenda(n, desc=True, **kw):
    items = [{"text": f"項目{i + 1}の見出し", **({"desc": f"項目{i + 1}の補足の説明文"} if desc else {})} for i in range(n)]
    return dict({"type": "agenda", "title": "目次", "items": items}, **kw)


class AgendaTest(unittest.TestCase):
    def test_few_items_grow_and_use_the_body(self):
        st, _ = resolve(agenda(4))
        body = st["body"]
        self.assertGreaterEqual(body["row_h"], 84)
        self.assertGreaterEqual(body["text_size"], 26)
        self.assertGreater(body["desc_size"], 14)
        total = 4 * (body["row_h"] + body["gap"])
        self.assertLessEqual(total, 452)                    # 描画側の「1 列に入る行数」（h // 行ピッチ）が 4 のまま = 1 列
        self.assertGreater(body["y"], 196)                  # 縦中央寄りに置く

    def test_density_changes_the_ceiling(self):
        talk, _ = resolve(agenda(3), density="talk")
        read, _ = resolve(agenda(3), density="read")
        self.assertEqual(talk["body"]["text_size"], 30)
        self.assertLessEqual(read["body"]["text_size"], 24)

    def test_many_items_are_left_alone(self):
        for n, desc in ((6, False), (5, True), (8, True)):
            st, _ = resolve(agenda(n, desc))
            self.assertEqual(st["body"]["text_size"], 20, (n, desc))
            self.assertEqual(st["body"]["y"], 196)

    def test_pagination_is_not_changed(self):
        for n in range(2, 9):
            for desc in (True, False):
                deck = one(agenda(n, desc))
                b._WARNED.clear()
                validate(deck)
                out = b.expand_slides(deck, LAYOUT)["slides"]
                self.assertEqual(len(out), 1, (n, desc))

    def test_explicit_style_and_autofit_off_win(self):
        st, _ = resolve(agenda(4, style={"body": {"text_size": 22}}))
        self.assertEqual(st["body"]["text_size"], 22)
        self.assertEqual(st["body"]["y"], 196)
        st, _ = resolve(agenda(4, autofit=False))
        self.assertEqual(st["body"]["text_size"], 20)
        st, _ = resolve(agenda(4), layout_overrides={"agenda": {"body": {"thin_grow": 1}}})
        self.assertEqual(st["body"]["text_size"], 20)

    def test_no_worse_wrap(self):
        long = dict(agenda(3))
        long["items"] = [{"text": "現状と課題と、その前提になる考え方を整理する長い見出しの項目", "desc": "補足"}] * 3
        st, _ = resolve(long)
        # 見出しが 1 行のまま（行数が増える大きさには上げない）
        w = 1088 - st["body"]["num_w"]
        self.assertEqual(autofit.wrap_profile(long["items"][0]["text"], st["body"]["text_size"], w, None, True)[0],
                         autofit.wrap_profile(long["items"][0]["text"], 20, 1088 - 52, None, True)[0])


def steps(n, k, **kw):
    return dict({"type": "steps", "title": "進め方", "steps": [{"label": f"段階{i + 1}", "items": [f"項目{j + 1}を行う" for j in range(k)]}
                                                                for i in range(n)]}, **kw)


class StepsSingleTest(unittest.TestCase):
    def test_short_steps_stretch_to_a_middle_height_and_center_items(self):
        st, _ = resolve(steps(4, 4))
        body = st["body"]
        self.assertEqual(body.get("valign"), "middle")
        self.assertGreaterEqual(body["min_h"], 0.7 * 440)
        self.assertLessEqual(body["min_h"], 0.85 * 440)
        card_h = b.steps_card_height(body, steps(4, 4)["steps"], (1136 - 60) / 4)
        self.assertGreaterEqual(card_h, 0.7 * 440)

    def test_few_items_grow_the_text(self):
        st, _ = resolve(steps(2, 2))
        self.assertGreater(st["body"]["item_size"], 15)
        self.assertLessEqual(st["body"]["item_size"], 24)
        self.assertLessEqual(st["body"]["label_size"], 28)

    def test_full_cards_are_left_alone(self):
        st, _ = resolve(steps(3, 9))
        self.assertNotEqual(st["body"].get("valign"), "middle")
        self.assertNotIn("min_h", st["body"])

    def test_explicit_values_and_autofit_off_win(self):
        st, _ = resolve(steps(4, 3, style={"body": {"min_h": 200}}))
        self.assertEqual(st["body"]["min_h"], 200)
        self.assertNotEqual(st["body"].get("valign"), "middle")
        st, _ = resolve(steps(4, 3, autofit=False))
        self.assertNotIn("min_h", st["body"])
        st, _ = resolve(steps(4, 3, style={"body": {"fit": "fill"}}))
        self.assertNotEqual(st["body"].get("valign"), "middle")

    def test_no_items_is_left_alone(self):
        st, _ = resolve(steps(4, 0))
        self.assertNotIn("min_h", st["body"])


def cards(n, body="見積もりの作成に 3 日かかる", **kw):
    return dict({"type": "cards", "title": "課題", "cards": [{"heading": f"課題{i + 1}の見出し", "body": body} for i in range(n)]}, **kw)


class CardsSingleTest(unittest.TestCase):
    def test_two_cards_use_two_columns(self):
        st, _ = resolve(cards(2))
        self.assertEqual(st["grid"]["cols"], 2)

    def test_four_cards_do_not_leave_a_lone_card(self):
        st, _ = resolve(cards(4))
        self.assertIn(st["grid"]["cols"], (2, 4))

    def test_explicit_columns_are_kept(self):
        st, _ = resolve(cards(2, columns=3))
        self.assertEqual(st["grid"].get("cols", 3), 3)

    def test_short_cards_get_a_taller_box(self):
        st, _ = resolve(cards(3))
        g = st["grid"]
        self.assertGreaterEqual(g["h"], 0.5 * 440)
        self.assertGreater(g["heading_size"], 19)

    def test_growth_does_not_break_a_word_or_leave_a_short_tail(self):
        for n in (2, 3, 4):
            c = cards(n)
            st, _ = resolve(c)
            g = st["grid"]
            cols = g.get("cols", 3)
            w = (1136 - (cols - 1) * g.get("gap", 16)) / cols - 2 * g["pad"]
            for card in c["cards"]:
                p0 = autofit.card_wrap_profile(card["heading"], 19, w, autofit.ja_text.heading_fonts(), True)
                p1 = autofit.card_wrap_profile(card["heading"], g["heading_size"], w, autofit.ja_text.heading_fonts(), True)
                self.assertTrue(autofit.wrap_not_broken(p0, p1), (n, p0, p1))

    def test_emphasis_card_heading_is_not_broken(self):
        c = cards(3)
        c["cards"][0]["emphasis"] = True
        st, _ = resolve(c, density="talk")
        g = st["grid"]
        w = (1136 - 2 * g["gap"]) / 3 - 2 * g["pad"]
        size = round(g["heading_size"] * g.get("emph_scale", 1))
        prof = autofit.card_wrap_profile(c["cards"][0]["heading"], size, w, autofit.ja_text.heading_fonts(), True)
        self.assertEqual(prof[2], 0)          # 語の途中の折れが無い

    def test_autofit_off_keeps_the_old_look(self):
        st, _ = resolve(cards(2, autofit=False))
        self.assertEqual(st["grid"]["heading_size"], 19)


def status_table(rows=3, **kw):
    return dict({"type": "status_table", "title": "進捗", "columns": ["項目", "状況", "実績", "計画"],
                 "rows": [{"label": f"行{i + 1}", "status": "green", "cells": [["完了した作業"], ["次の作業"]]} for i in range(rows)]}, **kw)


class StatusTableTest(unittest.TestCase):
    def test_few_rows_grow_the_cell_text(self):
        st, _ = resolve(status_table(3))
        self.assertGreater(st["table"]["cell_size"], 13)
        self.assertLessEqual(st["table"]["cell_size"], 16)

    def test_full_tables_stay(self):
        slide = status_table(8)
        for r in slide["rows"]:
            r["cells"] = [["完了した作業", "確認した内容", "残りの作業"], ["次の作業", "予定の内容", "担当の確認"]]
        st, _ = resolve(slide)
        self.assertLessEqual(st["table"]["cell_size"], 13)

    def test_explicit_cell_size_wins(self):
        st, _ = resolve(status_table(3, style={"table": {"cell_size": 13}}))
        self.assertEqual(st["table"]["cell_size"], 13)
        st, _ = resolve(status_table(3, autofit=False))
        self.assertEqual(st["table"]["cell_size"], 13)


class CycleTest(unittest.TestCase):
    SLIDE = {"type": "cycle", "title": "改善", "center": "毎週",
             "stages": [{"title": t, "items": ["分類別の件数", "AI の解決率", "人が答えた件数"]} for t in ("計測", "分析", "更新", "反映")]}

    def test_roomy_panels_grow_the_text(self):
        st, _ = resolve(dict(self.SLIDE))
        self.assertGreaterEqual(st["body"]["sizes"][0], 16)
        self.assertLessEqual(st["body"]["sizes"][0], 20)

    def test_explicit_sizes_win(self):
        st, _ = resolve(dict(self.SLIDE, style={"body": {"sizes": [14, 13]}}))
        self.assertEqual(st["body"]["sizes"], [14, 13])
        st, _ = resolve(dict(self.SLIDE, autofit=False))
        self.assertNotIn("sizes", st["body"])


class ScheduleTest(unittest.TestCase):
    def slide(self, n, **kw):
        rows = [{"label": f"作業{i + 1}", "bars": [{"start": "2026-11", "end": "2026-12", "label": "実施"}]} for i in range(n)]
        return dict({"type": "schedule", "title": "計画", "timeline": {"start": "2026-11", "end": "2027-03", "unit": "month"}, "rows": rows}, **kw)

    def test_five_rows_fill_more_of_the_body(self):
        st, _ = resolve(self.slide(5))
        self.assertGreater(st["chart"]["max_row_h"], 64)
        self.assertLessEqual(st["chart"]["max_row_h"], 64 * 1.3 + 1)

    def test_many_rows_stay(self):
        st, _ = resolve(self.slide(8))
        self.assertEqual(st["chart"]["max_row_h"], 64)

    def test_explicit_chart_key_stops(self):
        st, _ = resolve(self.slide(5, style={"chart": {"label_size": 15}}))
        self.assertEqual(st["chart"]["max_row_h"], 64)
        st, _ = resolve(self.slide(5, autofit=False))
        self.assertEqual(st["chart"]["max_row_h"], 64)

    def test_fill_trigger_zero_stops_the_mid_growth(self):
        st, _ = resolve(self.slide(5), layout_overrides={"schedule": {"chart": {"fill_trigger": 0}}})
        self.assertEqual(st["chart"]["max_row_h"], 64)


ARCH_BIG = {"type": "architecture", "heading": "構成", "legend": False,
            "nodes": [{"id": "a", "type": "frontend", "label": "受付チャット", "sublabel": "社員が質問する", "row": 0, "col": 0},
                      {"id": "b", "type": "backend", "label": "AI 回答", "sublabel": "確信度を計算", "row": 0, "col": 1},
                      {"id": "c", "type": "database", "label": "手順書", "sublabel": "220 件", "row": 0, "col": 2}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c", "arrow": "both", "label": "検索", "label_back": "根拠"}]}


def block_state(block, arrange="main-side", **meta):
    slide = comp_slide([block, bl(3, heading="点", frame="line")], arrange=arrange)
    st, deck = resolve(slide, **meta)
    return st["_composite"]["blocks"][0]


class DiagramBlockTest(unittest.TestCase):
    def test_architecture_block_is_scaled(self):
        rb = block_state(dict(ARCH_BIG))
        d = rb["st"]["diagram"]
        self.assertGreater(d.get("scale_k", 1), 1.1)
        self.assertLessEqual(d["scale_k"], 1.5)

    def test_scaled_text_stays_within_the_cap(self):
        rb = block_state(dict(ARCH_BIG))
        d = rb["st"]["diagram"]
        self.assertLessEqual(d["node_size"] * d["scale_k"], 22.5)

    def test_scaled_geometry_stays_inside_the_block(self):
        rb = block_state(dict(ARCH_BIG))
        d = rb["st"]["diagram"]
        geo = dscale.layout_grid(rb["bs"], "architecture", d, [])
        for nb in geo["nodes"].values():
            self.assertGreaterEqual(nb["x"], d["x"] - 0.5)
            self.assertLessEqual(nb["x"] + nb["w"], d["x"] + d["w"] + 0.5)
            self.assertGreaterEqual(nb["y"], d["y"] - 0.5)
            self.assertLessEqual(nb["y"] + nb["h"], d["y"] + d["h"] + 0.5)
        ds = dscale.scaled_style(d)
        self.assertAlmostEqual(ds["node_size"], d["node_size"] * d["scale_k"])
        self.assertEqual(ds["w"], d["w"])

    def test_scaling_matches_a_natural_layout_times_k(self):
        rb = block_state(dict(ARCH_BIG))
        d = rb["st"]["diagram"]
        k = d["scale_k"]
        geo = dscale.layout_grid(rb["bs"], "architecture", d, [])
        nat = dict(d)
        nat.update({"scale_k": 1, "x": 0.0, "y": 0.0, "w": d["w"] / k, "h": d["h"] / k})
        g0 = dscale.de.layout_grid_diagram(rb["bs"], "architecture", nat, [])
        a, c = geo["nodes"]["a"], g0["nodes"]["a"]
        self.assertAlmostEqual(a["w"], c["w"] * k, places=3)
        self.assertAlmostEqual(a["x"], d["x"] + c["x"] * k, places=3)
        self.assertAlmostEqual(geo["edges"][0]["points"][0][0], d["x"] + g0["edges"][0]["points"][0][0] * k, places=3)

    def test_explicit_scale_stops_and_autofit_off(self):
        blk = dict(ARCH_BIG, style={"diagram": {"scale_k": 1}})
        self.assertEqual(dscale.scale_of(block_state(blk)["st"]["diagram"]), 1.0)
        rb = block_state(dict(ARCH_BIG), autofit=False)
        self.assertEqual(dscale.scale_of(rb["st"]["diagram"]), 1.0)
        rb = block_state(dict(ARCH_BIG), layout_overrides={"composite": {"blocks": {"architecture": {"diagram": {"thin_grow": 1}}}}})
        self.assertEqual(dscale.scale_of(rb["st"]["diagram"]), 1.0)

    def test_single_diagram_slide_is_not_scaled(self):
        slide = dict(ARCH_BIG, title="単独")
        slide.pop("heading")
        st, _ = resolve(slide)
        self.assertEqual(dscale.scale_of(st["diagram"]), 1.0)

    def test_text_does_not_wrap_more(self):
        rb = block_state(dict(ARCH_BIG))
        d = rb["st"]["diagram"]
        geo = dscale.layout_grid(rb["bs"], "architecture", d, [])
        nat = dict(d)
        nat["scale_k"] = 1
        g1 = dscale.de.layout_grid_diagram(rb["bs"], "architecture", nat, [])
        for nid, fit in geo["text"].items():
            self.assertLessEqual(len(fit["lines"]), len(g1["text"][nid]["lines"]))

    def test_sequence_and_dataflow_blocks_do_not_fail(self):
        seq = {"type": "sequence", "heading": "流れ", "participants": [{"id": "u", "label": "利用者"}, {"id": "a", "label": "AI"}],
               "messages": [{"from": "u", "to": "a", "label": "質問"}, {"from": "a", "to": "u", "label": "回答", "style": "return"}]}
        rb = block_state(seq)
        self.assertGreaterEqual(dscale.scale_of(rb["st"]["diagram"]), 1.0)
        flow = {"type": "dataflow", "heading": "流れ", "stages": ["入力", "加工"],
                "nodes": [{"id": "a", "type": "frontend", "label": "受付", "col": 0, "row": 0}, {"id": "b", "type": "backend", "label": "加工", "col": 1, "row": 0}],
                "edges": [{"from": "a", "to": "b"}]}
        rb = block_state(flow, arrange="top-bottom")
        self.assertGreaterEqual(dscale.scale_of(rb["st"]["diagram"]), 1.0)

    def test_org_block_is_scaled_and_other_scale_unit(self):
        org = {"type": "org", "heading": "体制",
               "left": {"title": "部門", "nodes": [{"id": "a", "title": "責任者", "name": "部長"}, {"id": "b", "parent": "a", "title": "担当", "name": "課長"}]}}
        rb = block_state(org)
        self.assertGreaterEqual(dscale.scale_of(rb["st"]["body"]), 1.0)

    def test_scaled_style_scales_sizes_not_ratios(self):
        d = {"x": 10, "y": 20, "w": 300, "h": 200, "node_size": 14, "node_wr": 0.8, "edge_w": 1.5, "scale_k": 1.5, "thin_grow": 1.5, "type_labels": {}}
        ds = dscale.scaled_style(d)
        self.assertEqual((ds["x"], ds["y"], ds["w"], ds["h"]), (10, 20, 300, 200))
        self.assertAlmostEqual(ds["node_size"], 21)
        self.assertAlmostEqual(ds["edge_w"], 2.25)
        self.assertEqual(ds["node_wr"], 0.8)
        self.assertEqual(ds["thin_grow"], 1.5)
        same = {"x": 1, "scale_k": 1}
        self.assertIs(dscale.scaled_style(same), same)


class StatusLegendPptxTest(unittest.TestCase):
    def test_legend_title_is_a_shape_not_a_merged_cell(self):
        import tempfile
        from pptx import Presentation
        slide = status_table(3)
        deck = one(slide, id="s5a-status")
        with tempfile.TemporaryDirectory() as td:
            import json
            Path(td, "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            import subprocess
            r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), td, "--pptx"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            prs = Presentation(str(Path(td, "build", "s5a-status.pptx")))
            sl = prs.slides[0]
            tables = [s for s in sl.shapes if s.has_table]
            legend = [t for t in tables if len(t.table.columns) == 2]
            self.assertEqual(len(legend), 1)                           # 凡例は 2 列（記号・説明）。見出しは表の外の図形
            self.assertTrue(any(s.has_text_frame and "ステータス" in s.text_frame.text for s in sl.shapes))
            xml = legend[0]._element.xml
            self.assertNotIn("rowSpan", xml)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# レビュー（ra）の指摘への修正: 明示した領域・短い cards の下限・図解の拡大の採用条件ほか
# ---------------------------------------------------------------------------

import copy  # noqa: E402
import json  # noqa: E402

SAMPLE = json.loads((TOOLS.parent / "examples" / "template-sample" / "deck.json").read_text(encoding="utf-8"))
DIAG_TYPES = ("architecture", "dataflow", "lifecycle", "sequence")
BUL3 = {"type": "bullets", "heading": "ポイント", "frame": "line", "bullets": ["質問は社内ポータルで受ける", "回答に手順書と更新日を付ける", "確信度が低いと人に回す"]}


def sample_block(kind):
    s = next(s for s in SAMPLE["slides"] if s["type"] == kind)
    blk = {k: v for k, v in copy.deepcopy(s).items() if k not in ("eyebrow", "title", "notes", "legend_page", "legend_lead", "conclusion")}
    blk["heading"] = "図の見出し"
    return blk


def comp_variants(kind):
    return {"single": {"type": "composite", "title": "t", "blocks": [sample_block(kind)]},
            "mainside": {"type": "composite", "title": "t", "arrange": "main-side", "blocks": [sample_block(kind), copy.deepcopy(BUL3)]},
            "topbottom": {"type": "composite", "title": "t", "arrange": "top-bottom", "rows": [3, 2], "blocks": [sample_block(kind), copy.deepcopy(BUL3)]}}


def block_diags(rb, k):
    d = dict(rb["st"].get("diagram") or {})
    kind = rb["type"]
    geo, diags = dscale._layout_at(rb["bs"], kind, d, k, [])
    return geo, diags, d


class DiagramScaleAdoptionTest(unittest.TestCase):
    """R-03 / R-04: 拡大は「k = 1 に無い診断を増やさない・k = 1 が too-dense なら拡大しない・描く枠に収まる」ときだけ。"""

    def test_scaling_never_adds_diagnostics_or_leaves_the_frame(self):
        seen_scaled = seen_dense = 0
        for kind in DIAG_TYPES:
            for name, slide in comp_variants(kind).items():
                for density in ("talk", "standard", "read"):
                    st, _ = resolve(copy.deepcopy(slide), density=density)
                    rb = st["_composite"]["blocks"][0]
                    k = dscale.scale_of(rb["st"]["diagram"])
                    geo1, diags1, d = block_diags(rb, 1)
                    if dscale._has_blocking(diags1):
                        seen_dense += 1
                        self.assertEqual(k, 1.0, (kind, name, density))
                    if k > 1.0:
                        seen_scaled += 1
                        geok, diagsk, _ = block_diags(rb, k)
                        self.assertLessEqual(dscale._diag_keys(diagsk), dscale._diag_keys(diags1), (kind, name, density))
                        self.assertLessEqual(dscale.overflow_px(geok, d), max(dscale.overflow_px(geo1, d), 0.0) + 0.5, (kind, name, density))
        self.assertGreater(seen_scaled, 5)          # 拡大そのものは残っている
        self.assertGreater(seen_dense, 0)           # 密すぎる図（k = 1 が too-dense）の組み合わせも試した

    def test_diag_keys_use_the_real_level_name(self):
        # diagram_engine の診断の level は "warning"。"warn" だけを数えて見逃していた（R-03 の原因）
        self.assertEqual(dscale._diag_keys([{"level": "warning", "code": "label-collision", "subject": "a→b"}, {"level": "info", "code": "x", "subject": "y"}]),
                         {("label-collision", "a→b")})
        self.assertTrue(dscale._has_blocking([{"level": "warning", "code": "too-dense", "subject": "messages"}]))
        self.assertFalse(dscale._has_blocking([{"level": "warning", "code": "label-collision", "subject": "a→b"}]))

    def test_a_replaced_diagnostic_is_not_missed(self):
        # 件数が同じでも、中身が別の診断に入れ替わったら増えたと見なす
        self.assertFalse(dscale._diag_keys([{"level": "warning", "code": "label-collision", "subject": "b"}])
                         <= dscale._diag_keys([{"level": "warning", "code": "label-collision", "subject": "a"}]))


class ProposalScaleWrapTest(unittest.TestCase):
    """R-05: kpi_tree / org の拡大で、折り返しが悪くならない（1 字の最終行・語の途中の折れを増やさない）。"""

    def test_scaled_proposal_does_not_break_words(self):
        seen = 0
        for kind in ("kpi_tree", "org"):
            for name, slide in comp_variants(kind).items():
                for density in ("talk", "standard", "read"):
                    st, _ = resolve(copy.deepcopy(slide), density=density)
                    rb = st["_composite"]["blocks"][0]
                    body = rb["st"]["body"]
                    k = dscale.scale_of(body)
                    if k <= 1.0:
                        continue
                    seen += 1
                    base_els = b.pe.layout_elements(rb["bs"], {**rb["st"], "body": {**body, "scale_k": 1}})
                    self.assertTrue(autofit._scaled_wrap_ok(rb["bs"], rb["st"], k, base_els, autofit._element_wrap_profiles(base_els)), (kind, name, density, k))
        self.assertGreater(seen, 0)

    def test_wrap_check_rejects_a_scale_that_breaks_words(self):
        # read 密度の kpi_tree（main-side）は、そのまま 1.29 倍にすると「早く答え/る」のように折れる
        st, _ = resolve(comp_variants("kpi_tree")["mainside"], density="read")
        rb = st["_composite"]["blocks"][0]
        view = {**rb["st"], "body": {**rb["st"]["body"], "scale_k": 1}}
        base_els = b.pe.layout_elements(rb["bs"], view)
        self.assertFalse(autofit._scaled_wrap_ok(rb["bs"], rb["st"], 1.294, base_els, autofit._element_wrap_profiles(base_els)))


def tokens_off(d):
    """領域の値から、拡大のトークン（thin_* / fill_*）を除いた写し（比べる対象は出力の寸法）。"""
    return {k: v for k, v in d.items() if not k.startswith(("thin_", "fill_"))}


def msg(exc, err):
    return (str(exc.args[0]) if exc is not None and exc.args else "") + err


STEPS_OFF = {"steps": {"body": {"thin_grow": 1}}}                                  # S5a の steps の拡大・箱の伸ばしを止めた（変更前と同じ）
CARDS_S3 = {"cards": {"grid": {"thin_grow": 1.4, "thin_min_ratio": 0, "thin_legacy_ratio": 0}}}   # 変更前（S3）と同じ cards


class UserSetRegionTest(unittest.TestCase):
    """R-01: style / layout_overrides に領域のキー（位置・大きさ・文字・列数）を書いたスライドは、S5a の拡大・箱の伸ばしを全部飛ばす。"""

    def test_steps_with_any_body_key_is_not_touched(self):
        for density in ("talk", "standard", "read"):
            for style in ({"min_h": 200}, {"valign": "top"}, {"fit": "content"}, {"h": 300}, {"item_size": 16}, {"label_size": 18}, {"gap": 24}):
                for n, k in ((4, 3), (3, 2), (2, 1)):
                    got, _ = resolve(steps(n, k, style={"body": style}), density=density)
                    ref, _ = resolve(steps(n, k, style={"body": style}), density=density, layout_overrides=STEPS_OFF)
                    self.assertEqual(tokens_off(got["body"]), tokens_off(ref["body"]), (density, style, n, k))

    def test_steps_token_only_style_still_grows(self):
        # thin_* などのトークンは「領域を自分で決めた」とは見なさない
        st, _ = resolve(steps(4, 3, style={"body": {"thin_target": 0.7}}))
        self.assertEqual(st["body"].get("valign"), "middle")

    def test_cards_with_any_grid_key_or_columns_is_not_touched(self):
        for density in ("talk", "standard", "read"):
            for kw in ({"style": {"grid": {"cols": 3}}}, {"style": {"grid": {"heading_size": 20}}}, {"style": {"grid": {"body_size": 16}}},
                       {"style": {"grid": {"gap": 20}}}, {"columns": 3}):
                for n in (3, 5):
                    got, _ = resolve(cards(n, **kw), density=density)
                    ref, _ = resolve(cards(n, **kw), density=density, layout_overrides=CARDS_S3)
                    for key in ("heading_size", "body_size", "item_size", "y", "h", "cols"):
                        self.assertEqual(got["grid"].get(key), ref["grid"].get(key), (density, kw, n, key))

    def test_user_thin_grow_is_used_as_written(self):
        got, _ = resolve(cards(3, style={"grid": {"thin_grow": 2.0, "heading_size": 20}}), density="standard")
        capped, _ = resolve(cards(3, style={"grid": {"thin_grow": 1.4, "heading_size": 20}}), density="standard")
        self.assertGreaterEqual(got["grid"]["body_size"], capped["grid"]["body_size"])


class ShortCardsFloorTest(unittest.TestCase):
    """R-02: 短い cards は、変更前（S3 の薄い cards の拡大）より文字が小さくならない。"""

    @staticmethod
    def many(n, long_body=False):
        heads = ["手順書から一次回答", "担当者への引き継ぎ", "根拠の表示", "履歴からの改善", "利用状況の見える化", "権限の管理"]
        bodies = ["質問の意味を読み取り根拠つきで答える", "確信度が低い質問は人に引き継ぐ", "回答に元の手順書と更新日を付ける",
                  "誤回答の報告を毎週の更新に反映する", "件数と解決率を週次で確認できる", "部署ごとに見られる範囲を分ける"]
        return {"type": "cards", "title": "課題", "cards": [{"heading": heads[i], "body": bodies[i] + ("。" + bodies[i] if long_body else "")} for i in range(n)]}

    def test_never_smaller_than_the_old_growth(self):
        for density in ("talk", "standard", "read"):
            for n in (2, 3, 4, 5, 6):
                for lb in (False, True):
                    new, _ = resolve(self.many(n, lb), density=density)
                    old, _ = resolve(self.many(n, lb), density=density, layout_overrides=CARDS_S3)
                    for key in ("heading_size", "body_size"):
                        self.assertGreaterEqual(new["grid"][key], old["grid"][key], (density, n, lb, key))

    def test_two_pass_fit_keeps_the_size(self):
        # 文節の改行（\n）を入れた文で二度目の自動フィットをしても、薄いと見なされず小さくなる、ということが無い
        base, _ = resolve(self.many(5), density="talk")
        broken = self.many(5)
        broken["cards"][0]["body"] = "質問の意味を\n読み取り根拠つきで\n答える"
        again, _ = resolve(broken, density="talk")
        self.assertEqual((again["grid"]["heading_size"], again["grid"]["body_size"]), (base["grid"]["heading_size"], base["grid"]["body_size"]))


class ScheduleThinBranchTest(unittest.TestCase):
    """R-06: 1〜3 行（S4 の薄い分岐）は、行見出しが長くても変更前と同じ拡大をする。fill_trigger: 0 で 4 行以上も変更前と同じ。"""

    def slide(self, n, label="現状整理と課題の洗い出し"):
        rows = [{"label": label, "bars": [{"start": "2026-11", "end": "2026-12", "label": "実施"}]} for _ in range(n)]
        return {"type": "schedule", "title": "計画", "timeline": {"start": "2026-11", "end": "2027-03", "unit": "month"}, "rows": rows}

    def test_long_row_labels_still_grow_with_few_rows(self):
        base, _ = resolve(self.slide(3), autofit=False)
        for n in (1, 2, 3):
            st, _ = resolve(self.slide(n))
            self.assertGreater(st["chart"]["bar_size"], base["chart"]["bar_size"], n)
            self.assertGreater(st["chart"]["col_size"], base["chart"]["col_size"], n)

    def test_fill_trigger_zero_equals_the_old_result(self):
        for n in (1, 2, 3, 4, 5):
            got, _ = resolve(self.slide(n), layout_overrides={"schedule": {"chart": {"fill_trigger": 0}}})
            ref, _ = resolve(self.slide(n), layout_overrides={"schedule": {"chart": {"fill_trigger": 0, "fill_grow": 1, "fill_text_grow": 1}}})
            self.assertEqual(tokens_off(got["chart"]), tokens_off(ref["chart"]), n)


class ScaleKValidationTest(unittest.TestCase):
    """R-07: 文書化した止め方 style.diagram.scale_k: 1（org / kpi_tree は style.body.scale_k）は誤警告にならず、値の型・範囲を見る。"""

    def test_scale_k_is_a_known_key(self):
        for kind in DIAG_TYPES:
            blk = sample_block(kind)
            blk["style"] = {"diagram": {"scale_k": 1}}
            exc, err = validate(one({"type": "composite", "title": "t", "blocks": [blk, copy.deepcopy(BUL3)]}))
            self.assertIsNone(exc, (kind, err))
            self.assertNotIn("scale_k", err, kind)
        for kind in ("org", "kpi_tree"):
            blk = sample_block(kind)
            blk["style"] = {"body": {"scale_k": 1}}
            exc, err = validate(one({"type": "composite", "title": "t", "arrange": "top-bottom", "blocks": [blk, copy.deepcopy(BUL3)]}))
            self.assertIsNone(exc, (kind, err))
            self.assertNotIn("scale_k", err, kind)

    def test_scale_k_range_and_type(self):
        for bad in (0, 0.5, 5, -1, "1", True, float("nan")):
            blk = sample_block("architecture")
            blk["style"] = {"diagram": {"scale_k": bad}}
            exc, err = validate(one({"type": "composite", "title": "t", "blocks": [blk, copy.deepcopy(BUL3)]}))
            self.assertIsNotNone(exc, bad)
            self.assertIn("scale_k", msg(exc, err), bad)
        blk = sample_block("architecture")
        blk["style"] = {"diagram": {"scale_k": 1.3}}
        exc, _ = validate(one({"type": "composite", "title": "t", "blocks": [blk, copy.deepcopy(BUL3)]}))
        self.assertIsNone(exc)

    def test_scale_k_stops_the_scaling_without_a_warning(self):
        blk = sample_block("architecture")
        blk["style"] = {"diagram": {"scale_k": 1}}
        st, _ = resolve({"type": "composite", "title": "t", "blocks": [blk, copy.deepcopy(BUL3)]})
        self.assertEqual(dscale.scale_of(st["_composite"]["blocks"][0]["st"]["diagram"]), 1.0)


class GrowSizesValidationTest(unittest.TestCase):
    """R-11: cycle の grow_sizes は数値の配列（各 1〜200）。それ以外はキー名つきのエラー。[] は「止める」として有効。"""
    SLIDE = CycleTest.SLIDE

    def check(self, value):
        return validate(one(dict(self.SLIDE, style={"body": {"grow_sizes": value}})))

    def test_bad_values_fail_with_the_key_name(self):
        for bad in (-1, 1e9, float("nan"), "abc", "", [1, "a"], [0], [201], {"a": 1}, True, [True], [float("nan")], 20):
            exc, err = self.check(bad)
            self.assertIsNotNone(exc, bad)
            self.assertIn("grow_sizes", msg(exc, err), bad)

    def test_good_values_pass(self):
        for ok in ([], [20, 18], [16], [1, 200], [20.5]):
            exc, err = self.check(ok)
            self.assertIsNone(exc, (ok, err))

    def test_empty_array_stops_the_growth(self):
        st, _ = resolve(dict(self.SLIDE, style={"body": {"grow_sizes": []}}))
        self.assertNotIn("sizes", st["body"])


class ScheduleAutoBeforeTest(unittest.TestCase):
    def test_auto_before_is_a_known_bool_key(self):
        sl = {"type": "schedule", "title": "計画", "timeline": {"start": "2026-11", "end": "2027-03", "unit": "month"},
              "rows": [{"label": "A", "bars": [{"start": "2026-11", "end": "2026-12", "label": "実施"}]}], "style": {"chart": {"auto_before": False}}}
        exc, err = validate(one(sl))
        self.assertIsNone(exc, err)
        self.assertNotIn("auto_before", err)
        sl["style"] = {"chart": {"auto_before": "no"}}
        exc, err = validate(one(sl))
        self.assertIsNotNone(exc)
        self.assertIn("auto_before", msg(exc, err))


class ColsSearchTokenTest(unittest.TestCase):
    """R-08（前半）: 単独 cards の列数の選び直しは、columns を書くほかに、トークン cols_search: false でも止められる。"""

    def test_cols_search_false_keeps_the_default_columns(self):
        st, _ = resolve(cards(2))
        self.assertEqual(st["grid"]["cols"], 2)
        st, _ = resolve(cards(2), layout_overrides={"cards": {"grid": {"cols_search": False}}})
        self.assertEqual(st["grid"].get("cols", 3), 3)

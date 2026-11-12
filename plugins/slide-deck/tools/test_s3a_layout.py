#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3a 仕上げ: 薄い箱（cards / ブロックの steps・cards）・talk の表・表だけの split・callout の強調・kpi の from_unit と大きさ・
sharp の start ノード・status_table の凡例なし・カードのアイコンと見出し・lint の基準・brand の対比。

実行: python3 -m unittest plugins/slide-deck/tools/test_s3a_layout.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import color_pick as cp  # noqa: E402
import dataviz_engine as dv  # noqa: E402
import lint_deck_text as lint  # noqa: E402

PY = sys.executable


def mk(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s3a_l_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def styled(slides, idx=0, **meta):
    d = mk(slides, **meta)
    deck, theme, layout = b.load_deck(d)
    b.validate_deck(deck, layout, theme, d)
    return deck, theme, layout, b.resolve_style(layout, deck, deck["slides"][idx])


THIN = [{"heading": "速い", "body": "1 時間で終わる"}, {"heading": "安い", "body": "月額は定額"}, {"heading": "確実", "body": "二重に確認する"}]
THICK = [{"heading": "速い", "body": "1 時間で終わる。手順は自動化され、人が触るのは最後の確認だけに絞られる。" * 2, "items": ["自動で下書き", "自動で整形", "人が最終確認", "監査ログ"]}] * 3


class ThinBoxTest(unittest.TestCase):
    def test_pure_function(self):
        g = {"thin_k": 1.3, "thin_trigger": 0.72, "thin_valign": "middle", "min_h": 100}
        y, h = autofit.thin_box(100, 1, 16, 196, 440, g)
        self.assertEqual(h, 130.0)
        self.assertAlmostEqual(y, 196 + (440 - 130) / 2, places=1)
        self.assertEqual(autofit.thin_box(100, 1, 16, 196, 440, {**g, "thin_valign": "top"})[0], 196)
        self.assertIsNone(autofit.thin_box(300, 1, 16, 196, 440, g))          # 厚い: 抑えない
        self.assertIsNone(autofit.thin_box(100, 1, 16, 196, 440, {}))         # 指定なし
        self.assertEqual(autofit.thin_box(10, 2, 10, 0, 400, g)[1], 210.0)     # min_h 100 × 2 段 + gap

    def test_thin_cards_are_shrunk_and_centered(self):
        _, _, _, st = styled([{"type": "cards", "title": "t", "cards": THIN}])
        g = st["grid"]
        self.assertLess(g["h"], 250)
        self.assertAlmostEqual(g["y"] + g["h"] / 2, 196 + 440 / 2, delta=2)        # 本文領域の縦中央

    def test_thick_cards_unchanged(self):
        _, _, _, st = styled([{"type": "cards", "title": "t", "cards": THICK}])
        self.assertEqual(st["grid"]["y"], 196)

    def test_explicit_values_win(self):
        _, _, _, st = styled([{"type": "cards", "title": "t", "cards": THIN, "style": {"grid": {"h": 300}}}])
        self.assertEqual(st["grid"]["h"], 300)
        _, _, _, st = styled([{"type": "cards", "title": "t", "cards": THIN, "style": {"grid": {"fit": "fill"}}}])
        self.assertEqual(st["grid"]["h"], 440)

    def test_block_cards_top_aligned_and_steps_min_h(self):
        slide = {"type": "composite", "title": "t", "arrange": "top-bottom", "rows": [3, 2], "blocks": [
            {"type": "cards", "cards": THIN}, {"type": "steps", "steps": [{"label": "a", "items": ["x"]}, {"label": "b", "items": ["y"]}]}]}
        _, _, _, st = styled([slide])
        blocks = st["_composite"]["blocks"]
        rect0 = blocks[0]["rect"]
        g = blocks[0]["st"]["grid"]
        self.assertAlmostEqual(g["y"], rect0[1], delta=1)             # ブロックの上端（上寄せ）
        # S4: 列数を書いていない薄いカードは、列数を選び直して（3 枚 → 2 列 × 2 段）枠いっぱいに並べ、縦中央に置く
        self.assertEqual(g["cols"], 2)
        self.assertAlmostEqual(g["h"], rect0[3], delta=1)
        self.assertEqual(g["valign"], "middle")
        self.assertGreater(blocks[0]["st"]["_fit"]["info"]["cards"]["grown"], 1.3)
        sb = blocks[1]["st"]["body"]
        self.assertEqual(sb["content_y_ratio"], 0)
        self.assertEqual(sb["min_h"], 120)

    def test_block_cards_with_explicit_columns_pack_the_box(self):
        # 列数を書いたときは列数を動かさず、従来どおり箱を中身に合わせて詰める（上端はブロックの上端）
        slide = {"type": "composite", "title": "t", "arrange": "top-bottom", "rows": [3, 2], "blocks": [
            {"type": "cards", "cards": THIN, "columns": 3}, {"type": "steps", "steps": [{"label": "a", "items": ["x"]}, {"label": "b", "items": ["y"]}]}]}
        _, _, _, st = styled([slide])
        blk = st["_composite"]["blocks"][0]
        g = blk["st"]["grid"]
        self.assertEqual(g["cols"], 3)
        self.assertAlmostEqual(g["y"], blk["rect"][1], delta=1)
        self.assertLess(g["h"], blk["rect"][3] - 100)                    # 詰めた（rect 288px に対して 130px）
        self.assertTrue(blk["st"]["_fit"]["info"]["cards"].get("thin"))


class TableTest(unittest.TestCase):
    def test_talk_table_stretched_and_centered(self):
        rows = [["A", "1"], ["B", "2"], ["C", "3"]]
        _, _, _, st = styled([{"type": "table", "title": "t", "columns": ["x", "y"], "rows": rows}], density="talk")
        tr = st["table"]
        self.assertGreater(tr["row_h"], 66)
        self.assertLessEqual(tr["row_h"], 96)
        self.assertGreater(tr["y"], 192)                                 # 余った分は縦中央へ

    def test_talk_table_user_row_h_wins(self):
        rows = [["A", "1"], ["B", "2"]]
        _, _, _, st = styled([{"type": "table", "title": "t", "columns": ["x", "y"], "rows": rows, "style": {"table": {"row_h": 66, "y": 192}}}], density="talk")
        self.assertEqual(st["table"]["row_h"], 66)
        self.assertEqual(st["table"]["y"], 192)

    def test_standard_table_unchanged(self):
        rows = [["A", "1"], ["B", "2"]]
        _, _, _, st = styled([{"type": "table", "title": "t", "columns": ["x", "y"], "rows": rows}])
        self.assertEqual(st["table"]["y"], 192)

    def test_lone_table_in_split_is_centered(self):
        slide = {"type": "split", "title": "t", "panel": {"kpi": {"value": "72%", "label": "x"}},
                 "blocks": [{"type": "table", "columns": ["a", "b"], "rows": [["1", "2"], ["3", "4"], ["5", "6"]]}]}
        _, _, _, st = styled([slide])
        rb = st["_composite"]["blocks"][0]
        rect = rb["rect"]
        tr = rb["st"]["table"]
        self.assertGreater(tr["y"], rect[1] + 40)
        info = rb["st"]["_fit"]["info"]["table"]
        used = info["total_h"] + (tr["row_h"] - info["row_h"]) * 3
        self.assertAlmostEqual(tr["y"] - rect[1], (rect[3] - used) / 2, delta=3)


class CalloutTest(unittest.TestCase):
    def test_emphasis_callout_has_no_white_bar(self):
        d = mk([{"type": "composite", "title": "t", "blocks": [{"type": "callout", "text": "強調", "emphasis": True}, {"type": "callout", "text": "通常"}]}])
        r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), "--html"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        html = (d / "build" / "d.html").read_text(encoding="utf-8")
        self.assertNotIn("ブロック1の帯", html)



class KpiTest(unittest.TestCase):
    def test_from_unit_rules(self):
        self.assertEqual(dv.from_unit({"from": "6.5", "unit": "時間"}), "時間")
        self.assertEqual(dv.from_unit({"from": "3か月", "unit": "週間"}), "")
        self.assertEqual(dv.from_unit({"from": "6.5", "unit": "時間", "from_unit": "分"}), "分")
        self.assertEqual(dv.from_unit({"from": "3か月", "unit": "週間", "from_unit": ""}), "")
        self.assertEqual(dv.from_unit({"from": 22, "unit": "%"}), "%")

    def test_of_and_from_prefers_from(self):
        out = dv._kpi_items({"items": [{"value": "9", "of": "12", "from": "6"}, {"value": "3", "of": "5"}]})
        self.assertNotIn("of", out[0])
        self.assertEqual(out[1]["of"], "5")

    def test_tiles_fill_the_body(self):
        deck, th, layout, st = styled([{"type": "kpi", "title": "t", "items": [{"value": "1", "unit": "時間", "label": "a"}, {"value": "2", "unit": "件", "label": "b"}, {"value": "3", "unit": "%", "label": "c"}]}])
        self.assertGreaterEqual(st["body"]["tile_max_size"], 100)
        self.assertGreaterEqual(st["body"]["tile_min_ratio"], 0.9)


class SharpStartTest(unittest.TestCase):
    def test_start_node_thicker_only_without_rounding(self):
        d = {"start_border_w_sharp": 3.5, "node_border_w": 1.5}
        round_vis = b._node_visual({"kind": "start"}, d, "lifecycle", 999)
        sharp_vis = b._node_visual({"kind": "start"}, d, "lifecycle", 0)
        proc = b._node_visual({"kind": "active"}, d, "lifecycle", 0)
        self.assertEqual(round_vis["border_w"], 2)                      # classic は従来どおり
        self.assertEqual(sharp_vis["border_w"], 3.5)
        self.assertLess(proc["border_w"], sharp_vis["border_w"])


class StatusTableTest(unittest.TestCase):
    def test_legend_false_widens_title(self):
        s = {"type": "status_table", "title": "t", "columns": ["a", "b", "c"], "rows": [{"label": "PMO", "status": "green", "cells": [["実績"]]}], "legend": False}
        _, _, _, st = styled([s])
        self.assertEqual(st["title"]["w"], st["rule"]["w"])
        s2 = dict(s)
        s2.pop("legend")
        _, _, _, st2 = styled([s2])
        self.assertEqual(st2["title"]["w"], 690)

    def test_user_title_width_wins(self):
        s = {"type": "status_table", "title": "t", "columns": ["a", "b", "c"], "rows": [{"label": "PMO", "status": "green", "cells": [["実績"]]}], "legend": False,
             "style": {"title": {"w": 500}}}
        _, _, _, st = styled([s])
        self.assertEqual(st["title"]["w"], 500)


class CardIconTest(unittest.TestCase):
    def test_heading_width_reserves_icon_space(self):
        g = {"icon_size": 28, "pad": 18}
        self.assertEqual(autofit.card_icon_reserve({"icon": "database"}, g), 28.0)
        self.assertEqual(autofit.card_icon_reserve({"heading": "x"}, g), 0.0)
        a = autofit.cards_content({"heading": "とても長い見出しの文字列です", "icon": "bolt"}, {"heading_size": 19, "pad": 18}, 300)
        c = autofit.cards_content({"heading": "とても長い見出しの文字列です"}, {"heading_size": 19, "pad": 18}, 300)
        self.assertGreaterEqual(a["head_h"], c["head_h"])


class LintTest(unittest.TestCase):
    def test_ika_ni_is_not_layout_description(self):
        self.assertIsNone(lint.LAYOUT_DESC.search("作成時間を半分以下にしたい"))
        self.assertIsNone(lint.LAYOUT_DESC.search("差し戻しを 3 割未満にする"))
        self.assertTrue(lint.LAYOUT_DESC.search("図の下に表を置く"))

    def test_todo_warning_wording(self):
        res = lint.lint({"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "結論", "bullets": ["数字【要確認】"]}]})
        text = " ".join(res["warnings"])
        self.assertIn("確かめる点を【要確認: …】で明示するか", text)
        self.assertNotIn("断定を弱める", text)

    def test_space_lint_end_to_end(self):
        mixed = lint.lint({"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "AI 活用の3か月", "bullets": ["a"]}]})
        unified = lint.lint({"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "AI 活用の 3 か月", "bullets": ["a"]}]})
        self.assertTrue(any("空白がそろっていない" in w for w in mixed["warnings"]))
        self.assertFalse(any("空白" in w for w in unified["warnings"]))

    def test_space_style_only_warns_when_mixed(self):
        rx_s, rx_t = lint.JA_SPACE, lint.JA_TIGHT
        spaced = "AI 活用の 3 か月"
        mixed = "AI 活用の3か月"
        self.assertTrue(rx_s.search(spaced) and not rx_t.search(spaced))
        self.assertTrue(rx_s.search(mixed) and rx_t.search(mixed))


class BrandTest(unittest.TestCase):
    def test_brand_readable_on_dark_section(self):
        for theme in ("default", "acn-slide-master", "accenture"):
            deck, th, layout, st = styled([{"type": "section", "title": "章"}], theme=theme, brand="ACME")
            self.assertGreaterEqual(cp.contrast(b.col(th, st["brand"]["color"]), b.col(th, st["bg"]["fill"])), 4.5, theme)

    def test_brand_on_plain_slide_untouched(self):
        deck, th, layout, st = styled([{"type": "bullets", "title": "t", "bullets": ["a"]}], brand="ACME")
        self.assertEqual(st["brand"]["color"], "accent")


if __name__ == "__main__":
    unittest.main()

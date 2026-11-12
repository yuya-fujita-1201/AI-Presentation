#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 のレビュー指摘の修正（s3-A-01 / A-03 / A-04 / A-05 / A-07 / A-10 など）のテスト。

実行: python3 -m unittest plugins/slide-deck/tools/test_s3_fix.py
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
import build_deck as b  # noqa: E402

PY = sys.executable
ROOT = TOOLS.parent
LAY = b.load_json(ROOT / "templates" / "layouts" / "default.json")


def build(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s3fix_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
    return d, r


class TitleWrapTest(unittest.TestCase):
    """s3-A-01: variant なしの表紙 title も、大きな文字は文節で折る（語の途中で切らない）。"""

    def test_cover_title_breaks_at_phrase(self):
        text = "経営会議向けの月次レポートを自動で整える仕組みを導入した"
        d, r = build([{"type": "title", "title": text, "subtitle": "s"}])
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (d / "build" / "d.html").read_text(encoding="utf-8")
        m = re.search(r'role="heading"[^>]*>([^<]*(?:<br>[^<]*)*)</div>', h)
        self.assertIsNotNone(m)
        first, _, rest = m.group(1).partition("<br>")
        self.assertTrue(rest, "2 行に折れていない")
        self.assertFalse(first.endswith(("整", "経営会議向")), f"語の途中で切れている: {first}|{rest}")
        self.assertGreaterEqual(len(rest), 5)          # 最終行が短い切れ端にならない


class SchedulePlaceTest(unittest.TestCase):
    """s3-A-07: 縮めないと入らない（12px 未満）矢羽根のラベルは、右が空いていれば外に出す。空きが無ければ中のまま縮める。"""
    CHART = LAY["types"]["schedule"]["chart"]

    def geo(self, label, start, end, **kw):
        slide = {"type": "schedule", "title": "t", "timeline": {"start": "2026-01", "end": "2026-12", "unit": "month"},
                 "rows": [{"label": "A", "bars": [dict({"start": start, "end": end, "label": label}, **kw)]}]}
        return se.layout_schedule(slide, self.CHART)

    def test_small_label_moves_out_when_room(self):
        g = self.geo("本稼働準備と最終確認", "2026-03", "2026-03")
        bar = g["bars"][0]
        self.assertEqual(bar["label_pos"], "after")
        self.assertGreaterEqual(bar["size"], 12)

    def test_no_room_keeps_inside_shrunk(self):
        g = self.geo("本稼働準備と最終確認", "2026-12", "2026-12")        # 右が時間軸の端
        bar = g["bars"][0]
        self.assertEqual(bar["label_pos"], "before")                     # S4: 右に出せないときは左に出す（12px 未満まで縮めない）
        self.assertGreaterEqual(bar["size"], 12)
        self.assertLess(bar["lbl_x"], bar["x"])
        g = self.geo("本稼働準備と最終確認", "2026-12", "2026-12", label_pos="inside")
        self.assertEqual(g["bars"][0]["label_pos"], "inside")

    def test_explicit_inside_is_respected(self):
        g = self.geo("本稼働準備と最終確認", "2026-03", "2026-03", label_pos="inside")
        self.assertEqual(g["bars"][0]["label_pos"], "inside")


import schedule_engine as se  # noqa: E402


class AgendaKeyTest(unittest.TestCase):
    """s3-A-10: agenda の items に title と書くと、黙って空の項目にならず警告が出る。"""

    def test_title_key_warns(self):
        d, r = build([{"type": "agenda", "title": "流れ", "items": [{"title": "現状"}, {"text": "ok"}]}])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("items[0] の未知のキー \"title\"", r.stderr)
        self.assertIn("\"text\" に項目名を書く", r.stderr)

    def test_valid_items_no_warning(self):
        d, r = build([{"type": "agenda", "title": "流れ", "items": ["a", {"text": "b", "desc": "c"}]}])
        self.assertNotIn("items[", r.stderr)


class BrandTest(unittest.TestCase):
    """s3-A-04: meta.brand は split のパネルの上に置く（タイトルを狭めず、check_layout の overlap にならない）。"""

    def test_split_brand_in_panel_and_title_full_width(self):
        deck = {"meta": {"brand": "ACME"}}
        slide = {"type": "split", "title": "内訳: 体裁の修正が消え、下書きとレビューが縮んだ", "panel": {"fill": "primary", "title": "x"},
                 "blocks": [{"type": "text", "text": "a"}]}
        # resolve_style は load_layout 済みのレイアウトが要る
        lay = b.load_layout("default", None)
        st = b.resolve_style(lay, deck, slide)
        self.assertGreaterEqual(st["brand"]["x"], st["panel"]["x"])
        self.assertLessEqual(st["brand"]["x"] + st["brand"]["w"], st["panel"]["x"] + st["panel"]["w"])
        self.assertEqual(st["title"]["w"], st["rule"]["w"])

    def test_bleed_image_text_brand_is_on_bg_palette(self):
        lay = b.load_layout("default", None)
        import hero_engine as hero
        self.assertEqual(hero.on_bg_regions(lay, "image_text", "bleed", True), ["brand"])
        self.assertEqual(hero.on_bg_regions(lay, "image_text", "bleed", False), [])
        # 画像が左のときの brand は文字側（下地）にあるので、画像の上の色にしない
        self.assertEqual(hero.on_bg_regions(lay, "image_text", "bleed", True, {"image_side": "left"}), [])


class StatementKickerTest(unittest.TestCase):
    """s3-A-05: statement の kicker も、地の色の上で読める色に寄せる。"""

    def test_readable_pair_registered(self):
        self.assertIn(["kicker", "color", ["@ground"]], LAY["readable_pairs"]["statement"])


class KpiTreeNarrowTest(unittest.TestCase):
    """s3-A-03: 半幅の合成ブロックの kpi_tree は、縮めて収める（fail しない）。値が途中で折れない。"""

    def test_half_width_block_builds(self):
        tree = {"type": "kpi_tree", "headers": ["目標", "方向性", "KPI", "", "測り方"], "root": "価値",
                "branches": [{"title": "止める", "kpis": [{"title": "未承認ゼロ", "value": "100%", "note": "月次棚卸"}]}]}
        d, r = build([{"type": "composite", "title": "narrow", "arrange": "main-side",
                       "blocks": [tree, {"type": "bullets", "bullets": ["a", "b"]}]}])
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (d / "build" / "d.html").read_text(encoding="utf-8")
        self.assertNotIn("100<br>", h)
        self.assertNotRegex(h, r">100<br>%")


if __name__ == "__main__":
    unittest.main()

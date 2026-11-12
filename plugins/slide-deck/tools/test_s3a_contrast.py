#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3a コントラスト: 「地の色に対して読める文字色」（color_pick / readable_pairs / ノード・表の tone）のテスト。

実行: python3 -m unittest plugins/slide-deck/tools/test_s3a_contrast.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import color_pick as cp  # noqa: E402

PY = sys.executable
SAMPLE = TOOLS.parent / "examples" / "template-sample"


def deck_dir(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s3a_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def resolved(slides, idx=0, **meta):
    d = deck_dir(slides, **meta)
    deck, theme, layout = b.load_deck(d)
    return deck, theme, layout, b.resolve_style(layout, deck, deck["slides"][idx])


class ColorPickTest(unittest.TestCase):
    def test_enough_contrast_kept(self):
        self.assertEqual(cp.readable_on("#1A2233", "#FFFFFF"), "#1A2233")

    def test_low_contrast_moved_keeping_hue(self):
        c = cp.readable_on("#007D96", "#BFDDE7")
        self.assertGreaterEqual(cp.contrast(c, "#BFDDE7"), 4.5)
        r, g, bl = cp.hex_to_rgb(c)
        self.assertTrue(bl >= r)                 # 青緑のまま（黒一色に飛ばない）

    def test_dark_ground_goes_lighter(self):
        c = cp.readable_on("#A100FF", "#460073")
        self.assertGreaterEqual(cp.contrast(c, "#460073"), 4.5)
        self.assertGreater(cp.luminance(c), cp.luminance("#A100FF"))

    def test_same_color_as_ground_becomes_readable(self):
        c = cp.readable_on("#007D96", "#007D96")
        self.assertGreaterEqual(cp.contrast(c, "#007D96"), 4.5)

    def test_all_grounds(self):
        c = cp.readable_on_all("#007D96", ["#FFFFFF", "#E0E7F0"])
        self.assertGreaterEqual(cp.contrast(c, "#FFFFFF"), 4.5)
        self.assertGreaterEqual(cp.contrast(c, "#E0E7F0"), 4.5)

    def test_build_deck_readable_on_delegates(self):
        self.assertEqual(b.readable_on("#007D96", "#BFDDE7"), cp.readable_on("#007D96", "#BFDDE7"))


class ReadablePairsTest(unittest.TestCase):
    def test_steps_num_color_on_dark_header(self):
        for theme in ("default", "acn-slide-master", "accenture", "acn-technology-graphik"):
            deck, th, layout, st = resolved([{"type": "steps", "title": "t", "steps": [{"label": "a", "items": ["x"]}]}], theme=theme)
            fg = b.col(th, st["body"]["num_color"])
            bg = b.col(th, st["body"]["header_fill"])
            self.assertGreaterEqual(cp.contrast(fg, bg), 4.5, theme)

    def test_explicit_user_value_wins(self):
        s = {"type": "steps", "title": "t", "steps": [{"label": "a", "items": ["x"]}], "style": {"body": {"num_color": "accent"}}}
        deck, th, layout, st = resolved([s])
        self.assertEqual(st["body"]["num_color"], "accent")

    def test_matrix_highlight_heading(self):
        s = {"type": "matrix", "title": "t", "x_axis": "x", "y_axis": "y",
             "quadrants": [{"heading": "a", "body": "b", "highlight": True}, {"heading": "c", "body": "d"}, {"heading": "e", "body": "f"}, {"heading": "g", "body": "h"}]}
        for theme in ("default", "acn-slide-master"):
            deck, th, layout, st = resolved([s], theme=theme)
            g = st["grid"]
            self.assertGreaterEqual(cp.contrast(b.col(th, g["hi_heading_color"]), b.col(th, g["hi_fill"])), 4.5, theme)
            self.assertGreaterEqual(cp.contrast(b.col(th, g["body_color"]), b.col(th, g["hi_fill"])), 4.5, theme)

    def test_section_with_variant_is_not_touched(self):
        s = {"type": "section", "title": "章", "variant": "side"}
        deck, th, layout, st = resolved([s])
        self.assertEqual(st["number"]["color"], "accent_on_primary")

    def test_layout_without_colors_is_skipped(self):
        d = deck_dir([{"type": "steps", "title": "t", "steps": [{"label": "a", "items": ["x"]}]}])
        deck, th, layout = b.load_deck(d)
        layout.pop("_colors")
        st = b.resolve_style(layout, deck, deck["slides"][0])
        self.assertEqual(st["body"]["num_color"], "accent")          # 変えない（default の steps は accent）


class ToneTest(unittest.TestCase):
    def test_tone_on_emphasis_row_is_readable(self):
        rows = [{"cells": ["A", {"text": "注意", "tone": "warn"}], "emphasis": True},
                {"cells": ["B", {"text": "重点", "tone": "accent"}], "emphasis": True},
                ["C", {"text": "補足", "tone": "accent"}], ["D", {"text": "補足", "tone": "accent"}]]
        d = deck_dir([{"type": "table", "title": "t", "columns": ["項目", "状態"], "rows": rows}])
        r = subprocess.run([PY, str(TOOLS / "check_layout.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
        self.assertRegex(r.stdout + r.stderr, r"contrast=0 ")

    def test_cell_tone_color_without_bg_is_unchanged(self):
        th = {"colors": {"accent": "#007D96", "muted": "#566781"}}
        self.assertEqual(b._cell_tone_color(th, {"tone_colors": {"accent": "accent"}}, {"tone": "accent"}), "#007D96")
        got = b._cell_tone_color(th, {"tone_colors": {"accent": "accent"}}, {"tone": "accent"}, "#BFDDE7")
        self.assertGreaterEqual(cp.contrast(got, "#BFDDE7"), 4.5)


class DiagramNodeTest(unittest.TestCase):
    def test_node_hexes_readable_on_their_fill(self):
        deck, th, layout, st = resolved([{"type": "lifecycle", "title": "t", "nodes": [{"id": "a", "label": "a", "kind": "success", "step": "05"}]}])
        d = st["diagram"]
        box = {"variant": "default", "kind": "success"}
        vis = b._node_visual(box, d, "lifecycle")
        hx = b._node_hexes(vis, d, th, box)
        fill = b.col(th, vis["fill"])
        for k in ("color", "sub", "step", "glyph"):
            self.assertGreaterEqual(cp.contrast(hx[k], fill), 4.5, k)

    def test_emphasis_node_sub_and_tag(self):
        deck, th, layout, st = resolved([{"type": "architecture", "title": "t", "nodes": [{"id": "a", "label": "a", "row": 0, "col": 0}]}])
        d = st["diagram"]
        box = {"variant": "emphasis"}
        vis = b._node_visual(box, d, "architecture")
        hx = b._node_hexes(vis, d, th, box)
        self.assertGreaterEqual(cp.contrast(hx["sub"], b.col(th, vis["fill"])), 4.5)
        self.assertGreaterEqual(cp.contrast(hx["tag"], b.col(th, d.get("tag_fill", "highlight_fill"))), 4.5)


class SampleContrastTest(unittest.TestCase):
    """見本 46 枚 × 同梱 4 テーマで contrast 警告が 0 件（章扉のブランド名などデッキ固有の指定は見本に無い）。"""

    def test_sample_all_themes(self):
        if not SAMPLE.exists():
            self.skipTest("見本が無い")
        for theme in ("default", "accenture", "acn-slide-master", "acn-technology-graphik"):
            d = Path(tempfile.mkdtemp(prefix="s3a_sample_")) / "d"
            shutil.copytree(SAMPLE, d, ignore=shutil.ignore_patterns("build"))
            j = json.loads((d / "deck.json").read_text(encoding="utf-8"))
            j["meta"]["theme"] = theme
            (d / "deck.json").write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
            subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), "--html"], capture_output=True, text=True, encoding="utf-8")
            r = subprocess.run([PY, str(TOOLS / "check_layout.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
            out = r.stdout + r.stderr
            m = re.search(r"contrast=(\d+)", out)
            self.assertIsNotNone(m, out[-400:])
            self.assertEqual(m.group(1), "0", f"{theme}: " + "\n".join(l for l in out.splitlines() if "contrast:" in l)[:800])
            self.assertIn("minfont=0", out, theme)
            shutil.rmtree(d.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

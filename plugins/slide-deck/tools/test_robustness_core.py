#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""頑健性（独立レビュー fin-S-01 / 02 / 04 / 07）: 大きさ系の数値の上限、反復の上限、合成の図解ブロックの row / col の事前検査、
行数の多い表の PPTX、巨大な画素数の画像。

実行: python3 -m unittest plugins/slide-deck/tools/test_robustness_core.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import deck_schema as ds  # noqa: E402
import proposal_engine as pe  # noqa: E402

PY = sys.executable


def deck_dir(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="rob_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def build(d, *args, timeout=30):
    return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


class SizeBounds(unittest.TestCase):
    def levels(self, **region):
        return [lvl for lvl, _ in ds.check_region_value(region, {"size": 20, "w": 100, "h": 50, "label_size": 18, "row_h": 40, "node_size": 14}, "style.body")]

    def test_text_size_upper_bound(self):
        for k in ("size", "label_size", "node_size"):
            self.assertEqual(self.levels(**{k: 2000}), [], k)
            self.assertEqual(self.levels(**{k: 1e6}), ["fail"], k)
            self.assertEqual(self.levels(**{k: 1e308}), ["fail"], k)
            self.assertEqual(self.levels(**{k: 2 ** 60}), ["fail"], k)
            self.assertEqual(self.levels(**{k: float("nan")}), ["fail"], k)
            self.assertEqual(self.levels(**{k: float("inf")}), ["fail"], k)

    def test_extent_upper_bound(self):
        for k in ("w", "h", "row_h"):
            self.assertEqual(self.levels(**{k: 100000}), [], k)
            self.assertEqual(self.levels(**{k: 100001}), ["fail"], k)
            self.assertEqual(self.levels(**{k: 1e308}), ["fail"], k)
        self.assertEqual(self.levels(x=-5000), [])
        self.assertEqual(self.levels(x=-1e6), ["fail"])

    def test_message_names_key_and_gives_a_fix(self):
        p = ds.check_region_value({"label_size": 1e6}, {"label_size": 18}, "style.body")
        self.assertIn("style.body.label_size", p[0][1])
        self.assertIn("2000", p[0][1])
        self.assertIn("→", p[0][1])

    def test_shipped_layout_values_are_inside_the_bounds(self):
        layout = json.loads((TOOLS.parent / "templates" / "layouts" / "default.json").read_text(encoding="utf-8"))
        bad = []
        for tname, regions in layout.get("types", {}).items():
            for rname, region in regions.items():
                if isinstance(region, dict):
                    nums = {k: v for k, v in region.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
                    for lvl, msg in ds.check_region_value(nums, region, f"{tname}.{rname}", check_unknown=False):
                        if lvl == "fail":
                            bad.append(msg)
        self.assertEqual(bad, [])

    def test_build_rejects_huge_size_quickly(self):
        t = time.time()
        d = deck_dir([{"type": "section", "title": "章", "style": {"title": {"size": 1e308}}}])
        r = build(d, "--html")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("style.title.size", r.stdout + r.stderr)
        self.assertLess(time.time() - t, 10)


class IterationCaps(unittest.TestCase):
    def test_fit_text_size_terminates_on_huge_cap(self):
        t = time.time()
        res = autofit.fit_text_size("あ" * 50, 400, 40, 1e308, 12, 1.2)
        self.assertLess(time.time() - t, 3)
        self.assertIn("size", res)
        res = autofit.fit_text_size("あ" * 50, 400, 40, 2.0 ** 60, 12, 1.2, step=1)
        self.assertIn("fits", res)

    def test_fit_text_size_same_result_for_normal_values(self):
        import ja_text
        res = autofit.fit_text_size("あ" * 40, 400, 60, 30, 12, 1.2)
        want = next((sz for sz in range(30, 11, -1) if ja_text.estimate_lines("あ" * 40, sz, 400, None, False) * sz * 1.2 <= 60.5), 12)
        self.assertEqual(res["size"], want)            # 従来どおり 1px ずつ下げて収まる最大
        self.assertTrue(res["fits"])

    def test_descending_is_bounded_and_unchanged_for_normal_values(self):
        self.assertEqual(pe.descending(14, 11), [14, 13, 12, 11])
        self.assertEqual(pe.descending(10, 12), [10])
        self.assertLessEqual(len(pe.descending(1e308, 12)), 402)
        self.assertLessEqual(len(pe.descending(2.0 ** 60, 12)), 402)


class CompositeDiagramRows(unittest.TestCase):
    def slide(self, row):
        return [{"type": "composite", "title": "t", "arrange": "main-side", "blocks": [
            {"type": "architecture", "heading": "構成", "nodes": [
                {"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": row, "col": 1}],
             "edges": [{"from": "a", "to": "b"}]},
            {"type": "bullets", "bullets": ["x"]}]}]

    def test_huge_row_fails_fast_with_the_same_limit_as_single_slide(self):
        for row in (20000000, 12345678901234567890, 40):
            t = time.time()
            r = build(deck_dir(self.slide(row)), "--html", timeout=20)
            self.assertNotEqual(r.returncode, 0, row)
            self.assertIn("行は 40 行までです", r.stdout + r.stderr)
            self.assertIn("1 つ目のブロック（architecture）", r.stdout + r.stderr)
            self.assertLess(time.time() - t, 10, row)

    def test_normal_rows_still_build(self):
        r = build(deck_dir(self.slide(1)), "--html")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TableRowHeights(unittest.TestCase):
    def test_pptx_row_heights_and_frame_height(self):
        from pptx import Presentation
        rows = [[f"行{i}の項目を確認する", str(i), "備考"] for i in range(25)]
        d = deck_dir([{"type": "table", "title": "t", "columns": ["項目", "数", "備考"], "rows": rows}])
        self.assertEqual(build(d, "--pptx").returncode, 0)
        prs = Presentation(str(d / "build" / "d.pptx"))
        gf = [s for s in prs.slides[0].shapes if s.has_table][0]
        hs = [r.height for r in gf.table.rows]
        self.assertEqual(len(hs), 26)
        self.assertEqual(gf.height, sum(hs), "枠の高さは行の高さの合計（1 行ずつ設定したときと同じ）")
        self.assertTrue(all(h > 0 for h in hs))

    def test_many_rows_build_is_fast(self):
        rows = [[f"行{i}の項目を確認して進める", str(i), "備考の文章を書く"] for i in range(300)]
        d = deck_dir([{"type": "table", "title": "t", "columns": ["項目", "数", "備考"], "rows": rows}])
        t = time.time()
        r = build(d, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.time() - t, 20)


class HugeImages(unittest.TestCase):
    def test_pixel_limit_message(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp(prefix="rob_img_"))
        Image.new("L", (100, 100), 5).save(d / "a.png")
        self.assertIsNone(ds.image_too_big(d / "a.png", "assets/a.png"))
        with mock.patch.object(ds, "MAX_IMAGE_PIXELS", 5000), mock.patch.dict(ds._IMAGE_SIZE_CACHE, {}, clear=True):
            msg = ds.image_too_big(d / "a.png", "assets/a.png")
        self.assertIn("画像が大きすぎます", msg)
        self.assertIn("100×100", msg)
        self.assertIn("縮小", msg)
        self.assertIsNone(ds.image_too_big(d / "missing.png"))
        (d / "b.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        self.assertIsNone(ds.image_too_big(d / "b.svg"))

    def _deck_with_image(self, slide, size):
        from PIL import Image
        d = deck_dir([slide])
        (d / "assets").mkdir()
        Image.new("L", size, 7).save(d / "assets" / "big.png")
        return d

    def test_every_route_fails_without_raw_warning(self):
        routes = {
            "image": {"type": "image", "title": "t", "path": "assets/big.png"},
            "image_text": {"type": "image_text", "title": "t", "path": "assets/big.png", "bullets": ["a"]},
            "background": {"type": "title", "title": "t", "background": {"image": "assets/big.png"}},
            "composite": {"type": "composite", "title": "t", "blocks": [{"type": "image", "path": "assets/big.png"}, {"type": "bullets", "bullets": ["a"]}]},
            "canvas": {"type": "canvas", "title": "t", "elements": [{"kind": "image", "path": "assets/big.png", "x": 0, "y": 0, "w": 200, "h": 100}]},
        }
        for name, slide in routes.items():
            with self.subTest(route=name):
                d = self._deck_with_image(slide, (12000, 9000))           # 1.08 億画素（PIL の警告しきい値も超える）
                r = build(d, "--html", timeout=40)
                out = r.stdout + r.stderr
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("画像が大きすぎます（12000×9000", out)
                self.assertNotIn("DecompressionBomb", out)
                self.assertFalse((d / "build" / "d.html").exists())

    def test_normal_image_still_builds(self):
        d = self._deck_with_image({"type": "image", "title": "t", "path": "assets/big.png"}, (800, 600))
        r = build(d, "--html")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()

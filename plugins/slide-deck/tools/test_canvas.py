#!/usr/bin/env python3
"""canvas 型（canvas_engine.py）と PPTX 取り込み（pptx_import.py）の回帰テスト（unittest）。

    python -m unittest discover -s tools -p "test_*.py"
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import canvas_engine as ce  # noqa: E402

PY = sys.executable


def _deck(slides):
    return {"meta": {"id": "t", "title": "t"}, "slides": slides}


SHAPES = [
    {"x": 10, "y": 20, "w": 200, "h": 40, "geom": "homePlate", "adj": {"adj": 13400}, "fill": "#F0E7FF",
     "line": {"color": "#7F7F7F", "width": 0.75},
     "text": {"anchor": "ctr", "paragraphs": [{"align": "ctr", "runs": [{"text": "要件定義", "size": 12}]}]}},
    {"x": 10, "y": 80, "w": 100, "h": 0, "geom": "straightConnector1",
     "line": {"color": "#000000", "width": 0.75, "dash": "dash", "tail": {"type": "triangle"}}},
    {"x": 300, "y": 20, "w": 100, "h": 40, "fill": {"pattern": "ltDnDiag", "fg": "#A100FF", "bg": "#FFFFFF"}},
    {"kind": "table", "x": 10, "y": 200, "w": 200, "h": 40, "cols": [100, 100],
     "rows": [{"h": 20, "cells": [{"fill": "#A100FF", "paragraphs": [{"runs": [{"text": "見出し", "size": 12, "bold": True, "color": "#FFFFFF"}]}]},
                                  {"paragraphs": [{"runs": [{"text": "値", "size": 12}]}], "borders": {"b": {"color": "#000000", "width": 4}}}]},
              {"h": 20, "cells": [{"span": 2, "paragraphs": [{"runs": [{"text": "結合", "size": 12}]}]}, {"merged": "h"}]}]},
    {"kind": "svg", "x": 500, "y": 20, "w": 40, "h": 40, "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><defs><linearGradient id="a"/></defs><rect width="10" height="10" fill="url(#a)" onclick="x()"/></svg>'},
    {"kind": "placeholder", "x": 600, "y": 20, "w": 100, "h": 60, "label": "画像（スクリーンショット）"},
]


class CanvasHtmlTest(unittest.TestCase):
    def test_shapes_render(self):
        html = ce.canvas_html({"elements": SHAPES})
        self.assertIn("要件定義", html)
        self.assertIn("<pattern", html)
        self.assertIn("stroke-dasharray", html)
        self.assertIn('colspan="2"', html)
        self.assertNotIn("onclick", html)  # SVG のイベント属性は除去する
        self.assertNotIn('id="a"', html)   # SVG の id は接頭辞付きに置き換える
        self.assertIn("画像（スクリーンショット）", html)

    def test_homeplate_text_rect_is_narrower(self):
        l, t, r, b = ce.text_rect({"geom": "homePlate", "w": 200, "h": 40, "adj": {"adj": 50000}})
        self.assertLess(r, 200)
        l, t, r, b = ce.text_rect({"geom": "flowChartDecision", "w": 200, "h": 40})
        self.assertEqual((l, t, r, b), (50, 10, 150, 30))

    def test_mixed_size_lines_are_split(self):
        p = {"runs": [{"text": "75.1", "size": 24}, {"br": True}, {"text": "(▲6.6)", "size": 12}]}
        parts = ce._split_lines(p)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[1]["runs"][0]["text"], "(▲6.6)")

    def test_table_border_compensated(self):
        html = ce.table_html(SHAPES[3])
        # 4px の下罫線の半分（2px）だけ下余白が減る（既定 4.8px → 2.8px）
        self.assertIn("padding:4.8px 9.6px 2.8px 9.6px", html)

    def test_validate_rejects_unknown_kind_and_script(self):
        errors = []

        def fail(msg):
            errors.append(msg)
            raise SystemExit(1)
        with self.assertRaises(SystemExit):
            ce.validate_canvas({"elements": [{"kind": "video", "x": 0, "y": 0}]}, 0, fail, lambda m: None)
        with self.assertRaises(SystemExit):
            ce.validate_canvas({"elements": [{"kind": "svg", "x": 0, "y": 0, "svg": "<svg><script>1</script></svg>"}]},
                               0, fail, lambda m: None)
        self.assertEqual(len(errors), 2)


class CanvasSanitizeTest(unittest.TestCase):
    """deck.json の値が HTML 属性・CSS・PPTX の XML へ素通しされないこと（取り込み元は信用しない）"""

    def _issues(self, els):
        issues = []
        ce.sanitize_elements(els, "elements", issues)
        return issues

    def test_svg_allowlist(self):
        s = ce.sanitize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" onload="x()">'
            '<script>alert(1)</script><foreignObject><div/></foreignObject>'
            '<a href="javascript:alert(1)"><rect/></a><image href="https://evil.example/x.png"/>'
            '<use xlink:href="#p"/><path id="p" d="M0 0" fill="url(#g)" style="fill:url(https://evil.example)"/></svg>')
        for bad in ("onload", "script", "foreignObject", "javascript", "evil", "<a ", "<image"):
            self.assertNotIn(bad, s)
        self.assertIn('<use href="#p"', s)
        self.assertIn('fill="url(#g)"', s)
        self.assertEqual(ce.sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg>&x;</svg>'), "")
        self.assertEqual(ce.sanitize_svg("<svg><rect></svg>"), "")
        self.assertEqual(ce.sanitize_svg("<div/>"), "")

    def test_bad_values_are_reported_and_neutralized(self):
        els = [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": 'red"/><x onload="1',
                "line": {"color": "#000000", "dash": 'x"', "tail": {"type": 'x"', "w": "huge"}},
                "text": {"anchor": 'ctr" foo="', "paragraphs": [{"align": "zz", "runs": [
                    {"text": "a", "color": "#12345", "font": ["Meiryo UI'\"><b>"]}]}]}},
               {"geom": "custom", "x": 0, "y": 0, "w": 1, "h": 1, "path": [{"cmds": [['M"/>', 0, 0], ["L", 1, 1]]}]},
               {"kind": "table", "x": 0, "y": 0, "cols": [10], "rows": [{"h": 10, "cells": [{"span": '2" evilspan="'}]}]}]
        issues = self._issues(els)
        self.assertGreaterEqual(len(issues), 8, issues)
        html = ce.canvas_html({"elements": els})
        for bad in ("onload", 'foo="', "<b>", "evilspan", 'M"'):
            self.assertNotIn(bad, html)
        from pptx import Presentation
        prs = Presentation()
        ce.add_canvas_to_pptx(prs.slides.add_slide(prs.slide_layouts[6]), els)  # 不正な XML なら parse_xml で例外

    def test_imported_values_pass(self):
        self.assertEqual(self._issues([e for e in SHAPES if e.get("kind") != "svg"]), [])

    def test_validate_fails_on_bad_color(self):
        with self.assertRaises(SystemExit):
            ce.validate_canvas({"elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "fill": "purple"}]}, 0,
                               lambda m: (_ for _ in ()).throw(SystemExit(1)), lambda m: None)


class CanvasBuildTest(unittest.TestCase):
    def test_build_html_and_pptx(self):
        with tempfile.TemporaryDirectory() as d:
            deck_dir = Path(d) / "t"
            deck_dir.mkdir()
            els = [e for e in SHAPES if e.get("kind") != "svg"]  # PPTX の SVG 画像化は Playwright 依存のため除外
            (deck_dir / "deck.json").write_text(json.dumps(_deck([
                {"type": "canvas", "title": "T", "background": "#FFFFFF", "elements": els},
                {"type": "bullets", "title": "通常スライド", "bullets": ["a"]}]), ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir)], capture_output=True, text=True,
                               encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            html = (deck_dir / "build" / "t.html").read_text(encoding="utf-8")
            self.assertIn('data-type="canvas"', html)
            self.assertIn(".cv-s{", html)
            from pptx import Presentation
            prs = Presentation(str(deck_dir / "build" / "t.pptx"))
            texts = [sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame]
            self.assertIn("要件定義", texts)

    def test_bad_background_fails(self):
        with tempfile.TemporaryDirectory() as d:
            deck_dir = Path(d) / "t"
            deck_dir.mkdir()
            (deck_dir / "deck.json").write_text(json.dumps(_deck([
                {"type": "canvas", "background": "purple", "elements": []}])), encoding="utf-8")
            r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir), "--html"], capture_output=True,
                               text=True, encoding="utf-8")
            self.assertNotEqual(r.returncode, 0)


class PptxImportTest(unittest.TestCase):
    def test_roundtrip(self):
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.util import Emu
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.pptx"
            prs = Presentation()
            prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
            s = prs.slides.add_slide(prs.slide_layouts[6])
            sh = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Emu(952500), Emu(952500), Emu(1905000), Emu(476250))
            sh.fill.solid()
            sh.fill.fore_color.rgb = RGBColor(0xA1, 0x00, 0xFF)
            sh.text_frame.text = "Plan"
            tb = s.shapes.add_table(2, 2, Emu(952500), Emu(2857500), Emu(3810000), Emu(762000)).table
            tb.cell(0, 0).text = "見出し"
            tb.cell(1, 1).text = "値"
            prs.save(str(src))
            deck_dir = Path(d) / "deck"
            r = subprocess.run([PY, str(TOOLS / "pptx_import.py"), str(src), "--into", str(deck_dir)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            deck = json.loads((deck_dir / "deck.json").read_text(encoding="utf-8"))
            els = deck["slides"][0]["elements"]
            chev = next(e for e in els if e.get("geom") == "chevron")
            self.assertEqual((chev["x"], chev["y"], chev["w"], chev["h"]), (100, 100, 200, 50))
            self.assertEqual(chev["fill"], "#A100FF")
            self.assertEqual(chev["text"]["paragraphs"][0]["runs"][0]["text"], "Plan")
            table = next(e for e in els if e.get("kind") == "table")
            self.assertEqual(table["rows"][0]["cells"][0]["paragraphs"][0]["runs"][0]["text"], "見出し")
            # 既定の表スタイル（中間スタイル2-アクセント1）の見出し行は太字・白文字になる
            run = table["rows"][0]["cells"][0]["paragraphs"][0]["runs"][0]
            self.assertTrue(run.get("bold"))

            # 既存 deck.json があると --confirm 無しでは書き込まない（丸ごと置き換えになるため）
            before = (deck_dir / "deck.json").read_bytes()
            r = subprocess.run([PY, str(TOOLS / "pptx_import.py"), str(src), "--into", str(deck_dir)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("--confirm", r.stderr)
            self.assertEqual((deck_dir / "deck.json").read_bytes(), before)
            self.assertFalse((deck_dir / "deck.json.bak").exists())
            r = subprocess.run([PY, str(TOOLS / "pptx_import.py"), str(src), "--into", str(deck_dir), "--confirm"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((deck_dir / "deck.json.bak").read_bytes(), before)


class PptxImportExcelTest(unittest.TestCase):
    def test_huge_range_is_rejected(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl 未導入")
        import io
        from pptx_import_excel import excel_table
        wb = openpyxl.Workbook()
        wb.active["A1"] = "x"
        wb.active["ZZ5000"] = "y"  # oleSize が無いので ws.dimensions（A1:ZZ5000）が表示範囲になる
        buf = io.BytesIO()
        wb.save(buf)
        with self.assertRaises(ValueError):
            excel_table(buf.getvalue(), 0, 0, 100, 100)


def _collect():
    errs = []

    def fail(msg):
        errs.append(msg)
    return errs, fail


class CanvasValidationTest(unittest.TestCase):
    """手書き JSON でトレースバックにならず、問題が全件まとめて出ること"""

    def test_all_problems_reported_at_once(self):
        errs, fail = _collect()
        ce.validate_canvas({"elements": [
            {"x": 0, "y": 0, "fill": "#FF0000"},                                  # w / h が無い
            {"x": 0, "y": 0, "w": "100", "h": 10},                                # 文字列の数値
            {"x": 0, "y": 0, "w": 10, "h": 10, "text": {"paragraphs": [{"runs": [{"text": "a", "size": "big"}]}]}},
            {"kind": "table", "x": 0, "y": 0},                                    # cols / rows が無い
            {"x": 0, "y": 0, "w": 1, "h": 1, "fill": "purple"},                   # 色
        ]}, 0, fail, lambda m: None)
        self.assertEqual(len(errs), 1)                                            # fail は 1 回（全件を 1 つにまとめる）
        msg = errs[0]
        for needle in ("elements[0].w", "elements[1].w", "size 'big'", "elements[3].cols", "purple"):
            self.assertIn(needle, msg)

    def test_invalid_inputs_do_not_raise_traceback(self):
        bad = [
            {"elements": "x"},
            {"elements": [1]},
            {"elements": [{"kind": "shape", "x": 0, "y": 0, "w": 1, "h": 1, "text": "abc"}]},
            {"elements": [{"kind": "backdrop", "x": 0, "y": 0, "w": 10, "h": 10, "grid": {"cols": 2, "rows": 2, "colors": ["#000000"]}}]},
            {"elements": [{"kind": "group", "children": "x"}]},
            {"elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "geom": "custom"}]},
            {"elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "text": {"insets": [1, 2], "paragraphs": []}}]},
        ]
        for sl in bad:
            errs, fail = _collect()
            ce.validate_canvas(sl, 0, fail, lambda m: None)
            self.assertTrue(errs, sl)

    def test_font_string_and_rgb_shorthand(self):
        els = [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "#abc",
                "text": {"paragraphs": [{"runs": [{"text": "a", "font": "Arial", "color": "#fff"}]}]}}]
        errs, fail = _collect()
        ce.validate_canvas({"elements": els}, 0, fail, lambda m: None)
        self.assertEqual(errs, [])
        self.assertIn("#AABBCC", ce.canvas_html({"elements": els}).upper())


class CanvasImageTest(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "assets").mkdir()
        Image.new("RGB", (400, 200), (200, 100, 50)).save(self.dir / "assets" / "p.png")

    def tearDown(self):
        self.tmp.cleanup()

    def _el(self, **kw):
        return dict({"kind": "image", "x": 10, "y": 20, "w": 200, "h": 200, "path": "assets/p.png"}, **kw)

    def test_path_checks(self):
        for bad in ("../x.png", "/etc/x.png", "C:\\x.png", "assets/a.exe", "assets/none.png", "", "assets/../../x.png"):
            self.assertIsNotNone(ce.check_image_path(bad, self.dir), bad)
        self.assertIsNone(ce.check_image_path("assets/p.png", self.dir))
        self.assertIsNone(ce.check_image_path("assets/anything.png", None))   # deck_dir なしは文字列の検査だけ

    def test_symlink_escape_is_rejected(self):
        outside = tempfile.TemporaryDirectory()
        try:
            from PIL import Image
            Image.new("RGB", (4, 4)).save(Path(outside.name) / "s.png")
            (self.dir / "assets" / "link.png").symlink_to(Path(outside.name) / "s.png")
            self.assertIn("外", ce.check_image_path("assets/link.png", self.dir))
        finally:
            outside.cleanup()

    def test_validate_reports_bad_image(self):
        errs, fail = _collect()
        ce.validate_canvas({"elements": [self._el(path="../x.png"), self._el(fit="stretch")]}, 0, fail, lambda m: None, self.dir)
        self.assertIn("..", errs[0])
        self.assertIn("fit", errs[0])

    def test_html_embeds_image_and_fit(self):
        html = ce.canvas_html({"elements": [self._el(fit="contain", alt="写真")]}, deck_dir=self.dir)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("object-fit:contain", html)
        self.assertIn('alt="写真"', html)
        # 画像を読めない（loader なし）ときは灰色の枠
        self.assertIn("cv-ph", ce.canvas_html({"elements": [self._el()]}))

    def test_custom_loader_is_used(self):
        calls = []

        def loader(rel, for_pptx, w=None, h=None):
            calls.append((rel, for_pptx, w, h))
            return self.dir / "assets" / "p.png"
        ce.canvas_html({"elements": [self._el()]}, image_source=loader)
        self.assertEqual(calls, [("assets/p.png", False, 200, 200)])

    def test_pptx_cover_crops_and_contain_fits(self):
        from pptx import Presentation
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(s, [self._el(), self._el(fit="contain", x=300)], deck_dir=self.dir)
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        self.assertEqual(len(pics), 2)
        cover, contain = pics
        # 400x200 の画像を 200x200 の枠に cover: 左右を 25% ずつ切り抜く
        self.assertAlmostEqual(cover.crop_left, 0.25, places=3)
        self.assertAlmostEqual(cover.crop_right, 0.25, places=3)
        # contain: 幅 200 に縮め、高さ 100 になって枠の中央に置く
        self.assertAlmostEqual(contain.width / 9525, 200, places=1)
        self.assertAlmostEqual(contain.height / 9525, 100, places=1)
        self.assertAlmostEqual(contain.top / 9525, 70, places=1)

    def test_default_loader_downsizes_large_images(self):
        from PIL import Image
        Image.new("RGB", (4000, 2000), (1, 2, 3)).save(self.dir / "assets" / "big.png")
        src = ce.default_image_source(self.dir)
        out = src("assets/big.png", False, 100, 50)
        self.assertTrue(str(out).endswith(".png") and ".img-cache" in str(out))
        with __import__("PIL.Image", fromlist=["Image"]).open(out) as im:
            self.assertLessEqual(max(im.size), 200)
        self.assertIsNone(src("../x.png", False))


class CanvasPptxEffectsTest(unittest.TestCase):
    def test_shadow_is_written_to_pptx(self):
        from pptx import Presentation
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        el = {"x": 10, "y": 10, "w": 100, "h": 50, "fill": "#0F3D6E",
              "shadow": {"dx": 3, "dy": 4, "blur": 8, "color": {"color": "#000000", "alpha": 0.4}}}
        ce.add_canvas_to_pptx(s, [el, dict(el, fill=None, line=None)])   # 塗りも線もない図形には付けない（HTML と同じ）
        xml = [sh._element.xml for sh in s.shapes]
        self.assertIn("<a:outerShdw", xml[0])
        self.assertIn('dist="47625"', xml[0])       # hypot(3, 4) = 5px = 47625 EMU
        self.assertIn('blurRad="76200"', xml[0])    # 8px
        self.assertIn('dir="3187806"', xml[0])      # atan2(4, 3) = 53.13 度
        self.assertIn("a:alpha", xml[0])
        self.assertNotIn("outerShdw", xml[1])

    def test_vert270_html_and_pptx(self):
        el = {"x": 0, "y": 0, "w": 60, "h": 200, "text": {"vert": "270", "paragraphs": [{"runs": [{"text": "Client", "size": 20}]}]}}
        self.assertIn("cv-vi270", ce.canvas_html({"elements": [el]}))
        from pptx import Presentation
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(s, [el, dict(el, text={"vert": True, "paragraphs": el["text"]["paragraphs"]})])
        xmls = [sh._element.xml for sh in s.shapes]
        self.assertIn('vert="vert270"', xmls[0])
        self.assertIn('vert="eaVert"', xmls[1])


class CanvasTransformTest(unittest.TestCase):
    def test_fit_elements_scales_geometry_text_and_lines(self):
        els = [{"x": 100, "y": 100, "w": 200, "h": 100, "line": {"color": "#000000", "width": 2},
                "shadow": {"dx": 4, "dy": 4, "blur": 8, "color": "#000000"},
                "text": {"insets": [10, 5, 10, 5], "paragraphs": [{"spaceAfter": 10, "marL": 20, "lineHeightPx": 40,
                                                                    "runs": [{"text": "a", "size": 24}]}]}},
               {"kind": "table", "x": 0, "y": 0, "cols": [100, 200], "rows": [{"h": 40, "cells": [
                   {"pad": [10, 4, 10, 4], "paragraphs": [{"runs": [{"text": "x", "size": 20}]}]}]}]},
               {"kind": "group", "rot": 10, "origin": [100, 100], "children": [{"x": 50, "y": 50, "w": 10, "h": 10}]},
               {"geom": "custom", "x": 0, "y": 0, "w": 100, "h": 50, "path": [{"cmds": [["M", 0, 0], ["L", 100, 50]]}]}]
        import copy
        orig = copy.deepcopy(els)
        out = ce.fit_elements(els, (640, 360, 320, 180))
        self.assertEqual(els, orig)                                  # 入力は変更しない
        e = out[0]
        self.assertEqual((e["x"], e["y"], e["w"], e["h"]), (665, 385, 50, 25))
        self.assertEqual(e["line"]["width"], 0.5)
        self.assertEqual(e["shadow"]["blur"], 2)
        self.assertEqual(e["text"]["insets"], [2.5, 1.25, 2.5, 1.25])
        p = e["text"]["paragraphs"][0]
        self.assertEqual((p["spaceAfter"], p["marL"], p["lineHeightPx"], p["runs"][0]["size"]), (2.5, 5, 10, 6))
        t = out[1]
        self.assertEqual((t["cols"], t["rows"][0]["h"], t["rows"][0]["cells"][0]["pad"]), ([25, 50], 10, [2.5, 1, 2.5, 1]))
        self.assertEqual(out[2]["origin"], [665, 385])
        self.assertEqual((out[2]["children"][0]["x"], out[2]["children"][0]["w"]), (652.5, 2.5))
        self.assertEqual(out[3]["path"][0]["cmds"][1], ["L", 25, 12.5])
        # 結果は描画できる
        ce.canvas_html({"elements": out})

    def test_non_uniform_stretch_uses_smaller_scale_for_text(self):
        out = ce.fit_elements([{"x": 0, "y": 0, "w": 1280, "h": 720, "text": {"paragraphs": [{"runs": [{"text": "a", "size": 40}]}]}}],
                              (0, 0, 640, 720), mode="stretch")
        self.assertEqual((out[0]["w"], out[0]["h"]), (640, 720))
        self.assertEqual(out[0]["text"]["paragraphs"][0]["runs"][0]["size"], 20)


class PptxImportExtrasTest(unittest.TestCase):
    def _make(self, d, w, h, vert=None):
        from pptx import Presentation
        from pptx.util import Emu
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(w), Emu(h)
        s = prs.slides.add_slide(prs.slide_layouts[6])
        tb = s.shapes.add_textbox(Emu(952500), Emu(952500), Emu(1905000), Emu(1905000))
        tb.text_frame.text = "縦"
        if vert:
            tb.text_frame._txBody.bodyPr.set("vert", vert)
        src = Path(d) / "s.pptx"
        prs.save(str(src))
        return src

    def test_vert270_is_kept(self):
        import pptx_import as pi
        with tempfile.TemporaryDirectory() as d:
            sl = pi.Importer(self._make(d, 12192000, 6858000, "vert270")).convert({1})[0]
            self.assertEqual(sl["elements"][0]["text"]["vert"], "270")
            sl = pi.Importer(self._make(d, 12192000, 6858000, "eaVert")).convert({1})[0]
            self.assertIs(sl["elements"][0]["text"]["vert"], True)

    def test_non_16_9_is_scaled_into_canvas(self):
        import pptx_import as pi
        with tempfile.TemporaryDirectory() as d:
            # 4:3（9144000x6858000 = 960x720px）は縦横比を保って 1280x720 の中央に置く
            e = pi.Importer(self._make(d, 9144000, 6858000)).convert({1})[0]["elements"][0]
            self.assertEqual((e["x"], e["w"]), (260, 200))
            # 10in x 5.625in の 16:9（960x540px）は 4/3 倍に拡大する
            e = pi.Importer(self._make(d, 9144000, 5143500)).convert({1})[0]["elements"][0]
            self.assertAlmostEqual(e["x"], 100 * 4 / 3, places=1)
            self.assertAlmostEqual(e["w"], 200 * 4 / 3, places=1)

    def test_tag_adds_origin_and_placeholder_type(self):
        import pptx_import as pi
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as d:
            prs = Presentation()
            s = prs.slides.add_slide(prs.slide_layouts[1])
            s.shapes.title.text = "題"
            s.placeholders[1].text = "本文"
            src = Path(d) / "p.pptx"
            prs.save(str(src))
            els = pi.Importer(src, tag=True).convert({1})[0]["elements"]
            self.assertTrue(all(e.get("src") == "slide" for e in els))
            self.assertEqual({e["ph"]["type"] for e in els}, {"title", "body"})
            plain = pi.Importer(src).convert({1})[0]["elements"]
            self.assertFalse(any("ph" in e or "src" in e for e in plain))   # 既定では付けない（取り込み結果は変わらない）


class CanvasReviewFixTest(unittest.TestCase):
    """レビュー指摘（C-02 制御文字 / C-04 cover の縮小 / A-06 型の検証 / C-01 負の大きさ）の回帰テスト"""

    def _shape(self, **kw):
        return dict({"kind": "shape", "x": 0, "y": 0, "w": 100, "h": 50}, **kw)

    def test_xml_illegal_chars_do_not_break_pptx_or_html(self):
        from pptx import Presentation
        bad = "A\x0cB\x00C\x0bD\x08E\ud800F"
        el = self._shape(name="n" + bad, alt="a" + bad, text={"paragraphs": [{"runs": [{"text": bad, "size": 20}]}]})
        self.assertEqual(ce.clean_text(bad), "ABCDEF")
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(slide, [el])            # 例外にならない
        texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]
        self.assertEqual(texts, ["ABCDEF"])
        html = ce.canvas_html({"elements": [el]})
        self.assertNotIn("\x0c", html)
        self.assertIn("ABCDEF", html)
        self.assertEqual(ce.validate_canvas_problems({"elements": [el]}), [])      # エラーにはせず黙って落とす
        self.assertEqual(ce.clean_text("改行\n\tタブ"), "改行\n\tタブ")            # 普通の空白文字は残す

    def test_negative_size_is_an_error(self):
        probs = ce.validate_canvas_problems({"elements": [self._shape(w=-5)]})
        self.assertEqual(len(probs), 1)
        self.assertIn("elements[0].w", probs[0])
        self.assertIn("→", probs[0])
        self.assertEqual(ce.validate_canvas_problems({"elements": [self._shape(h=0)]}), [])

    def test_style_types_are_reported_with_element_and_key(self):
        cases = {"line": "red", "shadow": "x", "fill": 5}
        for key, val in cases.items():
            probs = ce.validate_canvas_problems({"elements": [self._shape(**{key: val})]})
            self.assertEqual(len(probs), 1, (key, probs))
            self.assertIn(f"elements[0].{key}", probs[0])
        probs = ce.validate_canvas_problems({"elements": [self._shape(shadow={"color": 5})]})
        self.assertIn("elements[0].shadow.color", probs[0])
        probs = ce.validate_canvas_problems({"elements": [self._shape(
            text={"paragraphs": [{"runs": [{"text": "a", "font": 5}]}]})]})
        self.assertIn("runs[0].font", probs[0])
        # 正しい形は通る（font は文字列でも配列でもよい）
        ok = self._shape(line={"color": "#333333", "width": 2}, shadow={"dx": 0, "dy": 2, "blur": 4, "color": "#000000"},
                         fill="#ABC", text={"paragraphs": [{"runs": [{"text": "a", "font": "Arial"}, {"text": "b", "font": ["Meiryo"]}]}]})
        self.assertEqual(ce.validate_canvas_problems({"elements": [ok]}), [])

    def test_cover_shrink_limit_uses_needed_scale(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "assets").mkdir()
            Image.new("RGB", (8000, 1000), (10, 120, 200)).save(d / "assets" / "pano.png")
            src = ce.default_image_source(d)
            self.assertTrue(src.accepts_fit)
            cover = src("assets/pano.png", False, 300, 300, "cover")
            with Image.open(cover) as im:
                # 高さ 300 の枠を埋めるのに必要な倍率 0.3 の 2 倍（0.6）を残す → 高さは 600 近く（上限 2560 で長辺が決まる）
                self.assertGreaterEqual(im.size[1], 300)
                self.assertEqual(im.size[0], 2560)
            contain = src("assets/pano.png", False, 300, 300, "contain")
            with Image.open(contain) as im:
                self.assertEqual(im.size, (600, 75))                                  # contain は従来どおり
            # 4 引数だけの関数（build_deck 側の image_source）にも fit を押し付けない
            seen = []
            legacy = lambda rel, pp, w=None, h=None: seen.append((rel, pp, w, h)) or None   # noqa: E731
            ce.image_html({"kind": "image", "x": 0, "y": 0, "w": 30, "h": 30, "path": "assets/pano.png", "fit": "cover"}, legacy)
            self.assertEqual(seen, [("assets/pano.png", False, 30, 30)])



if __name__ == "__main__":
    unittest.main()

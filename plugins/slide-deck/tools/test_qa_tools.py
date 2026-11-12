"""検証ツール群（verify_pptx / check_pptx / preview_deck / deck_metrics / check_diagram / compare_ref）の単体テスト。"""
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import check_pptx  # noqa: E402
import deck_metrics  # noqa: E402
import preview_deck  # noqa: E402
import verify_pptx  # noqa: E402

try:
    from pptx import Presentation
except ImportError:  # pragma: no cover
    Presentation = None
try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def make_pptx(path: Path, props=True, notes=False, n=2):
    prs = Presentation()
    for _ in range(n):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        if notes:
            s.notes_slide.notes_text_frame.text = "メモ"
    if props:
        cp = prs.core_properties
        cp.title = "テストデッキ"
        cp.author = "tester"
        cp.last_modified_by = "tester"
        cp.created = datetime.datetime(2026, 11, 1)
        cp.modified = datetime.datetime(2026, 11, 1)
    prs.save(str(path))


@unittest.skipIf(Presentation is None, "python-pptx が無い")
class VerifyPptxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_import_has_no_side_effects(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import verify_pptx; print('ok')" % str(TOOLS)],
                           capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "ok")
        self.assertEqual(r.stderr, "")

    def test_good_file_passes(self):
        p = self.dir / "ok.pptx"
        make_pptx(p)
        self.assertEqual(verify_pptx.verify(p), [])

    def test_missing_file(self):
        self.assertTrue(verify_pptx.verify(self.dir / "none.pptx"))

    def test_not_a_zip(self):
        p = self.dir / "bad.pptx"
        p.write_bytes(b"not a zip at all")
        problems = verify_pptx.verify(p)
        self.assertEqual(len(problems), 1)
        self.assertIn("zip", problems[0])

    def test_notes_are_rejected(self):
        p = self.dir / "notes.pptx"
        make_pptx(p, notes=True)
        problems = verify_pptx.verify(p)
        self.assertTrue(any("ノート" in x and "枚目" in x for x in problems), problems)
        self.assertTrue(any("部品" in x for x in problems), problems)

    def test_default_properties_are_rejected(self):
        p = self.dir / "props.pptx"
        make_pptx(p, props=False)
        problems = verify_pptx.verify(p)
        self.assertTrue(any("title" in x for x in problems))
        self.assertTrue(any("Steve Canny" in x for x in problems))
        self.assertTrue(any("2013" in x for x in problems))
        self.assertEqual(verify_pptx.verify(p, check_props=False), [])

    def test_malformed_slide_xml(self):
        src = self.dir / "src.pptx"
        make_pptx(src)
        dst = self.dir / "broken.pptx"
        with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
            for it in zi.infolist():
                data = zi.read(it.filename)
                if it.filename == "ppt/slides/slide1.xml":
                    data = data[:-20]
                zo.writestr(it, data)
        problems = verify_pptx.verify(dst)
        self.assertTrue(any("整形式" in x and "slide1.xml" in x for x in problems), problems)

    def _corrupt_copy(self, name, mode):
        """slide1.xml の圧縮データの先頭を潰した pptx を作る（zlib.error になる破損）。"""
        src = self.dir / "src.pptx"
        make_pptx(src)
        dst = self.dir / name
        raw = bytearray(src.read_bytes())
        with zipfile.ZipFile(src) as zf:
            info = zf.getinfo("ppt/slides/slide1.xml")
            # ローカルヘッダ（30 バイト＋ファイル名＋extra）の直後が圧縮データ
            off = info.header_offset + 30 + len(info.filename.encode()) + int.from_bytes(raw[info.header_offset + 28:info.header_offset + 30], "little")
        if mode == "data":
            for k in range(8):    # 先頭の数バイトを潰して zlib ストリームを確実に壊す
                raw[off + k] ^= 0xFF
        dst.write_bytes(bytes(raw))
        return dst

    def test_corrupt_compressed_part_reports_problem_not_traceback(self):
        dst = self._corrupt_copy("corrupt.pptx", "data")
        problems = verify_pptx.verify(dst)
        self.assertTrue(any("壊れています" in x and "slide1.xml" in x and "やり直す" in x for x in problems), problems)
        r = subprocess.run([sys.executable, str(TOOLS / "verify_pptx.py"), str(dst)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NG:", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_crc_mismatch_reports_problem(self):
        src = self.dir / "src.pptx"
        make_pptx(src)
        dst = self.dir / "crc.pptx"
        with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as zo:
            for it in zi.infolist():
                zo.writestr(it.filename, zi.read(it.filename))
        raw = bytearray(dst.read_bytes())
        i = raw.index(b"<p:sld")
        raw[i + 8] ^= 0x01     # 無圧縮の中身を 1 ビット変える（CRC が合わなくなる）
        dst.write_bytes(bytes(raw))
        problems = verify_pptx.verify(dst)
        self.assertTrue(any("壊れています" in x for x in problems), problems)

    def test_cli_exit_codes(self):
        ok = self.dir / "ok.pptx"
        make_pptx(ok)
        bad = self.dir / "bad.pptx"
        make_pptx(bad, props=False)
        self.assertEqual(subprocess.run([sys.executable, str(TOOLS / "verify_pptx.py"), str(ok)], capture_output=True).returncode, 0)
        r = subprocess.run([sys.executable, str(TOOLS / "verify_pptx.py"), str(bad)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NG:", r.stdout)


class CheckPptxTests(unittest.TestCase):
    def test_missing_tools_message(self):
        self.assertEqual(check_pptx.missing_tools("/x/soffice", "/x/pdftoppm"), [])
        m = check_pptx.missing_tools(None, None)
        self.assertEqual(len(m), 2)
        self.assertIn("soffice", m[0])
        self.assertIn("pdftoppm", m[1])

    def test_rank_scores(self):
        r = check_pptx.rank_scores({1: 2.0, 2: 9.5, 3: 8.0, 4: 3.0}, 8.0)
        self.assertEqual([x[0] for x in r], [2, 3, 4, 1])
        self.assertEqual([x[2] for x in r], [True, True, False, False])

    def test_page_number(self):
        self.assertEqual(check_pptx.page_number(Path("page-07.png")), 7)
        self.assertEqual(check_pptx.page_number(Path("page-123.png")), 123)
        self.assertIsNone(check_pptx.page_number(Path("other.png")))

    def test_exits_zero_when_tools_missing(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "deck.json").write_text(json.dumps({"meta": {"id": "x"}, "slides": []}), encoding="utf-8")
            orig = (check_pptx.find_soffice, check_pptx.find_pdftoppm)
            check_pptx.find_soffice = lambda: None
            check_pptx.find_pdftoppm = lambda: None
            try:
                import contextlib
                import io
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    self.assertEqual(check_pptx.main([str(dd)]), 0)
                self.assertIn("soffice", buf.getvalue())
            finally:
                check_pptx.find_soffice, check_pptx.find_pdftoppm = orig

    @unittest.skipIf(Image is None, "pillow が無い")
    def test_compare_deck_writes_side_by_side(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            pages = {}
            for n, col in ((1, "white"), (2, "black")):
                Image.new("RGB", (1280, 720), "white").save(prev / f"slide-{n:02d}.png")
                p = dd / f"page-{n}.png"
                Image.new("RGB", (1280, 720), col).save(p)
                pages[n] = p
            res = check_pptx.compare_deck(dd, pages, dd / "build" / "pptx-compare", 8.0)
            self.assertAlmostEqual(res["scores"][1], 0.0)
            self.assertGreater(res["scores"][2], 200)
            self.assertEqual(res["ranked"][0][0], 2)
            with Image.open(dd / "build" / "pptx-compare" / "cmp-02.png") as im:
                self.assertGreaterEqual(im.width, 2560)


class PreviewDeckTests(unittest.TestCase):
    def test_remove_stale_pngs(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            for n in (1, 2, 3, 14, 15):
                (dd / f"slide-{n:02d}.png").write_bytes(b"x")
            (dd / "notes.txt").write_text("keep", encoding="utf-8")
            removed = preview_deck.remove_stale_pngs(dd, 3)
            self.assertEqual(removed, ["slide-14.png", "slide-15.png"])
            self.assertEqual(sorted(p.name for p in dd.iterdir()), ["notes.txt", "slide-01.png", "slide-02.png", "slide-03.png"])


class DeckMetricsTests(unittest.TestCase):
    def test_header_keeps_full_deck_name(self):
        self.assertEqual(deck_metrics._short("template-sample"), "template-sample")
        self.assertTrue(deck_metrics._short("x" * 40).endswith("…"))

    def test_non_display_keys_not_counted(self):
        s = {"type": "cards", "title": "t", "cards": [{"heading": "見出し", "icon": "とてもながいアイコン名" * 5}]}
        texts = deck_metrics.display_texts(s)
        self.assertIn("見出し", texts)
        self.assertFalse(any("アイコン" in t for t in texts))


class CheckDiagramNumberingTests(unittest.TestCase):
    def test_numbers_follow_preview_png_and_report_src(self):
        # swimlane の直前に凡例ページが自動挿入されるので、PNG の番号は deck.json の番号より 1 つ多い
        deck = {"meta": {"id": "d", "title": "D"}, "slides": [
            {"type": "bullets", "title": "a", "bullets": ["x"]},
            {"type": "architecture", "title": "A", "cols": 1,
             "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": 0, "col": 3}]},
            {"type": "swimlane", "title": "s", "lanes": [{"id": "l", "label": "L"}],
             "steps": [{"id": "t1", "lane": "l", "label": "x", "col": 0}]}]}
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            out = dd / "r.json"
            r = subprocess.run([sys.executable, str(TOOLS / "check_diagram.py"), str(dd), "--json", str(out)],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            data = json.loads(out.read_text(encoding="utf-8"))
            rows = {e["type"]: e for e in data["slides"]}
            # swimlane の前には凡例ページが入る → PNG の番号は 4、deck.json では 3 枚目
            sw = rows["swimlane"]
            self.assertEqual((sw["index"], sw["src"]), (4, 3))
            self.assertEqual((rows["architecture"]["index"], rows["architecture"]["src"]), (2, 2))
            # --slides は PNG の番号で選ぶ
            only = subprocess.run([sys.executable, str(TOOLS / "check_diagram.py"), str(dd), "--slides", "4"],
                                  cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertIn("図解スライド 1 枚", only.stdout)
            bad = subprocess.run([sys.executable, str(TOOLS / "check_diagram.py"), str(dd), "--slides", "99"],
                                 cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(bad.returncode, 1)

class SmallToolsTests(unittest.TestCase):
    """contact_sheet / export_pdf / check_svg_fonts の、道具なしで確かめられる部分（import 副作用・探索・入力エラー・SVG なし）。"""

    def run_tool(self, name, *args):
        return subprocess.run([sys.executable, str(TOOLS / name), *args], capture_output=True, text=True, encoding="utf-8")

    def test_import_has_no_side_effects(self):
        code = ("import sys; sys.path.insert(0, %r); import export_pdf, check_svg_fonts; print('ok')" % str(TOOLS))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "ok")

    def test_export_pdf_find_soffice_uses_path_then_candidates(self):
        import unittest.mock as mock
        import export_pdf
        with mock.patch.object(export_pdf.shutil, "which", side_effect=lambda n: "/x/soffice" if n == "soffice" else None):
            self.assertEqual(export_pdf.find_soffice(), "/x/soffice")
        with mock.patch.object(export_pdf.shutil, "which", return_value=None), \
                mock.patch.object(export_pdf.Path, "exists", return_value=False):
            self.assertIsNone(export_pdf.find_soffice())
        with mock.patch.object(export_pdf.shutil, "which", return_value=None), \
                mock.patch.object(export_pdf.Path, "exists", lambda self: str(self) == export_pdf.MACOS_CANDIDATES[0]):
            self.assertEqual(export_pdf.find_soffice(), export_pdf.MACOS_CANDIDATES[0])

    def test_export_pdf_manual_steps_mention_alternatives(self):
        import export_pdf
        self.assertIn("PowerPoint", export_pdf.MANUAL_STEPS)
        self.assertIn("LibreOffice", export_pdf.MANUAL_STEPS)

    def test_missing_deck_dir_fails_with_message_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            for tool in ("export_pdf.py", "contact_sheet.py"):
                r = self.run_tool(tool, str(Path(d) / "none"))
                self.assertNotEqual(r.returncode, 0, tool)
                self.assertNotIn("Traceback", r.stderr, tool)

    def test_check_svg_fonts_without_svgs_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_tool("check_svg_fonts.py", d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("SVGなし", r.stdout)

    def test_contact_sheet_label_font_and_total(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("pillow が無い")
        import contact_sheet
        self.assertIsNotNone(contact_sheet._load_label_font(14))
        with tempfile.TemporaryDirectory() as d:
            deck = {"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "a", "bullets": ["x"]},
                                                       {"type": "bullets", "title": "b", "bullets": ["y"]}]}
            (Path(d) / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(contact_sheet._slide_total(Path(d), deck), 2)


if __name__ == "__main__":
    unittest.main()

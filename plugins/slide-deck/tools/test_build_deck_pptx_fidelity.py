"""PPTX の忠実度（core-2）のテスト: 行送りの固定値・影なし・自動調整なし・文書プロパティ・表・検証。"""
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402

try:
    from pptx import Presentation
except ImportError:   # python-pptx が無い環境では丸ごと飛ばす
    Presentation = None


def build(deck: dict, files=None):
    """deck を一時フォルダでビルドし (pptx のパス, html の文字列, 一時フォルダ) を返す。"""
    tmp = tempfile.TemporaryDirectory()
    d = Path(tmp.name)
    (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
    deck_, theme, layout = b.load_deck(d)
    b.validate_deck(deck_, layout, theme, d)
    deck_ = b.expand_slides(deck_, layout)
    deck_ = b.apply_line_balance(deck_, layout)
    out = d / "o.pptx"
    b.build_pptx(deck_, theme, layout, d, out)
    html = d / "o.html"
    b.build_html(deck_, theme, layout, d, html)
    return out, html.read_text(encoding="utf-8"), tmp


def slide_xml(pptx: Path, n=1) -> str:
    with zipfile.ZipFile(pptx) as z:
        return z.read(f"ppt/slides/slide{n}.xml").decode("utf-8")


SAMPLE = {
    "meta": {"id": "t", "title": "検証デッキ", "subtitle": "副題", "author": "山田 太郎"},
    "slides": [
        {"type": "bullets", "title": "箇条書き", "lead": "リード",
         "bullets": ["親1", {"text": "親2", "children": ["子A", "子B"]}, "親3"]},
        {"type": "table", "title": "表", "columns": ["項目", "内容"],
         "rows": [["a", "1 行目\n2 行目"], ["b", "短い"]]},
        {"type": "steps", "title": "手順", "steps": [{"label": "A", "items": ["x"]}, {"label": "B", "items": ["y"]}]},
        {"type": "quote", "text": "引用文", "attribution": "誰か"},
        {"type": "code", "title": "コード", "code": "print(1)\nprint(2)"},
    ],
}


@unittest.skipIf(Presentation is None, "python-pptx が無い")
class PptxFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pptx, cls.html, cls._tmp = build(SAMPLE)
        with zipfile.ZipFile(cls.pptx) as z:
            cls.parts = {n: z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".xml")}
        cls.slides = [cls.parts[f"ppt/slides/slide{i}.xml"] for i in range(1, 6)]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # --- 1. 行間 ---
    def test_line_spacing_is_fixed_points_everywhere(self):
        for i, xml in enumerate(self.slides, 1):
            self.assertNotIn("spcPct", xml, f"slide{i}: 行送りが倍率（spcPct）のまま")
        self.assertIn("<a:spcPts", self.slides[0])
        self.assertIn("<a:spcPts", self.slides[1])   # 表のセル

    def test_line_spacing_equals_px_times_line_height(self):
        prs = Presentation(str(self.pptx))
        layout = b.load_json(b.ROOT / "templates" / "layouts" / "default.json")
        st = b.resolve_style(layout, SAMPLE, SAMPLE["slides"][0])["body"]
        want = round(st["size"] * st["line_height"] * 0.75 * 100)
        vals = set()
        for sp in prs.slides[0].shapes:
            if sp.has_text_frame and "親1" in sp.text_frame.text:
                for p in sp.text_frame.paragraphs:
                    ls = p.line_spacing
                    vals.add(round(ls.pt * 100))
        self.assertIn(want, vals)

    def test_child_bullet_line_height_matches_parent(self):
        # HTML の子 ul は親の line-height を継承する（以前は PPTX だけ -0.15 していた）
        prs = Presentation(str(self.pptx))
        layout = b.load_json(b.ROOT / "templates" / "layouts" / "default.json")
        st = b.resolve_style(layout, SAMPLE, SAMPLE["slides"][0])["body"]
        for sp in prs.slides[0].shapes:
            if sp.has_text_frame and "子A" in sp.text_frame.text:
                for p in sp.text_frame.paragraphs:
                    if p.text == "子A":
                        self.assertEqual(round(p.line_spacing.pt * 100),
                                         round(st["child_size"] * st["line_height"] * 0.75 * 100))
                        return
        self.fail("子項目の段落が見つからない")

    def test_proposal_engine_paragraphs_carry_fixed_line_height(self):
        import proposal_engine as pe
        ctx = pe.Ctx({"colors": {"text": "#000000"}, "fonts": {"body": "Meiryo UI"}})
        p = ctx.para("あ", 20, "text", lh=1.15)
        self.assertAlmostEqual(p["lineHeightPx"], 20 * pe.LINE_H * 1.15, places=1)

    # --- 2. 影 ---
    def test_no_shadow_anywhere(self):
        theme = self.parts["ppt/theme/theme1.xml"]
        self.assertNotIn("outerShdw", theme)
        for xml in self.slides:
            self.assertEqual(set(re.findall(r'<a:effectRef idx="(\d)"', xml)) - {"0"}, set())

    # --- 3. 自動調整 ---
    def test_no_shape_autofit(self):
        for xml in self.slides:
            self.assertNotIn("spAutoFit", xml)
        self.assertIn("<a:noAutofit/>", self.slides[0])

    # --- 4. 文書プロパティ・言語 ---
    def test_core_properties_from_meta(self):
        prs = Presentation(str(self.pptx))
        cp = prs.core_properties
        self.assertEqual(cp.title, "検証デッキ")
        self.assertEqual(cp.author, "山田 太郎")
        self.assertEqual(cp.last_modified_by, "山田 太郎")
        self.assertNotIn("Steve Canny", {cp.author, cp.last_modified_by})
        self.assertGreater(cp.created.year, 2020)
        self.assertEqual(cp.comments, "")
        with zipfile.ZipFile(self.pptx) as z:
            self.assertFalse([n for n in z.namelist() if "thumbnail" in n])

    def test_runs_are_japanese(self):
        for xml in self.slides:
            runs = re.findall(r"<a:rPr[^>]*>", xml)
            self.assertTrue(runs)
            self.assertTrue(all('lang="ja-JP"' in r for r in runs), runs[:3])

    # --- 5. 表 ---
    def test_table_style_borders_and_margins(self):
        xml = self.slides[1]
        self.assertIn("{2D5ABB26-0587-4C30-8999-92F81FD0307C}", xml)      # スタイルなし・グリッドなし
        self.assertNotIn("5C22544A", xml)
        layout = b.load_json(b.ROOT / "templates" / "layouts" / "default.json")
        pad_y = b.resolve_style(layout, SAMPLE, SAMPLE["slides"][1])["table"]["pad_y"]
        self.assertIn(f'marT="{int(round(pad_y * 9525))}"', xml)
        # 本文の各行に下罫線（実線）がある。ヘッダーは線なし
        self.assertEqual(len(re.findall(r"<a:lnB [^>]*><a:solidFill>", xml)), 4)   # 2 行 × 2 列
        self.assertIn("<a:lnL w=\"0\"><a:noFill/>", xml)

    def test_table_cell_newline_in_both_outputs(self):
        self.assertIn("1 行目<br>2 行目", self.html)
        self.assertIn("<a:br>", self.slides[1].replace("<a:br/>", "<a:br>"))

    def test_table_auto_widths(self):
        tr = {"w": 1000, "pad_x": 16, "header_size": 19, "cell_size": 17}
        w = b.table_auto_widths(["短", "長い見出しの列"], [["a", "あ" * 30], ["b", "い" * 28]], tr)
        self.assertAlmostEqual(sum(w), 1000, places=3)
        self.assertLess(w[0], w[1])
        self.assertGreater(w[0], 2 * 16)                  # 余白より広い
        # 内容が極端に長い列があっても、短い列を 1 文字幅より狭くしない
        w = b.table_auto_widths(["A", "B"], [["x", "あ" * 400]], tr)
        self.assertAlmostEqual(sum(w), 1000, places=3)
        self.assertGreater(w[0], 16 * 2 + 17 * 0.5)
        self.assertEqual(b.table_auto_widths([], [], tr), [])

    def test_pptx_table_uses_auto_widths_when_unspecified(self):
        prs = Presentation(str(self.pptx))
        tbl = [sh for sh in prs.slides[1].shapes if sh.has_table][0].table
        widths = [c.width for c in tbl.columns]
        self.assertNotEqual(widths[0], widths[1])         # 等分ではない
        self.assertAlmostEqual(sum(widths) / 9525, 1136, delta=2)

    # --- 7. 値の食い違い ---
    def test_steps_header_has_only_top_corners_rounded(self):
        self.assertIn('prst="round2SameRect"', self.slides[2])

    # --- 6. ビルド後の検証 ---
    def test_verify_fails_on_broken_file(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "x.pptx"
            bad.write_bytes(b"not a zip")
            with self.assertRaises(SystemExit) as cm:
                b._verify_saved_pptx(bad)
            self.assertIn("検証に失敗", str(cm.exception))

    def test_verify_passes_on_built_file(self):
        b._verify_saved_pptx(self.pptx)   # 例外にならない


if __name__ == "__main__":
    unittest.main()

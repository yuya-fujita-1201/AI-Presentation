"""check_visual（本文の空白帯・似たスライドの連続・古い PNG）のテスト。合成した PNG で判定だけを確かめる。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None

import check_visual  # noqa: E402


def _png(path: Path, lines_until: int, stripes: bool = False):
    im = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((60, 40, 900, 90), fill="black")              # タイトル
    for y in range(160, lines_until, 40):                       # 本文の行
        d.rectangle((60, y, 1100, y + 18), fill="black")
    if stripes:
        for x in range(0, 1280, 80):
            d.rectangle((x, 130, x + 30, 650), fill=(30, 30, 30))
    im.save(path)


@unittest.skipIf(Image is None, "pillow が無い")
class CheckVisualTests(unittest.TestCase):
    def test_empty_bottom_and_similar(self):
        deck = {"meta": {"title": "t"}, "slides": [
            {"type": "bullets", "title": "a", "bullets": ["x"]},
            {"type": "bullets", "title": "b", "bullets": ["x"]},
            {"type": "table", "title": "c", "columns": ["a"], "rows": [["1"]]},
            {"type": "section", "title": "d"},
        ]}
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            _png(prev / "slide-01.png", 220)                    # 本文が上だけ → 下が空
            _png(prev / "slide-02.png", 220)                    # 1 枚目と同じ見た目
            _png(prev / "slide-03.png", 640, stripes=True)      # 下まで埋まっている
            _png(prev / "slide-04.png", 200)                    # 章扉は空白でよい
            rows, warns = check_visual.analyze(dd)
        self.assertEqual(len(rows), 4)
        joined = "\n".join(warns)
        self.assertIn("1枚目（type=bullets）: [empty-bottom]", joined)
        self.assertIn("2枚目（type=bullets）: [similar]", joined)
        self.assertNotIn("3枚目", joined)
        self.assertNotIn("4枚目", joined)

    def test_rows_map_back_to_deck_json(self):
        # swimlane の直前には凡例ページが自動挿入されるので、PNG の番号と deck.json の並びがずれる
        deck = {"meta": {"title": "t"}, "slides": [
            {"type": "bullets", "title": "a", "bullets": ["x"]},
            {"type": "swimlane", "title": "b", "lanes": [], "steps": []},
            {"type": "closing", "title": "c"},
        ]}
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            for i in range(1, 5):
                _png(prev / f"slide-{i:02d}.png", 640, stripes=i % 2 == 0)
            rows, _ = check_visual.analyze(dd)
        self.assertEqual([(r["slide"], r["type"], r["src"]) for r in rows],
                         [(1, "bullets", 1), (2, "swimlane_legend", None), (3, "swimlane", 2), (4, "closing", 3)])
        self.assertEqual(rows[2]["title"], "b")


def _blocks_png(path: Path, ranges):
    """タイトルと、指定した y 範囲の本文ブロックだけを描いた PNG。"""
    im = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((60, 40, 900, 90), fill="black")
    for y0, y1 in ranges:
        d.rectangle((60, y0, 1100, y1), fill="black")
    im.save(path)


@unittest.skipIf(Image is None, "pillow が無い")
class BandTests(unittest.TestCase):
    def band(self, ranges):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            _blocks_png(p, ranges)
            im = Image.open(p).convert("RGB")
            return check_visual.largest_blank_band(check_visual.row_ink(im, check_visual.background(im)))

    def test_trailing_band(self):
        h, y0, y1 = self.band([(140, 160), (200, 380)])
        self.assertEqual((y0, y1), (381, 650))
        self.assertGreater(h, 250)

    def test_middle_band_survives_a_conclusion_strip(self):
        # 下に帯を 1 本足しても、途中の空白は残って検出される（A5-10）
        h, y0, y1 = self.band([(140, 160), (200, 330), (620, 640)])
        self.assertLess(y1, 650)
        self.assertGreaterEqual(h, 280)

    def test_filled_body_has_no_band(self):
        h, _, _ = self.band([(140, 640)])
        self.assertLess(h, 20)

    def test_band_warning_rules(self):
        w = check_visual.band_warning("1枚目（type=table）", "table", (200, 450, 650), 0.1, 150)
        self.assertIn("[empty-bottom]", w)
        w = check_visual.band_warning("1枚目（type=cards）", "cards", (180, 400, 580), 0.1, 150)
        self.assertIn("[empty-band]", w)
        self.assertIsNone(check_visual.band_warning("1枚目（type=cards）", "cards", (140, 130, 270), 0.1, 150))   # 閾値未満
        self.assertIsNone(check_visual.band_warning("1枚目（type=closing）", "closing", (300, 350, 650), 0.1, 150))  # 余白でよい型
        # リード直下から始まる隙間は、本文を縦中央に寄せた配置として許容する
        self.assertIsNone(check_visual.band_warning("1枚目（type=bullets）", "bullets", (164, 160, 324), 0.1, 150))

    def test_top_gap_tolerated_only_when_content_is_balanced(self):
        # 上が 390px 空いて、中身が下端に寄っている（下の空き 0px）→ 中央寄せではないので警告（qa-C-06）
        w = check_visual.band_warning("1枚目（type=image）", "image", (390, 130, 520), 0.1, 150, bottom_gap=0)
        self.assertIn("[empty-band]", w)
        # 中央寄せ（上の隙間 164px に対して下の空きも同程度）は従来どおり許容
        self.assertIsNone(check_visual.band_warning("1枚目（type=bullets）", "bullets", (164, 160, 324), 0.1, 150, bottom_gap=160))
        self.assertIsNone(check_visual.band_warning("1枚目（type=bullets）", "bullets", (164, 160, 324), 0.1, 150, bottom_gap=82))
        # 下の空きが上の隙間の半分未満なら警告
        self.assertTrue(check_visual.band_warning("1枚目（type=bullets）", "bullets", (164, 160, 324), 0.1, 150, bottom_gap=40))

    def test_bottom_gap_of(self):
        prof = [0.0] * 720
        for y in range(140, 500):
            prof[y] = 0.5
        self.assertEqual(check_visual.bottom_gap_of(prof), 650 - 1 - 499)
        self.assertEqual(check_visual.bottom_gap_of([0.0] * 720), 520)
        for y in range(600, 700):    # 本文領域（650 まで）の外のインクは数えない
            prof[y] = 0.5
        self.assertEqual(check_visual.bottom_gap_of(prof), 0)

    def test_table_empty_bottom_40_percent_is_detected(self):
        # 本文領域の下 40%（約 210px）が空いた表（A6-09）。ぎりぎり埋まった帯のある旧判定では見逃していた
        deck = {"meta": {"title": "t"}, "slides": [{"type": "table", "title": "c", "columns": ["a"], "rows": [["1"]]}]}
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            _blocks_png(prev / "slide-01.png", [(140, 160), (200, 300), (360, 440), (640, 646)])  # 下端に凡例線だけ
            rows, warns = check_visual.analyze(dd)
        self.assertTrue(any("[empty-band]" in w for w in warns), warns)
        self.assertGreaterEqual(rows[0]["band_h"], 190)


@unittest.skipIf(Image is None, "pillow が無い")
class StaleTests(unittest.TestCase):
    def test_extra_and_missing_pngs(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            for n in (1, 2, 4, 5):
                _png(prev / f"slide-{n:02d}.png", 640)
            w = check_visual.stale_warnings(dd, None, 3)
        joined = "\n".join(w)
        self.assertIn("足りません", joined)
        self.assertIn("slide-04.png", joined)
        self.assertIn("slide-05.png", joined)

    def test_png_older_than_input(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            png = prev / "slide-01.png"
            _png(png, 640)
            (dd / "deck.json").write_text("{}", encoding="utf-8")
            old = (dd / "deck.json").stat().st_mtime - 100
            os.utime(png, (old, old))
            w = check_visual.stale_warnings(dd, None, 1)
            self.assertTrue(any("入力（deck.json）の更新より古い" in x for x in w), w)
            os.utime(png, None)
            self.assertEqual(check_visual.stale_warnings(dd, None, 1), [])

    def test_rebuilt_html_alone_is_not_stale(self):
        """check_layout.py の自動再ビルドで HTML だけ新しくなっても、入力が変わっていなければ古い扱いにしない。"""
        import os
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            (dd / "deck.json").write_text("{}", encoding="utf-8")
            png = prev / "slide-01.png"
            _png(png, 640)
            base = png.stat().st_mtime
            os.utime(dd / "deck.json", (base - 50, base - 50))
            html = dd / "build" / "x.html"
            html.write_text("<html></html>", encoding="utf-8")
            os.utime(html, (base + 100, base + 100))
            self.assertEqual(check_visual.stale_warnings(dd, html, 1), [])

    def test_asset_newer_than_png_is_stale(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            prev = dd / "build" / "preview"
            prev.mkdir(parents=True)
            (dd / "assets").mkdir()
            png = prev / "slide-01.png"
            _png(png, 640)
            base = png.stat().st_mtime
            (dd / "assets" / "a.png").write_bytes(b"x")
            os.utime(dd / "assets" / "a.png", (base + 50, base + 50))
            w = check_visual.stale_warnings(dd, None, 1)
            self.assertTrue(any("a.png" in x for x in w), w)


if __name__ == "__main__":
    unittest.main()

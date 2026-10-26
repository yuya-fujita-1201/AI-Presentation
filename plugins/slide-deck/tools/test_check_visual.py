"""check_visual（下 1/3 の空白・似たスライドの連続）のテスト。合成した PNG で判定だけを確かめる。"""
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


if __name__ == "__main__":
    unittest.main()

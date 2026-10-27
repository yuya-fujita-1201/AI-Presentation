"""icon_engine（同梱アイコンの意味検索・canvas 要素化）と scripts/build_icon_set.py のパス変換のテスト。"""
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
# アイコン集を作り直す保守用スクリプトは配布物の外（リポジトリ直下の scripts/）にある
SCRIPTS = TOOLS.parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    import build_icon_set as bis  # noqa: E402
except ImportError:  # 配布 zip には scripts/ が無い
    bis = None
import canvas_engine as ce  # noqa: E402
import icon_engine as ie  # noqa: E402


class IconSetTests(unittest.TestCase):
    def test_bundled_icons_are_small_and_licensed(self):
        data = ie.load()
        self.assertGreaterEqual(len(data["icons"]), 60)
        self.assertIn("Tabler", data["source"])
        self.assertTrue((ie.ICON_FILE.parent / "LICENSE-tabler.txt").is_file())
        self.assertLess(ie.ICON_FILE.stat().st_size, 200_000)   # 素材を増やしすぎない
        for name, meta in data["icons"].items():
            with self.subTest(name=name):
                self.assertTrue(meta["ja"] and meta["en"] and meta["paths"])
                for p in meta["paths"]:
                    self.assertTrue(all(c[0] in "MLCQZ" for c in p))   # canvas の自由曲線が扱える命令だけ


class SearchTests(unittest.TestCase):
    def test_concept_words_find_icons(self):
        cases = {"セキュリティ": "shield-check", "コスト削減": "trending-down", "研修": "school",
                 "スケジュール": "calendar", "q:統制 安全": "shield-check", "security": "shield-check"}
        for q, want in cases.items():
            with self.subTest(q=q):
                self.assertEqual(ie.resolve(q), want)

    def test_name_and_unknown(self):
        self.assertEqual(ie.resolve("rocket"), "rocket")
        self.assertIsNone(ie.resolve("ほげほげ"))
        self.assertIsNone(ie.resolve(""))

    def test_element_is_scaled_stroke_only_shape(self):
        el = ie.element("rocket", 10, 20, 48, "#112233")
        self.assertEqual((el["x"], el["y"], el["w"], el["h"]), (10, 20, 48, 48))
        self.assertEqual(el["line"]["width"], 4.0)   # 24px で 2px の線 → 48px で 4px
        self.assertTrue(all(p["fill"] is False for p in el["path"]))
        issues = []
        ce.sanitize_elements([el], issues=issues)
        self.assertEqual(issues, [])
        pts = [v for p in el["path"] for c in p["cmds"] for v in c[1:]]
        self.assertTrue(all(-1 <= v <= 49 for v in pts))


@unittest.skipIf(bis is None, "scripts/build_icon_set.py が無い（配布 zip では省略）")
class PathConversionTests(unittest.TestCase):
    def test_relative_and_shorthand_commands(self):
        cmds = bis.path_to_cmds("M2 3h4v5H1zm1 1l2 2")
        self.assertEqual(cmds[0], ["M", 2, 3])
        self.assertEqual(cmds[1], ["L", 6, 3])
        self.assertEqual(cmds[2], ["L", 6, 8])
        self.assertEqual(cmds[3], ["L", 1, 8])
        self.assertEqual(cmds[4], ["Z"])
        self.assertEqual(cmds[5], ["M", 3, 4])     # Z の後の相対 m は始点基準
        self.assertEqual(cmds[6], ["L", 5, 6])

    def test_arc_becomes_cubic_ending_at_target(self):
        cmds = bis.path_to_cmds("M0 12a12 12 0 1 0 24 0")
        self.assertTrue(all(c[0] in "MC" for c in cmds))
        self.assertAlmostEqual(cmds[-1][-2], 24, places=2)
        self.assertAlmostEqual(cmds[-1][-1], 12, places=2)

    def test_circle_rect_line(self):
        self.assertEqual(bis.shape_to_cmds("line", {"x1": "1", "y1": "2", "x2": "3", "y2": "4"}),
                         [["M", 1, 2], ["L", 3, 4]])
        self.assertEqual(bis.shape_to_cmds("rect", {"x": "0", "y": "0", "width": "2", "height": "2"})[-1], ["Z"])
        self.assertTrue(bis.shape_to_cmds("circle", {"cx": "12", "cy": "12", "r": "5"}))


class IntegrationTests(unittest.TestCase):
    def test_icons_in_layouts(self):
        import build_deck as b
        import proposal_engine as pe
        layout = b.load_json(b.ROOT / "templates" / "layouts" / "default.json")
        theme = b.load_theme("default", b.theme_dirs(None))
        slide = {"type": "summary", "items": [{"lead": "a", "icon": "rocket"}, {"lead": "b", "icon": "ほげ"}]}
        els = pe.layout(slide, b.resolve_style(layout, {"meta": {}}, slide), theme)
        self.assertIn("要点1のアイコン", {e.get("name") for e in els})
        self.assertNotIn("要点2のアイコン", {e.get("name") for e in els})
        warns = []
        pe.validate(slide, 0, lambda m: None, warns.append)
        self.assertTrue(any("ほげ" in w for w in warns))
        cards = {"type": "cards", "cards": [{"heading": "x", "icon": "コスト"}]}
        ex = pe.extras(cards, b.resolve_style(layout, {"meta": {}}, cards), theme)
        self.assertEqual([e["name"] for e in ex], ["カード1のアイコン"])


if __name__ == "__main__":
    unittest.main()

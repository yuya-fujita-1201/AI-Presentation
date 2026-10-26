"""build_settings_widget（新規作成の設定フォーム）のテスト。仕上げの度合い（quality）の選択だけを確かめる。"""
import re
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_settings_widget as w  # noqa: E402


def _pressed(html: str, name: str):
    group = re.search(rf'data-name="{name}".*?</div>', html, re.S).group(0)
    return re.findall(r'data-value="([^"]+)" aria-pressed="true"', group)


class QualityFieldTests(unittest.TestCase):
    def test_draft_is_default(self):
        html = w.build([], {}, set())
        self.assertEqual(_pressed(html, "quality"), ["ドラフト"])
        self.assertIn('data-value="仕上げ"', html)

    def test_defaults_and_from_request(self):
        html = w.build([], {"quality": "仕上げ"}, {"quality"})
        self.assertEqual(_pressed(html, "quality"), ["仕上げ"])
        self.assertIn("依頼文から反映", html)

    def test_unknown_value_falls_back_to_draft(self):
        self.assertEqual(_pressed(w.build([], {"quality": "おまかせ"}, set()), "quality"), ["ドラフト"])
        self.assertIn("quality", w.FIELDS)


if __name__ == "__main__":
    unittest.main()

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


class ThemeChoiceTests(unittest.TestCase):
    def test_bundled_choices_are_default_and_three_acn_themes(self):
        """配布版で選べるのは default と acnpptx の3テンプレートに寄せた配色。旧名の別名は出さない。"""
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"SLIDE_DECK_THEMES": ""}):
            themes = w.list_themes(None)
        self.assertEqual([t["name"] for t in themes],
                         ["default", "accenture", "acn-slide-master", "acn-technology-graphik"])
        self.assertEqual([t["label"] for t in themes][1:], ["Accenture", "ACN Slide Master", "ACN Technology Graphik"])
        html = w.build(themes, {"theme": "acn-technology-graphik"}, set())
        self.assertEqual(_pressed(html, "theme"), ["acn-technology-graphik"])
        self.assertNotIn("accenture-purple", html)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""型エンジンの統合（PE 強化 × S2d 主役のあるページ）で入れた結線のテスト:
合成・split のブロックに置いた型の検査が矩形の幅で行われる、エンジンが入れた改行を check_layout / canvas が自動改行として扱う、
番号の文字枠が折り返さない。

    python -m unittest tools/test_pe_merge.py
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
import pattern_engine as pe  # noqa: E402

PATTERNS = TOOLS.parent / "templates" / "patterns"


def _slots(name):
    p = pe.load_pattern(name)
    return pe.show_example_slide(p)["slots"]


WIDE_ONLY = {"name": "wide-only", "label": "幅の広い型", "frame": "body", "size": [1136, 400], "min_width": 900,
             "slots": {"t": {"kind": "text", "label": "文", "max_chars": 20, "example": "例"}},
             "elements": [{"name": "文", "x": 0, "y": 0, "w": 1136, "h": 100, "text": {"paragraphs": [{"runs": [{"text": "{{t}}", "size": 30, "color": "text"}]}]}}]}


def _build(slides, wide_only=False):
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        if wide_only:       # 同梱の型はすべて狭い構図を持つので、幅の下限だけを持つ型をデッキの patterns/ に置く
            (d / "patterns").mkdir()
            (d / "patterns" / "wide-only.json").write_text(json.dumps(WIDE_ONLY, ensure_ascii=False), encoding="utf-8")
        (d / "deck.json").write_text(json.dumps({"meta": {"title": "t", "id": "t"}, "slides": slides}, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), "--html", str(d)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


def _block(name):
    return {"type": "pattern", "pattern": name, "slots": _slots(name)}


class BlockWidthTest(unittest.TestCase):
    """合成・split のブロックに置いた型は、ブロックの幅で narrow の構図と min_width が選ばれる"""

    def test_composite_half_width_numbered_list_has_no_width_warning(self):
        rc, out = _build([{"type": "composite", "title": "t", "columns": [1, 1],
                           "blocks": [_block("numbered-list"), {"type": "bullets", "bullets": ["a", "b"], "frame": "none"}]}])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("以上向き", out)

    def test_composite_half_width_wide_pattern_warns(self):
        rc, out = _build([{"type": "composite", "title": "t", "columns": [1, 1],
                           "blocks": [{"type": "pattern", "pattern": "wide-only", "slots": {"t": "例"}}, {"type": "bullets", "bullets": ["a", "b"], "frame": "none"}]}], wide_only=True)
        self.assertEqual(rc, 0, out)
        self.assertIn("wide-only", out)
        self.assertIn("以上向き", out)

    def test_split_body_pattern_is_checked_by_block_width(self):
        panel = {"fill": "primary", "title": "p"}
        rc, out = _build([{"type": "split", "side": "left", "ratio": 0.5, "panel": panel, "title": "t", "blocks": [_block("funnel")]}])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("以上向き", out)
        rc, out = _build([{"type": "split", "side": "left", "ratio": 0.5, "panel": panel, "title": "t", "blocks": [{"type": "pattern", "pattern": "wide-only", "slots": {"t": "例"}}]}], wide_only=True)
        self.assertEqual(rc, 0, out)
        self.assertIn("以上向き", out)


class SoftBreakTest(unittest.TestCase):
    def test_soft_br_is_marked_in_html_only_when_soft(self):
        def html(runs):
            return ce.text_html({"paragraphs": [{"runs": runs}]}, 100, 40)
        h = html([{"text": "あ", "size": 20}, {"br": True, "size": 20, "soft": True}, {"text": "い", "size": 20}])
        self.assertIn('<br data-soft="1">', h)
        h2 = html([{"text": "あ", "size": 20}, {"br": True, "size": 20}, {"text": "い", "size": 20}])
        self.assertNotIn("data-soft", h2)
        self.assertIn("<br>", h2)

    def test_check_layout_ignores_soft_br_and_checks_pre_wrap(self):
        src = (TOOLS / "check_layout.py").read_text(encoding="utf-8")
        self.assertIn("hasAttribute('data-soft')", src)
        self.assertIn("cs.whiteSpace === 'pre'", src)


class NumberBoxTest(unittest.TestCase):
    def test_numbered_list_number_boxes_do_not_wrap(self):
        d = json.loads((PATTERNS / "numbered-list.json").read_text(encoding="utf-8"))
        found = []

        def walk(o):
            if isinstance(o, dict):
                if "番号" in str(o.get("name", "")) and isinstance(o.get("text"), dict):
                    found.append(o["text"].get("wrap"))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(d)
        self.assertTrue(found)
        self.assertTrue(all(w is False for w in found), found)


if __name__ == "__main__":
    unittest.main()

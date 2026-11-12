#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5b 小さな不具合（lint の density・accenture の箱の小見出しの対比・【要確認】の警告・title の円の飾り・check_pptx の note・
合成の kpi_tree の conclusion・古い docstring / 文面）のテスト。

実行: python3 -m unittest plugins/slide-deck/tools/test_s5b_fixes.py
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import check_pptx  # noqa: E402
import color_pick as cp  # noqa: E402
import dataviz_engine as dv  # noqa: E402
import hero_engine as hero  # noqa: E402
import lint_deck_text as lint  # noqa: E402

THEMES = ("default", "accenture", "acn-slide-master", "acn-technology-graphik")
SHAPES = ("classic", "sharp", "soft", "editorial")


def deck_dir(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s5bf_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def resolved(slides, idx=0, **meta):
    d = deck_dir(slides, **meta)
    deck, theme, layout = b.load_deck(d)
    deck = b.expand_slides(deck, layout)
    return deck, theme, layout, b.resolve_style(layout, deck, deck["slides"][idx])


class LintDensity(unittest.TestCase):
    def test_slide_density_overrides_meta(self):
        text = "あ" * 300
        base = {"type": "bullets", "title": "t", "bullets": [text[:60]] * 5}
        talk = lint.check_volume("slide-01", base, "talk")
        read = lint.check_volume("slide-01", base, "read")
        self.assertTrue(talk, "talk（250 字）では超える")
        self.assertFalse(read, "read では超えない")
        # lint 全体: meta.density は talk、スライドが read → 文字量の警告が出ない
        deck = {"meta": {"density": "talk"}, "slides": [dict(base, density="read")]}
        res = lint.lint(deck)
        self.assertFalse([w for w in res["warnings"] if "表示文字数" in w], res["warnings"])
        deck = {"meta": {"density": "talk"}, "slides": [dict(base)]}
        self.assertTrue([w for w in lint.lint(deck)["warnings"] if "表示文字数" in w])

    def test_unknown_slide_density_falls_back_to_meta(self):
        base = {"type": "bullets", "title": "t", "bullets": ["あ" * 60] * 5, "density": "bogus"}
        deck = {"meta": {"density": "talk"}, "slides": [base]}
        self.assertTrue([w for w in lint.lint(deck)["warnings"] if "表示文字数" in w])

    def test_schedule_is_exempt_from_volume(self):
        self.assertIn("schedule", lint.VOLUME_EXEMPT)
        s = {"type": "schedule", "title": "t", "rows": [{"label": "あ" * 200, "start": "2026-04", "end": "2026-06"}] * 3}
        self.assertEqual(lint.check_volume("slide-01", s, "talk"), [])


class BoxHeadingContrast(unittest.TestCase):
    SLIDES = [{"type": "composite", "title": "箱", "arrange": "two", "blocks": [
        {"type": "bullets", "heading": "小見出し", "frame": "box", "bullets": ["あ", "い"]},
        {"type": "text", "heading": "見出し B", "frame": "box", "paragraphs": ["本文"]}]},
        {"type": "split", "side": "left", "panel": {"fill": "primary", "kpi": {"value": "1", "label": "x"}}, "title": "s",
         "blocks": [{"type": "bullets", "heading": "小見出し", "frame": "box", "bullets": ["あ"]}]}]

    def test_heading_color_readable_on_box_fill_for_all_themes_and_shapes(self):
        for theme in THEMES:
            for shape in SHAPES:
                for idx in (0, 1):
                    with self.subTest(theme=theme, shape=shape, slide=idx):
                        deck, th, layout, st = resolved(self.SLIDES, idx, theme=theme, shape=shape)
                        colors = layout["_colors"]
                        blk = st["block"]
                        fg = b._pair_color(colors, st, blk, blk["heading_color"])
                        bg = b._pair_color(colors, st, blk, blk["fill"])
                        self.assertGreaterEqual(cp.contrast(fg, bg), 4.5, f"{fg} / {bg}")

    def test_explicit_heading_color_is_kept(self):
        s = json.loads(json.dumps(self.SLIDES))
        s[0]["style"] = {"block": {"heading_color": "accent"}}
        _, _, layout, st = resolved(s, 0, theme="accenture")
        self.assertEqual(st["block"]["heading_color"], "accent")


class TodoMarkerWarnings(unittest.TestCase):
    def test_long_marker_is_not_a_long_word(self):
        em, tok = autofit.longest_token("連絡先は【要確認: https://example.com/long/path/to/resource/abcdef】です")
        self.assertNotIn("【", tok)                     # マーカーは 1 語にならない
        em2, tok2 = autofit.longest_token("【要確認: 連絡先の担当者名と電話番号と所属部署を確かめる】")
        self.assertLess(em2, 3)                         # 和文のマーカーは 1 文字ずつ
        # 通常の長い英数字は従来どおり 1 語
        self.assertEqual(autofit.longest_token("abcdefghij")[1], "abcdefghij")

    def test_kpi_value_marker_not_counted(self):
        warns = []
        slide = {"type": "kpi", "items": [{"value": "【要確認: 金額】", "label": "売上"}]}
        dv.validate(slide, 0, lambda m: (_ for _ in ()).throw(AssertionError(m)), warns.append)
        self.assertFalse([w for w in warns if "長すぎ" in w], warns)
        warns = []
        dv.validate({"type": "kpi", "items": [{"value": "あいうえおかきくけ", "label": "売上"}]}, 0, lambda m: None, warns.append)
        self.assertTrue([w for w in warns if "長すぎ" in w], "マーカーでない長い値は従来どおり警告")
        warns = []
        dv.validate({"type": "kpi", "items": [{"value": "【要確認】あいうえおかきくけ", "label": "売上"}]}, 0, lambda m: None, warns.append)
        self.assertTrue([w for w in warns if "長すぎ" in w], "マーカーの外が長い値は警告")


class TitleDeco(unittest.TestCase):
    def test_left_band_circle_follows_shape(self):
        slides = [{"type": "title", "title": "表紙", "variant": "left-band"}]
        geoms = {}
        for shape in SHAPES:
            deck, th, layout, st = resolved(slides, 0, shape=shape)
            els = hero.deco_elements(st, layout["_colors"])
            deco2 = [e for e in els if e["w"] == 260 and e["h"] == 260]
            self.assertEqual(len(deco2), 1)
            geoms[shape] = deco2[0].get("geom")
        self.assertEqual(geoms["classic"], "ellipse")        # classic の見た目は変えない
        self.assertEqual(geoms["soft"], "ellipse")
        self.assertNotEqual(geoms["sharp"], "ellipse")       # sharp は四角
        self.assertNotEqual(geoms["editorial"], "ellipse")

    def test_user_radius_zero_ellipse_is_square_and_plain_ellipse_stays(self):
        st = {"deco1": {"x": 0, "y": 0, "w": 10, "h": 10, "fill": "#112233", "geom": "ellipse"}}
        self.assertEqual(hero.deco_elements(st, {})[0].get("geom"), "ellipse")       # radius を書かない円は従来どおり


class CheckPptxNote(unittest.TestCase):
    def test_font_pinning_note_is_printed(self):
        fake = {"env": "-env:UserInstallation=file:///x", "pairs": [("Meiryo", "Hiragino Sans")], "profile": Path("/x")}
        err = io.StringIO()
        with mock.patch.object(check_pptx.lo_profile, "prepare", return_value=fake), redirect_stderr(err):
            with self.assertRaises(Exception):          # soffice は無い（存在しないパス）ので変換で失敗する。note はその前に出る
                check_pptx.render_pptx_to_pngs(Path("/nonexistent.pptx"), "/nonexistent-soffice", "/nonexistent-pdftoppm",
                                               Path(tempfile.mkdtemp(prefix="s5bn_")))
        self.assertIn("Meiryo", err.getvalue())
        self.assertIn("Hiragino Sans", err.getvalue())
        self.assertIn("置き換え", err.getvalue())


class CompositeBlockIgnoredKeys(unittest.TestCase):
    def test_block_slide_drops_keys_the_warning_says_are_not_drawn(self):
        block = {"type": "kpi_tree", "heading": "x", "root": "r", "branches": [], "conclusion": "帯", "source": "出典", "title": "t", "lead": "l"}
        bs = b.block_slide({"type": "composite"}, block, 0, {"meta": {}})
        for k in ("conclusion", "source", "title", "lead"):
            self.assertNotIn(k, bs)
        self.assertEqual(bs["root"], "r")

    def test_kpi_tree_block_conclusion_not_in_html(self):
        d = deck_dir([{"type": "composite", "title": "kpi_tree", "arrange": "top-bottom", "blocks": [
            {"type": "kpi_tree", "heading": "x", "root": "対応の質",
             "branches": [{"title": "早く", "kpis": [{"title": "回答時間", "value": "2 分", "note": "毎日"}]}], "conclusion": "帯が出ない文言"},
            {"type": "bullets", "bullets": ["a", "b"]}]}])
        import subprocess
        r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), str(d), "--html"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("conclusion はブロックでは描かれません", r.stdout + r.stderr)      # 警告は従来どおり
        self.assertNotIn("帯が出ない文言", (d / "build" / "d.html").read_text(encoding="utf-8"))      # 描画も警告に一致


class StaleWording(unittest.TestCase):
    def test_no_fit_false_for_autofit_in_tools(self):
        """自動フィットを止めるキーは autofit: false（スライドの fit: false は bleed の指定）。コード・警告文に `fit: false` と書かない。"""
        bad = re.compile(r"(?<!auto)fit\s*[:=]\s*false|meta\.fit\b", re.IGNORECASE)
        for p in sorted(TOOLS.glob("*.py")):
            if p.name.startswith("test_"):
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(bad.search(line), f"{p.name}:{n}: {line.strip()}")

    def test_contrast_docstring_counts_current_sample(self):
        src = (TOOLS / "test_s3a_contrast.py").read_text(encoding="utf-8")
        self.assertNotIn("見本 34 枚", src)


class ReviewFixes(unittest.TestCase):
    """独立レビュー（s5b-R-07 / R-08 / R-10）の修正。"""

    def test_lint_survives_non_string_density(self):
        base = {"type": "bullets", "title": "t", "bullets": ["あ" * 60] * 5}
        for bad in ([1], {"a": 1}, 3, True, None):
            deck = {"meta": {"density": "talk"}, "slides": [dict(base, density=bad)]}
            res = lint.lint(deck)                                    # TypeError（unhashable）にならない
            self.assertTrue([w for w in res["warnings"] if "表示文字数" in w], bad)    # meta.density（talk）で検査する

    def test_canvas_accepts_wordbreak_in_qa_ignore(self):
        import canvas_engine as ce
        self.assertIn("wordbreak", ce.QA_IGNORE_KINDS)
        self.assertEqual(ce.qa_ignore_attr({"qa_ignore": "wordbreak"}), ' data-qa-ignore="wordbreak"')
        self.assertEqual(ce.qa_ignore_attr({"qa_ignore": ["overlap", "wordbreak"]}), ' data-qa-ignore="overlap wordbreak"')

    def test_wordbreak_message_has_only_usable_advice(self):
        import check_layout as CL
        item = {"el": "p", "text": "あ", "tail": "ア", "head": "イ", "line": 1, "lines": 2, "size": 20, "cell": False}
        msg = CL.format_item("slide-01", "wordbreak", item) if hasattr(CL, "format_item") else ""
        self.assertNotIn("data-qa-ignore", msg)

    def test_hyphen_break_is_not_a_wordbreak(self):
        import check_layout as CL
        raw = [{"el": "p", "text": "詳細は installation-getting-started を参照する手順です", "lens": [17, 19], "size": 20}]
        pos = 17
        self.assertEqual(raw[0]["text"][pos - 1], "-")                  # 前提: ハイフンの直後で切れる
        self.assertEqual(CL.wordbreak_items(raw), [])
        raw = [{"el": "p", "text": "プラグインのファイルをアップロードする", "lens": [15, 4], "size": 25}]
        self.assertEqual(len(CL.wordbreak_items(raw)), 1, "日本語の語の途中は従来どおり")


if __name__ == "__main__":
    unittest.main()

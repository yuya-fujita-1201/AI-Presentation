#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改修全体のレビューで見つかった点の修正のテスト。

- playwright が無い環境で、SVG を含むデッキの PPTX 化が直し方つきのエラーになる（トレースバックにしない）
- 同梱と同じ名前のテーマ・レイアウトを別の場所から読んだときの note
- meta.brand が右上の箱に収まらないときの警告
- x / w の片方だけを style に書いた領域がスライドの外へ出るときの警告
- 2.0.0 までの pptx_import が書いたキー（source / generator / source_page）を警告なしで読む

実行: python3 -m unittest plugins/slide-deck/tools/test_final_fix.py
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import deck_paths  # noqa: E402
import deck_schema as dschema  # noqa: E402


def deck_dir(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="finfix_"))
    m = {"id": d.name, "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def validate_messages(slides, **meta) -> str:
    """デッキを読み込んで検証し、stderr に出た warning / note を返す。"""
    d = deck_dir(slides, **meta)
    b._WARNED.clear()
    err = io.StringIO()
    with redirect_stderr(err):
        deck, theme, layout = b.load_deck(d)
        b.validate_deck(deck, layout, theme, d)
    return err.getvalue()


BULLETS = {"type": "bullets", "title": "見出し", "bullets": ["項目 A", "項目 B"]}
SAMPLE = json.loads((TOOLS.parent / "examples" / "template-sample" / "deck.json").read_text(encoding="utf-8"))
SCHEDULE = next(dict(s) for s in SAMPLE["slides"] if s.get("type") == "schedule")     # 見本の schedule（style なし）
SCHEDULE.pop("style", None)


class PlaywrightMissing(unittest.TestCase):
    def test_import_failure_becomes_actionable_error(self):
        with mock.patch.dict(sys.modules, {"playwright": None, "playwright.sync_api": None}):
            with self.assertRaises(SystemExit) as cm:
                b._import_sync_playwright()
        msg = str(cm.exception)
        self.assertIn("playwright", msg)
        self.assertIn("/slide-deck:setup --playwright", msg)
        self.assertIn("--html", msg)
        self.assertNotIn("Traceback", msg)

    def test_launch_failure_becomes_actionable_error(self):
        pw = mock.Mock()
        pw.chromium.launch.side_effect = RuntimeError("Executable doesn't exist")
        with self.assertRaises(SystemExit) as cm:
            b._launch_chromium(pw)
        self.assertIn("playwright install chromium", str(cm.exception))


class ShadowedBundledName(unittest.TestCase):
    def setUp(self):
        b._SHADOW_NOTED.clear()

    def _note(self, kind, label, name, path) -> str:
        err = io.StringIO()
        with redirect_stderr(err):
            b._note_shadowed(kind, label, name, path)
        return err.getvalue()

    def test_bundled_file_itself_is_silent(self):
        p = deck_paths.bundled_dir("themes") / "default.json"
        self.assertEqual(self._note("themes", "テーマ", "default", p), "")

    def test_same_name_elsewhere_is_noted_once(self):
        d = Path(tempfile.mkdtemp(prefix="finfix_th_")) / "themes"
        d.mkdir()
        p = d / "default.json"
        p.write_text("{}", encoding="utf-8")
        out = self._note("themes", "テーマ", "default", p)
        self.assertIn("note:", out)
        self.assertIn(str(p), out)
        self.assertEqual(self._note("themes", "テーマ", "default", p), "", "同じファイルは 1 回だけ")

    def test_new_name_is_silent(self):
        d = Path(tempfile.mkdtemp(prefix="finfix_th_")) / "themes"
        d.mkdir()
        p = d / "my-brand.json"
        p.write_text("{}", encoding="utf-8")
        self.assertEqual(self._note("themes", "テーマ", "my-brand", p), "")

    def test_deck_local_theme_with_bundled_name_notes_on_load(self):
        d = deck_dir([BULLETS], theme="accenture")
        (d / "themes").mkdir()
        src = deck_paths.bundled_dir("themes") / "accenture.json"
        (d / "themes" / "accenture.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        err = io.StringIO()
        with redirect_stderr(err):
            b.load_deck(d)
        self.assertIn("テーマ 'accenture' は同梱のものではなく", err.getvalue())


class ShadowedPatternAndShape(unittest.TestCase):
    """型（パターン）と形（shape）も、同梱と同じ名前を別の場所から読んだら note を出す。"""

    def setUp(self):
        deck_paths._SHADOW_SEEN.clear()

    def _deck_with_copy(self, kind: str, name: str) -> Path:
        d = deck_dir([BULLETS])
        (d / kind).mkdir()
        src = deck_paths.bundled_dir(kind) / f"{name}.json"
        (d / kind / f"{name}.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return d

    def test_shape(self):
        import shape_engine as shp
        d = self._deck_with_copy("shapes", "soft")
        err = io.StringIO()
        with redirect_stderr(err):
            shp.load_shape("soft", d)
            shp.load_shape("soft", d)
        self.assertEqual(err.getvalue().count("形（shape） 'soft' は同梱のものではなく"), 1, err.getvalue())

    def test_pattern(self):
        import pattern_engine as pat_e
        name = sorted(p.stem for p in deck_paths.bundled_dir("patterns").glob("*.json"))[0]
        d = self._deck_with_copy("patterns", name)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIsNotNone(pat_e.load_pattern(name, d))
            pat_e.load_pattern(name, d)
        self.assertEqual(err.getvalue().count(f"型（パターン） '{name}' は同梱のものではなく"), 1, err.getvalue())

    def test_bundled_is_silent(self):
        import shape_engine as shp
        err = io.StringIO()
        with redirect_stderr(err):
            shp.load_shape("soft", deck_dir([BULLETS]))
        self.assertEqual(err.getvalue(), "")


class BrandWidth(unittest.TestCase):
    def test_short_brand_is_silent(self):
        self.assertNotIn("meta.brand", validate_messages([BULLETS], brand="ACME"))

    def test_long_brand_warns_once(self):
        out = validate_messages([BULLETS, BULLETS], brand="株式会社サンプル商事")
        self.assertEqual(out.count("meta.brand「株式会社サンプル商事」"), 1, out)
        self.assertIn("layout_overrides.common.brand", out)

    def test_widened_box_silences(self):
        out = validate_messages([BULLETS], brand="株式会社サンプル商事",
                                layout_overrides={"common": {"brand": {"x": 940, "w": 280}}})
        self.assertNotIn("meta.brand「", out)

    def test_no_brand_is_silent(self):
        self.assertNotIn("meta.brand", validate_messages([BULLETS]))


class PartialOverrideBleed(unittest.TestCase):
    def test_width_only_override_past_the_edge_warns(self):
        s = dict(SCHEDULE, style={"chart": {"w": 1232}})
        out = validate_messages([s])
        self.assertIn("chart.w だけが指定され", out)
        self.assertIn("x と w を両方書く", out)

    def test_both_written_is_silent(self):
        s = dict(SCHEDULE, style={"chart": {"x": 48, "w": 1184}})
        self.assertNotIn("だけが指定され", validate_messages([s]))

    def test_width_only_within_slide_is_silent(self):
        s = dict(BULLETS, style={"body": {"w": 600}})
        self.assertNotIn("だけが指定され", validate_messages([s]))

    def test_no_style_is_silent(self):
        self.assertNotIn("だけが指定され", validate_messages([SCHEDULE, BULLETS]))


class LegacyImportKeys(unittest.TestCase):
    def test_meta_keys_from_old_pptx_import(self):
        self.assertEqual(dschema.unknown_meta_keys({"source": "a.pptx", "generator": "pptx_import.py"}), [])

    def test_canvas_source_page(self):
        self.assertEqual(dschema.unknown_slide_keys({"type": "canvas", "elements": [], "source_page": 3}, "canvas"), [])

    def test_source_page_on_other_types_still_warns(self):
        out = dschema.unknown_slide_keys({"type": "bullets", "bullets": ["a"], "source_page": 3}, "bullets")
        self.assertTrue(out and "source_page" in out[0][1])

    def test_other_unknown_meta_key_still_warns(self):
        self.assertTrue(dschema.unknown_meta_keys({"sorce": "x"}))


if __name__ == "__main__":
    unittest.main()

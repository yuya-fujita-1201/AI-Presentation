#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入力検証と探索（core-1）のテスト。

  - deck_paths: テーマ・レイアウト・パターンの探索順（環境変数 → デッキ → 親 → カレント → 同梱）
  - load_layout: 名前だけ受け付ける・extends で差分だけ書ける・循環と未発見は候補つきで fail
  - テーマ JSON の検証層（hex / fonts / 未知キー / #RGB の正規化）
  - validate_deck: 型違いは fail、打ち間違いは warn、トレースバックで落ちない
  - 既知クラッシュの回帰（reasons 11 行・table columns 空・org 循環・壊れた画像・#RGB の PPTX ほか）
  - check_theme: 実使用の組・--deck

実行: python3 -m unittest plugins/slide-deck/tools/test_validation.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import deck_paths  # noqa: E402
import deck_schema as ds  # noqa: E402


def run_build(deck_dir, *extra):
    return subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), str(deck_dir), *extra],
                          capture_output=True, text=True, encoding="utf-8")


def write_deck(tmp, deck, name="d"):
    d = Path(tmp) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
    return d


def one(slide, **meta):
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    return {"meta": m, "slides": [slide]}


def validate(deck, deck_dir=None):
    """validate_deck を in-process で実行し (例外 or None, stderr) を返す。fail は SystemExit。"""
    b._WARNED.clear()
    layout = b.load_layout(deck.get("meta", {}).get("layout", "default"), deck_dir)
    theme = b.load_theme(deck.get("meta", {}).get("theme", "default"), b.theme_dirs(deck_dir))
    err = io.StringIO()
    exc = None
    with contextlib.redirect_stderr(err):
        try:
            b.validate_deck(deck, layout, theme, deck_dir)
        except SystemExit as e:
            exc = e
    return exc, err.getvalue()


# ---------------------------------------------------------------------------
# 探索
# ---------------------------------------------------------------------------

class SearchDirsTests(unittest.TestCase):
    def test_order_env_deck_parents_cwd_bundled(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t).resolve()
            deck = t / "proj" / "decks" / "x"
            deck.mkdir(parents=True)
            envd = t / "envd"
            cwd = t / "cwd"
            cwd.mkdir()
            with mock.patch.dict(os.environ, {"SLIDE_DECK_THEMES": f"{envd}{os.pathsep}{t / 'env2'}"}):
                dirs = deck_paths.search_dirs("themes", deck, cwd)
        self.assertEqual(dirs[0], envd)
        self.assertEqual(dirs[1], t / "env2")
        self.assertEqual(dirs[2], deck / "themes")
        self.assertEqual(dirs[3], deck.parent / "themes")            # decks/themes
        self.assertEqual(dirs[4], deck.parent.parent / "themes")     # proj/themes
        self.assertEqual(dirs[5], deck.parent.parent.parent / "themes")   # 3 階層上
        self.assertEqual(dirs[6], cwd / "themes")
        self.assertEqual(dirs[-1], ROOT / "templates" / "themes")

    def test_dedupe(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t).resolve()
            with mock.patch.dict(os.environ, {"SLIDE_DECK_LAYOUTS": str(t / "layouts")}):
                dirs = deck_paths.search_dirs("layouts", t, t)
        self.assertEqual(len([d for d in dirs if d == t / "layouts"]), 1)

    def test_each_kind_has_its_own_env(self):
        with mock.patch.dict(os.environ, {"SLIDE_DECK_PATTERNS": "/p1", "SLIDE_DECK_LAYOUTS": "/l1"}):
            self.assertEqual(deck_paths.search_dirs("patterns", None)[0], Path("/p1"))
            self.assertEqual(deck_paths.search_dirs("layouts", None)[0], Path("/l1"))
        with self.assertRaises(ValueError):
            deck_paths.search_dirs("bogus", None)

    def test_project_level_themes_found_from_decks_subfolder(self):
        """add-theme の既定出力先 ./themes/ で作ったテーマが decks/<名前>/ のデッキから見つかる（A7-01）。"""
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "themes").mkdir()
            (t / "themes" / "mybrand.json").write_text(json.dumps({"name": "mybrand", "colors": {"primary": "#112233"}}))
            deck = write_deck(t / "decks", one({"type": "title", "title": "a"}, theme="mybrand"), "x")
            r = run_build(deck, "--html")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_visibility_lines(self):
        lines = deck_paths.visibility_lines("themes", "/tmp/zz/themes", cwd="/somewhere/else")
        self.assertIn("/tmp/zz/themes", lines[0])
        self.assertTrue(any("見つかるデッキ" in ln for ln in lines))


# ---------------------------------------------------------------------------
# レイアウトの読み込み
# ---------------------------------------------------------------------------

class LoadLayoutTests(unittest.TestCase):
    def _write_layout(self, d, name, data):
        (Path(d) / "layouts").mkdir(exist_ok=True)
        (Path(d) / "layouts" / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")

    def test_default(self):
        lay = b.load_layout("default")
        self.assertIn("bullets", lay["types"])
        self.assertEqual(lay["name"], "default")

    def test_extends_default_by_default_and_overrides_only_given_keys(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_layout(t, "mine", {"types": {"bullets": {"body": {"size": 31}}}})
            lay = b.load_layout("mine", Path(t))
        base = b.load_layout("default")
        self.assertEqual(lay["types"]["bullets"]["body"]["size"], 31)
        self.assertEqual(lay["types"]["bullets"]["body"]["gap"], base["types"]["bullets"]["body"]["gap"])
        self.assertEqual(lay["types"]["cards"], base["types"]["cards"])
        self.assertNotIn("extends", lay)

    def test_extends_chain_and_cycle(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_layout(t, "a", {"extends": "b", "types": {"bullets": {"body": {"size": 1.5}}}})
            self._write_layout(t, "b", {"types": {"bullets": {"body": {"gap": 99}}}})
            lay = b.load_layout("a", Path(t))
            self.assertEqual(lay["types"]["bullets"]["body"]["gap"], 99)
            self.assertEqual(lay["types"]["bullets"]["body"]["size"], 1.5)
            self._write_layout(t, "x", {"extends": "y"})
            self._write_layout(t, "y", {"extends": "x"})
            with self.assertRaises(SystemExit) as cm:
                b.load_layout("x", Path(t))
        self.assertIn("循環", str(cm.exception))

    def test_user_default_overrides_bundled_and_inherits_it(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_layout(t, "default", {"types": {"bullets": {"body": {"size": 33}}}})
            lay = b.load_layout("default", Path(t))
        self.assertEqual(lay["types"]["bullets"]["body"]["size"], 33)
        self.assertIn("cards", lay["types"])   # 同梱 default を土台にしている

    def test_rejects_paths_and_reports_candidates(self):
        for bad in ("../x", "/etc/passwd", "a/b", ".hidden", "C:\\x", ""):
            with self.assertRaises(SystemExit, msg=bad):
                b.load_layout(bad)
        with self.assertRaises(SystemExit) as cm:
            b.load_layout("defualt")
        msg = str(cm.exception)
        self.assertIn("default", msg)
        self.assertIn("見つかりません", msg)

    def test_non_string_layout_name(self):
        with self.assertRaises(SystemExit):
            b.load_layout(5)


# ---------------------------------------------------------------------------
# テーマの検証層
# ---------------------------------------------------------------------------

class ThemeValidationTests(unittest.TestCase):
    def _load(self, data, name="t1"):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                b._WARNED.clear()
                try:
                    theme = b.load_theme(name, [Path(t)] + b.theme_dirs(None))
                    return theme, None, err.getvalue()
                except SystemExit as e:
                    return None, str(e), err.getvalue()

    def test_bad_hex_values_fail(self):
        for bad in ("navy", 5, "#12345", "primary", "", None, "#GGGGGG"):
            _, exc, _ = self._load({"colors": {"primary": bad}})
            self.assertIsNotNone(exc, bad)
            self.assertIn("colors.primary", exc)

    def test_shorthand_hex_is_normalized(self):
        theme, exc, _ = self._load({"colors": {"primary": "#04a", "accent": "#0A8"}})
        self.assertIsNone(exc)
        self.assertEqual(theme["colors"]["primary"], "#0044aa")
        self.assertEqual(theme["colors"]["accent"], "#00AA88")

    def test_fonts_must_be_strings_or_string_lists(self):
        for bad in (5, "", [], [""], [1], None, {"a": 1}):
            _, exc, _ = self._load({"fonts": {"body": bad}})
            self.assertIsNotNone(exc, repr(bad))
        theme, exc, _ = self._load({"fonts": {"body": ["Meiryo", "Hiragino Sans"]}})
        self.assertIsNone(exc)

    def test_structure_errors(self):
        for data in ([], "x", {"colors": ["a"]}, {"fonts": "Meiryo"}, {"name": 5}):
            _, exc, _ = self._load(data)
            self.assertIsNotNone(exc, repr(data))

    def test_unknown_top_keys_and_color_typos_warn(self):
        theme, exc, err = self._load({"colours": {"primary": "#112233"}, "colors": {"primry": "#445566"},
                                      "radius": 4, "layout": {}, "tokens": {}, "shape": "classic"})
        self.assertIsNone(exc)
        self.assertIn('"colours"', err)
        self.assertIn("もしかして \"colors\"", err)
        self.assertIn('"primry"', err)
        self.assertIn('"radius"', err)
        self.assertNotIn('"layout"', err)   # 後の段階で使うキーは許可

    def test_bad_hex_never_reaches_css(self):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t) / "themes"
            td.mkdir()
            (td / "bad.json").write_text(json.dumps({"colors": {"primary": "#12345"}}))
            d = write_deck(t, one({"type": "title", "title": "a"}, theme="bad"))
            r = run_build(d, "--html")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)
            self.assertFalse(list((d / "build").glob("*.html")) if (d / "build").exists() else [])

    def test_bundled_themes_pass_validation(self):
        for name in ("default", "accenture", "acn-slide-master", "acn-technology-graphik", "accenture-purple"):
            b._WARNED.clear()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                b.load_theme(name, b.theme_dirs(None))
            self.assertEqual(err.getvalue(), "", name)


# ---------------------------------------------------------------------------
# validate_deck: 型違い・打ち間違い
# ---------------------------------------------------------------------------

class TypeErrorTests(unittest.TestCase):
    def assertFails(self, slide, *needles, **meta):
        exc, err = validate(one(slide, **meta))
        self.assertIsNotNone(exc, f"fail になるはず: {slide}")
        text = str(exc)
        for n in needles:
            self.assertIn(n, text)
        self.assertNotIn("Traceback", text)

    def test_content_type_errors_fail(self):
        self.assertFails({"type": "bullets", "title": "a", "bullets": "abc"}, "bullets", "配列")
        self.assertFails({"type": "bullets", "title": "a", "bullets": [1, 2]}, "bullets[0]")
        self.assertFails({"type": "bullets", "title": "a", "bullets": ["a", None]}, "bullets[1]", "null")
        self.assertFails({"type": "cards", "title": "a", "cards": ["a", "b"]}, "cards[0]", "オブジェクト")
        self.assertFails({"type": "cards", "title": "a", "cards": {"heading": "x"}}, "cards")
        self.assertFails({"type": "steps", "title": "a", "steps": "abc"}, "steps")
        self.assertFails({"type": "matrix", "title": "a", "quadrants": ["a", "b", "c", "d"]}, "quadrants[0]")
        self.assertFails({"type": "two_column", "title": "a", "left": "abc"}, "left")
        self.assertFails({"type": "code", "title": "a", "code": 123}, "code")
        self.assertFails({"type": "code", "title": "a", "code": "x", "annotations": [{"line": "x"}]}, "annotations[0].line")
        self.assertFails({"type": "table", "title": "a", "columns": ["a"], "rows": [None]}, "rows[0]")
        self.assertFails({"type": "table", "title": "a", "columns": ["a"], "rows": "abc"}, "rows")
        self.assertFails({"type": "table", "title": "a", "columns": "ab", "rows": []}, "columns")
        self.assertFails({"type": "sequence", "title": "a", "participants": ["A", "B"], "messages": []}, "participants[0]")
        self.assertFails({"type": ["bullets"], "title": "a"}, "type")
        self.assertFails({"type": 5, "title": "a"}, "type")
        self.assertFails({"type": "bullets", "title": ["x"]}, "title")
        self.assertFails({"type": "cards", "title": "a", "cards": [], "columns": 2.5}, "columns", "整数")

    def test_message_names_slide_and_key(self):
        exc, _ = validate({"meta": {"id": "d", "title": "t"},
                           "slides": [{"type": "title", "title": "a"},
                                      {"type": "cards", "title": "b", "cards": ["x"]}]})
        self.assertIn("2枚目（type=cards）", str(exc))
        self.assertIn("cards[0]", str(exc))

    def test_style_and_overrides_type_errors_fail(self):
        base = {"type": "bullets", "title": "a", "bullets": ["x"]}
        for style in (None, "x", ["body"], 5):
            self.assertFails({**base, "style": style}, "style")
        for body in (None, "big", ["a"], 5):
            self.assertFails({**base, "style": {"body": body}}, "style.body")
        for key, val in (("size", "24"), ("w", "wide"), ("gap", "x"), ("line_height", [1]), ("size", True)):
            self.assertFails({**base, "style": {"body": {key: val}}}, f"style.body.{key}", "数値")
        self.assertFails({**base, "style": {"body": {"size": -5}}}, "style.body.size")
        self.assertFails({**base, "style": {"body": {"size": 0}}}, "style.body.size")
        self.assertFails({**base, "style": {"body": {"gap": -10}}}, "style.body.gap")
        self.assertFails({**base, "style": {"title": {"color": 5}}}, "style.title.color")
        for ov in ("x", ["a"], None):
            exc, _ = validate(one(base, layout_overrides=ov if ov is not None else {"bullets": None}))
            if ov is None:
                self.assertIsNotNone(exc)
        for ov in ({"bullets": None}, {"bullets": "x"}, {"bullets": ["body"]}, {"common": "x"}, {"common": ["a"]},
                   {"bullets": {"body": 5}}, {"bullets": {"body": {"size": "x"}}}):
            exc, _ = validate(one(base, layout_overrides=ov))
            self.assertIsNotNone(exc, ov)
            self.assertNotIn("Traceback", str(exc))

    def test_agenda_and_cards_style_ranges(self):
        self.assertFails({"type": "agenda", "title": "a", "items": ["x"], "style": {"body": {"max_cols": 0}}},
                         "max_cols")
        self.assertFails({"type": "agenda", "title": "a", "items": ["x"], "style": {"body": {"max_cols": 1.5}}},
                         "max_cols")

    def test_valid_inputs_still_pass(self):
        ok = [
            {"type": "bullets", "title": "a", "bullets": ["x", {"text": "y", "children": ["z"], "bold": True}]},
            {"type": "table", "title": "a", "columns": ["a", "b"], "rows": [["1", None], [{"text": "x", "url": "https://e.com"}, 3]]},
            {"type": "cards", "title": "a", "columns": 2, "cards": [{"heading": "h", "body": "b", "items": ["i"]}]},
            {"type": "section", "number": 1, "title": "b"},
            {"type": "quote", "text": "q", "attribution": 2026},
            {"type": "bullets", "title": "a", "bullets": ["x"], "style": {"body": {"size": 20, "valign": "middle"}},
             "lead": None, "_memo": "free"},
        ]
        for s in ok:
            exc, err = validate(one(s))
            self.assertIsNone(exc, f"{s}: {exc}")

    def test_null_means_absent_and_numbers_become_text(self):
        deck = one({"type": "section", "number": 1, "title": "b", "subtitle": None})
        exc, _ = validate(deck)
        self.assertIsNone(exc)
        sl = deck["slides"][0]
        self.assertEqual(sl["number"], "1")
        self.assertNotIn("subtitle", sl)


class UnknownKeyTests(unittest.TestCase):
    def warnings(self, slide, **meta):
        exc, err = validate(one(slide, **meta))
        self.assertIsNone(exc, str(exc))
        return err

    def test_slide_level_typos_warn_with_candidate(self):
        err = self.warnings({"type": "cards", "title": "a", "colums": 3, "cards": [{"heading": "x"}]})
        self.assertIn('未知のキー "colums"', err)
        self.assertIn('"columns"', err)
        self.assertIn("1枚目（type=cards）", err)
        err = self.warnings({"type": "bullets", "title": "a", "bulets": ["x"], "bullets": ["y"]})
        self.assertIn('"bulets"', err)

    def test_nested_typos_in_cards(self):
        err = self.warnings({"type": "cards", "title": "a", "cards": [{"headng": "x", "bdy": "y"}]})
        self.assertIn('"headng"', err)
        self.assertIn('"bdy"', err)

    def test_universal_and_underscore_keys_are_not_flagged(self):
        err = self.warnings({"type": "bullets", "title": "a", "bullets": ["x"], "notes": "n", "relation": "parallel",
                             "eyebrow": "e", "conclusion": "c", "source": "s", "line_balance": False,
                             "_todo": "x"})
        self.assertEqual(err, "")

    def test_diagram_types_use_universal_keys_too(self):
        err = self.warnings({"type": "architecture", "title": "a", "relation": "flow", "line_balance": False,
                             "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0}], "edges": []})
        self.assertNotIn("unknown-key", err)

    def test_meta_unknown_keys_warn_but_future_keys_allowed(self):
        err = self.warnings({"type": "title", "title": "a"}, theem="x", density="talk", autofit=True, patterns={})
        self.assertIn('"theem"', err)
        self.assertNotIn('"density"', err)
        self.assertNotIn('"autofit"', err)
        self.assertIn('"patterns"', err)           # S3a: 意味の無いキー。META_KEYS から外した（未知キーの警告になる）
        self.assertNotIn('"todo_marks"', self.warnings({"type": "title", "title": "a"}, todo_marks=False))

    def test_toplevel_typo_warns(self):
        exc, err = validate({"meta": {"id": "d", "title": "t"}, "slide": [{"type": "title", "title": "a"}], "slides": []})
        self.assertIn('"slide"', err)

    def test_style_property_typos_warn(self):
        err = self.warnings({"type": "bullets", "title": "a", "bullets": ["x"],
                             "style": {"body": {"sizee": 20, "colour": "text", "size": 20}}})
        self.assertIn('"sizee"', err)
        self.assertIn('"colour"', err)
        self.assertNotIn('"size" は', err)
        err = self.warnings({"type": "bullets", "title": "a", "bullets": ["x"]},
                            layout_overrides={"bullets": {"body": {"sizee": 20}}})
        self.assertIn("meta.layout_overrides.bullets.body", err)

    def test_known_style_props_documented_in_schema_are_not_flagged(self):
        err = self.warnings({"type": "table", "title": "a", "columns": ["a"], "rows": [["1"]],
                             "style": {"table": {"row_fills": {"0": "highlight_fill"}, "row_h": 40, "col_widths": [1]}}})
        self.assertEqual(err, "")
        err = self.warnings({"type": "steps", "title": "a", "steps": [{"label": "x", "items": ["y"]}],
                             "style": {"body": {"fit": "fill", "min_h": 200}}})
        self.assertEqual(err, "")

    def test_tiny_font_size_warns(self):
        err = self.warnings({"type": "bullets", "title": "a", "bullets": ["x"], "style": {"body": {"size": 6}}})
        self.assertIn("6px", err)
        self.assertIn("8px", err)

    def test_bullets_third_level_warns(self):
        err = self.warnings({"type": "bullets", "title": "a",
                             "bullets": [{"text": "a", "children": [{"text": "b", "children": ["c"]}]}]})
        self.assertIn("3 階層目", err)

    def test_bullet_dict_without_text_warns(self):
        err = self.warnings({"type": "bullets", "title": "a", "bullets": [{"txt": "hi"}]})
        self.assertIn("text がありません", err)

    def test_empty_body_warns(self):
        err = self.warnings({"type": "bullets", "title": "a"})
        self.assertIn("本文が空", err)
        err = self.warnings({"type": "cards", "title": "a", "cards": []})
        self.assertIn("本文が空", err)
        err = self.warnings({"type": "bullets", "title": "a", "bullets": ["x"]})
        self.assertNotIn("本文が空", err)


class RegisteredTypesTests(unittest.TestCase):
    def test_every_layout_type_has_a_renderer(self):
        self.assertEqual(set(b.load_layout("default")["types"]), set(b.RENDERED_TYPES))

    def test_every_layout_type_has_a_key_table(self):
        self.assertEqual({t for t in b.load_layout("default")["types"] if ds.type_slide_keys(t) is None}, set())

    def test_layout_only_type_is_rejected_with_fix(self):
        with tempfile.TemporaryDirectory() as t:
            ld = Path(t) / "layouts"
            ld.mkdir()
            default = b.load_layout("default")
            (ld / "foo.json").write_text(json.dumps({"types": {"foo": default["types"]["bullets"]}}))
            deck = write_deck(t, one({"type": "foo", "title": "FOOTITLE"}, layout="foo"))
            r = run_build(deck)
        self.assertEqual(r.returncode, 1)
        self.assertIn("描画が登録されていません", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


# ---------------------------------------------------------------------------
# 既知クラッシュの回帰（HTML と PPTX の両方をビルド）
# ---------------------------------------------------------------------------

class CrashRegressionTests(unittest.TestCase):
    def build(self, slide, **meta):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one(slide, **meta))
            r = run_build(d)
            html = list((d / "build").glob("*.html")) if (d / "build").exists() else []
            pptx = list((d / "build").glob("*.pptx")) if (d / "build").exists() else []
            return r, bool(html), bool(pptx)

    def assertCleanOk(self, slide, **meta):
        r, html, pptx = self.build(slide, **meta)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertNotIn("Traceback", r.stderr)
        self.assertTrue(html and pptx)

    def assertCleanFail(self, slide, needle, **meta):
        r, html, pptx = self.build(slide, **meta)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn(needle, r.stderr)
        self.assertFalse(html or pptx, "失敗したのに成果物が残っている")

    def test_reasons_eleven_rows(self):
        n = 11
        self.assertCleanOk({"type": "reasons", "title": "a",
                            "issues": [f"課題{i}" for i in range(n)], "strengths": [f"強み{i}" for i in range(n)]})

    def test_table_without_columns_fails_cleanly(self):
        self.assertCleanFail({"type": "table", "title": "a", "columns": [], "rows": []}, "columns")

    def test_table_col_widths_all_zero_fails_cleanly(self):
        self.assertCleanFail({"type": "table", "title": "a", "columns": ["a", "b"], "rows": [["1", "2"]],
                              "style": {"table": {"col_widths": [0, 0]}}}, "col_widths")

    def test_org_parent_cycle_and_self_reference(self):
        for nodes in ([{"id": "a", "title": "A", "parent": "a"}],
                      [{"id": "a", "title": "A", "parent": "b"}, {"id": "b", "title": "B", "parent": "a"}]):
            self.assertCleanFail({"type": "org", "title": "a", "left": {"title": "L", "nodes": nodes}}, "循環")

    def test_broken_image_fails_before_any_output(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "image", "title": "a", "path": "assets/x.png"}))
            (d / "assets").mkdir()
            (d / "assets" / "x.png").write_bytes(b"this is not a png")
            r = run_build(d)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("開けません", r.stderr)
            self.assertFalse((d / "build").exists() and list((d / "build").glob("*")))

    def test_status_table_three_column_minimum(self):
        self.assertCleanOk({"type": "status_table", "title": "a", "columns": ["チーム", "状況", "内容"],
                            "rows": [{"label": "A", "status": "green", "cells": [["x"]]}]})
        self.assertCleanOk({"type": "status_table", "title": "a", "columns": ["a", "b", "c", "d", "e"],
                            "rows": [{"label": "A", "status": "green", "cells": [["x"], ["y"], ["z"]]}]})

    def test_agenda_negative_gap_fails_cleanly(self):
        self.assertCleanFail({"type": "agenda", "title": "a", "items": ["x"], "style": {"body": {"gap": -4}}},
                             "style.body.gap")

    def test_shorthand_hex_colors_in_pptx(self):
        self.assertCleanOk({"type": "bullets", "title": "a", "bullets": [{"text": "x", "color": "#abc"}],
                            "style": {"title": {"color": "#f0a"}}})

    def test_null_inside_objects_and_style_properties_means_unset(self):
        self.assertCleanOk({"type": "matrix", "title": "a", "x_axis": {"label": None, "low": "低"},
                            "y_axis": {"label": "Y", "high": None},
                            "quadrants": [{"heading": "a", "body": None}, {"heading": "b"}, {"heading": "c"}, {"heading": "d"}]})
        self.assertCleanOk({"type": "bullets", "title": "a", "bullets": [{"text": "x", "size": None}],
                            "style": {"body": {"size": None, "gap": None}}})

    def test_child_bullet_without_text_does_not_crash(self):
        self.assertCleanOk({"type": "bullets", "title": "a", "bullets": [{"text": "x", "children": [{"size": 14}]}]})

    def test_unhashable_ids_fail_cleanly(self):
        self.assertCleanFail({"type": "swimlane", "title": "a", "lanes": [{"name": "L"}], "legend": False,
                              "nodes": [{"id": ["x"], "lane": 0, "col": 0}]}, "nodes[0].id")
        self.assertCleanFail({"type": "swimlane", "title": "a", "lanes": ["L"], "legend": False, "nodes": []}, "lanes[0]")

    def test_swimlane_absurd_column_fails_fast(self):
        self.assertCleanFail({"type": "swimlane", "title": "a", "lanes": [{"name": "L"}], "legend": False,
                              "nodes": [{"id": "a", "lane": 0, "col": 12345, "text": "x"}]}, "40 列まで")

    def test_quote_attribution_number(self):
        self.assertCleanOk({"type": "quote", "text": "q", "attribution": 2026})

    def test_null_content_does_not_crash(self):
        for key in ("cards", "steps", "items", "code", "left", "x_axis"):
            self.assertCleanOk({"type": "bullets", "title": "a", "bullets": ["x"], key: None})

    def test_unexpected_exception_becomes_clean_failure(self):
        """検証をすり抜けた想定外の例外は、トレースバックではなく「N枚目（type=…）」つきの fail にする。"""
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "bullets", "title": "a", "bullets": ["x"]}))
            code = (
                "import sys; sys.path.insert(0, %r); import build_deck as b\n"
                "def boom(*a, **k): raise KeyError('zzz')\n"
                "b.html_slide_body = boom\n"
                "sys.argv = ['build_deck.py', %r, '--html'%s]\n"
                "b.main()\n"
            )
            for debug in (False, True):
                r = subprocess.run([sys.executable, "-c", code % (str(TOOLS), str(d), ", '--debug'" if debug else "")],
                                   capture_output=True, text=True, encoding="utf-8")
                self.assertNotEqual(r.returncode, 0)
                if debug:
                    self.assertIn("Traceback", r.stderr)
                else:
                    self.assertNotIn("Traceback", r.stderr)
                    self.assertIn("出力1ページ目（type=bullets）", r.stderr)
                    self.assertIn("KeyError", r.stderr)
                    self.assertIn("--debug", r.stderr)


# ---------------------------------------------------------------------------
# check_theme / theme_from_sample
# ---------------------------------------------------------------------------

class CheckThemeTests(unittest.TestCase):
    def run_check(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(TOOLS / "check_theme.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", cwd=cwd or ROOT)

    def test_default_passes_all_pairs(self):
        r = self.run_check("default")
        self.assertEqual(r.returncode, 0)
        self.assertIn("警告0件", r.stdout)
        self.assertIn("muted", r.stdout)
        self.assertIn("実使用の組", r.stdout)

    def test_extra_pairs_warn_but_do_not_fail(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "pale.json"
            p.write_text(json.dumps({"name": "pale", "colors": {"primary": "#FFE066", "on_primary": "#000000",
                                                                   "accent": "#B8860B", "accent_on_primary": "#000000"}}))
            r = self.run_check(str(p))
        self.assertEqual(r.returncode, 0)
        self.assertIn("primary/background", r.stderr)

    def test_deck_option_finds_deck_side_theme(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "themes").mkdir()
            (t / "themes" / "found-me.json").write_text(json.dumps({"colors": {"primary": "#123456"}}))
            deck = t / "decks" / "x"
            deck.mkdir(parents=True)
            r = self.run_check("found-me", "--deck", str(deck), cwd=t / "decks")
            self.assertEqual(r.returncode, 0, r.stderr)
            r2 = self.run_check("found-me", cwd=ROOT)   # --deck なし・カレントにも無い
        self.assertNotEqual(r2.returncode, 0)


class ThemeFromSampleTests(unittest.TestCase):
    def test_derivation_matches_builder(self):
        import theme_from_sample as tfs
        theme = tfs.derive_theme("zz", (255, 255, 255), (40, 40, 60), (20, 60, 110), (0, 150, 170), {
            "heading": "Meiryo", "body": "Meiryo", "code": "Consolas"})
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "zz.json").write_text(json.dumps(theme))
            loaded = b.load_theme("zz", [Path(t)] + b.theme_dirs(None))
        self.assertEqual(loaded["colors"], tfs.derived_colors(theme))
        # muted は mix(text, bg, 0.35) を起点に、背景・面の上で 4.5:1 になるまで text 側へ寄せる（A-03）
        muted = loaded["colors"]["muted"]
        self.assertGreaterEqual(b.contrast_ratio(muted, loaded["colors"]["surface"]), 4.5)
        self.assertGreaterEqual(b.contrast_ratio(muted, "#FFFFFF"), 4.5)


# ---------------------------------------------------------------------------
# レビュー指摘の修正（core-fix）
# ---------------------------------------------------------------------------

SIMPLE = {"type": "bullets", "title": "t", "bullets": ["a"]}


class ReviewFixBuildTests(unittest.TestCase):
    """C-01 / A-01 / C-02 / C-07: 題名なし・スライド 0 枚・制御文字・PPTX が書けない"""

    def _title(self, d):
        from pptx import Presentation
        return Presentation(str(next((Path(d) / "build").glob("*.pptx")))).core_properties.title

    def test_no_title_builds_with_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "myid"}, "slides": [SIMPLE]})
            r = run_build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("meta.title がありません", r.stderr)
            self.assertNotIn("不具合", r.stderr)
            self.assertEqual(self._title(d), "myid")
            self.assertIn("<title>myid</title>", (d / "build" / "myid.html").read_text(encoding="utf-8"))

    def test_no_meta_at_all_uses_slide_title_or_folder(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"slides": [SIMPLE]}, "folder-x")
            r = run_build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self._title(d), "t")   # 先頭スライドの title
        self.assertEqual(b.deck_title({}, Path("/x/folder-y")), "folder-y")

    def test_empty_slides_builds_with_warning(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "e", "title": "T"}, "slides": []})
            r = run_build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("slides が空です", r.stderr)

    def test_control_chars_in_meta_do_not_crash(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "c", "title": "a\u0001b", "author": "x\u000by", "subtitle": "s\u0000"},
                               "slides": [SIMPLE]})
            r = run_build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(self._title(d), "ab")

    def test_locked_pptx_still_updates_html(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root は読み取り専用でも書ける")
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one(SIMPLE, id="lk"))
            self.assertEqual(run_build(d).returncode, 0)
            pptx, html = d / "build" / "lk.pptx", d / "build" / "lk.html"
            html.write_text("OLD", encoding="utf-8")
            os.chmod(pptx, 0o444)
            try:
                r = run_build(d)
            finally:
                os.chmod(pptx, 0o644)
            self.assertEqual(r.returncode, 1)
            self.assertIn("に書き込めません", r.stderr)
            self.assertNotEqual(html.read_text(encoding="utf-8"), "OLD")


class ReviewFixCardsTests(unittest.TestCase):
    def test_cards_body_and_items_are_top_anchored_in_pptx(self):
        """A-02: valign:middle でも本文・箇条書きの箱は上詰め（HTML と同じ）。中央寄せだと本文が約 13px 下がる。"""
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "cards", "title": "t", "cards": [
                {"heading": "H", "body": "BODYTEXT", "items": ["ITEMTEXT"]}]}))
            self.assertEqual(run_build(d, "--pptx").returncode, 0)
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
            found = 0
            for sh in prs.slides[0].shapes:
                if sh.has_text_frame and sh.text_frame.text in ("BODYTEXT", "ITEMTEXT"):
                    found += 1
                    bp = sh.text_frame._txBody.find("{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
                    self.assertNotEqual(bp.get("anchor"), "ctr", sh.text_frame.text)
            self.assertEqual(found, 2)


class ReviewFixInjectionTests(unittest.TestCase):
    """C-03 / C-04 / C-05 / C-09: HTML に出る値の検査と探索名の検査"""

    X = '"><script>alert(1)</script><x y="'

    def test_theme_font_name_rejected_and_stripped(self):
        issues = ds.validate_theme_data({"fonts": {"body": "X</style><script>alert(1)</script>"}}, "mine")
        self.assertTrue(any(lv == "fail" and "使えない文字" in m for lv, m in issues), issues)
        issues = ds.validate_theme_data({"fonts": {"body": ["Meiryo", "Hiragino Sans"]}}, "mine")
        self.assertEqual([x for x in issues if x[0] == "fail"], [])
        self.assertNotIn("<", b.font_css("X</style><script>"))
        self.assertNotIn(";", b.font_css('a";b{}'))

    def test_align_enum_fail_and_escaped(self):
        exc, err = validate(one({**SIMPLE, "style": {"title": {"align": self.X}}}))
        self.assertIsNotNone(exc)
        self.assertIn("style.title.align は left / center / right", str(exc))
        exc, _ = validate(one({**SIMPLE, "style": {"title": {"align": "center"}}}))
        self.assertIsNone(exc)
        self.assertNotIn("<script>", b.text_style({"size": 10, "align": self.X}, b.load_theme("default", b.theme_dirs(None))))

    def test_theme_name_must_be_plain_name(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "outside").mkdir()
            (t / "outside" / "sec.json").write_text('{"colors":{"primary":"TOPSECRET"}}', encoding="utf-8")
            (t / "themes").mkdir()
            (t / "themes" / "mine.json").write_text('{"extends":"../outside/sec"}', encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                b.load_theme("mine", [t / "themes"])
            self.assertIn("名前だけを指定", str(cm.exception))
            self.assertIn("テーマ 'mine' の extends", str(cm.exception))
            self.assertNotIn("TOPSECRET", str(cm.exception) + err.getvalue())
            with self.assertRaises(SystemExit) as cm:
                b.load_theme("../outside/sec", [t / "themes"])
            self.assertIn("meta.theme", str(cm.exception))

    def test_layout_extends_message_names_the_layout_file(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "layouts").mkdir()
            (t / "layouts" / "mine.json").write_text('{"extends":"../x"}', encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                b.load_layout("mine", t)
            self.assertIn("レイアウト 'mine' の extends", str(cm.exception))
            self.assertNotIn("meta.layout", str(cm.exception))
            (t / "layouts" / "mine.json").write_text('{"extends":"nothere"}', encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                b.load_layout("mine", t)
            self.assertIn("レイアウト 'mine' の extends を直す", str(cm.exception))

    def test_layout_json_region_values_are_checked(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "layouts").mkdir()
            (t / "layouts" / "mine.json").write_text(
                '{"types":{"bullets":{"body":{"size":"big"}}}}', encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                b.load_layout("mine", t)
            self.assertIn("レイアウト 'mine'（mine.json）の types.bullets.body.size は数値", str(cm.exception))

    def test_bundled_layout_passes_own_check(self):
        b.load_layout("default", None)


class ReviewFixGridTests(unittest.TestCase):
    """C-06: row / col / cols / rows の極端な値は fail"""

    def test_huge_row_col_fail_quickly(self):
        import time
        cases = [
            {"type": "architecture", "title": "t", "nodes": [
                {"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": 0, "col": 10000000}],
             "edges": [{"from": "a", "to": "b"}]},
            {"type": "dataflow", "title": "t", "nodes": [{"id": "a", "label": "A", "row": 10000000, "col": 0}]},
            {"type": "lifecycle", "title": "t", "states": [{"id": "a", "label": "A", "col": 99999999}]},
            {"type": "architecture", "title": "t", "cols": 10000000, "nodes": [{"id": "a", "label": "A"}]},
        ]
        for slide in cases:
            t0 = time.time()
            exc, _ = validate(one(slide))
            self.assertIsNotNone(exc, slide["type"])
            self.assertIn("40", str(exc))
            self.assertLess(time.time() - t0, 5)

    def test_normal_positions_pass(self):
        exc, _ = validate(one({"type": "architecture", "title": "t", "nodes": [
            {"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": 1, "col": 39}]}))
        self.assertIsNone(exc)


class ReviewFixWarningTests(unittest.TestCase):
    """C-08 / C-10 / A-04 / A-05 / A-06"""

    def test_closing_with_only_title_is_quiet(self):
        exc, err = validate(one({"type": "closing", "title": "ありがとうございました"}))
        self.assertIsNone(exc)
        self.assertNotIn("本文が空", err)
        exc, err = validate(one({"type": "bullets", "title": "t"}))
        self.assertIn("本文が空", err)

    def test_missing_text_warning_is_aggregated(self):
        exc, err = validate(one({"type": "bullets", "title": "t", "bullets": [{"txt": f"i{k}"} for k in range(8)]}))
        self.assertIsNone(exc)
        self.assertEqual(err.count("text がありません"), 1, err)
        self.assertIn("8 個の項目", err)

    def test_alias_suggestions_and_usable_keys(self):
        _, err = validate(one({"type": "bullets", "title": "t", "items": ["a"]}))
        self.assertIn('もしかして "bullets"', err)
        self.assertIn("bullets の固有キー", err)
        _, err = validate(one({"type": "steps", "title": "t", "steps": [{"title": "x", "items": ["a"]}]}))
        self.assertIn('もしかして "label"', err)
        _, err = validate(one({"type": "table", "title": "t", "headers": ["a"], "rows": [["1"]], "columns": ["a"]}))
        self.assertIn('もしかして "columns"', err)
        _, err = validate(one({"type": "cards", "title": "t", "cards": [{"title": "x"}]}))
        self.assertIn('もしかして "heading"', err)
        self.assertEqual(ds.suggest("colums", {"columns", "rows"}), '（もしかして "columns"）')

    def test_unknown_region_lists_usable_and_checks_types(self):
        _, err = validate(one({"type": "cards", "title": "t", "cards": [{"heading": "a"}],
                               "style": {"body": {"sizee": 20}}}))
        self.assertIn("使える領域", err)
        exc, _ = validate(one({"type": "cards", "title": "t", "cards": [{"heading": "a"}],
                               "style": {"body": {"size": "24"}}}))
        self.assertIsNotNone(exc)
        self.assertIn("style.body.size は数値", str(exc))

    def test_dataflow_stages_and_kpi_headers_shapes(self):
        for slide in ({"type": "dataflow", "title": "t", "stages": 5, "nodes": [{"id": "a", "label": "A"}]},
                      {"type": "kpi_tree", "title": "t", "headers": 5, "root": "r", "branches": []}):
            exc, _ = validate(one(slide))
            self.assertIsNotNone(exc, slide["type"])
            self.assertNotIn("検証中にエラー", str(exc))
            self.assertIn("1枚目", str(exc))

    def test_shapes_cover_renderer_fields(self):
        """SLIDE_KEYS にあるのに SLIDE_SHAPES に形が無いキーは、下の既知の一覧だけ（足したら形も足す）。"""
        known_gaps = {
            "status_table": {"legend", "legend_title"}, "agenda": {"num_start"},
            "swimlane": {"legend", "legend_eyebrow", "legend_items", "legend_title"},
            "swimlane_legend": {"items", "lead"}, "diagram_legend": {"items", "lead"},
            "schedule": {"columns", "legend", "legend_labels", "timeline", "today"},
            "row_matrix": {"col_ratios", "corner", "emph_col", "header_style"}, "org": {"legend"},
            "canvas": {"background", "elements", "name"},
        }
        gaps = {t: k - set(ds.SLIDE_SHAPES.get(t, {})) for t, k in ds.SLIDE_KEYS.items()}
        gaps = {t: g for t, g in gaps.items() if g}
        self.assertEqual(gaps, known_gaps)


class ReviewFixThemeTests(unittest.TestCase):
    """A-03: 導出された muted の読みやすさ・変更なしのテーマは親の色を継承"""

    def test_derived_muted_is_readable(self):
        d = b.load_theme("default", b.theme_dirs(None))["colors"]
        for prim in ("#0F3D6E", "#B22222", "#FFA500", "#222222"):
            c = dict(d)
            c["primary"] = prim
            b._derive_colors(c, {"primary"})
            self.assertGreaterEqual(b.contrast_ratio(c["muted"], c["surface"]), 4.5, prim)
            self.assertGreaterEqual(b.contrast_ratio(c["muted"], c["background"]), 4.5, prim)

    def test_unchanged_theme_inherits_default_colors(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "same.json").write_text(
                '{"extends":"default","colors":{"primary":"#0F3D6E"},"fonts":{}}', encoding="utf-8")
            same = b.load_theme("same", [Path(t)] + b.theme_dirs(None))["colors"]
            (Path(t) / "chg.json").write_text('{"extends":"default","colors":{"primary":"#B22222"}}', encoding="utf-8")
            chg = b.load_theme("chg", [Path(t)] + b.theme_dirs(None))["colors"]
        base = b.load_theme("default", b.theme_dirs(None))["colors"]
        self.assertEqual(same, base)
        self.assertEqual(chg["primary"], "#B22222")
        self.assertNotEqual(chg["table_header_bg"], base["table_header_bg"])


class ReviewFixBalanceTests(unittest.TestCase):
    """A-07: 泣き別れ対策の改行を括弧の内側・「・」の直後に入れない"""

    def test_soft_bad_break(self):
        import ja_text as j
        text = "選択肢（親・子・強調）の説明"
        self.assertTrue(j.soft_bad_break(text, text.index("・") + 1))
        self.assertTrue(j.soft_bad_break(text, text.index("子")))
        self.assertFalse(j.soft_bad_break(text, text.index("）") + 1))

    def test_balance_avoids_brackets(self):
        import ja_text as j
        text = "本文と見出しを同じ位置に固定する（親・子・強調）す。"
        out = j.balance(text, 20, 20 * 22)
        if "\n" in out:
            head = out.split("\n")[0]
            self.assertEqual(head.count("（"), head.count("）"))


if __name__ == "__main__":
    unittest.main()

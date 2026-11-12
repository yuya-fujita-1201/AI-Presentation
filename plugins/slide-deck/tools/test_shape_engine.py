#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2b テーマの形（トークンと shape プリセット）のテスト。

トークン解決・未知トークン・shape の探索と検証・解決順・rule.style 4 種の HTML / PPTX・weight / tracking の PPTX XML・
shape 未指定（classic）が従来と同じ出力になること・角丸の付け方（提案書系・パターン）。

実行: python3 -m unittest plugins/slide-deck/tools/test_shape_engine.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import proposal_engine as pe  # noqa: E402
import shape_engine as shp  # noqa: E402
from test_validation import one, validate, write_deck  # noqa: E402

PY = sys.executable
BUNDLED = ("classic", "sharp", "soft", "editorial")

BULLETS = {"type": "bullets", "eyebrow": "Section", "title": "形のテスト", "lead": "リード文",
           "bullets": ["一つ目", "二つ目"]}
CARDS = {"type": "cards", "title": "カード", "cards": [{"heading": "A", "body": "本文"}, {"heading": "B", "body": "本文"}]}
SECTION = {"type": "section", "number": "01", "title": "章扉"}


def build(deck_dir, *extra):
    return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir), *extra], capture_output=True, text=True, encoding="utf-8")


def deck_of(slides, **meta):
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    return {"meta": m, "slides": slides}


def html_of(tmp, deck, name="d"):
    d = write_deck(tmp, deck, name)
    r = build(d, "--html")
    assert r.returncode == 0, r.stderr
    return next((d / "build").glob("*.html")).read_text(encoding="utf-8")


def load(deck, deck_dir=None):
    with tempfile.TemporaryDirectory() as tmp:
        d = write_deck(tmp, deck) if deck_dir is None else deck_dir
        with contextlib.redirect_stderr(io.StringIO()):
            return b.load_deck(d)


class TokenResolveTests(unittest.TestCase):
    TOKENS = {"radius": {"card": 12, "pill": 999}, "rule": {"style": "line"}}

    def test_resolve_refs_replaces_nested_values(self):
        out = shp.resolve_refs({"a": {"radius": "$radius.card", "k": ["$radius.pill", "x"]}}, self.TOKENS)
        self.assertEqual(out, {"a": {"radius": 12, "k": [999, "x"]}})

    def test_resolve_refs_does_not_touch_original(self):
        src = {"a": "$radius.card"}
        shp.resolve_refs(src, self.TOKENS)
        self.assertEqual(src, {"a": "$radius.card"})

    def test_unknown_token_names_candidate(self):
        with self.assertRaises(ValueError) as cm:
            shp.resolve_refs({"radius": "$radius.cad"}, self.TOKENS, "style")
        self.assertIn("$radius.card", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            shp.resolve_refs({"radius": "$radus.card"}, self.TOKENS)
        self.assertIn("radius", str(cm.exception))

    def test_plain_strings_are_not_refs(self):
        for v in ("$5", "price $10.5 each", "$radius", "primary", 12):
            self.assertFalse(shp.is_ref(v), v)

    def test_default_layout_resolves_to_classic_values(self):
        layout = b.load_layout("default")
        self.assertTrue(layout["_tokens_resolved"])
        self.assertEqual(layout["types"]["bullets"]["title"]["size"], 36)
        self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 12)
        self.assertEqual(layout["types"]["two_column"]["left"]["radius"], 14)
        self.assertEqual(layout["types"]["bullets"]["rule"]["h"], 5)
        self.assertEqual(layout["types"]["section"]["rule"]["h"], 6)
        self.assertEqual(layout["types"]["architecture"]["diagram"]["node_radius"], 10)
        self.assertEqual(layout["types"]["bullets"]["title"]["weight"], 700)

    def test_raw_json_layout_is_resolved_by_resolve_style_and_validate(self):
        raw = json.loads((TOOLS.parent / "templates" / "layouts" / "default.json").read_text(encoding="utf-8"))
        st = b.resolve_style(raw, {"meta": {}}, {"type": "cards", "title": "t", "cards": []})
        self.assertEqual(st["grid"]["radius"], 12)

    def test_style_and_overrides_accept_token_refs(self):
        deck = deck_of([dict(CARDS, style={"grid": {"radius": "$radius.pill"}})],
                       layout_overrides={"bullets": {"title": {"size": "$type.h2"}}})
        exc, err = validate(deck)
        self.assertIsNone(exc, err)
        deck_, theme, layout = load(deck)
        st = b.resolve_style(layout, deck_, deck_["slides"][0])
        self.assertEqual(st["grid"]["radius"], 999)
        st = b.resolve_style(layout, deck_, dict(BULLETS))
        self.assertEqual(st["title"]["size"], 28)

    def test_unknown_token_in_style_fails_with_candidate(self):
        exc, err = validate(deck_of([dict(CARDS, style={"grid": {"radius": "$radius.cardd"}})]))
        self.assertIsNotNone(exc)
        self.assertIn("$radius.card", str(exc) + err)


class ShapeFileTests(unittest.TestCase):
    def test_bundled_shapes_exist_and_validate_clean(self):
        names = [n for n, _ in shp.list_shapes()]
        for n in BUNDLED:
            self.assertIn(n, names)
        base = b.load_layout("default")["tokens"]
        for n in BUNDLED:
            data = shp.load_shape(n)
            self.assertEqual(shp.validate_shape(data, n, base), [], n)

    def test_bundled_shapes_tokens_all_known_to_layout(self):
        base = b.load_layout("default")["tokens"]
        for n in BUNDLED:
            for grp, group in shp.load_shape(n).get("tokens", {}).items():
                for name in group:
                    self.assertIn(name, base[grp], f"{n}: tokens.{grp}.{name} がレイアウトに無い")

    def test_validate_catches_bad_values_and_typos(self):
        base = b.load_layout("default")["tokens"]
        issues = shp.validate_shape({"tokens": {"radius": {"card": -1}, "rule": {"style": "wavy"},
                                                "weight": {"heading": 1200}, "tracking": {"heading": "x"},
                                                "shadow": {"alpha": 2}, "case": {"eyebrow": "lower"}}}, "t", base)
        fails = [m for lv, m in issues if lv == "fail"]
        self.assertEqual(len(fails), 6, issues)
        issues = shp.validate_shape({"tokens": {"radius": {"cadr": 4}}, "layuot": {}, "tokenz": {}}, "t", base)
        warns = " ".join(m for lv, m in issues if lv == "warn")
        self.assertIn("もしかして \"card\"", warns)
        self.assertIn("layuot", warns)
        self.assertEqual([m for lv, m in issues if lv == "fail"], [])

    def test_bad_names_are_rejected(self):
        for bad in ("../x", "a/b", ".hidden", "/abs", "", None, 3):
            self.assertIsNotNone(shp.check_name(bad), repr(bad))
        self.assertIsNone(shp.check_name("sharp"))

    def test_unknown_shape_fails_with_candidate(self):
        with self.assertRaises(ValueError) as cm:
            shp.load_shape("shrap")
        self.assertIn("もしかして \"sharp\"", str(cm.exception))
        exc, _ = validate(deck_of([BULLETS], shape="nope"))   # validate は load_deck を通らないので build で確かめる
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], shape="shrap"))
            r = build(d, "--html")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("sharp", r.stderr)
            d = write_deck(tmp, deck_of([BULLETS], shape="../evil"), "e")
            r = build(d, "--html")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("名前だけ", r.stderr)

    def test_user_shape_is_found_in_deck_folder_and_env(self):
        shape = {"name": "mine", "tokens": {"radius": {"card": 3}}}
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([CARDS], shape="mine"))
            (d / "shapes").mkdir()
            (d / "shapes" / "mine.json").write_text(json.dumps(shape), encoding="utf-8")
            _deck, theme, layout = b.load_deck(d)
            self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 3)
            # 環境変数の置き場
            d2 = write_deck(tmp, deck_of([CARDS], shape="envshape"), "d2")
            env_dir = Path(tmp) / "envshapes"
            env_dir.mkdir()
            (env_dir / "envshape.json").write_text(json.dumps({"tokens": {"radius": {"card": 5}}}), encoding="utf-8")
            old = os.environ.get("SLIDE_DECK_SHAPES")
            os.environ["SLIDE_DECK_SHAPES"] = str(env_dir)
            try:
                _deck, _theme, layout = b.load_deck(d2)
            finally:
                if old is None:
                    os.environ.pop("SLIDE_DECK_SHAPES")
                else:
                    os.environ["SLIDE_DECK_SHAPES"] = old
            self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 5)


class OrderTests(unittest.TestCase):
    def test_default_theme_shape_meta_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([CARDS], shape="soft", theme="mytheme"))
            (d / "themes").mkdir()
            (d / "themes" / "mytheme.json").write_text(json.dumps({"extends": "default", "shape": "sharp"}), encoding="utf-8")
            _deck, theme, layout = b.load_deck(d)
            self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 20)       # meta.shape が優先
            self.assertEqual(theme["_shape"], "soft")
            deck = deck_of([CARDS], theme="mytheme")
            (d / "deck.json").write_text(json.dumps(deck), encoding="utf-8")
            _deck, theme, layout = b.load_deck(d)
            self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 0)        # shape 指定が無ければテーマの shape
            self.assertEqual(theme["_shape"], "sharp")

    def test_theme_tokens_and_layout_override_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([CARDS, BULLETS], shape="soft", theme="mytheme"))
            (d / "themes").mkdir()
            (d / "themes" / "mytheme.json").write_text(json.dumps({
                "extends": "default", "tokens": {"radius": {"card": 7}},
                "layout": {"types": {"bullets": {"title": {"size": 30}}}}}), encoding="utf-8")
            deck, theme, layout = b.load_deck(d)
            self.assertEqual(layout["types"]["cards"]["grid"]["radius"], 7)        # テーマの tokens > shape の tokens
            self.assertEqual(layout["types"]["bullets"]["title"]["size"], 30)      # テーマの layout > 既定
            self.assertEqual(theme["tokens"]["radius"]["panel"], 24)               # 書かなかったトークンは shape の値
            deck["slides"][0]["style"] = {"grid": {"radius": 2}}
            st = b.resolve_style(layout, deck, deck["slides"][0])
            self.assertEqual(st["grid"]["radius"], 2)                              # slide.style が最優先

    def test_shape_layout_diff_applies_and_user_layout_values_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], shape="myshape",
                                        layout_overrides={"bullets": {"title": {"size": 20}}}))
            (d / "shapes").mkdir()
            (d / "shapes" / "myshape.json").write_text(json.dumps({"layout": {"types": {"bullets": {"title": {"size": 44, "y": 30}}}}}),
                                                       encoding="utf-8")
            deck, _theme, layout = b.load_deck(d)
            self.assertEqual(layout["types"]["bullets"]["title"]["y"], 30)
            st = b.resolve_style(layout, deck, deck["slides"][0])
            self.assertEqual(st["title"]["size"], 20)                              # layout_overrides > shape
            self.assertEqual(st["title"]["y"], 30)

    def test_theme_tokens_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], theme="bad"))
            (d / "themes").mkdir()
            (d / "themes" / "bad.json").write_text(json.dumps({"extends": "default", "tokens": {"radius": {"card": "big"}}}),
                                                   encoding="utf-8")
            r = build(d, "--html")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("radius.card", r.stderr)

    def test_pattern_engine_reads_the_same_resolved_tokens(self):
        import pattern_engine
        _deck, theme, _layout = load(deck_of([BULLETS], shape="soft"))
        self.assertEqual(pattern_engine._tokens(theme)["radius"]["card"], 20)
        self.assertEqual(pattern_engine.DEFAULT_TOKENS["radius"]["card"], 12)


class RuleStyleTests(unittest.TestCase):
    def st(self, style, t="bullets", **extra):
        tokens = {"rule": dict({"style": style, "length": 80, "gap": 16}, **extra)}
        layout = b.load_layout("default")
        st = copy.deepcopy(b.resolve_style(layout, {"meta": {}}, {"type": t, "title": "t"}))
        st2 = copy.deepcopy(layout["types"][t])
        shp.apply_rule_style(st2, tokens, t)
        return st2

    def test_line_keeps_full_width(self):
        self.assertEqual(self.st("line")["rule"]["w"], 1136)

    def test_short_shrinks_to_length(self):
        r = self.st("short")["rule"]
        self.assertEqual((r["x"], r["w"]), (72, 80))

    def test_none_removes_rule(self):
        self.assertNotIn("rule", self.st("none"))

    def test_bar_left_sits_left_of_title_and_keeps_title_x(self):
        st = self.st("bar-left")
        self.assertEqual(st["title"]["x"], 72)
        r = st["rule"]
        self.assertEqual(r["w"], 5)                                    # 太さ = line.rule
        self.assertEqual(r["x"], 72 - 16 - 5)
        self.assertGreater(r["h"], r["w"])

    def test_bar_left_on_section_falls_back_to_short(self):
        r = self.st("bar-left", "section")["rule"]
        self.assertEqual(r["w"], 80)

    def test_html_and_pptx_for_each_style(self):
        from pptx import Presentation
        for style, shape in (("none", {"rule": {"style": "none"}}), ("short", {"rule": {"style": "short", "length": 90}}),
                             ("bar-left", {"rule": {"style": "bar-left"}}), ("line", {})):
            with self.subTest(style=style), tempfile.TemporaryDirectory() as tmp:
                d = write_deck(tmp, deck_of([BULLETS], shape="r"))
                (d / "shapes").mkdir()
                (d / "shapes" / "r.json").write_text(json.dumps({"tokens": shape}), encoding="utf-8")
                r = build(d)
                self.assertEqual(r.returncode, 0, r.stderr)
                html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
                prs = Presentation(str(next((d / "build").glob("*.pptx"))))
                accent_rects = [s for s in prs.slides[0].shapes if s.shape_type == 1 and s.fill.type == 1
                                and str(s.fill.fore_color.rgb) == "007D96"]
                n_html = html.count("background:#007D96;")
                if style == "none":
                    self.assertEqual(len(accent_rects), 0)
                    self.assertEqual(n_html, 0)
                else:
                    self.assertEqual(len(accent_rects), 1)
                    self.assertEqual(n_html, 1)
                    w_px = accent_rects[0].width / 9525
                    if style == "short":
                        self.assertAlmostEqual(w_px, 90, delta=0.5)
                        self.assertIn("width:90px;", html)
                    elif style == "bar-left":
                        self.assertAlmostEqual(w_px, 5, delta=0.5)
                        self.assertAlmostEqual(accent_rects[0].left / 9525, 72 - 14 - 5, delta=0.5)
                    else:
                        self.assertAlmostEqual(w_px, 1136, delta=0.5)


class TextTokenTests(unittest.TestCase):
    def test_text_style_weight_tracking_case(self):
        css = b.text_style({"size": 20, "color": "#112233", "bold": True, "weight": 500, "tracking": 0.12, "case": "upper"}, {"colors": {}})
        self.assertIn("font-weight:500;", css)
        self.assertIn("letter-spacing:0.12em;", css)
        self.assertIn("text-transform:uppercase;", css)
        plain = b.text_style({"size": 20, "color": "#112233", "bold": True, "weight": 700}, {"colors": {}})
        self.assertIn("font-weight:700;", plain)
        self.assertNotIn("letter-spacing", plain)
        self.assertEqual(b.text_style({"size": 20, "color": "#112233", "weight": 400}, {"colors": {}}),
                         "font-size:20px;color:#112233;")

    def test_bold_flag_follows_weight(self):
        self.assertTrue(shp.is_bold({"bold": True}))
        self.assertTrue(shp.is_bold({"bold": True, "weight": 600}))
        self.assertFalse(shp.is_bold({"bold": True, "weight": 500}))
        self.assertEqual(shp.weight_of({"bold": True}), 700)
        self.assertEqual(shp.weight_of({}), 400)

    def test_pptx_xml_has_spc_cap_and_bold_off_for_light_weight(self):
        from pptx import Presentation
        from pptx.oxml.ns import qn
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], shape="editorial"))
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
            runs = {}
            for sh in prs.slides[0].shapes:
                if sh.has_text_frame and sh.text_frame.text:
                    rpr = sh.text_frame.paragraphs[0].runs[0]._r.find(qn("a:rPr"))
                    runs[sh.text_frame.text] = rpr
            eb = runs["Section"]                       # eyebrow: 大文字・字間 0.14em・weight 600（太字）
            self.assertEqual(eb.get("cap"), "all")
            self.assertEqual(eb.get("spc"), str(int(round(0.14 * 13 * 75))))
            self.assertEqual(eb.get("b"), "1")
            title = runs["形のテスト"]                   # 見出し: weight 500 → 太字なし。サイズは type.h1 = 40px
            self.assertNotEqual(title.get("b"), "1")
            self.assertEqual(title.get("sz"), str(int(40 * 75)))
            self.assertIsNone(title.get("spc"))

    def test_sharp_tracking_is_negative_in_pptx(self):
        from pptx import Presentation
        from pptx.oxml.ns import qn
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], shape="sharp"))
            self.assertEqual(build(d).returncode, 0)
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
            for sh in prs.slides[0].shapes:
                if sh.has_text_frame and sh.text_frame.text == "形のテスト":
                    rpr = sh.text_frame.paragraphs[0].runs[0]._r.find(qn("a:rPr"))
                    self.assertEqual(rpr.get("spc"), str(int(round(-0.01 * 36 * 75))))
                    self.assertEqual(rpr.get("b"), "1")

    def test_autofit_widths_include_tracking(self):
        import autofit
        long = "あ" * 28
        plain = autofit.fit_text_size(long, 1000, 64, 36, 20, 1.2, heading=True, bold=True)
        wide = autofit.fit_text_size(long, 1000 / 1.3, 64, 36, 20, 1.2, heading=True, bold=True)
        self.assertLessEqual(wide["size"], plain["size"])
        self.assertAlmostEqual(shp.width_factor({"tracking": 0.3}), 1.3)
        self.assertEqual(shp.width_factor({}), 1.0)


class ClassicIdentityTests(unittest.TestCase):
    """shape を指定しない（または classic）デッキは従来と同じ出力（HTML は文字列が一致、PPTX の形の XML も一致）"""

    SLIDES = [{"type": "title", "title": "表紙"}, BULLETS, CARDS, SECTION,
              {"type": "summary", "title": "要旨", "items": [{"lead": "a", "text": "b"}, {"lead": "c", "text": "d"}], "conclusion": "結論"},
              {"type": "two_column", "title": "二列", "left": {"heading": "L", "bullets": ["x"]}, "right": {"heading": "R", "bullets": ["y"]}},
              {"type": "steps", "title": "手順", "steps": [{"label": "a", "items": ["1"]}, {"label": "b", "items": ["2"]}]}]

    def test_html_is_identical_for_unspecified_and_classic(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = html_of(tmp, deck_of(self.SLIDES), "a")
            c = html_of(tmp, deck_of(self.SLIDES, shape="classic"), "c")
            self.assertEqual(a, c)

    def test_classic_html_has_no_new_style_properties(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = html_of(tmp, deck_of(self.SLIDES))
        for needle in ("letter-spacing", "text-transform", "box-shadow", "font-weight:500", "font-weight:800"):
            self.assertNotIn(needle, html)

    def test_classic_pptx_has_no_spc_cap_or_shadow(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of(self.SLIDES))
            self.assertEqual(build(d).returncode, 0)
            z = zipfile.ZipFile(next((d / "build").glob("*.pptx")))
            xml = "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        self.assertNotIn(' spc="', xml)
        self.assertNotIn(' cap="', xml)
        self.assertNotIn("outerShdw", xml)


class BoxShapeTests(unittest.TestCase):
    def test_soft_cards_have_radius_shadow_and_no_border_in_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = html_of(tmp, deck_of([CARDS], shape="soft"))
        self.assertIn("border-radius:20px", html)
        self.assertIn("box-shadow:0 6px 18px rgba(15,23,42,0.100)", html)
        self.assertNotIn("border:1px solid", html)

    def test_sharp_has_no_border_radius_on_boxes(self):
        two = {"type": "two_column", "title": "二列", "left": {"heading": "L", "bullets": ["x"]}, "right": {"heading": "R", "bullets": ["y"]}}
        with tempfile.TemporaryDirectory() as tmp:
            html = html_of(tmp, deck_of([CARDS, two], shape="sharp"))
        import re
        self.assertIsNone(re.search(r"border-radius:[1-9]", html))      # 0px だけ（角丸なし）

    def test_soft_pptx_box_has_shadow_effect_and_zero_border_hidden(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([CARDS], shape="soft"))
            self.assertEqual(build(d).returncode, 0)
            z = zipfile.ZipFile(next((d / "build").glob("*.pptx")))
            xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertEqual(xml.count("<a:outerShdw"), 2)       # カード 2 枚
        self.assertIn('prst="roundRect"', xml)

    def test_border_w_zero_hides_the_outline_in_pptx(self):
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([CARDS], shape="soft"))
            self.assertEqual(build(d).returncode, 0)
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
            boxes = [s for s in prs.slides[0].shapes if s.shape_type == 1 and s.fill.type == 1 and str(s.fill.fore_color.rgb) == "E0E7F0"]
            self.assertEqual(len(boxes), 2)
            for s in boxes:
                self.assertEqual(s.line.fill.type, 5)        # MSO_FILL.BACKGROUND = 線なし

    def test_radius_pill_zero_squares_the_chips_and_pptx_builds(self):
        # 見本の図解・表・グラフ系をすべて sharp（pill / 角丸 0）で PPTX まで組める（adjustments の無い図形で落ちない）
        sample = json.loads((TOOLS.parent / "examples" / "template-sample" / "deck.json").read_text(encoding="utf-8"))
        slides = [s for s in sample["slides"] if s["type"] in
                  ("architecture", "dataflow", "lifecycle", "sequence", "swimlane", "swimlane_legend", "schedule", "agenda", "diagram_legend")]
        self.assertGreaterEqual(len(slides), 7)
        for shape in ("sharp", "soft", "editorial"):
            with tempfile.TemporaryDirectory() as tmp:
                deck = {"meta": dict(sample["meta"], shape=shape), "slides": slides}
                d = write_deck(tmp, deck)
                for sub in ("assets",):
                    src = TOOLS.parent / "examples" / "template-sample" / sub
                    if src.exists():
                        import shutil
                        shutil.copytree(src, d / sub)
                r = build(d)
                self.assertEqual(r.returncode, 0, shape + r.stderr[-600:])


class RoundBoxesTests(unittest.TestCase):
    def box(self, x, y, w, h, name="b", fill="#112233"):
        return {"kind": "shape", "geom": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "name": name}

    def test_zero_radius_is_a_noop(self):
        els = [self.box(0, 0, 100, 40)]
        self.assertEqual(pe.round_boxes(copy.deepcopy(els), 0), els)

    def test_lone_box_becomes_round_rect(self):
        e = pe.round_boxes([self.box(10, 10, 200, 60)], 14)[0]
        self.assertEqual(e["geom"], "roundRect")
        self.assertEqual(e["adj"]["adj"], int(14 / 60 * 100000))

    def test_adjacent_boxes_keep_the_shared_edge_square(self):
        left, right = pe.round_boxes([self.box(0, 0, 64, 50, "num"), self.box(64, 0, 300, 50, "band")], 12)
        self.assertEqual(left["geom"], "custom")
        self.assertEqual(right["geom"], "custom")
        # 左の箱: 右側の 2 隅は直角（パスの右上・右下に曲線 C が無い）
        cmds = left["path"][0]["cmds"]
        cs = [c for c in cmds if c[0] == "C"]
        self.assertEqual(len(cs), 2)
        self.assertEqual(len([c for c in right["path"][0]["cmds"] if c[0] == "C"]), 2)

    def test_stacked_boxes_keep_the_shared_edge_square(self):
        head, body = pe.round_boxes([self.box(0, 0, 200, 30, "head"), self.box(0, 30, 200, 100, "body")], 10)
        self.assertEqual(len([c for c in head["path"][0]["cmds"] if c[0] == "C"]), 2)
        self.assertEqual(len([c for c in body["path"][0]["cmds"] if c[0] == "C"]), 2)

    def test_badge_inside_a_box_is_rounded_like_its_container(self):
        outer, badge = pe.round_boxes([self.box(0, 0, 400, 80, "outer"), self.box(0, 0, 34, 80, "badge")], 12)
        self.assertEqual(outer["geom"], "roundRect")
        self.assertEqual(badge["geom"], "roundRect")

    def test_thin_bars_and_background_are_left_alone(self):
        bar, bg = pe.round_boxes([self.box(0, 0, 64, 4), self.box(0, 0, 1280, 720)], 14)
        self.assertEqual(bar["geom"], "rect")
        self.assertEqual(bg["geom"], "rect")

    def test_corner_path_is_closed_and_inside_box(self):
        cmds = pe.corner_path(100, 40, (10, 0, 10, 0))
        self.assertEqual(cmds[0][0], "M")
        self.assertEqual(cmds[-1], ["Z"])
        for c in cmds[:-1]:
            for v in c[1:]:
                self.assertGreaterEqual(v, 0)
                self.assertLessEqual(v, 100)

    def test_summary_slide_renders_rounded_under_soft(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([{"type": "summary", "title": "要旨", "conclusion": "結論",
                                          "items": [{"lead": "a", "text": "b"}, {"lead": "c", "text": "d"}]}], shape="soft"))
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_kpi_and_chart_conclusion_band_is_rounded(self):
        kpi = {"type": "kpi", "title": "t", "conclusion": "結論", "items": [{"value": "1", "label": "a"}]}
        layout = b.load_layout("default")
        deck = deck_of([kpi])
        _d, theme, layout = load(deck_of([kpi], shape="soft"))
        st = b.resolve_style(layout, deck, kpi)
        els = pe.layout(kpi, st, theme)
        band = [e for e in els if e.get("name") == "結論"][0]
        self.assertEqual(band["geom"], "roundRect")


class PatternShapeTests(unittest.TestCase):
    TOKENS_SOFT = None

    def tokens(self, name):
        data = shp.load_shape(name)
        return shp.merge_tokens(shp.default_tokens(), data["tokens"])

    def pattern_els(self):
        return [
            {"kind": "shape", "x": 72, "y": 16, "w": 1136, "h": 24, "_role": "eyebrow",
             "text": {"paragraphs": [{"runs": [{"text": "Section", "size": 15, "bold": True}]}]}},
            {"kind": "shape", "x": 72, "y": 42, "w": 1136, "h": 64, "_role": "title",
             "text": {"paragraphs": [{"runs": [{"text": "題", "size": 36, "bold": True}]}]}},
            {"kind": "shape", "x": 72, "y": 106, "w": 1136, "h": 5, "fill": "#007D96", "_role": "rule"},
        ]

    def test_classic_changes_nothing_but_drops_role_marks(self):
        els = self.pattern_els()
        out = shp.apply_pattern_shape(copy.deepcopy(els), shp.default_tokens())
        for a, c in zip(els, out):
            c2 = dict(c)
            self.assertNotIn("_role", c2)
            a2 = {k: v for k, v in a.items() if k != "_role"}
            self.assertEqual(a2, c2)

    def test_editorial_makes_bar_left_and_uppercase_eyebrow(self):
        out = shp.apply_pattern_shape(self.pattern_els(), self.tokens("editorial"))
        rule = out[2]
        self.assertEqual(rule["w"], 6)
        self.assertEqual(rule["x"], 72 - 16 - 6)
        run = out[0]["text"]["paragraphs"][0]["runs"][0]
        self.assertEqual(run["text"], "SECTION")
        self.assertAlmostEqual(run["tracking"], 0.14)

    def test_short_and_none(self):
        out = shp.apply_pattern_shape(self.pattern_els(), self.tokens("soft"))
        self.assertEqual(out[2]["w"], 72)
        self.assertEqual(out[2]["geom"], "roundRect")
        tok = self.tokens("soft")
        tok["rule"]["style"] = "none"
        out = shp.apply_pattern_shape(self.pattern_els(), tok)
        self.assertEqual(len(out), 2)

    def test_clip_bands_cuts_a_band_at_a_rounded_corner(self):
        card = {"kind": "shape", "geom": "roundRect", "adj": {"adj": int(20 / 100 * 100000)}, "x": 0, "y": 0, "w": 200, "h": 100, "fill": "#EEEEEE"}
        band = {"kind": "shape", "geom": "rect", "x": 0, "y": 0, "w": 200, "h": 8, "fill": "#007D96"}
        mid = {"kind": "shape", "geom": "rect", "x": 20, "y": 30, "w": 100, "h": 4, "fill": "#007D96"}
        shp.clip_bands([card, band, mid])
        self.assertEqual(band["geom"], "custom")
        xs = [v for c in band["path"][0]["cmds"] if c[0] in "ML" for v in c[1:2]]
        self.assertGreater(min(xs), -0.01)
        self.assertLessEqual(max(xs), 200.01)
        self.assertEqual(mid["geom"], "rect")                  # 角にかからない要素は触らない

    def test_pillars_pattern_follows_the_shape_in_html(self):
        pat = {"type": "pattern", "pattern": "pillars", "slots": {
            "title": "柱", "pillars": [{"head": "a", "body": "b"}, {"head": "c", "body": "d"}, {"head": "e", "body": "f"}],
            "foundation": "土台"}}
        with tempfile.TemporaryDirectory() as tmp:
            classic = html_of(tmp, deck_of([pat]), "c")
            edit = html_of(tmp, deck_of([pat], shape="editorial"), "e")
        self.assertNotIn("data-role", classic)
        self.assertNotIn("_role", edit)
        self.assertNotEqual(classic, edit)

    def test_role_key_does_not_break_pattern_check(self):
        r = subprocess.run([PY, str(TOOLS / "pattern_engine.py"), "check", str(TOOLS.parent / "templates" / "patterns" / "pillars.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ImageRadiusTests(unittest.TestCase):
    def test_image_slide_gets_rounded_picture_under_soft(self):
        from PIL import Image
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([{"type": "image", "title": "図", "path": "assets/a.png"}], shape="soft"))
            (d / "assets").mkdir()
            Image.new("RGB", (800, 400), (30, 90, 160)).save(d / "assets" / "a.png")
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
            self.assertIn("border-radius:20px;object-fit:contain", html)
            xml = zipfile.ZipFile(next((d / "build").glob("*.pptx"))).read("ppt/slides/slide1.xml").decode("utf-8")
            self.assertIn('<a:prstGeom prst="roundRect">', xml)

    def test_image_slide_is_plain_under_classic(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([{"type": "image", "title": "図", "path": "assets/a.png"}]))
            (d / "assets").mkdir()
            Image.new("RGB", (800, 400), (30, 90, 160)).save(d / "assets" / "a.png")
            self.assertEqual(build(d, "--html").returncode, 0)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
            self.assertIn("width:100%;height:100%;object-fit:contain;", html)


class ToolsTests(unittest.TestCase):
    def test_check_theme_lists_shapes(self):
        r = subprocess.run([PY, str(TOOLS / "check_theme.py"), "--shapes"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for n in BUNDLED:
            self.assertIn(n, r.stdout)

    def test_check_theme_shapes_flags_a_broken_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "broken.json").write_text(json.dumps({"tokens": {"radius": {"card": "big"}}}), encoding="utf-8")
            env = dict(os.environ, SLIDE_DECK_SHAPES=tmp)
            r = subprocess.run([PY, str(TOOLS / "check_theme.py"), "--shapes"], capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("radius.card", r.stdout + r.stderr)

    def test_new_theme_writes_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([PY, str(TOOLS / "new_theme.py"), "shapey", "--shape", "soft", "--dir", tmp],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            data = json.loads(Path(tmp, "shapey.json").read_text(encoding="utf-8"))
            self.assertEqual(data["shape"], "soft")

    def test_new_theme_rejects_unknown_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([PY, str(TOOLS / "new_theme.py"), "shapey", "--shape", "shrap", "--dir", tmp],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("sharp", r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# レビュー指摘の修正（s2b-C-01〜C-08, s2b-A-01〜A-08）
# ---------------------------------------------------------------------------

def _runs_of(slide):
    """PPTX スライドの {テキスト: rPr}。"""
    from pptx.oxml.ns import qn
    out = {}
    for sh in slide.shapes:
        if sh.has_text_frame:
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    if r.text:
                        out[r.text] = r._r.find(qn("a:rPr"))
    return out


class BoldOverridesWeightTests(unittest.TestCase):
    """C-01: style / layout_overrides の bold は、レイアウト・shape 由来の weight より優先する。"""

    def test_apply_bold_override_unit(self):
        st = {"lead": {"bold": False, "weight": 400}, "title": {"bold": True, "weight": 700}, "t2": {"bold": True, "weight": 500}}
        shp.apply_bold_override(st, {"lead": {"bold": True}, "title": {"bold": False}, "t2": {"bold": True}})
        self.assertNotIn("weight", st["lead"])
        self.assertNotIn("weight", st["title"])
        self.assertNotIn("weight", st["t2"])                 # 500 は太字未満なので外して 700 にする
        st = {"title": {"bold": True, "weight": 800}}
        shp.apply_bold_override(st, {"title": {"bold": True}})
        self.assertEqual(st["title"]["weight"], 800)         # 既に太字の weight（shape の見出し）は残す
        st = {"title": {"bold": True, "weight": 800}}
        shp.apply_bold_override(st, {"title": {"bold": True, "weight": 300}})
        self.assertEqual(st["title"]["weight"], 800)         # weight を明示した層は触らない（deep_merge 側で 300 が勝つ）

    def test_html_and_pptx_lead_bold_true_wins_over_body_weight(self):
        from pptx import Presentation
        deck = deck_of([BULLETS, dict(BULLETS, title="B2", lead="リード太字", style={"lead": {"bold": True}})],
                       layout_overrides={"title": {"subtitle": {"bold": True}}})
        deck["slides"].insert(0, {"type": "title", "title": "表紙", "subtitle": "サブ太字"})
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck)
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
        self.assertRegex(html, r"font-weight:700;[^>]*>リード太字")
        self.assertRegex(html, r"font-weight:700;[^>]*>サブ太字")
        import re
        self.assertNotIn("font-weight", re.search(r"<div[^>]*>リード文", html).group(0))      # 指定していないスライドの lead は従来どおり（400 = font-weight 無し）
        self.assertEqual(_runs_of(prs.slides[2])["リード太字"].get("b"), "1")
        self.assertEqual(_runs_of(prs.slides[0])["サブ太字"].get("b"), "1")
        self.assertNotEqual(_runs_of(prs.slides[1])["リード文"].get("b"), "1")

    def test_html_and_pptx_title_bold_false_wins_over_heading_weight(self):
        from pptx import Presentation
        deck = deck_of([dict(BULLETS, title="太字なし", style={"title": {"bold": False}}), dict(BULLETS, title="太字あり")])
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck)
            self.assertEqual(build(d).returncode, 0)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
        self.assertNotRegex(html, r"font-weight:[^>]*>太字なし")
        self.assertRegex(html, r"font-weight:700;[^>]*>太字あり")
        self.assertNotEqual(_runs_of(prs.slides[0])["太字なし"].get("b"), "1")
        self.assertEqual(_runs_of(prs.slides[1])["太字あり"].get("b"), "1")

    def test_bold_true_on_light_heading_shape_gives_bold(self):
        """editorial の見出しは weight 500（太字なし）。利用者が bold:true を書けば太字になる。"""
        deck = deck_of([dict(BULLETS, style={"title": {"bold": True}})], shape="editorial")
        with tempfile.TemporaryDirectory() as tmp:
            html = html_of(tmp, deck)
        self.assertRegex(html, r"font-weight:700;[^>]*>形のテスト")


class BarLeftFollowsTitleTests(unittest.TestCase):
    """C-02 / A-06: bar-left の縦帯は、利用者のタイトル指定と自動フィットに追従する。"""

    def _bars(self, deck):
        import re
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck)
            (d / "shapes").mkdir()
            (d / "shapes" / "bl.json").write_text(json.dumps({"tokens": {"rule": {"style": "bar-left"}}}), encoding="utf-8")
            r = build(d, "--html")
            self.assertEqual(r.returncode, 0, r.stderr)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
        return [tuple(float(x) for x in m) for m in re.findall(
            r"left:(-?[\d.]+)px;top:([\d.]+)px;width:5px;height:([\d.]+)px;background:#007D96;", html)]

    def test_bar_follows_slide_style_title_position_and_size(self):
        bars = self._bars(deck_of([dict(BULLETS, style={"title": {"x": 200, "y": 120, "size": 24}})], shape="bl"))
        self.assertEqual(len(bars), 1)
        x, y, h = bars[0]
        self.assertEqual((x, y), (200 - 14 - 5, 124.0))
        self.assertAlmostEqual(h, 24 * 1.35, places=1)

    def test_bar_follows_layout_overrides_title_x(self):
        bars = self._bars(deck_of([BULLETS], shape="bl", layout_overrides={"bullets": {"title": {"x": 120}}}))
        self.assertEqual(bars[0][0], 120 - 14 - 5)

    def test_bar_follows_autofit_shrunk_title(self):
        long = "これは一行に収まらない長いタイトルです" * 3
        bars = self._bars(deck_of([dict(BULLETS, title=long)], shape="bl"))
        self.assertEqual(len(bars), 1)
        self.assertLessEqual(bars[0][2], 64 - 8)             # タイトルの枠の高さを超えない

    def test_user_rule_geometry_wins_and_h_is_thickness(self):
        tokens = {"rule": {"style": "bar-left", "gap": 14}}
        st = {"title": {"x": 72, "y": 42, "h": 64, "size": 36}, "rule": {"x": 72, "y": 106, "w": 1136, "h": 8}}
        shp.apply_rule_style(st, tokens, "bullets", user_rule={"h": 8})
        self.assertEqual(st["rule"]["w"], 8)                 # 利用者の h = 帯の太さ
        self.assertEqual(st["rule"]["x"], 72 - 14 - 8)
        st = {"title": {"x": 72, "y": 42, "h": 64, "size": 36}, "rule": {"x": 72, "y": 106, "w": 1136, "h": 5}}
        shp.apply_rule_style(st, tokens, "bullets", user_rule={"x": 30})
        self.assertEqual(st["rule"]["x"], 30)

    def test_wrapped_title_makes_taller_bar(self):
        base = {"title": {"x": 72, "y": 42, "h": 200, "size": 30, "line_height": 1.2}, "rule": {"x": 72, "y": 106, "w": 1136, "h": 5}}
        one, two = copy.deepcopy(base), copy.deepcopy(base)
        tokens = {"rule": {"style": "bar-left"}}
        shp.apply_rule_style(one, tokens, "bullets", title_lines=1)
        shp.apply_rule_style(two, tokens, "bullets", title_lines=2)
        self.assertAlmostEqual(two["rule"]["h"] - one["rule"]["h"], 30 * 1.2, places=1)


class RuleNoneWithUserRuleTests(unittest.TestCase):
    """C-03: rule.style=none のとき、style / overrides の rule 指定は無視して落ちない。"""

    def _build(self, deck):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck)
            (d / "shapes").mkdir()
            (d / "shapes" / "nr.json").write_text(json.dumps({"tokens": {"rule": {"style": "none"}}}), encoding="utf-8")
            r = build(d)
            html = next((d / "build").glob("*.html")).read_text(encoding="utf-8") if r.returncode == 0 else ""
            return r, html

    def test_style_rule_fill_does_not_crash(self):
        for style in ({"rule": {"fill": "accent"}}, {"rule": {"h": 8}}):
            with self.subTest(style=style):
                r, html = self._build(deck_of([dict(BULLETS, style=style)], shape="nr"))
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn("KeyError", r.stderr)
                self.assertIn("rule.style が none", r.stderr)
                self.assertNotIn("width:1136px;height:8px", html)

    def test_layout_overrides_rule_does_not_crash(self):
        r, _ = self._build(deck_of([BULLETS], shape="nr", layout_overrides={"bullets": {"rule": {"fill": "accent"}}}))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_fragment_rule_is_not_drawn(self):
        self.assertEqual(b.rule_html({"rule": {"fill": "accent"}}, {"colors": {"accent": "#007D96"}}), "")


class LayoutDiffValidationTests(unittest.TestCase):
    """C-04 / A-04: shape・テーマの layout 差分も、レイアウト JSON と同じに値の型・領域名・色を検査する。"""

    BASE = None

    @classmethod
    def setUpClass(cls):
        cls.base = b.load_layout("default")

    def issues(self, layout, **kw):
        return shp.validate_shape({"layout": layout}, "zz", self.base["_unresolved"]["tokens"], self.base,
                                  kw.get("colors", {"accent": "#007D96", "text": "#111111"}))

    def test_wrong_type_is_a_fail_naming_the_shape(self):
        out = self.issues({"types": {"bullets": {"title": {"size": "big"}}}})
        msgs = [m for lv, m in out if lv == "fail"]
        self.assertTrue(msgs and "shape 'zz'" in msgs[0] and "layout.types.bullets.title.size" in msgs[0], out)

    def test_negative_and_tiny_size_fail(self):
        for v in (-5, 1):
            out = self.issues({"types": {"bullets": {"title": {"size": v}}}})
            self.assertTrue(any(lv == "fail" for lv, _ in out), (v, out))

    def test_unknown_region_type_and_property_warn_with_candidate(self):
        out = self.issues({"types": {"bullets": {"titel": {"size": 30}}}})
        self.assertTrue(any(lv == "warn" and "titel" in m and "title" in m for lv, m in out), out)
        out = self.issues({"types": {"bulets": {"title": {"size": 30}}}})
        self.assertTrue(any(lv == "warn" and "bullets" in m for lv, m in out), out)
        out = self.issues({"types": {"bullets": {"title": {"sizee": 30}}}})
        self.assertTrue(any(lv == "warn" and "size" in m for lv, m in out), out)
        out = self.issues({"common": {"brandd": {"size": 20}}})
        self.assertTrue(any(lv == "warn" and "brand" in m for lv, m in out), out)

    def test_token_refs_are_resolved_before_checking(self):
        self.assertEqual(self.issues({"types": {"bullets": {"title": {"size": "$type.h2", "radius": "$radius.card"}}}}), [])
        out = self.issues({"types": {"bullets": {"title": {"size": "$type.nope"}}}})
        self.assertTrue(any(lv == "fail" and "$type" in m for lv, m in out), out)

    def test_bad_color_is_flagged(self):
        out = self.issues({"types": {"title": {"bar": {"fill": "nocolor"}}}})
        self.assertTrue(any(lv == "fail" and "nocolor" in m for lv, m in out), out)
        out = shp.validate_shape({"layout": {"types": {"title": {"bar": {"fill": "nocolor"}}}}}, "zz",
                                 self.base["_unresolved"]["tokens"], self.base, {"accent": "#007D96"}, "warn")
        self.assertTrue(any(lv == "warn" and "nocolor" in m for lv, m in out), out)
        self.assertEqual(self.issues({"types": {"title": {"bar": {"fill": "accent"}}}}), [])
        self.assertEqual(self.issues({"types": {"title": {"bar": {"fill": "#112233"}}}}), [])

    def test_densities_must_be_an_object(self):
        out = self.issues({"densities": ["talk"]})
        self.assertTrue(any(lv == "fail" and "densities" in m for lv, m in out), out)

    def test_bundled_shapes_have_no_layout_diff_issues(self):
        colors = b.load_theme("default", b.theme_dirs(None))["colors"]
        for n in BUNDLED:
            data = shp.load_shape(n)
            self.assertEqual(shp.validate_shape(data, n, self.base["_unresolved"]["tokens"], self.base, colors), [], n)

    def test_build_stops_with_shape_name_on_wrong_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], shape="zz"))
            (d / "shapes").mkdir()
            (d / "shapes" / "zz.json").write_text(json.dumps({"layout": {"types": {"bullets": {"title": {"size": "big"}}}}}), encoding="utf-8")
            r = build(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("shape 'zz'", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertNotIn("検証中にエラー", r.stderr)

    def test_build_flags_bad_theme_layout_with_theme_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([BULLETS], theme="zt"))
            (d / "themes").mkdir()
            (d / "themes" / "zt.json").write_text(json.dumps({"extends": "default", "layout": {"types": {"bullets": {"title": {"size": "x"}}}}}),
                                                  encoding="utf-8")
            r = build(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("テーマ 'zt'", r.stderr)
        self.assertNotIn("検証中にエラー", r.stderr)


class CheckThemeShapeTests(unittest.TestCase):
    """C-05 / A-03: check_theme.py がテーマの shape・tokens・layout を検証し、壊れた shape でも落ちない。"""

    def _run(self, *args, env=None):
        return subprocess.run([PY, str(TOOLS / "check_theme.py"), *args], capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ, **(env or {})))

    def test_shapes_with_string_tokens_is_reported_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "zz.json").write_text(json.dumps({"tokens": "x"}), encoding="utf-8")
            Path(tmp, "yy.json").write_text(json.dumps({"tokens": {"rule": "x"}}), encoding="utf-8")
            r = self._run("--shapes", env={"SLIDE_DECK_SHAPES": tmp})
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(r.returncode, 1)
        self.assertIn("zz", r.stdout)
        self.assertIn("tokens", r.stdout)

    def _theme(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "themes").mkdir()
        (d / "themes" / "mt.json").write_text(json.dumps(dict({"name": "mt", "extends": "default"}, **data)), encoding="utf-8")
        return d

    def test_theme_with_unknown_shape_fails(self):
        d = self._theme({"shape": "nope"})
        r = self._run("mt", "--deck", str(d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("nope", r.stdout)

    def test_theme_with_bad_tokens_and_layout_fails(self):
        d = self._theme({"tokens": {"rule": {"style": "wavy"}}})
        r = self._run("mt", "--deck", str(d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("rule.style", r.stdout)
        d = self._theme({"layout": {"types": {"bullets": {"title": {"size": "$radius.nope"}}}}})
        r = self._run("mt", "--deck", str(d))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("$radius.nope", r.stdout)

    def test_good_theme_with_shape_passes(self):
        d = self._theme({"shape": "sharp", "tokens": {"radius": {"card": 2}}, "layout": {"types": {"bullets": {"title": {"size": 30}}}}})
        r = self._run("mt", "--deck", str(d))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_shapes_command_flags_bad_layout_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "zz.json").write_text(json.dumps({"layout": {"types": {"bullets": {"title": {"size": "big"}}}}}), encoding="utf-8")
            r = self._run("--shapes", env={"SLIDE_DECK_SHAPES": tmp})
        self.assertEqual(r.returncode, 1)
        self.assertIn("layout.types.bullets.title.size", r.stdout)


class StyleValueRangeTests(unittest.TestCase):
    """C-06: style 側の weight / tracking / case / shadow も範囲・列挙を検査する。spc は ±400000 に収める。"""

    def test_style_values_are_validated(self):
        for region, prop, val in (("title", "weight", -100), ("title", "weight", 1000), ("title", "tracking", 200),
                                  ("eyebrow", "case", "lower"), ("grid", "shadow", "huge")):
            with self.subTest(prop=prop, val=val), tempfile.TemporaryDirectory() as tmp:
                slide = dict(CARDS, style={region: {prop: val}}) if region == "grid" else dict(BULLETS, style={region: {prop: val}})
                d = write_deck(tmp, deck_of([slide]))
                r = build(d, "--html")
                self.assertEqual(r.returncode, 1, (prop, val, r.stderr))
                self.assertIn(prop, r.stderr)
                self.assertNotIn("Traceback", r.stderr)

    def test_valid_style_values_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([dict(BULLETS, style={"title": {"weight": 600, "tracking": 0.05}, "eyebrow": {"case": "upper"}})]))
            r = build(d, "--html")
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_canvas_spc_is_clamped(self):
        import canvas_engine
        xml = canvas_engine._runs_xml({"runs": [{"text": "x", "size": 100, "tracking": 100}]})
        self.assertIn('spc="400000"', xml)
        xml = canvas_engine._runs_xml({"runs": [{"text": "x", "size": 100, "tracking": -100}]})
        self.assertIn('spc="-400000"', xml)


class DiagramRadiusParityTests(unittest.TestCase):
    """A-01 / C-07 / A-05: 図解のノード・タグ・辺ラベルの角丸が HTML と PPTX で同じ。"""

    DIAGRAM = {"type": "architecture", "title": "構成", "eyebrow": "SYS",
               "nodes": [{"id": "a", "type": "backend", "label": "API", "row": 0, "col": 0, "tag": "NEW"},
                         {"id": "b", "type": "database", "label": "DB", "row": 0, "col": 1}],
               "edges": [{"from": "a", "to": "b", "label": "SQL"}]}
    LIFECYCLE = {"type": "lifecycle", "title": "状態", "lanes": [{"name": "main"}],
                 "states": [{"id": "s1", "label": "受付", "kind": "start", "lane": 0, "col": 0},
                            {"id": "s2", "label": "処理", "lane": 0, "col": 1}],
                 "transitions": [{"from": "s1", "to": "s2", "label": "Y"}]}

    def _html(self, shape):
        with tempfile.TemporaryDirectory() as tmp:
            return html_of(tmp, deck_of([self.DIAGRAM, self.LIFECYCLE], shape=shape))

    def test_classic_keeps_pill_and_rx4(self):
        html = self._html("classic")
        self.assertRegex(html, r'rx="4"')
        self.assertRegex(html, r"border-radius:\d+px;background:[^;]*;color:[^;]*;font-size:10px")      # タグピル

    def test_editorial_pill_radius_is_capped_by_token_in_html(self):
        import re
        html = self._html("editorial")                       # radius.pill = 4, small = 3
        self.assertRegex(html, r'rx="3"')                     # 辺ラベル: min(4, radius.small)
        self.assertIn("border-radius:4px;background:", html)  # タグピル: min(ts*0.8, radius.pill)
        # start ノード（pill 形）の角丸は h/2 ではなく radius.pill
        start = re.findall(r'height:(\d+\.\d)px;box-sizing:border-box;background:[^;]*;border:[^;]*;border-radius:(\d+)px', html)
        self.assertTrue(start)
        self.assertIn("4", {r for _h, r in start})

    def test_sharp_has_square_start_node_and_edge_label_in_html(self):
        html = self._html("sharp")                           # pill = 0, small = 0
        self.assertRegex(html, r'rx="0"')
        self.assertNotRegex(html, r"border-radius:[1-9]\d*px;background:[^;]*;color:[^;]*;font-size:10px")

    def test_pptx_tag_pill_adjustment_matches_html_radius(self):
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([self.DIAGRAM], shape="editorial"))
            self.assertEqual(build(d).returncode, 0)
            prs = Presentation(str(next((d / "build").glob("*.pptx"))))
            found = False

            def walk(shapes):
                for sh in shapes:
                    if sh.shape_type == 6:
                        yield from walk(sh.shapes)
                    else:
                        yield sh
            for sh in walk(prs.slides[0].shapes):
                if sh.has_text_frame and sh.text_frame.text == "NEW" and len(sh.adjustments):
                    h = sh.height / 9525
                    self.assertAlmostEqual(sh.adjustments[0] * min(sh.width, sh.height) / 9525, 4, delta=0.2)
                    self.assertAlmostEqual(h, 16, delta=0.5)
                    found = True
            self.assertTrue(found)


class EditorialTitleFloorTests(unittest.TestCase):
    """A-02: editorial は見出しが大きい（40px）が、タイトルは classic と同じ 28px まで縮められる。"""

    def test_editorial_title_floor_equals_classic(self):
        import autofit
        deck, _theme, layout = load(deck_of([BULLETS], shape="editorial"))
        for t, tv in layout["types"].items():
            if isinstance(tv.get("title"), dict) and tv["title"].get("size") == 40:
                self.assertEqual(tv["title"].get("min_size"), 28, t)

    def test_38_char_title_fits_in_editorial(self):
        title = "あいうえお" * 7 + "かきく"            # 38 字
        with tempfile.TemporaryDirectory() as tmp:
            d = write_deck(tmp, deck_of([dict(BULLETS, title=title)], shape="editorial"))
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("はみ出し", r.stderr)


class TokenGroupMessageTests(unittest.TestCase):
    """C-08: 使えるグループの一覧に _comment を出さない。"""

    def test_unknown_group_message_has_no_comment_key(self):
        base = b.load_layout("default")["_unresolved"]["tokens"]
        out = shp.check_tokens({"zzz": {"a": 1}}, base, "w")
        self.assertTrue(out and "_comment" not in out[0][1], out)
        ok, msg = shp.lookup(base, "$zzz.a")
        self.assertFalse(ok)
        self.assertNotIn("_comment", msg)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2d 主役のあるページのテスト: 背景（画像＋覆い／色面）と文字色の自動選択・variant・section の自動番号・split・cards の強弱（emphasis / span）・
cards の泣き別れ・画像の bleed・canvas の改行・soft の影（kpi / summary）。

実行: python3 -m unittest plugins/slide-deck/tools/test_hero.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import hero_engine as hero  # noqa: E402
import canvas_engine as ce  # noqa: E402
from test_validation import one, validate, write_deck  # noqa: E402

PY = sys.executable
COLORS = {"background": "#FFFFFF", "surface": "#E0E7F0", "text": "#1A2233", "muted": "#566781", "primary": "#0F3D6E",
          "accent": "#007D96", "on_primary": "#FFFFFF", "on_primary_soft": "#EAF1F8", "on_primary_muted": "#C7D6E8",
          "heading_text": "#0F3D6E", "accent_on_primary": "#7FDDF0", "highlight_fill": "#BFDDE7"}


def make_images(d: Path):
    from PIL import Image, ImageDraw
    a = d / "assets"
    a.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1600, 900), (20, 40, 90)).save(a / "dark.png")                 # 暗い一色
    Image.new("RGB", (1600, 900), (250, 245, 230)).save(a / "bright.png")             # 明るい一色
    im = Image.new("RGB", (1600, 900), (30, 60, 110))                                  # 暗い地に白い部分（最悪ケース）
    ImageDraw.Draw(im).rectangle([800, 0, 1600, 900], fill=(255, 255, 255))
    im.save(a / "split.png")


def build(deck_dir, *extra):
    return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir), *extra], capture_output=True, text=True, encoding="utf-8")


def deck_with(slides, **meta):
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    return {"meta": m, "slides": slides}


def html_of(d):
    return (Path(d) / "build" / "d.html").read_text(encoding="utf-8")


def pptx_slides(d):
    z = zipfile.ZipFile(Path(d) / "build" / "d.pptx")
    return [z.read(n).decode("utf-8") for n in sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                                                       key=lambda s: int(re.findall(r"\d+", s)[0]))]


class ColorMathTests(unittest.TestCase):
    def test_contrast_black_white(self):
        self.assertAlmostEqual(hero.contrast((0, 0, 0), (255, 255, 255)), 21.0, places=1)

    def test_parse_position(self):
        self.assertEqual(hero.parse_position("center"), (0.5, 0.5))
        self.assertEqual(hero.parse_position("top left"), (0.0, 0.0))
        self.assertEqual(hero.parse_position("left top"), (0.0, 0.0))
        self.assertEqual(hero.parse_position("30% 70%"), (0.3, 0.7))
        self.assertIsNone(hero.parse_position("middle-ish"))
        self.assertIsNone(hero.parse_position("120% 10%"))
        self.assertIsNone(hero.parse_position(5))


class BackgroundValidateTests(unittest.TestCase):
    def run_v(self, bg, deck_dir=None):
        msgs = []

        def fail(m):
            raise ValueError(m)
        try:
            out = hero.validate_background(bg, "1枚目: background", COLORS, deck_dir, fail, msgs.append)
        except ValueError as e:
            return None, [str(e)]
        return out, msgs

    def test_string_shorthand(self):
        out, _ = self.run_v("assets/x.jpg")
        self.assertEqual(out, {"image": "assets/x.jpg"})

    def test_needs_image_or_fill(self):
        out, msgs = self.run_v({"overlay": "primary"})
        self.assertIsNone(out)
        self.assertIn("image も fill もありません", msgs[0])

    def test_bad_opacity_and_overlay_and_position(self):
        for bad, key in (({"image": "a.png", "opacity": 1.5}, "opacity"), ({"image": "a.png", "opacity": "x"}, "opacity"),
                         ({"image": "a.png", "overlay": "nope"}, "overlay"), ({"image": "a.png", "position": "xx"}, "position")):
            out, msgs = self.run_v(bad)
            self.assertIsNone(out)
            self.assertIn(key, msgs[0])

    def test_unknown_key_warns_with_hint(self):
        out, msgs = self.run_v({"image": "a.png", "opacty": 0.5})
        self.assertTrue(any("opacty" in m and "opacity" in m for m in msgs))

    def test_fill_with_overlay_warns(self):
        out, msgs = self.run_v({"fill": "primary", "overlay": "accent"})
        self.assertEqual(out, {"fill": "primary"})
        self.assertTrue(any("overlay は画像の背景だけ" in m for m in msgs))

    def test_unknown_fill_color_fails(self):
        out, msgs = self.run_v({"fill": "nonexistent"})
        self.assertIsNone(out)
        self.assertIn("テーマの色トークン", msgs[0])


class SolveBackgroundTests(unittest.TestCase):
    PAL = {"light": {"title": {"color": "on_primary"}, "subtitle": {"color": "on_primary_soft"}, "meta": {"color": "on_primary_muted"}},
           "dark": {"title": {"color": "heading_text"}, "subtitle": {"color": "text"}, "meta": {"color": "muted"}}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        make_images(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def solve(self, bg, pal=None, only=None):
        return hero.solve_background(bg, COLORS, (0, 0, 1280, 720), self.d, self.PAL if pal is None else pal, only)

    def test_dark_image_dark_overlay_uses_light_text_at_start_opacity(self):
        r = self.solve({"image": "assets/dark.png"})
        self.assertEqual(r["mode"], "light")
        self.assertEqual(r["opacity"], hero.OVERLAY_START)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["ratio"], 4.5)
        self.assertTrue(r["auto"])

    def test_bright_image_raises_opacity_until_contrast_holds(self):
        r = self.solve({"image": "assets/bright.png"})
        self.assertTrue(r["ok"])
        self.assertGreater(r["opacity"], hero.OVERLAY_START)
        self.assertGreaterEqual(r["ratio"], 4.5)
        # 実際に下地と混ぜて確かめる
        under = hero.hex_to_rgb(r["qa_bg"])
        eff = hero.mix(under, hero.hex_to_rgb(r["overlay"]), r["opacity"])
        self.assertGreaterEqual(min(hero.contrast(hero.hex_to_rgb(c), eff) for c in r["texts"]), 4.49)

    def test_half_white_image_is_judged_by_its_worst_region(self):
        r = self.solve({"image": "assets/split.png"})
        self.assertTrue(r["ok"])
        self.assertGreater(r["opacity"], hero.OVERLAY_START)        # 白い半分があるので、暗い画像より濃い覆いが要る

    def test_light_overlay_picks_dark_text(self):
        r = self.solve({"image": "assets/bright.png", "overlay": "background"})
        self.assertEqual(r["mode"], "dark")
        self.assertTrue(r["ok"])

    def test_user_opacity_too_low_reports_and_suggests(self):
        r = self.solve({"image": "assets/bright.png", "opacity": 0.2})
        self.assertFalse(r["ok"])
        self.assertEqual(r["opacity"], 0.2)
        self.assertIsNotNone(r["suggest"])
        msgs = hero.background_problems(r, {"image": "x", "opacity": 0.2}, "1枚目")
        self.assertIn(f"opacity を {r['suggest']:g} 以上", msgs[0][1])
        # 提案した濃さなら届く
        again = self.solve({"image": "assets/bright.png", "opacity": r["suggest"]})
        self.assertTrue(again["ok"])

    def test_fill_only_chooses_mode_by_contrast(self):
        self.assertEqual(self.solve({"fill": "primary"})["mode"], "light")
        self.assertEqual(self.solve({"fill": "surface"})["mode"], "dark")
        self.assertTrue(self.solve({"fill": "primary"})["ok"])

    def test_fill_with_no_good_text_color_is_flagged(self):
        r = self.solve({"fill": "#7F7F7F"})          # 中間のグレーは明暗どちらの文字でも 4.5 に届かない
        self.assertFalse(r["ok"])
        self.assertIn("4.5:1 に届きません", hero.background_problems(r, {"fill": "#7F7F7F"}, "1枚目")[0][1])

    def test_no_text_means_no_overlay_unless_asked(self):
        self.assertIsNone(self.solve({"image": "assets/dark.png"}, pal={})["overlay"])
        self.assertEqual(self.solve({"image": "assets/dark.png", "overlay": "primary"}, pal={})["overlay"], "#0F3D6E")

    def test_overlay_none_means_no_overlay_element(self):
        r = self.solve({"image": "assets/dark.png", "overlay": "none"})
        els = hero.background_elements(r)
        self.assertEqual([e["kind"] for e in els], ["image"])

    def test_elements_image_then_alpha_overlay(self):
        r = self.solve({"image": "assets/dark.png", "position": "top"})
        els = hero.background_elements(r, (0, 0, 1280, 720))
        self.assertEqual([e["kind"] for e in els], ["image", "shape"])
        self.assertEqual(els[0]["position"], "top")
        self.assertEqual(els[0]["fit"], "cover")
        self.assertEqual(els[1]["fill"]["alpha"], r["opacity"])
        self.assertEqual(els[0]["qa_bg"], r["qa_bg"])


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.layout = b.load_layout("default", None)

    def test_variants_exist_per_type(self):
        v = self.layout["variants"]
        self.assertEqual(set(v["title"]), {"center", "left-band", "split", "bottom"})
        self.assertEqual(set(v["section"]), {"number", "band", "side"})
        self.assertEqual(set(v["closing"]), {"center", "contact"})
        self.assertEqual(set(v["statement"]), {"center", "left-bar", "mark"})
        self.assertEqual(set(v["quote"]), {"left-bar", "mark"})

    def test_variant_of_priority_and_default(self):
        s = {"type": "title", "variant": "center"}
        self.assertEqual(hero.variant_of(self.layout, {}, s), "center")
        self.assertEqual(hero.variant_of(self.layout, {"meta": {"variants": {"title": "split"}}}, {"type": "title"}), "split")
        self.assertIsNone(hero.variant_of(self.layout, {"meta": {"variants": {"title": "split"}}}, {"type": "title", "variant": "default"}))
        self.assertEqual(hero.variant_of({**self.layout, "variant_defaults": {"title": "left-band"}}, {}, {"type": "title"}), "left-band")
        self.assertIsNone(hero.variant_of(self.layout, {}, {"type": "bullets", "variant": "center"}))

    def test_auto_variants(self):
        self.assertEqual(hero.variant_of(self.layout, {}, {"type": "image", "fit": "bleed"}), "bleed")
        self.assertEqual(hero.variant_of(self.layout, {}, {"type": "image", "fit": "bleed", "caption_position": "band", "caption": "図"}), "bleed-band")
        self.assertEqual(hero.variant_of(self.layout, {}, {"type": "image", "caption_position": "band", "caption": "図"}), "band")
        # caption が無いのに band にすると空の色帯が残る（s2d-C-03）: 帯の variant は選ばない
        self.assertEqual(hero.variant_of(self.layout, {}, {"type": "image", "fit": "bleed", "caption_position": "band"}), "bleed")
        self.assertIsNone(hero.variant_of(self.layout, {}, {"type": "image", "caption_position": "band", "caption": "  "}))
        self.assertEqual(hero.variant_of(self.layout, {}, {"type": "image_text", "bleed": True}), "bleed")
        self.assertIsNone(hero.variant_of(self.layout, {}, {"type": "image"}))

    def test_unknown_variant_fails_with_candidates(self):
        exc, err = validate(one({"type": "title", "title": "T", "variant": "centre"}))
        self.assertIsNotNone(exc)
        self.assertIn("variant 'centre' はありません", str(exc))
        self.assertIn("center", str(exc))

    def test_variant_on_unsupported_type_warns_unknown_key(self):
        exc, err = validate(one({"type": "bullets", "title": "T", "bullets": ["a"], "variant": "center"}))
        self.assertIsNone(exc)
        self.assertIn("variant", err)

    def test_style_layer_only_when_variant_given(self):
        base = b.resolve_style(self.layout, {"meta": {}}, {"type": "title", "title": "T"})
        v = b.resolve_style(self.layout, {"meta": {}}, {"type": "title", "title": "T", "variant": "center"})
        self.assertEqual(base["title"]["x"], 72)
        self.assertEqual(v["title"]["align"], "center")
        self.assertNotIn("panel", base)

    def test_user_style_beats_variant(self):
        st = b.resolve_style(self.layout, {"meta": {}}, {"type": "title", "title": "T", "variant": "left-band", "style": {"title": {"x": 500}}})
        self.assertEqual(st["title"]["x"], 500)

    def test_style_may_tune_variant_region(self):
        exc, err = validate(one({"type": "title", "title": "T", "variant": "left-band", "style": {"panel": {"w": 300}}}))
        self.assertIsNone(exc)
        self.assertNotIn("領域名ではありません", err)

    def test_shape_can_set_default_variant(self):
        # shape の layout 差分に variant_defaults を書けて、検証も通る（未知の variant は warn）
        import shape_engine as shp
        ok = shp.check_layout_diff({"variant_defaults": {"title": "center"}}, "shape 'x'", None, self.layout)
        self.assertEqual(ok, [])
        bad = shp.check_layout_diff({"variant_defaults": {"title": "centre"}}, "shape 'x'", None, self.layout)
        self.assertTrue(any("centre" in m for _lv, m in bad))
        merged = shp.apply_to_layout(self.layout, {"name": "x", "layout": {"variant_defaults": {"title": "center"}}})
        self.assertEqual(merged["variant_defaults"]["title"], "center")


class MetaHeroTests(unittest.TestCase):
    def test_section_numbers_must_be_bool(self):
        exc, err = validate({"meta": {"id": "d", "title": "T", "theme": "default", "section_numbers": "yes"}, "slides": [{"type": "section", "title": "S"}]})
        self.assertIn("meta.section_numbers は true / false", str(exc))

    def test_meta_variants_unknown_name_fails_and_unknown_type_warns(self):
        exc, err = validate(one({"type": "title", "title": "T"}, variants={"title": "centre"}))
        self.assertIn("meta.variants.title の 'centre'", str(exc))
        self.assertIn("center", str(exc))
        exc, err = validate(one({"type": "title", "title": "T"}, variants={"bullets": "x"}))
        self.assertIsNone(exc)
        self.assertIn("variant を持つタイプではありません", err)

    def test_meta_variants_applies_to_all_slides_of_the_type(self):
        deck = one({"type": "title", "title": "T"}, variants={"title": "center"})
        exc, err = validate(deck)
        self.assertIsNone(exc, err)
        lay = b.load_layout("default", None)
        self.assertEqual(b.resolve_style(lay, deck, deck["slides"][0])["title"]["align"], "center")


class HeroBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_images(self.root / "d")

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, slides, **meta):
        d = write_deck(self.root, deck_with(slides, **meta), "d")
        make_images(d)
        return d

    def ok(self, d, *extra):
        r = build(d, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_no_background_no_variant_is_unchanged(self):
        d = self.mk([{"type": "title", "title": "T", "subtitle": "s"}, {"type": "section", "title": "S"},
                     {"type": "closing", "title": "C", "bullets": ["a"]}, {"type": "quote", "text": "q"},
                     {"type": "statement", "message": "m"}])
        self.ok(d)
        h = html_of(d)
        self.assertNotIn("<img", h)
        self.assertNotIn("data-qa-bg", h)

    # S2d より前（frozen-s2c）のビルドと同じ構造を保っている印: 何も指定しない 9 枚の HTML の div / img の数、PPTX の図形 / 画像の数と使われる色。
    # 値は S2d の前のツールで実測したもの（2026-11-11。フォントに依存しない数と色だけを比べる）
    UNCHANGED_SIGNATURE = [
        (4, 0, 5, 0, ["007D96", "0F3D6E", "566781", "FFFFFF"]),
        (3, 0, 4, 0, ["007D96", "0F3D6E", "7FDDF0", "FFFFFF"]),
        (4, 0, 5, 0, ["007D96", "0F3D6E", "7FDDF0", "EAF1F8", "FFFFFF"]),
        (3, 0, 4, 0, ["007D96", "0F3D6E", "566781", "FFFFFF"]),
        (8, 0, 5, 0, ["0F3D6E", "7FDDF0", "C7D6E8", "FFFFFF"]),
        (14, 0, 15, 0, ["007D96", "0F3D6E", "1A2233", "566781", "BCC8D8", "E0E7F0", "FFFFFF"]),
        (6, 1, 6, 1, ["007D96", "0F3D6E", "566781", "FFFFFF"]),
        (6, 1, 6, 1, ["007D96", "0F3D6E", "1A2233", "566781", "FFFFFF"]),
        (5, 0, 6, 0, ["007D96", "0F3D6E", "1A2233", "566781", "FFFFFF"]),
    ]

    def test_default_deck_structure_matches_pre_s2d_build(self):
        slides = [{"type": "title", "title": "表紙", "subtitle": "副題", "meta": "2026-11-11"},
                  {"type": "section", "title": "章扉", "number": "01"},
                  {"type": "closing", "title": "終わり", "bullets": ["a", "b"], "message": "m"},
                  {"type": "quote", "text": "引用の文", "attribution": "某"},
                  {"type": "statement", "message": "言い切りの一文", "kicker": "k"},
                  {"type": "cards", "title": "打ち手", "cards": [{"heading": "A", "body": "本文 A"},
                                                                {"heading": "B", "body": "本文 B", "items": ["x", "y"]},
                                                                {"heading": "C", "body": "本文 C"}]},
                  {"type": "image", "title": "図", "path": "assets/dark.png", "caption": "図 1"},
                  {"type": "image_text", "title": "画像と文", "path": "assets/dark.png", "bullets": ["a", "b"]},
                  {"type": "bullets", "title": "箇条書き", "bullets": ["一", "二", "三"]}]
        d = self.mk(slides)
        self.ok(d)
        secs = re.findall(r'<section class="slide".*?</section>', html_of(d), re.S)
        xs = pptx_slides(d)
        self.assertEqual(len(secs), len(self.UNCHANGED_SIGNATURE))
        got = [(sec.count("<div"), sec.count("<img"), x.count("<p:sp>"), x.count("<p:pic>"),
                sorted(set(re.findall(r'srgbClr val="([0-9A-F]{6})"', x)))) for sec, x in zip(secs, xs)]
        for i, (g, want) in enumerate(zip(got, self.UNCHANGED_SIGNATURE), 1):
            self.assertEqual(g, want, f"{i} 枚目（{slides[i - 1]['type']}）の構造が S2d より前のビルドと違います")

    def test_title_background_image_html_and_pptx(self):
        d = self.mk([{"type": "title", "title": "T", "subtitle": "s", "background": {"image": "assets/dark.png"}}])
        r = self.ok(d)
        h = html_of(d)
        self.assertIn("<img", h)
        self.assertIn('data-qa-bg="#', h)
        self.assertIn("object-fit:cover", h)
        # 文字色は覆いの上の対比で明るい色（on_primary）になる
        self.assertIn("color:#FFFFFF", h)
        x = pptx_slides(d)[0]
        self.assertIn("<p:pic>", x)
        self.assertRegex(x, r'<a:alpha val="\d+"/>')          # 半透明の覆い

    def test_background_shorthand_string(self):
        d = self.mk([{"type": "section", "title": "S", "background": "assets/dark.png"}])
        self.ok(d)
        self.assertIn("<img", html_of(d))

    def test_bright_image_auto_overlay_makes_contrast_pass_check(self):
        d = self.mk([{"type": "title", "title": "明るい画像の上のタイトル", "subtitle": "サブ", "meta": "2026-11-11",
                      "background": "assets/bright.png"}])
        r = self.ok(d)
        self.assertNotIn("対比", r.stderr)
        m = re.search(r'fill-opacity="([0-9.]+)"|rgba\(15,\s*61,\s*110,\s*([0-9.]+)\)', html_of(d))
        self.assertIsNotNone(m)
        self.assertGreater(float(m.group(1) or m.group(2)), 0.55)

    def test_low_opacity_warns_with_fix(self):
        d = self.mk([{"type": "title", "title": "T", "background": {"image": "assets/split.png", "opacity": 0.1}}])
        r = self.ok(d)
        self.assertIn("4.5:1 に届きません", r.stderr)
        self.assertRegex(r.stderr, r"opacity を 0\.\d+ 以上にする")

    def test_missing_image_fails_with_location(self):
        d = self.mk([{"type": "title", "title": "T", "background": {"image": "assets/none.png"}}])
        r = build(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("1枚目（type=title）: background", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_fill_background_changes_text_color_automatically(self):
        d = self.mk([{"type": "quote", "text": "引用", "attribution": "出典", "background": {"fill": "primary"}}])
        self.ok(d)
        h = html_of(d)
        self.assertIn('fill="#0F3D6E"', h)             # 全面の色面（canvas の図形）
        self.assertIn("color:#FFFFFF", h)              # 文字は反転
        x = pptx_slides(d)[0]
        self.assertIn('val="0F3D6E"', x)

    def test_statement_background_image_uses_canvas_image(self):
        d = self.mk([{"type": "statement", "message": "言い切り", "background": "assets/dark.png", "variant": "left-bar"}])
        self.ok(d)
        self.assertIn("<img", html_of(d))
        self.assertIn("<p:pic>", pptx_slides(d)[0])

    def test_variants_build_for_all_types_and_both_outputs(self):
        slides = []
        for t, extra in (("title", {"subtitle": "s", "meta": "m"}), ("section", {"subtitle": "s"}),
                         ("closing", {"bullets": ["a", "b"], "message": "m"}), ("statement", {"message": "m", "kicker": "k"}),
                         ("quote", {"text": "q", "attribution": "a"})):
            for v in hero.variant_names(b.load_layout("default", None), t):
                slides.append(dict({"type": t, "title": "タイトル", "variant": v}, **extra))
        d = self.mk(slides)
        self.ok(d)
        self.assertEqual(len(pptx_slides(d)), len(slides))
        self.assertIn('data-type="section"', html_of(d))

    def test_variant_panel_takes_background_image(self):
        d = self.mk([{"type": "title", "title": "T", "variant": "split", "background": "assets/split.png"}])
        self.ok(d)
        h = html_of(d)
        self.assertEqual(h.count("<img"), 1)
        self.assertNotIn("rgba(15, 61, 110", h.replace("rgba(15,61,110", "rgba(15, 61, 110"))      # 文字は panel の外なので覆いは付かない

    def test_section_auto_numbers(self):
        d = self.mk([{"type": "section", "title": "A"}, {"type": "bullets", "title": "b", "bullets": ["x"]},
                     {"type": "section", "title": "B"}, {"type": "section", "title": "C", "number": "X"}], section_numbers=True)
        self.ok(d)
        h = html_of(d)
        self.assertIn(">01<", h)
        self.assertIn(">02<", h)
        self.assertIn(">X<", h)
        self.assertNotIn(">03<", h)

    def test_section_without_option_has_no_number(self):
        d = self.mk([{"type": "section", "title": "A"}])
        self.ok(d)
        self.assertNotIn(">01<", html_of(d))

    def test_number_variant_numbers_itself(self):
        d = self.mk([{"type": "section", "title": "A", "variant": "number"}])
        self.ok(d)
        self.assertIn(">01<", html_of(d))


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, slides, **meta):
        d = write_deck(self.root, deck_with(slides, **meta), "d")
        make_images(d)
        return d

    def split(self, **kw):
        s = {"type": "split", "title": "内訳", "panel": {"fill": "primary", "title": "作成時間は 3 分の 1 に", "text": "実測"},
             "blocks": [{"type": "bullets", "bullets": ["a", "b"]}]}
        s.update(kw)
        return s

    def test_builds_html_and_pptx_left_and_right(self):
        d = self.mk([self.split(side="left"), self.split(side="right", ratio=0.5)])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = html_of(d)
        self.assertIn("パネルの文字", h)
        self.assertEqual(len(pptx_slides(d)), 2)
        self.assertIn("作成時間は", pptx_slides(d)[0])

    def test_panel_bleeds_to_edges(self):
        lay = b.load_layout("default", None)
        st = b.resolve_style(lay, {"meta": {}}, {"type": "split", "panel": {"fill": "primary", "title": "x"}, "blocks": [{"type": "text", "text": "a"}]})
        p = st["panel"]
        self.assertEqual((p["x"], p["y"], p["w"], p["h"]), (0, 0, 512, 720))
        st = b.resolve_style(lay, {"meta": {}}, {"type": "split", "side": "right", "ratio": 0.5, "panel": {"title": "x"},
                                                  "blocks": [{"type": "text", "text": "a"}]})
        p = st["panel"]
        self.assertEqual((p["x"], p["w"]), (640, 640))
        self.assertEqual(p["x"] + p["w"], 1280)

    def test_body_avoids_the_panel(self):
        lay = b.load_layout("default", None)
        for side in ("left", "right"):
            st = b.resolve_style(lay, {"meta": {}}, {"type": "split", "side": side, "title": "t", "panel": {"title": "x"},
                                                      "blocks": [{"type": "text", "text": "a"}]})
            p, body = st["panel"], st["body"]
            self.assertTrue(body["x"] >= p["x"] + p["w"] or body["x"] + body["w"] <= p["x"], (side, p, body))
            self.assertLessEqual(body["x"] + body["w"], 1280)
            self.assertGreaterEqual(body["x"], 0)
            for name in ("title", "footer_l", "footer_r"):
                r = st[name]
                self.assertTrue(r["x"] >= p["x"] + p["w"] or r["x"] + r["w"] <= p["x"], (side, name))

    def test_default_arranges_blocks_vertically(self):
        lay = b.load_layout("default", None)
        st = b.resolve_style(lay, {"meta": {}}, {"type": "split", "panel": {"title": "x"},
                                                  "blocks": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]})
        rects = [rb["rect"] for rb in st["_composite"]["blocks"]]
        self.assertEqual(rects[0][0], rects[1][0])
        self.assertLess(rects[0][1], rects[1][1])

    def test_no_title_lifts_body(self):
        lay = b.load_layout("default", None)
        a = b.resolve_style(lay, {"meta": {}}, {"type": "split", "title": "t", "panel": {"title": "x"}, "blocks": [{"type": "text", "text": "a"}]})
        c = b.resolve_style(lay, {"meta": {}}, {"type": "split", "panel": {"title": "x"}, "blocks": [{"type": "text", "text": "a"}]})
        self.assertLess(c["body"]["y"], a["body"]["y"])
        self.assertNotIn("title", c)

    def test_validation_errors(self):
        for kw, frag in (({"side": "up"}, "side は left / right"), ({"ratio": 0.9}, "ratio はパネルの幅の割合"), ({"ratio": "x"}, "ratio"),
                         ({"panel": "x"}, "panel はオブジェクト"), ({"panel": {"kpi": {"label": "x"}}}, "value"),
                         ({"panel": {"items": "x"}}, "panel.items は文字列の配列"), ({"panel": {"fill": "nope"}}, "テーマの色トークン"),
                         ({"panel": {"image": "assets/none.png"}}, "画像ファイルが見つかりません")):
            exc, err = validate(one(self.split(**kw)), self.root)
            self.assertIsNotNone(exc, kw)
            self.assertIn(frag, str(exc), kw)
            self.assertIn("1枚目（type=split）", str(exc), kw)

    def test_panel_required(self):
        s = self.split()
        del s["panel"]
        exc, err = validate(one(s))
        self.assertIn("panel（端まで届く色面か画像のパネル）が必要", str(exc))

    def test_blocks_required_and_block_errors_name_split(self):
        s = self.split(blocks=[])
        exc, err = validate(one(s))
        self.assertIn("1枚目（type=split）", str(exc))
        s = self.split(blocks=[{"type": "title"}])
        exc, err = validate(one(s))
        self.assertIn("1枚目（type=split）: 1 つ目のブロック", str(exc))

    def test_single_block_is_fine_but_composite_warns(self):
        exc, err = validate(one(self.split()))
        self.assertIsNone(exc)
        self.assertNotIn("1 個だけ", err)
        exc, err = validate(one({"type": "composite", "title": "c", "blocks": [{"type": "text", "text": "a"}]}))
        self.assertIn("1 個だけ", err)

    def test_too_many_items_and_kpi_with_title_warn(self):
        exc, err = validate(one(self.split(panel={"fill": "primary", "items": ["a", "b", "c", "d"]})))
        self.assertIn("3個までが目安", err)
        exc, err = validate(one(self.split(panel={"fill": "primary", "kpi": "72%", "title": "x"})))
        self.assertIn("主役は 1 つ", err)

    def test_unknown_panel_key_warns(self):
        exc, err = validate(one(self.split(panel={"fill": "primary", "titel": "x", "title": "y"})))
        self.assertIn("titel", err)

    def test_panel_overflow_warns_when_text_cannot_fit(self):
        long_title = "あ" * 400
        d = write_deck(self.root, deck_with([self.split(panel={"fill": "primary", "title": long_title})]), "o")
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("パネルの文字が最小の文字サイズでも収まりません", r.stderr)

    def test_panel_plan_shrinks_long_title(self):
        import proposal_engine as pe
        lay = b.load_layout("default", None)
        short = {"type": "split", "panel": {"title": "短い"}, "blocks": [{"type": "text", "text": "a"}]}
        long = {"type": "split", "panel": {"title": "とても長い主役の一文がここに入りますが、パネルの幅に収める必要があります" * 4}, "blocks": [{"type": "text", "text": "a"}]}
        th = {"colors": COLORS, "fonts": {"body": "Meiryo", "heading": "Meiryo"}}
        ctx = pe.Ctx(th)
        a = hero.panel_plan(short, b.resolve_style(lay, {"meta": {}}, short), ctx)
        c = hero.panel_plan(long, b.resolve_style(lay, {"meta": {}}, long), ctx)
        self.assertGreater(a["sizes"]["title"], c["sizes"]["title"])
        self.assertTrue(a["fit"])

    def test_panel_image_with_kpi_checks_contrast(self):
        d = self.mk([self.split(panel={"image": "assets/split.png", "kpi": {"value": "72%", "label": "削減"}}, side="right")])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<img", html_of(d))
        self.assertNotIn("対比", r.stderr)

    def test_diagram_in_split_is_diagnosed_by_check_diagram(self):
        arch = {"type": "architecture", "nodes": [{"id": "a", "type": "external", "label": "利用者", "row": 0, "col": 0},
                                                  {"id": "b", "type": "backend", "label": "API", "row": 0, "col": 1}],
                "edges": [{"from": "a", "to": "b"}]}
        d = self.mk([self.split(blocks=[arch])])
        r = subprocess.run([PY, str(TOOLS / "check_diagram.py"), str(d), "--no-build"], capture_output=True, text=True, encoding="utf-8")
        self.assertNotIn("Traceback", r.stderr)

    def test_lint_counts_split_blocks_and_ignores_background_keys(self):
        import lint_deck_text as lint
        s = {"type": "title", "title": "T", "background": {"image": "assets/x.png", "overlay": "primary"}, "variant": "center"}
        texts = [t for _p, t in lint.iter_texts(s)]
        self.assertEqual(texts, ["T"])
        sp = self.split(blocks=[{"type": "bullets", "bullets": ["あ" * 60]}])
        self.assertTrue(lint.composite_blocks(sp))


class CardsHeroTests(unittest.TestCase):
    G = {"x": 72, "y": 196, "w": 1136, "h": 440, "cols": 3, "gap": 16}

    def test_plan_without_spans_matches_cards_cells(self):
        import proposal_engine as pe
        a = pe.cards_cells(5, None, self.G)
        c = hero.cards_plan(5, None, self.G, [1] * 5)
        self.assertEqual(a["cells"], c["cells"])

    def test_span_widths_and_rows(self):
        p = hero.cards_plan(4, 3, self.G, [2, 1, 1, 2])
        cw = p["cw"]
        self.assertAlmostEqual(p["cells"][0][2], 2 * cw + 16)
        self.assertEqual(p["rows_of"], [[0, 1], [2, 3]])
        self.assertEqual(p["gaps"], [])
        self.assertAlmostEqual(p["cells"][0][0] + p["cells"][0][2] + 16, p["cells"][1][0])
        self.assertAlmostEqual(p["cells"][3][0] + p["cells"][3][2], self.G["x"] + self.G["w"])

    def test_gap_is_reported(self):
        p = hero.cards_plan(2, 3, self.G, [2, 2])
        self.assertEqual(p["rows_of"], [[0], [1]])
        self.assertEqual(len(p["gaps"]), 2)

    def test_span_is_clamped(self):
        p = hero.cards_plan(1, 3, self.G, [9])
        self.assertAlmostEqual(p["cells"][0][2], self.G["w"])

    def test_card_style_colors(self):
        g = b.load_layout("default", None)["types"]["cards"]["grid"]
        base = hero.card_style(g, None)
        self.assertEqual(base["fill"], "surface")
        strong = hero.card_style(g, True)
        self.assertEqual((strong["fill"], strong["heading_color"], strong["body_color"]), ("primary", "on_primary", "on_primary_soft"))
        self.assertEqual(hero.card_style(g, "accent")["fill"], "accent")
        self.assertEqual(hero.card_style(g, "soft")["fill"], "highlight_fill")

    def test_emphasis_text_contrast_meets_4_5_in_all_bundled_themes(self):
        # 同梱の全テーマ（accenture 系の on_primary_soft など、テーマごとに色の対比が違う）で、強調カードの文字は 4.5:1、記号・アイコンは 3:1 以上
        themes = sorted(p.stem for p in (TOOLS.parent / "templates" / "themes").glob("*.json"))
        self.assertGreaterEqual(len(themes), 5)
        for theme in themes:
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "deck.json").write_text(json.dumps({"meta": {"id": "d", "theme": theme}, "slides": []}), encoding="utf-8")
                _deck, th, lay = b.load_deck(Path(td))
            g, colors = lay["types"]["cards"]["grid"], th["colors"]
            for emph in (True, "accent", "soft"):
                cs = hero.card_style(g, emph)
                bg = hero.color_rgb(colors, cs["fill"])
                for key in ("heading_color", "body_color", "item_color"):
                    k = hero.contrast(hero.color_rgb(colors, cs[key]), bg)
                    self.assertGreaterEqual(k, 4.5, (theme, emph, key, round(k, 2)))
                for key in ("marker_color", "icon_color"):
                    k = hero.contrast(hero.color_rgb(colors, cs[key]), bg)
                    self.assertGreaterEqual(k, 3.0, (theme, emph, key, round(k, 2)))

    def test_validate_cards(self):
        def run(cards, **kw):
            msgs = []

            def fail(m):
                raise ValueError(m)
            try:
                hero.validate_cards({"cards": cards, **kw}, "1枚目（type=cards）", self.G, fail, msgs.append)
            except ValueError as e:
                return str(e), msgs
            return None, msgs
        self.assertIn("emphasis は true", run([{"heading": "a", "emphasis": "loud"}])[0])
        self.assertIn("span は 1 以上の整数", run([{"heading": "a", "span": 0}])[0])
        self.assertIn("列数（3）を超えています", run([{"heading": "a", "span": 4}])[0])
        _, msgs = run([{"heading": str(i), "emphasis": True} for i in range(3)])
        self.assertTrue(any("全部を強調すると強調にならない" in m for m in msgs))
        _, msgs = run([{"heading": "a", "span": 2}, {"heading": "b", "span": 2}])
        self.assertTrue(any("空きができます" in m for m in msgs))
        err, msgs = run([{"heading": "a", "emphasis": True}, {"heading": "b", "span": 2}])
        self.assertIsNone(err)
        self.assertEqual(msgs, [])


class CardsBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def cards(self, **kw):
        return dict({"type": "cards", "title": "打ち手", "cards": [
            {"heading": "A", "body": "本文 A", "emphasis": True, "icon": "bolt"},
            {"heading": "B", "body": "本文 B", "span": 2}]}, **kw)

    def test_emphasis_html_and_pptx_colors(self):
        d = write_deck(self.root, deck_with([self.cards(columns=3)]), "d")
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = html_of(d)
        self.assertIn("background:#0F3D6E", h.replace(" ", ""))        # 強調のカードは primary で塗る
        self.assertIn("color:#FFFFFF", h)                                # 見出しは反転
        x = pptx_slides(d)[0]
        self.assertIn('<a:srgbClr val="0F3D6E"/>', x)

    def test_span_changes_card_width_in_html(self):
        d = write_deck(self.root, deck_with([self.cards(columns=3)]), "d")
        build(d)
        h = html_of(d)
        widths = sorted({round(float(w), 1) for w in re.findall(r"width:([0-9.]+)px;height:\d+(?:\.\d+)?px;background:#E0E7F0", h.replace(" ", ""))})
        self.assertTrue(len(widths) >= 1)
        cw = (1136 - 2 * 16) / 3
        self.assertIn(round(2 * cw + 16, 1), widths)

    def test_no_emphasis_cards_html_unchanged_in_colors(self):
        d = write_deck(self.root, deck_with([{"type": "cards", "title": "t", "cards": [{"heading": "A", "body": "b"}]}]), "d")
        self.assertEqual(build(d).returncode, 0)
        h = html_of(d).replace(" ", "")
        self.assertNotIn("background:#0F3D6E;border-radius:12px", h)        # 強調の塗り（primary のカード）は出ない
        self.assertIn("background:#E0E7F0;border-radius:12px", h)             # 従来のカード（surface の塗り・角丸 12）のまま

    def test_icon_position_follows_span(self):
        import proposal_engine as pe
        lay = b.load_layout("default", None)
        g = b.resolve_style(lay, {"meta": {}}, {"type": "cards", "cards": [{"heading": "a", "span": 2, "icon": "bolt"}, {"heading": "b"}], "columns": 3})["grid"]
        ctx = pe.Ctx({"colors": COLORS, "fonts": {}})
        els = pe.card_icons({"cards": [{"heading": "a", "span": 2, "icon": "bolt"}, {"heading": "b"}], "columns": 3}, {"grid": g}, ctx)
        self.assertTrue(els)
        cell = hero.cards_plan(2, 3, g, [2, 1])["cells"][0]
        self.assertLess(els[0]["x"], cell[0] + cell[2])
        self.assertGreater(els[0]["x"], cell[0] + cell[2] / 2)

    def test_too_many_emphasis_warns_in_build(self):
        s = self.cards(cards=[{"heading": str(i), "emphasis": True} for i in range(3)])
        d = write_deck(self.root, deck_with([s]), "d")
        r = build(d)
        self.assertIn("全部を強調すると強調にならない", r.stderr)

    def test_heading_line_break_is_applied_to_both_outputs(self):
        # 3 列のカードで「…を設計す／る」のように最終行が 1 字だけ残る見出し。改行が必ず入り、HTML の <br> と PPTX の a:br の両方に出る
        head = "拡張性の高いプラットフォームを設計する"
        s = {"type": "cards", "title": "t", "columns": 3, "cards": [
            {"heading": head, "body": "x"}, {"heading": "b", "body": "y"}, {"heading": "c"}],
             "style": {"grid": {"thin_grow": 1}}}        # 薄い cards の文字拡大を止めて、既定の大きさで確かめる
        d = write_deck(self.root, deck_with([s]), "d")
        self.assertEqual(build(d).returncode, 0)
        h = html_of(d)
        self.assertRegex(h, r"拡張性の高い<br>プラットフォームを設計する")
        self.assertNotIn(head, h)                              # 元の 1 続きの文字列は残っていない（改行で分けた）
        self.assertIn("<a:br>", pptx_slides(d)[0])
        self.assertIn("拡張性の高い", pptx_slides(d)[0])
        # 止めたとき（line_balance: false）は改行が入らない
        s2 = dict(s, line_balance=False)
        d2 = write_deck(self.root, deck_with([s2]), "d2")
        self.assertEqual(build(d2).returncode, 0)
        self.assertIn(head, html_of(d2))

    def test_line_balance_for_cards_can_be_turned_off(self):
        s = {"type": "cards", "title": "t", "columns": 4, "line_balance": False,
             "cards": [{"heading": "拡張性の高いプラットフォーム設計", "body": "x"}, {"heading": "b"}, {"heading": "c"}, {"heading": "d"}]}
        d = write_deck(self.root, deck_with([s]), "d")
        self.assertEqual(build(d).returncode, 0)
        self.assertNotIn("<br>", re.sub(r"<br\s*/?>(?=)", "<br>", html_of(d)).split("拡張性")[1][:60])


class ImageBleedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, slides):
        d = write_deck(self.root, deck_with(slides), "d")
        make_images(d)
        return d

    def test_image_bleed_overlay_and_title_color(self):
        d = self.mk([{"type": "image", "fit": "bleed", "title": "全面", "path": "assets/bright.png", "caption": "cap"}])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = html_of(d)
        self.assertEqual(h.count("<img"), 1)               # 通常の画像枠は出さない（全面の画像だけ）
        self.assertIn('data-qa-bg="#', h)
        self.assertIn("color:#FFFFFF", h)
        self.assertEqual(pptx_slides(d)[0].count("<p:pic>"), 1)

    def test_image_default_is_unchanged(self):
        d = self.mk([{"type": "image", "title": "t", "path": "assets/dark.png"}])
        self.assertEqual(build(d).returncode, 0)
        self.assertNotIn("data-qa-bg", html_of(d))

    def test_bad_fit_and_caption_position_fail(self):
        for kw, frag in (({"fit": "stretch"}, "fit は contain / bleed"), ({"caption_position": "top"}, "caption_position は below / band")):
            exc, err = validate(one({"type": "image", "title": "t", "path": "x.png", **kw}))
            self.assertIsNotNone(exc)
            self.assertIn(frag, str(exc))

    def test_overlay_without_bleed_warns(self):
        d = self.mk([{"type": "image", "title": "t", "path": "assets/dark.png", "overlay": "primary"}])
        r = build(d)
        self.assertIn("fit: bleed", r.stderr)

    def test_caption_band_variant(self):
        d = self.mk([{"type": "image", "title": "t", "path": "assets/dark.png", "caption": "図", "caption_position": "band"}])
        self.assertEqual(build(d).returncode, 0)
        self.assertIn("飾り", pptx_slides(d)[0])

    def test_image_text_bleed_html_and_pptx_both_sides(self):
        d = self.mk([{"type": "image_text", "title": "t", "bullets": ["a"], "path": "assets/dark.png", "bleed": True},
                     {"type": "image_text", "title": "t", "bullets": ["a"], "path": "assets/dark.png", "bleed": True, "image_side": "left"}])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        for x in pptx_slides(d):
            self.assertEqual(x.count("<p:pic>"), 1)
        lay = b.load_layout("default", None)
        st = b.resolve_style(lay, {"meta": {}}, {"type": "image_text", "title": "t", "bullets": ["a"], "path": "x", "bleed": True})
        self.assertEqual((st["img"]["x"] + st["img"]["w"], st["img"]["y"] + st["img"]["h"]), (1280, 720))
        left = b.flip_image_text(st, True)
        self.assertEqual(left["img"]["x"], 0)
        self.assertEqual(left["footer_r"]["x"] + left["footer_r"]["w"], 1208)

    def test_image_text_bleed_must_be_bool(self):
        exc, err = validate(one({"type": "image_text", "title": "t", "bullets": ["a"], "path": "x.png", "bleed": "yes"}))
        self.assertIn("bleed は", str(exc))
        self.assertIn("true / false", str(exc))


class CanvasHeroTests(unittest.TestCase):
    def test_newline_in_run_becomes_line_break_in_pptx(self):
        from pptx import Presentation
        from pptx.util import Inches
        import proposal_engine as pe
        ctx = pe.Ctx({"colors": COLORS, "fonts": {"body": "Meiryo", "heading": "Meiryo"}})
        els = [ctx.box(0, 0, 400, 200, paras=[ctx.para("一行目\n二行目", 20, "text")])]
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(s, els)
        xml = s.shapes[-1]._element.xml
        self.assertIn("<a:br>", xml)
        self.assertNotIn("一行目\n二行目", xml)

    def test_image_position_html_and_crop(self):
        self.assertEqual(ce._object_position({"position": "top"}), "object-position:50% 0%;")
        self.assertEqual(ce._object_position({}), "")
        self.assertEqual(ce._position_xy({"position": "bottom right"}), (1.0, 1.0))

    def test_qa_bg_attribute_only_for_hex(self):
        self.assertEqual(ce._position_xy({"position": "zzz"}), (0.5, 0.5))


class SoftShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def slides(self):
        return [{"type": "kpi", "title": "t", "items": [{"value": "2.1", "unit": "時間", "label": "作成時間"},
                                                          {"value": "3", "unit": "倍", "label": "速度"}]},
                {"type": "summary", "title": "s", "items": [{"lead": "要点", "text": "本文"}, {"lead": "要点2", "text": "本文2"}]}]

    def test_classic_has_no_shadow_and_soft_has(self):
        d = write_deck(self.root, deck_with(self.slides()), "c")
        self.assertEqual(build(d).returncode, 0)
        self.assertNotIn("drop-shadow", (d / "build" / "d.html").read_text(encoding="utf-8"))
        d2 = write_deck(self.root, deck_with(self.slides(), shape="soft"), "s")
        r = build(d2)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (d2 / "build" / "d.html").read_text(encoding="utf-8")
        self.assertIn("drop-shadow", h)
        self.assertIn("<a:outerShdw", "".join(pptx_slidesd(d2)))


class ReviewFixTests(unittest.TestCase):
    """S2d のレビュー指摘（s2d-A-01〜13 / s2d-C-01〜06）の修正の回帰テスト。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lay = b.load_layout("default", None)

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, slides, **meta):
        d = write_deck(self.root, deck_with(slides, **meta), "d")
        make_images(d)
        return d

    def rs(self, slide, **meta):
        return b.resolve_style(self.lay, {"meta": meta}, slide)

    def panel(self, **kw):
        return {"fill": "primary", "title": "x", "text": "y", **kw}

    # --- C-01 / A-07: split の結論帯と本文領域のタイトル ---------------------------------------------------------
    def test_split_conclusion_is_fitted_to_the_remaining_width(self):
        long = "結論の文章がとても長くて、パネルの残りの幅の中で何行になるかを確かめるためのものですよ"
        base = {"type": "split", "title": "T", "panel": self.panel(), "blocks": [{"type": "bullets", "bullets": ["aaa"]}]}
        st4 = self.rs({**base, "ratio": 0.4, "conclusion": long})
        st6 = self.rs({**base, "ratio": 0.6, "conclusion": long})
        self.assertLess(st4["conclusion"]["size"], 17)                      # 640px の幅で縮む（全幅 1136px の測りだと縮まなかった）
        self.assertLessEqual(st6["conclusion"]["size"], st4["conclusion"]["size"])
        d = self.mk([{**base, "ratio": 0.6, "conclusion": long * 3}])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("結論の帯に文字が収まりません", r.stderr)
        self.assertIn("ratio を下げて本文側を広げる", r.stderr)               # split は直し方に ratio を添える
        d2 = self.mk([{**base, "ratio": 0.6, "source": "出典: " + "長い出典の文章" * 12}])
        self.assertIn("出典が3行になります", build(d2).stderr)

    def test_split_title_is_shrunk_early_for_meiryo_width(self):
        st = self.rs({"type": "split", "title": "内訳: 体裁の修正が消え、下書きとレビューが縮んだ", "panel": self.panel(),
                      "blocks": [{"type": "bullets", "bullets": ["a"]}]})
        self.assertLess(st["title"]["size"], 28)                            # 1 行ぎりぎり（約 25 字）は実機の字幅で 2 行になるので縮める
        self.assertEqual(st["title"]["fit_safety"], 0.93)

    # --- C-02: 飾り領域の値の型 --------------------------------------------------------------------------------
    def test_deco_style_values_are_validated(self):
        for bad in ({"alpha": "x"}, {"alpha": []}, {"alpha": 2}, {"w": 1e9}, {"radius": -3}, {"geom": "star"}, {"fill": "nope"}):
            exc, err = validate(one({"type": "title", "title": "T", "variant": "left-band", "style": {"deco1": bad}}))
            self.assertIsNotNone(exc, bad)
            self.assertIn("1枚目（type=title）: style.deco1.", str(exc), bad)
        exc, _ = validate(one({"type": "title", "title": "T", "variant": "left-band", "style": {"deco1": {"alpha": "x"}}}))
        self.assertIn("→", str(exc))                                           # 直し方つき（例: "alpha": 0.16）
        exc, _ = validate(one({"type": "title", "title": "T", "variant": "left-band", "style": {"deco1": {"alpha": 0.3, "w": 12}}}))
        self.assertIsNone(exc)

    def test_deco_elements_skip_bad_values_instead_of_crashing(self):
        st = {"deco1": {"x": 0, "y": 0, "w": 10, "h": 10, "fill": "accent", "alpha": "x"},
              "deco2": {"x": 0, "y": 0, "w": 1e12, "h": 10, "fill": "accent"}}
        els = hero.deco_elements(st, COLORS)
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0]["fill"], COLORS["accent"])                   # alpha が数値でなければ不透明のまま

    # --- C-03: caption の無い band ------------------------------------------------------------------------------
    def test_caption_band_without_caption_warns_and_draws_no_band(self):
        d = self.mk([{"type": "image", "title": "t", "path": "assets/dark.png", "caption_position": "band"}])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("caption_position: band は caption", r.stderr)
        self.assertNotIn("飾り", pptx_slides(d)[0])
        self.assertNotIn('data-n="飾り"', html_of(d))

    # --- C-06: 場所と直し方の文言 --------------------------------------------------------------------------------
    def test_messages_say_where_and_how_to_fix(self):
        exc, _ = validate(one({"type": "image", "fit": "bleed", "path": "/abs/x.jpg", "title": "T"}))
        self.assertIn("1枚目（type=image）: background.image:", str(exc))     # 「.image」だけがコロンの前に付かない
        exc, _ = validate(one({"type": "image_text", "title": "T", "bullets": ["a"], "path": "/abs/x.jpg", "bleed": True}))
        self.assertIn("1枚目（type=image_text）: background.image:", str(exc))
        d = self.mk([{"type": "split", "title": "T", "panel": {"image": "assets/split.png", "opacity": 0.05, "kpi": {"value": "1"}},
                      "blocks": [{"type": "bullets", "bullets": ["a"]}]}])
        self.assertIn("1枚目（type=split）: panel: 背景画像の上の文字の対比", build(d).stderr)
        d = self.mk([{"type": "title", "title": "T", "background": {"image": "assets/split.png", "overlay": "none"}}])
        err = build(d).stderr
        self.assertIn('overlay を "none" 以外', err)
        self.assertNotIn("覆いを濃く", err)                                    # 自分で none と書いたのに「覆いを濃く」とは言わない
        exc, _ = validate(one({"type": "split", "title": "T", "panel": self.panel(), "blocks": [{"type": "split", "panel": self.panel()}]}))
        self.assertIn("split は合成スライドのブロックにできません", str(exc))
        self.assertIn("入れ子", str(exc))
        exc, _ = validate(one({"type": "image_text", "title": "T", "bullets": ["a"], "path": "x.png", "bleed": "yes"}))
        self.assertIn("→", str(exc))                                          # A-12: 直し方が付く
        self.assertIn('"bleed": true', str(exc))
        self.assertIn("bleed は true / false で指定", str(exc))                 # 空白の入れ方

    # --- A-02: 章扉のタイトル行の高さ --------------------------------------------------------------------------------
    def test_section_variant_titles_are_fitted_with_their_line_height(self):
        title = "第 3 章: 実績と今後の展開について、経営会議で承認いただきたい事項"
        for var, key in (("number", "title"), ("band", "title"), ("side", "title")):
            st = self.rs({"type": "section", "title": title, "variant": var, "number": "01"})
            r, info = st[key], st["_fit"]["info"]["title"]
            self.assertEqual(r["line_height"], 1.3)
            self.assertLessEqual(info["lines"] * r["size"] * r["line_height"], r["h"] + 0.5, (var, r["size"], info))

    # --- A-03 / A-04: split パネルの kpi と細いパネル --------------------------------------------------------------------
    def _plan(self, panel, ratio=0.6):
        import proposal_engine as pe
        slide = {"type": "split", "ratio": ratio, "panel": panel, "blocks": [{"type": "text", "text": "a"}]}
        st = self.rs(slide)
        return hero.panel_plan(slide, st, pe.Ctx({"colors": COLORS, "fonts": {"body": "Meiryo", "heading": "Meiryo"}})), st

    def test_panel_kpi_never_wraps_inside_the_number(self):
        import ja_text
        plan, st = self._plan({"kpi": {"value": "¥123,456,789", "unit": "円", "label": "年間の削減見込み額"}}, ratio=0.6)
        w = st["panel"]["w"] - 2 * min(st["panel"].get("pad_x", 56), round(st["panel"]["w"] * 0.12))
        size = plan["sizes"]["kpi"]
        self.assertLess(size, 120)
        self.assertEqual(ja_text.estimate_lines("¥123,456,789円", size, w, ja_text.heading_fonts(), True), 1)
        self.assertFalse([c for c, _ in plan["issues"] if c == "panel-kpi-wide"])
        plan, _ = self._plan({"kpi": {"value": "¥123,456,789,012,345,678", "unit": "円"}}, ratio=0.25)
        self.assertIn("panel-kpi-wide", [c for c, _ in plan["issues"]])
        self.assertTrue(any("value を短く" in t for c, t in plan["issues"]))

    def test_narrow_panel_keeps_a_readable_width_and_warns_on_many_lines(self):
        plan, st = self._plan({"title": "年間の削減見込み額は、人件費換算で約 1 億 2,000 万円にのぼる"}, ratio=0.25)
        self.assertIn("panel-title-long", [c for c, _ in plan["issues"]])
        el = plan["els"][0]
        self.assertGreater(el["w"], 200)                                      # 左右の余白を詰めて 256px を切らない（以前は 144px）
        _, st4 = self._plan({"title": "短い"}, ratio=0.4)
        self.assertEqual(plan["els"][0]["x"], round(st["panel"]["w"] * 0.12))

    def test_panel_text_breaks_at_phrase_boundaries(self):
        import ja_text
        plan, st = self._plan({"title": "人が直さない仕組みをつくる", "items": ["それ以上は別のページへ分ける", "短い項目"]}, ratio=0.3)
        paras = plan["els"][0]["text"]["paragraphs"]
        texts = ["".join(r["text"] for r in p["runs"]) for p in paras]
        for t in texts:
            flat = t.replace("\n", "")
            at = 0
            for part in t.split("\n")[:-1]:
                at += len(part)
                self.assertTrue(ja_text.good_break(flat, at), (t, at))          # 改行は語の途中に入らない

    # --- A-05: phrase_wrap ---------------------------------------------------------------------------------------
    def test_phrase_wrap_only_breaks_at_good_positions(self):
        import ja_text
        texts = ["人が直さない仕組みをつくる", "経営会議向け年次報告と来期の計画", "口述から骨子を作り型に当てはめて資料を組む"]
        for t in texts:
            for width in range(180, 520, 23):
                out = ja_text.phrase_wrap(t, 40, width, None, True, min_tail=4)
                flat = out.replace("\n", "")
                self.assertEqual(flat, t)
                at = 0
                for part in out.split("\n")[:-1]:
                    at += len(part)
                    nat = ja_text.wrap_lines(t, 40, width * 0.98, None, True)
                    # 自然な折り返しの位置か、良い切れ目のどちらか（語の途中に新しく入れない）
                    self.assertTrue(ja_text.good_break(t, at) or at in [sum(len(x) for x in nat[:i + 1]) for i in range(len(nat))], (t, width, out))
        self.assertEqual(ja_text.phrase_wrap("短い", 40, 400), "短い")
        self.assertEqual(ja_text.phrase_wrap("a\nb あ", 40, 20), "a\nb あ")        # 改行済みは触らない

    def test_phrase_wrap_applies_only_to_variant_slides(self):
        import ja_text
        title = "口述から骨子を作り型に当てはめて資料を組む仕組み"
        deck = {"meta": {"id": "d"}, "slides": [{"type": "title", "title": title, "variant": "split"}, {"type": "title", "title": title}]}
        out = b.apply_line_balance(deck, self.lay)
        hf = ja_text.heading_fonts()
        # variant なし: 最終行が短いときだけ直す balance（S3a: 大きな文字は最終行に残す最低文字数が文字サイズで増える）
        self.assertEqual(out["slides"][1]["title"], ja_text.balance(title, 60, 1136, font=hf, bold=True, min_tail=ja_text.tail_min(60)))
        # variant あり（split は文字領域 576px・44px）: 文節の切れ目で改行（直せなければ従来の balance）
        pw = ja_text.phrase_wrap(title, 44, 576, font=hf, bold=True, min_tail=5)
        self.assertEqual(out["slides"][0]["title"], pw if pw != title else ja_text.balance(title, 44, 576, font=hf, bold=True))
        self.assertIn("\n", out["slides"][0]["title"])                         # 24 字は 576px に 1 行で入らない → 必ず改行が入る
        self.assertEqual(out["slides"][0]["title"].replace("\n", ""), title)

    # --- A-06: brand --------------------------------------------------------------------------------------------
    def test_brand_color_follows_the_background(self):
        d = self.mk([{"type": "title", "title": "T", "background": {"fill": "accent"}}], brand="ACME")
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        deck, th, lay = b.load_deck(d)
        slide = deck["slides"][0]
        b.validate_deck(deck, lay, th, d)
        st = b.resolve_style(lay, deck, slide)
        self.assertNotEqual(st["brand"]["color"], "accent")                     # accent 色の面に accent 色の brand は読めない
        self.assertGreaterEqual(hero.contrast(hero.color_rgb(th["colors"], st["brand"]["color"]), hero.color_rgb(th["colors"], "accent")), 4.5)
        # 背景の無いスライドは従来どおり
        st0 = b.resolve_style(lay, deck, {"type": "title", "title": "T"})
        self.assertEqual(st0["brand"]["color"], "accent")

    def test_split_moves_brand_and_title_out_of_the_way(self):
        # s3-A-04: meta.brand はパネルの上に置く（タイトルを狭めない）。文字色はパネルの文字と同じ（パネルの塗りの上で読める色）
        deck = {"meta": {"brand": "ACME"}}
        left = b.resolve_style(self.lay, deck, {"type": "split", "title": "t", "panel": self.panel(), "blocks": [{"type": "text", "text": "a"}]})
        right = b.resolve_style(self.lay, deck, {"type": "split", "side": "right", "title": "t", "panel": self.panel(),
                                                 "blocks": [{"type": "text", "text": "a"}]})
        self.assertGreaterEqual(left["brand"]["x"], left["panel"]["x"])
        self.assertLessEqual(left["brand"]["x"] + left["brand"]["w"], left["panel"]["x"] + left["panel"]["w"])   # 左のパネルの内側
        self.assertGreaterEqual(right["brand"]["x"], right["panel"]["x"])                                           # 右のパネルの内側
        self.assertLessEqual(left["title"]["x"] + left["title"]["w"], 1280 - 72)                    # タイトルは狭めない（残りの領域の全幅）
        self.assertEqual(left["title"]["w"], left["rule"]["w"])
        notitle = b.resolve_style(self.lay, deck, {"type": "split", "panel": self.panel(), "blocks": [{"type": "text", "text": "a"}]})
        self.assertEqual(notitle["body"]["y"], notitle["body"]["y_no_title"])                       # brand が残りの領域に無いので、本文は上に詰める
        plain = b.resolve_style(self.lay, {"meta": {}}, {"type": "split", "panel": self.panel(), "blocks": [{"type": "text", "text": "a"}]})
        self.assertEqual(plain["body"]["y"], plain["body"]["y_no_title"])                           # brand が無ければ従来どおり

    # --- A-08: 引用符を図形で ---------------------------------------------------------------------------------------
    def test_quote_mark_variant_is_a_shape_in_both_outputs(self):
        d = self.mk([{"type": "quote", "text": "引用", "variant": "mark"}, {"type": "statement", "message": "文", "variant": "mark"}])
        r = build(d)
        self.assertEqual(r.returncode, 0, r.stderr)
        h = html_of(d)
        self.assertNotIn("“", h)                                             # グリフ（フォントで左右が変わる）は使わない
        for x in pptx_slides(d):
            self.assertIn("<a:custGeom>", x)
            self.assertNotIn("“", x)
        # 既定（variant なし）の引用符は従来どおり文字
        d2 = self.mk([{"type": "quote", "text": "引用"}])
        self.assertEqual(build(d2).returncode, 0)
        self.assertIn("“", html_of(d2))

    # --- A-09: contact の箱 -----------------------------------------------------------------------------------------
    def test_contact_box_follows_content_height(self):
        four = self.rs({"type": "closing", "title": "C", "variant": "contact", "bullets": ["a", "b", "c", "d"]})
        eight = self.rs({"type": "closing", "title": "C", "variant": "contact", "bullets": [f"項目 {i}" for i in range(8)]})
        self.assertLess(four["deco1"]["h"], 330)
        self.assertGreater(eight["deco1"]["h"], four["deco1"]["h"])
        self.assertLessEqual(eight["deco1"]["h"], 420)
        self.assertEqual(round(four["deco1"]["y"] + four["deco1"]["h"] / 2), 360)               # 箱の縦の中心は変えない
        b0 = four["body"]
        self.assertGreaterEqual(b0["y"], four["deco1"]["y"])                                     # 中身は箱の中
        self.assertLessEqual(b0["y"] + b0["h"], four["deco1"]["y"] + four["deco1"]["h"])
        usr = self.rs({"type": "closing", "title": "C", "variant": "contact", "bullets": ["a"], "style": {"deco1": {"h": 400}}})
        self.assertEqual(usr["deco1"]["h"], 400)                                                  # 利用者の指定が勝つ

    # --- A-10: split の空白の検査 -------------------------------------------------------------------------------------
    def test_check_visual_measures_the_body_side_of_a_split(self):
        import check_visual as cv
        from PIL import Image, ImageDraw
        s = {"type": "split", "side": "left", "ratio": 0.4}
        self.assertEqual(cv.body_side_crop(s, self.lay), (568, 1208))
        self.assertEqual(cv.body_side_crop({**s, "side": "right"}, self.lay), (72, 1280 - 512 - 56))
        self.assertIsNone(cv.body_side_crop({"type": "bullets"}, self.lay))
        im = Image.new("RGB", (1280, 720), "white")
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 511, 719], fill=(15, 61, 110))                       # 全高のパネル
        dr.rectangle([568, 140, 1200, 300], fill=(30, 30, 30))                   # 本文側は上 1/3 だけに表
        x0, x1 = cv.body_side_crop(s, self.lay)
        sub = im.crop((x0, 0, x1, 720))
        prof = cv.row_ink(sub, cv.background(sub), 0, sub.width)
        band = cv.largest_blank_band(prof)
        self.assertGreaterEqual(band[0], 300)
        self.assertIn("empty-bottom", cv.band_warning("1枚目（type=split）", "split", band, 0.1, 150, cv.bottom_gap_of(prof)))
        self.assertTrue(cv.is_centered(200, 204))                                 # 縦中央の本文（valign: middle）は警告しない
        self.assertFalse(cv.is_centered(10, 277))
        full = cv.row_ink(im, cv.background(im))                                 # パネルを含めて測ると（以前）空白帯を見逃す
        self.assertLess(cv.largest_blank_band(full)[0], 150)

    # --- A-11: left-band の meta ----------------------------------------------------------------------------------------
    def test_left_band_meta_grows_upward(self):
        one_line = self.rs({"type": "title", "title": "T", "variant": "left-band", "meta": "2026-11-11"})["meta"]
        four = self.rs({"type": "title", "title": "T", "variant": "left-band", "meta": "2026-11-11\nAI 活用推進室\n部外秘\n第 2 版"})["meta"]
        self.assertEqual(one_line["y"] + one_line["h"], 686)
        self.assertEqual(four["y"] + four["h"], 686)                                              # 下端は動かない
        self.assertLess(four["y"], one_line["y"])
        self.assertGreaterEqual(four["h"], 4 * four["size"] * four["line_height"])                # 4 行が入る高さ

    # --- A-01 の build 側: パネル画像の上に 2 行以上の文字を置いたスライドが check_layout を通る -----------------------------
    def test_split_image_panel_with_two_line_title_passes_check_layout(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            self.skipTest("playwright が無い")
        d = self.mk([{"type": "split", "title": "根拠", "ratio": 0.45,
                      "panel": {"image": "assets/dark.png", "title": "この施策は、工数を 3 分の 1 に減らす"},
                      "blocks": [{"type": "bullets", "bullets": ["a", "b"]}]}])
        self.assertEqual(build(d).returncode, 0)
        r = subprocess.run([PY, str(TOOLS / "check_layout.py"), str(d), "--no-build"], capture_output=True, text=True, encoding="utf-8")
        if "Executable doesn't exist" in (r.stdout + r.stderr):
            self.skipTest("Chromium が無い")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("覆っている", r.stdout)


def pptx_slidesd(d):
    z = zipfile.ZipFile(Path(d) / "build" / "d.pptx")
    return [z.read(n).decode("utf-8") for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)]


if __name__ == "__main__":
    unittest.main()

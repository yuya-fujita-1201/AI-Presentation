#!/usr/bin/env python3
"""パターンエンジン（pattern_engine.py）と型起こしツール（pattern_from_pptx.py）のテスト（unittest）。

    python -m unittest tools/test_pattern_engine.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import canvas_engine as ce  # noqa: E402
import pattern_engine as pe  # noqa: E402

PY = sys.executable
ROOT = TOOLS.parent

THEME = {
    "colors": {"background": "#FFFFFF", "surface": "#E0E7F0", "text": "#1A2233", "muted": "#5A6B85", "primary": "#0F3D6E",
               "accent": "#007D96", "on_primary": "#FFFFFF", "border": "#BCC8D8", "heading_text": "#0F3D6E",
               "highlight_fill": "#BFDDE7", "accent_on_primary": "#7FDDF0"},
    "fonts": {"heading": "Meiryo", "body": "Yu Gothic", "code": "Consolas"},
}


def run(text, **kw):
    return {"text": text, "size": 20, "color": "text", **kw}


def box(paras, **kw):
    return {"x": 0, "y": 0, "w": 400, "h": 100, "text": {"insets": [0, 0, 0, 0], "paragraphs": paras}, **kw}


def pat(elements, slots=None, **kw):
    return {"name": "t", "slots": slots or {"a": {"kind": "text"}}, "elements": elements, **kw}


def ex(elements, slots_vals=None, slots=None, theme=THEME, deck=None, **kw):
    """pattern を展開して (elements, warns, errors) を返す"""
    warns, errs = [], []
    p = pat(elements, slots, **kw)
    els, bg = pe.expand({"slots": slots_vals or {}}, p, theme, deck, 3, 10, warns.append, errs)
    return els, warns, errs


def texts(el):
    return [[r.get("text") for r in p["runs"]] for p in el["text"]["paragraphs"]]


class InterpolationTest(unittest.TestCase):
    def test_slot_records_current_and_builtins(self):
        slots = {"a": {"kind": "text"}, "pts": {"kind": "list"}, "cards": {"kind": "records", "fields": {"head": {}, "body": {}}}}
        els, w, e = ex([box([{"runs": [run("{{a}}|{{page}}/{{total}}|{{deck.title}}|{{deck.brand}}")]},
                             {"repeat": "pts", "runs": [run("{{index}}/{{count}}:{{.}}")]},
                             {"repeat": "cards", "runs": [run("{{cards.head}}-{{body}}")]}])],
                       {"a": "値", "pts": ["x", "y"], "cards": [{"head": "H1", "body": "B1"}, {"head": "H2", "body": "B2"}]},
                       slots, deck={"meta": {"title": "デッキ", "brand": "ブランド"}})
        self.assertEqual(texts(els[0]), [["値|3/10|デッキ|ブランド"], ["1/2:x"], ["2/2:y"], ["H1-B1"], ["H2-B2"]])
        self.assertEqual((w, e), ([], []))

    def test_value_with_braces_is_not_reexpanded(self):
        els, w, e = ex([box([{"runs": [run("{{a}}")]}])], {"a": "{{page}} と {{deck.title}}"})
        self.assertEqual(texts(els[0]), [["{{page}} と {{deck.title}}"]])

    def test_unknown_variable_is_reported(self):
        els, w, e = ex([box([{"runs": [run("{{nope}}")]}])], {"a": "x"})
        self.assertEqual(len(e), 1)
        self.assertIn("nope", e[0])

    def test_newline_in_value_becomes_br(self):
        els, _, _ = ex([box([{"runs": [run("{{a}}")]}])], {"a": "1行目\n2行目"})
        runs = els[0]["text"]["paragraphs"][0]["runs"]
        self.assertEqual([r.get("text") or "br" for r in runs], ["1行目", "br", "2行目"])
        # PPTX にも出せる（a:t に生の改行を入れない）
        from pptx import Presentation
        prs = Presentation()
        ce.add_canvas_to_pptx(prs.slides.add_slide(prs.slide_layouts[6]), els)

    def test_name_alt_label_are_interpolated(self):
        els, _, _ = ex([{"kind": "placeholder", "x": 0, "y": 0, "w": 10, "h": 10, "label": "{{a}}", "name": "n{{a}}"}], {"a": "Z"})
        self.assertEqual((els[0]["label"], els[0]["name"]), ("Z", "nZ"))


class ConditionTest(unittest.TestCase):
    def test_if_and_negation(self):
        slots = {"note": {"kind": "text"}}
        els = [box([{"runs": [run("あり")]}], **{"if": "note", "name": "A"}), box([{"runs": [run("なし")]}], **{"if": "!note", "name": "B"})]
        a, _, _ = ex(els, {"note": "x"}, slots)
        b, _, _ = ex(els, {}, slots)
        c, _, _ = ex(els, {"note": "   "}, slots)
        self.assertEqual([e["name"] for e in a], ["A"])
        self.assertEqual([e["name"] for e in b], ["B"])
        self.assertEqual([e["name"] for e in c], ["B"])

    def test_if_on_paragraph_and_run_and_empty_paragraph_dropped(self):
        slots = {"a": {"kind": "text"}, "b": {"kind": "text"}}
        el = box([{"runs": [run("A:{{a}}")]}, {"runs": [run("B:{{b}}")]}, {"if": "b", "runs": [run("固定")]},
                  {"runs": [run("x"), run("y", **{"if": "b"})]}])
        els, _, _ = ex([el], {"a": "1"}, slots)
        # b が空: 差し込みがすべて空の段落（B:{{b}} は固定文字 "B:" を含むが、差し込みは空）は出ない / if 段落・if の run も出ない
        self.assertEqual(texts(els[0]), [["A:1"], ["x"]])

    def test_loop_conditions(self):
        slots = {"c": {"kind": "list"}}
        tpl = [{"x": 0, "y": 0, "w": 10, "h": 10, "name": "first", "if": "@first"}, {"x": 0, "y": 0, "w": 10, "h": 10, "name": "last", "if": "@last"},
               {"x": 0, "y": 0, "w": 10, "h": 10, "name": "odd{{index}}", "if": "@odd"}]
        els, _, _ = ex([{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 300, "h": 100, "cols": 3}, "template": tpl}], {"c": ["a", "b", "c"]}, slots)
        self.assertEqual(sorted(e["name"] for e in els), sorted(["first", "odd1", "odd3", "last"]))


class RepeatGridTest(unittest.TestCase):
    SLOTS = {"c": {"kind": "list"}}

    def cells(self, n, grid):
        tpl = [{"x": 0, "y": 0, "name": "c{{index}}"}]
        els, _, _ = ex([{"repeat": "c", "grid": dict({"x": 100, "y": 50, "w": 1000, "h": 400}, **grid), "template": tpl}],
                       {"c": [f"i{k}" for k in range(n)]}, self.SLOTS)
        return els

    def test_auto_columns_and_rows(self):
        for n, cols, rows in ((1, 1, 1), (3, 3, 1), (4, 4, 1), (5, 3, 2), (6, 3, 2), (7, 4, 2), (9, 3, 3)):
            els = self.cells(n, {"cols": "auto", "gap": 10})
            self.assertEqual(len({e["x"] for e in els}), min(n, cols), n)
            self.assertEqual(len({e["y"] for e in els}), rows, n)

    def test_cell_geometry_and_relative_margins(self):
        tpl = [{"x": 10, "y": 5, "r": 20, "b": 15, "name": "a"}, {"x": 0, "y": 0, "name": "full"}, {"x": 8, "y": 8, "w": 30, "h": 12, "name": "fix"}]
        els, _, _ = ex([{"repeat": "c", "grid": {"x": 100, "y": 50, "w": 1000, "h": 400, "cols": 2, "gap": 20}, "template": tpl}],
                       {"c": ["a", "b", "c", "d"]}, self.SLOTS)
        a = els[0]                                  # 1 つ目のセル: x=100, y=50, w=490, h=190
        self.assertEqual((a["x"], a["y"], a["w"], a["h"]), (110, 55, 490 - 10 - 20, 190 - 5 - 15))
        full = els[1]
        self.assertEqual((full["w"], full["h"]), (490, 190))
        fix = els[2]
        self.assertEqual((fix["x"], fix["w"], fix["h"]), (108, 30, 12))
        second_row = [e for e in els if e["name"] == "a"][2]
        self.assertEqual((second_row["x"], second_row["y"]), (110, 55 + 190 + 20))

    def test_last_row_center_and_cell_h(self):
        els = self.cells(5, {"cols": 3, "gap": 0, "last_row": "center"})
        xs = [e["x"] for e in els]
        self.assertAlmostEqual(xs[3], 100 + 1000 / 3 / 2, places=1)           # 2 個の最終行は半セル分ずらす
        els = self.cells(2, {"cols": 2, "cell_h": 60})
        self.assertEqual(els[0]["y"], 50)

    def test_empty_list_gives_no_elements(self):
        els = self.cells(0, {"cols": "auto"})
        self.assertEqual(els, [])

    def test_repeat_without_grid_is_an_error(self):
        els, _, errs = ex([{"repeat": "c", "template": []}], {"c": ["a"]}, self.SLOTS)
        self.assertTrue(errs)

    def test_group_in_cell_is_translated(self):
        tpl = [{"kind": "group", "rot": 0, "origin": [5, 5], "children": [{"x": 2, "y": 3, "w": 4, "h": 4}]}]
        els, _, _ = ex([{"repeat": "c", "grid": {"x": 100, "y": 200, "w": 300, "h": 100, "cols": 1}, "template": tpl}], {"c": ["a"]}, self.SLOTS)
        self.assertEqual((els[0]["children"][0]["x"], els[0]["children"][0]["y"]), (102, 203))
        self.assertEqual(els[0]["origin"], [105, 205])


class VariantsTest(unittest.TestCase):
    P = {"name": "v", "slots": {"c": {"kind": "list"}}, "variants_by": "c",
         "elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "name": "common"}],
         "variants": {"3": {"elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "name": "three"}]},
                      "4": {"elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "name": "four"}], "background": "#112233"}}}

    def test_exact_and_nearest(self):
        warns = []
        els, bg = pe.expand({"slots": {"c": list("abc")}}, self.P, THEME, None, 1, 1, warns.append)
        self.assertEqual([e["name"] for e in els], ["common", "three"])
        self.assertEqual((bg, warns), ("#FFFFFF", []))
        els, bg = pe.expand({"slots": {"c": list("abcd")}}, self.P, THEME)
        self.assertEqual(([e["name"] for e in els], bg), (["common", "four"], "#112233"))
        els, bg = pe.expand({"slots": {"c": list("abcdef")}}, self.P, THEME, None, 1, 1, warns.append)   # 6 個は無い → 4 個用で描き、注意を出す
        self.assertEqual(els[-1]["name"], "four")
        self.assertIn("4 個用", warns[0])
        els, bg = pe.expand({"slots": {"c": list("a")}}, self.P, THEME, None, 1, 1, warns.append)        # 1 個は 3 個用で
        self.assertEqual(els[-1]["name"], "three")

    def test_check_pattern_expands_every_variant(self):
        errs, warns = pe.check_pattern(dict(self.P, name="v"), THEME)
        self.assertEqual(errs, [])
        bad = json.loads(json.dumps(self.P))
        bad["variants"]["4"]["elements"][0]["fill"] = "nonexistent_token"
        errs, _ = pe.check_pattern(bad, THEME)
        self.assertTrue(any("nonexistent_token" in e for e in errs))


class TokenTest(unittest.TestCase):
    def test_colors_fonts_sizes(self):
        el = {"x": 0, "y": 0, "w": 100, "h": 50, "fill": "primary", "line": {"color": {"color": "border", "alpha": 0.5}, "width": "$line.normal"},
              "shadow": {"dx": 1, "dy": 1, "blur": 2, "color": "#000"},
              "text": {"paragraphs": [{"runs": [{"text": "a", "size": "$type.h1", "color": "#abc", "font": ["@heading"]},
                                                {"text": "b", "size": 12, "color": "on_primary", "font": ["@body", "Arial"]},
                                                {"text": "c", "size": 12, "font": ["@code"]}]}]}}
        els, w, e = ex([el])
        o = els[0]
        self.assertEqual(o["fill"], "#0F3D6E")
        self.assertEqual(o["line"], {"color": {"color": "#BCC8D8", "alpha": 0.5}, "width": 2})
        self.assertEqual(o["shadow"]["color"], "#000000")
        r = o["text"]["paragraphs"][0]["runs"]
        self.assertEqual((r[0]["size"], r[0]["color"], r[0]["font"]), (36, "#AABBCC", ["Meiryo"]))
        self.assertEqual(r[1]["font"], ["Yu Gothic", "Arial"])
        self.assertEqual(r[2]["font"], ["Consolas"])
        self.assertEqual(e, [])

    def test_gradient_and_pattern_colors(self):
        el = {"x": 0, "y": 0, "w": 1, "h": 1, "fill": {"gradient": {"angle": 90, "stops": [[0, "primary"], [100, "#FFF"]]}}}
        el2 = {"x": 0, "y": 0, "w": 1, "h": 1, "fill": {"pattern": "ltDnDiag", "fg": "accent", "bg": "background"}}
        els, _, e = ex([el, el2])
        self.assertEqual(els[0]["fill"]["gradient"]["stops"], [[0, "#0F3D6E"], [100, "#FFFFFF"]])
        self.assertEqual((els[1]["fill"]["fg"], els[1]["fill"]["bg"]), ("#007D96", "#FFFFFF"))

    def test_unknown_tokens_are_reported_with_fix(self):
        el = {"x": 0, "y": 0, "w": 1, "h": 1, "fill": "no_such_color",
              "text": {"paragraphs": [{"runs": [{"text": "a", "size": "$type.zzz", "font": ["@fancy"]}]}]}}
        els, w, e = ex([el])
        self.assertEqual(els[0]["fill"], "#000000")
        self.assertEqual(len(e), 3)
        self.assertTrue(any("no_such_color" in m and "使えるトークン" in m for m in e))
        self.assertTrue(any("$type.zzz" in m for m in e))

    def test_theme_tokens_override_defaults(self):
        th = dict(THEME, tokens={"type": {"h1": 40, "huge": 90}, "radius": {"card": 20}})
        el = {"x": 0, "y": 0, "w": 100, "h": 100, "fill": "primary", "radius": "$radius.card",
              "text": {"paragraphs": [{"runs": [{"text": "a", "size": "$type.h1"}, {"text": "b", "size": "$type.huge"}, {"text": "c", "size": "$type.h2"}]}]}}
        els, _, e = ex([el], theme=th)
        self.assertEqual([r["size"] for r in els[0]["text"]["paragraphs"][0]["runs"]], [40, 90, 28])   # h2 は既定の表から
        self.assertEqual((els[0]["geom"], els[0]["adj"]["adj"]), ("roundRect", 20000))

    def test_radius_px_is_relative_to_short_side(self):
        els, _, _ = ex([{"x": 0, "y": 0, "w": 300, "h": 60, "fill": "primary", "radius": 12}])
        self.assertEqual(els[0]["adj"]["adj"], 20000)
        els, _, _ = ex([{"x": 0, "y": 0, "w": 30, "h": 20, "fill": "primary", "radius": 999}])
        self.assertEqual(els[0]["adj"]["adj"], 50000)

    def test_line_height_becomes_fixed_pitch(self):
        els, _, _ = ex([box([{"lineHeight": 1.5, "runs": [run("a", size=24)]}, {"runs": [run("b", size=20)]},
                             {"lineHeightPx": 30, "lineHeight": 2, "runs": [run("c")]}])])
        ps = els[0]["text"]["paragraphs"]
        self.assertEqual([p.get("lineHeightPx") for p in ps], [round(24 * 1.2 * 1.5, 2), round(20 * 1.2 * pe.DEFAULT_LH, 2), 30])
        self.assertFalse(any("lineHeight" in p for p in ps))
        # HTML の行送りと PPTX の行送り（固定値）が一致する
        from pptx import Presentation
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(s, els)
        self.assertIn(f'<a:spcPts val="{int(ps[0]["lineHeightPx"] * 75)}"/>', next(iter(s.shapes))._element.xml.replace("\n", "").replace("  ", ""))


class FitTest(unittest.TestCase):
    def fit_el(self, text, sizes, w=300, h=100, marker=False):
        r = {"text": "{{a}}", "size": "@fit" if marker else sizes[0], "color": "text"}
        return {"x": 0, "y": 0, "w": w, "h": h, "fit": {"sizes": sizes}, "name": "F",
                "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [r]}]}}

    def size_of(self, els):
        return els[0]["text"]["paragraphs"][0]["runs"][0]["size"]

    def test_picks_largest_that_fits(self):
        short, w1, _ = ex([self.fit_el("", [28, 24, 20, 16])], {"a": "短い文"})
        self.assertEqual(self.size_of(short), 28)
        self.assertEqual(w1, [])
        long, w2, _ = ex([self.fit_el("", [28, 24, 20, 16])], {"a": "これは長い文章です。" * 6})
        self.assertLess(self.size_of(long), 28)
        self.assertGreaterEqual(self.size_of(long), 16)
        self.assertEqual(w2, [])
        # 選んだサイズで実際に収まる
        from ja_text import estimate_lines
        s = self.size_of(long)
        self.assertLessEqual(estimate_lines("これは長い文章です。" * 6, s, 300, font=["Yu Gothic"]) * s * 1.2 * pe.DEFAULT_LH, 100.5)

    def test_warns_when_even_smallest_does_not_fit(self):
        els, w, _ = ex([self.fit_el("", [28, 24, 20, 16])], {"a": "あ" * 400})
        self.assertEqual(self.size_of(els), 16)
        self.assertEqual(len(w), 1)
        self.assertIn("最小サイズ 16px", w[0])
        self.assertIn("→", w[0])

    def test_marker_only_changes_marked_runs_and_others_scale_otherwise(self):
        el = self.fit_el("", [30, 20], marker=True)
        el["text"]["paragraphs"][0]["runs"].append({"text": "固定", "size": 12})
        els, _, _ = ex([el], {"a": "あ" * 60})
        runs = els[0]["text"]["paragraphs"][0]["runs"]
        self.assertEqual(runs[0]["size"], 20)
        self.assertEqual(runs[1]["size"], 12)
        # マーカーなし: 全 run を sizes[0] からの比率で拡縮する
        el = {"x": 0, "y": 0, "w": 300, "h": 100, "fit": {"sizes": [30, 15]},
              "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{a}}", "size": 30}]}, {"runs": [{"text": "小", "size": 20}]}]}}
        els, _, _ = ex([el], {"a": "あ" * 60})
        ps = els[0]["text"]["paragraphs"]
        self.assertEqual((ps[0]["runs"][0]["size"], ps[1]["runs"][0]["size"]), (15, 10))

    def test_fit_uses_cell_size_in_repeat(self):
        tpl = [{"x": 0, "y": 0, "w": 100, "h": 40, "fit": {"sizes": [24, 18, 12]},
                "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{.}}", "size": 24}]}]}}]
        els, _, _ = ex([{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 300, "h": 40, "cols": 3}, "template": tpl}],
                       {"c": ["短", "中くらいの文字列です", "かなり長い文字列がここに入る場合の例"]}, {"c": {"kind": "list"}})
        sizes = [e["text"]["paragraphs"][0]["runs"][0]["size"] for e in els]
        self.assertEqual(sizes[0], 24)
        self.assertGreater(sizes[0], sizes[1])
        self.assertGreaterEqual(sizes[1], sizes[2])


class SlotValidationTest(unittest.TestCase):
    P = {"name": "sv", "slots": {
        "title": {"kind": "text", "required": True, "max_chars": 10, "label": "見出し", "example": "例"},
        "pts": {"kind": "list", "min": 2, "max": 3, "max_chars": 5},
        "cards": {"kind": "records", "min": 1, "max": 2, "fields": {"head": {"max_chars": 4, "required": True}, "body": {}}},
        "img": {"kind": "image"}}, "elements": []}

    def check(self, slots):
        return pe.slot_problems({"type": "pattern", "pattern": "sv", "slots": slots}, self.P)

    def test_missing_required_is_error_with_fix(self):
        errs, _ = self.check({})
        self.assertEqual(len(errs), 1)
        self.assertIn("title", errs[0])
        self.assertIn("→", errs[0])
        self.assertIn("例", errs[0])

    def test_unknown_slot_has_suggestion(self):
        _, warns = self.check({"title": "a", "titel": "b", "zzz": "c"})
        self.assertTrue(any("titel" in w and "title" in w.split("もしかして")[-1] for w in warns))
        self.assertTrue(any("zzz" in w and "使えるスロット" in w for w in warns))

    def test_max_chars_and_counts_warn(self):
        errs, warns = self.check({"title": "あ" * 11, "pts": ["a"], "cards": [{"head": "12345", "body": "x"}] * 3})
        self.assertEqual(errs, [])
        text = "\n".join(warns)
        for needle in ("目安（10 文字）", "最小 2 個", "最大 2 個", "'head' が 5 文字"):
            self.assertIn(needle, text)
        _, warns = self.check({"title": "a", "pts": ["abcdefg", "b"]})
        self.assertTrue(any("1 個目が 7 文字" in w for w in warns))

    def test_type_errors_are_errors_not_exceptions(self):
        errs, _ = self.check({"title": ["x"], "pts": {"a": 1}, "cards": ["str"], "img": 5})
        self.assertEqual(len(errs), 4)
        errs, _ = self.check({"title": "a", "cards": [{"body": "x"}]})
        self.assertTrue(any("'head'" in e for e in errs))
        errs, _ = pe.slot_problems({"slots": [1]}, self.P)
        self.assertTrue(errs)


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._env = os.environ.pop("SLIDE_DECK_PATTERNS", None)
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        os.environ.pop("SLIDE_DECK_PATTERNS", None)
        if self._env is not None:
            os.environ["SLIDE_DECK_PATTERNS"] = self._env
        self.tmp.cleanup()

    def write(self, d, name, label):
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.json").write_text(json.dumps({"name": name, "label": label, "slots": {"a": {}}, "elements": []}), encoding="utf-8")

    def test_search_order(self):
        proj = self.root / "proj"
        deck = proj / "decks" / "d1"
        deck.mkdir(parents=True)
        os.chdir(self.root)
        self.write(proj / "patterns", "x", "project")
        self.assertEqual(pe.load_pattern("x", deck)["label"], "project")          # 親の patterns/
        self.write(deck / "patterns", "x", "deck")
        self.assertEqual(pe.load_pattern("x", deck)["label"], "deck")             # <deck>/patterns/ が先
        env = self.root / "envpat"
        self.write(env, "x", "env")
        os.environ["SLIDE_DECK_PATTERNS"] = str(env)
        self.assertEqual(pe.load_pattern("x", deck)["label"], "env")              # 環境変数が最優先
        del os.environ["SLIDE_DECK_PATTERNS"]
        self.write(self.root / "patterns", "cwdonly", "cwd")
        self.assertEqual(pe.load_pattern("cwdonly", deck)["label"], "cwd")        # カレントの patterns/
        self.assertEqual(pe.load_pattern("conclusion-evidence", deck)["name"], "conclusion-evidence")   # 同梱
        self.assertIn("pillars", pe.available_names(deck))
        dirs = pe.pattern_dirs(deck)
        self.assertEqual(dirs[0].resolve(), (deck / "patterns").resolve())      # deck_paths は解決済みのパスで返す
        self.assertEqual(dirs[-1].resolve(), pe.BUNDLED_DIR.resolve())

    def test_same_rule_as_deck_paths(self):
        """core の deck_paths.search_dirs("patterns", ...) と同じ探索順（次の段階で寄せられる）"""
        try:
            import deck_paths as dp
        except ImportError:
            self.skipTest("deck_paths 未導入")
        deck = self.root / "a" / "b" / "c" / "d" / "deck"
        deck.mkdir(parents=True)
        os.chdir(self.root)
        os.environ["SLIDE_DECK_PATTERNS"] = str(self.root / "e1") + os.pathsep + str(self.root / "e2")
        mine = [Path(p).resolve() for p in pe.pattern_dirs(deck)]
        theirs = [Path(p).resolve() for p in dp.search_dirs("patterns", deck)]
        self.assertEqual(mine, theirs)

    def test_bad_names_and_files(self):
        self.assertIsNone(pe.load_pattern("../etc/passwd", self.root))
        self.assertIsNone(pe.load_pattern("a.b", self.root))
        self.assertIsNone(pe.load_pattern("nonexistent-pattern", self.root))
        d = self.root / "decks" / "d"
        (d / "patterns").mkdir(parents=True)
        (d / "patterns" / "broken.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(pe.PatternError):
            pe.load_pattern("broken", d)
        (d / "patterns" / "arr.json").write_text("[1]", encoding="utf-8")
        with self.assertRaises(pe.PatternError):
            pe.load_pattern("arr", d)

    def test_validate_for_slides(self):
        errs, warns = [], []

        def fail(m):
            errs.append(m)
        pe.validate({"type": "pattern", "pattern": "conclusion-evidencee", "slots": {}}, 2, self.root, fail, warns.append)
        self.assertIn("3枚目（type=pattern）", errs[0])
        self.assertIn("もしかして: conclusion-evidence", errs[0])
        errs.clear()
        pe.validate({"type": "pattern", "slots": {}}, 0, self.root, fail, warns.append)
        self.assertIn("pattern（パターン名）", errs[0])
        errs.clear()
        pe.validate({"type": "pattern", "pattern": "pillars", "slots": {"title": "t"}}, 0, self.root, fail, warns.append)
        self.assertIn("必須のスロット 'pillars'", errs[0])
        self.assertIn("foundation", "".join(errs))
        errs.clear()
        pe.validate({"type": "pattern", "pattern": "pillars", "slots": {"title": "t", "foundation": "f", "pillars": [
            {"head": "a", "body": "b"}] * 3, "bogus": 1}}, 0, self.root, fail, warns.append)
        self.assertEqual(errs, [])
        self.assertTrue(any("bogus" in w for w in warns))

    def test_image_slot_path_is_validated_through_canvas(self):
        d = self.root / "d"
        (d / "patterns").mkdir(parents=True)
        (d / "assets").mkdir()
        (d / "patterns" / "pic.json").write_text(json.dumps({
            "name": "pic", "slots": {"photo": {"kind": "image", "required": True, "example": "assets/a.png"}},
            "elements": [{"kind": "image", "x": 0, "y": 0, "w": 100, "h": 100, "path": "{{photo}}", "fit": "cover"}]}), encoding="utf-8")
        errs = []
        pe.validate({"type": "pattern", "pattern": "pic", "slots": {"photo": "../secret.png"}}, 0, d, errs.append, lambda m: None)
        self.assertIn("..", errs[0])
        errs.clear()
        pe.validate({"type": "pattern", "pattern": "pic", "slots": {"photo": "assets/none.png"}}, 0, d, errs.append, lambda m: None)
        self.assertIn("見つかりません", errs[0])
        from PIL import Image
        Image.new("RGB", (10, 10)).save(d / "assets" / "ok.png")
        errs.clear()
        pe.validate({"type": "pattern", "pattern": "pic", "slots": {"photo": "assets/ok.png"}}, 0, d, errs.append, lambda m: None)
        self.assertEqual(errs, [])


class ReviewFixTest(unittest.TestCase):
    """レビュー指摘（C-01 負の大きさ / C-02 制御文字 / C-03 数値 / C-05 wrap・vert / C-07 空の項目 / C-08・A-07 メッセージ / A-03 文節改行）"""

    def pillars_expand(self, n):
        pat_ = pe.load_pattern("pillars", None)
        sl_ = pe.example_slide(pat_, n)
        warns, errs = [], []
        els, _ = pe.expand(sl_, pat_, THEME, None, 1, 1, warns.append, errs)
        return sl_, pat_, els, warns, errs

    def test_over_max_never_gives_negative_extent_and_explains(self):
        _sl, _pat, els, warns, errs = self.pillars_expand(5)
        self.assertEqual(errs, [])
        self.assertTrue(all(e.get("w", 0) >= 0 and e.get("h", 0) >= 0 for e in els))
        self.assertEqual(ce.validate_canvas_problems({"elements": els}), [])
        self.assertEqual(len(warns), 1)                                   # 要素ごとに警告を出さない（1 回にまとめる）
        self.assertIn("4 個まで", warns[0])
        self.assertIn("'pillars'", warns[0])
        self.assertNotIn("{{", warns[0])                                  # 未展開のテンプレート名を出さない
        _sl, _pat, els, warns, errs = self.pillars_expand(30)
        self.assertTrue(all(e.get("w", 0) >= 0 and e.get("h", 0) >= 0 for e in els))

    def test_over_max_in_pptx_has_no_negative_extent(self):
        from pptx import Presentation
        import re
        import zipfile
        sl_, pat_, _els, _w, _e = self.pillars_expand(30)
        canvas = pe.to_canvas_slide(sl_, pat_, THEME)
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        ce.add_canvas_to_pptx(slide, canvas["elements"])
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "o.pptx"
            prs.save(str(f))
            xml = zipfile.ZipFile(f).read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIsNone(re.search(r'c[xy]="-', xml))

    def test_validate_reports_over_max_once(self):
        sl_ = pe.example_slide(pe.load_pattern("pillars", None), 5)
        warns, errs = [], []
        pe.validate(sl_, 0, None, errs.append, warns.append)
        self.assertEqual(errs, [])
        self.assertEqual(len([w for w in warns if "pillars" in w]), 1)
        self.assertIn("先頭の 4 個だけ描きました", warns[0])

    def test_negative_size_in_absolute_element_is_pattern_error(self):
        els, warns, errs = ex([{"x": 0, "y": 700, "b": 100, "w": 50, "name": "はみ出し", "fill": "primary"}])
        self.assertEqual(els[0]["h"], 0)
        self.assertEqual(len(errs), 1)
        self.assertIn("はみ出し", errs[0])

    def test_float_slots_keep_digits_and_never_use_exponent(self):
        self.assertEqual(pe._to_text(1234567.0), "1234567")
        self.assertEqual(pe._to_text(12345678.5), "12345678.5")
        self.assertEqual(pe._to_text(1234.5678), "1234.5678")
        self.assertEqual(pe._to_text(0.1), "0.1")
        self.assertEqual(pe._to_text(1e-7), "0.0000001")
        self.assertEqual(pe._to_text(-3.0), "-3")
        self.assertEqual(pe._to_text(7), "7")

    def test_xml_illegal_chars_are_dropped_from_slots(self):
        self.assertEqual(pe._to_text("a\x0cb\x00c\x0bd"), "abcd")
        els, warns, errs = ex([box([{"runs": [run("{{a}}")]}])], {"a": "題\x0c名"})
        self.assertEqual(texts(els[0]), [["題名"]])

    def test_blank_items_are_counted_after_normalising(self):
        P = {"name": "bl", "slots": {
            "before": {"kind": "list", "required": True, "min": 2, "label": "前"},
            "ev": {"kind": "records", "required": True, "fields": {"head": {}, "body": {}}}}, "elements": []}

        def chk(slots):
            return pe.slot_problems({"type": "pattern", "pattern": "bl", "slots": slots}, P)
        errs, _ = chk({"before": ["", " "], "ev": [{"head": "a", "body": "b"}]})
        self.assertTrue(any("'before'" in e and "空の項目だけ" in e for e in errs))
        errs, _ = chk({"before": ["a", "b"], "ev": [{"head": "", "body": ""}] * 2})
        self.assertTrue(any("'ev'" in e for e in errs))
        errs, warns = chk({"before": ["a", "", "b"], "ev": [{"head": "x", "body": ""}]})
        self.assertEqual(errs, [])
        self.assertTrue(any("2 個目が空" in w for w in warns))
        _, warns = chk({"before": ["a", "", ""], "ev": [{"head": "x"}]})          # 空を除くと 1 個 → min 2 を下回る
        self.assertTrue(any("最小 2 個" in w for w in warns))
        recs = pe._norm_value(P["slots"]["ev"], [{"head": "", "body": ""}, {"head": "a"}])
        self.assertEqual(recs, [{"head": "a", "body": ""}])

    def test_fit_respects_wrap_false_and_vert(self):
        def size(tx, w, h):
            el = {"x": 0, "y": 0, "w": w, "h": h, "fit": {"sizes": [24, 21, 19, 17]}, "text": dict(
                {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{a}}", "size": 24, "color": "text"}]}]}, **tx)}
            els, warns, _ = ex([el], {"a": "ラベルテキスト"})
            return els[0]["text"]["paragraphs"][0]["runs"][0]["size"], warns
        self.assertEqual(size({}, 120, 50)[0], 17)                   # 折り返す枠: 120px 幅では 2 行になって縮む
        self.assertEqual(size({"wrap": False}, 120, 50), (24, []))   # 折り返さない 1 行ラベルは縮まない
        self.assertEqual(size({"vert": "270"}, 50, 200), (24, []))   # 縦書きは行の長さ = 枠の高さ
        self.assertLess(size({"vert": "270"}, 50, 100)[0], 24)

    def test_messages_use_expanded_name_and_location(self):
        sl_, pat_, _els, warns, _e = self.pillars_expand(4)
        long_slide = dict(sl_, slots=dict(sl_["slots"], pillars=[{"head": "見出し", "body": "あ" * 400}] * 4))
        w = []
        pe.expand(long_slide, pat_, THEME, None, 1, 1, w.append, [])
        fit_w = [m for m in w if "最小サイズ" in m]
        self.assertTrue(fit_w)
        self.assertTrue(all("{{" not in m for m in fit_w), fit_w)
        self.assertTrue(any("柱1の説明" in m for m in fit_w), fit_w)
        # 名前のない要素は位置で示す
        _els, _w, errs = ex([{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "nocolor"}])
        self.assertIn("elements[0]", errs[0])

    def test_image_slot_error_names_the_slot(self):
        P = {"name": "im", "slots": {"photo": {"kind": "image", "label": "写真"}}, "elements": []}
        with tempfile.TemporaryDirectory() as d:
            errs, _ = pe.slot_problems({"slots": {"photo": "assets/none.png"}}, P, d)
        self.assertIn("'photo'", errs[0])
        self.assertIn("assets/none.png", errs[0])
        errs, _ = pe.slot_problems({"slots": {"photo": "../x.png"}}, P, None)
        self.assertIn("'photo'", errs[0])

    def test_check_pattern_reports_structure_and_tokens_together_and_token_hints(self):
        bad = {"name": "b", "slots": {"a": {"kind": "text"}, "pts": {"kind": "list"}},
               "elements": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "primry", "radius": "$radius.cardd"},
                            {"x": 0, "y": 0, "w": 1, "h": 1, "text": {"paragraphs": [{"runs": [{"text": "{{nope}}"}]}]}}]}
        errs, _ = pe.check_pattern(bad, THEME)
        text = "\n".join(errs)
        self.assertIn("nope", text)                          # 構造の誤り
        self.assertIn("primry", text)                        # 色・トークンの誤りも同時に出る
        self.assertIn("もしかして: primary", text)
        self.assertIn("もしかして: $radius.card", text)
        self.assertIn("elements[0]", text)                   # 名前のない要素は位置で示す

    def test_check_pattern_warns_grid_slot_without_max_and_probes_max_plus_one(self):
        grid = {"repeat": "cards", "grid": {"x": 0, "y": 0, "w": 400, "h": 300, "cols": 2},
                "template": [{"x": 0, "y": 0, "w": 100, "h": 100, "fill": "primary"}]}
        _e, warns = pe.check_pattern({"name": "g", "slots": {"cards": {"kind": "list", "example": ["a"]}}, "elements": [grid]}, THEME)
        self.assertTrue(any("cards.max" in w for w in warns))
        tight = {"repeat": "cards", "grid": {"x": 0, "y": 0, "w": 400, "h": 100, "cols": 1, "gap": 40},
                 "template": [{"x": 0, "y": 0, "w": 100, "b": 10, "fill": "primary"}]}
        errs, warns = pe.check_pattern({"name": "g", "slots": {"cards": {"kind": "list", "max": 2, "example": ["a"]}},
                                        "elements": [tight]}, THEME)
        self.assertEqual(errs, [])                           # 上限 +1 個で潰れても、エラー・例外にはならない

    def test_japanese_wraps_at_phrase_boundaries(self):
        text = "各部署に 1 名の推進役を置き、勉強会と相談窓口で支える。1 か月ごとに 1 つずつ自動化する"
        els, warns, _ = ex([box([{"runs": [run("{{a}}")]}], w=230)], {"a": text})
        paras = els[0]["text"]["paragraphs"]
        lines = []
        cur = ""
        for r in paras[0]["runs"]:
            if r.get("br"):
                lines.append(cur)
                cur = ""
            else:
                cur += r["text"]
        lines.append(cur)
        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines).replace(" ", ""), text.replace(" ", ""))
        for ln in lines:
            self.assertFalse(ln.endswith(("窓", "か")) and not ln.endswith("か月"), ln)
        self.assertFalse(any(a.endswith("窓") and b.startswith("口") for a, b in zip(lines, lines[1:])))
        self.assertFalse(any(a.endswith("1") and b.startswith("か月") for a, b in zip(lines, lines[1:])))
        # 実測の幅に収まる（折り返しが増えない）
        import ja_text
        for ln in lines:
            self.assertLessEqual(len(ja_text.wrap_lines(ln, 20, 230, font=["Yu Gothic"])), 1, ln)
        # 止めたいとき
        els2, _, _ = ex([dict(box([{"runs": [run("{{a}}")]}], w=230), balance=False)], {"a": text})
        self.assertEqual(len(els2[0]["text"]["paragraphs"][0]["runs"]), 1)
        # 英文・短文・すでに改行のある文は触らない
        for t in ("short", "A fairly long english sentence that will wrap at word boundaries only", "一行目\n二行目"):
            els3, _, _ = ex([box([{"runs": [run("{{a}}")]}], w=230)], {"a": t})
            self.assertEqual(len([r for r in els3[0]["text"]["paragraphs"][0]["runs"] if not r.get("br")]), len(t.split("\n")))

    def test_bundled_patterns_do_not_break_words(self):
        pat_ = pe.load_pattern("pillars", None)
        sl_ = pe.example_slide(pat_, 4)
        els, _ = pe.expand(sl_, pat_, THEME, None, 1, 1, lambda m: None, [])
        broken = []
        for e in els:
            for p in (e.get("text") or {}).get("paragraphs", []):
                rs = p["runs"]
                joined, cuts = "", []
                for r in rs:
                    if r.get("br"):
                        cuts.append(len(joined))
                    else:
                        joined += r.get("text", "")
                for c in cuts:
                    if not pe._can_break(joined, c):
                        broken.append(joined[max(0, c - 3):c + 3])
        self.assertEqual(broken, [])


    # ---- 型起こし（レビュー指摘 C-05 / C-06 / A-01 / A-02 / A-04 / A-09）
    def _slide(self, elements):
        return {"type": "canvas", "background": "#FFFFFF", "elements": elements}

    @staticmethod
    def _t(x, y, w, h, text, size, **kw):
        runs = [{"text": text, "size": size, "color": "#1A2233"}]
        return dict({"x": x, "y": y, "w": w, "h": h, "text": {"paragraphs": [{"runs": runs}]}}, **kw)

    def test_from_pptx_keeps_line_breaks_and_counts_only_real_format_mixes(self):
        r = {"size": 28, "color": "#1A2233"}
        el = {"x": 10, "y": 10, "w": 600, "h": 100, "text": {"paragraphs": [
            {"runs": [dict(r, text="Hello"), {"br": True, "size": 28}, dict(r, text="World second line")]},
            {"runs": [dict(r, text="混ぜる"), dict(r, text="太字", bold=True)]}]}}
        pat_, rep = pfp.build_pattern(self._slide([el]), "lb", THEME, "default")
        ex_ = [d["example"] for d in pat_["slots"].values()]
        self.assertEqual(ex_[0], "Hello\nWorld second line")
        self.assertEqual(rep["multi_run"], ["混ぜる太字"])               # 同じ書式の run が br で分かれているだけのものは数えない
        els, _ = pe.expand(pe.example_slide(pat_), pat_, THEME)
        self.assertTrue(any(r_.get("br") for p_ in els[0]["text"]["paragraphs"] for r_ in p_["runs"]))     # 展開で br に戻る

    def test_from_pptx_does_not_fit_nowrap_labels(self):
        el = self._t(10, 10, 120, 40, "ラベルテキスト", 24)
        el["text"]["wrap"] = False
        el2 = self._t(10, 80, 300, 40, "折り返す文", 24)
        pat_, _ = pfp.build_pattern(self._slide([el, el2]), "nw", THEME, "default")
        self.assertNotIn("fit", pat_["elements"][0])
        self.assertIn("fit", pat_["elements"][1])

    def test_from_pptx_restores_deck_title_and_names_card_slots(self):
        boxes = []
        for k in range(3):
            x = 72 + k * 380
            boxes.append({"x": x, "y": 200, "w": 360, "h": 300, "geom": "roundRect", "fill": "#E0E7F0", "line": {"color": "#BCC8D8", "width": 1}})
            boxes.append(self._t(x + 18, 220, 320, 40, f"見出し{k}", 24))
            boxes.append(self._t(x + 18, 270, 320, 40, f"説明{k}", 16))
        els = [self._t(72, 16, 600, 24, "上の小さな文言", 14), self._t(72, 42, 1000, 60, "ページの見出し", 36),
               self._t(72, 120, 1000, 40, "リード文です", 20)] + boxes + [self._t(72, 678, 700, 24, "デッキ名", 13)]
        pat_, rep = pfp.build_pattern(self._slide(els), "cards", THEME, "default", deck_meta={"title": "デッキ名", "brand": "社名"})
        names = list(pat_["slots"])
        for want in ("kicker", "title", "lead", "card1_head", "card1_sub", "card2_head", "card3_sub"):
            self.assertIn(want, names)
        self.assertFalse(any(n.startswith("text") for n in names), names)
        self.assertEqual(rep["deck_vars"], ["title"])
        self.assertIn("{{deck.title}}", json.dumps(pat_, ensure_ascii=False))
        self.assertNotIn("デッキ名", [d["example"] for d in pat_["slots"].values()])     # フッターはスロットにならない
        self.assertIn("カード1の見出し", pat_["slots"]["card1_head"]["label"])
        # テーマ・文言を変えて展開すると、フッターはデッキ名に追随する
        els2, _ = pe.expand(pe.example_slide(pat_), pat_, THEME, {"meta": {"title": "別の案件", "brand": ""}})
        self.assertIn("別の案件", json.dumps(els2, ensure_ascii=False))
        # deck_meta が無ければ従来どおりスロット（PPTX 単体から起こす場合）
        pat2, _ = pfp.build_pattern(self._slide(els), "cards", THEME, "default")
        self.assertTrue(any(d["example"] == "デッキ名" for d in pat2["slots"].values()))

    def test_from_pptx_list_max_follows_what_fits(self):
        runs = lambda t: [{"text": t, "size": 14, "color": "#1A2233"}]      # noqa: E731
        el = {"x": 20, "y": 20, "w": 300, "h": 70, "name": "points", "text": {"paragraphs": [
            {"bullet": {"char": "•"}, "marL": 18, "indent": -18, "runs": runs("一つ目の点")},
            {"bullet": {"char": "•"}, "marL": 18, "indent": -18, "runs": runs("二つ目の点")}]}}
        pat_, _ = pfp.build_pattern(self._slide([el]), "bl", THEME, "default")
        d = next(v for v in pat_["slots"].values() if v["kind"] == "list")
        self.assertGreaterEqual(d["max"], 2)
        self.assertLessEqual(d["max"], 4)
        errs, warns = pe.check_pattern(pat_, THEME)
        self.assertEqual((errs, [w for w in warns if "収まりません" in w]), ([], []))     # 作った直後から直せない警告が出ない

    def test_import_uses_underscore_keys_so_core_does_not_warn(self):
        import pptx_import as pi
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as d:
            prs = Presentation()
            prs.slides.add_slide(prs.slide_layouts[6])
            src = Path(d) / "a.pptx"
            prs.save(str(src))
            sl_ = pi.Importer(src).convert({1})[0]
            self.assertIn("_source_page", sl_)
            self.assertNotIn("source_page", sl_)
            r = subprocess.run([PY, str(TOOLS / "pptx_import.py"), str(src), "--into", str(Path(d) / "deck")],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            meta = json.loads((Path(d) / "deck" / "deck.json").read_text(encoding="utf-8"))["meta"]
            self.assertEqual((meta["_source"], meta["_generator"]), ("a.pptx", "pptx_import.py"))

    def test_deck_info_maps_deck_slide_numbers_to_pptx_numbers(self):
        deck = ROOT / "examples" / "template-sample"
        if not (deck / "deck.json").is_file():
            self.skipTest("examples/template-sample が無い")
        meta, pmap = pfp._deck_info(deck)
        self.assertTrue(meta and meta.get("title"))
        self.assertIsNotNone(pmap)
        d2p = pmap["deck_to_pptx"]
        self.assertEqual(d2p[0], 1)
        self.assertEqual(d2p, sorted(set(d2p)))                                     # 単調増加
        inserted = [k for k, m in enumerate(pmap["pptx_to_deck"]) if m is None]     # 凡例ページなど、deck.json に無いページ
        self.assertEqual(len(pmap["pptx_to_deck"]) - len(inserted), len(d2p))
        for k, n in enumerate(d2p):
            self.assertEqual(pmap["pptx_to_deck"][n - 1][0], k + 1)


class CheckPatternTest(unittest.TestCase):
    def test_structure_errors(self):
        bad = {"name": "b", "slots": {"a": {"kind": "weird"}, "r": {"kind": "records"}, "l": {"kind": "list"}},
               "elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "if": "ghost", "text": {"paragraphs": [{"runs": [{"text": "{{missing}}"}]}]}},
                            {"repeat": "a", "grid": {}, "template": []},
                            {"x": 0, "y": 0, "w": 1, "h": 1, "fit": {"sizes": []}}]}
        errs, _ = pe.check_pattern(bad, THEME)
        text = "\n".join(errs)
        for needle in ("kind 'weird'", "fields が必要", "if 'ghost'", "{{missing}}", "repeat 'a'", "fit は"):
            self.assertIn(needle, text)
        self.assertTrue(pe.check_pattern({"name": "x"}, THEME)[0])
        self.assertTrue(pe.check_pattern([], THEME)[0])

    def test_warns_unused_slot(self):
        errs, warns = pe.check_pattern({"name": "u", "slots": {"a": {}, "b": {}}, "elements": [box([{"runs": [run("{{a}}")]}])]}, THEME)
        self.assertEqual(errs, [])
        self.assertTrue(any("'b'" in w for w in warns))

    def test_expanded_canvas_problems_are_errors(self):
        errs, _ = pe.check_pattern({"name": "c", "slots": {"a": {}}, "elements": [{"x": 0, "y": 0, "w": "wide", "h": 1}]}, THEME)
        self.assertTrue(any("w" in e for e in errs))

    def test_bundled_patterns_are_clean_in_both_themes(self):
        for theme_name in ("default", "acn-slide-master"):
            theme = pe._load_theme_for_cli(theme_name)
            for f in sorted((ROOT / "templates" / "patterns").glob("*.json")):
                pat_ = pe._read_pattern_file(f)
                errs, warns = pe.check_pattern(pat_, theme)
                self.assertEqual(errs, [], f"{f.name} / {theme_name}")
                self.assertEqual(warns, [], f"{f.name} / {theme_name}")


class RenderTest(unittest.TestCase):
    """展開結果が HTML / PPTX の両方で描けること"""

    def test_bundled_patterns_render_html_and_pptx(self):
        from pptx import Presentation
        for theme_name in ("default", "acn-slide-master"):
            theme = pe._load_theme_for_cli(theme_name)
            for f in sorted((ROOT / "templates" / "patterns").glob("*.json")):
                pat_ = pe._read_pattern_file(f)
                sl = pe.example_slide(pat_)
                canvas = pe.to_canvas_slide(sl, pat_, theme, {"meta": {"title": "T"}}, 2, 5, None, [])
                self.assertEqual(canvas["type"], "canvas")
                probs = ce.validate_canvas_problems(canvas)
                self.assertEqual(probs, [], f.name)
                html = ce.canvas_html(canvas)
                if pe.frame_of(pat_) == "full":      # frame:"body" の型はフッター（ページ番号）をプラグインの見出し骨格が描く
                    self.assertIn("2 / 5", html)
                prs = Presentation()
                ce.add_canvas_to_pptx(prs.slides.add_slide(prs.slide_layouts[6]), canvas["elements"])
                # テーマの色に追随する（primary が展開結果に含まれる）
                self.assertIn(theme["colors"]["primary"].upper(), json.dumps(canvas).upper(), f.name)

    def test_conclusion_evidence_adapts_to_item_count(self):
        pat_ = pe.load_pattern("conclusion-evidence")
        heights = {}
        for n in (2, 3, 4):
            els, _ = pe.expand(pe.example_slide(pat_, n), pat_, THEME, None, 1, 1)
            faces = [e for e in els if e.get("name", "").endswith("の面") and e["name"].startswith("根拠")]
            self.assertEqual(len(faces), n)
            heights[n] = faces[0]["h"]
        self.assertGreater(heights[2], heights[3])
        self.assertGreater(heights[3], heights[4])


class CliTest(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([PY, str(TOOLS / "pattern_engine.py"), *args], capture_output=True, text=True, encoding="utf-8")

    def test_list_show_check(self):
        r = self.cli("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        for n in ("conclusion-evidence", "before-after", "pillars"):
            self.assertIn(n, r.stdout)
        r = self.cli("show", "pillars")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"pattern": "pillars"', r.stdout)
        self.assertIn("foundation", r.stdout)
        self.assertNotEqual(self.cli("show", "no-such").returncode, 0)
        r = self.cli("check", str(ROOT / "templates" / "patterns" / "pillars.json"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bad.json"
            f.write_text(json.dumps({"name": "bad", "slots": {"a": {}}, "elements": [{"x": 0, "y": 0, "w": 1, "h": 1, "fill": "zzz"}]}), encoding="utf-8")
            r = self.cli("check", str(f))
            self.assertEqual(r.returncode, 1)
            self.assertIn("zzz", r.stdout)


# ---------------------------------------------------------------- pattern_from_pptx
import pattern_from_pptx as pfp  # noqa: E402


class FromPptxTest(unittest.TestCase):
    def make_pptx(self, d):
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.util import Emu, Pt
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
        s = prs.slides.add_slide(prs.slide_layouts[6])

        def tb(x, y, w, h, text, size, bold=False, color=None):
            t = s.shapes.add_textbox(Emu(x * 9525), Emu(y * 9525), Emu(w * 9525), Emu(h * 9525))
            t.text_frame.text = text
            r = t.text_frame.paragraphs[0].runs[0]
            r.font.size = Pt(size * 0.75)
            r.font.bold = bold
            if color:
                r.font.color.rgb = RGBColor.from_string(color)
            return t
        tb(72, 40, 1000, 60, "結論を先に述べる見出し", 36, True, "0F3D6E")
        for k in range(3):
            card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu((72 + k * 380) * 9525), Emu(200 * 9525), Emu(360 * 9525), Emu(300 * 9525))
            card.fill.solid()
            card.fill.fore_color.rgb = RGBColor(0xE0, 0xE7, 0xF0)
            card.line.color.rgb = RGBColor(0xBC, 0xC8, 0xD8)
            tb(90 + k * 380, 220, 320, 40, f"カード{k + 1}", 24, True, "0F3D6E")
        odd = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(72 * 9525), Emu(540 * 9525), Emu(200 * 9525), Emu(30 * 9525))
        odd.fill.solid()
        odd.fill.fore_color.rgb = RGBColor(0xFF, 0x00, 0xAA)        # テーマのどの色とも遠い色
        tb(1088, 678, 120, 24, "4 / 34", 13, False, "5A6B85")
        src = Path(d) / "src.pptx"
        prs.save(str(src))
        return src

    def test_snap_color(self):
        cols = THEME["colors"]
        self.assertEqual(pfp.snap_color("#0F3D6E", cols, "fill"), "primary")
        self.assertEqual(pfp.snap_color("#0F3D6E", cols, "text"), "heading_text")     # 同じ色は用途別の優先順
        self.assertEqual(pfp.snap_color("#FFFFFF", cols, "fill"), "background")
        self.assertEqual(pfp.snap_color("#FFFFFF", cols, "text"), "on_primary")
        self.assertEqual(pfp.snap_color("#0F3E6F", cols, "fill"), "primary")          # 僅差は寄せる
        self.assertIsNone(pfp.snap_color("#FF00AA", cols, "fill"))                    # 遠い色は寄せない
        self.assertIsNone(pfp.snap_color("primary", cols, "fill"))

    def test_end_to_end_from_pptx(self):
        import pptx_import as pi
        with tempfile.TemporaryDirectory() as d:
            src = self.make_pptx(d)
            sl = pi.Importer(src, tag=True).convert({1})[0]
            pat_, rep = pfp.build_pattern(sl, "demo", THEME, "default", False, None, "src.pptx の 1 枚目")
            self.assertEqual(pat_["background"], "background")
            # 見出しは最大サイズの文字 → title、ページ番号は {{page}} / {{total}} に戻る
            self.assertIn("title", pat_["slots"])
            self.assertTrue(pat_["slots"]["title"]["required"])
            self.assertEqual(pat_["slots"]["title"]["example"], "結論を先に述べる見出し")
            self.assertEqual(pat_["slots"]["title"]["max_chars"], 16)
            flat = json.dumps(pat_, ensure_ascii=False)
            self.assertIn("{{page}} / {{total}}", flat)
            self.assertNotIn("4 / 34", flat)
            # 色はトークンに（寄せ切れない 1 色だけ hex のまま、一覧に出る）
            self.assertIn("#FF00AA", rep["unsnapped"])                                   # 寄せ切れない色は報告に出る
            self.assertNotIn("#0F3D6E", rep["unsnapped"])
            self.assertTrue(any(e.get("fill") == "surface" for e in pat_["elements"]))
            # 同じ形が等間隔に 3 つ → repeat 候補
            self.assertTrue(any("3 個" in desc for desc, _ in rep["repeat"]))
            # 検証を通り、別の文言・別テーマで展開できる
            errs, warns = pe.check_pattern(pat_, THEME)
            self.assertEqual(errs, [])
            slots = {"title": "別の見出し", "text1": "A", "text2": "B", "text3": "C"}
            els, bg = pe.expand({"slots": slots}, pat_, pe._load_theme_for_cli("acn-slide-master"), {"meta": {}}, 7, 9)
            blob = json.dumps(els, ensure_ascii=False)
            self.assertIn("別の見出し", blob)
            self.assertIn("7 / 9", blob)
            self.assertIn("#460073", blob.upper())          # acn-slide-master の primary（見出し色）に追随
            self.assertEqual(ce.validate_canvas_problems({"elements": els}), [])

    def test_cli_from_pptx_writes_pattern_and_check_deck_and_requires_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            src = self.make_pptx(d)
            out = Path(d) / "pats"
            cmd = [PY, str(TOOLS / "pattern_from_pptx.py"), str(src), "--slide", "1", "--name", "demo", "--theme", "default", "--dir", str(out)]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((out / "demo.json").is_file())
            deck = json.loads((out / "_check" / "demo" / "deck.json").read_text(encoding="utf-8"))
            self.assertEqual(len(deck["slides"]), 3)
            self.assertIn("#FF00AA", r.stdout)                  # 寄せ切れない色の報告
            self.assertIn("繰り返し", r.stdout)
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("--confirm", r.stderr)
            r = subprocess.run(cmd + ["--confirm"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run(cmd[:-6] + ["--slide", "9", "--name", "x", "--dir", str(out)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("範囲外", r.stderr)

    def test_bullets_become_list_slot_with_repeat(self):
        from pptx import Presentation
        from pptx.util import Emu
        import pptx_import as pi
        with tempfile.TemporaryDirectory() as d:
            prs = Presentation()
            prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
            s = prs.slides.add_slide(prs.slide_layouts[6])
            sl_ = {"type": "canvas", "background": "#FFFFFF", "elements": [
                {"x": 10, "y": 10, "w": 500, "h": 200, "text": {"paragraphs": [
                    {"bullet": {"char": "•"}, "marL": 20, "indent": -20, "runs": [{"text": "一つ目", "size": 20, "color": "#1A2233"}]},
                    {"bullet": {"char": "•"}, "marL": 20, "indent": -20, "runs": [{"text": "二つ目", "size": 20, "color": "#1A2233"}]}]}}]}
            pat_, rep = pfp.build_pattern(sl_, "b", THEME, "default")
            self.assertEqual(pat_["slots"]["items"]["kind"], "list")
            self.assertEqual(pat_["slots"]["items"]["example"], ["一つ目", "二つ目"])
            para = pat_["elements"][0]["text"]["paragraphs"][0]
            self.assertEqual((para["repeat"], para["runs"][0]["text"]), ("items", "{{.}}"))
            els, _ = pe.expand({"slots": {"items": ["a", "b", "c"]}}, pat_, THEME)
            self.assertEqual(len(els[0]["text"]["paragraphs"]), 3)

    def test_picture_placeholder_becomes_image_slot(self):
        sl_ = {"type": "canvas", "background": "#FFFFFF", "elements": [
            {"kind": "placeholder", "x": 10, "y": 10, "w": 300, "h": 200, "label": "画像（スクリーンショット）"}]}
        pat_, _ = pfp.build_pattern(sl_, "p", THEME, "default")
        self.assertEqual(pat_["slots"]["image"]["kind"], "image")
        none, _ = pe.expand({"slots": {}}, pat_, THEME)
        self.assertEqual([e["kind"] for e in none], ["placeholder"])      # 画像が無いときは枠のまま
        some, _ = pe.expand({"slots": {"image": "assets/a.png"}}, pat_, THEME)
        self.assertEqual([(e["kind"], e["path"]) for e in some], [("image", "assets/a.png")])

    def test_master_shapes_are_separated(self):
        sl_ = {"type": "canvas", "background": "#FFFFFF", "elements": [
            {"x": 0, "y": 0, "w": 100, "h": 10, "fill": "#0F3D6E", "src": "master", "name": "ロゴ帯"},
            {"x": 0, "y": 20, "w": 100, "h": 10, "fill": "#0F3D6E", "src": "slide"}]}
        pat_, rep = pfp.build_pattern(sl_, "m", THEME, "default")
        self.assertEqual(len(pat_["elements"]), 1)
        self.assertEqual(rep["master_dropped"], ["ロゴ帯"])
        pat_, _ = pfp.build_pattern(sl_, "m", THEME, "default", keep_master=True)
        self.assertEqual(len(pat_["elements"]), 2)


if __name__ == "__main__":
    unittest.main()

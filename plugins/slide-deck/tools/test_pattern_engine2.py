#!/usr/bin/env python3
"""パターンエンジンの強化（PE）のテスト: グループ fit・値の分岐と候補・max の打ち切り・min_width / narrow・影・show / list・同梱画像・壊れた入力。

    python -m unittest tools/test_pattern_engine2.py
"""
import copy
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

PY = sys.executable
ROOT = TOOLS.parent
THEME = pe._default_theme()


def cell_text(size_marker=True, **kw):
    """枠の中の 1 行テキスト（fit つき）。"""
    return {"x": 0, "y": 0, "w": 300, "h": 60, "name": "文", "text": {"insets": [0, 0, 0, 0], "anchor": "ctr", "paragraphs": [
        {"lineHeight": 1.0, "runs": [{"text": "{{.}}", "size": "@fit", "color": "text"}]}]}, **kw}


def sizes_of(els):
    return [e["text"]["paragraphs"][0]["runs"][0]["size"] for e in els if e.get("text")]


def expand_list(items, fit, theme=THEME, tpl_extra=None, slot_extra=None, cols=3):
    pat = {"name": "g", "slots": {"c": dict({"kind": "list", "max": 6}, **(slot_extra or {}))},
           "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 900, "h": 80, "cols": cols, "gap": 10},
                         "template": [dict(cell_text(), fit=fit, **(tpl_extra or {}))]}]}
    warns, errs = [], []
    els, _ = pe.expand({"slots": {"c": items}}, pat, theme, None, 1, 1, warns.append, errs)
    return els, warns, errs


class GroupFitTest(unittest.TestCase):
    SIZES = [30, 26, 22, 18, 14]

    def test_without_group_each_item_gets_its_own_size(self):
        els, _w, _e = expand_list(["短い", "これはかなり長い文章でひと目では読み切れないくらいの長さがある"], {"sizes": self.SIZES})
        s = sizes_of(els)
        self.assertGreater(s[0], s[1])

    def test_group_gives_everyone_the_smallest_fitting_size(self):
        long_ = "これはかなり長い文章でひと目では読み切れないくらいの長さがある"
        a, _w, _e = expand_list(["短い", long_], {"sizes": self.SIZES, "group": "g1"})
        b, _w, _e = expand_list(["短い", "短い"], {"sizes": self.SIZES, "group": "g1"})
        s_a, s_b = sizes_of(a), sizes_of(b)
        self.assertEqual(s_a[0], s_a[1])
        self.assertEqual(s_b[0], s_b[1])
        self.assertGreater(s_b[0], s_a[0])           # 全員が短ければ大きく、1 つだけ長ければ全員がそれに合わせる
        self.assertEqual(s_b[0], 30)

    def test_group_true_means_same_template_position_in_a_repeat(self):
        long_ = "これはかなり長い文章でひと目では読み切れないくらいの長さがある"
        els, _w, _e = expand_list(["短い", long_, "短い"], {"sizes": self.SIZES, "group": True})
        s = sizes_of(els)
        self.assertEqual(len(set(s)), 1)
        self.assertLess(s[0], 30)

    def test_group_false_is_the_same_as_no_group(self):
        long_ = "これはかなり長い文章でひと目では読み切れないくらいの長さがある"
        a, _w, _e = expand_list(["短い", long_], {"sizes": self.SIZES, "group": False})
        b, _w, _e = expand_list(["短い", long_], {"sizes": self.SIZES})
        self.assertEqual(sizes_of(a), sizes_of(b))

    def test_different_groups_are_independent(self):
        pat = {"name": "g", "slots": {"a": {"kind": "text"}, "b": {"kind": "text"}}, "elements": [
            dict(cell_text(), text={"insets": [0, 0, 0, 0], "paragraphs": [{"lineHeight": 1.0, "runs": [{"text": "{{a}}", "size": "@fit"}]}]},
                 fit={"sizes": self.SIZES, "group": "x"}),
            dict(cell_text(), y=100, text={"insets": [0, 0, 0, 0], "paragraphs": [{"lineHeight": 1.0, "runs": [{"text": "{{b}}", "size": "@fit"}]}]},
                 fit={"sizes": self.SIZES, "group": "y"})]}
        els, _ = pe.expand({"slots": {"a": "短い", "b": "これはかなり長い文章でひと目では読み切れないくらいの長さがある"}}, pat, THEME, None, 1, 1, lambda m: None, [])
        s = sizes_of(els)
        self.assertGreater(s[0], s[1])

    def test_tokens_in_sizes(self):
        els, _w, errs = expand_list(["短い", "短い"], {"sizes": ["$type.h2", "$type.h3", 16], "group": True})
        self.assertEqual(errs, [])
        self.assertEqual(sizes_of(els), [28, 28])
        els, _w, errs = expand_list(["短い"], {"sizes": ["$type.nope", 20]})
        self.assertTrue(any("$type.nope" in e for e in errs))

    def test_group_warns_once_and_names_the_worst_item(self):
        huge = "とても長い文章" * 30
        els, warns, _e = expand_list(["短い", huge, huge + "さらに", "短い"], {"sizes": [20, 14], "group": "z"}, cols=2)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("最小サイズ 14px", warns[0])
        self.assertIn("3 個目", warns[0])             # いちばん溢れる項目
        self.assertIn("同じグループ 4 個のうち 2 個", warns[0])
        self.assertEqual(set(sizes_of(els)), {14})

    def test_group_with_marker_less_text_scales_by_ratio(self):
        pat = {"name": "g", "slots": {"c": {"kind": "list", "max": 4}}, "elements": [
            {"repeat": "c", "grid": {"x": 0, "y": 0, "w": 800, "h": 60, "cols": "row", "gap": 10},
             "template": [{"x": 0, "y": 0, "w": 190, "h": 60, "fit": {"sizes": [30, 20], "group": True},
                           "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"lineHeight": 1.0, "runs": [{"text": "{{.}}", "size": 30}]}]}}]}]}
        els, _ = pe.expand({"slots": {"c": ["あ", "い" * 12]}}, pat, THEME, None, 1, 1, lambda m: None, [])
        s = sizes_of(els)
        self.assertEqual(s[0], s[1])

    def test_group_lineheight_is_recomputed(self):
        long_ = "これはかなり長い文章でひと目では読み切れないくらいの長さがある"
        els, _w, _e = expand_list(["短い", long_], {"sizes": self.SIZES, "group": True})
        for e in els:
            p = e["text"]["paragraphs"][0]
            self.assertAlmostEqual(p["lineHeightPx"], p["runs"][0]["size"] * ce.LINE_HEIGHT * 1.0, places=1)

    def test_check_pattern_validates_group_value(self):
        p = {"name": "g", "slots": {"c": {"kind": "list", "max": 3, "example": ["a"]}},
             "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 900, "h": 80, "cols": 3},
                           "template": [dict(cell_text(), fit={"sizes": [20, 16], "group": 5})]}]}
        errs, _ = pe.check_pattern(p, THEME)
        self.assertTrue(any("fit.group" in e for e in errs))
        p["elements"][0]["template"][0]["fit"]["group"] = True
        errs, warns = pe.check_pattern(p, THEME)
        self.assertEqual(errs, [])


class ConditionTest(unittest.TestCase):
    P = {"name": "t", "slots": {
        "items": {"kind": "records", "min": 1, "max": 5, "fields": {
            "t": {"kind": "text"},
            "state": {"kind": "text", "values": {"done": ["済", "完了", "done", "true"], "wip": ["中", "wip"], "todo": ["", "未", "todo"]}},
            "now": {"kind": "flag"}, "vals": {"kind": "list", "count_of": "opts"}}},
        "opts": {"kind": "list", "min": 2, "max": 4},
        "mode": {"kind": "text", "values": {"a": ["エー"], "b": ["ビー"]}}},
        "elements": [{"repeat": "items", "grid": {"x": 0, "y": 0, "w": 800, "h": 400, "cols": 1, "gap": 4}, "template": [
            {"name": "done", "x": 0, "y": 0, "w": 10, "h": 10, "fill": "primary", "if": {"slot": "state", "is": "done"}},
            {"name": "notdone", "x": 20, "y": 0, "w": 10, "h": 10, "fill": "accent", "if": {"not": {"slot": "state", "is": "done"}}},
            {"name": "active", "x": 40, "y": 0, "w": 10, "h": 10, "fill": "muted", "if": {"slot": "state", "in": ["wip", "todo"]}},
            {"name": "now", "x": 60, "y": 0, "w": 10, "h": 10, "fill": "border", "if": "now"},
            {"name": "txt", "x": 80, "y": 0, "w": 200, "h": 20, "text": {"insets": [0, 0, 0, 0], "paragraphs": [
                {"runs": [{"text": "{{vals.2}}|{{now}}", "size": 14, "color": "text"}], "keep": True}]}}]}]}

    def render(self, items, **extra):
        warns, errs = [], []
        slots = {"items": items, "opts": ["A", "B"], **extra}
        els, _ = pe.expand({"slots": slots}, self.P, THEME, None, 1, 1, warns.append, errs)
        return els, warns, errs

    def names_per_row(self, items):
        els, _w, _e = self.render(items)
        rows = {}
        for e in els:
            rows.setdefault(e["y"], []).append(e["name"])
        return [rows[y] for y in sorted(rows)]

    def test_is_in_not_with_aliases(self):
        rows = self.names_per_row([{"t": "a", "state": "完了"}, {"t": "b", "state": "中"}, {"t": "c", "state": ""}, {"t": "d", "state": "TODO"},
                                   {"t": "e", "state": "ＤＯＮＥ"}])
        self.assertEqual(rows[0][:1], ["done"])
        self.assertNotIn("notdone", rows[0])
        self.assertIn("notdone", rows[1])
        self.assertIn("active", rows[1])
        self.assertIn("active", rows[2])         # 空 = todo
        self.assertIn("active", rows[3])         # 大文字小文字を区別しない
        self.assertEqual(rows[4][0], "done")     # 全角半角をそろえる

    def test_done_string_false_is_not_done_but_true_is(self):
        rows = self.names_per_row([{"t": "a", "state": "true"}, {"t": "b", "state": "false"}])
        self.assertEqual(rows[0][0], "done")
        self.assertNotEqual(rows[1][0], "done")     # "false" は完了にならない（候補外 = どの状態でもない）

    def test_unknown_value_warns_with_candidates(self):
        errs, warns = pe.slot_problems({"slots": {"items": [{"t": "a", "state": "しばらく後"}], "opts": ["A", "B"]}}, self.P)
        self.assertEqual(errs, [])
        text = "\n".join(warns)
        self.assertIn("しばらく後", text)
        for k in ("done", "wip", "todo"):
            self.assertIn(k, text)
        self.assertIn("済", text)                          # 別名の例も出す

    def test_known_aliases_do_not_warn(self):
        _e, warns = pe.slot_problems({"slots": {"items": [{"t": "a", "state": "完了"}, {"t": "b", "state": ""}, {"t": "c"}], "opts": ["A", "B"]}}, self.P)
        self.assertEqual([w for w in warns if "候補" in w], [])

    def test_flag_values(self):
        for v, want in ((True, True), (False, False), ("false", False), ("no", False), ("0", False), (0, False), ("×", False), ("", False),
                        (None, False), ("true", True), ("○", True), ("現在地", True), (1, True)):
            self.assertEqual(pe._as_flag(v), want, repr(v))
        els, _w, _e = self.render([{"t": "a", "state": "済", "now": "false"}, {"t": "b", "state": "済", "now": True}])
        ys = sorted({e["y"] for e in els})
        now_rows = [e["y"] for e in els if e["name"] == "now"]
        self.assertEqual(len(now_rows), 1)
        self.assertEqual(now_rows[0], ys[1])

    def test_flag_is_never_printed_as_text(self):
        els, _w, _e = self.render([{"t": "a", "state": "済", "now": True, "vals": ["x", "y"]}])
        txt = [e for e in els if e["name"] == "txt"][0]
        self.assertEqual(txt["text"]["paragraphs"][0]["runs"][0]["text"], "y|")       # true という札にならない

    def test_list_field_index_is_one_based_and_missing_is_empty(self):
        els, _w, errs = self.render([{"t": "a", "state": "済", "vals": ["p", "q"]}, {"t": "b", "state": "済", "vals": ["p"]}, {"t": "c", "state": "済"}])
        self.assertEqual(errs, [])
        got = [e["text"]["paragraphs"][0]["runs"][0]["text"] for e in els if e["name"] == "txt"]
        self.assertEqual(got, ["q|", "|", "|"])
        self.assertIs(pe._lookup({"v": ["a"]}, "v.0"), pe._MISSING)

    def test_count_of_warns_when_value_count_differs(self):
        _e, warns = pe.slot_problems({"slots": {"items": [{"t": "a", "vals": ["p", "q"]}, {"t": "b", "vals": ["p"]}], "opts": ["A", "B"]}}, self.P)
        hit = [w for w in warns if "'vals'" in w]
        self.assertEqual(len(hit), 1)
        self.assertIn("2 個目", hit[0])
        self.assertIn("合っていません", hit[0])

    def test_check_pattern_reports_bad_conditions(self):
        base = lambda cond: {"name": "t", "slots": {"s": {"kind": "text", "values": {"a": [], "b": []}, "example": "a"}},
                             "elements": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "primary", "if": cond}]}
        for bad in ({"slot": "s"}, {"slot": "s", "is": "a", "in": ["a"]}, {"is": "a"}, {"slot": "zz", "is": "a"}, {"slot": "s", "in": []},
                    {"slot": "s", "isnt": "a"}, {"not": {"slot": "s", "is": "a"}, "slot": "s"}):
            errs, _ = pe.check_pattern(base(bad), THEME)
            self.assertTrue(errs, bad)
        errs, warns = pe.check_pattern(base({"slot": "s", "is": "a"}), THEME)
        self.assertEqual((errs, warns), ([], []))
        _e, warns = pe.check_pattern(base({"slot": "s", "is": "zzz"}), THEME)
        self.assertTrue(any("候補にありません" in w for w in warns))
        errs, warns = pe.check_pattern(base({"not": {"slot": "s", "in": ["a", "b"]}}), THEME)
        self.assertEqual((errs, warns), ([], []))

    def test_check_pattern_reports_bad_values_definitions(self):
        base = lambda sd: {"name": "t", "slots": {"s": dict({"kind": "text", "example": "a"}, **sd)}, "elements": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "primary", "if": "s"}]}
        for bad in ({"values": ["a"]}, {"values": {"a": "x"}}, {"values": {}}, {"kind": "list", "values": {"a": []}}, {"count_of": "nope"}, {"count_of": "s"}):
            errs, _ = pe.check_pattern(base(bad), THEME)
            self.assertTrue(errs, bad)

    def test_old_if_forms_still_work(self):
        p = {"name": "t", "slots": {"a": {"kind": "text"}, "b": {"kind": "text"}}, "elements": [
            {"name": "x1", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary", "if": "a"},
            {"name": "x2", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary", "if": "!a"},
            {"name": "x3", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary", "if": ["a", "!b"]}]}
        els, _ = pe.expand({"slots": {"a": "v"}}, p, THEME, None, 1, 1, lambda m: None, [])
        self.assertEqual([e["name"] for e in els], ["x1", "x3"])


class OverMaxTest(unittest.TestCase):
    P = {"name": "m", "slots": {"c": {"kind": "list", "label": "項目", "min": 1, "max": 3}},
         "variants_by": "c", "variants": {"1": {"elements": []}, "2": {"elements": []}, "3": {"elements": [{"name": "V3", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary"}]}},
         "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 300, "h": 50, "cols": "row"},
                       "template": [{"name": "i{{index}}", "x": 0, "y": 0, "w": 50, "h": 50, "fill": "primary"}]}]}

    def test_extra_items_are_not_drawn_and_warned_once(self):
        warns, errs = [], []
        els, _ = pe.expand({"slots": {"c": list("abcdef")}}, self.P, THEME, None, 1, 1, warns.append, errs)
        self.assertEqual([e["name"] for e in els], ["i1", "i2", "i3", "V3"])      # 4 個目以降は描かない・3 個用の構図
        self.assertEqual(errs, [])
        self.assertEqual(len(warns), 1)
        self.assertIn("6 個のうち先頭の 3 個だけ描きました", warns[0])
        self.assertIn("2 枚に分けて", warns[0])

    def test_within_max_unchanged(self):
        warns = []
        els, _ = pe.expand({"slots": {"c": list("abc")}}, self.P, THEME, None, 1, 1, warns.append, [])
        self.assertEqual(len(els), 4)
        self.assertEqual(warns, [])

    def test_validate_reports_over_max_once(self):
        # validate は pattern 名で型を探すので、型を置いたデッキで確かめる
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "patterns").mkdir()
            (d / "patterns" / "m.json").write_text(json.dumps(self.P, ensure_ascii=False), encoding="utf-8")
            fails, warns = [], []
            pe.validate({"type": "pattern", "pattern": "m", "slots": {"c": list("abcd")}}, 0, d, fails.append, warns.append)
            self.assertEqual(fails, [])
            self.assertEqual(len([w for w in warns if "最大 3 個を超えています" in w]), 1)
            self.assertEqual(len(warns), 1)

    def test_blank_items_do_not_count_toward_max(self):
        warns = []
        pe.expand({"slots": {"c": ["a", " ", "b", "", "c"]}}, self.P, THEME, None, 1, 1, warns.append, [])
        self.assertEqual(warns, [])


class NarrowLevelsTest(unittest.TestCase):
    """narrow を配列にすると、幅に応じて段階的に構図が切り替わる（PN）。既存の書き方（辞書 1 つ）はそのまま動く"""

    def el(self, name, w):
        return [{"name": name, "x": 0, "y": 0, "w": w, "h": 100, "fill": "primary"}]

    def pat(self, narrow, **kw):
        base = {"name": "lv", "label": "段", "frame": "body", "size": [1136, 400], "slots": {"a": {"kind": "text", "example": "あ"}},
                "elements": self.el("wide", 1136), "narrow": narrow}
        base.update(kw)
        return base

    LEVELS = lambda self: [{"below": 1000, "size": [800, 400], "elements": self.el("mid", 800)},
                           {"below": 700, "size": [540, 400], "elements": self.el("small", 540), "min_width": 440}]

    def test_level_is_chosen_by_width_and_order_does_not_matter(self):
        p = self.pat(self.LEVELS())
        self.assertEqual([_["below"] for _ in pe.narrow_levels(p)], [700, 1000])
        for w, name in ((400, "small"), (556, "small"), (699, "small"), (700, "mid"), (741, "mid"), (999, "mid"), (1000, "wide"), (1136, "wide")):
            els = pe.pattern_block_elements({"slots": {"a": "あ"}}, p, (0, 0, w, 400), THEME)
            self.assertEqual([e["name"] for e in els], [name], w)
        self.assertEqual(pe.design_size(pe.effective_pattern(p, 556)), (540.0, 400.0))
        self.assertEqual(pe.design_size(pe.effective_pattern(p, 741)), (800.0, 400.0))
        self.assertIs(pe.effective_pattern(p, 1136), p)
        self.assertEqual(pe._below(pe.narrow_of(p)), 1000)        # narrow_of は、いちばん広い幅まで効く段

    def test_single_dict_narrow_still_works(self):
        p = self.pat({"below": 700, "size": [540, 400], "elements": self.el("small", 540)})
        self.assertEqual(len(pe.narrow_levels(p)), 1)
        self.assertEqual([e["name"] for e in pe.pattern_block_elements({"slots": {"a": "あ"}}, p, (0, 0, 556, 400), THEME)], ["small"])
        self.assertEqual([e["name"] for e in pe.pattern_block_elements({"slots": {"a": "あ"}}, p, (0, 0, 800, 400), THEME)], ["wide"])

    def test_floor_warns_with_the_alternative(self):
        p = self.pat(self.LEVELS(), block_alt="代わりに numbered-list を使う")
        self.assertEqual(pe.narrow_floor(p), 440)
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 400, "h": 400}, in_block=True)
        self.assertEqual(len([w for w in warns if "以上向き" in w]), 1)
        self.assertIn("幅 440px 以上向きです（いま 400px）", warns[0])
        self.assertIn("代わりに numbered-list を使う", warns[0])
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 556, "h": 300}, in_block=True)
        self.assertEqual(warns, [])        # 高さで縮んでも、幅が足りていれば警告しない（狭い構図の下限は矩形の幅で見る）
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 400, "h": 400})
        self.assertIn("本文領域を広げる", warns[0])

    def test_min_width_by_count(self):
        lv = self.LEVELS()
        lv[1]["min_width_by_count"] = {"4": 700}
        lv[1]["variants_by"] = "c"
        lv[1]["variants"] = {"2": {"elements": self.el("s2", 540)}, "4": {"elements": self.el("s4", 540)}}
        p = self.pat(lv, slots={"c": {"kind": "list", "min": 2, "max": 4, "example": ["a", "b"]}}, variants_by="c", variants={"2": {"elements": []}, "4": {"elements": []}})
        errs, _w = pe.check_pattern(p, THEME)
        self.assertEqual(errs, [])
        _f, w2 = pe.body_rect_problems({"slots": {"c": ["a", "b"]}}, p, {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertEqual(w2, [])
        _f, w4 = pe.body_rect_problems({"slots": {"c": ["a", "b", "c", "d"]}}, p, {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertTrue(any("幅 700px 以上向き" in w for w in w4), w4)
        _f, w4 = pe.body_rect_problems({"slots": {"c": ["a", "b", "c", "d"]}}, p, {"x": 0, "y": 0, "w": 741, "h": 400}, in_block=True)
        self.assertEqual(w4, [])

    def test_check_reports_a_broken_level(self):
        for bad in ([{"below": 700, "size": [540, 400], "elements": []}, {"below": 700, "size": [540, 400], "elements": []}],
                    [{"below": 700, "size": [540, 400], "elements": []}, {"below": "x"}],
                    [], [{"below": 700, "size": [540, 400], "elements": [], "min_width": "a"}],
                    [{"below": 700, "size": [540, 400], "elements": [], "min_width_by_count": {"x": 5}}]):
            errs, _ = pe.check_pattern(self.pat(bad), THEME)
            self.assertTrue(errs, bad)
        errs, _ = pe.check_pattern(self.pat(self.LEVELS(), block_alt=5), THEME)
        self.assertTrue(any("block_alt" in e for e in errs))
        errs, _ = pe.check_pattern(self.pat(self.LEVELS()), THEME)
        self.assertEqual(errs, [])

    def test_short_level_is_chosen_by_height(self):
        """below_h のある段は、矩形の高さがその値未満のときだけ使われる（同じ below なら高さの条件つきが先）"""
        lv = self.LEVELS() + [{"below": 700, "below_h": 340, "size": [540, 300], "elements": self.el("small-short", 540)},
                              {"below": 1000, "below_h": 340, "no_max_width": True, "size": [800, 300], "elements": self.el("mid-short", 800)}]
        p = self.pat(lv)
        self.assertEqual([(int(pe._below(x)), pe._below_h(x)) for x in pe.narrow_levels(p)], [(700, 340), (700, None), (1000, 340), (1000, None)])
        self.assertEqual([int(pe._below(x)) for x in pe.base_levels(p)], [700, 1000])
        for (w, h), name in (((556, 400), "small"), ((556, 300), "small-short"), ((556, 339), "small-short"), ((556, 340), "small"),
                             ((741, 400), "mid"), ((741, 300), "mid-short"), ((1136, 400), "wide"), ((1136, 300), "mid-short")):
            els = pe.pattern_block_elements({"slots": {"a": "あ"}}, p, (0, 0, w, h), THEME)
            self.assertEqual([e["name"] for e in els], [name], (w, h))
        self.assertIs(pe.effective_pattern(p, 1136, None), p)          # 高さが分からないときは高さの条件つきの段を選ばない
        self.assertEqual(pe.narrow_floor(p), 440)                      # 下限は幅だけの段の値
        errs, _w = pe.check_pattern(p, THEME)
        self.assertEqual(errs, [])
        short = pe.effective_pattern(p, 556, 300)
        self.assertEqual(short["min_width"], 440)                       # 短い構図は、同じ below の幅だけの段から下限を引き継ぐ

    def test_narrow_stretches_to_the_rect_width_but_keeps_circles_round(self):
        circle = {"name": "c", "x": 100, "y": 100, "w": 100, "h": 100, "geom": "ellipse", "fill": "primary"}
        lv = [{"below": 700, "size": [540, 400], "elements": self.el("bar", 540) + [circle]}]
        p = self.pat(lv)
        sl = {"slots": {"a": "あ"}}
        els = {e["name"]: e for e in pe.pattern_block_elements(sl, p, (0, 0, 640, 400), THEME)}
        self.assertAlmostEqual(els["bar"]["w"], 640, places=1)              # 540 → 640（1.185 倍。上限 1.25 倍以内）: 左右に余白が残らない
        self.assertAlmostEqual(els["bar"]["x"], 0, places=1)
        self.assertAlmostEqual(els["c"]["w"], els["c"]["h"], places=3)      # 円は円のまま
        self.assertAlmostEqual(els["c"]["x"] + els["c"]["w"] / 2, 150 * 640 / 540, places=1)     # 中心は広げた位置
        wide = {e["name"]: e for e in pe.pattern_block_elements(sl, p, (0, 0, 690, 400), THEME)}
        self.assertAlmostEqual(wide["bar"]["w"], 540 * 1.25, places=1)      # 広げる上限は 1.25 倍。余りは左右の余白
        self.assertAlmostEqual(wide["bar"]["x"], (690 - 540 * 1.25) / 2, places=1)
        short = {e["name"]: e for e in pe.pattern_block_elements(sl, p, (0, 0, 556, 300), THEME)}
        self.assertAlmostEqual(short["bar"]["h"], 75, places=1)              # 高さは文字の倍率（300/400）のまま

    def test_font_size_warning_uses_the_measured_size(self):
        """縮小率ではなく、描かれる文字の大きさ（設計の文字 × 縮小率）が 12px 未満なら警告（validate）"""
        small = {"name": "T", "x": 0, "y": 0, "w": 540, "h": 400, "fill": "accent",
                 "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{a}}", "size": 15, "color": "on_primary"}]}]}}
        p = self.pat([{"below": 700, "size": [540, 400], "elements": [small]}])
        with tempfile.TemporaryDirectory() as d:
            Path(d, "patterns").mkdir()
            Path(d, "patterns", "lv.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
            for h, expect in ((400, False), (300, True), (360, False)):
                warns = []
                sl = {"type": "pattern", "pattern": "lv", "title": "t", "slots": {"a": "あいう"}, "_block": 1}
                pe.validate(sl, 0, d, lambda m: None, warns.append, THEME, rect_w=540, rect_h=h)
                got = [w for w in warns if "文字が最小" in w]
                self.assertEqual(bool(got), expect, (h, warns))
        self.assertEqual(pe.min_text_px([small, {"name": "x", "text": {"paragraphs": [{"runs": [{"text": "1", "size": 5}]}]}}]), (15, "T"))

    def test_tag_text_has_a_lower_floor(self):
        """札・タグ・印の文字は 11px まで、それ以外は 12px まで許す（worst_small_text）"""
        def el(name, size):
            return {"name": name, "text": {"paragraphs": [{"runs": [{"text": "おすすめ", "size": size}]}]}}
        self.assertIsNone(pe.worst_small_text([el("案2の推奨タグ", 12), el("見出し", 13)], 0.95))        # 11.4px の札と 12.35px の見出し
        w = pe.worst_small_text([el("案2の推奨タグ", 12), el("説明", 12)], 0.95)
        self.assertEqual((round(w[0], 2), w[1], w[2]), (11.4, "説明", 12.0))
        w = pe.worst_small_text([el("現在地の札", 11)], 0.9)
        self.assertEqual(w[2], 11.0)

    def test_reduce_hint_only_when_it_works(self):
        """「項目を n 個までにする」は、個数を減らすと下限を満たせるときだけ書く（減らしても同じ警告が残るなら書かない）"""
        lv = [{"below": 700, "size": [540, 400], "min_width": 440, "min_width_by_count": {"5": 600, "4": 500}, "variants_by": "c",
               "elements": [], "variants": {str(n): {"elements": self.el("s%d" % n, 540)} for n in (3, 4, 5)}}]
        p = self.pat(lv, slots={"c": {"kind": "list", "min": 3, "max": 5, "example": ["a", "b", "c"]}}, variants_by="c",
                     variants={str(n): {"elements": []} for n in (3, 4, 5)})
        five = {"slots": {"c": list("abcde")}}
        _f, w = pe.body_rect_problems(five, p, {"x": 0, "y": 0, "w": 520, "h": 400}, in_block=True)
        self.assertIn("5 個のとき 幅 600px 以上向きです", w[0])
        self.assertIn("項目を 4 個までにする（4 個なら幅 500px 以上で読める）", w[0])
        _f, w = pe.body_rect_problems(five, p, {"x": 0, "y": 0, "w": 450, "h": 400}, in_block=True)
        self.assertIn("項目を 3 個までにする（3 個なら幅 440px 以上で読める）", w[0])
        _f, w = pe.body_rect_problems(five, p, {"x": 0, "y": 0, "w": 400, "h": 400}, in_block=True)
        self.assertNotIn("個までにする", w[0])            # 3 個でも 440px 未満: 減らしても直らないので提案しない
        _f, w = pe.body_rect_problems({"slots": {"c": list("abc")}}, p, {"x": 0, "y": 0, "w": 520, "h": 400}, in_block=True)
        self.assertEqual(w, [])

    def test_broken_narrow_input_never_raises(self):
        """型 JSON の narrow が壊れていても、show / list の表示部品・段の選択・check はトレースバックを出さない"""
        inf, nan = float("inf"), float("nan")
        bads = [{"below": inf}, {"below": nan}, {"below": 700, "below_h": inf}, {"below": 700, "below_h": "x"}, {"below": 700, "below_h": -1},
                {"below": 700, "min_width_by_count": [4, 700]}, {"below": 700, "min_width_by_count": {"4": "x", "y": 3}},
                {"below": 700, "min_width": "x"}, {"below": 700, "min_width": inf}, {"below": 700, "no_max_width": "yes", "below_h": 300}]
        for b in bads:
            nr = dict({"size": [540, 400], "elements": []}, **b)
            p = self.pat([nr, {"below": 1000, "size": [800, 400], "elements": []}])
            pe.check_pattern(p, THEME)
            pe.block_note(p); pe.block_class(p); pe.narrow_floor(p); pe.count_floors(p); pe.max_floor(p); pe.narrow_of(p)
            for w in (None, 0, -1, nan, inf, "x", 400, 999.9):
                pe.effective_pattern(p, w, 300)
                pe.body_rect_problems({"slots": {}}, p, {"x": 0, "y": 0, "w": w if isinstance(w, (int, float)) else 400, "h": 300}, in_block=True) if isinstance(w, (int, float)) and w > 0 and w == w and w != inf else None
        errs, _ = pe.check_pattern(self.pat([{"below": inf, "size": [540, 400], "elements": []}]), THEME)
        self.assertTrue(errs)
        errs, _ = pe.check_pattern(self.pat([{"below": 700, "below_h": inf, "size": [540, 400], "elements": []}]), THEME)
        self.assertTrue(errs)

    def test_phrase_lines_does_not_trust_an_exact_fit(self):
        """枠の幅にちょうど収まる 1 行（幅の 100%）は 1 行と決めず、折る（描画側が 1 文字だけ折り返す「必／要」を防ぐ）"""
        from ja_text import _width
        text = "新しい顧客を開拓する施策"
        w = _width(text, 20, None, False)
        lines = pe._phrase_lines(text, 20, w, None, False)
        self.assertGreaterEqual(len(lines), 2)
        self.assertTrue(all(len(x) >= 3 for x in lines), lines)
        self.assertEqual(pe._phrase_lines(text, 20, w + 12, None, False), [text])         # 余裕があれば 1 行

    def test_fit_avoids_a_two_character_last_line_by_one_size_down(self):
        """最終行が 1〜2 文字になる大きさは避け、少し小さい大きさで 1 行に収める（収まる大きさが無いときは大きいほうのまま）"""
        el = {"name": "t", "x": 0, "y": 0, "w": 180, "h": 80, "text": {"insets": [0, 0, 0, 0], "anchor": "ctr", "paragraphs": [
            {"runs": [{"text": "初期費用は年間", "size": 28, "color": "text"}]}]}, "fit": {"sizes": [28, 26, 24, 22, 20]}}
        p = {"name": "o", "label": "o", "frame": "body", "size": [400, 100], "slots": {}, "elements": [el]}
        warns = []
        els, _ = pe.expand({"slots": {}}, p, THEME, None, 1, 1, warns.append, [])
        run = els[0]["text"]["paragraphs"][0]["runs"]
        self.assertFalse(any(r.get("br") for r in run), run)            # 1 行（「初期費用は／年間」にならない）
        self.assertLess(run[0]["size"], 28)
        self.assertEqual(warns, [])

    def test_check_expands_every_level(self):
        lv = self.LEVELS()
        lv[0]["elements"] = [{"name": "bad", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "nocolor"}]
        errs, _ = pe.check_pattern(self.pat(lv), THEME)
        self.assertTrue(any("nocolor" in e and "狭い構図" in e for e in errs), errs)


class MinWidthNarrowTest(unittest.TestCase):
    def pat(self, **kw):
        base = {"name": "wide", "label": "幅広", "frame": "body", "size": [1000, 300], "slots": {"a": {"kind": "text", "example": "本文"}},
                "elements": [{"name": "W", "x": 0, "y": 0, "w": 1000, "h": 300, "fill": "primary",
                              "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{a}}", "size": 40, "color": "on_primary"}]}]}}]}
        base.update(kw)
        return base

    def test_min_width_warns_when_narrower(self):
        p = self.pat(min_width=900)
        fails, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertEqual(fails, [])
        mine = [w for w in warns if "幅 900px 以上向き" in w]
        self.assertEqual(len(mine), 1)
        self.assertIn("この型（wide）は幅 900px 以上向きです（いま 556px）", mine[0])
        self.assertIn("ブロックを広げる", mine[0])
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 1000, "h": 400}, in_block=True)
        self.assertEqual(warns, [])
        _f, warns = pe.body_rect_problems({}, self.pat(), {"x": 0, "y": 0, "w": 800, "h": 400}, in_block=True)
        self.assertEqual(warns, [])          # min_width が無い型は今までどおり

    def test_min_width_uses_the_width_after_scaling(self):
        p = self.pat(min_width=900)
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 1200, "h": 200}, in_block=False)    # 高さで縮む: 1000 * (200/300) = 667px
        self.assertTrue(any("いま 666px" in w or "いま 667px" in w for w in warns), warns)

    NARROW = {"below": 700, "size": [520, 400], "elements": [
        {"name": "N", "x": 0, "y": 0, "w": 520, "h": 400, "fill": "accent",
         "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{a}}", "size": 24, "color": "on_primary"}]}]}}]}

    def test_narrow_construction_is_used_below_the_width(self):
        p = self.pat(narrow=self.NARROW)
        sl = {"slots": {"a": "あ"}}
        wide = pe.pattern_block_elements(sl, p, (0, 0, 1000, 300), THEME)
        self.assertEqual([e["name"] for e in wide], ["W"])
        half = pe.pattern_block_elements(sl, p, (0, 0, 556, 400), THEME)
        self.assertEqual([e["name"] for e in half], ["N"])
        self.assertAlmostEqual(half[0]["w"], 556, places=1)      # 縮まず、矩形の幅いっぱいまで横に広がる（狭い構図）
        self.assertEqual(pe.design_size(pe.effective_pattern(p, 556)), (520.0, 400.0))
        self.assertIs(pe.effective_pattern(p, 900), p)
        self.assertIs(pe.effective_pattern(p, None), p)

    def test_narrow_changes_the_scale_check(self):
        p = self.pat(narrow=self.NARROW)
        _f, warns = pe.body_rect_problems({}, p, {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertEqual(warns, [])        # 広い構図のままなら 0.55 倍に縮む警告になるところ、狭い構図(520x400)なので警告なし
        _f, warns = pe.body_rect_problems({}, self.pat(), {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertEqual(len(warns), 1)

    def test_narrow_variants_and_check_pattern(self):
        p = self.pat(slots={"c": {"kind": "list", "min": 1, "max": 2, "example": ["a", "b"]}}, variants_by="c",
                     variants={"1": {"elements": []}, "2": {"elements": []}},
                     narrow={"below": 700, "size": [520, 400], "elements": [], "variants": {"1": {"elements": [{"name": "n1", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary"}]},
                                                                                         "2": {"elements": [{"name": "n2", "x": 0, "y": 0, "w": 5, "h": 5, "fill": "primary"}]}}})
        p["elements"] = []
        errs, _w = pe.check_pattern(p, THEME)
        self.assertEqual(errs, [])
        sl = {"slots": {"c": ["x", "y"]}}
        names = [e["name"] for e in pe.pattern_block_elements(sl, p, (0, 0, 520, 400), THEME)]
        self.assertEqual(names, ["n2"])

    def test_narrow_with_a_mistake_is_reported_by_check(self):
        p = self.pat(narrow={"below": 700, "size": [520, 400], "elements": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "nocolor"}]})
        errs, _ = pe.check_pattern(p, THEME)
        self.assertTrue(any("nocolor" in e and "狭い構図" in e for e in errs))
        for bad in ({"below": "x", "elements": []}, {"below": 700}, {"below": 700, "size": [1], "elements": []}):
            errs, _ = pe.check_pattern(self.pat(narrow=bad), THEME)
            self.assertTrue(errs, bad)
        errs, _ = pe.check_pattern(self.pat(min_width="900"), THEME)
        self.assertTrue(any("min_width" in e for e in errs))

    def test_validate_uses_narrow_when_rect_w_is_given(self):
        p = self.pat(narrow=self.NARROW)
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "patterns").mkdir()
            (d / "patterns" / "wide.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
            fails, warns = [], []
            pe.validate({"type": "pattern", "pattern": "wide", "title": "t", "slots": {"a": "あ"}}, 0, d, fails.append, warns.append, None, rect_w=500)
            self.assertEqual((fails, warns), ([], []))


class ShadowTokenTest(unittest.TestCase):
    def render(self, tokens):
        theme = dict(THEME, tokens=tokens)
        p = {"name": "s", "slots": {"a": {"kind": "text"}}, "elements": [{"x": 0, "y": 0, "w": 100, "h": 50, "fill": "surface", "shadow": "$shadow.card"}]}
        errs = []
        els, _ = pe.expand({"slots": {}}, p, theme, None, 1, 1, lambda m: None, errs)
        return els[0], errs

    def test_classic_has_no_shadow_soft_has(self):
        e, errs = self.render({"shadow": {"card": "none"}})
        self.assertEqual(errs, [])
        self.assertNotIn("shadow", e)
        e, errs = self.render({"shadow": {"card": "soft", "dy": 6, "blur": 20, "alpha": 0.2}})
        self.assertEqual(errs, [])
        self.assertEqual((e["shadow"]["dy"], e["shadow"]["blur"]), (6, 20))
        self.assertEqual(e["shadow"]["color"]["alpha"], 0.2)
        self.assertEqual(ce.validate_canvas_problems({"elements": [e]}), [])

    def test_dict_shadow_is_passed_through_and_bad_token_is_an_error(self):
        p = {"name": "s", "slots": {"a": {"kind": "text"}}, "elements": [
            {"x": 0, "y": 0, "w": 10, "h": 10, "fill": "surface", "shadow": {"dx": 0, "dy": 3, "blur": 8, "color": "#000000"}},
            {"x": 0, "y": 0, "w": 10, "h": 10, "fill": "surface", "shadow": "$shadow.zzz"}]}
        errs = []
        els, _ = pe.expand({"slots": {}}, p, THEME, None, 1, 1, lambda m: None, errs)
        self.assertEqual(els[0]["shadow"]["blur"], 8)
        self.assertNotIn("shadow", els[1])
        self.assertTrue(any("$shadow.zzz" in e for e in errs))


class CanBreakTest(unittest.TestCase):
    def test_kanji_space_digit_is_not_split(self):
        t = "毎日の送料は無料で週 2 回届ける"
        for i in range(1, len(t)):
            if t[i - 1:i + 1] in ("週 ",) or (t[i] == " " and t[i - 1] == "週"):
                self.assertFalse(pe._can_break(t, i), i)
        t = "70 歳以上は無料。約 8 億円の効果"
        i = t.index("約 8")
        self.assertFalse(pe._can_break(t, i + 1))
        self.assertFalse(pe._can_break(t, i + 2))

    def test_particle_before_a_number_may_still_break(self):
        t = "まず 1 部署で 3 か月試す"
        i = t.index("3 か")
        self.assertTrue(pe._can_break(t, i))


class ShowListTest(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([PY, str(TOOLS / "pattern_engine.py"), *args], capture_output=True, text=True, encoding="utf-8")

    def test_list_is_one_row_per_pattern_with_block_column(self):
        r = self.cli("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        names = pe.available_names()
        lines = r.stdout.splitlines()
        for n in names:
            rows = [ln for ln in lines if ln.startswith(n + " ")]
            self.assertEqual(len(rows), 1, n)
        self.assertIn("ブロック", r.stdout)
        self.assertIn("何を言うときに使うか", r.stdout)
        self.assertLess(len(lines), len(names) + 8)

    def test_list_detail_has_slots(self):
        r = self.cli("list", "--detail")
        self.assertIn("records", r.stdout)

    def test_show_example_for_body_pattern_has_title_and_is_warning_free(self):
        pat = pe.load_pattern("numbered-columns")
        sl = pe.show_example_slide(pat)
        self.assertIn("title", sl)
        self.assertIn("slots", sl)
        self.assertEqual(sl["type"], "pattern")
        fails, warns = [], []
        pe.validate(sl, 0, None, fails.append, warns.append)
        self.assertEqual((fails, warns), ([], []))
        r = self.cli("show", "numbered-columns")
        self.assertIn("合成スライドのブロック", r.stdout)
        self.assertIn("幅の下限", r.stdout)

    def test_show_example_for_full_pattern_has_no_extra_keys(self):
        sl = pe.show_example_slide(pe.load_pattern("pillars"))
        self.assertEqual(set(sl), {"type", "pattern", "slots"})

    def test_show_prints_descriptions_and_values(self):
        pat = {"name": "z", "frame": "body", "slots": {"state": {"kind": "text", "label": "状態", "description": "進み具合",
                                                             "values": {"done": ["済"], "todo": [""]}}}}
        out = "\n".join(pe._slot_table(pat))
        self.assertIn("説明: 進み具合", out)
        self.assertIn("値の候補: done（済） / todo", out)

    def test_block_note(self):
        self.assertIn("置けない", pe.block_note({"frame": "full"}))
        note = pe.block_note({"frame": "body"})
        self.assertIn("幅およそ", note)               # narrow も min_width も無い型は、縮小率の下限に当たる幅を言う（半幅は不向き）
        self.assertIn("不向き", note)
        nc = pe.load_pattern("numbered-columns")
        self.assertIn("380px", pe.block_note(nc))                       # 狭い構図があるので、読める幅の下限（個数別の実測）を言う
        self.assertIn("4 個のときは 400px 以上", pe.block_note(nc))
        self.assertIn("半幅", pe.block_note(nc))
        self.assertIn("4 個のときは 500px 以上", pe.block_note(pe.load_pattern("compare-options")))        # 4 案は 500px 以上
        self.assertIn("900px 以上", pe.block_note({"frame": "body", "min_width": 900}))
        self.assertIn("半幅", pe.block_note({"frame": "body", "narrow": {"below": 700, "elements": []}}))


class ImageExampleTest(unittest.TestCase):
    def make_dir(self, t):
        d = Path(t) / "pats"
        (d / "assets").mkdir(parents=True)
        # 画像つきの型（example は assets/ 配下）と、同じ場所の画像
        from PIL import Image
        Image.new("RGB", (40, 30), (200, 100, 50)).save(d / "assets" / "sample.png")
        pat = {"name": "pic", "frame": "body", "size": [1136, 300], "slots": {
            "photo": {"kind": "image", "label": "写真", "example": "assets/sample.png"},
            "note": {"kind": "text", "example": "説明"}},
               "elements": [{"if": "photo", "kind": "image", "name": "写真", "x": 0, "y": 0, "w": 400, "h": 300, "path": "{{photo}}", "fit": "cover"},
                            {"if": "!photo", "name": "写真の代わり", "x": 0, "y": 0, "w": 400, "h": 300, "fill": "surface"},
                            {"name": "説明", "x": 420, "y": 0, "w": 700, "h": 100, "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{note}}", "size": 20, "color": "text"}]}]}}]}
        (d / "pic.json").write_text(json.dumps(pat, ensure_ascii=False), encoding="utf-8")
        return d

    def test_optional_image_slot_without_example_is_left_out(self):
        pat = {"name": "p", "slots": {"photo": {"kind": "image"}, "t": {"kind": "text", "example": "x"}}, "elements": []}
        self.assertEqual(pe.example_slide(pat)["slots"], {"t": "x"})
        pat["slots"]["photo"]["required"] = True
        self.assertEqual(pe.example_slide(pat)["slots"]["photo"], "assets/example.png")

    def test_preview_finds_pattern_images_next_to_the_pattern_and_copies_them(self):
        import os
        with tempfile.TemporaryDirectory() as t:
            d = self.make_dir(t)
            old = os.environ.get("SLIDE_DECK_PATTERNS")
            os.environ["SLIDE_DECK_PATTERNS"] = str(d)
            try:
                deck, errors = pe.preview_deck(None, "default")
                self.assertEqual([e for e in errors if e.startswith("pic")], [])
                self.assertIn("pic", [s["pattern"] for s in deck["slides"]])
                out = Path(t) / "out"
                out.mkdir()
                n = pe._copy_preview_assets(deck, None, out)
                self.assertGreaterEqual(n, 1)
                self.assertTrue((out / "assets" / "sample.png").is_file())
            finally:
                if old is None:
                    os.environ.pop("SLIDE_DECK_PATTERNS", None)
                else:
                    os.environ["SLIDE_DECK_PATTERNS"] = old

    def test_missing_example_image_is_skipped_with_a_reason(self):
        import os
        with tempfile.TemporaryDirectory() as t:
            d = self.make_dir(t)
            (d / "assets" / "sample.png").unlink()
            old = os.environ.get("SLIDE_DECK_PATTERNS")
            os.environ["SLIDE_DECK_PATTERNS"] = str(d)
            try:
                deck, errors = pe.preview_deck(None, "default")
                self.assertNotIn("pic", [s["pattern"] for s in deck["slides"]])
                self.assertTrue(any(e.startswith("pic") and "sample.png" in e for e in errors))
            finally:
                if old is None:
                    os.environ.pop("SLIDE_DECK_PATTERNS", None)
                else:
                    os.environ["SLIDE_DECK_PATTERNS"] = old

    def test_empty_image_slot_switches_to_the_no_photo_composition(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.make_dir(t)
            pat = json.loads((d / "pic.json").read_text(encoding="utf-8"))
            els, _ = pe.expand({"slots": {"note": "x"}}, pat, THEME, None, 1, 1, lambda m: None, [])
            self.assertEqual([e["name"] for e in els], ["写真の代わり", "説明"])


class ReviewFixTest(unittest.TestCase):
    """独立レビュー（pe-C / pe-V）の指摘への対応: 警告の絞り込み・count_of・at_most・unknown_as・variants_by の形違い"""

    def problems(self, name, slots):
        return pe.slot_problems({"slots": slots}, pe.load_pattern(name))

    def test_checklist_unknown_state_message_matches_behaviour(self):             # pe-C-03
        _e, w = self.problems("checklist", {"items": [{"text": "a", "state": "ほげ"}] * 3})
        self.assertIn("未着手", w[0])
        self.assertNotIn("どの状態にも当てはまらない", w[0])
        els, _ = pe.expand({"slots": {"items": [{"text": "a", "state": "ほげ"}] * 3}}, pe.load_pattern("checklist"), THEME, None, 1, 1, lambda m: None, [])
        names = [e["name"] for e in ce.flatten(els) if e.get("name")]
        self.assertIn("項目1の枠（未着手）", names)

    def test_checklist_everyday_state_words_are_aliases_and_no_length_warning(self):    # pe-C-03
        for w in ("対応中", "着手", "実施中", "対応済", "doing", "in progress", "完了済み"):
            _e, ws = self.problems("checklist", {"items": [{"text": "a", "state": w}] * 3})
            self.assertEqual(ws, [], w)
        els, _ = pe.expand({"slots": {"items": [{"text": "a", "state": "対応中"}] * 3}}, pe.load_pattern("checklist"), THEME, None, 1, 1, lambda m: None, [])
        self.assertIn("項目1の進行中の印", [e["name"] for e in ce.flatten(els) if e.get("name")])

    def test_items_beyond_max_are_not_checked_one_by_one(self):                     # pe-C-04
        items = [{"head": "a", "body": "b"} for _ in range(5)] + [{"head": "あ" * 99, "body": "い" * 999}]
        _e, w = self.problems("numbered-columns", {"items": items})
        self.assertEqual(len(w), 1)
        self.assertIn("先頭の 5 個だけ描きました", w[0])

    def test_many_same_warnings_are_collapsed(self):                                # pe-C-04
        _e, w = self.problems("checklist", {"items": [{"text": "a", "state": "ほげ"}] * 7})
        self.assertEqual(len(w), 4)
        self.assertIn("ほかに 4 件", w[-1])
        _e, w = self.problems("checklist", {"items": [{"text": "a", "state": "ほげ"}] * 20000})
        self.assertLess(len(w), 10)
        self.assertLess(sum(len(x) for x in w), 5000)

    def test_collapsing_leaves_a_single_remaining_warning_as_is(self):              # pe-C-04
        _e, w = self.problems("checklist", {"items": [{"text": "a", "state": "ほげ"}] * 4})
        self.assertEqual(len(w), 4)
        self.assertFalse(any("上と同じ直し方" in x for x in w))

    def test_check_pattern_variants_by_of_wrong_type_is_an_error_not_a_traceback(self):   # pe-C-05
        for bad in ({"a": 1}, ["x"], 3, None, True):
            pat = copy.deepcopy(pe.load_pattern("icon-grid"))
            pat["variants_by"] = bad
            errs, _w = pe.check_pattern(pat, THEME, quick=True)
            self.assertTrue(any("variants_by" in e for e in errs), repr(bad))

    def test_check_pattern_out_of_bounds_check_ignores_non_numbers(self):           # pe-C-05
        pat = copy.deepcopy(pe.load_pattern("quote-block"))
        for els in ([pat["elements"]] if "elements" in pat else []):
            pass
        pat["elements"] = [{"x": None, "y": "a", "w": 10, "h": [1], "fill": "primary"}, {"x": 0, "y": 0, "w": "x", "h": None, "fill": "primary"}]
        pat.pop("variants", None)
        pat.pop("variants_by", None)
        pat.pop("narrow", None)
        try:
            pe.check_pattern(pat, THEME)
        except Exception as e:  # noqa: BLE001
            self.fail(repr(e))

    def test_flag_false_words_include_everyday_ones(self):                          # pe-C-06
        for v in ("無", "否", "x", "X", "ー", "-", "－", "なし", "対象外", "不要", "×"):
            self.assertFalse(pe._as_flag(v), v)
        for v in ("現在地", "○", "おすすめ", "あり", True, 1):
            self.assertTrue(pe._as_flag(v), repr(v))

    def test_at_most_warns_when_too_many_are_marked(self):                          # pe-C-06 / pe-V-12
        base = [{"date": str(i), "head": "h", "body": "b", "now": False} for i in range(4)]
        for k, n in (([1], 0), ([1, 2], 1), ([0, 1, 2], 1)):
            items = copy.deepcopy(base)
            for j in k:
                items[j]["now"] = True
            _e, w = self.problems("timeline", {"items": items})
            if len(k) == 1:
                self.assertEqual(w, [])
            else:
                self.assertEqual(len(w), 1)
                self.assertIn("1 個までにしてください", w[0])
        items = copy.deepcopy(base)
        items[1]["now"] = "否"
        items[2]["now"] = "無"
        _e, w = self.problems("timeline", {"items": items})
        self.assertEqual(w, [])

    def test_at_most_for_text_field_counts_filled(self):                            # pe-V-12
        opts = [{"name": n, "tag": "おすすめ"} for n in "ABC"]
        _e, w = self.problems("compare-options", {"options": opts, "rows": [{"label": "x", "values": ["1", "2", "3"]}] * 2})
        self.assertEqual(len(w), 1)
        self.assertIn("1 個までにしてください", w[0])
        opts[1]["tag"] = opts[2]["tag"] = ""
        _e, w = self.problems("compare-options", {"options": opts, "rows": [{"label": "x", "values": ["1", "2", "3"]}] * 2})
        self.assertEqual(w, [])

    def test_at_most_and_unknown_as_definitions_are_checked(self):
        for fd, word in (({"kind": "flag", "at_most": "1"}, "at_most"), ({"kind": "flag", "at_most": -1}, "at_most"),
                         ({"kind": "text", "values": {"a": ["x"]}, "unknown_as": "zz"}, "unknown_as"), ({"kind": "text", "unknown_as": "a"}, "unknown_as")):
            pat = {"name": "q", "frame": "body", "size": [1136, 300], "slots": {"c": {"kind": "records", "fields": {"f": fd}}},
                   "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 800, "h": 200, "cols": 1}, "template": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "primary"}]}]}
            errs, _w = pe.check_pattern(pat, THEME, quick=True)
            self.assertTrue(any(word in e for e in errs), (fd, errs))

    def test_record_flag_uses_default_like_slot_flag(self):                         # pe-C-06
        self.assertTrue(pe._field_value({"kind": "flag", "default": True}, None))
        self.assertFalse(pe._field_value({"kind": "flag", "default": True}, False))
        self.assertFalse(pe._field_value({"kind": "flag"}, None))

    def test_count_of_warning_is_one_line_per_field_not_per_row(self):             # pe-C-07
        rows = [{"label": f"観点{i}", "values": ["1", "2"]} for i in range(4)]
        opts = [{"name": n} for n in "ABC"]
        _e, w = self.problems("compare-options", {"options": opts, "rows": rows})
        w = [x for x in w if "合っていません" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("すべての項目（4 個）", w[0])
        rows[1]["values"] = ["1", "2", "3"]
        _e, w = self.problems("compare-options", {"options": opts, "rows": rows})
        w = [x for x in w if "合っていません" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("1・3・4 個目の項目", w[0])

    def test_count_of_compares_with_the_drawn_count_when_over_max(self):           # pe-C-07
        opts = [{"name": str(i)} for i in range(6)]
        rows = [{"label": "x", "values": ["1", "2", "3", "4"]}]
        _e, w = self.problems("compare-options", {"options": opts, "rows": rows})
        self.assertEqual(len([x for x in w if "最大 4 個" in x]), 1)
        self.assertEqual([x for x in w if "合っていません" in x], [])             # 描かれるのは先頭 4 案なので 4 個で合っている
        _e, w = self.problems("compare-options", {"options": opts, "rows": [{"label": "x", "values": ["1", "2", "3", "4", "5", "6"]}]})
        self.assertTrue(any("4 個そろえて" in x for x in w))

    def test_zero_index_in_a_placeholder_gets_a_specific_message(self):            # pe-C-07
        pat = {"name": "z", "frame": "body", "size": [1136, 300], "slots": {"c": {"kind": "records", "fields": {"v": {"kind": "list"}}}},
               "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 800, "h": 200, "cols": 1}, "template": [
                   {"x": 0, "y": 0, "w": 100, "h": 20, "text": {"paragraphs": [{"runs": [{"text": "{{v.0}}", "size": 14, "color": "text"}]}]}}]}]}
        errs, _w = pe.check_pattern(pat, THEME, quick=True)
        self.assertTrue(any("添字は 1 から" in e for e in errs), errs)
        errs2 = []
        pe.expand({"slots": {"c": [{"v": ["a"]}]}}, pat, THEME, None, 1, 1, lambda m: None, errs2)
        self.assertTrue(any("添字は 1 から" in e for e in errs2), errs2)


class RenderFixTest(unittest.TestCase):
    """独立レビュー（pe-C-02 / pe-V-01〜03・09）: 全段 body なしの構図・仮名の途中で切らない・最終行・引用の折り・下の隙間"""

    def test_aggregate_condition_any(self):
        sc = {"stages": [{"name": "a", "body": ""}, {"name": "b", "body": "x"}]}
        self.assertTrue(pe._cond({"slot": "stages", "field": "body", "any": True}, sc))
        self.assertFalse(pe._cond({"slot": "stages", "field": "body", "any": False}, sc))
        sc = {"stages": [{"name": "a", "body": ""}, {"name": "b"}]}
        self.assertTrue(pe._cond({"slot": "stages", "field": "body", "any": False}, sc))
        self.assertFalse(pe._cond({"slot": "nothing", "field": "body", "any": True}, sc))      # 無いスロットは「ある項目なし」

    def test_aggregate_condition_is_checked_by_check_pattern(self):
        pat = {"name": "q", "frame": "body", "size": [1136, 300], "slots": {"c": {"kind": "records", "fields": {"b": {"kind": "text"}}}, "t": {"kind": "text"}},
               "elements": [{"x": 0, "y": 0, "w": 10, "h": 10, "fill": "primary", "if": {"slot": "c", "field": "b", "any": False}}]}
        self.assertEqual(pe.check_pattern(pat, THEME, quick=True)[0], [])
        for bad in ({"slot": "c", "field": "zz", "any": False}, {"slot": "t", "field": "b", "any": False}, {"slot": "c", "field": "b", "any": "no"},
                    {"slot": "c", "field": "b", "any": True, "is": "x"}):
            pat["elements"][0]["if"] = bad
            self.assertTrue(pe.check_pattern(pat, THEME, quick=True)[0], bad)

    def _names(self, name, slots):
        p = pe.load_pattern(name)
        warns = []
        els, _ = pe.expand({"slots": slots}, p, THEME, None, 1, 1, warns.append, [])
        return [e for e in ce.flatten(els)], warns

    def test_funnel_and_pyramid_without_body_are_centered_and_wide(self):                  # pe-C-02 / pe-V-05
        for name, key, ns in (("funnel", "stages", (3, 4, 5)), ("pyramid", "tiers", (3, 4, 5))):
            for n in ns:
                for body in ("", None):
                    items = [{"name": f"段{i}", **({"value": f"{i}0 人"} if name == "funnel" else {}), **({"body": body} if body is not None else {})} for i in range(n)]
                    els, warns = self._names(name, {key: items})
                    self.assertEqual(warns, [], (name, n))
                    shapes = [e for e in els if e.get("geom") == "custom"]
                    self.assertEqual(len(shapes), n, (name, n))
                    left = min(e["x"] for e in shapes)
                    right = max(e["x"] + e["w"] for e in shapes)
                    self.assertAlmostEqual((left + right) / 2, 568, delta=1, msg=(name, n))        # 設計幅 1136 の中央
                    self.assertGreater(right - left, 800, (name, n))
                    self.assertFalse([e for e in els if "説明" in str(e.get("name")) and "説明なし" not in str(e.get("name"))], (name, n))   # 説明の帯・文は出ない

    def test_funnel_with_one_body_keeps_the_left_construction(self):
        items = [{"name": "a", "value": "1", "body": ""}, {"name": "b", "value": "2", "body": "説明"}, {"name": "c", "value": "3"}]
        els, _w = self._names("funnel", {"stages": items})
        shapes = [e for e in els if e.get("geom") == "custom"]
        self.assertLess(max(e["x"] + e["w"] for e in shapes), 600)
        self.assertTrue([e for e in els if "説明" in str(e.get("name"))])

    def test_no_break_inside_kana_verbs(self):                                                # pe-V-01
        f = ["Hiragino Sans"]
        for text in ("全校分を新棟でまとめて調理する", "空床が出にくかった理由を調べる", "冬休み明けから、全校分を新棟でまとめて調理する"):
            for w in (130, 170, 220):               # 1 語（「出にくかった」6 字 = 120px）が収まる幅から。それより狭いときは文字単位の折りになる
                joined = pe._phrase_lines(text, 20, w, f, False)
                for a, b in zip(joined, joined[1:]):
                    self.assertFalse(a.endswith("まと") and b.startswith("めて"), (text, w, joined))
                    self.assertFalse(a.endswith("出に") and b.startswith("くかった"), (text, w, joined))

    def test_number_unit_last_line_is_not_a_single_char(self):                               # pe-V-01
        f = ["Hiragino Sans"]
        for w in (70, 80, 100):
            lines = pe._phrase_lines("従業員 420 名", 20, w, f, False)
            self.assertGreaterEqual(len(lines[-1].replace(" ", "")), 3, (w, lines))
            self.assertNotEqual(lines[-1], "名")

    def test_can_break_levels(self):
        t = "週 2 回、実際の献立で"
        self.assertFalse(pe._can_break(t, 1))
        self.assertTrue(pe._can_break(t, 1, 2))          # level 2: 和文 + 空白 + 数字の空白は切ってよい
        self.assertFalse(pe._can_break(t, 3, 2))         # 数字と単位は離さない
        self.assertFalse(pe._can_break("まとめて", 2))      # 仮名の途中

    def test_multi_run_paragraph_is_wrapped_as_one_sentence(self):                            # pe-V-03
        st = pe._St(THEME, lambda m: None, [], "t", {}, ())
        q = "導入前は不安でしたが、最初の 1 か月で、毎週の集計に使っていた 4 時間がほぼ無くなりました。"
        runs = [{"text": "“", "size": 38, "color": "#007A8F", "bold": True}, {"text": q, "size": 38, "color": "#000000", "bold": True},
                {"text": "”", "size": 38, "color": "#007A8F", "bold": True}]
        out = pe._wrap_paragraphs([{"runs": runs}], 700, st)[0]["runs"]
        lines, cur = [], ""
        for r in out:
            if r.get("br"):
                self.assertTrue(r.get("soft"))
                lines.append(cur)
                cur = ""
            else:
                cur += r["text"]
        lines.append(cur)
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual("".join(lines).replace(" ", ""), ("“" + q + "”").replace(" ", ""))   # 文字は失われない（行頭・行末の空白だけ落ちる）（先頭・末尾の run の色も保たれる）
        self.assertEqual(out[0]["color"], "#007A8F")
        self.assertEqual(out[-1]["color"], "#007A8F")
        for a, b in zip(lines, lines[1:]):
            self.assertFalse(a.endswith("1") and b.startswith("か月"), lines)    # 数字と単位は離れない
        self.assertGreaterEqual(len(lines[-1]), 3)
        # 書式の違う run が混ざる段落は触らない
        mixed = [{"text": "あ" * 40, "size": 38}, {"text": "い" * 40, "size": 20}]
        self.assertEqual(pe._wrap_paragraphs([{"runs": mixed}], 300, st)[0]["runs"], mixed)

    def test_quote_block_breaks_by_phrase(self):                                            # pe-V-03
        els, _w = self._names("quote-block", {"quote": "導入前は不安でしたが、最初の 1 か月で、毎週の集計に使っていた 4 時間がほぼ無くなりました。", "name": "山本 健一"})
        txt = [e for e in els if e.get("text")][0]
        brs = [r for p in txt["text"]["paragraphs"] for r in p["runs"] if r.get("br")]
        self.assertTrue(brs)                                                                  # 明示の折り（型が決めた位置）

    def test_short_last_line_is_warned_once(self):                                          # pe-V-02
        pat = {"name": "o", "frame": "body", "size": [300, 200], "slots": {"c": {"kind": "list", "max": 3}},
               "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 300, "h": 120, "cols": 1, "gap": 4}, "template": [
                   {"name": "文", "x": 0, "y": 0, "w": 160, "h": 40, "text": {"insets": [0, 0, 0, 0], "paragraphs": [{"runs": [{"text": "{{.}}", "size": 20, "color": "text"}]}]}}]}]}
        w = []
        pe.expand({"slots": {"c": ["ABCDEFGH" * 2 + "いろ", "ABCDEFGH" * 2 + "は"]}}, pat, THEME, None, 1, 1, w.append, [])
        # 英字の折りはエンジンが決めない（soft の改行が無い）ので警告は出ない。和文だけで確かめる
        w = []
        els = [{"text": {"paragraphs": [{"runs": [{"text": "配膳ラインを止めて、調理機器を", "size": 20}, {"br": True, "soft": True}, {"text": "搬出", "size": 20}]}]}}]
        st = pe._St(THEME, w.append, [], "t", {}, ())
        pe._warn_short_last_lines(els, st)
        self.assertEqual(len(w), 1)
        self.assertIn("最終行が 1〜2 文字", w[0])
        w.clear()
        els[0]["text"]["paragraphs"][0]["runs"][2]["text"] = "搬出する"
        pe._warn_short_last_lines(els, st)
        self.assertEqual(w, [])

    def test_example_slide_clears_at_most_marks_on_repeats(self):
        p = pe.load_pattern("timeline")
        for n in (3, 5, 6):
            items = pe.example_slide(p, n)["slots"]["items"]
            self.assertEqual(len(items), n)
            self.assertLessEqual(sum(1 for it in items if it.get("now")), 1)

    def test_tight_region_with_conclusion_keeps_a_bottom_gap(self):                         # pe-V-09
        p = pe.load_pattern("numbered-columns")
        sl = dict(pe.example_slide(p), conclusion="結論", source="出典")
        els = pe.pattern_block_elements(sl, p, (0, 0, 1136, 380), THEME, None, 1, 1, None, [])
        bottom = max(e["y"] + e.get("h", 0) for e in ce.flatten(els) if _is_num(e.get("y")) and _is_num(e.get("h", 0)))
        self.assertLessEqual(bottom, 380 - pe.BODY_BOTTOM_GAP + 1)
        # 結論帯が無いとき・ブロックのときは今までどおり（隙間を足さない）
        els2 = pe.pattern_block_elements(pe.example_slide(p), p, (0, 0, 1136, 380), THEME, None, 1, 1, None, [])
        bottom2 = max(e["y"] + e.get("h", 0) for e in ce.flatten(els2) if _is_num(e.get("y")) and _is_num(e.get("h", 0)))
        self.assertGreater(bottom2, bottom)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class BrokenInputFuzzTest(unittest.TestCase):
    """壊れた型 JSON・壊れたスロット値でトレースバックを出さない（例外にせず errors / warns で返す）"""

    def try_all(self, pat, slots_list):
        for sl in slots_list:
            try:
                pe.check_pattern(copy.deepcopy(pat), THEME)
            except Exception as e:  # noqa: BLE001
                self.fail(f"check_pattern が例外: {e!r} / {pat}")
            try:
                pe.slot_problems({"slots": sl}, pat)
                pe.expand({"slots": sl}, copy.deepcopy(pat), THEME, None, 1, 1, lambda m: None, [])
            except Exception as e:  # noqa: BLE001
                self.fail(f"例外: {e!r} / {pat} / {sl}")

    BASE = {"name": "f", "frame": "body", "size": [1136, 300], "slots": {
        "t": {"kind": "text", "values": {"a": ["x"]}}, "c": {"kind": "records", "fields": {"h": {"kind": "list"}, "s": {"kind": "text", "values": {"a": ["x"]}}, "n": {"kind": "flag"}}, "max": 3},
        "l": {"kind": "list", "max": 3}, "f": {"kind": "flag"}},
            "elements": [{"repeat": "c", "grid": {"x": 0, "y": 0, "w": 800, "h": 200, "cols": 3}, "template": [
                {"x": 0, "y": 0, "w": 100, "h": 50, "if": {"slot": "s", "is": "a"}, "fill": "primary",
                 "text": {"paragraphs": [{"runs": [{"text": "{{h.1}}{{h.5}}", "size": "@fit"}]}]}, "fit": {"sizes": [20, 16], "group": True}}]}]}

    SLOTS = [{}, {"t": None}, {"t": {"a": 1}}, {"t": ["a", ["b"]]}, {"c": None}, {"c": "x"}, {"c": [None, 1, "x", [], {}]}, {"c": [{"h": None, "s": None, "n": None}]},
             {"c": [{"h": {"a": 1}, "s": {"b": 2}, "n": [1]}]}, {"c": [{"h": [["a"], {"b": 1}, None], "s": 5, "n": "false"}]},
             {"l": 5}, {"l": [None, [], {}]}, {"f": {"a": 1}}, {"f": [0]}, {"c": [{"h": ["あ"] * 500}] * 50}, {"l": ["x" * 100000]},
             {"c": [{"h": "a", "s": "a", "n": 0}] * 100}]

    def test_broken_slot_values(self):
        self.try_all(self.BASE, self.SLOTS)

    def test_broken_conditions_and_groups_and_widths(self):
        variants = []
        for cond in ({"slot": 5, "is": 1}, {"slot": "t", "in": "a"}, {"slot": "t", "in": [[1], {"a": 1}, None]}, {"not": None}, {"not": [1]},
                     {"slot": "t", "is": {"a": 1}}, {"slot": "nope", "is": 1}, 5, None, [None, {}], {"all": 1}):
            p = copy.deepcopy(self.BASE)
            p["elements"][0]["template"][0]["if"] = cond
            variants.append(p)
        for fit in ({"sizes": [20], "group": []}, {"sizes": [20], "group": {"a": 1}}, {"sizes": ["$nope", "$type", None, True], "group": "g"},
                    {"sizes": [0, -5], "group": True}, {"group": True}, {"sizes": "x", "group": "g"}):
            p = copy.deepcopy(self.BASE)
            p["elements"][0]["template"][0]["fit"] = fit
            variants.append(p)
        for extra in ({"min_width": "900"}, {"min_width": None}, {"min_width": [1]}, {"min_width": -5}, {"narrow": "x"}, {"narrow": {"below": "a"}},
                      {"narrow": {"below": 100, "elements": "x"}}, {"narrow": {"below": 100, "size": "x", "elements": [], "variants": 5}},
                      {"narrow": {"below": 700, "size": [0, 0], "elements": [], "variants": {"x": 1}, "variants_by": 5}}):
            p = copy.deepcopy(self.BASE)
            p.update(extra)
            variants.append(p)
        for v in variants:
            try:
                pe.check_pattern(copy.deepcopy(v), THEME)
                pe.body_rect_problems({}, v, {"w": 556, "h": 300}, True)
                pe.body_rect_problems({}, v, {"w": "x", "h": None}, True)
                pe.pattern_block_elements({"slots": {"c": [{"h": ["a"], "s": "a"}]}}, copy.deepcopy(v), (0, 0, 556, 300), THEME)
                pe.expand({"slots": {"c": [{"h": ["a"], "s": "a"}], "t": "a"}}, copy.deepcopy(v), THEME, None, 1, 1, lambda m: None, [])
            except Exception as e:  # noqa: BLE001
                self.fail(f"例外: {e!r} / {v.get('narrow')} {v.get('min_width')} {v['elements'][0]['template'][0].get('if')} {v['elements'][0]['template'][0].get('fit')}")

    def test_values_definition_junk(self):
        for vals in ({"a": None}, {"a": [None, [1], {"x": 1}]}, {"": []}, {"b": 5}, [], "x", 5):
            p = copy.deepcopy(self.BASE)
            p["slots"]["t"]["values"] = vals
            self.try_all(p, [{"t": "a"}, {"t": None}, {"t": 5}])

    def test_group_cycle_like_names_and_nonexistent_group_are_harmless(self):
        p = copy.deepcopy(self.BASE)
        p["elements"][0]["template"][0]["fit"] = {"sizes": [20, 16], "group": "no-such-other-member"}
        errs, warns = pe.check_pattern(p, THEME)
        self.assertEqual(errs, [])
        els, _ = pe.expand({"slots": {"c": [{"h": ["あ"], "s": "a"}]}}, p, THEME, None, 1, 1, lambda m: None, [])
        self.assertEqual(len(els), 1)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自動フィットの土台と table / 見出しのフィット（core-3）のテスト。

  - density / autofit / 明示値の判定（autofit.density_of / autofit_on / explicit_props）
  - meta.density・autofit の値検査（不正は fail）
  - fit_table_layout（純関数）: 既定で収まれば今と同じ、詰める・下限・列幅・警告
  - resolve_style 経由: 明示値は動かさない・density プリセット・autofit:false
  - 見出し（title）の縮小と警告
  - 実ビルド: HTML は固定レイアウトの列幅、PPTX の列幅が HTML と同じ

実行: python3 -m unittest plugins/slide-deck/tools/test_autofit.py
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import autofit  # noqa: E402
import build_deck as b  # noqa: E402
import ja_text  # noqa: E402

LAYOUT = json.loads((ROOT / "templates" / "layouts" / "default.json").read_text(encoding="utf-8"))

PARAMS = dict(cell_size=17, header_size=19, header_h=52, row_h=58, line_height=1.35, pad_x=16, pad_y=10,
              col_widths=None, min_size=12, max_lines=2, wrap_ratio=0.7)
RECT = {"x": 72, "y": 192, "w": 1136}


def table_slide(n_rows, cell, ncols=4, **extra):
    cols = ["項目"] + [f"列{j}" for j in range(1, ncols)]
    rows = [[f"R{i + 1}"] + [cell] * (ncols - 1) for i in range(n_rows)]
    return {"type": "table", "title": "表", "columns": cols, "rows": rows, **extra}


def deck_of(slide, **meta):
    return {"meta": {"title": "t", **meta}, "slides": [slide]}


def resolve(slide, **meta):
    deck = deck_of(slide, **meta)
    return b.resolve_style(LAYOUT, deck, slide)


@contextlib.contextmanager
def quiet():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        yield err


class SettingsTests(unittest.TestCase):
    def test_density_default_and_values(self):
        self.assertEqual(autofit.density_of({}), "standard")
        self.assertEqual(autofit.density_of({"meta": {"density": "read"}}), "read")
        # スライドの density が meta より優先
        self.assertEqual(autofit.density_of({"meta": {"density": "read"}}, {"density": "talk"}), "talk")
        # 不正な値は standard（検査は validate_deck）
        self.assertEqual(autofit.density_of({"meta": {"density": "huge"}}), "standard")

    def test_autofit_flags(self):
        self.assertTrue(autofit.autofit_on({"meta": {}}, {}))
        self.assertFalse(autofit.autofit_on({"meta": {"autofit": False}}, {}))
        self.assertFalse(autofit.autofit_on({"meta": {}}, {"autofit": False}))
        self.assertTrue(autofit.autofit_on({"meta": {"autofit": False}}, {"autofit": True}) is False)

    def test_explicit_props_collects_overrides_and_slide_style(self):
        deck = {"meta": {"layout_overrides": {"table": {"table": {"row_h": 50}}, "common": {"title": {"size": 30}}}}}
        slide = {"type": "table", "style": {"table": {"cell_size": 15}}}
        ex = autofit.explicit_props(deck, slide)
        self.assertEqual(ex["table"], {"row_h", "cell_size"})
        self.assertEqual(ex["title"], {"size"})
        self.assertTrue(autofit.is_explicit(deck, slide, "table", "row_h"))
        self.assertFalse(autofit.is_explicit(deck, slide, "table", "col_widths"))
        # 別タイプの overrides は効かない
        self.assertFalse(autofit.is_explicit(deck, {"type": "bullets"}, "table", "row_h"))


class ValidationTests(unittest.TestCase):
    def _validate(self, deck):
        with quiet():
            b.validate_deck(deck, LAYOUT, {"colors": {}}, None)

    def test_bad_meta_density_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self._validate(deck_of({"type": "section", "title": "x"}, density="huge"))
        self.assertIn("meta.density", str(cm.exception))
        self.assertIn("talk / standard / read", str(cm.exception))

    def test_bad_autofit_type_fails(self):
        with self.assertRaises(SystemExit) as cm:
            self._validate(deck_of({"type": "section", "title": "x"}, autofit="yes"))
        self.assertIn("meta.autofit", str(cm.exception))

    def test_bad_slide_density_and_autofit_fail(self):
        with self.assertRaises(SystemExit) as cm:
            self._validate(deck_of({"type": "section", "title": "x", "density": "tiny"}))
        self.assertIn("density", str(cm.exception))
        with self.assertRaises(SystemExit):
            self._validate(deck_of({"type": "section", "title": "x", "autofit": 1}))

    def test_valid_values_pass_without_unknown_key_warning(self):
        theme = b.load_theme("default", b.theme_dirs(None))
        with quiet() as err:
            b.validate_deck(deck_of({"type": "bullets", "title": "x", "bullets": ["a"], "density": "read", "autofit": False},
                                    density="talk", autofit=True), LAYOUT, theme, None)
        self.assertNotIn("未知", err.getvalue())

    def test_layout_densities_shape_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "layouts").mkdir()
            (Path(d) / "layouts" / "bad.json").write_text(json.dumps({"densities": {"read": {"table": 3}}}), encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                b.load_layout("bad", Path(d))
            self.assertIn("densities", str(cm.exception))


class BadColWidthsTests(unittest.TestCase):
    """col_widths が不正でも、自動フィットが例外で落ちず、検証の明快なエラーに届く（core-C-01）。"""

    def _validate(self, widths):
        slide = table_slide(2, "a", ncols=3, style={"table": {"col_widths": widths}})
        deck = deck_of(slide)
        theme = b.load_theme("default", b.theme_dirs(None))
        with quiet():
            b.validate_deck(deck, LAYOUT, theme, None)

    def test_wrong_length_reports_count_mismatch(self):
        for w in ([1, 2], [1, 2, 3, 4]):
            with self.assertRaises(SystemExit) as cm:
                self._validate(w)
            self.assertIn("要素数", str(cm.exception))

    def test_non_numeric_reports_shape_error(self):
        with self.assertRaises(SystemExit) as cm:
            self._validate(["a", "b", "c"])
        self.assertIn("0 以上の数値の配列", str(cm.exception))

    def test_resolve_style_does_not_crash(self):
        for w in ([1, 2], ["a", "b", "c"], [1, -1, 2], "x"):
            slide = table_slide(2, "a", ncols=3, style={"table": {"col_widths": w}})
            resolve(slide)
        self.assertEqual(autofit.fit_table_layout(["A", "B", "C"], [["a", "b", "c"]], RECT, 650, PARAMS | {"col_widths": [1, 2]},
                                                  set())["col_widths"].__len__(), 3)


class OrphanWrapTests(unittest.TestCase):
    """表のセルが 1〜2 字だけの最終行に折れる「泣き別れ」を避ける（core-A-01）と、行ごとの罫線 1px（core-C-03）。"""

    def test_is_orphan_wrap(self):
        self.assertTrue(autofit.is_orphan_wrap("あ" * 11 + "ク", 17, 11 * 17))
        self.assertFalse(autofit.is_orphan_wrap("あ" * 11, 17, 11 * 17))              # 折れない
        self.assertFalse(autofit.is_orphan_wrap("あ" * 20, 17, 11 * 17))              # 最終行が 9 字

    def test_widths_are_rebalanced_so_no_cell_ends_with_one_or_two_chars(self):
        cols = ["項目", "論点", "検討ポイント", "備考"]
        base = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも"
        rows = [[f"A-{i}", base[:31] + "デスク", base[:12] + "確定", "備考です"] for i in range(5)]
        n_orphan = lambda w: autofit._table_orphans(cols, rows, w, 17, 19, 16, (), ())
        raw = autofit.table_column_widths(cols, rows, 17, 19, 1136, 16, max_lines=0)
        bal = autofit.table_column_widths(cols, rows, 17, 19, 1136, 16, max_lines=2)
        self.assertGreater(n_orphan(raw), 0)         # 配分前は 5 セルとも「…デスク」の「ク」だけの最終行になる
        self.assertEqual(n_orphan(bal), 0)
        self.assertAlmostEqual(sum(bal), 1136, delta=0.5)

    def test_fit_layout_reports_orphans_and_prefers_orphan_free_size(self):
        cols = ["項目", "内容"]
        rows = [["A", "あ" * 26 + "ク"] for _ in range(3)]
        r = autofit.fit_table_layout(cols, rows, RECT, 660, PARAMS | {"col_widths": [1, 1]}, set())
        self.assertIn("orphans", r)
        self.assertEqual(r["orphans"], 0)           # 固定の列幅でも、サイズを 2px 以内で縮めて避ける

    def test_row_border_is_counted_in_total_height(self):
        s = table_slide(6, "短い文")
        r = autofit.fit_table_layout(s["columns"], s["rows"], RECT, 660, PARAMS, set())
        self.assertAlmostEqual(r["total_h"], r["header_h"] + 6 * (r["row_h"] + autofit.TABLE_ROW_BORDER), delta=1.0)

    def test_html_keeps_id_like_words_together(self):
        self.assertEqual(b.esc_ids_nowrap("D-04と<b>"), '<span style="white-space:nowrap">D-04</span>と&lt;b&gt;')
        self.assertEqual(b.esc_ids_nowrap("通常の文"), "通常の文")
        self.assertNotIn("nowrap", b.esc_ids_nowrap("A" + "-b" * 20))     # 長すぎる語は対象外


class FitTableLayoutTests(unittest.TestCase):
    def fit(self, slide, bottom=660, fixed=(), **params):
        p = dict(PARAMS)
        p.update(params)
        return autofit.fit_table_layout(slide["columns"], slide["rows"], RECT, bottom, p, set(fixed))

    def test_short_table_keeps_defaults(self):
        r = self.fit(table_slide(4, "短い"))
        self.assertEqual((r["size"], r["header_size"], r["header_h"], r["pad_y"]), (17, 19, 52, 10))
        self.assertEqual(r["row_h"], 58)
        self.assertEqual(r["overflow"], 0)

    def test_widths_sum_to_total_and_are_positive(self):
        r = self.fit(table_slide(5, "これは少し長めの説明文です。"))
        self.assertAlmostEqual(sum(r["col_widths"]), 1136, places=0)
        self.assertTrue(all(w > 40 for w in r["col_widths"]))
        self.assertTrue(r["auto_widths"])

    def test_short_id_column_is_not_broken(self):
        s = table_slide(6, "あ" * 40)
        s["rows"][0][0] = "AP-01"
        s["columns"][0] = "ID"
        r = self.fit(s)
        need = ja_text.estimate_lines("AP-01", r["size"], r["col_widths"][0] - 32)
        self.assertEqual(need, 1)

    def test_long_text_column_gets_the_most_width_but_not_all(self):
        s = {"columns": ["項目", "説明", "担当"], "rows": [["A", "あ" * 60, "営業"] for _ in range(4)]}
        r = self.fit(s)
        w = r["col_widths"]
        self.assertGreater(w[1], w[0] * 2)
        self.assertGreater(w[0], 60)

    def test_twelve_rows_of_short_text_fit_by_shrinking_row_height(self):
        r = self.fit(table_slide(12, "短い文"))
        self.assertEqual(r["overflow"], 0)
        self.assertEqual(r["size"], 17)          # 文字は縮めず、行高と余白で収める
        self.assertLess(r["row_h"], 58)
        self.assertLessEqual(r["total_h"], r["avail"] + 2.0)

    def test_dense_table_shrinks_text_never_below_floor(self):
        r = self.fit(table_slide(8, "あ" * 60))
        self.assertGreaterEqual(r["size"], 12)
        r2 = self.fit(table_slide(30, "あ" * 40))
        self.assertEqual(r2["size"], 12)
        self.assertGreater(r2["overflow"], 0)
        self.assertLess(r2["rows_fit"], 30)

    def test_no_cell_wraps_to_three_lines_when_avoidable(self):
        r = self.fit(table_slide(5, "あ" * 45))
        self.assertLessEqual(max(r["lines"]), 2)

    def test_header_is_two_larger_than_body(self):
        r = self.fit(table_slide(8, "あ" * 30))
        self.assertEqual(r["header_size"], r["size"] + 2)

    def test_explicit_cell_size_is_not_changed(self):
        r = self.fit(table_slide(8, "あ" * 60), fixed={"cell_size"}, cell_size=15)
        self.assertEqual(r["size"], 15)

    def test_given_col_widths_are_used_as_ratio(self):
        r = self.fit(table_slide(3, "x", ncols=3), fixed={"col_widths"}, col_widths=[1, 2, 1])
        self.assertEqual(r["col_widths"], [284.0, 568.0, 284.0])
        self.assertFalse(r["auto_widths"])

    def test_explicit_row_h_is_not_squeezed(self):
        r = self.fit(table_slide(12, "短い"), fixed={"row_h"}, row_h=58)
        self.assertEqual(r["row_h"], 58)
        self.assertGreater(r["overflow"], 0)       # 動かさないので収まらない → 警告の材料

    def test_smaller_rect_is_respected(self):
        # 合成スライド用: 幅・下端を小さい矩形で渡せる
        s = table_slide(6, "あ" * 20, ncols=3)
        p = dict(PARAMS)
        r = autofit.fit_table_layout(s["columns"], s["rows"], {"x": 0, "y": 100, "w": 500}, 400, p, set())
        self.assertAlmostEqual(sum(r["col_widths"]), 500, places=0)
        self.assertEqual(r["avail"], 300)

    def test_uniform_row_height_when_some_rows_wrap(self):
        s = table_slide(4, "短い")
        s["rows"][2][1] = "あ" * 60
        r = self.fit(s)
        self.assertGreaterEqual(r["row_h"], 58)
        self.assertEqual(r["row_h"], max(58, max(r["lines"]) * r["size"] * 1.35 + 20))


class ResolveStyleTests(unittest.TestCase):
    def test_nostyle_table_gets_col_widths_and_marker(self):
        st = resolve(table_slide(6, "これは少し長めの説明文です。"))
        tr = st["table"]
        self.assertTrue(tr["col_widths"])
        self.assertTrue(tr["_auto_widths"])
        self.assertAlmostEqual(sum(tr["col_widths"]), tr["w"], places=0)

    def test_explicit_style_is_untouched(self):
        s = table_slide(8, "あ" * 60, style={"table": {"cell_size": 16, "header_size": 18, "row_h": 60, "col_widths": [1, 1, 1, 1],
                                                       "header_h": 50, "pad_y": 9}})
        tr = resolve(s)["table"]
        self.assertEqual((tr["cell_size"], tr["header_size"], tr["row_h"], tr["col_widths"], tr["header_h"], tr["pad_y"]),
                         (16, 18, 60, [1, 1, 1, 1], 50, 9))
        self.assertNotIn("_auto_widths", tr)

    def test_layout_overrides_are_explicit_too(self):
        s = table_slide(8, "あ" * 60)
        st = resolve(s, layout_overrides={"table": {"table": {"cell_size": 15}}})
        self.assertEqual(st["table"]["cell_size"], 15)

    def test_partial_explicit_still_fits_the_rest(self):
        # cell_size だけ明示 → 列幅・行高は自動で決まる
        s = table_slide(7, "あ" * 40, style={"table": {"cell_size": 14}})
        tr = resolve(s)["table"]
        self.assertEqual(tr["cell_size"], 14)
        self.assertTrue(tr["_auto_widths"])

    def test_autofit_false_changes_nothing(self):
        s = table_slide(12, "あ" * 40)
        off = resolve(s, autofit=False)["table"]
        self.assertEqual((off["cell_size"], off["row_h"], off["col_widths"]), (17, 58, None))
        self.assertNotIn("_auto_widths", off)
        s2 = table_slide(12, "あ" * 40, autofit=False)
        self.assertEqual(resolve(s2)["table"]["cell_size"], 17)

    def test_density_presets(self):
        s = table_slide(5, "短い")
        self.assertEqual(resolve(s, density="read")["table"]["cell_size"], 14)
        self.assertEqual(resolve(s)["table"]["cell_size"], 17)
        self.assertEqual(resolve(s, density="talk")["table"]["cell_size"], 20)
        self.assertEqual(resolve(s, density="read")["table"]["header_size"], 16)

    def test_slide_density_overrides_meta(self):
        s = table_slide(5, "短い", density="read")
        self.assertEqual(resolve(s, density="talk")["table"]["cell_size"], 14)

    def test_explicit_wins_over_density(self):
        s = table_slide(5, "短い", style={"table": {"cell_size": 16}})
        self.assertEqual(resolve(s, density="read")["table"]["cell_size"], 16)

    def test_talk_is_upper_limit_and_shrinks_when_dense(self):
        s = table_slide(9, "あ" * 25)
        tr = resolve(s, density="talk")["table"]
        self.assertLessEqual(tr["cell_size"], 20)
        self.assertGreaterEqual(tr["cell_size"], 15)

    def test_conclusion_band_lowers_the_bottom(self):
        a = resolve(table_slide(7, "短い文"))["_fit"]["info"]["table"]
        b_ = resolve(table_slide(7, "短い文", conclusion="結論です"))["_fit"]["info"]["table"]
        self.assertLess(b_["avail"], a["avail"])
        self.assertLessEqual(b_["total_h"], b_["avail"] + 2.0)

    def test_result_is_cached_and_stable(self):
        s = table_slide(7, "あ" * 30)
        a = resolve(s)["table"]
        c = resolve(s)["table"]
        self.assertEqual(a, c)


class IssueTests(unittest.TestCase):
    def issues(self, slide, **meta):
        st = resolve(slide, **meta)
        return [(lv, code) for lv, code, _ in st["_fit"]["issues"]], st["_fit"]["issues"]

    def test_overflow_warns_with_how_to_fix(self):
        lv, full = self.issues(table_slide(30, "あ" * 40))
        self.assertIn(("warn", "table-overflow"), lv)
        text = [t for _, c, t in full if c == "table-overflow"][0]
        self.assertIn("{label}", text)
        self.assertIn("12px", text)
        self.assertIn("2 枚に分ける", text)

    def test_two_step_shrink_gives_note_only(self):
        lv, _ = self.issues(table_slide(8, "あ" * 40))
        self.assertIn(("note", "table-shrunk"), lv)
        self.assertNotIn(("warn", "table-overflow"), lv)

    def test_small_table_has_no_issues(self):
        lv, _ = self.issues(table_slide(4, "短い"))
        self.assertEqual(lv, [])

    def test_explicit_size_overflow_mentions_style(self):
        s = table_slide(14, "あ" * 40, style={"table": {"cell_size": 17, "row_h": 58}})
        _, full = self.issues(s)
        text = [t for _, c, t in full if c == "table-overflow"][0]
        self.assertIn("style.table", text)

    def test_autofit_off_still_warns_with_real_estimate(self):
        lv, _ = self.issues(table_slide(8, "あ" * 60), autofit=False)
        self.assertIn(("warn", "table-overflow"), lv)

    def test_check_overflow_prints_label_with_slide_number(self):
        s = table_slide(30, "あ" * 40)
        deck = deck_of(s)
        st = b.resolve_style(LAYOUT, deck, s)
        with quiet() as err:
            b._check_overflow(s, st, 4, "table")
        self.assertIn("5枚目（type=table）", err.getvalue())
        self.assertIn("warning:", err.getvalue())


class TitleFitTests(unittest.TestCase):
    def title_st(self, title, **kw):
        s = {"type": "bullets", "title": title, "bullets": ["a"], **kw}
        return resolve(s)

    def test_short_title_keeps_cap(self):
        self.assertEqual(self.title_st("短いタイトル")["title"]["size"], 36)

    def test_long_title_shrinks_stepwise(self):
        st = self.title_st("あ" * 34)       # 36px だと 1136/36=31 字で折れる
        size = st["title"]["size"]
        self.assertLess(size, 36)
        self.assertGreaterEqual(size, 28)
        self.assertEqual(ja_text.estimate_lines("あ" * 34, size, 1136, ja_text.heading_fonts(), True), 1)
        self.assertEqual(st["_fit"]["issues"][0][1] if st["_fit"]["issues"] else "title-shrunk", "title-shrunk")

    def test_too_long_title_warns_at_floor(self):
        st = self.title_st("あ" * 60)
        self.assertEqual(st["title"]["size"], 28)
        self.assertIn("title-overflow", [c for _, c, _ in st["_fit"]["issues"]])

    def test_explicit_title_size_is_kept_and_warned(self):
        st = self.title_st("あ" * 45, style={"title": {"size": 36}})
        self.assertEqual(st["title"]["size"], 36)
        self.assertIn("title-overflow", [c for _, c, _ in st["_fit"]["issues"]])

    def test_lead_two_lines_does_not_touch_body(self):
        st = resolve({"type": "bullets", "title": "t", "lead": "あ" * 62, "bullets": ["a"]})
        lead = st["lead"]
        lines = ja_text.estimate_lines("あ" * 62, lead["size"], lead["w"])
        self.assertLessEqual(lead["y"] + lines * lead["size"] * lead["line_height"], st["body"]["y"])

    def test_status_table_narrow_title(self):
        st = resolve({"type": "status_table", "title": "あ" * 21, "columns": ["a", "b", "c", "d"], "rows": []})
        self.assertLess(st["title"]["size"], 36)       # 幅 690 では 21 字が 36px で折れる

    def test_autofit_false_leaves_title(self):
        st = resolve({"type": "bullets", "title": "あ" * 34, "bullets": ["a"]}, autofit=False)
        self.assertEqual(st["title"]["size"], 36)


class BuildIntegrationTests(unittest.TestCase):
    def build(self, deck, *extra):
        d = tempfile.mkdtemp()
        (Path(d) / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), d, *extra], capture_output=True, text=True, encoding="utf-8")
        return Path(d), r

    def test_html_uses_fixed_layout_and_pptx_has_same_widths(self):
        s = table_slide(6, "これは少し長めの説明文です。")
        d, r = self.build(deck_of(s))
        self.assertEqual(r.returncode, 0, r.stderr)
        html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
        self.assertIn("width:100%;border-collapse:collapse;table-layout:fixed", html)
        from pptx import Presentation
        prs = Presentation(str(next((d / "build").glob("*.pptx"))))
        tbl = [sh for sh in prs.slides[0].shapes if sh.has_table][0].table
        px = [c.width / 9525 for c in tbl.columns]
        st = resolve(s)["table"]
        unit = st["w"] / sum(st["col_widths"])
        for got, want in zip(px, st["col_widths"]):
            self.assertAlmostEqual(got, want * unit, delta=1.0)

    def test_explicit_widths_html_unchanged(self):
        s = table_slide(3, "x", ncols=3, style={"table": {"col_widths": [1, 2, 1]}})
        d, r = self.build(deck_of(s), "--html")
        html = next((d / "build").glob("*.html")).read_text(encoding="utf-8")
        self.assertNotIn("width:100%;border-collapse:collapse;table-layout:fixed", html)

    def test_overflow_is_reported_in_build_output(self):
        d, r = self.build(deck_of(table_slide(30, "あ" * 40)), "--html")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("12px まで縮めても", r.stderr)

    def test_bad_density_fails_build_with_message(self):
        d, r = self.build(deck_of(table_slide(3, "x"), density="big"), "--html")
        self.assertEqual(r.returncode, 1)
        self.assertIn("meta.density", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TableSemanticsTests(unittest.TestCase):
    """表のセルの意味づけ: 行の emphasis と セルの tone。既存の書き方（配列の行）はそのまま通る。"""

    def deck(self, rows):
        return deck_of({"type": "table", "title": "表", "columns": ["項目", "評価"], "rows": rows})

    def test_normalize_moves_emphasis_and_keeps_cells(self):
        d = self.deck([["A", {"text": "高", "tone": "bad"}], {"cells": ["B", "低"], "emphasis": True}])
        theme = b.load_theme("default", b.theme_dirs(None))
        with quiet():
            b.validate_deck(d, LAYOUT, theme, None)
        s = d["slides"][0]
        self.assertEqual(s["rows"], [["A", {"text": "高", "tone": "bad"}], ["B", "低"]])
        self.assertEqual(s["_row_emphasis"], [1])

    def test_unknown_tone_fails_with_candidates(self):
        d = self.deck([["A", {"text": "高", "tone": "red"}]])
        theme = b.load_theme("default", b.theme_dirs(None))
        with self.assertRaises(SystemExit) as cm:
            with quiet():
                b.validate_deck(d, LAYOUT, theme, None)
        self.assertIn("good / warn / bad / accent / muted", str(cm.exception))

    def test_row_without_cells_fails(self):
        d = self.deck([{"emphasis": True}])
        theme = b.load_theme("default", b.theme_dirs(None))
        with self.assertRaises(SystemExit) as cm:
            with quiet():
                b.validate_deck(d, LAYOUT, theme, None)
        self.assertIn("cells", str(cm.exception))

    def test_autofit_accepts_dict_rows(self):
        s = {"type": "table", "title": "t", "columns": ["a", "b"], "rows": [{"cells": ["x", "y"], "emphasis": True}, ["p", "q"]]}
        st = resolve(s)
        self.assertTrue(st["table"]["col_widths"])

    def test_build_renders_tone_and_emphasis_in_html_and_pptx(self):
        d = tempfile.mkdtemp()
        deck = self.deck([["A", {"text": "高", "tone": "bad"}], {"cells": ["B", "低"], "emphasis": True}])
        (Path(d) / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), d], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        html = next((Path(d) / "build").glob("*.html")).read_text(encoding="utf-8")
        self.assertIn("#B3261E", html)                      # bad の文字色
        self.assertIn("font-weight:700", html)
        from pptx import Presentation
        prs = Presentation(str(next((Path(d) / "build").glob("*.pptx"))))
        tbl = [sh for sh in prs.slides[0].shapes if sh.has_table][0].table
        run = tbl.cell(1, 1).text_frame.paragraphs[0].runs[0]
        self.assertEqual(str(run.font.color.rgb), "B3261E")
        self.assertTrue(run.font.bold)
        self.assertTrue(tbl.cell(2, 0).text_frame.paragraphs[0].runs[0].font.bold)   # 強調行


if __name__ == "__main__":
    unittest.main()

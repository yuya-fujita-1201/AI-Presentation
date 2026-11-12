#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全性と頑健性のレビュー（fin-S-01〜09）の修正のテスト。

- canvas の数値欄・色・矢じり・罫線などの型違いが、描画段の TypeError ではなく検証の fail（位置つき）になる
- ja_text.wrap_lines が行頭禁則文字の長い連続でも線形時間（通常の文の折り返しは従来と同じ）
- 取り込み系 3 ツールの PPTX の入口（展開後サイズの上限・壊れた zip / XML を 1 行のエラーに）
- pattern_engine.check_pattern が型違いの型 JSON でトレースバックにならない
- export_pdf の meta.id 検査
- dataviz / schedule / diagram の「1 ずつ下げる」ループが極端な大きさでも終わる
- 図解エンジンが巨大な row / col で格子を作らない

実行: python3 -m unittest plugins/slide-deck/tools/test_robustness.py
"""
from __future__ import annotations

import copy
import json
import math
import random
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import canvas_engine as ce  # noqa: E402
import dataviz_engine as dv  # noqa: E402
import diagram_engine as de  # noqa: E402
import export_pdf  # noqa: E402
import ja_text  # noqa: E402
import pattern_engine as pe  # noqa: E402
import pptx_import  # noqa: E402
import proposal_engine as pe_  # noqa: E402
import schedule_engine as se  # noqa: E402


# ---------------------------------------------------------------- canvas（fin-S-03）
def _shape(**kw):
    el = {"kind": "shape", "x": 10, "y": 10, "w": 100, "h": 40,
          "text": {"paragraphs": [{"runs": [{"text": "a", "size": 20, "color": "#112233"}]}]}}
    el.update(kw)
    return el


def _problems(el):
    return ce.validate_canvas_problems({"elements": [el]}, None)


class CanvasTypeTests(unittest.TestCase):
    def test_valid_element_has_no_problem(self):
        el = _shape(line={"color": "#333333", "width": 2, "tail": {"type": "triangle"}}, fill="#FFFFFF")
        self.assertEqual(_problems(el), [])

    def test_bad_numbers_are_reported_with_position(self):
        bad = [[1], {"a": 1}, True, float("nan"), float("inf"), "12", None]
        for key in ("x", "y", "w", "h", "rot"):
            for v in bad:
                with self.subTest(key=key, value=repr(v)):
                    el = _shape()
                    el[key] = v
                    msgs = _problems(el)
                    self.assertTrue(any(m.startswith(f"elements[0].{key}") for m in msgs), msgs)

    def test_bad_nested_numbers(self):
        cases = {
            "elements[0].text.paragraphs[0].runs[0].size": lambda e: e["text"]["paragraphs"][0]["runs"][0].__setitem__("size", [1]),
            "elements[0].text.paragraphs[0].lineHeightPx": lambda e: e["text"]["paragraphs"][0].__setitem__("lineHeightPx", {"a": 1}),
            "elements[0].text.paragraphs[0].spaceAfter": lambda e: e["text"]["paragraphs"][0].__setitem__("spaceAfter", True),
            "elements[0].text.paragraphs[0].marL": lambda e: e["text"]["paragraphs"][0].__setitem__("marL", float("nan")),
            "elements[0].text.paragraphs[0].indent": lambda e: e["text"]["paragraphs"][0].__setitem__("indent", [None]),
            "elements[0].line.width": lambda e: e.__setitem__("line", {"color": "#000000", "width": [3]}),
        }
        for want, mutate in cases.items():
            with self.subTest(want=want):
                el = _shape()
                mutate(el)
                self.assertTrue(any(m.startswith(want) for m in _problems(el)), _problems(el))

    def test_bad_colors_and_arrow_and_borders(self):
        for name, mutate in {
            "run color number": lambda e: e["text"]["paragraphs"][0]["runs"][0].__setitem__("color", 12345),
            "run color list": lambda e: e["text"]["paragraphs"][0]["runs"][0].__setitem__("color", [None]),
            "run color nan": lambda e: e["text"]["paragraphs"][0]["runs"][0].__setitem__("color", float("nan")),
            "line tail str": lambda e: e.__setitem__("line", {"color": "#000000", "width": 1, "tail": "arrow"}),
            "line tail list": lambda e: e.__setitem__("line", {"color": "#000000", "width": 1, "tail": [1, 2]}),
            "fill list": lambda e: e.__setitem__("fill", [[]]),
            "fill dict color number": lambda e: e.__setitem__("fill", {"color": 5}),
            "bullet color": lambda e: e["text"]["paragraphs"][0].__setitem__("bullet", {"char": "•", "color": [1]}),
            "bullet font number": lambda e: e["text"]["paragraphs"][0].__setitem__("bullet", {"char": "•", "font": 3}),
            "run font none ok": None,
            "align dict": lambda e: e["text"]["paragraphs"][0].__setitem__("align", {"a": 1}),
            "anchor number": lambda e: e["text"].__setitem__("anchor", 0),
            "geom list": lambda e: e.__setitem__("geom", [[]]),
            "adj str": lambda e: e.__setitem__("adj", "x"),
            "run text list": lambda e: e["text"]["paragraphs"][0]["runs"][0].__setitem__("text", [1, 2, 3]),
        }.items():
            with self.subTest(name=name):
                el = _shape()
                if mutate is None:
                    el["text"]["paragraphs"][0]["runs"][0]["font"] = None     # None は「指定なし」として受け付ける
                    self.assertEqual(_problems(el), [])
                    continue
                mutate(el)
                msgs = _problems(el)
                self.assertTrue(msgs and all(m.startswith("elements[0]") for m in msgs), msgs)

    def test_table_borders_and_custom_path(self):
        tbl = {"kind": "table", "x": 0, "y": 0, "cols": [100, 100],
               "rows": [{"h": 30, "cells": [{"paragraphs": [], "borders": {"r": [None]}}, {"paragraphs": [], "borders": "x"}]}]}
        msgs = _problems(tbl)
        self.assertTrue(any("borders" in m and "cells[0]" in m for m in msgs), msgs)
        self.assertTrue(any("borders" in m and "cells[1]" in m for m in msgs), msgs)
        for path in ([-1], ["x"], [{"cmds": -0.0}], [{"cmds": [[None], 1, 2]}], [{"cmds": [[{}], 1, 2]}]):
            with self.subTest(path=path):
                msgs = _problems(_shape(geom="custom", path=path))
                self.assertTrue(msgs and all("elements[0]" in m for m in msgs), msgs)

    def test_invalid_input_never_raises_in_render(self):
        """検証を通らなかった値を、描画関数に直接渡しても例外にならない（二重の防御）"""
        for el in (_shape(geom=[[]]), _shape(adj="x"), _shape(text={"anchor": {"a": 1}, "paragraphs": [{"align": []}]}),
                   _shape(line={"tail": "arrow"}), _shape(fill=[1])):
            clean = ce.sanitize_elements([el])
            self.assertTrue(clean)


# ---------------------------------------------------------------- wrap_lines（fin-S-05）
def _reference_wrap_lines(text, size_px, width_px, font=None, bold=False, loose=False):
    """修正前の wrap_lines（追い出しのたびに先頭まで戻って数える版）。折り返し結果が変わっていないことの比較用"""
    text = str(text or "")
    width_px = max(1.0, float(width_px))
    no_start = ja_text.LOOSE_NO_LINE_START if loose else ja_text.NO_LINE_START
    NO_LINE_END = ja_text.NO_LINE_END
    lines = []
    for raw in text.split("\n"):
        if raw == "":
            lines.append("")
            continue
        cur: list = []
        widths: list = []
        w = 0.0

        def flush(keep=()):
            nonlocal cur, widths, w
            lines.append("".join(cur).rstrip(" "))
            cur = [t for t, _ in keep]
            widths = [x for _, x in keep]
            w = sum(widths)

        toks = []
        for tok in ja_text._tokens(raw):
            if len(tok) > 1 and tok.startswith("【") and sum(ja_text.char_em(c, font, bold) for c in tok) * size_px > width_px:
                toks.extend(tok)
            else:
                toks.append(tok)
        for tok in toks:
            tw = sum(ja_text.char_em(c, font, bold) for c in tok) * size_px
            if cur and w + tw > width_px:
                if tok[0] in no_start:
                    k = len(cur) - 1
                    while k > 0 and cur[k][0] in no_start:
                        k -= 1
                    if k > 0:
                        carry = list(zip(cur[k:], widths[k:]))
                        cur, widths = cur[:k], widths[:k]
                        flush(carry)
                    else:
                        cur.append(tok)
                        widths.append(tw)
                        w += tw
                        continue
                elif cur[-1][-1] in NO_LINE_END and len(cur) > 1:
                    carry = [(cur[-1], widths[-1])]
                    cur, widths = cur[:-1], widths[:-1]
                    flush(carry)
                else:
                    flush()
                if tok == " ":
                    continue
            if len(tok) > 1 and tw > width_px:
                for c in tok:
                    cw = ja_text.char_em(c, font, bold) * size_px
                    if cur and w + cw > width_px:
                        flush()
                    cur.append(c)
                    widths.append(cw)
                    w += cw
                continue
            cur.append(tok)
            widths.append(tw)
            w += tw
        lines.append("".join(cur))
    return lines or [""]


class WrapLinesTests(unittest.TestCase):
    def test_long_no_start_run_is_linear(self):
        for text in ("。" * 40000, "あ" + "、。" * 20000, "ab" + "、" * 30000 + "cd"):
            t = time.time()
            lines = ja_text.wrap_lines(text, 16, 300)
            self.assertLess(time.time() - t, 1.0, "禁則文字の連続で時間がかかりすぎる")
            self.assertEqual("".join(lines), text)

    def test_same_result_as_reference(self):
        rnd = random.Random(7)
        pool = sorted(ja_text.NO_LINE_START)[:30] + list("あいうえお漢字カタカナabcdefg 12345（「【") + ["\n"]
        texts = ["これは、とても長い文章です。「括弧」も含みます。だから、折り返し位置が、変わらないはずです。",
                 "ねえ…！？ー、。。。ー初めてのサーバーを立てる。", "ab。。。。。。。cdefg、、、、、、hij",
                 "【要確認: 日付を確かめる】それから、、、続く。", "）」』】 closing 「opening（text hello world"]
        for _ in range(250):
            texts.append("".join(rnd.choice(pool) for _ in range(rnd.randint(1, 50))))
        for text in texts:
            for size, width in ((12, 80), (16, 200), (20, 120), (14, 33), (18, 18)):
                for loose in (False, True):
                    self.assertEqual(ja_text.wrap_lines(text, size, width, loose=loose),
                                     _reference_wrap_lines(text, size, width, loose=loose), (text, size, width, loose))


# ---------------------------------------------------------------- 取り込み（fin-S-06）
def _zip_with(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


class ImportGuardTests(unittest.TestCase):
    def test_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "big.pptx"
            _zip_with(p, {"ppt/media/junk.bin": b"\0" * 5000})
            with mock.patch.object(pptx_import, "MAX_PPTX_ENTRY", 1000):
                with self.assertRaises(pptx_import.PptxError) as cm:
                    pptx_import.check_pptx_archive(p)
            self.assertIn("PPTX が大きすぎます", str(cm.exception))
            self.assertIn("ppt/media/junk.bin", str(cm.exception))
            _zip_with(p, {f"ppt/media/{i}.bin": b"\0" * 400 for i in range(5)})
            with mock.patch.object(pptx_import, "MAX_PPTX_TOTAL", 1500):
                with self.assertRaises(pptx_import.PptxError) as cm:
                    pptx_import.check_pptx_archive(p)
            self.assertIn("展開後の合計", str(cm.exception))
            pptx_import.check_pptx_archive(p)     # 既定の上限なら通る
            self.assertEqual((pptx_import.MAX_PPTX_TOTAL, pptx_import.MAX_PPTX_ENTRY), (500 * 2 ** 20, 100 * 2 ** 20))

    def test_broken_files_become_one_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.pptx"
            p.write_text("not a zip")
            with self.assertRaises(pptx_import.PptxError) as cm:
                pptx_import.check_pptx_archive(p)
            self.assertIn("PPTX が壊れているか大きすぎます", str(cm.exception))
            with self.assertRaises(pptx_import.PptxError) as cm:
                pptx_import.Importer(p)
            self.assertIn("PPTX が壊れているか大きすぎます", str(cm.exception))
        with self.assertRaises(pptx_import.PptxError) as cm:
            with pptx_import.pptx_errors():
                pptx_import._xml(b"<a><b></a>")
        self.assertIn("XMLSyntaxError", str(cm.exception))
        self.assertNotIn("\n", str(cm.exception))

    def test_three_tools_report_without_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.pptx"
            p.write_text("not a zip")
            runs = [
                ["pptx_import.py", str(p), "--into", str(Path(d) / "out")],
                ["theme_from_sample.py", str(p), "--name", "robust-test", "--dir", str(Path(d) / "th")],
                ["pattern_from_pptx.py", str(p), "--slide", "1", "--name", "robust-test", "--dir", str(Path(d) / "pat")],
            ]
            for args in runs:
                with self.subTest(tool=args[0]):
                    r = subprocess.run([sys.executable, "-I", str(TOOLS / args[0]), *args[1:]], capture_output=True, text=True, timeout=60,
                                       env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": ""})
                    self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stderr)
                    self.assertIn("PPTX が壊れているか大きすぎます", r.stderr)

    def test_theme_from_sample_keeps_accepting_non_pptx(self):
        """PPTX 以外（HTML）は展開後サイズの検査を通らず、従来どおり読める"""
        with tempfile.TemporaryDirectory() as d:
            html = Path(d) / "s.html"
            html.write_text("<html><body style='background:#0F3D6E;color:#fff'><h1 style='color:#E4A000'>x</h1></body></html>", encoding="utf-8")
            r = subprocess.run([sys.executable, "-I", str(TOOLS / "theme_from_sample.py"), str(html), "--name", "robust-test",
                                "--dir", str(Path(d) / "th")], capture_output=True, text=True, timeout=60, env={"PYTHONDONTWRITEBYTECODE": "1"})
            self.assertNotIn("PPTX が", r.stdout + r.stderr)
            self.assertNotIn("Traceback", r.stderr)


# ---------------------------------------------------------------- pattern check（fin-S-08）
def _bundled(name):
    return json.loads((TOOLS.parent / "templates" / "patterns" / f"{name}.json").read_text(encoding="utf-8"))


def _find_first(obj, pred, path=()):
    if pred(obj, path):
        return path
    if isinstance(obj, dict):
        for k, v in obj.items():
            r = _find_first(v, pred, path + (k,))
            if r is not None:
                return r
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            r = _find_first(v, pred, path + (i,))
            if r is not None:
                return r
    return None


def _set(obj, path, val):
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = val


class PatternCheckTests(unittest.TestCase):
    def _errs(self, pat):
        errs, _warns = pe.check_pattern(pat, None)
        return errs

    def test_bundled_patterns_still_clean(self):
        for p in sorted((TOOLS.parent / "templates" / "patterns").glob("*.json"))[:3]:
            pat = json.loads(p.read_text(encoding="utf-8"))
            errs, warns = pe.check_pattern(pat, None, quick=True)
            self.assertEqual((errs, warns), ([], []), p.name)

    def test_unhashable_values_become_errors(self):
        base = _bundled("funnel")
        cmd = _find_first(base, lambda o, p: isinstance(o, list) and o and o[0] == "M" and len(p) > 2 and p[-2] == "cmds")
        geom = _find_first(base, lambda o, p: p and p[-1] == "geom" and isinstance(o, str))
        self.assertIsNotNone(cmd)
        self.assertIsNotNone(geom)
        cases = [(cmd + (0,), {"text": "x"}), (cmd + (0,), [None]), (geom, []), (geom, {"text": "x"})]
        for path, val in cases:
            with self.subTest(path=path, val=val):
                pat = copy.deepcopy(base)
                _set(pat, path, val)
                errs = self._errs(pat)
                self.assertTrue(errs)

    def test_slot_shape_errors(self):
        pat = _bundled("compare-options")
        lst = next(k for k, d in pat["slots"].items() if d.get("kind") in ("list", "records"))
        for field, val in (("min", {"text": None}), ("max", [1]), ("kind", [])):
            with self.subTest(field=field):
                p = copy.deepcopy(pat)
                p["slots"][lst][field] = val
                self.assertTrue(self._errs(p))
        rec = _bundled("funnel")
        recs = next((k for k, d in rec["slots"].items() if d.get("kind") == "records"), None)
        if recs:
            rec["slots"][recs]["fields"] = [1, 2, 3]
            errs = self._errs(rec)
            self.assertTrue(any(f"slots.{recs}.fields" in m for m in errs), errs)

    def test_repeat_with_object_name(self):
        pat = _bundled("compare-options")
        path = _find_first(pat, lambda o, p: p and p[-1] == "repeat" and isinstance(o, str))
        self.assertIsNotNone(path)
        _set(pat, path, {"text": "x"})
        self.assertTrue(any("repeat" in m for m in self._errs(pat)))

    def test_internal_type_error_is_wrapped(self):
        with mock.patch.object(pe, "_check_pattern_impl", side_effect=TypeError("unhashable type: 'dict'")):
            errs, warns = pe.check_pattern({"name": "x"})
        self.assertEqual(warns, [])
        self.assertEqual(len(errs), 1)
        self.assertIn("パターンの構造を検査できません", errs[0])
        self.assertIn("見直してください", errs[0])


# ---------------------------------------------------------------- export_pdf（fin-S-09）
class ExportPdfIdTests(unittest.TestCase):
    def test_id_problem(self):
        for bad in ("../../x", "..", ".", "a/b", "a\\b", "a:b", 'a"b', "a|b", "a\x00b", "a?b", "a*b", "<a>"):
            with self.subTest(id=bad):
                self.assertTrue(export_pdf.deck_id_problem(bad), bad)
        for ok in ("template-sample", "デッキ2026", "v1..2", "a b", "x.y"):
            with self.subTest(id=ok):
                self.assertIsNone(export_pdf.deck_id_problem(ok), ok)

    def test_no_build_rejects_traversal_id(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "deck.json").write_text(json.dumps({"meta": {"id": "../../x", "title": "t"}, "slides": []}), encoding="utf-8")
            r = subprocess.run([sys.executable, "-I", str(TOOLS / "export_pdf.py"), d, "--no-build"], capture_output=True, text=True, timeout=60,
                               env={"PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(r.returncode, 1)
            self.assertIn("meta.id", r.stderr)
            self.assertNotIn("Traceback", r.stderr)


# ---------------------------------------------------------------- 極端な大きさのループ（fin-S-01）
class LoopBoundTests(unittest.TestCase):
    EXTREME = (1e6, 1e15, 1e300, 1e308, float("inf"), float("nan"), -1e308)

    def test_dataviz_fit_labels_and_cat_labels(self):
        ctx = pe_.Ctx({"colors": {"background": "#FFFFFF", "text": "#000000", "muted": "#666666", "primary": "#0F3D6E", "accent": "#007D96",
                                  "surface": "#EEEEEE", "border": "#CCCCCC", "on_primary": "#FFFFFF", "heading_text": "#0F3D6E"},
                       "fonts": {"heading": "Meiryo", "body": "Meiryo"}})
        t = time.time()
        for size in self.EXTREME:
            for smin in (10, 1e308, -1e308, float("nan")):
                dv._fit_labels(ctx, ["1,234,567 件"] * 3, ["1,234,567"] * 3, 20, size, smin)
                dv._cat_labels(ctx, ["カテゴリ名その一", "カテゴリ名その二"], 40, size, smin)
                dv._hbar_fit({"bar_h_max": 44}, 30, 2, size, smin)
        self.assertLess(time.time() - t, 8.0)

    def test_dataviz_normal_values_unchanged(self):
        self.assertEqual(dv._cap_size(18, 10), 18.0)
        self.assertEqual(dv._cap_size(200, 10), 200.0)
        self.assertEqual(dv._cap_size(1e308, 10), dv.SIZE_CAP)
        self.assertEqual(dv._smin(12), 12.0)
        self.assertEqual(dv._smin(float("nan")), 1.0)

    def test_schedule_fit_size(self):
        self.assertEqual(se._fit_size("短い", 500, 20, 10), 20)           # 収まるときはそのまま
        self.assertEqual(se._fit_size("あ" * 40, 100, 20, 10), 10)        # 収まらなければ下限まで
        t = time.time()
        for size in self.EXTREME:
            se._fit_size("日本語のラベル", 120, size, 10)
            se._fit_size("日本語のラベル", 120, 20, size)
        self.assertLess(time.time() - t, 3.0)

    def test_diagram_fit_font_size(self):
        self.assertEqual(de.fit_font_size("短い", 14, 200, 40)[0], 14.0)
        t = time.time()
        for size in self.EXTREME:
            de.fit_font_size("あ" * 30, size, 100, 30)
            de.fit_font_size("あ" * 30, 14, 100, 30, min_size=size)
        self.assertLess(time.time() - t, 5.0)


# ---------------------------------------------------------------- 格子（fin-S-02）
class GridLimitTests(unittest.TestCase):
    AREA = {"x": 72, "y": 190, "w": 1136, "h": 468, "node_wr": 0.78, "node_hr": 0.62}

    def test_grid_clamps_huge_counts(self):
        t = time.time()
        g = de.Grid(0, 0, 100, 100, 10 ** 19, 20_000_000)
        self.assertEqual((g.rows, g.cols), (de.GRID_HARD_MAX, de.GRID_HARD_MAX))
        self.assertEqual(de.Grid(0, 0, 100, 100, float("nan"), float("inf")).rows, 1)
        self.assertLess(time.time() - t, 1.0)
        g = de.Grid(0, 0, 100, 100, 3, 4)
        self.assertEqual((g.rows, g.cols), (3, 4))

    def test_layout_reports_error_instead_of_building_grid(self):
        for row, col in ((12345678901234567890, 0), (20_000_000, 0), (0, 5_000_000)):
            slide = {"type": "architecture", "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0},
                                                       {"id": "b", "label": "B", "row": row, "col": col}],
                     "edges": [{"from": "a", "to": "b"}]}
            t = time.time()
            geo = de.layout_grid_diagram(slide, "architecture", self.AREA)
            self.assertLess(time.time() - t, 2.0)
            errs = [d for d in geo["diagnostics"] if d.get("severity") == "error" or d.get("level") == "error"]
            self.assertTrue(errs, geo["diagnostics"])
            self.assertTrue(any("40" in d.get("message", "") for d in errs), errs)
            self.assertLessEqual(geo["grid"].rows, de.GRID_MAX_CELLS)
            self.assertLessEqual(geo["grid"].cols, de.GRID_MAX_CELLS)
            self.assertIn("a", geo["nodes"])
            self.assertNotIn("b", geo["nodes"])

    def test_rows_key_is_clamped_too(self):
        slide = {"type": "architecture", "rows": 10 ** 12, "cols": 10 ** 12,
                 "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0}]}
        geo = de.layout_grid_diagram(slide, "architecture", self.AREA)
        self.assertLessEqual(geo["grid"].rows, de.GRID_MAX_CELLS)
        self.assertTrue(any(d.get("code") == "invalid-position" for d in geo["diagnostics"]))

    def test_normal_diagram_unchanged(self):
        slide = {"type": "architecture", "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": 2, "col": 3}],
                 "edges": [{"from": "a", "to": "b"}]}
        geo = de.layout_grid_diagram(slide, "architecture", self.AREA)
        self.assertEqual((geo["grid"].rows, geo["grid"].cols), (3, 4))
        self.assertFalse([d for d in geo["diagnostics"] if d.get("code") == "invalid-position"])


if __name__ == "__main__":
    unittest.main()

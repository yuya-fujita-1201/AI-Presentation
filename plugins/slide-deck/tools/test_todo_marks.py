#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【要確認】マーカーの強調表示（todo_marks.py）のテスト。HTML と PPTX の両方で、全タイプ共通に効くこと。

実行: python3 -m unittest plugins/slide-deck/tools/test_todo_marks.py
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
import todo_marks as tm  # noqa: E402

PY = sys.executable


def build(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="todo_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
    return d, r


def html_slides(d):
    h = (d / "build" / "d.html").read_text(encoding="utf-8")
    return re.findall(r'<section class="slide".*?</section>', h, re.S)


def pptx_xml(d):
    z = zipfile.ZipFile(d / "build" / "d.pptx")
    names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)), key=lambda s: int(re.findall(r"\d+", s)[0]))
    return [z.read(n).decode("utf-8") for n in names]


def painted_runs(x):
    """マーカー全体だけを持つ run のうち、太字＋色つきのもの。"""
    runs = re.findall(r"<a:r>(?:(?!</a:r>).)*?</a:r>", x)
    out = [r for r in runs if "【要確認" in r]
    return out, [r for r in out if 'b="1"' in r and re.search(r'<a:solidFill><a:srgbClr val="(9A3412|FCD34D)"', r)]


class HtmlMarkTest(unittest.TestCase):
    def test_text_node_only(self):
        out = tm.html_mark('<div title="【要確認】">前【要確認: 出典】後</div>')
        self.assertIn('title="【要確認】"', out)                       # 属性値は触らない
        self.assertIn('前<mark class="todo">【要確認: 出典】</mark>後', out)

    def test_half_width_colon_and_plain(self):
        out = tm.html_mark("<p>a【要確認:x】b【要確認】</p>")
        self.assertEqual(out.count('<mark class="todo">'), 2)

    def test_skips_code_title_script(self):
        for tag in ("pre", "code", "title", "script", "style"):
            src = f"<{tag}>【要確認】</{tag}>"
            self.assertEqual(tm.html_mark(src), src, tag)
        # 閉じたあとは対象に戻る
        self.assertIn("<mark", tm.html_mark("<pre>【要確認】</pre><p>【要確認】</p>"))

    def test_svg_text_uses_tspan_and_svg_title_skipped(self):
        out = tm.html_mark('<svg><title>【要確認】</title><text x="1">A【要確認】</text></svg>')
        self.assertIn("<title>【要確認】</title>", out)
        self.assertIn('<tspan class="todo" fill="#9A3412" font-weight="700">【要確認】</tspan>', out)
        self.assertNotIn("<mark", out)

    def test_no_marker_unchanged(self):
        s = "<p>普通</p>"
        self.assertIs(tm.html_mark(s), s)

    def test_colors_from_layout(self):
        c = tm.colors({"todo_color": "#112233", "todo_bg": "bad"})
        self.assertEqual(c["todo_color"], "#112233")
        self.assertEqual(c["todo_bg"], tm.DEFAULT_COLORS["todo_bg"])
        self.assertIn("#112233", tm.html_css({"todo_color": "#112233"}))


class SplitMarkerTest(unittest.TestCase):
    """折り返しの改行でマーカーが割れても、行ごとに分けて強調する（s3-C-01 / s3-A-06）。"""

    def test_html_br_split(self):
        out = tm.html_mark("<div>顧客管理基盤【要確<br>認】</div>")
        self.assertEqual(out, '<div>顧客管理基盤<mark class="todo">【要確</mark><br><mark class="todo">認】</mark></div>')

    def test_html_canvas_paragraphs_split(self):
        src = '<p style="a"><span style="x">注釈【要確認: 経理に</span></p><p style="a"><span style="x">確認して数字をもらう】です</span></p>'
        out = tm.html_mark(src)
        self.assertIn('<mark class="todo">【要確認: 経理に</mark>', out)
        self.assertIn('<mark class="todo">確認して数字をもらう】</mark>です', out)

    def test_html_does_not_bridge_across_blocks(self):
        # li をまたぐ「【」と「】」は別の文なので、つなげない
        src = "<ul><li>前【要確</li><li>認】後</li></ul>"
        self.assertEqual(tm.html_mark(src), src)

    def test_html_unclosed_marker_untouched(self):
        src = "<p>【要確認: 閉じ忘れ<br>次の行</p>"
        self.assertEqual(tm.html_mark(src), src)

    def test_pptx_br_split(self):
        from pptx import Presentation
        from pptx.oxml.ns import qn
        prs = Presentation()
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        tf = sl.shapes.add_textbox(0, 0, 3000000, 1000000).text_frame
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = "顧客【要確"
        p.add_line_break()
        r2 = p.add_run()
        r2.text = "認: 方式】です"
        n = tm.pptx_mark(prs, {})
        self.assertEqual(n, 1)
        runs = [(r.find(qn("a:t")).text, (r.find(qn("a:rPr")) is not None and r.find(qn("a:rPr")).get("b") == "1")) for r in p._p.findall(qn("a:r"))]
        self.assertEqual(runs, [("顧客", False), ("【要確", True), ("認: 方式】", True), ("です", False)])

    def test_pptx_paragraph_per_line_split(self):
        from pptx import Presentation
        from pptx.oxml.ns import qn
        prs = Presentation()
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        tf = sl.shapes.add_textbox(0, 0, 3000000, 1000000).text_frame
        tf.paragraphs[0].add_run().text = "顧客管理基盤【要確"
        tf.add_paragraph().add_run().text = "認】"
        self.assertEqual(tm.pptx_mark(prs, {}), 1)
        painted = [r.find(qn("a:t")).text for r in sl._element.iter(qn("a:r")) if r.find(qn("a:rPr")) is not None and r.find(qn("a:rPr")).get("b") == "1"]
        self.assertEqual(painted, ["【要確", "認】"])

    def test_diagram_wrap_keeps_short_marker_whole(self):
        import diagram_engine as de
        self.assertEqual(de.wrap_text("顧客管理基盤【要確認】", 10.5, 70), ["顧客管理基盤", "【要確認】"])

    def test_ja_text_keeps_short_marker_whole(self):
        import ja_text
        self.assertEqual(ja_text.wrap_lines("顧客管理基盤【要確認】", 13, 70), ["顧客管理基", "盤", "【要確認】"])
        # 幅に収まらない長いマーカーは文字単位で折る（無限に伸ばさない）
        self.assertGreater(len(ja_text.wrap_lines("【要確認: 経理部門に確認して正式な数字をもらう】", 18, 200)), 1)


class ScanTest(unittest.TestCase):
    def test_scan_counts_slide_text_not_notes_or_code(self):
        deck = {"meta": {"title": "【要確認】"}, "slides": [
            {"type": "bullets", "title": "a", "bullets": ["x【要確認: 値】"], "notes": "【要確認】"},
            {"type": "code", "code": "【要確認】"},
            {"type": "cards", "cards": [{"heading": "h【要確認】", "body": "b"}], "style": {"x": "【要確認】"}},
        ]}
        found = tm.scan_deck(deck)
        self.assertEqual([(f["slide"], f["what"]) for f in found], [(1, "値"), (3, "")])

    def test_unknown_slide_key_not_counted(self):
        deck = {"meta": {}, "slides": [{"type": "quote", "text": "a【要確認】", "author": "誰か【要確認】"}]}
        self.assertEqual(len(tm.scan_deck(deck)), 1)

    def test_summary_note(self):
        self.assertIsNone(tm.summary_note([]))
        msg = tm.summary_note([{"slide": 1, "what": "出典", "text": ""}, {"slide": 4, "what": "", "text": ""}])
        self.assertIn("要確認が 2 件", msg)
        self.assertIn("1 枚目 1 件（出典）", msg)
        self.assertIn("4 枚目 1 件", msg)


class BuildTest(unittest.TestCase):
    SLIDES = [
        {"type": "bullets", "title": "箇条書き", "bullets": ["売上は増えた【要確認】", "コスト【要確認: 経理に確認】"]},
        {"type": "table", "title": "表", "columns": ["項目", "値"], "rows": [["A", "10【要確認】"], ["B", "20"]]},
        {"type": "cards", "title": "カード", "cards": [{"heading": "一", "body": "本文【要確認: 出典】"}, {"heading": "二【要確認】", "body": "x"},
                                                         {"heading": "三", "body": "y"}]},
        {"type": "kpi", "title": "kpi", "items": [{"label": "売上【要確認】", "value": "12", "unit": "億円"}, {"label": "利益", "value": "3", "unit": "億円"}]},
        {"type": "architecture", "title": "図", "nodes": [{"id": "a", "label": "API【要確認】", "row": 0, "col": 0},
                                                       {"id": "b", "label": "DB", "row": 0, "col": 1}], "edges": [{"from": "a", "to": "b"}]},
        {"type": "chart", "title": "chart", "chart": "bar", "categories": ["A", "B"], "series": [{"name": "s", "values": [1, 2]}], "note": "注釈【要確認: 値】"},
        {"type": "pattern", "pattern": "keyword-explain", "title": "型", "slots": {"keyword": "一言【要確認】", "points": [
            {"head": "見出し", "body": "説明【要確認: 数字】"}, {"head": "二", "body": "b"}]}},
        {"type": "composite", "title": "合成", "blocks": [{"type": "text", "text": "ブロック【要確認】"}, {"type": "callout", "text": "強調【要確認: 根拠】"}]},
        {"type": "split", "title": "分割", "panel": {"title": "パネル【要確認】", "text": "本文"}, "blocks": [{"type": "bullets", "bullets": ["項目【要確認】"]}]},
        {"type": "section", "title": "章【要確認】"},
    ]

    @classmethod
    def setUpClass(cls):
        cls.d, cls.r = build(cls.SLIDES)

    def test_build_ok_and_note(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr)
        self.assertRegex(self.r.stderr, r"note: 要確認が 1\d 件あります")
        self.assertIn("1 枚目 2 件（経理に確認）", self.r.stderr)

    def test_html_every_type(self):
        for i, s in enumerate(html_slides(self.d)):
            self.assertIn('<mark class="todo">【要確認', s, f"{i + 1} 枚目（{self.SLIDES[i]['type']}）")
            bare = re.sub(r'(aria-label|data-notes)="[^"]*"', "", s)        # 属性値（aria-label・data-notes）は強調の対象外
            self.assertEqual(len(re.findall("【要確認", bare)), len(re.findall('<mark class="todo">【要確認', bare)), f"{i + 1} 枚目")

    def test_pptx_every_type(self):
        for i, x in enumerate(pptx_xml(self.d)):
            allr, ok = painted_runs(x)
            self.assertTrue(allr, f"{i + 1} 枚目（{self.SLIDES[i]['type']}）にマーカーが無い")
            self.assertEqual(len(allr), len(ok), f"{i + 1} 枚目（{self.SLIDES[i]['type']}）: 強調されていない run がある")

    def test_pptx_dark_background_uses_on_dark_color(self):
        x = pptx_xml(self.d)[-1]      # section（濃い面・白い文字）
        self.assertIn("FCD34D", x)

    def test_runs_split_not_whole_text_colored(self):
        x = pptx_xml(self.d)[0]
        self.assertRegex(x, r"<a:t>売上は増えた</a:t>")
        self.assertRegex(x, r"<a:t>【要確認】</a:t>")


def coverage(d):
    """各スライドで、マーカーの全文字が強調されているか。[(html 全部, html 強調, pptx 全部, pptx 強調)]"""
    from pptx import Presentation
    from pptx.oxml.ns import qn
    out = []
    prs = Presentation(str(d / "build" / "d.pptx"))
    for sec, sl in zip(html_slides(d), prs.slides):
        sec = re.sub(r' (aria-label|data-notes)="[^"]*"', "", sec)
        chars, flags, depth = [], [], 0
        for tok in re.split(r"(<[^>]*>)", sec):
            if tok.startswith("<"):
                m = re.match(r"<(/?)(mark|tspan)\b", tok)
                if m:
                    depth = max(0, depth - 1) if m.group(1) else depth + (1 if "todo" in tok else 0)
                continue
            chars += list(tok)
            flags += [depth > 0] * len(tok)
        ms = list(tm.TODO_MARK.finditer("".join(chars)))
        hc = sum(all(flags[m.start():m.end()]) for m in ms)
        pt = pc = 0
        for p in sl._element.iter(qn("a:p")):
            cs, fl = [], []
            for r in p.findall(qn("a:r")):
                t, rp = r.find(qn("a:t")).text or "", r.find(qn("a:rPr"))
                cs += list(t)
                painted = rp is not None and rp.get("b") == "1" and any(c.get("val") in ("9A3412", "FCD34D") for c in rp.iter(qn("a:srgbClr")))
                fl += [painted] * len(t)
            for m in tm.TODO_MARK.finditer("".join(cs)):
                pt += 1
                pc += all(fl[m.start():m.end()])
        out.append((len(ms), hc, pt, pc))
    return out


class SplitBuildTest(unittest.TestCase):
    """狭い箱・長いマーカー・キャンバス描画の文字でも、マーカー全体が強調される（s3-C-01 / s3-C-05）。"""
    LONG = "【要確認: 経理部門に確認して正式な数字をもらう必要あり】"
    SLIDES = [
        {"type": "architecture", "title": "狭いノード", "nodes": [
            {"id": f"n{i}", "label": lb, "row": 0, "col": i} for i, lb in enumerate(
                ["顧客管理基盤【要確認】", "認証と権限管理【要確認: 方式】", "データ連携基盤【要確認】", "分析基盤", "通知サービス【要確認】"])],
         "edges": [{"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]},
        {"type": "cards", "title": "長いマーカー", "cards": [
            {"heading": "現場の実感とおおむね一致" + LONG, "body": "現場の実感とおおむね一致している数字" + LONG},
            {"heading": "B", "body": "x"}, {"heading": "C", "body": "y"}]},
        {"type": "chart", "title": "注釈", "chart": "bar", "categories": ["A", "B"], "series": [{"name": "s", "values": [1, 2]}],
         "annotations": [{"at": "A", "text": "注釈" + LONG}], "note": "注" + LONG},
        {"type": "bullets", "title": "改行つき", "bullets": ["【要確認:\n改行】", "売上は前年比20%増で推移【要確認】"]},
        {"type": "table", "title": "表", "columns": ["項目", "値"], "rows": [["売上の見込みと前提条件の整理【要確認】", "10"], ["B" + LONG, "20"]]},
    ]

    @classmethod
    def setUpClass(cls):
        cls.d, cls.r = build(cls.SLIDES)

    def test_every_marker_fully_highlighted(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr)
        for i, (h_all, h_ok, p_all, p_ok) in enumerate(coverage(self.d)):
            where = f"{i + 1} 枚目（{self.SLIDES[i]['type']}）"
            self.assertGreater(h_all, 0, where)
            self.assertEqual(h_all, h_ok, f"{where}: HTML で強調されていないマーカーがある")
            self.assertEqual(p_all, p_ok, f"{where}: PPTX で強調されていないマーカーがある")

    def test_narrow_node_keeps_short_marker_on_one_line(self):
        s = html_slides(self.d)[0]
        self.assertNotIn("【要確<br>", s)


class LayoutJsonTest(unittest.TestCase):
    """レイアウト JSON の readable_pairs / todo_* の検証（s3-C-03）。"""

    def run_layout(self, layout):
        d = Path(tempfile.mkdtemp(prefix="todo_lay_"))
        (d / "layouts").mkdir()
        (d / "layouts" / "mine.json").write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")
        (d / "deck.json").write_text(json.dumps({"meta": {"id": "d", "title": "T", "layout": "mine"},
                                                 "slides": [{"type": "bullets", "title": "t", "bullets": ["a"]}]}, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True, encoding="utf-8")

    def test_bad_readable_pairs_type_fails_with_place(self):
        r = self.run_layout({"extends": "default", "readable_pairs": {"steps": 5}})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("readable_pairs.steps", r.stderr)
        self.assertIn("mine.json", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_bad_spec_fails(self):
        r = self.run_layout({"extends": "default", "readable_pairs": {"steps": [["body", "num_color"]]}})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("readable_pairs.steps[0]", r.stderr)

    def test_bad_todo_color_warns(self):
        r = self.run_layout({"extends": "default", "todo_color": "red"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("todo_color は #RRGGBB", r.stderr)

    def test_empty_pairs_is_allowed(self):
        r = self.run_layout({"extends": "default", "readable_pairs": {"steps": []}})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("readable_pairs", r.stderr)


class SwitchTest(unittest.TestCase):
    def test_todo_marks_false_keeps_note_drops_highlight(self):
        d, r = build([{"type": "bullets", "title": "t", "bullets": ["a【要確認】"]}], todo_marks=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("<mark", html_slides(d)[0])
        self.assertNotIn("<mark", (d / "build" / "d.html").read_text(encoding="utf-8"))
        self.assertNotIn("FCD34D", pptx_xml(d)[0])
        self.assertNotIn("9A3412", pptx_xml(d)[0])
        self.assertIn("要確認が 1 件", r.stderr)

    def test_bad_value_fails(self):
        d, r = build([{"type": "bullets", "title": "t", "bullets": ["a"]}], todo_marks="no")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("meta.todo_marks", r.stderr)

    def test_no_marker_no_note(self):
        d, r = build([{"type": "bullets", "title": "t", "bullets": ["a"]}])
        self.assertNotIn("要確認が", r.stderr)


if __name__ == "__main__":
    unittest.main()

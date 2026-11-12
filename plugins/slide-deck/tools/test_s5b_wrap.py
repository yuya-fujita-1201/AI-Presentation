#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5b 語の途中で折れる文を文節の切れ目で折る（wrap_fix / build_deck.apply_wrap_fix / check_layout の wordbreak）のテスト。

実行: python3 -m unittest plugins/slide-deck/tools/test_s5b_wrap.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import check_layout as CL  # noqa: E402
import autofit  # noqa: E402
import ja_text  # noqa: E402
import wrap_fix  # noqa: E402

PY = sys.executable

# 仕様 70 の実例（語の途中で折れる文）。(文, 文字サイズ, 箱の幅)。自然な折り返しで語中折れになる組
EXAMPLES = [
    ("プラグインのファイルをアップロードする", 25, 460),                     # プラグイ／ン・アップロー／ド
    ("担当者へ手順書のブロックを共有して確認する", 25, 460),                   # 担当／者へ・ブロ／ック・確／認する
    ("手順書のブロックごとに、確認する担当者を決めて始めます", 19, 160),          # 始／めます
    ("論点ごとに整理して始めます", 22, 190),                                # 論点ごと／に整理
    ("印象でなく目的で確認した件数", 30, 200),                              # 印／象で
    ("迷う論点は、いったん置いて先へ進み、必ず後で確認する", 36, 520),             # 置い／て先へ進む
]


def mid(text, size, width):
    return wrap_fix.midword_breaks(text, size, width, level=3)


class WrapFixUnit(unittest.TestCase):
    def test_examples_are_midword_before_and_clean_after(self):
        for text, size, width in EXAMPLES:
            with self.subTest(text=text):
                self.assertGreater(mid(text, size, width), 0, "実例が自然な折り返しで語中折れになっていない（前提が崩れた）")
                out = wrap_fix.fix(text, size, width)
                self.assertNotEqual(out, text)
                self.assertEqual(out.replace("\n", ""), text, "文字は増減しない")
                self.assertEqual(mid(out, size, width), 0)

    def test_no_change_when_no_midword_break(self):
        for text, size, width in [("短い文", 20, 400), ("あ" * 5 + "、" + "い" * 5, 20, 400), ("確認する", 20, 80)]:
            self.assertEqual(wrap_fix.fix(text, size, width), text)

    def test_explicit_newline_untouched(self):
        t = "プラグインの\nファイルをアップロードする"
        self.assertEqual(wrap_fix.fix(t, 25, 300), t)

    def test_non_japanese_and_non_string_untouched(self):
        self.assertEqual(wrap_fix.fix("Upload the plugin file to the workspace now", 20, 200), "Upload the plugin file to the workspace now")
        self.assertEqual(wrap_fix.fix(None, 20, 200), None)
        self.assertEqual(wrap_fix.fix(12, 20, 200), 12)

    def test_disabled_by_config(self):
        text, size, width = EXAMPLES[0]
        cfg = wrap_fix.config({"wrap": {"enabled": False}})
        self.assertEqual(wrap_fix.fix(text, size, width, cfg), text)

    def test_min_px_skips_small_text(self):
        text, size, width = EXAMPLES[2]
        self.assertNotEqual(wrap_fix.fix(text, size, width), text)
        self.assertEqual(wrap_fix.fix(text, size, width, wrap_fix.config({"wrap": {"min_px": 24}})), text)

    def test_never_adds_lines_without_room(self):
        # 行数が増える直し方は、呼び出し側が余りを渡したときだけ
        text, size, width = "この資料の目的は。手順書を整えることにします", 21, 175
        base = ja_text.estimate_lines(text, size, width)
        out0 = wrap_fix.fix(text, size, width)
        self.assertLessEqual(len(wrap_fix._lines(out0, size, width, None, False)), base)
        out1 = wrap_fix.fix(text, size, width, extra=2)
        self.assertNotEqual(out1, text)
        self.assertGreater(len(wrap_fix._lines(out1, size, width, None, False)), base)
        # max_extra_lines: 0 は余りがあっても増やさない
        self.assertEqual(wrap_fix.fix(text, size, width, wrap_fix.config({"wrap": {"max_extra_lines": 0}}), extra=2), out0)

    def test_loose_model_small_kana_at_line_start(self):
        """Chromium の既定は小書きの仮名・長音を行頭に置く（「ブロ／ック」）。禁則どおりの折り返しでは語中にならない文も、実際の HTML では語中で折れる。"""
        text = "あ" * 22 + "ブロックを並べる"
        strict = ja_text.wrap_lines(text, 20, 480)
        loose = ja_text.wrap_lines(text, 20, 480, loose=True)
        self.assertTrue(strict[0].endswith("ブ"))
        self.assertTrue(loose[0].endswith("ブロ") and loose[1].startswith("ック"))
        self.assertGreater(mid(text, 20, 480), 0)
        out = wrap_fix.fix(text, 20, 480, extra=1)
        self.assertNotEqual(out, text)
        self.assertEqual(mid(out, 20, 480), 0)
        self.assertEqual(ja_text.wrap_lines("あ" * 30, 20, 480), ja_text.wrap_lines("あ" * 30, 20, 480, loose=False))   # 既定は従来どおり

    def test_deterministic(self):
        for text, size, width in EXAMPLES:
            self.assertEqual(wrap_fix.fix(text, size, width), wrap_fix.fix(text, size, width))

    def test_todo_marker_not_split(self):
        t = "手順書のブロックごとに、【要確認: 担当者の名前】を決めて始めます"
        out = wrap_fix.fix(t, 19, 300)
        for part in out.split("\n"):
            self.assertEqual(part.count("【"), part.count("】"), "【要確認】のマーカーを行で割らない")

    def test_config_clamps_and_ignores_bad_types(self):
        cfg = wrap_fix.config({"wrap": {"safety": 5, "detect_level": 9, "enabled": "no", "max_back_em": "x"}})
        self.assertEqual(cfg["safety"], 1.0)
        self.assertEqual(cfg["detect_level"], 3)
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["max_back_em"], wrap_fix.DEFAULTS["max_back_em"])
        self.assertEqual(wrap_fix.config({}), wrap_fix.DEFAULTS)
        self.assertEqual(wrap_fix.config(None), wrap_fix.DEFAULTS)


def deck_dir(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s5b_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def build(d, *args):
    r = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), *args], capture_output=True, text=True, encoding="utf-8")
    return r


def processed(slides, **meta):
    """expand → apply_line_balance → apply_wrap_fix を通したスライド列。"""
    d = deck_dir(slides, **meta)
    deck, theme, layout = b.load_deck(d)
    deck = b.expand_slides(deck, layout)
    deck = b.apply_line_balance(deck, layout)
    return b.apply_wrap_fix(deck, layout)["slides"], deck, layout, d


BULLETS = [{"type": "two_column", "title": "t",
            "left": {"heading": "進め方", "bullets": ["手順書のブロックごとに、確認する担当者を決めて始めます", "プラグインのファイルをアップロードして共有する"]},
            "right": {"heading": "確認", "bullets": ["印象でなく根拠で、論点ごとに整理する"]}}]


class ApplyWrapFix(unittest.TestCase):
    def test_two_column_bullets_get_phrase_breaks(self):
        before = BULLETS[0]["left"]["bullets"]
        out, _, _, _ = processed(BULLETS)
        after = out[0]["left"]["bullets"]
        self.assertTrue(any("\n" in x for x in after), after)
        for x, y in zip(before, after):
            self.assertEqual(y.replace("\n", ""), x)

    def test_cards_heading_and_body(self):
        cards = [{"type": "cards", "title": "t", "columns": 4, "cards": [
            {"heading": "確認と整理", "body": "目的は、印象でなく手順書の根拠で決めること"},
            {"heading": "置いて先へ進む", "body": "迷う点は置いて先へ進み、必ず後で見直す"},
            {"heading": "プラグイン導入", "body": "プラグインをアップロードして、担当者へ連絡する"},
            {"heading": "始めます", "body": "論点ごとに整理してから始めます"}]}]
        out, deck, layout, _ = processed(cards)
        st = b.resolve_style(layout, deck, out[0])
        for c in out[0]["cards"]:
            self.assertEqual(c["body"].replace("\n", "").count("\n"), 0)
        self.assertTrue(any("\n" in c["body"] for c in out[0]["cards"]))

    def test_off_switches(self):
        base, *_ = processed(BULLETS)
        # デッキ全体: meta.layout_overrides.common.wrap.enabled
        off, *_ = processed(BULLETS, layout_overrides={"common": {"wrap": {"enabled": False}}})
        self.assertFalse(any("\n" in x for x in off[0]["left"]["bullets"]))
        # スライド単位: style.wrap.enabled
        s = json.loads(json.dumps(BULLETS))
        s[0]["style"] = {"wrap": {"enabled": False}}
        off2, *_ = processed(s)
        self.assertFalse(any("\n" in x for x in off2[0]["left"]["bullets"]))
        # meta.line_balance / slide.line_balance
        off3, *_ = processed(BULLETS, line_balance=False)
        self.assertFalse(any("\n" in x for x in off3[0]["left"]["bullets"]))
        s = json.loads(json.dumps(BULLETS))
        s[0]["line_balance"] = False
        off4, *_ = processed(s)
        self.assertFalse(any("\n" in x for x in off4[0]["left"]["bullets"]))
        self.assertTrue(any("\n" in x for x in base[0]["left"]["bullets"]))

    def test_user_size_or_width_keeps_text(self):
        s = json.loads(json.dumps(BULLETS))
        s[0]["style"] = {"col_body": {"size": 19}}
        out, *_ = processed(s)
        self.assertFalse(any("\n" in x for x in out[0]["left"]["bullets"]), "利用者が size を書いた領域は触らない")

    def test_explicit_newline_kept(self):
        s = json.loads(json.dumps(BULLETS))
        s[0]["left"]["bullets"] = ["手順書のブロックごとに\n確認する担当者を決めて始めます"]
        out, *_ = processed(s)
        self.assertEqual(out[0]["left"]["bullets"], s[0]["left"]["bullets"])

    def test_wrap_region_validates(self):
        d = deck_dir(BULLETS, layout_overrides={"common": {"wrap": {"safety": 2.5}}})
        r = build(d, "--html")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("safety", r.stdout + r.stderr)
        d = deck_dir(BULLETS, layout_overrides={"common": {"wrap": {"max_back_em": 12, "enabled": True}}})
        r = build(d, "--html")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_same_input_same_output(self):
        d = deck_dir(BULLETS)
        outs = []
        for _ in range(2):
            self.assertEqual(build(d).returncode, 0)
            outs.append((d / "build" / "d.html").read_text(encoding="utf-8"))
        self.assertEqual(outs[0], outs[1])

    def test_html_and_pptx_break_at_same_place(self):
        d = deck_dir(BULLETS)
        self.assertEqual(build(d).returncode, 0)
        html = (d / "build" / "d.html").read_text(encoding="utf-8")
        with zipfile.ZipFile(d / "build" / "d.pptx") as z:
            xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
        # 改行の直前の文字列が両方にある（HTML は <br>、PPTX は a:br）
        out, *_ = processed(BULLETS)
        for item in out[0]["left"]["bullets"]:
            if "\n" not in item:
                continue
            first, second = item.split("\n")[:2]
            self.assertIn(first + "<br", html.replace("\n", ""))
            self.assertRegex(xml, re.escape(first) + r"</a:t></a:r><a:br")
            self.assertIn(second, xml)

    def test_composite_callout_and_block_bullets(self):
        s = [{"type": "composite", "title": "t", "arrange": "main-side", "blocks": [
            {"type": "callout", "text": "迷う論点は、いったん置いて先へ進み、必ず後で確認する"},
            {"type": "bullets", "heading": "進め方", "frame": "box",
             "bullets": ["プラグインのファイルをアップロードする", "担当者へ手順書のブロックを共有して確認する"]}]}]
        out, *_ = processed(s)
        blocks = out[0]["blocks"]
        self.assertIn("\n", blocks[0]["text"])
        self.assertTrue(any("\n" in x for x in blocks[1]["bullets"]))

    def test_steps_items(self):
        s = [{"type": "steps", "title": "t", "steps": [
            {"label": "導入", "items": ["プラグインを入れて、ファイルをアップロードする", "担当者へ手順書を渡す"]},
            {"label": "確認", "items": ["目的は印象でなく根拠で確認すること"]},
            {"label": "整理", "items": ["論点ごとに整理して始めます"]}]}]
        out, *_ = processed(s)
        joined = [x for stp in out[0]["steps"] for x in stp["items"]]
        self.assertTrue(any("\n" in x for x in joined), joined)

    def test_closing_and_statement_support(self):
        s = [{"type": "closing", "title": "次", "variant": "contact", "message": "迷う論点は置いて先へ進みます",
              "bullets": ["プラグインをアップロードして、担当者へ共有する", "手順書のブロックを論点ごとに整理して始めます"]},
             {"type": "statement", "message": "要点", "support": "プラグインのファイルをアップロードして、担当者へ共有する手順書のブロックを確認します"}]
        out, *_ = processed(s)
        self.assertTrue(any("\n" in x for x in out[0]["bullets"]))
        self.assertIn(("support", False), b._WRAP_TEXT_REGIONS)        # 副文（statement.support / quote.attribution）も対象の領域
        self.assertIn(("attribution", False), b._WRAP_TEXT_REGIONS)


class TableCells(unittest.TestCase):
    TABLE = [{"type": "table", "title": "t", "columns": ["項目", "内容", "担当"], "rows": [
        ["プラグイン", "ファイルをアップロードして担当者へ共有する", "情シス"],
        ["手順書", "目的は印象でなく論点ごとに整理して始めます", "総務"],
        ["ブロック", "迷う論点は置いて先へ進み、必ず後で確認する", "営業"],
        ["確認", "担当者へ手順書のブロックを共有して確認する", "人事"]]}]

    def test_col_widths_unchanged_after_cell_breaks(self):
        out, deck, layout, _ = processed(self.TABLE)
        d0 = deck["slides"][0]
        w0 = b.resolve_style(layout, deck, d0)["table"]["col_widths"]
        w1 = b.resolve_style(layout, deck, out[0])["table"]["col_widths"]
        self.assertEqual(len(w0), len(w1))
        for a, c in zip(w0, w1):
            self.assertLessEqual(abs(a - c), 0.5, "セルに改行を入れたあとも、列幅は変わらない（変わるなら入れない）")

    def test_cell_text_keeps_characters(self):
        out, deck, _, _ = processed(self.TABLE)
        for r0, r1 in zip(deck["slides"][0]["rows"], out[0]["rows"]):
            for c0, c1 in zip(r0, r1):
                self.assertEqual(str(c1).replace("\n", ""), str(c0))

    def test_user_col_widths_keep_cells(self):
        s = json.loads(json.dumps(self.TABLE))
        s[0]["style"] = {"table": {"col_widths": [120, 700, 316]}}
        out, deck, _, _ = processed(s)
        self.assertEqual(out[0]["rows"], deck["slides"][0]["rows"])


class WordbreakCheck(unittest.TestCase):
    def test_items_pure(self):
        raw = [{"el": "p", "text": "プラグインのファイルをアップロードする", "lens": [11, 8], "size": 25}]   # プラグインのファイルを|アップロードする → 良い
        self.assertEqual(CL.wordbreak_items(raw), [])
        raw = [{"el": "p", "text": "プラグインのファイルをアップロードする", "lens": [15, 4], "size": 25}]    # プラグインのファイルをアップロ|ードする → 語の途中
        r = CL.wordbreak_items(raw)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["line"], 1)
        self.assertIn("ロ", r[0]["tail"])

    def test_explicit_newline_and_english_ignored(self):
        self.assertEqual(CL.wordbreak_items([{"el": "p", "text": "あいう\nえおかき", "lens": [3, 5], "size": 20}]), [])
        self.assertEqual(CL.wordbreak_items([{"el": "p", "text": "Upload the file now", "lens": [10, 9], "size": 20}]), [])

    def test_format_has_fix_and_kind_registered(self):
        item = {"el": "li", "text": "本文", "tail": "アップロ", "head": "ードする", "line": 1, "lines": 2, "size": 25, "cell": False}
        line = CL.format_item("slide-02", "wordbreak", item)
        self.assertIn("wordbreak", line)
        self.assertIn("\\n", line)
        cell = CL.format_item("slide-02", "wordbreak", dict(item, cell=True))
        self.assertIn("col_widths", cell)
        self.assertIn("wordbreak", CL.SOFT_KINDS)
        self.assertIn("wordbreak", CL.ALL_KINDS)
        report = {"slides": {"slide-01": {k: [] for k in CL.ALL_KINDS}}}
        report["slides"]["slide-01"]["wordbreak"] = [item]
        self.assertEqual(CL.classify(report), (0, 1))


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


@unittest.skipUnless(sync_playwright, "Playwright が無い")
class WordbreakInBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # noqa: BLE001
            cls.pw.stop()
            raise unittest.SkipTest(f"Chromium を起動できない: {e}")
        cls.page = cls.browser.new_page(viewport={"width": 1280, "height": 720})

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def run_html(self, inner):
        html = ('<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0"><section class="slide active" data-type="x" '
                'style="position:absolute;left:0;top:0;width:1280px;height:720px;overflow:hidden;font-family:sans-serif">' + inner + "</section></body></html>")
        self.page.set_content(html)
        CL.wait_ready(self.page)
        return CL.analyze_page(self.page)

    def test_detects_midword_and_not_phrase_break(self):
        box = '<div style="position:absolute;left:40px;top:40px;width:250px;font-size:25px">{}</div>'
        r = self.run_html(box.format("プラグインのファイルをアップロードする"))     # 10 字 + 9 字: アップロ|ードする
        self.assertEqual(len(r["wordbreak"]), 1, r["wordbreak"])
        wide = '<div style="position:absolute;left:40px;top:40px;width:300px;font-size:25px">{}</div>'
        r = self.run_html(wide.format("プラグインのファイルを<br>アップロードする"))
        self.assertEqual(r["wordbreak"], [])


# ---------------------------------------------------------------------------
# 順序「大きさを決める → 決まった大きさで改行を入れる」と、検算・止め方（独立レビュー s5b-R-01〜R-11 の修正）
# ---------------------------------------------------------------------------

KPI = {"type": "kpi", "title": "数字", "items": [
    {"value": "10", "unit": "件", "label": "プラグインのファイルをアップロードする", "note": "詳細は https://example.com/docs/getting-started/installation を参照"},
    {"value": "10", "unit": "件", "label": "詳細は https://example.com/docs/getting-started/installation を参照", "note": "社内ポータルで受け付けた質問に、手順書の根拠つきで答える"},
    {"value": "10", "unit": "件", "label": "社内ポータルで受け付けた質問に、手順書の根拠つきで答える", "note": "データベースのバックアップは毎日午前3時に自動で取得される"}]}


def _blank(slides, **meta):
    d = deck_dir(slides, **meta)
    deck, theme, layout = b.load_deck(d)
    return b.expand_slides(deck, layout), layout


class SizeBeforeBreaks(unittest.TestCase):
    def test_composite_steps_keep_the_unwrapped_size(self):
        s = [{"type": "composite", "title": "t", "arrange": "two", "blocks": [
            {"type": "kpi", "items": [{"value": "5", "unit": "件", "label": "a"}, {"value": "7", "label": "b"}]},
            {"type": "steps", "steps": [{"label": "見積書", "items": ["印象で判断せず、目的は何かを確認します", "✅ 完了した作業を確認して次のステップへ進みます 🚀"]},
                                         {"label": "完了", "items": ["月次の定例会議で進み具合と課題を確認して、次の月の計画を決める"]}]}]}]
        out, deck, layout, _ = processed(s)
        self.assertTrue(any("\n" in x for stp in out[0]["blocks"][1]["steps"] for x in stp["items"]), "前提: 改行が入る")
        a = b.resolve_style(layout, deck, deck["slides"][0])["_composite"]["blocks"][1]["st"]["body"]
        c = b.resolve_style(layout, deck, out[0])["_composite"]["blocks"][1]["st"]["body"]
        for k in ("h", "item_size", "label_size", "header_h", "fit"):
            self.assertEqual(a.get(k), c.get(k), k)

    def test_title_size_does_not_change_with_breaks(self):
        t = "確信度が低い質問は、経緯を添えて担当者に回して学び直す新入社員向けのオンボ"
        s = [{"type": "title", "title": t, "subtitle": "ユーザーインタビューで得た気づきを、プロトタイプに反映する"}]
        out, deck, layout, _ = processed(s, density="talk", shape="sharp")
        a = b.resolve_style(layout, deck, deck["slides"][0])["title"]["size"]
        self.assertEqual(b.resolve_style(layout, deck, out[0])["title"]["size"], a)

    def test_cards_after_growth_have_no_rewrapped_segment(self):
        cards = [{"type": "cards", "title": "t", "columns": 4, "cards": [
            {"heading": "復旧", "body": "復旧作業に着手する"}, {"heading": "連絡", "body": "連絡漏れを防ぐ"},
            {"heading": "導入", "body": "インターナショナルコンプライアンスマネジメントシステムの導入"}, {"heading": "確認", "body": "答える"}]}]
        out, deck, layout, _ = processed(cards)
        st = b.resolve_style(layout, deck, out[0])
        g = st["grid"]
        geo = b.pe.cards_cells(4, 4, g, b.hero.card_spans(out[0]))
        for k, c in enumerate(out[0]["cards"]):
            w = geo["cells"][k][2] - 2 * g.get("pad", 18)
            for key, size in (("body", g.get("body_size", 15)),):
                if isinstance(c.get(key), str) and "\n" in c[key]:
                    self.assertTrue(wrap_fix.breaks_ok(c[key], size, w), (key, c[key]))

    def test_wrap_src_is_hidden_from_scanners_and_keeps_markers(self):
        from todo_marks import scan_deck
        s = [{"type": "two_column", "title": "t", "left": {"heading": "進め方", "bullets": ["手順書のブロックごとに、確認する担当者を決めて始めます【要確認: 期限】"]},
              "right": {"heading": "確認", "bullets": ["印象でなく根拠で、論点ごとに整理する"]}}]
        out, deck, layout, _ = processed(s)
        self.assertIsInstance(out[0].get("_wrap_src"), b.WrapSrc)
        before = [m["text"] for m in scan_deck({"slides": deck["slides"]})]
        after = [m["text"] for m in scan_deck({"slides": out})]
        self.assertEqual(before, after)
        self.assertEqual(json.dumps(out[0].get("left"), ensure_ascii=False).count("【要確認"), 1)

    def test_slide_without_midword_break_is_untouched(self):
        s = [{"type": "bullets", "title": "t", "bullets": ["短い文", "もう一つ"]}]
        out, deck, *_ = processed(s)
        self.assertEqual(out[0], deck["slides"][0])
        self.assertNotIn("_wrap_src", out[0])


class BreakCheck(unittest.TestCase):
    CFG = wrap_fix.DEFAULTS

    def test_url_is_never_split(self):
        t = "詳細は https://example.com/docs/getting-started/installation を参照してください"
        for size, width in ((20, 330), (15, 250), (18, 300)):
            out = wrap_fix.fix(t, size, width, self.CFG, extra=1)
            joined_pos = 0
            for seg in out.split("\n")[:-1]:
                joined_pos += len(seg)
                self.assertFalse(wrap_fix._inside_token(out.replace("\n", ""), joined_pos), out)

    def test_todo_marker_inside_is_not_a_break_position(self):
        t = "確かめる点は【要確認: 担当者の確認先と期限】のとおりです"
        j = t
        a = t.index("担当者")
        self.assertTrue(wrap_fix._inside_token(j, a + 2))
        self.assertFalse(wrap_fix._inside_token(j, t.index("【")))      # マーカーの手前は切れ目にしてよい
        out = wrap_fix.fix(t, 20, 300, self.CFG, extra=1)
        for part in out.split("\n"):
            self.assertEqual(part.count("【"), part.count("】"))

    def test_breaks_ok_rules(self):
        self.assertTrue(wrap_fix.breaks_ok("データベースのバックアップは\n毎日午前3時に自動で取得される", 20, 444.8))
        self.assertFalse(wrap_fix.breaks_ok("データベースの\nバックアップは毎日午前3時に自動で取得されるのでしょうか確認する", 20, 300), "どの行も折り返されない")
        self.assertFalse(wrap_fix.breaks_ok("確認\nの\n手順書を共有する", 20, 400), "1 字だけの行を作らない")
        self.assertFalse(wrap_fix.breaks_ok("手順書を共有して確認する\nね", 20, 400), "最終行が 1〜2 字になる")
        self.assertTrue(wrap_fix.breaks_ok("手順書を共有して確認する\nね", 20, 400, tail_min=0), "元から短い最終行は許す")

    def test_no_one_char_line_in_very_narrow_box(self):
        for t in ("手順書の確認をお願いします", "目的はこの資料の整理です", "印象で判断せず確認する"):
            for w in (60, 70, 86, 100):
                out = wrap_fix.fix(t, 20, w, self.CFG, extra=3)
                for seg in out.split("\n")[:-1]:
                    self.assertGreaterEqual(len(seg.strip()), 2, (t, w, out))

    def test_last_line_not_shortened_to_one_or_two_chars(self):
        for t, size, width in (("連絡漏れを防ぐための手順を確認して答える。", 21, 170), ("目的は印象でなく根拠で決めて答える。", 21, 190)):
            out = wrap_fix.fix(t, size, width, self.CFG, extra=1)
            self.assertGreaterEqual(len(out.split("\n")[-1].strip()), 3 if len(ja_text.wrap_lines(t, size, width)[-1].strip()) >= 3 else 0, out)

    def test_deterministic_full_pipeline(self):
        a, *_ = processed(BULLETS)
        c, *_ = processed(BULLETS)
        self.assertEqual(json.dumps(a, ensure_ascii=False, default=lambda o: "S"), json.dumps(c, ensure_ascii=False, default=lambda o: "S"))


class Switches(unittest.TestCase):
    def test_autofit_false_stops_phrase_breaks(self):
        base, *_ = processed(BULLETS)
        self.assertTrue(any("\n" in x for x in base[0]["left"]["bullets"]))
        off, *_ = processed(BULLETS, autofit=False)
        self.assertEqual(off[0]["left"]["bullets"], BULLETS[0]["left"]["bullets"])
        s = json.loads(json.dumps(BULLETS))
        s[0]["autofit"] = False
        off2, *_ = processed(s)
        self.assertEqual(off2[0]["left"]["bullets"], BULLETS[0]["left"]["bullets"])

    def test_kpi_flag_follows_the_same_conditions(self):
        def flagged(slides, **meta):
            out, *_ = processed(slides, **meta)
            return isinstance(out[0].get("_wrap_cfg"), dict)
        self.assertTrue(flagged([KPI]))
        self.assertFalse(flagged([KPI], line_balance=False))
        self.assertFalse(flagged([KPI], autofit=False))
        self.assertFalse(flagged([KPI], layout_overrides={"common": {"wrap": {"enabled": False}}}))
        self.assertFalse(flagged([KPI], layout_overrides={"kpi": {"body": {"label_size": 18}}}))
        self.assertFalse(flagged([KPI], layout_overrides={"kpi": {"body": {"note_size": 14}}}))
        for patch in ({"line_balance": False}, {"autofit": False}, {"style": {"wrap": {"enabled": False}}}, {"style": {"body": {"label_size": 18}}}):
            self.assertFalse(flagged([{**KPI, **patch}]), patch)

    def test_kpi_block_follows_slide_level_switches(self):
        comp = {"type": "composite", "title": "t", "arrange": "two", "blocks": [KPI, {"type": "bullets", "bullets": ["a", "b"]}]}
        out, *_ = processed([comp])
        self.assertTrue(isinstance(out[0]["blocks"][0].get("_wrap_cfg"), dict))
        for patch in ({"style": {"wrap": {"enabled": False}}}, {"autofit": False}, {"line_balance": False}):
            out, *_ = processed([{**comp, **patch}])
            self.assertFalse(isinstance(out[0]["blocks"][0].get("_wrap_cfg"), dict), patch)

    def _kpi_breaks(self, slide, **meta):
        d = deck_dir([slide], **meta)
        r = build(d, "--html")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        html = (d / "build" / "d.html").read_text(encoding="utf-8")
        html = html[html.index('<section class="slide"'):html.rindex("</section>")]
        return len(re.findall(r">[^<>]*[^\s<>]\n[^\s<>][^<>]*<", html)) + html.count("<br")

    def test_kpi_breaks_follow_switches_in_html(self):
        on = self._kpi_breaks(KPI)
        self.assertGreater(on, 0)
        self.assertEqual(self._kpi_breaks(KPI, line_balance=False), 0)
        self.assertEqual(self._kpi_breaks({**KPI, "style": {"wrap": {"enabled": False}}}), 0)


NARROW_TABLE = [{"type": "table", "title": "表 2", "columns": ["項目", "内容", "備考"], "rows": [
    ["印象で判断せず、目的", "✅ 完了した作業を確認して次のステップへ進みます 🚀", "月次の定例会議で進み具合と課題を確認して、次の月の計画を決める"],
    ["見積書の承認フローを", "印象で判断せず、目的は何かを確認します", "✅ 完了した作業を確認して次のステップへ進みます 🚀"],
    ["月次の定例会議で", "見積書の承認フローを見直し、決裁までの日数を半分にする", "印象で判断せず、目的は何かを確認します"]]}]


class TableWrapEffective(unittest.TestCase):
    def test_cells_actually_get_breaks_and_widths_stay(self):
        out, deck, layout, _ = processed(NARROW_TABLE, density="standard", shape="classic")
        changed = [c for r0, r1 in zip(deck["slides"][0]["rows"], out[0]["rows"]) for c0, c in zip(r0, r1) if c != c0]
        self.assertTrue(changed, "表のセルにも文節の改行が入る（安定性の確認で全部取り消されない）")
        w0 = b.resolve_style(layout, deck, deck["slides"][0])["table"]["col_widths"]
        w1 = b.resolve_style(layout, deck, out[0])["table"]["col_widths"]
        self.assertEqual(w0, w1)

    def test_many_rows_skip_the_search(self):
        out, deck, *_ = processed([{"type": "table", "title": "t", "columns": ["項目", "内容", "備考"], "rows": NARROW_TABLE[0]["rows"] * 21}])
        self.assertEqual(out[0]["rows"], deck["slides"][0]["rows"])
        self.assertEqual(autofit.TABLE_SEARCH_MAX_ROWS, b.WRAP_TABLE_MAX_ROWS)


class WrapTokenValidation(unittest.TestCase):
    def _problems(self, **wrap):
        import deck_schema as ds
        return ds.check_region_value(wrap, {"enabled": True, "detect_level": 3, "safety": 0.95, "max_back_em": 10.0, "max_extra_lines": 1, "min_px": 0.0},
                                     "meta.layout_overrides.common.wrap")

    def test_fractional_integers_are_rejected_with_key(self):
        for k, v in (("detect_level", 2.5), ("max_extra_lines", 1.5)):
            p = self._problems(**{k: v})
            self.assertEqual([lvl for lvl, _ in p], ["fail"], p)
            self.assertIn(k, p[0][1])
            self.assertIn("整数", p[0][1])
        self.assertEqual(self._problems(detect_level=2, max_extra_lines=0), [])

    def test_range_error_hint_matches_the_key(self):
        p = self._problems(safety=2.5)
        self.assertIn("safety", p[0][1])
        self.assertNotIn("拡大", p[0][1])
        self.assertIn("wrap.enabled", p[0][1])
        p = self._problems(safety="x")
        self.assertNotIn(": 24 ", p[0][1])


if __name__ == "__main__":
    unittest.main()

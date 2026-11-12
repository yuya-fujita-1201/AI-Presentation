#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2a 結線のテスト: A 型エンジンの登録表 / kpi・chart / pattern（full・body の 2 つの枠）/ canvas の画像 /
data-max-lines・data-qa-ignore / code の溢れ警告 / pattern_engine preview。

実行: python3 -m unittest plugins/slide-deck/tools/test_s2a_wiring.py
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

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import canvas_engine as ce  # noqa: E402
import engine_registry as er  # noqa: E402
import pattern_engine as pe  # noqa: E402
from test_validation import one, validate, write_deck  # noqa: E402

PY = sys.executable


def make_assets(d: Path):
    from PIL import Image, ImageDraw
    a = d / "assets"
    a.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (1600, 900), (20, 80, 160))
    ImageDraw.Draw(im).ellipse([600, 200, 1000, 700], fill=(250, 200, 40))
    im.save(a / "wide.png")
    im = Image.new("RGB", (600, 1000), (160, 60, 60))
    ImageDraw.Draw(im).rectangle([100, 100, 500, 900], outline=(255, 255, 255), width=10)
    im.save(a / "tall.jpg")
    (a / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
                                '<rect width="200" height="100" fill="#0F6E8C"/><circle cx="50" cy="50" r="40" fill="#F2A33A"/></svg>',
                                encoding="utf-8")


def build(deck_dir, *extra):
    return subprocess.run([PY, str(TOOLS / "build_deck.py"), str(deck_dir), *extra], capture_output=True, text=True, encoding="utf-8")


KPI = {"type": "kpi", "title": "作成時間は 3 分の 1 になった",
       "items": [{"value": "2.1", "unit": "時間", "label": "作成時間", "from": "6.5", "delta": "−68%", "good": "down"}]}
CHART = {"type": "chart", "title": "作成時間は下がった", "chart": "bar", "unit": "時間", "categories": ["Q1", "Q2", "Q3"],
         "series": [{"name": "作成時間", "values": [6.8, 6.5, 2.4]}]}


class RegistryTests(unittest.TestCase):
    def test_a_type_registry_has_proposal_and_dataviz_types(self):
        names = set(er.names())
        self.assertTrue({"summary", "reasons", "statement", "row_matrix", "org", "house", "cycle", "kpi_tree", "kpi", "chart"} <= names)
        self.assertFalse(er.get("statement").chrome)
        self.assertTrue(er.get("kpi").chrome)

    def test_registered_types_are_rendered_and_in_layout(self):
        layout = b.load_layout("default")
        for t in er.names():
            self.assertIn(t, b.RENDERED_TYPES)
            self.assertIn(t, layout["types"], f"{t} の既定レイアウトが default.json に無い")
        self.assertIn("pattern", b.RENDERED_TYPES)

    def test_inspection_properties_come_from_registry(self):
        import check_visual
        import lint_deck_text as lint
        self.assertTrue(check_visual.band_warning("1枚目", "kpi", (400, 300, 700), 0.1, 150) is None)    # kpi は余白が前提
        self.assertIsNotNone(check_visual.band_warning("1枚目", "chart", (400, 300, 700), 0.1, 150))
        self.assertIn("kpi", lint.relation_table()["parallel"])
        self.assertIn("chart", lint.relation_table()["contrast"])
        texts = [t for _p, t in lint.iter_texts({**CHART, "chart": "bar", "unit": "時間", "highlight": ["Q3"]})]
        self.assertNotIn("bar", texts)          # 種類・単位・強調の列挙値は本文として数えない
        self.assertNotIn("時間", texts)

    def test_kpi_chart_unknown_key_warns_once_with_candidate(self):
        exc, err = validate(one({**KPI, "itms": []}))
        self.assertEqual(err.count("itms"), 1, err)
        self.assertIn("未知のキー", err)
        exc, err = validate(one({**CHART, "categoris": ["a"]}))
        self.assertEqual(err.count("categoris"), 1, err)
        exc, err = validate(one({**CHART, "style": {"body": {"bogus_key": 1}}}))
        self.assertEqual(err.count("bogus_key"), 1, err)

    def test_kpi_chart_validation_fails_with_fix(self):
        exc, err = validate(one({"type": "kpi", "title": "t"}))
        self.assertIsNotNone(exc)
        self.assertIn("items", str(exc) + err)
        exc, err = validate(one({"type": "chart", "title": "t", "chart": "bar", "categories": ["a", "b"], "series": [{"name": "x", "values": [1]}]}))
        self.assertIsNotNone(exc)
        self.assertIn("values", str(exc) + err)

    def test_chart_diagnostics_reach_build_warnings_once(self):
        cats = [f"項目{i}" for i in range(12)]
        slide = {"type": "chart", "title": "t", "chart": "bar", "categories": cats,
                 "series": [{"name": "a", "values": list(range(1, 13))}, {"name": "b", "values": list(range(12, 0, -1))},
                            {"name": "c", "values": list(range(1, 13))}], "values": True}
        exc, err = validate(one(slide))
        self.assertIsNone(exc)
        self.assertEqual(err.count("値ラベルが隣と重なります"), 1, err)


class BuildKpiChartTests(unittest.TestCase):
    def test_html_and_pptx_build(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "d", "title": "T", "theme": "default"},
                               "slides": [KPI, CHART, {**KPI, "conclusion": "結論", "source": "出典"}]})
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((d / "build" / "d.pptx").exists())
            html = (d / "build" / "d.html").read_text(encoding="utf-8")
            self.assertIn('data-type="kpi"', html)
            self.assertIn('data-type="chart"', html)
            from pptx import Presentation
            prs = Presentation(str(d / "build" / "d.pptx"))
            self.assertEqual(len(prs.slides), 3)
            self.assertGreater(len(prs.slides[1].shapes), 10)         # 棒・ラベルがネイティブ図形


class PatternWiringTests(unittest.TestCase):
    FULL = {"type": "pattern", "pattern": "conclusion-evidence",
            "slots": {"title": "結論を言い切る", "label": "結論", "conclusion": "まず 1 業務から",
                      "evidence": [{"head": "効果", "body": "大きい"}, {"head": "影響", "body": "小さい"}]}}
    BODY = {"type": "pattern", "pattern": "numbered-columns", "title": "段階で進める", "lead": "各段階で判断する",
            "slots": {"items": [{"head": "把握", "body": "現状を一覧にする"}, {"head": "試行", "body": "1 業務で試す"},
                                {"head": "展開", "body": "隣へ渡す"}]},
            "conclusion": "段階ごとに判断する", "source": "出典：計画"}

    def test_both_frames_build_html_and_pptx(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "d", "title": "T", "theme": "default"}, "slides": [self.FULL, self.BODY]})
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.count("warning"), 0, r.stderr)
            html = (d / "build" / "d.html").read_text(encoding="utf-8")
            self.assertIn('data-pattern="conclusion-evidence"', html)
            self.assertIn('data-pattern="numbered-columns"', html)
            # body 枠は見出し骨格（title / 結論帯 / 出典）をプラグインが描く。full 枠は型自身が描く
            body_sec = html.split('data-pattern="numbered-columns"')[1]
            self.assertIn("段階で進める", body_sec)
            self.assertIn("段階ごとに判断する", body_sec)
            self.assertIn("出典：計画", body_sec)
            self.assertNotIn("結論を言い切る", body_sec)
            self.assertEqual(html.count("結論を言い切る"), html.split('data-pattern="numbered-columns"')[0].count("結論を言い切る"))
            from pptx import Presentation
            prs = Presentation(str(d / "build" / "d.pptx"))
            texts = [[sh.text_frame.text for sh in s.shapes if sh.has_text_frame] for s in prs.slides]
            self.assertTrue(any("結論を言い切る" in x for x in texts[0]))
            self.assertTrue(any("段階で進める" in x for x in texts[1]))
            self.assertTrue(any("段階ごとに判断する" in x for x in texts[1]))      # 結論帯（common_parts）が 1 回
            self.assertEqual(sum("段階ごとに判断する" in x for x in texts[1]), 1)

    def test_body_frame_block_fits_the_real_body_rect(self):
        pat = pe.load_pattern("numbered-columns")
        theme = b.load_theme("default", b.theme_dirs(None))
        slide = {"type": "pattern", "pattern": "numbered-columns", "slots": self.BODY["slots"]}
        full = pe.pattern_block_elements(slide, pat, (72, 192, 1136, 452), theme)
        small = pe.pattern_block_elements(slide, pat, (72, 192, 568, 226), theme)      # 半分の矩形（合成スライドのブロック用）
        for els, rect in ((full, (72, 192, 1136, 452)), (small, (72, 192, 568, 226))):
            for e in ce.flatten(els):
                self.assertGreaterEqual(e["x"], rect[0] - 0.5)
                self.assertLessEqual(e["x"] + e["w"], rect[0] + rect[2] + 0.5)
                self.assertGreaterEqual(e["y"], rect[1] - 0.5)
                self.assertLessEqual(e["y"] + e["h"], rect[1] + rect[3] + 0.5)
        fs_full = max(r["size"] for e in ce.flatten(full) if e.get("text") for p in e["text"]["paragraphs"] for r in p["runs"])
        fs_small = max(r["size"] for e in ce.flatten(small) if e.get("text") for p in e["text"]["paragraphs"] for r in p["runs"])
        self.assertLess(fs_small, fs_full)           # 文字も縮む

    def test_body_frame_without_title_warns_and_unknown_pattern_fails(self):
        exc, err = validate(one({**self.BODY, "title": ""}))
        self.assertIsNone(exc)
        self.assertIn("title がありません", err)
        exc, err = validate(one({"type": "pattern", "pattern": "nonexistent", "slots": {}}))
        self.assertIsNotNone(exc)
        self.assertIn("見つかりません", str(exc) + err)
        exc, err = validate(one({"type": "pattern", "pattern": "numbered-columns", "title": "t", "slots": {}}))
        self.assertIsNotNone(exc)
        self.assertIn("items", str(exc) + err)

    def test_pattern_slide_warnings_are_not_duplicated(self):
        slide = {**self.BODY, "slots": {"items": [{"head": "ア" * 30, "body": "イ" * 200}, {"head": "b", "body": "c"}, {"head": "d", "body": "e"}]}}
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one(slide))
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stderr.splitlines() if ln.startswith("warning")]
            self.assertEqual(len(lines), len(set(lines)), r.stderr)
            self.assertGreaterEqual(len(lines), 1)

    def test_frame_and_size_are_checked(self):
        pat = pe.load_pattern("numbered-columns")
        errs, _ = pe.check_pattern({**pat, "frame": "middle"})
        self.assertTrue(any("frame" in e for e in errs))
        errs, _ = pe.check_pattern({**pat, "size": [100]})
        self.assertTrue(any("size" in e for e in errs))
        errs, _ = pe.check_pattern({**pat, "valign": "bottom"})
        self.assertTrue(any("valign" in e for e in errs))
        errs, warns = pe.check_pattern(pat)
        self.assertEqual((errs, warns), ([], []))
        # 設計寸法の外へはみ出す要素は警告
        pat2 = json.loads(json.dumps(pat))
        pat2["elements"].append({"name": "はみ出し", "x": 1100, "y": 0, "w": 200, "h": 20, "fill": "accent"})
        _, warns = pe.check_pattern(pat2)
        self.assertTrue(any("はみ出す" in w for w in warns), warns)

    def test_bundled_patterns_are_clean_in_both_themes(self):
        for name in pe.available_names():
            pat = pe.load_pattern(name)
            for theme_name in ("default", "acn-slide-master"):
                theme = b.load_theme(theme_name, b.theme_dirs(None))
                errs, warns = pe.check_pattern(pat, theme)
                self.assertEqual((errs, warns), ([], []), f"{name}/{theme_name}")
        self.assertTrue({"conclusion-evidence", "before-after", "pillars", "numbered-columns", "keyword-explain"} <= set(pe.available_names()))

    def test_pattern_search_uses_deck_paths(self):
        import deck_paths
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual([p.resolve() for p in pe.pattern_dirs(t)], [p.resolve() for p in deck_paths.search_dirs("patterns", t)])


class PreviewTests(unittest.TestCase):
    def test_preview_deck_lists_every_pattern_with_example(self):
        deck, errors = pe.preview_deck(None, "default")
        self.assertEqual(errors, [])
        names = [s["pattern"] for s in deck["slides"]]
        self.assertEqual(sorted(names), sorted(pe.available_names()))
        body = [s for s in deck["slides"] if s["pattern"] == "numbered-columns"][0]
        self.assertIn("title", body)
        self.assertIn("numbered-columns", body["notes"])

    def test_preview_cli_builds_html(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "pv"
            r = subprocess.run([PY, str(TOOLS / "pattern_engine.py"), "preview", "--out", str(out), "--html"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((out / "build" / "pv.html").exists())

    def test_preview_includes_deck_local_patterns(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "deck"
            (d / "patterns").mkdir(parents=True)
            pat = json.loads(json.dumps(pe.load_pattern("numbered-columns")))
            pat.pop("_path")
            pat["name"] = "mine"
            (d / "patterns" / "mine.json").write_text(json.dumps(pat, ensure_ascii=False), encoding="utf-8")
            deck, _ = pe.preview_deck(d, "default")
            self.assertIn("mine", [s["pattern"] for s in deck["slides"]])


class CanvasImageTests(unittest.TestCase):
    def deck(self, elements, **kw):
        return {"meta": {"id": "d", "title": "T", "theme": "default"},
                "slides": [{"type": "canvas", "background": "#FFFFFF", "elements": elements}], **kw}

    def test_png_jpg_svg_appear_in_html_and_pptx(self):
        els = [{"kind": "image", "name": "a", "x": 10, "y": 10, "w": 400, "h": 300, "path": "assets/wide.png", "fit": "cover"},
               {"kind": "image", "name": "b", "x": 420, "y": 10, "w": 400, "h": 300, "path": "assets/wide.png", "fit": "contain"},
               {"kind": "image", "name": "c", "x": 10, "y": 330, "w": 400, "h": 300, "path": "assets/tall.jpg", "fit": "cover"},
               {"kind": "image", "name": "d", "x": 420, "y": 330, "w": 400, "h": 200, "path": "assets/mark.svg", "fit": "contain"}]
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, self.deck(els))
            make_assets(d)
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = (d / "build" / "d.html").read_text(encoding="utf-8")
            self.assertEqual(html.count('class="cv-s cv-img"'), 4, "画像が灰色の枠になっている")
            self.assertNotIn('class="cv-s cv-ph"', html)
            from pptx import Presentation
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            prs = Presentation(str(d / "build" / "d.pptx"))
            pics = [sh for sh in prs.slides[0].shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
            self.assertEqual(len(pics), 4, [sh.shape_type for sh in prs.slides[0].shapes])
            cover = [p for p in pics if p.name.startswith("a")][0]
            self.assertGreater(cover.crop_left + cover.crop_right + cover.crop_top + cover.crop_bottom, 0.05)    # cover は切り抜き

    def test_image_path_problems_fail_with_fix(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, self.deck([{"kind": "image", "x": 0, "y": 0, "w": 100, "h": 100, "path": "assets/none.png"}]))
            (d / "assets").mkdir()
            r = build(d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("見つかりません", r.stderr)
            d2 = write_deck(t, self.deck([{"kind": "image", "x": 0, "y": 0, "w": 100, "h": 100, "path": "../x.png"}]), "d2")
            r = build(d2)
            self.assertEqual(r.returncode, 1)
            self.assertIn("..", r.stderr)

    def test_pattern_image_slot_renders(self):
        pat = {"name": "photo", "frame": "body", "size": [1136, 400], "background": "background",
               "slots": {"photo": {"kind": "image", "required": True, "example": "assets/wide.png"}},
               "elements": [{"kind": "image", "name": "写真", "x": 0, "y": 0, "w": 500, "h": 400, "path": "{{photo}}", "fit": "cover"}]}
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "pattern", "pattern": "photo", "title": "写真", "slots": {"photo": "assets/wide.png"}}))
            (d / "patterns").mkdir()
            (d / "patterns" / "photo.json").write_text(json.dumps(pat, ensure_ascii=False), encoding="utf-8")
            make_assets(d)
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("cv-img", (d / "build" / "d.html").read_text(encoding="utf-8"))
            from pptx import Presentation
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            prs = Presentation(str(d / "build" / "d.pptx"))
            self.assertEqual(sum(sh.shape_type == MSO_SHAPE_TYPE.PICTURE for sh in prs.slides[0].shapes), 1)


class QaAttributeTests(unittest.TestCase):
    def test_data_max_lines_on_title_and_lead(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "bullets", "title": "短い見出し", "lead": "リードの文", "bullets": ["a", "b"]}))
            self.assertEqual(build(d, "--html").returncode, 0)
            html = (d / "build" / "d.html").read_text(encoding="utf-8")
            self.assertRegex(html, r'role="heading" aria-level="1" data-max-lines="1"')
            self.assertIn('data-max-lines="', html.split("リードの文")[0].rsplit("<div", 1)[1])

    def test_check_layout_lines_does_not_fail_fixed_height_box(self):
        """固定高の箱（タイトル h=64）に 1 行で収まる文は、data-max-lines=1 でも lines に出ない（実測は行ボックス）。"""
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, one({"type": "bullets", "title": "短い見出し", "lead": "リード", "bullets": ["a", "b"]}))
            self.assertEqual(build(d, "--html").returncode, 0)
            r = subprocess.run([PY, str(TOOLS / "check_layout.py"), str(d)], capture_output=True, text=True, encoding="utf-8")
            self.assertIn("lines=0", r.stdout + r.stderr)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_canvas_qa_ignore_attribute(self):
        el = {"kind": "shape", "x": 0, "y": 0, "w": 10, "h": 10, "fill": "#000000", "qa_ignore": "overlap contrast bogus"}
        html = ce.canvas_html({"elements": [el]})
        self.assertIn('data-qa-ignore="overlap contrast"', html)
        self.assertNotIn("bogus", html)
        self.assertNotIn("data-qa-ignore", ce.canvas_html({"elements": [{**el, "qa_ignore": None}]}))

    def test_code_overflow_warns(self):
        code = "\n".join(f"line {i} = compute(value_{i}) + 1" for i in range(40)) + "\nx=" + "a" * 150
        exc, err = validate(one({"type": "code", "title": "コード", "code": code}))
        self.assertIsNone(exc)
        self.assertIn("枠の高さを約", err)
        self.assertIn("2 枚に分ける", err)
        self.assertIn("枠の幅を約", err)
        exc, err = validate(one({"type": "code", "title": "コード", "code": "print(1)\nprint(2)"}))
        self.assertNotIn("枠の高さ", err)

    def test_fit_code_size_is_unchanged(self):
        r = {"size": 20, "line_height": 1.45, "pad": 28, "w": 1136, "h": 452, "min_size": 13}
        size, lines = b.fit_code_size("a\nb\nc", r)
        self.assertEqual((size, lines), (20, ["a", "b", "c"]))
        size, _ = b.fit_code_size("\n".join("x" * 10 for _ in range(30)), r)
        self.assertLess(size, 20)


# ---------------------------------------------------------------------------
# レビュー指摘の修正（s2a-C-01〜C-10 / A-01〜A-10）
# ---------------------------------------------------------------------------
PHOTO_PAT = {"name": "photo-caption", "frame": "body", "size": [1136, 400], "background": "background",
             "slots": {"photo": {"kind": "image", "required": True, "label": "写真", "example": "assets/wide.png"},
                       "head": {"kind": "text", "example": "見出し"}},
             "elements": [{"kind": "image", "name": "写真", "x": 0, "y": 0, "w": 500, "h": 400, "path": "{{photo}}",
                           "alt": "写真", "fit": "cover"}]}


def deck_with_photo_pattern(t, example="assets/wide.png"):
    d = write_deck(t, one({"type": "pattern", "pattern": "photo-caption", "title": "x", "slots": {"photo": "assets/wide.png"}}), "deck")
    (d / "patterns").mkdir()
    pat = json.loads(json.dumps(PHOTO_PAT))
    pat["slots"]["photo"]["example"] = example
    (d / "patterns" / "photo-caption.json").write_text(json.dumps(pat, ensure_ascii=False), encoding="utf-8")
    make_assets(d)
    return d


class PreviewFixTests(unittest.TestCase):
    def run_preview(self, *args):
        return subprocess.run([PY, str(TOOLS / "pattern_engine.py"), "preview", *args], capture_output=True, text=True, encoding="utf-8")

    def test_preview_builds_deck_with_image_slot_pattern_html_and_pptx(self):
        """C-01 / A-02: 画像スロットを持つデッキ専用の型があっても preview は全体をビルドできる（PPTX まで）"""
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            r = self.run_preview("--deck", str(d))
            self.assertEqual(r.returncode, 0, r.stderr)
            out = d / "build" / "pattern-preview"
            self.assertTrue((out / "assets" / "wide.png").exists())
            self.assertTrue(any((out / "build").glob("*.pptx")))
            self.assertIn("cv-img", next((out / "build").glob("*.html")).read_text(encoding="utf-8"))

    def test_preview_skips_pattern_whose_example_image_is_missing(self):
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t, example="assets/none.png")
            r = self.run_preview("--deck", str(d), "--html")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("photo-caption", r.stderr)
            self.assertIn("example", r.stderr)
            deck = json.loads((d / "build" / "pattern-preview" / "deck.json").read_text(encoding="utf-8"))
            self.assertNotIn("photo-caption", [s["pattern"] for s in deck["slides"]])
            self.assertIn("numbered-columns", [s["pattern"] for s in deck["slides"]])

    def test_preview_refuses_to_overwrite_a_real_deck(self):
        """C-02: --out にデッキ自身を指しても deck.json を上書きしない（--force なら上書き）"""
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            before = (d / "deck.json").read_text(encoding="utf-8")
            r = self.run_preview("--deck", str(d), "--out", str(d), "--html")
            self.assertEqual(r.returncode, 1)
            self.assertIn("上書き", r.stderr)
            self.assertEqual((d / "deck.json").read_text(encoding="utf-8"), before)
            # 確認用デッキ（前回の出力）は作り直せる
            out = d / "pv"
            self.assertEqual(self.run_preview("--deck", str(d), "--out", str(out), "--html").returncode, 0)
            self.assertEqual(self.run_preview("--deck", str(d), "--out", str(out), "--html").returncode, 0)
            r = self.run_preview("--deck", str(d), "--out", str(d), "--html", "--force")
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_preview_missing_deck_dir_is_an_error_not_a_traceback(self):
        r = self.run_preview("--deck", "/nonexistent-deck-dir-xyz", "--html")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("見つかりません", r.stderr)

    def test_preview_notes_have_no_absolute_path(self):
        """C-08: notes にローカルの絶対パスを入れない"""
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            deck, _ = pe.preview_deck(d, "default")
            for s in deck["slides"]:
                self.assertNotIn(str(Path(t)), s["notes"])
                self.assertNotIn("/Users/", s["notes"])
            notes = {s["pattern"]: s["notes"] for s in deck["slides"]}
            self.assertIn("同梱", notes["numbered-columns"])
            self.assertIn("patterns/photo-caption.json", notes["photo-caption"])

    def test_sample_of_body_frame_pattern_is_a_pattern_slide(self):
        """C-06: frame:body の型の sample は type:pattern のスライドで出し、ビルドできる"""
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "sm"
            r = subprocess.run([PY, str(TOOLS / "pattern_engine.py"), "sample", "keyword-explain", "--out", str(out)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            deck = json.loads((out / "deck.json").read_text(encoding="utf-8"))
            self.assertTrue(all(s["type"] == "pattern" and s.get("title") for s in deck["slides"]))
            self.assertEqual(build(out, "--html").returncode, 0)


class FullFramePatternTests(unittest.TestCase):
    SLOTS = {"eyebrow": "推進", "title": "3 つの柱", "pillars": [{"head": "A", "body": "a"}, {"head": "B", "body": "b"}, {"head": "C", "body": "c"}],
             "foundation": "土台"}

    def test_full_frame_warns_for_undrawn_top_level_keys(self):
        """C-03 / A-04: frame:full の型でスライド直下の lead / conclusion / source / style は描かれないので警告する"""
        sl = {"type": "pattern", "pattern": "pillars", "title": "見出し", "lead": "リード", "conclusion": "結論", "source": "出典",
              "style": {"title": {"size": 20}}, "slots": self.SLOTS}
        exc, err = validate(one(sl))
        self.assertIsNone(exc)
        self.assertIn("スライド直下の lead は描かれません", err)
        self.assertIn("slots の \"lead\" に書いてください", err)           # この型は lead スロットを持つ
        self.assertIn("スライド直下の conclusion は描かれません", err)
        self.assertIn("結論帯を持ちません", err)                              # conclusion スロットは無い
        self.assertIn("出典", err)
        self.assertIn("style（title）は効きません", err)

    def test_full_frame_does_not_warn_about_undrawn_title_and_lead_size(self):
        sl = {"type": "pattern", "pattern": "pillars", "title": "あ" * 108, "slots": self.SLOTS}
        exc, err = validate(one({**sl, "lead": "い" * 240}))
        self.assertNotIn("まで縮めても", err)
        self.assertNotIn("タイトルを短く", err)

    def test_body_frame_still_measures_title(self):
        sl = {"type": "pattern", "pattern": "numbered-columns", "title": "あ" * 108,
              "slots": {"items": [{"head": "a", "body": "b"}] * 3}}
        exc, err = validate(one(sl))
        self.assertIn("タイトル", err)

    def test_body_frame_tiny_rect_fails_or_warns(self):
        """C-10"""
        base = {"type": "pattern", "pattern": "keyword-explain", "title": "t",
                "slots": {"keyword": "k", "points": [{"head": "a", "body": "b"}, {"head": "c", "body": "d"}]}}
        exc, err = validate(one({**base, "style": {"body": {"w": 0}}}))
        self.assertIsNotNone(exc)
        self.assertIn("0 以下", str(exc) + err)
        exc, err = validate(one({**base, "style": {"body": {"h": 10}}}))
        self.assertIsNone(exc)
        self.assertIn("縮めます", err)
        exc, err = validate(one(base))
        self.assertNotIn("縮めます", err)


class PatternImageAltTests(unittest.TestCase):
    def test_slot_alt_overrides_fixed_alt_in_html_and_pptx(self):
        """A-10"""
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            deck = json.loads((d / "deck.json").read_text(encoding="utf-8"))
            deck["slides"][0]["slots"]["photo_alt"] = "会議室の様子"
            (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("photo_alt", r.stderr)                                # 未知スロットの警告にならない
            self.assertIn('alt="会議室の様子"', (d / "build" / "d.html").read_text(encoding="utf-8"))
            import zipfile
            with zipfile.ZipFile(d / "build" / "d.pptx") as z:
                self.assertIn('descr="会議室の様子"', z.read("ppt/slides/slide1.xml").decode("utf-8"))

    def test_without_slot_alt_the_pattern_alt_is_used(self):
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            self.assertEqual(build(d, "--html").returncode, 0)
            self.assertIn('alt="写真"', (d / "build" / "d.html").read_text(encoding="utf-8"))


class PatternSvgBrowserTests(unittest.TestCase):
    def test_pattern_needs_svg_detects_svg_slot(self):
        """C-05: SVG の画像スロットがある pattern スライドは共有ブラウザを使う対象"""
        with tempfile.TemporaryDirectory() as t:
            d = deck_with_photo_pattern(t)
            sl = {"type": "pattern", "pattern": "photo-caption", "slots": {"photo": "assets/mark.svg"}}
            self.assertTrue(b._pattern_needs_svg(sl, d))
            self.assertFalse(b._pattern_needs_svg({**sl, "slots": {"photo": "assets/wide.png"}}, d))
            self.assertFalse(b._pattern_needs_svg({"type": "pattern", "pattern": "pillars", "slots": {}}, d))


class SeriesColorsTests(unittest.TestCase):
    def chart(self, sc):
        return one({**CHART, "series": [{"name": "a", "values": [1, 2, 3]}, {"name": "b", "values": [2, 3, 4]}],
                    "style": {"body": {"series_colors": sc}}})

    def test_series_colors_are_validated(self):
        """C-04"""
        exc, err = validate(self.chart(["nope"]))
        self.assertIsNotNone(exc)
        self.assertIn("不明な色指定 'nope'", str(exc) + err)
        exc, err = validate(self.chart("primary"))
        self.assertIsNotNone(exc)
        self.assertIn("色の配列", str(exc) + err)
        exc, err = validate(self.chart([1, 2]))
        self.assertIsNotNone(exc)
        self.assertIn("色の配列", str(exc) + err)
        for ok in (["primary", "#12AB34"], []):
            exc, err = validate(self.chart(ok))
            self.assertIsNone(exc, err)


class DatavizFixTests(unittest.TestCase):
    def test_y_limit_warning_shows_value_as_written(self):
        """C-09"""
        deck = one({**CHART, "series": [{"name": "a", "values": [1, 2, 3]}], "y": {"min": 2, "max": 2.5}})
        exc, err = validate(deck)
        r = build_text(deck)
        self.assertIn("y.max（2.5）", r)

    def test_line_with_single_point_warns_and_is_not_on_baseline(self):
        """A-03"""
        deck = one({"type": "chart", "chart": "line", "title": "t", "categories": ["a", "b"], "series": [{"name": "s", "values": [5, None]}]})
        r = build_text(deck)
        self.assertIn("2 点以上", r)
        import dataviz_engine as dv
        import proposal_engine as pe_
        theme = b.load_theme("default", b.theme_dirs(None))
        layout = b.load_layout("default", None)
        st = b.resolve_style(layout, deck, deck["slides"][0])
        els = dv.layout_chart(deck["slides"][0], st, pe_.Ctx(theme), pe_.body_region(deck["slides"][0], st))
        pts = [e for e in els if str(e.get("name", "")).startswith("点:")]
        axis_y = min(e["y"] for e in els if e.get("geom") == "custom")      # 基線
        self.assertEqual(len(pts), 1)
        self.assertLess(pts[0]["y"], axis_y - 100)          # 点は基線に貼り付かず、0〜5 のレンジの上端にある

    def test_kpi_numeric_value_digit_check(self):
        """A-07"""
        for v in (12345678901234, "12345678901234"):
            exc, err = validate(one({"type": "kpi", "title": "t", "items": [{"value": v, "label": "l"}]}))
            self.assertIn("桁が多すぎます", err, repr(v))
        exc, err = validate(one({"type": "kpi", "title": "t", "items": [{"value": 1234567, "label": "l"}]}))
        self.assertNotIn("桁が多すぎます", err)

    def test_chart_note_does_not_split_word(self):
        """A-05: 注釈パネルは文節の切れ目で折り返す（「システ/ム」で切らない）"""
        import dataviz_engine as dv
        import proposal_engine as pe_
        sl = {**CHART, "chart": "stacked", "categories": ["7月", "8月"], "series": [{"name": "手続き", "values": [120, 130]}, {"name": "システム", "values": [60, 55]}],
              "note": "手続きの質問は横ばい。システムの質問は減っている"}
        deck = one(sl)
        theme = b.load_theme("default", b.theme_dirs(None))
        st = b.resolve_style(b.load_layout("default", None), deck, sl)
        els = dv.layout_chart(sl, st, pe_.Ctx(theme), pe_.body_region(sl, st))
        panel = [e for e in els if e.get("name") == "読み取り"][0]
        lines = [p["runs"][0]["text"] for p in panel["text"]["paragraphs"]]
        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines), sl["note"])
        for ln in lines[:-1]:
            self.assertFalse(ln.endswith(("シス", "システ")), lines)         # 語の途中で切れていない


def build_text(deck):
    with tempfile.TemporaryDirectory() as t:
        d = write_deck(t, deck)
        r = build(d, "--html")
        return r.stdout + r.stderr


class CanvasFixTests(unittest.TestCase):
    def test_qa_ignore_on_image_group_table_and_validation(self):
        """C-07"""
        shape = {"kind": "shape", "x": 0, "y": 0, "w": 10, "h": 10, "fill": "#000000"}
        els = [{"kind": "image", "x": 0, "y": 0, "w": 10, "h": 10, "path": "assets/a.png", "qa_ignore": "overlap"},
               {"kind": "group", "children": [shape], "qa_ignore": ["lines"]},
               {"kind": "table", "x": 0, "y": 0, "cols": [50], "rows": [{"h": 20, "cells": [{"paragraphs": [{"runs": [{"text": "a"}]}]}]}],
                "qa_ignore": "contrast"}]
        html = ce.canvas_html({"elements": els})
        self.assertIn('class="cv-s cv-ph" data-qa-ignore="overlap"', html)
        self.assertIn('class="cv-grp" data-qa-ignore="lines"', html)
        self.assertIn('class="cv-tb" data-qa-ignore="contrast"', html)
        warns = []
        ce.validate_canvas_problems({"elements": [{**shape, "qa_ignore": 5}, {**shape, "qa_ignore": "overlpa"}]}, None, warns.append)
        self.assertEqual(len(warns), 2)
        self.assertIn("もしかして: overlap", warns[1])

    def test_pptx_bullet_has_color_and_size(self):
        """A-09"""
        el = {"kind": "shape", "x": 0, "y": 0, "w": 300, "h": 100, "text": {"paragraphs": [
            {"bullet": {"char": "●", "color": "#566781", "size": 12}, "marL": 20, "indent": -20,
             "runs": [{"text": "a", "size": 24, "color": "#000000"}]}]}}
        xml = ce._paras_xml(el["text"]["paragraphs"])
        self.assertIn('<a:buClr><a:srgbClr val="566781"/></a:buClr>', xml)
        self.assertIn('<a:buSzPct val="50000"/>', xml)
        self.assertLess(xml.index("buClr"), xml.index("buChar"))

    def test_corrupt_image_falls_back_to_placeholder_in_html_and_pptx(self):
        """A-01"""
        with tempfile.TemporaryDirectory() as t:
            d = write_deck(t, {"meta": {"id": "d", "title": "T", "theme": "default"}, "slides": [
                {"type": "canvas", "elements": [{"kind": "image", "x": 10, "y": 10, "w": 300, "h": 200, "path": "assets/bad.png", "alt": "壊れた"}]}]})
            (d / "assets").mkdir()
            (d / "assets" / "bad.png").write_text("not a png", encoding="utf-8")
            r = build(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("読み込めません", r.stderr)
            self.assertIn("灰色の枠", r.stderr)
            self.assertEqual(r.stderr.count("読み込めません"), 1)          # HTML と PPTX で警告が重ならない
            html = (d / "build" / "d.html").read_text(encoding="utf-8")
            self.assertIn("cv-ph", html)
            self.assertIn("壊れた", html)


if __name__ == "__main__":
    unittest.main()

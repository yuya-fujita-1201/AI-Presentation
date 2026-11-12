#!/usr/bin/env python3
"""同梱の型 19 個（templates/patterns/）の品質テスト: check がエラー 0・警告 0、全個数・長文・短文で例外なし、
標準の本文領域で文字が小さくならない、show の例がそのまま警告なしで通る、画像つきの型が preview に並ぶ。

    python -m unittest tools/test_pattern_library.py
"""
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import canvas_engine as ce  # noqa: E402
import pattern_engine as pe  # noqa: E402

THEME = pe._default_theme()
EXPECTED = {
    "before-after", "big-number-context", "checklist", "compare-options", "conclusion-evidence", "funnel", "icon-grid", "keyword-explain",
    "numbered-columns", "numbered-list", "photo-caption", "pillars", "problem-solution", "pyramid", "quote-block", "quote-photo",
    "roadmap-lanes", "team", "timeline"}
NARROW_OK = {"numbered-list", "checklist", "big-number-context", "quote-block", "funnel", "icon-grid", "numbered-columns", "keyword-explain", "problem-solution",
             "timeline", "compare-options", "team", "roadmap-lanes", "pyramid", "photo-caption", "quote-photo"}      # 本文枠の 16 型すべて
SHORT_OK = {"icon-grid", "numbered-columns", "keyword-explain", "problem-solution", "timeline", "compare-options", "team", "photo-caption", "checklist"}   # 高さ 340px 未満の短い構図を持つ型


def bundled():
    return [(n, p) for n, _path, p, _e in pe.list_patterns() if p]


def counts_of(p):
    vb = p.get("variants_by")
    slots = p["slots"]
    if vb and slots.get(vb, {}).get("kind") in ("list", "records"):
        return list(range(slots[vb].get("min", 1), slots[vb].get("max", 3) + 1))
    return [None]


def run_sizes(els):
    out = []
    for e in ce.flatten(els):
        for para in (e.get("text") or {}).get("paragraphs", []):
            for r in para.get("runs", []):
                if isinstance(r.get("size"), (int, float)) and r.get("text"):
                    out.append(r["size"])
    return out


class BundledPatternsTest(unittest.TestCase):
    def test_nineteen_patterns_and_names(self):
        self.assertEqual({n for n, _ in bundled()}, EXPECTED)

    def test_check_is_clean(self):
        for n, p in bundled():
            errs, warns = pe.check_pattern(p, THEME)
            self.assertEqual((errs, warns), ([], []), n)

    def test_every_count_renders_without_warnings_and_inside_the_design_size(self):
        for n, p in bundled():
            for c in counts_of(p):
                warns, errs = [], []
                els, _bg = pe.expand(pe.example_slide(p, c), p, THEME, {"meta": {"title": "T", "brand": "B"}}, 1, 5, warns.append, errs)
                self.assertEqual((warns, errs), ([], []), f"{n} {c}")
                self.assertEqual(ce.validate_canvas_problems({"elements": els}), [], f"{n} {c}")

    def test_over_max_is_cut_not_drawn(self):
        for n, p in bundled():
            vb = p.get("variants_by")
            if not vb:
                continue
            mx = p["slots"][vb]["max"]
            warns = []
            els_a, _ = pe.expand(pe.example_slide(p, mx + 2), p, THEME, None, 1, 1, warns.append, [])
            els_b, _ = pe.expand(pe.example_slide(p, mx), p, THEME, None, 1, 1, lambda m: None, [])
            self.assertTrue(any("先頭の" in w for w in warns), n)
            self.assertEqual(len(els_a), len(els_b), n)

    def test_text_is_not_small_in_the_standard_body_region(self):
        """標準の本文領域（結論帯なし 1136x452・結論帯あり 1136x380）で、文字が 15px（結論帯ありは 14px）を下回らない（札・注記を除く最小値）"""
        for n, p in bundled():
            if pe.frame_of(p) != "body":
                continue
            for rect, floor in (((0, 0, 1136, 452), 15.0), ((0, 0, 1136, 380), 14.0)):
                for c in counts_of(p):
                    els = pe.pattern_block_elements(pe.example_slide(p, c), p, rect, THEME, None, 1, 1, None, [])
                    self.assertGreaterEqual(min(run_sizes(els)), floor, f"{n} {c} {rect}")

    def test_every_body_pattern_has_narrow_levels(self):
        body = {n for n, p in bundled() if pe.frame_of(p) == "body"}
        self.assertEqual(body, NARROW_OK)
        for n in sorted(body):
            p = pe.load_pattern(n)
            self.assertEqual([int(pe._below(x)) for x in pe.base_levels(p)], [700, 1000], n)         # 幅だけで選ぶ段: 700 未満・700〜1000 未満の 2 段
            fl = pe.narrow_floor(p)
            self.assertTrue(360 <= fl <= 480, (n, fl))                                  # 実測した下限（440 固定ではない）
            for c, v in pe.count_floors(p).items():
                self.assertGreater(v, fl, (n, c))                                       # 個数別の下限は、基準より厳しい個数だけに書く
                self.assertLessEqual(v, 520, (n, c))
        for n in sorted(SHORT_OK):
            lv = pe.narrow_levels(pe.load_pattern(n))
            self.assertEqual(sorted((int(pe._below(x)), pe._below_h(x)) for x in lv if pe._below_h(x)), [(700, 340), (1000, 340)] if n not in ("icon-grid",) else [(700, 340)], n)
            self.assertFalse(any("no_max_width" in x for x in lv), n)      # 幅 1000px 以上の短いブロックは、広い構図を縮めて置く（縦のリストにしない）

    def test_text_is_readable_at_half_and_two_thirds_width(self):
        """半幅（556）・3 分の 2 幅（741）× 高さ 400 と 300 のブロックで、全個数の例が警告なし・描かれる最小文字 12px 以上。
        高さ 340px 未満は短い構図（below_h）に切り替わる"""
        for n in sorted(NARROW_OK):
            p = pe.load_pattern(n)
            for w in (556, 741):
                for h in (400, 300):
                    for c in counts_of(p):
                        sl = pe.example_slide(p, c)
                        els = pe.pattern_block_elements(sl, p, (0, 0, w, h), THEME, None, 1, 1, None, [])
                        self.assertGreaterEqual(min(run_sizes(els)), 12.0, f"{n} {c} w={w} h={h}")
                        warns = []
                        pe.expand(sl, pe.effective_pattern(p, w, h), THEME, None, 1, 1, warns.append, [])
                        self.assertEqual(warns, [], f"{n} {c} w={w} h={h}")
                        _f, bw = pe.body_rect_problems(sl, p, {"x": 0, "y": 0, "w": w, "h": h}, in_block=True)
                        self.assertEqual(bw, [], f"{n} {c} w={w} h={h}")
                        if n == "photo-caption":
                            continue
                        # validate（ビルドが呼ぶ）の文字の実測の警告も出ない
                        vw = []
                        pe.validate(dict(sl, type="pattern", pattern=n, title="t", _block=1, style={"body": {"w": w, "h": h}}), 0, None, lambda m: None, vw.append, THEME, rect_w=w, rect_h=h)
                        self.assertEqual([m for m in vw if "文字が最小" in m], [], f"{n} {c} w={w} h={h}")

    def test_below_the_floor_warns_with_an_alternative(self):
        for n in sorted(NARROW_OK):
            p = pe.load_pattern(n)
            self.assertTrue(isinstance(p.get("block_alt"), str) and p["block_alt"].strip(), n)
            _f, warns = pe.body_rect_problems(pe.example_slide(p), p, {"x": 0, "y": 0, "w": 340, "h": 400}, in_block=True)
            self.assertTrue(any("以上向きです（いま 340px）" in w and p["block_alt"] in w for w in warns), (n, warns))

    def test_reducing_the_count_clears_the_width_warning(self):
        """警告の「項目を n 個までにする」を実行すると、その警告は消える（個数別の下限が全型にあり、減らして効くときだけ提案する）"""
        for n in sorted(NARROW_OK):
            p = pe.load_pattern(n)
            cf = pe.count_floors(p)
            for c, need in sorted(cf.items()):
                w = int(need) - 10
                sl = pe.example_slide(p, c)
                _f, warns = pe.body_rect_problems(sl, p, {"x": 0, "y": 0, "w": w, "h": 400}, in_block=True)
                wide = [m for m in warns if "以上向きです" in m]
                self.assertEqual(len(wide), 1, (n, c, w, warns))
                m = re.search(r"項目を (\d+) 個までにする", wide[0])
                if m:
                    c2 = int(m.group(1))
                    self.assertLess(c2, c)
                    _f, w2 = pe.body_rect_problems(pe.example_slide(p, c2), p, {"x": 0, "y": 0, "w": w, "h": 400}, in_block=True)
                    self.assertEqual([x for x in w2 if "以上向きです" in x], [], (n, c, c2, w))

    def test_four_options_need_500px(self):
        p = pe.load_pattern("compare-options")
        sl = pe.example_slide(p, 4)
        _f, w = pe.body_rect_problems(sl, p, {"x": 0, "y": 0, "w": 480, "h": 400}, in_block=True)
        self.assertTrue(any("4 個のとき 幅 500px 以上向き" in x for x in w), w)
        self.assertTrue(any("項目を 3 個までにする" in x for x in w), w)
        _f, w = pe.body_rect_problems(sl, p, {"x": 0, "y": 0, "w": 556, "h": 400}, in_block=True)
        self.assertEqual(w, [])
        _f, w = pe.body_rect_problems(pe.example_slide(p, 3), p, {"x": 0, "y": 0, "w": 450, "h": 400}, in_block=True)
        self.assertTrue(any("幅 470px 以上向き" in x for x in w), w)

    def test_list_column_uses_the_measured_floors(self):
        for n in sorted(NARROW_OK):
            p = pe.load_pattern(n)
            mark, text = pe.block_class(p)
            self.assertEqual(mark, "◎", n)                       # 全個数で半幅（約 556px）から読める
            self.assertIn(f"{int(math.ceil(pe.max_floor(p) / 10.0) * 10)}px〜", text)
        self.assertEqual(pe.block_class(pe.load_pattern("pillars")), ("×", "×"))

    def test_no_orphan_or_overflow_in_realistic_content_with_year_dates(self):
        """年つきの日付（2027年11月）が 2 行に割れない（timeline）。値 7 字・4 案の比較表で最終行が 1〜2 字にならない"""
        p = pe.load_pattern("timeline")
        for w in (480, 556, 640, 741, 900, 1010, 1136):
            for h in (300, 400):
                sl = pe.example_slide(p, 6)
                for it in sl["slots"]["items"]:
                    it["date"] = "2027年11月"
                warns = []
                pe.expand(sl, pe.effective_pattern(p, w, h), THEME, None, 1, 1, warns.append, [])
                self.assertEqual(warns, [], (w, h))
        p = pe.load_pattern("compare-options")
        for w in (556, 741, 900, 1136):
            sl = pe.example_slide(p, 4)
            for r in sl["slots"]["rows"]:
                r["values"] = ["初期費用は年間"] * 4
            warns = []
            pe.expand(sl, pe.effective_pattern(p, w, 400), THEME, None, 1, 1, warns.append, [])
            self.assertEqual(warns, [], w)

    def test_pyramid_apex_text_stays_inside_the_trapezoid(self):
        """頂点の段の文字枠は、台形の上辺の幅より狭く、長い名前（6 字）は文字が縮んで枠に収まる（白い文字が台形の外に出ない）"""
        p = pe.load_pattern("pyramid")
        for w in (480, 556, 741, 900):
            for n in (3, 5):
                sl = pe.example_slide(p, n)
                sl["slots"]["tiers"][0]["name"] = "長期ビジョン"
                warns = []
                els, _ = pe.expand(sl, pe.effective_pattern(p, w, 400), THEME, None, 1, 1, warns.append, [])
                self.assertEqual(warns, [], (w, n))
                flat = ce.flatten(els)
                tri = next(e for e in flat if str(e.get("name", "")).startswith("1段目の面"))
                name = next(e for e in flat if str(e.get("name", "")).startswith("1段目の名前"))
                path = tri["path"][0]["cmds"]
                top_w = path[1][1] - path[0][1]                       # 台形の上辺の幅
                bot_w = path[2][1] - path[3][1]
                self.assertLess(name["w"], bot_w, (w, n))
                self.assertLessEqual(name["w"], top_w + (bot_w - top_w) * 0.35 + 0.5, (w, n))
                size = name["text"]["paragraphs"][0]["runs"][0]["size"]
                self.assertLessEqual(size * 3 + 1, name["w"] * 2 + 1)                # 6 字が 2 行までに収まる大きさ

    def test_numbered_columns_five_max_length_items_warn_instead_of_shrinking_silently(self):
        """5 項目 × 70 字いっぱいは、説明 13px 未満で黙って縮まず「収まらない」警告を出す（狭い構図）"""
        p = pe.load_pattern("numbered-columns")
        sl = pe.example_slide(p, 5)
        for it in sl["slots"]["items"]:
            it["body"] = "今の手順と所要時間を一覧にして、時間のかかる箇所を数字で示し、次の一手を早く決める。数字で進み具合を見て、改善を続ける"[:70]
        warns = []
        els, _ = pe.expand(sl, pe.effective_pattern(p, 556, 400), THEME, None, 1, 1, warns.append, [])
        self.assertTrue(any("収まりません" in m for m in warns), warns)
        self.assertGreaterEqual(min(run_sizes(els)), 13.0 - 1e-6)

    def test_wide_construction_is_unchanged_at_1000px_and_up(self):
        """幅 1000px 以上は従来の広い構図（狭い構図の段は below 1000 未満だけ）"""
        for n in sorted(NARROW_OK):
            p = pe.load_pattern(n)
            self.assertIs(pe.effective_pattern(p, 1000), p, n)
            self.assertIs(pe.effective_pattern(p, 1136), p, n)

    def test_show_example_validates_without_warnings(self):
        for n, p in bundled():
            sl = pe.show_example_slide(p)
            fails, warns = [], []
            pe.validate(sl, 0, None, fails.append, warns.append)
            self.assertEqual((fails, warns), ([], []), n)
            # 例は同梱の画像（利用者のデッキには無い）を指さない
            self.assertNotIn("sample-", json.dumps(sl, ensure_ascii=False), n)

    def test_show_example_builds_in_an_empty_deck(self):
        """show の例を、assets/ の無い空のデッキに貼ってそのままビルドできる（pe-C-01）"""
        import build_deck
        for n, p in bundled():
            sl = pe.show_example_slide(p)
            with tempfile.TemporaryDirectory() as td:
                d = Path(td)
                (d / "deck.json").write_text(json.dumps({"meta": {"title": "t"}, "slides": [sl]}, ensure_ascii=False), encoding="utf-8")
                r = subprocess.run([sys.executable, str(TOOLS / "build_deck.py"), "--html", str(d)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{n}: {r.stderr[-400:]}")
                self.assertNotIn("警告", r.stdout + r.stderr, f"{n}: {(r.stdout + r.stderr)[-400:]}")

    def test_show_prints_how_to_use_the_image_slot(self):
        import io
        import contextlib
        for n in ("photo-caption", "quote-photo"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
                pe.main(["show", n])
            out = buf.getvalue()
            self.assertIn("assets/", out)
            self.assertIn("画像スロット 'photo'", out)

    def test_summary_for_every_pattern(self):
        for n, p in bundled():
            self.assertTrue(isinstance(p.get("summary"), str) and 8 <= len(p["summary"]) <= 70, n)

    def test_checklist_state_aliases_and_flag_timeline(self):
        p = pe.load_pattern("checklist")
        sl = {"slots": {"items": [{"text": "a", "state": "完了"}, {"text": "b", "state": "false"}, {"text": "c", "state": "進行中"}, {"text": "d"}]}}
        warns = []
        els, _ = pe.expand(sl, p, THEME, None, 1, 1, warns.append, [])
        names = [e["name"] for e in ce.flatten(els) if e.get("name")]
        self.assertIn("項目1のチェック", names)
        self.assertIn("項目3の進行中の印", names)
        self.assertNotIn("項目2のチェック", names)                  # "false" は完了にならない
        t = pe.load_pattern("timeline")
        sl = {"slots": {"items": [{"date": "1 月", "head": "a", "body": "b", "now": "false"}, {"date": "2 月", "head": "c", "body": "d", "now": True}, {"date": "3 月", "head": "e", "body": "f"}]}}
        els, _ = pe.expand(sl, t, THEME, None, 1, 1, lambda m: None, [])
        flat = [e for e in ce.flatten(els) if e.get("name")]
        self.assertEqual([e["name"] for e in flat if "現在地" in e["name"]].count("節目2の現在地タグ"), 1)
        self.assertEqual(len([e for e in flat if e["name"].endswith("の現在地タグ")]), 1)

    def test_compare_options_values_by_position(self):
        p = pe.load_pattern("compare-options")
        sl = {"slots": {"options": [{"name": "甲"}, {"name": "乙"}], "rows": [{"label": "費用", "values": ["高", "低"]}, {"label": "期間", "values": ["長"]}]}}
        errs, warns = pe.slot_problems(sl, p)
        self.assertEqual(errs, [])
        self.assertEqual(len([w for w in warns if "'values'" in w]), 1)
        els, _ = pe.expand(sl, p, THEME, None, 1, 1, lambda m: None, [])
        texts = ["".join(r.get("text", "") for pa in (e.get("text") or {}).get("paragraphs", []) for r in pa["runs"]) for e in ce.flatten(els)]
        self.assertIn("高", texts)
        self.assertIn("―", texts)

    def test_numbered_columns_with_five_long_items_fits(self):
        p = pe.load_pattern("numbered-columns")
        sl = pe.example_slide(p, 5)
        for it in sl["slots"]["items"]:
            it["body"] = "今の手順と所要時間を一覧にして、時間のかかる箇所を数字で示す"
        warns = []
        els, _ = pe.expand(sl, p, THEME, None, 1, 1, warns.append, [])
        self.assertEqual(warns, [])                                   # 5 項目・長めの文でも「収まらない」警告が出ない


class PreviewWithImagesTest(unittest.TestCase):
    def test_preview_lists_the_image_patterns_and_copies_their_images(self):
        import tempfile
        deck, errors = pe.preview_deck(None, "default")
        self.assertEqual(errors, [])
        names = [s["pattern"] for s in deck["slides"]]
        self.assertIn("quote-photo", names)
        self.assertIn("photo-caption", names)
        with tempfile.TemporaryDirectory() as t:
            n = pe._copy_preview_assets(deck, None, Path(t))
            self.assertGreaterEqual(n, 2)
            self.assertTrue((Path(t) / "assets" / "sample-portrait.png").is_file())
            self.assertTrue((Path(t) / "assets" / "sample-landscape.png").is_file())


if __name__ == "__main__":
    unittest.main()

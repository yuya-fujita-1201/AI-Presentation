"""lint_deck_text の拡張ルール（主張の書き方・表・数・relation・リズム・日付）のテスト。"""
import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import lint_deck_text as L  # noqa: E402


class ClaimTests(unittest.TestCase):
    def test_vague_and_layout_desc(self):
        w = L.check_claims("s", {"title": "導入効果", "lead": "左に現状、右に施策など様々な観点を示す。"})
        self.assertTrue(any("曖昧語" in x and "など" in x for x in w))
        self.assertTrue(any("構成の説明" in x for x in w))

    def test_title_layout_words_only_slide_reference(self):
        # タイトルの「上図」等は話題名として普通に使うので、本スライド/このスライドだけ拾う
        self.assertFalse(any("構成の説明" in x for x in L.check_claims("s", {"title": "上図の読み方"})))
        self.assertTrue(any("構成の説明" in x for x in L.check_claims("s", {"title": "本スライドの要点"})))

    def test_noun_ending_lead(self):
        w = L.check_claims("s", {"lead": "問い合わせ対応の自動化による工数40%削減"})
        self.assertTrue(any("体言止め" in x for x in w))
        self.assertFalse(any("体言止め" in x for x in L.check_claims("s", {"lead": "問い合わせ対応を自動化し、工数を40%減らす。"})))
        self.assertFalse(any("体言止め" in x for x in L.check_claims("s", {"lead": "問い合わせ対応を自動化して工数を減らせる"})))

    def test_lead_restates_title(self):
        w = L.check_claims("s", {"title": "問い合わせ対応を自動化する", "lead": "問い合わせ対応を自動化する。"})
        self.assertTrue(any("言い直し" in x for x in w))
        w = L.check_claims("s", {"title": "問い合わせ対応を自動化する", "lead": "一次回答をAIが返し、担当者は例外だけを見る。"})
        self.assertFalse(any("言い直し" in x for x in w))


class TableNumberTests(unittest.TestCase):
    def test_vague_columns_only_for_tables(self):
        self.assertTrue(L.check_tables("s", {"type": "table", "columns": ["施策", "概要"]}, []))
        self.assertEqual(L.check_tables("s", {"type": "cards", "columns": 3}, []), [])

    def test_rating_legend(self):
        s = {"type": "table", "columns": ["案", "費用"], "rows": [["A", "◎"], ["B", "△"]]}
        texts = list(L.iter_texts(s))
        self.assertTrue(any("凡例" in x for x in L.check_tables("s", s, texts)))
        s["lead"] = "◎=優れる、△=課題あり"
        self.assertFalse(any("凡例" in x for x in L.check_tables("s", s, list(L.iter_texts(s)))))

    def test_multiply_sign_is_not_rating(self):
        s = {"type": "matrix", "quadrants": [{"heading": "シンプル × 大量"}, {"heading": "複雑 × 少量"}]}
        self.assertEqual(L.check_tables("s", s, list(L.iter_texts(s))), [])

    def test_big_numbers(self):
        self.assertTrue(L.check_numbers("s", "p", "年間12000件の問い合わせ"))
        self.assertEqual(L.check_numbers("s", "p", "2026年に12,000件、1024×768、ISO27001、v1234、port:8080"), [])


class AiLookTests(unittest.TestCase):
    """AI 生成資料の定番パターン（content-guide.md 8章）。"""

    def look(self, s):
        return L.check_ai_look("s", s, list(L.iter_texts(s)))

    def test_zero_padded_numbers(self):
        w = self.look({"type": "section", "number": "01", "title": "背景"})
        self.assertTrue(any("0埋め" in x for x in w))
        w = self.look({"type": "lifecycle", "states": [{"label": "受付", "step": "01"}, {"label": "完了", "step": "02"}]})
        self.assertEqual(sum("0埋め" in x for x in w), 1)   # スライドごとに1行にまとめる
        self.assertFalse(any("0埋め" in x for x in self.look({"type": "section", "number": "1", "title": "背景"})))
        self.assertFalse(any("0埋め" in x for x in self.look({"type": "bullets", "title": "2026年の方針"})))

    def test_emphasis_brackets_and_label(self):
        w = self.look({"title": "AIは人の「代替」ではなく「伴走者」", "lead": "【基本方針】社員の可能性を引き出す"})
        self.assertTrue(any("カギカッコ" in x and "代替" in x for x in w))
        self.assertTrue(any("【】" in x for x in w))
        self.assertFalse(any("カギカッコ" in x for x in self.look({"title": "問い合わせの一次回答を自動化する"})))

    def test_repeated_labels_across_items(self):
        s = {"type": "cards", "cards": [{"heading": "リスク：形骸化"}, {"heading": "リスク：期待値のズレ"},
                                         {"heading": "リスク：属人化"}]}
        self.assertTrue(any("同じラベル「リスク」" in x for x in self.look(s)))
        s = {"type": "cards", "cards": [{"heading": "ご判断いただきたい点"}] * 3}
        self.assertTrue(any("全項目が同じ" in x for x in self.look(s)))
        # 番号・年度つきの見出しは繰り返しとみなさない
        s = {"type": "row_matrix", "columns": [], "periods": [{"label": "FY27 上期"}, {"label": "FY27 下期"}],
             "steps": [{"label": "Phase 1｜試行"}, {"label": "Phase 2｜展開"}]}
        self.assertFalse(any("同じラベル" in x for x in self.look(s)))
        s = {"type": "summary", "items": [{"title": "背景｜標準化"}, {"title": "課題｜リスク"}]}
        self.assertFalse(any("同じラベル" in x for x in self.look(s)))

    def test_title_mixes_share_and_ask(self):
        w = self.look({"title": "論点4：生成AI活用の推進方針とご判断事項"})
        self.assertTrue(any("問いの形" in x for x in w))
        self.assertTrue(any("1スライド1メッセージ" in x for x in w))
        w = self.look({"title": "論点：対象業務を全社に広げるか"})
        self.assertFalse(any("問いの形" in x for x in w))
        self.assertFalse(any("1スライド1メッセージ" in x for x in self.look({"title": "現状と課題を整理する"})))

    def test_disclaimer_and_long_note(self):
        w = self.look({"source": "本資料の内容は将来の成果を保証するものではありません。"})
        self.assertTrue(any("免責" in x for x in w))
        w = self.look({"source": "あ" * 120})
        self.assertTrue(any("改行なし" in x for x in w))
        self.assertEqual(self.look({"source": "出典: 社内調査（2026年9月、回答120名）"}), [])

    def test_quotes_and_todo_marks_are_not_emphasis(self):
        # 「〜」と聞く（引用）・問いの引用・【要確認】の印は強調カギカッコ／【】ラベルとみなさない
        w = self.look({"message": "困ったら「どう頼めばいい？」と聞く", "lead": "【要確認】件数は月 120 件"})
        self.assertFalse(any("カギカッコ" in x or "【】" in x for x in w))


class RelationRhythmTests(unittest.TestCase):
    def test_relation_mismatch(self):
        self.assertTrue(L.check_relation("s", {"type": "cards", "relation": "sequence"}))
        self.assertEqual(L.check_relation("s", {"type": "steps", "relation": "sequence"}), [])
        self.assertTrue(any("未知" in x for x in L.check_relation("s", {"type": "steps", "relation": "foo"})))

    def test_ordered_card_headings(self):
        s = {"type": "cards", "cards": [{"heading": "STEP1 調査"}, {"heading": "STEP2 設計"}, {"heading": "STEP3 実装"}]}
        self.assertTrue(L.check_relation("s", s))
        s = {"type": "cards", "cards": [{"heading": "Python"}, {"heading": "Go"}]}
        self.assertEqual(L.check_relation("s", s), [])

    def test_rhythm(self):
        slides = [{"type": "bullets"}] * 3 + [{"type": "section"}] * 3 + [{"type": "table"}]
        w = L.check_rhythm(slides)
        self.assertEqual(len(w), 1)
        self.assertIn("bullets", w[0])


class DateTests(unittest.TestCase):
    def test_as_of_resolution(self):
        self.assertEqual(L.resolve_as_of({"as_of": "2026-10", "date": "2025-01-01"})[0], (2026, 10, 1))
        self.assertEqual(L.resolve_as_of({"date": "2026-09-11"})[0], (2026, 9, 11))
        self.assertEqual(L.resolve_as_of({}, datetime.date(2026, 3, 4))[0], (2026, 3, 4))

    def test_future_achievement(self):
        slides = [{"type": "bullets", "bullets": ["2027年3月に導入した10社で工数を削減した", "2027年3月に本番稼働を予定"]}]
        w = L.check_dates(slides, {"as_of": "2026-10"})
        self.assertEqual(len(w), 1)
        self.assertIn("実績", w[0])

    def test_schedule_start_and_today(self):
        past = {"type": "schedule", "timeline": {"start": "2026-06", "end": "2027-03"}}
        self.assertTrue(L.check_dates([past], {"as_of": "2026-10"}))
        self.assertEqual(L.check_dates([dict(past, today="2026-10-20")], {"as_of": "2026-10"}), [])
        self.assertTrue(L.check_dates([dict(past, today="2027-02-01")], {"as_of": "2026-10"}))

    def test_bad_as_of(self):
        self.assertTrue(any("読めない" in x for x in L.check_dates([], {"as_of": "来月"})))


class CliTests(unittest.TestCase):
    def test_cli_warnings_do_not_fail(self):
        deck = {"meta": {"title": "t", "as_of": "2026-10"}, "slides": [
            {"type": "bullets", "title": "効果", "lead": "左に現状を示す", "bullets": ["年間12000件"]}]}
        with tempfile.TemporaryDirectory() as d:
            Path(d, "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, str(TOOLS / "lint_deck_text.py"), d],
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("構成の説明", r.stdout)
        self.assertIn("桁区切り", r.stdout)


class TodoMarkerTests(unittest.TestCase):
    def test_find_todos_with_and_without_note(self):
        slides = [{"type": "bullets", "title": "a", "bullets": ["売上は伸びる【要確認】", "根拠あり"], "notes": "【要確認: 出典URL】を探す"},
                  {"type": "table", "title": "b", "rows": [["x", "【要確認：単位】"]]}]
        todos = L.find_todos(slides)
        self.assertEqual([(t["slide"], t["path"], t["note"]) for t in todos],
                         [("slide-01", "bullets[0]", ""), ("slide-01", "notes", "出典URL"), ("slide-02", "rows[0][1]", "単位")])

    def test_lint_counts_todos_and_fail_flag(self):
        deck = {"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "結論", "bullets": ["数字【要確認: 出典】"]}]}
        res = L.lint(deck)
        self.assertEqual(res["stats"]["todo"], 1)
        self.assertTrue(any("要確認マーカー【出典】" in w and "slide-01" in w for w in res["warnings"]))
        self.assertIn("要確認マーカー1箇所", res["summary"])
        self.assertEqual(res["errors"], [])   # 既定は警告のみ

    def test_cli_fail_on_todo(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "deck.json").write_text(json.dumps(
                {"meta": {"title": "t"}, "slides": [{"type": "bullets", "title": "結論", "bullets": ["数字【要確認】"]}]}, ensure_ascii=False), encoding="utf-8")
            base = [sys.executable, str(TOOLS / "lint_deck_text.py"), d]
            self.assertEqual(subprocess.run(base, capture_output=True, text=True, encoding="utf-8").returncode, 0)
            r = subprocess.run(base + ["--fail-on-todo"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)
            self.assertIn("NG: 【要確認】マーカーが1箇所", r.stdout)


class PageReferenceTests(unittest.TestCase):
    def lint_text(self, text, n_slides=3):
        deck = {"meta": {}, "slides": [{"type": "bullets", "title": f"t{i}", "bullets": [text if i == 0 else "x"]} for i in range(n_slides)]}
        return L.lint(deck)

    def test_pdf_page_counts_are_not_references(self):
        for text in ("全200ページのPDF", "3ページ構成", "A4で5ページ分", "12ページ"):
            self.assertEqual(self.lint_text(text, 2)["errors"], [], msg=text)

    def test_real_references_beyond_total_fail(self):
        self.assertTrue(self.lint_text("詳細は50ページを参照", 3)["errors"])
        self.assertTrue(self.lint_text("9枚目で説明", 3)["errors"])
        self.assertTrue(self.lint_text("10ページ目に戻る", 3)["errors"])

    def test_reference_within_total_is_warning(self):
        res = self.lint_text("詳細は2ページを参照", 3)
        self.assertEqual(res["errors"], [])
        self.assertTrue(any("ページ番号直書き" in w for w in res["warnings"]))


    def test_estimate_review_words_are_not_references(self):
        # 「見積もり」「見込み」「見直し」の「見」、「枚目標」「枚目安」の「枚目」を参照と誤認しない
        for text in ("全体で200ページの見積もりが必要", "現行は100ページの見直しを行う", "50ページの見込み",
                     "3枚目標を設定", "5枚目安で作る"):
            res = self.lint_text(text, 1)
            self.assertEqual(res["errors"], [], msg=text)
            self.assertFalse(any("ページ番号直書き" in w for w in res["warnings"]), msg=text)

    def test_see_verb_forms_are_references(self):
        for text in ("200ページを見る", "200ページを見て確認", "200ページを見よ"):
            self.assertTrue(self.lint_text(text, 3)["errors"], msg=text)

    def test_p_dot_prefix_form(self):
        self.assertTrue(self.lint_text("p.9 を参照", 3)["errors"])
        self.assertTrue(self.lint_text("P.12", 3)["errors"])
        res = self.lint_text("p.2 を参照", 3)
        self.assertEqual(res["errors"], [])
        self.assertTrue(any("ページ番号直書き" in w for w in res["warnings"]))


class TodoMarkerColonTests(unittest.TestCase):
    def half_colon_warns(self, text):
        deck = {"meta": {}, "slides": [{"type": "bullets", "title": "B", "bullets": [text]}]}
        return [w for w in L.lint(deck)["warnings"] if "半角コロン:" in w]

    def test_todo_marker_colon_is_not_warned(self):
        self.assertEqual(self.half_colon_warns("売上は 120 億円【要確認: 根拠の出典】"), [])
        self.assertEqual(self.half_colon_warns("い【要確認:根拠】"), [])

    def test_real_halfwidth_colon_next_to_marker_still_warned(self):
        self.assertTrue(self.half_colon_warns("売上: 日本【要確認: 根拠】"))


class SlideNumberLabelTests(unittest.TestCase):
    def test_relabel_uses_png_numbers_only_where_shifted(self):
        text = "slide-01 a / slide-02 b / slide-02〜slide-03 c"
        out = L.relabel_slides(text, [1, 3, 4])
        self.assertIn("slide-01 a", out)
        self.assertIn("slide-03（deck.json 2枚目） b", out)
        self.assertIn("slide-03（deck.json 2枚目）〜slide-04（deck.json 3枚目）", out)

    def test_lint_applies_png_numbers_to_warnings_and_todos(self):
        deck = {"meta": {}, "slides": [
            {"type": "bullets", "title": "A", "bullets": ["x"]},
            {"type": "bullets", "title": "B", "bullets": ["【要確認: 出典】"]}]}
        plain = L.lint(deck)
        self.assertEqual(plain["todos"][0]["slide"], "slide-02")
        res = L.lint(deck, png_numbers=[1, 3])
        self.assertEqual(res["todos"][0]["slide"], "slide-03（deck.json 2枚目）")
        self.assertTrue(any("slide-03（deck.json 2枚目）" in w for w in res["warnings"]))


class ErrorMessagesHaveFixesTests(unittest.TestCase):
    def test_every_error_has_arrow_fix(self):
        deck = {"meta": {}, "slides": [
            {"type": "closing", "title": "あ" * 30},
            {"type": "bullets", "title": "t", "bullets": ["**強調**", "これを実現します", "9枚目を見る"]}]}
        errors = L.lint(deck)["errors"]
        self.assertGreaterEqual(len(errors), 4)
        for e in errors:
            self.assertIn("→", e)


class SourceAndNonDisplayTests(unittest.TestCase):
    def test_source_halfwidth_colon_not_warned(self):
        deck = {"meta": {}, "slides": [{"type": "bullets", "title": "t", "source": "試算の前提: 削減時間は6,300時間", "bullets": ["本文: これは警告"]}]}
        warns = [w for w in L.lint(deck)["warnings"] if "半角コロン" in w]
        self.assertTrue(any("bullets[0]" in w for w in warns))
        self.assertFalse(any(" source " in w for w in warns))

    def test_icon_variant_shape_are_not_body_text(self):
        s = {"type": "cards", "title": "t", "cards": [{"heading": "h", "icon": "shield-check 100000", "variant": "最適化 onpf", "shape": "を実現"}]}
        paths = [p for p, _ in L.iter_texts(s)]
        self.assertFalse(any(p.endswith(("icon", "variant", "shape")) for p in paths), paths)
        deck = {"meta": {}, "slides": [s]}
        res = L.lint(deck)
        self.assertEqual(res["errors"], [])


class DensityTests(unittest.TestCase):
    def deck(self, density, punch="あ" * 60):
        meta = {"density": density} if density else {}
        return {"meta": meta, "slides": [{"type": "bullets", "title": "t", "punch": punch,
                                          "bullets": ["い" * 35, "う", "え", "お", "か", "き"]}]}

    def test_punch_limit_follows_density(self):
        talk = L.lint(self.deck("talk"))
        std = L.lint(self.deck(None))
        read = L.lint(self.deck("read"))
        self.assertTrue(any("punch" in w and "density=talk" in w for w in talk["warnings"]))
        self.assertFalse(any("punch 60字" in w for w in std["warnings"]))
        self.assertFalse(any("punch 60字" in w for w in read["warnings"]))

    def test_bullet_chars_and_count_follow_density(self):
        talk = L.lint(self.deck("talk"))
        std = L.lint(self.deck("standard"))
        self.assertTrue(any("bullets の項目が30字超" in w for w in talk["warnings"]))
        self.assertTrue(any("bullets 6項目 > 5" in w for w in talk["warnings"]))
        self.assertFalse(any("bullets の項目が" in w or "項目 >" in w for w in std["warnings"]))

    def test_explicit_punch_max_wins(self):
        res = L.lint(self.deck("read"), punch_max=40)
        self.assertTrue(any("punch 60字 > 40" in w for w in res["warnings"]))

    def test_non_string_density_does_not_crash(self):
        for bad in (["talk"], {"a": 1}, 3):
            res = L.lint({"meta": {"density": bad}, "slides": []})
            self.assertEqual(res["density"], "standard")
            self.assertTrue(any("meta.density" in w for w in res["warnings"]))

    def test_unknown_density_warns_and_falls_back(self):
        res = L.lint(self.deck("dense"))
        self.assertEqual(res["density"], "standard")
        self.assertTrue(any("meta.density" in w and "未知" in w for w in res["warnings"]))

    def test_slide_volume(self):
        deck = {"meta": {"density": "talk"}, "slides": [{"type": "table", "title": "t", "rows": [["あ" * 20] * 15]}]}
        self.assertTrue(any("表示文字数" in w for w in L.lint(deck)["warnings"]))
        deck["meta"]["density"] = "read"
        self.assertFalse(any("表示文字数" in w for w in L.lint(deck)["warnings"]))


if __name__ == "__main__":
    unittest.main()

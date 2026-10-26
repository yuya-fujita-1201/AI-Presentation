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


if __name__ == "__main__":
    unittest.main()

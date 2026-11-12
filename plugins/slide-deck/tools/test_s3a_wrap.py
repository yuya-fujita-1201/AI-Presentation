#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3a 折り返し: 共通の切れ目の規則（ja_text.can_break）・大きな文字の最終行（tail_min）・quote / 背景つきの文節折り。

実行: python3 -m unittest plugins/slide-deck/tools/test_s3a_wrap.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import ja_text  # noqa: E402


def cuts(text):
    return [i for i in range(1, len(text)) if ja_text.can_break(text, i, 1)]


class CanBreakTest(unittest.TestCase):
    def test_kana_continuation_not_cut(self):
        t = "出にくかった"
        self.assertNotIn(2, cuts(t))                               # 「出に|くかった」

    def test_digit_space_not_cut_at_level1(self):
        t = "週 2 回の会議"
        self.assertEqual([i for i in cuts(t) if t[i - 1:i + 1].strip() == "" or t[i - 1] == " " or t[i] == " "], [])
        self.assertTrue(any(ja_text.can_break(t, i, 2) for i in (1, 2)))     # level 2 でゆるむ

    def test_compound_particle(self):
        t = "型として使う"
        self.assertFalse(ja_text.can_break(t, 2, 1))                 # 「と|して」

    def test_particle_after_alnum_not_split_from_word(self):
        t = "微修正は JSON の数値を変える"
        for i in range(1, len(t)):
            if t[i] == "の" and t[i - 1] == " ":
                self.assertFalse(ja_text.can_break(t, i, 1))
        i = t.index("JSON") + 4
        self.assertFalse(ja_text.can_break(t, i, 1))               # 「JSON| の」

    def test_level3_equals_good_break(self):
        t = "資料のために使っていた週 3 時間が、顧客との対話に変わりました。"
        for i in range(1, len(t)):
            self.assertEqual(ja_text.can_break(t, i, 3), ja_text.good_break(t, i))

    def test_levels_only_tighten(self):
        t = "出にくかった週 2 回の新棟でまとめて渡す"
        for i in range(1, len(t)):
            a, c, d = (ja_text.can_break(t, i, lv) for lv in (1, 2, 3))
            self.assertTrue((not a) or c)
            self.assertTrue((not c) or d)


class TailMinTest(unittest.TestCase):
    def test_small_text_keeps_base(self):
        self.assertEqual(ja_text.tail_min(20), 3)
        self.assertEqual(ja_text.tail_min(35), 3)

    def test_big_text_grows(self):
        self.assertEqual(ja_text.tail_min(36), 4)
        self.assertEqual(ja_text.tail_min(52), 6)
        self.assertGreater(ja_text.tail_min(60), ja_text.tail_min(36))


class BigTextTest(unittest.TestCase):
    lay = b.load_layout("default")

    def run_slides(self, slides):
        deck = {"meta": {"id": "d"}, "slides": slides}
        return b.apply_line_balance(deck, self.lay)["slides"]

    def test_title_last_line_not_a_stub(self):
        # 60px・幅 1136 で、自然な折り返しの最終行が「つくる」3 字になる文
        t = "口述から資料へ。人が直さない仕組みをつくる"
        hf = ja_text.heading_fonts()
        self.assertEqual(ja_text.wrap_lines(t, 60, 1136, hf, True)[-1], "つくる")
        out = self.run_slides([{"type": "title", "title": t, "background": {"fill": "primary"}}, {"type": "title", "title": t}])
        for s in out:
            lines = s["title"].split("\n")
            self.assertGreaterEqual(len(lines[-1]), 6, s["title"])
            self.assertEqual(s["title"].replace("\n", ""), t)

    def test_quote_without_variant_gets_phrase_wrap(self):
        t = "資料のために使っていた週 3 時間が、顧客との対話に変わりました。"
        out = self.run_slides([{"type": "quote", "text": t, "variant": "mark", "background": {"fill": "primary"}},
                               {"type": "quote", "text": t, "background": {"fill": "primary"}}])
        for s in out:
            lines = s["text"].split("\n")
            self.assertNotIn("変\nわ", s["text"])                         # 「変|わりました」と語の途中で切らない
            self.assertGreaterEqual(len(lines[-1]), 5, s["text"])
            self.assertNotIn("週\n", s["text"])
            self.assertNotIn("週 3\n", s["text"])

    def test_ascii_word_particle_stays_together(self):
        t = "内容とデザインを分離する。だから微修正は JSON の数値を変えるだけでいい。"
        out = self.run_slides([{"type": "quote", "text": t}])
        self.assertNotIn("JSON\nの", out[0]["text"])

    def test_small_titles_unchanged_rule(self):
        # 36px 未満のタイトル（箇条書き見出しの縮小後など）は従来の min_tail=3
        t = "短い見出しです"
        out = self.run_slides([{"type": "bullets", "title": t, "bullets": ["a"]}])
        self.assertEqual(out[0]["title"], t)

    def test_non_quote_text_key_not_touched(self):
        s = {"type": "bullets", "title": "t", "bullets": ["a"], "text": "資料のために使っていた週 3 時間が、顧客との対話に変わりました。"}
        out = self.run_slides([s])
        self.assertEqual(out[0]["text"], s["text"])


class BalanceFallbackTest(unittest.TestCase):
    def test_balance_never_worse_than_before_when_only_loose_break_exists(self):
        # 厳しい規則では切れ目が無い文（仮名だけが続く）でも、level 3（従来）で直せる文は直る
        t = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほ" * 2
        out = ja_text.balance(t, 24, 520)
        self.assertEqual(out.replace("\n", ""), t)


if __name__ == "__main__":
    unittest.main()

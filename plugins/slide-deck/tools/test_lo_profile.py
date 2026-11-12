#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lo_profile（LibreOffice のフォント置き換えの固定）のテスト。

実行: python3 -m unittest plugins/slide-deck/tools/test_lo_profile.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import lo_profile as lp  # noqa: E402

PY = sys.executable


class FakeJa:
    """ja_text の代わり: Meiryo は無く、代替は Hiragino Sans。"""
    @staticmethod
    def _open_font(name, bold):
        return object() if name in ("Hiragino Sans", "Arial") else None

    @staticmethod
    def measure_source(font=None):
        return (font, "Hiragino Sans")


class PairsTest(unittest.TestCase):
    def test_missing_font_is_substituted_and_installed_is_kept(self):
        pairs = lp.substitution_pairs(["Meiryo", "Hiragino Sans"], FakeJa)
        self.assertEqual(pairs, [("Meiryo", "Hiragino Sans")])

    def test_no_substitute_means_no_pairs(self):
        class NoSub(FakeJa):
            @staticmethod
            def measure_source(font=None):
                return (font, None)
        self.assertEqual(lp.substitution_pairs(["Meiryo"], NoSub), [])

    def test_registry_xml_has_font_pair(self):
        x = lp.registry_xml([("Mei&ryo", "Hiragino Sans")])
        self.assertIn("Font/Substitution/FontPairs", x)
        self.assertIn("Mei&amp;ryo", x)
        self.assertIn("<value>Hiragino Sans</value>", x)
        self.assertNotIn("FontPairs", lp.registry_xml([]))

    def test_prepare_writes_profile_and_env(self):
        d = Path(tempfile.mkdtemp(prefix="lo_"))
        r = lp.prepare(d / "prof", faces=["NoSuchFontXYZ"])
        self.assertTrue((d / "prof" / "user" / "registrymodifications.xcu").exists())
        self.assertTrue(r["env"].startswith("-env:UserInstallation=file://"))
        shutil.rmtree(d, ignore_errors=True)

    def test_pptx_typefaces(self):
        from pptx import Presentation
        d = Path(tempfile.mkdtemp(prefix="lo_"))
        deck = {"meta": {"id": "d", "title": "t", "theme": "default"}, "slides": [{"type": "bullets", "title": "あ", "bullets": ["い"]}]}
        (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), "--pptx"], capture_output=True, text=True)
        faces = lp.pptx_typefaces(d / "build" / "d.pptx")
        self.assertIn("Meiryo", faces)
        self.assertFalse([f for f in faces if f.startswith("+")])
        shutil.rmtree(d, ignore_errors=True)


@unittest.skipUnless(shutil.which("soffice") and shutil.which("pdffonts"), "soffice / pdffonts が無い")
class StableFontsTest(unittest.TestCase):
    def test_three_conversions_embed_the_same_fonts(self):
        d = Path(tempfile.mkdtemp(prefix="lo_"))
        deck = {"meta": {"id": "d", "title": "t", "theme": "default"}, "slides": [{"type": "bullets", "title": "要確認 の確認", "bullets": ["日本語の本文（約物）"]}]}
        (d / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d), "--pptx"], capture_output=True, text=True)
        sets = []
        for i in range(3):
            out = d / f"o{i}"
            r = subprocess.run([PY, str(TOOLS / "export_pdf.py"), str(d), "--no-build", "--out", str(out)], capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr)
            fonts = subprocess.run(["pdffonts", str(out / "d.pdf")], capture_output=True, text=True).stdout.splitlines()[2:]
            sets.append(sorted({ln.split()[0].split("+")[-1] for ln in fonts if ln.strip()}))
        self.assertEqual(sets[0], sets[1])
        self.assertEqual(sets[1], sets[2])
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

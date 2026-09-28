from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_deck  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
BUILD_DECK = ROOT / "tools" / "build_deck.py"


def _write_deck(deck_dir: Path, rows, columns=("Title", "URL")):
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck = {
        "meta": {"id": deck_dir.name, "title": "Link deck", "layout": "default"},
        "slides": [{"type": "table", "title": "Sources",
                    "columns": list(columns), "rows": rows}],
    }
    (deck_dir / "deck.json").write_text(
        json.dumps(deck, ensure_ascii=False), encoding="utf-8"
    )
    return deck_dir


def _build(deck_dir: Path, *args):
    # build_deck.py は stdout/stderr を UTF-8 に固定するため、ロケール既定（Windows は
    # cp932）で復号すると日本語のエラーメッセージで UnicodeDecodeError になる。
    return subprocess.run(
        [sys.executable, str(BUILD_DECK), str(deck_dir), *args],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


class TableUrlLinkTest(unittest.TestCase):
    def test_complete_http_url_cells_are_clickable_in_html_and_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_dir = Path(tmp) / "link-deck"
            deck_dir.mkdir()
            url = "https://example.com/source?a=1&b=2"
            title_url = "https://example.com/linked-title"
            deck = {
                "meta": {
                    "id": "link-deck",
                    "title": "Link deck",
                    "theme": "accenture-purple",
                    "layout": "default",
                },
                "slides": [
                    {
                        "type": "table",
                        "title": "Sources",
                        "columns": ["Title", "URL"],
                        "rows": [
                            ["Source", url],
                            [{"text": "Linked title", "url": title_url}, "URLなし"],
                        ],
                    }
                ],
            }
            (deck_dir / "deck.json").write_text(
                json.dumps(deck, ensure_ascii=False), encoding="utf-8"
            )

            subprocess.run(
                [sys.executable, str(BUILD_DECK), str(deck_dir)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            html = (deck_dir / "build" / "link-deck.html").read_text(encoding="utf-8")
            self.assertIn(
                'href="https://example.com/source?a=1&amp;b=2"',
                html,
            )
            self.assertIn('target="_blank" rel="noopener noreferrer"', html)
            self.assertNotIn('href="URLなし"', html)
            self.assertIn(
                '<a href="https://example.com/linked-title"',
                html,
            )
            self.assertIn('>Linked title</a>', html)

            prs = Presentation(deck_dir / "build" / "link-deck.pptx")
            links = []
            for shape in prs.slides[0].shapes:
                if not getattr(shape, "has_table", False):
                    continue
                for row in shape.table.rows:
                    for cell in row.cells:
                        for paragraph in cell.text_frame.paragraphs:
                            links.extend(
                                run.hyperlink.address
                                for run in paragraph.runs
                                if run.hyperlink.address
                            )
            self.assertEqual([url, title_url], links)


class LinkSchemeAllowlistTest(unittest.TestCase):
    """href に出せるスキームは http / https / mailto だけ（XSS 対策）。"""

    UNSAFE = (
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "java\nscript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "vbscript:msgbox(1)",
        "file:///C:/Windows/System32",
        "//evil.example.com",
    )

    def test_unsafe_schemes_are_never_returned_as_urls(self):
        for raw in self.UNSAFE:
            with self.subTest(url=raw):
                self.assertEqual(
                    ("表示", None), build_deck.table_cell_parts({"text": "表示", "url": raw})
                )
                self.assertEqual((raw, None), build_deck.table_cell_parts(raw))

    def test_allowed_schemes_are_returned_as_urls(self):
        for raw, autolink in (("https://example.com/a", True),
                              ("http://example.com", True),
                              ("mailto:sales@example.com", False)):
            with self.subTest(url=raw):
                self.assertEqual(
                    ("表示", raw), build_deck.table_cell_parts({"text": "表示", "url": raw})
                )
                # セル全体が URL のときの自動リンク化は http(s) のみ（mailto は対象外）
                self.assertEqual(
                    (raw, raw if autolink else None), build_deck.table_cell_parts(raw)
                )

    def test_explicit_unsafe_url_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_dir = _write_deck(
                Path(tmp) / "bad-url-deck",
                [[{"text": "資料", "url": "javascript:alert(1)"}, "説明"]],
            )
            proc = _build(deck_dir, "--html")
            self.assertNotEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("使用できないリンク先", proc.stderr)
            self.assertFalse((deck_dir / "build").exists())

    def test_unsafe_scheme_in_plain_cell_renders_as_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_dir = _write_deck(
                Path(tmp) / "plain-cell-deck",
                [["javascript:alert(1)", "説明"]],
            )
            proc = _build(deck_dir, "--html")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            html = (deck_dir / "build" / "plain-cell-deck.html").read_text(encoding="utf-8")
            self.assertNotIn("href=\"javascript:", html)
            self.assertNotIn("<a ", html)
            self.assertIn("javascript:alert(1)", html)

    def test_mailto_url_is_linked_in_html_and_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck_dir = _write_deck(
                Path(tmp) / "mailto-deck",
                [[{"text": "問い合わせ", "url": "mailto:sales@example.com"}, "説明"]],
            )
            proc = _build(deck_dir)
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            html = (deck_dir / "build" / "mailto-deck.html").read_text(encoding="utf-8")
            self.assertIn('<a href="mailto:sales@example.com"', html)
            prs = Presentation(deck_dir / "build" / "mailto-deck.pptx")
            links = [
                run.hyperlink.address
                for shape in prs.slides[0].shapes if getattr(shape, "has_table", False)
                for row in shape.table.rows for cell in row.cells
                for paragraph in cell.text_frame.paragraphs for run in paragraph.runs
                if run.hyperlink.address
            ]
            self.assertEqual(["mailto:sales@example.com"], links)


if __name__ == "__main__":
    unittest.main()

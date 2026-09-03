#!/usr/bin/env python3
"""SVG図版のフォント機械ゲート: <deck_dir>/assets/*.svg を Chromium で開き、
全 <text>/<tspan> の computed font-family にゴシック系（Hiragino Sans / Noto Sans / sans-serif 等）が
含まれないものを「明朝体フォールバック」として報告する。exit 1 = 検出あり。

使い方: python tools/check_svg_fonts.py <deck_dir> [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
try:
    import build_deck  # type: ignore
except Exception:
    build_deck = None


def _fallback_setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _fallback_fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _fallback_warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def _fallback_note(msg):
    print(f"note: {msg}", file=sys.stderr)


setup_console = getattr(build_deck, "setup_console", None) or _fallback_setup_console
fail = getattr(build_deck, "fail", None) or _fallback_fail
warn = getattr(build_deck, "warn", None) or _fallback_warn
note = getattr(build_deck, "note", None) or _fallback_note

GOTHIC = ("hiragino sans", "hiragino kaku gothic", "noto sans", "sans-serif", "yu gothic", "meiryo",
          "helvetica", "arial", "inter", "roboto", "system-ui", "-apple-system", "bizudpgothic", "source han sans")

JS = r"""
() => {
  const out = [];
  const els = Array.from(document.querySelectorAll('text, tspan'));
  for (const el of els) {
    const t = (el.textContent || '').trim();
    if (!t) continue;
    if (el.tagName.toLowerCase() === 'tspan' && el.parentElement && el.parentElement.tagName.toLowerCase() === 'text') {
      // tspan は親 text と同じ font-family なら親側で見る
      if (getComputedStyle(el).fontFamily === getComputedStyle(el.parentElement).fontFamily) continue;
    }
    out.push({text: t.slice(0, 30), family: getComputedStyle(el).fontFamily});
  }
  return out;
}
"""


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="SVG図版のフォント機械ゲート")
    ap.add_argument("deck_dir")
    ap.add_argument("--json")
    args = ap.parse_args()
    svgs = sorted(Path(args.deck_dir, "assets").glob("*.svg"))
    if not svgs:
        print("check_svg_fonts: SVGなし")
        sys.exit(0)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("Playwright が未インストールのため check_svg_fonts.py を実行できません。初回セットアップ: /slide-deck:setup --playwright")
    bad = {}
    n_text = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for svg in svgs:
            page.goto(svg.resolve().as_uri())
            page.wait_for_timeout(50)
            rows = page.evaluate(JS)
            n_text += len(rows)
            for r in rows:
                fam = r["family"].lower()
                if not any(g in fam for g in GOTHIC):
                    bad.setdefault(svg.name, []).append(r)
        browser.close()
    if args.json:
        Path(args.json).write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, rows in bad.items():
        for r in rows:
            print(f"{name}: 「{r['text']}」 font-family={r['family']}")
    n_bad = sum(len(v) for v in bad.values())
    print(f"check_svg_fonts: {len(svgs)}ファイル text要素{n_text}件 明朝体フォールバック疑い={n_bad}")
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()

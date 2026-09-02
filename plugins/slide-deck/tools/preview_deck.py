#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビルド済み HTML スライドを PNG に書き出すプレビューツール。

使い方:
    python3 tools/preview_deck.py decks/<デッキ名>            # 全スライド
    python3 tools/preview_deck.py decks/<デッキ名> 5          # 5枚目のみ
    python3 tools/preview_deck.py decks/<デッキ名> 3 5 10     # 指定枚のみ

微修正ループでの用途:
    deck.json の style を編集 → build_deck.py → preview_deck.py <番号> で当該スライドだけ目視確認。
出力: decks/<デッキ名>/build/preview/slide-NN.png
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: preview_deck.py <deck_dir> [slide numbers...]")
    deck_dir = Path(sys.argv[1]).resolve()
    deck = json.loads((deck_dir / "deck.json").read_text(encoding="utf-8"))
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    html_path = deck_dir / "build" / f"{deck_id}.html"
    if not html_path.exists():
        sys.exit(f"error: {html_path} がありません。先に build_deck.py を実行してください")

    total = len(deck.get("slides", []))
    nums = [int(a) for a in sys.argv[2:]] or list(range(1, total + 1))
    bad = [n for n in nums if not 1 <= n <= total]
    if bad:
        sys.exit(f"error: スライド番号が範囲外です（1〜{total}）: {bad}")

    out_dir = deck_dir / "build" / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "error: Playwright が未インストールのためプレビューPNGを生成できません。\n"
            "  初回セットアップを実行してください: /slide-deck:setup --playwright\n"
            "  （または `pip install playwright && playwright install chromium`）"
        )

    url = html_path.as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for n in nums:
            page.goto(f"{url}#{n}")
            page.reload()
            page.wait_for_timeout(250)
            page.evaluate("""() => {
              const hud = document.getElementById('hud');
              const notes = document.getElementById('notes');
              if (hud) hud.style.display = 'none';
              if (notes) notes.style.display = 'none';
            }""")
            out = out_dir / f"slide-{n:02d}.png"
            page.screenshot(path=str(out))
            print(f"PNG: {out}")
        browser.close()


if __name__ == "__main__":
    main()

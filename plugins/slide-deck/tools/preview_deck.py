#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビルド済み HTML スライドを PNG に書き出すプレビューツール。

使い方:
    python tools/preview_deck.py <deck_dir>            # 全スライド
    python tools/preview_deck.py <deck_dir> 5          # 5枚目のみ
    python tools/preview_deck.py <deck_dir> 3 5 10     # 指定枚のみ

微修正ループでの用途:
    deck.json の style を編集 → build_deck.py → preview_deck.py <番号> で当該スライドだけ目視確認。
スライド番号は build_deck.expand_slides() 適用後（swimlaneの凡例自動挿入・agendaの
自動改ページ込み）の実際の出力枚数を基準にする（deck.json記載の枚数とは異なることがある）。
出力: <deck_dir>/build/preview/slide-NN.png
番号を省略して全スライドを出したときは、スライド枚数を超えた古い slide-NN.png（デッキを減らした後の残り）を消す。
描画はフォント・画像の読み込み完了を待ってから撮る（固定の待ち時間ではない）。
"""
from __future__ import annotations

import argparse
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


# ページ（フォント・画像）の読み込み完了と、描画の反映を待つ（check_layout.py と同じ内容）
WAIT_READY_JS = """async () => {
  try { await document.fonts.ready; } catch (e) {}
  await Promise.all(Array.from(document.images).map(i => (i.decode ? i.decode().catch(() => null) : null)));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""


def wait_ready(page) -> None:
    page.evaluate(WAIT_READY_JS)


def remove_stale_pngs(out_dir: Path, total: int) -> list:
    """slide-NN.png のうち NN が total を超えるもの（以前の長いデッキの残り）を消して、消した名前を返す。"""
    removed = []
    for p in sorted(out_dir.glob("slide-*.png")):
        try:
            n = int(p.stem.split("-")[1])
        except (IndexError, ValueError):
            continue
        if n > total:
            p.unlink()
            removed.append(p.name)
    return removed


def _slide_total(deck_dir: Path) -> int:
    """expand_slides() 適用後の実際の総枚数を返す（build_deck が使えなければ deck.json 枚数で妥協）。"""
    if build_deck is not None:
        try:
            deck, theme, layout = build_deck.load_deck(deck_dir)
            expanded = build_deck.expand_slides(deck, layout)
            return len(expanded["slides"])
        except SystemExit:
            raise
        except Exception:
            pass
    import json
    deck = json.loads((deck_dir / "deck.json").read_text(encoding="utf-8-sig"))
    return len(deck.get("slides", []))


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="ビルド済みHTMLスライドをPNGに書き出す")
    ap.add_argument("deck_dir")
    ap.add_argument("slides", nargs="*", type=int, help="対象スライド番号（省略時は全部）")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    import json
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    html_path = deck_dir / "build" / f"{deck_id}.html"
    if not html_path.exists():
        fail(f"{html_path} がありません。先に build_deck.py を実行してください")

    total = _slide_total(deck_dir)
    nums = args.slides or list(range(1, total + 1))
    bad = [n for n in nums if not 1 <= n <= total]
    if bad:
        fail(f"スライド番号が範囲外です（1〜{total}。凡例ページ等の自動挿入込みの枚数）: {bad}")

    out_dir = deck_dir / "build" / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail(
            "Playwright が未インストールのためプレビューPNGを生成できません。\n"
            "  初回セットアップを実行してください: /slide-deck:setup --playwright\n"
            "  （または `pip install playwright && playwright install chromium`）\n"
            "  導入できない環境では export_pdf.py でPDF化してから閲覧する方法もあります。"
        )

    url = html_path.as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{url}#{nums[0]}")
        wait_ready(page)
        # 下部ツールバー（#toolbar）とノート欄がスライド下端に重なるため隠す
        page.evaluate("""() => {
          for (const id of ['toolbar', 'notes', 'hud']) {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
          }
          window.dispatchEvent(new Event('resize'));
        }""")
        wait_ready(page)
        for n in nums:
            # 1枚ごとにページを読み直すと大きいデッキで遅いので、ビューアの show() で切り替える
            page.evaluate("(n) => show(n - 1)", n)
            wait_ready(page)
            out = out_dir / f"slide-{n:02d}.png"
            page.screenshot(path=str(out))
            print(f"PNG: {out}")
        browser.close()
    if not args.slides:
        removed = remove_stale_pngs(out_dir, total)
        if removed:
            note(f"スライド枚数（{total}枚）を超えた古いプレビュー画像を消しました: {', '.join(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""preview PNG をコンタクトシート（既定2列×3行＝6枚/シート）にまとめる。
採点エージェントが全スライドを少ない画像数で実見するための補助。文字の精読は deck.json 側で行う前提。

使い方: python tools/contact_sheet.py <deck_dir> [--out build/contact] [--cols 2 --rows 3]
preview PNG は既定で毎回 preview_deck.py を呼んで最新化する（要 Playwright）。
既存PNGをそのまま使いたい場合は --no-build を付ける。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent

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

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


# ラベル文字が読める和文フォント候補（見つかったものを使う。無ければPillow既定にフォールバック）。
LABEL_FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",              # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",         # macOS(保険)
    r"C:\Windows\Fonts\meiryo.ttc",                                  # Windows
    r"C:\Windows\Fonts\YuGothM.ttc",                                 # Windows
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",       # Linux (Noto)
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",       # Linux (Noto, 別配置)
]


def _load_label_font(size):
    for path in LABEL_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _slide_total(deck_dir: Path, deck: dict) -> int:
    """expand_slides() 適用後の実際の総枚数（build_deck が使えなければ deck.json 枚数で妥協）。"""
    if build_deck is not None:
        try:
            _, _, layout = build_deck.load_deck(deck_dir)
            expanded = build_deck.expand_slides(deck, layout)
            return len(expanded["slides"])
        except SystemExit:
            raise
        except Exception:
            pass
    return len(deck.get("slides", []))


def main():
    setup_console()
    if Image is None:
        fail("pillow が必要です。/slide-deck:setup --pillow（または pip install pillow）")
    ap = argparse.ArgumentParser(description="preview PNG をコンタクトシートにまとめる")
    ap.add_argument("deck_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--no-build", action="store_true", help="preview PNG が既にあれば再生成しない（既定は毎回 preview_deck.py で最新化）")
    args = ap.parse_args()
    deck_dir = Path(args.deck_dir).resolve()
    if args.cols <= 0 or args.rows <= 0:
        fail("--cols / --rows は1以上を指定してください")
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    prev = deck_dir / "build" / "preview"
    pngs = sorted(prev.glob("slide-*.png"))
    if args.no_build:
        if not pngs:
            fail(f"{prev} にpreview PNGがありません。--no-build のため生成しません。先に preview_deck.py を実行してください")
    else:
        note(f"preview_deck.py を実行して {prev} を最新化します")
        proc = subprocess.run([sys.executable, str(ROOT / "tools" / "preview_deck.py"), str(deck_dir)],
                               cwd=ROOT, stdout=subprocess.DEVNULL)
        if proc.returncode != 0:
            fail("preview_deck.py の実行に失敗しました（Playwright が未導入の可能性があります）")
        pngs = sorted(prev.glob("slide-*.png"))
    if not pngs:
        fail(f"{prev} にPNGが生成されませんでした")
    total = _slide_total(deck_dir, deck)
    if total and len(pngs) != total:
        fail(
            f"preview PNGの枚数（{len(pngs)}）が想定枚数（{total}。凡例ページ等の自動挿入込み）と"
            f"一致しません。{prev} を削除するか --no-build を外して再実行してください"
        )
    out_dir = Path(args.out) if args.out else deck_dir / "build" / "contact"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet-*.png"):
        old.unlink()
    w, h = int(1280 * args.scale), int(720 * args.scale)
    per = args.cols * args.rows
    label_h = 22
    font = _load_label_font(16)
    sheets = []
    for si in range(0, len(pngs), per):
        chunk = pngs[si:si + per]
        sheet = Image.new("RGB", (args.cols * w, args.rows * (h + label_h)), "#202024")
        draw = ImageDraw.Draw(sheet)
        for k, p in enumerate(chunk):
            im = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
            x = (k % args.cols) * w
            y = (k // args.cols) * (h + label_h)
            draw.rectangle([x, y, x + w, y + label_h], fill="#202024")
            draw.text((x + 6, y + 3), p.stem, fill="#f0f0f0", font=font)
            sheet.paste(im, (x, y + label_h))
        first, last = chunk[0].stem.split("-")[1], chunk[-1].stem.split("-")[1]
        out = out_dir / f"sheet-{first}-{last}.png"
        sheet.save(out, optimize=True)
        sheets.append(out)
    for s in sheets:
        print(s)
    print(f"contact_sheet: {len(pngs)}枚 -> {len(sheets)}シート ({out_dir})")


if __name__ == "__main__":
    main()

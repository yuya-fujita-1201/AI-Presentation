#!/usr/bin/env python3
"""preview PNG をコンタクトシート（2列×3行＝6枚/シート、各 640x360）にまとめる。
採点エージェントが全スライドを少ない画像数で実見するための補助。文字の精読は deck.json 側で行う前提。

使い方: python3 tools/contact_sheet.py decks/<deck> [--out build/contact] [--cols 2 --rows 3]
preview PNG が無ければ preview_deck.py を呼んで生成する。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--scale", type=float, default=0.5)
    args = ap.parse_args()
    deck_dir = Path(args.deck_dir)
    prev = deck_dir / "build" / "preview"
    pngs = sorted(prev.glob("slide-*.png"))
    if not pngs:
        subprocess.run([sys.executable, str(ROOT / "tools" / "preview_deck.py"), str(deck_dir)], check=True,
                       cwd=ROOT, stdout=subprocess.DEVNULL)
        pngs = sorted(prev.glob("slide-*.png"))
    out_dir = Path(args.out) if args.out else deck_dir / "build" / "contact"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet-*.png"):
        old.unlink()
    w, h = int(1280 * args.scale), int(720 * args.scale)
    per = args.cols * args.rows
    label_h = 22
    try:
        font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 16)
    except Exception:
        font = ImageFont.load_default()
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
    print(f"contact_sheet: {len(pngs)}枚 → {len(sheets)}シート ({out_dir})")


if __name__ == "__main__":
    main()

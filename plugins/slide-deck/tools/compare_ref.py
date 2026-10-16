#!/usr/bin/env python3
"""プレビューPNG（preview_deck.py の出力）と参照PNG（元 PPTX を書き出したもの）を並べて比較する。

使い方:
    python tools/compare_ref.py <deck_dir> <ref_dir> [スライド番号 ...]

- 参照PNGは <ref_dir>/slide_001.png 形式（tools/export_pptx_png.ps1 の出力）か slide-01.png 形式
- 出力: <deck_dir>/build/compare/cmp-NN.png（上=参照、下=HTML）と scores.txt（差分の大きい順）
- canvas 型（pptx_import.py で取り込んだデッキ）の見た目崩れを探すための補助ツール
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_dir")
    ap.add_argument("ref_dir")
    ap.add_argument("slides", nargs="*", type=int)
    args = ap.parse_args()
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageOps
    except ImportError:
        print("error: Pillow が必要です（/slide-deck:setup --pillow）", file=sys.stderr)
        return 1
    deck_dir, ref_dir = Path(args.deck_dir), Path(args.ref_dir)
    prev = deck_dir / "build" / "preview"
    out = deck_dir / "build" / "compare"
    out.mkdir(parents=True, exist_ok=True)
    scores = []
    for png in sorted(prev.glob("slide-*.png")):
        n = int(png.stem.split("-")[1])
        if args.slides and n not in args.slides:
            continue
        ref = next((p for p in (ref_dir / f"slide_{n:03d}.png", ref_dir / f"slide-{n:02d}.png") if p.exists()), None)
        if ref is None:
            continue
        a = Image.open(ref).convert("RGB").resize((1280, 720))
        b = Image.open(png).convert("RGB").resize((1280, 720))
        side = Image.new("RGB", (1280, 1450), "white")
        side.paste(a, (0, 0))
        side.paste(b, (0, 730))
        side.save(out / f"cmp-{n:02d}.png")
        ga = ImageOps.grayscale(a).resize((320, 180)).filter(ImageFilter.GaussianBlur(1.2))
        gb = ImageOps.grayscale(b).resize((320, 180)).filter(ImageFilter.GaussianBlur(1.2))
        d = ImageChops.difference(ga, gb)
        hist = d.histogram()
        scores.append((sum(i * c for i, c in enumerate(hist)) / (320 * 180), n))
    scores.sort(reverse=True)
    (out / "scores.txt").write_text("\n".join(f"{n:3d} {s:6.2f}" for s, n in scores), encoding="utf-8")
    print("差分の大きい順:", " ".join(f"{n}:{s:.1f}" for s, n in scores[:20]))
    if scores:
        print(f"平均 {sum(s for s, _ in scores) / len(scores):.2f}（{len(scores)}枚） 出力: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

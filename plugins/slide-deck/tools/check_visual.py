#!/usr/bin/env python3
"""プレビュー画像（preview_deck.py の PNG）から見た目の偏りを検出する。

警告（exit 0。--strict で exit 1）:
  - empty-bottom: 本文の下 1/3 がほぼ空で、本文全体の描画量（インク量）も少ない
                  （大きな箱に少ない文字・上に寄った短い本文。中身を足すか箱を詰める）
  - similar:      直前のスライドと見た目がよく似ている（dHash のハミング距離がしきい値以下。
                  同じ構図が続くと単調に見える）

インク量 = 背景色（画像の縁で最も多い色）と明確に違う画素の割合。表紙・章扉・引用・まとめ・
凡例ページなど、余白を取るのが普通のタイプは empty-bottom の対象外。

使い方:
  python tools/build_deck.py <deck_dir> --html
  python tools/preview_deck.py <deck_dir>
  python tools/check_visual.py <deck_dir> [--json out.json] [--similar 6] [--strict]
--json の各行は PNG の番号（slide）・type・src（deck.json の slides の何枚目か。自動挿入の凡例ページは null）・
title・インク量を持つ（deck-evaluator エージェントと review-deck の修正ループが番号の対応に使う）。
要: pillow（setup_deps.py --pillow）
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import build_deck  # noqa: E402

W, H = 1280, 720
BODY_BOX = (40, 130, 1240, 650)     # タイトル帯とフッターを除いた本文の範囲（px）
LOWER_BOX = (40, 480, 1240, 650)    # 本文の下 1/3
INK_DIFF = 60                       # 背景色との RGB 差の合計がこれを超える画素をインクとみなす
LOWER_EMPTY = 0.01                  # 下 1/3 のインク量がこれ未満なら「空」
BODY_THIN = 0.10                    # かつ本文全体のインク量がこれ未満なら警告
SIMILAR_DEFAULT = 6                 # dHash（64bit）のハミング距離がこれ以下なら「似ている」
SPARSE_OK = {"title", "section", "quote", "closing", "agenda", "canvas", "swimlane_legend", "diagram_legend",
             "statement"}
SIMILAR_SKIP = {"title", "section", "statement"}


def _pixels(im):
    get = getattr(im, "get_flattened_data", None)
    return list(get() if get else im.getdata())


def background(im) -> tuple:
    """画像の縁で最も多い色（8 階調に丸める）を背景色とみなす。"""
    w, h = im.size
    edge = [im.getpixel((x, y)) for x in range(0, w, 16) for y in (2, h - 3)]
    edge += [im.getpixel((x, y)) for y in range(0, h, 16) for x in (2, w - 3)]
    return Counter(tuple(c // 8 * 8 for c in p[:3]) for p in edge).most_common(1)[0][0]


def ink(im, box, bg) -> float:
    """box の範囲で背景色と明確に違う画素の割合（1/4 に縮小して数える）。"""
    reg = im.crop(box)
    reg = reg.resize((max(1, reg.width // 4), max(1, reg.height // 4)))
    px = _pixels(reg)
    n = sum(1 for p in px if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > INK_DIFF)
    return n / len(px) if px else 0.0


def dhash(im) -> int:
    """9×8 のグレースケールで横方向の明暗差から作る 64bit のハッシュ。"""
    g = im.convert("L").resize((9, 8))
    px = _pixels(g)
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (1 if px[r * 9 + c] > px[r * 9 + c + 1] else 0)
    return bits


def analyze(deck_dir: Path, similar: int = SIMILAR_DEFAULT):
    """(スライドごとの指標, 警告) を返す。"""
    from PIL import Image
    deck, theme, layout = build_deck.load_deck(deck_dir)
    # 展開（凡例ページの自動挿入・agenda の改ページ）後も deck.json の何枚目かを辿れるよう印を付ける
    src_deck = dict(deck, slides=[dict(s, _src=i) for i, s in enumerate(deck.get("slides", []), 1)])
    slides = build_deck.expand_slides(src_deck, layout)["slides"]
    prev_dir = deck_dir / "build" / "preview"
    pngs = sorted(prev_dir.glob("slide-*.png"))
    if not pngs:
        build_deck.fail(f"{prev_dir} にプレビュー画像がありません。先に build_deck.py --html と preview_deck.py を実行してください")
    if len(pngs) != len(slides):
        build_deck.warn(f"プレビュー画像 {len(pngs)} 枚とスライド {len(slides)} 枚が一致しません"
                        f"（preview_deck.py <deck_dir> を番号なしで再実行すると揃う）")
    rows, warns, prev = [], [], None
    for i, s in enumerate(slides, 1):
        p = prev_dir / f"slide-{i:02d}.png"
        t = s.get("type")
        if not p.exists():
            prev = None
            continue
        im = Image.open(p).convert("RGB").resize((W, H))
        bg = background(im)
        body, lower = ink(im, BODY_BOX, bg), ink(im, LOWER_BOX, bg)
        h = dhash(im)
        dist = bin(h ^ prev[0]).count("1") if prev else None
        rows.append({"slide": i, "type": t, "src": s.get("_src"), "title": s.get("title", ""), "ink": round(body, 3), "ink_lower": round(lower, 3), "similar_prev": dist})
        label = f"{i}枚目（type={t}）"
        if t not in SPARSE_OK and lower < LOWER_EMPTY and body < BODY_THIN:
            warns.append(f"{label}: [empty-bottom] 本文の下1/3がほぼ空（インク量 全体{body:.0%}・下{lower:.0%}）。"
                         f"根拠・事例を足すか、style で箱の高さを詰める・中央に寄せる")
        if dist is not None and dist <= similar and t not in SIMILAR_SKIP and prev[1] not in SIMILAR_SKIP:
            warns.append(f"{label}: [similar] 直前のスライドと見た目がよく似ている（距離{dist}）。"
                         f"同じ構図が続くので、表・図解・2カラムなど別のタイプを検討する")
        prev = (h, t)
    return rows, warns


def main():
    build_deck.setup_console()
    ap = argparse.ArgumentParser(description="プレビュー画像から見た目の偏り（下の空白・似たスライドの連続）を検出する")
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="スライドごとの指標を JSON で書き出す")
    ap.add_argument("--similar", type=int, default=SIMILAR_DEFAULT, help=f"似ているとみなす距離（既定 {SIMILAR_DEFAULT}）")
    ap.add_argument("--strict", action="store_true", help="警告があれば exit 1")
    args = ap.parse_args()
    try:
        import PIL  # noqa: F401
    except ImportError:
        build_deck.fail("pillow が必要です。初回セットアップを実行してください: /slide-deck:setup --pillow")
    deck_dir = Path(args.deck_dir).resolve()
    rows, warns = analyze(deck_dir, args.similar)
    if args.json:
        Path(args.json).write_text(json.dumps({"slides": rows, "warnings": warns}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    for w in warns:
        print("warn:", w)
    print(f"check_visual: {len(rows)}枚 警告{len(warns)}件")
    sys.exit(1 if args.strict and warns else 0)


if __name__ == "__main__":
    main()

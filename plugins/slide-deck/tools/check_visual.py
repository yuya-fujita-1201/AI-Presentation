#!/usr/bin/env python3
"""プレビュー画像（preview_deck.py の PNG）から見た目の偏りを検出する。

警告（exit 0。--strict で exit 1）:
  - empty-bottom: 本文領域（タイトル帯とフッターを除く y=130〜650）の下側に、縦に連続した空白帯が
                  --band px 以上ある（既定 150px。大きな箱に少ない文字・上に寄った短い本文・下 40% が空いた表。
                  箱を詰める・中央に寄せる・中身を足す）
  - empty-band:   同じく本文領域の途中（上下に中身がある位置）に空白帯が --band px 以上ある
                  （帯を 1 本足しても途中の空白は残るので、インク量ではなく帯の高さで見る。
                  リード直下から始まる隙間 y<=200 は、本文を縦中央に寄せた配置として許容する。ただし本文下端の空きが
                  その隙間の半分に満たない（中身が下に寄っている）場合は許容しない）
  - similar:      直前のスライドと見た目がよく似ている（dHash のハミング距離がしきい値以下。
                  同じ構図が続くと単調に見える）
  - stale:        プレビュー PNG が入力（deck.json・素材。build/ は除く）より古い／枚数が合わない／枚数を超えた古い PNG が残っている
                  （preview_deck.py <deck_dir> を番号なしで再実行すると揃う）

空白帯 = 背景色と明確に違う画素（インク）がほぼ無い行が縦に連続している範囲。表の罫線・図の線も
インクなので、罫線だけが下まで伸びた表は「埋まっている」扱いになる。表紙・章扉・引用・まとめ・
凡例ページなど、余白を取るのが普通のタイプは空白の対象外。

使い方:
  python tools/build_deck.py <deck_dir> --html
  python tools/preview_deck.py <deck_dir>
  python tools/check_visual.py <deck_dir> [--json out.json] [--similar 6] [--band 150] [--strict]
--json の各行は PNG の番号（slide）・type・src（deck.json の slides の何枚目か。自動挿入の凡例ページは null）・
title・インク量・最大の空白帯（band_h / band_y）を持つ（deck-evaluator エージェントと review-deck の修正ループが
番号の対応に使う）。
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
LOWER_BOX = (40, 480, 1240, 650)    # 本文の下 1/3（JSON の ink_lower 用。判定には使わない）
INK_DIFF = 60                       # 背景色との RGB 差の合計がこれを超える画素をインクとみなす
ROW_BLANK = 0.004                   # 1 行のインク量がこれ未満なら「空白の行」（幅 1200px の 5px 弱）
TOP_GAP_OK = 200                    # 空白帯がこの y 以前から始まる（リード直下〜本文開始の隙間）なら中央寄せとして許容
BALANCE_MIN = 0.5                   # 中央寄せとみなす条件: 下の空き >= 上の隙間 × この値
BAND_DEFAULT = 150                  # 空白帯がこの高さ（px）以上なら警告（本文領域 520px の約 29%）
SIMILAR_DEFAULT = 6                 # dHash（64bit）のハミング距離がこれ以下なら「似ている」
SPARSE_OK = {"title", "section", "quote", "closing", "agenda", "canvas", "swimlane_legend", "diagram_legend",
             "statement"}
SIMILAR_SKIP = {"title", "section", "statement"}


def _registry_types(attr: str) -> frozenset:
    """登録表（engine_registry）に登録された A 型タイプのうち、性質 attr が真のもの（kpi など。新しいタイプはここに書かなくてよい）。"""
    try:
        import engine_registry
        return engine_registry.types_where(attr)
    except Exception:     # pragma: no cover  （登録表を読めなくても検査は動く）
        return frozenset()


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


def row_ink(im, bg, x0: int = BODY_BOX[0], x1: int = BODY_BOX[2]) -> list:
    """画像の各行（y=0..H-1）の、x0〜x1 でのインク量（0〜1）。Pillow だけで求める。"""
    from PIL import Image, ImageChops
    diff = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, tuple(bg)))
    r, g, b = diff.split()
    mask = ImageChops.add(ImageChops.add(r, g), b).point(lambda v: 255 if v > INK_DIFF else 0)
    col = mask.crop((x0, 0, x1, im.height)).resize((1, im.height), Image.BOX)
    return [col.getpixel((0, y)) / 255 for y in range(im.height)]


def largest_blank_band(profile, top: int = BODY_BOX[1], bottom: int = BODY_BOX[3], row_blank: float = ROW_BLANK):
    """[top, bottom) の中で、空白の行が最も長く連続する範囲を (高さ, 開始 y, 終了 y) で返す。無ければ (0, top, top)。
    終了 y == bottom なら本文の下端まで空いている（trailing）。"""
    best = (0, top, top)
    start = None
    for y in range(top, bottom):
        if profile[y] < row_blank:
            if start is None:
                start = y
        else:
            if start is not None and y - start > best[0]:
                best = (y - start, start, y)
            start = None
    if start is not None and bottom - start > best[0]:
        best = (bottom - start, start, bottom)
    return best


def bottom_gap_of(profile, top: int = BODY_BOX[1], bottom: int = BODY_BOX[3], row_blank: float = ROW_BLANK) -> int:
    """本文領域の下端から、最後にインクのある行までの空き（px）。インクが 1 行も無ければ領域の高さ。"""
    for y in range(bottom - 1, top - 1, -1):
        if profile[y] >= row_blank:
            return bottom - 1 - y
    return bottom - top


def top_gap_of(profile, top: int = BODY_BOX[1], bottom: int = BODY_BOX[3], row_blank: float = ROW_BLANK) -> int:
    """本文領域の上端から、最初にインクのある行までの空き（px）。"""
    for y in range(top, bottom):
        if profile[y] >= row_blank:
            return y - top
    return bottom - top


def is_centered(top_gap: int, bottom_gap: int, min_gap: int = 60, tol: float = 0.4) -> bool:
    """中身が本文領域の縦中央に置かれているか（上下の空きが同程度）。split の本文側の bullets など、valign: middle の配置を空白として警告しない。"""
    if top_gap < min_gap or bottom_gap < min_gap:
        return False
    return abs(top_gap - bottom_gap) <= tol * max(top_gap, bottom_gap)


def band_warning(label: str, t, band, ink_body: float, min_band: int, bottom_gap=None):
    """空白帯の警告文（無ければ None）。純関数なので画像なしでテストできる。
    bottom_gap: 本文の下端から最後のインクまでの空き（px）。リード直下の隙間を「縦中央寄せ」として許容するときの
    釣り合いの確認に使う（中央寄せなら上の隙間と下の空きは同程度。中身が下端に寄っているなら許容しない）。None なら確認しない。"""
    h, y0, y1 = band
    if t in SPARSE_OK or t in _registry_types("sparse_ok") or h < min_band:
        return None
    body_h = BODY_BOX[3] - BODY_BOX[1]
    if y0 <= TOP_GAP_OK and y1 < BODY_BOX[3]:
        # リード直下から始まる隙間 = 本文を縦中央に寄せた（valign:middle）配置。下側の余白は別の帯として判定される。
        # ただし下の空きが上の隙間の半分に満たない（中身が下に寄っている）なら、中央寄せではなく上の空白として警告する
        if bottom_gap is None or bottom_gap >= h * BALANCE_MIN:
            return None
    if y1 >= BODY_BOX[3]:
        return (f"{label}: [empty-bottom] 本文の下側に{h}px（本文の{h / body_h:.0%}）の空白（y={y0}〜{y1}、本文のインク量{ink_body:.0%}）。"
                f"箱の高さを詰める・中央に寄せる・根拠や事例を足す（帯を 1 本足すだけでは途中の空白が残る）")
    return (f"{label}: [empty-band] 本文の途中に{h}px（本文の{h / body_h:.0%}）の空白帯（y={y0}〜{y1}）。"
            f"上下の中身の間を詰める・箱を中央に寄せる・内容を均等に配置する")


def input_mtime(deck_dir: Path) -> tuple:
    """デッキの入力（deck.json・画像などの素材・独自のレイアウト/テーマ。build/ 以下は除く）の最新の更新時刻と、そのファイル名。
    HTML の更新時刻ではなく入力で比べる理由: check_layout.py などが内容の変わらない再ビルドで HTML を作り直しても、
    プレビュー画像が古いことにはならないため。"""
    import os
    latest, name = 0.0, ""
    for root, dirs, files in os.walk(deck_dir):
        if Path(root) == deck_dir:
            dirs[:] = [d for d in dirs if d != "build"]
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.startswith("."):
                continue
            try:
                t = os.stat(os.path.join(root, f)).st_mtime
            except OSError:
                continue
            if t > latest:
                latest, name = t, f
    return latest, name


def stale_warnings(deck_dir: Path, html_path, n_slides: int) -> list:
    """プレビュー PNG の鮮度・枚数の警告。鮮度は入力ファイル（deck.json 等）の更新時刻と比べる。
    html_path は互換のために残してある（HTML の更新時刻は見ない。上の input_mtime の説明）。"""
    prev_dir = deck_dir / "build" / "preview"
    pngs = sorted(prev_dir.glob("slide-*.png"))
    out = []
    names = {p.name for p in pngs}
    missing = [i for i in range(1, n_slides + 1) if f"slide-{i:02d}.png" not in names]
    extra = [p.name for p in pngs if int(p.stem.split("-")[1]) > n_slides]
    if missing:
        out.append(f"[stale] プレビュー画像が足りません（{len(pngs)}枚。無い番号: {', '.join(map(str, missing[:8]))}"
                   f"{'…' if len(missing) > 8 else ''}）。preview_deck.py <deck_dir> を番号なしで実行して全枚作り直す")
    if extra:
        out.append(f"[stale] スライドは{n_slides}枚なのに、枚数を超えた古いプレビュー画像が残っています"
                   f"（{', '.join(extra[:6])}{'…' if len(extra) > 6 else ''}）。削除するか、preview_deck.py を番号なしで再実行する"
                   f"（全枚実行で自動的に消える）")
    t_in, f_in = input_mtime(deck_dir)
    if t_in:
        old = [p.name for p in pngs if p.stat().st_mtime < t_in - 1.0]
        if old:
            out.append(f"[stale] プレビュー画像{len(old)}枚が、入力（{f_in}）の更新より古い（{', '.join(old[:4])}{'…' if len(old) > 4 else ''}）。"
                       f"deck.json・素材を直した後は build_deck.py --html → preview_deck.py <deck_dir> で作り直してから判定する")
    return out


def body_side_crop(s: dict, layout: dict):
    """split は左右どちらかが端まで届くパネル（色面・画像）。パネルを含めて測ると、本文側が空でも行にインクがあると数えて
    空白帯を見逃す。本文側（パネルの反対側）だけを切り出す → (x0, x1)。split 以外は None。"""
    if not isinstance(s, dict) or s.get("type") != "split":
        return None
    p = ((layout.get("types") or {}).get("split") or {}).get("panel") or {}
    side = s.get("side") if s.get("side") in ("left", "right") else "left"
    r = s.get("ratio")
    ratio = r if isinstance(r, (int, float)) and not isinstance(r, bool) and 0.25 <= r <= 0.6 else p.get("ratio", 0.4)
    pw = round(W * ratio)
    mg, edge = p.get("margin", 56), p.get("edge", 72)
    x0, x1 = (pw + mg, W - edge) if side == "left" else (edge, W - pw - mg)
    return (x0, x1) if x1 - x0 > 100 else None


def analyze(deck_dir: Path, similar: int = SIMILAR_DEFAULT, band: int = BAND_DEFAULT):
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
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    rows, warns, prev = [], [], None
    warns.extend(stale_warnings(deck_dir, deck_dir / "build" / f"{deck_id}.html", len(slides)))
    for i, s in enumerate(slides, 1):
        p = prev_dir / f"slide-{i:02d}.png"
        t = s.get("type")
        if not p.exists():
            prev = None
            continue
        im = Image.open(p).convert("RGB").resize((W, H))
        crop = body_side_crop(s, layout)
        if crop:        # split: 本文側だけで、背景色・インク量・空白帯を測る
            im_b = im.crop((crop[0], 0, crop[1], H))
            bg = background(im_b)
            bw = im_b.width
            body, lower = ink(im_b, (0, BODY_BOX[1], bw, BODY_BOX[3]), bg), ink(im_b, (0, LOWER_BOX[1], bw, LOWER_BOX[3]), bg)
            prof = row_ink(im_b, bg, 0, bw)
        else:
            bg = background(im)
            body, lower = ink(im, BODY_BOX, bg), ink(im, LOWER_BOX, bg)
            prof = row_ink(im, bg)
        bnd = largest_blank_band(prof)
        h = dhash(im)
        dist = bin(h ^ prev[0]).count("1") if prev else None
        rows.append({"slide": i, "type": t, "src": s.get("_src"), "title": s.get("title", ""), "ink": round(body, 3),
                     "ink_lower": round(lower, 3), "band_h": bnd[0], "band_y": bnd[1], "similar_prev": dist})
        label = f"{i}枚目（type={t}）"
        # 画像を全面に敷く（fit: bleed）スライドは、画像が面を埋める主役のページなので空白帯の判定から外す
        bgap = bottom_gap_of(prof)
        if crop and is_centered(top_gap_of(prof), bgap):
            w = None       # split の本文側が縦中央に置かれている（意図した配置）
        else:
            w = band_warning(label, "canvas" if s.get("fit") == "bleed" else t, bnd, body, band, bgap)
        if w:
            warns.append(w)
        if dist is not None and dist <= similar and t not in SIMILAR_SKIP | _registry_types("similar_skip") and prev[1] not in SIMILAR_SKIP | _registry_types("similar_skip"):
            warns.append(f"{label}: [similar] 直前のスライドと見た目がよく似ている（距離{dist}）。"
                         f"同じ構図が続くので、表・図解・2カラムなど別のタイプを検討する")
        prev = (h, t)
    return rows, warns


def main():
    build_deck.setup_console()
    ap = argparse.ArgumentParser(description="プレビュー画像から見た目の偏り（本文の大きな空白帯・似たスライドの連続・古い画像）を検出する")
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="スライドごとの指標を JSON で書き出す")
    ap.add_argument("--similar", type=int, default=SIMILAR_DEFAULT, help=f"似ているとみなす距離（既定 {SIMILAR_DEFAULT}）")
    ap.add_argument("--band", type=int, default=BAND_DEFAULT,
                    help=f"本文領域の縦の空白帯がこの px 以上なら警告（既定 {BAND_DEFAULT}）")
    ap.add_argument("--strict", action="store_true", help="警告があれば exit 1")
    args = ap.parse_args()
    try:
        import PIL  # noqa: F401
    except ImportError:
        build_deck.fail("pillow が必要です。初回セットアップを実行してください: /slide-deck:setup --pillow")
    deck_dir = Path(args.deck_dir).resolve()
    rows, warns = analyze(deck_dir, args.similar, args.band)
    if args.json:
        Path(args.json).write_text(json.dumps({"slides": rows, "warnings": warns}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    for w in warns:
        print("warn:", w)
    print(f"check_visual: {len(rows)}枚 警告{len(warns)}件")
    sys.exit(1 if args.strict and warns else 0)


if __name__ == "__main__":
    main()

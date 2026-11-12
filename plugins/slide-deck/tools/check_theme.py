#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テーマの配色コントラスト（WCAG 2.x）を確認する機械ゲート。

対象のペア（テーマ内で実際に「文字色 / 背景色」として重なる組み合わせ）:
    text            / background        本文の基本色
    heading_text    / background        title / quote.text / col_heading 等の見出し文字色
    muted           / background        サブテキスト・脚注（footer は13pxまで下がるため normal 基準）
    accent          / background        eyebrow（15px bold）など小さい用途があるため normal 基準
    on_primary      / primary           section.title(52px bold) / closing.title(46px bold) のみに使用 → 大文字用途
    accent_on_primary / primary         section.number(72px bold) / closing.message(22px bold) のみに使用 → 大文字用途
    table_header_text / table_header_bg 表ヘッダー文字
    code_text       / code_bg           コードブロック文字

しきい値: 通常文字は 4.5:1、大文字用途（上記 on_primary/accent_on_primary の2組）は 3.0:1。
未達はすべて warning として列挙する。exit 1 になるのは「text/background が 4.5 未満」の
ときだけ（本文が読めないという最も実害の大きい欠陥のみを不合格にする）。

加えて、実使用の組（警告のみ・exit code には影響しない）:
    primary         / background       見出しや数値の文字色として使う（大文字用途 3.0:1）
    muted           / surface          淡い箱の中の補足文字（14〜15px。通常 4.5:1）
    accent          / highlight_fill   強調象限の見出し（18px 太字。大文字用途 3.0:1）
    on_primary_soft / primary          濃色面のリード・本文
    on_primary_muted / primary         濃色面の補足

さらに「面の視認性」（文字色ではなく塗り面同士のコントラスト）も確認する。steps/matrix/
cards/two_column などの淡い箱（surface）がディスプレイによって背景に溶けて見えなくなる
ことを防ぐためのチェックで、いずれも warning のみ（exit code には影響しない）:
    surface         / background  1.18 未満
    border          / background  1.40 未満
    highlight_fill  / surface     1.08 未満

使い方:
    python tools/check_theme.py default
    python tools/check_theme.py acn-slide-master
    python tools/check_theme.py ./my-theme.json         # 未保存のテーマ案を確認
    python tools/check_theme.py brand-navy --json out.json
    python tools/check_theme.py brand-navy --deck decks/my-deck   # そのデッキから見えるテーマ置き場を探す
    python tools/check_theme.py --shapes [--deck decks/my-deck]   # 同梱・登録済みの shape（形のプリセット）の一覧と検証
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
BUNDLED_THEMES = ROOT / "templates" / "themes"

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


# ---------------------------------------------------------------------------
# WCAG コントラスト比
# ---------------------------------------------------------------------------

def hex2rgb(h):
    h = str(h).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        fail(f"色の形式が不正です（#RRGGBB / #RGB ではありません）: {h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _channel(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    r, g, b = (_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    la = relative_luminance(hex2rgb(hex_a))
    lb = relative_luminance(hex2rgb(hex_b))
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# (フロント色トークン, 背景色トークン, 大文字用途か)
PAIRS = [
    ("text", "background", False),
    ("heading_text", "background", False),
    ("muted", "background", False),
    ("accent", "background", False),
    ("on_primary", "primary", True),
    ("accent_on_primary", "primary", True),
    ("table_header_text", "table_header_bg", False),
    ("code_text", "code_bg", False),
]
# 実使用の組（新規。警告のみで exit code には影響しない）。(前景, 背景, 大文字用途か)
EXTRA_PAIRS = [
    ("primary", "background", True),
    ("muted", "surface", False),
    ("accent", "highlight_fill", True),
    ("on_primary_soft", "primary", False),
    ("on_primary_muted", "primary", False),
]
NORMAL_MIN = 4.5
LARGE_MIN = 3.0

# 面の視認性（文字色ではなく塗り面同士のコントラスト）。steps/matrix/cards/two_column などの
# 淡い箱（surface）やハイライト（highlight_fill）、罫線（border）が、ディスプレイの発色や
# 輝度・彩度の違いによって背景色と見分けがつかなくなるのを防ぐための最低限のしきい値。
# 文字色の WCAG 基準（4.5:1）ほど厳しくする必要はないが、隣接する面同士が肉眼で区別できる
# 程度は必要。未達はすべて warning（exit code には影響しない。exit 1 は text/background のみ）。
# (面トークン, 比較先トークン, 最低コントラスト比, 説明)
SURFACE_PAIRS = [
    ("surface", "background", 1.18, "steps/matrix/cards/two_column などの淡い箱が背景から浮くか"),
    ("border", "background", 1.40, "表の罫線・箱の外枠が背景から見分けられるか"),
    ("highlight_fill", "surface", 1.08, "matrix の強調象限が通常の箱から見分けられるか"),
]


# ---------------------------------------------------------------------------
# テーマ読み込み（テーマ名 or 未保存の json ファイルの両対応。extends を解決する）
# ---------------------------------------------------------------------------

def load_theme_input(spec, deck_dir=None):
    """テーマ名、または未保存のテーマ JSON ファイルのパスを受け取り、解決済みテーマ dict を返す。

    ファイルパスの場合は一時ディレクトリにそのまま配置して探索パスの先頭に加えたうえで
    build_deck.load_theme() を呼ぶ（build_deck が読み込めるとき）。これにより、実際に
    build_deck.py がビルド時に使う派生ロジック（mix() によるトークン再計算・extends チェーンの
    解決）をそのまま通し、そのJSONを保存してビルドしたときと同じ数値になるようにする。
    以前は deep_merge だけで済ませており、派生トークン（table_header_bg / muted / surface /
    highlight_fill / border / heading_text 等）の再計算が抜けていた（P0）。"""
    p = Path(spec)
    if p.suffix.lower() == ".json" and p.exists():
        raw = p.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
        if build_deck is None:
            # build_deck が読み込めない場合の劣化動作（deep_merge のみ。派生は行わない）。
            parent = data.get("extends") or (None if data.get("name") == "default" else "default")
            if parent:
                base = _load_bundled_or_named(parent)
                merged = dict(base)
                merged.update(data)
                merged["colors"] = {**base.get("colors", {}), **data.get("colors", {})}
                merged["fonts"] = {**base.get("fonts", {}), **data.get("fonts", {})}
                data = merged
            return data
        name = data.get("name") or p.stem
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            (tmp_dir / f"{name}.json").write_text(raw, encoding="utf-8")
            dirs = [tmp_dir] + build_deck.theme_dirs(deck_dir)
            return build_deck.load_theme(name, dirs)
    return _load_bundled_or_named(spec, deck_dir)


def _load_bundled_or_named(name, deck_dir=None):
    if build_deck is not None:
        # カレントディレクトリの ./themes/ も探索対象に含める。new_theme.py の既定の書き込み先が
        # ./themes/<name>.json のため、これが無いと themes.md / add-theme SKILL.md が案内する
        # 「new_theme.py <name>」→「check_theme.py <name>」の手順がそのままではテーマを
        # 見つけられずエラーになっていた（P0）。
        dirs = build_deck.theme_dirs(deck_dir)
        return build_deck.load_theme(name, dirs)
    path = BUNDLED_THEMES / f"{name}.json"
    if not path.exists():
        fail(f"テーマ '{name}' が見つかりません（{path}）")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _default_layout(deck_dir):
    """同梱の default レイアウト（解決済み）。shape / テーマの layout 差分の領域名・値の型の検査に使う。"""
    if build_deck is None:
        return None
    try:
        return build_deck.load_layout("default", deck_dir)
    except SystemExit:
        return None


def _default_colors(deck_dir) -> dict:
    """shape 単体の検査で、色キーの値が存在するかを見る基準（同梱 default テーマの色。別テーマにだけある色は警告になる）。"""
    if build_deck is None:
        return {}
    try:
        return build_deck.load_theme("default", build_deck.theme_dirs(deck_dir)).get("colors") or {}
    except SystemExit:
        return {}


def check_shapes(deck_dir) -> int:
    """見つかった shape を一覧にして検証する（形・値の型・領域名・色・使われないトークン）。fail が 1 つでもあれば exit 1。"""
    import shape_engine
    resolved = _default_layout(deck_dir) or {}
    base = (resolved.get("_unresolved") or resolved).get("tokens") or {}
    colors = _default_colors(deck_dir) or None
    bad = 0
    print("shape の探索先: " + " / ".join(str(d) for d in shape_engine.shape_dirs(deck_dir)))
    shapes = shape_engine.list_shapes(deck_dir)
    if not shapes:
        print("  shape が見つかりません")
    for name, path in shapes:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            print(f"  {name:12} NG  読めません: {e}")
            bad += 1
            continue
        issues = shape_engine.validate_shape(data, name, base, resolved or None, colors, "warn")
        fails = [m for lv, m in issues if lv == "fail"]
        label = data.get("label", "") if isinstance(data, dict) else ""
        toks = data.get("tokens") if isinstance(data, dict) else None
        rule_tok = toks.get("rule") if isinstance(toks, dict) else None
        rule = rule_tok.get("style", "line") if isinstance(rule_tok, dict) else "line"
        shown = f"{label}（罫線: {rule}）"
        print(f"  {name:12} {'NG' if fails else 'OK'}  {shown}  {path}")
        for lv, m in issues:
            print(f"      {'エラー' if lv == 'fail' else '警告'}: {m}")
        bad += 1 if fails else 0
    return 1 if bad else 0


def check_theme_shape(theme, deck_dir) -> list:
    """テーマ JSON の shape / tokens / layout の検査 → [(level, 本文)]（build_deck の読み込みと同じ検査。fail でも止まらず列挙する）。"""
    import shape_engine as shp
    if build_deck is None:
        return []
    resolved = _default_layout(deck_dir)
    if resolved is None:
        return []
    raw = resolved.get("_unresolved") or resolved
    base_tokens = raw.get("tokens")
    where = f"テーマ '{theme.get('name', '')}'"
    out, shape = [], None
    name = theme.get("shape")
    if name is not None:
        try:
            shape = shp.load_shape(name, deck_dir, f"{where} の shape")
        except ValueError as e:
            out.append(("fail", str(e)))
        else:
            out += shp.validate_shape(shape, name, base_tokens, resolved, theme.get("colors") or {})
    th_tokens, th_layout = theme.get("tokens"), theme.get("layout")
    out += shp.check_tokens(th_tokens, base_tokens, where)
    toks = shp.merge_tokens(base_tokens, (shape or {}).get("tokens"), th_tokens if isinstance(th_tokens, dict) else None)
    out += shp.check_layout_diff(th_layout, where, toks, resolved, theme.get("colors") or {})
    return out


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description="テーマ配色のWCAGコントラスト比を確認")
    ap.add_argument("theme", nargs="?", help="テーマ名（例: default, acn-slide-master）または未保存のテーマJSONのパス")
    ap.add_argument("--shapes", action="store_true", help="テーマではなく shape（形のプリセット）の一覧と検証を行う（探索先: SLIDE_DECK_SHAPES / <デッキ>/shapes/ / 同梱）")
    ap.add_argument("--json", help="結果JSONの出力先")
    ap.add_argument("--deck", help="デッキのフォルダ。<deck>/themes/ とその親（3階層上まで）の themes/ もテーマの探索先に加える"
                                   "（build_deck.py と同じ探索）")
    args = ap.parse_args()

    deck_dir = Path(args.deck).resolve() if args.deck else None
    if args.shapes:
        return check_shapes(deck_dir)
    if not args.theme:
        fail("テーマ名（または JSON のパス）を指定してください。shape の一覧は --shapes")
    theme = load_theme_input(args.theme, deck_dir)
    colors = theme.get("colors", {})
    missing = [t for pair in PAIRS + EXTRA_PAIRS for t in pair[:2] if t not in colors]
    missing += [t for pair in SURFACE_PAIRS for t in pair[:2] if t not in colors]
    if missing:
        fail(f"テーマにトークンがありません: {', '.join(sorted(set(missing)))}")

    rows = []
    surface_rows = []
    warnings = []
    hard_fail = False
    shape_fail = False
    print(f"check_theme: {theme.get('name', args.theme)}")
    shape_issues = check_theme_shape(theme, deck_dir)
    if theme.get("shape") is not None or theme.get("tokens") or theme.get("layout"):
        print(f"  --- shape / tokens / layout（{'エラー ' + str(sum(1 for lv, _ in shape_issues if lv == 'fail')) + '件' if any(lv == 'fail' for lv, _ in shape_issues) else 'OK'}） ---")
    for lv, m in shape_issues:
        print(f"  {'エラー' if lv == 'fail' else '警告'}: {m}")
        if lv == "fail":
            shape_fail = True
        warnings.append(m)
    for fg, bg, is_large in PAIRS:
        ratio = contrast_ratio(colors[fg], colors[bg])
        min_needed = LARGE_MIN if is_large else NORMAL_MIN
        ok = ratio >= min_needed
        label = "大文字用途" if is_large else "通常文字"
        line = f"  {fg:18} / {bg:18} = {ratio:5.2f}:1  (基準 {min_needed}:1・{label})  {'OK' if ok else 'NG'}"
        print(line)
        rows.append({"fg": fg, "bg": bg, "ratio": round(ratio, 2), "min": min_needed, "large_text": is_large, "ok": ok})
        if not ok:
            msg = f"{fg}/{bg} のコントラスト比 {ratio:.2f}:1 が基準 {min_needed}:1 未満です（{label}）"
            warnings.append(msg)
            warn(msg)
            if fg == "text" and bg == "background":
                hard_fail = True

    print("  --- 実使用の組（警告のみ。exit code には影響しません） ---")
    for fg, bg, is_large in EXTRA_PAIRS:
        ratio = contrast_ratio(colors[fg], colors[bg])
        min_needed = LARGE_MIN if is_large else NORMAL_MIN
        ok = ratio >= min_needed
        label = "大文字用途" if is_large else "通常文字"
        print(f"  {fg:18} / {bg:18} = {ratio:5.2f}:1  (基準 {min_needed}:1・{label})  {'OK' if ok else 'NG'}")
        rows.append({"fg": fg, "bg": bg, "ratio": round(ratio, 2), "min": min_needed, "large_text": is_large,
                     "ok": ok, "extra": True})
        if not ok:
            msg = f"{fg}/{bg} のコントラスト比 {ratio:.2f}:1 が基準 {min_needed}:1 未満です（{label}。実使用の組）"
            warnings.append(msg)
            warn(msg)

    print("  --- 面の視認性（塗り面同士。exit code には影響しません） ---")
    for surf, against, min_needed, desc in SURFACE_PAIRS:
        ratio = contrast_ratio(colors[surf], colors[against])
        ok = ratio >= min_needed
        line = f"  {surf:18} / {against:18} = {ratio:5.2f}:1  (基準 {min_needed}:1)  {'OK' if ok else 'NG'}"
        print(line)
        surface_rows.append({"fg": surf, "bg": against, "ratio": round(ratio, 2), "min": min_needed, "ok": ok})
        if not ok:
            msg = (f"{surf}/{against} のコントラスト比 {ratio:.2f}:1 が基準 {min_needed}:1 未満です"
                   f"（面の視認性: {desc}）")
            warnings.append(msg)
            warn(msg)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"theme": theme.get("name", args.theme), "pairs": rows, "surface_pairs": surface_rows},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    print(f"check_theme: {len(PAIRS) + len(EXTRA_PAIRS) + len(SURFACE_PAIRS)}組中 警告{len(warnings)}件"
          + ("（text/background が基準未達のため不合格）" if hard_fail else "")
          + ("（shape / tokens / layout にエラーがあるため不合格）" if shape_fail else ""))
    return 1 if (hard_fail or shape_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())

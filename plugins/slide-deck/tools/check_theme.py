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

さらに「面の視認性」（文字色ではなく塗り面同士のコントラスト）も確認する。steps/matrix/
cards/two_column などの淡い箱（surface）がディスプレイによって背景に溶けて見えなくなる
ことを防ぐためのチェックで、いずれも warning のみ（exit code には影響しない）:
    surface         / background  1.18 未満
    border          / background  1.40 未満
    highlight_fill  / surface     1.08 未満

使い方:
    python tools/check_theme.py default
    python tools/check_theme.py accenture-purple
    python tools/check_theme.py ./my-theme.json         # 未保存のテーマ案を確認
    python tools/check_theme.py brand-navy --json out.json
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

def load_theme_input(spec):
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
            dirs = [tmp_dir] + build_deck.theme_dirs(Path.cwd())
            return build_deck.load_theme(name, dirs)
    return _load_bundled_or_named(spec)


def _load_bundled_or_named(name):
    if build_deck is not None:
        # カレントディレクトリの ./themes/ も探索対象に含める。new_theme.py の既定の書き込み先が
        # ./themes/<name>.json のため、これが無いと themes.md / add-theme SKILL.md が案内する
        # 「new_theme.py <name>」→「check_theme.py <name>」の手順がそのままではテーマを
        # 見つけられずエラーになっていた（P0）。
        dirs = build_deck.theme_dirs(Path.cwd())
        return build_deck.load_theme(name, dirs)
    path = BUNDLED_THEMES / f"{name}.json"
    if not path.exists():
        fail(f"テーマ '{name}' が見つかりません（{path}）")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description="テーマ配色のWCAGコントラスト比を確認")
    ap.add_argument("theme", help="テーマ名（例: default, accenture-purple）または未保存のテーマJSONのパス")
    ap.add_argument("--json", help="結果JSONの出力先")
    args = ap.parse_args()

    theme = load_theme_input(args.theme)
    colors = theme.get("colors", {})
    missing = [t for pair in PAIRS for t in pair[:2] if t not in colors]
    missing += [t for pair in SURFACE_PAIRS for t in pair[:2] if t not in colors]
    if missing:
        fail(f"テーマにトークンがありません: {', '.join(sorted(set(missing)))}")

    rows = []
    surface_rows = []
    warnings = []
    hard_fail = False
    print(f"check_theme: {theme.get('name', args.theme)}")
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

    print(f"check_theme: {len(PAIRS) + len(SURFACE_PAIRS)}組中 警告{len(warnings)}件"
          + ("（text/background が基準未達のため不合格）" if hard_fail else ""))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

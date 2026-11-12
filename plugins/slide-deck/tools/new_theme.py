#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新しいテーマ（色・フォント）を追加するための雛形ジェネレーター。

使い方:
    python tools/new_theme.py <name>                  # default 全トークンを写した雛形を作成
    python tools/new_theme.py <name> --from acn-slide-master   # 別テーマを写して作成
    python tools/new_theme.py <name> --extends acn-slide-master # 差分だけ書く最小テーマを作成
    python tools/new_theme.py <name> --dir ./themes    # 出力先を明示
    python tools/new_theme.py <name> --shape soft      # 形のプリセット（角丸・罫線・見出しの組み方）も指定する

出力先の優先順:
    --dir 指定 → --deck 指定（<deck>/themes/）→ 環境変数 SLIDE_DECK_THEMES の先頭 → カレントディレクトリの ./themes/
    作成後に「書き込み先」と「どのデッキから見つかるか」を表示する（探索規則は deck_paths.py）。
    （同梱の templates/themes/ には --dir で明示したときだけ書く。プラグイン更新で
      ユーザーの独自テーマが無警告で失われないようにするため）

作成後は deck.json の meta.theme に <name> を指定すればそのテーマでビルドされる。
テーマは default をベースにマージされ、明示していないトークンは自身の基本色
（background/surface/text/muted/primary/accent/on_primary）から自動導出されるため、
--extends では上書きしたい基本色だけ書けばよい。トークンの意味は references/themes.md を参照。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
BUNDLED_THEMES = ROOT / "templates" / "themes"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

sys.path.insert(0, str(TOOLS_DIR))
try:
    import build_deck  # type: ignore
except Exception:
    build_deck = None
import deck_paths  # noqa: E402
import shape_engine  # noqa: E402


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


def load_theme_file(name: str) -> dict:
    path = BUNDLED_THEMES / f"{name}.json"
    if not path.exists():
        fail(f"ベーステーマ '{name}' が同梱テーマに見つかりません（{path}）")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_out_dir(arg_dir, deck=None):
    return deck_paths.default_out_dir("themes", deck, arg_dir)


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description="新しいテーマの雛形を作成")
    ap.add_argument("name", help="テーマ名（kebab-case。例: brand-navy）")
    ap.add_argument("--from", dest="seed", default="default", help="トークン値の写し元テーマ（既定: default）")
    ap.add_argument("--extends", help="差分だけ書く最小テーマにする（このテーマを親にする）")
    ap.add_argument("--dir", help="出力先ディレクトリ（既定: SLIDE_DECK_THEMES / ./themes/）")
    ap.add_argument("--deck", help="このデッキのフォルダの themes/ に作る（--dir より弱い）")
    ap.add_argument("--shape", help="形のプリセット名（classic / sharp / soft / editorial、または登録した shape）。テーマ JSON に \"shape\" を書く")
    ap.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    args = ap.parse_args()

    if not NAME_RE.match(args.name):
        fail(f"テーマ名は kebab-case で指定してください（英小文字・数字・ハイフン）: {args.name}")
    if args.name == "default":
        fail("'default' は予約名です。別名にしてください。")

    if args.shape:
        shape_engine.load_shape(args.shape, args.deck, "--shape", fail=fail)    # 無い名前・不正な名前は候補つきで fail

    out_dir = resolve_out_dir(args.dir, args.deck)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.json"
    if out_path.exists() and not args.force:
        fail(f"すでに存在します: {out_path}（上書きは --force）")

    if args.extends:
        # 差分だけ書く最小テーマ（親のトークンを継承し、上書きしたい分だけ書く）
        base = load_theme_file(args.extends)
        theme = {
            "name": args.name,
            "extends": args.extends,
            "colors": {"primary": base["colors"].get("primary", "#000000")},
            "fonts": {},
        }
        made_note = (
            f"extends: {args.extends} を継承。colors には background/surface/text/muted/"
            "primary/accent/on_primary のうち変えたい基本色だけ書けば、table_header_bg 等の"
            "残りは自動導出される（references/themes.md の派生規則を参照）"
        )
    else:
        # default（または --from）の全トークンを写した自己完結テーマ
        seed = load_theme_file(args.seed)
        theme = {"name": args.name, "colors": dict(seed["colors"]), "fonts": dict(seed["fonts"])}
        made_note = f"{args.seed} の全トークンを複製。色・フォントを編集して使う（不要な行は消せば default から継承）"

    if args.shape:
        theme["shape"] = args.shape
        made_note += f"。shape: {args.shape}（deck.json の meta.shape があればそちらが優先）"
    try:
        out_path.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except PermissionError:
        fail(f"{out_path} に書き込めません（他アプリで開いている場合は閉じてから再実行してください）")

    print(f"作成しました: {out_path}")
    print(f"  {made_note}")
    if out_dir == BUNDLED_THEMES:
        note("同梱テーマ置き場に作成しました。プラグイン更新で消えないようにするには")
        note("環境変数 SLIDE_DECK_THEMES にユーザー用ディレクトリを設定するか、--dir で明示してください。")
    for line in deck_paths.visibility_lines("themes", out_dir):
        print(line)
    print(f'次の手順: 色を編集 -> deck.json の meta.theme に "{args.name}" を指定 -> build_deck.py で再ビルド')
    print("トークンの意味は references/themes.md を参照。作成後は check_theme.py でコントラストを確認してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

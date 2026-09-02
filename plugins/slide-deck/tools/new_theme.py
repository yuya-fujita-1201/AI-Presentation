#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新しいテーマ（色・フォント）を追加するための雛形ジェネレーター。

使い方:
    python tools/new_theme.py <name>                  # default 全トークンを写した雛形を作成
    python tools/new_theme.py <name> --from accenture-purple   # 別テーマを写して作成
    python tools/new_theme.py <name> --extends accenture-purple # 差分だけ書く最小テーマを作成
    python tools/new_theme.py <name> --dir ./themes    # 出力先を明示

出力先の優先順:
    --dir 指定 → 環境変数 SLIDE_DECK_THEMES の先頭 → 同梱 templates/themes/

作成後は deck.json の meta.theme に <name> を指定すればそのテーマでビルドされる。
テーマは default をベースにマージされるため、不要なトークンは消して default から継承してよい。
トークンの意味は references/themes.md を参照。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLED_THEMES = ROOT / "templates" / "themes"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_theme_file(name: str) -> dict:
    path = BUNDLED_THEMES / f"{name}.json"
    if not path.exists():
        sys.exit(f"error: ベーステーマ '{name}' が同梱テーマに見つかりません（{path}）")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_out_dir(arg_dir: str | None) -> Path:
    if arg_dir:
        return Path(arg_dir)
    env = os.environ.get("SLIDE_DECK_THEMES")
    if env:
        first = next((p for p in env.split(os.pathsep) if p.strip()), None)
        if first:
            return Path(first)
    return BUNDLED_THEMES


def main() -> int:
    ap = argparse.ArgumentParser(description="新しいテーマの雛形を作成")
    ap.add_argument("name", help="テーマ名（kebab-case。例: brand-navy）")
    ap.add_argument("--from", dest="seed", default="default", help="トークン値の写し元テーマ（既定: default）")
    ap.add_argument("--extends", help="差分だけ書く最小テーマにする（このテーマを親にする）")
    ap.add_argument("--dir", help="出力先ディレクトリ")
    ap.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    args = ap.parse_args()

    if not NAME_RE.match(args.name):
        sys.exit(f"error: テーマ名は kebab-case で指定してください（英小文字・数字・ハイフン）: {args.name}")
    if args.name == "default":
        sys.exit("error: 'default' は予約名です。別名にしてください。")

    out_dir = resolve_out_dir(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.json"
    if out_path.exists() and not args.force:
        sys.exit(f"error: すでに存在します: {out_path}（上書きは --force）")

    if args.extends:
        # 差分だけ書く最小テーマ（親のトークンを継承し、上書きしたい分だけ書く）
        base = load_theme_file(args.extends)
        theme = {
            "name": args.name,
            "extends": args.extends,
            "colors": {"primary": base["colors"].get("primary", "#000000")},
            "fonts": {},
        }
        note = f"extends: {args.extends} を継承。colors/fonts に上書きしたいトークンだけ残す"
    else:
        # default（または --from）の全トークンを写した自己完結テーマ
        seed = load_theme_file(args.seed)
        theme = {"name": args.name, "colors": dict(seed["colors"]), "fonts": dict(seed["fonts"])}
        note = f"{args.seed} の全トークンを複製。色・フォントを編集して使う（不要な行は消せば default から継承）"

    out_path.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"作成しました: {out_path}")
    print(f"  {note}")
    if out_dir == BUNDLED_THEMES:
        print("  ※ 同梱テーマ置き場に作成しました。プラグイン更新で消したくない場合は")
        print("     環境変数 SLIDE_DECK_THEMES にユーザー用ディレクトリを設定し、--dir で出力してください。")
    print(f"次の手順: 色を編集 → deck.json の meta.theme に \"{args.name}\" を指定 → build_deck.py で再ビルド")
    print("トークンの意味は references/themes.md を参照。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

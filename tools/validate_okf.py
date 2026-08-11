#!/usr/bin/env python3
"""OKFバンドルの機械検証ゲート。

チェック内容:
1. 非予約Markdown（index.md / log.md 以外）に YAML フロントマターがあり `type:` を含む
2. frontmatter に `generated:`（by / at）があるか（v0.2 準拠。無ければ警告）
3. Markdown 相対リンクのリンク切れ検出（http(s) と #アンカーのみは対象外）
4. 各ディレクトリの index.md が、同階層の .md（index/log 除く）を全て言及しているか
5. ルート index.md に okf_version 宣言があるか

使い方: python3 tools/validate_okf.py [knowledge/]
終了コード: エラーありなら 1（警告のみなら 0）
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
RESERVED = {"index.md", "log.md"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

errors = []
warnings = []


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    for fn in sorted(filenames):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT)
        text = open(path, encoding="utf-8").read()
        fm = parse_frontmatter(text)

        is_root_index = rel == "index.md"
        if fn in RESERVED and not is_root_index:
            if fm is not None and fn == "index.md":
                errors.append(f"{path}: 予約ファイル index.md にフロントマターがある（ルート以外は禁止）")
        elif is_root_index:
            if fm is None or "okf_version" not in fm:
                errors.append(f"{path}: ルート index.md に okf_version 宣言がない")
        else:
            if fm is None:
                errors.append(f"{path}: フロントマターがない")
            else:
                if not re.search(r"^type:\s*\S+", fm, re.M):
                    errors.append(f"{path}: frontmatter に type がない")
                if "generated:" not in fm:
                    warnings.append(f"{path}: frontmatter に generated がない（v0.2推奨）")
                elif "timestamp:" in fm:
                    warnings.append(f"{path}: 旧 timestamp フィールドが残っている")

        # リンク検証（フェンスコードブロック内のサンプルリンクは対象外）
        body = text[len(fm) + 8 if fm else 0:]
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        for m in LINK_RE.finditer(body):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path = target.split("#")[0]
            if not target_path:
                continue
            if target_path.startswith("/"):
                errors.append(f"{path}: 絶対パスリンク {target}")
                continue
            resolved = os.path.normpath(os.path.join(dirpath, target_path))
            if not os.path.exists(resolved):
                errors.append(f"{path}: リンク切れ {target}")

    # index.md の網羅チェック
    index_path = os.path.join(dirpath, "index.md")
    if os.path.exists(index_path):
        index_text = open(index_path, encoding="utf-8").read()
        for fn in sorted(filenames):
            if fn.endswith(".md") and fn not in RESERVED:
                if fn not in index_text:
                    errors.append(f"{index_path}: {fn} が index.md に載っていない")

print(f"=== OKF validate: {ROOT} ===")
for w in warnings:
    print(f"WARN  {w}")
for e in errors:
    print(f"ERROR {e}")
print(f"--- errors: {len(errors)}, warnings: {len(warnings)} ---")
sys.exit(1 if errors else 0)

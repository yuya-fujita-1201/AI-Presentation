#!/usr/bin/env python3
"""sources台帳の機械ゲート。validate_okf.pyの穴（type語彙・必須フィールド・主張テーブル・重複）を塞ぐ。"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TYPE_ENUM = {"Concept", "Video", "Article", "Book", "Guide", "Topic"}


def frontmatter(text):
    m = re.match(r"^---\n([\s\S]*?)\n---\n", text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def fail(msg):
    print("NG:", msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--mode", choices=["video", "article"], required=True)
    a = ap.parse_args()

    existing_resources = {}
    for p in glob.glob(os.path.join(ROOT, "knowledge/sources/*.md")):
        try:
            fm, _ = frontmatter(open(p).read())
        except Exception:
            continue
        if fm:
            m = re.search(r"^resource:\s*(\S+)", fm, re.M)
            if m:
                existing_resources.setdefault(m.group(1).strip(), []).append(os.path.basename(p))

    origins = set()
    for f in a.files:
        path = os.path.join(ROOT, f) if not os.path.isabs(f) else f
        if not os.path.exists(path):
            fail(f"{f}: 実在しない")
        text = open(path).read()
        fm, body = frontmatter(text)
        if fm is None:
            fail(f"{f}: frontmatterなし")
        tm = re.search(r"^type:\s*(\S+)", fm, re.M)
        if not tm or tm.group(1) not in TYPE_ENUM:
            fail(f"{f}: type語彙違反 ({tm.group(1) if tm else 'なし'})")
        expect_type = "Video" if a.mode == "video" else "Article"
        if tm.group(1) != expect_type:
            fail(f"{f}: type={tm.group(1)} (期待 {expect_type})")
        for field in ["title:", "description:", "resource:", "tags:", "generated:", "origin:", "retrieved:"]:
            if not re.search(rf"^{field}", fm, re.M):
                fail(f"{f}: frontmatter必須欠落 {field}")
        if a.mode == "video":
            if not re.search(r"^subs:\s*(auto|manual)", fm, re.M):
                fail(f"{f}: subs: auto|manual 欠落")
        else:
            if not re.search(r"^source_tier:\s*(primary|secondary)", fm, re.M):
                fail(f"{f}: source_tier欠落")
            if not re.search(r"^site:", fm, re.M):
                fail(f"{f}: site欠落")
        if len(body) < 2000:
            fail(f"{f}: 本文{len(body)}字 (<2000)")
        rm = re.search(r"^resource:\s*(\S+)", fm, re.M)
        if rm:
            url = rm.group(1).strip()
            dupes = [b for b in existing_resources.get(url, []) if b != os.path.basename(path)]
            if dupes:
                fail(f"{f}: resource重複 {url} ↔ {dupes}")
        om = re.search(r"^origin:\s*\"?([^\"\n]+)\"?", fm, re.M)
        if om:
            origins.add(om.group(1).strip())
        if a.mode == "video":
            rows = re.findall(r"^\|\s*c\d+\s*\|\s*\[\d{1,2}:\d{2}\]", body, re.M)
            if len(rows) < 3:
                fail(f"{f}: 主張テーブル行 {len(rows)}件 (<3)  形式: | c1 | [mm:ss] | 主張 | 出所種別 | impact |")
            if "（聞き取り）" not in body and re.search(r"^subs:\s*auto", fm, re.M):
                print(f"WARN {f}: auto字幕だが（聞き取り）注記が0件")
    print(f"check_ledger OK: {len(a.files)}件 (origins: {len(origins)})")
    sys.exit(0)


if __name__ == "__main__":
    main()

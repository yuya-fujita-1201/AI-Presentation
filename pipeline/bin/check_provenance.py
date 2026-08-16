#!/usr/bin/env python3
"""出典系譜ゲート（v1簡易版）: knowledge→grade_k遷移前に実行。
- 各videoソース台帳に主張テーブル（3行以上）があるか
- knowledgeコンセプトにソースへのインラインリンクが実在するか
- 独立origin数
（完全な独立性保証ではなく「検知の一層」— T-MAX R4 P4の設計判断どおり）"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fail(msg):
    print("NG:", msg)
    sys.exit(1)


def main():
    kdir = sys.argv[sys.argv.index("--kdir") + 1]
    theme = sys.argv[sys.argv.index("--theme") + 1]
    src_files = glob.glob(os.path.join(ROOT, f"knowledge/sources/*-{theme}-*.md"))
    origins = set()
    for p in src_files:
        text = open(p).read()
        om = re.search(r"^origin:\s*\"?([^\"\n]+)\"?", text, re.M)
        if om:
            origins.add(om.group(1).strip())
        if os.path.basename(p).startswith("video-"):
            # 主張テーブルはパイプラインの台帳テンプレートが持つ仕様。パイプライン以前に
            # 手作業で作られた台帳（generated.by が pipeline でない）に遡及適用すると、
            # 事実を後から捏造しないと通せない偽の失敗になるため対象外とする。
            # 作成時点の強制は check_ledger.py が担っているので検知層は失われない（2026-08-16）
            by = re.search(r"^\s*by:\s*(\S+)", text, re.M)
            if by and "pipeline" not in by.group(1):
                print(f"SKIP {os.path.basename(p)}: パイプライン以前の台帳（by={by.group(1)}）")
                continue
            rows = re.findall(r"^\|\s*c\d+\s*\|", text, re.M)
            if len(rows) < 3:
                fail(f"{os.path.basename(p)}: 主張テーブル{len(rows)}行 (<3)")
    kfiles = [p for p in glob.glob(os.path.join(ROOT, kdir, "*.md"))
              if os.path.basename(p) != "index.md"]
    if not kfiles:
        fail(f"{kdir} にコンセプトがない")
    for p in kfiles:
        text = open(p).read()
        links = re.findall(r"\]\((\.\./)*sources/[^)]+\)|\]\((\.\./)+sources/", text)
        links2 = re.findall(r"\((?:\.\./)+sources/[^)]+\.md\)", text)
        if not links and not links2:
            fail(f"{os.path.basename(p)}: sources/へのインライン出典リンクが0件")
    if len(origins) < min(3, len(src_files)):
        fail(f"独立origin {len(origins)}種 (<3)")
    print(f"check_provenance OK: 台帳{len(src_files)}本 / origin{len(origins)}種 / コンセプト{len(kfiles)}本")
    sys.exit(0)


if __name__ == "__main__":
    main()

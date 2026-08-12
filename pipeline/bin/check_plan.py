#!/usr/bin/env python3
"""knowledgeチェックポイント（plan.json）のsemantic gate。
「同一ソースの言い換え量産で進捗を偽装する」経路を塞ぐ（T-MAX R4 P2）。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fail(msg):
    print("NG:", msg)
    sys.exit(1)


def main():
    plan_f = sys.argv[1]
    kdir = sys.argv[sys.argv.index("--kdir") + 1] if "--kdir" in sys.argv else None
    if not os.path.exists(plan_f):
        print("plan.json未作成（初回ランなら次回作成）")
        sys.exit(0)
    try:
        plan = json.load(open(plan_f))
    except Exception as e:
        fail(f"plan.jsonがJSONでない: {e}")
    concepts = plan.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        fail("concepts配列がない")
    seen_sets = []
    for e in concepts:
        f = e.get("file", "")
        if not f or not f.endswith(".md"):
            fail(f"file不正: {f}")
        if not e.get("purpose"):
            fail(f"{f}: purposeなし")
        srcs = e.get("sources", [])
        if not isinstance(srcs, list):
            fail(f"{f}: sources不正")
        if len(srcs) < 2 and not e.get("single_source_attributed"):
            fail(f"{f}: sources {len(srcs)}件 (<2) かつ single_source_attributed でない")
        for s in srcs:
            sp = os.path.join(ROOT, s)
            if not os.path.exists(sp):
                fail(f"{f}: 参照先台帳が実在しない {s}")
        fs = frozenset(srcs)
        if fs and fs in seen_sets:
            fail(f"{f}: sources集合が他コンセプトと完全重複（言い換え量産の疑い）")
        seen_sets.append(fs)
        if e.get("status") == "done":
            kp = os.path.join(ROOT, kdir or "", os.path.basename(f)) if kdir else os.path.join(ROOT, f)
            if not os.path.exists(kp):
                kp2 = os.path.join(ROOT, f)
                if not os.path.exists(kp2):
                    fail(f"{f}: done宣言だが実ファイルなし")
                kp = kp2
            body = open(kp).read()
            if len(body) < 1200:
                fail(f"{f}: done宣言だが本文{len(body)}字 (<1200)")
    done = sum(1 for e in concepts if e.get("status") == "done")
    print(f"check_plan OK: {done}/{len(concepts)} done")
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""draft.md（スライド原稿）の機械ゲート。連番・type語彙・必須キー・image_text比率を検査。"""
import re
import sys

TYPES = {"title", "section", "bullets", "two_column", "table", "code",
         "quote", "image", "image_text", "closing"}
SLIDES_MIN, SLIDES_MAX = 30, 35
IMAGE_TEXT_RATIO_MIN = 0.4


def fail(msg):
    print("NG:", msg)
    sys.exit(1)


def main():
    path = sys.argv[1]
    partial = "--partial" in sys.argv
    try:
        text = open(path).read()
    except FileNotFoundError:
        if partial:
            print("draft未作成（初回ラン）")
            sys.exit(0)
        fail("draft.mdが存在しない")
    headers = re.findall(r"^## SLIDE (\d+) \| type: ([a-z_]+)(?: \| side: (\w+))?\s*$", text, re.M)
    if not headers:
        if partial:
            print("ブロック0件（作成中）")
            sys.exit(0)
        fail("SLIDEブロックが1件もない")
    nums = [int(h[0]) for h in headers]
    if len(nums) != len(set(nums)):
        fail(f"スライド番号重複: {sorted(set(n for n in nums if nums.count(n) > 1))}")
    if nums != sorted(nums):
        fail("スライド番号が昇順でない")
    if nums[0] != 1 or nums != list(range(1, len(nums) + 1)):
        fail(f"連番が1..Nでない: {nums[:5]}...{nums[-3:]}")
    for n, t, _ in headers:
        if t not in TYPES:
            fail(f"SLIDE {n}: type語彙違反 '{t}'")
    blocks = re.split(r"^## SLIDE ", text, flags=re.M)[1:]
    n_it = 0
    for blk, (n, t, side) in zip(blocks, headers):
        has = {k: bool(re.search(rf"^- {k}:", blk, re.M)) for k in
               ("title", "punch", "bullets", "figure", "caption", "notes")}
        if t not in ("quote",) and not has["title"]:
            fail(f"SLIDE {n}: - title: がない")
        if not has["notes"]:
            fail(f"SLIDE {n}: - notes: がない")
        if t == "image_text":
            n_it += 1
            for k in ("punch", "figure", "caption"):
                if not has[k]:
                    fail(f"SLIDE {n} (image_text): - {k}: がない")
    if not partial:
        if not (SLIDES_MIN <= len(headers) <= SLIDES_MAX):
            fail(f"枚数 {len(headers)} (期待 {SLIDES_MIN}〜{SLIDES_MAX})")
        ratio = n_it / len(headers)
        if ratio < IMAGE_TEXT_RATIO_MIN:
            fail(f"image_text比率 {ratio:.2f} (<{IMAGE_TEXT_RATIO_MIN})")
    print(f"check_draft OK: {len(headers)}枚 (image_text {n_it})" + (" [partial]" if partial else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()

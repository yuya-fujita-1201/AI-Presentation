#!/usr/bin/env python3
"""「文言不変」ゲート: draft.md と deck.json の title/punch/caption/notes/bullets を正規化比較。
Sonnet変換の勝手な文言改変・省略はrubric正確性を静かに壊す主経路（T-MAX R3）。"""
import json
import re
import sys


def norm(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s))


def flatten_bullets(bullets):
    out = []
    for b in bullets or []:
        if isinstance(b, str):
            out.append(b)
        elif isinstance(b, dict):
            out.append(b.get("text", ""))
            out.extend(b.get("children", []) or [])
    return norm("".join(out))


def parse_draft(path):
    text = open(path).read()
    blocks = []
    for m in re.finditer(r"^## SLIDE (\d+) \| type: ([a-z_]+)(?: \| side: (\w+))?\s*$", text, re.M):
        blocks.append({"n": int(m.group(1)), "type": m.group(2), "start": m.end()})
    for i, b in enumerate(blocks):
        end = blocks[i + 1]["start"] - 30 if i + 1 < len(blocks) else len(text)
        seg = text[b["start"]:end]
        b["fields"] = {}
        for key in ("title", "punch", "caption"):
            m = re.search(rf"^- {key}:\s*(.*)$", seg, re.M)
            if m:
                b["fields"][key] = m.group(1).strip()
        bl = re.search(r"^- bullets:\n((?:\s+- .*\n?)+)", seg, re.M)
        if bl:
            items = re.findall(r"^\s+- (.*)$", bl.group(1), re.M)
            b["fields"]["bullets"] = norm("".join(items))
    return blocks


def main():
    draft_f, deck_f = sys.argv[1], sys.argv[2]
    blocks = parse_draft(draft_f)
    deck = json.load(open(deck_f))
    slides = deck.get("slides", [])
    if len(blocks) != len(slides):
        print(f"NG: 枚数不一致 draft={len(blocks)} deck={len(slides)}")
        sys.exit(1)
    errors = []
    for b, s in zip(blocks, slides):
        n = b["n"]
        if s.get("type") != b["type"]:
            errors.append(f"SLIDE {n}: type {b['type']}→{s.get('type')}")
            continue
        for key in ("title", "punch", "caption"):
            if key in b["fields"]:
                if norm(b["fields"][key]) != norm(s.get(key)):
                    errors.append(f"SLIDE {n}: {key} 文言変更")
        if "bullets" in b["fields"]:
            deck_b = flatten_bullets(s.get("bullets"))
            if b["fields"]["bullets"] != deck_b:
                errors.append(f"SLIDE {n}: bullets 文言/順序変更")
    if errors:
        print("NG: 文言不変違反", len(errors), "件")
        for e in errors[:10]:
            print(" ", e)
        sys.exit(1)
    print(f"check_deck_text OK: {len(slides)}枚 文言一致")
    sys.exit(0)


if __name__ == "__main__":
    main()

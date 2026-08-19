#!/usr/bin/env python3
"""デッキ文言の機械リント（loop-learnings.md §3 の「機械ゲートに昇格すべきもの」の文言系）。

不合格（exit 1）:
  - closing.title が 22 字超（固定 72px 枠で 2 行化→罫線貫通の事故）
  - Markdown 記法の残留（**強調** / `code` / 行頭 # ）が表示フィールドにある
  - 「N枚目」「Nページ目」直書きが総枚数を超える、または存在しないスライドを指す
警告（件数と箇所を表示。exit に影響しない。rubric の減点材料）:
  - punch が --punch-max 字超（既定80＝正本01の最大。01/02 も2行折り返しが常態なので長さ自体は問題にしない）
  - AI 定型句（rubric-ai-eng-tone の一覧）の出現箇所
  - 「AではなくB」型（「ではなく」）、全角ダッシュ「——」、丸数字①②③ の出現回数
  - 半角コロン「:」と全角コロン「：」の混在（日本語文中の半角コロン）
  - 表示テキスト中の英字のみラベル（図の英語ラベルの検出は SVG 側を別途）

使い方: python3 tools/lint_deck_text.py decks/<deck> [--json out.json] [--punch-max 35]
対象フィールド: title / punch / lead / caption / message / bullets / rows / columns の文字列（notes・code は対象外）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AI_PHRASES = ["することができます", "と言えるでしょう", "重要な要素", "効果的に", "を実現", "最適化", "において",
              "に留意", "シームレス", "性を高める", "本資料では", "つまり、", "ということです", "言い換えれば",
              "さらに重要なのは", "鍵となる", "カギとなる", "真価を発揮", "飛躍的に"]
DISPLAY_KEYS = ("title", "punch", "lead", "caption", "message", "subtitle", "eyebrow", "heading", "quote", "attribution", "label")


def iter_texts(slide):
    """表示テキストを (field_path, text) で列挙する（notes は除外）"""
    def walk(obj, path):
        if isinstance(obj, str):
            yield path, obj
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from walk(v, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("notes", "style", "figure", "path", "src", "image", "type", "id", "layout", "theme", "code"):
                    continue
                yield from walk(v, f"{path}.{k}" if path else k)
    yield from walk(slide, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_dir")
    ap.add_argument("--json")
    ap.add_argument("--punch-max", type=int, default=80, help="正本01の最大値80で較正。2行折り返しは01でも常態なので長さ自体は減点しない")
    ap.add_argument("--closing-max", type=int, default=22)
    args = ap.parse_args()
    deck = json.loads((Path(args.deck_dir) / "deck.json").read_text(encoding="utf-8"))
    slides = deck.get("slides", [])
    total = len(slides)
    errors, warns = [], []
    stats = {"punch_total": 0, "punch_over": 0, "dewanaku": 0, "dash": 0, "circled": 0, "ai_phrase": 0,
             "half_colon": 0, "full_colon": 0}
    for i, s in enumerate(slides, 1):
        sid = f"slide-{i:02d}"
        t = s.get("type")
        if t == "closing" and len(str(s.get("title", ""))) > args.closing_max:
            errors.append(f"{sid} closing.title {len(s['title'])}字 > {args.closing_max}字: 「{s['title']}」")
        if s.get("punch"):
            stats["punch_total"] += 1
            if len(s["punch"]) > args.punch_max:
                stats["punch_over"] += 1
                warns.append(f"{sid} punch {len(s['punch'])}字 > {args.punch_max}: 「{s['punch'][:30]}…」")
        for path, text in iter_texts(s):
            if re.search(r"\*\*[^*]+\*\*|(?<!`)`[^`]+`|^#{1,6}\s", text):
                errors.append(f"{sid} {path} Markdown記法残留: 「{text[:40]}」")
            for m in re.finditer(r"(\d+)\s*(枚目|ページ目|ページ)", text):
                n = int(m.group(1))
                if n > total:
                    errors.append(f"{sid} {path} 「{m.group(0)}」が総枚数{total}を超過")
                else:
                    warns.append(f"{sid} {path} ページ番号直書き「{m.group(0)}」（付録追加でずれる。実体: {slides[n-1].get('title','')[:20]}）")
            for ph in AI_PHRASES:
                c = text.count(ph)
                if c:
                    stats["ai_phrase"] += c
                    warns.append(f"{sid} {path} AI定型句「{ph}」×{c}: 「{text[:40]}」")
            stats["dewanaku"] += text.count("ではなく")
            stats["dash"] += text.count("——") + text.count("—")
            stats["circled"] += len(re.findall(r"[①-⑳]", text))
            # 日本語文中の半角コロン（URL・時刻を除く）
            if re.search(r"[぀-ヿ一-鿿]\s*:\s*[぀-ヿ一-鿿]", text) and not re.search(r"https?:", text):
                stats["half_colon"] += 1
                warns.append(f"{sid} {path} 日本語文中の半角コロン: 「{text[:40]}」")
            stats["full_colon"] += text.count("：")
    # 「ではなく」等は件数を1行で
    warns.append(f"[集計] 「ではなく」{stats['dewanaku']}回 / ダッシュ{stats['dash']}回 / 丸数字{stats['circled']}個 / "
                 f"AI定型句{stats['ai_phrase']}箇所 / punch {stats['punch_over']}/{stats['punch_total']}枚が{args.punch_max}字超 / "
                 f"半角コロン混在{stats['half_colon']}箇所（全角：{stats['full_colon']}回）")
    out = {"deck": args.deck_dir, "slides": total, "errors": errors, "warnings": warns, "stats": stats}
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for e in errors:
        print("NG:", e)
    for w in warns:
        print("warn:", w)
    print(f"lint_deck_text: {total}枚 不合格{len(errors)}件 / 警告{len(warns) - 1}件")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

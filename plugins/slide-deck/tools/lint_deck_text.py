#!/usr/bin/env python3
"""デッキ文言の機械リント（AI定型句・文字量・記法崩れの回帰チェック）。

不合格（exit 1）:
  - closing.title が 22 字超（固定 72px 枠で 2 行化→罫線貫通の事故）
  - Markdown 記法の残留（**強調** / `code` / 行頭 # ）が表示フィールドにある
  - 「N枚目」「Nページ目」直書きが総枚数を超える、または存在しないスライドを指す
  - AI 定型句（単独では使われない特徴的な言い回し）が表示フィールドに 1 件でもある
警告（件数と箇所を表示。exit に影響しない。rubric の減点材料）:
  - 「最適化」「において」等、それ単独では一般的なビジネス語彙でもあるため警告止まりの語
  - punch が --punch-max 字超（既定80）
  - 「AではなくB」型（「ではなく」）、全角ダッシュ「——」、丸数字①②③ の出現回数
  - 半角コロン「:」と全角コロン「：」の混在（日本語文中の半角コロン）
  - 表示テキスト中の英字のみラベル（図の英語ラベルの検出は SVG 側を別途）

使い方: python tools/lint_deck_text.py <deck_dir> [--json out.json] [--punch-max 35]
対象フィールド: title / punch / lead / caption / message / bullets / rows / columns の文字列（notes・code は対象外）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
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

# 単独でもAIが多用しがちな特徴的フレーズ（複合語）。表示フィールドに出たら不合格。
AI_PHRASES = ["することができます", "と言えるでしょう", "重要な要素", "効果的に", "を実現",
              "に留意", "シームレス", "性を高める", "本資料では", "ということです", "言い換えれば",
              "さらに重要なのは", "鍵となる", "カギとなる", "真価を発揮", "飛躍的に"]
# それ単独では一般的なビジネス語彙でもある語（「価格最適化」「〜においては」等の正当な用法がある）。
# AI定型句リストに含めたい気持ちは分かるが、hard errorにすると誤検知するため警告止まりにする。
AI_PHRASES_SOFT = ["最適化", "において"]
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
    setup_console()
    ap = argparse.ArgumentParser(description="デッキ文言の機械リント")
    ap.add_argument("deck_dir")
    ap.add_argument("--json")
    ap.add_argument("--punch-max", type=int, default=80, help="punch文字数の警告しきい値（既定80）")
    ap.add_argument("--closing-max", type=int, default=22)
    args = ap.parse_args()
    deck_json = Path(args.deck_dir) / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    slides = deck.get("slides", [])
    total = len(slides)
    errors, warns = [], []
    stats = {"punch_total": 0, "punch_over": 0, "dewanaku": 0, "dash": 0, "circled": 0, "ai_phrase": 0,
             "ai_phrase_soft": 0, "half_colon": 0, "full_colon": 0}
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
                    errors.append(f"{sid} {path} AI定型句「{ph}」×{c}: 「{text[:40]}」")
            for ph in AI_PHRASES_SOFT:
                c = text.count(ph)
                if c:
                    stats["ai_phrase_soft"] += c
                    warns.append(f"{sid} {path} 一般語「{ph}」×{c}（文脈次第。AI定型句と紛らわしければ言い換え検討）: 「{text[:40]}」")
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
                 f"AI定型句{stats['ai_phrase']}箇所 / 一般語(要確認){stats['ai_phrase_soft']}箇所 / "
                 f"punch {stats['punch_over']}/{stats['punch_total']}枚が{args.punch_max}字超 / "
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

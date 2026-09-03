#!/usr/bin/env python3
"""複数デッキの文章・構成の定量指標を横並びで比較する（文体・情報量の一貫性チェック用）。

使い方: python tools/deck_metrics.py <deck_dir> [<deck_dir> ...] [--json out.json]
指標（表示テキストは notes/code を除く）:
  枚数 / type 構成 / 導入4枚の type 列 / 章扉数
  punch: 枚数・中央値字数・です・ます終止率
  bullets: 1枚あたり本数・1本あたり字数・文末が「。」の率・体言止め率（名詞/記号終わり）
  notes: 平均字数・言い淀み語の出現数（だと思います／正直／んです／かなと／かもしれません／迷い）・文末の種類数
  語彙: 「ではなく」回数 / ダッシュ / カタカナ語(4字以上)の異なり数 / 英字語の異なり数 / 初出で（ ）説明がある割合（概算）
  図: 図版つきスライド率 / image_text 枚数 / caption 枚数 / table 枚数 / code 枚数
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
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

HEDGE = ["だと思います", "正直", "んです", "かなと", "かもしれません", "迷い", "と思っています", "気がします", "ですね"]
DESU = re.compile(r"(です|ます|ましょう|ません|でした|ますか|でしょうか|ですか)[。！？]?$")


def display_texts(slide):
    out = []
    def walk(o):
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("notes", "style", "figure", "path", "src", "image", "type", "id", "layout", "theme", "code"):
                    continue
                walk(v)
    walk(slide)
    return out


def bullet_texts(slide):
    res = []
    def grab(items):
        for b in items or []:
            if isinstance(b, str):
                res.append(b)
            elif isinstance(b, dict):
                if b.get("text"):
                    res.append(b["text"])
                grab(b.get("children"))
    grab(slide.get("bullets"))
    cols = slide.get("columns")
    # cards/table では columns が列数(int)や見出し文字列のリストであり、
    # two_column の列オブジェクト配列と型が違うのでここでは無視する。
    if isinstance(cols, list):
        for c in cols:
            if isinstance(c, dict):
                grab(c.get("bullets"))
    return res


def metrics(deck_dir):
    deck_json = Path(deck_dir) / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    slides = deck["slides"]
    n = len(slides)
    types = [s.get("type") for s in slides]
    m = {"deck": Path(deck_dir).name, "slides": n,
         "intro": ">".join(types[:4]), "sections": types.count("section"),
         "types": {t: types.count(t) for t in sorted(set(types))}}
    punches = [s["punch"] for s in slides if s.get("punch")]
    m["punch_n"] = len(punches)
    m["punch_med"] = int(st.median(len(p) for p in punches)) if punches else 0
    m["punch_desu"] = round(sum(1 for p in punches if DESU.search(p)) / len(punches), 2) if punches else None
    bl = [b for s in slides for b in bullet_texts(s)]
    bslides = [s for s in slides if bullet_texts(s)]
    m["bullets_per_slide"] = round(len(bl) / len(bslides), 1) if bslides else 0
    m["bullet_chars"] = int(st.median(len(b) for b in bl)) if bl else 0
    m["bullet_end_maru"] = round(sum(1 for b in bl if b.rstrip().endswith("。")) / len(bl), 2) if bl else None
    noun_end = re.compile(r"[ぁ-んァ-ヶ一-龥A-Za-z0-9）」）]$")
    verb_end = re.compile(r"(る|い|う|す|く|た|だ|ない|です|ます|ません|ましょう|か|ね|よ)[。]?$")
    m["bullet_taigen"] = round(sum(1 for b in bl if not verb_end.search(b.rstrip("。")) ) / len(bl), 2) if bl else None
    notes = [s.get("notes", "") for s in slides if s.get("notes")]
    m["notes_n"] = len(notes)
    m["notes_chars"] = int(st.median(len(x) for x in notes)) if notes else 0
    m["notes_hedge"] = sum(x.count(h) for x in notes for h in HEDGE)
    ends = [re.sub(r"[。！？\s]+$", "", sent)[-3:] for x in notes for sent in re.split(r"[。！？]", x) if sent.strip()]
    m["notes_end_variety"] = round(len(set(ends)) / len(ends), 2) if ends else None
    disp = [t for s in slides for t in display_texts(s)]
    alltext = "\n".join(disp)
    m["dewanaku"] = alltext.count("ではなく")
    m["dash"] = alltext.count("—")
    kata = set(re.findall(r"[ァ-ヶー]{4,}", alltext))
    eng = set(w for w in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", alltext) if not re.fullmatch(r"\d+", w))
    m["katakana_terms"] = len(kata)
    m["english_terms"] = len(eng)
    # 初出に（ ）説明があるか（概算）: 用語の最初の出現の直後に「（」が続く割合
    explained = 0
    for term in kata | eng:
        i = alltext.find(term)
        if i >= 0 and alltext[i + len(term): i + len(term) + 1] in ("（", "("):
            explained += 1
    m["terms_explained_ratio"] = round(explained / len(kata | eng), 2) if (kata | eng) else None
    m["chars_per_slide"] = int(len(alltext) / n)
    fig_slides = sum(1 for s in slides if json.dumps(s, ensure_ascii=False).find("assets/") >= 0)
    m["figure_slide_ratio"] = round(fig_slides / n, 2)
    m["image_text"] = types.count("image_text")
    m["caption_n"] = sum(1 for s in slides if s.get("caption"))
    m["table_n"] = types.count("table")
    m["code_n"] = types.count("code")
    m["two_column_n"] = types.count("two_column")
    m["quote_n"] = types.count("quote")
    return m


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="複数デッキの文章・構成の定量指標を横並びで比較する")
    ap.add_argument("decks", nargs="+", help="比較する deck_dir（2つ以上を指定すると横並び表示）")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [metrics(d) for d in args.decks]
    keys = ["slides", "sections", "intro", "punch_n", "punch_med", "punch_desu", "bullets_per_slide", "bullet_chars",
            "bullet_end_maru", "bullet_taigen", "notes_n", "notes_chars", "notes_hedge", "notes_end_variety",
            "dewanaku", "dash", "katakana_terms", "english_terms", "terms_explained_ratio", "chars_per_slide",
            "figure_slide_ratio", "image_text", "caption_n", "table_n", "code_n", "two_column_n", "quote_n"]
    print("| 指標 | " + " | ".join(r["deck"][:2] for r in rows) + " |")
    print("|---|" + "---|" * len(rows))
    for k in keys:
        print(f"| {k} | " + " | ".join(str(r.get(k)) for r in rows) + " |")
    print("| types | " + " | ".join(",".join(f"{t}:{c}" for t, c in r["types"].items()) for r in rows) + " |")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

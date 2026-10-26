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

# --- 主張（タイトル・リード・パンチライン・メッセージ）の書き方 ---------------------------
CLAIM_KEYS = ("title", "lead", "punch", "message", "conclusion")
# 言い切りを弱める曖昧語
VAGUE_WORDS = ["など", "様々", "さまざま", "適切に", "適切な", "効果的", "各種", "柔軟に", "一定の", "幅広く", "多角的"]
# 構成の説明（主張ではなく「何がどこにあるか」を書いている）
LAYOUT_DESC = re.compile(r"左側?に|右側?に|上側?に|下側?に|[左右上下]図|[上下]表|以下の通り|次の通り|下記の通り|本スライド|このスライド")
# 文の終わりとみなす文字（これ以外の漢字・カタカナ・英数字で終わるリードは体言止め）
SENTENCE_END = set("。！？!?」』）)…")
# 曖昧な表の列名
VAGUE_COLUMNS = {"概要", "備考", "その他", "詳細", "内容"}
# 評価記号（凡例が無いと読み手が意味を取れない。× は掛け算・組み合わせにも使うので対象外）
RATING_MARKS = re.compile(r"[◎○△]")
RATING_LEGEND = re.compile(r"凡例|[◎○△]\s*[:：=＝]")
# 和文と英数字の間の半角空白（コード・URL らしいものは除く）
JA = "぀-ヿ一-鿿々"
JA_SPACE = re.compile(rf"[{JA}] +[A-Za-z0-9]|[A-Za-z0-9%] +[{JA}]")
CODE_LIKE = re.compile(r"[{}();=<>$`\\]|://")
# 桁区切りの無い 4 桁以上の数（西暦 1900〜2100・型番・バージョン・時刻・ファイル名は除く）
BIG_NUMBER = re.compile(r"(?<![A-Za-z0-9_.,/:#\-×*])(\d{4,})(?![A-Za-z0-9_.,/:\-×*])")

# --- relation（内容の関係）とスライドタイプの対応 -------------------------------------
RELATION_TYPES = {
    "parallel": ["cards", "bullets", "two_column", "table", "matrix", "image_text", "status_table", "summary",
                 "row_matrix", "house"],
    "sequence": ["steps", "swimlane", "schedule", "sequence", "dataflow", "agenda", "row_matrix"],
    "flow": ["dataflow", "swimlane", "steps", "sequence", "architecture"],
    "hierarchy": ["architecture", "bullets", "table", "org", "house", "kpi_tree"],
    "cause": ["steps", "dataflow", "two_column", "bullets", "reasons"],
    "contrast": ["two_column", "table", "matrix", "status_table", "reasons", "row_matrix"],
    "cycle": ["lifecycle", "cycle"],
}
# 順序を表す見出し（cards の見出しがこれで始まるなら steps の方が合う）
ORDERED_HEADING = re.compile(r"^\s*(STEP|Step|step|PHASE|Phase|phase|フェーズ|ステップ|第\s*\d|\d+\s*[.．)）:：]|[①-⑳])")
# 同じタイプが続いても単調にならないタイプ
RHYTHM_EXEMPT = {"section", "agenda", "title", "closing", "swimlane_legend", "diagram_legend", "canvas", "statement"}
RHYTHM_RUN = 3

# --- 日付の整合 ---------------------------------------------------------------------
YM = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$")
TEXT_DATE = re.compile(r"(20\d\d)\s*(?:年\s*(\d{1,2})\s*月|[/\-.](\d{1,2})(?!\d))")
TEXT_YEAR = re.compile(r"(20\d\d)\s*年(?!\s*\d{1,2}\s*月)(?!度)")
ACHIEVED = re.compile(r"実績|達成|完了|導入済|導入した|稼働した|削減した|改善した|獲得した|事例")


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


def _bigrams(text: str) -> set:
    """記号・空白を除いた文字 2-gram の集合（日本語でも形態素解析なしで重なりを測れる）。"""
    s = re.sub(r"[\s、。，．・：:；;！!？?「」『』（）()\[\]【】\-—–/]", "", str(text or ""))
    return {s[k:k + 2] for k in range(len(s) - 1)}


def overlap(a: str, b: str) -> float:
    """a の 2-gram のうち b にも含まれる割合（0〜1）。"""
    ba = _bigrams(a)
    return len(ba & _bigrams(b)) / len(ba) if ba else 0.0


def _item_texts(items):
    for it in items or []:
        if isinstance(it, str):
            yield it
        elif isinstance(it, dict):
            if isinstance(it.get("text"), str):
                yield it["text"]
            yield from _item_texts(it.get("children"))


def parse_ym(value):
    """"YYYY-MM" / "YYYY-MM-DD" を (年, 月, 日) にする。読めなければ None。"""
    m = YM.match(str(value or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
    return (y, mo, d) if 1 <= mo <= 12 else None


def _months(ymd) -> int:
    return ymd[0] * 12 + ymd[1]


def check_claims(sid: str, s: dict) -> list:
    """タイトル・リードなど主張の書き方（曖昧語・構成の説明・体言止め・言い直し）。"""
    out = []
    for key in CLAIM_KEYS:
        text = s.get(key)
        if not isinstance(text, str) or not text.strip():
            continue
        vague = [w for w in VAGUE_WORDS if w in text]
        if vague:
            out.append(f"{sid} {key} 曖昧語「{'」「'.join(vague)}」（具体的な数字・対象に言い換える）: 「{text[:40]}」")
        m = LAYOUT_DESC.search(text)
        if m and (key != "title" or m.group(0) in ("本スライド", "このスライド")):
            out.append(f"{sid} {key} 構成の説明「{m.group(0)}」（何がどこにあるかではなく主張を書く）: 「{text[:40]}」")
    for key in ("lead", "punch", "message"):
        text = s.get(key)
        if isinstance(text, str) and len(text.strip()) >= 15:
            last = text.strip()[-1]
            if last not in SENTENCE_END and re.match(rf"[{JA}A-Za-z0-9]", last) and not re.match(r"[ぁ-ゖ]", last):
                out.append(f"{sid} {key} 体言止め（主語と述語のある文にすると結論が伝わる）: 「…{text.strip()[-20:]}」")
    title, lead = s.get("title"), s.get("lead")
    if isinstance(title, str) and isinstance(lead, str) and len(_bigrams(title)) >= 5:
        r = overlap(title, lead)
        if r >= 0.8:
            out.append(f"{sid} lead がタイトルの言い直し（2-gram 重複 {r:.0%}。リードには根拠か手段を書く）")
    if isinstance(lead, str) and len(_bigrams(lead)) >= 8:
        for t in _item_texts(s.get("bullets")):
            if len(_bigrams(t)) >= 8 and overlap(t, lead) >= 0.6:
                out.append(f"{sid} bullets がリードの言い直し（本文には根拠・事例を書く）: 「{t[:30]}」")
                break
    return out


def check_tables(sid: str, s: dict, texts: list) -> list:
    """表の列名・評価記号の凡例。"""
    out = []
    cols = s.get("columns") if s.get("type") in ("table", "status_table") else None
    for c in cols if isinstance(cols, list) else []:
        name = c.get("text") if isinstance(c, dict) else c
        if isinstance(name, str) and name.strip() in VAGUE_COLUMNS:
            out.append(f"{sid} columns 曖昧な列名「{name}」（何が入る列かを具体的に書く）")
    body = " ".join(t for p, t in texts if p.startswith(("rows", "quadrants", "cards", "cells")))
    if len(RATING_MARKS.findall(body)) >= 2 and not RATING_LEGEND.search(" ".join(t for _, t in texts)):
        out.append(f"{sid} ◎○△ を使っているが凡例が無い（lead か caption に「◎=…」を書く）")
    return out


def check_numbers(sid: str, path: str, text: str) -> list:
    out = []
    for m in BIG_NUMBER.finditer(text):
        n = m.group(1)
        if len(n) == 4 and 1900 <= int(n) <= 2100:
            continue
        out.append(f"{sid} {path} 桁区切りの無い数「{n}」（{int(n):,} のように書く）")
    return out


def check_relation(sid: str, s: dict) -> list:
    """relation（内容の関係）とタイプが合っているか。relation が無くても cards の順序見出しは検出する。"""
    t = s.get("type")
    rel = s.get("relation")
    out = []
    if rel is not None:
        if rel not in RELATION_TYPES:
            out.append(f"{sid} relation「{rel}」は未知の値（{' / '.join(RELATION_TYPES)}）")
        elif t not in RELATION_TYPES[rel]:
            out.append(f"{sid} relation={rel} に type={t} は合わない（候補: {' / '.join(RELATION_TYPES[rel])}）")
    elif t == "cards":
        heads = [c.get("heading", "") for c in s.get("cards") or [] if isinstance(c, dict)]
        if sum(1 for h in heads if ORDERED_HEADING.match(str(h))) >= 2:
            out.append(f"{sid} cards の見出しが順序（STEP・番号）を表している。順番があるなら steps、並列なら番号を外す")
    return out


def check_rhythm(slides: list) -> list:
    """同じタイプが RHYTHM_RUN 枚以上続く箇所（単調に見える）。"""
    out, k = [], 0
    while k < len(slides):
        t = slides[k].get("type")
        j = k
        while j + 1 < len(slides) and slides[j + 1].get("type") == t:
            j += 1
        if t not in RHYTHM_EXEMPT and j - k + 1 >= RHYTHM_RUN:
            out.append(f"slide-{k + 1:02d}〜slide-{j + 1:02d} type={t} が{j - k + 1}枚続く（構図が単調。"
                       f"1枚を表・図解・2カラムなどに変えると流れが付く）")
        k = j + 1
    return out


def resolve_as_of(meta: dict, today=None):
    """日付チェックの基準日。meta.as_of → meta.date → 今日 の順に使う。(基準日, 出どころ) を返す。"""
    for key in ("as_of", "date"):
        ymd = parse_ym(meta.get(key))
        if ymd:
            return ymd, f"meta.{key}"
    import datetime
    d = today or datetime.date.today()
    return (d.year, d.month, d.day), "今日の日付"


def check_dates(slides: list, meta: dict, today=None) -> list:
    """日付の整合: 基準日より後の「実績」、基準日より前に始まる計画、today と基準日のずれ。"""
    as_of, src = resolve_as_of(meta, today)
    label = f"{as_of[0]}-{as_of[1]:02d}（{src}）"
    out = []
    if meta.get("as_of") is not None and parse_ym(meta.get("as_of")) is None:
        out.append(f"meta.as_of「{meta.get('as_of')}」が読めない（\"YYYY-MM\" か \"YYYY-MM-DD\" で書く）")
    for i, s in enumerate(slides, 1):
        sid = f"slide-{i:02d}"
        if s.get("type") == "schedule":
            today_v = parse_ym(s.get("today"))
            if today_v and abs(_months(today_v) - _months(as_of)) > 1:
                out.append(f"{sid} schedule.today（{s.get('today')}）が基準日 {label} と離れている")
            start = parse_ym((s.get("timeline") or {}).get("start"))
            if not today_v and start and _months(start) < _months(as_of):
                out.append(f"{sid} schedule の開始（{s['timeline']['start']}）が基準日 {label} より前"
                           f"（計画なら開始を見直す。進捗報告なら today を書く）")
        for path, text in iter_texts(s):
            if not ACHIEVED.search(text):
                continue
            for m in TEXT_DATE.finditer(text):
                y, mo = int(m.group(1)), int(m.group(2) or m.group(3))
                if 1 <= mo <= 12 and y * 12 + mo > _months(as_of):
                    out.append(f"{sid} {path} 基準日 {label} より後の時期「{m.group(0)}」を実績として書いている")
                    break
            else:
                for m in TEXT_YEAR.finditer(text):
                    if int(m.group(1)) > as_of[0]:
                        out.append(f"{sid} {path} 基準日 {label} より後の年「{m.group(0)}」を実績として書いている")
                        break
    return out


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
             "ai_phrase_soft": 0, "half_colon": 0, "full_colon": 0, "ja_space": 0}
    ja_space_examples = []
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
        texts = list(iter_texts(s))
        warns.extend(check_claims(sid, s))
        warns.extend(check_tables(sid, s, texts))
        warns.extend(check_relation(sid, s))
        for path, text in texts:
            warns.extend(check_numbers(sid, path, text))
            if JA_SPACE.search(text) and not CODE_LIKE.search(text):
                stats["ja_space"] += 1
                if len(ja_space_examples) < 3:
                    ja_space_examples.append(f"{sid} {path}「{text[:30]}」")
        for path, text in texts:
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
    warns.extend(check_rhythm(slides))
    warns.extend(check_dates(slides, deck.get("meta", {})))
    if stats["ja_space"]:
        warns.append(f"和文と英数字の間に半角空白 {stats['ja_space']}箇所（表記を統一するなら詰める。例: "
                     f"{' / '.join(ja_space_examples)}）")
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

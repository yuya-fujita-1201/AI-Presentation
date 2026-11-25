#!/usr/bin/env python3
"""デッキ文言の機械リント（AI定型句・文字量・記法崩れの回帰チェック）。

不合格（exit 1。どの行にも直し方を添える）:
  - closing.title が 22 字超（固定 72px 枠で 2 行化→罫線貫通の事故）
  - Markdown 記法の残留（**強調** / `code` / 行頭 # ）が表示フィールドにある
  - 「N枚目」「Nページ目」「N ページを参照」直書きが総枚数を超える（「全200ページのPDF」「3ページ構成」は対象外）
  - AI 定型句（単独では使われない特徴的な言い回し）が表示フィールドに 1 件でもある
  - --fail-on-todo のとき、【要確認】マーカーが 1 つでも残っている
警告（件数と箇所を表示。exit に影響しない。rubric の減点材料）:
  - 【要確認】/【要確認: 何を確かめるか】マーカー（根拠が無い箇所の目印）。スライド番号・項目つきで一覧にする
  - 「最適化」「において」等、それ単独では一般的なビジネス語彙でもあるため警告止まりの語
  - punch が --punch-max 字超（既定は密度で変わる: talk 50 / standard 80 / read 120）
  - 文字量の目安超え（密度で変わる。bullets の 1 項目の字数・項目数、1 枚の表示文字数）
  - 「AではなくB」型（「ではなく」）、全角ダッシュ「——」、丸数字①②③ の出現回数
  - 半角コロン「:」と全角コロン「：」の混在（日本語文中の半角コロン。出典 source は除く）
  - AI 生成資料の定番パターン（references/content-guide.md 8章）: 0埋めの番号「01」／強調のためのカギカッコ・
    行頭の【】ラベル（【要確認】は除く）／兄弟の項目で同じラベルの繰り返し／「論点」なのに問いでないタイトル・
    共有と判断依頼の盛り合わせタイトル／定型の免責文・改行の無い長い注釈

meta.density（"talk" / "standard" / "read"。未指定は standard）で文字量の目安を切り替える。
talk は話す用で厳しめ、read は読ませる用で緩め。--punch-max を明示したときはそれを優先する。

使い方: python tools/lint_deck_text.py <deck_dir> [--json out.json] [--punch-max 35] [--fail-on-todo]
対象フィールド: 表示される文字列（title / punch / lead / caption / message / bullets / rows / columns …）。
notes・code・アイコン名や形の指定（icon / variant / shape など）は対象外。【要確認】の数え上げだけは notes も見る。
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
# 表示されない文字列（アイコン名・図形の種類・配置・色・ノード ID の参照など）を持つキー。本文として検査しない
NON_DISPLAY_KEYS = ("icon", "variant", "shape", "kind", "align", "valign", "relation", "tone", "mode", "direction",
                    "orientation", "position", "lane", "from", "to", "color", "fill", "bg", "pattern",
                    "background", "overlay", "side", "fit", "caption_position", "emphasis")
# 密度（meta.density）ごとの文字量の目安。talk=話す用（大きく少なく）/ standard=既定 / read=読ませる用（小さめ・密）
DENSITY_LIMITS = {
    "talk": {"punch": 50, "bullet_chars": 30, "bullets": 5, "slide_chars": 250},
    "standard": {"punch": 80, "bullet_chars": 40, "bullets": 6, "slide_chars": 500},
    "read": {"punch": 120, "bullet_chars": 60, "bullets": 8, "slide_chars": 800},
}
DEFAULT_DENSITY = "standard"
# 文字量（1 枚の表示文字数）を数えないタイプ（表紙・章扉・目次などは内容量の指標にならない）
VOLUME_EXEMPT = {"title", "section", "agenda", "closing", "swimlane_legend", "diagram_legend", "canvas", "statement", "quote", "schedule"}   # schedule: 行・凡例・月の目盛りが表の形で並ぶので 1 枚の字数では測らない（S5b）
# 【要確認】/【要確認: 何を確かめるか】（根拠が無い箇所の目印。全角・半角コロンどちらも可）
TODO_MARK = re.compile(r"【要確認(?:\s*[:：]\s*([^】]*))?】")

# --- 主張（タイトル・リード・パンチライン・メッセージ）の書き方 ---------------------------
CLAIM_KEYS = ("title", "lead", "punch", "message", "conclusion")
# 言い切りを弱める曖昧語
VAGUE_WORDS = ["など", "様々", "さまざま", "適切に", "適切な", "効果的", "各種", "柔軟に", "一定の", "幅広く", "多角的"]
# 構成の説明（主張ではなく「何がどこにあるか」を書いている）
# 「下に」は位置の説明のとき（「図の下に」）だけ。数量・比較のあと（「半分以下にしたい」「3 割未満に」「2 倍以下に」）は除く
LAYOUT_DESC = re.compile(r"左側?に|右側?に|上側?に|(?<![以未割分倍％%度])下側?に|[左右上下]図|[上下]表|以下の通り|次の通り|下記の通り|本スライド|このスライド")
# 文の終わりとみなす文字（これ以外の漢字・カタカナ・英数字で終わるリードは体言止め）
SENTENCE_END = set("。！？!?」』）)…")
# 曖昧な表の列名
VAGUE_COLUMNS = {"概要", "備考", "その他", "詳細", "内容"}
# 評価記号（凡例が無いと読み手が意味を取れない。× は掛け算・組み合わせにも使うので対象外）
RATING_MARKS = re.compile(r"[◎○△]")
RATING_LEGEND = re.compile(r"凡例|[◎○△]\s*[:：=＝]")
# 和文と英数字の間の半角空白（コード・URL らしいものは除く）。
# 警告にするのは「同じ文字列の中で、空白のある所と無い所が混ざっている」ときだけ（「AI 活用の3か月」）。
# 空白をそろえて入れている / 全部詰めている文書は、どちらも正しい書き方なので警告しない（確認用デッキ・見本は空白入りで統一している）
JA = "぀-ヿ一-鿿々"
JA_SPACE = re.compile(rf"[{JA}] +[A-Za-z0-9]|[A-Za-z0-9%] +[{JA}]")
JA_TIGHT = re.compile(rf"[{JA}][A-Za-z0-9]|[A-Za-z0-9%][{JA}]")
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


def _spec(t):
    """登録表（engine_registry）のタイプ定義。kpi / chart など A 型タイプの検査用の性質（text_skip_keys など）を引く。"""
    try:
        import engine_registry
        return engine_registry.get(t)
    except Exception:       # pragma: no cover
        return None


def relation_table() -> dict:
    """relation → タイプの表。固定の RELATION_TYPES に、登録表で relation を宣言したタイプを足したもの。"""
    out = {k: list(v) for k, v in RELATION_TYPES.items()}
    try:
        import engine_registry
        for rel, types in engine_registry.relation_types().items():
            for t in types:
                if t not in out.setdefault(rel, []):
                    out[rel].append(t)
    except Exception:       # pragma: no cover
        pass
    return out


def iter_texts(slide):
    """表示テキストを (field_path, text) で列挙する（notes は除外）"""
    spec = _spec(slide.get("type")) if isinstance(slide, dict) else None
    extra_skip = tuple(spec.text_skip_keys) if spec else ()
    def walk(obj, path):
        if isinstance(obj, str):
            yield path, obj
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from walk(v, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("notes", "style", "figure", "path", "src", "image", "type", "id", "layout", "theme", "code") + NON_DISPLAY_KEYS + extra_skip:
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
    spec = _spec(s.get("type"))
    for key in CLAIM_KEYS + (tuple(spec.claim_keys) if spec else ()):
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


# --- AI 生成資料に見える定番パターン（references/content-guide.md 8章） ---------------------
# 番号の 0 埋め（「01」「02」）。number / step などの番号フィールドと、見出しの先頭の番号
ZERO_PAD_KEYS = ("number", "step", "num", "badge")
ZERO_PAD = re.compile(r"^\s*0\d(?!\d)")
# 強調のためだけのカギカッコ（短い語を「」で囲む）と、行頭の【】ラベル
EMPH_BRACKET = re.compile(r"「([^「」]{1,12})」(?!\s*と(?:聞|言|い|頼|書|入力|伝|話|打))")   # 「〜」と聞く・と言う は引用なので対象外
LABEL_BRACKET = re.compile(r"^\s*【(?!要確認)[^】]{1,12}】")   # 【要確認】マーカーは対象外
EMPH_KEYS = CLAIM_KEYS + ("heading", "label", "kicker", "subtitle", "eyebrow")
# 見出し・ラベルの区切り（「リスク：形骸化」「ご判断｜範囲」「リスク 形骸化」）
LABEL_SEP = re.compile(r"[：:｜|／/　 ]")
LABEL_KEYS = ("heading", "label", "title", "eyebrow", "kicker", "tag")
# タイトルが「共有」と「判断依頼」を1枚に盛っている
SHARE_WORDS = re.compile(r"方針|現状|状況|概要|報告|共有|結果|進捗|全体像|計画")
ASK_WORDS = re.compile(r"判断|承認|決定|決裁|ご相談|お願い|依頼")
# 読まれない定型の免責注釈
DISCLAIMER_PHRASES = ["保証するものではありません", "保証するものではない", "前提としております", "一般的な傾向",
                      "変更となる可能性", "個別の状況により", "貴社にて実施", "あくまで目安"]
NOTE_KEYS = ("source", "caption", "note", "footnote", "disclaimer")
NOTE_MAX = 100


def _label_nodes(obj, path=""):
    """slide 内の「辞書のリスト」（cards / steps / items 等）を (path, [辞書…]) で列挙する。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("notes", "style", "rows", "columns", "cells"):
                continue
            yield from _label_nodes(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        dicts = [v for v in obj if isinstance(v, dict)]
        if len(dicts) >= 2:
            yield path, dicts
        for i, v in enumerate(obj):
            yield from _label_nodes(v, f"{path}[{i}]")


def check_ai_look(sid: str, s: dict, texts: list) -> list:
    """AI 生成資料の定番パターン（0 埋め番号・強調カギカッコ・同じラベルの繰り返し・
    共有と判断の盛り合わせタイトル・読まれない長い注釈）。いずれも警告。"""
    out = []
    # 1. 0 埋めの番号
    padded = []
    for path, text in texts:
        key = path.rsplit(".", 1)[-1].split("[")[0]
        if (key in ZERO_PAD_KEYS and ZERO_PAD.match(text)) or (
                key in ("heading", "label", "title") and re.match(r"^\s*0\d\s*[\s.．:：|｜]", text)):
            padded.append((path, text.strip()[:2]))
    if padded:
        where = padded[0][0] + (f" など{len(padded)}箇所" if len(padded) > 1 else "")
        out.append(f"{sid} {where} 0埋めの番号「{'」「'.join(n for _, n in padded[:3])}」"
                   f"（AIの定番。「1」「2」と書く。順番に意味が無いなら番号ごと外す）")
    # 2. 強調のためのカギカッコ・【】ラベル
    for key in EMPH_KEYS:
        text = s.get(key)
        if not isinstance(text, str):
            continue
        hits = [h for h in EMPH_BRACKET.findall(text) if not re.search(r"[？?！!。]$", h)]   # 問い・文の引用は対象外
        if hits:
            out.append(f"{sid} {key} 強調のためのカギカッコ「{'」「'.join(hits[:3])}」（引用・固有名でなければ外す。"
                       f"大事な語は文の組み立てで目立たせる）")
        if LABEL_BRACKET.match(text):
            out.append(f"{sid} {key} 行頭の【】ラベル「{LABEL_BRACKET.match(text).group(0).strip()}」"
                       f"（ラベルを外して主張だけを書く）")
    for path, items in _label_nodes(s):
        for key in ("heading", "label"):
            for k, it in enumerate(items):
                v = it.get(key)
                if isinstance(v, str) and EMPH_BRACKET.search(v):
                    out.append(f"{sid} {path}[{k}].{key} 強調のためのカギカッコ「{EMPH_BRACKET.search(v).group(1)}」")
                    break
    # 3. 兄弟の項目で同じラベルを繰り返す（「リスク：…」「リスク：…」「リスク：…」）
    for path, items in _label_nodes(s):
        for key in LABEL_KEYS:
            vals = [it.get(key) for it in items if isinstance(it.get(key), str) and it.get(key).strip()]
            if len(vals) < 2 or len(vals) != len(items):
                continue
            heads = []
            for v in vals:
                parts = LABEL_SEP.split(v.strip(), maxsplit=1)
                # 「Phase 1」「FY27 上期」のような番号・年度つきの見出しは繰り返しではない
                numbered = len(parts) == 2 and bool(re.search(r"\d", parts[0]) or re.match(r"\s*[0-9０-９]", parts[1]))
                heads.append(parts[0] if len(parts) == 2 and 1 <= len(parts[0]) <= 10 and not numbered else None)
            if heads[0] and all(h == heads[0] for h in heads):
                out.append(f"{sid} {path}[*].{key} 全項目が同じラベル「{heads[0]}」で始まる（繰り返さず行見出しに"
                           f"括り出す: row_matrix の rows[].label、または lead に1回だけ書く）")
            elif len(vals) >= 3 and len(set(vals)) == 1:
                out.append(f"{sid} {path}[*].{key} 全項目が同じ「{vals[0]}」（1回だけ書いて左に括り出す）")
    # 4. タイトル: 「論点」なのに問いになっていない／共有と判断依頼の盛り合わせ
    title = s.get("title")
    if isinstance(title, str) and title.strip():
        t = title.strip()
        if "論点" in t and not re.search(r"[か？?]$", t):
            out.append(f"{sid} title 「論点」と書いているが問いの形になっていない（「〜をどこまで広げるか」のように"
                       f"問いで書くか、言い切りの結論にして「論点」を外す）: 「{t[:30]}」")
        if "と" in t and SHARE_WORDS.search(t) and ASK_WORDS.search(t):
            out.append(f"{sid} title 共有（{SHARE_WORDS.search(t).group(0)}）と判断依頼（{ASK_WORDS.search(t).group(0)}）"
                       f"を1枚に盛っている（1スライド1メッセージ。共有と判断依頼でスライドを分ける）: 「{t[:30]}」")
    # 5. 読まれない定型の免責注釈
    for path, text in texts:
        key = path.rsplit(".", 1)[-1].split("[")[0]
        hits = [p for p in DISCLAIMER_PHRASES if p in text]
        if hits:
            out.append(f"{sid} {path} 定型の免責文「{hits[0]}」（読まれない注釈はAI生成に見える。"
                       f"このスライド固有の前提だけを1文で書く）")
        elif key in NOTE_KEYS and len(text) > NOTE_MAX and "\n" not in text:
            out.append(f"{sid} {path} 注釈が{len(text)}字で改行なし（{NOTE_MAX}字以内に削るか、前提ごとに改行する）")
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
        table = relation_table()
        if rel not in table:
            out.append(f"{sid} relation「{rel}」は未知の値（{' / '.join(table)}）")
        elif t not in table[rel] and not (t in ("composite", "split") and any(b.get("type") in table[rel] for b in composite_blocks(s))):
            out.append(f"{sid} relation={rel} に type={t} は合わない（候補: {' / '.join(table[rel])}）")
    elif t == "cards":
        heads = [c.get("heading", "") for c in s.get("cards") or [] if isinstance(c, dict)]
        if sum(1 for h in heads if ORDERED_HEADING.match(str(h))) >= 2:
            out.append(f"{sid} cards の見出しが順序（STEP・番号）を表している。順番があるなら steps、並列なら番号を外す")
    return out


def check_rhythm(slides: list) -> list:
    """同じタイプが RHYTHM_RUN 枚以上続く箇所（単調に見える）。"""
    out, k = [], 0

    def key(s):
        # 合成スライドは、ブロックのタイプの組み合わせが同じときだけ「同じ構図」とみなす
        bl = composite_blocks(s)
        return (s.get("type"), tuple(b.get("type") for b in bl)) if bl else s.get("type")
    while k < len(slides):
        t = slides[k].get("type")
        j = k
        while j + 1 < len(slides) and key(slides[j + 1]) == key(slides[k]):
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


def find_todos(slides: list, meta: dict | None = None) -> list:
    """【要確認】マーカーを {slide, path, note, text} で列挙する。notes も含めて全ての文字列を見る
    （骨子段階では根拠メモを notes に書くため）。slide は 'slide-NN'、デッキ共通の meta は 'meta'。"""
    found = []

    def walk(obj, path, sid):
        if isinstance(obj, str):
            for m in TODO_MARK.finditer(obj):
                found.append({"slide": sid, "path": path or "(slide)", "note": (m.group(1) or "").strip(), "text": obj[:40]})
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]", sid)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("style", "path", "src", "image", "id", "type", "layout", "theme"):
                    continue
                walk(v, f"{path}.{k}" if path else k, sid)

    if meta:
        walk(meta, "", "meta")
    for i, s in enumerate(slides, 1):
        walk(s, "", f"slide-{i:02d}")
    return found


def resolve_density(meta: dict) -> tuple[str, str | None]:
    """(密度, 警告)。未指定は standard。未知の値は standard 扱いにして警告を返す。"""
    d = (meta or {}).get("density")
    if d is None:
        return DEFAULT_DENSITY, None
    if isinstance(d, str) and d in DENSITY_LIMITS:
        return d, None
    return DEFAULT_DENSITY, (f"meta.density「{d}」は未知の値（{' / '.join(DENSITY_LIMITS)}）。"
                             f"standard の目安で検査した。値を直す")


def _visible_chars(s: dict) -> int:
    return sum(len(re.sub(r"\s", "", t)) for _, t in iter_texts(s))


COMPOSITE_VOLUME_FACTOR = 1.5       # 合成スライド（composite）は複数ブロックを置くので、1 枚の文字数の目安を 1.5 倍にする


def composite_blocks(s: dict) -> list:
    """合成スライドのブロック（辞書だけ）。合成スライドでなければ []。"""
    if isinstance(s, dict) and s.get("type") in ("composite", "split") and isinstance(s.get("blocks"), list):
        return [b for b in s["blocks"] if isinstance(b, dict)]
    return []


def check_volume(sid: str, s: dict, density: str) -> list:
    """文字量の目安（密度で変わる）: bullets の 1 項目の字数・項目数・1 枚の表示文字数。合成スライドはブロックごとに bullets を見る。"""
    lim = DENSITY_LIMITS[density]
    out = []
    owners = [(sid, s)] + [(f"{sid} blocks[{k}]", b) for k, b in enumerate(composite_blocks(s))]
    for where, o in owners:
        items = [t for t in _item_texts(o.get("bullets"))]
        top = o.get("bullets") if isinstance(o.get("bullets"), list) else []
        if len(top) > lim["bullets"]:
            out.append(f"{where} bullets {len(top)}項目 > {lim['bullets']}（density={density}）"
                       f" → 絞るか two_column / cards に分ける（話す資料は少なく、読ませる資料は meta.density を read に）")
        long_items = [t for t in items if len(t) > lim["bullet_chars"]]
        if long_items:
            out.append(f"{where} bullets の項目が{lim['bullet_chars']}字超（density={density}）: {len(long_items)}件、"
                       f"例「{long_items[0][:24]}…」{len(long_items[0])}字 → 1 項目 1 メッセージに削る。詳細は本文に回す")
    if s.get("type") not in VOLUME_EXEMPT:
        n = _visible_chars(s)
        limit = int(lim["slide_chars"] * (COMPOSITE_VOLUME_FACTOR if s.get("type") in ("composite", "split") else 1))
        if n > limit:
            out.append(f"{sid} 表示文字数 {n}字 > {limit}（density={density}）"
                       f" → 項目を減らす・2 枚に分ける。読ませる資料なら meta.density を read にする")
    return out


# 「Nページを参照」のような、ほかのページを指す書き方（「全200ページのPDF」「3ページ構成」「5ページの見積もり」は指していない）。
# 「見」は「見る/見て/見よ…」の活用形に限る（見積もり・見込み・見直しを拾わない）。「3枚目標」「5枚目安」も除く。
# 「p.12」「12p.」の両方を受ける（数字は group(1) か group(2)）。
PAGE_REF = re.compile(
    r"(\d+)\s*(?:枚目(?![標安的])|ページ目(?![標安的])"
    r"|ページ(?=\s*(?:を|に|で|は|の)?\s*(?:参照|参考|記載|説明|見(?:る|て|よ|れ|ら|え|ま)|示|ご覧|戻))"
    r"|p\.)"
    r"|(?<![A-Za-z])[pP]\.\s*(\d+)")


def relabel_slides(text: str, png_numbers: list) -> str:
    """文中の 'slide-NN'（deck.json の NN 枚目）を、プレビュー PNG の番号に直して
    'slide-MM（deck.json NN枚目）' にする。凡例ページの自動挿入などで番号がずれたスライドだけ。"""
    def rep(m):
        n = int(m.group(1))
        if 1 <= n <= len(png_numbers) and png_numbers[n - 1] != n:
            return f"slide-{png_numbers[n - 1]:02d}（deck.json {n}枚目）"
        return m.group(0)
    return re.sub(r"slide-(\d{2})(?!\d)", rep, text)


def png_numbers_for(deck: dict, layout: dict) -> list:
    """deck.json の各スライドが、expand_slides 後（= check_layout / check_diagram / プレビュー PNG）で
    何枚目になるかの列。build_deck が使えない・展開に失敗したときは空リスト（番号はそのまま）。"""
    if build_deck is None:
        return []
    try:
        nums, pos = [], 1
        for s in deck.get("slides", []):
            part = build_deck.expand_slides({**deck, "slides": [s]}, layout)["slides"]
            # 凡例ページが前に挿入されるタイプは、スライド本体（同一オブジェクト）の位置を指す。agenda の分割は先頭
            own = next((k for k, x in enumerate(part) if x is s), 0)
            nums.append(pos + own)
            pos += len(part)
        return nums
    except BaseException:
        return []


def lint(deck: dict, punch_max: int | None = None, closing_max: int = 22,
         png_numbers: list | None = None) -> dict:
    """デッキ全体を検査して {errors, warnings, stats, todos, density} を返す（ファイルは読まない）。
    png_numbers を渡すと、出力の slide-NN を expand_slides 後（プレビュー PNG）の番号にして
    deck.json の番号を併記する（check_layout / check_diagram と同じ体系）。省略時は deck.json の番号。"""
    res = _lint(deck, punch_max, closing_max)
    if png_numbers and any(n != i for i, n in enumerate(png_numbers, 1)):
        res["errors"] = [relabel_slides(e, png_numbers) for e in res["errors"]]
        res["warnings"] = [relabel_slides(w, png_numbers) for w in res["warnings"]]
        res["summary"] = relabel_slides(res["summary"], png_numbers)
        for td in res["todos"]:
            td["slide"] = relabel_slides(td["slide"], png_numbers)
    return res


def _lint(deck: dict, punch_max: int | None = None, closing_max: int = 22) -> dict:
    slides = deck.get("slides", [])
    meta = deck.get("meta", {}) or {}
    total = len(slides)
    density, density_warn = resolve_density(meta)
    if punch_max is None:
        punch_max = DENSITY_LIMITS[density]["punch"]
    errors, warns = [], []
    if density_warn:
        warns.append(density_warn)
    stats = {"punch_total": 0, "punch_over": 0, "dewanaku": 0, "dash": 0, "circled": 0, "ai_phrase": 0,
             "ai_phrase_soft": 0, "half_colon": 0, "full_colon": 0, "ja_space": 0, "todo": 0, "ai_look": 0}
    ja_space_examples = []
    for i, s in enumerate(slides, 1):
        sid = f"slide-{i:02d}"
        t = s.get("type")
        if t == "closing" and len(str(s.get("title", ""))) > closing_max:
            errors.append(f"{sid} closing.title {len(s['title'])}字 > {closing_max}字: 「{s['title']}」"
                          f" → {closing_max}字以内に縮める（長い主張は lead か本文へ回す。固定枠で 2 行になると罫線を貫通する）")
        if s.get("punch"):
            stats["punch_total"] += 1
            if len(s["punch"]) > punch_max:
                stats["punch_over"] += 1
                warns.append(f"{sid} punch {len(s['punch'])}字 > {punch_max}（density={density}）: 「{s['punch'][:30]}…」"
                             f" → 結論を 1 文に削り、根拠は本文へ")
        texts = list(iter_texts(s))
        warns.extend(check_claims(sid, s))
        warns.extend(check_tables(sid, s, texts))
        warns.extend(check_relation(sid, s))
        ai_look = check_ai_look(sid, s, texts)
        stats["ai_look"] += len(ai_look)
        warns.extend(ai_look)
        warns.extend(check_volume(sid, s, s.get("density") if isinstance(s.get("density"), str) and s.get("density") in DENSITY_LIMITS else density))     # スライドの density を優先（S5b）
        for path, text in texts:
            warns.extend(check_numbers(sid, path, text))
            if JA_SPACE.search(text) and JA_TIGHT.search(TODO_MARK.sub("", text)) and not CODE_LIKE.search(text):
                stats["ja_space"] += 1
                if len(ja_space_examples) < 3:
                    ja_space_examples.append(f"{sid} {path}「{text[:30]}」")
        for path, text in texts:
            if re.search(r"\*\*[^*]+\*\*|(?<!`)`[^`]+`|^#{1,6}\s", text):
                errors.append(f"{sid} {path} Markdown記法残留: 「{text[:40]}」"
                              f" → ** ` # の記号を外す（強調は bullets の強調項目・太字指定で表す。画面にそのまま記号が出る）")
            for m in PAGE_REF.finditer(text):
                n = int(m.group(1) or m.group(2))
                if n > total:
                    errors.append(f"{sid} {path} 「{m.group(0)}」が総枚数{total}を超過"
                                  f" → ページ番号は書かず、タイトルの言葉で指す（実在しない番号になっている）")
                elif 1 <= n <= total:
                    warns.append(f"{sid} {path} ページ番号直書き「{m.group(0)}」（付録追加でずれる。実体: {slides[n-1].get('title','')[:20]}）"
                                 f" → 番号の代わりにそのスライドのタイトルで指す")
            for ph in AI_PHRASES:
                c = text.count(ph)
                if c:
                    stats["ai_phrase"] += c
                    errors.append(f"{sid} {path} AI定型句「{ph}」×{c}: 「{text[:40]}」"
                                  f" → 具体的な主語・動詞・数字で書き換える（例: 「〜を実現」→「〜を月 20 時間減らす」）")
            for ph in AI_PHRASES_SOFT:
                c = text.count(ph)
                if c:
                    stats["ai_phrase_soft"] += c
                    warns.append(f"{sid} {path} 一般語「{ph}」×{c}（文脈次第。AI定型句と紛らわしければ言い換え検討）: 「{text[:40]}」")
            stats["dewanaku"] += text.count("ではなく")
            stats["dash"] += text.count("——") + text.count("—")
            stats["circled"] += len(re.findall(r"[①-⑳]", text))
            # 日本語文中の半角コロン（URL・時刻・出典 source を除く）
            # 【要確認: …】のコロンは仕様上どちらも可なので、マーカー部分は除いて判定する
            plain = TODO_MARK.sub("", text)
            if (not path.split(".")[-1].startswith("source")
                    and re.search(r"[぀-ヿ一-鿿]\s*:\s*[぀-ヿ一-鿿]", plain) and not re.search(r"https?:", plain)):
                stats["half_colon"] += 1
                warns.append(f"{sid} {path} 日本語文中の半角コロン: 「{text[:40]}」 → 全角「：」にする")
            stats["full_colon"] += text.count("：")
    todos = find_todos(slides, meta)
    stats["todo"] = len(todos)
    for td in todos:
        what = td["note"] or "何を確かめるか未記入"
        warns.append(f"{td['slide']} {td['path']} 要確認マーカー【{what}】: 「{td['text']}」"
                     f" → 確かめる点を【要確認: …】で明示するか、根拠を確かめて本文を確定しマーカーを消す")
    warns.extend(check_rhythm(slides))
    warns.extend(check_dates(slides, meta))
    if stats["ja_space"]:
        warns.append(f"和文と英数字の間の空白がそろっていない文字列 {stats['ja_space']}箇所（空白のある所と無い所が混ざっている。"
                     f"空白を入れるなら全部に、詰めるなら全部に統一する。例: {' / '.join(ja_space_examples)}）")
    # 「ではなく」等は件数を1行で
    todo_slides = sorted({td["slide"] for td in todos})
    summary = (f"[集計] 「ではなく」{stats['dewanaku']}回 / ダッシュ{stats['dash']}回 / 丸数字{stats['circled']}個 / "
               f"AI定型句{stats['ai_phrase']}箇所 / AIの定番パターン{stats['ai_look']}件 / 一般語{stats['ai_phrase_soft']}箇所 / "
               f"punch {stats['punch_over']}/{stats['punch_total']}枚が{punch_max}字超 / "
               f"半角コロン混在{stats['half_colon']}箇所（全角：{stats['full_colon']}回） / "
               f"要確認マーカー{stats['todo']}箇所" + (f"（{', '.join(todo_slides[:8])}{'…' if len(todo_slides) > 8 else ''}）" if todos else "")
               + f" / density={density}")
    return {"errors": errors, "warnings": warns, "summary": summary, "stats": stats, "todos": todos,
            "density": density, "slides": total}


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="デッキ文言の機械リント")
    ap.add_argument("deck_dir")
    ap.add_argument("--json")
    ap.add_argument("--punch-max", type=int, default=None,
                    help="punch文字数の警告しきい値（既定は meta.density で変わる: talk 50 / standard 80 / read 120）")
    ap.add_argument("--closing-max", type=int, default=22)
    ap.add_argument("--fail-on-todo", action="store_true", help="【要確認】マーカーが 1 つでも残っていれば exit 1（仕上げの最終確認用）")
    args = ap.parse_args()
    deck_json = Path(args.deck_dir) / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    png_numbers = []
    if build_deck is not None:
        try:
            _, _, layout = build_deck.load_deck(Path(args.deck_dir))
            png_numbers = png_numbers_for(deck, layout)
        except BaseException:
            png_numbers = []
    res = lint(deck, args.punch_max, args.closing_max, png_numbers)
    errors, warns = res["errors"], res["warnings"]
    if args.fail_on_todo and res["todos"]:
        errors = errors + [f"【要確認】マーカーが{len(res['todos'])}箇所残っています（--fail-on-todo）"
                           f" → 上の警告の箇所を確かめて確定し、マーカーを消してから再実行する"]
    out = {"deck": args.deck_dir, "slides": res["slides"], "errors": errors, "warnings": warns + [res["summary"]],
           "stats": res["stats"], "todos": res["todos"], "density": res["density"]}
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for e in errors:
        print("NG:", e)
    for w in warns:
        print("warn:", w)
    print("warn:", res["summary"])
    print(f"lint_deck_text: {res['slides']}枚 不合格{len(errors)}件 / 警告{len(warns)}件")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

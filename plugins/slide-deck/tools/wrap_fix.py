#!/usr/bin/env python3
"""語の途中で折れる文を、文節の切れ目で折る（S5b）。

考え方: ブラウザ・PowerPoint の自然な折り返しだと「プラグイ／ン」「担当／者へ」のように語の途中で行が切れる段落だけ、
文節の切れ目（ja_text.can_break）に明示の改行（\\n）を入れる。HTML と PPTX の両方に同じ位置の改行が入る。
語の途中で折れない段落・すでに \\n を書いた段落・和文でない段落には何もしない（既存の見た目を変えない）。

値はレイアウト JSON の共通領域 `common.wrap`（meta.layout_overrides.common.wrap / スライドの style.wrap で変えられる）:
  enabled         false で止める（既定 true）
  detect_level    語の途中かどうかの判定に使う ja_text.can_break の level（既定 3 = good_break だけ。1 にすると活用語の途中も拾う）
  safety          実機（Meiryo など）で字幅が少しずれても破綻しないよう、改行を入れるときの幅と、直したあとの語中折れの数え方に、幅をこの倍率に狭めた折り返しも使う（既定 0.95）。直すかどうかの判定は実幅の折り返しだけで行う
  max_back_em     切れ目を探して行の中をさかのぼってよい最大の字数（既定 10。長い行で右端が大きく不ぞろいになるのを防ぐ）
  max_extra_lines 改行を入れて行数が増えてよい上限（既定 1）。増やしてよいのは、箱の高さに余裕があると呼び出し側が確かめたときだけ（余裕を測れない場所は増やさない）。0 で常に増やさない
  min_px          この文字サイズ(px)未満の文には掛けない（既定 0 = 掛ける）
build_deck.apply_line_balance が呼ぶ（決まった大きさ・幅に対して改行を入れる。順序は「大きさを決める → 改行を入れる」）。
"""
from __future__ import annotations

import re

import ja_text

# 切れ目を入れてはいけない場所: 英数字・URL のかたまりの内側（前後とも空白でない ASCII）と、【要確認…】の内側
_TODO_SPAN = re.compile(r"【要確認[^】]*】?")
_MIN_LINE = 2                  # 明示の改行でできる行（最終行を除く）の最小の字数。1 字だけの行（「の」だけ）を作らない
_TAIL_MIN = 3                  # 最終行の最小の字数（元の最終行が 3 字以上のとき、改行を入れて 1〜2 字にしない）

DEFAULTS = {"enabled": True, "detect_level": 3, "safety": 0.95, "max_back_em": 10.0, "max_extra_lines": 1, "min_px": 0.0}


def config(st) -> dict:
    """resolve_style の結果（st）から common.wrap の値を取り出す（足りない・型違いは既定値）。"""
    cfg = dict(DEFAULTS)
    raw = st.get("wrap") if isinstance(st, dict) else None
    if isinstance(raw, dict):
        for k, dv in DEFAULTS.items():
            v = raw.get(k)
            if isinstance(dv, bool):
                if isinstance(v, bool):
                    cfg[k] = v
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                cfg[k] = type(dv)(v)
    cfg["detect_level"] = min(3, max(1, int(cfg["detect_level"])))
    cfg["safety"] = min(1.0, max(0.5, float(cfg["safety"])))
    return cfg


def _lines(text: str, size, width, font, bold, loose: bool = False) -> list:
    out = []
    for para in str(text).split("\n"):
        out.extend(ja_text.wrap_lines(para, size, width, font, bold, loose))
    return out


def midword_breaks(text: str, size, width, font=None, bold: bool = False, level: int = 3) -> int:
    """行の終わりが語の途中になっている箇所の数。自然な折り返しの行末に加え、明示の改行（\\n）の位置も数える
    （語の途中に入れた明示の改行は、自然な折り返しと同じ見た目の欠点なので）。
    自然な折り返しは 2 通りで見積もる: 禁則どおり（小書きの仮名・長音を行頭に置かない）と、Chromium の既定（置く。「ブロ／ック」）。
    数は両方の合計（同じ場所で折れれば 2 と数える。比べるための数で、件数ではない）。"""
    n = 0
    paras = str(text).split("\n")
    joined = "".join(paras)
    base = 0
    for pi, para in enumerate(paras):
        if pi > 0 and 0 < base < len(joined) and paras[pi - 1] and para and not ja_text.can_break(joined, base, level):
            n += 1
        if para:
            for loose in (False, True):
                lines = ja_text.wrap_lines(para, size, width, font, bold, loose)
                pos = 0
                for ln in lines[:-1]:
                    k = para.find(ln, pos) if ln else pos
                    k = pos if k < 0 else k
                    pos = k + len(ln)
                    while pos < len(para) and para[pos] == " ":
                        pos += 1
                    if 0 < pos < len(para) and not ja_text.can_break(joined, base + pos, level):
                        n += 1
        base += len(para)
    return n


def _score(text, size, width, safety, font, bold, level) -> tuple:
    """(実幅と余裕幅の語中折れの合計, 実幅での行数（2 通りの折り返しの多いほう）)"""
    return (midword_breaks(text, size, width, font, bold, level) + midword_breaks(text, size, width * safety, font, bold, level),
            max(len(_lines(text, size, width, font, bold, loose)) for loose in (False, True)))


def _slack_ok(cand: str, size, width, back_em, safety, font, bold) -> bool:
    """改行を入れた各行（最終行を除く）が、行幅から back_em 字分より大きく余っていない（右端が大きく不ぞろいにならない）。"""
    allow = back_em * size + width * (1.0 - safety)
    for para in cand.split("\n")[:-1]:
        if width - sum(ja_text.char_em(c, font, bold) for c in para) * size > allow:
            return False
    return True


def _inside_token(joined: str, pos: int) -> bool:
    """改行を入れる位置 pos（改行を除いた文字列での位置）が、英数字・URL のかたまり、または【要確認…】の内側か。"""
    if 0 < pos < len(joined):
        a, b = joined[pos - 1], joined[pos]
        if a.isascii() and b.isascii() and not a.isspace() and not b.isspace():
            return True
    for m in _TODO_SPAN.finditer(joined):
        if m.start() < pos < m.end():
            return True
    return False


def breaks_ok(cand: str, size, width, font=None, bold: bool = False, tail_min: int = _TAIL_MIN) -> bool:
    """入れた改行の検算。(1) 位置が語の途中（英数字・URL・【要確認…】の内側）でない (2) どの行も、最終の大きさ・幅で折り返されない
    (3) 最終行以外に 1 字だけの行がない (4) 最終行が 1〜2 字に短くならない。"""
    segs = cand.split("\n")
    joined = "".join(segs)
    pos = 0
    for sg in segs[:-1]:
        pos += len(sg)
        if _inside_token(joined, pos) or len(sg.strip()) < _MIN_LINE:
            return False
    if len(segs[-1].strip()) < tail_min:
        return False
    for loose in (False, True):
        for sg in segs:
            if sg and len(ja_text.wrap_lines(sg, size, width, font, bold, loose)) > 1:
                return False
    return True


def line_count(text, size, width, font=None, bold: bool = False) -> int:
    return max(len(_lines(text, size, width, font, bold, loose)) for loose in (False, True))


def fix(text, size, width, cfg=None, font=None, bold: bool = False, min_tail: int = 4, extra: int = 0):
    """語の途中で折れる文に文節の切れ目の改行を入れて返す（入れる必要がない・入れると行が増える・直せないときは text のまま）。
    extra: 行数が増えてよい数（呼び出し側が箱の高さの余裕から決める。cfg.max_extra_lines が上限。既定 0 = 増やさない）。
    候補は ja_text.phrase_wrap（自然な折り返しの行末だけ直す）と ja_text.phrase_lines（文節だけで全体を組み直す）を、
    余裕幅と実幅で作り、語中折れが減り・行数が増えず・右端が大きく不ぞろいにならないもののうち、語中折れ・行数が最小のものを選ぶ。"""
    cfg = cfg or DEFAULTS
    if (not cfg.get("enabled", True) or not isinstance(text, str) or not text or "\n" in text or len(text) > 200
            or size < max(1.0, cfg.get("min_px", 0.0)) or width < size * 2 or not ja_text._has_cjk(text)):
        return text
    level, safety = cfg.get("detect_level", 3), cfg.get("safety", 0.95)
    if midword_breaks(text, size, width, font, bold, level) == 0:
        return text                      # 実幅の自然な折り返しで語の途中が無ければ何もしない（余裕幅だけで語中になる文は触らない）
    bad0, lines0 = _score(text, size, width, safety, font, bold, level)
    if lines0 < 2:
        return text
    tail0 = len((ja_text.wrap_lines(text, size, width, font, bold)[-1] or "").strip())
    tail_min = _TAIL_MIN if tail0 >= _TAIL_MIN else 0          # 元の最終行が 3 字以上なら、改行を入れて 1〜2 字の最終行にしない
    back_em = float(cfg.get("max_back_em", 10.0))
    back = min(0.5, max(0.05, back_em * size / max(width, 1.0)))
    limit = lines0 + max(0, min(int(extra), int(cfg.get("max_extra_lines", 1))))
    best = None
    for w in (width * safety, width):               # まず余裕幅で切る（実機で字幅が少し広くても同じ位置で折れる）。行が増えるなら実幅で切る
        cands = [ja_text.phrase_wrap(text, size, w, font=font, bold=bold, min_tail=min_tail, max_back=back),
                 "\n".join(ja_text.phrase_lines(text, size, w, font, bold))]
        for cand in cands:
            if cand == text or "\n" not in cand or not _slack_ok(cand, size, width, back_em, safety, font, bold):
                continue
            if not breaks_ok(cand, size, width, font, bold, tail_min):
                continue
            bad, lines = _score(cand, size, width, safety, font, bold, level)
            if lines > limit or bad >= bad0:
                continue
            if best is None or (bad, lines) < best[0]:
                best = ((bad, lines), cand)
    return best[1] if best else text

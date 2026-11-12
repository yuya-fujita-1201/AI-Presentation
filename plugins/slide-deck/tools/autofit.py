# -*- coding: utf-8 -*-
"""自動フィットの土台: 内容量から文字サイズ・列幅・行高を決める純関数と、決定を style に反映する薄い層。

build_deck.resolve_style が「レイアウト既定 → density → meta.layout_overrides → slide.style」を解決したあとに
`apply(layout, deck, slide, st)` を呼ぶ。HTML も PPTX も `st` の値だけを読むので、同じ決定が両方に効く。

## 設計の約束（新しいタイプのフィットを足す人向け）

1. フィット関数は `@fitter("type名")` で登録し、`fn(ctx) -> None` として書く。
   - 入力は `ctx`（`Ctx`）: `ctx.slide`（内容）、`ctx.st`（解決済み style。書き換えず読むだけ）、`ctx.density`、`ctx.adjust`。
   - 結果は `ctx.set(領域, キー, 値)`（style の更新）、`ctx.warn(コード, 文)`、`ctx.note(コード, 文)` で返す。
   - 文は `{label}` を含めて書く（「N枚目（type=table）」に置き換わる。resolve_style はスライド番号を知らないため）。
2. **明示値の判定**は必ず `ctx.explicit(領域, キー)`。meta.layout_overrides と slide.style に書かれたキーだけが明示。
   明示値は書き換えない（候補を [明示値] 1 つに絞る）。明示値のままでは収まらないときは `warn` で伝える。
3. **上限は style の値**: 明示でない値（レイアウト既定 + density）を「上限」として、そこから縮める方向に探す
   （standard は既定で収まるなら今と同じ見た目）。下限は領域の `min_size` など（レイアウト JSON に置く）。
4. 領域の矩形は `ctx.st[領域]` の x / y / w / h から読む（全面前提の定数を埋めない）。下端は `ctx.content_bottom()`。
5. 純粋な計算は `fit_table_layout` のように「引数 → 結果の dict」の関数に分ける（単体テストしやすく、合成スライドで矩形を変えて呼べる）。
6. 決定はキャッシュされる（同じ入力なら 1 回だけ計算）。`ctx.st` に `_fit` が入る: `{"issues": [[level, code, text], ...], "info": {...}}`。
   警告の出力は build_deck._check_overflow が `_fit.issues` を `warn()` / `note()` に流す（1 か所）。

## 密度（density）

`meta.density`（talk / standard / read。スライドの `density` で上書き可）。プリセットはレイアウト JSON の
`densities.<密度>.<タイプ>.<領域>.<プロパティ>`（タイプ単位の差分）に置き、resolve_style が
「レイアウト既定 → density → meta.layout_overrides → slide.style」の順に重ねる。
"""
from __future__ import annotations

import copy
import json
import re
import unicodedata

import ja_text
import shape_engine

DENSITIES = ("talk", "standard", "read")
DEFAULT_DENSITY = "standard"

# 見出し・リードの下限（上限サイズに対する比。領域に min_size があればそれを使う）
TITLE_MIN_RATIO = 0.78
LEAD_MIN_RATIO = 0.8

# 下端の余白: 本文の下端はフッターの上端からこの分だけ空ける
FOOTER_GAP = 18
# 表の上下余白の下限
MIN_PAD_Y = 6

# 本文領域とみなさない領域（lead の下に何があるかを探すときに除く）
_CHROME = {"eyebrow", "title", "rule", "lead", "punch", "footer_l", "footer_r", "brand", "conclusion", "source", "legend", "bg"}


# ---------------------------------------------------------------------------
# 設定の読み出し（density / autofit / 明示値）
# ---------------------------------------------------------------------------

def density_of(deck: dict, slide: dict | None = None) -> str:
    """このスライドの密度。スライドの density → meta.density → standard。不正な値は standard（検査は validate_deck）。"""
    for src in (slide, (deck or {}).get("meta")):
        if isinstance(src, dict) and src.get("density") in DENSITIES:
            return src["density"]
    return DEFAULT_DENSITY


def autofit_on(deck: dict, slide: dict | None = None) -> bool:
    """自動フィットを行うか。スライドの autofit:false → meta.autofit:false（既定 true）。"""
    if isinstance(slide, dict) and slide.get("autofit") is False:
        return False
    meta = (deck or {}).get("meta")
    if isinstance(meta, dict) and meta.get("autofit") is False:
        return False
    return True


def density_layer(layout: dict, density: str, type_name: str) -> dict:
    """レイアウト JSON の densities.<密度>.<タイプ>（領域 → プロパティ）。無ければ {}。"""
    d = ((layout or {}).get("densities") or {}).get(density) or {}
    layer = d.get(type_name)
    return layer if isinstance(layer, dict) else {}


def explicit_props(deck: dict, slide: dict) -> dict:
    """利用者が明示した値の一覧 {領域: {キー,...}}。meta.layout_overrides.common / [type] と slide.style に現れたキー。
    resolve_style が返す辞書からは明示かどうか分からないため、元の deck から数える。"""
    out: dict = {}
    t = slide.get("type")
    meta = (deck or {}).get("meta") or {}
    ov = meta.get("layout_overrides") if isinstance(meta, dict) else None
    ov = ov if isinstance(ov, dict) else {}
    for src in (ov.get("common"), ov.get(t), slide.get("style")):
        if not isinstance(src, dict):
            continue
        for region, props in src.items():
            if isinstance(props, dict):
                out.setdefault(region, set()).update(props.keys())
    return out


def is_explicit(deck: dict, slide: dict, region: str, key: str) -> bool:
    """region.key が meta.layout_overrides か slide.style に書かれているか。"""
    return key in explicit_props(deck, slide).get(region, ())


# 利用者が書いても「領域を自分で決めた」とは見なさない領域のキー（拡大・箱の伸ばしの強さを変えるトークン）。
USER_TOKEN_KEYS = ("cols_search", "center_ratio", "grow_sizes", "scale_k")


def user_set_region(deck: dict, slide: dict, region: str) -> bool:
    """利用者が領域 region のキー（位置・大きさ・文字など。thin_* などの拡大のトークンは除く）を style / meta.layout_overrides に書いたか。
    単独スライドの steps / cards は、書いた領域には S5a の拡大・箱の伸ばしを一切かけない（変更前と同じ結果にする。agenda の AGENDA_FIXED_KEYS と同じ考え方）。"""
    return any(not (k.startswith(("thin_", "fill_")) or k in USER_TOKEN_KEYS) for k in explicit_props(deck, slide).get(region, ()))


# ---------------------------------------------------------------------------
# フィット関数に渡す文脈と、結果の入れ物
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self, deck, slide, st, density, adjust):
        self.deck = deck
        self.slide = slide
        self.st = st
        self.type = slide.get("type")
        self.density = density
        self.adjust = adjust                       # False なら style を変えず、見積もりと警告だけ
        self._explicit = explicit_props(deck, slide)
        self.updates: dict = {}
        self.issues: list = []
        self.info: dict = {}

    # ---- 読み出し
    def explicit(self, region: str, key: str) -> bool:
        return key in self._explicit.get(region, ())

    def fixed(self, region: str, key: str) -> bool:
        """この値を動かしてはいけないか（明示値、または自動フィットが切られている）。"""
        return self.explicit(region, key) or not self.adjust

    def by_spec(self, spec: str) -> str:
        """警告の「なぜ縮めていないか」。autofit が切られていれば style の指定のせいにしない（core-C-04）。
        spec は「style.table.cell_size=24」のような指定の表記。"""
        return f"{spec} の指定どおり" if self.adjust else "autofit が切られているため縮めていません"

    def undo_hint(self) -> str:
        """「縮めたければこうする」の括弧書き。autofit が切られているときは、消すのは style の指定ではなく autofit:false。"""
        return "（指定を消すと自動で縮めます）" if self.adjust else "（meta.autofit または autofit: false を外すと自動で縮めます）"

    def val(self, region: str, key: str, default=None):
        """領域の値。このフィットで先に決めた更新（まだ st には入っていない）を優先して読む。"""
        up = self.updates.get(region)
        if isinstance(up, dict) and key in up:
            return up[key]
        r = self.st.get(region)
        return r.get(key, default) if isinstance(r, dict) else default

    def view(self) -> dict:
        """st に、このフィットで決めた更新を重ねた浅いコピー（結論帯・出典で本文が狭まった後の状態を見る用）。"""
        v = dict(self.st)
        for region, props in self.updates.items():
            reg = v.get(region)
            if isinstance(reg, dict):
                v[region] = {**reg, **props}
        return v

    def content_bottom(self, region: str = "body") -> float:
        """本文の下端 y。フッターの少し上。結論帯・出典があればその上（proposal_engine.CONTENT_BOTTOM 基準）。"""
        import proposal_engine as pe
        footer = self.st.get("footer_l") or self.st.get("footer_r")
        base = (footer["y"] if isinstance(footer, dict) and "y" in footer else 720 - 24) - FOOTER_GAP
        r = pe.reserve(self.slide, self.view())
        if r:
            base = min(base, pe.CONTENT_BOTTOM - r)
        reg = self.st.get(region)
        if isinstance(reg, dict) and "h" in reg and "y" in reg:
            base = min(base, reg["y"] + reg["h"])
        return base

    # ---- 書き込み
    def set(self, region: str, key: str, value, force: bool = False) -> None:
        """style の更新を記録する（明示値には書かない。adjust=False のときは何もしない）。
        force=True は、利用者が fit:"content" を明示したときに、明示の h を上限として縮めるなど、明示値を意図的に動かす場合だけ。"""
        if not self.adjust or (self.explicit(region, key) and not force):
            return
        self.updates.setdefault(region, {})[key] = value

    def warn(self, code: str, text: str) -> None:
        self.issues.append(["warn", code, text])

    def note(self, code: str, text: str) -> None:
        self.issues.append(["note", code, text])


_FITTERS: dict = {}


def fitter(*type_names):
    """タイプ固有のフィット関数を登録する: `@fitter("table")`。複数タイプで共有してもよい。"""
    def deco(fn):
        for t in type_names:
            _FITTERS[t] = fn
        return fn
    return deco


def fitters() -> dict:
    return dict(_FITTERS)


# ---------------------------------------------------------------------------
# 適用層（キャッシュつき）
# ---------------------------------------------------------------------------

_CACHE: dict = {}


def _font_signature():
    return [list(ja_text._default_fonts.get("body") or []), list(ja_text._default_fonts.get("heading") or []),
            list(ja_text.measure_source())]


def _cache_key(ctx: Ctx):
    return json.dumps([ctx.type, ctx.slide, ctx.st, ctx.density, ctx.adjust,
                       {k: sorted(v) for k, v in ctx._explicit.items()}, _font_signature()],
                      sort_keys=True, ensure_ascii=False, default=str)


def clear_cache() -> None:
    _CACHE.clear()


def apply(layout: dict, deck: dict, slide: dict, st: dict) -> dict:
    """スライド 1 枚の自動フィットを決めて st に反映する（resolve_style から呼ぶ）。st を書き換え、`st["_fit"]` を付ける。
    戻り値は `{"handled": {...}, "issues": [...], "info": {...}}`。レイアウトに densities が無い・フィット関数が無いタイプでも安全。"""
    ctx = Ctx(deck, slide, st, density_of(deck, slide), autofit_on(deck, slide))
    key = _cache_key(ctx)
    hit = _CACHE.get(key)
    if hit is None:
        _chrome_fit(ctx)
        _bottom_parts_fit(ctx)
        fn = _FITTERS.get(ctx.type)
        if fn is not None:
            fn(ctx)
        hit = {"updates": ctx.updates, "issues": ctx.issues, "info": ctx.info}
        if len(_CACHE) > 2000:
            _CACHE.clear()
        _CACHE[key] = hit
    for region, props in hit["updates"].items():
        reg = st.get(region)
        if isinstance(reg, dict):
            reg.update(copy.deepcopy(props))
    res = {"handled": sorted(hit["updates"].keys()), "issues": copy.deepcopy(hit["issues"]), "info": copy.deepcopy(hit["info"])}
    st["_fit"] = res
    return res


# ---------------------------------------------------------------------------
# 小さな道具
# ---------------------------------------------------------------------------

TONES = ("good", "warn", "bad", "accent", "muted")


def table_rows(slide: dict):
    """表の行を (セルの配列の配列, 強調する行番号の集合) にそろえる。
    行は [..]（従来）か {"cells": [..], "emphasis": true}。validate_deck が正規化した `_row_emphasis` も読む。"""
    rows, emph = [], set(slide.get("_row_emphasis") or [])
    for i, r in enumerate(slide.get("rows") or []):
        if isinstance(r, dict):
            if r.get("emphasis"):
                emph.add(i)
            r = r.get("cells")
        rows.append(r if isinstance(r, list) else [])
    return rows, emph


def _toned(value) -> bool:
    """意味の色（tone）が付いたセルは太字で描くので、幅の見積もりも太字で測る。"""
    return isinstance(value, dict) and value.get("tone") in TONES


def cell_text(value) -> str:
    """表のセルの表示文字列（文字列 / {text,url} / 数値 / None）。"""
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("text", ""))
    return str(value)


def text_em(text: str, bold: bool = False) -> float:
    """テキストの 1 行あたり最大幅（em）。明示改行は行ごとに測る。"""
    best = 0.0
    for ln in str(text).split("\n"):
        best = max(best, sum(ja_text.char_em(c, None, bold) for c in ln))
    return best


def longest_token_em(text: str, bold: bool = False) -> float:
    """それ以上折れない最長の単位（英数字連続は 1 語、和文は 1 文字）の幅（em）。"""
    best = 0.0
    for ln in str(text).split("\n"):
        for tok in ja_text._tokens(ln):
            best = max(best, sum(ja_text.char_em(c, None, bold) for c in tok))
    return best


def longest_token(text: str, bold: bool = False):
    """それ以上折れない最長の単位（幅 em, 文字列）。long_word_check（途中で折れる警告）が使う。
    【要確認…】のマーカーは 1 語に数えない（長い印は文節で折れて読める。中の英数字の連続は通常どおり数える。S5b）。"""
    best, best_tok = 0.0, ""
    for ln in str(text).split("\n"):
        for tok in ja_text._tokens(ln, marker_atomic=False):
            w = sum(ja_text.char_em(c, None, bold) for c in tok)
            if w > best:
                best, best_tok = w, tok
    return best, best_tok


def long_word_check(ctx: Ctx, entries, where_default: str = "枠") -> None:
    """折り返せない長い文字列（URL・長い英単語）が枠の幅を超えるときの警告（core-A-02）。
    entries: [(text, size, width_px, where)]。1 スライドにつき 1 件にまとめる（いちばんはみ出す語を例に出す）。
    HTML は overflow-wrap で途中で折り、PPTX も枠で折るので「途中で切れる」。切れ方がよくないので短くしてもらう。"""
    worst = None
    count = 0
    for text, size, width, where in entries:
        if not text or width <= 0:
            continue
        em, tok = longest_token(text)
        over = em * size - width
        if over > 1.0 and len(tok) >= 4:
            count += 1
            if worst is None or over > worst[0]:
                worst = (over, tok, int(width), where or where_default, em * size)
    if worst is None:
        return
    over, tok, width, where, need = worst
    shown = tok if len(tok) <= 24 else tok[:22] + "…"
    more = f"（ほか {count - 1} 件）" if count > 1 else ""
    ctx.warn("long-word",
             f"{{label}}: 「{shown}」が{where}の幅（{width}px）に収まらず（{int(need)}px）、途中で折れて表示されます{more}"
             f" → URL や長い英単語は短くするか、区切りの位置に改行（\\n）を入れる")


def _px(v: float) -> float:
    return round(v, 1)


# ---------------------------------------------------------------------------
# 見出し・リード（全タイプ共通）
# ---------------------------------------------------------------------------

FIT_MAX_ITER = 400            # 文字サイズを 1 ずつ下げる探索の反復の上限（検証が文字サイズを 2000 までに制限するので、ふつうは届かない）


def fit_text_size(text, width, budget_h, cap, floor, line_height, heading=False, bold=False, step=1):
    """1 領域の文字サイズを cap から floor まで下げて、budget_h に収まる最大のサイズを返す純関数。
    戻り値 {size, lines, need_h, fits}。収まらなければ size=floor・fits=False。"""
    font = ja_text.heading_fonts() if heading else None
    size = cap
    last = None
    step = max(step, (cap - floor) / FIT_MAX_ITER)          # 極端に大きい cap でも反復は FIT_MAX_ITER 回まで（2^53 以上では size - 1 == size で終わらない）
    for _ in range(FIT_MAX_ITER + 2):
        lines = ja_text.estimate_lines(text, size, width, font, bold)
        need = lines * size * line_height
        last = {"size": size, "lines": lines, "need_h": need, "fits": need <= budget_h + 0.5}
        if last["fits"] or size - step < floor:
            return last
        size -= step
    return last


def _lead_budget(ctx: Ctx, lead: dict) -> float:
    """リードに使える高さ: 本文の領域の上端までの距離（無ければ領域の h）。2 行になっても本文に触れないようにする。"""
    h = lead.get("h", 40)
    tops = []
    for name, reg in ctx.st.items():
        if name in _CHROME or not isinstance(reg, dict) or "y" not in reg or name.startswith("_"):
            continue
        if reg["y"] >= lead.get("y", 0) + h * 0.5:
            tops.append(reg["y"])
    if not tops:
        return h
    return max(h, min(tops) - lead.get("y", 0) - 2)


def _full_pattern(ctx: Ctx) -> bool:
    """frame:"full" のパターン（全面を型が描く）か。見出し骨格・結論帯・出典は描かれないので、測っても警告しても意味がない。
    build_deck が resolve_style の前に slide["_pattern_frame"] を付ける（無ければ従来どおり測る）"""
    return ctx.type == "pattern" and ctx.slide.get("_pattern_frame") == "full"


SECTION_TITLE_MAX_LINES = 3
SECTION_TITLE_HARD_LINES = 4            # 下限の大きさでも 3 行に収まらないときの最後の手段（枠を 4 行分まで伸ばす）
PHRASE_WRAP_MIN_SIZE = 36               # build_deck.apply_line_balance が文節折り返し（phrase_wrap）を掛ける文字サイズの下限


def _section_lines(ctx: Ctx, text, size, w_est, w_raw, bold) -> int:
    """章扉のタイトルが、実際の HTML で何行になるか。36px 以上の大きな文字は apply_line_balance が文節折り返し
    （phrase_wrap。1 行の長さを揃えるので、素直な折り返しより行が増えることがある）で改行を入れるため、
    素直な折り返しの見積もりだけでは足りない（s4-C-01）。両方の大きいほうを取る。"""
    font = ja_text.heading_fonts()
    n = ja_text.estimate_lines(text, size, w_est, font, bold)
    if (size >= PHRASE_WRAP_MIN_SIZE and "\n" not in str(text)
            and ctx.deck.get("meta", {}).get("line_balance") is not False and ctx.slide.get("line_balance") is not False):
        pw = ja_text.phrase_wrap(text, size, w_raw, font=font, bold=bold, min_tail=max(5, ja_text.tail_min(size)))
        n = max(n, pw.count("\n") + 1)
    return n


def _fit_section_title(ctx: Ctx, r: dict, text, cap, lh, floor, fixed) -> bool:
    """章扉（section）のタイトルは 1 行の高さの枠しか無く、2 行に折れると下の罫線・副題に重なる（S4）。
    2 行までなら文字を縮めずに枠を下へ伸ばし、罫線・副題を同じだけ下げる（帯の variant は帯の高さも伸ばす）。
    2 行に収まるよう縮めても足りないときだけ 3 行まで伸ばす。枠の位置を利用者が書いたとき（title.h）は呼ばれない。
    行数は phrase_wrap が実際に入れる改行まで数える（s4-C-01）。下限まで縮めても 3 行に収まらないときは 4 行まで枠を伸ばす。
    処理したら True（1 行に収まるときは False で従来どおり）。"""
    w = r.get("w", 400) * r.get("fit_safety", 1.0) / shape_engine.width_factor(r)
    w_raw = r.get("w", 400)
    lh = max(lh, 1.25)                    # 見出しフォントの実際の行の高さは 1.2 より大きい（実測 1.25）
    h0 = r.get("h", 84)
    bold = shape_engine.is_bold(r)
    lo = cap if fixed else min(floor, cap)

    def lines_at(size):
        return _section_lines(ctx, text, size, w, w_raw, bold)

    def search(max_lines):
        size = cap
        while True:
            n = lines_at(size)
            if n <= max_lines:
                return {"size": size, "lines": n}
            if size - 1 < lo:
                return None
            size -= 1

    one = fit_text_size(text, w, h0, cap, lo, lh, heading=True, bold=bold)
    if one["fits"] and one["size"] >= cap and lines_at(cap) * cap * lh <= h0 + 0.5:
        return False                      # 1 行に収まる
    pick = None
    for n in range(2, SECTION_TITLE_MAX_LINES + 1):
        pick = search(n)
        if pick:
            break
    if pick is None:
        pick = search(SECTION_TITLE_HARD_LINES)
    if pick is None:
        return False
    size = pick["size"]
    need = pick["lines"] * size * lh
    delta = max(0.0, need + 6 - h0)       # 6px: 行の高さの見積もり誤差
    ctx.info["title"] = {"size": size, "lines": pick["lines"], "cap": cap, "max_lines": pick["lines"], "grown": round(delta, 1)}
    if size < cap and not fixed:
        ctx.set("title", "size", size)
    if delta > 0:
        ctx.set("title", "h", round(h0 + delta + 6, 1))
        ctx.set("title", "line_height", lh)         # 行の高さを明示して、見積もり（枠の高さ）と描画をそろえる（書体・太さによる差を避ける）
        y0 = r.get("y", 0)
        for name in ("rule", "subtitle"):
            reg = ctx.st.get(name)
            if isinstance(reg, dict) and "y" in reg and reg["y"] >= y0 + h0 * 0.5:
                ctx.set(name, "y", round(reg["y"] + delta, 1))
        panel = ctx.st.get("panel")
        if isinstance(panel, dict) and panel.get("y", 0) < y0 and panel.get("y", 0) + panel.get("h", 0) < 700:
            ctx.set("panel", "h", round(panel["h"] + delta, 1))
        sub = ctx.st.get("subtitle")
        if isinstance(sub, dict) and sub.get("y", 0) + delta + sub.get("h", 0) > 700:
            ctx.note("title-tall", "{label}: タイトルが " + str(pick["lines"]) + " 行になるので、罫線と副題を下げました → タイトルを短くすると 1 行に収まります")
    return True


def _chrome_fit(ctx: Ctx) -> None:
    """タイトルが 1 行（領域の高さ）に収まるよう段階的に縮め、収まらなければ警告する。リードは 2 行まで。"""
    if _full_pattern(ctx):
        return
    for region in ("title", "lead", "punch"):
        r = ctx.st.get(region)
        text = ctx.slide.get(region)
        if not isinstance(r, dict) or not text or not isinstance(text, str) or "size" not in r:
            continue
        heading = region in ("title", "punch")      # 見出しフォントで測る
        cap = r["size"]
        lh = r.get("line_height", 1.2)
        budget = r.get("h", 64) if region == "title" else _lead_budget(ctx, r)
        ratio = TITLE_MIN_RATIO if region == "title" else LEAD_MIN_RATIO
        floor = r.get("min_size") or max(8, round(cap * ratio))
        fixed = ctx.fixed(region, "size")
        # 太さ・字間は形トークン（weight / tracking）。字間を入れると 1 文字の幅が (1 + tracking) 倍になる見積もり
        if ctx.type == "section" and region == "title" and ctx.adjust and not ctx.explicit("title", "h"):
            if _fit_section_title(ctx, r, text, cap, lh, floor, fixed):
                continue
        res = fit_text_size(text, r.get("w", 400) * r.get("fit_safety", 1.0) / shape_engine.width_factor(r), budget, cap, cap if fixed else min(floor, cap), lh,
                            heading=heading, bold=shape_engine.is_bold(r))
        name = {"title": "タイトル", "lead": "リード", "punch": "パンチライン"}[region]
        ctx.info[region] = {"size": res["size"], "lines": res["lines"], "cap": cap}
        if res["fits"]:
            # 「最大 N 行に収まる」の保証（領域の高さ ÷ 行の高さ）。HTML が data-max-lines に出し、check_layout の lines 検査が実測する
            ctx.info[region]["max_lines"] = max(res["lines"], int((budget + 0.5) // (res["size"] * lh)))
            if res["size"] < cap:
                ctx.set(region, "size", res["size"])
                if cap - res["size"] >= 2:
                    ctx.note(f"{region}-shrunk",
                             f"{{label}}: {name}が長いので {cap}px → {res['size']}px に縮めました（{len(str(text))}字）"
                             f" → 縮めたくなければ{name}を短くする")
            continue
        # 下限でも収まらない
        if not fixed:
            ctx.set(region, "size", res["size"])
        over = int(res["need_h"] - budget)
        if fixed:
            ctx.warn(f"{region}-overflow",
                     f"{{label}}: {name}が枠の高さを約{over}px超える見込みです（{ctx.by_spec(f'style.{region}.size={cap}')}）"
                     f" → {name}を短くするか、style.{region}.size を下げる{ctx.undo_hint()}")
        else:
            ctx.warn(f"{region}-overflow",
                     f"{{label}}: {name}が {res['size']}px まで縮めても{res['lines']}行になり、約{over}px はみ出します"
                     f"（{len(str(text))}字）→ {name}を短くする（目安: 1 行に収まる字数）")


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

TABLE_SEARCH_MAX_ROWS = 60       # これより行の多い表は、泣き別れ回避などの探索を省く（build_deck.WRAP_TABLE_MAX_ROWS と同じ値）


def table_column_widths(columns, rows, size, header_size, total_w, pad_x, strong_cols=(), strong_rows=(),
                        power=0.7, floor_em=8.0, token_cap_em=12.0, max_lines=0):
    """列幅（px の配列。合計 = total_w）。実デッキの校正（A2 §3-2）の規則:
    列の平均文字幅の power 乗に比例（長文の列が全幅を奪わない）＋短い列の下限（それが 1 行に収まる幅。IDや短い見出しが途中で折れない）。
    下限 = min(その列の最長セルの幅, floor_em em) と、折れない最長の語（token_cap_em まで）の大きいほう。"""
    n = len(columns)
    if n == 0:
        return []
    avg = [0.0] * n
    mx_px = [0.0] * n          # 最長セルの px（ヘッダは header_size・太字で測る）
    tok_px = [0.0] * n
    for j in range(n):
        ems = []
        for i, row in enumerate(rows):
            if j >= len(row):
                continue
            strong = (j in strong_cols) or (i in strong_rows) or _toned(row[j])
            t = cell_text(row[j])
            e = text_em(t, strong)
            ems.append(e)
            mx_px[j] = max(mx_px[j], e * size)
            tok_px[j] = max(tok_px[j], min(longest_token_em(t, strong), token_cap_em) * size)
        avg[j] = (sum(ems) / len(ems)) if ems else 1.0
        h = str(columns[j])
        mx_px[j] = max(mx_px[j], text_em(h, True) * header_size)
        tok_px[j] = max(tok_px[j], min(longest_token_em(h, True), token_cap_em) * header_size)
    v = [max(a, 1.0) ** power for a in avg]
    tot = sum(v)
    px = [total_w * x / tot for x in v]
    floors = [max(min(mx_px[j], floor_em * size), tok_px[j]) + 2 * pad_x + 2.0 for j in range(n)]   # +2px: 丸め・字幅の誤差で途中折れしない余裕
    if sum(floors) >= total_w:
        px = [f * total_w / sum(floors) for f in floors]
    else:
        for _ in range(12):
            low = [j for j in range(n) if px[j] < floors[j] - 1e-6]
            if not low:
                break
            need = sum(floors[j] - px[j] for j in low)
            for j in low:
                px[j] = floors[j]
            others = [j for j in range(n) if j not in low]
            so = sum(px[j] for j in others)
            if not others or so <= 0:
                break
            for j in others:
                px[j] -= need * px[j] / so
    if max_lines:
        px = _relieve_wraps(columns, rows, px, floors, size, header_size, total_w, pad_x, strong_cols, strong_rows, max_lines)
        px = _relieve_orphans(columns, rows, px, floors, size, header_size, pad_x, strong_cols, strong_rows, max_lines)
    out = [_px(x) for x in px]
    out[-1] = _px(total_w - sum(out[:-1]))
    return out


def _relieve_wraps(columns, rows, px, floors, size, header_size, total_w, pad_x, strong_cols, strong_rows, max_lines):
    """べき乗配分のままだと max_lines 行を超えて折れる列があるとき、余裕のある列から幅を回す。
    列ごとに「全セルが max_lines 行以内になる最小幅」を求め、それを下限にして配り直す（全部は無理なら何もしない）。"""
    n = len(columns)

    def need_width(j):
        cells = [(str(columns[j]), header_size, True)]
        for i, row in enumerate(rows):
            if j < len(row):
                cells.append((cell_text(row[j]), size, (j in strong_cols) or (i in strong_rows) or _toned(row[j])))

        def ok(w):
            inner = max(1.0, w - 2 * pad_x)
            return all(ja_text.estimate_lines(t, sz, inner, None, b) <= max_lines for t, sz, b in cells)
        lo, hi = floors[j], total_w
        if ok(lo):
            return lo
        if not ok(hi):
            return None
        for _ in range(14):
            mid = (lo + hi) / 2
            if ok(mid):
                hi = mid
            else:
                lo = mid
        return hi + 1.0

    needs = [need_width(j) for j in range(n)]
    if any(x is None for x in needs) or sum(needs) > total_w:
        return px
    px = list(px)
    for _ in range(12):
        low = [j for j in range(n) if px[j] < needs[j] - 1e-6]
        if not low:
            break
        gap = sum(needs[j] - px[j] for j in low)
        for j in low:
            px[j] = needs[j]
        # 余裕（現在の幅 - 必要な幅）に比例して他の列から取る
        slack = {j: px[j] - needs[j] for j in range(n) if j not in low}
        tot = sum(slack.values())
        if tot <= 0:
            break
        for j, sl in slack.items():
            px[j] -= min(sl, gap * sl / tot)
    return px


ORPHAN_MAX_CHARS = 2       # 折り返したセルの最終行がこの文字数以下なら「泣き別れ」（「…デス/ク」「…適/用」）


def is_orphan_wrap(text, size, inner_w, bold=False, max_chars: int = ORPHAN_MAX_CHARS) -> bool:
    """セルの文が 2 行以上に折れ、最終行が 1〜2 字だけになるか（core-A-01）。"""
    lines = ja_text.wrap_lines(text, size, inner_w, None, bold)
    return len(lines) >= 2 and 0 < len(lines[-1].strip()) <= max_chars


def _col_state(cells, w, pad_x, max_lines):
    """列幅 w のときの (行数超過のセル数, 泣き別れのセル数)。cells は (文, サイズ, 太字) の配列。"""
    inner = max(1.0, w - 2 * pad_x)
    over = orph = 0
    for t, sz, b in cells:
        lines = ja_text.wrap_lines(t, sz, inner, None, b)
        if len(lines) > max_lines:
            over += 1
        if len(lines) >= 2 and 0 < len(lines[-1].strip()) <= ORPHAN_MAX_CHARS:
            orph += 1
    return over, orph


def _relieve_orphans(columns, rows, px, floors, size, header_size, pad_x, strong_cols, strong_rows, max_lines):
    """最終行が 1〜2 字だけになるセルのある列を少し広げ、余裕のある列から幅をもらう（最大 +30%、1 回に 4px 刻み）。
    もらう側の列で「行数超過・泣き別れ」が増えるなら取らない。直せない列はそのまま（高さ側の候補選びが吸収する）。"""
    n = len(columns)
    cells = []
    for j in range(n):
        cj = [(str(columns[j]), header_size, True)]
        for i, row in enumerate(rows):
            if j < len(row):
                cj.append((cell_text(row[j]), size, (j in strong_cols) or (i in strong_rows) or _toned(row[j])))
        cells.append(cj)
    px = list(px)
    state = [_col_state(cells[j], px[j], pad_x, max_lines) for j in range(n)]
    STEP = 4.0
    for _ in range(40):
        bad = [j for j in range(n) if state[j][1] > 0]
        if not bad:
            break
        progressed = False
        for j in bad:
            w0, s0 = px[j], state[j]
            for k in range(1, 9):
                w1 = w0 + STEP * k
                if w1 > w0 * 1.3 + 0.01:
                    break
                s1 = _col_state(cells[j], w1, pad_x, max_lines)
                if s1[1] >= s0[1] or s1[0] > s0[0]:
                    continue
                # 取る列: 状態を悪くせず、床より広い列のうち、いちばん余裕のある列から
                took = False
                donors = sorted((d for d in range(n) if d != j and px[d] - floors[d] >= w1 - w0 + 1.0),
                                key=lambda d: floors[d] - px[d])
                for d in donors:
                    sd = _col_state(cells[d], px[d] - (w1 - w0), pad_x, max_lines)
                    if sd[0] <= state[d][0] and sd[1] <= state[d][1]:
                        px[d] -= (w1 - w0)
                        px[j] = w1
                        state[d], state[j] = sd, s1
                        took = progressed = True
                        break
                if took:
                    break
        if not progressed:
            break
    return px


def _table_orphans(columns, rows, widths, size, header_size, pad_x, strong_cols, strong_rows) -> int:
    """最終行が 1〜2 字だけになるセルの数。"""
    inner = [max(1.0, w - 2 * pad_x) for w in widths]
    n = 0
    for i, row in enumerate(rows):
        for j, v in enumerate(row[:len(columns)]):
            strong = (j in strong_cols) or (i in strong_rows) or _toned(v)
            if is_orphan_wrap(cell_text(v), size, inner[j], strong):
                n += 1
    return n


def _table_lines(columns, rows, widths, size, header_size, pad_x, strong_cols, strong_rows):
    """各行の最大行数 [..] と、ヘッダの行数。"""
    inner = [max(1.0, w - 2 * pad_x) for w in widths]
    hl = max((ja_text.estimate_lines(c, header_size, inner[j], None, True) for j, c in enumerate(columns)), default=1)
    ls = []
    for i, row in enumerate(rows):
        best = 1
        for j, v in enumerate(row[:len(columns)]):
            strong = (j in strong_cols) or (i in strong_rows) or _toned(v)
            best = max(best, ja_text.estimate_lines(cell_text(v), size, inner[j], None, strong))
        ls.append(best)
    return ls, hl


TABLE_FIT_TOL = 2.0        # 表の高さの収まり判定の許容（px。フッターとの間に 18px の余白があるので見た目に影響しない）
TABLE_ROW_BORDER = 1.0     # HTML の表は行ごとの下罫線（border-collapse の 1px）ぶん 1 行が高くなる（core-C-03）


def _solve_heights(hdr_need, hdr_pref, hdr_fixed, row_pref, row_min, row_fixed, needs, avail):
    """行高を決める。まず希望の高さ（既定の header_h・row_h）で収まるならそれ。収まらなければ、ヘッダを内容の高さまで、
    行を row_min まで縮めて、収まる最大の row_h を探す。戻り値 (header_h, row_h, total, fits)。"""
    hdr = max(hdr_pref, hdr_need)
    rp = max(row_pref, row_min)

    def total(h, r):
        return h + sum(max(r, nd) + TABLE_ROW_BORDER for nd in needs)

    if total(hdr, rp) <= avail + 0.01:
        # 折り返す行があるときは、全行の高さをそろえる（一番高い行に合わせる）。収まらなければ従来の希望の高さ
        ru = max([rp] + list(needs))
        if not row_fixed and total(hdr, ru) <= avail + 0.01:
            return hdr, ru, total(hdr, ru), True
        return hdr, rp, total(hdr, rp), True
    if not hdr_fixed:
        hdr = hdr_need if hdr_need < hdr else hdr
    if row_fixed:
        return hdr, rp, total(hdr, rp), total(hdr, rp) <= avail + 0.01
    lo, hi = row_min, rp
    if total(hdr, lo) > avail + 0.01:
        return hdr, lo, total(hdr, lo), False
    for _ in range(30):
        mid = (lo + hi) / 2
        if total(hdr, mid) <= avail + 0.01:
            lo = mid
        else:
            hi = mid
    r = int(lo * 10) / 10.0
    return hdr, r, total(hdr, r), True


def fit_table_layout(columns, rows, rect, bottom, params, fixed, strong_cols=(), strong_rows=(), adjust=True):
    """表の文字サイズ・列幅・行高を決める純関数（HTML・PPTX 共通）。

    rect: {"x","y","w"}（表の左上と幅。合成スライドでは小さい矩形を渡す）。bottom: 表の下端の y。
    params: cell_size（上限）, header_size, header_h, row_h, line_height, pad_x, pad_y, col_widths（None なら自動）,
            min_size, max_lines（セルの最大行数。既定 2）, wrap_ratio（2 行以上に折れる行の割合の上限。既定 0.7）。
    fixed: 動かさないキーの集合（cell_size / header_size / header_h / row_h / pad_y / col_widths）。
    戻り値: {size, header_size, header_h, row_h, pad_y, col_widths, auto_widths, lines(行ごと), header_lines,
             total_h, avail, overflow, fits, strict, rows_fit, cap}"""
    cap = params["cell_size"]
    hs_cap = params["header_size"]
    hs_off = hs_cap - cap
    lh = params["line_height"]
    pad_x = params["pad_x"]
    W = rect["w"]
    avail = bottom - rect["y"]
    given = params.get("col_widths")
    if given and (len(given) != len(columns) or any(not isinstance(w, (int, float)) for w in given)):
        given = None
    if given and sum(given) > 0:
        unit = W / sum(given)
        given_px = [_px(w * unit) for w in given]
    else:
        given_px = None
    if "col_widths" in fixed and not given_px:
        given_px = None
    min_size = params.get("min_size", 12)
    max_lines = params.get("max_lines", 2)
    wrap_ratio = params.get("wrap_ratio", 0.7)

    if "cell_size" in fixed or not adjust or cap <= min_size:
        sizes = [cap]
    else:
        sizes = list(range(int(cap), int(min_size) - 1, -1)) or [cap]
    pads = [params["pad_y"]]
    if "pad_y" not in fixed and adjust and params["pad_y"] > MIN_PAD_Y:
        pads.append(MIN_PAD_Y)

    n = len(rows)
    search = n <= TABLE_SEARCH_MAX_ROWS           # 行の多い表は、列幅の回し直し・泣き別れ回避の探索を省く（行数の 2 乗に近い時間がかかる。警告は従来どおり出る）

    def evaluate(size):
        hsz = hs_cap if "header_size" in fixed else size + hs_off
        widths = given_px or table_column_widths(columns, rows, size, hsz, W, pad_x, strong_cols, strong_rows,
                                                 max_lines=max_lines if search else 0)
        ls, hl = _table_lines(columns, rows, widths, size, hsz, pad_x, strong_cols, strong_rows)
        multi = sum(1 for l in ls if l >= 2) / n if n else 0.0
        orph = _table_orphans(columns, rows, widths, size, hsz, pad_x, strong_cols, strong_rows) if search else 0
        strict_ok = (max(ls, default=1) <= max_lines and hl <= 2 and multi <= wrap_ratio + 1e-9 and orph == 0)
        out = []
        for pad in pads:
            hdr_need = hl * hsz * lh + 2 * pad
            needs = [l * size * lh + 2 * pad for l in ls]
            row_min = size * lh + 2 * pad
            hdr, r, total, fits = _solve_heights(
                hdr_need, params["header_h"], "header_h" in fixed or not adjust,
                params["row_h"], row_min, "row_h" in fixed or not adjust, needs, avail + TABLE_FIT_TOL)   # 丸めの許容（罫線を数えるため）
            out.append({"size": size, "header_size": hsz, "header_h": hdr, "row_h": r, "pad_y": pad,
                        "col_widths": widths, "auto_widths": given_px is None, "lines": ls, "header_lines": hl,
                        "max_lines": max(ls, default=1), "orphans": orph,
                        "total_h": total, "fits": fits, "strict": strict_ok, "needs": needs})
        return out

    cands = [c for s in sizes for c in evaluate(s)]
    # 段階的に条件をゆるめる: (1) 高さに収まり、折り返しも控えめ → (2) 高さに収まり、セルは max_lines 行まで
    # → (3) 高さに収まる（3 行以上に折れるセルを許す）→ (4) 下限まで縮めても入らない
    strict = next((c for c in cands if c["fits"] and c["strict"]), None)
    lines_ok = next((c for c in cands if c["fits"] and c["max_lines"] <= max_lines and c["header_lines"] <= 2), None)
    if strict and lines_ok and strict["size"] < lines_ok["size"] - 2:
        strict = None       # 折り返しの割合を減らすための縮小は 2px まで（それ以上は読みやすさより大きさを優先）
    pick = strict or lines_ok or next((c for c in cands if c["fits"]), None)
    if pick is None:
        pick = cands[-1]          # 下限まで縮めても入らない: 最小サイズ・最小余白で返す
    pick = dict(pick)
    pick["avail"] = avail
    pick["overflow"] = max(0.0, pick["total_h"] - avail - TABLE_FIT_TOL)     # 丸め・罫線の許容（_solve_heights と同じ）
    pick["cap"] = cap
    # 何行目まで入るか（警告の「M 行以下に減らす」用）
    acc = pick["header_h"]
    k = 0
    for nd in pick["needs"]:
        h = max(pick["row_h"], nd) + TABLE_ROW_BORDER
        if acc + h > avail + 0.01:
            break
        acc += h
        k += 1
    pick["rows_fit"] = k
    pick.pop("needs", None)
    return pick


TABLE_FIXED_KEYS = ("cell_size", "header_size", "header_h", "row_h", "pad_y", "col_widths")


def thin_table(ctx: Ctx, tr: dict, res: dict, fixed, n: int, params: dict) -> None:
    """行数が少なく下が空くとき（talk の表など）: 行の高さを上限（table.stretch_row_h_max）まで広げ、それでも余るなら
    領域の中で縦中央（table.thin_valign: "middle"）に置く。cards の薄い箱（thin_box）と同じ考え方。
    値はレイアウト JSON の表の領域（density ごとに持てる）。利用者が row_h / y を書いたとき・自動フィットを切ったときは動かさない。"""
    rmax = tr.get("stretch_row_h_max")
    if not ctx.adjust or not n or not isinstance(rmax, (int, float)) or isinstance(rmax, bool) or res["overflow"] > 0 or not res.get("fits", True):
        return
    size, pad, lh = res["size"], res["pad_y"], params["line_height"]
    needs = [ls * size * lh + 2 * pad for ls in res["lines"]]
    hdr, row_h, avail = res["header_h"], res["row_h"], res["avail"]
    if "row_h" not in fixed and not ctx.explicit("table", "row_h") and rmax > row_h:
        def total(r):
            return hdr + sum(max(r, nd) + TABLE_ROW_BORDER for nd in needs)
        r = row_h
        while r + 1 <= rmax and total(r + 1) <= avail:
            r += 1
        if r > row_h:
            ctx.set("table", "row_h", _px(r))
            row_h = r
    used = hdr + sum(max(row_h, nd) + TABLE_ROW_BORDER for nd in needs)
    spare = avail - used
    if tr.get("thin_valign", "middle") == "middle" and spare >= 24 and not ctx.explicit("table", "y"):
        ctx.set("table", "y", round(tr.get("y", 192) + spare / 2, 1))
    ctx.info["table"]["thin"] = {"row_h": row_h, "spare": round(spare, 1)}


def _thin_grow_table(ctx: Ctx, tr: dict, cols, rows, bottom, params, fixed, strong_cols, strong_rows, res):
    """表ブロックの行が少なく枠が余るとき（表の高さが枠の thin_trigger 割未満）、セルの文字を大きくした fit_table_layout の結果と倍率。
    thin_max_size を超えない・折り返し（行数・泣き別れ）が増えない・枠に収まる、の範囲で最大のもの。大きくしないとき None。"""
    gp = thin_grow_params(tr)
    if gp is None or not ctx.adjust or "cell_size" in fixed or res["size"] < res["cap"] or res["overflow"] > 0:
        return None
    grow, mx, trig = gp
    cap = res["cap"]
    if res["avail"] <= 0 or res["total_h"] >= res["avail"] * trig:
        return None
    top = int(min(round(cap * grow), mx))
    rect = {"x": tr.get("x", 72), "y": tr.get("y", 192), "w": tr.get("w", 1136)}
    for size in range(top, int(cap), -1):
        p2 = {**params, "cell_size": size, "header_size": params["header_size"] + (size - cap)}
        r2 = fit_table_layout(cols, rows, rect, bottom, p2, fixed, strong_cols, strong_rows, adjust=ctx.adjust)
        if (r2["size"] == size and r2["overflow"] <= 0 and r2["fits"] and max(r2["lines"], default=1) <= max(res["lines"], default=1)
                and r2["header_lines"] <= res["header_lines"] and r2.get("orphans", 0) <= res.get("orphans", 0)):
            return r2, round(size / cap, 3)
    return None


@fitter("table")
def _fit_table(ctx: Ctx) -> None:
    tr = ctx.st.get("table")
    cols = ctx.slide.get("columns")
    if not isinstance(tr, dict) or not isinstance(cols, list) or not cols or not isinstance(ctx.slide.get("rows"), list):
        return
    cw = tr.get("col_widths")
    if cw is not None and not (isinstance(cw, list) and len(cw) == len(cols) and
                               all(isinstance(w, (int, float)) and not isinstance(w, bool) and w >= 0 for w in cw)):
        return      # col_widths の形が不正: 自動フィットは飛ばし、検証（_check_col_widths）に明快なエラーを任せる
    rows, emph = table_rows(ctx.slide)
    fixed = {k for k in TABLE_FIXED_KEYS if ctx.fixed("table", k)}
    # レイアウト・density が col_widths を持っているときも、そのまま使う（自動で上書きしない）
    if tr.get("col_widths"):
        fixed.add("col_widths")
    strong_cols = (0,) if ctx.slide.get("row_header") else ()
    strong_rows = set(emph)
    if ctx.slide.get("total_row") and rows:
        strong_rows.add(len(rows) - 1)
    strong_rows = tuple(sorted(strong_rows))
    params = {k: tr[k] for k in ("cell_size", "header_size", "header_h", "row_h", "line_height", "pad_x", "pad_y") if k in tr}
    if len(params) < 7:
        return
    params["col_widths"] = tr.get("col_widths")
    for k, d in (("min_size", 12), ("max_lines", 2), ("wrap_ratio", 0.7)):
        params[k] = tr.get(k, d)
    bottom = ctx.content_bottom("table")
    res = fit_table_layout(cols, rows, {"x": tr.get("x", 72), "y": tr.get("y", 192), "w": tr.get("w", 1136)},
                           bottom, params, fixed, strong_cols, strong_rows, adjust=ctx.adjust)
    grown_f = None
    if thin_participates(tr):
        grown = _thin_grow_table(ctx, tr, cols, rows, bottom, params, fixed, strong_cols, strong_rows, res)
        grown_f = 1.0
        if grown:
            res, grown_f = grown
    ctx.info["table"] = {k: res[k] for k in ("size", "header_size", "header_h", "row_h", "pad_y", "col_widths",
                                              "auto_widths", "total_h", "avail", "overflow", "rows_fit", "cap")}
    if grown_f is not None:
        ctx.info["thin_factor"] = grown_f
        if grown_f > 1.0:
            ctx.info["table"]["grown"] = grown_f
    ctx.info["table"]["adjusted"] = bool(ctx.adjust)
    ctx.info["table"]["lines"] = res["lines"]
    ctx.info["table"]["header_lines"] = res["header_lines"]
    ctx.info["table"]["max_lines"] = max(res["lines"], default=1)
    ctx.info["table"]["orphans"] = res.get("orphans", 0)
    for key, v in (("cell_size", res["size"]), ("header_size", res["header_size"]), ("header_h", _px(res["header_h"])),
                   ("row_h", _px(res["row_h"])), ("pad_y", res["pad_y"])):
        if key not in fixed and v != tr.get(key):
            ctx.set("table", key, v)
    if res["auto_widths"] and "col_widths" not in fixed:
        ctx.set("table", "col_widths", res["col_widths"])
        ctx.set("table", "_auto_widths", True)
    n = len(rows)
    thin_table(ctx, tr, res, fixed, n, params)
    cwid = res["col_widths"]
    words = [(cell_text(c), res["size"], cwid[j] - 2 * params["pad_x"], "セル")
             for r in rows for j, c in enumerate(r[:len(cwid)])]
    words += [(str(c), res["header_size"], cwid[j] - 2 * params["pad_x"], "見出しセル") for j, c in enumerate(cols[:len(cwid)])]
    long_word_check(ctx, words)
    shrunk = cap_minus = res["cap"] - res["size"]
    if res["overflow"] > 12:
        explicit_size = "cell_size" in fixed
        m = res["rows_fit"]
        if explicit_size:
            ctx.warn("table-overflow",
                     f"{{label}}: 表が枠の高さを約{int(res['overflow'])}px超える見込みです"
                     f"（{n}行・文字 {res['size']}px のまま）→ 行を {m} 行以下に減らすか 2 枚に分ける、"
                     f"または style.table.cell_size / row_h を下げる{ctx.undo_hint()}")
        else:
            ctx.warn("table-overflow",
                     f"{{label}}: 表は {res['size']}px まで縮めても約{int(res['overflow'])}px はみ出します"
                     f"（{n}行）→ 行を {m} 行以下に減らすか 2 枚に分ける（セルの文字を短くする・列を減らすのも有効）")
    elif shrunk >= 2 and "cell_size" not in fixed:
        ctx.note("table-shrunk",
                 f"{{label}}: 表の文字を {res['cap']}px → {res['size']}px に縮めました（{n}行・列幅と行高も自動調整）"
                 f" → 大きく読ませたいときは行を減らすか 2 枚に分ける")
    if res.get("orphans", 0) and res["overflow"] <= 12:
        ctx.note("table-orphan",
                 f"{{label}}: 表のセル {res['orphans']} 個で、折り返した最終行が 1〜2 字だけになります"
                 f" → 該当セルの文を少し短くするか、列幅（style.table.col_widths）を調整する")
    big = max(res["lines"], default=1)
    if big >= 3 and res["overflow"] <= 12:
        cnt = sum(1 for x in res["lines"] if x >= 3)
        ctx.note("table-wrap3",
                 f"{{label}}: 表のセルが 3 行以上に折れる行が {cnt} 行あります → 該当セルの文字を短くするか、列を減らす")


# ---------------------------------------------------------------------------
# 結論帯（conclusion）と出典（source）: 全タイプ共通の下端パーツ
# ---------------------------------------------------------------------------

CONCLUSION_LH = 1.2 * 1.15     # proposal_engine.LINE_H * PARA_LH（結論帯の 1 行の高さ = 文字サイズ × これ）
SOURCE_LH = 1.2                # 出典の 1 行（lh=1.0）
BAND_W = 1136                  # 結論帯・出典の幅（本文と同じ）
BAND_PAD_X = 16                # 結論帯の左右の内側余白（pe.common_parts の insets）
BAND_PAD_Y = 2


def fit_band(text, width, box_h, cap, floor, grow_to):
    """結論帯の文字サイズ。まず帯の高さ box_h の中で cap → floor に縮め、入らなければ帯を grow_to まで高くして探す。
    戻り値 {size, h, lines, fits}（h は帯の高さ。変えないときは box_h）。"""
    sizes = [cap] + [x for x in range(int(cap) - 1 if cap == int(cap) else int(cap), int(floor) - 1, -1) if x < cap]
    for s_ in sizes:
        lines = ja_text.estimate_lines(text, s_, width, ja_text.heading_fonts(), True)
        if lines * s_ * CONCLUSION_LH + 2 * BAND_PAD_Y <= box_h + 0.5:
            return {"size": s_, "h": box_h, "lines": lines, "fits": True}
    for s_ in sizes:
        lines = ja_text.estimate_lines(text, s_, width, ja_text.heading_fonts(), True)
        need = lines * s_ * CONCLUSION_LH + 2 * BAND_PAD_Y
        if need <= grow_to + 0.5:
            return {"size": s_, "h": int(need + 0.999), "lines": lines, "fits": True}
    s_ = sizes[-1]
    lines = ja_text.estimate_lines(text, s_, width, ja_text.heading_fonts(), True)
    return {"size": s_, "h": box_h, "lines": lines, "fits": False, "need": lines * s_ * CONCLUSION_LH + 2 * BAND_PAD_Y}


def _band_width(ctx: Ctx) -> float:
    """結論帯・出典の幅。split はパネルの残りの幅（proposal_engine.extras が body の x / w に置く）、それ以外は全幅。"""
    if ctx.type == "split":
        b = ctx.st.get("body")
        if isinstance(b, dict) and isinstance(b.get("w"), (int, float)) and b["w"] > 0:
            return b["w"]
    return BAND_W


def _bottom_parts_fit(ctx: Ctx) -> None:
    """結論帯の文字が帯に収まる大きさに縮める（帯が低すぎれば高くする）。出典が 2 行以上になるなら高さを確保する。
    以前は長い結論が帯の外にあふれ、長い出典はフッターに重なっていた（A8-11 / A8-10）。"""
    import proposal_engine as pe
    if ctx.type in pe.NO_BOTTOM_PARTS or _full_pattern(ctx):
        return
    cb = ctx.st.get("conclusion")
    text = ctx.slide.get("conclusion")
    if isinstance(cb, dict) and isinstance(text, str) and text:
        cap = cb.get("size", 17)
        h = cb.get("h", 40)
        fixed_size = ctx.fixed("conclusion", "size")
        floor = cap if fixed_size else min(cb.get("min_size", 13), cap)
        grow = h if ctx.fixed("conclusion", "h") else cb.get("max_h", 72)
        res = fit_band(text, _band_width(ctx) - 2 * BAND_PAD_X, h, cap, floor, max(grow, h))
        ctx.info["conclusion"] = {"size": res["size"], "h": res["h"], "lines": res["lines"], "cap": cap}
        if res["fits"]:
            if res["size"] != cap:
                ctx.set("conclusion", "size", res["size"])
            if res["h"] != h:
                ctx.set("conclusion", "h", res["h"])
            if cap - res["size"] >= 2 or res["h"] != h:
                ctx.note("conclusion-shrunk",
                         f"{{label}}: 結論の文が長いので帯の文字を {cap}px → {res['size']}px"
                         f"{'、帯の高さを ' + str(h) + 'px → ' + str(res['h']) + 'px' if res['h'] != h else ''}にしました"
                         f"（{len(text)}字）→ 帯には 1 行で言い切れる短い結論を置く")
        else:
            over = int(res["need"] - h)
            if not fixed_size:
                ctx.set("conclusion", "size", res["size"])
            ctx.warn("conclusion-overflow",
                     f"{{label}}: 結論の帯に文字が収まりません（{res['size']}px でも{res['lines']}行・帯より約{over}px高い）"
                     f"（{len(text)}字）→ 結論を短くする（帯に置くのは 1〜2 行。長い説明は本文か lead に回す）"
                     f"{'。split は帯の幅がパネルの残りしかないので、ratio を下げて本文側を広げる手もある' if ctx.type == 'split' else ''}")
    sr = ctx.st.get("source")
    src = ctx.slide.get("source")
    if isinstance(sr, dict) and isinstance(src, str) and src:
        size = sr.get("size", 12)
        lines = ja_text.estimate_lines(src, size, _band_width(ctx), None, False)
        need = lines * size * SOURCE_LH
        h = sr.get("h", 18)
        ctx.info["source"] = {"lines": lines}
        if need > h + 1:
            new_h = int(need + 0.999)
            ctx.set("source", "h", new_h)
            ctx.set("source", "reserve", max(sr.get("reserve", 20), new_h + 2))
        if lines >= 3:
            ctx.warn("source-long",
                     f"{{label}}: 出典が{lines}行になります（{len(src)}字）→ 出典は 1〜2 行に収める（前提の長い説明は notes か本文へ）")


# ---------------------------------------------------------------------------
# 箇条書き（bullets / closing / image_text / two_column）
# ---------------------------------------------------------------------------

def norm_items(items):
    """bullets 配列を正規化。要素は文字列 or {text, children, size, color, bold}。"""
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append({"text": it, "children": []})
        else:
            d = dict(it)
            d.setdefault("text", "")
            kids = []
            for c in d.get("children") or []:
                kid = {"text": c} if isinstance(c, str) else dict(c)
                kid.setdefault("text", "")
                kids.append(kid)
            d["children"] = kids
            out.append(d)
    return out


def bullets_height(items, r: dict) -> float:
    """箇条書き（親＋子）を描いたときのおおよその高さ（px。各項目の下の間隔を含む）。
    items は norm_items 前後どちらでもよい。子の幅は HTML の入れ子リストの字下げ（indent-6）を引いて測る。"""
    items = norm_items(items)
    size = r.get("size", 16)
    lh = r.get("line_height", 1.4)
    gap = r.get("gap", 10)
    indent = r.get("indent", 30)
    width = max(10.0, r.get("w", 400) - indent)
    child_size = r.get("child_size", max(10, size - 3))
    child_gap = r.get("child_gap", 6)
    child_width = max(10.0, width - (indent - 6))
    total = 0.0
    for it in items:
        isize = it.get("size", size)
        total += ja_text.estimate_lines(it.get("text", ""), isize, width) * isize * lh + gap
        for c in it.get("children", []):
            csize = c.get("size", child_size)
            total += ja_text.estimate_lines(c.get("text", ""), csize, child_width) * csize * lh + child_gap
    return total


def bullets_line_counts(items, r: dict, safety: float = 1.0) -> list:
    """箇条書き（親＋子）の各文の行数（描く順）。bullets_height と同じ幅・文字サイズで測る。
    safety < 1 は幅を狭めて測る（見積もりより早く折れるブラウザ・PowerPoint を見込む。文字を大きくしてよいかの判定用）。"""
    items = norm_items(items)
    size = r.get("size", 16)
    indent = r.get("indent", 30)
    width = max(10.0, (r.get("w", 400) - indent) * safety)
    child_size = r.get("child_size", max(10, size - 3))
    child_width = max(10.0, width - (indent - 6))
    out = []
    for it in items:
        out.append(ja_text.estimate_lines(it.get("text", ""), it.get("size", size), width))
        for c in it.get("children", []):
            out.append(ja_text.estimate_lines(c.get("text", ""), c.get("size", child_size), child_width))
    return out


WRAP_TAIL_MIN = 3             # 文字を大きくした結果、最終行がこれ未満の字数になる（泣き別れ）のは避ける


def wrap_profile(text, size, width, font=None, bold: bool = False) -> tuple:
    """折り返したときの (行数, 最終行の字数, 語の途中で折れた回数)。語の途中 = ja_text.good_break でない位置の折り返し。
    文字を大きくしてよいかの判定（折り返しの質が悪くならないか）に使う。"""
    text = str(text or "")
    ls = ja_text.wrap_lines(text, size, max(1.0, width), font, bold)
    if len(ls) <= 1:
        return 1, len(text.strip()), 0
    pos, bad = 0, 0
    for ln in ls[:-1]:
        pos += len(ln)
        while pos < len(text) and text[pos] == " ":
            pos += 1
        if 0 < pos < len(text) and not ja_text.good_break(text, pos):
            bad += 1
    return len(ls), len((ls[-1] or "").strip()), bad


def wrap_not_worse(base: tuple, cand: tuple) -> bool:
    """文字を大きくした折り返し cand が、いまの折り返し base より悪くならないか。
    行数が増えない・語の途中の折れが増えない・最終行が 3 字未満に（それまで 3 字以上だったのが）ならない。"""
    if cand[0] > base[0] or cand[2] > base[2]:
        return False
    if cand[0] > 1 and cand[1] < WRAP_TAIL_MIN and not (base[0] > 1 and base[1] <= cand[1]):
        return False
    return True


def bullets_wrap_profiles(items, r: dict, safety: float = 1.0) -> list:
    """箇条書き（親＋子）の各文の wrap_profile（描く順）。bullets_line_counts と同じ幅・文字サイズで測る。"""
    items = norm_items(items)
    size = r.get("size", 16)
    indent = r.get("indent", 30)
    width = max(10.0, (r.get("w", 400) - indent) * safety)
    child_size = r.get("child_size", max(10, size - 3))
    child_width = max(10.0, width - (indent - 6))
    out = []
    for it in items:
        out.append(wrap_profile(it.get("text", ""), it.get("size", size), width))
        for c in it.get("children", []):
            out.append(wrap_profile(c.get("text", ""), c.get("size", child_size), child_width))
    return out


def bullets_visible_height(items, r: dict) -> float:
    """末尾の余白（最後の項目の下の間隔）を除いた、目に見える高さ。枠に収まるかの判定に使う。"""
    items = norm_items(items)
    if not items:
        return 0.0
    tail = r.get("gap", 10) + (r.get("child_gap", 6) if items[-1]["children"] else 0)
    return max(0.0, bullets_height(items, r) - tail)


def scaled_bullets(base: dict, size, cap, fixed=()) -> dict:
    """本文を size に縮めたときの箇条書きの値。子の文字・間隔は size/cap に比例して詰める（明示値 fixed は動かさない）。"""
    r = dict(base)
    r["size"] = size
    if size == cap:
        return r
    f = size / cap
    if "child_size" not in fixed and "child_size" in base:
        r["child_size"] = max(11, round(base["child_size"] * f))
    if "gap" not in fixed and "gap" in base:
        r["gap"] = max(4, round(base["gap"] * f))
    if "child_gap" not in fixed and "child_gap" in base:
        r["child_gap"] = max(3, round(base["child_gap"] * f))
    return r


def size_candidates(cap, floor, fixed=False) -> list:
    """cap から floor まで 1px 刻みの候補（大きい順）。fixed なら cap だけ。"""
    out = [cap]
    if fixed or floor >= cap:
        return out
    x = int(cap) - 1 if cap == int(cap) else int(cap)
    while x >= floor:
        out.append(x)
        x -= 1
    return out


def items_that_fit(items, r: dict, avail: float) -> int:
    """先頭から何項目まで枠（avail px）に収まるか。"""
    items = norm_items(items)
    k = 0
    for i in range(1, len(items) + 1):
        if bullets_visible_height(items[:i], r) <= avail + 0.5:
            k = i
        else:
            break
    return k


def fit_bullets(items, base: dict, avail: float, floor, fixed=(), adjust=True, extra=0.0) -> dict:
    """箇条書きの文字サイズを cap(base.size) から floor まで下げて、avail に収まる最大のサイズを返す純関数。
    base: size / child_size / gap / child_gap / line_height / indent / w。extra: 箇条書きの上に積む高さ（見出しなど）。
    戻り値 {size, params, need, avail, fits, over, cap, items_fit}。"""
    cap = base.get("size", 16)
    size_fixed = "size" in fixed or not adjust
    last = None
    for s_ in size_candidates(cap, floor, size_fixed):
        r = scaled_bullets(base, s_, cap, fixed)
        need = bullets_visible_height(items, r) + extra
        last = {"size": s_, "params": {k: r[k] for k in ("size", "child_size", "gap", "child_gap") if k in r},
                "need": need, "avail": avail, "fits": need <= avail + 0.5, "over": max(0.0, need - avail), "cap": cap}
        if last["fits"]:
            last["items_fit"] = len(norm_items(items))
            return last
    last["items_fit"] = items_that_fit(items, scaled_bullets(base, last["size"], cap, fixed), avail - extra)
    return last


def bullets_word_entries(items, r: dict, width: float, where: str) -> list:
    """箇条書き（親＋子）の各文を long_word_check に渡す形にする。r は size / child_size / indent を持つ値。"""
    ind = r.get("indent", 30)
    out = []
    for it in norm_items(items):
        out.append((it["text"], it.get("size", r.get("size", 16)), width - ind, where))
        for c in it["children"]:
            out.append((c["text"], c.get("size", r.get("child_size", 13)), width - ind - (ind - 6), where))
    return out


def _bullets_msgs(ctx: Ctx, name: str, region: str, res: dict, n_items: int, fixed_size: bool, shrunk_ok=True) -> None:
    """箇条書きのフィット結果を警告・注記にする。"""
    cap, size = res["cap"], res["size"]
    if res["fits"]:
        if size < cap and cap - size >= 2 and shrunk_ok:
            ctx.note(f"{region}-shrunk",
                     f"{{label}}: {name}の文字を {cap}px → {size}px に縮めました（{n_items}項目）"
                     f" → 大きく読ませたいときは項目を減らすか 2 枚に分ける")
        return
    over = int(res["over"])
    if over <= 6:
        return          # 見積もりの誤差の範囲
    m = res.get("items_fit", 0)
    hint = f"項目を {m} 個以下に減らすか、2 枚に分ける" if m else "文を短くするか、2 枚に分ける"
    if fixed_size:
        ctx.warn(f"{region}-overflow",
                 f"{{label}}: {name}が枠の高さを約{over}px超える見込みです（{ctx.by_spec(f'style の size={cap}')}・{n_items}項目）"
                 f" → {hint}、または size を下げる{ctx.undo_hint()}")
    else:
        ctx.warn(f"{region}-overflow",
                 f"{{label}}: {name}は {size}px まで縮めても枠の高さを約{over}px超えます（{n_items}項目）"
                 f" → {hint}（文を短くするのも有効）")


def _apply_bullets(ctx: Ctx, region: str, res: dict, fixed: set) -> None:
    for k, v in res["params"].items():
        if k not in fixed and v != ctx.val(region, k):
            ctx.set(region, k, v)


# ---------------------------------------------------------------------------
# 合成ブロックの「中身が少ないとき」: 文字を大きくする（S4）
# ---------------------------------------------------------------------------
# ブロックの矩形は格子が決める（利用者の明示ではない）。矩形に block_rect: true が付いているときだけ働く。
# 値は領域のトークン: thin_grow（上限の倍率）・thin_max_size（px の上限＝読み上げ資料の標準サイズ）・thin_trigger（中身が枠の何割未満なら大きくするか）。
# thin_limit は resolve_composite_blocks が、同じスライドの同じ種類のブロックで倍率をそろえるために渡す上限（1.0 なら大きくしない）。

THIN_GROW_CAP = 4.0           # thin_grow の上限（倍）
THIN_SIZE_CAP = 200.0         # thin_max_size の上限（px）


def thin_grow_params(r: dict):
    """領域 r の thin_grow / thin_max_size / thin_trigger / thin_limit → (倍率の上限, px の上限, 割合) 。大きくしないなら None。"""
    if not isinstance(r, dict) or not r.get("block_rect"):
        return None
    g = r.get("thin_grow")
    if not isinstance(g, (int, float)) or isinstance(g, bool) or g <= 1.0:
        return None
    g = min(g, THIN_GROW_CAP)               # 極端な値で 1px ずつの探索が終わらなくならないよう頭打ちにする（s4-C-03。検証は deck_schema.TOKEN_RANGES）
    lim = r.get("thin_limit")
    if isinstance(lim, (int, float)) and not isinstance(lim, bool):
        g = min(g, lim)
    if g <= 1.02:
        return None
    mx = r.get("thin_max_size")
    mx = min(float(mx), THIN_SIZE_CAP) if isinstance(mx, (int, float)) and not isinstance(mx, bool) and mx > 0 else THIN_SIZE_CAP
    trig = r.get("thin_trigger", 0.6)
    trig = float(trig) if isinstance(trig, (int, float)) and not isinstance(trig, bool) else 0.6
    return g, mx, trig


THIN_WRAP_SAFETY = 0.93       # 大きくしてよいかの判定で、行の幅をこの割合に狭めて測る
WRAP_CHECK_SAFETIES = (1.0, THIN_WRAP_SAFETY)      # 折り返しの質の判定は、実幅と狭めた幅の両方で行う（ブラウザの折り返しは見積もりとずれる）


def thin_participates(r: dict) -> bool:
    """この領域は「中身が少ないとき文字を大きくする」の対象か（ブロックの矩形で、thin_grow が 1 より大きい）。
    対象のブロックは info["thin_factor"]（実際に大きくした倍率。大きくしなければ 1.0）を残し、同じ種類のブロックの倍率をそろえるのに使う。"""
    g = r.get("thin_grow") if isinstance(r, dict) else None
    return bool(isinstance(r, dict) and r.get("block_rect") and isinstance(g, (int, float)) and not isinstance(g, bool) and g > 1.0)


def _thin_grow_bullets(ctx: Ctx, r: dict, items, res: dict, fixed, cap, avail):
    """bullets ブロックの中身が薄い（枠の thin_trigger 割未満）とき、文字を cap の thin_grow 倍まで大きくした結果（fit_bullets と同じ形）。大きくしないとき None。"""
    gp = thin_grow_params(r)
    if gp is None or not ctx.adjust or "size" in fixed or not res["fits"] or res["size"] < cap:
        return None
    grow, mx, trig = gp
    if avail <= 0 or res["need"] >= avail * trig:
        return None
    best = None
    top = int(min(cap * grow, mx))
    base_prof = bullets_wrap_profiles(items, scaled_bullets(r, res["size"], cap, fixed))      # いまの折り返し（実際に描かれる幅）
    for s_ in range(top, int(cap), -1):
        rr = scaled_bullets(r, s_, cap, fixed)
        need = bullets_visible_height(items, rr)
        # 大きくした結果、折り返さなかった項目が折れる・語の途中で折れる・最終行が 1〜2 字になるのは避ける（「ブロ／ック」を増やさない）
        if need <= avail * trig + 0.5 and all(wrap_not_worse(a, b) for sf in WRAP_CHECK_SAFETIES for a, b in zip(base_prof, bullets_wrap_profiles(items, rr, sf))):
            best = {"size": s_, "params": {k: rr[k] for k in ("size", "child_size", "gap", "child_gap") if k in rr},
                    "need": need, "avail": avail, "fits": True, "over": 0.0, "cap": cap, "items_fit": len(norm_items(items))}
            break
    return best


@fitter("bullets", "closing", "image_text")
def _fit_bullets_types(ctx: Ctx) -> None:
    r = ctx.st.get("body")
    items = ctx.slide.get("bullets")
    if not isinstance(r, dict) or not isinstance(items, list) or not items or "size" not in r:
        return
    fixed = {k for k in ("size", "child_size", "gap", "child_gap") if ctx.fixed("body", k)}
    cap = r["size"]
    floor = min(r.get("min_size") or max(12, round(cap * 0.7)), cap)
    avail = ctx.content_bottom("body") - r.get("y", 0)
    res = fit_bullets(items, r, avail, floor, fixed, ctx.adjust)
    ctx.info["body"] = {"size": res["size"], "need": round(res["need"], 1), "avail": round(avail, 1), "cap": cap,
                        "fits": res["fits"]}
    grown = _thin_grow_bullets(ctx, r, items, res, fixed, cap, avail)
    if grown:
        res = grown
        ctx.info["body"].update({"size": res["size"], "need": round(res["need"], 1), "grown": round(res["size"] / cap, 3)})
    if thin_participates(r):
        ctx.info["thin_factor"] = round(res["size"] / cap, 3) if grown else 1.0
    _apply_bullets(ctx, "body", res, fixed)
    _bullets_msgs(ctx, "本文", "body", res, len(items), "size" in fixed)
    long_word_check(ctx, bullets_word_entries(items, {**r, **res["params"]}, r.get("w", 400), "本文"))


TWO_COLUMN_HEAD_LH = 1.4     # build_deck._two_column_side_layout と同じ（見出し 1 行の高さ = size × これ）


def _two_col_need(side_box: dict, colc: dict, hd: dict, body: dict) -> float:
    """two_column の 1 サイド（見出し＋箇条書き）が箱の中で必要とする高さ（余白込み）。"""
    pad = side_box.get("pad", 0)
    inner_w = side_box.get("w", 400) - 2 * pad
    need = 2 * pad
    if colc.get("heading"):
        lines = ja_text.estimate_lines(colc["heading"], hd.get("size", 22), inner_w, ja_text.heading_fonts(), True)
        need += lines * hd.get("size", 22) * TWO_COLUMN_HEAD_LH + hd.get("gap_below", 12)
    if colc.get("bullets"):
        need += bullets_visible_height(colc["bullets"], {**body, "w": inner_w})
    return need


@fitter("two_column")
def _fit_two_column(ctx: Ctx) -> None:
    cb, hd = ctx.st.get("col_body"), ctx.st.get("col_heading")
    if not isinstance(cb, dict) or not isinstance(hd, dict) or "size" not in cb:
        return
    sides = []
    for name in ("left", "right"):
        box, colc = ctx.st.get(name), ctx.slide.get(name)
        if isinstance(box, dict) and isinstance(colc, dict) and (colc.get("bullets") or colc.get("heading")):
            sides.append((name, box, colc))
    if not sides:
        return
    fixed = {k for k in ("size", "child_size", "gap", "child_gap") if ctx.fixed("col_body", k)}
    hd_fixed = ctx.fixed("col_heading", "size")
    cap = cb["size"]
    floor = min(cb.get("min_size") or max(12, round(cap * 0.7)), cap)
    hd_cap = hd.get("size", 22)
    hd_floor = min(hd.get("min_size") or max(14, round(hd_cap * 0.75)), hd_cap)
    avails = {n: ctx.content_bottom(n) - b.get("y", 0) for n, b, _ in sides}
    chosen = None
    for s_ in size_candidates(cap, floor, "size" in fixed):
        body = scaled_bullets(cb, s_, cap, fixed)
        f = s_ / cap
        hsz = hd_cap if (hd_fixed or s_ == cap) else max(hd_floor, round(hd_cap * f))
        hgap = hd.get("gap_below", 12) if (hd_fixed or s_ == cap) else max(6, round(hd.get("gap_below", 12) * f))
        if not hd_fixed and ctx.density != "standard":
            # （talk / read のみ）見出しは 1 行に収まる大きさまで（下限まで）縮める。折れた見出しは「リリ／ース」のように泣き別れしやすい
            while hsz > hd_floor and any(c.get("heading") and ja_text.estimate_lines(
                    c["heading"], hsz, bx.get("w", 400) - 2 * bx.get("pad", 0), ja_text.heading_fonts(), True) > 1
                    for _, bx, c in sides):
                hsz -= 1
        hdp = {**hd, "size": hsz, "gap_below": hgap}
        needs = {n: _two_col_need(b, c, hdp, body) for n, b, c in sides}
        res = {"size": s_, "body": body, "head": hdp, "needs": needs,
               "fits": all(needs[n] <= avails[n] + 0.5 for n in needs)}
        chosen = res
        if res["fits"]:
            break
    body, hdp, needs = chosen["body"], chosen["head"], chosen["needs"]
    for k in ("size", "child_size", "gap", "child_gap"):
        if k in body and k not in fixed and body[k] != cb.get(k):
            ctx.set("col_body", k, body[k])
    for k in ("size", "gap_below"):
        if not hd_fixed and hdp[k] != hd.get(k):
            ctx.set("col_heading", k, hdp[k])
    words = []
    for n, bx, c in sides:
        w_in = bx.get("w", 400) - 2 * bx.get("pad", 0)
        label_ = {"left": "左", "right": "右"}.get(n, "")
        words += bullets_word_entries(c.get("bullets") or [], body, w_in, f"{label_}の列")
        if c.get("heading"):
            words.append((c["heading"], hdp["size"], w_in, f"{label_}の列の見出し"))
    long_word_check(ctx, words)
    ctx.info["two_column"] = {"size": chosen["size"], "needs": {k: round(v, 1) for k, v in needs.items()},
                              "avail": {k: round(v, 1) for k, v in avails.items()}, "cap": cap, "fits": chosen["fits"]}
    # 箱を内容に合わせて縮める（fit: "content"。steps と同じ作法）。read 密度では既定で有効
    content_sides = [(n, b) for n, b, _ in sides if (ctx.val(n, "fit") or "fill") == "content"]
    if content_sides:
        new_h = max(needs[n] for n, _ in content_sides)
        for n, b in content_sides:
            h0 = b.get("h", 300)
            h1 = min(h0, max(new_h, b.get("min_h", 200)))
            # 利用者が h を明示し、fit は明示していない（density 由来の content）なら箱に触らない（cards と同じ作法）
            if h1 < h0 - 1 and (not ctx.explicit(n, "h") or ctx.explicit(n, "fit")):
                ctx.set(n, "h", round(h1, 1), force=True)
                if not ctx.explicit(n, "y"):
                    ctx.set(n, "y", round(b.get("y", 0) + (h0 - h1) * 0.4, 1))
    # 警告
    if not chosen["fits"]:
        over = max(needs[n] - avails[n] for n in needs)
        n_over = max(needs, key=lambda n: needs[n] - avails[n])
        label = {"left": "左", "right": "右"}[n_over]
        if int(over) > 6:
            box_o, colc_o = next((bx, c) for n, bx, c in sides if n == n_over)
            head_only = _two_col_need(box_o, {**colc_o, "bullets": None}, hdp, body)
            m = items_that_fit(colc_o.get("bullets") or [], {**body, "w": box_o.get("w", 400) - 2 * box_o.get("pad", 0)},
                               avails[n_over] - head_only)
            hint = f"{label}の項目を {m} 個以下に減らすか、2 枚に分ける" if m else f"{label}の文を短くするか、2 枚に分ける"
            if "size" in fixed:
                ctx.warn("two_column-overflow",
                         f"{{label}}: {label}の列が枠の高さを約{int(over)}px超える見込みです（{ctx.by_spec(f'style.col_body.size={cap}')}）"
                         f" → {hint}、または size を下げる{ctx.undo_hint()}")
            else:
                ctx.warn("two_column-overflow",
                         f"{{label}}: {label}の列は {chosen['size']}px まで縮めても枠の高さを約{int(over)}px超えます"
                         f" → {hint}")
    elif cap - chosen["size"] >= 2:
        ctx.note("two_column-shrunk",
                 f"{{label}}: 2 列の文字を {cap}px → {chosen['size']}px に縮めました"
                 f" → 大きく読ませたいときは項目を減らすか 2 枚に分ける")


# ---------------------------------------------------------------------------
# cards
# ---------------------------------------------------------------------------

CARD_HEAD_LH = 1.2        # 見出し 1 行の高さ = size × これ + CARD_HEAD_PAD
CARD_HEAD_PAD = 5
CARD_HEAD_GAP = 4         # 見出しと本文の間
CARD_BODY_GAP = 10        # 本文と箇条書きの間（本文の高さを内容基準にしたので、固定 44px 時代の余白感に近づける）
CARD_BODY_LH = 1.4
CARD_ITEM_LH = 1.35
CARD_ITEM_INDENT = 14


def cards_item_params(g: dict, body_w: float) -> dict:
    """cards の箇条書き（items）を測るときの値（描画側 build_deck の itemr と同じ）。"""
    return {"size": g.get("item_size", 14), "gap": g.get("item_gap", 6), "line_height": CARD_ITEM_LH,
            "indent": CARD_ITEM_INDENT, "child_size": 12, "child_gap": 4, "w": body_w}


def card_icon_reserve(card: dict, g: dict) -> float:
    """アイコンつきのカードで、見出しの幅から引く値（アイコンは右上に置くので、長い見出しが重ならないように）。アイコンが無ければ 0。"""
    if not (isinstance(card, dict) and card.get("icon")):
        return 0.0
    return max(0.0, g.get("icon_size", 28) + 12 + 6 - g.get("pad", 18))


def cards_content(card: dict, g: dict, body_w: float) -> dict:
    """カード 1 枚の中身（見出し＋本文＋箇条書き）の各段の高さ。本文の高さは固定 44px ではなく内容の行数から決める。
    戻り値 {head_h, body_h, items_h（末尾の間隔を含む）, items_vis（含まない）}。HTML・PPTX・自動フィットで共通。"""
    hs = g.get("heading_size", 19)
    bs = g.get("body_size", 15)
    head_lines = ja_text.estimate_lines(card.get("heading", ""), hs, body_w - card_icon_reserve(card, g), ja_text.heading_fonts(), True)
    head_h = round(head_lines * hs * CARD_HEAD_LH + CARD_HEAD_PAD, 1)
    body_h = 0.0
    if card.get("body"):
        body_h = round(ja_text.estimate_lines(card["body"], bs, body_w) * bs * CARD_BODY_LH, 1)
    items_h = items_vis = None
    if card.get("items"):
        probe = cards_item_params(g, body_w)
        items_h = bullets_height(card["items"], probe)
        items_vis = bullets_visible_height(card["items"], probe)
    return {"head_h": head_h, "body_h": body_h, "items_h": items_h, "items_vis": items_vis}


def _phrase_min_size() -> float:
    """build_deck の CARD_PHRASE_MIN_SIZE（cards の見出し・本文を文節の切れ目で折る文字サイズの下限）。build_deck が未読込なら 20。"""
    import sys
    return getattr(sys.modules.get("build_deck"), "CARD_PHRASE_MIN_SIZE", 20)


def card_wrap_profile(text, size, width, font=None, bold: bool = False, tail_only: bool = False) -> tuple:
    """cards の見出し・本文の (行数, 最終行の字数, 語の途中の折れ) 。描くときと同じに、文字が CARD_PHRASE_MIN_SIZE 以上なら
    文節の切れ目に改行を入れた（ja_text.phrase_wrap）あとの折り返しで測る。小さい文字は自然な折り返し（wrap_profile）。
    tail_only=True（単独の cards の拡大の判定）は、文節の切れ目で折らない小さな文字の「語の途中の折れ」を数えない（0 にする）。
    それは、決めた大きさに文節の改行を入れる処理（S5b）が直す。行数と最終行の字数（泣き別れ）は自然な折り返しのまま測る。"""
    text = str(text or "")
    if size < _phrase_min_size() or not text:
        p_ = wrap_profile(text, size, width, font, bold)
        return (p_[0], p_[1], 0) if tail_only else p_
    pw = ja_text.phrase_wrap(text, size, width, font=font, bold=bold, min_tail=max(4, ja_text.tail_min(size)))
    lines, bad = [], 0
    for seg in pw.split("\n"):
        ls = ja_text.wrap_lines(seg, size, max(1.0, width), font, bold) or [seg]
        pos = 0
        for ln in ls[:-1]:
            pos += len(ln)
            while pos < len(seg) and seg[pos] == " ":
                pos += 1
            if 0 < pos < len(seg) and not ja_text.good_break(seg, pos):
                bad += 1
        lines += ls
    return len(lines), len((lines[-1] or "").strip()), bad


def wrap_not_broken(base: tuple, cand: tuple) -> bool:
    """wrap_not_worse から「行数が増えない」を外したもの（箱に高さの余裕があるとき用）。語の途中の折れが増えない・最終行が 3 字未満に悪化しない。"""
    if cand[2] > base[2]:
        return False
    if cand[0] > 1 and cand[1] < WRAP_TAIL_MIN and not (base[0] > 1 and base[1] <= cand[1]):
        return False
    return True


def _card_item_profiles(items, r: dict) -> list:
    """cards の項目（親＋子）の折り返し（bullets_wrap_profiles と同じ幅・大きさ）。語の途中の折れは数えない（card_wrap_profile の tail_only）。"""
    items = norm_items(items)
    size = r.get("size", 16)
    indent = r.get("indent", 30)
    width = max(10.0, r.get("w", 400) - indent)
    child_size = r.get("child_size", max(10, size - 3))
    out = []

    def prof(text, sz, w):
        p_ = wrap_profile(text, sz, w)
        return (p_[0], p_[1], 0)
    for it in items:
        out.append(prof(it.get("text", ""), it.get("size", size), width))
        for c in it.get("children", []):
            out.append(prof(c.get("text", ""), c.get("size", child_size), max(10.0, width - (indent - 6))))
    return out


def _cards_wrap_more(cards, cell_w, pad, g0_: dict, g1_: dict, lines_ok: bool = False) -> bool:
    """文字を g0 → g1 に大きくしたとき、カードの見出し・本文・項目の折り返しが悪くなるか（行数が増える・語の途中の折れが増える・
    最終行が 1〜2 字になる）。いまの折り返し g0 は実幅、大きくした g1 は実幅と幅を THIN_WRAP_SAFETY 倍に狭めた幅の両方で測る。
    lines_ok=True（単独スライド）は、箱に高さの余裕があるので、行数が増えること自体は悪くないとする（語中折れ・短い最終行は同じく悪い）。
    見出し・本文は、描くときと同じ文節の切れ目の折り返し（card_wrap_profile）で測る。"""
    ok = wrap_not_broken if lines_ok else wrap_not_worse
    import hero_engine
    for k, c in enumerate(cards):
        w0 = max(10.0, cell_w[k] - 2 * pad)
        g0, g1 = hero_engine.emph_grid(g0_, hero_engine.card_emphasis(c)), hero_engine.emph_grid(g1_, hero_engine.card_emphasis(c))     # 強調のカードは文字が emph_scale 倍
        # 単独は行数が増えてよい分、折り返し位置のずれ（見積もりと実際の差）で最終行が 1〜2 字になるのを、より広い幅の範囲で避ける
        for sf in (WRAP_CHECK_SAFETIES + (1.04, 0.88) if lines_ok else WRAP_CHECK_SAFETIES):
            w1 = w0 * sf
            for key, getter in (("heading", lambda g: (c.get("heading", ""), g.get("heading_size", 19), True)),
                                ("body", lambda g: (c.get("body", ""), g.get("body_size", 15), False))):
                t0, s0, b0 = getter(g0)
                t1, s1, b1 = getter(g1)
                if not t0:
                    continue
                f = ja_text.heading_fonts() if b0 else None
                res = card_icon_reserve(c, g0) if key == "heading" else 0
                if not ok(card_wrap_profile(t0, s0, w0 - res, f, b0, lines_ok), card_wrap_profile(t1, s1, w1 - res, f, b1, lines_ok)):
                    return True
            if c.get("items"):
                p0, p1 = cards_item_params(g0, w0), cards_item_params(g1, w1)
                if lines_ok:
                    a_, b_ = _card_item_profiles(c["items"], p0), _card_item_profiles(c["items"], p1)
                else:
                    a_, b_ = bullets_wrap_profiles(c["items"], p0), bullets_wrap_profiles(c["items"], p1)
                if not all(ok(a, b) for a, b in zip(a_, b_)):
                    return True
    return False


def _cards_nobreak(card: dict) -> dict:
    """カードの見出し・本文から改行（\\n）を外した写し（日本語どうしの間は詰め、英数字の間は空白にする）。"""
    out = dict(card)
    for key in ("heading", "body"):
        v = card.get(key)
        if isinstance(v, str) and "\n" in v:
            out[key] = re.sub(r"(?<=[^\x00-\x7f])\n|\n(?=[^\x00-\x7f])", "", v).replace("\n", " ")
    return out


def cards_need(card: dict, g: dict, body_w: float, pad: float) -> float:
    """カード 1 枚が必要とする高さ（上下の余白込み）。"""
    c = cards_content(card, g, body_w)
    need = 2 * pad + c["head_h"]
    if card.get("body"):
        need += CARD_HEAD_GAP + c["body_h"]
    if card.get("items"):
        need += CARD_BODY_GAP + c["items_vis"]
    return need


def thin_box(need: float, rows: int, gap: float, y: float, h: float, g: dict):
    """中身が薄いとき、箱を「中身 + 余白」の高さに抑えて、領域（y, h）の中の縦中央（thin_valign: "top" なら上寄せ）に置く。
    返り値は (新しい y, 新しい合計の高さ)。抑える必要が無い（中身が領域の thin_trigger 倍以上）・指定が無いときは None。
    cards の薄い箱（単独スライド = 縦中央、合成スライドのブロック = 上寄せ）と同じ考え方の共通関数
    （表の talk の縦中央・表だけの split も、同じ値の名前 thin_* で揃える）。値はレイアウト JSON の領域（thin_k / thin_trigger / thin_valign / min_h）。
    need は箱 1 つぶんの必要な高さ（上下の余白込み）、rows は段数。箱の高さ = max(min_h, need × thin_k)（同じ並びの箱は同じ高さ）。"""
    k = g.get("thin_k")
    if not isinstance(k, (int, float)) or isinstance(k, bool) or k <= 0 or rows < 1 or h <= 0:
        return None
    per = max(float(g.get("min_h", 0) or 0), need * k)
    ratio = g.get("thin_min_ratio")
    if isinstance(ratio, (int, float)) and not isinstance(ratio, bool) and 0 < ratio <= 1:
        per = max(per, (h * ratio - (rows - 1) * gap) / rows)      # 単独スライド（S5a）: 箱は枠の高さの thin_min_ratio 割以上にする（短い文だけの箱が小さく浮かない）
    total = rows * per + (rows - 1) * gap
    if total >= h * float(g.get("thin_trigger", 0.75)) or total >= h - 1:
        return None
    ny = y + (h - total) / 2 if g.get("thin_valign", "middle") == "middle" else y
    return round(ny, 1), round(total, 1)


def _scale_steps(cap, floor, step=0.04):
    """cap から floor まで比例して縮める倍率の列（1.0, 0.96, ...）。floor に当たったら打ち切る。"""
    out, f = [], 1.0
    while True:
        out.append(round(f, 3))
        if cap * f <= floor + 1e-9:
            break
        f -= step
    return out


def _cards_wrap_dirty(cards, g: dict, cols: int, info: dict) -> int:
    """列数 cols で並べたとき、カードの見出し・本文・項目に、最終行が 1〜2 字（泣き別れ。1 つにつき 3）・語の途中の折れ（1 つにつき 1）の点数。"""
    pad = info.get("pad", g.get("pad", 14))
    w = (g.get("w", 1136) - (cols - 1) * g.get("gap", 16)) / max(cols, 1)
    inner = max(10.0, w - 2 * pad)
    hs, bs, isz = info.get("heading_size", g.get("heading_size", 19)), info.get("body_size", g.get("body_size", 15)), info.get("item_size", g.get("item_size", 14))
    n = 0
    for c in cards:
        if not isinstance(c, dict):
            continue
        profs = []
        if c.get("heading"):
            profs.append(wrap_profile(c["heading"], hs, inner - card_icon_reserve(c, g), ja_text.heading_fonts(), True))
        if c.get("body"):
            profs.append(wrap_profile(c["body"], bs, inner))
        if c.get("items"):
            profs += bullets_wrap_profiles(c["items"], cards_item_params({**g, "item_size": isz}, inner))
        n += sum((3 if (p_[0] > 1 and p_[1] < WRAP_TAIL_MIN) else 0) + p_[2] for p_ in profs)       # 最終行が 1〜2 字は目立つので重く、語の途中の折れは 1 つにつき 1
    return n


@fitter("cards")
def _fit_cards(ctx: Ctx) -> None:
    """cards の自動フィット。合成ブロックの中で、利用者が列数（columns / style.grid.cols）を書いていないときは、列数の候補
    （既定の列数・2・1）をそれぞれ解いて、文字がいちばん大きく読める列数を選ぶ（4 枚が 3 + 1 に割れる、細長いカードが縦に並ぶのを避ける）。"""
    g = ctx.st.get("grid")
    cards = ctx.slide.get("cards")
    n = len(cards) if isinstance(cards, list) else 0
    import hero_engine
    searchable = ((thin_participates(g) or single_participates(g)) and ctx.adjust and n >= 2 and not isinstance(ctx.slide.get("columns"), int)
                  and not ctx.explicit("grid", "cols") and not hero_engine.card_spans(ctx.slide) and g.get("cols_search", True)
                  and not (not thin_participates(g) and user_set_region(ctx.deck, ctx.slide, "grid")))
    if not searchable:
        _fit_cards_core(ctx)
        return
    base = max(1, int(g.get("cols", 3)))
    cands = [base] + [c for c in (2, 1, 3) if c != base and c <= n]
    if not thin_participates(g):
        # 単独スライド（S5a）: 全幅に横に並べるのが自然。2 枚は 2 列（3 列の左 2 つだけに寄らない）、4 枚は 2 × 2 か 4 列、ほかは 3 列まで（縦に積まない）
        cands = [2] if n == 2 else ([2, 4] if n == 4 else [min(base, n)])
    results = []
    for c in cands:
        st2 = dict(ctx.st)
        st2["grid"] = {**g, "cols": c}
        sub = Ctx(ctx.deck, ctx.slide, st2, ctx.density, ctx.adjust)
        _fit_cards_core(sub)
        info = sub.info.get("cards") or {}
        orphan = c >= 3 and n > c and n % c == 1
        dirty = _cards_wrap_dirty(cards, g, c, info)
        results.append(((bool(info.get("fits")), 0, info.get("heading_size", 0) + (3 if not info.get("thin") else 0) + (2 if not orphan else 0) - (0 if c == base else 0.5)), c, sub, dirty))
    # 泣き別れ・語の途中の折れが少ない列数を先に選ぶ（細い列に 2 列で並べて見出しが 1 字だけ折れる、を避ける・s4 レビュー）
    results = [((k[0], -d, k[2]), c, sub) for k, c, sub, d in results]
    best = max(results, key=lambda r: r[0])
    key, c, sub = best
    ctx.updates.update(sub.updates)
    ctx.issues.extend(sub.issues)
    ctx.info.update(sub.info)
    if c != base:
        ctx.set("grid", "cols", c)
        ctx.info["cards"]["cols"] = c


def _fit_cards_core(ctx: Ctx) -> None:
    import proposal_engine as pe
    g = ctx.st.get("grid")
    cards = ctx.slide.get("cards")
    if not isinstance(g, dict) or not isinstance(cards, list) or not cards or not all(isinstance(c, dict) for c in cards):
        return
    bottom = ctx.content_bottom("grid")
    geo_g = {**g, "h": max(40, min(g.get("h", 440), bottom - g.get("y", 196)))}
    import hero_engine
    geo = pe.cards_cells(len(cards), ctx.slide.get("columns"), geo_g, hero_engine.card_spans(ctx.slide))
    cw, chh, rows = geo["cw"], geo["chh"], geo["rows"]
    cell_w = [c[2] for c in geo["cells"]]
    hs0, bs0, is0 = g.get("heading_size", 19), g.get("body_size", 15), g.get("item_size", 14)
    ig0, pad0 = g.get("item_gap", 6), g.get("pad", 18)
    min_body = g.get("min_size", 12)
    f_h, f_b, f_i = (ctx.fixed("grid", k) for k in ("heading_size", "body_size", "item_size"))
    pad_fixed = ctx.fixed("grid", "pad")
    ig_fixed = ctx.fixed("grid", "item_gap")
    floors = {"h": max(min_body + 4, 14), "b": min_body, "i": max(min_body - 1, 11)}
    # 候補: 倍率を下げながら (見出し, 本文, 項目, 項目の間隔)、各倍率で余白をそのまま → 詰めた余白
    cands = []
    seen = set()
    k_scales = _scale_steps(max(bs0, 1), floors["b"]) if not (f_b and f_h and f_i) and ctx.adjust else [1.0]
    for f in k_scales:
        hs = hs0 if f_h else max(min(floors["h"], hs0), round(hs0 * f))
        bs = bs0 if f_b else max(min(floors["b"], bs0), round(bs0 * f))
        isz = is0 if f_i else max(min(floors["i"], is0), round(is0 * f))
        ig = ig0 if ig_fixed or f == 1.0 else max(3, round(ig0 * f))
        for pad in ([pad0] if (pad_fixed or pad0 <= 10) else [pad0, max(10, pad0 - 6)]):
            key = (hs, bs, isz, ig, pad)
            if key not in seen:
                seen.add(key)
                cands.append(key)
    pick, last = None, None
    for hs, bs, isz, ig, pad in cands:
        gg = {**g, "heading_size": hs, "body_size": bs, "item_size": isz, "item_gap": ig, "pad": pad}
        needs = [cards_need(c, hero_engine.emph_grid(gg, hero_engine.card_emphasis(c)), cell_w[k] - 2 * pad, pad) for k, c in enumerate(cards)]
        need = max(needs)
        last = (gg, need, hs, bs, isz, ig, pad)
        if need <= chh + 0.5:
            pick = last
            break
    fits = pick is not None
    gg, need, hs, bs, isz, ig, pad = pick or last
    for key, v in (("heading_size", hs), ("body_size", bs), ("item_size", isz), ("item_gap", ig), ("pad", pad)):
        if v != g.get(key):
            ctx.set("grid", key, v)
    ctx.info["cards"] = {"heading_size": hs, "body_size": bs, "item_size": isz, "pad": pad, "need": round(need, 1),
                         "card_h": round(chh, 1), "fits": fits, "rows": rows}
    # 箱を内容に合わせて縮める（fit: "content"。steps と同じ作法）。read 密度では既定で有効
    if (ctx.val("grid", "fit") or "fill") == "content" and fits:
        h0 = g.get("h", 440)
        h1 = min(h0, max(rows * need + (rows - 1) * geo["gap"], g.get("min_h", 160)))
        if h1 < h0 - 1 and (not ctx.explicit("grid", "h") or ctx.explicit("grid", "fit")):
            ctx.set("grid", "h", round(h1, 1), force=True)
            if not ctx.explicit("grid", "y"):
                ctx.set("grid", "y", round(g.get("y", 196) + (h0 - h1) * 0.4, 1))
    elif fits and (ctx.val("grid", "fit") or "fill") != "content" and g.get("thin_k") and (
            ctx.val("grid", "block_rect") or not (ctx.explicit("grid", "h") or ctx.explicit("grid", "y") or ctx.explicit("grid", "fit"))):
        # 中身が薄い（本文 1〜2 行など）: 箱を縮める前に、文字を大きくして領域を使う（thin_grow 倍まで。収まる最大の倍率）。
        # そのうえでまだ薄ければ、箱を中身 + 余白の高さに抑えて、領域の中で縦中央（ブロックの中は上寄せ）に置く
        grow = g.get("thin_grow")
        block = thin_participates(g)
        # 利用者が grid の位置・大きさ・文字・列数（style.grid.* / columns）を書いたスライドは、S5a の拡大・箱の伸ばしを一切かけず、変更前（S3）と同じ結果にする
        user_set = not block and (user_set_region(ctx.deck, ctx.slide, "grid") or isinstance(ctx.slide.get("columns"), int))
        # span で大きさを変えたカードのあるスライドは、S3 の挙動（1.4 倍まで・箱の高さの下限なし）のまま動かさない（S5a の約束）
        # 中身が箱の高さの 4 割以上ある（文字がすでに多い・長い項目の並び）カードも、S3 の挙動のまま（拡大は 1.4 倍まで。折り返しの判定は箱の高さに余裕がある薄い箱だけ）
        need_nb = need if block else max(cards_need(_cards_nobreak(c), hero_engine.emph_grid(gg, hero_engine.card_emphasis(c)), cell_w[k] - 2 * pad, pad)
                                         for k, c in enumerate(cards))      # 改行（\n）を外した文で測る（改行を入れた後の二度目のフィットでも同じ判断になる）
        strict = (bool(hero_engine.card_spans(ctx.slide)) or user_set) and not block          # 変更前（S3）と完全に同じにする（改行を入れた文のまま測る）
        legacy = (strict or need_nb >= chh * float(g.get("thin_legacy_ratio", 0.4))) and not block
        if isinstance(grow, (int, float)) and not isinstance(grow, bool):
            grow = min(grow, THIN_GROW_CAP)
        # 変更前（S3）の拡大。単独の cards は thin_grow の既定が 1.4 だった（利用者が thin_grow を書いたときはその値）
        grow_s3 = min(grow, 1.4) if isinstance(grow, (int, float)) and not ctx.explicit("grid", "thin_grow") else grow
        if legacy:
            grow = grow_s3

        def sizes_at(f):
            return {**g, "heading_size": hs if f_h else round(hs * f), "body_size": bs if f_b else round(bs * f),
                    "item_size": isz if f_i else round(isz * f), "item_gap": ig, "pad": pad}

        # 拡大の判断（薄さ・収まり・折り返し）は、改行（\n。大きくした文字に合わせて入れた分）を外した文で行う。改行を入れる前と後で同じ大きさになり、
        # 入れた改行が小さい文字で行を増やして「薄くない」と見なされ、拡大が戻る（二度目の自動フィットで小さくなる）のを防ぐ。ブロック・利用者が決めた領域は従来どおり
        cards_n = cards if (block or strict) else [_cards_nobreak(c) for c in cards]

        def need_of(gg_):
            return max(cards_need(c, hero_engine.emph_grid(gg_, hero_engine.card_emphasis(c)), cell_w[k] - 2 * pad, pad) for k, c in enumerate(cards_n))
        need_t = need if cards_n is cards else need_nb
        if (isinstance(grow, (int, float)) and not isinstance(grow, bool) and grow > 1.0 and ctx.adjust and not (f_h and f_b and f_i)
                and rows * need_t + (rows - 1) * geo["gap"] < geo_g["h"] * float(g.get("thin_trigger", 0.75))):
            def s3_search():
                """変更前（S3）と同じ探し方: 収まる最大の倍率（0.1 刻み。折り返しは見ない）。"""
                f_ = float(grow_s3) if isinstance(grow_s3, (int, float)) else 0.0
                while f_ > 1.04:
                    gg_ = sizes_at(f_)
                    n_ = need_of(gg_)
                    if n_ <= chh + 0.5:
                        return f_, gg_, n_
                    f_ -= 0.1
                return None
            pick_g = None
            f = float(grow)
            while f > 1.04:
                gg2 = sizes_at(f)
                need2 = need_of(gg2)
                if need2 <= chh + 0.5 and (legacy or not _cards_wrap_more(cards_n, cell_w, pad, {**g, "heading_size": hs, "body_size": bs, "item_size": isz}, gg2, lines_ok=not block)):
                    pick_g = (f, gg2, need2)
                    break
                f -= 0.1 if (block or legacy) else 0.04       # 単独は、折り返しが悪くならない最大の倍率を細かく探す（S5a）
            if not block and not legacy:
                # 変更前（S3）より文字が小さくならないことを保証する（折り返しの判定で拡大が止まっても、S3 の拡大までは行う）
                s3 = s3_search()
                if s3 and (pick_g is None or any(pick_g[1][k_] < s3[1][k_] for k_ in ("heading_size", "body_size", "item_size"))):
                    pick_g = s3
            if pick_g:
                f, gg2, need2 = pick_g
                for key in ("heading_size", "body_size", "item_size"):
                    if gg2[key] != g.get(key):
                        ctx.set("grid", key, gg2[key])
                need, hs, bs, isz = need2, gg2["heading_size"], gg2["body_size"], gg2["item_size"]
                ctx.info["cards"].update({"heading_size": hs, "body_size": bs, "item_size": isz, "need": round(need, 1), "grown": round(f, 2)})
        res = thin_box(need, rows, geo["gap"], g.get("y", 196), geo_g["h"], {**g, "thin_min_ratio": None} if legacy else g)
        if res:
            ctx.set("grid", "y", res[0], force=True)
            ctx.set("grid", "h", res[1], force=True)
            ctx.info["cards"]["thin"] = True
    # 合成ブロックの中で、箱を詰めずに枠いっぱいに並べたカードに余裕があるとき（中身が箱の高さの 8 割未満）は、中身を箱の縦中央に置く
    ci = ctx.info.get("cards") or {}
    if fits and thin_participates(g) and ctx.adjust and not ci.get("thin") and need < chh * float(g.get("center_ratio", 0.8)):
        ctx.set("grid", "valign", "middle")
        ci["centered"] = True
    # 警告
    if not fits:
        over = int(need - chh)
        if over > 6:
            per_row = max(1, int((geo_g["h"] + geo["gap"]) // (need + geo["gap"])))
            fit_n = per_row * geo["cols"]
            explicit = f_b or f_h or f_i
            if explicit:
                ctx.warn("cards-overflow",
                         f"{{label}}: カードの中身が枠に収まらず、約{over}px はみ出します（{len(cards)}枚・{rows}段・{ctx.by_spec('style の文字サイズ')}）"
                         f" → カードを {fit_n} 枚以下にするか列数を増やす、または style.grid の size を下げる{ctx.undo_hint()}")
            else:
                ctx.warn("cards-overflow",
                         f"{{label}}: カードの中身が最小の文字サイズ（本文 {bs}px・項目 {isz}px）でも枠に収まらず、約{over}px はみ出します"
                         f"（{len(cards)}枚・{rows}段）→ カードを {fit_n} 枚以下にするか、2 枚に分ける（本文や項目を短くするのも有効）")
    elif hs0 - hs >= 2 or bs0 - bs >= 2:
        ctx.note("cards-shrunk",
                 f"{{label}}: カードの文字を縮めました（本文 {bs0}px → {bs}px・見出し {hs0}px → {hs}px・{len(cards)}枚）"
                 f" → 大きく読ませたいときはカードを減らすか 2 枚に分ける")


# ---------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------

STEP_LABEL_TOP = 28       # 見出し帯の中で、ラベルが始まる y（"STEP n" の下）
STEP_LABEL_LH = 1.15
STEP_LABEL_PAD = 4
STEP_NUM_W = 56            # 「STEP n」の札（13px 太字）が折れない幅の最低値（実際は最大桁数の札を測って決める）
STEP_NUM_SIZE = 13
STEP_MIN_CARD_W = 80       # これより細いカードには、ほとんど文字が入らない


def steps_item_params(b: dict, w: float) -> dict:
    """steps の各カードの箇条書きを測る（描くとき）の値。"""
    return {"w": w, "size": b.get("item_size", 15), "gap": b.get("item_gap", 8), "line_height": 1.4,
            "child_size": b.get("child_size", 13), "child_gap": b.get("child_gap", 4), "indent": 16}


def _thin_grow_steps(ctx: Ctx, b: dict, steps, labels, inner_w, pad, lcap, lsz, hdr_eff, cap, res, ifix, label_ok, base) -> None:
    """steps ブロックの中身が薄いとき（カードの中身が枠の thin_trigger 割未満）、見出しと項目の文字を大きくし（thin_grow 倍まで）、
    カードを枠の高さいっぱいに広げ、項目は見出しの直下に置く（fit: "fill"。thin_fill_valign が "middle" なら縦中央）。折り返しが増える大きさには上げない。"""
    single = not b.get("block_rect")              # 単独のスライド（S5a）: 同じ部品で文字を大きくし、箱の高さは _steps_stretch が決める
    if not (single_participates(b) if single else thin_participates(b)):
        return
    if single and user_set_region(ctx.deck, ctx.slide, "body"):
        return                                    # 利用者が body の位置・大きさ・文字を書いたスライドは動かさない（変更前と同じ）
    n = len(steps)
    ctx.info["thin_factor"] = 1.0
    gp = single_grow_params(b) if single else thin_grow_params(b)
    if gp is None or not ctx.adjust or not res["fits"] or not label_ok:
        return
    grow, mx, trig = gp[:3]
    h_total = ctx.content_bottom("body") - b.get("y", 0)
    if h_total <= 0:
        return
    lfix, ifixed = ctx.fixed("body", "label_size"), "item_size" in ifix
    if (lfix and ifixed) or res["size"] < cap or lsz < lcap:
        return                           # すでに縮めている（中身は薄くない）、または明示された大きさ
    lmax = b.get("thin_label_max_size", mx)
    lmax = min(float(lmax), THIN_SIZE_CAP) if isinstance(lmax, (int, float)) and not isinstance(lmax, bool) and lmax > 0 else mx

    def need_at(f):
        ls = lsz if lfix else min(int(round(lcap * f)), int(lmax))
        isz = res["size"] if ifixed else min(int(round(cap * f)), int(mx))
        r = scaled_bullets(base, isz, cap, {"gap" if k == "item_gap" else k for k in ifix})
        lab_lines = max(ja_text.estimate_lines(t, ls, inner_w, ja_text.heading_fonts(), True) for t in labels)
        hdr = max(hdr_eff, int(STEP_LABEL_TOP + lab_lines * ls * STEP_LABEL_LH + STEP_LABEL_PAD + 0.999))
        items_need = max((bullets_visible_height(st_.get("items") or [], r) for st_ in steps), default=0.0)
        # f = 1.0 は「いまの折り返し」（実際に描かれる幅）。拡大の候補は、実幅と少し狭めた幅の両方で測る（ブラウザの折り返しはその間にある）
        lines = []
        for sf in ((1.0,) if f <= 1.0 else WRAP_CHECK_SAFETIES):
            lines.append([wrap_profile(t, ls, inner_w * sf, ja_text.heading_fonts(), True) for t in labels]
                         + [pp for st_ in steps for pp in bullets_wrap_profiles(st_.get("items") or [], r, sf)])
        return ls, isz, r, hdr, hdr + 2 * pad + items_need, lines
    base_need = need_at(1.0)
    if (max(base_need[4] + 12, min(h_total, float(b.get("min_h", 260)))) if single else base_need[4]) >= h_total * trig:
        return                                    # 単独は、実際の箱の高さ（内容 + 12px、下限 min_h）が枠の trig 割未満のときだけ
    best, f = None, grow
    while f > 1.02:
        cand = need_at(f)
        if cand[4] <= h_total * trig + 0.5 and all(wrap_not_worse(a, c) for ln in cand[5] for a, c in zip(base_need[5][0], ln)):
            best = (f, cand)
            break
        f -= 0.04
    if best is None:
        return
    f, (ls, isz, r, hdr, tot, _) = best
    if not lfix and ls != lsz:
        ctx.set("body", "label_size", ls)
    if hdr != hdr_eff:
        ctx.set("body", "header_h", hdr)
    for key, rk in (("item_size", "size"), ("item_gap", "gap"), ("child_size", "child_size"), ("child_gap", "child_gap")):
        if key not in ifix and r[rk] != ctx.val("body", key, base.get(rk)):
            ctx.set("body", key, r[rk])
    ctx.info["thin_factor"] = round(isz / cap, 3)
    ctx.info["steps"].update({"label_size": ls, "item_size": isz, "header_h": hdr, "need": round(tot, 1), "grown": round(f, 2)})
    # カードは枠の高さいっぱいに広げ、項目をカードの白い部分の縦中央に置く（隣のブロックと上端・下端がそろう）
    card_w = (b.get("w", 1136) - (n - 1) * b.get("gap", 20)) / n
    # 細長すぎるカード（幅の 2.4 倍を超える高さ）と、項目の文字が thin_fill_min_size 未満のままのカードは広げない（小さい説明文が背の高い柱の中央に浮く・s4-A-01）
    if (b.get("thin_fill", True) and f >= 1.15 and h_total <= card_w * float(b.get("thin_fill_aspect", 2.4))
            and isz >= float(b.get("thin_fill_min_size", 0))):
        ctx.set("body", "fit", "fill")
        if b.get("thin_fill_valign", "top") == "middle":
            ctx.set("body", "valign", "middle")       # 既定は見出しの直下（小さい説明が背の高い柱の中央に浮かない・s4-A-01）
        ctx.info["steps"]["filled"] = True


@fitter("steps")
def _fit_steps(ctx: Ctx) -> None:
    b = ctx.st.get("body")
    steps = ctx.slide.get("steps")
    if not isinstance(b, dict) or not isinstance(steps, list) or not steps or not all(isinstance(s_, dict) for s_ in steps):
        return
    n = len(steps)
    gap, pad = b.get("gap", 20), b.get("pad", 16)
    card_w = (b.get("w", 1136) - (n - 1) * gap) / n
    # 「STEP 10」のように桁が増えると札が広がる。いちばん広い札を実測する（core-A-04）
    num_w = max([STEP_NUM_W] + [text_em(f"STEP {i + 1}", True) * STEP_NUM_SIZE + 2 for i in range(n)])
    if card_w - 2 * pad < num_w and not ctx.fixed("body", "pad"):
        # 段が多くてカードが細いとき、「STEP n」の札が折れないよう内側の余白を詰める
        pad = max(6, int((card_w - num_w) / 2))
        ctx.set("body", "pad", pad)
    inner_w = max(10.0, card_w - 2 * pad)
    num_short = inner_w < num_w
    if num_short:
        if ctx.adjust:
            ctx.set("body", "_num_short", True)       # 余白を詰めても入らない: 札を数字だけにする
        else:
            ctx.warn("steps-num", f"{{label}}: {n}段ではカードの幅（内側 {int(inner_w)}px）に「STEP {n}」の札が入らず、"
                                  f"見出しと重なります → 段を減らすか、2 枚に分ける")
    labels = [str(s_.get("label", "")) for s_ in steps]
    # 1) 見出し帯のラベル: 折れて帯からはみ出さないよう、文字を縮める → 帯を高くする
    lcap, hcap = b.get("label_size", 18), b.get("header_h", 60)
    lfix, hfix = ctx.fixed("body", "label_size"), ctx.fixed("body", "header_h")
    max_h = hcap if hfix else b.get("max_header_h", hcap + 24)

    def lab_need(sz):
        lines = max(ja_text.estimate_lines(t, sz, inner_w, ja_text.heading_fonts(), True) for t in labels)
        return STEP_LABEL_TOP + lines * sz * STEP_LABEL_LH + STEP_LABEL_PAD, lines
    sizes = [lcap] if lfix else size_candidates(lcap, min(b.get("label_min_size", 13), lcap))
    pick = None
    nogrow_floor = lcap if lfix else max(15, round(lcap * 0.85))
    for sz in sizes:
        if sz >= nogrow_floor and lab_need(sz)[0] <= hcap + 0.5:
            pick = (sz, hcap, lab_need(sz)[1])
            break
    if pick is None:
        for sz in sizes:
            nd, ln = lab_need(sz)
            if nd <= max_h + 0.5:
                pick = (sz, max(hcap, int(nd + 0.999)), ln)
                break
    label_ok = pick is not None
    if pick is None:
        sz = sizes[-1]
        nd, ln = lab_need(sz)
        pick = (sz, max(hcap, min(int(nd + 0.999), max_h)), ln)
    lsz, hdr, llines = pick
    if lsz != lcap:
        ctx.set("body", "label_size", lsz)
    if hdr != hcap:
        ctx.set("body", "header_h", hdr)
    hdr_eff = ctx.val("body", "header_h", hcap)
    # 2) 各カードの項目: 文字サイズ・間隔を比例して縮める（カード高さの上限は body.h）
    avail = ctx.content_bottom("body") - b.get("y", 0) - hdr_eff - 2 * pad
    cap = b.get("item_size", 15)
    ifix = {k for k in ("item_size", "item_gap", "child_size", "child_gap") if ctx.fixed("body", k)}
    ifloor = min(b.get("min_size", 12), cap)
    res = None
    base = steps_item_params(b, inner_w)
    for s_ in size_candidates(cap, ifloor, "item_size" in ifix):
        r = scaled_bullets(base, s_, cap, {"gap" if k == "item_gap" else k for k in ifix})
        need = max((bullets_visible_height(st_.get("items") or [], r) for st_ in steps), default=0.0)
        res = {"size": s_, "r": r, "need": need, "fits": need <= avail + 0.5}
        if res["fits"]:
            break
    for key, rk in (("item_size", "size"), ("item_gap", "gap"), ("child_size", "child_size"), ("child_gap", "child_gap")):
        if key not in ifix and res["r"][rk] != (b.get(key) if key in b else (steps_item_params(b, 0)[rk])):
            ctx.set("body", key, res["r"][rk])
    ctx.info["steps"] = {"label_size": lsz, "header_h": hdr_eff, "item_size": res["size"], "need": round(res["need"], 1),
                         "avail": round(avail, 1), "fits": res["fits"], "label_lines": llines}
    _thin_grow_steps(ctx, b, steps, labels, inner_w, pad, lcap, lsz, hdr_eff, cap, res, ifix, label_ok, base)
    _steps_stretch(ctx, b, steps, inner_w, card_w, pad)
    words = [(t, lsz, inner_w, "ステップの見出し") for t in labels]
    for st_ in steps:
        words += bullets_word_entries(st_.get("items") or [], {**base, **res["r"]}, inner_w, "ステップの項目")
    long_word_check(ctx, words)
    if card_w < STEP_MIN_CARD_W:
        ctx.warn("steps-narrow",
                 f"{{label}}: {n}段ではカードの幅が約{int(card_w)}px になり、見出しや項目がほとんど入りません"
                 f" → 段を {max(2, int((b.get('w', 1136) + gap) // (STEP_MIN_CARD_W + gap)))} 段以下にするか、2 枚に分ける")
    if not label_ok:
        ctx.warn("steps-label",
                 f"{{label}}: ステップの見出しが {llines} 行に折れて帯に収まりません（{n}段・カード幅 {int(card_w)}px）"
                 f" → 見出しを短くする（目安: {max(2, int(inner_w // max(lsz, 1)))} 字前後）か、段を減らす")
    if not res["fits"]:
        over = int(res["need"] - avail)
        if over > 6:
            if ifix and "item_size" in ifix:
                ctx.warn("steps-overflow",
                         f"{{label}}: ステップの項目がカードの高さを約{over}px超える見込みです（{ctx.by_spec(f'style の item_size={cap}')}）"
                         f" → 項目を減らすか、item_size を下げる{ctx.undo_hint()}")
            else:
                ctx.warn("steps-overflow",
                         f"{{label}}: ステップの項目は {res['size']}px まで縮めてもカードの高さを約{over}px超えます（{n}段）"
                         f" → 1 つのステップの項目を減らすか、段を分ける")
    elif cap - res["size"] >= 2:
        ctx.note("steps-shrunk", f"{{label}}: ステップの項目の文字を {cap}px → {res['size']}px に縮めました（{n}段）")


def single_participates(r: dict) -> bool:
    """単独スライドの領域 r は「中身が少ないとき文字・箱を大きくする」の対象か（block_rect が無く、thin_grow が 1 より大きい）。"""
    return isinstance(r, dict) and not r.get("block_rect") and single_grow_params(r) is not None


def _steps_stretch(ctx: Ctx, b: dict, steps, inner_w: float, card_w: float, pad: float) -> None:
    """単独の steps: 文字を大きくしても箱が本文の高さの thin_trigger 割に届かないとき、箱の高さを本文の thin_target 割まで伸ばし、
    項目を箱の白い部分の縦中央に置く（min_h と valign を決める。箱の並びは build_deck.steps_card_height の位置のまま）。
    箱を本文いっぱいまで広げる（fit: "fill"）と、少ない項目の上下が大きく空くので、中間の高さにする。
    項目が無い段だけのとき・利用者が min_h / valign / fit を書いたとき・細長すぎる箱になるときは何もしない。"""
    if b.get("block_rect") or not ctx.adjust:
        return
    gp = single_grow_params(b)
    if gp is None:
        return
    _, _, trig, tgt = gp
    if user_set_region(ctx.deck, ctx.slide, "body") or b.get("fit", "content") != "content":
        return                                    # min_h・valign・fit・h を含め、body の位置・大きさ・文字を書いたスライドは動かさない
    if not any(norm_items(st_.get("items") or []) for st_ in steps if isinstance(st_, dict)):
        return
    h_total = ctx.content_bottom("body") - b.get("y", 0)
    if h_total <= 0:
        return
    v = ctx.view()["body"]
    hdr, pad_ = v.get("header_h", 60), v.get("pad", 16)
    est = max((bullets_visible_height(norm_items(st_.get("items") or []), steps_item_params(v, inner_w)) for st_ in steps), default=0.0)
    h_now = max(min(b.get("h", h_total), hdr + 2 * pad_ + est + 12), min(b.get("h", h_total), float(v.get("min_h", 260))))
    if h_now >= h_total * trig:
        return
    target = min(h_total * tgt, card_w * float(b.get("thin_fill_aspect", 2.4)), float(b.get("h", h_total)))
    if target < h_now + 8:
        return
    ctx.set("body", "min_h", int(target))
    ctx.set("body", "valign", "middle")
    ctx.info.setdefault("steps", {}).update({"stretched": int(target), "card_h_before": round(h_now, 1)})


# ---------------------------------------------------------------------------
# agenda（S5a: 項目が少ないとき、行と文字を大きくして本文の高さを使う）
# ---------------------------------------------------------------------------

AGENDA_FIXED_KEYS = ("row_h", "gap", "text_size", "num_size", "num_w", "desc_size", "y", "h")
AGENDA_DESC_GROW = 0.7        # 説明文は、見出しの拡大幅（倍率 - 1）のこの割合だけ大きくする（見出しが 30px のとき説明は 18〜19px）


def single_grow_params(r: dict):
    """単独スライド（block_rect の無い領域）の thin_grow / thin_max_size / thin_trigger / thin_target → (倍率の上限, px の上限, 割合, 目標)。
    大きくしない（thin_grow が 1 以下・無い）とき None。thin_grow_params のブロック版と同じトークン名。"""
    if not isinstance(r, dict):
        return None
    g = r.get("thin_grow")
    if not isinstance(g, (int, float)) or isinstance(g, bool) or g <= 1.02:
        return None
    g = min(float(g), THIN_GROW_CAP)
    mx = r.get("thin_max_size")
    mx = min(float(mx), THIN_SIZE_CAP) if isinstance(mx, (int, float)) and not isinstance(mx, bool) and mx > 0 else THIN_SIZE_CAP
    trig = r.get("thin_trigger", 0.7)
    trig = float(trig) if isinstance(trig, (int, float)) and not isinstance(trig, bool) else 0.7
    tgt = r.get("thin_target", 1.0)
    tgt = float(tgt) if isinstance(tgt, (int, float)) and not isinstance(tgt, bool) else 1.0
    return g, mx, trig, tgt


def _agenda_scaled(b: dict, f: float, has_desc: bool) -> dict:
    """倍率 f での行の高さ・間隔・文字サイズ（agenda の既定値を f 倍。説明文は控えめに）。"""
    return {"row_h": int(round(b.get("row_h", 44) * f)), "gap": int(round(b.get("gap", 10) * f)),
            "text_size": int(round(b.get("text_size", 20) * f)), "num_size": int(round(b.get("num_size", 24) * f)),
            "num_w": int(round(b.get("num_w", 52) * f)),
            "desc_size": int(round(b.get("desc_size", 14) * (1 + (f - 1) * AGENDA_DESC_GROW)))}


@fitter("agenda")
def _fit_agenda(ctx: Ctx) -> None:
    """項目が少ない（既定の行の高さで並べても本文の thin_trigger 割未満）とき、行の高さ・間隔・番号・見出し・説明の文字を
    同じ倍率で大きくして本文の高さを使い、行の並びを本文の縦中央（少し上寄り）に置く。折り返しが悪くならない倍率まで。
    利用者が行の高さ・文字・本文の位置を style に書いたスライドは動かさない。"""
    b = ctx.st.get("body")
    items = ctx.slide.get("items")
    if not isinstance(b, dict) or not isinstance(items, list) or not items or not ctx.adjust:
        return
    if any(ctx.explicit("body", k) for k in AGENDA_FIXED_KEYS):
        return
    gp = single_grow_params(b)
    if gp is None:
        return
    grow, mx, trig, tgt = gp
    its = norm_items(items)
    n = len(its)
    has_desc = any(it.get("desc") for it in its)
    base = _agenda_scaled(b, 1.0, has_desc)
    h = float(b.get("h", 452))
    pitch0 = base["row_h"] + base["gap"]
    if n * pitch0 >= h * trig:
        return                                    # すでに本文を使っている（項目が多い）
    f_fit = (h * tgt) / (n * pitch0)              # 描画側の 1 列に入る行数の数え方（h // (row_h + gap)）に合わせ、最後の行の下の間隔も含める
    col_w = float(b.get("w", 1088))
    bold = True if has_desc else False
    base_prof = [wrap_profile(it.get("text", ""), base["text_size"], col_w - base["num_w"], None, has_desc) for it in its]
    desc_prof = [wrap_profile(it.get("desc", ""), base["desc_size"], col_w - base["num_w"]) if it.get("desc") else None for it in its]
    f = min(grow, mx / max(base["text_size"], 1), f_fit)
    pick = None
    while f > 1.04:
        sc = _agenda_scaled(b, f, has_desc)
        ok = sc["text_size"] <= mx and n * (sc["row_h"] + sc["gap"]) <= h * tgt + 0.5
        for sf in WRAP_CHECK_SAFETIES:
            w_ = (col_w - sc["num_w"]) * sf
            for it, bp, dp in zip(its, base_prof, desc_prof):
                if not wrap_not_worse(bp, wrap_profile(it.get("text", ""), sc["text_size"], w_, None, has_desc)):
                    ok = False
                if dp is not None and not wrap_not_worse(dp, wrap_profile(it.get("desc", ""), sc["desc_size"], w_)):
                    ok = False
        if ok:
            pick = (f, sc)
            break
        f -= 0.04
    if pick is None:
        return
    f, sc = pick
    total = n * (sc["row_h"] + sc["gap"]) - sc["gap"]
    for k, v in sc.items():
        ctx.set("body", k, v)
    ratio = b.get("thin_valign_ratio", 0.45)
    ratio = float(ratio) if isinstance(ratio, (int, float)) and not isinstance(ratio, bool) else 0.45
    shift = max(0.0, (h - total) * ratio)
    if shift >= 1:
        ctx.set("body", "y", int(round(b.get("y", 196) + shift)))      # h は変えない（build_deck.expand_slides の 1 枚に入る行数の見積もりが変わらないように）
    ctx.info["agenda"] = {"factor": round(f, 2), "total": round(total, 1), "n": n}


# ---------------------------------------------------------------------------
# status_table
# ---------------------------------------------------------------------------

def flatten_status_items(items, level: int = 0) -> list:
    """status_table のセル内容（文字列 or {text, children} の入れ子）を (level, text) の平坦な列にする。"""
    out = []
    for it in items or []:
        if isinstance(it, dict):
            out.append((level, str(it.get("text", ""))))
            out += flatten_status_items(it.get("children"), level + 1)
        else:
            out.append((level, str(it)))
    return out


def status_table_rows(slide: dict, tr: dict, size=None):
    """status_table の列幅（px）と、各行がセルの内容から必要とする高さ。戻り値 (ws, [{row, cells, need}])。
    build_deck.status_table_geometry（HTML/PPTX の行配置）と自動フィットで共通。"""
    cols = slide.get("columns", [])
    widths = tr.get("col_widths") or [1] * len(cols)
    if len(widths) != len(cols):
        widths = [1] * len(cols)
    unit = tr["w"] / sum(widths)
    ws = [w * unit for w in widths]
    size = size if size is not None else tr["cell_size"]
    lh, indent = tr["line_height"], tr["indent"]
    rows = []
    for row in slide.get("rows", []):
        cells = [flatten_status_items(c) for c in row.get("cells", [])]
        need = tr["label_size"] * 1.4 + 2 * tr["pad_y"]
        for j, paras in enumerate(cells):
            avail = ws[j + 2] - 2 * tr["pad_x"] if j + 2 < len(ws) else 100
            h = sum(ja_text.estimate_lines(text, size, avail - indent * (lv + 1)) * size * lh + tr["item_gap"]
                    for lv, text in paras)
            need = max(need, h + 2 * tr["pad_y"])
        rows.append({"row": row, "cells": cells, "need": need})
    return ws, rows


def _thin_grow_status_table(ctx: Ctx, tr: dict, cap, avail: float, total: float):
    """行が少なく表が枠の thin_trigger 割に届かないとき、セルの文字を cap から thin_grow 倍（thin_max_size px）まで大きくした (大きさ, 行の高さの合計)。
    どのセルも、折り返しの行数・語の途中の折れ・短い最終行が悪くならない大きさだけ（wrap_not_worse）。大きくしないとき None。"""
    gp = single_grow_params(tr)
    if gp is None or not ctx.adjust:
        return None
    grow, mx, trig, _ = gp
    if total >= avail * trig:
        return None
    cols = ctx.slide.get("columns") or []
    ws, base_rows = status_table_rows(ctx.slide, tr, cap)
    cells = [(lv, text, j) for r in base_rows for j, paras in enumerate(r["cells"]) for lv, text in paras]

    def profs(size, sf):
        return [wrap_profile(text, size, max(10.0, (ws[j + 2] - 2 * tr["pad_x"] - tr["indent"] * (lv + 1)) * sf)) if j + 2 < len(ws) else None
                for lv, text, j in cells]
    base = profs(cap, 1.0)
    top = int(min(cap * grow, mx))
    for s_ in range(top, int(cap), -1):
        _, rr = status_table_rows(ctx.slide, tr, s_)
        tot = sum(r["need"] for r in rr)
        if tot > avail * trig + 0.5:
            continue
        if all(b is None or wrap_not_worse(b, c) for sf in WRAP_CHECK_SAFETIES for b, c in zip(base, profs(s_, sf))):
            return s_, tot
    return None


@fitter("status_table")
def _fit_status_table(ctx: Ctx) -> None:
    tr = ctx.st.get("table")
    rows = ctx.slide.get("rows")
    cols = ctx.slide.get("columns")
    need_keys = ("w", "cell_size", "line_height", "indent", "label_size", "pad_y", "pad_x", "item_gap", "header_h", "y", "h")
    if (not isinstance(tr, dict) or not isinstance(rows, list) or not rows or not isinstance(cols, list)
            or any(k not in tr for k in need_keys) or not all(isinstance(r, dict) for r in rows)):
        return
    bottom = min(tr["y"] + tr["h"], ctx.content_bottom("table"))
    avail = bottom - tr["y"] - tr["header_h"]
    cap = tr["cell_size"]
    fixed = ctx.fixed("table", "cell_size")
    floor = min(tr.get("min_size", 11), cap)
    res = None
    for s_ in size_candidates(cap, floor, fixed):
        _, rr = status_table_rows(ctx.slide, tr, s_)
        total = sum(r["need"] for r in rr)
        res = {"size": s_, "total": total, "fits": total <= avail + 0.5}
        if res["fits"]:
            break
    if res["fits"] and res["size"] == cap and not fixed:
        grown = _thin_grow_status_table(ctx, tr, cap, avail, res["total"])
        if grown:
            res = {"size": grown[0], "total": grown[1], "fits": True}
    if res["size"] != cap:
        ctx.set("table", "cell_size", res["size"])
    ctx.info["status_table"] = {"size": res["size"], "total": round(res["total"], 1), "avail": round(avail, 1), "cap": cap,
                                "fits": res["fits"]}
    ws, rr_final = status_table_rows(ctx.slide, tr, res["size"])
    words = []
    for r in rr_final:
        lab = r["row"].get("label")
        if lab and ws:
            words.append((str(lab), tr.get("label_size", 15), ws[0] - 2 * tr["pad_x"], "行見出し"))
        for j, paras in enumerate(r["cells"]):
            if j + 2 < len(ws):
                words += [(text, res["size"], ws[j + 2] - 2 * tr["pad_x"] - tr["indent"] * (lv + 1), "セル") for lv, text in paras]
    long_word_check(ctx, words)
    if not res["fits"]:
        over = int(res["total"] - avail)
        if over > 6:
            m, acc = 0, 0.0
            for r in status_table_rows(ctx.slide, tr, res["size"])[1]:
                if acc + r["need"] > avail + 0.5:
                    break
                acc += r["need"]
                m += 1
            if fixed:
                ctx.warn("status_table-overflow",
                         f"{{label}}: 表が枠の高さを約{over}px超える見込みです（{ctx.by_spec(f'style.table.cell_size={cap}')}・{len(rows)}行）"
                         f" → 行を {m} 行以下に減らして 2 枚に分けるか、cell_size を下げる{ctx.undo_hint()}")
            else:
                ctx.warn("status_table-overflow",
                         f"{{label}}: 表は {res['size']}px まで縮めても枠の高さを約{over}px超えます（{len(rows)}行）"
                         f" → 行を {m} 行以下に減らして 2 枚に分ける（セルの文を短くするのも有効）")
    elif cap - res["size"] >= 2:
        ctx.note("status_table-shrunk",
                 f"{{label}}: 表の文字を {cap}px → {res['size']}px に縮めました（{len(rows)}行）"
                 f" → 大きく読ませたいときは行を減らすか 2 枚に分ける")


# ---------------------------------------------------------------------------
# matrix
# ---------------------------------------------------------------------------

MATRIX_HEAD_H = 26
MATRIX_HEAD_GAP = 4
MATRIX_BODY_LH = 1.4
MATRIX_AXIS_H = 46          # 格子の下にある軸ラベルの高さ（pe.shrink_for_bottom と同じ）


def _matrix_axis_words(ctx: Ctx, g: dict) -> list:
    """軸ラベルの箱（build_deck の matrix 描画と同じ幅）に入らない長い文字列を拾う。"""
    ax = ctx.st.get("axis") or {}
    size = ax.get("size", 15)
    xa, ya = ctx.slide.get("x_axis") or {}, ctx.slide.get("y_axis") or {}
    if not isinstance(xa, dict) or not isinstance(ya, dict):
        return []
    gw = g.get("w", 1000)
    return [(str(ya.get("label", "")), size, 360 - size * 2, "縦軸の名前"), (str(ya.get("high", "")), size, 88, "縦軸の「高」ラベル"),
            (str(ya.get("low", "")), size, 88, "縦軸の「低」ラベル"), (str(xa.get("label", "")), size, gw - size * 2, "横軸の名前"),
            (str(xa.get("low", "")), size, 160, "横軸の「低」ラベル"), (str(xa.get("high", "")), size, 160, "横軸の「高」ラベル")]


@fitter("matrix")
def _fit_matrix(ctx: Ctx) -> None:
    import proposal_engine as pe
    g = ctx.st.get("grid")
    quads = ctx.slide.get("quadrants")
    if not isinstance(g, dict) or not isinstance(quads, list):
        return
    quads = [q for q in quads if isinstance(q, dict)]
    gap, pad = g.get("gap", 14), g.get("pad", 18)
    bottom = g.get("y", 208) + g.get("h", 372)
    if pe.reserve(ctx.slide, ctx.view()):
        bottom = min(bottom, ctx.content_bottom("grid") - MATRIX_AXIS_H)
    ch = (bottom - g.get("y", 208) - gap) / 2
    cw = (g.get("w", 1000) - gap) / 2
    body_w = cw - 2 * pad
    cap = g.get("body_size", 14)
    fixed = ctx.fixed("grid", "body_size")
    floor = min(g.get("min_size", 12), cap)
    res = None
    for s_ in size_candidates(cap, floor, fixed):
        need = max((MATRIX_HEAD_H + MATRIX_HEAD_GAP + ja_text.estimate_lines(q.get("body", ""), s_, body_w) * s_ * MATRIX_BODY_LH
                    if q.get("body") else MATRIX_HEAD_H) + 2 * pad for q in quads) if quads else 0
        res = {"size": s_, "need": need, "fits": need <= ch + 0.5}
        if res["fits"]:
            break
    if res and res["size"] != cap:
        ctx.set("grid", "body_size", res["size"])
    if res:
        ctx.info["matrix"] = {"size": res["size"], "need": round(res["need"], 1), "cell_h": round(ch, 1), "fits": res["fits"]}
        if not res["fits"] and int(res["need"] - ch) > 6:
            ctx.warn("matrix-overflow",
                     f"{{label}}: 象限の文が{'指定の' if fixed else ''} {res['size']}px"
                     f"{'のまま' if fixed else 'まで縮めても'}枠の高さを約{int(res['need'] - ch)}px超える見込みです"
                     f" → 象限の本文を短くする（目安: {max(1, int((ch - 2 * pad - MATRIX_HEAD_H - MATRIX_HEAD_GAP) // (res['size'] * MATRIX_BODY_LH)))} 行以内）")
        elif res["size"] < cap and cap - res["size"] >= 2:
            ctx.note("matrix-shrunk", f"{{label}}: 象限の文字を {cap}px → {res['size']}px に縮めました")
    long_word_check(ctx, [(q.get("body", ""), ctx.val("grid", "body_size", cap), body_w, "象限") for q in quads]
                    + [(q.get("heading", ""), g.get("heading_size", 17), body_w, "象限の見出し") for q in quads]
                    + _matrix_axis_words(ctx, g))
    # 散布の点のラベル（pe.matrix_points）: 長いと何行にも折れて象限の外にあふれる
    for k, pt in enumerate(ctx.slide.get("points") or []):
        if isinstance(pt, dict) and pt.get("label"):
            lines = ja_text.estimate_lines(str(pt["label"]), pe.POINT_LABEL_SIZE, pe.POINT_LABEL_W, None, bool(pt.get("highlight")))
            if lines > 2:
                ctx.warn("matrix-point-label",
                         f"{{label}}: points[{k}] のラベルが{lines}行に折れます（{len(str(pt['label']))}字・幅 {pe.POINT_LABEL_W}px）"
                         f" → ラベルは 1〜2 行（全角 14 字前後）に短くし、詳細は本文に回す")
                break


# ---------------------------------------------------------------------------
# 提案書系（summary / reasons / row_matrix / house / kpi_tree / cycle / org / statement）
# ---------------------------------------------------------------------------

_PROPOSAL_WHAT = {
    "summary": ("要点の行", "項目を減らす（目安 3〜6 個）か、説明文を短くする。2 枚に分けてもよい"),
    "reasons": ("課題と強みの行", "行を減らす（目安 3 行前後）か、文を短くする。2 枚に分けてもよい"),
    "row_matrix": ("表のセル", "行を減らす（目安 6 行以内）かセルの文を短くする。2 枚に分けてもよい"),
    "row_matrix.label": ("行見出し", "行見出しを短くする"),
    "row_matrix.head": ("列見出し", "列見出しを短くするか、列を減らす"),
    "house": ("柱の本文", "柱の項目を減らすか文を短くする（目安 3〜4 本・各 3 項目）"),
    "house.head": ("柱の見出し", "柱の見出しを短くする"),
    "house.roof": ("屋根の文字", "屋根の文を短くする"),
    "house.found": ("土台の文字", "土台の文を短くする"),
    "cycle": ("段の本文", "段の文を短くするか、段を減らす（目安 3〜6 段）"),
    "kpi_tree": ("KPI の文字", "KPI の行を減らす（目安 6 行以内）か文を短くする"),
    "kpi_tree.root": ("目標の文字", "目標の文を短くする（目安: 30 字以内）"),
    "kpi_tree.kpi": ("KPI の名前", "KPI の行を減らすか名前を短くする（目安 6 行以内）"),
    "kpi_tree.value": ("目標値", "目標値を短くする（「10%」のような短い値にし、説明は測り方へ）か、KPI の行を減らす"),
    "kpi_tree.note": ("測り方", "測り方を短くするか、KPI の行を減らす"),
    "org": ("ノードの文字", "ノードを減らすか、名前・役割を短くする"),
    "statement": ("メッセージ", "文を短くする（目安: 全角 40 字前後）"),
}


def _element_wrap_profiles(els, sf: float = 1.0) -> list:
    """canvas 要素列の各段落の折り返し [(行数, 最終行の字数, 語の途中の折れ)]（文字を持たない要素は空の列）。幅は要素の幅から左右の余白を引いたもの（sf 倍）。"""
    out = []
    for e in els:
        profs = []
        tx = e.get("text") if isinstance(e, dict) else None
        if isinstance(tx, dict):
            ins = tx.get("insets") or [0, 0, 0, 0]
            w = float(e.get("w", 0)) - float(ins[0] if len(ins) > 0 else 0) - float(ins[2] if len(ins) > 2 else 0)
            for para in tx.get("paragraphs") or []:
                runs = [r for r in para.get("runs") or [] if isinstance(r, dict) and r.get("text")]
                if not runs or not isinstance(runs[0].get("size"), (int, float)):
                    continue
                text = "".join(str(r["text"]) for r in runs)
                bold = bool(runs[0].get("bold"))
                profs.append(wrap_profile(text, runs[0]["size"], max(10.0, w * sf), ja_text.heading_fonts() if bold else None, bold))
        out.append(profs)
    return out


def _scaled_wrap_ok(slide: dict, view: dict, k: float, base_els, base_prof) -> bool:
    """倍率 k で拡大した図（自然な大きさで、枠を 1/k にして組んだもの）の文字が、k = 1 より折り返しで悪くならないか（wrap_not_worse。
    行数・語の途中の折れ・最終行の短さ）。要素の並びが変わる（数が違う）ときは悪くなると見なす。"""
    import proposal_engine as pe
    els = pe.layout_elements(slide, {**view, "body": {**view["body"], "scale_k": k}})
    if len(els) != len(base_els):
        return False
    for sf in WRAP_CHECK_SAFETIES:
        cand = _element_wrap_profiles(els, sf)
        for a_, b_ in zip(base_prof, cand):
            if len(a_) != len(b_) or not all(wrap_not_worse(x, y) for x, y in zip(a_, b_)):
                return False
    return True


def _scale_proposal(ctx: Ctx) -> None:
    """合成のブロックに置いた org / kpi_tree は、枠に対して小さいので、自然な大きさで組んだ図を同じ倍率 k で拡大する
    （proposal_engine.layout が style.body.scale_k に従って canvas_engine.transform_elements で k 倍する）。
    k は、自然な大きさで組んだときに文字の大きさの選択（_fit）が縮まず・枠に収まる最大の倍率で、thin_grow まで・文字が thin_max_size px を超えない範囲。
    利用者が scale_k を書いたとき（1 で止まる）・autofit: false のときは動かさない。"""
    import proposal_engine as pe
    body = ctx.st.get("body")
    if not isinstance(body, dict) or not body.get("block_rect") or not ctx.adjust or ctx.explicit("body", "scale_k"):
        return
    gp = thin_grow_params(body)
    if gp is None:
        return
    grow, mx, _ = gp
    view = ctx.view()
    base = [e for e in pe.fit_report(ctx.slide, view) if e["ok"]]
    if not base or any(not e["ok"] for e in pe.fit_report(ctx.slide, view)):
        return                                   # すでに枠に収まらない（拡大しない）

    def top_size(e):
        c = e["chosen"]
        vals = [x for x in (c if isinstance(c, (list, tuple)) else [c]) if isinstance(x, (int, float))]
        return max(vals) if vals else 0
    text_sizes = [top_size(e) for e in base if not str(e["tag"]).endswith(".value")] or [top_size(e) for e in base]     # 目標値（大きな数字）は上限の判定に入れない
    cap_k = min(grow, mx / max(max(text_sizes), 1))
    k = cap_k
    base_els = pe.layout_elements(ctx.slide, {**view, "body": {**view["body"], "scale_k": 1}})
    base_prof = _element_wrap_profiles(base_els)
    while k > 1.04:
        kk = round(k, 3)
        ent = pe.fit_report(ctx.slide, {**view, "body": {**view["body"], "scale_k": kk}})
        if ent and len(ent) == len(base) and all(e["ok"] for e in ent) and all(e["chosen"] == b["chosen"] for e, b in zip(ent, base)) and _scaled_wrap_ok(
                ctx.slide, view, kk, base_els, base_prof):
            ctx.set("body", "scale_k", kk)
            ctx.info["proposal_scale"] = kk
            return
        k -= 0.05


def _grow_cycle(ctx: Ctx) -> None:
    """cycle: パネルに余裕があるとき（既定の候補の最大の大きさで収まる）、本文の文字を grow_sizes の大きい方から試して大きくする。
    パネルの高さに収まり、見出し・項目の折り返しが悪くならない（語の途中の折れ・短い最終行・行数が増えない）最大の大きさを、
    style.body.sizes の先頭に足す（utility: proposal_engine の _fit は sizes の大きい順に試す）。利用者が sizes を書いたときは動かさない。"""
    import proposal_engine as pe
    body = ctx.st.get("body")
    grow = body.get("grow_sizes") if isinstance(body, dict) else None
    if (not ctx.adjust or ctx.explicit("body", "sizes") or not isinstance(grow, list)
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in grow)):
        return
    view = ctx.view()
    ent = [e for e in pe.fit_report(ctx.slide, view) if e["tag"] == "cycle"]
    if not ent or not ent[0]["ok"] or ent[0]["chosen"] != ent[0]["cap"]:
        return                                  # すでに縮めている（パネルに余裕が無い）
    base = ent[0]["chosen"]
    sizes = list(view["body"].get("sizes") or [15, 14, 13, 12, 11])
    reg = pe.body_region(ctx.slide, view)
    g = view["body"]
    n = max(len(ctx.slide.get("stages") or []), 1)
    ring_w = min(g.get("ring_d", 300), reg["h"], reg["w"] * 0.32)
    pw = (reg["w"] - ring_w) / 2 - g.get("side_gap", 24)
    tw = pw - g.get("badge_d", 30) - 2 * g.get("pad", 12)
    stages = [s_ if isinstance(s_, dict) else {"title": str(s_)} for s_ in ctx.slide.get("stages") or []]

    def profs(sz, sf):
        out = []
        for s_ in stages:
            text, its = pe.as_items(s_.get("items") if s_.get("items") is not None else s_.get("text"))
            out.append(wrap_profile(s_.get("title", ""), sz + 2, tw * sf, ja_text.heading_fonts(), True))
            if text:
                out.append(wrap_profile(text, sz, tw * sf))
            out += [wrap_profile(t, sz, (tw - sz) * sf) for t in its]
        return out
    b0 = profs(base, 1.0)
    for sz in sorted([x for x in grow if x > base], reverse=True):
        ent2 = [e for e in pe.fit_report(ctx.slide, {**view, "body": {**g, "sizes": [sz]}}) if e["tag"] == "cycle"]
        if ent2 and ent2[0]["ok"] and all(wrap_not_worse(a, b) for sf in WRAP_CHECK_SAFETIES for a, b in zip(b0, profs(sz, sf))):
            ctx.set("body", "sizes", [sz] + sizes)
            ctx.info["cycle_grown"] = sz
            return


@fitter("summary", "reasons", "row_matrix", "house", "kpi_tree", "cycle", "org", "statement")
def _fit_proposal(ctx: Ctx) -> None:
    """提案書系は proposal_engine が文字サイズの候補表から選ぶ。最小の候補でも収まらないときに黙らず警告する。
    候補表（上限）は style.<領域>.sizes。密度ごとの候補は layout の densities に置く。"""
    import proposal_engine as pe
    if ctx.type == "cycle":
        _grow_cycle(ctx)
    elif ctx.type in ("org", "kpi_tree"):
        _scale_proposal(ctx)
    view = ctx.view()
    entries = pe.fit_report(ctx.slide, view)
    if not entries:
        return
    ctx.info["proposal"] = {}
    for e in entries:
        ctx.info["proposal"].setdefault(e["tag"], e["chosen"])
    seen = set()
    sized = bool((view.get("body") or {}).get("sizes")) and ctx.explicit("body", "sizes")
    for e in entries:
        tag = e["tag"]
        if e["ok"] or tag in seen:
            continue
        seen.add(tag)
        what, hint = _PROPOSAL_WHAT.get(tag, ("文字", "項目を減らすか文を短くする"))
        ch = e["chosen"]
        ch_s = "/".join(str(x) for x in ch) if isinstance(ch, (list, tuple)) else str(ch)
        extra = "（style の sizes の指定どおり）" if sized and tag == ctx.type else ""
        if not ctx.adjust:
            extra = "（autofit が切られているため縮めていません）"
        ctx.warn(f"{ctx.type}-overflow",
                 f"{{label}}: {what}が最小の文字サイズ（{ch_s}px）まで縮めても枠に収まりません{extra} → {hint}")
    shrunk = [e for e in entries if e["ok"] and e["tag"] == ctx.type and isinstance(e["cap"], (int, float))
              and isinstance(e["chosen"], (int, float)) and e["cap"] - e["chosen"] >= 3]
    if shrunk:
        e = shrunk[0]
        ctx.note(f"{ctx.type}-shrunk", f"{{label}}: 文字を {e['cap']}px → {e['chosen']}px に縮めました"
                                       f" → 大きく読ませたいときは項目を減らすか 2 枚に分ける")


# ---------------------------------------------------------------------------
# chart（dataviz_engine）: 配置の試算で分かる問題（ラベルの重なり・注釈の衝突・カテゴリ間引き）を警告にする
# ---------------------------------------------------------------------------

_DIAG_COLORS = {"background": "#FFFFFF", "text": "#1A2233", "muted": "#5A6B85", "primary": "#0F3D6E", "accent": "#007D96",
                "surface": "#E0E7F0", "border": "#BCC8D8", "on_primary": "#FFFFFF", "heading_text": "#0F3D6E"}


@fitter("chart")
def _fit_chart(ctx: Ctx) -> None:
    """グラフの配置は dataviz_engine が矩形から決める（文字サイズは矩形に合わせて縮む）。ここでは実際のスタイル・本文矩形
    （リード・結論帯・出典の有無を反映）で試算し、診断（ラベルが重なる・注釈が近すぎる等）を警告にする。色は寸法に影響しない。"""
    import proposal_engine as pe
    import dataviz_engine as dv
    if not isinstance(ctx.slide.get("series"), (list, type(None))):
        return          # 型違いは validate が fail にする
    view = ctx.view()
    body = pe.body_region(ctx.slide, view)
    fonts = {"body": ja_text._default_fonts.get("body") or None, "heading": ja_text._default_fonts.get("heading") or None}
    try:
        pctx = pe.Ctx({"colors": _DIAG_COLORS, "fonts": {k: v for k, v in fonts.items() if v}})
        diags = dv.diagnose_chart(ctx.slide, view, pctx, body)
    except Exception as e:      # noqa: BLE001  （試算で落ちても検証全体は止めない。入力の誤りは validate が fail にする）
        ctx.warn("chart-diagnose", f"{{label}}: グラフの配置試算に失敗しました（{type(e).__name__}）。データの形を確かめてください")
        return
    for code, msg in diags:
        ctx.warn(f"chart-{code}", f"{{label}}: {msg}")


# ---------------------------------------------------------------------------
# code: 等幅の固定行送りなので、最小サイズでも枠に収まらなければ警告する（PPTX は枠の下・右へ文字が流れる）
# ---------------------------------------------------------------------------

def _mono_em(line: str) -> float:
    """コード 1 行の幅（em）。等幅フォントの字幅（半角 0.58em・全角 1.1em。タブは 4 桁）。"""
    return sum(1.1 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.58 for ch in line.expandtabs(4))


def code_fit(code: str, r: dict) -> dict:
    """コード領域に収まる文字サイズ（HTML / PPTX 共通）。純関数。
    戻り値 {size, lines（行の配列）, need_h, avail_h, longest_em, avail_w, fits_h, fits_w}。min_size まで縮めても収まらなければ fits_* が偽。"""
    lines = code.splitlines() or [""]
    size = r["size"]
    lh = r["line_height"]
    avail_h = r["h"] - 2 * r["pad"]
    avail_w = r["w"] - 2 * r["pad"]
    longest = max(_mono_em(ln) for ln in lines)
    floor = r.get("min_size", 12)
    while size > floor and (len(lines) * size * lh > avail_h or longest * size > avail_w):
        size -= 1
    need = len(lines) * size * lh
    return {"size": size, "lines": lines, "need_h": need, "avail_h": avail_h, "longest_em": longest, "avail_w": avail_w,
            "fits_h": need <= avail_h + 0.5, "fits_w": longest * size <= avail_w + 0.5}


@fitter("code")
def _fit_code(ctx: Ctx) -> None:
    r = ctx.st.get("code")
    code = ctx.slide.get("code")
    if not isinstance(r, dict) or not isinstance(code, str) or not all(k in r for k in ("size", "line_height", "pad", "w", "h")):
        return
    res = code_fit(code, r)
    ctx.info["code"] = {"size": res["size"], "lines": len(res["lines"]), "fits": res["fits_h"] and res["fits_w"]}
    if not res["fits_h"]:
        per = res["size"] * r["line_height"]
        ctx.warn("code-overflow",
                 f"{{label}}: コードが{len(res['lines'])}行あり、最小の文字サイズ（{res['size']}px）でも枠の高さを約{int(res['need_h'] - res['avail_h'])}px超えます"
                 f"（PowerPoint では枠の下へ文字が流れます） → 行数を減らす（この大きさでは {max(1, int(res['avail_h'] // per))} 行まで）か、2 枚に分ける")
    if not res["fits_w"]:
        ctx.warn("code-wide",
                 f"{{label}}: コードの最長行が{res['size']}px で枠の幅を約{int(res['longest_em'] * res['size'] - res['avail_w'])}px超えます"
                 f"（折り返さないので右へはみ出します） → 長い行を改行する、または短くする")


# ---------------------------------------------------------------------------
# schedule: 行が少ないとき、行の高さと文字を大きくして、図が上に寄って下が空くのを避ける（S4）
# ---------------------------------------------------------------------------

@fitter("architecture", "dataflow", "lifecycle", "sequence")
def _fit_diagram(ctx: Ctx) -> None:
    """合成のブロックに置いた図解は、枠に対して図が小さい（文字・箱が自然な大きさのまま）ので、図全体を同じ倍率 k で拡大する
    （diagram_scale。座標・箱・線の太さ・文字を k 倍して枠の中に置く）。k は、図の文字が縮まない・折り返しが増えない・
    診断（error / warn）が増えない最大の倍率で、thin_grow（既定 1.5）まで・見出しの文字が thin_max_size px を超えない範囲。
    style.diagram.scale_k を書いたとき（1 で止まる）・autofit: false・thin_grow が 1 のときは動かさない。"""
    import diagram_scale as dscale
    d = ctx.st.get("diagram")
    if not isinstance(d, dict) or not d.get("block_rect") or not ctx.adjust or ctx.explicit("diagram", "scale_k"):
        return
    gp = thin_grow_params(d)
    if gp is None:
        return
    grow, mx, _ = gp
    k, _why = dscale.best_scale(ctx.slide, ctx.type, d, grow, mx)
    if k > 1.0:
        ctx.set("diagram", "scale_k", k)
        ctx.info["diagram"] = {"scale_k": k}


@fitter("schedule")
def _fit_schedule(ctx: Ctx) -> None:
    """行 1〜3 本の矢羽根スケジュールは、図が枠の 6 割に満たない（既定の行の高さ × 行数 < 枠 × thin_trigger）とき、
    行の高さ・矢羽根の太さを f 倍（thin_grow まで。図が枠の thin_target 割になる倍率）、文字を min(f, thin_text_grow) 倍にする。
    値はレイアウト JSON の chart 領域のトークン。利用者が書いた値（style.chart）・autofit: false のときは動かさない。"""
    c = ctx.st.get("chart")
    rows = [r for r in (ctx.slide.get("rows") or []) if isinstance(r, dict)]
    if not isinstance(c, dict) or not rows or not ctx.adjust:
        return
    grow = c.get("thin_grow")
    if not isinstance(grow, (int, float)) or isinstance(grow, bool) or grow <= 1.0:
        return
    sized = ("max_row_h", "bar_max_h", "label_size", "sub_size", "bar_size", "col_size", "period_size", "col_h", "period_h", "min_row_h")
    if any(ctx.explicit("chart", k) for k in sized):
        return                      # 利用者が行の高さ・文字の大きさのどれかを書いたスライドは、手で整えたものとして動かさない
    h_chart = c.get("h_no_lead", c.get("h", 486)) if not ctx.slide.get("lead") else c.get("h", 486)
    legend_h = c.get("legend_h", 28) if ctx.slide.get("legend", True) is not False else 0
    period_h = c.get("period_h", 30) if ctx.slide.get("periods") else 0
    area = h_chart - period_h - c.get("col_h", 28) - legend_h
    row_h = c.get("max_row_h", 64)
    natural = len(rows) * row_h
    if area <= 0:
        return
    fill = natural >= area * float(c.get("thin_trigger", 0.6))
    if fill:
        # 4 行以上（S5a）: 図（行 + 期間・列見出し・凡例）が枠の fill_trigger 割に満たないとき、行の高さを配って fill_target 割まで使う（倍率は fill_grow まで）。文字は控えめに（fill_text_grow まで）
        ft = float(c.get("fill_trigger", 0) or 0)
        if ft <= 0 or natural + (h_chart - area) >= h_chart * ft:
            return
        f = min(float(c.get("fill_grow", 1.3)), (h_chart * float(c.get("fill_target", 0.95)) - (h_chart - area)) / natural)
        tg = min(f, float(c.get("fill_text_grow", 1.2)))
    else:
        f = min(float(grow), float(c.get("thin_target", 0.75)) * area / natural)
        tg = min(f, float(c.get("thin_text_grow", 1.5)))
    if f < 1.1:
        return
    # 4 行以上（fill）: 行見出し（label・sub）の文字を大きくして折り返しが悪くならないか（wrap_not_worse）。悪くなるなら、文字は大きくせず行の高さだけ配る
    # 1〜3 行（S4 の薄い分岐）は変更前と同じ（この判定は掛けない）
    wpx = max(10.0, float(c.get("label_w", 232)) - 2 * float(c.get("label_pad", 10)))
    for key in ("label_size", "sub_size"):
        v = c.get(key)
        if fill and isinstance(v, (int, float)) and not isinstance(v, bool) and tg > 1.0:
            texts = [str(r_.get("label" if key == "label_size" else "sub", "")) for r_ in rows]
            nv = round(v * tg)
            if not all(wrap_not_worse(wrap_profile(t, v, wpx), wrap_profile(t, nv, wpx * sf)) for t in texts if t for sf in WRAP_CHECK_SAFETIES):
                tg = 1.0
                break
    caps = {"label_size": 24, "sub_size": 17, "bar_size": 22, "col_size": 18, "period_size": 18, "milestone_label_size": 16,
            "legend_size": 15, "note_size": 15, "group_size": 18}
    for key, cap in caps.items():
        v = c.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            ctx.set("chart", key, min(cap, round(v * tg)) if v < cap else v)
    for key, k in (("max_row_h", f), ("bar_max_h", f), ("col_h", min(f, 1.4)), ("period_h", min(f, 1.4)), ("milestone_size", min(f, 1.4))):
        v = c.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            ctx.set("chart", key, round(v * k))
    ctx.info["schedule"] = {"grown": round(f, 2), "rows": len(rows), "area": round(area, 1), "fill": fill}

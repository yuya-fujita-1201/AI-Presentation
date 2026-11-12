#!/usr/bin/env python3
"""大きな数字（kpi）とデータグラフ（chart）のレイアウトエンジン。

proposal_engine と同じ契約の純関数 ``layout_kpi(slide, st, ctx, body)`` / ``layout_chart(slide, st, ctx, body)`` が、
canvas_engine の要素列（shape / text。色は #RRGGBB に解決済み）を返す。描画は canvas_engine が担うので、
HTML と PPTX の両方で同じ図形になり、PowerPoint では棒・線・ラベルを1つずつ選んで編集できる。

- ``body`` は描く矩形（x, y, w, h）。全面（1136x452）だけでなく、小さい矩形（例 520x360）でも収まるよう、
  文字の大きさ・余白・目盛の数を矩形から決める（合成スライドのブロックとして使える）。
- 色はテーマトークン（primary / accent / muted / surface …）から作る。良し悪しの色（positive / negative）は
  テーマに無ければ控えめな既定色を使う。強調色（accent）は「変化後の値」「highlight に挙げた項目」だけに使う。
- 検証は ``validate(slide, i, fail, warn)``。レイアウト計算で分かる問題（ラベルが重なる・注釈が近すぎる等）も
  ``diagnose_chart`` で集めて警告にする。
"""
from __future__ import annotations

import difflib
import math
import re

import engine_registry
import ja_text
import proposal_engine as pe
import wrap_fix

LINE_H = pe.LINE_H
MIN_BAR_W = 4.0         # 棒の太さの下限（px）。これを下回るなら詰める／警告する

# ---------------------------------------------------------------------------
# レイアウト既定値（templates/layouts/default.json の types.kpi / types.chart に入れる）
# ---------------------------------------------------------------------------

_CHROME = {
    "eyebrow": {"x": 72, "y": 16, "w": 1136, "h": 24, "size": 15, "color": "accent", "bold": True},
    "title": {"x": 72, "y": 42, "w": 1136, "h": 64, "size": 36, "color": "heading_text", "bold": True},
    "rule": {"x": 72, "y": 106, "w": 1136, "h": 5, "fill": "accent"},
    "lead": {"x": 72, "y": 134, "w": 1136, "h": 40, "size": 20, "color": "muted", "line_height": 1.5},
    "footer_l": {"x": 72, "y": 678, "w": 700, "h": 24, "size": 13, "color": "muted"},
    "footer_r": {"x": 1088, "y": 678, "w": 120, "h": 24, "size": 13, "color": "muted", "align": "right"},
}

_KPI_BODY = {
    "x": 72, "y": 192, "w": 1136, "h": 452, "y_no_lead": 140,
    "gap": 24, "pad_x": 28, "pad_y": 26, "radius": 14,
    "hero_max_size": 120, "tile_max_size": 100, "min_size": 26,      # 数字の大きさの上限・下限（px）。value_size で固定も可
    "tile_fill": "surface", "tile_line": "",
    "label_color": "text", "value_color": "primary", "to_color": "accent", "from_color": "muted",
    "note_color": "muted", "arrow_color": "muted",
    "bar_fill": "primary", "bar_track": "background", "bar_track_hero": "surface",
    "good_color": "#1F8A5B", "bad_color": "#C8382E", "neutral_color": "muted",
    "chip_tint": 0.86, "tile_min_ratio": 0.94,       # 1 段（2〜4 件）のタイルの高さの下限（本文領域の高さに対する割合）
}

_CHART_BODY = {
    "x": 72, "y": 192, "w": 1136, "h": 452, "y_no_lead": 140,
    "tick_size": 15, "cat_size": 17, "value_size": 18, "legend_size": 15, "note_size": 20, "anno_size": 15,
    "min_size": 11,
    "text_color": "text", "muted_color": "muted", "grid_color": "border", "axis_color": "muted",
    "base_color": "primary", "highlight_color": "accent", "fade_tint": 0.55, "forecast_tint": 0.5,
    "series_colors": ["primary", "accent", "muted"],
    "bar_max_w": 96, "bar_gap": 0.42, "bar_inner_gap": 4, "bar_h_max": 44,
    "line_w": 3.5, "line_w_dim": 2.25, "marker": 10,
    "anno_fill": "heading_text", "anno_color": "on_primary",
    "note_fill": "surface", "note_bar": "accent",
    "good_color": "#1F8A5B", "bad_color": "#C8382E",
    "donut_hole": 0.62,
}


def _copy(d):
    return {k: (dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)) for k, v in d.items()}


def default_layout() -> dict:
    """layout JSON の types に足す既定値（kpi / chart）。毎回新しい辞書を返す。"""
    out = {}
    for name, body in (("kpi", _KPI_BODY), ("chart", _CHART_BODY)):
        d = _copy(_CHROME)
        d["body"] = _copy(body)
        out[name] = d
    return out


DEFAULT_LAYOUT = default_layout()

# 良し悪しの色。テーマに positive / negative があればそちらを使う
SEMANTIC_COLORS = {"positive": "#1F8A5B", "negative": "#C8382E"}

try:      # 全タイプ共通のキー（autofit / density / pattern / blocks を含む）は deck_schema を正本にする
    from deck_schema import UNIVERSAL_SLIDE_KEYS as _UNIVERSAL_SLIDE_KEYS
except Exception:       # pragma: no cover  （deck_schema が無い古い配置でも動くように）
    _UNIVERSAL_SLIDE_KEYS = frozenset({"type", "notes", "style", "relation", "eyebrow", "conclusion", "source",
                                       "line_balance", "title", "autofit", "density", "pattern", "blocks"})
COMMON_SLIDE_KEYS = set(_UNIVERSAL_SLIDE_KEYS) | {"type", "title", "eyebrow", "lead", "conclusion", "source", "style",
                                                   "notes", "relation", "line_balance"}
KPI_SLIDE_KEYS = {"items"}
KPI_ITEM_KEYS = {"value", "unit", "from_unit", "label", "from", "delta", "good", "note", "of", "emphasis"}
CHART_KINDS = ("bar", "hbar", "stacked", "line", "waterfall", "donut")
CHART_ALIASES = {"column": "bar", "vbar": "bar", "barh": "hbar", "pie": "donut", "ring": "donut",
                 "stack": "stacked", "stacked_bar": "stacked", "lines": "line"}
CHART_SLIDE_KEYS = {"chart", "unit", "categories", "series", "highlight", "forecast_from", "annotations", "y",
                    "values", "note", "totals", "good"}
CHART_SERIES_KEYS = {"name", "values", "color"}
CHART_ANNO_KEYS = {"at", "text", "series"}
CHART_Y_KEYS = {"min", "max", "label", "step", "grid"}

KNOWN_KEYS = {
    "kpi": COMMON_SLIDE_KEYS | KPI_SLIDE_KEYS,
    "chart": COMMON_SLIDE_KEYS | CHART_SLIDE_KEYS,
}


# ---------------------------------------------------------------------------
# 小道具: 数値・色・文字幅
# ---------------------------------------------------------------------------

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def to_float(v):
    """数字として読める値なら float、読めなければ None（"1,200" "−68%" "6.5" などを許す）。"""
    if _is_num(v):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip().replace("−", "-").replace("▲", "").replace("▼", "").replace("＋", "+").replace("－", "-")
    s = s.replace(",", "").replace("，", "").rstrip("%％").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _decimals(values, cap=2) -> int:
    d = 0
    for v in values:
        if not _is_num(v):
            continue
        s = f"{round(float(v), cap):.{cap}f}".rstrip("0")
        d = max(d, len(s.split(".")[1]) if "." in s else 0)
    return d


TICK_DEC_CAP = 6        # 目盛の小数桁の上限（刻み 0.025 のような値を丸めないため）
VALUE_DEC_CAP = 4       # 値ラベルで「0 に潰れる小さい値」を救うときの小数桁の上限


def fmt_num(v, dec=0) -> str:
    """桁区切りつきの数字。負の値はマイナス記号（−）。"""
    if v is None:
        return ""
    s = f"{float(v):,.{dec}f}"
    if float(s.replace(",", "")) == 0:
        s = s.lstrip("-")
    return s.replace("-", "−")


_HEX6 = re.compile(r"#[0-9A-Fa-f]{6}")


def is_hex6(c) -> bool:
    return isinstance(c, str) and _HEX6.fullmatch(c) is not None


def fmt_val(v, dec=0) -> str:
    """値ラベル用。既定の小数桁で 0 に潰れてしまう小さい値（0.004 など）だけ、桁を増やして見えるようにする。"""
    if v is not None and _is_num(v) and v != 0:
        d = dec
        while d < VALUE_DEC_CAP and round(float(v), d) == 0:
            d += 1
        dec = d
    return fmt_num(v, dec)


def _hex(c):
    if not is_hex6(c):          # 不正な色でも例外にしない（黒として扱う）
        return (0, 0, 0)
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a: str, b: str, t: float) -> str:
    """a と b を混ぜる（t=0 で a、t=1 で b）。t は 0〜1 に、各チャンネルは 0〜255 に収める。"""
    t = max(0.0, min(1.0, t))
    ra, rb = _hex(a), _hex(b)
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x * (1 - t) + y * t))) for x, y in zip(ra, rb))


def luminance(c: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in _hex(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def col(ctx, token, default="#000000") -> str:
    """トークン→hex。positive / negative はテーマに無ければ既定色。解決できない値（不正な hex など）は default。"""
    if isinstance(token, str) and token in SEMANTIC_COLORS and token not in ctx.colors:
        return SEMANTIC_COLORS[token]
    c = ctx.c(token, default)
    return c.upper() if is_hex6(c) else (default if is_hex6(default) else "#000000")


def resolve_color(ctx, token):
    """トークン名または #RRGGBB を hex にする。解決できなければ None（黙って黒にしない）。"""
    if not isinstance(token, str) or not token:
        return None
    if token.startswith("#"):
        return token.upper() if is_hex6(token) else None
    if token in ctx.colors or token in SEMANTIC_COLORS:
        c = col(ctx, token, "")
        return c if is_hex6(c) else None
    return None


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ensure_contrast(fg: str, bg: str, ratio: float = 4.5) -> str:
    """fg を bg との対比が ratio 以上になるまで暗く（bg が暗いなら明るく）する。"""
    toward = "#000000" if luminance(bg) > 0.4 else "#FFFFFF"
    c = fg
    for k in range(1, 21):
        if contrast(c, bg) >= ratio:
            return c
        c = mix(fg, toward, k * 0.06)
    return c


def _bg(ctx) -> str:
    return ctx.c("background", "#FFFFFF")


def char_w(c, font, bold) -> float:
    """1 文字の幅（em）。テーマのフォントを実測できない環境では、半角の字幅を少し広めに見積もる（はみ出しを防ぐ）。"""
    em = ja_text.char_em(c, font, bold)
    return em * 1.12 if (ord(c) < 128 and not ja_text.measuring()) else em


def tw(ctx, text, size, bold=False, head=False) -> float:
    """1 行の文字幅（px）。複数行なら最長の行。"""
    font = ctx.head_font if head else ctx.body_font
    return max((sum(char_w(c, font, bold) for c in line) for line in str(text).split("\n")), default=0.0) * size


def wrap(ctx, text, size, width, bold=False, head=False) -> list:
    return ja_text.wrap_lines(str(text), size, max(width, 1.0), ctx.head_font if head else ctx.body_font, bold)


def _lines(ctx, text, size, width, bold=False, head=False) -> int:
    return len(wrap(ctx, text, size, width, bold, head))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _text_box(ctx, x, y, w, text, size, color, bold=False, head=False, align="l", anchor="t", h=None, nowrap=False,
              lh=1.0, name=None, fill=None, insets=(0, 0, 0, 0), line=None):
    """文字だけ（または塗りつき）の箱。高さの既定は行数 × 文字サイズ × 1.2。"""
    if h is None:
        n = (str(text).count("\n") + 1) if nowrap else _lines(ctx, text, size, w - insets[0] - insets[2], bold, head)
        h = math.ceil(n * size * LINE_H * lh) + 1 + insets[1] + insets[3]
    paras = [ctx.para(line_, size, color, bold=bold, head=head, align=align, lh=lh) for line_ in str(text).split("\n")] \
        if nowrap else [ctx.para(str(text), size, color, bold=bold, head=head, align=align, lh=lh)]
    el = ctx.box(x, y, w, h, fill=fill, line=line, paras=paras, anchor=anchor, insets=insets, name=name)
    if nowrap and "text" in el:
        el["text"]["wrap"] = False
    return el


def _rbox(ctx, x, y, w, h, fill, radius, name=None, line=None, paras=None, anchor="ctr", insets=(0, 0, 0, 0),
          dash=None, line_w=0.75):
    adj = {"adj": int(clamp(radius / max(min(w, h), 1.0), 0, 0.5) * 100000)}
    return ctx.box(x, y, w, h, fill=fill, line=line, geom="roundRect", adj=adj, paras=paras, anchor=anchor,
                   insets=insets, name=name, dash=dash, line_w=line_w)


def _tri(ctx, x, y, w, h, fill, up=True, name=None):
    el = ctx.tri_down(x, y, w, h, fill, name)
    if up:
        el["path"][0]["cmds"] = [["M", round(w / 2, 2), 0], ["L", round(w, 2), round(h, 2)], ["L", 0, round(h, 2)],
                                 ["Z"]]
    return el


def _placeholder(ctx, body, text, name="空"):
    size = clamp(body["h"] * 0.08, 12, 22)
    return [_rbox(ctx, body["x"], body["y"], body["w"], body["h"], ctx.c("surface", "#EEEEEE"), ctx.radius("node", 10), name=name,
                  paras=[ctx.para(text, size, "muted", align="ctr", lh=1.2)], anchor="ctr", insets=(12, 8, 12, 8))]


# ===========================================================================
# kpi — 大きな数字
# ===========================================================================

def _kpi_items(slide) -> list:
    out = []
    for it in slide.get("items") or []:
        if isinstance(it, dict):
            if it.get("of") is not None and it.get("from") is not None:
                it = {k: v for k, v in it.items() if k != "of"}      # from（変化）と of（進捗）の併用は from を優先する（検査が警告する）
            out.append(it)
        elif it is not None:
            out.append({"value": str(it)})
    return out


def from_unit(it: dict) -> str:
    """変化前（from）に付ける単位。from_unit があればそれ（"" で単位なし）。無ければ、from が「3か月」のように単位つきの文字列のときは付けない
    （unit を後ろに付けて「3か月 週間 →」にならないように）。数字だけの from には unit を付ける（従来どおり）。"""
    if "from_unit" in it and it["from_unit"] is not None:
        return str(it["from_unit"])
    f = it.get("from")
    if isinstance(f, str) and to_float(f) is None and re.search(r"[A-Za-zぁ-ヿ一-鿿]", f):
        return ""
    return str(it.get("unit", "") or "")


def _show(v) -> str:
    """表示用の数字。数値型は桁区切り、文字列はそのまま。"""
    if v is None:
        return ""
    if _is_num(v):
        return fmt_num(v, _decimals([v]))
    return str(v)


def _direction(it):
    """値の動き。from と value の大小 → delta の符号の順に判定する。+1 増 / -1 減 / None 不明。"""
    a, b = to_float(it.get("from")), to_float(it.get("value"))
    if a is not None and b is not None and a != b:
        return 1 if b > a else -1
    d = str(it.get("delta", "")).strip()
    if d[:1] in ("+", "＋", "▲"):
        return 1
    if d[:1] in ("-", "−", "－", "▼"):
        return -1
    return None


def _delta_color(ctx, g, it) -> str:
    good = it.get("good")
    d = _direction(it)
    if good in ("up", "down"):
        if d is None:
            return col(ctx, g.get("good_color", SEMANTIC_COLORS["positive"]))
        ok = (d > 0) == (good == "up")
        return col(ctx, g.get("good_color", SEMANTIC_COLORS["positive"]) if ok else g.get("bad_color", SEMANTIC_COLORS["negative"]))
    return ctx.c(g.get("neutral_color", "muted"))


class _Tile:
    """kpi の 1 件ぶんの寸法（幅・高さの見積もり）と描画。全件で共通のスロットを使い、並べたとき行が揃う。"""

    def __init__(self, ctx, g, items, avail_w, avail_h, hero, S, stack=False):
        self.ctx, self.g, self.items, self.hero, self.S = ctx, g, items, hero, S
        # stack: 変化前（from）を数字の上の小さい 1 行に分け、数字そのものを大きくする（2〜4 件のタイル用）
        self.stack = bool(stack) and not hero and any(it.get("from") is not None for it in items)
        self.avail_w = avail_w
        self.ls = clamp(S * (0.26 if hero else 0.30), 16, 30)           # ラベル
        self.cs = clamp(S * 0.27, 15, 30)                               # delta
        self.ns = clamp(S * (0.20 if hero else 0.24), 13, 22)           # 注記
        self.bh = clamp(S * 0.13, 8, 18)                                # 進捗バー
        self.gap = clamp(S * 0.16, 8, 26)
        self.label_n = max([_lines(ctx, it.get("label", ""), self.ls, avail_w) for it in items] + [1]) \
            if any(it.get("label") for it in items) else 0
        self.note_n = max([_lines(ctx, it.get("note", ""), self.ns, avail_w) for it in items] + [1]) \
            if any(it.get("note") for it in items) else 0
        self.has_delta = any(it.get("delta") for it in items)
        self.has_bar = any(it.get("of") is not None for it in items)
        self.label_h = math.ceil(self.label_n * self.ls * LINE_H * 1.1) + 1
        self.fs = clamp(S * 0.36, 14, 30)                               # 変化前の行
        self.from_h = math.ceil(self.fs * LINE_H) + 1 if self.stack else 0
        self.num_h = math.ceil(S * LINE_H)
        self.chip_h = math.ceil(self.cs * LINE_H + self.cs * 0.7)
        self.note_h = math.ceil(self.note_n * self.ns * LINE_H * 1.15) + 1
        blocks = [h for h in (self.label_h if self.label_n else 0, self.from_h, self.num_h,
                              self.chip_h if self.has_delta else 0, self.bh if self.has_bar else 0,
                              self.note_h if self.note_n else 0) if h]
        self.total = sum(blocks) + self.gap * (len(blocks) - 1)

    # --- 数字の行 -------------------------------------------------------
    def value_runs(self, it, emph_to):
        ctx, g, S = self.ctx, self.g, self.S
        unit = str(it.get("unit", "") or "")
        us = max(S * 0.42, 14)
        gapu = "" if unit[:1] in ("%", "％", "‰") else " "
        has_from = it.get("from") is not None
        vcol = g.get("to_color", "accent") if (has_from and emph_to) else g.get("value_color", "primary")
        runs = []
        if has_from and not self.stack:
            fs = S * 0.58
            runs.append(ctx.run(_show(it["from"]), fs, g.get("from_color", "muted"), bold=True, head=True))
            funit = from_unit(it)
            if funit:
                runs.append(ctx.run(("" if funit[:1] in ("%", "％", "‰") else " ") + funit, max(us * 0.8, 13), g.get("from_color", "muted"), bold=False))
            runs.append(ctx.run("  →  ", S * 0.42, g.get("arrow_color", "muted")))
        runs.append(ctx.run(_show(it.get("value")), S, vcol, bold=True, head=True))
        if it.get("of") is not None:
            runs.append(ctx.run(" / " + _show(it["of"]), S * 0.5, g.get("from_color", "muted"), bold=True, head=True))
        if unit:
            runs.append(ctx.run(gapu + unit, us, vcol, bold=False))
        return runs

    def from_runs(self, it):
        """変化前の行（stack のとき）。「6.5 時間 →」の形で、すぐ下の大きい数字へ視線を落とす。"""
        ctx, g, fs = self.ctx, self.g, self.fs
        unit = from_unit(it)
        gapu = "" if unit[:1] in ("%", "％", "‰") else " "
        fcol = g.get("from_color", "muted")
        runs = [ctx.run(_show(it["from"]), fs, fcol, bold=True, head=True)]
        if unit:
            runs.append(ctx.run(gapu + unit, max(fs * 0.8, 13), fcol, bold=False))
        runs.append(ctx.run("  →", fs * 0.9, g.get("arrow_color", "muted")))
        return runs

    @staticmethod
    def runs_w(ctx, runs) -> float:
        return sum(sum(char_w(c, r["font"], r["bold"]) for c in r["text"]) * r["size"] for r in runs)

    def max_w(self, emph_to) -> float:
        w = max(self.runs_w(self.ctx, self.value_runs(it, emph_to)) for it in self.items) * 1.04
        if self.stack:
            w = max([w] + [self.runs_w(self.ctx, self.from_runs(it)) * 1.04 for it in self.items
                           if it.get("from") is not None])
        return w


def _fit_tile(ctx, g, items, avail_w, avail_h, hero, emph_to, stack=False):
    if g.get("value_size"):
        cands = [float(g["value_size"])]
    else:
        hi = g.get("hero_max_size", 120) if hero else g.get("tile_max_size", 76)
        lo = g.get("min_size", 26)
        cands = list(range(int(_cap_size(hi, 0)), int(_cap_size(lo, 0)) - 1, -2)) or [lo]     # 候補の数に上限（極端な値で 50 万個の _Tile を作らない）
    last = None
    for S in cands:
        t = _Tile(ctx, g, items, avail_w, avail_h, hero, S, stack)
        last = t
        if t.max_w(emph_to) <= avail_w and t.total <= avail_h:
            return t
    return last


def _wrap_text(g, text, size, w):
    """ラベル・注記が語の途中で折れるとき、文節の切れ目に改行を入れる（S5b。行数は増やさない。高さは直す前の行数で確保済み）。
    利用者がラベル・注記の大きさ（style.body.label_size / note_size）を書いたときと、layout_kpi が設定を渡していないときは触らない。"""
    cfg = g.get("_wrap")
    if not isinstance(cfg, dict) or g.get("_wrap_user"):
        return text
    return wrap_fix.fix(str(text), size, w, cfg)


def _draw_tile(ctx, g, t, it, x, y_top, w, hero, idx, emph_to):
    """1 件ぶんの要素。x, w は内側（余白を引いた）幅、y_top は共通スロットの上端。"""
    out = []
    align = "ctr" if hero else "l"
    gap = t.gap
    y = y_top
    pre = f"数字{idx + 1}" if not hero else "数字"
    if t.label_n:
        if it.get("label"):
            out.append(_text_box(ctx, x, y, w, _wrap_text(g, it["label"], t.ls, w), t.ls, g.get("label_color", "text"), align=align,
                                 h=t.label_h, lh=1.1, name=f"ラベル{idx + 1}" if not hero else "ラベル"))
        y += t.label_h + gap
    if t.stack:
        if it.get("from") is not None:
            out.append(_text_box(ctx, x, y, w, "", t.fs, "muted", h=t.from_h, name=f"変化前{idx + 1}"))
            el_f = out[-1]
            el_f["text"]["paragraphs"] = [{"align": align, "lineHeight": 1.0, "runs": t.from_runs(it)}]
            el_f["text"]["wrap"] = False
        y += t.from_h + gap
    runs = t.value_runs(it, emph_to)
    p = {"align": align, "lineHeight": 1.0, "runs": runs}
    el = ctx.box(x, y, w, t.num_h, paras=[p], anchor="ctr", name=pre)
    el["text"]["wrap"] = False
    out.append(el)
    y += t.num_h + gap
    if t.has_delta:
        if it.get("delta"):
            dcol = _delta_color(ctx, g, it)
            d = _direction(it)
            dtxt = str(it["delta"])
            cs = t.cs
            tri = cs * 0.55 if d else 0
            padx = cs * 0.7 + 3
            cw = tw(ctx, dtxt, cs, bold=True, head=True) * 1.2 + cs * 0.5 + 2 * padx + (tri + cs * 0.3 if d else 0)
            cw = min(cw, w)
            cx = x + (w - cw) / 2 if hero else x
            bgc = _bg(ctx)
            tile_bg = bgc if hero else ctx.c(g.get("tile_fill", "surface"))
            fill = mix(dcol, tile_bg, g.get("chip_tint", 0.86))
            tcol = ensure_contrast(dcol, fill, 4.5)        # 小さい太字なので、チップ上の文字は対比 4.5:1 以上にする
            ins_l = padx + (tri + cs * 0.3 if d else 0)
            chip = _rbox(ctx, cx, y, cw, t.chip_h, fill, min(t.chip_h / 2, ctx.radius("pill", 999)), name=f"変化{idx + 1}" if not hero else "変化",
                         paras=[ctx.para(dtxt, cs, tcol, bold=True, head=True, align="l" if d else "ctr", lh=1.0)],
                         insets=(ins_l if d else 0, 0, padx if d else 0, 0))
            chip["text"]["wrap"] = False
            out.append(chip)
            if d:
                out.append(_tri(ctx, cx + padx, y + (t.chip_h - tri * 0.8) / 2, tri, tri * 0.8, dcol, up=d > 0,
                                name="増減の向き"))
        y += t.chip_h + gap
    if t.has_bar:
        if it.get("of") is not None:
            a, b = to_float(it.get("value")), to_float(it.get("of"))
            ratio = clamp(a / b, 0.0, 1.0) if (a is not None and b) else 0.0
            bw = min(w, 560) if hero else w
            bx = x + (w - bw) / 2 if hero else x
            track = ctx.c(g.get("bar_track_hero", "surface") if hero else g.get("bar_track", "background"))
            out.append(_rbox(ctx, bx, y, bw, t.bh, track, min(t.bh / 2, ctx.radius("pill", 999)), name="進捗の地" if hero else f"進捗の地{idx + 1}"))
            if ratio > 0:
                out.append(_rbox(ctx, bx, y, max(bw * ratio, t.bh), t.bh, ctx.c(g.get("bar_fill", "primary")), min(t.bh / 2, ctx.radius("pill", 999)),
                                 name="進捗" if hero else f"進捗{idx + 1}"))
        y += t.bh + gap
    if t.note_n and it.get("note"):
        out.append(_text_box(ctx, x, y, w, _wrap_text(g, it["note"], t.ns, w), t.ns, g.get("note_color", "muted"), align=align, h=t.note_h,
                             lh=1.15, name=f"注記{idx + 1}" if not hero else "注記"))
    return out


def _degrade(items, level):
    """入りきらないとき、付随情報を順に落とす（1: 注記 / 2: 変化 / 3: ラベル）。"""
    drop = {1: ("note",), 2: ("note", "delta"), 3: ("note", "delta", "label")}.get(level, ())
    return [{k: v for k, v in it.items() if k not in drop} for it in items]


def layout_kpi(slide, st, ctx, body):
    g = st.get("body", {})
    # 文節の改行を入れてよいかは build_deck.apply_wrap_fix が決める（止め方・利用者が書いた大きさ・autofit: false を同じ条件で見る）。
    # 入れてよいスライド・ブロックにだけ、その設定（_wrap_cfg）が付いている
    wcfg = slide.get("_wrap_cfg") if isinstance(slide, dict) else None
    g = dict(g, _wrap=wcfg if isinstance(wcfg, dict) else None, _wrap_user=False)
    items = _kpi_items(slide)
    if not items:
        return _placeholder(ctx, body, "items（数字の配列）がありません")
    n = len(items)
    cols = 1 if n == 1 else (n if n <= 4 else (3 if n <= 6 else 4))
    gap = g.get("gap", 24) * (clamp(body["w"] / 1136, 0.5, 1.0))
    while cols > 1 and (body["w"] - gap * (cols - 1)) / cols < 150:    # 狭い矩形では列を減らす
        cols -= 1
    rows = math.ceil(n / cols)
    hero = n == 1
    tw_ = (body["w"] - gap * (cols - 1)) / cols
    th_ = (body["h"] - gap * (rows - 1)) / rows
    px = g.get("pad_x", 28) if not hero else max(g.get("pad_x", 28), 12)
    px = min(px, max(tw_ * 0.08, 10))
    py = g.get("pad_y", 26)
    if min(tw_, th_) < 220:      # 小さい矩形では余白も詰める
        px, py = px * 0.6, py * 0.6
    n_from = sum(1 for it in items if it.get("from") is not None)
    emph_to = n_from <= 2 or n == 1
    out = []
    for r in range(rows):
        row_items = items[r * cols:(r + 1) * cols]
        t = None
        for level in range(4):
            cur = _degrade(row_items, level)
            lo_g = dict(g, min_size=g.get("min_size", 26) if level == 0 else 12)
            aw, ah = tw_ - 2 * px, th_ - 2 * py
            t = _fit_tile(ctx, lo_g, cur, aw, ah, hero, emph_to)
            ok = t.max_w(emph_to) <= aw and t.total <= ah
            if not hero and any(it.get("from") is not None for it in cur):
                # 変化前を数字の上の行に分けたほうが、数字を大きくできるなら（1.25 倍以上）そちらにする
                t2 = _fit_tile(ctx, lo_g, cur, aw, ah, hero, emph_to, stack=True)
                ok2 = t2.max_w(emph_to) <= aw and t2.total <= ah
                if (ok2 and (not ok or t2.S >= t.S * 1.25)) or (not ok and not ok2 and t2.S > t.S):
                    t, ok = t2, ok2
            if ok:
                break
        row_items = cur
        tile_h = th_ if (rows > 1 or hero) else min(th_, max(t.total + 2 * py + 40, th_ * g.get("tile_min_ratio", 0.62)))
        ty = body["y"] + r * (th_ + gap) + (th_ - tile_h) / 2 if rows == 1 else body["y"] + r * (th_ + gap)
        for c, it in enumerate(row_items):
            idx = r * cols + c
            tx = body["x"] + c * (tw_ + gap)
            if not hero:
                out.append(_rbox(ctx, tx, ty, tw_, tile_h, ctx.c(g.get("tile_fill", "surface")), g.get("radius", 14),
                                 name=f"タイル{idx + 1}", line=ctx.c(g["tile_line"]) if g.get("tile_line") else None))
            y_top = max(ty + (tile_h - t.total) / 2, ty)
            out += _draw_tile(ctx, g, t, it, tx + px, y_top, tw_ - 2 * px, hero, idx,
                              emph_to if (it.get("emphasis") is None) else bool(it.get("emphasis")))
    return out


# ===========================================================================
# chart — データグラフ
# ===========================================================================

def chart_kind(slide) -> str:
    k = str(slide.get("chart", "bar") or "bar")
    return CHART_ALIASES.get(k, k)


def _chart_data(slide) -> dict:
    """スライドの生データを、描画しやすい形にそろえる（不正な値は None / 空にして落ちないようにする）。"""
    cats = [str(c) for c in (slide.get("categories") if isinstance(slide.get("categories"), list) else [])]
    series = []
    for s in (slide.get("series") if isinstance(slide.get("series"), list) else []):
        if not isinstance(s, dict):
            continue
        vals = [float(v) if _is_num(v) else None for v in (s.get("values") if isinstance(s.get("values"), list) else [])]
        series.append({"name": str(s.get("name", "") or ""), "vals": vals, "color": s.get("color")})
    n = max([len(cats)] + [len(s["vals"]) for s in series]) if (cats or series) else 0
    if len(cats) < n:
        cats = cats + [""] * (n - len(cats))
    for s in series:
        s["vals"] = (s["vals"] + [None] * n)[:n]
    hl = slide.get("highlight")
    hl = {str(x) for x in hl} if isinstance(hl, list) else ({str(hl)} if isinstance(hl, str) else set())
    ff = slide.get("forecast_from")
    fc = cats.index(str(ff)) if ff is not None and str(ff) in cats else None
    annos = []
    for a in slide.get("annotations") or []:
        if isinstance(a, dict) and str(a.get("at", "")) in cats and a.get("text"):
            annos.append({"i": cats.index(str(a["at"])), "text": str(a["text"]), "series": a.get("series")})
    y = slide.get("y") if isinstance(slide.get("y"), dict) else {}
    totals = slide.get("totals")
    totals = {str(t) for t in totals} if isinstance(totals, list) else None
    return {"cats": cats, "series": series, "n": n, "hl": hl, "fc": fc, "annos": annos, "y": y,
            "unit": str(slide.get("unit", "") or ""), "totals": totals, "good": slide.get("good"),
            "values": slide.get("values", True), "note": str(slide.get("note", "") or "")}


def nice_axis(lo, hi, ticks, fixed_lo=None, fixed_hi=None, step=None):
    """切りのよい目盛。(下端, 上端, 刻み) を返す。"""
    a = fixed_lo if fixed_lo is not None else lo
    b = fixed_hi if fixed_hi is not None else hi
    if b - a < 1e-12:
        b = a + (abs(a) * 0.1 or 1.0)
    if not step:
        raw = (b - a) / max(ticks, 1)
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw * 0.999)
    na = fixed_lo if fixed_lo is not None else math.floor(a / step + 1e-9) * step
    nb = fixed_hi if fixed_hi is not None else math.ceil(b / step - 1e-9) * step
    if nb - na < 1e-12:
        nb = na + step
    return na, nb, step


def _ticks(lo, hi, step):
    out, k = [], math.ceil(lo / step - 1e-9)
    while k * step <= hi + 1e-9 and len(out) < 40:
        out.append(round(k * step, 10))
        k += 1
    return out


def _series_palette(ctx, g, m) -> list:
    toks = list(g.get("series_colors") or ["primary", "accent", "muted"])
    bg = _bg(ctx)
    out = [ctx.c(t) for t in toks]
    k = 0
    while len(out) < m:
        out.append(mix(out[k % len(toks)], bg, 0.5))
        k += 1
    return out[:max(m, 1)]


def _hline_segments(x0, x1, y, blockers, pad=3.0):
    """文字の矩形(blockers)を避けて水平線を切る。"""
    cuts = sorted((bx - pad, bx + bw + pad) for bx, by, bw, bh in blockers if by - pad < y < by + bh + pad)
    segs, cur = [], x0
    for a, b in cuts:
        if b <= cur:
            continue
        if a > cur:
            segs.append((cur, min(a, x1)))
        cur = max(cur, b)
        if cur >= x1:
            break
    if cur < x1:
        segs.append((cur, x1))
    return [(a, b) for a, b in segs if b - a >= 14]


class _Plan:
    """グラフ 1 枚の計算結果。elements と、計算中に見つけた問題(diags)。"""

    def __init__(self):
        self.diags = []
        self.layers = {"grid": [], "marks": [], "text": [], "ann": [], "head": []}
        self.blockers = []     # 文字の矩形（グリッド線を切る・注釈を避ける）
        self.anchors = {}      # (カテゴリ番号, 系列番号 or None) → (x, 上端 y)
        self.deficit = 0.0
        self.anno_top = None   # 注釈の箱の最上端（plot の取りしろの調整に使う）
        self.bars = []         # 棒の矩形（注釈が棒に重ならないように避ける）

    def diag(self, code, msg):
        if not any(d[0] == code and d[1] == msg for d in self.diags):
            self.diags.append((code, msg))

    def elements(self):
        return [e for k in ("grid", "marks", "text", "ann", "head") for e in self.layers[k]]


SIZE_CAP = 2000.0     # 「1px ずつ下げる」探索の出発点の上限。極端に大きい値（1e6〜1e308）でも探索が必ず終わるようにする（通常の 1〜200px には影響しない）


def _cap_size(size, smin=0.0):
    """探索の出発点にする文字サイズ。上限（SIZE_CAP。ただし下限 smin より小さくはしない）に丸め、NaN は下限にする"""
    try:
        size = float(size)
    except (TypeError, ValueError):
        return float(smin)
    if size != size:
        return float(smin)
    return min(size, max(SIZE_CAP, float(smin)))


def _smin(smin):
    """探索の下限にする文字サイズ。1〜SIZE_CAP に収め、NaN は 1 にする（下限が極端な値でも「1px ずつ下げる」が必ず終わる）"""
    try:
        smin = float(smin)
    except (TypeError, ValueError):
        return 1.0
    return 1.0 if smin != smin else max(1.0, min(smin, SIZE_CAP))


def _fit_labels(ctx, texts_with_unit, texts_plain, pitch, size, smin, bold=True):
    """値ラベルが隣と重ならないよう、単位つき→単位なし、文字サイズを下げる、の順で収める。(texts, size, ok)"""
    smin = _smin(smin)
    size = _cap_size(size, smin)
    for texts in (texts_with_unit, texts_plain):
        s = size
        while s >= smin - 1e-6:
            if all(tw(ctx, t, s, bold=bold, head=True) + 6 <= pitch for t in texts):
                return texts, s, True
            s -= 1
    return texts_plain, smin, False


def _cat_labels(ctx, cats, slot, size, smin):
    """カテゴリ名を 2 行までで収める。(サイズ, 最大行数, 間引き間隔, ok)"""
    smin = _smin(smin)
    s = _cap_size(size, smin)
    while s >= smin - 1e-6:
        ls = [wrap(ctx, c, s, slot - 6) for c in cats]
        if all(len(x) <= 2 for x in ls) and all(tw(ctx, ln, s) <= slot - 2 for x in ls for ln in x):
            return s, max(len(x) for x in ls), 1, True
        s -= 1
    for step in range(2, len(cats) + 1):
        ls = [wrap(ctx, c, smin, slot * step - 6) for c in cats[::step]]
        if all(len(x) <= 2 for x in ls):
            return smin, max(len(x) for x in ls), step, False
    return smin, 2, max(len(cats), 1), False


def _clip_lines(ctx, text, size, width, max_lines, bold=False):
    """max_lines 行に収まらない文字は「…」で切る（箱から文字がはみ出さないように）。"""
    ls = wrap(ctx, text, size, width, bold)
    if len(ls) <= max_lines:
        return text
    head, last = "".join(ls[:max_lines - 1]), "".join(ls[max_lines - 1:])
    while len(last) > 1 and tw(ctx, last + "…", size, bold) > width - 2:
        last = last[:-1]
    return head + last + "…"


def _legend_layout(ctx, names, colors, size, width):
    """凡例を並べる。[(x, row, name, color)], 行数, 1 行にしたときの幅。"""
    sw, gap_in, gap = size * 0.9, size * 0.4, size * 1.4
    items = [(tw(ctx, n, size) + sw + gap_in + 4) for n in names]
    one_row = sum(items) + gap * (len(items) - 1)
    pos, x, row = [], 0.0, 0
    for n, c, wi in zip(names, colors, items):
        if x > 0 and x + wi > width:
            x, row = 0.0, row + 1
        pos.append((x, row, n, c))
        x += wi + gap
    return pos, row + 1, one_row


def _hl_modes(hl, cats, ser_names):
    """highlight が項目名に一致する(cat_mode)か、系列名に一致する(ser_mode)か。どちらにも一致しなければ強調なし。"""
    cat_mode = any(h in cats for h in hl)
    return cat_mode, (not cat_mode) and any(h in ser_names for h in hl)


def _point_color_fn(series, palette, cats, hl, cat_mode, ser_mode, base_c, hi_c, fade):
    """棒・横棒で共通の色決め。highlight が項目にも系列にも一致しないときは強調なし（全部を薄くしない）。"""
    m = len(series)

    def point_color(si, ci):
        base = palette[si] if (m > 1 or series[si].get("color")) else base_c
        if not hl or not (cat_mode or ser_mode):
            return base
        hit = (cats[ci] in hl) if cat_mode else (series[si]["name"] in hl)
        if hit:
            return hi_c if m == 1 else base
        return fade(base) if m > 1 else fade(base_c)
    return point_color


def _hit(a, b, pad=0):
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0] or a[1] + a[3] + pad <= b[1] or
                b[1] + b[3] + pad <= a[1])


def run_first(vals):
    return next((i for i, v in enumerate(vals) if v is not None), -1)


def run_last(vals):
    return next((i for i in range(len(vals) - 1, -1, -1) if vals[i] is not None), -1)


def _plan_chart(slide, st, ctx, body) -> _Plan:
    g = st.get("body", {})
    P = _Plan()
    D = _chart_data(slide)
    kind = chart_kind(slide)
    if kind not in CHART_KINDS:
        kind = "bar"
    cats, series, n = D["cats"], D["series"], D["n"]
    if not n or not series:
        P.layers["marks"] += _placeholder(ctx, body, "表示するデータがありません（categories と series を確認）")
        return P
    W, H = body["w"], body["h"]
    scale = clamp(0.55 + 0.45 * min(W / 1136, H / 452), 0.6, 1.1)
    smin = g.get("min_size", 11)

    def sz(key, default):
        return max(round(g.get(key, default) * scale, 1), smin)

    tick_s, cat_s, val_s = sz("tick_size", 15), sz("cat_size", 17), sz("value_size", 18)
    leg_s, note_s, anno_s = sz("legend_size", 15), sz("note_size", 20), sz("anno_size", 15)
    text_c, muted_c = ctx.c(g.get("text_color", "text")), ctx.c(g.get("muted_color", "muted"))
    grid_c, axis_c = ctx.c(g.get("grid_color", "border")), ctx.c(g.get("axis_color", "muted"))
    bg = _bg(ctx)
    m = len(series)
    if kind in ("waterfall", "donut"):
        m = 1
        series = series[:1]
    palette = _series_palette(ctx, g, m)
    for i, s in enumerate(series):
        c_ = resolve_color(ctx, s.get("color")) if s.get("color") else None
        if c_:
            palette[i] = c_
        else:
            s["color"] = None       # 解決できない色は無視して既定の色にする（validate が fail で知らせる）
    base_c, hi_c = ctx.c(g.get("base_color", "primary")), ctx.c(g.get("highlight_color", "accent"))
    fade = lambda c: mix(c, bg, g.get("fade_tint", 0.55))       # noqa: E731
    tint = lambda c: mix(c, bg, g.get("forecast_tint", 0.5))   # noqa: E731
    wf_totals = None
    if kind == "waterfall":
        wf_totals = D["totals"] if D["totals"] is not None else ({cats[0], cats[-1]} if n >= 2 else set())
    dec = _decimals([v for s in series for v in s["vals"]])
    unit = D["unit"]
    uf = lambda v, d=dec: fmt_val(v, d)                          # noqa: E731
    ufu = lambda v, d=dec: fmt_val(v, d) + unit                  # noqa: E731
    sv = D["values"]
    show_vals = sv is not False
    # 折れ線は、系列が複数・点が多い・"ends" のとき最初と最後の点だけにラベルを付ける
    ends_only = kind == "line" and show_vals and (sv == "ends" or m > 1 or n > 12)

    # --- 右の読み取り欄 / 下の一言 -----------------------------------------
    rx, ry, rw, rh = body["x"], body["y"], W, H
    note = D["note"]
    if note:
        if W >= 640:
            np_w = clamp(W * 0.27, 200, 330)
            import pattern_engine as pat_e      # 文節の切れ目での折り返し（語の途中「シス/テム」で切らない）。循環 import を避けるため遅延 import
            nlines_l = pat_e._phrase_lines(note, note_s, np_w - 40, ctx.body_font, True)
            nlines = max(len(nlines_l), _lines(ctx, note, note_s, np_w - 40))
            nh = min(rh, nlines * note_s * LINE_H * 1.25 + 36)
            ny = ry + (rh - nh) / 2
            P.layers["head"].append(ctx.box(rx + W - np_w, ny, np_w, nh, fill=ctx.c(g.get("note_fill", "surface")),
                                            paras=[ctx.para(ln, note_s, text_c, bold=True, lh=1.25) for ln in nlines_l], anchor="ctr",
                                            insets=(22, 12, 14, 12), name="読み取り"))
            P.layers["head"].append(ctx.box(rx + W - np_w, ny, 6, nh, fill=ctx.c(g.get("note_bar", "accent")),
                                            name="読み取りの帯"))
            rw = W - np_w - 28
        else:
            cap_s = max(note_s * 0.8, smin)
            ch = _lines(ctx, note, cap_s, W) * cap_s * LINE_H * 1.1 + 4
            P.layers["head"].append(_text_box(ctx, rx, ry + rh - ch, W, note, cap_s, text_c, bold=True, h=ch, lh=1.1,
                                              name="読み取り"))
            rh -= ch + 8

    if kind == "donut":
        _plan_donut(ctx, g, P, D, series[0], (rx, ry, rw, rh), scale, text_c, muted_c, bg, ufu, leg_s, smin)
        return P

    # --- 上の見出し行（単位の説明・凡例） -----------------------------------
    ylab = D["y"].get("label") if isinstance(D["y"].get("label"), str) else None
    if not ylab and unit and kind != "waterfall" and (kind == "line" or not show_vals):
        ylab = f"単位：{unit}"
    legend = m > 1 and kind != "waterfall"
    head_h, same_row = 0.0, False
    leg_pos = []
    ylab_w = tw(ctx, ylab, tick_s) + 4 if ylab else 0
    if legend:
        names = [s["name"] or f"系列{i + 1}" for i, s in enumerate(series)]
        leg_pos, nrows, one_row = _legend_layout(ctx, names, palette, leg_s, rw)
        row_h = leg_s * LINE_H + 6
        if ylab and ylab_w + 24 + one_row <= rw:
            head_h, same_row = row_h, True
        else:
            head_h = row_h * nrows + (tick_s * LINE_H + 2 if ylab else 0)
    elif ylab:
        head_h = tick_s * LINE_H + 4
    horiz = kind == "hbar"
    top0 = ry + head_h + ((8 if head_h else 4) + (tick_s * 0.5 if head_h else 0)) + (0 if horiz else tick_s * 0.6)

    # カテゴリ名の寸法
    if horiz:
        lab_cap = rw * 0.30
        smin_h = _smin(smin)
        cat_s_h = _cap_size(cat_s, smin_h)
        while cat_s_h > smin_h and max(tw(ctx, c, cat_s_h) for c in cats) > lab_cap and \
                max(len(wrap(ctx, c, cat_s_h, lab_cap)) for c in cats) > 2:
            cat_s_h -= 1
        cat_w = min(max(tw(ctx, c, cat_s_h) for c in cats) + 6, lab_cap)
    # 軸の範囲
    vals_all = [v for s in series for v in s["vals"] if v is not None]
    wf = None
    if kind == "stacked":
        pos = [sum(max(s["vals"][i] or 0, 0) for s in series) for i in range(n)]
        neg = [sum(min(s["vals"][i] or 0, 0) for s in series) for i in range(n)]
        dlo, dhi = min(min(neg), 0), max(max(pos), 0)
    elif kind == "waterfall":
        lv, run = [], 0.0
        wf = []          # (開始, 終了, 合計か)
        for i, c in enumerate(cats):
            v = series[0]["vals"][i]
            if c in wf_totals:
                end = run if v is None else v
                wf.append((0.0, end, True))
                run = end
            else:
                v = v or 0.0
                wf.append((run, run + v, False))
                run += v
            lv += [wf[-1][0], wf[-1][1]]
        dlo, dhi = min(min(lv), 0), max(max(lv), 0)
    elif kind == "line":
        dlo, dhi = (min(vals_all), max(vals_all)) if vals_all else (0, 1)
        if dlo > 0 and ((dhi - dlo) > 0.5 * dhi or dlo / max(dhi, 1e-9) < 0.5):
            dlo = 0
        dhi = max(dhi, dlo)
        if dhi - dlo < 1e-12:
            # 有効な点が 1 つだけ（または全部同じ値）だと範囲が 0 になり、点が基線に貼り付いて値と位置が食い違う。0 起点に広げる（棒と同じ扱い）
            dlo, dhi = min(dlo, 0), max(dhi, 0)
            if dhi - dlo < 1e-12:
                dhi = dlo + 1
    else:
        dlo = min(min(vals_all), 0) if vals_all else 0
        dhi = max(max(vals_all), 0) if vals_all else 1
    yfix_lo = D["y"].get("min") if _is_num(D["y"].get("min")) else None
    yfix_hi = D["y"].get("max") if _is_num(D["y"].get("max")) else None
    ystep = D["y"].get("step") if _is_num(D["y"].get("step")) and D["y"].get("step") > 0 else None
    if kind == "line":
        for si, sr in enumerate(series):
            cnt = sum(1 for v in sr["vals"] if v is not None)
            if cnt < 2 and n >= 2:
                nm = f"「{sr['name']}」" if sr.get("name") else f"{si + 1}"
                P.diag("line-single-point", f"折れ線の系列{nm}は有効な点が{cnt}つだけで線になりません"
                                            " → 折れ線は 2 点以上必要です。1 点なら bar か kpi にする（null は欠測で、線が途切れます）")
    uy = lambda v: fmt_val(v, _decimals([v], 4))     # noqa: E731  （利用者が書いた y.min / y.max は、データの桁数で丸めず書いた桁のまま示す）
    if yfix_hi is not None and yfix_hi < dhi - 1e-9:
        P.diag("y-max-low", f"y.max（{uy(yfix_hi)}）がデータの最大値（{uf(dhi)}）より小さいため棒・線が上で切れます"
                            " → y.max を大きくするか省く")
    bar_zero = yfix_lo is not None and kind in ("bar", "hbar", "stacked", "waterfall") and yfix_lo > 0
    if bar_zero:
        P.diag("y-min-nonzero", f"y.min が 0 でない（{uy(yfix_lo)}）ため、棒の長さが値の比を表しません"
                                " → 棒グラフは 0 から始めるか line を使う")
    if yfix_lo is not None and not bar_zero and vals_all and yfix_lo > min(vals_all) + 1e-9:
        P.diag("y-min-high", f"y.min（{uy(yfix_lo)}）がデータの最小値（{uf(min(vals_all))}）より大きいため、"
                             "軸より下の値が下端に押し付けて描かれ、値と位置が合いません → y.min を下げるか省く")
    grid_on = D["y"].get("grid")
    if grid_on is None:
        grid_on = (not show_vals) or (kind == "line" and ends_only)
    if horiz and show_vals and n:
        # 横棒は、棒 1 本あたりの高さに値ラベルが入るかを先に確かめる。入らなければラベルを省いて目盛を出す
        axis_h0 = tick_s * LINE_H + 8 if grid_on else 0
        row_h0 = max((ry + rh) - axis_h0 - top0, 10) / n
        if _hbar_fit(g, row_h0, m, val_s, smin) is None:
            show_vals = False
            if D["y"].get("grid") is None:
                grid_on = True
            P.diag("value-labels-crowded", f"値ラベルが棒の間隔に入らないため省きました（項目 {n} × 系列 {m}）"
                                           " → 項目か系列を減らす・縦棒（bar）にする・積み上げ（stacked）にする")

    # --- plot の矩形 -------------------------------------------------------
    vl_w = 0.0
    if horiz:
        plot_l = rx + cat_w + 12
        if show_vals and vals_all:
            vl_w = max(tw(ctx, ufu(v), val_s, bold=True, head=True) for v in vals_all) + 10
        axis_h = 0 if (show_vals and not grid_on) else tick_s * LINE_H + 8
        plot_r = rx + rw - vl_w
        plot_t, plot_b = top0, ry + rh - axis_h
        if dlo < 0 and show_vals:
            plot_l += vl_w
        cs_ = cl_ = cstep = None
    else:
        cs_, cl_, cstep, _ok = _cat_labels(ctx, cats, (rw - 40) / n, cat_s, smin)
        cat_block = math.ceil(cl_ * cs_ * LINE_H) + 12
        plot_b = ry + rh - cat_block
        plot_t = top0
        plot_l = rx + 6
        plot_r = rx + rw - 6
    if (plot_b - plot_t) < 36 or (plot_r - plot_l) < 40:
        # 凡例・カテゴリ名・目盛で矩形が埋まり、グラフ本体を描く場所が無い
        P.layers["marks"] += _placeholder(ctx, {"x": rx, "y": ry, "w": rw, "h": rh}, "グラフを描く領域が小さすぎます")
        P.diag("area-too-small", f"グラフを描く領域が小さすぎます（{rw:.0f}×{rh:.0f}px）"
                                 " → ブロックを大きくする・系列や項目を減らす・凡例の名前を短くする")
        P.layers["head"] = []
        return P
    # 縦方向の取りしろ(注釈) を反復で解く
    top_extra = 0.0
    P2 = None
    best = None
    for _ in range(5):
        P2 = _Plan()
        P2.diags = list(P.diags)
        P2.layers["head"] = list(P.layers["head"])
        if horiz:
            _draw_hbar(ctx, g, P2, D, series, palette, (plot_l, plot_t + top_extra, plot_r, plot_b), (rx, ry, rw, rh),
                       dict(cat_w=cat_w, cat_s=cat_s_h, vl_w=vl_w, val_s=val_s, tick_s=tick_s), (dlo, dhi),
                       (yfix_lo, yfix_hi, ystep), grid_on, show_vals, text_c, muted_c, grid_c, axis_c, base_c, hi_c,
                       fade, tint, uf, ufu, anno_s, smin)
        else:
            _draw_vertical(ctx, g, P2, D, kind, series, palette, (plot_l, plot_t + top_extra, plot_r, plot_b),
                           (rx, ry, rw, rh, top0), dict(cat_s=cs_, cat_lines=cl_, cat_step=cstep, tick_s=tick_s,
                                                         val_s=val_s), (dlo, dhi), (yfix_lo, yfix_hi, ystep),
                           grid_on, show_vals, ends_only, wf, wf_totals, text_c, muted_c, grid_c, axis_c, base_c, hi_c,
                           fade, tint, uf, ufu, anno_s, smin)
        if P2.deficit <= 0.5:
            if best is None or top_extra < best[0]:
                best = (top_extra, P2)
            # 注釈の上に余白が余っているなら、plot を上へ戻して縦を使い切る
            slack = (P2.anno_top - top0) if P2.anno_top is not None else 0.0
            if top_extra <= 0 or slack <= 6:
                break
            top_extra = max(0.0, top_extra - (slack - 3))
        else:
            top_extra += P2.deficit + 2
            if top_extra > rh * 0.5:
                break
    P = best[1] if best else P2
    # --- 見出し行 --------------------------------------------------------
    if ylab:
        P.layers["head"].append(_text_box(ctx, rx, ry, ylab_w + 4, ylab, tick_s, muted_c, nowrap=True,
                                          name="単位・軸の説明"))
    if legend:
        row_h = leg_s * LINE_H + 6
        x_off = rx + rw - one_row if same_row else rx
        y_off = ry + ((tick_s * LINE_H + 2) if (ylab and not same_row) else 0)
        swd = leg_s * 0.9
        for (lx, lrow, nm, c) in leg_pos:
            yy = y_off + lrow * row_h
            sx = x_off + lx
            if kind == "line":
                el = ctx.path([(sx, yy + row_h / 2 - 1), (sx + swd, yy + row_h / 2 - 1)], c, g.get("line_w", 3.5))
                el["name"] = f"凡例の色:{nm}"
                P.layers["head"].append(el)
            else:
                P.layers["head"].append(ctx.box(sx, yy + (row_h - swd) / 2 - 1, swd, swd, fill=c, name=f"凡例の色:{nm}"))
            P.layers["head"].append(_text_box(ctx, sx + swd + leg_s * 0.4, yy, tw(ctx, nm, leg_s) + 4, nm, leg_s,
                                              text_c, nowrap=True, name=f"凡例:{nm}"))
    return P


# ---------------------------------------------------------------------------
# 縦の棒・積み上げ・ウォーターフォール・折れ線
# ---------------------------------------------------------------------------

def _draw_vertical(ctx, g, P, D, kind, series, palette, plot, region, S, drange, yfix, grid_on, show_vals, ends_only,
                   wf, wf_totals, text_c, muted_c, grid_c, axis_c, base_c, hi_c, fade, tint, uf, ufu, anno_s, smin):
    plot_l, plot_t, plot_r, plot_b = plot
    rx, ry, rw, rh, top0 = region
    cats, n, hl, fc = D["cats"], D["n"], D["hl"], D["fc"]
    m = len(series)
    tick_s, val_s, cat_s = S["tick_s"], S["val_s"], S["cat_s"]
    bg = _bg(ctx)
    ticks_on = grid_on or not show_vals
    dlo, dhi = drange
    plot_h0 = max(plot_b - plot_t, 20)
    nt = int(clamp(plot_h0 / 70, 3, 6))                 # 目盛は高さ 70px ごとに 1 本（3〜6 本）
    lo, hi, step = nice_axis(dlo, dhi, nt, yfix[0], yfix[1], yfix[2])
    lab_room = val_s * LINE_H + 8                        # 値ラベルの取りしろ（自動の端だけ広げる）
    if show_vals:
        for _ in range(3):
            unit_px = plot_h0 / (hi - lo)
            if yfix[1] is None and (hi - dhi) * unit_px < lab_room:
                hi += step
            if yfix[0] is None and dlo < 0 and (dlo - lo) * unit_px < lab_room:
                lo -= step
    ticks = _ticks(lo, hi, step)
    tick_dec = max(_decimals([step, lo], cap=TICK_DEC_CAP), 0)
    tick_txt = {t: fmt_num(t, tick_dec) for t in ticks}
    if ticks_on:
        plot_l = rx + max(tw(ctx, t, tick_s) for t in tick_txt.values()) + 10
    sw = (plot_r - plot_l) / n
    plot_h = plot_b - plot_t

    def Y(v):
        return plot_b - (clamp(v, lo, hi) - lo) / (hi - lo) * plot_h

    base_v = 0.0 if lo <= 0 <= hi else lo
    y0 = Y(base_v)
    gap_r = g.get("bar_gap", 0.42)
    inner = g.get("bar_inner_gap", 4)
    cx = lambda i: plot_l + sw * (i + 0.5)       # noqa: E731
    marks, texts, anchors, blockers = P.layers["marks"], P.layers["text"], P.anchors, P.blockers
    ser_names = [s["name"] for s in series]
    cat_mode, ser_mode = _hl_modes(hl, cats, ser_names)
    point_color = _point_color_fn(series, palette, cats, hl, cat_mode, ser_mode, base_c, hi_c, fade)

    def is_fc(ci):
        return fc is not None and ci >= fc

    def bar_el(x, y, w, h, c, ci, name):
        P.bars.append((x, y, w, max(h, 0)))
        el = ctx.box(x, y, w, max(h, 0), fill=(tint(c) if is_fc(ci) else c), name=name)
        if is_fc(ci):
            el["line"] = {"color": c, "width": 1.25, "dash": "dash"}
        return el

    labels = []        # dict(x, y, upper, v, ci, si, pitch, prefix)
    if kind == "bar":
        group_w = min(sw * (1 - gap_r), m * g.get("bar_max_w", 96) + (m - 1) * inner)
        bw = (group_w - (m - 1) * inner) / m
        if m > 1 and bw < MIN_BAR_W:        # 細すぎるときは、系列間の隙間 → 項目間の隙間の順に詰める
            inner = max(0.0, min(inner, (group_w - m * MIN_BAR_W) / (m - 1)))
            bw = (group_w - (m - 1) * inner) / m
            if bw < MIN_BAR_W:
                group_w = min(sw * 0.86, m * g.get("bar_max_w", 96))
                bw = (group_w - (m - 1) * inner) / m
        if bw < MIN_BAR_W:
            bw = max(bw, 0.5)
            P.diag("bars-too-thin", f"棒が細すぎます（{bw:.1f}px。項目 {n} × 系列 {m}）"
                                    " → 項目か系列を減らす・横棒（hbar）にする・積み上げ（stacked）にする")
        for ci in range(n):
            for si in range(m):
                v = series[si]["vals"][ci]
                if v is None:
                    continue
                x = cx(ci) - group_w / 2 + si * (bw + inner)
                top, bot = (Y(v), y0) if v >= base_v else (y0, Y(v))
                h = bot - top
                if abs(v - base_v) > 1e-12 and h < 1.5:
                    h = 1.5
                    top = y0 - 1.5 if v >= base_v else y0
                nm = f"棒:{cats[ci]}" + (f"/{series[si]['name']}" if m > 1 else "")
                marks.append(bar_el(x, top, bw, h, point_color(si, ci), ci, nm))
                edge = top if v >= base_v else top + h
                labels.append(dict(x=x + bw / 2, y=edge, upper=v >= base_v, v=v, ci=ci, si=si,
                                   pitch=(bw + inner) if m > 1 else sw, prefix=""))
                anchors[(ci, si)] = (x + bw / 2, edge)
                anchors.setdefault((ci, None), (x + bw / 2, edge))
    elif kind == "stacked":
        bw = min(sw * (1 - gap_r), g.get("bar_max_w", 96) * 1.3)
        for ci in range(n):
            pos_c, neg_c = 0.0, 0.0
            neg_unlabeled = False
            for si in range(m):
                v = series[si]["vals"][ci]
                if not v:
                    continue
                a, b = (pos_c, pos_c + v) if v > 0 else (neg_c + v, neg_c)
                if v > 0:
                    pos_c += v
                else:
                    neg_c += v
                ya, yb = Y(b), Y(a)
                c = point_color(si, ci)
                el = bar_el(cx(ci) - bw / 2, ya, bw, yb - ya, c, ci, f"棒:{cats[ci]}/{series[si]['name'] or si + 1}")
                el["line"] = el.get("line") or {"color": bg, "width": 1.0}
                marks.append(el)
                ls_ = val_s * 0.85
                if show_vals and yb - ya >= ls_ * LINE_H + 2 and bw >= tw(ctx, uf(v), ls_, True, True) + 8:
                    lc = ctx.c("on_primary") if luminance(tint(c) if is_fc(ci) else c) < 0.42 else ctx.c("text")
                    texts.append(_text_box(ctx, cx(ci) - bw / 2, (ya + yb) / 2 - ls_ * LINE_H / 2, bw, uf(v), ls_, lc,
                                           bold=True, head=True, align="ctr", nowrap=True,
                                           name=f"値:{cats[ci]}/{series[si]['name'] or si + 1}"))
                elif show_vals and v < 0:
                    neg_unlabeled = True        # 棒の中に入らない負の部分は、棒の下に値を出す
            top_y = Y(pos_c) if pos_c > 0 else y0
            if show_vals:
                # 負の部分があるときの上の数字は差し引き後の合計。そうと分かる接頭辞を付ける
                labels.append(dict(x=cx(ci), y=top_y, upper=True, v=pos_c + neg_c, ci=ci, si=None, pitch=sw,
                                   prefix="差引 " if neg_c < 0 else ""))
                if neg_unlabeled:
                    labels.append(dict(x=cx(ci), y=Y(neg_c), upper=False, v=neg_c, ci=ci, si=None, pitch=sw, prefix="", tag="（マイナス）"))
            for key in [(ci, None)] + [(ci, si) for si in range(m)]:
                anchors[key] = (cx(ci), top_y)
    elif kind == "waterfall":
        bw = min(sw * (1 - gap_r), g.get("bar_max_w", 96) * 1.3)
        good = D["good"] if D["good"] in ("up", "down") else None
        prev_end = None
        for ci in range(n):
            s0, s1, is_tot = wf[ci]
            top, bot = Y(max(s0, s1)), Y(min(s0, s1))
            if bot - top < 1.5:
                top, bot = top - 0.75, bot + 0.75
            if is_tot:
                c = base_c
            elif good:
                up = s1 >= s0
                c = col(ctx, g.get("good_color", SEMANTIC_COLORS["positive"]) if (up == (good == "up")) else
                        g.get("bad_color", SEMANTIC_COLORS["negative"]))
            else:
                c = hi_c if s1 >= s0 else fade(base_c)
            if hl and cats[ci] in hl and is_tot:
                c = hi_c
            marks.append(bar_el(cx(ci) - bw / 2, top, bw, bot - top, c, ci, f"棒:{cats[ci]}"))
            if prev_end is not None:
                el = ctx.path([(cx(ci - 1) + bw / 2, Y(prev_end)), (cx(ci) - bw / 2, Y(prev_end))], axis_c, 0.75,
                              dash="sysDash")
                el["name"] = "つなぎ線"
                marks.append(el)
            prev_end = s1
            delta = s1 - s0
            labels.append(dict(x=cx(ci), y=top, upper=True, v=(s1 if is_tot else abs(delta)), ci=ci, si=0, pitch=sw,
                               prefix="" if is_tot else ("+" if delta >= 0 else "−")))
            anchors[(ci, 0)] = anchors[(ci, None)] = (cx(ci), top)
    else:   # line
        lw = g.get("line_w", 3.5)
        mk = g.get("marker", 10)
        for si in range(m):
            vals = series[si]["vals"]
            c = palette[si]
            emph = True
            if ser_mode:
                emph = series[si]["name"] in hl
                if not emph:
                    c = fade(c)
            w_ = lw if emph else g.get("line_w_dim", 2.25)
            runs, cur = [], []
            for ci, v in enumerate(vals):
                if v is None:
                    if cur:
                        runs.append(cur)
                    cur = []
                else:
                    cur.append(ci)
            if cur:
                runs.append(cur)
            nm = series[si]["name"] or si + 1
            for run in runs:
                act = [ci for ci in run if not is_fc(ci)]
                fcs = [ci for ci in run if is_fc(ci)]
                if len(act) >= 2:           # 実績は実線、見込みは破線（実績の最後の点から続ける）
                    el_ = ctx.path([(cx(ci), Y(vals[ci])) for ci in act], c, w_)
                    el_["name"] = f"線:{nm}"
                    marks.append(el_)
                seg = ([act[-1]] if act else []) + fcs
                if fcs and len(seg) >= 2:
                    el_ = ctx.path([(cx(ci), Y(vals[ci])) for ci in seg], c, w_, dash="dash")
                    el_["name"] = f"見込みの線:{nm}"
                    marks.append(el_)
            mk_s = mk if emph else mk * 0.8
            for ci, v in enumerate(vals):
                if v is None:
                    continue
                el = ctx.box(cx(ci) - mk_s / 2, Y(v) - mk_s / 2, mk_s, mk_s, fill=(bg if is_fc(ci) else c), geom="ellipse",
                             line=(c if is_fc(ci) else bg), line_w=2.0 if is_fc(ci) else 1.5, name=f"点:{cats[ci]}/{nm}")
                marks.append(el)
                anchors[(ci, si)] = (cx(ci), Y(v) - mk_s / 2)
                anchors.setdefault((ci, None), (cx(ci), Y(v) - mk_s / 2))
                if show_vals and (not ends_only or ci in (run_first(vals), run_last(vals))):
                    labels.append(dict(x=cx(ci), y=Y(v), upper=True, v=v, ci=ci, si=si, pitch=sw * (3 if ends_only else 1),
                                       prefix=""))

    # --- 値ラベルの配置 ---------------------------------------------------
    if labels:
        plain = [l["prefix"] + uf(l["v"]) for l in labels]
        with_u = [p + D["unit"] for p in plain]
        pitch_min = min(l["pitch"] for l in labels)
        txts, vs, ok = _fit_labels(ctx, with_u, plain, pitch_min, val_s, smin)
        if not ok:
            P.diag("value-labels-crowded", f"値ラベルが隣と重なります（棒の幅 {pitch_min:.0f}px に対して文字が広い）"
                                           " → 項目数を減らす・横棒（hbar）にする・values を false にする")
        plans = []
        for i in sorted(range(len(labels)), key=lambda i: labels[i]["x"]):
            l = labels[i]
            ci, si, v = l["ci"], l["si"], l["v"]
            t = txts[i]
            emph = (cats[ci] in hl) or (kind == "line" and si is not None and series[si]["name"] in hl)
            lw_ = tw(ctx, t, vs, bold=True, head=True) + 6
            lh_ = math.ceil(vs * LINE_H) + 1
            above = l["upper"]
            if kind == "line":
                col_vals = [(series[k]["vals"][ci], k) for k in range(m) if series[k]["vals"][ci] is not None]
                if m > 1:
                    above = (si == max(col_vals)[1])      # 同じ位置で一番上の点だけ上に出し、他は下
                else:
                    nb = [series[0]["vals"][j] for j in (ci - 1, ci + 1) if 0 <= j < n and series[0]["vals"][j] is not None]
                    above = not nb or v >= sum(nb) / len(nb)
            off = val_s * 0.55 if kind == "line" else 4
            yy = l["y"] - off - lh_ if above else l["y"] + off
            yy = clamp(yy, ry, max(ry + rh - lh_, ry))
            xx = clamp(l["x"] - lw_ / 2, rx, rx + rw - lw_)
            clr = ctx.c("heading_text") if emph else text_c
            name = f"値:{cats[ci]}" + (f"/{series[si]['name']}" if (si is not None and m > 1) else "") + l.get("tag", "")
            plans.append(dict(xx=xx, yy=yy, lw=lw_, lh=lh_, t=t, clr=clr, name=name, above=above, ci=ci, si=si))
        if kind == "line" and m > 1:
            # 同じ列に集まる端点ラベルは、点の高さの順に最小間隔(ラベルの高さ+1)を確保して縦にずらす
            by_col = {}
            for pl in plans:
                by_col.setdefault(pl["ci"], []).append(pl)
            lo_y, hi_y = ry, ry + rh
            for grp in by_col.values():
                grp.sort(key=lambda pl: pl["yy"])
                for a_, b_ in zip(grp, grp[1:]):
                    b_["yy"] = max(b_["yy"], a_["yy"] + a_["lh"] + 1)
                over = grp[-1]["yy"] + grp[-1]["lh"] - hi_y
                if over > 0:             # 下にはみ出すぶんは全体を上へ戻し、上から詰め直す
                    for pl in grp:
                        pl["yy"] -= over
                    for a_, b_ in zip(grp, grp[1:]):
                        b_["yy"] = max(b_["yy"], a_["yy"] + a_["lh"] + 1)
                if grp[0]["yy"] < lo_y:
                    grp[0]["yy"] = lo_y
                    for a_, b_ in zip(grp, grp[1:]):
                        b_["yy"] = max(b_["yy"], a_["yy"] + a_["lh"] + 1)
                if grp[-1]["yy"] + grp[-1]["lh"] > hi_y + 0.5:
                    P.diag("value-labels-crowded", f"{cats[grp[0]['ci']]} の値ラベルが縦に収まりません"
                                                   " → 系列を絞る・values を false にする・項目を減らす")
        for pl in plans:
            texts.append(_text_box(ctx, pl["xx"], pl["yy"], pl["lw"], pl["t"], vs, pl["clr"], bold=True, head=True,
                                   align="ctr", nowrap=True, h=pl["lh"], name=pl["name"]))
            blockers.append((pl["xx"], pl["yy"], pl["lw"], pl["lh"]))
            if pl["above"]:       # 注釈の起点は値ラベルの上
                for key in ((pl["ci"], pl["si"]), (pl["ci"], None)):
                    if key in anchors:
                        ax, ay = anchors[key]
                        anchors[key] = (ax, min(ay, pl["yy"] - 1))
    # --- 縦軸・グリッド・基準線 --------------------------------------------
    grid = P.layers["grid"]
    if ticks_on:
        for t in ticks:
            yy = Y(t)
            if grid_on and abs(t - base_v) > 1e-9:
                for a, b in _hline_segments(plot_l, plot_r, yy, blockers):
                    grid.append(ctx.path([(a, yy), (b, yy)], grid_c, 0.75))
            texts.append(_text_box(ctx, rx, clamp(yy - tick_s * LINE_H / 2, ry, ry + rh - math.ceil(tick_s * LINE_H) - 1),
                                   plot_l - rx - 8, tick_txt[t], tick_s, muted_c,
                                   align="r", nowrap=True, name=f"目盛:{tick_txt[t]}"))
    grid.append(ctx.path([(plot_l, y0), (plot_r, y0)], axis_c, 1.0))
    # --- カテゴリ名 -------------------------------------------------------
    step = S["cat_step"]
    cl = S["cat_lines"]
    for ci in range(0, n, step):
        w_ = min(sw * step, rw)
        c = ctx.c("heading_text") if cats[ci] in hl else text_c
        x_ = cx(ci) + sw * (step - 1) / 2 - w_ / 2
        texts.append(_text_box(ctx, clamp(x_, rx, rx + rw - w_), plot_b + 6, w_,
                               _clip_lines(ctx, cats[ci], cat_s, w_, cl, cats[ci] in hl), cat_s, c,
                               bold=cats[ci] in hl, align="ctr", h=math.ceil(cl * cat_s * LINE_H) + 2,
                               name=f"カテゴリ:{cats[ci]}"))
    if step > 1:
        P.diag("category-thinned", f"カテゴリ名が収まらないため {step} つおきに表示しています"
                                   " → 項目を減らす・横棒（hbar）にする・カテゴリ名を短くする")
    _draw_annotations(ctx, g, P, D, (rx, ry, rw, rh), top0, anno_s)


ANNO_PAD = 28       # 注釈の箱の左右の余白(内側 8px × 2 + 字幅の見積もり誤差ぶんの余裕 12px)


def _draw_annotations(ctx, g, P, D, region, top0, size):
    """対象の上に短い吹き出し（角丸の箱＋細い引出線＋矢じり）。重なるときは横にずらし、だめなら段を上げる。"""
    if not D["annos"]:
        return
    rx, ry, rw, rh = region
    fill, fcol = ctx.c(g.get("anno_fill", "heading_text")), ctx.c(g.get("anno_color", "on_primary"))
    placed = []
    deficit = 0.0
    for a in sorted(D["annos"], key=lambda a: a["i"]):
        key = (a["i"], None)
        if a.get("series") is not None:
            for k, s in enumerate(D["series"]):
                if s["name"] == str(a["series"]):
                    key = (a["i"], k)
        anc = P.anchors.get(key) or P.anchors.get((a["i"], None))
        if not anc:
            P.diag("annotation-no-target", f"注釈「{a['text']}」の対象に値がありません")
            continue
        ax, ay = anc
        maxw = min(rw * 0.4, 280)

        def shape(mw):
            ls = wrap(ctx, a["text"], size, mw - ANNO_PAD, bold=True)
            return ls, min(max(tw(ctx, ln, size, bold=True) for ln in ls) + ANNO_PAD, mw)

        # 幅の候補: まず従来の最大幅。棒・ラベルに重なるときは、折り返して箱を細くして隣の棒の間に入れる
        shapes = []
        for f in (1.0, 0.75, 0.55, 0.4):
            mw = max(maxw * f, 90)
            ls, w_ = shape(mw)
            if not any(abs(w_ - o[2]) < 4 for o in shapes):
                shapes.append((ls, len(ls) * size * LINE_H + 10, w_))
        chosen, tiers, lines = None, 0, shapes[0][0]
        while chosen is None and tiers < 4:
            for ls, h, w in shapes:
                yy = ay - 16 - h - tiers * (shapes[0][1] + 8)
                ideal = ax - w / 2
                x_lo, x_hi = rx, rx + rw - w
                cand = sorted({clamp(ideal + d, x_lo, x_hi) for d in range(-400, 401, 8)}, key=lambda x: abs(x - ideal))
                for x in cand:
                    if not (x + 10 <= ax <= x + w - 10) and abs(x - ideal) > 1:
                        continue
                    r = (x, yy, w, h)
                    if any(_hit(r, o, 4) for o in placed) or any(_hit(r, o, 2) for o in P.blockers) or \
                            any(_hit(r, o, 2) for o in P.bars):
                        continue
                    chosen, lines = r, ls
                    break
                if chosen:
                    break
            if chosen is None:
                tiers += 1
        if chosen is None:        # 段を上げても入らない → 障害物の真上まで上げる（plot の上に取りしろが作られる）
            for ls, h, w in shapes:
                x = clamp(ax - w / 2, rx, rx + rw - w)
                obs = [o for o in P.bars + P.blockers + placed if o[0] < x + w + 2 and o[0] + o[2] > x - 2]
                yy = min([ay - 16 - h] + [o[1] - h - 6 for o in obs])
                r = (x, yy, w, h)
                if not any(_hit(r, o, 4) for o in placed):
                    chosen, lines, tiers = r, ls, tiers + 1
                    break
        if chosen is None:
            ls, h, w = shapes[0]
            lines = ls
            chosen = (clamp(ax - w / 2, rx, rx + rw - w), ay - 16 - h, w, h)
            P.diag("annotations-overlap", f"注釈「{a['text']}」が他の注釈・ラベル・棒と重なります"
                                          " → 注釈の文を短くする・注釈を減らす・項目を減らす")
        elif tiers:
            P.diag("annotations-stacked", f"注釈「{a['text']}」が近くの注釈・棒と並べられず上の段に移しました（引出線が長くなります）")
        x, yy, w, h = chosen
        deficit = max(deficit, top0 - yy)
        if yy < ry:               # 矩形の上にはみ出すときは、中に収めて、重なるなら警告する
            yy = ry
            chosen = (x, yy, w, h)
            if any(_hit(chosen, o, 2) for o in P.bars + P.blockers + placed):
                P.diag("annotations-overlap", f"注釈「{a['text']}」を置く縦の余白がなく、棒・ラベルと重なります"
                                              " → 注釈を減らす・短くする・項目を減らす")
        placed.append(chosen)
        P.anno_top = yy if P.anno_top is None else min(P.anno_top, yy)
        box = _rbox(ctx, x, yy, w, h, fill, ctx.radius("small", 6), name=f"注釈:{D['cats'][a['i']]}",
                    paras=[ctx.para(ln_, size, fcol, bold=True, align="ctr", lh=1.0) for ln_ in lines],
                    insets=(8, 3, 8, 3))
        box["text"]["wrap"] = False       # 行は見積もりで切り済み。HTML / PPTX の字幅差で勝手に折り返させない
        P.layers["ann"].append(box)
        lx = clamp(ax, x + 8, x + w - 8)
        el = ctx.path([(lx, yy + h), (ax, ay - 2)], fill, 1.25)
        el["name"] = "注釈の引出線"
        P.layers["ann"].append(el)
        P.layers["ann"].append(_tri(ctx, ax - 5, ay - 9, 10, 7, fill, up=False, name="注釈の矢じり"))
    P.deficit = max(P.deficit, deficit)


# ---------------------------------------------------------------------------
# 横棒
# ---------------------------------------------------------------------------

def _hbar_fit(g, row_h, m, val_s, smin, inner=3):
    """横棒 1 行ぶんの寸法。(棒群の太さ, 値ラベルの文字サイズ) を返す。値ラベルが隣の棒のラベルと縦に重ならない最大の文字サイズを選ぶ。
    入らなければ None。"""
    smin = _smin(smin)
    val_s = _cap_size(val_s, smin)
    base = min(row_h * 0.62, g.get("bar_h_max", 44))
    for bar_t in (base, max(base, row_h * 0.9)):
        bar_h = max((bar_t - (m - 1) * inner) / m, 1.0)
        pitch = (bar_h + inner) if m > 1 else row_h
        s_ = val_s
        while s_ >= smin - 1e-6:
            if math.ceil(s_ * LINE_H) + 1 <= pitch + 0.5:
                return bar_t, s_
            s_ -= 1
    return None


def _draw_hbar(ctx, g, P, D, series, palette, plot, region, S, drange, yfix, grid_on, show_vals, text_c, muted_c, grid_c,
               axis_c, base_c, hi_c, fade, tint, uf, ufu, anno_s, smin):
    plot_l, plot_t, plot_r, plot_b = plot
    rx, ry, rw, rh = region
    cats, n, hl, fc = D["cats"], D["n"], D["hl"], D["fc"]
    m = len(series)
    cat_s, val_s, tick_s, cat_w = S["cat_s"], S["val_s"], S["tick_s"], S["cat_w"]
    dlo, dhi = drange
    nt = int(clamp((plot_r - plot_l) / 110, 3, 6))
    lo, hi, step = nice_axis(dlo, dhi, nt, yfix[0], yfix[1], yfix[2])
    ticks = _ticks(lo, hi, step)
    pw = max(plot_r - plot_l, 10)
    X = lambda v: plot_l + (clamp(v, lo, hi) - lo) / (hi - lo) * pw           # noqa: E731
    base_v = 0.0 if lo <= 0 <= hi else lo
    x0 = X(base_v)
    row_h = max(plot_b - plot_t, 10) / n
    inner = 3
    bar_t = min(row_h * 0.62, g.get("bar_h_max", 44))
    if show_vals:
        fit = _hbar_fit(g, row_h, m, val_s, smin)
        if fit is None:
            show_vals = False
            P.diag("value-labels-crowded", f"値ラベルが棒の間隔に入らないため省きました（項目 {n} × 系列 {m}）"
                                           " → 項目か系列を減らす・縦棒（bar）にする・積み上げ（stacked）にする")
        else:
            bar_t, val_s = fit
    bar_h = max((bar_t - (m - 1) * inner) / m, 1.0)
    marks, texts, blockers = P.layers["marks"], P.layers["text"], P.blockers
    cat_mode, ser_mode = _hl_modes(hl, cats, [s["name"] for s in series])
    point_color = _point_color_fn(series, palette, cats, hl, cat_mode, ser_mode, base_c, hi_c, fade)
    tick_dec = max(_decimals([step, lo], cap=TICK_DEC_CAP), 0)
    if grid_on:
        for t in ticks:
            if abs(t - base_v) > 1e-9:
                P.layers["grid"].append(ctx.path([(X(t), plot_t), (X(t), plot_b)], grid_c, 0.75))
        for t in ticks:
            s = fmt_num(t, tick_dec)
            w_ = tw(ctx, s, tick_s) + 6
            texts.append(_text_box(ctx, clamp(X(t) - w_ / 2, rx, rx + rw - w_), plot_b + 4, w_, s, tick_s, muted_c,
                                   align="ctr", nowrap=True, name=f"目盛:{s}"))
    for ci in range(n):
        cy = plot_t + row_h * (ci + 0.5)
        hit_c = cat_mode and cats[ci] in hl
        cs_ = cat_s
        nl = len(wrap(ctx, cats[ci], cs_, cat_w))
        if nl * cs_ * LINE_H > row_h:       # 行の高さに収まらなければ文字を小さくする（下限 9px）
            cs_ = max(row_h / (nl * LINE_H), 9)
            nl = len(wrap(ctx, cats[ci], cs_, cat_w))
        c_h = math.ceil(nl * cs_ * LINE_H) + 1
        texts.append(_text_box(ctx, rx, clamp(cy - c_h / 2, ry, ry + rh - c_h), cat_w, cats[ci], cs_,
                               ctx.c("heading_text") if hit_c else text_c, bold=hit_c, align="r", h=c_h,
                               name=f"カテゴリ:{cats[ci]}"))
        for si in range(m):
            v = series[si]["vals"][ci]
            if v is None:
                continue
            c = point_color(si, ci)
            fcst = fc is not None and ci >= fc
            xa, xb = sorted((X(v), x0))
            by = cy - bar_t / 2 + si * (bar_h + inner)
            bw_ = max(xb - xa, 1.5)
            xa = xb - bw_ if v < base_v else min(xa, rx + rw - bw_)          # 細い棒は値の向き（負なら左）へ伸ばす。矩形の外へはみ出さない
            el = ctx.box(xa, by, bw_, bar_h, fill=(tint(c) if fcst else c),
                         name=f"棒:{cats[ci]}" + (f"/{series[si]['name']}" if m > 1 else ""))
            if fcst:
                el["line"] = {"color": c, "width": 1.25, "dash": "dash"}
            marks.append(el)
            P.bars.append((el["x"], el["y"], el["w"], el["h"]))
            right_end = xb + 6
            if show_vals:
                t = ufu(v)
                lw_ = tw(ctx, t, val_s, True, True) + 6
                lh_ = math.ceil(val_s * LINE_H) + 1
                lx = xb + 6 if v >= base_v else xa - 6 - lw_
                lx = clamp(lx, rx, rx + rw - lw_)
                ly = clamp(by + bar_h / 2 - lh_ / 2, ry, ry + rh - lh_)
                texts.append(_text_box(ctx, lx, ly, lw_, t, val_s,
                                       ctx.c("heading_text") if hit_c else text_c, bold=True, head=True,
                                       align="l" if v >= base_v else "r", nowrap=True, h=lh_,
                                       name=f"値:{cats[ci]}" + (f"/{series[si]['name']}" if m > 1 else "")))
                blockers.append((lx, ly, lw_, lh_))
                right_end = lx + lw_ + 6
            if v >= base_v:
                P.anchors.setdefault((ci, None), (right_end, by + bar_h / 2))
    P.layers["grid"].append(ctx.path([(x0, plot_t), (x0, plot_b)], axis_c, 1.0))
    # 注釈: 行の右、値ラベルのさらに右に置く（空きが足りなければ警告して省く）
    fill, fcol = ctx.c(g.get("anno_fill", "heading_text")), ctx.c(g.get("anno_color", "on_primary"))
    placed_h = []
    for a in D["annos"]:
        anc = P.anchors.get((a["i"], None))
        if not anc:
            continue
        ax, ay = anc
        lines = wrap(ctx, a["text"], anno_s, max(min(rw * 0.3, 240), 80), bold=True)
        w = min(max(tw(ctx, ln, anno_s, bold=True) for ln in lines) + ANNO_PAD, rw * 0.4)
        h = len(lines) * anno_s * LINE_H + 10
        # 行の右に置く。ほかの行の長い棒・注釈に重なるときは右へずらす
        ax0, x_ = ax, ax
        while x_ + w <= rx + rw and x_ - ax <= 12 * 400 and any(_hit((x_, ay - h / 2, w, h), o, 2) for o in P.bars + placed_h + P.blockers):
            x_ += 12
        if x_ + w > rx + rw or ay - h / 2 < ry or ay + h / 2 > ry + rh:
            P.diag("annotation-no-room", f"注釈「{a['text']}」を置く余白が右にありません（棒・値ラベルと重なる）"
                                         " → 注釈の文を短くする・y.max を大きくする")
            continue
        ax = x_
        placed_h.append((ax, ay - h / 2, w, h))
        box = _rbox(ctx, ax, ay - h / 2, w, h, fill, ctx.radius("small", 6), name=f"注釈:{cats[a['i']]}",
                    paras=[ctx.para(ln_, anno_s, fcol, bold=True, align="ctr", lh=1.0) for ln_ in lines],
                    insets=(8, 3, 8, 3))
        box["text"]["wrap"] = False
        P.layers["ann"].append(box)


# ---------------------------------------------------------------------------
# ドーナツ（構成比）。円弧は 3 次ベジェで近似
# ---------------------------------------------------------------------------

def _arc_cmds(cx, cy, r, a0, a1, move=True):
    """角度 a0→a1（ラジアン、12 時が 0、時計回り。a1 < a0 なら反時計回り）の円弧を 3 次ベジェの列にする（90° 以下に分割）。"""
    cmds = []
    segs = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2) - 1e-9))
    da = (a1 - a0) / segs
    pt = lambda a: (cx + r * math.sin(a), cy - r * math.cos(a))                # noqa: E731
    p0 = pt(a0)
    cmds.append(["M" if move else "L", round(p0[0], 2), round(p0[1], 2)])
    k = 4 / 3 * math.tan(da / 4)
    for i in range(segs):
        s, e = a0 + i * da, a0 + (i + 1) * da
        ps, pe_ = pt(s), pt(e)
        t_s, t_e = (math.cos(s), math.sin(s)), (math.cos(e), math.sin(e))      # 接線方向
        c1 = (ps[0] + k * r * t_s[0], ps[1] + k * r * t_s[1])
        c2 = (pe_[0] - k * r * t_e[0], pe_[1] - k * r * t_e[1])
        cmds.append(["C"] + [round(v, 2) for v in (*c1, *c2, *pe_)])
    return cmds


def _plan_donut(ctx, g, P, D, s, region, scale, text_c, muted_c, bg, ufu, leg_s, smin):
    rx, ry, rw, rh = region
    cats = D["cats"]
    vals = [max(v or 0.0, 0.0) for v in s["vals"]]
    total = sum(vals)
    if total <= 0:
        P.layers["marks"] += _placeholder(ctx, {"x": rx, "y": ry, "w": rw, "h": rh}, "構成比を出すには 0 より大きい値が必要です")
        return
    n = len(vals)
    toks = [ctx.c(t) for t in (g.get("series_colors") or ["primary", "accent", "muted"])]
    cols = [toks[i % len(toks)] if i < len(toks) else mix(toks[i % len(toks)], bg, min(0.35 + 0.15 * (i // len(toks)), 0.85))
            for i in range(n)]
    if D["hl"] and any(h in cats for h in D["hl"]):      # 項目名に一致する highlight があるときだけ他を薄くする
        cols = [c if cats[i] in D["hl"] else mix(c, bg, g.get("fade_tint", 0.55)) for i, c in enumerate(cols)]
    # --- 凡例の寸法（名前の列と構成比の列を近づけ、必要な幅だけ取る） --------------------
    shares = [f"{v / total * 100:.0f}%" for v in vals]
    gap_dl = 36

    def legend_metrics(ls):
        sw_ = ls * 0.9
        pct_w = max(tw(ctx, t, ls, True, True) for t in shares) + 6
        name_w = max(tw(ctx, c, ls) for c in cats) + 4
        return sw_, pct_w, name_w

    ls = clamp(min(leg_s * 1.15, rh / max(n, 1) / 1.35), smin, 20)     # 項目が多いときは文字を縮めて縦に収める
    sw_, pct_w, name_w = legend_metrics(ls)
    leg_w = sw_ + 8 + name_w + 14 + pct_w
    min_d = max(min(rw, rh) * 0.5, 80)
    layout, ncol = "right", 1
    d = min(rh, rw - gap_dl - leg_w)
    if d < min_d or n * smin * 1.3 > rh:      # 横に並べると輪が小さくなりすぎる／行が縦に入らない → 凡例を輪の下に置く
        layout = "bottom"
        while True:
            sw_, pct_w, name_w = legend_metrics(ls)
            leg_w = sw_ + 8 + name_w + 14 + pct_w
            row_h = ls * 1.55
            ncol = 2 if (n * row_h > rh * 0.4 and rw >= 2 * leg_w + 16) else 1
            leg_h = math.ceil(n / ncol) * row_h
            d = min(rw, rh - leg_h - 10)
            if d >= 56 or ls <= smin + 1e-6:
                break
            ls = max(ls - 1, smin)
        if d < 56:
            layout = "none"
            d = min(rw, rh)
            P.diag("donut-legend-no-room", f"項目名を置く余白がありません（{rw:.0f}×{rh:.0f}px に {n} 項目）"
                                           " → 矩形を広げる・項目を絞る・ブロックを大きくする")
    leg_w = min(leg_w, rw)
    if layout == "right":
        cluster = d + gap_dl + leg_w
        cx0 = rx + max((rw - cluster) / 2, 0)
        cx_, cy_ = cx0 + d / 2, ry + rh / 2
        lx0, ly0 = cx0 + d + gap_dl, None
    elif layout == "bottom":
        cx_, cy_ = rx + rw / 2, ry + d / 2
        lx0, ly0 = None, ry + d + 10
    else:
        cx_, cy_ = rx + rw / 2, ry + rh / 2
        lx0 = ly0 = None
    ro = d / 2
    ri = ro * g.get("donut_hole", 0.62)
    a = 0.0
    for i, v in enumerate(vals):
        if v <= 0:
            continue
        a1 = a + 2 * math.pi * v / total
        a1e = min(a1, a + 2 * math.pi - 1e-4)
        cmds = _arc_cmds(ro, ro, ro, a, a1e) + _arc_cmds(ro, ro, ri, a1e, a, move=False) + [["Z"]]
        P.layers["marks"].append({"kind": "shape", "geom": "custom", "x": round(cx_ - ro, 2), "y": round(cy_ - ro, 2),
                                  "w": round(2 * ro, 2), "h": round(2 * ro, 2), "fill": cols[i],
                                  "line": {"color": bg, "width": 2.0}, "name": f"構成:{cats[i]}",
                                  "path": [{"cmds": cmds, "fill": True, "stroke": True}]})
        a = a1
    # --- 中央の合計。穴に収まる大きさに縮め、収まらなければ単位を外し、それでもだめなら出さない ---
    unit = D["unit"]
    pct_unit = unit.strip() in ("%", "％")
    if ri >= 22 and not (pct_unit and abs(total - 100) < 0.5):      # 百分率で 100% は情報が無いので出さない
        dec_t = _decimals(vals)
        avail_t = ri * 1.6
        shown = None
        for text in ([ufu(total, dec_t)] + ([fmt_val(total, dec_t)] if unit else [])):
            t_ = min(clamp(ri * 0.5, smin, 54), 54)
            while t_ >= smin - 1e-6:
                if tw(ctx, text, t_, True, True) <= avail_t:
                    shown = (text, t_)
                    break
                t_ -= 1
            if shown:
                break
        if shown:
            text, ts = shown
            P.layers["text"].append(_text_box(ctx, cx_ - ri * 0.8, cy_ - ts * 0.85, ri * 1.6, text, ts,
                                              text_c, bold=True, head=True, align="ctr", nowrap=True, name="合計"))
            P.layers["text"].append(_text_box(ctx, cx_ - ri * 0.8, cy_ + ts * 0.45, ri * 1.6, "合計",
                                              max(ts * 0.38, smin), muted_c, align="ctr", nowrap=True,
                                              name="合計の見出し"))
    if layout == "none":
        return
    # --- 凡例 --------------------------------------------------------------
    def put_row(x, y, row_h, i, name_col_w):
        P.layers["text"].append(ctx.box(x, y + (row_h - sw_) / 2, sw_, sw_, fill=cols[i], name=f"凡例の色:{cats[i]}"))
        nm = cats[i]
        if tw(ctx, nm, ls) > name_col_w:                          # 長すぎる名前は「…」で切る
            while len(nm) > 1 and tw(ctx, nm + "…", ls) > name_col_w:
                nm = nm[:-1]
            nm += "…"
        th_ = math.ceil(ls * LINE_H) + 1
        ty = clamp(y + (row_h - th_) / 2, ry, ry + rh - th_)
        P.layers["text"].append(_text_box(ctx, x + sw_ + 8, ty, name_col_w + 2, nm, ls,
                                          text_c, h=th_, nowrap=True, name=f"凡例:{cats[i]}"))
        P.layers["text"].append(_text_box(ctx, x + sw_ + 8 + name_col_w + 14, ty, pct_w,
                                          shares[i], ls, text_c, bold=True, head=True, align="r", nowrap=True,
                                          h=th_, name=f"構成比:{cats[i]}"))

    if layout == "right":
        row_h = min(clamp(rh / max(n, 1), ls * 1.6, ls * 2.6), rh / max(n, 1))
        y = ry + (rh - row_h * n) / 2
        ncw = max(min(name_w, leg_w - sw_ - 8 - 14 - pct_w), 10)
        for i in range(n):
            put_row(lx0, y, row_h, i, ncw)
            y += row_h
    else:
        row_h = ls * 1.55
        per = math.ceil(n / ncol)
        col_w = (rw - (ncol - 1) * 16) / ncol
        ncw = max(min(name_w, col_w - sw_ - 8 - 14 - pct_w), 10)
        block_w = min(sw_ + 8 + ncw + 14 + pct_w, col_w)
        total_w = block_w * ncol + 16 * (ncol - 1)
        x0 = rx + (rw - total_w) / 2
        for i in range(n):
            c_, r_ = divmod(i, per)
            put_row(x0 + c_ * (block_w + 16), ly0 + r_ * row_h, row_h, i, ncw)


def layout_chart(slide, st, ctx, body):
    return _plan_chart(slide, st, ctx, body).elements()


def diagnose_chart(slide, st, ctx, body) -> list:
    """レイアウト計算でわかる問題 [(コード, 説明)]。合成スライドのブロックなど、実際の矩形で呼べる。"""
    return list(_plan_chart(slide, st, ctx, body).diags)


# ---------------------------------------------------------------------------
# 検証
# ---------------------------------------------------------------------------

def _unknown(where, keys, known, warn, label):
    for k in keys:
        if isinstance(k, str) and k.startswith("_"):      # `_` 始まりは利用者のメモ用（常に除外）
            continue
        if k not in known:
            m = difflib.get_close_matches(str(k), sorted(known), n=1)
            warn(f"{where}: {label}の '{k}' は未知のキーです" + (f"（候補: {m[0]}）" if m else "") +
                 " → references/schema/ の kpi / chart の節にあるキー名に直す（メモなら先頭に _ を付ける）")


THEME_COLOR_TOKENS = ("background", "surface", "text", "muted", "primary", "accent", "on_primary", "on_primary_soft",
                      "on_primary_muted", "code_bg", "code_text", "table_header_bg", "table_header_text", "table_row_alt",
                      "highlight_fill", "border", "heading_text", "accent_on_primary")
_KPI_BODY_KEYS = set(_KPI_BODY) | {"value_size"}
_CHART_BODY_KEYS = set(_CHART_BODY)


def json_repr(v) -> str:
    return f"'{v}'" if isinstance(v, str) else repr(v)


def _check_style_body(slide, where, known, warn):
    """style.body の未知キーを警告する（打ち間違いが無言で無視されないように）。"""
    st = slide.get("style")
    body = st.get("body") if isinstance(st, dict) else None
    if isinstance(body, dict):
        _unknown(where, body.keys(), known, warn, "style.body")


def validate(slide: dict, i: int, fail, warn, unknown_keys: bool = True, diagnose: bool = True) -> None:
    """kpi / chart の検証。unknown_keys=False: スライド直下の未知キー警告は deck_schema が出すので出さない（二重にしない）。
    diagnose=False: 配置の試算（ラベルの重なり・注釈の衝突）は呼び出し側が実際のスタイル・矩形で行う（build_deck では autofit）。"""
    t = slide.get("type")
    where = f"{i + 1}枚目（type={t}）"
    if t == "kpi":
        _validate_kpi(slide, where, fail, warn, unknown_keys)
    elif t == "chart":
        _validate_chart(slide, where, fail, warn, unknown_keys, diagnose)


def _validate_kpi(slide, where, fail, warn, unknown_keys=True):
    items = slide.get("items")
    if unknown_keys:
        _unknown(where, slide.keys(), KNOWN_KEYS["kpi"], warn, "スライド")
    if not isinstance(items, list) or not items:
        fail(f"{where}: items（[{{value, unit, label}}] の配列）が必要です"
             " → 例: \"items\": [{\"value\": \"2.1\", \"unit\": \"時間\", \"label\": \"作成時間\"}]")
        return
    if len(items) > 4:
        warn(f"{where}: items が{len(items)}件あります（1〜4件が目安。多いと数字が小さくなる）→ 主役を絞るか、cards / table に分ける")
    if unknown_keys:       # build_deck では style の領域内プロパティ検査（deck_schema.check_region_value）が出す
        _check_style_body(slide, where, _KPI_BODY_KEYS, warn)
    for k, it in enumerate(items):
        if not isinstance(it, dict):
            if not isinstance(it, (str, int, float)) or isinstance(it, bool):
                fail(f"{where}: items[{k}] は {{value, unit, label}} のオブジェクトで書いてください")
            else:
                warn(f"{where}: items[{k}] が値だけ（'{it}'）です。単位や説明が付けられません"
                     " → {\"value\": \"2.1\", \"unit\": \"時間\", \"label\": \"…\"} の形で書く")
            continue
        _unknown(where, it.keys(), KPI_ITEM_KEYS, warn, f"items[{k}]")
        v = it.get("value")
        if v is None or v == "" or isinstance(v, bool):
            fail(f"{where}: items[{k}] に value（大きく見せる数字）が必要です")
            continue
        if not isinstance(v, (str, int, float)):
            fail(f"{where}: items[{k}].value は文字列か数値にしてください（{type(v).__name__} は使えません）"
                 " → 例: \"value\": \"2.1\"")
            continue
        for key in ("unit", "from_unit", "label", "from", "delta", "note", "of"):
            x = it.get(key)
            if x is not None and (isinstance(x, (dict, list)) or isinstance(x, bool)):
                fail(f"{where}: items[{k}].{key} は文字列か数値にしてください")
        if it.get("of") is not None and it.get("from") is not None:
            warn(f"{where}: items[{k}] に of（全体の数）と from（変化前）が両方あります。併用すると「6.5 → 9 / 12」のような読めない表示になるため、"
                 "of は無視して from（変化）を表示します → 進捗（9 / 12）にしたいなら from を消す。変化（6.5 → 2.1）なら of を消す")
        if isinstance(v, (int, float)) and math.isfinite(v):
            # 数値型も文字列と同じ桁数検査にかける（JSON の数値で書いても検査をすり抜けない）
            vs = str(v) if isinstance(v, int) else (f"{v:.10f}".rstrip("0").rstrip("."))
            digits = len(re.sub(r"\D", "", vs))
            if digits > 10:
                warn(f"{where}: items[{k}].value {v} は桁が多すぎます（{digits}桁。10桁以内が目安）"
                     " → 万・億に換算して unit に「万円」「億円」のように書く")
        elif isinstance(v, str) and v.strip():
            vs = v.strip()
            if to_float(vs) is not None:        # 数字だけ（桁区切り・小数点・符号・% は桁数に数えない）
                digits = len(re.sub(r"\D", "", vs))
                if digits > 10:
                    warn(f"{where}: items[{k}].value '{v}' は桁が多すぎます（{digits}桁。10桁以内が目安）"
                         " → 万・億に換算して unit に「万円」「億円」のように書く")
            elif len(re.sub(r"【要確認[^】]*】", "", vs)) > 8:     # 【要確認: …】の印は字数に数えない（強調表示で足りる。確かめる点は印の中に書いてよい。S5b）
                warn(f"{where}: items[{k}].value '{v}' が長すぎます（8文字以内が目安）"
                     " → 数字だけにして単位は unit に、説明は label / note に分ける")
        g_ = it.get("good")
        if g_ is not None and g_ not in ("up", "down"):
            m = difflib.get_close_matches(str(g_), ["up", "down"], n=1)
            fail(f"{where}: items[{k}].good '{g_}' は \"up\"（増えると良い）か \"down\"（減ると良い）で指定してください" +
                 (f"（候補: {m[0]}）" if m else ""))
        if g_ and not it.get("delta"):
            warn(f"{where}: items[{k}] に good があるのに delta がありません → delta（例 \"−68%\"）を足すか good を外す")
        if it.get("of") is not None:
            a, b = to_float(v), to_float(it.get("of"))
            if a is None or b is None or b <= 0:
                warn(f"{where}: items[{k}] の of（全体の数）は 0 より大きい数、value は数字にしてください（進捗バーを描けません）")
            elif a > b:
                warn(f"{where}: items[{k}] の value（{v}）が of（{it.get('of')}）より大きいです")
        if it.get("delta") and g_ in ("up", "down") and _direction(it) is None:
            warn(f"{where}: items[{k}] の動き（増減）を value と from か delta の符号（+ / −）から読めません。色は「良い」側になります"
                 " → from を足すか delta を \"+10%\" / \"−68%\" の形にする")


def _validate_chart(slide, where, fail, warn, unknown_keys=True, diagnose=True):
    if unknown_keys:
        _unknown(where, slide.keys(), KNOWN_KEYS["chart"], warn, "スライド")
    raw_kind = str(slide.get("chart", "bar") or "bar")
    kind = CHART_ALIASES.get(raw_kind, raw_kind)
    if kind not in CHART_KINDS:
        m = difflib.get_close_matches(raw_kind, list(CHART_KINDS) + list(CHART_ALIASES), n=1)
        fail(f"{where}: chart '{raw_kind}' は未対応の種類です（{' / '.join(CHART_KINDS)}）" + (f"。候補: {m[0]}" if m else ""))
        return
    cats, series = slide.get("categories"), slide.get("series")
    if not isinstance(cats, list) or not cats:
        fail(f"{where}: categories（項目名の配列）が必要です → 例: \"categories\": [\"Q1\", \"Q2\"]")
        return
    if not isinstance(series, list) or not series:
        fail(f"{where}: series（[{{name, values}}] の配列）が必要です"
             " → 例: \"series\": [{\"name\": \"作成時間\", \"values\": [6.8, 6.5]}]")
        return
    ok = True
    for k, s in enumerate(series):
        if not isinstance(s, dict) or not isinstance(s.get("values"), list):
            fail(f"{where}: series[{k}] は {{name, values}} で、values は数値の配列にしてください")
            ok = False
            continue
        _unknown(where, s.keys(), CHART_SERIES_KEYS, warn, f"series[{k}]")
        if s.get("color") is not None:
            c_ = s.get("color")
            if not isinstance(c_, str) or not (is_hex6(c_) or c_ in THEME_COLOR_TOKENS or c_ in SEMANTIC_COLORS):
                near = difflib.get_close_matches(str(c_), list(THEME_COLOR_TOKENS) + list(SEMANTIC_COLORS), n=1)
                fail(f"{where}: series[{k}].color {json_repr(c_)} はテーマの色名でも #RRGGBB でもありません"
                     f"（色名の例: primary / accent / muted / text / surface / border、または \"#0F3D6E\" のように # と6桁で）"
                     + (f"。候補: {near[0]}" if near else ""))
        if len(s["values"]) != len(cats):
            fail(f"{where}: series[{k}]（{s.get('name', '')}）の values が{len(s['values'])}個ですが categories は{len(cats)}個です"
                 " → 個数をそろえる（欠測は null）")
            ok = False
        for j, v in enumerate(s["values"]):
            if v is not None and not _is_num(v):
                fail(f"{where}: series[{k}].values[{j}] '{v}' が数値ではありません → 数値（JSON の数）で書く。欠測は null")
                ok = False
        if kind not in ("waterfall", "donut") and len(series) > 1 and not s.get("name"):
            warn(f"{where}: series[{k}] に name がありません（凡例に「系列{k + 1}」と出ます）")
    if not ok:
        return
    if unknown_keys:
        _check_style_body(slide, where, _CHART_BODY_KEYS, warn)
    n, m = len(cats), len(series)
    seen, dups = set(), []
    for c in cats:
        if str(c) in seen and str(c) not in dups:
            dups.append(str(c))
        seen.add(str(c))
    if dups:
        warn(f"{where}: categories に同じ名前の項目があります（{' / '.join(dups[:3])}）。highlight・annotations・forecast_from が"
             "どの項目を指すか曖昧になります → 項目名を区別する（例: Q1（2025）/ Q1（2026））")
    if all(v is None for s_ in series for v in s_["values"]):
        warn(f"{where}: values がすべて null です。描くものがありません → 値を入れる")
    if kind in ("waterfall", "donut") and m > 1:
        warn(f"{where}: {kind} は系列を1つだけ使います（2つ目以降は描かれません）")
    if (kind in ("bar", "line") and m > 5) or (kind == "stacked" and m > 6):
        warn(f"{where}: 系列が{m}本あります（5本程度まで。色が見分けにくい）→ 系列を絞るか表（table）にする")
    if kind == "bar" and n > 12:
        warn(f"{where}: 項目が{n}個あります（縦棒は12個程度まで。ラベルが重なる）→ 横棒（hbar）にするか項目を絞る")
    if kind == "hbar" and n > 15:
        warn(f"{where}: 項目が{n}個あります（15個程度まで）→ 上位だけに絞る")
    if kind == "line" and n > 24:
        warn(f"{where}: 点が{n}個あります（24個程度まで）→ 期間を集約する")
    if kind == "donut":
        if n > 6:
            warn(f"{where}: donut の項目が{n}個あります（6個程度まで）→ 小さい項目を「その他」にまとめる")
        if any(_is_num(v) and v < 0 for v in series[0]["values"]):
            fail(f"{where}: donut に負の値は使えません → bar か waterfall にする")
    names = {str(c) for c in cats} | {str(s.get("name", "")) for s in series if isinstance(s, dict)}
    hl = slide.get("highlight")
    if hl is not None and not isinstance(hl, list):
        fail(f"{where}: highlight は項目名（または系列名）の配列にしてください")
    for h in hl if isinstance(hl, list) else []:
        if str(h) not in names:
            m_ = difflib.get_close_matches(str(h), sorted(names), n=1)
            warn(f"{where}: highlight '{h}' が categories にも series の name にもありません" +
                 (f"（候補: {m_[0]}）" if m_ else ""))
    ff = slide.get("forecast_from")
    if ff is not None and str(ff) not in [str(c) for c in cats]:
        m_ = difflib.get_close_matches(str(ff), [str(c) for c in cats], n=1)
        fail(f"{where}: forecast_from '{ff}' が categories にありません" + (f"（候補: {m_[0]}）" if m_ else ""))
    annos = slide.get("annotations")
    if annos is not None and not isinstance(annos, list):
        fail(f"{where}: annotations は [{{at, text}}] の配列にしてください")
    for k, a in enumerate(annos if isinstance(annos, list) else []):
        if not isinstance(a, dict) or not a.get("text") or a.get("at") is None:
            fail(f"{where}: annotations[{k}] には at（項目名）と text（短い文）が必要です")
            continue
        _unknown(where, a.keys(), CHART_ANNO_KEYS, warn, f"annotations[{k}]")
        if a.get("series") is not None and str(a["series"]) not in [str(s_.get("name", "")) for s_ in series]:
            m_ = difflib.get_close_matches(str(a["series"]), [str(s_.get("name", "")) for s_ in series], n=1)
            warn(f"{where}: annotations[{k}].series '{a['series']}' が series の name にありません" +
                 (f"（候補: {m_[0]}）" if m_ else "") + " → 系列名を直す（無指定なら項目の先頭の系列に付く）")
        if str(a["at"]) not in [str(c) for c in cats]:
            m_ = difflib.get_close_matches(str(a["at"]), [str(c) for c in cats], n=1)
            fail(f"{where}: annotations[{k}].at '{a['at']}' が categories にありません" + (f"（候補: {m_[0]}）" if m_ else ""))
        elif len(str(a["text"])) > 20:
            warn(f"{where}: annotations[{k}].text が長いです（20字以内が目安）→ 短くして、詳しい説明は note や本文に")
    if isinstance(annos, list) and len(annos) > 4:
        warn(f"{where}: 注釈が{len(annos)}個あります（3個以内が目安）→ 要点だけに絞る")
    y = slide.get("y")
    if y is not None:
        if not isinstance(y, dict):
            fail(f"{where}: y は {{min, max, label}} のオブジェクトにしてください")
        else:
            _unknown(where, y.keys(), CHART_Y_KEYS, warn, "y")
            for key in ("min", "max", "step"):
                if y.get(key) is not None and not _is_num(y[key]):
                    fail(f"{where}: y.{key} は数値で指定してください")
            if _is_num(y.get("min")) and _is_num(y.get("max")) and y["min"] >= y["max"]:
                fail(f"{where}: y.min（{y['min']}）は y.max（{y['max']}）より小さくしてください")
    vals_flag = slide.get("values")
    if vals_flag is not None and vals_flag not in (True, False, "ends"):
        fail(f"{where}: values は true / false / \"ends\"（最初と最後の点だけ）のいずれかです")
    if kind == "waterfall":
        tot = slide.get("totals")
        if tot is not None and (not isinstance(tot, list) or any(str(x) not in [str(c) for c in cats] for x in tot)):
            fail(f"{where}: totals は categories にある項目名の配列にしてください（合計・開始の項目）")
        else:
            tset = {str(x) for x in tot} if isinstance(tot, list) else {str(cats[0]), str(cats[-1])}
            run = 0.0
            for c, v in zip(cats, series[0]["values"]):
                if str(c) in tset:
                    if v is not None and run != 0.0 and abs(run - v) > 1e-6:
                        warn(f"{where}: 合計「{c}」の値（{v}）が手前までの積み上げ（{round(run, 6)}）と一致しません"
                             " → 値を確かめる（【要確認】）")
                    run = v if v is not None else run
                else:
                    run += v or 0.0
        if slide.get("good") not in (None, "up", "down"):
            fail(f"{where}: good は \"up\" か \"down\" です")
    # レイアウト計算でわかる問題（既定の全面サイズで試算）
    if not diagnose:
        return
    try:
        ctx = pe.Ctx({"colors": {"background": "#FFFFFF", "text": "#1A2233", "muted": "#5A6B85", "primary": "#0F3D6E",
                                 "accent": "#007D96", "surface": "#E0E7F0", "border": "#BCC8D8", "on_primary": "#FFFFFF",
                                 "heading_text": "#0F3D6E"}, "fonts": {}})
        for code, msg in diagnose_chart(slide, {"body": dict(_CHART_BODY)}, ctx, {"x": 72, "y": 192, "w": 1136, "h": 452}):
            warn(f"{where}: {msg}")
    except Exception as e:   # 試算で落ちても検証全体は止めない
        warn(f"{where}: グラフの配置試算に失敗しました（{type(e).__name__}）。データの形を確かめてください")


# 型ごとの入口（proposal_engine.LAYOUTS と同じ形）
LAYOUTS = {"kpi": layout_kpi, "chart": layout_chart}


# スライド直下のタイプ固有キー（共通キーを除く）。deck_schema.known_slide_keys が登録表経由で引く
SLIDE_KEYS = {
    "kpi": frozenset(KNOWN_KEYS["kpi"] - set(_UNIVERSAL_SLIDE_KEYS)),
    "chart": frozenset(KNOWN_KEYS["chart"] - set(_UNIVERSAL_SLIDE_KEYS)),
}

def validate_wired(slide: dict, i: int, fail, warn) -> None:
    """build_deck に結線した検証。スライド直下の未知キーは deck_schema が、配置の試算は autofit が実際のスタイルで行うので、
    ここでは出さない（二重に警告しない）。"""
    validate(slide, i, fail, warn, unknown_keys=False, diagnose=False)


# 登録表への登録（engine_registry）。kpi は余白が前提（大きな数字だけで構成する）
engine_registry.register(
    "kpi", layout_kpi, validate_wired, slide_keys=SLIDE_KEYS["kpi"], self_checked=False,
    sparse_ok=True, relation=("parallel",), claim_keys=("note",), display_keys=("label", "note", "delta"),
    text_skip_keys=("good", "of", "emphasis", "unit"))
engine_registry.register(
    "chart", layout_chart, validate_wired, slide_keys=SLIDE_KEYS["chart"],
    relation=("contrast",), claim_keys=("note",), display_keys=("note", "text"),
    text_skip_keys=("chart", "good", "highlight", "forecast_from", "totals", "unit"))

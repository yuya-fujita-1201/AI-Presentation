# -*- coding: utf-8 -*-
"""合成スライド（type: "composite"）の純粋な部分: 格子の割り付け・ブロックの枠と小見出し・合成専用ブロック（text / callout / image）。

1 枚のスライドに複数のブロックを置く。本文領域を `columns`（列の比率）と `rows`（行の比率）の格子に分け、
ブロックを書いた順に左上から右へ、行を折り返して置く。位置を指定したいときだけ `col` `row`（0 始まり）と
`col_span` `row_span` を書く。x / y / w / h は書かせない。

このモジュールは build_deck を import しない（標準ライブラリと ja_text / autofit / proposal_engine / canvas_engine だけ）。
既存タイプ（bullets / table / cards / 図解 …）をブロックの矩形に描く部分は build_deck 側（resolve_composite_blocks /
html_slide_body(bare=True) / build_pptx の s_composite）が担い、ここは次を提供する。

    plan_grid(blocks, columns, rows, arrange)      -> {"columns", "rows", "cells", "empty"}   格子の割り付け（検証つき）
    grid_rects(body, plan, gap_x, gap_y)           -> ブロックごとの矩形 (x, y, w, h)
    frame_geometry(rect, block, bs)                -> 枠・小見出しを引いた内容の矩形と、枠の寸法
    frame_elements(ctx, geo, block, theme_ctx ...) -> 枠と小見出しの canvas 要素
    fit_text_block / text_elements / callout_elements / image_elements   合成専用ブロックの描画（canvas 要素）

文字の大きさ・余白・小見出しの大きさなどの数値は `templates/layouts/default.json` の `types.composite` が持つ
（形トークン参照）。このモジュールは st（解決済みの領域の値）から読むだけで、見た目の数値を直書きしない。
"""
from __future__ import annotations

import difflib
import math

import autofit
import ja_text
import proposal_engine as pe

# ---------------------------------------------------------------------------
# ブロックのキーと種類
# ---------------------------------------------------------------------------

# ブロック共通のキー（中身のキーはタイプごと）
BLOCK_COMMON_KEYS = ("type", "heading", "frame", "emphasis", "align", "valign", "col", "row", "col_span", "row_span", "style")
FRAMES = ("none", "box", "line")
ALIGNS = ("left", "center", "right")
VALIGNS = ("top", "middle", "bottom")

# 合成専用のブロック（スライドのタイプとしては存在しない）。中身のキー
NATIVE_KEYS = {
    "text": {"text", "paragraphs"},
    "callout": {"text", "note"},
    "image": {"path", "caption", "fit", "alt"},
}
NATIVE_TYPES = tuple(NATIVE_KEYS)

# ブロックにできない既存タイプと、その理由と直し方
UNSUPPORTED = {
    "title": "表紙は 1 枚を使う全面のタイプです → 表紙は単独のスライドにする",
    "section": "章扉は 1 枚を使う全面のタイプです → 章扉は単独のスライドにする",
    "closing": "終わりのスライドは全面のタイプです → 単独のスライドにする",
    "statement": "全面に 1 つの主張を置くタイプです → 単独のスライドにする（合成の中なら callout のブロックを使う）",
    "quote": "引用は全面のタイプです → 単独のスライドにする（合成の中なら text か callout のブロックを使う）",
    "agenda": "目次は全面のタイプです → 単独のスライドにする",
    "canvas": "canvas は座標で自由に置くタイプです → 単独の canvas スライドにする",
    "composite": "合成スライドの入れ子はできません → ブロックを同じ composite のブロックとして並べるか、2 枚に分ける",
    "split": "split は端まで届くパネルを持つ全面のタイプです（split の中にも置けません） → 入れ子にせず、中身のブロックを外側の split か composite の blocks に並べる（2 枚に分けてもよい）",
    "two_column": "two_column は 2 つの箱で 1 枚を使うタイプです → bullets のブロック（frame: box）を 2 つ並べる",
    "image_text": "image_text は画像と箇条書きで 1 枚を使うタイプです → image のブロックと bullets のブロックを並べる",
    "swimlane_legend": "凡例ページは swimlane から自動で作られます → 単独のスライドにはしない",
    "diagram_legend": "凡例ページは図解から自動で作られます → 単独のスライドにはしない",
}


def key_hint(key, pool) -> str:
    m = difflib.get_close_matches(str(key), sorted(str(p) for p in pool), n=1, cutoff=0.5)
    return f"（もしかして \"{m[0]}\"）" if m else ""


# ---------------------------------------------------------------------------
# 格子: 名前つきの配置と割り付け
# ---------------------------------------------------------------------------

# 名前 → columns / rows と、先頭のブロックから順に置く場所 cells=[(col, row, col_span, row_span)]（無ければ自動）
ARRANGE = {
    "two":             {"columns": [1, 1], "rows": [1], "doc": "2 列（左 | 右）"},
    "three":           {"columns": [1, 1, 1], "rows": [1], "doc": "3 列"},
    "four":            {"columns": [1, 1, 1, 1], "rows": [1], "doc": "4 列"},
    "main-side":       {"columns": [3, 2], "rows": [1], "doc": "主 3 : 副 2（左が主）"},
    "side-main":       {"columns": [2, 3], "rows": [1], "doc": "副 2 : 主 3（右が主）"},
    "top-bottom":      {"columns": [1], "rows": [1, 1], "doc": "上 | 下"},
    "main-bottom":     {"columns": [1], "rows": [2, 1], "doc": "上が主（2）| 下が副（1）"},
    "top-main":        {"columns": [1], "rows": [1, 2], "doc": "上が副（1）| 下が主（2）"},
    "2x2":             {"columns": [1, 1], "rows": [1, 1], "doc": "2 × 2 の 4 ブロック"},
    "3x2":             {"columns": [1, 1, 1], "rows": [1, 1], "doc": "3 列 × 2 段の 6 ブロック"},
    "main-side-stack": {"columns": [3, 2], "rows": [1, 1], "cells": [(0, 0, 1, 2)],
                        "doc": "左に主（縦に全高）、右に 2 段（1 番目が主、2 番目と 3 番目が右の上と下）"},
    "stack-main":      {"columns": [2, 3], "rows": [1, 1], "cells": [(0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 2)],
                        "doc": "左に 2 段（1 番目と 2 番目）、右に主（3 番目、縦に全高）"},
    "top-wide":        {"columns": [1, 1], "rows": [1, 1], "cells": [(0, 0, 2, 1)],
                        "doc": "上に横長の 1 ブロック（1 番目）、下に 2 ブロック"},
    "bottom-wide":     {"columns": [1, 1], "rows": [1, 1], "cells": [(0, 0, 1, 1), (1, 0, 1, 1), (0, 1, 2, 1)],
                        "doc": "上に 2 ブロック、下に横長の 1 ブロック（3 番目）"},
}


# rows を書かないとき、置ききれなければ行を足していくが、その上限（桁を間違えた row / row_span が巨大な格子を作らないため）
MAX_AUTO_ROWS = 12
# columns / rows の比率 1 つの上限（NaN・Infinity・1e308 を弾く）
MAX_RATIO = 1e6


def default_columns(n: int) -> list:
    """columns を書かず arrange も無いときの列の比率（ブロック数から決める）。"""
    if n <= 1:
        return [1]
    if n == 2:
        return [1, 1]
    if n == 3:
        return [1, 1, 1]
    if n == 4:
        return [1, 1]
    return [1, 1, 1]


def _ratio_list(v, name: str, problems: list):
    """比率の配列（正の数）にそろえる。形が悪ければ problems に fail の文を足して None。"""
    if not isinstance(v, list) or not v:
        problems.append(f"{name} は比率の配列で指定してください（例: [3, 2]）")
        return None
    out = []
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not (x > 0):
            problems.append(f"{name} の要素は 0 より大きい数で指定してください（{x!r} が書かれています）")
            return None
        if not math.isfinite(x) or x > MAX_RATIO:
            problems.append(f"{name} の要素は有限で {MAX_RATIO:g} 以下の数で指定してください（{x!r} が書かれています）"
                            f" → 比率は [3, 2] のような小さい数にする")
            return None
        out.append(float(x))
    return out


def plan_grid(blocks: list, columns=None, rows=None, arrange=None) -> dict:
    """ブロックを格子に割り付ける。
    戻り値 {"columns": [比率], "rows": [比率], "cells": [(col, row, col_span, row_span)] ,"empty": [(col, row)], "problems": [fail の文]}
    problems が空でないとき、cells は信用できない（呼び出し側が fail にする）。
    規則: 明示した col/row が先に置かれる → 残りは書いた順に左上から右へ（行を折り返して）空いている最初の場所へ。
    rows を書かず、置ききれないときは行を足す。rows を書いたのに置ききれないときは problems。"""
    problems: list = []
    n = len(blocks)
    preset = ARRANGE.get(arrange) if isinstance(arrange, str) else None
    if isinstance(arrange, str) and preset is None:
        names = " / ".join(ARRANGE)
        problems.append(f"arrange '{arrange}' は未知の配置名です{key_hint(arrange, ARRANGE)} → 使える名前: {names}")
    cols_user = columns is not None
    rows_user = rows is not None
    cols = _ratio_list(columns, "columns", problems) if cols_user else None
    rws = _ratio_list(rows, "rows", problems) if rows_user else None
    if problems:
        return {"columns": cols or [1.0], "rows": rws or [1.0], "cells": [], "empty": [], "problems": problems}
    if cols is None:
        cols = [float(x) for x in preset["columns"]] if preset else [float(x) for x in default_columns(n)]
    if rws is None:
        rws = [float(x) for x in preset["rows"]] if preset else None
    rows_auto = rws is None
    if rws is None:
        rws = [1.0]
    nc = len(cols)
    # 名前つき配置の cells は、格子の大きさが名前の定義と同じときだけ使う（columns / rows を書き換えたら自動配置）
    preset_cells = []
    if preset and preset.get("cells") and len(preset["columns"]) == nc and len(preset["rows"]) == len(rws) and not rows_auto:
        preset_cells = list(preset["cells"])
    elif preset and preset.get("cells") and rows_auto and len(preset["columns"]) == nc:
        preset_cells = list(preset["cells"])
    cells: list = [None] * n
    occupied: set = set()

    def area(c, r, cs, rs):
        return {(c + a, r + b) for a in range(cs) for b in range(rs)}

    def spans_of(b):
        cs = b.get("col_span", 1) if isinstance(b, dict) else 1
        rs = b.get("row_span", 1) if isinstance(b, dict) else 1
        return (cs if isinstance(cs, int) and not isinstance(cs, bool) and cs >= 1 else 1,
                rs if isinstance(rs, int) and not isinstance(rs, bool) and rs >= 1 else 1)

    def label(k):
        t = blocks[k].get("type") if isinstance(blocks[k], dict) else "?"
        return f"{k + 1} つ目のブロック（{t}）"

    # 1) 明示の位置（col / row）
    explicit = []
    for k, b in enumerate(blocks):
        if not isinstance(b, dict):
            continue
        has_c, has_r = b.get("col") is not None, b.get("row") is not None
        cs, rs = spans_of(b)
        if cs > nc:
            problems.append(f"{label(k)}: col_span={cs} が列の数（{nc}）を超えています → col_span を {nc} 以下にするか columns を増やす")
            continue
        if has_c and has_r:
            c, r = b["col"], b["row"]
            for nm, v in (("col", c), ("row", r)):
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    problems.append(f"{label(k)}: {nm} は 0 以上の整数で指定してください（0 始まり。{v!r} が書かれています）")
            if problems and any(label(k) in p for p in problems):
                continue
            if c + cs > nc:
                problems.append(f"{label(k)}: col={c}・col_span={cs} が列の数（{nc}）を超えています"
                                f" → col を 0〜{nc - cs} にする（列は 0 から数える）か columns を増やす")
                continue
            if r + rs > len(rws):
                if rows_auto and r + rs <= MAX_AUTO_ROWS:
                    rws += [1.0] * (r + rs - len(rws))
                elif rows_auto:
                    problems.append(f"{label(k)}: row={r}・row_span={rs} は大きすぎます（行は自動で最大 {MAX_AUTO_ROWS} 行まで）"
                                    f" → row を 0〜{max(MAX_AUTO_ROWS - rs, 0)} にする（行は 0 から数える）。それ以上の行が要るなら 2 枚に分ける")
                    continue
                else:
                    problems.append(f"{label(k)}: row={r}・row_span={rs} が行の数（{len(rws)}）を超えています"
                                    f" → row を 0〜{len(rws) - rs} にするか rows を増やす")
                    continue
            a = area(c, r, cs, rs)
            if a & occupied:
                problems.append(f"{label(k)}: col={c}・row={r} は別のブロックと重なります → 場所をずらすか span を小さくする")
                continue
            occupied |= a
            cells[k] = (c, r, cs, rs)
        elif has_c != has_r:
            explicit.append(k)       # 片方だけ書いた: 自動配置のとき、その列（行）の中で最初に空いている場所に置く
    # 2) 名前つき配置の cells（先頭のブロックから、明示の位置が無いものだけ）
    for k, (c, r, cs, rs) in zip(range(n), preset_cells):
        if cells[k] is not None or not isinstance(blocks[k], dict) or blocks[k].get("col") is not None or blocks[k].get("row") is not None:
            continue
        a = area(c, r, cs, rs)
        if (c + cs <= nc and r + rs <= len(rws)) and not (a & occupied):
            occupied |= a
            cells[k] = (c, r, cs, rs)
    # 3) 残りを書いた順に自動配置
    cur_r, cur_c = 0, 0
    for k, b in enumerate(blocks):
        if cells[k] is not None or not isinstance(b, dict):
            continue
        cs, rs = spans_of(b)
        if cs > nc:
            problems.append(f"{label(k)}: col_span={cs} が列の数（{nc}）を超えています → col_span を {nc} 以下にするか columns を増やす")
            continue
        only_c = b.get("col") if (b.get("col") is not None and b.get("row") is None) else None
        only_r = b.get("row") if (b.get("row") is not None and b.get("col") is None) else None
        row_limit = MAX_AUTO_ROWS if rows_auto else len(rws)
        # 範囲外の col / row / row_span は、探索に入る前に fail にする（どの行にも置けないまま行を足し続けないため）
        if only_c is not None and only_c + cs > nc:
            problems.append(f"{label(k)}: col={only_c}・col_span={cs} が列の数（{nc}）を超えています"
                            f" → col を 0〜{nc - cs} にする（列は 0 から数える）か columns を増やす")
            continue
        if rs > row_limit:
            problems.append(f"{label(k)}: row_span={rs} が行の数（{row_limit}{'。自動で増やせる上限' if rows_auto else ''}）を超えています"
                            f" → row_span を {row_limit} 以下にする" + ("" if rows_auto else "か rows を増やす"))
            continue
        if only_r is not None and only_r + rs > row_limit:
            if rows_auto:
                problems.append(f"{label(k)}: row={only_r}・row_span={rs} は大きすぎます（行は自動で最大 {MAX_AUTO_ROWS} 行まで）"
                                f" → row を 0〜{MAX_AUTO_ROWS - rs} にする（行は 0 から数える）。それ以上の行が要るなら 2 枚に分ける")
            else:
                problems.append(f"{label(k)}: row={only_r}・row_span={rs} が行の数（{len(rws)}）を超えています"
                                f" → row を 0〜{len(rws) - rs} にするか rows を増やす")
            continue
        placed = False
        r = cur_r
        while True:
            if r + rs > len(rws):
                if rows_auto and r + rs <= MAX_AUTO_ROWS:
                    rws += [1.0] * (r + rs - len(rws))
                else:
                    break
            if only_r is not None and r != only_r:
                if r > only_r:
                    break
                r += 1
                continue
            for c in range(0, nc - cs + 1):
                if only_c is not None and c != only_c:
                    continue
                if only_r is None and only_c is None and (r, c) < (cur_r, cur_c):
                    continue
                a = area(c, r, cs, rs)
                if not (a & occupied):
                    occupied |= a
                    cells[k] = (c, r, cs, rs)
                    placed = True
                    if only_r is None and only_c is None:
                        cur_r, cur_c = r, c + cs
                        if cur_c >= nc:
                            cur_r, cur_c = r + 1, 0
                    break
            if placed:
                break
            r += 1
            if r > row_limit:
                break
        if not placed:
            if rows_auto:
                fix = (f"自動で増やせる行は最大 {MAX_AUTO_ROWS} 行です → ブロックを減らして 2 枚に分ける"
                       f"（または columns を増やす、col / row の指定を見直す）")
            elif preset is not None and not rows_user:
                fix = (f"arrange '{arrange}' は {nc} 列 × {len(rws)} 行です → arrange を外す（行は自動で足される）か、"
                       f"rows を書く（例: \"rows\": {[1] * (len(rws) + 1)}）。columns を増やしてもよい")
            else:
                fix = "rows を増やすか、columns を増やす（または rows を省略して自動で増やす）"
            problems.append(f"{label(k)}: 置ける場所がありません（格子は {nc} 列 × {len(rws)} 行）→ {fix}")
    if not problems and preset is None and not cols_user and rows_auto:
        # columns も arrange も書かないとき、最後の行に余りが出たら、その行の最後のブロックを余りの分だけ広げる（5 個・7 個の空きを作らない）
        _widen_last_row(blocks, cells, occupied, nc, len(rws))
    empty = [(c, r) for r in range(len(rws)) for c in range(nc) if (c, r) not in occupied] if not problems else []
    return {"columns": cols, "rows": rws, "cells": cells, "empty": empty, "problems": problems}


def _widen_last_row(blocks: list, cells: list, occupied: set, nc: int, nrows: int):
    """最後の行の右側が空いていて、その行の右端のブロックが自動配置（col / row / col_span を書いていない）なら、空きの分だけ広げる。"""
    last = nrows - 1
    row_cells = [k for k, c in enumerate(cells) if c is not None and c[1] <= last < c[1] + c[3]]
    if not row_cells or any(c is None for c in cells):
        return
    k = max(row_cells, key=lambda q: cells[q][0] + cells[q][2])
    c, r, cs, rs = cells[k]
    b = blocks[k]
    if not isinstance(b, dict) or any(b.get(key) is not None for key in ("col", "row", "col_span", "row_span")):
        return
    free = [x for x in range(c + cs, nc) if (x, r) not in occupied]
    if r != last or not free or free != list(range(c + cs, nc)):
        return
    for x in free:
        occupied.add((x, r))
    cells[k] = (c, r, cs + len(free), rs)


def split_axis(total: float, ratios: list, gap: float) -> list:
    """全長 total を比率で分ける。戻り値 [(開始, 長さ)]（gap を挟む）。"""
    n = len(ratios)
    room = max(total - gap * (n - 1), 1.0)
    s = sum(ratios)
    out, pos = [], 0.0
    for k, r in enumerate(ratios):
        ln = room * r / s
        out.append((pos, ln))
        pos += ln + gap
    return out


def grid_rects(body: dict, plan: dict, gap_x: float, gap_y: float) -> list:
    """ブロックごとの矩形 (x, y, w, h)。span したブロックは、またがる格子の間隔も含めた矩形になる。"""
    xs = split_axis(body["w"], plan["columns"], gap_x)
    ys = split_axis(body["h"], plan["rows"], gap_y)
    out = []
    for cell in plan["cells"]:
        if cell is None:
            out.append(None)
            continue
        c, r, cs, rs = cell
        x0 = body["x"] + xs[c][0]
        x1 = body["x"] + xs[c + cs - 1][0] + xs[c + cs - 1][1]
        y0 = body["y"] + ys[r][0]
        y1 = body["y"] + ys[r + rs - 1][0] + ys[r + rs - 1][1]
        out.append((round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)))
    return out


# ---------------------------------------------------------------------------
# 枠と小見出し
# ---------------------------------------------------------------------------

def frame_of(block: dict) -> str:
    f = block.get("frame")
    if block.get("emphasis"):
        return "box"                      # 強調は塗りの箱で見せる
    return f if f in FRAMES else "none"


def frame_geometry(rect, block: dict, bk: dict, heading_fit: dict | None = None) -> dict:
    """矩形から、枠・小見出しを引いた内容の矩形を決める。bk = st["block"]（default.json の types.composite.block）。
    小見出しの位置は枠の種類によらず、枠なし（none）と同じ高さ（ブロックの上端）にそろう。
    frame none: 小見出し + 細い下線 / box: 塗りの箱（内側に余白 pad）/ line: 小見出し + アクセント色の太い下線
    （小見出しが無いときは左端に縦線）。戻り値 {"frame", "outer", "content", "heading": (x, y, w, h) | None, "heading_size", "pad", "left_line"}"""
    x, y, w, h = rect
    frame = frame_of(block)
    has_h = bool(block.get("heading"))
    pad = bk.get("pad", 18) if frame == "box" else 0
    left_line = bk.get("line_w", 3) if frame == "line" and not has_h else 0
    inset_l = pad + (left_line + bk.get("line_gap", 14) if left_line else 0)
    ix, iy, iw, ih = x + inset_l, y + pad, w - inset_l - pad, h - 2 * pad
    heading = None
    hsize = (heading_fit or {}).get("size", bk.get("heading_size", 18))
    under_w = 0
    if has_h:
        hh = (heading_fit or {}).get("h", round(hsize * 1.3, 2))
        under_w = bk.get("line_w", 3) if frame == "line" else (bk.get("rule_w", 1) if frame == "none" else 0)
        under = (bk.get("rule_gap", 8) + under_w) if under_w else 0
        heading = (ix, iy, iw, hh)
        used = hh + under + bk.get("heading_gap", 12)
        iy, ih = iy + used, ih - used
    return {"frame": frame, "outer": (x, y, w, h), "content": (ix, iy, max(iw, 1.0), max(ih, 1.0)),
            "heading": heading, "heading_size": hsize, "pad": pad, "under_w": under_w, "left_line": left_line}


def fit_heading(text: str, width: float, bk: dict) -> dict:
    """小見出しを 1 行に収める文字サイズ。下限でも収まらなければ fits=False。"""
    cap = bk.get("heading_size", 18)
    floor = min(bk.get("heading_min_size", 14), cap)
    lh = 1.2
    res = autofit.fit_text_size(text, width, cap * lh * 1.02, cap, floor, lh, heading=True, bold=True)
    return {"size": res["size"], "fits": res["fits"], "lines": res["lines"], "h": round(res["size"] * 1.3, 2), "cap": cap}


def frame_elements(ctx: pe.Ctx, geo: dict, block: dict, bk: dict, shadow=None, radius: float = 0) -> list:
    """枠と小見出しの canvas 要素（HTML と PPTX で同じ形になる）。"""
    x, y, w, h = geo["outer"]
    els = []
    emph = bool(block.get("emphasis"))
    name = f"ブロック{block.get('_index', 0) + 1}"
    frame = geo["frame"]
    if frame == "box":
        fill = bk.get("emphasis_fill", "primary") if emph else bk.get("fill", "surface")
        line = None if emph else bk.get("border_color", "border")
        els.append(ctx.box(x, y, w, h, fill=fill, line=line, line_w=bk.get("border_w", 1), radius=radius or None,
                           shadow=shadow, name=f"{name}の枠"))
    elif frame == "line" and geo["left_line"]:
        els.append(ctx.box(x, y, geo["left_line"], h, fill=bk.get("line_color", "accent"), name=f"{name}の線"))
    if geo["heading"]:
        hx, hy, hw, hh = geo["heading"]
        color = bk.get("emphasis_color", "on_primary") if emph else bk.get("heading_color", "primary")
        els.append(ctx.box(hx, hy, hw, hh, anchor="ctr",
                           paras=[ctx.para(block["heading"], geo["heading_size"], color, bold=True, head=True, lh=1.0)],
                           name=f"{name}の小見出し"))
        if geo["under_w"]:
            ry = hy + hh + bk.get("rule_gap", 8)
            rc = bk.get("line_color", "accent") if frame == "line" else bk.get("rule_color", "border")
            els.append(ctx.box(hx, ry, hw, geo["under_w"], fill=rc, name=f"{name}の小見出し線"))
    return els


# ---------------------------------------------------------------------------
# 合成専用ブロック: text / callout / image
# ---------------------------------------------------------------------------

def text_paragraphs(block: dict) -> list:
    """text ブロックの段落（文字列の配列）。text は改行で段落を分け、paragraphs は配列の各要素が段落。"""
    out = []
    if isinstance(block.get("paragraphs"), list):
        out += [str(p) for p in block["paragraphs"] if p is not None and str(p).strip()]
    t = block.get("text")
    if isinstance(t, str) and t.strip():
        out = [s for s in (q.strip() for q in t.split("\n")) if s] + out
    return out


def _para_height(texts: list, size: float, width: float, gap: float, lh: float, bold=False, head=False) -> float:
    total = 0.0
    for s in texts:
        n = ja_text.estimate_lines(s, size, max(width, 10), font=ja_text.heading_fonts() if head else None, bold=bold)
        total += n * size * pe.LINE_H * lh
    return total + gap * max(len(texts) - 1, 0)


def fit_text_block(block: dict, content, tx: dict) -> dict:
    """text ブロックの文字サイズ。tx = st["text"]（size 上限・min_size・line_height・gap）。
    戻り値 {"size", "fits", "need", "avail", "paras"}。収まる最大のサイズを 1px 刻みで探す。"""
    x, y, w, h = content
    paras = text_paragraphs(block)
    cap = tx.get("size", 20)
    floor = min(tx.get("min_size", 14), cap)
    lh = tx.get("line_height", 1.5)
    gap_k = tx.get("para_gap", 0.6)
    size = cap
    while True:
        need = _para_height(paras, size, w, gap_k * size, lh)
        if need <= h + 0.5 or size <= floor:
            break
        size -= 1
    out = {"size": size, "fits": need <= h + 0.5, "need": round(need, 1), "avail": round(h, 1), "paras": paras, "cap": cap}
    gp = autofit.thin_grow_params(tx) if not tx.get("_size_fixed") else None
    if autofit.thin_participates(tx) and not tx.get("_size_fixed"):
        out["thin_factor"] = 1.0
    if gp and out["fits"] and size >= cap and h > 0 and need < h * gp[2]:
        grow, mx, trig = gp
        base_prof = [autofit.wrap_profile(t, size, max(w, 10)) for t in paras]          # いまの折り返し
        for s_ in range(int(min(cap * grow, mx)), int(cap), -1):
            nd = _para_height(paras, s_, w, gap_k * s_, lh)
            # 折り返しが増える・語の途中で折れる・最終行が 1〜2 字になる大きさには上げない（s4-C-06）
            if nd <= h * trig + 0.5 and all(autofit.wrap_not_worse(a, autofit.wrap_profile(t, s_, max(w * sf, 10)))
                                            for sf in autofit.WRAP_CHECK_SAFETIES for a, t in zip(base_prof, paras)):
                out.update({"size": s_, "need": round(nd, 1), "thin_factor": round(s_ / cap, 3)})
                break
    return out


def text_elements(ctx: pe.Ctx, content, block: dict, tx: dict, fit: dict, emph: bool = False) -> list:
    x, y, w, h = content
    color = tx.get("emphasis_color", "on_primary") if emph else tx.get("color", "text")
    size = fit["size"]
    lh = tx.get("line_height", 1.5)
    paras = [ctx.para(s, size, color, align=_al(block), after=tx.get("para_gap", 0.6) * size if i < len(fit["paras"]) - 1 else 0, lh=lh)
             for i, s in enumerate(fit["paras"])]
    anchor = {"top": "t", "middle": "ctr", "bottom": "b"}.get(block.get("valign") or tx.get("valign", "top"), "t")
    return [ctx.box(x, y, w, h, paras=paras, anchor=anchor, name=f"ブロック{block.get('_index', 0) + 1}の文")]


def _al(block: dict) -> str:
    return {"left": "l", "center": "ctr", "right": "r"}.get(block.get("align") or "left", "l")


def fit_callout(block: dict, content, co: dict) -> dict:
    """callout の文字サイズ。強調の一文（text）を主役に、補足（note）を小さく下に置く。
    戻り値 {"size", "note_size", "fits", "need", "avail", "bar_w"}"""
    x, y, w, h = content
    bar_w = co.get("bar_w", 5)
    tw = w - bar_w - co.get("bar_gap", 16)
    cap = co.get("size", 28)
    floor = min(co.get("min_size", 17), cap)
    ratio = co.get("note_ratio", 0.62)
    lh = co.get("line_height", 1.4)
    gap_k = co.get("note_gap", 0.5)
    main, note = str(block.get("text") or ""), str(block.get("note") or "")
    size = cap
    while True:
        nsz = max(round(size * ratio), co.get("note_min_size", 14))
        need = _para_height([main], size, tw, 0, lh, bold=True, head=True)
        if note:
            need += gap_k * size + _para_height([n for n in note.split("\n") if n.strip()], nsz, tw, nsz * 0.3, 1.45)
        if need <= h + 0.5 or size <= floor:
            break
        size -= 1
    nsz = max(round(size * ratio), co.get("note_min_size", 14))
    out = {"size": size, "note_size": nsz, "fits": need <= h + 0.5, "need": round(need, 1), "avail": round(h, 1),
           "bar_w": bar_w, "tw": tw, "cap": cap}
    gp = autofit.thin_grow_params(co) if not co.get("_size_fixed") else None
    if autofit.thin_participates(co) and not co.get("_size_fixed"):
        out["thin_factor"] = 1.0
    if gp and out["fits"] and size >= cap and h > 0 and need < h * gp[2]:
        grow, mx, trig = gp
        hf = ja_text.heading_fonts()
        note_lines = [n for n in note.split("\n") if n.strip()]
        base_main = autofit.wrap_profile(main, size, max(tw, 10), hf, True)             # いまの折り返し
        nsz0 = max(round(size * ratio), co.get("note_min_size", 14))
        base_notes = [autofit.wrap_profile(n, nsz0, max(tw, 10)) for n in note_lines]
        for s_ in range(int(min(cap * grow, mx)), int(cap), -1):
            ns = max(round(s_ * ratio), co.get("note_min_size", 14))
            nd = _para_height([main], s_, tw, 0, lh, bold=True, head=True)
            if note:
                nd += gap_k * s_ + _para_height(note_lines, ns, tw, ns * 0.3, 1.45)
            # 強調文・補足とも、折り返しが増える・語の途中で折れる・最終行が 1〜2 字になる大きさには上げない（s4-C-06。「（月）」だけの最終行など）
            if nd <= h * trig + 0.5 and all(autofit.wrap_not_worse(base_main, autofit.wrap_profile(main, s_, max(tw * sf, 10), hf, True))
                                            and all(autofit.wrap_not_worse(a, autofit.wrap_profile(n, ns, max(tw * sf, 10))) for a, n in zip(base_notes, note_lines))
                                            for sf in autofit.WRAP_CHECK_SAFETIES):
                out.update({"size": s_, "note_size": ns, "need": round(nd, 1), "thin_factor": round(s_ / cap, 3)})
                break
    return out


def callout_elements(ctx: pe.Ctx, content, block: dict, co: dict, fit: dict, emph: bool = False) -> list:
    x, y, w, h = content
    idx = block.get("_index", 0) + 1
    main, note = str(block.get("text") or ""), str(block.get("note") or "")
    # 強調（濃い箱）のときは縦帯を出さない（濃い箱の中に白い縦帯が残ると二重の強調に見える）。帯を出したいなら bar_on_emphasis に色を書く
    bar_color = co.get("bar_on_emphasis", "none") if emph else co.get("bar_color", "accent")
    if bar_color in (None, False, "", "none"):
        bar_color = None
    mcolor = co.get("emphasis_color", "on_primary") if emph else co.get("color", "heading_text")
    ncolor = co.get("emphasis_note_color", "on_primary") if emph else co.get("note_color", "muted")
    size, nsz = fit["size"], fit["note_size"]
    lh = co.get("line_height", 1.4)
    paras = [ctx.para(main, size, mcolor, bold=True, head=True, align=_al(block), lh=lh,
                      after=(co.get("note_gap", 0.5) * size) if note else 0)]
    for i, line in enumerate([n for n in note.split("\n") if n.strip()]):
        paras.append(ctx.para(line, nsz, ncolor, align=_al(block), lh=1.45, after=nsz * 0.3))
    # 文の高さを測り、箱の中で縦位置を決める（既定は中央。HTML と PPTX が同じ位置になるよう、アンカーではなく箱の高さで決める）
    anchor = {"top": "t", "middle": "ctr", "bottom": "b"}.get(block.get("valign") or co.get("valign", "middle"), "ctr")
    els = [ctx.box(x + fit["bar_w"] + co.get("bar_gap", 16), y, fit["tw"], h, paras=paras, anchor=anchor,
                   name=f"ブロック{idx}の強調文")]
    if bar_color is not None:
        els.insert(0, ctx.box(x, y, fit["bar_w"], h, fill=bar_color, name=f"ブロック{idx}の帯"))
    return els


def image_elements(ctx: pe.Ctx, block: dict, content, im: dict, radius: float = 0) -> list:
    """image ブロックの canvas 要素。画像は枠いっぱい（contain は余白が出る。cover は切り抜き）、キャプションは下に中央寄せ。"""
    x, y, w, h = content
    idx = block.get("_index", 0) + 1
    cap = str(block.get("caption") or "")
    cap_h = caption_height(block, im)
    fit = block.get("fit") if block.get("fit") in ("contain", "cover") else im.get("image_fit", "contain")
    el = {"kind": "image", "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(max(h - cap_h, 1), 2),
          "path": block.get("path"), "fit": fit, "name": f"ブロック{idx}の画像",
          "alt": str(block.get("alt") or block.get("caption") or block.get("heading") or "")}
    if radius and fit == "cover":
        el["radius"] = radius
    out = [el]
    if cap:
        csz = im.get("caption_size", 14)
        out.append(ctx.box(x, y + h - cap_h + im.get("caption_gap", 8), w, csz * 1.5, anchor="t",
                           paras=[ctx.para(cap, csz, im.get("caption_color", "muted"), align="ctr", lh=1.0)],
                           name=f"ブロック{idx}のキャプション"))
    return out


def caption_height(block: dict, im: dict) -> float:
    if not block.get("caption"):
        return 0.0
    return round(im.get("caption_size", 14) * 1.5 + im.get("caption_gap", 8), 2)

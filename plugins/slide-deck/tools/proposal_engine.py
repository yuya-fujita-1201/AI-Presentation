#!/usr/bin/env python3
"""提案書向けスライドタイプのレイアウトエンジン。

summary / reasons / statement / row_matrix / org と、どのタイプにも付けられる共通パーツ
（下端の結論帯 conclusion・出典の行 source）の配置を計算し、canvas 型と同じ要素列
（canvas_engine の shape / text）にして返す。描画は canvas_engine が担うので、HTML と PPTX の
両方で同じ図形（PowerPoint では1つずつ編集できるネイティブ図形）になる。

色はテーマトークン（primary / surface など）で受け取り、ここで #RRGGBB に解決する。
文字の大きさは ja_text の実測字幅で行数を見積もり、枠に収まる最大のサイズを選ぶ。
"""
from __future__ import annotations

import ja_text

PROPOSAL_TYPES = ("summary", "reasons", "statement", "row_matrix", "org")
LINE_H = 1.2          # canvas_engine.LINE_HEIGHT と同じ（行の高さ = 文字サイズ × 1.2 × lineHeight）
PARA_LH = 1.15        # 本文段落の行間（lineHeight）


class Ctx:
    """テーマ（色・フォント）を持ち回し、トークン→hex の解決と文字要素の生成を受け持つ。"""

    def __init__(self, theme: dict):
        self.colors = theme.get("colors", {})
        fonts = theme.get("fonts", {})
        self.body_font = ja_text._names(fonts.get("body")) or ["Meiryo UI"]
        self.head_font = ja_text._names(fonts.get("heading")) or self.body_font

    def c(self, token, default="#000000") -> str:
        v = token if isinstance(token, str) else default
        if v.startswith("#") and len(v) == 7:
            return v.upper()
        v = self.colors.get(v, default)
        if isinstance(v, str) and v.startswith("#") and len(v) == 4:
            v = "#" + "".join(ch * 2 for ch in v[1:])
        return v.upper() if isinstance(v, str) and v.startswith("#") and len(v) == 7 else default

    # --- 要素の生成 ---------------------------------------------------------
    def run(self, text, size, color, bold=False, head=False):
        return {"text": str(text), "size": round(size, 2), "color": self.c(color), "bold": bool(bold),
                "font": list(self.head_font if head else self.body_font)}

    def para(self, text, size, color, bold=False, head=False, align="l", bullet=None, after=0.0, lh=PARA_LH):
        p = {"align": align, "lineHeight": lh, "runs": [self.run(text, size, color, bold, head)]}
        if after:
            p["spaceAfter"] = round(after, 2)
        if bullet:
            ind = round(size * 1.0, 2)
            p.update({"marL": ind, "indent": -ind,
                      "bullet": {"char": bullet, "color": self.c(color), "size": size, "font": list(self.body_font)}})
        return p

    def box(self, x, y, w, h, fill=None, line=None, geom="rect", paras=None, anchor="t", insets=(0, 0, 0, 0),
            adj=None, dash=None, line_w=0.75, name=None):
        el = {"kind": "shape", "geom": geom, "x": round(x, 2), "y": round(y, 2), "w": round(max(w, 0), 2),
              "h": round(max(h, 0), 2)}
        if fill:
            el["fill"] = self.c(fill)
        if line:
            el["line"] = {"color": self.c(line), "width": line_w}
            if dash:
                el["line"]["dash"] = dash
        if adj:
            el["adj"] = adj
        if paras:
            el["text"] = {"insets": [round(v, 2) for v in insets], "anchor": anchor, "paragraphs": paras}
        if name:
            el["name"] = name
        return el

    def tri_right(self, x, y, w, h, fill, name=None):
        """右向きの三角（ゾーンの間の流れ・因果を示す灰色の三角）"""
        el = {"kind": "shape", "geom": "custom", "x": round(x, 2), "y": round(y, 2), "w": round(w, 2),
              "h": round(h, 2), "fill": self.c(fill),
              "path": [{"cmds": [["M", 0, 0], ["L", round(w, 2), round(h / 2, 2)], ["L", 0, round(h, 2)], ["Z"]],
                        "fill": True, "stroke": False}]}
        if name:
            el["name"] = name
        return el

    def tri_down(self, x, y, w, h, fill, name=None):
        el = self.tri_right(x, y, w, h, fill, name)
        el["path"][0]["cmds"] = [["M", 0, 0], ["L", round(w, 2), 0], ["L", round(w / 2, 2), round(h, 2)], ["Z"]]
        return el

    def path(self, pts, color, width=1.0, dash=None, arrow=False):
        """折れ線（ネイティブの自由曲線。arrow=True なら終点に矢じりを付けた直線コネクタにする）"""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, y0 = min(xs), min(ys)
        w, h = max(max(xs) - x0, 0.01), max(max(ys) - y0, 0.01)
        line = {"color": self.c(color), "width": width}
        if dash:
            line["dash"] = dash
        if arrow and len(pts) == 2:
            (ax, ay), (bx, by) = pts
            el = {"kind": "shape", "geom": "straightConnector1", "x": round(min(ax, bx), 2), "y": round(min(ay, by), 2),
                  "w": round(abs(bx - ax), 2), "h": round(abs(by - ay), 2), "line": dict(line, tail={"type": "triangle"})}
            if bx < ax:
                el["flipH"] = True
            if by < ay:
                el["flipV"] = True
            return el
        cmds = [["M", round(pts[0][0] - x0, 2), round(pts[0][1] - y0, 2)]]
        cmds += [["L", round(px - x0, 2), round(py - y0, 2)] for px, py in pts[1:]]
        return {"kind": "shape", "geom": "custom", "x": round(x0, 2), "y": round(y0, 2), "w": round(w, 2),
                "h": round(h, 2), "line": line, "path": [{"cmds": cmds, "fill": False, "stroke": True}]}


# ---------------------------------------------------------------------------
# 文字量の見積もり
# ---------------------------------------------------------------------------

def text_h(text, size, width, head=False, bold=False, lh=PARA_LH) -> float:
    font = ja_text.heading_fonts() if head else None
    return ja_text.estimate_lines(text, size, max(width, 10), font=font, bold=bold) * size * LINE_H * lh


def items_h(items, size, width, gap) -> float:
    return sum(text_h(t, size, width - size) + gap for t in items)


def as_items(v) -> list:
    """文字列 / 配列 / {text, items} を「本文 + 箇条書き」の (text, items) にそろえる。"""
    if v is None:
        return "", []
    if isinstance(v, str):
        return v, []
    if isinstance(v, list):
        return "", [str(x) for x in v]
    if isinstance(v, dict):
        return str(v.get("text", "")), [str(x) for x in v.get("items", []) or []]
    return str(v), []


# ---------------------------------------------------------------------------
# 本文領域と共通パーツ（結論帯・出典）
# ---------------------------------------------------------------------------

def body_region(slide: dict, st: dict) -> dict:
    """本文を描ける矩形。lead が無ければ上に詰め、結論帯・出典の分を下から差し引く。"""
    b = dict(st.get("body", {"x": 72, "y": 192, "w": 1136, "h": 452}))
    if not slide.get("lead") and "y_no_lead" in b:
        bottom = b["y"] + b["h"]
        b["y"] = b["y_no_lead"]
        b["h"] = bottom - b["y"]
    cb = st.get("conclusion", {})
    if slide.get("conclusion"):
        b["h"] -= cb.get("h", 40) + cb.get("gap", 12)
    if slide.get("source"):
        b["h"] -= st.get("source", {}).get("reserve", 20)
    return b


def common_parts(slide: dict, st: dict, ctx: Ctx, body: dict) -> list:
    """下端の結論帯（conclusion）と出典の行（source）。"""
    out = []
    if slide.get("conclusion"):
        cb = st.get("conclusion", {})
        y = body["y"] + body["h"] + cb.get("gap", 12)
        out.append(ctx.box(body["x"], y, body["w"], cb.get("h", 40), fill=cb.get("fill", "primary"),
                           paras=[ctx.para(slide["conclusion"], cb.get("size", 17), cb.get("color", "on_primary"),
                                           bold=True, head=True, align="ctr")],
                           anchor="ctr", insets=(16, 2, 16, 2), name="結論"))
    if slide.get("source"):
        sr = st.get("source", {})
        y = body["y"] + body["h"] + (st.get("conclusion", {}).get("h", 40) + st.get("conclusion", {}).get("gap", 12)
                                     if slide.get("conclusion") else 0) + 4
        out.append(ctx.box(body["x"], y, body["w"], sr.get("h", 18),
                           paras=[ctx.para(slide["source"], sr.get("size", 12), sr.get("color", "muted"), lh=1.0)],
                           anchor="t", name="出典"))
    return out


def _fit(candidates, need) -> tuple:
    """need(sizes) が True を返す最初の候補（大きい順に並べる）。どれも収まらなければ最後の候補。"""
    for s in candidates:
        if need(s):
            return s
    return candidates[-1]


# ---------------------------------------------------------------------------
# summary — 番号の箱＋要点＋説明の行（要旨・エグゼクティブサマリー）
# ---------------------------------------------------------------------------

def layout_summary(slide, st, ctx, body):
    g = st.get("body", {})
    items = [it if isinstance(it, dict) else {"lead": str(it)} for it in slide.get("items", [])]
    n = max(len(items), 1)
    gap = g.get("gap", 10)
    num_w = g.get("num_w", 64)
    pad = g.get("pad", 18)
    row_h = (body["h"] - gap * (n - 1)) / n
    tw = body["w"] - num_w - 2 * pad

    def fits(sz):
        ls, ts = sz
        return all(text_h(it.get("lead", ""), ls, tw, head=True, bold=True)
                   + (text_h(it["text"], ts, tw) + 4 if it.get("text") else 0) + 8 <= row_h for it in items)

    ls, ts = _fit(g.get("sizes", [(20, 16), (19, 15), (18, 14), (16, 13), (15, 12)]), fits)
    out = []
    for i, it in enumerate(items):
        y = body["y"] + i * (row_h + gap)
        out.append(ctx.box(body["x"], y, num_w, row_h, fill=g.get("num_fill", "primary"),
                           paras=[ctx.para(str(i + 1), g.get("num_size", 26), g.get("num_color", "on_primary"),
                                           bold=True, head=True, align="ctr", lh=1.0)],
                           anchor="ctr", name=f"番号{i + 1}"))
        paras = [ctx.para(it.get("lead", ""), ls, g.get("lead_color", "heading_text"), bold=True, head=True,
                          after=4 if it.get("text") else 0)]
        if it.get("text"):
            paras.append(ctx.para(it["text"], ts, g.get("text_color", "text")))
        out.append(ctx.box(body["x"] + num_w, y, body["w"] - num_w, row_h, fill=g.get("band_fill", "surface"),
                           paras=paras, anchor="ctr", insets=(pad, 4, pad, 4), name=f"要点{i + 1}"))
    return out


# ---------------------------------------------------------------------------
# reasons — 課題（番号）× 強み（a/b/c）の対応（選ばれる理由）
# ---------------------------------------------------------------------------

def layout_reasons(slide, st, ctx, body):
    g = st.get("body", {})
    issues = slide.get("issues", [])
    strengths = slide.get("strengths", [])
    n = max(len(issues), len(strengths), 1)
    head_h = g.get("head_h", 36)
    gap = g.get("gap", 10)
    tri_w = g.get("tri_w", 30)
    lw = body["w"] * g.get("left_ratio", 0.32)
    rx = body["x"] + lw + tri_w
    rw = body["x"] + body["w"] - rx
    out = [
        ctx.box(body["x"], body["y"], lw, head_h, fill=g.get("head_fill", "primary"),
                paras=[ctx.para(slide.get("left_heading", "貴社の課題"), g.get("head_size", 16),
                                g.get("head_color", "on_primary"), bold=True, head=True, align="ctr", lh=1.0)],
                anchor="ctr", name="課題の見出し"),
        ctx.box(rx, body["y"], rw, head_h, fill=g.get("head_fill", "primary"),
                paras=[ctx.para(slide.get("right_heading", "選ばれる理由"), g.get("head_size", 16),
                                g.get("head_color", "on_primary"), bold=True, head=True, align="ctr", lh=1.0)],
                anchor="ctr", name="強みの見出し"),
    ]
    top = body["y"] + head_h + gap
    row_h = (body["y"] + body["h"] - top - gap * (n - 1)) / n
    badge = g.get("badge_w", 34)
    pad = g.get("pad", 12)

    def need(sz):
        ts, bs = sz
        for k in range(n):
            iss = issues[k] if k < len(issues) else {}
            s = strengths[k] if k < len(strengths) else {}
            iss = iss if isinstance(iss, dict) else {"title": str(iss)}
            s = s if isinstance(s, dict) else {"title": str(s)}
            hl = text_h(iss.get("title", ""), ts, lw - badge - 2 * pad, head=True, bold=True) + \
                (text_h(iss.get("text", ""), bs, lw - badge - 2 * pad) if iss.get("text") else 0)
            _, its = as_items(s.get("items"))
            hr = text_h(s.get("title", ""), ts, rw - badge - 2 * pad, head=True, bold=True) + \
                (text_h(s.get("text", ""), bs, rw - badge - 2 * pad) if s.get("text") else 0) + \
                items_h(its, bs, rw - badge - 2 * pad, 2)
            if max(hl, hr) + 2 * pad > row_h:
                return False
        return True

    ts, bs = _fit(g.get("sizes", [(17, 14), (16, 13), (15, 12), (14, 12)]), need)
    for k in range(n):
        y = top + k * (row_h + gap)
        iss = issues[k] if k < len(issues) else None
        s = strengths[k] if k < len(strengths) else None
        if iss is not None:
            iss = iss if isinstance(iss, dict) else {"title": str(iss)}
            out.append(ctx.box(body["x"], y, lw, row_h, fill=g.get("issue_fill", "surface"), name=f"課題{k + 1}"))
            out.append(ctx.box(body["x"] + pad, y + row_h / 2 - (badge - 8) / 2, badge - 8, badge - 8, geom="ellipse",
                               fill=g.get("num_fill", "primary"),
                               paras=[ctx.para(str(k + 1), 14, g.get("num_color", "on_primary"), bold=True,
                                               align="ctr", lh=1.0)], anchor="ctr", name=f"課題番号{k + 1}"))
            paras = [ctx.para(iss.get("title", ""), ts, g.get("title_color", "heading_text"), bold=True, head=True,
                              after=3 if iss.get("text") else 0)]
            if iss.get("text"):
                paras.append(ctx.para(iss["text"], bs, g.get("text_color", "text")))
            out.append(ctx.box(body["x"] + badge + pad, y, lw - badge - 2 * pad, row_h, paras=paras, anchor="ctr",
                               insets=(0, pad / 2, 0, pad / 2), name=f"課題本文{k + 1}"))
            # 課題 → 強み の灰色の三角
            out.append(ctx.tri_right(body["x"] + lw + 6, y + row_h / 2 - 12, tri_w - 12, 24,
                                     g.get("tri_fill", "border"), name=f"対応{k + 1}"))
        if s is not None:
            s = s if isinstance(s, dict) else {"title": str(s)}
            label = s.get("label") or "abcdefghij"[k]
            out.append(ctx.box(rx, y, rw, row_h, fill="background", line=g.get("border_color", "border"),
                               name=f"強み{k + 1}"))
            out.append(ctx.box(rx, y, badge, row_h, fill=g.get("badge_fill", "accent"),
                               paras=[ctx.para(label, 16, g.get("badge_color", "on_primary"), bold=True,
                                               head=True, align="ctr", lh=1.0)], anchor="ctr",
                               name=f"強み記号{k + 1}"))
            _, its = as_items(s.get("items"))
            paras = [ctx.para(s.get("title", ""), ts, g.get("title_color", "heading_text"), bold=True, head=True,
                              after=3 if (s.get("text") or its) else 0)]
            if s.get("text"):
                paras.append(ctx.para(s["text"], bs, g.get("text_color", "text"), after=2 if its else 0))
            paras += [ctx.para(t, bs, g.get("item_color", "muted"), bullet="•", after=1) for t in its]
            out.append(ctx.box(rx + badge, y, rw - badge, row_h, paras=paras, anchor="ctr",
                               insets=(pad, pad / 2, pad, pad / 2), name=f"強み本文{k + 1}"))
    return out


# ---------------------------------------------------------------------------
# statement — 濃色の面に大きな一文（物語の転換点の言い切り）
# ---------------------------------------------------------------------------

def layout_statement(slide, st, ctx, body=None):
    bg = st.get("background", {})
    out = [ctx.box(0, 0, 1280, 720, fill=bg.get("fill", "primary"), name="背景")]
    k, m, s = st.get("kicker", {}), st.get("message", {}), st.get("support", {})
    msg = slide.get("message") or slide.get("title", "")
    size = _fit([m.get("size", 44), 40, 36, 32, 28],
                lambda sz: text_h(msg, sz, m.get("w", 1040), head=True, bold=True, lh=1.25) <= m.get("h", 220))
    if slide.get("kicker"):
        out.append(ctx.box(k.get("x", 120), k.get("y", 220), k.get("w", 1040), k.get("h", 32),
                           paras=[ctx.para(slide["kicker"], k.get("size", 20), k.get("color", "on_primary_muted"),
                                           bold=True, head=True, lh=1.0)], name="キッカー"))
        out.append(ctx.box(k.get("x", 120), k.get("y", 220) + k.get("h", 32) + 4, 64, 4,
                           fill=k.get("rule", "accent_on_primary"), name="区切り"))
    out.append(ctx.box(m.get("x", 120), m.get("y", 280), m.get("w", 1040), m.get("h", 220),
                       paras=[ctx.para(msg, size, m.get("color", "on_primary"), bold=True, head=True, lh=1.25)],
                       anchor="ctr", name="メッセージ"))
    if slide.get("support"):
        out.append(ctx.box(s.get("x", 120), s.get("y", 520), s.get("w", 1040), s.get("h", 80),
                           paras=[ctx.para(slide["support"], s.get("size", 20), s.get("color", "on_primary_soft"))],
                           name="補足"))
    return out


# ---------------------------------------------------------------------------
# row_matrix — 行見出し × 列の整理表（見出しを工程の矢印にもできる）
# ---------------------------------------------------------------------------

def layout_row_matrix(slide, st, ctx, body):
    g = st.get("body", {})
    cols = [c if isinstance(c, str) else str(c.get("text", "")) for c in slide.get("columns", [])] or [""]
    rows = slide.get("rows", [])
    nc = len(cols)
    has_head = any(cols)
    label_w = g.get("label_w", 170)
    head_h = g.get("head_h", 40) if has_head else 0
    gap = g.get("gap", 4)
    arrow = slide.get("header_style") == "arrow"
    emph = slide.get("emph_col")
    ratios = slide.get("col_ratios") or [1] * nc
    tot = sum(ratios) or 1
    cw_all = body["w"] - label_w - gap
    cws = [cw_all * r / tot for r in ratios]
    xs, x = [], body["x"] + label_w + gap
    for w in cws:
        xs.append(x)
        x += w
    out = []
    if has_head:
        if slide.get("corner"):
            out.append(ctx.box(body["x"], body["y"], label_w, head_h, fill=g.get("corner_fill", "surface"),
                               paras=[ctx.para(slide["corner"], g.get("head_size", 15), g.get("label_color", "heading_text"),
                                               bold=True, head=True, align="ctr", lh=1.0)], anchor="ctr", name="左上"))
        for j, c in enumerate(cols):
            if arrow:
                out.append(ctx.box(xs[j] + 2, body["y"], cws[j] - 4 + (14 if j < nc - 1 else 0), head_h,
                                   geom="homePlate" if j == 0 else "chevron", adj={"adj": 30000},
                                   fill=g.get("head_fill", "table_header_bg"),
                                   paras=[ctx.para(c, g.get("head_size", 15), g.get("head_color", "table_header_text"),
                                                   bold=True, head=True, align="ctr", lh=1.0)],
                                   anchor="ctr", insets=(16, 0, 8, 0), name=f"列見出し{j + 1}"))
            else:
                out.append(ctx.box(xs[j], body["y"], cws[j] - (gap if j < nc - 1 else 0), head_h,
                                   fill=g.get("head_fill", "table_header_bg"),
                                   paras=[ctx.para(c, g.get("head_size", 15), g.get("head_color", "table_header_text"),
                                                   bold=True, head=True, align="ctr", lh=1.0)],
                                   anchor="ctr", insets=(8, 0, 8, 0), name=f"列見出し{j + 1}"))
    top = body["y"] + head_h + (gap if has_head else 0)
    avail = body["y"] + body["h"] - top - gap * (len(rows) - 1)
    pad = g.get("pad", 10)

    def cell_need(cell, size, w):
        text, its = as_items(cell)
        return (text_h(text, size, w - 2 * pad) if text else 0) + items_h(its, size, w - 2 * pad, 2) + 2 * pad

    def heights(size):
        hs = []
        for r in rows:
            cells = r.get("cells", []) if isinstance(r, dict) else []
            need = max([cell_need(c, size, cws[j]) for j, c in enumerate(cells[:nc])] + [g.get("min_row_h", 44)])
            hs.append(need)
        return hs

    size = _fit(g.get("sizes", [16, 15, 14, 13, 12]), lambda s: sum(heights(s)) <= avail)
    hs = heights(size)
    extra = max(avail - sum(hs), 0) / max(len(rows), 1)
    hs = [h + extra for h in hs]
    y = top
    for i, r in enumerate(rows):
        r = r if isinstance(r, dict) else {"label": str(r)}
        h = hs[i]
        out.append(ctx.box(body["x"], y, label_w, h, fill=g.get("label_fill", "highlight_fill"),
                           paras=[ctx.para(r.get("label", ""), g.get("label_size", 15), g.get("label_color", "heading_text"),
                                           bold=True, head=True, align="ctr")],
                           anchor="ctr", insets=(8, 4, 8, 4), name=f"行見出し{i + 1}"))
        for j, cell in enumerate((r.get("cells") or [])[:nc]):
            text, its = as_items(cell)
            paras = []
            if text:
                paras.append(ctx.para(text, size, g.get("cell_color", "text"), after=3 if its else 0))
            paras += [ctx.para(t, size, g.get("cell_color", "text"), bullet="•", after=2) for t in its]
            fill = g.get("emph_fill", "surface") if emph is not None and j == emph else "background"
            out.append(ctx.box(xs[j], y, cws[j] - (gap if j < nc - 1 else 0), h, fill=fill,
                               line=g.get("border_color", "border"), paras=paras or None,
                               anchor=g.get("cell_anchor", "ctr"), insets=(pad, pad, pad, pad), name=f"セル{i + 1}-{j + 1}"))
        y += h + gap
    return out


# ---------------------------------------------------------------------------
# org — 体制図（左右の組織ツリー＋提案範囲の破線枠）
# ---------------------------------------------------------------------------

def _tree(nodes):
    """nodes（parent で親を指す）を、葉の並び順に x スロットを割り当てた階層にする。"""
    by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id")}
    kids = {i: [] for i in by_id}
    roots = []
    for n in by_id.values():
        p = n.get("parent")
        (kids[p] if p in kids else roots).append(n["id"])
    pos, depth = {}, {}
    slot = [0]

    def walk(i, d):
        depth[i] = d
        if not kids[i]:
            pos[i] = slot[0]
            slot[0] += 1
        else:
            for c in kids[i]:
                walk(c, d + 1)
            pos[i] = (pos[kids[i][0]] + pos[kids[i][-1]]) / 2
    for r in roots:
        walk(r, 0)
    return by_id, kids, pos, depth, max(slot[0], 1), (max(depth.values()) + 1 if depth else 1)


def layout_org(slide, st, ctx, body):
    g = st.get("body", {})
    sides = [s for s in (slide.get("left"), slide.get("right")) if isinstance(s, dict)]
    if not sides:
        return []
    gap_side = g.get("side_gap", 60)
    side_w = (body["w"] - gap_side * (len(sides) - 1)) / len(sides)
    title_h = g.get("side_title_h", 26)
    out, centers = [], {}
    for si, side in enumerate(sides):
        sx = body["x"] + si * (side_w + gap_side)
        is_right = si == len(sides) - 1 and len(sides) == 2
        out.append(ctx.box(sx, body["y"], side_w, title_h,
                           paras=[ctx.para(side.get("title", ""), g.get("side_title_size", 16),
                                           g.get("side_title_color", "heading_text"), bold=True, head=True, lh=1.0)],
                           anchor="ctr", name=f"{side.get('title', '')}の見出し"))
        by_id, kids, pos, depth, leaves, levels = _tree(side.get("nodes", []))
        top = body["y"] + title_h + 10
        avail_h = body["y"] + body["h"] - top - 6
        level_gap = g.get("level_gap", 26)
        node_h = min(g.get("node_h", 64), (avail_h - level_gap * (levels - 1)) / levels)
        if levels > 1:
            # 階層が浅いときは段の間隔を広げ（最大 max_level_gap）、余りは上 1/3・下 2/3 に配って上寄りに置く
            level_gap = min(max(level_gap, (avail_h - levels * node_h) / (levels - 1) * 0.6),
                            g.get("max_level_gap", 70))
        used = levels * node_h + (levels - 1) * level_gap
        top += max(avail_h - used, 0) / 3
        slot_w = side_w / leaves
        node_w = min(g.get("node_w", 200), slot_w - g.get("node_gap", 14))
        head_h = min(g.get("node_head_h", 26), node_h * 0.45)
        hf = g.get("right_head_fill" if is_right else "left_head_fill", "primary" if is_right else "muted")
        for nid, n in by_id.items():
            cx = sx + (pos[nid] + 0.5) * slot_w
            y = top + depth[nid] * (node_h + level_gap)
            x = cx - node_w / 2
            centers[nid] = (cx, y, y + node_h, x, x + node_w)
            ts = _fit([14, 13, 12, 11], lambda s: text_h(n.get("title", ""), s, node_w - 12, bold=True) <= head_h)
            out.append(ctx.box(x, y, node_w, head_h, fill=n.get("fill", hf),
                               paras=[ctx.para(n.get("title", ""), ts, g.get("node_head_color", "on_primary"), bold=True,
                                               head=True, align="ctr", lh=1.0)], anchor="ctr", insets=(6, 0, 6, 0),
                               name=nid))
            body_lines = [str(n[k]) for k in ("name", "members") if n.get(k)]
            bs = _fit([13, 12, 11], lambda s: sum(text_h(t, s, node_w - 12) for t in body_lines) <= node_h - head_h - 4)
            out.append(ctx.box(x, y + head_h, node_w, node_h - head_h, fill="background",
                               line=g.get("border_color", "border"),
                               paras=[ctx.para(t, bs, g.get("node_text_color", "text"), align="ctr", lh=1.05)
                                      for t in body_lines] or None,
                               anchor="ctr", insets=(6, 2, 6, 2), name=f"{nid}の内容"))
        # 親子のカギ線
        for pid, cs in kids.items():
            if not cs:
                continue
            pcx, _, pb, _, _ = centers[pid]
            mid = pb + level_gap / 2
            out.append(ctx.path([(pcx, pb), (pcx, mid)], g.get("line_color", "muted"), 1.0))
            xs_c = [centers[c][0] for c in cs]
            if len(cs) > 1:
                out.append(ctx.path([(min(xs_c), mid), (max(xs_c), mid)], g.get("line_color", "muted"), 1.0))
            for c in cs:
                out.append(ctx.path([(centers[c][0], mid), (centers[c][0], centers[c][1])],
                                    g.get("line_color", "muted"), 1.0))
        if side.get("scope"):
            pad = 8
            out.append(ctx.box(sx - pad, body["y"] + title_h + 2, side_w + 2 * pad,
                               body["y"] + body["h"] - (body["y"] + title_h + 2), line=g.get("scope_color", "accent"),
                               dash="dash", line_w=1.5, name="提案範囲"))
            label = side["scope"] if isinstance(side["scope"], str) else "ご支援範囲"
            out.append(ctx.box(sx + side_w + pad - 110, body["y"] + body["h"] - 24, 110, 24,
                               fill=g.get("scope_color", "accent"),
                               paras=[ctx.para(label, 12, "on_primary", bold=True, align="ctr", lh=1.0)],
                               anchor="ctr", name="提案範囲の札"))
    # 組織をまたぐ連携線
    for ln in slide.get("links", []) or []:
        a, b = centers.get(ln.get("from")), centers.get(ln.get("to"))
        if not a or not b:
            continue
        ya = (a[1] + a[2]) / 2
        yb = (b[1] + b[2]) / 2
        ax = a[4] if a[0] < b[0] else a[3]
        bx = b[3] if a[0] < b[0] else b[4]
        midx = (ax + bx) / 2
        out.append(ctx.path([(ax, ya), (midx, ya), (midx, yb), (bx, yb)], g.get("link_color", "accent"), 1.25,
                            dash="dash"))
        if ln.get("label"):
            out.append(ctx.box(midx - 70, min(ya, yb) - 20, 140, 18,
                               paras=[ctx.para(ln["label"], 12, g.get("link_color", "accent"), bold=True, align="ctr",
                                               lh=1.0)], anchor="b", name="連携の名前"))
    if slide.get("legend"):
        out.append(ctx.box(body["x"], body["y"], body["w"], title_h,
                           paras=[ctx.para(slide["legend"], 12, "muted", align="r", lh=1.0)], anchor="ctr",
                           name="凡例"))
    return out


LAYOUTS = {
    "summary": layout_summary,
    "reasons": layout_reasons,
    "statement": layout_statement,
    "row_matrix": layout_row_matrix,
    "org": layout_org,
}


def layout(slide: dict, st: dict, theme: dict) -> list:
    """スライド1枚分の canvas 要素列（本文＋共通パーツ）。statement はクロムを持たない全面レイアウト。"""
    ctx = Ctx(theme)
    t = slide.get("type")
    if t == "statement":
        return layout_statement(slide, st, ctx)
    body = body_region(slide, st)
    return LAYOUTS[t](slide, st, ctx, body) + common_parts(slide, st, ctx, body)


def chrome_parts(slide: dict, st: dict, theme: dict) -> list:
    """既存タイプにも付ける共通パーツ（結論帯・出典）。本文の領域は st の主要領域の下端から求める。"""
    if not (slide.get("conclusion") or slide.get("source")):
        return []
    ctx = Ctx(theme)
    body = body_region(slide, st)
    return common_parts(slide, st, ctx, body)


def validate(slide: dict, i: int, fail, warn) -> None:
    """スキーマ的な誤りは fail、詰め込みすぎは warn。"""
    t = slide.get("type")
    where = f"{i + 1}枚目（type={t}）"
    if t == "summary":
        items = slide.get("items")
        if not isinstance(items, list) or not items:
            fail(f"{where}: items（[{{lead, text}}] の配列）が必要です")
        if len(items) > 6:
            warn(f"{where}: items が{len(items)}個あります（3〜6個が目安。多いと文字が小さくなる）")
    elif t == "reasons":
        if not isinstance(slide.get("issues"), list) or not isinstance(slide.get("strengths"), list):
            fail(f"{where}: issues と strengths（それぞれ配列）が必要です")
        n = max(len(slide["issues"]), len(slide["strengths"]))
        if n > 5:
            warn(f"{where}: 行が{n}行あります（3行前後が目安）")
    elif t == "statement":
        if not (slide.get("message") or slide.get("title")):
            fail(f"{where}: message（大きく見せる一文）が必要です")
    elif t == "row_matrix":
        rows = slide.get("rows")
        if not isinstance(rows, list) or not rows:
            fail(f"{where}: rows（[{{label, cells}}] の配列）が必要です")
        nc = len(slide.get("columns") or [""])
        for k, r in enumerate(rows):
            if isinstance(r, dict) and len(r.get("cells") or []) > nc:
                warn(f"{where}: rows[{k}] の cells が columns より多い（{len(r['cells'])} > {nc}）。余りは描かれません")
        if len(rows) > 7:
            warn(f"{where}: 行が{len(rows)}行あります（6行以内が目安）")
        ratios = slide.get("col_ratios")
        if ratios is not None and (not isinstance(ratios, list) or len(ratios) != nc):
            fail(f"{where}: col_ratios は columns と同じ数の数値の配列で指定してください")
    elif t == "org":
        sides = [s for s in (slide.get("left"), slide.get("right")) if isinstance(s, dict)]
        if not sides:
            fail(f"{where}: left か right（{{title, nodes}}）が必要です")
        ids = set()
        for s in sides:
            for n in s.get("nodes", []) or []:
                if not isinstance(n, dict) or not n.get("id"):
                    fail(f"{where}: nodes の各要素には id が必要です")
                if n["id"] in ids:
                    fail(f"{where}: node id '{n['id']}' が重複しています")
                ids.add(n["id"])
            for n in s.get("nodes", []) or []:
                if n.get("parent") and n["parent"] not in {m.get("id") for m in s.get("nodes", [])}:
                    fail(f"{where}: node '{n['id']}' の parent '{n['parent']}' が同じ側の nodes にありません")
        for ln in slide.get("links", []) or []:
            if ln.get("from") not in ids or ln.get("to") not in ids:
                fail(f"{where}: links の from / to '{ln.get('from')}' → '{ln.get('to')}' が nodes にありません")

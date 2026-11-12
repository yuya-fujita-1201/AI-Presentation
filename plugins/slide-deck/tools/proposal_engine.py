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

import engine_registry
import icon_engine as ie
import ja_text
import shape_engine as shp

PROPOSAL_TYPES = ("summary", "reasons", "statement", "row_matrix", "org", "house", "cycle", "kpi_tree")
LINE_H = 1.2          # canvas_engine.LINE_HEIGHT と同じ（行の高さ = 文字サイズ × 1.2 × lineHeight）
PARA_LH = 1.15        # 本文段落の行間（lineHeight）


class Ctx:
    """テーマ（色・フォント）を持ち回し、トークン→hex の解決と文字要素の生成を受け持つ。"""

    def __init__(self, theme: dict):
        self.colors = theme.get("colors", {})
        self.tokens = theme.get("tokens") or {}      # 形トークン（角丸・太さ・字間）。無ければ classic の値
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
    def radius(self, name="box", default=0) -> float:
        """形トークン radius.<name>（px）。classic の提案書系の箱は角丸なし（box = 0）。"""
        return shp.tok(self.tokens, "radius", name, default)

    def run(self, text, size, color, bold=False, head=False):
        r = {"text": str(text), "size": round(size, 2), "color": self.c(color), "bold": bool(bold),
             "font": list(self.head_font if head else self.body_font)}
        if bold:
            w = shp.tok(self.tokens, "weight", "heading" if head else "label", 700)
            if w != 700:
                r["weight"] = w                      # 600 以上は太字（PPTX）、数値は HTML の font-weight
            tr = shp.tok(self.tokens, "tracking", "heading", 0) if head else 0
            if tr:
                r["tracking"] = tr
        return r

    def para(self, text, size, color, bold=False, head=False, align="l", bullet=None, after=0.0, lh=PARA_LH):
        # 行送りは px の固定値でも持つ（lineHeightPx）。PPTX は spcPts になり、フォントの自然な行高さに
        # 左右されず HTML（size × 1.2 × lh）と同じ行送りになる（A3-01。倍率 spcPct だとフォントで 12〜30% 広がる）
        p = {"align": align, "lineHeight": lh, "lineHeightPx": round(size * LINE_H * lh, 2),
             "runs": [self.run(text, size, color, bold, head)]}
        if after:
            p["spaceAfter"] = round(after, 2)
        if bullet:
            ind = round(size * 1.0, 2)
            p.update({"marL": ind, "indent": -ind,
                      "bullet": {"char": bullet, "color": self.c(color), "size": size, "font": list(self.body_font)}})
        return p

    def box(self, x, y, w, h, fill=None, line=None, geom="rect", paras=None, anchor="t", insets=(0, 0, 0, 0),
            adj=None, dash=None, line_w=0.75, name=None, radius=None, shadow=None):
        if radius and geom == "rect" and not adj and w > 0 and h > 0:
            # 角丸（px）。roundRect の adj は短辺に対する比率（1/100000）
            geom, adj = "roundRect", {"adj": int(min(50000, radius / min(w, h) * 100000))}
        el = {"kind": "shape", "geom": geom, "x": round(x, 2), "y": round(y, 2), "w": round(max(w, 0), 2),
              "h": round(max(h, 0), 2)}
        if shadow:
            el["shadow"] = shadow
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

    def icon(self, spec, x, y, size, color="primary", name=None):
        """同梱アイコン（名前か概念語）を線の図形にする。見つからなければ None。"""
        return ie.element(spec, x, y, size, self.c(color), name)

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


def _text_w(ctx, text, size, bold=False) -> float:
    """1 行の文字列の幅（px）。字幅の実測（ja_text.char_em）の合計。"""
    return sum(ja_text.char_em(ch, ctx.body_font, bold) for ch in str(text)) * size


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

CONTENT_BOTTOM = 644   # 本文の下端（フッターの上）。結論帯・出典はここから上に積む


def reserve(slide: dict, st: dict) -> float:
    """結論帯・出典のために本文の下から空ける高さ（px）。"""
    r = 0.0
    if slide.get("conclusion"):
        cb = st.get("conclusion", {})
        r += cb.get("h", 40) + cb.get("gap", 12)
    if slide.get("source"):
        r += st.get("source", {}).get("reserve", 20)
    return r


def body_region(slide: dict, st: dict) -> dict:
    """本文を描ける矩形。lead が無ければ上に詰め、結論帯・出典の分を下から差し引く。"""
    b = dict(st.get("body", {"x": 72, "y": 192, "w": 1136, "h": 452}))
    if not slide.get("lead") and "y_no_lead" in b:
        bottom = b["y"] + b["h"]
        b["y"] = b["y_no_lead"]
        b["h"] = bottom - b["y"]
    b["h"] -= reserve(slide, st)
    return b


K_BEZIER = 0.5522847498


def corner_path(w: float, h: float, radii) -> list:
    """角ごとに半径が違う角丸四角の canvas 自由曲線（cmds）。radii = (左上, 右上, 右下, 左下)。"""
    tl, tr_, br, bl = [round(max(0.0, min(r, w / 2, h / 2)), 2) for r in radii]
    k = K_BEZIER
    c = lambda v: round(v, 2)
    cmds = [["M", tl, 0], ["L", c(w - tr_), 0]]
    if tr_:
        cmds.append(["C", c(w - tr_ + tr_ * k), 0, w, c(tr_ - tr_ * k), w, tr_])
    cmds.append(["L", w, c(h - br)])
    if br:
        cmds.append(["C", w, c(h - br + br * k), c(w - br + br * k), h, c(w - br), h])
    cmds.append(["L", bl, h])
    if bl:
        cmds.append(["C", c(bl - bl * k), h, 0, c(h - bl + bl * k), 0, c(h - bl)])
    cmds.append(["L", 0, tl])
    if tl:
        cmds.append(["C", 0, c(tl - tl * k), c(tl - tl * k), 0, tl, 0])
    cmds.append(["Z"])
    return cmds


def round_boxes(els: list, radius: float, skip_names=(), only_names=None) -> list:
    """塗りか枠のある四角に角丸をかける（形トークン radius.box。0 なら何もしない）。
    他の箱と辺で接している角（番号の帯と本文の帯、見出し帯と本体など）は、つながって見えるよう角を落とさない。
    小さい箱は短辺の半分まで。背景（ほぼ全面）・線・自由曲線・楕円は対象外。"""
    if not radius or radius <= 0:
        return els
    cand = []
    for i, e in enumerate(els):
        if e.get("kind", "shape") != "shape" or e.get("geom", "rect") != "rect" or e.get("path"):
            continue
        if not (e.get("fill") or e.get("line")) or e.get("name") in skip_names:
            continue
        if only_names is not None and e.get("name") not in only_names:
            continue
        if e["w"] >= 1200 and e["h"] >= 680:
            continue
        if min(e["w"], e["h"]) < 6:
            continue            # 細い帯・線は角丸にしない
        cand.append(i)
    tol = 0.75

    def inside(b, px, py):
        return b["x"] - tol <= px <= b["x"] + b["w"] + tol and b["y"] - tol <= py <= b["y"] + b["h"] + tol

    def touches(a, px, py, ix, iy):
        """(px, py)（角の外側）が別の箱の中にあり、かつその箱が a の角の内側（ix, iy）を覆っていない = 隣り合う箱"""
        for j in cand:
            if j != a and inside(els[j], px, py) and not inside(els[j], ix, iy):
                return True
        return False

    for i in cand:
        e = els[i]
        x, y, w, h = e["x"], e["y"], e["w"], e["h"]
        r = min(radius, w / 2, h / 2)
        # 角の少し外側（辺の延長上）に別の箱があれば、その角は直角のまま
        sq = (touches(i, x - 1.5, y + 1.5, x + 1.5, y + 1.5) or touches(i, x + 1.5, y - 1.5, x + 1.5, y + 1.5),                      # 左上
              touches(i, x + w + 1.5, y + 1.5, x + w - 1.5, y + 1.5) or touches(i, x + w - 1.5, y - 1.5, x + w - 1.5, y + 1.5),      # 右上
              touches(i, x + w + 1.5, y + h - 1.5, x + w - 1.5, y + h - 1.5) or touches(i, x + w - 1.5, y + h + 1.5, x + w - 1.5, y + h - 1.5),  # 右下
              touches(i, x - 1.5, y + h - 1.5, x + 1.5, y + h - 1.5) or touches(i, x + 1.5, y + h + 1.5, x + 1.5, y + h - 1.5))              # 左下
        radii = tuple(0 if q else r for q in sq)
        if not any(radii):
            continue
        if all(radii):
            e["geom"], e["adj"] = "roundRect", {"adj": int(min(50000, r / min(w, h) * 100000))}
        else:
            e["geom"] = "custom"
            e["path"] = [{"cmds": corner_path(w, h, radii), "fill": True, "stroke": True}]
    return els


def common_parts(slide: dict, st: dict, ctx: Ctx, body: dict) -> list:
    """下端の結論帯（conclusion）と出典の行（source）。body は結論帯の分を差し引いた本文の矩形。角は形トークン radius.box。"""
    out = _common_parts(slide, st, ctx, body)
    return round_boxes(out, ctx.radius("box"), only_names=("結論",))


def _common_parts(slide: dict, st: dict, ctx: Ctx, body: dict) -> list:
    out = []
    y = body["y"] + body["h"]
    if slide.get("conclusion"):
        cb = st.get("conclusion", {})
        y += cb.get("gap", 12)
        out.append(ctx.box(body["x"], y, body["w"], cb.get("h", 40), fill=cb.get("fill", "primary"),
                           paras=[ctx.para(slide["conclusion"], cb.get("size", 17), cb.get("color", "on_primary"),
                                           bold=True, head=True, align="ctr")],
                           anchor="ctr", insets=(16, 2, 16, 2), name="結論"))
        y += cb.get("h", 40)
    if slide.get("source"):
        sr = st.get("source", {})
        out.append(ctx.box(body["x"], y + 4, body["w"], sr.get("h", 18),
                           paras=[ctx.para(slide["source"], sr.get("size", 12), sr.get("color", "muted"), lh=1.0)],
                           anchor="t", name="出典"))
    return out


# 結論帯・出典を自分で描くタイプ（A 型の登録表のタイプと pattern。build_deck の extras / shrink_for_bottom の対象外にする。
# pattern は frame:"body" のとき build_deck が common_parts で結論帯・出典を描く。frame:"full" は型自身が描く）
OWN_PARTS_TYPES = {"pattern"}


def draws_own_parts(t) -> bool:
    return t in OWN_PARTS_TYPES or engine_registry.has(t)


# 結論帯・出典を付けられない（全面・固有レイアウトの）タイプ
NO_BOTTOM_PARTS = {"title", "section", "quote", "closing", "canvas", "statement"}
# 本文の高さを詰めるときに触らない領域（タイトルまわり・フッター）
CHROME_REGIONS = {"eyebrow", "title", "rule", "lead", "footer_l", "footer_r", "brand", "conclusion", "source", "legend", "panel"}


def shrink_for_bottom(slide: dict, st: dict, skip_table_rows: bool = False) -> dict:
    """既存タイプで結論帯・出典を付けるとき、本文の領域の下端を詰める（resolve_style から呼ぶ）。"""
    t = slide.get("type")
    r = reserve(slide, st)
    if not r or t in NO_BOTTOM_PARTS or draws_own_parts(t):
        return st
    limit = CONTENT_BOTTOM - r
    for name, reg in st.items():
        if name in CHROME_REGIONS or not isinstance(reg, dict) or "y" not in reg:
            continue
        lim = limit - (46 if (t == "matrix" and name == "grid") else 0)   # matrix は格子の下に軸ラベルがある
        if "h" in reg and reg["y"] + reg["h"] > lim:
            reg["h"] = max(lim - reg["y"], 40)
        if name == "table" and "row_h" in reg and not skip_table_rows:
            # 表は行の高さで決まるので、収まらなければ行を詰める（下限は文字の高さ程度）
            n = len(slide.get("rows", []) or [])
            if n and reg["y"] + reg.get("header_h", 0) + reg["row_h"] * n > limit:
                reg["row_h"] = max((limit - reg["y"] - reg.get("header_h", 0)) / n, reg.get("cell_size", 16) * 1.6)
    return st


def extras(slide: dict, st: dict, theme: dict) -> list:
    """既存タイプに重ねて描く追加の要素（結論帯・出典、two_column の三角、matrix の点、code の注釈）。"""
    t = slide.get("type")
    if draws_own_parts(t) or t == "canvas":
        return []
    ctx = Ctx(theme)
    out = []
    if t == "two_column" and slide.get("connector") in ("arrow", "triangle"):
        lb, rb = st.get("left", {}), st.get("right", {})
        gx = lb.get("x", 72) + lb.get("w", 548)
        gw = rb.get("x", 660) - gx
        cy = lb.get("y", 192) + lb.get("h", 452) / 2
        tw = max(min(gw - 10, 26), 10)
        out.append(ctx.tri_right(gx + (gw - tw) / 2, cy - 22, tw, 44, "border", name="流れ"))
    if t == "cards" and any(isinstance(c, dict) and c.get("icon") for c in slide.get("cards", []) or []):
        out += card_icons(slide, st, ctx)
    if t == "matrix" and slide.get("points"):
        out += matrix_points(slide, st, ctx)
    if t == "code" and slide.get("annotations"):
        out += code_annotations(slide, st, ctx)
    if t not in NO_BOTTOM_PARTS and (slide.get("conclusion") or slide.get("source")):
        r = reserve(slide, st)
        sb = st.get("body") if t == "split" and isinstance(st.get("body"), dict) else None     # split はパネルの残りの幅に置く
        body = {"x": sb["x"] if sb else 72, "y": CONTENT_BOTTOM - r, "w": sb["w"] if sb else 1136, "h": 0}
        out += common_parts(slide, st, ctx, body)
    return out


def cards_cells(n: int, slide_columns, g: dict, spans=None) -> dict:
    """cards の格子の配置（HTML・PPTX・アイコン・自動フィットで共通）。
    戻り値 {cols, rows, gap, cw, chh, cells: [(x, y, w, h)]}。列数は slide.columns が grid.cols に優先する。
    spans（各カードの占める列数。hero_engine.card_spans(slide)）があれば、その幅で左上から右へ詰めて置く（cells は span ぶんの幅）。"""
    if spans:
        import hero_engine
        return hero_engine.cards_plan(n, slide_columns, g, spans)
    cols = max(1, slide_columns if isinstance(slide_columns, int) and not isinstance(slide_columns, bool)
               else g.get("cols", 3))
    rows = max(1, (n + cols - 1) // cols)
    gap = g.get("gap", 16)
    cw = (g["w"] - (cols - 1) * gap) / cols
    chh = (g["h"] - (rows - 1) * gap) / rows
    cells = [(g["x"] + (i % cols) * (cw + gap), g["y"] + (i // cols) * (chh + gap), cw, chh) for i in range(n)]
    return {"cols": cols, "rows": rows, "gap": gap, "cw": cw, "chh": chh, "cells": cells}


def card_icons(slide: dict, st: dict, ctx: Ctx) -> list:
    """cards の各カードの右上にアイコンを置く（カードの位置は cards_cells と同じ計算）。"""
    g = st.get("grid", {})
    cards = slide.get("cards", []) or []
    import hero_engine
    geo = cards_cells(len(cards), slide.get("columns"), g, hero_engine.card_spans(slide))
    size = g.get("icon_size", 28)
    out = []
    for idx, card in enumerate(cards):
        if not isinstance(card, dict) or not card.get("icon"):
            continue
        x, y, cw = geo["cells"][idx][0], geo["cells"][idx][1], geo["cells"][idx][2]
        ic = ctx.icon(card["icon"], x + cw - size - 12, y + 12, size, hero_engine.card_style(g, hero_engine.card_emphasis(card))["icon_color"],
                      name=f"カード{idx + 1}のアイコン")
        if ic:
            out.append(ic)
    return out


def icon_specs(slide: dict) -> list:
    """スライドに書かれた icon 指定を (場所, 指定) で列挙する（検証用）。"""
    out = []
    for key in ("items", "strengths", "pillars", "stages", "cards"):
        for k, it in enumerate(slide.get(key, []) or []):
            if isinstance(it, dict) and it.get("icon"):
                out.append((f"{key}[{k}].icon", it["icon"]))
    return out


POINT_LABEL_W = 200      # matrix の点のラベルの幅 / 文字サイズ（自動フィットの警告でも使う）
POINT_LABEL_SIZE = 14


def matrix_points(slide: dict, st: dict, ctx: Ctx) -> list:
    """2×2 マトリクスの上に項目を点で置く（x・y は 0〜1。x は右、y は上ほど大きい）。"""
    g = st.get("grid", {})
    gx, gy, gw, gh = g.get("x", 172), g.get("y", 208), g.get("w", 1000), g.get("h", 372)
    d = 26
    out = []
    for k, pt in enumerate(slide.get("points", [])):
        if not isinstance(pt, dict):
            continue
        px = gx + min(max(float(pt.get("x", 0.5)), 0), 1) * gw
        py = gy + (1 - min(max(float(pt.get("y", 0.5)), 0), 1)) * gh
        hi = bool(pt.get("highlight"))
        out.append(ctx.box(px - d / 2, py - d / 2, d, d, geom="ellipse", fill="accent" if hi else "primary",
                           line="background", line_w=1.5,
                           paras=[ctx.para(str(pt.get("n", k + 1)), 13, "on_primary", bold=True, align="ctr", lh=1.0)],
                           anchor="ctr", name=f"点{k + 1}"))
        if pt.get("label"):
            left = px > gx + gw * 0.75
            lw = POINT_LABEL_W
            lines = ja_text.estimate_lines(str(pt["label"]), POINT_LABEL_SIZE, lw, None, hi)
            lh_px = max(22.0, lines * POINT_LABEL_SIZE * LINE_H)       # 長いラベルは行数ぶん箱を伸ばす（以前は 22px 固定ではみ出した）
            out.append(ctx.box(px - d / 2 - 6 - lw if left else px + d / 2 + 6, py - lh_px / 2, lw, lh_px,
                               paras=[ctx.para(pt["label"], POINT_LABEL_SIZE, "heading_text", bold=hi,
                                               align="r" if left else "l", lh=1.0)], anchor="ctr", name=f"点{k + 1}の名前"))
    return out


def code_annotations(slide: dict, st: dict, ctx: Ctx) -> list:
    """コードの右に番号付きの注釈を並べ、該当行に同じ番号の丸と左端の印を置く。"""
    import build_deck   # 循環 import を避けて遅延 import（コードの文字サイズは build_deck と同じ計算を使う）
    r = st.get("code", {})
    size, _ = build_deck.fit_code_size(slide.get("code", ""), r)
    lh = r.get("line_height", 1.45)
    pad = r.get("pad", 28)
    nx = r["x"] + r["w"] + 34   # コードと注釈の間に、行の番号丸を置く溝を空ける
    nw = 72 + 1136 - nx
    anns = [a for a in slide.get("annotations", []) if isinstance(a, dict)]
    out = []
    n = max(len(anns), 1)
    gap = 10
    nh = min((r["h"] - gap * (n - 1)) / n, 120)
    for k, a in enumerate(anns):
        line = int(a.get("line", 0) or 0)
        if line > 0:
            ly = r["y"] + pad + (line - 1) * size * lh + size * lh / 2
            if ly < r["y"] + r["h"] - 8:
                out.append(ctx.box(r["x"] + r["w"] + 1, ly - 11, 22, 22, geom="ellipse", fill="accent",
                                   paras=[ctx.para(str(k + 1), 12, "on_primary", bold=True, align="ctr", lh=1.0)],
                                   anchor="ctr", name=f"注釈の行{k + 1}"))
                out.append(ctx.box(r["x"] + 8, ly - size * lh / 2, 4, size * lh, fill="accent", name=f"注釈の印{k + 1}"))
        y = r["y"] + k * (nh + gap)
        out.append(ctx.box(nx, y + 2, 26, 26, geom="ellipse", fill="accent",
                           paras=[ctx.para(str(k + 1), 13, "on_primary", bold=True, align="ctr", lh=1.0)],
                           anchor="ctr", name=f"注釈番号{k + 1}"))
        paras = [ctx.para(a.get("title", ""), 16, "heading_text", bold=True, head=True, after=3 if a.get("text") else 0)]
        if a.get("text"):
            paras.append(ctx.para(a["text"], 14, "text"))
        out.append(ctx.box(nx + 36, y, nw - 36, nh, paras=paras, anchor="t", name=f"注釈{k + 1}"))
    return out


_FITLOG = None   # fit_report() が有効な間だけ、_fit の結果（収まったか）を貯めるリスト


def _fit(candidates, need, tag: str = "") -> tuple:
    """need(sizes) が True を返す最初の候補（大きい順に並べる）。どれも収まらなければ最後の候補。
    fit_report() の最中は、どの候補を選んだか・最小の候補でも収まらなかったか（ok=False）を記録する
    （以前は最小サイズで黙って描いていた。A5-03 / A8-10〜13）。"""
    for s in candidates:
        if need(s):
            if _FITLOG is not None:
                _FITLOG.append({"tag": tag, "chosen": s, "ok": True, "cap": candidates[0]})
            return s
    if _FITLOG is not None:
        _FITLOG.append({"tag": tag, "chosen": candidates[-1], "ok": False, "cap": candidates[0]})
    return candidates[-1]


def descending(cap, floor, step=1) -> list:
    """cap から floor まで step 刻みで下げた候補（大きい順）。cap が floor 以下なら [cap]。"""
    step = max(step, (cap - floor) / 400)       # 極端に大きい cap でも候補は 400 個まで（2^53 以上では x - 1 == x で終わらない）
    out, x = [cap], cap - step
    while x >= floor and len(out) < 402:
        out.append(x)
        x -= step
    return out


def _virtual_body(body: dict, st: dict):
    """本文の矩形と拡大率 k（style.body.scale_k。既定 1）→ (自然な大きさで組む仮想の矩形, k)。k > 1 のとき、仮想の矩形は原点 (0, 0)・幅と高さが 1/k
    （合成のブロックの org / kpi_tree を、自然な大きさで組んでから canvas_engine.transform_elements で k 倍する・S5a）。"""
    import diagram_scale as dscale
    k = dscale.scale_of(st.get("body") or {})
    if k == 1.0:
        return body, 1.0
    bv = dict(body)
    bv.update({"x": 0.0, "y": 0.0, "w": body["w"] / k, "h": body["h"] / k})
    return bv, k


def layout_elements(slide: dict, st: dict) -> list:
    """提案書系タイプを一度レイアウトして、本体の canvas 要素列（共通パーツは含まない）を返す。st["body"]["scale_k"] > 1 のときは、
    自然な大きさで組んだ仮想の矩形（枠を 1/k にしたもの）の要素列のまま（k 倍はしない）。組めなければ []。折り返しの比較（autofit._scale_proposal）が使う。"""
    fn = LAYOUTS.get(slide.get("type"))
    if fn is None or slide.get("type") == "statement":
        return []
    try:
        return list(fn(slide, st, Ctx({"colors": {}, "fonts": {}}), _virtual_body(body_region(slide, st), st)[0]))
    except Exception:
        return []


def fit_report(slide: dict, st: dict) -> list:
    """提案書系タイプを一度レイアウトして、_fit の選択結果 [{tag, chosen, ok, cap}] を返す（描画はしない）。
    ok=False は「最小の文字サイズでも枠に収まらない」。build_deck の自動フィットが警告にする。"""
    global _FITLOG
    t = slide.get("type")
    fn = LAYOUTS.get(t)
    if fn is None:
        return []
    log: list = []
    _FITLOG = log
    try:
        ctx = Ctx({"colors": {}, "fonts": {}})
        if t == "statement":
            layout_statement(slide, st, ctx)
        else:
            fn(slide, st, ctx, _virtual_body(body_region(slide, st), st)[0])
    except Exception:
        return []        # 入力の誤りは本番の描画が slide_guard で報告する。ここでは警告を出せないだけ
    finally:
        _FITLOG = None
    return log


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

    ls, ts = _fit(g.get("sizes", [(20, 16), (19, 15), (18, 14), (16, 13), (15, 12)]), fits, "summary")
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
        ic = ctx.icon(it.get("icon"), body["x"] + num_w + pad, y + row_h / 2 - 14, 28, g.get("icon_color", "primary"),
                      name=f"要点{i + 1}のアイコン") if it.get("icon") else None
        out.append(ctx.box(body["x"] + num_w, y, body["w"] - num_w, row_h, fill=g.get("band_fill", "surface"),
                           paras=paras, anchor="ctr", insets=(pad + (42 if ic else 0), 4, pad, 4), name=f"要点{i + 1}"))
        if ic:
            out.append(ic)
    return out


# ---------------------------------------------------------------------------
# reasons — 課題（番号）× 強み（a/b/c）の対応（選ばれる理由）
# ---------------------------------------------------------------------------

def _alpha_label(k: int) -> str:
    """強みの記号 a, b, c …（26 個を超えたら番号）。"""
    return chr(ord("a") + k) if 0 <= k < 26 else str(k + 1)


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

    ts, bs = _fit(g.get("sizes", [(17, 14), (16, 13), (15, 12), (14, 12)]), need, "reasons")
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
            label = s.get("label") or _alpha_label(k)
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
            ic = ctx.icon(s.get("icon"), rx + badge + pad, y + row_h / 2 - 13, 26, g.get("icon_color", "primary"),
                          name=f"強み{k + 1}のアイコン") if s.get("icon") else None
            out.append(ctx.box(rx + badge, y, rw - badge, row_h, paras=paras, anchor="ctr",
                               insets=(pad + (38 if ic else 0), pad / 2, pad, pad / 2), name=f"強み本文{k + 1}"))
            if ic:
                out.append(ic)
    return out


# ---------------------------------------------------------------------------
# statement — 濃色の面に大きな一文（物語の転換点の言い切り）
# ---------------------------------------------------------------------------

_ALIGN = {"left": "l", "center": "ctr", "right": "r"}


def layout_statement(slide, st, ctx, body=None):
    import hero_engine as hero
    bg = st.get("background", {})
    out = [ctx.box(0, 0, 1280, 720, fill=bg.get("fill", "primary"), name="背景")]
    # 背景画像（background）・variant の飾り（deco*）・大きな引用符（mark）。色面の指定は st.background.fill に反映済み
    out += hero.hero_background_elements(st, slide.get("_bg"), ctx.colors) if isinstance(slide.get("_bg"), dict) and slide["_bg"].get("image") else []
    out += hero.deco_elements(st, ctx.colors)
    out += hero.mark_elements(st, ctx.colors)          # mark に "vector": true があれば図形で描く（フォントの字形の左右ずれを避ける）
    mk = st.get("mark")
    if isinstance(mk, dict) and mk.get("size") and mk.get("w") and mk.get("h") and not hero.mark_is_vector(st):
        out.append(ctx.box(mk.get("x", 96), mk.get("y", 60), mk["w"], mk["h"],
                           paras=[ctx.para("\u201c", mk["size"], mk.get("color", "accent_on_primary"), bold=True, head=True, lh=1.0)], name="引用符"))
    k, m, s = st.get("kicker", {}), st.get("message", {}), st.get("support", {})
    msg = slide.get("message") or slide.get("title", "")
    cap = m.get("size", 44)
    floor = min(m.get("min_size", 28), cap)
    step = 1 if cap <= 48 else max(2, round(cap * 0.04))     # 100px の指定でも 28px まで一気に落とさず、刻んで探す
    cands = [cap] + [x for x in (40, 36, 32, 28) if floor <= x < cap] if cap <= 48 else descending(cap, floor, step)
    if cands[-1] > floor:
        cands.append(floor)          # 刻みが floor を通らなくても、最後は必ず下限を試す（警告の「最小サイズ」を実際の下限にする）
    size = _fit(cands, lambda sz: text_h(msg, sz, m.get("w", 1040), head=True, bold=True, lh=1.25) <= m.get("h", 220) + 0.5,
                "statement")
    if slide.get("kicker"):
        out.append(ctx.box(k.get("x", 120), k.get("y", 220), k.get("w", 1040), k.get("h", 32),
                           paras=[ctx.para(slide["kicker"], k.get("size", 20), k.get("color", "on_primary_muted"),
                                           bold=True, head=True, lh=1.0, align=_ALIGN.get(k.get("align"), "l"))], name="キッカー"))
        rx = k.get("x", 120) + ((k.get("w", 1040) - 64) / 2 if k.get("align") == "center" else 0)
        out.append(ctx.box(rx, k.get("y", 220) + k.get("h", 32) + 4, 64, 4,
                           fill=k.get("rule", "accent_on_primary"), name="区切り"))
    out.append(ctx.box(m.get("x", 120), m.get("y", 280), m.get("w", 1040), m.get("h", 220),
                       paras=[ctx.para(msg, size, m.get("color", "on_primary"), bold=True, head=True, lh=1.25,
                                       align=_ALIGN.get(m.get("align"), "l"))],
                       anchor="ctr", name="メッセージ"))
    if slide.get("support"):
        out.append(ctx.box(s.get("x", 120), s.get("y", 520), s.get("w", 1040), s.get("h", 80),
                           paras=[ctx.para(slide["support"], s.get("size", 20), s.get("color", "on_primary_soft"),
                                           align=_ALIGN.get(s.get("align"), "l"))],
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
    head_size = g.get("head_size", 15)
    if has_head:
        inset_w = 24 if arrow else 16
        head_size = _fit(descending(head_size, min(g.get("head_min_size", 12), head_size)),
                         lambda sz: all(text_h(c, sz, max(cws[j] - inset_w, 10), head=True, bold=True, lh=1.0) <= head_h + 0.5
                                        for j, c in enumerate(cols)), "row_matrix.head")
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
                                   paras=[ctx.para(c, head_size, g.get("head_color", "table_header_text"),
                                                   bold=True, head=True, align="ctr", lh=1.0)],
                                   anchor="ctr", insets=(16, 0, 8, 0), name=f"列見出し{j + 1}"))
            else:
                out.append(ctx.box(xs[j], body["y"], cws[j] - (gap if j < nc - 1 else 0), head_h,
                                   fill=g.get("head_fill", "table_header_bg"),
                                   paras=[ctx.para(c, head_size, g.get("head_color", "table_header_text"),
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

    size = _fit(g.get("sizes", [16, 15, 14, 13, 12]), lambda s: sum(heights(s)) <= avail + 0.5, "row_matrix")
    hs = heights(size)
    extra = max(avail - sum(hs), 0) / max(len(rows), 1)
    hs = [h + extra for h in hs]
    # 行見出し（左の列）が行の高さに収まる文字サイズ
    label_size = g.get("label_size", 15)
    row_labels = [(r.get("label", "") if isinstance(r, dict) else str(r)) for r in rows]
    if rows:
        label_size = _fit(descending(label_size, min(g.get("label_min_size", 12), label_size)),
                          lambda sz: all(text_h(t, sz, label_w - 16, head=True, bold=True) <= h - 8 + 0.5
                                         for t, h in zip(row_labels, hs)), "row_matrix.label")
    y = top
    for i, r in enumerate(rows):
        r = r if isinstance(r, dict) else {"label": str(r)}
        h = hs[i]
        out.append(ctx.box(body["x"], y, label_w, h, fill=g.get("label_fill", "highlight_fill"),
                           paras=[ctx.para(r.get("label", ""), label_size, g.get("label_color", "heading_text"),
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
        # 提案範囲の破線枠は、見出しの列と同じ幅（本文領域の中）に収める。枠の中の木はその分だけ内側に寄せる
        # （枠を外側へ pad 広げていた頃は、右の枠が右余白を越えていた）
        scope_pad = g.get("scope_pad", 8) if side.get("scope") else 0
        tx0, tw0 = sx + scope_pad, side_w - 2 * scope_pad
        tag_h = g.get("scope_tag_h", 24)
        top = body["y"] + title_h + 10
        avail_h = body["y"] + body["h"] - top - 6 - ((tag_h + 8) if any(sd.get("scope") for sd in sides) else 0)   # 札の分は全部の側で空け、左右の根の高さをそろえる
        level_gap = g.get("level_gap", 26)
        node_h = min(g.get("node_h", 64), (avail_h - level_gap * (levels - 1)) / levels)
        if levels > 1:
            # 階層が浅いときは段の間隔を広げ（最大 max_level_gap）、余りは上 1/3・下 2/3 に配って上寄りに置く
            level_gap = min(max(level_gap, (avail_h - levels * node_h) / (levels - 1) * 0.6),
                            g.get("max_level_gap", 70))
        used = levels * node_h + (levels - 1) * level_gap
        top += max(avail_h - used, 0) / 3
        slot_w = tw0 / leaves
        node_w = min(g.get("node_w", 200), slot_w - g.get("node_gap", 14))
        head_h = min(g.get("node_head_h", 26), node_h * 0.45)
        hf = g.get("right_head_fill" if is_right else "left_head_fill", "primary" if is_right else "muted")
        for nid, n in by_id.items():
            cx = tx0 + (pos[nid] + 0.5) * slot_w
            y = top + depth[nid] * (node_h + level_gap)
            x = cx - node_w / 2
            centers[nid] = (cx, y, y + node_h, x, x + node_w)
            ts = _fit([14, 13, 12, 11], lambda s: text_h(n.get("title", ""), s, node_w - 12, bold=True) <= head_h, "org")
            out.append(ctx.box(x, y, node_w, head_h, fill=n.get("fill", hf),
                               paras=[ctx.para(n.get("title", ""), ts, g.get("node_head_color", "on_primary"), bold=True,
                                               head=True, align="ctr", lh=1.0)], anchor="ctr", insets=(6, 0, 6, 0),
                               name=nid))
            body_lines = [str(n[k]) for k in ("name", "members") if n.get(k)]
            bs = _fit([13, 12, 11], lambda s: sum(text_h(t, s, node_w - 12) for t in body_lines) <= node_h - head_h - 4, "org")
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
            out.append(ctx.box(sx, body["y"] + title_h + 2, side_w,
                               body["y"] + body["h"] - (body["y"] + title_h + 2), line=g.get("scope_color", "accent"),
                               dash="dash", line_w=1.5, name="提案範囲"))
            label = side["scope"] if isinstance(side["scope"], str) else "ご支援範囲"
            tag_w = max(g.get("scope_tag_w", 110), _text_w(ctx, label, 12, True) + 24)
            # 札は枠の右下の内側に置く（枠線の上にまたがらない）
            out.append(ctx.box(sx + side_w - tag_w - 4, body["y"] + body["h"] - tag_h - 4, tag_w, tag_h,
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
            # 連携の名前は背景（地の色）つきの札にして、背後を通る破線枠・線が文字を貫通して見えないようにする
            lab_w = _text_w(ctx, ln["label"], 12, True) + 12
            out.append(ctx.box(midx - lab_w / 2, min(ya, yb) - 21, lab_w, 18, fill="background",
                               paras=[ctx.para(ln["label"], 12, g.get("link_color", "accent"), bold=True, align="ctr",
                                               lh=1.0)], anchor="ctr", name="連携の名前"))
    if slide.get("legend"):
        out.append(ctx.box(body["x"], body["y"], body["w"], title_h,
                           paras=[ctx.para(slide["legend"], 12, "muted", align="r", lh=1.0)], anchor="ctr",
                           name="凡例"))
    return out


# ---------------------------------------------------------------------------
# house — 全体像（屋根＝目指す姿 / 柱＝取り組み / 土台＝基盤）
# ---------------------------------------------------------------------------

def layout_house(slide, st, ctx, body):
    g = st.get("body", {})
    roof = slide.get("roof") or {}
    roof = roof if isinstance(roof, dict) else {"title": str(roof)}
    pillars = slide.get("pillars", []) or []
    founds = [f if isinstance(f, dict) else {"title": str(f)} for f in slide.get("foundations", []) or []]
    gap = g.get("gap", 10)
    roof_h = g.get("roof_h", 84) if roof else 0
    found_h = g.get("found_h", 36)
    fz = len(founds) * (found_h + gap)
    out = []
    x0, w = body["x"], body["w"]
    top_y = body["y"]        # 屋根の上端（柱が内容より低くなったとき、全体を上下中央に置くため後で動かす）
    if roof:
        inset = g.get("roof_inset", 40)
        # 屋根は台形（左右の斜辺＋上辺）。文字は中央の帯に置く
        out.append({"kind": "shape", "geom": "custom", "x": round(x0, 2), "y": round(body["y"], 2), "w": round(w, 2),
                    "h": round(roof_h, 2), "fill": ctx.c(g.get("roof_fill", "primary")), "name": "屋根",
                    "path": [{"cmds": [["M", 0, round(roof_h, 2)], ["L", inset * 3, 0], ["L", round(w - inset * 3, 2), 0],
                                       ["L", round(w, 2), round(roof_h, 2)], ["Z"]], "fill": True, "stroke": False}]})
        roof_w = w - inset * 6 - 8

        def roof_need(sz):
            sub = g.get("roof_sub_size", 14)
            return (text_h(roof.get("title", ""), sz, roof_w, head=True, bold=True, lh=1.1)
                    + (text_h(roof["text"], sub, roof_w, lh=1.1) + 2 if roof.get("text") else 0)) <= roof_h - 8 + 0.5
        roof_size = _fit(descending(g.get("roof_size", 20), min(g.get("roof_min_size", 14), g.get("roof_size", 20))),
                         roof_need, "house.roof")
        paras = [ctx.para(roof.get("title", ""), roof_size, g.get("roof_color", "on_primary"), bold=True,
                          head=True, align="ctr", lh=1.1, after=2 if roof.get("text") else 0)]
        if roof.get("text"):
            paras.append(ctx.para(roof["text"], g.get("roof_sub_size", 14), g.get("roof_sub_color", "on_primary_soft"),
                                  align="ctr", lh=1.1))
        out.append(ctx.box(x0 + inset * 3, body["y"] + 6, w - inset * 6, roof_h - 8, paras=paras, anchor="ctr",
                           name="屋根の文字"))
    top = body["y"] + roof_h + (gap if roof else 0)
    ph = body["y"] + body["h"] - top - fz
    n = max(len(pillars), 1)
    pgap = g.get("pillar_gap", 12)
    pw = (w - pgap * (n - 1)) / n
    head_h = g.get("pillar_head_h", 38)
    pad = g.get("pad", 12)

    def need_h(sz):
        """全部の柱のうち最も高い中身（余白込み）の高さ。"""
        m = 0.0
        for p in pillars:
            p = p if isinstance(p, dict) else {"title": str(p)}
            text, its = as_items(p.get("items") if p.get("items") is not None else p.get("text"))
            m = max(m, (text_h(text, sz, pw - 2 * pad) if text else 0) + items_h(its, sz, pw - 2 * pad, 3) + 2 * pad)
        return m

    def need(sz):
        return need_h(sz) <= ph - head_h

    size = _fit(g.get("sizes", [15, 14, 13, 12, 11]), need, "house")
    # 柱の枠は「中身＋余白」までに抑える（中身が少ないと、枠の下半分が空いて見えた）。全体は本文領域の上下中央に置く
    pillar_h = ph - head_h
    if pillars and g.get("fit_content", True):
        pillar_h = min(pillar_h, max(g.get("pillar_min_h", 130), need_h(size) * g.get("pillar_k", 1.3)))
        ph = head_h + pillar_h
    y_shift = max(0.0, (body["y"] + body["h"] - top - fz - ph) / 2) if g.get("fit_content", True) else 0.0

    def head_need(sz):
        for p in pillars:
            p = p if isinstance(p, dict) else {"title": str(p)}
            iw = pw - 16 - (28 if p.get("icon") else 0) * 2
            if text_h(p.get("title", ""), sz, iw, head=True, bold=True, lh=1.05) > head_h - 4 + 0.5:
                return False
        return True
    pillar_head = _fit(descending(g.get("pillar_head_size", 16), min(g.get("pillar_head_min_size", 12),
                                                                       g.get("pillar_head_size", 16))),
                       head_need, "house.head") if pillars else g.get("pillar_head_size", 16)
    for k, p in enumerate(pillars):
        p = p if isinstance(p, dict) else {"title": str(p)}
        x = x0 + k * (pw + pgap)
        ic = ctx.icon(p.get("icon"), x + 10, top + head_h / 2 - 11, 22, g.get("pillar_head_color", "heading_text"),
                      name=f"柱{k + 1}のアイコン") if p.get("icon") else None
        out.append(ctx.box(x, top, pw, head_h, fill=g.get("pillar_head_fill", "highlight_fill"),
                           paras=[ctx.para(p.get("title", ""), pillar_head,
                                           g.get("pillar_head_color", "heading_text"), bold=True, head=True,
                                           align="ctr", lh=1.05)], anchor="ctr",
                           insets=(8 + (28 if ic else 0), 2, 8 + (28 if ic else 0), 2), name=f"柱{k + 1}"))
        if ic:
            out.append(ic)
        text, its = as_items(p.get("items") if p.get("items") is not None else p.get("text"))
        paras = ([ctx.para(text, size, g.get("text_color", "text"), after=3 if its else 0)] if text else [])
        paras += [ctx.para(t, size, g.get("text_color", "text"), bullet="•", after=3) for t in its]
        out.append(ctx.box(x, top + head_h, pw, ph - head_h, fill="background", line=g.get("border_color", "border"),
                           paras=paras or None, anchor="t", insets=(pad, pad, pad, pad), name=f"柱{k + 1}の内容"))
    y = top + ph + gap

    def found_label(f):
        label = f.get("title", "")
        if f.get("text"):
            label = f"{label}｜{f['text']}" if label else f["text"]
        return label
    found_size = g.get("found_size", 15)
    if founds:
        found_size = _fit(descending(found_size, min(g.get("found_min_size", 12), found_size)),
                          lambda sz: all(text_h(found_label(f), sz, w - 24, head=True, bold=True, lh=1.0) <= found_h + 0.5
                                         for f in founds), "house.found")
    for k, f in enumerate(founds):
        label = found_label(f)
        out.append(ctx.box(x0, y, w, found_h, fill=g.get("found_fill", "primary") if k == len(founds) - 1
                           else g.get("found_fill2", "accent"),
                           paras=[ctx.para(label, found_size, g.get("found_color", "on_primary"), bold=True,
                                           head=True, align="ctr", lh=1.0)], anchor="ctr", insets=(12, 0, 12, 0),
                           name=f"土台{k + 1}"))
        y += found_h + gap
    if y_shift:
        for el in out:
            el["y"] = round(el["y"] + y_shift, 2)
    return out


# ---------------------------------------------------------------------------
# cycle — 循環（中央の円＋円弧の矢印＋左右の段のパネル）
# ---------------------------------------------------------------------------

def _arc_pts(cx, cy, r, a0, a1, steps=12):
    import math
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def layout_cycle(slide, st, ctx, body):
    import math
    g = st.get("body", {})
    stages = [s if isinstance(s, dict) else {"title": str(s)} for s in slide.get("stages", []) or []]
    n = max(len(stages), 1)
    ring_w = min(g.get("ring_d", 300), body["h"], body["w"] * 0.32)
    cx, cy = body["x"] + body["w"] / 2, body["y"] + body["h"] / 2
    r = ring_w / 2 - 14
    col = g.get("ring_color", "border")
    out = []
    # 円弧の矢印（段と段の間。始点・終点は番号丸の外側から）
    badge = g.get("badge_d", 30)
    gap_deg = math.degrees((badge / 2 + 6) / r) if r > 0 else 10
    for k in range(n):
        a0 = -90 + 360 * k / n + gap_deg
        a1 = -90 + 360 * (k + 1) / n - gap_deg
        pts = _arc_pts(cx, cy, r, a0, a1)
        out.append(ctx.path(pts, col, g.get("ring_w", 6)))
        # 矢じり（終点の接線方向を向いた三角）
        ex, ey = pts[-1]
        ang = math.radians(a1 + 90)
        size = g.get("head", 14)
        tip = (ex + math.cos(ang) * size * 0.6, ey + math.sin(ang) * size * 0.6)
        nx, ny = math.cos(math.radians(a1)), math.sin(math.radians(a1))
        p1 = (ex - math.cos(ang) * size * 0.4 + nx * size * 0.5, ey - math.sin(ang) * size * 0.4 + ny * size * 0.5)
        p2 = (ex - math.cos(ang) * size * 0.4 - nx * size * 0.5, ey - math.sin(ang) * size * 0.4 - ny * size * 0.5)
        xs, ys = [tip[0], p1[0], p2[0]], [tip[1], p1[1], p2[1]]
        x0, y0 = min(xs), min(ys)
        out.append({"kind": "shape", "geom": "custom", "x": round(x0, 2), "y": round(y0, 2),
                    "w": round(max(xs) - x0, 2), "h": round(max(ys) - y0, 2), "fill": ctx.c(col), "name": f"矢じり{k + 1}",
                    "path": [{"cmds": [["M", round(tip[0] - x0, 2), round(tip[1] - y0, 2)],
                                       ["L", round(p1[0] - x0, 2), round(p1[1] - y0, 2)],
                                       ["L", round(p2[0] - x0, 2), round(p2[1] - y0, 2)], ["Z"]],
                              "fill": True, "stroke": False}]})
    # 番号丸（各段の位置）
    for k in range(n):
        a = math.radians(-90 + 360 * k / n)
        bx, by = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(ctx.box(bx - badge / 2, by - badge / 2, badge, badge, geom="ellipse", fill=g.get("badge_fill", "primary"),
                           paras=[ctx.para(str(k + 1), 14, g.get("badge_color", "on_primary"), bold=True, align="ctr",
                                           lh=1.0)], anchor="ctr", name=f"段番号{k + 1}"))
    if slide.get("center"):
        cd = ring_w * 0.42
        out.append(ctx.box(cx - cd / 2, cy - cd / 2, cd, cd, geom="ellipse", fill=g.get("center_fill", "surface"),
                           paras=[ctx.para(slide["center"], g.get("center_size", 20), g.get("center_color", "heading_text"),
                                           bold=True, head=True, align="ctr", lh=1.1)], anchor="ctr", name="中心"))
    # 左右のパネル（右列＝前半を上から、左列＝後半を下から → 時計回りに読める）
    right = list(range((n + 1) // 2))
    left = list(range((n + 1) // 2, n))[::-1]
    pgap = g.get("panel_gap", 14)
    side_gap = g.get("side_gap", 24)
    pw = (body["w"] - ring_w) / 2 - side_gap
    pad = g.get("pad", 12)

    def place(idx, x):
        m = max(len(idx), 1)
        ph = (body["h"] - pgap * (m - 1)) / m
        return [(k, x, body["y"] + j * (ph + pgap), ph) for j, k in enumerate(idx)]

    slots = place(right, cx + ring_w / 2 + side_gap) + place(left, body["x"])

    def need(sz):
        for k, x, y, ph in slots:
            s = stages[k] if k < len(stages) else {}
            text, its = as_items(s.get("items") if s.get("items") is not None else s.get("text"))
            hh = text_h(s.get("title", ""), sz + 2, pw - badge - 2 * pad, head=True, bold=True) + \
                (text_h(text, sz, pw - badge - 2 * pad) if text else 0) + items_h(its, sz, pw - badge - 2 * pad, 2)
            if hh + 2 * pad > ph:
                return False
        return True

    size = _fit(g.get("sizes", [15, 14, 13, 12, 11]), need, "cycle")
    for k, x, y, ph in slots:
        if k >= len(stages):
            continue
        s = stages[k]
        text, its = as_items(s.get("items") if s.get("items") is not None else s.get("text"))
        # 番号丸と本文の塊をまとめてパネルの縦中央に置く（番号丸は見出しの行にそろえる）
        hh = text_h(s.get("title", ""), size + 2, pw - badge - 2 * pad, head=True, bold=True) + 3 +             (text_h(text, size, pw - badge - 2 * pad) + 2 if text else 0) + items_h(its, size, pw - badge - 2 * pad, 2)
        off = max((ph - hh) / 2, pad / 2)
        title_line = (size + 2) * LINE_H * PARA_LH
        out.append(ctx.box(x, y, pw, ph, fill=g.get("panel_fill", "surface"), name=f"段{k + 1}"))
        out.append(ctx.box(x + pad, y + off + title_line / 2 - (badge - 6) / 2, badge - 6, badge - 6, geom="ellipse",
                           fill=g.get("badge_fill", "primary"),
                           paras=[ctx.para(str(k + 1), 13, g.get("badge_color", "on_primary"), bold=True, align="ctr",
                                           lh=1.0)], anchor="ctr", name=f"段{k + 1}の番号"))
        paras = [ctx.para(s.get("title", ""), size + 2, g.get("title_color", "heading_text"), bold=True, head=True,
                          after=3)]
        if text:
            paras.append(ctx.para(text, size, g.get("text_color", "text"), after=2))
        paras += [ctx.para(t, size, g.get("text_color", "text"), bullet="•", after=2) for t in its]
        out.append(ctx.box(x + badge + pad, y, pw - badge - pad, ph, paras=paras, anchor="t",
                           insets=(0, off, pad + (34 if s.get("icon") else 0), 0), name=f"段{k + 1}の内容"))
        if s.get("icon"):
            ic = ctx.icon(s["icon"], x + pw - pad - 26, y + off, 26, g.get("icon_color", "primary"), name=f"段{k + 1}のアイコン")
            if ic:
                out.append(ic)
    return out


# ---------------------------------------------------------------------------
# kpi_tree — KPI ツリー（目標 → 方向性 → KPI＋目標値＋測り方）
# ---------------------------------------------------------------------------

def layout_kpi_tree(slide, st, ctx, body):
    g = st.get("body", {})
    branches = [b if isinstance(b, dict) else {"title": str(b)} for b in slide.get("branches", []) or []]
    heads = slide.get("headers")
    head_h = g.get("head_h", 28) if heads else 0
    out = []
    root_w, br_w, kpi_w, val_w = g.get("root_w", 150), g.get("branch_w", 170), g.get("kpi_w", 230), g.get("value_w", 120)
    gap_x = g.get("gap_x", 26)
    # 領域（body）が狭いときは、列の幅と間隔を同じ比率で縮めて、測り方の欄（最低 note_min_w）が領域の中に収まるようにする。
    # 以前は列幅が固定値の合計で決まり、幅 560 の領域に置くとスライドの外（x=1417）まで溢れた（合成スライドのブロックに置くとき）
    has_note = any(isinstance(kp, dict) and (kp.get("items") or kp.get("note")) for b in branches
                   for kp in (b.get("kpis", []) or []))
    cols_w = root_w + br_w + kpi_w + val_w
    avail_cols = body["w"] - (gap_x * 3 + 12) - (g.get("note_min_w", 200) if has_note else 0)
    scaled = cols_w > avail_cols
    if scaled:
        k_ = max(avail_cols / cols_w, g.get("min_scale", 0.5))
        root_w, br_w, kpi_w, val_w, gap_x = root_w * k_, br_w * k_, kpi_w * k_, val_w * k_, gap_x * k_
    xs = [body["x"]]
    for w_ in (root_w, br_w, kpi_w):
        xs.append(xs[-1] + w_ + gap_x)
    vx = xs[3] + val_w + 12
    note_w = body["x"] + body["w"] - vx
    top = body["y"] + head_h + (6 if heads else 0)
    rows = [(bi, k) for bi, b in enumerate(branches) for k in range(max(len(b.get("kpis", []) or []), 1))]
    nrows = max(len(rows), 1)
    rgap = g.get("row_gap", 8)
    bgap = g.get("branch_gap", 14)
    avail = body["y"] + body["h"] - top - rgap * (nrows - len(branches)) - bgap * max(len(branches) - 1, 0)
    rh = avail / nrows
    # 文字が行・箱の高さに収まる大きさ（収まらないときは最小サイズで描き、fit_report が警告にする）
    kpi_items = [(kp if isinstance(kp, dict) else {"title": str(kp)})
                 for b in branches for kp in (b.get("kpis", []) or [{}])]

    def _cap(key, default):
        return g.get(key, default)
    kpi_size = _fit(descending(_cap("kpi_size", 14), min(g.get("kpi_min_size", 11), _cap("kpi_size", 14))),
                    lambda sz: all(text_h(k.get("title", ""), sz, kpi_w - 16, bold=True, lh=1.1) <= rh - 4 + 0.5
                                   for k in kpi_items), "kpi_tree.kpi") if kpi_items else _cap("kpi_size", 14)
    value_size = _fit(descending(_cap("value_size", 24), min(g.get("value_min_size", 12), _cap("value_size", 24))),
                      lambda sz: all(text_h(k["value"], sz, val_w - 4, head=True, bold=True, lh=1.0) <= rh + 0.5
                                     # 領域が狭くて列を縮めたときは、目標値（「100%」など）が途中で折り返さない大きさまで下げる
                                     and (not scaled or _text_w(ctx, k["value"], sz, bold=True) <= val_w - 4)
                                     for k in kpi_items if k.get("value")), "kpi_tree.value")

    def _note_need(sz):
        for k in kpi_items:
            text, its = as_items(k.get("items") if k.get("items") is not None else k.get("note"))
            hh = (text_h(text, sz, note_w - 8) + 2 if text else 0) + sum(text_h(t, sz, note_w - 8 - sz) + 3 for t in its)
            if hh > rh - 4 + 0.5:
                return False
        return True
    note_size = _fit(descending(13, 11), _note_need, "kpi_tree.note")
    if heads:
        for j, (x, w_) in enumerate(zip(xs + [vx], [root_w, br_w, kpi_w + val_w + 12, 0, note_w])):
            if j == 3 or j >= len(heads) or not heads[j]:
                continue
            out.append(ctx.box(x, body["y"], w_ if j != 4 else note_w, head_h,
                               paras=[ctx.para(heads[j], 13, g.get("head_color", "muted"), bold=True, align="ctr", lh=1.0)],
                               anchor="ctr", name=f"見出し{j + 1}"))
            out.append(ctx.path([(x, body["y"] + head_h), (x + (w_ if j != 4 else note_w), body["y"] + head_h)],
                                g.get("border_color", "border"), 0.75))
    y = top
    branch_boxes, kpi_rows = [], []
    for bi, b in enumerate(branches):
        kpis = b.get("kpis", []) or [{}]
        h_b = rh * len(kpis) + rgap * (len(kpis) - 1)
        branch_boxes.append((y, h_b))
        out.append(ctx.box(xs[1], y + h_b / 2 - min(h_b, 64) / 2, br_w, min(h_b, 64), fill=g.get("branch_fill", "primary"),
                           paras=[ctx.para(b.get("title", ""), g.get("branch_size", 15), g.get("branch_color", "on_primary"),
                                           bold=True, head=True, align="ctr", lh=1.1)], anchor="ctr", insets=(8, 2, 8, 2),
                           name=f"方向性{bi + 1}"))
        for k, kp in enumerate(kpis):
            kp = kp if isinstance(kp, dict) else {"title": str(kp)}
            ky = y + k * (rh + rgap)
            kpi_rows.append((bi, ky))
            out.append(ctx.box(xs[2], ky, kpi_w, rh, fill=g.get("kpi_fill", "surface"),
                               paras=[ctx.para(kp.get("title", ""), kpi_size, g.get("kpi_color", "heading_text"),
                                               bold=True, align="ctr", lh=1.1)], anchor="ctr", insets=(8, 2, 8, 2),
                               name=f"KPI{bi + 1}-{k + 1}"))
            if kp.get("value"):
                out.append(ctx.box(xs[3], ky, val_w, rh, line=g.get("border_color", "border"),
                                   paras=[ctx.para(kp["value"], value_size, g.get("value_color", "primary"),
                                                   bold=True, head=True, align="ctr", lh=1.0)], anchor="ctr",
                                   name=f"目標値{bi + 1}-{k + 1}"))
            text, its = as_items(kp.get("items") if kp.get("items") is not None else kp.get("note"))
            paras = ([ctx.para(text, note_size, g.get("note_color", "text"), after=2)] if text else [])
            paras += [ctx.para(t, note_size, g.get("note_color", "text"), bullet="•", after=2) for t in its]
            if paras:
                out.append(ctx.box(vx, ky, note_w, rh, paras=paras, anchor="ctr", insets=(4, 2, 4, 2),
                                   name=f"測り方{bi + 1}-{k + 1}"))
            # 方向性 → KPI のカギ線
            mid = xs[2] - gap_x / 2
            out.append(ctx.path([(mid, ky + rh / 2), (xs[2], ky + rh / 2)], g.get("line_color", "muted"), 1.0))
        if len(kpis) > 1:
            mid = xs[2] - gap_x / 2
            out.append(ctx.path([(mid, y + rh / 2), (mid, y + h_b - rh / 2)], g.get("line_color", "muted"), 1.0))
        out.append(ctx.path([(xs[1] + br_w, y + h_b / 2), (xs[2] - gap_x / 2, y + h_b / 2)], g.get("line_color", "muted"), 1.0))
        y += h_b + bgap
    # 目標（根）
    total_top, total_bot = top, y - bgap
    rh_root = min(total_bot - total_top, g.get("root_h", 120))
    ry = (total_top + total_bot) / 2 - rh_root / 2
    # 目標の箱: 長い文は文字を縮める（収まらなければ最小サイズで描き、fit_report が警告にする。core-A-03）
    root_cap = g.get("root_size", 17)
    root_text = slide.get("root", "")
    root_size = _fit(descending(root_cap, min(g.get("root_min_size", 12), root_cap)),
                     lambda sz: text_h(root_text, sz, root_w - 20, head=True, bold=True, lh=1.15) <= rh_root - 8 + 0.5,
                     "kpi_tree.root") if root_text else root_cap
    out.append(ctx.box(xs[0], ry, root_w, rh_root, fill=g.get("root_fill", "primary"),
                       paras=[ctx.para(root_text, root_size, g.get("root_color", "on_primary"),
                                       bold=True, head=True, align="ctr", lh=1.15)], anchor="ctr", insets=(10, 4, 10, 4),
                       name="目標"))
    if branch_boxes:
        mid = xs[1] - gap_x / 2
        cys = [yb + hb / 2 for yb, hb in branch_boxes]
        out.append(ctx.path([(xs[0] + root_w, (total_top + total_bot) / 2), (mid, (total_top + total_bot) / 2)],
                            g.get("line_color", "muted"), 1.0))
        if len(cys) > 1:
            out.append(ctx.path([(mid, min(cys)), (mid, max(cys))], g.get("line_color", "muted"), 1.0))
        for c_y in cys:
            out.append(ctx.path([(mid, c_y), (xs[1], c_y)], g.get("line_color", "muted"), 1.0))
    return out


LAYOUTS = {
    "summary": layout_summary,
    "reasons": layout_reasons,
    "statement": layout_statement,
    "row_matrix": layout_row_matrix,
    "org": layout_org,
    "house": layout_house,
    "cycle": layout_cycle,
    "kpi_tree": layout_kpi_tree,
}


def layout(slide: dict, st: dict, theme: dict) -> list:
    """スライド1枚分の canvas 要素列（本文＋共通パーツ）。登録表（engine_registry）のタイプを引く。
    chrome=False のタイプ（statement）は見出し骨格も結論帯も持たない全面レイアウト。"""
    ctx = Ctx(theme)
    t = slide.get("type")
    spec = engine_registry.get(t)
    if spec is None:
        raise KeyError(t)
    if not spec.chrome:
        return spec.layout(slide, st, ctx, None)
    body = body_region(slide, st)
    bv, k = _virtual_body(body, st)
    els = spec.layout(slide, st, ctx, bv)
    if k != 1.0:
        import canvas_engine as ce
        els = ce.transform_elements(els, k, dx=body["x"], dy=body["y"])
    els = els + common_parts(slide, st, ctx, body)
    # 形トークン radius.box（classic は 0 = 変化なし）。提案書系は全部の箱、kpi / chart は結論帯だけ（本体は自前の角丸）
    round_boxes(els, ctx.radius("box"), only_names=None if t in PROPOSAL_TYPES else ("結論",))
    soft_shadows(els, st, ctx, t)
    return els


# soft の影（形トークン shadow.card）を付ける箱の名前。タイプ → 要素名の正規表現（kpi のタイル・summary の箱）。classic は none で何も変わらない
SHADOW_BOXES = {"kpi": r"^タイル\d+$", "summary": r"^要点\d+$"}


def soft_shadows(els: list, st: dict, ctx: Ctx, t: str) -> list:
    """本体の領域（st.body.shadow が "soft"）に従い、kpi のタイル・summary の箱に影を付ける（要素を直接書き換える）。"""
    import re
    pat = SHADOW_BOXES.get(t)
    sh = shp.shadow_params(ctx.tokens, (st.get("body") or {}).get("shadow")) if pat else {}
    if not sh:
        return els
    spec = {"dx": sh["dx"], "dy": sh["dy"], "blur": sh["blur"], "color": {"color": shp.SHADOW_COLOR, "alpha": sh["alpha"]}}
    for e in els:
        if e.get("fill") and re.match(pat, str(e.get("name", ""))):
            e["shadow"] = dict(spec)
    return els


def validate(slide: dict, i: int, fail, warn) -> None:
    """スキーマ的な誤りは fail、詰め込みすぎは warn。"""
    t = slide.get("type")
    where = f"{i + 1}枚目（type={t}）"
    for path, spec in icon_specs(slide):
        if not ie.resolve(spec):
            warn(f"{where}: {path} '{spec}' に合うアイコンがありません（tools/icon_engine.py --list で一覧を確認）")
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
    elif t == "house":
        if not isinstance(slide.get("pillars"), list) or not slide["pillars"]:
            fail(f"{where}: pillars（柱の配列）が必要です")
        if len(slide["pillars"]) > 5:
            warn(f"{where}: 柱が{len(slide['pillars'])}本あります（3〜4本が目安）")
    elif t == "cycle":
        stages = slide.get("stages")
        if not isinstance(stages, list) or len(stages) < 3:
            fail(f"{where}: stages（3つ以上の段の配列）が必要です")
        if len(stages) > 6:
            warn(f"{where}: 段が{len(stages)}つあります（3〜6つが目安）")
    elif t == "kpi_tree":
        br = slide.get("branches")
        if not slide.get("root") or not isinstance(br, list) or not br:
            fail(f"{where}: root（目標）と branches（[{{title, kpis}}] の配列）が必要です")
        n = sum(max(len(b.get("kpis", []) or []), 1) for b in br if isinstance(b, dict))
        if n > 7:
            warn(f"{where}: KPI が{n}行あります（6行以内が目安）")
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
            parent_of = {n["id"]: n.get("parent") for n in s.get("nodes", []) or []}
            for nid in parent_of:
                seen_chain, cur = {nid}, parent_of.get(nid)
                while cur:
                    if cur in seen_chain:
                        fail(f"{where}: node '{nid}' の parent をたどると自分自身に戻ります（循環）"
                             f" → parent は上位のノードの id を指し、自分や子孫を指さないようにする")
                    seen_chain.add(cur)
                    cur = parent_of.get(cur)
        for ln in slide.get("links", []) or []:
            if ln.get("from") not in ids or ln.get("to") not in ids:
                fail(f"{where}: links の from / to '{ln.get('from')}' → '{ln.get('to')}' が nodes にありません")


# ---------------------------------------------------------------------------
# 登録表への登録（engine_registry）。新しい A 型タイプはエンジンの末尾で同じように register する
# ---------------------------------------------------------------------------

for _t, _fn in LAYOUTS.items():
    engine_registry.register(_t, _fn, validate, chrome=(_t != "statement"))
del _t, _fn

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck.json → HTML / PPTX ビルダー v2（パラメーター駆動）。

使い方:
    python3 tools/build_deck.py decks/<デッキ名>          # HTML + PPTX
    python3 tools/build_deck.py decks/<デッキ名> --html   # HTML のみ
    python3 tools/build_deck.py decks/<デッキ名> --pptx   # PPTX のみ

設計:
- 仮想キャンバス 1280x720px。全オブジェクトの位置・サイズ・フォント・色を px で持つ
- 解決順: templates/layouts/<layout>.json の既定値
          ← deck.meta.layout_overrides（デッキ全体の調整）
          ← slides[i].style（スライド個別の微修正）
- HTML は px をそのまま使用、PPTX は 96dpi 換算（px/96 インチ、フォント px*0.75 pt）
  なので両形式で座標・サイズが一致する
- スキーマは docs/deck-schema.md を参照

注意: PPTX にはスピーカーノートを出力しない（python-pptx の notes_slide は
macOS Keynote の互換性を壊す既知問題があるため）。notes は HTML でのみ表示される。
"""

import argparse
import base64
import copy
import html as html_mod
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
CANVAS_W, CANVAS_H = 1280, 720


# ---------------------------------------------------------------------------
# 読み込みとスタイル解決
# ---------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        sys.exit(f"error: {path} が見つかりません")
    return json.loads(path.read_text(encoding="utf-8"))


def theme_dirs(deck_dir: Path):
    """テーマの探索ディレクトリを優先順に返す。
    1. 環境変数 SLIDE_DECK_THEMES（複数可・OS区切り）… ユーザー追加テーマ置き場
    2. <deck_dir>/themes/                           … デッキ／プロジェクト同梱テーマ
    3. 同梱テーマ（templates/themes/）              … default・accenture-purple 等
    先に見つかったものが勝つ。プラグイン更新で消したくないテーマは 1 か 2 に置く。"""
    dirs = []
    env = os.environ.get("SLIDE_DECK_THEMES")
    if env:
        dirs += [Path(p) for p in env.split(os.pathsep) if p.strip()]
    if deck_dir is not None:
        dirs.append(Path(deck_dir) / "themes")
    dirs.append(ROOT / "templates" / "themes")
    return dirs


def load_theme(name: str, dirs, _seen=None):
    """テーマを解決して返す。default.json（または extends 先）をベースにマージするため、
    新しいテーマは上書きしたいトークンだけ書けばよい。`extends` を指定すると任意のテーマを
    親にできる（未指定なら default が親）。探索は theme_dirs() の順。"""
    _seen = _seen or []
    if name in _seen:
        sys.exit(f"error: テーマの extends が循環しています: {' -> '.join(_seen + [name])}")
    path = next((d / f"{name}.json" for d in dirs if (d / f"{name}.json").exists()), None)
    if path is None:
        searched = ", ".join(str(d) for d in dirs)
        sys.exit(f"error: テーマ '{name}' が見つかりません（探索: {searched}）")
    data = load_json(path)
    parent = data.get("extends") or (None if name == "default" else "default")
    if parent:
        data = deep_merge(load_theme(parent, dirs, _seen + [name]), data)
    data["name"] = name
    return data


def load_deck(deck_dir: Path):
    deck = load_json(deck_dir / "deck.json")
    meta = deck.get("meta", {})
    theme = load_theme(meta.get("theme", "default"), theme_dirs(deck_dir))
    layout = load_json(ROOT / "templates" / "layouts" / f"{meta.get('layout', 'default')}.json")
    return deck, theme, layout


def deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if k in out else copy.deepcopy(v)
    return out


def resolve_style(layout, deck, slide):
    t = slide["type"]
    types = layout.get("types", {})
    if t not in types:
        sys.exit(f"error: 未知のスライドタイプ: {t}")
    st = types[t]
    st = deep_merge(st, deck.get("meta", {}).get("layout_overrides", {}).get(t, {}))
    st = deep_merge(st, slide.get("style", {}))
    return st


def col(theme, c):
    """テーマトークン名 → hex。hex 直書きはそのまま返す。"""
    return theme["colors"].get(c, c)


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
                kids.append({"text": c} if isinstance(c, str) else dict(c))
            d["children"] = kids
            out.append(d)
    return out


def _route_edge(A, B):
    """2ノード間の直交ポリライン経路と、ラベル配置座標を返す。"""
    dx = B["cx"] - A["cx"]; dy = B["cy"] - A["cy"]
    if abs(A["cx"] - B["cx"]) < 2 and abs(dy) >= 1:
        # ほぼ同列：垂直に接続
        if dy > 0:
            p = [(A["cx"], A["y"] + A["h"]), (B["cx"], B["y"])]
        else:
            p = [(A["cx"], A["y"]), (B["cx"], B["y"] + B["h"])]
        return p, (A["cx"] + 8, (A["cy"] + B["cy"]) / 2)
    if abs(dy) < 1:
        # 同一レーン：水平に接続
        if dx >= 0:
            p = [(A["x"] + A["w"], A["cy"]), (B["x"], B["cy"])]
        else:
            p = [(A["x"], A["cy"]), (B["x"] + B["w"], B["cy"])]
        return p, ((p[0][0] + p[1][0]) / 2, A["cy"] - 12)
    # レーンをまたぐ：H-V-H の Z 経路
    if dx >= 0:
        sx = A["x"] + A["w"]; ex = B["x"]
    else:
        sx = A["x"]; ex = B["x"] + B["w"]
    midx = (sx + ex) / 2
    p = [(sx, A["cy"]), (midx, A["cy"]), (midx, B["cy"]), (ex, B["cy"])]
    return p, (midx + 8, (A["cy"] + B["cy"]) / 2)


def swimlane_geometry(slide, st):
    """スイムレーン図の全要素（レーン・グループ・工程・ノード・エッジ経路）の座標を計算する。
    HTML と PPTX で同一のジオメトリを共有し、見た目を一致させる。"""
    f = st["flow"]
    lanes = slide.get("lanes", [])
    n = max(1, len(lanes))
    has_group = any(l.get("group") for l in lanes)
    g1 = f.get("g1_w", 34) if has_group else 0
    g2 = f.get("g2_w", 96)
    label_w = g1 + g2
    phases = slide.get("phases") or []
    phase_h = f.get("phase_h", 30) if any(phases) else 0
    content_x = f["x"] + label_w
    content_w = f["w"] - label_w
    top = f["y"] + phase_h
    avail_h = f["h"] - phase_h
    row_h = avail_h / n
    maxcol = 0
    for nd in slide.get("nodes", []):
        maxcol = max(maxcol, nd.get("col", 0))
    cols = max(1, slide.get("cols") or (maxcol + 1))
    col_w = content_w / cols
    lane_boxes = []
    for i, l in enumerate(lanes):
        y = top + i * row_h
        lane_boxes.append({"label": l.get("name", l.get("label", "")),
                           "x": f["x"] + g1, "y": y, "w": g2, "h": row_h,
                           "band_x": content_x, "band_y": y, "band_w": content_w, "band_h": row_h,
                           "alt": i % 2})
    groups = []
    if has_group:
        i = 0
        while i < n:
            gname = lanes[i].get("group")
            j = i
            while j + 1 < n and lanes[j + 1].get("group") == gname and gname is not None:
                j += 1
            if gname:
                groups.append({"label": gname, "x": f["x"], "y": top + i * row_h,
                               "w": g1, "h": (j - i + 1) * row_h})
            i = j + 1
    phase_boxes = []
    for c, ph in enumerate(phases):
        if ph:
            phase_boxes.append({"label": ph, "x": content_x + c * col_w, "y": f["y"], "w": col_w, "h": phase_h})
    node_map = {}
    for nd in slide.get("nodes", []):
        c = nd.get("col", 0); L = nd.get("lane", 0)
        cx = content_x + (c + 0.5) * col_w
        cy = top + (L + 0.5) * row_h
        shape = nd.get("shape", "task")
        if shape == "decision":
            w = min(col_w, row_h) * 0.66; h = w
        elif shape in ("terminal", "connector"):
            w = col_w * f.get("node_wr", 0.72); h = row_h * 0.42
        elif shape == "marker":
            w = min(col_w, row_h) * 0.34; h = w
        elif shape == "mail":
            w = min(col_w, row_h) * 0.44; h = w * 0.72
        elif shape == "io":
            w = col_w * 0.88; h = row_h * 0.92
        else:  # task, system
            w = col_w * f.get("node_wr", 0.72); h = row_h * f.get("node_hr", 0.52)
        node_map[nd["id"]] = {"shape": shape, "variant": nd.get("variant"), "kind": nd.get("kind"),
                              "text": nd.get("text", ""),
                              "cx": cx, "cy": cy, "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
                              "input": nd.get("input"), "output": nd.get("output"), "loop": nd.get("loop")}
    edges = []
    for e in slide.get("edges", []):
        A = node_map.get(e["from"]); B = node_map.get(e["to"])
        if not A or not B:
            continue
        pts, lp = _route_edge(A, B)
        edges.append({"points": pts, "label": e.get("label", ""), "label_pos": lp,
                      "style": e.get("style", "solid")})
    return {"flow": f, "content_x": content_x, "content_w": content_w, "top": top,
            "row_h": row_h, "col_w": col_w, "cols": cols, "lanes": lane_boxes,
            "groups": groups, "phases": phase_boxes, "nodes": node_map, "edges": edges}


# スイムレーンの凡例エントリ（業務フロー標準記号）: (shape, variant/kind, ラベル, 説明)
SWIMLANE_LEGEND = [
    ("task", "onpf", "作業（オンラインPF）", "PF 上で実施する作業"),
    ("task", "onother", "作業（PF以外）", "他システムで実施する作業"),
    ("task", "offline", "作業（オフライン）", "オフラインで実施する作業"),
    ("system", None, "システム/サービス", "利用するシステム・サービス名"),
    ("decision", None, "分岐条件", "フロー内で分岐する条件"),
    ("io", None, "成果物（input/output）", "作業の入力・出力ドキュメント"),
    ("marker", "start", "フロー開始", "フローの起点"),
    ("marker", "end", "フロー終了", "フローの終点"),
    ("marker", "mid", "フロー途中", "フロー途中の状態"),
    ("terminal", "prev", "前ページより", "前ページからの続き"),
    ("terminal", "next", "次ページへ", "後続ページへ続く"),
    ("connector", None, "遷移先（分岐）", "複数の後続業務への遷移先"),
    ("mail", None, "メール配信", "メール通知の発生"),
    ("flow", "solid", "作業の流れ", "実線＝作業の流れ"),
    ("flow", "dashed", "システム操作", "破線＝システム操作"),
]


def _sw_node_html(nd, theme, f):
    """スイムレーンのノード1個を HTML で描く（フロー本体・凡例ページ共通）。"""
    def C(tok):
        return col(theme, tok)
    x, y, w, h = nd["x"], nd["y"], nd["w"], nd["h"]
    box = f'position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;'
    shape = nd["shape"]; text = esc(nd.get("text", "")); ns = f.get("node_size", 14)
    center = ('display:flex;align-items:center;justify-content:center;text-align:center;'
              'box-sizing:border-box;line-height:1.15;padding:2px;')
    if shape == "decision":
        return (f'<div style="{box}">'
                f'<div style="position:absolute;inset:0;background:{C(f.get("decision_fill","on_primary_soft"))};'
                f'border:2px solid {C(f.get("decision_border","accent"))};transform:rotate(45deg);"></div>'
                f'<div style="position:absolute;inset:0;{center}font-size:{ns-2}px;'
                f'color:{C(f.get("decision_color","primary"))};">{text}</div></div>')
    if shape == "terminal":
        return (f'<div style="{box}{center}font-size:{ns-2}px;background:{C(f.get("terminal_fill","surface"))};'
                f'border:1.5px solid {C(f.get("terminal_border","muted"))};border-radius:{h/2:.0f}px;'
                f'color:{C(f.get("terminal_color","muted"))};">{text}</div>')
    if shape == "connector":
        return (f'<div style="{box}{center}font-size:{ns-3}px;background:{C(f.get("connector_fill","surface"))};'
                f'color:{C(f.get("connector_color","text"))};clip-path:polygon(0 0,72% 0,100% 50%,72% 100%,0 100%);">{text}</div>')
    if shape == "marker":
        kind = nd.get("kind", "mid")
        mc = {"start": f.get("marker_start", "accent"), "end": f.get("marker_end", "primary"),
              "mid": f.get("marker_mid", "#E6B800")}.get(kind, f.get("marker_mid", "#E6B800"))
        return f'<div style="{box}background:{C(mc)};border-radius:50%;border:1.5px solid {C("background")};"></div>'
    if shape == "mail":
        return (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" style="{box}">'
                f'<rect x="1" y="1" width="{w-2:.0f}" height="{h-2:.0f}" fill="{C("background")}" '
                f'stroke="{C(f.get("edge_color","text"))}" stroke-width="1.5"/>'
                f'<path d="M1,1 L{w/2:.0f},{h*0.55:.0f} L{w-1:.0f},1" fill="none" '
                f'stroke="{C(f.get("edge_color","text"))}" stroke-width="1.5"/></svg>')
    if shape == "io":
        half = (w - 2) / 2
        cells = []
        for key, lbl in (("input", "input"), ("output", "output")):
            vals = nd.get(key) or []
            lis = "".join(f'<div style="margin-top:3px;">{esc(v)}</div>' for v in vals)
            cells.append(f'<div style="width:{half:.0f}px;padding:6px;box-sizing:border-box;'
                         f'font-size:{f.get("io_size",11)}px;color:{C(f.get("io_color","text"))};line-height:1.2;">'
                         f'<div style="font-weight:700;color:{C(f.get("io_head_color","accent"))};">{lbl}</div>{lis}</div>')
        return (f'<div style="{box}display:flex;background:{C(f.get("io_fill","on_primary_soft"))};'
                f'border:1px solid {C(f.get("io_border","accent"))};border-radius:8px;box-sizing:border-box;overflow:hidden;">'
                f'{cells[0]}<div style="width:1px;background:rgba(0,0,0,0.12);"></div>{cells[1]}</div>')
    if shape == "system":
        return (f'<div style="{box}{center}font-size:{ns}px;background:{C(f.get("system_fill","surface"))};'
                f'border:1.5px solid {C(f.get("system_border","muted"))};color:{C(f.get("system_color","text"))};">{text}</div>')
    # task (+variant)
    variant = nd.get("variant") or "onother"
    vmap = {
        "onpf": (f.get("task_onpf_fill", "on_primary_soft"), f.get("task_border", "accent"), f.get("task_onpf_color", "primary")),
        "onother": (f.get("task_onother_fill", "background"), f.get("task_border", "accent"), f.get("task_color", "text")),
        "offline": (f.get("task_offline_fill", "surface"), f.get("task_offline_border", "muted"), f.get("task_color", "text")),
    }
    fill_t, bord_t, col_t = vmap.get(variant, vmap["onother"])
    loop = ""
    if nd.get("loop"):
        loop = (f'<span style="position:absolute;left:-6px;top:-8px;color:{C("accent")};'
                f'font-size:16px;font-weight:700;">&#8635;</span>')
    return (f'<div style="{box}{center}font-size:{ns}px;background:{C(fill_t)};'
            f'border:2px solid {C(bord_t)};border-radius:{f.get("node_radius",8)}px;color:{C(col_t)};">{text}{loop}</div>')


def _legend_sym_size(shape):
    return {"decision": (26, 26), "marker": (16, 16), "mail": (30, 20), "terminal": (74, 24),
            "connector": (66, 26), "io": (78, 30), "flow": (54, 0)}.get(shape, (60, 26))


def _legend_symbol_html(shape, vk, x, cy, sym_w, theme, f):
    """凡例の1シンボルを HTML で描く（中心 x..x+sym_w に配置）。"""
    w, h = _legend_sym_size(shape)
    cx = x + sym_w / 2
    if shape == "flow":
        dash = ' stroke-dasharray="7,5"' if vk == "dashed" else ""
        ec = col(theme, f.get("edge_color", "text"))
        return (f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;'
                f'pointer-events:none;" viewBox="0 0 {CANVAS_W} {CANVAS_H}">'
                f'<defs><marker id="lg-arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" '
                f'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L9,4 L0,8 z" fill="{ec}"/></marker></defs>'
                f'<line x1="{cx-w/2:.0f}" y1="{cy:.0f}" x2="{cx+w/2:.0f}" y2="{cy:.0f}" stroke="{ec}" '
                f'stroke-width="2"{dash} marker-end="url(#lg-arrow)"/></svg>')
    nd = {"shape": shape, "variant": (vk if shape == "task" else None),
          "kind": (vk if shape == "marker" else None), "text": "",
          "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
          "input": (["…"] if shape == "io" else None), "output": (["…"] if shape == "io" else None),
          "loop": None}
    return _sw_node_html(nd, theme, f)


def expand_slides(deck, layout):
    """ビルド前処理: agenda のあふれを複数ページに分割し、swimlane の直前に凡例ページを挿入する。"""
    out = []
    for s in deck.get("slides", []):
        t = s.get("type")
        if t == "swimlane" and s.get("legend", True):
            leg = {"type": "swimlane_legend",
                   "title": s.get("legend_title", "凡例（スイムレーン記号）"),
                   "eyebrow": s.get("legend_eyebrow", s.get("eyebrow"))}
            if "legend_items" in s:
                leg["items"] = s["legend_items"]
            out.append(leg)
            out.append(s)
        elif t == "agenda":
            items = s.get("items", [])
            st = resolve_style(layout, deck, s)
            b = st.get("body", {})
            pitch = b.get("row_h", 44) + b.get("gap", 10)
            R = max(1, int(b.get("h", 452) // pitch))
            cap = R * b.get("max_cols", 2)
            if len(items) > cap:
                for p in range(0, len(items), cap):
                    ns = dict(s)
                    ns["items"] = items[p:p + cap]
                    ns["num_start"] = p
                    if p > 0:
                        ns["title"] = s.get("title", "") + "（続き）"
                    out.append(ns)
            else:
                out.append(s)
        else:
            out.append(s)
    d = dict(deck); d["slides"] = out
    return d


def fit_code_size(code: str, r: dict):
    """コード領域に収まるフォントサイズを計算（HTML/PPTX 共通ロジック）。"""
    lines = code.splitlines() or [""]
    size = r["size"]
    lh = r["line_height"]
    avail = r["h"] - 2 * r["pad"]
    while size > r.get("min_size", 12) and len(lines) * size * lh > avail:
        size -= 1
    return size, lines


def is_http_url(value) -> bool:
    """Return True only when the entire table-cell value is an HTTP(S) URL."""
    return bool(re.fullmatch(r"https?://\S+", str(value)))


def table_cell_parts(value):
    """Normalize a table cell into visible text and an optional external URL."""
    if isinstance(value, dict):
        text = str(value.get("text", ""))
        url = value.get("url")
        return text, str(url) if url and is_http_url(url) else None
    text = str(value)
    return text, text if is_http_url(text) else None


def svg_size(svg_text: str):
    """SVG の描画サイズを viewBox / width / height 属性から取得する。"""
    m = re.search(
        r'viewBox\s*=\s*"\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"',
        svg_text,
    )
    if m:
        return float(m.group(1)), float(m.group(2))
    wm = re.search(r'<svg[^>]*?\swidth\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    hm = re.search(r'<svg[^>]*?\sheight\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    if wm and hm:
        return float(wm.group(1)), float(hm.group(1))
    return 1136.0, 440.0


def svg_to_png(svg_path: Path, out_png: Path):
    """SVG を透過 PNG にラスタライズ（PPTX 埋め込み用、2x 解像度）。"""
    from playwright.sync_api import sync_playwright

    svg_text = svg_path.read_text(encoding="utf-8")
    w, h = svg_size(svg_text)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": max(1, int(w)), "height": max(1, int(h))},
            device_scale_factor=2,
        )
        page.set_content(
            "<!doctype html><style>html,body{margin:0;background:transparent}"
            "svg{display:block}</style>" + svg_text
        )
        page.wait_for_timeout(120)
        page.screenshot(path=str(out_png), omit_background=True,
                        clip={"x": 0, "y": 0, "width": w, "height": h})
        browser.close()


def flip_regions(st: dict, keys) -> dict:
    """image_side: "left" 用に、指定領域の x をキャンバス中心で左右反転する。"""
    out = copy.deepcopy(st)
    for k in keys:
        r = out.get(k)
        if isinstance(r, dict) and "x" in r and "w" in r:
            r["x"] = CANVAS_W - r["x"] - r["w"]
    return out


def image_source(deck_dir: Path, rel_path: str, for_pptx: bool) -> Path:
    """image スライドの実ファイルを解決。PPTX 用に SVG は PNG 化してキャッシュする。"""
    img_path = deck_dir / rel_path
    if for_pptx and img_path.suffix.lower() == ".svg":
        cache = deck_dir / "build" / ".svg-cache"
        cache.mkdir(parents=True, exist_ok=True)
        png = cache / (img_path.stem + ".png")
        if not png.exists() or png.stat().st_mtime < img_path.stat().st_mtime:
            svg_to_png(img_path, png)
        return png
    return img_path


# ---------------------------------------------------------------------------
# HTML ビルド
# ---------------------------------------------------------------------------

def esc(s):
    return html_mod.escape(str(s), quote=True)


def pos(r, extra=""):
    s = (f"position:absolute;left:{r['x']}px;top:{r['y']}px;width:{r['w']}px;")
    if "h" in r:
        s += f"height:{r['h']}px;"
    return s + extra


def text_style(r, theme):
    s = f"font-size:{r['size']}px;color:{col(theme, r.get('color', 'text'))};"
    if r.get("bold"):
        s += "font-weight:700;"
    if r.get("align"):
        s += f"text-align:{r['align']};"
    if r.get("line_height"):
        s += f"line-height:{r['line_height']};"
    return s


def div(r, theme, inner, extra=""):
    return f'<div style="{pos(r)}{text_style(r, theme)}{extra}">{inner}</div>'


def rect(r, theme, extra=""):
    fill = col(theme, r.get("fill", "accent"))
    radius = f"border-radius:{r['radius']}px;" if r.get("radius") else ""
    return f'<div style="{pos(r)}background:{fill};{radius}{extra}"></div>'


def bullets_html(items, r, theme):
    mk = col(theme, r.get("marker_color", "accent"))
    parts = [
        f'<ul style="margin:0;padding-left:{r["indent"]}px;list-style:disc;'
        f'font-size:{r["size"]}px;line-height:{r["line_height"]};'
        f'color:{col(theme, r["color"])};--mk:{mk};">'
    ]
    for it in items:
        li = f'font-size:{it["size"]}px;' if it.get("size") else ""
        li += f'color:{col(theme, it["color"])};' if it.get("color") else ""
        li += "font-weight:700;" if it.get("bold") else ""
        parts.append(f'<li style="margin-bottom:{r["gap"]}px;{li}">{esc(it["text"])}')
        if it["children"]:
            parts.append(
                f'<ul style="margin:{r["child_gap"]}px 0 0;padding-left:{r["indent"] - 6}px;'
                f'list-style:circle;font-size:{r["child_size"]}px;'
                f'color:{col(theme, r["child_color"])};">'
            )
            for c in it["children"]:
                cs = f'font-size:{c["size"]}px;' if c.get("size") else ""
                cs += f'color:{col(theme, c["color"])};' if c.get("color") else ""
                parts.append(f'<li style="margin-bottom:{r["child_gap"]}px;{cs}">{esc(c["text"])}</li>')
            parts.append("</ul>")
        parts.append("</li>")
    parts.append("</ul>")
    return "".join(parts)


def footer_html(st, deck, theme, page, total):
    out = ""
    if "footer_l" in st:
        out += div(st["footer_l"], theme, esc(deck["meta"].get("title", "")))
    if "footer_r" in st:
        out += div(st["footer_r"], theme, esc(st["footer_r"].get("text") or f"{page} / {total}"))
    return out


def html_slide_body(slide, st, deck, theme, deck_dir, page, total):
    t = slide["type"]
    fonts = theme["fonts"]
    parts = []

    def chrome():
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"])))
        parts.append(div(st["title"], theme, esc(slide.get("title", ""))))
        parts.append(rect(st["rule"], theme))
        if slide.get("lead") and "lead" in st:
            parts.append(div(st["lead"], theme, esc(slide["lead"])))
        parts.append(footer_html(st, deck, theme, page, total))

    if t == "title":
        parts.append(rect(st["bar"], theme))
        parts.append(div(st["title"], theme, esc(slide.get("title", ""))))
        if slide.get("subtitle"):
            parts.append(div(st["subtitle"], theme, esc(slide["subtitle"])))
        if slide.get("meta"):
            parts.append(div(st["meta"], theme, esc(slide["meta"])))

    elif t == "section":
        if slide.get("number"):
            parts.append(div(st["number"], theme, esc(slide["number"])))
        parts.append(div(st["title"], theme, esc(slide.get("title", ""))))
        parts.append(rect(st["rule"], theme))
        if slide.get("subtitle"):
            parts.append(div(st["subtitle"], theme, esc(slide["subtitle"])))

    elif t == "bullets":
        chrome()
        parts.append(
            f'<div style="{pos(st["body"])}">'
            + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
            + "</div>"
        )

    elif t == "two_column":
        chrome()
        for side in ("left", "right"):
            box = st[side]
            colc = slide.get(side, {})
            radius = f"border-radius:{box.get('radius', 0)}px;"
            inner = ""
            hd = st["col_heading"]
            if colc.get("heading"):
                inner += (
                    f'<div style="font-size:{hd["size"]}px;color:{col(theme, hd["color"])};'
                    f'font-weight:700;margin-bottom:{hd["gap_below"]}px;">{esc(colc["heading"])}</div>'
                )
            inner += bullets_html(norm_items(colc.get("bullets")), st["col_body"], theme)
            parts.append(
                f'<div style="{pos(box)}background:{col(theme, box["fill"])};{radius}'
                f'padding:{box["pad"]}px;box-sizing:border-box;overflow:hidden;">{inner}</div>'
            )

    elif t == "table":
        chrome()
        tr = st["table"]
        cols = slide.get("columns", [])
        widths = tr.get("col_widths")
        colgroup = ""
        if widths:
            total_w = sum(widths)
            colgroup = "<colgroup>" + "".join(
                f'<col style="width:{w / total_w * 100:.2f}%;">' for w in widths
            ) + "</colgroup>"
        cells_pad = f"padding:{tr['pad_y']}px {tr['pad_x']}px;"
        html = [
            f'<div style="{pos(tr)}"><table style="width:100%;border-collapse:collapse;'
            f'line-height:{tr["line_height"]};">{colgroup}<thead><tr>'
        ]
        for c in cols:
            html.append(
                f'<th style="background:{col(theme, tr["header_fill"])};'
                f'color:{col(theme, tr["header_color"])};font-size:{tr["header_size"]}px;'
                f'text-align:left;font-weight:600;height:{tr["header_h"]}px;'
                f'{cells_pad}box-sizing:border-box;">{esc(c)}</th>'
            )
        html.append("</tr></thead><tbody>")
        row_fills = tr.get("row_fills", {})
        for i, row in enumerate(slide.get("rows", [])):
            if str(i) in row_fills:
                bg = col(theme, row_fills[str(i)])
            else:
                bg = col(theme, tr["row_alt_fill"]) if i % 2 else col(theme, "background")
            html.append("<tr>")
            for cell in row:
                visible_text, cell_url = table_cell_parts(cell)
                cell_text = esc(visible_text)
                if cell_url:
                    cell_text = (
                        f'<a href="{esc(cell_url)}" target="_blank" rel="noopener noreferrer" '
                        'style="color:inherit;text-decoration:underline;'
                        f'text-underline-offset:2px;">{cell_text}</a>'
                    )
                html.append(
                    f'<td style="background:{bg};color:{col(theme, tr["cell_color"])};'
                    f'font-size:{tr["cell_size"]}px;height:{tr["row_h"]}px;{cells_pad}'
                    f'box-sizing:border-box;border-bottom:1px solid rgba(0,0,0,0.08);">{cell_text}</td>'
                )
            html.append("</tr>")
        html.append("</tbody></table></div>")
        parts.append("".join(html))

    elif t == "code":
        chrome()
        r = st["code"]
        size, _lines = fit_code_size(slide.get("code", ""), r)
        radius = f"border-radius:{r.get('radius', 0)}px;"
        parts.append(
            f'<pre style="{pos(r)}margin:0;background:{col(theme, r["fill"])};{radius}'
            f'padding:{r["pad"]}px;box-sizing:border-box;overflow:hidden;">'
            f'<code style="font-family:\'{fonts["code"]}\',monospace;font-size:{size}px;'
            f'line-height:{r["line_height"]};color:{col(theme, r["color"])};">'
            f"{esc(slide.get('code', ''))}</code></pre>"
        )

    elif t == "quote":
        parts.append(div(st["mark"], theme, "“"))
        parts.append(div(st["text"], theme, esc(slide.get("text", ""))))
        if slide.get("attribution"):
            parts.append(div(st["attribution"], theme, "— " + esc(slide["attribution"])))

    elif t == "image":
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"])))
        if slide.get("title"):
            parts.append(div(st["title"], theme, esc(slide["title"])))
            parts.append(rect(st["rule"], theme))
        r = st["img"]
        img_path = deck_dir / slide["path"]
        mime = mimetypes.guess_type(img_path.name)[0] or "image/png"
        data = base64.b64encode(img_path.read_bytes()).decode()
        parts.append(
            f'<div style="{pos(r)}"><img src="data:{mime};base64,{data}" alt="" '
            f'style="width:100%;height:100%;object-fit:contain;"></div>'
        )
        if slide.get("caption"):
            parts.append(div(st["caption"], theme, esc(slide["caption"])))
        parts.append(footer_html(st, deck, theme, page, total))

    elif t == "image_text":
        if slide.get("image_side") == "left":
            st = flip_regions(st, ("body", "img", "caption"))
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"])))
        parts.append(div(st["title"], theme, esc(slide.get("title", ""))))
        parts.append(rect(st["rule"], theme))
        if slide.get("punch"):
            parts.append(div(st["punch"], theme, esc(slide["punch"])))
        parts.append(
            f'<div style="{pos(st["body"])}">'
            + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
            + "</div>"
        )
        r = st["img"]
        img_path = deck_dir / slide["path"]
        mime = mimetypes.guess_type(img_path.name)[0] or "image/png"
        data = base64.b64encode(img_path.read_bytes()).decode()
        parts.append(
            f'<div style="{pos(r)}"><img src="data:{mime};base64,{data}" alt="" '
            f'style="width:100%;height:100%;object-fit:contain;"></div>'
        )
        if slide.get("caption"):
            parts.append(div(st["caption"], theme, esc(slide["caption"])))
        parts.append(footer_html(st, deck, theme, page, total))

    elif t == "closing":
        parts.append(div(st["title"], theme, esc(slide.get("title", ""))))
        parts.append(rect(st["rule"], theme))
        if slide.get("bullets"):
            parts.append(
                f'<div style="{pos(st["body"])}">'
                + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
                + "</div>"
            )
        if slide.get("message"):
            parts.append(div(st["message"], theme, esc(slide["message"])))

    elif t == "agenda":
        chrome()
        b = st["body"]
        items = norm_items(slide.get("items", []))
        num_start = slide.get("num_start", 0)
        row_h = b.get("row_h", 44); gap = b.get("gap", 10); num_w = b.get("num_w", 52)
        col_gap = b.get("col_gap", 56); pitch = row_h + gap
        R = max(1, int(b["h"] // pitch))
        N = len(items)
        cols = 1 if N <= R else min(b.get("max_cols", 2), -(-N // R))
        rows = -(-N // cols)
        col_w = (b["w"] - (cols - 1) * col_gap) / cols
        noff = (row_h - b.get("num_size", 24)) / 2
        toff = (row_h - b.get("text_size", 20)) / 2
        for i, it in enumerate(items):
            c = i // rows; r = i % rows
            x = b["x"] + c * (col_w + col_gap); y = b["y"] + r * pitch
            active = it.get("active")
            if active:
                parts.append(f'<div style="{pos({"x": x-14, "y": y-3, "w": col_w+18, "h": row_h+6})}'
                             f'background:{col(theme, b.get("active_fill","surface"))};border-radius:8px;"></div>')
            parts.append(div({"x": x, "y": y+noff, "w": num_w, "h": row_h, "size": b.get("num_size", 24),
                              "color": b.get("num_color", "accent"), "bold": True, "line_height": 1.1},
                             theme, f"{num_start+i+1:02d}"))
            parts.append(div({"x": x+num_w, "y": y+toff, "w": col_w-num_w, "h": row_h, "size": b.get("text_size", 20),
                              "color": (b.get("active_color", "primary") if active else b.get("text_color", "text")),
                              "bold": bool(active), "line_height": 1.2}, theme, esc(it["text"])))

    elif t == "steps":
        chrome()
        b = st["body"]; steps = slide.get("steps", [])
        n = max(1, len(steps)); gap = b.get("gap", 20)
        card_w = (b["w"] - (n-1)*gap) / n
        header_h = b.get("header_h", 60); pad = b.get("pad", 16); radius = b.get("radius", 12)
        for i, step in enumerate(steps):
            x = b["x"] + i * (card_w + gap)
            parts.append(f'<div style="{pos({"x": x, "y": b["y"], "w": card_w, "h": b["h"]})}'
                         f'background:{col(theme, b.get("card_fill","surface"))};border-radius:{radius}px;"></div>')
            parts.append(f'<div style="{pos({"x": x, "y": b["y"], "w": card_w, "h": header_h})}'
                         f'background:{col(theme, b.get("header_fill","primary"))};'
                         f'border-radius:{radius}px {radius}px 0 0;"></div>')
            parts.append(div({"x": x+pad, "y": b["y"]+9, "w": card_w-2*pad, "h": 18, "size": 13,
                              "color": b.get("num_color", "accent"), "bold": True}, theme, f"STEP {i+1}"))
            parts.append(div({"x": x+pad, "y": b["y"]+28, "w": card_w-2*pad, "h": header_h-26,
                              "size": b.get("label_size", 18), "color": b.get("header_color", "on_primary"),
                              "bold": True, "line_height": 1.15}, theme, esc(step.get("label", ""))))
            itemr = {"x": x+pad, "y": b["y"]+header_h+pad, "w": card_w-2*pad, "h": b["h"]-header_h-2*pad,
                     "size": b.get("item_size", 15), "gap": b.get("item_gap", 8), "color": b.get("item_color", "text"),
                     "line_height": 1.4, "marker_color": "accent", "child_size": 13, "child_color": "muted",
                     "indent": 16, "child_gap": 4}
            parts.append(f'<div style="{pos(itemr)}">'
                         + bullets_html(norm_items(step.get("items", [])), itemr, theme) + "</div>")
            if i < n-1:
                parts.append(div({"x": x+card_w, "y": b["y"]+b["h"]/2-18, "w": gap, "h": 36,
                                  "size": b.get("chevron_size", 28), "color": b.get("chevron_color", "accent"),
                                  "align": "center", "bold": True}, theme, "›"))

    elif t == "matrix":
        chrome()
        g = st["grid"]; ax = st.get("axis", {})
        gx, gy, gw, gh = g["x"], g["y"], g["w"], g["h"]
        gap = g.get("gap", 14); pad = g.get("pad", 18); radius = g.get("radius", 12)
        cw = (gw - gap) / 2; ch = (gh - gap) / 2
        quads = slide.get("quadrants", [])
        positions = [(gx, gy), (gx+cw+gap, gy), (gx, gy+ch+gap), (gx+cw+gap, gy+ch+gap)]
        for qi, (qx, qy) in enumerate(positions):
            q = quads[qi] if qi < len(quads) else {}
            hi = q.get("highlight")
            fill = col(theme, g.get("hi_fill", "on_primary_soft") if hi else g.get("fill", "surface"))
            parts.append(f'<div style="{pos({"x": qx, "y": qy, "w": cw, "h": ch})}'
                         f'background:{fill};border-radius:{radius}px;"></div>')
            parts.append(div({"x": qx+pad, "y": qy+pad, "w": cw-2*pad, "h": 26, "size": g.get("heading_size", 18),
                              "color": (g.get("hi_heading_color", "accent") if hi else g.get("heading_color", "primary")),
                              "bold": True, "line_height": 1.2}, theme, esc(q.get("heading", ""))))
            parts.append(div({"x": qx+pad, "y": qy+pad+30, "w": cw-2*pad, "h": ch-2*pad-30,
                              "size": g.get("body_size", 14), "color": g.get("body_color", "muted"),
                              "line_height": 1.4}, theme, esc(q.get("body", "")).replace("\n", "<br>")))
        xa = slide.get("x_axis", {}); ya = slide.get("y_axis", {})
        asize = ax.get("size", 15); acol = ax.get("color", "muted"); ncol = ax.get("name_color", "text")
        parts.append(div({"x": 72, "y": gy-30, "w": 360, "h": 22, "size": asize, "color": ncol, "bold": True},
                         theme, "▲ " + esc(ya.get("label", ""))))
        parts.append(div({"x": gx-96, "y": gy+6, "w": 88, "h": 22, "size": asize, "color": acol, "align": "right"}, theme, esc(ya.get("high", ""))))
        parts.append(div({"x": gx-96, "y": gy+gh-28, "w": 88, "h": 22, "size": asize, "color": acol, "align": "right"}, theme, esc(ya.get("low", ""))))
        parts.append(div({"x": gx, "y": gy+gh+30, "w": gw, "h": 22, "size": asize, "color": ncol, "align": "center", "bold": True},
                         theme, esc(xa.get("label", "")) + " ▶"))
        parts.append(div({"x": gx, "y": gy+gh+6, "w": 160, "h": 22, "size": asize, "color": acol}, theme, esc(xa.get("low", ""))))
        parts.append(div({"x": gx+gw-160, "y": gy+gh+6, "w": 160, "h": 22, "size": asize, "color": acol, "align": "right"}, theme, esc(xa.get("high", ""))))

    elif t == "cards":
        chrome()
        g = st["grid"]; cards = slide.get("cards", [])
        cols = max(1, slide.get("columns", g.get("cols", 3)))
        n = len(cards); rows = max(1, (n + cols - 1) // cols)
        gap = g.get("gap", 16); pad = g.get("pad", 18); radius = g.get("radius", 12)
        cw = (g["w"] - (cols-1)*gap) / cols; chh = (g["h"] - (rows-1)*gap) / rows
        for idx, card in enumerate(cards):
            rr = idx // cols; cc = idx % cols
            x = g["x"] + cc * (cw + gap); y = g["y"] + rr * (chh + gap)
            parts.append(f'<div style="{pos({"x": x, "y": y, "w": cw, "h": chh})}'
                         f'background:{col(theme, g.get("fill","surface"))};border-radius:{radius}px;"></div>')
            parts.append(div({"x": x+pad, "y": y+pad, "w": cw-2*pad, "h": 28, "size": g.get("heading_size", 19),
                              "color": g.get("heading_color", "primary"), "bold": True, "line_height": 1.2},
                             theme, esc(card.get("heading", ""))))
            yy = y + pad + 32
            if card.get("body"):
                parts.append(div({"x": x+pad, "y": yy, "w": cw-2*pad, "h": 44, "size": g.get("body_size", 15),
                                  "color": g.get("body_color", "text"), "line_height": 1.4}, theme,
                                 esc(card["body"]).replace("\n", "<br>")))
                yy += 48
            if card.get("items"):
                itemr = {"x": x+pad, "y": yy, "w": cw-2*pad, "h": chh-(yy-y)-pad, "size": g.get("item_size", 14),
                         "gap": g.get("item_gap", 6), "color": g.get("item_color", "muted"), "line_height": 1.35,
                         "marker_color": "accent", "child_size": 12, "child_color": "muted", "indent": 14, "child_gap": 4}
                parts.append(f'<div style="{pos(itemr)}">'
                             + bullets_html(norm_items(card["items"]), itemr, theme) + "</div>")

    elif t == "swimlane":
        chrome()
        f = st["flow"]
        geo = swimlane_geometry(slide, st)
        def cc(key, default):
            return col(theme, f.get(key, default))
        # lane bands (subtle stripes across full width)
        for ln in geo["lanes"]:
            bg = cc("lane_band_b", "surface") if ln["alt"] else col(theme, "background")
            parts.append(f'<div style="{pos({"x": f["x"], "y": ln["y"], "w": f["w"], "h": ln["h"]})}'
                         f'background:{bg};border-top:1px solid rgba(0,0,0,0.06);"></div>')
        # group boxes (Lv1, vertical text)
        for gp in geo["groups"]:
            parts.append(f'<div style="{pos(gp)}display:flex;align-items:center;justify-content:center;'
                         f'background:{cc("group_fill","primary")};box-sizing:border-box;">'
                         f'<span style="writing-mode:vertical-rl;text-orientation:mixed;'
                         f'color:{cc("group_color","on_primary")};font-weight:700;font-size:{f.get("group_size",13)}px;">'
                         f'{esc(gp["label"])}</span></div>')
        # lane labels (Lv2)
        for ln in geo["lanes"]:
            parts.append(f'<div style="{pos({"x": ln["x"], "y": ln["y"], "w": ln["w"], "h": ln["h"]})}'
                         f'display:flex;align-items:center;justify-content:center;text-align:center;'
                         f'background:{cc("lane_fill","surface")};border:1px solid rgba(0,0,0,0.08);'
                         f'box-sizing:border-box;color:{cc("lane_color","text")};font-size:{f.get("lane_size",13)}px;'
                         f'padding:2px;line-height:1.2;">{esc(ln["label"])}</div>')
        # phase band
        for ph in geo["phases"]:
            parts.append(f'<div style="{pos(ph)}display:flex;align-items:center;justify-content:center;'
                         f'background:{cc("phase_fill","on_primary_soft")};box-sizing:border-box;'
                         f'color:{cc("phase_color","primary")};font-weight:700;font-size:{f.get("phase_size",14)}px;'
                         f'border-left:2px solid {col(theme,"background")};">{esc(ph["label"])}</div>')
        # edges (SVG overlay, solid=flow / dashed=system operation)
        svg = [f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;'
               f'pointer-events:none;" viewBox="0 0 {CANVAS_W} {CANVAS_H}">'
               f'<defs><marker id="swm-arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" '
               f'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L9,4 L0,8 z" '
               f'fill="{cc("edge_color","text")}"/></marker></defs>']
        for e in geo["edges"]:
            pstr = " ".join(f"{x:.1f},{y:.1f}" for x, y in e["points"])
            dash = ' stroke-dasharray="7,5"' if e.get("style") == "dashed" else ""
            svg.append(f'<polyline points="{pstr}" fill="none" stroke="{cc("edge_color","text")}" '
                       f'stroke-width="{f.get("edge_w",2)}"{dash} marker-end="url(#swm-arrow)"/>')
            if e["label"]:
                lx, ly = e["label_pos"]
                svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{cc("label_color","accent")}" '
                           f'font-size="13" font-weight="700" text-anchor="middle">{esc(e["label"])}</text>')
        svg.append("</svg>")
        parts.append("".join(svg))
        # nodes
        for nid, nd in geo["nodes"].items():
            parts.append(_sw_node_html(nd, theme, f))

    elif t == "swimlane_legend":
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"])))
        parts.append(div(st["title"], theme, esc(slide.get("title", "凡例"))))
        parts.append(rect(st["rule"], theme))
        if slide.get("lead") and "lead" in st:
            parts.append(div(st["lead"], theme, esc(slide["lead"])))
        a = st["area"]; sym = st.get("sym", {})
        entries = slide.get("items") or SWIMLANE_LEGEND
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 60); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 120)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, (shape, vk, label, desc) in enumerate(entries):
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h
            parts.append(_legend_symbol_html(shape, vk, x, y + row_h / 2, sym_w, theme, sym))
            tx = x + sym_w + 8
            parts.append(div({"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                              "size": a.get("label_size", 16), "color": "text", "bold": True}, theme, esc(label)))
            parts.append(div({"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                              "size": a.get("desc_size", 13), "color": "muted"}, theme, esc(desc)))
        parts.append(footer_html(st, deck, theme, page, total))

    return "".join(parts)


HTML_TEMPLATE = Template("""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$TITLE</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; background: #101014; overflow: hidden; }
#stage { position: absolute; top: 50%; left: 50%; width: ${W}px; height: ${H}px; }
.slide {
  position: absolute; inset: 0; width: ${W}px; height: ${H}px;
  font-family: "$F_BODY", "Hiragino Sans", sans-serif;
  display: none; overflow: hidden;
}
.slide.active { display: block; }
.slide li::marker { color: var(--mk, inherit); }
#hud {
  position: fixed; right: 16px; bottom: 12px; color: #9a94ab;
  font: 13px/1 "$F_BODY", sans-serif; user-select: none; z-index: 10;
}
#notes {
  position: fixed; left: 0; right: 0; bottom: 0; max-height: 32vh; overflow: auto;
  background: rgba(16, 10, 26, 0.94); color: #e6def3; padding: 16px 28px 20px;
  font: 15px/1.7 "$F_BODY", sans-serif; z-index: 20; border-top: 2px solid $C_ACCENT;
}
#notes .label { color: $C_ACCENT; font-size: 12px; font-weight: 700; margin-bottom: 6px; }
</style>
</head>
<body>
<div id="stage">
$SLIDES
</div>
<div id="hud"><span id="pageno"></span>&nbsp;&nbsp;[&larr;/&rarr;] 移動 [N] ノート</div>
<div id="notes" hidden><div class="label">SPEAKER NOTES</div><div id="notes-body"></div></div>
<script>
var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
var stage = document.getElementById('stage');
var pageno = document.getElementById('pageno');
var notes = document.getElementById('notes');
var notesBody = document.getElementById('notes-body');
var idx = 0;

function fit() {
  var s = Math.min(window.innerWidth / $W, window.innerHeight / $H);
  stage.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
}
function show(i) {
  idx = Math.max(0, Math.min(slides.length - 1, i));
  slides.forEach(function (s, j) { s.classList.toggle('active', j === idx); });
  pageno.textContent = (idx + 1) + ' / ' + slides.length;
  location.replace('#' + (idx + 1));
  var n = slides[idx].getAttribute('data-notes') || '';
  notesBody.textContent = n || '（このスライドにノートはありません）';
}
function toggleNotes() { notes.hidden = !notes.hidden; }

window.addEventListener('resize', fit);
window.addEventListener('keydown', function (e) {
  if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { show(idx + 1); e.preventDefault(); }
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { show(idx - 1); e.preventDefault(); }
  else if (e.key === 'Home') { show(0); }
  else if (e.key === 'End') { show(slides.length - 1); }
  else if (e.key === 'n' || e.key === 'N') { toggleNotes(); }
});
window.addEventListener('click', function (e) {
  if (notes.contains(e.target)) { return; }
  if (e.clientX > window.innerWidth / 2) { show(idx + 1); } else { show(idx - 1); }
});

var start = parseInt((location.hash || '#1').slice(1), 10);
fit();
show(isNaN(start) ? 0 : start - 1);
</script>
</body>
</html>
""")


def slide_bg(slide, st, theme):
    if "bg" in st:
        return col(theme, st["bg"].get("fill", "primary"))
    return col(theme, "background")


def build_html(deck, theme, layout, deck_dir: Path, out_path: Path):
    slides = deck.get("slides", [])
    total = len(slides)
    rendered = []
    for i, slide in enumerate(slides):
        st = resolve_style(layout, deck, slide)
        body = html_slide_body(slide, st, deck, theme, deck_dir, i + 1, total)
        if deck.get("meta", {}).get("brand"):
            brand_r = {"x": 1080, "y": 43, "w": 140, "h": 34,
                       "size": 23, "color": "accent", "bold": True, "align": "right"}
            body += div(brand_r, theme, esc(deck["meta"]["brand"]))
        notes_attr = f' data-notes="{esc(slide["notes"])}"' if slide.get("notes") else ""
        bg = slide_bg(slide, st, theme)
        rendered.append(
            f'<section class="slide" style="background:{bg};color:{col(theme, "text")};"'
            f"{notes_attr}>{body}</section>"
        )
    doc = HTML_TEMPLATE.safe_substitute(
        TITLE=esc(deck["meta"].get("title", deck["meta"].get("id", ""))),
        SLIDES="\n".join(rendered),
        W=str(CANVAS_W), H=str(CANVAS_H),
        C_ACCENT=col(theme, "accent"),
        F_BODY=theme["fonts"]["body"],
    )
    out_path.write_text(doc, encoding="utf-8")


# ---------------------------------------------------------------------------
# PPTX ビルド
# ---------------------------------------------------------------------------

def build_pptx(deck, theme, layout, deck_dir: Path, out_path: Path):
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
        from pptx.enum.text import PP_ALIGN
        from pptx.oxml.ns import qn
        from pptx.util import Emu, Inches, Pt
    except ImportError:
        sys.exit(
            "error: python-pptx が未インストールのため PPTX を生成できません。\n"
            "  初回セットアップを実行してください: /slide-deck:setup"
            "（または `pip install python-pptx`）。HTML だけなら --html を付けて再実行できます。"
        )

    fonts = theme["fonts"]

    def IN(px):
        return Inches(px / 96.0)

    def PTS(px):
        return Pt(px * 0.75)

    def C(name):
        return RGBColor.from_string(col(theme, name).lstrip("#"))

    ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}

    prs = Presentation()
    prs.slide_width = IN(CANVAS_W)
    prs.slide_height = IN(CANVAS_H)
    blank = prs.slide_layouts[6]

    def set_run(run, text, size_px, color, bold=False, name=None):
        run.text = text
        f = run.font
        f.name = name or fonts["body"]
        f.size = PTS(size_px)
        f.bold = bold
        f.color.rgb = color
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = rPr.makeelement(qn("a:ea"), {})
            rPr.append(ea)
        ea.set("typeface", name or fonts["body"])

    def add_box(slide, r):
        box = slide.shapes.add_textbox(IN(r["x"]), IN(r["y"]), IN(r["w"]), IN(r.get("h", 40)))
        tf = box.text_frame
        tf.word_wrap = True
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, Emu(0))
        return tf

    def para(tf, used):
        if not used[0]:
            used[0] = True
            return tf.paragraphs[0]
        return tf.add_paragraph()

    def text_region(slide, r, text, font=None):
        tf = add_box(slide, r)
        p = tf.paragraphs[0]
        if r.get("align"):
            p.alignment = ALIGN[r["align"]]
        if r.get("line_height"):
            p.line_spacing = r["line_height"]
        set_run(p.add_run(), text, r["size"], C(r.get("color", "text")),
                bold=r.get("bold", False), name=font)
        return tf

    def add_rect(slide, x, y, w, h, fill, radius=0):
        shape = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        sp = slide.shapes.add_shape(shape, IN(x), IN(y), IN(w), IN(h))
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
        sp.line.fill.background()
        sp.shadow.inherit = False
        return sp

    def rect_region(slide, r):
        add_rect(slide, r["x"], r["y"], r["w"], r["h"], C(r.get("fill", "accent")),
                 radius=r.get("radius", 0))

    def para_indent(p, px):
        p._p.get_or_add_pPr().set("marL", str(Emu(IN(px))))

    def add_bullets(slide, items, r):
        tf = add_box(slide, r)
        used = [False]
        for it in items:
            p = para(tf, used)
            p.space_after = PTS(r["gap"])
            p.line_spacing = r["line_height"]
            size = it.get("size", r["size"])
            color = C(it["color"]) if it.get("color") else C(r["color"])
            set_run(p.add_run(), "•  ", size, C(r["marker_color"]), bold=True)
            set_run(p.add_run(), it["text"], size, color, bold=it.get("bold", False))
            for c in it["children"]:
                p = para(tf, used)
                p.space_after = PTS(r["child_gap"])
                p.line_spacing = max(1.0, r["line_height"] - 0.15)
                para_indent(p, r["indent"] + 6)
                csize = c.get("size", r["child_size"])
                ccolor = C(c["color"]) if c.get("color") else C(r["child_color"])
                set_run(p.add_run(), "–  ", csize, C(r["marker_color"]))
                set_run(p.add_run(), c["text"], csize, ccolor)
        return tf

    def footer(slide, st, page, total):
        if "footer_l" in st:
            text_region(slide, st["footer_l"], deck["meta"].get("title", ""))
        if "footer_r" in st:
            text_region(slide, st["footer_r"], st["footer_r"].get("text") or f"{page} / {total}")

    def chrome(slide, data, st, page, total):
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"])
        text_region(slide, st["title"], data.get("title", ""))
        rect_region(slide, st["rule"])
        if data.get("lead") and "lead" in st:
            text_region(slide, st["lead"], data["lead"])
        footer(slide, st, page, total)

    def s_title(slide, data, st, page, total):
        rect_region(slide, st["bar"])
        text_region(slide, st["title"], data.get("title", ""))
        if data.get("subtitle"):
            text_region(slide, st["subtitle"], data["subtitle"])
        if data.get("meta"):
            text_region(slide, st["meta"], data["meta"])

    def s_section(slide, data, st, page, total):
        add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C(st["bg"]["fill"]))
        if data.get("number"):
            text_region(slide, st["number"], data["number"])
        text_region(slide, st["title"], data.get("title", ""))
        rect_region(slide, st["rule"])
        if data.get("subtitle"):
            text_region(slide, st["subtitle"], data["subtitle"])

    def s_bullets(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        add_bullets(slide, norm_items(data.get("bullets")), st["body"])

    def s_two_column(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        for side in ("left", "right"):
            box = st[side]
            colc = data.get(side, {})
            add_rect(slide, box["x"], box["y"], box["w"], box["h"],
                     C(box["fill"]), radius=box.get("radius", 0))
            pad = box["pad"]
            iy = box["y"] + pad
            if colc.get("heading"):
                hd = st["col_heading"]
                hr = {"x": box["x"] + pad, "y": iy, "w": box["w"] - 2 * pad, "h": hd["size"] * 1.4,
                      "size": hd["size"], "color": hd["color"], "bold": hd.get("bold", False)}
                text_region(slide, hr, colc["heading"])
                iy += hd["size"] * 1.4 + hd["gap_below"]
            body = dict(st["col_body"])
            body.update({"x": box["x"] + pad, "y": iy, "w": box["w"] - 2 * pad,
                         "h": box["y"] + box["h"] - pad - iy})
            add_bullets(slide, norm_items(colc.get("bullets")), body)

    def s_table(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        tr = st["table"]
        cols = data.get("columns", [])
        rows = data.get("rows", [])
        n_rows, n_cols = len(rows) + 1, len(cols)
        total_h = tr["header_h"] + tr["row_h"] * len(rows)
        gfx = slide.shapes.add_table(n_rows, n_cols, IN(tr["x"]), IN(tr["y"]),
                                     IN(tr["w"]), IN(total_h))
        table = gfx.table
        table.first_row = False
        table.horz_banding = False
        widths = tr.get("col_widths")
        if widths:
            unit = tr["w"] / sum(widths)
            for j, w in enumerate(widths):
                table.columns[j].width = IN(w * unit)
        table.rows[0].height = IN(tr["header_h"])
        for i in range(len(rows)):
            table.rows[i + 1].height = IN(tr["row_h"])
        for j, name in enumerate(cols):
            cell = table.cell(0, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C(tr["header_fill"])
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = IN(tr["pad_x"])
            cell.margin_right = IN(tr["pad_x"])
            p = cell.text_frame.paragraphs[0]
            set_run(p.add_run(), str(name), tr["header_size"], C(tr["header_color"]), bold=True)
        row_fills = tr.get("row_fills", {})
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = table.cell(i + 1, j)
                cell.fill.solid()
                if str(i) in row_fills:
                    cell.fill.fore_color.rgb = C(row_fills[str(i)])
                else:
                    cell.fill.fore_color.rgb = C(tr["row_alt_fill"]) if i % 2 else C("background")
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_left = IN(tr["pad_x"])
                cell.margin_right = IN(tr["pad_x"])
                p = cell.text_frame.paragraphs[0]
                p.line_spacing = tr["line_height"]
                visible_text, cell_url = table_cell_parts(val)
                run = p.add_run()
                set_run(run, visible_text, tr["cell_size"], C(tr["cell_color"]))
                if cell_url:
                    run.hyperlink.address = cell_url

    def s_code(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        r = st["code"]
        size, lines = fit_code_size(data.get("code", ""), r)
        add_rect(slide, r["x"], r["y"], r["w"], r["h"], C(r["fill"]), radius=r.get("radius", 0))
        tf = add_box(slide, {"x": r["x"] + r["pad"], "y": r["y"] + r["pad"],
                             "w": r["w"] - 2 * r["pad"], "h": r["h"] - 2 * r["pad"]})
        used = [False]
        for line in lines:
            p = para(tf, used)
            p.line_spacing = r["line_height"]
            set_run(p.add_run(), line if line else " ", size, C(r["color"]),
                    name=fonts["code"])

    def s_quote(slide, data, st, page, total):
        text_region(slide, st["mark"], "“")
        text_region(slide, st["text"], data.get("text", ""))
        if data.get("attribution"):
            text_region(slide, st["attribution"], "— " + data["attribution"])

    def s_image(slide, data, st, page, total):
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"])
        if data.get("title"):
            text_region(slide, st["title"], data["title"])
            rect_region(slide, st["rule"])
        r = st["img"]
        pic = slide.shapes.add_picture(str(image_source(deck_dir, data["path"], True)),
                                       IN(r["x"]), IN(r["y"]))
        ratio = min(IN(r["w"]) / pic.width, IN(r["h"]) / pic.height, 1.0)
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
        pic.left = int(IN(r["x"]) + (IN(r["w"]) - pic.width) / 2)
        pic.top = int(IN(r["y"]) + (IN(r["h"]) - pic.height) / 2)
        if data.get("caption"):
            text_region(slide, st["caption"], data["caption"])
        footer(slide, st, page, total)

    def s_image_text(slide, data, st, page, total):
        if data.get("image_side") == "left":
            st = flip_regions(st, ("body", "img", "caption"))
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"])
        text_region(slide, st["title"], data.get("title", ""))
        rect_region(slide, st["rule"])
        if data.get("punch"):
            text_region(slide, st["punch"], data["punch"])
        add_bullets(slide, norm_items(data.get("bullets")), st["body"])
        r = st["img"]
        pic = slide.shapes.add_picture(str(image_source(deck_dir, data["path"], True)),
                                       IN(r["x"]), IN(r["y"]))
        ratio = min(IN(r["w"]) / pic.width, IN(r["h"]) / pic.height, 1.0)
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
        pic.left = int(IN(r["x"]) + (IN(r["w"]) - pic.width) / 2)
        pic.top = int(IN(r["y"]) + (IN(r["h"]) - pic.height) / 2)
        if data.get("caption"):
            text_region(slide, st["caption"], data["caption"])
        footer(slide, st, page, total)

    def s_closing(slide, data, st, page, total):
        add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C(st["bg"]["fill"]))
        text_region(slide, st["title"], data.get("title", ""))
        rect_region(slide, st["rule"])
        if data.get("bullets"):
            add_bullets(slide, norm_items(data.get("bullets")), st["body"])
        if data.get("message"):
            text_region(slide, st["message"], data["message"])

    def s_agenda(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        b = st["body"]
        items = norm_items(data.get("items", []))
        num_start = data.get("num_start", 0)
        row_h = b.get("row_h", 44); gap = b.get("gap", 10); num_w = b.get("num_w", 52)
        col_gap = b.get("col_gap", 56); pitch = row_h + gap
        R = max(1, int(b["h"] // pitch))
        N = len(items)
        cols = 1 if N <= R else min(b.get("max_cols", 2), -(-N // R))
        rows = -(-N // cols)
        col_w = (b["w"] - (cols - 1) * col_gap) / cols
        noff = (row_h - b.get("num_size", 24)) / 2
        toff = (row_h - b.get("text_size", 20)) / 2
        for i, it in enumerate(items):
            c = i // rows; r = i % rows
            x = b["x"] + c * (col_w + col_gap); y = b["y"] + r * pitch
            active = it.get("active")
            if active:
                add_rect(slide, x-14, y-3, col_w+18, row_h+6, C(b.get("active_fill", "surface")), radius=8)
            text_region(slide, {"x": x, "y": y+noff, "w": num_w, "h": row_h, "size": b.get("num_size", 24),
                                "color": b.get("num_color", "accent"), "bold": True, "line_height": 1.1}, f"{num_start+i+1:02d}")
            text_region(slide, {"x": x+num_w, "y": y+toff, "w": col_w-num_w, "h": row_h, "size": b.get("text_size", 20),
                                "color": (b.get("active_color", "primary") if active else b.get("text_color", "text")),
                                "bold": bool(active), "line_height": 1.2}, it["text"])

    def s_steps(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        b = st["body"]; steps = data.get("steps", [])
        n = max(1, len(steps)); gap = b.get("gap", 20)
        card_w = (b["w"] - (n-1)*gap) / n
        header_h = b.get("header_h", 60); pad = b.get("pad", 16); radius = b.get("radius", 12)
        for i, step in enumerate(steps):
            x = b["x"] + i * (card_w + gap)
            add_rect(slide, x, b["y"], card_w, b["h"], C(b.get("card_fill", "surface")), radius=radius)
            add_rect(slide, x, b["y"], card_w, header_h, C(b.get("header_fill", "primary")), radius=radius)
            text_region(slide, {"x": x+pad, "y": b["y"]+9, "w": card_w-2*pad, "h": 18, "size": 13,
                                "color": b.get("num_color", "accent"), "bold": True}, f"STEP {i+1}")
            text_region(slide, {"x": x+pad, "y": b["y"]+28, "w": card_w-2*pad, "h": header_h-26,
                                "size": b.get("label_size", 18), "color": b.get("header_color", "on_primary"),
                                "bold": True, "line_height": 1.15}, step.get("label", ""))
            itemr = {"x": x+pad, "y": b["y"]+header_h+pad, "w": card_w-2*pad, "h": b["h"]-header_h-2*pad,
                     "size": b.get("item_size", 15), "gap": b.get("item_gap", 8), "color": b.get("item_color", "text"),
                     "line_height": 1.4, "marker_color": "accent", "child_size": 13, "child_color": "muted",
                     "indent": 16, "child_gap": 4}
            add_bullets(slide, norm_items(step.get("items", [])), itemr)
            if i < n-1:
                text_region(slide, {"x": x+card_w, "y": b["y"]+b["h"]/2-18, "w": gap, "h": 36,
                                    "size": b.get("chevron_size", 28), "color": b.get("chevron_color", "accent"),
                                    "align": "center", "bold": True}, "›")

    def s_matrix(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        g = st["grid"]; ax = st.get("axis", {})
        gx, gy, gw, gh = g["x"], g["y"], g["w"], g["h"]
        gap = g.get("gap", 14); pad = g.get("pad", 18); radius = g.get("radius", 12)
        cw = (gw - gap) / 2; ch = (gh - gap) / 2
        quads = data.get("quadrants", [])
        positions = [(gx, gy), (gx+cw+gap, gy), (gx, gy+ch+gap), (gx+cw+gap, gy+ch+gap)]
        for qi, (qx, qy) in enumerate(positions):
            q = quads[qi] if qi < len(quads) else {}
            hi = q.get("highlight")
            fill = C(g.get("hi_fill", "on_primary_soft")) if hi else C(g.get("fill", "surface"))
            add_rect(slide, qx, qy, cw, ch, fill, radius=radius)
            text_region(slide, {"x": qx+pad, "y": qy+pad, "w": cw-2*pad, "h": 26, "size": g.get("heading_size", 18),
                                "color": (g.get("hi_heading_color", "accent") if hi else g.get("heading_color", "primary")),
                                "bold": True, "line_height": 1.2}, q.get("heading", ""))
            text_region(slide, {"x": qx+pad, "y": qy+pad+30, "w": cw-2*pad, "h": ch-2*pad-30,
                                "size": g.get("body_size", 14), "color": g.get("body_color", "muted"),
                                "line_height": 1.4}, q.get("body", ""))
        xa = data.get("x_axis", {}); ya = data.get("y_axis", {})
        asize = ax.get("size", 15); acol = ax.get("color", "muted"); ncol = ax.get("name_color", "text")
        text_region(slide, {"x": 72, "y": gy-30, "w": 360, "h": 22, "size": asize, "color": ncol, "bold": True}, "▲ " + ya.get("label", ""))
        text_region(slide, {"x": gx-96, "y": gy+6, "w": 88, "h": 22, "size": asize, "color": acol, "align": "right"}, ya.get("high", ""))
        text_region(slide, {"x": gx-96, "y": gy+gh-28, "w": 88, "h": 22, "size": asize, "color": acol, "align": "right"}, ya.get("low", ""))
        text_region(slide, {"x": gx, "y": gy+gh+30, "w": gw, "h": 22, "size": asize, "color": ncol, "align": "center", "bold": True}, xa.get("label", "") + " ▶")
        text_region(slide, {"x": gx, "y": gy+gh+6, "w": 160, "h": 22, "size": asize, "color": acol}, xa.get("low", ""))
        text_region(slide, {"x": gx+gw-160, "y": gy+gh+6, "w": 160, "h": 22, "size": asize, "color": acol, "align": "right"}, xa.get("high", ""))

    def s_cards(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        g = st["grid"]; cards = data.get("cards", [])
        cols = max(1, data.get("columns", g.get("cols", 3)))
        n = len(cards); rows = max(1, (n + cols - 1) // cols)
        gap = g.get("gap", 16); pad = g.get("pad", 18); radius = g.get("radius", 12)
        cw = (g["w"] - (cols-1)*gap) / cols; chh = (g["h"] - (rows-1)*gap) / rows
        for idx, card in enumerate(cards):
            rr = idx // cols; cc = idx % cols
            x = g["x"] + cc * (cw + gap); y = g["y"] + rr * (chh + gap)
            add_rect(slide, x, y, cw, chh, C(g.get("fill", "surface")), radius=radius)
            text_region(slide, {"x": x+pad, "y": y+pad, "w": cw-2*pad, "h": 28, "size": g.get("heading_size", 19),
                                "color": g.get("heading_color", "primary"), "bold": True, "line_height": 1.2}, card.get("heading", ""))
            yy = y + pad + 32
            if card.get("body"):
                text_region(slide, {"x": x+pad, "y": yy, "w": cw-2*pad, "h": 44, "size": g.get("body_size", 15),
                                    "color": g.get("body_color", "text"), "line_height": 1.4}, card["body"])
                yy += 48
            if card.get("items"):
                itemr = {"x": x+pad, "y": yy, "w": cw-2*pad, "h": chh-(yy-y)-pad, "size": g.get("item_size", 14),
                         "gap": g.get("item_gap", 6), "color": g.get("item_color", "muted"), "line_height": 1.35,
                         "marker_color": "accent", "child_size": 12, "child_color": "muted", "indent": 14, "child_gap": 4}
                add_bullets(slide, norm_items(card["items"]), itemr)

    def _shape_text(sp, text, size, color, bold=False):
        tf = sp.text_frame; tf.word_wrap = True
        tf.vertical_anchor = 3
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, Emu(0))
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; p.line_spacing = 1.1
        set_run(p.add_run(), text, size, color, bold=bold)

    def _sw_node_pptx(slide, nd, f):
        ns = f.get("node_size", 14)
        shape = nd["shape"]; x, y, w, h = nd["x"], nd["y"], nd["w"], nd["h"]
        if shape == "decision":
            sp = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("decision_fill", "on_primary_soft"))
            sp.line.color.rgb = C(f.get("decision_border", "accent")); sp.line.width = Pt(1.5); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, nd["text"], ns - 2, C(f.get("decision_color", "primary")))
        elif shape == "terminal":
            sp = slide.shapes.add_shape(MSO_SHAPE.OVAL, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("terminal_fill", "surface"))
            sp.line.color.rgb = C(f.get("terminal_border", "muted")); sp.line.width = Pt(1.25); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, nd["text"], ns - 2, C(f.get("terminal_color", "muted")))
        elif shape == "connector":
            sp = slide.shapes.add_shape(MSO_SHAPE.PENTAGON, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("connector_fill", "surface"))
            sp.line.color.rgb = C(f.get("connector_border", "muted")); sp.line.width = Pt(1); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, nd["text"], ns - 3, C(f.get("connector_color", "text")))
        elif shape == "marker":
            kind = nd.get("kind", "mid")
            mc = {"start": f.get("marker_start", "accent"), "end": f.get("marker_end", "primary"),
                  "mid": f.get("marker_mid", "#E6B800")}.get(kind, f.get("marker_mid", "#E6B800"))
            sp = slide.shapes.add_shape(MSO_SHAPE.OVAL, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(mc)
            sp.line.color.rgb = C("background"); sp.line.width = Pt(1.25); sp.shadow.inherit = False
        elif shape == "mail":
            sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C("background")
            sp.line.color.rgb = C(f.get("edge_color", "text")); sp.line.width = Pt(1.25); sp.shadow.inherit = False
            cxm = x + w / 2; my = y + h * 0.55
            for (x1, y1, x2, y2) in ((x, y, cxm, my), (cxm, my, x + w, y)):
                cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(y1), IN(x2), IN(y2))
                cn.line.color.rgb = C(f.get("edge_color", "text")); cn.line.width = Pt(1.25); cn.shadow.inherit = False
        elif shape == "io":
            sp = add_rect(slide, x, y, w, h, C(f.get("io_fill", "on_primary_soft")), radius=8)
            sp.line.color.rgb = C(f.get("io_border", "accent")); sp.line.width = Pt(1)
            half = (w - 2) / 2
            for idx, (key, lbl) in enumerate((("input", "input"), ("output", "output"))):
                vals = nd.get(key) or []
                tf = add_box(slide, {"x": x + idx * half + 6, "y": y + 6, "w": half - 10, "h": h - 12})
                p0 = tf.paragraphs[0]
                set_run(p0.add_run(), lbl, f.get("io_size", 11), C(f.get("io_head_color", "accent")), bold=True)
                for v in vals:
                    pp = tf.add_paragraph()
                    set_run(pp.add_run(), v, f.get("io_size", 11), C(f.get("io_color", "text")))
        elif shape == "system":
            sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("system_fill", "surface"))
            sp.line.color.rgb = C(f.get("system_border", "muted")); sp.line.width = Pt(1.5); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, nd["text"], ns, C(f.get("system_color", "text")))
        else:  # task (+variant)
            variant = nd.get("variant") or "onother"
            vmap = {"onpf": (f.get("task_onpf_fill", "on_primary_soft"), f.get("task_border", "accent"), f.get("task_onpf_color", "primary")),
                    "onother": (f.get("task_onother_fill", "background"), f.get("task_border", "accent"), f.get("task_color", "text")),
                    "offline": (f.get("task_offline_fill", "surface"), f.get("task_offline_border", "muted"), f.get("task_color", "text"))}
            fl, bd, cl = vmap.get(variant, vmap["onother"])
            sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(fl)
            sp.line.color.rgb = C(bd); sp.line.width = Pt(2); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, nd["text"], ns, C(cl))
            if nd.get("loop"):
                text_region(slide, {"x": x - 8, "y": y - 14, "w": 24, "h": 20, "size": 16,
                                    "color": "accent", "bold": True}, "↺")

    def s_swimlane(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        f = st["flow"]
        geo = swimlane_geometry(data, st)
        # lane bands (alt stripes)
        for ln in geo["lanes"]:
            if ln["alt"]:
                add_rect(slide, f["x"], ln["y"], f["w"], ln["h"], C(f.get("lane_band_b", "surface")))
        # group boxes (Lv1, rotated text)
        for gp in geo["groups"]:
            sp = add_rect(slide, gp["x"], gp["y"], gp["w"], gp["h"], C(f.get("group_fill", "primary")))
            _shape_text(sp, gp["label"], f.get("group_size", 13), C(f.get("group_color", "on_primary")), bold=True)
            sp.text_frame.word_wrap = False
            sp.rotation = 270
        # lane labels (Lv2)
        for ln in geo["lanes"]:
            sp = add_rect(slide, ln["x"], ln["y"], ln["w"], ln["h"], C(f.get("lane_fill", "surface")))
            sp.line.color.rgb = C("muted"); sp.line.width = Pt(0.5)
            _shape_text(sp, ln["label"], f.get("lane_size", 13), C(f.get("lane_color", "text")))
        # phase band
        for ph in geo["phases"]:
            sp = add_rect(slide, ph["x"], ph["y"], ph["w"], ph["h"], C(f.get("phase_fill", "on_primary_soft")))
            _shape_text(sp, ph["label"], f.get("phase_size", 14), C(f.get("phase_color", "primary")), bold=True)
        # edges (orthogonal connectors + arrowhead; solid=flow / dashed=system op)
        ec = C(f.get("edge_color", "text")); ew = Pt(f.get("edge_w", 2) * 0.75)
        for e in geo["edges"]:
            pts = e["points"]; dashed = e.get("style") == "dashed"
            for k in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[k], pts[k + 1]
                conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(y1), IN(x2), IN(y2))
                conn.line.color.rgb = ec; conn.line.width = ew; conn.shadow.inherit = False
                lnx = conn.line._get_or_add_ln()
                if dashed:
                    lnx.append(lnx.makeelement(qn("a:prstDash"), {"val": "dash"}))
                if k == len(pts) - 2:
                    lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
            if e["label"]:
                lx, ly = e["label_pos"]
                text_region(slide, {"x": lx - 30, "y": ly - 11, "w": 60, "h": 20, "size": 13,
                                    "color": f.get("label_color", "accent"), "bold": True, "align": "center"}, e["label"])
        # nodes
        for nid, nd in geo["nodes"].items():
            _sw_node_pptx(slide, nd, f)

    def s_swimlane_legend(slide, data, st, page, total):
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"])
        text_region(slide, st["title"], data.get("title", "凡例"))
        rect_region(slide, st["rule"])
        if data.get("lead") and "lead" in st:
            text_region(slide, st["lead"], data["lead"])
        a = st["area"]; sym = st.get("sym", {})
        entries = data.get("items") or SWIMLANE_LEGEND
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 60); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 120)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, (shape, vk, label, desc) in enumerate(entries):
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h; cy = y + row_h / 2
            sw, sh = _legend_sym_size(shape)
            scx = x + sym_w / 2
            if shape == "flow":
                x1, x2 = scx - sw / 2, scx + sw / 2
                conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(cy), IN(x2), IN(cy))
                conn.line.color.rgb = C(sym.get("edge_color", "text")); conn.line.width = Pt(2); conn.shadow.inherit = False
                lnx = conn.line._get_or_add_ln()
                if vk == "dashed":
                    lnx.append(lnx.makeelement(qn("a:prstDash"), {"val": "dash"}))
                lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
            else:
                nd = {"shape": shape, "variant": (vk if shape == "task" else None),
                      "kind": (vk if shape == "marker" else None), "text": "",
                      "x": scx - sw / 2, "y": cy - sh / 2, "w": sw, "h": sh,
                      "input": (["…"] if shape == "io" else None), "output": (["…"] if shape == "io" else None), "loop": None}
                _sw_node_pptx(slide, nd, sym)
            tx = x + sym_w + 8
            text_region(slide, {"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                                "size": a.get("label_size", 16), "color": "text", "bold": True}, label)
            text_region(slide, {"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                                "size": a.get("desc_size", 13), "color": "muted"}, desc)
        footer(slide, st, page, total)

    builders = {
        "title": s_title, "section": s_section, "bullets": s_bullets,
        "two_column": s_two_column, "table": s_table, "code": s_code,
        "quote": s_quote, "image": s_image, "image_text": s_image_text,
        "closing": s_closing,
        "agenda": s_agenda, "steps": s_steps, "matrix": s_matrix, "cards": s_cards,
        "swimlane": s_swimlane, "swimlane_legend": s_swimlane_legend,
    }

    slides = deck.get("slides", [])
    total = len(slides)
    for i, data in enumerate(slides):
        st = resolve_style(layout, deck, data)
        slide = prs.slides.add_slide(blank)
        if "bg" not in st:
            add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C("background"))
        builders[data["type"]](slide, data, st, i + 1, total)
        if deck.get("meta", {}).get("brand"):
            brand_r = {"x": 1080, "y": 43, "w": 140, "h": 34,
                       "size": 23, "color": "accent", "bold": True, "align": "right"}
            text_region(slide, brand_r, deck["meta"]["brand"])
        # 注意: notes は意図的に PPTX へ出力しない（Keynote 互換性問題のため）

    prs.save(str(out_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="deck.json → HTML / PPTX ビルダー v2")
    ap.add_argument("deck_dir", help="デッキのディレクトリ（deck.json を含む）")
    ap.add_argument("--html", action="store_true", help="HTML のみ生成")
    ap.add_argument("--pptx", action="store_true", help="PPTX のみ生成")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    deck, theme, layout = load_deck(deck_dir)
    deck = expand_slides(deck, layout)
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name

    out_dir = deck_dir / "build"
    out_dir.mkdir(exist_ok=True)

    if args.html or not args.pptx:
        out = out_dir / f"{deck_id}.html"
        build_html(deck, theme, layout, deck_dir, out)
        print(f"HTML: {out}")
    if args.pptx or not args.html:
        out = out_dir / f"{deck_id}.pptx"
        build_pptx(deck, theme, layout, deck_dir, out)
        print(f"PPTX: {out}")


if __name__ == "__main__":
    main()

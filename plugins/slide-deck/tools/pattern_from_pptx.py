#!/usr/bin/env python3
"""PPTX の 1 枚（またはこのプラグインのデッキの 1 枚）から、パターン（構図の型）の JSON を起こす。

    python3 tools/pattern_from_pptx.py <src.pptx> --slide N --name <名前> [--theme <テーマ名>] [--dir DIR]
    python3 tools/pattern_from_pptx.py --from-deck <deck_dir> --slide N --name <名前> [--theme <テーマ名>] [--dir DIR]

手順（pptx_import.py の取り込みを土台にする）
  1. 指定の 1 枚を canvas 要素として取り込む。マスター・レイアウト由来の図形は型に入れず、一覧に出す（--keep-master で固定の飾りとして残せる）。
  2. 色をテーマトークンに寄せる（Lab 色空間で近い色だけ。寄せ切れない色は hex のまま残し、一覧に出す）。
  3. 文字を段落単位でスロットにする（見出し・小見出し・本文の判定、例文の保存、max_chars の目安、箇条書きは list スロット）。
     ページ番号は {{page}} / {{total}} に戻す。画像の枠は image スロットにする。
  4. 同じ大きさの図形が等間隔に並ぶ箇所は「repeat にできる候補」として報告する（自動では書き換えない）。
出力: <dir>/<名前>.json（既存のものを上書きするときは --confirm が要る）と、型を例文で展開した確認用デッキ
      <dir>/_check/<名前>/deck.json（元のスライドと型の展開結果を並べた 1 枚目つき。build_deck.py で HTML / PPTX にできる）。
--from-deck は、デッキを build_deck.py でビルドし、できた PPTX の N 枚目（PPTX 上の通し番号）から起こす。
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import canvas_engine as ce  # noqa: E402
import pattern_engine as pe  # noqa: E402

SNAP_DELTA_E = 6.0   # 「近い色」とみなす Lab 距離（ΔE76）
AUTO_NAME_RE = re.compile(
    r"^(TextBox|Rectangle|Rounded Rectangle|Title|Subtitle|Content Placeholder|Text Placeholder|Group|Straight Connector|"
    r"Straight Arrow Connector|Elbow Connector|Connector|Oval|Isosceles Triangle|Right Arrow|Arrow|Pentagon|Chevron|Freeform|"
    r"Picture|Slide Number Placeholder|Footer Placeholder|Date Placeholder|Table|Diamond|Flowchart[^\d]*|canvas)\b.*?\s*\d+$",
    re.I)
PAGE_RE = re.compile(r"^\s*(\d{1,3})\s*(?:/\s*(\d{1,3}))?\s*$")
# 同じ色が複数のトークンに当たるときの優先順（用途別）
PREF = {
    "fill": ["background", "surface", "primary", "accent", "highlight_fill", "table_row_alt", "code_bg", "table_header_bg",
             "on_primary", "muted", "border", "text"],
    "text": ["text", "heading_text", "muted", "on_primary", "primary", "accent", "accent_on_primary", "background",
             "table_header_text", "on_primary_soft", "on_primary_muted", "code_text"],
    "line": ["border", "muted", "primary", "accent", "text", "heading_text", "surface"],
}


# ---------------------------------------------------------------- 色
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lab(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def t(v):
        return v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116
    fx, fy, fz = t(x), t(y), t(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(a, b):
    return math.dist(_lab(_rgb(a)), _lab(_rgb(b)))


def snap_color(hexv, colors, role):
    """hex に一番近いテーマトークンの名前。ΔE が SNAP_DELTA_E 以内でなければ None。
    ほぼ同じ距離のトークンが複数あるときは、用途（role）別の優先順で選ぶ"""
    if not (isinstance(hexv, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", hexv)):
        return None
    best = []
    for tok, tv in colors.items():
        if isinstance(tv, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", tv):
            d = delta_e(hexv, tv)
            if d <= SNAP_DELTA_E:
                best.append((d, tok))
    if not best:
        return None
    dmin = min(d for d, _ in best)
    near = [t for d, t in best if d <= dmin + 0.75]
    pref = PREF.get(role, [])
    near.sort(key=lambda t: (pref.index(t) if t in pref else 99, t))
    return near[0]


class Snapper:
    def __init__(self, colors):
        self.colors = colors
        self.snapped = Counter()
        self.left = Counter()

    def one(self, v, role):
        if isinstance(v, str) and v.startswith("#"):
            tok = snap_color(v, self.colors, role)
            if tok:
                self.snapped[tok] += 1
                return tok
            self.left[v.upper()] += 1
        return v

    def walk(self, obj, role="fill", key=None):
        """要素ツリーの色を寄せる。role は用途（fill / text / line）で、同じ色が複数トークンに当たるときの優先順を決める"""
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                r = role
                if k in ("line", "borders", "head", "tail"):
                    r = "line"
                elif k in ("text", "paragraphs", "runs", "bullet"):
                    r = "text"
                elif k in ("fill", "background"):
                    r = "fill"
                if k == "shadow" or k == "colors":
                    out[k] = v                      # 影・backdrop の色格子は寄せない
                elif k in ce.COLOR_KEYS and isinstance(v, str):
                    out[k] = self.one(v, "fill" if k in ("fill", "bg", "fg") else r)
                else:
                    out[k] = self.walk(v, r, k)
            return out
        if isinstance(obj, list):
            if key == "stops":
                return [[s[0], self.one(s[1], "fill")] if isinstance(s, (list, tuple)) and len(s) == 2 else s for s in obj]
            return [self.walk(x, role, key) for x in obj]
        return obj


# ---------------------------------------------------------------- スロット化
class Slots:
    def __init__(self):
        self.defs = {}
        self.order = []

    def unique(self, base):
        base = re.sub(r"[^A-Za-z0-9_]", "_", base).strip("_") or "text"
        if not re.match(r"[A-Za-z_]", base):
            base = "t_" + base
        name, k = base, 2
        while name in self.defs:
            name = f"{base}{k}"
            k += 1
        return name

    def add(self, base, d):
        name = self.unique(base)
        self.defs[name] = d
        return name


def _fonts_map(theme):
    f = (theme or {}).get("fonts", {}) or {}
    head, body = pe.ja_text._names(f.get("heading")), pe.ja_text._names(f.get("body"))
    return [x.lower() for x in head[:1]], [x.lower() for x in body[:1]]


def _map_font(fonts, head, body):
    if not fonts:
        return fonts
    first = str(fonts[0]).lower()
    if head and first == head[0] and head != body:
        return ["@heading"]
    if body and first == body[0]:
        return ["@body"]
    return fonts


def _para_text(p):
    """段落の文字。段落内の改行（Shift+Enter の br）は \n にする（展開側が br に戻す）"""
    return "".join("\n" if r.get("br") else r.get("text", "") for r in p.get("runs", []))


def _run_fmt(r):
    return {k: v for k, v in r.items() if k not in ("text", "br")}


def _max_size(el):
    sizes = [r.get("size", 0) for p in (el.get("text") or {}).get("paragraphs", []) for r in p.get("runs", [])]
    return max(sizes) if sizes else 0


def _ladder(size):
    out = []
    for k in (1.0, 0.9, 0.8, 0.7):
        v = round(size * k)
        if v >= 11 and v not in out:
            out.append(v)
    return out if len(out) > 1 else None


def _is_page_el(el):
    tx = el.get("text") or {}
    ps = [p for p in tx.get("paragraphs", []) if _para_text(p).strip()]
    if len(ps) != 1:
        return False
    t = _para_text(ps[0])
    ph = (el.get("ph") or {}).get("type")
    return ph == "sldNum" or (bool(PAGE_RE.match(t)) and el.get("y", 0) > 600 and _max_size(el) <= 18)


ROLE_SEQ = ["head", "sub", "body", "note"]                # 繰り返しの箱の中の文字を上から順に呼ぶ名前
ROLE_LABEL = {"head": "見出し", "sub": "小見出し", "body": "本文", "note": "補足", "points": "箇条書き"}
CLUSTER_PREFIX = [("card", "カード"), ("item", "項目"), ("box", "ボックス"), ("cell", "セル")]


def _clusters(elements, text_els):
    """同じ大きさの箱（塗りか枠線のある図形）が 3 つ以上並ぶとき、その箱の中の文字をまとめる。
    戻り値 {文字枠の id: (箱の通し番号, 接頭辞, 日本語の接頭辞, 箱の id)}。箱の通し番号は上→下・左→右の読み順で 1 から"""
    boxes = [e for e in _flat(elements)
             if e.get("kind", "shape") == "shape" and e.get("geom") not in ce.LINE_GEOMS
             and e.get("w", 0) >= 80 and e.get("h", 0) >= 40 and not (e["w"] > 1000 and e["h"] > 600)
             and (e.get("fill") or e.get("line"))]
    owner = {}
    for t in text_els:
        cx, cy = t.get("x", 0) + t.get("w", 0) / 2, t.get("y", 0) + t.get("h", 0) / 2
        inside = [b for b in boxes if b["x"] - 1 <= cx <= b["x"] + b["w"] + 1 and b["y"] - 1 <= cy <= b["y"] + b["h"] + 1]
        if inside:
            owner[id(t)] = min(inside, key=lambda b: b["w"] * b["h"])
    buckets = {}
    for b in {id(o): o for o in owner.values()}.values():
        buckets.setdefault((round(b["w"] / 8), round(b["h"] / 8), b.get("geom", "rect")), []).append(b)
    out = {}
    rep_buckets = sorted((v for v in buckets.values() if len(v) >= 3), key=lambda v: -len(v))
    for bi, bs in enumerate(rep_buckets[:len(CLUSTER_PREFIX)]):
        bs.sort(key=lambda b: (round(b["y"] / 20), b["x"]))
        rank = {id(b): k + 1 for k, b in enumerate(bs)}
        for tid, b in owner.items():
            if id(b) in rank:
                out[tid] = (rank[id(b)], CLUSTER_PREFIX[bi][0], CLUSTER_PREFIX[bi][1], id(b))
    return out


def _list_capacity(el, defs, theme, base_n, extra=2):
    """箇条書きの文字枠 el に、元の個数 base_n から何個まで足しても fit の最小サイズで収まるかを調べる（最大 base_n + extra）。
    収まらない個数を max にすると、型を作った直後から「収まりません」の警告が出て、利用者には直しようがないため"""
    names = [n for n in defs]
    best = base_n
    for n in range(base_n + 1, base_n + extra + 1):
        mini = {"name": "_cap", "slots": {k: dict(defs[k], max=n) for k in names}, "elements": [el]}
        warns = []
        try:
            pe.expand(pe.example_slide(mini, n), mini, theme, {"meta": {}}, 1, 1, warns.append, [])
        except Exception:  # noqa: BLE001
            break
        if warns:
            break
        best = n
    return best


def slotify(elements, theme, report, page_total_hint=None, deck_meta=None):
    """canvas 要素列の文字を、段落単位で {{slot}} にする。戻り値 (新しい要素列, Slots)。
    deck_meta（{"title","brand"}）が分かるとき、それと同じ文字は {{deck.title}} / {{deck.brand}} に戻す（スロットにしない）"""
    slots = Slots()
    head, body = _fonts_map(theme)
    text_els = [e for e in _flat(elements) if e.get("kind", "shape") == "shape" and e.get("text") and not _is_page_el(e)
                and any(_para_text(p).strip() for p in e["text"].get("paragraphs", []))]
    # 見出しの判定: プレースホルダー種別 → 最大の文字サイズ（24px 以上）
    title_el = next((e for e in text_els if (e.get("ph") or {}).get("type") in ("title", "ctrTitle")), None)
    if title_el is None and text_els:
        cand = max(text_els, key=lambda e: (_max_size(e), -e.get("y", 0)))
        if _max_size(cand) >= 24:
            title_el = cand
    used_roles = {"title": title_el}
    out = []
    n_text = [0]
    cl_info = _clusters(elements, [e for e in text_els if e is not title_el])
    cl_seq = {}
    box_tops = [e.get("y", 0) for e in text_els if id(e) in cl_info]
    named = set()      # kicker / lead / footer を 1 回ずつ名づけるための記録
    meta_texts = {}
    for key in ("title", "brand"):
        v = str((deck_meta or {}).get(key) or "").strip()
        if v:
            meta_texts.setdefault(v, key)

    def role_of(e):
        ph = (e.get("ph") or {}).get("type")
        return {"subTitle": "subtitle", "body": "body", "obj": "body", "ftr": "footer", "dt": None}.get(ph, "text")

    def free_name(e):
        """箱の中ではない文字枠に、位置から役割の名前を付ける。戻り値 (名前, 表示名) または None"""
        y, h = e.get("y", 0), e.get("h", 0)
        if title_el is not None and e is not title_el:
            if y + h <= title_el.get("y", 0) + 2 and "kicker" not in named:
                named.add("kicker")
                return "kicker", "見出しの上の小さな文言"
            top_box = min(box_tops) if box_tops else 9999
            if y >= title_el.get("y", 0) + title_el.get("h", 0) - 2 and y < top_box - 2 and y < 400 and "lead" not in named:
                named.add("lead")
                return "lead", "リード文"
        if y >= 640 and "footer" not in named and _max_size(e) <= 16:
            named.add("footer")
            return "footer", "フッターの文言"
        return None

    def conv(e):
        is_title = e is title_el          # deepcopy する前の同一性で判定する
        cl = cl_info.get(id(e))
        e_orig = e
        e = copy.deepcopy(e)
        k = e.get("kind", "shape")
        if k == "group":
            e["children"] = [conv(c) for c in e.get("children", [])]
            return e
        if k == "placeholder":
            base = slots.unique("image")
            slots.defs[base] = {"kind": "image", "label": (e.get("label") or "画像")[:30], "example": ""}
            slots.order.append(base)
            ph_el = dict(e, **{"if": "!" + base})
            img = {"kind": "image", "x": e["x"], "y": e["y"], "w": e["w"], "h": e["h"], "path": "{{%s}}" % base,
                   "fit": "cover", "if": base, "name": base}
            if e.get("alt"):
                img["alt"] = e["alt"]
            return [ph_el, img]
        if k != "shape" or not e.get("text"):
            return e
        if _is_page_el(e):
            for p in e["text"]["paragraphs"]:
                t = _para_text(p)
                m = PAGE_RE.match(t)
                if m and p.get("runs"):
                    r0 = dict(p["runs"][0], text="{{page}} / {{total}}" if m.group(2) else "{{page}}")
                    if r0.get("font"):
                        r0["font"] = _map_font(r0["font"], head, body)
                    p["runs"] = [r0]
            e["name"] = "ページ番号"
            return e
        role = "title" if is_title else role_of(e)
        paras_in = e["text"].get("paragraphs", [])
        new_paras, i = [], 0
        el_slots = []
        while i < len(paras_in):
            p = paras_in[i]
            txt = _para_text(p)
            if not txt.strip():
                if not p.get("runs") or all(r.get("br") for r in p.get("runs", [])):
                    new_paras.append(p)
                i += 1
                continue
            run0 = next(r for r in p["runs"] if not r.get("br"))
            fmts = [_run_fmt(r) for r in p["runs"] if not r.get("br")]
            if any(f != fmts[0] for f in fmts[1:]):   # 書式（size / bold / color / font…）が実際に違うときだけ数える
                report["multi_run"].append(txt[:20].replace("\n", " "))
            run = {k: v for k, v in run0.items() if k not in ("text", "br")}
            if run.get("font"):
                run["font"] = _map_font(run["font"], head, body)
            if p.get("bullet"):
                items = [txt]
                j = i + 1
                while j < len(paras_in) and paras_in[j].get("bullet") and _para_text(paras_in[j]).strip():
                    items.append(_para_text(paras_in[j]))
                    j += 1
                base = {"body": "points"}.get(role, "items" if role == "text" else role)
                lbl = f"箇条書き（{items[0][:10]}…）" if len(items[0]) > 10 else f"箇条書き（{items[0]}）"
                if cl and role == "text":
                    base, lbl = f"{cl[1]}{cl[0]}_points", f"{cl[2]}{cl[0]}の箇条書き（{items[0][:8].strip()}）"
                name = slots.add(base, {"kind": "list", "label": lbl,
                                        "min": 1, "max": len(items) + 3,
                                        "max_chars": max(int(max(len(t) for t in items) * 1.5), 12), "example": items})
                slots.order.append(name)
                q = {k: v for k, v in p.items() if k != "runs"}
                q["repeat"] = name
                q["runs"] = [dict(run, text="{{.}}")]
                new_paras.append(q)
                el_slots.append(name)
                i = j
                continue
            mkey = meta_texts.get(txt.strip()) if role in ("text", "footer") else None
            if mkey:    # デッキ名・ブランド名と同じ文言は、スロットにせず組み込み変数へ戻す（別の文言に差し替えられて浮くのを防ぐ）
                q = {k: v for k, v in p.items() if k != "runs"}
                q["runs"] = [dict(run, text="{{deck.%s}}" % mkey)]
                new_paras.append(q)
                report["deck_vars"].append(mkey)
                i += 1
                continue
            if role == "text":
                n_text[0] += 1
            lbl_default = (e.get("name") if e.get("name") and not AUTO_NAME_RE.match(e["name"]) else f"テキスト{n_text[0]}")
            base = role if role in ("title", "subtitle", "footer") else ("body" if role == "body" else f"text{n_text[0]}")
            if role == "body":
                base = "body"
            lbl = ("見出し" if role == "title" else "小見出し" if role == "subtitle" else
                   "本文" if role == "body" else "フッター" if role == "footer" else lbl_default)
            if role == "text":
                # 意味のある名前: 同じ形の箱が並ぶなら card1_head など、そうでなければ kicker / lead / footer
                if cl:
                    seq = cl_seq.get(cl[3], 0)
                    cl_seq[cl[3]] = seq + 1
                    rname = ROLE_SEQ[seq] if seq < len(ROLE_SEQ) else f"text{seq + 1}"
                    base = f"{cl[1]}{cl[0]}_{rname}"
                    lbl = f"{cl[2]}{cl[0]}の{ROLE_LABEL.get(rname, '文字')}（{txt[:8].strip()}）"
                else:
                    fn = free_name(e_orig)
                    if fn:
                        base, lbl = fn[0], f"{fn[1]}（{txt[:8].strip()}）"
            name = slots.add(base, {"kind": "text", "label": lbl,
                                    **({"required": True} if role == "title" else {}), "max_chars": max(int(len(txt) * 1.5), 8), "example": txt})
            slots.order.append(name)
            q = {k: v for k, v in p.items() if k != "runs"}
            q["runs"] = [dict(run, text="{{%s}}" % name)]
            new_paras.append(q)
            el_slots.append(name)
            i += 1
        e["text"]["paragraphs"] = new_paras
        if el_slots and not (e.get("name") and not AUTO_NAME_RE.match(e["name"])):
            e["name"] = el_slots[0]
        if el_slots:
            sz = max((r.get("size", 0) for p in new_paras for r in p.get("runs", [])), default=0)
            lad = _ladder(sz) if sz >= 12 else None
            # wrap:false（折り返さない 1 行のラベル）には fit を付けない（折り返す前提の計算で不要に縮むため）
            if lad and e.get("geom", "rect") not in ("custom",) and e.get("w", 0) > 0 and e["text"].get("wrap") is not False:
                e["fit"] = {"sizes": lad}
            # 箇条書きの max は、元の個数から枠に収まる個数まで（収まらない個数を許すと、直せない警告になる）
            lists = {n: slots.defs[n] for n in el_slots if slots.defs[n]["kind"] == "list"}
            for n, d in lists.items():
                base_n = len(d["example"])
                if e.get("fit"):
                    cap = _list_capacity(e, {k: slots.defs[k] for k in el_slots}, theme, base_n)
                else:
                    cap = base_n + 2
                d["max"] = max(base_n, cap)
        return e

    for e in elements:
        r = conv(e)
        out.extend(r if isinstance(r, list) else [r])
    return out, slots


def _flat(elements):
    for e in elements:
        if e.get("kind") == "group":
            yield from _flat(e.get("children", []))
        else:
            yield e


# ---------------------------------------------------------------- 繰り返し候補
def repeat_candidates(elements):
    """同じ大きさ・形の図形が等間隔に並ぶ箇所を探す。戻り値: [(説明, [要素名...])]"""
    buckets = {}
    for e in _flat(elements):
        if e.get("kind", "shape") != "shape" or not e.get("w") or not e.get("h") or e.get("geom") in ce.LINE_GEOMS:
            continue
        if e["w"] > 1000 and e["h"] > 600:
            continue
        buckets.setdefault((round(e["w"] / 4), round(e["h"] / 4), e.get("geom", "rect")), []).append(e)
    out = []
    for (_w, _h, g), els in buckets.items():
        if len(els) < 3:
            continue
        for axis, other in (("x", "y"), ("y", "x")):
            groups = {}
            for e in els:
                groups.setdefault(round(e[other] / 4), []).append(e)
            for grp in groups.values():
                if len(grp) < 3:
                    continue
                grp.sort(key=lambda e: e[axis])
                gaps = [grp[k + 1][axis] - grp[k][axis] for k in range(len(grp) - 1)]
                if max(gaps) - min(gaps) <= 3 and min(gaps) > 0:
                    out.append((f"{len(grp)} 個の同じ大きさの図形が{'横' if axis == 'x' else '縦'}に等間隔（{g}, {grp[0]['w']:.0f}x{grp[0]['h']:.0f}px, 間隔 {gaps[0]:.0f}px）",
                                [e.get("name", "?") for e in grp]))
    return out


# ---------------------------------------------------------------- テーマの選択
def _theme_candidates(deck_dir=None):
    try:
        import build_deck as bd  # type: ignore
        names = set()
        for d in bd.theme_dirs(Path(deck_dir) if deck_dir else None):
            if d.is_dir():
                names.update(f.stem for f in d.glob("*.json"))
        return {n: bd.load_theme(n, bd.theme_dirs(Path(deck_dir) if deck_dir else None)) for n in sorted(names)}
    except Exception:  # noqa: BLE001
        out = {}
        for d in ([Path(deck_dir) / "themes"] if deck_dir else []) + [HERE.parent / "templates" / "themes"]:
            if d.is_dir():
                for f in d.glob("*.json"):
                    out[f.stem] = pe._load_theme_for_cli(f.stem, deck_dir)
        return out


def _used_colors(elements):
    cnt = Counter()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ce.COLOR_KEYS and isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
                    cnt[v.upper()] += 1
                elif k != "colors":
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(elements)
    return cnt


def pick_theme(elements, background, deck_dir=None):
    """使われている色に一番多く当たる同梱テーマを選ぶ。戻り値 (テーマ名, テーマ dict, 当たった割合)"""
    used = _used_colors(elements)
    used[background.upper()] += 1
    cands = _theme_candidates(deck_dir)
    best = (None, None, -1.0)
    total = sum(used.values()) or 1
    for name, th in cands.items():
        cols = [v for v in (th.get("colors") or {}).values() if isinstance(v, str)]
        hit = sum(n for c, n in used.items() if any(re.fullmatch(r"#[0-9A-Fa-f]{6}", t) and delta_e(c, t) <= SNAP_DELTA_E for t in cols))
        frac = hit / total
        if frac > best[2] + 1e-9 or (abs(frac - best[2]) < 1e-9 and name == "default"):
            best = (name, th, frac)
    return best


# ---------------------------------------------------------------- 本体
def build_pattern(slide, name, theme, theme_name, keep_master=False, label=None, source="", deck_meta=None):
    """取り込んだ canvas スライド dict → (パターン dict, 報告 dict)。deck_meta（デッキの meta）があれば、
    デッキ名・ブランド名と同じ文言を {{deck.title}} / {{deck.brand}} に戻す"""
    report = {"master_dropped": [], "multi_run": [], "unsnapped": Counter(), "snapped": Counter(), "tables": 0,
              "repeat": [], "svg": 0, "deck_vars": []}
    els = []
    for e in slide["elements"]:
        if e.get("src") in ("master", "layout") and not keep_master:
            report["master_dropped"].append(e.get("name") or e.get("kind", "shape"))
            continue
        els.append(e)
    for e in els:
        e.pop("src", None)
    report["repeat"] = repeat_candidates(els)
    report["tables"] = sum(1 for e in _flat(els) if e.get("kind") == "table")
    report["svg"] = sum(1 for e in _flat(els) if e.get("kind") == "svg")
    snap = Snapper(theme.get("colors", {}))
    bg = snap.one(slide.get("background", "#FFFFFF"), "fill")
    els = snap.walk(els)
    els = _strip_meta(_tidy(els))
    els, slots = slotify(els, theme, report, deck_meta=deck_meta)
    report["unsnapped"], report["snapped"] = snap.left, snap.snapped
    # 先頭に背景（取り込みの背景は slide.background なので、パターンの background に入れる）
    defs = {k: slots.defs[k] for k in slots.order}
    pat = {"name": name, "label": label or name,
           "description": f"{source} から起こした型。スロット: " + "、".join(defs) if defs else f"{source} から起こした型",
           "version": 1, "source": source, "background": bg, "slots": defs, "elements": els}
    return pat, report


def _tidy(o):
    """1280.0 → 1280（JSON を読みやすくする）"""
    if isinstance(o, dict):
        return {k: _tidy(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_tidy(x) for x in o]
    if isinstance(o, float) and o.is_integer():
        return int(o)
    return o


def _strip_meta(o):
    """型に不要な由来メタ（ph）を落とす"""
    if isinstance(o, dict):
        return {k: _strip_meta(v) for k, v in o.items() if k not in ("ph",)}
    if isinstance(o, list):
        return [_strip_meta(x) for x in o]
    return o


def make_check_deck(out_dir, pat, imported_slide, theme, theme_name, deck_meta=None):
    """元のスライドと、型を例文で展開した結果を並べた確認用デッキを書く"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    warns = []
    sl = pe.example_slide(pat)
    meta = {"meta": {"title": (deck_meta or {}).get("title") or "確認用", "brand": (deck_meta or {}).get("brand") or ""}}
    expanded = pe.to_canvas_slide(sl, pat, theme, meta, 1, 3, warns.append, [])
    orig = {"type": "canvas", "background": imported_slide["background"],
            "elements": [{k: v for k, v in e.items() if k not in ("src", "ph")} for e in imported_slide["elements"]
                         if e.get("src") not in ("master", "layout")]}
    half = []
    label = lambda x, y, t: {"x": x, "y": y, "w": 600, "h": 26, "text": {"insets": [0, 0, 0, 0], "anchor": "ctr", "paragraphs": [
        {"runs": [{"text": t, "size": 16, "bold": True, "color": "#444444"}]}]}}
    side = {"type": "canvas", "background": "#F2F2F2", "title": "元のスライドと型の展開結果",
            "elements": [{"x": 0, "y": 0, "w": 1280, "h": 720, "fill": "#F2F2F2"},
                         label(20, 44, "元のスライド（取り込み結果）"), label(660, 44, f"型から展開（テーマ {theme_name}、例文）"),
                         {"x": 19, "y": 79, "w": 602, "h": 339, "fill": "#CCCCCC"}, {"x": 659, "y": 79, "w": 602, "h": 339, "fill": "#CCCCCC"}]
            + [{"x": 20, "y": 80, "w": 600, "h": 337, "fill": orig["background"]}]
            + ce.fit_elements(orig["elements"], (20, 80, 600, 337))
            + [{"x": 660, "y": 80, "w": 600, "h": 337, "fill": expanded["background"]}]
            + ce.fit_elements(expanded["elements"], (660, 80, 600, 337))}
    orig["title"], expanded["title"] = "元のスライド", f"型の展開結果（{theme_name}）"
    deck = {"meta": {"id": out_dir.name, "title": f"型 {pat['name']} の確認用", "theme": theme_name},
            "slides": [side, orig, expanded]}
    (out_dir / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
    return warns


def _deck_info(deck_dir):
    """--from-deck 用: デッキの meta（title / brand）と、deck.json の枚数目 ↔ PPTX の枚数目の対応表。
    戻り値 (meta dict | None, {"deck_to_pptx": [N...], "pptx_to_deck": [(M, type) | None...]} | None)。調べられなければ None"""
    meta, pmap = None, None
    try:
        raw = json.loads((Path(deck_dir) / "deck.json").read_text(encoding="utf-8"))
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else None
    except (OSError, ValueError):
        return None, None
    try:
        import build_deck as bd  # type: ignore
        slides = raw.get("slides", [])
        for si, sl in enumerate(slides):
            if isinstance(sl, dict):
                sl["_orig_idx"] = si          # expand_slides は元のスライドを（agenda 分割は浅いコピーで）引き継ぐので目印が残る
        _deck, _theme, layout = bd.load_deck(Path(deck_dir))
        exp = bd.expand_slides(dict(raw), layout)["slides"]
        pptx_to_deck, deck_to_pptx = [], {}
        for k, sl in enumerate(exp):
            oi = sl.get("_orig_idx") if isinstance(sl, dict) else None
            pptx_to_deck.append((oi + 1, sl.get("type")) if oi is not None else None)
            if oi is not None and oi not in deck_to_pptx:
                deck_to_pptx[oi] = k + 1
        pmap = {"deck_to_pptx": [deck_to_pptx.get(i, 0) for i in range(len(slides))], "pptx_to_deck": pptx_to_deck}
    except Exception:  # noqa: BLE001
        pmap = None
    return meta, pmap


def main(argv=None):
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="PPTX の 1 枚から、パターン（構図の型）の JSON を起こす")
    ap.add_argument("src", nargs="?", help="元の PPTX")
    ap.add_argument("--from-deck", help="このプラグインのデッキフォルダ（ビルドしてできた PPTX の N 枚目から起こす）")
    ap.add_argument("--slide", type=int, help="PPTX 上の枚数目（1 始まり）。--from-deck では agenda の分割や図解の凡例ページが入るため、deck.json の番号とずれることがある")
    ap.add_argument("--deck-slide", type=int, help="--from-deck 専用: deck.json の N 枚目（1 始まり）から起こす（PPTX 上の枚数目に自動で直す）")
    ap.add_argument("--name", required=True, help="パターン名（英数字・日本語・- _）")
    ap.add_argument("--label", help="一覧に出す表示名（省略時は名前）")
    ap.add_argument("--theme", help="色の寄せ先にするテーマ名（省略時: --from-deck はデッキのテーマ、PPTX は使われている色に一番合う同梱テーマ）")
    ap.add_argument("--dir", help="出力先ディレクトリ（省略時: --from-deck は <deck>/patterns、PPTX は ./patterns）")
    ap.add_argument("--keep-master", action="store_true", help="マスター・レイアウト由来の図形も固定の飾りとして型に残す")
    ap.add_argument("--confirm", action="store_true", help="同名のパターンを上書きすることを承認する")
    args = ap.parse_args(argv)
    if (args.slide is None) == (args.deck_slide is None):
        print("error: --slide（PPTX 上の枚数目）か --deck-slide（deck.json の枚数目。--from-deck 専用）のどちらか 1 つを指定してください", file=sys.stderr)
        return 1
    if args.deck_slide is not None and not args.from_deck:
        print("error: --deck-slide は --from-deck と一緒に指定してください（PPTX を直接指定するときは --slide）", file=sys.stderr)
        return 1
    if not re.fullmatch(r"[\w\-]{1,64}", args.name):
        print("error: --name は英数字・日本語・- _ の 1〜64 文字にしてください", file=sys.stderr)
        return 1
    deck_dir = Path(args.from_deck) if args.from_deck else None
    if deck_dir:
        r = subprocess.run([sys.executable, str(HERE / "build_deck.py"), str(deck_dir)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"error: デッキのビルドに失敗しました。\n{r.stdout[-600:]}{r.stderr[-600:]}", file=sys.stderr)
            return 1
        pptxs = sorted((deck_dir / "build").glob("*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not pptxs:
            print(f"error: {deck_dir}/build に PPTX ができていません", file=sys.stderr)
            return 1
        src = pptxs[0]
    else:
        if not args.src:
            print("error: 元の PPTX（位置引数）か --from-deck を指定してください", file=sys.stderr)
            return 1
        src = Path(args.src)
        if not src.is_file():
            print(f"error: {src} が見つかりません", file=sys.stderr)
            return 1
    out_dir = Path(args.dir) if args.dir else ((deck_dir / "patterns") if deck_dir else Path("patterns"))
    target = out_dir / f"{args.name}.json"
    if target.exists() and not args.confirm:
        print(f"error: {target} が既にあります。上書きしてよいか利用者に確認し、承認を得てから --confirm を付けて再実行してください"
              "（別の名前にすることもできます）。", file=sys.stderr)
        return 1
    import pptx_import as pi
    try:
        imp = pi.Importer(src, tag=True)
    except pi.PptxError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    n_slides = len(imp.prs.slides)
    deck_meta, page_map = None, None
    if deck_dir is not None:
        deck_meta, page_map = _deck_info(deck_dir)
    if args.deck_slide is not None:
        if not page_map or not 1 <= args.deck_slide <= len(page_map["deck_to_pptx"]):
            print(f"error: --deck-slide {args.deck_slide} は範囲外です（deck.json は {len(page_map['deck_to_pptx']) if page_map else '?'} 枚）",
                  file=sys.stderr)
            return 1
        args.slide = page_map["deck_to_pptx"][args.deck_slide - 1]
    if not 1 <= args.slide <= n_slides:
        print(f"error: --slide {args.slide} は範囲外です（この PPTX は {n_slides} 枚）", file=sys.stderr)
        return 1
    if page_map and len(page_map["pptx_to_deck"]) == n_slides:
        m = page_map["pptx_to_deck"][args.slide - 1]
        if m is None:
            print(f"注意: PPTX の {args.slide} 枚目は、ビルドが自動で挿入したページ（凡例ページ等）で、deck.json にはありません。"
                  "deck.json の番号で指定するときは --deck-slide を使ってください")
        else:
            print(f"起こすスライド: PPTX の {args.slide} 枚目 = deck.json の {m[0]} 枚目（type={m[1]}）")
    elif page_map:
        print(f"注意: PPTX は {n_slides} 枚で、deck.json から数えた枚数（{len(page_map['pptx_to_deck'])}）と一致しないため、番号の対応は確かめられません")
    try:
        slides = imp.convert({args.slide})
    except pi.PptxError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    sl = slides[0]
    # 色の寄せ先テーマ
    theme_name, theme = args.theme, None
    if theme_name is None and deck_dir is not None:
        try:
            theme_name = json.loads((deck_dir / "deck.json").read_text(encoding="utf-8")).get("meta", {}).get("theme")
        except (OSError, ValueError):
            theme_name = None
    if theme_name:
        theme = pe._load_theme_for_cli(theme_name, deck_dir)
        if not theme.get("colors"):
            print(f"error: テーマ '{theme_name}' が見つかりません", file=sys.stderr)
            return 1
    else:
        theme_name, theme, frac = pick_theme(sl["elements"], sl.get("background", "#FFFFFF"), deck_dir)
        print(f"色の寄せ先テーマ: {theme_name}（使われている色の {frac * 100:.0f}% が近い色。違うときは --theme で指定）")
    pat, rep = build_pattern(sl, args.name, theme, theme_name, args.keep_master, args.label,
                             f"{src.name} の {args.slide} 枚目", deck_meta)
    errs, warns = pe.check_pattern(pat, theme)
    if errs:
        print("error: 起こした型が検証に通りません（このツールの不具合の可能性があります）:", file=sys.stderr)
        for m in errs[:10]:
            print("  " + m, file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(pat, ensure_ascii=False, indent=1), encoding="utf-8")
    check_dir = out_dir / "_check" / args.name
    cw = make_check_deck(check_dir, pat, sl, theme, theme_name, deck_meta)
    # 報告
    print(f"パターン: {target}")
    print(f"確認用デッキ: {check_dir / 'deck.json'}（python3 tools/build_deck.py {check_dir}）")
    print(f"スロット {len(pat['slots'])} 個: " + "、".join(f"{k}({v['kind']})" for k, v in pat["slots"].items()))
    print(f"色: トークンに寄せたもの {sum(rep['snapped'].values())} か所（{', '.join(f'{k}×{v}' for k, v in rep['snapped'].most_common())}）")
    if rep["unsnapped"]:
        print(f"    寄せ切れず hex のまま残した色 {len(rep['unsnapped'])} 種（テーマを変えても色が変わりません）: "
              + ", ".join(f"{k}×{v}" for k, v in rep["unsnapped"].most_common()))
    if rep["master_dropped"]:
        print(f"マスター・レイアウト由来で型に入れなかった図形 {len(rep['master_dropped'])} 個（--keep-master で残せます）")
    if rep["multi_run"]:
        print(f"複数の書式が混ざる段落 {len(rep['multi_run'])} 個は、先頭の書式で 1 つのスロットにしました: " + "、".join(rep["multi_run"][:5]))
    if rep["deck_vars"]:
        print(f"デッキ名・ブランド名と同じ文言 {len(rep['deck_vars'])} か所は、スロットにせず {{{{deck.title}}}} / {{{{deck.brand}}}} に戻しました")
    if rep["tables"]:
        print(f"表 {rep['tables']} 個は固定のまま（セルの文字はスロットにしていません）")
    if rep["svg"]:
        print(f"アイコン等のベクター図形 {rep['svg']} 個は固定のままです")
    if rep["repeat"]:
        print("繰り返し（repeat）にできる候補（自動では書き換えていません。型の JSON の elements を repeat + grid + template に直すと個数を変えられます）:")
        for desc, names in rep["repeat"]:
            print(f"    - {desc}: {', '.join(names[:6])}")
    for w in warns + cw:
        print(f"warn: {w}")
    if pi.WARNINGS:
        print(f"取り込み時の警告 {len(pi.WARNINGS)} 件（未対応の図形等）: " + " / ".join(pi.WARNINGS[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

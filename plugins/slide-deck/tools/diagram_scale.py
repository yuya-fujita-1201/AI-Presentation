#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""図解（architecture / dataflow / lifecycle / sequence）を、同じ倍率で拡大して描く（S5a）。

合成スライドのブロックに置いた図解は、ブロックが大きいのに文字・箱が自然な大きさ（ノード 14px）のままで、小さく見える。
図を「枠を 1/k にした仮想の領域」に自然な大きさで組み、できた座標・箱・線の太さ・文字を k 倍して、元の枠の中に置く
（HTML と PPTX が同じ幾何を使うので、どちらも同じ結果になる）。k は style.diagram.scale_k（既定 1）。
自動フィット（autofit._fit_diagram）が、折り返し・診断が悪くならない最大の倍率を決める。利用者が scale_k を書けばそれを使う（1 で止まる）。

  layout_grid(slide, kind, d, diags, subject_prefix)   de.layout_grid_diagram と同じ形（scale_k > 1 なら拡大した幾何）
  layout_seq(slide, d, diags, subject_prefix)           de.layout_sequence と同じ形
  scaled_style(d)                                       文字・線・余白のトークンを k 倍した diagram 領域（描画側が読む）
"""
from __future__ import annotations

import copy

import diagram_engine as de

K_MIN = 1.001
_X_KEYS = ("x", "cx", "band_x")
_Y_KEYS = ("y", "cy")
_S_KEYS = ("w", "h", "band_w", "size", "sub_size", "used_h")
# scaled_style が k 倍しないトークン（領域の座標・比率・倍率の指定）
_KEEP = frozenset({"x", "y", "w", "h", "node_wr", "node_hr", "scale_k", "opacity", "weight", "tracking", "line_height"})


def scale_of(d) -> float:
    k = d.get("scale_k", 1) if isinstance(d, dict) else 1
    return float(k) if isinstance(k, (int, float)) and not isinstance(k, bool) and k > K_MIN else 1.0


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def scaled_style(d: dict) -> dict:
    """diagram 領域のトークンを k 倍した写し（x・y・w・h と比率は元のまま）。k = 1 なら d そのもの。"""
    k = scale_of(d)
    if k == 1.0:
        return d
    out = dict(d)
    for key, v in d.items():
        if key in _KEEP or key.startswith(("thin_", "fill_")) or key.endswith(("_ratio", "_wr", "_hr")):
            continue
        if _is_num(v):
            out[key] = v * k
    return out


def _scale(obj, k: float, ox: float, oy: float):
    """幾何の入れ子（dict / list）を、位置は (ox, oy) を原点に k 倍して移し、大きさは k 倍する（破壊的）。"""
    if isinstance(obj, list):
        for it in obj:
            _scale(it, k, ox, oy)
        return obj
    if not isinstance(obj, dict):
        return obj
    for key in list(obj.keys()):
        v = obj[key]
        if key == "points" and isinstance(v, list):
            obj[key] = [[ox + p[0] * k, oy + p[1] * k] for p in v]
        elif key in _X_KEYS and _is_num(v):
            obj[key] = ox + v * k
        elif key in _Y_KEYS and _is_num(v):
            obj[key] = oy + v * k
        elif key in _S_KEYS and _is_num(v):
            obj[key] = v * k
        elif key == "area" and _is_num(v):
            obj[key] = v * k * k
        elif isinstance(v, (dict, list)):
            _scale(v, k, ox, oy)
    return obj


def _virtual(d: dict, k: float) -> dict:
    """枠を 1/k にした領域（原点 0, 0）。トークンは自然な大きさのまま。"""
    v = dict(d)
    v["x"], v["y"] = 0.0, 0.0
    v["w"], v["h"] = float(d["w"]) / k, float(d["h"]) / k
    v["scale_k"] = 1
    return v


def layout_grid(slide: dict, kind: str, d: dict, diags=None, subject_prefix: str = "") -> dict:
    k = scale_of(d)
    if k == 1.0:
        return de.layout_grid_diagram(slide, kind, d, diags, subject_prefix)
    geo = de.layout_grid_diagram(slide, kind, _virtual(d, k), diags, subject_prefix)
    ox, oy = float(d["x"]), float(d["y"])
    for key in ("nodes", "edges", "groups", "col_headers", "row_headers", "text"):
        _scale(geo.get(key), k, ox, oy)
    if geo.get("legend_y") is not None:
        geo["legend_y"] = oy + geo["legend_y"] * k
    geo["legend_h"] = (geo.get("legend_h") or 0.0) * k
    return geo


def layout_seq(slide: dict, d: dict, diags=None, subject_prefix: str = "") -> dict:
    k = scale_of(d)
    if k == 1.0:
        return de.layout_sequence(slide, d, diags, subject_prefix)
    geo = de.layout_sequence(slide, _virtual(d, k), diags, subject_prefix)
    ox, oy = float(d["x"]), float(d["y"])
    for key in ("participants", "messages", "activations", "segments"):
        _scale(geo.get(key), k, ox, oy)
    for key in ("lifeline_top", "lifeline_bottom"):
        if _is_num(geo.get(key)):
            geo[key] = oy + geo[key] * k
    for key in ("col_w", "box_w", "box_h", "pitch", "label_size"):
        if _is_num(geo.get(key)):
            geo[key] = geo[key] * k
    return geo


_BAD_LEVELS = ("error", "warn", "warning")


def _diag_keys(diags) -> set:
    """診断（error / warning）の中身の集合 {(code, subject)}。件数ではなく中身で比べる（同じ件数でも別の診断に入れ替わるのを見逃さない）。
    diagram_engine の診断の level は "error" / "warning"（"warn" ではない）。"""
    return {(x.get("code"), x.get("subject")) for x in diags or [] if isinstance(x, dict) and x.get("level") in _BAD_LEVELS}


def _has_blocking(diags) -> bool:
    """拡大してはいけない診断（error 級・too-dense）が k=1 にあるか。"""
    return any(isinstance(x, dict) and x.get("level") in _BAD_LEVELS and (x.get("level") == "error" or x.get("code") == "too-dense") for x in diags or [])


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _extent(obj, box: list) -> None:
    """幾何の入れ子から、描かれる要素（x, y, w, h を持つ矩形・points の点）の外接矩形 box = [minx, miny, maxx, maxy] を求める（破壊的）。"""
    if isinstance(obj, list):
        for it in obj:
            _extent(it, box)
        return
    if not isinstance(obj, dict):
        return
    if all(_num(obj.get(k)) for k in ("x", "y", "w", "h")):
        box[0], box[1] = min(box[0], obj["x"]), min(box[1], obj["y"])
        box[2], box[3] = max(box[2], obj["x"] + obj["w"]), max(box[3], obj["y"] + obj["h"])
    elif all(_num(obj.get(k)) for k in ("cx", "cy", "w", "h")):
        box[0], box[1] = min(box[0], obj["cx"] - obj["w"] / 2), min(box[1], obj["cy"] - obj["h"] / 2)
        box[2], box[3] = max(box[2], obj["cx"] + obj["w"] / 2), max(box[3], obj["cy"] + obj["h"] / 2)
    for key, v in obj.items():
        if key == "points" and isinstance(v, list):
            for p_ in v:
                if isinstance(p_, (list, tuple)) and len(p_) >= 2 and _num(p_[0]) and _num(p_[1]):
                    box[0], box[1], box[2], box[3] = min(box[0], p_[0]), min(box[1], p_[1]), max(box[2], p_[0]), max(box[3], p_[1])
        elif isinstance(v, (dict, list)) and key not in ("grid", "diagnostics", "text"):
            _extent(v, box)


def overflow_px(geo: dict, d: dict) -> float:
    """最終的に描く幾何 geo（scale_k を掛けた座標）が、図の枠 d（x, y, w, h）からはみ出す量（px。収まっていれば 0）。"""
    box = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for key in ("nodes", "edges", "groups", "col_headers", "row_headers", "participants", "messages", "activations", "segments"):
        _extent(geo.get(key), box)
    if _num(geo.get("legend_y")):
        box[3] = max(box[3], geo["legend_y"] + (geo.get("legend_h") or 0.0))
    if _num(geo.get("lifeline_bottom")):
        box[3] = max(box[3], geo["lifeline_bottom"])
    if box[0] == float("inf"):
        return 0.0
    x, y, w, h = (float(d.get(k, 0)) for k in ("x", "y", "w", "h"))
    return max(0.0, x - box[0], y - box[1], box[2] - (x + w), box[3] - (y + h))


def _text_lines(kind: str, slide: dict, geo: dict, d: dict) -> dict:
    """ノードごとの (見出しの大きさ, 見出しの行, 補足の行)。grid は geo["text"]、sequence は check_node_text。"""
    if kind == "sequence":
        fit = de.check_node_text(geo["participants"], d.get("node_size", 14), d.get("sub_size", 11), d.get("node_pad", 8), [],
                                 icon_w=d.get("icon_size", 16) + 6)
    else:
        fit = geo.get("text") or {}
    return {nid: (f.get("size"), list(f.get("lines") or []), list(f.get("sub_lines") or [])) for nid, f in fit.items()}


def _layout_at(slide: dict, kind: str, d: dict, k: float, diags: list):
    """倍率 k で描く幾何（最終の描画と同じ diagram_scale.layout_*）と、そのときの診断（引数 diags と幾何の diagnostics）。"""
    dk = dict(d)
    dk["scale_k"] = k
    geo = layout_seq(slide, dk, diags) if kind == "sequence" else layout_grid(slide, kind, dk, diags)
    return geo, list(diags) + list(geo.get("diagnostics") or [])


def best_scale(slide: dict, kind: str, d: dict, kmax: float, size_cap: float, step: float = 0.05):
    """図を拡大する倍率 k（最大 kmax・見出し文字が size_cap を超えない範囲）。次の全部を満たす最大の k を返す。満たす k が無ければ (1.0, None)。
      - k = 1 のときに無かった診断（error / warning。code と subject で比べる）が 1 つも増えない
      - k = 1 に error 級・too-dense の診断があるときは拡大しない（密すぎる図を大きくしない）
      - 最終的に描く幾何（scale_k を掛けた座標）が、k = 1 より枠の外へはみ出さない（枠の外にあるものは、枠内に収まるか k = 1 以下）
      - 図の文字が縮まない・折り返しが増えない・最終行が 1〜2 字にならない
    None の位置には試した理由を入れる（info 用）。"""
    d1 = dict(d)
    d1["scale_k"] = 1
    try:
        geo1, diags1 = _layout_at(slide, kind, d1, 1, [])
    except Exception:
        return 1.0, None
    if _has_blocking(diags1):
        return 1.0, None
    base_keys = _diag_keys(diags1)
    base_ov = overflow_px(geo1, d1)
    base = _text_lines(kind, slide, geo1, d1)
    node_size = float(d.get("node_size", 14))
    kmax = min(kmax, size_cap / max(node_size, 1.0))
    k = kmax
    while k > 1.04:
        kk = round(k, 3)
        try:
            diags: list = []
            dv = _virtual(d, kk)          # 自然な大きさの仮想の領域（k 倍する前）で、文字の折り返しと診断を見る
            geo = de.layout_sequence(slide, dv, diags) if kind == "sequence" else de.layout_grid_diagram(slide, kind, dv, diags)
            cand = _text_lines(kind, slide, geo, dv)
            ok = _diag_keys(list(diags) + list(geo.get("diagnostics") or [])) <= base_keys
            if ok:
                geo_f, diags_f = _layout_at(slide, kind, d1, kk, [])      # 最終に描く幾何と診断（仮想の判定が最終と食い違わないことの確認）
                ok = _diag_keys(diags_f) <= base_keys and overflow_px(geo_f, d1) <= max(base_ov, 0.0) + 0.5
        except Exception:
            k -= step
            continue
        if ok:
            for nid, (sz0, ln0, sub0) in base.items():
                sz1, ln1, sub1 = cand.get(nid, (None, None, None))
                if sz1 is None or sz1 < sz0 - 0.01 or len(ln1) > len(ln0) or len(sub1) > len(sub0):
                    ok = False
                    break
                # 折り返した最終行が 1〜2 字（泣き別れ）になるのは避ける（増える場合）
                for a, b in ((ln0, ln1), (sub0, sub1)):
                    if len(b) > 1 and len((b[-1] or "").strip()) < 3 and not (len(a) > 1 and len((a[-1] or "").strip()) <= len((b[-1] or "").strip())):
                        ok = False
                if not ok:
                    break
        if ok:
            return kk, None
        k -= step
    return 1.0, None

# -*- coding: utf-8 -*-
"""deck.json / テーマ JSON の「既知のキー」と「値の形」の表（標準ライブラリのみ・副作用なし）。

build_deck.validate_deck が、打ち間違い（未知のキー）の警告と、型違いの入力（配列のはずが文字列など）の
fail に使う。ここは表と純関数だけを持ち、fail / warn は呼び出し側が行う（戻り値は (level, 本文) のリスト）。

新しいスライドタイプを足すとき、この表で触るのは次の 1 か所:
    SLIDE_KEYS["新タイプ"] = {"title", "lead", ...}       # スライド直下の既知キー（共通キーは書かなくてよい）
    SLIDE_SHAPES["新タイプ"] = {"items": ("list", "str")}   # 任意: 内容フィールドの形（型違いを fail にする）
（style の領域名・プロパティ名はレイアウト JSON の既定値から自動で決まる。EXTRA_STYLE_PROPS は
  既定値に無いがコードが読むプロパティだけ。）
"""
from __future__ import annotations

import difflib
import re

# ---------------------------------------------------------------------------
# スライド直下の既知キー
# ---------------------------------------------------------------------------

# 全タイプ共通（どのタイプに書いても無警告）。`_` で始まるキーは常に除外（利用者のメモ用）
UNIVERSAL_SLIDE_KEYS = frozenset({
    "type", "notes", "style", "relation", "eyebrow", "conclusion", "source", "line_balance", "title",
    "autofit", "density", "pattern", "blocks",   # 後の段階（自動フィット・密度・パターン・合成スライド）で使うキー
})

# タイプ固有のキー。diagram_engine が自前で未知キー検査をする 4 タイプ（SELF_CHECKED）は、
# 型の検査だけをここで行い、未知キーの警告は diagram_engine 側に任せる。
SLIDE_KEYS = {
    "title": {"subtitle", "meta", "background", "variant"},
    "section": {"number", "subtitle", "background", "variant"},
    "bullets": {"lead", "bullets"},
    "two_column": {"lead", "left", "right", "connector"},
    "table": {"lead", "columns", "rows", "row_header", "total_row"},
    "status_table": {"lead", "columns", "rows", "legend", "legend_title"},
    "code": {"lead", "language", "code", "annotations"},
    "quote": {"text", "attribution", "background", "variant"},
    "image": {"path", "caption", "fit", "caption_position", "overlay", "opacity", "position"},
    "image_text": {"punch", "bullets", "path", "caption", "image_side", "bleed", "position"},
    "closing": {"bullets", "message", "background", "variant"},
    "agenda": {"lead", "items", "num_start"},
    "steps": {"lead", "steps", "header_style"},
    "matrix": {"lead", "x_axis", "y_axis", "quadrants", "points"},
    "cards": {"lead", "cards", "columns"},
    "swimlane": {"lead", "cols", "phases", "lanes", "nodes", "edges", "legend", "legend_title",
                 "legend_eyebrow", "legend_items"},
    "swimlane_legend": {"lead", "items"},
    "diagram_legend": {"lead", "items"},
    "architecture": {"lead"},
    "dataflow": {"lead"},
    "lifecycle": {"lead"},
    "sequence": {"lead"},
    "schedule": {"lead", "timeline", "columns", "periods", "today", "rows", "legend", "legend_labels", "note"},
    "summary": {"lead", "items"},
    "reasons": {"lead", "left_heading", "right_heading", "issues", "strengths"},
    "statement": {"message", "kicker", "support", "background", "variant"},
    "row_matrix": {"lead", "columns", "rows", "header_style", "emph_col", "col_ratios", "corner"},
    "org": {"lead", "left", "right", "links", "legend"},
    "house": {"lead", "roof", "pillars", "foundations"},
    "cycle": {"lead", "center", "stages"},
    "kpi_tree": {"lead", "root", "headers", "branches"},
    "canvas": {"background", "elements", "name"},
    "split": {"lead", "columns", "rows", "arrange", "side", "ratio", "panel"},     # blocks は共通キー（合成スライドと同じ）
    "composite": {"lead", "columns", "rows", "arrange"},      # blocks は共通キー。ブロックの中身は composite_engine / build_deck が検証する
    "pattern": {"lead", "slots"},      # pattern（パターン名）は共通キー。kpi / chart は engine_registry に登録したキー表から引く
}
SELF_CHECKED = frozenset({"architecture", "dataflow", "lifecycle", "sequence"})

META_KEYS = frozenset({
    "id", "title", "subtitle", "author", "date", "as_of", "theme", "layout", "layout_overrides", "brand",
    "line_balance",
    "density", "autofit", "shape", "section_numbers", "variants", "todo_marks",
})

# テーマ JSON
THEME_TOP_KEYS = frozenset({"name", "label", "description", "colors", "fonts", "extends", "alias_of",
                            "layout", "tokens", "shape"})
THEME_FONT_KEYS = ("heading", "body", "code")
# レイアウト JSON
LAYOUT_TOP_KEYS = frozenset({"name", "description", "extends", "canvas", "common", "types", "densities", "tokens",
                            "variants", "palettes", "variant_defaults", "todo_color", "todo_color_on_dark", "todo_bg", "readable_pairs"})


def hint(key, pool, cutoff: float = 0.6) -> str:
    """difflib の既存流儀の「（候補: xxx）」。無ければ空文字。"""
    m = difflib.get_close_matches(str(key), sorted(str(p) for p in pool), n=1, cutoff=cutoff)
    return f"（もしかして \"{m[0]}\"）" if m else ""


# AI が書きがちな名前の取り違え（誤ったキー → 正しいキーの候補。候補のうち、その場で使えるキーだけを採用する）
KEY_ALIASES = {
    "items": ("bullets", "cards", "steps", "rows"), "bullet": ("bullets",), "list": ("bullets", "items"),
    "points": ("bullets",), "content": ("bullets", "body", "text"), "contents": ("bullets", "body", "text"),
    "headers": ("columns",), "header": ("columns", "heading"), "head": ("columns", "heading"),
    "column_headers": ("columns",), "data": ("rows",), "row": ("rows",), "column": ("columns",),
    "title": ("heading", "label", "name"), "name": ("label", "heading"), "heading": ("label", "title"),
    "desc": ("body", "text", "sublabel"), "description": ("body", "text", "sublabel"), "detail": ("body", "text"),
    "body": ("bullets", "text", "message"), "text": ("body", "message", "bullets", "label"),
    "subtitle": ("lead",), "sub": ("sublabel", "lead"), "subheading": ("sublabel", "lead"),
    "img": ("path",), "image": ("path",), "src": ("path",), "file": ("path",),
    "author": ("attribution",), "cite": ("attribution",), "source_text": ("source",),
    "quote": ("text",), "cols": ("columns",), "step": ("steps",), "card": ("cards",),
}


def suggest(key, pool) -> str:
    """未知キーの「もしかして」。よくある別名の表を先に当て、無ければ綴りの近さ（厳しめ）で探す。"""
    pool = set(str(p) for p in pool)
    for cand in KEY_ALIASES.get(str(key), ()):
        if cand in pool:
            return f"（もしかして \"{cand}\"）"
    return hint(key, pool, cutoff=0.75)


def type_slide_keys(t: str):
    """タイプ t のスライド直下の固有キー（共通キーを除く）。この表に無くても、登録表（engine_registry）に
    slide_keys つきで登録された A 型タイプ（kpi / chart など）はそこから引く。どちらにも無ければ None。"""
    if t in SLIDE_KEYS:
        return SLIDE_KEYS[t]
    try:
        import engine_registry
        spec = engine_registry.get(t)
    except Exception:       # pragma: no cover  （登録表を読めなくても検証は止めない）
        spec = None
    if spec is not None and spec.slide_keys:
        return spec.slide_keys
    return None


def known_slide_keys(t: str):
    """タイプ t のスライド直下で既知のキー全体。表に無いタイプ（レイアウト JSON だけで足した型など）は None。"""
    own = type_slide_keys(t)
    if own is None:
        return None
    return UNIVERSAL_SLIDE_KEYS | own


# 2.0.0 までの pptx_import.py が書いたメモ用のキー（いまは _source / _generator / _source_page）。古い取り込み結果を警告なしで読む
LEGACY_META_KEYS = frozenset({"source", "generator"})
LEGACY_CANVAS_SLIDE_KEYS = frozenset({"source_page"})


def unknown_slide_keys(slide: dict, t: str) -> list:
    """スライド直下の未知キー → [(level, 本文)]。`_` 始まりと共通キーは除外。"""
    known = known_slide_keys(t)
    if known is None or t in SELF_CHECKED:
        return []
    out = []
    for key in slide:
        if not isinstance(key, str) or key.startswith("_") or key in known:
            continue
        if t == "canvas" and key in LEGACY_CANVAS_SLIDE_KEYS:
            continue
        usable = " / ".join(sorted(type_slide_keys(t)))
        out.append(("warn", f"未知のキー \"{key}\" は無視されます{suggest(key, known)}"
                            f" → {t} の固有キー: {usable or 'なし'}（title / notes / style などの共通キーも使える）。"
                            f"キー名を直す（メモなら先頭に _ を付ける）"))
    return out


def unknown_meta_keys(meta: dict) -> list:
    out = []
    for key in meta:
        if isinstance(key, str) and (key.startswith("_") or key in META_KEYS or key in LEGACY_META_KEYS):
            continue
        out.append(("warn", f"meta の未知のキー \"{key}\" は無視されます{hint(key, META_KEYS)}"
                            f" → meta に書けるキーは {' / '.join(sorted(META_KEYS))}"))
    return out


# ---------------------------------------------------------------------------
# 値の形（型違いの検出）
# ---------------------------------------------------------------------------
# 形の書き方:
#   "text"  文字列または数値（None は「無し」。ビルド前に文字列へそろえる）
#   "str"   文字列だけ
#   "num"   数値（bool は不可）   "int" 整数   "bool" 真偽
#   "any"   何でもよい
#   ("list", 要素の形)   ("dict", {キー: 形} または None, 閉じているか)   ("or", 形, 形, ...)

BULLET_CHILD = ("or", "str", ("dict", {"text": "text", "size": "num", "color": "str", "bold": "bool"}, False))
BULLET_ITEM = ("or", "str", ("dict", {"text": "text", "children": ("list", BULLET_CHILD),
                                      "size": "num", "color": "str", "bold": "bool"}, False))
BULLETS = ("list", BULLET_ITEM)
TEXT_LIST = ("list", "str")
DICT_LIST = ("list", ("dict", None, False))
# 表のセル: 文字列・数値・null・{text,url}・複数行 ... （要素の形は固定しない）
ROWS = ("list", ("list", "any"))
# table の行: セルの配列、または {"cells": [...], "emphasis": true}（行の強調。セルは {"text", "tone", "url"} でもよい）
TABLE_ROWS = ("list", ("or", ("list", "any"), ("dict", {"cells": ("list", "any"), "emphasis": "bool"}, False)))

# 図解タイプのノード・エッジ（キーの打ち間違いの警告は diagram_engine 側。ここは値の型だけ）
DIAGRAM_NODE = ("dict", {"id": "id", "label": "text", "text": "text", "sublabel": "text", "tag": "text",
                         "type": "str", "variant": "str", "kind": "str", "row": "int", "col": "int"}, False)
DIAGRAM_EDGE = ("dict", {"from": "id", "to": "id", "label": "text", "variant": "str", "arrow": "str",
                         "route": "str", "style": "str"}, False)
DIAGRAM_NODES = ("list", DIAGRAM_NODE)
# グリッド図の見出し帯（列: stages / col_headers / phases、行: lanes / row_headers）
DIAGRAM_HEADERS = {"stages": ("list", "text"), "col_headers": ("list", "text"), "row_headers": ("list", "text"),
                   "phases": ("list", "text"), "lanes": ("list", ("or", "text", ("dict", None, False)))}
DIAGRAM_EDGES = ("list", DIAGRAM_EDGE)

SLIDE_SHAPES = {
    "composite": {"lead": "text", "columns": ("list", "num"), "rows": ("list", "num"), "arrange": "str",
                  "blocks": ("list", ("dict", None, False))},
    "split": {"lead": "text", "columns": ("list", "num"), "rows": ("list", "num"), "arrange": "str", "side": "str", "ratio": "num",
              "panel": ("dict", None, False), "blocks": ("list", ("dict", None, False))},
    "pattern": {"lead": "text", "slots": ("dict", None, False)},      # スロットの中身はパターン側の定義（pattern_engine）で検証する
    "title": {"title": "text", "subtitle": "text", "meta": "text", "variant": "str", "background": ("or", "str", ("dict", None, False))},
    "section": {"number": "text", "title": "text", "subtitle": "text", "variant": "str", "background": ("or", "str", ("dict", None, False))},
    "bullets": {"lead": "text", "bullets": BULLETS},
    "two_column": {"lead": "text", "connector": "text",
                   "left": ("dict", {"heading": "text", "bullets": BULLETS}, True),
                   "right": ("dict", {"heading": "text", "bullets": BULLETS}, True)},
    "table": {"lead": "text", "columns": ("list", ("or", "str", "num", ("dict", None, False))), "rows": TABLE_ROWS,
              "row_header": "bool", "total_row": "bool"},
    "status_table": {"lead": "text", "columns": TEXT_LIST, "rows": DICT_LIST},
    "code": {"lead": "text", "language": "text", "code": "str",
             "annotations": ("list", ("dict", {"line": "num", "title": "text", "text": "text"}, False))},
    "quote": {"text": "text", "attribution": "text", "variant": "str", "background": ("or", "str", ("dict", None, False))},
    "image": {"path": "str", "caption": "text", "fit": "str", "caption_position": "str", "overlay": "str", "opacity": "num", "position": "str"},
    "image_text": {"punch": "text", "bullets": BULLETS, "path": "str", "caption": "text", "image_side": "str", "bleed": "bool", "position": "str"},
    "closing": {"bullets": BULLETS, "message": "text", "variant": "str", "background": ("or", "str", ("dict", None, False))},
    "agenda": {"lead": "text", "items": ("list", ("or", "str", ("dict", {"text": "text", "desc": "text",
                                                                           "active": "bool"}, True)))},
    "steps": {"lead": "text", "header_style": "str",
              "steps": ("list", ("dict", {"label": "text", "items": BULLETS}, True))},
    "matrix": {"lead": "text",
               "x_axis": ("dict", {"label": "text", "low": "text", "high": "text"}, True),
               "y_axis": ("dict", {"label": "text", "low": "text", "high": "text"}, True),
               "quadrants": ("list", ("dict", {"heading": "text", "body": "text", "highlight": "bool"}, True)),
               "points": ("list", ("dict", {"label": "text", "x": "num", "y": "num", "highlight": "bool"}, False))},
    "cards": {"lead": "text", "columns": "int",
              "cards": ("list", ("dict", {"heading": "text", "body": "text", "items": BULLETS, "icon": "str", "emphasis": "any", "span": "int"}, True))},
    "swimlane": {"lead": "text", "cols": "int", "phases": ("list", "text"),
                 "lanes": ("list", ("dict", {"group": "text", "name": "text"}, False)),
                 "nodes": ("list", ("dict", {"id": "id", "lane": "int", "col": "int", "shape": "str", "variant": "str",
                                             "kind": "str", "text": "text", "label": "text"}, False)),
                 "edges": ("list", ("dict", {"from": "id", "to": "id", "label": "text", "variant": "str",
                                             "style": "str"}, False))},
    "architecture": {"lead": "text", "nodes": DIAGRAM_NODES, "edges": DIAGRAM_EDGES, "groups": DICT_LIST,
                     **DIAGRAM_HEADERS},
    "dataflow": {"lead": "text", "nodes": DIAGRAM_NODES, "edges": DIAGRAM_EDGES, "flows": DIAGRAM_EDGES,
                 "groups": DICT_LIST, **DIAGRAM_HEADERS},
    "lifecycle": {"lead": "text", "states": DIAGRAM_NODES, "nodes": DIAGRAM_NODES, "transitions": DIAGRAM_EDGES,
                  "edges": DIAGRAM_EDGES, "groups": DICT_LIST, **DIAGRAM_HEADERS},
    "sequence": {"lead": "text", "participants": DICT_LIST, "messages": DICT_LIST, "activations": DICT_LIST,
                 "segments": DICT_LIST},
    "schedule": {"lead": "text", "periods": DICT_LIST, "rows": DICT_LIST, "note": "text"},
    "summary": {"lead": "text", "items": ("list", ("or", "str", ("dict", None, False)))},
    "reasons": {"lead": "text", "left_heading": "text", "right_heading": "text",
                "issues": ("list", ("or", "str", ("dict", None, False))),
                "strengths": ("list", ("or", "str", ("dict", None, False)))},
    "statement": {"message": "text", "kicker": "text", "support": "text", "variant": "str", "background": ("or", "str", ("dict", None, False))},
    "row_matrix": {"lead": "text", "rows": DICT_LIST, "columns": ("list", ("or", "str", ("dict", None, False)))},
    "org": {"lead": "text", "links": DICT_LIST,
            "left": ("dict", {"title": "text", "nodes": DICT_LIST}, False),
            "right": ("dict", {"title": "text", "nodes": DICT_LIST}, False)},
    "house": {"lead": "text", "roof": ("dict", None, False), "pillars": ("list", ("or", "str", ("dict", None, False))),
              "foundations": ("list", ("or", "str", ("dict", None, False)))},
    "cycle": {"lead": "text", "center": "text", "stages": ("list", ("or", "str", ("dict", None, False)))},
    "kpi_tree": {"lead": "text", "root": "text", "headers": ("list", "text"), "branches": ("list", ("or", "str", ("dict", None, False)))},
}
# 全タイプ共通のフィールド
COMMON_SHAPES = {"eyebrow": "text", "title": "text", "conclusion": "text", "source": "text",
                 "notes": "text", "style": ("dict", None, False)}

_SCALARS = {"text": "文字列（または数値）", "str": "文字列", "num": "数値", "int": "整数", "bool": "true / false",
            "id": "文字列または整数の id"}


def describe(shape) -> str:
    """期待する形の説明（日本語）。"""
    if isinstance(shape, str):
        return _SCALARS.get(shape, "任意の値")
    kind = shape[0]
    if kind == "list":
        return f"配列（要素は{describe(shape[1])}）" if shape[1] != "any" else "配列"
    if kind == "dict":
        return "オブジェクト（{ … }）"
    if kind == "or":
        return " または ".join(describe(s) for s in shape[1:])
    return "任意の値"


def _vtype(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "真偽値"
    if isinstance(v, (int, float)):
        return "数値"
    if isinstance(v, str):
        return "文字列"
    if isinstance(v, list):
        return "配列"
    if isinstance(v, dict):
        return "オブジェクト"
    return type(v).__name__


def _matches_scalar(v, shape: str) -> bool:
    if shape == "any":
        return True
    if shape == "text":
        return isinstance(v, str) or (isinstance(v, (int, float)) and not isinstance(v, bool))
    if shape == "str":
        return isinstance(v, str)
    if shape == "num":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if shape == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if shape == "id":
        return isinstance(v, str) or (isinstance(v, int) and not isinstance(v, bool))
    if shape == "bool":
        return isinstance(v, bool)
    return True


def check_shape(value, shape, path: str, issues: list) -> None:
    """value が shape に合うか。違反は issues に (level, 本文) を足す（最初の違反で止めず、同じ配列では 1 件だけ）。"""
    if value is None:
        return   # null は「書いていない」と同じ扱い（トップレベルは呼び出し側で取り除く）
    if isinstance(shape, str):
        if not _matches_scalar(value, shape):
            if shape == "bool":    # 真偽値は ASCII の語が日本語に挟まるので空白を入れ、直し方（書く値・書かない選択）を添える
                key = re.split(r"[.\[\]]", path)[-1] or path
                issues.append(("fail", f"{path} は true / false で指定してください（{_vtype(value)}が書かれています）"
                                       f" → \"{key}\": true か false（使わないなら書かない）"))
            else:
                issues.append(("fail", f"{path} は{describe(shape)}で指定してください（{_vtype(value)}が書かれています）"))
        return
    kind = shape[0]
    if kind == "or":
        # 先に合う形があれば OK。値の種類（文字列/オブジェクト/配列）が合う候補があれば、その候補の中の誤りを報告し、
        # どれにも合わなければ全候補の説明で報告する
        for s in shape[1:]:
            probe: list = []
            check_shape(value, s, path, probe)
            if not any(lv == "fail" for lv, _ in probe):
                issues.extend(probe)   # 通っても warn は引き継ぐ
                return
        for s in shape[1:]:
            same_kind = (isinstance(s, str) and _matches_scalar(value, s)) or \
                        (not isinstance(s, str) and ((s[0] == "dict" and isinstance(value, dict))
                                                    or (s[0] == "list" and isinstance(value, list))))
            if same_kind:
                check_shape(value, s, path, issues)
                return
        issues.append(("fail", f"{path} は{describe(shape)}で指定してください（{_vtype(value)}が書かれています）"))
        return
    if kind == "list":
        if not isinstance(value, list):
            issues.append(("fail", f"{path} は{describe(shape)}で指定してください（{_vtype(value)}が書かれています）"))
            return
        for idx, el in enumerate(value):
            if el is None and shape[1] == "any":
                continue
            if el is None:
                issues.append(("fail", f"{path}[{idx}] が null です（{describe(shape[1])}で指定してください）"))
                return
            sub: list = []
            check_shape(el, shape[1], f"{path}[{idx}]", sub)
            if sub:
                issues.extend(sub)
                if any(lv == "fail" for lv, _ in sub):
                    return   # 同じ配列で fail は 1 件だけ報告する
        return
    if kind == "dict":
        if not isinstance(value, dict):
            issues.append(("fail", f"{path} は{describe(shape)}で指定してください（{_vtype(value)}が書かれています）"))
            return
        fields, closed = shape[1], (shape[2] if len(shape) > 2 else False)
        if not fields:
            return
        for k, v in value.items():
            if k in fields:
                check_shape(v, fields[k], f"{path}.{k}", issues)
            elif closed and isinstance(k, str) and not k.startswith("_"):
                issues.append(("warn", f"{path} の未知のキー \"{k}\" は無視されます{suggest(k, fields)}"
                                       f" → 使えるキー: {' / '.join(fields)}"))
        return


def check_slide_shapes(slide: dict, t: str) -> list:
    """スライドの内容フィールドの型検査 → [(level, 本文)]（本文の先頭にスライド番号は付けない）。"""
    issues: list = []
    shapes = dict(COMMON_SHAPES)
    shapes.update(SLIDE_SHAPES.get(t, {}))
    for key, shape in shapes.items():
        if key in slide:
            check_shape(slide[key], shape, key, issues)
    if t == "agenda" and isinstance(slide.get("items"), list):
        for idx, it in enumerate(slide["items"]):
            if isinstance(it, dict) and not str(it.get("text") or "").strip():
                alt = next((k for k in ("title", "label", "name", "heading") if isinstance(it.get(k), str) and it[k].strip()), None)
                issues.append(("warn", f"items[{idx}] に text（項目名）がありません。番号だけの行になります"
                                       f" → {'\"' + alt + '\" ではなく ' if alt else ''}\"text\" に項目名を書く（例: {{\"text\": \"現状と課題\", \"desc\": \"補足\"}}）"))
    return issues


# ---------------------------------------------------------------------------
# style / layout_overrides の領域の中のプロパティ
# ---------------------------------------------------------------------------

# どの領域でも読まれる共通プロパティ
COMMON_STYLE_PROPS = frozenset({
    "x", "y", "w", "h", "size", "color", "fill", "bold", "italic", "align", "valign", "line_height", "gap",
    "pad", "radius", "text", "border_color", "border_w", "font", "opacity", "shadow", "nowrap",
})
# レイアウト JSON の既定値には無いが、コードが読む（または文書に載っている）プロパティ
EXTRA_STYLE_PROPS = frozenset({
    "fit", "min_h", "row_fills", "total_fill", "label_fill", "label_color", "min_size", "sizes", "follow_body",
    "scale_k", "min_y", "y_no_lead", "h_no_lead", "y_no_conclusion", "reserve", "max_cols", "col_gap", "row_h",
    "col_widths", "text_color", "head_size", "head_fill", "head_color", "num_w", "num_size", "num_fill",
    "num_color", "band_fill", "lead_color", "label_pos", "icon_style", "icon_tile_size", "type_labels",
})
# 数値であるべきプロパティ。ここに無くても、レイアウトの既定値が数値のプロパティは数値として検査する
NUMERIC_STYLE_PROPS = frozenset({"x", "y", "w", "h", "size", "line_height", "gap", "pad", "radius", "row_h",
                                 "max_cols", "col_gap", "min_size", "min_h", "border_w", "opacity"})
INT_STYLE_PROPS = frozenset({"max_cols", "cols"})   # 1 以上の整数
# 0 以上であるべきもの / 0 より大きいもの（x, y は負でもよい）
NONNEG_STYLE_PROPS = frozenset({"w", "h", "gap", "pad", "radius", "row_h", "col_gap", "min_size", "min_h", "border_w"})
NONNEG_SUFFIXES = ("_w", "_h", "_gap", "_pad", "_radius")
POSITIVE_STYLE_PROPS = frozenset({"size", "line_height", "max_cols", "cols"})
# 自動フィットのトークン（S4）の範囲。極端な値で探索が終わらなくなる・意味のない値を黙って受け取らないための上限と下限（含む）
TOKEN_RANGES = {
    "thin_grow": (1.0, 4.0), "thin_text_grow": (1.0, 4.0),            # 文字の拡大の倍率の上限（1 = 大きくしない）
    "thin_max_size": (1.0, 200.0), "thin_label_max_size": (1.0, 200.0),   # 拡大後の文字サイズの上限(px)
    "thin_trigger": (0.0, 1.0), "thin_target": (0.0, 1.0),            # 中身が枠の何割未満なら整えるか／整えたあとの割合
    "safety": (0.5, 1.0), "detect_level": (1, 3), "max_back_em": (0.0, 60.0),      # common.wrap（語の途中で折れる文の文節折り返し。S5b）
    "max_extra_lines": (0, 5), "min_px": (0.0, 200.0),
    "center_ratio": (0.0, 1.0), "thin_center_ratio": (0.0, 1.0),      # 縦中央に置く条件（0 で無効）
    "thin_fill_aspect": (0.5, 20.0), "thin_fill_min_size": (1.0, 200.0),                                 # steps のカードを枠いっぱいに広げる高さ／幅の上限
    "clear_gap": (0.0, 400.0),                                        # brand とタイトルの間の余白(px)
    "fill_trigger": (0.0, 1.0), "fill_target": (0.0, 1.0), "fill_grow": (1.0, 4.0), "fill_text_grow": (1.0, 4.0),   # schedule の 4 行以上の行の高さの配り方（S5a）
    "thin_min_ratio": (0.0, 1.0), "thin_valign_ratio": (0.0, 1.0), "thin_legacy_ratio": (0.0, 1.0),    # 単独の cards の箱の高さの下限・agenda の縦の置き位置（S5a）
    "scale_k": (1.0, 4.0),                                            # 合成ブロックの図解（style.diagram）・org / kpi_tree（style.body）の拡大の倍率（1 で拡大しない。上限は thin_grow と同じ）
}
BOOL_TOKEN_PROPS = frozenset({"thin_fill", "cols_search", "auto_before"})
INT_TOKEN_PROPS = frozenset({"detect_level", "max_extra_lines"})        # common.wrap の整数（2.5 のような小数を黙って切り捨てない）
# 数値の上限。極端な値（1e6 や 2^53 以上）で自動フィットの 1px ずつの探索が終わらなくならないための、現実の使い方より十分大きい値
MAX_TEXT_SIZE = 2000.0       # 文字サイズ（size・*_size）の上限(px)
MAX_EXTENT = 1e5             # 位置・寸法・間隔など、そのほかの数値の絶対値の上限
MAX_LINE_HEIGHT = 100.0      # line_height（文字サイズの倍率）の上限
MAX_COLS = 1000              # cols / max_cols の上限
# 値のヒントに使う例（既定は 24）。common.wrap の安全率に「24」の例を出さない
TOKEN_EXAMPLES = {"safety": "0.9", "detect_level": "3", "max_back_em": "10", "max_extra_lines": "1", "min_px": "0",
                  "thin_grow": "1.4", "thin_text_grow": "1.4", "scale_k": "1.4", "thin_trigger": "0.5", "thin_target": "0.7"}
WRAP_TOKEN_KEYS = frozenset({"safety", "detect_level", "max_back_em", "max_extra_lines", "min_px"})
POSITIVE_SUFFIXES = ("_size",)
# 取りうる値が決まっているプロパティ（HTML の style にそのまま出るため、それ以外は fail）
ENUM_STYLE_PROPS = {"align": ("left", "center", "right"), "valign": ("top", "middle", "bottom"),
                    "fit": ("content", "fill"), "case": ("upper", "none"), "shadow": ("none", "soft"), "thin_fill_valign": ("top", "middle")}
# 形トークン由来のプロパティの範囲（shape_engine.TOKEN_KINDS の weight / tracking と同じ）
WEIGHT_RANGE = (100, 900)
TRACKING_RANGE = (-0.2, 0.6)
MIN_PPTX_SIZE = 1.4   # px。PowerPoint の文字サイズは 1pt（約 1.33px）以上
MIN_READABLE_SIZE = 8   # px。これ未満は warn


MAX_IMAGE_PIXELS = 80_000_000      # 画像の画素数の上限（幅 × 高さ。8000 万画素 ≒ 10000×8000）。これを超えるとメモリを使い切るので置き直してもらう
_IMAGE_SIZE_CACHE: dict = {}


def image_too_big(path, rel=None):
    """画像ファイル path の画素数が MAX_IMAGE_PIXELS を超えるときの説明文（幅×高さ・直し方）。超えない・調べられない（SVG・Pillow なし・壊れている）ときは None。
    ヘッダーだけを読む（画素は読み込まない）。PIL の DecompressionBombWarning は出さない。同じファイルは 1 回しか調べない。"""
    from pathlib import Path
    p = Path(path)
    if p.suffix.lower() == ".svg":
        return None
    try:
        key = (str(p), p.stat().st_mtime_ns)
    except OSError:
        return None
    if key in _IMAGE_SIZE_CACHE:
        return _IMAGE_SIZE_CACHE[key]
    msg = None
    try:
        import warnings
        from PIL import Image
        old = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with Image.open(p) as im:
                    w, h = im.size
        finally:
            Image.MAX_IMAGE_PIXELS = old
        if w * h > MAX_IMAGE_PIXELS:
            msg = (f"画像が大きすぎます（{w}×{h} = {w * h / 1e6:.0f} 百万画素。上限 {MAX_IMAGE_PIXELS / 1e6:.0f} 百万画素）"
                   f"{(': ' + str(rel)) if rel else ''} → 長辺 4000px 程度に縮小して置き直す（スライドは 1280×720px なので、それ以上は表示に効かない）")
    except Exception:       # noqa: BLE001  （Pillow なし・壊れた画像は、別の検査が言う）
        msg = None
    _IMAGE_SIZE_CACHE[key] = msg
    return msg


def region_props(region_defaults) -> set:
    props = set(COMMON_STYLE_PROPS) | set(EXTRA_STYLE_PROPS)
    if isinstance(region_defaults, dict):
        props |= set(region_defaults)
    return props


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_region_value(region: dict, defaults, where: str, check_unknown: bool = True) -> list:
    """style / layout_overrides の 1 領域（辞書）の中身を検査 → [(level, 本文)]。
    where は「style.body」のような場所の表記。defaults はその領域のレイアウト既定値（辞書。無ければ None）。
    未知のプロパティ名は warn、数値であるべき値が数値でない・負の値などは fail、極小の文字サイズは warn。"""
    out = []
    if not isinstance(region, dict):
        return [("fail", f"{where} はオブジェクト（{{ \"size\": 20, … }}）で指定してください（{_vtype(region)}が書かれています）"
                         f" → 領域ごと消したいときは書かずに、h や size で調整する")]
    defaults = defaults if isinstance(defaults, dict) else {}
    allowed = region_props(defaults)
    for k, v in region.items():
        if not isinstance(k, str) or k.startswith("_"):
            continue
        if k not in allowed and check_unknown:   # レイアウト JSON 自身の検査では新しいプロパティ名を定義として許す（値の型だけ見る）
            out.append(("warn", f"{where} の \"{k}\" は無視されます（この領域にそのプロパティはありません）"
                                f"{hint(k, allowed)}"))
            continue
        if v is None:
            continue
        if k in BOOL_TOKEN_PROPS or isinstance(defaults.get(k), bool):
            if not isinstance(v, bool):
                out.append(("fail", f"{where}.{k} は true / false で指定してください（{_vtype(v)} {v!r} が書かれています）"
                                    f" → \"{k}\": false のように引用符なしで書く"))
            continue
        numeric = k in NUMERIC_STYLE_PROPS or k in ("weight", "tracking") or k in TOKEN_RANGES or _is_num(defaults.get(k))
        if numeric:
            if not _is_num(v):
                out.append(("fail", f"{where}.{k} は数値で指定してください（{_vtype(v)} {v!r} が書かれています）"
                                    f" → \"{k}\": {TOKEN_EXAMPLES.get(k, '24')} のように引用符なしの数値にする"))
                continue
            if v != v or v in (float("inf"), float("-inf")):
                out.append(("fail", f"{where}.{k} は有限の数値で指定してください"))
                continue
            if k in INT_STYLE_PROPS and (v != int(v) or v < 1):
                out.append(("fail", f"{where}.{k} は 1 以上の整数で指定してください（{v}）"))
                continue
            if k in INT_TOKEN_PROPS and v != int(v):
                lo, hi = TOKEN_RANGES[k]
                out.append(("fail", f"{where}.{k} は整数（{lo:g}〜{hi:g}）で指定してください（{v:g}）"
                                    f" → \"{k}\": {TOKEN_EXAMPLES.get(k, '1')} のように小数でない値にする"))
                continue
            if (k in POSITIVE_STYLE_PROPS or k.endswith(POSITIVE_SUFFIXES)) and v <= 0:
                out.append(("fail", f"{where}.{k} は 0 より大きい数値で指定してください（{v}）"))
                continue
            if (k in NONNEG_STYLE_PROPS or k.endswith(NONNEG_SUFFIXES)) and v < 0:
                out.append(("fail", f"{where}.{k} は 0 以上で指定してください（{v}）"))
                continue
            if k in TOKEN_RANGES and not (TOKEN_RANGES[k][0] <= v <= TOKEN_RANGES[k][1]):
                lo, hi = TOKEN_RANGES[k]
                if k in WRAP_TOKEN_KEYS:
                    tip = " → 範囲内の値にする（文節の折り返しを止めたいときは wrap.enabled を false にする）"
                else:
                    tip = " → 範囲内の値にする（自動フィットの拡大を止めたいときは autofit: false か、その種類の文字の大きさを style に書く）"
                out.append(("fail", f"{where}.{k} は {lo:g}〜{hi:g} の範囲で指定してください（{v:g}）{tip}"))
                continue
            if k not in TOKEN_RANGES and k not in ("weight", "tracking"):
                if (k == "size" or k.endswith("_size")) and v > MAX_TEXT_SIZE:
                    out.append(("fail", f"{where}.{k} は {MAX_TEXT_SIZE:g}px 以下で指定してください（{v:g}）"
                                        f" → 文字サイズは 12〜100px 程度。大きく見せたいときは図や余白を使う"))
                    continue
                if k == "line_height" and v > MAX_LINE_HEIGHT:
                    out.append(("fail", f"{where}.{k} は {MAX_LINE_HEIGHT:g} 以下（文字サイズの倍率）で指定してください（{v:g}）"
                                        f" → 1.2〜2 程度にする"))
                    continue
                if k in INT_STYLE_PROPS and v > MAX_COLS:
                    out.append(("fail", f"{where}.{k} は {MAX_COLS} 以下の整数で指定してください（{v:g}）"))
                    continue
                if abs(v) > MAX_EXTENT and k not in ("size", "line_height") and not k.endswith("_size"):
                    out.append(("fail", f"{where}.{k} は絶対値 {MAX_EXTENT:g} 以下で指定してください（{v:g}）"
                                        f" → スライドは 1280×720px。位置・幅・高さ・間隔はその範囲の値にする"))
                    continue
            if k == "weight" and not (WEIGHT_RANGE[0] <= v <= WEIGHT_RANGE[1]):
                out.append(("fail", f"{where}.weight は 100〜900 の太さで指定してください（{v}。400 = 標準、700 = 太字）"))
                continue
            if k == "tracking" and not (TRACKING_RANGE[0] <= v <= TRACKING_RANGE[1]):
                out.append(("fail", f"{where}.tracking は -0.2〜0.6（em 単位の字間。0.05 = 文字の幅の 5% を足す）で指定してください（{v}）"))
                continue
            if k == "size" and v < MIN_PPTX_SIZE:
                out.append(("fail", f"{where}.size は {MIN_PPTX_SIZE}px 以上で指定してください（{v}。PowerPoint の文字は 1pt 未満にできません）"
                                    f" → 12px 以上にする"))
                continue
            if (k == "size" or k.endswith("_size")) and v < MIN_READABLE_SIZE and k in ("size", "cell_size", "item_size", "body_size", "heading_size", "text_size", "label_size", "header_size"):
                out.append(("warn", f"{where}.{k} が {v}px です。{MIN_READABLE_SIZE}px 未満は読めません"
                                    f" → 文字量を減らして 12px 以上にする"))
        elif k in ("color", "fill", "border_color") and not isinstance(v, (str, dict, list)):
            out.append(("fail", f"{where}.{k} はテーマトークン名か #RRGGBB で指定してください（{_vtype(v)}が書かれています）"))
        elif k == "grow_sizes":
            if not isinstance(v, list) or not all(_is_num(x) and x == x and 1 <= x <= TOKEN_RANGES["thin_max_size"][1] for x in v):
                out.append(("fail", f"{where}.{k} は文字サイズ（1〜200）の配列で指定してください（{_vtype(v)} {v!r} が書かれています）"
                                    f" → \"{k}\": [20, 18] のように大きい順に並べる（[] で本文を大きくしない）"))
        elif k == "series_colors" and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
            out.append(("fail", f"{where}.{k} は色の配列で指定してください（{_vtype(v)} {v!r} が書かれています）"
                                f" → \"{k}\": [\"primary\", \"accent\", \"#1F8A5B\"] のようにテーマトークン名か #RRGGBB を並べる"))
        elif k in ENUM_STYLE_PROPS and v not in ENUM_STYLE_PROPS[k]:
            out.append(("fail", f"{where}.{k} は {' / '.join(ENUM_STYLE_PROPS[k])} のいずれかで指定してください"
                                f"（{v!r} が書かれています）{hint(str(v), ENUM_STYLE_PROPS[k])}"
                                f" → 例: \"{k}\": \"{ENUM_STYLE_PROPS[k][0]}\""))
        elif k in ("bold", "italic") and not isinstance(v, bool):
            out.append(("fail", f"{where}.{k} は true / false で指定してください（{_vtype(v)}が書かれています）"))
    return out


# ---------------------------------------------------------------------------
# テーマ JSON の検証
# ---------------------------------------------------------------------------

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def normalize_hex(c: str) -> str:
    """#RGB → #RRGGBB（6 桁はそのまま）。"""
    if isinstance(c, str) and re.match(r"^#[0-9A-Fa-f]{3}$", c):
        return "#" + "".join(ch * 2 for ch in c[1:])
    return c


# フォント名に使えない文字（HTML の <style> / style 属性にそのまま出るため、引用符・タグ・CSS の区切りと制御文字は禁止）
FONT_NAME_BAD_RE = re.compile(r'["\\<>;{}\x00-\x1f\x7f]')


def validate_theme_data(data, name: str, known_color_keys=()) -> list:
    """読み込んだテーマ JSON 1 ファイルの検査 → [(level, 本文)]。name はテーマ名（メッセージ用）。
    fail: 最上位がオブジェクトでない / colors が hex でない / fonts が文字列か文字列の配列でない。
    warn: 未知のトップキー、標準トークン名に似た色名（打ち間違いの疑い）。"""
    pre = f"テーマ '{name}'"
    if not isinstance(data, dict):
        return [("fail", f"{pre}: JSON の最上位はオブジェクト（{{ \"name\": …, \"colors\": {{…}} }}）にしてください"
                         f"（{_vtype(data)}が書かれています）")]
    out = []
    for key in data:
        if isinstance(key, str) and (key.startswith("_") or key in THEME_TOP_KEYS):
            continue
        out.append(("warn", f"{pre}: 未知のトップキー \"{key}\" は無視されます{hint(key, THEME_TOP_KEYS)}"
                            f" → 使えるキー: {' / '.join(sorted(THEME_TOP_KEYS))}"))
    for key in ("name", "label", "description", "extends", "alias_of"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            out.append(("fail", f"{pre}: {key} は文字列で指定してください（{_vtype(data[key])}が書かれています）"))
    colors = data.get("colors")
    if colors is not None:
        if not isinstance(colors, dict):
            out.append(("fail", f"{pre}: colors はオブジェクト（{{ \"primary\": \"#0F3D6E\", … }}）で指定してください"
                                f"（{_vtype(colors)}が書かれています）"))
        else:
            for k, v in colors.items():
                if not isinstance(v, str) or not HEX_RE.match(v):
                    out.append(("fail", f"{pre}: colors.{k} は #RRGGBB（または #RGB）で指定してください（{v!r}）"
                                        f" → 色名や他トークンの参照は使えません。例: \"{k}\": \"#0F3D6E\""))
                elif known_color_keys and k not in known_color_keys:
                    m = difflib.get_close_matches(k, list(known_color_keys), n=1, cutoff=0.75)
                    if m:
                        out.append(("warn", f"{pre}: colors.\"{k}\" は標準の色トークンではありません"
                                            f"（もしかして \"{m[0]}\"）。打ち間違いなら無視されます"))
    fonts = data.get("fonts")
    if fonts is not None:
        if not isinstance(fonts, dict):
            out.append(("fail", f"{pre}: fonts はオブジェクト（{{ \"heading\": \"Meiryo\", \"body\": …, \"code\": … }}）で"
                                f"指定してください（{_vtype(fonts)}が書かれています）"))
        else:
            for k, v in fonts.items():
                ok = (isinstance(v, str) and v.strip()) or \
                     (isinstance(v, list) and v and all(isinstance(x, str) and x.strip() for x in v))
                names = [v] if isinstance(v, str) else (v if isinstance(v, list) else [])
                bad = [x for x in names if isinstance(x, str) and FONT_NAME_BAD_RE.search(x)]
                if ok and bad:
                    out.append(("fail", f"{pre}: fonts.{k} のフォント名に使えない文字があります（{bad[0]!r}）"
                                        f" → フォント名は \" \\ < > ; {{ }} と制御文字を含めずに書く（例: \"Meiryo\"）。"
                                        f"CSS に出力されるため、これらは受け付けません"))
                elif not ok:
                    out.append(("fail", f"{pre}: fonts.{k} は空でない文字列か、文字列の配列で指定してください（{v!r}）"
                                        f" → 例: \"{k}\": [\"Meiryo\", \"Hiragino Sans\"]"))
                elif k not in THEME_FONT_KEYS:
                    out.append(("warn", f"{pre}: fonts.\"{k}\" は使われません{hint(k, THEME_FONT_KEYS)}"
                                        f" → 使えるのは heading / body / code"))
    for key in ("layout", "tokens"):
        if key in data and data[key] is not None and not isinstance(data[key], dict):
            out.append(("fail", f"{pre}: {key} はオブジェクトで指定してください（{_vtype(data[key])}が書かれています）"))
    if "shape" in data and data["shape"] is not None and not isinstance(data["shape"], str):
        out.append(("fail", f"{pre}: shape は shape の名前（文字列。例: \"sharp\"）で指定してください（{_vtype(data['shape'])}が書かれています）"))
    return out

"""canvas 型スライドの描画エンジン（HTML / PPTX）。

canvas は 1280x720 の座標系に図形・文字・表・ベクターアイコンを座標指定で置くスライドタイプ。
既存 PPTX の見た目を崩さず取り込む用途（tools/pptx_import.py が生成する）を主目的とする。
要素スキーマは references/schema/canvas.mdを参照。単位はすべて px（文字サイズも px）。
"""
from __future__ import annotations

import html as _html
import math
import re

EMU_PER_PX = 9525

GEOMS = {
    "rect", "roundRect", "ellipse", "triangle", "diamond", "homePlate", "chevron", "flowChartDecision",
    "flowChartMerge", "flowChartDocument", "can", "flowChartMagneticDisk", "borderCallout1",
    "borderCallout2", "line", "straightConnector1", "bentConnector2", "bentConnector3",
    "bentConnector4", "bentConnector5", "custom",
}
LINE_GEOMS = {"line", "straightConnector1", "bentConnector2", "bentConnector3", "bentConnector4", "bentConnector5"}
KINDS = {"shape", "table", "svg", "backdrop", "placeholder", "group", "image"}
# kind: "image" で読み込める画像の拡張子（build_deck.ALLOWED_IMAGE_EXT と同じ）
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".tiff"}
IMAGE_FITS = ("cover", "contain")

DASH = {"dash": (4, 3), "sysDash": (3, 1), "sysDot": (1, 1), "dot": (1, 3), "dashDot": (4, 3, 1, 3),
        "lgDash": (8, 3), "lgDashDot": (8, 3, 1, 3), "lgDashDotDot": (8, 3, 1, 3, 1, 3),
        "sysDashDot": (3, 1, 1, 1), "sysDashDotDot": (3, 1, 1, 1, 1, 1)}
ARROW_SZ = {"sm": 2.0, "med": 3.0, "lg": 5.0}
# PowerPoint の行間 100% に相当する line-height 倍率
LINE_HEIGHT = 1.2


# XML 1.0 で使えない文字（制御文字・孤立サロゲート・U+FFFE/FFFF）。PDF からの貼り付け等で混じると PPTX の XML が不正になる
_XML_BAD_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def clean_text(s):
    """XML 1.0 で使えない文字を取り除く（文字列以外はそのまま返す）。
    HTML・PPTX どちらに出す文字も、描画の前にこれを通す"""
    return _XML_BAD_RE.sub("", s) if isinstance(s, str) else s


def esc(s) -> str:
    return _html.escape(clean_text(str(s)), quote=True)


# ---------------------------------------------------------------- sanitize
# canvas の要素値は HTML の属性・CSS と PPTX の XML 属性へそのまま埋め込まれるため、描画の前に
# 必ず sanitize_elements() を通す（取り込み元の PPTX や手書きの deck.json は信用しない）。
# validate_canvas() も同じ関数で置き換えが起きた箇所を集めてエラーにする。
_HEX6_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_HEX3_RE = re.compile(r"^#[0-9A-Fa-f]{3}$")
_WORD_RE = re.compile(r"^[A-Za-z0-9_]{1,40}$")
_FONT_BAD_RE = re.compile(r"[\"'<>&;{}\\\x00-\x1f]")
ENUMS = {
    "anchor": {"t", "ctr", "b"},
    "align": {"l", "ctr", "r", "just", "dist"},
    "cap": {"rnd", "sq", "flat"},
    "merged": {"h", "v"},
}
ARROW_TYPES = {"triangle", "stealth", "arrow", "oval", "diamond", "none"}
PATH_OPS = {"M", "L", "C", "Q", "Z"}
COLOR_KEYS = {"color", "highlight", "fg", "bg", "fill"}
_DROP = object()  # 不正な列挙値はキーごと落として既定値に任せる
_STR_ENUM_KEYS = set(ENUMS) | {"dash", "pattern", "geom"}


def _num(v, default=0.0):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else default


def _sanitize(v, key, path, issues):
    """要素ツリーを再帰的に複製しながら危険な値を安全な値へ置き換える。置き換えたら issues に記録"""
    def bad(msg, repl):
        issues.append(f"{path}: {msg}")
        return repl

    if isinstance(v, str):
        v = clean_text(v)  # XML に使えない文字（\x0c 等）は黙って落とす（PPTX 生成が例外で止まらないように）
    # 値の型の検査（描画段の AttributeError / TypeError を前もって潰す。置き換えが起きたら issues に残り、validate_canvas が fail にする）
    if key in COLOR_KEYS and v is not None and not isinstance(v, (str, dict)) and not (key == "fill" and isinstance(v, bool)):
        return bad(f"{key} {_show(v)} は色の文字列（#RRGGBB）で指定してください", "#000000")
    if key in _STR_ENUM_KEYS and v is not None and not isinstance(v, str):
        return bad(f"{key} {_show(v)} は文字列で指定してください", _DROP)
    if key in ("head", "tail") and v and not isinstance(v, dict):
        return bad(f"{key} {_show(v)} は {{\"type\": \"triangle\"}} のようなオブジェクトで指定してください", _DROP)
    if key in ("adj", "borders") and v is not None and not isinstance(v, dict):
        return bad(f"{key} {_show(v)} はオブジェクトで指定してください", _DROP)
    if key == "cmds" and not isinstance(v, list):
        return bad(f"cmds {_show(v)} はパス命令の配列で指定してください（例: [[\"M\", 0, 0], [\"L\", 10, 10]]）", [])
    if key == "font" and v is None:
        return _DROP
    if key == "font" and not isinstance(v, (str, list)):
        return bad(f"font {_show(v)} はフォント名の文字列か、文字列の配列で指定してください", _DROP)
    if key in COLOR_KEYS and isinstance(v, dict) and "color" in v and not isinstance(v["color"], str):
        return bad(f"{key}.color {_show(v['color'])} は色の文字列（#RRGGBB）で指定してください", "#000000")
    if key in ("span", "rowspan"):
        n = _num(v, None)
        return max(int(n), 1) if n is not None else bad(f"{key} '{v}' は整数で指定してください", 1)
    if key == "alpha":
        return min(max(_num(v, 1.0), 0.0), 1.0)
    if isinstance(v, dict):
        if key in ("head", "tail"):
            out = {}
            t = v.get("type", "triangle")
            out["type"] = t if t in ARROW_TYPES else bad(f"矢じり type '{t}' は未対応です", "triangle")
            for k in ("w", "len"):
                s = v.get(k, "med")
                out[k] = s if s in ARROW_SZ else bad(f"矢じり {k} '{s}' は sm/med/lg のいずれかです", "med")
            return out
        if key == "adj":
            return {k: _num(x) for k, x in v.items() if isinstance(k, str) and _WORD_RE.match(k)}
        if key == "borders":
            out = {}
            for side, b in v.items():
                if b is not None and not isinstance(b, dict):
                    bad(f"borders.{side} {_show(b)} は線のオブジェクト（{{\"color\": \"#333333\", \"width\": 1}}）か null で指定してください", None)
                else:
                    out[side] = _sanitize(b, side, f"{path}.{side}", issues)
            return out
        out = {k: _sanitize(x, k, f"{path}.{k}", issues) for k, x in v.items()}
        return {k: x for k, x in out.items() if x is not _DROP}
    if isinstance(v, list):
        if key == "font":
            out = []
            for x in v:
                s = str(x)
                if _FONT_BAD_RE.search(s):
                    s = bad(f"フォント名 '{s}' に使えない文字が含まれています", _FONT_BAD_RE.sub("", s))
                out.append(s)
            return out
        if key == "cmds":
            out = []
            for c in v:
                if not (isinstance(c, list) and c and isinstance(c[0], str) and c[0] in PATH_OPS):
                    bad(f"パス命令 {c!r} は M/L/C/Q/Z のいずれかで始めてください", None)
                    continue
                out.append([c[0]] + [_num(x) for x in c[1:]])
            return out
        if key == "stops":
            return [[_num(s[0]), _sanitize(s[1], "color", f"{path}[{i}]", issues)]
                    for i, s in enumerate(v) if isinstance(s, (list, tuple)) and len(s) == 2]
        if key == "colors":
            return [_sanitize(c, "color", f"{path}[{i}]", issues) for i, c in enumerate(v)]
        return [_sanitize(x, key, f"{path}[{i}]", issues) for i, x in enumerate(v)]
    if isinstance(v, str):
        if key == "font":  # 手書きで "font": "Arial" と文字列にしても落ちないよう、1 要素の配列として扱う
            return _sanitize([v], key, path, issues)
        if key in COLOR_KEYS:
            if _HEX6_RE.match(v):
                return v
            if _HEX3_RE.match(v):  # #RGB は #RRGGBB に展開して受け付ける
                return "#" + "".join(c * 2 for c in v[1:]).upper()
            return bad(f"色 '{v}' は #RRGGBB（または #RGB）で指定してください", "#000000")
        if key in ENUMS and v not in ENUMS[key]:
            return bad(f"{key} '{v}' は {'/'.join(sorted(ENUMS[key]))} のいずれかです", _DROP)
        if key == "dash" and v not in DASH and v != "solid":
            return bad(f"dash '{v}' は未対応です", _DROP)
        if key == "pattern" and not _WORD_RE.match(v):
            return bad(f"pattern '{v}' は英数字のプリセット名で指定してください", "pct50")
        if key == "svg":
            clean = sanitize_svg(v)
            return clean if clean else bad("svg を解析できないか、許可されない内容です", "")
        return v
    return v


def sanitize_elements(elements, path="elements", issues=None):
    """canvas 要素列の安全な複製を返す（描画前に必ず通す）"""
    return _sanitize(elements if isinstance(elements, list) else [], "elements", path,
                     issues if issues is not None else [])


# SVG はベクターアイコン用途に限るため、要素・属性とも許可リスト方式で残す
_SVG_NS = "http://www.w3.org/2000/svg"
_SVG_TAGS = {
    "svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan",
    "defs", "linearGradient", "radialGradient", "stop", "clipPath", "mask", "use", "symbol", "title",
    "desc", "pattern", "marker", "filter", "feGaussianBlur", "feOffset", "feBlend", "feFlood",
    "feComposite", "feColorMatrix", "feMerge", "feMergeNode",
}
_SVG_ATTRS = {
    "id", "class", "viewBox", "width", "height", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r",
    "rx", "ry", "fx", "fy", "d", "points", "transform", "fill", "fill-opacity", "fill-rule", "stroke",
    "stroke-width", "stroke-opacity", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
    "stroke-dashoffset", "stroke-miterlimit", "opacity", "clip-path", "clip-rule", "mask", "offset",
    "stop-color", "stop-opacity", "gradientUnits", "gradientTransform", "spreadMethod",
    "patternUnits", "patternContentUnits", "patternTransform", "clipPathUnits", "maskUnits",
    "maskContentUnits", "preserveAspectRatio", "font-family", "font-size", "font-weight",
    "font-style", "text-anchor", "dominant-baseline", "letter-spacing", "dx", "dy", "style",
    "visibility", "display", "markerWidth", "markerHeight", "refX", "refY", "orient", "markerUnits",
    "stdDeviation", "in", "in2", "result", "mode", "operator", "k1", "k2", "k3", "k4", "values",
    "type", "flood-color", "flood-opacity", "filterUnits", "primitiveUnits", "href", "version",
}
_SVG_BAD_STYLE_RE = re.compile(r"url\(\s*['\"]?\s*[^#'\"\s)]|javascript:|expression\s*\(|@import|behavior\s*:|[<>]", re.I)


def sanitize_svg(src) -> str:
    """インライン SVG を許可リストで浄化して返す。解析できない・DOCTYPE を含む場合は空文字"""
    import xml.etree.ElementTree as ET
    if not isinstance(src, str) or len(src) > 2_000_000 or re.search(r"<!(DOCTYPE|ENTITY)", src, re.I):
        return ""
    try:
        root = ET.fromstring(src)
    except ET.ParseError:
        return ""

    def local(name):
        return name.rsplit("}", 1)[-1]

    def clean(el):
        for child in list(el):
            if not isinstance(child.tag, str) or local(child.tag) not in _SVG_TAGS:
                el.remove(child)
            else:
                clean(child)
        for name in list(el.attrib):
            ln, val = local(name), el.attrib[name]
            ok = ln in _SVG_ATTRS
            if ok and ln == "href":
                ok = val.strip().startswith("#")
            elif ok and ln == "style":
                ok = not _SVG_BAD_STYLE_RE.search(val)
            elif ok and "url(" in val:
                ok = not _SVG_BAD_STYLE_RE.search(val)
            if not ok:
                del el.attrib[name]
            elif ln == "href" and name != "href":
                # xlink:href は SVG2 の href に寄せる（名前空間接頭辞なしで HTML へ直挿しできるように）
                del el.attrib[name]
                el.set("href", val)

    if local(root.tag) != "svg":
        return ""
    clean(root)
    for el in root.iter():
        if isinstance(el.tag, str):
            el.tag = local(el.tag)
    root.set("xmlns", _SVG_NS)
    return ET.tostring(root, encoding="unicode")


def f2(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def css_color(c) -> str:
    """'#RRGGBB' / {'color':'#RRGGBB','alpha':0.5} / None → CSS色"""
    if c is None:
        return "transparent"
    if isinstance(c, str):
        return c
    hx, a = c.get("color", "#000000"), c.get("alpha", 1.0)
    if a >= 0.999:
        return hx
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{a:.3f})"


# ---------------------------------------------------------------- geometry
def _poly(pts, close=True):
    d = "M" + " L".join(f"{f2(x)},{f2(y)}" for x, y in pts)
    return d + (" Z" if close else "")


def cmds_to_d(cmds) -> str:
    out = []
    for c in cmds:
        op = c[0]
        if op == "Z":
            out.append("Z")
        else:
            out.append(op + " ".join(f"{f2(c[i])},{f2(c[i + 1])}" for i in range(1, len(c), 2)))
    return " ".join(out)


def geometry(el):
    """戻り値: (paths[(d, filled, stroked)], 線の点列 or None)"""
    g = el.get("geom", "rect")
    w, h = el["w"], el["h"]
    adj = el.get("adj", {})
    ss = min(w, h)

    def a(name, default):
        return adj.get(name, default)

    rect = [(_poly([(0, 0), (w, 0), (w, h), (0, h)]), True, True)]
    if g == "rect":
        return rect, None
    if g == "custom":
        return [(cmds_to_d(p["cmds"]), p.get("fill", True), p.get("stroke", True)) for p in el.get("path", [])], None
    if g == "roundRect":
        r = ss * min(max(a("adj", 16667), 0), 50000) / 100000
        d = (f"M{f2(r)},0 L{f2(w - r)},0 A{f2(r)},{f2(r)} 0 0 1 {f2(w)},{f2(r)} L{f2(w)},{f2(h - r)} "
             f"A{f2(r)},{f2(r)} 0 0 1 {f2(w - r)},{f2(h)} L{f2(r)},{f2(h)} A{f2(r)},{f2(r)} 0 0 1 0,{f2(h - r)} "
             f"L0,{f2(r)} A{f2(r)},{f2(r)} 0 0 1 {f2(r)},0 Z")
        return [(d, True, True)], None
    if g == "ellipse":
        d = (f"M0,{f2(h / 2)} A{f2(w / 2)},{f2(h / 2)} 0 1 1 {f2(w)},{f2(h / 2)} "
             f"A{f2(w / 2)},{f2(h / 2)} 0 1 1 0,{f2(h / 2)} Z")
        return [(d, True, True)], None
    if g == "triangle":
        return [(_poly([(0, h), (w * a("adj", 50000) / 100000, 0), (w, h)]), True, True)], None
    if g == "homePlate":
        v = min(max(a("adj", 50000), 0), 100000 * w / ss if ss else 0)
        x1 = w - ss * v / 100000
        return [(_poly([(0, 0), (x1, 0), (w, h / 2), (x1, h), (0, h)]), True, True)], None
    if g == "chevron":
        v = min(max(a("adj", 50000), 0), 100000 * w / ss if ss else 0)
        x1 = ss * v / 100000
        return [(_poly([(0, 0), (w - x1, 0), (w, h / 2), (w - x1, h), (0, h), (x1, h / 2)]), True, True)], None
    if g in ("flowChartDecision", "diamond"):
        return [(_poly([(0, h / 2), (w / 2, 0), (w, h / 2), (w / 2, h)]), True, True)], None
    if g == "flowChartMerge":
        return [(_poly([(0, 0), (w, 0), (w / 2, h)]), True, True)], None
    if g == "flowChartDocument":
        sx, sy = w / 21600, h / 21600
        d = (f"M0,0 L{f2(w)},0 L{f2(w)},{f2(17322 * sy)} "
             f"C{f2(10800 * sx)},{f2(17322 * sy)} {f2(10800 * sx)},{f2(23922 * sy)} 0,{f2(20172 * sy)} Z")
        return [(d, True, True)], None
    if g in ("can", "flowChartMagneticDisk"):
        ry = ss * a("adj", 25000) / 200000 if g == "can" else h / 6
        rx = w / 2
        body = (f"M0,{f2(ry)} L0,{f2(h - ry)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(w)},{f2(h - ry)} "
                f"L{f2(w)},{f2(ry)} A{f2(rx)},{f2(ry)} 0 0 0 0,{f2(ry)} Z")
        top = f"M0,{f2(ry)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(w)},{f2(ry)}"
        return [(body, True, True), (top, False, True)], None
    if g == "borderCallout1":
        pts = [(w * a("adj2", -8333) / 1e5, h * a("adj1", 18750) / 1e5),
               (w * a("adj4", -38333) / 1e5, h * a("adj3", 112500) / 1e5)]
        return rect + [(_poly(pts, False), False, True)], None
    if g == "borderCallout2":
        pts = [(w * a("adj2", -8333) / 1e5, h * a("adj1", 18750) / 1e5),
               (w * a("adj4", -16667) / 1e5, h * a("adj3", 18750) / 1e5),
               (w * a("adj6", -46667) / 1e5, h * a("adj5", 112500) / 1e5)]
        return rect + [(_poly(pts, False), False, True)], None
    if g in ("line", "straightConnector1"):
        return [], [(0, 0), (w, h)]
    if g == "bentConnector2":
        return [], [(0, 0), (w, 0), (w, h)]
    if g == "bentConnector3":
        x1 = w * a("adj1", 50000) / 1e5
        return [], [(0, 0), (x1, 0), (x1, h), (w, h)]
    if g == "bentConnector4":
        x1, y2 = w * a("adj1", 50000) / 1e5, h * a("adj2", 50000) / 1e5
        return [], [(0, 0), (x1, 0), (x1, y2), (w, y2), (w, h)]
    if g == "bentConnector5":
        x1, y2, x3 = w * a("adj1", 50000) / 1e5, h * a("adj2", 50000) / 1e5, w * a("adj3", 50000) / 1e5
        return [], [(0, 0), (x1, 0), (x1, y2), (x3, y2), (x3, h), (w, h)]
    return rect, None


def text_rect(el):
    """図形ごとの文字領域（presetShapeDefinitions の <a:rect>）。戻り値 (l, t, r, b)"""
    g = el.get("geom", "rect")
    w, h = el["w"], el["h"]
    ss = min(w, h)
    adj = el.get("adj", {})
    if g == "ellipse":
        dx, dy = w / 2 * (1 - math.cos(math.radians(45))), h / 2 * (1 - math.sin(math.radians(45)))
        return dx, dy, w - dx, h - dy
    if g in ("flowChartDecision", "diamond"):
        return w / 4, h / 4, w * 3 / 4, h * 3 / 4
    if g == "flowChartMerge":
        return w / 4, 0, w * 3 / 4, h / 2
    if g == "flowChartDocument":
        return 0, 0, w, h * 17322 / 21600
    if g == "homePlate":
        v = min(max(adj.get("adj", 50000), 0), 100000 * w / ss if ss else 0)
        x1 = w - ss * v / 100000
        return 0, 0, (x1 + w) / 2, h
    if g == "chevron":
        v = min(max(adj.get("adj", 50000), 0), 100000 * w / ss if ss else 0)
        x1 = ss * v / 100000
        return (x1, 0, w - x1, h) if w - x1 > x1 else (0, 0, w, h)
    if g == "triangle":
        x1 = w * adj.get("adj", 50000) / 200000
        return x1, h / 2, x1 + w / 2, h
    if g == "roundRect":
        r = ss * min(max(adj.get("adj", 16667), 0), 50000) / 100000
        il = r * 0.29289
        return il, il, w - il, h - il
    if g == "can":
        y1 = ss * adj.get("adj", 25000) / 200000
        return 0, y1 * 2, w, h - y1
    if g == "flowChartMagneticDisk":
        return 0, h / 3, w, h * 5 / 6
    return 0, 0, w, h


# ---------------------------------------------------------------- html: shape
class _Uid:
    n = 0

    @classmethod
    def next(cls, prefix="c"):
        cls.n += 1
        return f"{prefix}{cls.n}"


def _fill_svg(fill, uid):
    if fill is None:
        return "none", ""
    if isinstance(fill, str) or "color" in fill:
        return css_color(fill), ""
    if "gradient" in fill:
        gr = fill["gradient"]
        rad = math.radians(gr.get("angle", 90))
        x1, y1 = 0.5 - 0.5 * math.cos(rad), 0.5 - 0.5 * math.sin(rad)
        x2, y2 = 0.5 + 0.5 * math.cos(rad), 0.5 + 0.5 * math.sin(rad)
        st = "".join(f'<stop offset="{f2(p)}%" stop-color="{css_color(c)}"/>' for p, c in gr["stops"])
        return (f"url(#{uid})",
                f'<linearGradient id="{uid}" x1="{f2(x1)}" y1="{f2(y1)}" x2="{f2(x2)}" y2="{f2(y2)}">{st}</linearGradient>')
    if "pattern" in fill:
        prst, fg, bg = fill["pattern"], css_color(fill.get("fg", "#000000")), css_color(fill.get("bg", "#FFFFFF"))
        if "DnDiag" in prst or prst == "dnDiag":
            sw = {"ltDnDiag": 1, "dnDiag": 1.5, "dkDnDiag": 2, "wdDnDiag": 3}.get(prst, 1)
            body = f'<path d="M-1,-1 L5,5 M3,-1 L5,1 M-1,3 L1,5" stroke="{fg}" stroke-width="{sw}"/>'
        elif "UpDiag" in prst or prst == "upDiag":
            sw = {"ltUpDiag": 1, "upDiag": 1.5, "dkUpDiag": 2, "wdUpDiag": 3}.get(prst, 1)
            body = f'<path d="M-1,5 L5,-1 M-1,1 L1,-1 M3,5 L5,3" stroke="{fg}" stroke-width="{sw}"/>'
        else:
            body = f'<rect width="1" height="1" fill="{fg}"/>'
        return (f"url(#{uid})", f'<pattern id="{uid}" width="4" height="4" patternUnits="userSpaceOnUse">'
                                 f'<rect width="4" height="4" fill="{bg}"/>{body}</pattern>')
    return "none", ""


def _arrow(end, pts, line, at_start):
    if len(pts) < 2:
        return "", 0
    seq = list(reversed(pts)) if at_start else pts
    tip = seq[-1]
    prev = next((q for q in reversed(seq[:-1]) if abs(q[0] - tip[0]) > 0.01 or abs(q[1] - tip[1]) > 0.01), None)
    if prev is None:
        return "", 0
    ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
    lw = line.get("width", 0.75)
    base = max(lw, 2.4)  # 細線でも PowerPoint の矢じりは一定以上の大きさで描かれる
    aw, al = base * ARROW_SZ.get(end.get("w", "med"), 3), base * ARROW_SZ.get(end.get("len", "med"), 3)
    c, s = math.cos(ang), math.sin(ang)

    def tr(dx, dy):
        return (tip[0] + dx * c - dy * s, tip[1] + dx * s + dy * c)
    col = css_color(line.get("color"))
    typ = end.get("type", "triangle")
    if typ in ("triangle", "stealth"):
        p = [tr(0, 0), tr(-al, aw / 2), tr(-al * (0.6 if typ == "stealth" else 1), 0), tr(-al, -aw / 2)]
        return f'<path d="{_poly(p)}" fill="{col}"/>', al * 0.9
    if typ == "arrow":
        p = [tr(-al, aw / 2), tr(0, 0), tr(-al, -aw / 2)]
        return f'<path d="{_poly(p, False)}" fill="none" stroke="{col}" stroke-width="{f2(max(lw, 0.75))}"/>', 0
    if typ == "oval":
        cx, cy = tr(-al / 2, 0)
        return f'<ellipse cx="{f2(cx)}" cy="{f2(cy)}" rx="{f2(al / 2)}" ry="{f2(aw / 2)}" fill="{col}"/>', al / 2
    if typ == "diamond":
        p = [tr(0, 0), tr(-al / 2, aw / 2), tr(-al, 0), tr(-al / 2, -aw / 2)]
        return f'<path d="{_poly(p)}" fill="{col}"/>', al / 2
    return "", 0


def _shorten(pts, d, at_start):
    if d <= 0 or len(pts) < 2:
        return pts
    pts = list(pts)
    i, j = (0, 1) if at_start else (-1, -2)
    a, b = pts[i], pts[j]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 0.01:
        return pts
    k = min(d, L * 0.9) / L
    pts[i] = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    return pts


def _shape_svg(el):
    w, h = el["w"], el["h"]
    paths, line_pts = geometry(el)
    fill = el.get("fill") if line_pts is None else None
    line = el.get("line")
    if fill is None and not line:
        return ""
    uid = _Uid.next("p")
    fill_val, defs = _fill_svg(fill, uid)
    stroke = css_color(line.get("color")) if line else "none"
    sw = max(line.get("width", 0.75), 0.75) if line else 0
    dash = ""
    if line and line.get("dash") in DASH:
        dash = f' stroke-dasharray="{" ".join(f2(v * max(sw, 1)) for v in DASH[line["dash"]])}"'
    cap = {"rnd": "round", "sq": "square"}.get((line or {}).get("cap", ""), "butt")
    pad = 12 + sw * 6
    body, extra = [], []
    if line_pts is not None:
        if not line:
            return ""
        pts = line_pts
        if line.get("tail"):
            a, d = _arrow(line["tail"], pts, line, False); extra.append(a); pts = _shorten(pts, d, False)
        if line.get("head"):
            a, d = _arrow(line["head"], pts, line, True); extra.append(a); pts = _shorten(pts, d, True)
        body.append(f'<path d="{_poly(pts, False)}" fill="none" stroke="{stroke}" stroke-width="{f2(sw)}"{dash} '
                    f'stroke-linecap="{cap}"/>')
    else:
        for d, filled, stroked in paths:
            body.append(f'<path d="{d}" fill="{fill_val if filled else "none"}" stroke="{stroke if stroked else "none"}" '
                        f'stroke-width="{f2(sw)}"{dash} stroke-linecap="{cap}"/>')
    fh, fv = el.get("flipH"), el.get("flipV")
    g_open = (f'<g transform="translate({f2(w if fh else 0)},{f2(h if fv else 0)}) scale({-1 if fh else 1},{-1 if fv else 1})">'
              if fh or fv else "<g>")
    filt = ""
    sh = el.get("shadow")
    if sh:
        filt = f' style="left:{f2(-pad)}px;top:{f2(-pad)}px;filter:drop-shadow({f2(sh.get("dx", 0))}px {f2(sh.get("dy", 0))}px {f2(sh.get("blur", 0))}px {css_color(sh.get("color", "#000000"))})"'
    else:
        filt = f' style="left:{f2(-pad)}px;top:{f2(-pad)}px"'
    return (f'<svg class="cv-sh" width="{f2(w + 2 * pad)}" height="{f2(h + 2 * pad)}" '
            f'viewBox="{f2(-pad)} {f2(-pad)} {f2(w + 2 * pad)} {f2(h + 2 * pad)}"{filt} aria-hidden="true">'
            f'{"<defs>" + defs + "</defs>" if defs else ""}{g_open}{"".join(body)}{"".join(extra)}</g></svg>')


# ---------------------------------------------------------------- html: text
def _run_css(r):
    fam = []
    for x in r.get("font", []) + ["Meiryo UI"]:
        if x and x not in fam:
            fam.append(x)
    size = r.get("size", 24)
    css = [f"font-size:{f2(size)}px", "font-family:" + ",".join(f"'{x}'" for x in fam),
           f"color:{css_color(r.get('color', '#000000'))}"]
    if _isnum(r.get("weight")):
        if r["weight"] != 400 or r.get("bold"):
            css.append(f"font-weight:{int(r['weight'])}")    # weight（形トークン）。600 以上は PPTX では太字
    elif r.get("bold"):
        css.append("font-weight:700")
    if _isnum(r.get("tracking")) and r["tracking"]:
        css.append(f"letter-spacing:{r['tracking']:g}em")
    if r.get("italic"):
        css.append("font-style:italic")
    deco = [d for d, k in (("underline", "underline"), ("line-through", "strike")) if r.get(k)]
    if deco:
        css.append("text-decoration:" + " ".join(deco))
    if r.get("baseline"):
        css.append(f"vertical-align:{r['baseline']:.0f}%;font-size:{f2(size * 0.66)}px")
    if r.get("highlight"):
        css.append(f"background:{css_color(r['highlight'])}")
    return ";".join(css)


def _split_lines(p):
    """改行（br）で区切った行ごとに文字サイズが違う段落は、行ごとの段落に分ける。
    PowerPoint は行ごとに最大文字サイズで行の高さを決めるが、CSS の p は段落全体の最大サイズで決まるため"""
    lines, cur = [], []
    for r in p.get("runs", []):
        if r.get("br"):
            lines.append((cur, r.get("size")))
            cur = []
        else:
            cur.append(r)
    lines.append((cur, None))
    sizes = {max([r.get("size", 24) for r in ln] or [bs or p.get("size") or 24]) for ln, bs in lines}
    if len(lines) < 2 or len(sizes) < 2:
        return [p]
    out = []
    for k, (runs, br_size) in enumerate(lines):
        q = {key: v for key, v in p.items() if key not in ("runs", "spaceBefore", "spaceAfter", "bullet", "indent", "size")}
        q["runs"] = runs
        if not runs:
            q["size"] = br_size or p.get("size") or 24
        if k == 0:
            for key in ("spaceBefore", "bullet", "indent"):
                if key in p:
                    q[key] = p[key]
        if k == len(lines) - 1 and "spaceAfter" in p:
            q["spaceAfter"] = p["spaceAfter"]
        out.append(q)
    return out


def paragraphs_html(paras):
    out = []
    for p in [q for p0 in paras for q in _split_lines(p0)]:
        runs = p.get("runs", [])
        size = p.get("size") or max([r.get("size", 24) for r in runs if not r.get("br")] or [24])
        if p.get("lineHeightPx"):
            lh_css = f"{f2(p['lineHeightPx'])}px"
        else:
            lh_css = f2(p.get("lineHeight", 1.0) * LINE_HEIGHT)
        # 行の高さは p（最大ランの文字サイズ×行間）だけで決め、span は line-height:0 にする（CANVAS_CSS）。
        # フォントの異なる span（箇条書きの Arial と本文の Meiryo UI 等）が混ざると、ブラウザが行ボックスを押し広げるため
        fam = next((r.get("font") for r in runs if r.get("font")), None) or ["Meiryo UI"]
        css = [f"text-align:{ {'l': 'left', 'ctr': 'center', 'r': 'right', 'just': 'justify', 'dist': 'justify'}.get(p.get('align', 'l'), 'left') }",
               f"font-size:{f2(size)}px", "font-family:" + ",".join(f"'{x}'" for x in fam + ["Meiryo UI"]),
               f"line-height:{lh_css}",
               f"margin:{f2(p.get('spaceBefore', 0))}px 0 {f2(p.get('spaceAfter', 0))}px 0",
               f"padding-left:{f2(p.get('marL', 0))}px", f"text-indent:{f2(p.get('indent', 0))}px"]
        inner = []
        bu = p.get("bullet")
        if bu and any((r.get("text") or "").strip() for r in runs):
            bcss = _run_css({"size": bu.get("size", size), "color": bu.get("color", runs[0].get("color") if runs else "#000000"),
                             "font": bu.get("font", runs[0].get("font", []) if runs else []),
                             "bold": runs[0].get("bold") if runs else False})
            inner.append(f'<span class="cv-bu" style="{bcss};width:{f2(max(-p.get("indent", 0), 0))}px">{esc(bu.get("char", "•"))}</span>')
        for r in runs:
            if r.get("br"):
                inner.append('<br data-soft="1">' if r.get("soft") else "<br>")
            else:
                inner.append(f'<span style="{_run_css(r)}">{esc(r.get("text", ""))}</span>')
        if not any(not r.get("br") for r in runs):
            inner.append(f'<span style="font-size:{f2(size)}px">&#8203;</span>')
        out.append(f'<p style="{";".join(css)}">{"".join(inner)}</p>')
    return "".join(out)


def _is_vert270(v):
    return v in ("270", 270, "vert270")


def text_html(tx, w, h):
    if not tx or not tx.get("paragraphs"):
        return ""
    l_in, t_in, r_in, b_in = tx.get("insets", [9.6, 4.8, 9.6, 4.8])
    anchor = tx.get("anchor", "t")
    body = paragraphs_html(tx["paragraphs"])
    pad = f"padding:{f2(t_in)}px {f2(r_in)}px {f2(b_in)}px {f2(l_in)}px"
    rot = f";transform:rotate({f2(tx['rot'])}deg)" if tx.get("rot") else ""
    nowrap = tx.get("wrap") is False
    if _is_vert270(tx.get("vert")):
        # vert270: 文字を 270 度回して下から上へ読む（行は左から右へ積む）。縦書き(vertical-rl)を 180 度回して作る。
        # 180 度回すので、anchor の上下（t / b）は縦書き(eaVert)とは逆の端に寄る
        jc = {"t": "flex-end", "ctr": "center", "b": "flex-start"}.get(anchor, "flex-end")
        return (f'<div class="cv-tx cv-vt cv-v270" style="width:{f2(w)}px;height:{f2(h)}px;{pad};justify-content:{jc}{rot}">'
                f'<div class="cv-vi cv-vi270{" cv-nw" if nowrap else ""}">{body}</div></div>')
    if tx.get("vert"):
        jc = {"t": "flex-end", "ctr": "center", "b": "flex-start"}.get(anchor, "flex-end")
        return (f'<div class="cv-tx cv-vt" style="width:{f2(w)}px;height:{f2(h)}px;{pad};justify-content:{jc}{rot}">'
                f'<div class="cv-vi{" cv-nw" if nowrap else ""}">{body}</div></div>')
    jc = {"t": "flex-start", "ctr": "center", "b": "flex-end"}.get(anchor, "flex-start")
    if nowrap:
        # 折り返しなしの文字は、段落の揃えに従って箱の左端/中央/右端を基準に伸びる
        al = (tx["paragraphs"][0].get("align", "l") if tx["paragraphs"] else "l")
        ai = {"ctr": "center", "r": "flex-end"}.get(al, "flex-start")
        return (f'<div class="cv-tx cv-nwbox" style="width:{f2(w)}px;height:{f2(h)}px;{pad};justify-content:{jc};align-items:{ai}{rot}">'
                f'<div class="cv-nw">{body}</div></div>')
    inner = "width:auto;margin:0 auto" if tx.get("anchorCtr") else "width:100%"
    return (f'<div class="cv-tx" style="width:{f2(w)}px;height:{f2(h)}px;{pad};justify-content:{jc}{rot}">'
            f'<div style="{inner}">{body}</div></div>')


# ---------------------------------------------------------------- html: other kinds
def _line_css(ln):
    if not ln:
        return "none"
    dash = ln.get("dash") or ""
    st = "dashed" if "ash" in dash else ("dotted" if "ot" in dash else "solid")
    return f"{f2(max(ln.get('width', 0.75), 0.75))}px {st} {css_color(ln.get('color'))}"


def table_html(el):
    cols = el["cols"]
    out = [f'<table class="cv-tb"{qa_ignore_attr(el)} style="left:{f2(el["x"])}px;top:{f2(el["y"])}px;width:{f2(sum(cols))}px">',
           "<colgroup>" + "".join(f'<col style="width:{f2(c)}px">' for c in cols) + "</colgroup>"]
    for row in el["rows"]:
        out.append(f'<tr style="height:{f2(row["h"])}px">')
        for c in row["cells"]:
            if c.get("merged"):
                continue
            pad = list(c.get("pad", [9.6, 4.8, 9.6, 4.8]))
            # border-collapse では罫線幅の半分がセル寸法に加算される（PowerPoint は加算しない）ため、余白から差し引く
            bds = c.get("borders", {})
            short = [0.0, 0.0, 0.0, 0.0]  # 余白で吸収しきれない分は中身の負マージンで相殺する
            for k, idx in (("l", 0), ("t", 1), ("r", 2), ("b", 3)):
                if bds.get(k):
                    half = max(bds[k].get("width", 0.75), 0.75) / 2
                    short[idx] = max(half - pad[idx], 0)
                    pad[idx] = max(pad[idx] - half, 0)
            css = [f"background:{css_color(c.get('fill')) if c.get('fill') else 'transparent'}",
                   f"padding:{f2(pad[1])}px {f2(pad[2])}px {f2(pad[3])}px {f2(pad[0])}px",
                   "vertical-align:" + {"t": "top", "ctr": "middle", "b": "bottom"}.get(c.get("anchor", "t"), "top")]
            for side, key in (("left", "l"), ("right", "r"), ("top", "t"), ("bottom", "b")):
                if key in c.get("borders", {}):
                    css.append(f"border-{side}:{_line_css(c['borders'][key])}")
            body = paragraphs_html(c.get("paragraphs", []))
            if c.get("vert"):
                body = f'<div class="cv-vc">{body}</div>'
            if any(short):
                body = (f'<div style="margin:{f2(-short[1])}px {f2(-short[2])}px {f2(-short[3])}px {f2(-short[0])}px">'
                        f"{body}</div>")
            attrs = (f' colspan="{c["span"]}"' if c.get("span", 1) > 1 else "") + \
                    (f' rowspan="{c["rowspan"]}"' if c.get("rowspan", 1) > 1 else "")
            cls = " ".join(k for k, on in (("cv-nowrap", c.get("nowrap")), ("cv-clip", c.get("clip"))) if on)
            cls = f' class="{cls}"' if cls else ""
            out.append(f'<td{attrs}{cls} style="{";".join(css)}">{body}</td>')
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


_SVG_ID_RE = re.compile(r'\bid="([^"]+)"')


def svg_html(el):
    """ベクターアイコン。id 衝突を避けるため要素ごとに接頭辞を付ける"""
    pref = _Uid.next("i") + "_"
    s = el["svg"]  # sanitize_elements() で許可リスト浄化済み
    if not s:
        return ""
    s = _SVG_ID_RE.sub(lambda m: f'id="{pref}{m.group(1)}"', s)
    s = s.replace("url(#", f"url(#{pref}")
    s = re.sub(r'(xlink:href|href)="#', lambda m: f'{m.group(1)}="#{pref}', s)
    s = re.sub(r"<svg\b", f'<svg width="{f2(el["w"])}" height="{f2(el["h"])}" preserveAspectRatio="none"', s, count=1)
    return s


def backdrop_svg(el):
    g = el["grid"]
    gx, gy = g["cols"], g["rows"]
    w, h = el["w"], el["h"]
    cw, ch = w / gx, h / gy
    fid = _Uid.next("bd")
    rects = "".join(
        f'<rect x="{f2(i * cw - 1)}" y="{f2(j * ch - 1)}" width="{f2(cw + 2)}" height="{f2(ch + 2)}" fill="{g["colors"][j * gx + i]}"/>'
        for j in range(gy) for i in range(gx))
    return (f'<svg width="{f2(w)}" height="{f2(h)}" style="position:absolute;left:0;top:0" aria-hidden="true">'
            f'<defs><filter id="{fid}" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="{f2(cw * 0.6)}"/></filter>'
            f'<clipPath id="{fid}c"><rect width="{f2(w)}" height="{f2(h)}"/></clipPath></defs>'
            f'<g clip-path="url(#{fid}c)"><g filter="url(#{fid})">{rects}</g></g></svg>')


QA_IGNORE_KINDS = ("bleed", "overlap", "lines", "orphan", "wordbreak", "minfont", "contrast", "linecross")


def qa_ignore_attr(el) -> str:
    """要素の qa_ignore（"overlap contrast" のように check_layout の種別を空白区切り）→ data-qa-ignore 属性。
    意図して重ねる要素（画像の上の文字・塗りの上のラベルなど）にだけ付ける。付けた要素と子孫はその種別の検査から外れる。"""
    v = el.get("qa_ignore")
    if isinstance(v, list):
        v = " ".join(str(x) for x in v)
    if not isinstance(v, str):
        return ""
    kinds = [w for w in v.split() if w in QA_IGNORE_KINDS]
    return f' data-qa-ignore="{" ".join(kinds)}"' if kinds else ""


def _check_qa_ignore(v, path, warn):
    """qa_ignore の値の検査（文字列か文字列の配列。種別は QA_IGNORE_KINDS）。誤りは警告（検査を黙らせたつもりで黙っていない状態を防ぐ）"""
    words = None
    if isinstance(v, str):
        words = v.split()
    elif isinstance(v, list) and all(isinstance(x, str) for x in v):
        words = [w for x in v for w in x.split()]
    if words is None:
        warn(f"canvas: {path}.qa_ignore は検査の種別を空白区切りの文字列（\"overlap contrast\"）か配列で指定してください → 無視されます")
        return
    import difflib
    for w in words:
        if w not in QA_IGNORE_KINDS:
            near = difflib.get_close_matches(w, QA_IGNORE_KINDS, n=1, cutoff=0.5)
            warn(f"canvas: {path}.qa_ignore の '{w}' は検査の種別ではありません → 使えるのは {' / '.join(QA_IGNORE_KINDS)}"
                 + (f"（もしかして: {near[0]}）" if near else ""))


def element_html(el, image_source=None):
    k = el.get("kind", "shape")
    if k == "group":
        cx, cy = el.get("origin", [0, 0])
        inner = "".join(element_html(c, image_source) for c in el.get("children", []))
        return (f'<div class="cv-grp"{qa_ignore_attr(el)} style="transform-origin:{f2(cx)}px {f2(cy)}px;'
                f'transform:rotate({f2(el.get("rot", 0))}deg)">{inner}</div>')
    if k == "table":
        return table_html(el)
    box = f'left:{f2(el["x"])}px;top:{f2(el["y"])}px;width:{f2(el["w"])}px;height:{f2(el["h"])}px'
    if el.get("rot"):
        box += f';transform:rotate({f2(el["rot"])}deg)'
    name = f' data-n="{esc(el["name"])}"' if el.get("name") else ""
    qa = qa_ignore_attr(el)
    name += qa
    title = f' title="{esc(el["alt"])}"' if el.get("alt") else ""
    if k == "image":
        return image_html(el, image_source)
    if k == "svg":
        return f'<div class="cv-s cv-svg"{name}{title} style="{box}">{svg_html(el)}</div>'
    if k == "backdrop":
        return f'<div class="cv-s"{name}{title} style="{box}">{backdrop_svg(el)}</div>'
    if k == "placeholder":
        return f'<div class="cv-s cv-ph"{name} style="{box}"><span>{esc(el.get("label", ""))}</span></div>'
    txt = ""
    if el.get("text"):
        l, t, r, b = text_rect(el)
        txt = text_html(el["text"], r - l, b - t)
        if txt and (l or t):
            txt = f'<div class="cv-tr" style="left:{f2(l)}px;top:{f2(t)}px">{txt}</div>'
    inner = _shape_svg(el) + txt
    if not inner:
        return ""
    return f'<div class="cv-s"{name} style="{box}">{inner}</div>'


def canvas_html(slide, image_source=None, deck_dir=None) -> str:
    """canvas 要素列 → HTML。kind:"image" の画像は image_source(rel_path, for_pptx, w, h) -> Path|None で読む
    （build_deck の image_source を包んで渡す）。省略時は deck_dir があれば default_image_source(deck_dir)、
    どちらも無ければ画像は灰色の枠で代用する"""
    if image_source is None and deck_dir is not None:
        image_source = default_image_source(deck_dir)
    return "".join(element_html(e, image_source) for e in sanitize_elements(slide.get("elements", [])))


CANVAS_CSS = """
.cv-s{position:absolute}
.cv-grp{position:absolute;left:0;top:0;width:1280px;height:720px}
.cv-tr{position:absolute}
.cv-sh{position:absolute;overflow:visible;pointer-events:none}
.cv-tx{position:absolute;left:0;top:0;display:flex;flex-direction:column;overflow:visible}
.cv-tx p,.cv-tb p{margin:0;white-space:pre-wrap;word-break:normal;overflow-wrap:anywhere;line-break:strict}
.cv-tx p>span,.cv-tb p>span{line-height:0}
.cv-tb td.cv-clip{overflow:hidden}
.cv-tb td.cv-nowrap{max-width:0}
.cv-tb td.cv-nowrap p{white-space:pre;overflow-wrap:normal}
.cv-nwbox{align-items:center}
.cv-nw{display:flex;flex-direction:column;width:max-content}
.cv-nw p{white-space:pre}
.cv-vt{flex-direction:row}
.cv-vi{writing-mode:vertical-rl;height:100%}
.cv-vi270{text-orientation:sideways;transform:rotate(180deg)}
.cv-bu{display:inline-block;text-indent:0}
.cv-tb{position:absolute;border-collapse:collapse;table-layout:fixed}
.cv-tb td{overflow:visible}
.cv-vc{writing-mode:vertical-rl;margin:0 auto}
.cv-svg svg{position:absolute;left:0;top:0}
.cv-img{overflow:hidden}
.cv-img img{display:block}
.cv-ph{border:1px dashed #9a9a9a;background:repeating-linear-gradient(45deg,#f4f4f4 0 10px,#ececec 10px 20px);display:flex;align-items:center;justify-content:center;text-align:center;color:#777;font-size:12px;padding:6px}
"""


# ---------------------------------------------------------------- transform (別の矩形へ写す)
def _scale_paragraphs(paras, ts):
    out = []
    for p in paras:
        q = dict(p)
        for k in ("lineHeightPx", "spaceBefore", "spaceAfter", "marL", "indent", "size"):
            if _isnum(q.get(k)):
                q[k] = q[k] * ts
        if isinstance(q.get("bullet"), dict):
            b = dict(q["bullet"])
            if _isnum(b.get("size")):
                b["size"] = b["size"] * ts
            q["bullet"] = b
        if isinstance(q.get("runs"), list):
            runs = []
            for r in q["runs"]:
                r = dict(r)
                if _isnum(r.get("size")):
                    r["size"] = r["size"] * ts
                runs.append(r)
            q["runs"] = runs
        out.append(q)
    return out


def _scale_line(ln, ts):
    if isinstance(ln, dict) and _isnum(ln.get("width")):
        ln = dict(ln, width=ln["width"] * ts)
    return ln


def transform_elements(elements, sx=1.0, sy=None, dx=0.0, dy=0.0, ts=None):
    """要素列の複製を返す。座標を x' = x*sx + dx, y' = y*sy + dy に写し、幅・高さを sx / sy 倍にする。
    文字サイズ・線幅・余白・影・表のセル余白は ts 倍（既定 min(sx, sy)）に縮める。回転・色・adj は変えない。
    group の子や table の列幅・行高も写す。入力は変更しない。
    合成スライドやパターンの埋め込みで、1280x720 用に作った要素列を小さな矩形に置くときに使う（fit_elements が便利）"""
    sy = sx if sy is None else sy
    ts = min(abs(sx), abs(sy)) if ts is None else ts

    def one(el):
        e = dict(el)
        k = e.get("kind", "shape")
        if k == "group":
            e["children"] = [one(c) for c in e.get("children", [])]
            if isinstance(e.get("origin"), list) and len(e["origin"]) == 2:
                e["origin"] = [e["origin"][0] * sx + dx, e["origin"][1] * sy + dy]
            return e
        if _isnum(e.get("x")):
            e["x"] = e["x"] * sx + dx
        if _isnum(e.get("y")):
            e["y"] = e["y"] * sy + dy
        for key, f in (("w", sx), ("h", sy)):
            if _isnum(e.get(key)):
                e[key] = e[key] * f
        if "line" in e:
            e["line"] = _scale_line(e["line"], ts)
        if isinstance(e.get("shadow"), dict):
            sh = dict(e["shadow"])
            for key in ("dx", "dy", "blur"):
                if _isnum(sh.get(key)):
                    sh[key] = sh[key] * ts
            e["shadow"] = sh
        if isinstance(e.get("text"), dict):
            tx = dict(e["text"])
            if isinstance(tx.get("insets"), list):
                tx["insets"] = [v * ts if _isnum(v) else v for v in tx["insets"]]
            if isinstance(tx.get("paragraphs"), list):
                tx["paragraphs"] = _scale_paragraphs(tx["paragraphs"], ts)
            e["text"] = tx
        if k == "table":
            e["cols"] = [c * sx if _isnum(c) else c for c in e.get("cols", [])]
            rows = []
            for row in e.get("rows", []):
                row = dict(row)
                if _isnum(row.get("h")):
                    row["h"] = row["h"] * sy
                cells = []
                for c in row.get("cells", []):
                    c = dict(c)
                    if isinstance(c.get("pad"), list):
                        c["pad"] = [v * ts if _isnum(v) else v for v in c["pad"]]
                    if isinstance(c.get("paragraphs"), list):
                        c["paragraphs"] = _scale_paragraphs(c["paragraphs"], ts)
                    if isinstance(c.get("borders"), dict):
                        c["borders"] = {side: _scale_line(b, ts) for side, b in c["borders"].items()}
                    cells.append(c)
                row["cells"] = cells
                rows.append(row)
            e["rows"] = rows
        if k == "shape" and e.get("geom") == "custom" and isinstance(e.get("path"), list):
            # custom のパス座標は要素ローカル px。幅・高さと同じ比率で伸縮させる
            e["path"] = [dict(p, cmds=[[c[0]] + [v * (sx if (n % 2 == 0) else sy) for n, v in enumerate(c[1:])]
                                       for c in p.get("cmds", [])]) for p in e["path"]]
        return e
    return [one(e) for e in elements]


def fit_elements(elements, rect, src=(1280, 720), mode="contain"):
    """1280x720（src）の座標系で作った要素列を、矩形 rect = (x, y, w, h) に収まるよう写して返す。
    mode: "contain"（既定。縦横比を保って rect の中央に収める）/ "stretch"（rect いっぱいに引き伸ばす。文字は小さい方の倍率）"""
    rx, ry, rw, rh = rect
    sw, sh = src
    if mode == "stretch":
        return transform_elements(elements, rw / sw, rh / sh, rx, ry)
    k = min(rw / sw, rh / sh)
    return transform_elements(elements, k, k, rx + (rw - sw * k) / 2, ry + (rh - sh * k) / 2)


# ---------------------------------------------------------------- image (kind: "image")
def check_image_path(rel, deck_dir=None):
    """画像パス（デッキフォルダからの相対パス）の検査。問題があれば日本語のメッセージ、なければ None。
    `..`・絶対パス・未対応の拡張子・デッキ外を指すシンボリックリンク・存在しないファイルを弾く
    （canvas 経由でデッキ外のファイルを読めないようにする）。deck_dir が None のときは文字列としての検査だけ行う"""
    from pathlib import Path, PurePosixPath, PureWindowsPath
    if not isinstance(rel, str) or not rel.strip():
        return "path が指定されていません → assets/ 配下の相対パスを書いてください（例: assets/photo.png）"
    if rel.startswith(("/", "\\", "~")) or PureWindowsPath(rel).drive or Path(rel).is_absolute():
        return f"path '{rel}' は絶対パスです → デッキフォルダからの相対パス（assets/photo.png）にしてください"
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    if ".." in parts:
        return f"path '{rel}' に .. が含まれています → デッキフォルダの外は指せません。assets/ 配下に画像を置いてください"
    ext = Path(rel).suffix.lower()
    if ext not in IMAGE_EXTS:
        return (f"画像形式 '{ext or rel}' には対応していません"
                f" → {', '.join(sorted(e.lstrip('.') for e in IMAGE_EXTS))} のいずれかにしてください")
    if deck_dir is not None:
        try:
            base = Path(deck_dir).resolve()
            full = (base / rel).resolve()
        except (OSError, ValueError):
            return f"path '{rel}' を解決できません"
        if full != base and not full.is_relative_to(base):
            return f"path '{rel}' がデッキフォルダの外を指しています → assets/ 配下に画像を置いてください"
        if not full.is_file():
            return f"画像ファイルが見つかりません: {rel} → パスとファイル名を確かめてください"
        try:
            from deck_schema import image_too_big      # 巨大な画素数の画像は置き直してもらう（メモリを使い切る）
            big = image_too_big(full, rel)
        except ImportError:
            big = None
        if big:
            return big
    return None


def default_image_source(deck_dir, max_px=2560):
    """kind:"image" の既定の画像読み込み関数を返す。単体（build_deck 抜き）でも動く。
    戻り値の関数の形: source(rel_path, for_pptx, target_w=None, target_h=None, fit="contain") -> Path | None
      （fit="cover" のとき、縮小の上限を「枠を埋めるのに必要な倍率」から決める。canvas_engine は accepts_fit が真の関数にだけ fit を渡す）
      - HTML 用（for_pptx=False）: svg はそのまま。ラスタ画像は表示枠の 2 倍（最大 max_px）を超えるときだけ縮小して
        deck_dir/build/.img-cache/ に書く（Pillow が無ければ原本）。
      - PPTX 用: webp / tiff / bmp は PNG にして返す。svg は既定ではラスタ化できないので None（呼び出し側が差し替える）。
    build_deck から使うときは、build_deck.image_source をこの形に包んで canvas_html / add_canvas_to_pptx の
    image_source 引数に渡す（例: lambda rel, pp, w=None, h=None: image_source(deck_dir, rel, pp, None, w, h)）。
    パスはここでも check_image_path で再検査する（不正なら None）"""
    from pathlib import Path
    base = Path(deck_dir).resolve()

    def source(rel, for_pptx, target_w=None, target_h=None, fit="contain"):
        if check_image_path(rel, base):
            return None
        src = (base / rel).resolve()
        ext = src.suffix.lower()
        if ext == ".svg":
            return None if for_pptx else src
        need_png = for_pptx and ext in (".webp", ".tiff", ".bmp")
        try:
            from PIL import Image
        except ImportError:
            return None if need_png else src
        try:
            with Image.open(src) as im:
                iw, ih = im.size
                limit = max_px
                if target_w and target_h:
                    if fit == "cover":
                        # cover は短辺側に合わせて拡大してから切り抜く。画像全体の長辺を枠の長辺で決めると、
                        # 極端な縦横比（8000x1000 を 300x300 に敷く等）で必要より小さく縮んで荒れる。
                        # 必要倍率 k で表示される大きさの 2 倍までを残す
                        k_need = max(target_w / iw, target_h / ih)
                        limit = min(max_px, max(iw, ih) * min(1.0, 2.0 * k_need))
                    else:
                        limit = min(max_px, max(target_w, target_h) * 2)
                if not need_png and max(iw, ih) <= limit:
                    return src
                cache = base / "build" / ".img-cache"
                cache.mkdir(parents=True, exist_ok=True)
                import hashlib
                tag = hashlib.sha1(f"{src}:{int(limit)}:{need_png}".encode()).hexdigest()[:8]
                keep_alpha = im.mode in ("RGBA", "LA", "P")
                out_ext = ".png" if (need_png or keep_alpha) else ext
                out = cache / f"{src.stem}-{tag}{out_ext}"
                if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
                    k = min(1.0, limit / max(iw, ih))
                    im2 = im.convert("RGBA" if keep_alpha else "RGB")
                    if k < 1.0:
                        im2 = im2.resize((max(1, round(iw * k)), max(1, round(ih * k))), Image.LANCZOS)
                    im2.save(out)
                return out
        except Exception:
            return None if need_png else src
    source.accepts_fit = True
    return source


def _call_image_source(image_source, el, for_pptx):
    """image_source(rel, for_pptx, w, h) を呼ぶ。fit を受け取れる実装（default_image_source の戻り値）には fit も渡す
    （build_deck 側の 4 引数の関数にはそのまま 4 引数で呼ぶ）"""
    if getattr(image_source, "accepts_fit", False):
        fit = el.get("fit", "cover") if el.get("fit") in IMAGE_FITS else "cover"
        return image_source(el.get("path"), for_pptx, el["w"], el["h"], fit)
    return image_source(el.get("path"), for_pptx, el["w"], el["h"])


def _image_data_uri(path):
    import base64
    import mimetypes
    mt = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).lower().endswith(".svg"):
        mt = "image/svg+xml"
    with open(path, "rb") as f:
        return f"data:{mt};base64,{base64.b64encode(f.read()).decode()}"


def _position_xy(el):
    """画像の position（cover で切り抜く位置。center / top / "30% 70%" …）→ (x, y) 各 0〜1。無い・不正なら中央。"""
    v = el.get("position")
    if not isinstance(v, str):
        return (0.5, 0.5)
    try:
        import hero_engine
        return hero_engine.parse_position(v) or (0.5, 0.5)
    except ImportError:     # pragma: no cover
        return (0.5, 0.5)


def _object_position(el) -> str:
    x, y = _position_xy(el)
    return "" if (x, y) == (0.5, 0.5) else f"object-position:{x * 100:g}% {y * 100:g}%;"


def image_html(el, image_source=None):
    """kind:"image" → HTML。image_source が無い・画像を解決できないときは灰色の枠で代用する"""
    path = None
    if image_source is not None:
        try:
            path = _call_image_source(image_source, el, False)
        except Exception:
            path = None
    box = f'left:{f2(el["x"])}px;top:{f2(el["y"])}px;width:{f2(el["w"])}px;height:{f2(el["h"])}px'
    if el.get("rot"):
        box += f';transform:rotate({f2(el["rot"])}deg)'
    name = f' data-n="{esc(el["name"])}"' if el.get("name") else ""
    name += qa_ignore_attr(el)
    if isinstance(el.get("qa_bg"), str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", el["qa_bg"]):
        name += f' data-qa-bg="{el["qa_bg"]}"'       # 画像の上の文字の対比を check_layout が測れるよう、画像の「文字にとって最悪の色」を渡す
    if path is None:
        return f'<div class="cv-s cv-ph"{name} style="{box}"><span>{esc(el.get("alt") or el.get("path") or "画像")}</span></div>'
    fit = el.get("fit", "cover") if el.get("fit") in IMAGE_FITS else "cover"
    if _isnum(el.get("radius")) and el["radius"] > 0 and fit == "cover":
        box += f';border-radius:{f2(el["radius"])}px'      # 角丸（cover のときだけ。.cv-img の overflow:hidden で画像も丸く切る）
    flip = "transform:" + " ".join(t for t, on in (("scaleX(-1)", el.get("flipH")), ("scaleY(-1)", el.get("flipV"))) if on) + ";" \
        if el.get("flipH") or el.get("flipV") else ""
    return (f'<div class="cv-s cv-img"{name} style="{box}"><img src="{_image_data_uri(path)}" alt="{esc(el.get("alt", ""))}" '
            f'style="width:100%;height:100%;object-fit:{fit};{_object_position(el)}{flip}"></div>')


# ---------------------------------------------------------------- validation
_NUM_KEYS = {"x", "y", "w", "h", "rot", "size", "width", "lineHeight", "lineHeightPx", "spaceBefore", "spaceAfter",
             "marL", "indent", "baseline", "dx", "dy", "blur", "angle", "weight", "tracking", "radius"}
_NUM_LISTS = {"insets": 4, "pad": 4, "origin": 2}


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _show(v):
    """エラー文に出す値の短い表示（長い値・入れ子の値を切る）"""
    t = repr(v)
    return t if len(t) <= 40 else t[:37] + "…"


def _check_types(obj, path, out):
    """数値であるべきキー・数値の配列であるべきキーの型を検査する（描画時の例外を前もって潰す）"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("head", "tail"):
                continue  # 矢じりの w / len は sm/med/lg（sanitize が検査）
            if k in _NUM_KEYS and not _isnum(v):
                out.append(f"{path}.{k} {_show(v)} は数値で指定してください（例: 24）。"
                           f"文字列・配列・オブジェクト・true / false・NaN / Infinity は使えません")
            elif k in _NUM_LISTS:
                if not (isinstance(v, list) and len(v) == _NUM_LISTS[k] and all(_isnum(x) for x in v)):
                    out.append(f"{path}.{k} は数値 {_NUM_LISTS[k]} 個の配列で指定してください（例: [10, 5, 10, 5]）")
            elif isinstance(v, (dict, list)):
                _check_types(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for j, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                _check_types(v, f"{path}[{j}]", out)


def _check_style_types(el, path, out):
    """line / shadow / fill の型と w / h の符号を検査する（描画時の AttributeError / TypeError と、負の大きさの XML を前もって潰す）"""
    for key in ("w", "h"):
        v = el.get(key)
        if _isnum(v) and v < 0:
            out.append(f"{path}.{key} が負の値（{v:g}）です → 0 以上にしてください"
                       f"（パターンの場合は個数が多すぎて枠が潰れている可能性があります。スロットの個数を減らしてください）")
    ln = el.get("line")
    if ln and not isinstance(ln, dict):
        out.append(f"{path}.line はオブジェクトで指定してください（例: {{\"color\": \"#333333\", \"width\": 2}}）")
    elif isinstance(ln, dict) and "color" in ln and not isinstance(ln["color"], (str, dict)):
        out.append(f"{path}.line.color は色の文字列（#RRGGBB）で指定してください")
    sh = el.get("shadow")
    if sh and not isinstance(sh, dict):
        out.append(f"{path}.shadow はオブジェクトで指定してください（例: {{\"dx\": 0, \"dy\": 4, \"blur\": 12, \"color\": \"#000000\"}}）")
    elif isinstance(sh, dict) and "color" in sh and not isinstance(sh["color"], (str, dict)):
        out.append(f"{path}.shadow.color は色の文字列（#RRGGBB）で指定してください")
    fl = el.get("fill")
    if fl is not None and not isinstance(fl, (str, dict)):
        out.append(f"{path}.fill は色の文字列（#RRGGBB）か {{\"gradient\": …}} などのオブジェクトで指定してください")
    elif isinstance(fl, dict):
        gr = fl.get("gradient")
        if gr is not None and not (isinstance(gr, dict) and isinstance(gr.get("stops"), list)):
            out.append(f"{path}.fill.gradient は {{\"stops\": [[0, \"#FFFFFF\"], [100, \"#000000\"]], \"angle\": 90}} の形で指定してください")


def _check_font(f, path, out):
    if f is None:
        return
    if not (isinstance(f, str) or (isinstance(f, list) and all(isinstance(x, str) for x in f))):
        out.append(f"{path}.font はフォント名の文字列か、文字列の配列で指定してください（例: [\"Meiryo UI\"]）")


def _check_text(tx, path, out):
    if tx is None:
        return
    if not isinstance(tx, dict):
        out.append(f"{path} はオブジェクトで指定してください")
        return
    paras = tx.get("paragraphs")
    if not isinstance(paras, list):
        out.append(f"{path}.paragraphs は配列で指定してください")
        return
    for j, p in enumerate(paras):
        pp = f"{path}.paragraphs[{j}]"
        if not isinstance(p, dict):
            out.append(f"{pp} はオブジェクトで指定してください")
            continue
        runs = p.get("runs", [])
        if not isinstance(runs, list):
            out.append(f"{pp}.runs は配列で指定してください")
            continue
        for q, r in enumerate(runs):
            if not isinstance(r, dict):
                out.append(f"{pp}.runs[{q}] はオブジェクトで指定してください")
            else:
                if "text" in r and not isinstance(r["text"], str):
                    out.append(f"{pp}.runs[{q}].text {_show(r['text'])} は文字列で指定してください")
                if "size" in r and _isnum(r["size"]) and r["size"] <= 0:
                    out.append(f"{pp}.runs[{q}].size は 0 より大きい数値にしてください")
                _check_font(r.get("font"), f"{pp}.runs[{q}]", out)
        if "bullet" in p and not isinstance(p["bullet"], dict):
            out.append(f"{pp}.bullet はオブジェクトで指定してください（例: {{\"char\": \"•\"}}）")
        elif isinstance(p.get("bullet"), dict):
            _check_font(p["bullet"].get("font"), f"{pp}.bullet", out)


def validate_canvas_problems(slide, deck_dir=None, warn=None):
    """canvas スライドの問題を全件集めて文字列のリストで返す（位置情報つき）。fail / warn を呼ばないので単体でも使える。
    warn が渡されたときは、致命的ではないもの（未対応の geom）をそちらへ流す"""
    out: list = []
    els = slide.get("elements")
    if not isinstance(els, list):
        return ["elements は配列で指定してください"]

    def num(el, key, p):
        if key not in el:  # 型の誤りは _check_types が報告する
            out.append(f"{p}.{key} がありません → 数値で指定してください")

    def walk(lst, path):
        for j, el in enumerate(lst):
            p = f"{path}[{j}]"
            if not isinstance(el, dict):
                out.append(f"{p} はオブジェクトである必要があります")
                continue
            k = el.get("kind", "shape")
            if k not in KINDS:
                out.append(f"{p}.kind '{k}' は未知です（{', '.join(sorted(KINDS))}）")
                continue
            if "qa_ignore" in el and warn:
                _check_qa_ignore(el["qa_ignore"], p, warn)
            if k == "group":
                ch = el.get("children", [])
                if not isinstance(ch, list):
                    out.append(f"{p}.children は配列で指定してください")
                else:
                    walk(ch, p + ".children")
                _check_types({kk: vv for kk, vv in el.items() if kk != "children"}, p, out)
                continue
            num(el, "x", p)
            num(el, "y", p)
            if k != "table":
                num(el, "w", p)
                num(el, "h", p)
            _check_types(el, p, out)
            _check_style_types(el, p, out)
            if k == "shape":
                g = el.get("geom", "rect")
                if isinstance(g, str) and g not in GEOMS and warn:     # 文字列でない geom は sanitize が報告する
                    warn(f"canvas: {p}.geom '{g}' は未対応のため矩形で描きます")
                if g == "custom" and not isinstance(el.get("path"), list):
                    out.append(f"{p}.path がありません → geom が custom のときは path（コマンド列）が必要です")
                elif g == "custom":
                    for q, sub in enumerate(el["path"]):
                        if not (isinstance(sub, dict) and isinstance(sub.get("cmds"), list)):
                            out.append(f"{p}.path[{q}] は {{\"cmds\": [[\"M\", 0, 0], …]}} の形で指定してください")
                _check_text(el.get("text"), p + ".text", out)
            elif k == "table":
                cols, rows = el.get("cols"), el.get("rows")
                if not (isinstance(cols, list) and cols and all(_isnum(c) for c in cols)):
                    out.append(f"{p}.cols は列幅（px）の数値配列で指定してください（例: [200, 300]）")
                if not isinstance(rows, list):
                    out.append(f"{p}.rows は配列で指定してください")
                else:
                    for r, row in enumerate(rows):
                        rp = f"{p}.rows[{r}]"
                        if not isinstance(row, dict):
                            out.append(f"{rp} はオブジェクトで指定してください")
                            continue
                        if not _isnum(row.get("h")):
                            out.append(f"{rp}.h が数値ではありません → 行の高さ（px）を指定してください")
                        cells = row.get("cells")
                        if not isinstance(cells, list):
                            out.append(f"{rp}.cells は配列で指定してください")
                            continue
                        for c, cell in enumerate(cells):
                            if not isinstance(cell, dict):
                                out.append(f"{rp}.cells[{c}] はオブジェクトで指定してください")
                            else:
                                _check_text({"paragraphs": cell.get("paragraphs", [])}, f"{rp}.cells[{c}]", out)
            elif k == "svg":
                if not isinstance(el.get("svg"), str):
                    out.append(f"{p}.svg は SVG の文字列で指定してください")
                elif "<script" in el["svg"].lower():
                    out.append(f"{p}.svg に script を含めることはできません")
            elif k == "backdrop":
                g = el.get("grid")
                if not (isinstance(g, dict) and isinstance(g.get("cols"), int) and isinstance(g.get("rows"), int)
                        and g["cols"] > 0 and g["rows"] > 0 and isinstance(g.get("colors"), list)
                        and len(g["colors"]) == g["cols"] * g["rows"]):
                    out.append(f"{p}.grid は {{cols, rows, colors}} で、colors の個数は cols×rows にしてください")
            elif k == "image":
                msg = check_image_path(el.get("path"), deck_dir)
                if msg:
                    out.append(f"{p}: {msg}")
                if "fit" in el and el["fit"] not in IMAGE_FITS:
                    out.append(f"{p}.fit '{el['fit']}' は cover / contain のいずれかです")
    walk(els, "elements")
    # 色・列挙値・フォント名・パス命令・SVG を描画と同じ規則で検査する（置き換えが起きる値はエラー）
    issues: list = []
    sanitize_elements(els, "elements", issues)
    # 同じ場所を型の検査（上）と浄化が両方報告したときは、先に出した型の検査の 1 件だけにする
    out.extend(m for m in issues if not any(o.startswith(m.split(":", 1)[0] + " ") for o in out))
    del out[200:]
    return out


def validate_canvas(slide, i, fail, warn, deck_dir=None):
    """canvas スライドの検証。問題は 1 件で止めず全件まとめて fail に渡す（最大 30 件）。
    deck_dir を渡すと kind:"image" の画像ファイルの存在・デッキ外参照も検査する"""
    head = f"{i + 1}枚目（type=canvas）: "
    problems = validate_canvas_problems(slide, deck_dir, lambda m: warn(head + m.removeprefix("canvas: ")))
    if problems:
        extra = f"\n  …ほか {len(problems) - 30} 件" if len(problems) > 30 else ""
        fail(head + problems[0] + "".join(f"\n  {head}{m}" for m in problems[1:30]) + extra)


# ---------------------------------------------------------------- pptx
def _emu(v):
    return int(round(v * EMU_PER_PX))


def _hex(c):
    if c is None:
        return None, 1.0
    if isinstance(c, str):
        return c.lstrip("#").upper(), 1.0
    return c.get("color", "#000000").lstrip("#").upper(), c.get("alpha", 1.0)


def _solid_xml(c):
    hx, a = _hex(c)
    alpha = f'<a:alpha val="{int(a * 100000)}"/>' if a < 0.999 else ""
    return f'<a:solidFill><a:srgbClr val="{hx}">{alpha}</a:srgbClr></a:solidFill>'


def _fill_xml(fill):
    if fill is None:
        return "<a:noFill/>"
    if isinstance(fill, str) or "color" in fill:
        return _solid_xml(fill)
    if "gradient" in fill:
        gr = fill["gradient"]
        gs = "".join(f'<a:gs pos="{int(p * 1000)}"><a:srgbClr val="{_hex(c)[0]}"/></a:gs>' for p, c in gr["stops"])
        return f'<a:gradFill><a:gsLst>{gs}</a:gsLst><a:lin ang="{int(gr.get("angle", 90) * 60000)}" scaled="0"/></a:gradFill>'
    if "pattern" in fill:
        return (f'<a:pattFill prst="{fill["pattern"]}"><a:fgClr><a:srgbClr val="{_hex(fill.get("fg", "#000000"))[0]}"/></a:fgClr>'
                f'<a:bgClr><a:srgbClr val="{_hex(fill.get("bg", "#FFFFFF"))[0]}"/></a:bgClr></a:pattFill>')
    return "<a:noFill/>"


def _ln_xml(line, tag="a:ln"):
    if not line:
        return f"<{tag}><a:noFill/></{tag}>"
    dash = f'<a:prstDash val="{line["dash"]}"/>' if line.get("dash") else ""
    ends = ""
    for k, t in (("head", "a:headEnd"), ("tail", "a:tailEnd")):
        if line.get(k):
            e = line[k]
            ends += f'<{t} type="{e.get("type", "triangle")}" w="{e.get("w", "med")}" len="{e.get("len", "med")}"/>'
    cap = f' cap="{line["cap"]}"' if line.get("cap") else ""
    return f'<{tag} w="{_emu(line.get("width", 0.75))}"{cap}>{_solid_xml(line.get("color", "#000000"))}{dash}{ends}</{tag}>'


def _shadow_xml(sh):
    """shadow {dx, dy, blur, color} → <a:effectLst><a:outerShdw>（HTML の drop-shadow と同じ向き・ぼかし）"""
    if not isinstance(sh, dict):
        return ""
    dx, dy = float(sh.get("dx", 0)), float(sh.get("dy", 0))
    dist = math.hypot(dx, dy)
    ang = int(round(math.degrees(math.atan2(dy, dx)) % 360 * 60000)) if dist else 0
    hx, a = _hex(sh.get("color", "#000000"))
    alpha = f'<a:alpha val="{int(a * 100000)}"/>' if a < 0.999 else ""
    return (f'<a:effectLst><a:outerShdw blurRad="{_emu(float(sh.get("blur", 0)))}" dist="{_emu(dist)}" dir="{ang}" '
            f'algn="ctr" rotWithShape="0"><a:srgbClr val="{hx}">{alpha}</a:srgbClr></a:outerShdw></a:effectLst>')


def _runs_xml(p):
    out = []
    for r in p.get("runs", []):
        if r.get("br"):
            out.append("<a:br/>")
            continue
        attrs = f' lang="ja-JP" sz="{int(round(r.get("size", 24) * 75))}"'
        if (r["weight"] >= 600) if _isnum(r.get("weight")) else r.get("bold"):
            attrs += ' b="1"'
        if _isnum(r.get("tracking")) and r["tracking"]:
            attrs += f' spc="{max(-400000, min(400000, int(round(r["tracking"] * r.get("size", 24) * 75))))}"'
        if r.get("italic"):
            attrs += ' i="1"'
        if r.get("underline"):
            attrs += ' u="sng"'
        if r.get("strike"):
            attrs += ' strike="sngStrike"'
        if r.get("baseline"):
            attrs += f' baseline="{int(r["baseline"] * 1000)}"'
        fonts = r.get("font", [])
        lat = esc(fonts[0]) if fonts else "Meiryo UI"
        ea = esc(fonts[-1]) if fonts else "Meiryo UI"
        rpr = (f'<a:rPr{attrs}>{_solid_xml(r.get("color", "#000000"))}<a:latin typeface="{lat}"/>'
               f'<a:ea typeface="{ea}"/></a:rPr>')
        # 文字列の中の改行（\n。泣き別れ対策の改行など）は段落内の改行（a:br）にする。a:t に生の改行を入れても PowerPoint では改行にならない
        pieces = str(r.get("text", "")).replace("\r\n", "\n").split("\n")
        for k, piece in enumerate(pieces):
            if k:
                out.append(f'<a:br><a:rPr{attrs}/></a:br>')
            if piece or len(pieces) == 1:
                out.append(f'<a:r>{rpr}<a:t>{esc(piece)}</a:t></a:r>')
    return "".join(out)


def _paras_xml(paras):
    out = []
    for p in paras:
        algn = p.get("align", "l")
        ln = f'<a:lnSpc><a:spcPct val="{int(p.get("lineHeight", 1.0) * 100000)}"/></a:lnSpc>'
        if p.get("lineHeightPx"):
            ln = f'<a:lnSpc><a:spcPts val="{int(p["lineHeightPx"] * 75)}"/></a:lnSpc>'
        sp = (f'<a:spcBef><a:spcPts val="{int(p.get("spaceBefore", 0) * 75)}"/></a:spcBef>'
              f'<a:spcAft><a:spcPts val="{int(p.get("spaceAfter", 0) * 75)}"/></a:spcAft>')
        bu = "<a:buNone/>"
        if p.get("bullet"):
            b = p["bullet"]
            # 記号の色・大きさも HTML（cv-bu）と同じに揃える（指定が無いと PowerPoint は本文と同じ色・大きさで描き、HTML と食い違う）
            bu = ""
            if b.get("color"):
                bu += f'<a:buClr><a:srgbClr val="{_hex(b["color"])[0]}"/></a:buClr>'
            run_sizes = [r.get("size") for r in p.get("runs", []) if not r.get("br") and _isnum(r.get("size"))]
            base = max(run_sizes) if run_sizes else (p.get("size") if _isnum(p.get("size")) else None)
            if _isnum(b.get("size")) and base:
                bu += f'<a:buSzPct val="{int(min(max(b["size"] / base, 0.25), 4.0) * 100000)}"/>'
            bu += f'<a:buChar char="{esc(b.get("char", "•"))}"/>'
        out.append(f'<a:p><a:pPr marL="{_emu(p.get("marL", 0))}" indent="{_emu(p.get("indent", 0))}" algn="{algn}">'
                   f'{ln}{sp}{bu}</a:pPr>{_runs_xml(p)}</a:p>')
    return "".join(out) or "<a:p/>"


def _txbody_xml(tx, tag="p:txBody"):
    if not tx:
        return f'<{tag}><a:bodyPr/><a:lstStyle/><a:p/></{tag}>'
    l_in, t_in, r_in, b_in = tx.get("insets", [9.6, 4.8, 9.6, 4.8])
    vert = ' vert="vert270"' if _is_vert270(tx.get("vert")) else (' vert="eaVert"' if tx.get("vert") else "")
    wrap = ' wrap="none"' if tx.get("wrap") is False else ' wrap="square"'
    actr = ' anchorCtr="1"' if tx.get("anchorCtr") else ""
    return (f'<{tag}><a:bodyPr lIns="{_emu(l_in)}" tIns="{_emu(t_in)}" rIns="{_emu(r_in)}" bIns="{_emu(b_in)}"'
            f' anchor="{tx.get("anchor", "t")}"{vert}{wrap}{actr} rtlCol="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>'
            f'{_paras_xml(tx.get("paragraphs", []))}</{tag}>')


def _geom_xml(el):
    g = el.get("geom", "rect")
    if g == "custom":
        w, h = _emu(el["w"]), _emu(el["h"])
        paths = []
        for p in el.get("path", []):
            cmds = []
            for c in p["cmds"]:
                pts = [(_emu(c[i]), _emu(c[i + 1])) for i in range(1, len(c), 2)]
                tag = {"M": "moveTo", "L": "lnTo", "C": "cubicBezTo", "Q": "quadBezTo"}.get(c[0])
                if c[0] == "Z":
                    cmds.append("<a:close/>")
                elif tag:
                    cmds.append(f"<a:{tag}>" + "".join(f'<a:pt x="{x}" y="{y}"/>' for x, y in pts) + f"</a:{tag}>")
            fl = "" if p.get("fill", True) else ' fill="none"'
            sk = "" if p.get("stroke", True) else ' stroke="0"'
            paths.append(f'<a:path w="{w}" h="{h}"{fl}{sk}>{"".join(cmds)}</a:path>')
        return (f'<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/>'
                f'<a:pathLst>{"".join(paths)}</a:pathLst></a:custGeom>')
    if g not in GEOMS:
        g = "rect"
    av = "".join(f'<a:gd name="{k}" fmla="val {int(v)}"/>' for k, v in el.get("adj", {}).items())
    return f'<a:prstGeom prst="{g}"><a:avLst>{av}</a:avLst></a:prstGeom>'


def _xfrm_xml(el, tag="a:xfrm"):
    rot = f' rot="{int(el.get("rot", 0) * 60000)}"' if el.get("rot") else ""
    fh = ' flipH="1"' if el.get("flipH") else ""
    fv = ' flipV="1"' if el.get("flipV") else ""
    return (f'<{tag}{rot}{fh}{fv}><a:off x="{_emu(el["x"])}" y="{_emu(el["y"])}"/>'
            f'<a:ext cx="{_emu(el["w"])}" cy="{_emu(el["h"])}"/></{tag}>')


NSDECL = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def element_pptx_xml(el, sid):
    """要素 → spTree 直下に置く XML 文字列（svg/backdrop は None を返し、呼び出し側で画像化する）"""
    k = el.get("kind", "shape")
    name = esc(el.get("name") or f"canvas {sid}")
    if k == "shape":
        is_line = el.get("geom") in LINE_GEOMS
        fill = "<a:noFill/>" if is_line else _fill_xml(el.get("fill"))
        # 影は HTML（_shape_svg）と同じく、塗りか線のある図形にだけ付ける
        shadow = _shadow_xml(el.get("shadow")) if (el.get("shadow") and (el.get("line") or (el.get("fill") and not is_line))) else ""
        if is_line:
            return (f'<p:cxnSp {NSDECL}><p:nvCxnSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
                    f'<p:spPr>{_xfrm_xml(el)}{_geom_xml(el)}{fill}{_ln_xml(el.get("line"))}{shadow}</p:spPr></p:cxnSp>')
        return (f'<p:sp {NSDECL}><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                f'<p:spPr>{_xfrm_xml(el)}{_geom_xml(el)}{fill}{_ln_xml(el.get("line"))}{shadow}</p:spPr>'
                f'{_txbody_xml(el.get("text"))}</p:sp>')
    if k == "placeholder":
        tx = {"anchor": "ctr", "paragraphs": [{"align": "ctr", "runs": [{"text": el.get("label", ""), "size": 12, "color": "#777777"}]}]}
        e2 = dict(el, geom="rect", fill="#F0F0F0", line={"color": "#9A9A9A", "width": 1, "dash": "dash"}, text=tx)
        e2["kind"] = "shape"
        return element_pptx_xml(e2, sid)
    if k == "table":
        cols = "".join(f'<a:gridCol w="{_emu(c)}"/>' for c in el["cols"])
        rows = []
        for row in el["rows"]:
            cells = []
            for c in row["cells"]:
                attrs = ""
                if c.get("span", 1) > 1:
                    attrs += f' gridSpan="{c["span"]}"'
                if c.get("rowspan", 1) > 1:
                    attrs += f' rowSpan="{c["rowspan"]}"'
                if c.get("merged") == "h":
                    attrs += ' hMerge="1"'
                elif c.get("merged") == "v":
                    attrs += ' vMerge="1"'
                pad = c.get("pad", [9.6, 4.8, 9.6, 4.8])
                bd = "".join(_ln_xml(c.get("borders", {}).get(s), t) for s, t in (("l", "a:lnL"), ("r", "a:lnR"), ("t", "a:lnT"), ("b", "a:lnB")))
                tx = {"paragraphs": c.get("paragraphs", [])}
                body = _txbody_xml(tx, "a:txBody").replace("<a:noAutofit/>", "")
                cells.append(f'<a:tc{attrs}>{body}<a:tcPr marL="{_emu(pad[0])}" marR="{_emu(pad[2])}" marT="{_emu(pad[1])}" '
                             f'marB="{_emu(pad[3])}" anchor="{c.get("anchor", "t")}">{bd}{_fill_xml(c.get("fill"))}</a:tcPr></a:tc>')
            rows.append(f'<a:tr h="{_emu(row["h"])}">{"".join(cells)}</a:tr>')
        return (f'<p:graphicFrame {NSDECL}><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="{name}"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
                f'{_xfrm_xml(dict(el, w=sum(el["cols"]), h=sum(r["h"] for r in el["rows"])), "p:xfrm")}'
                f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
                f'<a:tbl><a:tblPr/><a:tblGrid>{cols}</a:tblGrid>{"".join(rows)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
    return None


def flatten(elements):
    """group を展開した要素列（PPTX 出力用。group の回転は子に加算する簡易処理）"""
    for el in elements:
        if el.get("kind") == "group":
            for c in flatten(el.get("children", [])):
                if el.get("rot") and c.get("kind") != "table":
                    c = dict(c)
                    cx, cy = el.get("origin", [0, 0])
                    ang = math.radians(el["rot"])
                    mx, my = c["x"] + c.get("w", 0) / 2 - cx, c["y"] + c.get("h", 0) / 2 - cy
                    nx, ny = cx + mx * math.cos(ang) - my * math.sin(ang), cy + mx * math.sin(ang) + my * math.cos(ang)
                    c["x"], c["y"] = nx - c.get("w", 0) / 2, ny - c.get("h", 0) / 2
                    c["rot"] = c.get("rot", 0) + el["rot"]
                yield c
        else:
            yield el


def _add_image_to_pptx(slide, el, path):
    """kind:"image" を python-pptx の picture として置く。cover は枠いっぱいに拡大して余りを切り抜き、contain は枠の中央に収める"""
    from pptx.util import Emu
    x, y, w, h = el["x"], el["y"], el["w"], el["h"]
    iw = ih = None
    try:
        from PIL import Image
        with Image.open(path) as im:
            iw, ih = im.size
    except Exception:
        pass
    fit = el.get("fit", "cover") if el.get("fit") in IMAGE_FITS else "cover"
    crop = (0.0, 0.0, 0.0, 0.0)
    if iw and ih and w > 0 and h > 0:
        if fit == "contain":
            k = min(w / iw, h / ih)
            nw, nh = iw * k, ih * k
            x, y, w, h = x + (w - nw) / 2, y + (h - nh) / 2, nw, nh
        else:
            k = max(w / iw, h / ih)
            vis_w, vis_h = w / (iw * k), h / (ih * k)  # 画像のうち見える割合
            px, py = _position_xy(el)
            cx0, cy0 = (1 - vis_w) * px, (1 - vis_h) * py          # position（既定は中央）に合わせて切り抜く位置を決める
            crop = (cx0, cy0, 1 - vis_w - cx0, 1 - vis_h - cy0)
    pic = slide.shapes.add_picture(str(path), Emu(_emu(x)), Emu(_emu(y)), Emu(_emu(w)), Emu(_emu(h)))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = crop
    if _isnum(el.get("radius")) and el["radius"] > 0 and fit == "cover":
        from pptx.enum.shapes import MSO_SHAPE
        pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
        av = pic._element.spPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom").find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}avLst")
        for gd in list(av):
            av.remove(gd)
        gd = av.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}gd",
                            {"name": "adj", "fmla": f"val {int(min(0.5, el['radius'] / max(1.0, min(w, h))) * 100000)}"})
        av.append(gd)
    if el.get("rot"):
        pic.rotation = el["rot"]
    if el.get("name"):
        pic.name = str(el["name"])
    if el.get("alt"):
        pic._element.nvPicPr.cNvPr.set("descr", str(el["alt"]))
    if el.get("flipH") or el.get("flipV"):
        xfrm = pic._element.spPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
        if xfrm is not None:
            if el.get("flipH"):
                xfrm.set("flipH", "1")
            if el.get("flipV"):
                xfrm.set("flipV", "1")
    return pic


def add_canvas_to_pptx(slide, elements, png_for_svg=None, png_for_backdrop=None, image_source=None, deck_dir=None):
    """python-pptx の slide に canvas 要素を追加する。
    kind:"image" は image_source(rel_path, for_pptx, w, h) -> Path|None で読む（省略時は deck_dir があれば
    default_image_source(deck_dir)。読めないときは灰色の枠で代用する）"""
    from pptx.oxml import parse_xml
    from pptx.util import Emu
    if image_source is None and deck_dir is not None:
        image_source = default_image_source(deck_dir)
    tree = slide.shapes._spTree
    # 同じスライドに何度追加しても図形 ID が重ならないよう、既存の最大 ID の次から振る
    sid = max([100] + [int(v) for v in tree.xpath(".//p:cNvPr/@id") if str(v).isdigit()])
    for el in flatten(sanitize_elements(elements)):
        sid += 1
        k = el.get("kind", "shape")
        if k == "image":
            path = None
            if image_source is not None:
                try:
                    path = _call_image_source(image_source, el, True)
                except Exception:
                    path = None
            if path:
                _add_image_to_pptx(slide, el, path)
            else:
                xml = element_pptx_xml(dict(el, kind="placeholder", label=el.get("alt") or el.get("path") or "画像"), sid)
                tree.append(parse_xml(xml))
            continue
        if k in ("svg", "backdrop"):
            png = (png_for_svg if k == "svg" else png_for_backdrop)
            path = png(el) if png else None
            if path:
                pic = slide.shapes.add_picture(str(path), Emu(_emu(el["x"])), Emu(_emu(el["y"])),
                                               Emu(_emu(el["w"])), Emu(_emu(el["h"])))
                if el.get("rot"):
                    pic.rotation = el["rot"]
            continue
        xml = element_pptx_xml(el, sid)
        if xml:
            tree.append(parse_xml(xml))

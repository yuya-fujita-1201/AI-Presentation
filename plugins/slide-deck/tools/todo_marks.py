#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【要確認】マーカーの強調表示（HTML と PPTX の両方。タイプごとの実装はしない）。

文字列の中の `【要確認】` / `【要確認: 何を確かめるか】`（コロンは全角・半角どちらも可）は、根拠が無い箇所の目印。
人が見落とさないよう、ビルドの最後（出力の直前）にマーカーの部分だけを目立たせる:
  - HTML: 出力する HTML のテキストノードの中のマーカーを `<mark class="todo">…</mark>` で包む。
          属性値・`<title>`・`<script>`・`<style>`・コード枠（`<pre>` / `<code>`）・SVG の `<title>` / `<desc>` の中は対象外。
          SVG の `<text>` の中は `<tspan class="todo" fill=… font-weight="700">` にする（`<mark>` は SVG で使えない）。
  - PPTX: 保存の直前に全スライドの全 run（表のセル・グループ内の図形・canvas 経由の文字も同じ）を走査し、
          マーカーを含む run を分割して、マーカー部分に文字色＋太字を付ける（PPTX の run には塗りが無い）。
          文字が明るい（暗い地の上）run には `todo_color_on_dark`、それ以外には `todo_color` を使う。
          コード用フォントの run は対象外。
  - 一覧: `scan_deck()` がスライド番号つきで数える（ビルドの note に使う）。`meta.todo_marks: false` で強調を切れる（一覧は出す）。
色は layout の `todo_color`（明るい地の上）/ `todo_color_on_dark`（暗い地の上）/ `todo_bg`（HTML の下地）。
"""

from __future__ import annotations

import copy
import re

# lint_deck_text.TODO_MARK と同じ形（ここに置くのは、build_deck → lint の依存を作らないため）
TODO_MARK = re.compile(r"【要確認(?:\s*[:：]\s*([^】]*))?】")

DEFAULT_COLORS = {"todo_color": "#9A3412", "todo_color_on_dark": "#FCD34D", "todo_bg": "#FEF3C7"}
# 一覧に出さない・数えないキー（スタイル指定・パス・ID など。notes は PPTX に出ないので数えない）
SCAN_SKIP_KEYS = frozenset({"style", "path", "src", "image", "id", "type", "layout", "theme", "notes", "code", "icon"})


def colors(layout: dict | None) -> dict:
    """layout の todo_color 系（無ければ既定）。"""
    out = dict(DEFAULT_COLORS)
    for k in out:
        v = (layout or {}).get(k)
        if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v.strip()):
            out[k] = v.strip().upper()
    return out


def enabled(deck: dict) -> bool:
    meta = deck.get("meta") if isinstance(deck.get("meta"), dict) else {}
    return meta.get("todo_marks", True) is not False


# ---------------------------------------------------------------------------
# 一覧
# ---------------------------------------------------------------------------

def scan_deck(deck: dict) -> list:
    """スライド上に出る文字列の中のマーカーを [{slide: 番号(1 始まり), text: マーカー全体, what: 何を確かめるか}] で返す。
    スライドの外（meta）と notes・code・スタイル指定、未知のキー（表示されない値）の中は数えない。内部キー（_ で始まる）も見ない。"""
    found = []

    def walk(obj, n):
        if isinstance(obj, str):
            for m in TODO_MARK.finditer(obj):
                found.append({"slide": n, "text": m.group(0), "what": (m.group(1) or "").strip()})
        elif isinstance(obj, list):
            for v in obj:
                walk(v, n)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and (k in SCAN_SKIP_KEYS or k.startswith("_")):
                    continue
                walk(v, n)

    try:
        import deck_schema
    except Exception:       # pragma: no cover  （スキーマ表を読めなくても一覧は出す）
        deck_schema = None
    for i, s in enumerate(deck.get("slides") or [], 1):
        # 未知のキー（警告が出て、画面には出ない値）は数えない。数えると note の件数と画面の強調数が食い違う
        known = None
        if deck_schema is not None and isinstance(s, dict):
            try:
                known = deck_schema.known_slide_keys(s.get("type"))
            except Exception:       # pragma: no cover
                known = None
        if known is not None and isinstance(s, dict):
            s = {k: v for k, v in s.items() if not (isinstance(k, str) and not k.startswith("_") and k not in known)}
        walk(s, i)
    return found


def summary_note(found: list, limit: int = 6) -> str | None:
    """ビルドの note の文面。無ければ None。"""
    if not found:
        return None
    per = {}
    for f in found:
        per.setdefault(f["slide"], []).append(f)
    parts = []
    for n, fs in list(per.items())[:limit]:
        whats = [f["what"] for f in fs if f["what"]]
        label = f"{n} 枚目 {len(fs)} 件"
        if whats:
            label += "（" + whats[0][:24] + ("…" if len(whats[0]) > 24 else "") + ("ほか" if len(whats) > 1 else "") + "）"
        parts.append(label)
    more = f"、ほか {len(per) - limit} 枚" if len(per) > limit else ""
    return (f"要確認が {len(found)} 件あります（{'、'.join(parts)}{more}）"
            "→ 根拠を確かめて文を確定し、マーカーを消す")


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"(<!--.*?-->|<[^>]*>)", re.S)
_TAG_NAME = re.compile(r"^<\s*(/?)\s*([A-Za-z][A-Za-z0-9:-]*)")
_SKIP_TAGS = {"title", "script", "style", "pre", "code", "textarea", "desc"}
# エンジンが挿入する行の区切り（<br>・canvas の行ごとの <p>・span）。マーカーがこの間で割れても、続きを同じマーカーとして扱う
_BRIDGE_TAGS = {"br", "span", "p", "b", "i", "em", "strong", "u", "wbr"}


def html_mark(doc: str, layout: dict | None = None) -> str:
    """HTML 断片（スライド本体）の中のテキストノードのマーカーを強調する。マーカーが無ければそのまま返す。
    折り返しの改行（<br>・canvas の行ごとの <p>）でマーカーが割れているときは、行ごとに分けて強調する（各行に <mark>）。"""
    if "【" not in doc:
        return doc
    c = colors(layout)
    mark_open = '<mark class="todo">'
    tspan_open = f'<tspan class="todo" fill="{c["todo_color"]}" font-weight="700">'
    parts = [p for p in _TOKEN.split(doc) if p]
    # 1) 部品を走査して、強調の対象になるテキストノードを集める。bridge: 直前の対象ノードと <br> / 行の <p> だけを挟んで続いているか
    nodes = []          # {i: parts の添字, svg: SVG の <text> の中か, bridge: bool}
    skip = 0
    svg_text = 0
    gap_ok = False      # 前の対象ノードから今まで、橋渡しできるタグだけだったか
    for idx, part in enumerate(parts):
        if part.startswith("<"):
            m = _TAG_NAME.match(part)
            if m and not part.startswith("<!--"):
                closing, name = m.group(1) == "/", m.group(2).lower()
                selfclose = part.rstrip().endswith("/>")
                if name in _SKIP_TAGS:
                    skip = max(0, skip - 1) if closing else skip + (0 if selfclose else 1)
                    gap_ok = False
                elif name == "text":
                    svg_text = max(0, svg_text - 1) if closing else svg_text + (0 if selfclose else 1)
                    gap_ok = False
                elif name not in _BRIDGE_TAGS:
                    gap_ok = False
            else:
                gap_ok = False
            continue
        if skip:
            gap_ok = False
            continue
        nodes.append({"i": idx, "svg": bool(svg_text), "bridge": gap_ok and nodes and not svg_text and not nodes[-1]["svg"]})
        gap_ok = True
    # 2) 橋渡しでつながったノードを 1 本の文字列にして、マーカーを探す（ノードをまたぐ一致は各ノードの該当部分に分ける）
    ranges = {}         # parts の添字 → [(開始, 終了)]
    k = 0
    while k < len(nodes):
        j = k + 1
        while j < len(nodes) and nodes[j]["bridge"]:
            j += 1
        chain = nodes[k:j]
        texts = [parts[n["i"]] for n in chain]
        if "【" in "".join(texts):
            joined = "".join(texts)
            offs = [0]
            for t in texts:
                offs.append(offs[-1] + len(t))
            for m in TODO_MARK.finditer(joined):
                for n, t0, t1 in zip(chain, offs, offs[1:]):
                    a, b = max(m.start(), t0), min(m.end(), t1)
                    if a < b:
                        ranges.setdefault(n["i"], []).append((a - t0, b - t0))
        k = j
    # 3) 該当部分を <mark>（SVG の <text> の中は <tspan>）で包む
    svg_idx = {n["i"] for n in nodes if n["svg"]}
    for idx, rs in ranges.items():
        text = parts[idx]
        wrap, close = (tspan_open, "</tspan>") if idx in svg_idx else (mark_open, "</mark>")
        out, pos = [], 0
        for a, b in rs:
            if not text[a:b].strip():
                continue
            out.append(text[pos:a] + wrap + text[a:b] + close)
            pos = b
        out.append(text[pos:])
        parts[idx] = "".join(out)
    return "".join(parts)


def html_css(layout: dict | None = None) -> str:
    """<mark class="todo"> の CSS（スタイルシートに足す）。"""
    c = colors(layout)
    return (f"mark.todo {{ background: {c['todo_bg']}; color: {c['todo_color']}; font-weight: 700; "
            "border-radius: 3px; padding: 0 .12em; -webkit-box-decoration-break: clone; box-decoration-break: clone; }")


# ---------------------------------------------------------------------------
# PPTX
# ---------------------------------------------------------------------------

def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def pptx_mark(prs, layout: dict | None = None, code_font: str | None = None) -> int:
    """全スライドの全段落を走査して、マーカー部分を文字色＋太字にする（run を分割する）。分割したマーカーの数を返す。
    折り返しの改行（a:br・行ごとの段落）や run の境目でマーカーが割れているときは、同じ図形・セルの中で続きを探し、各 run の断片に色と太字を付ける。"""
    from pptx.oxml.ns import qn
    c = colors(layout)
    count = 0
    for slide in prs.slides:
        # 同じ txBody（図形・表のセル）の段落をまとめて 1 本の文字列にする。エンジンが行ごとに段落を分けても、マーカーを探せるように
        owners = []
        for p in slide._element.iter(qn("a:p")):
            par = p.getparent()
            if not any(par is o for o in owners):
                owners.append(par)
        for par in owners:
            chain = []          # 直下の段落の a:r（コード用フォントの run は除く）
            for p in par.findall(qn("a:p")):
                for r in p.findall(qn("a:r")):
                    t = r.find(qn("a:t"))
                    if t is None or t.text is None:
                        continue
                    rpr = r.find(qn("a:rPr"))
                    if code_font and rpr is not None:
                        latin = rpr.find(qn("a:latin"))
                        if latin is not None and latin.get("typeface") == code_font:
                            continue
                    chain.append(r)
            if not chain:
                continue
            joined = "".join(r.find(qn("a:t")).text for r in chain)
            if "【" not in joined:
                continue
            matches = [(m.start(), m.end()) for m in TODO_MARK.finditer(joined)]
            if not matches:
                continue
            count += len(matches)
            pos = 0
            for r in chain:
                t = r.find(qn("a:t"))
                n = len(t.text)
                rs = [(max(a, pos) - pos, min(b, pos + n) - pos) for a, b in matches if max(a, pos) < min(b, pos + n)]
                pos += n
                if rs:
                    _split_run(r, t, r.find(qn("a:rPr")), c, rs)
    return count


def _run_is_light(rpr) -> bool:
    """run の文字色が明るい（= 暗い地の上に載っている）か。"""
    from pptx.oxml.ns import qn
    if rpr is None:
        return False
    fill = rpr.find(qn("a:solidFill"))
    if fill is None:
        return False
    clr = fill.find(qn("a:srgbClr"))
    if clr is None or not re.fullmatch(r"[0-9A-Fa-f]{6}", clr.get("val") or ""):
        return False
    return _lum(clr.get("val")) > 0.45


def _split_run(r, t, rpr, c, ranges) -> None:
    """run を ranges（[(開始, 終了)] = マーカーの部分）で分割し、マーカーの部分に色と太字を付ける。"""
    from pptx.oxml.ns import qn
    text = t.text
    pieces = []     # (文字列, マーカーか)
    pos = 0
    for a, b in ranges:
        if a > pos:
            pieces.append((text[pos:a], False))
        pieces.append((text[a:b], True))
        pos = b
    if pos < len(text):
        pieces.append((text[pos:], False))
    light = _run_is_light(rpr)
    color = (c["todo_color_on_dark"] if light else c["todo_color"]).lstrip("#")
    parent = r.getparent()
    idx = parent.index(r)
    for k, (s, mk) in enumerate(pieces):
        nr = copy.deepcopy(r)
        nr.find(qn("a:t")).text = s
        if mk:
            _paint(nr, color)
        parent.insert(idx + k, nr)
    parent.remove(r)


def _paint(r, color: str):
    """run に文字色と太字を付ける（rPr の子の順序 ln → fill → effect … → latin を守る）。"""
    from pptx.oxml.ns import qn
    from lxml import etree
    rpr = r.find(qn("a:rPr"))
    if rpr is None:
        rpr = etree.SubElement(r, qn("a:rPr"))
        r.remove(rpr)
        r.insert(0, rpr)
    rpr.set("b", "1")
    for old in rpr.findall(qn("a:solidFill")):
        rpr.remove(old)
    for tag in ("a:gradFill", "a:noFill", "a:pattFill", "a:blipFill", "a:grpFill"):
        for old in rpr.findall(qn(tag)):
            rpr.remove(old)
    fill = etree.Element(qn("a:solidFill"))
    clr = etree.SubElement(fill, qn("a:srgbClr"))
    clr.set("val", color)
    # fill は ln の後、effectLst / highlight / latin などの前
    pos = 0
    for i, ch in enumerate(list(rpr)):
        if ch.tag == qn("a:ln"):
            pos = i + 1
    rpr.insert(pos, fill)

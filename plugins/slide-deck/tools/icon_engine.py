#!/usr/bin/env python3
"""同梱アイコン（templates/icons/icons.json）の意味検索と、canvas 要素への変換。

アイコンは Tabler Icons（MIT）の outline から定番の約70点だけを同梱している。各アイコンに
日本語・英語の概念語を付けてあり、スライドの `icon` には次のどれかを書ける:
  - アイコン名（例 "shield-check"）
  - 概念語（例 "セキュリティ" / "q:統制 安全"）→ 最も近いアイコンを選ぶ（似た概念は同じ絵を使い回す）
描画は線だけの自由曲線（canvas の custom）なので、PowerPoint でも色・太さを変えられるネイティブ図形になる。

使い方（一覧・検索）:
  python tools/icon_engine.py "セキュリティ 統制"     # 上位の候補
  python tools/icon_engine.py --list                  # 全アイコン名と概念語
  python tools/icon_engine.py --sheet icons.png       # 一覧画像（要 pillow）
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

ICON_FILE = Path(__file__).resolve().parent.parent / "templates" / "icons" / "icons.json"


@lru_cache(maxsize=1)
def load() -> dict:
    try:
        return json.loads(ICON_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"icons": {}, "viewbox": 24, "stroke_width": 2}


def _bigrams(s: str) -> set:
    s = s.lower()
    return {s[k:k + 2] for k in range(len(s) - 1)}


def search(query: str, top: int = 5) -> list:
    """概念語で検索し、(スコア, アイコン名) を高い順に返す。"""
    icons = load().get("icons", {})
    q = str(query or "").strip()
    if q.startswith("q:"):
        q = q[2:]
    toks = [t.lower() for t in q.replace("　", " ").replace("・", " ").replace("、", " ").split() if t]
    scored = []
    for name, meta in icons.items():
        tags = [t.lower() for t in meta.get("ja", []) + meta.get("en", [])]
        score = 0.0
        for t in toks:
            if t == name:
                score += 10
            elif t in tags:
                score += 3
            elif len(t) >= 2 and any(t in g or (len(g) >= 2 and g in t) for g in tags):
                score += 2
            else:
                bg = _bigrams(t)
                if bg:
                    best = max((len(bg & _bigrams(g)) / len(bg) for g in tags), default=0)
                    if best >= 0.5:
                        score += best
        if score:
            scored.append((round(score, 2), name))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[:top]


def resolve(spec) -> str | None:
    """`icon` の指定（名前 / 概念語 / q:概念語）からアイコン名を決める。見つからなければ None。"""
    if not spec or not isinstance(spec, str):
        return None
    icons = load().get("icons", {})
    s = spec.strip()
    if s in icons:
        return s
    hit = search(s, 1)
    return hit[0][1] if hit else None


def element(spec, x: float, y: float, size: float, color: str, name: str | None = None) -> dict | None:
    """アイコンを canvas の custom 要素（線だけの自由曲線）にする。color は #RRGGBB。"""
    icon = resolve(spec)
    if not icon:
        return None
    data = load()
    vb = data.get("viewbox", 24)
    k = size / vb
    paths = [{"cmds": [[c[0]] + [round(v * k, 2) for v in c[1:]] for c in p], "fill": False, "stroke": True}
             for p in data["icons"][icon]["paths"]]
    return {"kind": "shape", "geom": "custom", "x": round(x, 2), "y": round(y, 2), "w": round(size, 2),
            "h": round(size, 2), "line": {"color": color, "width": round(data.get("stroke_width", 2) * k, 2),
                                         "cap": "rnd"},
            "path": paths, "name": name or f"アイコン:{icon}"}


def _sheet(out: Path):
    from PIL import Image, ImageDraw
    icons = load()["icons"]
    names = sorted(icons)
    cols, cell = 8, 150
    rows = (len(names) + cols - 1) // cols
    im = Image.new("RGB", (cols * cell, rows * cell), "white")
    dr = ImageDraw.Draw(im)
    for i, nm in enumerate(names):
        ox, oy = (i % cols) * cell + 35, (i // cols) * cell + 15
        k = 80 / 24
        for p in icons[nm]["paths"]:
            cur, start = None, None
            for c in p:
                if c[0] == "M":
                    cur = start = (c[1], c[2])
                elif c[0] == "L":
                    dr.line([(ox + cur[0] * k, oy + cur[1] * k), (ox + c[1] * k, oy + c[2] * k)], fill="black", width=4)
                    cur = (c[1], c[2])
                elif c[0] in ("C", "Q"):
                    pts = [cur] + [(c[j], c[j + 1]) for j in range(1, len(c), 2)]
                    seg = []
                    for s in range(11):
                        t = s / 10
                        if c[0] == "C":
                            bx = sum(coef * pt[0] for coef, pt in zip(((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3), pts))
                            by = sum(coef * pt[1] for coef, pt in zip(((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3), pts))
                        else:
                            bx = sum(coef * pt[0] for coef, pt in zip(((1 - t) ** 2, 2 * (1 - t) * t, t * t), pts))
                            by = sum(coef * pt[1] for coef, pt in zip(((1 - t) ** 2, 2 * (1 - t) * t, t * t), pts))
                        seg.append((ox + bx * k, oy + by * k))
                    dr.line(seg, fill="black", width=4)
                    cur = pts[-1]
                elif c[0] == "Z" and cur and start:
                    dr.line([(ox + cur[0] * k, oy + cur[1] * k), (ox + start[0] * k, oy + start[1] * k)], fill="black", width=4)
                    cur = start
        dr.text(((i % cols) * cell + 6, (i // cols) * cell + 120), nm, fill="black")
    im.save(out)


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="同梱アイコンの検索・一覧")
    ap.add_argument("query", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sheet", help="一覧画像の出力先（PNG、要 pillow）")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    data = load()
    if a.list:
        for nm, meta in sorted(data["icons"].items()):
            print(f"{nm:20s} {' '.join(meta['ja'])} / {' '.join(meta['en'])}")
    if a.sheet:
        _sheet(Path(a.sheet))
        print(f"sheet: {a.sheet}")
    if a.query:
        hits = search(a.query, a.top)
        if not hits:
            print("該当なし（--list で一覧を確認し、近い概念語かアイコン名を指定してください）")
        for sc, nm in hits:
            meta = data["icons"][nm]
            print(f"{sc:5.1f}  {nm:20s} {' '.join(meta['ja'])}")
    print(f"（{data.get('source', '')} / {data.get('license', '')}）", file=sys.stderr)


if __name__ == "__main__":
    main()

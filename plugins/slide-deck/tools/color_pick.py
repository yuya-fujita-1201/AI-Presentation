#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文字色の選び方（「地の色に対して、読める文字色」を 1 か所にまとめる）。

方針: 色の組み合わせを各所で直書きしない。「この地の上にこの文字色を置きたい」と書いたら、対比（WCAG）が足りないときだけ、
同じ色味のまま白または黒の側へ寄せて 4.5:1 を満たす色にする（足りていれば元の色のまま）。
利用者が明示した色は呼び出し側が触らない（このモジュールは色の計算だけ）。
"""

from __future__ import annotations

MIN_RATIO = 4.5


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    """hex a・b を (1-t):t で線形混合する。"""
    ra, ga, ba = hex_to_rgb(a)
    rb, gb, bb = hex_to_rgb(b)
    return rgb_to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def luminance(h: str) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(color: str, bg: str, min_ratio: float = MIN_RATIO) -> str:
    """color を bg の上で min_ratio 以上にする。足りていればそのまま。足りなければ bg が暗いなら白へ、明るいなら黒へ 0.1 刻みで寄せる。"""
    if contrast(color, bg) >= min_ratio:
        return color
    toward = "#FFFFFF" if luminance(bg) < 0.5 else "#000000"
    for i in range(1, 11):
        cand = mix(color, toward, i / 10)
        if contrast(cand, bg) >= min_ratio:
            return cand
    return toward


def readable_on_all(color: str, bgs, min_ratio: float = MIN_RATIO) -> str:
    """複数の地（例: 通常行の地と強調行の地）の全部の上で読める色。地の明暗が割れて両立しないときは、最初の地を優先する。"""
    bgs = [b for b in bgs if b]
    if not bgs:
        return color
    if all(contrast(color, b) >= min_ratio for b in bgs):
        return color
    # 暗い側へ寄せて全部を満たせるか → だめなら明るい側 → だめなら最初の地だけ満たす
    for toward in ("#000000", "#FFFFFF"):
        for i in range(1, 11):
            cand = mix(color, toward, i / 10)
            if all(contrast(cand, b) >= min_ratio for b in bgs):
                return cand
    return readable_on(color, bgs[0], min_ratio)

# -*- coding: utf-8 -*-
"""主役のあるページ（S2d）の純粋な部分: 背景（画像＋覆い／色面）と文字色の自動選択・variant・split のパネル・cards の強弱。

デッキの中に抑揚（主役のページ）を作るための部品。build_deck を import しない（標準ライブラリと Pillow・ja_text・autofit・
proposal_engine・canvas_engine だけ）。描くのは canvas 要素（HTML と PPTX が同じ要素列から描く）。

  背景          {"image": "assets/x.jpg", "overlay": "primary", "opacity": 0.6, "position": "center"} / {"fill": "primary"} / "assets/x.jpg"
                画像は cover で敷き、テーマ色の半透明の覆いを重ねる。文字色は覆いの上の対比（4.5:1 以上）で自動で選ぶ。
  variant       title / section / closing / statement / quote / image の見た目の型。値は layout JSON の `variants` が持つ
  split         非対称分割（端まで届く色面か画像のパネル＋残りの本文領域）
  cards の強弱  emphasis（true / "accent" / "soft"）と span（占める列数）

見た目の数値は `templates/layouts/default.json`（`variants` `palettes` `types.split` `types.cards.grid.emph_*`）が持ち、
ここは st（解決済みの領域の値）から読むだけで、数値を直書きしない（対比の基準 4.5:1・覆いの探索範囲・画像の標本数だけ定数）。
"""
from __future__ import annotations

import copy
import difflib
import math
import re

import ja_text

CANVAS_W, CANVAS_H = 1280, 720

# 背景（background）を持てるタイプ。split は panel が背景の役をする
BG_TYPES = ("title", "section", "closing", "quote", "statement")
# 画像の上の文字の対比（WCAG AA）。大きい文字でも 4.5 を求める（仕様: 画像や色面の上の文字は必ず 4.5:1 以上）
CONTRAST_MIN = 4.5
# 覆いの濃さ: 既定は開始値から必要なだけ上げる。上限を超えても足りなければ警告
OVERLAY_START, OVERLAY_MAX, OVERLAY_STEP = 0.55, 0.94, 0.01
SAMPLE_W, SAMPLE_H = 96, 54            # 対比の見積もりに使う画像の標本の大きさ
BG_KEYS = ("image", "fill", "overlay", "opacity", "position")
POSITION_WORDS = {"center": (0.5, 0.5), "top": (0.5, 0.0), "bottom": (0.5, 1.0), "left": (0.0, 0.5), "right": (1.0, 0.5),
                  "top left": (0.0, 0.0), "top right": (1.0, 0.0), "bottom left": (0.0, 1.0), "bottom right": (1.0, 1.0)}
SPLIT_SIDES = ("left", "right")
SPLIT_RATIO = (0.25, 0.6)
SPLIT_PANEL_KEYS = ("fill", "image", "overlay", "opacity", "position", "eyebrow", "title", "text", "kpi", "items")
SPLIT_KPI_KEYS = ("value", "label", "unit")
SPLIT_ITEMS_MAX = 3
CARD_EMPHASIS = (True, "accent", "soft")
CARD_EMPHASIS_MAX = 2
IMAGE_FITS = ("contain", "bleed")
CAPTION_POSITIONS = ("below", "band")

_HEX = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


# ---------------------------------------------------------------------------
# 色の計算
# ---------------------------------------------------------------------------

def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02X}" for v in rgb)


def luminance(rgb) -> float:
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b) -> float:
    """2 色（RGB のタプル）のコントラスト比（WCAG）。"""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mix(under, over, alpha: float) -> tuple:
    return tuple(under[i] * (1 - alpha) + over[i] * alpha for i in range(3))


def color_rgb(colors: dict, token, default="#000000") -> tuple:
    """テーマ色トークン名か #hex → RGB。"""
    if isinstance(token, str) and token in colors:
        token = colors[token]
    if not (isinstance(token, str) and _HEX.match(token)):
        token = default
    return hex_to_rgb(token)


def color_hex(colors: dict, token, default="#000000") -> str:
    return rgb_to_hex(color_rgb(colors, token, default))


def is_color(colors: dict, v) -> bool:
    return isinstance(v, str) and (v in colors or bool(_HEX.match(v)))


# ---------------------------------------------------------------------------
# 背景: 正規化・検証
# ---------------------------------------------------------------------------

def parse_position(v):
    """position（center / top / bottom left / "30% 70%"）→ (x, y) 各 0〜1。解釈できなければ None。"""
    if v is None:
        return (0.5, 0.5)
    if not isinstance(v, str):
        return None
    s = " ".join(v.lower().split())
    if s in POSITION_WORDS:
        return POSITION_WORDS[s]
    words = s.split()
    if len(words) == 2 and words[0] in ("left", "right") and words[1] in ("top", "bottom"):
        s = f"{words[1]} {words[0]}"
        if s in POSITION_WORDS:
            return POSITION_WORDS[s]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%", s)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        if 0 <= x <= 100 and 0 <= y <= 100:
            return (x / 100.0, y / 100.0)
    return None


def validate_background(bg, where: str, colors: dict, deck_dir, fail, warn, image_check=None) -> dict | None:
    """background（または split.panel の背景キー）の検査と正規化 → 辞書 or None（指定なし）。
    where は「3枚目（type=title）: background」のような場所の表記。image_check(rel) -> 問題文 or None で画像のパスを調べる。"""
    if bg is None:
        return None
    if isinstance(bg, str):
        if not bg.strip():
            fail(f"{where} が空文字です → 画像のパス（\"assets/x.jpg\"）か {{\"fill\": \"primary\"}} を書く（背景を使わないなら消す）")
        bg = {"image": bg.strip()}
    if not isinstance(bg, dict):
        fail(f"{where} は {{\"image\": \"assets/x.jpg\", \"overlay\": \"primary\", \"opacity\": 0.6}} か {{\"fill\": \"primary\"}}、"
             f"または画像のパス（文字列）で指定してください（{type(bg).__name__} が書かれています）")
    for k in bg:
        if k not in BG_KEYS and isinstance(k, str) and not k.startswith("_"):
            if k in SPLIT_PANEL_KEYS:
                continue
            m = difflib.get_close_matches(k, BG_KEYS, n=1, cutoff=0.6)
            warn(f"{where} の \"{k}\" は無視されます{'（もしかして \"' + m[0] + '\"）' if m else ''}"
                 f" → 使えるキー: {' / '.join(BG_KEYS)}")
    out = {k: bg[k] for k in BG_KEYS if k in bg}
    img, fill = out.get("image"), out.get("fill")
    if img is None and fill is None:
        fail(f"{where} に image も fill もありません → \"background\": {{\"image\": \"assets/x.jpg\"}} か {{\"fill\": \"primary\"}} のように書く")
    if img is not None:
        if not isinstance(img, str) or not img.strip():
            fail(f"{where}.image は画像のパス（文字列。例: assets/x.jpg）で指定してください")
        prob = image_check(img) if image_check else None
        if prob:
            fail(f"{where}.image: {prob}")
        if fill is not None:
            warn(f"{where}: image と fill を両方書いています。fill は使いません（画像の覆いの色は overlay で指定します）"
                 f" → 色面だけにするなら image を消す")
            out.pop("fill")
            fill = None
    if fill is not None and not is_color(colors, fill):
        fail(f"{where}.fill '{fill}' がテーマの色トークンでも #RRGGBB でもありません（トークン: {', '.join(sorted(colors))}）")
    ov = out.get("overlay")
    if ov is not None:
        if fill is not None:
            warn(f"{where}: overlay は画像の背景だけで使います（色面には無視されます）")
            out.pop("overlay")
        elif ov != "none" and not is_color(colors, ov):
            fail(f"{where}.overlay '{ov}' がテーマの色トークンでも #RRGGBB でもありません"
                 f" → \"primary\" のようなテーマ色か、覆いを使わないなら \"none\"")
    op = out.get("opacity")
    if op is not None:
        if isinstance(op, bool) or not isinstance(op, (int, float)) or not (0 <= op <= 1) or op != op:
            fail(f"{where}.opacity は 0〜1 の数値で指定してください（{op!r}）→ 0.6 のように（省略すると文字の対比が足りる濃さを自動で選ぶ）")
        if fill is not None:
            warn(f"{where}: opacity は画像の背景だけで使います（色面には無視されます）")
            out.pop("opacity")
    if "position" in out and parse_position(out["position"]) is None:
        fail(f"{where}.position '{out['position']}' を解釈できません → center / top / bottom / left / right / top left … か \"30% 70%\" の形で書く")
    if "position" in out and fill is not None:
        warn(f"{where}: position は画像の背景だけで使います（色面には無視されます）")
        out.pop("position")
    return out


# ---------------------------------------------------------------------------
# 背景: 画像の標本と、覆いの濃さ・文字色の自動選択
# ---------------------------------------------------------------------------

_STAT_CACHE: dict = {}


def image_samples(path, rect_w: float, rect_h: float, position=(0.5, 0.5)):
    """画像を矩形に cover で敷いたときの見え方を小さく標本にする → [(luminance, (r, g, b))] を明るさ順に。読めなければ None（SVG 等）。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    key = (str(path), round(rect_w), round(rect_h), position)
    try:
        mt = path.stat().st_mtime
    except OSError:
        return None
    hit = _STAT_CACHE.get(key)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            iw, ih = im.size
            k = max(rect_w / iw, rect_h / ih)
            vw, vh = rect_w / k, rect_h / k          # 画像のうち見える範囲（元画像の px）
            x0 = (iw - vw) * position[0]
            y0 = (ih - vh) * position[1]
            im = im.crop((int(x0), int(y0), int(math.ceil(x0 + vw)), int(math.ceil(y0 + vh)))).resize((SAMPLE_W, SAMPLE_H))
            px = list(im.getdata())
    except Exception:
        return None
    out = sorted(((luminance(p), p) for p in px), key=lambda t: t[0])
    _STAT_CACHE[key] = (mt, out)
    return out


def _band_mean(samples, lo: float, hi: float) -> tuple:
    n = len(samples)
    a, b = int(n * lo), max(int(n * hi), int(n * lo) + 1)
    seg = [s[1] for s in samples[a:b]] or [samples[-1][1]]
    return tuple(sum(p[i] for p in seg) / len(seg) for i in range(3))


def unfavorable(samples, mode: str) -> tuple:
    """文字にとって最悪の下地の色。明るい文字（mode=light）は画像の明るいところ、暗い文字（dark）は暗いところ。"""
    if mode == "light":
        return _band_mean(samples, 0.90, 0.97)
    return _band_mean(samples, 0.03, 0.10)


# 飾りの文字（大きな引用符）の領域。対比の基準に入れない（check_layout も記号 1 文字は文字として測らない）
DECORATIVE_REGIONS = ("mark",)


TEXT_COLOR_KEYS = ("color", "child_color", "title_color", "text_color", "eyebrow_color", "kpi_color", "label_color",
                   "items_color", "note_color")


def palette_colors(palettes_for_type: dict, mode: str, only=None) -> list:
    """palettes.<type>.<mode> の文字色のトークン（重複なし・順序保持）を集める。only=領域名のリストなら、その領域だけ。"""
    layer = (palettes_for_type or {}).get(mode) or {}
    out = []
    for region, props in layer.items():
        if only is not None and region not in only:
            continue
        if region in DECORATIVE_REGIONS or not isinstance(props, dict):
            continue
        for k, v in props.items():
            if k in TEXT_COLOR_KEYS and isinstance(v, str) and v not in out:
                out.append(v)
    return out


def _evaluate(tokens: list, colors: dict, eff, fallbacks: list) -> tuple:
    """文字色（トークン）を下地 eff の上で評価する → (最悪の対比, 置き換え {トークン: 代わりのトークン})。
    基準に届かない色は、fallbacks（layout の palettes._fallback.<mode>。on_primary など）のうち届くものに置き換える（届くものが無ければそのまま）。"""
    worst, subst = None, {}
    for tok in tokens:
        k = contrast(color_rgb(colors, tok), eff)
        if k < CONTRAST_MIN - 0.01:
            for fb in fallbacks:
                kk = contrast(color_rgb(colors, fb), eff)
                if kk >= CONTRAST_MIN - 0.01:
                    subst[tok], k = fb, kk
                    break
        worst = k if worst is None else min(worst, k)
    return (worst if worst is not None else 99.0), subst


def solve_background(bg: dict, colors: dict, rect, deck_dir, palettes_for_type: dict, only_regions=None, fallbacks=None) -> dict:
    """背景の覆いの濃さ・文字色モードを決める。bg は validate_background の戻り値（正規化済み）。
    戻り値: {image, fill, overlay（hex or None）, opacity, position, mode（light=明るい文字 / dark=暗い文字）, qa_bg（hex or None）,
             ratio（文字色の最悪の対比）, ok, auto（opacity を自動で選んだか）, texts（検査した文字色）, subst（対比が足りず置き換えた文字色）, suggest}
    fallbacks: {"light": [トークン…], "dark": […]}（文字色が届かないときの代わり。layout の palettes._fallback）"""
    fallbacks = fallbacks or {}
    pos = parse_position(bg.get("position")) or (0.5, 0.5)
    res = {"image": bg.get("image"), "fill": bg.get("fill"), "position": bg.get("position") or "center", "overlay": None,
           "opacity": None, "mode": "light", "qa_bg": None, "ratio": None, "ok": True, "auto": False, "texts": [], "subst": {},
           "suggest": None}
    cand = {m: palette_colors(palettes_for_type, m, only_regions) for m in ("light", "dark")}
    if bg.get("fill") is not None and bg.get("image") is None:
        base = color_rgb(colors, bg["fill"])
        res["fill_rgb"] = base
        best = None
        for mode in ("light", "dark"):
            if not cand[mode]:
                continue
            worst, subst = _evaluate(cand[mode], colors, base, fallbacks.get(mode, []))
            if best is None or worst > best[1] + 1e-9:
                best = (mode, worst, subst)
        if best is None:
            res["mode"] = "light" if luminance(base) < 0.4 else "dark"
        else:
            res.update(mode=best[0], ratio=round(best[1], 2), ok=best[1] >= CONTRAST_MIN - 0.01, subst=best[2])
        res["texts"] = [color_hex(colors, c) for c in cand[res["mode"]]]
        return res

    # 画像 + 覆い
    ov_tok = bg.get("overlay", "primary")
    has_overlay = ov_tok != "none" and bg.get("opacity", 1) != 0
    if not (cand["light"] or cand["dark"]) and "overlay" not in bg and bg.get("opacity") is None:
        has_overlay = False          # 画像の上に文字が無い（variant の panel など）なら、覆いは書かれたときだけ
    ov_rgb = color_rgb(colors, ov_tok if ov_tok != "none" else "primary")
    samples = None
    if deck_dir is not None and bg.get("image"):
        samples = image_samples(_resolve(deck_dir, bg["image"]), rect[2], rect[3], pos)
    if samples is None:
        samples = [(0.2, (128, 128, 128))]        # 読めない画像（SVG 等）は中間の明るさとして扱う
    res["overlay"] = rgb_to_hex(ov_rgb) if has_overlay else None
    user_op = bg.get("opacity")
    steps = ([float(user_op)] if user_op is not None else
             [round(OVERLAY_START + i * OVERLAY_STEP, 2) for i in range(int(round((OVERLAY_MAX - OVERLAY_START) / OVERLAY_STEP)) + 1)])
    if not has_overlay:
        steps = [0.0]
    # 覆いの色が暗ければ明るい文字から、明るければ暗い文字から試す
    order = ["light", "dark"] if luminance(ov_rgb) < 0.4 else ["dark", "light"]
    if not has_overlay:
        order = ["light", "dark"] if luminance(_band_mean(samples, 0.3, 0.7)) < 0.4 else ["dark", "light"]
    best = chosen = None
    for mode in order:
        if not cand[mode]:
            continue
        under = unfavorable(samples, mode)
        for a in steps:
            eff = mix(under, ov_rgb, a) if has_overlay else under
            worst, subst = _evaluate(cand[mode], colors, eff, fallbacks.get(mode, []))
            if best is None or worst > best[2] + 1e-9:
                best = (mode, a, worst, subst)
            if worst >= CONTRAST_MIN - 0.01:
                chosen = (mode, a, worst, subst)
                break
        if chosen:
            break
    pick = chosen or best
    if pick is None:
        res.update(mode=order[0], opacity=steps[0] if user_op is not None else OVERLAY_START)      # 文字色の候補が無い（palette が無いタイプ）
    else:
        res.update(mode=pick[0], opacity=pick[1], ratio=round(pick[2], 2), ok=bool(chosen), subst=pick[3])
        res["texts"] = [color_hex(colors, c) for c in cand[pick[0]]]
    res["auto"] = user_op is None and has_overlay
    if not res["ok"] and has_overlay and user_op is not None:
        # 足りないとき、同じ覆いの色で届く最小の濃さ（利用者が opacity を書いたときの直し方。覆いの色に合う文字色の側から探す）
        for mode in order:
            if not cand[mode]:
                continue
            under = unfavorable(samples, mode)
            hit = None
            for k in range(int(user_op * 100) + 1, 100):
                a = k / 100.0
                if _evaluate(cand[mode], colors, mix(under, ov_rgb, a), fallbacks.get(mode, []))[0] >= CONTRAST_MIN - 0.01:
                    hit = a
                    break
            if hit is not None:
                res["suggest"] = hit
                break
    if not has_overlay:
        res["opacity"] = 0.0
    # check_layout が画像の上の文字の対比を見られるよう、画像の「文字にとって最悪の色」を渡す
    res["qa_bg"] = rgb_to_hex(unfavorable(samples, res["mode"]))
    return res


def _resolve(deck_dir, rel):
    from pathlib import Path
    return Path(deck_dir) / rel


def background_problems(res: dict, bg: dict, where: str) -> list:
    """solve_background の結果から警告文を作る → [(level, 文)]。足りなければ具体的な直し方（覆いの濃さ・色）つき。"""
    out = []
    if res.get("ok", True) or res.get("ratio") is None:
        return out
    if res.get("image") is not None:
        if bg.get("overlay") == "none":
            fix = "overlay を \"none\" 以外（\"primary\" など）にして opacity を足す（覆いなしでは対比を確保できない）"
        elif res.get("suggest"):
            fix = f"opacity を {res['suggest']:g} 以上にする"
        else:
            fix = "覆いを濃く（暗い面の上の明るい文字なら primary より暗い色、明るい面の上の暗い文字なら background）して"
        out.append(("warn", f"{where}: 背景画像の上の文字の対比が {res['ratio']}:1 で、4.5:1 に届きません"
                            f"（覆い {bg.get('overlay', 'primary')}・濃さ {res['opacity']}）"
                            f" → {fix}、またはもっと明暗のはっきりしない（文字の下が均一な）画像に替える"))
    else:
        out.append(("warn", f"{where}: 色面 '{bg.get('fill')}' の上の文字の対比が {res['ratio']}:1 で、4.5:1 に届きません"
                            f" → 濃い色（primary など）か薄い色（background・surface）の面にする"))
    return out


# ---------------------------------------------------------------------------
# 背景の canvas 要素
# ---------------------------------------------------------------------------

def background_elements(res: dict, rect=(0, 0, CANVAS_W, CANVAS_H), colors=None, name="背景") -> list:
    """背景（解決済み）→ canvas 要素（HTML と PPTX が同じ列から描く）。画像は cover で敷き、覆いは半透明の矩形。"""
    x, y, w, h = rect
    if res.get("image"):
        els = [{"kind": "image", "path": res["image"], "x": x, "y": y, "w": w, "h": h, "fit": "cover",
                "position": res.get("position") or "center", "name": f"{name}画像", "alt": ""}]
        if res.get("qa_bg"):
            els[0]["qa_bg"] = res["qa_bg"]
        if res.get("overlay") and (res.get("opacity") or 0) > 0:
            els.append({"kind": "shape", "x": x, "y": y, "w": w, "h": h,
                        "fill": {"color": res["overlay"], "alpha": round(float(res["opacity"]), 3)}, "name": f"{name}の覆い"})
        return els
    fill = res.get("fill")
    if fill is not None and colors is not None:
        return [{"kind": "shape", "x": x, "y": y, "w": w, "h": h, "fill": color_hex(colors, fill), "name": name}]
    return []


# ---------------------------------------------------------------------------
# variant・palette・背景を st（領域の値）に反映する
# ---------------------------------------------------------------------------

def variant_names(layout: dict, t: str) -> list:
    return list(((layout.get("variants") or {}).get(t) or {}).keys())


def auto_variant(slide: dict) -> str | None:
    """利用者が variant を書かずに、別のキーで決まる variant（image の fit: bleed / caption_position: band、image_text の bleed: true）。"""
    t = slide.get("type")
    if t == "image":
        band = slide.get("caption_position") == "band" and bool(str(slide.get("caption") or "").strip())   # 帯は caption を入れるもの（無ければ空の帯になる）
        if slide.get("fit") == "bleed":
            return "bleed-band" if band else "bleed"
        if band:
            return "band"
    if t == "image_text" and slide.get("bleed") is True:
        return "bleed"
    return None


def variant_of(layout: dict, deck: dict, slide: dict) -> str | None:
    """このスライドの variant 名。slide.variant → meta.variants.<type> → shape の既定（layout.variant_defaults.<type>）。
    "default" は「何も付けない」（meta / shape の既定を打ち消す）。無い名前は無視して None。"""
    t = slide.get("type")
    names = variant_names(layout, t)
    auto = auto_variant(slide)
    if auto in names:
        return auto
    cands = (slide.get("variant"), ((deck.get("meta") or {}).get("variants") or {}).get(t) if isinstance((deck.get("meta") or {}).get("variants"), dict) else None,
             (layout.get("variant_defaults") or {}).get(t))
    for v in cands:
        if v is None:
            continue
        if v == "default":
            return None
        if v in names:
            return v
    return None


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def variant_layer(layout: dict, t: str, name: str | None) -> dict:
    """variant の領域の差分（palettes / on_bg などの制御キーを除く）。"""
    if not name:
        return {}
    v = ((layout.get("variants") or {}).get(t) or {}).get(name) or {}
    return {k: v[k] for k in v if k not in CONTROL_KEYS}


CONTROL_KEYS = ("palettes", "on_bg", "brand_on_bg", "label", "description")


def palettes_for(layout: dict, t: str, name: str | None) -> dict:
    """この type（と variant）の palettes: {light: {領域: {色…}}, dark: {…}}。variant の palettes が type の上に重なる。"""
    base = ((layout.get("palettes") or {}).get(t)) or {}
    v = (((layout.get("variants") or {}).get(t) or {}).get(name) or {}) if name else {}
    return deep_merge(base, v.get("palettes") or {})


def on_bg_regions(layout: dict, t: str, name: str | None, brand: bool = False, slide: dict | None = None):
    """palette を当てる領域の絞り込み（variant の on_bg）。None = 絞らない。
    variant が "brand_on_bg": true を持ち、meta.brand があるとき（brand = True）は、brand（右上のブランド名）も背景の上の文字として数える
    （title の bottom は文字が背景の外にあるが、brand だけは背景の画像の上に出る）。"""
    v = (((layout.get("variants") or {}).get(t) or {}).get(name) or {}) if name else {}
    ob = v.get("on_bg")
    if not isinstance(ob, list):
        return None
    ob = list(ob)
    if t == "image_text" and isinstance(slide, dict) and slide.get("image_side") == "left":
        brand = False        # 画像が左のとき、右上の brand は文字側（地は下地）にある
    if brand and v.get("brand_on_bg") and "brand" not in ob:
        ob.append("brand")
    return ob


def bg_rect_of(st: dict) -> tuple:
    """背景（画像・色面）を敷く矩形。variant が panel 領域を持てばその矩形、無ければ全面。"""
    p = st.get("panel")
    if isinstance(p, dict) and all(k in p for k in ("x", "y", "w", "h")):
        return (p["x"], p["y"], p["w"], p["h"])
    return (0, 0, CANVAS_W, CANVAS_H)


def grow_up_regions(st: dict, slide: dict) -> None:
    """variant の領域に "grow_up": true があれば、文字が増えても下端を動かさず、上へ広げる（left-band の帯の中の meta など。
    文字が枠の高さを超えると、4 行の meta が枠からはみ出していた）。明示の値（利用者の style）は、この後の層が上書きする。"""
    for name, r in st.items():
        if not (isinstance(r, dict) and r.get("grow_up") and all(k in r for k in ("y", "h", "w", "size"))):
            continue
        text = slide.get(name)
        if not isinstance(text, str) or not text:
            continue
        lines = ja_text.estimate_lines(text, r["size"], r["w"], None, bool(r.get("bold")))
        need = lines * r["size"] * r.get("line_height", 1.2) + 2
        if need > r["h"]:
            bottom = r["y"] + r["h"]
            r["h"] = int(need + 0.999)
            r["y"] = bottom - r["h"]


def fit_boxes_to_content(st: dict, info: dict, user_style) -> None:
    """variant の飾りの箱（deco*）に "fit_to": "<領域名>" があれば、その領域の中身（自動フィットが測った必要な高さ）に合わせて箱を低くする。
    箱は領域の縦の中心に置いたまま、高さ = 中身 + 上下の余白（fit_pad。既定 40）。元の高さより高くはしない。
    利用者が style.deco*.y / h を書いたときは動かさない。closing の contact（箱の下が空かない）が使う。"""
    for name in [k for k in st if isinstance(k, str) and k.startswith("deco")]:
        r = st[name]
        tgt = r.get("fit_to") if isinstance(r, dict) else None
        body = st.get(tgt) if isinstance(tgt, str) else None
        need = ((info or {}).get(tgt) or {}).get("need") if isinstance(tgt, str) else None
        if not (isinstance(body, dict) and _is_num(need) and all(k in r for k in ("y", "h")) and all(k in body for k in ("y", "h"))):
            continue
        usr = (user_style or {}).get(name) if isinstance(user_style, dict) else None
        if isinstance(usr, dict) and ("y" in usr or "h" in usr):
            continue
        h = min(r["h"], max(r.get("fit_min_h", 160), need + 2 * r.get("fit_pad", 40)))
        cy = r["y"] + r["h"] / 2                   # 箱の元の縦の中心に置く
        r["h"], r["y"] = round(h), round(cy - h / 2)
        if need < body["h"]:                         # 中身を箱の中央に置く（領域の上端から並べると箱の上に寄る）
            body["y"], body["h"] = round(cy - need / 2), int(need + 1.999)


def apply_style_layers(st: dict, layout: dict, deck: dict, slide: dict, t: str) -> dict:
    """variant と背景の palette を st に重ねる（resolve_style から、タイプ既定の直後・density / 利用者の指定の前に呼ぶ）。
    palette が当たるのは、背景（slide["_bg"]）があるときだけ。何も指定しなければ st は変わらない。"""
    name = variant_of(layout, deck, slide)
    if name:
        st = deep_merge(st, variant_layer(layout, t, name))
        grow_up_regions(st, slide)
    bg = slide.get("_bg") if isinstance(slide.get("_bg"), dict) else None
    if bg:
        pal = palettes_for(layout, t, name)
        only = on_bg_regions(layout, t, name, bool((deck.get("meta") or {}).get("brand")), slide)
        layer = (pal.get(bg.get("mode") or "light")) or {}
        if only is not None:
            layer = {r: v for r, v in layer.items() if r in only}
        layer = {r: v for r, v in layer.items() if r != "brand" or isinstance(st.get("brand"), dict)}   # brand はレイアウトに無ければ作らない
        subst = bg.get("subst") or {}
        if subst:       # 対比が足りない文字色（テーマによっては accent_on_primary など）は、届く色に置き換える
            layer = {r: ({k: subst.get(v, v) if k in TEXT_COLOR_KEYS and isinstance(v, str) else v for k, v in props.items()}
                         if isinstance(props, dict) else props) for r, props in layer.items()}
        st = deep_merge(st, layer)
        if bg.get("fill") is not None and bg.get("image") is None:
            if isinstance(st.get("panel"), dict):
                st["panel"]["fill"] = bg["fill"]
            else:
                for region in BG_REGION_NAMES:
                    if isinstance(st.get(region), dict):
                        st[region]["fill"] = bg["fill"]
                        break
    return st


# 下地の塗りを持つ領域の名前（section / closing は bg、statement は background）。色面の背景はここに反映する
BG_REGION_NAMES = ("bg", "background")


def needs_bg_element(st: dict, bg: dict | None) -> bool:
    """背景の要素（画像・覆い・色面）を別に描く必要があるか。色面で st.bg / st.panel の塗りに反映済みなら不要。"""
    if not bg:
        return False
    if bg.get("image") is not None:
        return True
    return not (isinstance(st.get("panel"), dict) or any(isinstance(st.get(r), dict) for r in BG_REGION_NAMES))


def hero_background_elements(st: dict, bg: dict | None, colors: dict) -> list:
    """全面系タイプ（title / section / closing / quote / statement / image）の背景の canvas 要素。無ければ []。"""
    if not needs_bg_element(st, bg):
        return []
    return background_elements(bg, bg_rect_of(st), colors)


DECO_NUM_LIMIT = 4 * CANVAS_W      # 飾りの座標・大きさの上限（これを超える値は PPTX で書き出せない）


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def deco_problems(style, where: str, colors: dict) -> list:
    """slide.style の飾りの領域（deco1 / deco2 …）の値の検査 → [(level, 文)]。型違い・範囲違いは fail（直し方つき）。"""
    out = []
    if not isinstance(style, dict):
        return out
    for name, r in style.items():
        if not (isinstance(name, str) and name.startswith("deco") and isinstance(r, dict)):
            continue
        here = f"{where}style.{name}"
        for k in ("x", "y", "w", "h"):
            if k in r and (not _is_num(r[k]) or abs(r[k]) > DECO_NUM_LIMIT):
                out.append(("fail", f"{here}.{k} は数値（px。{DECO_NUM_LIMIT} 以下）で指定してください（{r[k]!r}）→ 例: \"{k}\": 0"))
        if "alpha" in r and (not _is_num(r["alpha"]) or not (0 <= r["alpha"] <= 1)):
            out.append(("fail", f"{here}.alpha は 0〜1 の数値で指定してください（{r['alpha']!r}）→ 例: \"alpha\": 0.16（0 = 透明、1 = 不透明）"))
        if "radius" in r and (not _is_num(r["radius"]) or r["radius"] < 0 or r["radius"] > DECO_NUM_LIMIT):
            out.append(("fail", f"{here}.radius は 0 以上の数値（px）で指定してください（{r['radius']!r}）→ 例: \"radius\": 12"))
        if "geom" in r and r["geom"] not in ("ellipse", "rect"):
            out.append(("fail", f"{here}.geom は ellipse / rect のどちらかで指定してください（{r['geom']!r}）→ 円なら \"geom\": \"ellipse\""))
        if "fill" in r and r["fill"] is not None and not (isinstance(r["fill"], str) and is_color(colors, r["fill"])):
            out.append(("fail", f"{here}.fill はテーマの色トークンか #RRGGBB で指定してください（{r['fill']!r}）→ 例: \"fill\": \"accent\""))
    return out


DECO_PILL_MIN = 50       # 飾りの geom: ellipse に radius（形トークン radius.pill）が付いているとき、これ未満なら円にしない


def deco_elements(st: dict, colors: dict) -> list:
    """st の deco* 領域（variant の飾りの帯・箱。fill / alpha / radius）→ canvas 要素。HTML と PPTX が同じ列から描く。"""
    out = []
    for name in sorted(k for k in st if isinstance(k, str) and k.startswith("deco")):
        r = st[name]
        if not isinstance(r, dict) or not all(k in r for k in ("x", "y", "w", "h")) or not r.get("fill"):
            continue
        if not all(_is_num(r[k]) and abs(r[k]) <= DECO_NUM_LIMIT for k in ("x", "y", "w", "h")):
            continue       # 検証（deco_problems）が先に fail にする。ここは型違いの値で落ちないための保険
        alpha = r.get("alpha") if _is_num(r.get("alpha")) else None
        fill = color_hex(colors, r["fill"])
        el = {"kind": "shape", "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"],
              "fill": {"color": fill, "alpha": max(0.0, alpha)} if alpha is not None and alpha < 1 else fill,
              "name": r.get("name") or "飾り"}
        if r.get("geom") == "ellipse" and not (_is_num(r.get("radius")) and r["radius"] < DECO_PILL_MIN):
            el["geom"] = "ellipse"        # radius が小さい形（sharp = 0・editorial = 4）では円にせず、その角丸の四角にする（S5b）
        elif _is_num(r.get("radius")) and r["radius"] > 0 and min(r["w"], r["h"]) > 0:
            rad = min(r["radius"], r["w"] / 2, r["h"] / 2)
            el["geom"], el["adj"] = "roundRect", {"adj": int(min(50000, rad / min(r["w"], r["h"]) * 100000))}
        out.append(el)
    return out


def _quote_mark_cmds(w: float, h: float) -> list:
    """二重の引用符（“）の自由曲線。1 つの「6」形（下に丸み、上に右へ伸びる尾）を 2 つ並べる。w × h の箱の中（単位 0〜1 を拡大）。"""
    k_w, k_h = w / 2.3, h        # 1 つの形は幅 1、間隔 0.3、2 つで 2.3
    cmds = []
    for off in (0.0, 1.3):
        def pt(x, y, o=off):
            return [round((o + x) * k_w, 2), round(y * k_h, 2)]
        cmds += [["M"] + pt(0.92, 0.0),
                 ["C"] + pt(0.50, 0.06) + pt(0.06, 0.34) + pt(0.06, 0.68),
                 ["C"] + pt(0.06, 0.86) + pt(0.22, 1.0) + pt(0.43, 1.0),
                 ["C"] + pt(0.64, 1.0) + pt(0.80, 0.86) + pt(0.80, 0.68),
                 ["C"] + pt(0.80, 0.44) + pt(0.62, 0.30) + pt(0.50, 0.30),
                 ["C"] + pt(0.60, 0.16) + pt(0.74, 0.07) + pt(0.92, 0.0),
                 ["Z"]]
    return cmds


def mark_elements(st: dict, colors: dict) -> list:
    """variant の引用符（mark）を、フォントの字形ではなく図形（自由曲線）で描く canvas 要素。mark に "vector": true があるときだけ。
    “ のグリフは HTML と PPTX でフォントが違うと左右に 100px 近くずれる（和文フォントでは全角の字形になる）ので、図形にして位置を固定する。
    mark の x / y は図形の左上（size は図形の高さの目安: 高さ = size × 0.42、幅 = 高さ × 1.55）。"""
    mk = st.get("mark")
    if not (isinstance(mk, dict) and mk.get("vector") and _is_num(mk.get("size")) and _is_num(mk.get("x")) and _is_num(mk.get("y"))):
        return []
    h = round(mk["size"] * 0.42, 2)
    w = round(h * 1.55, 2)
    return [{"kind": "shape", "geom": "custom", "x": mk["x"], "y": mk["y"], "w": w, "h": h,
             "fill": color_hex(colors, mk.get("color", "accent_on_primary")), "name": "引用符",
             "path": [{"cmds": _quote_mark_cmds(w, h), "fill": True, "stroke": False}]}]


def mark_is_vector(st: dict) -> bool:
    mk = st.get("mark")
    return isinstance(mk, dict) and bool(mk.get("vector"))


def panel_rect_drawn(st: dict, bg: dict | None) -> bool:
    """variant の panel 領域（色の面）を自分で塗るか。背景に画像があれば画像が覆うので塗らない。"""
    return isinstance(st.get("panel"), dict) and st["panel"].get("fill") and not (bg and bg.get("image") is not None)


def panel_region_elements(st: dict, bg: dict | None, colors: dict) -> list:
    """variant の panel 領域（画像が無いときの色面）→ canvas 要素。"""
    if not panel_rect_drawn(st, bg):
        return []
    p = st["panel"]
    return [{"kind": "shape", "x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"], "fill": color_hex(colors, p["fill"]),
             "name": "パネル"}]


def hero_layers(st: dict, bg: dict | None, colors: dict) -> list:
    """全面系タイプの下地から順に: 背景（画像・覆い・色面）→ variant の panel → 飾り。HTML / PPTX が最初に描く canvas 要素列。"""
    return hero_background_elements(st, bg, colors) + panel_region_elements(st, bg, colors) + deco_elements(st, colors) + mark_elements(st, colors)


# ---------------------------------------------------------------------------
# split（非対称分割）
# ---------------------------------------------------------------------------

def split_params(slide: dict, panel_default: dict) -> tuple:
    """(side, ratio)。検証前でも安全に値を返す（不正なら既定）。"""
    side = slide.get("side") if slide.get("side") in SPLIT_SIDES else "left"
    r = slide.get("ratio")
    lo, hi = SPLIT_RATIO
    ratio = r if isinstance(r, (int, float)) and not isinstance(r, bool) and lo <= r <= hi else (panel_default or {}).get("ratio", 0.4)
    return side, ratio


def apply_split_geometry(st: dict, slide: dict, brand: bool = False) -> dict:
    """split の領域（panel / title / body / footer …）を side・ratio で配置する。タイトルが無ければ本文を上に詰める。
    余白・パネルの色などの値は types.split（レイアウト JSON）が持つ。ここは「パネルの幅から残りの領域の x と幅を決める」計算だけ。"""
    p = st["panel"]
    side, ratio = split_params(slide, p)
    pw = round(CANVAS_W * ratio)
    p.update({"x": 0 if side == "left" else CANVAS_W - pw, "y": 0, "w": pw, "h": CANVAS_H, "side": side, "ratio": ratio})
    mg = p.get("margin", 56)                     # パネルと本文の間の余白
    edge = p.get("edge", 72)                     # スライドの端と本文の間の余白
    if side == "left":
        x0, x1 = pw + mg, CANVAS_W - edge
    else:
        x0, x1 = edge, CANVAS_W - pw - mg
    w = x1 - x0
    for name in ("eyebrow", "title", "rule", "lead", "body"):
        r = st.get(name)
        if isinstance(r, dict):
            r["x"], r["w"] = x0, w
    if isinstance(st.get("footer_l"), dict):
        st["footer_l"]["x"] = x0
        st["footer_l"]["w"] = min(st["footer_l"].get("w", 700), max(w - 130, 100))
    if isinstance(st.get("footer_r"), dict):
        st["footer_r"]["w"] = min(st["footer_r"].get("w", 120), w)
        st["footer_r"]["x"] = x1 - st["footer_r"]["w"]
    br = st.get("brand") if brand and isinstance(st.get("brand"), dict) else None
    if br:
        # meta.brand はパネルの上端に置く（右のパネルは既定の位置のまま、左のパネルは右上の角 = パネルの内側）。文字色はパネルの文字（title_color）と同じ。
        # 残りの領域に置くと、タイトルを brand の分だけ狭めることになり、2 行に折れて罫線に重なる（s3-A-04）
        if side == "left":
            br["x"] = pw - p.get("pad_x", 56) - br.get("w", 140)
        br["color"] = p.get("title_color", "on_primary")
    has_title = bool(slide.get("title"))
    if not has_title:
        st.pop("rule", None)
        st.pop("title", None)
        b = st["body"]
        if not slide.get("lead"):
            top = b.get("y_no_title", b.get("y_no_lead", b["y"]))
            bottom = b["y"] + b["h"]
            b["y_no_lead"] = top
            b["y"], b["h"] = top, bottom - top
    return st


def validate_split(slide: dict, where: str, fail, warn, colors: dict, deck_dir, image_check=None) -> None:
    """split の入力の検査（スタイル解決より前）。型違いは fail、未知キー・多すぎる項目は warn。"""
    side = slide.get("side")
    if side is not None and side not in SPLIT_SIDES:
        fail(f"{where}: side は left / right のどちらかで指定してください（{side!r}）→ パネルを置く側。例: \"side\": \"left\"")
    ratio = slide.get("ratio")
    if ratio is not None:
        lo, hi = SPLIT_RATIO
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or ratio != ratio or not (lo <= ratio <= hi):
            fail(f"{where}: ratio はパネルの幅の割合（{lo}〜{hi}）で指定してください（{ratio!r}）→ 例: \"ratio\": 0.4（既定）")
    panel = slide.get("panel")
    if panel is None:
        fail(f"{where}: panel（端まで届く色面か画像のパネル）が必要です"
             f" → \"panel\": {{\"fill\": \"primary\", \"title\": \"作成時間は 3 分の 1 に\", \"text\": \"…\"}} のように書く")
    if not isinstance(panel, dict):
        fail(f"{where}: panel はオブジェクト（{{\"fill\": \"primary\", \"title\": \"…\"}}）で指定してください（{type(panel).__name__} が書かれています）")
    for k in panel:
        if k not in SPLIT_PANEL_KEYS and isinstance(k, str) and not k.startswith("_"):
            m = difflib.get_close_matches(k, SPLIT_PANEL_KEYS, n=1, cutoff=0.6)
            warn(f"{where}: panel の \"{k}\" は無視されます{'（もしかして \"' + m[0] + '\"）' if m else ''}"
                 f" → panel のキー: {' / '.join(SPLIT_PANEL_KEYS)}")
    for k in ("eyebrow", "title", "text"):
        v = panel.get(k)
        if v is not None and not isinstance(v, (str, int, float)) or isinstance(v, bool):
            fail(f"{where}: panel.{k} は文字列で指定してください（{type(v).__name__} が書かれています）")
    kp = panel.get("kpi")
    if kp is not None:
        if isinstance(kp, (str, int, float)) and not isinstance(kp, bool):
            kp = panel["kpi"] = {"value": str(kp)}
        if not isinstance(kp, dict) or not str(kp.get("value", "")).strip():
            fail(f"{where}: panel.kpi は {{\"value\": \"1/3\", \"label\": \"作成時間\"}} の形で、value（大きく見せる数字）が必要です")
        for k in kp:
            if k not in SPLIT_KPI_KEYS and isinstance(k, str) and not k.startswith("_"):
                warn(f"{where}: panel.kpi の \"{k}\" は無視されます → 使えるキー: {' / '.join(SPLIT_KPI_KEYS)}")
        if panel.get("title"):
            warn(f"{where}: panel に kpi と title を両方書いています。数字（kpi）を主役にするなら title は短く、"
                 f"文（title）を主役にするなら kpi を消す（主役は 1 つ）")
    items = panel.get("items")
    if items is not None:
        if not isinstance(items, list) or not all(isinstance(x, (str, int, float)) and not isinstance(x, bool) for x in items):
            fail(f"{where}: panel.items は文字列の配列で指定してください（例: [\"下書き\", \"レビュー\", \"承認\"]）")
        panel["items"] = [str(x) for x in items]
        if len(items) > SPLIT_ITEMS_MAX:
            warn(f"{where}: panel.items が{len(items)}個あります（{SPLIT_ITEMS_MAX}個までが目安。パネルは短く言い切る場所）"
                 f" → 本文側の bullets ブロックに移す")
    if not any(panel.get(k) for k in ("title", "text", "kpi", "items", "eyebrow")):
        warn(f"{where}: panel に文字がありません（色面か画像だけになります）→ 主役の一文（title）か数字（kpi）を書く")
    bgd = {k: panel[k] for k in ("fill", "image", "overlay", "opacity", "position") if k in panel}
    if not bgd:
        # 何も書かなければ既定の色面（layout の types.split.panel.fill）
        return
    validate_background(bgd, f"{where}: panel", colors, deck_dir, fail, warn, image_check)


def panel_content(slide: dict) -> dict:
    """panel の文字の内容（正規化）。"""
    p = slide.get("panel") or {}
    kp = p.get("kpi")
    if isinstance(kp, (str, int, float)) and not isinstance(kp, bool):
        kp = {"value": str(kp)}
    return {"eyebrow": str(p["eyebrow"]) if p.get("eyebrow") not in (None, "") else "",
            "title": str(p["title"]) if p.get("title") not in (None, "") else "",
            "text": str(p["text"]) if p.get("text") not in (None, "") else "",
            "kpi": kp if isinstance(kp, dict) else None,
            "items": [str(x) for x in (p.get("items") or [])][:SPLIT_ITEMS_MAX + 3]}


def panel_plan(slide: dict, st: dict, ctx) -> dict:
    """split のパネルの中身を、パネルの幅・高さに収まる文字サイズで組む → {"els": canvas 要素, "issues": [(コード, 文)], "sizes": {...}}。
    HTML と PPTX が同じ要素列から描く。寸法・色・文字サイズの上限と下限は st["panel"]（レイアウト JSON の値）。"""
    import proposal_engine as pe
    p = st["panel"]
    c = panel_content(slide)
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    side = p.get("side", "left")
    padx, pady = p.get("pad_x", 56), p.get("pad_y", 64)
    padx = min(padx, round(w * 0.12))      # 細いパネル（ratio が小さい）は左右の余白を詰め、文字の幅を確保する（0.4 以上では変わらない）
    # 本文側の境目の反対側（スライドの端）に余白を多めに取らない。内側（本文に面する側）にも同じ余白
    inner_w = max(w - 2 * padx, 80)
    inner_h = max(h - 2 * pady, 80)
    gap = p.get("gap", 18)
    caps = {"eyebrow": p.get("eyebrow_size", 15), "title": p.get("title_size", 44), "text": p.get("text_size", 20),
            "kpi": p.get("kpi_size", 120), "kpi_label": p.get("kpi_label_size", 22), "items": p.get("items_size", 20)}
    floors = {"eyebrow": p.get("eyebrow_min_size", 13), "title": p.get("title_min_size", 26), "text": p.get("text_min_size", 15),
              "kpi": p.get("kpi_min_size", 56), "kpi_label": p.get("kpi_label_min_size", 15), "items": p.get("items_min_size", 15)}
    # kpi の数字は途中で折り返さない（「¥123,456」の次の行が「,789円」になる）: 1 行に収まる大きさまで下げる。下限でも入らなければ警告
    kpi_issue = None
    if c["kpi"]:
        kval = str(c["kpi"].get("value", "")) + (str(c["kpi"].get("unit", "") or ""))
        kem = sum(ja_text.char_em(ch, ja_text.heading_fonts(), True) for ch in kval)
        if kem > 0:
            cap_w = int(inner_w * 0.94 / kem)
            if cap_w < caps["kpi"]:
                caps["kpi"] = max(floors["kpi"], cap_w)
            if cap_w < floors["kpi"]:
                kpi_issue = (kval, cap_w)
    lh = {"title": p.get("title_line_height", 1.25), "text": p.get("text_line_height", 1.55), "kpi": 1.0,
          "kpi_label": p.get("text_line_height", 1.55), "items": p.get("items_line_height", 1.5), "eyebrow": 1.2}

    # 文字は文節の切れ目で折り返す（語の途中・1 文字だけの最終行を避ける。高さの見積もりも改行を入れた文で測る）
    def ph_title(t, size):
        return ja_text.phrase_wrap(t, size, inner_w, font=ja_text.heading_fonts(), bold=True, min_tail=5)

    def ph_text(t, size):
        return ja_text.phrase_wrap(t, size, inner_w, min_tail=4)

    def ph_item(t, size):
        return ja_text.phrase_wrap(t, size, inner_w - size, min_tail=3)

    def height(f):
        sz = {k: max(floors[k], round(caps[k] * f)) if f < 1 else caps[k] for k in caps}
        total, parts = 0.0, 0
        if c["eyebrow"]:
            total += sz["eyebrow"] * 1.2 * 1.4 + 10
            parts += 1
        if c["kpi"]:
            val = str(c["kpi"].get("value", "")) + str(c["kpi"].get("unit", "") or "")
            total += pe.text_h(val, sz["kpi"], inner_w, head=True, bold=True, lh=lh["kpi"]) + (gap if parts else 0)
            parts += 1
            if c["kpi"].get("label"):
                total += pe.text_h(str(c["kpi"]["label"]), sz["kpi_label"], inner_w, lh=lh["kpi_label"]) + 6
        if c["title"]:
            total += pe.text_h(ph_title(c["title"], sz["title"]), sz["title"], inner_w, head=True, bold=True, lh=lh["title"]) + (gap if parts else 0)
            parts += 1
        if c["text"]:
            total += pe.text_h(ph_text(c["text"], sz["text"]), sz["text"], inner_w, lh=lh["text"]) + (gap if parts else 0)
            parts += 1
        if c["items"]:
            total += sum(pe.text_h(ph_item(t, sz["items"]), sz["items"], inner_w - sz["items"], lh=lh["items"]) + 8 for t in c["items"]) + (gap if parts else 0)
        return total, sz

    f, fit = 1.0, False
    while True:
        total, sz = height(f)
        if total <= inner_h + 0.5:
            fit = True
            break
        if all(sz[k] <= floors[k] for k in sz):
            break
        f = round(f - 0.04, 3)
        if f < 0.2:
            break
    issues = []
    if not fit:
        issues.append(("panel-overflow", f"{{label}}: パネルの文字が最小の文字サイズでも収まりません（約{int(total - inner_h)}px はみ出す）"
                                         f" → panel の title / text を短くする、items を減らす、または ratio を上げてパネルを広げる"))
    elif f < 0.9:
        issues.append(("panel-shrunk", f"{{label}}: パネルの文字を {caps['title']}px 基準から縮めました（title {sz['title']}px）"
                                       f" → パネルの文は短く言い切る（目安: title 30 字以内）"))
    # 大きく見せる一文は、最終行に 4 文字以下の切れ端（「1 に」など）だけ残さない
    if c["title"]:
        t0 = ph_title(c["title"], sz["title"])
        c["title"] = t0 if t0 != c["title"] else ja_text.balance(c["title"], sz["title"], inner_w, font=ja_text.heading_fonts(), bold=True, min_tail=5)
    if c["text"]:
        t0 = ph_text(c["text"], sz["text"])
        c["text"] = t0 if t0 != c["text"] else ja_text.balance(c["text"], sz["text"], inner_w, min_tail=4)
    c["items"] = [ph_item(t, sz["items"]) for t in c["items"]]
    if kpi_issue:
        issues.append(("panel-kpi-wide", f"{{label}}: panel.kpi の数字 '{kpi_issue[0]}' が最小の文字サイズ（{floors['kpi']}px）でも幅に収まらず、途中で折り返されます"
                                         f" → value を短くする（単位は unit ではなく label に移す・「億」「万」にまとめる）、または ratio を上げてパネルを広げる"))
    # 大きく見せる一文が 5 行以上に折れるなら、パネルが狭すぎる（細切れの文は主役にならない）
    n_title = ja_text.estimate_lines(c["title"], sz["title"], inner_w, ja_text.heading_fonts(), True) if c["title"] else 0
    if n_title > 4:
        issues.append(("panel-title-long", f"{{label}}: パネルの title が{n_title}行に折れます（{len(c['title'].replace(chr(10), ''))}字・{sz['title']}px）"
                                           f" → title を短くする（目安: 30 字以内）、または ratio を上げてパネルを広げる"))
    paras = []
    col = lambda k, d: p.get(k, d)
    if c["eyebrow"]:
        paras.append(ctx.para(c["eyebrow"], sz["eyebrow"], col("eyebrow_color", "accent_on_primary"), bold=True, head=True,
                              lh=1.4, after=10))
    first = not paras
    if c["kpi"]:
        val = str(c["kpi"].get("value", "")) + (str(c["kpi"].get("unit", "")) if c["kpi"].get("unit") else "")
        paras.append(ctx.para(val, sz["kpi"], col("kpi_color", "on_primary"), bold=True, head=True, lh=lh["kpi"],
                              after=6 if c["kpi"].get("label") else gap))
        if c["kpi"].get("label"):
            paras.append(ctx.para(str(c["kpi"]["label"]), sz["kpi_label"], col("label_color", "on_primary_soft"), lh=lh["kpi_label"], after=gap))
    if c["title"]:
        paras.append(ctx.para(c["title"], sz["title"], col("title_color", "on_primary"), bold=True, head=True, lh=lh["title"], after=gap))
    if c["text"]:
        paras.append(ctx.para(c["text"], sz["text"], col("text_color", "on_primary_soft"), lh=lh["text"], after=gap))
    for it in c["items"]:
        paras.append(ctx.para(it, sz["items"], col("text_color", "on_primary_soft"), bullet="•", lh=lh["items"], after=8))
    if paras and paras[-1].get("spaceAfter"):
        paras[-1]["spaceAfter"] = 0
    els = []
    if paras:
        els.append(ctx.box(x + padx, y + pady, inner_w, inner_h, paras=paras, anchor="ctr", name="パネルの文字"))
    return {"els": els, "issues": issues, "sizes": sz, "fit": fit}


# ---------------------------------------------------------------------------
# cards の強弱（emphasis）と span
# ---------------------------------------------------------------------------

EMPH_KEYS = ("fill", "heading_color", "body_color", "item_color", "marker_color", "icon_color", "border_color", "border_w")


def card_emphasis(card) -> object:
    """カードの emphasis の値（True / "accent" / "soft"）。強調なしは None。"""
    e = card.get("emphasis") if isinstance(card, dict) else None
    if e is True or e in ("accent", "soft"):
        return e
    return None


def card_style(g: dict, emph) -> dict:
    """カード 1 枚の色（grid の値から。emph_*・emph_accent_*・emph_soft_*）。強調なしは通常の色。
    戻り値のキー: fill / heading_color / body_color / item_color / marker_color / icon_color / border_color / border_w / shadow"""
    base = {"fill": g.get("fill", "surface"), "heading_color": g.get("heading_color", "primary"), "body_color": g.get("body_color", "text"),
            "item_color": g.get("item_color", "muted"), "marker_color": "accent", "icon_color": g.get("icon_color", "primary"),
            "border_color": g.get("border_color"), "border_w": g.get("border_w")}
    if not emph:
        return base
    prefix = {True: "emph_", "accent": "emph_accent_", "soft": "emph_soft_"}[emph]
    out = dict(base)
    for k in EMPH_KEYS:
        v = g.get(prefix + k)
        if v is not None:
            out[k] = v
    if emph is not None:
        out["emphasized"] = True
    return out


def emph_grid(g: dict, emph) -> dict:
    """強調のカードは文字も大きくする（grid.emph_scale 倍。既定 1 = 変えない）。見出し・本文・項目の文字サイズだけを掛けた grid の写しを返す。"""
    k = g.get("emph_scale", 1.0)
    if not emph or not isinstance(k, (int, float)) or k == 1:
        return g
    out = dict(g)
    for key, dflt in (("heading_size", 19), ("body_size", 15), ("item_size", 14)):
        out[key] = round(g.get(key, dflt) * k)
    return out


def cards_plan(n: int, slide_columns, g: dict, spans=None) -> dict:
    """cards の格子の配置（span つき）。spans は各カードの占める列数（無ければ 1）。
    戻り値は proposal_engine.cards_cells と同じ形（cells は span ぶんの幅）に rows_of（段ごとのカード番号）と空きの段 gaps を足したもの。
    カードは書いた順に左上から右へ置き、残りの列に入らなければ次の段へ（空きは gaps に記録し、検証が警告する）。"""
    cols = max(1, slide_columns if isinstance(slide_columns, int) and not isinstance(slide_columns, bool) else g.get("cols", 3))
    spans = [max(1, min(int(s) if isinstance(s, (int, float)) and not isinstance(s, bool) else 1, cols)) for s in (spans or [1] * n)]
    spans = (spans + [1] * n)[:n]
    placed, rows_of, row, used = [], [], [], 0
    for i, sp in enumerate(spans):
        if used + sp > cols and row:
            rows_of.append(row)
            row, used = [], 0
        placed.append((len(rows_of), used, sp))
        row.append(i)
        used += sp
    if row:
        rows_of.append(row)
    rows = max(1, len(rows_of))
    gap = g.get("gap", 16)
    cw = (g["w"] - (cols - 1) * gap) / cols
    chh = (g["h"] - (rows - 1) * gap) / rows
    cells = []
    for (r, c, sp) in placed:
        cells.append((g["x"] + c * (cw + gap), g["y"] + r * (chh + gap), cw * sp + gap * (sp - 1), chh))
    gaps = [(ri, cols - sum(spans[i] for i in rw)) for ri, rw in enumerate(rows_of) if sum(spans[i] for i in rw) < cols]
    return {"cols": cols, "rows": rows, "gap": gap, "cw": cw, "chh": chh, "cells": cells, "rows_of": rows_of, "gaps": gaps,
            "spans": spans}


def card_spans(slide: dict) -> list | None:
    """cards の span の一覧（どれにも span が無ければ None = 従来の等分）。"""
    cards = slide.get("cards")
    if not isinstance(cards, list) or not any(isinstance(c, dict) and c.get("span") not in (None, 1) for c in cards):
        return None
    return [c.get("span", 1) if isinstance(c, dict) else 1 for c in cards]


def validate_cards(slide: dict, where: str, g: dict, fail, warn) -> None:
    """cards の emphasis / span の検査（型違いは fail、強調の多すぎ・段の空きは warn）。"""
    cards = slide.get("cards")
    if not isinstance(cards, list):
        return
    n_emph = 0
    cols = slide.get("columns") if isinstance(slide.get("columns"), int) and not isinstance(slide.get("columns"), bool) else (g or {}).get("cols", 3)
    for k, c in enumerate(cards):
        if not isinstance(c, dict):
            continue
        e = c.get("emphasis")
        if e is not None and e is not False and e not in CARD_EMPHASIS:
            fail(f"{where}: cards[{k}].emphasis は true / \"accent\" / \"soft\" のいずれかで指定してください（{e!r}）"
                 f" → 主役のカードを塗りつぶすなら true（強調しないなら書かない）")
        if card_emphasis(c) is not None:
            n_emph += 1
        sp = c.get("span")
        if sp is not None:
            if isinstance(sp, bool) or not isinstance(sp, int) or sp < 1:
                fail(f"{where}: cards[{k}].span は 1 以上の整数（そのカードが占める列数）で指定してください（{sp!r}）→ 横に 2 列分なら \"span\": 2")
            if sp > cols:
                fail(f"{where}: cards[{k}].span（{sp}）が列数（{cols}）を超えています → span を {cols} 以下にするか、columns を増やす")
    if n_emph > CARD_EMPHASIS_MAX:
        warn(f"{where}: 強調（emphasis）のカードが{n_emph}枚あります（{CARD_EMPHASIS_MAX}枚まで）→ 全部を強調すると強調にならない。"
             f"主役の 1〜{CARD_EMPHASIS_MAX} 枚だけにする")
    spans = card_spans(slide)
    if spans:
        plan = cards_plan(len(cards), slide.get("columns"), g or {"w": 1136, "h": 440}, spans)
        if plan["gaps"]:
            rows = "・".join(f"{r + 1}段目" for r, _ in plan["gaps"][:3])
            warn(f"{where}: span の組み合わせで{rows}に空きができます（1 段は {plan['cols']} 列ぶんを使い切る組み合わせが整う）"
                 f" → 段ごとの span の合計を {plan['cols']} にそろえる（例: 2 + 1、1 + 1 + 1）か、カードの順番を替える")

# -*- coding: utf-8 -*-
"""テーマの「形」: トークン表と shape プリセット（色のテーマとは独立に選べる角丸・罫線・見出しの組み方・太さ・字間）。

仕組み（build_deck.load_deck が apply_to_layout を呼ぶ。標準ライブラリのみ・副作用なし）:

  1. レイアウト JSON（templates/layouts/default.json）の最上位 ``tokens`` が既定値の表（= classic。何も指定しない見た目）。
     領域の値は ``"$グループ.名前"``（例 ``"radius": "$radius.card"``）でその表を参照できる。
  2. shape プリセット ``templates/shapes/<名前>.json``（``{"name", "label", "description", "tokens", "layout"}``）が
     tokens を差し替え、``layout``（``{"common": {...}, "types": {...}}``）で個別の領域の値を上書きする。
     選び方は ``meta.shape``、無ければテーマ JSON の ``"shape"``、どちらも無ければ ``classic``。
  3. テーマ JSON も ``tokens`` と ``layout`` を持てる（shape より後に重なる）。
  4. 解決順: レイアウト既定 → shape → テーマ → density → meta.layout_overrides → slide.style → 自動フィット。
     ``$`` 参照は layout・style・layout_overrides のどれに書いても、解決済みの tokens で置き換わる（未知は fail）。

解決済みの tokens 表は ``theme["tokens"]`` と ``layout["tokens"]`` に入る（パターン・dataviz・canvas が同じ表を読む）。
"""
from __future__ import annotations

import copy
import difflib
import json
import os
import re
import sys
from pathlib import Path

import deck_paths

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHAPE = "classic"

REF_RE = re.compile(r"^\$([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z0-9_]+)$")

RULE_STYLES = ("line", "short", "none", "bar-left")
CASES = ("upper", "none")
SHADOW_CARD = ("none", "soft")

# 値の型の検査表: グループ -> {名前 or "*": 種類}。種類: nonneg / pos / weight / tracking / enum:... / unit
TOKEN_KINDS = {
    "radius": {"*": "nonneg"},
    "line": {"*": "nonneg"},
    "rule": {"style": "enum:" + "|".join(RULE_STYLES), "length": "pos", "gap": "nonneg", "*": "nonneg"},
    "weight": {"*": "weight"},
    "tracking": {"*": "tracking"},
    "type": {"*": "pos"},
    "space": {"*": "nonneg"},
    "shadow": {"card": "enum:" + "|".join(SHADOW_CARD), "dy": "nonneg", "blur": "nonneg", "alpha": "unit", "*": "nonneg"},
    "case": {"*": "enum:" + "|".join(CASES)},
}

SHAPE_TOP_KEYS = frozenset({"name", "label", "description", "tokens", "layout"})


_DEFAULT_TOKENS: dict = {}


def default_tokens() -> dict:
    """同梱レイアウト（templates/layouts/default.json）の tokens 表 = classic の値。パターンの $radius.card などの既定にも使う。"""
    if not _DEFAULT_TOKENS:
        try:
            data = json.loads((ROOT / "templates" / "layouts" / "default.json").read_text(encoding="utf-8-sig"))
            _DEFAULT_TOKENS.update({g: v for g, v in (data.get("tokens") or {}).items() if isinstance(v, dict)})
        except (OSError, ValueError):
            pass
    return copy.deepcopy(_DEFAULT_TOKENS)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


# ---------------------------------------------------------------------------
# 探索と読み込み
# ---------------------------------------------------------------------------

def shape_dirs(deck_dir=None) -> list:
    """shape の探索ディレクトリ（環境変数 SLIDE_DECK_SHAPES → <デッキ>/shapes/ → 親 3 階層 → カレント → 同梱）。"""
    return deck_paths.search_dirs("shapes", deck_dir)


def check_name(name, key: str = "meta.shape"):
    """名前の検査（パス区切り・絶対パス・先頭ドットは不可）。誤りなら理由の文字列、正しければ None。"""
    if not isinstance(name, str) or not name.strip():
        return f"{key} は shape の名前（文字列。例: \"sharp\"）で指定してください"
    if any(ch in name for ch in ("/", "\\", ":", "\x00")) or name.startswith(".") or os.path.isabs(name):
        return (f"{key} '{name}' は名前だけを指定してください（パス区切り・絶対パス・先頭のドットは使えません）。"
                f"shape は探索先に <名前>.json として置きます")
    return None


def list_shapes(deck_dir=None) -> list:
    """見つかった shape の [(名前, パス)]（先に見つかった順・同名は先勝ち）。"""
    seen, out = set(), []
    for d in shape_dirs(deck_dir):
        try:
            for p in sorted(d.glob("*.json")):
                if p.stem not in seen:
                    seen.add(p.stem)
                    out.append((p.stem, p))
        except OSError:
            continue
    return out


def load_shape(name, deck_dir=None, key: str = "meta.shape", fail=None):
    """名前から shape JSON を探して読み、検証して返す。fail は build_deck.fail 相当（無ければ ValueError）。"""
    def _fail(msg):
        if fail:
            fail(msg)
        raise ValueError(msg)

    bad = check_name(name, key)
    if bad:
        _fail(bad)
    cands = [d / f"{name}.json" for d in shape_dirs(deck_dir) if (d / f"{name}.json").is_file()]
    if not cands:
        names = [n for n, _ in list_shapes(deck_dir)]
        near = difflib.get_close_matches(str(name), names, n=1, cutoff=0.5)
        hint = f"（もしかして \"{near[0]}\"）" if near else ""
        _fail(f"shape '{name}' が見つかりません{hint}（使える名前: {', '.join(names) or 'なし'}。"
              f"探索: {', '.join(str(d) for d in shape_dirs(deck_dir))}）→ {key} を直すか、{name}.json を探索先のどれかに置く")
    path = cands[0]
    _shadow = deck_paths.shadow_note("shapes", name, path)
    if _shadow:
        print(f"note: {_shadow}", file=sys.stderr)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        _fail(f"shape '{name}'（{path}）を読めません: {e}")
    if not isinstance(data, dict):
        _fail(f"shape '{name}'（{path}）の最上位はオブジェクトにしてください")
    data["name"] = name
    data["_path"] = str(path)
    return data


# ---------------------------------------------------------------------------
# トークン表の検査
# ---------------------------------------------------------------------------

def _kind_of(group: str, name: str):
    k = TOKEN_KINDS.get(group)
    if not k:
        return None
    return k.get(name, k.get("*"))


def check_token_value(group: str, name: str, v) -> str:
    """トークン 1 つの値の検査。問題があれば理由（日本語）、無ければ空文字。"""
    kind = _kind_of(group, name)
    path = f"{group}.{name}"
    if kind is None:
        if isinstance(v, (dict, list)) or v is None:
            return f"{path} は数値か文字列で指定してください"
        return ""
    if kind.startswith("enum:"):
        opts = kind[5:].split("|")
        if v not in opts:
            return f"{path} は {' / '.join(opts)} のいずれかで指定してください（{v!r} が書かれています）"
        return ""
    if not _is_num(v):
        return f"{path} は数値で指定してください（{v!r} が書かれています） → 引用符なしの数値にする"
    if kind == "pos" and v <= 0:
        return f"{path} は 0 より大きい数値で指定してください（{v}）"
    if kind == "nonneg" and v < 0:
        return f"{path} は 0 以上で指定してください（{v}）"
    if kind == "weight" and not (100 <= v <= 900):
        return f"{path} は 100〜900 の太さで指定してください（{v}。400 = 標準、700 = 太字）"
    if kind == "tracking" and not (-0.2 <= v <= 0.6):
        return f"{path} は -0.2〜0.6（em 単位の字間。0.05 = 文字の幅の 5% を足す）で指定してください（{v}）"
    if kind == "unit" and not (0 <= v <= 1):
        return f"{path} は 0〜1 で指定してください（{v}）"
    return ""


def check_tokens(tokens, base_tokens, where: str) -> list:
    """tokens 表の検査 → [(level, 本文)]。base_tokens はレイアウト既定の表（定義の無い名前は「使われない」と警告する）。"""
    out = []
    if tokens is None:
        return out
    if not isinstance(tokens, dict):
        return [("fail", f"{where}: tokens はオブジェクト（{{ \"radius\": {{ \"card\": 0 }} }}）で指定してください")]
    for grp, group in tokens.items():
        if isinstance(grp, str) and grp.startswith("_"):
            continue
        if not isinstance(group, dict):
            out.append(("fail", f"{where}: tokens.{grp} はオブジェクト（{{ 名前: 値 }}）で指定してください"))
            continue
        base_group = (base_tokens or {}).get(grp)
        if base_tokens and base_group is None:
            near = difflib.get_close_matches(str(grp), [g for g in base_tokens if not str(g).startswith("_")], n=1, cutoff=0.6)
            out.append(("warn", f"{where}: tokens.{grp} のグループはレイアウトにありません。参照する領域が無ければ使われません"
                                f"{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                f" → 使えるグループ: {' / '.join(g for g in base_tokens if not str(g).startswith('_'))}"))
        for name, v in group.items():
            if isinstance(name, str) and name.startswith("_"):
                continue
            bad = check_token_value(grp, name, v)
            if bad:
                out.append(("fail", f"{where}: tokens.{bad}"))
                continue
            if isinstance(base_group, dict) and name not in base_group:
                near = difflib.get_close_matches(str(name), list(base_group), n=1, cutoff=0.6)
                out.append(("warn", f"{where}: tokens.{grp}.{name} はレイアウトで使われていません"
                                    f"{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                    f" → 使える名前: {' / '.join(base_group)}"))
    return out


_HEX = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def _color_issues(rd, label: str, colors, level: str) -> list:
    """領域の色キー（color / fill / *_color / *_fill）が、テーマの色トークン名か #hex かを見る。"""
    out = []
    for k, v in rd.items():
        if isinstance(k, str) and isinstance(v, str) and (k in ("color", "fill") or k.endswith(("_color", "_fill"))) \
                and v not in colors and not _HEX.match(v) and not v.startswith("$"):
            near = difflib.get_close_matches(v, list(colors), n=1, cutoff=0.6)
            out.append((level, f"{label}.{k} の色 '{v}' が見つかりません{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                               f" → テーマの色トークン名（{' / '.join(list(colors)[:6])} …）か #RRGGBB で指定する"))
    return out


def _region_issues(rd, defaults, label: str, tokens, known: bool, colors=None, color_level: str = "fail") -> list:
    """layout 差分の領域 1 つ（{プロパティ: 値}）の値の検査。``$`` 参照は解決した値で検査する（未知の参照は fail）。
    known = その領域がレイアウト既定にある（プロパティ名のタイポも見る）。"""
    import deck_schema as dschema
    out = []
    if tokens is not None and has_refs(rd):
        msgs = []
        rd = resolve_refs(rd, tokens, "", msgs.append)
        out += [("fail", f"{label}: {m}") for m in msgs]
        if msgs:
            return out
    out += dschema.check_region_value(rd, defaults if known else None, label, check_unknown=known)
    if colors is not None and isinstance(rd, dict):
        out += _color_issues(rd, label, colors, color_level)
    return out


# shape / テーマの layout（差分）に書ける節。variants / palettes / variant_defaults は主役系タイプ（title / section …）の見た目の型
LAYOUT_DIFF_SECTIONS = ("common", "types", "densities", "variants", "palettes", "variant_defaults")


def check_layout_diff(diff, where: str, tokens=None, base=None, colors=None, color_level: str = "fail") -> list:
    """shape / テーマの layout（差分）の検査 → [(level, 本文)]。
    形（common / types / densities が辞書の辞書）に加え、``base``（レイアウト既定。common / types を持つ辞書）を渡すと
    タイプ名・領域名・プロパティ名（候補つき warn）と、領域の値の型・範囲（レイアウト JSON と同じ検査）も見る。
    ``tokens`` は ``$`` 参照を解決するための tokens 表（無ければ参照は検査から外す）。
    ``colors``（テーマの色トークン名の集まり）を渡すと、色キーの値がその名前か #hex かも見る（level は color_level）。"""
    out = []
    if diff is None:
        return out
    if not isinstance(diff, dict):
        return [("fail", f"{where}: layout はオブジェクト（{{ \"common\": {{…}}, \"types\": {{…}} }}）で指定してください")]
    for k in diff:
        if k not in LAYOUT_DIFF_SECTIONS and not (isinstance(k, str) and k.startswith("_")):
            near = difflib.get_close_matches(str(k), list(LAYOUT_DIFF_SECTIONS), n=1, cutoff=0.6)
            out.append(("warn", f"{where}: layout の \"{k}\" は無視されます{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                f" → 使えるのは {' / '.join(LAYOUT_DIFF_SECTIONS)}"))
    base_types = (base or {}).get("types") if isinstance((base or {}).get("types"), dict) else None
    base_common = (base or {}).get("common") if isinstance((base or {}).get("common"), dict) else {}

    def region_checks(label, rn, rd, known_regions, defaults_of):
        if not isinstance(rd, dict):
            return
        known = known_regions is not None and rn in known_regions
        if known_regions is not None and not known:
            near = difflib.get_close_matches(str(rn), list(known_regions), n=1, cutoff=0.6)
            out.append(("warn", f"{label}: 領域 \"{rn}\" はレイアウトにありません。描かれないので無視されます"
                                f"{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                f" → 使える領域: {' / '.join(known_regions)}"))
        out.extend(_region_issues(rd, defaults_of(rn) if known else None, f"{label}.{rn}", tokens, known, colors, color_level))

    for sec in ("common", "types"):
        v = diff.get(sec)
        if v is None:
            continue
        if not isinstance(v, dict):
            out.append(("fail", f"{where}: layout.{sec} はオブジェクトにしてください"))
            continue
        if sec == "common":
            for rn, rd in v.items():
                if not isinstance(rd, dict):
                    out.append(("fail", f"{where}: layout.common.{rn} は {{ プロパティ }} の形にしてください"))
                    continue
                region_checks(f"{where} の layout.common", rn, rd, list(base_common) if base is not None else None,
                              lambda n: base_common.get(n))
        else:
            for tn, td in v.items():
                if not isinstance(td, dict) or any(not isinstance(x, dict) for x in td.values()):
                    out.append(("fail", f"{where}: layout.types.{tn} は {{ 領域名: {{ プロパティ }} }} の形にしてください"))
                    continue
                if base_types is not None and tn not in base_types:
                    near = difflib.get_close_matches(str(tn), list(base_types), n=1, cutoff=0.6)
                    out.append(("warn", f"{where}: layout.types.{tn} はレイアウトにないスライドタイプです。無視されます"
                                        f"{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                        f" → 使えるタイプ: {' / '.join(base_types)}"))
                    for rn, rd in td.items():
                        out.extend(_region_issues(rd, None, f"{where} の layout.types.{tn}.{rn}", tokens, False, colors, color_level))
                    continue
                known_regions = None
                if base_types is not None:
                    known_regions = list(base_types[tn]) + [r for r in base_common if r not in base_types[tn]]
                for rn, rd in td.items():
                    region_checks(f"{where} の layout.types.{tn}", rn, rd, known_regions,
                                  lambda n, tn=tn: (base_types or {}).get(tn, {}).get(n) or base_common.get(n))
    dens = diff.get("densities")
    if dens is not None:
        if not isinstance(dens, dict):
            out.append(("fail", f"{where}: layout.densities は {{ 密度名: {{ タイプ名: {{ 領域名: {{ プロパティ }} }} }} }} の形にしてください"))
        else:
            import autofit
            for dn, dd in dens.items():
                if dn not in autofit.DENSITIES:
                    out.append(("warn", f"{where}: layout.densities の \"{dn}\" は使われません → 使えるのは {' / '.join(autofit.DENSITIES)}"))
                if not isinstance(dd, dict) or any(not isinstance(tv, dict) or any(not isinstance(rv, dict) for rv in tv.values())
                                                  for tv in dd.values()):
                    out.append(("fail", f"{where}: layout.densities.{dn} は {{ タイプ名: {{ 領域名: {{ プロパティ }} }} }} の形にしてください"))
                    continue
                for tn, tv in dd.items():
                    for rn, rv in tv.items():
                        out.extend(_region_issues(rv, None, f"{where} の layout.densities.{dn}.{tn}.{rn}", tokens, False, colors, color_level))
    base_variants = (base or {}).get("variants") if isinstance((base or {}).get("variants"), dict) else {}
    vd = diff.get("variant_defaults")
    if vd is not None:
        if not isinstance(vd, dict) or any(not isinstance(v, str) for v in vd.values()):
            out.append(("fail", f"{where}: layout.variant_defaults は {{ タイプ名: variant 名 }} の形にしてください（例: {{\"title\": \"left-band\"}}）"))
        elif base_variants:
            for tn, vn in vd.items():
                names = list((base_variants.get(tn) or {}).keys()) + list(((diff.get("variants") or {}).get(tn) or {}).keys())
                if vn != "default" and vn not in names:
                    near = difflib.get_close_matches(vn, names, n=1, cutoff=0.6)
                    out.append(("warn", f"{where}: layout.variant_defaults.{tn} の \"{vn}\" という variant はありません。無視されます"
                                        f"{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                                        f"{' → 使える variant: ' + ' / '.join(names) if names else ' → このタイプに variant はありません'}"))
    for sec in ("variants", "palettes"):
        v = diff.get(sec)
        if v is None:
            continue
        if not isinstance(v, dict) or any(not isinstance(x, dict) for x in v.values()):
            out.append(("fail", f"{where}: layout.{sec} は {{ タイプ名: {{ {'variant 名' if sec == 'variants' else 'light / dark'}: {{ 領域名: {{ プロパティ }} }} }} }} の形にしてください"))
    return out


def validate_shape(data, name: str, base_tokens=None, base_layout=None, colors=None, color_level: str = "fail") -> list:
    """shape JSON 1 つの検査 → [(level, 本文)]。fail: 形・値の型違い。warn: 未知のキー・使われないトークン・タイプ名や領域名のタイポ。
    base_layout（レイアウト既定）を渡すと layout 差分の領域名・値の型も見る。"""
    pre = f"shape '{name}'"
    if not isinstance(data, dict):
        return [("fail", f"{pre}: 最上位はオブジェクト（{{ \"name\": …, \"tokens\": {{…}}, \"layout\": {{…}} }}）にしてください")]
    out = []
    for k in data:
        if isinstance(k, str) and (k.startswith("_") or k in SHAPE_TOP_KEYS):
            continue
        near = difflib.get_close_matches(str(k), sorted(SHAPE_TOP_KEYS), n=1, cutoff=0.6)
        out.append(("warn", f"{pre}: 未知のトップキー \"{k}\" は無視されます{'（もしかして \"' + near[0] + '\"）' if near else ''}"
                            f" → 使えるキー: {' / '.join(sorted(SHAPE_TOP_KEYS))}"))
    for key in ("name", "label", "description"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            out.append(("fail", f"{pre}: {key} は文字列で指定してください"))
    out += check_tokens(data.get("tokens"), base_tokens, pre)
    toks = merge_tokens(base_tokens, data.get("tokens")) if base_tokens else None
    out += check_layout_diff(data.get("layout"), pre, toks, base_layout, colors, color_level)
    return out


# ---------------------------------------------------------------------------
# 参照の解決
# ---------------------------------------------------------------------------

def is_ref(v) -> bool:
    return isinstance(v, str) and bool(REF_RE.match(v))


def lookup(tokens, ref: str):
    """``$グループ.名前`` を引く。見つからなければ (False, 理由)、あれば (True, 値)。"""
    m = REF_RE.match(ref)
    if not m:
        return False, f"トークン参照 {ref!r} の形が違います → \"$グループ.名前\"（例: \"$radius.card\"）"
    grp, name = m.group(1), m.group(2)
    group = (tokens or {}).get(grp)
    if not isinstance(group, dict):
        groups = [g for g in (tokens or {}) if not str(g).startswith("_")]
        near = difflib.get_close_matches(grp, groups, n=1, cutoff=0.5)
        return False, (f"トークン {ref} のグループ '{grp}' がありません{'（もしかして $' + near[0] + '.' + name + '）' if near else ''}"
                       f" → 使えるグループ: {' / '.join(groups) or 'なし'}")
    if name not in group:
        near = difflib.get_close_matches(name, list(group), n=1, cutoff=0.5)
        return False, (f"トークン {ref} がありません{'（もしかして $' + grp + '.' + near[0] + '）' if near else ''}"
                       f" → $%s で使える名前: %s" % (grp, " / ".join(group)))
    return True, group[name]


def resolve_refs(obj, tokens, where: str = "", on_error=None):
    """obj の中の ``"$グループ.名前"`` を表の値に置き換えた新しいオブジェクトを返す（元は変えない）。
    未知の参照は on_error(メッセージ) を呼ぶ（無ければ ValueError）。on_error が戻ったら元の文字列のまま残す。"""
    def walk(v, path):
        if isinstance(v, dict):
            return {k: walk(x, f"{path}.{k}" if path else str(k)) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x, f"{path}[{i}]") for i, x in enumerate(v)]
        if is_ref(v):
            ok, val = lookup(tokens, v)
            if ok:
                return copy.deepcopy(val)
            msg = f"{where + ' の ' if where else ''}{path}: {val}"
            if on_error:
                on_error(msg)
                return v
            raise ValueError(msg)
        return v
    return walk(obj, "")


def has_refs(obj) -> bool:
    if isinstance(obj, dict):
        return any(has_refs(x) for x in obj.values())
    if isinstance(obj, list):
        return any(has_refs(x) for x in obj)
    return is_ref(obj)


def _deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = _deep_merge(out[k], v) if k in out else copy.deepcopy(v)
    return out


def merge_tokens(*tables) -> dict:
    """tokens 表を後勝ちで重ねる（グループごとにマージ）。"""
    out: dict = {}
    for t in tables:
        if not isinstance(t, dict):
            continue
        for grp, group in t.items():
            if isinstance(group, dict):
                out.setdefault(grp, {}).update(copy.deepcopy(group))
    return out


def apply_to_layout(layout: dict, shape: dict = None, theme: dict = None, fail=None, warn=None) -> dict:
    """レイアウトに shape とテーマの層を重ね、``$`` 参照を解決した新しいレイアウトを返す。
    layout["tokens"] は解決済みの表、layout["_shape"] は使った shape の名前。"""
    def _fail(msg):
        if fail:
            fail(msg)
        raise ValueError(msg)

    base_tokens = layout.get("tokens") or {}
    layers_tokens = [base_tokens]
    merged = copy.deepcopy(layout)
    for src in (shape, theme):
        if not isinstance(src, dict):
            continue
        layers_tokens.append(src.get("tokens"))
        diff = src.get("layout")
        if isinstance(diff, dict):
            for sec in ("common", "types", "densities", "variants", "palettes", "variant_defaults"):
                if isinstance(diff.get(sec), dict):
                    merged[sec] = _deep_merge(merged.get(sec) or {}, diff[sec])
    tokens = merge_tokens(*layers_tokens)
    merged["tokens"] = tokens
    for sec in ("common", "types", "densities", "variants", "palettes"):
        if sec in merged:
            merged[sec] = resolve_refs(merged[sec], tokens, f"レイアウト '{layout.get('name', '')}' の {sec}", _fail)
    # split は composite（見出し骨格・ブロックの枠と既定）にパネルの領域を足したもの。shape・テーマの composite への指定も引き継ぐ
    types = merged.get("types")
    if isinstance(types, dict) and isinstance(types.get("composite"), dict) and isinstance(types.get("split"), dict):
        types["split"] = _deep_merge(types["composite"], types["split"])
    merged["_shape"] = (shape or {}).get("name", DEFAULT_SHAPE) if shape else DEFAULT_SHAPE
    merged["_tokens_resolved"] = True
    return merged


def resolve_style_refs(st_obj, layout, where: str, on_error=None):
    """style / layout_overrides の ``$`` 参照を解決する（無ければ同じオブジェクトを返す）。"""
    if not has_refs(st_obj):
        return st_obj
    return resolve_refs(st_obj, layout.get("tokens") or {}, where, on_error)


# ---------------------------------------------------------------------------
# 見出しの罫線（rule.style）
# ---------------------------------------------------------------------------

def tok(tokens, group: str, name: str, default=None):
    g = (tokens or {}).get(group)
    if isinstance(g, dict) and name in g:
        return g[name]
    return default


def apply_rule_style(st: dict, tokens: dict, slide_type: str = "", user_rule=None, title_lines: int = 1) -> None:
    """見出し骨格の罫線 ``st["rule"]`` を rule.style に従って変える（st を直接書き換える）。
    line = 全幅の線（既定・何もしない）/ short = 短い太い帯 / none = 罫線なし / bar-left = タイトルの左の縦帯。
    section / closing のように見出しの位置が違うタイプは bar-left を short にする。

    呼ぶ位置: density・layout_overrides・slide.style を重ねた後、自動フィットの後（resolve_style）。縦帯の位置・高さは
    最終的なタイトルの x / y / 文字サイズ / 行数から決まるので、利用者がタイトルを動かしても帯がついていく。
    ``user_rule`` は利用者（layout_overrides / slide.style）が rule に書いた値。位置・大きさは利用者の明示値を優先する
    （bar-left の h だけは「太さ」として帯の幅に使い、帯の高さにはしない）。none のときは rule ごと消える。
    ``title_lines`` はタイトルが折り返して何行になるか（帯の高さを行数ぶんにする。枠の高さまで）。"""
    style = tok(tokens, "rule", "style", "line")
    rule = st.get("rule")
    if style == "line" or not isinstance(rule, dict):
        return
    if style == "none":
        del st["rule"]
        return
    user_rule = user_rule if isinstance(user_rule, dict) else {}
    length = tok(tokens, "rule", "length", 96)
    title = st.get("title")
    if style == "bar-left" and isinstance(title, dict) and slide_type not in ("section", "closing", "title") \
            and rule.get("w", 0) >= 600 and "x" in title and "y" in title:
        gap = tok(tokens, "rule", "gap", 14)
        bar_w = rule.get("h", 5)
        tsize = title.get("size", 36)
        lines = max(1, int(title_lines or 1))
        full = tsize * 1.35 + (lines - 1) * tsize * title.get("line_height", 1.2)
        rule.update({"x": round(title["x"] - gap - bar_w, 2),
                     "y": round(title["y"] + 4, 2),
                     "w": bar_w,
                     "h": round(min(title.get("h", 64) - 8, full), 2)})
        for k in ("x", "y", "w"):            # 利用者が位置・太さを明示していればそれを優先
            if k in user_rule:
                rule[k] = user_rule[k]
        return
    # short（bar-left の使えないタイプも）: 左端はそのまま、長さだけ縮める。利用者が書いた値はそのまま
    rule["w"] = min(rule.get("w", length), length)
    for k in ("x", "y", "w", "h"):
        if k in user_rule:
            rule[k] = user_rule[k]


# ---------------------------------------------------------------------------
# 描画側の小さな道具（HTML / PPTX が同じ解釈をするための純関数）
# ---------------------------------------------------------------------------

BOLD_FROM = 600       # 太さがこの値以上なら太字（PPTX は太字か否かの 2 値）


def weight_of(r) -> int:
    """領域・要素 r の font-weight の数値。weight が書かれていればそれ、無ければ bold なら 700、なければ 400。"""
    if isinstance(r, dict):
        w = r.get("weight")
        if _is_num(w):
            return int(w)
        if r.get("bold"):
            return 700
    return 400


def is_bold(r) -> bool:
    """太字で描くか（PPTX の b 属性・幅の見積もりの bold 判定）。weight があればそれが優先（600 以上 = 太字）。"""
    if isinstance(r, dict):
        w = r.get("weight")
        if _is_num(w):
            return w >= BOLD_FROM
        return bool(r.get("bold"))
    return False


def apply_bold_override(st: dict, layer) -> None:
    """利用者の層（layout_overrides / slide.style）が領域に ``bold`` を書き、``weight`` を書いていないとき、
    レイアウトや shape 由来の ``weight`` を取り除く（利用者の明示した bold を優先する。st を直接書き換える）。
    bold: false → weight を外して太字なし。bold: true → 既に 600 以上の weight（shape の見出しの太さ）はそのまま、
    それ未満（本文の 400 など）は外して 700 にする。"""
    if not isinstance(layer, dict):
        return
    for rn, rv in layer.items():
        if not isinstance(rv, dict) or "bold" not in rv or "weight" in rv:
            continue
        cur = st.get(rn)
        if not isinstance(cur, dict) or "weight" not in cur:
            continue
        w = cur["weight"]
        if rv["bold"] and _is_num(w) and w >= BOLD_FROM:
            continue
        del cur["weight"]


def tracking_of(r) -> float:
    """字間（em）。無ければ 0。"""
    if isinstance(r, dict):
        t = r.get("tracking")
        if _is_num(t):
            return float(t)
    return 0.0


def width_factor(r) -> float:
    """字間を入れたときの 1 文字あたりの幅の倍率の目安（和文 1em + tracking）。幅の見積もりを 1/この値 に縮めて使う。"""
    t = tracking_of(r)
    return 1.0 + t if t > -0.5 else 0.5


SHADOW_COLOR = "#0F172A"      # 箱の影の色（alpha は tokens.shadow.alpha）


def shadow_params(tokens, mode) -> dict:
    """影の指定（領域の shadow: "none" / "soft"）→ {dx, dy, blur, alpha}。none・不明は空。"""
    if mode != "soft":
        return {}
    return {"dx": 0, "dy": tok(tokens, "shadow", "dy", 4), "blur": tok(tokens, "shadow", "blur", 14),
            "alpha": tok(tokens, "shadow", "alpha", 0.12)}


def apply_text_tokens(elements, tokens, heading_min: float = 22.0):
    """canvas 要素（パターンの展開結果など）の太字の文字に、形トークンの太さ・字間を入れる（要素を直接書き換える）。
    weight.heading / weight.label ≠ 700、tracking.heading ≠ 0 のときだけ変わる（classic は何もしない）。
    heading_min 以上の大きさの太字は見出し（weight.heading・tracking.heading）、それより小さい太字はラベル（weight.label）。"""
    wh, wl = tok(tokens, "weight", "heading", 700), tok(tokens, "weight", "label", 700)
    th = tok(tokens, "tracking", "heading", 0)
    if wh == 700 and wl == 700 and not th:
        return elements

    def walk(o):
        if isinstance(o, dict):
            runs = o.get("runs")
            if isinstance(runs, list):
                for r in runs:
                    if isinstance(r, dict) and r.get("bold") and "weight" not in r:
                        head = _is_num(r.get("size")) and r["size"] >= heading_min
                        w = wh if head else wl
                        if w != 700:
                            r["weight"] = w
                        if head and th:
                            r["tracking"] = th
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(elements)
    return elements


# ---------------------------------------------------------------------------
# パターン（canvas 要素）への形の適用
# ---------------------------------------------------------------------------

def _round_poly(x, y, w, h, r, n=10):
    """角丸四角の外周を折れ線（頂点の列）にする。"""
    import math
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _clip_poly(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman: 折れ線を軸平行の長方形で切り抜く。"""
    def clip(pts, inside, inter):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(inter(q, p))
                out.append(p)
            elif inside(q):
                out.append(inter(q, p))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)

    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        poly = clip(poly, inside, inter)
        if not poly:
            break
    return poly


def clip_bands(elements, tol: float = 0.75):
    """角丸の箱（roundRect）の角にかかる平らな帯（上帯・左帯など）を、箱の角丸の形に切り抜く。
    角丸の箱の外へ帯の直角の角がはみ出すのを防ぐ（shape で角丸を大きくしたとき用）。要素を直接書き換える。"""
    rr = []
    for e in elements:
        if e.get("kind", "shape") == "shape" and e.get("geom") == "roundRect" and isinstance(e.get("adj"), dict):
            rr.append(e)
    if not rr:
        return elements
    for b in elements:
        if b.get("kind", "shape") != "shape" or b.get("geom", "rect") != "rect" or b.get("path") or b.get("text") \
                or not b.get("fill") or b in rr:
            continue
        for e in rr:
            ex, ey, ew, eh = e["x"], e["y"], e["w"], e["h"]
            R = min(ew, eh) * min(max(e["adj"].get("adj", 16667), 0), 50000) / 100000
            bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
            if R <= 0 or bx < ex - tol or by < ey - tol or bx + bw > ex + ew + tol or by + bh > ey + eh + tol:
                continue
            corners = [(ex, ey), (ex + ew, ey), (ex + ew, ey + eh), (ex, ey + eh)]
            if not any(bx - tol <= cx <= bx + bw + tol and by - tol <= cy <= by + bh + tol for cx, cy in corners):
                continue
            poly = _clip_poly(_round_poly(ex, ey, ew, eh, R), bx, by, bx + bw, by + bh)
            if len(poly) < 3:
                continue
            cmds = [["M", round(poly[0][0] - bx, 2), round(poly[0][1] - by, 2)]]
            cmds += [["L", round(px - bx, 2), round(py - by, 2)] for px, py in poly[1:]]
            cmds.append(["Z"])
            b["geom"] = "custom"
            b["path"] = [{"cmds": cmds, "fill": True, "stroke": False}]
            break
    return elements


def _first_run(el):
    tx = el.get("text") if isinstance(el, dict) else None
    for p in (tx or {}).get("paragraphs", []) if isinstance(tx, dict) else []:
        for r in p.get("runs", []) or []:
            if isinstance(r, dict):
                return r
    return None


def apply_pattern_shape(elements, tokens):
    """パターン（frame:"full"）が自前で描く見出し骨格（role: title / rule / eyebrow を付けた要素）に、形トークンを当てる。
    rule.style（short / none / bar-left）・line.rule・radius.rule、eyebrow の大文字化と字間を、見出し骨格（build_deck の chrome）と同じにする。
    あわせて、角丸の箱にかかる帯の切り抜き（radius の token が classic と違うときだけ）。role の印（_role）は最後に消す。"""
    els = [e for e in elements if isinstance(e, dict)]
    roles = {}
    for e in els:
        r = e.get("_role")
        if isinstance(r, str) and r not in roles:
            roles[r] = e
    style = tok(tokens, "rule", "style", "line")
    rule, title, eyebrow = roles.get("rule"), roles.get("title"), roles.get("eyebrow")
    if rule is not None:
        thick = tok(tokens, "line", "rule", rule.get("h", 5))
        rule["h"] = thick
        if style == "none":
            elements[:] = [e for e in elements if e is not rule]
        elif style == "bar-left" and title is not None:
            run = _first_run(title) or {}
            size = run.get("size", 36) if _is_num(run.get("size")) else 36
            gap = tok(tokens, "rule", "gap", 14)
            rule.update({"x": round(title["x"] - gap - thick, 2), "y": round(title["y"] + 4, 2), "w": thick,
                         "h": round(min(title["h"] - 8, size * 1.35), 2)})
        elif style in ("short", "bar-left"):
            rule["w"] = min(rule["w"], tok(tokens, "rule", "length", 96))
        rad = tok(tokens, "radius", "rule", 0)
        if rad and rule in elements:
            rule["geom"], rule["adj"] = "roundRect", {"adj": int(min(50000, rad / max(1, min(rule["w"], rule["h"])) * 100000))}
    if eyebrow is not None:
        for p in ((eyebrow.get("text") or {}).get("paragraphs") or []):
            for r in p.get("runs", []) or []:
                if not isinstance(r, dict):
                    continue
                if tok(tokens, "case", "eyebrow", "none") == "upper" and isinstance(r.get("text"), str):
                    r["text"] = r["text"].upper()
                tr_ = tok(tokens, "tracking", "eyebrow", 0)
                if tr_:
                    r["tracking"] = tr_
                w = tok(tokens, "weight", "eyebrow", 700)
                if r.get("bold") and w != 700:
                    r["weight"] = w
    base = default_tokens().get("radius", {})
    cur = (tokens or {}).get("radius", {}) or {}
    if any(cur.get(k) != v for k, v in base.items()):
        clip_bands(elements)
    for e in els:
        e.pop("_role", None)
    return elements

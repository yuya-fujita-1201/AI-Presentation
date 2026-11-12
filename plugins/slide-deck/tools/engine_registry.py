# -*- coding: utf-8 -*-
"""A 型エンジン（レイアウト関数が canvas 要素列を返し、canvas_engine が HTML と PPTX の両方を描くタイプ）の登録表。

提案書系 8 種（summary / reasons / statement / row_matrix / org / house / cycle / kpi_tree）と kpi / chart が
同じ経路を通る。新しいタイプを足す人がやることは次の 2 つだけ:

  1. エンジンのモジュールの末尾で ``engine_registry.register("名前", layout_fn, validate_fn, ...)`` を 1 回呼ぶ
  2. ``templates/layouts/default.json`` の ``types`` に、見出し骨格（eyebrow / title / rule / lead / body / footer_l / footer_r）と
     タイプ固有トークンの既定値を足す

これで HTML / PPTX の描画、入力検証、未知キー警告、結論帯・出典、検査（check_visual / lint）の免除が効く。
build_deck / proposal_engine / deck_schema / check_visual / lint_deck_text は、タイプ名を直書きせずこの表から引く。

このモジュールは標準ライブラリだけを import する（エンジンが先頭でここを import するので、循環しないため）。
``get`` / ``names`` などの参照系は、初回に同梱エンジン（proposal_engine / dataviz_engine）を読み込んで登録を済ませる。

    register(
        name,                 # タイプ名
        layout,               # layout(slide, st, ctx, body) -> canvas 要素列（body は本文を描ける矩形 dict）
        validate=None,        # validate(slide, i, fail, warn) -> None（必須キー欠落 = fail、詰めすぎ = warn）
        chrome=True,          # 見出し骨格（eyebrow / title / rule / lead / フッター）と結論帯・出典を付けるか
        slide_keys=None,      # スライド直下のタイプ固有キー（共通キーは含めない）。deck_schema の未知キー警告が使う
        self_checked=False,   # 未知キー警告をエンジンの validate が自前で出すなら True（deck_schema 側は黙る）
        sparse_ok=False,      # 余白が多くてよい（check_visual の empty-bottom / empty-band を出さない）
        similar_skip=False,   # 似たスライドが続いても警告しない（check_visual）
        relation=(),          # lint の relation 表: このタイプに合う relation 名（parallel / sequence / …）
        claim_keys=(),        # lint が「主張」として曖昧語・体言止めを検査する、このタイプ固有のキー
        display_keys=(),      # lint が表示文字列として数える、このタイプ固有のキー
        text_skip_keys=(),    # lint が本文として検査しないキー（列挙値・単位・数値指定など）
        volume_exempt=False,  # 文字量（density）の検査をしない
        rhythm_exempt=False,  # 同じタイプが続いても警告しない
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class EngineSpec:
    name: str
    layout: Callable
    validate: Optional[Callable] = None
    chrome: bool = True
    slide_keys: frozenset = frozenset()
    self_checked: bool = False
    sparse_ok: bool = False
    similar_skip: bool = False
    relation: tuple = ()
    claim_keys: tuple = ()
    display_keys: tuple = ()
    text_skip_keys: tuple = ()
    volume_exempt: bool = False
    rhythm_exempt: bool = False


_REGISTRY: dict = {}
_LOADING = False
_LOADED = False


def register(name: str, layout: Callable, validate: Optional[Callable] = None, **props) -> EngineSpec:
    """タイプを登録する（同名は上書き）。props は EngineSpec の項目（上の docstring 参照）。"""
    for k in ("slide_keys",):
        if k in props and props[k] is not None:
            props[k] = frozenset(props[k])
        elif k in props:
            props[k] = frozenset()
    for k in ("relation", "claim_keys", "display_keys", "text_skip_keys"):
        if k in props:
            props[k] = tuple(props[k] or ())
    spec = EngineSpec(name=name, layout=layout, validate=validate, **props)
    _REGISTRY[name] = spec
    return spec


def _ensure() -> None:
    """同梱エンジンを読み込んで登録を済ませる（初回だけ）。エンジンは import の末尾で register を呼ぶ。"""
    global _LOADING, _LOADED
    if _LOADED or _LOADING:
        return
    _LOADING = True
    try:
        import proposal_engine  # noqa: F401
        import dataviz_engine  # noqa: F401
        _LOADED = True
    finally:
        _LOADING = False


def get(name) -> Optional[EngineSpec]:
    _ensure()
    return _REGISTRY.get(name) if isinstance(name, str) else None


def has(name) -> bool:
    return get(name) is not None


def names() -> tuple:
    """登録済みのタイプ名（登録順）。"""
    _ensure()
    return tuple(_REGISTRY)


def specs() -> dict:
    _ensure()
    return dict(_REGISTRY)


def types_where(attr: str) -> frozenset:
    """属性が真（または空でない）のタイプ名の集合。例: types_where("sparse_ok")。"""
    _ensure()
    return frozenset(n for n, s in _REGISTRY.items() if getattr(s, attr))


def relation_types() -> dict:
    """relation 名 → このレジストリのタイプ名のリスト。lint の RELATION_TYPES に足す。"""
    _ensure()
    out: dict = {}
    for n, s in _REGISTRY.items():
        for r in s.relation:
            out.setdefault(r, []).append(n)
    return out


def validate_slide(slide: dict, i: int, fail, warn, **kw) -> None:
    spec = get(slide.get("type"))
    if spec is not None and spec.validate is not None:
        spec.validate(slide, i, fail, warn, **kw)

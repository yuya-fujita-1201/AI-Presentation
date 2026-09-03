#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archify（https://github.com/tt-a1i/archify , MIT）の JSON IR を、このプラグインの
スライド JSON（deck.json の 1 スライド分）に変換する CLI。

Archify は「AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して
描く」方式の図解 IR で、diagram_engine.py はその方式を取り込んだもの（同ファイル冒頭の
docstring 参照）。本ツールは Archify の 5 つの diagram_type を、本プラグインの対応する
ネイティブ図解タイプに変換する:

    architecture → architecture      workflow → swimlane
    dataflow     → dataflow          sequence → sequence
    lifecycle    → lifecycle

Archify 固有の絶対座標・幾何指定（pos/size/via/labelAt/labelDx/labelDy/labelSegment/
channelX/channelY/route/width/bias/cornerRadius 等）は、本プラグインが自動配線・自動配置
するため捨てる。何を捨てたかは stderr に note: で要約する（1 行ずつ）。

architecture だけは componentに pos/size（絶対px座標）しか無いことが多いため、中心座標を
x/y それぞれでクラスタリングして row/col（グリッド位置）に量子化する（--tolerance）。

使い方:
    python tools/archify_import.py <archify.json>                   # 変換結果を stdout に JSON 出力
    python tools/archify_import.py <archify.json> --eyebrow "TYPE / architecture"
    python tools/archify_import.py <archify.json> --tolerance 70    # architecture の座標量子化の距離閾値(px)
    python tools/archify_import.py <archify.json> --out slide.json  # 変換結果をファイルに保存（stdout には出さない）
    python tools/archify_import.py <archify.json> --into <deck_dir> # deck.json の slides 末尾に追記して保存
                                                                     # （deck.json が無ければ新規作成）

変換結果は必ず diagram_engine.validate_grid_diagram（architecture/dataflow/lifecycle）/
layout_sequence（sequence）/ build_deck._validate_swimlane（swimlane、幾何診断込み）で検証し、
診断を stderr に出す。error が 1 件でもあれば exit code 1（この場合も stdout には変換結果の
JSON を出す＝壊れたままの出力を見て deck.json 側で直せるようにするため）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import build_deck  # noqa: E402
import check_diagram  # noqa: E402
import diagram_engine as de  # noqa: E402

DEFAULT_TOLERANCE = 70.0
MAX_CLUSTER_ATTEMPTS = 3

TYPE_MAP = {
    "architecture": "architecture",
    "workflow": "swimlane",
    "dataflow": "dataflow",
    "sequence": "sequence",
    "lifecycle": "lifecycle",
}


# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------

def load_archify(path: Path) -> dict:
    if not path.exists():
        build_deck.fail(f"{path} が見つかりません")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        build_deck.fail(f"{path} の JSON が不正です: {e}")
    except PermissionError:
        build_deck.fail(f"{path} を読み込めません（権限がありません）")


def _copy_if(src: dict, dst: dict, key: str, dst_key: str = None) -> None:
    """src[key] が存在し None でなければ dst[dst_key or key] にコピーする。"""
    if key in src and src[key] is not None:
        dst[dst_key or key] = src[key]


def _note_dropped(items, keys, notes: list, template: str) -> None:
    """items（辞書のリスト）内で keys のいずれかを持つ件数を数え、1 件以上あれば
    notes に 1 行だけ追記する（1 種類の情報につき 1 行。個体ごとには出さない）。
    template は {key}（フィールド名）と {count}（件数）を埋め込む。"""
    counts = {k: 0 for k in keys}
    for it in items:
        if not isinstance(it, dict):
            continue
        for k in keys:
            if it.get(k) is not None:
                counts[k] += 1
    for k in keys:
        if counts[k]:
            notes.append(template.format(key=k, count=counts[k]))


def cards_to_notes(cards) -> str:
    """cards（結論カード）を notes（スピーカーノート。build_deck では HTML でのみ表示され、
    PPTX には出力されない）用のテキストに変換する。「■タイトル: 項目1 / 項目2」の形。"""
    lines = []
    for c in cards or []:
        if not isinstance(c, dict):
            continue
        items = c.get("items") or []
        lines.append(f"■{c.get('title', '')}: " + " / ".join(str(i) for i in items))
    return "\n".join(lines)


def convert_edge_common(e: dict, extra_keep: tuple = (), add_dashed_style: bool = False) -> dict:
    """from/to/label/variant（+ extra_keep で指定した追加フィールド）をそのまま写し、
    fromSide/toSide を from_side/to_side にリネームする（本プラグインの全図解タイプ共通の
    エッジ表現）。add_dashed_style=True のときは variant が dashed なら style も併記する
    （swimlane の edges はドキュメント上 style で破線を表すため。workflow 用）。"""
    out: dict = {}
    _copy_if(e, out, "from")
    _copy_if(e, out, "to")
    _copy_if(e, out, "label")
    variant = e.get("variant")
    if variant:
        out["variant"] = variant
    for k in extra_keep:
        _copy_if(e, out, k)
    if e.get("fromSide"):
        out["from_side"] = e["fromSide"]
    if e.get("toSide"):
        out["to_side"] = e["toSide"]
    if add_dashed_style and variant == "dashed":
        out["style"] = "dashed"
    return out


# ---------------------------------------------------------------------------
# architecture: 絶対座標（pos/size）→ グリッド位置（row/col）の量子化
# ---------------------------------------------------------------------------

def cluster_1d(values, tolerance: float) -> dict:
    """values: [(id, coordinate), ...] を 1 次元でクラスタリングし、
    id -> クラスタ index（0 始まり、座標の小さい順）を返す。

    ソート順に隣り合う値どうしの距離が tolerance 未満なら同じクラスタにする
    （チェイン式 / 単連結クラスタリング）。そのため一つのクラスタの中で最初と最後の値の
    距離が tolerance を超えることもある（a-b, b-c がそれぞれ近ければ a-c が遠くても
    a/b/c は同じクラスタになる）。"""
    if not values:
        return {}
    ordered = sorted(values, key=lambda p: p[1])
    idx: dict = {}
    cluster = 0
    idx[ordered[0][0]] = 0
    prev = ordered[0][1]
    for nid, v in ordered[1:]:
        if v - prev >= tolerance:
            cluster += 1
        idx[nid] = cluster
        prev = v
    return idx


def quantize_positions(centers: dict, tolerance: float, notes: list, reserved: frozenset = frozenset()) -> dict:
    """centers: {id: (cx, cy)} を x/y それぞれでクラスタリングし {id: (row, col)} を返す。

    同じ (row, col) に複数ノード（または reserved で渡した既存の位置）が入ったら、
    tolerance を半分にして再クラスタリングする（最大 MAX_CLUSTER_ATTEMPTS 回）。
    それでも衝突が残る場合は、衝突したノードの col を空いているセルが見つかるまで
    +1 ずつずらす（決定論的に id の登場順で処理する）。衝突を解消したら notes に記録する。"""
    ids = list(centers.keys())
    tol = tolerance
    row_of: dict = {}
    col_of: dict = {}
    collided = True
    for _attempt in range(MAX_CLUSTER_ATTEMPTS):
        col_of = cluster_1d([(i, centers[i][0]) for i in ids], tol)
        row_of = cluster_1d([(i, centers[i][1]) for i in ids], tol)
        occupied = set(reserved)
        collided = False
        for i in ids:
            key = (row_of[i], col_of[i])
            if key in occupied:
                collided = True
            else:
                occupied.add(key)
        if not collided:
            break
        tol /= 2.0
    if collided:
        notes.append(
            f"architecture: tolerance を {MAX_CLUSTER_ATTEMPTS} 回半分にしても同じマス（row, col）に"
            "複数ノードが残ったため、衝突したノードの col を +1 ずつずらしました（配置がやや不自然に"
            "なる場合は deck.json の該当ノードに明示的な row/col を書いて調整してください）"
        )
        occupied = set(reserved)
        for i in ids:
            key = (row_of[i], col_of[i])
            while key in occupied:
                col_of[i] += 1
                key = (row_of[i], col_of[i])
            occupied.add(key)
    return {i: (row_of[i], col_of[i]) for i in ids}


def convert_architecture(ir: dict, tolerance: float, notes: list) -> dict:
    if ir.get("layout"):
        notes.append("architecture: layout（グリッド原点・セル寸法の指定）は自動配置に置き換えるため捨てました")

    components = ir.get("components") or []
    explicit: dict = {}
    centers: dict = {}
    no_pos_ids = []
    for c in components:
        nid = c.get("id")
        row, col = c.get("row"), c.get("col")
        if isinstance(row, int) and not isinstance(row, bool) and isinstance(col, int) and not isinstance(col, bool):
            explicit[nid] = (row, col)
            continue
        pos = c.get("pos")
        size = c.get("size") or [0, 0]
        if pos:
            centers[nid] = (pos[0] + size[0] / 2.0, pos[1] + size[1] / 2.0)
        else:
            centers[nid] = (0.0, 0.0)
            no_pos_ids.append(nid)
    if no_pos_ids:
        notes.append(f"architecture: pos も row/col も無いノード {', '.join(no_pos_ids)} を row=0/col=0 付近に置きました")

    positions = dict(explicit)
    if centers:
        clustered = quantize_positions(centers, tolerance, notes, reserved=frozenset(explicit.values()))
        positions.update(clustered)
        notes.append(
            f"architecture: {len(centers)} 個のノードの pos/size（絶対座標）を tolerance={tolerance:g}px で"
            " row/col（グリッド位置）に量子化しました。自動配線用の目安になり、元の座標とは一致しません"
        )

    nodes = []
    for c in components:
        nid = c.get("id")
        row, col = positions.get(nid, (0, 0))
        node = {"id": nid, "type": c.get("type"), "label": c.get("label", ""), "row": row, "col": col}
        _copy_if(c, node, "sublabel")
        _copy_if(c, node, "tag")
        nodes.append(node)

    kind_map = {"region": "region", "security-group": "security"}
    groups = []
    for b in ir.get("boundaries") or []:
        g = {"label": b.get("label", ""), "kind": kind_map.get(b.get("kind"), "generic"),
             "nodes": list(b.get("wraps") or [])}
        _copy_if(b, g, "pad")
        groups.append(g)

    edges = [convert_edge_common(conn) for conn in (ir.get("connections") or [])]

    _note_dropped(components, ("brand", "sources"), notes,
                  "architecture: components の {key} 指定 {count} 件を捨てました")
    _note_dropped(ir.get("connections") or [],
                  ("id", "route", "via", "labelAt", "labelDx", "labelDy", "labelSegment", "width"),
                  notes, "architecture: connections の {key} 指定 {count} 件を捨てました（自動配線に置き換え）")

    content = {"nodes": nodes}
    if groups:
        content["groups"] = groups
    content["edges"] = edges
    return content


# ---------------------------------------------------------------------------
# workflow → swimlane
# ---------------------------------------------------------------------------

def convert_workflow(ir: dict, notes: list) -> dict:
    lane_list = ir.get("lanes") or []
    lane_index = {ln.get("id"): i for i, ln in enumerate(lane_list)}
    lanes = [{"name": ln.get("label", "")} for ln in lane_list]

    raw_nodes = ir.get("nodes") or []
    nodes = []
    for nd in raw_nodes:
        lane_id = nd.get("lane")
        lane_i = lane_index.get(lane_id)
        if lane_i is None:
            lane_i = 0
            notes.append(f"workflow: ノード '{nd.get('id')}' の lane '{lane_id}' が lanes に無いため lane 0 にしました")
        nodes.append({
            "id": nd.get("id"), "lane": lane_i, "col": nd.get("col", 0),
            "shape": "task", "variant": "onother", "text": nd.get("label", ""),
        })

    maxcol = max([nd.get("col", 0) for nd in raw_nodes] + [0])
    phase_list = ir.get("phases") or []
    maxcol = max([maxcol] + [p.get("toCol", 0) for p in phase_list])
    cols = maxcol + 1
    phases = [""] * cols
    for p in phase_list:
        fc = p.get("fromCol", 0)
        if 0 <= fc < cols:
            phases[fc] = p.get("label", "")

    edges = [convert_edge_common(e, add_dashed_style=True) for e in (ir.get("edges") or [])]

    if ir.get("groups"):
        notes.append(f"workflow: groups（{len(ir['groups'])} 件）は swimlane 未対応のため捨てました")
    if ir.get("mainPath"):
        notes.append("workflow: mainPath（主経路の強調）は捨てました（swimlane は主経路の強調に未対応）")
    _note_dropped(lane_list, ("variant",), notes,
                  "workflow: lanes の {key} 指定 {count} 件を捨てました（swimlane はレーンの強調種別に未対応）")
    _note_dropped(phase_list, ("variant",), notes, "workflow: phases の {key} 指定 {count} 件を捨てました")
    _note_dropped(raw_nodes, ("type", "sublabel", "tag", "width", "height", "yOffset", "brand"), notes,
                  "workflow: nodes の {key} 指定 {count} 件を捨てました"
                  "（swimlane の task ノードは text のみで、type/sublabel/tag 等は表現できないため）")
    _note_dropped(ir.get("edges") or [],
                  ("id", "role", "route", "via", "labelAt", "labelDx", "labelDy", "labelSegment",
                   "channelX", "channelY", "bias", "width"),
                  notes, "workflow: edges の {key} 指定 {count} 件を捨てました（自動配線に置き換え）")

    return {"legend": False, "lanes": lanes, "phases": phases, "cols": cols, "nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# dataflow
# ---------------------------------------------------------------------------

def convert_dataflow(ir: dict, notes: list) -> dict:
    stages = [s.get("label", "") for s in (ir.get("stages") or [])]
    raw_nodes = ir.get("nodes") or []
    nodes = []
    for nd in raw_nodes:
        node = {"id": nd.get("id"), "type": nd.get("type"), "label": nd.get("label", ""),
                "col": nd.get("stage", 0), "row": nd.get("row", 0)}
        _copy_if(nd, node, "sublabel")
        _copy_if(nd, node, "tag")
        nodes.append(node)

    edges = [convert_edge_common(f, extra_keep=("classification",)) for f in (ir.get("flows") or [])]

    _note_dropped(raw_nodes, ("width", "height", "yOffset", "brand"), notes,
                  "dataflow: nodes の {key} 指定 {count} 件を捨てました")
    _note_dropped(ir.get("flows") or [],
                  ("id", "route", "via", "labelAt", "labelDx", "labelDy", "labelSegment", "channelX", "channelY", "width"),
                  notes, "dataflow: flows の {key} 指定 {count} 件を捨てました（自動配線に置き換え）")

    return {"stages": stages, "nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# sequence
# ---------------------------------------------------------------------------

def convert_sequence(ir: dict, notes: list) -> dict:
    participants = []
    for p in ir.get("participants") or []:
        part = {"id": p.get("id"), "type": p.get("type"), "label": p.get("label", "")}
        _copy_if(p, part, "sublabel")
        participants.append(part)
    _note_dropped(ir.get("participants") or [], ("brand",), notes,
                  "sequence: participants の {key} 指定 {count} 件を捨てました")

    raw_msgs = list(ir.get("messages") or [])
    sorted_msgs = sorted(raw_msgs, key=lambda m: m.get("y", 0))
    ys = [m.get("y", 0) for m in sorted_msgs]
    messages = []
    for m in sorted_msgs:
        msg: dict = {}
        _copy_if(m, msg, "id")
        _copy_if(m, msg, "from")
        _copy_if(m, msg, "to")
        _copy_if(m, msg, "label")
        _copy_if(m, msg, "variant")
        messages.append(msg)
    if raw_msgs:
        notes.append(f"sequence: messages（{len(raw_msgs)} 件）を y 座標順に並べ替え、y 座標そのものは捨てました"
                     "（表示位置は本プラグインが自動で割り付けます）")
    _note_dropped(raw_msgs, ("note",), notes, "sequence: messages の {key} 指定 {count} 件を捨てました")

    def y_to_range(from_y, to_y):
        """Archify の y 座標範囲を「その範囲に入る最初/最後のメッセージ index」に変換する。"""
        lo, hi = (from_y, to_y) if from_y <= to_y else (to_y, from_y)
        first_ge = next((i for i, y in enumerate(ys) if y >= lo), len(ys) - 1)
        last_le = -1
        for i, y in enumerate(ys):
            if y <= hi:
                last_le = i
        if last_le < 0:
            last_le = 0
        if last_le < first_ge:
            first_ge, last_le = last_le, first_ge
        return first_ge, last_le

    activations = []
    for a in ir.get("activations") or []:
        fi, ti = y_to_range(a.get("from", 0), a.get("to", 0))
        activations.append({"participant": a.get("participant"), "from": fi, "to": ti})
    _note_dropped(ir.get("activations") or [], ("type",), notes,
                  "sequence: activations の {key} 指定 {count} 件を捨てました")

    segments = []
    for s in ir.get("segments") or []:
        fi, ti = y_to_range(s.get("from", 0), s.get("to", 0))
        segments.append({"from": fi, "to": ti, "label": s.get("label", "")})

    content = {"participants": participants, "messages": messages}
    if activations:
        content["activations"] = activations
    if segments:
        content["segments"] = segments
    return content


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------

def convert_lifecycle(ir: dict, notes: list) -> dict:
    lane_list = ir.get("lanes") or []
    lane_index = {ln.get("id"): i for i, ln in enumerate(lane_list)}
    lanes = [{"name": ln.get("label", "")} for ln in lane_list]

    raw_states = ir.get("states") or []
    states = []
    for st in raw_states:
        lane_id = st.get("lane")
        lane_i = lane_index.get(lane_id)
        if lane_i is None:
            lane_i = 0
            notes.append(f"lifecycle: 状態 '{st.get('id')}' の lane '{lane_id}' が lanes に無いため lane 0 にしました")
        state = {"id": st.get("id"), "kind": st.get("type"), "label": st.get("label", ""),
                 "lane": lane_i, "col": st.get("col", 0)}
        _copy_if(st, state, "sublabel")
        _copy_if(st, state, "tag")
        _copy_if(st, state, "step")
        states.append(state)

    transitions = [convert_edge_common(t) for t in (ir.get("transitions") or [])]

    _note_dropped(raw_states, ("width", "height", "yOffset", "brand"), notes,
                  "lifecycle: states の {key} 指定 {count} 件を捨てました")
    _note_dropped(ir.get("transitions") or [],
                  ("id", "note", "route", "via", "labelAt", "labelDx", "labelDy", "labelSegment",
                   "channelX", "channelY", "cornerRadius", "width"),
                  notes, "lifecycle: transitions の {key} 指定 {count} 件を捨てました（自動配線に置き換え）")

    return {"lanes": lanes, "states": states, "transitions": transitions}


# ---------------------------------------------------------------------------
# ディスパッチ・共通フィールド（title/lead/eyebrow/notes）
# ---------------------------------------------------------------------------

CONVERTERS = {
    "architecture": lambda ir, args, notes: convert_architecture(ir, args.tolerance, notes),
    "workflow": lambda ir, args, notes: convert_workflow(ir, notes),
    "dataflow": lambda ir, args, notes: convert_dataflow(ir, notes),
    "sequence": lambda ir, args, notes: convert_sequence(ir, notes),
    "lifecycle": lambda ir, args, notes: convert_lifecycle(ir, notes),
}


def convert(ir: dict, args, notes: list) -> dict:
    dtype = ir.get("diagram_type")
    if dtype not in TYPE_MAP:
        build_deck.fail(
            f"未対応の diagram_type です: {dtype!r}（対応: {', '.join(TYPE_MAP)}）"
        )
    content = CONVERTERS[dtype](ir, args, notes)

    meta = ir.get("meta") or {}
    slide = {"type": TYPE_MAP[dtype]}
    if getattr(args, "eyebrow", None):
        slide["eyebrow"] = args.eyebrow
    slide["title"] = meta.get("title", "")
    if meta.get("subtitle"):
        slide["lead"] = meta["subtitle"]
    slide.update(content)

    notes_text = cards_to_notes(ir.get("cards"))
    if notes_text:
        slide["notes"] = notes_text
        notes.append("cards（結論カード）は notes（スピーカーノート。HTML でのみ表示）に変換しました")

    meta_extra = sorted(k for k in meta if k not in ("title", "subtitle"))
    if meta_extra:
        notes.append(f"meta の {', '.join(meta_extra)} は Archify 固有の表示設定のため捨てました")

    return slide


# ---------------------------------------------------------------------------
# 検証（diagram_engine / build_deck の既存チェックをそのまま利用する）
# ---------------------------------------------------------------------------

def resolve_validation_style(slide: dict, deck_dir: Path = None) -> dict:
    """検証用の style（resolve_style の戻り値）を作る。--into で既存デッキが指定されて
    いればそのデッキの layout/layout_overrides を、無ければ同梱の default レイアウトを使う。"""
    if deck_dir is not None and (deck_dir / "deck.json").exists():
        deck, _theme, layout = build_deck.load_deck(deck_dir)
    else:
        deck = {}
        layout = build_deck.load_json(ROOT / "templates" / "layouts" / "default.json")
    return build_deck.resolve_style(layout, deck, slide)


def validate_slide(slide: dict, deck_dir: Path = None) -> bool:
    """slide を check_diagram.diagnose_slide（= validate_grid_diagram / layout_sequence /
    build_deck._validate_swimlane を内部で呼ぶ）で検証し、診断を stderr に出す。
    error が 1 件も無ければ True。"""
    st = resolve_validation_style(slide, deck_dir)
    diags = check_diagram.diagnose_slide(slide, st, slide.get("type"))
    has_error = False
    for d in diags:
        level = d.get("level")
        mark = {"error": "error", "warning": "warning", "info": "note"}.get(level, level)
        print(f"{mark}: {de.format_diagnostic(d)}", file=sys.stderr)
        if level == "error":
            has_error = True
    return not has_error


def save_into_deck(slide: dict, deck_dir: Path, ir: dict) -> None:
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck_path = deck_dir / "deck.json"
    if deck_path.exists():
        deck = build_deck.load_json(deck_path)
        if not isinstance(deck, dict):
            build_deck.fail(f"{deck_path} の形式が不正です（トップレベルはオブジェクトである必要があります）")
        deck.setdefault("slides", [])
        if not isinstance(deck["slides"], list):
            build_deck.fail(f"{deck_path} の slides は配列である必要があります")
    else:
        deck = {"meta": {"title": (ir.get("meta") or {}).get("title", "")}, "slides": []}
    deck["slides"].append(slide)
    deck_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_deck.note(f"{deck_path} に追記しました（{len(deck['slides'])}枚目 type={slide.get('type')}）")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    build_deck.setup_console()
    ap = argparse.ArgumentParser(
        description="Archify の JSON IR を slide-deck プラグインのスライド JSON（1 スライド分）に変換する")
    ap.add_argument("archify_json", metavar="archify.json", help="Archify の diagram JSON ファイル")
    ap.add_argument("--eyebrow", help="スライドの eyebrow（タイトル上の小さなサブタイトル）")
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                     help=f"architecture の pos/size 座標を row/col に量子化する距離閾値(px)（既定 {DEFAULT_TOLERANCE:g}）")
    ap.add_argument("--into", metavar="DECK_DIR",
                     help="このディレクトリの deck.json の slides 末尾に追記して保存する（無ければ新規作成）")
    ap.add_argument("--out", metavar="FILE", help="変換結果のスライド JSON をこのファイルに保存する（省略時は stdout）")
    args = ap.parse_args()

    ir = load_archify(Path(args.archify_json))
    if not isinstance(ir, dict):
        build_deck.fail(f"{args.archify_json} の形式が不正です（トップレベルはオブジェクトである必要があります）")

    notes: list = []
    slide = convert(ir, args, notes)
    for n in notes:
        build_deck.note(n)

    deck_dir = Path(args.into).resolve() if args.into else None
    ok = validate_slide(slide, deck_dir)

    payload = json.dumps(slide, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        build_deck.note(f"変換結果を書き出しました: {args.out}")
    elif not args.into:
        print(payload)

    if args.into:
        save_into_deck(slide, deck_dir, ir)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

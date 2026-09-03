#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diagram_engine.py — ネイティブ図解タイプ共通のジオメトリ・自動配線・診断エンジン。

Archify（https://github.com/tt-a1i/archify , MIT）の方式
「AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して描く」を
Python で取り込んだもの。build_deck.py（HTML / PPTX）と check_diagram.py（診断 CLI）が共用する。
外部依存なし（Python 3.9+）。

役割:
  - グリッド配置: 領域を rows×cols のセルに分割し、ノード箱をセル中央に置く
  - 自動配線: 格子（列間・行間のガター＋ノード中心線）上で最短の直交経路を探索し、
    途中のノードを横切らない経路を選ぶ。同じ回廊を通る複数線・同じ辺から出る複数線は
    等間隔にずらす（Archify の Automatic Port Spread / corridor に相当）
  - ラベル配置: 最長セグメントの脇に背景ピル付きで置き、ノード・他ラベルとの衝突を避ける
  - 診断: 重複 id / 未知 id / セル衝突 / 横切り / ラベル衝突 / 交差 / 文字あふれ / 密度 などを
    Archify の diagnostics と同じ形（code / level / subject / evidence / fixes）で返す
  - sequence（シーケンス図）専用のレイアウト

座標はすべて 1280×720 キャンバスの絶対 px。HTML と PPTX は同じジオメトリから描く。
"""

from __future__ import annotations

import heapq
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]

# ---------------------------------------------------------------------------
# 定数（Archify の Readable v2 / showcase 規約に倣った閾値）
# ---------------------------------------------------------------------------

CLEARANCE = 2.0          # ノードを横切る判定のクリアランス（px）
MIN_SEGMENT = 8.0        # これ未満のセグメントは「リズム」違反（info）
MIN_INTERIOR = 16.0      # 内側の折れセグメントの最小長
CORRIDOR_STEP = 7.0      # 同一回廊で複数線をずらす間隔（px）
MAX_SPREAD = 24.0        # 同一回廊での広がりの上限（px。レーン/列のマージンに収める）
LABEL_PAD_X = 5.0        # ラベルピルの左右パディング
LABEL_PAD_Y = 1.5        # ラベルピルの上下パディング
LABEL_GAP = 4.0          # 線とラベルピルの隙間
LABEL_BREATH = 2.0       # ラベル衝突判定時に周囲へ足す余白（px）
TOUCH_TOL = 3.0          # この深さまでの接触は衝突とみなさない（px）
BEND_PENALTY = 26.0      # 折れ 1 回のコスト（px 換算）
CROSS_PENALTY = 30.0     # 既存の線と交差 1 回のコスト（px 換算）
CENTER_TRACK_PENALTY = 0.35   # ノード中心線トラックを通る際の追加コスト率（ガター優先）
SHARED_TRACK_PENALTY = 0.25   # 既に他の線が通ったトラックの追加コスト率（回廊の分散）
BACK_SIDE_PENALTY = 60.0      # 相手と反対側の辺から出る／入るときのコスト
MAX_PRIMARY_NODES = 12        # これを超えると too-dense（Archify: at most 12 primary nodes）
MAX_COLS = 6
MAX_MESSAGES = 12
MAX_PARTICIPANTS = 7

COMPONENT_TYPES = ("frontend", "backend", "database", "cloud", "security", "messagebus", "external", "generic")
NODE_VARIANTS = ("default", "emphasis", "security", "dashed", "muted")
EDGE_VARIANTS = ("default", "emphasis", "security", "dashed", "return")
LIFECYCLE_KINDS = ("start", "active", "waiting", "decision", "success", "failure", "neutral", "external")
SIDES = ("left", "right", "top", "bottom")

TYPE_LABELS_JA = {
    "frontend": "フロント", "backend": "バックエンド", "database": "DB", "cloud": "クラウド",
    "security": "セキュリティ", "messagebus": "メッセージ基盤", "external": "外部", "generic": "コンポーネント",
}


# ---------------------------------------------------------------------------
# 文字幅の推定（build_deck.estimate_lines と同じ規則: 全角 1.0 / 半角 0.55）
# ---------------------------------------------------------------------------

def char_ratio(ch: str) -> float:
    """1 文字の幅（フォントサイズに対する比）。全角 1.0、英大文字・数字 0.68、その他半角 0.55、空白 0.3。"""
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 1.0
    if ch == " ":
        return 0.3
    if ch.isupper() or ch.isdigit():
        return 0.68
    return 0.55


def text_width(text, size: float) -> float:
    """テキスト 1 行の推定幅（px）。"""
    return sum(size * char_ratio(c) for c in str(text or ""))


BREAK_AFTER = "・、。／/をのはがにとで"   # 日本語の自然な折り返し位置（この文字の直後で切ってよい）


def _tokens(line: str) -> List[str]:
    """英数字の連なり（単語）は 1 トークン、空白は 1 トークン、それ以外（CJK 等）は 1 文字 1 トークン。"""
    out: List[str] = []
    cur = ""
    for ch in line:
        if ch.isascii() and not ch.isspace():
            cur += ch
            continue
        if cur:
            out.append(cur)
            cur = ""
        out.append(ch)
    if cur:
        out.append(cur)
    return out


def wrap_text(text, size: float, width: float) -> List[str]:
    """幅 width に収まるよう折り返した行のリスト（明示の改行も尊重）。
    - 英単語（英数字の連なり）は途中で切らない（単語だけで幅を超える場合のみ文字単位で切る）
    - 日本語は直近 3 文字以内に「・」「、」や助詞（を の は が に と で）があればその直後で切る"""
    out: List[str] = []
    width = max(1.0, width)
    for raw in str(text or "").split("\n"):
        if raw == "":
            out.append("")
            continue
        line = ""
        for tok in _tokens(raw):
            if not line and tok.isspace():
                continue
            cand = line + tok
            if text_width(cand, size) <= width or not line:
                if text_width(cand, size) > width and len(tok) > 1:
                    # 単語だけで幅を超える: 文字単位で分割
                    for ch in tok:
                        if line and text_width(line + ch, size) > width:
                            out.append(line)
                            line = ""
                        line += ch
                else:
                    line = cand
                continue
            # 折り返し: 直近 3 文字以内の自然な切れ目を探す（英単語の内部は対象外）
            cut = len(line)
            for back in range(1, 4):
                idx = len(line) - back
                if idx <= 0:
                    break
                if line[idx - 1] in BREAK_AFTER and idx < len(line):
                    cut = idx
                    break
            head, tail = line[:cut], line[cut:]
            out.append(head.rstrip())
            line = (tail + tok).lstrip()
        if line:
            out.append(line)
    return out or [""]


def fit_font_size(text, size: float, width: float, height: float, line_h: float = 1.15,
                  min_size: float = 10.0, max_lines: Optional[int] = None) -> Tuple[float, List[str]]:
    """箱（width×height）に収まる最大のフォントサイズと折り返し結果を返す（min_size まで縮小）。
    ほぼ同じ大きさ（既定 −1px まで）で 1 行に収まるなら 1 行を優先し、そうでなければサイズを保ったまま折り返す。"""
    for s1 in (float(size), float(size) - 1):
        if s1 >= min_size and text_width(text, s1) <= width and s1 * line_h <= height + 0.5 \
                and "\n" not in str(text or ""):
            return s1, [str(text or "")]
    s = float(size)
    while True:
        lines = wrap_text(text, s, width)
        ok_h = len(lines) * s * line_h <= height + 0.5
        ok_n = max_lines is None or len(lines) <= max_lines
        if (ok_h and ok_n) or s <= min_size:
            return s, lines
        s -= 1


# ---------------------------------------------------------------------------
# 矩形・セグメントの幾何
# ---------------------------------------------------------------------------

def rect_of(x, y, w, h) -> dict:
    return {"x": float(x), "y": float(y), "w": float(w), "h": float(h)}


def inflate(r: dict, d: float) -> dict:
    return rect_of(r["x"] - d, r["y"] - d, r["w"] + 2 * d, r["h"] + 2 * d)


def rects_overlap(a: dict, b: dict, tol: float = 0.0) -> bool:
    return (a["x"] + tol < b["x"] + b["w"] and b["x"] + tol < a["x"] + a["w"]
            and a["y"] + tol < b["y"] + b["h"] and b["y"] + tol < a["y"] + a["h"])


def penetration(a: dict, b: dict) -> float:
    """2 矩形の重なりの「浅い方の深さ」（px）。0 以下なら重なっていない。"""
    ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return min(ox, oy) if ox > 0 and oy > 0 else 0.0


def overlap_area(a: dict, b: dict) -> float:
    ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return ox * oy if ox > 0 and oy > 0 else 0.0


def segment_hits_rect(p: Point, q: Point, r: dict, clearance: float = CLEARANCE) -> bool:
    """直交セグメント p-q が矩形 r（clearance 分ふくらませた）の内部を通るか。
    端点が矩形の境界上にあるだけ（接する）の場合は通ったとみなさない。"""
    rr = inflate(r, clearance)
    x1, y1 = p
    x2, y2 = q
    if abs(y1 - y2) < 1e-6:  # 水平
        if not (rr["y"] < y1 < rr["y"] + rr["h"]):
            return False
        lo, hi = min(x1, x2), max(x1, x2)
        return lo < rr["x"] + rr["w"] and hi > rr["x"]
    if abs(x1 - x2) < 1e-6:  # 垂直
        if not (rr["x"] < x1 < rr["x"] + rr["w"]):
            return False
        lo, hi = min(y1, y2), max(y1, y2)
        return lo < rr["y"] + rr["h"] and hi > rr["y"]
    # 斜め（via 指定の異常ケース）: 端点の外接矩形で近似
    bx = rect_of(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    return rects_overlap(bx, rr)


def segments_cross(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """直交セグメント同士の「真の交差」（端点接触・同一直線上は除く）。"""
    ah = abs(a1[1] - a2[1]) < 1e-6
    bh = abs(b1[1] - b2[1]) < 1e-6
    if ah == bh:
        return False
    if ah:
        h1, h2, v1, v2 = a1, a2, b1, b2
    else:
        h1, h2, v1, v2 = b1, b2, a1, a2
    y = h1[1]
    x = v1[0]
    hx_lo, hx_hi = min(h1[0], h2[0]), max(h1[0], h2[0])
    vy_lo, vy_hi = min(v1[1], v2[1]), max(v1[1], v2[1])
    return hx_lo + 0.5 < x < hx_hi - 0.5 and vy_lo + 0.5 < y < vy_hi - 0.5


def collinear_overlap(a1: Point, a2: Point, b1: Point, b2: Point) -> float:
    """同一直線上の 2 セグメントの重なり長（重ならなければ 0）。"""
    ah = abs(a1[1] - a2[1]) < 1e-6
    bh = abs(b1[1] - b2[1]) < 1e-6
    if ah and bh and abs(a1[1] - b1[1]) < 0.75:
        return max(0.0, min(max(a1[0], a2[0]), max(b1[0], b2[0])) - max(min(a1[0], a2[0]), min(b1[0], b2[0])))
    av = abs(a1[0] - a2[0]) < 1e-6
    bv = abs(b1[0] - b2[0]) < 1e-6
    if av and bv and abs(a1[0] - b1[0]) < 0.75:
        return max(0.0, min(max(a1[1], a2[1]), max(b1[1], b2[1])) - max(min(a1[1], a2[1]), min(b1[1], b2[1])))
    return 0.0


def seg_len(p: Point, q: Point) -> float:
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def simplify(points: List[Point]) -> List[Point]:
    """同一直線上の中間点・重複点を取り除く。"""
    out: List[Point] = []
    for p in points:
        if out and abs(out[-1][0] - p[0]) < 1e-6 and abs(out[-1][1] - p[1]) < 1e-6:
            continue
        out.append(p)
    changed = True
    while changed and len(out) >= 3:
        changed = False
        for i in range(1, len(out) - 1):
            a, b, c = out[i - 1], out[i], out[i + 1]
            if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or \
               (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6):
                del out[i]
                changed = True
                break
    return out


# ---------------------------------------------------------------------------
# 診断
# ---------------------------------------------------------------------------

class Diagnostic(dict):
    """{code, level, subject, message, evidence, fixes} の辞書（JSON 化しやすいよう dict を継承）。"""

    def __init__(self, code: str, level: str, subject: str, message: str,
                 evidence: Optional[dict] = None, fixes: Optional[List[str]] = None):
        super().__init__(code=code, level=level, subject=subject, message=message,
                         evidence=evidence or {}, fixes=fixes or [])


def diag_error(code, subject, message, evidence=None, fixes=None) -> Diagnostic:
    return Diagnostic(code, "error", subject, message, evidence, fixes)


def diag_warn(code, subject, message, evidence=None, fixes=None) -> Diagnostic:
    return Diagnostic(code, "warning", subject, message, evidence, fixes)


def diag_info(code, subject, message, evidence=None, fixes=None) -> Diagnostic:
    return Diagnostic(code, "info", subject, message, evidence, fixes)


def format_diagnostic(d: dict, prefix: str = "") -> str:
    """人が読む 1 行メッセージ（fixes は「→」で続ける）。"""
    s = f"{prefix}[{d['code']}] {d['message']}"
    if d.get("fixes"):
        s += " → " + " / ".join(d["fixes"])
    return s


# ---------------------------------------------------------------------------
# グリッド
# ---------------------------------------------------------------------------

class Grid:
    """rows×cols のセル格子。h_tracks / v_tracks は配線に使えるガター（行間・列間・外周）の座標。"""

    def __init__(self, x: float, y: float, w: float, h: float, rows: int, cols: int,
                 node_wr: float = 0.78, node_hr: float = 0.62,
                 v_tracks: Optional[List[float]] = None, h_tracks: Optional[List[float]] = None):
        self.x, self.y, self.w, self.h = float(x), float(y), float(w), float(h)
        self.rows, self.cols = max(1, int(rows)), max(1, int(cols))
        self.cell_w = self.w / self.cols
        self.cell_h = self.h / self.rows
        self.node_wr, self.node_hr = node_wr, node_hr
        mx = self.cell_w * (1 - node_wr)  # セル内の左右マージン合計
        my = self.cell_h * (1 - node_hr)
        if v_tracks is None:
            v_tracks = [self.x + mx * 0.25] + [self.x + c * self.cell_w for c in range(1, self.cols)] \
                       + [self.x + self.w - mx * 0.25]
        if h_tracks is None:
            h_tracks = [self.y + my * 0.25] + [self.y + r * self.cell_h for r in range(1, self.rows)] \
                       + [self.y + self.h - my * 0.25]
        self.v_tracks = sorted(set(round(v, 3) for v in v_tracks))
        self.h_tracks = sorted(set(round(v, 3) for v in h_tracks))

    def cell(self, row: int, col: int) -> dict:
        return rect_of(self.x + col * self.cell_w, self.y + row * self.cell_h, self.cell_w, self.cell_h)

    def node_box(self, row: int, col: int, wr: Optional[float] = None, hr: Optional[float] = None,
                 max_w: Optional[float] = None, max_h: Optional[float] = None) -> dict:
        c = self.cell(row, col)
        w = c["w"] * (wr if wr is not None else self.node_wr)
        h = c["h"] * (hr if hr is not None else self.node_hr)
        if max_w:
            w = min(w, max_w)
        if max_h:
            h = min(h, max_h)
        return rect_of(c["x"] + (c["w"] - w) / 2, c["y"] + (c["h"] - h) / 2, w, h)


# ---------------------------------------------------------------------------
# 格子ルーター（直交最短経路。Dijkstra: 距離 + 折れペナルティ + トラック種別ペナルティ）
# ---------------------------------------------------------------------------

def _ports(box: dict) -> Dict[str, Point]:
    cx = box["x"] + box["w"] / 2
    cy = box["y"] + box["h"] / 2
    return {"left": (box["x"], cy), "right": (box["x"] + box["w"], cy),
            "top": (cx, box["y"]), "bottom": (cx, box["y"] + box["h"])}


def _facing_sides(a: dict, b: dict) -> List[str]:
    """a から b に向かう「自然な辺」（相手側の辺）を優先順で返す。"""
    acx, acy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    bcx, bcy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    dx, dy = bcx - acx, bcy - acy
    horiz = ["right"] if dx > 0 else ["left"]
    vert = ["bottom"] if dy > 0 else ["top"]
    if abs(dx) >= abs(dy):
        return horiz + vert
    return vert + horiz


class LatticeRouter:
    """トラック（垂直線 xs・水平線 ys）の交点をノードとする格子グラフ上で直交経路を探索する。"""

    def __init__(self, grid: Grid, boxes: Dict[str, dict]):
        self.grid = grid
        self.boxes = boxes
        xs = set(grid.v_tracks)
        ys = set(grid.h_tracks)
        self.center_x = set()
        self.center_y = set()
        for b in boxes.values():
            cx = round(b["x"] + b["w"] / 2, 3)
            cy = round(b["y"] + b["h"] / 2, 3)
            xs.add(cx); ys.add(cy)
            self.center_x.add(cx); self.center_y.add(cy)
        self.xs = sorted(xs)
        self.ys = sorted(ys)
        self.xi = {x: i for i, x in enumerate(self.xs)}
        self.yi = {y: i for i, y in enumerate(self.ys)}
        self.used: Dict[Tuple[str, float], int] = {}  # 既に線が通ったトラック → 本数
        self.routed_segments: List[Tuple[Point, Point]] = []  # 既に配線した線分（交差ペナルティ用）

    # -- 障害物判定 ---------------------------------------------------------
    def _blocked(self, p: Point, q: Point, ignore: Sequence[str]) -> bool:
        for nid, b in self.boxes.items():
            if nid in ignore:
                continue
            if segment_hits_rect(p, q, b):
                return True
        return False

    @staticmethod
    def _step_crosses(p: Point, q: Point, a: Point, b: Point) -> bool:
        """格子の 1 ステップ p→q が既存線分 a-b を横切るか。格子上では交点が p→q の端点（格子点）に
        乗るため、既存線分の内側を通り、かつ交点がステップの始点 p 以外にあれば交差と数える。"""
        step_h = abs(p[1] - q[1]) < 1e-6
        seg_h = abs(a[1] - b[1]) < 1e-6
        if step_h == seg_h:
            return False
        if step_h:  # 水平ステップ × 垂直線分
            x = a[0]
            lo, hi = min(p[0], q[0]), max(p[0], q[0])
            if not (lo - 1e-6 <= x <= hi + 1e-6) or abs(x - p[0]) < 1e-6:
                return False
            return min(a[1], b[1]) + 0.5 < p[1] < max(a[1], b[1]) - 0.5
        y = a[1]
        lo, hi = min(p[1], q[1]), max(p[1], q[1])
        if not (lo - 1e-6 <= y <= hi + 1e-6) or abs(y - p[1]) < 1e-6:
            return False
        return min(a[0], b[0]) + 0.5 < p[0] < max(a[0], b[0]) - 0.5

    def _step_cost(self, p: Point, q: Point) -> float:
        d = seg_len(p, q)
        cost = d
        # 既に配線した線との交差 1 箇所ごとにペナルティ（交差の少ない経路を選ぶ）
        for a, b in self.routed_segments:
            if self._step_crosses(p, q, a, b):
                cost += CROSS_PENALTY
        if abs(p[1] - q[1]) < 1e-6:  # 水平移動: 使っている水平トラックは y
            y = round(p[1], 3)
            if y in self.center_y:
                cost += d * CENTER_TRACK_PENALTY
            cost += d * SHARED_TRACK_PENALTY * self.used.get(("h", y), 0)
        else:
            x = round(p[0], 3)
            if x in self.center_x:
                cost += d * CENTER_TRACK_PENALTY
            cost += d * SHARED_TRACK_PENALTY * self.used.get(("v", x), 0)
        return cost

    def _stub(self, box: dict, side: str) -> Optional[Tuple[Point, Point]]:
        """辺の中点（ポート）から、外側の最初のトラック交点までのスタブを返す。"""
        ports = _ports(box)
        p = ports[side]
        px, py = round(p[0], 3), round(p[1], 3)
        if side == "right":
            cands = [x for x in self.xs if x > px + 1e-6]
            if not cands:
                return None
            return (px, py), (cands[0], py)
        if side == "left":
            cands = [x for x in self.xs if x < px - 1e-6]
            if not cands:
                return None
            return (px, py), (cands[-1], py)
        if side == "bottom":
            cands = [y for y in self.ys if y > py + 1e-6]
            if not cands:
                return None
            return (px, py), (px, cands[0])
        cands = [y for y in self.ys if y < py - 1e-6]
        if not cands:
            return None
        return (px, py), (px, cands[-1])

    # -- 探索 ---------------------------------------------------------------
    def route(self, a_id: str, b_id: str, from_sides: Optional[Sequence[str]] = None,
              to_sides: Optional[Sequence[str]] = None) -> Optional[List[Point]]:
        A, B = self.boxes[a_id], self.boxes[b_id]
        ignore = (a_id, b_id)
        pref_a = _facing_sides(A, B)
        pref_b = _facing_sides(B, A)
        starts = list(from_sides) if from_sides else list(SIDES)
        ends = list(to_sides) if to_sides else list(SIDES)

        # 開始・終了スタブ（ポート → 最初の交点）。中心線トラックは自ノードの中心を通るので、
        # スタブの終点は必ず格子点になる。
        start_nodes = {}
        for s in starts:
            st = self._stub(A, s)
            if not st:
                continue
            if self._blocked(st[0], st[1], ignore):
                continue
            pen = 0.0 if s == pref_a[0] else (BACK_SIDE_PENALTY * 0.5 if s == pref_a[1] else BACK_SIDE_PENALTY)
            start_nodes[st[1]] = (pen + seg_len(*st), st[0])
        end_nodes = {}
        for s in ends:
            st = self._stub(B, s)
            if not st:
                continue
            if self._blocked(st[0], st[1], ignore):
                continue
            pen = 0.0 if s == pref_b[0] else (BACK_SIDE_PENALTY * 0.5 if s == pref_b[1] else BACK_SIDE_PENALTY)
            end_nodes[st[1]] = (pen + seg_len(*st), st[0])
        if not start_nodes or not end_nodes:
            return None

        # 状態 = (格子点, 進入方向) で Dijkstra（折れ判定のため方向を持つ）
        INF = float("inf")
        best: Dict[Tuple[Point, Optional[str]], float] = {}
        prev: Dict[Tuple[Point, Optional[str]], Tuple[Point, Optional[str]]] = {}
        pq: List[Tuple[float, int, Point, Optional[str]]] = []
        counter = 0
        for pt, (c0, _port) in start_nodes.items():
            key = (pt, None)
            best[key] = c0
            heapq.heappush(pq, (c0, counter, pt, None))
            counter += 1
        goal_key = None
        goal_cost = INF
        while pq:
            cost, _, pt, dirn = heapq.heappop(pq)
            if best.get((pt, dirn), INF) < cost - 1e-9:
                continue
            if pt in end_nodes:
                total = cost + end_nodes[pt][0]
                if total < goal_cost:
                    goal_cost = total
                    goal_key = (pt, dirn)
            # 展開: 上下左右の隣接格子点
            xi, yi = self.xi[pt[0]], self.yi[pt[1]]
            nbrs = []
            if xi + 1 < len(self.xs):
                nbrs.append(((self.xs[xi + 1], pt[1]), "h"))
            if xi > 0:
                nbrs.append(((self.xs[xi - 1], pt[1]), "h"))
            if yi + 1 < len(self.ys):
                nbrs.append(((pt[0], self.ys[yi + 1]), "v"))
            if yi > 0:
                nbrs.append(((pt[0], self.ys[yi - 1]), "v"))
            for q, nd in nbrs:
                if self._blocked(pt, q, ignore):
                    continue
                c = cost + self._step_cost(pt, q)
                if dirn is not None and nd != dirn:
                    c += BEND_PENALTY
                key = (q, nd)
                if c < best.get(key, INF) - 1e-9:
                    best[key] = c
                    prev[key] = (pt, dirn)
                    heapq.heappush(pq, (c, counter, q, nd))
                    counter += 1
        if goal_key is None:
            return None
        # 経路復元
        pts: List[Point] = []
        key = goal_key
        while key in prev:
            pts.append(key[0])
            key = prev[key]
        pts.append(key[0])
        pts.reverse()
        start_port = start_nodes[pts[0]][1]
        end_port = end_nodes[pts[-1]][1]
        full = [start_port] + pts + [end_port]
        full = simplify(full)
        # 使用トラック・線分を記録（後続の線が同じ回廊・交差を避けやすくする）
        for i in range(len(full) - 1):
            p, q = full[i], full[i + 1]
            self.routed_segments.append((p, q))
            if abs(p[1] - q[1]) < 1e-6:
                self.used[("h", round(p[1], 3))] = self.used.get(("h", round(p[1], 3)), 0) + 1
            else:
                self.used[("v", round(p[0], 3))] = self.used.get(("v", round(p[0], 3)), 0) + 1
        return full


def _orthogonalize(points: List[Point]) -> List[Point]:
    """連続する 2 点が斜めなら「水平 → 垂直」の肘を挟んで直交化する（via 指定用）。"""
    out: List[Point] = [points[0]]
    for p in points[1:]:
        q = out[-1]
        if abs(p[0] - q[0]) > 1e-6 and abs(p[1] - q[1]) > 1e-6:
            out.append((p[0], q[1]))
        out.append(p)
    return simplify(out)


def _route_via(A: dict, B: dict, via: List[Point], from_side: Optional[str], to_side: Optional[str]) -> List[Point]:
    pa = _ports(A)
    pb = _ports(B)
    first = via[0]
    last = via[-1]

    def pick(ports, target, forced):
        if forced in ports:
            return ports[forced]
        # target に最も近い辺
        return min(ports.values(), key=lambda p: abs(p[0] - target[0]) + abs(p[1] - target[1]))

    start = pick(pa, first, from_side)
    end = pick(pb, last, to_side)
    pts = [start] + [tuple(map(float, v)) for v in via] + [end]
    return _orthogonalize(pts)


def _straight(A: dict, B: dict, from_side: Optional[str], to_side: Optional[str]) -> List[Point]:
    pa, pb = _ports(A), _ports(B)
    sides_a = _facing_sides(A, B)
    sides_b = _facing_sides(B, A)
    sa = from_side or sides_a[0]
    sb = to_side or sides_b[0]
    p, q = pa[sa], pb[sb]
    if abs(p[0] - q[0]) < 1e-6 or abs(p[1] - q[1]) < 1e-6:
        return [p, q]
    # 直線にならないときは L 字で妥協
    if sa in ("left", "right"):
        return simplify([p, (q[0], p[1]), q])
    return simplify([p, (p[0], q[1]), q])


# ---------------------------------------------------------------------------
# 回廊オフセット（同一トラック上で重なるセグメント／同じ辺のポートを等間隔にずらす）
# ---------------------------------------------------------------------------

def spread_segments(routed: List[dict], boxes: Dict[str, dict], step: float = CORRIDOR_STEP) -> None:
    """routed[i]["points"] を in-place で更新する。
    同一トラック（同じ y の水平 or 同じ x の垂直）で範囲が重なるセグメント群に、
    -k…+k の対称オフセットを与える。端点がノードのポートに接している場合はポート位置も
    辺に沿ってずれる（＝Port Spread）。順序は「相手側端点の座標」で安定ソートする。"""
    # セグメント一覧: (edge_idx, seg_idx, orientation, track, lo, hi)
    segs = []
    for ei, e in enumerate(routed):
        pts = e["points"]
        for si in range(len(pts) - 1):
            p, q = pts[si], pts[si + 1]
            if abs(p[1] - q[1]) < 1e-6:
                segs.append((ei, si, "h", round(p[1], 3), min(p[0], q[0]), max(p[0], q[0])))
            elif abs(p[0] - q[0]) < 1e-6:
                segs.append((ei, si, "v", round(p[0], 3), min(p[1], q[1]), max(p[1], q[1])))
    # トラックごとにグループ化し、範囲が重なる連結成分を作る
    by_track: Dict[Tuple[str, float], List[tuple]] = {}
    for s in segs:
        by_track.setdefault((s[2], s[3]), []).append(s)
    offsets: Dict[Tuple[int, int], float] = {}
    for key, group in by_track.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda s: (s[4], s[5]))
        comps: List[List[tuple]] = []
        for s in group:
            if comps and s[4] < comps[-1][-1][5] - 0.5 and any(
                    min(s[5], t[5]) - max(s[4], t[4]) > 0.5 for t in comps[-1]):
                comps[-1].append(s)
            else:
                comps.append([s])
        for comp in comps:
            if len(comp) < 2:
                continue
            # 同じ from/to の「同じ線の別セグメント」は 1 本として扱う（通常は起きない）
            # 並び順: 他端の座標（線の向きの一貫性）→ エッジ index
            def sort_key(s):
                e = routed[s[0]]
                pts = e["points"]
                other = pts[-1] if s[1] == 0 else pts[0]
                return (other[0] + other[1], s[0])
            comp.sort(key=sort_key)
            n = len(comp)
            # 同一回廊に本数が多いときは刻みを詰め、全体の広がりが MAX_SPREAD を超えないようにする
            eff = min(step, MAX_SPREAD / max(1, n - 1))
            for k, s in enumerate(comp):
                offsets[(s[0], s[1])] = (k - (n - 1) / 2) * eff
    if not offsets:
        return

    def shifted(ei, si, off):
        pts = routed[ei]["points"]
        p, q = pts[si], pts[si + 1]
        if abs(p[1] - q[1]) < 1e-6:
            return (p[0], p[1] + off), (q[0], q[1] + off)
        return (p[0] + off, p[1]), (q[0] + off, q[1])

    def hits(ei, si, off):
        e = routed[ei]
        p, q = shifted(ei, si, off)
        return any(segment_hits_rect(p, q, b) for nid, b in boxes.items() if nid not in (e.get("from"), e.get("to")))

    # ずらした先がノードに当たる場合は、そのグループ全体の向きを反転し、それでも当たれば間隔を縮める
    # （ずらし処理が線をノードの当たり判定の中へ押し込むのを防ぐ）
    groups: Dict[Tuple[str, float], List[Tuple[int, int]]] = {}
    for (ei, si) in offsets:
        pts = routed[ei]["points"]
        p, q = pts[si], pts[si + 1]
        key = ("h", round(p[1], 3)) if abs(p[1] - q[1]) < 1e-6 else ("v", round(p[0], 3))
        groups.setdefault(key, []).append((ei, si))
    for key, members in groups.items():
        scale = 1.0
        while scale >= 0.25:
            if not any(hits(ei, si, offsets[(ei, si)] * scale) for ei, si in members):
                break
            if not any(hits(ei, si, -offsets[(ei, si)] * scale) for ei, si in members):
                scale = -scale
                break
            scale = abs(scale) * 0.5
        else:
            scale = 0.0
        for ei, si in members:
            offsets[(ei, si)] *= scale
    for (ei, si), off in offsets.items():
        if abs(off) < 1e-6:
            continue
        e = routed[ei]
        pts = list(e["points"])
        pts[si], pts[si + 1] = shifted(ei, si, off)
        e["points"] = pts
    for e in routed:
        e["points"] = simplify(e["points"])


# ---------------------------------------------------------------------------
# ラベル配置
# ---------------------------------------------------------------------------

def tag_pill_rect(box: dict, tag_size: float = 10.0) -> dict:
    """ノード右上の tag ピルの矩形（build_deck の描画式と同じ: 幅=文字幅+12、高さ=size×1.6、上に 0.8×size はみ出す）。"""
    tw = text_width(box.get("tag", ""), tag_size) + 12
    return rect_of(box["x"] + box["w"] - tw - 8, box["y"] - tag_size * 0.8, tw, tag_size * 1.6)


def label_box_size(text, size: float) -> Tuple[float, float]:
    return text_width(text, size) + 2 * LABEL_PAD_X, size * 1.25 + 2 * LABEL_PAD_Y


def place_labels(routed: List[dict], boxes: Dict[str, dict], label_size: float,
                 diags: List[dict], subject_prefix: str = "", extra_obstacles: Optional[List[dict]] = None) -> None:
    """各線のラベル位置（label_box: 中心 cx,cy と w,h）を決める。
    候補: 最長セグメント（水平優先）の中点の上／下（水平）・右／左（垂直）→ 次に長いセグメント…。
    ノード箱・確定済みラベルと衝突しない最初の候補を採用。全候補が衝突するときは
    重なり面積最小の候補を採用し label-collision を警告する。label_at 指定は無条件で採用。"""
    placed: List[dict] = []
    # ひし形（decision）は外接矩形の角が空いているので、ラベル衝突判定では中央 60% の矩形に縮めて扱う
    # （配線の横切り判定は外接矩形のまま。角をすり抜けさせないため）
    obstacles = []
    for b in boxes.values():
        if b.get("shape") == "diamond":
            obstacles.append(rect_of(b["x"] + b["w"] * 0.2, b["y"] + b["h"] * 0.2, b["w"] * 0.6, b["h"] * 0.6))
        else:
            obstacles.append(b)
    obstacles.extend(extra_obstacles or [])  # tag ピルなど、ノード箱の外にはみ出す小要素
    for e in routed:
        text = e.get("label")
        if not text:
            e["label_box"] = None
            continue
        lw, lh = label_box_size(text, label_size)
        # classification（dataflow のデータ区分。2 行目に小さく表示）があればその分だけピルを高くする
        if e.get("classification"):
            cls_size = label_size * 0.85
            lw = max(lw, text_width(e["classification"], cls_size) + 2 * LABEL_PAD_X)
            lh += cls_size * 1.2
            e["class_h"] = cls_size * 1.2
        if e.get("label_at"):
            cx, cy = float(e["label_at"][0]), float(e["label_at"][1])
            e["label_box"] = {"cx": cx, "cy": cy, "w": lw, "h": lh, "x": cx - lw / 2, "y": cy - lh / 2}
            placed.append(e["label_box"])
            continue
        pts = e["points"]
        segs = []
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            horiz = abs(p[1] - q[1]) < 1e-6
            L = seg_len(p, q)
            score = L + (40 if horiz else 0)
            # 分岐ラベル（Y/N 等）は発側の最初の線分に置くのが読みやすい。ラベルが収まる長さなら優先する
            if i == 0 and L >= (lw if horiz else lh) + 8:
                score += 70
            segs.append((score, i, horiz, p, q))
        segs.sort(key=lambda s: -s[0])
        candidates = []
        for _, i, horiz, p, q in segs:
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            if horiz:
                candidates.append((mx, my - LABEL_GAP - lh / 2))
                candidates.append((mx, my + LABEL_GAP + lh / 2))
            else:
                candidates.append((mx + LABEL_GAP + lw / 2, my))
                candidates.append((mx - LABEL_GAP - lw / 2, my))
        best = None
        best_pen = float("inf")
        for cx, cy in candidates:
            box = {"cx": cx, "cy": cy, "w": lw, "h": lh, "x": cx - lw / 2, "y": cy - lh / 2}
            probe = inflate(box, LABEL_BREATH)  # Archify: clear gap > mask width + breathing room
            pen = 0.0
            for ob in obstacles:
                # 縁が数 px 触れるだけ（狭いガターで避けようのない接触）は衝突とみなさない
                if penetration(box, ob) > TOUCH_TOL:
                    pen += overlap_area(probe, ob)
            for ob in placed:
                if penetration(box, ob) > TOUCH_TOL:
                    pen += overlap_area(probe, ob) * 1.5
            # 他の線のセグメントを隠す場合も軽いペナルティ
            for other in routed:
                if other is e:
                    continue
                opts = other["points"]
                for k in range(len(opts) - 1):
                    if segment_hits_rect(opts[k], opts[k + 1], box, 0.0):
                        pen += 40.0
            if pen < best_pen:
                best_pen = pen
                best = box
            if pen == 0.0:
                break
        e["label_box"] = best
        if best is not None:
            placed.append(best)
            if best_pen > 0.0:
                subj = f"{subject_prefix}{e.get('from')}→{e.get('to')}"
                diags.append(diag_warn(
                    "label-collision", subj,
                    f"エッジ {e.get('from')}→{e.get('to')} のラベル「{text}」が他の要素と重なります",
                    {"label": text, "at": [round(best['cx']), round(best['cy'])], "overlap": round(best_pen)},
                    [f"edges の該当要素に \"label_at\": [{round(best['cx'])}, {round(best['cy'] - lh - 6)}] のように位置を指定する",
                     "ノードの row/col を離してセグメントを長くする",
                     "意味を保ったまま文言を短くする（意味のあるラベルは削らない）",
                     "列数（cols）を減らす、または style.diagram.node_wr を 0.7 程度に下げてノード間の隙間を広げる"]))


# ---------------------------------------------------------------------------
# グリッド図（architecture / dataflow / lifecycle / swimlane 共通）の配線と診断
# ---------------------------------------------------------------------------

def route_all(grid: Grid, boxes: Dict[str, dict], edges: List[dict], label_size: float = 13.0,
              diags: Optional[List[dict]] = None, subject_prefix: str = "",
              label_obstacles: Optional[List[dict]] = None) -> List[dict]:
    """edges（{from,to,label,variant,arrow,from_side,to_side,via,route,...}）を配線して
    [{... , "points": [...], "label_box": {...}}] を返す。診断は diags に追記する。"""
    if diags is None:
        diags = []
    router = LatticeRouter(grid, boxes)
    routed: List[dict] = []
    for idx, e in enumerate(edges):
        a, b = e.get("from"), e.get("to")
        if a not in boxes or b not in boxes:
            continue
        A, B = boxes[a], boxes[b]
        out = dict(e)
        if e.get("style") and e.get("variant") and e.get("style") != "solid" and e.get("style") != e.get("variant"):
            diags.append(diag_warn("style-conflict", f"{subject_prefix}edges[{idx}]",
                                   f"edges[{idx}] に style '{e.get('style')}' と variant '{e.get('variant')}' の両方が指定されています（variant を優先）",
                                   {}, ["style は旧形式の別名なので variant だけを書く"]))
        out.setdefault("variant", e.get("variant") or ("dashed" if e.get("style") == "dashed" else "default"))
        out.setdefault("arrow", "end")
        fs, ts = e.get("from_side"), e.get("to_side")
        if fs and fs not in SIDES:
            diags.append(diag_warn("invalid-side", f"{subject_prefix}edges[{idx}]",
                                   f"edges[{idx}] の from_side '{fs}' は left/right/top/bottom のいずれかで指定してください"))
            fs = None
        if ts and ts not in SIDES:
            diags.append(diag_warn("invalid-side", f"{subject_prefix}edges[{idx}]",
                                   f"edges[{idx}] の to_side '{ts}' は left/right/top/bottom のいずれかで指定してください"))
            ts = None
        if a == b:
            # 自己ループ: 右辺から出て上へ回り込む小さなコの字
            p = _ports(A)
            r = (p["right"][0], p["right"][1] - A["h"] * 0.2)
            pts = [r, (r[0] + 22, r[1]), (r[0] + 22, A["y"] - 12), (A["x"] + A["w"] * 0.75, A["y"] - 12),
                   (A["x"] + A["w"] * 0.75, A["y"])]
            out["points"] = pts
            routed.append(out)
            continue
        pts: Optional[List[Point]] = None
        via = e.get("via")
        if via:
            try:
                pts = _route_via(A, B, [(float(v[0]), float(v[1])) for v in via], fs, ts)
            except (TypeError, ValueError, IndexError):
                diags.append(diag_warn("invalid-via", f"{subject_prefix}edges[{idx}]",
                                       f"edges[{idx}] の via は [[x, y], ...] の形で指定してください"))
                pts = None
        if pts is None and e.get("route") == "straight":
            pts = _straight(A, B, fs, ts)
        if pts is None:
            pts = router.route(a, b, [fs] if fs else None, [ts] if ts else None)
            if pts is None and (fs or ts):
                pts = router.route(a, b)  # 指定辺では出られない → 辺指定を無視して再試行
                if pts is not None:
                    diags.append(diag_warn("side-ignored", f"{subject_prefix}{a}→{b}",
                                           f"エッジ {a}→{b} は指定された from_side/to_side では他ノードを避けられないため辺指定を無視しました"))
        if pts is None:
            pts = _straight(A, B, fs, ts)
            out["forced"] = True
        out["points"] = pts
        routed.append(out)
    spread_segments(routed, boxes)
    # 横切り・交差・重なり・リズムの診断
    for e in routed:
        pts = e["points"]
        a, b = e["from"], e["to"]
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            for nid, box in boxes.items():
                if nid in (a, b):
                    continue
                if segment_hits_rect(p, q, box):
                    node_label = box.get("label") or nid
                    diags.append(diag_error(
                        "edge-through-node", f"{subject_prefix}{a}→{b}",
                        f"エッジ {a}→{b} がノード「{node_label}」（id={nid}）を横切ります",
                        {"segment": [[round(p[0]), round(p[1])], [round(q[0]), round(q[1])]],
                         "node": {"id": nid, "x": round(box["x"]), "y": round(box["y"]), "w": round(box["w"]), "h": round(box["h"])}},
                        [f"ノード '{nid}' または '{a}'/'{b}' の row/col を変えて直線上から外す",
                         f"edges の該当要素に \"via\": [[{round(box['x'] - 20)}, {round(p[1] if abs(p[1]-q[1])<1e-6 else box['y'] - 20)}]] のような経由点を指定する",
                         "\"from_side\" / \"to_side\" で出入りする辺を指定する"]))
                    break
            L = seg_len(p, q)
            if 0 < L < MIN_SEGMENT:
                diags.append(diag_info("short-segment", f"{subject_prefix}{a}→{b}",
                                       f"エッジ {a}→{b} に {L:.0f}px の短いセグメントがあります",
                                       {"length": round(L, 1)}, ["row/col の間隔を広げるか via で経路を単純化する"]))
    crossings = 0
    overlaps = 0
    for i in range(len(routed)):
        for j in range(i + 1, len(routed)):
            ei, ej = routed[i], routed[j]
            related = {ei["from"], ei["to"]} & {ej["from"], ej["to"]}
            pi, pj = ei["points"], ej["points"]
            for k in range(len(pi) - 1):
                for m in range(len(pj) - 1):
                    if segments_cross(pi[k], pi[k + 1], pj[m], pj[m + 1]):
                        crossings += 1
                    if not related and collinear_overlap(pi[k], pi[k + 1], pj[m], pj[m + 1]) >= MIN_SEGMENT:
                        overlaps += 1
    if crossings:
        mk = diag_warn if crossings >= 2 else diag_info
        diags.append(mk("crossings", f"{subject_prefix}edges",
                               f"エッジ同士の交差が {crossings} 箇所あります",
                               {"count": crossings},
                               ["交差する線の端点ノードの row/col を入れ替えて、主経路が一筆書きになるよう並べ替える",
                                "戻りの線（下流→上流）は from_side/to_side を bottom/top にして主経路の外側を通す"]))
    if overlaps:
        diags.append(diag_warn("edge-overlap", f"{subject_prefix}edges",
                               f"無関係なエッジが同じ線上で {overlaps} 箇所重なっています（どちらの線か判別しにくい）",
                               {"count": overlaps},
                               ["どちらかのエッジに via を指定して別の回廊を通す", "ノードの row/col をずらす"]))
    place_labels(routed, boxes, label_size, diags, subject_prefix, label_obstacles)
    return routed


def check_node_text(boxes: Dict[str, dict], size: float, sub_size: float, pad: float,
                    diags: List[dict], subject_prefix: str = "", icon_w: float = 0.0,
                    line_h: float = 1.15) -> Dict[str, dict]:
    """各ノードの label / sublabel が箱に収まるフォントサイズを求め、収まらなければ警告する。
    戻り値: {id: {"size", "lines", "sub_size", "sub_lines"}}"""
    fit: Dict[str, dict] = {}
    for nid, b in boxes.items():
        inner_w = max(10.0, b["w"] - 2 * pad - icon_w)
        inner_h = max(8.0, b["h"] - 2 * pad)
        label = b.get("label", "")
        sub = b.get("sublabel", "")
        sub_h = (sub_size * 1.2 + 2) if sub else 0.0
        s, lines = fit_font_size(label, size, inner_w, inner_h - sub_h, line_h, min_size=max(9.0, size - 4), max_lines=3)
        sub_lines = wrap_text(sub, sub_size, inner_w) if sub else []
        used = len(lines) * s * line_h + (len(sub_lines) * sub_size * 1.2 + 2 if sub else 0)
        fit[nid] = {"size": s, "lines": lines, "sub_size": sub_size, "sub_lines": sub_lines, "used_h": used}
        if used > inner_h + 1.0 or len(lines) > 3:
            # PPTX は文字を自動縮小もクリップもしない（箱の外にはみ出す）ため、1 行分以上のあふれは error 扱い
            mk = diag_error if (used > inner_h + s * line_h or len(lines) > 3) else diag_warn
            diags.append(mk(
                "node-text-overflow", f"{subject_prefix}{nid}",
                f"ノード「{label}」（id={nid}）の文字が箱に収まりません（必要 {used:.0f}px / 箱 {inner_h:.0f}px）",
                {"needed": round(used), "available": round(inner_h), "lines": len(lines)},
                ["label を短くする（詳細は sublabel か lead に移す）",
                 "cols / rows を減らしてセルを大きくする",
                 "style.diagram.node_size を下げる（下限 10）"]))
    return fit


# ---------------------------------------------------------------------------
# sequence（シーケンス図）レイアウト
# ---------------------------------------------------------------------------

def layout_sequence(slide: dict, d: dict, diags: Optional[List[dict]] = None, subject_prefix: str = "") -> dict:
    """participants / messages / activations / segments から座標を計算する。
    d は layout の diagram 領域（x,y,w,h と各種トークン）。"""
    if diags is None:
        diags = []
    diags.extend(check_unknown_keys(slide, "sequence", subject_prefix))
    parts = slide.get("participants") or []
    msgs = slide.get("messages") or []
    x0, y0, w, h = d["x"], d["y"], d["w"], d["h"]
    n = max(1, len(parts))
    col_w = w / n
    box_h = d.get("participant_h", 54)
    box_w = min(d.get("participant_max_w", 170), col_w * d.get("participant_wr", 0.82))
    ids = [p.get("id") for p in parts]
    px = {pid: x0 + (i + 0.5) * col_w for i, pid in enumerate(ids)}
    pboxes = {}
    for i, p in enumerate(parts):
        cx = px[p.get("id")]
        pboxes[p.get("id")] = {"x": cx - box_w / 2, "y": y0, "w": box_w, "h": box_h, "cx": cx,
                               "label": p.get("label", ""), "sublabel": p.get("sublabel", ""),
                               "type": p.get("type", "generic"), "variant": p.get("variant", "default"), "id": p.get("id")}
    if len(parts) > MAX_PARTICIPANTS:
        diags.append(diag_warn("too-dense", f"{subject_prefix}participants",
                               f"参加者が {len(parts)} 人います（目安 {MAX_PARTICIPANTS} 人まで）",
                               {"count": len(parts)}, ["参加者をまとめる（例: 複数のバックエンドを 1 つに）", "2 枚に分ける"]))
    if len(msgs) > MAX_MESSAGES:
        diags.append(diag_warn("too-dense", f"{subject_prefix}messages",
                               f"メッセージが {len(msgs)} 本あります（目安 {MAX_MESSAGES} 本まで）",
                               {"count": len(msgs)}, ["主要なやり取りだけ残し、詳細は別スライドに分ける"]))
    top = y0 + box_h + d.get("top_gap", 22)
    bottom = y0 + h - d.get("bottom_pad", 10)
    m = max(1, len(msgs))
    pitch = (bottom - top) / m
    pitch = max(d.get("min_pitch", 30), min(d.get("max_pitch", 58), pitch))
    label_size = d.get("label_size", 13)
    # メッセージ y（ラベルは線の上に置くため、各行の下寄り 68% の位置に線を引く）
    ys = [top + i * pitch + pitch * 0.68 for i in range(len(msgs))]
    if msgs and ys[-1] > bottom + 0.5:
        diags.append(diag_warn("too-dense", f"{subject_prefix}messages",
                               f"メッセージが領域に収まりません（最後の線 y={ys[-1]:.0f} > 下端 {bottom:.0f}）",
                               {"last_y": round(ys[-1]), "bottom": round(bottom)},
                               ["メッセージを減らす／分割する", "style.diagram.min_pitch を下げる（下限 24 目安）"]))
    # activations: {participant, from, to}（メッセージ index または id）
    def msg_index(ref):
        if isinstance(ref, int):
            return ref
        for i, mm in enumerate(msgs):
            if mm.get("id") == ref:
                return i
        return None
    acts = []
    act_w = d.get("activation_w", 10)
    for ai, a in enumerate(slide.get("activations") or []):
        pid = a.get("participant")
        fi, ti = msg_index(a.get("from")), msg_index(a.get("to"))
        if pid not in px or fi is None or ti is None or not (0 <= fi < len(msgs)) or not (0 <= ti < len(msgs)):
            diags.append(diag_warn("unknown-endpoint", f"{subject_prefix}activations[{ai}]",
                                   f"activations[{ai}] の participant / from / to が participants・messages と一致しません",
                                   {}, ["participant は participants の id、from/to は messages の index（0 始まり）または id を指定する"]))
            continue
        if ti < fi:
            fi, ti = ti, fi
        acts.append({"participant": pid, "x": px[pid] - act_w / 2, "y": ys[fi] - pitch * 0.35,
                     "w": act_w, "h": (ys[ti] - ys[fi]) + pitch * 0.55})
    active_at = {}  # (pid, msg index) → 帯があるか
    for a in acts:
        for i, y in enumerate(ys):
            if a["y"] - 0.5 <= y <= a["y"] + a["h"] + 0.5:
                active_at[(a["participant"], i)] = True
    # messages
    out_msgs = []
    seen_ids = set()
    for i, mm in enumerate(msgs):
        f, t = mm.get("from"), mm.get("to")
        mid = mm.get("id")
        if mid is not None:
            if mid in seen_ids:
                diags.append(diag_error("duplicate-id", f"{subject_prefix}messages[{i}]",
                                        f"messages の id '{mid}' が重複しています", {}, ["id を一意にする"]))
            seen_ids.add(mid)
        if f not in px or t not in px:
            diags.append(diag_error("unknown-endpoint", f"{subject_prefix}messages[{i}]",
                                    f"messages[{i}] の from '{f}' / to '{t}' は participants に無い id です",
                                    {}, ["participants の id と一致させる"]))
            continue
        y = ys[i]
        variant = mm.get("variant", "default")
        label = mm.get("label", "")
        if not label:
            diags.append(diag_warn("missing-label", f"{subject_prefix}messages[{i}]",
                                   f"messages[{i}]（{f}→{t}）に label がありません", {}, ["何のやり取りか（動詞や API 名）を label に書く"]))
        xf, xt = px[f], px[t]
        gap_f = act_w / 2 + 1 if active_at.get((f, i)) else 0
        gap_t = act_w / 2 + 1 if active_at.get((t, i)) else 0
        if f == t:
            # 自己メッセージ: 右へ出て下がって戻る
            x1 = xf + gap_f
            loop_w = d.get("self_w", 46)
            pts = [(x1, y - pitch * 0.28), (x1 + loop_w, y - pitch * 0.28), (x1 + loop_w, y), (x1, y)]
            lb_cx = x1 + loop_w + LABEL_PAD_X + text_width(label, label_size) / 2 + 4
            lb_cy = y - pitch * 0.14
        else:
            direction = 1 if xt > xf else -1
            x1 = xf + direction * gap_f
            x2 = xt - direction * gap_t
            pts = [(x1, y), (x2, y)]
            lb_cx = (x1 + x2) / 2
            lb_cy = y - LABEL_GAP - (label_size * 1.25 + 2 * LABEL_PAD_Y) / 2
            dist = abs(x2 - x1)
            lw = text_width(label, label_size) + 2 * LABEL_PAD_X
            if lw > dist + 20 and dist > 0:
                diags.append(diag_warn("label-collision", f"{subject_prefix}messages[{i}]",
                                       f"messages[{i}] のラベル「{label}」（約 {lw:.0f}px）が矢印の長さ（{dist:.0f}px）より長く、隣のライフラインに掛かります",
                                       {"label_w": round(lw), "arrow_w": round(dist)},
                                       ["文言を短くする（意味は保つ）", "参加者の順番を入れ替えて距離を伸ばす", "participants を減らして列幅を広げる"]))
        lw, lh = label_box_size(label, label_size) if label else (0, 0)
        out_msgs.append({"index": i, "id": mid, "from": f, "to": t, "label": label, "variant": variant,
                         "points": pts, "y": y,
                         "label_box": ({"cx": lb_cx, "cy": lb_cy, "w": lw, "h": lh, "x": lb_cx - lw / 2, "y": lb_cy - lh / 2} if label else None)})
    # segments: {from, to, label}（メッセージ index または id）
    segs = []
    for si, sg in enumerate(slide.get("segments") or []):
        fi, ti = msg_index(sg.get("from")), msg_index(sg.get("to"))
        if fi is None or ti is None or not (0 <= fi < len(msgs)) or not (0 <= ti < len(msgs)):
            diags.append(diag_warn("unknown-endpoint", f"{subject_prefix}segments[{si}]",
                                   f"segments[{si}] の from / to が messages と一致しません", {},
                                   ["from/to は messages の index（0 始まり）または id を指定する"]))
            continue
        if ti < fi:
            fi, ti = ti, fi
        sy = ys[fi] - pitch * 0.62
        ey = ys[ti] + pitch * 0.26
        segs.append({"label": sg.get("label", ""), "x": x0 + 2, "y": sy, "w": w - 4, "h": ey - sy})
    lifeline_bottom = bottom
    return {"participants": pboxes, "order": ids, "col_w": col_w, "box_w": box_w, "box_h": box_h,
            "messages": out_msgs, "activations": acts, "segments": segs, "pitch": pitch,
            "lifeline_top": y0 + box_h, "lifeline_bottom": lifeline_bottom, "label_size": label_size}


# ---------------------------------------------------------------------------
# グリッド図の共通レイアウト（architecture / dataflow / lifecycle）
# ---------------------------------------------------------------------------

def _norm_nodes(slide: dict, kind: str) -> List[dict]:
    """タイプごとの配列名の違いを吸収して nodes のリストを返す。
    lifecycle は states（nodes も受理）。lane 指定は row に写す。"""
    nodes = slide.get("nodes")
    if kind == "lifecycle":
        nodes = slide.get("states") or nodes
    out = []
    for nd in nodes or []:
        if not isinstance(nd, dict):
            continue
        d = dict(nd)
        if "lane" in d and "row" not in d:
            d["row"] = d["lane"]
        if kind == "dataflow" and "stage" in d and "col" not in d:
            d["col"] = d["stage"]
        d.setdefault("row", 0)
        d.setdefault("col", 0)
        if "text" in d and "label" not in d:
            d["label"] = d["text"]
        out.append(d)
    return out


def _norm_edges(slide: dict, kind: str) -> List[dict]:
    edges = slide.get("edges")
    if kind == "lifecycle":
        edges = slide.get("transitions") or edges
    if kind == "dataflow":
        edges = slide.get("flows") or edges
    return [dict(e) for e in (edges or []) if isinstance(e, dict)]


COMMON_SLIDE_KEYS = {"type", "title", "eyebrow", "lead", "notes", "style", "legend", "cols", "rows",
                     "col_headers", "row_headers", "groups"}
ALLOWED_KEYS = {
    "architecture": COMMON_SLIDE_KEYS | {"nodes", "edges", "stages", "lanes"},
    "dataflow": COMMON_SLIDE_KEYS | {"nodes", "edges", "stages", "flows", "lanes"},
    "lifecycle": COMMON_SLIDE_KEYS | {"nodes", "edges", "states", "transitions", "lanes", "stages", "phases"},
    "sequence": COMMON_SLIDE_KEYS | {"participants", "messages", "activations", "segments"},
}
NODE_KEYS = {"id", "label", "text", "sublabel", "tag", "type", "variant", "row", "col", "lane", "stage", "kind", "step"}
EDGE_KEYS = {"from", "to", "label", "variant", "style", "arrow", "from_side", "to_side", "via", "label_at", "route",
             "classification", "id"}


def check_unknown_keys(slide: dict, kind: str, subject_prefix: str = "") -> List[dict]:
    """スライド直下・ノード・エッジの未知キー（typo）を候補付きの warning にする。
    validate_deck は style / layout_overrides の領域名しか検証しないため、内容側のキーはここで見る。"""
    import difflib
    diags: List[dict] = []
    allowed = ALLOWED_KEYS.get(kind)
    if not allowed:
        return diags

    def hint(key, pool):
        m = difflib.get_close_matches(key, sorted(pool), n=1)
        return f"（候補: {m[0]}）" if m else ""

    for key in slide.keys():
        if key not in allowed:
            diags.append(diag_warn("unknown-key", f"{subject_prefix}{key}",
                                   f"'{key}' は {kind} のフィールド名ではありません{hint(key, allowed)}", {},
                                   ["deck-schema.md の該当タイプの節にあるキー名に直す"]))
    if kind != "sequence":
        for i, nd in enumerate(_norm_nodes(slide, kind)):
            for key in nd.keys():
                if key not in NODE_KEYS:
                    diags.append(diag_warn("unknown-key", f"{subject_prefix}nodes[{i}].{key}",
                                           f"ノード '{nd.get('id', i)}' の '{key}' は未知のキーです{hint(key, NODE_KEYS)}", {}, []))
        for i, ed in enumerate(_norm_edges(slide, kind)):
            for key in ed.keys():
                if key not in EDGE_KEYS:
                    diags.append(diag_warn("unknown-key", f"{subject_prefix}edges[{i}].{key}",
                                           f"edges[{i}] の '{key}' は未知のキーです{hint(key, EDGE_KEYS)}", {}, []))
    return diags


def validate_grid_diagram(slide: dict, kind: str, subject_prefix: str = "") -> List[dict]:
    """ビルド前のスキーマ的検証（id 重複・未知 id・型・範囲）。error は fail 相当。"""
    diags: List[dict] = check_unknown_keys(slide, kind, subject_prefix)
    nodes = _norm_nodes(slide, kind)
    edges = _norm_edges(slide, kind)
    coll = "states" if kind == "lifecycle" else "nodes"
    ecoll = "transitions" if kind == "lifecycle" else "edges"
    if not nodes:
        diags.append(diag_error("empty", f"{subject_prefix}{coll}", f"{coll} が空です", {}, [f"{coll} に 1 個以上のノードを書く"]))
        return diags
    ids = set()
    cells: Dict[Tuple[int, int], str] = {}
    for i, nd in enumerate(nodes):
        nid = nd.get("id")
        if nid is None or str(nid) == "":
            diags.append(diag_error("missing-id", f"{subject_prefix}{coll}[{i}]", f"{coll}[{i}] に id がありません", {}, ["一意な id（英数字）を付ける"]))
            continue
        if nid in ids:
            diags.append(diag_error("duplicate-id", f"{subject_prefix}{nid}", f"ノード id '{nid}' が重複しています", {}, ["id を一意にする"]))
        ids.add(nid)
        if not nd.get("label"):
            diags.append(diag_warn("missing-label", f"{subject_prefix}{nid}", f"ノード '{nid}' に label がありません", {}, ["表示名を label に書く"]))
        for key in ("row", "col"):
            v = nd.get(key)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                diags.append(diag_error("invalid-position", f"{subject_prefix}{nid}",
                                        f"ノード '{nid}' の {key} は 0 以上の整数で指定してください（現在: {v!r}）", {},
                                        [f"{key} を 0 始まりの整数にする"]))
        t = nd.get("type")
        if t is not None and t not in COMPONENT_TYPES:
            diags.append(diag_warn("unknown-type", f"{subject_prefix}{nid}",
                                   f"ノード '{nid}' の type '{t}' は未対応です（{', '.join(COMPONENT_TYPES)}）", {},
                                   ["近い type に直す（不明なら省略して generic）"]))
        v = nd.get("variant")
        if v is not None and v not in NODE_VARIANTS:
            diags.append(diag_warn("unknown-variant", f"{subject_prefix}{nid}",
                                   f"ノード '{nid}' の variant '{v}' は未対応です（{', '.join(NODE_VARIANTS)}）", {}, ["default / emphasis / security / dashed / muted のいずれかにする"]))
        if kind == "lifecycle":
            k = nd.get("kind", "active")
            if k not in LIFECYCLE_KINDS:
                diags.append(diag_warn("unknown-kind", f"{subject_prefix}{nid}",
                                       f"状態 '{nid}' の kind '{k}' は未対応です（{', '.join(LIFECYCLE_KINDS)}）", {}, ["近い kind に直す"]))
        pos = (nd.get("row"), nd.get("col"))
        if isinstance(pos[0], int) and isinstance(pos[1], int):
            if pos in cells:
                diags.append(diag_error("cell-collision", f"{subject_prefix}{nid}",
                                        f"ノード '{nid}' と '{cells[pos]}' が同じ位置（row={pos[0]}, col={pos[1]}）にあります",
                                        {"row": pos[0], "col": pos[1]}, ["どちらかの row または col を変える"]))
            else:
                cells[pos] = nid
    lanes = slide.get("lanes")
    if kind == "lifecycle" and lanes is not None:
        if not isinstance(lanes, list) or not lanes:
            diags.append(diag_error("empty", f"{subject_prefix}lanes", "lanes は 1 個以上の配列で指定してください", {}, []))
        else:
            for nd in nodes:
                r = nd.get("row")
                if isinstance(r, int) and r >= len(lanes):
                    diags.append(diag_error("invalid-position", f"{subject_prefix}{nd.get('id')}",
                                            f"状態 '{nd.get('id')}' の lane={r} は lanes の範囲（0〜{len(lanes) - 1}）外です", {},
                                            ["lane を lanes の index（0 始まり）にする", "lanes に行を追加する"]))
    for i, e in enumerate(edges):
        for key in ("from", "to"):
            v = e.get(key)
            if v not in ids:
                diags.append(diag_error("unknown-endpoint", f"{subject_prefix}{ecoll}[{i}]",
                                        f"{ecoll}[{i}] の {key} '{v}' は未知のノード id です", {},
                                        [f"{coll} に存在する id を指定する"]))
        v = e.get("variant")
        if v is not None and v not in EDGE_VARIANTS:
            diags.append(diag_warn("unknown-variant", f"{subject_prefix}{ecoll}[{i}]",
                                   f"{ecoll}[{i}] の variant '{v}' は未対応です（{', '.join(EDGE_VARIANTS)}）", {}, ["default / emphasis / security / dashed のいずれかにする"]))
    groups = slide.get("groups") or []
    for gi, g in enumerate(groups):
        if not isinstance(g, dict):
            diags.append(diag_error("invalid-group", f"{subject_prefix}groups[{gi}]", f"groups[{gi}] はオブジェクトで指定してください", {}, []))
            continue
        members = g.get("nodes") or g.get("wraps") or []
        if not members:
            diags.append(diag_warn("empty-group", f"{subject_prefix}groups[{gi}]",
                                   f"groups[{gi}]「{g.get('label', '')}」にメンバー（nodes）がありません", {}, ["nodes にノード id を 1 個以上書く"]))
        for mid in members:
            if mid not in ids:
                diags.append(diag_error("unknown-endpoint", f"{subject_prefix}groups[{gi}]",
                                        f"groups[{gi}] の nodes '{mid}' は未知のノード id です", {}, ["存在する id にする"]))
    if len(nodes) > MAX_PRIMARY_NODES:
        diags.append(diag_warn("too-dense", f"{subject_prefix}{coll}",
                               f"ノードが {len(nodes)} 個あります（目安 {MAX_PRIMARY_NODES} 個まで。多いと文字が小さく線が絡みます）",
                               {"count": len(nodes)}, ["補助的なノードを省くか sublabel にまとめる", "2 枚に分ける（全体像＋詳細）"]))
    return diags


def layout_grid_diagram(slide: dict, kind: str, d: dict, diags: Optional[List[dict]] = None,
                        subject_prefix: str = "") -> dict:
    """architecture / dataflow / lifecycle のジオメトリ（HTML/PPTX 共通）。
    d = layout の diagram 領域（x,y,w,h とトークン）。戻り値:
      {"grid", "nodes": {id: box+meta}, "edges": [...], "groups": [...], "col_headers": [...],
       "row_headers": [...], "legend": [...], "text": {id: fit}, "diagnostics": [...]}"""
    if diags is None:
        diags = []
    nodes = _norm_nodes(slide, kind)
    edges = _norm_edges(slide, kind)
    x0, y0, w, h = float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"])

    # 見出し帯（列: stages / col_headers、行: lanes / row_headers）
    # 列見出し帯: col_headers が正式名。dataflow の stages / swimlane 流の phases も別名として受理する
    col_headers = slide.get("col_headers") or slide.get("stages") or slide.get("phases")
    col_headers = list(col_headers or [])
    # 行見出し: lanes が正式名（lifecycle）。row_headers も別名として受理する
    lanes = slide.get("lanes") or slide.get("row_headers")
    row_headers = []
    for ln in lanes or []:
        if isinstance(ln, dict):
            row_headers.append(ln.get("name") or ln.get("label") or "")
        else:
            row_headers.append(str(ln))
    header_h = float(d.get("header_h", 30)) if col_headers else 0.0
    row_label_w = float(d.get("row_label_w", 96)) if row_headers else 0.0

    # 凡例（type が 2 種以上のとき自動）
    legend_mode = slide.get("legend", "auto")
    types_present = []
    for nd in nodes:
        t = nd.get("type") or ("generic" if kind != "lifecycle" else None)
        if t and t != "generic" and t not in types_present:
            types_present.append(t)
    show_legend = (legend_mode is True) or (legend_mode == "auto" and len(types_present) >= 2)
    if legend_mode is False or legend_mode == "hidden":
        show_legend = False
    legend_h = float(d.get("legend_h", 26)) if show_legend else 0.0

    maxcol = max([nd.get("col", 0) for nd in nodes if isinstance(nd.get("col"), int)] + [0])
    maxrow = max([nd.get("row", 0) for nd in nodes if isinstance(nd.get("row"), int)] + [0])
    cols = slide.get("cols") or (len(col_headers) if col_headers else 0) or (maxcol + 1)
    rows = slide.get("rows") or (len(row_headers) if row_headers else 0) or (maxrow + 1)
    if maxcol >= cols:
        diags.append(diag_warn("out-of-grid", f"{subject_prefix}cols",
                               f"cols（{cols}）を超える col={maxcol} のノードがあるため cols を {maxcol + 1} に自動拡張しました",
                               {"cols": cols, "max_col": maxcol}, [f"\"cols\": {maxcol + 1} と明示する"]))
        cols = maxcol + 1
    if maxrow >= rows:
        if row_headers:
            diags.append(diag_warn("out-of-grid", f"{subject_prefix}rows",
                                   f"lanes/row_headers（{rows} 行）を超える row={maxrow} のノードがあるため行を {maxrow + 1} に自動拡張しました",
                                   {"rows": rows, "max_row": maxrow}, ["lanes に行を追加する", "row を範囲内にする"]))
        else:
            diags.append(diag_warn("out-of-grid", f"{subject_prefix}rows",
                                   f"rows（{rows}）を超える row={maxrow} のノードがあるため rows を {maxrow + 1} に自動拡張しました",
                                   {"rows": rows, "max_row": maxrow}, [f"\"rows\": {maxrow + 1} と明示する"]))
        rows = maxrow + 1
    if cols > MAX_COLS:
        diags.append(diag_warn("too-dense", f"{subject_prefix}cols",
                               f"列が {cols} 列あります（目安 {MAX_COLS} 列まで。ノードが細くなり文字が入りません）",
                               {"cols": cols}, ["列をまとめる", "2 枚に分ける"]))

    gx, gy = x0 + row_label_w, y0 + header_h
    gw, gh = w - row_label_w, h - header_h - legend_h
    grid = Grid(gx, gy, gw, gh, rows, cols, node_wr=d.get("node_wr", 0.78), node_hr=d.get("node_hr", 0.62))
    max_w = d.get("node_max_w")
    max_h = d.get("node_max_h")

    boxes: Dict[str, dict] = {}
    for nd in nodes:
        nid = nd.get("id")
        if nid is None:
            continue
        r, c = nd.get("row", 0), nd.get("col", 0)
        if not isinstance(r, int) or not isinstance(c, int) or r < 0 or c < 0:
            continue
        shape = "rect"
        wr, hr = None, None
        if kind == "lifecycle":
            k = nd.get("kind", "active")
            if k == "decision":
                shape = "diamond"
                # ひし形は外接矩形が大きく見えるため、セル高いっぱい・幅は高さの 1.25 倍に留める
                hr = min(0.9, d.get("node_hr", 0.62) * 1.35)
                wr = min(d.get("node_wr", 0.78), (grid.cell_h * hr * 1.25) / grid.cell_w)
            elif k == "start":
                shape = "pill"
                wr = d.get("node_wr", 0.78) * 0.9
        box = grid.node_box(r, c, wr, hr, max_w, max_h)
        box.update({"id": nid, "label": nd.get("label", ""), "sublabel": nd.get("sublabel", ""),
                    "tag": nd.get("tag", ""), "type": nd.get("type", "generic"), "variant": nd.get("variant", "default"),
                    "kind": nd.get("kind"), "step": nd.get("step"), "shape": shape, "row": r, "col": c,
                    "cx": box["x"] + box["w"] / 2, "cy": box["y"] + box["h"] / 2})
        boxes[nid] = box

    # グループ（境界）: メンバーの外接セル範囲
    groups_out = []
    for gi, g in enumerate(slide.get("groups") or []):
        if not isinstance(g, dict):
            continue
        members = [m for m in (g.get("nodes") or g.get("wraps") or []) if m in boxes]
        if not members:
            continue
        rs = [boxes[m]["row"] for m in members]
        cs = [boxes[m]["col"] for m in members]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        pad = float(g.get("pad", d.get("group_pad", 8)))
        c_tl = grid.cell(r0, c0)
        c_br = grid.cell(r1, c1)
        # 外接セル範囲の内側（ノード箱の外側マージンの半分）で囲む
        mx = grid.cell_w * (1 - grid.node_wr) / 2
        my = grid.cell_h * (1 - grid.node_hr) / 2
        bx = c_tl["x"] + mx - pad
        by = c_tl["y"] + my - pad - float(d.get("group_label_h", 18)) * 0.6
        bw = (c_br["x"] + c_br["w"] - mx + pad) - bx
        bh = (c_br["y"] + c_br["h"] - my + pad) - by
        leak = [nid for nid, b in boxes.items() if nid not in members and r0 <= b["row"] <= r1 and c0 <= b["col"] <= c1]
        if leak:
            diags.append(diag_warn("group-leak", f"{subject_prefix}groups[{gi}]",
                                   f"グループ「{g.get('label', '')}」の範囲内にメンバーでないノード {', '.join(leak)} が入っています",
                                   {"leak": leak}, ["メンバーの row/col を隣接させて矩形にまとめる", "はみ出したノードを groups.nodes に加えるか、範囲外へ動かす"]))
        groups_out.append({"label": g.get("label", ""), "kind": g.get("kind", "generic"), "variant": g.get("variant"),
                           "x": bx, "y": by, "w": bw, "h": bh, "nodes": members, "area": bw * bh})
    groups_out.sort(key=lambda g: -g["area"])  # 大きいものを先に（下に）描く

    # 見出し帯の座標
    ch_boxes = []
    for c, label in enumerate(col_headers):
        if c >= cols:
            break
        cell = grid.cell(0, c)
        ch_boxes.append({"label": label, "x": cell["x"], "y": y0, "w": cell["w"], "h": header_h})
    rh_boxes = []
    for r, label in enumerate(row_headers):
        if r >= rows:
            break
        cell = grid.cell(r, 0)
        rh_boxes.append({"label": label, "x": x0, "y": cell["y"], "w": row_label_w, "h": cell["h"], "alt": r % 2,
                         "band_x": gx, "band_w": gw})

    tag_rects = [tag_pill_rect(b, d.get("tag_size", 10)) for b in boxes.values() if b.get("tag")]
    routed = route_all(grid, boxes, edges, d.get("label_size", 13), diags, subject_prefix, tag_rects)

    text_fit = check_node_text(boxes, d.get("node_size", 14), d.get("sub_size", 11), d.get("node_pad", 8),
                               diags, subject_prefix, icon_w=(d.get("icon_size", 16) + 6) if kind != "lifecycle" else 0.0)

    legend_items = []
    if show_legend:
        labels = dict(TYPE_LABELS_JA)
        labels.update(d.get("type_labels") or {})
        # 並び順は Archify の凡例と同じ安定順（出現順ではない）
        for t in [t for t in COMPONENT_TYPES if t in types_present]:
            legend_items.append({"type": t, "label": labels.get(t, t)})

    return {"grid": grid, "nodes": boxes, "edges": routed, "groups": groups_out,
            "col_headers": ch_boxes, "row_headers": rh_boxes, "legend": legend_items,
            "legend_y": y0 + h - legend_h if show_legend else None, "legend_h": legend_h,
            "text": text_fit, "diagnostics": diags, "rows": rows, "cols": cols}

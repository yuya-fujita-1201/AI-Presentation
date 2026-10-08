#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedule_engine.py — 矢羽根スケジュール（`schedule` タイプ）のジオメトリ・検証エンジン。

diagram_engine.py と同じく Archify の方式「AI は型付き JSON（期間・行・矢羽根・節目）だけを
書き、決定論的なコードが検証して座標を決める」を取り込んだもの。座標を人や AI が手で
書かないので、HTML と PPTX のどちらでも矢羽根の始点・終点が時間軸とズレない。
（Archify 自体にはガント／スケジュールの図種が無いため、取り込みツール archify_import.py の
対象ではない。方式だけを適用している。）

時間軸は「列」単位の連続値で扱う。0 が先頭列の左端、len(columns) が最終列の右端。
位置（矢羽根の start / end、節目の at、today）は次のいずれでも書ける:
  - 数値           … 列単位の位置（例: 1.5 = 2列目の中央）
  - 列ラベル文字列 … columns の要素と完全一致（start は列の左端、end は列の右端）
  - "YYYY-MM"      … timeline 指定時。start は月初、end は月末
  - "YYYY-MM-DD"   … timeline 指定時。start はその日の始まり、end / at はその日の終わり

build_deck.py（HTML / PPTX 描画・ビルド時検証）と check_diagram.py（診断 CLI）が共用する。
外部依存なし。座標はすべて 1280×720 キャンバスの絶対 px。
"""

from __future__ import annotations

import calendar
import datetime as _dt
import re
from typing import List, Optional

import diagram_engine as de

BAR_VARIANTS = ("main", "accent", "muted", "prep", "ongoing", "tbd")
BAR_SHAPES = ("arrow", "chevron", "bar")
TIMELINE_UNITS = ("month", "week")

# 凡例の既定ラベル（legend_labels で上書きできる）
DEFAULT_LEGEND_LABELS = {
    "main": "主要タスク",
    "accent": "重点タスク",
    "muted": "確認・調整",
    "prep": "準備・付帯作業",
    "ongoing": "継続運用",
    "tbd": "要調整・未確定",
    "milestone": "マイルストーン",
    "today": "現在",
}

MAX_ROWS = 14            # これを超えると too-dense
MAX_MS_LEVELS = 3        # 節目ラベルの段数がこれを超えると milestone-crowded

_YM_RE = re.compile(r"^(\d{4})-(\d{1,2})$")
_YMD_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


# ---------------------------------------------------------------------------
# 時間軸
# ---------------------------------------------------------------------------

def _parse_ym(s):
    m = _YM_RE.match(str(s).strip())
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    return (y, mo) if 1 <= mo <= 12 else None


def _parse_ymd(s):
    m = _YMD_RE.match(str(s).strip())
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


class Axis:
    """列（時間軸）の定義。timeline から自動生成するか、columns を明示する。"""

    def __init__(self, slide: dict, diags: list):
        self.unit = None
        self.start_ym = None     # month 単位の先頭 (year, month)
        self.start_date = None   # week 単位の先頭日
        self.labels: List[str] = []
        tl = slide.get("timeline")
        cols = slide.get("columns")
        if tl is not None:
            self._from_timeline(tl, diags)
        if cols is not None:
            if not isinstance(cols, list) or not cols:
                diags.append(de.diag_error("invalid-columns", "columns",
                                           "columns は1個以上の文字列の配列で指定してください",
                                           fixes=["例: \"columns\": [\"9月\", \"10月\", \"11月\"]"]))
            elif self.labels and len(cols) != len(self.labels):
                diags.append(de.diag_error(
                    "columns-mismatch", "columns",
                    f"columns の数（{len(cols)}）が timeline から決まる列数（{len(self.labels)}）と一致しません",
                    {"columns": len(cols), "timeline": len(self.labels)},
                    ["columns を削除して timeline の自動ラベルを使う", "timeline の start / end を見直す"]))
            else:
                self.labels = [str(c) for c in cols]
        if not self.labels and not any(d["level"] == "error" for d in diags):
            diags.append(de.diag_error("missing-axis", "timeline",
                                       "時間軸がありません（timeline か columns のどちらかが必要です）",
                                       fixes=["\"timeline\": {\"start\": \"2026-09\", \"end\": \"2027-08\", \"unit\": \"month\"} を書く",
                                              "\"columns\": [\"9月\", \"10月\", ...] を書く"]))

    def _from_timeline(self, tl, diags):
        if not isinstance(tl, dict):
            diags.append(de.diag_error("invalid-timeline", "timeline", "timeline はオブジェクトで指定してください"))
            return
        unit = tl.get("unit", "month")
        if unit not in TIMELINE_UNITS:
            diags.append(de.diag_error("invalid-timeline", "timeline",
                                       f"timeline.unit '{unit}' は未対応です（month / week のみ）"))
            return
        self.unit = unit
        if unit == "month":
            a, b = _parse_ym(tl.get("start", "")), _parse_ym(tl.get("end", ""))
            if not a or not b:
                diags.append(de.diag_error("invalid-timeline", "timeline",
                                           "timeline.start / end は \"YYYY-MM\" 形式で指定してください（unit=month）",
                                           {"start": tl.get("start"), "end": tl.get("end")}))
                return
            n = (b[0] - a[0]) * 12 + (b[1] - a[1]) + 1
            if n < 1:
                diags.append(de.diag_error("invalid-timeline", "timeline", "timeline.end が start より前です"))
                return
            self.start_ym = a
            for k in range(n):
                y, mo = divmod(a[1] - 1 + k, 12)
                self.labels.append(f"{mo + 1}月")
        else:
            a, b = _parse_ymd(tl.get("start", "")), _parse_ymd(tl.get("end", ""))
            if not a or not b:
                diags.append(de.diag_error("invalid-timeline", "timeline",
                                           "timeline.start / end は \"YYYY-MM-DD\" 形式で指定してください（unit=week）",
                                           {"start": tl.get("start"), "end": tl.get("end")}))
                return
            if b < a:
                diags.append(de.diag_error("invalid-timeline", "timeline", "timeline.end が start より前です"))
                return
            self.start_date = a
            n = (b - a).days // 7 + 1
            for k in range(n):
                d = a + _dt.timedelta(days=7 * k)
                self.labels.append(f"{d.month}/{d.day}")

    @property
    def n(self) -> int:
        return len(self.labels)

    def _date_pos(self, d: _dt.date, end: bool) -> float:
        if self.unit == "month":
            y0, m0 = self.start_ym
            idx = (d.year - y0) * 12 + (d.month - m0)
            dim = calendar.monthrange(d.year, d.month)[1]
            return idx + (d.day if end else d.day - 1) / dim
        return ((d - self.start_date).days + (1 if end else 0)) / 7.0

    def pos(self, value, role: str) -> Optional[float]:
        """role: "start" / "end" / "at"。解釈できなければ None。"""
        end = role in ("end", "at")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if s in self.labels:
            i = self.labels.index(s)
            return float(i + (1 if role == "end" else 0.5 if role == "at" else 0))
        if self.unit:
            d = _parse_ymd(s)
            if d:
                return self._date_pos(d, end)
            ym = _parse_ym(s)
            if ym:
                first = _dt.date(ym[0], ym[1], 1)
                last = _dt.date(ym[0], ym[1], calendar.monthrange(ym[0], ym[1])[1])
                return self._date_pos(last, True) if role == "end" else self._date_pos(first, False)
        return None

    def short_label(self, value) -> str:
        d = _parse_ymd(str(value)) if not isinstance(value, (int, float)) else None
        return f"{d.month}/{d.day}" if d else ""


# ---------------------------------------------------------------------------
# 検証
# ---------------------------------------------------------------------------

def _row_name(r: dict, i: int) -> str:
    return f"rows[{i}]「{r.get('label', '')}」"


def validate_schedule(slide: dict) -> list:
    """スキーマ的な検証（ビルドを止める error を含む）。幾何の診断は layout_schedule() が返す。"""
    diags: list = []
    axis = Axis(slide, diags)
    if any(d["level"] == "error" for d in diags):
        return diags
    rows = slide.get("rows")
    if not isinstance(rows, list) or not rows:
        diags.append(de.diag_error("missing-rows", "rows", "rows は1個以上の配列で指定してください"))
        return diags
    n = axis.n

    def check_pos(val, role, subject):
        p = axis.pos(val, role)
        if p is None:
            hint = "数値（列単位）/ columns のラベル / \"YYYY-MM\" / \"YYYY-MM-DD\""
            if not axis.unit:
                hint = "数値（列単位）/ columns のラベル（日付で書くには timeline を指定する）"
            diags.append(de.diag_error("invalid-position", subject,
                                       f"{subject} の {role}「{val}」を時間軸上の位置として解釈できません",
                                       {"value": val}, [f"{hint} のいずれかで書く"]))
            return None
        if p < -1e-6 or p > n + 1e-6:
            diags.append(de.diag_error("out-of-range", subject,
                                       f"{subject} の {role}「{val}」が時間軸（{axis.labels[0]}〜{axis.labels[-1]}）の範囲外です",
                                       {"value": val, "pos": round(p, 3), "cols": n},
                                       ["timeline / columns の範囲を広げる", "日付・列を範囲内に直す"]))
            return None
        return p

    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            diags.append(de.diag_error("invalid-row", f"rows[{i}]", f"rows[{i}] はオブジェクトで指定してください"))
            continue
        name = _row_name(r, i)
        if not r.get("label"):
            diags.append(de.diag_warn("missing-label", name, f"{name} に label がありません"))
        bars = r.get("bars", [])
        if not isinstance(bars, list):
            diags.append(de.diag_error("invalid-bars", name, f"{name} の bars は配列で指定してください"))
            bars = []
        spans = []
        for j, b in enumerate(bars):
            subj = f"{name}.bars[{j}]"
            if not isinstance(b, dict):
                diags.append(de.diag_error("invalid-bar", subj, f"{subj} はオブジェクトで指定してください"))
                continue
            if "start" not in b or "end" not in b:
                diags.append(de.diag_error("invalid-bar", subj, f"{subj} には start と end が必要です"))
                continue
            a = check_pos(b["start"], "start", subj)
            z = check_pos(b["end"], "end", subj)
            if a is not None and z is not None:
                if z - a <= 1e-6:
                    diags.append(de.diag_error("empty-bar", subj,
                                               f"{subj} の end（{b['end']}）が start（{b['start']}）以前です",
                                               fixes=["start と end を入れ替える / 期間を見直す"]))
                else:
                    spans.append((a, z, subj))
            v = b.get("variant", "main")
            if v not in BAR_VARIANTS:
                diags.append(de.diag_warn("unknown-variant", subj,
                                          f"{subj} の variant '{v}' は未知です（main として描きます）",
                                          fixes=[f"{' / '.join(BAR_VARIANTS)} のいずれかにする"]))
            sh = b.get("shape", "arrow")
            if sh not in BAR_SHAPES:
                diags.append(de.diag_warn("unknown-shape", subj,
                                          f"{subj} の shape '{sh}' は未知です（arrow として描きます）",
                                          fixes=[f"{' / '.join(BAR_SHAPES)} のいずれかにする"]))
        spans.sort()
        for (a1, z1, s1), (a2, z2, s2) in zip(spans, spans[1:]):
            if a2 < z1 - 1e-3:
                diags.append(de.diag_warn("bar-overlap", name,
                                          f"{s1} と {s2} の期間が重なっていて、矢羽根が重なって描かれます",
                                          {"overlap_cols": round(z1 - a2, 3)},
                                          ["片方を別の行に分ける", "期間を見直して前後に並べる"]))
        ms = r.get("milestones", [])
        if not isinstance(ms, list):
            diags.append(de.diag_error("invalid-milestones", name, f"{name} の milestones は配列で指定してください"))
            ms = []
        for j, m in enumerate(ms):
            subj = f"{name}.milestones[{j}]"
            if not isinstance(m, dict) or "at" not in m:
                diags.append(de.diag_error("invalid-milestone", subj, f"{subj} には at（位置）が必要です"))
                continue
            check_pos(m["at"], "at", subj)
    if slide.get("today") is not None:
        check_pos(slide["today"], "at", "today")
    periods = slide.get("periods")
    if periods is not None:
        if not isinstance(periods, list):
            diags.append(de.diag_error("invalid-periods", "periods", "periods は配列で指定してください"))
        else:
            total = 0
            for k, p in enumerate(periods):
                sp = p.get("span") if isinstance(p, dict) else None
                if not isinstance(sp, int) or isinstance(sp, bool) or sp < 1:
                    diags.append(de.diag_error("invalid-periods", f"periods[{k}]",
                                               f"periods[{k}] には 1 以上の整数の span（列数）が必要です"))
                    continue
                total += sp
            if total > n:
                diags.append(de.diag_error("invalid-periods", "periods",
                                           f"periods の span 合計（{total}）が列数（{n}）を超えています"))
            elif 0 < total < n:
                diags.append(de.diag_warn("periods-short", "periods",
                                          f"periods の span 合計（{total}）が列数（{n}）より少なく、右端の見出しが空きます"))
    if len(rows) > MAX_ROWS:
        diags.append(de.diag_warn("too-dense", "rows",
                                  f"行数 {len(rows)} は多すぎます（目安 {MAX_ROWS} 行以下）",
                                  fixes=["スライドを分ける", "細かいタスクを1行にまとめる"]))
    return diags


# ---------------------------------------------------------------------------
# レイアウト
# ---------------------------------------------------------------------------

def chart_region(slide: dict, c: dict) -> dict:
    """lead の有無で図の上端を決める（lead が無ければ上へ詰めて縦を広く使う）。"""
    if slide.get("lead"):
        return {"x": c["x"], "y": c["y"], "w": c["w"], "h": c["h"]}
    return {"x": c["x"], "y": c.get("y_no_lead", c["y"]), "w": c["w"],
            "h": c.get("h_no_lead", c["h"])}


def _fit_size(text: str, avail: float, size: float, min_size: float) -> float:
    s = size
    while s > min_size and de.text_width(text, s) > avail:
        s -= 0.5
    return s


def _bar_geometry(x0: float, x1: float, y: float, h: float, shape: str, head_max: float):
    """矢羽根の外形（polygon 頂点）・矢頭の深さ・テキスト領域。PPTX のプリセット図形
    （homePlate / chevron）の adj 定義と同じ式で頂点とテキスト領域を決め、HTML と一致させる。"""
    w = x1 - x0
    if shape == "bar":
        return {"points": [(x0, y), (x1, y), (x1, y + h), (x0, y + h)], "head": 0.0,
                "tx": x0, "tw": w}
    head = min(head_max, h / 2, w * 0.45)
    if shape == "chevron":
        pts = [(x0, y), (x1 - head, y), (x1, y + h / 2), (x1 - head, y + h), (x0, y + h), (x0 + head, y + h / 2)]
        return {"points": pts, "head": head, "tx": x0 + head, "tw": max(1.0, w - 2 * head)}
    pts = [(x0, y), (x1 - head, y), (x1, y + h / 2), (x1 - head, y + h), (x0, y + h)]
    return {"points": pts, "head": head, "tx": x0, "tw": max(1.0, w - head / 2)}


def _legend_plan(slide: dict, axis: "Axis", c: dict, rg: dict, diags: list) -> dict:
    """凡例の項目（使われた variant ＋ 節目 ＋ 現在線）と並べ方を決める。1行に収まらなければ
    文字を最大2px縮め、それでも収まらなければ折り返す（その分だけ図の行の高さが減る）。"""
    n = axis.n
    labels = dict(DEFAULT_LEGEND_LABELS)
    custom = slide.get("legend_labels") or {}
    labels.update({k: str(v) for k, v in custom.items()})
    used, has_ms = set(), False

    def ok(v, role):
        p = axis.pos(v, role)
        return p is not None and -1e-6 <= p <= n + 1e-6

    for r in slide.get("rows", []) or []:
        if not isinstance(r, dict):
            continue
        for b in r.get("bars", []) or []:
            if isinstance(b, dict) and ok(b.get("start"), "start") and ok(b.get("end"), "end"):
                v = b.get("variant", "main")
                used.add(v if v in BAR_VARIANTS else "main")
        for m in r.get("milestones", []) or []:
            if isinstance(m, dict) and ok(m.get("at"), "at"):
                has_ms = True
    items = [{"kind": "bar", "variant": v, "label": labels[v]} for v in BAR_VARIANTS if v in used]
    if has_ms:
        items.append({"kind": "milestone", "label": labels["milestone"]})
    if slide.get("today") is not None and ok(slide["today"], "at"):
        tl = labels["today"]
        short = axis.short_label(slide["today"])
        if "today" not in custom and short:
            tl = f"{tl}（{short}）"
        items.append({"kind": "today", "label": tl})

    note = str(slide.get("note", "") or "")
    sym_w, gap = c.get("legend_sym_w", 34), 18
    width = rg["w"] - 8
    base, nbase = c.get("legend_size", 12), c.get("note_size", 12)

    def widths(size):
        return [(12 if it["kind"] != "bar" else sym_w) + 6 + de.text_width(it["label"], size) + 2 for it in items]

    size = base
    for cand in (base, base - 1, base - 2):
        nsz = min(nbase, cand)
        ws = widths(cand)
        nw = de.text_width(note, nsz) + 2 if note else 0
        if sum(ws) + gap * max(0, len(ws) - 1) + (nw + 24 if note else 0) <= width:
            size = cand
            break
    else:
        size = max(10, base - 2)
    nsize = min(nbase, size)
    note_w = de.text_width(note, nsize) + 2 if note else 0
    line_h = 20
    line, lx = 0, rg["x"] + 4
    for it, w in zip(items, widths(size)):
        if lx > rg["x"] + 4 and lx + w > rg["x"] + 4 + width:
            line, lx = line + 1, rg["x"] + 4
        sw = 12 if it["kind"] != "bar" else sym_w
        it.update(x=lx, line=line, sym_w=sw, sym_h=14, size=size, tx=lx + sw + 6,
                  tw=de.text_width(it["label"], size) + 2)
        lx += w + gap
    note_line = line
    if note and lx + note_w > rg["x"] + rg["w"]:
        note_line = line + 1
    lines = max(note_line, line) + 1
    if lines > 1:
        diags.append(de.diag_info("legend-wrapped", "legend",
                                  f"凡例が1行に収まらないため {lines} 行に折り返しました（図の行の高さが減ります）",
                                  fixes=["legend_labels で凡例ラベルを短くする", "note を短くする"]))
    return {"items": items, "line_h": line_h, "h": max(c.get("legend_h", 28), 8 + lines * line_h),
            "note": note, "note_size": nsize, "note_w": note_w, "note_line": note_line,
            "note_x": rg["x"] + rg["w"] - note_w}


def layout_schedule(slide: dict, c: dict) -> dict:
    """スタイル c（resolve 済みの style.chart）からジオメトリを計算する。
    validate_schedule() で error が無いことを前提にする（不正な位置は描かずに飛ばす）。"""
    diags: list = []
    axis = Axis(slide, [])
    rg = chart_region(slide, c)
    rows = [r for r in slide.get("rows", []) if isinstance(r, dict)]
    n = max(1, axis.n)

    has_groups = any(r.get("group") for r in rows)
    group_w = c.get("group_w", 34) if has_groups else 0
    label_w = c.get("label_w", 260)
    x_lab = rg["x"] + group_w
    tx0 = x_lab + label_w
    tw = rg["x"] + rg["w"] - tx0
    col_w = tw / n

    def X(p):
        return tx0 + p * col_w

    periods = slide.get("periods") or []
    period_h = c.get("period_h", 30) if periods else 0
    col_h = c.get("col_h", 28)
    legend_on = slide.get("legend", True) is not False
    legend = _legend_plan(slide, axis, c, rg, diags) if legend_on else None
    legend_h = legend["h"] if legend else 0
    head_y = rg["y"]
    body_y = head_y + period_h + col_h
    area = rg["h"] - period_h - col_h - legend_h

    # 節目ラベルの段組み（同じ行の中で横に重なるラベルは下の段へ）
    ms_size = c.get("milestone_label_size", 12)
    ms_d = c.get("milestone_size", 16)
    ms_line = ms_size * 1.35
    ms_layout = {}
    for ri, r in enumerate(rows):
        items = []
        for m in r.get("milestones", []) or []:
            if not isinstance(m, dict):
                continue
            p = axis.pos(m.get("at"), "at")
            if p is None or p < 0 or p > n:
                continue
            label = str(m.get("label", ""))
            lw = de.text_width(label, ms_size) + 4
            items.append({"p": p, "label": label, "lw": lw})
        items.sort(key=lambda it: it["p"])
        level_right: List[float] = []
        for it in items:
            cx = X(it["p"])
            lx = min(max(cx - it["lw"] / 2, tx0 + 2), tx0 + tw - it["lw"] - 2)
            lv = 0
            while lv < len(level_right) and lx < level_right[lv] + 6:
                lv += 1
            if lv == len(level_right):
                level_right.append(-1e9)
            level_right[lv] = lx + it["lw"]
            it.update(cx=cx, lx=lx, level=lv)
        levels = len(level_right)
        if levels > MAX_MS_LEVELS:
            diags.append(de.diag_warn("milestone-crowded", _row_name(r, ri),
                                      f"{_row_name(r, ri)} の節目ラベルが近接していて {levels} 段に積まれています",
                                      {"levels": levels},
                                      ["ラベルを短くする", "節目を別の行に分ける", "label_w を小さくして時間軸を広げる"]))
        ms_layout[ri] = (items, levels)

    # 行の高さ: 節目のある行は必要高さを確保し、残りを他の行で等分（min/max で制限）
    min_h, max_h = c.get("min_row_h", 28), c.get("max_row_h", 54)
    need = {}
    for ri, (items, levels) in ms_layout.items():
        if items:
            need[ri] = 8 + ms_d + 4 + levels * ms_line + 6
    plain = [ri for ri in range(len(rows)) if ri not in need]
    rest = area - sum(need.values())
    base = rest / len(plain) if plain else max_h
    if base < min_h:
        diags.append(de.diag_warn("too-dense", "rows",
                                  f"行が多く1行の高さが {base:.0f}px になります（目安 {min_h}px 以上）",
                                  {"row_h": round(base, 1)},
                                  ["スライドを分ける", "lead を削って縦を広げる", "style.chart.min_row_h を下げる"]))
    base = max(min_h, min(max_h, base))
    heights = [max(need.get(ri, 0), base) if ri in need else base for ri in range(len(rows))]

    geo = {"region": rg, "tx0": tx0, "tw": tw, "col_w": col_w, "n": n,
           "periods": [], "columns": [], "groups": [], "rows": [], "vlines": [], "hlines": [],
           "bars": [], "milestones": [], "today": None, "legend": None, "diagnostics": diags}

    # 見出し（期間・列）
    x = tx0
    for p in periods:
        if not isinstance(p, dict) or not isinstance(p.get("span"), int):
            continue
        w = p["span"] * col_w
        label = str(p.get("label", ""))
        size = _fit_size(label, w - 8, c.get("period_size", 15), 10)
        geo["periods"].append({"x": x, "y": head_y, "w": w, "h": period_h, "label": label, "size": size})
        x += w
    col_size = c.get("col_size", 13)
    for k, lab in enumerate(axis.labels):
        size = _fit_size(lab, col_w - 4, col_size, 8)
        geo["columns"].append({"x": X(k), "y": head_y + period_h, "w": col_w, "h": col_h, "label": lab, "size": size})
    if geo["columns"] and min(cc["size"] for cc in geo["columns"]) < col_size - 2:
        diags.append(de.diag_info("column-label-shrunk", "columns",
                                  "列幅が狭いため列見出しの文字を縮小しました",
                                  fixes=["列見出しを短くする（例: \"2026年9月\" → \"9月\"）", "label_w を小さくする"]))

    # 行・グループ
    y = body_y
    lab_size, sub_size = c.get("label_size", 15), c.get("sub_size", 11)
    for ri, r in enumerate(rows):
        h = heights[ri]
        label, sub = str(r.get("label", "")), str(r.get("sub", "") or "")
        avail = label_w - 2 * c.get("label_pad", 10)
        # 行が低いときは label＋sub の2段が行に収まるよう文字サイズを比例で縮める
        need_h = (lab_size + (sub_size if sub else 0)) * 1.3 + 4
        k = min(1.0, h / need_h)
        ls = _fit_size(label, avail, max(10, lab_size * k), 10)
        ss = _fit_size(sub, avail, max(8, sub_size * k), 8) if sub else sub_size
        if de.text_width(label, ls) > avail:
            diags.append(de.diag_warn("row-label-overflow", _row_name(r, ri),
                                      f"{_row_name(r, ri)} の label が左の見出し欄に収まりません",
                                      fixes=["label を短くし、補足は sub に移す", "style.chart.label_w を広げる"]))
        geo["rows"].append({"x": x_lab, "y": y, "w": label_w, "h": h, "label": label, "sub": sub,
                            "size": ls, "sub_size": ss, "alt": ri % 2 == 1, "group": r.get("group")})
        # 矢羽根
        bar_h = min(c.get("bar_max_h", 30), h * c.get("bar_hr", 0.64))
        gap = c.get("bar_gap", 3) / 2
        for j, b in enumerate(r.get("bars", []) or []):
            if not isinstance(b, dict):
                continue
            a, z = axis.pos(b.get("start"), "start"), axis.pos(b.get("end"), "end")
            if a is None or z is None or z <= a:
                continue
            a, z = max(0.0, a), min(float(n), z)
            x0, x1 = X(a) + gap, X(z) - gap
            shape = b.get("shape", "arrow") if b.get("shape", "arrow") in BAR_SHAPES else "arrow"
            variant = b.get("variant", "main") if b.get("variant", "main") in BAR_VARIANTS else "main"
            by = y + (h - bar_h) / 2
            g = _bar_geometry(x0, x1, by, bar_h, shape, c.get("bar_head", 14))
            label = str(b.get("label", "") or "")
            pos = b.get("label_pos", "inside")
            size = c.get("bar_size", 13)
            if label and pos != "after":
                size = _fit_size(label, g["tw"] - 8, size, c.get("bar_min_size", 10))
                if de.text_width(label, size) > g["tw"] - 8:
                    diags.append(de.diag_warn(
                        "bar-label-overflow", f"{_row_name(r, ri)}.bars[{j}]",
                        f"{_row_name(r, ri)}.bars[{j}] のラベル「{label}」が矢羽根の中に収まりません",
                        {"bar_w": round(x1 - x0, 1), "need_w": round(de.text_width(label, size) + 8, 1)},
                        ["ラベルを短くする", "\"label_pos\": \"after\" で矢羽根の右に出す",
                         "style.chart.label_w を小さくして時間軸を広げる"]))
            geo["bars"].append({"x": x0, "y": by, "w": x1 - x0, "h": bar_h, "shape": shape,
                                "variant": variant, "label": label, "size": size, "label_pos": pos,
                                "points": g["points"], "head": g["head"], "tx": g["tx"], "tw": g["tw"],
                                "row": ri})
        # 節目
        items, _levels = ms_layout.get(ri, ([], 0))
        dy = y + 8
        for it in items:
            geo["milestones"].append({"cx": it["cx"], "cy": dy + ms_d / 2, "d": ms_d, "label": it["label"],
                                      "lx": it["lx"], "ly": dy + ms_d + 4 + it["level"] * ms_line,
                                      "lw": it["lw"], "lh": ms_line, "size": ms_size, "row": ri})
        y += h
    body_bottom = y

    # 左端のグループ帯（連続する同じ group をまとめる）
    if has_groups:
        k = 0
        while k < len(geo["rows"]):
            gname = geo["rows"][k]["group"]
            k2 = k
            while k2 + 1 < len(geo["rows"]) and geo["rows"][k2 + 1]["group"] == gname:
                k2 += 1
            if gname:
                top, bot = geo["rows"][k]["y"], geo["rows"][k2]["y"] + geo["rows"][k2]["h"]
                geo["groups"].append({"x": rg["x"], "y": top, "w": group_w, "h": bot - top, "label": str(gname)})
            k = k2 + 1

    # 罫線: 列境界（期間境界は太く）と行境界（グループ境界は太く）
    pbounds = set()
    acc = 0
    for p in periods:
        if isinstance(p, dict) and isinstance(p.get("span"), int):
            acc += p["span"]
            pbounds.add(acc)
    for k in range(n + 1):
        geo["vlines"].append({"x": X(k), "y1": head_y + period_h, "y2": body_bottom,
                              "strong": k in pbounds or k in (0, n)})
    prev_group = object()
    for rr in geo["rows"]:
        strong = has_groups and rr["group"] != prev_group
        geo["hlines"].append({"y": rr["y"], "x1": rg["x"] + group_w, "x2": rg["x"] + rg["w"], "strong": strong})
        prev_group = rr["group"]
    geo["hlines"].append({"y": body_bottom, "x1": rg["x"], "x2": rg["x"] + rg["w"], "strong": True})

    # 現在線
    if slide.get("today") is not None:
        p = axis.pos(slide["today"], "at")
        if p is not None and 0 <= p <= n:
            geo["today"] = {"x": X(p), "y1": head_y + period_h + col_h, "y2": body_bottom,
                            "label": axis.short_label(slide["today"])}

    # 凡例（位置の割り付けは _legend_plan 済み。ここでは図の下端に合わせて y を決めるだけ）
    if legend:
        y0 = body_bottom + 8
        for it in legend["items"]:
            it["y"] = y0 + it.pop("line") * legend["line_h"]
        geo["legend"] = {"note_y": y0 + legend["note_line"] * legend["line_h"], "h": 14, "items": legend["items"],
                         "note": legend["note"], "note_size": legend["note_size"],
                         "note_x": legend["note_x"], "note_w": legend["note_w"]}
    return geo

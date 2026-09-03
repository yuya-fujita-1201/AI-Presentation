#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""図解タイプ（architecture / dataflow / lifecycle / sequence / swimlane）の機械診断。

Archify（https://github.com/tt-a1i/archify ）の `validate --json` に相当する。ビルドせずに
deck.json だけを読み、図解スライドごとに次を検査して「修理指示（fixes）」付きで報告する:

  スキーマ  : id 重複 / 未知 id / セル衝突（同じ row,col）/ 範囲外 / 未対応 type・variant・kind
  配線      : エッジがノードを横切る（edge-through-node）/ 交差数 / 無関係な線の重なり / 短すぎる線
  ラベル    : ラベルがノード・他ラベルと重なる（label-collision）→ 候補座標を label_at として提示
  文字      : ノード内の label/sublabel が箱に収まらない（node-text-overflow）
  密度      : ノード > 12、列 > 6、メッセージ > 12（too-dense）
  グループ  : 範囲内に非メンバーが入る（group-leak）

使い方:
    python tools/check_diagram.py <deck_dir>                 # テキスト報告（exit 1 = error あり）
    python tools/check_diagram.py <deck_dir> --json out.json # JSON 出力（code / subject / evidence / fixes）
    python tools/check_diagram.py <deck_dir> --strict        # warning も不合格にする
    python tools/check_diagram.py <deck_dir> --slides 3 7    # 対象スライド（deck.json 内の番号）

修理ループの規約（create-deck スキル参照）: 報告された fixes のうち **1 点だけ**を deck.json に
反映して再実行する。2 ラウンド続けて件数が減らなければ止めて、残った診断をそのまま報告する。
Playwright / python-pptx は不要（純 Python）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import build_deck  # noqa: E402
import diagram_engine as de  # noqa: E402

DIAGRAM_TYPES = ("architecture", "dataflow", "lifecycle", "sequence", "swimlane")


def diagnose_slide(slide: dict, st: dict, t: str):
    """1 スライド分の診断リストを返す（fail せずに集める）。"""
    diags = []
    if t in ("architecture", "dataflow", "lifecycle"):
        diags += de.validate_grid_diagram(slide, t)
        if not any(d["level"] == "error" for d in diags):
            geo = de.layout_grid_diagram(slide, t, st["diagram"], [])
            diags += geo["diagnostics"]
    elif t == "sequence":
        de.layout_sequence(slide, st["diagram"], diags)
    elif t == "swimlane":
        # スキーマ的な検証は build_deck の fail() を捕まえて error に変換する
        try:
            build_deck._validate_swimlane(slide, 0, t)
        except SystemExit as ex:
            msg = str(ex).replace("error: ", "").replace("1枚目（type=swimlane）: ", "")
            diags.append(de.diag_error("schema", "swimlane", msg, {}, ["メッセージに沿って deck.json を直す"]))
            return diags
        geo = build_deck.swimlane_geometry(slide, st)
        diags += geo.get("diagnostics", [])
    return diags


def main():
    build_deck.setup_console()
    ap = argparse.ArgumentParser(description="図解スライドの機械診断（Archify validate 相当）")
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="結果 JSON の出力先")
    ap.add_argument("--strict", action="store_true", help="warning も不合格（exit 1）にする")
    ap.add_argument("--slides", nargs="*", type=int, help="対象スライド番号（deck.json 内の順、1 始まり）")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    if not (deck_dir / "deck.json").exists():
        build_deck.fail(f"{deck_dir / 'deck.json'} が見つかりません")
    deck, theme, layout = build_deck.load_deck(deck_dir)
    slides = deck.get("slides", [])
    report = {"deck": str(deck_dir), "slides": [], "summary": {"error": 0, "warning": 0, "info": 0}}
    checked = 0
    for i, slide in enumerate(slides):
        if args.slides and (i + 1) not in args.slides:
            continue
        t = slide.get("type")
        if t not in DIAGRAM_TYPES:
            continue
        checked += 1
        try:
            st = build_deck.resolve_style(layout, deck, slide)
        except SystemExit as ex:
            report["slides"].append({"index": i + 1, "type": t, "diagnostics": [
                de.diag_error("schema", "style", str(ex).replace("error: ", ""), {}, [])]})
            report["summary"]["error"] += 1
            continue
        diags = diagnose_slide(slide, st, t)
        for d in diags:
            report["summary"][d["level"]] = report["summary"].get(d["level"], 0) + 1
        report["slides"].append({"index": i + 1, "type": t, "diagnostics": diags})

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    for entry in report["slides"]:
        for d in entry["diagnostics"]:
            mark = {"error": "error", "warning": "warning", "info": "note"}.get(d["level"], d["level"])
            print(f"{mark}: {entry['index']}枚目（type={entry['type']}）: {de.format_diagnostic(d)}")
    s = report["summary"]
    print(f"check_diagram: 図解スライド {checked} 枚 error={s['error']} warning={s['warning']} info={s['info']}"
          + ("（--strict）" if args.strict else ""))
    bad = s["error"] + (s["warning"] if args.strict else 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

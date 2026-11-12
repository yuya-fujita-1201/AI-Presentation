#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""図解タイプ（architecture / dataflow / lifecycle / sequence / swimlane / schedule）の機械診断。

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
    python tools/check_diagram.py <deck_dir> --slides 3 7    # 対象スライド（プレビュー PNG と同じ番号）

スライド番号は preview_deck.py の PNG（slide-NN.png）・check_layout.py と同じ番号（凡例ページの自動挿入・
agenda の分割込み。--slides もこの番号）。deck.json の何枚目かは「deck.json N枚目」として併記する
（JSON では index / slide が PNG の番号、src が deck.json の番号）。

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
import diagram_scale as dscale  # noqa: E402

DIAGRAM_TYPES = ("architecture", "dataflow", "lifecycle", "sequence", "swimlane", "schedule")


def diagnose_slide(slide: dict, st: dict, t: str):
    """1 スライド分の診断リストを返す（fail せずに集める）。"""
    diags = []
    if t in ("architecture", "dataflow", "lifecycle"):
        diags += de.validate_grid_diagram(slide, t)
        if not any(d["level"] == "error" for d in diags):
            geo = dscale.layout_grid(slide, t, st["diagram"], [])
            diags += geo["diagnostics"]
    elif t == "sequence":
        dscale.layout_seq(slide, st["diagram"], diags)
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
    elif t == "schedule":
        diags += build_deck.se.validate_schedule(slide)
        if not any(d["level"] == "error" for d in diags):
            diags += build_deck.se.layout_schedule(slide, st["chart"])["diagnostics"]
    return diags


def main():
    build_deck.setup_console()
    ap = argparse.ArgumentParser(description="図解スライドの機械診断（Archify validate 相当）")
    ap.add_argument("deck_dir")
    ap.add_argument("--json", help="結果 JSON の出力先")
    ap.add_argument("--strict", action="store_true", help="warning も不合格（exit 1）にする")
    ap.add_argument("--slides", nargs="*", type=int,
                    help="対象スライド番号（プレビュー PNG・check_layout.py と同じ番号。凡例ページの自動挿入込み、1 始まり）")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    if not (deck_dir / "deck.json").exists():
        build_deck.fail(f"{deck_dir / 'deck.json'} が見つかりません")
    deck, theme, layout = build_deck.load_deck(deck_dir)
    # 展開（凡例ページの自動挿入・agenda の改ページ）後の番号 = プレビュー PNG の番号で数える。
    # deck.json の何枚目かは、展開前の dict との同一性から辿る（図解タイプは展開で複製されない。
    # スライドに印のキーを足すと検証が「未知のキー」と警告するので、キーは足さない）
    src_of = {id(s): i for i, s in enumerate(deck.get("slides", []), 1)}
    slides = build_deck.expand_slides(deck, layout)["slides"]
    report = {"deck": str(deck_dir), "slides": [], "summary": {"error": 0, "warning": 0, "info": 0}}
    checked = 0
    bad_nums = [n for n in (args.slides or []) if not 1 <= n <= len(slides)]
    if bad_nums:
        build_deck.fail(f"スライド番号が範囲外です（1〜{len(slides)}。preview_deck.py の PNG と同じ番号で、凡例ページ等の自動挿入込み）: {bad_nums}")
    for n, slide in enumerate(slides, 1):
        if args.slides and n not in args.slides:
            continue
        t = slide.get("type")
        if t in ("composite", "split"):
            # 合成スライド（split も）: 図解のブロックを、そのブロックの矩形で診断する（type 欄は「composite/ブロックのタイプ」）
            try:
                cst = build_deck.resolve_style(layout, deck, slide)
            except (SystemExit, Exception) as ex:   # noqa: BLE001 - 検証を通っていない deck でも、トレースバックではなく診断として報告する
                if isinstance(ex, SystemExit):
                    msg = str(ex).replace("error: ", "")
                else:
                    msg = (f"{n}枚目（type={t}）: ブロックの形が不正です（{type(ex).__name__}: {ex}）"
                           f" → build_deck.py を実行すると、場所と直し方つきのエラーが出る")
                report["slides"].append({"index": n, "slide": n, "src": src_of.get(id(slide)), "build_page": n, "type": t,
                                         "diagnostics": [de.diag_error("schema", "style", msg, {}, [])]})
                report["summary"]["error"] += 1
                checked += 1
                continue
            for rb in (cst.get("_composite") or {}).get("blocks", []):
                if rb["type"] not in DIAGRAM_TYPES or rb["bs"] is None:
                    continue
                checked += 1
                head = {"index": n, "slide": n, "src": src_of.get(id(slide)), "build_page": n,
                        "type": f"{t}/{rb['type']}（{rb['index'] + 1} つ目のブロック）"}
                diags = diagnose_slide(rb["bs"], rb["st"], rb["type"])
                for d in diags:
                    report["summary"][d["level"]] = report["summary"].get(d["level"], 0) + 1
                report["slides"].append(dict(head, diagnostics=diags))
            continue
        if t not in DIAGRAM_TYPES:
            continue
        checked += 1
        src = src_of.get(id(slide))
        head = {"index": n, "slide": n, "src": src, "build_page": n, "type": t}
        try:
            st = build_deck.resolve_style(layout, deck, slide)
        except SystemExit as ex:
            report["slides"].append(dict(head, diagnostics=[
                de.diag_error("schema", "style", str(ex).replace("error: ", ""), {}, [])]))
            report["summary"]["error"] += 1
            continue
        diags = diagnose_slide(slide, st, t)
        for d in diags:
            report["summary"][d["level"]] = report["summary"].get(d["level"], 0) + 1
        report["slides"].append(dict(head, diagnostics=diags))

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    for entry in report["slides"]:
        src = entry.get("src")
        page_note = f"（deck.json {src}枚目）" if src is not None else ""
        for d in entry["diagnostics"]:
            mark = {"error": "error", "warning": "warning", "info": "note"}.get(d["level"], d["level"])
            print(f"{mark}: {entry['index']}枚目{page_note}（type={entry['type']}）: {de.format_diagnostic(d)}")
    s = report["summary"]
    print(f"check_diagram: 図解スライド {checked} 枚 error={s['error']} warning={s['warning']} info={s['info']}"
          + ("（--strict）" if args.strict else ""))
    bad = s["error"] + (s["warning"] if args.strict else 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPTX の見た目を HTML のプレビューと 1 枚ずつ比べ、差の大きいスライドを報告する（警告のみ。exit 0）。

HTML（check_layout / check_visual が見ている側）と PPTX（利用者が PowerPoint で開く側）は別のレンダラで描かれるため、
折り返し位置・箱の高さ・文字サイズがずれることがある（HTML では収まるが PPTX では 2 行になる、など）。
このツールは soffice（LibreOffice）で PPTX を PDF にし、pdftoppm で PNG にして、build/preview の PNG と比べる。

  1. build/<id>.pptx → soffice → PDF → pdftoppm（96dpi = 1280x720）→ PNG
  2. build/preview/slide-NN.png（HTML）と 1 枚ずつ差分スコアを出す（compare_ref.py の diff_score を再利用）
  3. 差の大きい順に報告し、左（HTML）・右（PPTX）を並べた画像を build/pptx-compare/cmp-NN.png に出す

注意: LibreOffice の描画は PowerPoint と同じではありません（フォント代替・字幅・行間・図形の細部が違う）。
差が大きい＝壊れている、とは限らず、差が小さい＝PowerPoint で崩れない、とも限りません。
特に、濃い箱の中の明るい文字が箱の下へ溢れる（コード 40 行など）ような、背景に溶けて見えにくいはみ出しは、
画像の差分では拾えません（差が見本の平均程度にとどまる）。コード・長い表のスライドは cmp-NN.png を目で確かめてください。
どのスライドを目で確かめるべきかを絞るための参考値で、PowerPoint 実機での確認の代わりにはなりません。

soffice または pdftoppm が無い環境では、何が無いかを表示して終了します（exit 0）。警告のみで、不合格にはしません。

使い方:
    python tools/check_pptx.py <deck_dir> [--threshold 8.0] [--top 10] [--dpi 96] [--no-preview]
前提: build_deck.py <deck_dir> --pptx と、preview_deck.py（無ければ自動で実行する）。要: pillow
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import lo_profile  # noqa: E402

DISCLAIMER = ("※ LibreOffice の描画は PowerPoint と同じではありません（フォント代替・折り返し・行間が違う）。"
              "ここでの差は「目で確かめる候補」を絞る参考値で、PowerPoint 実機での確認の代わりにはなりません。")
THRESHOLD_DEFAULT = 8.0     # 差分スコアがこれ以上のスライドに印を付ける（template-sample の平均は約 4、最大約 10）


def _setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def find_soffice():
    try:
        from export_pdf import find_soffice as _f  # type: ignore
        return _f()
    except Exception:  # noqa: BLE001
        return shutil.which("soffice")


def find_pdftoppm():
    return shutil.which("pdftoppm")


def missing_tools(soffice, pdftoppm) -> list:
    """足りない道具の説明のリスト（空なら揃っている）。"""
    out = []
    if not soffice:
        out.append("soffice（LibreOffice。PPTX を PDF にする）: brew install --cask libreoffice または https://www.libreoffice.org/")
    if not pdftoppm:
        out.append("pdftoppm（poppler。PDF を PNG にする）: brew install poppler（macOS）/ apt install poppler-utils（Linux）")
    return out


def rank_scores(scores: dict, threshold: float) -> list:
    """{スライド番号: スコア} を [(番号, スコア, 要確認か)] に。差の大きい順。"""
    return [(n, s, s >= threshold) for n, s in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def page_number(path: Path):
    """pdftoppm の出力名（prefix-1.png / prefix-01.png / prefix-001.png）からページ番号を取り出す。"""
    m = re.search(r"-(\d+)\.png$", path.name)
    return int(m.group(1)) if m else None


def render_pptx_to_pngs(pptx: Path, soffice: str, pdftoppm: str, work: Path, dpi: int = 96, timeout: int = 240) -> dict:
    """PPTX → PDF → PNG。{ページ番号: PNG パス} を返す。失敗したら RuntimeError（理由つき）。"""
    work.mkdir(parents=True, exist_ok=True)
    profile = work / "lo-profile"   # 他の soffice 起動とプロファイルが衝突しないよう専用の場所を使う
    prof = lo_profile.prepare(profile, pptx)        # フォントの置き換えを固定する（変換のたびに代替フォントの組が変わるのを防ぐ）
    for src, dst in prof["pairs"]:                    # export_pdf.py と同じ note（どのフォントに置き換えて描くか。S5b）
        print(f"note: フォント '{src}' がこの環境に無いため、LibreOffice では '{dst}' に置き換えて描きます（PowerPoint の見え方とは字幅が違う）", file=sys.stderr)
    cmd = [soffice, prof["env"], "--headless", "--norestore",
           "--convert-to", "pdf", "--outdir", str(work), str(pptx)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"soffice の変換がタイムアウトしました（{timeout}秒）")
    pdf = work / f"{pptx.stem}.pdf"
    if proc.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"PDF 変換に失敗しました（soffice exit={proc.returncode}）: {(proc.stderr or proc.stdout or '')[-300:]}")
    prefix = work / "page"
    proc = subprocess.run([pdftoppm, "-png", "-r", str(dpi), str(pdf), str(prefix)], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"pdftoppm に失敗しました（exit={proc.returncode}）: {(proc.stderr or '')[-300:]}")
    pages = {}
    for p in sorted(work.glob("page-*.png")):
        n = page_number(p)
        if n is not None:
            pages[n] = p
    if not pages:
        raise RuntimeError("PDF から PNG が作られませんでした")
    return pages


def compare_deck(deck_dir: Path, pages: dict, out_dir: Path, threshold: float) -> dict:
    """build/preview の PNG と PPTX 側の PNG を 1 枚ずつ比べ、左右並べ画像を out_dir に書く。
    戻り値: {"scores": {n: score}, "ranked": [...], "missing_html": [...], "missing_pptx": [...]}"""
    from PIL import Image
    from compare_ref import diff_score, stack_images  # type: ignore
    prev = deck_dir / "build" / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("cmp-*.png"):   # 前回の残りを消す
        old.unlink()
    scores, missing_html = {}, []
    html_pngs = {}
    for p in prev.glob("slide-*.png"):
        try:
            html_pngs[int(p.stem.split("-")[1])] = p
        except (IndexError, ValueError):
            pass
    for n in sorted(set(html_pngs) | set(pages)):
        if n not in html_pngs:
            missing_html.append(n)
            continue
        if n not in pages:
            continue
        a = Image.open(html_pngs[n]).convert("RGB")
        b = Image.open(pages[n]).convert("RGB")
        scores[n] = diff_score(a, b)
        stack_images(a, b, horizontal=True, labels=("HTML (preview)", "PPTX (LibreOffice)")).save(out_dir / f"cmp-{n:02d}.png")
    missing_pptx = sorted(n for n in html_pngs if n not in pages)
    (out_dir / "scores.txt").write_text(
        "\n".join(f"{n:3d} {s:6.2f}" for n, s, _ in rank_scores(scores, threshold)), encoding="utf-8")
    return {"scores": scores, "ranked": rank_scores(scores, threshold), "missing_html": missing_html,
            "missing_pptx": missing_pptx}


def main(argv=None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="PPTX（LibreOffice で描画）と HTML プレビューを 1 枚ずつ比べて差の大きい順に報告する（警告のみ）")
    ap.add_argument("deck_dir")
    ap.add_argument("--threshold", type=float, default=THRESHOLD_DEFAULT, help=f"この差分スコア以上に印を付ける（既定 {THRESHOLD_DEFAULT}）")
    ap.add_argument("--top", type=int, default=10, help="表示する件数（既定 10。全件は scores.txt）")
    ap.add_argument("--dpi", type=int, default=96, help="PPTX を PNG にする解像度（96 で 1280x720）")
    ap.add_argument("--no-preview", action="store_true", help="build/preview が無くても preview_deck.py を自動実行しない")
    ap.add_argument("--json", help="結果を JSON で書き出す")
    args = ap.parse_args(argv)

    deck_dir = Path(args.deck_dir).resolve()
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        print(f"error: {deck_json} が見つかりません", file=sys.stderr)
        return 1
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    pptx = deck_dir / "build" / f"{deck_id}.pptx"
    html = deck_dir / "build" / f"{deck_id}.html"

    soffice, pdftoppm = find_soffice(), find_pdftoppm()
    miss = missing_tools(soffice, pdftoppm)
    if miss:
        print("check_pptx: 次の道具が無いため PPTX の見た目比較を行いません（警告のみ・不合格にはしません）:")
        for m in miss:
            print(f"  - {m}")
        print("  代わりに PowerPoint / Keynote で build/<id>.pptx を開いて目視で確認する（verify_pptx.py は道具なしで使えます）")
        return 0
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("check_pptx: pillow が無いため比較できません（/slide-deck:setup --pillow）。警告のみ・不合格にはしません")
        return 0
    if not pptx.exists():
        print(f"error: {pptx} がありません。先に build_deck.py {deck_dir} --pptx を実行してください", file=sys.stderr)
        return 1
    prev = deck_dir / "build" / "preview"
    if not list(prev.glob("slide-*.png")) and not args.no_preview:
        if not html.exists():
            print(f"error: {html} がありません。先に build_deck.py {deck_dir} --html を実行してください", file=sys.stderr)
            return 1
        print("note: build/preview が無いので preview_deck.py を実行します", file=sys.stderr)
        subprocess.run([sys.executable, str(TOOLS_DIR / "preview_deck.py"), str(deck_dir)], stdout=subprocess.DEVNULL)
    if not list(prev.glob("slide-*.png")):
        print(f"error: {prev} にプレビュー画像がありません。preview_deck.py {deck_dir} を実行してください", file=sys.stderr)
        return 1

    out_dir = deck_dir / "build" / "pptx-compare"
    with tempfile.TemporaryDirectory(prefix="check-pptx-") as tmp:
        try:
            pages = render_pptx_to_pngs(pptx, soffice, pdftoppm, Path(tmp), args.dpi)
        except RuntimeError as e:
            print(f"check_pptx: PPTX を画像にできませんでした（警告のみ）: {e}")
            return 0
        res = compare_deck(deck_dir, pages, out_dir, args.threshold)

    ranked = res["ranked"]
    flagged = [r for r in ranked if r[2]]
    for n, sc, flag in ranked[: args.top]:
        mark = "  ← 目で確かめる" if flag else ""
        print(f"slide-{n:02d}: 差 {sc:5.2f}{mark}  ({out_dir / f'cmp-{n:02d}.png'})")
    if res["missing_pptx"]:
        print(f"warn: HTML にあって PPTX の描画に無い番号: {res['missing_pptx'][:10]}（枚数が一致しません。凡例ページ・agenda の分割を確認）")
    if res["missing_html"]:
        print(f"warn: PPTX にあって HTML プレビューに無い番号: {res['missing_html'][:10]}（preview_deck.py を再実行）")
    avg = sum(res["scores"].values()) / len(res["scores"]) if res["scores"] else 0.0
    print(f"check_pptx: {len(res['scores'])}枚を比較 平均差{avg:.2f} / しきい値{args.threshold}以上 {len(flagged)}枚 "
          f"→ 左右並べ画像: {out_dir}（警告のみ）")
    print(DISCLAIMER)
    if args.json:
        Path(args.json).write_text(json.dumps({"scores": {str(k): v for k, v in res["scores"].items()}, "flagged": [n for n, _, f in ranked if f],
                                               "average": avg, "threshold": args.threshold}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

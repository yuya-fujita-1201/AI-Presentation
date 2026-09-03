#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/<id>.pptx を PDF に変換する（LibreOffice の soffice --headless を使用）。
既定では毎回 build_deck.py --pptx で PPTX を最新化してから変換する
（deck.json 更新後に古い PPTX がそのまま使われるのを防ぐため）。
既存の PPTX をそのまま使いたい場合は --no-build を付ける。

使い方:
    python tools/export_pdf.py <deck_dir>          # build_deck.py --pptx を実行してから変換
    python tools/export_pdf.py <deck_dir> --no-build   # 既存の build/<id>.pptx をそのまま変換
    python tools/export_pdf.py <deck_dir> --out other/dir

soffice の探索順:
    PATH → Windows 既定パス（Program Files / Program Files (x86)）→ macOS 既定パス
    （/Applications/LibreOffice.app/Contents/MacOS/soffice）
見つからない場合は PowerPoint での手動書き出し手順を案内して終了する（exit 1）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(TOOLS_DIR))
try:
    import build_deck  # type: ignore
except Exception:
    build_deck = None


def _fallback_setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _fallback_fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _fallback_warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def _fallback_note(msg):
    print(f"note: {msg}", file=sys.stderr)


setup_console = getattr(build_deck, "setup_console", None) or _fallback_setup_console
fail = getattr(build_deck, "fail", None) or _fallback_fail
warn = getattr(build_deck, "warn", None) or _fallback_warn
note = getattr(build_deck, "note", None) or _fallback_note


WINDOWS_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]
MACOS_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]
LINUX_CANDIDATES = [
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/libreoffice/program/soffice",
]

MANUAL_STEPS = """\
soffice（LibreOffice）が見つかりませんでした。以下のいずれかで対応してください:
  (a) LibreOffice をインストールする: https://www.libreoffice.org/download/
      Windows: インストール後は既定で C:\\Program Files\\LibreOffice\\program\\soffice.exe
      macOS  : brew install --cask libreoffice、または上記サイトの .dmg
  (b) PowerPoint で build/<id>.pptx を開き、[ファイル] -> [エクスポート] ->
      [PDF/XPSドキュメントの作成] で手動書き出しする
  (c) Keynote（macOS）で開き、[ファイル] -> [書き出す] -> [PDF] で手動書き出しする"""


def find_soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("soffice.exe") or shutil.which("soffice.bin")
    if found:
        return found
    for cand in WINDOWS_CANDIDATES + MACOS_CANDIDATES + LINUX_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser(description="build/<id>.pptx を PDF に変換（LibreOffice使用）")
    ap.add_argument("deck_dir")
    ap.add_argument("--out", help="出力先ディレクトリ（既定: <deck_dir>/build）")
    ap.add_argument("--no-build", action="store_true", help="PPTX が既にあれば build_deck.py を呼ばず、そのまま使う（既定は毎回 build_deck.py --pptx で最新化）")
    args = ap.parse_args()

    deck_dir = Path(args.deck_dir).resolve()
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        fail(f"{deck_json} が見つかりません")
    deck = json.loads(deck_json.read_text(encoding="utf-8-sig"))
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name
    pptx_path = deck_dir / "build" / f"{deck_id}.pptx"

    if args.no_build:
        if not pptx_path.exists():
            fail(f"{pptx_path} がありません。先に build_deck.py を実行してください")
    else:
        note(f"build_deck.py --pptx を実行して {pptx_path} を最新化します")
        cmd = [sys.executable, str(TOOLS_DIR / "build_deck.py"), str(deck_dir), "--pptx"]
        proc = subprocess.run(cmd, cwd=ROOT)
        if proc.returncode != 0 or not pptx_path.exists():
            fail("PPTX のビルドに失敗しました")

    soffice = find_soffice()
    if not soffice:
        print(MANUAL_STEPS, file=sys.stderr)
        fail("soffice（LibreOffice）が見つかりません")

    out_dir = Path(args.out) if args.out else deck_dir / "build"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)]
    print(f"  $ {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        print(MANUAL_STEPS, file=sys.stderr)
        fail(f"soffice の起動に失敗しました: {soffice}")
    except subprocess.TimeoutExpired:
        fail("soffice の変換がタイムアウトしました（180秒）。PPTX が壊れていないか確認してください")

    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    if proc.returncode != 0 or not pdf_path.exists():
        sys.stderr.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        print(MANUAL_STEPS, file=sys.stderr)
        fail(f"PDF変換に失敗しました（soffice exit={proc.returncode}）")

    print(f"PDF: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

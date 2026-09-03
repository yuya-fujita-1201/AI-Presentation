#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slide-deck プラグインの依存関係を確認・インストールする初回セットアップ。

使い方:
    python tools/setup_deps.py                 # 必須(python-pptx)を確認/導入
    python tools/setup_deps.py --playwright     # + プレビューPNG用(playwright + chromium)
    python tools/setup_deps.py --pillow         # + 一覧シート用(pillow)
    python tools/setup_deps.py --pdf            # + PDFエクスポート/抽出用(pymupdf)
    python tools/setup_deps.py --all            # 全部
    python tools/setup_deps.py --check          # 導入せず状態確認のみ
    python tools/setup_deps.py --pip-args "--user"   # pip install に追加引数を渡す

依存の役割:
    python-pptx  必須。PPTX 生成に使用
    pillow       任意。contact_sheet.py の一覧シート生成／画像からのテーマ抽出に使用
    playwright   任意。preview_deck.py のプレビューPNG生成・check_layout.py の機械ゲートに使用（chromium も要install）
    pymupdf      任意。theme_from_sample.py で PDF からテーマを抽出する場合に使用

Windows で `python` が Microsoft Store を開いてしまう場合は Python 未インストールです。
python.org からインストールするか、`py -3 tools/setup_deps.py` のように `py` ランチャーを使ってください。
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import subprocess
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
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

MIN_PY = (3, 9)


def have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _pep668_guidance():
    print("  このPython環境は externally-managed-environment（PEP 668）のため pip install がブロックされました。",
          file=sys.stderr)
    print("  対処の選択肢（どれか一つを選んでください。安全のため自動では選びません）:", file=sys.stderr)
    print("    (a) venv を作って中で実行する（推奨）:", file=sys.stderr)
    print(f"        {sys.executable} -m venv .venv", file=sys.stderr)
    if os.name == "nt":
        print(r"        .venv\Scripts\activate", file=sys.stderr)
    else:
        print("        source .venv/bin/activate", file=sys.stderr)
    print(f"        {os.path.basename(sys.executable)} tools/setup_deps.py " + " ".join(sys.argv[1:]), file=sys.stderr)
    print("    (b) このユーザーだけに入れる: --pip-args \"--user\"", file=sys.stderr)
    print("    (c) システムPythonへの影響を理解した上で強制する: --pip-args \"--break-system-packages\"", file=sys.stderr)


def pip_install(*args: str, pip_args=None) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", *(pip_args or []), *args]
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        combined = (proc.stdout or "") + (proc.stderr or "")
        if "externally-managed-environment" in combined:
            _pep668_guidance()
        return False
    return True


def main() -> int:
    setup_console()
    if sys.version_info < MIN_PY:
        fail(
            f"Python {MIN_PY[0]}.{MIN_PY[1]} 以上が必要です（現在: {sys.version.split()[0]}）。"
            "python.org から新しいバージョンを導入するか、`py -3` （Windows）で実行してください。"
        )

    ap = argparse.ArgumentParser(description="slide-deck の依存セットアップ")
    ap.add_argument("--playwright", action="store_true", help="プレビューPNG用 playwright + chromium も導入")
    ap.add_argument("--pillow", action="store_true", help="一覧シート／画像テーマ抽出用 pillow も導入")
    ap.add_argument("--pdf", action="store_true", help="PDFからのテーマ抽出用 pymupdf も導入")
    ap.add_argument("--all", action="store_true", help="任意依存もすべて導入")
    ap.add_argument("--check", action="store_true", help="導入せず状態確認のみ")
    ap.add_argument("--pip-args", default="", help="pip install に追加で渡す引数（例: \"--user\" \"--index-url https://...\"）")
    args = ap.parse_args()

    try:
        pip_args = shlex.split(args.pip_args) if args.pip_args else []
    except ValueError as e:
        fail(f"--pip-args の解析に失敗しました: {e}")

    want_playwright = args.playwright or args.all
    want_pillow = args.pillow or args.all
    want_pdf = args.pdf or args.all

    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")

    # 現状レポート
    status = {
        "python-pptx (必須)": have("pptx"),
        "playwright (任意)": have("playwright"),
        "pillow (任意)": have("PIL"),
        "pymupdf (任意)": have("fitz"),
    }
    print("現在の状態:")
    for name, ok in status.items():
        print(f"  [{'OK ' if ok else '  未'}] {name}")

    if args.check:
        return 0 if status["python-pptx (必須)"] else 1

    ok = True
    # 必須: python-pptx
    if not have("pptx"):
        print("\npython-pptx を導入します…")
        ok = pip_install("python-pptx", pip_args=pip_args) and ok
    # 任意: playwright
    if want_playwright and not have("playwright"):
        print("\nplaywright を導入します…")
        if pip_install("playwright", pip_args=pip_args):
            print("chromium を導入します…")
            proc = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                                   capture_output=True, text=True)
            if proc.stdout:
                sys.stdout.write(proc.stdout)
            if proc.stderr:
                sys.stderr.write(proc.stderr)
            if proc.returncode != 0:
                warn(
                    "chromium の取得に失敗しました。社内プロキシ経由の場合は環境変数 HTTPS_PROXY を設定するか、"
                    "PLAYWRIGHT_DOWNLOAD_HOST でミラーのホストを指定してから再実行してください。"
                    "プレビュー機能（preview_deck.py / check_layout.py / contact_sheet.py）は任意機能なので、"
                    "導入できなくても HTML/PPTX の生成自体は問題なく行えます（export_pdf.py での確認に切り替え可能）。"
                )
                ok = False
        else:
            ok = False
    # 任意: pillow
    if want_pillow and not have("PIL"):
        print("\npillow を導入します…")
        ok = pip_install("pillow", pip_args=pip_args) and ok
    # 任意: pymupdf
    if want_pdf and not have("fitz"):
        print("\npymupdf を導入します…")
        ok = pip_install("pymupdf", pip_args=pip_args) and ok

    print("\n完了。" if ok else "\n一部の導入に失敗しました。上のログを確認してください。")
    if not want_playwright:
        print("プレビューPNG(preview_deck.py)を使うには: python tools/setup_deps.py --playwright")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

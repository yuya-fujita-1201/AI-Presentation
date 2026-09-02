#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slide-deck プラグインの依存関係を確認・インストールする初回セットアップ。

使い方:
    python tools/setup_deps.py                 # 必須(python-pptx)を確認/導入
    python tools/setup_deps.py --playwright     # + プレビューPNG用(playwright + chromium)
    python tools/setup_deps.py --pillow         # + 一覧シート用(pillow)
    python tools/setup_deps.py --all            # 全部
    python tools/setup_deps.py --check          # 導入せず状態確認のみ

依存の役割:
    python-pptx  必須。PPTX 生成に使用
    playwright   任意。preview_deck.py のプレビューPNG生成に使用（chromium も要install）
    pillow       任意。contact_sheet.py の一覧シート生成に使用
"""

import argparse
import importlib.util
import subprocess
import sys


def have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def pip_install(*args: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", *args]
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="slide-deck の依存セットアップ")
    ap.add_argument("--playwright", action="store_true", help="プレビューPNG用 playwright + chromium も導入")
    ap.add_argument("--pillow", action="store_true", help="一覧シート用 pillow も導入")
    ap.add_argument("--all", action="store_true", help="任意依存もすべて導入")
    ap.add_argument("--check", action="store_true", help="導入せず状態確認のみ")
    args = ap.parse_args()

    want_playwright = args.playwright or args.all
    want_pillow = args.pillow or args.all

    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")

    # 現状レポート
    status = {
        "python-pptx (必須)": have("pptx"),
        "playwright (任意)": have("playwright"),
        "pillow (任意)": have("PIL"),
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
        ok &= pip_install("python-pptx")
    # 任意: playwright
    if want_playwright and not have("playwright"):
        print("\nplaywright を導入します…")
        if pip_install("playwright"):
            print("chromium を導入します…")
            ok &= subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"]).returncode == 0
        else:
            ok = False
    # 任意: pillow
    if want_pillow and not have("PIL"):
        print("\npillow を導入します…")
        ok &= pip_install("pillow")

    print("\n完了。" if ok else "\n一部の導入に失敗しました。上のログを確認してください。")
    if not want_playwright:
        print("プレビューPNG(preview_deck.py)を使うには: python tools/setup_deps.py --playwright")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

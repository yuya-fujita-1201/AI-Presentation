#!/usr/bin/env python3
"""配布用の slide-deck.zip を作り直す。

中身は「git が追跡している plugins/slide-deck/ 以下のファイル」だけ。
zip の中のパスはプラグインのフォルダからの相対（先頭に slide-deck/ を付けない）。
build/・__pycache__・.DS_Store は .gitignore 済みなので入らない。

使い方（リポジトリの直下で）:
    python3 scripts/build_zip.py            # slide-deck.zip を上書き
    python3 scripts/build_zip.py --out x.zip

plugins/slide-deck/ に、ステージしていない変更や未追跡のファイルがあると止まる
（zip とコミットの中身を一致させるため）。先に git add してから実行する。
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = "plugins/slide-deck"


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if r.returncode != 0:
        sys.exit("error: git %s が失敗しました: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return [p for p in r.stdout.decode("utf-8").split("\0") if p]


def main():
    ap = argparse.ArgumentParser(description="配布用の slide-deck.zip を作り直す")
    ap.add_argument("--out", default=str(REPO / "slide-deck.zip"), help="出力先（既定: リポジトリ直下の slide-deck.zip）")
    args = ap.parse_args()

    dirty = git("diff", "--name-only", "-z", "--", PLUGIN)
    untracked = git("ls-files", "-z", "--others", "--exclude-standard", "--", PLUGIN)
    if dirty or untracked:
        names = "\n  ".join((dirty + untracked)[:10])
        sys.exit("error: %s にステージしていない変更・未追跡のファイルがあります。git add してから実行してください:\n  %s" % (PLUGIN, names))

    files = sorted(git("ls-files", "-z", "--", PLUGIN))
    if not files:
        sys.exit("error: %s に追跡中のファイルがありません" % PLUGIN)

    out = Path(args.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in files:
            zf.write(REPO / f, f[len(PLUGIN) + 1:])

    with zipfile.ZipFile(out) as zf:
        bad = zf.testzip()
        if bad:
            sys.exit("error: zip が壊れています: %s" % bad)
        version = json.loads(zf.read(".claude-plugin/plugin.json"))["version"]
        count = len(zf.namelist())
    print("%s: バージョン %s・%d ファイル・%.1f MB" % (out, version, count, out.stat().st_size / 1e6))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成した PPTX の機械検証（zip 整合・再パース・ノート無し・XML 整形式・文書プロパティ）。

PPTX は PowerPoint / Keynote で開けて初めて完成だが、壊れた zip・不正な XML・python-pptx が付けるノート・
テンプレート既定のままの文書プロパティは、ビルド直後に機械で拾える。build_deck.py が保存の直後に
`verify(path)` を呼べるよう、import しただけでは何もしない（副作用なし。python-pptx も関数内で読み込む）。

検査:
  1. zip として開ける（CRC 不整合なし）
  2. ppt/ 内の XML（slides・presentation・rels・[Content_Types].xml など）が整形式
  3. python-pptx で再パースでき、スライドが 1 枚以上ある
  4. どのスライドにもスピーカーノートが無い（notesSlide・notesMaster の部品も無い。
     python-pptx の notes_slide は Keynote 互換性を壊すので出力しない決まり）
  5. グループ（p:grpSp）の中に表（p:graphicFrame）が入っていない
  6. 文書プロパティがテンプレート既定のままでない（title が空、last_modified_by / author が
     python-pptx 既定の "Steve Canny"、created が既定の 2013-01-27 のまま、は NG）

使い方:
    python tools/verify_pptx.py <file.pptx> [<file2.pptx> ...] [--skip-props]
    問題があれば 1 行ずつ表示して exit 1（直し方つき）。無ければ OK を表示して exit 0。
Python から:
    from verify_pptx import verify
    problems = verify("build/deck.pptx")   # list[str]。空なら合格
"""
from __future__ import annotations

import argparse
import sys
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree

# python-pptx の既定テンプレートに入っている値（保存しただけだとこのまま出てくる）
DEFAULT_AUTHORS = {"Steve Canny"}
DEFAULT_CREATED_YEAR = 2013
MAX_XML_BYTES = 64 * 1024 * 1024    # これを超える XML 部品は整形式の検査を飛ばす（想定外に巨大なものを読み込まない）


# 壊れた部品を読むと出る例外（圧縮データの破損=zlib.error、CRC 不一致=BadZipFile、途中で切れた=EOFError、
# 暗号化・未対応の圧縮方式=RuntimeError / NotImplementedError）。どれもトレースバックにせず問題文にする
_READ_ERRORS = (zipfile.BadZipFile, zlib.error, OSError, EOFError, RuntimeError, NotImplementedError)


def _corrupt_parts(zf: "zipfile.ZipFile") -> list:
    """全部品を最後まで読み、読めなかった部品名を返す（zipfile.testzip と違い、圧縮データの破損でも落ちない）。"""
    bad = []
    for info in zf.infolist():
        try:
            with zf.open(info) as fh:
                while fh.read(1 << 20):
                    pass
        except _READ_ERRORS:
            bad.append(info.filename)
    return bad


def _check_zip(path: Path) -> tuple[list, "zipfile.ZipFile | None"]:
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        return [f"zip として開けません（{e}）。ビルドが途中で止まった可能性がある → build_deck.py --pptx をやり直す"], None
    except OSError as e:
        return [f"ファイルを開けません（{e}）"], None
    bad = _corrupt_parts(zf)
    if bad:
        shown = "、".join(f"「{n}」" for n in bad[:3]) + (f" ほか{len(bad) - 3}個" if len(bad) > 3 else "")
        return [f"zip 内の部品{shown}が壊れています（圧縮データの破損か CRC 不一致）→ build_deck.py --pptx をやり直す"], zf
    return [], zf


def _check_xml(zf: "zipfile.ZipFile") -> list:
    problems = []
    for info in zf.infolist():
        n = info.filename
        if not (n.endswith(".xml") or n.endswith(".rels")):
            continue
        if info.file_size > MAX_XML_BYTES:
            continue
        try:
            data = zf.read(n)
        except _READ_ERRORS:
            continue    # 壊れた部品は _check_zip が報告済み
        try:
            ElementTree.fromstring(data)
        except ElementTree.ParseError as e:
            kind = "スライド" if n.startswith("ppt/slides/slide") else "部品"
            problems.append(f"{kind}の XML が整形式ではありません: {n}（{e}）"
                            f" → そのスライドの文字に制御文字・不正な記号が混じっていないか deck.json を確認して再ビルドする")
    return problems


_NS_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _check_table_in_group(zf: "zipfile.ZipFile") -> list:
    """グループ（p:grpSp）の中に表（p:graphicFrame）が入っていないか。PowerPoint の UI は表をグループ化できず、
    ファイルに書いたときに開けるか（修復ダイアログ・表の欠落）は実機で確かめていない。"""
    problems = []
    for info in zf.infolist():
        n = info.filename
        if not (n.startswith("ppt/slides/slide") and n.endswith(".xml")) or info.file_size > MAX_XML_BYTES:
            continue
        try:
            root = ElementTree.fromstring(zf.read(n))
        except (ElementTree.ParseError,) + _READ_ERRORS:
            continue    # 壊れた部品は他の検査が報告済み
        bad = sum(1 for grp in root.iter(_NS_P + "grpSp") for _ in grp.iter(_NS_P + "graphicFrame"))
        if bad:
            problems.append(f"グループの中に表（graphicFrame）が入っています（{n}、{bad} 件）"
                            f" → PowerPoint は表のグループ化に対応していません。表はグループの外に置く（build_deck の place_composite_block のように分ける）")
    return problems


def _check_notes(zf: "zipfile.ZipFile") -> list:
    parts = [n for n in zf.namelist() if n.startswith("ppt/notesSlides/") or n.startswith("ppt/notesMasters/")]
    if not parts:
        return []
    return [f"スピーカーノートの部品が入っています（{len(parts)}個: {', '.join(parts[:3])}{'…' if len(parts) > 3 else ''}）"
            f" → PPTX にノートは出力しない決まり（Keynote 互換性が壊れる）。build_deck.py で notes_slide を作らないようにする"]


def _check_pptx_api(path: Path, check_props: bool) -> list:
    problems = []
    try:
        from pptx import Presentation  # 関数内で読み込む（import 時に副作用・依存を持たない）
    except ImportError:
        return ["python-pptx が無いため再パース検査を飛ばしました（/slide-deck:setup で導入）"]
    try:
        prs = Presentation(str(path))
    except Exception as e:  # noqa: BLE001  python-pptx は壊れた入力でさまざまな例外を出す
        return [f"python-pptx で再パースできません（{type(e).__name__}: {e}）→ build_deck.py --pptx をやり直す"]
    slides = list(prs.slides)
    if not slides:
        problems.append("スライドが 0 枚です → deck.json の slides を確認して再ビルドする")
    for i, s in enumerate(slides, 1):
        try:
            if s.has_notes_slide:
                problems.append(f"{i}枚目にスピーカーノート（notes_slide）があります"
                                f" → PPTX にはノートを出力しない決まり。build_deck.py の PPTX 出力でノートを作らないようにする")
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}枚目のノート有無を確認できません（{type(e).__name__}: {e}）")
    if check_props:
        problems.extend(_check_props(prs))
    return problems


def _check_props(prs) -> list:
    cp = prs.core_properties
    problems = []
    if not (cp.title or "").strip():
        problems.append("文書プロパティの title が空です → build_deck.py で core_properties.title に meta.title を入れる"
                        "（Finder・メール添付のタイトル表示に出る）")
    for field in ("author", "last_modified_by"):
        v = (getattr(cp, field) or "").strip()
        if v in DEFAULT_AUTHORS:
            problems.append(f"文書プロパティの {field} が python-pptx テンプレート既定の「{v}」のままです"
                            f" → core_properties.{field} を deck の作成者（meta.author 等）か空に設定する")
    created = cp.created
    if created is not None and created.year == DEFAULT_CREATED_YEAR and created.month == 1 and created.day == 27:
        problems.append("文書プロパティの作成日時がテンプレート既定（2013-01-27）のままです"
                        " → core_properties.created / modified をビルド時刻に設定する")
    return problems


def verify(path, check_props: bool = True) -> list:
    """PPTX を検証して、問題の説明（日本語・直し方つき）のリストを返す。空リストなら合格。

    check_props=False で文書プロパティの検査を飛ばす（既存ファイルの確認用）。"""
    p = Path(path)
    if not p.exists():
        return [f"{p} がありません → 先に build_deck.py <deck_dir> --pptx を実行する"]
    problems, zf = _check_zip(p)
    if zf is None:
        return problems
    with zf:
        problems.extend(_check_xml(zf))
        problems.extend(_check_notes(zf))
        problems.extend(_check_table_in_group(zf))
    if any("壊れています" in x for x in problems):
        return problems     # 壊れた部品があると再パースも同じ理由で落ちる。重複して報告しない
    problems.extend(_check_pptx_api(p, check_props))
    return problems


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="PPTX の機械検証（zip 整合・再パース・ノート無し・XML 整形式・文書プロパティ）")
    ap.add_argument("files", nargs="+", help="検証する .pptx")
    ap.add_argument("--skip-props", action="store_true", help="文書プロパティ（title / author / created）の検査を飛ばす")
    args = ap.parse_args(argv)
    bad = 0
    for f in args.files:
        problems = verify(f, check_props=not args.skip_props)
        if problems:
            bad += 1
            for pr in problems:
                print(f"NG: {f}: {pr}")
        else:
            try:
                from pptx import Presentation
                n = len(Presentation(f).slides)
                print(f"OK: {f}（{n}枚）")
            except Exception:  # noqa: BLE001
                print(f"OK: {f}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

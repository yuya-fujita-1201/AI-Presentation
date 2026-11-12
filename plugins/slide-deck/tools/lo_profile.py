#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LibreOffice（soffice）に渡す一時プロファイルを作り、フォントの置き換えを固定する。

背景: PPTX のテーマのフォント（Meiryo など）がこの環境に無いと、LibreOffice は変換のたびに代わりのフォントを選ぶ。
同じ PPTX でも「1 回目は STHeitiSC、2 回目以降は BIZ UDPGothic」のように組が変わり、約物の幅が変わって全スライドの見た目が変わる
（check_pptx の画素比較・export_pdf の出力が実行ごとに揺れる）。
対策: 一時プロファイルの registrymodifications.xcu に「フォント置換表」を書き、PPTX が使うフォントのうちこの環境に無いものを、
字幅の見積もりに使っている代替フォント（ja_text.measure_source() と同じ）へ固定して置き換える。

使い方（check_pptx.py / export_pdf.py が呼ぶ）:
    prof = lo_profile.prepare(profile_dir, pptx_path)       # {"profile": Path, "env": "-env:UserInstallation=file://…", "pairs": [(元, 代替)…]}
    cmd = [soffice, prof["env"], "--headless", ...]
置換が要らない（フォントが全部ある・代替も見つからない）ときも env は返す（空の置換表）。
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

TYPEFACE_RE = re.compile(r'<a:(?:latin|ea|cs)\s+typeface="([^"]+)"')
# テーマの置き換えやシステムが付ける名前（置換しない）
SKIP_FACES = ("+mj-", "+mn-", "Symbol", "Wingdings", "Arial", "Calibri", "Times New Roman", "Courier New")


def pptx_typefaces(pptx: Path) -> list:
    """PPTX の中で指定されているフォント名（スライド・レイアウト・マスター・テーマ）を出現順で重複なく返す。"""
    seen: dict = {}
    try:
        with zipfile.ZipFile(pptx) as z:
            for n in z.namelist():
                if n.startswith("ppt/") and n.endswith(".xml"):
                    for m in TYPEFACE_RE.finditer(z.read(n).decode("utf-8", "ignore")):
                        seen.setdefault(m.group(1), True)
    except (OSError, zipfile.BadZipFile):
        return []
    return [f for f in seen if f and not f.startswith("+") and not any(f.startswith(s) for s in SKIP_FACES)]


def substitution_pairs(faces, ja_text_mod=None) -> list:
    """[(元のフォント名, 代替のフォント名)]。この環境に無いフォントだけを、字幅の見積もりに使っている代替フォントへ。
    代替が見つからない（近似で測っている）ときは空。"""
    if ja_text_mod is None:
        import ja_text as ja_text_mod  # type: ignore
    out = []
    for f in faces:
        if ja_text_mod._open_font(f, False) is not None:
            continue            # 入っているフォントはそのまま使う
        wanted, used = ja_text_mod.measure_source(f)
        if used and used != f:
            out.append((f, used))
    return out


def registry_xml(pairs) -> str:
    """registrymodifications.xcu の本文（フォント置換表。pairs が空なら空の設定）。"""
    items = []
    if pairs:
        items.append('<item oor:path="/org.openoffice.Office.Common/Font/Substitution">'
                     '<prop oor:name="Replacement" oor:op="fuse"><value>true</value></prop></item>')
        for i, (src, dst) in enumerate(pairs):
            items.append(
                f'<item oor:path="/org.openoffice.Office.Common/Font/Substitution/FontPairs">'
                f'<node oor:name="_{i}" oor:op="replace">'
                f'<prop oor:name="Always" oor:op="fuse"><value>true</value></prop>'
                f'<prop oor:name="OnScreenOnly" oor:op="fuse"><value>false</value></prop>'
                f'<prop oor:name="ReplaceFont" oor:op="fuse"><value>{escape(src)}</value></prop>'
                f'<prop oor:name="SubstituteFont" oor:op="fuse"><value>{escape(dst)}</value></prop>'
                f'</node></item>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + "\n".join(items) + "\n</oor:items>\n")


def prepare(profile_dir: Path, pptx: Path | None = None, faces=None) -> dict:
    """一時プロファイルを作る（作り直す）。faces を渡さなければ pptx から読む。"""
    profile_dir = Path(profile_dir)
    user = profile_dir / "user"
    user.mkdir(parents=True, exist_ok=True)
    if faces is None:
        faces = pptx_typefaces(Path(pptx)) if pptx else []
    pairs = substitution_pairs(faces)
    (user / "registrymodifications.xcu").write_text(registry_xml(pairs), encoding="utf-8")
    return {"profile": profile_dir, "env": f"-env:UserInstallation={profile_dir.resolve().as_uri()}", "pairs": pairs}

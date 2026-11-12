# -*- coding: utf-8 -*-
"""テーマ・レイアウト・パターンの探索先を 1 か所で決める（標準ライブラリのみ・副作用なし）。

build_deck / check_theme / new_theme / theme_from_sample / パターン読み込みが同じ規則で探すための関数。
種類（kind）は "themes" / "layouts" / "patterns" / "shapes"。探索順（先に見つかったものが勝つ。重複は除く）:

  1. 環境変数（os.pathsep 区切りで複数可）
       themes   → SLIDE_DECK_THEMES
       layouts  → SLIDE_DECK_LAYOUTS
       patterns → SLIDE_DECK_PATTERNS
       shapes   → SLIDE_DECK_SHAPES
  2. <deck_dir>/<kind>/
  3. <deck_dir> の親（1 階層上 → 3 階層上まで）の <kind>/
       例: decks/<名前>/deck.json に対して、プロジェクト直下の themes/ を拾う
  4. カレントディレクトリの <kind>/
  5. 同梱 templates/<kind>/

プラグイン更新で消したくないものは 1〜4 に置く。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KIND_ENV = {
    "themes": "SLIDE_DECK_THEMES",
    "layouts": "SLIDE_DECK_LAYOUTS",
    "patterns": "SLIDE_DECK_PATTERNS",
    "shapes": "SLIDE_DECK_SHAPES",
}
PARENT_LEVELS = 3   # deck_dir の親を何階層上まで探すか


def bundled_dir(kind: str) -> Path:
    return ROOT / "templates" / kind


def search_dirs(kind: str, deck_dir=None, cwd=None) -> list:
    """kind の探索ディレクトリを優先順に返す（存在しないディレクトリも含む。重複は除く）。"""
    if kind not in KIND_ENV:
        raise ValueError(f"未知の種類: {kind}（{' / '.join(KIND_ENV)} のいずれか）")
    out: list = []
    seen: set = set()

    def add(p) -> None:
        p = Path(p)
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key in seen:
            return
        seen.add(key)
        out.append(p)

    env = os.environ.get(KIND_ENV[kind])
    if env:
        for p in env.split(os.pathsep):
            if p.strip():
                add(p.strip())
    if deck_dir is not None:
        base = Path(deck_dir)
        try:
            base = base.resolve()
        except OSError:
            pass
        add(base / kind)
        parent = base
        for _ in range(PARENT_LEVELS):
            if parent.parent == parent:
                break
            parent = parent.parent
            add(parent / kind)
    add(Path(cwd) / kind if cwd is not None else Path.cwd() / kind)
    add(bundled_dir(kind))
    return out


KIND_LABEL = {"themes": "テーマ", "layouts": "レイアウト", "patterns": "型（パターン）", "shapes": "形（shape）"}
_SHADOW_SEEN: set = set()


def shadow_note(kind: str, name: str, path, layered: bool = False):
    """同梱と同じ名前の <kind>/<name>.json を同梱以外（環境変数・デッキ・デッキの親・カレント）から読んだときの知らせの文面。
    該当しない・同じファイルで 2 回目以降は None（同じ deck.json の見た目が置き場所で変わる原因に、利用者が気づけるようにする）。"""
    path = Path(path)
    bundled = bundled_dir(kind) / f"{name}.json"
    try:
        if not bundled.is_file() or path.resolve() == bundled.resolve():
            return None
    except OSError:
        return None
    key = (kind, str(path))
    if key in _SHADOW_SEEN:
        return None
    _SHADOW_SEEN.add(key)
    how = "同梱のものに重ねて" if layered else "同梱のものではなく"
    return (f"{KIND_LABEL.get(kind, kind)} '{name}' は{how} {path} を読みました（探索順で先に見つかったほうが優先されます。"
            f"意図していなければ、そのファイルを別の名前にするか移します）")


def list_names(kind: str, deck_dir=None, cwd=None) -> list:
    """探索先で見つかる名前（拡張子なし）の一覧（先に見つかった順・重複なし）。"""
    names: list = []
    for d in search_dirs(kind, deck_dir, cwd):
        try:
            for p in sorted(d.glob("*.json")):
                if p.stem not in names:
                    names.append(p.stem)
        except OSError:
            continue
    return names


def describe(kind: str, deck_dir=None, cwd=None) -> str:
    """探索先を「A / B / C」の 1 行にする（案内・エラーメッセージ用）。"""
    return " / ".join(str(d) for d in search_dirs(kind, deck_dir, cwd))


def default_out_dir(kind: str, deck_dir=None, explicit=None) -> Path:
    """新しいテーマ等の書き込み先。--dir 指定 → デッキ指定（<deck_dir>/<kind>/）→ 環境変数の先頭 → ./<kind>/。"""
    if explicit:
        return Path(explicit)
    if deck_dir is not None:
        return Path(deck_dir) / kind
    env = os.environ.get(KIND_ENV[kind])
    if env:
        first = next((p.strip() for p in env.split(os.pathsep) if p.strip()), None)
        if first:
            return Path(first)
    return Path.cwd() / kind


def visibility_lines(kind: str, out_dir, cwd=None) -> list:
    """out_dir に置いたファイルが「どのデッキから見つかるか」の説明（表示用の文字列のリスト）。"""
    out = Path(out_dir)
    try:
        resolved = out.resolve()
    except OSError:
        resolved = out
    lines = [f"書き込み先: {out}"]
    env_dirs = []
    env = os.environ.get(KIND_ENV[kind])
    if env:
        env_dirs = [Path(p.strip()).resolve() for p in env.split(os.pathsep) if p.strip()]
    if resolved in env_dirs:
        lines.append(f"見つかるデッキ: すべて（環境変数 {KIND_ENV[kind]} に含まれる場所です）")
    elif resolved == bundled_dir(kind).resolve():
        lines.append("見つかるデッキ: すべて（同梱の置き場所です。プラグイン更新で消えることがあります）")
    elif resolved.name == kind:
        base = resolved.parent
        lines.append(f"見つかるデッキ: {base} 配下のデッキ（{base}/deck.json、{base}/<名前>/deck.json など、"
                     f"{PARENT_LEVELS} 階層下まで）")
        cwd_kind = (Path(cwd) if cwd is not None else Path.cwd()).resolve() / kind
        if resolved == cwd_kind:
            lines.append(f"  このコマンドを {resolved.parent} で実行するときは、どのデッキからも見つかります（カレントディレクトリ）")
    else:
        lines.append(f"見つかるデッキ: 探索先ではない場所です。{kind} の探索先（{KIND_ENV[kind]}"
                     f" または <デッキ>/{kind}/）に移すか、環境変数 {KIND_ENV[kind]} にこの場所を追加してください")
    lines.append(f"探索順: 環境変数 {KIND_ENV[kind]} → <デッキ>/{kind}/ → デッキの親（{PARENT_LEVELS} 階層上まで）の {kind}/"
                 f" → カレントの {kind}/ → 同梱 templates/{kind}/")
    return lines

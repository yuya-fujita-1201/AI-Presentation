#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck.json → HTML / PPTX ビルダー v2（パラメーター駆動）。

使い方:
    python tools/build_deck.py <deck_dir>          # HTML + PPTX
    python tools/build_deck.py <deck_dir> --html   # HTML のみ
    python tools/build_deck.py <deck_dir> --pptx   # PPTX のみ
（環境により python3 / py -3 を使う）

設計:
- 仮想キャンバス 1280x720px。全オブジェクトの位置・サイズ・フォント・色を px で持つ
- 解決順: templates/layouts/<layout>.json の既定値
          ← deck.meta.layout_overrides（デッキ全体の調整）
          ← slides[i].style（スライド個別の微修正）
- HTML は px をそのまま使用、PPTX は 96dpi 換算（px/96 インチ、フォント px*0.75 pt）
  なので両形式で座標・サイズが一致する
- スキーマは references/deck-schema.md を参照

注意: PPTX にはスピーカーノートを出力しない（python-pptx の notes_slide は
macOS Keynote の互換性を壊す既知問題があるため）。notes は HTML でのみ表示される。
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import copy
import difflib
import hashlib
import html as html_mod
import json
import mimetypes
import os
import re
import sys
import unicodedata
from pathlib import Path
from string import Template
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CANVAS_W, CANVAS_H = 1280, 720

# 図解タイプ（architecture / dataflow / lifecycle / sequence / swimlane の配線）共通エンジン。
# tools/ 直下の同名モジュール。スクリプト実行時は tools/ が sys.path[0] に入るが、
# 他ツールから import build_deck されるケースでも解決できるよう明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagram_engine as de  # noqa: E402
import diagram_scale as dscale  # noqa: E402
import canvas_engine as ce  # noqa: E402
import schedule_engine as se  # noqa: E402
import ja_text  # noqa: E402
import engine_registry  # noqa: E402
import proposal_engine as pe  # noqa: E402
import pattern_engine as pat_e  # noqa: E402
import deck_paths  # noqa: E402
import deck_schema as dschema  # noqa: E402
import shape_engine as shp  # noqa: E402
import autofit  # noqa: E402
import composite_engine as comp  # noqa: E402
import hero_engine as hero  # noqa: E402
import todo_marks  # noqa: E402
import wrap_fix  # noqa: E402
import color_pick as cp  # noqa: E402


# ---------------------------------------------------------------------------
# エラー・警告の共通ヘルパー（他ツールからも `import build_deck` して再利用可）
# ---------------------------------------------------------------------------

_WARNED: set = set()
# 合成スライドのブロックを既存タイプの検証・フィットに通すとき、メッセージの先頭の「N枚目（type=xxx）」を
# 「N枚目（type=composite）の K つ目のブロック（xxx）」に書き換える（既存の検証コードをそのまま使うため）。[(正規表現, 置換)]
_MSG_REWRITES: list = []


def _rewrite_msg(msg: str) -> str:
    for rx, rep in _MSG_REWRITES:
        msg = rx.sub(rep, msg)
    return msg


@contextlib.contextmanager
def block_messages(page: int, k: int, bt: str, stype: str = "composite"):
    """この中で出る fail / warn / note の場所表記を、合成スライド（split も）の k 番目（0 始まり）のブロックにする。"""
    rx = re.compile(rf"{page}枚目（type={re.escape(bt)}(?:[,、][^）]*)?）")
    rep = f"{page}枚目（type={stype}）の {k + 1} つ目のブロック（{bt}）"
    # 色指定のエラーは「（N枚目 type=xxx の body.color）」の形で出る（_color_issue）ので、これもブロックの場所にする
    rx2 = re.compile(rf"{page}枚目 type={re.escape(bt)} の ")
    _MSG_REWRITES.append((rx, rep))
    _MSG_REWRITES.append((rx2, rep + "の "))
    try:
        yield
    finally:
        _MSG_REWRITES.pop()
        _MSG_REWRITES.pop()


def fail(msg: str):
    """stderr に error: <msg> を出して exit code 1 で終了する。"""
    sys.exit(f"error: {_rewrite_msg(msg)}")


class OutputLockedError(SystemExit):
    """出力ファイルに書き込めない（PowerPoint 等で開いている）ときの終了。main は PPTX が書けなくても HTML は作ってから、これで終了する。"""


def warn(msg: str):
    """stderr に warning: <msg> を出す。ビルドは続行する。同一メッセージは1回だけ表示。"""
    msg = _rewrite_msg(msg)
    if msg in _WARNED:
        return
    _WARNED.add(msg)
    print(f"warning: {msg}", file=sys.stderr)


def note(msg: str):
    """stderr に note: <msg> を出す。"""
    print(f"note: {_rewrite_msg(msg)}", file=sys.stderr)


def _import_sync_playwright():
    """SVG の画像化に使う playwright を読み込む。無ければ直し方つきで fail（トレースバックにしない）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("このデッキは SVG の画像を含むため、PPTX 化に playwright が必要です（SVG を PNG にして貼ります）"
             " → `/slide-deck:setup --playwright` で導入する（または `pip install playwright` と `playwright install chromium`）。"
             "HTML だけなら --html を付けて再実行できます")
    return sync_playwright


def _launch_chromium(pw):
    """SVG の画像化に使う Chromium を起動する。ブラウザ本体が未導入などで起動できなければ直し方つきで fail。"""
    try:
        return pw.chromium.launch()
    except Exception as e:      # playwright は入っているがブラウザ本体が無い、など
        fail(f"SVG の画像化に使う Chromium を起動できません（{type(e).__name__}）"
             " → `/slide-deck:setup --playwright`（または `playwright install chromium`）でブラウザを導入する。"
             "HTML だけなら --html を付けて再実行できます")


def setup_console():
    """stdout/stderr を UTF-8 に強制する（Windows の既定コードページ対策）。失敗は無視。"""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 読み込みとスタイル解決
# ---------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        fail(f"{path} が見つかりません")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        fail(f"{path} の JSON が不正です: {e}")
    except PermissionError:
        fail(f"{path} を読み込めません（権限がありません）")


def theme_dirs(deck_dir: Path):
    """テーマの探索ディレクトリを優先順に返す（規則は deck_paths.search_dirs に集約）。
    1. 環境変数 SLIDE_DECK_THEMES（複数可・OS区切り）… ユーザー追加テーマ置き場
    2. <deck_dir>/themes/ → deck_dir の親（3 階層上まで）の themes/ … デッキ／プロジェクト同梱テーマ
    3. カレントディレクトリの themes/（new_theme.py の既定の書き込み先）
    4. 同梱テーマ（templates/themes/）
    先に見つかったものが勝つ。プラグイン更新で消したくないテーマは 1 か 2 に置く。"""
    return deck_paths.search_dirs("themes", deck_dir)


def layout_dirs(deck_dir: Path):
    """レイアウト JSON の探索ディレクトリ（環境変数 SLIDE_DECK_LAYOUTS → デッキ → 親 → カレント → 同梱）。"""
    return deck_paths.search_dirs("layouts", deck_dir)


def pattern_dirs(deck_dir: Path):
    """パターン JSON の探索ディレクトリ（環境変数 SLIDE_DECK_PATTERNS → デッキ → 親 → カレント → 同梱）。"""
    return deck_paths.search_dirs("patterns", deck_dir)


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    """hex カラー a・b を (1-t):t の割合で線形混合した hex を返す。"""
    ra, ga, ba = _hex_to_rgb(a)
    rb, gb, bb = _hex_to_rgb(b)
    return _rgb_to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))




def _luminance(hex_color: str) -> float:
    """WCAG 相対輝度。"""
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, bl = _hex_to_rgb(hex_color)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(bl)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG コントラスト比（1.0〜21.0）。"""
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(color: str, bg: str, min_ratio: float = 4.5) -> str:
    """color を bg 上で min_ratio 以上のコントラストになるまで白/黒側へ寄せた色を返す（color_pick.readable_on）。"""
    return cp.readable_on(color, bg, min_ratio)


def _derive_colors(colors: dict, own_color_keys) -> None:
    """default 以外の階層で、その階層が自分の JSON で明示していないトークン（own_color_keys に
    無いもの）を、colors の現在値（親から継承した値に own_color_keys 分を重ねたもの＝
    「その階層自身の基本色」）から導出して colors を書き換える（in-place）。
    親テーマ（default 以外）がそのトークンを明示していても、この階層が明示していなければ
    継承値を採用せず、この階層自身の primary/accent 等から改めて導出し直す（themes.md 参照）。"""
    bg = colors.get("background", "#FFFFFF")
    text = colors.get("text", "#1A2233")
    primary = colors.get("primary", "#0F3D6E")
    accent = colors.get("accent", "#007D96")
    on_primary = colors.get("on_primary", "#FFFFFF")
    if "surface" not in own_color_keys:
        # M-面の視認性: 0.93 だと surface/background のコントラスト比が 1.1 程度しかなく
        # ディスプレイによって面が背景に溶けて見えなくなる。0.88 まで primary 側に寄せて
        # 面自体をはっきり視認できるようにする（check_theme.py の面チェック参照）。
        colors["surface"] = mix(primary, bg, 0.88)
    surface = colors.get("surface", bg)
    if "muted" not in own_color_keys:
        # 補助文字色。背景の上でも、面（surface）の上でも 4.5:1 以上で読めるまで text 側へ寄せる
        # （check_theme の muted/surface 組。寄せないと extends しただけのテーマで NG になる）
        muted0 = mix(text, bg, 0.35)
        colors["muted"] = muted0
        for i in range(0, 11):
            cand = mix(muted0, text, i / 10) if i else muted0
            if min(contrast_ratio(cand, bg), contrast_ratio(cand, surface)) >= 4.5:
                colors["muted"] = cand
                break
        else:
            colors["muted"] = readable_on(readable_on(muted0, bg), surface)
    derived = {
        "table_header_bg": primary,
        "table_header_text": on_primary,
        "table_row_alt": mix(surface, bg, 0.5),
        "on_primary_soft": mix(primary, "#FFFFFF", 0.90),
        "on_primary_muted": mix(primary, "#FFFFFF", 0.75),
        "code_bg": mix(primary, "#000000", 0.55),
        "code_text": "#E6EDF5",
        # M-面の視認性: highlight_fill / border も同様に濃い側へ調整（0.85→0.75 / 0.82→0.72）。
        "highlight_fill": mix(accent, bg, 0.75),
        "border": mix(text, bg, 0.72),
        "accent_on_primary": mix(accent, "#FFFFFF", 0.45),
        # 見出し文字色: primary が背景上で読めなければ白/黒側へ寄せる（暗色テーマ対策）
        "heading_text": readable_on(primary, bg),
    }
    for key, value in derived.items():
        if key not in own_color_keys:
            colors[key] = value


def _load_theme_chain(name: str, dirs, _seen, key: str = "meta.theme"):
    """テーマ JSON を extends チェーンに沿って読み込み、マージ済み dict を返す。
    default 以外の各階層は、親（既にこの関数で解決済み＝派生も適用済み）を deep_merge した直後、
    自分の JSON ファイルが明示していない colors キーだけをその階層自身の基本色から再導出する。
    階層ごとに導出をやり直すことで、`extends` 先が default 以外のテーマ（例: acn-slide-master）
    であっても、子テーマが primary/accent だけを上書きすれば派生トークン（table_header_bg 等）
    が親の固定値のままにならず新しい基本色に追随する。"""
    _check_resource_name("テーマ", name, key)   # パス区切り等を拒否（デッキ外の JSON を読ませない）
    if name in _seen:
        fail(f"テーマの extends が循環しています: {' -> '.join(_seen + [name])}")
    path = next((d / f"{name}.json" for d in dirs if (d / f"{name}.json").exists()), None)
    if path is None:
        searched = ", ".join(str(d) for d in dirs)
        fix = "meta.theme を直す" if key == "meta.theme" else f"{key} を直す"
        fail(f"テーマ '{name}' が見つかりません（探索: {searched}） → {fix}か、{name}.json を探索先のどれかに置く")
    _note_shadowed("themes", "テーマ", name, path)
    own = load_json(path)
    _report_issues(dschema.validate_theme_data(own, name, _default_color_keys()))
    if own.get("alias_of"):
        # 旧名（別名）テーマ: 本体をそのまま使う（派生トークンを再計算すると色が少しずれるため）
        target = _load_theme_chain(own["alias_of"], dirs, _seen + [name], f"テーマ '{name}' の alias_of")
        return target
    own_color_keys = set(own.get("colors", {}).keys())
    parent = own.get("extends") or (None if name == "default" else "default")
    if parent:
        parent_data = _load_theme_chain(parent, dirs, _seen + [name], f"テーマ '{name}' の extends")
        merged = deep_merge(parent_data, own)
    else:
        merged = copy.deepcopy(own)
    merged["name"] = name
    unchanged = bool(parent) and all(
        dschema.normalize_hex(v) == dschema.normalize_hex(parent_data["colors"].get(k))
        for k, v in (own.get("colors") or {}).items())
    if name != "default" and not unchanged:
        # 色を書いていない・親と同じ値しか書いていないテーマ（new_theme の雛形のまま、fonts だけ変える等）は、
        # 親の色（default なら手で調整した値）をそのまま継承する。1 つでも変えたときだけ、変えていない派生トークンを導出し直す
        _derive_colors(merged.setdefault("colors", {}), own_color_keys)
    merged["colors"] = {k: dschema.normalize_hex(v) for k, v in merged.get("colors", {}).items()}
    return merged


_DEFAULT_COLOR_KEYS: list = []


def _default_color_keys():
    """標準の色トークン名（同梱 default テーマの colors のキー）。テーマ JSON の打ち間違い検出に使う。"""
    if not _DEFAULT_COLOR_KEYS:
        try:
            data = json.loads((ROOT / "templates" / "themes" / "default.json").read_text(encoding="utf-8-sig"))
            _DEFAULT_COLOR_KEYS.extend(data.get("colors", {}).keys())
        except (OSError, ValueError):
            pass
    return tuple(_DEFAULT_COLOR_KEYS)


def _report_issues(issues, prefix: str = ""):
    """deck_schema の (level, 本文) のリストを warn / fail に流す。fail は最初の 1 件で終了する。"""
    for level, msg in issues:
        if level == "fail":
            fail(prefix + msg)
    for level, msg in issues:
        if level == "warn":
            warn(prefix + msg)
        elif level == "note":
            note(prefix + msg)


def load_theme(name: str, dirs, _seen=None):
    """テーマを解決して返す。default.json（または extends 先）をベースにマージするため、
    新しいテーマは上書きしたいトークンだけ書けばよい。`extends` を指定すると任意のテーマを
    親にできる（未指定なら default が親）。探索は theme_dirs() の順。
    default 以外のテーマが明示していない派生トークンは、default の固定 hex ではなく
    そのテーマ自身の基本色から自動導出する（themes.md 参照）。"""
    return _load_theme_chain(name, dirs, _seen or [])


_SHADOW_NOTED: set = set()


def _note_shadowed(kind: str, kind_label: str, name: str, path: Path, layered: bool = False):
    """同梱と同じ名前の <kind>/<name>.json を、同梱以外（環境変数・デッキ・デッキの親・カレント）から読んだことを 1 回だけ知らせる。
    同じ deck.json の見た目が置き場所で変わる原因に、利用者が気づけるようにする。"""
    bundled = deck_paths.bundled_dir(kind) / f"{name}.json"
    try:
        if not bundled.is_file() or path.resolve() == bundled.resolve():
            return
    except OSError:
        return
    key = (kind, str(path))
    if key in _SHADOW_NOTED:
        return
    _SHADOW_NOTED.add(key)
    how = "同梱のものに重ねて" if layered else "同梱のものではなく"
    note(f"{kind_label} '{name}' は{how} {path} を読みました（探索順で先に見つかったほうが優先されます。"
         f"意図していなければ、そのファイルを別の名前にするか移します）")


def _check_resource_name(kind_label: str, name, key: str):
    """テーマ・レイアウト・パターンの「名前」を検査する。パス区切り・絶対パスは任意ファイル読みになるので fail。"""
    if not isinstance(name, str) or not name.strip():
        fail(f"{key} は{kind_label}の名前（文字列。例: \"default\"）で指定してください")
    if any(ch in name for ch in ("/", "\\", ":", "\x00")) or name.startswith(".") or os.path.isabs(name):
        fail(f"{key} '{name}' は名前だけを指定してください（パス区切り・絶対パス・先頭のドットは使えません）。"
             f"{kind_label}は探索先に <名前>.json として置きます")


def _without_refs(region):
    """領域の値のうち ``"$グループ.名前"``（形トークンの参照）を除いた浅いコピー（型の検査は解決後の値で行うため）。"""
    if not isinstance(region, dict):
        return region
    return {k: v for k, v in region.items() if not shp.is_ref(v)}


def _layout_candidates(name: str, dirs):
    return [d / f"{name}.json" for d in dirs if (d / f"{name}.json").is_file()]


def _load_layout_chain(name: str, dirs, seen, key: str):
    """レイアウト JSON を extends チェーンに沿って読み、マージ済み dict を返す。
    extends 省略時の親は default（default 自身は親なし）。差分だけ書ける。循環は fail。"""
    _check_resource_name("レイアウト", name, key)
    used = {p for _, p in seen}
    cands = [p for p in _layout_candidates(name, dirs) if p.resolve() not in used]
    if not cands:
        if any(n == name for n, _ in seen):
            fail(f"レイアウトの extends が循環しています: {' -> '.join([n for n, _ in seen] + [name])}")
        avail = deck_paths.list_names("layouts", None)
        pool = list(dict.fromkeys(
            [p.stem for d in dirs if d.is_dir() for p in sorted(d.glob("*.json"))] + avail))
        hint = dschema.hint(name, pool)
        fail(f"レイアウト '{name}' が見つかりません{hint}（使える名前: {', '.join(pool) or 'なし'}。"
             f"探索: {', '.join(str(d) for d in dirs)}）→ {key} を直すか、{name}.json を探索先のどれかに置く")
    path = cands[0]
    _note_shadowed("layouts", "レイアウト", name, path, layered=True)   # 同名のレイアウトは同梱の既定に差分として重なる
    own = load_json(path)
    if not isinstance(own, dict):
        fail(f"レイアウト '{name}'（{path}）の最上位はオブジェクトにしてください")
    for k in own:
        if isinstance(k, str) and not k.startswith("_") and k not in dschema.LAYOUT_TOP_KEYS:
            warn(f"レイアウト '{name}': 未知のトップキー \"{k}\" は無視されます{dschema.hint(k, dschema.LAYOUT_TOP_KEYS)}"
                 f"（使えるキー: {' / '.join(sorted(dschema.LAYOUT_TOP_KEYS))}）")
    for sec in ("common", "types"):
        if sec in own and not isinstance(own[sec], dict):
            fail(f"レイアウト '{name}': {sec} はオブジェクトにしてください")
    for tname, tdef in (own.get("types") or {}).items():
        if not isinstance(tdef, dict) or any(not isinstance(v, dict) for v in tdef.values()):
            fail(f"レイアウト '{name}': types.{tname} は {{ 領域名: {{ プロパティ }} }} の形にしてください")
    for rname, rdef in (own.get("common") or {}).items():
        if not isinstance(rdef, dict):
            fail(f"レイアウト '{name}': common.{rname} は {{ プロパティ }} の形にしてください")
    # 領域の値の型（size が文字列、align が不正な値など）は、描画の途中で TypeError になる前にここで知らせる
    for sec_name, regions in [("common", own.get("common") or {})] + \
            [(f"types.{tn}", td) for tn, td in (own.get("types") or {}).items()]:
        for rn, rd in regions.items():
            _report_issues(dschema.check_region_value(_without_refs(rd), None, f"レイアウト '{name}'（{path.name}）の {sec_name}.{rn}",
                                                      check_unknown=False))
    dens = own.get("densities")
    if dens is not None:
        if not isinstance(dens, dict):
            fail(f"レイアウト '{name}': densities は {{ 密度名: {{ タイプ名: {{ 領域名: {{ プロパティ }} }} }} }} の形にしてください")
        for dn, dd in dens.items():
            if dn not in autofit.DENSITIES:
                warn(f"レイアウト '{name}': densities の \"{dn}\" は使われません → 使えるのは {' / '.join(autofit.DENSITIES)}")
            if not isinstance(dd, dict) or any(not isinstance(tv, dict) or any(not isinstance(rv, dict) for rv in tv.values())
                                              for tv in dd.values()):
                fail(f"レイアウト '{name}': densities.{dn} は {{ タイプ名: {{ 領域名: {{ プロパティ }} }} }} の形にしてください")
            for tn, tv in dd.items():
                for rn, rv in tv.items():
                    _report_issues(dschema.check_region_value(_without_refs(rv), None, f"レイアウト '{name}'（{path.name}）の densities.{dn}.{tn}.{rn}",
                                                              check_unknown=False))
    _check_readable_pairs(own, name, path)
    parent = own.get("extends")
    if parent is not None and not isinstance(parent, str):
        fail(f"レイアウト '{name}': extends はレイアウト名（文字列）で指定してください")
    if parent is None and name != "default":
        parent = "default"
    elif parent is None and path.resolve() != (deck_paths.bundled_dir("layouts") / "default.json").resolve():
        parent = "default"   # 利用者が置いた default.json は、同梱の default を土台にして差分だけ上書きする
    if parent:
        base = _load_layout_chain(parent, dirs, seen + [(name, path.resolve())], f"レイアウト '{name}' の extends")
        merged = deep_merge(base, own)
    else:
        merged = copy.deepcopy(own)
    merged.pop("extends", None)
    merged["name"] = name
    if "tokens" in own and not isinstance(own["tokens"], dict):
        fail(f"レイアウト '{name}': tokens は {{ グループ: {{ 名前: 値 }} }} の形にしてください")
    return merged


def shape_dirs(deck_dir: Path):
    """shape（形のプリセット）の探索ディレクトリ（環境変数 SLIDE_DECK_SHAPES → デッキ → 親 → カレント → 同梱）。"""
    return deck_paths.search_dirs("shapes", deck_dir)


def _check_readable_pairs(own: dict, name: str, path) -> None:
    """レイアウト JSON の readable_pairs（タイプ名 → [[領域, 文字色のキー, [地の色…]], …]）と todo_*（#RRGGBB）の形を確かめる。
    形が違うと、描画の途中で TypeError になる・黙って既定色に戻る、のどちらかになるので、ここで場所つきで知らせる。"""
    where = f"レイアウト '{name}'（{path.name}）"
    for key in ("todo_color", "todo_color_on_dark", "todo_bg"):
        v = own.get(key)
        if v is not None and not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v.strip())):
            warn(f"{where}: {key} は #RRGGBB の形で書いてください（{v!r} は使われず、既定の色になります）→ 例: \"#9A3412\"")
    pairs = own.get("readable_pairs")
    if pairs is None:
        return
    if not isinstance(pairs, dict):
        fail(f"{where}: readable_pairs は {{ タイプ名: [[領域, 文字色のキー, [地の色…]], …] }} の形にしてください"
             f"（{dschema._vtype(pairs)}が書かれています）→ 例: \"readable_pairs\": {{\"steps\": [[\"body\", \"num_color\", [\"body.fill\"]]]}}")
    for tname, specs in pairs.items():
        if isinstance(tname, str) and tname.startswith("_"):
            continue            # "_comment" などのメモ
        if not isinstance(specs, list):
            fail(f"{where}: readable_pairs.{tname} は [[領域, 文字色のキー, [地の色…]], …] の配列にしてください"
                 f"（{dschema._vtype(specs)}が書かれています）→ 使わないタイプは [] にするか、キーごと消す")
        for k, spec in enumerate(specs):
            if not (isinstance(spec, list) and len(spec) == 3 and isinstance(spec[0], str) and isinstance(spec[1], str)
                    and isinstance(spec[2], list) and all(isinstance(o, str) for o in spec[2])):
                fail(f"{where}: readable_pairs.{tname}[{k}] は [領域, 文字色のキー, [地の色…]] の形にしてください"
                     f"（地の色は色トークン名 / hex / \"領域.キー\" / \"@ground\" の配列）→ 例: [\"body\", \"num_color\", [\"body.fill\"]]")


def load_layout(name, deck_dir=None):
    """meta.layout の名前からレイアウトを探して読む（探索は layout_dirs。名前だけ受け付け、パスは fail）。
    形トークンの参照（$radius.card など）は既定の tokens（classic）で解決済みの形で返す。shape・テーマの層を重ねるのは load_deck
    （元の参照つきのレイアウトは "_unresolved" に持つ）。"""
    raw = _load_layout_chain(name, layout_dirs(deck_dir), [], "meta.layout")
    out = shp.apply_to_layout(raw, None, None, fail=fail)
    out["_unresolved"] = raw
    return out


def _apply_shape(layout, theme, meta, deck_dir):
    """形の層を重ねる: レイアウト既定 → shape（meta.shape、無ければテーマの shape、無ければ classic）→ テーマの tokens / layout。
    ``$`` 参照を解決したレイアウトと shape 名を返す。"""
    key = "meta.shape"
    resolved_base = layout                            # 領域名・値の型の検査に使う（既定 tokens で解決済み）
    layout = layout.get("_unresolved") or layout      # 参照つきの元のレイアウトに shape の層を重ねる
    name = meta.get("shape")
    if name is None:
        name = theme.get("shape")
        key = f"テーマ '{theme.get('name', '')}' の shape"
    shape = None
    if name is not None:
        shape = shp.load_shape(name, deck_dir, key, fail=fail)
        _report_issues(shp.validate_shape(shape, name, layout.get("tokens"), resolved_base, theme.get("colors") or {}))
    else:
        name = shp.DEFAULT_SHAPE
    th = {}
    if theme.get("tokens") or theme.get("layout"):
        th = {"tokens": theme.get("tokens"), "layout": theme.get("layout")}
        where = f"テーマ '{theme.get('name', '')}'"
        _report_issues(shp.check_tokens(th["tokens"], layout.get("tokens"), where))
        _report_issues(shp.check_layout_diff(th["layout"], where, shp.merge_tokens(layout.get("tokens"), (shape or {}).get("tokens"),
                                                                                  th["tokens"] if isinstance(th["tokens"], dict) else None),
                                             resolved_base, theme.get("colors") or {}))
    out = shp.apply_to_layout(layout, shape, th or None, fail=fail)
    out["_shape"] = name
    return out, name


def load_deck(deck_dir: Path):
    deck = load_json(deck_dir / "deck.json")
    if not isinstance(deck, dict):
        fail("deck.json の形式が不正です（トップレベルはオブジェクトである必要があります）")
    meta = deck.get("meta", {})
    if not isinstance(meta, dict):
        fail("deck.json の形式が不正です（meta はオブジェクトである必要があります）")
    theme_name = meta.get("theme", "default")
    if not isinstance(theme_name, str) or not theme_name.strip():
        fail("meta.theme はテーマ名（文字列。例: \"default\"）で指定してください")
    theme = load_theme(theme_name, theme_dirs(deck_dir))
    layout = load_layout(meta.get("layout", "default"), deck_dir)
    layout, shape_name = _apply_shape(layout, theme, meta, deck_dir)
    theme["tokens"] = copy.deepcopy(layout["tokens"])     # パターン・dataviz・canvas が同じ解決済みの表を読む
    layout["_colors"] = theme.get("colors") or {}         # resolve_style が「地の色に対して読める文字色」を決めるために読む（apply_readable_pairs）
    theme["_shape"] = shape_name
    # 文字あふれの見積もり・改行位置の調整はテーマのフォントの実測字幅で行う（Pillow が無ければ近似）
    ja_text.set_fonts(theme.get("fonts", {}))
    return deck, theme, layout


def deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if k in out else copy.deepcopy(v)
    return out


class WrapSrc:
    """apply_wrap_fix が文に入れた改行を取り除いた元の内容（変えたキーだけ）。スライド・ブロックの `_wrap_src` に持たせる。
    大きさを決める自動フィットは、この元の文で行う（改行の有無で大きさが揺れない。順序は「大きさを決める → 決まった大きさで改行を入れる」）。
    辞書・リスト・文字列ではないので、内容を走査する処理（【要確認】の一覧など）には見えない。"""
    __slots__ = ("orig",)

    def __init__(self, orig: dict):
        self.orig = orig


def _sizing_view(slide):
    """大きさを決めるときに見るスライド（ブロック）の内容。文節の改行を入れていれば、入れる前の文に戻したもの。"""
    src = slide.get("_wrap_src") if isinstance(slide, dict) else None
    return {**slide, **src.orig} if isinstance(src, WrapSrc) else slide


def resolve_style(layout, deck, slide, block_defaults=None):
    """スタイル解決順: layout["common"]（全タイプ共通の領域。brand 等）
       ← layout["types"][t]（タイプ既定値）
       ← meta.layout_overrides.common（全タイプ共通のデッキ全体調整）
       ← meta.layout_overrides[t]（タイプ単位のデッキ全体調整）
       ← slide.style（スライド個別の微修正）"""
    t = slide.get("type")
    drawn = slide                          # 合成ブロックの描画には、改行を入れた内容のまま渡す
    slide = _sizing_view(slide)            # 大きさ・余白の決定は、文節の改行を入れる前の内容で行う
    if not layout.get("_tokens_resolved"):
        # load_deck を通っていないレイアウト（json から直接読んだものなど）は、既定の tokens で $ 参照を解決する
        layout = shp.apply_to_layout(layout, None, None, fail=fail)
    types = layout.get("types", {})
    if not t:
        fail("スライドに type がありません")
    if t not in types:
        fail(f"未知のスライドタイプ: {t}")
    # split は composite（見出し骨格・ブロックの枠と既定）に、パネルの領域を足したもの。composite への shape・密度の指定がそのまま効く
    base_t = deep_merge(types["composite"], types[t]) if t == "split" and "composite" in types else types[t]
    st = deep_merge(layout.get("common", {}), base_t)
    # variant（全面系タイプの見た目の型）と背景の文字色（palette）。タイプ既定の上、密度・利用者の明示値の下
    st = hero.apply_style_layers(st, layout, deck, slide, t)
    # 密度（meta.density / slide.density）のプリセット。レイアウト既定の上、利用者の明示値（overrides・slide.style）の下
    if t == "split":
        st = deep_merge(st, autofit.density_layer(layout, autofit.density_of(deck, slide), "composite"))
        hero.apply_split_geometry(st, slide, bool((deck.get("meta") or {}).get("brand")))
    st = deep_merge(st, autofit.density_layer(layout, autofit.density_of(deck, slide), t))
    if block_defaults:
        # 合成スライドのブロック: その中で釣り合う文字サイズ・余白（types.composite.blocks.<タイプ>）。密度の上、利用者の明示値の下
        st = deep_merge(st, block_defaults)
    overrides = shp.resolve_style_refs(deck.get("meta", {}).get("layout_overrides") or {}, layout,
                                       "meta.layout_overrides", fail)
    slide_style = shp.resolve_style_refs(slide.get("style") or {}, layout, "style", fail)
    for layer in (overrides.get("common"), overrides.get(t), slide_style):
        st = deep_merge(st, layer or {})
        shp.apply_bold_override(st, layer)       # 利用者が bold を書いた領域は、レイアウト・shape 由来の weight より bold を優先
    if t == "code" and slide.get("annotations") and "w" not in (slide.get("style", {}).get("code") or {}):
        st["code"]["w"] = round(st["code"]["w"] * 0.6)   # 右の 4 割を注釈の欄にする
    if t == "agenda" and any(isinstance(it, dict) and it.get("desc") for it in slide.get("items", []) or []) \
            and "row_h" not in (slide.get("style", {}).get("body") or {}):
        st["body"]["row_h"] = max(st["body"].get("row_h", 44), 64)   # 説明文の2行目が入る高さ
        st["body"]["gap"] = min(st["body"].get("gap", 10), 8)
    if t == "status_table" and not status_legend(slide):
        # 凡例を出さない（legend: false）ときは、凡例のために空けてあるタイトル脇の幅（690px）を、罫線と同じ幅まで使う（長いタイトルが 2 行に折れない）
        wide = (st.get("rule") or {}).get("w")
        ex = autofit.explicit_props(deck, slide)
        for reg in ("eyebrow", "title"):
            if isinstance(st.get(reg), dict) and wide and "w" not in ex.get(reg, ()):
                st[reg]["w"] = wide
    if t == "status_table" and isinstance(slide.get("columns"), list) and len(slide["columns"]) >= 3:
        # 既定の col_widths は 4 列分。3 列や 5 列以上の最小形でも組めるよう、利用者が列幅を書いていないときだけ
        # 内容列の数に合わせて作る（ラベル列・状況列は既定のまま、内容列で残りを等分）
        widths = st.get("table", {}).get("col_widths")
        user_set = any(isinstance(src, dict) and isinstance(src.get("table"), dict) and src["table"].get("col_widths")
                       for src in (overrides.get("common"), overrides.get(t), slide.get("style")))
        n = len(slide["columns"])
        if not user_set and isinstance(widths, list) and len(widths) != n and len(widths) >= 3:
            k = n - 2
            total_content = sum(widths[2:])
            st["table"]["col_widths"] = widths[:2] + [round(total_content / k, 3)] * k
    if not block_defaults:
        _brand_clearance(deck, slide, st)
    # 自動フィット（文字サイズ・列幅・行高。明示値は動かさない）。結論帯・出典の分の下端は自動フィットが見るので、
    # 表の行高を詰める従来処理は、自動フィットが行高を決めたときは飛ばす
    fit = autofit.apply(layout, deck, slide, st)
    # rule.style（短い帯・縦帯・なし）は、利用者の層（density・overrides・style）と自動フィットが決めたタイトルの位置・大きさに合わせて最後に当てる
    user_rule = {}
    for layer in (overrides.get("common"), overrides.get(t), slide_style):
        if isinstance(layer, dict) and isinstance(layer.get("rule"), dict):
            user_rule.update(layer["rule"])
    if user_rule and isinstance(st.get("rule"), dict) and shp.tok(layout.get("tokens"), "rule", "style", "line") == "none":
        warn(f"rule.style が none のため、type={t} の rule への指定（meta.layout_overrides / style の rule）は無視します（罫線は描きません）"
             f" → 罫線を出したいなら shape の rule.style を line / short / bar-left にする。この指定を消してもよい")
    if isinstance(fit, dict):
        hero.fit_boxes_to_content(st, fit.get("info") or {}, slide.get("style"))      # variant の箱（closing の contact）を中身の高さに合わせる
    tl = ((fit.get("info") or {}).get("title") or {}).get("lines") if isinstance(fit, dict) else None
    shp.apply_rule_style(st, layout.get("tokens"), t, user_rule=user_rule, title_lines=tl if isinstance(tl, int) else 1)
    st = pe.shrink_for_bottom(slide, st, skip_table_rows=("table" in fit.get("info", {}) and autofit.autofit_on(deck, slide)))
    apply_readable_pairs(st, layout, deck, slide, t)
    if t in COMPOSITE_TYPES:
        st["_composite"] = resolve_composite_blocks(layout, deck, drawn, st)       # ブロックごとの矩形・枠・スタイル（描画と検証が共有）
    return st


CARD_PHRASE_MIN_SIZE = 20     # cards の見出し・本文がこの大きさ以上のとき、改行を文節の切れ目に置く（語の途中で折れない）
BRAND_FIT_SAFETY = 0.97       # brand でタイトルの幅を狭めたとき、自動フィットの見積もりに掛ける余裕（幅の 97%）


def _brand_clearance(deck, slide, st):
    """meta.brand を付けたとき、タイトルの右端を brand の文字の左端より brand.clear_gap 手前までに狭める（長いタイトルが brand に重なるのを避ける）。
    タイトルが折れるときは自動フィット・文節折り返しがこの幅で行う。利用者がタイトルの幅（style.title.w）を書いたときは動かさない。"""
    brand_text = (deck.get("meta") or {}).get("brand")
    br = st.get("brand")
    if not brand_text or not isinstance(brand_text, str) or not isinstance(br, dict):
        return
    if not all(isinstance(br.get(k), (int, float)) for k in ("x", "y", "w", "h")):
        return
    size = br.get("size", 23)
    tw = min(autofit.text_em(brand_text, bool(br.get("bold"))) * size + 4, br["w"])
    left = br["x"] + br["w"] - tw if br.get("align", "left") == "right" else br["x"]
    ex = autofit.explicit_props(deck, slide)
    for name, min_w in (("title", 200), ("legend", 300)):          # legend: status_table の凡例（タイトル脇に置く）
        r = st.get(name)
        if not isinstance(r, dict) or not all(isinstance(r.get(k), (int, float)) for k in ("x", "y", "w", "h")):
            continue
        if r["y"] >= br["y"] + br["h"] or r["y"] + r["h"] <= br["y"]:
            continue                              # 縦に重ならない（brand より下にある型）
        if "w" in ex.get(name, ()):
            continue
        new_w = left - br.get("clear_gap", 24) - r["x"]       # clear_gap: brand の文字との間に空ける幅（レイアウト JSON の brand）
        if min_w <= new_w < r["w"]:
            r["w"] = round(new_w, 1)
            # 狭めた幅ぎりぎりの長さのタイトルは、見積もりが 1 行に収まると判断してもブラウザは 1 字だけ 2 行目に送る（s4-C-02）。
            # 狭めたときだけ見積もりに余裕を持たせる（利用者が fit_safety を書いていれば、小さいほうを採る）
            r["fit_safety"] = min(r.get("fit_safety", 1.0), BRAND_FIT_SAFETY)


def _pair_color(colors: dict, st: dict, region: dict, ref):
    """readable_pairs の色の参照を hex にする。参照は同じ領域のキー / "領域.キー" / テーマの色トークン / hex。解決できなければ None。"""
    v = ref
    if isinstance(ref, str):
        if ref in region:
            v = region[ref]
        elif "." in ref:
            rn, _, pn = ref.partition(".")
            v = (st.get(rn) or {}).get(pn) if isinstance(st.get(rn), dict) else None
    if not isinstance(v, str):
        return None
    if v in colors:
        v = colors[v]
    return dschema.normalize_hex(v) if _HEX_RE.match(v) else None


def _ground_of(st: dict, layout: dict, deck: dict, slide: dict, t: str, region: str):
    """領域 region の文字の地の色（トークン名 / hex）。背景（slide["_bg"]）があれば None（背景の側が決める）。
    variant に panel があるとき: on_bg に挙げた領域は panel の塗り、それ以外はスライドの下地。on_bg が無い variant は不明（None）。"""
    if slide.get("_bg"):
        return None
    if t == "split" and region == "brand":
        panel = st.get("panel")      # split の brand はパネルの上（hero_engine.apply_split_geometry）。地はパネルの塗り
        return panel.get("fill") if isinstance(panel, dict) else None
    bgr = next((st[k] for k in ("bg", "background") if isinstance(st.get(k), dict) and st[k].get("fill")), None)
    base = bgr.get("fill") if bgr else None
    panel = st.get("panel")
    if isinstance(panel, dict) and panel.get("fill") and hero.variant_of(layout, deck, slide) is not None:
        only = hero.on_bg_regions(layout, t, hero.variant_of(layout, deck, slide), bool((deck.get("meta") or {}).get("brand")), slide)
        if only is None:
            return None
        return panel["fill"] if region in only else base
    return base


def apply_readable_pairs(st: dict, layout: dict, deck: dict, slide: dict, t: str):
    """レイアウトの readable_pairs（タイプ別 [[領域, 文字色のキー, [地の色…]], …]。"*" は全タイプ）に従って、
    文字色が地の色の上で 4.5:1 に満たなければ、同じ色味のまま白 / 黒の側へ寄せる（color_pick.readable_on_all）。
    地の色は、同じ領域のキー・"領域.キー"・テーマの色トークン・hex のどれか。"@ground" は「この領域の文字が載る下地」
    （章扉・表紙・statement の背景の塗り、variant のパネル。背景つきのスライドは hero_engine の palette が決めるので触らない）。
    利用者が明示した値（meta.layout_overrides / slide.style）は動かさない。地の色が複数あるときは全部の上で読める色にする。"""
    colors = layout.get("_colors")
    pairs = layout.get("readable_pairs")
    if not colors or not isinstance(pairs, dict):
        return
    explicit = autofit.explicit_props(deck, slide)
    for spec in list(pairs.get("*") or []) + list(pairs.get(t) or []):
        if not (isinstance(spec, (list, tuple)) and len(spec) == 3):
            continue
        rn, prop, ons = spec
        region = st.get(rn)
        if not isinstance(region, dict) or prop not in region or prop in explicit.get(rn, ()):
            continue
        fg = _pair_color(colors, st, region, region[prop])
        bgs = []
        for o in ons:
            if o == "@ground":
                o = _ground_of(st, layout, deck, slide, t, rn)
            bgs.append(_pair_color(colors, st, region, o))
        if fg is None or not any(bgs):
            continue
        new = cp.readable_on_all(fg, bgs)
        if new != fg:
            region[prop] = new


# ---------------------------------------------------------------------------
# 合成スライド（type: "composite"）: ブロックごとの矩形・枠・スタイルの解決
# ---------------------------------------------------------------------------
# 設計: ブロックを「見出し骨格なしの小さなスライド」として扱う。ブロックの辞書から bs（スライドの形）を作り、
# 本文領域（bullets の body、cards の grid …）をブロックの矩形で差し替えて resolve_style に通す。
# 矩形は bs["style"] に書くので、自動フィットは明示値として動かさず、その矩形に収まるよう文字サイズなどを決める。
# 描画は既存の html_slide_body(bare=True) / build_pptx のビルダー（chrome を呼ばない）をそのまま使う。

COMPOSITE_TYPES = ("composite", "split")      # ブロックを格子に置くタイプ（split は本文領域がパネルの残り）
COMPOSITE_CHROME_REGIONS = ("eyebrow", "title", "rule", "lead", "footer_l", "footer_r", "brand", "conclusion", "source")
# ブロックのタイプ → 本文領域の名前（矩形を差し替える領域）。A 型タイプ（提案書系・kpi・chart）と pattern は "body"
BLOCK_MAIN_REGION = {
    "bullets": "body", "steps": "body", "table": "table", "code": "code", "cards": "grid",
    "architecture": "diagram", "dataflow": "diagram", "lifecycle": "diagram", "sequence": "diagram",
    "swimlane": "flow", "schedule": "chart", "matrix": "grid", "status_table": "table",
    "pattern": "body",
}
# valign（縦位置）を領域の valign に写せるタイプ
BLOCK_VALIGN_REGION = {"bullets": "body", "steps": "body", "cards": "grid", "matrix": "grid"}
# emphasis（濃い塗りに白文字）の色替えに対応する既存タイプ。ほかは emphasis を無視して warn（合成専用の text / callout は対応）
EMPHASIS_TYPES = ("bullets",)
# 合成ブロックにできないことが実装上わかったタイプ → 理由と直し方（実装の結果で更新する）
BLOCK_RUNTIME_UNSUPPORTED: dict = {}


def block_main_region(bt):
    if bt in BLOCK_MAIN_REGION:
        return BLOCK_MAIN_REGION[bt]
    if engine_registry.has(bt):
        return "body"
    return None


def block_type_problem(bt, types_known) -> str | None:
    """ブロックの type が使えないときの理由と直し方。使えるなら None。"""
    if not isinstance(bt, str):
        return f"type は文字列で指定してください（{dschema._vtype(bt)}が書かれています）"
    if bt in comp.NATIVE_TYPES:
        return None
    if bt in comp.UNSUPPORTED:
        return f"{bt} は合成スライドのブロックにできません。{comp.UNSUPPORTED[bt]}"
    if bt in BLOCK_RUNTIME_UNSUPPORTED:
        return f"{bt} は合成スライドのブロックにできません。{BLOCK_RUNTIME_UNSUPPORTED[bt]}"
    if block_main_region(bt) is None:
        usable = sorted(set(comp.NATIVE_TYPES) | set(BLOCK_MAIN_REGION) | set(engine_registry.names()))
        if bt in types_known:
            return f"{bt} は合成スライドでは使えません → 単独のスライドにする（ブロックに使えるタイプ: {', '.join(usable)}）"
        hint = difflib.get_close_matches(bt, usable, n=1)
        return (f"未知のタイプ '{bt}' です{('（もしかして ' + hint[0] + '）') if hint else ''}"
                f" → ブロックに使えるタイプ: {', '.join(usable)}")
    if bt not in types_known and bt not in comp.NATIVE_TYPES:
        return f"{bt} のレイアウト定義がありません"
    return None


def block_slide(slide, block, k, deck):
    """合成ブロックを、既存タイプのスライドとして扱える辞書にする（内容のキーだけ引き継ぐ浅いコピー）。style は呼び出し側が作る。"""
    bs = {key: v for key, v in block.items() if key not in comp.BLOCK_COMMON_KEYS and key not in _BLOCK_IGNORED_KEYS}   # 「ブロックでは描かれません」と警告するキー（conclusion など）は描かない（S5b）
    bs["type"] = block.get("type")
    bs["density"] = autofit.density_of(deck, slide)
    if not autofit.autofit_on(deck, slide):
        bs["autofit"] = False
    bs["_bare"] = True
    bs["_block"] = k
    if bs["type"] == "pattern":
        bs.setdefault("title", "（ブロック）")      # パターンの検査はスライド直下の title を求める。ブロックでは見出し骨格を描かないので形だけ満たす
    return bs


def _matrix_axis_boxes(ax: dict, gx: float, gy: float, gw: float, gh: float, xa: dict, ya: dict) -> list:
    """matrix の軸ラベル 6 個（縦軸の名前・高 / 低、横軸の名前・低 / 高）の位置と文字。HTML と PPTX が共有する。
    位置は格子（gx, gy, gw, gh）からの相対で決め、オフセットはレイアウトの axis 領域のトークンで持つ（格子を動かすと軸ラベルも付いてくる）。
    縦軸の名前の x（x0）は、指定が無ければ格子の左端から left_margin だけ左（既定 100）。"""
    size = ax.get("size", 15)
    acol, ncol = ax.get("color", "muted"), ax.get("name_color", "text")
    th = ax.get("tick_h", 22)
    ytw, ytg = ax.get("y_tick_w", 88), ax.get("y_tick_gap", 8)
    xtw = ax.get("x_tick_w", 160)
    x0 = ax.get("x0", gx - ax.get("left_margin", 100))
    return [
        {"text": "▲ " + str(ya.get("label", "")),
         "region": {"x": x0, "y": gy + ax.get("y_name_dy", -30), "w": ax.get("y_name_w", 360), "h": th, "size": size, "color": ncol, "bold": True}},
        {"text": str(ya.get("high", "")),
         "region": {"x": gx - ytw - ytg, "y": gy + ax.get("y_high_dy", 6), "w": ytw, "h": th, "size": size, "color": acol, "align": "right"}},
        {"text": str(ya.get("low", "")),
         "region": {"x": gx - ytw - ytg, "y": gy + gh + ax.get("y_low_dy", -28), "w": ytw, "h": th, "size": size, "color": acol, "align": "right"}},
        {"text": str(xa.get("label", "")) + " ▶",
         "region": {"x": gx, "y": gy + gh + ax.get("x_name_dy", 30), "w": gw, "h": th, "size": size, "color": ncol, "align": "center", "bold": True}},
        {"text": str(xa.get("low", "")),
         "region": {"x": gx, "y": gy + gh + ax.get("x_tick_dy", 6), "w": xtw, "h": th, "size": size, "color": acol}},
        {"text": str(xa.get("high", "")),
         "region": {"x": gx + gw - xtw, "y": gy + gh + ax.get("x_tick_dy", 6), "w": xtw, "h": th, "size": size, "color": acol, "align": "right"}},
    ]


def _block_rect_layer(bt, rect, block):
    """ブロックの内容矩形を、そのタイプの本文領域に差し替える style の層。"""
    x, y, w, h = rect
    region = block_main_region(bt)
    r = {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2)}
    layer = {region: r}
    if region == "body" and (bt == "pattern" or engine_registry.has(bt)):
        r["y_no_lead"] = r["y"]               # lead が無いと本文の y を y_no_lead で上書きする仕組みを、矩形の y に合わせる
    if bt == "schedule":
        r["y_no_lead"], r["h_no_lead"] = r["y"], r["h"]
    r["block_rect"] = True                    # 矩形は格子が決めた値（利用者の明示ではない）。中身が薄いとき文字を大きくする・箱を詰めるのを許す（autofit.thin_*）
    if bt == "matrix":
        # 軸ラベル（縦軸の名前・高低・横軸の名前）が格子の外に出るぶんの余白を、矩形の中に取る（左 100・上 34・下 58）
        ml, mt, mb = 100, 34, 58
        r.update({"x": round(x + ml, 2), "y": round(y + mt, 2), "w": round(max(w - ml, 40), 2), "h": round(max(h - mt - mb, 40), 2)})
        layer["axis"] = {"x0": round(x, 2)}
    if bt == "status_table":
        # 凡例は矩形の上に置き（標準ではスライド右上のタイトル脇）、表はその下
        lh = 84
        has_legend = block.get("legend") is not False
        layer["legend"] = {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": lh}
        if has_legend:
            r.update({"y": round(y + lh + 12, 2), "h": round(max(h - lh - 12, 60), 2)})
    va = block.get("valign")
    if va in comp.VALIGNS and bt in BLOCK_VALIGN_REGION:
        layer.setdefault(BLOCK_VALIGN_REGION[bt], r)["valign"] = va
    return layer


def _emphasize_style(bst, bt, bk):
    """emphasis ブロックの文字色を、濃い塗りの上で読める色にする（対応するタイプだけ）。"""
    fg = bk.get("emphasis_color", "on_primary")
    if bt == "bullets":
        for key in ("color", "child_color", "marker_color"):
            bst["body"][key] = fg


def resolve_block(layout, deck, slide, st, k, block, rect, issues, limits=None):
    """合成ブロック 1 つの解決: 矩形 rect（x, y, w, h）に、枠・小見出し・本文のスタイルとフィット（文字サイズなど）を決める。
    resolve_composite_blocks が格子の矩形ごとに呼ぶ。S2d の split のように、格子を使わず自分で決めた矩形にブロックを置くときも、
    これをそのまま呼べる（slide は {"blocks": [...]} を持つ親スライド、st はその resolve_style の結果、k は blocks の何番目か）。
    戻り値は resolve_composite_blocks の説明にあるブロックの dict。フィットの警告・注記は issues（[level, code, 文]）に足す。"""
    bk = st.get("block") or {}
    bdefs = st.get("blocks") or {}
    bt = block.get("type") if isinstance(block, dict) else None
    where = f"{{label}}の {k + 1} つ目のブロック（{bt}）"
    sblock = _sizing_view(block)                      # 文字の大きさのフィットは、文節の改行を入れる前の内容で行う（block は描画用）
    blk = {"index": k, "type": bt, "block": block, "rect": rect, "native": bt in comp.NATIVE_TYPES,
           "emph": bool(block.get("emphasis")) and (bt in ("text", "callout") or bt in EMPHASIS_TYPES), "bs": None, "st": None, "fit": None, "heading_fit": None}
    # emphasis が効かないタイプ（警告して無視するもの）は、枠も強調の箱にしない（frame の指定どおり）
    gblock = block if (blk["emph"] or not block.get("emphasis")) else {**block, "emphasis": False}
    geo0 = comp.frame_geometry(rect, gblock, bk)
    if block.get("heading"):
        hf = comp.fit_heading(str(block["heading"]), geo0["heading"][2], bk)
        blk["heading_fit"] = hf
        if not hf["fits"]:
            issues.append(["warn", "block-heading", f"{where}: 小見出しが 1 行に収まりません（{hf['size']}px まで縮めても{hf['lines']}行）"
                           f" → 小見出しを短くする（目安: ブロックの幅に 1 行）"])
    geo = comp.frame_geometry(rect, gblock, bk, blk["heading_fit"])
    blk["geo"] = geo
    cx, cy, cw, ch = geo["content"]
    user_style = block.get("style") if isinstance(block.get("style"), dict) else {}
    if bt in comp.NATIVE_TYPES:
        reg = deep_merge(st.get(bt) or {}, user_style.get(bt) or {})
        blk["region"] = reg
        if bt in ("text", "callout"):
            reg["block_rect"] = True                  # 矩形は格子が決めた値。中身が薄いとき文字を大きくするのを許す（利用者が size を書いた・autofit が切れているときは動かさない）
            if "size" in (user_style.get(bt) or {}) or "size" in autofit.explicit_props(deck, slide).get(bt, ()) or not autofit.autofit_on(deck, slide):
                reg["_size_fixed"] = True
            lim = (limits or {}).get(bt)
            if lim is not None:
                reg["thin_limit"] = lim
        if bt == "text":
            fit = comp.fit_text_block(sblock, geo["content"], reg)
        elif bt == "callout":
            fit = comp.fit_callout(sblock, geo["content"], reg)
        else:
            fit = {"caption_h": comp.caption_height(sblock, reg)}
        if sblock is not block and bt == "text":
            fit["paras"] = comp.text_paragraphs(block)       # 描く段落は改行を入れた内容（大きさは入れる前の内容で決めた）
        blk["fit"] = fit
        blk["thin_factor"] = fit.get("thin_factor")
        if bt == "text":
            ratio = bk.get("thin_center_ratio")
            if (ratio and geo["frame"] == "box" and not block.get("valign") and "valign" not in (user_style.get(bt) or {})
                    and fit["avail"] > 0 and fit["need"] < fit["avail"] * ratio and not reg.get("_size_fixed")):
                if not _center_heading_group(slide, block, blk, fit["need"], bst=None):
                    reg["valign"] = "middle"
                blk["thin_centered"] = True
        if bt in ("text", "callout"):
            over = int(fit["need"] - fit["avail"])
            if not fit["fits"]:
                issues.append(["warn", "block-overflow", f"{where}: 文字がブロックに収まりません（{fit['size']}px まで縮めても約{over}px はみ出す。"
                               f"{len(str(block.get('text') or ''))}字）→ 文を短くするか、ブロックを広くする（columns / rows の比率）、2 枚に分ける"])
            elif fit["cap"] - fit["size"] >= 2:
                issues.append(["note", "block-shrunk", f"{where}: 文字が多いので {fit['cap']}px → {fit['size']}px に縮めました → 短くすると大きく読ませられます"])
        return blk
    bs = block_slide(slide, block, k, deck)
    layer = _block_rect_layer(bt, geo["content"], block)
    lim = (limits or {}).get(bt)
    if lim is not None:
        layer[block_main_region(bt)]["thin_limit"] = lim          # 同じ種類のブロックで文字の倍率をそろえる上限（resolve_composite_blocks の 2 周目）
    region0 = block_main_region(bt)
    if any(_user_set_block_prop(deck, slide, block, bs, bt, region0, k) for k in THIN_SIZE_KEYS.get(bt, ())):
        layer[region0]["thin_grow"] = 1.0                         # 利用者が文字の大きさを書いた種類は、中身が少なくても大きくしない（meta.layout_overrides.composite.blocks も含む）
    bs["style"] = deep_merge(copy.deepcopy(user_style), layer)
    bst = resolve_style(layout, deck, bs, block_defaults=bdefs.get(bt))
    for key in COMPOSITE_CHROME_REGIONS:
        bst.pop(key, None)
    if blk["emph"] and bt in EMPHASIS_TYPES:
        _emphasize_style(bst, bt, bk)
    blk["bs"], blk["st"] = bs, bst
    blk["thin_factor"] = ((bst.get("_fit") or {}).get("info") or {}).get("thin_factor")
    _thin_valign(deck, slide, st, block, bs, bst, blk)
    if bt == "table":
        added = _stretch_table_block(deck, slide, st, block, bs, bst)
        _center_lone_table(deck, slide, st, block, bs, bst, blk, added)
        _warn_sparse_block(blk, bk, bst, issues, where, extra=added)
    elif bt == "bullets":
        _warn_sparse_block(blk, bk, bst, issues, where)
    elif bt == "steps":
        n_steps = len([x for x in (bs.get("steps") or []) if isinstance(x, dict)])
        min_w = bk.get("steps_min_w")
        body_w = (bst.get("body") or {}).get("w", 0)
        if min_w and n_steps >= 2 and body_w / n_steps < min_w:
            issues.append(["warn", "block-steps-narrow", f"{where}: steps の 1 段の幅が約{int(body_w / n_steps)}px しかありません（{n_steps} 段をブロックの幅 {int(body_w)}px に横並び）。"
                           f"文が 1〜2 文字で折り返して読みにくくなります → 幅の広いブロックにする（col_span / columns の比率）、段を減らす、または bullets のブロックにする"])
    return blk


def _thin_valign(deck, slide, st, block, bs, bst, blk):
    """箱（frame: box）つきのブロックで、中身が枠の thin_center_ratio 割未満のとき、本文を箱の縦中央に置く（上に寄って下が空くのを避ける）。
    箱の見出しは動かさない（隣のブロックと見出しの位置がそろう）。利用者が valign を書いたとき・箱が無いときは動かさない。
    値は types.composite.block.thin_center_ratio（0 または無しで無効）。"""
    bt = blk["type"]
    ratio = (st.get("block") or {}).get("thin_center_ratio")
    region = BLOCK_VALIGN_REGION.get(bt)
    if not ratio or not region or blk["geo"]["frame"] != "box" or block.get("valign"):
        return
    if _user_set_block_prop(deck, slide, block, bs, bt, region, "valign") or not autofit.autofit_on(deck, slide):
        return
    ent = ((bst.get("_fit") or {}).get("info") or {}).get("body" if bt == "bullets" else bt)
    if not ent or not ent.get("avail") or ent.get("need") is None:
        return
    if ent["need"] < ent["avail"] * ratio and isinstance(bst.get(region), dict):
        if not (bt == "bullets" and _center_heading_group(slide, block, blk, ent["need"], bst=bst)):
            bst[region]["valign"] = "middle"
        blk["thin_centered"] = True


def _center_heading_group(slide, block, blk, need, bst=None) -> bool:
    """箱つきブロックで小見出しと本文を 1 つの塊にして箱の縦中央に置く（小見出しだけ上に残って本文と離れるのを避ける・s4-A-02）。
    同じスライドに小見出しつきの箱が他にもあるときは、見出しの位置をそろえるため塊にしない（False を返して、本文だけ中央に置く従来の置き方）。
    塊にしたら小見出しと本文の矩形を下へずらして True。bst があれば本文の領域（bullets の body）も同じだけずらす。"""
    geo = blk["geo"]
    if not geo.get("heading") or geo["frame"] != "box":
        return False
    for j, other in enumerate(slide.get("blocks") or []):
        if isinstance(other, dict) and j != blk.get("index") and other.get("heading") and comp.frame_of(other) == "box":
            return False
    ox, oy, ow, oh = geo["outer"]
    hx, hy, hw, hh = geo["heading"]
    cx, cy, cw, ch = geo["content"]
    pad = geo.get("pad", 0)
    group_h = (cy - hy) + need
    off = round((oh - 2 * pad - group_h) / 2, 1)
    if off < 4:
        return False
    geo["heading"] = (hx, round(hy + off, 1), hw, hh)
    geo["content"] = (cx, round(cy + off, 1), cw, max(1.0, round(ch - off, 1)))
    if bst is not None:
        reg = bst.get(BLOCK_VALIGN_REGION.get(blk["type"]))
        if isinstance(reg, dict) and "y" in reg:
            reg["y"] = round(reg["y"] + off, 1)
            if "h" in reg:
                reg["h"] = max(1.0, round(reg["h"] - off, 1))
    return True


THIN_SIZE_KEYS = {"bullets": ("size",), "steps": ("label_size", "item_size"), "table": ("cell_size",),
                  "cards": ("heading_size", "body_size", "item_size")}      # これらを利用者が書いたら、中身が少なくても文字を大きくしない


def _user_set_block_prop(deck, slide, block, bs, bt, region, key) -> bool:
    """合成ブロックの region.key を利用者が書いたか（ブロックの style・スライドの style.blocks・meta.layout_overrides の composite.blocks / <タイプ>）。"""
    if key in autofit.explicit_props(deck, bs).get(region, ()):
        return True        # ブロックの style と meta.layout_overrides.<タイプ>（autofit が見る明示値）
    sources = [((slide.get("style") or {}).get("blocks") or {}),
               ((((deck.get("meta") or {}).get("layout_overrides") or {}).get("composite") or {}).get("blocks") or {})]
    for src in sources:
        reg = (src.get(bt) or {}).get(region) if isinstance(src, dict) else None
        if isinstance(reg, dict) and reg.get(key) is not None:
            return True
    return False


def _stretch_table_block(deck, slide, st, block, bs, bst):
    """表のブロックが、表の自然な高さよりずっと高いとき、行の高さを広げて隣のブロックの下端に近づける
    （上限は types.composite.block.table_row_h_max）。利用者が row_h を書いたときは動かさない。"""
    info = ((bst.get("_fit") or {}).get("info") or {}).get("table")
    tr = bst.get("table")
    if not info or not isinstance(tr, dict) or not info.get("adjusted") or not info.get("rows_fit") or "row_h" not in tr:
        return 0.0
    cap_h = (st.get("block") or {}).get("table_row_h_max")
    n = len(bs.get("rows") or [])
    if not cap_h or not n or _user_set_block_prop(deck, slide, block, bs, "table", "table", "row_h"):
        return 0.0
    spare = info["avail"] - info["total_h"]
    row_h = info.get("row_h", tr["row_h"])
    new_h = int(min(cap_h, row_h + spare / n))
    if new_h - row_h >= 2:
        tr["row_h"] = new_h
        return float((new_h - row_h) * n)
    return 0.0


def _center_lone_table(deck, slide, st, block, bs, bst, blk, added):
    """表だけの split（本文側のブロックが表 1 つ）で、行を広げても余る高さがあれば、表を本文側の上下中央に置く
    （上に詰まって下が空くのを避ける。talk の表と同じ考え方。types.composite.block.center_lone_table が true のとき）。
    枠（frame: box）つき・利用者が表の y を書いたとき・複数ブロックのスライドは動かさない。"""
    if not (st.get("block") or {}).get("center_lone_table") or slide.get("type") != "split":
        return
    if len([x for x in (slide.get("blocks") or []) if isinstance(x, dict)]) != 1 or blk["geo"]["frame"] == "box":
        return
    info = ((bst.get("_fit") or {}).get("info") or {}).get("table")
    tr = bst.get("table")
    ust = block.get("style") if isinstance(block.get("style"), dict) else {}
    if not info or not isinstance(tr, dict) or not info.get("rows_fit") or "y" in (ust.get("table") or {}):
        return
    spare = info.get("avail", 0) - (info.get("total_h", 0) + added)
    if spare >= 24:
        tr["y"] = round(tr["y"] + spare / 2, 2)


def _warn_sparse_block(blk, bk, bst, issues, where, extra=0.0):
    """枠（frame: box）つきのブロックの中身が、枠の高さの半分に満たないとき、下が空くことを知らせる（箱は格子の高さいっぱいに描くため）。"""
    geo = blk["geo"]
    if geo["frame"] != "box" or blk.get("thin_centered"):
        return          # 箱でないとき・文字を大きくして縦中央に置いて整えたとき（_thin_valign）は、空きを警告しない
    ratio = bk.get("sparse_ratio")
    info = ((bst.get("_fit") or {}).get("info") or {})
    if not ratio:
        return
    ent = info.get("body") if blk["type"] == "bullets" else None
    if ent:
        need, avail = ent.get("need"), ent.get("avail")
    else:
        t = info.get("table")
        if not t or not t.get("adjusted"):
            return
        need, avail = t.get("total_h", 0) + extra, t.get("avail")      # 行を広げた分も含めた、表の高さ
    if not need or not avail or avail <= 0:
        return
    if need < avail * ratio and avail - need >= bk.get("sparse_min_px", 140):
        issues.append(["warn", "block-sparse", f"{where}: 枠の中身が少なく、下の約{int(avail - need)}px が空きます（枠の高さの{int(need / avail * 100)}%しか使っていません）"
                       f" → 項目を増やす、rows の比率を変えて低くする、枠（frame）を外す、2 枚に分ける"])


def _grid_spec(slide):
    """(columns, rows, arrange)。split で何も書かないときは 1 列（ブロックを縦に並べる。パネルの残りは幅が狭いので横には並べない）。"""
    cols, rows, arr = slide.get("columns"), slide.get("rows"), slide.get("arrange")
    if slide.get("type") == "split" and cols is None and arr is None:
        cols = [1]
    return cols, rows, arr


THIN_GROUP = {"bullets": "body", "text": "body", "steps": "body", "cards": "body"}      # 文字を大きくする倍率をそろえるグループ（同じグループの隣のブロックより大きくしない）


def resolve_composite_blocks(layout, deck, slide, st):
    """合成スライドの格子とブロックを解決する。戻り値:
    {"plan": 格子の割り付け, "body": 本文矩形, "blocks": [ブロックごとの dict], "issues": [[level, code, 文]]}
    ブロックの dict: index / type / block / rect / geo（枠・小見出し・内容の矩形）/ native（text・callout・image か）/
    fit（合成専用ブロックの文字サイズ）/ bs, st（既存タイプのブロックのスライド辞書と解決済みスタイル）/ emph。
    issues の文は {label} を含む（検証が「N枚目（type=composite）」に置き換える）。ここでは warn / fail を出さない。"""
    blocks = slide.get("blocks")
    blocks = blocks if isinstance(blocks, list) else []
    plan = comp.plan_grid(blocks, *_grid_spec(slide))
    out = {"plan": plan, "body": None, "blocks": [], "issues": []}
    if plan["problems"] or not blocks:
        return out
    b = dict(st["body"])
    if not slide.get("lead") and "y_no_lead" in b:
        bottom = b["y"] + b["h"]
        b["y"] = b["y_no_lead"]
        b["h"] = bottom - b["y"]
    out["body"] = b
    gap = b.get("gap", 24)
    rects = comp.grid_rects(b, plan, b.get("col_gap", gap), b.get("row_gap", gap))
    results = []
    for k, block in enumerate(blocks):
        iss: list = []
        results.append((resolve_block(layout, deck, slide, st, k, block, rects[k], iss), iss))
    # 中身が少なくて文字を大きくしたブロックは、同じスライドの同じ種類のブロックと倍率をそろえる（いちばん小さい倍率に合わせて 2 周目を解く）
    # 本文の文字（bullets / text / steps / cards）は同じ「本文」として倍率をそろえる（隣の text が小さいまま bullets だけ大きい、を避ける・s4-A-03）
    limits: dict = {}
    for blk, _ in results:
        f = blk.get("thin_factor")
        if f is not None:
            gk = THIN_GROUP.get(blk["type"], blk["type"])
            limits[gk] = min(limits.get(gk, f), f)
    for k, block in enumerate(blocks):
        blk, iss = results[k]
        f = blk.get("thin_factor")
        gk = THIN_GROUP.get(blk["type"], blk["type"]) if f is not None else None
        if f is not None and f > limits[gk] + 1e-6:
            iss = []
            blk = resolve_block(layout, deck, slide, st, k, block, rects[k], iss, limits={blk["type"]: limits[gk]})
        out["blocks"].append(blk)
        out["issues"].extend(iss)
    return out


_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def is_color_value(theme, c) -> bool:
    """テーマ colors のキー名、または #RGB / #RRGGBB 形式の hex であれば True。"""
    if not isinstance(c, str):
        return False
    return c in theme.get("colors", {}) or bool(_HEX_RE.match(c))


def col(theme, c):
    """テーマトークン名 → hex。hex 直書きはそのまま返す。不正な値は fail する
    （通常は validate_deck が事前に検出するので、これは最後の防波堤）。"""
    colors = theme.get("colors", {})
    if isinstance(c, str) and c in colors:
        return dschema.normalize_hex(colors[c])
    if isinstance(c, str) and _HEX_RE.match(c):
        return dschema.normalize_hex(c)   # #RGB は #RRGGBB にそろえる（PPTX は 6 桁しか受けない）
    fail(f"不明な色指定 '{c}' です。テーマトークン名か #RRGGBB 形式のhexを指定してください")


# ---------------------------------------------------------------------------
# フォント（fonts.heading / body / code は文字列 または 文字列配列）
# ---------------------------------------------------------------------------

FONT_FALLBACK_SANS = '"Yu Gothic UI", "Meiryo", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Noto Sans CJK JP", sans-serif'
FONT_FALLBACK_MONO = '"Consolas", "Menlo", "Courier New", monospace'


def _font_names(value) -> list:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    if value:
        return [str(value)]
    return []


def font_css(value, mono: bool = False) -> str:
    """fonts.* の値（文字列 or 配列）から CSS font-family 用の文字列を作る。
    末尾に組込フォールバック（和文 or 等幅）を必ず付ける。"""
    # 検証（validate_theme_data）をすり抜けた値でも CSS の外へ出ないよう、引用符・タグ・区切りと制御文字を除く
    names = [n for n in (dschema.FONT_NAME_BAD_RE.sub("", n).strip() for n in _font_names(value)) if n]
    quoted = ", ".join(f'"{n}"' for n in names)
    fallback = FONT_FALLBACK_MONO if mono else FONT_FALLBACK_SANS
    return f"{quoted}, {fallback}" if quoted else fallback


def font_pptx(value):
    """fonts.* の値（文字列 or 配列）から PPTX に設定する先頭の1フォント名を返す。"""
    names = [n for n in (dschema.FONT_NAME_BAD_RE.sub("", n).strip() for n in _font_names(value)) if n]
    return names[0] if names else None


def steps_arrow_header(i, n, x, y, card_w, gap, header_h, b, theme):
    """steps の見出しを工程の矢羽根（先頭は五方向、2つ目以降は山形）にした canvas 要素。
    矢じりは次のカードとの隙間に食い込ませ、全段が1本の流れに見えるようにする。"""
    ext = gap - 4 if i < n - 1 else 0
    return {"kind": "shape", "geom": "homePlate" if i == 0 else "chevron", "x": round(x, 2), "y": round(y, 2),
            "w": round(card_w + ext, 2), "h": header_h, "adj": {"adj": 28000},
            "fill": pe.Ctx(theme).c(b.get("header_fill", "primary")), "name": f"工程{i + 1}"}


def norm_items(items):
    """bullets 配列を正規化。要素は文字列 or {text, children, size, color, bold}。"""
    return autofit.norm_items(items)


def _route_edge(A, B):
    """2ノード間の直交ポリライン経路と、ラベル配置座標を返す。"""
    dx = B["cx"] - A["cx"]; dy = B["cy"] - A["cy"]
    if abs(A["cx"] - B["cx"]) < 2 and abs(dy) >= 1:
        # ほぼ同列：垂直に接続
        if dy > 0:
            p = [(A["cx"], A["y"] + A["h"]), (B["cx"], B["y"])]
        else:
            p = [(A["cx"], A["y"]), (B["cx"], B["y"] + B["h"])]
        return p, (A["cx"] + 8, (A["cy"] + B["cy"]) / 2)
    if abs(dy) < 1:
        # 同一レーン：水平に接続
        if dx >= 0:
            p = [(A["x"] + A["w"], A["cy"]), (B["x"], B["cy"])]
        else:
            p = [(A["x"], A["cy"]), (B["x"] + B["w"], B["cy"])]
        return p, ((p[0][0] + p[1][0]) / 2, A["cy"] - 12)
    # レーンをまたぐ：H-V-H の Z 経路
    if dx >= 0:
        sx = A["x"] + A["w"]; ex = B["x"]
    else:
        sx = A["x"]; ex = B["x"] + B["w"]
    midx = (sx + ex) / 2
    p = [(sx, A["cy"]), (midx, A["cy"]), (midx, B["cy"]), (ex, B["cy"])]
    return p, (midx + 8, (A["cy"] + B["cy"]) / 2)


def _io_lines_fit(nd: dict, w: float, h: float, size: float, min_size: float, pad: float):
    """swimlane の io ノード（左 input・右 output の 2 欄）の項目を、幅に収まるよう折り返した行にする。
    size から min_size まで 1px ずつ下げ、全部の項目が（長い項目は 2 行までに折って）幅に収まり、かつ箱の高さに入る最初の大きさを返す。
    返り値: ({"input": [[行, …], …], "output": […]}, size)。min_size でも収まらなければ None（呼び出し側が従来の縮小に戻す）。"""
    half_w = (w - 2) / 2 - 2 * pad
    cols = {k: [str(v) for v in (nd.get(k) or [])] for k in ("input", "output")}
    if not any(cols.values()):
        return None
    sz = size
    while sz >= min_size - 1e-9:
        lines = {}
        ok = True
        for k, vals in cols.items():
            lines[k] = []
            for v in vals:
                if de.text_width(v, sz) <= half_w:
                    lines[k].append([v])
                    continue
                two = None
                if de.text_width(v, sz) <= half_w * 2 * 0.94:
                    two = ja_text._equal_two(v, sz, half_w, None, False, 2) or _split_greedy(v, sz, half_w)
                if not two or any(de.text_width(x, sz) > half_w for x in two):
                    ok = False
                    break
                lines[k].append(two)
            if not ok:
                break
        if ok:
            need = max(sz * 1.2 + sum(len(it) * sz * 1.2 + 3 for it in lines[k]) for k in lines) + pad * 2
            if need <= h:
                return lines, sz
        sz -= 1
    return None


def _split_greedy(v: str, size: float, width: float):
    """文字列を 2 行に分ける（ja_text._equal_two で切れ目が見つからないとき。漢字だけの語・カタカナ語は文節の切れ目が無い）。
    行頭に来てはいけない文字（長音・小さい仮名・句読点）では切らない。漢字だけの語は 1 行目に幅いっぱい入れて 2 行目を短く（「原因分析／報告」）、
    それ以外は前後の幅を近づける（「ポスト／モーテム」）。2 行目は 2 文字以上残す。"""
    bad = set("ーッゃゅょっぁぃぅぇぉ、。・）」』】,.)")
    cands = [k for k in range(2, len(v) - 1)
             if v[k] not in bad and de.text_width(v[:k], size) <= width and de.text_width(v[k:], size) <= width]
    if not cands:
        return None
    if all("\u4e00" <= ch <= "\u9fff" for ch in v):
        k = max(cands)
    else:
        k = min(cands, key=lambda k: abs(de.text_width(v[:k], size) - de.text_width(v[k:], size)))
    return [v[:k], v[k:]]


def swimlane_geometry(slide, st, slide_no=None):
    """スイムレーン図の全要素（レーン・グループ・工程・ノード・エッジ経路）の座標を計算する。
    HTML と PPTX で同一のジオメトリを共有し、見た目を一致させる。
    slide_no（1始まりのスライド番号）を渡すと、自動拡張の warning にどのスライドかを含められる。"""
    f = st["flow"]
    lanes = slide.get("lanes", [])
    n = max(1, len(lanes))
    has_group = any(l.get("group") for l in lanes)
    g1 = f.get("g1_w", 34) if has_group else 0
    g2 = f.get("g2_w", 96)
    label_w = g1 + g2
    phases = slide.get("phases") or []
    phase_h = f.get("phase_h", 30) if any(phases) else 0
    content_x = f["x"] + label_w
    content_w = f["w"] - label_w
    top = f["y"] + phase_h
    avail_h = f["h"] - phase_h
    row_h = avail_h / n
    maxcol = 0
    for nd in slide.get("nodes", []):
        maxcol = max(maxcol, nd.get("col", 0))
    explicit_cols = slide.get("cols")
    cols = max(1, explicit_cols or (maxcol + 1))
    if explicit_cols and maxcol >= cols:
        new_cols = maxcol + 1
        where = f"{slide_no}枚目（type=swimlane）: " if slide_no else ""
        warn(f"{where}cols（{cols}）を超える col={maxcol} のノードがあるため cols を {new_cols} に自動拡張しました")
        cols = new_cols
    col_w = content_w / cols
    lane_boxes = []
    for i, l in enumerate(lanes):
        y = top + i * row_h
        lane_boxes.append({"label": l.get("name", l.get("label", "")),
                           "x": f["x"] + g1, "y": y, "w": g2, "h": row_h,
                           "band_x": content_x, "band_y": y, "band_w": content_w, "band_h": row_h,
                           "alt": i % 2})
    groups = []
    if has_group:
        i = 0
        while i < n:
            gname = lanes[i].get("group")
            j = i
            while j + 1 < n and lanes[j + 1].get("group") == gname and gname is not None:
                j += 1
            if gname:
                groups.append({"label": gname, "x": f["x"], "y": top + i * row_h,
                               "w": g1, "h": (j - i + 1) * row_h})
            i = j + 1
    phase_boxes = []
    for c, ph in enumerate(phases):
        if ph:
            phase_boxes.append({"label": ph, "x": content_x + c * col_w, "y": f["y"], "w": col_w, "h": phase_h})
    node_map = {}
    for nd in slide.get("nodes", []):
        c = nd.get("col", 0); L = nd.get("lane", 0)
        cx = content_x + (c + 0.5) * col_w
        cy = top + (L + 0.5) * row_h
        shape = nd.get("shape", "task")
        if shape == "decision":
            # ひし形は箱に内接する形で描く（HTML は SVG polygon、PPTX は DIAMOND プリセット）。
            # 0.88 倍でレーン帯の上下境界から約 6% の余白を確保し、ストロークがはみ出さないようにする。
            # 当たり判定（配線・ラベル衝突）もこの外接矩形で行うので、菱形の角がすり抜けない。
            w = min(col_w, row_h) * 0.88; h = w
        elif shape in ("terminal", "connector"):
            w = col_w * f.get("node_wr", 0.72); h = row_h * 0.42
        elif shape == "marker":
            w = min(col_w, row_h) * 0.34; h = w
        elif shape == "mail":
            w = min(col_w, row_h) * 0.44; h = w * 0.72
        elif shape == "io":
            w = col_w * 0.88; h = row_h * 0.92
        else:  # task, system
            w = col_w * f.get("node_wr", 0.72); h = row_h * f.get("node_hr", 0.52)
        text = nd.get("text", nd.get("label", ""))  # label は text の別名として受理
        rec = {"shape": shape, "variant": nd.get("variant"), "kind": nd.get("kind"), "text": text,
               "cx": cx, "cy": cy, "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
               "input": nd.get("input"), "output": nd.get("output"), "loop": nd.get("loop")}
        # 文字を箱に収める: 既定サイズで入らなければ下限 10px まで縮小し、折り返し行も確定する
        # （HTML / PPTX 共通。「起/票」のような語の途中での折り返しを減らし、はみ出しを防ぐ）
        ns = f.get("node_size", 14)
        base = {"task": ns, "system": ns, "decision": ns - 2, "terminal": ns - 2, "connector": ns - 3}.get(shape)
        if base and text:
            if shape == "decision":
                inner_w, inner_h = w * 0.62, h * 0.58
            elif shape == "connector":
                inner_w, inner_h = w * 0.68, h - 4
            elif shape == "terminal":
                inner_w, inner_h = w - 14, h - 4
            else:
                inner_w, inner_h = w - 12, h - 6
            size, lines = de.fit_font_size(text, base, inner_w, inner_h, 1.15, min_size=10, max_lines=3)
            rec["font_size"] = size
            rec["lines"] = lines
        if shape == "io":
            half_w = (w - 2) / 2 - 12
            items = [str(v) for v in (nd.get("input") or []) + (nd.get("output") or [])]
            io_size = f.get("io_size", 11)
            # まず「文字を 10px 未満にしない」範囲で、長い項目を 2 行に折って収める（箱の高さに入るときだけ）。
            # 収まらないときは従来どおり 1 行のまま 8px まで縮める
            io_lines = _io_lines_fit(nd, w, h, io_size, f.get("io_min_size", 10), f.get("io_pad", 6))
            if io_lines is not None:
                rec["io_lines"], rec["io_font"] = io_lines
            else:
                while io_size > 8 and items and max(de.text_width(v, io_size) for v in items) > half_w:
                    io_size -= 1
                rec["io_font"] = io_size
        node_map[nd["id"]] = rec
    # エッジ配線: 共通の格子ルーター（diagram_engine）。列境界・レーン境界のガターをトラックにし、
    # 途中のノードを横切らない直交経路を選ぶ。同じ辺から出る複数線・同じ回廊を通る複数線は
    # 等間隔にずらし、ラベルは線の脇に背景ピル付きで置く（Archify の workflow レンダラに倣う）。
    my = row_h * (1 - f.get("node_hr", 0.64)) / 2   # レーン内の上下マージン（片側）
    mx = col_w * (1 - f.get("node_wr", 0.74)) / 2
    h_tracks = [top + my * 0.5, top + avail_h - my * 0.5]
    for i in range(1, n):
        yb = top + i * row_h
        # レーン境界線そのものの上を線が走らないよう、境界の上下マージンの中央を通す
        h_tracks += [yb - my * 0.5, yb + my * 0.5]
    v_tracks = [content_x + mx * 0.5, content_x + content_w - mx * 0.5] + \
               [content_x + c * col_w for c in range(1, cols)]
    grid = de.Grid(content_x, top, content_w, avail_h, n, cols,
                   node_wr=f.get("node_wr", 0.74), node_hr=f.get("node_hr", 0.64),
                   v_tracks=v_tracks, h_tracks=h_tracks)
    boxes = {nid: dict(nd, label=nd.get("text", "")) for nid, nd in node_map.items()}
    diags = []
    routed = de.route_all(grid, boxes, slide.get("edges", []), f.get("label_size", 13), diags,
                          subject_prefix="")
    edges = []
    for e in routed:
        lb = e.get("label_box")
        edges.append({"points": e["points"], "label": e.get("label", ""),
                      "label_pos": ((lb["cx"], lb["cy"]) if lb else None), "label_box": lb,
                      "label_back": e.get("label_back"), "label_back_box": e.get("label_back_box"),
                      "style": e.get("style", "solid"), "variant": e.get("variant", "default"),
                      "arrow": e.get("arrow", "end"), "from": e.get("from"), "to": e.get("to")})
    return {"flow": f, "content_x": content_x, "content_w": content_w, "top": top,
            "row_h": row_h, "col_w": col_w, "cols": cols, "lanes": lane_boxes,
            "groups": groups, "phases": phase_boxes, "nodes": node_map, "edges": edges,
            "diagnostics": diags}


# スイムレーンの凡例エントリ（業務フロー標準記号）: (shape, variant/kind, ラベル, 説明)
SWIMLANE_LEGEND = [
    ("task", "onpf", "作業（オンラインPF）", "PF 上で実施する作業"),
    ("task", "onother", "作業（PF以外）", "他システムで実施する作業"),
    ("task", "offline", "作業（オフライン）", "オフラインで実施する作業"),
    ("system", None, "システム/サービス", "利用するシステム・サービス名"),
    ("decision", None, "分岐条件", "フロー内で分岐する条件"),
    ("io", None, "成果物（input/output）", "作業の入力・出力ドキュメント"),
    ("marker", "start", "フロー開始", "フローの起点"),
    ("marker", "end", "フロー終了", "フローの終点"),
    ("marker", "mid", "フロー途中", "フロー途中の状態"),
    ("terminal", "prev", "前ページより", "前ページからの続き"),
    ("terminal", "next", "次ページへ", "後続ページへ続く"),
    ("connector", None, "遷移先（分岐）", "複数の後続業務への遷移先"),
    ("mail", None, "メール配信", "メール通知の発生"),
    ("flow", "solid", "作業の流れ", "実線＝作業の流れ"),
    ("flow", "dashed", "システム操作", "破線＝システム操作"),
]


def _sw_node_html(nd, theme, f):
    """スイムレーンのノード1個を HTML で描く（フロー本体・凡例ページ共通）。"""
    def C(tok):
        return col(theme, tok)
    x, y, w, h = nd["x"], nd["y"], nd["w"], nd["h"]
    box = f'position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;'
    shape = nd["shape"]; ns = f.get("node_size", 14)
    text = "<br>".join(esc(ln) for ln in nd["lines"]) if nd.get("lines") else esc(nd.get("text", ""))
    fs = nd.get("font_size")  # swimlane_geometry で収まるよう縮小したフォントサイズ（無ければ既定）
    # 折り返し位置はエンジン側で決めているので、ブラウザに再折り返しさせない（1 文字だけ落ちる崩れを防ぐ）
    nowrap = "white-space:nowrap;" if nd.get("lines") else ""
    center = ('display:flex;align-items:center;justify-content:center;text-align:center;'
              'box-sizing:border-box;line-height:1.15;padding:2px;' + nowrap)
    if shape == "decision":
        # 箱に内接するひし形（PPTX の DIAMOND プリセットと同じ輪郭。当たり判定も箱＝外接矩形で一致する）
        return (f'<div style="{box}">'
                f'<svg viewBox="0 0 {w:.1f} {h:.1f}" width="{w:.1f}" height="{h:.1f}" style="position:absolute;inset:0;overflow:visible;">'
                f'<polygon points="{w/2:.1f},1 {w-1:.1f},{h/2:.1f} {w/2:.1f},{h-1:.1f} 1,{h/2:.1f}" '
                f'fill="{C(f.get("decision_fill","on_primary_soft"))}" stroke="{C(f.get("decision_border","accent"))}" '
                f'stroke-width="2" stroke-linejoin="round"/></svg>'
                f'<div style="position:absolute;inset:{h*0.2:.1f}px {w*0.18:.1f}px;{center}font-size:{fs or ns-2}px;'
                f'color:{C(f.get("decision_color","primary"))};">{text}</div></div>')
    if shape == "terminal":
        return (f'<div style="{box}{center}font-size:{fs or ns-2}px;background:{C(f.get("terminal_fill","surface"))};'
                f'border:1.5px solid {C(f.get("terminal_border","muted"))};border-radius:{min(h/2, rtok(theme, "pill", 999)):.0f}px;'
                f'color:{C(f.get("terminal_color","muted"))};">{text}</div>')
    if shape == "connector":
        # M-90: PPTX（PENTAGON + connector_border 罫線）と見た目を揃える。
        # div+clip-path は塗り・背景しか切り抜かず斜辺に罫線を描けない（周囲と同系色の背景だと
        # 輪郭が消えてただの四角に見える）ため、SVG の polygon（fill+stroke）で5辺すべてに
        # 一貫した罫線を描く。テキストは別レイヤーの div で中央寄せする。
        pts = f"0,0 {w * 0.72:.1f},0 {w:.1f},{h / 2:.1f} {w * 0.72:.1f},{h:.1f} 0,{h:.1f}"
        return (f'<div style="{box}">'
                f'<svg viewBox="0 0 {w:.1f} {h:.1f}" style="position:absolute;inset:0;'
                f'width:100%;height:100%;overflow:visible;" preserveAspectRatio="none">'
                f'<polygon points="{pts}" fill="{C(f.get("connector_fill","surface"))}" '
                f'stroke="{C(f.get("connector_border","muted"))}" stroke-width="1"/></svg>'
                f'<div style="position:absolute;inset:0;{center}font-size:{fs or ns-3}px;'
                f'color:{C(f.get("connector_color","text"))};">{text}</div></div>')
    if shape == "marker":
        kind = nd.get("kind", "mid")
        mc = {"start": f.get("marker_start", "accent"), "end": f.get("marker_end", "primary"),
              "mid": f.get("marker_mid", "#E6B800")}.get(kind, f.get("marker_mid", "#E6B800"))
        return f'<div style="{box}background:{C(mc)};border-radius:50%;border:1.5px solid {C("background")};"></div>'
    if shape == "mail":
        return (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" style="{box}">'
                f'<rect x="1" y="1" width="{w-2:.0f}" height="{h-2:.0f}" fill="{C("background")}" '
                f'stroke="{C(f.get("edge_color","text"))}" stroke-width="1.5"/>'
                f'<path d="M1,1 L{w/2:.0f},{h*0.55:.0f} L{w-1:.0f},1" fill="none" '
                f'stroke="{C(f.get("edge_color","text"))}" stroke-width="1.5"/></svg>')
    if shape == "io":
        half = (w - 2) / 2
        cells = []
        for key, lbl in (("input", "input"), ("output", "output")):
            vals = nd.get(key) or []
            fitted_io = (nd.get("io_lines") or {}).get(key)
            if fitted_io:
                # 折り返しはエンジンが決めている（HTML と PPTX で同じ位置）。ブラウザに再折り返しさせない
                lis = "".join(f'<div style="margin-top:3px;white-space:nowrap;">{"<br>".join(esc(x) for x in it)}</div>' for it in fitted_io)
            else:
                lis = "".join(f'<div style="margin-top:3px;">{esc(v)}</div>' for v in vals)
            cells.append(f'<div style="width:{half:.0f}px;padding:6px;box-sizing:border-box;'
                         f'font-size:{nd.get("io_font", f.get("io_size",11))}px;color:{C(f.get("io_color","text"))};line-height:1.2;">'
                         f'<div style="font-weight:700;white-space:nowrap;color:{C(f.get("io_head_color","accent"))};">{lbl}</div>{lis}</div>')
        return (f'<div style="{box}display:flex;background:{C(f.get("io_fill","on_primary_soft"))};'
                f'border:1px solid {C(f.get("io_border","accent"))};border-radius:{rtok(theme, "node_sm", 8):g}px;box-sizing:border-box;overflow:hidden;">'
                f'{cells[0]}<div style="width:1px;background:{C("border")};"></div>{cells[1]}</div>')
    if shape == "system":
        return (f'<div style="{box}{center}font-size:{fs or ns}px;background:{C(f.get("system_fill","surface"))};'
                f'border:1.5px solid {C(f.get("system_border","muted"))};color:{C(f.get("system_color","text"))};">{text}</div>')
    # task (+variant)
    variant = nd.get("variant") or "onother"
    vmap = {
        "onpf": (f.get("task_onpf_fill", "on_primary_soft"), f.get("task_border", "accent"), f.get("task_onpf_color", "primary")),
        "onother": (f.get("task_onother_fill", "background"), f.get("task_border", "accent"), f.get("task_color", "text")),
        "offline": (f.get("task_offline_fill", "surface"), f.get("task_offline_border", "muted"), f.get("task_color", "text")),
    }
    fill_t, bord_t, col_t = vmap.get(variant, vmap["onother"])
    loop = ""
    if nd.get("loop"):
        # 反復記号: ノード右上に小さな円弧矢印（SVG）。旧実装の「↺」1 文字は 16px でも見落とされやすかった。
        # テキストの div の外（兄弟要素）に置く: 中に入れると check_layout がテキスト高の見積もりに
        # バッジ分を含めて「はみ出し」と誤検出するため。
        loop = (f'<svg width="18" height="18" viewBox="0 0 18 18" style="position:absolute;left:{x + w - 11:.1f}px;'
                f'top:{y - 8:.1f}px;" aria-hidden="true">'
                f'<circle cx="9" cy="9" r="8" fill="{C("background")}" stroke="{C("accent")}" stroke-width="1.5"/>'
                f'<path d="M13 9a4 4 0 1 1-1.2-2.9 M12 4.5v2.6h-2.6" fill="none" stroke="{C("accent")}" stroke-width="1.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return (f'<div style="{box}{center}font-size:{fs or ns}px;background:{C(fill_t)};'
            f'border:2px solid {C(bord_t)};border-radius:{f.get("node_radius",8)}px;color:{C(col_t)};">{text}</div>{loop}')


def _legend_sym_size(shape):
    return {"decision": (26, 26), "marker": (16, 16), "mail": (30, 20), "terminal": (74, 24),
            "connector": (66, 26), "io": (112, 42), "flow": (54, 0)}.get(shape, (60, 26))


def _legend_symbol_html(shape, vk, x, cy, sym_w, theme, f):
    """凡例の1シンボルを HTML で描く（中心 x..x+sym_w に配置）。"""
    w, h = _legend_sym_size(shape)
    cx = x + sym_w / 2
    if shape == "flow":
        dash = ' stroke-dasharray="7,5"' if vk == "dashed" else ""
        ec = col(theme, f.get("edge_color", "text"))
        return (f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;'
                f'pointer-events:none;" viewBox="0 0 {CANVAS_W} {CANVAS_H}">'
                f'<defs><marker id="lg-arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" '
                f'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L9,4 L0,8 z" fill="{ec}"/></marker></defs>'
                f'<line x1="{cx-w/2:.0f}" y1="{cy:.0f}" x2="{cx+w/2:.0f}" y2="{cy:.0f}" stroke="{ec}" '
                f'stroke-width="2"{dash} marker-end="url(#lg-arrow)"/></svg>')
    nd = {"shape": shape, "variant": (vk if shape == "task" else None),
          "kind": (vk if shape == "marker" else None), "text": "",
          "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
          "input": (["…"] if shape == "io" else None), "output": (["…"] if shape == "io" else None),
          "loop": None}
    return _sw_node_html(nd, theme, f)


def _diag_legend_sym_size(sample):
    """diagram_legend の 1 シンボルの箱サイズ（w, h）。edge は h=0（線）。"""
    if "edge" in sample:
        return (88, 0)
    if "kind" in sample:
        k = sample["kind"]
        if k == "decision":
            return (54, 40)
        if k == "start":
            return (108, 34)
        return (108, 40)
    return (108, 40)  # icon / node（variant 色見本）


def _diag_legend_sym_html(sample, x, cy, sym_w, d, theme, hf, uid=""):
    """diagram_legend の 1 シンボル（type アイコン / variant 色 / lifecycle kind / edge 矢印）を
    実図と同じ描画関数（_diag_node_html / _edge_visual）で描く。中心 x..x+sym_w に配置。"""
    w, h = _diag_legend_sym_size(sample)
    cx = x + sym_w / 2
    if "edge" in sample:
        ev = _edge_visual({"variant": sample["edge"]}, d)
        ec = col(theme, ev["color"]); wpx = ev["w"]
        dash = f' stroke-dasharray="{ev["dash"]}"' if ev["dash"] else ""
        x1, x2 = cx - w / 2, cx + w / 2
        mid = f"dlm-{uid}"
        if ev["open"]:
            marker = (f'<marker id="{mid}" markerWidth="12" markerHeight="12" refX="9" refY="5" orient="auto" '
                      f'markerUnits="userSpaceOnUse"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{ec}" stroke-width="1.6"/></marker>')
        else:
            marker = (f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto" '
                      f'markerUnits="userSpaceOnUse"><path d="M0,0 L9,4 L0,8 z" fill="{ec}"/></marker>')
        return (f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;'
                f'pointer-events:none;" viewBox="0 0 {CANVAS_W} {CANVAS_H}"><defs>{marker}</defs>'
                f'<line x1="{x1:.0f}" y1="{cy:.0f}" x2="{x2:.0f}" y2="{cy:.0f}" stroke="{ec}" '
                f'stroke-width="{wpx}"{dash} marker-end="url(#{mid})"/></svg>')
    box = {"label": "", "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h}
    if "kind" in sample:
        k = sample["kind"]
        box["kind"] = k
        box["shape"] = "diamond" if k == "decision" else ("pill" if k == "start" else "rect")
        return _diag_node_html(box, {}, d, theme, "lifecycle", hf)
    box["shape"] = "rect"
    if "node" in sample:
        box["variant"] = sample["node"]
    else:
        box["type"] = sample["icon"]
    return _diag_node_html(box, {}, d, theme, "architecture", hf)


def norm_legend_items(items):
    """swimlane の legend_items を (shape, variant_or_kind, label, desc) の4要素タプル配列に正規化する。
    4要素配列（リスト/タプル）はそのまま、辞書は {shape, variant|kind, label, desc} から変換する。"""
    out = []
    for it in items or []:
        if isinstance(it, dict):
            shape = it.get("shape") or it.get("kind")
            variant = it.get("variant", it.get("kind"))
            label = it.get("label", "")
            desc = it.get("desc", "")
            out.append((shape, variant, label, desc))
        else:
            out.append(tuple(it))
    return out


# ---------------------------------------------------------------------------
# ネイティブ図解タイプ（architecture / dataflow / lifecycle / sequence）の見た目解決と HTML 描画
# ジオメトリと診断は diagram_engine が担当し、ここではテーマトークンへの解決と描画だけを行う。
# PPTX 側（build_pptx 内の _diag_* 関数）も同じ _node_visual / _edge_visual を使う。
# ---------------------------------------------------------------------------

GRID_DIAGRAM_TYPES = ("architecture", "dataflow", "lifecycle")
# HTML（html_slide_body）と PPTX（build_pptx の builders）の両方に描画器があるタイプ。
# レイアウト JSON にだけ足したタイプは validate_deck が止める。新タイプを描画できるようにしたらここに足す。
RENDERED_TYPES = frozenset({
    "canvas", "title", "section", "bullets", "two_column", "table", "status_table", "code", "quote", "image",
    "image_text", "closing", "agenda", "steps", "matrix", "cards", "swimlane", "swimlane_legend",
    "architecture", "dataflow", "lifecycle", "sequence", "diagram_legend", "schedule",
    "pattern", "composite", "split",
}) | frozenset(engine_registry.names())     # A 型タイプ（提案書系・kpi・chart）は登録表（engine_registry）から
DIAGRAM_TYPES = GRID_DIAGRAM_TYPES + ("sequence",)

# type アイコン（16×16、stroke ベース）。HTML はインライン SVG、PPTX はプリセット図形で近似する。
ICON_PATHS = {
    "frontend": "M1.5 2.5h13v11h-13z M1.5 5.5h13 M3.6 4h.01 M5.6 4h.01",
    "backend": "M2 2.5h12v4.5H2z M2 9h12v4.5H2z M4.6 4.75h.01 M4.6 11.25h.01",
    "database": ("M2.5 4.5c0-1.4 2.5-2.5 5.5-2.5s5.5 1.1 5.5 2.5v7c0 1.4-2.5 2.5-5.5 2.5S2.5 12.9 2.5 11.5z "
                 "M2.5 4.5c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5 M2.5 8c0 1.4 2.5 2.5 5.5 2.5S13.5 9.4 13.5 8"),
    "cloud": "M5 13.5h6.5a3 3 0 0 0 .5-5.96A4 4 0 0 0 4.3 7.2 3.2 3.2 0 0 0 5 13.5z",
    "security": "M8 1.8l5.5 2.2v3.9c0 3.3-2.3 5.6-5.5 6.6-3.2-1-5.5-3.3-5.5-6.6V4z M5.6 8l1.7 1.7 3.2-3.2",
    "messagebus": "M2 4.5h12 M2 8h9 M11.5 6.5L13 8l-1.5 1.5 M2 11.5h12",
    "external": "M12 9v4.5H2.5V4H7 M9.5 2H14v4.5 M14 2L7.5 8.5",
}
# lifecycle の kind 記号（右上の小さなグリフ）
KIND_GLYPHS = {
    "start": "M5 3l7 5-7 5z",
    "waiting": "M4 2h8 M4 14h8 M5 2c0 4 3 5 3 6s-3 2-3 6 M11 2c0 4-3 5-3 6s3 2 3 6",
    "success": "M3 8.5l3.2 3.2L13 5",
    "failure": "M4 4l8 8 M12 4l-8 8",
}
EDGE_DASH_SVG = {"dashed": "7,5", "security": "8,4,2,4", "return": "6,4"}
EDGE_DASH_PPTX = {"dashed": "dash", "security": "dashDot", "return": "sysDash"}


def _node_visual(box: dict, d: dict, kind: str, pill_r: float = 999) -> dict:
    """ノード 1 個の描画属性（テーマトークン名）を variant / lifecycle kind から解決する。
    返り値: fill, border, border_w, dash(bool), color, sub_color, radius_mode(rect|pill|diamond)"""
    v = box.get("variant") or "default"
    vis = {"fill": d.get("node_fill", "background"), "border": d.get("node_border", "border"),
           "border_w": d.get("node_border_w", 1.5), "dash": False,
           "color": d.get("node_color", "heading_text"), "sub_color": d.get("sub_color", "muted"),
           "shape": box.get("shape", "rect")}
    if kind == "lifecycle":
        k = box.get("kind") or "active"
        vis["fill"] = d.get(f"{k}_fill", vis["fill"])
        vis["border"] = d.get(f"{k}_border", vis["border"])
        if k in ("waiting", "external"):
            vis["dash"] = True
        elif k == "failure":
            vis["border_w"] = 2
            vis["dash"] = True
        elif k == "success":
            vis["color"] = d.get("success_color", "on_primary")
            vis["sub_color"] = d.get("success_sub_color", "on_primary_soft")
            vis["border_w"] = 2
        elif k in ("start", "decision"):
            vis["border_w"] = 2
            if k == "start" and pill_r < 4:
                # 角丸が無い shape（sharp）では start が process と形で区別できない → 枠線を太くして区別する（角丸のある shape は従来どおり）
                vis["border_w"] = d.get("start_border_w_sharp", 3.5)
    if v == "emphasis":
        vis["fill"] = d.get("emphasis_fill", "highlight_fill")
        vis["border"] = d.get("emphasis_border", "accent")
        vis["border_w"] = d.get("emphasis_border_w", 2.5)
    elif v == "security":
        vis["border"] = d.get("security_border", "primary")
        vis["border_w"] = 2
        vis["dash"] = True
    elif v == "dashed":
        vis["border"] = d.get("dashed_border", "muted")
        vis["dash"] = True
    elif v == "muted":
        vis["color"] = d.get("muted_color", "muted")
        vis["sub_color"] = d.get("muted_color", "muted")
    return vis


def _node_hexes(vis: dict, d: dict, theme, box: dict) -> dict:
    """ノードの文字・アイコン・番号・タグの色（hex）。地（ノードの塗り / タグの塗り）の上で 4.5:1 に満たないときは、
    同じ色味のまま白 / 黒へ寄せる（color_pick.readable_on_all）。HTML と PPTX が共有する（色の組み合わせを両方に直書きしない）。"""
    fill = col(theme, vis["fill"])

    def on(tok, bg=fill):
        return cp.readable_on(col(theme, tok), bg)
    icon_tok = d.get("muted_color", "muted") if box.get("variant") == "muted" else d.get("icon_color", "accent")
    out = {"color": on(vis["color"]), "sub": on(vis["sub_color"]), "icon": on(icon_tok),
           "step": on(d.get("step_color", "accent")), "glyph": on(d.get("icon_color", "accent")),
           "tag": on(d.get("tag_color", "text"), col(theme, d.get("tag_fill", "highlight_fill")))}
    return out


def _step_label_spec(b: dict, vis: dict, d: dict, theme, hx: dict) -> dict:
    """lifecycle の番号ラベル（01 など）の位置と文字色。HTML と PPTX が共有する。
    四角のノードは左上の内側。角丸（pill）は輪郭の曲線の内側まで右へ寄せる。ひし形は中に置ける場所が無いので、
    外接矩形の左上の角（輪郭の外）に置き、地（背景・レーンの面）の上で読める色にする。番号が図形の輪郭に重ならない。"""
    import math
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    ss = d.get("step_size", 11)
    top = d.get("step_top", 4)
    if vis["shape"] == "diamond":
        c = cp.readable_on_all(col(theme, d.get("step_color", "accent")), [col(theme, "background"), col(theme, "surface")])
        return {"x": x + d.get("step_corner_dx", 4), "y": y + top - 1, "color": c, "size": ss}
    sx = x + d.get("step_dx", 8)
    if vis["shape"] == "pill":
        r = min(h / 2, rtok(theme, "pill", 999))
        if r > top:
            off = r - math.sqrt(max(0.0, r * r - (r - top) ** 2))
            sx = x + max(d.get("step_dx", 8), off + d.get("step_clear", 6))
    return {"x": sx, "y": y + top, "color": hx["step"], "size": ss}


def _edge_visual(e: dict, d: dict) -> dict:
    """エッジの描画属性: color(token), w(px), dash(svg pattern or None), pptx_dash, open_arrow(bool)。"""
    v = e.get("variant") or "default"
    if v == "emphasis":
        return {"color": d.get("edge_emphasis_color", "accent"), "w": d.get("edge_emphasis_w", 3),
                "dash": None, "pptx_dash": None, "open": False}
    if v == "security":
        return {"color": d.get("edge_security_color", "primary"), "w": d.get("edge_w", 2),
                "dash": EDGE_DASH_SVG["security"], "pptx_dash": EDGE_DASH_PPTX["security"], "open": False}
    if v == "dashed":
        return {"color": d.get("edge_dashed_color", "muted"), "w": d.get("edge_w", 2),
                "dash": EDGE_DASH_SVG["dashed"], "pptx_dash": EDGE_DASH_PPTX["dashed"], "open": False}
    if v == "return":
        return {"color": d.get("edge_return_color", "muted"), "w": max(1.5, d.get("edge_w", 2) - 0.5),
                "dash": EDGE_DASH_SVG["return"], "pptx_dash": EDGE_DASH_PPTX["return"], "open": True}
    return {"color": d.get("edge_color", "text"), "w": d.get("edge_w", 2), "dash": None, "pptx_dash": None, "open": False}


def _icon_svg(kind: str, size: float, color_hex: str, extra_style: str = "") -> str:
    path = ICON_PATHS.get(kind)
    if not path:
        return ""
    return (f'<svg width="{size:.0f}" height="{size:.0f}" viewBox="0 0 16 16" style="flex:none;{extra_style}" '
            f'aria-hidden="true"><path d="{path}" fill="none" stroke="{color_hex}" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


# AWS 風タイルアイコン（icon_style:"aws"）: type ごとのカテゴリ色の角丸タイル＋白いグリフ。
# 実物の AWS アイコン画像は使わず、役割（type）を AWS のカテゴリ配色に寄せて自作している。
# 各色は diagram トークン icon_tile_<type> で上書きできる。
ICON_TILE_COLORS = {
    "frontend": "#C925D1",    # マゼンタ（Front-End Web & Mobile 風）
    "backend": "#ED7100",     # オレンジ（Compute 風）
    "database": "#2E73B8",    # ブルー（Database 風）
    "cloud": "#01A88D",       # ティール（General / Managed 風）
    "security": "#DD344C",    # レッド（Security 風）
    "messagebus": "#E7157B",  # ピンク（Application Integration 風）
    "external": "#5A6B86",    # スレート（外部システム）
    "generic": "#7D8998",     # グレー（汎用）
}


def _icon_tile_color(d: dict, ntype: str):
    return d.get(f"icon_tile_{ntype}") or ICON_TILE_COLORS.get(ntype, ICON_TILE_COLORS["generic"])


def _icon_tile_svg(kind: str, tile: float, fill_hex: str, glyph_hex: str = "#ffffff", radius: float = 6) -> str:
    """カテゴリ色の角丸タイルの中央に白いグリフを置く（AWS アイコン風）。"""
    path = ICON_PATHS.get(kind)
    glyph = ""
    if path:
        inner = tile * 0.58
        off = (tile - inner) / 2
        scale = inner / 16.0
        glyph = (f'<g transform="translate({off:.2f},{off:.2f}) scale({scale:.3f})">'
                 f'<path d="{path}" fill="none" stroke="{glyph_hex}" stroke-width="{1.6/scale:.2f}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/></g>')
    return (f'<svg width="{tile:.0f}" height="{tile:.0f}" viewBox="0 0 {tile:.1f} {tile:.1f}" '
            f'style="flex:none;" aria-hidden="true">'
            f'<rect x="0.5" y="0.5" width="{tile-1:.1f}" height="{tile-1:.1f}" rx="{radius}" ry="{radius}" '
            f'fill="{fill_hex}"/>{glyph}</svg>')


def _glyph_svg(kind: str, size: float, color_hex: str, x: float, y: float) -> str:
    path = KIND_GLYPHS.get(kind)
    if not path:
        return ""
    fill = color_hex if kind == "start" else "none"
    return (f'<svg width="{size:.0f}" height="{size:.0f}" viewBox="0 0 16 16" style="position:absolute;'
            f'left:{x:.1f}px;top:{y:.1f}px;" aria-hidden="true"><path d="{path}" fill="{fill}" stroke="{color_hex}" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _diag_node_html(b: dict, fit: dict, d: dict, theme, kind: str, heading_font_css: str) -> str:
    """ノードカード 1 個（箱・アイコン・label/sublabel・tag・step）を HTML で描く。"""
    vis = _node_visual(b, d, kind, rtok(theme, "pill", 999))
    hx = _node_hexes(vis, d, theme, b)
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    pad = d.get("node_pad", 8)
    radius = d.get("node_radius", 10)
    fill = col(theme, vis["fill"]); border = col(theme, vis["border"])
    bstyle = "dashed" if vis["dash"] else "solid"
    parts = []
    box_css = f'position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;box-sizing:border-box;'
    if vis["shape"] == "diamond":
        # PPTX の DIAMOND プリセットと同じ輪郭（箱の 4 辺の中点を結ぶ）を SVG で描く
        dash_attr = ' stroke-dasharray="6,4"' if vis["dash"] else ""
        parts.append(f'<div style="{box_css}"><svg viewBox="0 0 {w:.1f} {h:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'style="position:absolute;inset:0;overflow:visible;"><polygon points="{w/2:.1f},1 {w-1:.1f},{h/2:.1f} '
                     f'{w/2:.1f},{h-1:.1f} 1,{h/2:.1f}" fill="{fill}" stroke="{border}" stroke-width="{vis["border_w"]}"'
                     f'{dash_attr} stroke-linejoin="round"/></svg></div>')
        icon_w = 0.0
    else:
        rad = f"{min(h/2, rtok(theme, 'pill', 999)):.0f}px" if vis["shape"] == "pill" else f"{radius}px"   # PPTX（adjustments）と同じく radius.pill で頭打ち
        parts.append(f'<div style="{box_css}background:{fill};border:{vis["border_w"]}px {bstyle} {border};border-radius:{rad};"></div>')
        icon_w = 0.0
    # type アイコン（左・縦中央）。icon_style:"aws" ならカテゴリ色タイル、既定は線画グリフ。
    icon_size = d.get("icon_size", 16)
    ntype = b.get("type") or "generic"
    if kind != "lifecycle" and ntype in ICON_PATHS and vis["shape"] == "rect":
        if d.get("icon_style") == "aws":
            tsz = d.get("icon_tile_size", 30)
            tile_hex = col(theme, _icon_tile_color(d, ntype))
            parts.append(f'<div style="position:absolute;left:{x+pad:.1f}px;top:{y + h/2 - tsz/2:.1f}px;'
                         f'width:{tsz}px;height:{tsz}px;">' + _icon_tile_svg(ntype, tsz, tile_hex) + "</div>")
            icon_w = tsz + 8
        else:
            # muted variant はアイコンも muted に落とす（type は形で表す・色は variant が担う、の唯一の例外）
            parts.append(f'<div style="position:absolute;left:{x+pad:.1f}px;top:{y + h/2 - icon_size/2:.1f}px;'
                         f'width:{icon_size}px;height:{icon_size}px;">'
                         + _icon_svg(ntype, icon_size, hx["icon"]) + "</div>")
            icon_w = icon_size + 6
    # テキストブロック（アイコンの右側の残り幅で中央寄せ）
    tx = x + pad + icon_w
    tw = max(10.0, w - 2 * pad - icon_w)
    if vis["shape"] == "diamond":
        tx, tw = x + w * 0.12, w * 0.76
    size = fit.get("size", d.get("node_size", 14)) if fit else d.get("node_size", 14)
    lines = fit.get("lines") if fit else [b.get("label", "")]
    label_html = "<br>".join(esc(ln) for ln in (lines or [b.get("label", "")]))
    sub_html = ""
    if b.get("sublabel"):
        sub_lines = fit.get("sub_lines") if fit else [b["sublabel"]]
        sub_html = (f'<div style="font-size:{d.get("sub_size", 11)}px;color:{hx["sub"]};'
                    f'line-height:1.2;margin-top:2px;">{"<br>".join(esc(l) for l in sub_lines)}</div>')
    parts.append(f'<div style="position:absolute;left:{tx:.1f}px;top:{y:.1f}px;width:{tw:.1f}px;height:{h:.1f}px;'
                 f'display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;'
                 f'box-sizing:border-box;padding:{pad}px 0;">'
                 f'<div style="font-size:{size}px;font-weight:700;color:{hx["color"]};line-height:1.15;'
                 f'white-space:nowrap;font-family:{esc(heading_font_css)};">{label_html}</div>{sub_html}</div>')
    # tag（右上に小さなピル。枠線に半分かぶせる）
    if b.get("tag"):
        ts = d.get("tag_size", 10)
        tw_ = de.text_width(b["tag"], ts) + 12
        parts.append(f'<div style="position:absolute;left:{x + w - tw_ - 8:.1f}px;top:{y - ts*0.8:.1f}px;'
                     f'width:{tw_:.1f}px;height:{ts*1.6:.1f}px;border-radius:{min(ts*0.8, rtok(theme, "pill", 999)):.0f}px;'
                     f'background:{col(theme, d.get("tag_fill", "highlight_fill"))};color:{hx["tag"]};'
                     f'font-size:{ts}px;font-weight:700;display:flex;align-items:center;justify-content:center;'
                     f'line-height:1;">{esc(b["tag"])}</div>')
    if kind == "lifecycle":
        if b.get("step"):
            sp_ = _step_label_spec(b, vis, d, theme, hx)
            parts.append(f'<div style="position:absolute;left:{sp_["x"]:.1f}px;top:{sp_["y"]:.1f}px;font-size:{sp_["size"]}px;'
                         f'font-weight:700;color:{sp_["color"]};line-height:1;">{esc(b["step"])}</div>')
        k = b.get("kind") or "active"
        if k in KIND_GLYPHS and vis["shape"] == "rect":
            gc = hx["color"] if k == "success" else hx["glyph"]
            parts.append(_glyph_svg(k, 13, gc, x + w - 21, y + 5))
    return "".join(parts)


def _arrow_defs(colors, uid: str) -> str:
    """色ごとの矢印マーカー（塗り三角）と開き矢印（return 用）を定義する。"""
    defs = []
    for hexc, is_open in colors:
        key = f"{uid}-{hexc.lstrip('#')}-{'o' if is_open else 'c'}"
        if is_open:
            defs.append(f'<marker id="ae-{key}" markerWidth="12" markerHeight="12" refX="9" refY="5" orient="auto-start-reverse" '
                        f'markerUnits="userSpaceOnUse"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{hexc}" stroke-width="1.6"/></marker>')
        else:
            defs.append(f'<marker id="ae-{key}" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto-start-reverse" '
                        f'markerUnits="userSpaceOnUse"><path d="M0,0 L9,4 L0,8 z" fill="{hexc}"/></marker>')
    return "<defs>" + "".join(defs) + "</defs>"


def _edges_svg_html(edges, d: dict, theme, uid: str, heading_font_css: str, layer: str = "both") -> str:
    """エッジ（折れ線＋矢印）とラベルピルを SVG オーバーレイに描く。
    layer="lines" で線だけ、"labels" でラベルピルだけ（ノードの上に重ねるため 2 層に分けて呼ぶ）。"""
    colors = set()
    lines = []
    pills = []
    lc = col(theme, d.get("label_color", "accent"))
    lf = col(theme, d.get("label_fill", "background"))
    lsize = d.get("label_size", 13)
    for e in edges:
        vis = _edge_visual(e, d)
        hexc = col(theme, vis["color"])
        colors.add((hexc, vis["open"]))
        key = f"{uid}-{hexc.lstrip('#')}-{'o' if vis['open'] else 'c'}"
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in e["points"])
        dash = f' stroke-dasharray="{vis["dash"]}"' if vis["dash"] else ""
        arrow = e.get("arrow", "end")
        mk = ""
        if arrow in ("end", "both"):
            mk += f' marker-end="url(#ae-{key})"'
        if arrow == "both":
            mk += f' marker-start="url(#ae-{key})"'
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{hexc}" stroke-width="{vis["w"]}"{dash}{mk} '
                     f'stroke-linejoin="round"/>')
        # 順方向のラベルと、双方向（arrow: both）の逆向きのラベル（label_back）
        for lb, ltext, classification in ((e.get("label_box"), e.get("label"), e.get("classification")),
                                          (e.get("label_back_box"), e.get("label_back"), None)):
            if not (lb and ltext):
                continue
            pills.append(f'<rect x="{lb["x"]:.1f}" y="{lb["y"]:.1f}" width="{lb["w"]:.1f}" height="{lb["h"]:.1f}" rx="{min(4, rtok(theme, "small", 6)):g}" fill="{lf}"/>')   # PPTX の _label_pill_pptx と同じ
            if classification:
                # ピルは 2 行分の高さ（engine が class_h を足している）。上段 label・下段 classification
                cs = d.get("class_size", 11)
                ch = e.get("class_h", cs * 1.2)
                pills.append(f'<text x="{lb["cx"]:.1f}" y="{lb["cy"] - ch / 2:.1f}" fill="{lc}" font-size="{lsize}" font-weight="700" '
                             f'text-anchor="middle" dominant-baseline="central">{esc(ltext)}</text>')
                pills.append(f'<text x="{lb["cx"]:.1f}" y="{lb["cy"] + (lb["h"] - ch) / 2 - 1:.1f}" fill="{col(theme, d.get("class_color", "muted"))}" '
                             f'font-size="{cs}" text-anchor="middle" dominant-baseline="central">{esc(classification)}</text>')
            else:
                pills.append(f'<text x="{lb["cx"]:.1f}" y="{lb["cy"]:.1f}" fill="{lc}" font-size="{lsize}" font-weight="700" '
                             f'text-anchor="middle" dominant-baseline="central">{esc(ltext)}</text>')
    body = ""
    if layer in ("both", "lines"):
        body += _arrow_defs(sorted(colors), uid) + "".join(lines)
    if layer in ("both", "labels"):
        body += "".join(pills)
    return (f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;pointer-events:none;" '
            f'viewBox="0 0 {CANVAS_W} {CANVAS_H}">' + body + "</svg>")


def _legend_html(items, y: float, x: float, d: dict, theme) -> str:
    if not items:
        return ""
    ls = d.get("legend_size", 12)
    lc = col(theme, d.get("legend_color", "muted"))
    ic = col(theme, d.get("icon_color", "accent"))
    cells = []
    for it in items:
        cells.append(f'<div style="display:flex;align-items:center;gap:5px;">{_icon_svg(it["type"], 14, ic)}'
                     f'<span>{esc(it["label"])}</span></div>')
    return (f'<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;height:{d.get("legend_h", 26)}px;'
            f'display:flex;align-items:center;gap:22px;font-size:{ls}px;color:{lc};">' + "".join(cells) + "</div>")


def _group_html(g: dict, d: dict, theme) -> str:
    kind = g.get("kind") or "generic"
    radius = d.get("group_radius", 10)
    gc = col(theme, d.get("group_color", "muted"))
    if kind == "zone":
        box = (f'background:{col(theme, d.get("zone_fill", "surface"))};border:1px solid {col(theme, d.get("group_border", "muted"))};')
    elif kind == "security":
        box = f'border:1.5px dashed {col(theme, d.get("security_group_border", "primary"))};'
        gc = col(theme, d.get("security_group_border", "primary"))
    else:
        box = f'border:1.5px dashed {col(theme, d.get("group_border", "muted"))};'
    out = (f'<div style="position:absolute;left:{g["x"]:.1f}px;top:{g["y"]:.1f}px;width:{g["w"]:.1f}px;height:{g["h"]:.1f}px;'
           f'box-sizing:border-box;border-radius:{radius}px;{box}"></div>')
    if g.get("label"):
        gs = d.get("group_size", 12)
        out += (f'<div style="position:absolute;left:{g["x"] + 10:.1f}px;top:{g["y"] + 3:.1f}px;font-size:{gs}px;'
                f'font-weight:700;color:{gc};line-height:1.2;">{esc(g["label"])}</div>')
    return out


def grid_diagram_html(slide, st, theme, kind: str, page: int, heading_font_css: str) -> str:
    """architecture / dataflow / lifecycle の図領域を HTML で描く（chrome 以外）。"""
    geo = dscale.layout_grid(slide, kind, st["diagram"], [], subject_prefix="")
    d = dscale.scaled_style(st["diagram"])         # 合成ブロックで拡大した図（scale_k > 1）は、文字・線のトークンも同じ倍率（S5a）
    parts = []
    # 行帯（lifecycle の lanes）。区切り線は帯 div の border で描く（swimlane と同じ。独立した 1px div に
    # すると check_layout がラベル文字との交差を「罫線」誤検出するため）。
    for i, rh in enumerate(geo["row_headers"]):
        bg = col(theme, d.get("row_band_b", "surface")) if rh["alt"] else col(theme, "background")
        bottom = f'border-bottom:1px solid {col(theme, d.get("row_border", "border"))};' if i == len(geo["row_headers"]) - 1 else ""
        parts.append(f'<div style="{pos({"x": rh["band_x"], "y": rh["y"], "w": rh["band_w"], "h": rh["h"]})}'
                     f'background:{bg};border-top:1px solid {col(theme, d.get("row_border", "border"))};{bottom}'
                     f'box-sizing:border-box;"></div>')
        parts.append(f'<div style="{pos({"x": rh["x"], "y": rh["y"], "w": rh["w"], "h": rh["h"]})}'
                     f'display:flex;align-items:center;justify-content:center;text-align:center;'
                     f'background:{col(theme, d.get("row_fill", "surface"))};border:1px solid {col(theme, d.get("row_border", "border"))};'
                     f'box-sizing:border-box;color:{col(theme, d.get("row_color", "text"))};font-size:{d.get("row_size", 13)}px;'
                     f'padding:2px;line-height:1.2;">{esc(rh["label"])}</div>')
    # 列見出し帯（dataflow の stages / col_headers）
    for ch in geo["col_headers"]:
        parts.append(f'<div style="{pos(ch)}display:flex;align-items:center;justify-content:center;'
                     f'background:{col(theme, d.get("header_fill", "highlight_fill"))};box-sizing:border-box;'
                     f'color:{col(theme, d.get("header_color", "text"))};font-weight:700;font-size:{d.get("header_size", 14)}px;'
                     f'border-left:2px solid {col(theme, "background")};">{esc(ch["label"])}</div>')
    for g in geo["groups"]:
        parts.append(_group_html(g, d, theme))
    parts.append(_edges_svg_html(geo["edges"], d, theme, f"s{page}", heading_font_css, layer="lines"))
    for nid, b in geo["nodes"].items():
        parts.append(_diag_node_html(b, geo["text"].get(nid, {}), d, theme, kind, heading_font_css))
    parts.append(_edges_svg_html(geo["edges"], d, theme, f"s{page}", heading_font_css, layer="labels"))
    if geo["legend"]:
        parts.append(_legend_html(geo["legend"], geo["legend_y"], d["x"] + 4, d, theme))
    return "".join(parts)


def sequence_html(slide, st, theme, page: int, heading_font_css: str) -> str:
    geo = dscale.layout_seq(slide, st["diagram"], [], subject_prefix="")
    d = dscale.scaled_style(st["diagram"])
    parts = []
    # segments（区間の薄い枠）
    for sg in geo["segments"]:
        parts.append(f'<div style="{pos(sg)}box-sizing:border-box;border:1px dashed {col(theme, d.get("segment_border", "muted"))};'
                     f'border-radius:{rtok(theme, "small", 6):g}px;"></div>')
    # lifelines
    svg = [f'<svg style="position:absolute;left:0;top:0;width:{CANVAS_W}px;height:{CANVAS_H}px;pointer-events:none;" '
           f'viewBox="0 0 {CANVAS_W} {CANVAS_H}">']
    llc = col(theme, d.get("lifeline_color", "muted"))
    for pid in geo["order"]:
        pb = geo["participants"].get(pid)
        if not pb:
            continue
        svg.append(f'<line x1="{pb["cx"]:.1f}" y1="{geo["lifeline_top"]:.1f}" x2="{pb["cx"]:.1f}" y2="{geo["lifeline_bottom"]:.1f}" '
                   f'stroke="{llc}" stroke-width="{d.get("lifeline_w", 1.5)}" stroke-dasharray="6,5"/>')
    svg.append("</svg>")
    parts.append("".join(svg))
    # 区間の見出しは生存線より上に描く（背景つきの札で生存線を隠す。線が見出しの文字を貫通しない）
    for sg in geo["segments"]:
        if sg.get("label"):
            ss = d.get("segment_size", 12)
            parts.append(f'<div style="position:absolute;left:{sg["x"] + 8:.1f}px;top:{sg["y"] - ss * 0.75:.1f}px;padding:0 6px;'
                         f'background:{col(theme, "background")};font-size:{ss}px;font-weight:700;'
                         f'color:{col(theme, d.get("segment_color", "muted"))};line-height:1.3;">{esc(sg["label"])}</div>')
    # activations
    for a in geo["activations"]:
        parts.append(f'<div style="{pos(a)}background:{col(theme, d.get("activation_fill", "highlight_fill"))};'
                     f'border:1.5px solid {col(theme, d.get("activation_border", "accent"))};border-radius:{rtok(theme, "tiny", 3):g}px;box-sizing:border-box;"></div>')
    # messages
    parts.append(_edges_svg_html(geo["messages"], d, theme, f"s{page}", heading_font_css))
    # participants
    fit = de.check_node_text(geo["participants"], d.get("node_size", 14), d.get("sub_size", 11), d.get("node_pad", 8), [],
                             icon_w=d.get("icon_size", 16) + 6)
    for pid, pb in geo["participants"].items():
        parts.append(_diag_node_html(dict(pb, shape="rect"), fit.get(pid, {}), d, theme, "sequence", heading_font_css))
    return "".join(parts)


# diagram_legend の自動生成用: 記号 → (ラベル, 説明) の既定辞書と、凡例に載せる順序。
DIAG_LEGEND_ICON = {
    "frontend": ("フロントエンド", "画面・UI（Web / モバイル）"),
    "backend": ("バックエンド", "API・アプリケーションサーバ"),
    "database": ("データベース", "DB・ストレージ・キャッシュ"),
    "cloud": ("クラウド", "マネージドサービス"),
    "security": ("セキュリティ", "認証・認可・境界防御"),
    "messagebus": ("メッセージ基盤", "キュー・イベントストリーム"),
    "external": ("外部システム", "自社外のサービス・利用者"),
    "generic": ("コンポーネント", "汎用の構成要素"),
}
DIAG_LEGEND_NODE_VARIANT = {
    "emphasis": ("主要ノード", "強調色＝主経路の中心"),
    "security": ("セキュア対象", "認証・境界防御の対象"),
    "dashed": ("任意・外部", "任意・将来・外部の要素"),
    "muted": ("参考", "背景・参考の要素"),
}
DIAG_LEGEND_KIND = {
    "start": ("開始", "フローの起点"),
    "active": ("進行中", "通常の状態"),
    "waiting": ("待機", "外部入力・承認待ち"),
    "decision": ("分岐", "条件による分岐"),
    "success": ("成功・完了", "正常終了"),
    "failure": ("失敗・中止", "異常終了"),
    "neutral": ("中立", "補助的な状態"),
    "external": ("外部", "外部要因の状態"),
}
DIAG_LEGEND_EDGE = {
    "default": ("実線矢印", "同期の呼び出し・主な流れ"),
    "emphasis": ("主要フロー", "太線＝最重要の経路"),
    "security": ("セキュア経路", "認証付き・境界をまたぐ通信"),
    "dashed": ("破線矢印", "非同期・任意・補助的な経路"),
    "return": ("戻り矢印", "応答・戻り値（開いた破線）"),
}
DIAG_LEGEND_TITLE = {
    "architecture": "システム構成図の記号（architecture）",
    "dataflow": "データフローの記号（dataflow）",
    "lifecycle": "ライフサイクルの記号（lifecycle）",
    "sequence": "シーケンス図の記号（sequence）",
}
_ICON_ORDER = ["frontend", "backend", "database", "cloud", "security", "messagebus", "external", "generic"]


# ---------------------------------------------------------------------------
# 矢羽根スケジュール（schedule）の見た目解決と HTML 描画。
# ジオメトリと診断は schedule_engine が担当し、PPTX 側（build_pptx 内の s_schedule）も
# 同じジオメトリと schedule_bar_visual() を使うので、HTML と PPTX で位置・配色が一致する。
# ---------------------------------------------------------------------------

def schedule_bar_visual(variant: str, c: dict) -> dict:
    """variant → 塗り・枠・文字色のトークン（style.chart の <variant>_fill / _border / _color）。"""
    defaults = {
        "main": ("primary", None, "on_primary"),
        "accent": ("accent", None, "on_primary"),
        "muted": ("muted", None, "on_primary"),
        "prep": ("highlight_fill", "accent", "primary"),
        "ongoing": ("background", "primary", "primary"),
        "tbd": ("background", "accent", "primary"),
    }
    fill, border, color = defaults.get(variant, defaults["main"])
    return {"fill": c.get(f"{variant}_fill", fill), "border": c.get(f"{variant}_border", border),
            "color": c.get(f"{variant}_color", color), "dashed": variant == "tbd"}


def _schedule_poly_svg(points, x, y, w, h, fill, stroke, dashed, stroke_w=1.5) -> str:
    pts = " ".join(f"{px - x:.2f},{py - y:.2f}" for px, py in points)
    st = f'stroke="{stroke}" stroke-width="{stroke_w}"' if stroke else 'stroke="none"'
    if stroke and dashed:
        st += ' stroke-dasharray="5 3"'
    return (f'<svg width="{w:.2f}" height="{h:.2f}" style="position:absolute;left:0;top:0;overflow:visible;">'
            f'<polygon points="{pts}" fill="{fill}" {st} stroke-linejoin="miter"/></svg>')


def schedule_html(slide, st, theme, heading_font_css: str) -> str:
    c = st["chart"]
    geo = se.layout_schedule(slide, c)
    rg = geo["region"]
    out = []

    def cc(key, default):
        return col(theme, c.get(key, default))

    grid = cc("grid_color", "border")
    strong_w = c.get("grid_strong_w", 2)

    def _sched_rowbg(item):
        """行の地の色（縞の行か通常の行か）。節目・矢羽根の外のラベルの座布団に使う。"""
        return cc("row_alt_fill", "on_primary_soft") if item.get("alt") else col(theme, "background")
    # 行の縞（見出し欄＋時間軸）。行境界は border-top（グループ境界は太線）で描き、
    # 1〜2px の細い要素を作らない（check_layout の rule 判定で文字との交差と誤認させないため）。
    hl = {round(h["y"], 2): h for h in geo["hlines"]}
    for r in geo["rows"]:
        bg = cc("row_alt_fill", "on_primary_soft") if r["alt"] else col(theme, "background")
        line = hl.get(round(r["y"], 2))
        bw = strong_w if line and line["strong"] else 1
        out.append(f'<div style="{pos({"x": r["x"], "y": r["y"], "w": rg["x"] + rg["w"] - r["x"], "h": r["h"]})}'
                   f'background:{bg};border-top:{bw}px solid {grid};box-sizing:border-box;"></div>')
    # 列の縦罫線（列幅の箱の左罫線。期間境界・両端は太線）
    if geo["rows"]:
        top = geo["columns"][0]["y"] if geo["columns"] else geo["rows"][0]["y"]
        bottom = geo["rows"][-1]["y"] + geo["rows"][-1]["h"]
        vl = geo["vlines"]
        for k in range(len(vl) - 1):
            lw = strong_w if vl[k]["strong"] else 1
            right = f"border-right:{strong_w}px solid {grid};" if k == len(vl) - 2 else ""
            out.append(f'<div style="{pos({"x": vl[k]["x"], "y": top, "w": vl[k + 1]["x"] - vl[k]["x"], "h": bottom - top})}'
                       f'border-left:{lw}px solid {grid};{right}box-sizing:border-box;"></div>')
        out.append(f'<div style="{pos({"x": rg["x"], "y": bottom - 1, "w": rg["w"], "h": strong_w + 1})}'
                   f'border-top:{strong_w}px solid {grid};box-sizing:border-box;"></div>')
    # 見出し（期間・列）
    for p in geo["periods"]:
        out.append(f'<div style="{pos(p)}display:flex;align-items:center;justify-content:center;'
                   f'background:{cc("period_fill", "primary")};color:{cc("period_color", "on_primary")};'
                   f'font-family:{esc(heading_font_css)};font-weight:700;font-size:{p["size"]}px;white-space:nowrap;'
                   f'border-right:2px solid {col(theme, "background")};box-sizing:border-box;">{esc(p["label"])}</div>')
    for k in geo["columns"]:
        out.append(f'<div style="{pos(k)}display:flex;align-items:center;justify-content:center;'
                   f'background:{cc("col_fill", "highlight_fill")};color:{cc("col_color", "text")};'
                   f'font-size:{k["size"]}px;white-space:nowrap;border-right:1px solid {col(theme, "background")};'
                   f'box-sizing:border-box;">{esc(k["label"])}</div>')
    # 左端のグループ帯（縦書き）
    for g in geo["groups"]:
        out.append(f'<div style="{pos(g)}display:flex;align-items:center;justify-content:center;'
                   f'background:{cc("group_fill", "primary")};border-top:2px solid {col(theme, "background")};'
                   f'box-sizing:border-box;"><span style="writing-mode:vertical-rl;text-orientation:mixed;'
                   f'color:{cc("group_color", "on_primary")};font-weight:700;font-size:{c.get("group_size", 13)}px;'
                   f'white-space:nowrap;">{esc(g["label"])}</span></div>')
    # 行見出し（label ＋ sub）
    pad = c.get("label_pad", 10)
    for r in geo["rows"]:
        sub = (f'<div style="font-size:{r["sub_size"]}px;color:{cc("sub_color", "muted")};white-space:nowrap;'
               f'line-height:1.3;">{esc(r["sub"])}</div>') if r["sub"] else ""
        out.append(f'<div style="{pos(r)}display:flex;flex-direction:column;justify-content:center;'
                   f'padding:0 {pad}px;box-sizing:border-box;">'
                   f'<div style="font-size:{r["size"]}px;color:{cc("label_color", "text")};white-space:nowrap;'
                   f'line-height:1.3;">{esc(r["label"])}</div>{sub}</div>')
    # 現在線（矢羽根より下のレイヤー。10px 幅の箱の中央に破線を描き、細い罫線要素にしない）
    if geo["today"]:
        t = geo["today"]
        tc = cc("today_color", "accent")
        out.append(f'<div style="{pos({"x": t["x"] - 5, "y": t["y1"], "w": 10, "h": t["y2"] - t["y1"]})}'
                   f'background:repeating-linear-gradient(to bottom,{tc} 0 5px,transparent 5px 9px);'
                   f'background-size:2px 100%;background-repeat:no-repeat;background-position:center top;"></div>')
    # 矢羽根
    for b in geo["bars"]:
        vis = schedule_bar_visual(b["variant"], c)
        stroke = col(theme, vis["border"]) if vis["border"] else None
        inner = _schedule_poly_svg(b["points"], b["x"], b["y"], b["w"], b["h"],
                                   col(theme, vis["fill"]), stroke, vis["dashed"])
        if b["label"] and b["label_pos"] not in ("after", "before"):
            inner += (f'<div style="position:absolute;left:{b["tx"] - b["x"]:.2f}px;top:0;width:{b["tw"]:.2f}px;'
                      f'height:{b["h"]:.2f}px;display:flex;align-items:center;justify-content:center;'
                      f'font-size:{b["size"]}px;font-weight:700;color:{cp.readable_on(col(theme, vis["color"]), col(theme, vis["fill"]))};'
                      f'white-space:nowrap;">{esc(b["label"])}</div>')
        out.append(f'<div style="{pos(b)}">{inner}</div>')
        if b["label"] and b["label_pos"] in ("after", "before"):
            # 矢羽根の外に出したラベルは、行の地の色の座布団を敷く（背後の月の縦線が文字を貫通しない）
            out.append(f'<div style="{pos({"x": b["lbl_x"], "y": b["y"], "w": b["lbl_w"], "h": b["h"]})}'
                       f'display:flex;align-items:center;justify-content:center;font-size:{b["size"]}px;font-weight:700;background:{_sched_rowbg(b)};'
                       f'color:{cc("label_color", "text")};white-space:nowrap;">{esc(b["label"])}</div>')
    # 節目（ひし形＋ラベル）
    for m in geo["milestones"]:
        d = m["d"]
        pts = [(m["cx"], m["cy"] - d / 2), (m["cx"] + d / 2, m["cy"]), (m["cx"], m["cy"] + d / 2), (m["cx"] - d / 2, m["cy"])]
        out.append(f'<div style="{pos({"x": m["cx"] - d / 2, "y": m["cy"] - d / 2, "w": d, "h": d})}">'
                   + _schedule_poly_svg(pts, m["cx"] - d / 2, m["cy"] - d / 2, d, d,
                                        cc("milestone_fill", "accent"), cc("milestone_border", "primary"), False, 1)
                   + '</div>')
        if m["label"]:
            out.append(f'<div style="{pos({"x": m["lx"] - 2, "y": m["ly"], "w": m["lw"] + 4, "h": m["lh"]})}'
                       f'text-align:center;font-size:{m["size"]}px;font-weight:700;line-height:{m["lh"]}px;background:{_sched_rowbg(m)};'
                       f'color:{cc("milestone_color", "text")};white-space:nowrap;">{esc(m["label"])}</div>')
    # 凡例と注記
    lg = geo["legend"]
    if lg:
        for it in lg["items"]:
            sx, sy, sw, sh = it["x"], it["y"], it["sym_w"], it["sym_h"]
            if it["kind"] == "bar":
                vis = schedule_bar_visual(it["variant"], c)
                g = se._bar_geometry(sx, sx + sw, sy, sh, "arrow", 7)
                out.append(f'<div style="{pos({"x": sx, "y": sy, "w": sw, "h": sh})}">'
                           + _schedule_poly_svg(g["points"], sx, sy, sw, sh, col(theme, vis["fill"]),
                                                col(theme, vis["border"]) if vis["border"] else None, vis["dashed"], 1.2)
                           + '</div>')
            elif it["kind"] == "milestone":
                pts = [(sx + 6, sy + 1), (sx + 12, sy + 7), (sx + 6, sy + 13), (sx, sy + 7)]
                out.append(f'<div style="{pos({"x": sx, "y": sy, "w": 12, "h": 14})}">'
                           + _schedule_poly_svg(pts, sx, sy, 12, 14, cc("milestone_fill", "accent"),
                                                cc("milestone_border", "primary"), False, 1) + '</div>')
            else:
                tc = cc("today_color", "accent")
                out.append(f'<div style="{pos({"x": sx, "y": sy - 2, "w": 12, "h": sh + 4})}'
                           f'background:repeating-linear-gradient(to bottom,{tc} 0 4px,transparent 4px 7px);'
                           f'background-size:2px 100%;background-repeat:no-repeat;background-position:center top;"></div>')
            out.append(f'<div style="{pos({"x": it["tx"], "y": sy - 2, "w": it["tw"], "h": sh + 4})}'
                       f'display:flex;align-items:center;font-size:{it["size"]}px;'
                       f'color:{cc("legend_color", "text")};white-space:nowrap;">{esc(it["label"])}</div>')
        if lg["note"]:
            out.append(f'<div style="{pos({"x": lg["note_x"], "y": lg["note_y"] - 2, "w": lg["note_w"], "h": lg["h"] + 4})}'
                       f'display:flex;align-items:center;font-size:{lg["note_size"]}px;'
                       f'color:{cc("note_color", "muted")};white-space:nowrap;">{esc(lg["note"])}</div>')
    return "".join(out)


_NODE_VARIANT_ORDER = ["emphasis", "security", "dashed", "muted"]
_KIND_ORDER = ["start", "active", "waiting", "decision", "success", "failure", "neutral", "external"]
_EDGE_ORDER = ["default", "emphasis", "security", "dashed", "return"]


def _edge_variant_of(e: dict) -> str:
    """エッジの実効 variant（swimlane 互換の style:"dashed" も dashed とみなす）。"""
    v = e.get("variant")
    if v:
        return v
    if e.get("style") == "dashed":
        return "dashed"
    return "default"


def auto_diagram_legend_items(slide: dict, t: str) -> list:
    """図解スライドの実内容（使われている type / variant / kind / edge variant）だけから
    diagram_legend の items（[sample, label, desc] の配列）を組み立てる。"""
    nodes = slide.get("nodes") or slide.get("states") or slide.get("participants") or []
    edges = (slide.get("edges") or slide.get("transitions")
             or slide.get("messages") or slide.get("flows") or [])
    items = []
    if t == "lifecycle":
        for k in _KIND_ORDER:
            if any((n.get("kind") or "active") == k for n in nodes):
                items.append([{"kind": k}, *DIAG_LEGEND_KIND[k]])
    else:
        for ty in _ICON_ORDER:
            if any((n.get("type") or "generic") == ty for n in nodes):
                items.append([{"icon": ty}, *DIAG_LEGEND_ICON[ty]])
        for v in _NODE_VARIANT_ORDER:
            if any(n.get("variant") == v for n in nodes):
                items.append([{"node": v}, *DIAG_LEGEND_NODE_VARIANT[v]])
    for v in _EDGE_ORDER:
        if any(_edge_variant_of(e) == v for e in edges):
            items.append([{"edge": v}, *DIAG_LEGEND_EDGE[v]])
    return items


def build_diagram_legend_slide(slide: dict, t: str) -> dict:
    """図解スライドの直前に挿入する diagram_legend スライドを生成する。"""
    leg = {"type": "diagram_legend",
           "title": slide.get("legend_title", DIAG_LEGEND_TITLE.get(t, "凡例"))}
    eyebrow = slide.get("legend_eyebrow")
    if eyebrow is None and slide.get("eyebrow"):
        eyebrow = slide["eyebrow"] + " — 凡例"
    if eyebrow:
        leg["eyebrow"] = eyebrow
    if slide.get("legend_lead"):
        leg["lead"] = slide["legend_lead"]
    leg["items"] = slide.get("legend_items") or auto_diagram_legend_items(slide, t)
    # 図本体と凡例で記号の見た目を揃えるため、アイコン関連の diagram トークンだけ引き継ぐ
    # （icon_style:"aws" のタイル色など。geometry 系は持ち込まない）。
    src_diag = (slide.get("style") or {}).get("diagram") or {}
    icon_keys = {k: v for k, v in src_diag.items()
                 if k in ("icon_style", "icon_tile_size", "icon_size", "icon_color") or k.startswith("icon_tile_")}
    if icon_keys:
        leg["style"] = {"diagram": icon_keys}
    return leg


def expand_slides(deck, layout):
    """ビルド前処理: agenda のあふれを複数ページに分割し、swimlane / 図解タイプの直前に凡例ページを挿入する。"""
    out = []
    for si, s in enumerate(deck.get("slides", [])):
        with slide_guard(f"{si + 1}枚目（type={s.get('type')}）", "展開"):
            t = s.get("type")
            if t == "swimlane" and s.get("legend", True):
                leg = {"type": "swimlane_legend",
                       "title": s.get("legend_title", "凡例（スイムレーン記号）"),
                       "eyebrow": s.get("legend_eyebrow", s.get("eyebrow"))}
                if "legend_items" in s:
                    leg["items"] = norm_legend_items(s["legend_items"])
                out.append(leg)
                out.append(s)
            elif t in DIAGRAM_TYPES and s.get("legend_page"):
                out.append(build_diagram_legend_slide(s, t))
                out.append(s)
            elif t == "agenda":
                items = s.get("items", [])
                st = resolve_style(layout, deck, s)
                b = st.get("body", {})
                pitch = b.get("row_h", 44) + b.get("gap", 10)
                R = max(1, int(b.get("h", 452) // pitch))
                cap = R * b.get("max_cols", 2)
                if len(items) > cap:
                    for p in range(0, len(items), cap):
                        ns = dict(s)
                        ns["items"] = items[p:p + cap]
                        ns["num_start"] = p
                        if p > 0:
                            ns["title"] = s.get("title", "") + "（続き）"
                        out.append(ns)
                else:
                    out.append(s)
            else:
                out.append(s)
    d = dict(deck); d["slides"] = out
    return d


# ---------------------------------------------------------------------------
# 文字あふれ推定（M-74）: title / lead / bullets 系 / table のオーバーフローを warn する
# ---------------------------------------------------------------------------

def _char_width_ratio(ch: str) -> float:
    """全角=1.0、半角=0.55（フォントを実測できないときの近似。ja_text.fallback_ratio と同じ）。"""
    return ja_text.fallback_ratio(ch)


def estimate_lines(text, size_px: float, width_px: float, font=None, bold: bool = False) -> int:
    """テキストが width_px の枠に折り返して何行になるかを見積もる。
    字幅はテーマのフォントファイルから実測し（ja_text）、英単語は途中で切らない・行頭禁則は
    前の行に残すという描画側の挙動に寄せて折り返す。Pillow かフォントが無い環境では
    全角=1.0 / 半角=0.55 の近似になる。font 未指定なら fonts.body で測る。"""
    return ja_text.estimate_lines(text, size_px, width_px, font, bold)


# ---------------------------------------------------------------------------
# 泣き別れ対策: 折り返した最終行が 1〜2 文字だけになる和文に、文節の切れ目で改行を入れる
# ---------------------------------------------------------------------------

# 1 段落のテキスト領域（領域名, 見出しフォントで測るか）
_BALANCE_TEXT_REGIONS = (("title", True), ("subtitle", False), ("lead", False),
                         ("punch", True), ("message", True), ("text", False))
# 箇条書きを持つタイプ（bullets を body 領域に描くもの）
_BALANCE_BULLET_TYPES = ("bullets", "closing", "image_text")


def _balance_items(items, region: dict):
    """bullets（文字列 or {text, children}）の各項目に balance を掛けた新しいリストを返す。"""
    if not isinstance(items, list) or not region:
        return items
    size = region.get("size", 16)
    width = max(10.0, region.get("w", 400) - region.get("indent", 30))
    child_size = region.get("child_size", max(10, size - 3))
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(ja_text.balance(it, size, width))
        elif isinstance(it, dict):
            nit = dict(it)
            if isinstance(nit.get("text"), str):
                nit["text"] = ja_text.balance(nit["text"], nit.get("size", size), width, bold=bool(nit.get("bold")))
            if isinstance(nit.get("children"), list):
                nit["children"] = [
                    ja_text.balance(c, child_size, width - 20) if isinstance(c, str)
                    else ({**c, "text": ja_text.balance(c["text"], c.get("size", child_size), width - 20)}
                          if isinstance(c, dict) and isinstance(c.get("text"), str) else c)
                    for c in nit["children"]]
            out.append(nit)
        else:
            out.append(it)
    return out


def apply_line_balance(deck: dict, layout: dict) -> dict:
    """タイトル・リード・箇条書きなどの泣き別れを、改行（\\n）を入れて防いだデッキを返す。
    HTML と PPTX の両方に同じ改行が入る。すでに改行を書いてある文字列は触らない。
    デッキ全体で止めるなら meta.line_balance: false、スライド単位なら line_balance: false。"""
    if deck.get("meta", {}).get("line_balance") is False:
        return deck
    slides = []
    for si, slide in enumerate(deck.get("slides", [])):
        with slide_guard(f"{si + 1}枚目（type={slide.get('type')}）", "文字組みの調整"):
            t = slide.get("type")
            if slide.get("line_balance") is False or t not in layout.get("types", {}) or t == "canvas":
                slides.append(slide)
                continue
            st = resolve_style(layout, deck, slide)
            ns = dict(slide)
            # variant（表紙・章扉などの主役のページ）は大きな文字なので、改行を語の途中ではなく文節の切れ目に置く（何も指定しなければ従来どおり）
            # 背景つきのスライドと title / section / quote / statement の大きな文（36px 以上）も同じ（背景を指定すると variant が付かないことがある）
            big_phrase = (hero.variant_of(layout, deck, slide) is not None or bool(slide.get("background")) or t in ("title", "section", "quote", "statement"))
            for key, heading in _BALANCE_TEXT_REGIONS:
                r = st.get(key)
                if key == "text" and t != "quote":
                    continue                # "text" は quote の引用文だけ（ほかのタイプの text は別の領域・ブロックが扱う）
                if isinstance(ns.get(key), str) and isinstance(r, dict) and r.get("w") and r.get("size"):
                    font = ja_text.heading_fonts() if heading else None
                    tail = ja_text.tail_min(r["size"])        # 大きな文字ほど、最終行に残す最低限の文字数を増やす
                    if big_phrase and r["size"] >= 36:
                        pw = ja_text.phrase_wrap(ns[key], r["size"], r["w"], font=font, bold=bool(r.get("bold")), min_tail=max(5, tail))
                        if pw != ns[key]:
                            ns[key] = pw
                            continue
                    ns[key] = ja_text.balance(ns[key], r["size"], r["w"], font=font, bold=bool(r.get("bold")), min_tail=tail)
            if t in _BALANCE_BULLET_TYPES and isinstance(ns.get("bullets"), list):
                ns["bullets"] = _balance_items(ns["bullets"], st.get("body"))
            elif t == "two_column":
                for side in ("left", "right"):
                    box, colc = st.get(side), ns.get(side)
                    if isinstance(box, dict) and isinstance(colc, dict) and isinstance(colc.get("bullets"), list):
                        inner = dict(st.get("col_body", {}))
                        inner["w"] = box.get("w", 400) - 2 * box.get("pad", 0)
                        ns[side] = {**colc, "bullets": _balance_items(colc["bullets"], inner)}
            elif t == "cards" and isinstance(ns.get("cards"), list) and isinstance(st.get("grid"), dict):
                # カードの見出し・本文・項目: 各カードの幅・文字サイズで、最終行に 1〜2 文字だけ残る泣き別れを防ぐ
                g = st["grid"]
                geo = pe.cards_cells(len(ns["cards"]), ns.get("columns"), g, hero.card_spans(ns))
                pad = g.get("pad", 18)
                newc = []
                for k, c in enumerate(ns["cards"]):
                    if not isinstance(c, dict):
                        newc.append(c)
                        continue
                    w_ = max(geo["cells"][k][2] - 2 * pad, 10)
                    g = hero.emph_grid(st["grid"], hero.card_emphasis(c))
                    nc = dict(c)
                    if isinstance(nc.get("heading"), str):
                        hsz, hw = g.get("heading_size", 19), w_ - autofit.card_icon_reserve(nc, g)
                        pw = (ja_text.phrase_wrap(nc["heading"], hsz, hw, font=ja_text.heading_fonts(), bold=True, min_tail=max(4, ja_text.tail_min(hsz)))
                              if hsz >= CARD_PHRASE_MIN_SIZE else nc["heading"])        # 大きな文字（20px 以上）は文節の切れ目で折る（S4）
                        nc["heading"] = pw if pw != nc["heading"] else ja_text.balance(nc["heading"], hsz, hw, font=ja_text.heading_fonts(), bold=True)
                    if isinstance(nc.get("body"), str):
                        bsz = g.get("body_size", 15)
                        pw = (ja_text.phrase_wrap(nc["body"], bsz, w_, min_tail=max(4, ja_text.tail_min(bsz))) if bsz >= CARD_PHRASE_MIN_SIZE else nc["body"])
                        nc["body"] = pw if pw != nc["body"] else ja_text.balance(nc["body"], bsz, w_)
                    if isinstance(nc.get("items"), list):
                        nc["items"] = _balance_items(nc["items"], {"size": g.get("item_size", 14), "w": w_, "indent": autofit.CARD_ITEM_INDENT, "child_size": 12})
                    newc.append(nc)
                ns["cards"] = newc
            elif t == "composite" and isinstance(ns.get("blocks"), list):
                # 合成スライド: bullets のブロックは、そのブロックの本文の幅・文字サイズで泣き別れを防ぐ
                nb = list(ns["blocks"])
                for rb in (st.get("_composite") or {}).get("blocks", []):
                    blk = nb[rb["index"]]
                    if rb["type"] == "bullets" and rb["st"] and isinstance(blk.get("bullets"), list):
                        nb[rb["index"]] = {**blk, "bullets": _balance_items(blk["bullets"], rb["st"].get("body"))}
                    elif rb["type"] == "callout" and rb.get("fit") and isinstance(blk.get("text"), str):
                        # 強調の一文: 最終行に 3 文字以下（「6 割」など）だけ残さない（大きく見せる文なので、短い切れ端を許さない）
                        nb[rb["index"]] = {**blk, "text": ja_text.balance(blk["text"], rb["fit"]["size"], rb["fit"]["tw"],
                                                                         font=ja_text.heading_fonts(), bold=True, min_tail=4)}
                    elif rb["type"] == "text" and rb.get("fit") and isinstance(blk.get("paragraphs"), list):
                        w_ = rb["geo"]["content"][2]
                        nb[rb["index"]] = {**blk, "paragraphs": [ja_text.balance(p_, rb["fit"]["size"], w_) if isinstance(p_, str) else p_
                                                                  for p_ in blk["paragraphs"]]}
                ns["blocks"] = nb
            slides.append(ns)
    d = dict(deck)
    d["slides"] = slides
    return d


# ---------------------------------------------------------------------------
# 語の途中で折れる文を、文節の切れ目で折る（S5b。tools/wrap_fix.py。値は layout の common.wrap）
# ---------------------------------------------------------------------------

# 利用者が文字の大きさ・幅を書いた領域は、手で調整した折り返しなので触らない
_WRAP_USER_KEYS = frozenset({"size", "w", "heading_size", "body_size", "item_size", "label_size", "child_size", "text_size",
                             "cell_size", "header_size", "col_widths"})
# 1 段落のテキスト領域（領域名, 見出しフォントで測るか）。apply_line_balance の領域に、副文（support / attribution）を足したもの
_WRAP_TEXT_REGIONS = _BALANCE_TEXT_REGIONS + (("support", False), ("attribution", False))


def _wrap_user(ex: dict, region: str) -> bool:
    return bool(ex.get(region, ()) and set(ex[region]) & _WRAP_USER_KEYS)


class _WrapRoom:
    """箱の高さの余り（px）。語の途中の折れを直して行が増えるとき、余りの中に収まる行数だけ許す（収まらないなら増やさない）。"""

    def __init__(self, px=0.0):
        self.px = max(0.0, float(px or 0.0))

    def fix(self, text, size, width, cfg, lh=1.4, font=None, bold=False, min_tail=4):
        """wrap_fix.fix に、余りから決めた行数の増加を許して掛け、増えた行ぶんの高さを余りから引く。"""
        if not isinstance(text, str):
            return text
        lines = max(1.0, size * lh)
        out = wrap_fix.fix(text, size, width, cfg, font=font, bold=bold, min_tail=min_tail, extra=int(self.px // lines))
        if out != text:
            grown = wrap_fix.line_count(out, size, width, font, bold) - wrap_fix.line_count(text, size, width, font, bold)
            self.px -= max(0, grown) * lines
        return out


def _wrap_items(items, region: dict, cfg: dict, room=None):
    """bullets（文字列 or {text, children}）の各項目に wrap_fix.fix を掛けた新しいリスト（autofit.bullets_height と同じ幅・大きさ）。
    room（_WrapRoom）が無ければ行数を増やさない。"""
    if not isinstance(items, list) or not region:
        return items
    room = room or _WrapRoom(0)
    size = region.get("size", 16)
    lh = region.get("line_height", 1.4)
    indent = region.get("indent", 30)
    width = max(10.0, region.get("w", 400) - indent)
    child_size = region.get("child_size", max(10, size - 3))
    cw = max(10.0, width - (indent - 6))
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(room.fix(it, size, width, cfg, lh))
        elif isinstance(it, dict):
            nit = dict(it)
            if isinstance(nit.get("text"), str):
                nit["text"] = room.fix(nit["text"], nit.get("size", size), width, cfg, lh, bold=bool(nit.get("bold")))
            if isinstance(nit.get("children"), list):
                nit["children"] = [
                    room.fix(c, child_size, cw, cfg, lh) if isinstance(c, str)
                    else ({**c, "text": room.fix(c["text"], c.get("size", child_size), cw, cfg, lh)}
                          if isinstance(c, dict) and isinstance(c.get("text"), str) else c)
                    for c in nit["children"]]
            out.append(nit)
        else:
            out.append(it)
    return out


WRAP_TABLE_MAX_ROWS = autofit.TABLE_SEARCH_MAX_ROWS       # これより行の多い表は、文節の折り返しの探索を省く（時間がかかる。警告は従来どおり出る）


def _wrap_table(ns: dict, tr: dict, cfg: dict) -> dict:
    """表のセルの、語の途中で折れる文に文節の切れ目の改行を入れる（HTML は <br>、PPTX はセル内の改行）。
    列幅（px。自動フィットか利用者が決めたもの）が分かるときだけ。行が増えると行の高さが変わるので、行数は増やさない。
    列幅は改行を入れる前の文で決まる（resolve_style が _wrap_src の元の文で自動フィットする）ので、改行を入れても動かない。
    URL のセル・数字だけのセル・利用者が cell_size / header_size / col_widths を書いた表は触らない。"""
    widths = tr.get("col_widths")
    if len(ns.get("rows") or ()) > WRAP_TABLE_MAX_ROWS:
        return ns                                       # 行の多い表は探索に時間がかかるうえ、1 行ずつの折れは目立たない
    if not (isinstance(widths, list) and widths and all(isinstance(w, (int, float)) and w > 0 for w in widths)
            and isinstance(tr.get("w"), (int, float)) and tr.get("cell_size")):
        return ns
    total = float(sum(widths))
    px = [w / total * float(tr["w"]) - 2 * tr.get("pad_x", 16) for w in widths]
    ns = dict(ns)
    cols = ns.get("columns")
    if isinstance(cols, list) and tr.get("header_size"):
        ns["columns"] = [wrap_fix.fix(c, tr["header_size"], px[j], cfg, bold=True) if isinstance(c, str) and j < len(px) else c
                         for j, c in enumerate(cols)]
    emph = set(ns.get("_row_emphasis") or [])
    rows = []
    for i, row in enumerate(ns["rows"]):
        if not isinstance(row, list):
            rows.append(row)
            continue
        strong_row = (bool(ns.get("total_row")) and i == len(ns["rows"]) - 1) or i in emph
        out = []
        for j, cell in enumerate(row):
            text, url = table_cell_parts(cell)
            if j >= len(px) or url or not text or isinstance(cell, bool):
                out.append(cell)
                continue
            bold = strong_row or (bool(ns.get("row_header")) and j == 0) or (isinstance(cell, dict) and bool(cell.get("tone")))
            new = wrap_fix.fix(text, tr["cell_size"], px[j], cfg, bold=bold)
            if new == text:
                out.append(cell)
            elif isinstance(cell, dict):
                out.append({**cell, "text": new})
            else:
                out.append(new)
        rows.append(out)
    ns["rows"] = rows
    return ns


def _wrap_fix_typed(t: str, ns: dict, st: dict, cfg: dict, ex: dict) -> dict:
    """1 つのスライド（またはブロックを既存タイプのスライドとして見たもの）の、語の途中で折れる文を直した新しい辞書。
    行が増える直し方は、箱の高さの余りに収まるときだけ使う（あふれ・縮小を新しく作らない）。"""
    ns = dict(ns)
    for key, heading in _WRAP_TEXT_REGIONS:
        r = st.get(key)
        if key == "text" and t != "quote":
            continue
        if isinstance(ns.get(key), str) and isinstance(r, dict) and r.get("w") and r.get("size") and not _wrap_user(ex, key):
            font = ja_text.heading_fonts() if heading else None
            lh = r.get("line_height", 1.4)
            w = r["w"] / shp.width_factor(r)          # 字間（tracking）を入れた文字は 1 字が広がる。自動フィットと同じ見積もりの幅で測る
            room = _WrapRoom((r.get("h") or 0) - ja_text.estimate_lines(ns[key], r["size"], w, font, shp.is_bold(r)) * r["size"] * lh)
            ns[key] = room.fix(ns[key], r["size"], w, cfg, lh, font=font, bold=shp.is_bold(r), min_tail=max(4, ja_text.tail_min(r["size"])))
    if t in _BALANCE_BULLET_TYPES and isinstance(ns.get("bullets"), list) and isinstance(st.get("body"), dict) and not _wrap_user(ex, "body"):
        ns["bullets"] = _wrap_items(ns["bullets"], st["body"], cfg, _WrapRoom(st["body"].get("h", 0) - autofit.bullets_height(ns["bullets"], st["body"])))
    elif t == "two_column":
        for side in ("left", "right"):
            box, colc = st.get(side), ns.get(side)
            if isinstance(box, dict) and isinstance(colc, dict) and isinstance(colc.get("bullets"), list) and not _wrap_user(ex, "col_body"):
                inner = dict(st.get("col_body", {}))
                inner["w"] = box.get("w", 400) - 2 * box.get("pad", 0)
                head = (st.get("col_heading", {}).get("size", 22) * 1.5 + 16) if colc.get("heading") else 0
                room = _WrapRoom(box.get("h", 0) - 2 * box.get("pad", 0) - head - autofit.bullets_height(colc["bullets"], inner))
                ns[side] = {**colc, "bullets": _wrap_items(colc["bullets"], inner, cfg, room)}
    elif t == "cards" and isinstance(ns.get("cards"), list) and isinstance(st.get("grid"), dict):
        g0 = st["grid"]
        geo = pe.cards_cells(len(ns["cards"]), ns.get("columns"), g0, hero.card_spans(ns))
        pad = g0.get("pad", 18)
        user = ex.get("grid", set())
        newc = []
        for k, c in enumerate(ns["cards"]):
            if not isinstance(c, dict):
                newc.append(c)
                continue
            w_ = max(geo["cells"][k][2] - 2 * pad, 10)
            g = hero.emph_grid(g0, hero.card_emphasis(c))
            nc = dict(c)
            room = _WrapRoom(geo["cells"][k][3] - autofit.cards_need(c, g, w_, pad))
            if isinstance(nc.get("heading"), str) and "heading_size" not in user:
                hsz = g.get("heading_size", 19)
                nc["heading"] = room.fix(nc["heading"], hsz, w_ - autofit.card_icon_reserve(nc, g), cfg, autofit.CARD_HEAD_LH,
                                         font=ja_text.heading_fonts(), bold=True, min_tail=max(4, ja_text.tail_min(hsz)))
            if isinstance(nc.get("body"), str) and "body_size" not in user:
                bsz = g.get("body_size", 15)
                nc["body"] = room.fix(nc["body"], bsz, w_, cfg, autofit.CARD_BODY_LH, min_tail=max(4, ja_text.tail_min(bsz)))
            if isinstance(nc.get("items"), list) and "item_size" not in user:
                nc["items"] = _wrap_items(nc["items"], {"size": g.get("item_size", 14), "w": w_, "indent": autofit.CARD_ITEM_INDENT, "child_size": 12}, cfg, room)
            newc.append(nc)
        ns["cards"] = newc
    elif t == "table" and isinstance(ns.get("rows"), list) and isinstance(st.get("table"), dict) and not _wrap_user(ex, "table"):
        ns = _wrap_table(ns, st["table"], cfg)
    elif t == "kpi":
        # kpi のラベル・注記は描くとき（dataviz_engine.layout_kpi）に改行を入れる。入れてよいかの判定（止め方・利用者が書いた大きさ）をここでそろえる
        if not (set(ex.get("body", ())) & (_WRAP_USER_KEYS | {"note_size", "value_size"})):
            ns["_wrap_cfg"] = dict(cfg)
    elif t == "steps" and isinstance(ns.get("steps"), list) and isinstance(st.get("body"), dict) and not _wrap_user(ex, "body"):
        b = st["body"]
        n = max(1, len(ns["steps"]))
        card_w = (b["w"] - (n - 1) * b.get("gap", 20)) / n
        inner = card_w - 2 * b.get("pad", 16)
        proto = autofit.steps_item_params(b, inner)
        avail = b.get("h", 0) - b.get("header_h", 60) - 2 * b.get("pad", 16) - 12
        newc = []
        for stp in ns["steps"]:
            if not isinstance(stp, dict):
                newc.append(stp)
                continue
            nst = dict(stp)
            if isinstance(nst.get("label"), str):
                nst["label"] = wrap_fix.fix(nst["label"], b.get("label_size", 18), inner, cfg, font=ja_text.heading_fonts(), bold=True)
            if isinstance(nst.get("items"), list):
                nst["items"] = _wrap_items(nst["items"], proto, cfg, _WrapRoom(avail - autofit.bullets_height(nst["items"], proto)))
            newc.append(nst)
        ns["steps"] = newc
    return ns


def _attach_src(old: dict, new: dict) -> dict:
    """改行を入れて変わったキーについて、入れる前の内容を new["_wrap_src"] に持たせる（大きさを決める自動フィットはそちらを見る）。"""
    changed = {k: old[k] for k, v in new.items() if k != "blocks" and k in old and not k.startswith("_") and v != old[k]}
    if changed:
        new["_wrap_src"] = WrapSrc(changed)
    return new


def apply_wrap_fix(deck: dict, layout: dict) -> dict:
    """自然な折り返しだと語の途中で折れる段落に、文節の切れ目の改行（\\n）を入れたデッキを返す（apply_line_balance のあとに掛ける。
    すでに \\n がある文（line_balance・phrase_wrap が入れたものを含む）・利用者が大きさ・幅を書いた領域は触らない）。
    順序は「大きさを決める → 決まった大きさと幅で改行を入れる」: 改行を入れたスライド・ブロックは `_wrap_src` に入れる前の内容を持ち、
    resolve_style / resolve_block はそちらで大きさを決める（改行の有無で自動フィットの結果が変わらない）。
    止め方: meta.layout_overrides.common.wrap.enabled / スライドの style.wrap.enabled を false、meta.line_balance / slide.line_balance を false、
    meta.autofit / slide.autofit を false（自動で整えない約束。kpi も含む）。"""
    if deck.get("meta", {}).get("line_balance") is False:
        return deck
    slides = []
    for si, slide in enumerate(deck.get("slides", [])):
        with slide_guard(f"{si + 1}枚目（type={slide.get('type')}）", "文字組みの調整（語の途中の折れ）"):
            t = slide.get("type")
            if slide.get("line_balance") is False or t not in layout.get("types", {}) or t == "canvas" or not autofit.autofit_on(deck, slide):
                slides.append(slide)
                continue
            st = resolve_style(layout, deck, slide)
            cfg = wrap_fix.config(st)
            if not cfg["enabled"]:
                slides.append(slide)
                continue
            ex = autofit.explicit_props(deck, slide)
            ns = _wrap_fix_typed(t, slide, st, cfg, ex)
            if t in COMPOSITE_TYPES and isinstance(ns.get("blocks"), list):
                nb = list(ns["blocks"])
                for rb in (st.get("_composite") or {}).get("blocks", []):
                    blk = nb[rb["index"]]
                    if not isinstance(blk, dict) or isinstance(blk.get("style"), dict) and _wrap_user(blk["style"], "body"):
                        continue
                    new = None
                    if rb["type"] == "callout" and rb.get("fit") and isinstance(blk.get("text"), str):
                        new = {**blk, "text": wrap_fix.fix(blk["text"], rb["fit"]["size"], rb["fit"]["tw"], cfg,
                                                           font=ja_text.heading_fonts(), bold=True, min_tail=4)}
                    elif rb["type"] == "text" and rb.get("fit") and isinstance(blk.get("paragraphs"), list):
                        w_ = rb["geo"]["content"][2]
                        new = {**blk, "paragraphs": [wrap_fix.fix(p_, rb["fit"]["size"], w_, cfg) if isinstance(p_, str) else p_
                                                      for p_ in blk["paragraphs"]]}
                    elif rb.get("st") and rb["type"] in ("bullets", "steps", "cards", "kpi"):
                        new = _wrap_fix_typed(rb["type"], blk, rb["st"], cfg, autofit.explicit_props(deck, {**blk, "type": rb["type"]}))
                    if new is not None:
                        nb[rb["index"]] = _attach_src(blk, new)
                ns["blocks"] = nb
            slides.append(_attach_src(slide, ns))
    d = dict(deck)
    d["slides"] = slides
    return d


def estimate_bullets_height(items, r: dict) -> float:
    """bullets 領域（親＋子）が実際に描画されたときのおおよその高さを推定する（px。末尾の間隔を含む）。
    items は norm_items() 前後どちらの形式でも受け付ける。自動フィットと同じ見積もり（autofit.bullets_height）。"""
    return autofit.bullets_height(items, r)


DEFAULT_STATUS_LEGEND = [
    {"key": "red", "color": "#FF0000", "label": "遅延(マイルストーンの日程再調整が必要)"},
    {"key": "yellow", "color": "#FFC000", "label": "遅延(マイルストーンの日程再調整は不要。リカバリ予定有)"},
    {"key": "green", "color": "#00B050", "label": "予定通りまたは前倒し"},
]
STATUS_LEGEND_TITLE = "進捗状況\nステータス\n定義"


def status_legend(slide: dict) -> list:
    """status_table の凡例。slide.legend 未指定なら既定の信号3色、false なら非表示（空配列）。"""
    legend = slide.get("legend", DEFAULT_STATUS_LEGEND)
    return legend if isinstance(legend, list) else []


def status_color(slide: dict, status) -> str:
    """行の status（凡例 key、テーマトークン、#hex のいずれか）を色指定に解決する。"""
    for it in status_legend(slide) or DEFAULT_STATUS_LEGEND:
        if it.get("key") == status:
            return it.get("color", "text")
    return status or "text"


def flatten_status_items(items, level: int = 0) -> list:
    """status_table のセル内容（文字列 or {text, children} の入れ子）を (level, text) の平坦な列にする。"""
    return autofit.flatten_status_items(items, level)


def status_table_geometry(slide: dict, st: dict) -> dict:
    """status_table の列・行の座標を計算する（HTML/PPTX 共通）。
    行の高さはセル内容の見積もり高さを基準にし、fill_height なら余白を各行へ比例配分して表の高さを埋める。"""
    tr = st["table"]
    ws, rows = autofit.status_table_rows(slide, tr)
    xs, x = [], tr["x"]
    for w in ws:
        xs.append(x)
        x += w
    avail_h = tr["h"] - tr["header_h"]
    total_need = sum(r["need"] for r in rows) or 1
    scale = avail_h / total_need if tr.get("fill_height", True) and total_need < avail_h else 1.0
    y = tr["y"] + tr["header_h"]
    for r in rows:
        r["y"], r["h"] = y, r["need"] * scale
        y += r["h"]
    return {"xs": xs, "ws": ws, "rows": rows, "header_y": tr["y"], "bottom": y,
            "overflow": max(0.0, total_need - avail_h)}


def steps_card_height(b: dict, steps, card_w: float) -> float:
    """steps のカード高さ。既定（fit="content"）では最も長いカードの内容に合わせて縮め、
    短い内容で下半分が空くのを防ぐ。fit="fill" で従来どおり body.h いっぱいに描く。
    下限 min_h（既定 260px）、上限 body.h。HTML/PPTX 共通。"""
    if b.get("fit", "content") != "content" or not steps:
        return b["h"]
    header_h = b.get("header_h", 60); pad = b.get("pad", 16)
    proto = autofit.steps_item_params(b, card_w - 2*pad)
    est = max(estimate_bullets_height(norm_items(st.get("items", [])), proto) for st in steps)
    return max(min(b["h"], header_h + 2*pad + est + 12), min(b["h"], b.get("min_h", 260)))


def _matrix_content_layout(body_text, g: dict, cw: float, ch: float, pad: float, valign: str) -> dict:
    """matrix の1象限（heading + body の縦積み）の各要素の y オフセット（象限上端からの相対値）
    と body の高さを計算する（HTML/PPTX 共通）。valign:middle のときは heading を含めた
    コンテンツ全体の実高さを見積もり、その全体を象限の中央に配置できるよう heading の y から
    計算し直す（heading だけを上端固定にして body だけを残り高さでセンタリングすると、
    見出し直下に不自然な空白ができるため）。valign:top（既定）は従来どおり heading 上端固定。"""
    body_w = cw - 2 * pad
    head_h = 26
    head_gap = 4
    body_size = g.get("body_size", 14)
    if valign == "middle":
        lines = estimate_lines(body_text, body_size, body_w) if body_text else 0
        body_h = lines * body_size * 1.4
        content_h = head_h + (head_gap + body_h if body_text else 0)
        head_y = pad + max(0.0, (ch - 2 * pad - content_h) / 2)
    else:
        head_y = pad
        body_h = ch - 2 * pad - (head_h + head_gap)
    body_y = head_y + head_h + head_gap
    return {"head_h": head_h, "head_y": head_y, "body_y": body_y, "body_h": body_h}


def _cards_content_layout(card: dict, g: dict, cw: float, chh: float, pad: float, valign: str) -> dict:
    """cards の1枚（heading + body + items の縦積み）の各要素の y オフセット（カード上端からの
    相対値）と items の高さを計算する（HTML/PPTX 共通）。各段の高さは内容から決める
    （autofit.cards_content。以前は本文の高さが固定 44px で、1 行の本文でも余白が出て、3 行以上は重なった）。
    valign:middle のときは heading を含めたコンテンツ全体（実際に描画される段だけ）の実高さを見積もり、
    その全体をカードの中央に配置できるよう heading の y から計算し直す。valign:top（既定）は heading 上端固定。"""
    body_w = cw - 2 * pad
    has_body = bool(card.get("body"))
    has_items = bool(card.get("items"))
    c = autofit.cards_content(card, g, body_w)
    head_h = c["head_h"]
    head_gap = autofit.CARD_HEAD_GAP
    body_h = c["body_h"]
    body_gap = autofit.CARD_BODY_GAP
    items_h = c["items_h"]
    if valign == "middle":
        content_h = head_h
        if has_body:
            content_h += head_gap + body_h
        if has_items:
            content_h += body_gap + items_h
        head_y = pad + max(0.0, (chh - 2 * pad - content_h) / 2)
    else:
        head_y = pad
    yy = head_y + head_h + head_gap
    body_y = None
    if has_body:
        body_y = yy
        yy += body_h + body_gap
    items_y = None
    if has_items:
        items_y = yy
        if valign != "middle":
            items_h = chh - yy - pad
    return {"head_h": head_h, "head_y": head_y, "body_h": body_h, "body_y": body_y,
            "items_h": items_h, "items_y": items_y}


def _two_column_side_layout(colc: dict, box: dict, hd: dict, body_style: dict, valign: str) -> dict:
    """two_column の1サイド（heading + bullets の縦積み）の各要素の y オフセット（箱上端からの
    相対値）と bullets 領域の高さを計算する（PPTX 用。HTML 側は flexbox で同じ効果を実際の
    描画高さから得られるためこの見積もりを使わない）。style.left.valign / style.right.valign
    が "middle" のときは heading を含めたコンテンツ全体を箱の中央に配置できるよう heading の y
    から計算し直す。既定の "top" は従来どおり heading 上端固定。"""
    pad = box.get("pad", 0)
    inner_w = box.get("w", 400) - 2 * pad
    has_heading = bool(colc.get("heading"))
    head_h = (hd.get("size", 22) * 1.4) if has_heading else 0.0
    head_gap = hd.get("gap_below", 12) if has_heading else 0.0
    probe = dict(body_style)
    probe["w"] = inner_w
    body_h = estimate_bullets_height(colc.get("bullets"), probe) if colc.get("bullets") else 0.0
    if valign == "middle":
        content_h = head_h + head_gap + body_h
        avail_h = box.get("h", 300) - 2 * pad
        head_y = pad + max(0.0, (avail_h - content_h) / 2)
    else:
        head_y = pad
    body_y = head_y + head_h + head_gap
    if valign == "middle":
        final_body_h = body_h
    else:
        final_body_h = box.get("h", 300) - pad - body_y
    return {"head_y": head_y, "head_h": head_h, "body_y": body_y, "body_h": final_body_h}


def closing_message_style(st: dict, slide: dict) -> dict:
    """closing.message の描画スタイルを解決する（M-38: HTML/PPTX 共通の計算式）。
    message.follow_body が真で、かつスライドの style.message.y が明示されていなければ、
    message.y を「body の実描画高さの直後 + follow_gap」に自動配置する
    （上限は layout 既定の message.y、下限は min_y）。follow_body が無い、または
    style.message.y が明示されている場合は st["message"] をそのまま返す。"""
    msg = dict(st["message"])
    style_msg = (slide.get("style") or {}).get("message", {})
    if msg.get("follow_body") and "y" not in style_msg:
        body = st["body"]
        bullets = slide.get("bullets") or []
        body_bottom = body["y"] + (estimate_bullets_height(bullets, body) if bullets else 0)
        max_y = msg["y"]
        min_y = msg.get("min_y", max_y)
        msg["y"] = min(max_y, max(min_y, body_bottom + msg.get("follow_gap", 48)))
    return msg


def _check_overflow(slide: dict, st: dict, i: int, t: str):
    """文字・箱のあふれの警告。自動フィット（autofit）が文字量から見積もった結果（収まったか・縮めたか・
    最小サイズでも収まらないか）を、st["_fit"]["issues"] からそのまま warn / note にする。
    以前はタイプごとに「項目数×固定の高さ」で見積もり、文字量を見ずに警告していた（A2-05）。
    新しいタイプの警告は autofit.fitter で issue を出せば、ここを足さずに出る。"""
    label = f"{i + 1}枚目（type={t}）"
    for level, _code, text in (st.get("_fit") or {}).get("issues", []):
        (warn if level == "warn" else note)(text.replace("{label}", label))


# ---------------------------------------------------------------------------
# 色指定の検証（M-68 等）: テーマトークン名 or #RRGGBB/#RGB のみを許可する
# ---------------------------------------------------------------------------

_COLOR_KEY_RE = re.compile(r"(color|fill|fills|series_colors)$")   # series_colors: chart の系列色（色の配列）


def _color_issue(theme, value, path: str, i: int, t: str):
    if not isinstance(value, str):
        return None
    if is_color_value(theme, value):
        return None
    return (f"不明な色指定 '{value}'（{i + 1}枚目 type={t} の {path}）。"
            f"テーマトークン名か #RRGGBB 形式のhexを指定してください")


def _walk_colors(obj, path: str, theme, i: int, t: str, issues: list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            npath = f"{path}.{k}" if path else k
            if _COLOR_KEY_RE.search(k):
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        msg = _color_issue(theme, vv, f"{npath}[{kk}]", i, t)
                        if msg:
                            issues.append(msg)
                elif isinstance(v, list):
                    for idx, vv in enumerate(v):
                        msg = _color_issue(theme, vv, f"{npath}[{idx}]", i, t)
                        if msg:
                            issues.append(msg)
                else:
                    msg = _color_issue(theme, v, npath, i, t)
                    if msg:
                        issues.append(msg)
            elif isinstance(v, (dict, list)) and k != "_composite":
                _walk_colors(v, npath, theme, i, t, issues)
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                _walk_colors(v, f"{path}[{idx}]", theme, i, t, issues)


# ---------------------------------------------------------------------------
# 画像パスの検証（X-1 パストラバーサル対策 / M-72, M-96 存在チェック）
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".tiff"}


def _validate_image_path(slide: dict, i: int, t: str, deck_dir: Path):
    rel = slide.get("path")
    if not rel:
        fail(f"{i + 1}枚目（type={t}）: path が指定されていません")
    try:
        base = Path(deck_dir).resolve()
        resolved = (base / rel).resolve()
    except (OSError, ValueError):
        fail(f"{i + 1}枚目（type={t}）: path '{rel}' を解決できません")
    if resolved != base and not resolved.is_relative_to(base):
        fail(f"{i + 1}枚目（type={t}）: path '{rel}' がデッキフォルダの外を指しています"
             f"（パストラバーサルは禁止されています。assets/ 配下の相対パスを指定してください）")
    ext = resolved.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        fail(f"{i + 1}枚目（type={t}）: 画像形式 '{ext or rel}' には対応していません"
             f"（対応拡張子: {', '.join(sorted(e.lstrip('.') for e in ALLOWED_IMAGE_EXT))}）")
    if not resolved.exists():
        fail(f"{i + 1}枚目（type={t}）: 画像ファイルが見つかりません: {rel}")
    if not resolved.is_file():
        fail(f"{i + 1}枚目（type={t}）: path '{rel}' はファイルではありません")
    big = dschema.image_too_big(resolved, rel)
    if big:
        fail(f"{i + 1}枚目（type={t}）: {big}")
    # 壊れた画像は PPTX 段で例外になり HTML だけ先にできてしまうので、ここで開けるか確かめる
    if ext != ".svg":
        try:
            from PIL import Image
        except ImportError:
            Image = None
        if Image is not None:
            try:
                with Image.open(resolved) as im:
                    im.verify()
            except Exception as e:   # noqa: BLE001 - PIL は形式ごとに多様な例外を出す
                fail(f"{i + 1}枚目（type={t}）: 画像ファイルを開けません（壊れているか、拡張子と中身の形式が違います）: "
                     f"{rel}（{type(e).__name__}）→ 画像を作り直すか、正しい形式で保存し直す")
    elif not resolved.read_text(encoding="utf-8", errors="replace").lstrip().startswith(("<", "\ufeff<")):
        fail(f"{i + 1}枚目（type={t}）: SVG ファイルが SVG として読めません: {rel} → 中身が <svg …> で始まるファイルにする")


# ---------------------------------------------------------------------------
# swimlane の検証（M-77 node id 重複 / edges 未知 id / lanes 空、M-53 legend_items の形）
# ---------------------------------------------------------------------------

def _validate_legend_items(items, i: int, t: str):
    if not isinstance(items, list):
        fail(f"{i + 1}枚目（type={t}）: legend_items はリスト（配列）で指定してください")
    for idx, item in enumerate(items):
        if isinstance(item, (list, tuple)):
            if len(item) != 4:
                fail(f"{i + 1}枚目（type={t}）: legend_items[{idx}] は4要素の配列"
                     f"（[shape, variant_or_kind, label, description]）である必要があります"
                     f"（{len(item)}要素でした）")
        elif isinstance(item, dict):
            # shape は必須ではなく、kind だけでも図形を解決できる（norm_legend_items 参照）。
            has_shape = "shape" in item or "kind" in item
            has_text = "label" in item and "desc" in item
            if not (has_shape and has_text):
                fail(f"{i + 1}枚目（type={t}）: legend_items[{idx}] の辞書形式には "
                     f"shape（または kind）/ label / desc がすべて必要です")
        else:
            fail(f"{i + 1}枚目（type={t}）: legend_items[{idx}] の形式が不正です"
                 f"（4要素配列、または {{shape, variant, label, desc}} の辞書を指定してください）")


SWIMLANE_MAX_COLS = 40   # これを超える列は読めず、配線の計算も極端に重くなる
SWIMLANE_TASK_VARIANTS = ("onpf", "onother", "offline")
SWIMLANE_SHAPES = ("task", "system", "decision", "terminal", "marker", "connector", "mail", "io")


def _validate_swimlane(slide: dict, i: int, t: str):
    if not slide.get("lanes"):
        fail(f"{i + 1}枚目（type=swimlane）: lanes が空です")
    lanes = slide["lanes"]
    if not isinstance(lanes, list):
        fail(f"{i + 1}枚目（type=swimlane）: lanes は配列（リスト）で指定してください")
    n_lanes = len(lanes)
    sl_cols = slide.get("cols")
    if isinstance(sl_cols, int) and not isinstance(sl_cols, bool) and sl_cols > SWIMLANE_MAX_COLS:
        fail(f"{i + 1}枚目（type=swimlane）: cols が {sl_cols} です。列は {SWIMLANE_MAX_COLS} 列までです"
             f" → 工程の数に合わせた cols にする（多すぎるときはスライドを分ける）")

    nodes = slide.get("nodes", [])
    if not isinstance(nodes, list):
        fail(f"{i + 1}枚目（type=swimlane）: nodes は配列（リスト）で指定してください")
    edges = slide.get("edges", [])
    if not isinstance(edges, list):
        fail(f"{i + 1}枚目（type=swimlane）: edges は配列（リスト）で指定してください")

    seen_ids = set()
    for nd in nodes:
        if not isinstance(nd, dict):
            fail(f"{i + 1}枚目（type=swimlane）: nodes の要素が正しい形式（オブジェクト）ではありません")
        nid = nd.get("id")
        if nid is None:
            fail(f"{i + 1}枚目（type=swimlane）: ノードに id が指定されていません")
        if nid in seen_ids:
            fail(f"{i + 1}枚目（type=swimlane）: ノード id '{nid}' が重複しています")
        seen_ids.add(nid)
        lane = nd.get("lane", 0)
        if isinstance(lane, bool) or not isinstance(lane, int) or not (0 <= lane < n_lanes):
            fail(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' の lane は 0〜{n_lanes - 1} の整数で"
                 f"指定してください（lanes の行 index。id文字列ではありません）")
        col = nd.get("col", 0)
        if isinstance(col, bool) or not isinstance(col, int) or col < 0:
            fail(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' の col は0以上の整数で指定してください")
        if col >= SWIMLANE_MAX_COLS:
            fail(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' の col が {col} です。列は {SWIMLANE_MAX_COLS} 列までです"
                 f" → col は 0 始まりの工程の順で、飛ばさずに詰めて指定する（多すぎるときはスライドを分ける）")
        # variant は task ノード専用の語彙（onpf / onother / offline）。新図解タイプの variant
        # （emphasis / security …）とは別の名前空間なので、混同した値は warning で知らせる
        # （未知の値は無警告で onother 扱いになり、typo が成果物に紛れ込むため）。
        variant = nd.get("variant")
        if variant is not None and variant not in SWIMLANE_TASK_VARIANTS:
            hint = difflib.get_close_matches(str(variant), SWIMLANE_TASK_VARIANTS, n=1)
            hint_s = f"（候補: {hint[0]}）" if hint else ""
            warn(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' の variant '{variant}' は swimlane では "
                 f"onpf / onother / offline のいずれかです{hint_s}（それ以外は onother として描かれます。"
                 f"emphasis 等の強調は architecture 系タイプの語彙で、swimlane では使えません）")
        shape = nd.get("shape", "task")
        if shape not in SWIMLANE_SHAPES:
            hint = difflib.get_close_matches(str(shape), SWIMLANE_SHAPES, n=1)
            hint_s = f"（候補: {hint[0]}）" if hint else ""
            warn(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' の shape '{shape}' は未対応です{hint_s}"
                 f"（task として描かれます）")
        if "text" not in nd and "label" not in nd and shape not in ("marker", "mail", "io"):
            warn(f"{i + 1}枚目（type=swimlane）: ノード '{nid}' に text がありません（表示名は text に書く。label も受理）")
    for ei, e in enumerate(edges):
        if not isinstance(e, dict):
            fail(f"{i + 1}枚目（type=swimlane）: edges の要素が正しい形式（オブジェクト）ではありません")
        for key in ("from", "to"):
            eid = e.get(key)
            if eid not in seen_ids:
                fail(f"{i + 1}枚目（type=swimlane）: edges の {key} '{eid}' は未知のノード id です")
        ev = e.get("variant")
        if ev is not None and ev not in de.EDGE_VARIANTS:
            warn(f"{i + 1}枚目（type=swimlane）: edges[{ei}] の variant '{ev}' は未対応です"
                 f"（default / emphasis / security / dashed のいずれか）")
        es = e.get("style")
        if es is not None and es not in ("solid", "dashed"):
            warn(f"{i + 1}枚目（type=swimlane）: edges[{ei}] の style '{es}' は solid / dashed のいずれかです"
                 f"（強調などは variant で指定する）")
    if "legend_items" in slide:
        _validate_legend_items(slide["legend_items"], i, t)


# ---------------------------------------------------------------------------
# デッキ全体の検証（ビルド前に一括実行）
# ---------------------------------------------------------------------------

_ID_FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _report_diagnostics(diags, i: int, t: str, geometry_only: bool = False):
    """diagram_engine の診断を build の error / warning / note に振り分けて表示する。
    - スキーマ的な誤り（id 重複・未知 id・セル衝突など）の error はビルドを止める（fail）
    - geometry_only=True（配線・ラベル・文字あふれなど幾何の診断）のときは error でもビルドは
      止めず warning として報告する。厳密に通したいときは check_diagram.py --strict を使う
      （Archify の validate に相当。修理指示 fixes を「→」以降に表示する）"""
    for dg in diags:
        msg = f"{i + 1}枚目（type={t}）: {de.format_diagnostic(dg)}"
        level = dg.get("level")
        if level == "error" and not geometry_only:
            fail(msg)
        elif level in ("error", "warning"):
            warn(msg)
        else:
            note(msg)


DEBUG = False   # --debug を付けたとき True。スライド単位の例外をトレースバックのまま出す


@contextlib.contextmanager
def slide_guard(label: str, what: str = "処理"):
    """スライド 1 枚の処理中に想定外の例外が出たら、トレースバックではなく fail で知らせる。
    label は「3枚目（type=table）」のような場所の表記。--debug のときだけ元の例外を出す。"""
    try:
        yield
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:   # noqa: BLE001 - 想定外の入力の形をまとめて受ける
        if DEBUG:
            raise
        detail = f"{type(e).__name__}: {e}"
        if len(detail) > 160:
            detail = detail[:157] + "..."
        fail(f"{label}の{what}中にエラー: {detail}。入力の形を確認してください"
             f"（キーの型・配列の要素・数値の範囲。詳細は --debug を付けて再実行）")


def _drop_nulls(v):
    """入れ子のオブジェクトの値が null のキーを取り除く（配列の要素は触らない: 要素が null なのは検証で fail にする）。"""
    if isinstance(v, dict):
        for k in [k for k, x in v.items() if x is None]:
            del v[k]
        for x in v.values():
            _drop_nulls(x)
    elif isinstance(v, list):
        for x in v:
            _drop_nulls(x)


def _prune_and_coerce(slide: dict, t: str):
    """スライド直下の値をそろえる（検証の前処理。deck を直接書き換える）。
    - 値が null のキーは「書いていない」と同じ扱いで取り除く（style だけは別に fail する）。
    - 文字列のはずのフィールドに数値が書かれていたら文字列にする（例: number: 1 → "1"）。"""
    for key in [k for k, v in slide.items() if v is None and k != "style"]:
        del slide[key]
    if t != "canvas":
        for key, v in slide.items():
            if key != "style":
                _drop_nulls(v)
    shapes = dict(dschema.COMMON_SHAPES)
    shapes.update(dschema.SLIDE_SHAPES.get(t, {}))
    for key, shape in shapes.items():
        v = slide.get(key)
        if shape == "text" and isinstance(v, (int, float)) and not isinstance(v, bool):
            slide[key] = str(v)
        elif v == "" and not isinstance(shape, str) and key != "style":
            del slide[key]   # 配列・オブジェクトのはずのフィールドに空文字が書かれていたら「書いていない」扱い


def _validate_style_values(style, where_prefix: str, st_defaults: dict, common_defaults: dict, label: str):
    """slide.style / meta.layout_overrides.<type> の各領域の中身（プロパティ名・値の型・範囲）を検査する。"""
    for rname, region in style.items():
        if not isinstance(rname, str) or rname.startswith("_"):
            continue
        if rname == "blocks" and isinstance(st_defaults.get("blocks"), dict):
            continue    # 合成スライドのブロックのタイプ別既定（blocks.<タイプ>.<領域>.<プロパティ>）は _validate_block_defaults_style が見る
        if isinstance(region, dict):
            for pk in [pk for pk, pv in region.items() if pv is None]:
                del region[pk]   # 値が null のプロパティは「指定なし」（既定値のまま）
        defaults = st_defaults.get(rname, common_defaults.get(rname))
        if rname not in st_defaults and rname not in common_defaults:
            # 領域名の未知は呼び出し側が警告する。値が dict なら、プロパティの型（size が文字列など）だけは見る
            if isinstance(region, dict):
                _report_issues(dschema.check_region_value(region, None, f"{where_prefix}.{rname}", check_unknown=False), label)
            continue
        _report_issues(dschema.check_region_value(region, defaults, f"{where_prefix}.{rname}"), label)


def _validate_block_defaults_style(bstyle, where_prefix: str, layout: dict, label: str):
    """合成スライドの style.blocks / meta.layout_overrides.composite.blocks（ブロックのタイプ別の既定の上書き）を検査する。
    形は blocks.<タイプ>.<領域>.<プロパティ>。型違い・範囲違いは、ブロックごとの style と同じ直し方つきの fail にする。"""
    if not isinstance(bstyle, dict):
        fail(f"{label}{where_prefix} はオブジェクト（タイプ名 → 領域名 → プロパティ。例: {{ \"bullets\": {{ \"body\": {{ \"size\": 18 }} }} }}）で指定してください"
             f"（{dschema._vtype(bstyle)}が書かれています）")
    types = layout.get("types", {})
    for tk in list(bstyle):
        tv = bstyle[tk]
        if not isinstance(tk, str) or tk.startswith("_"):
            continue
        here = f"{where_prefix}.{tk}"
        if tk in comp.NATIVE_TYPES:
            warn(f"{label}{here} は無視されます（text / callout / image のブロックの文字サイズなどは、style.{tk} か、ブロックごとの style に書く）")
            continue
        if tk not in types or tk == "composite":
            pool = [x for x in types if x != "composite"]
            warn(f"{label}{here} は合成スライドのブロックのタイプ名ではありません{dschema.hint(tk, pool)}"
                 f" → ブロックに使うタイプ名（bullets / table / cards / steps …）を書く")
            continue
        if not isinstance(tv, dict):
            fail(f"{label}{here} はオブジェクト（領域名 → プロパティ。例: {{ \"body\": {{ \"size\": 18 }} }}）で指定してください"
                 f"（{dschema._vtype(tv)}が書かれています）")
        for rn in list(tv):
            rv = tv[rn]
            if not isinstance(rn, str) or rn.startswith("_"):
                continue
            if rn not in types[tk] and rn not in layout.get("common", {}):
                warn(f"{label}{here}.{rn} は {tk} の領域名ではありません{dschema.hint(rn, list(types[tk]))}"
                     f" → 使える領域: {' / '.join(types[tk].keys())}")
                continue
            if isinstance(rv, dict):
                for pk in [pk for pk, pv in rv.items() if pv is None]:
                    del rv[pk]
            defaults = types[tk].get(rn, layout.get("common", {}).get(rn))
            extra = ((types.get("composite", {}).get("blocks") or {}).get(tk) or {}).get(rn)       # ブロックの既定（thin_* など、合成のブロックだけが読むトークン）
            if isinstance(extra, dict):
                defaults = {**(defaults if isinstance(defaults, dict) else {}), **extra}
            _report_issues(dschema.check_region_value(rv, defaults, f"{here}.{rn}"), label)


def _validate_meta_hero(meta: dict, layout: dict):
    """meta.section_numbers（章番号の自動採番）と meta.variants（タイプ別の既定の variant）の検査。"""
    sn = meta.get("section_numbers")
    if sn is not None and not isinstance(sn, bool):
        fail(f"meta.section_numbers は true / false で指定してください（{dschema._vtype(sn)}が書かれています）"
             f" → 章扉（section）に 01, 02 … を自動で振るなら true")
    tm = meta.get("todo_marks")
    if tm is not None and not isinstance(tm, bool):
        fail(f"meta.todo_marks は true / false で指定してください（{dschema._vtype(tm)}が書かれています）"
             f" → 【要確認】の強調表示を切るなら false（既定は true）")
    mv = meta.get("variants")
    if mv is None:
        return
    if not isinstance(mv, dict):
        fail(f"meta.variants は {{ タイプ名: variant 名 }} のオブジェクトで指定してください（例: {{\"title\": \"left-band\", \"section\": \"number\"}}）")
    vtypes = layout.get("variants") or {}
    for tn, vn in mv.items():
        if tn not in vtypes:
            near = difflib.get_close_matches(str(tn), list(vtypes), n=1)
            warn(f"meta.variants の '{tn}' は variant を持つタイプではありません。無視します{('（もしかして ' + near[0] + '）') if near else ''}"
                 f" → variant を持つタイプ: {' / '.join(vtypes)}")
            continue
        names = list(vtypes[tn])
        if not isinstance(vn, str) or (vn != "default" and vn not in names):
            near = difflib.get_close_matches(str(vn), names, n=1)
            fail(f"meta.variants.{tn} の '{vn}' という variant はありません{('（もしかして ' + near[0] + '）') if near else ''}"
                 f" → {tn} の variant: {' / '.join(names)}（既定の見た目なら \"default\"）")


def _check_brand_width(meta: dict, layout: dict):
    """meta.brand が右上の箱（common.brand の w）に 1 行で入らないと、全スライドで 2 行に折れて箱からあふれる。ビルドで 1 回だけ知らせる。"""
    brand = meta.get("brand")
    if not isinstance(brand, str) or not brand.strip():
        return
    br = dict((layout.get("common") or {}).get("brand") or {})
    ov = meta.get("layout_overrides")
    ov_brand = ((ov.get("common") or {}).get("brand") if isinstance(ov, dict) and isinstance(ov.get("common"), dict) else None)
    if isinstance(ov_brand, dict):
        br.update(ov_brand)
    w, size = br.get("w"), br.get("size")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in (w, size)):
        return
    need = autofit.text_em(brand, bool(br.get("bold"))) * size
    if need <= w + 0.5:
        return
    zen, han = max(1, int(w // size)), max(1, int(w // (size * 0.72)))     # 半角は英大文字の幅（約 0.72em）で見積もる
    warn(f"meta.brand「{brand}」は右上の箱（幅 {w:g}px・文字 {size:g}px）に 1 行で収まりません（約 {need:.0f}px）。"
         f"全スライドで 2 行に折れて箱からあふれます → 短くする（目安は全角 {zen} 字・半角 {han} 字前後まで）か、"
         f"meta.layout_overrides.common.brand で w を広げる（x も同じだけ左へ）・size を下げる")


def validate_deck(deck: dict, layout: dict, theme: dict, deck_dir: Path):
    """deck.json をビルド前に一括検証する。問題があれば fail()（即終了）または warn()/note()。
    型違いの入力（配列のはずが文字列など）は fail、未知のキー・極端な値は warn。
    スライド直下の null は「書いていない」とみなして取り除き、数値の文字列フィールドは文字列にそろえる（deck を書き換える）。"""
    if not isinstance(deck, dict):
        fail("deck.json の形式が不正です（トップレベルはオブジェクトである必要があります）")
    meta = deck.get("meta", {})
    if not isinstance(meta, dict):
        fail("deck.json の形式が不正です（meta はオブジェクトである必要があります）")

    for key in deck:
        if key not in ("meta", "slides") and isinstance(key, str) and not key.startswith("_"):
            warn(f"deck.json の最上位の未知のキー \"{key}\" は無視されます{dschema.hint(key, ('meta', 'slides'))}"
                 f" → 使えるのは meta と slides だけです")
    _report_issues(dschema.unknown_meta_keys(meta), "")

    # meta.id: 省略可。禁止文字は fail、フォルダ名と異なる場合は note。
    raw_id = meta.get("id")
    if raw_id is not None:
        if _ID_FORBIDDEN_RE.search(str(raw_id)):
            fail(f"meta.id に使用できない文字が含まれています: '{raw_id}'"
                 f"（\\ / : * ? \" < > | と制御文字は使用できません）")
        if deck_dir is not None and str(raw_id) != Path(deck_dir).name:
            note(f"meta.id（{raw_id}）とフォルダ名（{Path(deck_dir).name}）が一致していません")

    mt = meta.get("title")
    if mt is None or (isinstance(mt, str) and not mt.strip()):
        warn("meta.title がありません。HTML の <title> と PPTX の文書プロパティ（Finder・メールで見える題名）には"
             f"代わりに「{deck_title(deck, deck_dir) or 'デッキ'}」を使います"
             " → meta.title に資料の題名を書く")

    if not layout.get("_tokens_resolved"):
        layout = shp.apply_to_layout(layout, None, None, fail=fail)   # json から直接読んだレイアウトも、既定の tokens で解決する
    # 形トークンの参照（"$radius.card" など）は、型や範囲の検査の前に解決済みの値へ置き換える（未知の参照は fail）
    if isinstance(meta.get("layout_overrides"), dict):
        meta["layout_overrides"] = shp.resolve_style_refs(meta["layout_overrides"], layout, "meta.layout_overrides", fail)
    for _s in (deck.get("slides") if isinstance(deck.get("slides"), list) else []):
        if isinstance(_s, dict) and isinstance(_s.get("style"), dict):
            _s["style"] = shp.resolve_style_refs(_s["style"], layout, f"{(deck['slides'].index(_s) + 1)}枚目の style", fail)

    _check_brand_width(meta, layout)

    types_known = set(layout.get("types", {}).keys())
    common_keys = set(layout.get("common", {}).keys())
    common_defaults = layout.get("common", {})

    _check_density_autofit(meta, "meta.")
    _validate_meta_hero(meta, layout)

    # meta.layout_overrides のトップキー検証（"common" は特別扱い）
    overrides = meta.get("layout_overrides", {})
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        fail("meta.layout_overrides はオブジェクト（タイプ名 → 領域 → プロパティ）である必要があります")
    for ov_type, ov_val in overrides.items():
        if ov_type == "common":
            if not isinstance(ov_val, dict):
                fail("meta.layout_overrides.common はオブジェクト（領域名 → プロパティ）で指定してください")
            for key in ov_val:
                if key not in common_keys:
                    hint = difflib.get_close_matches(key, common_keys, n=1)
                    hint_s = f"（候補: {hint[0]}）" if hint else ""
                    warn(f"meta.layout_overrides.common: '{key}' は共通領域名ではありません{hint_s}")
            _validate_style_values(ov_val, "meta.layout_overrides.common", {}, common_defaults, "")
            continue
        if not isinstance(ov_type, str) or ov_type not in types_known:
            hint = difflib.get_close_matches(str(ov_type), types_known, n=1)
            hint_s = f"（候補: {hint[0]}）" if hint else ""
            fail(f"meta.layout_overrides に未知のスライドタイプ '{ov_type}' があります{hint_s}")
        if not isinstance(ov_val, dict):
            fail(f"meta.layout_overrides.{ov_type} はオブジェクト（領域名 → プロパティ）で指定してください"
                 f"（{dschema._vtype(ov_val)}が書かれています）")
        allowed = common_keys | set(layout["types"][ov_type].keys())
        for key in ov_val:
            if key not in allowed:
                hint = difflib.get_close_matches(key, allowed, n=1)
                hint_s = f"（候補: {hint[0]}）" if hint else ""
                warn(f"meta.layout_overrides.{ov_type}: '{key}' は {ov_type} の領域名ではありません{hint_s}")
        _validate_style_values(ov_val, f"meta.layout_overrides.{ov_type}", layout["types"][ov_type],
                               common_defaults, "")
        if ov_type == "composite" and "blocks" in ov_val:
            _validate_block_defaults_style(ov_val["blocks"], "meta.layout_overrides.composite.blocks", layout, "")

    slides = deck.get("slides", [])
    if not isinstance(slides, list):
        fail("slides は配列（リスト）である必要があります")
    if not slides:
        warn("slides が空です。1枚もスライドがありません → deck.json の最上位は meta と slides の2つです"
             "（\"slide\" など打ち間違いがないか確認）")

    _assign_section_numbers(deck, layout)
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            fail(f"{i + 1}枚目のスライドが正しい形式（オブジェクト）ではありません")

        t = slide.get("type")
        if not t:
            fail(f"{i + 1}枚目のスライドに type がありません")
        if not isinstance(t, str):
            fail(f"{i + 1}枚目: type は文字列で指定してください（{dschema._vtype(t)}が書かれています）"
                 f" → 使えるタイプ: {', '.join(sorted(types_known))}")
        if t not in types_known:
            hint = difflib.get_close_matches(t, types_known, n=1)
            hint_s = f"（候補: {hint[0]}）" if hint else ""
            fail(f"{i + 1}枚目: 未知のスライドタイプ: {t}{hint_s}"
                 f" → 使えるタイプ: {', '.join(sorted(types_known))}")
        if t not in RENDERED_TYPES:
            fail(f"{i + 1}枚目（type={t}）: このタイプの描画が登録されていません"
                 f"（レイアウト JSON にはあるが、HTML / PPTX の描画器が無い）"
                 f" → 描画器のあるタイプ: {', '.join(sorted(RENDERED_TYPES & types_known))}")

        with slide_guard(f"{i + 1}枚目（type={t}）", "検証"):
            _validate_slide(deck, layout, theme, deck_dir, i, slide, t, types_known, common_keys)


_BLOCK_IGNORED_KEYS = ("title", "lead", "eyebrow", "conclusion", "source")


def _validate_composite_blocks(deck, layout, theme, deck_dir, i, slide, types_known, common_keys):
    """合成スライドのブロックの検査（スタイル解決より前）。型違い・未知のキー・使えないタイプは fail / warn。
    既存タイプのブロックは、そのタイプの検査（内容の型・未知キー・style）をブロックの場所つきでそのまま通す。"""
    pre = f"{i + 1}枚目（type={slide.get('type')}）: "
    blocks = slide.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        fail(f"{pre}blocks（ブロックの配列）が空か書かれていません"
             f" → \"blocks\": [{{\"type\": \"bullets\", \"bullets\": [\"…\"]}}, {{\"type\": \"architecture\", …}}] のように 2〜4 個書く"
             f"（\"block\" など打ち間違いも確認）")
    if len(blocks) > 6:
        warn(f"{pre}ブロックが{len(blocks)}個あります（2〜4 個が目安。多いと文字が小さくなる）→ 2 枚に分ける")
    elif len(blocks) == 1 and slide.get("type") == "composite":
        warn(f"{pre}ブロックが 1 個だけです → 合成にする意味がありません。そのタイプのスライドにする（または 2 個以上にする）")
    emph_n = 0
    for k, block in enumerate(blocks):
        where = f"{k + 1} つ目のブロック"
        if not isinstance(block, dict):
            fail(f"{pre}{where}がオブジェクトではありません（{dschema._vtype(block)}が書かれています）"
                 f" → {{\"type\": \"bullets\", \"bullets\": [...]}} の形で書く")
        bt = block.get("type")
        if bt is None:
            fail(f"{pre}{where}に type がありません → ブロックに使えるタイプ: "
                 f"{', '.join(sorted(set(comp.NATIVE_TYPES) | set(BLOCK_MAIN_REGION) | set(engine_registry.names())))}")
        prob = block_type_problem(bt, types_known)
        if prob:
            fail(f"{pre}{where}: {prob}")
        # 共通キーの型
        if block.get("heading") is not None and not isinstance(block["heading"], (str, int, float)):
            fail(f"{pre}{where}: heading は文字列で指定してください（{dschema._vtype(block['heading'])}が書かれています）")
        if isinstance(block.get("heading"), (int, float)) and not isinstance(block["heading"], bool):
            block["heading"] = str(block["heading"])
        if isinstance(block.get("heading"), bool):
            fail(f"{pre}{where}: heading は文字列で指定してください（真偽値が書かれています） → \"heading\": \"ポイント\" のように書く")
        if isinstance(block.get("heading"), str) and not block["heading"].strip():
            warn(f"{pre}{where}（{bt}）: heading が空文字です。小見出しなしとして扱います → 小見出しが要らなければ heading を消す、要るなら文字を書く")
            del block["heading"]
        for key in ("x", "y", "w", "h"):
            if key in block:
                warn(f"{pre}{where}（{bt}）: {key} は書けません。位置と大きさは columns / rows / arrange（と col / row / col_span / row_span）で決まります。"
                     f"この指定は無視します → 位置を変えたいときは配置の指定を直す")
                del block[key]
        if block.get("frame") is not None and block["frame"] not in comp.FRAMES:
            fail(f"{pre}{where}: frame は {' / '.join(comp.FRAMES)} のいずれかで指定してください（{block['frame']!r}が書かれています）"
                 f"{comp.key_hint(block['frame'], comp.FRAMES)}")
        if block.get("emphasis") is not None and not isinstance(block["emphasis"], bool):
            fail(f"{pre}{where}: emphasis は true / false で指定してください（{dschema._vtype(block['emphasis'])}が書かれています）")
        for key, pool in (("align", comp.ALIGNS), ("valign", comp.VALIGNS)):
            if block.get(key) is not None and block[key] not in pool:
                fail(f"{pre}{where}: {key} は {' / '.join(pool)} のいずれかで指定してください（{block[key]!r}が書かれています）")
        for key in ("col", "row", "col_span", "row_span"):
            v = block.get(key)
            lo = 1 if key.endswith("span") else 0
            if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < lo):
                fail(f"{pre}{where}: {key} は {lo} 以上の整数で指定してください（{v!r}が書かれています）"
                     f"{'（0 始まり）' if lo == 0 else ''}")
        if "style" in block and not isinstance(block["style"], dict):
            fail(f"{pre}{where}: style はオブジェクト（{{ \"body\": {{ \"size\": 18 }} }}）である必要があります"
                 f"（{dschema._vtype(block['style'])}が書かれています）")
        for key in _BLOCK_IGNORED_KEYS:
            if key in block:
                warn(f"{pre}{where}（{bt}）: {key} はブロックでは描かれません"
                     f"{' → ブロックの見出しは heading に書く' if key in ('title', 'eyebrow') else ' → スライド全体の ' + key + ' に書く'}")
        for key in ("legend_page", "legend_lead", "legend_eyebrow", "legend_items"):
            if key in block:
                warn(f"{pre}{where}（{bt}）: {key} は合成スライドのブロックでは使えません（凡例ページは自動では挿入されません）"
                     f" → 凡例が要るなら、その図解を単独のスライドにする")
                block.pop(key)
        if bt == "code" and block.get("annotations"):
            warn(f"{pre}{where}（code）: annotations（番号つきの注釈）は合成スライドのブロックでは描きません。この指定は無視します"
                 f" → 注釈つきのコードは単独のスライドにする（合成の中なら、注釈の文を隣の bullets / text のブロックに書く）")
            block.pop("annotations")
        if block.get("emphasis"):
            emph_n += 1
            if not (bt in ("text", "callout") or bt in EMPHASIS_TYPES):
                warn(f"{pre}{where}（{bt}）: emphasis は {' / '.join(('text', 'callout') + EMPHASIS_TYPES)} のブロックで使えます。"
                     f"この指定は無視します → 強調したいブロックを callout か bullets にする（または frame: box にする）")
        if block.get("align") and bt not in ("text", "callout"):
            warn(f"{pre}{where}（{bt}）: align は text / callout のブロックだけで効きます。この指定は無視します")
        if block.get("valign") and bt not in ("text", "callout") and bt not in BLOCK_VALIGN_REGION:
            warn(f"{pre}{where}（{bt}）: valign は text / callout / {' / '.join(BLOCK_VALIGN_REGION)} のブロックだけで効きます。この指定は無視します")
        user_style = block.get("style") or {}
        if user_style:
            block["style"] = user_style = shp.resolve_style_refs(user_style, layout, f"{i + 1}枚目の {k + 1} つ目のブロックの style", fail)
        main = block_main_region(bt)
        for rname, region in user_style.items():
            if isinstance(region, dict) and main and rname == main and any(g in region for g in ("x", "y", "w", "h")):
                warn(f"{pre}{where}（{bt}）: style.{rname} の x / y / w / h は無視します（ブロックの位置と大きさは columns / rows / arrange で決まる）")
        if bt in comp.NATIVE_TYPES:
            allowed = set(comp.NATIVE_KEYS[bt]) | set(comp.BLOCK_COMMON_KEYS) | set(_BLOCK_IGNORED_KEYS)
            for key in block:
                if isinstance(key, str) and not key.startswith("_") and key not in allowed:
                    warn(f"{pre}{where}（{bt}）: 未知のキー \"{key}\" は無視されます{dschema.suggest(key, allowed)}"
                         f" → {bt} のキー: {' / '.join(sorted(comp.NATIVE_KEYS[bt]))}（共通: heading / frame / emphasis / align / valign / col / row / col_span / row_span / style）")
            for rname, region in user_style.items():
                if rname != bt:
                    warn(f"{pre}{where}（{bt}）: style の '{rname}' は {bt} の領域名ではありません → 使える領域: {bt}")
                else:
                    _report_issues(dschema.check_region_value(region, layout.get("types", {}).get("composite", {}).get(bt), f"style.{bt}"), pre)
            if bt in ("text", "callout"):
                if bt == "text" and not comp.text_paragraphs(block):
                    fail(f"{pre}{where}（text）: text（段落。改行で段落を分ける）か paragraphs（段落の配列）が必要です")
                if bt == "callout" and not (isinstance(block.get("text"), str) and block["text"].strip()):
                    fail(f"{pre}{where}（callout）: text（強調する一文）が必要です → \"text\": \"移行は 2 段階で進める\"、補足は note に書く")
                for key in ("text", "note"):
                    if block.get(key) is not None and not isinstance(block[key], (str, int, float)):
                        fail(f"{pre}{where}（{bt}）: {key} は文字列で指定してください（{dschema._vtype(block[key])}が書かれています）")
                if isinstance(block.get("paragraphs"), list) and not all(isinstance(p, (str, int, float)) for p in block["paragraphs"]):
                    fail(f"{pre}{where}（text）: paragraphs は文字列の配列で指定してください")
            else:
                if block.get("fit") is not None and block["fit"] not in ("contain", "cover"):
                    fail(f"{pre}{where}（image）: fit は contain / cover のどちらかで指定してください（{block['fit']!r}）")
                if block.get("path") is not None and not isinstance(block["path"], str):
                    fail(f"{pre}{where}（image）: path は文字列で指定してください（{dschema._vtype(block['path'])}が書かれています）"
                         f" → \"path\": \"assets/図.png\" のように、デッキフォルダからの相対パスを 1 つ書く")
                with block_messages(i + 1, k, "image", slide.get("type")):
                    _validate_image_path({"path": block.get("path")}, i, "image", deck_dir)
            continue
        # 既存タイプのブロック: そのタイプの前半の検査をそのまま通す（場所はブロックに書き換える）
        bs = block_slide(slide, block, k, deck)
        bs["style"] = user_style
        for key in _BLOCK_IGNORED_KEYS:
            bs.pop(key, None)
        with block_messages(i + 1, k, bt, slide.get("type")):
            _validate_slide_head(deck, layout, theme, deck_dir, i, bs, bt, types_known, common_keys)
            if bt in GRID_DIAGRAM_TYPES:
                # 格子の図解は row / col の上限を、スタイル解決（自動フィットの拡大が格子を作る）より前に確かめる（単独スライドと同じ上限）
                _report_diagnostics([d for d in de.validate_grid_diagram(bs, bt) if d.get("level") == "error"], i, bt)
        # 検査が書き換えた分（null の除去・数値の文字列化・表の行の正規化）を、元のブロックに戻す
        for key in [key for key in block if key not in comp.BLOCK_COMMON_KEYS and key not in _BLOCK_IGNORED_KEYS]:
            if key not in bs:
                del block[key]
            else:
                block[key] = bs[key]
        if "_row_emphasis" in bs:
            block["_row_emphasis"] = bs["_row_emphasis"]
        else:
            block.pop("_row_emphasis", None)
        if bt == "pattern":
            try:
                _pat = pat_e.load_pattern(block.get("pattern"), deck_dir)
            except pat_e.PatternError:
                _pat = None
            if _pat is not None and pat_e.frame_of(_pat) != "body":
                fail(f"{pre}{where}（pattern）: パターン '{block.get('pattern')}' は全面（frame: full）の型なのでブロックにできません"
                     f" → 単独の pattern スライドにするか、body 枠のパターン（pattern_engine.py list で frame を確認）を使う")
    if emph_n > 1:
        warn(f"{pre}emphasis が{emph_n}個のブロックにあります（1 枚に 1 つまで。主役が分からなくなる）→ 主役のブロックだけにする")
    plan = comp.plan_grid(blocks, *_grid_spec(slide))
    if plan["problems"]:
        fail(f"{pre}{plan['problems'][0]}")
    if plan["empty"]:
        cells = "、".join(f"{r + 1}行{c + 1}列目" for c, r in plan["empty"][:3])
        warn(f"{pre}格子に空きがあります（{cells}）→ ブロックを足すか、columns / rows / arrange を減らす（col_span / row_span で広げるのも有効）")


def _validate_composite_tail(deck, layout, theme, deck_dir, i, slide, st):
    """合成スライドのブロックの検査（スタイル解決より後）。合成専用ブロックの文字あふれと、既存タイプのブロックのタイプ別検査。"""
    cs = st.get("_composite") or {}
    for level, _code, text in cs.get("issues", []):
        (warn if level == "warn" else note)(text.replace("{label}", f"{i + 1}枚目（type={slide.get('type')}）"))
    for rb in cs.get("blocks", []):
        bt, k = rb["type"], rb["index"]
        if rb["native"]:
            issues: list = []
            _walk_colors(rb.get("region") or {}, "", theme, i, bt, issues)
            if issues:
                with block_messages(i + 1, k, bt, slide.get("type")):
                    fail(issues[0])
            continue
        bs = rb["bs"]
        if bt == "kpi_tree":
            r = rb["st"]["body"]
            # kpi_tree は領域が狭いと列の幅と間隔を同じ比率で縮める（proposal_engine.layout_kpi_tree。下限 min_scale）。
            # 下限まで縮めても入らない幅だけを fail にする（縮めれば入る幅は通す）
            cols_w = r.get("root_w", 150) + r.get("branch_w", 170) + r.get("kpi_w", 230) + r.get("value_w", 120)
            has_note = any(isinstance(kp, dict) and (kp.get("items") or kp.get("note")) for br in (bs.get("branches") or [])
                           if isinstance(br, dict) for kp in (br.get("kpis") or []))
            need = (cols_w + 3 * r.get("gap_x", 26)) * r.get("min_scale", 0.5) + 12 + (r.get("note_min_w", 200) if has_note else 0)
            if r["w"] < need:
                fail(f"{i + 1}枚目（type={slide.get('type')}）の {k + 1} つ目のブロック（kpi_tree）: 幅 {int(r['w'])}px に収まりません"
                     f"（列を半分まで縮めても、最低 {int(need)}px 要る）→ ブロックを広げる（arrange / columns の比率、col_span で 2 列にまたがせる）か、"
                     f"単独のスライドにする")
        with block_messages(i + 1, k, bt, slide.get("type")):
            _validate_slide_tail(deck, layout, theme, deck_dir, i, bs, bt, st_fn=lambda rb=rb: rb["st"])


def _normalize_table_rows(slide: dict, pre: str):
    """table の行を [セルの配列] にそろえ、強調行は slide["_row_emphasis"]（行番号の配列）に移す。
    行は [..] か {"cells": [..], "emphasis": true}。セルの tone（good / warn / bad / accent / muted）を検査する。"""
    rows = slide.get("rows")
    if not isinstance(rows, list):
        return
    emph = []
    out = []
    for ri, r in enumerate(rows):
        if isinstance(r, dict):
            if "cells" not in r:
                fail(f"{pre}{ri + 1}行目に cells がありません → {{\"cells\": [\"A\", \"B\"], \"emphasis\": true}} の形で書く")
            if r.get("emphasis"):
                emph.append(ri)
            r = r["cells"]
        out.append(r)
        for ci, cell in enumerate(r):
            if isinstance(cell, dict) and cell.get("tone") is not None and cell["tone"] not in autofit.TONES:
                fail(f"{pre}{ri + 1}行{ci + 1}列目の tone '{cell['tone']}' は使えません"
                     f" → {' / '.join(autofit.TONES)} のいずれかを指定する")
    slide["rows"] = out
    if emph:
        slide["_row_emphasis"] = emph
    else:
        slide.pop("_row_emphasis", None)


def _check_density_autofit(src: dict, where: str):
    """meta / スライドの density（talk / standard / read）と autofit（真偽値）の値を検査する。"""
    d = src.get("density")
    if d is not None and d not in autofit.DENSITIES:
        shown = d if isinstance(d, str) else dschema._vtype(d)
        fail(f"{where}density は {' / '.join(autofit.DENSITIES)} のいずれかで指定してください（{shown} が書かれています）"
             f" → 話す用は talk、読ませる用は read、迷ったら省略（standard）")
    a = src.get("autofit")
    if a is not None and not isinstance(a, bool):
        fail(f"{where}autofit は true / false で指定してください（{dschema._vtype(a)}が書かれています）"
             f" → 自動フィットを切るときは false")


def _check_col_widths(widths, i: int, t: str, ncols: int):
    """col_widths（比率の配列）の検査: 要素数が列数と同じ・すべて 0 以上の数値・合計が 0 より大きい。"""
    if not widths:
        return
    pre = f"{i + 1}枚目（type={t}）: "
    if not isinstance(widths, list) or any(isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0
                                           for w in widths):
        fail(f"{pre}col_widths は 0 以上の数値の配列（例: [3, 3, 6]）で指定してください")
    if len(widths) != ncols:
        fail(f"{pre}col_widths の要素数（{len(widths)}）が columns 数（{ncols}）と一致しません")
    if sum(widths) <= 0:
        fail(f"{pre}col_widths の合計が 0 です → 列の幅の比率を 1 つ以上 0 より大きくする（例: [3, 3, 6]）")


def _warn_missing_text(missing: list, pre: str):
    """text の無い項目の警告を 1 スライドにつき 1 件にまとめる（キーの打ち間違いは全項目で同じになるため）。"""
    if not missing:
        return
    path, hint_s = missing[0]
    if len(missing) == 1:
        warn(f"{pre}{path} に text がありません（空の項目になります）{hint_s} → 項目の文字は \"text\" に書く")
    else:
        warn(f"{pre}{len(missing)} 個の項目に text がありません（例: {path}。空の項目になります）{hint_s}"
             f" → 項目の文字は \"text\" に書く")


def _check_bullet_items(items, path: str, pre: str, depth: int = 1, missing=None):
    """箇条書きの項目の検査: dict なのに text が無い（txt などの打ち間違い）、3 階層目以降（描画されない）を warn。
    text が無い項目は missing（リスト）に集める。None のときはこの呼び出しの分をその場でまとめて警告する。"""
    if not isinstance(items, list):
        return
    own = missing is None
    if own:
        missing = []
    for idx, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        if "text" not in it:
            missing.append((f"{path}[{idx}]", dschema.hint(next(iter(it), ''), ['text'])))
        kids = it.get("children")
        if kids:
            if depth >= 2:
                warn(f"{pre}{path}[{idx}] の children は 3 階層目以降のため表示されません"
                     f" → 2 階層（項目＋子項目）までにまとめるか、別のスライドに分ける")
            else:
                _check_bullet_items(kids, f"{path}[{idx}].children", pre, depth + 1, missing)
    if own:
        _warn_missing_text(missing, pre)


# 本文として最低限必要な内容フィールド（すべて空のとき白紙スライドになる）。タイプ → フィールド名
EMPTY_BODY_FIELDS = {
    "bullets": ("bullets",), "cards": ("cards",), "steps": ("steps",), "agenda": ("items",),
    "two_column": ("left", "right"), "matrix": ("quadrants",), "code": ("code",), "closing": ("bullets", "message", "title"),
    "table": ("rows",), "status_table": ("rows",), "image_text": ("bullets", "punch"),
}


def _warn_empty_body(slide: dict, i: int, t: str):
    fields = EMPTY_BODY_FIELDS.get(t)
    if not fields:
        return

    def empty(v):
        if v in (None, "", [], {}):
            return True
        if isinstance(v, dict):
            return all(empty(x) for x in v.values())
        if isinstance(v, list):
            return all(empty(x) for x in v)
        return False
    if all(empty(slide.get(f)) for f in fields):
        warn(f"{i + 1}枚目（type={t}）: 本文が空です（{' / '.join(fields)} が無いか空）。白紙に近いスライドになります"
             f" → 内容を書くか、このスライドを削る（フィールド名の打ち間違いも確認）")


# 主役系（S2d）: 背景・variant を持てる全面系のタイプと、画像の底上げをするタイプ
HERO_BG_TYPES = hero.BG_TYPES


def _assign_section_numbers(deck: dict, layout: dict):
    """meta.section_numbers: true のとき、number の無い section に章の順で 01, 02 … を振る。
    number / side の variant を使う section は、number が無ければ（meta の指定が無くても）同じ順で振る。"""
    slides = deck.get("slides") if isinstance(deck.get("slides"), list) else []
    on = (deck.get("meta") or {}).get("section_numbers") is True
    n = 0
    for sl in slides:
        if not isinstance(sl, dict) or sl.get("type") != "section":
            continue
        n += 1
        if sl.get("number") in (None, ""):
            needs = hero.variant_of(layout, deck, sl) in ("number", "side")
            if on or needs:
                sl["number"] = f"{n:02d}"


def _prepare_hero(deck, layout, theme, deck_dir, i, slide, t):
    """主役系の入力の検査と、背景の解決（覆いの濃さ・文字色モード）。結果は slide["_bg"]（resolve_style と描画が読む）。"""
    slide.pop("_bg", None)
    colors = theme.get("colors", {})
    pre = f"{i + 1}枚目（type={t}）"
    img_check = lambda rel: ce.check_image_path(rel, deck_dir)
    for level, text in hero.deco_problems(slide.get("style"), f"{pre}: ", colors):     # variant の飾り（style.deco1 など）の値
        (fail if level == "fail" else warn)(text)
    # variant の値
    v = slide.get("variant")
    if v is not None and t in (layout.get("variants") or {}):
        names = hero.variant_names(layout, t)
        if not isinstance(v, str) or (v != "default" and v not in names):
            near = difflib.get_close_matches(str(v), names, n=1, cutoff=0.5)
            fail(f"{pre}: variant '{v}' はありません{('（もしかして ' + near[0] + '）') if near else ''}"
                 f" → {t} の variant: {' / '.join(names)}（既定の見た目にするなら variant を消すか \"default\"）")
    name = hero.variant_of(layout, deck, slide)
    bgd = None
    rect = (0, 0, hero.CANVAS_W, hero.CANVAS_H)
    merged = layout.get("types", {}).get(t, {})
    if hero.variant_layer(layout, t, name):
        merged = hero.deep_merge(merged, hero.variant_layer(layout, t, name))
    if t in HERO_BG_TYPES:
        raw = slide.get("background")
        if raw is not None:
            bgd = hero.validate_background(raw, f"{pre}: background", colors, deck_dir, fail, warn, img_check)
            rect = hero.bg_rect_of(merged)
    elif t == "split":
        hero.validate_split(slide, pre, fail, warn, colors, deck_dir, img_check)
        p = slide.get("panel") or {}
        bgd = hero.validate_background({k: p[k] for k in ("fill", "image", "overlay", "opacity", "position") if k in p}, f"{pre}: panel", colors,
                                       deck_dir, fail, warn, img_check) if any(k in p for k in ("fill", "image")) else None
        if bgd is None:
            bgd = {"fill": merged.get("panel", {}).get("fill", "primary")}
        side, ratio = hero.split_params(slide, merged.get("panel") or {})
        pw = round(hero.CANVAS_W * ratio)
        rect = (0 if side == "left" else hero.CANVAS_W - pw, 0, pw, hero.CANVAS_H)
    elif t == "image":
        fit = slide.get("fit")
        if fit is not None and fit not in hero.IMAGE_FITS:
            fail(f"{pre}: fit は {' / '.join(hero.IMAGE_FITS)} のどちらかで指定してください（{fit!r}）→ 全面に敷くなら \"fit\": \"bleed\"（既定は contain）")
        cp = slide.get("caption_position")
        if cp is not None and cp not in hero.CAPTION_POSITIONS:
            fail(f"{pre}: caption_position は {' / '.join(hero.CAPTION_POSITIONS)} のどちらかで指定してください（{cp!r}）→ 画像の下に帯を敷くなら \"band\"")
        if cp == "band" and not str(slide.get("caption") or "").strip():
            warn(f"{pre}: caption_position: band は caption（帯の中に入れる文）が必要です。caption が無いので帯は出しません"
                 f" → caption を書く（帯が要らないなら caption_position を消す）")
        if fit == "bleed":
            src = {k: slide[k] for k in ("overlay", "opacity", "position") if k in slide}
            src["image"] = slide.get("path")
            bgd = hero.validate_background(src, f"{pre}: background", colors, deck_dir, fail, warn, img_check) if slide.get("path") else None
        elif any(k in slide for k in ("overlay", "opacity")):
            warn(f"{pre}: overlay / opacity は fit: bleed（画像を全面に敷く）のときだけ使います。この指定は無視します → 全面に敷くなら \"fit\": \"bleed\" を足す")
    elif t == "image_text":
        if slide.get("bleed") is not None and not isinstance(slide["bleed"], bool):
            fail(f"{pre}: bleed は true / false で指定してください（{slide['bleed']!r}）→ 画像を端まで届かせるなら \"bleed\": true（届かせないなら書かない）")
        if slide.get("bleed") is True and slide.get("path"):
            src = {"image": slide["path"], "overlay": "none"}
            if "position" in slide:
                src["position"] = slide["position"]
            bgd = hero.validate_background(src, f"{pre}: background", colors, deck_dir, fail, warn, img_check)
            rect = hero.bg_rect_of(merged)
    if bgd is None:
        return
    pal = hero.palettes_for(layout, t, name)
    res = hero.solve_background(bgd, colors, rect, deck_dir, pal, hero.on_bg_regions(layout, t, name, bool((deck.get("meta") or {}).get("brand")), slide),
                                (layout.get("palettes") or {}).get("_fallback"))
    res["rect"] = rect
    for level, text in hero.background_problems(res, bgd, f"{pre}: panel" if t == "split" else pre):
        (warn if level == "warn" else note)(text)
    slide["_bg"] = res


def _validate_slide(deck, layout, theme, deck_dir, i, slide, t, types_known, common_keys):
    """validate_deck のスライド 1 枚分。前半（内容の型・キー・style の検査）→ 合成スライドのブロック検査 → 後半（スタイル解決・タイプ別の検査）。"""
    _validate_slide_head(deck, layout, theme, deck_dir, i, slide, t, types_known, common_keys)
    _prepare_hero(deck, layout, theme, deck_dir, i, slide, t)
    if t in COMPOSITE_TYPES:
        _validate_composite_blocks(deck, layout, theme, deck_dir, i, slide, types_known, common_keys)
    _validate_slide_tail(deck, layout, theme, deck_dir, i, slide, t)


def _validate_slide_head(deck, layout, theme, deck_dir, i, slide, t, types_known, common_keys):
    """_validate_slide の前半: 内容フィールドの型・未知のキー・style の領域名と値。スタイルの解決より前。"""
    pre = f"{i + 1}枚目（type={t}）: "
    # slide.style は必ずオブジェクト（またはキー欠落）。null・文字列・配列だと deep_merge が
    # 解決済みスタイルを丸ごと非dict値に置き換えてしまい、後段の全処理がクラッシュする。
    if "style" in slide and not isinstance(slide["style"], dict):
        fail(f"{pre}style はオブジェクト（{{ \"body\": {{ \"size\": 20 }} }}）である必要があります"
             f"（{dschema._vtype(slide['style'])}が書かれています）")
    _prune_and_coerce(slide, t)
    _check_density_autofit(slide, pre)
    # 内容フィールドの型（配列のはずが文字列、要素が数値や null など）
    shape_issues = dschema.check_slide_shapes(slide, t)
    _report_issues(shape_issues, pre)
    if t == "table":
        _normalize_table_rows(slide, pre)
    # 打ち間違いのキー
    _report_issues(dschema.unknown_slide_keys(slide, t), pre)

    missing_text: list = []
    _check_bullet_items(slide.get("bullets"), "bullets", pre, missing=missing_text)
    for side in ("left", "right"):
        if isinstance(slide.get(side), dict):
            _check_bullet_items(slide[side].get("bullets"), f"{side}.bullets", pre, missing=missing_text)
    for ci, card in enumerate(slide.get("cards") or []):
        if isinstance(card, dict):
            _check_bullet_items(card.get("items"), f"cards[{ci}].items", pre, missing=missing_text)
    for si, stp in enumerate(slide.get("steps") or []):
        if isinstance(stp, dict):
            _check_bullet_items(stp.get("items"), f"steps[{si}].items", pre, missing=missing_text)
    _warn_missing_text(missing_text, pre)
    _warn_empty_body(slide, i, t)

    slide_style = slide.get("style", {})

    # slide.style のキー名タイポ検証（M-75）
    # variant が足す領域（panel・deco1 など）も style で調整できる
    types_t = hero.deep_merge(layout["types"][t], hero.variant_layer(layout, t, hero.variant_of(layout, deck, slide)))
    allowed = common_keys | set(types_t.keys())
    for key in slide_style:
        if key not in allowed:
            hint = difflib.get_close_matches(key, allowed, n=1)
            hint_s = f"（候補: {hint[0]}）" if hint else ""
            warn(f"{i + 1}枚目（type={t}）: style の '{key}' は {t} の領域名ではありません{hint_s}"
                 f" → 使える領域: {' / '.join(types_t.keys())}（共通: {' / '.join(common_keys)}）。"
                 f"領域名を直す")
    # 領域の中のプロパティ名・値の型・範囲
    _validate_style_values(slide_style, "style", types_t, layout.get("common", {}), pre)
    if t == "composite" and "blocks" in slide_style:
        _validate_block_defaults_style(slide_style["blocks"], "style.blocks", layout, pre)


def _check_partial_override_bleed(deck, slide, st, label: str):
    """style / meta.layout_overrides に x・w（または y・h）の片方だけを書き、もう片方は既定値のままの領域が、
    合わせるとスライドの外へ出るときに知らせる（既定の位置・幅はバージョンで変わることがある。両方書けば動かない）。"""
    for region, props in autofit.explicit_props(deck, slide).items():
        r = st.get(region)
        if not isinstance(r, dict):
            continue
        for pos, size, limit, name in (("x", "w", CANVAS_W, "幅"), ("y", "h", CANVAS_H, "高さ")):
            if (pos in props) == (size in props):
                continue                      # 両方書いた（意図した配置）か、どちらも書いていない
            a, b = r.get(pos), r.get(size)
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b)):
                continue
            if a + b > limit + 0.5:
                given, other = (pos, size) if pos in props else (size, pos)
                warn(f"{label}: style の {region}.{given} だけが指定され、{other} は既定値（{r[other]:g}）のままのため、"
                     f"{pos} + {size} = {a + b:g} がスライドの{name}（{limit}）を超えます"
                     f" → {region} の {pos} と {size} を両方書く（片方だけだと、もう片方は既定値に従います）")


def _validate_slide_tail(deck, layout, theme, deck_dir, i, slide, t, st_fn=None):
    """_validate_slide の後半（スタイル解決より後）。合成スライドのブロックは、ブロックの矩形で解決したスタイルを st_fn で渡す。"""
    if t == "pattern":
        # 自動フィットは frame:"full" の型では見出し・結論帯を測らない（描かれないため）。枠の種類をスライドに控える
        try:
            _pat = pat_e.load_pattern(slide.get("pattern"), deck_dir)
        except pat_e.PatternError:
            _pat = None
        if _pat is not None:
            slide["_pattern_frame"] = pat_e.frame_of(_pat)
        else:
            slide.pop("_pattern_frame", None)

    st = st_fn() if st_fn is not None else resolve_style(layout, deck, slide)
    if st_fn is None:
        _check_partial_override_bleed(deck, slide, st, f"{i + 1}枚目（type={t}）")

    if t in COMPOSITE_TYPES:
        _validate_composite_tail(deck, layout, theme, deck_dir, i, slide, st)
    if t == "split":
        for _code, _text in hero.panel_plan(slide, st, pe.Ctx(theme))["issues"]:
            (warn if _code == "panel-overflow" else note)(_text.replace("{label}", f"{i + 1}枚目（type=split）"))

    if engine_registry.has(t):
        engine_registry.validate_slide(slide, i, fail, warn)      # A 型タイプ（提案書系・kpi・chart）は登録表の検証
    elif t == "cards":
        pe.validate(slide, i, fail, warn)   # アイコン指定の確認
        hero.validate_cards(slide, f"{i + 1}枚目（type=cards）", st.get("grid"), fail, warn)   # emphasis / span

    if t == "pattern":
        # 色・スロットの検証は pattern_engine が行う（展開結果を canvas の検証にも通す）。見出し骨格の色（st）だけここで見る
        pat_e.validate(slide, i, deck_dir, fail, warn, theme, rect_w=pe.body_region(slide, st).get("w"), rect_h=pe.body_region(slide, st).get("h"))   # 狭い・短い矩形（合成ブロックの半幅・上下 2 段など）では型の narrow 構図で検査し、描かれる文字の大きさも見る
        _pat = pat_e.load_pattern(slide.get("pattern"), deck_dir)
        if _pat is not None and pat_e.frame_of(_pat) == "body":
            _fails, _warns = pat_e.body_rect_problems(slide, _pat, pe.body_region(slide, st), in_block="_block" in slide)
            for m in _fails:
                fail(f"{i + 1}枚目（type=pattern, pattern={slide.get('pattern')}）: {m}")
            for m in _warns:
                warn(f"{i + 1}枚目（type=pattern, pattern={slide.get('pattern')}）: {m}")
        issues = []
        _walk_colors(st, "", theme, i, t, issues)
        if issues:
            fail(issues[0])
        _check_overflow(slide, st, i, t)
        return

    if t == "canvas":
        # canvas は色を hex / {color, alpha} / gradient / pattern で直接持つため、専用の検証のみ行う
        ce.validate_canvas(slide, i, fail, warn, deck_dir)
        bg = slide.get("background", "#FFFFFF")
        if not (isinstance(bg, str) and _HEX_RE.match(bg)):
            fail(f"{i + 1}枚目（type=canvas）: background は #RRGGBB で指定してください（'{bg}'）")
        return

    # 色検証: 解決済みスタイル辞書と、スライド生データ（bullets の color 等）の両方を走査
    issues: list = []
    _walk_colors(st, "", theme, i, t, issues)
    _walk_colors(slide, "", theme, i, t, issues)
    if issues:
        fail(issues[0])

    if t == "table":
        cols = slide.get("columns", [])
        if not cols:
            fail(f"{i + 1}枚目（type=table）: columns（列見出しの配列）が空か書かれていません"
                 f" → \"columns\": [\"項目\", \"内容\"] のように1つ以上書く（\"colums\" など打ち間違いも確認）")
        for ridx, row in enumerate(slide.get("rows", [])):
            if len(row) != len(cols):
                fail(f"{i + 1}枚目（type=table）: {ridx + 1}行目のセル数（{len(row)}）が "
                     f"columns 数（{len(cols)}）と一致しません")
            # セルの url はスキーム許可リストで検証する。javascript: 等を href に
            # 出すと XSS になるため、黙って無視せずビルド時点でエラーにして気付かせる。
            for cidx, cell in enumerate(row):
                if isinstance(cell, dict) and cell.get("url") and not is_allowed_link_url(cell["url"]):
                    fail(f"{i + 1}枚目（type=table）: {ridx + 1}行{cidx + 1}列目の url に"
                         f"使用できないリンク先が指定されています: '{cell['url']}'"
                         f"（使用できるのは {' / '.join(ALLOWED_LINK_SCHEMES)} のみ）")
        widths = st.get("table", {}).get("col_widths")
        _check_col_widths(widths, i, t, len(cols))

    if t == "status_table":
        cols = slide.get("columns", [])
        if len(cols) < 3:
            fail(f"{i + 1}枚目（type=status_table）: columns は「ラベル列・状況列・内容列1つ以上」の3つ以上が必要です")
        rows = slide.get("rows", [])
        if not isinstance(rows, list):
            fail(f"{i + 1}枚目（type=status_table）: rows は配列（リスト）で指定してください")
        for ridx, row in enumerate(rows):
            if not isinstance(row, dict):
                fail(f"{i + 1}枚目（type=status_table）: {ridx + 1}行目は "
                     f"{{\"label\", \"status\", \"cells\"}} のオブジェクトで指定してください")
            cells = row.get("cells", [])
            if not isinstance(cells, list) or len(cells) != len(cols) - 2:
                fail(f"{i + 1}枚目（type=status_table）: {ridx + 1}行目の cells 数が "
                     f"内容列の数（columns - 2 = {len(cols) - 2}）と一致しません")
            for c in cells:
                if not isinstance(c, list):
                    fail(f"{i + 1}枚目（type=status_table）: {ridx + 1}行目の cells の各要素は配列で指定してください")
            color = status_color(slide, row.get("status"))
            if not is_color_value(theme, color):
                fail(f"{i + 1}枚目（type=status_table）: {ridx + 1}行目の status '{row.get('status')}' が "
                     f"凡例の key・テーマトークン・#hex のいずれでもありません")
        _check_col_widths(st.get("table", {}).get("col_widths"), i, t, len(cols))

    if t in ("image", "image_text"):
        _validate_image_path(slide, i, t, deck_dir)

    if t == "matrix":
        quadrants = slide.get("quadrants", [])
        if not isinstance(quadrants, list):
            fail(f"{i + 1}枚目（type=matrix）: quadrants は配列（リスト）で指定してください")
        n = len(quadrants)
        if n != 4:
            warn(f"{i + 1}枚目（type=matrix）: quadrants は4つの想定ですが{n}個指定されています"
                 f"（5個以上は無視され、4個未満は空の象限になります）")

    if t == "cards":
        columns = slide.get("columns")
        if columns is not None and columns < 1:
            warn(f"{i + 1}枚目（type=cards）: columns が {columns} です。1 列として描きます → 1 以上の整数にする")

    if t == "swimlane":
        _validate_swimlane(slide, i, t)
        _report_diagnostics(swimlane_geometry(slide, st, i + 1).get("diagnostics", []), i, t,
                            geometry_only=True)

    if t in GRID_DIAGRAM_TYPES:
        _report_diagnostics(de.validate_grid_diagram(slide, t), i, t)
        geo = dscale.layout_grid(slide, t, st["diagram"], [])
        _report_diagnostics(geo["diagnostics"], i, t, geometry_only=True)

    if t == "sequence":
        diags = []
        dscale.layout_seq(slide, st["diagram"], diags)
        _report_diagnostics(diags, i, t)

    if t == "schedule":
        _report_diagnostics(se.validate_schedule(slide), i, t)
        _report_diagnostics(se.layout_schedule(slide, st["chart"])["diagnostics"], i, t,
                            geometry_only=True)

    _check_overflow(slide, st, i, t)


def fit_code_size(code: str, r: dict):
    """コード領域に収まるフォントサイズを計算（HTML/PPTX 共通ロジック。計算本体は autofit.code_fit）。"""
    res = autofit.code_fit(code, r)
    return res["size"], res["lines"]


# 表セルのリンク（HTML の href / PPTX の外部ハイパーリンク）に出力してよい URL スキームの
# 許可リスト。esc() は < > & " ' を実体参照に変換するが、スキームそのものは無害化できない。
# javascript: / data: / vbscript: などをそのまま href に載せると、生成した HTML を開いた人の
# 画面で任意のスクリプトが動く（XSS）ため、href に出す直前に urlparse でスキームを取り出し、
# この許可リストに無いものはリンクにせず通常の文字列セルとして出力する。
ALLOWED_LINK_SCHEMES = ("http", "https", "mailto")
# セル全体が URL のときに自動リンク化するスキーム（明示指定の url より狭い＝
# references/schema/basic.md の table 節「セル全体が http:// または https:// のURLなら自動リンク」に対応）。
AUTOLINK_SCHEMES = ("http", "https")


def url_scheme(value) -> str:
    """value をリンク先 URL として解釈できるときに小文字のスキームを返す（不可なら ""）。

    空白・制御文字を含む文字列は URL として扱わない。ブラウザは href 内のタブや改行を
    取り除いてから解釈するため、"java<改行>script:..." のような細工を素通しさせないため。
    """
    text = str(value)
    if not text or any(c.isspace() or ord(c) < 0x20 for c in text):
        return ""
    try:
        parsed = urlparse(text)
    except ValueError:  # 壊れた IPv6 リテラル等、urlparse が解釈できない文字列
        return ""
    scheme = parsed.scheme.lower()
    if scheme in ("http", "https") and not parsed.netloc:
        return ""  # "https:///path" のようにホストが無いものはリンクにしない
    if scheme == "mailto" and not parsed.path:
        return ""  # "mailto:" だけの空アドレス
    return scheme


def is_http_url(value) -> bool:
    """セル値全体が自動リンク化の対象（HTTP(S) URL）かどうか。"""
    return url_scheme(value) in AUTOLINK_SCHEMES


def is_allowed_link_url(value) -> bool:
    """{"text": ..., "url": ...} の url をリンクとして出力してよいかどうか。"""
    return url_scheme(value) in ALLOWED_LINK_SCHEMES


def table_cell_parts(value):
    """Normalize a table cell into visible text and an optional external URL."""
    if value is None:
        return "", None
    if isinstance(value, dict):
        text = str(value.get("text", ""))
        url = value.get("url")
        return text, str(url) if url and is_allowed_link_url(url) else None
    text = str(value)
    return text, text if is_http_url(text) else None


def _cell_tone_color(theme, tr, cell, bg=None):
    """セルの tone（意味の色）に対応する文字色。tone が無ければ None。
    bg（セルの地の色 hex）が分かるときは、地の上で 4.5:1 に満たない tone 色を同じ色味のまま濃い側へ寄せる
    （強調行の塗り・縞の行の上で good / warn / accent が読めなくなるのを避ける。color_pick.readable_on）。"""
    tone = cell.get("tone") if isinstance(cell, dict) else None
    if tone not in autofit.TONES:
        return None
    c = col(theme, (tr.get("tone_colors") or {}).get(tone, tone))
    return cp.readable_on(c, bg) if bg else c


def table_auto_widths(cols, rows, tr, data=None) -> list:
    """table の col_widths が無いときの列幅（px の配列。合計 = tr["w"]）。
    ブラウザの <table width:100%>（自動レイアウト）が決める幅を模擬する: 各列の最小幅（それ以上縮められない最長の
    単位。和文は 1 文字・英数字は 1 語）と最大幅（折り返さない 1 行の幅）を文字幅の実測で出し、
    最大幅の合計が入れば余りを最大幅に比例して配り、入らなければ最小幅に「最大 − 最小」の比で上乗せする。
    PPTX は列幅を明示するしかない（以前は等分で、HTML と食い違っていた）。"""
    data = data or {}
    ncols = len(cols)
    if ncols == 0:
        return []
    pad = 2 * tr.get("pad_x", 16)
    mins = [0.0] * ncols
    maxs = [0.0] * ncols

    def measure(j, text, size, bold):
        lines = str(text).split("\n") or [""]
        wmax = max((sum(ja_text.char_em(c, None, bold) for c in ln) * size for ln in lines), default=0.0)
        wmin = 0.0
        for ln in lines:
            for tok in ja_text._tokens(ln, marker_atomic=False):
                wmin = max(wmin, sum(ja_text.char_em(c, None, bold) for c in tok) * size)
        mins[j] = max(mins[j], wmin + pad)
        maxs[j] = max(maxs[j], wmax + pad)

    for j, name in enumerate(cols):
        measure(j, name, tr["header_size"], True)
    for i, row in enumerate(rows):
        strong_row = bool(data.get("total_row")) and i == len(rows) - 1
        for j, val in enumerate(row[:ncols]):
            measure(j, table_cell_parts(val)[0], tr["cell_size"], strong_row or (bool(data.get("row_header")) and j == 0))
    total = float(tr["w"])
    smin, smax = sum(mins), sum(maxs)
    if smax <= 0:
        return [total / ncols] * ncols
    if smax <= total:
        return [m + (total - smax) * m / smax for m in maxs]
    if smin >= total:
        return [m * total / smin for m in mins]
    k = (total - smin) / (smax - smin)
    return [lo + (hi - lo) * k for lo, hi in zip(mins, maxs)]


def svg_size(svg_text: str):
    """SVG の描画サイズを viewBox / width / height 属性から取得する。"""
    m = re.search(
        r'viewBox\s*=\s*"\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"',
        svg_text,
    )
    if m:
        return float(m.group(1)), float(m.group(2))
    wm = re.search(r'<svg[^>]*?\swidth\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    hm = re.search(r'<svg[^>]*?\sheight\s*=\s*"([\d.]+)(?:px)?"', svg_text)
    if wm and hm:
        return float(wm.group(1)), float(hm.group(1))
    return 1136.0, 440.0


def svg_to_png(svg_path: Path, out_png: Path, browser=None):
    """SVG を透過 PNG にラスタライズ（PPTX 埋め込み用、2x 解像度）。
    browser に既存の Playwright Browser を渡すと、それを再利用する
    （M-25: デッキ内に複数 SVG があっても Chromium の起動は1回で済む）。
    省略時は従来どおり自分で Playwright/Chromium を起動して使い終わったら閉じる。"""
    svg_text = svg_path.read_text(encoding="utf-8")
    w, h = svg_size(svg_text)

    def _render(b):
        page = b.new_page(
            viewport={"width": max(1, int(w)), "height": max(1, int(h))},
            device_scale_factor=2,
        )
        try:
            page.set_content(
                "<!doctype html><style>html,body{margin:0;background:transparent}"
                "svg{display:block}</style>" + svg_text
            )
            page.wait_for_timeout(120)
            page.screenshot(path=str(out_png), omit_background=True,
                            clip={"x": 0, "y": 0, "width": w, "height": h})
        finally:
            page.close()

    if browser is not None:
        _render(browser)
        return
    sync_playwright = _import_sync_playwright()
    with sync_playwright() as pw:
        b = _launch_chromium(pw)
        try:
            _render(b)
        finally:
            b.close()


def flip_image_text(st: dict, bleed: bool) -> dict:
    """image_side: "left" の image_text。画像側と文字側の領域を左右反転する。bleed（画像を端まで）のときはタイトル・パネルも反転し、
    フッターは反転せずに文字の列の左端・右端にそろえる。"""
    keys = ("body", "img", "caption") + (("panel", "eyebrow", "title", "rule", "punch") if bleed else ())
    out = flip_regions(st, keys)
    if bleed:
        if isinstance(out.get("rule"), dict) and isinstance(out.get("title"), dict) and isinstance(st.get("rule"), dict):
            out["rule"]["x"] = out["title"]["x"] + (st["rule"]["x"] - st["title"]["x"])      # 罫線（縦帯・短い帯も）はタイトルの相対位置のまま
        if isinstance(out.get("footer_l"), dict) and isinstance(out.get("title"), dict):
            out["footer_l"]["x"] = out["title"]["x"]
        if isinstance(out.get("footer_r"), dict):
            out["footer_r"]["x"] = CANVAS_W - 72 - out["footer_r"]["w"]
    return out


def flip_regions(st: dict, keys) -> dict:
    """image_side: "left" 用に、指定領域の x をキャンバス中心で左右反転する。"""
    out = copy.deepcopy(st)
    for k in keys:
        r = out.get(k)
        if isinstance(r, dict) and "x" in r and "w" in r:
            r["x"] = CANVAS_W - r["x"] - r["w"]
    return out


# webp/tiff/bmp は python-pptx が扱えない、または PowerPoint との互換性が低いため
# PPTX 埋め込み時のみ PNG に変換する（M-72）。HTML はブラウザがそのまま表示できるので対象外。
PPTX_PNG_CONVERT_EXTS = (".webp", ".tiff", ".tif", ".bmp")


def _image_has_alpha(im) -> bool:
    if im.mode in ("RGBA", "LA"):
        return True
    if im.mode == "P":
        return "transparency" in im.info
    return False


def _resample_image_cache(deck_dir: Path, img_path: Path, target_w, target_h, force_convert: bool):
    """Pillow で画像をリサイズ・再圧縮／形式変換してキャッシュする
    （X-4: リサイズ・再圧縮キャッシュ、M-72: webp/tiff/bmp の PPTX 用 PNG 変換）。
    - target_w/target_h（表示枠 px）が指定されていれば、長辺が表示枠の2倍を超える場合のみ
      縮小する（拡大はしない）。アニメーション画像（複数フレームの gif/webp 等）はアニメーションが
      壊れるためリサイズ対象から除外する。
    - force_convert が真なら、サイズに関わらず PNG（または JPEG）へ変換したキャッシュを作る
      （webp/tiff/bmp を PPTX 埋め込み可能な形式にするため。アニメーションがある場合は先頭フレーム
      のみになる）。
    - アルファチャンネルが無ければ JPEG（品質85）、あれば PNG で保存する。
    - 条件を満たさない（リサイズも変換も不要）場合、または Pillow が無い／変換に失敗した場合は
      None を返す（呼び出し元は元ファイルをそのまま使う）。"""
    try:
        from PIL import Image as PILImage
    except ImportError:
        warn("Pillow が見つからないため画像のリサイズ・再圧縮・形式変換をスキップします"
             "（PowerPoint 非対応形式の画像がある場合は PPTX 生成に失敗する可能性があります。"
             "python-pptx を導入すれば通常 Pillow も同梱されます）")
        return None
    try:
        with PILImage.open(img_path) as im:
            is_animated = bool(getattr(im, "is_animated", False))
            im.load()
            w, h = im.size
            cap_w = target_w * 2 if target_w else None
            cap_h = target_h * 2 if target_h else None
            need_resize = (not is_animated) and cap_w and cap_h and (w > cap_w or h > cap_h)
            if not need_resize and not force_convert:
                return None
            has_alpha = _image_has_alpha(im)
            out_ext = ".png" if has_alpha else ".jpg"
            cache_dir = deck_dir / "build" / ".img-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            tag = f"{int(cap_w or 0)}x{int(cap_h or 0)}" if need_resize else "conv"
            # 元のファイル名（拡張子込み）とパスのハッシュをキャッシュ名に含める。stem のみだと
            # 同一フォルダ内の拡張子違い（foo.png/foo.jpg）や別フォルダの同名ファイルが
            # 衝突してキャッシュを取り違えるため。
            path_hash = hashlib.sha1(str(img_path.resolve()).encode("utf-8")).hexdigest()[:8]
            out_path = cache_dir / f"{img_path.stem}-{path_hash}-{tag}{out_ext}"
            if out_path.exists() and out_path.stat().st_mtime >= img_path.stat().st_mtime:
                return out_path
            frame = im
            if need_resize:
                ratio = min(cap_w / w, cap_h / h)
                if ratio < 1.0:
                    frame = im.resize((max(1, round(w * ratio)), max(1, round(h * ratio))), PILImage.LANCZOS)
            if out_ext == ".jpg":
                if frame.mode != "RGB":
                    frame = frame.convert("RGB")
                frame.save(out_path, "JPEG", quality=85)
            else:
                if frame.mode not in ("RGBA", "RGB", "LA", "P"):
                    frame = frame.convert("RGBA" if has_alpha else "RGB")
                frame.save(out_path, "PNG")
            return out_path
    except Exception as e:
        warn(f"画像 '{img_path.name}' のリサイズ・再圧縮・形式変換に失敗したため原本を使用します（{e}）")
        return None


def image_source(deck_dir: Path, rel_path: str, for_pptx: bool, browser=None,
                  target_w=None, target_h=None) -> Path:
    """image/image_text スライドの実ファイルを解決する。HTML の data URI・PPTX 埋め込みの
    両方から呼ばれる共通の入口（X-4）。
    - SVG: HTML はそのまま返す。PPTX はラスタライズして PNG 化しキャッシュする
      （browser に既存の Playwright Browser を渡すと svg_to_png() がそれを再利用する。M-25）。
    - webp/tiff/bmp: for_pptx のときだけ PNG 化する（M-72）。
    - それ以外（png/jpg/jpeg/gif 等）: target_w/target_h（表示枠 px）が指定されていれば、
      deck_dir/build/.img-cache/ に「長辺が表示枠の2倍」を上限にリサイズ・再圧縮した版を作り
      それを返す（X-4）。HTML と PPTX の両方が同じキャッシュを共有するため、リサイズは一度だけ行う。
      Pillow が無い、またはリサイズ・変換が不要なときは元ファイルをそのまま返す。"""
    img_path = deck_dir / rel_path
    ext = img_path.suffix.lower()
    if ext == ".svg":
        if not for_pptx:
            return img_path
        cache_dir = deck_dir / "build" / ".img-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        path_hash = hashlib.sha1(str(img_path.resolve()).encode("utf-8")).hexdigest()[:8]
        png = cache_dir / f"{img_path.stem}-{path_hash}.svg.png"
        if not png.exists() or png.stat().st_mtime < img_path.stat().st_mtime:
            svg_to_png(img_path, png, browser=browser)
        return png
    force_convert = for_pptx and ext in PPTX_PNG_CONVERT_EXTS
    cached = _resample_image_cache(deck_dir, img_path, target_w, target_h, force_convert)
    return cached if cached is not None else img_path


# ---------------------------------------------------------------------------
# HTML ビルド
# ---------------------------------------------------------------------------

def esc(s):
    return html_mod.escape(str(s), quote=True)


_ID_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.]*(?:-[A-Za-z0-9_.]+)+")


def esc_ids_nowrap(s):
    """esc() と同じだが、「D-04」「I-01」のような ID 風の語（英数字がハイフンでつながる 20 字以内）を折らない。
    ブラウザはハイフンの後ろで折り返すため（「D-／04」）、幅の見積もり（ja_text は 1 語として扱う）と食い違う（core-A-01）。"""
    s = str(s)
    out, pos_ = [], 0
    for m in _ID_TOKEN.finditer(s):
        if len(m.group(0)) > 20:
            continue
        out.append(esc(s[pos_:m.start()]))
        out.append(f'<span style="white-space:nowrap">{esc(m.group(0))}</span>')
        pos_ = m.end()
    out.append(esc(s[pos_:]))
    return "".join(out)


def pos(r, extra=""):
    s = (f"position:absolute;left:{r['x']}px;top:{r['y']}px;width:{r['w']}px;")
    if "h" in r:
        s += f"height:{r['h']}px;"
    return s + extra


def text_style(r, theme):
    s = f"font-size:{r['size']}px;color:{col(theme, r.get('color', 'text'))};"
    if r.get("weight") is not None:
        w = shp.weight_of(r)
        if w != 400 or r.get("bold"):
            s += f"font-weight:{w};"      # weight（形トークン）があればそれ。無ければ従来どおり bold → 700
    elif r.get("bold"):
        s += "font-weight:700;"
    tr = shp.tracking_of(r)
    if tr:
        s += f"letter-spacing:{tr:g}em;"
    if r.get("case") == "upper":
        s += "text-transform:uppercase;"
    if r.get("align"):
        s += f"text-align:{esc(r['align'])};"
    if r.get("line_height"):
        s += f"line-height:{r['line_height']};"
    return s


def fit_lines(st, region):
    """自動フィット（autofit）が「この領域は最大 N 行に収まる」と見積もったときの N（check_layout の data-max-lines 用）。無ければ None。"""
    info = ((st.get("_fit") or {}).get("info") or {}).get(region) if isinstance(st, dict) else None
    n = info.get("max_lines") if isinstance(info, dict) else None
    return n if isinstance(n, int) and n >= 1 else None


def div(r, theme, inner, extra="", font_family=None, heading=False, max_lines=None):
    """テキストの絶対配置 div を1つ作る。
    font_family: font_css() 済みの CSS 値を渡すと font-family を明示する（M-21/M-64/M-83: 見出し系に
    fonts.heading を適用する際に使う。未指定なら .slide の既定フォント（fonts.body）を継承する）。
    heading=True でその要素をスクリーンリーダー向けの見出しとしてマークする
    （role="heading" aria-level="1"。X-3: タイトル要素のアクセシビリティ対応）。
    font_family は font_css() が返す `"名前1", "名前2", ...` という値（二重引用符を含む）を
    そのまま style 属性（二重引用符区切り）に埋めると属性値がそこで打ち切られ、以降の
    プロパティが丸ごと無効になる（P0: code スライドの本文が判読不能になる不具合の原因）。
    esc() で `"` を `&quot;` にエスケープしてから埋め込む（ブラウザは属性値を文字参照
    展開してから CSS として使うため、フォント名自体は変わらない）。
    inner中の生の改行(\n)は<br>に変換する（P2: title等の明示的な改行がPPTXでは反映されるのに
    HTMLのwhite-space:normalではスペースに畳まれて消える食い違いの修正。呼び出し側は
    esc()済みの文字列を渡す前提なので、ここでの変換対象はエスケープ後に残る生の\nのみで、
    HTMLタグを誤って壊す心配はない）。"""
    ff = f"font-family:{esc(font_family)};" if font_family else ""
    attrs = ' role="heading" aria-level="1"' if heading else ""
    if max_lines:
        attrs += f' data-max-lines="{int(max_lines)}"'     # 自動フィットが保証した最大行数。check_layout の lines 検査が実測する
    if isinstance(inner, str) and "\n" in inner:
        inner = inner.replace("\n", "<br>")
    return f'<div{attrs} style="{pos(r)}{text_style(r, theme)}{ff}{extra}">{inner}</div>'


def _rule_drawable(r) -> bool:
    """罫線として描ける形か（x / y / w / h が揃っている。style.rule だけが残った断片は描かない）。"""
    return isinstance(r, dict) and all(isinstance(r.get(k), (int, float)) for k in ("x", "y", "w", "h"))


def rule_html(st, theme):
    """見出し骨格の罫線（rule.style = none のときは st に rule が無い）。"""
    return rect(st["rule"], theme) if _rule_drawable(st.get("rule")) else ""


def box_border_css(r, theme, key="border_color", default_w=1):
    """箱の枠線。r[key] があれば border_w（既定 1px。0 で枠なし）の実線。"""
    if not r.get(key):
        return ""
    w = r.get("border_w", default_w)
    if not w:
        return ""
    return f'border:{w:g}px solid {col(theme, r[key])};box-sizing:border-box;'


SHADOW_COLOR = shp.SHADOW_COLOR


def shadow_spec(r, theme):
    """箱の影（領域の shadow: "soft" のとき。パラメーターは theme.tokens.shadow）→ canvas の shadow 形式 {dx, dy, blur, color}。無ければ None。"""
    p = shp.shadow_params(theme.get("tokens"), r.get("shadow") if isinstance(r, dict) else None)
    if not p:
        return None
    return {"dx": p["dx"], "dy": p["dy"], "blur": p["blur"], "color": {"color": SHADOW_COLOR, "alpha": p["alpha"]}}


def box_shadow_css(r, theme):
    sh = shadow_spec(r, theme)
    if not sh:
        return ""
    return f'box-shadow:0 {sh["dy"]:g}px {sh["blur"]:g}px {ce.css_color(sh["color"])};'


def rtok(theme, name, default):
    """形トークン radius.<name>（px）。テーマに tokens が無い（単体テスト等）ときは default。"""
    return shp.tok((theme or {}).get("tokens"), "radius", name, default)


def label_weight(theme):
    """見出し・ラベル（カード見出し・STEP など）の太さ。classic は 700。"""
    return shp.tok(theme.get("tokens"), "weight", "label", 700)


def rect(r, theme, extra=""):
    fill = col(theme, r.get("fill", "accent"))
    radius = f"border-radius:{r['radius']}px;" if r.get("radius") else ""
    return f'<div style="{pos(r)}background:{fill};{radius}{extra}"></div>'


def bullets_html(items, r, theme):
    mk = col(theme, r.get("marker_color", "accent"))
    parts = [
        f'<ul style="margin:0;padding-left:{r["indent"]}px;list-style:disc;'
        f'font-size:{r["size"]}px;line-height:{r["line_height"]};'
        f'color:{col(theme, r["color"])};--mk:{mk};">'
    ]
    for it in items:
        li = f'font-size:{it["size"]}px;' if it.get("size") else ""
        li += f'color:{col(theme, it["color"])};' if it.get("color") else ""
        li += "font-weight:700;" if it.get("bold") else ""
        parts.append(f'<li style="margin-bottom:{r["gap"]}px;{li}">{esc(it["text"]).replace(chr(10), "<br>")}')
        if it["children"]:
            parts.append(
                f'<ul style="margin:{r["child_gap"]}px 0 0;padding-left:{r["indent"] - 6}px;'
                f'list-style:circle;font-size:{r["child_size"]}px;'
                f'color:{col(theme, r["child_color"])};">'
            )
            for c in it["children"]:
                cs = f'font-size:{c["size"]}px;' if c.get("size") else ""
                cs += f'color:{col(theme, c["color"])};' if c.get("color") else ""
                parts.append(f'<li style="margin-bottom:{r["child_gap"]}px;{cs}">{esc(c["text"]).replace(chr(10), "<br>")}</li>')
            parts.append("</ul>")
        parts.append("</li>")
    parts.append("</ul>")
    return "".join(parts)


def footer_html(st, deck, theme, page, total):
    out = ""
    if "footer_l" in st:
        out += div(st["footer_l"], theme, esc(deck.get("meta", {}).get("title", "")))
    if "footer_r" in st:
        out += div(st["footer_r"], theme, esc(st["footer_r"].get("text") or f"{page} / {total}"))
    return out


def img_box_html(r, mime, data, alt, src):
    """image / image_text の画像の HTML。radius.image が 0 なら従来どおり（枠いっぱいに contain）。
    角丸のときは、等比フィットした実際の画像の大きさに角丸をかける（枠に対する余白に丸みが付かないように）。"""
    rad = r.get("radius")
    if not rad:
        return (f'<div style="{pos(r)}"><img src="data:{mime};base64,{data}" alt="{alt}" '
                f'style="width:100%;height:100%;object-fit:contain;"></div>')
    fw, fh = fit_size_in(r, src)
    return (f'<div style="{pos(r)}display:flex;align-items:center;justify-content:center;">'
            f'<img src="data:{mime};base64,{data}" alt="{alt}" '
            f'style="width:{fw:.1f}px;height:{fh:.1f}px;border-radius:{rad:g}px;object-fit:contain;"></div>')


def fit_size_in(r, src):
    """枠 r（w, h）に画像 src を等比で収めたときの (幅, 高さ) px。読めなければ枠いっぱい。"""
    try:
        from PIL import Image
        with Image.open(src) as im:
            iw, ih = im.size
        k = min(r["w"] / iw, r["h"] / ih)
        return iw * k, ih * k
    except Exception:
        return float(r["w"]), float(r["h"])


def canvas_image_source(deck_dir: Path, browser=None):
    """canvas の kind:"image"（手書き canvas とパターンの画像スロット）が使う画像読み込み関数。
    build_deck.image_source（縮小・キャッシュ・webp 等の変換・SVG の PNG 化）を、canvas_engine の呼び方
    source(rel_path, for_pptx, w, h, fit) に合わせて包む。fit="cover" は枠を埋めるのに必要な倍率から縮小の上限を決める
    （細長い画像を枠の高さに合わせて縮めすぎて、拡大で荒れないように）。"""
    probed: dict = {}       # rel -> (幅, 高さ) / None（壊れている）/ "svg"。同じ画像を HTML と PPTX で何度も調べない

    def probe(rel):
        if rel in probed:
            return probed[rel]
        res = "svg"
        if not str(rel).lower().endswith(".svg"):
            try:
                from PIL import Image as PILImage
                with PILImage.open(Path(deck_dir) / rel) as im:
                    res = im.size
                    im.verify()           # 壊れた PNG / 途中で切れた JPEG をここで見つける
            except ImportError:
                res = "svg"               # Pillow が無ければ調べない（原本をそのまま使う）
            except Exception as e:      # noqa: BLE001  （UnidentifiedImageError・破損・読み取り失敗）
                warn(f"画像 '{rel}' を読み込めません（{type(e).__name__}）。ファイルが壊れているか、画像ではない可能性があります"
                     " → 画像ファイルを確かめて入れ直してください。灰色の枠で代用します")
                res = None
        probed[rel] = res
        return res

    def source(rel, for_pptx, w=None, h=None, fit="contain"):
        try:
            size = probe(rel)
            if size is None:
                return None           # canvas_engine が灰色の枠（alt つき）で代用する
            tw, th = w, h
            if fit == "cover" and w and h and isinstance(size, tuple):
                iw, ih = size
                k = max(w / iw, h / ih)       # 枠を埋める倍率
                tw, th = iw * k, ih * k
            return image_source(deck_dir, rel, for_pptx, browser, tw, th)
        except Exception as e:      # noqa: BLE001  （画像 1 枚の失敗でビルド全体を止めない。canvas_engine が灰色の枠で代用する）
            warn(f"画像 '{rel}' を読み込めませんでした（{type(e).__name__}: {e}）。灰色の枠で代用します")
            return None
    source.accepts_fit = True
    return source


def _pattern_needs_svg(slide, deck_dir) -> bool:
    """pattern スライドの PPTX 描画で SVG の PNG 化（共有ブラウザ）が要るか: 画像スロットの値が .svg、または型の要素に kind:"svg" がある"""
    try:
        pat = pat_e.load_pattern(slide.get("pattern"), deck_dir)
    except pat_e.PatternError:
        return False
    if pat is None:
        return False
    slots = slide.get("slots") if isinstance(slide.get("slots"), dict) else {}
    for name, d in (pat.get("slots") or {}).items():
        if isinstance(d, dict) and d.get("kind") == "image" and str(slots.get(name) or "").lower().endswith(".svg"):
            return True
        if isinstance(d, dict) and d.get("kind") == "image" and not slots.get(name) and str(d.get("default") or "").lower().endswith(".svg"):
            return True
    return '"kind": "svg"' in json.dumps(pat.get("elements") or [], ensure_ascii=False)


def resolve_pattern_slide(slide, st, deck, theme, deck_dir, page, total) -> dict:
    """type:"pattern" のスライドを描画用に展開する。戻り値 {"frame", "elements", "background", "pattern"}。
    - frame "full"（既定）: 型が 1280x720 全面を描く。見出し・フッターも型の中にある。
    - frame "body": 見出し骨格（eyebrow / title / rule / lead / フッター）は呼び出し側（chrome）が描く。
      ここでは本文領域（lead / 結論帯 / 出典の有無で変わる）に型を写し、結論帯・出典（common_parts）も足して返す。
    展開の警告は validate_deck（pattern_engine.validate）が出し済みなので、ここでは warn を渡さない（二重に出さない）。"""
    pat = pat_e.load_pattern(slide.get("pattern"), deck_dir)
    if pat is None:
        fail(f"{page}枚目（type=pattern）: パターン '{slide.get('pattern')}' が見つかりません"
             f" → 使えるパターン: {', '.join(pat_e.available_names(deck_dir))}")
    if pat_e.frame_of(pat) == "body":
        body = pe.body_region(slide, st)
        els = pat_e.pattern_block_elements(slide, pat, (body["x"], body["y"], body["w"], body["h"]), theme, deck, page, total)
        els += pe.common_parts(slide, st, pe.Ctx(theme), body)
        return {"frame": "body", "elements": els, "background": None, "pattern": pat.get("name", "")}
    els, bg = pat_e.expand(slide, pat, theme, deck, page, total)
    return {"frame": "full", "elements": els, "background": bg, "pattern": pat.get("name", "")}


def composite_block_elements(rb, theme, bk):
    """合成スライドの 1 ブロックの canvas 要素: (枠と小見出し, 合成専用ブロック[text / callout / image]の本文)。
    HTML と PPTX が同じものを描く。既存タイプのブロックの本文は、ここではなく html_slide_body(bare=True) / builders が描く。"""
    tc = pe.Ctx(theme)
    block = dict(rb["block"])
    block["_index"] = rb["index"]
    block["emphasis"] = rb["emph"]
    frame = comp.frame_elements(tc, rb["geo"], block, bk, shadow=shadow_spec(bk, theme), radius=bk.get("radius", 0) or 0)
    content = []
    if rb["native"]:
        bt, geo, reg = rb["type"], rb["geo"], rb.get("region") or {}
        if bt == "text":
            content = comp.text_elements(tc, geo["content"], block, reg, rb["fit"], rb["emph"])
        elif bt == "callout":
            content = comp.callout_elements(tc, geo["content"], block, reg, rb["fit"], rb["emph"])
        else:
            content = comp.image_elements(tc, block, geo["content"], reg, rtok(theme, "image", 0))
    return frame, content


def composite_block_html(rb, bk, deck, theme, deck_dir, page, total, img_src=None):
    """合成ブロック 1 つの HTML（data-block / data-block-type つきの display:contents の枠で包む。配置には影響しない）。
    rb は resolve_block の戻り値。S2d の split もこれでブロックを描ける（page / total は SVG の id の接頭辞とページ表示用）。"""
    frame_els, content_els = composite_block_elements(rb, theme, bk)
    inner = ce.canvas_html({"elements": frame_els + content_els}, image_source=img_src)
    if not rb["native"]:
        inner += html_slide_body(rb["bs"], rb["st"], deck, theme, deck_dir, page, total, bare=True,
                                 uid=f"{page}b{rb['index'] + 1}")
    return f'<div data-block="{rb["index"] + 1}" data-block-type="{esc(rb["type"])}" style="display:contents">{inner}</div>'


def composite_html(slide, st, deck, theme, deck_dir, page, total):
    """合成スライドの本文（ブロックごとの HTML をつなぐ）。"""
    bk = st.get("block") or {}
    img_src = canvas_image_source(deck_dir)
    return "".join(composite_block_html(rb, bk, deck, theme, deck_dir, page, total, img_src) for rb in st["_composite"]["blocks"])


def html_slide_body(slide, st, deck, theme, deck_dir, page, total, pattern_resolved=None, bare=False, uid=None):
    """スライド 1 枚の本文 HTML。bare=True は合成スライドのブロック用: 見出し骨格（eyebrow / title / rule / lead / フッター）を描かない。
    uid は SVG の id の接頭辞（同じ枚に図解が複数あるとき、矢じりの id が衝突しないよう呼び出し側が変える）。"""
    t = slide["type"]
    uid = uid if uid is not None else page
    fonts = theme["fonts"]
    parts = []
    # M-21/M-64/M-83: 見出し系要素（title/eyebrow/section.number/quote.text/col_heading/
    # cards・matrix の heading/steps の label/image_text の punch/closing.message）には
    # fonts.heading（未指定なら body）を適用する。PPTX 側の HEADING_FONT と同じ考え方。
    HEADING_FONT_CSS = font_css(fonts.get("heading") or fonts["body"])

    def chrome():
        if bare:
            return
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"]), font_family=HEADING_FONT_CSS))
        if "title" in st:       # split でタイトルが無いときは領域ごと無い
            parts.append(div(st["title"], theme, esc(slide.get("title", "")), font_family=HEADING_FONT_CSS, heading=True,
                              max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("lead") and "lead" in st:
            parts.append(div(st["lead"], theme, esc(slide["lead"]), max_lines=fit_lines(st, "lead")))
        parts.append(footer_html(st, deck, theme, page, total))

    def hero_html(extra=None):
        """主役系の下地（背景の画像・覆い・色面 → variant の panel → 飾り）。HTML と PPTX が同じ canvas 要素から描く。"""
        els = hero.hero_layers(st, slide.get("_bg"), theme.get("colors", {})) + (extra or [])
        if els:
            parts.append(ce.canvas_html({"elements": els}, image_source=canvas_image_source(deck_dir)))

    if t == "canvas":
        # 座標指定の自由配置。テーマのクロム（タイトル・罫線・フッター）は付けない
        parts.append(ce.canvas_html(slide, image_source=canvas_image_source(deck_dir)))

    elif t == "pattern":
        # 登録した構図（パターン）。frame:"body" は見出し骨格をプラグインが描き、本文だけ型が描く。frame:"full" は型が全面を描く
        r = pattern_resolved or resolve_pattern_slide(slide, st, deck, theme, deck_dir, page, total)
        if r["frame"] == "body":
            chrome()
        parts.append(ce.canvas_html({"elements": r["elements"]}, image_source=canvas_image_source(deck_dir)))

    elif t == "composite":
        # 合成スライド: 見出し骨格は 1 回だけ。ブロックごとに枠・小見出し・本文を、格子の矩形に描く
        chrome()
        parts.append(composite_html(slide, st, deck, theme, deck_dir, page, total))

    elif t == "split":
        # 非対称分割: 端まで届くパネル（色面か画像＋文字）と、残りの領域の見出し骨格・ブロック
        hero_html(hero.panel_plan(slide, st, pe.Ctx(theme))["els"])
        chrome()
        parts.append(composite_html(slide, st, deck, theme, deck_dir, page, total))

    elif engine_registry.has(t):
        # A 型タイプ（提案書系・kpi・chart）: レイアウトは各エンジンが canvas 要素として計算する（登録表。statement はクロムなし）
        if engine_registry.get(t).chrome:
            chrome()
        parts.append(ce.canvas_html({"elements": pe.layout(slide, st, theme)}, image_source=canvas_image_source(deck_dir)))

    elif t == "title":
        hero_html()
        parts.append(rect(st["bar"], theme))
        parts.append(div(st["title"], theme, esc(slide.get("title", "")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        if slide.get("subtitle"):
            parts.append(div(st["subtitle"], theme, esc(slide["subtitle"])))
        if slide.get("meta"):
            parts.append(div(st["meta"], theme, esc(slide["meta"])))

    elif t == "section":
        hero_html()
        if slide.get("number"):
            parts.append(div(st["number"], theme, esc(slide["number"]), font_family=HEADING_FONT_CSS))
        parts.append(div(st["title"], theme, esc(slide.get("title", "")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("subtitle"):
            parts.append(div(st["subtitle"], theme, esc(slide["subtitle"])))

    elif t == "bullets":
        chrome()
        # style.body.valign（既定 top）: "middle" で項目群を body 枠の縦中央に寄せる（項目数が
        # 少ないデッキでキャンバス下半分だけ空白になる問題への対応。two_column/matrix/cards と
        # 同じ考え方。PPTX 側は text_frame.vertical_anchor=MIDDLE で対応、こちらは実際の描画高さ
        # で自動的に中央寄せされる flex を使うため見積もり計算は不要）。
        body_valign = st["body"].get("valign", "top")
        body_extra = "display:flex;flex-direction:column;justify-content:center;" if body_valign == "middle" else ""
        parts.append(
            f'<div style="{pos(st["body"])}{body_extra}">'
            + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
            + "</div>"
        )

    elif t == "two_column":
        chrome()
        for side in ("left", "right"):
            box = st[side]
            colc = slide.get(side, {})
            radius = f"border-radius:{box.get('radius', 0)}px;"
            inner = ""
            hd = st["col_heading"]
            if colc.get("heading"):
                inner += (
                    f'<div style="font-size:{hd["size"]}px;color:{col(theme, hd["color"])};'
                    # P0: font_css() の戻り値は二重引用符を含むため esc() でエスケープしてから
                    # style 属性（二重引用符区切り）に埋め込む（そのまま埋めると属性値がここで
                    # 打ち切られ、font-weight/margin-bottom が丸ごと無効になる）。
                    f'font-family:{esc(HEADING_FONT_CSS)};'
                    f'font-weight:700;margin-bottom:{hd["gap_below"]}px;">{esc(colc["heading"])}</div>'
                )
            inner += bullets_html(norm_items(colc.get("bullets")), st["col_body"], theme)
            # style.left.valign / style.right.valign（references/schema/basic.md の two_column 節）: "middle" で
            # heading+bullets をまとめて箱の縦中央に寄せる。flex column なら実際に描画された
            # 高さで自動的に中央寄せされるため、estimate_lines() 等の見積もりが不要。
            valign = box.get("valign", "top")
            justify = "justify-content:center;" if valign == "middle" else ""
            border = box_border_css(box, theme).replace("box-sizing:border-box;", "") + box_shadow_css(box, theme)
            parts.append(
                f'<div style="{pos(box)}background:{col(theme, box["fill"])};{radius}{border}'
                f'padding:{box["pad"]}px;box-sizing:border-box;overflow:hidden;'
                f'display:flex;flex-direction:column;{justify}">{inner}</div>'
            )

    elif t == "table":
        chrome()
        tr = st["table"]
        cols = slide.get("columns", [])
        widths = tr.get("col_widths")
        colgroup = ""
        if widths:
            total_w = sum(widths)
            colgroup = "<colgroup>" + "".join(
                f'<col style="width:{w / total_w * 100:.2f}%;">' for w in widths
            ) + "</colgroup>"
        cells_pad = f"padding:{tr['pad_y']}px {tr['pad_x']}px;"
        html = [
            f'<div style="{pos(tr)}"><table style="width:100%;border-collapse:collapse;'
            f'{"table-layout:fixed;" if tr.get("_auto_widths") else ""}'      # 自動フィットが決めた列幅は固定レイアウトで（PPTX と同じ幅）
            f'line-height:{tr["line_height"]};">{colgroup}<thead><tr>'
        ]
        for c in cols:
            html.append(
                f'<th style="background:{col(theme, tr["header_fill"])};'
                f'color:{col(theme, tr["header_color"])};font-size:{tr["header_size"]}px;'
                f'text-align:left;font-weight:600;height:{tr["header_h"]}px;'
                f'{cells_pad}box-sizing:border-box;">{esc(c).replace(chr(10), "<br>")}</th>'
            )
        html.append("</tr></thead><tbody>")
        row_fills = tr.get("row_fills", {})
        for i, row in enumerate(slide.get("rows", [])):
            emph_row = i in set(slide.get("_row_emphasis") or [])
            if emph_row:
                bg = col(theme, tr.get("emphasis_fill", "highlight_fill"))
            elif str(i) in row_fills:
                bg = col(theme, row_fills[str(i)])
            else:
                bg = col(theme, tr["row_alt_fill"]) if i % 2 else col(theme, "background")
            html.append("<tr>")
            is_total = bool(slide.get("total_row")) and i == len(slide.get("rows", [])) - 1
            for j, cell in enumerate(row):
                is_label = bool(slide.get("row_header")) and j == 0
                cbg = (col(theme, tr.get("total_fill", "surface")) if is_total
                       else col(theme, tr.get("label_fill", "highlight_fill")) if is_label else bg)
                tone = _cell_tone_color(theme, tr, cell, cbg)
                cweight = "font-weight:700;" if (is_total or is_label or emph_row or tone) else ""
                ccolor = col(theme, tr.get("label_color", "heading_text")) if (is_total or is_label) else col(theme, tr["cell_color"])
                if tone and not (is_total or is_label):
                    ccolor = tone
                visible_text, cell_url = table_cell_parts(cell)
                cell_text = esc_ids_nowrap(visible_text).replace("\n", "<br>")   # セル内の改行は PPTX（a:br）と同じく改行にする
                if cell_url:
                    cell_text = (
                        f'<a href="{esc(cell_url)}" target="_blank" rel="noopener noreferrer" '
                        'style="color:inherit;text-decoration:underline;'
                        f'text-underline-offset:2px;">{cell_text}</a>'
                    )
                html.append(
                    f'<td style="background:{cbg};color:{ccolor};{cweight}'
                    f'font-size:{tr["cell_size"]}px;height:{tr["row_h"]}px;{cells_pad}'
                    f'box-sizing:border-box;border-bottom:1px solid {col(theme, tr.get("border_color", "border"))};">{cell_text}</td>'
                )
            html.append("</tr>")
        html.append("</tbody></table></div>")
        parts.append("".join(html))

    elif t == "status_table":
        chrome()
        lg = st["legend"]
        legend = status_legend(slide)
        if legend:
            bc = col(theme, lg["border_color"])
            row_h = lg["h"] / len(legend)
            legend_title = esc(slide.get("legend_title", STATUS_LEGEND_TITLE)).replace("\n", "<br>")
            out = [f'<div style="{pos(lg)}border:1px solid {bc};box-sizing:border-box;">']
            out.append(
                f'<div style="position:absolute;left:0;top:0;width:{lg["title_w"]}px;height:100%;'
                f'background:{col(theme, lg["title_fill"])};color:{col(theme, lg["title_color"])};'
                f'font-size:{lg["size"] + 1}px;font-weight:700;line-height:{lg["line_height"]};'
                f'font-family:{esc(HEADING_FONT_CSS)};display:flex;align-items:center;justify-content:center;'
                f'text-align:center;">{legend_title}</div>'
            )
            for k, it in enumerate(legend):
                top = k * row_h
                bt = f"border-top:1px solid {bc};" if k else ""
                out.append(
                    f'<div style="position:absolute;left:{lg["title_w"]}px;top:{top:.1f}px;width:{lg["symbol_w"]}px;'
                    f'height:{row_h:.1f}px;{bt}border-left:1px solid {bc};box-sizing:border-box;display:flex;'
                    f'align-items:center;justify-content:center;font-size:{lg["symbol_size"]}px;'
                    f'color:{col(theme, it.get("color", "text"))};">●</div>'
                    f'<div style="position:absolute;left:{lg["title_w"] + lg["symbol_w"]}px;top:{top:.1f}px;'
                    f'width:{lg["w"] - lg["title_w"] - lg["symbol_w"]}px;height:{row_h:.1f}px;{bt}'
                    f'border-left:1px solid {bc};box-sizing:border-box;display:flex;align-items:center;'
                    f'padding:0 {lg["pad_x"]}px;font-size:{lg["size"]}px;line-height:{lg["line_height"]};'
                    f'background:{col(theme, lg["fill"])};color:{col(theme, lg["color"])};">{esc(it.get("label", ""))}</div>'
                )
            out.append("</div>")
            parts.append("".join(out))

        tr = st["table"]
        geo = status_table_geometry(slide, st)
        bc = col(theme, tr["border_color"])
        xs, ws = geo["xs"], geo["ws"]

        def cell_div(j, y, h, fill, inner, extra=""):
            return (f'<div style="position:absolute;left:{xs[j]:.1f}px;top:{y:.1f}px;width:{ws[j]:.1f}px;'
                    f'height:{h:.1f}px;background:{col(theme, fill)};border:1px solid {bc};'
                    f'margin:-0.5px 0 0 -0.5px;box-sizing:border-box;overflow:hidden;{extra}">{inner}</div>')

        center = "display:flex;align-items:center;justify-content:center;text-align:center;"
        for j, name in enumerate(slide.get("columns", [])):
            parts.append(cell_div(
                j, geo["header_y"], tr["header_h"], tr["header_fill"], esc(name),
                f'{center}color:{col(theme, tr["header_color"])};font-size:{tr["header_size"]}px;font-weight:700;'))
        mk = col(theme, tr["marker_color"])
        for r in geo["rows"]:
            row = r["row"]
            parts.append(cell_div(
                0, r["y"], r["h"], tr["label_fill"], esc(row.get("label", "")),
                f'{center}color:{col(theme, tr["label_color"])};font-size:{tr["label_size"]}px;'))
            status = row.get("status")
            label = next((it.get("label", "") for it in status_legend(slide) if it.get("key") == status), "")
            parts.append(cell_div(
                1, r["y"], r["h"], tr["status_fill"],
                f'<span title="{esc(label)}" style="color:{col(theme, status_color(slide, status))};'
                f'font-size:{tr["status_size"]}px;line-height:1;">●</span>', center))
            for j, paras in enumerate(r["cells"]):
                body = []
                for lv, text in paras:
                    left = tr["indent"] * (lv + 1)
                    marker = tr["check_char"] if lv == 0 else tr["bullet_char"]
                    deco = "text-decoration:underline;" if lv == 0 and tr.get("heading_underline") else ""
                    body.append(
                        f'<div style="position:relative;padding-left:{left}px;margin-bottom:{tr["item_gap"]}px;">'
                        f'<span style="position:absolute;left:{left - tr["indent"]}px;color:{mk};">{esc(marker)}</span>'
                        f'<span style="{deco}">{esc(text)}</span></div>'
                    )
                parts.append(cell_div(
                    j + 2, r["y"], r["h"], tr["cell_fill"], "".join(body),
                    f'padding:{tr["pad_y"]}px {tr["pad_x"]}px;font-size:{tr["cell_size"]}px;'
                    f'line-height:{tr["line_height"]};color:{col(theme, tr["cell_color"])};'))

    elif t == "code":
        chrome()
        r = st["code"]
        size, _lines = fit_code_size(slide.get("code", ""), r)
        radius = f"border-radius:{r.get('radius', 0)}px;"
        parts.append(
            f'<pre style="{pos(r)}margin:0;background:{col(theme, r["fill"])};{radius}'
            f'padding:{r["pad"]}px;box-sizing:border-box;overflow:hidden;">'
            # P0: font_css() は二重引用符を含む値を返すため esc() でエスケープしてから style
            # 属性に埋める（そのまま埋めると属性値がここで打ち切られ、font-size/line-height/
            # color が丸ごと無効になり、コード本文が背景とほぼ同色で判読不能になっていた）。
            f'<code style="font-family:{esc(font_css(fonts["code"], mono=True))};font-size:{size}px;'
            f'line-height:{r["line_height"]};color:{col(theme, r["color"])};">'
            f"{esc(slide.get('code', ''))}</code></pre>"
        )

    elif t == "quote":
        hero_html()
        if st["mark"].get("w") and st["mark"].get("h") and not hero.mark_is_vector(st):
            parts.append(div(st["mark"], theme, "“"))
        parts.append(div(st["text"], theme, esc(slide.get("text", "")), font_family=HEADING_FONT_CSS))
        if slide.get("attribution"):
            parts.append(div(st["attribution"], theme, "— " + esc(slide["attribution"])))

    elif t == "image":
        bleed = slide.get("fit") == "bleed"
        hero_html()         # fit: bleed は全面の画像＋覆い、caption_position: band は下帯（variant の飾り）
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"]), font_family=HEADING_FONT_CSS))
        if slide.get("title"):
            parts.append(div(st["title"], theme, esc(slide["title"]), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
            parts.append(rule_html(st, theme))
        r = st["img"]
        if not bleed:
            # X-4/M-72: image_source() を通す（HTML/PPTX 共通のリサイズ・再圧縮キャッシュ）。
            src = image_source(deck_dir, slide["path"], False, target_w=r.get("w"), target_h=r.get("h"))
            mime = mimetypes.guess_type(src.name)[0] or "image/png"
            data = base64.b64encode(src.read_bytes()).decode()
            alt = esc(slide.get("caption") or slide.get("title") or "")  # X-3
            parts.append(img_box_html(r, mime, data, alt, src))
        if slide.get("caption"):
            parts.append(div(st["caption"], theme, esc(slide["caption"])))
        parts.append(footer_html(st, deck, theme, page, total))

    elif t == "image_text":
        bleed = slide.get("bleed") is True
        if slide.get("image_side") == "left":
            st = flip_image_text(st, bleed)
        hero_html()         # bleed: true は画像を端まで届かせる（canvas の画像要素。cover）
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"]), font_family=HEADING_FONT_CSS))
        parts.append(div(st["title"], theme, esc(slide.get("title", "")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("punch"):
            parts.append(div(st["punch"], theme, esc(slide["punch"]), font_family=HEADING_FONT_CSS, max_lines=fit_lines(st, "punch")))
        parts.append(
            f'<div style="{pos(st["body"])}">'
            + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
            + "</div>"
        )
        r = st["img"]
        if not bleed:
            src = image_source(deck_dir, slide["path"], False, target_w=r.get("w"), target_h=r.get("h"))
            mime = mimetypes.guess_type(src.name)[0] or "image/png"
            data = base64.b64encode(src.read_bytes()).decode()
            alt = esc(slide.get("caption") or slide.get("title") or "")  # X-3
            parts.append(img_box_html(r, mime, data, alt, src))
        if slide.get("caption"):
            parts.append(div(st["caption"], theme, esc(slide["caption"])))
        parts.append(footer_html(st, deck, theme, page, total))

    elif t == "closing":
        hero_html()
        parts.append(div(st["title"], theme, esc(slide.get("title", "")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("bullets"):
            parts.append(
                f'<div style="{pos(st["body"])}">'
                + bullets_html(norm_items(slide.get("bullets")), st["body"], theme)
                + "</div>"
            )
        if slide.get("message"):
            msg = closing_message_style(st, slide)  # M-38: body 直後に自動配置（PPTX と共通の計算式）
            parts.append(div(msg, theme, esc(slide["message"]), font_family=HEADING_FONT_CSS))

    elif t == "agenda":
        chrome()
        b = st["body"]
        items = norm_items(slide.get("items", []))
        num_start = slide.get("num_start", 0)
        row_h = b.get("row_h", 44); gap = b.get("gap", 10); num_w = b.get("num_w", 52)
        col_gap = b.get("col_gap", 56); pitch = row_h + gap
        R = max(1, int(b["h"] // pitch))
        N = len(items)
        cols = 1 if N <= R else min(b.get("max_cols", 2), -(-N // R))
        rows = -(-N // cols)
        col_w = (b["w"] - (cols - 1) * col_gap) / cols
        noff = (row_h - b.get("num_size", 24)) / 2
        toff = (row_h - b.get("text_size", 20)) / 2
        for i, it in enumerate(items):
            c = i // rows; r = i % rows
            x = b["x"] + c * (col_w + col_gap); y = b["y"] + r * pitch
            active = it.get("active")
            if active:
                a_border = (f'border:1px solid {col(theme, b["active_border"])};box-sizing:border-box;'
                            if b.get("active_border") else "")
                parts.append(f'<div style="{pos({"x": x-14, "y": y-3, "w": col_w+18, "h": row_h+6})}'
                             f'background:{col(theme, b.get("active_fill","surface"))};'
                             f'border-radius:{rtok(theme, "node_sm", 8):g}px;{a_border}"></div>')
            parts.append(div({"x": x, "y": y+noff, "w": num_w, "h": row_h, "size": b.get("num_size", 24),
                              "color": b.get("num_color", "accent"), "bold": True, "line_height": 1.1},
                             theme, f"{num_start+i+1:02d}"))
            inner = esc(it["text"])
            ty = y + toff
            if it.get("desc"):
                ds = b.get("desc_size", 14)
                ty = y + (row_h - b.get("text_size", 20) * 1.2 - ds * 1.35) / 2
                inner += (f'<br><span style="font-size:{ds}px;font-weight:400;'
                          f'color:{col(theme, b.get("desc_color", "muted"))};">{esc(it["desc"])}</span>')
            parts.append(div({"x": x+num_w, "y": ty, "w": col_w-num_w, "h": row_h, "size": b.get("text_size", 20),
                              "color": (b.get("active_color", "primary") if active else b.get("text_color", "text")),
                              "bold": bool(active) or bool(it.get("desc")), "line_height": 1.2}, theme, inner))

    elif t == "steps":
        chrome()
        b = st["body"]; steps = slide.get("steps", [])
        n = max(1, len(steps)); gap = b.get("gap", 20)
        card_w = (b["w"] - (n-1)*gap) / n
        header_h = b.get("header_h", 60); pad = b.get("pad", 16); radius = b.get("radius", 12)
        card_h = steps_card_height(b, steps, card_w)
        # fit="content" で縮めた分は行全体を少し上寄りの中央（40%）に置き、上下の余白を均す
        row_y = b["y"] + (b["h"] - card_h) * b.get("content_y_ratio", 0.4)
        card_border = box_border_css(b, theme, "card_border") + box_shadow_css(b, theme)
        for i, step in enumerate(steps):
            x = b["x"] + i * (card_w + gap)
            parts.append(f'<div style="{pos({"x": x, "y": row_y, "w": card_w, "h": card_h})}'
                         f'background:{col(theme, b.get("card_fill","surface"))};'
                         f'border-radius:{radius}px;{card_border}"></div>')
            if slide.get("header_style") == "arrow":
                parts.append(ce.canvas_html({"elements": [steps_arrow_header(i, n, x, row_y, card_w, gap, header_h, b, theme)]}))
            else:
                parts.append(f'<div style="{pos({"x": x, "y": row_y, "w": card_w, "h": header_h})}'
                             f'background:{col(theme, b.get("header_fill","primary"))};'
                             f'border-radius:{radius}px {radius}px 0 0;"></div>')
            parts.append(div({"x": x+pad, "y": row_y+9, "w": card_w-2*pad, "h": 18, "size": 13,
                              "color": b.get("num_color", "accent"), "bold": True, "weight": label_weight(theme)}, theme,
                              f"{i+1}" if b.get("_num_short") else f"STEP {i+1}"))
            parts.append(div({"x": x+pad, "y": row_y+28, "w": card_w-2*pad, "h": header_h-26,
                              "size": b.get("label_size", 18), "color": b.get("header_color", "on_primary"),
                              "bold": True, "weight": label_weight(theme), "line_height": 1.15}, theme, esc(step.get("label", "")),
                             font_family=HEADING_FONT_CSS))
            itemr = {"x": x+pad, "y": row_y+header_h+pad, "w": card_w-2*pad, "h": card_h-header_h-2*pad,
                     "size": b.get("item_size", 15), "gap": b.get("item_gap", 8), "color": b.get("item_color", "text"),
                     "line_height": 1.4, "marker_color": "accent", "child_size": b.get("child_size", 13),
                     "child_color": "muted", "indent": 16, "child_gap": b.get("child_gap", 4)}
            # style.body.valign（既定 top）: "middle" で items をカードの残り高さの中で縦中央寄せにする
            # （ヘッダー帯は動かさない。items だけが可変コンテンツのため flex で十分）。
            items_extra = "display:flex;flex-direction:column;justify-content:center;" if b.get("valign", "top") == "middle" else ""
            parts.append(f'<div style="{pos(itemr)}{items_extra}">'
                         + bullets_html(norm_items(step.get("items", [])), itemr, theme) + "</div>")
            if i < n-1 and slide.get("header_style") != "arrow":
                parts.append(div({"x": x+card_w, "y": row_y+card_h/2-18, "w": gap, "h": 36,
                                  "size": b.get("chevron_size", 28), "color": b.get("chevron_color", "accent"),
                                  "align": "center", "bold": True}, theme, "›"))

    elif t == "matrix":
        chrome()
        g = st["grid"]; ax = st.get("axis", {})
        gx, gy, gw, gh = g["x"], g["y"], g["w"], g["h"]
        gap = g.get("gap", 14); pad = g.get("pad", 18); radius = g.get("radius", 12)
        valign = g.get("valign", "top")  # M-37
        cw = (gw - gap) / 2; ch = (gh - gap) / 2
        quads = slide.get("quadrants", [])
        positions = [(gx, gy), (gx+cw+gap, gy), (gx, gy+ch+gap), (gx+cw+gap, gy+ch+gap)]
        g_border = box_border_css(g, theme) + box_shadow_css(g, theme)
        for qi, (qx, qy) in enumerate(positions):
            q = quads[qi] if qi < len(quads) else {}
            hi = q.get("highlight")
            fill = col(theme, g.get("hi_fill", "on_primary_soft") if hi else g.get("fill", "surface"))
            parts.append(f'<div style="{pos({"x": qx, "y": qy, "w": cw, "h": ch})}'
                         f'background:{fill};border-radius:{radius}px;{g_border}"></div>')
            # M-37: heading を含めたコンテンツ全体を象限中央に配置する（heading の y も
            # valign に応じて計算し直す。見出し固定＋本文だけセンタリングだと見出し直下に
            # 不自然な空白ができるため）。
            lay = _matrix_content_layout(q.get("body", ""), g, cw, ch, pad, valign)
            parts.append(div({"x": qx+pad, "y": qy+lay["head_y"], "w": cw-2*pad, "h": lay["head_h"],
                              "size": g.get("heading_size", 18),
                              "color": (g.get("hi_heading_color", "accent") if hi else g.get("heading_color", "primary")),
                              "bold": True, "weight": label_weight(theme), "line_height": 1.2}, theme, esc(q.get("heading", "")),
                             font_family=HEADING_FONT_CSS))
            parts.append(div({"x": qx+pad, "y": qy+lay["body_y"], "w": cw-2*pad, "h": lay["body_h"],
                              "size": g.get("body_size", 14), "color": g.get("body_color", "muted"),
                              "line_height": 1.4}, theme, esc(q.get("body", "")).replace("\n", "<br>")))
        xa = slide.get("x_axis", {}); ya = slide.get("y_axis", {})
        for ab in _matrix_axis_boxes(ax, gx, gy, gw, gh, xa, ya):
            parts.append(div(ab["region"], theme, esc(ab["text"])))

    elif t == "cards":
        chrome()
        g = st["grid"]; cards = slide.get("cards", [])
        geo = pe.cards_cells(len(cards), slide.get("columns"), g, hero.card_spans(slide))   # 配置は 1 か所（アイコン・PPTX・自動フィットと共通）
        pad = g.get("pad", 18); radius = g.get("radius", 12)
        valign = g.get("valign", "top")  # M-37
        for idx, card in enumerate(cards):
            x, y, cw, chh = geo["cells"][idx]
            cs = hero.card_style(g, hero.card_emphasis(card))          # 強調（emphasis）のカードは塗りと文字色が違う
            gc = hero.emph_grid(g, hero.card_emphasis(card))           # 強調のカードは文字も大きい（emph_scale）
            g_card = dict(g)
            g_card["border_color"] = cs["border_color"]
            if cs.get("border_w") is not None:
                g_card["border_w"] = cs["border_w"]
            g_border = box_border_css(g_card, theme) + box_shadow_css(g, theme)
            parts.append(f'<div style="{pos({"x": x, "y": y, "w": cw, "h": chh})}'
                         f'background:{col(theme, cs["fill"])};border-radius:{radius}px;{g_border}"></div>')
            # M-37: heading を含めたコンテンツ全体（実際に描画される段だけ）をカード中央に配置する
            # （heading の y も valign に応じて計算し直す。見出し固定＋本文/itemsだけセンタリング
            # だと見出し直下に不自然な空白ができるため）。
            lay = _cards_content_layout(card, gc, cw, chh, pad, valign)
            has_items = bool(card.get("items"))
            parts.append(div({"x": x+pad, "y": y+lay["head_y"], "w": cw-2*pad-autofit.card_icon_reserve(card, gc), "h": lay["head_h"],
                              "size": gc.get("heading_size", 19),
                              "color": cs["heading_color"], "bold": True, "weight": label_weight(theme), "line_height": 1.2},
                             theme, esc(card.get("heading", "")).replace("\n", "<br>"), font_family=HEADING_FONT_CSS))
            if card.get("body"):
                body_r = {"x": x+pad, "y": y+lay["body_y"], "w": cw-2*pad, "h": lay["body_h"],
                          "size": gc.get("body_size", 15), "color": cs["body_color"], "line_height": 1.4}
                parts.append(div(body_r, theme, esc(card["body"]).replace("\n", "<br>")))
            if has_items:
                itemr = {"x": x+pad, "y": y+lay["items_y"], "w": cw-2*pad, "h": lay["items_h"],
                         "size": gc.get("item_size", 14),
                         "gap": g.get("item_gap", 6), "color": cs["item_color"], "line_height": 1.35,
                         "marker_color": cs["marker_color"], "child_size": 12, "child_color": cs["item_color"] if cs.get("emphasized") else "muted",
                         "indent": 14, "child_gap": 4}
                parts.append(f'<div style="{pos(itemr)}">'
                             + bullets_html(norm_items(card["items"]), itemr, theme) + "</div>")

    elif t == "swimlane":
        chrome()
        f = st["flow"]
        geo = swimlane_geometry(slide, st, page)
        def cc(key, default):
            return col(theme, f.get(key, default))
        # lane bands (subtle stripes across full width)
        for ln in geo["lanes"]:
            bg = cc("lane_band_b", "surface") if ln["alt"] else col(theme, "background")
            parts.append(f'<div style="{pos({"x": f["x"], "y": ln["y"], "w": f["w"], "h": ln["h"]})}'
                         f'background:{bg};border-top:1px solid {cc("lane_border", "border")};"></div>')
        # group boxes (Lv1, vertical text)
        for gp in geo["groups"]:
            parts.append(f'<div style="{pos(gp)}display:flex;align-items:center;justify-content:center;'
                         f'background:{cc("group_fill","primary")};box-sizing:border-box;">'
                         f'<span style="writing-mode:vertical-rl;text-orientation:mixed;'
                         f'color:{cc("group_color","on_primary")};font-weight:700;font-size:{f.get("group_size",13)}px;">'
                         f'{esc(gp["label"])}</span></div>')
        # lane labels (Lv2)
        for ln in geo["lanes"]:
            parts.append(f'<div style="{pos({"x": ln["x"], "y": ln["y"], "w": ln["w"], "h": ln["h"]})}'
                         f'display:flex;align-items:center;justify-content:center;text-align:center;'
                         f'background:{cc("lane_fill","surface")};border:1px solid {cc("lane_border","border")};'
                         f'box-sizing:border-box;color:{cc("lane_color","text")};font-size:{f.get("lane_size",13)}px;'
                         f'padding:2px;line-height:1.2;">{esc(ln["label"])}</div>')
        # phase band
        for ph in geo["phases"]:
            parts.append(f'<div style="{pos(ph)}display:flex;align-items:center;justify-content:center;'
                         f'background:{cc("phase_fill","on_primary_soft")};box-sizing:border-box;'
                         f'color:{cc("phase_color","primary")};font-weight:700;font-size:{f.get("phase_size",14)}px;'
                         f'border-left:2px solid {col(theme,"background")};">{esc(ph["label"])}</div>')
        # edges (SVG overlay). 実線=作業の流れ / 破線=システム操作。配線・ラベル位置は
        # diagram_engine（共通ルーター）が計算し、描画は新図解タイプと同じ _edges_svg_html を使う
        # （variant: emphasis / security / dashed、ラベルは背景ピル付き）。
        # swimlane の style:"dashed" は edge_dashed_color ではなく従来どおり edge_color で描く。
        ed = dict(f)
        ed.setdefault("edge_dashed_color", f.get("edge_color", "text"))
        ed.setdefault("label_fill", "background")
        parts.append(_edges_svg_html(geo["edges"], ed, theme, f"sw{uid}", HEADING_FONT_CSS, layer="lines"))
        # nodes
        for nid, nd in geo["nodes"].items():
            parts.append(_sw_node_html(nd, theme, f))
        parts.append(_edges_svg_html(geo["edges"], ed, theme, f"sw{uid}", HEADING_FONT_CSS, layer="labels"))

    elif t in GRID_DIAGRAM_TYPES:
        chrome()
        parts.append(grid_diagram_html(slide, st, theme, t, uid, HEADING_FONT_CSS))

    elif t == "sequence":
        chrome()
        parts.append(sequence_html(slide, st, theme, uid, HEADING_FONT_CSS))

    elif t == "schedule":
        chrome()
        parts.append(schedule_html(slide, st, theme, HEADING_FONT_CSS))

    elif t == "swimlane_legend":
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"]), font_family=HEADING_FONT_CSS))
        parts.append(div(st["title"], theme, esc(slide.get("title", "凡例")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("lead") and "lead" in st:
            parts.append(div(st["lead"], theme, esc(slide["lead"]), max_lines=fit_lines(st, "lead")))
        a = st["area"]; sym = st.get("sym", {})
        entries = slide.get("items") or SWIMLANE_LEGEND
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 60); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 120)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, (shape, vk, label, desc) in enumerate(entries):
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h
            parts.append(_legend_symbol_html(shape, vk, x, y + row_h / 2, sym_w, theme, sym))
            tx = x + sym_w + 8
            parts.append(div({"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                              "size": a.get("label_size", 16), "color": "text", "bold": True,
                              "line_height": 1.15}, theme, esc(label)))
            parts.append(div({"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                              "size": a.get("desc_size", 13), "color": "muted"}, theme, esc(desc)))
        parts.append(footer_html(st, deck, theme, page, total))

    elif t == "diagram_legend":
        if slide.get("eyebrow") and "eyebrow" in st:
            parts.append(div(st["eyebrow"], theme, esc(slide["eyebrow"]), font_family=HEADING_FONT_CSS))
        parts.append(div(st["title"], theme, esc(slide.get("title", "凡例")), font_family=HEADING_FONT_CSS, heading=True,
                          max_lines=fit_lines(st, "title")))
        parts.append(rule_html(st, theme))
        if slide.get("lead") and "lead" in st:
            parts.append(div(st["lead"], theme, esc(slide["lead"]), max_lines=fit_lines(st, "lead")))
        a = st["area"]; d = st["diagram"]
        entries = slide.get("items") or []
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 56); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 140)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, entry in enumerate(entries):
            sample, label = entry[0], entry[1]
            desc = entry[2] if len(entry) > 2 else ""
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h
            parts.append(_diag_legend_sym_html(sample, x, y + row_h / 2, sym_w, d, theme, HEADING_FONT_CSS, uid=f"{page}-{i}"))
            tx = x + sym_w + 8
            parts.append(div({"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                              "size": a.get("label_size", 16), "color": "text", "bold": True,
                              "line_height": 1.15}, theme, esc(label)))
            parts.append(div({"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                              "size": a.get("desc_size", 13), "color": "muted"}, theme, esc(desc)))
        parts.append(footer_html(st, deck, theme, page, total))

    else:
        # 検証（validate_deck）で止まるので通常は来ない。描画器の無いタイプを空スライドにしないための防波堤
        fail(f"{page}枚目（type={t}）: このタイプの描画が登録されていません → build_deck.py の RENDERED_TYPES と描画の分岐に足す")

    over = pe.extras(slide, st, theme)
    if over:
        parts.append(ce.canvas_html({"elements": over}))
    return "".join(parts)


HTML_TEMPLATE = Template("""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$TITLE</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; background: #101014; overflow: hidden; }
#stage { position: absolute; top: 50%; left: 50%; width: ${W}px; height: ${H}px; }
.slide {
  position: absolute; inset: 0; width: ${W}px; height: ${H}px;
  font-family: $F_BODY;
  display: none; overflow: hidden;
  overflow-wrap: break-word;   /* URL・長い英単語は枠で折る（PPTX と同じ。はみ出し・スライド外への漏れを防ぐ） */
}
.slide.active { display: block; }
.slide li::marker { color: var(--mk, inherit); }
#toolbar {
  position: fixed; left: 0; right: 0; bottom: 0; height: 48px; z-index: 30;
  display: flex; align-items: center; justify-content: center; gap: 10px;
  background: #1b1b24; color: #c9c3d6; font: 13px/1 $F_BODY; user-select: none;
}
#toolbar button {
  height: 32px; min-width: 40px; padding: 0 14px; border: 1px solid #4a4458; border-radius: 4px;
  background: #2a2635; color: #fff; font: inherit; cursor: pointer;
}
#toolbar button:hover:not(:disabled) { background: $C_ACCENT; border-color: $C_ACCENT; }
#toolbar button:disabled { opacity: .35; cursor: default; }
#toolbar input {
  width: 56px; height: 32px; border: 1px solid #4a4458; border-radius: 4px;
  background: #fff; color: #1b1b24; font: inherit; text-align: center;
}
#toolbar .hint { position: absolute; right: 16px; color: #8a849b; font-size: 12px; }
#notes {
  position: fixed; left: 0; right: 0; bottom: 48px; max-height: 32vh; overflow: auto;
  background: rgba(16, 10, 26, 0.94); color: #e6def3; padding: 16px 28px 20px;
  font: 15px/1.7 $F_BODY; z-index: 20; border-top: 2px solid $C_ACCENT;
}
#notes .label { color: $C_ACCENT; font-size: 12px; font-weight: 700; margin-bottom: 6px; }

/* 一覧表示（body.overview）: 全スライドを縮小グリッドで並べ、クリックでそのスライドを開く */
body.overview { overflow-y: auto; }
body.overview #stage {
  position: static; transform: none !important; width: auto; height: auto;
  display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; align-items: flex-start; gap: 24px;
  padding: 24px 24px 72px;
}
body.overview .slide {
  position: relative; inset: auto; display: block !important; flex-shrink: 0; cursor: pointer;
  transform: scale(0.22); transform-origin: top left;
  /* transform はレイアウト上の大きさを変えないため、縮小分を負のマージンで詰める */
  margin: 0 calc(${W}px * -0.78) calc(${H}px * -0.78) 0;
  outline: 10px solid transparent;
}
body.overview .slide:hover { outline-color: $C_ACCENT; }
body.overview .slide::after {
  content: attr(data-page); position: absolute; left: 0; bottom: 0; z-index: 5;
  padding: 4px 22px; background: $C_ACCENT; color: #fff; font-size: 64px; font-weight: bold;
}

@media print {
  /* X-2: #stage の JS 由来の transform（画面フィット用の translate/scale）と、
     body の overflow:hidden/height:100% は、印刷時に複数ページへ正しく流し込む妨げになる
     ため無効化する（.slide/#toolbar/#notes だけを print 用にしても、この2つが残ると
     スライドが縮小・クリップされて壊れた出力になることを Playwright の page.pdf() で確認済み）。*/
  html, body { height: auto !important; overflow: visible !important; background: #fff !important; }
  #stage { position: static !important; top: auto !important; left: auto !important; transform: none !important; width: auto !important; height: auto !important; }
  .slide { position: relative !important; display: block !important; page-break-after: always; transform: none !important; margin: 0 !important; outline: none !important; }
  #toolbar, #notes { display: none !important; }
  /* 主要ブラウザは印刷ダイアログの「背景のグラフィック」が既定でOFF（Playwright の
     page.pdf() も printBackground の既定値が false）で、これが無いと背景色で塗られた
     要素（section の全面背景・table のヘッダ色・cards/matrix の塗り・code 背景等、
     テーマの大半の視覚設計）が丸ごと消え、白背景に白文字になるスライドが出る。 */
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
  @page { size: ${W}px ${H}px; margin: 0; }
}
$CANVAS_CSS
</style>
</head>
<body>
<div id="stage">
$SLIDES
</div>
<div id="toolbar">
  <button type="button" id="btn-prev" title="前へ（←）">&#9664;</button>
  <input type="number" id="page-input" min="1" max="$TOTAL" aria-label="ページ番号">&nbsp;/&nbsp;$TOTAL
  <button type="button" id="btn-next" title="次へ（→）">&#9654;</button>
  <button type="button" id="btn-overview" title="全スライドの一覧（Esc で戻る）">一覧</button>
  <span class="hint">[&larr;/&rarr;] 移動　[N] ノート　番号入力+Enter でジャンプ</span>
</div>
<div id="notes" hidden><div class="label">SPEAKER NOTES</div><div id="notes-body"></div></div>
<script>
var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
var stage = document.getElementById('stage');
var toolbar = document.getElementById('toolbar');
var notes = document.getElementById('notes');
var notesBody = document.getElementById('notes-body');
var pageInput = document.getElementById('page-input');
var prevButton = document.getElementById('btn-prev');
var nextButton = document.getElementById('btn-next');
var overviewButton = document.getElementById('btn-overview');
var idx = 0;

function isOverview() { return document.body.classList.contains('overview'); }

function fit() {
  if (isOverview()) { return; }
  var s = Math.min(window.innerWidth / $W, window.innerHeight / $H);
  stage.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
}

function setOverview(on) {
  document.body.classList.toggle('overview', on);
  overviewButton.textContent = on ? 'スライドに戻る' : '一覧';
  prevButton.disabled = on || idx === 0;
  nextButton.disabled = on || idx === slides.length - 1;
  if (on) { slides[idx].scrollIntoView({ block: 'center' }); }
  else { fit(); }
}

function show(i) {
  idx = Math.max(0, Math.min(slides.length - 1, i));
  slides.forEach(function (s, j) { s.classList.toggle('active', j === idx); });
  pageInput.value = idx + 1;
  prevButton.disabled = idx === 0;
  nextButton.disabled = idx === slides.length - 1;
  location.replace('#' + (idx + 1));
  var n = slides[idx].getAttribute('data-notes') || '';
  notesBody.textContent = n || '（このスライドにノートはありません）';
}
function toggleNotes() { notes.hidden = !notes.hidden; }

prevButton.addEventListener('click', function () { show(idx - 1); });
nextButton.addEventListener('click', function () { show(idx + 1); });
overviewButton.addEventListener('click', function () { setOverview(!isOverview()); });
pageInput.addEventListener('change', function () {
  var n = parseInt(pageInput.value, 10);
  if (isNaN(n)) { pageInput.value = idx + 1; return; }
  show(n - 1);
  setOverview(false);
  pageInput.blur();
});
stage.addEventListener('click', function (e) {
  if (!isOverview()) { return; }
  var slide = e.target.closest('.slide');
  if (!slide) { return; }
  show(slides.indexOf(slide));
  setOverview(false);
});

window.addEventListener('resize', fit);
window.addEventListener('keydown', function (e) {
  if (e.target === pageInput) { return; }
  if (e.key === 'Escape' && isOverview()) { setOverview(false); return; }
  if (isOverview()) { return; }
  if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { show(idx + 1); e.preventDefault(); }
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { show(idx - 1); e.preventDefault(); }
  else if (e.key === 'Home') { show(0); }
  else if (e.key === 'End') { show(slides.length - 1); }
  else if (e.key === 'n' || e.key === 'N') { toggleNotes(); }
});
window.addEventListener('click', function (e) {
  if (isOverview()) { return; }
  if (notes.contains(e.target) || toolbar.contains(e.target)) { return; }
  if (e.clientX > window.innerWidth / 2) { show(idx + 1); } else { show(idx - 1); }
});

var start = parseInt((location.hash || '#1').slice(1), 10);
fit();
show(isNaN(start) ? 0 : start - 1);
</script>
</body>
</html>
""")


def slide_bg(slide, st, theme, pattern_resolved=None):
    if slide.get("type") == "canvas":
        return slide.get("background", "#FFFFFF")
    if pattern_resolved and pattern_resolved.get("background"):
        return pattern_resolved["background"]       # frame:"full" のパターンは型が背景色を持つ
    if "bg" in st:
        return col(theme, st["bg"].get("fill", "primary"))
    return col(theme, "background")


def build_html(deck, theme, layout, deck_dir: Path, out_path: Path):
    slides = deck.get("slides", [])
    total = len(slides)
    rendered = []
    marks_on = todo_marks.enabled(deck)
    for i, slide in enumerate(slides):
        with slide_guard(f"出力{i + 1}ページ目（type={slide.get('type')}）", "HTML描画"):
            st = resolve_style(layout, deck, slide)
            resolved = (resolve_pattern_slide(slide, st, deck, theme, deck_dir, i + 1, total)
                        if slide.get("type") == "pattern" else None)
            body = html_slide_body(slide, st, deck, theme, deck_dir, i + 1, total, resolved)
            if deck.get("meta", {}).get("brand") and "brand" in st:
                body += div(st["brand"], theme, esc(deck.get("meta", {}).get("brand", "")))
            if marks_on:
                body = todo_marks.html_mark(body, layout)
            notes_attr = f' data-notes="{esc(slide["notes"])}"' if slide.get("notes") else ""
            bg = slide_bg(slide, st, theme, resolved)
            # X-3: スクリーンリーダー向けにスライド番号とタイトルを aria-label で伝える
            title_txt = slide.get("title", "")
            aria_label = f"{i + 1} / {total}: {title_txt}" if title_txt else f"{i + 1} / {total}"
            rendered.append(
                f'<section class="slide" aria-label="{esc(aria_label)}" '
                f'style="background:{bg};color:{col(theme, "text")};" data-page="{i + 1}" data-type="{esc(slide.get("type", ""))}"'
                + (f' data-pattern="{esc(resolved["pattern"])}"' if resolved else "")
                + f"{notes_attr}>{body}</section>"
            )
    doc = HTML_TEMPLATE.safe_substitute(
        TITLE=esc(deck_title(deck, deck_dir)),
        SLIDES="\n".join(rendered),
        W=str(CANVAS_W), H=str(CANVAS_H),
        C_ACCENT=col(theme, "accent"),
        F_BODY=font_css(theme["fonts"]["body"]),
        TOTAL=str(total),
        CANVAS_CSS=ce.CANVAS_CSS + ("\n" + todo_marks.html_css(layout) if marks_on else ""),
    )
    try:
        out_path.write_text(doc, encoding="utf-8")
    except PermissionError:
        fail(f"{out_path} に書き込めません。ファイル（ブラウザ等）を開いている場合は閉じてから再実行してください")


# ---------------------------------------------------------------------------
# PPTX ビルド
# ---------------------------------------------------------------------------

def _apply_ooxml_theme(prs, theme, fonts):
    """OOXML の theme1.xml（clrScheme/fontScheme）をデッキのテーマトークンで書き換える（M-49）。
    PowerPoint の「テーマの色/フォント」タブから見ても一致するようにするための付随機能であり、
    シェイプの塗り自体は従来どおり RGB 直書きのまま。失敗しても PPTX 生成は継続する。"""
    try:
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml import parse_xml
        from pptx.oxml.ns import qn as _qn
        from lxml import etree

        theme_part = prs.slide_masters[0].part.part_related_by(RT.THEME)
        root = parse_xml(theme_part.blob)

        def _set_solid(el, hex_color):
            if el is None:
                return
            for child in list(el):
                el.remove(child)
            el.append(el.makeelement(_qn("a:srgbClr"), {"val": hex_color}))

        clr = root.find(".//" + _qn("a:clrScheme"))
        if clr is not None:
            mapping = {
                "dk1": "text", "lt1": "background", "dk2": "primary", "lt2": "surface",
                "accent1": "accent", "accent2": "primary",
                "accent3": "highlight_fill", "accent4": "muted",
            }
            for tag, token in mapping.items():
                _set_solid(clr.find(_qn(f"a:{tag}")), col(theme, token).lstrip("#"))

        heading_name = font_pptx(fonts.get("heading")) or font_pptx(fonts["body"])
        body_name = font_pptx(fonts["body"])
        fs = root.find(".//" + _qn("a:fontScheme"))
        if fs is not None:
            for node, name in ((fs.find(_qn("a:majorFont")), heading_name),
                               (fs.find(_qn("a:minorFont")), body_name)):
                if node is None or not name:
                    continue
                for tag in ("a:latin", "a:ea"):
                    el = node.find(_qn(tag))
                    if el is not None:
                        el.set("typeface", name)

        # 効果スタイル（影・光彩）を全部空にする。python-pptx の既定テーマは 2 番目の効果スタイルが外側の影で、
        # 図形の p:style の effectRef がそれを参照している。図形側の空の effectLst を LibreOffice は無視して
        # 影を描く（PDF に出る影の原因。A3-02）。テーマ側を空にすれば、どのビューアでも影が付かない。
        est = root.find(".//" + _qn("a:effectStyleLst"))
        if est is not None:
            for child in list(est):
                est.remove(child)
            for _ in range(3):
                style = est.makeelement(_qn("a:effectStyle"), {})
                style.append(style.makeelement(_qn("a:effectLst"), {}))
                est.append(style)

        theme_part.blob = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )
    except Exception as e:   # 見た目は RGB 直書きなので続行できるが、黙って握りつぶさず知らせる
        warn(f"PPTX のテーマ（色・フォント・効果）の書き換えに失敗しました（{type(e).__name__}: {e}）。"
             "図形の色は個別に指定されているので見た目は変わりませんが、PowerPoint の「テーマ」表示と影の抑止が効かないことがあります")


_XML_BAD_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def xml_safe(s) -> str:
    """XML 1.0 で使えない制御文字を取り除く（文書プロパティは python-pptx / lxml が ValueError にするため）。"""
    return _XML_BAD_CHARS_RE.sub("", str(s))


def deck_title(deck: dict, deck_dir=None) -> str:
    """デッキの表題。meta.title → meta.id → 先頭スライドの title → フォルダ名の順で補う（HTML の <title> と PPTX の文書プロパティ共通）。"""
    meta = deck.get("meta") if isinstance(deck.get("meta"), dict) else {}
    cands = [meta.get("title"), meta.get("id")]
    slides = deck.get("slides")
    if isinstance(slides, list) and slides and isinstance(slides[0], dict):
        cands.append(slides[0].get("title"))
    if deck_dir is not None:
        cands.append(Path(deck_dir).name)
    for c in cands:
        if isinstance(c, (str, int, float)) and not isinstance(c, bool):
            c = xml_safe(c).strip()
            if c:
                return c
    return ""


def _finalize_pptx(prs, deck, deck_dir=None):
    """PPTX を保存する直前の仕上げ（全経路の図形に一括で効かせる）。
    - 影: 全図形の p:style/effectRef を idx=0（効果なし）にする（テーマ側を空にできなかった場合の保険。A3-02）
    - 自動調整: 残っている spAutoFit（図形が文章に合わせて伸縮）を noAutofit にする（A3-08）
    - 文書プロパティ: タイトル・作成者などを meta から入れる（python-pptx 既定の "Steve Canny" 等を残さない）"""
    import datetime
    from pptx.oxml.ns import qn
    for slide in prs.slides:
        root = slide._element
        for ref in root.iter(qn("a:effectRef")):
            ref.set("idx", "0")
        for sp_auto in list(root.iter(qn("a:spAutoFit"))):
            parent = sp_auto.getparent()
            idx = parent.index(sp_auto)
            parent.remove(sp_auto)
            parent.insert(idx, parent.makeelement(qn("a:noAutofit"), {}))
    meta = deck.get("meta", {}) if isinstance(deck.get("meta"), dict) else {}
    cp = prs.core_properties
    author = xml_safe(meta.get("author") or "")
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    cp.title = deck_title(deck, deck_dir)
    cp.subject = xml_safe(meta.get("subtitle") or "")
    cp.author = author
    cp.last_modified_by = author
    cp.comments = ""
    cp.keywords = ""
    cp.category = ""
    cp.language = "ja-JP"
    cp.revision = 1
    cp.created = now
    cp.modified = now
    # 既定テンプレートの白紙スライドのサムネイル（docProps/thumbnail.jpeg）は、中身と無関係なので外す
    try:
        pkg = prs.part.package
        for rid, rel in list(pkg._rels.items()):
            if rel.reltype.endswith("/thumbnail"):
                pkg._rels.pop(rid)
    except Exception:
        pass


def _verify_saved_pptx(path: Path, expect_slides=None):
    """保存した PPTX の機械検証（zip 整合・再パース・ノート無し・文書プロパティ）。失敗は fail。
    qa 担当の verify_pptx があればそれを使い、無い・読み込めないときは同等の最小検査を内蔵のもので行う。"""
    problems = None
    try:
        import verify_pptx
        problems = list(verify_pptx.verify(str(path)))
    except Exception:
        problems = None
    if problems is None:
        problems = []
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
                if bad:
                    problems.append(f"zip の部品 {bad} が壊れています")
                names = z.namelist()
            if any(n.startswith("ppt/notesSlides/") or n.startswith("ppt/notesMasters/") for n in names):
                problems.append("スピーカーノートの部品が入っています（Keynote 互換のため出力しない決まりです）")
            from pptx import Presentation
            prs = Presentation(str(path))
            if len(prs.slides) == 0:
                problems.append("スライドが 0 枚です")
            if any(sl.has_notes_slide for sl in prs.slides):
                problems.append("スピーカーノートが入っています")
        except Exception as e:
            problems.append(f"PPTX を開き直せません（{type(e).__name__}: {e}）")
    if expect_slides == 0:
        # slides が空のデッキは validate_deck が警告済み（入力の問題）。0 枚であること自体は検証の不合格にしない
        problems = [p for p in problems if "スライドが 0 枚" not in p]
    if problems:
        # 入力（deck.json）に原因がありうるものと、ツールの不具合を見分けて案内する
        from_input = [p for p in problems if "title が空" in p or "スライドが 0 枚" in p]
        if from_input and len(from_input) == len(problems):
            hint = "\n  → deck.json の meta.title と slides を確認してください（meta.title が無くても meta.id かフォルダ名で補います）"
        else:
            hint = ("\n  → build_deck.py の不具合の可能性があります（zip の破損・再パース不能など、入力の誤りでは起きないもの）。"
                    "--debug を付けて再実行し、出力を添えて報告してください")
        fail(f"{path.name} の検証に失敗しました:\n  - " + "\n  - ".join(problems) + hint)


def build_pptx(deck, theme, layout, deck_dir: Path, out_path: Path):
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
        from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
        from pptx.oxml.ns import qn
        from pptx.util import Emu, Inches, Pt
    except ImportError:
        sys.exit(
            "error: python-pptx が未インストールのため PPTX を生成できません。\n"
            "  初回セットアップを実行してください: /slide-deck:setup"
            "（または `pip install python-pptx`）。HTML だけなら --html を付けて再実行できます。"
        )

    fonts = theme["fonts"]
    # fonts.heading（見出し系トークン）。未指定なら body にフォールバック（M-21/M-64/M-83）。
    HEADING_FONT = fonts.get("heading") or fonts["body"]

    def IN(px):
        return Inches(px / 96.0)

    def PTS(px):
        return Pt(px * 0.75)

    def set_row_heights(table, heights_px):
        """表の行の高さを一度に設定する。python-pptx の Row.height は 1 行ごとに全行の高さを合計し直す（行数の 2 乗の時間）ので、
        a:tr の h を直接書き、枠（graphicFrame）の高さは最後に 1 回だけ合計する（結果の XML は 1 行ずつ設定したときと同じ）。"""
        trs = table._tbl.tr_lst
        for tr, h in zip(trs, heights_px):
            tr.h = IN(h)
        table._graphic_frame.height = Emu(sum(tr.h for tr in trs))

    def C(name):
        return RGBColor.from_string(col(theme, name).lstrip("#"))

    ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}

    prs = Presentation()
    prs.slide_width = IN(CANVAS_W)
    prs.slide_height = IN(CANVAS_H)
    sldsz = prs.element.find(qn("p:sldSz"))
    if sldsz is not None:
        sldsz.set("type", "screen16x9")
    _apply_ooxml_theme(prs, theme, fonts)
    blank = prs.slide_layouts[6]

    def set_lh(p, size_px, lh):
        """行送りを固定値（pt）で指定する（A3-01）。倍率（spcPct）はフォント固有の行高さに掛かるので、
        HTML の line-height（文字サイズ × 倍率）より 12〜21% 広がり、フォントによって幅も違う。
        px × 倍率を pt にした固定値なら、どのフォント・どのビューアでも HTML と同じ行送りになる。"""
        p.line_spacing = Pt(round(size_px * lh * 0.75, 2))

    def set_run(run, text, size_px, color, bold=False, name=None, tracking=0, case=None):
        text = str(text)
        rest = []
        if "\n" in text:
            # 明示的な改行は段落内の改行（a:br）にする（生の改行文字を a:t に入れても改行にならない）
            text, *rest = text.split("\n")
        run.text = text
        resolved_name = font_pptx(name) if name is not None else font_pptx(fonts["body"])
        f = run.font
        f.name = resolved_name
        f.size = PTS(size_px)
        f.bold = bold
        f.color.rgb = color
        rPr = run._r.get_or_add_rPr()
        rPr.set("lang", "ja-JP")    # 校正の言語・禁則の既定を日本語に（canvas の経路と同じ）
        if tracking:
            # 字間: em → 1/100 pt（px × 0.75 pt × 100）。ST_TextPoint の範囲（±400000）に収める
            rPr.set("spc", str(max(-400000, min(400000, int(round(tracking * size_px * 75))))))
        if case == "upper":
            rPr.set("cap", "all")
        for tag in ("a:ea", "a:cs"):
            el = rPr.find(qn(tag))
            if el is None:
                el = rPr.makeelement(qn(tag), {})
                rPr.append(el)
            el.set("typeface", resolved_name)
        prev = run._r
        for part in rest:
            br = prev.makeelement(qn("a:br"), {})
            br.append(copy.deepcopy(rPr))
            prev.addnext(br)
            nr = copy.deepcopy(run._r)
            nr.find(qn("a:t")).text = part
            br.addnext(nr)
            prev = nr

    def add_box(slide, r):
        box = slide.shapes.add_textbox(IN(r["x"]), IN(r["y"]), IN(r["w"]), IN(r.get("h", 40)))
        tf = box.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE   # python-pptx 既定の spAutoFit だと、PowerPoint で編集した瞬間に箱の高さが変わる（A3-08）
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, Emu(0))
        return tf

    def para(tf, used):
        if not used[0]:
            used[0] = True
            return tf.paragraphs[0]
        return tf.add_paragraph()

    def text_region(slide, r, text, font=None):
        tf = add_box(slide, r)
        p = tf.paragraphs[0]
        if r.get("align"):
            p.alignment = ALIGN[r["align"]]
        if r.get("line_height"):
            set_lh(p, r["size"], r["line_height"])
        set_run(p.add_run(), text, r["size"], C(r.get("color", "text")),
                bold=shp.is_bold(r), name=font, tracking=shp.tracking_of(r), case=r.get("case"))
        return tf

    def _apply_shadow(sp, shadow):
        """箱の影（canvas の shadow 形式）を effectLst に入れる。HTML の box-shadow と同じ向き・ぼかし。"""
        from lxml import etree
        spPr = sp._element.spPr
        for old in spPr.findall(qn("a:effectLst")):
            spPr.remove(old)
        xml = ce._shadow_xml(shadow)
        el = etree.fromstring(f'<r xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{xml}</r>')[0]
        # effectLst は ln の後ろ（schema 順: fill → ln → effectLst）
        ln = spPr.find(qn("a:ln"))
        if ln is not None:
            ln.addnext(el)
        else:
            spPr.append(el)

    def add_rect(slide, x, y, w, h, fill, radius=0, border=None, top_only=False, border_w=None, shadow=None):
        """top_only=True なら上辺の 2 隅だけ丸める（HTML の border-radius:r r 0 0。steps のヘッダ帯）。"""
        shape = (MSO_SHAPE.ROUND_2_SAME_RECTANGLE if top_only else MSO_SHAPE.ROUNDED_RECTANGLE) if radius else MSO_SHAPE.RECTANGLE
        sp = slide.shapes.add_shape(shape, IN(x), IN(y), IN(w), IN(h))
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
        if border is not None and (border_w is None or border_w > 0):
            # 面の視認性: surface 系の淡い塗りだけに頼らず 1px の枠線で輪郭を出す（border_w は px。0 で枠なし）。
            sp.line.color.rgb = border
            sp.line.width = Pt(0.75 if border_w is None else border_w * 0.75)
        else:
            sp.line.fill.background()
        sp.shadow.inherit = False
        if shadow:
            _apply_shadow(sp, shadow)
        if radius:
            # M-46: 角丸半径（px）を短辺に対する比率に変換して明示指定する
            # （px と EMU は単位変換の一次比例なので px のまま比を取ってよい）。
            sp.adjustments[0] = min(0.5, radius / max(1, min(w, h)))
            if top_only:
                sp.adjustments[1] = 0.0
        return sp

    def rect_region(slide, r):
        add_rect(slide, r["x"], r["y"], r["w"], r["h"], C(r.get("fill", "accent")),
                 radius=r.get("radius", 0))

    def rule_region(slide, st):
        if _rule_drawable(st.get("rule")):
            rect_region(slide, st["rule"])

    def _set_bullet(p, char, color, marL_px, hang_px, size_pct=100):
        """段落をネイティブの PowerPoint 箇条書きにする（M-47）。
        マーカーを文字として書かず a:buChar/a:buClr/a:buSzPct/a:buFont を設定し、
        marL=インデント・indent=-ハング幅 のぶら下げインデントにする。"""
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(IN(marL_px))))
        pPr.set("indent", str(int(-IN(hang_px))))
        buClr = pPr.makeelement(qn("a:buClr"), {})
        buClr.append(buClr.makeelement(qn("a:srgbClr"), {"val": str(color)}))
        pPr.append(buClr)
        pPr.append(pPr.makeelement(qn("a:buSzPct"), {"val": str(int(size_pct * 1000))}))
        pPr.append(pPr.makeelement(qn("a:buFont"), {"typeface": font_pptx(fonts["body"])}))
        pPr.append(pPr.makeelement(qn("a:buChar"), {"char": char}))

    def add_bullets(slide, items, r):
        tf = add_box(slide, r)
        used = [False]
        marL = r["indent"]
        child_hang = 28  # marker（○）と本文の間に十分な余白を確保する
        gap, cgap = r["gap"], r["child_gap"]
        for it in items:
            p = para(tf, used)
            # HTML は親 li の下に margin-bottom: gap、子 ul の上に margin-top: child_gap、最後の子の下は gap と child_gap の
            # 大きいほう（余白の相殺）。子のある親は下の余白を child_gap にして揃える。
            kids = it["children"]
            p.space_after = PTS(cgap if kids else gap)
            size = it.get("size", r["size"])
            set_lh(p, size, r["line_height"])
            color = C(it["color"]) if it.get("color") else C(r["color"])
            _set_bullet(p, "•", C(r["marker_color"]), marL, marL)
            set_run(p.add_run(), it["text"], size, color, bold=it.get("bold", False))
            for ci, c in enumerate(kids):
                p = para(tf, used)
                p.space_after = PTS(max(gap, cgap) if ci == len(kids) - 1 else cgap)
                csize = c.get("size", r["child_size"])
                set_lh(p, csize, r["line_height"])   # HTML の子 ul は親の line-height を継承する（以前は PPTX だけ -0.15）
                ccolor = C(c["color"]) if c.get("color") else C(r["child_color"])
                _set_bullet(p, "○", C(r["marker_color"]), marL + child_hang, child_hang)
                set_run(p.add_run(), c["text"], csize, ccolor)
        return tf

    def footer(slide, st, page, total):
        if "footer_l" in st:
            text_region(slide, st["footer_l"], deck.get("meta", {}).get("title", ""))
        if "footer_r" in st:
            text_region(slide, st["footer_r"], st["footer_r"].get("text") or f"{page} / {total}")

    def chrome(slide, data, st, page, total):
        if data.get("_bare"):
            return          # 合成スライドのブロック: 見出し骨格は合成スライド側が 1 回だけ描く
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"], font=HEADING_FONT)
        if "title" in st:
            text_region(slide, st["title"], data.get("title", ""), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("lead") and "lead" in st:
            text_region(slide, st["lead"], data["lead"])
        footer(slide, st, page, total)

    def hero_pptx(slide, data, st, extra=None):
        """主役系の下地（背景の画像・覆い・色面 → variant の panel → 飾り）。HTML と同じ canvas 要素。"""
        els = hero.hero_layers(st, data.get("_bg"), theme.get("colors", {})) + (extra or [])
        if els:
            ce.add_canvas_to_pptx(slide, els, _canvas_svg_png, _canvas_backdrop_png,
                                  image_source=canvas_image_source(deck_dir, browser))

    def s_title(slide, data, st, page, total):
        hero_pptx(slide, data, st)
        rect_region(slide, st["bar"])
        text_region(slide, st["title"], data.get("title", ""), font=HEADING_FONT)
        if data.get("subtitle"):
            text_region(slide, st["subtitle"], data["subtitle"])
        if data.get("meta"):
            text_region(slide, st["meta"], data["meta"])

    def s_section(slide, data, st, page, total):
        add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C(st["bg"]["fill"]))
        hero_pptx(slide, data, st)
        if data.get("number"):
            text_region(slide, st["number"], data["number"], font=HEADING_FONT)
        text_region(slide, st["title"], data.get("title", ""), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("subtitle"):
            text_region(slide, st["subtitle"], data["subtitle"])

    def s_bullets(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        tf_body = add_bullets(slide, norm_items(data.get("bullets")), st["body"])
        # style.body.valign（既定 top）: HTML 側の flex 中央寄せと同じ考え方（M-37 系と同一パターン）。
        if st["body"].get("valign", "top") == "middle":
            from pptx.enum.text import MSO_ANCHOR
            tf_body.vertical_anchor = MSO_ANCHOR.MIDDLE

    def s_two_column(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        for side in ("left", "right"):
            box = st[side]
            colc = data.get(side, {})
            add_rect(slide, box["x"], box["y"], box["w"], box["h"],
                     C(box["fill"]), radius=box.get("radius", 0),
                     border=C(box["border_color"]) if box.get("border_color") else None,
                     border_w=box.get("border_w"), shadow=shadow_spec(box, theme))
            pad = box["pad"]
            # style.left.valign / style.right.valign: "middle" で heading+bullets をまとめて
            # 箱の縦中央に寄せる（HTML と同じ考え方。PPTX は実描画高さを取れないため見積もる）。
            hd = st["col_heading"]
            valign = box.get("valign", "top")
            lay = _two_column_side_layout(colc, box, hd, st["col_body"], valign)
            if colc.get("heading"):
                hr = {"x": box["x"] + pad, "y": box["y"] + lay["head_y"], "w": box["w"] - 2 * pad,
                      "h": max(1.0, lay["head_h"]),
                      "size": hd["size"], "color": hd["color"], "bold": hd.get("bold", False)}
                text_region(slide, hr, colc["heading"], font=HEADING_FONT)
            body = dict(st["col_body"])
            body.update({"x": box["x"] + pad, "y": box["y"] + lay["body_y"], "w": box["w"] - 2 * pad,
                         "h": max(1.0, lay["body_h"])})
            add_bullets(slide, norm_items(colc.get("bullets")), body)

    # 表のスタイルは「スタイルなし・グリッドなし」にする。python-pptx 既定の Medium Style 2 だと、
    # スタイル由来の白い内側罫線が行間の線に勝って線が消え、ヘッダーに白い縦線が入る（A3-04）。
    NO_GRID_TABLE_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"

    def _no_grid_style(gfx):
        tblPr = gfx._element.graphic.graphicData.tbl.tblPr
        sid = tblPr.find(qn("a:tableStyleId"))
        if sid is None:
            sid = tblPr.makeelement(qn("a:tableStyleId"), {})
            tblPr.append(sid)
        sid.text = NO_GRID_TABLE_STYLE

    def _set_cell_lines(cell, lines):
        """セルの 4 辺の罫線を明示する。lines = {"L"|"R"|"T"|"B": (hex, pt) | None}。None は線なし（noFill）。
        schema 順（lnL, lnR, lnT, lnB → 塗り）を守るため tcPr の先頭に並べる。"""
        tcPr = cell._tc.get_or_add_tcPr()
        for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
            old = tcPr.find(qn(tag))
            if old is not None:
                tcPr.remove(old)
        for idx, side in enumerate(("L", "R", "T", "B")):
            spec = lines.get(side)
            if spec:
                ln = tcPr.makeelement(qn(f"a:ln{side}"), {"w": str(int(Pt(spec[1]))), "cap": "flat"})
                fill = ln.makeelement(qn("a:solidFill"), {})
                fill.append(fill.makeelement(qn("a:srgbClr"), {"val": spec[0]}))
                ln.append(fill)
            else:
                ln = tcPr.makeelement(qn(f"a:ln{side}"), {"w": "0"})
                ln.append(ln.makeelement(qn("a:noFill"), {}))
            tcPr.insert(idx, ln)

    def s_table(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        tr = st["table"]
        border_hex = str(C(tr.get("border_color", "border")))
        cols = data.get("columns", [])
        rows = data.get("rows", [])
        n_rows, n_cols = len(rows) + 1, len(cols)
        total_h = tr["header_h"] + tr["row_h"] * len(rows)
        fit_total = ((st.get("_fit") or {}).get("info", {}).get("table") or {}).get("total_h")
        if fit_total and fit_total > total_h and ((st.get("_fit") or {}).get("info", {}).get("table") or {}).get("adjusted"):
            total_h = fit_total      # 折り返して高くなる行を含めた見積もり（枠の高さの目安。行は内容に合わせて伸びる）
        gfx = slide.shapes.add_table(n_rows, n_cols, IN(tr["x"]), IN(tr["y"]),
                                     IN(tr["w"]), IN(total_h))
        _no_grid_style(gfx)
        table = gfx.table
        table.first_row = False
        table.horz_banding = False
        # 列幅: col_widths（比率）があればそれ、無ければ HTML の自動幅（table レイアウト）を模擬した幅（等分ではない）
        widths = tr.get("col_widths")
        if widths:
            unit = tr["w"] / sum(widths)
            px_widths = [w * unit for w in widths]
        else:
            px_widths = table_auto_widths(cols, rows, tr, data)
        for j, w in enumerate(px_widths):
            table.columns[j].width = IN(w)
        fit_info = (st.get("_fit") or {}).get("info", {}).get("table") or {}
        fit_lines = (fit_info.get("lines") or []) if fit_info.get("adjusted") else []
        row_hs = [tr["header_h"]]
        for i in range(len(rows)):
            h = tr["row_h"]
            if i < len(fit_lines):
                # 折り返して高くなる行は、HTML と同じく内容の高さ（行数 × 文字 × 行高 + 上下余白）まで広げて持つ
                h = max(h, fit_lines[i] * tr["cell_size"] * tr["line_height"] + 2 * tr["pad_y"])
            row_hs.append(h)
        set_row_heights(table, row_hs)
        # 罫線は HTML と同じ: ヘッダーは線なし、本文は各行の下に 1px。行の境目は上の行の下罫線と同じ線を上辺にも置く
        # （LibreOffice / PowerPoint のどちらで描いても線が消えない・二重にならない）
        line = (border_hex, 0.75)
        for j, name in enumerate(cols):
            cell = table.cell(0, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C(tr["header_fill"])
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = IN(tr["pad_x"])
            cell.margin_right = IN(tr["pad_x"])
            cell.margin_top = IN(tr["pad_y"])
            cell.margin_bottom = IN(tr["pad_y"])
            _set_cell_lines(cell, {})
            p = cell.text_frame.paragraphs[0]
            set_lh(p, tr["header_size"], tr["line_height"])
            set_run(p.add_run(), str(name), tr["header_size"], C(tr["header_color"]), bold=True)
        row_fills = tr.get("row_fills", {})
        for i, row in enumerate(rows):
            is_total = bool(data.get("total_row")) and i == len(rows) - 1
            for j, val in enumerate(row):
                is_label = bool(data.get("row_header")) and j == 0
                cell = table.cell(i + 1, j)
                cell.fill.solid()
                emph_row = i in set(data.get("_row_emphasis") or [])
                if is_total:
                    cell_bg = tr.get("total_fill", "surface")
                elif is_label:
                    cell_bg = tr.get("label_fill", "highlight_fill")
                elif emph_row:
                    cell_bg = tr.get("emphasis_fill", "highlight_fill")
                elif str(i) in row_fills:
                    cell_bg = row_fills[str(i)]
                else:
                    cell_bg = tr["row_alt_fill"] if i % 2 else "background"
                cell.fill.fore_color.rgb = C(cell_bg)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_left = IN(tr["pad_x"])
                cell.margin_right = IN(tr["pad_x"])
                cell.margin_top = IN(tr["pad_y"])       # HTML の td の padding と同じ（以前は既定の 4.8px）
                cell.margin_bottom = IN(tr["pad_y"])
                _set_cell_lines(cell, {"T": line if i > 0 else None, "B": line})
                p = cell.text_frame.paragraphs[0]
                set_lh(p, tr["cell_size"], tr["line_height"])
                visible_text, cell_url = table_cell_parts(val)
                run = p.add_run()
                strong = is_total or is_label
                tone = None if strong else _cell_tone_color(theme, tr, val, col(theme, cell_bg))
                set_run(run, visible_text, tr["cell_size"],
                        C(tr.get("label_color", "heading_text")) if strong else (C(tone) if tone else C(tr["cell_color"])),
                        bold=strong or emph_row or bool(tone))
                if cell_url:
                    run.hyperlink.address = cell_url

    def _cell_borders(cell, hex_color, width_pt=1.0):
        """セルの上下左右の罫線を設定する（schema 順 lnL/lnR/lnT/lnB を塗りより前に置く）。"""
        tcPr = cell._tc.get_or_add_tcPr()
        for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
            old = tcPr.find(qn(tag))
            if old is not None:
                tcPr.remove(old)
        for tag in ("a:lnB", "a:lnT", "a:lnR", "a:lnL"):
            ln = tcPr.makeelement(qn(tag), {"w": str(int(Pt(width_pt))), "cap": "flat"})
            fill = ln.makeelement(qn("a:solidFill"), {})
            fill.append(fill.makeelement(qn("a:srgbClr"), {"val": hex_color}))
            ln.append(fill)
            tcPr.insert(0, ln)

    def _plain_table(slide, n_rows, n_cols, x, y, widths, heights):
        gfx = slide.shapes.add_table(n_rows, n_cols, IN(x), IN(y), IN(sum(widths)), IN(sum(heights)))
        _no_grid_style(gfx)
        table = gfx.table
        table.first_row = False
        table.horz_banding = False
        for j, w in enumerate(widths):
            table.columns[j].width = IN(w)
        set_row_heights(table, heights)
        return table

    def _fill_cell(cell, fill, border_hex, pad_x=4, pad_y=2, anchor="middle"):
        from pptx.enum.text import MSO_ANCHOR
        cell.fill.solid()
        cell.fill.fore_color.rgb = C(fill)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE if anchor == "middle" else MSO_ANCHOR.TOP
        cell.margin_left = cell.margin_right = IN(pad_x)
        cell.margin_top = cell.margin_bottom = IN(pad_y)
        cell.text_frame.word_wrap = True
        _cell_borders(cell, border_hex)

    def s_status_table(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        lg = st["legend"]
        legend = status_legend(data)
        if legend:
            lbc = str(C(lg["border_color"]))
            row_h = lg["h"] / len(legend)
            # 凡例の見出し（左の濃い帯）は表の結合セルにせず、図形で描く（LibreOffice は結合セルの文字の高さを最後の行に足して、凡例が高くなり見出しの罫線に重なる・S5a）
            ts = add_rect(slide, lg["x"], lg["y"], lg["title_w"], lg["h"], C(lg["title_fill"]), border=C(lg["border_color"]), border_w=1)
            tf = ts.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = IN(lg["pad_x"])
            tf.margin_top = tf.margin_bottom = IN(1)
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            for n, line in enumerate(str(data.get("legend_title", STATUS_LEGEND_TITLE)).split("\n")):
                p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
                p.alignment = ALIGN["center"]
                set_lh(p, lg["size"] + 1, lg["line_height"])
                set_run(p.add_run(), line, lg["size"] + 1, C(lg["title_color"]), bold=True, name=HEADING_FONT)
            lt = _plain_table(slide, len(legend), 2, lg["x"] + lg["title_w"], lg["y"],
                              [lg["symbol_w"], lg["w"] - lg["title_w"] - lg["symbol_w"]],
                              [row_h] * len(legend))
            for k, it in enumerate(legend):
                for j in range(2):
                    _fill_cell(lt.cell(k, j), lg["fill"], lbc, pad_x=lg["pad_x"], pad_y=1)
                p = lt.cell(k, 0).text_frame.paragraphs[0]
                p.alignment = ALIGN["center"]
                set_lh(p, lg["symbol_size"], 1.0)      # 「●」の行の高さを固定する
                set_run(p.add_run(), "●", lg["symbol_size"], C(it.get("color", "text")))
                p = lt.cell(k, 1).text_frame.paragraphs[0]
                set_lh(p, lg["size"], lg["line_height"])
                set_run(p.add_run(), str(it.get("label", "")), lg["size"], C(lg["color"]))

        tr = st["table"]
        geo = status_table_geometry(data, st)
        bc = str(C(tr["border_color"]))
        cols = data.get("columns", [])
        table = _plain_table(slide, len(geo["rows"]) + 1, len(cols), tr["x"], tr["y"], geo["ws"],
                             [tr["header_h"]] + [r["h"] for r in geo["rows"]])
        for j, name in enumerate(cols):
            cell = table.cell(0, j)
            _fill_cell(cell, tr["header_fill"], bc)
            p = cell.text_frame.paragraphs[0]
            p.alignment = ALIGN["center"]
            set_run(p.add_run(), str(name), tr["header_size"], C(tr["header_color"]), bold=True)
        for i, r in enumerate(geo["rows"]):
            row = r["row"]
            cell = table.cell(i + 1, 0)
            _fill_cell(cell, tr["label_fill"], bc)
            p = cell.text_frame.paragraphs[0]
            p.alignment = ALIGN["center"]
            set_run(p.add_run(), str(row.get("label", "")), tr["label_size"], C(tr["label_color"]))
            cell = table.cell(i + 1, 1)
            _fill_cell(cell, tr["status_fill"], bc)
            p = cell.text_frame.paragraphs[0]
            p.alignment = ALIGN["center"]
            set_run(p.add_run(), "●", tr["status_size"], C(status_color(data, row.get("status"))))
            for j, paras in enumerate(r["cells"]):
                cell = table.cell(i + 1, j + 2)
                _fill_cell(cell, tr["cell_fill"], bc, pad_x=tr["pad_x"], pad_y=tr["pad_y"], anchor="top")
                tf = cell.text_frame
                for n, (lv, text) in enumerate(paras):
                    p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
                    set_lh(p, tr["cell_size"], tr["line_height"])
                    p.space_after = PTS(tr["item_gap"])
                    marker = tr["check_char"] if lv == 0 else tr["bullet_char"]
                    _set_bullet(p, marker, C(tr["marker_color"]), tr["indent"] * (lv + 1), tr["indent"])
                    run = p.add_run()
                    set_run(run, text, tr["cell_size"], C(tr["cell_color"]))
                    if lv == 0 and tr.get("heading_underline"):
                        run.font.underline = True

    def s_code(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        r = st["code"]
        size, lines = fit_code_size(data.get("code", ""), r)
        add_rect(slide, r["x"], r["y"], r["w"], r["h"], C(r["fill"]), radius=r.get("radius", 0))
        tf = add_box(slide, {"x": r["x"] + r["pad"], "y": r["y"] + r["pad"],
                             "w": r["w"] - 2 * r["pad"], "h": r["h"] - 2 * r["pad"]})
        tf.word_wrap = False  # M-24: HTML の <pre>（折り返しなし）に合わせる
        used = [False]
        for line in lines:
            p = para(tf, used)
            # M-24: spcPct（倍率）ではなく spcPts（px 起源の実寸 pt）で行送りを指定し、
            # HTML の line-height と同じ実測値に揃える。
            set_lh(p, size, r["line_height"])
            set_run(p.add_run(), line if line else " ", size, C(r["color"]),
                    name=fonts["code"])

    def s_quote(slide, data, st, page, total):
        hero_pptx(slide, data, st)
        if st["mark"].get("w") and st["mark"].get("h") and not hero.mark_is_vector(st):
            text_region(slide, st["mark"], "“")
        text_region(slide, st["text"], data.get("text", ""), font=HEADING_FONT)
        if data.get("attribution"):
            text_region(slide, st["attribution"], "— " + data["attribution"])

    def _load_pptx_picture(deck_dir_, rel_path, r, i, t):
        """image_source() 経由で PPTX 埋め込み用の画像パスを解決する（X-4: リサイズ・再圧縮
        キャッシュを HTML と共有、M-72: webp/tiff/bmp は PNG 化）。変換が必要なのに Pillow 不在等で
        変換できなかった場合は、生トレースバックの代わりに分かりやすいエラーで止める。"""
        src = image_source(deck_dir_, rel_path, True, browser, target_w=r.get("w"), target_h=r.get("h"))
        if src.suffix.lower() in PPTX_PNG_CONVERT_EXTS:
            fail(f"{i}枚目（type={t}）: 画像形式 '{src.suffix}' は PowerPoint 非対応のため PNG に変換が"
                 f"必要ですが失敗しました（Pillow を導入してください）")
        return src

    def _place_picture(slide, img_path, r, i, t):
        """画像を枠へ等比フィットして配置する（M-20: 縮小方向のクランプは外し拡大も行う）。
        枠に対して大きく拡大する場合（元解像度が枠の50%未満相当）は粗くなる旨を warn する。"""
        pic = slide.shapes.add_picture(str(img_path), IN(r["x"]), IN(r["y"]))
        ratio = min(IN(r["w"]) / pic.width, IN(r["h"]) / pic.height)
        if ratio > 2.0:
            warn(f"{i}枚目（type={t}）: 画像の解像度が表示枠に対して低く（約{ratio:.1f}倍に拡大）、"
                 f"粗く見える可能性があります。より高解像度の画像を用意してください")
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
        pic.left = int(IN(r["x"]) + (IN(r["w"]) - pic.width) / 2)
        pic.top = int(IN(r["y"]) + (IN(r["h"]) - pic.height) / 2)
        if r.get("radius"):
            # radius.image（px）: 画像の形を角丸四角にして、角丸の半径を短辺に対する比率で指定
            pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
            av = pic._element.spPr.find(qn("a:prstGeom")).find(qn("a:avLst"))
            for gd in list(av):
                av.remove(gd)
            gd = av.makeelement(qn("a:gd"), {"name": "adj", "fmla": f"val {int(min(0.5, r['radius'] / max(1, min(pic.width, pic.height) / 9525)) * 100000)}"})
            av.append(gd)
        return pic

    def s_image(slide, data, st, page, total):
        hero_pptx(slide, data, st)
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"], font=HEADING_FONT)
        if data.get("title"):
            text_region(slide, st["title"], data["title"], font=HEADING_FONT)
            rule_region(slide, st)
        r = st["img"]
        if data.get("fit") != "bleed":
            _place_picture(slide, _load_pptx_picture(deck_dir, data["path"], r, page, "image"), r, page, "image")
        if data.get("caption"):
            text_region(slide, st["caption"], data["caption"])
        footer(slide, st, page, total)

    def s_image_text(slide, data, st, page, total):
        bleed = data.get("bleed") is True
        if data.get("image_side") == "left":
            st = flip_image_text(st, bleed)
        hero_pptx(slide, data, st)
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"], font=HEADING_FONT)
        text_region(slide, st["title"], data.get("title", ""), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("punch"):
            text_region(slide, st["punch"], data["punch"], font=HEADING_FONT)
        add_bullets(slide, norm_items(data.get("bullets")), st["body"])
        r = st["img"]
        if not bleed:
            _place_picture(slide, _load_pptx_picture(deck_dir, data["path"], r, page, "image_text"), r, page, "image_text")
        if data.get("caption"):
            text_region(slide, st["caption"], data["caption"])
        footer(slide, st, page, total)

    def s_closing(slide, data, st, page, total):
        add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C(st["bg"]["fill"]))
        hero_pptx(slide, data, st)
        text_region(slide, st["title"], data.get("title", ""), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("bullets"):
            add_bullets(slide, norm_items(data.get("bullets")), st["body"])
        if data.get("message"):
            # M-38: body 直後に自動配置。HTML 側（closing_message_style）と共通の計算式。
            msg = closing_message_style(st, data)
            text_region(slide, msg, data["message"], font=HEADING_FONT)

    def s_agenda(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        b = st["body"]
        items = norm_items(data.get("items", []))
        num_start = data.get("num_start", 0)
        row_h = b.get("row_h", 44); gap = b.get("gap", 10); num_w = b.get("num_w", 52)
        col_gap = b.get("col_gap", 56); pitch = row_h + gap
        R = max(1, int(b["h"] // pitch))
        N = len(items)
        cols = 1 if N <= R else min(b.get("max_cols", 2), -(-N // R))
        rows = -(-N // cols)
        col_w = (b["w"] - (cols - 1) * col_gap) / cols
        noff = (row_h - b.get("num_size", 24)) / 2
        toff = (row_h - b.get("text_size", 20)) / 2
        for i, it in enumerate(items):
            c = i // rows; r = i % rows
            x = b["x"] + c * (col_w + col_gap); y = b["y"] + r * pitch
            active = it.get("active")
            if active:
                add_rect(slide, x-14, y-3, col_w+18, row_h+6, C(b.get("active_fill", "surface")), radius=rtok(theme, "node_sm", 8),
                         border=C(b["active_border"]) if b.get("active_border") else None)
            text_region(slide, {"x": x, "y": y+noff, "w": num_w, "h": row_h, "size": b.get("num_size", 24),
                                "color": b.get("num_color", "accent"), "bold": True, "line_height": 1.1}, f"{num_start+i+1:02d}")
            ty = y + toff
            if it.get("desc"):
                ty = y + (row_h - b.get("text_size", 20) * 1.2 - b.get("desc_size", 14) * 1.35) / 2
            tf_ag = text_region(slide, {"x": x+num_w, "y": ty, "w": col_w-num_w, "h": row_h, "size": b.get("text_size", 20),
                                        "color": (b.get("active_color", "primary") if active else b.get("text_color", "text")),
                                        "bold": bool(active) or bool(it.get("desc")), "line_height": 1.2}, it["text"])
            if it.get("desc"):
                p_desc = tf_ag.add_paragraph()
                set_run(p_desc.add_run(), it["desc"], b.get("desc_size", 14), C(b.get("desc_color", "muted")))

    def s_steps(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        b = st["body"]; steps = data.get("steps", [])
        n = max(1, len(steps)); gap = b.get("gap", 20)
        card_w = (b["w"] - (n-1)*gap) / n
        header_h = b.get("header_h", 60); pad = b.get("pad", 16); radius = b.get("radius", 12)
        card_h = steps_card_height(b, steps, card_w)
        row_y = b["y"] + (b["h"] - card_h) * b.get("content_y_ratio", 0.4)
        for i, step in enumerate(steps):
            x = b["x"] + i * (card_w + gap)
            add_rect(slide, x, row_y, card_w, card_h, C(b.get("card_fill", "surface")), radius=radius,
                     border=C(b["card_border"]) if b.get("card_border") else None,
                     border_w=b.get("border_w"), shadow=shadow_spec(b, theme))
            if data.get("header_style") == "arrow":
                ce.add_canvas_to_pptx(slide, [steps_arrow_header(i, n, x, row_y, card_w, gap, header_h, b, theme)])
            else:
                add_rect(slide, x, row_y, card_w, header_h, C(b.get("header_fill", "primary")), radius=radius,
                         top_only=True)   # HTML は上辺の 2 隅だけ丸い
            text_region(slide, {"x": x+pad, "y": row_y+9, "w": card_w-2*pad, "h": 18, "size": 13,
                                "color": b.get("num_color", "accent"), "bold": True, "weight": label_weight(theme)},
                        f"{i+1}" if b.get("_num_short") else f"STEP {i+1}")
            text_region(slide, {"x": x+pad, "y": row_y+28, "w": card_w-2*pad, "h": header_h-26,
                                "size": b.get("label_size", 18), "color": b.get("header_color", "on_primary"),
                                "bold": True, "weight": label_weight(theme), "line_height": 1.15}, step.get("label", ""), font=HEADING_FONT)
            itemr = {"x": x+pad, "y": row_y+header_h+pad, "w": card_w-2*pad, "h": card_h-header_h-2*pad,
                     "size": b.get("item_size", 15), "gap": b.get("item_gap", 8), "color": b.get("item_color", "text"),
                     "line_height": 1.4, "marker_color": "accent", "child_size": b.get("child_size", 13),
                     "child_color": "muted", "indent": 16, "child_gap": b.get("child_gap", 4)}
            tf_items = add_bullets(slide, norm_items(step.get("items", [])), itemr)
            # style.body.valign（既定 top）: "middle" で items をカードの残り高さの中で縦中央寄せにする
            # （HTML と同じ考え方。ヘッダー帯は動かさない）。
            if b.get("valign", "top") == "middle":
                tf_items.vertical_anchor = MSO_ANCHOR.MIDDLE
            if i < n-1 and data.get("header_style") != "arrow":
                text_region(slide, {"x": x+card_w, "y": row_y+card_h/2-18, "w": gap, "h": 36,
                                    "size": b.get("chevron_size", 28), "color": b.get("chevron_color", "accent"),
                                    "align": "center", "bold": True}, "›")

    def s_matrix(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        g = st["grid"]; ax = st.get("axis", {})
        gx, gy, gw, gh = g["x"], g["y"], g["w"], g["h"]
        gap = g.get("gap", 14); pad = g.get("pad", 18); radius = g.get("radius", 12)
        valign = g.get("valign", "top")
        cw = (gw - gap) / 2; ch = (gh - gap) / 2
        quads = data.get("quadrants", [])
        positions = [(gx, gy), (gx+cw+gap, gy), (gx, gy+ch+gap), (gx+cw+gap, gy+ch+gap)]
        for qi, (qx, qy) in enumerate(positions):
            q = quads[qi] if qi < len(quads) else {}
            hi = q.get("highlight")
            fill = C(g.get("hi_fill", "on_primary_soft")) if hi else C(g.get("fill", "surface"))
            add_rect(slide, qx, qy, cw, ch, fill, radius=radius,
                     border=C(g["border_color"]) if g.get("border_color") else None,
                     border_w=g.get("border_w"), shadow=shadow_spec(g, theme))
            # M-37: heading を含めたコンテンツ全体を象限中央に配置する（HTML と同じ計算式）。
            lay = _matrix_content_layout(q.get("body", ""), g, cw, ch, pad, valign)
            text_region(slide, {"x": qx+pad, "y": qy+lay["head_y"], "w": cw-2*pad, "h": lay["head_h"],
                                "size": g.get("heading_size", 18),
                                "color": (g.get("hi_heading_color", "accent") if hi else g.get("heading_color", "primary")),
                                "bold": True, "weight": label_weight(theme), "line_height": 1.2}, q.get("heading", ""), font=HEADING_FONT)
            tf_body = text_region(slide, {"x": qx+pad, "y": qy+lay["body_y"], "w": cw-2*pad, "h": lay["body_h"],
                                "size": g.get("body_size", 14), "color": g.get("body_color", "muted"),
                                "line_height": 1.4}, q.get("body", ""))
            if valign == "middle":
                tf_body.vertical_anchor = MSO_ANCHOR.MIDDLE
        xa = data.get("x_axis", {}); ya = data.get("y_axis", {})
        for ab in _matrix_axis_boxes(ax, gx, gy, gw, gh, xa, ya):
            text_region(slide, ab["region"], ab["text"])

    def s_cards(slide, data, st, page, total):
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        g = st["grid"]; cards = data.get("cards", [])
        geo = pe.cards_cells(len(cards), data.get("columns"), g, hero.card_spans(data))
        pad = g.get("pad", 18); radius = g.get("radius", 12)
        valign = g.get("valign", "top")
        for idx, card in enumerate(cards):
            x, y, cw, chh = geo["cells"][idx]
            cs = hero.card_style(g, hero.card_emphasis(card))
            gc = hero.emph_grid(g, hero.card_emphasis(card))
            add_rect(slide, x, y, cw, chh, C(cs["fill"]), radius=radius,
                     border=C(cs["border_color"]) if cs.get("border_color") else None,
                     border_w=cs.get("border_w"), shadow=shadow_spec(g, theme))
            # M-37: heading を含めたコンテンツ全体（実際に描画される段だけ）をカード中央に配置する
            # （HTML と同じ計算式）。
            lay = _cards_content_layout(card, gc, cw, chh, pad, valign)
            has_items = bool(card.get("items"))
            text_region(slide, {"x": x+pad, "y": y+lay["head_y"], "w": cw-2*pad-autofit.card_icon_reserve(card, gc), "h": lay["head_h"],
                                "size": gc.get("heading_size", 19),
                                "color": cs["heading_color"], "bold": True, "weight": label_weight(theme), "line_height": 1.2},
                        card.get("heading", ""), font=HEADING_FONT)
            if card.get("body"):
                body_r = {"x": x+pad, "y": y+lay["body_y"], "w": cw-2*pad, "h": lay["body_h"],
                          "size": gc.get("body_size", 15), "color": cs["body_color"], "line_height": 1.4}
                # 本文は固定高（44px）の箱の上詰め（HTML と同じ）。valign:middle は段全体の位置の計算（_cards_content_layout）
                # で効いており、箱の中で中央寄せにすると HTML より約 13px 下がる（A-02）
                text_region(slide, body_r, card["body"])
            if has_items:
                itemr = {"x": x+pad, "y": y+lay["items_y"], "w": cw-2*pad, "h": lay["items_h"],
                         "size": gc.get("item_size", 14),
                         "gap": g.get("item_gap", 6), "color": cs["item_color"], "line_height": 1.35,
                         "marker_color": cs["marker_color"], "child_size": 12, "child_color": cs["item_color"] if cs.get("emphasized") else "muted",
                         "indent": 14, "child_gap": 4}
                add_bullets(slide, norm_items(card["items"]), itemr)   # 上詰め（HTML と同じ。箱は内容の高さの見積もり）

    def _shape_text(sp, text, size, color, bold=False):
        """図形の中央にテキストを置く。改行（\\n）は段落に分ける（レンダラ差で崩れにくい）。"""
        tf = sp.text_frame; tf.word_wrap = True
        tf.vertical_anchor = 3
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, Emu(0))
        used = [False]
        for line in str(text).split("\n"):
            p = para(tf, used); p.alignment = PP_ALIGN.CENTER; set_lh(p, size, 1.15)   # HTML の swimlane ノードは 1.15
            set_run(p.add_run(), line, size, color, bold=bold)

    def _sw_node_pptx(slide, nd, f):
        ns = f.get("node_size", 14)
        shape = nd["shape"]; x, y, w, h = nd["x"], nd["y"], nd["w"], nd["h"]
        # swimlane_geometry で決めた縮小サイズ・折り返し行（HTML と同じ）を使う
        fs = nd.get("font_size")
        fitted = "\n".join(nd["lines"]) if nd.get("lines") else nd.get("text", "")
        io_font = nd.get("io_font", f.get("io_size", 11))
        if shape == "decision":
            sp = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("decision_fill", "on_primary_soft"))
            sp.line.color.rgb = C(f.get("decision_border", "accent")); sp.line.width = Pt(1.5); sp.shadow.inherit = False
            if nd.get("text"):
                # ひし形自体の text_frame は PowerPoint が内接矩形へ極端に幅を絞るため、
                # word_wrap=True のままだと全角文字が1文字ずつ縦に折り返されてしまう
                # （旧実装はこれを避けるため word_wrap=False にしていたが、今度は3〜4文字
                # 程度のラベルで図形の外へテキストがはみ出していた）。HTML 側は箱全体の幅 w
                # で自然に複数行へ折り返しており、ここでも同じ幅の別レイヤーのテキストボックスを
                # ひし形の上に重ねることで、はみ出しと縦1文字折り返しの両方を避ける。
                tb = slide.shapes.add_textbox(IN(x), IN(y), IN(w), IN(h))
                _shape_text(tb, fitted, fs or ns - 2, C(f.get("decision_color", "primary")))
        elif shape == "terminal":
            # M-48: HTML のスタジアム型（border-radius:h/2）に合わせ、真円ではなく
            # 角丸長方形＋adjustments[0]=0.5 で描く。
            sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.adjustments[0] = min(0.5, rtok(theme, "pill", 999) / max(1, min(w, h)))   # pill = 0 なら角丸なし
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("terminal_fill", "surface"))
            sp.line.color.rgb = C(f.get("terminal_border", "muted")); sp.line.width = Pt(1.25); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, fitted, fs or ns - 2, C(f.get("terminal_color", "muted")))
        elif shape == "connector":
            sp = slide.shapes.add_shape(MSO_SHAPE.PENTAGON, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("connector_fill", "surface"))
            sp.line.color.rgb = C(f.get("connector_border", "muted")); sp.line.width = Pt(1); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, fitted, fs or ns - 3, C(f.get("connector_color", "text")))
        elif shape == "marker":
            kind = nd.get("kind", "mid")
            mc = {"start": f.get("marker_start", "accent"), "end": f.get("marker_end", "primary"),
                  "mid": f.get("marker_mid", "#E6B800")}.get(kind, f.get("marker_mid", "#E6B800"))
            sp = slide.shapes.add_shape(MSO_SHAPE.OVAL, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(mc)
            sp.line.color.rgb = C("background"); sp.line.width = Pt(1.25); sp.shadow.inherit = False
        elif shape == "mail":
            sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C("background")
            sp.line.color.rgb = C(f.get("edge_color", "text")); sp.line.width = Pt(1.25); sp.shadow.inherit = False
            cxm = x + w / 2; my = y + h * 0.55
            for (x1, y1, x2, y2) in ((x, y, cxm, my), (cxm, my, x + w, y)):
                cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(y1), IN(x2), IN(y2))
                cn.line.color.rgb = C(f.get("edge_color", "text")); cn.line.width = Pt(1.25); cn.shadow.inherit = False
        elif shape == "io":
            sp = add_rect(slide, x, y, w, h, C(f.get("io_fill", "on_primary_soft")), radius=rtok(theme, "node_sm", 8))
            sp.line.color.rgb = C(f.get("io_border", "accent")); sp.line.width = Pt(1)
            half = (w - 2) / 2
            for idx, (key, lbl) in enumerate((("input", "input"), ("output", "output"))):
                vals = nd.get(key) or []
                tf = add_box(slide, {"x": x + idx * half + 6, "y": y + 6, "w": half - 10, "h": h - 12})
                p0 = tf.paragraphs[0]
                set_run(p0.add_run(), lbl, io_font, C(f.get("io_head_color", "accent")), bold=True)
                fitted_io = (nd.get("io_lines") or {}).get(key)
                for it in (fitted_io or [[v] for v in vals]):
                    for ln in it:
                        pp = tf.add_paragraph()
                        set_run(pp.add_run(), ln, io_font, C(f.get("io_color", "text")))
        elif shape == "system":
            sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(f.get("system_fill", "surface"))
            sp.line.color.rgb = C(f.get("system_border", "muted")); sp.line.width = Pt(1.5); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, fitted, fs or ns, C(f.get("system_color", "text")))
        else:  # task (+variant)
            variant = nd.get("variant") or "onother"
            vmap = {"onpf": (f.get("task_onpf_fill", "on_primary_soft"), f.get("task_border", "accent"), f.get("task_onpf_color", "primary")),
                    "onother": (f.get("task_onother_fill", "background"), f.get("task_border", "accent"), f.get("task_color", "text")),
                    "offline": (f.get("task_offline_fill", "surface"), f.get("task_offline_border", "muted"), f.get("task_color", "text"))}
            fl, bd, cl = vmap.get(variant, vmap["onother"])
            sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(y), IN(w), IN(h))
            if (theme.get("tokens") or {}).get("radius") != shp.default_tokens().get("radius"):
                # 角丸のトークンが既定（classic）のままなら PowerPoint 既定の角丸のまま（従来の PPTX を保つ）。shape などで変えたときだけ HTML と同じ半径にする
                sp.adjustments[0] = min(0.5, f.get("node_radius", 8) / max(1, min(w, h)))
            sp.fill.solid(); sp.fill.fore_color.rgb = C(fl)
            sp.line.color.rgb = C(bd); sp.line.width = Pt(2); sp.shadow.inherit = False
            if nd.get("text"):
                _shape_text(sp, fitted, fs or ns, C(cl))
            if nd.get("loop"):
                # 反復記号: 右上角に丸バッジ＋円弧矢印（HTML と同じ位置・見た目）
                bx, by = x + w - 9, y - 9
                badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, IN(bx), IN(by), IN(18), IN(18))
                badge.fill.solid(); badge.fill.fore_color.rgb = C("background")
                badge.line.color.rgb = C("accent"); badge.line.width = Pt(1.1); badge.shadow.inherit = False
                arr = slide.shapes.add_shape(MSO_SHAPE.CIRCULAR_ARROW, IN(bx + 3.5), IN(by + 3.5), IN(11), IN(11))
                arr.fill.solid(); arr.fill.fore_color.rgb = C("accent"); arr.line.fill.background(); arr.shadow.inherit = False

    def s_swimlane(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        f = st["flow"]
        geo = swimlane_geometry(data, st, page)
        start_idx = len(slide.shapes)  # M-50: この位置から後で作る図形だけを1グループにまとめる
        # lane bands (alt stripes)
        for ln in geo["lanes"]:
            if ln["alt"]:
                add_rect(slide, f["x"], ln["y"], f["w"], ln["h"], C(f.get("lane_band_b", "surface")))
        # group boxes (Lv1): 矩形自体は回転させず、bodyPr の vert=vert270 でテキストだけ縦書きにする
        # （M-19/M-45/M-89: sp.rotation を使うと矩形の外接位置がレーンからずれてしまうため）。
        for gp in geo["groups"]:
            sp = add_rect(slide, gp["x"], gp["y"], gp["w"], gp["h"], C(f.get("group_fill", "primary")))
            _shape_text(sp, gp["label"], f.get("group_size", 13), C(f.get("group_color", "on_primary")), bold=True)
            sp.text_frame.word_wrap = False
            sp.text_frame._txBody.bodyPr.set("vert", "vert270")
        # lane labels (Lv2)
        for ln in geo["lanes"]:
            sp = add_rect(slide, ln["x"], ln["y"], ln["w"], ln["h"], C(f.get("lane_fill", "surface")))
            sp.line.color.rgb = C(f.get("lane_border", "border")); sp.line.width = Pt(0.5)
            _shape_text(sp, ln["label"], f.get("lane_size", 13), C(f.get("lane_color", "text")))
        # phase band
        for ph in geo["phases"]:
            sp = add_rect(slide, ph["x"], ph["y"], ph["w"], ph["h"], C(f.get("phase_fill", "on_primary_soft")))
            _shape_text(sp, ph["label"], f.get("phase_size", 14), C(f.get("phase_color", "primary")), bold=True)
        # edges: 共通ルーターの経路を連結コネクタで描き、ラベルは背景ピル付きでノードの上に重ねる
        # （HTML 側と同じ _edge_visual。swimlane の style:"dashed" は従来どおり edge_color で描く）。
        ed = dict(f)
        ed.setdefault("edge_dashed_color", f.get("edge_color", "text"))
        ed.setdefault("label_fill", "background")
        for e in geo["edges"]:
            vis = _edge_visual(e, ed)
            arrow = e.get("arrow", "end")
            _poly_pptx(slide, e["points"], C(vis["color"]), vis["w"], vis["pptx_dash"],
                       arrow_end=arrow in ("end", "both"), arrow_start=(arrow == "both"), open_arrow=vis["open"])
        # nodes
        for nid, nd in geo["nodes"].items():
            _sw_node_pptx(slide, nd, f)
        for e in geo["edges"]:
            _label_pill_pptx(slide, e, ed, f.get("label_size", 13))
        # M-50: 図全体（タイトル等のチロームは除く）を1つの p:grpSp にまとめ、
        # PowerPoint 上でまとめて移動・拡大縮小できるようにする。
        group_shapes = list(slide.shapes)[start_idx:]
        if len(group_shapes) > 1:
            slide.shapes.add_group_shape(group_shapes)

    def s_swimlane_legend(slide, data, st, page, total):
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"], font=HEADING_FONT)
        text_region(slide, st["title"], data.get("title", "凡例"), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("lead") and "lead" in st:
            text_region(slide, st["lead"], data["lead"])
        a = st["area"]; sym = st.get("sym", {})
        legend_start_idx = len(slide.shapes)
        entries = data.get("items") or SWIMLANE_LEGEND
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 60); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 120)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, (shape, vk, label, desc) in enumerate(entries):
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h; cy = y + row_h / 2
            sw, sh = _legend_sym_size(shape)
            scx = x + sym_w / 2
            if shape == "flow":
                x1, x2 = scx - sw / 2, scx + sw / 2
                conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(cy), IN(x2), IN(cy))
                conn.line.color.rgb = C(sym.get("edge_color", "text")); conn.line.width = Pt(2); conn.shadow.inherit = False
                lnx = conn.line._get_or_add_ln()
                if vk == "dashed":
                    lnx.append(lnx.makeelement(qn("a:prstDash"), {"val": "dash"}))
                lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
            else:
                nd = {"shape": shape, "variant": (vk if shape == "task" else None),
                      "kind": (vk if shape == "marker" else None), "text": "",
                      "x": scx - sw / 2, "y": cy - sh / 2, "w": sw, "h": sh,
                      "input": (["…"] if shape == "io" else None), "output": (["…"] if shape == "io" else None), "loop": None}
                _sw_node_pptx(slide, nd, sym)
            tx = x + sym_w + 8
            text_region(slide, {"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                                "size": a.get("label_size", 16), "color": "text", "bold": True}, label)
            text_region(slide, {"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                                "size": a.get("desc_size", 13), "color": "muted"}, desc)
        legend_shapes = list(slide.shapes)[legend_start_idx:]
        if len(legend_shapes) > 1:
            slide.shapes.add_group_shape(legend_shapes)
        footer(slide, st, page, total)

    def _diag_legend_sym_pptx(slide, sample, x, cy, sym_w, d):
        """diagram_legend の 1 シンボルを実図と同じ描画関数で PPTX に描く。"""
        cx = x + sym_w / 2
        if "edge" in sample:
            ev = _edge_visual({"variant": sample["edge"]}, d)
            w = 88
            _poly_pptx(slide, [(cx - w / 2, cy), (cx + w / 2, cy)], C(ev["color"]), ev["w"],
                       ev["pptx_dash"], arrow_end=True, open_arrow=ev["open"])
            return
        w, h = _diag_legend_sym_size(sample)
        box = {"label": "", "x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h}
        if "kind" in sample:
            k = sample["kind"]
            box["kind"] = k
            box["shape"] = "diamond" if k == "decision" else ("pill" if k == "start" else "rect")
            _diag_node_pptx(slide, box, {}, d, "lifecycle")
            return
        box["shape"] = "rect"
        if "node" in sample:
            box["variant"] = sample["node"]
        else:
            box["type"] = sample["icon"]
        _diag_node_pptx(slide, box, {}, d, "architecture")

    def s_diagram_legend(slide, data, st, page, total):
        if data.get("eyebrow") and "eyebrow" in st:
            text_region(slide, st["eyebrow"], data["eyebrow"], font=HEADING_FONT)
        text_region(slide, st["title"], data.get("title", "凡例"), font=HEADING_FONT)
        rule_region(slide, st)
        if data.get("lead") and "lead" in st:
            text_region(slide, st["lead"], data["lead"])
        a = st["area"]; d = st["diagram"]
        start_idx = len(slide.shapes)
        entries = data.get("items") or []
        cols = a.get("cols", 2); rows = -(-len(entries) // cols)
        col_gap = a.get("col_gap", 56); row_h = a.get("row_h", 54); sym_w = a.get("sym_w", 140)
        col_w = (a["w"] - (cols - 1) * col_gap) / cols
        for i, entry in enumerate(entries):
            sample, label = entry[0], entry[1]
            desc = entry[2] if len(entry) > 2 else ""
            c = i // rows; r = i % rows
            x = a["x"] + c * (col_w + col_gap); y = a["y"] + r * row_h; cy = y + row_h / 2
            _diag_legend_sym_pptx(slide, sample, x, cy, sym_w, d)
            tx = x + sym_w + 8
            text_region(slide, {"x": tx, "y": y + 6, "w": col_w - sym_w - 8, "h": 22,
                                "size": a.get("label_size", 16), "color": "text", "bold": True}, label)
            text_region(slide, {"x": tx, "y": y + 29, "w": col_w - sym_w - 8, "h": 20,
                                "size": a.get("desc_size", 13), "color": "muted"}, desc)
        shapes = list(slide.shapes)[start_idx:]
        if len(shapes) > 1:
            slide.shapes.add_group_shape(shapes)
        footer(slide, st, page, total)

    # -----------------------------------------------------------------------
    # ネイティブ図解タイプ（architecture / dataflow / lifecycle / sequence）の PPTX 描画。
    # ジオメトリは diagram_engine、見た目の解決は _node_visual / _edge_visual（HTML と共通）。
    # -----------------------------------------------------------------------

    def _set_dash(shape_or_conn, pptx_dash):
        if not pptx_dash:
            return
        lnx = shape_or_conn.line._get_or_add_ln()
        lnx.append(lnx.makeelement(qn("a:prstDash"), {"val": pptx_dash}))

    def _poly_pptx(slide, pts, color, width_px, pptx_dash=None, arrow_end=True, arrow_start=False, open_arrow=False):
        """直交折れ線を連結コネクタで描く。最後のセグメントに矢印（arrow_start で先頭にも）。"""
        made = []
        for k in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[k], pts[k + 1]
            if abs(x1 - x2) < 0.05 and abs(y1 - y2) < 0.05:
                continue
            conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(y1), IN(x2), IN(y2))
            conn.line.color.rgb = color
            conn.line.width = Pt(width_px * 0.75)
            conn.shadow.inherit = False
            lnx = conn.line._get_or_add_ln()
            if pptx_dash:
                lnx.append(lnx.makeelement(qn("a:prstDash"), {"val": pptx_dash}))
            head_type = "arrow" if open_arrow else "triangle"
            if k == len(pts) - 2 and arrow_end:
                lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": head_type, "w": "med", "len": "med"}))
            if k == 0 and arrow_start:
                lnx.append(lnx.makeelement(qn("a:headEnd"), {"type": head_type, "w": "med", "len": "med"}))
            made.append(conn)
        return made

    def _outline(sp, color, width_px, pptx_dash=None):
        sp.fill.background()
        sp.line.color.rgb = color
        sp.line.width = Pt(width_px * 0.75)
        sp.shadow.inherit = False
        _set_dash(sp, pptx_dash)
        return sp

    def _icon_pptx(slide, kind, x, y, s, color):
        """type アイコンをプリセット図形の組合せで近似する（HTML の 16×16 線画に対応）。"""
        lw = 1.4
        if kind == "database":
            _outline(slide.shapes.add_shape(MSO_SHAPE.CAN, IN(x + s * 0.12), IN(y), IN(s * 0.76), IN(s)), color, lw)
        elif kind == "cloud":
            _outline(slide.shapes.add_shape(MSO_SHAPE.CLOUD, IN(x), IN(y + s * 0.14), IN(s), IN(s * 0.72)), color, lw)
        elif kind == "security":
            _outline(slide.shapes.add_shape(MSO_SHAPE.FLOWCHART_OFFPAGE_CONNECTOR, IN(x + s * 0.1), IN(y), IN(s * 0.8), IN(s)), color, lw)
        elif kind == "frontend":
            _outline(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y + s * 0.12), IN(s), IN(s * 0.76)), color, lw)
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y + s * 0.12), IN(s), IN(s * 0.2))
            bar.fill.solid(); bar.fill.fore_color.rgb = color; bar.line.fill.background(); bar.shadow.inherit = False
        elif kind == "backend":
            _outline(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y + s * 0.1), IN(s), IN(s * 0.32)), color, lw)
            _outline(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y + s * 0.58), IN(s), IN(s * 0.32)), color, lw)
        elif kind == "messagebus":
            for fy, fw in ((0.25, 1.0), (0.5, 0.72), (0.75, 1.0)):
                _poly_pptx(slide, [(x, y + s * fy), (x + s * fw, y + s * fy)], color, lw, arrow_end=(fy == 0.5), open_arrow=True)
        elif kind == "external":
            # 外部リンク（箱＋右上へ抜ける矢印）。箱は右上を欠いた形の代わりに全周矩形で近似する
            _outline(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(x + s * 0.15), IN(y + s * 0.25), IN(s * 0.6), IN(s * 0.6)), color, lw)
            _poly_pptx(slide, [(x + s * 0.47, y + s * 0.53), (x + s * 0.9, y + s * 0.1)], color, lw, arrow_end=True, open_arrow=True)

    def _glyph_pptx(slide, kind, x, y, s, color):
        """lifecycle kind の小グリフ（右上）。"""
        lw = 1.6
        if kind == "success":
            _poly_pptx(slide, [(x + s * 0.18, y + s * 0.55), (x + s * 0.42, y + s * 0.78)], color, lw, arrow_end=False)
            _poly_pptx(slide, [(x + s * 0.42, y + s * 0.78), (x + s * 0.85, y + s * 0.28)], color, lw, arrow_end=False)
        elif kind == "failure":
            _poly_pptx(slide, [(x + s * 0.22, y + s * 0.22), (x + s * 0.78, y + s * 0.78)], color, lw, arrow_end=False)
            _poly_pptx(slide, [(x + s * 0.78, y + s * 0.22), (x + s * 0.22, y + s * 0.78)], color, lw, arrow_end=False)
        elif kind == "waiting":
            _outline(slide.shapes.add_shape(MSO_SHAPE.FLOWCHART_COLLATE, IN(x + s * 0.2), IN(y + s * 0.08), IN(s * 0.6), IN(s * 0.84)), color, 1.2)
        elif kind == "start":
            sp = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, IN(x + s * 0.28), IN(y + s * 0.2), IN(s * 0.5), IN(s * 0.6))
            sp.rotation = 90
            sp.fill.solid(); sp.fill.fore_color.rgb = color; sp.line.fill.background(); sp.shadow.inherit = False

    def _diag_text_pptx(slide, r, lines, size, color, sub_lines=None, sub_size=11, sub_color=None, font=None):
        """箱の中央に label（太字・複数行）＋ sublabel（小）を描く（上下中央・左右中央）。"""
        from pptx.enum.text import MSO_ANCHOR
        tf = add_box(slide, r)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.word_wrap = True
        used = [False]
        for ln in (lines or [""]):
            p = para(tf, used)
            p.alignment = PP_ALIGN.CENTER
            set_lh(p, size, 1.15)   # HTML の図解ノードのラベルは 1.15
            set_run(p.add_run(), ln, size, color, bold=True, name=font)
        for ln in (sub_lines or []):
            p = para(tf, used)
            p.alignment = PP_ALIGN.CENTER
            set_lh(p, sub_size, 1.2)   # HTML の sublabel は 1.2
            p.space_before = PTS(2)
            set_run(p.add_run(), ln, sub_size, sub_color if sub_color is not None else color)
        return tf

    def _diag_node_pptx(slide, b, fit, d, kind):
        vis = _node_visual(b, d, kind, rtok(theme, "pill", 999))
        hx = _node_hexes(vis, d, theme, b)
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        pad = d.get("node_pad", 8)
        radius = d.get("node_radius", 10)
        fill = C(vis["fill"]); border = C(vis["border"])
        dash = "dash" if vis["dash"] else None
        icon_w = 0.0
        if vis["shape"] == "diamond":
            sp = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, IN(x), IN(y), IN(w), IN(h))
            sp.fill.solid(); sp.fill.fore_color.rgb = fill
            sp.line.color.rgb = border; sp.line.width = Pt(vis["border_w"] * 0.75); sp.shadow.inherit = False
            _set_dash(sp, dash)
            tx, tw = x + w * 0.12, w * 0.76
        else:
            sp = add_rect(slide, x, y, w, h, fill, radius=radius, border=border)
            sp.line.width = Pt(vis["border_w"] * 0.75)
            _set_dash(sp, dash)
            if vis["shape"] == "pill" and len(sp.adjustments):
                sp.adjustments[0] = min(0.5, rtok(theme, "pill", 999) / max(1, min(w, h)))   # pill = 0 なら角丸なし
            icon_size = d.get("icon_size", 16)
            ntype = b.get("type") or "generic"
            if kind != "lifecycle" and ntype in ICON_PATHS:
                if d.get("icon_style") == "aws":
                    tsz = d.get("icon_tile_size", 30)
                    add_rect(slide, x + pad, y + h / 2 - tsz / 2, tsz, tsz, C(_icon_tile_color(d, ntype)), radius=rtok(theme, "small", 6))
                    gs = tsz * 0.58
                    _icon_pptx(slide, ntype, x + pad + (tsz - gs) / 2, y + h / 2 - gs / 2, gs, C("#ffffff"))
                    icon_w = tsz + 8
                else:
                    _icon_pptx(slide, ntype, x + pad, y + h / 2 - icon_size / 2, icon_size, C(hx["icon"]))
                    icon_w = icon_size + 6
            tx = x + pad + icon_w
            tw = max(10.0, w - 2 * pad - icon_w)
        size = fit.get("size", d.get("node_size", 14)) if fit else d.get("node_size", 14)
        lines = (fit.get("lines") if fit else None) or [b.get("label", "")]
        sub_lines = (fit.get("sub_lines") if fit else None) or ([b["sublabel"]] if b.get("sublabel") else [])
        _diag_text_pptx(slide, {"x": tx, "y": y + 2, "w": tw, "h": h - 4}, lines, size, C(hx["color"]),
                        sub_lines, d.get("sub_size", 11), C(hx["sub"]), font=HEADING_FONT)
        if b.get("tag"):
            ts = d.get("tag_size", 10)
            tw_ = de.text_width(b["tag"], ts) + 12
            pill = add_rect(slide, x + w - tw_ - 8, y - ts * 0.8, tw_, ts * 1.6, C(d.get("tag_fill", "highlight_fill")),
                            radius=min(ts * 0.8, rtok(theme, "pill", 999)))      # HTML のタグピルと同じ半径（高さ ts*1.6 の半分で頭打ち。pill = 0 は四角）
            _shape_text(pill, b["tag"], ts, C(hx["tag"]), bold=True)
        if kind == "lifecycle":
            if b.get("step"):
                sp_ = _step_label_spec(b, vis, d, theme, hx)
                text_region(slide, {"x": sp_["x"], "y": sp_["y"] - 1, "w": 40, "h": sp_["size"] * 1.4, "size": sp_["size"],
                                    "color": sp_["color"], "bold": True}, b["step"])
            k = b.get("kind") or "active"
            if k in KIND_GLYPHS and vis["shape"] == "rect":
                gc = C(hx["color"]) if k == "success" else C(hx["glyph"])
                _glyph_pptx(slide, k, x + w - 21, y + 5, 13, gc)

    def _label_pill_pptx(slide, e, d, lsize):
        for lb, ltext, classification in ((e.get("label_box"), e.get("label"), e.get("classification")),
                                          (e.get("label_back_box"), e.get("label_back"), None)):
            if not lb or not ltext:
                continue
            pill = add_rect(slide, lb["x"], lb["y"], lb["w"], lb["h"], C(d.get("label_fill", "background")), radius=min(4, rtok(theme, "small", 6)))
            if classification:
                cs = d.get("class_size", 11)
                _diag_text_pptx(slide, {"x": lb["x"] - 20, "y": lb["y"], "w": lb["w"] + 40, "h": lb["h"]},
                                [ltext], lsize, C(d.get("label_color", "accent")), [classification], cs,
                                C(d.get("class_color", "muted")))
            else:
                _shape_text(pill, ltext, lsize, C(d.get("label_color", "accent")), bold=True)
                pill.text_frame.word_wrap = False

    def _edges_pptx(slide, edges, d):
        lsize = d.get("label_size", 13)
        for e in edges:
            vis = _edge_visual(e, d)
            arrow = e.get("arrow", "end")
            _poly_pptx(slide, e["points"], C(vis["color"]), vis["w"], vis["pptx_dash"],
                       arrow_end=arrow in ("end", "both"), arrow_start=(arrow == "both"), open_arrow=vis["open"])
        for e in edges:
            _label_pill_pptx(slide, e, d, lsize)

    def _group_pptx(slide, g, d):
        kind = g.get("kind") or "generic"
        radius = d.get("group_radius", 10)
        gc = d.get("group_color", "muted")
        if kind == "zone":
            sp = add_rect(slide, g["x"], g["y"], g["w"], g["h"], C(d.get("zone_fill", "surface")), radius=radius,
                          border=C(d.get("group_border", "muted")))
        else:
            sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(g["x"]), IN(g["y"]), IN(g["w"]), IN(g["h"]))
            sp.adjustments[0] = min(0.5, radius / max(1, min(g["w"], g["h"])))
            bc = d.get("security_group_border", "primary") if kind == "security" else d.get("group_border", "muted")
            _outline(sp, C(bc), 1.5, "dash")
            if kind == "security":
                gc = bc
        if g.get("label"):
            gs = d.get("group_size", 12)
            text_region(slide, {"x": g["x"] + 10, "y": g["y"] + 3, "w": max(40, g["w"] - 20), "h": gs * 1.5,
                                "size": gs, "color": gc, "bold": True}, g["label"])

    def _legend_pptx(slide, items, y, x, d):
        ls = d.get("legend_size", 12)
        cx = x
        for it in items:
            _icon_pptx(slide, it["type"], cx, y + (d.get("legend_h", 26) - 14) / 2, 14, C(d.get("icon_color", "accent")))
            lw = de.text_width(it["label"], ls) + 6
            text_region(slide, {"x": cx + 19, "y": y + 4, "w": lw + 8, "h": ls * 1.5, "size": ls,
                                "color": d.get("legend_color", "muted")}, it["label"])
            cx += 19 + lw + 22

    def _grid_diagram_pptx(slide, data, st, kind):
        geo = dscale.layout_grid(data, kind, st["diagram"], [])
        d = dscale.scaled_style(st["diagram"])
        start_idx = len(slide.shapes)
        for rh in geo["row_headers"]:
            if rh["alt"]:
                add_rect(slide, rh["band_x"], rh["y"], rh["band_w"], rh["h"], C(d.get("row_band_b", "surface")))
            sp = add_rect(slide, rh["x"], rh["y"], rh["w"], rh["h"], C(d.get("row_fill", "surface")))
            sp.line.color.rgb = C(d.get("row_border", "border")); sp.line.width = Pt(0.5)
            _shape_text(sp, rh["label"], d.get("row_size", 13), C(d.get("row_color", "text")))
        for rh in geo["row_headers"]:
            _poly_pptx(slide, [(rh["band_x"], rh["y"]), (rh["band_x"] + rh["band_w"], rh["y"])],
                       C(d.get("row_border", "border")), 1, arrow_end=False)
        if geo["row_headers"]:
            last = geo["row_headers"][-1]
            _poly_pptx(slide, [(last["band_x"], last["y"] + last["h"]), (last["band_x"] + last["band_w"], last["y"] + last["h"])],
                       C(d.get("row_border", "border")), 1, arrow_end=False)
        for ch in geo["col_headers"]:
            sp = add_rect(slide, ch["x"] + 1, ch["y"], ch["w"] - 2, ch["h"], C(d.get("header_fill", "highlight_fill")))
            _shape_text(sp, ch["label"], d.get("header_size", 14), C(d.get("header_color", "text")), bold=True)
        for g in geo["groups"]:
            _group_pptx(slide, g, d)
        lsize = d.get("label_size", 13)
        for e in geo["edges"]:
            vis = _edge_visual(e, d)
            arrow = e.get("arrow", "end")
            _poly_pptx(slide, e["points"], C(vis["color"]), vis["w"], vis["pptx_dash"],
                       arrow_end=arrow in ("end", "both"), arrow_start=(arrow == "both"), open_arrow=vis["open"])
        for nid, b in geo["nodes"].items():
            _diag_node_pptx(slide, b, geo["text"].get(nid, {}), d, kind)
        for e in geo["edges"]:
            _label_pill_pptx(slide, e, d, lsize)
        if geo["legend"]:
            _legend_pptx(slide, geo["legend"], geo["legend_y"], d["x"] + 4, d)
        group_shapes = list(slide.shapes)[start_idx:]
        if len(group_shapes) > 1:
            slide.shapes.add_group_shape(group_shapes)

    def s_architecture(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        _grid_diagram_pptx(slide, data, st, "architecture")

    def s_dataflow(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        _grid_diagram_pptx(slide, data, st, "dataflow")

    def s_lifecycle(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        _grid_diagram_pptx(slide, data, st, "lifecycle")

    def s_sequence(slide, data, st, page, total):
        chrome(slide, data, st, page, total)
        geo = dscale.layout_seq(data, st["diagram"], [])
        d = dscale.scaled_style(st["diagram"])
        start_idx = len(slide.shapes)
        for sg in geo["segments"]:
            sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(sg["x"]), IN(sg["y"]), IN(sg["w"]), IN(sg["h"]))
            sp.adjustments[0] = min(0.5, min(6, rtok(theme, "small", 6)) / max(1, min(sg["w"], sg["h"])))
            _outline(sp, C(d.get("segment_border", "muted")), 1, "dash")
        for pid in geo["order"]:
            pb = geo["participants"].get(pid)
            if not pb:
                continue
            _poly_pptx(slide, [(pb["cx"], geo["lifeline_top"]), (pb["cx"], geo["lifeline_bottom"])],
                       C(d.get("lifeline_color", "muted")), d.get("lifeline_w", 1.5), "dash", arrow_end=False)
        # 区間の見出しは生存線より上（背景つきの札で生存線を隠す。HTML と同じ重なり順）
        for sg in geo["segments"]:
            if sg.get("label"):
                ss = d.get("segment_size", 12)
                lw = de.text_width(sg["label"], ss) + 12
                bg = add_rect(slide, sg["x"] + 8, sg["y"] - ss * 0.75, lw, ss * 1.5, C("background"))
                _shape_text(bg, sg["label"], ss, C(d.get("segment_color", "muted")), bold=True)
                bg.text_frame.word_wrap = False
        for a in geo["activations"]:
            sp = add_rect(slide, a["x"], a["y"], a["w"], a["h"], C(d.get("activation_fill", "highlight_fill")), radius=rtok(theme, "tiny", 3),
                          border=C(d.get("activation_border", "accent")))
            sp.line.width = Pt(1.1)
        _edges_pptx(slide, geo["messages"], d)
        fit = de.check_node_text(geo["participants"], d.get("node_size", 14), d.get("sub_size", 11), d.get("node_pad", 8), [],
                                 icon_w=d.get("icon_size", 16) + 6)
        for pid, pb in geo["participants"].items():
            _diag_node_pptx(slide, dict(pb, shape="rect"), fit.get(pid, {}), d, "sequence")
        group_shapes = list(slide.shapes)[start_idx:]
        if len(group_shapes) > 1:
            slide.shapes.add_group_shape(group_shapes)

    def s_schedule(slide, data, st, page, total):
        """矢羽根スケジュール。PowerPoint で後から直せるよう、すべてネイティブ図形
        （矢羽根＝ホームベース/山形、節目＝ひし形、見出し＝四角形、罫線＝直線）で描き、
        文字は図形自体のテキストとして入れる（画像化しない）。"""
        from pptx.enum.text import MSO_ANCHOR
        chrome(slide, data, st, page, total)
        c = st["chart"]
        geo = se.layout_schedule(data, c)
        rg = geo["region"]
        start_idx = len(slide.shapes)
        grid = C(c.get("grid_color", "border"))
        strong_w = c.get("grid_strong_w", 2)
        # 行の縞（見出し欄＋時間軸）
        for r in geo["rows"]:
            if r["alt"]:
                add_rect(slide, r["x"], r["y"], rg["x"] + rg["w"] - r["x"], r["h"], C(c.get("row_alt_fill", "on_primary_soft")))
        # 見出し（期間・列）
        for p in geo["periods"]:
            sp = add_rect(slide, p["x"], p["y"], p["w"], p["h"], C(c.get("period_fill", "primary")),
                          border=C("background"))
            sp.line.width = Pt(1.5)
            _shape_text(sp, p["label"], p["size"], C(c.get("period_color", "on_primary")), bold=True)
            sp.text_frame.word_wrap = False
        for k in geo["columns"]:
            sp = add_rect(slide, k["x"], k["y"], k["w"], k["h"], C(c.get("col_fill", "highlight_fill")))
            _shape_text(sp, k["label"], k["size"], C(c.get("col_color", "text")))
            sp.text_frame.word_wrap = False
        # 罫線（列境界・行境界。期間境界・グループ境界・外枠は太線）
        if geo["rows"]:
            top = geo["columns"][0]["y"] if geo["columns"] else geo["rows"][0]["y"]
            for v in geo["vlines"]:
                _poly_pptx(slide, [(v["x"], top), (v["x"], v["y2"])], grid,
                           strong_w if v["strong"] else 1, arrow_end=False)
            for h in geo["hlines"]:
                _poly_pptx(slide, [(h["x1"], h["y"]), (h["x2"], h["y"])], grid,
                           strong_w if h["strong"] else 1, arrow_end=False)
        # 左端のグループ帯（縦書き）
        for g in geo["groups"]:
            sp = add_rect(slide, g["x"], g["y"], g["w"], g["h"], C(c.get("group_fill", "primary")),
                          border=C("background"))
            sp.line.width = Pt(1.5)
            gsz = c.get("group_size", 13)
            label = str(g["label"])
            if label.isascii() or len(label) * gsz * 1.15 > g["h"] - 4:
                _shape_text(sp, label, gsz, C(c.get("group_color", "on_primary")), bold=True)
                sp.text_frame.word_wrap = False
                sp.text_frame._txBody.bodyPr.set("vert", "vert270")
            else:
                # 和字の見出しは HTML（writing-mode: vertical-rl・和字は正立で縦に積む）と同じく、1 字 1 段落で積む。
                # vert270 は文字が横倒しになり小さく見えた。縦書き（eaVert）は LibreOffice が上端に寄せるので使わない
                _shape_text(sp, "\n".join(label), gsz, C(c.get("group_color", "on_primary")), bold=True)
                sp.text_frame.word_wrap = False
        # 行見出し（label ＋ sub の2段落）
        pad = c.get("label_pad", 10)
        for r in geo["rows"]:
            tf = add_box(slide, {"x": r["x"] + pad, "y": r["y"], "w": r["w"] - 2 * pad, "h": r["h"]})
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.word_wrap = False
            p0 = tf.paragraphs[0]
            set_lh(p0, r["size"], 1.3)   # HTML の schedule 行見出しは 1.3
            set_run(p0.add_run(), r["label"], r["size"], C(c.get("label_color", "text")))
            if r["sub"]:
                p1 = tf.add_paragraph()
                set_lh(p1, r["sub_size"], 1.3)
                set_run(p1.add_run(), r["sub"], r["sub_size"], C(c.get("sub_color", "muted")))
        # 現在線（矢羽根より下のレイヤー）
        if geo["today"]:
            t = geo["today"]
            _poly_pptx(slide, [(t["x"], t["y1"]), (t["x"], t["y2"])], C(c.get("today_color", "accent")),
                       c.get("today_w", 1.5), "dash", arrow_end=False)
        # 矢羽根（ホームベース / 山形 / 四角形）。矢頭の深さは adj＝head / 短辺 で HTML と一致させる
        preset = {"arrow": MSO_SHAPE.PENTAGON, "chevron": MSO_SHAPE.CHEVRON, "bar": MSO_SHAPE.RECTANGLE}
        for b in geo["bars"]:
            vis = schedule_bar_visual(b["variant"], c)
            sp = slide.shapes.add_shape(preset[b["shape"]], IN(b["x"]), IN(b["y"]), IN(b["w"]), IN(b["h"]))
            if b["shape"] != "bar":
                sp.adjustments[0] = b["head"] / max(1.0, min(b["w"], b["h"]))
            sp.fill.solid()
            sp.fill.fore_color.rgb = C(vis["fill"])
            if vis["border"]:
                sp.line.color.rgb = C(vis["border"])
                sp.line.width = Pt(1.5 * 0.75)
                _set_dash(sp, "dash" if vis["dashed"] else None)
            else:
                sp.line.fill.background()
            sp.shadow.inherit = False
            if b["label"] and b["label_pos"] not in ("after", "before"):
                _shape_text(sp, b["label"], b["size"], C(cp.readable_on(col(theme, vis["color"]), col(theme, vis["fill"]))), bold=True)
                sp.text_frame.word_wrap = False
            elif b["label"]:
                # 矢羽根の外のラベルは、行の地の色の座布団を敷く（HTML と同じ。背後の月の縦線が文字を貫通しない）
                bg = add_rect(slide, b["lbl_x"], b["y"], b["lbl_w"], b["h"],
                              C(c.get("row_alt_fill", "on_primary_soft")) if b.get("alt") else C("background"))
                _shape_text(bg, b["label"], b["size"], C(c.get("label_color", "text")), bold=True)
                bg.text_frame.word_wrap = False
        # 節目（ひし形＋ラベル）
        for m in geo["milestones"]:
            d = m["d"]
            sp = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, IN(m["cx"] - d / 2), IN(m["cy"] - d / 2), IN(d), IN(d))
            sp.fill.solid()
            sp.fill.fore_color.rgb = C(c.get("milestone_fill", "accent"))
            sp.line.color.rgb = C(c.get("milestone_border", "primary"))
            sp.line.width = Pt(0.75)
            sp.shadow.inherit = False
            if m["label"]:
                bg = add_rect(slide, m["lx"] - 2, m["ly"], m["lw"] + 4, m["lh"],
                              C(c.get("row_alt_fill", "on_primary_soft")) if m.get("alt") else C("background"))
                _shape_text(bg, m["label"], m["size"], C(c.get("milestone_color", "text")), bold=True)
                bg.text_frame.word_wrap = False
        # 凡例と注記
        lg = geo["legend"]
        if lg:
            for it in lg["items"]:
                sx, sy, sw, sh = it["x"], it["y"], it["sym_w"], it["sym_h"]
                if it["kind"] == "bar":
                    vis = schedule_bar_visual(it["variant"], c)
                    sp = slide.shapes.add_shape(MSO_SHAPE.PENTAGON, IN(sx), IN(sy), IN(sw), IN(sh))
                    sp.adjustments[0] = 7 / max(1.0, min(sw, sh))
                    sp.fill.solid()
                    sp.fill.fore_color.rgb = C(vis["fill"])
                    if vis["border"]:
                        sp.line.color.rgb = C(vis["border"])
                        sp.line.width = Pt(0.9)
                        _set_dash(sp, "dash" if vis["dashed"] else None)
                    else:
                        sp.line.fill.background()
                    sp.shadow.inherit = False
                elif it["kind"] == "milestone":
                    sp = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, IN(sx), IN(sy + 1), IN(12), IN(12))
                    sp.fill.solid()
                    sp.fill.fore_color.rgb = C(c.get("milestone_fill", "accent"))
                    sp.line.color.rgb = C(c.get("milestone_border", "primary"))
                    sp.line.width = Pt(0.75)
                    sp.shadow.inherit = False
                else:
                    _poly_pptx(slide, [(sx + 6, sy - 2), (sx + 6, sy + sh + 2)], C(c.get("today_color", "accent")),
                               c.get("today_w", 1.5), "dash", arrow_end=False)
                tf = add_box(slide, {"x": it["tx"], "y": sy - 2, "w": it["tw"] + 8, "h": sh + 4})
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf.word_wrap = False
                set_run(tf.paragraphs[0].add_run(), it["label"], it["size"], C(c.get("legend_color", "text")))
            if lg["note"]:
                tf = add_box(slide, {"x": lg["note_x"] - 8, "y": lg["note_y"] - 2, "w": lg["note_w"] + 8, "h": lg["h"] + 4})
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf.word_wrap = False
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.RIGHT
                set_run(p.add_run(), lg["note"], lg["note_size"], C(c.get("note_color", "muted")))
        # M-50: 図全体を1つのグループにまとめる（PowerPoint でまとめて移動・拡縮でき、
        # グループ内の矢羽根・文字は個別に選択して編集できる）。
        group_shapes = list(slide.shapes)[start_idx:]
        if len(group_shapes) > 1:
            slide.shapes.add_group_shape(group_shapes)

    canvas_cache = deck_dir / "build" / "_canvas_cache"

    def _canvas_svg_png(el):
        canvas_cache.mkdir(parents=True, exist_ok=True)
        import hashlib
        key = hashlib.sha1(el["svg"].encode("utf-8")).hexdigest()[:16]
        png = canvas_cache / f"svg_{key}_{int(el['w'])}x{int(el['h'])}.png"
        if not png.exists():
            src = canvas_cache / f"svg_{key}.svg"
            svg = re.sub(r"<svg\b", f'<svg width="{el["w"]}" height="{el["h"]}" preserveAspectRatio="none"',
                         el["svg"], count=1)
            src.write_text(svg, encoding="utf-8")
            try:
                svg_to_png(src, png, browser)
            except Exception as e:  # noqa: BLE001
                warn(f"canvas の SVG を PNG 化できませんでした（{e}）。PPTX では省略します")
                return None
        return png

    def _canvas_backdrop_png(el):
        try:
            from PIL import Image, ImageFilter
        except ImportError:
            return None
        canvas_cache.mkdir(parents=True, exist_ok=True)
        g = el["grid"]
        im = Image.new("RGB", (g["cols"], g["rows"]))
        im.putdata([tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in g["colors"]])
        im = im.resize((int(el["w"]), int(el["h"])), Image.BICUBIC).filter(ImageFilter.GaussianBlur(el["w"] / g["cols"] * 0.6))
        import hashlib
        png = canvas_cache / f"bd_{hashlib.sha1(''.join(g['colors']).encode()).hexdigest()[:16]}.png"
        im.save(png)
        return png

    def s_canvas(slide, d, st, page, total):
        bg = d.get("background", "#FFFFFF")
        els = [{"kind": "shape", "x": 0, "y": 0, "w": CANVAS_W, "h": CANVAS_H, "fill": bg, "name": "背景"}]
        ce.add_canvas_to_pptx(slide, els + d.get("elements", []), _canvas_svg_png, _canvas_backdrop_png,
                              image_source=canvas_image_source(deck_dir, browser))

    def s_pattern(slide, d, st, page, total):
        r = d["_resolved"]
        if r["frame"] == "body":
            chrome(slide, d, st, page, total)
            els = r["elements"]
        else:
            els = [{"kind": "shape", "x": 0, "y": 0, "w": CANVAS_W, "h": CANVAS_H, "fill": r["background"], "name": "背景"}] + r["elements"]
        ce.add_canvas_to_pptx(slide, els, _canvas_svg_png, _canvas_backdrop_png,
                              image_source=canvas_image_source(deck_dir, browser))

    def place_composite_block(slide, rb, bk, img_src, page, total):
        """合成ブロック 1 つを PPTX に置く（枠・小見出し → 本文。ブロックごとに 1 グループ）。rb は resolve_block の戻り値。
        S2d の split もこれでブロックを置ける。"""
        start = len(slide.shapes)
        frame_els, content_els = composite_block_elements(rb, theme, bk)
        if frame_els or content_els:
            ce.add_canvas_to_pptx(slide, frame_els + content_els, _canvas_svg_png, _canvas_backdrop_png, image_source=img_src)
        if not rb["native"]:
            bs = rb["bs"]
            if bs["type"] == "pattern":
                bs = {**bs, "_resolved": resolve_pattern_slide(bs, rb["st"], deck, theme, deck_dir, page, total)}
            builders[bs["type"]](slide, bs, rb["st"], page, total)
            over = pe.extras(bs, rb["st"], theme)
            if over:
                ce.add_canvas_to_pptx(slide, over)
        members = list(slide.shapes)[start:]
        # 表（p:graphicFrame）はグループに入れない。PowerPoint の UI は表をグループ化できず、グループの中の表を開けるか実機で未確認のため。
        # 表より前の図形・後の図形をそれぞれグループにし、表は元の重なり順のまま外に置く（枠 < 表 < 表より後の図形 を保つ）
        def is_frame(sh):
            return sh._element.tag.endswith("}graphicFrame")

        def group_run(run, part):
            if run:
                grp = slide.shapes.add_group_shape(run)
                grp.name = f"ブロック{rb['index'] + 1}（{rb['type']}）" + (f" {part}" if part else "")

        if any(is_frame(sh) for sh in members):
            run, part = [], 0
            for sh in members:
                if is_frame(sh):
                    if run:
                        part += 1
                        group_run(run, part)
                        run = []
                    sh.name = f"ブロック{rb['index'] + 1}（{rb['type']}）の表"
                    el = sh._element
                    el.getparent().remove(el)
                    slide.shapes._spTree.append(el)      # 作ったグループの後ろ（= 元の重なり順の位置）に戻す
                else:
                    run.append(sh)
            if run:
                part += 1
                group_run(run, part)
        else:
            group_run(members, 0)

    def s_composite(slide, d, st, page, total):
        chrome(slide, d, st, page, total)
        bk = st.get("block") or {}
        img_src = canvas_image_source(deck_dir, browser)
        for rb in st["_composite"]["blocks"]:
            place_composite_block(slide, rb, bk, img_src, page, total)

    def s_proposal(slide, d, st, page, total):
        if engine_registry.get(d["type"]).chrome:
            chrome(slide, d, st, page, total)
        ce.add_canvas_to_pptx(slide, pe.layout(d, st, theme), image_source=canvas_image_source(deck_dir, browser))

    def s_split(slide, d, st, page, total):
        hero_pptx(slide, d, st, hero.panel_plan(d, st, pe.Ctx(theme))["els"])
        chrome(slide, d, st, page, total)
        bk = st.get("block") or {}
        img_src = canvas_image_source(deck_dir, browser)
        for rb in st["_composite"]["blocks"]:
            place_composite_block(slide, rb, bk, img_src, page, total)

    builders = {
        "canvas": s_canvas,
        "pattern": s_pattern,
        "composite": s_composite,
        "split": s_split,
        **{t: s_proposal for t in engine_registry.names()},
        "title": s_title, "section": s_section, "bullets": s_bullets,
        "two_column": s_two_column, "table": s_table, "status_table": s_status_table, "code": s_code,
        "quote": s_quote, "image": s_image, "image_text": s_image_text,
        "closing": s_closing,
        "agenda": s_agenda, "steps": s_steps, "matrix": s_matrix, "cards": s_cards,
        "swimlane": s_swimlane, "swimlane_legend": s_swimlane_legend,
        "architecture": s_architecture, "dataflow": s_dataflow, "lifecycle": s_lifecycle,
        "sequence": s_sequence, "diagram_legend": s_diagram_legend,
        "schedule": s_schedule,
    }

    missing = sorted({d.get("type") for d in deck.get("slides", [])} - set(builders))
    if missing:
        fail(f"スライドタイプ {', '.join(map(str, missing))} の PPTX 描画が登録されていません"
             f" → build_deck.py の builders に足す")

    slides = deck.get("slides", [])
    total = len(slides)

    # M-25: デッキ内に SVG 画像があるときだけ Playwright/Chromium を1回起動し、
    # 全スライド分の svg_to_png() で使い回す（1点ごとの再起動を防ぐ）。
    needs_svg = any(
        (d.get("type") in ("image", "image_text")
         and str(d.get("path", "")).lower().endswith(".svg"))
        or (d.get("type") == "canvas" and any(e.get("kind") == "svg" or (e.get("kind") == "image" and str(e.get("path", "")).lower().endswith(".svg"))
                                               for e in ce.flatten(d.get("elements", []))))
        or (d.get("type") == "pattern" and _pattern_needs_svg(d, deck_dir))
        or (d.get("type") == "composite" and any(
            isinstance(bk, dict) and ((bk.get("type") == "image" and str(bk.get("path", "")).lower().endswith(".svg"))
                                      or (bk.get("type") == "pattern" and _pattern_needs_svg(bk, deck_dir)))
            for bk in (d.get("blocks") or [])))
        for d in slides
    )
    browser = None
    _pw_cm = None
    if needs_svg:
        sync_playwright = _import_sync_playwright()
        _pw_cm = sync_playwright()
        pw = _pw_cm.__enter__()
        browser = _launch_chromium(pw)

    try:
        for i, data in enumerate(slides):
            with slide_guard(f"出力{i + 1}ページ目（type={data.get('type')}）", "PPTX描画"):
                st = resolve_style(layout, deck, data)
                slide = prs.slides.add_slide(blank)
                if data["type"] == "pattern":
                    data = {**data, "_resolved": resolve_pattern_slide(data, st, deck, theme, deck_dir, i + 1, total)}
                if "bg" not in st and data["type"] != "canvas" and not (data["type"] == "pattern" and data["_resolved"]["frame"] == "full"):
                    add_rect(slide, 0, 0, CANVAS_W, CANVAS_H, C("background"))
                builders[data["type"]](slide, data, st, i + 1, total)
                over = pe.extras(data, st, theme)
                if over:
                    ce.add_canvas_to_pptx(slide, over)
                if deck.get("meta", {}).get("brand") and "brand" in st:
                    text_region(slide, st["brand"], deck.get("meta", {}).get("brand", ""))
                # 注意: notes は意図的に PPTX へ出力しない（Keynote 互換性問題のため）
    finally:
        if browser is not None:
            browser.close()
        if _pw_cm is not None:
            _pw_cm.__exit__(None, None, None)

    with slide_guard("PPTX", "仕上げ"):
        _finalize_pptx(prs, deck, deck_dir)
        if todo_marks.enabled(deck):
            todo_marks.pptx_mark(prs, layout, code_font=font_pptx(theme["fonts"].get("code")))
    try:
        prs.save(str(out_path))
    except PermissionError:
        raise OutputLockedError(f"error: {out_path} に書き込めません。PowerPoint 等で開いている場合は閉じてから再実行してください")
    _verify_saved_pptx(out_path, expect_slides=len(deck.get("slides") or []))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _note_measure_source():
    """字幅の見積もり（折り返し位置・あふれ警告・泣き別れ対策）に何のフォントを使っているかを 1 回知らせる。
    テーマのフォントがこの機械に無いのに黙って近似に落ちると、利用者は見積もりの精度を知る手がかりが無い（R2）。"""
    wanted, used = ja_text.measure_source()
    if not wanted or wanted == used:
        return
    if used:
        note(f"フォント '{wanted}' がこの環境に無いため、字幅は代替の '{used}'（ブラウザが代わりに使うフォント）で測っています"
             "（実機の PowerPoint では折り返し位置が数文字ずれることがあります）")
    else:
        note(f"フォント '{wanted}' も代替フォントもこの環境に無いため、字幅は近似（全角 1.0 / 半角 0.55）で測っています"
             "（英数字の多い文では折り返し位置が実際とずれることがあります）")


def main():
    setup_console()
    ap = argparse.ArgumentParser(description="deck.json → HTML / PPTX ビルダー v2")
    ap.add_argument("deck_dir", help="デッキのディレクトリ（deck.json を含む）")
    ap.add_argument("--html", action="store_true", help="HTML のみ生成")
    ap.add_argument("--pptx", action="store_true", help="PPTX のみ生成")
    ap.add_argument("--debug", action="store_true", help="想定外の例外を握りつぶさず、トレースバックをそのまま出す")
    args = ap.parse_args()
    global DEBUG
    DEBUG = args.debug

    deck_dir = Path(args.deck_dir).resolve()
    if not deck_dir.is_dir():
        fail(f"{deck_dir} はディレクトリではありません")
    deck, theme, layout = load_deck(deck_dir)
    _note_measure_source()
    validate_deck(deck, layout, theme, deck_dir)
    deck = expand_slides(deck, layout)
    deck = apply_line_balance(deck, layout)
    deck = apply_wrap_fix(deck, layout)
    deck_id = deck.get("meta", {}).get("id") or deck_dir.name

    out_dir = deck_dir / "build"
    out_dir.mkdir(exist_ok=True)

    # 失敗しやすい PPTX を先に作る（PPTX で落ちたとき HTML だけ新しくなる中途半端な状態を作らない）。表示は HTML → PPTX の順
    made = []
    pptx_locked = None
    if args.pptx or not args.html:
        out = out_dir / f"{deck_id}.pptx"
        try:
            build_pptx(deck, theme, layout, deck_dir, out)
            made.append(("PPTX", out))
        except OutputLockedError as e:
            # 書き込み先が開かれているだけ（内容の失敗ではない）ので、HTML は更新してから失敗で終わる
            pptx_locked = e
    if args.html or not args.pptx:
        out = out_dir / f"{deck_id}.html"
        build_html(deck, theme, layout, deck_dir, out)
        made.append(("HTML", out))
    msg = todo_marks.summary_note(todo_marks.scan_deck(deck))
    if msg:
        note(msg + ("" if todo_marks.enabled(deck) else "（meta.todo_marks が false なので強調表示はしていません）"))
    for label, out in sorted(made, key=lambda m: m[0] != "HTML"):
        print(f"{label}: {out}")
    if pptx_locked is not None:
        raise pptx_locked


if __name__ == "__main__":
    main()

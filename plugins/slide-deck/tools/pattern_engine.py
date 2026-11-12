#!/usr/bin/env python3
"""パターン（構図の型）エンジン。

「この構図をまた使いたい」スライドを JSON の型（パターン）として登録し、中身（スロット）だけ差し替えて何度でも使うための仕組み。
パターンは canvas 要素（canvas_engine と同じ形）の列＋スロット定義で、色はテーマトークンで持つので、テーマを変えれば配色も追随する。

    {"type": "pattern", "pattern": "conclusion-evidence", "slots": {"title": "...", "conclusion": "...", "evidence": [...]}}

このモジュールは「スライド + パターン + テーマ → 解決済み canvas 要素列」までを受け持つ（HTML / PPTX への描画は canvas_engine）。

公開 API（build_deck からの結線用）
    pattern_dirs(deck_dir)                       探索ディレクトリ（先勝ち）
    load_pattern(name, deck_dir)                 パターン JSON を読む（無ければ None。壊れていれば PatternError）
    validate(slide, i, deck_dir, fail, warn)     スライド側の検証（必須スロット・未知スロット・文字数・個数・展開後の canvas 検証）
    expand(slide, pattern, theme, deck, page, total) -> (elements, background)
                                                 hex に解決済みの canvas 要素列と背景色
    to_canvas_slide(...)                         expand の結果を {"type": "canvas", ...} のスライド dict にする
    check_pattern(pat, theme)                    パターン JSON 自体の検証 -> (errors, warnings)

CLI
    python3 tools/pattern_engine.py list [--deck DIR]
    python3 tools/pattern_engine.py show <名前> [--deck DIR]
    python3 tools/pattern_engine.py check <ファイル>
    python3 tools/pattern_engine.py sample <名前> --out DIR [--theme T ...] [--deck DIR]   例文で展開した確認用デッキを作る

仕様の全体は references/schema/pattern.md（docs 統合後）、または design/docs-fragments/pattern.md を参照。
"""
from __future__ import annotations

import copy
import difflib
import json
import math
import os
import re
import shutil
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canvas_engine as ce  # noqa: E402
import deck_paths  # noqa: E402
import ja_text  # noqa: E402
import shape_engine as shp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUNDLED_DIR = ROOT / "templates" / "patterns"

SLOT_KINDS = ("text", "list", "records", "image", "flag")
FIELD_KINDS = ("text", "list", "flag")             # records の項目の種類（list = 添字で引く文字列の列、flag = 真偽）
BUILTIN_VARS = ("page", "total", "deck", "slide")
LOOP_VARS = (".", "index", "count")
DEFAULT_LH = 1.15          # 段落の既定の行間（lineHeight）。proposal_engine.PARA_LH と同じ
CANVAS_W, CANVAS_H = 1280, 720
_NAME_RE = re.compile(r"^[\w\-]{1,64}$")
_VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_COLOR_KEYS = ce.COLOR_KEYS
_TEXT_KEYS = {"text", "name", "alt", "label", "path"}   # 文字列として扱う（トークン解決しない）キー
_META_KEYS = {"if", "fit", "repeat", "grid", "template", "radius", "r", "b", "balance", "role"}
_MISSING = object()

# テーマに tokens が無いとき（または一部しか無いとき）の既定の対応表。正本は同梱レイアウト（default.json）の tokens
# （shape_engine.default_tokens）。読めないときだけ、この最低限の表を使う
_FALLBACK_TOKENS = {
    "type": {"display": 60, "h1": 36, "h2": 28, "h3": 22, "body": 20, "small": 16, "caption": 13},
    "radius": {"card": 12, "small": 6, "pill": 999},
    "line": {"thin": 1, "normal": 2, "bold": 4},
    "space": {"gap": 16, "pad": 18},
}
DEFAULT_TOKENS = shp.default_tokens() or _FALLBACK_TOKENS


class PatternError(Exception):
    """パターン JSON を読めない（壊れている・形が違う）"""


FRAMES = ("full", "body")
DEFAULT_BODY_SIZE = (1136, 480)     # frame:"body" の設計寸法（幅, 高さ）の既定。見出し骨格の下の本文領域の標準（幅 1136）


def frame_of(pattern) -> str:
    """パターンの枠。"full"（既定。1280x720 全面を型が描く）か "body"（見出し骨格はプラグインが描き、型は本文領域だけ）"""
    f = pattern.get("frame") if isinstance(pattern, dict) else None
    return f if f in FRAMES else "full"


def design_size(pattern) -> tuple:
    """frame:"body" の設計寸法 (幅, 高さ)。size が正しくなければ既定。frame:"full" は (1280, 720)"""
    if frame_of(pattern) != "body":
        return (1280, 720)
    sz = pattern.get("size")
    if (isinstance(sz, (list, tuple)) and len(sz) == 2 and all(_pos(v) for v in sz)):
        return (float(sz[0]), float(sz[1]))
    return DEFAULT_BODY_SIZE


def _pos(v):
    """有限の正の数（bool・NaN・無限大は不可）"""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def _below(n):
    b = n.get("below") if isinstance(n, dict) else None
    return b if _pos(b) else None


def _below_h(n):
    """段の高さの条件（この高さ px 未満の矩形でだけ使う）。無い・正の有限の数でなければ None"""
    b = n.get("below_h") if isinstance(n, dict) else None
    return b if _pos(b) else None


def _level_key(n):
    """段の並び順: 幅の条件（below）の小さい順。同じ幅なら、高さの条件つき（below_h の小さい順）を先にする"""
    bh = _below_h(n)
    return (_below(n), 0 if bh else 1, bh or 0)


def narrow_levels(pat):
    """狭いとき用の構図の一覧（below の小さい順。同じ below なら below_h つきが先）。narrow は 1 つの辞書でも、辞書の配列でもよい
    （配列のときは幅に応じて段階的に切り替わる。例: [{"below": 700, …}, {"below": 1000, …}] なら 700 未満は 1 つ目、700〜1000 未満は 2 つ目。
    "below_h" を足した段は、矩形の高さがその値未満のときだけ使う短い構図）。
    形の違うもの（below が正の数でない・below_h が書かれていて正の数でない・elements が配列でない）は除く"""
    n = pat.get("narrow") if isinstance(pat, dict) else None
    items = n if isinstance(n, list) else [n]
    ok = [x for x in items if isinstance(x, dict) and _below(x) and isinstance(x.get("elements"), list)
          and ("below_h" not in x or _below_h(x))]
    return sorted(ok, key=_level_key)


def narrow_of(pat):
    """幅が狭いとき用の構図のうち、いちばん広い幅まで効くもの（below が最大。1 つだけの型ならそれ。高さの条件つきの段は数えない）
    {"below": 700, "size": [560, 380], "elements": […], "variants_by": …, "variants": …}。無い・形が違えば None"""
    lv = [x for x in narrow_levels(pat) if not _below_h(x)] or narrow_levels(pat)
    return lv[-1] if lv else None


def narrow_for(pat, width, height=None):
    """置く矩形の幅 width（px）・高さ height（px。分からなければ None）に合う狭い構図。
    w < below（かつ、段に below_h があれば h < below_h）を満たす段のうち、below が最小のもの（同じ below なら高さの条件つきが先）。
    below_h のある段に "no_max_width": true があれば、幅の条件（w < below）は問わない（高さが below_h 未満なら、幅の広い矩形でもこの段を使う。短くて広いブロック用）。
    無ければ None（= 広い構図）。height が None のときは高さの条件つきの段を選ばない"""
    if not _pos(width):
        return None
    for lv in narrow_levels(pat):
        bh = _below_h(lv)
        if width < _below(lv) or (bh and lv.get("no_max_width") is True):
            if bh is None or (_pos(height) and height < bh):
                return lv
    return None


def min_width_of(pat):
    """型の幅の下限（設計寸法を実際の矩形に写したあとの幅 px）。無ければ None"""
    mw = pat.get("min_width") if isinstance(pat, dict) else None
    return mw if _pos(mw) else None


def base_levels(pat):
    """高さの条件のない段（幅だけで選ばれる段）。下限・個数別の下限・一覧の表示は、この段の値を使う"""
    return [x for x in narrow_levels(pat) if not _below_h(x)]


def narrow_floor(pat):
    """狭い構図まで含めた、型が読める最小の幅（px）。最も狭い段の min_width、無ければ型の min_width、どちらも無ければ None"""
    lv = base_levels(pat)
    if lv and min_width_of(lv[0]):
        return min_width_of(lv[0])
    return None if lv else min_width_of(pat)


def count_floors(pat):
    """個数ごとの幅の下限 {個数(int): px}。最も狭い段の min_width_by_count のうち、正の数のものだけ（形の違う値は読み飛ばす）"""
    lv = base_levels(pat)
    by = lv[0].get("min_width_by_count") if lv else None
    out = {}
    if isinstance(by, dict):
        for k, v in by.items():
            if str(k).isdigit() and _pos(v):
                out[int(k)] = v
    return out


def _apply_level(pattern, nr):
    """型 pattern に狭い構図 nr（narrow の 1 段）を当てた型（"_narrow": True）。スロットの定義は共通"""
    out = {k: v for k, v in pattern.items() if k not in ("narrow", "variants", "variants_by", "min_width")}
    out["_narrow"] = True
    for k in ("size", "elements", "valign", "min_width", "min_width_by_count"):
        if k in nr:
            out[k] = nr[k]
    if isinstance(nr.get("variants"), dict):
        out["variants"] = nr["variants"]
        out["variants_by"] = nr.get("variants_by", pattern.get("variants_by"))
    # 高さの条件つき段（短い構図）が、下限（min_width / 個数別の下限）を持たないときは、同じ幅の幅だけの段から引き継ぐ
    if _pos(nr.get("max_stretch")):
        out["_max_stretch"] = nr["max_stretch"]
    if _below_h(nr):
        out["_short"] = True
        for k in ("min_width", "min_width_by_count"):
            if k not in nr:
                for b in base_levels(pattern):
                    if _below(b) == _below(nr) and k in b:
                        out[k] = b[k]
                        break
    return out


def effective_pattern(pattern, width, height=None):
    """置く矩形の幅 width（px）・高さ height（px。省略可）に合う構図の型を返す。型に narrow があり、width が narrow.below 未満なら、
    size / elements / variants を narrow（複数あれば width が below 未満になる最小の段。below_h のある段は height が below_h 未満のときだけ）のものに差し替えた型
    （"_narrow": True）、そうでなければ元の型そのもの。スロットの定義は共通（同じ slots を狭い構図でも使う）"""
    nr = narrow_for(pattern, width, height) if frame_of(pattern) == "body" else None
    return pattern if nr is None else _apply_level(pattern, nr)


# ---------------------------------------------------------------- 探索と読み込み
def pattern_dirs(deck_dir=None):
    """パターンの探索ディレクトリを優先順に返す（deck_paths.search_dirs("patterns", deck_dir)。先に見つかったものが勝つ）。
    1. 環境変数 SLIDE_DECK_PATTERNS（複数可・OS 区切り）
    2. <deck_dir>/patterns/
    3. <deck_dir> の親 3 階層分の patterns/（プロジェクト共通の置き場）
    4. カレントの patterns/
    5. 同梱の templates/patterns/"""
    return deck_paths.search_dirs("patterns", deck_dir)


def _read_pattern_file(path: Path) -> dict:
    try:
        pat = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PatternError(f"{path} の JSON が不正です: {e}（{e.lineno} 行目付近）")
    except OSError as e:
        raise PatternError(f"{path} を読み込めません: {e}")
    if not isinstance(pat, dict):
        raise PatternError(f"{path} の形式が不正です（トップレベルはオブジェクトである必要があります）")
    pat["_path"] = str(path)
    return pat


def load_pattern(name, deck_dir=None):
    """名前からパターン JSON を探して読む。無ければ None。ファイルが壊れていれば PatternError"""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        return None
    for d in pattern_dirs(deck_dir):
        f = d / f"{name}.json"
        if f.is_file():
            _shadow = deck_paths.shadow_note("patterns", name, f)
            if _shadow:
                print(f"note: {_shadow}", file=sys.stderr)
            return _read_pattern_file(f)
    return None


def list_patterns(deck_dir=None):
    """見つかった全パターン [(name, path, pattern or None, error or None)]。同名は先勝ち"""
    seen, out = set(), []
    for d in pattern_dirs(deck_dir):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            if f.stem in seen:
                continue
            seen.add(f.stem)
            try:
                out.append((f.stem, f, _read_pattern_file(f), None))
            except PatternError as e:
                out.append((f.stem, f, None, str(e)))
    return out


def available_names(deck_dir=None):
    return [n for n, _, _, _ in list_patterns(deck_dir)]


# ---------------------------------------------------------------- トークン・テーマ
def _tokens(theme):
    out = copy.deepcopy(DEFAULT_TOKENS)
    t = (theme or {}).get("tokens")
    if isinstance(t, dict):
        for grp, v in t.items():
            if isinstance(v, dict):
                out.setdefault(grp, {}).update(v)
    return out


def _hex(v):
    if isinstance(v, str):
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            return v.upper()
        if re.fullmatch(r"#[0-9A-Fa-f]{3}", v):
            return "#" + "".join(c * 2 for c in v[1:]).upper()
    return None


class _St:
    """展開中の状態（テーマ・トークン・警告の出し先）"""

    def __init__(self, theme, warn=None, errors=None, pname="", slots=None, quiet_squeeze=()):
        self.slots = slots if isinstance(slots, dict) else {}
        self.quiet_squeeze = set(quiet_squeeze or ())   # validate が「個数が max を超えている」警告を出したスロット（潰れ警告を重ねない）
        self.cur_repeat = None                          # 展開中の要素の繰り返しのスロット名
        self.squeeze = {}                               # 繰り返し名 → 大きさが負になった要素の数
        self.cur_item = None                            # 展開中の繰り返しの項目の番号（0 始まり）
        self.in_group = 0                               # group 要素の子を展開中か（子はあとで座標変換で複製されるので、グループ fit の対象外）
        self.groups = {}                                # fit.group の名前 → 所属する要素の記録（展開の最後にサイズをそろえる）
        self.theme = theme or {}
        self.colors = self.theme.get("colors", {}) or {}
        self.tokens = _tokens(self.theme)
        fonts = self.theme.get("fonts", {}) or {}
        body = ja_text._names(fonts.get("body")) or ["Meiryo UI"]
        self.fonts = {"body": body,
                      "heading": ja_text._names(fonts.get("heading")) or body,
                      "code": ja_text._names(fonts.get("code")) or ["Consolas"]}
        self._warn, self._errors, self.pname = warn, errors, pname
        self.dedupe = set()

    def warn(self, msg):          # 内容に由来する注意（文字あふれ等）
        if self._warn and msg not in self.dedupe:
            self.dedupe.add(msg)
            self._warn(msg)

    def error(self, msg):         # パターン作者の誤り（未知の色・トークン・変数）。errors があればそちらへ、無ければ warn
        if self.dedupe is not None and msg in self.dedupe:
            return
        self.dedupe.add(msg)
        if self._errors is not None:
            self._errors.append(msg)
        elif self._warn:
            self._warn(msg)

    def color(self, v, where=""):
        h = _hex(v)
        if h:
            return h
        if isinstance(v, str):
            tv = self.colors.get(v)
            h = _hex(tv)
            if h:
                return h
        near = difflib.get_close_matches(v, list(self.colors), n=2, cutoff=0.6) if isinstance(v, str) else []
        hint = f"もしかして: {', '.join(near)}" if near else f"使えるトークン: {', '.join(sorted(self.colors)[:8])} …"
        self.error(f"色 '{v}' はテーマの色トークンにも #RRGGBB にもありません{where} → {hint}")
        return "#000000"

    def number(self, v, where=""):
        """'$type.h1' のようなトークン参照を数値にする。数値はそのまま"""
        if isinstance(v, str) and v.startswith("$"):
            cur = self.tokens
            for part in v[1:].split("."):
                cur = cur.get(part) if isinstance(cur, dict) else None
            if isinstance(cur, (int, float)) and not isinstance(cur, bool):
                return cur
            allt = [f"${g}.{k}" for g, d in self.tokens.items() for k in d]
            near = difflib.get_close_matches(v, allt, n=2, cutoff=0.6)
            self.error(f"トークン '{v}' が見つかりません{where} → "
                       + (f"もしかして: {', '.join(near)}" if near else "使えるトークン: " + ", ".join(allt)))
            return 0
        return v


# ---------------------------------------------------------------- 差し込み
def _lookup(scope, key):
    key = key.strip()
    if key == ".":
        return scope.get(".", _MISSING)
    cur = scope
    for k, part in enumerate(key.split(".")):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and part != "0":
            cur = cur[int(part) - 1] if int(part) <= len(cur) else ""      # {{values.2}} = 2 番目（1 始まり）。足りない分は空
        else:
            return _MISSING
    return cur


def _float_text(v):
    """float を文字列にする。有効桁を落とさず（repr ベース）、指数表記にもしない（1234567.0 → '1234567'、1234.5678 → '1234.5678'）"""
    if not math.isfinite(v):
        return ""
    if v == int(v) and abs(v) < 1e21:
        return str(int(v))
    return format(Decimal(repr(v)), "f")


def _to_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else ""
    if isinstance(v, float):
        return _float_text(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return ce.clean_text(v)   # XML に使えない文字（\x0c 等）は落とす（PPTX 生成が止まらないように）
    if isinstance(v, list):
        return "\n".join(_to_text(x) for x in v)
    return ""


def _missing_var_message(key, where=""):
    """{{x}} に対応するスロットが無いときの文言。添字 0（{{values.0}}）は専用の案内にする（添字は 1 から）"""
    key = key.strip()
    parts = key.split(".")
    if "0" in parts[1:]:
        fixed = ".".join("1" if q == "0" else q for q in parts)
        return (f"差し込み {{{{{key}}}}} の添字 0 は使えません{where} → 添字は 1 から数えます（1 番目は {{{{{fixed}}}}}、2 番目は "
                f"{{{{{'.'.join('2' if q == '0' else q for q in parts)}}}}}）")
    return f"差し込み {{{{{key}}}}} に対応するスロットがありません{where} → slots に定義するか、書き間違いを直してください"


def _interp(s, scope, st, where="", stat=None):
    """文字列中の {{slot}} を値に置き換える（値の中の {{ は再展開しない）。
    stat=[差し込みの数, 空でなかった数] を渡すと数える（差し込みがすべて空の段落を出さないため）"""
    def rep(m):
        v = _lookup(scope, m.group(1))
        if v is _MISSING:
            st.error(_missing_var_message(m.group(1), where))
            out = ""
        elif isinstance(v, bool):
            out = ""                       # 真偽（flag）は文字として出さない（"true" という札にしない）
        else:
            out = _to_text(v)
        if stat is not None:
            stat[0] += 1
            stat[1] += 1 if out.strip() else 0
        return out
    return _VAR_RE.sub(rep, s)


def _truthy(v):
    if v is _MISSING or v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


_FALSE_WORDS = {"", "false", "no", "off", "0", "n", "none", "null", "nil", "x", "×", "✗", "✕", "✖", "❌", "-", "–", "—", "―", "ー", "−",
                "なし", "無し", "無", "否", "ない", "無い", "いいえ", "偽", "不要", "対象外"}


def _norm_key(v) -> str:
    """値の比較用: 全角・半角をそろえ、前後の空白を除き、大文字小文字を区別しない"""
    return unicodedata.normalize("NFKC", v if isinstance(v, str) else _to_text(v)).strip().casefold()


def _as_flag(v) -> bool:
    """真偽スロットの値 → bool。false / "false" / "no" / "0" / 0 / "×" / "なし" / 空は偽、それ以外（true・"○"・"現在地" など何か書いてある）は真"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if v is None or v is _MISSING:
        return False
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return _norm_key(v) not in _FALSE_WORDS


def _canon(values, raw):
    """values（正規の値 → 別名の配列）に照らして、raw を正規の値にそろえる。候補に無ければ None"""
    key = _norm_key(raw)
    for canon, aliases in values.items():
        names = [canon] + (list(aliases) if isinstance(aliases, (list, tuple)) else [aliases])
        if any(_norm_key(a) == key for a in names if isinstance(a, (str, int, float, bool)) or a is None):
            return canon
    return None


def _canon_value(d, raw):
    """スロット・項目 d の "values" に照らして raw を正規の値にそろえる。候補に無ければ、d の "unknown_as"（宣言があれば）、それも無ければ None"""
    vals = d.get("values")
    c = _canon(vals, raw)
    if c is None:
        ua = d.get("unknown_as")
        if isinstance(ua, str) and ua in vals:
            return ua
    return c


def _same(v, target) -> bool:
    """is / in の比較。真偽の値は真偽どうし、それ以外は文字列（全角半角・大文字小文字・前後の空白を無視）で比べる"""
    if isinstance(target, bool):
        return _as_flag(v) == target
    if isinstance(v, bool):
        return v == _as_flag(target)
    return _norm_key(v if v is not _MISSING else "") == _norm_key(target)


def _cond(spec, scope, st=None):
    """"if" の評価。
    "slot" / "!slot"（空でなければ真 / 空のとき真）/ "@first" / "@last" / "@odd" / "@even"（繰り返し内）、配列は全部が真のとき真。
    辞書: {"slot": "state", "is": "done"}（等しい）/ {"slot": "state", "in": ["done", "wip"]}（いずれか）/ {"not": 条件}（否定）。
    繰り返しの中では、スロット名は今の 1 件のフィールドを指す"""
    if spec is None:
        return True
    if isinstance(spec, list):
        return all(_cond(s, scope, st) for s in spec)
    if isinstance(spec, dict):
        if "not" in spec:
            return not _cond(spec["not"], scope, st)
        if "any" in spec or "field" in spec:
            # 集計: {"slot": "stages", "field": "body", "any": false} = records スロット stages の全項目で body が空のとき真
            #       （"any": true は 1 項目でも body があるとき真）。繰り返しの外（top の elements / variants）で使う
            root = scope.get(str(spec.get("slot", "")).strip().split(".")[0])
            rows = [r for r in root if isinstance(r, dict)] if isinstance(root, list) else []
            f = str(spec.get("field", ""))
            present = any(_truthy(r.get(f)) for r in rows)
            return present == bool(spec.get("any", True))
        v = _lookup(scope, str(spec.get("slot", "")))
        if "is" in spec:
            return _same(v, spec["is"])
        if "in" in spec:
            return any(_same(v, t) for t in (spec["in"] if isinstance(spec["in"], list) else [spec["in"]]))
        return _truthy(v)
    spec = str(spec).strip()
    neg = spec.startswith("!")
    name = spec[1:].strip() if neg else spec
    if name.startswith("@"):
        lp = scope.get("_loop")
        if not lp:
            val = False
        else:
            i, n = lp
            val = {"@first": i == 0, "@last": i == n - 1, "@odd": i % 2 == 0, "@even": i % 2 == 1}.get(name, False)
            # @odd は「1 番目・3 番目…」（0 起点で偶数）の意味
    else:
        val = _truthy(_lookup(scope, name))
    return (not val) if neg else val


def _child_scope(scope, item, i, n, name=None):
    sc = dict(scope)
    if name:
        sc[name] = item      # 繰り返しの中では {{cards.head}} のように「今の 1 件」を指す
    sc["."] = item
    sc["index"] = str(i + 1)
    sc["count"] = str(n)
    sc["_loop"] = (i, n)
    if isinstance(item, dict):
        sc.update(item)
    return sc


def _items(scope, name):
    v = _lookup(scope, name)
    if v is _MISSING or v is None:
        return []
    return v if isinstance(v, list) else [v]


# ---------------------------------------------------------------- 文字・段落の展開
def _split_br(runs):
    """run の text に含まれる改行を br run に分ける（PPTX の a:t に生の改行を入れないため）"""
    out = []
    for r in runs:
        t = r.get("text")
        if isinstance(t, str) and "\n" in t and not r.get("br"):
            parts = t.split("\n")
            for k, part in enumerate(parts):
                if k:
                    out.append({"br": True, **({"size": r["size"]} if "size" in r else {})})
                if part:
                    out.append({**r, "text": part})
        else:
            out.append(r)
    return out


def _expand_run(r, scope, st, where, stat):
    r = {k: v for k, v in r.items() if k != "if"}
    if isinstance(r.get("text"), str):
        r["text"] = _interp(r["text"], scope, st, where, stat)
        r.setdefault("font", ["@body"])      # font を省略した文字はテーマの本文フォント（canvas 既定の Meiryo UI にしない）
    return r


def _expand_paragraph(p, scope, st, where):
    """1 段落を展開する。差し込みがあり、そのすべてが空になった段落は None（出さない。"keep": true で残せる）"""
    keep = p.get("keep")
    p = {k: v for k, v in p.items() if k not in ("if", "repeat", "keep")}
    runs, stat = [], [0, 0]
    for r in p.get("runs", []) or []:
        if not isinstance(r, dict) or not _cond(r.get("if"), scope, st):
            continue
        r2 = _expand_run(r, scope, st, where, stat)
        if r2.get("br") or r2.get("text") or "text" not in r2:
            runs.append(r2)
    p["runs"] = _split_br(runs)
    if stat[0] and not stat[1] and not p.get("size") and not keep:
        return None
    return p


def _expand_paragraphs(paras, scope, st, where):
    out = []
    for p in paras or []:
        if not isinstance(p, dict) or not _cond(p.get("if"), scope, st):
            continue
        if "repeat" in p:
            items = _items(scope, p["repeat"])
            for i, item in enumerate(items):
                q = _expand_paragraph(p, _child_scope(scope, item, i, len(items), p["repeat"]), st, where)
                if q is not None:
                    out.append(q)
        else:
            q = _expand_paragraph(p, scope, st, where)
            if q is not None:
                out.append(q)
    return out


# ---------------------------------------------------------------- トークンの解決（色・サイズ・フォント）
def _resolve(obj, key, st, where=""):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _COLOR_KEYS and isinstance(v, str):
                out[k] = st.color(v, where)
            elif k in _TEXT_KEYS and isinstance(v, str):
                out[k] = v
            elif k == "font":
                names = []
                for f in (v if isinstance(v, list) else [v]):
                    if isinstance(f, str) and f.startswith("@"):
                        names += st.fonts.get(f[1:]) or st.error(f"フォント '{f}' は @heading / @body / @code のいずれかです{where}") or []
                    elif isinstance(f, str):
                        names.append(f)
                out[k] = names
            elif k == "size" and v == "@fit":
                out[k] = v
            else:
                out[k] = _resolve(v, k, st, where)
        return out
    if isinstance(obj, list):
        if key == "stops":
            return [[s[0], st.color(s[1], where)] if isinstance(s, (list, tuple)) and len(s) == 2 and isinstance(s[1], str) else s
                    for s in obj]
        if key == "colors":
            return [st.color(c, where) if isinstance(c, str) else c for c in obj]
        return [_resolve(x, key, st, where) for x in obj]
    if isinstance(obj, str) and obj.startswith("$"):
        return st.number(obj, where)
    return obj


# ---------------------------------------------------------------- 文字枠の自動フィット
def _para_size(p):
    sizes = [r.get("size") for r in p.get("runs", []) if isinstance(r.get("size"), (int, float))]
    return max(sizes) if sizes else (p.get("size") or 24)


def _para_lh_px(p, size):
    if p.get("lineHeightPx"):
        return p["lineHeightPx"]
    return size * ce.LINE_HEIGHT * p.get("lineHeight", DEFAULT_LH)


def _text_height(tx, avail_w, st):
    total = 0.0
    for p in tx.get("paragraphs", []):
        size = _para_size(p)
        n = 0
        segs = [[]]
        for r in p.get("runs", []):
            if r.get("br"):
                segs.append([])
            else:
                segs[-1].append(r)
        for seg in segs:
            text = "".join(r.get("text", "") for r in seg)
            sz = max([r.get("size", size) for r in seg if isinstance(r.get("size", size), (int, float))] or [size])
            bold = any(r.get("bold") for r in seg)
            font = (seg[0].get("font") if seg else None) or st.fonts["body"]
            w = max(avail_w - p.get("marL", 0), 10)
            n += ja_text.estimate_lines(text, sz, w, font=font, bold=bold) if text else 1
        total += n * _para_lh_px(p, size) + p.get("spaceBefore", 0) + p.get("spaceAfter", 0)
    return total


def _can_break(text, i, level=1):
    """文節の切れ目として使ってよいか。規則の本体は ja_text.can_break（既存タイプの見出し・本文の折り返しと同じ規則を使う）。
    level 1（既定）がいちばん厳しく、2・3 の順にゆるむ（意味は ja_text.can_break の説明を参照）"""
    return ja_text.can_break(text, i, level)


PHRASE_SLACK_PX = 1.0         # 1 行に収まる文でも、枠の幅からこれだけ（または幅の PHRASE_SLACK_RATIO 倍の大きいほう）余らないときは、1 行と決めない
PHRASE_SLACK_RATIO = 0.004


def _phrase_lines(text, size, width, font, bold):
    """和文を、文節の切れ目（ja_text.good_break）で折り返した行のリスト。語の途中（「窓/口」「測/り」）で切れる文字単位の折り返しを避ける。
    和文を含まない・すでに改行がある・1 行に収まる文は [text] を返す。文節が 1 行に収まらないときだけ文字単位で切る"""
    if not text or "\n" in text or len(text) > 400 or not ja_text._has_cjk(text) or width < size * 2:
        return [text]
    if len(ja_text.wrap_lines(text, size, width, font, bold)) < 2 and ja_text._width(text, size, font, bold) <= width - max(PHRASE_SLACK_PX, width * PHRASE_SLACK_RATIO):
        return [text]               # 枠の幅にちょうど収まる文（幅の 100%）は 1 行と決めない: 描画側が 1 文字だけ折り返すことがある（「必／要」）
    usable = width * 0.97          # 実際の描画との差を見込んで少し狭く見積もる

    def w(a, b):
        return ja_text._width(text[a:b], size, font, bold)
    n = len(text)
    # 文節の切れ目だけで、行末の余りの二乗和が最小になる分割（ばらつきを抑える）。最終行は余りを軽く見て、短すぎる行（3 文字未満）は避ける。
    # 切れ目の規則は level 1（厳しい）→ 2 → 3 の順にゆるめる: 規則が厳しすぎて収まらない・最終行が 1〜2 文字になるときだけ、次の level を試す
    pre = [0.0]
    for ch in text:
        pre.append(pre[-1] + ja_text.char_em(ch, font, bold) * size)
    INF = float("inf")
    first_ok = None
    for level in (1, 2, 3):
        cuts = [0] + [i for i in range(1, n) if _can_break(text, i, level)] + [n]
        best_cost, back = {0: 0.0}, {}
        for bi in range(1, len(cuts)):
            b = cuts[bi]
            cand = INF
            for ai in range(bi - 1, -1, -1):
                a = cuts[ai]
                wd = pre[b] - pre[a]
                if wd > usable:
                    break
                if a not in best_cost:
                    continue
                slack = usable - wd
                cost = best_cost[a] + usable * usable * 0.3 + slack * slack * (0.15 if b == n else 1.0)   # 行数を増やさない（1 行ごとの固定費）
                if b == n and len(text[a:b].strip()) < 3:
                    cost += 1e7
                if cost < cand:
                    cand, back[b] = cost, a
            if cand < INF:
                best_cost[b] = cand
        if n in best_cost:
            lines, b = [], n
            while b > 0:
                a = back[b]
                lines.append(text[a:b].strip(" "))
                b = a
            lines = [ln for ln in reversed(lines) if ln]
            if lines:
                if len(lines) < 2 or len(lines[-1]) >= 3:
                    return lines
                if first_ok is None:
                    first_ok = lines             # 最終行が 1〜2 文字: 規則をゆるめた分割で直せるか試す
    if first_ok:
        return first_ok
    lines, start = [], 0
    while start < n:
        if w(start, n) <= usable:
            lines.append(text[start:].strip(" "))
            break
        best, acc = None, 0.0
        for i in range(start + 1, n):
            acc += ja_text.char_em(text[i - 1], font, bold) * size
            if acc > usable:
                break
            if _can_break(text, i, 2):
                best = i
        if best is None:           # 文節が長くて収まらない: 文字単位の自然な折り返しに任せる
            first = ja_text.wrap_lines(text[start:], size, width, font, bold)[0]
            best = start + max(1, len(first))
        lines.append(text[start:best].strip(" "))
        start = best
        while start < n and text[start] == " ":
            start += 1
    # 最終行が 1〜2 文字だけにならないよう、最後の 2 行を釣り合う位置で切り直す
    if len(lines) >= 2 and len(lines[-1].strip()) < 3:
        joined = lines[-2] + lines[-1]
        cand = None
        for i in range(2, len(joined) - 2):
            if not _can_break(joined, i):
                continue
            hw = ja_text._width(joined[:i], size, font, bold)
            tw = ja_text._width(joined[i:], size, font, bold)
            if hw <= usable and tw <= usable and len(joined[i:].strip()) >= 3 and (cand is None or abs(hw - tw) < cand[0]):
                cand = (abs(hw - tw), i)
        if cand:
            lines[-2:] = [joined[:cand[1]].strip(" "), joined[cand[1]:].strip(" ")]
    return [ln for ln in lines if ln] or [text]


def _split_runs_by_lines(runs, lines):
    """連結した本文を lines（その行の文字列。前後の空白は除いてある）に分けたとき、各行の run の並び（書式は元の run のまま）を返す"""
    joined = "".join(r["text"] for r in runs)
    bounds, pos = [], 0
    for r in runs:
        bounds.append((pos, pos + len(r["text"])))
        pos += len(r["text"])
    out, at = [], 0
    for ln in lines:
        s0 = joined.find(ln, at)
        if s0 < 0:
            return None
        e0 = s0 + len(ln)
        at = e0
        seg = []
        for r, (a, b) in zip(runs, bounds):
            lo, hi = max(a, s0), min(b, e0)
            if lo < hi:
                seg.append(dict(r, text=joined[lo:hi]))
        out.append(seg)
    return out


def _wrap_paragraphs(paras, line_len, st):
    """単一書式の段落（改行なし）の和文を、文節の切れ目で改行する（\n の代わりに br run を入れる）。
    run が複数でも、文字サイズ・フォント・太さが同じなら（引用符と本文を別の色にした段落など）1 つの文として折り、行ごとに run を分け直す。
    入れた改行は "soft": true の印を付ける（最終行が短くなったときの警告に使う。HTML と PPTX の見た目は通常の改行と同じ）。
    HTML と PPTX は折り返し位置を別々に決めるため、展開時に改行を入れておくと両方で同じ位置になる"""
    out = []
    for p in paras:
        runs = p.get("runs", [])
        texts = [r for r in runs if not r.get("br")]
        if not texts or len(texts) != len(runs) or any(not isinstance(r.get("text"), str) or "\n" in r["text"] for r in texts):
            out.append(p)
            continue
        r = texts[0]
        size = r.get("size") if isinstance(r.get("size"), (int, float)) else _para_size(p)
        if len(texts) > 1 and any(x.get("size") != r.get("size") or x.get("font") != r.get("font") or bool(x.get("bold")) != bool(r.get("bold")) for x in texts[1:]):
            out.append(p)               # 書式の違う run が混ざる段落は、折る位置を決められないのでそのまま
            continue
        joined = "".join(x["text"] for x in texts)
        lines = _phrase_lines(joined, size, max(line_len - p.get("marL", 0), 10), r.get("font") or st.fonts["body"], bool(r.get("bold")))
        if len(lines) < 2:
            out.append(p)
            continue
        segs = [[dict(r, text=ln)] for ln in lines] if len(texts) == 1 else _split_runs_by_lines(texts, lines)
        if segs is None:
            out.append(p)
            continue
        new_runs = []
        for k, seg in enumerate(segs):
            if k:
                new_runs.append({"br": True, "size": size, "soft": True})
            new_runs.extend(seg)
        out.append(dict(p, runs=new_runs))
    return out


def _fit_sizes(fit, st=None, where=""):
    """fit.sizes → 大きい順の正の数（"$type.h3" のトークンも数にする）"""
    raw = fit.get("sizes") if isinstance(fit, dict) else None
    if not isinstance(raw, list):
        return []
    out = []
    for v in raw:
        if isinstance(v, str) and v.startswith("$") and st is not None:
            v = st.number(v, where)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            out.append(v)
    return sorted(set(out), reverse=True)


ORPHAN_MIN_SHRINK = 0.75    # 最終行が 1〜2 文字になるのを避けるために文字サイズを下げてよい下限（収まる最大サイズに対する比）


def _has_orphan(paras):
    """エンジンが入れた改行（soft の br）で、最終行が 1〜2 文字だけの段落があるか（_warn_short_last_lines と同じ条件）"""
    for p in paras:
        runs = p.get("runs", []) if isinstance(p, dict) else []
        if not any(r.get("soft") for r in runs):
            continue
        lines, cur = [], ""
        for r in runs:
            if r.get("br"):
                lines.append(cur)
                cur = ""
            else:
                cur += r.get("text", "") if isinstance(r.get("text"), str) else ""
        lines.append(cur)
        last, prev = lines[-1].strip(), lines[-2].strip() if len(lines) > 1 else ""
        if 1 <= _chars(last) <= 2 and _chars(prev) >= 4:
            return True
    return False


def _fit_text(el, fit, st, label, quiet=False, balance=True, cap=None, report=None):
    """fit: {"sizes": [28, 24, 20, 16]}。収まる最大のサイズを選ぶ。
    size が "@fit" の run があればその run だけがそのサイズになる。無ければ、全 run を sizes[0] からの比率で拡縮する。
    wrap:false の文字枠は折り返さない（幅の制約を外し、高さだけで判定する）。縦書き（vert）は行の長さが枠の高さ、行が積み重なる向きが幅になる。
    quiet=True（枠が負の大きさに潰れた要素）のときは「収まらない」警告を出さない（潰れた原因は繰り返し側で警告する）。
    cap: これ以下のサイズだけを候補にする（グループ fit が、グループの最小サイズを当てるとき）。
    report: dict を渡すと、警告を出さずに結果を入れる（グループ fit が、まとめて 1 回警告するため）"""
    tx = el.get("text")
    sizes = _fit_sizes(fit, st, label)
    if not tx or not sizes:
        return
    base = sizes[0]
    if cap is not None:
        sizes = [x for x in sizes if x <= cap + 1e-9] or [sizes[-1]]
    insets = tx.get("insets", [9.6, 4.8, 9.6, 4.8])
    l, t, r, b = ce.text_rect(el)
    avail_w = (r - l) - insets[0] - insets[2]
    avail_h = (b - t) - insets[1] - insets[3]
    line_len, across = (avail_h, avail_w) if tx.get("vert") else (avail_w, avail_h)
    if tx.get("wrap") is False:
        line_len = 1e6
    marker = any(r_.get("size") == "@fit" for p in tx["paragraphs"] for r_ in p.get("runs", []))

    def apply(sz):
        paras = copy.deepcopy(tx["paragraphs"])
        if marker:
            for p in paras:
                for r_ in p.get("runs", []):
                    if r_.get("size") == "@fit":
                        r_["size"] = sz
                if p.get("size") == "@fit":
                    p["size"] = sz
            return paras
        return ce._scale_paragraphs(paras, sz / base)
    can_wrap = balance and tx.get("wrap") is not False and not tx.get("vert")

    def paras_at(sz):
        ps = apply(sz)
        return _wrap_paragraphs(ps, line_len, st) if can_wrap else ps
    chosen = None
    first_fit = None
    for sz in sizes:
        cand = dict(tx, paragraphs=paras_at(sz))
        if _text_height(cand, line_len, st) <= across + 0.5:
            if first_fit is None:
                first_fit = sz
            if not _has_orphan(cand["paragraphs"]) or not can_wrap:
                chosen = sz
                break
            if sz < first_fit * ORPHAN_MIN_SHRINK - 1e-9:
                break
    if chosen is None and first_fit is not None:
        chosen = first_fit       # 最終行が 1〜2 文字になる大きさしか無い（少し小さくしても直らない）: 大きいほうを使う（警告は _warn_short_last_lines が出す）
    elif chosen is not None and first_fit is not None and chosen < first_fit and chosen < first_fit * ORPHAN_MIN_SHRINK - 1e-9:
        chosen = first_fit
    fits = chosen is not None
    need = 0.0
    if chosen is None:
        chosen = sizes[-1]
        cand = dict(tx, paragraphs=paras_at(chosen))
        need = _text_height(cand, line_len, st)
        if report is None and not quiet:
            st.warn(f"{label}の文字が最小サイズ {chosen:g}px でも枠に収まりません（必要な高さ約 {need:.0f}px / 枠 {max(across, 0):.0f}px）"
                    f" → 文字数を減らすか、パターンの枠を広げてください")
    el["text"] = dict(tx, paragraphs=paras_at(chosen))
    el["_fit_size"] = chosen
    if report is not None:
        report.update(chosen=chosen, fits=fits, need=need, across=max(across, 0), quiet=quiet)


def _group_name(fit, loc):
    """fit.group → グループ名。文字列はそのまま、true は「同じテンプレート位置の要素どうし」（loc が同じもの）、無し・false は None"""
    g = fit.get("group") if isinstance(fit, dict) else None
    if isinstance(g, str) and g.strip():
        return g.strip()
    if g is True:
        return f"@{loc}"
    return None


def _apply_groups(st):
    """fit.group を持つ要素のサイズをそろえる: 各要素が単独で収まる最大サイズのうち最小を、グループ全員が使う。
    最小サイズでも収まらない要素があれば、グループごとに 1 回、いちばん溢れる項目を名指しして警告する"""
    for gname, members in st.groups.items():
        g = min(m["report"]["chosen"] for m in members)
        for m in members:
            if m["report"]["chosen"] > g + 1e-9:
                el = m["el"]
                el["text"] = copy.deepcopy(m["text"])
                _fit_text(el, m["fit"], st, "", quiet=True, balance=m["balance"], cap=g, report={})
                el.pop("_fit_size", None)
                _finalize_text(el)
        bad = [m for m in members if not m["report"]["fits"] and not m["report"]["quiet"]]
        if bad:
            w = max(bad, key=lambda m: m["report"]["need"] - m["report"]["across"])
            rp = w["report"]
            who = w["who"]
            st.warn(f"パターン '{st.pname}' の{who}の文字が最小サイズ {rp['chosen']:g}px でも枠に収まりません"
                    f"（必要な高さ約 {rp['need']:.0f}px / 枠 {rp['across']:.0f}px"
                    + (f"。同じグループ {len(members)} 個のうち {len(bad)} 個が収まりません" if len(bad) > 1 else "")
                    + "） → 文字数を減らすか、パターンの枠を広げてください")


# ---------------------------------------------------------------- 要素の展開
SHADOW_COLOR = "#0F172A"        # build_deck.SHADOW_COLOR と同じ（箱の影の色）


def _shadow_from_token(spec, st, where=""):
    """要素の "shadow": "$shadow.card"（形トークン。"none" / "soft"）→ canvas の shadow {dx, dy, blur, color}。none は None。
    shape: soft で影が付き、classic では付かない（cards などの組み込みタイプの箱と同じ規則）。"soft" と直接書いてもよい"""
    mode = spec
    if isinstance(spec, str) and spec.startswith("$"):
        cur = st.tokens
        for part in spec[1:].split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        mode = cur
        if not isinstance(mode, str):
            st.error(f"影のトークン '{spec}' が見つかりません{where} → $shadow.card を使ってください")
            return None
    if mode == "none":
        return None
    p = shp.shadow_params(st.tokens, mode)
    if not p:
        st.error(f"影 '{spec}' は \"$shadow.card\"（またはモード none / soft）で指定してください{where}")
        return None
    return {"dx": p["dx"], "dy": p["dy"], "blur": p["blur"], "color": {"color": SHADOW_COLOR, "alpha": p["alpha"]}}


def _expand_element(n, scope, st, cell=None, loc=""):
    """パターン要素 1 つ → hex 解決済みの canvas 要素。cell=(x, y, w, h) のときは x/y/w/h/r/b をセル内の相対配置として扱う。
    loc は要素の位置（elements[2].template[1] など。名前の無い要素を特定するため）"""
    where = f"（要素 '{loc}'）" if loc else f"（要素 '{n.get('kind', 'shape')}'）"
    # fit は文字枠の自動フィット（dict）。画像の fit（"cover" / "contain"）は要素の値としてそのまま残す
    el = {k: v for k, v in n.items() if k not in _META_KEYS and not (k == "fit" and isinstance(v, str))}
    fit, radius = (n.get("fit") if isinstance(n.get("fit"), dict) else None), n.get("radius")
    if isinstance(n.get("role"), str):
        el["_role"] = n["role"]       # 見出し骨格の部品の印（title / rule / eyebrow）。形トークンを当てたあとで消す
    # 文字列の差し込み
    for key in ("name", "alt", "label", "path"):
        if isinstance(el.get(key), str):
            el[key] = _interp(el[key], scope, st, where)
    if el.get("kind") == "image" and isinstance(n.get("path"), str):
        m_ = re.fullmatch(r"\{\{\s*([^{}\s]+)\s*\}\}", n["path"].strip())
        if m_ and isinstance(scope.get(f"{m_.group(1)}_alt"), str) and scope[f"{m_.group(1)}_alt"]:
            el["alt"] = scope[f"{m_.group(1)}_alt"]          # スライドごとの代替テキスト（slots の <スロット名>_alt）が型の固定値より優先
    if el.get("name"):   # 以降のメッセージは、差し込み済みの名前（柱1の説明 など）で示す
        where = f"（要素 '{el['name']}'）"
    if isinstance(el.get("text"), dict):
        tx = dict(el["text"])
        tx["paragraphs"] = _expand_paragraphs(tx.get("paragraphs", []), scope, st, where)
        el["text"] = tx
    if el.get("kind") == "table":
        rows = []
        for row in el.get("rows", []) or []:
            if isinstance(row, dict) and "repeat" in row:
                items = _items(scope, row["repeat"])
                for i, item in enumerate(items):
                    sc = _child_scope(scope, item, i, len(items), row["repeat"])
                    rows.append(_expand_row(row, sc, st, where))
            elif isinstance(row, dict):
                rows.append(_expand_row(row, scope, st, where))
        el["rows"] = rows
    if el.get("kind") == "group":
        st.in_group += 1
        el["children"] = _expand_nodes(el.get("children", []), scope, st, f"{loc or 'group'}.children")
        st.in_group -= 1
    # 幾何: セル内相対 or 絶対（w の代わりに r、h の代わりに b で右・下の余白を指定できる）
    bx, by, bw, bh = cell if cell else (0, 0, CANVAS_W, CANVAS_H)
    squeezed = False
    xr, yr = st.number(n.get("x", 0), where), st.number(n.get("y", 0), where)
    if el.get("kind") != "group":
        if "w" in n:
            w = st.number(n["w"], where)
        elif "r" in n:
            w = bw - xr - st.number(n["r"], where)
        elif cell:
            w = bw - xr
        else:
            w = None
        if "h" in n:
            h = st.number(n["h"], where)
        elif "b" in n:
            h = bh - yr - st.number(n["b"], where)
        elif cell:
            h = bh - yr
        else:
            h = None
        # 個数が多すぎてセルが小さくなると w / h が負になる。負の大きさは PPTX の XML として不正なので 0 に丸める
        squeezed = False
        if _num(w) and w < 0:
            squeezed, w = True, 0
        if _num(h) and h < 0:
            squeezed, h = True, 0
        if squeezed:
            if cell and st.cur_repeat:
                st.squeeze[st.cur_repeat] = st.squeeze.get(st.cur_repeat, 0) + 1
            else:
                st.error(f"要素の幅または高さが負になります{where} → x / y / r / b の指定を見直してください（0 にして描きます）")
        if w is not None:
            el["w"] = w
        if h is not None:
            el["h"] = h
        el["x"] = bx + xr if cell else xr
        el["y"] = by + yr if cell else yr
    el.pop("r", None)
    el.pop("b", None)
    shadow_spec = el.pop("shadow") if isinstance(el.get("shadow"), str) else None     # "$shadow.card" など形トークンの影（dict は canvas の影そのまま）
    el = _resolve(el, None, st, where)
    if shadow_spec is not None:
        sh = _shadow_from_token(shadow_spec, st, where)
        if sh:
            el["shadow"] = sh
    if el.get("kind") == "group" and cell:
        el["children"] = ce.transform_elements(el["children"], 1, 1, cell[0], cell[1])
        if isinstance(el.get("origin"), list) and len(el["origin"]) == 2:
            el["origin"] = [el["origin"][0] + cell[0], el["origin"][1] + cell[1]]
    if radius is not None and el.get("kind", "shape") == "shape" and _num(el.get("w")) and _num(el.get("h")):
        rpx = st.number(radius, where)
        if isinstance(rpx, (int, float)) and rpx > 0:
            el["geom"] = "roundRect"
            el["adj"] = dict(el.get("adj", {}), adj=int(min(50000, max(0, rpx / max(min(el["w"], el["h"]), 1) * 100000))))
    if radius is not None and el.get("kind") == "image":
        rpx = st.number(radius, where)           # 画像の角丸（cover のときだけ。contain は枠より小さく描かれるため角丸にしない）
        if isinstance(rpx, (int, float)) and rpx > 0:
            el["radius"] = rpx
    balance = n.get("balance") is not False      # "balance": false で、文節での改行（和文）を止められる
    if fit:
        fit = dict(fit, sizes=_fit_sizes(fit, st, where))          # "$type.h3" のトークンを数にする
        label_ = f"パターン '{st.pname}' の{where[1:-1]}" if where else ""
        gname = _group_name(fit, loc) if (el.get("text") and not squeezed and not st.in_group) else None
        if gname:
            pre, rep = copy.deepcopy(el["text"]), {}
            _fit_text(el, fit, st, label_, quiet=False, balance=balance, report=rep)
            if rep:
                if st.cur_repeat and st.cur_item is not None:
                    d_ = st.slots.get(st.cur_repeat) if isinstance(st.slots.get(st.cur_repeat), dict) else {}
                    who = f"「{d_.get('label') or st.cur_repeat}」（スロット '{st.cur_repeat}'）の {st.cur_item + 1} 個目{where[1:-1] and '（' + where[1:-1] + '）'}"
                else:
                    who = where[1:-1] if where else "要素"
                st.groups.setdefault(gname, []).append({"el": el, "text": pre, "fit": fit, "balance": balance, "report": rep, "who": who})
        else:
            _fit_text(el, fit, st, label_, quiet=squeezed, balance=balance)
    elif balance and isinstance(el.get("text"), dict) and not el["text"].get("vert") and el["text"].get("wrap") is not False \
            and _num(el.get("w")) and el["w"] > 0 and el.get("kind", "shape") == "shape":
        tx = el["text"]
        ins = tx.get("insets", [9.6, 4.8, 9.6, 4.8])
        l_, _t, r_, _b = ce.text_rect(el)
        el["text"] = dict(tx, paragraphs=_wrap_paragraphs(tx.get("paragraphs", []), (r_ - l_) - ins[0] - ins[2], st))
    el.pop("_fit_size", None)
    _finalize_text(el)
    for key in ("x", "y", "w", "h"):
        if _num(el.get(key)):
            el[key] = round(el[key], 2)
    return el


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _expand_row(row, scope, st, where):
    row = {k: v for k, v in row.items() if k != "repeat"}
    cells = []
    for c in row.get("cells", []) or []:
        if not isinstance(c, dict) or not _cond(c.get("if"), scope, st):
            continue
        c = {k: v for k, v in c.items() if k != "if"}
        c["paragraphs"] = _expand_paragraphs(c.get("paragraphs", []), scope, st, where)
        cells.append(c)
    row["cells"] = cells
    return row


def _finalize_text(el):
    """段落の行間を固定の行送り（lineHeightPx = 文字サイズ × 1.2 × lineHeight）にする。
    HTML の line-height と同じ値になり、PPTX では固定ポイント（spcPts）になるので、PowerPoint のフォント固有の行高に左右されない。
    @fit が残っていたら（fit が無いのに指定した誤り）24px にする"""
    def fix_paras(paras):
        for p in paras:
            for r in p.get("runs", []):
                if r.get("size") == "@fit":
                    r["size"] = 24
            if p.get("size") == "@fit":
                p["size"] = 24
            if "lineHeightPx" not in p:
                size = _para_size(p)
                p["lineHeightPx"] = round(size * ce.LINE_HEIGHT * p.pop("lineHeight", DEFAULT_LH), 2)
            else:
                p.pop("lineHeight", None)
            for r in p.get("runs", []):
                if isinstance(r.get("size"), float):
                    r["size"] = round(r["size"], 2)
    if isinstance(el.get("text"), dict):
        paras = el["text"].get("paragraphs", [])
        fix_paras(paras)
        if not paras:
            del el["text"]
    for row in el.get("rows", []) if el.get("kind") == "table" else []:
        for c in row.get("cells", []):
            fix_paras(c.get("paragraphs", []))


def _grid_layout(n, grid, st, where):
    """個数 n とグリッド指定から、各セルの (x, y, w, h) を返す（行優先）"""
    g = {k: st.number(v, where) for k, v in grid.items()}
    gx, gy, gw, gh = g.get("x", 0), g.get("y", 0), g.get("w", CANVAS_W), g.get("h", CANVAS_H)
    cols = g.get("cols", "auto")
    if cols == "row":                 # 個数にかかわらず 1 行に並べる（番号つきの横並びなど）
        cols_, rows_ = max(1, n), 1
    elif cols in ("auto", None) or not isinstance(cols, (int, float)):
        rows_ = max(1, math.ceil(n / 4))
        cols_ = max(1, math.ceil(n / rows_))
    else:
        cols_ = max(1, int(cols))
        rows_ = max(1, math.ceil(n / cols_))
    gap = g.get("gap", 16)
    gapx, gapy = (gap.get("x", 16), gap.get("y", 16)) if isinstance(gap, dict) else (gap, gap)
    cw = max(0.0, (gw - gapx * (cols_ - 1)) / cols_)
    ch = g.get("cell_h") or max(0.0, (gh - gapy * (rows_ - 1)) / rows_)
    cells = []
    for i in range(n):
        r, c = divmod(i, cols_)
        shift = 0.0
        if g.get("last_row") == "center" and r == rows_ - 1:
            in_row = n - r * cols_
            shift = (cols_ - in_row) * (cw + gapx) / 2
        cells.append((gx + c * (cw + gapx) + shift, gy + r * (ch + gapy), cw, ch))
    return cells


def _expand_nodes(nodes, scope, st, loc="elements"):
    out = []
    for i, n in enumerate(nodes or []):
        if not isinstance(n, dict) or not _cond(n.get("if"), scope, st):
            continue
        nloc = f"{loc}[{i}]"
        if "repeat" in n and "grid" in n:
            rep = n["repeat"]
            items = _items(scope, rep)
            cells = _grid_layout(len(items), n["grid"], st, f"（repeat '{rep}'）")
            prev, st.cur_repeat = st.cur_repeat, rep
            for k, (item, cell) in enumerate(zip(items, cells)):
                st.cur_item = k
                sc = _child_scope(scope, item, k, len(items), rep)
                for j, t in enumerate(n.get("template", []) or []):
                    if isinstance(t, dict) and _cond(t.get("if"), sc, st):
                        out.append(_expand_element(t, sc, st, cell, f"{nloc}.template[{j}]"))
            st.cur_repeat, st.cur_item = prev, None
            if st.squeeze.pop(rep, 0) and rep not in st.quiet_squeeze:
                d = st.slots.get(rep) if isinstance(st.slots.get(rep), dict) else {}
                mx = d.get("max") if isinstance(d.get("max"), int) else None
                cw, ch = (cells[0][2], cells[0][3]) if cells else (0, 0)
                st.warn(f"パターン '{st.pname}' の「{d.get('label') or rep}」（スロット '{rep}'）が {len(items)} 個で、枠に収まりません"
                        f"（1 個あたり約 {cw:.0f}×{ch:.0f}px に潰れ、中身が重なったりはみ出したりします）"
                        + (f" → この構図は {mx} 個までです。{mx} 個以下に絞るか、スライドを分けてください"
                           if mx else " → 個数を減らすか、スライドを分けてください"))
        elif "repeat" in n:
            st.error(f"repeat '{n['repeat']}' には grid と template が必要です（{nloc}） → "
                     f'{{"repeat": "{n["repeat"]}", "grid": {{"x":..,"y":..,"w":..,"h":..,"cols":"auto"}}, "template": [...]}}')
        else:
            out.append(_expand_element(n, scope, st, None, nloc))
    return out


# ---------------------------------------------------------------- スロット値の正規化と展開
def _field_value(fd, x):
    """records の 1 項目の値を、項目の種類（text / list / flag）と values（候補・別名）にそろえる"""
    fd = fd if isinstance(fd, dict) else {}
    kind = fd.get("kind", "text")
    if kind == "list":
        return [_to_text(e).strip() for e in (x if isinstance(x, list) else ([] if x is None else [x]))]      # 位置が意味を持つので空の項目も残す
    if kind == "flag":
        return _as_flag(x if x is not None else fd.get("default"))      # 項目が省かれたときは default（宣言があれば）。slot の flag と同じ扱い
    t = _to_text(x) if not isinstance(x, dict) else ""
    if isinstance(fd.get("values"), dict):
        c = _canon_value(fd, t)
        if c is not None:
            return c
    return t


def _norm_value(d, v):
    kind = d.get("kind", "text")
    if v is None or (isinstance(v, str) and not v.strip() and kind not in ("text", "flag")):
        v = d.get("default")
    if kind == "flag":
        return _as_flag(v)
    if kind == "text":
        if v is None:
            t = ""
        elif isinstance(v, list):
            t = "\n".join(_to_text(x) for x in v)
        else:
            t = _to_text(v) if not isinstance(v, dict) else ""
        if isinstance(d.get("values"), dict):
            c = _canon_value(d, t)
            if c is not None:
                return c
        return t
    if kind == "list":
        if v is None:
            return []
        if not isinstance(v, list):
            v = [v]
        return [_to_text(x) for x in v if _to_text(x).strip()]
    if kind == "records":
        if not isinstance(v, list):
            return []
        fields = d.get("fields") or {}
        out = []
        for it in v:
            if isinstance(it, dict) and not _item_blank("records", it):
                rec = {k: (_field_value(fields[k], x) if k in fields else _to_text(x)) for k, x in it.items()}
                for f, fd in fields.items():
                    if f not in rec:
                        rec[f] = _field_value(fd, None)
                out.append(rec)
        return out
    if kind == "image":
        return v if isinstance(v, str) else ""
    return v


def over_max_message(name, label, n, mx):
    """個数が max を超えたときの警告文（validate と expand で同じ文）"""
    return (f"スロット '{name}'（{label}）が {n} 個で、最大 {mx} 個を超えています"
            f" → {n} 個のうち先頭の {mx} 個だけ描きました（残り {n - mx} 個は描きません）。{mx} 個までに絞るか、2 枚に分けてください")


def _build_scope(slide, pattern, deck, page, total, st=None):
    slots = pattern.get("slots") if isinstance(pattern.get("slots"), dict) else {}
    raw = slide.get("slots") if isinstance(slide.get("slots"), dict) else {}
    scope = {}
    for name, d in slots.items():
        scope[name] = _norm_value(d if isinstance(d, dict) else {}, raw.get(name))
        mx = d.get("max") if isinstance(d, dict) else None
        if isinstance(mx, int) and not isinstance(mx, bool) and mx >= 0 and isinstance(scope[name], list) and len(scope[name]) > mx \
                and d.get("kind") in ("list", "records"):
            # max を超えた分は描かない（枠の外や結論帯の下に隠れて描くより、潰れずに読める）。警告は validate が出していなければここで出す
            if st is not None and name not in st.quiet_squeeze:
                st.warn(over_max_message(name, d.get("label") or name, len(scope[name]), mx))
            scope[name] = scope[name][:mx]
        if isinstance(d, dict) and d.get("kind") == "image" and isinstance(raw.get(f"{name}_alt"), str):
            scope[f"{name}_alt"] = raw[f"{name}_alt"].strip()       # 画像の代替テキスト（読み上げ・画像が出ないときの表示）
    meta = (deck or {}).get("meta", {}) if isinstance(deck, dict) else {}
    scope.setdefault("page", str(page))
    scope.setdefault("total", str(total))
    scope.setdefault("deck", {"title": str(meta.get("title", "") or ""), "brand": str(meta.get("brand", "") or "")})
    scope.setdefault("slide", {"title": str(slide.get("title", "") or "")})
    return scope


def _select_variant(pattern, scope, st):
    """variants_by のスロットの個数に合う variants を選ぶ。無ければ個数が近い（小さい方優先）ものを使い、注意を出す"""
    var = pattern.get("variants")
    by = pattern.get("variants_by")
    if not isinstance(var, dict) or not isinstance(by, str) or not by:
        return None
    n = len(_items(scope, by))
    keys = sorted(int(k) for k in var if str(k).isdigit())
    if not keys:
        return None
    if str(n) in var:
        return str(n), var[str(n)]
    pick = max([k for k in keys if k <= n] or [keys[0]])
    st.warn(f"パターン '{st.pname}' に {by} が {n} 個の構図がないため、{pick} 個用の構図で描きます"
            f"（用意されている個数: {', '.join(str(k) for k in keys)}）")
    return str(pick), var[str(pick)]


def expand(slide, pattern, theme, deck=None, page=1, total=1, warn=None, errors=None, quiet_squeeze=()):
    """スライドとパターンを、hex に解決済みの canvas 要素列に展開する。戻り値 (elements, background_hex)。
    warn(msg): 文字あふれ・個数のずれなど内容に由来する注意の出し先。errors（リスト）: パターン作者の誤り（未知の色・
    トークン・差し込み）の出し先（省略時は warn に流す）"""
    st = _St(theme, warn, errors, pattern.get("name", ""), pattern.get("slots"), quiet_squeeze)
    scope = _build_scope(slide, pattern, deck, page, total, st)
    base = list(pattern.get("elements") or [])
    bg_spec = pattern.get("background", "background")
    vkey, var = _select_variant(pattern, scope, st) or (None, None)
    elements = _expand_nodes(base, scope, st, "elements")
    if var:
        elements += _expand_nodes(list(var.get("elements") or []), scope, st, f"variants[{vkey}].elements")
        bg_spec = var.get("background", bg_spec)
    bg = st.color(bg_spec, "（background）") if isinstance(bg_spec, str) else "#FFFFFF"
    _apply_groups(st)                                 # fit.group のサイズをそろえる（形トークンの太さ・字間より前）
    _warn_short_last_lines(elements, st)
    shp.apply_text_tokens(elements, st.tokens)       # 形トークンの太さ・字間（classic は変化なし）
    shp.apply_pattern_shape(elements, st.tokens)     # 自前の見出し骨格（role）と角丸の箱にかかる帯。_role の印をここで消す
    return elements, bg


def _warn_short_last_lines(elements, st):
    """エンジンが入れた改行（soft の br）で、最終行が 1〜2 文字だけの段落を 1 本の警告にまとめる（泣き別れ。型の文字枠は
    エンジンが改行を決めるので、check_layout が見落とさないようここで知らせる）"""
    hits = []
    for e in ce.flatten(elements):
        tx = e.get("text") if isinstance(e.get("text"), dict) else {}
        for p in tx.get("paragraphs", []) or []:
            runs = p.get("runs", []) if isinstance(p, dict) else []
            if not any(r.get("soft") for r in runs):
                continue
            lines, cur = [], ""
            for r in runs:
                if r.get("br"):
                    lines.append(cur)
                    cur = ""
                else:
                    cur += r.get("text", "") if isinstance(r.get("text"), str) else ""
            lines.append(cur)
            last, prev = lines[-1].strip(), lines[-2].strip() if len(lines) > 1 else ""
            if 1 <= _chars(last) <= 2 and _chars(prev) >= 4:
                hits.append(f"{prev[-6:]}／{last}")
    if hits:
        st.warn(f"パターン '{st.pname}' の文字枠 {len(hits)} 個で、最終行が 1〜2 文字だけになります（{'、'.join('「' + h + '」' for h in hits[:3])}"
                f"{' ほか' if len(hits) > 3 else ''}） → その文を少し言い換える・字数を増減して、行の終わりに 3 文字以上が残るようにしてください")


def to_canvas_slide(slide, pattern, theme, deck=None, page=1, total=1, warn=None, errors=None):
    """pattern スライドを同じ見た目の {"type": "canvas"} スライド dict にする（HTML / PPTX の既存の canvas 描画にそのまま渡せる）"""
    els, bg = expand(slide, pattern, theme, deck, page, total, warn, errors)
    out = {"type": "canvas", "background": bg, "elements": els}
    for k in ("title", "notes", "_source_page", "source_page", "id", "section"):
        if k in slide:
            out[k] = slide[k]
    if not out.get("title"):
        scope_title = (slide.get("slots") or {}).get("title") if isinstance(slide.get("slots"), dict) else None
        if isinstance(scope_title, str):
            out["title"] = scope_title
    out["pattern"] = pattern.get("name", slide.get("pattern", ""))
    return out


NARROW_STRETCH_MAX = 1.25     # 狭い構図を横に広げてよい上限（文字の倍率に対する比）。これを超える余りは左右の余白にする


def _placement(pattern, rect, has_footer=False):
    """型（設計寸法 sw x sh）を矩形 rect=(x, y, w, h) に写す倍率と位置。戻り値 (sx, sy, dx, dy, k)。k = 文字・線・余白の倍率。
    広い構図: 縦横比を保って収める（sx = sy = k）。横は中央、縦は valign。
    狭い構図（"_narrow"）: 文字は k = min(w/sw, h/sh) で拡縮し、横は矩形の幅いっぱいまで（文字の倍率の NARROW_STRETCH_MAX 倍まで）広げる。
    縦は k のまま（余りは valign）。設計幅より広い矩形でも左右に余白が残らず、合成スライドのほかのブロックの端とそろう"""
    rx, ry, rw, rh = rect
    sw, sh = design_size(pattern)
    valign = pattern.get("valign") if pattern.get("valign") in ("top", "middle") else "top"
    k = min(rw / sw, rh / sh)
    top_lock = False
    if has_footer and rh / sh < min(1.0, rw / sw) - 1e-9:
        # 結論帯・出典があって高さで縮むとき: 型の下端が帯にくっつかないよう、下に BODY_BOTTOM_GAP 以上の隙間を残す（上詰め）
        k = min(rw / sw, max(rh - BODY_BOTTOM_GAP, rh * 0.85) / sh)
        top_lock = True
    sx = k
    if pattern.get("_narrow"):
        mx = pattern.get("_max_stretch") if _pos(pattern.get("_max_stretch")) else NARROW_STRETCH_MAX
        sx = max(k, min(rw / sw, k * mx))
    dx = rx + (rw - sw * sx) / 2
    dy = ry if top_lock else ry + ((rh - sh * k) / 2 if valign == "middle" else 0)
    return sx, k, dx, dy, k


def _keep_ellipses_round(src, dst, sx, k, dx):
    """横に広げた要素列 dst の中の楕円（geom ellipse）を、元の縦横比のまま（倍率 k）に戻す。中心は動かさない（円の番号・丸い顔写真が楕円にならない）"""
    for a, b in zip(src, dst):
        if a.get("kind") == "group":
            _keep_ellipses_round(a.get("children", []), b.get("children", []), sx, k, dx)
            continue
        if a.get("geom") == "ellipse" and _num(a.get("w")) and _num(a.get("x")) and abs(sx - k) > 1e-9:
            w2 = a["w"] * k
            b["x"] = (a["x"] * sx + dx) + (a["w"] * sx - w2) / 2
            b["w"] = w2


def pattern_block_elements(slide, pattern, rect, theme, deck=None, page=1, total=1, warn=None, errors=None, valign=None):
    """pattern の本文（frame:"body" の型）を、任意の矩形 rect=(x, y, w, h) に描く canvas 要素列にして返す。
    型は設計寸法（size）の座標で書かれているので、縦横比を保って rect に収まるよう拡縮して置く
    （横は中央、縦は valign: "top"（上寄せ）/ "middle"。省略時はパターンの "valign"、それも無ければ "top"）。合成スライドのブロックとしても、pattern スライドの本文としても使う。
    狭い構図（narrow）のときは、横を矩形の幅いっぱいまで広げる（_placement）。
    frame:"full" の型を渡したときは、1280x720 全体を rect に収める（縮小した全面図として置ける）。
    見出し・罫線・フッター・結論帯・出典は含まない（それらは build_deck の見出し骨格と common_parts が描く）。"""
    rx, ry, rw, rh = rect
    pattern = effective_pattern(pattern, rw, rh)            # 幅・高さが小さい矩形には、型の narrow の構図を使う
    els, _bg = expand(slide, pattern, theme, deck, page, total, warn, errors)
    if valign is not None:
        pattern = dict(pattern, valign=valign)
    has_footer = isinstance(slide, dict) and ("conclusion" in slide or "source" in slide) and "_block" not in slide
    sx, sy, dx, dy, k = _placement(pattern, rect, has_footer)
    if abs(sx - 1.0) < 1e-9 and abs(sy - 1.0) < 1e-9 and dx == 0 and dy == 0:
        return els
    out = ce.transform_elements(els, sx, sy, dx, dy, ts=k)
    if pattern.get("_narrow") and abs(sx - k) > 1e-9:
        _keep_ellipses_round(els, out, sx, k, dx)
    return out


BODY_BOTTOM_GAP = 20       # 結論帯・出典つきで縮むとき、型の下端と帯のあいだに残す隙間（px）
MIN_BODY_SCALE = 0.5       # 本文矩形への縮小率の下限の目安（これより小さいと文字が読めない・PPTX の文字サイズが 0 に近づく）


BLOCK_MIN_BODY_SCALE = 0.7   # 合成スライドのブロックに置くときの下限（ブロックは本文領域より小さいので、縮み方が大きくなる前に知らせる）


def _pattern_count(slide, pattern):
    """スライドが実際に描く個数（狭い構図の variants_by が指すスロットの個数）。分からなければ None"""
    vb = pattern.get("variants_by")
    if not (isinstance(vb, str) and isinstance(slide, dict)):
        return None
    sd = (pattern.get("slots") or {}).get(vb)
    slots = slide.get("slots") if isinstance(slide.get("slots"), dict) else {}
    return _drawn_count(slots.get(vb), sd)


def _reduce_hint(pattern, cnt, shown, base_mw):
    """個数を減らせば幅の下限を満たせるときの直し方（「項目を n 個までにする」）。減らしても満たせない・減らせる個数が無いときは None。
    個数別の下限（min_width_by_count）が無い個数は、型の幅の下限 base_mw を使う"""
    by = pattern.get("min_width_by_count") if isinstance(pattern.get("min_width_by_count"), dict) else {}
    var = pattern.get("variants")
    avail = sorted(int(k) for k in var if str(k).isdigit()) if isinstance(var, dict) else []
    if cnt is None:
        return None
    for c in sorted((c for c in avail if c < cnt), reverse=True):
        need = by.get(str(c)) if _pos(by.get(str(c))) else base_mw
        if need is None or shown >= need - 0.5:
            return f"項目を {c} 個までにする" + (f"（{c} 個なら幅 {int(need)}px 以上で読める）" if need else "")
    return None


def body_rect_problems(slide, pattern, body, in_block=False):
    """frame:"body" の型を実際の本文矩形 body（x/y/w/h の dict）に写すときの問題 (fails, warns)。
    幅・高さが 0 以下は fail、縮小率が MIN_BODY_SCALE 未満は warn（文字が極端に小さくなる。PPTX では文字サイズが 0 になりうる）。
    in_block=True（合成スライドのブロック）は下限を BLOCK_MIN_BODY_SCALE にし、直し方を「ブロックを広げる」にする
    （ブロックでは style.body の x / y / w / h が無視されるため）。
    型に min_width（幅の下限。設計寸法を写したあとの実際の幅）があり、それを下回るときも warn。個数別の下限（min_width_by_count）は、描く個数のものを使う。
    型に narrow（狭いとき用の構図）があり、body の幅が narrow.below 未満（高さの条件つきの段は高さも below_h 未満）なら、その構図の寸法で調べる。"""
    w, h = body.get("w", 0), body.get("h", 0)
    if not (isinstance(w, (int, float)) and isinstance(h, (int, float))) or w <= 0 or h <= 0:
        fix = ("ブロックを広げる（columns / rows の比率、col_span / row_span）" if in_block
               else "style.body の w / h を 0 より大きくする（または style.body を消す）")
        return [f"本文領域の大きさが 0 以下です（{w}×{h}）→ {fix}"], []
    pattern = effective_pattern(pattern, w, h)
    sw, sh = design_size(pattern)
    k = min(w / sw, h / sh)
    limit = BLOCK_MIN_BODY_SCALE if in_block else MIN_BODY_SCALE
    warns = []
    mw = base_mw = min_width_of(pattern)
    by = pattern.get("min_width_by_count")
    cnt = _pattern_count(slide, pattern) if pattern.get("_narrow") else None
    if pattern.get("_narrow") and isinstance(by, dict) and cnt is not None:
        # 個数によって読める幅の下限が違う狭い構図（例: 4 案の比較表は 700px 以上）。個数は実際に描かれる個数
        v_ = by.get(str(cnt))
        if _pos(v_):
            mw = v_
    if k < limit and not (mw and sw * k < mw - 0.5):          # 幅の下限の警告（下）が同じことを言うので、重ねない
        fix = ("ブロックを広げる（columns / rows の比率、col_span / row_span）か、単独の pattern スライドにする" if in_block
               else "style.body の h / w を戻す、または lead・結論帯・出典を減らす")
        warns.append(f"本文領域が小さすぎて、型を {k * 100:.0f}% に縮めます（本文領域 {int(w)}×{int(h)}・型の設計寸法 {int(sw)}×{int(sh)}）"
                     f" → {fix}")
    # 型が実際に占める幅（高さで縮むときは w より狭い）。狭い構図の min_width は、置く矩形の幅そのもので比べる
    # （狭い構図は高さに合わせて縮むことがあり、占める幅は幅の足りなさを表さないため）
    shown = w if pattern.get("_narrow") else sw * k
    if mw and shown < mw - 0.5:
        name = pattern.get("name") or slide.get("pattern") or "この型"
        alt = pattern.get("block_alt") if isinstance(pattern.get("block_alt"), str) and pattern.get("block_alt").strip() else "幅の狭い型（numbered-list など）にする"
        red = _reduce_hint(pattern, cnt, shown, base_mw)
        alts = (red + "・" if red else "") + alt
        if in_block:
            fix = f"ブロックを広げる（col_span で横に広げる・columns の比率を変える）・単独のスライドにする・{alts}"
        else:
            fix = f"本文領域を広げる（style.body の w を戻す）・{alts}"
        who = f"この型（{name}）は" + (f" {cnt} 個のとき " if mw != base_mw and cnt is not None else "")
        warns.append(f"{who}幅 {int(mw)}px 以上向きです（いま {int(shown)}px）→ {fix}")
    return [], warns


# ---------------------------------------------------------------- スライド側の検証
def _default_theme():
    f = ROOT / "templates" / "themes" / "default.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"colors": {}, "fonts": {}}


def _chars(s):
    return len(re.sub(r"\s", "", s)) if isinstance(s, str) else 0


def _item_blank(kind, it):
    """list / records の項目が空白だけか（展開時に捨てられる項目）"""
    def blank(x):
        if isinstance(x, list):
            return all(blank(e) for e in x)
        return x is None or x is False or (isinstance(x, str) and not x.strip())
    if kind == "records":
        return isinstance(it, dict) and all(blank(x) for x in it.values())
    return blank(it)


def slot_problems(slide, pattern, deck_dir=None):
    """スロット値の検査。戻り値 (errors, warnings)（どちらも文字列のリスト。位置情報なし）"""
    errs, warns = [], []
    pname = pattern.get("name", slide.get("pattern", ""))
    slots = pattern.get("slots") if isinstance(pattern.get("slots"), dict) else {}
    raw = slide.get("slots")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return [f"slots はオブジェクトで指定してください（例: \"slots\": {{\"title\": \"...\"}}）"], warns
    def _alt_of(k):
        """画像スロット名 + "_alt"（その画像の代替テキスト）なら画像スロット名、そうでなければ None"""
        base = k[:-4] if isinstance(k, str) and k.endswith("_alt") else None
        d = slots.get(base) if base else None
        return base if isinstance(d, dict) and d.get("kind") == "image" and k not in slots else None
    for k in raw:
        if _alt_of(k):
            if not isinstance(raw[k], str):
                warns.append(f"スロット '{k}'（画像の代替テキスト）は文字列で指定してください（無視します）")
            continue
        if k not in slots:
            near = difflib.get_close_matches(k, list(slots), n=2, cutoff=0.5)
            hint = f"もしかして: {', '.join(near)}" if near else f"使えるスロット: {', '.join(slots)}"
            warns.append(f"スロット '{k}' はパターン '{pname}' にありません（無視します）→ {hint}")
    for name, d in slots.items():
        d = d if isinstance(d, dict) else {}
        kind = d.get("kind", "text")
        v = raw.get(name)
        label = d.get("label") or name
        # 空白だけの項目は展開時に捨てられる（_norm_value）ので、個数・必須の判定も捨てたあとの個数で行う
        n_eff = None
        if isinstance(v, list) and kind in ("list", "records"):
            blanks = [k for k, it in enumerate(v) if _item_blank(kind, it)]
            for k in blanks[:5]:
                warns.append(f"スロット '{name}' の {k + 1} 個目が空です（無視します）→ 文字を入れるか、その項目を消してください")
            n_eff = len(v) - len(blanks)
        empty = (v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)
                 or (n_eff is not None and n_eff == 0))
        if empty:
            if d.get("required") and d.get("default") in (None, ""):
                ex = d.get("example")
                exs = f"例: {json.dumps(ex, ensure_ascii=False)}" if ex is not None else "値を書いてください"
                errs.append(f"必須のスロット '{name}'（{label}）がありません" + ("（空の項目だけです）" if n_eff == 0 else "")
                            + f" → slots に \"{name}\" を足してください（{exs}）")
            continue
        if kind == "text":
            if isinstance(v, (list, dict)):
                errs.append(f"スロット '{name}' は文字列で指定してください → \"{name}\": \"文章\"")
                continue
            mc = d.get("max_chars")
            if mc and _chars(str(v)) > mc and not _has_alias(d, v):
                warns.append(f"スロット '{name}'（{label}）が {_chars(str(v))} 文字で、目安（{mc} 文字）を超えています"
                             f" → 短くするか、文字サイズが自動で縮みます（収まらないと枠からあふれます）")
            _values_check(f"スロット '{name}'（{label}）", d, v, warns)
        elif kind == "list":
            if not isinstance(v, list):
                errs.append(f"スロット '{name}' は文字列の配列で指定してください → \"{name}\": [\"1 点目\", \"2 点目\"]")
                continue
            _count_check(name, label, n_eff, d, warns, errs)
            _count_of_check(name, label, n_eff, d, raw, slots, warns)
            mc = d.get("max_chars")
            hi = d.get("max") if isinstance(d.get("max"), int) and not isinstance(d.get("max"), bool) else None
            cap = _WarnCap(warns)
            live = 0
            for k, it in enumerate(v):
                if _item_blank("list", it):
                    continue
                live += 1
                if hi is not None and live > hi:
                    break                     # max を超えた分は描かれないので、個別の検査はしない（over-max の警告 1 本で足りる）
                if isinstance(it, (list, dict)):
                    errs.append(f"スロット '{name}' の {k + 1} 個目は文字列にしてください")
                elif mc and _chars(str(it)) > mc:
                    cap.add(("文字数", name), f"スロット '{name}' の {k + 1} 個目が {_chars(str(it))} 文字で、目安（{mc} 文字）を超えています"
                            f" → 短くするか、文字サイズが縮みます", f"スロット '{name}' の文字数の目安超え")
            cap.flush()
        elif kind == "records":
            if not isinstance(v, list) or any(not isinstance(it, dict) for it in v):
                fields = d.get("fields") or {}
                sample = {f: "..." for f in fields} or {"head": "...", "body": "..."}
                errs.append(f"スロット '{name}' はオブジェクトの配列で指定してください → \"{name}\": [{json.dumps(sample, ensure_ascii=False)}]")
                continue
            _count_check(name, label, n_eff, d, warns, errs)
            _count_of_check(name, label, n_eff, d, raw, slots, warns)
            fields = d.get("fields") or {}
            hi = d.get("max") if isinstance(d.get("max"), int) and not isinstance(d.get("max"), bool) else None
            cap = _WarnCap(warns)
            bad_counts = {}          # 項目の list の個数が合わない: {項目名: [(何個目, 個数, 相手の個数)]}
            flagged = {}             # at_most を数える: {項目名: [何個目]}
            live = 0
            for k, it in enumerate(v):
                if _item_blank("records", it):
                    continue
                live += 1
                if hi is not None and live > hi:
                    break                     # max を超えた分は描かれないので、個別の検査はしない
                for f, fd in fields.items():
                    fd = fd if isinstance(fd, dict) else {}
                    fv = it.get(f)
                    if (fv is None or fv == "" or fv == []) and fd.get("required"):
                        errs.append(f"スロット '{name}' の {k + 1} 個目に必須の項目 '{f}' がありません")
                    mc = fd.get("max_chars")
                    if fd.get("kind") == "list":
                        if fv is not None and not isinstance(fv, (list, str)):
                            errs.append(f"スロット '{name}' の {k + 1} 個目の '{f}' は文字列の配列にしてください → \"{f}\": [\"1 つ目\", \"2 つ目\"]")
                            continue
                        for j, e in enumerate(fv if isinstance(fv, list) else ([fv] if fv else [])):
                            if isinstance(e, (list, dict)):
                                errs.append(f"スロット '{name}' の {k + 1} 個目の '{f}' の {j + 1} 番目は文字列にしてください")
                            elif mc and isinstance(e, str) and _chars(e) > mc:
                                cap.add(("文字数", name, f), f"スロット '{name}' の {k + 1} 個目の '{f}' の {j + 1} 番目が {_chars(e)} 文字で、目安（{mc} 文字）を超えています"
                                        f" → 短くするか、文字サイズが縮みます", f"スロット '{name}' の '{f}' の文字数の目安超え")
                        ref = fd.get("count_of")
                        if isinstance(ref, str) and ref in slots:
                            want = _drawn_count(raw.get(ref), slots[ref])
                            have = len(fv) if isinstance(fv, list) else (1 if fv else 0)
                            if want is not None and have != want:
                                bad_counts.setdefault(f, []).append((k + 1, have, want, ref))
                        continue
                    if fd.get("kind") == "flag":
                        if _as_flag(fv if fv is not None else fd.get("default")):
                            flagged.setdefault(f, []).append(k + 1)
                        continue
                    if isinstance(fv, str) and mc and _chars(fv) > mc and not _has_alias(fd, fv):
                        cap.add(("文字数", name, f), f"スロット '{name}' の {k + 1} 個目の '{f}' が {_chars(fv)} 文字で、目安（{mc} 文字）を超えています"
                                f" → 短くするか、文字サイズが縮みます", f"スロット '{name}' の '{f}' の文字数の目安超え")
                    msg = _values_check(f"スロット '{name}' の {k + 1} 個目の '{f}'", fd, fv)
                    if msg:
                        cap.add(("候補", name, f), msg, f"スロット '{name}' の '{f}' の候補にない値")
                    if fd.get("at_most") is not None and isinstance(fv, str) and fv.strip():
                        flagged.setdefault(f, []).append(k + 1)
                for f in it:
                    if fields and f not in fields:
                        near = difflib.get_close_matches(f, list(fields), n=2, cutoff=0.5)
                        cap.add(("未知", name, f), f"スロット '{name}' の {k + 1} 個目の項目 '{f}' はパターンにありません（無視します）"
                                + (f" → もしかして: {', '.join(near)}" if near else ""), f"スロット '{name}' の未知の項目 '{f}'")
            cap.flush()
            for f, rows in bad_counts.items():
                ref, want = rows[0][3], rows[0][2]
                rl = (slots[ref] or {}).get("label") or ref
                rows_text = _rows_text([r[0] for r in rows], min(live, hi) if hi is not None else live)
                if len({r[1] for r in rows}) == 1:
                    what = f"'{f}' が {rows[0][1]} 個で"
                else:
                    what = f"'{f}' の個数が（{'、'.join(f'{r[0]} 個目 {r[1]} 個' for r in rows[:4])}）で"
                warns.append(f"スロット '{name}' の {rows_text}は、{what}、「{rl}」（スロット '{ref}'）の数 {want} 個と合っていません"
                             f" → {want} 個そろえて書いてください（順番は「{rl}」の並びと同じ）")
            for f, rows in flagged.items():
                fd = fields.get(f) if isinstance(fields.get(f), dict) else {}
                am = fd.get("at_most")
                if isinstance(am, int) and not isinstance(am, bool) and am >= 0 and len(rows) > am:
                    fl = fd.get("label") or f
                    warns.append(f"スロット '{name}' の '{f}'（{fl}）が {len(rows)} 個（{'・'.join(str(r) for r in rows[:6])} 個目）に付いています"
                                 f" → 付けるのは {am} 個までにしてください（多いと強調の意味がなくなります）")
        elif kind == "image":
            if not isinstance(v, str):
                errs.append(f"スロット '{name}' は画像のパス（文字列）で指定してください → \"{name}\": \"assets/photo.png\"")
            else:
                msg = ce.check_image_path(v, deck_dir)
                if msg:
                    errs.append(f"スロット '{name}'（{label}）の画像 '{v}' が使えません: {msg}")
    return errs, warns


def _eff_count(v, d):
    """スロットの値の個数（空白だけの項目を除く）。list / records 以外・値なしは None"""
    d = d if isinstance(d, dict) else {}
    if d.get("kind") not in ("list", "records") or not isinstance(v, list):
        return None
    return sum(1 for it in v if not _item_blank(d.get("kind"), it))


def _drawn_count(v, d):
    """実際に描かれる個数（空白だけの項目を除き、max で頭打ち）。比べる相手の個数として使う"""
    n = _eff_count(v, d)
    hi = d.get("max") if isinstance(d, dict) else None
    return min(n, hi) if n is not None and isinstance(hi, int) and not isinstance(hi, bool) else n


def _rows_text(rows, total):
    """警告に書く「何個目か」: すべて → 「すべて（N 個）」、一部 → 「1・3 個目」（多いときは先頭 5 つ＋ほか）"""
    if total and len(rows) >= total:
        return f"すべての項目（{total} 個）"
    txt = "・".join(str(r) for r in rows[:5])
    return f"{txt}{' ほか' if len(rows) > 5 else ''} 個目の項目"


class _WarnCap:
    """同じ種類の警告を先頭 3 件に絞り、残りは「ほか N 件」の 1 行にまとめる（項目が多いときの警告の爆発を防ぐ）。
    残りが 1 件だけのときはまとめず、そのまま出す（「ほか 1 件」と書くより本文を見せたほうが直しやすい）"""
    LIMIT = 3

    def __init__(self, warns):
        self.warns = warns
        self.groups = {}

    def add(self, key, msg, summary):
        g = self.groups.setdefault(key, [[], summary, 0])
        g[2] += 1
        if len(g[0]) <= self.LIMIT:
            g[0].append(msg)              # 先頭 LIMIT + 1 件だけ持つ（巨大な入力でもメモリを使わない）

    def flush(self):
        for msgs, summary, n in self.groups.values():
            if n <= self.LIMIT + 1:
                self.warns.extend(msgs)
            else:
                self.warns.extend(msgs[:self.LIMIT])
                self.warns.append(f"{summary}は、ほかに {n - self.LIMIT} 件あります（上と同じ直し方です）")
        self.groups = {}


def _has_alias(d, v):
    """v が d の values（候補と別名）のどれかに当たるか（当たるなら文字数の目安は問わない）"""
    vals = d.get("values") if isinstance(d, dict) else None
    return isinstance(vals, dict) and isinstance(v, (str, int, float)) and _canon(vals, v) is not None


def _count_of_check(name, label, n, d, raw, slots, warns):
    """スロットの "count_of": "別のスロット名" — 個数がそのスロットと同じでなければ警告（案の数と各行の値の数など）。
    どちらも max で頭打ちにした「描かれる個数」で比べる（max を超えた分は描かれないので、そろえる数も max まで）"""
    ref = d.get("count_of")
    if not isinstance(ref, str) or ref not in slots:
        return
    want = _drawn_count(raw.get(ref), slots[ref])
    hi = d.get("max") if isinstance(d.get("max"), int) and not isinstance(d.get("max"), bool) else None
    have = min(n, hi) if n is not None and hi is not None else n
    if want is not None and have is not None and have != want:
        rl = (slots[ref] or {}).get("label") or ref
        warns.append(f"スロット '{name}'（{label}）が {have} 個で、「{rl}」（スロット '{ref}'）の数 {want} 個と合っていません → {want} 個そろえてください")


def _values_check(who, d, v, warns=None):
    """スロット・項目の "values"（候補と別名）に無い値の警告文を返す（無ければ None）。warns を渡すとそこへ足す。
    候補にない値の扱いは、スロット・項目の "unknown_as"（正規の値）で宣言された値として描かれる。宣言が無ければ、どの状態にも当てはまらない"""
    vals = d.get("values") if isinstance(d, dict) else None
    if not isinstance(vals, dict) or not isinstance(v, (str, int, float, bool)) or v == "" or isinstance(v, bool):
        return None
    if _canon(vals, v) is not None:
        return None
    def _als(k, al):
        xs = [str(a) for a in (al if isinstance(al, list) else [al]) if a not in ("", None) and str(a) != str(k)]
        return f"{k}（{'・'.join(xs[:3])}{'…' if len(xs) > 3 else ''}）" if xs else str(k)
    names = " / ".join(_als(k, al) for k, al in vals.items())
    ua = d.get("unknown_as")
    tail = (f"。候補にない値は「{ua}」として描きます" if isinstance(ua, str) and ua in vals
            else "。候補にない値は、どの状態にも当てはまらない扱いになります（状態による見た目の切り替えが働きません）")
    msg = f"{who} の値 \"{v}\" は候補にありません → {names} のいずれかにしてください" + ("（… のほかにも別名があります。型の show で確かめられます）" if "…" in names else "") + tail
    if warns is not None:
        warns.append(msg)
    return msg


def _count_check(name, label, n, d, warns, errs):
    lo, hi = d.get("min"), d.get("max")
    if isinstance(lo, int) and n < lo:
        warns.append(f"スロット '{name}'（{label}）が {n} 個で、最小 {lo} 個を下回っています → 項目を足してください")
    if isinstance(hi, int) and n > hi:
        warns.append(over_max_message(name, label, n, hi))


BLOCK_MIN_FONT = 12.0       # 狭い矩形に置いたときの、文字の実測の下限（px）。これを下回ると警告（縮小率ではなく、描かれる文字の大きさで見る）


def min_text_px(elements):
    """展開した要素列の中で、いちばん小さく描かれる文字の大きさ (px, 要素名)。1 字だけの文字（印・番号の数字）と空の文字は数えない。文字が無ければ (None, "")"""
    best = (None, "")
    for e in ce.flatten(elements):
        tx = e.get("text")
        paras = tx.get("paragraphs") if isinstance(tx, dict) else None
        if not isinstance(paras, list):
            continue
        for p in paras:
            for r in (p.get("runs") or []) if isinstance(p, dict) else []:
                t = r.get("text") if isinstance(r, dict) else None
                sz = r.get("size") if isinstance(r, dict) and isinstance(r.get("size"), (int, float)) else (p.get("size") if isinstance(p, dict) else None)
                if isinstance(t, str) and len(t.strip()) >= 2 and isinstance(sz, (int, float)) and not isinstance(sz, bool):
                    if best[0] is None or sz < best[0]:
                        best = (sz, str(e.get("name") or ""))
    return best


BLOCK_MIN_TAG_FONT = 11.0   # 札・タグ・印（要素名に「札」「タグ」「印」を含む文字）の下限


def worst_small_text(elements, scale):
    """展開した要素列を倍率 scale で描いたときの、下限に対していちばん足りない文字 (描かれる大きさ, 要素名, 下限)。足りない文字が無ければ None。
    下限は本文・見出しが BLOCK_MIN_FONT、札・タグ・印が BLOCK_MIN_TAG_FONT"""
    worst = None
    for e in ce.flatten(elements):
        tx = e.get("text")
        paras = tx.get("paragraphs") if isinstance(tx, dict) else None
        if not isinstance(paras, list):
            continue
        name = str(e.get("name") or "")
        thr = BLOCK_MIN_TAG_FONT if any(k in name for k in ("札", "タグ", "印")) else BLOCK_MIN_FONT
        for p in paras:
            for r in (p.get("runs") or []) if isinstance(p, dict) else []:
                t = r.get("text") if isinstance(r, dict) else None
                sz = r.get("size") if isinstance(r, dict) and isinstance(r.get("size"), (int, float)) else (p.get("size") if isinstance(p, dict) else None)
                if isinstance(t, str) and len(t.strip()) >= 2 and isinstance(sz, (int, float)) and not isinstance(sz, bool):
                    eff = sz * scale
                    if eff < thr - 0.05 and (worst is None or eff - thr < worst[0] - worst[2]):
                        worst = (eff, name, thr)
    return worst


def validate(slide, i, deck_dir, fail, warn, theme=None, rect_w=None, rect_h=None):
    """pattern スライドの検証（build_deck の validate_deck から呼ぶ）。
    見つからないパターン・必須スロットの欠落・型の誤りは fail、未知スロット・文字数/個数の超過・文字あふれは warn。
    最後に展開結果を canvas の検証（validate_canvas_problems）にも通す。theme を省略すると同梱の default テーマで展開する。
    rect_w: 型を置く本文矩形の幅（px）。型に narrow（狭いとき用の構図）があり rect_w がその below 未満なら、狭い構図で検査する
    rect_h: 同じく矩形の高さ（px）。省略時はスライド（ブロック）の style.body.h を使う。高さの条件つきの短い構図（below_h）の選択と、
            描かれる文字の実測（BLOCK_MIN_FONT 未満で警告）に使う"""
    head = f"{i + 1}枚目（type=pattern）: "
    name = slide.get("pattern")
    if not isinstance(name, str) or not name:
        names = available_names(deck_dir)
        fail(head + 'pattern（パターン名）が指定されていません → {"type": "pattern", "pattern": "名前", "slots": {...}} の形で書いてください'
             + (f"（使えるパターン: {', '.join(names)}）" if names else ""))
        return
    try:
        pat = load_pattern(name, deck_dir)
    except PatternError as e:
        fail(head + f"パターン '{name}' を読めません: {e}")
        return
    if pat is None:
        names = available_names(deck_dir)
        near = difflib.get_close_matches(name, names, n=2, cutoff=0.5)
        where = " / ".join(str(d) for d in pattern_dirs(deck_dir)[:4])
        fail(head + f"パターン '{name}' が見つかりません（探した場所: {where} …）"
             + (f" → もしかして: {', '.join(near)}" if near else (f" → 使えるパターン: {', '.join(names)}" if names else "")))
        return
    head = f"{i + 1}枚目（type=pattern, pattern={name}）: "
    if frame_of(pat) == "body" and not str(slide.get("title") or "").strip():
        warn(head + "title がありません（この型は見出しをプラグインが描くので、スライド直下の title が見出しになります）"
             ' → {"type": "pattern", "pattern": "' + name + '", "title": "結論を言い切る見出し", "slots": {...}} の形で書く')
    if frame_of(pat) == "full":
        # 全面の型は見出し骨格・結論帯・出典を描かない。スライド直下に書いても出力から黙って消えるので知らせる
        pslots = pat.get("slots") if isinstance(pat.get("slots"), dict) else {}
        keys = [("eyebrow", "見出し上の小見出し"), ("lead", "リード"), ("conclusion", "結論帯"), ("source", "出典")]
        if slide.get("_block") is None:
            keys.insert(0, ("title", "見出し"))          # 合成ブロックの title は形だけ満たす仮の値なので、ブロックでは知らせない
        for key, jp in keys:
            if str(slide.get(key) or "").strip():
                if key in pslots:
                    fix = f"slots の \"{key}\" に書いてください（例: \"slots\": {{\"{key}\": \"…\"}}）"
                else:
                    fix = f"この型は{jp}を持ちません。必要なら frame:\"body\" の型を使うか、型にスロット \"{key}\" を足してください"
                warn(head + f"frame:\"full\" の型は全面を自分で描くため、スライド直下の {key} は描かれません → {fix}")
        st_keys = [k for k, v in (slide.get("style") or {}).items() if isinstance(slide.get("style"), dict) and not str(k).startswith("_") and v]
        if st_keys:
            warn(head + f"frame:\"full\" の型は全面を自分で描くため、スライドの style（{', '.join(map(str, st_keys))}）は効きません"
                 " → 見た目はスロット（slots）か型の JSON で変える。見出し骨格の style を使うなら frame:\"body\" の型にする")
    pat_full = pat
    if rect_h is None and isinstance(slide.get("style"), dict) and isinstance(slide["style"].get("body"), dict):
        rect_h = slide["style"]["body"].get("h")
    pat = effective_pattern(pat, rect_w, rect_h)
    perrs, pwarns = check_pattern(pat_full, theme or _default_theme(), quick=True)
    if perrs:
        fail(head + f"パターン JSON に誤りがあります → pattern_engine.py check {pat.get('_path', name)} で詳細を確認してください\n  "
             + "\n  ".join(perrs[:10]))
        return
    errs, warns = slot_problems(slide, pat_full, deck_dir)
    if errs:
        fail(head + errs[0] + "".join(f"\n  {head}{m}" for m in errs[1:20]))
        return
    for m in warns:
        warn(head + m)
    hard: list = []
    raw_slots = slide.get("slots") if isinstance(slide.get("slots"), dict) else {}
    over = set()    # 「max 超過」の警告を出したスロット。展開側の「枠に収まらない」警告は重ねない
    for sname, d in (pat.get("slots") or {}).items():
        v = raw_slots.get(sname)
        if isinstance(d, dict) and isinstance(d.get("max"), int) and isinstance(v, list):
            if sum(1 for it in v if not _item_blank(d.get("kind", "list"), it)) > d["max"]:
                over.add(sname)
    elements, bg = expand(slide, pat, theme or _default_theme(), None, 1, 1, lambda m: warn(head + m), hard, over)
    probs = hard + ce.validate_canvas_problems({"elements": elements}, deck_dir,
                                               lambda m: warn(head + m.removeprefix("canvas: ")) if "qa_ignore" in m else None)
    if probs:
        fail(head + "展開した canvas に誤りがあります → " + probs[0] + "".join(f"\n  {head}{m}" for m in probs[1:20]))
        return
    if frame_of(pat) == "body" and _pos(rect_w) and _pos(rect_h):
        # 描かれる文字の大きさ（設計寸法の文字に、矩形に写す倍率を掛けたもの）が小さすぎないか。縮小率ではなく実測で見る
        has_footer = ("conclusion" in slide or "source" in slide) and "_block" not in slide
        _sx, _sy, _dx, _dy, kk = _placement(pat, (0, 0, rect_w, rect_h), has_footer)
        bad = worst_small_text(elements, kk)
        if bad is not None:
            eff, who, thr = bad
            nm = pat.get("name") or name
            if "_block" in slide:
                fix = "ブロックの高さを広げる（rows の比率、row_span）・項目の数を減らす・文を短くする・単独のスライドにする"
            else:
                fix = "本文領域を広げる（style.body の h / w を戻す・lead / 結論帯 / 出典を減らす）・項目の数を減らす・文を短くする"
            warn(head + f"この型（{nm}）は {int(rect_w)}×{int(rect_h)}px だと、文字が最小 {eff:.1f}px まで小さくなります"
                 f"（{who or '文字'}。目安は {thr:g}px 以上） → {fix}")


# ---------------------------------------------------------------- パターン JSON の検証
def _walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{k}]")
    elif isinstance(obj, str):
        yield path, obj


def _field_example(f, fd, k):
    fd = fd if isinstance(fd, dict) else {}
    ex = fd.get("example")
    if fd.get("kind") == "list":
        return list(ex) if isinstance(ex, list) else [f"{f} {k + 1}-1", f"{f} {k + 1}-2"]
    if fd.get("kind") == "flag":
        return ex if ex is not None else False
    return ex if isinstance(ex, str) else f"{f} {k + 1}"


def example_slide(pattern, count=None):
    """スロットの example（無ければ名前から作った仮の文）で埋めた pattern スライドを返す。
    count を渡すと list / records の個数をそれに合わせる（検証で個数ごとの展開を試すため）"""
    slots = pattern.get("slots") if isinstance(pattern.get("slots"), dict) else {}
    out = {}
    for name, d in slots.items():
        d = d if isinstance(d, dict) else {}
        kind = d.get("kind", "text")
        ex = d.get("example")
        if kind == "text":
            out[name] = ex if isinstance(ex, str) else (str(ex) if ex is not None else (d.get("label") or name) + "の例")
        elif kind == "image":
            if isinstance(ex, str):
                out[name] = ex
            elif d.get("required"):
                out[name] = "assets/example.png"          # 必須なのに例が無いときだけ仮の名前を入れる（任意の画像スロットには補わない）
        elif kind == "flag":
            out[name] = ex if ex is not None else False
        else:
            lo = d.get("min") if isinstance(d.get("min"), int) else 1
            hi = d.get("max") if isinstance(d.get("max"), int) else max(lo, 3)
            if count is not None:
                n = count
            elif isinstance(ex, list) and ex:
                n = len(ex)               # example の個数をそのまま使う（取り込んだ型は元の個数を再現する）
            else:
                n = max(lo, min(hi, 3))
            if kind == "list":
                base = ex if isinstance(ex, list) and ex else [f"{d.get('label') or name} {{k}}"]
                out[name] = [str(base[k % len(base)]).replace("{k}", str(k + 1)) for k in range(n)]
            else:
                fields = d.get("fields") or {}
                base = ex if isinstance(ex, list) and ex and all(isinstance(e, dict) for e in ex) else None
                recs = []
                for k in range(n):
                    if base:
                        rec = dict(base[k % len(base)])
                        if k >= len(base):          # 例の個数を超えて繰り返す項目では、「1 つだけ」の印（at_most）を外す
                            for f, fd in fields.items():
                                if isinstance(fd, dict) and fd.get("at_most") is not None and f in rec:
                                    rec[f] = False if fd.get("kind") == "flag" else ""
                        recs.append(rec)
                    else:
                        recs.append({f: _field_example(f, fd, k) for f, fd in fields.items()})
                out[name] = recs
    return {"type": "pattern", "pattern": pattern.get("name", ""), "slots": out}


def _check_values_def(where, d, errs):
    """"values": {"done": ["済", "完了"], "todo": [""]}（正規の値 → 別名の配列）の形"""
    if "at_most" in d:
        am = d["at_most"]
        if not (isinstance(am, int) and not isinstance(am, bool) and am >= 0):
            errs.append(f"{where}.at_most は 0 以上の整数にしてください（真・書いてある項目の数の上限。例: 現在地は 1）")
        elif d.get("kind", "text") not in ("flag", "text"):
            errs.append(f"{where}.at_most は kind が flag（真の数）か text（書いてある数）の項目だけに書けます")
        elif "." not in where.replace("slots.", "", 1):
            errs.append(f"{where}.at_most は records の項目（fields の中）に書いてください")
    if "unknown_as" in d and not (isinstance(d["unknown_as"], str) and isinstance(d.get("values"), dict) and d["unknown_as"] in d["values"]):
        errs.append(f"{where}.unknown_as は values の正規の値のどれか（候補にない値をこの値として描く。例: \"todo\"）にしてください")
    if "values" not in d:
        return
    vals = d["values"]
    if d.get("kind", "text") != "text":
        errs.append(f'{where}.values は kind が text のスロット・項目だけに書けます（値の候補と別名: {{"done": ["済", "完了"], "todo": [""]}}）')
        return
    if not (isinstance(vals, dict) and vals and all(isinstance(k, str) and k and isinstance(a, list)
                                                    and all(isinstance(x, (str, int, float, bool)) for x in a) for k, a in vals.items())):
        errs.append(f'{where}.values は 正規の値 → 別名の配列 の形にしてください（例: {{"done": ["済", "完了"], "wip": ["中"], "todo": [""]}}）')


def check_pattern(pat, theme=None, quick=False):
    """パターン JSON 自体の検証。戻り値 (errors, warnings)。
    型違いの値（辞書・配列をキーや集合の要素にする欄など）で検査自体が落ちたときは、トレースバックにせず
    「どの欄を見直すか」のエラー 1 件にして返す（_check_pattern_impl の先頭の構造検査で拾いきれなかった分の保険）"""
    try:
        return _check_pattern_impl(pat, theme, quick)
    except (TypeError, AttributeError, KeyError, ValueError) as e:
        where = ""
        tb = e.__traceback__
        while tb is not None and tb.tb_next is not None:
            tb = tb.tb_next
        if tb is not None:
            where = f"（検査の {tb.tb_frame.f_code.co_name} で発生）"
        return ([f"パターンの構造を検査できません: {type(e).__name__}: {str(e)[:120]}{where} → "
                 "slots・elements・variants・narrow の各欄の型を見直してください"
                 "（名前・個数・種別は文字列か整数、slots / fields / values はオブジェクト、elements は配列。"
                 "配列やオブジェクトを名前や種別の位置に書いていないか確認してください）"], [])


def _check_pattern_impl(pat, theme=None, quick=False):
    """パターン JSON 自体の検証。戻り値 (errors, warnings)。
    構造（slots・elements・repeat・変数の参照）を調べ、例の値で展開して canvas の検証に通す（quick=True のときは展開を 1 回に省く）"""
    errs, warns = [], []
    if not isinstance(pat, dict):
        return ["パターンはオブジェクトである必要があります"], warns
    name = pat.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        errs.append('name は英数字・日本語・- _ の 1〜64 文字で指定してください（例: "conclusion-evidence"）')
    path = pat.get("_path")
    if path and isinstance(name, str) and Path(path).stem != name:
        warns.append(f"name '{name}' とファイル名 '{Path(path).stem}.json' が違います → スライドの pattern には「ファイル名」を書きます。揃えてください")
    fr = pat.get("frame", "full")
    if fr not in FRAMES:
        errs.append(f'frame "{fr}" は "full"（全面）か "body"（本文領域だけ）のどちらかです')
    elif fr == "body":
        sz = pat.get("size")
        if sz is not None and not (isinstance(sz, list) and len(sz) == 2 and all(_pos(v) for v in sz)):
            errs.append('size は [幅, 高さ]（正の数 2 つ。例: [1136, 480]）で指定してください')
        if pat.get("valign") not in (None, "top", "middle"):
            errs.append('valign は "top"（上寄せ。既定）か "middle"（本文領域の縦中央）です')
        for sname in ("title", "lead", "eyebrow"):
            if sname in (pat.get("slots") or {}):
                warns.append(f"frame が body なのにスロット '{sname}' があります → 見出し・リード・小見出しはスライド直下の title / lead / eyebrow が描くので、"
                             "型のスロットには不要です（二重に出ます）")
    elif "size" in pat:
        warns.append('size は frame が "body" のときだけ使います（full は 1280x720 全面）')
    if "min_width" in pat and not _pos(pat["min_width"]):
        errs.append('min_width は正の数（px。設計寸法を写したあとの実際の幅の下限。例: 800）で指定してください')
    elif "min_width" in pat and fr != "body":
        warns.append('min_width は frame が "body" の型だけで使います（合成スライドのブロックや狭い本文領域に置く型の下限）')
    nr_raw = pat.get("narrow")
    if "block_alt" in pat and not (isinstance(pat["block_alt"], str) and pat["block_alt"].strip()):
        errs.append('block_alt は文字列（幅が足りないときの代わりの手。例: "代わりに numbered-list を使う"）で指定してください')
    if nr_raw is not None:
        if fr != "body":
            errs.append('narrow（狭いとき用の構図）は frame が "body" の型だけで使えます')
        else:
            nr_items = nr_raw if isinstance(nr_raw, list) else [nr_raw]
            if not nr_items:
                errs.append('narrow は {"below": 700, "size": [560, 360], "elements": [...]}（below = この幅 px 未満で使う。正の数）の形（またはその配列）にしてください')
            belows = []
            for ni, nr in enumerate(nr_items):
                nloc = f"narrow[{ni}]" if isinstance(nr_raw, list) else "narrow"
                if not (isinstance(nr, dict) and _below(nr) and isinstance(nr.get("elements"), list)):
                    errs.append(f'{nloc} は {{"below": 700, "size": [560, 360], "elements": [...]}}（below = この幅 px 未満で使う。正の数）の形にしてください')
                    continue
                if "below_h" in nr and not _below_h(nr):
                    errs.append(f'{nloc}.below_h は正の数（px。矩形の高さがこの値未満のときだけ使う短い構図。例: 340）で指定してください')
                    continue
                belows.append((_below(nr), _below_h(nr)))
                nsz = nr.get("size")
                if not (isinstance(nsz, list) and len(nsz) == 2 and all(_pos(v) for v in nsz)):
                    errs.append(f'{nloc}.size は [幅, 高さ]（正の数 2 つ。例: [560, 360]）で指定してください')
                elif nsz[0] > _below(nr):
                    warns.append(f"{nloc}.size の幅 {nsz[0]} が below {_below(nr)} より広いです → 狭い構図は below 未満の幅に置くので、size の幅は below 以下にしてください")
                if "no_max_width" in nr and not (nr["no_max_width"] is True and _below_h(nr)):
                    errs.append(f'{nloc}.no_max_width は true（below_h とセットで、幅の上限を外す）で指定してください')
                if "max_stretch" in nr and not (_pos(nr["max_stretch"]) and nr["max_stretch"] >= 1):
                    errs.append(f'{nloc}.max_stretch は 1 以上の数（この構図を横に広げてよい倍率の上限。既定 {NARROW_STRETCH_MAX}）で指定してください')
                if "min_width" in nr and not _pos(nr["min_width"]):
                    errs.append(f'{nloc}.min_width は正の数（px。この構図が読める矩形の幅の下限。例: 440）で指定してください')
                mwc = nr.get("min_width_by_count")
                if "min_width_by_count" in nr and not (isinstance(mwc, dict) and all(str(k_).isdigit() and _pos(v_) for k_, v_ in mwc.items())):
                    errs.append(f'{nloc}.min_width_by_count は {{"4": 700}}（個数の数字 → その個数で読める矩形の幅の下限 px。正の数）の形で指定してください')
                if "variants" in nr and not (isinstance(nr["variants"], dict) and (nr.get("variants_by") or pat.get("variants_by"))):
                    errs.append(f"{nloc}.variants は variants_by（個数を数えるスロット名）とセットで書いてください")
                for k_, v_ in (nr.get("variants") or {}).items() if isinstance(nr.get("variants"), dict) else []:
                    if not str(k_).isdigit() or not isinstance(v_, dict) or not isinstance(v_.get("elements"), list):
                        errs.append(f'{nloc}.variants["{k_}"] は {{"elements": [...]}} の形で、キーは個数の数字にしてください')
            if len(belows) != len(set(belows)):
                errs.append("narrow の below が重なっています → 段ごとに違う幅（例: 700 と 1000）にしてください（同じ幅の段を高さで分けるときは below_h も違う値にする）")
    nr_levels = narrow_levels(pat) if fr == "body" else []
    slots = pat.get("slots")
    if not isinstance(slots, dict) or not slots:
        errs.append('slots は {"スロット名": {"kind": "text", ...}} の形で 1 つ以上定義してください')
        slots = {}
    fields_all = set()
    for sname, d in slots.items():
        if not isinstance(sname, str) or not re.fullmatch(r"[A-Za-z_][\w]*", sname):
            errs.append(f"スロット名 '{sname}' は英数字と _ で、先頭は英字にしてください")
        if sname in BUILTIN_VARS or sname in LOOP_VARS:
            errs.append(f"スロット名 '{sname}' は組み込み変数と同じです → 別の名前にしてください")
        if not isinstance(d, dict):
            errs.append(f"slots.{sname} はオブジェクトで定義してください")
            continue
        kind = d.get("kind", "text")
        if not isinstance(kind, str):
            errs.append(f"slots.{sname}.kind は文字列で指定してください（{' / '.join(SLOT_KINDS)} のいずれか）")
        elif kind not in SLOT_KINDS:
            errs.append(f"slots.{sname}.kind '{kind}' は {' / '.join(SLOT_KINDS)} のいずれかです")
        for k in ("fields", "values"):
            if k in d and d[k] is not None and not isinstance(d[k], dict):
                errs.append(f"slots.{sname}.{k} はオブジェクトで指定してください（{'項目名 → {\"kind\": \"text\"}' if k == 'fields' else '値 → 説明'}）")
        for k in ("max_chars", "min", "max"):
            if k in d and not (isinstance(d[k], int) and not isinstance(d[k], bool) and d[k] >= 0):
                errs.append(f"slots.{sname}.{k} は 0 以上の整数にしてください")
        if kind == "records":
            f = d.get("fields")
            if f is not None and not isinstance(f, dict):
                pass        # 型違いは上の fields / values の検査で報告済み
            elif not isinstance(f, dict) or not f:
                errs.append(f"slots.{sname}.fields が必要です（records の項目名 → {{\"kind\": \"text\", \"max_chars\": 12}}）")
            else:
                fields_all.update(f)
                for fname, fd in f.items():
                    if not isinstance(fd, dict):
                        continue
                    if fd.get("kind", "text") not in FIELD_KINDS:
                        errs.append(f"slots.{sname}.fields.{fname}.kind '{fd.get('kind')}' は {' / '.join(FIELD_KINDS)} のいずれかです")
                    _check_values_def(f"slots.{sname}.fields.{fname}", fd, errs)
                    if "count_of" in fd and not (isinstance(fd["count_of"], str) and fd["count_of"] in slots):
                        errs.append(f"slots.{sname}.fields.{fname}.count_of '{fd['count_of']}' は別のスロット名にしてください（個数を合わせたい相手）")
        _check_values_def(f"slots.{sname}", d, errs)
        if "count_of" in d and not (isinstance(d["count_of"], str) and d["count_of"] in slots and d["count_of"] != sname):
            errs.append(f"slots.{sname}.count_of '{d['count_of']}' は別のスロット名にしてください（個数を合わせたい相手）")
        if "example" not in d and d.get("required"):
            warns.append(f"slots.{sname} に example がありません（show / check / 確認用デッキで使う例文です）")
    # 型違いの欄（上でエラーにした分）は、以降の検査が落ちないよう外した写しに差し替える（pat は書き換えない）
    def _safe_slot(d):
        if not isinstance(d, dict):
            return d
        d = dict(d)
        for f in ("fields", "values"):
            if f in d and not isinstance(d[f], dict):      # 項目名の配列は {項目名: {}} に読み替える（連鎖エラーを増やさない）
                d[f] = {x: {} for x in d[f] if isinstance(x, str)} if isinstance(d[f], list) else {}
        if not isinstance(d.get("kind", "text"), str):
            d["kind"] = "text"
        return d

    slots = {k: _safe_slot(d) for k, d in slots.items()}
    els = pat.get("elements")
    var = pat.get("variants")
    if not isinstance(els, list) and not isinstance(var, dict):
        errs.append("elements は canvas 要素の配列で指定してください")
    if var is not None:
        by = pat.get("variants_by")
        if not isinstance(var, dict) or not by:
            errs.append('variants を使うときは variants_by（個数を数えるスロット名）も指定してください（例: "variants_by": "cards"）')
        elif not isinstance(by, str):
            errs.append("variants_by は list / records のスロット名（文字列）にしてください（例: \"variants_by\": \"cards\"）")
        elif by not in slots or not isinstance(slots[by], dict) or slots[by].get("kind") not in ("list", "records"):
            errs.append(f"variants_by '{by}' は list か records のスロット名にしてください")
        for k, v in (var or {}).items() if isinstance(var, dict) else []:
            if not str(k).isdigit() or not isinstance(v, dict) or not isinstance(v.get("elements"), list):
                errs.append(f'variants["{k}"] は {{"elements": [...]}} の形で、キーは個数の数字にしてください')
    allowed = set(slots) | set(BUILTIN_VARS) | set(LOOP_VARS) | fields_all
    used = set()

    value_defs = {}
    for sn_, sd_ in slots.items():
        if isinstance(sd_, dict):
            if isinstance(sd_.get("values"), dict):
                value_defs[sn_] = sd_["values"]
            for fn_, fd_ in (sd_.get("fields") or {}).items() if isinstance(sd_.get("fields"), dict) else []:
                if isinstance(fd_, dict) and isinstance(fd_.get("values"), dict):
                    value_defs[fn_] = fd_["values"]

    def cond_check(c, loc):
        if isinstance(c, dict):
            unknown = [k for k in c if k not in ("slot", "is", "in", "not", "field", "any")]
            if unknown:
                errs.append(f"{loc}: if の辞書に使えないキー {unknown} があります → "
                            '{"slot": "名前", "is": "値"} / {"slot": "名前", "in": ["値1", "値2"]} / {"slot": "records名", "field": "項目名", "any": false} / {"not": 条件} のいずれかで書いてください')
            if "not" in c:
                if len(c) > 1:
                    errs.append(f'{loc}: if の "not" は単独で書いてください（{{"not": {{"slot": "名前", "is": "値"}}}}）')
                cond_check(c["not"], loc)
                return
            sl = c.get("slot")
            if not isinstance(sl, str) or not sl.strip():
                errs.append(f'{loc}: if の辞書には "slot"（スロット名）が必要です → {{"slot": "state", "is": "done"}}')
                return
            if "field" in c or "any" in c:
                sd = slots.get(sl.strip()) if isinstance(slots.get(sl.strip()), dict) else None
                fld = c.get("field")
                if not (sd and sd.get("kind") == "records" and isinstance(fld, str) and isinstance((sd.get("fields") or {}).get(fld), dict)
                        and isinstance(c.get("any", True), bool) and "is" not in c and "in" not in c):
                    errs.append(f'{loc}: 集計の if は {{"slot": "records のスロット名", "field": "その項目名", "any": false}} の形にしてください'
                                f'（any: false = 全項目で空のとき真、true = 1 項目でもあるとき真。is / in とは併用できません）')
                used.add(sl.strip())
                return
            if ("is" in c) == ("in" in c):
                errs.append(f'{loc}: if の辞書には "is"（等しい）か "in"（いずれか）のどちらか 1 つを書いてください → {{"slot": "{sl}", "is": "値"}}')
            if "in" in c and not (isinstance(c["in"], list) and c["in"]):
                errs.append(f'{loc}: if の "in" は値の配列にしてください → {{"slot": "{sl}", "in": ["値1", "値2"]}}')
            root = sl.strip().split(".")[0]
            if root not in allowed:
                errs.append(f"{loc}: if '{sl}' のスロットがありません → slots に定義してください")
            used.add(root)
            vd = value_defs.get(sl.strip().split(".")[-1])
            targets = [c["is"]] if "is" in c else (c["in"] if isinstance(c.get("in"), list) else [])
            if vd:
                for t_ in targets:
                    if isinstance(t_, (str, int, float)) and not isinstance(t_, bool) and t_ not in vd:
                        warns.append(f"{loc}: if の値 \"{t_}\" が '{sl}' の values の候補にありません → {' / '.join(map(str, vd))} のいずれかにしてください")
            return
        base = str(c).lstrip("!").strip()
        if base.startswith("@"):
            if base not in ("@first", "@last", "@odd", "@even"):
                errs.append(f"{loc}: if '{c}' は @first / @last / @odd / @even のいずれかです")
            return
        root = base.split(".")[0]
        if root not in allowed:
            errs.append(f"{loc}: if '{c}' のスロットがありません → slots に定義してください")
        used.add(root)

    def scan(obj, loc):
        if isinstance(obj, dict):
            if "repeat" in obj:
                r = obj["repeat"]
                if not isinstance(r, str) or r not in slots or not isinstance(slots[r], dict) or slots[r].get("kind") not in ("list", "records"):
                    errs.append(f"{loc}: repeat '{r}' は list か records のスロット名にしてください")
                else:
                    used.add(r)
                if "runs" not in obj and "cells" not in obj and not ("grid" in obj and "template" in obj):
                    errs.append(f"{loc}: 要素の repeat には grid と template の両方が必要です")
            if isinstance(obj.get("fit"), dict) or ("fit" in obj and "kind" not in obj and "runs" not in obj and "text" not in obj):
                fs = obj["fit"].get("sizes") if isinstance(obj["fit"], dict) else None
                if not (isinstance(fs, list) and fs and all((isinstance(s_, (int, float)) and not isinstance(s_, bool) and s_ > 0)
                                                           or (isinstance(s_, str) and s_.startswith("$")) for s_ in fs)):
                    errs.append(f'{loc}: fit は {{"sizes": [28, 24, 20, 16]}}（大きい順の正の数。"$type.h3" のトークンも可）で指定してください')
                if isinstance(obj["fit"], dict) and "group" in obj["fit"]:
                    g_ = obj["fit"]["group"]
                    if not (isinstance(g_, bool) or (isinstance(g_, str) and g_.strip())):
                        errs.append(f'{loc}: fit.group は名前（"items"）か true（同じ繰り返しの同じ位置の要素どうし）か false で指定してください')
                    elif g_ is True and ".template[" not in loc:
                        warns.append(f'{loc}: fit.group が true なのは繰り返しの template の中だけで意味があります → 名前（"items"）で書くか、template の中に移してください')
                    if ".children" in loc and g_ not in (False, None):
                        warns.append(f"{loc}: group 要素の子の fit.group は効きません（子ごとに単独で収まる大きさになります）→ group の外に出してください")
            if "if" in obj:
                for c in (obj["if"] if isinstance(obj["if"], list) else [obj["if"]]):
                    cond_check(c, loc)
            for k, v in obj.items():
                scan(v, f"{loc}.{k}")
        elif isinstance(obj, list):
            for k, v in enumerate(obj):
                scan(v, f"{loc}[{k}]")
        elif isinstance(obj, str):
            for m in _VAR_RE.finditer(obj):
                root = m.group(1).strip().split(".")[0]
                if root == "":
                    root = "."
                if root not in allowed:
                    errs.append(f"{loc}: {{{{{m.group(1).strip()}}}}} に対応するスロットがありません")
                elif "0" in m.group(1).strip().split(".")[1:]:
                    errs.append(f"{loc}: " + _missing_var_message(m.group(1)))
                used.add(root)
    scan(els if isinstance(els, list) else [], "elements")
    if isinstance(var, dict):
        for k, v in var.items():
            scan(v, f"variants[{k}]")
    nr_ok = bool(nr_levels)
    for ni, nr in enumerate(nr_levels):
        nloc = f"narrow[{ni}]" if len(nr_levels) > 1 else "narrow"
        scan(nr["elements"], f"{nloc}.elements")
        for k, v in (nr.get("variants") or {}).items() if isinstance(nr.get("variants"), dict) else []:
            scan(v, f"{nloc}.variants[{k}]")
    for sname in slots:
        if sname not in used and not (isinstance(slots[sname], dict) and slots[sname].get("kind") == "records" and
                                      any(f in used for f in (slots[sname].get("fields") or {}))):
            warns.append(f"スロット '{sname}' はどの要素からも使われていません")
    # grid で繰り返すスロットに max が無いと、個数が増えたときに枠が潰れる
    grid_slots = set()

    def find_grids(obj):
        if isinstance(obj, dict):
            if "repeat" in obj and "grid" in obj and isinstance(obj["repeat"], str):
                grid_slots.add(obj["repeat"])
            for v in obj.values():
                find_grids(v)
        elif isinstance(obj, list):
            for v in obj:
                find_grids(v)
    find_grids(els)
    if isinstance(var, dict):
        find_grids(list(var.values()))
    for nr in nr_levels:
        find_grids(nr["elements"])
        if isinstance(nr.get("variants"), dict):
            find_grids(list(nr["variants"].values()))
    for g in sorted(grid_slots):
        d = slots.get(g)
        if isinstance(d, dict) and d.get("kind") in ("list", "records") and not isinstance(d.get("max"), int):
            warns.append(f"slots.{g}.max がありません → 枠に収まる最大の個数を書いてください（超えると枠が潰れて崩れます。"
                         f"利用者に「{g} は N 個まで」と警告できるようになります）")
    # 例の値で展開し、canvas の検証に通す。構造の誤りがあっても、色・トークンの誤りは同時に出す（直す順番を待たせない）
    theme = theme or _default_theme()
    structural = bool(errs)

    def run(P, where_tag=""):
        var_ = P.get("variants")
        counts = [(None, False)]            # (個数, 上限超えの試し展開か)
        if not quick:
            for sname, d in slots.items():
                if isinstance(d, dict) and d.get("kind") in ("list", "records"):
                    counts += [(d.get("min"), False), (d.get("max"), False)]
                    if isinstance(d.get("max"), int) and sname in grid_slots:
                        counts.append((d["max"] + 1, True))   # 上限を 1 つ超えても、例外や不正な大きさ（負）にならないこと（超えた分は描かれない）
            if isinstance(var_, dict):
                counts += [(int(k), False) for k in var_ if str(k).isdigit()]
        seen = set()
        for cnt, probe in counts:
            if (cnt is not None and not isinstance(cnt, int)) or (cnt, probe) in seen:
                continue
            seen.add((cnt, probe))
            hard: list = []
            soft: list = []
            try:
                sl = example_slide(P, cnt)
                els_out, _bg = expand(sl, P, theme, {"meta": {"title": "デッキ名", "brand": "ブランド"}}, 1, 10, soft.append, hard)
            except Exception as e:  # noqa: BLE001
                if not structural:
                    errs.append(f"例の値での展開に失敗しました: {e!r}{where_tag}")
                break
            tag = (f"（{cnt} 個で展開）" if cnt is not None else "") + where_tag
            if structural:     # 構造エラーが連鎖して出す「スロットが無い」類は重複なので、色・トークンの誤りだけ足す
                errs.extend(m + tag for m in hard if m.startswith(("色 '", "トークン '")))
                continue
            errs.extend(m + tag for m in hard)
            errs.extend(m + tag for m in ce.validate_canvas_problems({"elements": els_out}, None))
            if not probe:      # 上限超えの試し展開で出る「N 個だけ描きました」警告は想定どおりなので載せない
                warns.extend(m + tag for m in soft)
            if frame_of(P) == "body" and not probe:
                sw, sh = design_size(P)
                out_of = [e.get("name") or e.get("kind", "shape") for e in ce.flatten(els_out)
                          if _num(e.get("x")) and _num(e.get("w"))
                          and (e["x"] < -0.5 or e["x"] + e["w"] > sw + 0.5
                               or (_num(e.get("y", 0)) and _num(e.get("h", 0))
                                   and (e.get("y", 0) < -0.5 or e.get("y", 0) + e.get("h", 0) > sh + 0.5)))]
                if out_of:
                    warns.append(f"frame が body の型で、設計寸法 {int(sw)}x{int(sh)} の外にはみ出す要素があります（{'、'.join(map(str, out_of[:4]))}）"
                                 f"{tag} → 要素の座標は 0〜{int(sw)} x 0〜{int(sh)} の中で書く（見出し・フッターの領域は含まない）")
    run(pat)
    if nr_ok and not quick:
        for ni, nr in enumerate(nr_levels):
            _bh = _below_h(nr)
            run(_apply_level(pat, nr), (f"（狭い構図 {ni + 1}: 幅 {int(_below(nr))}px 未満" + (f"・高さ {int(_bh)}px 未満" if _bh else "") + "）") if len(nr_levels) > 1 else "（狭い構図）")
    return list(dict.fromkeys(errs)), list(dict.fromkeys(warns))


# ---------------------------------------------------------------- CLI
def _load_theme_for_cli(name, deck_dir=None):
    try:
        import build_deck as bd  # type: ignore
        return bd.load_theme(name, bd.theme_dirs(Path(deck_dir) if deck_dir else None))
    except Exception:  # noqa: BLE001
        base = _default_theme()
        for d in ([Path(deck_dir) / "themes"] if deck_dir else []) + [ROOT / "templates" / "themes"]:
            f = d / f"{name}.json"
            if f.is_file():
                t = json.loads(f.read_text(encoding="utf-8"))
                return {**base, **t, "colors": {**base.get("colors", {}), **t.get("colors", {})},
                        "fonts": {**base.get("fonts", {}), **t.get("fonts", {})}}
        return base


def _wcols(text: str) -> int:
    """端末での表示幅（全角 2 桁）"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _wcols(text))


def _count_range(pat):
    """型の個数の幅の要約 (スロットの表示名, min, max)。variants_by のスロット、無ければ最初の list / records のスロット。無ければ None"""
    slots = pat.get("slots") if isinstance(pat.get("slots"), dict) else {}
    by = pat.get("variants_by")
    cands = [by] if by in slots else []
    cands += [k for k, d in slots.items() if isinstance(d, dict) and d.get("kind") in ("list", "records")]
    for k in cands:
        d = slots[k]
        if isinstance(d, dict) and d.get("kind") in ("list", "records") and (d.get("min") is not None or d.get("max") is not None):
            return d.get("label") or k, d.get("min", 0), d.get("max")
    return None


def _scale_limit_width(pat) -> int:
    """narrow も min_width も持たない型で、合成ブロックの縮小率の下限（BLOCK_MIN_BODY_SCALE）に当たる幅（10px 単位に切り上げ）"""
    sw, _sh = design_size(pat)
    return int(math.ceil(sw * BLOCK_MIN_BODY_SCALE / 10.0) * 10)


HALF_WIDTH = 560       # 合成スライドの半幅のブロックの幅の目安（約 556px。split の ratio 0.5 は約 512px）
TWO_THIRDS_WIDTH = 745  # 3 分の 2 幅のブロックの幅の目安（約 741px）


def max_floor(pat):
    """個数を問わず読める幅の下限（個数別の下限のうち最大、無ければ narrow_floor）。狭い構図の無い型は min_width。無ければ None"""
    fl = narrow_floor(pat)
    cf = count_floors(pat)
    vals = [v for v in [fl] + list(cf.values()) if v]
    return max(vals) if vals else None


def block_class(pat):
    """型を合成スライドのブロックに置けるか。(記号, 一覧の「ブロック」列の文)。
    ◎ = 全個数で半幅（約 556px）から読める / ○ = 3 分の 2 幅（約 741px）から読める / △ = それより広い幅が要る / × = 置けない"""
    if frame_of(pat) != "body":
        return "×", "×"
    if narrow_levels(pat):
        mx = max_floor(pat)
        if not mx:
            return "◎", "◎ 半幅可"
        n = int(math.ceil(mx / 10.0) * 10)
        if mx <= HALF_WIDTH:
            return "◎", f"◎ 半幅可 {n}px〜"
        if mx <= TWO_THIRDS_WIDTH:
            return "○", f"○ 3分の2幅可 {n}px〜"
        return "△", f"△ {n}px〜"
    if min_width_of(pat):
        return "△", f"△ {int(min_width_of(pat))}px〜"
    return "△", f"△ 約{_scale_limit_width(pat)}px〜"


def block_note(pat) -> str:
    """合成スライドのブロックに置けるか（1 行）"""
    if frame_of(pat) != "body":
        return "置けない（全面の型。合成スライドのブロックにはできない）"
    mw = min_width_of(pat)
    lv = base_levels(pat)
    if narrow_levels(pat):
        fl = narrow_floor(pat)
        top = int(_below(lv[-1])) if lv else int(_below(narrow_levels(pat)[-1]))
        cf = count_floors(pat)
        mx = max_floor(pat)
        base = f"幅 {int(fl)}px 以上のブロックに置ける" if fl else "置ける"
        extra = ("（" + "・".join(f"{k} 個のときは {int(v)}px 以上" for k, v in sorted(cf.items())) + "）") if cf else ""
        if mx and mx > TWO_THIRDS_WIDTH:
            read = "幅が足りないと警告が出る"
        elif mx and mx > HALF_WIDTH:
            read = "3 分の 2 幅でも読める。半幅は個数が少ないときだけ"
        else:
            read = "半幅・3 分の 2 幅でも読める"
        short = [x for x in narrow_levels(pat) if _below_h(x)]
        sh_note = f"。高さ {int(max(_below_h(x) for x in short))}px 未満は短い構図に切り替わる" if short else ""
        return f"{base}{extra}（{read}。幅 {top}px 未満は狭い構図に切り替わる{sh_note}）"
    if mw:
        return f"幅 {int(mw)}px 以上のブロックに置ける（半幅のブロックには向かない）"
    lim = _scale_limit_width(pat)
    return (f"幅およそ {lim}px 以上のブロックに置ける（それより狭いと縮小率が {int(BLOCK_MIN_BODY_SCALE * 100)}% を割って警告が出る。"
            f"半幅（556px）では縮小率が約 {int(556 / design_size(pat)[0] * 100)}% になり、文字が小さくなりすぎて不向き）")


def _value_line(vals) -> str:
    return " / ".join(f"{k}（{'・'.join(str(a) for a in al if a not in ('', None))}）" if isinstance(al, list) and any(a not in ("", None) for a in al)
                      else str(k) for k, al in vals.items())


def _slot_table(pat):
    lines = []
    for name, d in (pat.get("slots") or {}).items():
        d = d if isinstance(d, dict) else {}
        kind = d.get("kind", "text")
        bits = [kind]
        if d.get("required"):
            bits.append("必須")
        if d.get("max_chars"):
            bits.append(f"{d['max_chars']}字まで")
        if d.get("min") is not None or d.get("max") is not None:
            bits.append(f"{d.get('min', 0)}〜{d.get('max', '')}個")
        if d.get("default"):
            bits.append(f"省略時: {d['default']}")
        lines.append(f"    {name:<14}{' / '.join(bits)}  {d.get('label', '')}")
        if d.get("description"):
            lines.append(f"      説明: {d['description']}")
        if isinstance(d.get("values"), dict):
            lines.append(f"      値の候補: {_value_line(d['values'])}")
        if d.get("count_of"):
            lines.append(f"      個数: スロット '{d['count_of']}' と同じ数にそろえる")
        if kind == "records":
            for f, fd in (d.get("fields") or {}).items():
                fd = fd if isinstance(fd, dict) else {}
                fb = [fd.get("kind", "text")]
                if fd.get("required"):
                    fb.append("必須")
                if fd.get("max_chars"):
                    fb.append(f"{fd['max_chars']}字まで")
                lines.append(f"      .{f:<12}{' / '.join(fb)}" + (f"  {fd['label']}" if fd.get("label") else ""))
                if fd.get("description"):
                    lines.append(f"        説明: {fd['description']}")
                if isinstance(fd.get("values"), dict):
                    lines.append(f"        値の候補: {_value_line(fd['values'])}")
                if fd.get("count_of"):
                    lines.append(f"        個数: スロット '{fd['count_of']}' と同じ数にそろえる")
    return lines


def _frame_line(pat) -> str:
    if frame_of(pat) == "body":
        sw, sh = design_size(pat)
        return f"枠: body（見出し・フッターはスライド側。本文だけ描く。設計寸法 {int(sw)}x{int(sh)}。スライドに title / lead を書く）"
    return "枠: full（1280x720 全面。見出し・フッターも型の中にある）"


def summary_of(pat) -> str:
    """list に出す 1 行の説明。型の "summary"、無ければ description の最初の文"""
    sm = pat.get("summary")
    if isinstance(sm, str) and sm.strip():
        return sm.strip()
    return str(pat.get("description") or "").split("。")[0][:60]


def _cmd_list(args):
    rows = list_patterns(args.deck)
    if not rows:
        print("パターンが見つかりません（探した場所）:")
        for d in pattern_dirs(args.deck):
            print(f"  {d}")
        return 0
    if getattr(args, "detail", False):
        for name, path, pat, err in rows:
            if err:
                print(f"{name}\n    読み込みエラー: {err}")
                continue
            print(f"{name}  — {pat.get('label', '')}\n    {pat.get('description', '')}\n    {_frame_line(pat)}\n    ({path})")
            print("\n".join(_slot_table(pat)))
        return 0
    print(f"使えるパターン {len(rows)} 個（詳しい書き方は: pattern_engine.py show <名前>）\n")
    head = ("名前", "枠", "個数", "ブロック", "何を言うときに使うか")
    table = []
    for name, path, pat, err in rows:
        if err:
            table.append((name, "?", "", "", f"読み込みエラー: {err}"))
            continue
        cr = _count_range(pat)
        cnt = f"{cr[1]}〜{cr[2]}" if cr and cr[2] is not None else (f"{cr[1]}〜" if cr else "-")
        blk = block_class(pat)[1]
        table.append((name, frame_of(pat), cnt, blk, summary_of(pat)))
    widths = [max(_wcols(r[i]) for r in [head] + table) for i in range(4)]
    for r in [head] + table:
        print("  ".join(_pad(r[i], widths[i]) for i in range(4)) + "  " + r[4])
    print("\n枠: full = 1280x720 全面 / body = 本文だけ（見出しはスライド側）。ブロック = 合成スライド（type=composite）・split の本文側に置けるか"
          "（◎ 半幅（約 556px）から読める / ○ 3 分の 2 幅（約 741px）から読める / △ それより広い幅が要る。px〜 は全個数で読める幅の下限（個数ごとの下限は show に出る）。"
          "下限より狭いと警告が出る / × 置けない）")
    return 0


def show_example_slide(pat) -> dict:
    """show に出す「そのまま貼れる deck.json のスライド」。body 枠は title（と任意の lead / conclusion / source）を含める。
    型の "example_page"（{"title": …, "lead": …, "conclusion": …, "source": …}）があればその文、無ければ仮の文"""
    sl = example_slide(pat)
    # 任意の画像スロットは例から外す: 例の画像（型の隣の assets/）は利用者のデッキに無く、貼るとビルドが止まるため。
    # 画像を使うときの手順は show の末尾に出す（_cmd_show）
    slots_def = pat.get("slots") if isinstance(pat.get("slots"), dict) else {}
    for nm, d in slots_def.items():
        if isinstance(d, dict) and d.get("kind") == "image" and not d.get("required"):
            sl["slots"].pop(nm, None)
    if frame_of(pat) != "body":
        return sl
    ep = pat.get("example_page") if isinstance(pat.get("example_page"), dict) else {}
    out = {"type": "pattern", "pattern": pat.get("name", "")}
    out["title"] = ep.get("title") if isinstance(ep.get("title"), str) else f"{pat.get('label') or pat.get('name')}で言いたい結論を、一文で言い切る"
    out["lead"] = ep.get("lead") if isinstance(ep.get("lead"), str) else "見出しの補足（なくてもよい）"
    out["slots"] = sl["slots"]
    out["conclusion"] = ep.get("conclusion") if isinstance(ep.get("conclusion"), str) else "このページの結論を一文で（なくてもよい）"
    out["source"] = ep.get("source") if isinstance(ep.get("source"), str) else "出典: ○○調査 2026（なくてもよい）"
    return out


def _cmd_show(args):
    try:
        pat = load_pattern(args.name, args.deck)
    except PatternError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if pat is None:
        print(f"error: パターン '{args.name}' が見つかりません（使えるパターン: {', '.join(available_names(args.deck))}）", file=sys.stderr)
        return 1
    print(f"{pat.get('name')}  — {pat.get('label', '')}\n{pat.get('description', '')}\n{_frame_line(pat)}")
    mw = narrow_floor(pat)
    cf = count_floors(pat)
    print((f"幅の下限: {int(mw)}px（これより狭い本文領域・ブロックでは警告）" if mw else "幅の下限: なし")
          + (("。個数別: " + "・".join(f"{k} 個 {int(v)}px" for k, v in sorted(cf.items()))) if cf else ""))
    lv = narrow_levels(pat)
    if lv:
        def _sz(x):
            sz = x.get("size")
            return f"{int(sz[0])}x{int(sz[1])}" if isinstance(sz, list) and len(sz) == 2 and all(_pos(v) for v in sz) else "?"
        parts = []
        for x in lv:
            bh = _below_h(x)
            parts.append(f"{int(_below(x))}px 未満" + (f"かつ高さ {int(bh)}px 未満" if bh else "") + f" = 狭い構図（設計 {_sz(x)}）")
        top = max(_below(x) for x in lv)
        print("幅ごとの構図: " + " / ".join(parts) + f" / {int(top)}px 以上 = 広い構図（設計 {int(design_size(pat)[0])}x{int(design_size(pat)[1])}）")
    print(f"合成スライドのブロック: {block_note(pat)}")
    cr = _count_range(pat)
    if cr:
        print(f"個数: {cr[0]} は {cr[1]}〜{cr[2] if cr[2] is not None else ''} 個")
    print(f"場所: {pat.get('_path')}\n\nスロット:")
    print("\n".join(_slot_table(pat)))
    print("\nスライドの書き方（例の値つき。そのまま deck.json の slides に貼れる）:")
    print(json.dumps(show_example_slide(pat), ensure_ascii=False, indent=2))
    imgs = [(n, d) for n, d in (pat.get("slots") or {}).items() if isinstance(d, dict) and d.get("kind") == "image"]
    if imgs:
        adir = Path(pat["_path"]).parent / "assets" if pat.get("_path") else None
        for n, d in imgs:
            opt = not d.get("required")
            ex = d.get("example") if isinstance(d.get("example"), str) else "assets/photo.png"
            print(f"\n画像スロット '{n}'（{d.get('label') or n}）: " + ("省略可。上の例は画像なしの構図。" if opt else "必須。")
                  + f"画像を使うときは slots に \"{n}\": \"{ex}\" の行を足し、"
                  + "画像ファイルをデッキの assets/ に置いてください（パスはデッキのフォルダからの相対）。"
                  + (f"例の画像は {adir} にあります。" if adir else ""))
    if frame_of(pat) == "body":
        print("\ntitle は必須級（無いと警告）。lead / conclusion / source は任意（要らなければ消す。結論帯・出典を付けると本文領域が低くなり、型は全体が縮む）。")
    return 0


def _cmd_check(args):
    f = Path(args.file)
    try:
        pat = _read_pattern_file(f)
    except PatternError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    errs, warns = check_pattern(pat, _load_theme_for_cli(args.theme))
    for m in warns:
        print(f"warn: {m}")
    for m in errs:
        print(f"error: {m}")
    print(f"{f.name}: エラー {len(errs)} 件 / 警告 {len(warns)} 件")
    return 1 if errs else 0


def _cmd_sample(args):
    try:
        pat = load_pattern(args.name, args.deck)
    except PatternError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if pat is None:
        print(f"error: パターン '{args.name}' が見つかりません", file=sys.stderr)
        return 1
    out = Path(args.out)
    problem = _preview_out_problem(out, getattr(args, "force", False))
    if problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1
    slides = []
    themes = args.theme or ["default"]
    counts = [None]
    for sname, d in (pat.get("slots") or {}).items():
        if isinstance(d, dict) and d.get("kind") in ("list", "records"):
            counts = [d.get("min") if isinstance(d.get("min"), int) else None, d.get("max") if isinstance(d.get("max"), int) else None]
            break
    counts = list(dict.fromkeys(counts))
    body = frame_of(pat) == "body"
    if body:
        # frame:"body" の型は設計寸法の座標なので、全面 canvas に展開しても別物になる。見出し骨格つきの type:"pattern" スライドを出し、
        # ビルドに任せる（型 JSON は出力先の patterns/ に写して、デッキ単体でビルドできるようにする）。1 デッキ 1 テーマ
        if len(themes) > 1:
            print(f"warn: frame:body の型は 1 つのデッキで 1 テーマしか使えないため、最初のテーマ '{themes[0]}' だけで作ります"
                  " → ほかのテーマは --theme を変えて別の --out に作ってください", file=sys.stderr)
            themes = themes[:1]
    for tname in themes:
        theme = _load_theme_for_cli(tname, args.deck)
        for cnt in counts:
            sl = example_slide(pat, cnt)
            label = f"{pat.get('name')} / {tname}" + (f" / {cnt}個" if cnt else "")
            if body:
                sl["eyebrow"] = f"PATTERN  {pat.get('name')}"
                sl["title"] = label
                sl["lead"] = str(pat.get("description") or "").split("。")[0][:60]
                slides.append(sl)
                continue
            slides.append(to_canvas_slide(sl, pat, theme, {"meta": {"title": "確認用デッキ", "brand": "BRAND"}}, len(slides) + 1,
                                          len(themes) * len(counts), lambda m: print("warn:", m), []))
            slides[-1]["title"] = label
    out.mkdir(parents=True, exist_ok=True)
    if body and pat.get("_path"):
        (out / "patterns").mkdir(exist_ok=True)
        shutil.copyfile(pat["_path"], out / "patterns" / f"{pat.get('name')}.json")
    deck = {"meta": {"id": out.name, "title": f"パターン {pat.get('name')} の確認用", "theme": themes[0]}, "slides": slides}
    (out / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
    _copy_preview_assets(deck, args.deck, out)
    print(f"{out / 'deck.json'}（{len(slides)} 枚）" + ("。frame:body の型なので type:pattern のスライドで出しました（build_deck でビルドしてください）" if body else ""))
    return 0


PREVIEW_TITLE = "パターン一覧（確認用）"


def _where(path, deck_dir=None) -> str:
    """notes に書く「場所」。ローカルの絶対パス（ユーザー名やフォルダ構成）を共有物に残さない相対表記にする"""
    try:
        p = Path(path).resolve()
        if p.parent == deck_paths.bundled_dir("patterns").resolve():
            return "同梱"
        if deck_dir:
            base = Path(deck_dir).resolve()
            if p.is_relative_to(base):
                return str(p.relative_to(base))
    except (OSError, ValueError):
        pass
    return f"{Path(path).parent.name}/{Path(path).name}"


def example_image_source(pat, rel, deck_dir=None):
    """型の例の画像（image スロットの example。デッキからの相対パス "assets/sample-portrait.png"）の実体。
    デッキに同じパスの画像があればそれ、無ければ同梱の型の隣（templates/patterns/assets/）の画像。使えなければ None"""
    if not isinstance(rel, str) or not rel:
        return None
    bases = ([Path(deck_dir)] if deck_dir else []) + ([Path(pat["_path"]).parent] if pat.get("_path") else [])
    for base in bases:
        if ce.check_image_path(rel, base) is None:
            return (base / rel).resolve()
    return None


def _image_slot_paths(pat, slots):
    """型の画像スロット（kind: image）ごとの [(スロット名, 値)]"""
    out = []
    for name, d in (pat.get("slots") or {}).items():
        if isinstance(d, dict) and d.get("kind") == "image" and isinstance((slots or {}).get(name), str):
            out.append((name, slots[name]))
    return out


def preview_deck(deck_dir=None, theme="default"):
    """探索先にある全パターンを、スロットの例（example）で 1 枚ずつ並べた確認用デッキ dict を返す。
    利用者が型を登録した後に「いま何が使えるか」を一覧するための道具。frame:"body" の型は見出し・リードを付け、
    frame:"full" の型は型自身が見出しを描く。どちらもスライドの notes にパターン名と枠を書く（HTML の発表者ノートで見える）。
    画像スロットの example が実在しない型は、そのスライドだけ外して errors に理由を返す（1 つの型の不備で全体の確認を止めない）。
    deck_dir を渡すと、example の画像は deck_dir 基準で調べる（ビルド時は _cmd_preview が必要な画像だけ出力先へ写す）"""
    slides, errors = [], []
    for name, path, pat, err in list_patterns(deck_dir):
        if err:
            errors.append(f"{name}: {err}")
            continue
        sl = example_slide(pat)
        missing = []
        for sname, rel in _image_slot_paths(pat, sl.get("slots")):
            if example_image_source(pat, rel, deck_dir) is None:
                msg = ce.check_image_path(rel, Path(pat["_path"]).parent if pat.get("_path") else deck_dir) or "画像ファイルが見つかりません"
                missing.append(f"スロット '{sname}' の example '{rel}' が使えません（{msg}）")
        if missing:
            errors.append(f"{name}: {'; '.join(missing)} → スロットの example を実在する画像のパス（デッキの assets/ 配下）にすると確認用に並びます")
            continue
        label = pat.get("label") or name
        if frame_of(pat) == "body":
            sl["eyebrow"] = f"PATTERN  {name}"
            sl["title"] = f"{label}（{name}）"
            sl["lead"] = str(pat.get("description") or "").split("。")[0][:60]
        else:
            sl["title"] = f"{label}（{name}）"          # 全面の型は見出しを自分で描く。title は読み上げ用
        sl["notes"] = f"パターン名: {name} / 枠: {frame_of(pat)} / 場所: {_where(path, deck_dir)}"
        slides.append(sl)
    deck = {"meta": {"id": "pattern-preview", "title": PREVIEW_TITLE, "theme": theme or "default",
                     "author": ""},
            "slides": slides}
    return deck, errors


def _copy_preview_assets(deck, deck_dir, out):
    """確認用デッキが使う画像（example の deck 相対パス）を、デッキ（deck_dir）または同梱の型の隣（templates/patterns/assets/）から出力先へ写す。
    シンボリックリンクはデッキ外を指すとして画像検査が弾くので、実ファイルを写す（必要な画像だけ）。戻り値: 写したファイル数"""
    n = 0
    for sl in deck.get("slides", []):
        pat = load_pattern(sl.get("pattern"), deck_dir)
        if pat is None:
            continue
        for _name, rel in _image_slot_paths(pat, sl.get("slots")):
            src = example_image_source(pat, rel, deck_dir)
            dst = (Path(out) / rel).resolve()
            if src is None or src == dst or not src.is_file():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            n += 1
    return n


def _preview_out_problem(out, force) -> str | None:
    """出力先に既存の（確認用ではない）deck.json があれば上書きを止める理由を返す。--out にデッキ自身を指す打ち間違いを防ぐ"""
    f = out / "deck.json"
    if force or not f.exists():
        return None
    try:
        meta = (json.loads(f.read_text(encoding="utf-8")) or {}).get("meta") or {}
        title = str(meta.get("title") or "") if isinstance(meta, dict) else ""
        if title == PREVIEW_TITLE or re.fullmatch(r"パターン \S+ の確認用", title):
            return None                       # 前回の確認用デッキ。作り直してよい
    except (OSError, ValueError, AttributeError):
        pass
    return (f"出力先 {out} に確認用ではない deck.json があります。上書きすると元のデッキが失われます"
            f" → --out を別のフォルダ（例: {out / 'build' / 'pattern-preview'}）にしてください（本当に上書きするなら --force）")


def _cmd_preview(args):
    import subprocess
    if args.deck and not Path(args.deck).is_dir():
        print(f"error: --deck のフォルダが見つかりません: {args.deck} → デッキのフォルダ（deck.json があるところ）を指定してください", file=sys.stderr)
        return 1
    deck, errors = preview_deck(args.deck, args.theme)
    for m in errors:
        print(f"warn: 読み込めないパターンを飛ばしました — {m}", file=sys.stderr)
    if not deck["slides"]:
        print("error: 使えるパターンが見つかりません", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else Path(args.deck or ".") / "build" / "pattern-preview"
    problem = _preview_out_problem(out, args.force)
    if problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    deck["meta"]["id"] = out.resolve().name
    (out / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
    _copy_preview_assets(deck, args.deck, out)
    # 確認用デッキはデッキの patterns/ の外に出力されるので、探索先を環境変数で引き継ぐ
    env = dict(os.environ)
    env["SLIDE_DECK_PATTERNS"] = os.pathsep.join(str(d) for d in pattern_dirs(args.deck) if d.is_dir())
    if args.deck:
        env.setdefault("SLIDE_DECK_THEMES", str(Path(args.deck) / "themes"))
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "build_deck.py"), str(out)] + (["--html"] if args.html_only else []),
                       env=env)
    if r.returncode != 0:
        print(f"error: 確認用デッキのビルドに失敗しました（{out / 'deck.json'}）", file=sys.stderr)
        return r.returncode
    print(f"{out / 'deck.json'}（{len(deck['slides'])} 枚。パターン名は各スライドの notes に書いてあります）")
    return 0


def main(argv=None):
    import argparse
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="パターン（構図の型）の一覧・確認・検証")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list", help="使えるパターンの一覧（名前・枠・個数の幅・ブロック可否・何を言うときに使うか）")
    a.add_argument("--deck", help="デッキフォルダ（<deck>/patterns/ も探す）")
    a.add_argument("--detail", action="store_true", help="スロットまで全部出す（既定は 1 型 1 行の表）")
    a.set_defaults(fn=_cmd_list)
    a = sub.add_parser("show", help="パターンの詳細と、スライドの書き方の例")
    a.add_argument("name")
    a.add_argument("--deck")
    a.set_defaults(fn=_cmd_show)
    a = sub.add_parser("check", help="パターン JSON ファイルの検証（例の値で展開して canvas の検証まで通す）")
    a.add_argument("file")
    a.add_argument("--theme", default="default")
    a.set_defaults(fn=_cmd_check)
    a = sub.add_parser("sample", help="例の値で展開した確認用デッキ（canvas スライド）を作る")
    a.add_argument("name")
    a.add_argument("--out", required=True, help="出力先のデッキフォルダ")
    a.add_argument("--theme", nargs="*", help="展開するテーマ（複数可）")
    a.add_argument("--deck")
    a.add_argument("--force", action="store_true", help="出力先に確認用ではない deck.json があっても上書きする（既定は止める）")
    a.set_defaults(fn=_cmd_sample)
    a = sub.add_parser("preview", help="探索先の全パターンを例文で 1 枚ずつ並べた確認用デッキを作ってビルドする")
    a.add_argument("--deck", help="デッキフォルダ（<deck>/patterns/ と <deck>/themes/ も探す）")
    a.add_argument("--theme", default="default", help="確認に使うテーマ（既定 default）")
    a.add_argument("--out", help="出力先フォルダ（既定: <deck または .>/build/pattern-preview）")
    a.add_argument("--html", dest="html_only", action="store_true", help="HTML だけ作る（PPTX を省く）")
    a.add_argument("--force", action="store_true", help="出力先に確認用ではない deck.json があっても上書きする（既定は止める）")
    a.set_defaults(fn=_cmd_preview)
    args = ap.parse_args(argv)
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""和文テキストの計測と改行位置の調整（build_deck / lint から使う共通モジュール）。

- 字幅の実測: テーマのフォント（fonts.body / heading）のフォントファイルを Pillow で開き、
  1 文字ずつ幅を測る（キャッシュ付き）。Pillow かフォントファイルが無い環境では
  従来の近似（全角 1.0 / 半角 0.55）に戻るので、結果は今までと同じになる。
- 折り返しの模擬: 英単語は途中で切らない・行頭禁則文字は前の行に残す、というブラウザ／
  PowerPoint の挙動に寄せて行に分ける（estimate_lines の精度を上げる）。
- 泣き別れ対策: 折り返した最終行が 1〜2 文字だけになる文に、文節の切れ目で改行（\\n）を入れる。

Pillow は任意依存（setup_deps.py --pillow）。
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# フォントファイルの解決
# ---------------------------------------------------------------------------

_WIN_FONTS = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
_MAC_DIRS = [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]

# フォント名 → (通常, 太字) の候補。各候補は (ファイル名, ttc 内の index)
_KNOWN_FONTS = {
    "meiryo ui": ([("meiryo.ttc", 2)], [("meiryob.ttc", 2)]),
    "meiryo": ([("meiryo.ttc", 0)], [("meiryob.ttc", 0)]),
    "メイリオ": ([("meiryo.ttc", 0)], [("meiryob.ttc", 0)]),
    "yu gothic ui": ([("YuGothR.ttc", 1)], [("YuGothB.ttc", 1)]),
    "yu gothic": ([("YuGothM.ttc", 0), ("YuGothR.ttc", 0)], [("YuGothB.ttc", 0)]),
    "游ゴシック": ([("YuGothM.ttc", 0), ("YuGothR.ttc", 0)], [("YuGothB.ttc", 0)]),
    "biz udpgothic": ([("BIZ-UDGothicR.ttc", 1)], [("BIZ-UDGothicB.ttc", 1)]),
    "biz udgothic": ([("BIZ-UDGothicR.ttc", 0)], [("BIZ-UDGothicB.ttc", 0)]),
    "ms pgothic": ([("msgothic.ttc", 1)], []),
    "ms gothic": ([("msgothic.ttc", 0)], []),
    "hiragino sans": ([("ヒラギノ角ゴシック W3.ttc", 0)], [("ヒラギノ角ゴシック W6.ttc", 0)]),
    "hiragino kaku gothic pron": ([("ヒラギノ角ゴシック W3.ttc", 0)], [("ヒラギノ角ゴシック W6.ttc", 0)]),
    "ヒラギノ角ゴシック": ([("ヒラギノ角ゴシック W3.ttc", 0)], [("ヒラギノ角ゴシック W6.ttc", 0)]),
    "consolas": ([("consola.ttf", 0)], [("consolab.ttf", 0)]),
    "arial": ([("arial.ttf", 0)], [("arialbd.ttf", 0)]),
}

_font_cache: dict = {}
_em_cache: dict = {}


def _font_dirs():
    if platform.system() == "Windows":
        return [_WIN_FONTS, Path.home() / "AppData/Local/Microsoft/Windows/Fonts"]
    if platform.system() == "Darwin":
        return _MAC_DIRS
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"]


def _fc_match(name: str, bold: bool):
    """Linux 等で fc-match が使えればフォントファイルと index を引く（family が一致したときだけ）。"""
    if not shutil.which("fc-match"):
        return None
    pattern = f"{name}:bold" if bold else name
    try:
        out = subprocess.run(["fc-match", "-f", "%{family}\t%{file}\t%{index}", pattern],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    parts = out.split("\t")
    if len(parts) != 3 or name.lower() not in parts[0].lower():
        return None
    try:
        return parts[1], int(parts[2] or 0)
    except ValueError:
        return None


def _open_font(name: str, bold: bool):
    """フォント名から Pillow の FreeTypeFont（100px）を開く。開けなければ None。"""
    key = (name.lower(), bold)
    if key in _font_cache:
        return _font_cache[key]
    font = None
    try:
        from PIL import ImageFont
    except Exception:
        ImageFont = None
    if ImageFont is not None:
        regular, heavy = _KNOWN_FONTS.get(name.lower(), ([], []))
        candidates = (heavy if bold else regular)
        for fname, idx in candidates:
            for d in _font_dirs():
                p = d / fname
                if p.is_file():
                    try:
                        font = ImageFont.truetype(str(p), 100, index=idx)
                        break
                    except Exception:
                        continue
            if font:
                break
        if font is None and not candidates:
            hit = _fc_match(name, bold)
            if hit:
                try:
                    font = ImageFont.truetype(hit[0], 100, index=hit[1])
                except Exception:
                    font = None
    _font_cache[key] = font
    return font


def _names(value) -> list:
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip().strip('"\'') for v in value.split(",") if v.strip()]
    return [str(v) for v in value]


# 計測に使う既定フォント（build_deck が set_fonts で設定する）
_default_fonts = {"body": [], "heading": []}


def set_fonts(fonts: dict) -> None:
    """テーマの fonts（body / heading）を計測用の既定として登録する。"""
    _default_fonts["body"] = _names((fonts or {}).get("body"))
    _default_fonts["heading"] = _names((fonts or {}).get("heading")) or _default_fonts["body"]


def heading_fonts() -> list:
    """見出し用フォント（fonts.heading、無ければ fonts.body）の名前の列。"""
    return list(_default_fonts["heading"] or _default_fonts["body"])


def _pick_font(font, bold: bool):
    names = _names(font) if font else _default_fonts["body"]
    for n in names:
        f = _open_font(n, bold)
        if f is not None:
            return f, False
        if bold:
            f = _open_font(n, False)
            if f is not None:
                return f, True   # 太字のファイルが無いので通常体を少し広げて代用する
    return None, False


def fallback_ratio(ch: str) -> float:
    """フォントが測れないときの近似。全角=1.0、半角=0.55（従来の build_deck と同じ）。"""
    return 1.0 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.55


def char_em(ch: str, font=None, bold: bool = False) -> float:
    """1 文字の幅（em = 文字サイズに対する比）。"""
    key = (ch, tuple(_names(font) if font else _default_fonts["body"]), bold)
    if key in _em_cache:
        return _em_cache[key]
    f, synth_bold = _pick_font(font, bold)
    em = None
    if f is not None:
        try:
            em = f.getlength(ch) / 100.0
            if synth_bold:
                em *= 1.05
        except Exception:
            em = None
    if em is None or (em == 0 and not ch.isspace()):
        em = fallback_ratio(ch)
    _em_cache[key] = em
    return em


def measuring() -> bool:
    """既定フォントを実測できているか（テスト・診断用）。"""
    return _pick_font(None, False)[0] is not None


# ---------------------------------------------------------------------------
# 折り返しの模擬
# ---------------------------------------------------------------------------

# 行頭に来てはいけない文字（PowerPoint／ブラウザの標準的な禁則）
NO_LINE_START = set("、。，．・：；？！ー―‐～）」』】〕〉》｝］’”ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ々ゝゞ%％,.:;?!)]}")
# 行末に来てはいけない文字
NO_LINE_END = set("（「『【〔〈《｛［‘“([{")


def _is_word(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch in "_-.'%$#+/@&")


def _tokens(text: str) -> list:
    """折り返しの単位に分ける。英数字の連続は 1 単位（途中で切らない）、それ以外は 1 文字ずつ。"""
    out, buf = [], ""
    for ch in text:
        if _is_word(ch):
            buf += ch
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(ch)
    if buf:
        out.append(buf)
    return out


def wrap_lines(text, size_px: float, width_px: float, font=None, bold: bool = False) -> list:
    """幅 width_px で折り返したときの各行（文字列のリスト）。明示的な \\n でも改行する。"""
    text = str(text or "")
    width_px = max(1.0, float(width_px))
    lines = []
    for raw in text.split("\n"):
        if raw == "":
            lines.append("")
            continue
        cur, w = "", 0.0
        for tok in _tokens(raw):
            tw = sum(char_em(c, font, bold) for c in tok) * size_px
            if cur and w + tw > width_px:
                if tok[0] in NO_LINE_START:
                    # 行頭禁則: ぶら下げて前の行に残す
                    cur += tok
                    w += tw
                    continue
                if cur[-1] in NO_LINE_END and len(cur) > 1:
                    # 行末禁則: 開き括弧は次の行へ送る
                    carry = cur[-1]
                    lines.append(cur[:-1])
                    cur, w = carry, char_em(carry, font, bold) * size_px
                else:
                    lines.append(cur.rstrip(" "))
                    cur, w = "", 0.0
                if tok == " ":
                    continue
            if len(tok) > 1 and tw > width_px:
                # 1 行に収まらない長い英単語は文字単位で切る
                for c in tok:
                    cw = char_em(c, font, bold) * size_px
                    if cur and w + cw > width_px:
                        lines.append(cur)
                        cur, w = "", 0.0
                    cur += c
                    w += cw
                continue
            cur += tok
            w += tw
        lines.append(cur)
    return lines or [""]


def estimate_lines(text, size_px: float, width_px: float, font=None, bold: bool = False) -> int:
    """テキストが width_px の枠で何行になるか。"""
    text = str(text or "")
    if not text:
        return 1
    return max(1, len(wrap_lines(text, size_px, width_px, font, bold)))


# ---------------------------------------------------------------------------
# 泣き別れ対策
# ---------------------------------------------------------------------------

_PARTICLE_END = set("、。・のがをはにでとへもや）」』】")
_PREFIX_1 = set("全各新旧再非未同本当毎前後約計総両諸")


def _jtype(c: str) -> str:
    o = ord(c)
    if 0x3040 <= o <= 0x309F:
        return "hira"
    if 0x30A0 <= o <= 0x30FF:
        return "kata"
    if 0x4E00 <= o <= 0x9FFF or c == "々":
        return "kanji"
    if _is_word(c):
        return "alnum"
    return "other"


def good_break(text: str, i: int) -> bool:
    """text[i-1] と text[i] の間で改行してよいか（語の途中・送り仮名・数と単位の間・禁則を避ける）。"""
    if i <= 0 or i >= len(text):
        return False
    a, b = text[i - 1], text[i]
    if b in NO_LINE_START or a in NO_LINE_END:
        return False
    ta, tb = _jtype(a), _jtype(b)
    if b in "をがはにでへもの" and ta in ("hira", "kanji", "kata"):
        return False   # 助詞は前の語に付ける
    if a in _PREFIX_1 and (i < 2 or _jtype(text[i - 2]) != "kanji") and tb in ("kata", "kanji", "alnum"):
        return False   # 接頭の 1 字は次の語に付ける（「全／チーム」を避ける）
    if a == " " or b == " ":
        return True
    if a in _PARTICLE_END or b in "（「『【":
        return True
    if ta == tb and ta in ("alnum", "kata", "kanji"):
        return False
    if ta == "alnum" and tb in ("kanji", "hira"):
        return False   # 「120分」「Codeの」
    if ta == "hira" and tb == "kanji":
        run, j = 0, i - 1
        while j >= 0 and _jtype(text[j]) == "hira":
            run, j = run + 1, j - 1
        return run >= 2   # 送り仮名（「申し込み」）は切らない
    if ta in ("hira", "kanji", "kata") and tb in ("kata", "alnum") and ta != tb:
        return True
    if ta == "kata" and tb == "kanji":
        return True
    return False


def _has_cjk(text: str) -> bool:
    return any(_jtype(c) in ("hira", "kata", "kanji") for c in text)


def _width(s: str, size_px: float, font, bold: bool) -> float:
    return sum(char_em(c, font, bold) for c in s) * size_px


def balance(text, size_px: float, width_px: float, font=None, bold: bool = False, min_tail: int = 3) -> str:
    """最終行が min_tail 文字未満になる和文に、文節の切れ目で改行（\\n）を 1 つ入れて返す。
    2 行の文は前後が釣り合う位置、3 行以上の文は最終行が min_tail 文字以上になるなるべく後ろの位置で切る。
    直せないとき・対象外（改行済み・和文でない・長すぎる）のときは元の文字列をそのまま返す。"""
    if not isinstance(text, str) or "\n" in text or len(text) > 200 or not _has_cjk(text):
        return text
    lines = wrap_lines(text, size_px, width_px, font, bold)
    if len(lines) < 2 or len(lines[-1].strip()) >= min_tail:
        return text
    # 自然な折り返しの最終行・その前の行の開始位置
    starts, pos = [], 0
    for ln in lines:
        k = text.find(ln, pos) if ln else pos
        starts.append(k if k >= 0 else pos)
        pos = starts[-1] + len(ln)
    usable = width_px * 0.97   # 実際の描画との差を見込んで少し狭く見積もる
    best = None
    if len(lines) == 2:
        for i in range(2, len(text) - 1):
            if not good_break(text, i):
                continue
            head, tail = text[:i].rstrip(" "), text[i:].lstrip(" ")
            if len(tail) < min_tail:
                continue
            hw, tw = _width(head, size_px, font, bold), _width(tail, size_px, font, bold)
            if hw <= usable and tw <= usable:
                d = abs(hw - tw)
                if best is None or d < best[0]:
                    best = (d, i)
    else:
        prev_start, last_start = starts[-2], starts[-1]
        for i in range(last_start - 1, prev_start + min_tail - 1, -1):
            if not good_break(text, i):
                continue
            tail = text[i:].lstrip(" ")
            if len(tail) >= min_tail and _width(tail, size_px, font, bold) <= usable:
                best = (0, i)
                break
    if best is None:
        return text
    i = best[1]
    return text[:i].rstrip(" ") + "\n" + text[i:].lstrip(" ")

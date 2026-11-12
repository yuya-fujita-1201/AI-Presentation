#!/usr/bin/env python3
"""和文テキストの計測と改行位置の調整（build_deck / lint から使う共通モジュール）。

- 字幅の実測: テーマのフォント（fonts.body / heading）のフォントファイルを Pillow で開き、
  1 文字ずつ幅を測る（キャッシュ付き）。Pillow かフォントファイルが無い環境では
  従来の近似（全角 1.0 / 半角 0.55）に戻るので、結果は今までと同じになる。
- 折り返しの模擬: 英単語は途中で切らない・行頭禁則文字（「。」など）が行頭に来そうなときは直前の
  1 文字ごと次の行へ送る（追い出し。ブラウザの既定の挙動）、という規則で行に分ける（estimate_lines の精度を上げる）。
- テーマのフォントがこの機械に無いときは、ブラウザが代わりに使うフォント（SUBSTITUTE_FONTS）で測る。
  それも無いときだけ近似（全角 1.0 / 半角 0.55）。どれで測ったかは measure_source() で分かる。
- 泣き別れ対策: 折り返した最終行が 1〜2 文字だけになる文に、文節の切れ目で改行（\\n）を入れる。

Pillow は任意依存（setup_deps.py --pillow）。
"""
from __future__ import annotations

import os
import platform
import re
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


# テーマのフォントが無い機械で、ブラウザが実際に使う代替フォント（build_deck.FONT_FALLBACK_SANS と同じ順）。
# HTML の折り返しを模擬する目的では、近似（全角 1.0 / 半角 0.55）より実際に描かれるフォントの実測のほうが正確。
SUBSTITUTE_FONTS = ["Yu Gothic UI", "Meiryo", "Hiragino Sans", "Hiragino Kaku Gothic ProN"]


def _pick_font(font, bold: bool):
    names = _names(font) if font else _default_fonts["body"]
    for n in list(names) + [x for x in SUBSTITUTE_FONTS if x not in names]:
        f = _open_font(n, bold)
        if f is not None:
            return f, False
        if bold:
            f = _open_font(n, False)
            if f is not None:
                return f, True   # 太字のファイルが無いので通常体を少し広げて代用する
    return None, False


def measure_source(font=None) -> tuple:
    """字幅を何で測っているか。(要求した先頭のフォント名, 実際に測っているフォント名 or None)。
    2 つが同じなら指定どおり、違えば代替（SUBSTITUTE_FONTS）、後者が None なら近似（全角 1.0 / 半角 0.55）。"""
    names = _names(font) if font else _default_fonts["body"]
    for n in list(names) + [x for x in SUBSTITUTE_FONTS if x not in names]:
        if _open_font(n, False) is not None:
            return (names[0] if names else n), n
    return (names[0] if names else ""), None


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
    """既定フォントを（代替も含めて）実測できているか。False なら近似（全角 1.0 / 半角 0.55）で測っている。"""
    return measure_source()[1] is not None


# ---------------------------------------------------------------------------
# 折り返しの模擬
# ---------------------------------------------------------------------------

# 行頭に来てはいけない文字（PowerPoint／ブラウザの標準的な禁則）
NO_LINE_START = set("、。，．・：；？！ー―‐～）」』】〕〉》｝］’”ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ々ゝゞ%％,.:;?!)]}")
# Chromium の既定（line-break: auto）は、小書きの仮名（っ・ゃ・ッ・ャ・ヶ など）と長音「ー」を行頭に置く（「ブロ／ック」「サー／バー」）。
# wrap_lines(loose=True) はこちらで折る（HTML の実際の折り返しを見積もる。wrap_fix の判定用）
LOOSE_NO_LINE_START = NO_LINE_START - set("ーぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
# 行末に来てはいけない文字
NO_LINE_END = set("（「『【〔〈《｛［‘“([{")


def _is_word(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch in "_-.'%$#+/@&")


# 【要確認】/【要確認: …】のマーカー（todo_marks.TODO_MARK と同じ形。ここに置くのは ja_text を単独で使えるままにするため）
_TODO_MARK = re.compile(r"【要確認(?:\s*[:：]\s*([^】]*))?】")


def _tokens(text: str, marker_atomic: bool = True) -> list:
    """折り返しの単位に分ける。英数字の連続は 1 単位（途中で切らない）、それ以外は 1 文字ずつ。
    【要確認】/【要確認: …】のマーカーも 1 単位にする（行をまたぐと強調が付かなくなるため。幅に収まらない長いマーカーは wrap_lines が文字単位にほどく）。"""
    out = []
    pos = 0
    spans = [m.span() for m in _TODO_MARK.finditer(text)] if marker_atomic and "【要確認" in text else []
    spans.append((len(text), len(text)))
    for a, b in spans:
        buf = ""
        for ch in text[pos:a]:
            if _is_word(ch):
                buf += ch
                continue
            if buf:
                out.append(buf)
                buf = ""
            out.append(ch)
        if buf:
            out.append(buf)
        if b > a:
            out.append(text[a:b])
        pos = b
    return out


def wrap_lines(text, size_px: float, width_px: float, font=None, bold: bool = False, loose: bool = False) -> list:
    """幅 width_px で折り返したときの各行（文字列のリスト）。明示的な \\n でも改行する。

    行頭禁則（NO_LINE_START）は追い出し: 行頭に来てしまう「。」「、」などは、直前の 1 単位ごと次の行へ送る
    （ブラウザの既定の挙動。ぶら下げではない）。行末禁則（NO_LINE_END。開き括弧）も次の行へ送る。"""
    text = str(text or "")
    width_px = max(1.0, float(width_px))
    no_start = LOOSE_NO_LINE_START if loose else NO_LINE_START
    lines = []
    for raw in text.split("\n"):
        if raw == "":
            lines.append("")
            continue
        cur: list = []     # 現在の行の単位（トークン）と幅
        widths: list = []
        w = 0.0
        ns = 0             # cur の末尾に連続する行頭禁則の単位の数（追い出しの戻り幅。数え直さないよう持ち回る）

        def flush(keep=()):
            nonlocal cur, widths, w, ns
            lines.append("".join(cur).rstrip(" "))
            cur = [t for t, _ in keep]
            widths = [x for _, x in keep]
            w = sum(widths)
            ns = 0
            for t in reversed(cur):
                if t[0] not in no_start:
                    break
                ns += 1

        toks = []
        for tok in _tokens(raw):
            if len(tok) > 1 and tok.startswith("【") and sum(char_em(c, font, bold) for c in tok) * size_px > width_px:
                toks.extend(tok)        # 幅に収まらない長いマーカーは、従来どおり文字単位で折る
            else:
                toks.append(tok)
        for tok in toks:
            tw = sum(char_em(c, font, bold) for c in tok) * size_px
            if cur and w + tw > width_px:
                if tok[0] in no_start:
                    # 追い出し: 禁則文字が行頭に来ないよう、直前の単位（禁則文字が続くならさらに前）ごと次の行へ。
                    # 行全体を送っても行頭が空になるだけのとき（1 単位しか無い）は、ぶら下げて今の行に残す。
                    k = max(len(cur) - 1 - ns, 0)       # 末尾の禁則文字の連続をさかのぼった位置（逐次に数えると 2 乗時間になる）
                    if k > 0:
                        carry = list(zip(cur[k:], widths[k:]))
                        cur, widths = cur[:k], widths[:k]
                        flush(carry)
                    else:
                        cur.append(tok)
                        widths.append(tw)
                        w += tw
                        ns += 1
                        continue
                elif cur[-1][-1] in NO_LINE_END and len(cur) > 1:
                    # 行末禁則: 開き括弧は次の行へ送る
                    carry = [(cur[-1], widths[-1])]
                    cur, widths = cur[:-1], widths[:-1]
                    flush(carry)
                else:
                    flush()
                if tok == " ":
                    continue
            if len(tok) > 1 and tw > width_px:
                # 1 行に収まらない長い英単語は文字単位で切る
                for c in tok:
                    cw = char_em(c, font, bold) * size_px
                    if cur and w + cw > width_px:
                        flush()
                    cur.append(c)
                    widths.append(cw)
                    w += cw
                    ns = ns + 1 if c[0] in no_start else 0
                continue
            cur.append(tok)
            widths.append(tw)
            w += tw
            ns = ns + 1 if tok[0] in no_start else 0
        lines.append("".join(cur))
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


_OPEN_BR = set("（([「『【〔〈《｛［")
_CLOSE_BR = set("）)]」』】〕〉》｝］")


def soft_bad_break(text: str, i: int) -> bool:
    """禁則には当たらないが、体裁として避けたい切り位置: 括弧の内側、「・」の直後（並列語の途中）。"""
    if i <= 0 or i >= len(text):
        return False
    if text[i - 1] == "・":
        return True
    depth = 0
    for c in text[:i]:
        if c in _OPEN_BR:
            depth += 1
        elif c in _CLOSE_BR and depth:
            depth -= 1
    return depth > 0


# ---------------------------------------------------------------------------
# 文節の切れ目（共通の規則。型エンジン pattern_engine もこれを呼ぶ）
# ---------------------------------------------------------------------------

_PARTICLE_B = "をがはにでへもの"
_COMPOUND_PARTICLES = ("とし", "とい", "につ", "によ", "にお")

# 仮名の連続の途中で、語の続きに当たる並び（「出に|くかった」「読み|やすい」「見|ながら」…）。直前が助詞らしい字でも、ここでは切らない
_KANA_CONTINUE = ("くい", "くく", "くか", "くて", "くな", "やす", "づら", "ながら", "たい", "たく", "たか", "ます", "まし", "ませ", "ない", "なか",
                  "なく", "なっ", "なり", "ある", "あっ", "いる", "いた", "いな", "いま", "して", "した", "しま", "する", "され", "でき", "てい", "てお", "てく",
                  "てき", "てみ", "てあ", "てし", "ほし", "もら", "くれ", "あげ", "しれ", "すぎ", "られ", "せる", "よう", "そう", "らし", "みた")

BREAK_LEVELS = (1, 2, 3)


def can_break(text: str, i: int, level: int = 1) -> bool:
    """文節の切れ目として使ってよいか（good_break に、文字枠・見出しのための規則を足したもの。型エンジンと既存タイプの折り返しが共有する）。
    level 1（既定）: 数字と単位の間の空白（「1 か月」「3 名」）は切らない。「週 2 回」「第 3 期」のように和文 + 空白 + 数字の空白も切らない。
    仮名どうしの間は、名詞に付いた助詞（「新棟で|まとめて」）の直後だけ切る（「まと|めて」「出に|くかった」のような動詞・活用語の途中は切らない）。
    「として」「という」「について」「により」「において」は 1 語として扱う。
    level 2: 「週 2 回」の空白は切ってよい（数字と単位は離さない）。level 3: good_break だけ（どうしても収まらないとき）。"""
    if not good_break(text, i):
        return False
    if level >= 3:
        return True
    a, b = text[i - 1], text[i]
    ta, tb = _jtype(a), _jtype(b)
    if text[i - 1:i + 1] in _COMPOUND_PARTICLES:
        return False
    # 英数字（と、その後ろの空白）のあとに助詞が続くとき（「JSON の」「Slack を」）は、助詞の前で切らない（助詞は前の語に付ける）
    if (b in _PARTICLE_B and (a == " " or ta == "alnum")) or (b == " " and i + 1 < len(text) and text[i + 1] in _PARTICLE_B and ta == "alnum"):
        return False
    if ta == "hira" and tb == "hira":
        prev = _jtype(text[i - 2]) if i >= 2 else "other"
        if prev == "hira" or text[i:i + 3].startswith(_KANA_CONTINUE) or text[i:i + 2] in _KANA_CONTINUE:
            return False              # 仮名が続く途中・活用語の続き
    if i >= 2 and text[i - 1] == " " and text[i - 2].isdigit() and _jtype(text[i]) in ("hira", "kanji", "kata"):
        return False
    if i + 1 < len(text) and text[i] == " " and text[i - 1].isdigit() and _jtype(text[i + 1]) in ("hira", "kanji", "kata"):
        return False
    if level >= 2:
        return True
    # 逆向き: 漢字・カタカナ + 空白 + 数字（「週 2 回」「第 3 期」「約 8 億円」）も、空白の前後で切らない
    # （ひらがなの助詞のあと「部署で / 3 か月」は文節の切れ目なので切れる）
    if i >= 2 and text[i - 1] == " " and _jtype(text[i - 2]) in ("kanji", "kata") and text[i].isdigit():
        return False
    if i + 1 < len(text) and text[i] == " " and _jtype(text[i - 1]) in ("kanji", "kata") and text[i + 1].isdigit():
        return False
    return True


def tail_min(size_px: float, base: int = 3) -> int:
    """最終行に最低限残したい文字数。36px 以上の大きな文字は、短い切れ端（「つくる」）が目立つので、文字サイズに応じて増やす（36px で 4、52px で 6）。"""
    if size_px < 36:
        return base
    return max(base, int(round(size_px / 9)))



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
    # 切れ目の規則は level 1（厳しい: 活用語の途中・「週 2 回」の空白を切らない）→ 2 → 3（good_break だけ）の順にゆるめる。
    # 規則が厳しすぎて切れ目が無いときだけ次の level を使う（level 3 は従来と同じ）
    for level in BREAK_LEVELS:
        best = _balance_cut(text, lines, starts, size_px, font, bold, min_tail, usable, level)
        if best is not None:
            break
    if best is None:
        return text
    i = best
    return text[:i].rstrip(" ") + "\n" + text[i:].lstrip(" ")


def _balance_cut(text, lines, starts, size_px, font, bold, min_tail, usable, level):
    """balance の切り位置（文字の添字）。見つからなければ None。"""
    # 括弧の内側・「・」の直後は避ける（そこしか無いときだけ使う）。体裁の悪い候補は ok=False の組に分けて持つ
    best_ok = best_soft = None
    if len(lines) == 2:
        for i in range(2, len(text) - 1):
            if not can_break(text, i, level):
                continue
            head, tail = text[:i].rstrip(" "), text[i:].lstrip(" ")
            if len(tail) < min_tail:
                continue
            hw, tw = _width(head, size_px, font, bold), _width(tail, size_px, font, bold)
            if hw <= usable and tw <= usable:
                d = abs(hw - tw)
                if soft_bad_break(text, i):
                    if best_soft is None or d < best_soft[0]:
                        best_soft = (d, i)
                elif best_ok is None or d < best_ok[0]:
                    best_ok = (d, i)
    else:
        prev_start, last_start = starts[-2], starts[-1]
        for i in range(last_start - 1, prev_start + min_tail - 1, -1):
            if not can_break(text, i, level):
                continue
            tail = text[i:].lstrip(" ")
            if len(tail) >= min_tail and _width(tail, size_px, font, bold) <= usable:
                if soft_bad_break(text, i):
                    if best_soft is None:
                        best_soft = (0, i)
                else:
                    best_ok = (0, i)
                    break
    best = best_ok or best_soft
    return best[1] if best else None


def phrase_wrap(text, size_px: float, width_px: float, font=None, bold: bool = False, min_tail: int = 4, max_back: float = 0.5) -> str:
    """大きな文字（表紙のタイトル・パネルの一文など）の改行を、語の途中ではなく文節の切れ目に置く。
    自然な折り返しで各行の終わりが good_break（助詞のあと・送り仮名の後・和欧の境目など）でなければ、
    その行の中の少し前の良い切れ目（行の max_back 倍までさかのぼる）に改行（\\n）を入れる。
    最終行が min_tail 文字未満にならないようにする（なるなら 1 つ前の行から文を分け直す）。
    見つからなければ自然な折り返しのまま。行数が増えることがある（呼び出し側が文字サイズ・高さで吸収する）。
    改行済み・和文でない・長すぎる文字列はそのまま返す。"""
    if not isinstance(text, str) or "\n" in text or len(text) > 200 or not _has_cjk(text):
        return text
    width_px = width_px * 0.98    # 代替フォントと実機のフォントの字幅の差を見込む（ぎりぎり 1 行に見える文が語の途中で折れるのを防ぐ）
    out, rest = [], text
    guard = 0
    while rest and guard < 40:
        guard += 1
        ls = wrap_lines(rest, size_px, width_px, font, bold)
        if len(ls) <= 1:
            out.append(rest)
            rest = ""
            break
        first = ls[0]
        pos = len(first)
        if pos <= 0 or pos >= len(rest):
            out.append(rest)
            rest = ""
            break
        # 自然な切れ目が良ければそのまま。悪ければ（語の途中）少し前の良い切れ目を探す
        cut = pos
        lo = max(2, int(pos * (1 - max_back)))
        for level in BREAK_LEVELS:      # 厳しい規則で切れ目が見つからなければゆるめる（level 3 は従来と同じ）
            if can_break(rest, pos, level) and not soft_bad_break(rest, pos):
                break                    # 自然な折り返し位置がこの規則で良い切れ目 → そのまま
            cand = next((i for i in range(pos - 1, lo - 1, -1) if can_break(rest, i, level) and not soft_bad_break(rest, i)), None)
            if cand is not None:
                cut = cand
                break
        out.append(rest[:cut].rstrip(" "))
        rest = rest[cut:].lstrip(" ")
    if rest:
        out.append(rest)
    # 最終行が短すぎる場合は、直前の行の終わりから文節ごと送る（balance と同じ考え方）。直せなければ元の折り返しに戻す
    if len(out) >= 2 and len(out[-1].strip()) < min_tail:
        fixed = balance(text, size_px, width_px / 0.98, font, bold, min_tail=min_tail)       # 元の文から切り直す（行末で落とした空白を失わない）
        if "\n" in fixed:
            out = fixed.split("\n")
        else:
            return text
    if len(out) == 2:
        # 2 行に収まるときは、行の長さが近い切れ目を選ぶ（大きな文字では、長い行と短い行が並ぶより揃っているほうが読みやすい）
        eq = _equal_two(text, size_px, width_px, font, bold, min_tail)
        if eq is not None and eq != out:
            w0 = [_width(x, size_px, font, bold) for x in out]
            w1 = [_width(x, size_px, font, bold) for x in eq]
            if abs(w1[0] - w1[1]) + 1e-6 < abs(w0[0] - w0[1]):
                out = eq
    return "\n".join(out)


def _equal_two(text, size_px, width_px, font, bold, min_tail):
    """2 行に分けるとき、前後の幅の差が最小になる切れ目（規則は厳しい level から）。無ければ None。括弧の内側・「・」の直後は避ける。"""
    usable = width_px * 0.97
    for level in BREAK_LEVELS:
        best = None
        for i in range(2, len(text) - 1):
            if not can_break(text, i, level) or soft_bad_break(text, i):
                continue
            head, tail = text[:i].rstrip(" "), text[i:].lstrip(" ")
            if len(tail) < min_tail or len(head) < min_tail:
                continue
            hw, tw = _width(head, size_px, font, bold), _width(tail, size_px, font, bold)
            if hw <= usable and tw <= usable:
                d = abs(hw - tw)
                if text[i - 1] in "。！？、" and min(hw, tw) >= 0.55 * max(hw, tw):
                    d *= 0.1                 # 句読点の直後で、前後が大きく違わないなら、そこで切るのを優先する（文の切れ目）
                if best is None or d < best[0]:
                    best = (d, [head, tail])
        if best:
            return best[1]
    return None


# ---------------------------------------------------------------------------
# 行ごとの分割（型エンジンの文字枠。pattern_engine が呼ぶ）
# ---------------------------------------------------------------------------

def phrase_lines(text, size, width, font=None, bold=False):
    """和文を、文節の切れ目（good_break）で折り返した行のリスト。語の途中（「窓/口」「測/り」）で切れる文字単位の折り返しを避ける。
    和文を含まない・すでに改行がある・1 行に収まる文は [text] を返す。文節が 1 行に収まらないときだけ文字単位で切る"""
    if not text or "\n" in text or len(text) > 400 or not _has_cjk(text) or width < size * 2:
        return [text]
    if len(wrap_lines(text, size, width, font, bold)) < 2:
        return [text]
    usable = width * 0.97          # 実際の描画との差を見込んで少し狭く見積もる

    def w(a, b):
        return _width(text[a:b], size, font, bold)
    n = len(text)
    # 文節の切れ目だけで、行末の余りの二乗和が最小になる分割（ばらつきを抑える）。最終行は余りを軽く見て、短すぎる行（3 文字未満）は避ける。
    # 切れ目の規則は level 1（厳しい）→ 2 → 3 の順にゆるめる: 規則が厳しすぎて収まらない・最終行が 1〜2 文字になるときだけ、次の level を試す
    pre = [0.0]
    for ch in text:
        pre.append(pre[-1] + char_em(ch, font, bold) * size)
    INF = float("inf")
    first_ok = None
    for level in (1, 2, 3):
        cuts = [0] + [i for i in range(1, n) if can_break(text, i, level)] + [n]
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
            acc += char_em(text[i - 1], font, bold) * size
            if acc > usable:
                break
            if can_break(text, i, 2):
                best = i
        if best is None:           # 文節が長くて収まらない: 文字単位の自然な折り返しに任せる
            first = wrap_lines(text[start:], size, width, font, bold)[0]
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
            if not can_break(joined, i):
                continue
            hw = _width(joined[:i], size, font, bold)
            tw = _width(joined[i:], size, font, bold)
            if hw <= usable and tw <= usable and len(joined[i:].strip()) >= 3 and (cand is None or abs(hw - tw) < cand[0]):
                cand = (abs(hw - tw), i)
        if cand:
            lines[-2:] = [joined[:cand[1]].strip(" "), joined[cand[1]:].strip(" ")]
    return [ln for ln in lines if ln] or [text]

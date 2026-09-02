#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""サンプルスライド（PPTX / HTML / PDF / 画像）から配色・フォントを抽出してテーマ JSON を生成する。

使い方:
    python tools/theme_from_sample.py <file> --name <name> [--dir DIR] [--pages N] [--colors N]

対応形式と抽出方法:
    .pptx/.pptm  埋め込みテーマ（clrScheme/fontScheme）を直接読む（最良品質・追加依存なし）
    .png/.jpg…   主要色を量子化抽出（要 pillow）
    .pdf         先頭ページを描画して主要色を抽出＋埋め込みフォント名（要 pymupdf）
    .html/.htm   宣言された色（#hex / rgb()）と font-family を静的抽出

抽出は自動推定なので、生成後は必ずレポートを見て `colors`/`fonts` を微調整すること。
出力先の優先順: --dir → 環境変数 SLIDE_DECK_THEMES の先頭 → 同梱 templates/themes/
トークンの意味は references/themes.md を参照。
"""

import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLED_THEMES = ROOT / "templates" / "themes"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# ---------------------------------------------------------------------------
# 色ユーティリティ（純Python・依存なし）
# ---------------------------------------------------------------------------

def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb2hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(c1, c2, t):
    """c1 と c2 を線形補間。t は c2 の重み(0..1)。"""
    return tuple(c1[i] * (1 - t) + c2[i] * t for i in range(3))


def lighten(c, t):
    return mix(c, (255, 255, 255), t)


def darken(c, t):
    return mix(c, (0, 0, 0), t)


def lum(rgb):
    """相対輝度 0..1（sRGB）。"""
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def sat(rgb):
    """HSV 彩度 0..1。"""
    mx, mn = max(rgb), min(rgb)
    return 0.0 if mx == 0 else (mx - mn) / mx


def dist(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


# ---------------------------------------------------------------------------
# 4キー(bg/text/primary/accent) + フォント → 14+3 トークンへ導出
# ---------------------------------------------------------------------------

def derive_theme(name, bg, text, primary, accent, fonts):
    on_primary = (255, 255, 255) if lum(primary) < 0.55 else (27, 27, 36)
    colors = {
        "background": bg,
        "surface": lighten(primary, 0.92),
        "text": text,
        "muted": mix(text, bg, 0.45),
        "primary": primary,
        "accent": accent,
        "on_primary": on_primary,
        "on_primary_soft": lighten(primary, 0.90),
        "on_primary_muted": lighten(primary, 0.72),
        "code_bg": darken(primary, 0.62),
        "code_text": lighten(primary, 0.88),
        "table_header_bg": primary,
        "table_header_text": on_primary,
        "table_row_alt": lighten(primary, 0.92),
    }
    return {
        "name": name,
        "colors": {k: rgb2hex(v) for k, v in colors.items()},
        "fonts": fonts,
    }


# ---------------------------------------------------------------------------
# パレット分類（画像 / PDF / HTML 共通）: [(rgb, weight)] → bg,text,primary,accent
# ---------------------------------------------------------------------------

def classify_palette(colors, default_accent):
    """頻度付き色リストから 4 キーを推定。colors: [(rgb, weight)] weight 降順が望ましい。"""
    if not colors:
        raise ValueError("色を抽出できませんでした")
    by_weight = sorted(colors, key=lambda cw: -cw[1])
    rgbs = [c for c, _ in by_weight]
    # 背景: 明るい色で最も使われているもの（なければ最も明るい）
    light = [c for c in rgbs if lum(c) > 0.8]
    bg = light[0] if light else max(rgbs, key=lum)
    # 文字: 暗い色で最も使われているもの（なければ最も暗い）
    dark = [c for c in rgbs if lum(c) < 0.25]
    text = dark[0] if dark else min(rgbs, key=lum)
    # ブランド色候補: 彩度があり、bg/text から離れた色
    colored = [(c, w) for c, w in by_weight
               if sat(c) > 0.15 and dist(c, bg) > 40 and dist(c, text) > 40]
    if colored:
        primary = colored[0][0]                                  # 最も使われている有彩色
        acc_cands = [c for c, _ in colored if dist(c, primary) > 60]
        accent = max(acc_cands, key=sat) if acc_cands else lighten(primary, 0.25)
    else:
        primary = darken(text, 0.0) if lum(text) < 0.4 else (40, 40, 60)
        accent = default_accent
    return bg, text, primary, accent, bool(colored)


# ---------------------------------------------------------------------------
# 形式別の抽出
# ---------------------------------------------------------------------------

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _clr_from_elem(elem):
    """<a:srgbClr val=..> / <a:sysClr lastClr=..> から hex を得る。"""
    srgb = elem.find(f"{_A}srgbClr")
    if srgb is not None and srgb.get("val"):
        return hex2rgb(srgb.get("val"))
    sysclr = elem.find(f"{_A}sysClr")
    if sysclr is not None and sysclr.get("lastClr"):
        return hex2rgb(sysclr.get("lastClr"))
    return None


def _pptx_scheme_and_fonts(path):
    """theme1.xml から clrScheme（テーマ色スロット→rgb）と fontScheme を読む。"""
    with zipfile.ZipFile(path) as z:
        themes = [n for n in z.namelist() if re.match(r"ppt/theme/theme\d+\.xml$", n)]
        xml = z.read(sorted(themes)[0]) if themes else None
    scheme, fonts = {}, {}
    if xml:
        root = ET.fromstring(xml)
        clr = root.find(f"{_A}themeElements/{_A}clrScheme")
        for child in (list(clr) if clr is not None else []):
            rgb = _clr_from_elem(child)
            if rgb:
                scheme[child.tag.replace(_A, "")] = rgb
        fs = root.find(f"{_A}themeElements/{_A}fontScheme")
        if fs is not None:
            for slot, key in (("majorFont", "heading"), ("minorFont", "body")):
                latin = fs.find(f"{_A}{slot}/{_A}latin")
                if latin is not None and latin.get("typeface"):
                    fonts[key] = latin.get("typeface")
    return scheme, fonts


def extract_pptx(path):
    """スライド内で実際に使われている塗り色・文字色・フォントを面積/文字量で集計する。
    ビルダー生成PPTXやブランドPPTXは色を直接シェイプに適用することが多く、埋め込み
    clrScheme（既定Office色のことがある）より実使用色のほうが見た目に忠実なため。"""
    try:
        from pptx import Presentation
        from pptx.enum.dml import MSO_FILL, MSO_COLOR_TYPE, MSO_THEME_COLOR
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError:
        sys.exit("error: PPTX 抽出には python-pptx が必要です。/slide-deck:setup（または pip install python-pptx）")

    scheme, scheme_fonts = _pptx_scheme_and_fonts(path)
    THEME_SLOT = {
        MSO_THEME_COLOR.DARK_1: "dk1", MSO_THEME_COLOR.TEXT_1: "dk1",
        MSO_THEME_COLOR.LIGHT_1: "lt1", MSO_THEME_COLOR.BACKGROUND_1: "lt1",
        MSO_THEME_COLOR.DARK_2: "dk2", MSO_THEME_COLOR.TEXT_2: "dk2",
        MSO_THEME_COLOR.LIGHT_2: "lt2", MSO_THEME_COLOR.BACKGROUND_2: "lt2",
        MSO_THEME_COLOR.ACCENT_1: "accent1", MSO_THEME_COLOR.ACCENT_2: "accent2",
        MSO_THEME_COLOR.ACCENT_3: "accent3", MSO_THEME_COLOR.ACCENT_4: "accent4",
        MSO_THEME_COLOR.ACCENT_5: "accent5", MSO_THEME_COLOR.ACCENT_6: "accent6",
        MSO_THEME_COLOR.HYPERLINK: "hlink", MSO_THEME_COLOR.FOLLOWED_HYPERLINK: "folHlink",
    }

    def resolve(color):
        try:
            if color.type == MSO_COLOR_TYPE.RGB:
                return hex2rgb(str(color.rgb))
            if color.type == MSO_COLOR_TYPE.SCHEME:
                return scheme.get(THEME_SLOT.get(color.theme_color))
        except Exception:
            return None
        return None

    fill_ct, text_ct, font_ct = Counter(), Counter(), Counter()

    def walk(shapes):
        for sh in shapes:
            try:
                if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                    walk(sh.shapes)
                    continue
            except Exception:
                pass
            # 塗り（面積重み）
            try:
                if sh.fill.type == MSO_FILL.SOLID:
                    rgb = resolve(sh.fill.fore_color)
                    if rgb:
                        area = max(1, (sh.width or 0) // 9525) * max(1, (sh.height or 0) // 9525)
                        fill_ct[rgb] += area
            except Exception:
                pass
            # 文字色・フォント（文字量重み）
            try:
                if sh.has_text_frame:
                    for para in sh.text_frame.paragraphs:
                        for run in para.runs:
                            n = max(1, len(run.text))
                            if run.font.name:
                                font_ct[run.font.name] += n
                            rgb = resolve(run.font.color)
                            if rgb:
                                text_ct[rgb] += n
            except Exception:
                pass

    prs = Presentation(path)
    for slide in prs.slides:
        walk(slide.shapes)

    # パレット = 塗り色（面積） + 文字色（文字量を面積スケールに寄せる）
    palette = Counter()
    for rgb, w in fill_ct.items():
        palette[rgb] += w
    tscale = (sum(fill_ct.values()) / max(1, sum(text_ct.values()))) * 0.5 if text_ct else 1
    for rgb, w in text_ct.items():
        palette[rgb] += w * tscale

    colors = [(c, w) for c, w in palette.items()]
    if colors:
        bg, text, primary, accent, colored = classify_palette(colors, DEFAULT_ACCENT)
    else:
        # 塗りが取れない場合は埋め込みテーマ色にフォールバック
        bg = scheme.get("lt1", (255, 255, 255)); text = scheme.get("dk1", (26, 34, 51))
        primary = scheme.get("accent1", (15, 61, 110)); accent = scheme.get("accent2", lighten(primary, 0.25))
        colored = True

    fonts = {}
    if font_ct:
        fonts["heading"] = fonts["body"] = font_ct.most_common(1)[0][0]
    fonts = {**scheme_fonts, **fonts}  # 実使用フォント優先、無ければ fontScheme

    report = {"source": "pptx", "detected_colored": colored,
              "palette": [rgb2hex(c) for c, _ in sorted(colors, key=lambda x: -x[1])[:8]],
              "fonts_found": [n for n, _ in font_ct.most_common(5)] or list(scheme_fonts.values())}
    return bg, text, primary, accent, fonts, report


def _image_palette(pil_img, ncolors):
    from PIL import Image
    im = pil_img.convert("RGB")
    im.thumbnail((400, 400))
    q = im.quantize(colors=max(4, ncolors), method=Image.Quantize.FASTOCTREE)
    pal = q.getpalette()
    total = sum(c for c, _ in q.getcolors())
    out = []
    for count, idx in q.getcolors():
        rgb = tuple(pal[idx * 3: idx * 3 + 3])
        out.append((rgb, count / total))
    return out


def extract_image(path, ncolors):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("error: 画像抽出には pillow が必要です。/slide-deck:setup --pillow（または pip install pillow）")
    colors = _image_palette(Image.open(path), ncolors)
    bg, text, primary, accent, colored = classify_palette(colors, DEFAULT_ACCENT)
    report = {"source": "image", "detected_colored": colored,
              "palette": [rgb2hex(c) for c, _ in sorted(colors, key=lambda x: -x[1])[:8]]}
    return bg, text, primary, accent, {}, report


def extract_pdf(path, pages, ncolors):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("error: PDF 抽出には pymupdf が必要です。/slide-deck:setup --pdf（または pip install pymupdf）")
    from PIL import Image
    doc = fitz.open(path)
    counter = Counter()
    fonts_ct = Counter()
    for i in range(min(pages, doc.page_count)):
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        for rgb, w in _image_palette(img, ncolors):
            counter[rgb] += w
        for f in page.get_fonts(full=True):
            nm = (f[3] or "").split("+")[-1]
            if nm:
                fonts_ct[nm] += 1
    colors = [(c, w) for c, w in counter.items()]
    bg, text, primary, accent, colored = classify_palette(colors, DEFAULT_ACCENT)
    fonts = {}
    if fonts_ct:
        top = fonts_ct.most_common(1)[0][0]
        fonts = {"heading": top, "body": top}
    report = {"source": "pdf", "detected_colored": colored,
              "palette": [rgb2hex(c) for c, _ in sorted(colors, key=lambda x: -x[1])[:8]],
              "fonts_found": [n for n, _ in fonts_ct.most_common(5)]}
    return bg, text, primary, accent, fonts, report


def extract_html(path, ncolors):
    text_src = Path(path).read_text(encoding="utf-8", errors="ignore")
    counter = Counter()
    for h in re.findall(r"#[0-9a-fA-F]{6}\b", text_src):
        counter[hex2rgb(h)] += 1
    for h in re.findall(r"#[0-9a-fA-F]{3}\b", text_src):
        counter[hex2rgb(h)] += 1
    for m in re.findall(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text_src):
        counter[tuple(int(x) for x in m)] += 1
    if not counter:
        sys.exit("error: HTML から色を抽出できませんでした（インラインの #hex / rgb() が必要）")
    colors = [(c, n) for c, n in counter.items()]
    bg, text, primary, accent, colored = classify_palette(colors, DEFAULT_ACCENT)
    # font-family: 引用符付きも拾い、先頭ファミリだけを取り出す
    fams = re.findall(r"font-family\s*:\s*([^;}\n]+)", text_src, re.I)
    first_fams = [f.split(",")[0].strip().strip("'\"") for f in fams]
    first_fams = [f for f in first_fams if f and "monospace" not in f.lower()]
    fonts = {}
    counts = Counter(first_fams)
    if counts:
        top = counts.most_common(1)[0][0]
        fonts = {"heading": top, "body": top}
    report = {"source": "html", "detected_colored": colored,
              "palette": [rgb2hex(c) for c, _ in sorted(colors, key=lambda x: -x[1])[:8]],
              "fonts_found": [n for n, _ in counts.most_common(5)]}
    return bg, text, primary, accent, fonts, report


# ---------------------------------------------------------------------------

def load_default():
    return json.loads((BUNDLED_THEMES / "default.json").read_text(encoding="utf-8"))


DEFAULT_ACCENT = (0, 168, 204)  # default.json の accent（フォールバック用）。main で上書き


def resolve_out_dir(arg_dir):
    if arg_dir:
        return Path(arg_dir)
    env = os.environ.get("SLIDE_DECK_THEMES")
    if env:
        first = next((p for p in env.split(os.pathsep) if p.strip()), None)
        if first:
            return Path(first)
    return BUNDLED_THEMES


DISPATCH = {
    ".pptx": "pptx", ".pptm": "pptx",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".bmp": "image",
    ".pdf": "pdf",
    ".html": "html", ".htm": "html",
}


def main():
    global DEFAULT_ACCENT
    ap = argparse.ArgumentParser(description="サンプルスライドからテーマJSONを生成")
    ap.add_argument("file", help="サンプル(.pptx/.png/.jpg/.pdf/.html)")
    ap.add_argument("--name", required=True, help="作成するテーマ名（kebab-case）")
    ap.add_argument("--dir", help="出力先ディレクトリ")
    ap.add_argument("--pages", type=int, default=2, help="PDFで走査するページ数（既定2）")
    ap.add_argument("--colors", type=int, default=8, help="量子化する色数（既定8）")
    ap.add_argument("--force", action="store_true", help="既存を上書き")
    args = ap.parse_args()

    if not NAME_RE.match(args.name) or args.name == "default":
        sys.exit(f"error: テーマ名は kebab-case で 'default' 以外にしてください: {args.name}")
    src = Path(args.file)
    if not src.exists():
        sys.exit(f"error: ファイルがありません: {src}")
    kind = DISPATCH.get(src.suffix.lower())
    if not kind:
        sys.exit(f"error: 未対応の形式です: {src.suffix}（対応: {', '.join(sorted(DISPATCH))}）")

    default_theme = load_default()
    DEFAULT_ACCENT = hex2rgb(default_theme["colors"]["accent"])

    if kind == "pptx":
        bg, text, primary, accent, fonts, report = extract_pptx(src)
    elif kind == "image":
        bg, text, primary, accent, fonts, report = extract_image(src, args.colors)
    elif kind == "pdf":
        bg, text, primary, accent, fonts, report = extract_pdf(src, args.pages, args.colors)
    else:
        bg, text, primary, accent, fonts, report = extract_html(src, args.colors)

    # フォントは検出できた分だけ採用、残りは default から補完
    merged_fonts = dict(default_theme["fonts"])
    merged_fonts.update({k: v for k, v in fonts.items() if v})
    theme = derive_theme(args.name, bg, text, primary, accent, merged_fonts)

    out_dir = resolve_out_dir(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.json"
    if out_path.exists() and not args.force:
        sys.exit(f"error: すでに存在します: {out_path}（上書きは --force）")
    out_path.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # レポート
    print(f"サンプル: {src}  ({report['source']})")
    if "scheme" in report:
        print(f"  検出テーマ色: {report['scheme']}")
    if "palette" in report:
        print(f"  主要色: {', '.join(report['palette'])}")
    if report.get("fonts_found"):
        print(f"  検出フォント: {', '.join(report['fonts_found'])}")
    if not report.get("detected_colored", True):
        print("  ⚠ 有彩色を検出できず、primary/accent を推定/既定で補いました。要調整。")
    print("  → マッピング:")
    for k in ("background", "text", "primary", "accent"):
        print(f"      {k:10} = {theme['colors'][k]}")
    print(f"  フォント: heading={theme['fonts']['heading']} / body={theme['fonts']['body']} / code={theme['fonts']['code']}")
    print(f"\n作成しました: {out_path}")
    if out_dir == BUNDLED_THEMES:
        print("  ※ 同梱テーマ置き場に作成。更新で消したくない場合は SLIDE_DECK_THEMES を設定し --dir で出力を。")
    print("自動推定なので colors/fonts を目視で微調整してください（トークンの意味は references/themes.md）。")
    print(f"使い方: deck.json の meta.theme に \"{args.name}\" を指定して build_deck.py で再ビルド。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

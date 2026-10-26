#!/usr/bin/env python3
"""デッキ新規作成の設定フォーム（Claude の show_widget 用 HTML）を組み立てる。

create-deck スキルが新規作成の最初に 1 回だけ表示する。ユーザーは選んで送信するだけで、
回答は「スライドの設定 — Theme: … · Audience: … · …」の 1 行で Claude に届く
（ホストの elicitation フォーム。選択・送信はホスト側が処理するので <script> は使わない）。

- テーマの選択肢は探索順（SLIDE_DECK_THEMES → <deck_dir>/themes → 同梱）で見つかったテーマすべて。
  各テーマの色トークンから表紙と本文のミニプレビューを描く
- 依頼文から読み取れた値は --defaults-file（JSON）で渡すと選択済みになり、
  --from-request に挙げた項目には「依頼文から反映」の印が付く

使い方:
  python tools/build_settings_widget.py --out deck_widget.html \\
      [--deck-dir <deck_dir>] [--defaults-file defaults.json] [--from-request count audience]
defaults.json のキー: theme / audience / purpose / story / count / tone / visuals / output / notes
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import build_deck  # noqa: E402

AUTO = "おまかせ"
FIELDS = ("theme", "audience", "purpose", "story", "count", "tone", "visuals", "output", "notes")

# (値, Tabler アイコン, 補足)
AUDIENCE = [
    (AUTO, "ti-sparkles", "依頼内容から決める"),
    ("経営層・意思決定者", "ti-briefcase", "結論を先に、簡潔に"),
    ("実務者・現場", "ti-tools", "手順・具体例を厚めに"),
    ("顧客・社外", "ti-building", "背景から丁寧に"),
    ("社内メンバー全般", "ti-users", "前提をそろえて共有"),
    ("研修の受講者", "ti-school", "用語から段階的に"),
]
PURPOSE = [
    (AUTO, "ti-sparkles", "依頼内容から決める"),
    ("承認・予算をもらう", "ti-signature", "判断に必要な根拠をそろえる"),
    ("方針を合意する", "ti-arrows-join", "選択肢と推奨を示す"),
    ("理解して実行してもらう", "ti-list-check", "やり方を順に示す"),
    ("状況を共有する", "ti-report", "現状・課題・次の手"),
]
STORY = [
    (AUTO, "ti-sparkles", "内容に合う型を選ぶ"),
    ("SCQA", "ti-route", "状況→複雑化→問い→答え"),
    ("PREP", "ti-target-arrow", "結論→理由→具体例→結論"),
    ("課題→原因→打ち手→効果", "ti-stairs-up", "業務改善・施策提案"),
    ("比較検討", "ti-scale", "複数案から選んでもらう"),
]
VISUALS = [
    (AUTO, "ti-sparkles", "内容に合わせる"),
    ("図解を多めに", "ti-sitemap", "構成図・フロー・表で見せる"),
    ("文字中心で簡潔に", "ti-align-left", "箇条書きと表が中心"),
    ("画像・スクショを使う", "ti-photo", "手元の画像を配置する"),
]
COUNT = [AUTO, "5枚前後", "8〜12枚", "15枚前後", "20枚以上"]
TONE = [AUTO, "フォーマル", "カジュアル"]
OUTPUT = [
    ("HTML＋PPTX", '<rect x="3" y="7" width="20" height="14" rx="1"/><rect x="25" y="13" width="20" height="14" rx="1"/>'),
    ("HTMLのみ", '<rect x="6" y="5" width="36" height="26" rx="2"/><path d="M6 11h36"/>'),
    ("HTML＋PPTX＋PDF", '<rect x="2" y="9" width="14" height="18" rx="1"/><rect x="17" y="9" width="14" height="18" rx="1"/>'
                       '<path d="M32 9h10l4 4v14H32z"/>'),
]

E = html.escape
CARD = ("border-radius:12px; padding:12px 14px; display:flex; gap:10px; align-items:flex-start; text-align:left; "
        "min-width:170px; box-shadow:0 1px 2px rgba(0,0,0,0.04)")
TILE = ("width:132px; border-radius:12px; padding:12px 8px; display:flex; flex-direction:column; align-items:center; "
        "gap:8px; box-shadow:0 1px 2px rgba(0,0,0,0.04)")
BADGE = ("margin-left:8px; font-size:11px; font-weight:400; background:var(--bg-accent); color:var(--text-accent); "
         "padding:1px 8px; border-radius:var(--radius)")


def list_themes(deck_dir):
    """探索順で見つかったテーマ（name, colors, fonts）を、先に見つかったものを優先して返す。"""
    seen, out = set(), []
    for d in build_deck.theme_dirs(deck_dir):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            name = p.stem
            if name in seen:
                continue
            seen.add(name)
            try:
                theme = build_deck.load_theme(name, build_deck.theme_dirs(deck_dir))
            except SystemExit:
                continue   # 壊れたテーマは選択肢に出さない
            out.append({"name": name, "colors": theme.get("colors", {}), "fonts": theme.get("fonts", {})})
    out.sort(key=lambda t: (t["name"] != "default", t["name"]))
    return out


def _hex(colors, key, fallback):
    v = str(colors.get(key, fallback))
    return v if build_deck._HEX_RE.match(v) else fallback


def theme_preview(colors) -> str:
    """表紙と本文のミニプレビュー（96×34 の SVG）。テーマの色そのものを見せるので hex で描く。"""
    c = {k: _hex(colors, k, v) for k, v in (("primary", "#333333"), ("accent", "#888888"), ("background", "#FFFFFF"),
                                            ("on_primary", "#FFFFFF"), ("heading_text", "#222222"), ("text", "#222222"),
                                            ("surface", "#EEEEEE"), ("border", "#CCCCCC"))}
    return (f'<svg width="96" height="34" viewBox="0 0 96 34" aria-hidden="true">'
            f'<rect x="0.5" y="0.5" width="45" height="33" rx="2" fill="{c["primary"]}" stroke="{c["border"]}"/>'
            f'<rect x="5" y="13" width="26" height="3" fill="{c["on_primary"]}"/>'
            f'<rect x="5" y="19" width="16" height="2" fill="{c["on_primary"]}" opacity="0.7"/>'
            f'<rect x="50.5" y="0.5" width="45" height="33" rx="2" fill="{c["background"]}" stroke="{c["border"]}"/>'
            f'<rect x="54" y="4" width="22" height="3" fill="{c["heading_text"]}"/>'
            f'<rect x="54" y="9" width="38" height="1" fill="{c["accent"]}"/>'
            f'<rect x="54" y="13" width="17" height="16" rx="1" fill="{c["surface"]}"/>'
            f'<rect x="73" y="13" width="18" height="16" rx="1" fill="{c["surface"]}"/>'
            f'<rect x="56" y="16" width="11" height="1.5" fill="{c["text"]}"/>'
            f'<rect x="75" y="16" width="12" height="1.5" fill="{c["text"]}"/></svg>')


def _pressed(value, selected) -> str:
    return ' aria-pressed="true"' if value == selected else ""


def _question(text, name, from_request) -> str:
    badge = f'<span style="{BADGE}">依頼文から反映</span>' if name in from_request else ""
    return f'<label class="elicit-question">{E(text)}{badge}</label>'


def pills(name, question, options, selected, from_request, other=False) -> str:
    items = "".join(f'<button type="button" class="elicit-pill" data-value="{E(o)}"{_pressed(o, selected)}>{E(o)}</button>'
                    for o in options)
    other_btn = other_in = ""
    if other:
        is_other = selected not in options and selected not in (None, "")
        other_btn = (f'<button type="button" class="elicit-pill" data-value="その他" data-other'
                     f'{" aria-pressed=\"true\"" if is_other else ""}>その他</button>')
        val = f' value="{E(selected)}"' if is_other else ""
        other_in = (f'<input type="text" class="elicit-other" data-for="{name}" placeholder="例: 本文12枚・持ち時間15分"'
                    f'{val}{"" if is_other else " hidden"}>')
    return (f'<div class="elicit-group">{_question(question, name, from_request)}'
            f'<div class="elicit-pills" data-name="{name}" data-multi="false">{items}{other_btn}</div>{other_in}</div>')


def cards(name, question, options, selected, from_request) -> str:
    items = "".join(
        f'<button type="button" class="elicit-pill" data-value="{E(v)}"{_pressed(v, selected)} style="{CARD}">'
        f'<i class="ti {icon}" style="font-size:18px" aria-hidden="true"></i>'
        f'<span><span style="font-size:13px; font-weight:500">{E(v)}</span><br>'
        f'<span style="font-size:11px; color:var(--text-muted)">{E(sub)}</span></span></button>'
        for v, icon, sub in options)
    return (f'<div class="elicit-group">{_question(question, name, from_request)}'
            f'<div class="elicit-pills" data-name="{name}" data-multi="false">{items}</div></div>')


def theme_tiles(themes, selected, from_request) -> str:
    auto = (f'<button type="button" class="elicit-pill" data-value="{AUTO}"{_pressed(AUTO, selected)} style="{TILE}">'
            f'<i class="ti ti-sparkles" style="font-size:20px; height:34px; line-height:34px" aria-hidden="true"></i>'
            f'<span style="font-size:13px; font-weight:500">{AUTO}</span>'
            f'<span style="font-size:11px; color:var(--text-muted)">内容に合わせる</span></button>')
    tiles = []
    for t in themes:
        font = t["fonts"].get("body")
        font = font[0] if isinstance(font, list) and font else font
        tiles.append(
            f'<button type="button" class="elicit-pill" data-value="{E(t["name"])}"{_pressed(t["name"], selected)} '
            f'style="{TILE}">{theme_preview(t["colors"])}'
            f'<span style="font-size:13px; font-weight:500">{E(t["name"])}</span>'
            f'<span style="font-size:11px; color:var(--text-muted)">{E(str(font or ""))}</span></button>')
    return (f'<div class="elicit-group">{_question("どのテーマ（配色・フォント）で作りますか？", "theme", from_request)}'
            f'<div class="elicit-pills" data-name="theme" data-multi="false">{auto}{"".join(tiles)}</div></div>')


def output_tiles(selected, from_request) -> str:
    items = "".join(
        f'<button type="button" class="elicit-pill" data-value="{E(v)}"{_pressed(v, selected)} style="{TILE}">'
        f'<svg width="48" height="36" viewBox="0 0 48 36" fill="none" stroke="currentColor" stroke-width="1.5" '
        f'aria-hidden="true">{svg}</svg><span style="font-size:13px; font-weight:500">{E(v)}</span></button>'
        for v, svg in OUTPUT)
    return (f'<div class="elicit-group">{_question("何で受け取りますか？", "output", from_request)}'
            f'<div class="elicit-pills" data-name="output" data-multi="false">{items}</div></div>')


HEADER_SVG = ('<svg viewBox="0 0 20 20" fill="currentColor"><path d="M11.586 2a1.5 1.5 0 0 1 1.06.44l2.914 2.914a1.5 1.5 0 0 1 .44 1.06V16.5a1.5 1.5 0 0 1-1.5 1.5h-9a1.5 1.5 0 0 1-1.492-1.347L4 16.5v-13A1.5 1.5 0 0 1 5.5 2zM5.5 3a.5.5 0 0 0-.5.5v13a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V7h-2.5A1.5 1.5 0 0 1 11 5.5V3zm7.04 10.304a.5.5 0 0 1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713.574-1.2.574-.486 0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067a.5.5 0 0 1 .886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527.696.74.696s.519-.18.74-.696m0-4a.5.5 0 0 1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713.574-1.2.574-.486 0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067a.5.5 0 0 1 .886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527.696.74.696s.519-.18.74-.696M12 5.5a.5.5 0 0 0 .5.5h2.293L12 3.207z"/></svg>')
UPLOAD_SVG = ('<svg viewBox="0 0 20 20" fill="currentColor"><path d="M16.5 13a.5.5 0 0 1 .5.5v2a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 15.5v-2a.5.5 0 0 1 1 0v2a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-2a.5.5 0 0 1 .5-.5M10 3a.5.5 0 0 1 .374.168l4 4.5.059.082a.5.5 0 0 1-.732.65l-.075-.068L10.5 4.814V13.5a.5.5 0 0 1-1 0V4.814L6.374 8.332a.5.5 0 0 1-.748-.664l4-4.5.08-.071A.5.5 0 0 1 10 3"/></svg>')


def build(themes, defaults: dict, from_request) -> str:
    d = {k: defaults.get(k) for k in FIELDS}
    sel = lambda k, default=AUTO: d[k] if d[k] not in (None, "") else default  # noqa: E731
    theme_names = {t["name"] for t in themes}
    theme_sel = sel("theme") if sel("theme") in theme_names else AUTO
    notes = E(str(d["notes"] or ""))
    groups = [
        theme_tiles(themes, theme_sel, from_request),
        cards("audience", "誰に向けた資料ですか？", AUDIENCE, sel("audience"), from_request),
        cards("purpose", "聞き終わったあと、何をしてほしいですか？", PURPOSE, sel("purpose"), from_request),
        cards("story", "どの流れで話を組み立てますか？", STORY, sel("story"), from_request),
        pills("count", "何枚くらいにしますか？（表紙・まとめを含む）", COUNT, sel("count"), from_request, other=True),
        pills("tone", "トーンはどちらに寄せますか？", TONE, sel("tone"), from_request),
        cards("visuals", "図解や画像はどのくらい使いますか？", VISUALS, sel("visuals"), from_request),
        output_tiles(sel("output", "HTML＋PPTX"), from_request),
        ('<div class="elicit-group">'
         f'{_question("参考資料や、必ず入れたい内容はありますか？", "notes", from_request)}'
         f'<div class="elicit-files" data-name="materials"><label class="elicit-dropzone">{UPLOAD_SVG}'
         '<span>ファイルを選ぶ</span><input type="file" multiple></label></div>'
         '<textarea class="elicit-textarea" data-name="notes" '
         f'placeholder="参考URL、使いたい数値、入れてほしい論点など">{notes}</textarea></div>'),
    ]
    return ('<h2 class="sr-only">スライドを作る前の設定フォーム。テーマ・聞き手・目的・構成・枚数などを選んで送信する。</h2>'
            f'<form class="elicit"><div class="elicit-header">{HEADER_SVG}<span>スライドの設定</span></div>'
            f'<div class="elicit-body">{"".join(groups)}</div>'
            '<div class="elicit-footer"><button type="button" class="elicit-skip">おまかせで進める</button>'
            '<button type="button" class="elicit-submit">この設定で作成</button></div></form>')


def main():
    build_deck.setup_console()
    ap = argparse.ArgumentParser(description="デッキ新規作成の設定フォーム（show_widget 用 HTML）を作る")
    ap.add_argument("--out", required=True, help="書き出す HTML ファイル")
    ap.add_argument("--deck-dir", help="デッキのディレクトリ（<deck_dir>/themes のテーマも選択肢に入れる）")
    ap.add_argument("--defaults-file", help="依頼文から読み取った値の JSON（キー: " + " / ".join(FIELDS) + "）")
    ap.add_argument("--from-request", nargs="*", default=[], choices=FIELDS, help="「依頼文から反映」の印を付ける項目")
    args = ap.parse_args()
    defaults = {}
    if args.defaults_file:
        defaults = build_deck.load_json(Path(args.defaults_file))
        if not isinstance(defaults, dict):
            build_deck.fail("--defaults-file はオブジェクト形式の JSON にしてください")
    themes = list_themes(Path(args.deck_dir).resolve() if args.deck_dir else None)
    Path(args.out).write_text(build(themes, defaults, set(args.from_request)), encoding="utf-8")
    print(f"widget: {args.out}（テーマ {len(themes)} 種）")


if __name__ == "__main__":
    main()

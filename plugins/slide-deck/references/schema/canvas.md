# `canvas` — 座標指定の自由配置（既存 PPTX の取り込み専用）と取り込み手順

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。

テーマのタイトル・罫線・フッターを付けず、1280×720 の座標に図形・文字・表を直接置く。用途は、既存の PowerPoint 資料を**見た目を崩さず** HTML 化すること（矢羽根付きのガントチャートやスイムレーン図など、他のタイプに当てはまらない自由配置の図）に限る。**`tools/pptx_import.py` で生成するもので、canvas は取り込み結果を直すためのもの。新しい構図は [`pattern`](pattern.md) を使う（canvas の手書きは取り込み結果の修正に限る）**（テーマ切替・共通パーツ・自動フィットが効かないため。新規の図解・スケジュールは `architecture` / `schedule` 等、登録できる構図は `pattern`）。取り込んだ 1 枚を再利用したいときは `pattern_from_pptx.py` で型に起こせる（[pattern.md](pattern.md)）。元 PPTX のマスター上の図形は各スライドの `elements` に展開される。

```json
{ "type": "canvas", "title": "全体スケジュール", "background": "#FFFFFF", "notes": "（任意）",
  "elements": [
    { "x": 280, "y": 280, "w": 51, "h": 21, "geom": "homePlate", "adj": {"adj": 13400},
      "fill": "#FFFFFF", "line": {"color": "#7F7F7F", "width": 0.75},
      "text": {"insets": [0, 0, 0, 0], "anchor": "ctr",
               "paragraphs": [{"align": "ctr", "runs": [{"text": "CRP", "size": 9.33, "color": "#000000", "font": ["Meiryo UI"]}]}]} },
    { "x": 68, "y": 262, "w": 1153, "h": 0, "geom": "line", "line": {"color": "#919191", "width": 0.75, "dash": "dash"} },
    { "kind": "table", "x": 40, "y": 250, "w": 1180, "h": 400, "cols": [200, 160], "rows": [ {"h": 40, "cells": [ ... ]} ] },
    { "kind": "svg", "x": 446, "y": 362, "w": 40, "h": 38, "svg": "<svg ...>…</svg>", "alt": "繰り返し" },
    { "kind": "placeholder", "x": 128, "y": 0, "w": 528, "h": 321, "label": "画像（スクリーンショット）" }
  ] }
```

- 単位はすべて px（文字サイズも px。pt × 4/3）。要素は配列の順に重なる（後ろほど手前）
- `background` は `#RRGGBB`。色は `"#RRGGBB"`（`#RGB` の 3 桁も可）か `{"color": "#RRGGBB", "alpha": 0.5}`（テーマトークンは使わない＝元資料の色をそのまま持つ）。色・`anchor` / `align` / `dash` / `cap` / 矢じりの値・フォント名・パス命令はビルド時に検証され、規定外の値はエラーになる
- **検証**: 数値のキー（x y w h size width lineHeight …）・table の cols / rows・backdrop の grid などの型を検査し、問題を 1 件で止めず全件まとめて出す（`elements[0].shadow はオブジェクトで指定してください` のように要素とキー名つき）。`w` / `h` の負の値、`line` / `shadow` がオブジェクトでない、`fill` が色の文字列でもオブジェクトでない、`font` が文字列でも文字列の配列でもない、はビルドエラー。XML で使えない制御文字（`\x00-\x08` `\x0b` `\x0c` `\x0e-\x1f`・孤立サロゲート）は文字・`name`・`alt` から黙って取り除く。
- PPTX に出力すると図形・線・表は PowerPoint ネイティブの図形になり、1つずつ編集できる（`svg` / `backdrop` は画像、`group` は解除して子要素を個別に配置）

| kind | 内容 |
|---|---|
| `shape`（既定） | 図形。`geom` は `rect`（既定）/ `roundRect` / `ellipse` / `triangle` / `homePlate`（矢羽根）/ `chevron` / `flowChartDecision` / `flowChartMerge` / `flowChartDocument` / `can` / `flowChartMagneticDisk` / `borderCallout1` / `borderCallout2` / 線（`line` / `straightConnector1` / `bentConnector2`〜`5`）/ `custom`（`path` に `{"cmds": [["M",x,y],["L",x,y],["C",…],["Z"]], "fill": bool, "stroke": bool}` の配列）。`adj` は PowerPoint の調整値（`{"adj": 13400}` 等）。`rot`（度）/ `flipH` / `flipV` / `shadow`（`{dx, dy, blur, color}`。HTML と PPTX の両方に出る。塗りか線のある図形だけ）も可 |
| `table` | 表。`cols`（列幅 px）と `rows`（`{"h", "cells"}`）。セルは `paragraphs` / `fill` / `pad`（[左,上,右,下]）/ `anchor`（`t`/`ctr`/`b`）/ `borders`（`l`/`r`/`t`/`b` に線指定）/ `span` / `rowspan` / `merged`（結合で隠れるセル。`"h"` か `"v"`）/ `vert`（縦書き）/ `nowrap`（折り返さない）/ `clip`（はみ出しを隠す） |
| `svg` | ベクターアイコン（インライン SVG。要素・属性とも許可リスト方式で浄化され、`script` / `foreignObject` / イベント属性 / 外部参照（`#` 以外の href・`url()`）は除去される。DOCTYPE を含むものや解析できないものはエラー。id は衝突しないよう自動で接頭辞が付く）。PPTX では PNG 化して貼る |
| `image` | 画像。`{"kind":"image","x","y","w","h","path":"assets/photo.png","fit":"cover"\|"contain","alt","rot"}`。`path` はデッキからの相対パス（`..`・絶対パス・未対応の拡張子・存在しないファイルはビルドエラー）。`cover` は枠いっぱいに拡大して余りを切り抜き、`contain` は枠の中央に収める。HTML は埋め込み、PPTX は画像として配置（編集で差し替え可）。PNG / JPG / SVG に対応 |
| `backdrop` | 全面背景の写真の近似（`grid`: `{"cols", "rows", "colors": [...]}` の色格子をぼかして描く。画像は埋め込まない） |
| `placeholder` | 埋め込まない画像の代わりの枠（`label` を中央に表示） |
| `group` | 回転したグループ（`rot` / `origin`: [cx, cy] / `children`） |

- `fill` は色のほか `{"gradient": {"angle": 90, "stops": [[0, "#…"], [100, "#…"]]}}` / `{"pattern": "ltDnDiag", "fg": "#…", "bg": "#…"}`
- `line` は `{"color", "width", "dash"（dash/sysDash/sysDot/lgDash…）, "cap", "head"/"tail": {"type": "triangle|arrow|stealth|oval|diamond", "w", "len"}}`
- `text` は `{"insets": [左,上,右,下], "anchor", "anchorCtr", "wrap": false（折り返しなし）, "vert": true（縦書き。上から下）/ "vert": "270"（下から上へ読む。スイムレーンのレーン見出しなど）, "rot", "paragraphs": [...]}`。文字は図形ごとの文字領域（楕円なら内接矩形、ひし形なら中央の半分など PowerPoint と同じ）に置かれる
- 段落は `{"align": "l|ctr|r|just", "lineHeight": 1.0（行間100%の倍率）| "lineHeightPx", "spaceBefore", "spaceAfter", "marL", "indent", "bullet": {"char", "color", "size", "font"}, "runs": [...]}`。ランは `{"text", "size", "bold", "italic", "underline", "strike", "baseline", "color", "highlight", "font": ["Arial", "Meiryo UI"]}` か改行 `{"br": true}`

**取り込み手順**（既存 PPTX → canvas デッキ）:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/pptx_import.py" <src.pptx> --into <deck_dir> [--title "…"] [--slides 1 5]
# ↑ deck.json が既にあると書き込まずに終了する（丸ごと置き換えになるため）。承認後に --confirm を付けて再実行（元は deck.json.bak に退避）
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir>
pwsh "${CLAUDE_PLUGIN_ROOT}/tools/export_pptx_png.ps1" -Src <src.pptx> -OutDir <deck_dir>/_work/ref   # Windows + PowerPoint で元資料を画像化
python "${CLAUDE_PLUGIN_ROOT}/tools/compare_ref.py" <deck_dir> <deck_dir>/_work/ref                  # 上=元・下=HTML の比較画像と差分スコア
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>                                       # 見切れ・スライド外へのはみ出し
```
- ラスタ画像（スクリーンショット等）は埋め込まず `placeholder` にする。SVG アイコンはベクターのまま、全面背景の写真は `backdrop` で近似、埋め込み Excel はブックの表示範囲（`oleSize`）を表にする（`openpyxl` が必要。範囲が 300行 × 60列・6000セルを超える場合は枠になる）
- `check_layout.py` は canvas では「見切れ（clip）」「スライド外へのはみ出し（bleed）」だけを判定する（重なり等は元資料の配置そのものなので判定しない）。`pattern` から展開したスライドは通常のタイプと同じ検査を受ける
- 4:3 など 16:9 以外のスライドは、縦横比を保って 1280×720 の中央に拡縮して取り込む。取り込み結果のメモ用キー（`meta._source` / `meta._generator` / スライドの `_source_page`）は先頭が `_` なので未知キー警告の対象外
- **上書きの承認**: `deck.json` が既にあると `--into` は書き込まずに終了する。承認を得てから `--confirm`（[../approval-gates.md](../approval-gates.md)）

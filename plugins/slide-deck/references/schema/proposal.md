# 提案書向けタイプ（summary / reasons / statement / row_matrix / org / house / cycle / kpi_tree）

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。**共通パーツ**（`conclusion` 結論の帯 / `source` 出典の行）は索引にある。**アイコン**（`icon`）の書き方はこのファイルの末尾。

## 提案書向けタイプ共通

提案書・報告書の定型ページを、人が作った提案書と同じ型で描くタイプ。レイアウトは `tools/proposal_engine.py` が計算し、HTML と PPTX の両方でネイティブ図形（PowerPoint では四角・矢羽根・線を1つずつ編集できる）になる。文字の大きさはテーマのフォントの実測字幅で行数を見積もり、枠に収まる最大のサイズを自動で選ぶ（候補表 `body.sizes` から。**最小の候補でも収まらないときは警告**を出す。`meta.density` で候補の上限が変わる。規則は [autofit.md](autofit.md)。`org` は候補表も密度のプリセットも持たない）。`statement` 以外はタイトル・罫線・リード・フッターを持ち、本文は `body` 領域（lead が無ければ `y_no_lead` まで上に詰める）に描く。色・寸法は `style.body.<トークン>` で上書きできる（トークン名は `templates/layouts/default.json` の各タイプの `body`）。

## `summary` — 要旨（番号の箱＋要点＋説明の行）
```json
{ "type": "summary", "title": "ご提案の背景と要旨", "lead": "（任意）",
  "items": [ { "lead": "背景｜…", "text": "説明" }, { "lead": "課題｜…", "text": "…" } ],
  "source": "（任意）出典", "conclusion": "（任意）結論の帯" }
```
提案書の冒頭で結論と骨子を示す。各行は左に番号の箱（`primary`）、右に要点（太字）と説明。行の高さはすべて同じ。目安: **3〜6行**（7行以上は警告）。`items` に文字列だけを並べると要点だけの行になる。

## `reasons` — 選ばれる理由（課題 × 強みの対応）
```json
{ "type": "reasons", "title": "アクセンチュアが選ばれる理由",
  "left_heading": "貴社の課題", "right_heading": "選ばれる理由",
  "issues":    [ { "title": "判断材料が少ない", "text": "新機能で事例がない" } ],
  "strengths": [ { "title": "一次情報を読み解き…", "text": "（任意）", "items": ["根拠1", "根拠2"], "label": "a" } ] }
```
左に相手の課題（番号付き）、右に自社の強み（`label` 省略時は a/b/c…）を同じ行に並べ、間を灰色の三角でつなぐ。`issues` と `strengths` は同じ順で対応させる。目安: **3行前後**（6行以上は警告）。

## `statement` — 言い切り（濃色の面に大きな一文）
```json
{ "type": "statement", "kicker": "本提案の結論", "message": "Modsは、統制を先に固めた組織だけが、安全に増やせる",
  "support": "（任意）補足の一文" }
```
物語の転換点に置く全面ページ（タイトル・罫線・フッターなし）。`message`（無ければ `title`）を大きく、`kicker` を上に小さく、`support` を下に置く。長い一文は自動で文字を縮める。デッキに2〜3枚までが目安。領域: `background`（`fill`）/ `kicker` / `message` / `support`。`variant`（`center` / `left-bar` / `mark`）と、画像・色面の `background` キーは [hero.md](hero.md)。

## `row_matrix` — 行見出し × 列の整理表
```json
{ "type": "row_matrix", "title": "フェーズ別の実施事項", "header_style": "arrow",
  "corner": "（任意）左上の見出し", "columns": ["Phase 0", "Phase 1", "Phase 2"], "col_ratios": [1, 1, 1],
  "emph_col": 0,
  "rows": [ { "label": "統制", "cells": [ ["現状の棚卸し", "管理設定の設計"], "文字列も可", { "text": "本文", "items": ["箇条書き"] } ] } ] }
```
左の行見出しの帯と上の列見出しで、観点×対象（機会とリスク、工程×領域、前提・参考資料など）を整理する。セルは文字列・箇条書きの配列・`{text, items}` のいずれか。`header_style: "arrow"` で列見出しを工程の矢羽根（五方向）にする。`emph_col`（0 始まり）で主張する列を淡い色で塗る。`columns` を省略（または `[""]`）すると、行見出し＋1列の一覧（前提条件・参考資料など）になる。行の高さは中身に合わせて配分し、余りは均等に足す。目安: **6行以内**。

## `org` — 体制図（左右の組織ツリー＋提案範囲）
```json
{ "type": "org", "title": "推進体制", "legend": "(F) フルタイム　(P) パートタイム",
  "left":  { "title": "貴社", "nodes": [ { "id": "po", "title": "プロジェクトオーナー", "name": "開発本部長" },
                                        { "id": "pm", "parent": "po", "title": "貴社PM", "name": "開発基盤部" } ] },
  "right": { "title": "アクセンチュア", "scope": "ご支援範囲",
             "nodes": [ { "id": "apm", "title": "プロジェクトマネージャー", "name": "1名 (F)", "members": "（任意）" } ] },
  "links": [ { "from": "po", "to": "apm", "label": "ステアリング" } ] }
```
左右（片方だけでも可）に組織のツリーを描く。ノードは `id` と `parent`（同じ側の親の id）で親子を表し、見出し帯（左は `muted`、右は `primary`）＋本文（`name` / `members`）の箱になる。親子はカギ線で結ぶ。`scope` を書いた側は破線の枠（見出しの列と同じ幅で、本文領域の中に収まる）で囲み、文字列なら札（既定「ご支援範囲」）を枠の**内側の右下**に付ける（幅は文字に合わせる。札の分の高さは左右どちらにも空け、左右の根の高さをそろえる）。`links` は組織をまたぐ連携（点線＋ラベル）。連携の名前は地の色の札になり、背後の破線枠・線が文字を貫かない。id の重複・存在しない parent / links はビルドエラー。目安: 各側 **3階層・1段4ノード以内**。


## `house` — 全体像（屋根・柱・土台）
```json
{ "type": "house", "title": "ご提案の全体像",
  "roof": { "title": "目指す姿｜安全に増やせるmod基盤", "text": "（任意）補足" },
  "pillars": [ { "title": "① 統制", "items": ["入口を絞る", "成果物：方針書"] }, { "title": "② 構築", "text": "本文でも可" } ],
  "foundations": [ { "title": "土台", "text": "管理設定の配布" }, "文字列も可" ] }
```
屋根（台形の帯に目指す姿）、柱（見出し帯＋箇条書きの列）、土台（全幅の帯。最後が一番下）で提案の全体像を示す。柱の文字は収まる大きさに自動で縮む。柱の枠は「中身の 1.5 倍（下限 110px）」までに抑え、屋根・柱・土台の全体を本文領域の上下中央に置く（中身が多いときは領域いっぱいまで使う。`body.fit_content: false` で従来どおり領域いっぱい。`pillar_k` `pillar_min_h`）。柱の中身が 1〜2 行だと、枠の下が空きやすい（項目を足すか `pillar_min_h` を下げる）。目安: **柱3〜4本**（6本以上は警告）。

## `cycle` — 循環（中央の円＋円弧の矢印＋段のパネル）
```json
{ "type": "cycle", "title": "定着の仕組み", "center": "毎月",
  "stages": [ { "title": "計測", "items": ["使用状況", "失敗"] }, { "title": "改善", "text": "本文でも可" }, { "title": "審査" }, { "title": "配布" } ] }
```
中央に円弧の矢印の輪（番号丸つき）、左右に段のパネルを置く。右列が前半（上から）、左列が後半（下から）で、時計回りに読める。`center` は輪の中央の文字（任意）。目安: **3〜6段**（2段以下はビルドエラー、7段以上は警告）。
パネルに余裕があるとき、本文の文字は `types.cycle.body.grow_sizes`（既定 `[20, 19, 18, 17, 16]`。talk `[24 … 19]`・read `[16, 15]`）の大きい方から試して、パネルの高さに収まり折り返しが悪くならない最大の大きさになる。`style.body.sizes` を書いたときは動かさない。`grow_sizes: []` で止まる（[autofit.md](autofit.md) の「中身が少ないときの自動調整」）。

## `kpi_tree` — KPI ツリー（目標 → 方向性 → KPI＋目標値＋測り方）
```json
{ "type": "kpi_tree", "title": "期待する効果とKPI", "root": "mod基盤の価値",
  "headers": ["目標", "施策の方向性", "KPIと目標値", "", "測り方・具体例"],
  "branches": [ { "title": "止める（統制）", "kpis": [ { "title": "未承認modの稼働を無くす", "value": "0台", "note": "月次で棚卸し" } ] } ] }
```
左の目標から施策の方向性へ、方向性から KPI の行へカギ線でつなぎ、各 KPI に目標値（大きな数字）と測り方を添える。`headers` は列の見出し（4つ目は目標値の列で通常は空）。`note` の代わりに `items`（箇条書き）も可。目安: **KPI 6行以内**。領域の幅が列の合計（目標・方向性・KPI・目標値＋間隔＋測り方の最低幅 200px）に足りないときは、列幅と間隔を同じ比率で縮める（下限 0.5 倍。目標値は途中で折り返さない大きさまで下げる）。合成ブロックに置くなら 3 分の 2 幅（約 741px）以上にする（文字は 11〜12px になる）。半幅（約 556px）は最低幅（586px）に足りず fail する。下限まで縮めても入らない幅の合成ブロックは fail（「幅 NNNpx に収まりません（列を半分まで縮めても、最低 MMMpx 要る）」）。

## アイコン（`icon`）

提案書向けタイプと `cards` の項目には `icon` を書ける。値は同梱アイコンの名前（例 `"shield-check"`）か概念語（例 `"セキュリティ"` / `"q:統制 安全"`）で、概念語なら最も近いアイコンが選ばれる（似た概念は同じ絵を使い回す）。アイコンは Tabler Icons（MIT License、`templates/icons/LICENSE-tabler.txt`）から定番の約70点だけを同梱しており、HTML でも PPTX でも線だけのネイティブ図形になる（PowerPoint で色・太さを変えられる）。合うアイコンが無い指定はビルド時に警告する。
- 置ける場所: `summary` の `items[].icon`（帯の左）/ `reasons` の `strengths[].icon`（強みの記号の右）/ `house` の `pillars[].icon`（柱の見出しの左）/ `cycle` の `stages[].icon`（パネルの右上）/ `cards` の `cards[].icon`（カードの右上）
- 一覧と検索: `python "${CLAUDE_PLUGIN_ROOT}/tools/icon_engine.py" --list`、`python "${CLAUDE_PLUGIN_ROOT}/tools/icon_engine.py" "コスト削減"`、一覧画像は `--sheet icons.png`
- アイコンは脇役として小さく（22〜28px）置く。アイコンだけで中身を語らせない。並列・循環・全体像のページに絞り、`steps` や表・見積・スケジュールには入れない

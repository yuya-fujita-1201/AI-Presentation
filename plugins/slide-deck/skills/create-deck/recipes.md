# 最小の書き方と、内容が薄いときの逃げ道

`SKILL.md` の「タイプの選び方」で選んだタイプを、**最小のキーで書く早見**。ここで足りるなら詳細（`references/schema/*.md`）は読まなくてよい。キー・警告・既定値の詳細は、困ったときだけ各ファイルを開く。

（`${CLAUDE_PLUGIN_ROOT}` は `SKILL.md` に書かれた実パスに読み替える。この補助ファイルでは変数が展開されない。）

## 1. 最小の書き方

下の例はすべてそのまま deck.json の `slides` に貼ってビルドでき、警告が出ないことを確かめてある（文言は例。数字は材料の値に替える）。

```json
{ "type": "kpi", "title": "見積もりの作成は 3 日から 1 日に縮まる",
  "items": [ { "value": "1", "unit": "日", "label": "見積もりの作成", "from": "3", "delta": "−2日", "good": "down" } ] }
```
`kpi`: 大きな数字。2〜4 件並べられる。`from` `delta` `good` は任意。数字が決まらないときは `"value": "【要確認】"`。詳細は `references/schema/visual.md`。

```json
{ "type": "split", "panel": { "fill": "primary", "kpi": { "value": "27", "unit": "%", "label": "受注率の目標（いまは 22%）" } },
  "title": "受注率を 5pt 上げ、見積もりを 2 日縮める",
  "blocks": [ { "type": "kpi", "items": [ { "value": "1", "unit": "日", "label": "見積もりの所要日数", "from": "3", "delta": "−2日", "good": "down" } ] } ] }
```
`split`: 左に色面のパネル（主役の数字か一文）、右に根拠の図表。パネルは `kpi` だけにして `title` は足さない（両方書くと「主役は 1 つ」の警告）。本文側は kpi・chart・table など図表が向く。**短い bullets だけを置くと下が大きく空く**。詳細は `references/schema/composite.md`。

```json
{ "type": "composite", "title": "営業企画が旗を振り、情シス 1 名が支える", "arrange": "two",
  "blocks": [ { "type": "cards", "columns": 1, "cards": [ { "heading": "営業企画", "body": "旗振り役" }, { "heading": "情シス", "body": "1 名が付く" }, { "heading": "試行部署", "body": "5 月に決める" } ] },
              { "type": "kpi", "items": [ { "value": "1,200", "unit": "万円", "label": "初年度の費用（概算）" } ] } ] }
```
`composite`: 2〜3 個のブロックが 1 つの主張を支えるとき。`arrange` は `two`（左右同じ幅）/ `main-side`（左を広く）/ `top-bottom`（上下）。座標は書かない。詳細は `references/schema/composite.md`。

```json
{ "type": "closing", "variant": "contact", "title": "5 月の試行開始をご判断ください", "message": "初年度の費用は 1,200 万円ほど",
  "bullets": [ "4 月: 準備", "5 月: 2 部署で試行", "7 月: 全社展開" ] }
```
主役の締め（`closing` の `contact`）。右の白い箱は幅約 420px（全角 18 字前後）なので、1 行を短く書く。表紙・章扉は `"variant": "left-band"`（表紙）/ `"number"`（章扉）。種類と使いどころは `references/schema/hero.md`。

```json
{ "type": "pattern", "pattern": "numbered-columns", "title": "営業の足を止めている課題は 3 つある",
  "slots": { "items": [ { "head": "見積もりが遅い", "body": "作成に 3 日かかる" }, { "head": "進捗が見えない", "body": "状況が担当者の頭の中" }, { "head": "失注から学ばない", "body": "理由を誰も振り返らない" } ] } }
```
型（`pattern`）: 名前とスロットだけ。使う型は `pattern_engine.py show <名前>` の例を写して中身を替える。

## 2. 内容が薄いときの逃げ道

材料に無い根拠は足せない（作らない原則）。空きや小さい文字の警告が出たら、**内容を足さずに、タイプか構成を替える**。

| 状況 | やること |
|---|---|
| 20 字以内の短い項目が 3〜5 個（課題・原則・手順） | `cards` にせず `numbered-columns`（または `numbered-list`）の型。文字が大きくなり、警告なしで収まる。`icon-grid` は 3 個だと下が空くことがある。`cards` は薄いと文字を最大 1.6 倍に大きくして箱を低く詰めるが、上下が大きく空き、警告も出ない（目で見る） |
| 短い項目（体制・担当）と 1 つの数字 | `composite` の左に `cards`（`columns: 1`）、右に `kpi`（上の例）。または `split` のパネルに数字、本文に `cards` |
| 3 項目以下の `bullets` に `frame: "box"` を付けたら「枠の中身が少なく…」が出た | `frame` を外す。それでも薄いなら、体制は `org` か `cards`、2 つのブロックとも数字・図にする |
| 短い項目の枚が続いて、どれも下が空く | 前後の枚と 1 枚に統合する。`density` を `read` にしても空きは埋まらない（`outline.md` の density の項） |
| 根拠が足りず `empty-bottom` が消えない | 枚を統合するか、いったん要点を 1 行の `statement` にして次の枚の根拠につなぐ。空きのために材料に無い数字・事例を足さない |

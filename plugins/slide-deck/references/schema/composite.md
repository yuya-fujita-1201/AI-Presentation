# `composite` / `split` — 1 枚に図・要点・数字を並べる、色面や画像のパネル＋本文

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。`composite` は本文領域を格子に分けて**複数のブロック**（図解・表・グラフ・要点・数字…）を置く。`split` は端まで届く**色面か画像のパネル**と、残りの領域の本文（`composite` と同じブロック）を組み合わせる。どちらも座標は書かない。ブロックごとに文字の大きさ・表の行高・図の配置を、そのブロックの大きさで自動フィットする（縮小画像にはしない）。

## いつ使うか（使うか、2 枚に分けるか）

- **使う**: 「図と、その要点」「数字と、その内訳」「現状と対策」のように、**2〜3 個のブロックが 1 つの主張を支える**とき。聞き手が視線を行き来して 1 つの結論に着く構図。
- **2 枚に分ける**: ①ブロックが 4 個を超える ②どのブロックも文字が 12〜14px まで縮む（warn / note が出る）③ブロックごとに別の主張がある ④図解の線やラベルが重なる（label-collision が出る）。迷ったら 2 枚にして、1 枚目に図、2 枚目に要点と表を置く。
- 1 つのブロックに長い文章を入れない（`text` は 3〜4 行まで。長い説明は `notes` か別スライド）。主役は 1 つ: `emphasis` を付けるか、`arrange` の主（`main-side` の左など）に置く。同じ大きさのブロックを並べるなら、全部同じ種類（cards か bullets）でそろえる。
- **短い話（体制・担当の 3 項目など）と数字の組み合わせ**: 3 項目以下の `bullets` に `frame: "box"` を付けない（付けると「枠の中身が少なく…」が出る。外しても `empty-band` が出ることがある）。`cards`（`columns: 1`）を左、`kpi` を右に置くと警告なしで収まる（`skills/create-deck/recipes.md`）。`split` の本文側に短い bullets だけを置くと下が大きく空くので、数字・図表を置く。
- **中身が少ないブロックは、ビルドが整える**（`autofit: false` でなければ）: 文字を大きくし（折り返しが悪くならない範囲）、箱（`frame: "box"`）つきの bullets / text は本文を箱の縦中央に置く（小見出しがあれば小見出しと本文を 1 つの塊にして中央に）。同じスライドの bullets・text・steps・cards は文字の倍率をそろえる。cards は列数を書いていなければ、文字がいちばん大きく読める列数を選び直す（4 枚は 2 × 2。細い列の 3 枚は縦 3 段）。steps は幅 600px 以上の主側で枠の高さいっぱいに広がり、項目は見出しの直下に置く。表は行が少ないとき行の高さだけでなくセルの文字も 16px（talk 18px）まで大きくする。図解は図を自然な大きさで組んで同じ倍率で拡大する。倍率・上限・トークンは [autofit.md](autofit.md) の「中身が少ないときの自動調整」、止め方はブロックの文字の大きさを `style` に書くか `autofit: false`。
- **それでも空くとき**: 「枠の中身が少なく、下の約Npx が空きます」の warn は、**自動で整えられなかったときだけ**出る（`autofit: false`・ブロックに `valign` を書いた・表を箱に入れた）。整えられる場合は出ない。`steps` は横並びなので細いブロックに 3 段以上入れない。縦に長いブロックに薄い steps を置くと、枠の高さいっぱいに広がっても項目の文字は 16〜20px 止まりで、`check_visual.py` の `empty-bottom` が残ることがある。steps は横に長く低いブロックに置くか、段の中身（`items`）を足すか、`bullets` にする。

## `composite` — 書き方

```json
{ "type": "composite", "title": "新基盤は 3 層で、移行は 2 段階で進める", "lead": "画面・API・データを分け、切り替えの影響を層ごとに閉じ込める",
  "arrange": "main-side",
  "blocks": [
    { "type": "architecture", "heading": "新基盤の構成", "legend": false, "nodes": [ … ], "edges": [ … ] },
    { "type": "bullets", "heading": "ポイント", "frame": "box", "bullets": ["画面は既存のまま、API だけ入れ替える", "データは二重書き込みで 1 か月検証する", "切り替えは夜間 1 回、戻せる手順を先に用意する", "旧 API は第 2 段階の終わりに止める"] }
  ],
  "conclusion": "第 1 段階は 3 か月で完了する見込み", "source": "出典: 基盤刷新 PMO（2026 年 10 月）" }
```

```json
{ "type": "composite", "title": "経理と営業企画で、削減の 6 割を占める", "arrange": "top-bottom", "rows": [2, 3],
  "blocks": [
    { "type": "kpi", "items": [ { "value": "2.1", "unit": "時間", "label": "作成時間", "from": "6.5", "delta": "−68%", "good": "down" }, { "value": "9", "unit": "%", "label": "差し戻し率", "from": "22", "delta": "−13pt", "good": "down" } ] },
    { "type": "table", "heading": "部署別の削減時間（月）", "columns": ["部署", "現状", "導入後", "削減"], "rows": [["経理", "142時間", "56時間", "−86時間"], ["営業企画", "118時間", "44時間", "−74時間"], ["人事", "96時間", "55時間", "−41時間"]] }
  ] }
```

見出し（eyebrow / title / 罫線 / lead / フッター）と結論帯・出典は、他のタイプと同じものを 1 回だけ描く。

### スライド直下のキー

| キー | 内容 |
|---|---|
| `blocks` | ブロックの配列（必須。**2〜4 個が目安**。1 個だけは warn、7 個以上は warn） |
| `arrange` | 配置の名前（下の図）。`columns` / `rows` を書けばそちらが優先 |
| `columns` | 列の比率の配列（例 `[3, 2]`。0 より大きい有限の数）。省略時は `arrange`、無ければブロック数から決める（1: 1 列 / 2: 2 列 / 3: 3 列 / 4: 2×2 / 5 以上: 3 列。最後の行に余りが出るときは、その行の最後のブロックを自動で広げる） |
| `rows` | 行の比率の配列（例 `[1, 1]`）。省略時は `arrange` の行数、無ければ置ききれる行数を自動で足す（**最大 12 行**）。`arrange` を書くと行は名前の定義で固定され自動では増えない（ブロックが多すぎるときは `arrange` を外すか `rows` を書く） |
| `title` `lead` `eyebrow` `conclusion` `source` `notes` `density` `autofit` `relation` `style` | 他のタイプと同じ |

ブロックは**書いた順に左上から右へ、行を折り返して**置く。位置を指定したいブロックだけ `col` `row`（0 始まり）と `col_span` `row_span` を書く（明示した位置が先に置かれ、残りは空いている最初の場所に入る）。**x / y / w / h は書かない**（書くと無視して warn）。ブロック間の間隔は全部同じ（既定 24px。`style.body.gap`、列と行で分けるなら `col_gap` / `row_gap`）。

```
two             [ 1 | 2 ]                       three        [ 1 | 2 | 3 ]          four   [ 1 | 2 | 3 | 4 ]
main-side       [ 1 (3) | 2 (2) ]               side-main    [ 1 (2) | 2 (3) ]
top-bottom      [ 1 ] / [ 2 ]                   main-bottom  [ 1 (高さ 2) ] / [ 2 (高さ 1) ]     top-main  [ 1 (高さ 1) ] / [ 2 (高さ 2) ]
2x2             [ 1 | 2 ] / [ 3 | 4 ]           3x2          [ 1 | 2 | 3 ] / [ 4 | 5 | 6 ]
main-side-stack [ 1 (縦に全高) | 2 ]            stack-main   [ 1 | 3 (縦に全高) ]
                [                | 3 ]                       [ 2 |                ]
top-wide        [ 1 (横にまたがる) ]            bottom-wide  [ 1 | 2 ]
                [ 2 | 3 ]                                    [ 3 (横にまたがる) ]
```
`columns` / `rows` を直接書くと名前より優先する（名前の「置き場所」は無視され、自動配置になる）。未知の名前は候補つきで fail。

### ブロックに使えるタイプ

HTML と PPTX の両方でビルドし、LibreOffice の描画と HTML の PNG で確かめたもの（PowerPoint 実機は未確認）。

| 種類 | タイプ | 備考 |
|---|---|---|
| 合成専用 | `text`（`text`: 改行で段落／`paragraphs`）、`callout`（`text`: 強調の一文、`note`: 補足）、`image`（`path` `fit: contain / cover` `caption` `alt`） | スライドのタイプとしては使えない |
| 文字・表 | `bullets` `table` `code` | code の `annotations` は無視して warn |
| 箱 | `cards` `steps` `matrix` `status_table` | status_table の凡例はブロックの上（`legend: false` で消す） |
| 数字・グラフ | `kpi` `chart` | |
| 登録した構図 | `pattern`（**body 枠のパターンだけ**） | 全面（full 枠）の型は fail。幅の目安は [pattern.md](pattern.md) の一覧の「ブロック」列 |
| 提案書系 | `summary` `reasons` `row_matrix` `house` `cycle` `org` `kpi_tree` | `kpi_tree` は狭いと列幅を縮めるが、**半幅（約 556px）では列を半分まで縮めても入らず fail する**（最低 586px。「ブロックを広げる…」）。3 分の 2 幅（約 741px）では HTML・PPTX とも崩れずに描くが、文字は 11〜12px で、短い列見出しが語の途中で折れることがある。`col_span` で 2 列にまたがせるか、単独のスライドに置く。`org` は狭いと文字が小さくなる（warn） |
| 図解 | `architecture` `dataflow` `lifecycle` `sequence` `swimlane` `schedule` | ブロックの矩形で同じレイアウト計算を通す。小さいと配線ラベルの重なりなどの診断が warn になる。`legend_page` は無視して warn |

使えない（fail。直し方つき）: `title` `section` `closing` `statement` `quote` `agenda` `canvas` `composite`（入れ子）`split` `two_column` `image_text` `swimlane_legend` `diagram_legend` と、全面の `pattern`。例: `3枚目（type=composite）: 2 つ目のブロック: two_column は合成スライドのブロックにできません。two_column は 2 つの箱で 1 枚を使うタイプです → bullets のブロック（frame: box）を 2 つ並べる`

### ブロックの共通キー

| キー | 内容 |
|---|---|
| `type` | 上の表のタイプ（必須） |
| `heading` | ブロックの小見出し（1 行。長いと 18px → 14px まで縮め、収まらなければ warn） |
| `frame` | `none`（既定）: 小見出しの下に細い罫線／`box`: 淡い塗りと枠線の箱（内側の余白 20px）／`line`: 小見出しの下にアクセント色の太い罫線（小見出しが無ければ左端の縦線） |
| `emphasis` | true で主役のブロックにする（濃い塗り＋白文字。`callout` は、濃い箱の中に白い縦帯を出さない = 二重の強調にしない。帯を出したいときは `types.composite.callout.bar_on_emphasis` に色を書く。既定は `"none"`）。**1 枚に 1 つまで**（2 つ以上は warn）。対応は `text` `callout` `bullets`。ほかに付けると無視して warn |
| `align` / `valign` | `left` / `center` / `right`（text・callout のみ）、`top` / `middle` / `bottom`（text・callout・bullets・steps・cards・matrix） |
| `col` `row` `col_span` `row_span` | 位置の指定（上記） |
| `style` | そのタイプの `style`（領域 → プロパティ）。`style.body.size` などで文字サイズを固定できる（固定した値は自動フィットが動かさない）。位置と大きさ（x / y / w / h）は無視 |
| 中身のキー | そのタイプのスライドと同じ（`bullets` `columns` `rows` `nodes` `edges` …）。`title` `lead` `eyebrow` `conclusion` `source` はブロックでは描かれない（warn） |

### 見た目の既定値（`templates/layouts/default.json` の `types.composite`）

| 領域 | 値 |
|---|---|
| `body` | `gap` 24。lead が無ければ本文は y=140 から、結論帯・出典があれば下端を詰める |
| `block` | `pad` 20、角丸 `$radius.card`、塗り surface、枠 border、影 `$shadow.card`、小見出し 18px（下限 14）primary、`line` の太さ 3 accent、`emphasis` は primary 塗り＋on_primary |
| `text` / `callout` / `image` | text: 20px（下限 14）・行間 1.5 ／ callout: 強調文 28px（下限 17）＋補足 0.62 倍・左に太さ 5px の帯・縦中央 ／ image: contain・キャプション 14px |
| `blocks.<タイプ>` | ブロックに入れたときの文字サイズの既定（全面のときより小さい）: bullets 20/16（下限 13）、table セル 14・見出し 15・行高 46、cards 見出し 17・本文 14、steps ラベル 16・項目 14。中身が少ないときは大きくなる（上限と倍率は [autofit.md](autofit.md)） |
| 密度 | **talk**: text 24、callout 32、bullets 24/20（上寄せ）、table セル 17・行高 54、steps 19/17、cards 20/17。**read**: 下限を小さく（text 15、bullets 14、table 12）。standard は上の値 |
| 判定値 | `table_row_h_max` 64、`sparse_ratio` 0.5 / `sparse_min_px` 140（箱の中身が少ない警告）、`steps_min_w` 160 |

`frame: "box"` の小見出しの文字色は、箱の地の上で 4.5:1 に満たないとき（accenture テーマなど）、同じ色味のまま濃い側へ自動で寄る（`readable_pairs` の composite / split の `block.heading_color`）。`style.block.heading_color` を書けばそれが優先。

利用者の `style.blocks.<タイプ>.<領域>.<プロパティ>`（そのスライド）/ `meta.layout_overrides.composite.blocks…`（デッキ全体）が最優先。角丸・枠・影・見出しの太さは `meta.shape` に追随する（[themes.md](../themes.md)）。

### 警告・エラー（場所は「N枚目（type=composite）の K つ目のブロック（タイプ）: …」）

| 場面 | 例と直し方 |
|---|---|
| 使えないタイプ・入れ子（fail） | `two_column は合成スライドのブロックにできません … → bullets のブロック（frame: box）を 2 つ並べる` / `composite は…入れ子はできません → ブロックを並べるか、2 枚に分ける` |
| 置く場所が無い（fail） | `3 つ目のブロック（text）: 置ける場所がありません（格子は 2 列 × 1 行） → rows を増やすか、columns を増やす（または rows を省略して自動で増やす）`。`arrange` を書いているときは「arrange を外す（行は自動で足される）か、rows を書く」 |
| 位置の重なり・範囲外（fail） | `col=0・row=0 は別のブロックと重なります` / `col=2・col_span=1 が列の数（2）を超えています → col を 0〜1 にする（列は 0 から数える）` |
| 比率の値（fail） | `columns の要素は有限で 1e+06 以下の数で指定してください → 比率は [3, 2] のような小さい数にする` |
| 値違い（fail） | `frame は none / box / line のいずれかで指定してください（'boks'が書かれています）（もしかして "box"）`。ブロックの中身はそのタイプの検査がそのまま効く |
| 未知キー・使えない指定（warn） | `未知のキー "bulets" は無視されます（もしかして "bullets"）` / `emphasis は text / callout / bullets のブロックで使えます。この指定は無視します` / `style.body の x / y / w / h は無視します` |
| 文字があふれる（warn） | `文字がブロックに収まりません（14px まで縮めても約246px はみ出す）→ 文を短くするか、ブロックを広くする（columns / rows の比率）、2 枚に分ける`。bullets・table・cards などはそのタイプの自動フィットの警告が「ブロックの矩形で」出る |
| 縮めた（note） | `本文の文字を 20px → 16px に縮めました（14項目） → 大きく読ませたいときは項目を減らすか 2 枚に分ける` |
| 格子に空き・主役が複数（warn） | `格子に空きがあります（2行2列目） → ブロックを足すか、columns / rows / arrange を減らす（col_span / row_span で広げるのも有効）` / `emphasis が2個のブロックにあります（1 枚に 1 つまで）` |
| 箱の中身が少ない（warn） | `枠の中身が少なく、下の約162px が空きます → 項目を増やす、rows の比率で低くする、枠（frame）を外す、2 枚に分ける`（`frame: box` の bullets / table のみ測る） |
| 細い steps（warn） | `steps の 1 段の幅が約120px しかありません → 幅の広いブロックにする、段を減らす、または bullets のブロックにする`（1 段 160px 未満） |
| pattern の縮小（warn） | 縮小率 70% 未満で `型を 59% に縮めます → ブロックを広げる（columns / rows の比率、col_span / row_span）か、単独の pattern スライドにする`。幅の下限を持つ型は `この型（timeline）は幅 900px 以上向きです（いま 556px）→ …`（[pattern.md](pattern.md)） |

### 出力と検査

- HTML: ブロックごとに `<div data-block="K" data-block-type="タイプ" style="display:contents">` で包む（配置には影響しない）。PPTX: ブロックごとに 1 グループ（名前は `ブロック2（bullets）`）で、PowerPoint でブロックごと動かせる。**表（table / status_table）は実表のため、グループの外**に置く（表のあるブロックは束ねて動かせない）。`verify_pptx.py` は「グループの中に表」を検出する。
- `lint_deck_text.py` はブロックの中の文字も数える（【要確認】・記法・桁区切り・ブロックごとの項目数と字数。1 枚の文字量の目安は 1.5 倍）。`relation` は「ブロックのどれかが合うタイプなら可」。同じ構成の合成スライドが 3 枚続くと単調の warn。`check_diagram.py` は図解のブロックをそのブロックの矩形で診断する。

## `split` — 色面や画像のパネル＋本文

```json
{ "type": "split", "side": "left", "ratio": 0.4,
  "panel": { "fill": "primary", "eyebrow": "RESULT", "title": "作成時間は3分の1に", "text": "パイロット3チーム・2か月の実測" },
  "title": "内訳：体裁の修正が消え、下書きとレビューが縮んだ",
  "blocks": [ { "type": "chart", "chart": "waterfall", "unit": "分", "categories": ["導入前", "下書き", "レビュー", "体裁の修正", "導入後"],
                "series": [ { "name": "作成時間", "values": [100, -35, -18, -25, null] } ], "good": "down" } ],
  "conclusion": "体裁の修正がゼロになったのが最大の効果", "source": "出典: パイロット実績（延べ41本）" }
```

主役の一言か数字をパネルに置き、根拠の図表を本文側に置く「結論・実績の 1 枚」に向く。

| キー | 内容 |
|---|---|
| `side` | パネルを置く側。`left`（既定）/ `right` |
| `ratio` | パネルの幅の割合 0.25〜0.6（既定 0.4）。パネルは上下左右の端まで届く |
| `panel` | 必須。`fill`（色トークン。既定 primary）か `image`（`overlay` `opacity` `position` は背景と同じ。[hero.md](hero.md)）。中身は `eyebrow`（小さな見出し）`title`（大きな一文）`text`、または `kpi`（`{value, label, unit}`。大きな数字 1 つ）、`items`（短い箇条書き。3 つまで）。文字色は対比で自動選択し、自動フィット（上限 44px・下限 26px。kpi は 120px〜56px）で収める。kpi の数字は途中で折り返さず 1 行に収まる大きさまで下げる。数字が決まるまでの仮置きは `"value": "【要確認】"`（警告なし。大きな文字のまま強調されるので、確かめる点は `label` か骨子に書く）。title・text・items は文節で折り返す |
| `title` `eyebrow` `lead` | 残りの領域の見出し（28px）。`title` を書かなければ罫線も付けず本文を上に詰める |
| `blocks` `columns` `rows` `arrange` | `composite` と同じ。**書かなければ 1 列（縦に並べる）**。1〜2 個が目安（残りの幅は 570〜850px）。ブロック 1 個でも warn しない。body 枠の `pattern` も置ける（幅は `ratio` で決まる） |
| `conclusion` `source` | 残りの領域の幅で 1 回だけ（長ければ縮め、収まらなければ warn「結論の帯に文字が収まりません … ratio を下げて本文側を広げる手もある」） |

- フッターはパネルの反対側に置く。`meta.brand` は**パネルの上端**に置く（右のパネルは既定の位置、左のパネルはパネルの右上の角 = パネルの内側）。文字色はパネルの文字（`panel.title_color`）と同じで、パネルの塗りの上で読める色に自動で整う。残りの領域のタイトルは brand のために狭めない。残りの領域の `bullets` は大きめ（24px）で縦中央。
- ブロックにできないタイプは `composite` と同じ（`split` の入れ子も fail）。

| 場面 | 例と直し方 |
|---|---|
| panel が無い・値違い（fail） | `panel（端まで届く色面か画像のパネル）が必要です → "panel": {"fill": "primary", "title": "…", "text": "…"} のように書く` / `side は left / right のどちらかで…` / `ratio はパネルの幅の割合（0.25〜0.6）で指定してください（0.9）` |
| panel の型（fail） | `panel.kpi は {"value": "1/3", "label": "作成時間"} の形で、value が必要です` / `panel.items は文字列の配列で…` |
| 多すぎる（warn） | `panel.items が4個あります（3個までが目安）→ 本文側の bullets ブロックに移す` / `panel に kpi と title を両方書いています（主役は 1 つ）` |
| 収まらない（warn / note） | `パネルの文字が最小の文字サイズでも収まりません → panel の title / text を短くする、items を減らす、または ratio を上げる` / note `パネルの文字を 44px 基準から縮めました（目安: title 30 字以内）` |
| 色面・画像の対比（warn） | 背景と同じ文面（[hero.md](hero.md)） |

**表だけの split は上に詰まる**（`check_visual` が empty-bottom を警告する）。表の下に結論や根拠を足す、行を増やす、2 枚に分ける。

## 図解を合成に入れるとき

図解のブロックは、小さいほど配線ラベルが重なりやすい。`composite` の中の図解は、ノードとラベルを少なく短くし、凡例は `legend: false` で消して要点に書く（6 ノードの構成図が 2/3 幅のブロックに収まることは確認済み）。診断が出たら 1 点だけ直し、直らなければ図解を単独のスライドにして、要点を次の 1 枚に回す（作図の規約は [../diagram-guide.md](../diagram-guide.md)）。

# 自動フィットと密度（文字サイズ・列幅・行高が決まる仕組みと、警告の意味）

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。これは「文字が小さくなった」「縮めても収まらない警告が出た」ときに読むファイル。通常のデッキ作成では、各タイプのファイルの「自動フィット」の行で足りる。

## 基本の約束

- レイアウト既定値（＋密度のプリセット）を**上限**にして、内容が枠に収まる最大の大きさまで**縮める方向だけ**調整する。既定で収まる内容は見た目が変わらない。
- **`slide.style` / `meta.layout_overrides` に書いたキーは動かさない**（例: `style.table.cell_size` を書けば、その値のまま。列幅・行高だけ自動）。書いた値のままで収まらなければ警告する。
- 縮めたことは、2px 以上縮めたときだけ `note`（「文字を 24px → 20px に縮めました」）。収まらないときは警告（直し方つき）。
- 自動フィットを切る: `meta.autofit: false`（デッキ全体）、スライドの `autofit: false`。切っている間のあふれ警告は「autofit が切られているため縮めていません → `meta.autofit` または `autofit: false` を外すと自動で縮めます」になる。真偽値以外はビルドエラー。**スライドの `fit: false` は自動フィットのスイッチではない**（`fit` は cards / two_column の高さ・画像の `bleed` の指定）。
- `autofit: false` で止まるのは、文字・行・箱の縮小、中身が少ないときの拡大と整え（下の「中身が少ないときの自動調整」）、章扉の 2 行タイトルの枠の伸び、語の途中で折れる文への文節の改行（改行だけを止めるなら `line_balance: false`、1 枚だけなら `style.wrap.enabled: false`、デッキ全体なら `meta.layout_overrides.common.wrap.enabled: false`。下の「語の途中で折れる文」）。**止まらないもの**: 3.0.0 で既定の配置・間隔そのものを変えたもの（cards の内側・schedule の既定位置・一部の図解。戻し方と戻せないものは README の「互換性の注意」）。
- `style.table.col_widths` の形が不正（要素数が `columns` と違う・数値でない）なときは自動フィットを飛ばし、検証が「col_widths の要素数（2）が columns 数（3）と一致しません」と伝える。

## 密度（`meta.density` / スライドの `density`）

`"talk"`（映して話す。大きく・少なく）/ `"standard"`（既定。従来の見た目）/ `"read"`（配って読ませる。小さめ・密）。それ以外はビルドエラー（「meta.density は talk / standard / read のいずれかで指定してください」）。スライドの `density` で 1 枚だけ上書きできる。

- 効く順序: レイアウト既定 → 密度のプリセット → `meta.layout_overrides` → `slide.style`。**利用者が書いた値は常に勝つ**。
- プリセットはレイアウト JSON の `densities.<密度>.<タイプ>.<領域>.<プロパティ>`（タイプ単位の差分）。自作レイアウトでも書ける（`extends` で差分継承）。standard は `{}`（既定のまま）。
- 聞き手・用途で選ぶ（デッキを作る AI が決める）: 映して話すなら `talk`、配って読ませる資料や行数・文字数の多い表なら `read`。**7 行以上、または 5 列以上の表は `read` を勧める**（standard のままだと人が選ぶより 3〜4px 大きい 17px になり、2 行に折れるセルが増える）。
- `lint_deck_text.py` の文字量の目安も密度で変わる（talk: punch 50 字・bullets 1 項目 30 字・5 項目・1 枚 250 字 / standard: 80・40・6・500 / read: 120・60・8・800）。

| 密度 | table の文字（上限） | ヘッダ | 行高 | 上下余白 | 下限 |
|---|---|---|---|---|---|
| talk | 20px | 22px | 66 | 12 | 15px |
| standard | 17px | 19px | 58 | 10 | 12px |
| read | 14px | 16px | 56 | 8 | 12px |

他のタイプの上限（`default.json` の `densities`）:
- read: bullets 20 / two_column 本文 17 / cards 本文 13・見出し 17 / steps 項目 13 / status_table 12 / matrix 13 / summary `sizes` の先頭 18/14 ほか。cards・two_column は `fit: "content"`。
- talk: bullets 30（縦中央寄せ）/ two_column 本文 24 / cards 本文 19・見出し 24 / steps 項目 19 / status_table 17 / matrix 18 / summary 26/20 / statement 54 ほか。内容が多いときは上限から縮むので、**少ないときだけ大きく**間を埋める。
- `org` は自動フィットの対象だが、密度のプリセットは持たない（density を変えても文字サイズは変わらない）。
- `talk` の表は文字・行高が大きくなり、行数が少ないと行の高さを上限 96px まで広げ、それでも余ればタイトル帯の下の領域の縦中央に置く（`table.stretch_row_h_max` `thin_valign`）。`row_h` / `y` を明示したときは動かさない。standard / read の表は変わらない。

## タイプ別の縮め方と警告

| タイプ | 縮めるもの | 下限（`style` から上書き可） | 収まらないときの警告 |
|---|---|---|---|
| bullets / closing / image_text（`body`） | `size`。`child_size` `gap` `child_gap` は比例して詰める | `body.min_size`（bullets・closing 16 / image_text 14） | 「本文は 16px まで縮めても枠の高さを約Npx超えます → 項目を N 個以下に減らすか 2 枚に分ける」 |
| two_column（`col_body` / `col_heading`） | 左右そろえて `size` `gap`。talk / read では見出しも 1 行に収まるまで縮める | `col_body.min_size` 14 / `col_heading.min_size` 16 | 「左の列は 14px まで縮めても…」 |
| cards（`grid`） | `body_size` `heading_size` `item_size` `item_gap` を比例して縮め、さらに `pad` を詰める。本文の高さは内容の行数から決める | `grid.min_size`（本文 12。項目は −1、見出しは +4） | 「カードの中身が最小の文字サイズでも枠に収まらず、約Npx はみ出します → カードを N 枚以下に」 |
| steps（`body`） | 見出し（`label_size`。折れるときは帯の `header_h` を最大 `max_header_h` 84 まで高く）、項目（`item_size` `item_gap` `child_size` `child_gap`）。段が多くカードが細いときは `pad` も詰め、「STEP 10」の札の幅を実測して確保（それでも入らない幅では札を数字だけにする） | `body.label_min_size` 13 / `body.min_size` 12 | 見出しが折れて入らない（steps-label）、項目があふれる（steps-overflow）、カード幅 80px 未満（steps-narrow）、札が入らない（steps-num） |
| status_table（`table`） | `cell_size`（1px 刻み） | `table.min_size` 11 | 「表は 11px まで縮めても…→ 行を N 行以下に減らして 2 枚に分ける」 |
| matrix（`grid`） | `body_size`（象限の文）。`points` のラベルが 2 行を超えると警告（ラベルの箱は行数ぶん伸びる） | `grid.min_size` 12 | 象限の文のあふれ（matrix-overflow）、点ラベルが長い（matrix-point-label） |
| summary / reasons / row_matrix / house / cycle / kpi_tree / org / statement | 文字サイズの候補表（`body.sizes`。大きい順）から選ぶ。row_matrix の行見出し・列見出し、house の屋根・柱の見出し・土台、kpi_tree の目標（root）・KPI 名・目標値・測り方も箱に収まる大きさに縮める。**org は候補表も density プリセットも持たない** | 候補表の最後。root は `body.root_min_size` 12 | **最小の候補でも収まらないときは警告**。root が収まらなければ「目標の文を短くする（30 字以内）」。statement は `message.size` を上限として刻んで探す（100 を指定しても 28 に落ちない） |
| 結論帯（`conclusion`）・出典（`source`）（全タイプ） | 結論の文字を 17px から `conclusion.min_size`（13）まで縮め、入らなければ帯を `conclusion.max_h`（72）まで高くする。出典が 2 行以上なら高さ（`h` と `reserve`）を確保して本文を狭める | — | 結論が帯に入らない（conclusion-overflow）、出典が 3 行以上（source-long） |
| schedule | （縮めない）図が枠の下端を越えるとき、はみ出し量と「N 行以下」を伝える | — | `chart-overflow`: 「図が枠の下端を約Npx はみ出します → 行を N 行以下にして、スライドを分ける / lead を削る / min_row_h を下げる」 |
| table | 下記 | `min_size` 12 | 下記 |
| title / lead（全タイプ） | 下記 | title: cap の 0.78 倍 / lead: cap の 0.8 倍 | 下記 |
| kpi / chart / pattern | 矩形の大きさに合わせて自動。それぞれ [visual.md](visual.md) / [pattern.md](pattern.md) | `min_size` | 同じファイル |
| composite / split のブロック | **ブロックごとに**、そのブロックの矩形で、中に入れたタイプの規則（上の各行）をそのまま掛ける（文字サイズ・表の行高・図の配置）。小見出しは 18px → 14px。`text` / `callout` は 20px / 28px から下限まで。split のパネルの文字は上限 44px・下限 26px（kpi は 120px〜56px）、結論帯・出典・タイトル（28px。幅の 93% で測って早めに縮める）は残りの領域の幅で測る | ブロックの `style.<領域>.min_size`。タイプ別の既定は `types.composite.blocks` | 「文字がブロックに収まりません（14px まで縮めても約Npx はみ出す）→ 文を短くするか、ブロックを広くする、2 枚に分ける」。縮めたときは note（[composite.md](composite.md)） |

### table の規則

- **列幅**（`col_widths` を書かないとき。常に決まる。HTML は `table-layout: fixed`、PPTX も同じ幅）: 各列の平均文字幅の 0.7 乗に比例して配り、短い列は「それが 1 行に収まる幅」（ID・短い見出しが途中で折れない）を下限にする。折れすぎる列があれば余裕のある列から幅を回す。`col_widths` を書いたらその比率のまま。
- **文字サイズ**: 上限（`cell_size`）から 1px ずつ下げ、「セルが 3 行以上に折れない・2 行に折れる行が `wrap_ratio`（standard は 0.7、talk と read は 0.5）以下・高さに収まる」最大のサイズを選ぶ。折れる割合のために縮めるのは最大 2px。下限（`min_size` 12）まで縮めても収まらなければ警告。ヘッダは本文 +2。
- **泣き別れの回避**: 折り返したセルの最終行が 1〜2 字になる（「…デス／ク」）ときは、列幅を最大 +30% まで広げ（余裕のある列から幅をもらう）、それでも残るときは文字を最大 2px 縮める。避けきれないときだけ note。`D-04` `I-01` のような ID 風の語（英数字がハイフンでつながる 20 字以内）は HTML で `white-space: nowrap`（PPTX は PowerPoint 任せで、ハイフンの後ろで折れることがある）。
- **行高**: 既定の `row_h` / `header_h` で収まればそのまま（折り返す行があれば全行を一番高い行にそろえる）。収まらなければ行高 → 上下余白（下限 6px）→ 文字の順に詰める。HTML の表は行ごとの下罫線（1px）ぶん高くなるので、見積もりに 1 行 1px を足している。
- **下端**: フッターの 18px 上（y=660）。結論帯・出典があればその上。
- 新しい `style.table` のキー: `min_size`（既定 12）、`max_lines`（セルの最大行数。既定 2）、`wrap_ratio`（2 行以上に折れる行の割合の上限。standard は 0.7、talk と read のプリセットは 0.5）。

### table の警告・note

| 文言 | 意味 | 直し方 |
|---|---|---|
| `表が枠の高さを約Npx超える見込みです（N行・文字 12px のまま）→ 行を M 行以下に減らすか 2 枚に分ける…`（table-overflow） | 下限まで縮めても入らない（warn）。`cell_size` / `row_h` を書いているときは「style.table.cell_size / row_h を下げる（指定を消すと自動で縮めます）」 | 行を減らす・2 枚に分ける・列を減らす。style の該当キーを消す・下げる |
| `表の文字を 17px → 14px に縮めました`（table-shrunk） | 2px 以上縮めた（note） | 読ませたい文字量なら `meta.density: "read"` にして意図を明示する。大きく読ませたいなら行を減らす |
| `表のセルが 3 行以上に折れる行が N 行あります`（table-wrap3） | 収まる中で 3 行折りを避けられなかった（note） | セルの文字を短くする・列を減らす |
| `表のセル N 個で、折り返した最終行が 1〜2 字だけになります`（table-orphan） | 泣き別れを避けきれなかった（note） | 該当セルの文を少し短くする・`style.table.col_widths` を調整する |

### 折り返せない長い文字列（URL・長い英単語）

bullets / closing / image_text / two_column / steps / matrix（象限・軸ラベル）/ status_table / table で、折り返せない 1 語が枠の幅を超えるときは警告する（`long-word`。1 スライド 1 件にまとめ、いちばんはみ出す語を例に出す）:
`「長い語…」がセルの幅（Npx）に収まらず（Mpx）、途中で折れて表示されます → URL や長い英単語は短くするか、区切りの位置に改行（\n）を入れる`。HTML は `overflow-wrap: break-word` で枠の端で折り（PPTX も枠で折る）、スライド外へははみ出さない代わりに語の途中で切れる。

### 折り返しの規則（文節で折る・最終行を短くしない）

折り返し位置は、文字量の見積もりと同じ共通の規則（`tools/ja_text.py` の `can_break`）で決める。型エンジンも同じ規則を使う。`line_balance: false` で止められる（スライドか `meta`）。

- **切らない場所**: 「週 2 回」「第 3 期」の空白・数字と単位の間、仮名の連続の途中・活用語の続き（「出に｜くかった」「まと｜めて」）、「として・という・について・により・において」の途中、**英数字のあとの助詞の前（「JSON｜ の」）**。この規則では直せない文だけ、段階的にゆるめる（切ってよい場所が増えるだけで、直せなくなる文は増えない）。
- **大きな文字（36px 以上）**: 表紙・章扉（`title` / `section`）・`statement`・`quote` は、variant を付けなくても文節で折る。`background` つきのスライドの 36px 以上の文、quote の引用文（`text`）も同じ。最終行が 2〜4 字だけ残らないよう、サイズに応じた最小字数（36px 未満は 3、36px で 4、52px で 6、60px で 7）を確保する（「…仕組みを／つくる」を避ける）。2 行に収まるときは、行の長さが近い切れ目を選び、句読点（。、）の直後で前後が大きく違わなければそこで切る（「口述から資料へ。／人が直さない仕組みをつくる」）。
- 【要確認】のマーカーは、1 行に収まる長さなら 1 つの単位として折る（「【要確／認】」と割れない）。
- **直らないもの**: 表のセルや箱の見出しなど**狭い枠のカタカナ語の途中折れ**（「プラグ／イン」）。HTML と PPTX でずれるため自動では直していない。列幅の再配分で避けられる範囲は表の泣き別れ対策が扱う。残るときはその語を短くする・言い換える。

### 見出し（title）・リード（lead）の自動縮小（全タイプ）

- title が領域の高さ（既定 1 行）に収まらないとき、cap（既定 36px）から 1px ずつ下げ、下限（cap の 0.78 倍 = 28px）まで縮める。2px 以上縮めたら note。下限でも収まらなければ警告:「タイトルが 28px まで縮めても2行になり、約Npx はみ出します（N字）→ タイトルを短くする」。status_table のように幅の狭い title 枠（690px）でも同じ規則。
- lead は本文の上端までの高さ（2 行まで）に収まる最大サイズ（下限 cap の 0.8 倍 = 16px）。
- `style.title.size` / `style.lead.size` を書いたらそのサイズのまま（収まらなければ警告）。領域に `min_size` を書けば下限を変えられる。
- タイトルが縮むほど長いときは、縮めるより**短くする**（修飾語を削る。[../content-guide.md](../content-guide.md)）。

## 箱を内容に合わせて縮める: `fit: "content"`

cards の `grid`、two_column の `left` / `right` は、`"content"` にすると箱の高さを中身（最も長いカード・列）に合わせて縮め、余った分は上 4 割・下 6 割に配って少し上寄りの中央に置く（steps の `body.fit` と同じ作法）。`"fill"`（既定）は従来どおり領域いっぱい。それ以外の値はビルドエラー。下限は `grid.min_h`（cards 160）/ `left.min_h`・`right.min_h`（two_column 200）。
`meta.density: "read"` では既定で `"content"`。`style` の `h` を明示していて `fit` を密度から受けるだけのときは、h を優先して縮めず **y も動かさない**。`fit` を style に明示したときは h を上限として縮め、y を下げる。
**薄いカード（`thin_*`）**: 中身が領域の `thin_trigger`（0.72）倍に満たない cards は、`fit` を書かなくても、見出し・本文・項目の文字を最大 `thin_grow`（1.6）倍まで大きくし（折り返しが悪くならない範囲だけ。見出し・本文・項目は文節で折った前提で測る。強調 `emphasis` のカードは `emph_scale` 倍の文字で測る）、箱の高さを「中身 × `thin_k`（1.3）」と「領域の `thin_min_ratio`（0.55）」の大きいほう（下限 `min_h` 160）に抑えて本文領域の縦中央に置く（`thin_valign`）。`style.grid`（`meta.layout_overrides` の cards の `grid` も同じ）に `thin_*` 以外のキーを 1 つでも書いたとき（`cols`・`gap`・文字の大きさ・`h` / `y` / `fit` など）と、`columns` を書いたときは、手で決めたスライドとして扱い、従来の薄いカードの動き（文字は 1.4 倍まで・箱は中身 × `thin_k`・列数は選び直さない）のままにする。`span` で大きさを変えたカードがあるとき・`thin_grow: 1` のときは大きくしない。何も書いていないスライドでも、文字は従来（1.4 倍まで）の結果を下回らない。列数の選び直しだけを止めるなら `meta.layout_overrides.cards.grid.cols_search: false`。`fit: "content"` の cards は文字を大きくしない。列数を書いていないときは、2 枚 = 2 列、4 枚 = 2 × 2、5・6 枚 = 3 列にする（3 列の左側だけに寄る・3 + 1 に割れるのを避ける。3 枚は 3 列のまま）。ブロックの cards（composite / split）は同じ規則で**上寄せ**（`thin_grow` 1.3・`min_h` 90）、ブロックの steps は箱の高さの下限が 120px・行は上寄せ。表だけの split は、行を広げたうえで余りがあれば本文側の上下中央に置く（`types.composite.block.center_lone_table`。複数ブロック・枠つき・split 以外の composite は動かさない）。ブロックの中身が少ないときの整えは、下の「中身が少ないときの自動調整」。
**それでも薄いなら、スライドの上下は空く。** 3 項目・各 1〜2 行の `cards` は、箱が縮み文字が大きくなっても、本文領域の上と下が空く。`cards` は「見出し＋本文 2 行以上＋`items`」くらいの中身があるときのタイプで、中身が薄いなら**タイプを替える**: 短い並列 3 項目は、強調行つきの `bullets`、`summary`（番号の箱＋要点＋説明）、または `numbered-columns` / `keyword-explain` パターンにする。根拠・事例が材料にあるなら `items` に足す（無いものは足さず【要確認】）。

## 中身が少ないときの自動調整（`thin_*`）

中身が枠の一定割合（`thin_trigger`）に満たないとき、ビルドが文字を大きくし、箱の高さを中身に合わせて縦中央（または上寄せ）に置く。「枠の下が空きます」の警告を読んで `rows` の比を直す往復は要らない。**文字を大きくするのは折り返しが悪くならない範囲だけ**: 行数が増える・語の途中で折れる位置が増える・最終行が 1〜2 字になる（それまで 3 字以上だったとき）のどれかが起きる大きさは選ばない。何も足りないものがない（既定で枠を使い切る）スライドは変わらない。

**止め方（共通）**: ①`autofit: false`（スライド）／`meta.autofit: false`（デッキ）。②その領域の大きさ・位置・高さを `style` に書く（下の表の「書いたら動かさない」）。書いた値は動かさない。③`meta.layout_overrides` で拡大の倍率（`thin_grow`）を `1` にする。トークンの範囲外・型違いはキー名つきでビルドが止まる（`thin_grow` `thin_text_grow` `fill_grow` `fill_text_grow` は 1〜4、`thin_max_size` `thin_label_max_size` `thin_fill_min_size` は 1〜200、`thin_trigger` `thin_target` `thin_min_ratio` `thin_valign_ratio` `fill_trigger` `fill_target` `center_ratio` `thin_center_ratio` は 0〜1、`thin_fill_aspect` は 0.5〜20、`scale_k` は 1〜4、`grow_sizes` は 1〜200 の数値の配列（`[]` で止まる）、`thin_fill` `cols_search` と schedule の `auto_before` は true / false）。

### 単独のスライド（`types.<タイプ>.<領域>` と `meta.layout_overrides.<タイプ>.<領域>`）

| タイプ | 整え方 | トークン（既定） | 書いたら動かさない |
|---|---|---|---|
| `agenda`（`body`） | 項目が少ないとき（既定の行高で並べて本文の 7 割未満。説明なしで 6 項目以上・説明ありで 5 項目以上は従来どおり）、行の高さ・間隔・番号・見出し・説明を同じ倍率で大きくし、行の並びを本文の縦中央（少し上寄り）に置く。1 枚に入る行数（ページ分割）は変わらない | `thin_grow` 1.4（talk 1.5・read 1.2）/ `thin_max_size` 28（talk 30・read 24）/ `thin_trigger` 0.7 / `thin_target` 1.0 / `thin_valign_ratio` 0.45（0 で上寄せ） | `row_h` `gap` `text_size` `num_size` `num_w` `desc_size` `y` `h` のどれか |
| `steps`（`body`） | 見出しと項目の文字を大きくし、箱の高さを本文の 78% まで伸ばして、項目を箱の白い部分の縦中央に置く（領域いっぱいの `fit: "fill"` にすると少ない項目の上下が大きく空くので中間にしてある）。箱が本文の 8 割以上になる中身・項目が無いときは従来どおり | `thin_grow` 1.4 / `thin_max_size` 24 / `thin_label_max_size` 28 / `thin_trigger` 0.8 / `thin_target` 0.78（幅の `thin_fill_aspect` 2.4 倍を超えない） | `body` の位置・大きさ・文字のキーのどれか（`min_h` `valign` `fit` `h` `gap` `pad` `item_size` `label_size` など。`thin_*` のトークンは除く）。1 つでも書けば、文字の拡大も箱の伸ばしもしない |
| `cards`（`grid`） | 上の「薄いカード」 | `thin_grow` 1.6 / `thin_min_ratio` 0.55 / `thin_trigger` 0.72 | 上の「薄いカード」 |
| `status_table`（`table`） | 行が少なく（表が枠の 7 割未満）、どのセルも折り返しが悪くならないとき、セルの文字を大きくする | `thin_grow` 1.3 / `thin_max_size` 16（talk 19・read 14）/ `thin_trigger` 0.7 | `cell_size` |
| `cycle`（`body`） | パネルに余裕があるとき、本文の文字を `grow_sizes` の大きい方から試して、パネルの高さに収まり折り返しが悪くならない最大の大きさにする | `grow_sizes` `[20, 19, 18, 17, 16]`（talk `[24 … 19]`・read `[16, 15]`）。`[]` で止まる | `sizes` |
| `schedule`（`chart`） | **1〜3 行**（既定の行高 × 行数が図の領域の `thin_trigger` 割未満）: 行の高さ・矢羽根の太さを最大 2.2 倍（図が枠の約 72% になる倍率）、文字を最大 1.5 倍（行見出し 24px・矢羽根の文字 22px まで）。**4 行以上**: 図（行 + 期間・列見出し・凡例）が枠の `fill_trigger` 割に満たないとき、行の高さを `fill_grow` 倍まで配って `fill_target` 割まで使い、文字は `fill_text_grow` 倍まで（行見出しの折り返しが悪くなるときは、文字は大きくせず行の高さだけ配る） | `thin_grow` 2.2 / `thin_target` 0.72 / `thin_trigger` 0.6 / `thin_text_grow` 1.5 / `fill_trigger` 0.9（0 で 4 行以上の整えを止める）/ `fill_target` 0.95 / `fill_grow` 1.3 / `fill_text_grow` 1.2 | `style.chart` に行の高さ・文字の大きさ（`max_row_h` `label_size` `bar_size` など）のどれか |

status_table の PPTX の凡例（右上の「進捗状況ステータス定義」）は、見出しを図形、記号と説明を 2 列の表にして描く（以前は見出しを表の結合セルにしていたため、LibreOffice で凡例が高くなり見出しの罫線に重なった）。HTML と同じ位置・高さになる。

### 合成・split のブロック（`types.composite` 以下）

ブロックの矩形は格子が決める。中身がその高さの `thin_trigger` に満たないブロックを、次の順で整える。

1. 文字を大きくする（種類ごとの上限まで。`thin_grow` 倍と `thin_max_size` の小さいほう）。bullets・steps・text・callout の強調文と補足は、折り返しが悪くなる大きさには上げない。
2. 箱（`frame: "box"`）つきの bullets / text は、本文を箱の縦中央に置く。小見出しがあるときは**小見出しと本文を 1 つの塊にして**箱の縦中央に置く。同じスライドに小見出しつきの箱が他にもあるときは、見出しの位置をそろえるため、小見出しは動かさず本文だけを中央に置く（`types.composite.block.thin_center_ratio` 0.8。0 で無効）。
3. 同じスライドの本文のブロック（bullets・text・steps・cards）は、文字の倍率をそろえる（いちばん小さい倍率に合わせる）。table・callout・schedule は別々に決める。

| 種類 | 置き場所（`types.composite.…`） | `thin_grow` / `thin_max_size` / `thin_trigger` |
|---|---|---|
| bullets | `blocks.bullets.body` | 1.4 / 28 / 0.6 |
| text | `text` | 1.4 / 28 / 0.6 |
| callout | `callout` | 1.3 / 36 / 0.5 |
| table | `blocks.table.table` | 1.3 / 16（talk 18）/ 0.6。行が少ないときセルの文字も大きくし、行の高さは従来の `table_row_h_max` まで広げる。表だけの split のセルは 16px |
| steps | `blocks.steps.body` | 1.4 / 20（見出しは `thin_label_max_size` 22）/ 0.6 |
| cards | `blocks.cards.grid` | 1.6 / — / —（`center_ratio` 0.8。`cols_search` true） |
| 図解（architecture / dataflow / lifecycle / sequence。org / kpi_tree は `.body`） | `blocks.<タイプ>.diagram` | 1.5 / 22 / — |

- **steps**: 幅 600px 以上の主側では、見出し 16px 以上・項目 14px 以上（ふつうは 19〜22 / 16〜20）に上がる。項目が 16px（`thin_fill_min_size`）以上になったときは、カードが枠の高さいっぱいに広がり（`thin_fill`。`fit: "fill"`）、項目は見出しの直下に置かれる（`thin_fill_valign` が `"top"`。`"middle"` にするとカードの縦中央）。カードの高さが幅の 2.4 倍（`thin_fill_aspect`）を超える細長い枠、項目が 16px 未満のままのカードは広げず、従来どおり内容の高さ。
- **cards**: 列数を書いていないとき（`columns` も `style.grid.cols` も無いとき）、既定の列数・2 列・1 列を試して、文字がいちばん大きく読める列数を選ぶ。4 枚は 3 + 1 に割れず 2 × 2 になる。折り返しの質も見て、最終行が 1〜2 字・語の途中の折れが少ない列数を先に選ぶ。3 枚が細い箱の列になるときは縦に 3 段積む。列数を書けば動かさない。
- **schedule**: 単独の schedule と同じ拡大（行が少ないとき行の高さ・文字を大きくする）を、ブロックの高さに対して行う。
- **図解**: ブロックが大きいのに図が小さい（ノードの文字が 11〜14px のまま）とき、図を「枠を 1/k にした領域」に自然な大きさで組み、できた座標・箱・線の太さ・文字を**同じ倍率 k で拡大**して枠の中に置く（HTML と PPTX は同じ幾何なので同じ結果）。k は、図の文字が縮まない・折り返しが悪くならない（行数・語の途中の折れ・1〜2 字の最終行が増えない。org / kpi_tree も同じ）・拡大前（k = 1）に無かった診断が 1 つも増えない・描く枠から拡大前より外へ出ない、を満たす最大の値で、`thin_grow`（1.5）まで、ノードの見出しが `thin_max_size`（22px）を超えない範囲。決まった k は `style.diagram.scale_k`（org / kpi_tree は `style.body.scale_k`）に入る。拡大前の図に error か「詰まりすぎ」（too-dense）の診断があるときは拡大しない。`scale_k` に 1 より大きい値（1〜4）を書けばその倍率でそのまま拡大する。`check_diagram.py` とビルド時の診断は拡大後の幾何で出る（診断の `evidence` の座標は自然な大きさの値）。単独の図解スライド・matrix・swimlane は対象外。

**ブロックごとの止め方**: ブロックの `style`・スライドの `style.blocks`・`meta.layout_overrides.composite.blocks` に、その種類の文字の大きさ（bullets の `size`、steps の `label_size` / `item_size`、table の `cell_size`、cards の `heading_size` / `body_size` / `item_size`、text / callout の `size`）を 1 つでも書くと、その種類は大きくしない。ブロックの `valign` を書くと縦中央にしない。図解は `style.diagram.scale_k: 1`（org / kpi_tree は `style.body.scale_k: 1`）か、`composite.blocks.<タイプ>.diagram.thin_grow: 1`（org / kpi_tree は `.body.thin_grow`）。`autofit: false` では何も整えない。

**警告の変わった点**: 「枠の中身が少なく、下の約 N px が空きます」（`block-sparse`）は、**自動で整えられなかったときだけ**出る。整えられたら出ない。整えられないのは、`autofit: false` のとき・ブロックに `valign` を書いたとき・表を箱に入れたときで、文字の大きさを `style` で固定しただけでは出ない（本文は縦中央に置かれるため）。`check_visual.py` の empty-band も、整った分は出なくなる。

### 章扉（section）の 2 行タイトル

章扉のタイトルが折れて 2 行になると、タイトルの枠を下へ伸ばし、罫線と副題を同じだけ下げる（文字は縮めない。2 行に収まらないときだけ縮めて 3 行まで。縮めても 3 行に収まらないときは 4 行分まで枠を伸ばす）。行数は、36px 以上の大きな文字に掛かる文節折り返し（素直な折り返しより行が増えることがある）が実際に入れる改行まで数える。variant（number / band / side）・4 shape・背景画像つきでも重ならない。帯（band）の色の帯も伸びる。`style.title.h` を書いたときは動かさない。`autofit: false` では伸ばさず、「タイトルが枠の高さを約 N px 超える見込みです（autofit が切られているため縮めていません）」の警告になる。

## 語の途中で折れる文は、文節の切れ目で折る（`common.wrap`）

狭い箱の中の文が「プラグイ／ン」「担当／者へ」「始／めます」のように語の途中で折れるとき、ビルドが**文節の切れ目に改行を入れる**（HTML と PPTX の同じ位置。改行は `\n` と同じもの）。自然な折り返しで語の途中に折れない文には何もしない。

- **対象**: bullets（子項目を含む）・two_column・closing の bullets・image_text の本文・cards の見出し・本文・項目（20px 以上は従来から文節で折る）・steps（見出し・項目）・table のセルと見出し・kpi の label / note・タイトル / リード / 副題 / punch / message / quote の text / statement の `support` / quote の `attribution`、合成・split のブロックの bullets / text / steps / cards / callout。
- **触らないもの**: 明示の `\n` を書いた文／文字の大きさ・幅を `style` で書いた領域（`style.body.size`、`style.grid.body_size`、`style.table.cell_size` / `col_widths` ほか。`meta.layout_overrides` の同じ指定も）／英文・和文を含まない文／1 行に収まる文／URL のセル／60 行を超える表（探索を省く）。英数字の語・URL・【要確認…】の内側には切れ目を入れない。
- **行数を増やさない**: 改行を入れて行が増えるときは、箱の高さに余りがあると確かめられた場所（cards・bullets・two_column・steps・単独の見出し類）だけ、最大 1 行まで許す。余りを測れない場所（kpi の label / note・表のセル・合成ブロックの callout / text）は、行が増えるなら直さない（あふれ・縮小を新しく作らない）。入れた結果は描く前に検算し、決まった大きさと幅でどこかの行がさらに折れる・1 字だけの行ができる・最終行が 1〜2 字になる（元が 3 字以上のとき）なら、その段落には入れない。
- **実機の字幅のずれ**: 代替フォント（この環境では Hiragino Sans）で測っている。実機（Meiryo）で数文字ずれても同じ位置で折れるよう、改行は幅を `safety`（0.95）倍に狭めた折り返しで先に試し、入らなければ実幅で試す。
- **順序**: 文字の大きさ・列幅は、改行を入れる前の元の文で自動フィット（縮小・拡大）が決める → 決まった大きさと幅で改行を入れる。改行の有無で大きさは変わらず、同じ入力から同じ出力になる。

| `common.wrap` のキー | 既定 | 意味 |
|---|---|---|
| `enabled` | true | false で止める |
| `detect_level` | 3 | 語の途中かどうかの判定（1〜3。3 = 語の途中・送り仮名・行頭の助詞だけ。1 にすると「出に／くかった」のような活用語の途中も拾う） |
| `safety` | 0.95 | 実機のずれを見込む幅の倍率（0.5〜1） |
| `max_back_em` | 10 | 切れ目を探して行の中をさかのぼってよい字数 |
| `max_extra_lines` | 1 | 改行を入れて行が増えてよい上限（0 で常に増やさない） |
| `min_px` | 0 | この文字サイズ（px）未満の文には掛けない |

止め方: デッキ全体は `meta.layout_overrides.common.wrap.enabled: false`、1 枚だけは `style.wrap.enabled: false`。`line_balance: false`（`meta` / スライド。泣き別れ対策と同じスイッチ）と `autofit: false`（`meta` / スライド）でも止まる（kpi の label / note も同じ条件）。範囲外・型違い（`detect_level` `max_extra_lines` は整数）はキー名つきでビルドが止まる。

**直らないとき**: 利用者が文字の大きさ・幅を書いた領域と、行が増える直し方しか無い場所（表のセル・kpi の label / note・合成ブロックの callout / text）は直さない。`check_layout.py` の `wordbreak`（警告。[../../skills/create-deck/checks.md](../../skills/create-deck/checks.md)）で気づける。文を短くする／文節の切れ目に `\n` を入れる／箱の幅・size を調整する。表のセルは列幅（`style.table.col_widths`）を広げる。

## 新しいキー（`style` / `meta.layout_overrides` から使える）

`thin_trigger` `thin_k` `thin_grow` `thin_valign` `thin_min_ratio`（cards の `grid`。ほかのタイプの `thin_*` / `fill_*` は上の「中身が少ないときの自動調整」）/ `min_size`（bullets・closing・image_text の `body`、`col_body`、`col_heading`、cards の `grid`、steps の `body`、status_table の `table`、matrix の `grid`、`conclusion`）/ `fit`（cards の `grid`、two_column の `left` `right`）/ `min_h` / steps の `child_size` `child_gap` `label_min_size` `max_header_h` / `conclusion.max_h` / house の `roof_min_size` `pillar_head_min_size` `found_min_size` / kpi_tree の `kpi_min_size` `value_min_size` / row_matrix の `label_min_size` `head_min_size`。

## 運用の助言

- 警告が出たら、まず「N 個以下に減らす／2 枚に分ける」に従う。文字を小さくして詰め込むより、分けたほうが読める。
- 少ない内容を大きく見せたいときは `talk`、情報を密に見せたいときは `read`。スライド単位でも `density` を書ける。
- 自動フィットは文字量を実測（ブラウザが実際に使うフォントの字幅）で見積もる。フォントがこの機械に無いときの note は [validation.md](validation.md)。

## standard の見た目が変わるもの（従来のデッキを再ビルドしたとき）

- cards は本文の高さを固定 44px から内容の行数基準に変えたため、カード内の見出し・本文・項目の位置が数 px ずれ、項目の間隔が少し詰まる（`style` に値を明示していても起きる）。
- 表は、`col_widths` を書かない場合の列幅が HTML・PPTX で同じ計算結果（固定レイアウト）になる。行の下罫線 1px を高さの見積もりに入れる。泣き別れを避けるため列幅・文字が少し変わる。
- 中身が薄い cards は、文字が最大 1.6 倍まで大きくなり、箱が中身に合わせて縮んで縦中央に置かれる（以前は箱が領域いっぱいに伸びて下が空いた）。改行位置も文節寄りになる。
- 中身が少ない agenda・steps・status_table・cycle・schedule・合成/split のブロック・合成の図解ブロックは、文字が大きくなる（上の「中身が少ないときの自動調整」）。語の途中で折れる文には文節の改行が入る。章扉の 2 行タイトルは枠が伸びる。
- 表紙・章扉・言い切り・引用などの 36px 以上の文字は、語の途中で折れず、最終行が短くならないよう折り方が変わる。
- 文字色が自動で整う（地の色の上で 4.5:1 に足りなかった steps の「STEP n」・agenda の番号・図解ノードの文字など。default テーマの `muted` は `#5A6B85` → `#566781`）。
- `talk` の表（行が少ないとき）は行が高くなり縦中央に置かれる。kpi の 2〜4 件のタイルは本文領域いっぱいに広がる。schedule の既定の位置は x 72・幅 1136（2.0.0 は x 48・幅 1184。片方だけ `style.chart` に書いたデッキは警告が出る。README の「互換性の注意」）。
- `col_widths` を書いた表の列幅、style で明示したキー、`autofit: false` のスライド、既定のままで収まる表は変わらない。

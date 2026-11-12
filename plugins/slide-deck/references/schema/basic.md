# 基本タイプ（title / section / bullets / two_column / table / status_table / code / quote / image / image_text / closing / agenda / steps / matrix / cards）

座標系・3層構造・`meta`（`density` / `autofit` を含む）・全タイプ共通のオプション（`notes` / `style` / `relation` / `line_balance` / `density` / `autofit` / `eyebrow` / フッター）・文字量の目安は索引 [`../deck-schema.md`](../deck-schema.md)。
大きな数字・グラフは [visual.md](visual.md)、登録した構図は [pattern.md](pattern.md)、1 枚に複数ブロックを並べる `composite` と非対称分割 `split` は [composite.md](composite.md)、主役のページ（`variant` / `background` / cards の強弱 / 画像を端まで）は [hero.md](hero.md)、図解（swimlane / architecture など）は [swimlane.md](swimlane.md) / [diagram.md](diagram.md)、工程表は [schedule.md](schedule.md)、提案書向けの型は [proposal.md](proposal.md) を見る。

**文字サイズ・列幅・行の高さは、内容に合わせて自動フィットが決める**（既定の大きさを上限に、収まらないときだけ縮める。`style` に書いた値は動かさない）。各タイプの「自動フィット」の行は要点だけで、規則・下限・警告の意味は [autofit.md](autofit.md)。警告が出たらまず内容（項目数・文の長さ・分割）を直し、`meta.density`（`talk` / `standard` / `read`）で意図を伝える。`style` で大きさを手で詰めるのは最後。

**タイプ → 節**: 本文系 `title` / `section` / `bullets` / `two_column` / `table` / `quote` / `closing`、構造系 `agenda` / `steps` / `matrix` / `cards` / `status_table`、素材系 `code` / `image` / `image_text`。見出し（`## \`type\``）で探す。

## `title` — 表紙
```json
{ "type": "title", "title": "資料タイトル", "subtitle": "...", "meta": "社内勉強会 / 2026-08" }
```
領域: `bar`（左帯）, `title`, `subtitle`, `meta`
主役の表紙にするなら `variant`（`center` / `left-band` / `split` / `bottom`）と `background`（画像か色面）を書く（[hero.md](hero.md)）。

## `section` — 章扉
```json
{ "type": "section", "number": "01", "title": "...", "subtitle": "..." }
```
領域: `bg`, `number`, `title`, `rule`, `subtitle`
章扉の `variant`（`number` / `band` / `side`）と `background`、章番号の自動採番（`meta.section_numbers`）は [hero.md](hero.md)。
**タイトルが 2 行になるとき**は、タイトルの枠を下へ伸ばし、罫線と副題を同じだけ下げる（文字は縮めない。重ならない）。`autofit: false` では伸ばさず警告になる。詳しくは [autofit.md](autofit.md) の「章扉（section）の 2 行タイトル」。


## `bullets` — 箇条書き
```json
{ "type": "bullets", "title": "見出し", "lead": "リード文（任意）",
  "bullets": [
    "文字列そのまま",
    { "text": "子項目つき", "children": ["子1", "子2"] },
    { "text": "強調したい行", "bold": true, "size": 26, "color": "accent" }
  ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l`, `footer_r`。項目単位で `size` / `color` / `bold` を上書き可能（子項目も同様）。目安: **3〜6項目、1項目40字以内**。**自動フィット**: 内容が多いと本文の `size` を下限（`body.min_size` 16）まで縮める（子項目の大きさ・間隔は比例して詰める）。下限でも枠の高さを超えると警告（「項目を N 個以下に減らすか 2 枚に分ける」）。`meta.density: "talk"` は大きく（上限 30px・縦中央寄せ）、`"read"` は小さめ・密（上限 20px）。

既定は内容を上詰め（`valign: "top"`）。項目数が少ないスライドはキャンバス下半分が空白になりがちなので、`style.body.valign` を `"middle"` にすると `body` 枠（既定 y=192, h=456）の縦中央に項目群を寄せられる（`two_column` の `left`/`right` と同じ考え方。HTML/PPTX 共通で実際の描画高さに応じて自動的に中央寄せされるため、項目数を変えても再調整不要）。


## `two_column` — 2カラム比較
```json
{ "type": "two_column", "title": "見出し",
  "left":  { "heading": "左見出し", "bullets": ["..."] },
  "right": { "heading": "右見出し", "bullets": ["..."] } }
```
領域: `left` / `right`（ボックス）, `col_heading`, `col_body` ほか。既定は内容を上詰め（`valign: "top"`）。`style.left.valign` / `style.right.valign` を `"middle"` にすると箱内で縦中央寄せになる。

**自動フィット**: 左右そろえて本文の `size`・`gap` を縮める（下限 `col_body.min_size` 14、見出し `col_heading.min_size` 16）。**箱が内容に対して大きすぎるとき**は、文字を大きくせず `style.left.fit` / `style.right.fit` を `"content"` にして箱の高さを内容に合わせる（余りは上 4 割・下 6 割に配る。下限 `min_h` 200）。`meta.density: "read"` では既定で `"content"`。`"fill"`（既定）は領域いっぱい。

追加オプション:
- `two_column`: `connector: "arrow"` で左右の箱の間に灰色の三角（左から右への流れ・因果）を置く（目的 → 骨子など）

## `table` — 表
```json
{ "type": "table", "title": "見出し", "columns": ["列1", "列2"], "rows": [["a", "b"]],
  "style": { "table": { "row_h": 64, "cell_size": 16, "col_widths": [1, 2], "border_color": "border" } } }
```
領域: `table`（`col_widths` は比率の配列。**要素数は `columns` と一致させること**（不一致はビルドエラー）。各行のセル数も `columns` の数と一致させる。`header_h` / `row_h` で行の高さ、`header_size` / `cell_size` でフォント、`border_color` で罫線色（テーマトークン、既定 `border`））。目安: **6行以内**（超える場合はスライドを分けるか要約する。**7行以上、または5列以上なら `meta.density: "read"`**）。

セル全体が `http://` または `https://` のURLなら、HTMLではクリック可能なリンク、PPTXでは外部ハイパーリンクとして自動出力する。説明文にURLを混ぜたセルは自動リンク化しない。

URLを見せず、資料名など別の文字列をリンクにする場合は、セルを `{"text": "表示文字列", "url": "https://..."}` と書く。セル値が `null`（JSON の `null`）の場合は空文字として表示される。

**リンク先のスキーム制限（セキュリティ）**: リンクとして出力できるのは `http` / `https` / `mailto` のスキームだけ。ビルダーは href に出力する直前に `urlparse` でスキームを取り出して許可リストと突き合わせ、
- 自動リンク化（セル全体がURL）の対象は `http` / `https` のみ
- 明示指定の `url` は `http` / `https` / `mailto` のみ

とし、`javascript:` / `data:` / `vbscript:` / `file:` などが指定された場合は**ビルドエラー**にする（`url` を明示指定した場合）。文字列セルとして書かれた `javascript:...` はリンク化されず、そのまま通常のテキストとして表示される。HTMLのエスケープ（`<` `>` `&` `"` `'`）ではスキーム由来のXSSは防げないため、この許可リストで弾いている。

行単位の背景色は `style.table.row_fills` で指定する（キーは 0 始まりの行番号の文字列、値はテーマトークン or hex）。指定のない行は従来どおり交互色。意味のある行（例: AI 関連の行）に「しるし」を付ける用途に使う（強調色には `highlight_fill` トークンを推奨）:
```json
{ "type": "table", "...": "...",
  "style": { "table": { "row_fills": { "3": "highlight_fill" } } } }
```

**自動フィット**: `col_widths` を書かなければ列幅は内容から自動で決まり（HTML も PPTX も同じ幅）、文字サイズは上限 `cell_size`（17）から下限 `min_size`（12）まで、セルが 3 行以上に折れない最大のサイズを選ぶ。収まらなければ行高 → 上下余白 → 文字の順に詰め、下限でも入らなければ警告（「行を N 行以下に減らすか 2 枚に分ける」）。折り返した最終行が 1〜2 字になる泣き別れも自動で避ける。`style.table` に書いた値は動かさない。規則・密度ごとの上限・警告の表は [autofit.md](autofit.md)。

**行の強調とセルの意味づけ**:
- 行は配列のほか `{"cells": ["A", "B"], "emphasis": true}` でも書ける。強調行は `style.table.emphasis_fill`（既定 `highlight_fill`）で塗り、太字。行番号指定の `row_fills` より並べ替えに強い。`cells` が無いとビルドエラー
- セルは `{"text": "高", "tone": "bad"}` でも書ける（`url` と併用可）。`tone` は `good` / `warn` / `bad` / `accent` / `muted`（文字色＋太字。色は `style.table.tone_colors`）。それ以外の値はビルドエラー。強調行・縞の行・ラベル列の塗りの上で 4.5:1 に満たない色は、同じ色味のまま濃い側へ自動で寄る（強調行と `tone` を併用してよい。意味の色味は保たれる）。
- セルの中の `\n` は HTML でも PPTX でも改行になる

追加オプション:
- `table`: `row_header: true` で1列目を行見出し（淡い色の塗り・太字）、`total_row: true` で最終行を合計行（`surface` 塗り・太字）にする。色は `style.table.label_fill` / `total_fill` / `label_color`

## `status_table` — 進捗ステータス表（信号＋実績／計画）
```json
{ "type": "status_table", "title": "1. 全体・個別進捗報告（1/2）", "lead": "10/9(金)時点で、各チーム予定通り進行中。",
  "columns": ["チーム", "進捗状況", "実績（10/9時点）", "計画（今週末時点）"],
  "rows": [
    { "label": "PMO", "status": "green",
      "cells": [
        [ { "text": "進捗管理、課題管理等", "children": ["（継続）進捗管理", { "text": "論点議論", "children": ["顧客対応：…"] }] } ],
        [ "計画の項目" ]
      ] }
  ] }
```
- 1列目＝ラベル列（`label`、`highlight_fill` 地）、2列目＝信号（`status` の色の ●）、3列目以降＝内容列。`cells` の数は `columns` 数 − 2 と一致させる（不一致はビルドエラー）。
- セル内は文字列 or `{ "text", "children" }` の入れ子。最上位は ✓＋下線、2階層目以降は • で、階層ごとに字下げされる（PPTX ではネイティブ箇条書き）。
- `status` は凡例の `key`、テーマトークン、`#hex` のいずれか。凡例（右上）は `legend: [{ "key", "color", "label" }]` で指定し、省略時は赤（日程再調整が必要）／黄（リカバリ予定有）／緑（予定通り）の3色。`legend: false` で非表示、`legend_title` で凡例左の見出しを変更。
- 行の高さはセル内容から自動計算し、`table.fill_height`（既定 true）なら表の高さ（`table.h`）いっぱいまで比例配分する。内容が収まらない見込みならビルド時に warning。
- 領域: `title`（凡例と重ならないよう既定幅 690px。`legend: false` のときは罫線と同じ幅まで使う。`style.title.w` の明示が優先）, `rule`, `lead`, `legend`, `table`（`col_widths` / `header_h` / `cell_size` / `label_size` / `status_size` / `indent` / `border_color` / `check_char` / `bullet_char` / `heading_underline` 等）, `footer_l/r`。
- 1枚3行程度が目安。PPTX は PowerPoint のネイティブ表として出力されるので、文字や信号の色を PowerPoint 上でも編集できる。凡例（右上）は PPTX では見出しを図形、記号と説明を 2 列の表にして描く（HTML と同じ位置・高さ）。
- **行が少ないとき**（表が枠の 7 割未満で、どのセルも折り返しが悪くならない）は、セルの文字を最大 1.3 倍（上限 16px。talk 19・read 14）まで大きくする。`style.table.cell_size` を書いたときは動かさない（[autofit.md](autofit.md) の「中身が少ないときの自動調整」）。
- 列数が既定（4 列）と違っても、`col_widths` を書かなければ内容列で残りを等分して組む（3 列の最小形・5 列以上も可）。**自動フィット**: `cell_size` を 1px 刻みで `table.min_size`（11）まで縮め、下限でも入らなければ警告（「行を N 行以下に減らして 2 枚に分ける」）。


## `code` — コード / 設定例
```json
{ "type": "code", "title": "見出し", "language": "yaml", "code": "type: Concept\n..." }
```
領域: `code`。行数が多いときは `min_size` まで自動縮小（HTML/PPTX 共通ロジック）。折り返しはせずクリップする（HTML/PPTX 共通）ので、1行が極端に長いコードは事前に改行を入れる。行数が多すぎるコード（40 行級）は PPTX だけ箱の下へ文字が溢れることがあるので、短く抜粋するか 2 枚に分ける（`check_pptx.py` の画像比較では拾えない。PPTX を目で見る）。

追加オプション:
- `code`: `annotations: [{"line": 6, "title": "確認", "text": "…"}]` で右に番号付きの注釈を並べ、該当行に同じ番号の丸と左端の印を付ける（コードの幅は自動で6割に狭まり、文字は横幅にも収まるよう縮む）

## `quote` — 引用・キーメッセージ
```json
{ "type": "quote", "text": "強調したい一文", "attribution": "出典（任意）" }
```
領域: `mark`, `text`, `attribution`。`variant`（`left-bar` / `mark`）と `background` は [hero.md](hero.md)。

## `image` — 画像
```json
{ "type": "image", "title": "見出し（任意）", "path": "assets/figure.png", "caption": "..." }
```
`path` はデッキフォルダ配下（`assets/` 推奨）の相対パスのみ（デッキフォルダの外を指すパスや存在しないファイルはビルドエラー）。対応拡張子: png / jpg / jpeg / gif / bmp / svg / webp / tiff。領域 `img`（既定 1136×440px、比率 約2.58:1）の枠内に等比で収まる（拡大・縮小どちらも行う）。**推奨アスペクト比は 4:3 〜 2:1**（例 1024×768、1200×600）。極端な縦長・横長の画像は左右または上下に余白（レターボックス/ピラーボックス）ができる。写真を主役に全面へ敷くなら `fit: "bleed"`（タイトルは覆いの上）、キャプションを帯にするなら `caption_position: "band"`（[hero.md](hero.md)）。

**画像アセットはテーマに自動追従しない。** SVG/PNG 等の画像は静的なファイルなので、`meta.theme` を切り替えても配色・背景は変わらない。暗色系テーマ（背景が濃色のテーマ）で白背景の図版を使うと、スライドの中で図版だけ浮いて見える。暗色テーマを使うデッキでは (a) 画像側もそのテーマの背景色に合わせて用意する、(b) 可能なら `swimlane` / `matrix` / `steps` などテーマトークンで自動的に配色されるネイティブ図解タイプを使う、のいずれかを検討する。

## `image_text` — 画像＋パンチライン＋本文（1枚で伝える統合レイアウト）
```json
{ "type": "image_text", "title": "見出し",
  "punch": "一目で伝えたい一文（全幅・太字・アクセント色）",
  "bullets": ["本文（bulletsと同じ書式。childrenも可）"],
  "path": "assets/figure.png", "caption": "画像の下の補足（任意）",
  "image_side": "right" }
```
領域: `title`, `rule`, `punch`（全幅パンチライン）, `body`（本文カラム）, `img`（既定 524×378px）, `caption`, `footer_l/r`。
`image_side` を `"left"` にすると画像と本文の左右が入れ替わる（既定は右）。**左にしたとき、`style` の `img` / `body` の `x` は左右反転して適用される**（`style.img.x: 100` は右配置なら x=100、左配置では画像の右端が 100 の位置になり x=656）。左配置の `style` は、右配置にしたときの座標で書く。`bleed: true`（画像が右）では、右上の `meta.brand` は画像の上の文字として扱い、画像の明暗から白か濃い色を選ぶ（画像が中間の明るさだと「背景画像の上の文字の対比が x.xx:1 で 4.5:1 に届きません」の警告が出る。brand は大きな文字なので check_layout の基準 3:1 は満たす）。
**画像だけ・文章だけのページに分離せず、メッセージと図解を1枚に載せたいときはこのタイプを使う。**
画像は 4:3 前後（例: 1024×768）が最も収まりが良い。`path` の制約は `image` タイプと同じ（デッキフォルダ配下・対応拡張子のみ）。`bleed: true` で画像を上下と画面の端まで届かせる（[hero.md](hero.md)）。

## `closing` — まとめ
```json
{ "type": "closing", "title": "まとめ", "bullets": ["..."], "message": "締めの一言（任意）" }
```
領域: `bg`, `title`, `rule`, `body`, `message`。`title` は **22 字以内**（固定の 72px 枠で 2 行に折れると罫線を貫くため、`lint_deck_text.py` が超過を不合格にする）。`title` だけでも本文空の警告は出ない（「ありがとうございました」だけの結びも可）。`message` の縦位置は既定で **`body` の実描画高さの直後**に自動配置される（`follow_body: true`。`body` が短ければ `message` が上に詰まり、長ければ下がる。下限 `min_y`、上限はレイアウトの既定 `y`）。`style.message.y` を明示すればその固定値が優先される。 `variant`（`center` / `contact`）と `background` は [hero.md](hero.md)。


## `agenda` — アジェンダ / 目次
```json
{ "type": "agenda", "title": "Agenda", "lead": "（任意）",
  "items": [ "はじめに", { "text": "本日の議題", "active": true }, "まとめ" ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。各項目に自動で連番（`01`, `02`…）が付く。`active: true` の項目は面（`active_fill`）で強調され、文字色が `active_color` になる。項目のキーは `text`（項目名）/ `desc` / `active` だけ。`title` などと書くと「未知のキー」と「text（項目名）がありません」の警告が出て、番号だけの行になる。番号の色は通常行・強調行のどちらの地の上でも 4.5:1 になるよう自動で整う。`bullets` の代替ではなく「番号付き＋現在地ハイライト」が要るときに使う。

**自動2段組・ページ送り**（項目数に応じて自動。**deck.json に書いたスライド数より実際の出力枚数が増えることがある**）:
- 1列あたりの最大行数 `R = floor(body.h / (row_h+gap))`（既定値で **R = 8 行**）。
- 項目数 **N ≤ R** → 1段。**R < N ≤ R×max_cols** → 自動で2段（左列を上から埋めて右列へ）。**N > R×max_cols** → 次ページの agenda に自動で繰り越し（連番は通し、2枚目以降のタイトルに「（続き）」）。
- `body` の `max_cols`（既定 2）/ `row_h` / `gap` / `col_gap` で段数・行ピッチを調整できる。既定では **9〜16 項目=2段、17 項目以上=2ページ目**。

追加オプション:
- `agenda`: 項目に `desc`（説明文）を書くと、項目名の下に小さく説明が入る（行の高さは自動で 64px に広がる）。`{"text": "背景と目的", "desc": "…"}`
- **項目が少ないとき**: 行の高さ・間隔・番号・見出し・説明の文字を同じ倍率で自動で大きくし（最大 1.4 倍。talk 1.5・read 1.2）、行の並びを本文の縦中央（少し上寄り）に置く。項目が多い（説明なしで 6 項目以上・説明ありで 5 項目以上）ときは従来どおり。**`style.body` の手書き（`row_h` `text_size` …）は要らない**。`row_h` `gap` `text_size` `num_size` `num_w` `desc_size` `y` `h` のどれかを書くとその値で固定され、自動では大きくならない（トークンと止め方は [autofit.md](autofit.md) の「中身が少ないときの自動調整」）。

## `steps` — ステップチャート / フロー
```json
{ "type": "steps", "title": "見出し", "lead": "（任意）",
  "steps": [
    { "label": "研究開発", "items": ["基礎研究", "実験・検証"] },
    { "label": "社会実装", "items": ["インフラ整備"] }
  ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。手順・フロー・バリューチェーンを横並びのカードで表現し、カード間をシェブロン（›）で接続する。ステップ数（3〜5推奨）に応じてカード幅は自動調整。各カードはヘッダ（`header_fill`＝primary、`STEP n` は `num_color`）＋本文の箇条書き（`items`）。色はテーマの `primary` / `surface` / `on_primary_soft` に固定されており、カードごとに任意の色を指定するオプションは無い（要素ごとに色を変えたい場合は `image` / `image_text` で図を用意する）。

**自動フィット**: 見出し（`label_size`、折れるときは帯の `header_h` を最大 `max_header_h` 84 まで高くする）と項目（`item_size` / `item_gap` / `child_size` / `child_gap`）を縮める（下限 `body.label_min_size` 13 / `body.min_size` 12）。段が多くカードが細いときは `pad` も詰め、「STEP 10」の札の幅を実測して確保する（入らない幅では札を数字だけにする）。見出しが折れて入らない・項目があふれる・カード幅が 80px 未満のときは警告する（[autofit.md](autofit.md)）。

**カードの高さ**: 既定（`style.body.fit: "content"`）では最も長いカードの内容に合わせて高さを縮め、行全体を領域の上寄り中央に置く（短い内容で下半分が空くのを防ぐ）。下限は `style.body.min_h`（既定 260px）、上限は `body.h`。従来どおり領域いっぱいに描きたいときは `"fit": "fill"`。カードの枠線色は `card_border`（既定 `border` トークン）。

**段の中身が少ないとき**: 見出しと項目の文字を大きくし（折り返しが悪くならない範囲。上限 項目 24px・見出し 28px）、箱の高さを本文の高さの 78% まで伸ばして、項目を箱の白い部分の縦中央に置く（箱が本文の 8 割以上になる中身・項目が無いときは従来どおり）。`style.body` に位置・大きさ・文字のキー（`min_h` `valign` `fit` `h` `gap` `pad` `item_size` `label_size` など）を 1 つでも書いたスライドは、手で決めたものとして文字の拡大も箱の伸ばしもしない（[autofit.md](autofit.md)）。

追加オプション:
- `steps`: `header_style: "arrow"` で見出しを工程の矢羽根（先頭は五方向、2つ目以降は山形）にし、間の「›」をなくす

## `matrix` — 2×2 マトリクス
```json
{ "type": "matrix", "title": "見出し", "lead": "（任意）",
  "x_axis": { "label": "モデルの複雑さ", "low": "低", "high": "高" },
  "y_axis": { "label": "データの量", "low": "少", "high": "多" },
  "quadrants": [
    { "heading": "…", "body": "…", "highlight": true },
    { "heading": "…", "body": "…" },
    { "heading": "…", "body": "…" },
    { "heading": "…", "body": "…" }
  ] }
```
領域: `title`, `rule`, `lead`, `grid`, `axis`, `footer_l/r`。`quadrants` は**必ず4個**（左上 → 右上 → 左下 → 右下の順）。4個未満は残りが空象限になり、5個以上は5個目以降が無視され警告が出る。y軸は上が `high`、x軸は右が `high`。`highlight: true` の象限は `highlight_fill`／`hi_heading_color`（accent）で強調する。単純な行列は `table`、2軸の位置づけは `matrix` を使い分ける。軸ラベル 6 個（縦軸の名前・上下の目盛り・横軸の名前・左右の目盛り）の位置は格子（`grid`）からの相対で決まり（`style.axis` のトークン `left_margin` `tick_h` `y_name_dy` など）、`grid.x` を動かしても軸ラベルが付いてくる。強調象限の見出しと本文は、強調の塗りの上で読める色に自動で整う。**自動フィット**: 象限の文（`body_size`）を `grid.min_size`（12）まで縮める。`points` のラベルが 2 行を超えると警告（箱は行数ぶん伸びる）。既定で箱内のコンテンツは縦中央寄せ（`grid.valign: "middle"`）。`style.grid.valign: "top"` にすると上詰めに戻せる。

追加オプション:
- `matrix`: `points: [{"label": "本番ガード", "x": 0.8, "y": 0.9, "highlight": true, "n": 1}]` で格子の上に項目を番号付きの点で置く（`x` は右、`y` は上ほど大きい 0〜1）。散布して優先度を見せるときに使う

## `cards` — ボックスチャート / カードグリッド
```json
{ "type": "cards", "title": "見出し", "lead": "（任意）", "columns": 3,
  "cards": [
    { "heading": "Python", "body": "汎用・データ分析", "items": ["初学者向け", "AI/MLの定番"] },
    { "heading": "Go", "body": "クラウド基盤" }
  ] }
```
領域: `title`, `rule`, `lead`, `grid`, `footer_l/r`。整理軸に沿って要素カードを並べる（`two_column` の一般化）。`columns` で列数を指定（既定 3、数値で渡す）、カード数に応じて行が自動で折り返す。各カードは `heading`＋任意の `body`＋任意の `items`（箇条書き）。目安: **カード3〜6枚**。既定で箱内のコンテンツは縦中央寄せ（`grid.valign: "middle"`）。`style.grid.valign: "top"` にすると上詰めに戻せる。カードごとの色分け（系列色）は無く、既定は全カード同一の配色（`surface` 地）。主役のカードだけ `emphasis`（`true` で濃く塗る / `"accent"` / `"soft"` で淡く）と `span`（占める列数）で強弱を付けられる（1〜2 枚まで。[hero.md](hero.md)）。

**自動フィット**: `body_size` / `heading_size` / `item_size` / `item_gap` を比例して縮め、さらに `pad` を詰める（下限 `grid.min_size` 12。項目は −1、見出しは +4）。カード内の本文の高さは内容の行数から決まる。収まらなければ警告（「カードを N 枚以下に」）。

**薄いカードは自動で詰まる**: 中身が領域の 0.72 倍に満たない（本文 1〜2 行など）とき、まず見出し・本文・項目の文字を**最大 1.6 倍まで**、折り返しが悪くならない（語の途中の折れが増えない・最終行が 1〜2 字にならない）最大の倍率に大きくする。それでもまだ薄ければ、箱の高さを「中身 × 1.3」と「領域の 0.55 倍」の大きいほう（下限 160px）に抑え、本文領域の**縦中央**に置く（同じ並びの箱は同じ高さ。`emphasis` つきでも同じ）。**列数を書いていない**（`columns` も `style.grid.cols` も無い）ときは、2 枚 = 2 列、4 枚 = 2 × 2 にし、3 + 1 に割れない（3 枚・5 枚・6 枚は 3 列）。値は `grid.thin_trigger`（0.72）`thin_grow`（1.6）`thin_k`（1.3）`thin_min_ratio`（0.55）`thin_valign`（`middle`）。`style.grid` に `thin_*` 以外のキーを 1 つでも書いたとき（`cols`・`gap`・文字の大きさ・`h` / `y` / `fit` など）と `columns` を書いたときは、従来の動き（文字は 1.4 倍まで・列数は選び直さない）のまま。`span` で大きさを変えたカードがあるとき・`thin_grow: 1` のときは大きくしない。列数の選び直しだけを止めるなら `meta.layout_overrides.cards.grid.cols_search: false`。アイコンつきのカードの見出しは、右上のアイコンの幅を引いた幅で折り返す。
`style.grid.fit` を `"content"` にすると、文字は大きくせず、箱の高さを最も長いカードに合わせて縮め、余りは上 4 割・下 6 割に配る（下限 `grid.min_h` 160。`"fill"` が既定）。`meta.density: "read"` では既定で `"content"`。それでも中身が 3 項目・各 1〜2 行ほどだと、箱の上下が空く（`check_visual.py` の警告が残ることがある）ので、そのときは `cards` をやめて `bullets` / `summary` / パターンにする。詳細は [autofit.md](autofit.md)。

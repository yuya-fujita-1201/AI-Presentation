# deck.json スキーマリファレンス（v2: パラメーター駆動）

デッキは `<deck_dir>/deck.json` の 1 ファイルで管理する。**内容（コンテンツ）とデザイン（パラメーター）を分離**しており、デザインの微修正は JSON の数値を変えるだけで行える。AI に再生成させる必要はない。

```json
{
  "meta": { ... },
  "slides": [ { "type": "...", ..., "style": { ... } }, ... ]
}
```

## 座標系

- 仮想キャンバスは **1280 × 720 px（16:9）**。すべての位置・サイズ・フォントを px で指定する
- HTML は px をそのまま使い、PPTX は 96dpi で換算（px ÷ 96 = インチ、px × 0.75 = pt）する。座標・配色・フォントサイズの指定は共通ソース（テーマ＋レイアウト＋ deck.json）から解決されるため、HTML と PPTX の大枠のレイアウトは一致する（フォントの実体・画像の等比フィット・一部の図形表現などレンダラ由来の細部差は残る）
- **左右マージンは 72px、コンテンツ幅は 1136px** に統一されている（`title` / `section` / `bullets` / `table` など全タイプ共通のグリッド基準）。新しい領域を `style` で追加するときもこの基準に揃えると崩れにくい

## デザインの3層構造

| 層 | ファイル / キー | 役割 |
|----|----------------|------|
| テーマ | `templates/themes/<名前>.json` | 色トークンとフォント。`meta.theme` で選択 |
| レイアウト既定値 | `templates/layouts/default.json` | スライドタイプごとの全オブジェクト（領域）の位置・サイズ・フォント |
| オーバーライド | `meta.layout_overrides`（デッキ全体）/ `slides[i].style`（スライド個別） | 既定値への差分だけを書く |

解決順: **レイアウト既定値 ← meta.layout_overrides ← slides[i].style**（後勝ち・deep merge）。

全スライド共通の領域として `common.brand`（右上のブランド表記）があり、`meta.layout_overrides.common.brand` で全デッキ共通の位置・サイズを調整できる（3層構造の対象）。

### 微修正の例

```jsonc
// 5枚目のタイトルだけ 4px 下げて 40px にする
"slides": [ ..., { "type": "bullets", "title": "...",
  "style": { "title": { "y": 46, "size": 40 } } } ]

// このデッキ全体で箇条書きの本文を少し小さくする
"meta": { "layout_overrides": { "bullets": { "body": { "size": 22 } } } }
```

領域（`title`, `body`, `table` など）の名前と既定値は `templates/layouts/default.json` を見るのが早い。共通プロパティ: `x` `y` `w` `h`（px）、`size`（フォントpx）、`color` / `fill`（テーマトークン名 or hex 直書き）、`bold`、`align`（left/center/right）、`line_height`、`gap`（箇条書き間隔）など。

## meta

| キー | 必須 | 説明 |
|------|------|------|
| `id` | 省略可 | デッキ ID（出力ファイル名になる）。省略時はフォルダ名を使う。指定する場合は `\ / : * ? " < > \|` と制御文字を含められない（ファイル名として不正なため） |
| `title` | ✅ | デッキタイトル（フッターにも表示） |
| `subtitle` / `author` / `date` | | 補足情報 |
| `theme` | | テーマ名（省略時 `default`）。`templates/themes/` から選択（同梱: `default` / `accenture-purple`） |
| `layout` | | レイアウト名（省略時 `default`） |
| `layout_overrides` | | デッキ全体のレイアウト調整（タイプ名 → 領域 → プロパティ）。`common.brand` も指定可 |
| `brand` | | 全スライド右上に表示する短いブランド表記（例: `ACME`）。アクセント色・太字・右寄せ。位置は `layout_overrides.common.brand` で調整 |

## slides — スライドタイプ一覧

全タイプ共通のオプション: `notes`（スピーカーノート。**HTML でのみ表示**、N キーで開閉。PPTX には出力されない）、`style`（レイアウトオーバーライド）。

`eyebrow`（タイトル上の小さなサブタイトル。15px・アクセント色・太字。章や系列の目印に使う）は、見出し（`chrome()`）を持つほぼ全タイプで指定できる: `bullets` / `two_column` / `table` / `code` / `image` / `image_text` に加え `agenda` / `steps` / `matrix` / `cards` / `swimlane` / `architecture` / `dataflow` / `lifecycle` / `sequence` でも使える（`title` / `section` / `quote` / `closing` のような固有レイアウトのタイプは対象外）。

ページ番号を消したい/変えたいスライドは `style.footer_r.text` に表示文字列を指定する（空文字は不可。既定はページ番号）。

### `title` — 表紙
```json
{ "type": "title", "title": "資料タイトル", "subtitle": "...", "meta": "社内勉強会 / 2026-08" }
```
領域: `bar`（左帯）, `title`, `subtitle`, `meta`

### `section` — 章扉
```json
{ "type": "section", "number": "01", "title": "...", "subtitle": "..." }
```
領域: `bg`, `number`, `title`, `rule`, `subtitle`

### `bullets` — 箇条書き
```json
{ "type": "bullets", "title": "見出し", "lead": "リード文（任意）",
  "bullets": [
    "文字列そのまま",
    { "text": "子項目つき", "children": ["子1", "子2"] },
    { "text": "強調したい行", "bold": true, "size": 26, "color": "accent" }
  ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l`, `footer_r`。項目単位で `size` / `color` / `bold` を上書き可能（子項目も同様）。目安: **3〜6項目、1項目40字以内**（超えると自動的な折返し・縮小はされないため、`check_layout.py` の警告を確認する）。

既定は内容を上詰め（`valign: "top"`）。項目数が少ないスライドはキャンバス下半分が空白になりがちなので、`style.body.valign` を `"middle"` にすると `body` 枠（既定 y=192, h=456）の縦中央に項目群を寄せられる（`two_column` の `left`/`right` と同じ考え方。HTML/PPTX 共通で実際の描画高さに応じて自動的に中央寄せされるため、項目数を変えても再調整不要）。

### `two_column` — 2カラム比較
```json
{ "type": "two_column", "title": "見出し",
  "left":  { "heading": "左見出し", "bullets": ["..."] },
  "right": { "heading": "右見出し", "bullets": ["..."] } }
```
領域: `left` / `right`（ボックス）, `col_heading`, `col_body` ほか。既定は内容を上詰め（`valign: "top"`）。`style.left.valign` / `style.right.valign` を `"middle"` にすると箱内で縦中央寄せになる。

### `table` — 表
```json
{ "type": "table", "title": "見出し", "columns": ["列1", "列2"], "rows": [["a", "b"]],
  "style": { "table": { "row_h": 64, "cell_size": 16, "col_widths": [3, 3, 6], "border_color": "border" } } }
```
領域: `table`（`col_widths` は比率の配列。**要素数は `columns` と一致させること**（不一致はビルドエラー）。各行のセル数も `columns` の数と一致させる。`header_h` / `row_h` で行の高さ、`header_size` / `cell_size` でフォント、`border_color` で罫線色（テーマトークン、既定 `border`））。目安: **6行以内**（超える場合はスライドを分けるか要約する）。

セル全体が `http://` または `https://` のURLなら、HTMLではクリック可能なリンク、PPTXでは外部ハイパーリンクとして自動出力する。説明文にURLを混ぜたセルは自動リンク化しない。

URLを見せず、資料名など別の文字列をリンクにする場合は、セルを `{"text": "表示文字列", "url": "https://..."}` と書く。`url` がHTTP(S) URLでない場合は通常の文字列セルとして出力する。セル値が `null`（JSON の `null`）の場合は空文字として表示される。

行単位の背景色は `style.table.row_fills` で指定する（キーは 0 始まりの行番号の文字列、値はテーマトークン or hex）。指定のない行は従来どおり交互色。意味のある行（例: AI 関連の行）に「しるし」を付ける用途に使う（強調色には `highlight_fill` トークンを推奨）:
```json
{ "type": "table", "...": "...",
  "style": { "table": { "row_fills": { "3": "highlight_fill" } } } }
```

### `code` — コード / 設定例
```json
{ "type": "code", "title": "見出し", "language": "yaml", "code": "type: Concept\n..." }
```
領域: `code`。行数が多いときは `min_size` まで自動縮小（HTML/PPTX 共通ロジック）。折り返しはせずクリップする（HTML/PPTX 共通）ので、1行が極端に長いコードは事前に改行を入れる。

### `quote` — 引用・キーメッセージ
```json
{ "type": "quote", "text": "強調したい一文", "attribution": "出典（任意）" }
```
領域: `mark`, `text`, `attribution`

### `image` — 画像
```json
{ "type": "image", "title": "見出し（任意）", "path": "assets/figure.png", "caption": "..." }
```
`path` はデッキフォルダ配下（`assets/` 推奨）の相対パスのみ（デッキフォルダの外を指すパスや存在しないファイルはビルドエラー）。対応拡張子: png / jpg / jpeg / gif / bmp / svg / webp / tiff。領域 `img`（既定 1136×440px、比率 約2.58:1）の枠内に等比で収まる（拡大・縮小どちらも行う）。**推奨アスペクト比は 4:3 〜 2:1**（例 1024×768、1200×600）。極端な縦長・横長の画像は左右または上下に余白（レターボックス/ピラーボックス）ができる。

**画像アセットはテーマに自動追従しない。** SVG/PNG 等の画像は静的なファイルなので、`meta.theme` を切り替えても配色・背景は変わらない。暗色系テーマ（背景が濃色のテーマ）で白背景の図版を使うと、スライドの中で図版だけ浮いて見える。暗色テーマを使うデッキでは (a) 画像側もそのテーマの背景色に合わせて用意する、(b) 可能なら `swimlane` / `matrix` / `steps` などテーマトークンで自動的に配色されるネイティブ図解タイプを使う、のいずれかを検討する。

### `image_text` — 画像＋パンチライン＋本文（1枚で伝える統合レイアウト）
```json
{ "type": "image_text", "title": "見出し",
  "punch": "一目で伝えたい一文（全幅・太字・アクセント色）",
  "bullets": ["本文（bullets と同じ書式。children 可）"],
  "path": "assets/figure.png", "caption": "画像の下の補足（任意）",
  "image_side": "right" }
```
領域: `title`, `rule`, `punch`（全幅パンチライン）, `body`（本文カラム）, `img`（既定 524×378px）, `caption`, `footer_l/r`。
`image_side` を `"left"` にすると画像と本文の左右が入れ替わる（既定は右）。
**画像だけ・文章だけのページに分離せず、メッセージと図解を1枚に載せたいときはこのタイプを使う。**
画像は 4:3 前後（例: 1024×768）が最も収まりが良い。`path` の制約は `image` タイプと同じ（デッキフォルダ配下・対応拡張子のみ）。

### `closing` — まとめ
```json
{ "type": "closing", "title": "まとめ", "bullets": ["..."], "message": "締めの一言（任意）" }
```
領域: `bg`, `title`, `rule`, `body`, `message`。`message` の縦位置は既定で **`body` の実描画高さの直後**に自動配置される（`follow_body: true`。`body` が短ければ `message` が上に詰まり、長ければ下がる。下限 `min_y`、上限はレイアウトの既定 `y`）。`style.message.y` を明示すればその固定値が優先される。

### `agenda` — アジェンダ / 目次
```json
{ "type": "agenda", "title": "Agenda", "lead": "（任意）",
  "items": [ "はじめに", { "text": "本日の議題", "active": true }, "まとめ" ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。各項目に自動で連番（`01`, `02`…）が付く。`active: true` の項目は面（`active_fill`）で強調され、文字色が `active_color` になる。`bullets` の代替ではなく「番号付き＋現在地ハイライト」が要るときに使う。

**自動2段組・ページ送り**（項目数に応じて自動。**deck.json に書いたスライド数より実際の出力枚数が増えることがある**）:
- 1列あたりの最大行数 `R = floor(body.h / (row_h+gap))`（既定値で **R = 8 行**）。
- 項目数 **N ≤ R** → 1段。**R < N ≤ R×max_cols** → 自動で2段（左列を上から埋めて右列へ）。**N > R×max_cols** → 次ページの agenda に自動で繰り越し（連番は通し、2枚目以降のタイトルに「（続き）」）。
- `body` の `max_cols`（既定 2）/ `row_h` / `gap` / `col_gap` で段数・行ピッチを調整できる。既定では **9〜16 項目=2段、17 項目以上=2ページ目**。

### `steps` — ステップチャート / フロー
```json
{ "type": "steps", "title": "見出し", "lead": "（任意）",
  "steps": [
    { "label": "研究開発", "items": ["基礎研究", "実験・検証"] },
    { "label": "社会実装", "items": ["インフラ整備"] }
  ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。手順・フロー・バリューチェーンを横並びのカードで表現し、カード間をシェブロン（›）で接続する。ステップ数（3〜5推奨）に応じてカード幅は自動調整。各カードはヘッダ（`header_fill`＝primary、`STEP n` は `num_color`）＋本文の箇条書き（`items`）。色はテーマの `primary` / `surface` / `on_primary_soft` に固定されており、カードごとに任意の色を指定するオプションは無い（要素ごとに色を変えたい場合は `image` / `image_text` で図を用意する）。

**カードの高さ**: 既定（`style.body.fit: "content"`）では最も長いカードの内容に合わせて高さを縮め、行全体を領域の上寄り中央に置く（短い内容で下半分が空くのを防ぐ）。下限は `style.body.min_h`（既定 260px）、上限は `body.h`。従来どおり領域いっぱいに描きたいときは `"fit": "fill"`。カードの枠線色は `card_border`（既定 `border` トークン）。

### `matrix` — 2×2 マトリクス
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
領域: `title`, `rule`, `lead`, `grid`, `axis`, `footer_l/r`。`quadrants` は**必ず4個**（左上 → 右上 → 左下 → 右下の順）。4個未満は残りが空象限になり、5個以上は5個目以降が無視され警告が出る。y軸は上が `high`、x軸は右が `high`。`highlight: true` の象限は `highlight_fill`／`hi_heading_color`（accent）で強調する。単純な行列は `table`、2軸の位置づけは `matrix` を使い分ける。既定で箱内のコンテンツは縦中央寄せ（`grid.valign: "middle"`）。`style.grid.valign: "top"` にすると上詰めに戻せる。

### `cards` — ボックスチャート / カードグリッド
```json
{ "type": "cards", "title": "見出し", "lead": "（任意）", "columns": 3,
  "cards": [
    { "heading": "Python", "body": "汎用・データ分析", "items": ["初学者向け", "AI/ML の定番"] },
    { "heading": "Go", "body": "クラウド基盤" }
  ] }
```
領域: `title`, `rule`, `lead`, `grid`, `footer_l/r`。整理軸に沿って要素カードを並べる（`two_column` の一般化）。`columns` で列数を指定（既定 3、数値で渡す）、カード数に応じて行が自動で折り返す。各カードは `heading`＋任意の `body`＋任意の `items`（箇条書き）。目安: **カード3〜6枚**。既定で箱内のコンテンツは縦中央寄せ（`grid.valign: "middle"`）。`style.grid.valign: "top"` にすると上詰めに戻せる。カードごとの色分け（系列色）は無く、全カード同一の配色（`surface` 地）になる。

### `swimlane` — スイムレーン業務フロー
```json
{ "type": "swimlane", "title": "見出し", "lead": "（任意）",
  "cols": 6,
  "phases": ["", "作成", "精緻化", "レビュー", "判定", "次工程"],
  "lanes": [
    { "group": "Japan", "name": "開発T(Lead)" },
    { "group": "Japan", "name": "開発T(Member)" },
    { "name": "AI（Claude Code等）" }
  ],
  "nodes": [
    { "id": "start", "lane": 0, "col": 0, "shape": "terminal", "text": "開始" },
    { "id": "t1", "lane": 1, "col": 1, "shape": "task", "text": "ドラフト作成", "loop": true },
    { "id": "d1", "lane": 1, "col": 2, "shape": "decision", "text": "指摘あり" },
    { "id": "io1", "lane": 2, "col": 1, "shape": "io", "input": ["論点一覧"], "output": ["検討資料"] },
    { "id": "end", "lane": 1, "col": 3, "shape": "terminal", "text": "完了" }
  ],
  "edges": [
    { "from": "start", "to": "t1" },
    { "from": "t1", "to": "d1" },
    { "from": "d1", "to": "end", "label": "Y" }
  ] }
```
領域: `title`, `rule`, `lead`, `flow`, `footer_l/r`。業務フロー・運用フローを **image に頼らずネイティブ描画**する（座標を自動計算するのでズレない）。ノード・レーン帯・矢印はテーマの `primary` / `surface` / `on_primary_soft` / `highlight_fill` / `border` に固定される（系列ごとの色分けはできない。多系列を色分けしたい場合は `image` で図を用意する）。

- **レーン（横帯）＝役割**。`lanes[]` は上から順の行（1個以上必須）。`group`（Lv1）が同じ連続レーンは左端に縦帯でまとめられる。`group` を省けば **Lv1 なしのフラットなレーン** になる（Lv1 のみ・Lv1+Lv2 どちらも可）。
- **配置はグリッド**。各ノードに `lane`（行 index）と `col`（工程＝列 index、0始まり）を指定。**`id` はノード間で重複不可**（重複するとビルドエラー）。列数は `cols`（省略時はノードの最大 col+1。ノードの `col` が `cols` 以上の場合は `cols` を自動拡張して警告）。`phases[]` を書くと上部に工程ヘッダ帯が出る（列と対応、空文字で省略）。
- **ノード形状 `shape`**: `task`（角丸四角・`loop:true` で反復記号／`variant` で `onpf`＝オンラインPF・`onother`＝PF以外・`offline`＝オフラインを色分け）/ `system`（システム・サービス）/ `decision`（ひし形・分岐）/ `terminal`（楕円・前/次ページ等のラベル付き連結）/ `marker`（小さな丸・`kind` で `start`/`end`/`mid`）/ `connector`（ペンタゴン・分岐の遷移先）/ `mail`（メール配信）/ `io`（`input`/`output` の成果物リスト）。
- **エッジ `edges[]`**: `{ from, to, label, style }`。`from`/`to` は存在する `id` を指定する（未知の `id` はビルドエラー）。ノード id 同士を結ぶと、レーンをまたぐ L 字・Z 字の直交矢印を**自動ルーティング**する。`label` は Y/N などの分岐ラベル、`style: "dashed"` で破線（システム操作）になる（既定は実線＝作業の流れ）。
- **凡例 `legend`**: **既定 `true`**。true のとき、そのスイムレーンの**直前に凡例専用ページ（`swimlane_legend`）を自動挿入**する（業務フロー標準記号の一覧：作業3種・システム・分岐・成果物・開始/終了/途中・前/次ページ・遷移先・メール・実線/破線の15種）。**この自動挿入は合計ページ数に影響する（+1枚）**。指定枚数を厳守したい場合はあらかじめ考慮するか、`"legend": false` で凡例ページを省略する。`legend_title` で凡例ページのタイトル、`legend_items` で凡例内容をカスタムできる。
  - `legend_items` の正しい形は **4要素配列の配列**: `[[shape, variant_or_kind, label, description], ...]`（例: `[["task", "onpf", "オンラインPF作業", "..."], ["decision", "", "分岐", "..."]]`）。辞書形式 `{"shape": "...", "variant": "...", "label": "...", "desc": "..."}`（または `kind`/`label`/`desc`）も受理されるが、**要素数の合わない配列やこれ以外の形は文字化けした凡例の原因になる**ので必ず4要素配列（または上記の辞書キー）で書く。
- 色・線幅・ノードサイズは `flow` の各トークンで調整可（`task_onpf_fill` / `task_offline_fill` / `system_fill` / `marker_start` / `connector_fill` / `decision_fill` / `edge_color` / `lane_border`（レーン区切り線の色、既定 `border` トークン）など）。
- **v0.3.0 の変更点**（`architecture` 等の追加にともなう配線エンジン共通化）: 配線が下記「図解タイプ共通」と同じ共通ルーター（`tools/diagram_engine.py`）に置き換わった。見た目はほぼ従来どおりだが、線が途中のノードを横切らなくなり、同じ辺から出る複数の線・同じ回廊を通る線は自動で等間隔にずれ、ラベルは背景ピル付きで重なりにくくなる。
  - `edges[].variant`（`default` / `emphasis` / `security` / `dashed`）と `edges[].arrow`（`end` / `both` / `none`）が使える。従来の `style: "dashed"` は引き続き受理する（両方書くと `style-conflict` の警告になり `variant` を優先する）。
  - ノードの `text` の別名として `label` も受理する。
  - `decision`（ひし形）は箱に内接するサイズで描かれるようになり、HTML と PPTX の大きさが一致する（従来は HTML だけ大きく見えていた）。
  - 反復記号 `loop: true` は右上の丸バッジ（円弧矢印）に変わった。
  - 追加された検証（warning）: ノードの `variant` が `onpf` / `onother` / `offline` 以外（`architecture` 系タイプの `emphasis` 等は swimlane では使えない）、`shape` が未知、`text`/`label` が無い、`edges[].variant` / `edges[].style` の未知値。
  - 凡例ページ（`legend` bool による自動挿入）と凡例記号15種、`groups` を持たない点は変わらない。

### 図解タイプ共通（`architecture` / `dataflow` / `lifecycle`）

この3タイプは同じ描画エンジン（`tools/diagram_engine.py`）を共有し、ノード・エッジの語彙とトークンも共通。タイプごとの違いは行・列の意味づけだけで、詳細は次項以降の各タイプ節を見る。ノード・エッジの見た目トークン（`node_*` / `edge_*` / `label_*` など）は `sequence` の参加者・メッセージにも使われる（自動配線・groups・凡例は grid 系3タイプ専用）。

領域名は共通で `diagram`（既定 `x=72 y=190 w=1136 h=468`。`style.diagram.*` または `meta.layout_overrides.<type>.diagram.*` で調整する）。図全体を `rows`×`cols` のセルに分け、ノードはセル中央に置かれる（`cols`/`rows` は省略可。ノードの最大 `col`/`row`+1、または見出し数から自動算出）。

**ノード `nodes[]`**（lifecycle は `states[]` も同じ形）

| フィールド | 必須 | 説明 |
|---|---|---|
| `id` | ✅ | 一意な id（英数字推奨）。重複は `duplicate-id` エラー |
| `label`（別名 `text`） | 推奨 | 表示名（無いと `missing-label` 警告） |
| `sublabel` | | 小さな補足（1行） |
| `tag` | | 右上の小ピル（例: `"JWT"`） |
| `type` | | `frontend` / `backend` / `database` / `cloud` / `security` / `messagebus` / `external` / `generic`（既定）。**色ではなくアイコンの形**でコンポーネントの役割を表す |
| `variant` | | `default`（既定）/ `emphasis` / `security` / `dashed` / `muted`。**色はこちらが担う** |
| `row` / `col` | | 0始まりの整数。同じ (row, col) の重複は `cell-collision` エラー、負値や非整数は `invalid-position` エラー |

**エッジ `edges[]`**

| フィールド | 必須 | 説明 |
|---|---|---|
| `from` / `to` | ✅ | 既知の `id`（未知は `unknown-endpoint` エラー） |
| `label` | | ラベル文字列 |
| `variant` | | `default` / `emphasis` / `security` / `dashed`。旧 swimlane 互換の `style: "dashed"` も受理（`variant` と両方書くと `style-conflict` 警告、`variant` を優先） |
| `arrow` | | `end`（既定）/ `both` / `none` |
| `from_side` / `to_side` | | `left` / `right` / `top` / `bottom`。他ノードを避けられない場合は無視され `side-ignored` 警告 |
| `via` | | `[[x, y], ...]`（キャンバス絶対 px の経由点）。**最初から書かず、`check_diagram.py` が提示してから 1 つ加える** |
| `label_at` | | `[x, y]`（ラベル中心の固定座標） |
| `route` | | `auto`（既定）/ `straight` |
| `classification` | | `dataflow` 用。ラベルの2行目に小さく表示（例: 「個人データ」） |

**別名**: 列見出し帯は `col_headers`（正式）＝ `stages`（dataflow で自然）＝ `phases`（swimlane 流）のどれでも同じ。行見出しは `lanes: [{"name": "..."}]`（正式。`label` も可）＝ `row_headers`。lifecycle は `states`=`nodes`、`transitions`=`edges`、ノードの `lane`=`row`。dataflow はノードの `stage`=`col`、`flows`=`edges`。

**グループ（境界） `groups[]`**: `{ "label", "kind": "region" | "security" | "zone" | "generic", "nodes": [id, ...] }`。メンバーの外接セル範囲を囲む（`region`=破線、`security`=primary破線、`zone`=surface塗り）。範囲内に非メンバーが混ざると `group-leak` 警告（**本当の所有・信頼・配備の境界だけ**に使い、単なる見た目のグルーピングには使わない）。swimlane の `lanes[].group`（縦帯グループ）とは別概念で、swimlane には `groups` は無い。

**凡例 `legend`**: `"auto"`（既定。`type` が2種以上あると図の下に1行で表示）/ `true` / `false`。**ページを追加しない**（swimlane の `legend` bool＝凡例ページの自動挿入とは意味が違う）。type の表示名既定は「フロント／バックエンド／DB／クラウド／セキュリティ／メッセージ基盤／外部」（`style.diagram.type_labels` で変更可）。

**自動配線**: 列・行のガターとノード中心線を格子にした最短の直交経路を探索し、途中のノードを横切らないルートを優先する（横切ってしまう場合は `edge-through-node` の診断。ビルド自体は止まらず警告として報告される）。同じ辺から出入りする複数の線・同じ回廊を通る線は自動で等間隔にずらす。ラベルは最長セグメントの脇に背景ピル付きで置き、ノード・他ラベルと衝突すれば別候補へ、それでも衝突すれば `label-collision` 警告（`label_at` の候補座標が提示される）。`from == to` の自己ループは右上の小さなコの字で描く。

**主な `style.diagram` トークン**（既定値は `templates/layouts/default.json` 参照）: `node_wr` / `node_hr` / `node_max_w` / `node_max_h` / `node_radius` / `node_pad` / `node_size` / `sub_size` / `tag_size` / `node_fill` / `node_border` / `node_border_w` / `node_color` / `sub_color` / `emphasis_fill` / `emphasis_border` / `security_border` / `dashed_border` / `muted_color` / `tag_fill` / `tag_color` / `icon_size` / `icon_color` / `group_border` / `group_color` / `group_radius` / `security_group_border` / `zone_fill` / `header_h` / `header_fill` / `header_color` / `row_label_w` / `row_fill` / `row_color` / `edge_color` / `edge_w` / `edge_emphasis_color` / `edge_security_color` / `edge_dashed_color` / `edge_return_color` / `label_size` / `label_color` / `label_fill` / `legend_h` / `type_labels`。dataflow 追加: `class_size` / `class_color`。lifecycle 追加: `start_` / `active_` / `waiting_` / `decision_` / `success_` / `failure_` / `neutral_` / `external_` の `_fill` / `_border`、`success_color` / `step_color` / `step_size`。

### `architecture` — システム構成図
```json
{ "type": "architecture", "eyebrow": "SYSTEM", "title": "システム構成",
  "nodes": [
    {"id":"web","type":"frontend","label":"Web","sublabel":"React","row":0,"col":0},
    {"id":"api","type":"backend","label":"API","sublabel":"FastAPI","row":0,"col":1,"variant":"emphasis"},
    {"id":"db","type":"database","label":"PostgreSQL","row":0,"col":2},
    {"id":"auth","type":"security","label":"認証","sublabel":"OAuth","row":1,"col":1}
  ],
  "groups": [{"label":"VPC","kind":"region","nodes":["api","db","auth"]}],
  "edges": [
    {"from":"web","to":"api","label":"HTTPS","variant":"emphasis"},
    {"from":"api","to":"db","label":"SQL"},
    {"from":"auth","to":"api","label":"JWT検証","variant":"security"}
  ] }
```
領域・フィールド・別名・groups・凡例・配線・`style.diagram` トークンは上記「図解タイプ共通」を参照。

目安: ノード12個以下、列6以下（超えると `too-dense` 警告で自動拡張はしない）。

注意: コンポーネントの役割は `type`（アイコンの形）で表し、強調したいノード／境界越えの通信は `variant`（ノードは `emphasis`、エッジは `security` 等）で表す。主経路が1本の左→右（または上→下）になるよう `row`/`col` を揃えると線が交差しにくい。

### `dataflow` — データフロー
```json
{ "type": "dataflow", "eyebrow": "DATA", "title": "データフロー",
  "stages": ["収集", "処理", "保存", "活用"],
  "nodes": [
    {"id":"app","type":"frontend","label":"アプリ","col":0,"row":0},
    {"id":"collector","type":"cloud","label":"収集API","col":1,"row":0},
    {"id":"stream","type":"messagebus","label":"Kafka","col":2,"row":0},
    {"id":"dwh","type":"database","label":"DWH","col":3,"row":0}
  ],
  "edges": [
    {"from":"app","to":"collector","label":"送信"},
    {"from":"collector","to":"stream","label":"正規化"},
    {"from":"stream","to":"dwh","label":"格納","classification":"匿名化済み"}
  ] }
```
領域・フィールド・別名・凡例・配線・`style.diagram` トークンは上記「図解タイプ共通」を参照。`stages` は列見出し（`col_headers` の別名）で、工程を上部の帯に表示する。

目安: 列（`stages` の数、または最大 `col`+1）6以下、ノード12個以下。

注意: `edges[].classification` はラベル下に小さく表示され、データの区分（個人データ・匿名化済み等）を添えるのに使う。`row` は同じ工程内で並行する経路の書き分けに使う（lifecycle の `lane` と役割が近い）。

### `lifecycle` — ライフサイクル / 状態遷移
```json
{ "type": "lifecycle", "eyebrow": "STATE", "title": "承認フローの状態遷移",
  "lanes": [{"name":"主経路"},{"name":"差し戻し"}],
  "states": [
    {"id":"draft","kind":"start","label":"下書き","lane":0,"col":0},
    {"id":"review","kind":"decision","label":"レビュー","lane":0,"col":1},
    {"id":"done","kind":"success","label":"承認済み","lane":0,"col":2},
    {"id":"reject","kind":"failure","label":"差し戻し","lane":1,"col":1}
  ],
  "transitions": [
    {"from":"draft","to":"review"},
    {"from":"review","to":"done","label":"OK","variant":"emphasis"},
    {"from":"review","to":"reject","label":"NG"},
    {"from":"reject","to":"draft","label":"再提出","variant":"dashed"}
  ] }
```
`states`（`nodes` も受理）と `transitions`（`edges` も受理）を使う。`lane` は `row` の別名で、`lanes[]`（1個以上）が縦の帯になる（Archify のように main/terminal の3帯固定ではなく、任意の本数を書ける）。状態の性質は `kind` で描き分ける:

| `kind` | 見た目 |
|---|---|
| `start` | ピル形。accent 枠＋highlight_fill 塗り |
| `active`（既定） | 通常の角丸カード。primary 枠 |
| `waiting` | 破線・muted＋砂時計アイコン |
| `decision` | ひし形（accent 枠・highlight_fill 塗り） |
| `success` | accent 塗り・白文字＋チェック |
| `failure` | 太い破線＋×印 |
| `neutral` | surface 塗り |
| `external` | 破線・muted |

`step`（`"01"` のような番号バッジ）も指定できる。

目安: 状態12個以下。レーンは意味のある単位で3〜4本程度（本数の上限は無いが増やすほど1本あたりの文字が小さくなる）。

注意: 分岐は `decision`、成功/失敗の終端は `success`/`failure` を使い分けると状態の性質が一目で伝わる。

### `sequence` — シーケンス図
```json
{ "type": "sequence", "eyebrow": "FLOW", "title": "ログイン処理のやり取り",
  "participants": [
    {"id":"user","type":"external","label":"利用者"},
    {"id":"web","type":"frontend","label":"Web"},
    {"id":"api","type":"backend","label":"API"},
    {"id":"db","type":"database","label":"DB"}
  ],
  "messages": [
    {"from":"user","to":"web","label":"ログイン"},
    {"from":"web","to":"api","label":"POST /login","variant":"emphasis"},
    {"from":"api","to":"db","label":"SELECT user"},
    {"from":"db","to":"api","label":"rows","variant":"return"},
    {"from":"api","to":"web","label":"200 OK","variant":"return"}
  ] }
```
領域: `diagram`（他3タイプと共通）。上部に参加者カードを横並びに置き、下へライフライン（破線）を伸ばす。

| フィールド | 説明 |
|---|---|
| `participants[].id/label/sublabel/type/variant` | ノードと同じ語彙（`type` のアイコン、`variant` の `emphasis`/`security`/`dashed`/`muted` も使える） |
| `messages[].from/to/label` | 配列の**順に上から等間隔**に描く（`label` が無いと `missing-label` 警告） |
| `messages[].variant` | `default` / `emphasis` / `security` / `dashed` / `return`（戻りは破線の開いた矢印） |
| `activations[]`（任意） | `{ "participant", "from", "to" }`。`from`/`to` は `messages` の index（0始まり）または `id`。ライフライン上の帯 |
| `segments[]`（任意） | `{ "from", "to", "label" }`（同じく index/id）。区間を薄い破線枠で囲み左上にラベル |

`from == to` は自己メッセージ（右側に小さなコの字）として描く。

目安: 参加者7人以下、メッセージ12本以下（超えると `too-dense` 警告）。ラベルが矢印の長さより長いと `label-collision` 警告。

注意: 参加者カード・メッセージの矢印は「図解タイプ共通」節と同じノード/エッジのトークン・語彙で着色されるが、自動配線・groups・凡例（横切り回避を含む）は grid 系3タイプ専用でここには無い（メッセージは常に横一直線）。

## 検証（ビルド時にチェックされる内容）

`build_deck.py` はビルド前に deck.json 全体を検証する。**エラー（`error:`）はビルドを停止**し、**警告（`warning:`）はビルドを続けたまま報告**する。メッセージには可能な限り「N枚目（type=xxx）」が含まれるので、報告されたスライド番号から修正箇所を特定できる。

### エラー（ビルド停止）になる条件
- スライドに `type` が無い、または未知の `type`
- `color` / `fill` / `*_color` / `*_fill` / `marker_color` / `row_fills` の値、bullets 項目の `color` が「テーマ colors のキー」でも「`#RRGGBB` / `#RGB`」でもない（typo 検出。例: `primry` → 「テーマトークン名か #RRGGBB を指定してください」）
- `meta.layout_overrides` のトップキーが未知の `type`
- `table` の各行のセル数が `columns` 数と不一致、`col_widths` の長さが `columns` 数と不一致
- `image` / `image_text` の `path` が未指定、デッキフォルダの外を指す、存在しない、対応外の拡張子
- `swimlane` の `node.id` 重複、`edges` の `from`/`to` が未知 `id`、`lanes` が空、`legend_items` の各要素が4要素配列にも受理される辞書形式にも該当しない
- `architecture` / `dataflow` / `lifecycle` / `sequence`: ノード（`states`/`participants`）の `id` 重複・欠落、`edges`（`transitions`/`messages`）の `from`/`to` が未知 `id`、`row`/`col` が0以上の整数でない、同じ `(row, col)` の重複、`nodes`/`states` が空、`sequence` の `messages[].id` 重複
- `meta.id` に `\ / : * ? " < > |` や制御文字を含む

### 警告（ビルドは続行）になる条件
- `meta.layout_overrides[type]` や `slides[i].style` のトップキー（領域名）が、そのタイプの既定領域に無い（typo の可能性。候補が提示される。例:「'boddy' は bullets の領域名ではありません（候補: body）」）
- `matrix` の `quadrants` が4個以外
- `swimlane` のノードの `col` が `cols` 以上（自動拡張される）
- `architecture` / `dataflow` / `lifecycle` / `sequence` の**配線・ラベル・文字量などの幾何診断**（`too-dense` / `label-collision` / `edge-through-node` / `group-leak` / `out-of-grid` / `node-text-overflow` など）はビルドを止めず警告として報告される。詳しくは次項「図解タイプの診断」を参照
- タイトル・リード文・箇条書き本文・表などが**枠の高さを超える見込み**（文字あふれの推定）。「N枚目（type）: body が枠の高さを約 X px 超える見込み。項目を減らすか style.body.size を下げてください」のように表示される
- `meta.id` がフォルダ名と異なる（省略時はこの警告は出ない）

警告が出たら無視せず、内容に沿って `style` を調整するか項目数を減らして再ビルドする（`create-deck` スキルの手順4、または `review-deck` スキルでまとめて確認できる）。

### 図解タイプの診断（`check_diagram.py`）

`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane` の配線・ラベル・密度は、専用 CLI で deck.json だけを読んでビルドせずに診断できる（Playwright / python-pptx 不要）:

```bash
python "$TOOLS/check_diagram.py" <deck_dir>                 # テキスト報告
python "$TOOLS/check_diagram.py" <deck_dir> --json out.json # JSON 出力（code / subject / evidence / fixes）
python "$TOOLS/check_diagram.py" <deck_dir> --strict        # warning も不合格にする
python "$TOOLS/check_diagram.py" <deck_dir> --slides 3 7    # 対象スライド番号（deck.json 内、1始まり）を絞る
```

**exit 1 になるのは診断に error が1件でもあるとき**（`--strict` を付けると warning も含める）。ここが `build_deck.py` と異なる点として、`edge-through-node` や `node-text-overflow` は診断としては error 相当でも、`build_deck.py` の通常ビルドは（見た目が崩れているだけで座標計算自体は破綻していないため）止めずに警告として報告する。**「`check_diagram.py` は error と言うのにビルドは通る」のはこの理由による意図した挙動**で、矢印の向きやラベルの意味の正しさまでは診断できないので、`check_diagram.py` を通したうえで `preview_deck.py` の目視確認も行う。

修理ループの進め方は `references/diagram-guide.md` の「修理ループ」を参照。

| code | level | 内容 | fixes の例 |
|---|---|---|---|
| `duplicate-id` | error | ノード/状態/メッセージの `id` が重複 | id を一意にする |
| `missing-id` | error | ノードに `id` が無い | 一意な id（英数字）を付ける |
| `empty` | error | `nodes`/`states`/`lanes` が空 | 1個以上書く |
| `cell-collision` | error | 同じ `(row, col)` に2ノード | どちらかの `row`/`col` を変える |
| `invalid-position` | error | `row`/`col` が0以上の整数でない、`lane` が `lanes` の範囲外 | 整数にする／`lanes` に行を追加する |
| `unknown-endpoint` | error（`edges`/`groups`/`messages` の参照）／warning（`activations`/`segments`） | `from`/`to`/`nodes` が存在しない `id` を指す | 存在する `id` を指定する |
| `invalid-group` | error | `groups[]` の要素がオブジェクトでない | オブジェクトにする |
| `edge-through-node` | error（`check_diagram.py`）／ビルドは warning 扱い | エッジが無関係なノードを横切る | `via` を指定する／`row`/`col` を変える／`from_side`/`to_side` を指定する |
| `node-text-overflow` | error または warning（あふれ量による。`check_diagram.py`）／ビルドは warning 扱い | `label`/`sublabel` が箱に収まらない | `label` を短くする／`cols`/`rows` を減らす／`node_size` を下げる |
| `label-collision` | warning | ラベルが他要素と重なる | `label_at` を指定する／`row`/`col` を離す／文言を短くする |
| `crossings` | warning（2箇所以上）／info（1箇所） | エッジ同士が交差する | `row`/`col` を入れ替える／戻りの線を `from_side`/`to_side` で外側に回す |
| `edge-overlap` | warning | 無関係なエッジが同じ線上で重なる | 片方に `via` を指定する／`row`/`col` をずらす |
| `too-dense` | warning | ノード>12／列>6／メッセージ>12／参加者>7 | 要素を減らす／2枚に分ける |
| `group-leak` | warning | `groups` の範囲内に非メンバーが混入 | メンバーの `row`/`col` を隣接させる／範囲外へ動かす |
| `out-of-grid` | warning | `cols`/`rows` を超える `row`/`col` があり自動拡張された | `cols`/`rows` を明示する |
| `short-segment` | info | 8px未満の短いセグメント | `row`/`col` の間隔を広げる／`via` で単純化する |
| `unknown-key` | warning | 未知のフィールド名（typo の可能性。候補が提示される） | `deck-schema.md` の該当タイプのキー名に直す |
| `unknown-type` | warning | ノードの `type` が未対応 | 近い `type` に直す（不明なら省略して `generic`） |
| `unknown-variant` | warning | `variant` が未対応 | `default`/`emphasis`/`security`/`dashed`/`muted` のいずれかにする |
| `unknown-kind` | warning | lifecycle の `kind` が未対応 | 近い `kind` に直す |
| `style-conflict` | warning | `edges` の `style` と `variant` が矛盾 | `variant` だけを書く |
| `side-ignored` | warning | 指定した `from_side`/`to_side` では他ノードを避けられず無視された | 指定を外す／別の辺にする |
| `invalid-side` | warning | `from_side`/`to_side` の値が不正 | `left`/`right`/`top`/`bottom` のいずれかにする |
| `invalid-via` | warning | `via` の形式が不正 | `[[x, y], ...]` の形にする |
| `missing-label` | warning | ノード/メッセージに `label` が無い | 表示名・やり取りの内容を `label` に書く |
| `empty-group` | warning | `groups[].nodes` が空 | ノード id を1個以上書く |

## 文字量・要素量の目安

| タイプ | 目安 |
|---|---|
| `title` の `title` | 25字以内 |
| `lead` | 60字以内 |
| `bullets` の項目数 | 3〜6項目、1項目40字以内 |
| `table` の行数 | 6行以内 |
| `cards` の枚数 | 3〜6枚（列数は3前後） |
| `steps` | 3〜5ステップ |
| `matrix` の `quadrants` | 必ず4個 |
| `architecture`/`dataflow`/`lifecycle` のノード数 | 12個以下 |
| 同上の列（`cols`） | 6以下 |
| `sequence` の参加者 | 7人以下 |
| `sequence` のメッセージ数 | 12本以下 |
| 図解タイプのエッジ `label` | 全角8〜12字程度 |

超える場合はスライドを分ける、`two_column`/`cards` などの別タイプに分割する、または `style` でフォントサイズ・行間を調整する。目安を超えても即エラーにはならないが、`check_layout.py` / ビルド時の文字あふれ警告で検出されやすくなる。

## ビルドとプレビュー

```bash
# <deck_dir> は deck.json があるフォルダ。$TOOLS はビルダーの場所:
#   プラグイン利用時: "${CLAUDE_PLUGIN_ROOT}/tools" / このリポジトリ内: plugins/slide-deck/tools
python "$TOOLS/build_deck.py" <deck_dir>            # HTML + PPTX
python "$TOOLS/build_deck.py" <deck_dir> --html      # HTML のみ（高速）
python "$TOOLS/preview_deck.py" <deck_dir> 5         # 5枚目だけPNG化して目視確認
python "$TOOLS/preview_deck.py" <deck_dir>           # 全スライドPNG化
python "$TOOLS/check_layout.py" <deck_dir>           # 構造チェック（はみ出し・重なり）
python "$TOOLS/lint_deck_text.py" <deck_dir>         # 文言チェック
python "$TOOLS/export_pdf.py" <deck_dir>             # PDF書き出し（要 LibreOffice）
```
`preview_deck.py` / `check_layout.py` / `contact_sheet.py` の総枚数は、`agenda` の自動繰り越しや `swimlane` の凡例自動挿入を含めた**実際のビルド後の枚数**を使う（deck.json に書いた `slides` の要素数そのものではない）。

### 微修正ループ（推奨ワークフロー）

1. `deck.json` の該当スライドの `style`（または内容）だけを編集
2. `build_deck.py <deck_dir> --html` → `preview_deck.py <deck_dir> <番号>` で当該スライドのみ確認
3. 納得したら `build_deck.py <deck_dir>` で PPTX も再生成

ビルドは全体でも1秒未満なので、再生成コストを気にする必要はない。**生成物（build/ 配下）は絶対に直接編集しない**。

## 注意

- PPTX にスピーカーノートは出力しない仕様（python-pptx の notes_slide が Keynote 互換性を壊すため）
- 色は必ずテーマトークン（`primary`, `accent` など）で指定し、hex 直書きはスライド固有の特例に限る（テーマ切替が効かなくなるため）。テーマトークンでも hex でもない値を指定するとビルドエラーになる
- 新しいテーマは `tools/new_theme.py <name>` で雛形を作り、`colors`/`fonts` を編集して `meta.theme` を切り替えるだけでよい。テーマは `default` をベースにマージされ、明示していないトークンは自動導出されるので上書きしたいトークンだけ書けばよい（詳細は `themes.md`）

# deck.json スキーマリファレンス（v2: パラメーター駆動）

デッキは `decks/<デッキ名>/deck.json` の 1 ファイルで管理する。**内容（コンテンツ）とデザイン（パラメーター）を分離**しており、デザインの微修正は JSON の数値を変えるだけで行える。AI に再生成させる必要はない。

```json
{
  "meta": { ... },
  "slides": [ { "type": "...", ..., "style": { ... } }, ... ]
}
```

## 座標系

- 仮想キャンバスは **1280 × 720 px（16:9）**。すべての位置・サイズ・フォントを px で指定する
- HTML は px をそのまま使い、PPTX は 96dpi で換算（px ÷ 96 = インチ、px × 0.75 = pt）するため、**両形式で見た目が一致する**

## デザインの3層構造

| 層 | ファイル / キー | 役割 |
|----|----------------|------|
| テーマ | `templates/themes/<名前>.json` | 色トークンとフォント。`meta.theme` で選択 |
| レイアウト既定値 | `templates/layouts/default.json` | スライドタイプごとの全オブジェクト（領域）の位置・サイズ・フォント |
| オーバーライド | `meta.layout_overrides`（デッキ全体）/ `slides[i].style`（スライド個別） | 既定値への差分だけを書く |

解決順: **レイアウト既定値 ← meta.layout_overrides ← slides[i].style**（後勝ち・deep merge）。

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
| `id` | ✅ | デッキ ID（フォルダ名と一致。出力ファイル名になる） |
| `title` | ✅ | デッキタイトル（フッターにも表示） |
| `subtitle` / `author` / `date` | | 補足情報 |
| `theme` | | テーマ名（省略時 `default`）。`templates/themes/` から選択（同梱: `default` / `accenture-purple`） |
| `layout` | | レイアウト名（省略時 `default`） |
| `layout_overrides` | | デッキ全体のレイアウト調整（タイプ名 → 領域 → プロパティ） |
| `brand` | | 全スライド右上に表示する短いブランド表記（例: `ACME`）。アクセント色・太字・右寄せ |

## slides — スライドタイプ一覧

全タイプ共通のオプション: `notes`（スピーカーノート。**HTML でのみ表示**、N キーで開閉。PPTX には出力されない）、`style`（レイアウトオーバーライド）。

`bullets` / `two_column` / `table` / `code` / `image` / `image_text` では `eyebrow`（タイトル上の小さなサブタイトル。15px・アクセント色・太字）も指定できる。章や系列の目印に使う。ページ番号を消したい/変えたいスライドは `style.footer_r.text` に表示文字列を指定する（空文字は不可。既定はページ番号）。

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
領域: `title`, `rule`, `lead`, `body`, `footer_l`, `footer_r`。項目単位で `size` / `color` / `bold` を上書き可能（子項目も同様）。

### `two_column` — 2カラム比較
```json
{ "type": "two_column", "title": "見出し",
  "left":  { "heading": "左見出し", "bullets": ["..."] },
  "right": { "heading": "右見出し", "bullets": ["..."] } }
```
領域: `left` / `right`（ボックス）, `col_heading`, `col_body` ほか

### `table` — 表
```json
{ "type": "table", "title": "見出し", "columns": ["列1", "列2"], "rows": [["a", "b"]],
  "style": { "table": { "row_h": 64, "cell_size": 16, "col_widths": [3, 3, 6] } } }
```
領域: `table`（`col_widths` は比率の配列。`header_h` / `row_h` で行の高さ、`header_size` / `cell_size` でフォント）

セル全体が `http://` または `https://` のURLなら、HTMLではクリック可能なリンク、PPTXでは外部ハイパーリンクとして自動出力する。説明文にURLを混ぜたセルは自動リンク化しない。

URLを見せず、資料名など別の文字列をリンクにする場合は、セルを `{"text": "表示文字列", "url": "https://..."}` と書く。`url` がHTTP(S) URLでない場合は通常の文字列セルとして出力する。

行単位の背景色は `style.table.row_fills` で指定する（キーは 0 始まりの行番号の文字列、値はテーマトークン or hex）。指定のない行は従来どおり交互色。意味のある行（例: AI 関連の行）に「しるし」を付ける用途に使う:
```json
{ "type": "table", "...": "...",
  "style": { "table": { "row_fills": { "3": "#EAF1F8" } } } }
```

### `code` — コード / 設定例
```json
{ "type": "code", "title": "見出し", "language": "yaml", "code": "type: Concept\n..." }
```
領域: `code`。行数が多いときは `min_size` まで自動縮小（HTML/PPTX 共通ロジック）

### `quote` — 引用・キーメッセージ
```json
{ "type": "quote", "text": "強調したい一文", "attribution": "出典（任意）" }
```
領域: `mark`, `text`, `attribution`

### `image` — 画像
```json
{ "type": "image", "title": "見出し（任意）", "path": "assets/figure.png", "caption": "..." }
```
`path` はデッキフォルダからの相対パス。領域 `img`（既定 1136×440px）の枠内に等比で収まる。
PNG / JPG / SVG に対応（SVG は PPTX ビルド時に自動で PNG 化され `build/.svg-cache/` にキャッシュされる）

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
画像は 4:3 前後（例: 1024×768）が最も収まりが良い。

### `closing` — まとめ
```json
{ "type": "closing", "title": "まとめ", "bullets": ["..."], "message": "締めの一言（任意）" }
```
領域: `bg`, `title`, `rule`, `body`, `message`

### `agenda` — アジェンダ / 目次
```json
{ "type": "agenda", "title": "Agenda", "lead": "（任意）",
  "items": [ "はじめに", { "text": "本日の議題", "active": true }, "まとめ" ] }
```
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。各項目に自動で連番（`01`, `02`…）が付く。`active: true` の項目は面（`active_fill`）で強調され、文字色が `active_color` になる。`bullets` の代替ではなく「番号付き＋現在地ハイライト」が要るときに使う。

**自動2段組・ページ送り**（項目数に応じて自動）:
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
領域: `title`, `rule`, `lead`, `body`, `footer_l/r`。手順・フロー・バリューチェーンを横並びのカードで表現し、カード間をシェブロン（›）で接続する。ステップ数（3〜5推奨）に応じてカード幅は自動調整。各カードはヘッダ（`header_fill`＝primary、`STEP n` は `num_color`）＋本文の箇条書き（`items`）。

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
領域: `title`, `rule`, `lead`, `grid`, `axis`, `footer_l/r`。`quadrants` は **左上 → 右上 → 左下 → 右下** の順。y軸は上が `high`、x軸は右が `high`。`highlight: true` の象限は `hi_fill`／`hi_heading_color`（accent）で強調する。単純な行列は `table`、2軸の位置づけは `matrix` を使い分ける。

### `cards` — ボックスチャート / カードグリッド
```json
{ "type": "cards", "title": "見出し", "lead": "（任意）", "columns": 3,
  "cards": [
    { "heading": "Python", "body": "汎用・データ分析", "items": ["初学者向け", "AI/ML の定番"] },
    { "heading": "Go", "body": "クラウド基盤" }
  ] }
```
領域: `title`, `rule`, `lead`, `grid`, `footer_l/r`。整理軸に沿って要素カードを並べる（`two_column` の一般化）。`columns` で列数を指定（既定 3）、カード数に応じて行が自動で折り返す。各カードは `heading`＋任意の `body`＋任意の `items`（箇条書き）。

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
    { "id": "io1", "lane": 2, "col": 1, "shape": "io", "input": ["論点一覧"], "output": ["検討資料"] }
  ],
  "edges": [
    { "from": "start", "to": "t1" },
    { "from": "t1", "to": "d1" },
    { "from": "d1", "to": "end", "label": "Y" }
  ] }
```
領域: `title`, `rule`, `lead`, `flow`, `footer_l/r`。業務フロー・運用フローを **image に頼らずネイティブ描画**する（座標を自動計算するのでズレない）。

- **レーン（横帯）＝役割**。`lanes[]` は上から順の行。`group`（Lv1）が同じ連続レーンは左端に縦帯でまとめられる。`group` を省けば **Lv1 なしのフラットなレーン** になる（Lv1 のみ・Lv1+Lv2 どちらも可）。
- **配置はグリッド**。各ノードに `lane`（行 index）と `col`（工程＝列 index、0始まり）を指定。列数は `cols`（省略時はノードの最大 col+1）。`phases[]` を書くと上部に工程ヘッダ帯が出る（列と対応、空文字で省略）。
- **ノード形状 `shape`**: `task`（角丸四角・`loop:true` で反復記号／`variant` で `onpf`＝オンラインPF・`onother`＝PF以外・`offline`＝オフラインを色分け）/ `system`（システム・サービス）/ `decision`（ひし形・分岐）/ `terminal`（楕円・前/次ページ等のラベル付き連結）/ `marker`（小さな丸・`kind` で `start`/`end`/`mid`）/ `connector`（ペンタゴン・分岐の遷移先）/ `mail`（メール配信）/ `io`（`input`/`output` の成果物リスト）。
- **エッジ `edges[]`**: `{ from, to, label, style }`。ノード id 同士を結ぶと、レーンをまたぐ L 字・Z 字の直交矢印を**自動ルーティング**する。`label` は Y/N などの分岐ラベル、`style: "dashed"` で破線（システム操作）になる（既定は実線＝作業の流れ）。
- **凡例 `legend`**: **既定 `true`**。true のとき、そのスイムレーンの**直前に凡例専用ページ（`swimlane_legend`）を自動挿入**する（立命館サンプル準拠の記号一覧：作業3種・システム・分岐・成果物・開始/終了/途中・前/次ページ・遷移先・メール・実線/破線の15種）。`"legend": false` で凡例ページを省略。`legend_title` で凡例ページのタイトル、`legend_items` で凡例内容をカスタムできる。
- 色・線幅・ノードサイズは `flow` の各トークンで調整可（`task_onpf_fill` / `task_offline_fill` / `system_fill` / `marker_start` / `connector_fill` / `decision_fill` / `edge_color` など）。

## ビルドとプレビュー

```bash
python3 tools/build_deck.py decks/<デッキ名>            # HTML + PPTX
python3 tools/build_deck.py decks/<デッキ名> --html      # HTML のみ（高速）
python3 tools/preview_deck.py decks/<デッキ名> 5         # 5枚目だけPNG化して目視確認
python3 tools/preview_deck.py decks/<デッキ名>           # 全スライドPNG化
```

### 微修正ループ（推奨ワークフロー）

1. `deck.json` の該当スライドの `style`（または内容）だけを編集
2. `build_deck.py <デッキ> --html` → `preview_deck.py <デッキ> <番号>` で当該スライドのみ確認
3. 納得したら `build_deck.py <デッキ>` で PPTX も再生成

ビルドは全体でも1秒未満なので、再生成コストを気にする必要はない。**生成物（build/ 配下）は絶対に直接編集しない**。

## 注意

- PPTX にスピーカーノートは出力しない仕様（python-pptx の notes_slide が Keynote 互換性を壊すため）
- 色は必ずテーマトークン（`primary`, `accent` など）で指定し、hex 直書きはスライド固有の特例に限る（テーマ切替が効かなくなるため）
- 新しいテーマを作るときは `templates/themes/` に色トークン一式を定義した JSON を追加し、`meta.theme` を切り替えるだけでよい

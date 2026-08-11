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
| `theme` | | テーマ名（省略時 `default`）。`accenture-purple` あり |
| `layout` | | レイアウト名（省略時 `default`） |
| `layout_overrides` | | デッキ全体のレイアウト調整（タイプ名 → 領域 → プロパティ） |

## slides — スライドタイプ一覧

全タイプ共通のオプション: `notes`（スピーカーノート。**HTML でのみ表示**、N キーで開閉。PPTX には出力されない）、`style`（レイアウトオーバーライド）。

### `title` — 表紙
```json
{ "type": "title", "title": "OKF入門", "subtitle": "...", "meta": "社内勉強会 / 2026-08" }
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

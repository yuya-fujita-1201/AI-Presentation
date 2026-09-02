# テーマ（色・フォント）リファレンス

テーマは配色とフォントを定義する JSON。`deck.json` の `meta.theme` にテーマ名を指定して使う。
デッキ本文では色を hex 直書きせず、**テーマトークン名**（`primary` / `accent` 等）で指定する。テーマを切り替えるだけで全スライドの見た目が変わる。

## 仕組み: default をベースにマージ

- どのテーマも **`default` をベースにマージ**される。新しいテーマは**上書きしたいトークンだけ**書けばよく、書かなかったトークンは `default` から継承される。
- `extends` を指定すると、`default` の代わりに任意のテーマを親にできる（例: ブランド色だけ変えた派生テーマ）。
- テーマの探索順は **`SLIDE_DECK_THEMES`（環境変数のディレクトリ）→ `<deck_dir>/themes/` → 同梱 `templates/themes/`**。先に見つかったものが勝つ。

## トークン一覧

### colors（14種）

| トークン | 役割 |
|---|---|
| `background` | スライドの背景色 |
| `surface` | カード・淡い面・補助ブロックの背景 |
| `text` | 本文の基本文字色 |
| `muted` | キャプション等の弱い補助文字色 |
| `primary` | 主要色（見出し帯・章扉・表ヘッダ地などの構造色） |
| `accent` | 強調色（eyebrow・ブランド表記・差し色） |
| `on_primary` | `primary` 地の上に載せる文字色（通常は白） |
| `on_primary_soft` | `primary` 地の上のやや弱い文字・線 |
| `on_primary_muted` | `primary` 地の上のさらに弱い文字・線 |
| `code_bg` | コードブロックの背景 |
| `code_text` | コードブロックの文字色 |
| `table_header_bg` | 表のヘッダ行の背景 |
| `table_header_text` | 表のヘッダ行の文字色 |
| `table_row_alt` | 表の交互行（ゼブラ）の背景 |

### fonts（3種）

| トークン | 役割 |
|---|---|
| `heading` | 見出し用フォント |
| `body` | 本文用フォント |
| `code` | コード・等幅用フォント |

> フォントは PPTX/HTML を開く環境にインストールされている必要がある。社内配布では全員が持つフォント（例: `Meiryo UI` / `Yu Gothic` / `Consolas` 等）を選ぶと崩れにくい。

## 最小の作り方

最低限 `primary` と `accent` を決めれば見た目が大きく変わる。例（差分だけ書く最小テーマ）:

```json
{
  "name": "brand-navy",
  "colors": { "primary": "#1F3A5F", "accent": "#E8A33D" }
}
```

`default` の残りのトークン・フォントはそのまま継承される。

## 追加のしかた

1. 雛形を作る:
   - `python tools/new_theme.py <name>` … `default` の全トークンを写した自己完結テーマ
   - `python tools/new_theme.py <name> --extends accenture-purple` … 継承して差分だけ書く最小テーマ
2. `colors` / `fonts` を編集
3. `deck.json` の `meta.theme` に `<name>` を指定して再ビルド

### サンプルスライドから自動生成する

既存スライド（PPTX / HTML / PDF / 画像）から配色・フォントを抽出してテーマ JSON を作る:

```bash
python tools/theme_from_sample.py <sample-file> --name <name>
```

| 形式 | 抽出方法 | 追加依存 |
|---|---|---|
| `.pptx` `.pptm` | スライド内の**実使用色を面積重みで集計**＋文字フォント（最良品質） | なし |
| `.png` `.jpg` … | 主要色を量子化抽出 | pillow |
| `.pdf` | 先頭ページを描画して主要色＋埋め込みフォント名 | pymupdf |
| `.html` `.htm` | 宣言された `#hex`/`rgb()` と `font-family` を静的抽出 | なし |

- 各形式から `background` / `text` / `primary` / `accent` とフォントを推定し、**共通の色演算で残り14＋3トークンを導出**する（既存テーマに近い一貫した配色になる）。
- 自動推定なので、**出力レポートを確認して `colors`/`fonts` を微調整**すること。特に `primary` と `accent` は取り違えが起きやすい。PPTX が最も正確。
- 依存導入: 画像=`setup_deps.py --pillow`、PDF=`setup_deps.py --pdf`。

### 更新で消えないようにする（配布時）

`new_theme.py` は既定で同梱テーマ置き場に書くが、そこはプラグイン更新で上書きされうる。ユーザー独自テーマを永続させたい場合は専用ディレクトリを使う:

```bash
# 例: ホーム配下に置き、環境変数で常時探索させる
export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"
python tools/new_theme.py brand-navy   # → $SLIDE_DECK_THEMES/brand-navy.json
```

プロジェクトごとに `themes/<name>.json` を置く方法（`<deck_dir>/themes/`）でも自動で拾われる。

## 同梱テーマ

| 名前 | 概要 |
|---|---|
| `default` | すべてのベース（青系） |
| `accenture-purple` | 紫系（`primary #460073` / `accent #A100FF`） |

---
name: add-theme
description: デッキ全体の配色・フォントのセット（テーマ）を新規に追加、または既存テーマへの切替を行う。ユーザーがブランドカラー・独自テーマの追加、テーマ全体の切替を求めたときに使う。単一スライドの色・サイズなど個別要素の微修正は create-deck を使う。テーマは色トークン18種＋フォント3種で構成され、default を継承して差分だけ書ける。
allowed-tools: Bash, Read, Write, Edit
---

# add-theme — 新しいテーマ（色・フォント）を追加する

テーマは **色トークン18種＋フォント3種**の JSON。`default` をベースにマージされ、明示していないトークンはテーマ自身の基本色（`primary`/`accent`等）から自動導出されるので、**新テーマは上書きしたいトークンだけ書けばよい**。トークンの意味・導出規則は `${CLAUDE_PLUGIN_ROOT}/references/themes.md` を参照。

作り方は2通り: **A) サンプルスライドから自動生成**、**B) 雛形から手書き**。

## A) サンプルスライドから作る

既存のスライド（PPTX / HTML / PDF / 画像）を読み込ませ、配色・フォントを抽出してテーマ JSON を自動生成する。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/theme_from_sample.py" <sample-file> --name <name>
#   例: ブランドの .pptx から       … best（実使用色を面積重みで集計）
#   .png/.jpg（要 pillow）/ .pdf（要 pymupdf）/ .html にも対応
```

- 抽出は自動推定なので、**出力されるレポート（検出色・フォント・マッピング）を必ず確認**し、生成された `<name>.json` の `colors`/`fonts` を微調整する（特に `primary` と `accent` は入れ替わることがある。候補が僅差の場合はレポートに「要確認」と出る）。
- 追加依存が要る形式は事前に: 画像=`/slide-deck:setup --pillow`、PDF=`/slide-deck:setup --pdf`。
- 出力先は `--dir` → 環境変数 `SLIDE_DECK_THEMES` → カレントディレクトリの `./themes/` の順（下の「消えないように保存」参照）。

生成後は「B) 3. 使う」以降（コントラスト確認 → 使う）へ進む。

## B) 雛形から手書きで作る

### 1. 雛形を作る
```bash
# default の全トークンを写した自己完結テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name>

# 既存テーマを継承し、差分だけ書く最小テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> --extends accenture-purple
```
`<name>` は kebab-case（例 `brand-navy`）。

### 2. 色・フォントを編集
生成された `<name>.json` の `colors` / `fonts` を編集する。最低限 `primary` / `accent` を決めれば見た目が変わり、表ヘッダ色・コード背景・強調色などの派生トークンも自動的に追随する。トークンの役割・導出規則は `references/themes.md`。

### 3. コントラストを確認する
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <name>
```
`text`/背景 など主要な文字色/背景の組み合わせの WCAG コントラスト比を表示する。4.5 未満（大文字・太字用途は 3.0 未満）は警告として列挙される。`text`/背景 が 4.5 未満の場合は exit 1 になるので、`colors` の明度を調整してから次に進む。

### 4. 使う・代表スライドを目視確認する
デッキの `deck.json` の `meta.theme` に `"<name>"` を指定して再ビルドする。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> <番号...>
```
`title`（primary 地に文字が乗る）・`bullets`・`table`（ヘッダ色）・`matrix`（強調象限）など、primary/accent/highlight_fill を実際に使うスライドを選んで PNG を目視し、文字が読めるか・強調が意図通り見えるかを確認する。Playwright が使えない環境では `export_pdf.py` や `soffice --headless --convert-to png` で代替する。

## テーマを消えないように保存する（配布時の注意）
`new_theme.py` / `theme_from_sample.py` は既定で **`--dir` 明示 → 環境変数 `SLIDE_DECK_THEMES` → カレントディレクトリの `./themes/`** の順に書き込む（プラグイン同梱ディレクトリには `--dir` で明示したときだけ書く）。複数プロジェクトで使い回すユーザー独自テーマを永続させたい場合は、専用ディレクトリを作って環境変数で指定する:

```bash
export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"     # Windows: setx SLIDE_DECK_THEMES "%USERPROFILE%\.slide-deck-themes"
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name>   # SLIDE_DECK_THEMES に出力される
```
ビルダーは **`SLIDE_DECK_THEMES` → デッキ隣の `themes/` → 同梱** の順にテーマを探索する。プロジェクトに `themes/<name>.json` を置く方法でもよい。

## 補足
- テーマ変更は `meta.theme` の切替のみで完結する（deck.json 本文の色指定はトークン名で書くこと）
- `extends` を使うと「ブランド色だけ変えた派生テーマ」を簡単に量産できる

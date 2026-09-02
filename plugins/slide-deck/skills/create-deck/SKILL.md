---
name: create-deck
description: JSON(deck.json)をソースにスライドを HTML / PowerPoint(16:9) にビルドする。ユーザーがプレゼン資料・スライド・デッキの作成や、既存 deck.json の編集・微修正を求めたときに使う。内容もデザインも deck.json のパラメーターで管理し、色はテーマトークンで指定する。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# create-deck — deck.json からスライドをビルドする

スライドは **内容もデザインもすべて `deck.json` のパラメーター**で管理する。仮想キャンバス 1280×720px（16:9）。HTML と PPTX は同じパラメーターを読むので見た目が一致する。

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインの導入先ルート。スクリプトとテンプレートはそこに同梱されている。ユーザーのデッキ（`deck.json`）はユーザーのプロジェクト側に作る。

## 手順

### 0. 依存の確認（初回のみ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --check
```
`python-pptx` が未導入なら初回セットアップを促す（`/slide-deck:setup`、または `python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py"`）。`python` が無ければ `python3` を使う。

### 1. スキーマと見本を把握する
- スキーマの正: `${CLAUDE_PLUGIN_ROOT}/references/deck-schema.md`（全スライドタイプ・`style` で上書きできる領域とプロパティ）
- 全タイプの見本: `${CLAUDE_PLUGIN_ROOT}/examples/template-sample/deck.json`（新規はこれをコピーして書き換えるのが早い）

### 2. deck.json を作る（ユーザーのプロジェクト内）
- `decks/<デッキ名>/deck.json` を作成（場所はユーザーのプロジェクトに合わせる）
- `meta`（`id` / `title` / 任意で `theme`）と `slides` を記述。画像は同じデッキの `assets/` に置き相対参照
- 色は hex 直書きせず**テーマトークン**（`primary` / `accent` 等）で指定。テーマは `meta.theme` で切替（同梱: `default` / `accenture-purple`）。新テーマ追加は `/slide-deck:add-theme`

### 3. ビルド
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>          # HTML + PPTX
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html  # HTML のみ
```
生成物は `<deck_dir>/build/` に出力（ファイル名は `meta.id`）。

### 4. 目視確認と検証
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> [番号...]  # PNG化(要 playwright)
```
PNG を開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を確認する。PPTX は zip 整合と `Presentation()` 再パースで検証し、全スライドで `has_notes_slide` が False であること。

## 微修正のルール（重要）
- 位置・サイズ・フォント・色の変更依頼が来たら、**スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- 微修正後は `--html` で再ビルド → `preview_deck.py <deck_dir> <番号>` で当該スライドだけ再確認してから PPTX を再生成

## 厳守
- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示され、ビルダーが自動処理するので deck.json に書くのは OK
- 図解を使うスライドは原則 `image_text` タイプ（見出し＋本文＋図を1枚に統合）

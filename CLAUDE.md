# AI-Presentation プロジェクト作業ルール

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布するマーケットプレイス。全体像は `README.md`、プラグインの中身は `plugins/slide-deck/README.md`。

他エージェント（Codex 等）向けの入口は `AGENTS.md`（本ファイルは Claude Code 専用）。

## リポジトリの構造

- マーケットプレイス定義: `.claude-plugin/marketplace.json`
- プラグイン本体（自己完結）: `plugins/slide-deck/`
  - `skills/`（create-deck / add-theme / setup）、`tools/`、`templates/`、`references/`、`examples/`
- スクリプトは `plugins/slide-deck/tools/` にあり、テンプレートを `plugins/slide-deck/templates/` から解決する（`ROOT = tools の親 = plugins/slide-deck/`）

## デッキ作成のルール

- スライドの内容・デザインはすべて `deck.json` のパラメーターで管理。スキーマは `plugins/slide-deck/references/deck-schema.md`
- ビルド: `python plugins/slide-deck/tools/build_deck.py <deck_dir>`（環境により `python3`。python-pptx 導入必須）
- 見本は `plugins/slide-deck/examples/template-sample/`。新規デッキはこれをコピーして書き換えるのが早い
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- 画像は `<deck_dir>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **微修正の依頼（位置・サイズ・フォント・色の変更）が来たら、スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`、全デッキ共通なら `plugins/slide-deck/templates/layouts/default.json`
- 微修正後は `build_deck.py <deck_dir> --html` → `preview_deck.py <deck_dir> <番号>` で該当スライドだけ目視確認してから PPTX を再生成する
- 色は hex 直書きせずテーマトークン（`primary` / `accent` 等）で指定。テーマ変更は `meta.theme` の切替のみ（同梱: `default` / `accenture-purple`）
- **PPTX にスピーカーノートを絶対に入れない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示される
- PPTX 生成後の検証: zip 整合（`unzip -t` 等）と `Presentation()` 再パースの 2 点を必ず実施し、全スライドで `has_notes_slide` が False であることを確認する

## テーマ追加のルール

- テーマは `default` をベースにマージされる。新テーマは上書きしたいトークンだけ書けばよい（`extends` で任意の親も可）
- 雛形は `python plugins/slide-deck/tools/new_theme.py <name>`。トークンの意味は `plugins/slide-deck/references/themes.md`
- 探索順は `SLIDE_DECK_THEMES`（環境変数）→ `<deck_dir>/themes/` → 同梱 `templates/themes/`

## プラグインを編集したら

- ローカル検証: `claude --plugin-dir ./plugins/slide-deck`、または `/reload-plugins`
- スキルの description は簡潔に（skill 一覧での表示コストになる）。frontmatter は `name` / `description` / `allowed-tools` を基本にする

## 変更記録

- タスク完了時は該当デッキの deck.json の `meta.date` を更新する。プラグインの機能を変えたら `plugin.json` / `marketplace.json` の `version` を上げる

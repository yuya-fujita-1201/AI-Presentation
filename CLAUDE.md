# AI-Presentation プロジェクト作業ルール

JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み。全体像は `README.md`、スキーマは `docs/deck-schema.md` を参照。

他エージェント（Codex 等）向けの入口は `AGENTS.md`（本ファイルは Claude Code 専用）。ビルド・検証は作業したエージェント自身がローカル実行で完結してよい（手順は `AGENTS.md`「ビルド・検証手順」参照）。

## デッキ作成のルール

- スライドの内容・デザインはすべて `decks/<デッキ名>/deck.json` のパラメーターで管理。スキーマは `docs/deck-schema.md`
- ビルド: `python tools/build_deck.py decks/<デッキ名>`（環境により `python3`。python-pptx 導入必須）
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- 画像は `decks/<デッキ名>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **微修正の依頼（位置・サイズ・フォント・色の変更）が来たら、スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`、全デッキ共通なら `templates/layouts/default.json` を編集
- 微修正後は `build_deck.py <デッキ> --html` → `preview_deck.py <デッキ> <番号>` で該当スライドだけ目視確認してから PPTX を再生成する
- 色は hex 直書きせずテーマトークン（`primary` / `accent` 等）で指定。テーマ変更は `meta.theme` の切替のみ（同梱テーマ: `default` / `accenture-purple`）
- **PPTX にスピーカーノートを絶対に入れない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示される
- PPTX 生成後の検証: zip 整合（`unzip -t` 等）と `Presentation()` 再パースの 2 点を必ず実施し、全スライドで `has_notes_slide` が False であることを確認する

## 見本・スキーマ

- 全スライドタイプの見本は `decks/10-template-sample/deck.json`。新規デッキはこれをコピーして書き換えるのが早い
- 使えるスライドタイプ・`style` で上書きできる領域・プロパティはすべて `docs/deck-schema.md` に集約されている

## 変更記録

- タスク完了時は該当デッキの deck.json の `meta.date` を更新する

# presentation プロジェクト作業ルール

社内勉強会向けの資料プロジェクト。ナレッジは OKF、デッキは JSON ソース管理。全体像は README.md を参照。

Codex など他エージェント向けの入口は `AGENTS.md`（本ファイルは Claude Code 専用）。Codex への作業依頼書は `docs/codex-brief-*.md` に置く。ビルド・検証は作業したエージェント自身がローカル実行で完結してよい（手順は `AGENTS.md`「ビルド・検証手順」参照。Codex はクラウドサンドボックスでは実行できないため、ローカル CLI セッションで行うこと）。

## ナレッジ整理（OKF）のルール

- `knowledge/` は OKF バンドル。すべての非予約 Markdown ファイルに YAML フロントマターを付け、`type` を必ず入れる
- よく使う `type`: `Concept`（概念説明）, `Video`, `Article`, `Book`, `Guide`（手順）, `Topic`（テーマのまとめ）
- 推奨フィールド: `title`, `description`, `tags`, `generated: { by, at }`（v0.2 準拠。旧 `timestamp` は使わない）, 外部資料は `resource:` に URL。`by` の書式は AI が `<producer>/<version>`、人間が `human:<id>`
- バンドルは v0.2 準拠: ルートの `knowledge/index.md` に `okf_version: "0.2"` を宣言済み（frontmatter を書ける index.md はここだけ）
- 1コンセプト = 1ファイル。ファイル間は相対パスの Markdown リンクで接続する（絶対パスは使わない）
- 各ディレクトリの `index.md` は内容一覧（フロントマターなし）、バンドル直下の `log.md` に変更履歴を追記する
- ユーザーから資料リンクを渡されたら: ①内容を取得・要約 → ② `knowledge/sources/` に 1ソース1ファイルで登録 → ③関連テーマのコンセプトファイルに反映 → ④ `index.md` / `log.md` 更新

## デッキ作成のルール

- スライドの内容・デザインはすべて `decks/<デッキ名>/deck.json` のパラメーターで管理。スキーマは `docs/deck-schema.md`
- ビルド: `python3 tools/build_deck.py decks/<デッキ名>`（python3 は `/opt/homebrew/bin/python3`、python-pptx 導入済み）
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- **微修正の依頼（位置・サイズ・フォント・色の変更）が来たら、スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`、全デッキ共通なら `templates/layouts/default.json` を編集
- 微修正後は `build_deck.py <デッキ> --html` → `preview_deck.py <デッキ> <番号>` で該当スライドだけ目視確認してから PPTX を再生成する
- 色は hex 直書きせずテーマトークン（`primary` / `accent` 等）で指定。テーマ変更は `meta.theme` の切替のみ（`accenture-purple` あり）
- **PPTX にスピーカーノートを絶対に入れない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示される
- PPTX 生成後の検証: `unzip -t` と `Presentation()` 再パースの 2 点を必ず実施

## 変更記録

- タスク完了時は `knowledge/log.md`（ナレッジ変更）または該当デッキの deck.json の `meta.date` を更新する

# 工程: brief — Codex清書依頼書の発行

## 入力

- 手本（章構成を踏襲する）: `{{EXEMPLAR_BRIEF}}`
- デッキ: `{{DECK_DIR}}/deck.json`（punch / caption / bullets — 各図の設計根拠）
- 原稿: `{{DRAFT_FILE}}`（各image_textブロックの `- figure:` 行 = 図案の原文）
- 挿絵枚数: {{N_FIGURES}}
- 出力先: `{{BRIEF_PATH}}`

## 規則

- 手本の章立てを踏襲: 依頼概要 → 0.まず読むもの → 1.背景 → 変更禁止 → 触ってよいもの → 2.画像の共通仕様 → 3.良い図の判断基準 → 4以降.各図の個別指示 → 検証手順 → 完了チェックリスト
- **必須4節: 「背景」「変更禁止」「画像」「検証」の語を見出しに含める**（機械ゲートがgrep照合する）
- デッキ内容の説明は `{{KNOWLEDGE_DIR}}/` と deck.json 由来の事実のみ。**あなたの一般知識で補完しない**
- 画像の共通仕様は固定で記載: 4:3（1024×768推奨）・**画像内に文字を入れない**・フラットベクターイラスト風・テーマ準拠配色（仮版はaccenture-purple。**清書時に `meta.theme` の切替でテーマカラー変更可能**なことを明記）
- 対応表: 全{{N_FIGURES}}図について `| 図番号 | スライド番号 | 図案（draftのfigure行原文） | 参考punch |` の表を書く（**行数=図の枚数。ラッパーが照合**）
- **PPTXへのスピーカーノート操作を指示に含めない**（python-pptxのnotes_slideはKeynote互換性を破壊する既知問題。手本と同様に注意書きとして記載する）
- 変更禁止リストに他デッキ（decks/okf-visual*・decks/graph-engineering*）とknowledge/を明記
- 「未実施の項目は未実施と書く」チェックリスト様式を手本から踏襲

## 自己検証（CHECKログ必須）

- 必須4節の見出し存在 / 対応表{{N_FIGURES}}行 / 依頼書中の参照パスが実在すること（Readで確認）

## 出力

- outbox metrics.data: `{"brief": "{{BRIEF_PATH}}"}`

## 許可パス（書き込み）

- `{{BRIEF_PATH}}`・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}` のみ

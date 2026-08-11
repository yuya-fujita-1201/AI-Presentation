---
type: Specification
title: OKF 仕様書 v0.2（SPEC.md、一次情報）
description: GoogleCloudPlatform/knowledge-catalog リポジトリの OKF 公式仕様書。v0.2 の全フィールド定義・予約ファイル規定・v0.1 からの変更点の正となる文書
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
tags: [okf, specification, primary-source, v0.2]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T16:00:00+09:00"
---

# 概要

OKF の公式仕様書（一次情報）。全13セクション構成で、§13 が「Changes from v0.1」。リポジトリ直下には仕様書のほか bundles/（サンプルバンドル）、src/reference_agent/（参照実装エージェント）、tests/ がある。

# 要点（2026-08-06 参照時点）

- 必須フィールドは v0.2 でも `type` のみ。「a concept carrying just `type` is fully conformant」と明記
- v0.2 の信頼性フィールド（すべて小文字スネークケース）:
  - `sources` — 出所。各項目は `id` / `resource` / `title` / `author` / `usage_count` / `last_modified`、全体に `usage_window: { from, to }`
  - `generated: { by, at }` — 誰がいつ生成したか
  - `verified: { by, at }`（複数可のリスト形式もあり）— 誰がいつ確認したか
  - `status: draft | stable | deprecated`（デフォルトは stable）
  - `stale_after: YYYY-MM-DD` — 絶対日付での陳腐化日
- `type: Attested Computation` — 固有フィールドは `runtime`（bigquery / postgres / dbt / python / Looker）、`parameters`、`computation`、`executor`（`resource` と `receipt`）、`attester`
- actor の書式慣例: AIツールは `<producer>/<version>`、人間は `human:<id>`、自動処理は `process:<id>`
- バンドルのバージョン宣言は **バンドルルートの index.md の frontmatter に `okf_version: "0.2"`**。index.md に frontmatter を書けるのはこの1箇所だけ
- 予約ファイル規定: index.md はセクション見出し + 「リンク + 説明」のリスト。log.md は `## YYYY-MM-DD` 見出し（新しい順）+ `**Update**:` / `**Creation**:` 形式の箇条書き
- v0.1 からの破壊的変更は2つ: `timestamp` → `generated.at`（旧記法へのフォールバック可）、本文の `# Citations` → frontmatter の `sources`（旧記法も解析可）。それ以外は「carried forward unchanged」

# 活用先

- [okf/v02-changes.md](../okf/v02-changes.md) の正フィールド名の根拠
- [okf/file-format.md](../okf/file-format.md)、[okf/directory-structure.md](../okf/directory-structure.md) の仕様裏付け

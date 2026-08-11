---
type: Article
title: Open Knowledge Format (OKF) v0.1 ガイド（Classmethod）
description: OKF v0.1 の仕様を実装者視点で整理。準拠条件 3 点、予約ファイル、相対パスリンク推奨などの実務情報
resource: https://dev.classmethod.jp/articles/open-knowledge-format-okf-v01-guide/
tags: [okf, specification, guide]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T14:00:00+09:00"
---

# 要点

- OKF は 2026-06-12 に Google Cloud が公開。v0.1 はドラフト版でベンダー中立のオープン仕様
- 設計思想: 最小限の意見性（必須は `type` のみ）/ プロデューサー・コンシューマー独立 / フォーマットでありプラットフォームではない
- 準拠条件 3 点: ①全ての非予約 MD が解析可能な YAML フロントマターを持つ ②全フロントマターが空でない `type` を持つ ③予約ファイルが規定構造に従う
- 予約ファイル: `index.md`（内容一覧・フロントマターなし）、`log.md`（変更履歴）
- 他標準との関係: MCP（補完）、llms.txt（補完）、AGENTS.md（OKF が標準化する対象パターン）
- 実装上の注意: リファレンス実装のビジュアライザーは絶対パスリンクをエッジ生成対象外とする既知問題があり、**相対パス（./customers.md）での記述が推奨**

# 活用先

- [okf/design-principles.md](../okf/design-principles.md)、[okf/file-format.md](../okf/file-format.md)、[okf/directory-structure.md](../okf/directory-structure.md)

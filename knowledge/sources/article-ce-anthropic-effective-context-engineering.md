---
type: Article
title: "Effective context engineering for AI agents"
description: "Anthropic Applied AIチームによる公式解説。コンテキストを推論時にモデルへ渡る情報全体と捉え、必要十分で高シグナルな情報を選択・維持する設計原則、Just-in-Time取得、圧縮、外部メモリ、サブエージェント分離を整理している。"
source_id: CE-S01
site: Anthropic
published: "2025-09-29"
retrieved: "2026-08-14"
resource: "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents"
origin: "web:anthropic.com"
source_tier: primary
tags: [context-engineering, agents, context-window, retrieval, compaction, memory]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Anthropicが、プロンプトエンジニアリングを「指示の書き方・構造化」、コンテキストエンジニアリングを「推論時にモデルへ渡す情報全体の選択と維持」と区別して解説した記事。対象にはシステム指示、ツール定義、MCP、外部データ、メッセージ履歴などが含まれ、エージェントの各推論時点で何を入れるかを繰り返し調整する営みとして説明している。

# 要点

- コンテキストは推論時に利用されるトークンの集合であり、量を増やすだけではなく、期待する振る舞いに寄与する情報を選ぶ必要がある。
- 指針は「望む結果を得る確率を高める、できるだけ小さな高シグナルの情報集合」。ただし「小さい」は単に短いことではなく、必要な情報を欠かさないことを含む。
- 指示、ツール、例、履歴はそれぞれコンテキストを消費する。曖昧なツール群や例外の羅列は、選択を難しくし保守性も落とす。
- すべてを先に投入する方式だけでなく、ファイルパス、リンク、識別子などの軽量な手掛かりを渡し、必要になった時点で取得するJust-in-Time方式と段階的開示を紹介している。
- 長時間タスクの対策として、履歴の圧縮、構造化ノート、サブエージェントへの分離を区別している。圧縮は情報を失い得るため、保持対象を評価しながら調整する必要がある。

# 適用範囲と留保

- Anthropicの製品開発経験を基にした実務ガイドであり、すべてのモデル・タスクに同じ最適解を保証する比較実験ではない。
- 記事中の「attention budget」や性能劣化の説明は設計上の有用な比喩・観測だが、各モデルの内部注意量を直接測る共通指標ではない。
- Just-in-Time取得は常に優れるわけではない。追加の探索時間、取得失敗、ツール誤用があり、事前投入とのハイブリッドが適する場合がある。
- 圧縮、メモリ、サブエージェントは別の仕組みである。圧縮は現在の履歴を要約し直す操作、メモリはウィンドウ外に情報を保存・再取得する仕組み、サブエージェントは作業コンテキストを分離する構成である。

# 原文の根拠箇所

- **定義とPEとの関係**: `Context engineering vs. prompt engineering`
- **必要十分・高シグナル**: `The anatomy of effective context`
- **必要時取得と段階的開示**: `Context retrieval and agentic search`
- **圧縮損失・外部ノート・分離**: `Context engineering for long-horizon tasks` の `Compaction`、`Structured note-taking`、`Sub-agent architectures`

# デッキで安全に使える表現

- 「コンテキストエンジニアリングは、AIが次の判断に使う情報を、必要十分な形で選び直し続ける設計です。」
- 「大切なのは、情報量の最大化ではなく、必要な情報を欠かさずノイズを減らすことです。」
- 「全部を貼る、必要時に取りに行く、途中で圧縮する、別の作業空間に分ける。用途の違う手段を組み合わせます。」

# 活用先

- [../context-engineering/what-is-context-engineering.md](../context-engineering/what-is-context-engineering.md) — プロンプトとコンテキストの役割差、推論時の情報全体という定義
- [../context-engineering/context-components.md](../context-engineering/context-components.md) — システム指示、ツール、外部データ、履歴を含む推論時コンテキスト
- [../context-engineering/selection-and-sufficiency.md](../context-engineering/selection-and-sufficiency.md) — 必要十分・高シグナル・段階的開示・Just-in-Time取得
- [../context-engineering/context-window-and-attention.md](../context-engineering/context-window-and-attention.md) — 有限な注意予算と、容量を最大まで埋めない設計原則
- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — 圧縮（コンパクション）の役割、長期作業での取りこぼし注意という原則の根拠
- [../context-engineering/context-layers-and-intervention.md](../context-engineering/context-layers-and-intervention.md) — Write/Select/Compress/Isolateという4戦略の名称がこの一次資料自体には登場しないという帰属の留保（節構成はCompaction／Structured note-taking／Sub-agent architectures）
- [../context-engineering/long-horizon-and-tools.md](../context-engineering/long-horizon-and-tools.md) — 長期タスクでの段階的開示と必要時取得
- [../context-engineering/context-rot-and-editing.md](../context-engineering/context-rot-and-editing.md) — 有限なattention budgetという捉え方と、それが内部注意量の共通指標ではないという留保、渡す量を増やすことが単調に品質を上げるわけではないという設計原則の根拠

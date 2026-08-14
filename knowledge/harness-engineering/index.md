# harness-engineering — ハーネスエンジニアリングについてのナレッジ

AIエージェントが動く「環境そのもの」を設計対象にする考え方「ハーネスエンジニアリング」についてまとめたディレクトリ。arXiv論文 "AI Harness Engineering"、Anthropic公式のClaude Code / Agent SDKドキュメント、実務者による解説記事・動画（[../sources/index.md](../sources/index.md) 参照）を情報源とする。

想定読者は、チャット型のAIは使ったことがあるが、AIに手を動かさせる「エージェント的な使い方」はこれからという人。道具・権限・制限・ルールという4つの側面から、事故を起こさずにエージェントを働かせる環境の作り方をたどる。

## 内容

- [what-is-harness-engineering.md](./what-is-harness-engineering.md) — ハーネスエンジニアリングとは何か。論文の形式的定義と解説動画の4要素整理、他の「〇〇エンジニアリング」とのスコープ差、このバンドルの地図
- [why-harness-matters.md](./why-harness-matters.md) — なぜモデル単体では足りないのか。能力ギャップの所在と、人間が無自覚に埋めているランタイム支援
- [harness-responsibilities-and-ladder.md](./harness-responsibilities-and-ladder.md) — ハーネスの11責務とH0〜H3ラダー。「成果物ではなく証拠を評価する」トレースベース評価と、Agent SDKの機能との対応
- [tools-and-mcp.md](./tools-and-mcp.md) — 道具の設計。組み込みツール／MCP／WebMCP／スキルの4層と、道具を増やすことが事故の面積を増やすという緊張
- [permissions-design.md](./permissions-design.md) — 権限の設計。deny→ask→allowの評価順序と、「守らせるのはAIではなくソフトウェア」という原則
- [settings-scopes-and-governance.md](./settings-scopes-and-governance.md) — 設定の4スコープ、単一値の優先順位、配列・Permission・security keyの個別合成規則。「どの層に何を書くか」を統制設計として読む
- [sandbox-and-isolation.md](./sandbox-and-isolation.md) — 制限の最終防壁。OS／process sandbox・通常OCIコンテナ・gVisor等のsandboxed runtime・VM／microVMの境界と、権限設計との役割分担、最小権限の原則
- [project-memory-and-rules.md](./project-memory-and-rules.md) — CLAUDE.md／Rules／Skills／Hooksの内容と読込・制御機構を分け、AGENTS.md互換、段階的開示、継続メンテを整理

## 読む順番

what-is-harness-engineering → why-harness-matters → harness-responsibilities-and-ladder → tools-and-mcp → permissions-design → settings-scopes-and-governance → sandbox-and-isolation → project-memory-and-rules の順に読み進めるとよい。理由づけは[what-is-harness-engineering.mdの「読む順番の提案」](./what-is-harness-engineering.md#読む順番の提案)を参照。

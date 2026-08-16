# graph-engineering — グラフエンジニアリングについてのナレッジ

2026年7月に急速に広まった、複数のAIエージェントの分担・接続を設計する考え方「グラフエンジニアリング」についてまとめたディレクトリ。YouTube解説動画（[../sources/index.md](../sources/index.md) の「動画（グラフエンジニアリング）」参照）に加え、Anthropic・OpenAIの公式ドキュメントとarXiv論文を情報源とする。

## 内容

入口は [overview.md](./overview.md)（定義・登場の経緯・バンドルの地図）。以下は overview.md の順序表と同じ並びで、各ファイルの見出し語だけを挙げる。内容説明と読む順番の根拠は overview.md 側で一元管理しており、ここでは重複させない。

1. [term-lineage-and-layers.md](./term-lineage-and-layers.md) — 用語の系譜と5段階
2. [graph-primitives.md](./graph-primitives.md) — ノード・エッジ・状態・DAGの語彙
3. [loop-vs-graph-decision.md](./loop-vs-graph-decision.md) — ループかグラフかの判断
4. [multi-agent-break-even.md](./multi-agent-break-even.md) — 増やして得かの損益分岐点
5. [roles-and-orchestration.md](./roles-and-orchestration.md) — 役割分担とオーケストレーション
6. [handoffs-and-ownership.md](./handoffs-and-ownership.md) — 最終回答の所有権
7. [workflow-patterns-catalog.md](./workflow-patterns-catalog.md) — つなぎ方の型カタログ
8. [relationship-graph-for-operations.md](./relationship-graph-for-operations.md) — 業務運用グラフの設計
9. [subagent-design-in-practice.md](./subagent-design-in-practice.md) — サブエージェント設計の実務
10. [verification-and-testing.md](./verification-and-testing.md) — 検証レイヤーの設計
11. [verification-gates-and-evidence.md](./verification-gates-and-evidence.md) — 検証をゲートにする
12. [failure-taxonomy-and-debugging.md](./failure-taxonomy-and-debugging.md) — 失敗の分類とデバッグ
13. [knowledge-graph-as-memory.md](./knowledge-graph-as-memory.md) — 記憶としてのナレッジグラフ
14. [risks-and-safeguards.md](./risks-and-safeguards.md) — リスクと歯止め（総括）

## 読む順番

[overview.md](./overview.md) の「このバンドルの地図」節にある14本の順序表と「読む順番の提案」に従うこと。読む順番はこのファイルではなく overview.md 側で一元管理する。

# graph-engineering — グラフエンジニアリングについてのナレッジ

2026年7月に急速に広まった、複数のAIエージェントの分担・接続を設計する考え方「グラフエンジニアリング」についてまとめたディレクトリ。YouTube解説動画（[../sources/index.md](../sources/index.md) の「動画（グラフエンジニアリング）」参照）に加え、Anthropic・OpenAIの公式ドキュメントとarXiv論文を情報源とする。

## 内容

- [overview.md](./overview.md) — グラフエンジニアリングとは何か。定義・登場の経緯・このバンドルの読み方
- [term-lineage-and-layers.md](./term-lineage-and-layers.md) — 用語の系譜と5段階（プロンプト・コンテキスト・ハーネス・ループ・グラフ）。入れ子説と3層説の両論
- [graph-primitives.md](./graph-primitives.md) — グラフの基本要素。ノード・エッジ・状態・DAGと依存関係の描き方、偽エッジテスト
- [loop-vs-graph-decision.md](./loop-vs-graph-decision.md) — ループかグラフか。使い分けの判断基準と「グラフにしない方がいい時」
- [roles-and-orchestration.md](./roles-and-orchestration.md) — 役割分担とオーケストレーション。Manager/Worker/Verifier、CAID、アドバイザー/オーケストレーターパターン
- [relationship-graph-for-operations.md](./relationship-graph-for-operations.md) — 業務運用グラフの設計。目的・担当・作業・根拠・承認の5種ノードとコンテキストパック
- [verification-and-testing.md](./verification-and-testing.md) — 検証レイヤーの設計。自己修正の限界（RefineBench）と検証エージェント・テスト手法
- [knowledge-graph-as-memory.md](./knowledge-graph-as-memory.md) — もう1つのグラフ。記憶としてのナレッジグラフ、autoresearch/AgentHub、実行DAGとの分離
- [risks-and-safeguards.md](./risks-and-safeguards.md) — リスクと歯止め。グラフが増幅する失敗、アンカー、コスト、「グラフは提案、確定は人間」
- [workflow-patterns-catalog.md](./workflow-patterns-catalog.md) — つなぎ方の型カタログ。Anthropic公式の5つのワークフローパターンとダイナミックワークフローの6つの編成型、トポロジーの自動最適化
- [multi-agent-break-even.md](./multi-agent-break-even.md) — マルチエージェント化の損益分岐点。90.2%改善と15倍トークン、45%ルール、増やす前に確認する4条件
- [failure-taxonomy-and-debugging.md](./failure-taxonomy-and-debugging.md) — 失敗の分類とデバッグ。MASTの3カテゴリ14モード、AgentErrorTaxonomyの5領域、カスケード失敗の切り分け

## 読む順番

初めての人は overview → term-lineage-and-layers → graph-primitives → loop-vs-graph-decision の順で基礎を固め、その後 roles-and-orchestration → relationship-graph-for-operations → verification-and-testing で設計手法へ、最後に knowledge-graph-as-memory → risks-and-safeguards で視野を広げると全体像がつかめる。

公式ドキュメント・論文を根拠にした後半3本は、この流れに次のように差し込むとよい。loop-vs-graph-decision の直後に **multi-agent-break-even**（そもそも増やして得かを数字で確認する）、roles-and-orchestration の直後に **workflow-patterns-catalog**（つなぎ方の型を選ぶ）、verification-and-testing の直後に **failure-taxonomy-and-debugging**（失敗を分類して原因を切り分ける）。

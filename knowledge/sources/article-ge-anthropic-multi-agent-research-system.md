---
type: Article
title: How we built our multi-agent research system
description: Anthropic公式。リードエージェントがサブエージェント群に探索を委任するオーケストレーター・ワーカー構成と、内部評価による90.2%の性能改善・約15倍のトークン消費という実測値、開発中の失敗事例と対処、プロンプトエンジニアリング上の教訓を解説する
site: Anthropic
published: unknown
retrieved: 2026-08-16
resource: https://www.anthropic.com/engineering/multi-agent-research-system
origin: "web:anthropic.com"
source_tier: secondary
tags: [graph-engineering, multi-agent, orchestration, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

Anthropic公式が公開する「How we built our multi-agent research system」は、マルチエージェント構成による研究システムの設計を解説する記事である。同記事は、リードエージェントが調査戦略を立て複数のサブエージェントに探索を委任するオーケストレーター・ワーカー構成、内部評価による性能改善の実測値、開発中に直面した失敗事例とその対処、プロンプトエンジニアリング上の教訓、そして本番運用における状態管理・可観測性・デプロイメントの設計判断という5つの観点から、単一エージェントでは扱いきれない探索空間の広い調査タスクにマルチエージェント構成がどう機能するかを説明している。

# 要点

## アーキテクチャ: オーケストレーター・ワーカーパターン

同記事は、リードエージェント(Claude Opus 4)がユーザーのクエリを分析して戦略を立て、サブエージェント(Claude Sonnet 4)を生成して並列に異なる側面を探索させるオーケストレーター・ワーカーパターンを採用していると説明している。処理フローはユーザークエリ→リードエージェント→複数のサブエージェント→結果統合→引用エージェントによる最終処理という順に進むとしている。

> 引用: 「lead agent analyzes it, develops a strategy, and spawns subagents to explore」

またコンテキストウィンドウの超過に備え、リードエージェントが立てた計画をメモリ層に保存する仕組みも実装していると述べている。

## 性能評価とトークン消費

Anthropicは、内部評価においてOpus 4をリードエージェント・Sonnet 4をサブエージェントとする多エージェント構成が、単一のOpus 4エージェント構成に対し90.2%の性能改善を示したと報告している。

> 引用: 「In our evaluations, Claude Opus 4 as the lead agent with Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2%. Multi-agent systems use about 15× more tokens than chat interactions.」

評価にはLLM-as-judgeを用い、事実性・引用精度・完全性・ソース品質・ツール効率性の5項目を0.0〜1.0でスコアリングしたとしている。開発初期は「about 20 queries representing real usage patterns」という小規模テストから開始し、人間評価も併用することで自動評価が見逃す幻覚回答や情報源選択の偏りといったエッジケースを検出したと説明している。BrowseComp評価の分散分析では、トークン使用量単独で分散の80%を説明でき、残りは「the number of tool calls and the model choice」で説明されるとしている。トークン消費については、通常のチャットと比較して一般的なエージェントは約4倍、マルチエージェントシステムでは約15倍のトークンを消費すると述べており、この倍率は「tasks where the value of the task is high enough to pay for」という経済性の条件を満たす場合にのみ正当化されるとしている。

## 失敗事例と対処

Anthropicは、開発初期段階で単純なクエリに対して50個ものサブエージェントを生成してしまう問題が発生し、複雑度に応じたスケーリングルールを組み込むことで対処したと説明している。サブエージェント間で調査が重複する問題には、詳細なタスク説明と役割分担の明示で対応し、低品質なSEO最適化コンテンツを優先して選んでしまう問題にはソース品質のヒューリスティックを追加したとしている。加えて「agents continuing when they already had sufficient results」という、十分な結果が得られても探索を継続してしまう非効率も観察されたと述べている。

## プロンプトエンジニアリングの教訓

同記事は8原則のうち複数を紹介している。Consoleでプロンプトとツール環境を正確に再現するシミュレーション駆動開発を第一に挙げ、サブエージェントへの委譲においては目的・出力形式・ツール指定・境界を明示する必要があるとし、「simple, short instructions like 'research the semiconductor shortage'」のような曖昧な指示では不十分だと述べている。タスクの複雑さに応じて努力配分を変える必要があるとし、単純な事実確認には1エージェントによる3〜10回のツールコール、複雑な研究には10以上のエージェントによる明確な分業を割り当てるとしている。またツールの説明が不明瞭だと「agents encounter unseen tools...completely wrong paths」という誤動作が起きると指摘し、Claude自身にプロンプトの改善を提案させる自己改善メカニズムを導入したところ、ツール説明の改善によって40%のタスク完了時間短縮を達成したと報告している。さらに並列ツール実行(リードエージェントは3〜5個のサブエージェントを並列生成し、サブエージェントは3つ以上のツールを並列実行する)により「cut research time by up to 90%」を実現したとしている。

## 本番運用の設計判断

状態管理については「we need to durably execute code and handle errors along the way」という方針のもと、再開可能な実行パターン(チェックポイント機構)を採用し、エラー発生時はリスタートではなく適応的に処理すると説明している。可観測性については本番トレースを導入しつつ「without monitoring the contents of individual conversations」という形でユーザーのプライバシーを保全しているとしている。デプロイメントでは、ステートフルな実行中のエージェントを保護するため「gradually shifting traffic from old to new versions」というレインボーデプロイメントを採用しているとしている。実行フローについては現状同期実行(リードエージェントがサブエージェント群の完了を待ってから次に進む)であり「create bottlenecks in the information flow」という課題があるため将来的な非同期化が検討されているが、結果の調整や状態の一貫性が複雑化する点が課題として挙げられている。

# 活用先

- [../graph-engineering/multi-agent-break-even.md](../graph-engineering/multi-agent-break-even.md) — 90.2%の性能改善と15倍のトークン消費という引用、オーケストレーター・ワーカー構成、LLM-as-judgeによる5項目評価と約20クエリからの開始、トークン使用量が分散の80%を説明するという分析、「タスクの価値が支払いに見合う場合にのみ正当化される」という経済性条件の主根拠
- [../graph-engineering/failure-taxonomy-and-debugging.md](../graph-engineering/failure-taxonomy-and-debugging.md) — 実地の失敗事例（単純なクエリへの50サブエージェント生成、調査の重複、SEO最適化コンテンツの優先、十分な結果があっても探索を継続、ツール説明の不明瞭さと改善による40%の時間短縮）と、委譲時に目的・出力形式・ツール指定・境界を明示すべきという教訓を、MAST／AgentErrorTaxonomyの分類に対応づける実例として使用
- [../graph-engineering/risks-and-safeguards.md](../graph-engineering/risks-and-safeguards.md) — 動画（Caleb Writes Code、auto字幕）経由で紹介されていた「マルチエージェントはチャット比15倍のトークン」という数値に対する公式出典としての裏付け
- [../graph-engineering/handoffs-and-ownership.md](../graph-engineering/handoffs-and-ownership.md) — 処理フロー（ユーザークエリ→リードエージェント→複数サブエージェント→結果統合→引用エージェントによる最終処理）が最終回答の所有権をリードに残すマネージャー型の実例にあたることの根拠、および同期実行が情報フローのボトルネックを作るという課題と非同期化検討の根拠

---
type: Article
title: "GPTSwarm: Language Agents as Optimizable Graphs"
description: arXiv論文（ICML 2024採録）。単一エージェントおよび複数エージェント(スワーム)を有向非環グラフとして統一的に表現し、ノードのプロンプトとエッジ(通信トポロジ)の両方を自動最適化できると主張している。
site: arXiv / Proceedings of the 41st International Conference on Machine Learning (ICML 2024)
published: unknown
retrieved: 2026-08-16
resource: https://arxiv.org/abs/2402.16823
origin: "web:arxiv.org"
source_tier: primary
tags: [graph-engineering, multi-agent, graph-optimization, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

本論文は、LLMベースのエージェントを計算グラフとして統一的に表現するフレームワーク「GPTSwarm」を提案している。著者らは、単一エージェントおよび複数エージェント(スワーム)を有向非環グラフとして統一的に表現し、ノードのプロンプトとエッジ(通信トポロジ)の両方を自動最適化できると主張している。

> 引用: 「Various human-designed prompt engineering techniques have been proposed to improve problem solvers based on Large Language Models (LLMs), yielding many disparate code bases.」

# 要点

## 統一グラフ表現: DAGとしてのエージェント・スワーム

著者らは、単一エージェントを有向非環グラフ(DAG) G=(N,E,F,o)として定義すると説明している。ノードNはLLM推論・ツール使用・関数呼び出しなどの操作を表し、エッジEはノード間の情報フローを表す。入力xに対してトポロジカルソート順に各ノードを実行し、先行ノードの出力を後続ノードの文脈として利用するとしている。さらに、K個のエージェントを組み合わせた「スワーム」は複合グラフG_ℰ=(N',E_ℰ,F',o')として定義され、エッジ集合ℰは異なるエージェント間の接続を表すと述べている。

## 2段階最適化: エッジ最適化とノード最適化

著者らによれば、最適化は2段階からなる。エッジ最適化では、各潜在エッジe_iに実数パラメータθ_i∈[0,1]を割り当て、確率θ_iでエッジを含めるサンプリングを行い、REINFORCEアルゴリズム(∇_θ E[u_τ(G_ℰ)]≈(1/M)Σ û_τ(G_i)∇_θ log p_θ(G_i))で勾配推定しAdamで更新すると説明している。著者らは、エッジ最適化にREINFORCEベースの確率的グラフサンプリングを用いることで、離散的なエッジ選択の組合せ的複雑性を回避できると述べている。ノード最適化では、各ノードの入出力ペアを履歴h_nに蓄積し、OPRO等の既存プロンプト最適化手法でプロンプトp_nを反復改善するとしている。

## 評価結果: Mini Crosswords・HumanEval・GAIA

著者らは、Mini Crosswords(5×5、20問)でGPT-4-Turbo使用時に最適化後0.800(±0.0616)を達成し、先行技術のTree of Thought(GPT-4-Turbo、0.668)を上回ったと報告している。HumanEval(164問)ではノード最適化なしの0.76からオンライン学習で0.88(±0.007)まで改善したとしている。

GAIAベンチマークでは、GPT-4-Turbo単体の平均9.70%、AutoGPTの4.85%に対し、GPTSwarm(7×Tree of Thought構成)は平均18.45%(Level1: 30.56±3.25%、Level2: 20.93±1.27%)を記録したと著者らは述べている。著者らは、GAIAベンチマークにおいてGPTSwarm(7×Tree of Thought構成)がGPT-4-Turbo単体(平均9.70%)やAutoGPT(平均4.85%)を大きく上回る平均18.45%を達成したと報告し、Level2では260.2%の相対改善を示したとしている。Mini CrosswordsやHumanEvalでも同様の改善を確認したとしている。

## 実装範囲

著者らによれば、実装は41種類のファイル解析・ウェブ検索・インデックスベースメモリのモジュールに対応するとしている。

# 活用先

（コンセプト昇華時に追記）

---
type: Article
title: Where LLM Agents Fail and How They can Learn From Failures
description: arXiv論文。LLMエージェントの失敗をMemory・Reflection・Planning・Action・System-level operationsの5領域に分類するAgentErrorTaxonomyと、根本原因を特定し矯正フィードバックを与えるAgentDebugフレームワークを提案している。
site: arXiv
published: unknown
retrieved: 2026-08-16
resource: https://arxiv.org/abs/2509.25370
origin: "web:arxiv.org"
source_tier: primary
tags: [graph-engineering, agent-failure, debugging, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

本論文は、LLMエージェントが計画・メモリ・反省・ツール使用を統合する一方で、単一の根本原因エラーが後続の判断へと波及していく「カスケード失敗」に脆弱であるという課題認識から出発していると著者らは述べている。この課題に対して著者らは、失敗モードの分類体系であるAgentErrorTaxonomy、失敗軌跡のベンチマークデータセットであるAgentErrorBench、根本原因を特定し改善を支援するデバッグフレームワークであるAgentDebugという3つの貢献を提示していると説明している。著者らは、失敗の分類から軌跡データセットの構築、デバッグ支援フレームワークの実装、定量的な性能改善の実証までを一貫した枠組みとして提示している点が本研究の特徴だと位置づけている。

# 要点

## AgentErrorTaxonomy: 失敗モードを5領域に体系化

著者らは、LLMエージェントの失敗モードを体系化した分類体系としてAgentErrorTaxonomyを提案していると述べている。この分類体系は、Memory(メモリ)、Reflection(反省)、Planning(計画)、Action(行動)、System-level operations(システムレベル操作)という5つの領域から構成されており、計画・メモリ・反省・行動・システムレベルという広い範囲の失敗モードを横断的にカバーしている点が特徴だと著者らは説明している。

## AgentErrorBench: 初の大規模失敗軌跡データセット

著者らは、ALFWorld・GAIA・WebShopという3つの異なる環境での実エージェント軌跡を体系的にアノテーションしたベンチマークデータセットとしてAgentErrorBenchを構築したと報告している。著者らはこのデータセットを「実環境のエージェント軌跡から構築された初の大規模失敗軌跡データセット」と位置づけていると述べている。

## AgentDebug: 根本原因の特定と矯正フィードバック

著者らは、失敗の根本原因を特定した上で矯正フィードバックを提供することでエージェントの反復的な改善を可能にする設計としたデバッグフレームワーク、AgentDebugを提案していると説明している。

## 実験結果: 精度とタスク成功率の定量的な向上

著者らは、AgentErrorBenchを用いてAgentDebugの効果を検証した結果、全正解精度(all-correct accuracy)で24%の向上、ステップレベル精度(step-level accuracy)で17%の向上を達成したと報告している。さらに、ALFWorld・GAIA・WebShopの3ベンチマーク全体では、タスク成功率が最大26%の相対改善を示したとも述べている。

> 引用: 「原理的なデバッグがより信頼性があり適応的なLLMエージェントへの道筋を確立する。」

著者らはこの結果を踏まえ、根本原因に基づく原理的なデバッグがより信頼性が高く適応的なLLMエージェントの実現につながると位置づけていると説明している。このように本研究は、失敗の分類(AgentErrorTaxonomy)から軌跡データセットの構築(AgentErrorBench)、デバッグ支援フレームワークの実装(AgentDebug)、そして定量的な性能改善の実証までを一貫した枠組みとして提示している点に特徴があると著者らは説明している。

# 活用先

- [../graph-engineering/failure-taxonomy-and-debugging.md](../graph-engineering/failure-taxonomy-and-debugging.md) — カスケード失敗（単一の根本原因エラーが後続の判断へ波及する）という課題設定、AgentErrorTaxonomyの5領域（Memory / Reflection / Planning / Action / System-level operations）、AgentErrorBenchの構築環境（ALFWorld・GAIA・WebShop）、AgentDebugによる全正解精度24%・ステップレベル精度17%の向上と最大26%の相対改善という定量結果の主根拠

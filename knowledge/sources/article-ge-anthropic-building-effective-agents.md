---
type: Article
title: Building Effective AI Agents
description: Anthropic公式。WorkflowとAgentを定義で区別し、5つのワークフローパターンと、検索・ツール・メモリで拡張されたLLM(augmented LLM)を基本構築ブロックとするAgent構築の指針を解説する
site: Anthropic
published: unknown
retrieved: 2026-08-16
resource: https://www.anthropic.com/engineering/building-effective-agents
origin: "web:anthropic.com"
source_tier: secondary
tags: [graph-engineering, agents, workflows, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

Anthropic公式が公開する「Building Effective AI Agents」は、見出し構成として「導入」→「Agents と Workflows とは何か」→「いつ、どのようにAgentsを使うべきか」→「Workflowsの構築ブロックとパターン」→「Agentsの構築」→「まとめ」という流れをとる記事である。冒頭でAnthropicは、自社が観察した中で「最も成功した実装は複雑なフレームワークを使っていたのではなく、シンプルで組み合わせ可能なパターンで構築されていた」と述べ、この観察を記事全体の基調としている。同記事はWorkflowとAgentという2つの用語を明確に定義したうえで、前者を5つの構築パターンとして分解し、後者を「基本構築ブロックであるLLM」から積み上げる形で解説している。

# 要点

## WorkflowとAgentの定義と使い分け

同記事はWorkflowを「LLMsとツールが予め定義されたコードパスを通じてオーケストレーションされるシステム」、Agentを「LLMsが動的に自身のプロセスとツール使用を指示し、タスク達成方法をコントロールし続けるシステム」と定義している。

> 引用: 「Workflows are systems where LLMs and tools are orchestrated through predefined code paths, while agents are systems where LLMs dynamically direct their own processes and tool usage.」

使い分けの指針としては、「より複雑さが正当化される場合、workflowsは予測可能性と一貫性を提供する一方、agentsはより柔軟性とモデル主導の意思決定が大規模に必要な場合のより良い選択肢」だと説明している。

## 基本構成要素としてのaugmented LLM

同記事は、「エージェント的システムの基本的な構築ブロックは、検索・ツール・メモリなどの拡張機能で強化されたLLM」だと述べ、この augmented LLM を土台としてWorkflowとAgentの両方が組み立てられると位置づけている。

## 5つのワークフローパターン

同記事はWorkflowの構築パターンを5種類紹介している。(1) Prompt chainingはタスクを固定的な順序のサブタスクに分解し各LLM呼び出しが前段の出力を処理する方式で、マーケティングコピー生成後に別言語へ翻訳する例や、文書のアウトライン作成→基準確認→本文執筆という多段プロンプトの例が挙げられている。(2) Routingは入力を分類し特化した後続タスクに振り分ける方式で、顧客問い合わせを一般質問・払い戻し・技術サポートに分類する例や、簡単な質問はClaude Haikuに難しい質問はClaude Sonnetにルーティングしてコストと速度を最適化する例が示されている。(3) ParallelizationにはSectioning(独立サブタスクの並行実行)とVoting(同一タスクを複数回実行し多様な出力を得る)の2形態があり、コードの脆弱性レビューで複数プロンプトが並行して検証する例、コンテンツの適切性を複数インスタンスで投票判定する例が挙がっている。(4) Orchestrator-workersは中央のLLMが動的にタスクを分解し複数のワーカーLLMに委譲、結果を統合する方式で、必要なサブタスクが事前に予測できない複雑なタスクに適するとし、複数ファイルにまたがるコーディング変更を伴うタスクを例に挙げている。(5) Evaluator-optimizerは一方のLLMが応答を生成し、もう一方が評価とフィードバックを提供するループで、評価基準が明確で反復的な改善が測定可能な価値を生む場合に有効だとし、文学翻訳でのニュアンス改善を例に挙げている。

## Agent構築とシンプルさの原則

Agent構築の章では「Agentsは典型的には、環境からのフィードバックに基づきループでツールを使うだけのLLM」だと説明され、実行中の各ステップで環境から「grounded truth」を得ることが重要だとしている。実装上の推奨としては、「find the simplest solution possible, and only increase complexity when needed」というシンプルさの原則を掲げ、フレームワークは開発初速には有効だが本番段階では抽象化層を減らし基礎コンポーネントで組み直すことを躊躇しないよう述べている。あわせて、ツール設計(Agent-Computer Interface)にプロンプト全体と同程度の労力を割くべきだという指摘もしている。

# 活用先

（コンセプト昇華時に追記）

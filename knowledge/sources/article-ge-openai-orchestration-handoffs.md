---
type: Article
title: Orchestration and handoffs
description: OpenAI公式。会話の所有権を引き渡すHandoffsと、マネージャーが所有権を保持したまま専門エージェントをツール化するAgents as Toolsを対比し、専門家追加の判断基準と「まず単一エージェントから始める」原則を解説する
site: OpenAI
published: unknown
retrieved: 2026-08-16
resource: https://developers.openai.com/api/docs/guides/agents/orchestration
origin: "web:openai.com"
source_tier: secondary
tags: [graph-engineering, agents, orchestration, multi-agent, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

OpenAI公式が公開する「Orchestration and handoffs」は、見出し構成として「Orchestration and handoffsの概要」→「Handoffsパターン」→「Agents as Tools(Managerパターン)」→「パターンの使い分け」→「実装例」→「設計原則」という流れをとる記事である。冒頭で「マルチエージェントワークフローは、専門家(specialist)が仕事の異なる部分を所有すべき場合に有用」だと述べ、各分岐点で「最終的なユーザー向け回答の所有権を誰が持つか」を決める設計判断こそがOrchestrationの本質だとしている。同記事はこの所有権の所在という軸から、HandoffsとAgents as Toolsという2つのパターンを対比的に解説している。

# 要点

## Handoffsパターン: 所有権そのものを引き渡す

Handoffsパターンでは、トリアージ役のエージェントが特化したエージェントへ会話の所有権そのものを引き渡す。実装例として`Agent.create({ name: "Triage agent", handoffs: [billingAgent, handoff(refundAgent)] })`のようなコードが示され、「専門家が次の応答を所有すべき場合にHandoffsが最も明確に適合する」と説明されている。

## Agents as Tools(Managerパターン): 所有権はマネージャーに残る

対照的にAgents as Tools(Managerパターン)は、中央のマネージャーエージェントが会話の制御を保持したまま、専門化されたエージェントをツールとして呼び出し、その結果を統合して最終回答を自ら合成する方式である。実装例として`main_agent = Agent(name: "Research assistant", tools: [summarizer.as_tool(tool_name: "summarize_text")])`のようにサブエージェントを`.as_tool()`でラップする形が示されており、この方式は「マネージャーが最終回答を合成すべき場合に通常より適したフィット」だとされている。両パターンの比較として、Handoffsは制御フローがスペシャリストへ移り応答の所有権もスペシャリストに移る一方、Agents as Toolsは制御・所有権とも常にマネージャーに残る点が対比されている。

## 専門家を追加すべき判断基準

使い分けの判断基準として、「専門家を追加するのは、それがcapability isolation(能力の分離)、policy isolation(ポリシーの分離)、prompt clarity(プロンプトの明確さ)、trace legibility(トレースの可読性)のいずれかを実質的に改善する場合に限る」という原則が明記されている。

> 引用: 「Add specialists only when they materially improve capability isolation, policy isolation, prompt clarity, or trace legibility.」

追加の指針として、各スペシャリストは狭い職務スコープを持つべきこと、`handoff_description`は簡潔かつ具体的に書くべきこと、次の分岐が本当に異なる指示・ツール・ポリシーを必要とする場合にのみエージェントを分割すべきことが挙げられている。また実装面では、JavaScript/TypeScript向けAPIとして`handoff()`関数を用いて追加設定(input検証やonHandoffコールバック等)を付与でき、Agents as ToolsのPython版APIでは`.as_tool(tool_name, tool_description)`でツール名と説明を明示的に指定する点も示されている。

## 結論: まず単一エージェントから始める

設計全体の指針として「可能な限り、まずは単一エージェントから始める(Start with one agent whenever you can)」という原則が結論として示され、マルチエージェント構成は複雑さに見合う効果が実証されてから導入すべきという立場が一貫している。

# 活用先

- [../graph-engineering/multi-agent-break-even.md](../graph-engineering/multi-agent-break-even.md) — 専門家を追加してよい4条件（capability isolation / policy isolation / prompt clarity / trace legibility）の引用と、「Start with one agent whenever you can」という結論、次の分岐が本当に異なる指示・ツール・ポリシーを必要とする場合にのみ分割すべきという指針の根拠
- [../graph-engineering/handoffs-and-ownership.md](../graph-engineering/handoffs-and-ownership.md) — 「最終的なユーザー向け回答の所有権を誰が持つか」がオーケストレーションの本質だという位置づけ、Handoffsパターンと Agents as Tools（Managerパターン）の定義・実装例・制御フローと所有権の対比、狭い職務スコープ・`handoff_description`の書き方という追加指針の主根拠

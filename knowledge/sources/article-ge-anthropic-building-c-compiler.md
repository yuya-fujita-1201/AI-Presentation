---
type: Article
title: Building a C compiler with a team of parallel Claudes
description: Anthropic公式。16個のClaudeエージェントを並列稼働させRust製Cコンパイラを開発した実験の記録。タスクロックによる競合回避の運用設計と、「task verifierがほぼ完璧である必要がある」という教訓を解説する
site: Anthropic
published: unknown
retrieved: 2026-08-16
resource: https://www.anthropic.com/engineering/building-c-compiler
origin: "web:anthropic.com"
source_tier: secondary
tags: [graph-engineering, multi-agent, parallel-agents, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-16T00:00:00+09:00"
---

# 概要

Anthropic公式が公開する「Building a C compiler with a team of parallel Claudes」は、16個のClaudeエージェントを並列稼働させてRust言語でC言語コンパイラを一から開発し、Linuxカーネルのコンパイルを目指した実験の記録である。同記事は、モデルとエージェント構成、タスク分割と競合回避の運用設計、開発中に得た教訓、そして完成したコンパイラの性能という4つの観点から、多数のコーディングエージェントを長時間・大規模に並列稼働させる際に何が効き何が課題になるかを説明している。

# 要点

## 実験概要とモデル・エージェント構成

Anthropicは、16個のClaudeインスタンスを用いて約2週間、「nearly 2,000 Claude Code sessions」にわたって並列開発を行ったと報告している。使用モデルは「Opus 4.6 using agent teams」であり、各エージェントはDockerコンテナ内で独立して動作し、Gitリポジトリを共有インフラとして利用したとしている。役割は専門化されており、「one agent with coalescing duplicate code」(重複コードの統合担当)、「another in charge of improving performance」(性能改善担当)、「another responsible for outputting efficient compiled code」(効率的なコード出力担当)などに分かれていたと説明している。

## トークン消費とコスト

同記事は実測値として、入力トークンが「2 billion input tokens」(20億トークン)、出力トークンが「140 million output tokens」(1億4000万トークン)、総コストが「just under $20,000」(2万ドル弱)、セッション数が「nearly 2,000 Claude Code sessions」だったと報告している。

> 引用: 「Over nearly 2,000 Claude Code sessions across two weeks, the agents consumed 2 billion input tokens and generated 140 million output tokens, for a total cost just under $20,000.」

## マルチエージェント運用設計

タスク分割の仕組みとして、各エージェントは「current_tasks/」ディレクトリ内のテキストファイルでロックを取得してタスクを担当したと説明している。競合回避については「If two agents try to claim the same task, git's synchronization forces the second agent to pick a different one」という形で、Gitの同期機構自体を競合解決に利用したとしている。同期の流れは「pull from upstream, merges changes from other agents, pushes changes, and removes the lock」という手順を踏むとしている。Linuxカーネル対応にあたっては、GCCを「online known-good compiler oracle」(既知良好なコンパイラの参照実装)として使い、異なるファイルを異なるエージェントが並行して修正できるよう設計したと述べている。

## 課題と教訓

Anthropicは、最大の学習として「Claude will work autonomously to solve whatever problem I give it. So it's important that the task verifier is nearly perfect」を挙げ、検証機構(タスクベリファイア)がほぼ完璧である必要性を強調している。

> 引用: 「Claude will work autonomously to solve whatever problem I give it, so it's important that the task verifier is nearly perfect.」

文脈管理については「The test harness should not print thousands of useless bytes」として、テストハーネスが無駄に大量の出力をしないよう注意が必要だとしている。また「Claude can't tell time and, left alone, will happily spend hours running tests instead of making progress」という時間感覚の欠如も課題として挙げており、放置すると進捗のないままテスト実行に何時間も費やしてしまう傾向が観察されたとしている。並列化の限界として、単一タスクに固定すると全エージェントが同じバグで停止してしまう問題も見られたと述べている。

## 成果物の性能

完成したコンパイラは「100,000-line compiler」(10万行規模)で、「build Linux 6.9 on x86, ARM, and RISC-V」という複数アーキテクチャでのLinux 6.9ビルドに対応したと報告している。テスト成功率は「99% pass rate on most compiler test suites including the GCC torture test suite」に達し、コンパイル対象として「QEMU, FFmpeg, SQlite, postgres, redis」が挙げられているとしている。一方で制限事項として、16ビットx86コード生成ができずGCCに依存する点、アセンブラとリンカが「somewhat buggy」(やや不安定)である点、最適化を全て無効にした場合でも「less efficient code than GCC」しか生成できない点を挙げている。

# 活用先

- [../graph-engineering/multi-agent-break-even.md](../graph-engineering/multi-agent-break-even.md) — 16エージェント・約2週間・約2,000セッション・入力20億トークン・出力1億4000万トークン・総コスト2万ドル弱という実測値と、成果物の規模（10万行）・テスト合格率（99%）を、マルチエージェント化の実額コストの根拠として使用
- [../graph-engineering/handoffs-and-ownership.md](../graph-engineering/handoffs-and-ownership.md) — `current_tasks/`のテキストファイルによるタスクロック、Gitの同期機構を競合解決に利用する設計、pull→マージ→push→ロック削除という同期手順を、「回答の所有権」とは別種の「作業対象の所有権」の実装例として使用
- [../graph-engineering/verification-gates-and-evidence.md](../graph-engineering/verification-gates-and-evidence.md) — 「task verifierがほぼ完璧である必要がある」という教訓の引用、GCCを既知良好なコンパイラの参照実装（oracle）として使った設計、テストハーネスが大量出力しないよう注意すべき点、Claudeに時間感覚がなく放置するとテスト実行に何時間も費やす傾向の根拠

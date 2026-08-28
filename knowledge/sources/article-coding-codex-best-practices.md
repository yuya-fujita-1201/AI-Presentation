---
type: Article
title: Best practices for Codex
description: OpenAI公式ガイド。プロンプトの4要素構造化、AGENTS.mdによる恒久ルールの外部化、権限の保守的運用、MCP/Skills/スケジュールタスクの活用と、よくある誤り8種を解説
site: OpenAI
published: unknown
retrieved: 2026-08-28
resource: https://learn.chatgpt.com/guides/best-practices
origin: "web:chatgpt.com"
source_tier: secondary
tags: [ai-coding, codex, agents-md, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-28T00:00:00+09:00"
---

# 概要

OpenAIが公式に公開する「Best practices for Codex」は、developers.openai.com/codex/learn/best-practices から308リダイレクトされる learn.chatgpt.com 上のガイドで、新規ユーザー向けに10章構成で実務習慣を解説していると紹介している。同ガイドは、プロンプトの構造化から計画立て、AGENTS.mdによる恒久ルールの外部化、権限設定、レビュー・MCP・Skills・スケジュールタスクの活用、そしてよくある8つの誤りまでを一貫して扱っていると説明している。

# 要点

## プロンプトの4要素と推論レベルの使い分け

同ガイドは、タスクを「Goal」「Context」「Constraints」「Done when」の4要素で構造化することを推奨していると説明している。

> 引用: 「Clear prompting isn't required to get value, but it does make results more reliable」

そのうえで、Reasoning levelをLow（高速・範囲が明確なタスク向け）、Medium・High（複雑な変更やデバッグ向け）、Extra High（長期間・高い推論量を要するタスク向け）の3段階で使い分けるよう案内しているとしている。

## 計画フェーズとPlan mode

`/plan`コマンドまたは`Shift+Tab`でPlan modeを切り替えられるとし、次のように述べている。

> 引用: 「Plan mode lets Codex gather context, ask clarifying questions, and build a stronger plan before implementation」

長期・多段階の作業には`PLANS.md`テンプレートの利用も提案されているという。

## AGENTS.mdによる恒久ルールの外部化

同ガイドは、AGENTS.mdの位置づけを次のように説明している。

> 引用: 「Think of AGENTS.md as an open-format README for agents. It loads into context automatically.」

リポジトリのレイアウト、ビルド・テスト・lintコマンド、エンジニアリング規約、禁止事項（do-not rules）、完了条件を記載すべきだとし、階層は個人用の`~/.codex/AGENTS.md`、リポジトリ共有の`.codex/AGENTS.md`、サブディレクトリ別の3層に分かれると述べている。運用ルールとしては次の考え方が特徴的だとしている。

> 引用: 「When Codex makes the same mistake twice, ask it for a retrospective and update AGENTS.md」

## 設定の3層管理と保守的な権限運用

`config.toml`も個人用`~/.codex/config.toml`、リポジトリ用`.codex/config.toml`、プロファイル別`$CODEX_HOME/profile-name.config.toml`の3層で管理するとし、ChatGPTデスクトップアプリでは「Settings > Configuration > Open config.toml」から編集できると説明している。権限運用については次のように述べている。

> 引用: 「Start with the default permissions. Keep approval and sandboxing tight by default, then loosen permissions only for trusted repos」

承認とサンドボックスを保守的な設定から始め、信頼できるリポジトリに限って緩めていく運用を推奨しているとしている。

## レビュー・MCP・Skills・スケジュールタスクの活用

`/review`スラッシュコマンドでPRスタイルのレビュー、未コミット変更のレビュー、コミット単位のレビューが可能だとし、自社での運用実績として次の記述を紹介している。

> 引用: 「At OpenAI, Codex reviews 100% of PRs」

MCPは`codex mcp add`で追加できるとしつつ、次のように釘を刺している。

> 引用: 「Add tools only when they unlock a real workflow」

Skillについては、リポジトリ内`.agents/skills`（チーム共有）または`$HOME/.agents/skills`（個人用）に`SKILL.md`として配置するとし、設計原則として次を挙げている。

> 引用: 「Keep each skill scoped to one job」「Start with 2 to 3 concrete use cases」

スケジュールタスクはChatGPTデスクトップのScheduledページでプロジェクト・プロンプト・頻度・実行環境（Git worktreeまたはローカル）を設定するものだとし、両者の関係を次のようにまとめている。

> 引用: 「Skills define the method and scheduled tasks define the schedule」

## よくある誤り8種

同ガイドは、初心者が陥りやすい誤りとして、恒久ルールをAGENTS.mdに移さずプロンプトに詰め込むこと、ビルド・テストコマンドの実行方法を伝えないこと、複雑なタスクで計画を省略すること、ワークフローを理解する前にフルアクセス権限を付与すること、Git worktreeを使わず同一ファイルで並行作業させること、手動運用が安定する前に自動化してしまうこと、逐一監視しようとすること、プロジェクト全体を1つのチャットで扱うことの8点を挙げている。

# 活用先

（コンセプト昇華時に追記）

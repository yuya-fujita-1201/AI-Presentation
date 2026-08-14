---
type: Article
title: Agent SDK overview - Claude Code Docs
description: Anthropic公式のClaude Code Docs。Agent SDKの定義とCLI/Client SDK/Managed Agentsとの使い分け、組み込みツールやHooks・Subagents・MCP等の提供機能、Quickstart等の次のステップを解説している
site: Anthropic
published: unknown
retrieved: 2026-08-14
resource: https://code.claude.com/docs/en/agent-sdk/overview
origin: "web:claude.com"
source_tier: primary
tags: [harness-engineering, agent-sdk, claude-code, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-14T00:00:00+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは、Agent SDKの入門文書として「Agent SDK overview」を公開している。同文書は、エージェントとは、ファイルを読み取り・コマンドを実行し・コードを編集するツールを呼び出しながら自ら手順を計画してタスクを完了させるアプリケーションであると定義している。そのうえで、Agent SDKはClaude Codeを支えているのと同じツール群・エージェントループ・コンテキスト管理を、PythonとTypeScriptでプログラム可能な形で提供するライブラリであると説明している。

# 要点

## Agent SDKと他のClaudeツールとの使い分け

同文書は、Agent SDK・Claude Code CLI・Client SDK・Managed Agentsという4つの選択肢を、用途に応じた比較表で整理している。ツールループを自前実装せずにエージェントを構築したい場合はAgent SDKを使うべきだとし、これは自分自身のプロセス内でエージェントループを実行するPython/TypeScriptのライブラリであると説明している。対話的な開発やターミナルからの一度限りのタスク実行にはClaude Code CLIが適しており、日常の対話利用のために作られたターミナルインターフェースだとしている。自分でツールループを実装しながらAPIを直接呼び出したい場合はClient SDKを使うべきで、これはClaude CodeではなくAnthropic APIへの直接アクセスを提供するものだとしている。自前のサンドボックスやセッションインフラを管理せずに長時間・非同期のエージェントを動かしたい場合はManaged Agentsが対象で、AnthropicがエージェントとサンドボックスをホストするREST APIであり、Agent SDKとは別製品であると明記されている。

同文書はさらに、SDKがPythonとTypeScriptのライブラリとしてのみ提供されていると述べている。別の言語から同じエージェントループを動かしたい場合は、`-p`フラグと`--output-format json`を指定してCLIをサブプロセスとして実行する方法を案内している。

## Agent SDKの提供機能

同文書は、Claude Codeを強力にしている要素はすべてSDKでも利用できると述べ、機能を表形式で列挙している。ファイルの読み取り・書き込み・編集、コマンド実行、Web検索を行う「Built-in tools（組み込みツール）」、エージェントのライフサイクルの重要な地点でカスタムコードを実行する「Hooks」、焦点を絞ったサブタスクのために専門特化したエージェントを派生させる「Subagents」、Model Context Protocol（MCP）経由で外部のツールやデータソースを接続する「MCP」、どのツールが自動実行されどのツールが承認を必要とするかを制御する「Permissions」、複数回のやり取りにわたってコンテキストを維持し、後から再開したり分岐させたりできる「Sessions」が挙げられている。加えて、プロジェクトの`.claude/`とホームディレクトリの`~/.claude/`から自動的に読み込まれる「Skills, commands, and memory」はClaude Codeと同様の挙動であるとし、skills・agents・hooks・MCPサーバーをパッケージ化してローカルパスから読み込める「Plugins」も提供されているとしている。

## サードパーティ開発者への注意事項

同文書には、サードパーティ開発者への注記が含まれている。事前に承認を得ていない限り、Anthropicはサードパーティ開発者がclaude.aiのログインやレート制限を自社製品（Agent SDKで構築したエージェントを含む）に提供することを許可していないと明記されており、代わりにQuickstartで説明されているAPIキー認証方式を使うよう案内している。

## 次のステップとして案内されているリソース

同文書は、Agent SDKで構築を始めるための次のステップとして複数のリソースへのリンクを示している。既存コードのバグを見つけて修正する最初のエージェントを構築するQuickstart、Claudeがどのように計画を立ててツールを呼び出しタスク完了を判断するかを説明するAgent loop、ローカル開発向けのデモアプリ集であるExample agents、TypeScript SDKとPython SDKの完全なAPIリファレンスに加え、Claude Codeチームがダイナミックワークフローを使ってサブエージェントを大規模にオーケストレーションする手法を解説した「Agent harness design」というブログ記事が案内されている。

> 引用: 「An agent is an application that completes a task by planning its own steps and calling tools that read files, run commands, or edit code.」

# 活用先

- [../harness-engineering/what-is-harness-engineering.md](../harness-engineering/what-is-harness-engineering.md) — ハーネスの実装例としての機能群（組み込みツール・Hooks・Subagents・MCP・Permissions・Sessions・Skills/memory・Plugins）の根拠
- [../harness-engineering/harness-responsibilities-and-ladder.md](../harness-engineering/harness-responsibilities-and-ladder.md) — Agent SDKの位置づけ（Claude Codeと同じツール群・エージェントループ・コンテキスト管理の提供）と提供機能一覧を、11責務との対応表の材料として使用
- [../harness-engineering/tools-and-mcp.md](../harness-engineering/tools-and-mcp.md) — エージェントの定義（自ら手順を計画しファイル読み取り・コマンド実行・コード編集のツールを呼ぶ）、組み込みツールの内訳、MCPによる外部ツール・データソース接続という位置づけの根拠

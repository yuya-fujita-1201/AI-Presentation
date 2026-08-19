---
type: Article
title: Introduction to prompting
description: Google Cloud公式。プロンプトを自然言語の依頼として定義し、質問・指示・コンテキスト情報・few-shot例・補完対象を構成要素として整理する。
site: Google Cloud Documentation
published: unknown
retrieved: 2026-08-15
resource: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/introduction-prompt-design
origin: "web:docs.cloud.google.com"
source_tier: primary
tags: [prompt-engineering, context, few-shot, official-documentation]
generated:
  by: codex/gpt-5
  at: "2026-08-15T00:21:14+09:00"
---

# 概要

Google Cloudのプロンプト設計入門。プロンプトを言語モデルへ送る自然言語の依頼として説明し、質問、指示、コンテキスト情報、few-shot例、モデルに補完・継続させる部分を含みうるとしている。

# 要点

- 広い意味のプロンプトには、タスクだけでなくコンテキスト情報やfew-shot例も含まれる
- コンテキスト情報は、モデルが回答を生成するときに利用・参照する情報として説明される
- プロンプトエンジニアリングは、プロンプトを反復的に更新し、モデルの応答を評価する工程として説明される
- 単純な作業では追加のプロンプト設計が不要な場合もあり、複雑な作業ほど重要になるという限定がある

# 活用先

- [../../decks/01-prompt-engineering/deck.json](../../decks/01-prompt-engineering/deck.json) — 「プロンプト」と「コンテキスト」の広義・講義上の呼び分け、反復して直す説明の根拠

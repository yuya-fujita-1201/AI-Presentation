---
type: Article
title: Extend Claude with skills - Claude Code Docs
description: Claude Code Skillsの発見、関連判定、呼出時の本文ロード、allowed-tools／disallowed-toolsなど、内容と呼出機構のライフサイクルを示す公式文書
site: Anthropic
published: unknown
retrieved: 2026-08-15
resource: https://code.claude.com/docs/en/skills
origin: "web:code.claude.com"
source_tier: primary
tags: [harness-engineering, context-engineering, claude-code, skills]
generated:
  by: codex/gpt-5.6
  at: "2026-08-15T02:51:12+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは、Skillsを再利用可能な手順・知識・ツール制約のパッケージとして説明する。Skillのdescriptionは発見と関連判定に使われ、本文は関連すると判断された場合や明示的に呼び出された場合に読み込まれる。

# 要点

- descriptionと、呼出後にモデルが読む本文はコンテキスト
- Skillの発見、関連判定、呼出、`allowed-tools`／`disallowed-tools`による道具の制御はハーネス側の機構
- `allowed-tools`があっても、権限のask／deny規則が優先される場合があるため、Skillの許可を単独の安全境界として扱わない
- 常時コンテキストへ全手順を詰めず、必要なときに本文を読むライフサイクルが段階的開示を支える

# 活用先

- [../harness-engineering/project-memory-and-rules.md](../harness-engineering/project-memory-and-rules.md) — Skill本文と発見・発火・ツール制約を分ける一次根拠

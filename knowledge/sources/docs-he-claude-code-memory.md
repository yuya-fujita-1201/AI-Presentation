---
type: Article
title: How Claude remembers your project - Claude Code Docs
description: Claude CodeにおけるCLAUDE.md・auto memory・Rulesの読込方法、AGENTS.mdとの互換方法、文章による案内とsettings／Hooksによる強制の境界を示す公式文書
site: Anthropic
published: unknown
retrieved: 2026-08-15
resource: https://code.claude.com/docs/en/memory
origin: "web:code.claude.com"
source_tier: primary
tags: [harness-engineering, context-engineering, claude-code, memory, rules]
generated:
  by: codex/gpt-5.6
  at: "2026-08-15T02:51:12+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは、`CLAUDE.md`とauto memoryを、Claudeが参照するコンテキストとして説明する。これらは設定ファイルそのものではなく、書かれた内容に従うかはモデルの振る舞いを含む。絶対に禁止したい操作は、`settings.json`の権限や`PreToolUse` Hookなどの機械的な制御へ置く。

# 要点

## 内容と読込機構を分ける

- `CLAUDE.md`や`.claude/rules/*.md`の本文は、読み込まれたときにモデルへ渡るコンテキスト
- `CLAUDE.md`の自動発見、階層ロード、Rulesの`paths`条件による適用は、情報をいつ・どこで供給するかを決めるハーネス側の機構
- 同じ資産でも「モデルが読む内容」と「発見・読込・適用範囲」は別の設計責任を持つ

## AGENTS.mdとの関係

Claude Codeは`CLAUDE.md`を読み、`AGENTS.md`を直接の自動読込対象にはしない。既存の`AGENTS.md`を使う場合は、`CLAUDE.md`から`@AGENTS.md`でimportするか、`CLAUDE.md`へのsymlinkを用いる方法が公式に案内されている。

## 適用範囲と強制

Rulesはセッション開始時、または`paths`条件に一致したときにコンテキストへ読み込まれる。文章で「本番DBを触らない」と書くことは行動誘導であり、機械的なセキュリティ境界ではない。技術的に強制する必要がある場合はsettings、権限、Hooks等を使う。

# 活用先

- [../harness-engineering/project-memory-and-rules.md](../harness-engineering/project-memory-and-rules.md) — CLAUDE.md／Rulesの本文と読込機構の二面性、AGENTS.md互換、文章と機械強制の境界の一次根拠

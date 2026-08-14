---
type: Article
title: Automate workflows with hooks - Claude Code Docs
description: Claude Code Hooksのイベント、decision control、tool入出力の変更、additionalContext、記録専用Hookなど、Hookが担う複数の役割を示す公式文書
site: Anthropic
published: unknown
retrieved: 2026-08-15
resource: https://code.claude.com/docs/en/hooks
origin: "web:code.claude.com"
source_tier: primary
tags: [harness-engineering, context-engineering, claude-code, hooks, permissions]
generated:
  by: codex/gpt-5.6
  at: "2026-08-15T02:51:12+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは、HooksをClaude Codeのライフサイクル上のイベントで外部コードを実行する仕組みとして説明する。Hookは、記録、情報追加、許可・禁止・確認・延期の判定、tool入力や出力の変更など、イベントごとに異なる働きを持つ。

# 要点

- Hookの実行機構そのものはハーネス
- `PreToolUse`等のdecision controlは、許可・禁止・確認・保留の判断に使える
- Hookが返す`additionalContext`や書き換え後のtool outputなど、モデルへ渡された文章はコンテキストになる
- 全Hookが強制機能を持つわけではない。記録専用・情報追加専用・判定型・入出力変更型を区別する
- 権限側のdeny／askとHook側のallowには合成規則があるため、実装時は現行公式仕様を確認する

# 活用先

- [../harness-engineering/project-memory-and-rules.md](../harness-engineering/project-memory-and-rules.md) — Hook本体とadditionalContextの境界、Hookの役割差の一次根拠

---
type: Documentation
title: "Cursor Docs: Rules"
description: "Cursor公式のRulesドキュメント。ルールが適用時にモデルコンテキストの先頭へ毎回含まれる仕組みと、「500行以内に保つ」「大きなルールは複数の構成可能なルールへ分割する」というベストプラクティスを示す。"
source_id: CE-S21
site: Cursor Docs
published: unknown
retrieved: "2026-08-14"
resource: "https://cursor.com/docs/context/rules"
origin: "web:cursor.com"
source_tier: primary
tags: [context-engineering, rules-file, claude-code, cursor, best-practices]
generated:
  by: claude-code/fable-5
  at: "2026-08-14T15:10:00+09:00"
---

# 概要

Cursor公式のRules（ルールファイル）ドキュメント。LLMは補完間で記憶を保持しないため、ルールはプロンプトレベルで永続的・再利用可能なコンテキストを提供する仕組みだと位置づける。現行方式は `.cursor/rules` ディレクトリ内の `.mdc` ファイルで、適用されたルールの内容はモデルコンテキストの先頭に毎回含まれる。

# 要点

- ルールの位置づけ: 「Large language models don't retain memory between completions. Rules provide persistent, reusable context at the prompt level.」
- 読み込みの仕組み: 「When applied, rule contents are included at the start of the model context.」──適用時、ルール内容はモデルコンテキストの先頭へ含まれる。
- 分量のベストプラクティス: 「Keep rules under 500 lines」──ルールは500行以内に保つ。
- 大きなルールは、複数の構成可能な（composable）ルールへ分割することを推奨。

# 原文の根拠箇所

- Best practices 節: "Keep rules under 500 lines" / 大規模ルールの分割推奨
- 冒頭の仕組み説明: rules が model context の先頭へ含まれる旨

# 適用範囲と留保

- Cursor製品のドキュメントであり、500行という数値はCursorのルール機構に対する同社の推奨。他製品のルールファイル（CLAUDE.md 等）へは「毎回読む本文は簡潔に保ち、詳細は分割する」という設計指針として援用する。
- 取得日: 2026-08-14。仕様・推奨値は更新され得る。

# 関連

- [docs-ce-anthropic-skill-authoring.md](./docs-ce-anthropic-skill-authoring.md) — SKILL.md本文500行以内・分割推奨（CE-S22）
- [article-ce-cloco-context-engineering-claude.md](./article-ce-cloco-context-engineering-claude.md) — CLAUDE.md整備を実践の入り口とする解説（CE-S13）

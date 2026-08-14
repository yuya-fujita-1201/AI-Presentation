---
type: Documentation
title: "Skill authoring best practices"
description: "Anthropic公式のスキル作成ベストプラクティス。起動時は全スキルの名前と説明だけが読み込まれ、本文は関連時のみ読む段階的開示の仕組みと、「SKILL.md本文は500行以内・超えそうなら別ファイルへ分割」という指針を示す。"
source_id: CE-S22
site: Claude Platform Docs
published: unknown
retrieved: "2026-08-14"
resource: "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices"
origin: "web:platform.claude.com"
source_tier: primary
tags: [skills, progressive-disclosure, context-engineering, best-practices, claude]
generated:
  by: claude-code/fable-5
  at: "2026-08-14T15:10:00+09:00"
---

# 概要

Anthropic公式のSkill authoring best practices。コンテキストウィンドウを「公共財」と捉え、スキルは簡潔に書き、詳細は必要時にのみ読み込ませる段階的開示（progressive disclosure）を設計原則として示す。起動時に常時読み込まれるのは各スキルのメタデータ（name と description）のみで、SKILL.md本文は関連する作業が来たとき、追加ファイルはさらに必要になったときだけ読まれる。

# 要点

- 読み込みの仕組み: 「At startup, only the metadata (name and description) from all Skills is pre-loaded. Claude reads SKILL.md only when the Skill becomes relevant, and reads additional files only as needed.」
- 分量の指針: 「Keep SKILL.md body under 500 lines for optimal performance」「Split content into separate files when approaching this limit」──本文は500行以内、超えそうなら別ファイルへ分割。
- 「Claudeは既に賢い」を既定とし、AIが既に知っている説明は書かない。各情報に「このトークンコストに見合うか」を問う。
- 参照ファイルはSKILL.mdから1階層まで（深い入れ子は部分読みで情報が欠ける）。100行超の参照ファイルには目次を付ける。

# 原文の根拠箇所

- Core principles > Concise is key: メタデータのみ事前読み込み・本文は関連時のみ
- Progressive disclosure patterns > Practical guidance: "Keep SKILL.md body under 500 lines for optimal performance" / "Split content into separate files when approaching this limit"
- Technical notes > Token budgets: 同上の再掲

# 適用範囲と留保

- Anthropicのスキル機構に対する公式指針であり、500行はスキル本文への推奨値。ルールファイル一般への援用は「毎回・条件時に読む本文は簡潔に、詳細は分割」という設計指針としての参照。
- 取得日: 2026-08-14。仕様・推奨値は更新され得る。

# 関連

- [docs-ce-cursor-rules.md](./docs-ce-cursor-rules.md) — Cursor Rulesの500行以内推奨（CE-S21）
- [article-ce-anthropic-effective-context-engineering.md](./article-ce-anthropic-effective-context-engineering.md) — 段階的開示を含むCEの一般原則（CE-S01）

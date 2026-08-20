---
type: Article
title: Agent Skills
description: Anthropicの公式ドキュメントが、Skillsを再利用可能なfilesystemベースのリソースとして定義し、progressive disclosureによる3階層構造、Pre-built SkillsとCustom Skillsの違い、セキュリティ上の注意点を解説している
site: Anthropic (Claude Platform Docs)
published: unknown
retrieved: 2026-08-20
resource: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
origin: "web:claude.com"
source_tier: secondary
tags: [claude-skills, agent-skills, progressive-disclosure, ai-tools, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

Anthropicの公式ドキュメント「Agent Skills」は、Skillsを「reusable, filesystem-based resources that give Claude domain-specific expertise: workflows, context, and best practices」と定義し、会話単位の一時的な指示であるプロンプトとの違いを、再利用性の観点から説明している。同ドキュメントは、Skillsの利点として専門化・重複削減・能力の合成の3点を挙げ、事前構築済みのPre-built Agent SkillsとユーザーがCustom Skillsとして作成できる仕組みの両方を提示している。さらに、progressive disclosure（段階的開示）という仕組みによってコンテキストコストを抑える設計思想と、信頼できないSkillの利用に伴うセキュリティリスクについても言及している。

# 要点

## なぜSkillsを使うのか

Anthropicは、Skillsを「reusable, filesystem-based resources that give Claude domain-specific expertise: workflows, context, and best practices」と説明し、プロンプトが会話単位の一時的な指示であるのに対し、Skillsは「Skills load on demand, so you don't have to repeat the same guidance across conversations」という再利用性が違いだとしている。利点としてClaudeの専門化・重複の削減・能力の合成の3点を挙げている。

## Skillsの使い方

同ドキュメントによれば、事前構築済みのPre-built Agent SkillsはPowerPoint（pptx）・Excel（xlsx）・Word（docx）・PDF（pdf）の4種類が用意されており、claude.ai・Claude API・Claude Platform on AWS・Microsoft Foundry（Hosted on Anthropicデプロイのみ）で利用できると説明している。一方Custom SkillsはClaude Code・Claude API・claude.aiの設定のいずれからでも作成可能であり、「once a Skill is available in your environment, Claude uses it automatically when relevant to your request」という自動起動の挙動は両者に共通するとしている。

## Skillsの動作原理

Anthropicは、SkillsがClaudeの仮想マシン内のファイルシステムアクセスを基盤に、progressive disclosureを実現する仕組みだと説明し、「organized like an onboarding guide you'd create for a new team member」という比喩を用いている。3階層構造として、常時ロードされ約100トークン程度で済むLevel 1のメタデータ（name/description。「until a Skill is triggered, only its name and description occupy context」）、トリガー時にロードされ目安5,000トークン未満とされるLevel 2のSKILL.md本文、必要時のみロードされ未アクセス時のコストがゼロとなるLevel 3以降の参照ファイル・スクリプトを挙げている。特にスクリプトについては、bash実行されその出力のみがコンテキストに入り「the script code itself never enters context」と説明し、この設計により「no practical limit on bundled content」（未使用ファイルのコンテキストコストはゼロ）が成立するとしている。読み込みの実例として、pdf-processingスキルが (1) 起動時にname/descriptionがシステムプロンプトに入り、(2) ユーザー要求に一致すると `bash: cat pdf-processing/SKILL.md` でロードされ、(3) Claudeがフォーム入力が不要と判断すればFORMS.mdは読まれない、という流れを示している。

## Skillの構造

SKILL.mdのYAML frontmatterで必須なのはnameとdescriptionの2フィールドのみで、nameは「Maximum 64 characters」「Must contain only lowercase letters, numbers, and hyphens」であり、「anthropic」「claude」といった予約語を含んではならないとしている。descriptionは「Must be non-empty」「Maximum 1024 characters」で、「must say both what the Skill does and when to use it」という条件が課されている。

## Skillsが動く場所

Claude APIでは`container`パラメータに`skill_id`（pptx/xlsx/docx/pdf）を指定しcode execution toolが必須で、サンドボックスは「no network access and no runtime package installation」という制約を持つとしている。対照的にClaude Codeでは`~/.claude/skills/`（personal）または`.claude/skills/`（project）にディレクトリを置くだけでAPIアップロードは不要でフルネットワークアクセスがあるとしている。claude.aiではSettings > Featuresからzipでアップロードする方式（Pro/Max/Team/Enterprise、code execution有効時）で、個人単位での利用となり組織全体共有やadmin管理はできないとしたうえで、「Custom Skills do not sync across surfaces」という制約を明記している。

## セキュリティ上の注意

Anthropicは「Use Skills only from trusted sources: those you created yourself or obtained from Anthropic」と警告し、「a malicious Skill can direct Claude to invoke tools or execute code in ways that don't match the Skill's stated purpose」とリスクを説明している。外部URLを取得するSkillは特にリスクが高いとされ、Enterprise版ではSkills APIやConsole経由のアップロードを除くcustom Skillsに対して「Skill content scanning」機能があるとしている。

> 引用: 「Skills are reusable, filesystem-based resources that give Claude domain-specific expertise: workflows, context, and best practices that turn a general-purpose agent into a specialist.」

# 活用先

（コンセプト昇華時に追記）

---
type: Article
title: Equipping agents for the real world with Agent Skills
description: Anthropicのエンジニアリングブログが、2025年10月発表のAgent Skillsの開発動機とprogressive disclosureという段階的開示の設計原理、コード実行の役割、セキュリティ上の注意点を解説している
site: Anthropic (Engineering Blog)
published: unknown
retrieved: 2026-08-20
resource: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
origin: "web:anthropic.com"
source_tier: secondary
tags: [agent-skills, progressive-disclosure, ai-tools, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

Anthropicの公式エンジニアリングブログ記事で、2025年10月16日に発表されたAgent Skillsの開発動機と設計原理を解説している。記事は、モデル能力の向上によってローカルコード実行やファイルシステムと相互作用する汎用エージェントの構築が可能になった一方で「we need more composable, scalable, and portable ways to equip them with domain-specific expertise」という課題が生じたと説明し、この課題に対する解として progressive disclosure という段階的開示の設計思想に基づくSkillsを提示している。

# 要点

## 背景と課題意識

記事は開発動機について「Claude is powerful, but real work requires procedural knowledge and organizational context」と述べている。モデル自体の能力は高くても、実際の業務にはドメイン固有の手続き的知識や組織固有の文脈が必要であり、そうした専門知識を「構成可能・スケーラブル・可搬」な形でエージェントに与える手段が不足していたという課題認識が、Skills開発の出発点になっているとしている。

## 設計思想：progressive disclosure

Skillsの中核設計原理はprogressive disclosure（段階的開示）であると記事は説明する。

> 引用: 「Like a well-organized manual that starts with a table of contents, then specific chapters, and finally a detailed appendix, skills let Claude load information only as needed.」

具体的には、(1) SKILL.mdのYAMLメタデータ（name/description）がシステムプロンプトに事前ロードされ、Claudeがどのスキルを使うべきか判断する材料になる、(2) 関連性が確認されるとSKILL.md全体がコンテキストに読み込まれる、(3) 追加の参照ファイル（reference.md, forms.md等）は必要に応じてオンデマンドで読まれる、という3段階の構造を持つ。この設計により「the amount of context that can be bundled into a skill is effectively unbounded」という利点が生まれると記事は述べている。

## Skillの構成要素とコード実行の役割

Skillは、YAMLフロントマターと詳細説明を含むSKILL.mdファイル、関連ファイル群、実行可能コードの3種で構成される。記事が挙げるPDF編集スキルの例では、Claudeは既に「PDFの理解」には長けているが「manipulate them directly (e.g. to fill out a form)」という能力が不足しており、Skillsはこのギャップを埋めるものと位置づけられている。

コード実行の価値についても記事は明確に述べており、「Large language models excel at many tasks, but certain operations are better suited for traditional code execution」としたうえで、「sorting a list via token generation is far more expensive than simply running a sorting algorithm」という具体例を挙げている。また「many applications require the deterministic reliability that only code can provide」と、決定論的な信頼性が必要な処理におけるコード実行の価値も強調しており、Claudeはスクリプトをコンテキストに読み込まずに実行できるため「this workflow is consistent and repeatable」であるとしている。

## 既存アプローチとの位置づけ

記事は「Instead of building fragmented, custom-designed agents for each use case」という従来の課題を指摘し、Skillsによって「anyone can now specialize their agents with composable capabilities by capturing and sharing their procedural knowledge」という再利用可能・構成可能なコンポーネント化が実現するとしている。なお、ファインチューニングやRAGとの直接比較・ベンチマーク数値は記事内には掲載されていない。

## 開発ガイドライン

記事はSkill開発の指針として4点を挙げている。(1) 評価から始める：「Identify specific gaps in your agents' capabilities by running them on representative tasks」ことでギャップを特定する。(2) スケールを見て設計する：SKILL.mdが大きくなったら内容を分離し相互参照する。(3) Claudeの視点で考える：スキル名と説明の付け方に注意し、実際の使用パターンをモニタリングする。(4) Claudeと反復する：「ask Claude to capture its successful approaches and common mistakes into reusable context」というプロセスを回す。

## セキュリティと今後

セキュリティ面では「malicious skills may introduce vulnerabilities in the environment where they're used or direct Claude to exfiltrate data」というリスクを明示し、対策として「installing skills only from trusted sources」を推奨している。特に「code dependencies and bundled resources like images or scripts」や、外部の信頼できないネットワーク先へ接続させる指示・コードへの警戒を促している。

発表時点でClaude.ai・Claude Code・Claude Agent SDK・Claude Developer Platformが対応済みで、今後数週間でスキル作成・編集・検出・共有・使用のライフサイクル機能を追加予定としている。MCPサーバーとの補完的な活用の検討にも触れ、将来的には「enable agents to create, edit, and evaluate Skills on their own」という展望も述べている。記事は「Skills are a simple concept with a correspondingly simple format」「Building a skill for an agent is like putting together an onboarding guide for a new hire」という比喩で締めくくられている。

# 活用先

- [../agent-capabilities/overview.md](../agent-capabilities/overview.md) — 「real work requires procedural knowledge and organizational context」とコード実行の価値（ソートの例）を、能力をモデルの外側に置く理由として使用。ファインチューニング/RAGとの比較が記事内にないことも誤解の節で明示
- [../agent-capabilities/what-are-agent-skills.md](../agent-capabilities/what-are-agent-skills.md) — 開発動機（composable/scalable/portable）、PDF編集における「分かってはいるができない」ギャップ、Skillの3構成要素、コード実行の2つの価値（コストと決定論的信頼性）、onboarding guideの比喩の根拠
- [../agent-capabilities/progressive-disclosure.md](../agent-capabilities/progressive-disclosure.md) — 段階的開示のマニュアル比喩の引用と「effectively unbounded」の根拠

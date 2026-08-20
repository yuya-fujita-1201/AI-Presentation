---
type: Article
title: Skill authoring best practices
description: Anthropicの公式ドキュメントが、Skill作成における自由度設計・命名規則・description記述法・progressive disclosureのファイル分割規則・評価駆動開発の手順・アンチパターンを実務的なチェックリストとして解説している
site: Anthropic (Claude Platform Docs)
published: unknown
retrieved: 2026-08-20
resource: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
origin: "web:claude.com"
source_tier: secondary
tags: [claude-skills, skill-authoring, progressive-disclosure, ai-tools, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

Anthropicの公式ドキュメント「Skill authoring best practices」は、良いSkillを「concise, well-structured, and tested with real usage」と規定し、コンテキストウィンドウを「a public good」として捉える基本姿勢を示している。同ドキュメントは、命名規則・description記述法・progressive disclosureのファイル分割規則・評価駆動の開発手順・避けるべきアンチパターンまで、Skill作成の実務的なチェックリストを提示している。

# 要点

## 基本原則

Anthropicは、良いSkillの条件を「concise, well-structured, and tested with real usage」と説明し、コンテキストウィンドウを「a public good」として位置づけている（システムプロンプト・会話履歴・他Skillのメタデータ・実際の要求と共有されるため）。前提として「Claude is already very smart」であり、Claudeが既に知っている説明は書くべきでないとしている。具体例として、約50トークンで済む簡潔版（pdfplumberのコード例のみ）と、PDFとは何かの説明から始まる約150トークンの冗長版を対比し、簡潔版を推奨している。

## 自由度の設定

タスクの脆弱性・多様性に応じて指示の具体性を変えるべきだとし、複数の妥当なアプローチがあるHigh freedomではテキストによる一般的指示、Medium freedomでは擬似コードやパラメータ付きスクリプト、データベースマイグレーションのように操作が壊れやすく一貫性が重要なLow freedomでは「Run exactly this script」と特定のスクリプトを厳密に指定すべきだとしている。この違いを「narrow bridge with cliffs on both sides」（低自由度）と「open field with no hazards」（高自由度）という比喩で表現している。

## 全モデルでのテストと命名規則

SkillはHaiku（十分なガイダンスがあるか）・Sonnet（明確で効率的か）・Opus（過剰説明していないか）のそれぞれでテストすべきだとしている。命名についてはgerund形（processing-pdfs、analyzing-spreadsheetsのような動詞+ing形）を推奨し、helper/utils/toolsといった曖昧な名前や、anthropic-helperのような予約語を含む名前は避けるべきとしている。

## descriptionの書き方

descriptionは「Always write in third person」と明記されており、「I can help you...」のような一人称表現はdiscovery（発見）の問題を起こすため避けるべきだとしている。良い例として「Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.」を挙げ、「Helps with documents」のような曖昧な記述は不可としている。「The 'name' and 'description' in your Skill's metadata are particularly critical」と述べ、Claudeは100以上のSkillの中からdescriptionのみを手がかりに選択判断を行うとしている。

## progressive disclosureの分割規則

「Keep SKILL.md body under 500 lines for optimal performance」と具体的な行数上限を示し、この上限に近づく場合は複数ファイルに分割すべきとしている。参照ファイルはSKILL.mdから1階層のみとし（深いネストは避ける）、100行を超える参照ファイルには目次を付けるべきとしている。理由として「Claude may partially read files when they're referenced from other referenced files」、つまり`head -100`のような部分読みになりうる点を挙げている。

## ワークフローと評価駆動開発

複雑なタスクにはチェックリスト形式のワークフローを、品質が重要なタスクには「Run validator → fix errors → repeat」というフィードバックループを組み込むことを推奨している。また「Create evaluations BEFORE writing extensive documentation」と明記し、ギャップの特定→3シナリオ作成→ベースライン測定→最小限の指示作成→反復という評価駆動開発の5ステップを示している。開発手法としては、Skill設計を手伝う「Claude A」と実際にSkillを使ってタスクを行う「Claude B」に役割を分担させる手法を紹介している。

## アンチパターンとMCPツール参照

Windows形式のパス（バックスラッシュ）を避けフォワードスラッシュを常用すべきこと、pypdf/pdfplumber/PyMuPDFのように選択肢を並べすぎずデフォルト+エスケープハッチ形式にすべきことをアンチパターンとして挙げている。SkillがMCPツールを使う場合は必ず完全修飾名`ServerName:tool_name`（例：`BigQuery:bigquery_schema`）を使うべきで、サーバー名を省略すると「tool not found」エラーになりうるとしている。公開前チェックリストには、descriptionの具体性・SKILL.md本文500行未満・参照ファイルの1階層制限・Haiku/Sonnet/Opusでのテスト・評価3件以上の作成などが含まれるとしている。

> 引用: 「The 'name' and 'description' in your Skill's metadata are particularly critical. Claude uses these when determining whether to trigger the Skill in response to the current task.」

# 活用先

（コンセプト昇華時に追記）

---
type: Article
title: Documenting Architecture Decisions（Michael Nygard, 2011）
description: 「アーキテクチャ決定記録（ADR）」の原典。1決定1ファイルで「文脈・決定・結果」を短く残し、覆った決定は削除せず superseded として残す慣行を提案したブログ記事
tags: [adr, decision-record, documentation, si-practice, okf]
resource: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
source_tier: primary
generated:
  by: claude-code/fable-5.1
  at: "2026-09-02T11:30:00+09:00"
---

# Documenting Architecture Decisions（Michael Nygard, 2011）

## 要旨

- プロジェクトの重要な決定は、時間が経つと「なぜそう決めたか」が失われ、後から来た人は決定を盲目的に受け入れるか、盲目的に変えるかのどちらかになる。これを防ぐために、**決定を1件ずつ短い文書（Architecture Decision Record, ADR）として残す**ことを提案した記事
- 1件の ADR は次の節で構成する: **Title**（決定の名前）／**Context**（決定を迫った状況・制約）／**Decision**（何を決めたか。能動態で）／**Status**（proposed / accepted / deprecated / superseded）／**Consequences**（決定の結果として起きること。良いことも悪いことも）
- ADR は**プロジェクトのリポジトリの中**に、コードと一緒に置く（例: `doc/arch/adr-NNN.md`）。連番を振り、番号は再利用しない
- 決定が覆ったときは**古い ADR を削除しない**。古い方の Status を `superseded by adr-NNN` に変え、新しい ADR を追加する。こうして決定の系譜が残る
- 1件は1〜2ページに収める。長い設計書を書く代わりに、決定の連なりで設計の履歴を語る

## この勉強会での使い方

- OKF 実践編（`decks/08-okf-practice`）の「要件が覆ったときの扱い」の根拠。「現在の答えは1か所（要件ファイル）を上書きし、経緯は決定記録（`decisions/`）を追記で残す」という推奨は、ADR の「決定は削除せず superseded で残す」慣行を OKF の `status` と相対リンクに写したもの
- OKF の `status: deprecated` は ADR の `superseded` に相当する。ただし OKF v0.2 の status は draft / stable / deprecated の3値なので、`superseded` の代わりに `deprecated` と後継へのリンクで表す

## 留保

- 原典はアーキテクチャの決定を対象にしている。業務要件の決定に広げるのは本勉強会の応用であり、原典の主張ではない

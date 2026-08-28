---
type: Article
title: "Exploring the Problems, their Causes and Solutions of AI Pair Programming: A Study on GitHub and Stack Overflow"
description: GitHub CopilotをめぐるGitHub Issues・Discussions・Stack Overflow投稿を分析し、問題カテゴリ・原因・解決策を体系的に分類した研究論文
site: arXiv
published: unknown
retrieved: 2026-08-28
resource: https://arxiv.org/abs/2311.01020
origin: "web:arxiv.org"
source_tier: primary
tags: [ai-coding, github-copilot, research, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-28T00:00:00+09:00"
---

# 概要

arXivに掲載された本論文は、GitHub Copilotの利用実態を大規模なユーザー投稿の分析から明らかにした研究である。研究チームはGitHub IssuesとDiscussions、Stack Overflow投稿を対象に、Copilotに関して報告される問題の種類・原因・解決策を体系的に分類している。著者らはこの分析結果をもとに、利用者側とCopilot開発チーム側の双方に向けた提言をまとめている。

# 要点

## 調査方法：1,324件の投稿から1,355件の問題を分類

研究チームは、GitHub Copilotに関するGitHub Issues 476件、GitHub Discussions 706件、Stack Overflow投稿142件の計1,324件を収集したと説明している。対象期間はCopilot公開日である2021年6月29日以降、2023年6月18日時点までで、閉じたIssueと回答済みの投稿のみを収集対象にしたとしている。研究チームは、パイロット段階でCohen's Kappa係数0.806〜0.834というラベリングの信頼性を確認した上で分類作業を行い、最終的に1,355件の問題を分類したと報告している。

## 問題カテゴリ（RQ1）：Operation Issueが過半数を占める

研究チームは、問題カテゴリの分析（RQ1）において、機能障害・起動失敗・認証エラー・アクセス失敗・インストール問題などを含む「Operation Issue」が全体の57.5%を占め、最も多いカテゴリだったと報告している。次いでCompatibility Issueが15.6%、Feature Requestが15.0%、低品質提案・無意味な提案・バグ含有提案などを含むSuggestion Content Issueが4.4%、User Experience Issueが4.3%、Copyright and Policy Issueが3.3%と続いたとしている。Operation Issueの内訳では、機能障害が226件、認証失敗が198件、起動問題が193件と上位を占めたとしている。研究チームはこの傾向について次のように結論づけている。

> 引用: 「Operation IssueはCopilotの機能設計の不十分さと不安定性に起因する」

## 原因分析（RQ2）：Copilot内部エラーとネットワーク接続エラーが上位

研究チームは、問題の原因分析（RQ2）において、391件（全問題の28.9%）で原因を特定できたと報告している。最も頻出した原因はCopilot内部エラーで76件（19.4%）、次いでネットワーク接続エラーが53件（13.6%）、エディタ・IDE不適合が50件（12.8%）、未サポートプラットフォームが32件（8.2%）の順だったとしている。

## 解決策（RQ3）：Copilot側の修正が最多

研究チームは、解決策の分析（RQ3）において、497件（36.7%）で解決策を抽出できたと報告している。最も多かった解決策はCopilotによるバグ修正で135件（27.2%）、次いで設定・構成の変更が110件（22.1%）、適切なバージョンの使用が85件（17.1%）、再インストール・再起動が60件（12.1%）の順だったとしている。

## 著者の含意：ユーザーへの提言と開発チームへの提言

研究チームは、ユーザーへの提言として、Copilotを完全な代替ではなくインスピレーション源として活用すること、コード提案を受け入れる前にレビューすること、公式にサポートされたIDEを使用することを挙げている。研究チームはこの立場について次のように述べている。

> 引用: 「Copilotの価値は有用なスタートポイントとして機能することにある」

一方、Copilot開発チームへの提言としては、カスタマイズオプションの拡充、生成コンテンツの制御方法の充実、提案の多様性と品質の向上を挙げている。あわせて、機能要望115件のうち約45%（52件）がカスタマイズに関連する要望だった点も指摘している。

# 活用先

（コンセプト昇華時に追記）

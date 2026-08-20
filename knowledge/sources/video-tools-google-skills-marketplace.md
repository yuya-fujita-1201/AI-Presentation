---
type: Video
title: 【Anthropicの標準にGoogleが乗った】google/skillsで何が変わるのか
description: Anthropic発のAgent SkillsにGoogleが乗って公開したgoogle/skillsリポジトリを対話形式で解説し、109個のSKILL.mdの規模・progressive disclosure・Claude Codeプラグインmarketplace経由の導入・Apache-2.0ライセンス・Copybaraによる自動運用の実態を紹介する動画
channel: クロノITチャンネル
duration: "11:33"
published: 2026-08-13
retrieved: 2026-08-20
resource: https://www.youtube.com/watch?v=rVWmPYQrlGA
origin: "youtube:UClRQ_q3uE62Ixlx-8gYCsAw"
subs: auto
tags: [agent-skills, google-skills, claude-code, cli, ai-tools, video]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

GoogleがAnthropic発の仕様であるAgent Skillsに乗り、Google Cloud・Firebase・Android・Flutter・Dart等の操作手順をSKILL.md形式で公開したgoogle/skillsリポジトリを、対話形式で解説する動画である。109個のSKILL.mdファイルの規模や構成、progressive disclosureによる読み込み最適化、Claude Codeプラグインmarketplaceでの導入方法、Apache-2.0ライセンスの範囲、そしてほぼ自動化されたアカウントによって社内から継続的にエクスポートされているリポジトリの運用実態までを紹介している。

# 要点

## google/skillsの規模と構成

- 動画は、GoogleがAnthropicの提案したAgent Skillsという仕様に乗り、Google Cloud・Google Ads・Google Analytics等の操作手順をスキル集として公開したと紹介している（[00:00]）
- google/skillsだけでなくFirebase・Android・Flutter・Dartも同じ形式でスキルを出しており、Google全体としてこの標準にコミットしていると説明している
- SKILL.mdは109個あり、全部を足すと2万3千行を超えるとしている。中身の9割以上はMarkdownで、Pythonは一部のスキルに付随するスクリプト部分のみだとしている（[01:00]）
- 各スキルの厚みはばらつきが大きく、Agent Platform Inferenceが726行、Gemini Interactions APIが591行ある一方、Mobile Adsのバナー広告は30行台で終わっているとしている
- 109個のうち59個がreferencesフォルダを持ち、長いスキルは補助情報をそちらに分離して必要な部分だけを読ませる構成になっていると説明している。例としてBigQueryにはCLI・クライアントライブラリ・IAM・IaC等8個のreferencesがあるとしている（[02:00]）

## カテゴリ分けと製品横断スキル

- 109個はカテゴリ別に整理されており、AI/ML系が18個、Infrastructure系が28個、Databases系が10個あるとしている
- Infrastructure系はほとんどがGKE関連で、クラスター作成・ネットワーク・ストレージ・TPU監視まで揃っているとし、Agent Platform関連だけでも13個あると説明している
- Agent PlatformはVertex AIの後継として位置づけられており、Model Garden Deploy・RAG Engine・Tuning・Eval Flywheelが含まれるとしている
- 1つの製品の使い方ではなく、複数製品を組み合わせる手順をまとめたスキルも9個あり、例としてGKEとAlloyDBを組み合わせて社内検索用のRAGを立てる手順を挙げている（[02:00]〜[03:00]）
- Google Cloud以外にもGoogle Ads APIが12個、Google Analytics APIが2個あり、マーケティング業務にも活用できる設計だとしている。Well-Architected Frameworkの6本柱（コストと運用・パフォーマンス・信頼性・セキュリティ・サステナビリティ）もそのままスキル化されているとしている
- Firebase・Flutter・Android・Genkitはこの109個には含まれず、それぞれ別のリポジトリ（firebase/agent-skills等）で製品チーム側が管理しており、READMEの末尾から一覧を辿れると説明している（[03:00]〜[04:00]）

## progressive disclosureと発火精度を左右するdescription

- 109個のスキルを入れても重くならない理由として、progressive disclosureという仕組みを紹介している。普段読み込まれるのは各スキルのdescription部分のみで、ユーザーの入力に応じて該当スキルの本文が初めて展開されるとしている（[04:00]）
- そのため発火判定の精度はdescriptionの質で決まり、書き方が曖昧だと誤ったスキルが発火することもあるとしている
- firebase-basicsの例として、Use whenとDon't use whenが明記され、使わない場面まで書くことで誤発火を防いでいると紹介し、自作スキルを書く際もこの粒度を真似るとよいと述べている
- 本文が30行しかない薄いスキルでも発火判定はdescriptionだけで決まるため、薄いスキルほどdescriptionを削らずに書き切る必要があるとしている

## 依存関係の設計とCLI検証の仕組み

- gcloud CLI Skill for AI Agentsというスキルは、他のgcloud関連スキル全部の前提になる「安全弁」だと紹介している（[05:00]）
- LLMの事前知識は古くhallucinationしやすいため、毎回gcloud helpを叩いてleaf-levelで検証するよう強制する設計だとし、LLMの記憶に頼らずGoogle側の正解を都度引かせる仕組みだと説明している
- 109個は単純に並んでいるのではなく、こうした依存関係が内部にあり、CLIのhelpコマンドを持つツールであれば自作スキルにも同じ検証パターンを応用できるが、helpが親切でないツールでは使いにくいとしている

## 導入方法とバージョン管理

- Claude Codeで使うにはプラグインmarketplaceからの導入が楽だとし、marketplaceには16個のプラグインが登録されていると説明している（[06:00]）
- プラグインはスキルとMCPサーバーのセットになっており、中身はgoogle/skills本体ではなくgemini-cli-extensionsやGoogleCloudPlatform配下の別リポジトリを参照しているため、google/skills自体はカタログのような位置づけだとしている
- 導入はclaude plugin marketplace add google/skillsのあとclaude plugin install <名前>@google-pluginsという2ステップで、プラグインごとに選んで入れられ、後から外すこともできるとしている
- firebase-basicsのreferences配下にはsetupフォルダがあり、claude_code.md・gemini_cli.md・cursor.md・github_copilot.md・antigravity.mdといったツールごとの導入手順が用意され、ツール間の差をGoogle側が吸収していると紹介している（[07:00]）
- npx skills addでの導入は対話的に選べる一方でmainブランチの最新を追うため本番では挙動が変わる可能性があり、plugin marketplace経由はrefでバージョンがピン止めされているため、本番運用にはプラグイン経由かフォークでのバージョン管理が安全だと説明している

## ライセンスと運用実態

- ライセンスはApache-2.0であり、社内向けに削ったり書き換えたりするのは自由だとしている（[07:00]〜[08:00]）
- 一方で、直したものを本家に返す経路は細く、バグ報告と新しいスキルの提案は歓迎とされているものの、中身はGoogleの社内リポジトリから流れてくるためリポジトリの「正」はGoogle社内側にあるとしている
- リポジトリはCopybaraという仕組みで社内から自動でエクスポートされており、製品側の手順が変わると公開されているスキルも合わせて更新されるとしている
- GitHub上のコントリビューターは6人で、うちcloud-ix-copybaraという自動化アカウントが203コミットを入れており、人が集まって育てるOSSというよりGoogle社内のミラーに近いと評している。タグやリリース、Discussionsも用意されていないとしている（[08:00]〜[09:00]）
- 自作スキルとして書くべきは、命名規約やネットワーク設計の制約、IAMロールの割当ポリシーといった自社側のルールであり、SDKのバージョンアップ等で変わりうる部分はGoogle側に任せてよいという線引きを示している。例としてbigquery-basicsの前後に自社のvalidationを挟む運用を挙げている（[09:00]）

## 直近の更新傾向

- 直近3日のコミットでは、Airflowのパイプラインをエージェントに書かせるmanaged-airflow-dag-authoringやFilestore Autoscaleが新規追加されるなど、Infrastructure系とデータパイプライン系の拡充が続いているとしている（[09:00]〜[10:00]）
- Agent Platform周りも厚くなっており、agent-platform-eval-flywheelにはManaged Agents対応が追加されたとしている
- Cloud Monitoringのチャート生成スキルでは並列書き込みの衝突を避けるためUUIDベースのファイル名に変更されており、単体実行から並列実行を見据えた設計へ移っていると説明している
- 文章そのものを直すコミットもまとまって入っており、e.g.やi.e.といった略記を普通の言葉に置き換える、曖昧な言い回しを動詞に直す、リンク先ドメインを一本化するといった、エージェントが読む文章としての解釈の割れを減らす修正が続いているとしている

# 主張テーブル

| claim_id | タイムスタンプ | 主張 | 出所種別 | impact |
|---|---|---|---|---|
| c1 | [01:00] | google/skillsにはSKILL.mdが109個あり、合計で2万3千行を超える | auto字幕 | high |
| c2 | [04:00] | progressive disclosureの仕組みにより通常はスキルのdescription部分だけが読み込まれ、必要になった時に本文が展開される | auto字幕 | high |
| c3 | [06:00] | Claude Codeのプラグインmarketplaceには16個のプラグインが登録されている | auto字幕 | high |
| c4 | [08:00] | google/skillsのライセンスはApache-2.0で、社内向けに改変・削減して使うのは自由 | auto字幕 | high |

# 活用先

- [../agent-capabilities/progressive-disclosure.md](../agent-capabilities/progressive-disclosure.md) — 109個中59個がreferencesフォルダを持つ構成、BigQueryの8 references、726行と30行台という厚みのばらつきを、段階的開示が実物にどう現れるかの実例として使用（auto字幕由来のため帰属＋（聞き取り））

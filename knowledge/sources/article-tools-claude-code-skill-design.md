---
type: Article
title: Claude Code Skillの作り方｜21個運用して分かった設計と育て方
description: Zennの著者が、21個のClaude Code Skill運用経験から得た設計原則・作成方法・よくある失敗パターンと運用のコツを解説している
site: Zenn（yamato_snow）
published: unknown
retrieved: 2026-08-20
resource: https://zenn.dev/yamato_snow/articles/3cd6ed9ac340a2
origin: "web:zenn.dev/yamato_snow"
source_tier: secondary
tags: [claude-code, skills, jp-practice, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-21T00:00:00+09:00"
---

# 概要

Zennの著者yamato_snowが、Claude Code Skillの構造から配置の仕組み、自作の設計・作成方法、よくある失敗パターン、運用の実践例までを、自身の21個のSkill運用経験に基づいて解説している記事である。見出し構造は「Skillの構造→Skillの配置と読み込みの仕組み→Skillの入手方法→自作Skillの設計と作成→よくある失敗パターン→知っておくと便利な仕組み→運用環境の具体例」の順に組まれている。

# 要点

## 運用実績の内訳

著者は21個のSkillを運用しており、うち16個は自作だと述べている。内訳は執筆系6個・開発系5個・運用系5個・公式プラグイン5個だが、実際に毎週使用するのは5〜6個のみだと明かしており、保有数と常用数には差があることを示している。

## SKILL.mdの基本構造とfrontmatter

Skillファイルの基本構造はYAMLフロントマター付きのMarkdownファイル（SKILL.md）であり、最小構成はname（識別子、小文字・ハイフン・数字のみ、最大64文字）とdescriptionだとされている。descriptionについて著者は「250文字で切り詰められるため、重要なキーワードは前半に入れるのがコツ」と指摘しており、文字数上限を踏まえた記述順序の工夫を勧めている。フロントマターの主要フィールドとしては、デプロイ等副作用のあるSkillに必須とされるdisable-model-invocation、サブエージェント実行で履歴汚染を防止するcontext: fork、Globパターンで自動発動条件を限定するpathsの3つが紹介されている。

## Skillの配置優先順位

配置優先順位は「Enterprise > Personal > Project」の順で上位が優先されると説明されている。Personal（`~/.claude/skills/`）は全プロジェクトに、Project（`.claude/skills/`）はそのプロジェクトのみに適用される。

## /skill-creatorによる自作の推奨

自作にあたっては手書きではなく`/skill-creator`での生成を推奨しており、著者は「正しいフォーマットのSKILL.mdを自動生成してくれます」と述べている。`/skill-creator`にはCreate（対話形式で新規作成）・Eval（A/Bテストで品質検証）・Improve（description自動最適化）・Benchmark（Pass rate・実行時間・トークン数を計測）の4モードがあり、著者はEvalモード適用後の評価をB+レベルとし、Improveモード適用後は「6つのドキュメント作成スキルのうち5つでトリガー精度が改善」したと報告している。

## よくある失敗パターン4つ

著者はよくある失敗パターンとして4つを挙げている。1つ目は詰め込みすぎ（複数役割を1つに詰め込んでしまう問題で、対策は1 Skill = 1目的に分割すること）、2つ目はdescription曖昧（「便利なスキル」といった曖昧な記述のみで済ませてしまう問題で、対策は『何をするか』＋『いつ使うか』を具体化すること）、3つ目はテストなし（作って満足してしまう問題で、対策はEvalモードで必ず検証すること）、4つ目は放置（モデル更新後に未対応のまま放置してしまう問題で、対策は定期的にBenchmarkを実行すること）である。

## 運用の実践（引き算のメンテナンス）

運用面では月1回程度のSkill見直し、モデル更新時のBenchmark実行、不要なSkillの定期削除という「引き算のメンテナンス」を実践しているという。

## 便利な仕組み：`!<command>`構文

便利な仕組みとして、`!<command>`構文でシェルコマンド結果をSkillに動的注入できる点が紹介されている。ただし「Claude Codeがプロンプトを読む前にシェル上で実行」される点に注意を促しており、実行タイミングの理解が重要だとしている。

## 総括

著者は総括として「Skillは『自分専用のClaude Code』を育てることに近い」と述べている。

> 引用: 「Skillは『自分専用のClaude Code』を育てることに近い」

そのうえで「最初はnameとdescriptionだけのシンプルなSKILL.mdで十分。使いながら育てていくのが一番のコツ」と推奨しており、完成形を最初から目指すのではなく段階的な改善を通じてSkillを育てる姿勢を勧めている。

# 活用先

- [../agent-capabilities/what-are-agent-skills.md](../agent-capabilities/what-are-agent-skills.md) — 「最初はnameとdescriptionだけのシンプルなSKILL.mdで十分」という始め方のハードルの低さを、必須2フィールドという公式仕様と併せて提示（帰属を明示）
- [../agent-capabilities/writing-good-skills.md](../agent-capabilities/writing-good-skills.md) — description 250文字上限と重要キーワード前置き、よくある失敗4パターン（詰め込みすぎ・description曖昧・テストなし・放置）とその対策、`/skill-creator` の Eval/Improve/Benchmark と「6つのうち5つでトリガー精度が改善」、21個保有・毎週使うのは5〜6個、「引き算のメンテナンス」、「最初はnameとdescriptionだけで十分」「自分専用のClaude Codeを育てる」の根拠（いずれも著者個人の実践としてコンセプト側で帰属を明示）
- [../agent-capabilities/prompts-and-project-rules.md](../agent-capabilities/prompts-and-project-rules.md) — Skillの配置優先順位（Enterprise > Personal > Project）と Personal（`~/.claude/skills/`）＝全プロジェクト / Project（`.claude/skills/`）＝当該プロジェクトのみという適用範囲を、ルールファイルのスコープ使い分けの参照点として使用（著者の解説として帰属を明示）
- [../agent-capabilities/distribution-and-governance.md](../agent-capabilities/distribution-and-governance.md) — 21個運用中16個が自作・実際に毎週使うのは5〜6個という内訳と、月1回の見直し・モデル更新時のBenchmark・不要Skillの定期削除という「引き算のメンテナンス」を、カタログを増やしすぎない運用の根拠として使用（著者個人の実践として帰属を明示）

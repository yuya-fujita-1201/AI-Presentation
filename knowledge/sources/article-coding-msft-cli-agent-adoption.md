---
type: Article
title: "Adoption and Impact of Command-Line AI Coding Agents: A Study of Microsoft's Early 2026 Rollout of Claude Code and GitHub Copilot CLI"
description: Microsoft社内での2026年前半のClaude Code/Copilot CLI導入における採用要因と生産性影響を分析したarXiv論文。合成対照分析でマージPR数24.0%増加を報告
site: arXiv (Microsoft Research)
published: unknown
retrieved: 2026-08-28
resource: https://arxiv.org/abs/2607.01418
origin: "web:arxiv.org"
source_tier: primary
tags: [ai-coding, adoption-study, productivity, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-28T00:00:00+09:00"
---

# 概要

arXivに掲載されたMicrosoft Research発の論文「Adoption and Impact of Command-Line AI Coding Agents」は、Murphy-Hill、Butler、Savelievaら研究者が、2026年前半（1月5日〜4月29日）にMicrosoft社内数万人のエンジニアを対象として実施した、コマンドラインAIコーディングエージェント（Claude CodeとGitHub Copilot CLI）の採用・定着・生産性影響に関する分析であると説明している。採用研究はCopilot CLIのみを対象に2024年10月〜2026年4月29日（導入前13週間・導入後16週間）の期間を分析し、成果研究は両ツールを対象にエンジニア1人1日あたりのマージPR数を主要指標として扱ったとしている。

# 要点

## 採用を左右する最大の要因は「同僚の利用状況」

研究チームは、ツール採用の最も強い予測因子は社会的露出（同僚が使っているかどうか）であると報告している。同僚のうちskip-levelピア（直属ではない上位階層）の25%以上が利用している場合、初回使用のオッズが+216%になったとしている。同様に、マネージャーが使用している場合は初回試行のオッズが+82%・定着のオッズが+22%上昇し、コードレビューピアの25%以上が利用している場合は初回使用のオッズが+54%上昇したと述べている。

一方で研究チームは、IDE版Copilotの既存利用者について矛盾的な関連を指摘している。IDE版Copilotの事前利用者は新ツールの試行意欲こそ+83%と高いものの、定着率はむしろ−12〜15%低かったという。キャリアステージ別の差についても言及しており、シニアIC（IC5・IC6）では定着率が約+22%高い一方、ジュニアIC（IC2・IC3）では−13〜14%低かったとしている。

## マージPR数は24.0%増加、Copilot CLIがClaude Codeの2.2倍の効果

生産性への影響については、合成対照分析（CausalImpact）により、ツール導入後にエンジニア1人1日あたりのマージPR数が+24.0%増加したと報告している。

> 引用: 「合成対照分析により、エンジニア1人1日あたりのマージPR数は+24.0%増加した（95%CI +14.5%, +33.7%、p<0.001）」。Copilot CLIがClaude Codeの2.2倍の効果を示した。

研究チームは、この効果は4ヶ月間の観測期間を通じて減衰しなかった（2月+29.4%、3月〜4月+20.0%）としている。また、週あたりのツール使用日数との用量反応関係も示しており、週3日利用で+15.0%、週5日以上利用で+50.1%の増加が確認されたと述べている。ツール別の比較では、Claude Code単独利用者が+11.4%（95%CI +9.4%〜+13.6%）、Copilot CLI単独利用者が+24.9%（95%CI +23.0%〜+26.8%）のPR増加を示し、Copilot CLIがClaude Codeの約2.2倍の効果を示した（p<0.0001）としている。

## 著者自身が明記する限界

研究チームは、マージPR数は出力の不完全なプロキシであり、複雑性の追加といった品質面のコストは今回の分析では測定できていないと明記している。また、この結果は「Microsoft 2026年初期の単一企業」における観察結果であり、他組織への一般化には限界があるとも述べている。加えて、分析では28日間のPR完成ウィンドウを用いているため、それより長期的な効果は測定できない点も注記している。

# 活用先

（コンセプト昇華時に追記）

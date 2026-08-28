---
type: Article
title: Codex Prompting Guide (GPT-5-Codex)
description: OpenAI公式のGPT-5-Codexモデル向けプロンプティングガイド。計画ツールの使い分け、preamble（前置き発言）の作法、フロントエンド生成時のデザイン方針、冗長性コントロールを解説
site: OpenAI
published: unknown
retrieved: 2026-08-28
resource: https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide
origin: "web:openai.com"
source_tier: primary
tags: [ai-coding, codex, prompting, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-28T00:00:00+09:00"
---

# 概要

OpenAIが公式に公開する「Codex Prompting Guide (GPT-5-Codex)」は、GPT-5-Codexモデル向けのプロンプティングガイドであり、「Codex Prompting Guide／Getting Started／Prompting／Compaction／Tools／New features in GPT-5.3 Codex」という6つのセクションで構成されていると紹介している。同ガイドは、計画ツールをいつ使うべきかという判断基準から、ツール呼び出し前後の発言（preamble）の作法、フロントエンド生成時のデザイン方針、そして無駄な繰り返し編集を避けるための行動原則までを一貫して扱っていると説明している。

# 要点

## プランニングツールの運用基準

同ガイドは、全タスクのうち最も単純な下位25%程度のタスクでは計画ツールの使用を省略すべきだと述べている。

> 引用: 「Skip using the planning tool for straightforward tasks (roughly the easiest 25%).」

一方で複雑なタスクについては、段階的に計画を更新していくことを求め、各アイテムは「Done」「Blocked」「Cancelled」のいずれかで状態をマークすべきだとしている。Blockedとする場合は、1文の理由と的を絞った質問を添えることが望ましいとしている。避けるべき例としては、「Do not make single-step plans」（単一ステップだけの計画を作らないこと）を挙げるとともに、テストや大規模なリファクタリングを計画項目に含めたまま実行せずに作業を終えてしまうことも失敗例として挙げている。そのうえで、最終的にユーザーへ提示すべきものは計画そのものではなく、あくまで「動作するコード」であることが必須の到達点だと強調している。

## preamble（前置き発言）の扱い

同ガイドは、ツール呼び出しの前に「1 sentence acknowledgement, 1–2 sentence plan」という形で、依頼への了解と簡潔な計画を示すpreambleを述べることを推奨している。作業中の進捗更新についても通常は1〜2文にとどめ、重要なマイルストーンに達したときだけやや長めの記述を許容するとしている。更新の頻度には具体的な数値基準が設けられており、次のように述べている。

> 引用: 「aim every 1–3 execution steps; hard floor: at least within every 6 steps or 10 tool calls」

トーンについては「real person pairing, low-ceremony; avoid headings/status labels and log voice」（実在の人間とペア作業しているような、儀礼ばらない口調とし、見出しやステータスラベル、ログのような口調は避けること）と述べ、「Good catch」「Aha」のような不自然に繰り返される決まり文句も避けるべきだとしている。加えて、性格面のバリエーションとして、チームの士気を支えるFriendly型と、トークンあたりの実用情報量を高めることを重視するPragmatic型の2タイプが紹介されているという。

## フロントエンドタスクへの指示

フロントエンド生成に関する指示として、同ガイドは「avoid collapsing into 'AI slop' or safe, average-looking layouts」（AIが作りがちな没個性で無難なだけのレイアウトに陥ることを避けること）を求め、「Aim for interfaces that feel intentional, bold, and a bit surprising」（意図が感じられ大胆で、多少の驚きのあるインターフェースを目指すこと）と述べている。具体的な観点としてTypography（既定のフォントスタックを避け表現力のあるフォントを用いること）、Color（明確な方向性を定めCSS変数で管理すること）、Motion（ページロード時や段階的表示など意味のあるアニメーションを少数だけ使うこと）、Background（単色のフラットな背景に頼らずグラデーションや図形、微細なパターンを活用すること）の4要素を挙げている。既存のデザインシステムが存在する場合には「preserve the established patterns」（確立されたパターンを維持すること）を優先すべきだとし、完成の基準としては「Finish the website or app to completion, within the scope of what's possible」（可能な範囲内でウェブサイトやアプリを完成させ切ること）を明記している。

## 冗長性コントロール

最後に同ガイドは、「Avoid repeated micro-edits」（細かい編集を繰り返すことを避けること）を掲げ、編集に着手する前に十分なコンテキストを読み込んでおくべきだとしている。作業の終え方についても、「do not end your turn with clarifications unless truly blocked」（本当に行き詰まっていない限り、確認の問いかけでターンを終えないこと）と述べ、不要な確認質問への逃げを戒めている。また、「if you find yourself re-reading or re-editing the same files without clear progress, stop」（明確な進捗のないまま同じファイルを読み直したり編集し直したりしていると気づいたら、そこで止まること）というループ検知の指針も示されている。行動指針全体としては「Bias to action: default to implementing with reasonable assumptions」（行動優先——妥当な前提を置いてまず実装すること）という原則が掲げられ、並列実行可能な複数のツール呼び出しは並列で行うべきだとしている。最終メッセージの書き方については「be very concise; friendly coding teammate tone」（簡潔さを保ち、親しみのあるコーディング仲間のような口調にすること）を基本とするとしている。

# 活用先

（コンセプト昇華時に追記）

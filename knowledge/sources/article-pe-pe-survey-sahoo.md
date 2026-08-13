---
type: Article
title: A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications
description: arXiv論文（Sahoo et al.）。41種類以上のプロンプトエンジニアリング技法をアプリケーション領域別に分類する体系的なタキソノミーを提示し、モデルパラメータを変更せずタスク特化の指示でLLM/VLMの出力を導く手法としてプロンプトエンジニアリングを整理している。
site: arXiv
published: unknown
retrieved: 2026-08-13
resource: https://arxiv.org/abs/2402.07927
origin: "web:arxiv.org"
source_tier: primary
tags: [prompt-engineering, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-13T00:00:00+09:00"
---

# 概要

本論文は、大規模言語モデル（LLM）と視覚言語モデル（VLM）の能力を拡張するための不可欠な技法としてプロンプトエンジニアリングが登場したと説明している。コアのモデルパラメータを変更することなく、タスク特化の指示（プロンプト）を活用してモデルの効力を高めるアプローチであると位置づけたうえで、多様なプロンプトエンジニアリング手法・技法についての体系的な整理と理解がこれまで欠けていたという課題認識を示し、そのギャップに応えるためアプリケーション領域別に分類した構造化された概要を提供すると述べている。

# 要点

## プロンプトエンジニアリングの定義

本論文は、プロンプトエンジニアリングを、モデルパラメータを更新する代わりに、与えられたプロンプトのみに基づいて望ましいモデルの挙動を引き出すことで、事前学習済みモデルを下流タスクへシームレスに統合する手法であると定義している。

> 引用: 「Prompt engineering has emerged as an indispensable technique for extending the capabilities of large language models (LLMs) and vision-language models (VLMs)... Rather than updating the model parameters, prompts allow seamless integration of pre-trained models into downstream tasks by eliciting desired model behaviors solely based on the given prompt.」

プロンプトは、モデルを導くための文脈を提供する自然言語の指示である場合もあれば、関連知識を活性化させる学習済みのベクトル表現である場合もあると説明している。この急成長する分野は、質問応答からcommonsense reasoningに至るまで、様々なアプリケーションで成功を収めてきたと述べている。

プロンプトエンジニアリングの重要性は、LLMとVLMの適応性に対する変革的なインパクトにおいて特に顕著であるとも説明している。慎重に作られた指示を通じてモデル出力を微調整するメカニズムを提供することで、多様なタスクとドメインにわたってモデルを卓越させることができるとし、これはタスク特化の性能を得るためにモデルの再学習や大規模なファインチューニングがしばしば必要とされる従来のパラダイムとは異なるアプローチであると位置づけている。

## 41種類以上の技法を分類する体系的なタキソノミー

本論文は、現代のプロンプトエンジニアリングの風景が、zero-shotやfew-shot promptingのような基礎的な手法から、「chain of code」promptingのようなより複雑なアプローチまで、幅広い技法のスペクトルにまたがっていると説明している。プロンプトエンジニアリングという概念は当初LLMにおいて研究・普及し（Liu et al., 2023; Tonmoy et al., 2024; Chen et al., 2023）、その後VLMへと拡張されたと述べている（Wu et al., 2023; Bahng et al., 2022）。

本論文は、こうした絶えず進化するプロンプトエンジニアリングの風景を深く分析し、アプリケーション別に分類した41種類以上の異なる技法を扱うと述べている。各プロンプティングアプローチについては、その手法の詳細、アプリケーション、関わるモデル、使用されたデータセットの要約を提供するとし、加えて各アプローチの強みと限界にも踏み込み、タキソノミー図と、データセット・モデル・各技法の重要ポイントをまとめた表を含むと説明している。

## Zero-Shot Prompting

本論文は、zero-shot promptingを、大規模LLMを活用する上でのパラダイムシフトを提供する技法であると説明している。この技法は大量の学習データの必要性を排除し、代わりにモデルを新規タスクへ導く慎重に作られたプロンプトに依存すると述べている（Radford et al., 2019）。具体的には、モデルはプロンプト内でタスクの説明を受け取るが、特定の入出力マッピングについての学習用ラベル付きデータは与えられない。モデルはその代わりに、自身が事前に持つ知識を活用し、与えられたプロンプトに基づいて新規タスクの予測を生成すると説明している。

## Few-Shot Prompting

本論文は、few-shot promptingについて、モデルに少数の入出力例を提示することで、与えられたタスクに対する理解を誘導する技法であると説明している。例が一切提供されないzero-shot promptingとは対照的な位置づけであるとしている（Brown et al., 2020）。質の高い例をわずかでも提供することで、実演を与えない場合と比べて複雑なタスクにおけるモデル性能が改善してきたと述べている。

一方で、few-shot promptingには制約もあると指摘している。例を含めるために追加のトークンが必要となり、これは長いテキスト入力に対しては禁止的なコストとなりうるとしている。さらに、プロンプト内に含める例の選択と構成はモデルの挙動に大きく影響しうる、頻出する単語を優先してしまうといったバイアスが依然としてfew-shotの結果に影響を及ぼしうるとも述べている。GPT-3のような大規模な事前学習済みモデルにおいて、few-shot promptingは特に複雑なタスクの能力を高める一方で、最適な性能を達成し、意図しないモデルバイアスを緩和するには、慎重なプロンプトエンジニアリングが重要であると結論づけている。

# 活用先

- [../prompt-engineering/what-is-prompt-engineering.md](../prompt-engineering/what-is-prompt-engineering.md) — プロンプトエンジニアリングの学術的な定義（モデルパラメータを更新せずプロンプトのみで挙動を引き出す）と、再学習・ファインチューニングを要する従来パラダイムとの違いの根拠
- [../prompt-engineering/core-techniques.md](../prompt-engineering/core-techniques.md) — zero-shot promptingの定義（ラベル付きデータなしに事前知識で予測を生成）、few-shot promptingの定義と限界（追加トークンのコスト、例の選択・構成が挙動に与える影響、頻出単語バイアス）の根拠
- [../prompt-engineering/taxonomy-and-landscape.md](../prompt-engineering/taxonomy-and-landscape.md) — 41種類以上をアプリケーション領域別に分類するタキソノミーの構成（手法詳細・モデル・データセット・強みと限界）と、基礎的手法からchain of codeまでのスペクトルという地図の骨格の根拠

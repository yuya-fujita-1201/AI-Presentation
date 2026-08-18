---
type: Article
title: "Ragas: Automated Evaluation of Retrieval Augmented Generation"
description: Es et al. (2023) が提案するreference-free評価フレームワークRagas。Faithfulness・Answer Relevance・Context Relevanceの3指標とWikiEvalでの検証結果を解説
site: arXiv / EACL 2024 (System Demonstrations)
published: unknown
retrieved: 2026-08-18
resource: https://arxiv.org/abs/2309.15217
origin: "web:arxiv.org"
source_tier: primary
tags: [rag, research, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-19T00:00:00+09:00"
---

# 概要

Shahul Es, Jithin James, Luis Espinosa-Anke, Steven Schockaertは、人間作成のground truthアノテーションに依存しない「reference-free」な評価フレームワークRagasを提案したと説明している。論文はRAGパイプラインを検索・生成・全体品質という複数の次元から評価する枠組みを示すものであり、著者らは「faster evaluation cycles」（より高速な評価サイクル）の実現がLLM採用の急速化において重要だと指摘している。

# 要点

## 提案の核心

論文は、人間が作成したground truthアノテーションに依存しない評価フレームワークとしてRagasを提案している。RAGパイプラインの性能を、検索・生成という個別の観点だけでなく全体品質の観点からも捉える複数次元の評価枠組みを示したとしている。

## 3つの評価指標

Ragasは、Faithfulness（忠実性）・Answer Relevance（回答関連性）・Context Relevance（コンテキスト関連性）という3つの指標から構成されるとしている。

- Faithfulness（忠実性）: 「答えの主張がコンテキストから推論できる場合、その答えはコンテキストに忠実である」と定義されている。手法としては、まずLLMを用いて回答から陳述文の集合S(as(q))を抽出し、各陳述文がコンテキストから支持されるかを検証関数v(si, c(q))で判定する。支持された陳述数を全陳述数で割ったF=|V|/|S|というスコアで算出するとしている。この指標は、幻覚の回避と、取得したコンテキストが生成回答の正当化として機能することを保証する狙いを持つとしている。
- Answer Relevance（回答関連性）: 生成された答えが実際の質問に直接対応している程度を測定する指標だとしている。手法としては、LLMが答えからn個の仮想質問を生成し、テキスト埋め込みモデルを用いて元の質問との余弦類似度の平均AR=(1/n)Σsim(q, qi)を算出する。この指標は、不完全な回答や冗長な情報を含む回答を罰するよう設計されているとしている。
- Context Relevance（コンテキスト関連性）: コンテキストが質問に答えるために必要な情報のみを含んでいる範囲を評価する指標だとしている。手法としては、LLMが質問に答えるうえで重要な文を抽出し、抽出文数をコンテキストの全文数で割ったスコアCRを算出する。この指標は、冗長な情報の混入と、長いコンテキストによるLLMの効果低下を防ぐ狙いを持つとしている。

## 実験結果

著者らは、Wikipediaの50ページから構築したデータセットWikiEvalを用いて評価を行ったとしている。人間評価との一致率は、Faithfulnessが0.95、Answer Relevanceが0.78、Context Relevanceが0.70と報告されている。比較対象としたGPT ScoreおよびGPT Rankingは、いずれも大幅に低い精度だったとしている。この結果は、人間によるアノテーションを介さずに機械的に算出した3指標のスコアが、人間評価者の判断と高い水準で一致することを示すものとして提示されている。著者らはこの結果を踏まえ、「faster evaluation cycles」の実現がLLM採用の急速化において重要だと指摘している。人間によるground truthの作成を待たずにRAGパイプラインの評価サイクルを回せる点が、reference-freeという設計の意義であるとまとめられている。

> 引用: 「faster evaluation cycles」

# 活用先

- [../rag/evaluation.md](../rag/evaluation.md) — reference-free評価という設計思想と「faster evaluation cycles」の引用、Faithfulness／Answer Relevance／Context Relevanceの定義と算出手順、各指標の狙い（幻覚回避・不完全/冗長な回答への罰・長コンテキストによる効果低下の防止）、WikiEvalでの人間評価一致率0.95／0.78／0.70とGPT Score・GPT Rankingとの比較

---
type: Article
title: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
description: Lewis et al. (2020) によるRAGアーキテクチャの原典論文。parametric memoryとnon-parametric memoryを組み合わせる構成と実験結果を解説
site: arXiv (NeurIPS 2020)
published: 2020-05-22
retrieved: 2026-08-18
resource: https://arxiv.org/abs/2005.11401
origin: "web:arxiv.org"
source_tier: primary
tags: [rag, research, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-18T00:00:00+09:00"
---

# 概要

Patrick Lewisらによる論文「Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks」は、2020年5月22日にarXivへ投稿され（ID: 2005.11401）、NeurIPS 2020に採択された研究である。「RAG」という略称・アーキテクチャの起源となった原典論文として位置づけられており、後続の実装や解説記事が繰り返し参照する基礎文献となっている。論文は、知識を必要とするNLPタスクに対して、検索(retrieval)と生成(generation)を組み合わせるアプローチの有効性を示すことを主眼としている。

# 要点

## 著者・書誌情報

著者はPatrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kielaの共著である。2020年5月22日にarXiv投稿（ID: 2005.11401）、NeurIPS 2020に採択されたことが明記されている。この論文は、「RAG」という略称・アーキテクチャの起源となった原典論文であるとまとめられている。

## モデル構成: parametric memoryとnon-parametric memoryの組み合わせ

RAGは、事前学習済みのparametric memory（seq2seqトランスフォーマー）と、non-parametric memory（事前学習済みニューラルレトリーバーでアクセスするWikipediaの密ベクトルインデックス）を組み合わせるモデル構成として説明されている。原文では「the parametric memory is a pre-trained seq2seq transformer, and the non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever」と記述されており、これら2種類の記憶をエンドツーエンドで微調整(fine-tune)する仕組みを提案したとされている。パラメトリックな知識とノンパラメトリックな知識を単一のモデル内で統合するという発想が、この論文の核となるアイデアである。

## 主要な貢献

論文の核心的貢献は、知識集約的なNLPタスクにおいて、単体のパラメトリックモデルやタスク特化型アーキテクチャを上回る性能を示した点にあるとまとめられている。アブストラクトでは「RAG models generate more specific, diverse and factual language than a state-of-the-art parametric-only seq2seq baseline」と明記されており、著者らはRAGが従来のパラメトリック単体モデルのベースラインよりも、より具体的・多様・事実に忠実な言語を生成すると主張している。

## 実験結果

著者らは、3つのオープンドメイン質問応答タスクにおいて、当時の最先端(state-of-the-art)を達成したと報告している。加えて、言語生成タスクにおいても、既存の手法より具体性・多様性・事実性の高い出力を生成したと結論づけている。これらの結果から、検索によって外部知識を動的に参照する構成が、知識集約的なタスク全般で有効であることを示す実証研究として位置づけられている。

> 引用: 「RAG models generate more specific, diverse and factual language than a state-of-the-art parametric-only seq2seq baseline.」

# 活用先

- [../rag/rag-origin-and-definition.md](../rag/rag-origin-and-definition.md) — 書誌情報（arXiv 2005.11401 / NeurIPS 2020）、parametric memoryとnon-parametric memoryの組み合わせという提案の核、3タスクでのSOTA達成と「more specific, diverse and factual」という主張の主根拠
- [../rag/rag-and-neighbors.md](../rag/rag-and-neighbors.md) — parametric memory / non-parametric memory という2種類の記憶の呼び分けと、それらをエンドツーエンドで微調整（fine-tune）する構成。RAGとファインチューニングが原典では排他でなく役割分担であることの根拠

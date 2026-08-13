---
type: Article
title: "Deeper insights into retrieval augmented generation: The role of sufficient context"
description: "Google ResearchによるSufficient Context研究の公式解説。検索結果が質問に関連するだけでなく、確定的に答えるための必要情報を含むかを分け、RAGの誤答と棄権を分析している。"
source_id: CE-S07
site: Google Research
published: "2025-05-14"
retrieved: "2026-08-14"
resource: "https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/"
origin: "web:research.google"
source_tier: primary
tags: [rag, sufficient-context, retrieval, hallucination, abstention, evaluation]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Google ResearchがICLR 2025採択研究「Sufficient Context: A New Lens on Retrieval Augmented Generation Systems」を解説した記事。検索結果が質問に関連しているかだけでなく、確定的な回答に必要な情報をすべて含んでいるかという「十分性」を導入し、RAGの失敗を「モデルが使えなかった」のか「材料が足りなかった」のかに分けて分析している。

# 要点

- 十分なコンテキストは、質問へ確定的に答えるための必要情報を含む。話題が関連していても、答えの根拠が欠けていれば不十分である。
- RAGの評価では、検索の関連度だけでなく、回答に必要な情報がそろっているかを別に判定する必要がある。
- 研究対象では、十分な材料があると強いモデルでも、不十分な材料のときに誤答を避けて棄権することは難しい場合があった。
- 対策候補として、生成前の十分性判定、追加検索や再順位付け、信頼度と十分性を使った棄権判断を挙げている。
- 不十分と判定された文脈にも、曖昧さを減らすなど部分的な有用性がある場合があり、二値判定だけで価値を切り捨てない。

# 適用範囲と留保

- 記事は特定の質問応答データセット、モデル群、LLMによる自動評価器を用いた研究の解説である。他の業務、言語、長文生成へ同じ割合や傾向を直接一般化しない。
- 「十分」は質問と期待する回答粒度に依存する。一般に固定された十分量があるわけではない。
- 十分性判定器そのものも誤り得るため、重要業務では根拠表示、人手確認、追加取得の停止条件を組み合わせる。
- コンテキストを追加すれば必ず安全になるわけではない。実験では不十分な追加情報が誤った確信につながる場合も観測されている。

# 原文の根拠箇所

- **関連性と十分性の区別**: `Key insights into RAG systems`
- **不十分な追加情報と誤答**: `Adding context leads to more hallucinations`
- **十分性判定と棄権**: `Selective generation to reduce hallucinations`

# デッキで安全に使える表現

- 「関連している資料と、答えるのに十分な資料は同じではありません。」
- 「RAGでは『何件取れたか』だけでなく、『質問の各要素を裏付ける材料がそろったか』を確認します。」
- 「材料が足りないときは、追加検索する、範囲を限定する、わからないと返す、の分岐を設計します。」

# 活用先

- [../context-engineering/selection-and-sufficiency.md](../context-engineering/selection-and-sufficiency.md) — 関連性と十分性の区別、追加検索と棄権
- [../context-engineering/practical-context-packs.md](../context-engineering/practical-context-packs.md) — 取得失敗と利用失敗を分ける評価

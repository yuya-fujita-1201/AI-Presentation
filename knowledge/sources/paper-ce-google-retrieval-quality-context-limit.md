---
type: Paper
title: "Retrieval Quality at Context Limit"
description: "Gemini 2.5 Flashを単純なneedle-in-a-haystack型の事実質問で評価し、文書位置や入力上限近傍でも高い検索性能を報告したGoogle Research掲載論文。Lost in the Middleの普遍的な一般化に留保を与える。"
source_id: CE-S05
site: Google Research
published: "2025"
retrieved: "2026-08-14"
resource: "https://research.google/pubs/retrieval-quality-at-context-limit/"
origin: "web:research.google"
source_tier: primary
tags: [context-window, long-context, retrieval, gemini, evaluation, replication]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Max McKinnonによる短い評価研究。Gemini 2.5 Flashを対象に、長い入力の中から単純な事実を取り出すneedle-in-a-haystack形式で、情報の位置と入力上限付近での検索品質を調べた。著者はこの条件では、先行研究で知られる「Lost in the Middle」型の位置効果が確認されなかったと報告している。

# 要点

- 長文脈検索能力はモデル世代によって改善し得るため、古い研究結果を現在の全モデルへ固定的に当てはめないことを示唆する。
- 入力の中央や上限付近に情報があっても、対象モデルは単純な事実検索課題で高い性能を示した。
- 「長いほど必ず読めない」という断定ではなく、モデルと課題ごとの評価が必要だという反証材料になる。

# 適用範囲と留保

- 対象はGemini 2.5 Flashという一つのモデルで、課題も単純な事実質問である。複数文書の統合、長文要約、曖昧な指示、複数根拠の推論へは一般化できない。
- 論文は短い報告であり、すべての長文脈能力を網羅する大規模比較ではない。
- 「Lost in the Middleを完全に否定した」ではなく、「少なくともこのモデルと単純課題では観測されなかった」と表現する。
- 高い検索精度が、コスト、待ち時間、データ鮮度、安全性、矛盾処理まで解決するわけではない。

# 原文の根拠箇所

- **著者・掲載年**: Google Research掲載ページの著者欄 `Max McKinnon` と年 `2025`
- **モデル・課題・結果**: `Abstract`（Gemini 2.5 Flash単一、needle-in-a-haystack形式のsimple factoid Q&A）
- **適用限界**: 同じ `Abstract` の実験対象から、本台帳で複数文書統合等への一般化を除外

# デッキで安全に使える表現

- 「長文脈の位置効果は固定法則ではありません。新しい単一モデルの単純検索では、中央や上限近くでも高精度だった報告があります。」
- 「だからこそ『長い文脈は危険』とも『全部入れれば安心』とも断定せず、実際の仕事に近い課題で測ります。」
- 「容量だけでなく、検索、統合、推論、矛盾処理を別々に評価します。」

# 活用先

- [../context-engineering/context-window-and-attention.md](../context-engineering/context-window-and-attention.md) — Lost in the Middleを普遍法則にしないための対照研究
- [../context-engineering/practical-context-packs.md](../context-engineering/practical-context-packs.md) — モデル・課題別評価と反証可能性

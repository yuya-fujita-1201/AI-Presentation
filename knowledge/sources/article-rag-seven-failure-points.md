---
type: Article
title: Seven Failure Points When Engineering a Retrieval Augmented Generation System
description: Barnett et al. (2024) が研究・教育・バイオメディカルの3ケーススタディから特定したRAGシステムの7つの失敗点(FP1〜FP7)を解説
site: arXiv / ACM (IEEE/ACM 3rd International Conference on AI Engineering – CAIN 2024)
published: unknown
retrieved: 2026-08-18
resource: https://arxiv.org/abs/2401.05856
origin: "web:arxiv.org"
source_tier: primary
tags: [rag, research, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-19T00:00:00+09:00"
---

# 概要

Barnett et al. (2024) は、RAG（検索拡張生成）システムを実装する際に生じる典型的な失敗点を7種類（FP1〜FP7）に整理し、研究・教育・バイオメディカルの3つのケーススタディを通じて実証したと説明している。論文の核心的な主張は、RAGシステムの検証は設計段階では実現できず実運用を通じてしか行えないという点と、堅牢性は設計時に組み込まれるものではなく段階的に発展していくものだという点の2つである。

# 要点

## 7つの失敗点（FP1〜FP7）

論文は失敗点をFP1からFP7まで番号を付けて整理している。

- FP1 Missing Content: 利用可能な文書では答えられない質問をした場合に発生する失敗だとしている。原文では「asking a question that cannot be answered from the available documents」と説明されている。
- FP2 Missed the Top Ranked Documents: 答えが文書内に存在していても、検索の上位K件のランキングに入らず結果として返されないケースを指すとしている。
- FP3 Not in Context - Consolidation Strategy Limitations: 多数の文書を統合する過程で、回答を含む文書がコンテキストから脱落する失敗だとしている。原文は「Documents with the answer were retrieved from the database but did not make it into the context」と述べている。
- FP4 Not Extracted: コンテキスト中に答えが存在していても、大規模言語モデルが正しい答えを抽出できないケースだとしている。原文は「the answer is present in the context, but the large language model failed to extract out the correct answer」と説明しており、ノイズや矛盾する情報が多い場合に発生しやすいとしている。
- FP5 Wrong Format: テーブルやリスト形式で抽出するよう指示しても、大規模言語モデルがその指示を無視してしまうケースを指すとしている。
- FP6 Incorrect Specificity: 回答自体は返されるものの、ユーザーが求める粒度と合わず具体性が過不足するケースだとしている。原文は「The answer is returned in the response but is not specific enough or is too specific」と説明している。
- FP7 Incomplete: コンテキスト内に情報が存在するにもかかわらず、その一部しか抽出できず回答が不完全になるケースだとしている。論文は「Incomplete answers are not incorrect but miss some of the information even though that information was in the context」と述べ、誤りではなく欠落である点を強調している。

## ケーススタディ（3領域）

論文はこれら7つの失敗点を、性質の異なる3つの領域のケーススタディを通じて検証したと説明している。研究領域では、科学論文の分析支援を行い目的に応じた文書ランキング機能を備えたCognitive Reviewerを用いた。教育領域では、Whisperで動画を書き起こし、動画・HTML・PDFなど複数形式の教材に対応するAI Tutorを用いた。バイオメディカル領域では、BioASQデータセットから4017件のオープンアクセス文書と1000問の質問を用いた大規模な実験を通じて失敗点を検証したとしている。

## 結論

論文はRAGシステムの検証が「実運用時にしか実現できない」という点と、堅牢性が「設計時に組み込まれるのではなく段階的に発展する」という点の2つを核心的な結論として提示している。

> 引用: 「validation of a RAG system is only feasible during operation, and the robustness of a RAG system evolves rather than designed in at the start.」

今後の研究方向としては、チャンク戦略や埋め込み手法の改善、RAGとファインチューニングの比較、テストおよびモニタリング手法の確立を挙げているとしている。

# 適用範囲と留保

- ケーススタディは研究（Cognitive Reviewer）・教育（AI Tutor）・バイオメディカル（BioASQ：4017件のオープンアクセス文書、1000問、いずれも英語）の3領域に限定される。日本語の社内文書ドメインでの再現性は示されていない
- 著者ら自身が実施した検証であり、独立した第三者による追試ではない

# 活用先

- [../rag/failure-modes.md](../rag/failure-modes.md) — FP1〜FP7の名称と定義、FP4がノイズや矛盾で起きやすいこと、FP7が「誤りではなく欠落」であるという強調、3領域のケーススタディ、「検証は運用時にしか実現できず堅牢性は段階的に発展する」という結論文
- [../rag/evaluation.md](../rag/evaluation.md) — 「検証は運用時にしか実現できず堅牢性は段階的に発展する」という結論を評価ループの必要性の根拠として、およびRagas 3指標とFP1〜FP7の対応づけ

---
type: Article
title: "Self-Refine: Iterative Refinement with Self-Feedback"
description: Self-Refineは、同一のLLMが生成・批評・改善の三役を担い、追加学習なしで出力品質を反復的に高められると論文が主張していることを解説する。
site: arXiv (Madaan et al.)
published: unknown
retrieved: 2026-08-15
resource: https://arxiv.org/abs/2303.17651
origin: "web:arxiv.org"
source_tier: primary
tags: [loop-engineering, self-refine, iterative-refinement, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-15T00:00:00+09:00"
---

# 概要

本論文は、Madaan et al.によるSelf-Refineという手法を提案していると説明している。LLMは初回生成で必ずしも最良の出力を作れないという人間の執筆・推敲プロセスに着想を得た手法であり、追加の教師データ・追加学習・強化学習を一切必要とせずに、同一モデルが自らの出力を反復的に改善できる点を中心的な貢献として位置づけている。評価実験は7種類の多様なタスクにまたがって行われ、GPT-3.5・ChatGPT・GPT-4という3種類のモデルで効果が検証されたとされる。また、この反復的な自己改善の枠組みは、loop engineeringの文脈で頻繁に参照される「自己改善ループ」の原典として位置づけられている。

# 要点

## 提案の背景

論文は、人間が文章を書くときに一度で完成させるのではなく、推敲を重ねながら質を高めていく過程に着想を得ていると述べている。この着想の出発点として、論文冒頭では次のように指摘されている。

> 引用: 「Like humans, large language models (LLMs) do not always generate the best output on their first try.」

この一文は、LLMの初回出力をそのまま最終出力として扱うのではなく、出力そのものを反復的な改善の対象とみなす発想の土台になっていると読み取れる。人間の執筆行為とのアナロジーによって、モデルの出力精度を高める手段として「再生成」ではなく「自己による推敲」を採用する着想が導かれている。

## 手法の骨格

Self-Refineの手順として、論文は同一のLLMが生成器・批評者・改善者という三つの役割を兼ねる構成を説明している。具体的な流れは次の3ステップで構成される。

1. 初期出力を生成する
2. 同じLLMがその出力に対してフィードバックを与える
3. フィードバックを用いて出力を改善する

つまり、生成・フィードバック・改善という3段階を1サイクルとして繰り返す設計である。この3ステップを、満足のいく結果が得られるまで反復するというのがSelf-Refineの中核的な仕組みである。論文はこの一連の流れを次のように表現している。

> 引用: 「the same LLM provides feedback for its output and uses it to refine itself, iteratively」

さらに論文が強調しているのは、この手法が追加の教師データ・追加学習・強化学習のいずれも必要としない点である。

> 引用: 「Self-Refine does not require any supervised training data, additional training, or reinforcement learning.」

生成・批評・改善のすべてを単一モデルへのプロンプトのやり取りだけで完結させることで、パラメータ更新を伴う追加学習フェーズを挟まずに出力品質の向上を図れるという主張になっている。この「追加学習なしの反復改善」という設計方針が、Self-Refineを他の性能改善手法と区別する特徴として位置づけられている。

## 評価設定

論文は、対話応答生成から数学的推論まで多様な7種類のタスクでSelf-Refineの効果を評価したと報告している。使用したモデルはGPT-3.5・ChatGPT・GPT-4の3種類であり、単一のモデル世代だけでなく複数世代のモデルにまたがって効果を検証している点が特徴として述べられている。

## 性能結果

評価の結果として、論文はSelf-Refineで生成した出力が、同一LLMによる従来の一段階生成と比較して、人手評価・自動評価指標の双方で好まれたと述べている。タスク性能では平均して約20%の絶対的改善を達成したと報告されている。

> 引用: 「outputs generated with Self-Refine are preferred by humans and automatic metrics over those generated with the same LLM using conventional one-step generation」

この結果は、追加学習を経ずに同一モデル内の反復プロセスだけで出力品質を底上げできることを示すものとして提示されている。人手評価と自動評価指標の両方で一貫して優位性が見られたという記述は、この改善が特定の評価基準に偏った結果ではないことを示す根拠として扱われている。

## loop engineeringにおける位置づけ

本論文は、loop engineeringの文脈で頻繁に参照される「自己改善ループ」の原典として位置づけられている。同一モデルが生成・批評・改善という三役を兼ね、満足のいく結果が得られるまで反復するという構成は、後続の自己リファインメント系研究(RCI, CRITIC, Self-Correctなど)の起点になっているとされる。追加学習を必要としないという特性は、実運用のエージェントループに組み込みやすい手法として参照される理由の一つになっていると考えられる。

# 活用先

（コンセプト昇華時に追記）

---
type: Paper
title: "Lost in the Middle: How Language Models Use Long Contexts"
description: "長い入力内の関連情報の位置が性能へ与える影響を、複数文書質問応答とキー・バリュー検索で調べた研究。対象となった当時のモデルでは、関連情報が入力中央にあると性能が落ちる場合を報告した。"
source_id: CE-S04
site: arXiv
published: "2023-07-06"
retrieved: "2026-08-14"
resource: "https://arxiv.org/abs/2307.03172"
origin: "web:arxiv.org"
source_tier: primary
tags: [context-window, long-context, retrieval, position-effects, evaluation]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Nelson F. Liuらが、長い入力を受け取れる言語モデルが、その全体をどの程度安定して使えるかを調べた研究。複数文書質問応答とキー・バリュー検索を用い、関連情報の位置を変えたときに、入力の先頭や末尾より中央で性能が低下する傾向を観測した。論文はTACLへの採択が記載されている。

# 要点

- 「コンテキストウィンドウに入る」ことと「必要な情報を安定して利用できる」ことは同義ではない、という評価上の問題を示した。
- 同じ情報量でも、関連情報の位置によって結果が変わる場合があるため、単純な最大入力長だけでは実用性能を説明できない。
- 長文脈モデルを評価する際に、入力長だけでなく、関連情報の位置と課題形式も変えて確認するプロトコルを提案した。

# 適用範囲と留保

- 研究対象は公開当時のモデルと、複数文書質問応答・キー検索という限定された課題である。「現在の全モデルは必ず中央を読めない」と一般化してはいけない。
- 観測された位置効果は、モデル、プロンプト、データ、検索課題の難度によって変わり得る。
- 後続研究には、特定の新しいモデルと単純な事実検索では同じ効果が見られなかったという報告もある。両者は対象条件が異なるため、単純な否定関係にはしない。
- これは長文脈利用の評価研究であり、RAG、メモリ、圧縮、プロンプトキャッシュの優劣を直接比較した研究ではない。

# 原文の根拠箇所

- **研究全体と主結果**: `Abstract`
- **複数文書QAの条件**: 論文 `§2 Multi-Document Question Answering`
- **位置効果の留保を含む結論**: 論文 `§7 Conclusion`
- **固定版**: arXiv `2307.03172`（TACL 2024採録情報はabstract pageで確認）

# デッキで安全に使える表現

- 「長い入力を受け取れることは、その中の必要情報をいつでも同じ精度で使えることを保証しません。」
- 「旧世代を含む限定実験では、関連情報の置き場所で性能が変わる例が報告されました。現在のモデルでも自分の課題で評価が必要です。」
- 「最大コンテキスト長は容量の指標。使いこなしやすさは、モデル・課題・情報配置を含めて測ります。」

# 活用先

- [../context-engineering/context-window-and-attention.md](../context-engineering/context-window-and-attention.md) — 容量と実利用性能を分ける根拠
- [../context-engineering/practical-context-packs.md](../context-engineering/practical-context-packs.md) — 情報位置を変える長文脈テストの観点

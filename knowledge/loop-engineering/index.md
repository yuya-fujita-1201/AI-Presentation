# loop-engineering — ループエンジニアリングについてのナレッジ

エージェントに1回ずつプロンプトを打つのをやめ、実行・検証・改善を自動で繰り返す仕組みそのものを設計する考え方「ループエンジニアリング」についてまとめたディレクトリ。想定読者は、チャット型AIは使ったことがあるがエージェント的な使い方は未経験の方。

情報源は解説動画4本と記事8本の計13本（[../sources/index.md](../sources/index.md) を参照）。定義や数値は出所の異なる複数資料を突き合わせたうえで記述し、自動字幕からの聞き取りに依拠する箇所はその旨を明記している。

## 内容

- [what-is-loop-engineering.md](./what-is-loop-engineering.md) — ループエンジニアリングとは何か。「プロンプトを打つ人」を自分から外すという定義、チャットAIの使い方との違い、Human in the Loop から Human on the Loop への移行
- [from-prompt-to-loop.md](./from-prompt-to-loop.md) — プロンプト→コンテキスト→ハーネス→ループという段階の積み上がり。乗り換えではなく入れ子であること、プロンプトエンジニアリングとの焦点・評価者・失敗モードの違い
- [anatomy-of-a-loop.md](./anatomy-of-a-loop.md) — ループの解剖。Intent-Context-Action-Observation-Adjustment の5段階、設計の4ポイント、インナー／アウターの2層、速度の異なる3つの入れ子ループ
- [goal-and-stop-conditions.md](./goal-and-stop-conditions.md) — ゴールと停止条件の設計。核心は回し方ではなく止め方であること、ゴールを先に定義する原則、停止条件の多重化、ハードストップの置き方
- [verification-design.md](./verification-design.md) — 検証の設計。合否を返すチェックの用意の仕方、機械判定とLLM判定の使い分け、強制力を高める4段階、自己申告ではなく証拠を出させる運用
- [maker-checker-separation.md](./maker-checker-separation.md) — 作る役と採点する役を分ける。AIが自分の成果物に甘くなる性質、RefineBench の数値、権限剥奪による物理的な分離
- [self-refine-and-evaluator-optimizer.md](./self-refine-and-evaluator-optimizer.md) — 学術的な土台と参照実装。ReAct・Reflection・Self-Refine の系譜と、Anthropic 公式の evaluator-optimizer
- [loop-parts-and-harness.md](./loop-parts-and-harness.md) — ループを支える部品。自動化・ワークツリー・スキル・接続・サブエージェント＋メモリー、ロングラン自律動作の技術群、3ファイルの最小構成
- [when-to-use-loops.md](./when-to-use-loops.md) — いつループを使うか。有効に働く3条件と不向きな2条件、症状別の使い分け、5つの実践パターン、対象を狭く切って始める導入手順
- [risks-and-costs.md](./risks-and-costs.md) — 回しっぱなしの代価。トークン暴走・検証の積み残し・理解の劣化・判断の放棄、局所最適、検証の抜け道、人間が手放してはいけない判断

## 読む順番

初めての人は what-is-loop-engineering → from-prompt-to-loop → anatomy-of-a-loop の順に読むと、用語と全体像がつかめる。

そのうえで goal-and-stop-conditions → verification-design → maker-checker-separation が設計の中核にあたる。ループは「止め方」と「合否の返し方」でほぼ決まるため、実際に組むつもりならこの3本は飛ばさないほうがよい。

背景を知りたい場合は self-refine-and-evaluator-optimizer で学術的な土台と公式の参照実装を、手を動かす段になったら loop-parts-and-harness で部品と最小構成を確認する。

最後に when-to-use-loops → risks-and-costs で、適用すべきタスクの見極めと払う代価を押さえる。**時間がない場合は what-is-loop-engineering → goal-and-stop-conditions → risks-and-costs の3本**でも、何をする考え方で何に気をつけるかは通る。

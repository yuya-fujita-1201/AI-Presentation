---
type: Concept
title: Self-Refineとevaluator-optimizer——ループの土台と参照実装
description: ループエンジニアリングの学術的な土台（ReAct・Reflection・Self-Refine）とAnthropic公式のevaluator-optimizer実装を突き合わせ、生成と評価を分けて反復するという構造、履歴を積み増す設計、PASSという明確な終了条件を読み解く
tags: [loop-engineering, self-refine, evaluator-optimizer, react, reflection, agentic-workflow]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-15T12:55:00+09:00"
---

# Self-Refineとevaluator-optimizer——ループの土台と参照実装

「ループエンジニアリング」という言葉が広まったのは2026年だが、**中身の構造そのものは新発明ではない**。RUNTEQ の動画は、これを思いつきの流行語ではなく研究上の土台があるものとして紹介している（[動画: RUNTEQ](../sources/video-pe-loop-engineering-5plus1-parts.md)、聞き取り）。ここでは、その土台と、すぐ真似できる参照実装を1つずつ見ていく。実装を1本でも読んでおくと、[ループの解剖](./anatomy-of-a-loop.md)で見た抽象的な段階が具体的なコードに落ちる。

## 系譜——ReAct と Reflection

同動画が学術的な土台として挙げているのは次の2つである（聞き取り）。

- **ReAct**: 考えて（Reason）、行動して（Act）、観測して、また思考する、というサイクルを繰り返す考え方
- **Reflection**: 失敗を言葉にして記録し、次のトライに生かすパターン

この2つを並べると、ループの2つの軸が見える。ReAct は**1周をどう回すか**、Reflection は**周と周をどうつなぐか**である。前者だけだと同じ失敗を繰り返し、後者だけだと何も動かない。以降で見る2つの手法は、いずれもこの両方を含んでいる。

## Self-Refine——同一モデルが三役を兼ねる

Madaan らによる論文「Self-Refine: Iterative Refinement with Self-Feedback」は、この分野で頻繁に参照される原典として位置づけられている（[記事: Self-Refine (arXiv)](../sources/article-le-self-refine.md)）。着想は素朴で、論文冒頭はこう書いている。

> Like humans, large language models (LLMs) do not always generate the best output on their first try.

人間と同じで、LLMも一発目が最良とは限らない——だから初回出力を最終出力として扱わず、**出力そのものを推敲の対象にする**、という発想である。手順は3ステップで、同一のLLMが生成器・批評者・改善者の三役を兼ねる。

1. 初期出力を生成する
2. 同じLLMがその出力に対してフィードバックを与える
3. フィードバックを用いて出力を改善する

> the same LLM provides feedback for its output and uses it to refine itself, iteratively

この3ステップを1サイクルとして、満足のいく結果が得られるまで繰り返す。論文が強調しているのは、この手法が**追加の教師データ・追加学習・強化学習のいずれも必要としない**点である。

> Self-Refine does not require any supervised training data, additional training, or reinforcement learning.

評価は対話応答生成から数学的推論まで7種類のタスク、GPT-3.5・ChatGPT・GPT-4 の3モデルで行われ、Self-Refine の出力は同一LLMの従来の一段階生成と比べて人手評価・自動評価指標の双方で好まれ、**タスク性能は平均して約20%の絶対的改善**を達成したと報告されている。

ここが実務にとって大きい。**モデルを差し替えなくても、回し方を変えるだけで質が上がる余地がある**という主張だからである。追加学習が要らないということは、プロンプトのやり取りだけで組める——つまり今日の自分の環境で試せる。

MindStudio の記事は、この Self-Refine を loop engineering の**具体的な実装例**として位置づけている（[記事: MindStudio](../sources/article-le-loop-engineering-mindstudio.md)）。同一モデルが生成・批評・改善を行い満足のいく結果に至るまで反復する構成が、loop engineering という枠組みの中に収まる、という整理である。つまり loop engineering は新しい技術の発表というより、**Self-Refine のような既存の反復的自己改善アプローチを一般化した上位概念**として提示されている、と読める。

なお、同一モデルに批評をさせることの限界については[作る役と採点する役を分ける](./maker-checker-separation.md)で扱った。Self-Refine の報告と、自己修正はほとんど伸びないとする RefineBench の紹介は緊張関係にあり、手元の資料だけでは決着しない。

## evaluator-optimizer——公式の参照実装

Anthropic公式の Claude Cookbook が示す evaluator-optimizer は、Self-Refine の構造を**別々のLLM呼び出しに割った**形の参照実装である（[記事: Anthropic Claude Cookbook](../sources/article-le-evaluator-optimizer.md)）。`generate`・`evaluate`・`loop` という3つの関数からなる。

### generate——思考と応答を分けて返す

`generate(prompt, task, context)` は、docstring で「フィードバックに基づいて解決策を生成・改善する」関数と説明されている。プロンプト・タスク・（存在すれば）これまでのコンテキストを結合してLLMを呼び、応答から `thoughts` タグと `response` タグをそれぞれ抽出して、両者をタプルで返す。生成過程の思考と生成結果を分けて取り出しているのがポイントである。

### evaluate——評価とフィードバックを分けて返す

`evaluate(prompt, content, task)` は「解決策が要件を満たしているかを評価する」関数である。元のタスクと評価対象のコンテンツを組み合わせたプロンプトでLLMを呼び、応答から `evaluation` タグ（評価ステータス）と `feedback` タグ（フィードバック内容）を抽出して返す。

**合否と理由が別々のフィールドとして返る**——この形が重要である。合否だけならループは止められるが改善できない。理由だけなら止まらない。両方あって初めて、[検証の設計](./verification-design.md)で見た「合否を返すチェック」がループとして閉じる。

### loop——PASSになるまで履歴を積み増す

中核が `loop(task, evaluator_prompt, generator_prompt)` である。動きはこうなっている。

1. まずコンテキストなしで `generate` を呼び、結果を `memory`（過去の試行結果のリスト）と `chain_of_thought`（思考と結果の記録リスト）に追加する
2. ループの中で `evaluate` を呼ぶ
3. 評価結果が `"PASS"` なら、その時点の結果と `chain_of_thought` 全体を返して終了する
4. `"PASS"` でなければ、`memory` に蓄積された**全試行内容**と直近のフィードバックを `"Previous attempts:"` という見出しでまとめた文字列を新しいコンテキストとして `generate` を再度呼び、結果を追加してループを継続する

同ページは、この実装の特徴を**単に生成をやり直すのではなく、過去の試行履歴とフィードバックの両方をコンテキストとして次の生成に渡し続ける**点だと位置づけている。そして、評価が `"PASS"` を返すという明確な終了条件を持つため、無限に回り続けることのない反復構造になっているとしている。

ここには、実務でそのまま使える設計判断が2つ入っている。

- **やり直しではなく積み増し**。前回の失敗を捨てて白紙から作り直すと、同じ失敗を再生産する。過去の試行を渡すことで、これは前述の Reflection にあたる働きをする
- **終了条件を評価側に持たせる**。回数ではなく `"PASS"` という評価結果で止める。回数制限は暴走を防ぐ保険であって、本来の終了条件ではない（[ゴールと停止条件の設計](./goal-and-stop-conditions.md)）

## いつ効くのか

同ページは、evaluator-optimizer が特に効果的な条件として次の2つを挙げている。

- **明確な評価基準がある**
- **反復的な改善に価値がある**

さらに、適合の良さを判断する2つの兆候として、**フィードバックを与えることでLLMの応答が明確に改善されること**、**LLM自身が有意義なフィードバックを提供できること**を挙げている。

この4項目は、そのままチェックリストとして使える。**手元のタスクでこの4つが埋まらないなら、ループにしても報われない。** 特に3つ目と4つ目は、小さく試せば数分で確かめられる——一度フィードバックを手で与えてみて、出力が明確に良くなるかを見ればよい。適用条件の全体像は[いつループを使うか](./when-to-use-loops.md)で扱う。

## 2つを並べて見る

| | Self-Refine | evaluator-optimizer |
|---|---|---|
| 出所 | arXiv（研究） | Anthropic 公式 Cookbook（実装） |
| 生成と評価 | 同一LLMが三役を兼ねる | 別々のLLM呼び出しに分ける |
| 終了条件 | 満足のいく結果が得られるまで | 評価が `"PASS"` を返すまで |
| 前回の扱い | フィードバックを次の改善に渡す | 全試行履歴＋フィードバックを積み増す |
| 前提 | 追加学習・教師データ・強化学習は不要 | 明確な評価基準があること |

骨格は同じである。**生成する・評価する・その結果を次の生成に渡す**——この3つがそろえばループになる。違いは、評価者を誰にするか（同一モデルか別呼び出しか）と、何を持って止めるかの明示度だけだと言ってよい。

最初に組むなら evaluator-optimizer の形を勧める。関数が3つに分かれていること自体が、[ループの解剖](./anatomy-of-a-loop.md)で見た段階と対応しており、どこが壊れているかを切り分けやすいからである。

## まとめ

- ループの構造には ReAct（1周の回し方）と Reflection（周と周のつなぎ方）という土台がある
- Self-Refine は同一モデルの三役で、追加学習なしに平均約20%の改善を報告している
- evaluator-optimizer は生成と評価を別呼び出しに割った公式の参照実装で、`"PASS"` という明確な終了条件を持つ
- 実装の要点は**やり直しではなく履歴の積み増し**、そして**終了条件を回数ではなく評価に持たせる**こと
- 適用の目安は「明確な評価基準がある」「反復に価値がある」「フィードバックで改善する」「有意義なフィードバックを出せる」の4点

## 次に読む

- [作る役と採点する役を分ける](./maker-checker-separation.md) — 評価者を別にすべきかどうかの論点
- [ループを支える部品](./loop-parts-and-harness.md) — この構造を日常の環境で回すために必要な道具立て
- [いつループを使うか](./when-to-use-loops.md) — 4つの適用条件をタスクに当てはめる

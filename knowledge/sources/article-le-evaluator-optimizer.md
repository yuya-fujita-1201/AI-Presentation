---
type: Article
title: Evaluator optimizer | Claude Cookbook
description: 生成と評価を別々のLLM呼び出しに分離し、評価がPASSになるまで過去の試行とフィードバックを積み増しながら再生成を繰り返すevaluator-optimizerワークフローのリファレンス実装を解説するAnthropic公式ページ
site: Anthropic (Claude Developer Platform / Claude Cookbook)
published: unknown
retrieved: 2026-08-15
resource: https://platform.claude.com/cookbook/patterns-agents-evaluator-optimizer
origin: "web:claude.com"
source_tier: secondary
tags: [loop-engineering, claude-code, agentic-workflow, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-15T00:00:00+09:00"
---

# 概要

Anthropic公式のClaude Developer Platformが公開する「Claude Cookbook」内の解説ページ「Evaluator optimizer」は、生成と評価を別々のLLM呼び出しに分離して反復させるエージェントワークフローのパターンを解説している。同ページは、このワークフローを「一方のLLM呼び出しが応答を生成し、別のLLM呼び出しがループの中で評価とフィードバックを行う」パターンと定義し、明確な評価基準が存在し反復的な改善に価値がある場面で特に効果を発揮すると述べている。あわせて、`generate`・`evaluate`・`loop`という3つの関数からなるPythonのリファレンス実装を提示している。

# 要点

## このワークフローが有効な場面

同ページは、evaluator-optimizerワークフローが特に効果的なのは「明確な評価基準がある」「反復的な改善に価値がある」という2条件を満たす場合だと説明している。さらに、適合の良さを判断する2つの兆候として、フィードバックを与えることでLLMの応答が明確に改善されること、そしてLLM自身が有意義なフィードバックを提供できることを挙げている。

> 引用: 「In this workflow, one LLM call generates a response while another provides evaluation and feedback in a loop.」

## generate関数: 思考と応答を分離して生成する

同ページのリファレンス実装のうち`generate(prompt, task, context)`関数は、コード中のdocstringで「フィードバックに基づいて解決策を生成・改善する(Generate and improve a solution based on feedback.)」関数と説明されている。実装としては、プロンプトとタスク、そして(存在すれば)これまでのコンテキストを結合したプロンプト文字列を組み立ててLLM呼び出しを行うとしている。応答からは`thoughts`タグと`response`タグをそれぞれ抽出し、生成過程の思考内容(Thoughts)と実際の生成結果(Generated)を「=== GENERATION START ===」「=== GENERATION END ===」というマーカー行で挟んで標準出力に整形表示したうえで、両者をタプルとして返す構造になっていると説明されている。

## evaluate関数: 評価結果とフィードバックを分離して返す

`evaluate(prompt, content, task)`関数は、docstringで「解決策が要件を満たしているかを評価する(Evaluate if a solution meets requirements.)」関数と説明されている。実装は、元のタスクと評価対象のコンテンツを組み合わせたプロンプトでLLMを呼び出し、応答から`evaluation`タグと`feedback`タグを抽出するとしている。評価のステータス(Status)とフィードバック内容(Feedback)を「=== EVALUATION START ===」「=== EVALUATION END ===」というマーカー行とともに表示したうえで、両者をタプルとして返す構造になっているとしている。

## loop関数: PASSになるまで履歴を積み増しながら再生成する

`loop(task, evaluator_prompt, generator_prompt)`関数は、docstringで「要件を満たすまで生成と評価を続ける(Keep generating and evaluating until requirements are met.)」関数と説明されている中核のループである。まずコンテキストなしで`generate`を呼び出し、その結果を`memory`(過去の試行結果のリスト)と`chain_of_thought`(思考と結果の記録リスト)にそれぞれ追加する。以降はループの中で`evaluate`を呼び出し、評価結果が"PASS"であればその時点の結果と`chain_of_thought`全体を返して終了すると説明している。"PASS"でなければ、それまでの`memory`に蓄積された全試行内容と直近のフィードバックを"Previous attempts:"という見出しのもとに結合した文字列を新たなコンテキストとして`generate`を再度呼び出し、その結果を`memory`と`chain_of_thought`に追加してループを継続する構造になっていると説明している。

この実装は、単に生成をやり直すのではなく、過去の試行履歴とフィードバックの両方をコンテキストとして次の生成に渡し続ける点が特徴であり、評価が"PASS"を返すという明確な終了条件を持つ点で、無限に回り続けることのない反復構造になっていると位置づけられている。generateとevaluateの両関数がそれぞれ独立してdocstringで役割を明記されている点も、生成担当と評価担当を明確に分離するというこのワークフローの設計思想を反映していると読める。

# 活用先

- [../loop-engineering/self-refine-and-evaluator-optimizer.md](../loop-engineering/self-refine-and-evaluator-optimizer.md) — generate／evaluate／loop の3関数構成、thoughts と response・evaluation と feedback をそれぞれ分けて返す設計、"PASS" までコンテキストに全試行履歴とフィードバックを積み増す loop の動作、および有効な場面の4条件（明確な評価基準がある／反復的な改善に価値がある／フィードバックで応答が明確に改善する／LLM自身が有意義なフィードバックを出せる）の根拠
- [../loop-engineering/maker-checker-separation.md](../loop-engineering/maker-checker-separation.md) — 生成と評価を別々のLLM呼び出しに分離するというワークフロー定義（「one LLM call generates a response while another provides evaluation and feedback in a loop」）を、Maker-Checker の実装形態の1つとして引用した根拠

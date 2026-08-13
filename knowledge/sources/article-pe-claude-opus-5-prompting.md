---
type: Article
title: Prompting Claude Opus 5
description: Anthropic公式ドキュメント。Claude Opus 5固有のプロンプト設計パターンを、Opus 4.8との性能差分（agentic coding・コードレビュー・effort設定・vision・長文脈・オフィス業務・マルチエージェント調整）の観点から解説している。
site: Anthropic
published: unknown
retrieved: 2026-08-13
resource: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
origin: "web:claude.com"
source_tier: secondary
tags: [prompt-engineering, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-13T00:00:00+09:00"
---

# 概要

本ドキュメントはAnthropic公式が公開している、Claude Opus 5に固有のプロンプト設計パターンをまとめたガイドである。Claude Opus 5は複雑なagentic codingとエンタープライズ向けの業務に向けて構築されており、特に長時間にわたるエージェント的タスク(long-horizon agentic tasks)に強みを持つと説明している。Claude Opus 4.8向けに書かれた既存のプロンプトに対してもそのままの状態で良好に動作するとしたうえで、以下に紹介するパターンは特にチューニングが必要になりやすい挙動を扱っていると位置づけている。なお、Opus 4.8からの移行時にはthinkingがデフォルトで有効になる点や、thinkingを無効化した場合でもeffortの上限が`high`に制限される点などAPI仕様の変更があるとし、詳細は別途の移行ガイドを参照するよう案内している。

# 要点

## agentic coding

Claude Opus 5がもっとも強みを発揮するのは難易度の高いコーディングタスクだと説明している。具体的には複数ファイルにまたがる機能追加、大規模なリファクタリング、エンドツーエンドの機能実装といった作業である。スタブや未完成のプレースホルダーを残すことなくタスクを完了させる点が特徴で、タスクの完全な仕様を最初にまとめて与え、そのまま実行に委ねる形でもっとも高い性能を発揮するとしている。一方で単発の編集のような簡単なタスクでも良好に動作するが、その場合は旧モデルとの性能差は相対的に小さいとも述べている。

> 引用: 「Claude Opus 5 is built for complex agentic coding and enterprise work, with particular strengths in long-horizon agentic tasks. It performs well out of the box on existing Claude Opus 4.8 prompts.」

## コードレビューとバグ発見

Claude Opus 5は高い精度と再現率を両立させた形でコードレビューを行い、1回のパスで実在するバグを高い割合で発見できると報告している。追加で指摘する内容についても、多くが誤検知(false positive)ではなく実際の問題であるとしている。この精度は低いeffort設定でも維持されるため、レビュー実施時には高速な一次パスと、その後により時間をかけた二次パスという2段構えの運用を後押しするとしている。あわせて、レビュー用プロンプトに「重要度の高い問題だけを報告してほしい」「保守的に判断してほしい」といった指示を含めると、モデルがその指示を文字通り受け取り報告件数が減ってしまう可能性があるため、まずはすべての問題を報告させたうえで、フィルタリングは別のパスとして分離することを勧めている。

## 低いeffort設定での効率性

`low`や`medium`のeffort設定は、より高い設定に比べてごくわずかなトークン数とレイテンシで高い品質の出力を生み出すと説明している。運用上の推奨としては、デフォルトである`high`から始め、自社のeval結果に基づいて調整すること、品質が保たれる範囲では`low`や`medium`をトークンコストと応答速度の主要な制御手段として積極的に使うこと、そして要求の厳しいコーディングやエージェントタスクでは`xhigh`まで引き上げることを挙げている。旧モデルで設定していたeffortのデフォルト値をそのまま引き継いでいる場合は、自社のeval上でeffortの効果を再測定(effort sweep)し直すべきだとも述べている。

## vision

Claude Opus 5はチャート・文書・図表の理解や、UI・フロントエンドのビジュアルな再現において強みを持つと説明している。旧モデル向けにプロンプト側で施していたvisionの回避策については、Claude Opus 5ではもはや不要になっている可能性があるため、再検証を勧めている。vision性能は、モデルが自身の作業を反復的に分析・クロップ・視覚的に検証できるツールを持つ場合にもっとも高く発揮されるとし、thinkingだけに頼るよりもtool useの方が費用対効果の高い手段だとしている。

## 長文脈での作業

Claude Opus 5はデフォルトかつ最大値として100万トークンのコンテキストウィンドウを持つと説明している。この点についてドキュメントは、そのウィンドウ全域にわたって指示追従・ツール呼び出し・推論の一貫性が保たれると述べている。

> 引用: 「Claude Opus 5 has a 1M token context window as both the default and the maximum, and its instruction following, tool calling, and reasoning stay consistent throughout the window.」

## オフィス・文書業務

複雑な複数シート構成で、単純ではない数式を含むスプレッドシートの生成・操作に対応でき、構造がよく整理されたスライドデックの生成も行えると説明している。特定のスタイルやテンプレートに従わせたい場合は、プロンプト側でその情報を明示的に与えるべきだとしている。

## マルチエージェント調整

Claude Opus 5はサブエージェントのチームを適切に調整でき、効果的なwriter-verifierパターンを構築できるほか、エージェント同士が互いの作業を上書きしてしまうケースも少ないと説明している。コストに敏感なワークロードにおいては、サブエージェントへの委譲(delegation)に上限を設けることを推奨し、その具体的な制御方法については別セクション(Controlling subagent spawning)で扱っているとしている。

# 活用先

- [../prompt-engineering/modern-model-prompting.md](../prompt-engineering/modern-model-prompting.md) — コードレビュープロンプトで「重要度の高い問題だけ報告して」と指示すると報告件数が減りうるという過剰指示の実害、vision回避策の再検証の推奨、effort設定の運用指針（highから始めてevalで調整、low/mediumをコストとレイテンシの制御手段に、xhighまで引き上げる場面）、100万トークンのコンテキストウィンドウと全域での一貫性、既存プロンプトがそのまま動作すること、完全な仕様を最初に与えると最高性能を発揮すること、スタイル指定は明示すべきことの根拠
- [../prompt-engineering/loop-engineering.md](../prompt-engineering/loop-engineering.md) — サブエージェントのチーム調整とwriter-verifierパターン（作る役と検証する役の分離）が公式に言及されていること、コスト面からサブエージェントへの委譲に上限を設けるべきという推奨の根拠

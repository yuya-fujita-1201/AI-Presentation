---
type: Article
title: Prompting best practices
description: Anthropic公式ドキュメント。Claudeへの指示は「明確で直接的」であるべきという原則を軸に、文脈の追加・few-shot例の設計・XMLタグによる構造化という4つのプロンプト設計手法を解説している。
site: Anthropic
published: unknown
retrieved: 2026-08-13
resource: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
origin: "web:claude.com"
source_tier: secondary
tags: [prompt-engineering, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-13T00:00:00+09:00"
---

# 概要

本ドキュメントはAnthropic公式が公開しているプロンプトエンジニアリングのベストプラクティス集で、Claude Fable 5やClaude Mythos 5を含む現行の全Claudeモデルに共通して適用できる手法をまとめていると説明している。中心に据えられているのは「明確で直接的な指示」という原則であり、そこに文脈の付与・例示による誘導・XMLタグによる構造化という3つの補助的な技法を組み合わせる構成になっていると述べている。

# 要点

## 明確で直接的な指示（Be clear and direct）

ドキュメントは、Claudeは明確で明示的な指示に対してよく反応するとし、望む出力について具体的に指定するほど結果が改善すると説明している。「期待以上の」振る舞いを引き出したい場合は、曖昧なプロンプトからClaudeが推測することに頼るのではなく、そのように明示的に要求すべきだとしている。

たとえの表現として、Claudeを「自社の慣習やワークフローについて前提知識を持たない、優秀だが新しく入社した社員」と捉えるよう勧めている。何を求めているかを精密に説明するほど、結果が良くなるという考え方である。

> 引用: 「Claude responds well to clear, explicit instructions. Being specific about your desired output can help enhance results. Think of Claude as a brilliant but new employee who lacks context on your norms and workflows.」

自分のプロンプトを検証する方法として、「最小限の文脈しか持たない同僚にそのプロンプトを見せて、その通りに従ってもらう」というゴールデンルールを提示している。その同僚が読んで混乱するようであれば、Claudeも同様に混乱するはずだとしている。具体策としては、望む出力フォーマットや制約を具体的に示すこと、手順の順序や網羅性が重要な場面では番号付きリストや箇条書きで指示を与えることを挙げている。例として、単に「分析ダッシュボードを作って」と指示するより、「できるだけ多くの関連機能とインタラクションを含め、基本を超えたフル機能の実装にしてほしい」と指定する方が効果的だと説明している。

## 文脈の追加でパフォーマンスを高める（Add context to improve performance）

指示の背景や動機、つまり「なぜその挙動が重要なのか」をあわせて伝えることで、Claudeが目標をより正確に理解し、より的確な応答を返せるようになるとドキュメントは述べている。例として、単に「省略記号（ellipsis）を絶対に使うな」と命じるより、「この応答は音声合成エンジンで読み上げられるため、省略記号の発音方法をエンジンが認識できないので使わないでほしい」と理由をあわせて伝える方が効果的だとしている。Claudeはその説明から意図を一般化できるだけの理解力を持っているとまとめている。

## 例を効果的に使う（Use examples effectively）

例の提示は、Claudeの出力フォーマット・トーン・構造を誘導するもっとも信頼できる手段の一つであり、少数の練り込まれた例を与える手法(few-shotあるいはmultishot prompting)によって精度と一貫性が向上すると説明している。

良い例が備えるべき条件として、次の3点を挙げている。1つ目は「関連性(Relevant)」で、実際のユースケースに近い例を選ぶこと。2つ目は「多様性(Diverse)」で、エッジケースを含みつつ、Claudeが意図しないパターンを拾ってしまわない程度にバリエーションを持たせること。3つ目は「構造化(Structured)」で、例を`<example>`タグ(複数の例であれば`<examples>`タグ)で囲み、指示部分と明確に区別できるようにすることである。

具体的な推奨として、3〜5個の例を含めるのが最も効果的だとしている。また、作成した例の関連性や多様性についてClaude自身に評価させたり、初期の例をもとに追加の例を生成させたりする使い方も提案している。

## XMLタグによるプロンプトの構造化（Structure prompts with XML tags）

XMLタグは、指示・文脈・例・変数入力が混在する複雑なプロンプトを曖昧さなく解析するのに役立つと説明している。コンテンツの種類ごとに`<instructions>`・`<context>`・`<input>`のような専用タグで囲むことで、Claudeによる誤解釈を減らせるとしている。

ベストプラクティスとして、プロンプト全体を通して一貫性のある説明的なタグ名を使うこと、コンテンツに自然な階層構造がある場合はタグをネストすることを挙げている。具体例として、複数の文書を扱う場合は`<documents>`タグの中に、それぞれの文書を`<document index="n">`のようなインデックス付きタグで格納する構成を紹介している。

# 活用先

（コンセプト昇華時に追記）

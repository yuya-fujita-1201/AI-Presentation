---
type: Article
title: Introduction to Large Language Models
description: Google for Developers公式。言語モデルがトークンまたはトークン列の確率を推定すること、トークンが単語・サブワード・文字になりうることを説明する入門教材。
site: Google for Developers
published: unknown
retrieved: 2026-08-15
resource: https://developers.google.com/machine-learning/crash-course/llm
origin: "web:developers.google.com"
source_tier: primary
tags: [large-language-models, tokens, probability, official-documentation]
generated:
  by: codex/gpt-5
  at: "2026-08-15T00:21:14+09:00"
---

# 概要

GoogleのMachine Learning Crash Courseに含まれるLLM入門教材。言語モデルを、より長いトークン列の中でトークンまたはトークン列が現れる確率を推定するモデルとして説明している。

# 要点

- トークンは言語モデルが扱う基本単位で、単語、サブワード、1文字になりうる
- 現代の言語モデルでは、意味を持つテキスト断片であるサブワード単位のトークン化が一般的と説明される
- 「続きそうな言葉」という初心者向け説明を、より正確には「続きのトークン候補」と言い換えられる
- トークン列の確率推定は仕組みの一部であり、実際の出力はモデルや周辺の入力条件にも左右される

# 活用先

- [../../decks/ai-eng-01-prompt-engineering/deck.json](../../decks/ai-eng-01-prompt-engineering/deck.json) — 「言葉のかけら（トークン）」を一つずつ生成するという初心者向け説明の根拠

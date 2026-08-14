---
type: Article
title: Compaction
description: Anthropic公式ドキュメント。長時間の会話やタスクにおいて、コンテキストウィンドウの上限に近づくと古いコンテキストを自動的に要約するcompaction機能を解説している。有効化方法・動作の仕組み・パラメータ仕様を扱う。
site: Anthropic
published: unknown
retrieved: 2026-08-14
resource: https://platform.claude.com/docs/en/build-with-claude/compaction
origin: "web:claude.com"
source_tier: secondary
tags: [context-engineering, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-14T00:00:00+09:00"
---

# 概要

本ドキュメントはAnthropic公式が公開しているcompaction機能の解説で、長時間にわたる会話やタスクの実効的なコンテキスト長を、コンテキストウィンドウの上限に近づいた際に古いコンテキストを自動的に要約することで拡張する仕組みだと説明している。会話が長くなるほど応答品質が低下するという課題を踏まえ、アクティブなコンテキストを小さく保つために古い内容を簡潔な要約へ置き換える機能だと位置づけている。現時点ではBeta版であり、ベータヘッダーは`compact-2026-01-12`だとしている。

> 引用: 「Compaction extends the effective context length for long-running conversations and tasks by automatically summarizing older context when approaching the context window limit.」

# 要点

## どのような用途に向いているか

本ドキュメントは、compactionが理想的な用途として次の2つを挙げている。1つ目は、ユーザーが1つのチャットを長期間にわたって使い続けることを想定した、チャットベースの複数ターンにわたる会話。2つ目は、コンテキストウィンドウを超えうるほど多くのフォローアップ作業（多くの場合ツール使用を伴う）を必要とする、タスク指向のプロンプトである。

## 対応モデルとプラットフォーム

対応状況について、ステータスはBeta、ZDR（ゼロデータ保持）はCovered Modelsを除いて対象になると説明している。対応モデルとして、claude-fable-5・claude-mythos-5・claude-mythos-preview・claude-opus-5・claude-opus-4-8・claude-opus-4-7・claude-opus-4-6・claude-sonnet-5・claude-sonnet-4-6を挙げている。対応プラットフォームは、Claude API（Beta）・Claude Platform on AWS（Beta）・Amazon Bedrock（Beta）・Google Cloud（Beta）・Microsoft Foundry（Beta）だとしている。

## Compactionの動作の仕組み

compactionを有効にすると、会話が設定されたトークン閾値に達した時点でClaudeが自動的に会話を要約すると説明している。APIの処理手順として、次の4ステップを示している。1. 入力トークン数が指定されたトリガー閾値に達したことを検出する。2. 現在の会話の要約を生成する。3. その要約を含むcompactionブロックを作成する。4. 圧縮されたコンテキストのまま応答を継続する。

後続のリクエストでは、その応答をmessagesに追加すればよいと説明している。APIはcompactionブロックより前のすべてのコンテンツブロックを自動的に破棄し、要約から会話を継続するとしている。

## 基本的な使い方

compactionを有効化するには、Messages APIリクエストの`context_management.edits`に`compact_20260112`戦略を追加すると説明している。ドキュメントに掲載されているコード例では、`betas=["compact-2026-01-12"]`を指定した上で、`context_management={"edits": [{"type": "compact_20260112"}]}`という形でリクエストに含める使い方が示されている。具体的には次のコード例を掲載している。

```python
response = client.beta.messages.create(
    betas=["compact-2026-01-12"],
    model="claude-opus-5",
    max_tokens=4096,
    messages=messages,
    context_management={"edits": [{"type": "compact_20260112"}]},
)
```

## パラメータ仕様

本ドキュメントは、compactionの設定パラメータとして次の4項目を説明している。

- `type`（string、必須）: `"compact_20260112"`でなければならない。
- `trigger`（object、デフォルトは`{"type": "input_tokens", "value": 150000}`）: compactionを発動させるタイミングを指定する。`input_tokens`が唯一サポートされているトリガー種別であり、`value`は最低でも50,000トークン以上でなければならないとしている。
- `pause_after_compaction`（boolean、デフォルト`false`）: 要約を生成した後に処理を一時停止するかどうかを指定する。
- `instructions`（string、デフォルト`null`）: カスタムの要約プロンプト。指定した場合、デフォルトのプロンプトを完全に置き換えるとしている。

# 活用先

（コンセプト昇華時に追記）

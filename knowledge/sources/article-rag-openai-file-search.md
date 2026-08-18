---
type: Article
title: File search | OpenAI API
description: OpenAIのFile searchツールの公式ガイド。ベクトルストア作成からファイルアップロード、検索カスタマイズ、レート制限までの手順を解説している。
site: OpenAI
published: unknown
retrieved: 2026-08-18
resource: https://developers.openai.com/api/docs/guides/tools-file-search
origin: "web:openai.com"
source_tier: secondary
tags: [rag, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-18T00:00:00+09:00"
---

# 概要

OpenAIは、Responses APIで利用可能なホスト型ツール「File search」について、ベクトルストアの作成とファイルのアップロードだけでモデルの持つ知識を拡張できると説明している。検索の実行自体はOpenAI側が管理するため、開発者がコードで検索処理を実装する必要はなく、モデルがツール使用を判断すると自動的に呼び出されるとしている。

# 要点

## 概要: コード実装不要のホスト型検索ツール

OpenAIは、File searchについて「By creating vector stores and uploading files to them, you can augment the models' inherent knowledge」と説明しており、ベクトルストアを作成しファイルをアップロードするだけでモデル本来の知識を拡張できるとしている。検索の実行はOpenAIが管理するため開発者側でのコード実装は不要で、モデルがツール使用を判断すると自動的に呼び出され、ファイルから情報を取得して出力を返す仕組みだとしている。

## Vector Storeの作成とファイルのアップロード手順

各言語向けのコード例が提供されており、JavaScriptでは`const vectorStore = await openai.vectorStores.create({ name: "knowledge_base" });`という記述でVector Storeを作成できるとしている。Python、Go、Rubyの実装例も掲載されているとしている。ファイルのアップロードは3段階の手順として説明されており、(1) Files APIを通じてURLまたはローカルパスから`purpose: "assistants"`でファイルを登録し、(2) `vectorStores.files.create()`メソッドでVector Storeに関連付け、(3) ファイルが使用可能になるまで、すなわちステータスが`completed`になるまで確認するとしている(原文: 「until the file is ready to be used (i.e., when the status is `completed`)」)。

## 対応ファイル形式と検索カスタマイズ

対応ファイル形式はPDF、DOCX、TXT、JSON、Markdown、各種プログラミング言語ファイルなど23種類以上に及ぶとしている。テキスト形式については「utf-8, utf-16, or ascii」のいずれかのエンコーディングが必須だとしている。検索のカスタマイズについては、`max_num_results`パラメータで検索結果数を制限でき、これが「can help reduce both token usage and latency」という効果を持つとしている。またメタデータの`filters`パラメータで「category」などのキーによる絞り込みが可能だとしている。検索の仕組み自体は「semantic and keyword search」と総称されるのみでクエリ書き換えの内部処理の詳細は文書に明記されていないとしつつ、応答には`"queries": ["What is deep research?"]`のような書き換え後クエリの例が含まれるとしている。

## 料金・レート制限

File searchはResponses API、Chat Completions API、Assistants APIの3つのAPIで利用可能だとしている。レート制限については、Tier 1で毎分100リクエスト(RPM)、Tier 2-3で500RPM、Tier 4-5で1000RPMという上限が設定されているとしている。

> 引用: 「By creating vector stores and uploading files to them, you can augment the models' inherent knowledge.」

# 活用先

- [../rag/build-or-buy.md](../rag/build-or-buy.md) — ホスト型ツールという位置づけと「By creating vector stores and uploading files to them...」の引用、検索実行をOpenAI側が管理し開発者のコード実装が不要であること、`max_num_results`と`filters`という限られた調整範囲、「semantic and keyword search」の総称のみで内部処理が非公開であること、23種類以上の対応形式とエンコーディング要件、Tier別レート制限（100/500/1000 RPM）

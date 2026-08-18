---
type: Article
title: Generate grounded answers with RAG | Agent Search
description: Google Cloud公式ドキュメント。Answer Generation APIによる接地された回答生成を、接地ソース・リクエストパラメータ・動的取得の仕組みから解説
site: Google Cloud
published: unknown
retrieved: 2026-08-18
resource: https://docs.cloud.google.com/generative-ai-app-builder/docs/grounded-gen
origin: "web:google.com"
source_tier: primary
tags: [rag, grounding, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-18T00:00:00+09:00"
---

# 概要

Google Cloudの公式ドキュメント「Generate grounded answers with RAG | Agent Search」は、Agent Searchが提供するAnswer Generation APIについて解説している。同ドキュメントは、Retrieval Augmented Generation（RAG）を「LLMがデータソースから事実を取得し、それを用いて根拠のある回答を生成する」という2段階のプロセスとして定義している。以下、APIの構成要素と主要パラメータ、動的取得の仕組みを、ドキュメントの記述に沿って紹介する。

# 要点

## Answer Generation APIとその構成

同ドキュメントは、`generateGroundedContent`メソッドと`streamGenerateGroundedContent`メソッドという2つのAnswer Generation APIを解説対象としている。サンプルコードで使用されているモデルは「gemini-2.5-flash」であり、実装例として提示されている。

## 3種類の接地ソース(Grounding Sources)

回答を根拠づける接地ソース(Grounding Sources)として、3種類が利用可能だと説明されている。1つ目はGoogle Searchで、「世界知識、広範なトピック、またはインターネット上の最新情報に接続したい場合」に使用するとされる。2つ目はインラインテキストで、最大100個のfact textを直接指定できる。3つ目はAgent Search data storesで、エンタープライズドキュメントを利用する仕組みである。複数の接地ソースを組み合わせる場合は、最大10個まで指定できるとされている。

## リクエストパラメータ

主要なリクエストパラメータとして、`contents`（ユーザープロンプトとモデル応答のrole指定）、`systemInstruction`（モデル動作を制御するプリアンブル）、`groundingSpec`（接地ソースの指定）、`generationSpec`（モデルID・温度・top-P・top-Kの設定）、`languageCode`（デフォルトは"en"）の5つが挙げられている。

## 動的取得（Dynamic Retrieval）としきい値0.7

Google Searchを接地ソースとして使う場合、予測スコア（0〜1の範囲）としきい値を設定できる仕組みが用意されている。ドキュメントは「If the prediction score is greater than or equal to the threshold, the answer is grounded with Google Search.」と説明しており、予測スコアがしきい値以上の場合にのみGoogle Search検索が実行される。デフォルトのしきい値は0.7とされ、必要な場合にのみ外部検索を実行する設計だと読み取れる。

## レスポンス構成とマルチターン対応

APIのレスポンスには、0〜1の範囲のgrounding score、回答を支えるsupportChunks、claim textと支持チャンクを対応付けるgroundingSupport、ユーザープロンプトから構築されたwebSearchQueriesが含まれると説明されている。また、複数ターンの会話を扱う場合には、「in each request you must send all the text exchanged between the user and the model in all the previous turns」という要件が明記されており、過去のやり取り全文を毎回のリクエストに含める必要があるとしている。

> 引用: 「If the prediction score is greater than or equal to the threshold, the answer is grounded with Google Search.」

# 活用先

- [../rag/rag-origin-and-definition.md](../rag/rag-origin-and-definition.md) — 現在のベンダー定義における「事実を取得し、それを用いて根拠のある回答を生成する」2段階プロセスという定義。原典の特定構成と現在の総称的用法との距離を示す根拠
- [../rag/build-or-buy.md](../rag/build-or-buy.md) — 3種類の接地ソース（Google Search／インラインテキスト最大100 fact text／Agent Search data stores）と最大10個の組み合わせ、動的取得の引用としきい値デフォルト0.7、レスポンスのgrounding score・supportChunks・groundingSupport、マルチターンで過去のやり取り全文を毎回送る要件
- [../rag/overview.md](../rag/overview.md) — RAGを「LLMがデータソースから事実を取得し、それを用いて根拠のある回答を生成する」2段階のプロセスと定義するベンダー公式の記述。「取ってくる→それを踏まえて書く」という一言定義の裏づけ

---
type: Article
title: Contextual Retrieval in AI Systems
description: Anthropicが提案するContextual Retrievalの解説記事。チャンクへの文脈付加による検索失敗率の削減手法とコスト構造を紹介している。
site: Anthropic
published: unknown
retrieved: 2026-08-18
resource: https://www.anthropic.com/news/contextual-retrieval
origin: "web:anthropic.com"
source_tier: secondary
tags: [rag, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-18T00:00:00+09:00"
---

# 概要

Anthropicは、従来のRAGがナレッジベースを小さなチャンクに分割して検索する際、個々のチャンクが十分な文脈を欠くという問題を指摘している。同社はこの問題への対処法としてContextual Retrievalという手法を提案し、Contextual EmbeddingsとContextual BM25という2つのサブ技術を組み合わせることで検索精度を改善できるとしている。さらに、複数ドメインでの実験結果として、検索失敗率を段階的に削減できたことも報告している。

# 要点

## 背景: チャンク分割が招く文脈欠落

Anthropicは、従来のRAG手法がナレッジベースを比較的小さなチャンクへ分割してエンコードし取得する仕組みを持つ一方で、個別のチャンクが実用に足る文脈を欠く場合があると説明している。具体例として、SEC提出書類から「The company's revenue grew by 3% over the previous quarter.」というチャンクを取得しても、そのチャンクだけでは対象企業名や該当四半期が不明なため、検索・活用が困難になるとしている。

## 手法: Contextual EmbeddingsとContextual BM25

この課題への対処として提案されているのがContextual Retrievalであり、埋め込み生成および検索インデックス作成の前に、各チャンクへチャンク固有の説明的文脈を追加する手法だとしている。具体的にはContextual EmbeddingsとContextual BM25という2つのサブ技術から構成される。Contextual Embeddingsはチャンクの前に50〜100トークン程度の説明文を追加するもので、前述の元チャンクは文脈化後「This chunk is from an SEC filing on ACME corp's performance in Q2 2023; the previous quarter's revenue was $314 million. The company's revenue grew by 3% over the previous quarter.」という形に変換される例が示されている。Contextual BM25は同様の説明文脈を、語彙マッチング用のインデックスにも追加する技術だとしている。

## 実装: Claude 3 Haikuによる自動生成とプロンプトキャッシング

Anthropicは、手動でのチャンク注釈は非現実的であるため、Claude 3 Haikuに「Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else.」というプロンプトを与え、文脈記述を自動生成する方式を採っているとしている。コスト面については、プロンプトキャッシングを活用することで参照文書をチャンクごとに読み込み直す必要がないと説明しており、「With prompt caching, you don't need to pass in the reference document for every chunk. You simply load the document into the cache once」としている。この仕組みにより、100万ドキュメントトークンあたり$1.02という一度きりの処理コストで実装可能だとしている。

## 性能: 段階的な検索失敗率の削減

Anthropicは、コードベース・小説・ArXivペーパー・科学論文という複数ドメインでの実験結果として、基準となる検索失敗率5.7%が、Contextual Embeddingsの導入のみで35%削減され3.7%になったと報告している。さらにContextual Embeddings と Contextual BM25 を組み合わせると49%削減の2.9%となり、これにリランキングを加えると67%削減の1.9%まで改善したとしている。リランキングは上位150チャンクを取得したのちCohereなどのリランキングモデルに通し、関連性で上位20チャンクへ絞り込む処理だと説明されており、Anthropicは「Reranked Contextual Embedding and Contextual BM25 reduces the top-20-chunk retrieval failure rate by 67%」と結論づけている。推奨設定として、埋め込みモデルはVoyageまたはGeminiが最高性能を示し、取得チャンク数は5や10よりも20の方が効果的だとしている。

> 引用: 「With prompt caching, you don't need to pass in the reference document for every chunk. You simply load the document into the cache once. / Reranked Contextual Embedding and Contextual BM25 reduces the top-20-chunk retrieval failure rate by 67%.」

# 活用先

- [../rag/chunking-and-embedding.md](../rag/chunking-and-embedding.md) — チャンクの文脈欠落問題とSEC提出書類の例、Contextual Embeddings／Contextual BM25の定義、50〜100トークンの説明文前置、Claude 3 Haikuによる自動生成とプロンプトキャッシング（$1.02／100万ドキュメントトークン）、検索失敗率5.7%→3.7%（35%削減）、埋め込みモデルはVoyage／Geminiが最高性能という推奨
- [../rag/retrieval-and-reranking.md](../rag/retrieval-and-reranking.md) — Contextual BM25併用で49%削減（2.9%）、上位150チャンク取得→リランカーで上位20へ絞る処理、リランキング追加で67%削減（1.9%）という数値と結論文、取得チャンク数は20が5や10より効果的という推奨

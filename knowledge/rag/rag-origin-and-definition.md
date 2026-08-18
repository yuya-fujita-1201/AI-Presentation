---
type: Concept
title: RAGの原点と定義——2020年の論文は何を提案したのか
description: RAG（検索拡張生成）という語の出所であるLewis et al. (2020) の提案内容を確認し、現在「RAG」と呼ばれているものとの距離、および原典が保証していない範囲を整理する
tags: [rag, retrieval-augmented-generation, definition, lewis-2020, non-parametric-memory]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-19T00:00:00+09:00"
---

# RAGの原点と定義

RAGという略語は、いまや説明抜きで会話に登場する。しかし現場で「それはRAGなのか」「RAGで解決する問題なのか」を判断しようとすると、人によって指しているものが微妙に違うことに気づく。ずれの原因は、この語が**1本の論文が提案した特定の構成の名前**として生まれ、その後**やり方の総称**へと広がったところにある。まず原点を押さえておくと、以降の議論がぶれない。

## 出所は2020年の1本の論文

RAGという略称・アーキテクチャの起源は、Patrick Lewisらによる論文「Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks」である。2020年5月22日にarXivへ投稿され（ID: 2005.11401）、NeurIPS 2020に採択された（[Lewis 2020 解説](../sources/article-rag-lewis-2020-arxiv.md)）。著者はPatrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhinら12名の共著である。

解説動画側も同じ経緯を紹介しており、2020年にFacebook AI（当時）のPatrick Lewisらのチームが発表した論文でこの概念が提案されたとしている（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

## 提案された構成——2種類の「記憶」を組み合わせる

論文の核となる発想は、性質の異なる2つの記憶を1つのモデルの中で組み合わせることにある。

- **parametric memory（パラメトリックな記憶）**: 事前学習済みのseq2seqトランスフォーマー。モデルの重みそのものに埋め込まれた知識にあたる
- **non-parametric memory（ノンパラメトリックな記憶）**: 事前学習済みニューラルレトリーバーでアクセスする、Wikipediaの密ベクトルインデックス

原文では「the parametric memory is a pre-trained seq2seq transformer, and the non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever」と記述されており、この2種類の記憶をエンドツーエンドで微調整（fine-tune）する仕組みが提案されている（[Lewis 2020 解説](../sources/article-rag-lewis-2020-arxiv.md)）。

論文は単一の方式だけを示したのではなく、検索結果を生成シーケンス全体で共有する方式と、生成の途中で異なる文書を使える方式とを比較している（[Lewis 2020 台帳（CE版）](../sources/paper-ce-rag-lewis-2020.md)）。前者がRAG-Sequence、後者がRAG-Tokenと呼ばれるものにあたる。

具体的な部品としては、検索部分にDense Passage Retriever（DPR）が使われたと動画は紹介している。生成部分については、字幕上は「BR」と聞こえるものの原論文の構成からBART系のモデルを指すと考えられ、正確なモデル名は判別できない（聞き取り）とされている（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

## なぜ2つに分けたのか

分ける動機は、モデルの重みに知識を閉じ込めた場合の不便さにある。台帳は次の2点を挙げている（[Lewis 2020 台帳（CE版）](../sources/paper-ce-rag-lewis-2020.md)）。

1. **更新しやすさ**: 外部知識はモデル全体を再学習するより更新が容易である
2. **根拠の扱い**: 回答の根拠となる文書そのものを扱える

動画は同じ動機を、利用者から見た2つの困りごととして説明している。1つは「知識のカットオフ」で、LLMは学習データに含まれる情報しか知らず、学習データ作成日以降の出来事に答えられないという問題。もう1つは「ハルシネーション」で、事実に基づかないもっともらしい情報を生成してしまう問題である。この2つを解決するため、内部知識に頼るだけでなく外部の信頼できる情報源を都度参照するというアイデアが生まれ、それがRAGの基本的な考え方だと説明している（聞き取り）（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

## 何が示されたのか

著者らは、3つのオープンドメイン質問応答タスクにおいて当時の最先端（state-of-the-art）を達成したと報告している。加えて言語生成タスクでも、アブストラクトに「RAG models generate more specific, diverse and factual language than a state-of-the-art parametric-only seq2seq baseline」と明記される通り、パラメトリック単体モデルのベースラインより具体的・多様・事実に忠実な出力を生成したと結論づけている（[Lewis 2020 解説](../sources/article-rag-lewis-2020-arxiv.md)）。

## 現在の「RAG」との距離

ここで注意したいのが、今日ベンダーのドキュメントに書かれている定義には、DPRもWikipedia索引もseq2seqも出てこないという点である。たとえばGoogle Cloudの公式ドキュメントは、Retrieval Augmented Generation（RAG）を「LLMがデータソースから事実を取得し、それを用いて根拠のある回答を生成する」という**2段階のプロセス**として定義している（[Google Cloud: Generate grounded answers with RAG](../sources/article-rag-google-cloud-grounded-gen.md)）。

つまり現在のRAGは、特定のモデル構成の名前ではなく「取得してから生成する」という手順の名前として使われている。2020年の論文はその原型を示したものであり、両者は地続きだが同一ではない。この距離を意識しないまま論文の実験結果を自社システムの根拠に使うと、次節の落とし穴にはまる。

## 原典が保証していないこと

台帳は、この論文を引用する際の留保を明示している（[Lewis 2020 台帳（CE版）](../sources/paper-ce-rag-lewis-2020.md)）。実務ではここが最も効く。

- 論文のRAGは、**特定のモデル構成・検索器・Wikipedia索引・当時の知識集約型課題**を対象とする。現在広くRAGと呼ばれるすべての実装を、同じ性能で裏付けるものではない
- 検索は関連情報を返す可能性を高めるが、**取得漏れ・誤取得・古い文書・矛盾・権限違反を自動で解決しない**
- 論文中の「non-parametric memory」は検索可能な外部索引を指す技術用語であり、利用者の好みや過去の会話を保存する**会話メモリと同一ではない**

3点目は特に混同されやすい。「RAGを入れたのでAIが自社のことを覚えてくれる」という言い方は、少なくとも原典の用語法とは合わない。RAGは取得の方式であって、情報の永続化・再利用（メモリ）そのものではない。この切り分けは[RAGと隣接概念](rag-and-neighbors.md)で改めて扱う。

## この節の要点

- RAGの出所はLewis et al. (2020)、arXiv 2005.11401 / NeurIPS 2020である
- 提案の核はparametric memory（重みの知識）とnon-parametric memory（外部の密ベクトル索引）の組み合わせである
- 分ける動機は「更新しやすさ」と「根拠を扱えること」の2点である
- 現在の「RAG」は手順の総称へ広がっており、原典の実験結果がそのまま自社実装を保証するわけではない

次は、この「取得してから生成する」手順が実際どのような工程に分かれるかを[RAGのパイプライン](rag-pipeline-stages.md)で見ていく。

# Citations

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks（arXiv解説台帳）](../sources/article-rag-lewis-2020-arxiv.md) — 書誌情報（著者・arXiv ID・NeurIPS 2020採択）、parametric/non-parametric memoryの原文記述、3タスクでのSOTA達成と「more specific, diverse and factual」という主張の根拠
- [Lewis 2020（コンテキストエンジニアリング版台帳）](../sources/paper-ce-rag-lewis-2020.md) — RAG-Sequence／RAG-Tokenにあたる2方式の比較、外部知識の更新容易性と根拠追跡という動機、および「原典が保証していないこと」（適用範囲の限定、検索が自動解決しない事柄、non-parametric memoryと会話メモリの区別）の根拠
- [検索拡張生成(RAG)とは？LLMの嘘と知識不足を克服する仕組みを歴史から最新技術まで解説](../sources/video-rag-history-mechanism-limits.md) — 2020年Facebook AI（当時）のPatrick Lewisらによる提案という経緯、知識のカットオフとハルシネーションという2つの動機（auto字幕・帰属付き）、検索部分のDPRと生成部分のモデル名に関する聞き取りの不確実性
- [Generate grounded answers with RAG | Agent Search（Google Cloud公式）](../sources/article-rag-google-cloud-grounded-gen.md) — 現在のベンダー定義における「事実を取得し、それを用いて根拠のある回答を生成する」2段階プロセスという定義の根拠

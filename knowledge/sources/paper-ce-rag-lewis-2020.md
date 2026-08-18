---
type: Paper
title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
description: "生成モデルのパラメトリックな知識と、外部インデックスから検索する非パラメトリックな知識を組み合わせるRAGを提案したLewisらの代表的研究。外部知識の更新可能性と根拠追跡の課題に取り組む。"
source_id: CE-S06
site: arXiv
published: "2020-05-22"
retrieved: "2026-08-14"
resource: "https://arxiv.org/abs/2005.11401"
origin: "web:arxiv.org"
source_tier: primary
tags: [rag, retrieval, knowledge, grounding, non-parametric-memory]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Patrick Lewisらが、事前学習済み生成モデルと外部文書検索を統合するRetrieval-Augmented Generationを提案した研究。論文の構成では、生成モデルに保持されたパラメトリックな知識に対し、Wikipediaの密ベクトル索引を検索して得る文章を非パラメトリックな知識として組み合わせ、知識集約型の自然言語処理課題を評価した。

# 要点

- モデルの重みに埋め込まれた知識だけに依存せず、外部索引から関連文書を取得して生成時の条件に加える構成を示した。
- 外部知識はモデル全体を再学習するより更新しやすく、回答の根拠となる文書を扱えるという動機がある。
- 検索結果を生成シーケンス全体で共有する方式と、生成中に異なる文書を使える方式を比較した。
- RAGは「検索してきた情報をコンテキストへ供給する」代表的な仕組みであり、コンテキストエンジニアリングにおける情報取得経路の一つと位置づけられる。

# 適用範囲と留保

- 論文のRAGは特定のモデル構成、検索器、Wikipedia索引、当時の知識集約型課題を対象とする。現在広くRAGと呼ばれるすべての実装を同じ性能で裏付けるものではない。
- 検索は関連情報を返す可能性を高めるが、取得漏れ、誤取得、古い文書、矛盾、権限違反を自動で解決しない。
- 論文中の「non-parametric memory」は検索可能な外部索引を指す技術用語であり、利用者の好みや過去の会話を保存する会話メモリと同一ではない。
- RAGは取得方式、圧縮は履歴の縮約、メモリは情報の永続化・再利用、プロンプトキャッシュは計算再利用であり、目的を混同しない。

# 原文の根拠箇所

- **parametric / non-parametric memoryの組み合わせ**: `Abstract`
- **RAG-Sequence / RAG-Token**: 論文本体のモデル定義節
- **固定版**: arXiv `2005.11401`、NeurIPS 2020

# デッキで安全に使える表現

- 「RAGは、必要そうな外部資料を検索し、その結果を今回の判断材料としてAIへ渡す仕組みです。」
- 「検索できることと、答えるのに十分な根拠がそろうことは別です。」
- 「RAGはコンテキストを集める経路の一つであり、メモリやキャッシュの別名ではありません。」

# 活用先

- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — RAGの原型、外部索引と生成モデルの組み合わせ
- [../context-engineering/context-components.md](../context-engineering/context-components.md) — RAG、会話メモリ、圧縮、キャッシュの区別
- [../rag/rag-origin-and-definition.md](../rag/rag-origin-and-definition.md) — RAG-Sequence／RAG-Tokenにあたる2方式の比較、外部知識の更新容易性と根拠追跡という動機、および「原典が保証していないこと」（適用範囲の限定／検索が自動解決しない事柄／non-parametric memoryと会話メモリの区別）の根拠
- [../rag/rag-and-neighbors.md](../rag/rag-and-neighbors.md) — 外部知識がモデル全体の再学習より更新しやすいという動機、「non-parametric memory」が検索可能な外部索引であって会話メモリではないという区別、RAG（取得）／圧縮（履歴の縮約）／メモリ（永続化）／プロンプトキャッシュ（計算再利用）の目的を混同しないという整理
- [../rag/overview.md](../rag/overview.md) — 外部知識がモデル全体の再学習より更新しやすく、回答の根拠となる文書を扱えるという原典側の動機。「なぜ必要とされたのか」を後付け解釈でなく原典に接続する根拠

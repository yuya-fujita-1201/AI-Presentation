# rag — RAG（検索拡張生成）についてのナレッジ

社内の資料をAIに読ませて答えさせる仕組み「RAG（Retrieval-Augmented Generation、検索拡張生成）」についてまとめたディレクトリ。原典論文（Lewis et al. 2020）とarXiv論文（Barnett et al. 2024 / Es et al. 2023）、Anthropic・OpenAI・Google Cloudの公式ドキュメント、日本語の実務記事、YouTube解説動画を情報源とする（[../sources/index.md](../sources/index.md) の「記事（RAG）」「動画（RAG）」節を参照）。

想定読者は、チャット型AIを使ったことはあるが、社内システムとしてのRAGは未経験という段階の人。新入社員からSI/IT分野のコンサル・SE・エンジニアまでを対象に、用語の意味から設計・運用・導入判断までを扱う。

## 内容

入口は [overview.md](./overview.md)（一言定義・なぜ必要か・よくある5つの誤解・バンドルの地図）。以下は overview.md の順序表と同じ並びで、各ファイルの見出し語だけを挙げる。内容説明と読む順番の根拠は overview.md 側で一元管理しており、ここでは重複させない。

1. [rag-origin-and-definition.md](./rag-origin-and-definition.md) — RAGの原点と定義
2. [rag-pipeline-stages.md](./rag-pipeline-stages.md) — パイプラインの段階
3. [chunking-and-embedding.md](./chunking-and-embedding.md) — チャンク分割と埋め込み
4. [retrieval-and-reranking.md](./retrieval-and-reranking.md) — 検索とリランキング
5. [failure-modes.md](./failure-modes.md) — どこで壊れるか
6. [evaluation.md](./evaluation.md) — できているかをどう測るか
7. [build-or-buy.md](./build-or-buy.md) — 作るか借りるか
8. [governance-and-adoption.md](./governance-and-adoption.md) — 入れる前と入れた後
9. [rag-and-neighbors.md](./rag-and-neighbors.md) — 隣接概念との切り分け

## 読む順番

[overview.md](./overview.md) の「このバンドルの地図」節にある9本の順序表と「読む順番の提案」（全員／作る側／選ぶ側／混乱を整理したい人の4パターン）に従うこと。読む順番はこのファイルではなく overview.md 側で一元管理する。

## 関連するディレクトリ

- [../context-engineering/](../context-engineering/index.md) — RAGをコンテキスト設計の一手段として位置づける視点。特に [retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) は検索・記憶・圧縮・キャッシュの役割差を扱う
- [../graph-engineering/](../graph-engineering/index.md) — 検索をエージェントに任せる構成の損益分岐。特に [multi-agent-break-even.md](../graph-engineering/multi-agent-break-even.md)

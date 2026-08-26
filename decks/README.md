# decks — 現行デッキ一覧

トップ階層には、現在使う正本だけを表示順で置きます。フォルダ名先頭の2桁が並び順です。

## 正本

| 順番 | フォルダ | タイトル | 枚数 | 生成物ID |
|---:|---|---|---:|---|
| 00 | [`00-series-overview/`](00-series-overview/) | AIエンジニアリング超入門（シリーズ全体紹介） | 21 | `ai-eng-00-series-overview` |
| 01 | [`01-prompt-engineering/`](01-prompt-engineering/) | プロンプトエンジニアリング超入門 | 53 | `ai-eng-01-prompt-engineering` |
| 02 | [`02-context-engineering/`](02-context-engineering/) | コンテキストエンジニアリング超入門 | 72 | `ai-eng-02-context-engineering-v2` |
| 03 | [`03-harness-engineering/`](03-harness-engineering/) | ハーネスエンジニアリング超入門 | 66 | `ai-eng-03-harness-engineering` |
| 04 | [`04-loop-engineering/`](04-loop-engineering/) | ループエンジニアリング超入門 | 55 | `ai-eng-04-loop-engineering` |
| 05 | [`05-graph-engineering/`](05-graph-engineering/) | グラフエンジニアリング超入門 | 48 | `ai-eng-05-graph-engineering` |
| 06 | [`06-rag/`](06-rag/) | RAG（検索拡張生成）とは何か | 35 | `ai-topics-01-rag` |
| 07 | [`07-okf-visual-guide/`](07-okf-visual-guide/) | OKFビジュアルガイド v2 | 35 | `okf-visual-v2` |

`deck.json` の `meta.id` はHTML/PPTXの生成物名として使うため、フォルダ整理では変更しません。

## アーカイブ

- OKF旧版: [`_archive/okf/`](_archive/okf/)
- グラフエンジニアリング旧版: [`_archive/graph-engineering/`](_archive/graph-engineering/)
- AI Engineering 01旧版・不採用版: [`_archive/ai-eng-01/`](_archive/ai-eng-01/)
- Context Engineering旧版: [`_archive/ai-eng-02-context-engineering/`](_archive/ai-eng-02-context-engineering/)

## 命名ルール

- トップ階層: 現在使う正本だけ。`NN-slug` 形式で表示順を固定する
- `_archive/`: 旧版、比較用、採用しなかった版。正本として編集しない
- `.backups/`: 作業前のローカル全量バックアップ
- 正本の追加・順序変更時は、この一覧とリポジトリ内の参照パスを同時に更新する

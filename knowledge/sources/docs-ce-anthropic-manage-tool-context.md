---
type: Documentation
title: "Manage tool context"
description: "Anthropic公式ドキュメント。ツール定義とtool_resultがコンテキストを消費する問題に対し、ツール検索、プログラム的ツール呼び出し、プロンプトキャッシュ、コンテキスト編集を異なる圧力への対策として整理している。"
source_id: CE-S09
site: Claude Platform Docs
published: unknown
retrieved: "2026-08-14"
resource: "https://platform.claude.com/docs/en/agents-and-tools/tool-use/manage-tool-context"
origin: "web:platform.claude.com"
source_tier: primary
tags: [tools, context-engineering, tool-search, context-editing, prompt-caching, agents]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

ツールを使うエージェントで、ツール定義と蓄積した実行結果が作業コンテキストを圧迫する問題を整理したClaude Platformの公式ガイド。どの情報が膨らんでいるかに応じて、ツール検索、プログラム的ツール呼び出し、プロンプトキャッシュ、コンテキスト編集を使い分ける。

# 要点

- ツール定義と過去のtool_resultは、会話本文と同様にコンテキストウィンドウを使う。ツールが多い、または実行結果が積み上がる長時間タスクでは別々に対処する。
- ツール検索は、すべての定義を最初から渡さず、必要なツールの定義をオンデマンドで見つける。
- プログラム的ツール呼び出しは、一連の処理をまとめて実行し、中間結果を会話履歴へ何度も戻さない。
- コンテキスト編集は、役目を終えた古いツール結果を履歴から外し、次の呼び出しへ残す情報を減らす。
- プロンプトキャッシュは、安定したツール定義などの再計算を減らすが、モデルへ渡るトークン数そのものを減らす方式ではない。

# 適用範囲と留保

- Claude Platformの機能分類であり、対応機能、名称、利用条件は他社製品やモデルで異なる。
- ツール検索は初期コンテキストを小さくできる一方、検索の追加ステップとツール選択失敗の可能性がある。
- 古いtool_resultの削除は、監査記録や再現性のための原本削除を意味しない。モデルへ渡すビューから外すことと、保存系から消すことを分ける。
- プロンプトキャッシュはコスト・待ち時間の最適化であり、メモリ、RAG、圧縮、コンテキスト編集の代替ではない。

# 原文の根拠箇所

- **4手段の全体像**: `The four approaches`
- **定義の必要時ロード**: `Tool search`
- **中間結果を履歴へ戻さない処理**: `Programmatic tool calling`
- **計算再利用**: `Prompt caching`
- **古いtool resultを作業文脈から外す操作**: `Context editing`

# デッキで安全に使える表現

- 「ツールは使うたびだけでなく、定義を見せているだけでもコンテキストを使います。」
- 「定義が多いなら検索、途中結果が多いなら集約、古い結果が残るなら編集、同じ前半を繰り返すならキャッシュ、と原因別に直します。」
- 「履歴から外すこと、保存記録を消すこと、計算を再利用することは別の操作です。」

# 活用先

- [../context-engineering/context-components.md](../context-engineering/context-components.md) — ツール定義と結果を含む作業コンテキスト
- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — ツール検索、結果集約、コンテキスト編集、キャッシュの役割差
- [../context-engineering/long-horizon-and-tools.md](../context-engineering/long-horizon-and-tools.md) — 長時間ツール利用の圧力診断

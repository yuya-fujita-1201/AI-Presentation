---
type: Article
title: "Architecting efficient context-aware multi-agent framework for production"
description: "Google Agent Development Kitの設計者が、コンテキストを状態から毎回生成するcompiled viewとして扱うアーキテクチャを解説。作業コンテキスト、セッション、メモリ、アーティファクトを分離し、選択・変換・注入・圧縮・スコープ制御を明示する。"
source_id: CE-S03
site: Google Developers Blog
published: "2025-12-04"
retrieved: "2026-08-14"
resource: "https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/"
origin: "web:developers.googleblog.com"
source_tier: primary
tags: [context-engineering, google-adk, agents, session, memory, artifacts, compaction]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Google ADKのコンテキスト設計を、単なる文字列連結ではなく「状態から今回のモデル呼び出し用表示を組み立てるコンパイル」として説明した公式記事。永続的な情報源と、モデルがその一回で見る作業コンテキストを分離し、明示的な処理パイプラインを通じて必要な情報だけを投影する考え方を示している。

# 要点

- セッション、メモリ、アーティファクトを情報源、フローとプロセッサを変換パイプライン、作業コンテキストをモデルへ渡す生成物として整理する。
- 作業コンテキストは呼び出しごとに再構築される一時的なビューであり、保存された全状態そのものではない。
- セッションはやり取りやツール実行を構造化イベントとして保持し、選択・変換・注入を経て必要部分だけが履歴として渡される。
- 大きなファイルやログはアーティファクトとして外部化し、名前や要約を手掛かりに必要時だけ読み込む。メモリはセッションを越える検索可能な知識として別に扱う。
- マルチエージェントでは、親の全履歴を無条件に渡さず、相手の役割に必要な情報だけをスコープする。誰の発話・行動かを再表現し、実行主体の誤認も避ける。

# 適用範囲と留保

- Google ADKという具体的なフレームワークの設計であり、すべてのエージェント基盤が同じ用語や内部構造を持つわけではない。
- 「compiled view」は理解のための設計モデルであり、言語モデル内部がコンパイラとして動くという主張ではない。
- セッション、メモリ、アーティファクト、作業コンテキストは役割が異なる。保存場所とモデルが現在見ている内容を同一視しない。
- 圧縮は情報を短くして次のビューを変えるが、プロンプトキャッシュは主に同じ接頭部の再計算を減らす最適化であり、作業コンテキスト自体を小さくするとは限らない。

# 原文の根拠箇所

- **作業文脈を一時ビューとして組み立てる考え方**: `The design thesis: context as a compiled view`
- **session・memory・artifactの役割**: `Structure: The tiered model`
- **大きな成果物の外部化**: `Artifacts: externalizing large state`
- **必要時に検索する長期知識**: `Memory: long-term knowledge, retrieved on demand`

# デッキで安全に使える表現

- 「保存してある全情報と、AIが今見る情報は分けて設計できます。」
- 「作業コンテキストは、セッション・メモリ・ファイルなどから今回必要な部分を組み立てた一時ビューです。」
- 「マルチエージェントでは、引き継ぎ量だけでなく、誰が何をした情報かまで整えて渡します。」

# 活用先

- [../context-engineering/context-components.md](../context-engineering/context-components.md) — 情報源から作業コンテキストを組み立てるcompiled view
- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — セッション、メモリ、アーティファクト、圧縮、キャッシュの役割差
- [../context-engineering/long-horizon-and-tools.md](../context-engineering/long-horizon-and-tools.md) — マルチエージェントのスコープと発話主体の再表現

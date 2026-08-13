---
type: Course
title: "Context Engineering for AI Agents"
description: "Microsoft公式のAI Agents for Beginners教材。コンテキストを指示・知識・ツール・会話履歴・利用者設定に分け、write・select・compress・isolateの戦略と代表的な失敗モードを初心者向けに整理している。"
source_id: CE-S02
site: Microsoft
published: unknown
retrieved: "2026-08-14"
resource: "https://github.com/microsoft/ai-agents-for-beginners/blob/15ad10ca60577b75199c1ba828887ab7e66bac87/12-context-engineering/README.md"
origin: "web:github.com/microsoft"
source_tier: primary
tags: [context-engineering, agents, education, context-failures, compression, isolation]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Microsoftが公開するAI Agents for Beginnersのコンテキストエンジニアリング章。エージェントが次の一歩を実行するために必要な情報を管理する実務として定義し、単発の静的な指示に焦点を置くプロンプトエンジニアリングと、時間とともに変化する情報集合を管理するコンテキストエンジニアリングを対比している。

# 要点

- コンテキストの種類として、指示、知識、ツール定義と結果、会話履歴、利用者の設定・好みを挙げている。
- 設計手順は、完了状態を定義し、必要な情報の所在を地図化し、取得経路をパイプラインとして作る流れで説明される。
- 実装戦略として、スクラッチパッド、セッションをまたぐメモリ、要約・トリミングによる圧縮、マルチエージェント分離、サンドボックス、実行時状態を扱う。
- 失敗モードを、誤情報が残るpoisoning、情報過多によるdistraction、不要な選択肢によるconfusion、矛盾する情報のclashとして整理している。
- デバッグ時は「多すぎたか、違う情報だったか、必要な情報が欠けたか」を次のモデル呼び出し単位で確認する観点を示している。

# 適用範囲と留保

- 初学者向け教材の分類であり、用語や失敗モードが業界共通の唯一の標準という意味ではない。
- リポジトリは継続更新されるため、公開日と内容は固定版ではない。利用時は取得日と現在の内容を区別する。
- 教材中の製品実装例や個別の推奨値は、モデルやツールの更新で変わり得る。デッキでは固定数値を一般化しない。
- スクラッチパッド、メモリ、RAG、圧縮、キャッシュは情報を扱う目的と寿命が違うため、まとめて「記憶」と呼ばない。

# 原文の根拠箇所

- **定義とPEとの違い**: `What is Context Engineering?` > `Prompt Engineering vs Context Engineering`
- **構成要素**: `What is Context Engineering?` > `Types of Context`
- **計画と実装戦略**: `Strategies for Effective Context Engineering` > `Planning Strategies` / `Practical Strategies`
- **失敗診断**: `Common Context Failures`
- **固定版**: Git commit `15ad10ca60577b75199c1ba828887ab7e66bac87` のREADME

# デッキで安全に使える表現

- 「コンテキストは、指示だけでなく、知識、ツール、履歴、利用者情報まで含む『次の判断材料』です。」
- 「最初に完了状態を決め、必要な材料を洗い出し、どこからいつ持ってくるかを設計します。」
- 「失敗を『多すぎる・違う・欠けている・食い違う』に分けると、直す場所を見つけやすくなります。」

# 活用先

- [../context-engineering/context-components.md](../context-engineering/context-components.md) — コンテキストの種類とプロンプトとの違い
- [../context-engineering/practical-context-packs.md](../context-engineering/practical-context-packs.md) — 完了状態、情報地図、取得パイプライン
- [../context-engineering/selection-and-sufficiency.md](../context-engineering/selection-and-sufficiency.md) — poisoning、distraction、confusion、clashの診断

---
type: Documentation
title: "Memory tool"
description: "Anthropic公式のMemory toolドキュメント。アプリケーション側の保存領域へファイル操作を実装し、会話をまたいで情報を保存・必要時に再取得する仕組みと、その責任境界を説明している。"
source_id: CE-S08
site: Claude Platform Docs
published: unknown
retrieved: "2026-08-14"
resource: "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool"
origin: "web:platform.claude.com"
source_tier: primary
tags: [memory, agents, persistence, just-in-time-context, security]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

Claudeに会話をまたぐ情報の保存・取得を行わせるMemory toolの公式仕様。Claudeがファイル操作を要求し、実際の保存と読み書きは利用者のアプリケーションが実行するクライアント側の仕組みである。すべてを作業コンテキストへ常駐させず、必要なファイルだけをその都度読むJust-in-Time取得として説明している。

# 要点

- エージェントはメモリ用ディレクトリ内のファイルを作成、参照、更新、削除し、セッションをまたいで知識を蓄積できる。
- メモリの実体はAnthropic側に自動保存される前提ではなく、アプリケーションが管理するストレージに置かれる。アプリケーションが同じ保存領域を提供したときに再利用できる。
- 全メモリを毎回投入せず、ディレクトリや関連ファイルを確認して必要な内容を読むため、作業コンテキストを現在の課題へ集中させやすい。
- 代表用途は、プロジェクト状態の継続、過去の判断・フィードバックの再利用、長期的な知識ベースの構築である。
- 実装者は利用者ごとの分離、パス制限、アクセス制御、削除、内容検証を担当する。

# 適用範囲と留保

- これはClaude Platformの具体的なツール仕様であり、他製品の「メモリ」が同じ保存場所・自動動作・責任分界を持つとは限らない。
- メモリに保存された情報は自動的に正しい・最新・安全になるわけではない。出典、更新日、所有者、検証状態、削除方針が必要である。
- メモリは情報をウィンドウ外へ永続化し再取得する仕組み。RAGは外部コーパスから関連情報を検索する構成、圧縮は履歴を要約する操作、プロンプトキャッシュは計算再利用であり別物である。
- 保存対象には個人情報や機密が含まれ得る。製品のデータ処理条件だけでなく、自社ストレージとアクセス権も確認する。

# 原文の根拠箇所

- **ウィンドウ外への保存と再取得**: `Memory tool` / `How it works`
- **利用者分離・機密情報・パストラバーサル**: `Security considerations`
- **圧縮との役割差**: `Using with compaction`

# デッキで安全に使える表現

- 「メモリは、情報をいったん外に保存し、後の仕事で必要なときに取り戻す仕組みです。」
- 「覚えさせる前に、誰の情報か、いつまで使うか、正しいか、消せるかを設計します。」
- 「メモリは作業コンテキストそのものではありません。保存された情報のうち、今回読み込んだ部分だけが判断材料になります。」

# 活用先

- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — 永続メモリと作業コンテキストの区別
- [../context-engineering/security-and-trust-boundaries.md](../context-engineering/security-and-trust-boundaries.md) — 保存責任、利用者分離、検証、削除

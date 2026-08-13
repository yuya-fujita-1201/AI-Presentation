---
type: Documentation
title: "Prompt caching"
description: "OpenAI API公式のプロンプトキャッシュガイド。同一のプロンプト接頭部を再利用して待ち時間とコストを抑える仕組み、安定部分を前に置く設計、キャッシュが出力生成や記憶を代替しないことを説明している。"
source_id: CE-S10
site: OpenAI Developers
published: unknown
retrieved: "2026-08-14"
resource: "https://developers.openai.com/api/docs/guides/prompt-caching"
origin: "web:developers.openai.com"
source_tier: primary
tags: [prompt-caching, context-engineering, latency, cost, prefix, api]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

繰り返し現れるシステム指示、共通資料、例、ツール定義などのプロンプト接頭部について、以前の処理を再利用するOpenAI APIの公式ガイド。キャッシュが一致しやすいよう、変わらない内容を前方、利用者入力や時刻など変わる内容を後方へ置く構造を勧めている。

# 要点

- キャッシュ再利用は、プロンプトの先頭から一致する部分を基準にする。前半の変更は、その後ろにある共通内容の再利用も妨げ得る。
- 指示、共通資料、例、ツール定義、スキーマなど安定した内容を前にまとめ、リクエスト固有の内容を後に置くと再利用しやすい。
- キャッシュヒットは処理済み入力の再利用であり、モデルはその入力を基に新しい応答を生成する。キャッシュによって同じ出力が保証されるわけではない。
- キャッシュ状態と利用状況はAPIの計測項目で観測し、実際に再利用できているかを確認する。
- 対応モデル、保持条件、課金、最小条件などは変化し得るため、実装時点の公式ガイドで確認する。

# 適用範囲と留保

- これはOpenAI APIの現在の仕様であり、ChatGPTの会話メモリや他社のキャッシュ仕様と同一ではない。
- プロンプトキャッシュは同じ入力部分の計算を再利用する最適化で、作業コンテキストから情報を除く、長期記憶へ保存する、外部資料を検索する仕組みではない。
- キャッシュヒットは入力一致、利用可能状態、ルーティングなどに依存し、常に保証されるものではない。
- 対応モデル、価格、保持時間、データ処理条件を固定値として教材へ一般化しない。取得日を示し、導入時に再確認する。

# 原文の根拠箇所

- **prefix一致と計算再利用**: `Prompt caching fundamentals`
- **安定部分を前、可変部分を後ろへ置く設計**: `Caching best practices`
- **変動する対応条件**: 同ページの対象モデル・保持・利用条件（取得日 `2026-08-14`）

# デッキで安全に使える表現

- 「プロンプトキャッシュは、同じ前半をもう一度処理するときの計算を再利用する仕組みです。」
- 「安定した指示や共通資料を前、毎回変わる入力を後ろに置くと再利用しやすくなります。」
- 「キャッシュは記憶ではなく、情報量を減らす圧縮でもありません。主目的は待ち時間とコストの最適化です。」

# 活用先

- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — キャッシュ、メモリ、圧縮、RAGの区別
- [../context-engineering/long-horizon-and-tools.md](../context-engineering/long-horizon-and-tools.md) — 安定接頭部と可変後半の設計

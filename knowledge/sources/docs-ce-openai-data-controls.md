---
type: Documentation
title: "Data controls in the OpenAI platform"
description: "OpenAI API公式のデータ制御ドキュメント。学習利用、abuse monitoring、application state、Zero Data Retention等を分け、エンドポイント・機能・組織設定・外部サービスごとに保存条件が異なることを示す。"
source_id: CE-S12
site: OpenAI Developers
published: unknown
retrieved: "2026-08-14"
resource: "https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint"
origin: "web:developers.openai.com"
source_tier: primary
tags: [data-controls, privacy, retention, governance, api, third-party-tools]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

OpenAI APIへ送るデータの利用と保存を、モデル学習への利用、abuse monitoringのログ、機能提供のためのapplication stateに分けて説明する公式ドキュメント。さらに、組織・プロジェクト単位のデータ制御、エンドポイントごとの違い、外部MCPやネットワーク接続先の別ポリシーを示している。

# 要点

- 公式ドキュメントは、APIデータについて、明示的な共有を選ばない限りモデル学習へ利用しないという現在の方針を示している。
- 「学習に使わない」ことと「一切保存されない」ことは同じではない。安全監視ログと、会話・ファイル・検索など機能を提供するための状態を分けて確認する。
- Zero Data RetentionやModified Abuse Monitoringは、利用資格、承認、エンドポイント、機能ごとに適用可能性や挙動が異なる。
- 同じAPIでも、store設定、会話状態、ファイル、ベクトルストア、バックグラウンド処理、キャッシュなど、使う機能によってapplication stateの扱いが変わる。
- MCPサーバーやネットワーク経由の第三者サービスへ送られたデータは、その第三者の保存・利用ポリシーにも従う。

# 適用範囲と留保

- これは2026-08-14取得時点のOpenAI API公式文書である。保持条件、対象機能、申請要件、地域対応は更新され得る。
- APIとChatGPTの個人向け・法人向け製品を一括りにしない。利用中の製品、契約、組織設定、エンドポイントを特定して確認する。
- 「ZDRなら何も残らない」と一般化しない。対象外機能、application state、第三者サービス、利用者側のログや保存領域を別に監査する。
- 教材では固定の保持日数や製品別一覧を暗記項目にせず、公式表を導入時に確認する手順を教える。

# 原文の根拠箇所

- **保存データの種類**: `Types of data stored with the OpenAI API`
- **安全監視ログの扱い**: `Data retention controls for abuse monitoring`
- **機能・endpointごとの差**: `Storage requirements and retention controls per endpoint`
- **地域条件**: `Data residency controls`
- **第三者接続**: 同ページのMCP・third-party servicesに関する節（取得日 `2026-08-14`）

# デッキで安全に使える表現

- 「『学習に使われない』と『保存されない』は別の確認項目です。」
- 「機密情報を入れる前に、製品、契約、組織設定、使う機能、外部連携先を特定して現在のポリシーを確認します。」
- 「AI側の設定だけでなく、RAGの文書庫、メモリ、ログ、MCPなど自分たちが管理する保存先も対象です。」

# 活用先

- [../context-engineering/security-and-trust-boundaries.md](../context-engineering/security-and-trust-boundaries.md) — 学習利用、監視ログ、application state、外部連携を分ける確認手順
- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — メモリ・キャッシュ・会話状態の保存境界

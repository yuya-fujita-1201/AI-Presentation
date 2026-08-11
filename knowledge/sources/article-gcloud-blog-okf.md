---
type: Article
title: How the Open Knowledge Format can improve data sharing（Google Cloud 公式ブログ）
description: OKF の発表記事（一次情報）。コンテキスト断片化の課題、設計 3 原則、v0.1 の構造、リファレンス実装を解説
resource: https://cloud.google.com/blog/ja/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/
tags: [okf, google-cloud, primary-source]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T14:00:00+09:00"
---

# 要点

- OKF は「LLM-wiki パターンをポータブルで相互運用可能にするオープン仕様」。ベンダー非依存
- 課題認識: 組織の知識がカタログ・Wiki・コード・暗黙知に散在する「コンテキスト断片化」
- 「別のサービスではなく形式」: SDK 不要、バージョン管理に保存可、人間可読 & エージェント解析可
- 構造: YAML フロントマター（type 必須、title / description / resource / tags / timestamp 推奨）+ Markdown 本文 + 相互リンク。予約ファイルは index.md / log.md
- 設計 3 原則: 制限の最小化 / プロデューサーとコンシューマーの独立 / プラットフォーム非依存
- リファレンス実装: BigQuery スキャンの拡充エージェント、静的 HTML ビジュアライザー、サンプルバンドル 3 種（GA4 / Stack Overflow / Bitcoin）
- GitHub: GoogleCloudPlatform/knowledge-catalog の okf/ 配下。Knowledge Catalog も OKF サポート

# 活用先

- [okf/overview.md](../okf/overview.md) ほか okf/ ディレクトリ全般の一次ソース

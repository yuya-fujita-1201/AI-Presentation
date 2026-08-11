---
type: Concept
title: OKF のファイル形式
description: OKF コンセプトファイルの書き方。YAML フロントマターのフィールド定義と本文・リンクの慣例
tags: [okf, specification, markdown, frontmatter]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T15:00:00+09:00"
---

# OKF のファイル形式

OKF の知識単位（コンセプト）は **UTF-8 の Markdown ファイル**で、「YAML フロントマター + 本文」の二部構成をとる。

## フロントマターのフィールド

| フィールド | 必須 | 内容 |
|-----------|------|------|
| `type` | ✅ 必須 | ファイルの種類。値は自由（例: `Concept`, `Table`, `Video`, `Guide`） |
| `title` | 推奨 | タイトル |
| `description` | 推奨 | 一行説明。エージェントがファイルを開くか判断する手がかりになる |
| `tags` | 推奨 | タグの配列 |
| `timestamp` | 推奨 | 更新日時（ISO 8601 形式） |
| `resource` | 推奨 | 対象の実体への URL（例: BigQuery コンソール、動画 URL） |

カスタムフィールドの追加は自由（例: `owner`, `review_status`）。統一されたメタデータは検索精度の向上に直結する。

なお上記は v0.1 の基本形。**v0.2 では `timestamp` が `generated: { by, at }` に置き換えられ**（旧記法もフォールバックで読まれる）、信頼性フィールド群 `sources` / `verified` / `status` / `stale_after` が追加された。詳細は [v02-changes.md](./v02-changes.md) を参照。

### type の自由度（実例）

`type` の値に決まった選択肢リストはなく、未知の値でも読み手はそれを無視・破棄せず保持するよう定められている。実例として、Google Analytics 4 の公式サンプルバンドルでは `metrics/` 配下の 8 ファイルの `type` がいずれも「metric」ではなく「reference」で統一されている。これは `type` が厳密な分類名ではなく、作成者が自由に決めてよいものであることを示す例である。

## 記述例（データテーブルの場合）

```yaml
---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, revenue]
timestamp: 2026-05-28T14:30:00Z
---

# Schema
| Column | Type | Description |
|--------|------|-------------|
| `order_id` | STRING | Globally unique order identifier. |
| `customer_id` | STRING | FK to [customers](./customers.md). |

# Joins
Joined with [customers](./customers.md) on `customer_id`.
```

## 本文の慣例

- セクション構成は自由（スキーマ、結合、ビジネスロジック、注意点など、type に応じて書き手が決める）
- コンセプト間の関係は **通常の Markdown リンク**で表現する。リンク種別（依存・参照など）は文脈から読み取る
- リンクは**相対パス推奨**（`./customers.md`）。リファレンス実装のビジュアライザーは絶対パスリンクをグラフのエッジとして扱わない既知の問題がある
- `# Citations` セクションで外部ソースを明示し、主張の根拠を示す

ディレクトリ全体の構造は [directory-structure.md](./directory-structure.md) を参照。

# Citations

- [OKF 公式仕様書 SPEC.md v0.2（フィールド定義の正）](../sources/spec-okf-v02.md)
- [Google Cloud 公式ブログ（発表記事）](../sources/article-gcloud-blog-okf.md)
- [Classmethod による v0.1 実装ガイド](../sources/article-classmethod-okf-v01-guide.md)
- [note: Obsidian での導入例](../sources/article-note-sutero-okf.md)
- [動画: OKF入門（GA4バンドルのtype実例）](../sources/video-okf-intro-google-standard.md)

---
type: Concept
title: OKF の設計原則
description: OKF v0.1 を支える 3 つの設計原則と、消費側に課される「寛容な消費モデル」
tags: [okf, design, specification]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T15:00:00+09:00"
---

# OKF の設計原則

## 3 つの原則

| 原則 | 内容 |
|------|------|
| 制限の最小化 | 必須フィールドは `type` のみ。type の値の定義やセクション構成はプロデューサー（書き手）に委ねる |
| プロデューサー / コンシューマーの独立性 | 人間が手書きしたバンドルを AI が利用でき、AI が生成したバンドルを別の AI がクエリできる。書き手と読み手が互いを知らなくてよい |
| フォーマットであってプラットフォームではない | 特定のクラウド・DB・LLM・SDK に依存しない。ファイルさえあれば成立する |

## 寛容な消費モデル (tolerant consumption)

OKF は「知識は段階的に蓄積される」前提で設計されており、消費側（リーダー・エージェント）には次が求められる:

- 未知の `type` 値を拒否しない
- 未知のフロントマターフィールドを拒否しない
- 壊れたリンクがあっても処理を止めない

つまり **不完全なバンドルでも読めるところから読む**。これにより、完璧に整備してから公開するのではなく、書きながら育てる運用が可能になる。

## 準拠条件（v0.1）

バンドルが OKF 準拠と言えるための条件はわずか 3 つ:

1. すべての非予約 Markdown ファイルが、解析可能な YAML フロントマターを持つ
2. すべてのフロントマターが空でない `type` を持つ
3. 予約ファイル（[index.md / log.md](./directory-structure.md)）が規定の構造に従う

## 根拠の明示（Citations）

本文に `# Citations` セクションを設けて主張の根拠（外部ソース）を明示する慣例がある（v0.1）。

v0.1 公開から約 6 週間後に公開された **v0.2** では、この考え方が「出所（Sources）・信頼性（Generated/Verified）・鮮度（絶対日付の有効期限）・状態（Status）・検算（Attested Computation）」という 5 つの専用フィールドへと具体化された。仕様書の行数は 451 行からおよそ倍以上（新規約 550 行）に増えたが、公式ブログは「足したのは語彙（ボキャブラリー）であってルールは足していない」と説明しており、必須フィールドは v0.2 でも `type` のみで変わっていない。詳細は [v02-changes.md](./v02-changes.md) を参照。

# Citations

- [Google Cloud 公式ブログ（発表記事）](../sources/article-gcloud-blog-okf.md)
- [Qiita: OKF 仕様の解説](../sources/article-qiita-zumax-okf.md)
- [動画: OKF v0.2 の Citations 解説](../sources/video-okf-v02-citations.md)

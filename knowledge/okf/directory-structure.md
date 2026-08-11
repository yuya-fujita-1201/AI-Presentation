---
type: Concept
title: OKF のディレクトリ構造と予約ファイル
description: OKF バンドルのツリー構造、ファイルパス = コンセプト ID の考え方、予約ファイル index.md / log.md の役割
tags: [okf, specification, directory]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T15:00:00+09:00"
---

# OKF のディレクトリ構造

OKF の「バンドル」は Markdown ファイルのディレクトリツリーである。

## 基本ルール

- **1 コンセプト = 1 ファイル**。知識の単位ごとにファイルを分ける
- **ファイルパスがコンセプトの ID** になる（例: `tables/orders.md`）。階層がそのまま分類になる
- Git リポジトリでの管理が推奨される。プレーンテキストなので差分レビューが容易

## 構造例（Google Cloud 公式のサンプル）

```
sales/
├── index.md
├── datasets/
│   ├── index.md
│   └── orders_db.md
├── tables/
│   ├── index.md
│   ├── orders.md
│   └── customers.md
└── metrics/
    ├── index.md
    └── weekly_active_users.md
```

## 予約ファイル

| ファイル | 役割 |
|---------|------|
| `index.md` | ディレクトリ内容の一覧（ナビゲーション）。フロントマターは付けない。エージェントに「段階的に情報を開示する」入り口になる |
| `log.md` | 変更履歴。新しい変更を上に書く。AI が「この知識はいつ更新されたか」を把握するために使う |

index.md をエントリーポイントにして各ファイルへの概要付きリンクを並べる構造は、既存の Web サイトの情報設計と同じ発想。エージェントは index.md → description → 必要なファイルだけ開く、という段階的な読み方ができる。

**例外**: バンドル**ルート直下**の `index.md` だけは、frontmatter に `okf_version: "0.2"` のように対象バージョンを宣言できる（任意）。index.md に frontmatter を書けるのはこの1箇所だけで、それ以外のディレクトリの `index.md` はフロントマターなしで目次のみを書く。

log.md の書式は `## YYYY-MM-DD` の日付見出し（新しい順）の下に `**Update**:` / `**Creation**:` 形式の箇条書きを並べる。

ファイル単体の書き方は [file-format.md](./file-format.md) を参照。

# Citations

- [OKF 公式仕様書 SPEC.md v0.2（okf_version・予約ファイル書式の正）](../sources/spec-okf-v02.md)
- [Google Cloud 公式ブログ（発表記事）](../sources/article-gcloud-blog-okf.md)
- [Classmethod による v0.1 実装ガイド](../sources/article-classmethod-okf-v01-guide.md)
- [Qiita: OKF 仕様の解説](../sources/article-qiita-zumax-okf.md)
- [動画: OKF入門（index.md / log.mdの実例）](../sources/video-okf-intro-google-standard.md)

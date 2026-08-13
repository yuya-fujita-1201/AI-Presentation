---
okf_version: "0.2"
---

# knowledge — 勉強会ナレッジベース

このディレクトリは OKF (Open Knowledge Format) 形式のナレッジバンドルです。
勉強会のテーマごとにディレクトリを分け、収集した資料は sources/ に台帳として登録します。

## 内容

- [okf/](./okf/index.md) — OKF (Open Knowledge Format) そのものについてのナレッジ。仕様・設計思想・実践方法
- [graph-engineering/](./graph-engineering/index.md) — グラフエンジニアリング（複数AIエージェントの分担・接続の設計）のナレッジ。用語の系譜から設計パターン・検証・リスクまで
- [prompt-engineering/](./prompt-engineering/index.md) — プロンプトエンジニアリングのナレッジ。定義・構造・基本技法から、文脈設計・技法の全体地図・ループエンジニアリング・最新モデル時代の「削る」実践まで
- [slide-system/](./slide-system/index.md) — パラメーター駆動の資料作成システム（deck.json → HTML/PPTX、微修正ワークフロー）のナレッジ
- [sources/](./sources/index.md) — 収集した外部資料（動画・記事）の台帳。1ソース = 1ファイル

## 使い方

- 新しい資料はまず sources/ に登録し、テーマとして育ったら専用ディレクトリへ昇華する
- 変更したら [log.md](./log.md) に履歴を追記する

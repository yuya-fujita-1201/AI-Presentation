---
okf_version: "0.2"
---

# knowledge — 勉強会ナレッジベース

このディレクトリは OKF (Open Knowledge Format) 形式のナレッジバンドルです。
勉強会のテーマごとにディレクトリを分け、収集した資料は sources/ に台帳として登録します。

## 内容

- [okf/](./okf/index.md) — OKF (Open Knowledge Format) そのものについてのナレッジ。仕様・設計思想・実践方法
- [graph-engineering/](./graph-engineering/index.md) — グラフエンジニアリング（複数AIエージェントの分担・接続の設計）のナレッジ。用語の系譜・基本語彙から、つなぎ方の型・損益分岐点・最終回答の所有権・サブエージェント実装・検証ゲート・失敗の分類とリスクまで
- [prompt-engineering/](./prompt-engineering/index.md) — プロンプトエンジニアリングのナレッジ。定義・構造・基本技法から、文脈設計・技法の全体地図・ループエンジニアリング・最新モデル時代の「削る」実践まで
- [context-engineering/](./context-engineering/index.md) — コンテキストエンジニアリングのナレッジ。何を・いつ・どれだけ見せるか、選別・容量・RAG・メモリ・圧縮・キャッシュ・安全境界・実践テンプレートまで
- [harness-engineering/](./harness-engineering/index.md) — ハーネスエンジニアリング（AIエージェントが動く環境そのものの設計）のナレッジ。定義・11責務とラダーから、道具・権限・設定スコープ・サンドボックス・プロジェクトメモリまで
- [loop-engineering/](./loop-engineering/index.md) — ループエンジニアリング（実行・検証・改善を自動で繰り返す仕組みそのものの設計）のナレッジ。定義・段階の積み上がり・ループの解剖から、停止条件・検証・Maker-Checker・部品構成・適用条件・リスクまで
- [slide-system/](./slide-system/index.md) — パラメーター駆動の資料作成システム（deck.json → HTML/PPTX、微修正ワークフロー）のナレッジ
- [sources/](./sources/index.md) — 収集した外部資料（動画・記事）の台帳。1ソース = 1ファイル

## 使い方

- 新しい資料はまず sources/ に登録し、テーマとして育ったら専用ディレクトリへ昇華する
- 変更したら [log.md](./log.md) に履歴を追記する

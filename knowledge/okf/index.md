# okf — Open Knowledge Format についてのナレッジ

Google Cloud が 2026 年 6 月に公開した、AI エージェントと人間が共有する知識フォーマット「OKF」についてまとめたディレクトリ。

## 内容

- [overview.md](./overview.md) — OKF とは何か。背景（コンテキスト断片化）と位置づけ
- [design-principles.md](./design-principles.md) — 設計の 3 原則と「寛容な消費モデル」
- [v02-changes.md](./v02-changes.md) — OKF v0.2 で追加された Sources / Generated・Verified / 鮮度 / Status / Attested Computation の解説
- [file-format.md](./file-format.md) — ファイルの書き方。YAML フロントマターとフィールド定義
- [directory-structure.md](./directory-structure.md) — バンドルのディレクトリ構造、予約ファイル（index.md / log.md）、リンクの張り方
- [ecosystem.md](./ecosystem.md) — MCP / llms.txt / AGENTS.md との関係、リファレンス実装
- [practice-tips.md](./practice-tips.md) — 実際に運用するときの Tips（Obsidian、Claude Code 連携、適用範囲の絞り方）

## 読む順番

初めての人は overview → file-format → directory-structure の順で読むと全体像がつかめる。

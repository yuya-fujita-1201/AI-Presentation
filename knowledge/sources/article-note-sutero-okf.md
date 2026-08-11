---
type: Article
title: OKF を Obsidian で試す（note / sutero）
description: Obsidian に 11 ファイルの OKF 導入例を作り、Claude Code がメタデータだけでファイル選別できることを実証した記事
resource: https://note.com/sutero/n/ne44b10942b8c
tags: [okf, obsidian, claude-code, practice]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T14:00:00+09:00"
---

# 要点

- OKF の本質は「既存の Markdown・フォルダ・リンクの活用方法の工夫」に過ぎず、導入障壁が低い
- 各ファイルは二部構成: フロントマター（type 必須、resource / tags / timestamp 推奨）+ 通常の Markdown 本文
- 著者は Obsidian で 11 ファイルの導入例を作成。index.md をエントリーポイントに概要付きリンクで接続（Web サイトの情報設計と同等）
- 実証: Claude Code に読ませたところ「補足的 4 ファイルは必要時のみ参照」と自律判断。メタデータだけで適切なファイル選別が実現
- 工夫: Vault 全体ではなく特定フォルダのみ OKF 化し、専用スキルとして呼び出すことでトークン効率と検索精度を両立

# 活用先

- [okf/practice-tips.md](../okf/practice-tips.md) の中心ソース

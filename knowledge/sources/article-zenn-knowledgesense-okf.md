---
type: Article
title: OKF 解説（Zenn / knowledgesense）
description: 「AI によるナレッジ管理の失敗パターン」の観点から OKF の価値を解説。統一メタデータによる検索精度向上
resource: https://zenn.dev/knowledgesense/articles/14a874a9f423bb
tags: [okf, knowledge-management, rag]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T14:00:00+09:00"
---

# 要点

- OKF は「Markdown ファイルの冒頭に YAML 形式のメタデータを付与する」仕組み。Google Cloud チームが 2026 年 6 月に提案
- 課題認識: 自動化されたナレッジ管理は「AI が無価値な情報を追加する」「統一されない属人的な管理になる」問題を抱える
- 設計思想: 最小限のルール（必須は type のみ）/ 作成と利用の分離 / フォーマット専門
- ファイルパスが概念の ID となる階層構造。メタデータは type, title, description, tags, owner, review_status など
- Markdown リンクで文書同士を接続し、AI が「文書間のリレーション」を理解しながら回答を生成できる
- 統一されたメタデータにより複数ファイルにまたがる検索の精度が向上する

# 活用先

- [okf/overview.md](../okf/overview.md)、[okf/practice-tips.md](../okf/practice-tips.md)

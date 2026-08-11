---
type: Article
title: OKF 仕様解説（Qiita / zumax）
description: OKF の仕様最小性・寛容な消費モデル・Citations 慣例・Git 管理推奨を整理した解説記事
resource: https://qiita.com/zumax/items/bda5528e85b9da17ad60
tags: [okf, specification]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T14:00:00+09:00"
---

# 要点

- OKF は Google Cloud が 2026 年 6 月に公開したオープン仕様。「Markdown + YAML frontmatter で組織の知識を表現」し、人間と AI の両方による作成・消費を想定
- 必須は `type` のみ。他メタデータは全てオプションで、カスタムフィールド追加も自由
- バンドルは Markdown ツリー。`index.md`（内容一覧・段階的情報提示）、`log.md`（更新履歴）、その他が個別の知識単位（Concept）
- UTF-8 Markdown で構成し、Git リポジトリ管理が推奨（差分レビューが容易）
- 関係性は標準 Markdown リンクで表現。リンク種別は文脈から理解する
- `# Citations` セクションで外部ソースを明示して主張の根拠を示す
- 寛容な消費モデル: 未知の type・未知フィールド・壊れたリンクがあっても消費側は拒否してはいけない。段階的な知識蓄積を想定

# 活用先

- [okf/design-principles.md](../okf/design-principles.md)、[okf/directory-structure.md](../okf/directory-structure.md)

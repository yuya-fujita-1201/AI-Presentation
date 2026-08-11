---
type: Concept
title: OKF とは何か
description: Google Cloud が 2026 年 6 月 12 日に公開した、AI エージェントと人間が共有する知識フォーマット OKF の概要・誕生の経緯・背景
tags: [okf, ai-agent, knowledge-management]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T15:00:00+09:00"
---

# OKF (Open Knowledge Format) とは

OKF は **Google Cloud が 2026 年 6 月 12 日（米国時間）に公開した、組織の知識を「Markdown + YAML フロントマター」で表現するオープン仕様**。人間と AI エージェントの両方が読み書きできる「知識の書き方」の共通言語として設計されている。公開時点のバージョンは v0.1（ドラフト、その後 [v0.2](./v02-changes.md) に改定）。

## 誕生の経緯

発端は AI 研究者アンドレイ・カーパシー氏が行っていた先行的な取り組みで、それを Google Cloud が OKF v0.1 として正式な仕様にまとめたと紹介されている（動画内では固有名称が聞き取りにくく、取り組みの正式名称までは特定できていない）。

## 解決したい課題: コンテキスト断片化

組織のナレッジは次のような場所に散在しており、AI エージェントがまとめて読める形になっていない:

- メタデータカタログ（独自 API）
- Wiki、共有ドライブ
- コードコメント、ドキュメント文字列
- エンジニアの頭の中（暗黙知）

RAG やエージェントの回答精度は「知識がどう置かれているか」に大きく左右される。OKF は、社内 Wiki 的に蓄積された知識（LLM-wiki パターン）を **ポータブルで相互運用可能な形式** にすることでこの問題に取り組む。

## 「プラットフォームではなくフォーマット」

OKF の最重要ポイントは、これが**新しいサービスではなく単なる形式**であること:

- SDK 不要で誰でも作成できる（手書きでも、DB からの自動生成でも）
- 特定のクラウド・DB・LLM プロバイダに依存しない
- Git などのバージョン管理にそのまま保存できる
- システム間を移動しても知識が存続する
- 人間が読める & エージェントが解析できる

本質は「既存の Markdown・フォルダ・リンクの活用方法の工夫」であり、新技術ではない。だからこそ導入障壁が低い。

## 最小仕様

必須フィールドは frontmatter の `type` のみ。詳細は [file-format.md](./file-format.md) を参照。設計の考え方は [design-principles.md](./design-principles.md) にまとめた。

# Citations

- [Google Cloud 公式ブログ（発表記事）](../sources/article-gcloud-blog-okf.md)
- [Classmethod による v0.1 実装ガイド](../sources/article-classmethod-okf-v01-guide.md)
- [Zenn: ナレッジ管理の課題と OKF](../sources/article-zenn-knowledgesense-okf.md)
- [動画: OKF入門（誕生の経緯）](../sources/video-okf-intro-google-standard.md)
- [動画: Googleが密かに撃った一手（発表日の詳細）](../sources/video-okf-google-knowledge-infra.md)

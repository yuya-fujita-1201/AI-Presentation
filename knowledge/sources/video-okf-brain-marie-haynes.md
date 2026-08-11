---
type: Video
title: Build an OKF brain like mine!
description: SEO 専門家 Marie Haynes 氏が、自分で構築した OKF（個人ナレッジベース「brain」）の中身と実際の使い方を実演する動画
resource: https://www.youtube.com/watch?v=esYAIA6lU-s
channel: Marie Haynes
duration: 22:48
published: 2026-06-26
tags: [okf, video, english, practice, antigravity, playbook]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T15:00:00+09:00"
---

# 概要

SEO 専門家 Marie Haynes 氏が、Google の OKF（Open Knowledge Format）を使って自分専用のナレッジベース（本人は「brain」と呼ぶ）を構築した過程と、実際の業務での使い方を画面共有しながら解説する動画。前作の OKF 紹介動画が好評だったため、その後自分の brain を作り込んだと述べている。動画内で本人が明言している作業期間は「数日」のみで、「週」単位の言及はない。

# 要点

## OKF の基本構造（本人の理解として）

- 必須なのは YAML フロントマターの `type` のみ。`title` / `description` / `tags` / `timestamp` は推奨だが任意
- `tags` を付けるとファイル同士がリンクでつながり、いわゆる「ナレッジグラフ」ができると説明している
- フロントマター以下の本文は完全に自由で、エージェントへの指示文としても使える
- `index.md` はディレクトリ内容の一覧であり、「progressive disclosure（段階的開示）」の入り口だと説明。エージェントはまず index を読み、必要なファイルだけを開きに行く
- OKF と RAG（retrieval augmented generation）の違いとして、Gemini のような巨大なコンテキストウィンドウに情報を全部詰め込む方式はトークン消費が大きいのに対し、OKF は必要な Markdown ファイルだけを読みに行くため相対的に高速・省トークンだと述べている

## 自分の brain で使っている type

- `index`、`log`（エージェントが行った作業の記録ファイル）、`concepts`、`entities`、`playbooks`、`references`、`systems` を使用
- type は Google が示した例を参考にしただけで、実際は自由に決めてよいものだと説明
- 最初に作った OKF は type を作りすぎて失敗したという反省を語っている
- Antigravity が `entities` というタイプ名のスペルを間違えて生成したと述べているが、具体的にどう間違えたかは字幕からは判別できない

## playbook の実例

- **コミュニケーションボイスの playbook**: クライアント向け提案書を作らせた際、エージェントが「We（当社は）」を使う企業的な口調になってしまったため、「Marie 個人として一人称 `I` を使い、カジュアルなトーンで話す」というルールを playbook として保存した
- **Google コアアップデート後のサイトインパクト分析のチェックポイント手順**: あるクライアントで順位が上下したサイトを分析する手順を playbook 化するのに数日かかったが、一度作った後は別のクライアントに対して同種の分析を Antigravity に依頼するだけで、数日かかっていた作業がレポートとして即座に得られるようになったと述べている
- playbook の一部は本人が作成したものだが、一部は brain が自律的に作成したものもあると説明している（許可を与える設定がある前提）
- `skills.md` と OKF の playbook の違いについて、本人も明確に区別がついていないと述べ、視聴者にコメントで教えてほしいと呼びかけている

## ライブデモ：情報を ingest する流れ

- Search Engine Roundtable で見つけた「Search Console の新機能（AI にコンテンツの使われ方を管理させる機能）」についての記事の URL を、agent に「ingest this」と伝えて渡す
- エージェントは index を読み、実行計画（新しい reference ファイルの作成、既存の concept ファイルへのリンク追加・更新など）を提示する
- 実行前に承認ボタンを押す運用にしており、エージェントに無断で brain を書き換えさせない設計にしていると説明
- 承認後、新しい reference ファイルが生成され、関連する既存の concept（「AI features in Google Search」「AI Overviews」「AI mode」など）へのリンクが更新される
- 生成された reference に対して「1 段落で要約して」と質問すると、エージェントが index から該当ファイルを探し当てて回答を生成する様子を実演している
- サイト全体を丸ごと Markdown 化して 1 ページ 1 ファイルにするアプローチを他の実践者が取っているのを見たが、それは正しいやり方ではなく、情報を concept 単位に分解することに OKF の強みがある、という私見を述べている

## 使用ツール・モデル

- brain の構築には Google の Antigravity（AI コーディングエージェント）を使用
- モデルは Gemini API 経由で Gemini 3 Flash Preview 系を使用。より高価な Gemini 3.5 Flash よりコストパフォーマンスが良いと感じており、Antigravity 内でこのモデルを常に使うルールを設定していると述べている（字幕上の表記のため正確なモデル名は不確実）
- ナレッジグラフのビジュアライズ機能は OKF の仕様ドキュメントに手順が書かれており、それをそのままエージェントに渡すだけで実装できたと説明している

## 運用上の工夫

- Google の SEO スターターガイドなど公式ドキュメントの全文を reference として brain に保存している
- OKF とは別に、Google 公式ドキュメントの更新を定期的にチェックする仕組みを独自に構築しており、ドキュメントが更新されると通知が来るようにしている（本人はこれを OKF の一部ではないと明言）
- brain は毎日 GitHub にバックアップしており、コンピュータの不具合やプログラムによる上書きに備えていると説明している

## 今後の展望

- 自身が運営するコミュニティ（community.mariehaynes.com）の投稿を OKF に取り込み、人によるキュレーションを挟んだ上で、読者ごとにパーソナライズされたニュースレターを生成する構想を進めていると述べている。ただし結果はまだ分からない段階だとしている

## 視聴者へのアドバイス

- 自分の OKF を作りたい人は、概要欄にある Google 公式の仕様ドキュメントへのリンクと、この動画のトランスクリプトをエージェントに渡し「Marie がやったようなものを作って」と指示することを勧めている
- 使用エージェントは Claude、ChatGPT（Codex）、Antigravity のいずれでもよいとしつつ、本人は Antigravity を強く推している
- コーディング未経験でも構築可能だと強調しており、本人も数年前に ChatGPT でコーディングを学び始めたと述べている
- 最初に作った OKF は実際には内容を Markdown ファイルに保存しておらず、表示だけしていた不具合があり作り直しになったという失敗談を共有し、試行錯誤は前提だと述べている

# 活用先

- [okf/practice-tips.md](../okf/practice-tips.md) の補助教材候補
- [okf/directory-structure.md](../okf/directory-structure.md): index.md による progressive disclosure の実例として参照可能
- [okf/file-format.md](../okf/file-format.md): フロントマターの必須/推奨フィールドの実運用例として参照可能

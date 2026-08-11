# sources — 収集資料の台帳

勉強会のネタとして収集した外部資料の台帳。1 ソース = 1 ファイルで、フロントマターの `resource` に元 URL を持つ。

## 仕様書（一次情報）

- [spec-okf-v02.md](./spec-okf-v02.md) — OKF 公式仕様書 SPEC.md (v0.2)。フィールド定義・予約ファイル規定の正となる文書

## 記事

- [article-gcloud-blog-okf.md](./article-gcloud-blog-okf.md) — Google Cloud 公式ブログ。OKF の発表記事（一次情報）
- [article-classmethod-okf-v01-guide.md](./article-classmethod-okf-v01-guide.md) — Classmethod による OKF v0.1 の実装ガイド
- [article-zenn-knowledgesense-okf.md](./article-zenn-knowledgesense-okf.md) — Zenn。ナレッジ管理の課題の観点から OKF を解説
- [article-qiita-zumax-okf.md](./article-qiita-zumax-okf.md) — Qiita。OKF 仕様（最小性・寛容な消費）の解説
- [article-note-sutero-okf.md](./article-note-sutero-okf.md) — note。Obsidian での OKF 導入実例と Claude Code 実証

## 動画（YouTube）

- [video-okf-quick-understanding.md](./video-okf-quick-understanding.md) — 「AIが資料整理する新ルールOKFをサクッと理解する」。タグ・1件1ファイル・リンクの3ルールと、整理作業自体をAIに任せる実践法を解説する入門動画
- [video-okf-intro-google-standard.md](./video-okf-intro-google-standard.md) — 「OKF入門：AIの知識を"フォルダ"で共有するGoogleの新標準」。バンドル構造・frontmatter必須フィールド・相互リンクをGA4バンドルの実例で解説
- [video-okf-google-knowledge-infra.md](./video-okf-google-knowledge-infra.md) — 「Googleが密かに撃った一手 — OKFがAIエージェント時代の知識基盤を塗り替える」。データ/業務/個人の3活用例とBI標準OSIとの住み分けを解説
- [video-okf-markdown-standard.md](./video-okf-markdown-standard.md) — 「AIエージェントが利用するナレッジをMarkdownで標準化するオープンフォーマット」。コンテキストアセンブリー問題、寛容な消費モデル、MCPとの役割分担、ASOの概念を解説
- [video-okf-brain-marie-haynes.md](./video-okf-brain-marie-haynes.md) — "Build an OKF brain like mine!"（英語）。SEO専門家 Marie Haynes 氏が自作のOKF個人ナレッジベース「brain」の構築・運用を実演
- [video-okf-v02-citations.md](./video-okf-v02-citations.md) — 「GoogleのOKF v0.2、知識に『情報の根拠』を付け足す」。v0.1から6週間での大改定で追加されたSources/Generated・Verified/鮮度/Status/Attested Computationを解説
- [video-json-driven-video-production.md](./video-json-driven-video-production.md) — 「編集ソフトも動画生成AIも使わずに、解説動画を作っています」（クロノITチャンネル）。全要素を1枚のJSONで管理する動画制作パイプライン。スライドのパラメーター駆動管理の参考元

## 動画（グラフエンジニアリング）

- [video-ge-nyanta-loop-graph-claude-code.md](./video-ge-nyanta-loop-graph-claude-code.md) — 「最近話題の『ループエンジニアリング』『グラフエンジニアリング』とは？」（にゃんたのAIチャンネル、31分）。用語整理からRefineBench論文、Claude Codeサブエージェントでの検証ループ実践まで
- [video-ge-koremaji-single-to-multi.md](./video-ge-koremaji-single-to-multi.md) — 「グラフエンジニアリング入門：エージェント単体の挙動から、エージェント同士の分担へ」（海外テックの「これマジ?」）。エッジ=契約、2層グラフ、アドバイザーパターン、失敗の増幅とアンカー
- [video-ge-complete-guide-work-division.md](./video-ge-complete-guide-work-division.md) — 「【グラフエンジニアリング】完全ガイド｜AIエージェントは仕事をどう分ける？」（Sura×Asura）。DAG・Manager/Worker/Verifier・CAID・git worktree隔離
- [video-ge-relationship-design-intro.md](./video-ge-relationship-design-intro.md) — 「AIエージェント運用を関係性から設計する方法」（Sura×Asura）。目的・担当・作業・根拠・承認の型付きグラフとコンテキストパック
- [video-ge-kininarundamon-parallelism.md](./video-ge-kininarundamon-parallelism.md) — 「その順番待ち、ほんとに要るのだ？」（ずんだもんの実験道具箱）。偽エッジテスト、Claude Code dynamic workflows、Bun書き換えの隠れたエッジ事故
- [video-ge-ai-forgets-graph-remembers.md](./video-ge-ai-forgets-graph-remembers.md) — 「AIは忘れる、グラフは忘れない」（AISPALab）。Karpathyのautoresearch、AgentHub、知識グラフを共有メモリにする発想
- [video-ge-bpo-org-chart.md](./video-ge-bpo-org-chart.md) — 「グラフエンジニアリングとは何か ― AIチームの組織図をバックオフィス目線で解説」（管理のプロ）。請求書処理を5ノードでグラフ化、正体は業務フロー設計
- [video-ge-5-stages-beginner.md](./video-ge-5-stages-beginner.md) — 「Graphエンジニアリングとは？AI活用5段階の違いと構造を初心者向けに解説」（AI氣道）。厨房・経営・子育ての3比喩と「グラフは提案、確定は人間」
- [video-ge-gaodalie-forget-loop.md](./video-ge-gaodalie-forget-loop.md) — "FORGET Loop Engineering. Graph Engineering is about THIS"（Gao Dalie）。プロンプト/ループ/グラフの3層と「経路を人間が設計する」視点
- [video-ge-caleb-8min-explainer.md](./video-ge-caleb-8min-explainer.md) — "Graph Engineering explained in 8min.."（Caleb Writes Code）。オイラーのグラフ理論から、ノードが賢くなりボトルネックがエッジへ移った歴史
- [video-ge-techplay-3min-intro.md](./video-ge-techplay-3min-intro.md) — 「SNSで話題の『グラフエンジニアリング』の正体は？」（TECH PLAY、3分）。ノード/エッジ/状態の3要素、データ可視化との混同の訂正

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

## 記事（プロンプトエンジニアリング）

- [article-pe-claude-prompting-best-practices.md](./article-pe-claude-prompting-best-practices.md) — Anthropic公式「Prompting best practices」。明確で直接的な指示・文脈の追加・few-shot例の設計・XMLタグによる構造化の4原則を解説
- [article-pe-claude-opus-5-prompting.md](./article-pe-claude-opus-5-prompting.md) — Anthropic公式「Prompting Claude Opus 5」。Opus 4.8比の性能差分（agentic coding・コードレビュー・effort設定・vision・長文脈・オフィス業務・マルチエージェント調整）に基づくプロンプト設計パターンを解説
- [article-pe-prompt-report.md](./article-pe-prompt-report.md) — arXiv「The Prompt Report」（Schulhoff et al.）。PRISMAベースの系統的レビューで58技法・33用語を分類し、多言語・マルチモーダル・エージェント・評価・安全性まで扱う包括的サーベイ
- [article-pe-pe-survey-sahoo.md](./article-pe-pe-survey-sahoo.md) — arXiv「A Systematic Survey of Prompt Engineering in Large Language Models」（Sahoo et al.）。41種類以上の技法をアプリケーション領域別に分類、Zero-Shot/Few-Shot Promptingの位置づけを解説
- [article-pe-kddi-prompt-basics.md](./article-pe-kddi-prompt-basics.md) — KDDI株式会社「プロンプトとは？種類や作成方法、具体的なプロンプト例を紹介」。プロンプトの語源とAI時代の意味の広がり、命令・補完・実演の3類型、業務効率化やコンテンツ作成での活用シーンを解説
- [article-pe-qiita-kissy24-methods.md](./article-pe-qiita-kissy24-methods.md) — Qiita「【生成AI】サクッと学ぶプロンプトエンジニアリング手法」（kissy24）。Instruction/Context/Input Data/Output Indicatorの4要素構成、3種類の記載フォーマット、ロールプレイやZero-shot Promptingを解説
- [article-pe-sios-prompt-engineering-intro.md](./article-pe-sios-prompt-engineering-intro.md) — サイオステクノロジー株式会社「初心者必見！プロンプトエンジニアリング入門ガイド ~基礎編~」。NRIの定義とダイエット相談の具体例、OpenAI社セッションによる重要性の裏付け、プロンプトの続きを予測する性質、Instructions（命令）テクニックの基礎を解説

## 公式資料・原著（コンテキストエンジニアリング）

- **CE-S01** [article-ce-anthropic-effective-context-engineering.md](./article-ce-anthropic-effective-context-engineering.md) — Anthropicによる定義、必要十分な高シグナル情報、段階的開示、圧縮、サブエージェントの整理
- **CE-S02** [course-ce-microsoft-context-engineering.md](./course-ce-microsoft-context-engineering.md) — Microsoftの初心者向け教材。固定commitでinstructions・knowledge・tools・history・preferencesと管理戦略を確認
- **CE-S03** [article-ce-google-adk-context-architecture.md](./article-ce-google-adk-context-architecture.md) — Google ADKのworking context、session、memory、artifactを分けた設計モデル
- **CE-S04** [paper-ce-lost-in-the-middle.md](./paper-ce-lost-in-the-middle.md) — 長文中の位置効果を複数文書QAとキー値検索で調べたTACL採録研究
- **CE-S05** [paper-ce-google-retrieval-quality-context-limit.md](./paper-ce-google-retrieval-quality-context-limit.md) — McKinnon (2025) がGemini 2.5 Flash単一・単純factoid QAで示した、普遍化への限定的な対照結果
- **CE-S06** [paper-ce-rag-lewis-2020.md](./paper-ce-rag-lewis-2020.md) — 外部の非パラメトリック記憶と生成を結ぶRAG原著
- **CE-S07** [article-ce-google-sufficient-context-rag.md](./article-ce-google-sufficient-context-rag.md) — 検索結果の関連性と、回答に必要な情報が揃う十分性を分けるGoogle Research解説
- **CE-S08** [docs-ce-anthropic-memory-tool.md](./docs-ce-anthropic-memory-tool.md) — セッション外へ保存し、必要時に再投入する外部メモリと安全上の責任
- **CE-S09** [docs-ce-anthropic-manage-tool-context.md](./docs-ce-anthropic-manage-tool-context.md) — tool定義・結果による肥大化と、検索・集約・編集・cacheの役割差
- **CE-S10** [docs-ce-openai-prompt-caching.md](./docs-ce-openai-prompt-caching.md) — 同じ入力prefixの計算を再利用するPrompt cache。メモリや圧縮とは異なる
- **CE-S11** [docs-ce-anthropic-prompt-injection.md](./docs-ce-anthropic-prompt-injection.md) — 外部資料中の悪意ある命令に対する多層防御と継続評価
- **CE-S12** [docs-ce-openai-data-controls.md](./docs-ce-openai-data-controls.md) — API・機能・第三者接続によって異なる保存、保持、データ境界の確認事項

## 動画（プロンプトエンジニアリング）

- [video-pe-loop-engineering-overview.md](./video-pe-loop-engineering-overview.md) — 「【ゆる解説】ループエンジニアリングって何？」（安野貴博の自由研究）。プロンプト・コンテキスト・ハーネス・ループの4段階とHuman in the LoopからHuman on the Loopへの移行、アンドリュー・ン氏の3種の入れ子ループ論
- [video-pe-opus-5-prompt-tips.md](./video-pe-opus-5-prompt-tips.md) — 「Claude最新！新モデルOpus 5が予想以上に凄かったので解説」（にゃんたのAIチャンネル）。Fable5・GPT5.6とのベンチマーク/コスト比較、Opus5向けプロンプトの書き方とシステムプロンプト削減の知見
- [video-pe-opus-5-benchmark-tips.md](./video-pe-opus-5-benchmark-tips.md) — "A complete guide to Claude Opus 5!..."（keitoaiweb）。219ページ資料と22パターンの実践比較検証、公式ベストプラクティスに基づくOpus5向けプロンプトのコツ
- [video-pe-five-engineering-stages.md](./video-pe-five-engineering-stages.md) — "[How to Master AI] A Thorough Guide to Loop, Harness, Prompt, Context, and Graph Engineering"（keitoaiweb）。プロンプト・コンテキスト・ハーネス・ループ・グラフ5つの全体マップと「入れ子」構造の整理
- [video-pe-loop-engineering-5plus1-parts.md](./video-pe-loop-engineering-5plus1-parts.md) — "The End of the Era of Prompting AI | A Thorough Explanation of Loop Engineering"（RUNTEQ）。プロンプト→コンテキスト→ハーネス→ループの段階変遷、インナー/アウターループの2層構造、ループを構成する「5+1の部品」、自作のエピックフロー／移ローの実装とモデル使い分け

## 動画（コンテキストエンジニアリング）

- [video-ce-context-layers-intro.md](./video-ce-context-layers-intro.md) — 「【ゆっくり解説】コンテキストエンジニアリング入門、AI 出力品質を一段上げる設計術」（ゆっくり探究Lab）。コンテキストをシステムプロンプト・プロジェクトメモリ・検索拡張・ツール呼び出し・会話履歴の5層に整理し、Claude Codeでの実装例と構造化・削減のコツ、3つの落とし穴を解説
- [video-ce-context-rot-and-jit.md](./video-ce-context-rot-and-jit.md) — コンテキスト劣化(context rot)とJIT検索。Anthropic公式警告の解説動画
- [video-ce-context-4-elements.md](./video-ce-context-4-elements.md) — 「AI仕事術・実践｜コンテキストとは何か」（工藤あい　AI導入・AI駆動　バーニングトライブ）。コンテキストを「AIの目の前に置かれている情報の全部」と定義し、目的・前提・材料・見本の4点セットと仕組み化の実務型を解説
- [video-ce-harness-context-setup.md](./video-ce-harness-context-setup.md) — 「AIの性能は7割が"環境構築"で決まる」（チャエン【AI研究所】Byデジライズ）。プロンプト→コンテキスト→ハーネスの縦3段階とループ・グラフの横軸、コンテキストウィンドウ拡大とRAGの位置づけ、Claude Codeでのフォルダ・MCP実践を解説

## 記事（コンテキストエンジニアリング）

- [article-ce-compaction.md](./article-ce-compaction.md) — Anthropic公式ドキュメント「Compaction」。コンテキストウィンドウの上限に近づくと古いコンテキストを自動要約するcompaction機能の用途・動作の仕組み・パラメータ仕様を解説
- [article-ce-lost-in-the-middle.md](./article-ce-lost-in-the-middle.md) — DEV Community記事。コンテキスト内の位置によってLLMの正答率がU字型に変化する「lost in the middle」現象を、2023年のStanford等の論文と2025年のMIT研究による2つのアーキテクチャ的原因から解説

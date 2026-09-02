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
- [article-adr-nygard.md](./article-adr-nygard.md) — Michael Nygard「Documenting Architecture Decisions」（2011）。1決定1ファイルの ADR と、覆った決定を superseded で残す慣行の原典。OKF 実践編の「上書き＋決定記録」の根拠

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
- [video-ge-subagent-when-to-use.md](./video-ge-subagent-when-to-use.md) — 「How to use ClaudeCode and Codex subagents!」（にゃんたのAIチャンネル）。Googleの研究論文が示す「シングルエージェント精度45%」という損益分岐点と、並列調査・忖度回避・作成検証ループの3活用法
- [video-ge-dynamic-workflows-six-patterns.md](./video-ge-dynamic-workflows-six-patterns.md) — 「【Claude Code新機能】Dynamic Workflows完全解説」（みにこーへいのAI活用チャンネル、99秒）。分類振り分け・ファンアウト・敵対的検証・生成篩い落とし・トーナメント・終了判定の6つの編成パターン
- [video-ge-subagent-overview-basics.md](./video-ge-subagent-overview-basics.md) — 「【前編】Claude Codeサブエージェント完全ガイド」（まさやん【AIギルドch】）。フロントマターの全設定項目・拒否リスト優先の仕様・呼び出し方法・コンテキスト管理の基礎と、役割分離による品質向上・並列実行の高速化・ネスト不可などの制約を解説

## 記事（グラフエンジニアリング）

- [article-ge-anthropic-building-effective-agents.md](./article-ge-anthropic-building-effective-agents.md) — Anthropic公式「Building Effective AI Agents」。WorkflowとAgentの定義区別、augmented LLMという基本構築ブロック、5つのワークフローパターン（Prompt chaining/Routing/Parallelization/Orchestrator-workers/Evaluator-optimizer）、シンプルさの原則を解説
- [article-ge-openai-orchestration-handoffs.md](./article-ge-openai-orchestration-handoffs.md) — OpenAI公式「Orchestration and handoffs」。会話の所有権を引き渡すHandoffsと、マネージャーが所有権を保持するAgents as Tools(Managerパターン)の対比、専門家追加の4判断基準、「まず単一エージェントから始める」原則を解説
- [article-ge-anthropic-multi-agent-research-system.md](./article-ge-anthropic-multi-agent-research-system.md) — Anthropic公式「How we built our multi-agent research system」。リードエージェントがサブエージェント群に探索を委任するオーケストレーター・ワーカー構成、内部評価による90.2%の性能改善と約15倍のトークン消費、開発中の失敗事例と対処、プロンプトエンジニアリング上の教訓を解説
- [article-ge-anthropic-building-c-compiler.md](./article-ge-anthropic-building-c-compiler.md) — Anthropic公式「Building a C compiler with a team of parallel Claudes」。16個のClaudeエージェントを並列稼働させたRust製Cコンパイラ開発実験、タスクロックによる競合回避の運用設計、「task verifierがほぼ完璧である必要がある」という教訓を解説
- [article-ge-mast-multi-agent-failures.md](./article-ge-mast-multi-agent-failures.md) — arXiv「Why Do Multi-Agent LLM Systems Fail?」（Cemri, Pan, Yang et al.）。7フレームワーク・1600件超のトレースを含むMAST-Dataと、14の失敗モードを3カテゴリ(システム設計・エージェント間非整合・タスク検証)に整理したMAST分類体系を提案、kappa=0.88の高い一致度で構築された信頼性を解説
- [article-ge-gptswarm-optimizable-graphs.md](./article-ge-gptswarm-optimizable-graphs.md) — arXiv/ICML2024「GPTSwarm: Language Agents as Optimizable Graphs」。単一エージェント・スワームを有向非環グラフとして統一表現し、REINFORCEによるエッジ最適化とOPRO等によるノード最適化の2段階最適化、GAIAベンチマークでGPT-4-Turbo・AutoGPTを上回る平均18.45%達成を解説
- [article-ge-agent-error-taxonomy-debug.md](./article-ge-agent-error-taxonomy-debug.md) — arXiv「Where LLM Agents Fail and How They can Learn From Failures」。Memory/Reflection/Planning/Action/System-level operationsの5領域に失敗モードを体系化したAgentErrorTaxonomy、ALFWorld・GAIA・WebShopの実軌跡から成る初の大規模失敗軌跡データセットAgentErrorBench、根本原因デバッグでタスク成功率を最大26%改善したAgentDebugフレームワークを解説

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
- [article-ce-softbank-what-is-context-engineering.md](./article-ce-softbank-what-is-context-engineering.md) — ソフトバンク株式会社ビジネスブログ。コンテキストエンジニアリングの定義、会話履歴の忘却問題、プロンプトエンジニアリングとの違い、システムプロンプト・要約・外部保管という実践テクニックを解説
- [article-ce-cloco-context-engineering-claude.md](./article-ce-cloco-context-engineering-claude.md) — cloco Blog。KarpathyやTobi Lütkeの言及を紹介しつつ、AnthropicのWrite/Select/Compress/Isolateの4戦略とClaude CodeのCLAUDE.md整備を実践の入り口として解説
- [video-he-webmcp-cloudflare-guide.md](./video-he-webmcp-cloudflare-guide.md) — WebMCPの解説。AIエージェントにツール（道具）を与える仕組みとハーネス層の実際
- [video-he-claude-code-4hour-agent.md](./video-he-claude-code-4hour-agent.md) — 「【Claude Code活用法】4時間でMC野嶋専用のAIエージェントを構築」（PIVOT）。環境構築からスキル作成、業務効率化AIエージェント完成までの体験企画。「スキル＝AIへの業務マニュアル」「AIに任せすぎない」設計の実例

## 記事（ハーネスエンジニアリング）

- [article-he-claude-code-permissions.md](./article-he-claude-code-permissions.md) — Anthropic公式「Configure permissions」。ツール種別ごとの承認要否、deny→ask→allowの評価順序、ツール名指定denyによる完全除去とスコープ指定denyの違い、Ctrl+Eの説明表示機能を解説
- [article-he-claude-code-permissions-admin.md](./article-he-claude-code-permissions-admin.md) — AI Orchestra。法人導入支援の視点からdeny/ask/allow評価順序とCLAUDE.md記述との違い、sudoとbypassPermissionsモードの2論点、確認プロンプトを減らす4方法、managed settingsを含む設定ファイル4層を解説
- [article-he-claude-code-settings.md](./article-he-claude-code-settings.md) — Anthropic公式「Claude Code settings」。設定を適用するManaged/User/Project/Localの4スコープと優先順位、各スコープの想定用途を解説
- [article-he-agent-sdk-overview.md](./article-he-agent-sdk-overview.md) — Anthropic公式「Agent SDK overview」。エージェントの定義、Agent SDK/CLI/Client SDK/Managed Agentsの使い分け、Built-in tools・Hooks・Subagents・MCP等の提供機能を解説
- [article-he-harness-engineering-paper.md](./article-he-harness-engineering-paper.md) — arXiv「AI Harness Engineering」。SWE能力をモデル・ハーネス・環境から成るシステムの創発的性質として捉え直し、11の責務とH0〜H3ラダー、トレースベース評価プロトコルを提案
- [article-he-claude-md-best-practices.md](./article-he-claude-md-best-practices.md) — Zenn。CLAUDE.mdの「コンテキスト汚染」を避ける設計指針。300行以内・150〜200指示の目安、プロジェクト概要・頻出コマンド・罠の共有という3要素、段階的開示を解説
- [article-he-sandbox-technology.md](./article-he-sandbox-technology.md) — Zenn（株式会社松尾研究所）。コーディングエージェントのサンドボックス技術をOSネイティブ（Seatbelt/bubblewrap）・コンテナ（gVisor）・microVMの3分類で解説、Claude Code・Claude Desktopの実装比較
- [article-ce-fortune-replit-database-incident.md](./article-ce-fortune-replit-database-incident.md) — ReplitのAIエージェントによる本番DB削除事故（Fortune・2025年7月）。ハーネス不在の実害事例
- [article-ce-replit-production-database-incident.md](./article-ce-replit-production-database-incident.md) — コードフリーズ中の本番DB削除とロールバック復旧の経緯（2025年7月）
- [article-pe-google-introduction-to-llms.md](./article-pe-google-introduction-to-llms.md) — Google for Developers公式。言語モデルがトークン列の確率を推定する仕組みの入門
- [article-pe-google-introduction-to-prompting.md](./article-pe-google-introduction-to-prompting.md) — Google Cloud公式。プロンプトの定義と構成要素（質問・指示・文脈・few-shot例）
- [issue-ce-gemini-cli-4586.md](./issue-ce-gemini-cli-4586.md) — sandbox無効環境でファイルを失ったとするユーザー報告（gemini-cli issue #4586・2025年7月）

## 動画（ループエンジニアリング）

- [video-le-anno-team-mirai-loop-engineering.md](./video-le-anno-team-mirai-loop-engineering.md) — 「【ループエンジニアリングとは？】AIにプロンプトはもう要らない、、非エンジニアも必見！」（安野貴博とチームみらい通信）。「プロンプトを打つ」から「AIが自走するループを設計する」への移行、Human on the Loop、終盤の非エンジニア向け3業務例（日程調整・会議後タスク管理・書類作成チェック）。自由研究チャンネル版（video-pe-loop-engineering-overview）の別チャンネル再解説
- [video-le-loop-design-four-points.md](./video-le-loop-design-four-points.md) — 「【必見】AIエージェントは『ループ設計』の時代！完全自律で回す5つのポイント含め解説します」（まさおAIじっくり解説ch）。ループ設計の4つのポイント（ゴール明確化・エージェント割当・進捗検証・継続条件判定）と、ロングラン自律動作のための5つの技術（オートパーミッション・動的ワークフロー・ループコマンド・自己検証ツール・Ralph Loop）、「ゴール」と「ループ」の概念上の違いを解説

## 記事（ループエンジニアリング）

- [article-le-claude-code-best-practices.md](./article-le-claude-code-best-practices.md) — Anthropic公式「Best practices for Claude Code」。合否判定可能なチェック（テスト・ビルド・スクリーンショット比較）を与えることで実行→検証→反復のループを自律的に回す方法、チェックの強制力を高める4段階（単発プロンプト・/goal・Stopフック・検証サブエージェント）、成功の自己申告ではなく証拠を提示させる推奨を解説
- [article-le-evaluator-optimizer.md](./article-le-evaluator-optimizer.md) — Anthropic公式Claude Cookbook「Evaluator optimizer」。生成担当と評価担当のLLM呼び出しを分離し評価がPASSになるまで過去の試行とフィードバックを積み増しながら再生成するワークフローパターンと、generate・evaluate・loopの3関数によるPythonリファレンス実装を解説
- [article-le-self-refine.md](./article-le-self-refine.md) — arXiv「Self-Refine: Iterative Refinement with Self-Feedback」（Madaan et al.）。同一LLMが生成・批評・改善の三役を兼ね追加学習なしで出力を反復改善する手法、7タスク×3モデルでの評価で平均約20%の絶対的改善を報告。loop engineeringにおける「自己改善ループ」の原典として位置づけ
- [article-le-loop-engineering-mindstudio.md](./article-le-loop-engineering-mindstudio.md) — MindStudio「What Is Loop Engineering? The New Meta for Autonomous AI Agent Workflows」。loop engineeringを観察・推論・行動・評価の反復と定義し、/loop・/goal・/routinesの3構成要素、適用条件、Self-Refineを実装例とする位置づけを解説
- [article-le-kilo-loop-engineering-definition.md](./article-le-kilo-loop-engineering-definition.md) — Kilo「What Is Loop Engineering? AI Feedback Loops」。Intent-Context-Action-Observation-Adjustmentの5段階モデル、プロンプトエンジニアリングとの対比表、5つの実践パターン（Test-Driven/Compiler-Driven/Review-Driven/Runtime Debugging/Product Iteration）を解説
- [article-le-zenn-maker-checker-practice.md](./article-le-zenn-maker-checker-practice.md) — Zenn「Claude Code で『ループエンジニアリング』を実践してみた」（tetsu_don）。レビュー役から修正権限を剥奪するMaker-Checkerパターンの実装、「想定内の異常系か本当のバグか」を見極める性質判定ステップの重要性、書籍価格チェッカーでの実践検証を解説
- [article-le-qiita-syoitu-loop-engineering.md](./article-le-qiita-syoitu-loop-engineering.md) — Qiita「入門から実践 -「🔁 ループエンジニアリング」」（Syoitu）。Addy Osmaniの定義を軸に、ループの5つのアクション・6つのパーツ、Claude Codeでの3ファイル実装（CLAUDE.mdの停止条件・settings.jsonのフック・fixerサブエージェント）、Mastra Goals機能、回しっぱなしの代価を解説
- [article-le-note-masawunder-goal-loop-design.md](./article-le-note-masawunder-goal-loop-design.md) — note「Claude Code ループエンジニアリング入門」（masa_wunder）。ループの核心を停止条件と位置づけ、/goal（ゴール駆動）と/loop（時間駆動）の使い分け、単一条件で失敗した経験から品質スコア・最大イテレーション・最大時間の3重構成に至った設計、段階的導入の3ステップを解説

## 記事（RAG）

- [article-rag-anthropic-contextual-retrieval.md](./article-rag-anthropic-contextual-retrieval.md) — Anthropic公式「Contextual Retrieval in AI Systems」。チャンクへの文脈付加によるContextual Embeddings/Contextual BM25、Claude 3 Haikuでの自動生成とプロンプトキャッシングによるコスト抑制、検索失敗率の段階的削減を解説
- [article-rag-openai-file-search.md](./article-rag-openai-file-search.md) — OpenAI公式「File search」。Responses APIのホスト型検索ツールによるVector Store作成・ファイルアップロード手順、対応ファイル形式、検索カスタマイズ、レート制限を解説
- [article-rag-google-cloud-grounded-gen.md](./article-rag-google-cloud-grounded-gen.md) — Google Cloud公式「Generate grounded answers with RAG」。Answer Generation APIの3種の接地ソース（Google Search/インラインテキスト/Agent Search data stores）、動的取得のデフォルトしきい値0.7、レスポンス構成とマルチターン要件を解説
- [article-rag-lewis-2020-arxiv.md](./article-rag-lewis-2020-arxiv.md) — arXiv/NeurIPS2020「Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks」（Lewis et al.）。RAGという名称・アーキテクチャの原典論文。parametric memoryとnon-parametric memoryを組み合わせたモデル構成と3つのQAタスクでの最先端達成を解説
- [article-rag-seven-failure-points.md](./article-rag-seven-failure-points.md) — arXiv/CAIN2024「Seven Failure Points When Engineering a Retrieval Augmented Generation System」（Barnett et al.）。RAGシステムの7つの失敗点(FP1〜FP7)を研究・教育・バイオメディカルの3ケーススタディで実証、検証は実運用時にしか実現できないという結論を解説
- [article-rag-ragas-eval.md](./article-rag-ragas-eval.md) — arXiv/EACL2024「Ragas: Automated Evaluation of Retrieval Augmented Generation」（Es et al.）。reference-free評価フレームワークRagasのFaithfulness・Answer Relevance・Context Relevanceの3指標とWikiEvalでの人間評価一致率を解説
- [article-rag-todoonada-pipeline-guide.md](./article-rag-todoonada-pipeline-guide.md) — TodoONada株式会社。社内文書RAGの精度はパイプライン設計で決まるという立場から「パース→埋め込み→検索→リランク」の4段構成、日本語文書パースの三大障害、ハイブリッド検索の実務標準、規模別構成例を解説
- [article-rag-knowledgesense-retrieval-techniques.md](./article-rag-knowledgesense-retrieval-techniques.md) — Zenn（株式会社ナレッジセンス／門脇篤志）。LlamaIndexのRAGチートシート翻訳・解説。ドキュメント抽出精度を高める7テクニック（チャンク分割最適化・ハイブリッド検索・HyDE・情報構造化・メタデータ付加・ナレッジグラフ・埋め込みファインチューニング）を解説
- [article-rag-qiita-kentarok-poc-production-gap.md](./article-rag-qiita-kentarok-poc-production-gap.md) — Qiita（kentarok）。組織内情報集約RAGのPoCが本番展開で頓挫する根本原因は検証設計・評価の見方のズレにあるという立場から、規程・Wiki・Slack・メールへの分散という組織内情報の構造的課題と、本番展開時に顕在化する5つの失敗パターン（古い情報の使用・最新版の見落とし・矛盾の無視・文書の取り違え・ハルシネーション）を解説

## 動画（AIツール活用：Skills/MCP/CLI/プロンプト）

- [video-tools-webmcp-browser-proposal.md](./video-tools-webmcp-browser-proposal.md) — 「WebMCPとは何か ブラウザ側で動くMCPの提案」（chronoit）。WebサイトがAIエージェントに操作をツールとして構造化公開する仕組みの4要素構成、サーバー側MCPとの役割分担、Cloudflareのベンダー実装、主要AI製品の対応未確認という現状を解説
- [video-tools-google-skills-marketplace.md](./video-tools-google-skills-marketplace.md) — 「【Anthropicの標準にGoogleが乗った】google/skillsで何が変わるのか」（クロノITチャンネル）。109個のSKILL.mdの規模とprogressive disclosure、Claude Codeプラグインmarketplace経由の導入、Apache-2.0ライセンス、Copybaraによる自動運用の実態を解説
- [video-tools-claude-skills-beginner-guide.md](./video-tools-claude-skills-beginner-guide.md) — 「【Claude Skills入門】自分専用のClaude Skillsを作成する方法やSkillsで何ができるのかなどAIのプロがわかりやすく解説します」（いまにゅのAIプログラミング塾）。SKILL.mdのディスクリプション段階読み込み、MCPとのトークン消費差、図解・アルゴリズミックアート・IBスタイルExcelの実演、.skill形式での配布方法を解説

## 記事（AIツール活用：Skills/MCP/CLI/プロンプト）

- [article-tools-agent-skills-overview.md](./article-tools-agent-skills-overview.md) — Anthropic公式「Agent Skills」。Skillsの定義とプロンプトとの違い、Pre-built/Custom Skillsの違い、Level1〜3のprogressive disclosure構造、SKILL.mdのfrontmatter必須要件、セキュリティ上の注意点を解説
- [article-tools-agent-skills-best-practices.md](./article-tools-agent-skills-best-practices.md) — Anthropic公式「Skill authoring best practices」。自由度の3段階設計、gerund形の命名規則、三人称description記述法、SKILL.md500行未満の分割規則、評価駆動開発の5ステップ、MCPツール完全修飾名の必要性を解説
- [article-tools-agent-skills-equipping-real-world.md](./article-tools-agent-skills-equipping-real-world.md) — Anthropicエンジニアリングブログ「Equipping agents for the real world with Agent Skills」。Skills開発の動機とprogressive disclosureの3段階構造、トークン生成よりコード実行が適する場面、信頼できるソース限定というセキュリティ指針を解説
- [article-tools-mcp-architecture-overview.md](./article-tools-mcp-architecture-overview.md) — MCP公式ドキュメント「Architecture overview」。Host/Client/Serverのクライアント・サーバー構造、data layer/transport layerの2層設計、stdio/Streamable HTTPの2 transport、ステートレスなプロトコル設計を解説
- [article-tools-mcp-build-server.md](./article-tools-mcp-build-server.md) — MCP公式クイックスタート「Build an MCP server」。Resources/Tools/Promptsの3大機能、Python版の環境構築とツール実装手順、STDIOサーバーの標準出力書き込み禁止、Claude for Desktopとの接続設定を解説
- [article-tools-claude-code-skill-design.md](./article-tools-claude-code-skill-design.md) — Zenn（yamato_snow）「Claude Code Skillの作り方｜21個運用して分かった設計と育て方」。21個運用の内訳、SKILL.mdのfrontmatter主要フィールド、配置優先順位、/skill-creatorの4モード、よくある失敗パターン4つを解説
- [article-tools-codex-cli-mcp-vs-skill-bash.md](./article-tools-codex-cli-mcp-vs-skill-bash.md) — とつブログ「Claude Code から Codex CLI を呼び出すなら MCP と SKILL/BASH どっちがいい？」。CRUD処理にはMCP・コード生成や長時間タスクにはSKILL/BASH（codex exec）という使い分け、5サーバー58ツールで約55,000トークンという実測値、`codex exec --json`によるプログラム的成否判定と`--full-auto`のリトライ活用を解説

## 動画（RAG）

- [video-rag-history-mechanism-limits.md](./video-rag-history-mechanism-limits.md) — 「検索拡張生成(RAG)とは？LLMの嘘と知識不足を克服する仕組みを歴史から最新技術まで解説」（AIの履歴書）。知識のカットオフとハルシネーションという2課題からの誕生経緯、標準パイプラインの4段階（インデクシング・リトリーバル・ランキング・ジェネレーション）、リコール/プレシジョンのトレードオフ、アドバンストRAG各技術を歴史・仕組み・現状と限界・これからの4章で解説
- [video-rag-supabase-diy-chatbot.md](./video-rag-supabase-diy-chatbot.md) — 「社内文書や個人メモを学習させずに回答させるAIの作り方！SupabaseとClaude/OpenAIで作る自作RAGシステムを解説」（KIZUKI PROJECT）。RAGの3ステップ・ベクトルDBの仕組みを説明したうえで、Claude CodeとSupabase Vectorで約15分で自作RAGチャットボットを構築するハンズオン実演
- [video-rag-sme-adoption-guide.md](./video-rag-sme-adoption-guide.md) — 「RAG（検索拡張生成）とは？」（株式会社文武堂）。中小企業向けにRAGの仕組み・SSOT/GIGOの2鉄則・導入の4レベル・無料版のリスク・「運用して育てる」考え方を解説
- [video-rag-ragflow-oss-intro.md](./video-rag-ragflow-oss-intro.md) — 「RAGFlow入門｜社内文書を答えるAIに変えるオープンソースRAGエンジン」（さつきのOSS研究室）。OSS RAGエンジンRAGFlowの機能・LangChain/LlamaIndex/Difyとの違い・Apache 2.0ライセンス・3つの導入事例を解説
- [video-rag-ollama-local-privacy.md](./video-rag-ollama-local-privacy.md) — 「社内文書を外に出さずAIに検索させる、Ollamaローカル型RAGの作り方【ずんだもん解説】」（ずんだもんのAI図鑑）。取り込み・分割・ベクトル化・検索・生成の5段階を手元PCで完結させる構成、会話用LLMと埋め込みモデルの役割の違い、RAGとエージェントの違いを解説

## 動画（AIコーディング実務）

- [video-coding-vibe-coding-qa-followup.md](./video-coding-vibe-coding-qa-followup.md) — 「【コメント返し】バイブコーディング超入門動画への質問・疑問に回答します」（安野貴博）。CLAUDE.mdへのルール記載・自動テストによる品質担保・ローカル実行時のセキュリティリスク・クロードの料金プランなど視聴者からの質問に回答
- [video-coding-git-github-5-operations.md](./video-coding-git-github-5-operations.md) — 「【バイブコーディング超入門講座第5回】初心者向けGit&GitHub解説」（安野貴博）。Git/GitHubの役割の違いと、ブランチ・コミット・プッシュ・プルリクエスト・プルの5操作をセーブポイントの比喩で解説、クロードコードでの実演あり
- [video-coding-git-pr-conflict-practice.md](./video-coding-git-pr-conflict-practice.md) — 「【バイブコーディング超入門講座第6回】GitやGitHubはもう怖くない！？Claude Codeで楽々つかえるGit&GitHubの使い方！」（安野貴博）。リポジトリ作成からコミット・プッシュ・プルリクエスト、2ブランチが同じ行を変更した際のコンフリクト解決までをClaude Code越しに実演
- [video-coding-database-supabase-safety.md](./video-coding-database-supabase-safety.md) — 「【バイブコーディング超入門講座第7回】アプリにデータ保存機能を追加するには？」（安野貴博）。データベースの基本をExcelに例えて解説し、Supabase（BaaS）の紹介と、AIに本番データを壊されないための「壊さない意識」・DELETE/UPDATE/WHEREの注意・SELECT事前確認・環境分離・バックアップの実践を解説

## 記事（AIコーディング実務）

- [article-coding-codex-best-practices.md](./article-coding-codex-best-practices.md) — OpenAI公式「Best practices for Codex」。プロンプトの4要素（Goal/Context/Constraints/Done when）、AGENTS.mdによる恒久ルールの外部化、権限の保守的運用、MCP/Skills/スケジュールタスクの活用、よくある誤り8種を解説
- [article-coding-codex-prompting-guide.md](./article-coding-codex-prompting-guide.md) — OpenAI公式「Codex Prompting Guide (GPT-5-Codex)」。計画ツールを省略してよい下位25%の基準、preamble（前置き発言）の頻度と口調規定、フロントエンド生成の「AI slop」回避方針、冗長な繰り返し編集を避ける行動原則を解説
- [article-coding-msft-cli-agent-adoption.md](./article-coding-msft-cli-agent-adoption.md) — arXiv（Microsoft Research）「Adoption and Impact of Command-Line AI Coding Agents」。Microsoft社内での2026年前半のClaude Code/Copilot CLI導入で、社会的露出が採用の最大予測因子であること、合成対照分析によるマージPR数24.0%増加とCopilot CLIがClaude Codeの2.2倍の効果を示したという成果分析を解説
- [article-coding-copilot-issues-study.md](./article-coding-copilot-issues-study.md) — arXiv「Exploring the Problems, their Causes and Solutions of AI Pair Programming」。GitHub Issues・Discussions・Stack Overflow計1,324件を分析し、Operation Issue（機能障害・認証エラー等）が57.5%を占めると報告、原因はCopilot内部エラー19.4%が最多、ユーザーへの提言としてレビュー励行とインスピレーション源としての活用を解説
- [article-coding-qiita-team-rollout-pitfalls.md](./article-coding-qiita-team-rollout-pitfalls.md) — Qiita「チーム開発でClaude Codeを3ヶ月運用して分かった『壊れるポイント』と『仕組み化のコツ』」。エンジニア5名のチームが直面したCLAUDE.md属人化・トークンコスト3倍膨張・信頼バイアスによる本番障害という3つの崩壊パターンと、3層レイヤー分離・トークン予算可視化・AI生成コード専用レビューチェックリストによる仕組み化、3ヶ月後の定量的改善を解説
- [article-coding-plex-local-review-gate.md](./article-coding-plex-local-review-gate.md) — PLEX Product Team Blog「ローカルの Claude Code レビューを『すり抜けられない』必須チェックにした話」。コスト削減のためローカルで実行するClaude CodeレビューがGit hook未設定を検知できない弱点を、git notes・commit status・branch protectionでリモート側から証跡検証する仕組みにより構造的に塞いだ実装と、レビュー品質自体は保証しないという明示された限界を解説
- [article-coding-zenn-smartshopping-6points.md](./article-coding-zenn-smartshopping-6points.md) — Zenn（SmartShopping）「AIコーディングで失敗しまくった私が学んだ、効率的にAIを使うための6つのポイント」。バリデーション追加指示の空振り・保守困難なコード・段階的追加による重複コード乱立という3つの失敗例と、そこから導いた実装機能の理解／既存コード理解／事前調査／実装範囲の明確化／計画立案／入出力の明確化という6つの実践ポイントを解説

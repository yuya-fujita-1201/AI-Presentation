# 変更履歴

## 2026-08-14（続き）

- **Fix**: prompt-engineering/ の採点指摘4件を修正（improve_k工程 run:0814042504、findings 4件中fixed 2件・rejected 1件・deferred(out_of_scope) 1件）。modern-model-prompting.mdのL55（effort運用指針／API仕様変更／5段階からの推論の3論点が1段落に密集）とL71（既存プロンプト互換／long-horizon特性／完全仕様の推奨／オフィス業務の4論点が1段落に密集）を指摘単位で段落分割、five-engineering-stages.mdのL15（「もう古い」への言及）を簡潔化しL67（同テーマの反論）へ理由を集約、loop-engineering.mdのL15にfive-engineering-stages.mdへの参照リンクを追加。1件（ダッシュの「冒頭配置」・太字の「同じ位置」という指摘）は全8ファイルのL13前後を実読した結果、ダッシュは全て文中・文末位置で冒頭配置ではなく、太字も1〜2箇所とファイルごとにばらつきがあり指摘の前提が事実と異なるためrejected。1件（採点対象一覧pipeline/staging/lists-081403591d/grade-files.txtに既存バンドル比較対象が含まれない指摘）はknowledge/配下の修正対象スコープ外のためdeferred

## 2026-08-14

- **Fix**: prompt-engineering/ の採点指摘9件を修正（improve_k工程 run:0814032515、findings 9件全件fixed、うち1件は部分対応）。modern-model-prompting.mdのeffort節にthinking既定有効・effort無効時の上限high制限というAPI仕様変更とeffort 5段階構造への言及を追加、同ファイルの「削る」節にlong-horizon agentic tasksへの強み・スタブなし完了という中核的位置づけを追加、loop-engineering.mdに計画5〜10分・レート制限・必要スキル・黎明期である旨を追加、article-pe-claude-prompting-best-practices.mdの活用先を修正（ゴールデンルール等をprompt-anatomy.md行からcore-techniques.md行へ移設、modern-model-prompting.md行を追加）、article-pe-qiita-kissy24-methods.mdの活用先にtaxonomy-and-landscape.md行を追加、loop-engineering.md:76のリンクテキストを「5つのエンジニアリング」に統一、five-engineering-stages.md:37の「4要素」を「4つの観点」に変更しプロンプトの4要素との別概念である旨を明記、8ファイルに広がる「実務／SIに置き換えると腑に落ちる」型の引き寄せ段落を3箇所削除・簡潔化し太字強調過多の4ファイル（taxonomy/five/loop/modern）で地の文中の過剰な強調を削減（太字数の目標水準ファイルあたり3〜5箇所には未到達、用語定義・重要結論の可読性を優先し部分対応）

## 2026-08-13（さらに続き2）

- **Fix**: prompt-engineering/ の採点指摘11件を修正（improve_k工程 run:0813224586、findings 11件中fixed 10件・deferred(out_of_scope) 1件）。taxonomy-and-landscape.mdにSahooのプロンプト定義（ベクトル表現を含む）をThe Prompt Reportのsoft prompts除外と対比する形で追加・実務者向け参照先としてPrompt Engineering Guideの推薦を追加・「41と58の違いは矛盾ではない」直前の配信経路同一性から独立性への論理接続を補って書き直し、five-engineering-stages.mdに配信者独自の予測（AGIエンジニアリング・音声入力プロンプトエンジニアリング・AI工房）を末尾に追加、modern-model-prompting.mdにベストプラクティス記事の全モデル共通適用宣言との対比・22パターン比較検証の型を数値より長持ちする構造として追加、why-context-matters.md/taxonomy-and-landscape.mdの「次に読む」先頭に index.md の推奨読了順で直後に来るファイルを追加、what-is-prompt-engineering.mdのKDDI活用シーン4項目の詳細列挙を1文に圧縮、loop-engineering.md（42→16）とmodern-model-prompting.md（36→12）の太字強調を節あたり1〜2箇所に削減し引用・部品名列挙からは除去、5ファイルにまたがるヘッジ表現の反復（「のが妥当だろう」「のが安全だろう」「押さえておきたい」計7件）を具体的理由を書く形へ置換し全体で1件まで削減。1件（採点対象一覧pipeline/staging/lists-0813201530/grade-files.txtに既存バンドル比較対象が含まれない指摘）はknowledge/配下の修正対象スコープ外のためdeferred

## 2026-08-13（FEILERデザインノウハウ移植）

- **Creation**: slide-system/deck-design-grammar.md を追加。FEILER案件デッキ（feiler-hypotheses-ai, 35枚）で確立したコンサル調のデザイン文法（ヘッダー4点セット・eyebrow・意味を持つ第二パレット・全面SVG図版の規約・layout_overrides実例・検証の型）を移植
- **Update**: tools/build_deck.py に FEILER 側拡張をマージ（`eyebrow` フィールド、`style.table.row_fills` 行単位背景色、`meta.brand` 全ページ右上ブランドマーク、`style.footer_r.text` によるページ番号上書き。HTML+PPTX両対応・後方互換）。tools/preview_deck.py にスクリーンショット時の HUD/ノート非表示化を移植
- **Update**: templates/layouts/default.json の6タイプ（bullets/two_column/table/code/image/image_text）に `eyebrow` 領域を追加。templates/themes/ に `feiler-bright` と `cytra-wine` を追加
- **Update**: docs/deck-schema.md に `brand` / `eyebrow` / `row_fills` / `footer_r.text` を追記。slide-system/index.md に新文書の導線を追加

## 2026-08-13（さらに続き）

- **Fix**: prompt-engineering/ の採点指摘8件を修正（improve_k工程 run:08131916a1、findings 8件全件fixed）。loop-engineering.mdに5+1の部品が実際に組み上がった一例としてエピックフロー/移ローの実装節を追加、five-engineering-stages.mdのハーネス/ループ/グラフ各層に実例（Claude Codeの権限・自動読込・承認フロー、ビジョン確認/Excel再計算/文字数超過削るループ、AI100ライター/LPビルダー）を追加し「4段階か5段階か」節末に../graph-engineering/term-lineage-and-layers.mdへの導線を追加、modern-model-prompting.mdに一次パス+二次パスの2段構えレビューとvision×tool useの指針を追加、what-is-prompt-engineering.mdの活用シーン1段落を箇条書き4項目に分割しOpus 5のオフィス業務記述をmodern-model-prompting.mdへ移設（article-pe-claude-opus-5-prompting.mdの活用先も追随して更新）、prompt-anatomy.mdの「書き方のコツ」節を3項目再掲からcore-techniques.mdへの送り出しのみに整理しQiitaコツの重複を解消、taxonomy-and-landscape.md/five-engineering-stages.mdの冒頭導入を「あるある」型から定義から入る型/事例から入る型に変更し「つまり」締めの重複3箇所を言い換え

## 2026-08-13（続き）

- **Fix**: prompt-engineering/ の採点指摘8件を修正（improve_k工程 run:08131902bd、findings 8件全件fixed）。core-techniques.mdに「Instructions（命令）」を土台の技法名として追記しsios入門記事の活用先を追加、what-is-prompt-engineering.mdの活用シーンにセールスコピー生成・文体調整の例を追加、modern-model-prompting.mdの「8割削っても落ちない」節に自動メモリ・doctorコマンドという削る具体手段を追加しeffort節に用途別モデル使い分け（専門タスクはFable5・厳しい評価が必要な用途もFable5）を追加、core-techniques.mdの技法数の数え方（冒頭4つ/列挙5項目/末尾5つ）を「土台1つ＋技法4つ」で統一、core-techniques.mdとarticle-pe-pe-survey-sahoo.mdの非文「影響を与えうり」を「影響しうる」に修正、prompt-anatomy.mdの「書き方のコツ」節（他ファイルへの転送1文のみ）を要点3つ再掲する形に修正、article-pe-claude-prompting-best-practices.mdのdescription「4つの手法」と本文「3つの補助的な技法」の数え方不一致を統一し孤立表記「Claude Mythos 5」をバンドル内統一表記「Fable 5」に修正

## 2026-08-13

- **Creation**: prompt-engineering/ を新設（knowledge工程 run:081316062a / 0813181688）。sources/ の台帳12本（学術サーベイ2本・入門記事3本・Anthropic公式2本・YouTube解説動画5本）を情報源に、8コンセプトを追加（what-is-prompt-engineering / prompt-anatomy / core-techniques / why-context-matters / taxonomy-and-landscape / five-engineering-stages / loop-engineering / modern-model-prompting）。読者像は「チャット型AIの利用経験はあるがエージェント的活用は未経験の新入社員・ITコンサル・SE」。auto字幕のみを出所とする impact:high の主張（100万トークン、価格半額、システムプロンプト8割削除、ベンチマーク数値、人名など）はすべて帰属を明示し断定を避けた。人名表記が2つの動画で食い違う点（ピーター・バーガー／スタインバーガー、ボリス・チェルニー／カーニー）、5段階説と4段階説の差異も本文に明記
- **Update**: sources/ の台帳12本すべてに「活用先」の逆リンクを追記（コンセプト⇄台帳の双方向リンクを tools/validate_okf.py と自作クロスチェックで検証、不一致0件）
- **Update**: ルート index.md に prompt-engineering/ の項目を追加

- **Creation**: sources/ に記事1本を article-pe-*.md として登録（プロンプトエンジニアリングテーマ、日本語Web記事、web_ledger工程 run:08131602b6）。article-pe-sios-prompt-engineering-intro.md（サイオステクノロジー株式会社「初心者必見！プロンプトエンジニアリング入門ガイド ~基礎編~」、NRIの定義とダイエット相談の具体例、OpenAI社セッションによる重要性の裏付け、プロンプトの続きを予測する性質、Instructions（命令）テクニックの基礎を解説）
- **Update**: sources/index.md の「記事（プロンプトエンジニアリング）」節に上記1件を追加

- **Creation**: sources/ に記事2本を article-pe-*.md として登録（プロンプトエンジニアリングテーマ、日本語Web記事、web_ledger工程 run:0813155760）。article-pe-kddi-prompt-basics.md（KDDI株式会社「プロンプトとは？種類や作成方法、具体的なプロンプト例を紹介」、語源とAI時代の意味の広がり、命令・補完・実演の3類型、社内版ChatGPT「KDDI AI-Chat」の活用事例）、article-pe-qiita-kissy24-methods.md（Qiita「【生成AI】サクッと学ぶプロンプトエンジニアリング手法」、Instruction/Context/Input Data/Output Indicatorの4要素構成、記載フォーマット3種、ロールプレイ・Zero-shot Promptingの解説）
- **Update**: sources/index.md の「記事（プロンプトエンジニアリング）」節に上記2件を追加

- **Creation**: sources/ に記事2本を article-pe-*.md として登録（プロンプトエンジニアリングテーマ、arXiv論文、web_ledger工程 run:0813155352）。article-pe-prompt-report.md（Schulhoff et al.「The Prompt Report」、PRISMAベースの系統的レビューによる58技法・33用語の分類体系、多言語・マルチモーダル・エージェント・評価・安全性への拡張、2つのケーススタディ）、article-pe-pe-survey-sahoo.md（Sahoo et al.「A Systematic Survey of Prompt Engineering in Large Language Models」、41種類以上の技法のアプリケーション別タキソノミー、Zero-Shot/Few-Shot Promptingの解説）
- **Update**: sources/index.md の「記事（プロンプトエンジニアリング）」節に上記2件を追加

- **Creation**: sources/ に記事2本を article-pe-*.md として登録（プロンプトエンジニアリングテーマ、Anthropic公式ドキュメント、web_ledger工程 run:081315481f）。article-pe-claude-prompting-best-practices.md（明確で直接的な指示・文脈の追加・few-shot例の設計・XMLタグによる構造化の4原則）、article-pe-claude-opus-5-prompting.md（Opus 4.8比の性能差分に基づくOpus 5向けプロンプト設計パターン）
- **Update**: sources/index.md に「記事（プロンプトエンジニアリング）」節を新設し上記2件を追加

- **Creation**: sources/ に動画1本を video-pe-loop-engineering-5plus1-parts.md として登録（プロンプトエンジニアリングテーマ、RUNTEQチャンネル、字幕全文から要約・主張テーブルつき）。プロンプト→コンテキスト→ハーネス→ループの段階変遷、インナー/アウターループの2層構造、ループを構成する「5+1の部品」、自作のエピックフロー／移ローの実装とモデル使い分けを整理
- **Update**: sources/index.md の「動画（プロンプトエンジニアリング）」節に上記1件を追加

- **Fix**: prompt-engineering/ の採点指摘6件を修正（improve_k工程 run:08131833ae、findings 6件中5件fixed・1件deferred(out_of_scope)）。modern-model-prompting.mdのeffort判断基準を両ソースの食い違いが分かるよう修正、what-is-prompt-engineering.mdのQiita記事の格付け誤り（「ベンダー解説」→「技術者による個人投稿」）を修正、five-engineering-stages.md/loop-engineering.md/what-is-prompt-engineering.mdに未収録だった具体例（モデル使い分け・秘書業務応用・KDDI活用シーン/Opus5オフィス業務）を追記、core-techniques.md/index.mdの技法数の予告と本文の食い違い（4型→5型に統一）を修正、バンドル内の重複説明6ペアをそれぞれ正本1ファイルに統合し他方を要約+相対リンクに置換。採点対象一覧にokf/・graph-engineering/が含まれない指摘はpipeline設定ファイルの変更が必要なためこの工程では対応不可としdeferred

## 2026-08-12

- **Creation**: sources/ に動画2本を video-pe-*.md として登録（プロンプトエンジニアリングテーマ、字幕全文から要約・主張テーブルつき）。video-pe-loop-engineering-overview.md（安野貴博の自由研究、プロンプト/コンテキスト/ハーネス/ループの4段階とHuman on the Loop）、video-pe-opus-5-prompt-tips.md（にゃんたのAIチャンネル、Opus5のベンチマーク比較とプロンプト運用のコツ）
- **Update**: sources/index.md に「動画（プロンプトエンジニアリング）」節を新設し上記2件を追加
- **Creation**: sources/ に動画2本を追加登録（同テーマ、keitoaiwebチャンネル、字幕全文から要約・主張テーブルつき）。video-pe-opus-5-benchmark-tips.md（219ページ資料と22パターンの実践比較検証、公式ベストプラクティスに基づくOpus5向けプロンプトのコツ）、video-pe-five-engineering-stages.md（プロンプト/コンテキスト/ハーネス/ループ/グラフ5つの全体マップと「入れ子」構造の整理）
- **Update**: sources/index.md の「動画（プロンプトエンジニアリング）」節に上記2件を追加

## 2026-08-09

- **Creation**: graph-engineering/ を新設。YouTube解説動画11本（グラフエンジニアリング関連、2026年7〜8月公開）を情報源に、9コンセプトを追加（overview / term-lineage-and-layers / graph-primitives / loop-vs-graph-decision / roles-and-orchestration / relationship-graph-for-operations / verification-and-testing / knowledge-graph-as-memory / risks-and-safeguards）
- **Creation**: sources/ に動画11本を video-ge-*.md として登録（1ソース=1ファイル、字幕全文から要約・「活用先」リンクつき。自動字幕の誤変換は正規化し、聞き取り不確実箇所とソース間の数値食い違い（Bun書き換え行数53万/75万、explainX発表時期など）は明記）
- **Update**: ルート index.md と sources/index.md に graph-engineering 系の項目を追加
- **Creation**: decks/graph-engineering/ を新設（29枚、テーマ accenture-purple、全スライドにHTML用スピーカーノートつき）。構成は「序（用語誕生の事件）→ 地図 → 基本語彙 → ループかグラフか → 配線と検証 → 歯止め → 3フレーム+1原則」
- **Process**: 制作はダイナミックワークフロー3本（Digest 11並列 → Architect 3案合議 → Judge統合／コンセプト執筆9並列+リンク追記11並列／デッキ構成3案合議 → 審査統合）で実施。品質はループエンジニアリング（maker≠grader・機械ゲート・rubric採点、独立採点5体×3周）で担保し、ナレッジ 36→38→44/50、デッキ 51/60 で全rubric項目が目標（各8点）達成。活用先⇄Citations の双方向整合は自作クロスチェックで0件不一致。詳細は ../loop-log.md
- **Tooling**: tools/validate_okf.py を追加（フロントマター/type必須・リンク切れ・index網羅・okf_version の機械検証ゲート）

## 2026-08-06

- **Creation**: slide-system/ を新設（パラメーター駆動の資料作成システムのナレッジ3コンセプト）。参考動画「編集ソフトも動画生成AIも使わずに解説動画を作る」を sources/video-json-driven-video-production.md として取り込み・検証済み

- **Update**: 公式仕様書 SPEC.md (v0.2) を一次情報として確認し、`sources/spec-okf-v02.md` として登録。動画由来だった v0.2 フィールド名を仕様準拠の表記（`sources` / `generated` / `verified` / `status` / `stale_after` / `okf_version`）に修正（v02-changes / directory-structure / file-format）
- **Update**: バンドル自体を v0.2 準拠へ移行。ルート index.md に `okf_version: "0.2"` を宣言し、全ファイルの `timestamp` を `generated: { by, at }` に置換
- **Update**: 動画6本の内容を取り込み、要約を拡充。コンセプトへ統合（新規コンセプト v02-changes.md を追加、overview / design-principles / directory-structure / file-format / ecosystem / practice-tips を更新）
- バンドル初版を作成
- okf/ に OKF の概要・設計原則・ファイル形式・ディレクトリ構造・エコシステム・実践Tips の 6 コンセプトを追加
- sources/ に初期資料 11 件（YouTube 動画 6 本、記事 5 本）を登録

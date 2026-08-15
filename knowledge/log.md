# 変更履歴

## 2026-08-16（geソース台帳・動画1本 research_ledger run:0816034527）

- **Creation**: sources/ に動画1本を video-ge-subagent-overview-basics.md として登録（グラフエンジニアリングテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:0816034527）。まさやん【AIギルドch】「【前編】Claude Codeサブエージェント完全ガイド｜全体像・基本機能・メリットを徹底解説」（38分29秒、自動字幕）。サブエージェントの定義とコンテキスト独立性、フロントマターの全設定項目（name/description必須・tools/disallowedToolsの拒否リスト優先仕様・実行制御系・拡張統合系）、4通りの呼び出し方法とコンテキスト管理の仕組み、Anthropic公式ブログを引用した役割分離（プランナー/ジェネレーター/エバリエイター）による品質向上、並列実行で8分→3分未満に短縮された事例、ネスト不可などの制約事項、Claude Codeの機能体系（実行主体/能力/ルール環境）における位置付けを解説
- **Update**: sources/index.md の「動画（グラフエンジニアリング）」節に上記1件を追加

## 2026-08-16（geソース台帳・動画2本 research_ledger run:0816030875）

- **Creation**: sources/ に動画2本を video-ge-*.md として登録（グラフエンジニアリングテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:0816030875）。video-ge-subagent-when-to-use.md（にゃんたのAIチャンネル「How to use ClaudeCode and Codex subagents!」、30分49秒。Googleの研究者によるという実験論文を引用し、シングルエージェント単体の精度が約45%を超えるタスクにエージェントを追加するとネガティブリターンになるという損益分岐点、ファイナンスエージェント対プランクラフトでの並列分割可否による明暗、配信者自身が実践する3つの活用法（並列調査・忖度回避・作成検証ループ）を解説）、video-ge-dynamic-workflows-six-patterns.md（みにこーへいのAI活用チャンネル「【Claude Code新機能】Dynamic Workflows完全解説」、99秒。分類振り分け・ファンアウト・敵対的検証・生成篩い落とし・トーナメント・終了判定の6つの編成パターンと、プロンプトに「ウルトラコード」と書くだけの使い方、トークン予算指定の方法を解説）
- **Update**: sources/index.md の「動画（グラフエンジニアリング）」節に上記2件を追加

## 2026-08-15（シリーズ完走・スケジューラ解除）

- **Milestone**: pe→ce→he→le の4テーマすべてが完走。le（ループEG）のデッキ採点が 8/9/9/8/8/9 で2連続合格し、`docs/codex-brief-ai-eng-04-loop-engineering.md` を発行（run:081518579f / commit db0ea82）。パイプラインは `pipeline/PAUSE`（理由: シリーズ完走）で自動停止し `phase: done`
- **Ops**: ユーザー判断により launchd の定期実行を解除（`launchctl bootout gui/501/com.yuyafujita.presentation-pipeline`）。plist は `~/Library/LaunchAgents/` に残置。再開する場合は `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuyafujita.presentation-pipeline.plist` を実行し、新テーマを `pipeline/themes/` に追加のうえ `pipeline/PAUSE` を削除する
- **Status**: ナレッジ蓄積の到達点 — prompt-engineering 9 / context-engineering 12 / harness-engineering 9 / loop-engineering 11 コンセプト、ソース台帳 80本

## 2026-08-15（le ナレッジ完成・manual_override受理）

- **Add**: loop-engineering に10コンセプト（ループEGとは/プロンプトからループへ/ループの解剖/目標と停止条件/検証の設計/maker-checker分離/self-refineとevaluator-optimizer/ループの部品とハーネス/いつ使うか/リスクとコスト）。ソースは新規台帳9本＋既存共有4本（pe/geのループ動画）の計13本
- **Note**: 採点4周 8/7/8/7/7 → 7/7/8/8/7 → **8/8/8/9/7** → 9/8/7/8/7。①事実正確性は最終9点、④リンクは9点まで到達。③構成と⑤文章品質が採点者間で揺れ repair上限に到達したため、最良周の水準で manual_override 受理しdraftへ

## 2026-08-15（採点指摘の修正・improve_k run:0815130695）

- **Fix**: findings-k.json 9件すべてをfixedとして修正。①`index.md`のソース本数「解説動画4本」を実数の「5本」に訂正（記事8本と合わせ計13本は正しかった）②`goal-and-stop-conditions.md`にMastra Goals機能（judge/maxRuns=30/promptの3要素とexperimental注記）をClaude Code以外の実装例として追記③`anatomy-of-a-loop.md`のアウターループ節にエピックフローの実装例（プランナー分解→人間承認→タスク実行→マージ→最終PR確認）を追記④`what-is-loop-engineering.md`のHOTL節後にKarpathy氏の「オートリサーチ」をコーディング以外の自律改善実例として聞き取り留保つきで追記⑤`when-to-use-loops.md`に非開発業務への応用例（日程調整・会議後のタスク洗い出し）とチーム横断の標準化を追記、`verification-design.md`に「視覚的な成功判定」を追記⑥`goal-and-stop-conditions.md`のハードストップ節に「安全な作業環境」を追記し`loop-parts-and-harness.md`からの参照切れを解消⑦`goal-and-stop-conditions.md`の`/goal`と`/loop`の区別節ににゃんたのAIチャンネル動画への参照を追加⑧`goal-and-stop-conditions.md`の「小さく始める」節を`when-to-use-loops.md`側への1文＋リンクに縮約し二重展開を解消⑨3つの引用の重複（「検証が甘いと〜垂れ流す」「アサーションを1行こっそり消して」「少しずつ制約をつけていく」）をそれぞれ主担当ファイル1つに統一し他方を要約+リンクに縮約。関連する6ソースファイルの活用先にも対応する行を追加。OKF検証 errors:0 / warnings:0
- **Note**: findings 9件の内訳はfixed 9件、deferredなし。詳細は outbox（`pipeline/state/outbox/result-0815130695.json`）参照

## 2026-08-15（loop-engineering コンセプト10本 knowledge工程）

- **Creation**: `loop-engineering/` を新設。ソース台帳13本（動画4本・記事8本＋Anthropic公式2本を含む）を情報源に、コンセプト10本を追加（what-is-loop-engineering / from-prompt-to-loop / anatomy-of-a-loop / goal-and-stop-conditions / verification-design / maker-checker-separation / self-refine-and-evaluator-optimizer / loop-parts-and-harness / when-to-use-loops / risks-and-costs）。想定読者はチャット型AIの利用経験はあるがエージェント的活用は未経験の層。中核主張は出所の異なる2origin以上で支持させ、単一ソースの主張は「〜としている」と帰属を明示、auto字幕由来の主張は「（聞き取り）」を併記する方針で執筆
- **Creation**: `loop-engineering/index.md` を作成（内容一覧と推奨読書順。時間がない場合の3本ルートも記載）
- **Update**: 台帳13本の「# 活用先」に、各コンセプトからの参照理由を追記（コンセプト側の出典インラインリンクと双方向で対応）
- **Update**: ルート index.md に `loop-engineering/` を追加
- **Process**: 執筆は knowledge工程を4ランに分割して実施（run:081512243f・08151231ac・08151240b1・08151249f4）。plan.json（`pipeline/staging/knowledge/plan.json`）にコンセプト設計とsources割り当てを保持し、ランをまたいで status: todo→done で引き継ぐチェックポイント方式。最終ランで `tools/validate_okf.py knowledge` による機械検証と、コンセプト⇄台帳の双方向リンク自己照合を実施

## 2026-08-15（leソース台帳・記事2本 web_ledger run:0815121336）

- **Creation**: sources/ に記事2本を article-le-*.md として登録（ループエンジニアリングテーマ、web_ledger工程 run:0815121336）。article-le-qiita-syoitu-loop-engineering.md（Qiita「入門から実践 -「🔁 ループエンジニアリング」」Syoitu、二次情報。Addy Osmaniの定義「Loop engineering is replacing yourself as the person who prompts the agent」の引用、ループを構成する5つのアクション（発見・受け渡し・検証・記憶・スケジューリング）と6つのパーツ（Automations・Worktrees・Skills・Connectors/MCP・Sub-agents・Memory）、Claude Codeでの3ファイル実装（CLAUDE.mdの停止条件「全チェック通過」「最大5回」「同じエラー2回連続」と禁止事項、settings.jsonのStop/PostToolUseフック、fixerサブエージェントの「推測は禁止」条件）、Mastra Goals機能のjudge/maxRuns/prompt、回しっぱなしの代価4リスクを解説）、article-le-note-masawunder-goal-loop-design.md（note「Claude Code ループエンジニアリング入門 /goal・/loopの使い分けと停止条件の設計」masa_wunder、二次情報。「公式が定義した『ループ』の核心は停止条件」という位置づけ、人の関与度によるターン駆動・ゴール駆動・時間駆動・自律駆動の4分類、/goal（ゴール駆動）と/loop（時間駆動）の定義の違い、著者自身の「停止条件を1つだけにした時は失敗しました」という失敗談から品質スコア・最大12イテレーション・最大360分の3重構成に至った経緯、段階的導入の3ステップとトークン管理の確認方法、「賢くお願いする」から「止まり方まで含めて任せる」への総括を解説）
- **Update**: sources/index.md の「記事（ループエンジニアリング）」節に上記2件を追加

## 2026-08-15（leソース台帳・記事2本 web_ledger run:08151159f1）

- **Creation**: sources/ に記事2本を article-le-*.md として登録（ループエンジニアリングテーマ、web_ledger工程 run:08151159f1）。article-le-kilo-loop-engineering-definition.md（Kilo「What Is Loop Engineering? AI Feedback Loops」、二次情報。loop engineeringを「AIコーディングエージェントが計画立案・コード変更・結果観察・アプローチ修正を繰り返すフィードバックループの設計・運用・改善の実践」と定義する原文引用、Intent・Context・Action・Observation・Adjustmentの5段階モデル、プロンプトエンジニアリングとの対比表（「良い最初の回答」対「良い最終成果」、失敗モードの違い）、Test-Driven/Compiler-Driven/Review-Driven/Runtime Debugging/Product Iterationの5実践パターン、「テストの失敗は単なるエラーメッセージではなく新たな文脈情報である」という教訓と組織的な再現性標準の必要性を解説）、article-le-zenn-maker-checker-practice.md（Zenn「Claude Code で『ループエンジニアリング』を実践してみた」tetsu_don、二次情報。/spec-review・/code-reviewをMaker-Checker対応に再設計しレビュー役のtoolsからWrite・Editを外すことで修正権限を剥奪した設計、openBD書籍価格チェッカーを検証題材とした3パターンのエラー検証、「想定内の異常系か本当のバグかを判定する」性質判定ステップを最優先に組み込んだ理由、str.isdigit()が全角数字を誤判定していた実バグの修正とpytest 63件全パス、incident-checkerが独立コンテキストでゼロからやり直すことによる自己採点バイアス防止効果、単一プロジェクト専用実装から複数プロジェクト横断のレジストリ設計への今後の課題を解説）
- **Update**: sources/index.md の「記事（ループエンジニアリング）」節に上記2件を追加

## 2026-08-15（leソース台帳・記事2本 web_ledger run:08151148d9）

- **Creation**: sources/ に記事2本を article-le-*.md として登録（ループエンジニアリングテーマ、web_ledger工程 run:08151148d9）。article-le-self-refine.md（arXiv「Self-Refine: Iterative Refinement with Self-Feedback」Madaan et al.、一次情報。人間の推敲プロセスに着想を得て同一LLMが生成器・批評者・改善者を兼ねる3ステップの反復ループ、追加の教師データ・追加学習・強化学習を要しない設計、対話応答生成〜数学的推論の7タスク×GPT-3.5/ChatGPT/GPT-4で人手評価・自動評価とも平均約20%の絶対的改善、loop engineeringで頻繁に参照される「自己改善ループ」の原典としての位置づけ、RCI・CRITIC・Self-Correct等の後続研究の起点であることを解説）、article-le-loop-engineering-mindstudio.md（MindStudio「What Is Loop Engineering? The New Meta for Autonomous AI Agent Workflows」、二次情報。単一ターン依存の従来AIワークフローとの対比からloop engineeringを観察・推論・行動・評価の反復と定義、/loop（有界・条件付き反復）・/goal（成功条件と終了判定）・/routines（再利用可能なアクション配列）の3構成要素、ゴール未定義のままループから着手する失敗パターンへの警句、Self-Refineをloop engineeringの実装例とする位置づけ、多段階・条件付き・完了時間不定・人間レビューがボトルネックという適用条件を解説）
- **Update**: sources/index.md の「記事（ループエンジニアリング）」節に上記2件を追加

## 2026-08-15（leソース台帳・記事2本 web_ledger run:08151142ae）

- **Creation**: sources/ に記事2本を article-le-*.md として登録(ループエンジニアリングテーマ、Anthropic公式ドキュメント、web_ledger工程 run:08151142ae)。article-le-claude-code-best-practices.md(Claude Code Docs「Best practices for Claude Code」の「Give Claude a way to verify its work」節。合否判定可能なチェック(テスト・ビルド・スクリーンショット比較)を与えると実行→検証→反復のループが自律的に閉じるという主張、Before/After形式の3適用例(検証基準の明示・UI視覚検証・根本原因対処)、チェックの強制力を段階的に高める4段階(単発プロンプト内反復・/goalコンディション・Stopフックの決定的ゲート・検証サブエージェントによるセカンドオピニオン)、成功を自己申告させず証拠(evidence)を提示させる推奨を解説)、article-le-evaluator-optimizer.md(Claude Cookbook「Evaluator optimizer」。生成担当と評価担当のLLM呼び出しを分離するワークフローの定義、有効な場面の2条件と適合の2兆候、generate/evaluate/loopの3関数によるPythonリファレンス実装(docstring・thoughts/response・evaluation/feedbackタグ抽出・PASSになるまでmemoryとフィードバックを積み増す構造)を解説)
- **Update**: sources/index.md に「記事（ループエンジニアリング）」節を新設し上記2件を追加

## 2026-08-15（leソース台帳・動画1本 research_ledger run:0815112138）

- **Creation**: sources/ に動画1本を video-le-loop-design-four-points.md として登録（ループエンジニアリングテーマ、まさおAIじっくり解説chチャンネル、字幕全文から要約・主張テーブルつき、research_ledger工程 run:0815112138）。「【必見】AIエージェントは『ループ設計』の時代！完全自律で回す5つのポイント含め解説します」。ループ設計の4つのポイント（ゴール明確化・エージェント割当・進捗検証・継続条件判定）と、Claude Codeの中の人（ボリス氏）によるロングラン自律動作のための5つの技術（オートパーミッション・動的ワークフロー・ループコマンド・自己検証ツール・Ralph Loop）、「ゴール」と「ループ」の概念上の違いを解説
- **Update**: sources/index.md に「動画（ループエンジニアリング）」節を新設し上記1件を追加

## 2026-08-14（he ナレッジ完成・manual_override受理）

- **Add**: harness-engineering に8コンセプト（ハーネスとは/なぜ必要か/責務と段階/ツールとMCP/権限設計/設定スコープ/サンドボックス/プロジェクトメモリ）。ソースは動画2本＋記事7本
- **Note**: 採点は4周で 8/7/9/9/7 → 7/8/8/7/7 → 9/9/8/9/7 → 8/7/8/9/7 と推移。事実正確性・リンクは8〜9点で安定したが、②網羅性と⑤文章品質が採点者間で揺れ repair上限に到達。**最良周（9/9/8/9/7）の水準に達している判断で manual_override 受理**しdraftへ進めた

## 2026-08-14（harness-engineeringバンドル 採点指摘の修正 improve_k run:08142233fa）

- **Update**: 採点で未達だった指摘（findings-k.json 5件、from_run: 0814222564）をharness-engineering/配下で修正
  - `sandbox-and-isolation.md`: L51とL53で「microVMは独自カーネルを持つためホストに影響しない」が同一主張として反復していたため、L53の要約段落を削除しL51に統合。L74「筆者自身の運用は次のように紹介されている。」が単独1文で導入のみだったため削除し、続く段落と1つに畳んだ
  - `sandbox-and-isolation.md`: 「筆者が最も使い込んでいるツール」というぼかし表記と、同ファイル後半の「Claude Codeの/sandbox等」という実名表記が同一ファイル内で揺れていたため、前半もClaude Codeと明記
  - `why-harness-matters.md` / `harness-responsibilities-and-ladder.md`: 論文の「問いの立て直し」（「基盤モデルがパッチを生成できるか」から「モデル・ハーネス・環境からなるシステムが...」への立て直し）がほぼ同文で二重掲載されていたため、why側を初出として残しresponsibilities側は1文に圧縮してwhyへリンク委譲
  - `what-is-harness-engineering.md`: 「本バンドルの中盤4本が4要素に対応」という記述が、同ファイルの地図表（中盤は5本、権限が2本立て）と数が合わなかったため、「中盤5本（権限は2本立て）」に修正しsettingsが配布・統制面を担う旨を追記
  - `index.md` / `what-is-harness-engineering.md`: 読む順番の理由づけ（4要素の流れの説明、権限3本セットで読む理由）が両ファイルでほぼ同内容で二重化していたため、詳細な理由づけをwhat-is側に一本化し、index.md側は1行の順序提示＋リンクに圧縮
- **Verify**: `tools/validate_okf.py knowledge` → errors: 0, warnings: 0

## 2026-08-14（harness-engineeringバンドル 採点指摘の修正 improve_k run:08142218a0）

- **Update**: 採点で未達だった指摘（findings-k.json 7件、from_run: 081422098f）をharness-engineering/配下・関連sourcesで修正
  - `sandbox-and-isolation.md` / `project-memory-and-rules.md`: 「> 引用:」形式だが実際は「〜と筆者は説明している」という三人称要約だった4箇所（sandbox 53,75行目 / project-memory 51,86行目）を、地の文＋「（同記事の要約）」表記に変更。原文（Zenn記事）が再取得できないための代替対応
  - `tools-and-mcp.md`: 冒頭に「4要素はkeitoaiweb動画による整理であり業界標準ではない」という出所文を追加し、frontmatter descriptionにも「keitoaiweb動画由来の整理」を明記。Citationsに同動画を追加し `video-pe-five-engineering-stages.md` の活用先とを双方向リンク化
  - `why-harness-matters.md` / `article-he-claude-md-best-practices.md`（sources）: Citations・活用先が本文に登場しない「300行・150〜200指示・ワーキングメモリの比喩」を根拠として列挙していた問題を修正。whyファイル側は本文が扱う「コンテキスト汚染」のみに絞り、当該数値・比喩は本文に実在する `project-memory-and-rules.md` 側のCitations・活用先に明記して一本化
  - `project-memory-and-rules.md`: 3層対比表（CLAUDE.md／Lint等／denyルール）の性質セル2行が前回改訂で「→ permissions-design.mdの対比表を参照」というプレースホルダのみになっていたため、参照先の実際の文言（確率的なお願い／機械的な禁止）を書き戻し、掘り下げリンクは残す形に修正
  - `tools-and-mcp.md`: why-harness-matters.md 50-52行目と重複していたPIVOT動画由来の「クラウド型はローカルを読めない／環境差でできる仕事が変わる」の説明を、参照リンク付きの1〜2文に圧縮
  - `tools-and-mcp.md`: 「道具をどこで動かすか」節の4選択肢（CLI/Agent SDK/Client SDK/Managed Agents）を詰め込んでいた一文を箇条書きに分割し、原典表記に合わせ「rest API」を「REST API」に修正
- **Verify**: `tools/validate_okf.py knowledge` → errors: 0, warnings: 0

## 2026-08-14（harness-engineeringバンドル 採点指摘の修正 improve_k run:0814220412）

- **Update**: 採点で未達だった指摘（findings-k.json 5件）をharness-engineering/配下で修正
  - `tools-and-mcp.md`: 「道具をどこで動かすか——4つの実装形態」節を新設し、article-he-agent-sdk-overview.mdにあるCLI/Agent SDK/Client SDK/Managed Agentsの使い分けと「Agent harness design」ブログ案内をバンドルに反映。Managed Agentsをsandbox-and-isolation.md（サンドボックスのホスト）・harness-responsibilities-and-ladder.md（タスク状態）へ接続
  - `permissions-design.md`: 「設計の手順」節に、AI Orchestra記事の「確認プロンプトを減らす4つの方法（リスクの低い順）」という骨格と2026年7月時点の注記を追加
  - `why-harness-matters.md`: project-memory-and-rules.mdと重複していた「300行以下・150〜200指示」の引用と説明を落とし、2〜3文の予告に短縮してリンクへ委譲
  - `sandbox-and-isolation.md`: 「と筆者はした上でこう述べている」の文法破綻を修正
  - `project-memory-and-rules.md`: permissions-design.mdと重複していた対比表の2行（CLAUDE.md／denyルール）をpermissions-design.mdへの参照に置き換え
- **Verify**: `tools/validate_okf.py knowledge` → errors: 0, warnings: 0

## 2026-08-14（harness-engineering バンドル完成 knowledge run:081421457c）

- **Creation**: harness-engineering/ を新設し8コンセプトを整備（ソース台帳10本を情報源とする。設計と先行5本は先行ランで作成済み、本ラン 081421457c で残り3本を追加して全8本を完成）。本ランで追加したのは `settings-scopes-and-governance.md`（Managed/User/Project/Localの4スコープと優先順位、Managedだけ配信経路が影響範囲を決めること、権限ルールのみ優先順位ではなくマージで合成されdenyが層を問わず有効であること、「どの層に何を書くか」＝統制設計という読み替え、承認で育てた許可リストがLocal層に溜まりgitignoreされること）、`sandbox-and-isolation.md`（アプリケーション層の除外設定はツール側の制御であり突破されうるという限界、OSネイティブ／コンテナ／microVMの3分類と各実装、選定軸としての「うっかり許可への耐性」と「攻撃面の広さ」、権限とサンドボックスの強制主体の違いと「隔離が先、bypassが後」、最小権限の原則）、`project-memory-and-rules.md`（論文の11責務におけるproject memoryとしての位置づけ、コンテキスト汚染と分量の目安、コードスタイルはLint/hooksへ・絶対禁止はdenyへという3層の書き分け、トリガー＋アクションで書く罠の共有、段階的開示、長期記憶として育てる運用）の3本
- **Creation**: harness-engineering/index.md を作成（8コンセプトの一覧と、4要素を「与える→塞ぐ→配る→備える→渡す」の流れでたどる推奨読書順）
- **Update**: sources/ の台帳8本の「活用先」にコンセプト側からの被参照を追記し、コンセプトの Citations と双方向でリンクさせた（article-he-claude-code-settings / article-he-sandbox-technology は「（コンセプト昇華時に追記）」から実体へ差し替え、article-he-claude-code-permissions / article-he-claude-code-permissions-admin / article-he-claude-md-best-practices / article-he-harness-engineering-paper / article-he-agent-sdk-overview / video-pe-five-engineering-stages は行を追加）
- **Update**: ルート index.md に harness-engineering/ を追加

## 2026-08-14（heソース台帳・記事1本 web_ledger run:081421275c）

- **Creation**: sources/ に記事1本を article-he-*.md として登録（ハーネスエンジニアリングテーマ、web_ledger工程 run:081421275c）。article-he-claude-code-permissions-admin.md（AI Orchestra「Claude Codeの権限設定と管理者権限 — permissions実務ガイド」、法人導入支援の視点から解説する二次資料。deny→ask→allowの評価順序とCLAUDE.md記述との違い（プロンプトの「お願い」対permissionsによる機械的強制）、ツール名とパターンによるルール記法とワイルドカード・複合コマンド分解判定、`.claude/settings.json`への配置による適用範囲の使い分け、OSのsudo権限とbypassPermissionsモードという「管理者権限」の2つの異なる論点、確認プロンプトを減らす4方法とbypassPermissionsモードの起動フラグ・安全装置、managed/コマンドライン指定/local/project/userの4層設定ファイルとdenyルールの層を問わない絶対優先を解説。既存のAnthropic公式一次資料 article-he-claude-code-permissions.md と同一テーマだが視点が異なるため別ファイルとして登録）
- **Update**: sources/index.md の「記事（ハーネスエンジニアリング）」節に上記1件を追加

## 2026-08-14（heソース台帳・記事2本 web_ledger run:08142122e9）

- **Creation**: sources/ に記事2本を article-he-*.md として登録（ハーネスエンジニアリングテーマ、Zenn記事2本、web_ledger工程 run:08142122e9）。article-he-claude-md-best-practices.md（Zenn「【Claude Code】CLAUDE.md運用のベストプラクティス：失敗しないための7つの原則」、300行以内・指示150〜200個程度というLLMの処理限界に基づく目安、フォーマット・スタイル指示はLint/Formatter/Git hooksに委ねスタイルではなく知識・罠・運用ルールを書くという方針、プロジェクト一行説明・頻出コマンド・トリガー&アクション型の罠共有という3要素、詳細情報を別ファイルへ分離する段階的開示、CLAUDE.mdの文脈が無視されうる前提とLLMの先頭末尾重み付け特性、短期記憶/長期記憶の比喩とモノレポでの親子CLAUDE.md構成を解説）、article-he-sandbox-technology.md（Zenn/株式会社松尾研究所「コーディングエージェントのサンドボックス技術を理解する」、プロンプトインジェクションによる機密ファイル流出をアプリケーション層の除外設定だけでは防ぎきれない理由、OWASP Top 10 for Agentic Applications 2026、OSネイティブ（Seatbelt/Landlock+seccomp/bubblewrap）・コンテナ（gVisor、CVE-2020-14386）・microVM（Apple Virtualization Framework、Docker Sandbox）の3分類、Claude Code `/sandbox`とClaude Desktopの実装比較、最小権限の原則に基づく筆者の使い分けを解説）
- **Update**: sources/index.md の「記事（ハーネスエンジニアリング）」節に上記2件を追加

## 2026-08-14（heソース台帳・記事2本 web_ledger run:0814211575）

- **Creation**: sources/ に記事2本を article-he-*.md として登録（ハーネスエンジニアリングテーマ、web_ledger工程 run:0814211575）。article-he-agent-sdk-overview.md（Anthropic公式「Agent SDK overview」、エージェントの定義、Agent SDK/Claude Code CLI/Client SDK/Managed Agentsの4択比較、Built-in tools・Hooks・Subagents・MCP・Permissions・Sessions・Skills/commands/memory・Pluginsの提供機能、サードパーティ開発者への認証方式の注意事項、Quickstart等の次のステップを解説）、article-he-harness-engineering-paper.md（arXiv「AI Harness Engineering: A Runtime Substrate for Foundation-Model Software Agents」、自律的ソフトウェアエンジニアリング能力をモデル単体でなくモデル・ハーネス・環境から成るシステムの創発的性質として捉え直す論旨、C_system=F(C_model,C_harness,C_environment,T)の定式化、ハーネスを構成する11の責務、H0〜H3の4段階ラダーとトレースベース評価プロトコル、問いの立て直しを解説）
- **Update**: sources/index.md の「記事（ハーネスエンジニアリング）」節に上記2件を追加

## 2026-08-14（heソース台帳・記事2本 web_ledger run:0814211079）

- **Creation**: sources/ に記事2本を article-he-*.md として登録（ハーネスエンジニアリングテーマ、Anthropic公式Claude Code Docs、web_ledger工程 run:0814211079）。article-he-claude-code-permissions.md（「Configure permissions」、3段階のツール分類と承認要否、deny→ask→allowの評価順序、ツール名指定denyの完全除去とスコープ指定denyの違い、Ctrl+Eの説明表示機能を解説）、article-he-claude-code-settings.md（「Claude Code settings」、Managed/User/Project/Localの4スコープの所在・共有範囲・想定用途・優先順位を解説）
- **Update**: sources/index.md に「記事（ハーネスエンジニアリング）」節を新設し上記2件を追加

## 2026-08-14（heソース台帳・研究フェーズ run:08142019a0）

- **Creation**: sources/ に動画台帳を1本追加。`video-he-claude-code-4hour-agent.md`（PIVOT公式チャンネル「【Claude Code活用法】4時間でMC野嶋専用のAIエージェントを構築」、43分53秒）。環境構築・クロードコード基礎操作・悩みのヒアリングを踏まえたスキル作成・完成エージェントのデモという流れを、「スキル＝AIへの業務マニュアル」「AIに任せすぎない」というハーネスエンジニアリング関連の要点を軸に整理した
- **Update**: sources/index.md の既存`video-he-webmcp-cloudflare-guide.md`行（「記事（コンテキストエンジニアリング）」節末尾に配置済み）の直後に上記1行を追記

## 2026-08-14（ce ナレッジの品質判定・manual_override受理）

- **Note**: context-engineering の11コンセプトを採点 8/6/7/6/6（①事実正確性8・②網羅性6・③構成7・④リンク6・⑤文章品質6）のまま manual_override で受理し、テーマを he へ進めた。網羅性と独立裏取りに既知の弱みが残る**参考ナレッジ**の位置づけ（02の発表資料本体は `decks/ai-eng-02-context-engineering/` 側で別途品質担保済み）

## 2026-08-14（採点指摘の修正・improve_k run:0814155936）

- **Fix**: findings-k.json 15件中13件をfixed、1件をdeferred(out_of_scope)、1件をdeferred(needs_research)として処理。①`context-components.md`にGoogle ADKの中核主張「作業コンテキストは呼び出しごとに再構築される一時ビューであり保存された全状態ではない」を新段落で追加②`security-and-trust-boundaries.md`のOpenAIデータ制御の記述を「学習利用・安全監視ログ・application state」の3点別々確認の箇条書きへ展開③`context-layers-and-intervention.md`にMCP（Model Context Protocol）を第4層の説明として追加、あわせて第5層にfew-shot個数目安（1〜3個）、第1〜2層に制約の肯定形明示という入門動画のコツを追記④`what-is-context-engineering.md`にコンテキストエンジニアリングという呼称の出自（Karpathy・Tobi Lütke、cloco記事帰属）を追加⑤`retrieval-memory-compaction-cache.md`のRAG節に、ウィンドウ拡大でも更新頻度・権限・出所追跡は解決しないという反論段落を追加⑥`context-components.md`冒頭に3動画共通の「記憶リセットされる新人」比喩を追加⑦`what-is-context-engineering.md`の5層一覧再掲（five-engineering-scopes.mdとの重複）を1文+リンクに圧縮⑧`context-layers-and-intervention.md`の「Compress を製品機能として使う」節（compaction製品仕様）を`retrieval-memory-compaction-cache.md`の新設「製品機能としてのコンパクション」節へ移動し1文の参照に置換、連動して`article-ce-compaction.md`の活用先リンク先も付け替え⑨`context-rot-and-editing.md`の「次に読む」先頭に`practical-context-packs.md`を追加⑩`article-ce-anthropic-effective-context-engineering.md`の活用先を実体に合わせて修正（retrieval側の「構造化ノート・サブエージェント」という過大な記述を「圧縮の役割」に絞り、実際にこの一次資料を引用している`context-layers-and-intervention.md`の行を新設）⑪claude-code/pipeline-opus生成の3ファイル（`context-layers-and-intervention.md`・`context-rot-and-editing.md`・`five-engineering-scopes.md`）の冒頭を会話的な呼びかけ調から断定調の定義文へ書き換え、決定的でない太字強調を計10箇所前後削減⑫`video-pe-five-engineering-stages.md`にsource_id（CE-S21）と「適用範囲と留保」節を追加。ただしfix_hintが前提とする「他の動画ソースはsource_tierを持つ」は事実確認の結果誤りだった（CE系動画4本を含むバンドル内の全動画ソースがsource_tierを欠く）ため、新たな不整合を生まないようsource_tierは追加せず、この点をevidenceに明記。2件（f8: 「5層」同名衝突の完全解消、f14: sources 21件のテンプレート統一）は、前者が`what-is-context-engineering.md`・`long-horizon-and-tools.md`など当findingの`where`に含まれないファイルへの改名波及を要するため、後者が4本の二次記事へ「原文の根拠箇所」を追加するには原文への再アクセスが必要なため、いずれもdeferred。OKF検証はCHECK行を参照
- **Note**: findings 15件の内訳はfixed 13件、deferred(out_of_scope) 1件（f8）、deferred(needs_research) 1件（f14）。詳細は outbox（`pipeline/state/outbox/result-0814155936.json`）参照

## 2026-08-14（採点指摘の修正・improve_k run:0814145822）

- **Fix**: findings-k.json 13件中10件をfixed、3件をdeferred(out_of_scope)として修正。①`article-ce-lost-in-the-middle.md`が明記する「2025年のMIT研究」の書誌不明という留保を`context-rot-and-editing.md`に追記し、位置効果の一次的根拠（2023年"Lost in the Middle"論文）をrot.md内に自己完結させ初学者ルートからでも読める形にした②`context-components.md`のGoogle ADK役割列挙から台帳に無い「状態」を削り「作業コンテキスト」に統一③Google Researchのブログ解説（type: Article）を「一次研究」ではなく「公式解説」と呼ぶよう表現変更④`long-horizon-and-tools.md`にマルチエージェントの引き継ぎでスコープを絞ることと発話主体を再表現することの2文を追加⑤`five-engineering-scopes.md`に、layers.mdの5層とは別の切り口である旨を追記（同名衝突への注記が無かった3箇所目の穴を解消）⑥`index.md`推奨読み順のファイル名を全てMarkdownリンクに変更⑦`context-layers-and-intervention.md`内で4回反復していたauto字幕注記を17行目の包括注記に集約し38・44・55行目の個別注記を削除、59-67節のcompaction閾値の固定値（150,000/50,000トークン）を一般化し原著台帳参照に委ねた⑧sources 3本の活用先の不一致を解消（video-ce-context-4-elements.mdにcontext-components.md行を追加、video-ce-context-layers-intro.md・video-pe-five-engineering-stages.mdからリンク実体のないwhat-is-context-engineering.md行を削除）。3件（RAG不要論の論点追加・用語の広まりの経緯追加・layers.mdの4主題分割）は、fix_hintが示す実際の修正先ファイル（retrieval-memory-compaction-cache.md / what-is-context-engineering.md / 新規ファイルまたは既存他ファイルへの節統合）がいずれのfindingの`where`にも含まれず、この工程の許可パス外のためdeferred(out_of_scope)。OKF検証はCHECK行を参照
- **Note**: findings 13件の内訳はfixed 10件、deferred(out_of_scope) 3件。詳細は outbox（`pipeline/state/outbox/result-0814145822.json`）参照

## 2026-08-14（採点指摘の修正・improve_k run:0814142720）

- **Fix**: findings-k.json 12件すべてをfixedとして修正。①cloco記事のWrite/Select/Compress/Isolate帰属がAnthropic一次資料の節構成と一致しない点を明記（`context-layers-and-intervention.md`）②動画の「見本」実務主張を`context-components.md`に新設節として追加し`practical-context-packs.md`テンプレートにも見本欄を追加③「不十分な追加情報が誤った確信につながる」というGoogle Research一次知見を`context-rot-and-editing.md`に追加④Isolateの副作用・システム指示の粒度（ゴルディロックスゾーン）・Microsoftの3段階設計手順を`context-layers-and-intervention.md`と`practical-context-packs.md`に追記⑤「5層」という同一呼称が指す2つの別物（five-engineering-scopesの5スコープとcontext-layersの5層）を`index.md`・`context-layers-and-intervention.md`で明示的に区別⑥初学者ルート終点`practical-context-packs.md`の前方参照2段落を「システム設計まで進む場合の補足」節に分離⑦`what-is-context-engineering.md`の重複節を`five-engineering-scopes.md`へ集約⑧コンパクションの役割/製品仕様、U字カーブの機構説明、5層分類の3箇所に逆リンクを追加⑨claude-code生成の台帳8件（article-ce-cloco/compaction/lost-in-the-middle/softbank、video-ce-context-4-elements/context-layers-intro/context-rot-and-jit/harness-context-setup）に「適用範囲と留保」節とsource_id（CE-S13〜CE-S20）を付与⑩`context-layers-and-intervention.md`・`five-engineering-scopes.md`の「〜としているとしている」二重伝聞を解消。1件（article-ce-compaction.mdのtype/source_tier/origin不整合、CE-S14）はメタデータのみ修正しファイル名変更は許可パス外のため見送り。1件（Microsoft教材との対応、CE-S02関連）は④の修正に含めて解消。OKF検証 errors:0 / warnings:0
- **Note**: findings 12件の内訳はfixed 12件、deferredなし。詳細は outbox（`pipeline/state/outbox/result-0814142720.json`）参照

## 2026-08-14（さらに続き6・context-engineering コンセプト追加）

- **Update**: context-engineering/ にコンセプト3本を追加（`five-engineering-scopes` 5つのエンジニアリングのスコープ差と入れ子構造、`context-rot-and-editing` 情報を足すほど劣化する理由と「足すより編集する」判断、`context-layers-and-intervention` 介入点としての5層とWrite/Select/Compress/Isolate）。これによりCE系台帳21件すべてがコンセプトから被引用となった
- **Update**: `what-is-context-engineering.md` の5層地図の節に出典2件を追加（出典1件のみだった状態を解消）。あわせて index.md の学習の地図・推奨読み順・根拠の記述を更新
- **Update**: 上記3本が参照する台帳10件の「活用先」を追記し、コンセプト⇄台帳の双方向リンクを片方向0件まで揃えた（OKF検証 errors:0 / warnings:0）

## 2026-08-14（さらに続き5）

- **Creation**: sources/ に記事2本を article-ce-*.md として登録（コンテキストエンジニアリングテーマ、web_ledger工程 run:081413588c）。article-ce-softbank-what-is-context-engineering.md（ソフトバンク株式会社ビジネスブログ、コンテキストエンジニアリングの定義・会話履歴の忘却問題・プロンプトエンジニアリングとの違い・システムプロンプト/要約/外部保管の実践テクニックを解説）、article-ce-cloco-context-engineering-claude.md（cloco Blog、Karpathy・Tobi Lütkeの言及とQodo調査データを紹介しつつAnthropicのWrite/Select/Compress/Isolateの4戦略とClaude CodeのCLAUDE.md整備・Arize AI調査を解説）
- **Update**: sources/index.md の「記事（コンテキストエンジニアリング）」節に上記2件を追加

## 2026-08-14（コンテキストエンジニアリング・デッキ初版）

- **Creation**: context-engineering/ を新設。定義とPromptとの重なり、推論時の構成要素、5項目、必要性・十分性・信頼性・鮮度、window/history/memory/trainingの区別、RAG・外部メモリ・圧縮・Prompt cache、長期タスクとtool context、prompt injection・データ境界、コピー可能なcontext packを8コンセプトに分離
- **Creation**: sources/ に公式一次資料・原著12件を `*-ce-*` として登録。CE-S01〜CE-S12を一意に採番し、全台帳へ原文の見出し・節を示すlocatorを追加。Microsoft教材は固定commit URL、McKinnon (2025) はGemini 2.5 Flash単一・simple factoid Q&Aの限定的対照として記録
- **Update**: ルートindexとsources indexにcontext-engineeringの導線を追加。コンセプトから一次資料、台帳から活用先への双方向リンクを整備
- **Creation**: decks/ai-eng-02-context-engineering/ を新設。本編30枚＋付録21枚の全51枚（初版）
- **Note**: 上記は 2026-08-14 未明に loop/ai-eng-02-context-engineering ブランチへコミット済みだったが main へ未マージだったため、同日午後の改訂（51→58枚）時に loop/ce-deck-clarity ブランチへ復元した

## 2026-08-14（さらに続き4）

- **Creation**: sources/ に記事2本を article-ce-*.md として登録（コンテキストエンジニアリングテーマ、web_ledger工程 run:081413220d）。article-ce-compaction.md（Anthropic公式ドキュメント「Compaction」、コンテキストウィンドウ上限に近づくと古いコンテキストを自動要約する機能の用途・動作の仕組み・パラメータ仕様を解説）、article-ce-lost-in-the-middle.md（DEV Community記事、コンテキスト内の位置によってLLMの正答率がU字型に変化する「lost in the middle」現象を2023年のStanford等の論文と2025年のMIT研究による2つのアーキテクチャ的原因（因果的アテンションマスキング・位置エンコーディング減衰）から解説）
- **Update**: sources/index.md に「記事（コンテキストエンジニアリング）」節を新設し上記2件を追加

## 2026-08-14（さらに続き3）

- **Creation**: sources/ に動画2本を登録（コンテキストエンジニアリングテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:08141255bc）。video-ce-context-4-elements.md（工藤あい　AI導入・AI駆動　バーニングトライブ、コンテキストの定義と目的・前提・材料・見本の4点セット・仕組み化を解説）、video-ce-harness-context-setup.md（チャエン【AI研究所】Byデジライズ、プロンプト→コンテキスト→ハーネスの縦3段階とループ・グラフの横軸、コンテキストウィンドウ拡大とRAGの位置づけを解説）
- **Update**: sources/index.md の「動画（コンテキストエンジニアリング）」節に上記2件を追加

## 2026-08-14（さらに続き）

- **Creation**: sources/ に動画1本を video-ce-context-layers-intro.md として登録（コンテキストエンジニアリングテーマ、ゆっくり探究Labチャンネル、字幕全文から要約・主張テーブルつき、research_ledger工程 run:0814123181）。コンテキストを5層（システムプロンプト・プロジェクトメモリ・検索拡張・ツール呼び出し・会話履歴）に整理し、Claude Codeでの実装例と構造化・削減のコツ、3つの落とし穴を解説
- **Update**: sources/index.md に「動画（コンテキストエンジニアリング）」節を新設し上記1件を追加
- **Note**: マニフェストの対象動画2本のうち1本（動画ID 8VNLFKCQFa8、"[How to Master AI] A Thorough Guide to Loop, Harness, Prompt, Context, and Graph Engineering"、keitoaiweb）は、2026-08-12にprompt-engineeringテーマで video-pe-five-engineering-stages.md として同一URL・同一タイトルで既に登録済みのため重複登録をスキップ（run:0814123181）

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

# 変更履歴

## 2026-08-29（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:0829004573）

- **Source**: `sources/article-coding-plex-local-review-gate.md` を新規登録。PLEX Product Team Blog「ローカルの Claude Code レビューを『すり抜けられない』必須チェックにした話」。AIレビューの実行コストを抑えるため各開発者のローカル環境でClaude Codeレビューを実行する構成にしたところ、Git hookは未設定でも何も言わずスキップされ「痕跡すら残らない」ためセットアップ漏れが検知できないという弱点が生じたと報告。解決策としてgit notes（commit本体を書き換えずメモを貼れる機能）にレビューPASSを記述し、GitHub Actions経由でcommit statusに反映、branch protectionでstatus successを必須化することで、hook未セットアップの環境からのcommitにはnoteが付かずマージできない構造を実現したと解説。ただしレビュー品質やPASSの正当性自体の保証、意図的な迂回への対応はできないという限界も明示されている内容を解説
- **Update**: `sources/index.md` の「## 記事（AIコーディング実務）」節に上記1件を追記
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回も見送った（run:082810157b・run:082812459e・run:0828151527・run:0828224531・run:082823451bに続き6回目の同一確認）

## 2026-08-28（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:082823451b）

- **Source**: `sources/article-coding-qiita-team-rollout-pitfalls.md` を新規登録。Qiita「チーム開発でClaude Codeを3ヶ月運用して分かった『壊れるポイント』と『仕組み化のコツ』」。エンジニア5名（フロント2名・バック2名・フルスタック1名）、Next.js + Go + PostgreSQL構成のチームが2025年4月〜6月に運用し、CLAUDE.mdの属人化によるPRレビュー時間2倍化、丸投げリトライ等によるトークンコスト約3倍膨張、信頼バイアスによるGoのHTTPハンドラのリソースリーク本番障害という3つの崩壊パターンを報告。対策としてCLAUDE.mdの3層レイヤー分離・2週間毎の振り返り会、/compactとGitHub Actions/Slackによるトークン予算可視化、AI生成コード専用レビューチェックリストのCI組み込みを実施し、3ヶ月後にPRレビュー時間0.8倍・月額コスト1.4倍まで改善したと報告する内容を解説
- **Update**: `sources/index.md` の「## 記事（AIコーディング実務）」節に上記1件を追記
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回も見送った（run:082810157b・run:082812459e・run:0828151527・run:0828224531に続き5回目の同一確認）

## 2026-08-28（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:0828224531）

- **Source**: `sources/article-coding-copilot-issues-study.md` を新規登録。arXiv「Exploring the Problems, their Causes and Solutions of AI Pair Programming: A Study on GitHub and Stack Overflow」。GitHub Copilotに関するGitHub Issues 476件・Discussions 706件・Stack Overflow投稿142件（計1,324件）を分析し1,355件の問題を分類、Operation Issue（機能障害・認証エラー等）が57.5%を占めると報告。原因分析ではCopilot内部エラー19.4%・ネットワーク接続エラー13.6%が上位、解決策分析ではCopilotによるバグ修正27.2%が最多。ユーザーへの提言（レビュー励行・インスピレーション源としての活用・公式サポートIDEの使用）とCopilotチームへの提言（カスタマイズ拡充等）を解説
- **Update**: `sources/index.md` の「## 記事（AIコーディング実務）」節に上記1件を追記
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回も見送った（run:082810157b・run:082812459e・run:0828151527に続き4回目の同一確認）

## 2026-08-28（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:0828151527）

- **Source**: `sources/article-coding-msft-cli-agent-adoption.md` を新規登録。arXiv（Microsoft Research）「Adoption and Impact of Command-Line AI Coding Agents」（Murphy-Hill, Butler, Savelieva）。2026年前半のMicrosoft社内ロールアウトにおいて、社会的露出（skip-levelピア25%以上利用で初回使用オッズ+216%等）が採用の最大予測因子であること、IDE版Copilot既存利用者はむしろ定着率が低いという矛盾的関連、合成対照分析（CausalImpact）によるマージPR数+24.0%増加（95%CI +14.5%〜+33.7%、p<0.001）、Copilot CLIがClaude Codeの約2.2倍の効果を示したという成果分析と、マージPRは品質を反映しない不完全な指標であるという著者自身の限界の明記を解説
- **Update**: `sources/index.md` の「## 記事（AIコーディング実務）」節に上記1件を追記
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回も見送った（run:082810157b・run:082812459eに続き3回目の同一確認）

## 2026-08-28（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:082812459e）

- **Source**: `sources/article-coding-codex-prompting-guide.md` を新規登録。OpenAI公式「Codex Prompting Guide (GPT-5-Codex)」。計画ツールを省略してよい下位25%タスクの基準、preamble（前置き発言）の1〜2文ルールと更新頻度の数値規定、フロントエンド生成における「AI slop」回避とTypography/Color/Motion/Backgroundの4要素、冗長な繰り返し編集を避ける行動原則を解説
- **Update**: `sources/index.md` の「## 記事（AIコーディング実務）」節に上記1件を追記
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回も見送った（前回run:082810157bと同一の重複を再確認）

## 2026-08-28（AIコーディング実務テーマ：記事台帳1本を新規登録、1本は重複のためスキップ run:082810157b）

- **Source**: `sources/article-coding-codex-best-practices.md` を新規登録。OpenAI公式「Best practices for Codex」。プロンプトの4要素（Goal/Context/Constraints/Done when）、AGENTS.mdによる恒久ルールの外部化、権限の保守的運用、MCP/Skills/スケジュールタスクの活用、よくある誤り8種を解説
- **Update**: `sources/index.md` に新節「## 記事（AIコーディング実務）」を追加し、上記1件を登録
- **Skip**: マニフェストのもう1本「Best practices for Claude Code」（`https://code.claude.com/docs/en/best-practices`）は、既存の `sources/article-le-claude-code-best-practices.md` に同一URLで既に登録済み（source_tier: primary、活用先リンク4件あり）のため、重複登録を避けて今回は見送った

## 2026-08-27（AIコーディング実務テーマ：動画台帳2本を新規登録 run:08272345f6）

- **Source**: `sources/video-coding-git-pr-conflict-practice.md` を新規登録。安野貴博氏「【バイブコーディング超入門講座第6回】GitやGitHubはもう怖くない！？」。リポジトリ作成からコミット・プッシュ・プルリクエスト、2ブランチが同じ行を変更した際のコンフリクト解決までをClaude Code越しに実演
- **Source**: `sources/video-coding-database-supabase-safety.md` を新規登録。安野貴博氏「【バイブコーディング超入門講座第7回】アプリにデータ保存機能を追加するには？」。データベースの基本、Supabase（BaaS）の紹介、AIに本番データを壊されないための「壊さない意識」・危険な言葉（DELETE/UPDATE/WHERE）・SELECT事前確認・環境分離・バックアップの実践知見
- **Update**: `sources/index.md` の「## 動画（AIコーディング実務）」節に上記2件を追記

## 2026-08-27（AIコーディング実務テーマ：動画台帳2本を新規登録 run:08272245f6）

- **Source**: `sources/video-coding-vibe-coding-qa-followup.md` を新規登録。安野貴博氏「【コメント返し】バイブコーディング超入門動画への質問・疑問に回答します」。CLAUDE.mdへのルール記載・自動テスト・ローカル実行時のセキュリティリスク・クロードの料金プラン(無料/Pro17ドル/MAX100ドル)などQ&A形式の実務知見
- **Source**: `sources/video-coding-git-github-5-operations.md` を新規登録。安野貴博氏「【バイブコーディング超入門講座第5回】初心者向けGit&GitHub解説」。Git/GitHubの役割の違いと、ブランチ・コミット・プッシュ・プルリクエスト・プルの5操作をセーブポイントの比喩で整理、クロードコードでの実演あり
- **Update**: `sources/index.md` に新節「## 動画（AIコーディング実務）」を追加し、上記2件を登録

## 2026-08-27（安野氏ループ動画：図解文言の裏取り追記）

- **Update**: `sources/video-le-anno-team-mirai-loop-engineering.md` に「図解の要点（画面キャプチャで文言確認済み）」節を追加。ユーザー提供のスクリーンショット3枚により、HITL/HOTL・4段階（ハーネス＝お願いを制約に変える足場、ループ＝HOTLの実装）・Andrew Ng氏の3層入れ子（context advantage含む）の図中文言を聞き取りではなく画面文言として裏取りした
- **Context**: 同キャプチャを参考に `decks/00-series-overview` のループ部分を図解改修（HITL/HOTL対比図・3層入れ子スライド新設、23枚化）

## 2026-08-27（安野氏ループ動画の新版登録と、00デッキレビューで受けたシリーズ方針の反映）

- **Source**: `sources/video-le-anno-team-mirai-loop-engineering.md` を新規登録。安野貴博氏「【ループエンジニアリングとは？】AIにプロンプトはもう要らない」（チームみらい通信チャンネル、2026-08-21公開）。既存の自由研究チャンネル版（video-pe-loop-engineering-overview）の別チャンネル再解説で、終盤の非エンジニア向け3業務例（日程調整・会議後タスク管理・書類作成チェック）が新規要素
- **Update**: `loop-engineering/when-to-use-loops.md` に新節「症状からだけでは足りない——仕事を広げるための設計」を追加。シリーズオーナーのレビュー方針（2026-08-27）＝ループは品質対策に閉じず、一発のチャットでは難しい大規模作業・連続実行・自律動作を任せるための積極的な設計であり、プロンプト・コンテキスト・ハーネスの土台が連続実行の前提、5層は前半3つ＝答えの質を整える土台／後半2つ＝任せる仕事を広げる設計、という両面フレーミングを登録。非開発業務の例に新動画の3例目（書類作成チェック）を追記
- **Update**: `graph-engineering/loop-vs-graph-decision.md` の症状別使い分け節に同レビュー方針を追記。グラフ＝複数エージェントで並列度を上げ大量タスクを速くさばく積極的な発想であり、「構造」より「AIの仕事のプロセス・フロー（流れ）の設計」と捉える。「並列化は依存関係を描いた結果」の原則との整合も明記
- **Update**: `sources/index.md` の動画（ループエンジニアリング）節に新ソースのエントリを追加
- **Context**: 同方針は `decks/00-series-overview`（シリーズ全体紹介デッキ）の改訂にも反映（S5のポジティブフレーミング化・ループ/グラフ説明の書き換え・ハーネス5つの働き表の追加）

## 2026-08-22（agent-capabilities 採点指摘の修正 improve_k run:0822234571）

- **Fix (f1)**: `writing-good-skills.md:114` の完全修飾名の解説先リンクを、実際に内容がある `choosing-skill-mcp-or-cli.md` に差し替え、同一文中の重複リンクを1本化
- **Fix (f2)**: `prompts-and-project-rules.md` のスコープ節に、Skillの配置優先順位（Enterprise > Personal > Project）を出典帰属付きで追記し、`sources/article-tools-claude-code-skill-design.md` の活用先宣言と整合させた
- **Fix (f3)**: `choosing-skill-mcp-or-cli.md:33` の「CLIは既存の道具をそのまま呼ばせるだけ」という説明を、直後の「### CLIとは何か」節への参照に圧縮し重複を解消
- **Fix (f4)**: `choosing-skill-mcp-or-cli.md:39` のgcloud CLI Skillの実例・出所を削除し「実例は後述」に留めることで、`:97`との重複を解消
- **Fix (f5)**: `overview.md` / `choosing-skill-mcp-or-cli.md` / `webmcp-and-frontier.md` の該当箇所で、1段落・1項目内に複数あった太字強調を最重要の1箇所に絞った

## 2026-08-22（agent-capabilities 採点指摘の修正 improve_k run:082220158b）

- **Fix (f1)**: `progressive-disclosure.md` の「実物で確かめる」節に、google/skillsの中身は9割以上がMarkdown散文でPythonは一部の付随スクリプトのみという実物補正を1文追加
- **Fix (f2)**: `distribution-and-governance.md` の導入2ステップ直後に、プラグインが参照するのはgemini-cli-extensions等の別リポジトリでありgoogle/skills自体はカタログの位置づけである旨を1文追加
- **Fix (f3)**: `what-are-agent-skills.md`「なぜ生まれたのか」冒頭にAgent Skillsの発表日（2025-10-16）を追加。`webmcp-and-frontier.md` 冒頭に「エージェント自身がSkillを作成・編集・評価できるようにする」という公式の展望を追加
- **Fix (f4)**: `overview.md`「導入判断・技術選定をする立場」コースに `what-is-mcp.md` を `choosing-skill-mcp-or-cli.md` の直前として挿入し、判断材料を5点に修正（choosing-skill-mcp-or-cli.mdがMCPプリミティブの構造を前提としているため）
- **Fix (f5)**: `overview.md` の「4つの手段のうち3つがファイルを読ませる性質を利用している」という記述を、Skill/プロジェクトルール（ファイルを読ませる性質）とCLI（コマンド実行の性質）の2つに分けた記述に修正
- **Fix (f6)**: `prompts-and-project-rules.md` のSkill未習者向けにSkillの配置優先順位を詳述していた段落を、前方参照を圧縮した1文に修正
- **Fix (f7)**: `overview.md` のGPTs/Gems比較を圧縮し、詳細説明は `what-are-agent-skills.md` に一本化
- **Fix (f8)**: `writing-good-skills.md` と `choosing-skill-mcp-or-cli.md` の一言定義を、見出しの言い換えではなく持ち帰れる命題に置き換え

## 2026-08-22（agent-capabilities 採点指摘の修正 improve_k run:08221515e8）

- **Fix (f1)**: `what-are-agent-skills.md` の「Custom Skillsを置く場所と制約」表で、Claude API行の`skill_id`がPre-built 4種（pptx/xlsx/docx/pdf）の識別子である旨を明記し、Custom Skillの説明と区別
- **Fix (f2)**: `writing-good-skills.md` の「250文字で切り詰め」に、`what-are-agent-skills.md` の「上限1024文字」との関係（別概念であること）を1文で接続
- **Fix (f3)**: `what-is-mcp.md` 末尾の結論文「MCPは定額のコストを払う」の留保を、`overview.md` と同じ強度（実測記事・動画の指摘、公式`*/list`設計との整合）に揃えた
- **Fix (f4)**: `progressive-disclosure.md` 冒頭の「Skillを100個置いても動作が重くならない」を、限界節の「Level 1コストは常時かかる」と矛盾しない表現（「本文までは読み込まれない」）に修正
- **Fix (f5)**: `overview.md` の「導入判断・技術選定をする立場」コースの先頭に `what-are-agent-skills.md` を追加し、`progressive-disclosure.md` の既読前提と揃えた
- **Fix (f6)**: `index.md` の内容一覧に、CLIが専用ファイルを持たない旨と choosing-skill-mcp-or-cli.md への導線を1行追加
- **Fix (f7)**: `index.md` の「読む順番」節を、overview.md への外部参照と独自推奨の二重構造から、初学者向け1コースを直接示す形に一本化

## 2026-08-22（tools採点 repair上限の手動修正）

- **Add**: 9月シリーズ第2弾として `knowledge/agent-capabilities/` を新設（コンセプト9本・ソース台帳10本＝動画3・記事7）。Skills / MCP / CLI / プロンプトの4手段の使い分けを主題とし、Agent Skills公式仕様とMCP仕様の一次資料を確保
- **Fix (f1)**: CLIの定義が `overview.md` と `choosing-skill-mcp-or-cli.md` にほぼ同内容で重複していた。4手段のうちCLIだけ専用ファイルを持たない構成なので、定義と設計論点は choosing 側に集約し overview は1行＋リンクに縮約
- **Fix (f2)**: `index.md` の1〜8の並びと「初学者はプロンプト（6番）から」という推奨が食い違っていた。番号は地図上の位置であって読む順番ではない旨を明示
- **Fix (f3)**: `writing-good-skills.md` がMCPの完全修飾名という後続ファイルの概念を前提にしていたため、先に読む導線を追加
- **Fix (f4)**: 「コンテキスト汚染」とワーキングメモリの比喩が同一出典から2ファイルで完全に書き下されていた。行数の目安を持つ `prompts-and-project-rules.md` を本籍とし、`progressive-disclosure.md` 側は結論1文＋リンクに圧縮
- **Fix (f5)**: 節末を太字1文で締める型が反復していたため、各ファイル2箇所までに絞り9箇所の強調を通常文に戻した
- **Note**: 採点は 7/7/7/9/7 → 9/7/7/8/7 → 8/8/7/8/7 で repair 3回を使い切り stuck(repair_exhausted)。2026-08-21 22:54 から約16時間、stuck解除の担い手が不在で全スロットが空転した

## 2026-08-21（agent-capabilities 採点指摘の修正 improve_k run:0821174539）

- **Fix**: 採点findings 16件のうち13件を修正、3件は範囲外としてdeferred
  - 無帰属の断定を帰属付きに修正: `overview.md`（「接続中は常にツール一覧が載る」を実測記事＋動画由来と明示し表と本文を修正）、`choosing-skill-mcp-or-cli.md`（「3つの独立した出所が整合する」を「公式設計と矛盾しない・出所2本」に弱める）
  - 未収録の留保を追加: `choosing-skill-mcp-or-cli.md`（MCP仕様のUtility features（進捗通知）に触れ、「進捗が見えない」は実装・体験の話だと明示）
  - 引用記法の誤りを修正: `prompts-and-project-rules.md`（「〜と筆者は述べている」を含む要約文が引用ブロックになっていた箇所を地の文に統一）
  - 構造の不整合を解消: `index.md`（初学者向け起点として`prompts-and-project-rules.md`を1行案内）、`overview.md`（「読む順番の提案」2コース目の本数誤記と`prompts-and-project-rules.md`重複指定を修正、CLIの定義を表直後に新設）
  - 導線の欠落を補完: `progressive-disclosure.md`/`choosing-skill-mcp-or-cli.md`の「次に読む」に`overview.md`への1行を追加（`distribution-and-governance.md`は本findingsのwhere外のため対象外）
  - 反復緩和: `what-is-mcp.md`の太字締め5箇所のうち3箇所を地の文に戻し2箇所に絞った
  - 重複の要約化: `overview.md`（コード実行の2価値・「SkillはMCPの進化形ではない」を`what-are-agent-skills.md`/`what-is-mcp.md`への参照に畳んだ）
  - 引用の出典補完: `progressive-disclosure.md`のマニュアル比喩の引用に出典リンクを追加
  - 活用先の反映漏れを追加: `sources/video-tools-google-skills-marketplace.md`（`writing-good-skills.md`3箇所・`choosing-skill-mcp-or-cli.md`2箇所）、`sources/article-tools-agent-skills-equipping-real-world.md`（`writing-good-skills.md`のSkill開発指針4点）
  - **deferred(out_of_scope)** 3件: `sources/video-tools-google-skills-marketplace.md`の「9割以上Markdown」主張と「プラグインの中身は別リポジトリ参照」の未収録、`sources/article-tools-agent-skills-equipping-real-world.md`の発表時期・将来展望の未収録——いずれも修正には`what-are-agent-skills.md`等の非対象ファイルへの追記が必要なため本工程の範囲外
- **Note**: `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` で errors: 0, warnings: 0 を確認

## 2026-08-21（agent-capabilities 採点指摘の修正 improve_k run:082115153b）

- **Fix**: 採点findings 12件（severity mid5/low7）を全件修正
  - 台帳の反映漏れを追加: `distribution-and-governance.md`（google/skillsのカテゴリ内訳・別リポジトリの件）、`writing-good-skills.md`（`/skill-creator`のCreateモード起点作成推奨・`!<command>`構文・開発ガイドライン4点・文章修正傾向）、`what-are-agent-skills.md`（図クリエイトチャットの実演例）
  - 番号・構造の矛盾を解消: `overview.md`（「まず全体像だけ掴みたい」コースを4本に改め`prompts-and-project-rules.md`を含める。地図番号自体はf7の指摘との整合のため据え置き）、`choosing-skill-mcp-or-cli.md`（「CLIとは何か」節を新設し4手段中CLIだけ専用の居場所がない状態を解消、`overview.md`表からリンク）
  - 未定義語の手当て: `writing-good-skills.md`（MCPツール完全修飾名の箇所に`what-is-mcp.md`へのリンクを追加）、`choosing-skill-mcp-or-cli.md`（サブエージェントの一文定義を追加し4手段外の補助的選択肢と明記）
  - 重複の解消: 「Skills load on demand」「do not sync across surfaces」「誤起動注意」「引き算のメンテナンス」「コンテキストウィンドウ上限」の5主張について一次担当ファイル（順に`prompts-and-project-rules.md`/`what-are-agent-skills.md`/`writing-good-skills.md`/`distribution-and-governance.md`/`progressive-disclosure.md`）を決め、`overview.md`含む他ファイルは1文要約＋リンクに置換
  - タイムスタンプの補完: auto字幕由来の引用・言及に欠けていたタイムスタンプ（`.skill形式`[30:00]、規模[01:00]、プラグイン数[06:00]、ライセンス[08:00]、誤起動[19:00]、サブエージェントが受け取る5情報[22:00]、全ツール継承[08:00]）をソース側で検証のうえ補完
  - 文体の反復緩和: 「〜しておけばよい」型の文末定型が`what-is-mcp.md`に3箇所連続していたため2箇所を通常の断定文に書き換え、`progressive-disclosure.md`の同型1箇所も書き換え
  - 制作メモの露出を修正: `index.md`から「overview.md側で一元管理しており、ここでは重複させない」等の編集方針の文言を削除し、読者向けの一言案内に置き換え
- **Note**: `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` で errors: 0, warnings: 0 を確認

## 2026-08-21（agent-capabilities 採点指摘の修正 improve_k run:082112577c）

- **Fix**: 採点findings 14件のうち13件を修正（残り1件は範囲外としてdeferred）
  - 誤記・帰属の訂正: `what-are-agent-skills.md`（「decisive reliability」誤記、実務記事への帰属を単独化）、`what-is-mcp.md`（出所不明の「圧倒的に」を除去）
  - 出所マーカー統一: `progressive-disclosure.md` / `distribution-and-governance.md` の google/skills動画由来箇所に「（聞き取り）」を補完
  - 台帳の反映漏れを追加: `writing-good-skills.md`（frontmatter3フィールド・Use when/Don't use when・チェックリスト型ワークフロー）、`choosing-skill-mcp-or-cli.md`（gcloud help安全弁・`--full-auto`/resumeリトライ）、`what-is-mcp.md`（MCPを構成する4プロジェクト）
  - 矛盾・重複の解消: `overview.md`（読む順番の提案を`prompts-and-project-rules.md`の主張と整合）、`progressive-disclosure.md`（プロジェクトルールとの重複節を圧縮し`prompts-and-project-rules.md`に一本化）
  - 事実誤りの訂正: `index.md`（資料内訳を実測値に修正）、`webmcp-and-frontier.md`（「ここまでの7本」→「8本」）
  - 見出し構造の統一: 9ファイルの見出しから番号を除去し、「一言定義」節・末尾「次に読む」節を共通の型に揃えた（`overview.md`はバンドル入口としての性質上「読む順番の提案」を維持）
- **Deferred(out_of_scope)**: 太字強調の多用（各ファイル18〜50箇所）を「各節の結論のみ」に絞る修正は、9ファイル全体・数百箇所規模の主観的リライトを要するため本工程の局所修正の範囲外と判断
- **Note**: `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` で errors: 0, warnings: 0 を確認

## 2026-08-21（agent-capabilities バンドル新設・完成 knowledge run:0821025734 → 082110103b → 08211057a5）

- **Creation**: `knowledge/agent-capabilities/` を新設し、テーマ「AIに能力を足す4つの手段（Skills / MCP / CLI / プロンプト）」のコンセプト8本＋入口1本＝計9ファイルを執筆。台帳13本（Anthropic公式3本・MCP公式2本・実務記事3本・解説動画3本・ハーネス系公式/記事2本）を根拠とし、3ランに分けて段階実装した
  - run:0821025734 — 全9本を設計（`pipeline/staging/knowledge/plan.json`）し、`overview.md` / `what-are-agent-skills.md` / `progressive-disclosure.md` を執筆
  - run:082110103b — `writing-good-skills.md` / `what-is-mcp.md` / `choosing-skill-mcp-or-cli.md` を執筆
  - run:08211057a5 — `prompts-and-project-rules.md` / `distribution-and-governance.md` / `webmcp-and-frontier.md` を執筆し、バンドルを完成させた
- **Creation**: `knowledge/agent-capabilities/index.md` を作成（内容一覧・読む順番は `overview.md` の地図表に一元化し重複させない方針）
- **Update**: ルート `knowledge/index.md` に `agent-capabilities/` を1行登録
- **Update**: 台帳13本の「# 活用先」にコンセプト側からの被参照を追記し、コンセプトの出典インラインリンクと双方向で対応させた（本ランでは10本に計12行を追加。`video-tools-webmcp-browser-proposal.md` のプレースホルダ「（コンセプト昇華時に追記）」も実リンクへ差し替え）
- **Fix**: 未執筆コンセプトへの先行言及を `` `ファイル名`（未執筆） `` として退避していた12箇所を、実ファイル作成に伴い Markdownリンク形式（`[ファイル名]` ＋ 相対パス）へ復元（`overview.md` 8・`choosing-skill-mcp-or-cli.md` 2・`what-are-agent-skills.md` 1・`what-is-mcp.md` 1）
- **Note**: 出所が自動生成字幕のみの主張は、コンセプト側で帰属＋「（聞き取り）」を付して断定を避けた。特に `webmcp-and-frontier.md` は WebMCP に関する出所が解説動画1本に限られるため、その旨を本文冒頭に明記したうえで、主要AI製品の対応可否は「公式に確認できていない」という動画の明言をそのまま採用している

## 2026-08-21（tools 記事ソース台帳1本追加 web_ledger run:0821005753）

- **Add**: `knowledge/sources/article-tools-codex-cli-mcp-vs-skill-bash.md` — とつブログ「Claude Code から Codex CLI を呼び出すなら MCP と SKILL/BASH どっちがいい？実際に使って感じたこと」の台帳。CRUD処理はMCP・コード生成/長時間タスクはSKILL/BASH（codex exec）という使い分け、5サーバー58ツールで約55,000トークンという実測値、既知バグ（exit code 0を失敗時にも返すケース）、`codex exec --json`によるプログラム的成否判定、`--full-auto`とresumeによるリトライ活用、MCPのTasksプリミティブ安定化後の判断転換可能性を解説
- **Note**: `knowledge/sources/index.md` の「記事（AIツール活用：Skills/MCP/CLI/プロンプト）」節に上記1件を追加

## 2026-08-21（tools 記事ソース台帳2本追加 web_ledger run:082100456d）

- **Add**: `knowledge/sources/article-tools-mcp-build-server.md` — MCP公式クイックスタート「Build an MCP server」の台帳。MCPサーバーの3大機能（Resources/Tools/Prompts）、Python版の前提要件（Python 3.10以上・MCP SDK 2.0.0以上）、天気情報サーバーの環境構築・実装手順、STDIOサーバーの標準出力書き込み禁止とロギング推奨、Claude for Desktopとの接続設定を解説
- **Add**: `knowledge/sources/article-tools-claude-code-skill-design.md` — Zenn（yamato_snow）「Claude Code Skillの作り方｜21個運用して分かった設計と育て方」の台帳。21個運用の内訳と常用数のギャップ、SKILL.mdのfrontmatter主要フィールド（disable-model-invocation・context: fork・paths）、配置優先順位、/skill-creatorの4モードとEval/Improveの効果、よくある失敗パターン4つ、「引き算のメンテナンス」を解説
- **Note**: `knowledge/sources/index.md` の「記事（AIツール活用：Skills/MCP/CLI/プロンプト）」節に上記2件を追加

## 2026-08-20（tools 記事ソース台帳2本追加 web_ledger run:0820234556）

- **Add**: `knowledge/sources/article-tools-agent-skills-equipping-real-world.md` — Anthropicエンジニアリングブログ「Equipping agents for the real world with Agent Skills」の台帳。Skills開発の動機（procedural knowledgeとorganizational contextの不足）、progressive disclosureの3段階構造、トークン生成よりコード実行が適する場面、開発ガイドライン4点、信頼できるソース限定というセキュリティ指針を解説
- **Add**: `knowledge/sources/article-tools-mcp-architecture-overview.md` — MCP公式ドキュメント「Architecture overview」の台帳。MCP Host/Client/Serverのクライアント・サーバー構造（サーバーごとに専用Clientを1つ生成）、data layer（JSON-RPC）/transport layer（stdio・Streamable HTTP）の2層設計、ステートレスなプロトコル設計、Tools/Resources/Promptsの3大プリミティブを解説
- **Note**: `knowledge/sources/index.md` の「記事（AIツール活用：Skills/MCP/CLI/プロンプト）」節に上記2件を追加

## 2026-08-20（tools 記事ソース台帳2本追加 web_ledger run:08202257d3）

- **Add**: `knowledge/sources/article-tools-agent-skills-overview.md` — Anthropic公式「Agent Skills」の台帳。Skillsの定義とプロンプトとの違い、Pre-built/Custom Skillsの違い、Level1〜3のprogressive disclosure構造、SKILL.mdのfrontmatter必須要件、セキュリティ上の注意点を解説
- **Add**: `knowledge/sources/article-tools-agent-skills-best-practices.md` — Anthropic公式「Skill authoring best practices」の台帳。自由度の3段階設計、gerund形の命名規則、三人称description記述法、SKILL.md500行未満の分割規則、評価駆動開発の5ステップ、MCPツール完全修飾名の必要性を解説
- **Note**: `knowledge/sources/index.md` に新セクション「記事（AIツール活用：Skills/MCP/CLI/プロンプト）」を追加

## 2026-08-20（tools 動画ソース台帳1本追加 research_ledger run:08201857ae）

- **Add**: `knowledge/sources/video-tools-claude-skills-beginner-guide.md` — 「【Claude Skills入門】自分専用のClaude Skillsを作成する方法やSkillsで何ができるのかなどAIのプロがわかりやすく解説します」（いまにゅのAIプログラミング塾）の台帳。SKILL.mdのディスクリプション段階読み込み、MCPとのトークン消費差、図解・アルゴリズミックアート・IBスタイルExcelの実演、.skill形式での配布方法を主張テーブル6行で整理

## 2026-08-20（tools 動画ソース台帳2本追加 research_ledger run:0820174571）

- **Add**: `knowledge/sources/video-tools-webmcp-browser-proposal.md` — 「WebMCPとは何か ブラウザ側で動くMCPの提案」（chronoit）の台帳。4要素構成、サーバー側MCPとの使い分け、Cloudflareのベンダー実装、主要AI製品の対応未確認を主張テーブル5行で整理
- **Add**: `knowledge/sources/video-tools-google-skills-marketplace.md` — 「【Anthropicの標準にGoogleが乗った】google/skillsで何が変わるのか」（クロノITチャンネル）の台帳。109個のSKILL.md規模、progressive disclosure、プラグインmarketplace導入、Apache-2.0ライセンスを主張テーブル4行で整理
- **Note**: `knowledge/sources/index.md` に新セクション「動画（AIツール活用：Skills/MCP/CLI/プロンプト）」を追加（テーマ ai-topics-02-skills-mcp-cli 向けの初回投入）

## 2026-08-20（ragデッキ採点 停滞の手動修正）

- **Fix**: `decks/06-rag/deck.json` の採点指摘を修正。①slide-34の対比表と slide-20 で「ファインチューニング」に初出説明（モデルの重み自体を変える）を追加（severity high。チャット型AIしか使っていない読者に対比の意味が通らなかった）②slide-12の「パース」に初出説明を付け、slide-11の工程名を「取り込み・パース」に揃えて語の揺れを解消 ③slide-22のleadに「コンテキスト＝LLMに一度に渡せる文章のまとまり」を一度だけ補足 ④本文行末の泣き別れ（13枚で発生）に対し `meta.layout_overrides.image_text.body_size` を17に調整
- **Note**: 採点 7/9/9/7/7/9 が2周連続で非改善（stagnation）。未着手は slide-26 の情報過多（Ragas 4トピックを1枚）と、見出しの数字と箇条書き行数の不一致で、スライド分割を伴うため改善ループに委ねた
- **Note**: improve_d のランが許可外パス `tools/check_svg_fonts.py` を作成しようとして封じ込めが作動、`pipeline/staging/quarantine/08200057a1/` に隔離（既存資産の巻き込みではなく工程逸脱の抑止）

## 2026-08-19（rag 採点指摘の修正 improve_k run:0819185771）

- **Fix (f1)**: evaluation.md:107 の評価セット規模「30〜50問」がCitations節の4出典（Ragas／kentarok／Seven Failure Points／TodoONada）のいずれにも根拠がなく、出典なしの数値が手順に置かれていた。数値を削除し「壊れやすい条件を優先して仕込む」のみに留めた
- **Fix (f2)**: failure-modes.md のFP1〜FP7が、原典の適用範囲（英語・研究/教育/バイオメディカルの3領域限定のケーススタディ）に触れないまま日本の社内RAGへ適用されていた。evaluation.mdが既に持つ同種の留保（英語データセットの但し書き）に揃え、FP表の直後に留保文を追加
- **Fix (f3)**: governance-and-adoption.md／build-or-buy.mdの「5段階」（Ollama動画）が、rag-pipeline-stages.mdで統合済みの7工程と接続されないまま提示されていた。5段階が7工程のうち格納・再ランクを明示的に区別しない数え方である旨をgovernance-and-adoption.mdに橋渡し文として追加
- **Fix (f4)**: index.mdの9項目リストがファイル名と見出し語のみで内容一覧として機能していなかった。overview.mdの表（読む順番の地図）から1行要約を転記
- **Fix (f5)**: governance-and-adoption.md:30とbuild-or-buy.md:107で、RAGFlow動画の「入れる文書の質／整理は導入前にやる方が結局早い」がほぼ逐語で重複していた。本籍をgovernance-and-adoption.mdに置き、build-or-buy.md側は1行のポインタへ圧縮
- **Defer (f6, out_of_scope)**: overview.mdとrag-pipeline-stages.mdでauto字幕由来の帰属表記（「auto字幕からの聞き取り」「（聞き取り）」「表記なし」）が事実として揺れていることは確認したが、fix_hintが求める「9コンセプト全体への一括適用」は許可パス外の7ファイルにも及ぶため本工程の範囲では対応できない
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認（生出力は pipeline/logs/run-0819185771.md に記録）

## 2026-08-19（rag 採点指摘の修正 improve_k run:0819151577）

- **Fix (f1)**: rag-origin-and-definition.md:25-32 で seq2seqトランスフォーマー・密ベクトルインデックス・DPR・「エンドツーエンドで微調整」が無定義のまま使われていた。密ベクトルインデックスに補足句、seq2seqトランスフォーマー／ニューラルレトリーバー／DPRに平易な言い換えを括弧内追加、fine-tuneに補足句を追加
- **Fix (f2)**: chunking-and-embedding.md:45 でContextual BM25が初出するが、BM25自体の定義（retrieval-and-reranking.md）へのリンクがなかった。初出箇所に「キーワードの完全一致を見る伝統的な検索手法」の補足句とリンクを追加
- **Fix (f3)**: index.md:11-19 の「## 内容」連番リストがファイル並び順であり、実際の推奨読了順（1→2→5→3→4→6→7→8→9）と異なっていた。リスト直前に「番号は読む順番ではない」旨を明記し、overview.mdの「読む順番の提案」へ誘導
- **Fix (f4)**: build-or-buy.md:88-94 と governance-and-adoption.md:43-49 で、Ollama動画の「5段階のうち何段を外部任せにしたか」という締めくくりと外出し判断指針がほぼ同内容で重複していた。外出し判断の本籍をgovernance-and-adoption.md側に定め、build-or-buy.md側は1文＋リンクに縮約（Citations記載も整合）
- **Fix (f5)**: overview.md:55-59 と governance-and-adoption.md:81 で「最初は便利だったが物足りない」「使っても賢くならない」という同一引用が再掲されていた。governance-and-adoption.md側の引用を削り、overview.mdの「誤解1」への参照に絞った
- **Defer (f6, out_of_scope)**: 「〜が効く」「——」挿入句等の文体反復（9ファイル横断）は事実として確認したが、修正には9ファイル全体のリライトが必要で本工程のスコープを超えるため見送り
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認（生出力は pipeline/logs/run-0819151577.md に記録）

## 2026-08-19（rag採点 停滞の手動修正・読む順の前提と締め句）

- **Fix**: overview.md が示す役割別の読む順番のうち「選ぶ側」経路（1・2・5→7・8）が成立していなかった。`build-or-buy.md` の冒頭が3・4・6を、`governance-and-adoption.md` の冒頭が7を既読前提で書き出していたため、推奨順以外で読むと未読への参照に突き当たる。両ファイルの冒頭を非前提の書き方（「〜で扱う」の予告形）に改め、どちらから読んでも成立するようにした
- **Fix**: 「効く」型の締め句がバンドル全体で反復していた（6ファイル以上）。5箇所を別表現に分散（見過ごせない／外すと痛い／結果を大きく分ける／最後の砦になる／分かれ目になる）
- **Note**: 直前の重複一本化では③⑤が動かず stagnation で停止。今回の指摘は読む順の破綻と修辞の反復という具体的な内容だったため手動修正し再開

## 2026-08-19（rag採点 repair上限の手動修正・重複の一本化）

- **Add**: 9月シリーズ第1弾として `knowledge/rag/` を新設（コンセプト10本・ソース台帳15本＝動画5・記事10）。既存の context-engineering と重複しないよう、検索の作り方・失敗の直し方・評価に軸を置いた
- **Fix**: 採点者が指摘した「同じ主張が複数ファイルに全文再掲される」問題に対し、主張ごとに本籍ファイルを1つ決めて他は要約＋リンクに縮約。①「精度を決めるのはモデルではなくパイプライン設計」を `chunking-and-embedding.md` に一本化 ②SSOT/GIGO を `governance-and-adoption.md` に一本化 ③「会話用LLMと埋め込みモデルは別物」を `chunking-and-embedding.md` に一本化 ④XR-2000/XR-3000 の型番取り違え例を `retrieval-and-reranking.md` に一本化
- **Fix**: `rag-pipeline-stages.md` に混入していた編集方針の説明（auto字幕をどう帰属表記するかというメタ記述）を削除。読者向け本文に編集ルールが露出していた
- **Fix**: `rag-pipeline-stages.md` のパースツール比較（Docling / YomiToku / VLM直読みとライセンス条件）は調達側の判断のため `build-or-buy.md` へ寄せ、1文＋リンクに縮約
- **Fix**: `video-rag-history-mechanism-limits.md` の活用先が、rag-pipeline-stages.md に対してチャンク分割・再ランクの記述を挙げていたが、実際にそれらを書いているのは chunking-and-embedding.md と retrieval-and-reranking.md だった。双方向の記述ずれを実態に合わせて訂正
- **Fix**: リンク欠落2件を追加（overview.md 誤解4 → retrieval-and-reranking.md、failure-modes.md → governance-and-adoption.md）
- **Note**: 採点は 8/7/7/7/7 → 8/8/8/7/7 → 8/8/8/9/7 → 8/8/7/8/7 で repair 3回を使い切り stuck(repair_exhausted)。未達は③構成と⑤文章品質で、原因は共通して「重複」と診断されたため上記を手動修正し `reset-phase.sh grade_k` で再開

## 2026-08-19（rag 採点指摘の修正 improve_k run:0819124573）

- **Fix (f1)**: build-or-buy.md:109 が「RAG全体が砂上の楼閣になります」という警告をrag-pipeline-stages.md:53と逐語で重複していた。build-or-buy.md側をrag-pipeline-stages.mdへのリンク付き要約に置き換え。なおchunking-and-embedding.md:79とevaluation.md:101は既に1文＋リンクの委譲済みで修正不要だった
- **Fix (f2)**: rag-pipeline-stages.md:71 のベクトル検索「疲れた」/「体が重たい」の例が retrieval-and-reranking.md:19 とほぼ同一の全文説明を重複していた。retrieval-and-reranking.mdを本拠とし、rag-pipeline-stages.md側をリンク付き要約に圧縮。overview.md:71は既に簡潔な1文のみで修正不要だった
- **Fix (f3)**: overview.md:67・rag-pipeline-stages.md:26・chunking-and-embedding.md:15で「RAG精度を決めるのはLLM本体ではなく、パイプライン設計です」という同一引用が逐語反復していた。chunking-and-embedding.mdを引用の本拠とし、他2ファイルは引用符を外して要旨＋リンクに変更
- **Fix (f4)**: chunking-and-embedding.md:71とbuild-or-buy.md:67で国産埋め込みモデル（Ruri v3・PLaMo-embedding-1b）の紹介と「完全ローカルのままOpenAI API級の検索品質」「2026年の大きな変化」がほぼ逐語で重複していた。chunking-and-embedding.md側に紹介を残し、build-or-buy.md側を1文＋リンクに圧縮
- **Fix (f5)**: 「たいてい／ほぼ確実に誤解する→反転」という同型の導入修辞がoverview.md:13・rag-pipeline-stages.md:13・rag-and-neighbors.md:13で反復していた。3ファイルとも場面提示から入る書き出しに変更（chunking-and-embedding.md:13も類似構造だが未変更のまま残置。findingsのwhereに含まれていたfailure-modes.md:13-16は診断名の比喩から入る異なる書き出しで該当せず、修正対象から除外）
- **Fix (f6)**: build-or-buy.md:111 が governance-and-adoption.md を「運用とガバナンス」と参照していたが実タイトルは「入れる前と入れた後」だった。実タイトルに統一
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認（生出力は pipeline/logs/run-0819124573.md に記録）

## 2026-08-19（rag 採点指摘の修正 improve_k run:08191015f7）

- **Fix (f1)**: sources/video-rag-history-mechanism-limits.md の活用先に build-or-buy.md:84（高度なRAGの構築・運用コスト言及）が抜けていた。活用先へ1行追加
- **Fix (f2)**: sources/video-rag-sme-adoption-guide.md:78 の活用先が rag-and-neighbors.md を挙げるが、同ファイル:49は「誤解1」の内容をoverview.mdへ委譲するのみで直接引用していなかった。活用先からrag-and-neighbors.mdの行を削除しoverview.md側の記載に集約
- **Fix (f3)**: chunking-and-embedding.md:55・retrieval-and-reranking.md:76の「後で述べる」「この境目については〜で扱う」という前方参照が、推奨読了順（5:failure-modesが3:chunking-and-embedding・4:retrieval-and-rerankingより先）と矛盾していた。両箇所をfailure-modes.mdへのリンク付き既読前提の表現に修正
- **Fix (f4)**: sources/article-rag-*.md のうちanthropic-contextual-retrieval／google-cloud-grounded-gen／openai-file-search／lewis-2020-arxiv／ragas-eval／seven-failure-pointsの6本に「適用範囲と留保」節が欠落していた（既存3本のtodoonada／knowledgesense／qiitaのみ保有）。各記事の内容に応じた留保（ベンダー自己申告値である旨、評価データセットの限定範囲、取得時点の記述である旨）を追加
- **Fix (f5)**: failure-modes.md:66 と governance-and-adoption.md:32 が「組織内情報の分立と件数偏り」の説明をほぼ同文で重複展開していた。failure-modes.md側を本体として残し、governance-and-adoption.md側を1文要約+リンクに圧縮
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認（生出力は pipeline/logs/run-08191015f7.md に記録）

## 2026-08-19（rag 採点指摘の修正 improve_k run:08190745da）

- **Update**: 採点findings（9件）を実ファイル照合のうえ全件fixedとして反映。rag-pipeline-stages.md のパース節にパースツール3系統（Docling／YomiToku／VLM直読み）比較とマルチモーダルRAGへの言及を追加、「分割」「ベクトル化」「再ランク」の説明をchunking-and-embedding.md／retrieval-and-reranking.mdへの1〜2文要約＋リンクに圧縮
- **Update**: build-or-buy.md の4択比較表直後に、方式共通の運用コスト要素（ベクトルDB運用・埋め込み/再ランキング計算・パイプライン最適化・性能評価の難しさ）とYomiTokuのCC BY-NC-SA非商用ライセンス制約を追加
- **Update**: failure-modes.md の retrieval-and-reranking.md への参照を「後述の〜で扱う」という前方参照の書きぶりに修正し、症状表にリンクを追加。「RAGは学習しない」の重複記述をoverview.mdへの1文+リンクに圧縮
- **Update**: rag-origin-and-definition.md に本文中で唯一欠けていた他コンセプトへのリンク（rag-and-neighbors.md、rag-pipeline-stages.md）を追加
- **Update**: retrieval-and-reranking.md の「エージェント的検索」にrag-and-neighbors.mdへのリンクを追加
- **Update**: governance-and-adoption.md・rag-and-neighbors.md の「RAGは学習しない」重複記述をoverview.mdへの1文+リンクに圧縮
- **Update**: sources/article-rag-todoonada-pipeline-guide.md・article-rag-knowledgesense-retrieval-techniques.md・article-rag-qiita-kentarok-poc-production-gap.md に「適用範囲と留保」節を新設（一社/一個人の実務見解であること・数値の時点性・検証範囲の限定を明記）
- **Check**: tools/validate_okf.py knowledge をローカル実行し PASS（生出力は pipeline/logs/run-08190745da.md に記録）。なお「何段を外部任せにしたか」（build-or-buy.md側）と「パイプライン設計」（chunking-and-embedding.md側）の重複は、findingsのwhereに列挙されたファイル外のため今回は未対応（deferredではなくfixed判定の範囲外として明示）

## 2026-08-19（rag バンドル完成 knowledge run:081905159f）

- **Creation**: rag/ に残り2コンセプトを追加し、全10本（overview + 9コンセプト）が揃った。rag-and-neighbors.md（ファインチューニング・会話メモリ・コンパクション・プロンプトキャッシュ・エージェント的検索との切り分けを「何をして何をしないか」で対比し、症状→引き出しの対応表に落とす）、overview.md（一言定義・知識のカットオフとハルシネーションという2つの動機・よくある5つの誤解・9本の地図と役割別の読む順番）
- **Creation**: rag/index.md を作成（内容一覧と、読む順番は overview.md 側で一元管理する旨、関連ディレクトリ context-engineering / graph-engineering への導線）
- **Update**: ルート index.md の「内容」に rag/ を1行登録
- **Update**: sources/ の台帳13ファイルに「活用先」を追記（rag-and-neighbors.md へ7件、overview.md へ6件）。コンセプト側のインライン出典と台帳側の活用先が双方向で対応することを機械照合済み
- **Check**: tools/validate_okf.py knowledge をローカル実行し PASS（生出力は pipeline/logs/run-081905159f.md に記録）

## 2026-08-19（ragソース台帳・記事1本 web_ledger run:0819014585）

- **Creation**: sources/ に記事1本を article-rag-qiita-kentarok-poc-production-gap.md として登録（RAGテーマ、jp-practice subtopic、二次情報、web_ledger工程 run:0819014585）。Qiita「組織内情報集約RAGの実用化設計① なぜPoCレベルで頓挫するのか」（kentarok）。社内RAGのPoCが本番展開で頓挫する根本原因は技術不足ではなく検証設計・評価の見方のズレにあるという立場から、「検索してから答える」というRAGの基本仕組みと検索精度への依存、規程（人事フォルダ）・運用ルール（社内Wiki）・例外（Slack）・経緯（メール）に分立し性質も件数も不揃いな組織内情報の構造的課題、本番展開時に顕在化する5つの失敗パターン（古い情報の使用・最新版の見落とし・矛盾の無視・文書の取り違え・ハルシネーション）、根拠の透明性を問う「信頼できる回答」の5つの確認項目、平均正答率ではなく致命的失敗の発見を目的とする検証設計の役割を解説
- **Update**: sources/index.md の「記事（RAG）」節に上記1件を追加

## 2026-08-19（ragソース台帳・記事2本 web_ledger run:08190057ad）

- **Creation**: sources/ に記事2本を article-rag-*.md として登録（RAGテーマ、jp-practice subtopic、二次情報2本、web_ledger工程 run:08190057ad）。article-rag-todoonada-pipeline-guide.md（TodoONada株式会社「社内文書RAGの作り方2026。パース・埋め込み・リランクの最新構成」、二次情報。「RAG精度を決めるのはLLM本体ではなく、パイプライン設計です」という前提のもと「パース→埋め込み→検索→リランク」の4段パイプラインを提示。パース段階の三大障害（PDFレイアウト崩れ・罫線帳票・スキャン画像）とDocling/YomiToku/VLM直読みの3ツール系統、国産埋め込みモデルRuri v3・PLaMo-embedding-1bによる完全ローカル化、ベクトル検索の型番混同弱点を補うBM25とのハイブリッド検索が実務標準である点、国産リランカーを最も費用対効果の高い一手と評価する点、規模別構成例（個人〜小規模はOllama+AnythingLLM、部門規模はvLLM+ハイブリッド検索+リランカー）、RAGで解決しない文体学習はLoRA領域という切り分けを解説）、article-rag-knowledgesense-retrieval-techniques.md（Zenn「RAGでの回答精度向上のためのテクニック集（応用編-A）」株式会社ナレッジセンスCEO門脇篤志氏、二次情報。LlamaIndexのRAGチートシートの翻訳・解説で、RAG精度向上を「①ドキュメント抽出」「②回答生成」の2柱に分解し①に焦点。チャンク分割の最適化（マイクロソフト研究によるチャンクサイズの性能影響）、ハイブリッド検索（キーワード50%・セマンティック50%のブレンド例）、HyDE（ダミー回答生成によるセマンティック検索、得意・不得意領域が明確）、情報の構造化（親ノードによる木構造検索）、メタデータの付加、ナレッジグラフと埋め込みモデルのファインチューニング（上級テクニック）の7手法と「成果が出そうなものから取り組む」という優先順位付けの推奨を解説）
- **Update**: sources/index.md の「記事（RAG）」節に上記2件を追加

## 2026-08-19（ragソース台帳・記事2本 web_ledger run:08190045b0）

- **Creation**: sources/ に記事2本を article-rag-*.md として登録（RAGテーマ、arXiv一次情報2本、web_ledger工程 run:08190045b0）。article-rag-seven-failure-points.md（arXiv/CAIN2024「Seven Failure Points When Engineering a Retrieval Augmented Generation System」Barnett et al.、一次情報。RAGシステムの典型的な失敗点をFP1〜FP7の7種に整理（Missing Content/Missed the Top Ranked Documents/Not in Context - Consolidation Strategy Limitations/Not Extracted/Wrong Format/Incorrect Specificity/Incomplete）、研究領域のCognitive Reviewer・教育領域のAI Tutor・バイオメディカル領域のBioASQ（4017件の文書と1000問の質問）という3ケーススタディでの実証、「RAGシステムの検証は実運用時にしか実現できず、堅牢性は設計時に組み込まれるのではなく段階的に発展する」という結論を解説）、article-rag-ragas-eval.md（arXiv/EACL2024「Ragas: Automated Evaluation of Retrieval Augmented Generation」Es et al.、一次情報。人間作成のground truthアノテーションに依存しないreference-free評価フレームワークRagasが提案するFaithfulness（陳述文抽出とコンテキスト照合によるF=|V|/|S|）・Answer Relevance（仮想質問生成と埋め込み余弦類似度によるAR）・Context Relevance（重要文抽出比率によるCR）の3指標、WikiEval（Wikipedia50ページ）での人間評価との一致率（Faithfulness 0.95・Answer Relevance 0.78・Context Relevance 0.70、GPT Score/GPT Rankingより高精度）を解説）
- **Update**: sources/index.md の「記事（RAG）」節に上記2件を追加

## 2026-08-18（ragソース台帳・記事2本 web_ledger run:0818234501）

- **Creation**: sources/ に記事2本を article-rag-*.md として登録（RAGテーマ、公式ドキュメント・原典論文各1本、web_ledger工程 run:0818234501）。article-rag-google-cloud-grounded-gen.md（Google Cloud公式「Generate grounded answers with RAG | Agent Search」、一次情報。RAGを「データソースから事実を取得し根拠のある回答を生成する2段階プロセス」と定義、`generateGroundedContent`/`streamGenerateGroundedContent`の2 API、Google Search/インラインテキスト（最大100 fact text）/Agent Search data storesの3種の接地ソースと組み合わせ時最大10個の制約、動的取得の予測スコアとデフォルトしきい値0.7、grounding score・supportChunks・groundingSupport・webSearchQueriesを含むレスポンス構成、マルチターン会話での過去全文送信要件を解説）、article-rag-lewis-2020-arxiv.md（arXiv/NeurIPS2020「Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks」Lewis et al.、一次情報。「RAG」という略称・アーキテクチャの起源となった原典論文。事前学習済みseq2seqトランスフォーマーのparametric memoryとWikipedia密ベクトルインデックスのnon-parametric memoryを組み合わせエンドツーエンドで微調整する構成、3つのオープンドメインQAタスクでの当時の最先端達成、パラメトリック単体ベースラインより具体的・多様・事実的な言語生成を行うという主張を解説）
- **Update**: sources/index.md の「記事（RAG）」節に上記2件を追加

## 2026-08-18（ragソース台帳・記事2本 web_ledger run:08182245b0）

- **Creation**: sources/ に記事2本を article-rag-*.md として登録（RAGテーマ、公式ドキュメント2本、web_ledger工程 run:08182245b0）。article-rag-anthropic-contextual-retrieval.md（Anthropic公式「Contextual Retrieval in AI Systems」、二次情報。従来のRAGがチャンク分割により個別チャンクの文脈を欠く問題からの出発点、埋め込み・検索インデックス作成前にチャンク固有の説明文脈を追加するContextual EmbeddingsとContextual BM25の2サブ技術、Claude 3 Haikuへのプロンプトによる文脈自動生成とプロンプトキャッシングによる100万ドキュメントトークンあたり$1.02という一度きりの処理コスト、複数ドメイン実験での検索失敗率5.7%→Contextual Embeddingsのみで3.7%（35%削減）→BM25併用で2.9%（49%削減）→リランキング併用で1.9%（67%削減）という段階的改善を解説）、article-rag-openai-file-search.md（OpenAI公式「File search」、二次情報。Responses APIで利用可能なホスト型検索ツールがベクトルストア作成とファイルアップロードのみでモデルの知識を拡張できコード実装が不要である点、Vector Store作成からFiles API登録・vectorStores.files.create()での関連付け・ステータスcompleted確認までの3段階アップロード手順、23種類以上の対応ファイル形式とutf-8/utf-16/asciiのエンコーディング要件、max_num_results・filtersパラメータによる検索カスタマイズ、Tier別に毎分100〜1000リクエストのレート制限を解説）
- **Update**: sources/index.md に「記事（RAG）」節を新設し上記2件を追加

## 2026-08-18（ragソース台帳・動画1本 research_ledger run:08181745ed）

- **Creation**: sources/ に動画1本を video-rag-ollama-local-privacy.md として登録（RAGテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:08181745ed）。「社内文書を外に出さずAIに検索させる、Ollamaローカル型RAGの作り方【ずんだもん解説】」（ずんだもんのAI図鑑、2分51秒、自動字幕）。社内資料をAIに検索させると外部に漏れるのではという懸念を入り口に、取り込み・分割・ベクトル化・検索・生成の5段階に分解したRAGパイプライン全体を手元PCで動かす構成、手元完結によるコストメリット（電気代とマシン代のみ）、会話用LLMと埋め込みモデルの役割の違い・日本語では多言語対応埋め込みモデルを選ぶべきという点、RAGとエージェントの違い、社外に出せない文章か否かによる導入判断基準を解説
- **Update**: sources/index.md の「動画（RAG）」節に上記1件を追加

- **Creation**: sources/ に動画2本を video-rag-*.md として登録（RAGテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:08181710a9）。video-rag-sme-adoption-guide.md（株式会社文武堂「RAG（検索拡張生成）とは？」、10分48秒、自動字幕）。中小企業の経営者・担当者向けに、RAGの仕組み（就業規則の具体例）、RAGを賢くする2つの鉄則（SSOT・GIGO）、導入の4レベル（個人プラン→チーム→社内システム連携→フルスクラッチ）、無料版のリスクと安全に使うための4チェック、「RAGは学習しない・運用して育てるもの」という考え方を解説。video-rag-ragflow-oss-intro.md（さつきのOSS研究室「RAGFlow入門｜社内文書を答えるAIに変えるオープンソースRAGエンジン」、13分20秒、自動字幕）。OSS RAGエンジン「RAGFlow」（infiniflow/ragflow）の機能・LangChain/LlamaIndex/Difyとの違い・始め方（クラウド版→セルフホスト）・Apache 2.0ライセンスの条件・3つの導入事例（総務QA・カスタマーサポート・プリセールス）・セルフホスト運用の注意点を解説
- **Update**: sources/index.md の「動画（RAG）」節に上記2件を追加

## 2026-08-18（ragソース台帳・動画2本 research_ledger run:0818170467）

- **Creation**: sources/ に動画2本を video-rag-*.md として登録（RAGテーマ、字幕全文から要約・主張テーブルつき、research_ledger工程 run:0818170467）。video-rag-history-mechanism-limits.md（AIの履歴書「検索拡張生成(RAG)とは？LLMの嘘と知識不足を克服する仕組みを歴史から最新技術まで解説」、11分18秒、自動字幕）。知識のカットオフとハルシネーションという2課題からRAGが生まれた経緯、Lewisらの2020年論文への言及、標準パイプラインの4段階（インデクシング・リトリーバル・ランキング・ジェネレーション）、チャンク分割やリコール/プレシジョンのトレードオフといった実装上の課題、クエリ変換・ハイブリッド検索・Parent Document Retriever・Self-RAG・マルチモーダルRAGといったアドバンストRAG技術を解説。video-rag-supabase-diy-chatbot.md（KIZUKI PROJECT「社内文書や個人メモを学習させずに回答させるAIの作り方！SupabaseとClaude/OpenAIで作る自作RAGシステムを解説」、18分41秒、自動字幕）。RAGの3ステップ（変換・保管／検索／生成）とベクトルデータベースの意味検索の仕組みを説明したうえで、Claude CodeとSupabase Vectorを使い約15分で自作RAGチャットボットを構築する実演、精度を上げるコツ（チャンクサイズ調整・プロンプト制約・検索件数調整）を解説
- **Update**: sources/index.md に「動画（RAG）」節を新設し上記2件を追加

## 2026-08-17（ge ナレッジ完成・manual_override受理）

- **Add**: `graph-engineering/` を9コンセプト→**15コンセプト**に拡充。新規6本（workflow-patterns-catalog / multi-agent-break-even / failure-taxonomy-and-debugging / handoffs-and-ownership / subagent-design-in-practice / verification-gates-and-evidence）はすべて公式ドキュメント・論文を主根拠とする。既存9本は上書きせず、出典補強と前方リンク追加にとどめた
- **Add**: ソース台帳を11本→**21本**（新規10本＝動画3・記事7）。追加分は Anthropic公式（Building Effective AI Agents / multi-agent research system / C compiler）、OpenAI公式（orchestration・handoffs）、arXiv（MAST・GPTSwarm）などで、着手前ゼロだった一次資料の穴を解消。独立origin 6種→15種
- **Note**: 採点は9周で 7/6/6/7/6 → 7/7/7/7/7 → 7/7/6/6/6 → **8/8/8/7/7** → 8/7/7/8/7 → 8/7/7/9/7 → **7/8/8/8/7** → 7/8/7/6/7。5項目すべてが途中で8点以上に到達しているが、同一内容でも項目4が9点→6点に振れるなど採点者間のばらつきが大きく、5項目同時の8点達成には至らなかった。grade_k が run_cap 10/10 に到達したため、最良周（8/8/8/7/7 および 7/8/8/8/7）の水準で **manual_override 受理**しdraftへ
- **Note**: 受理にあたり、指摘のうち実質的なものは2回に分けて手動修正済み（8/16: 旧台帳11本のメタデータをyt-dlp実取得で補完、Orchestrator-workersの分類訂正、伝聞と一次資料の突き合わせ、目録一元化、前方リンク5件 ／ 8/17: 行数の確度不一致、数値3件の出典リンク、語彙の前方参照注記、roles主要5節の出典リンク）。保留したのは `graph-primitives.md`（12節）と `roles-and-orchestration.md`（10節）のファイル分割と、「作る役と通す役を分ける」説明の4箇所重複の一本化で、いずれも既存資産の大規模再編にあたるため

## 2026-08-17（graph-engineering 採点指摘の修正 knowledge run:081704574a）

- **Fix (f1)**: overview.md:55の「同動画は、Claudeデスクトップアプリのエフォートレベル『ウルトラコード』...」が、直前の[Gao Dalie動画]の段落を受ける「同動画」表記になっていたが、ウルトラコード/ウルトラの記述は実際にはにゃんた動画（video-ge-nyanta-loop-graph-claude-code.md:50）の内容だった。「同動画」を「[にゃんた動画]」への明示リンクに置換
- **Fix (f2)**: verification-and-testing.md:19-23のRefineBenchの数値（98.4%/75.8/94.7）が「論文の実験結果」として断定され、聞き取り由来であることを示す注記が無かった（同じ数値をloop-engineering/maker-checker-separation.mdは「動画がその論文の結果として紹介しているものであり、本教材では論文原典に当たっていない」と明記済み）。節冒頭に論文原典未確認の1文を追加し、各数値に「（動画の紹介・聞き取り）」を付記
- **Fix (f3)**: overview.md:60の「混同すると初心者は迷子になると両ソースとも警告している」が、実際にはAI氣道動画のみが「初心者は迷子になる」と警告しており（video-ge-5-stages-beginner.md:70）、これマジ?動画はTuring Post引用で「4つの意味が混在している」と指摘するのみで「迷子」という警告表現は無かった（video-ge-koremaji-single-to-multi.md:56）。主体を分けて記述するよう修正
- **Fix (f5)**: graph-primitives.md:65とrisks-and-safeguards.md:72が、請求書処理5ノードの図と「業務の言語化の限界がAI化の限界につながる」という結論をほぼ同文で相互参照なしに全文展開していた。結論の説明はrisks-and-safeguards.md側に残し、graph-primitives.md側はノード構成の列挙のみ残して結論部分を1文+リンクへ縮約
- **Fix (f6)**: roles-and-orchestration.md:74とrisks-and-safeguards.md:39が、アドバイザーパターンの「約92%・約63%」の説明（Sonnet 5+Fable 5、SWE-bench Pro、呼び出し頻度）をほぼ同文で二重展開していた。risks側は「独り歩きする数字」という論点（公開日・特定条件下の数字である点）に絞り、数値の内訳説明はroles側参照へ短縮
- **Fix (f4)**: overview.md:8ほか計9ファイル（graph-primitives/knowledge-graph-as-memory/loop-vs-graph-decision/relationship-graph-for-operations/risks-and-safeguards/roles-and-orchestration/term-lineage-and-layers/verification-and-testing、いずれもfrontmatter `generated.at: 2026-08-09`）が、git履歴上は2026-08-16・2026-08-17にも複数回の内容改訂を経ていることを確認した。本バンドルでは`generated.at`をコンセプトの**初出（新規作成）日時**として扱い、その後の改訂は本ファイル（log.md）の変更履歴側で追跡する方針とし、これを明文化する。frontmatter日付は改訂の都度更新しない
- **Check**: `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認（下記CHECK行参照）

## 2026-08-17（graph-engineering 採点指摘の修正 knowledge run:081703457a）

- **Fix (f1)**: video-ge-bpo-org-chart.md:47-58の請求書処理5ノード編成（受付AI・読み取りAI・仕訳AI・チェックAI・人間承認者）の具体例が未収載だった。graph-primitives.mdの「迂回路」節に追記
- **Fix (f2)**: video-pe-five-engineering-stages.md:60-72の症状別使い分け・モデル配分の考え方・AI100ライター/LPビルダーの分業実例が未収載だった。loop-vs-graph-decision.mdに症状別使い分け節を新設、roles-and-orchestration.mdのアドバイザーパターン節にモデル配分・分業実例を追記
- **Fix (f3)**: article-ge-anthropic-building-c-compiler.md:47の制限事項（16ビットx86生成不可・GCC依存、アセンブラ/リンカ不安定、最適化無効時の非効率性）とLinux 6.9マルチアーキ対応が未収載だった。multi-agent-break-even.md:35の99%合格率の直後に追記
- **Fix (f4)**: video-ge-gaodalie-forget-loop.md:29の「古くからの問題5点」（タスク分割・依存関係の表現・並列化の判断・障害復旧・状態の保存先）が未収載だった。overview.mdの「ワークフローの言い換えという見方」節にGao Dalie側の独立originとして追記
- **Fix (f6)**: verification-and-testing.md:86の境界宣言（検証役を分ける理由はここで扱う）と、verification-gates-and-evidence.md:78-88「採点者を分ける」節が同主題を再展開しており分担が崩れていた。後者を段階4の終了条件設計（合格基準・回数上限）に絞り、理由説明を前者への参照1行に置き換え
- **Fix (f7)**: verification-gates-and-evidence.md/handoffs-and-ownership.md/subagent-design-in-practice.md（いずれも2026-08-16生成）が、relationship-graph-for-operations.md（2026-08-09生成）と比べ結論文全体を太字強調する箇所が多く文体差があった。3ファイルの過剰な太字を整理。チェックリスト等の番号リスト構造は情報量維持のため保持し、全ファイル統一までは行っていない部分対応
- **Fix (f8)**: 「AIは自分の成果物を甘く評価するので生成役と評価役を分ける」という結論がverification-and-testing.md/verification-gates-and-evidence.md/subagent-design-in-practice.mdで反復されていた。verification-and-testing.md:25を唯一の説明箇所とし、subagent-design-in-practice.md:77の理由説明部分を参照1行に短縮（verification-gates-and-evidence.md分はf6の修正で解消）。workflow-patterns-catalog.md:66,98は既に妥当な状態のため変更不要と確認
- **Defer**: f5（graph-primitives.mdが177行で他コンセプトファイル平均の約1.7倍、10節超が1ファイルに混在）は指摘は事実だが、fix_hintが求める本質的対応（隠れたエッジ・実践ステップ節の別コンセプトへの分離）は参照元10ファイル（うち3ファイルは節単位で直接参照）のリンク修正とoverview.mdのバンドル地図再設計を伴う構造変更であり、findings単位の局所修正を前提とする本工程の範囲を超えるためdeferred(out_of_scope)。前回run（081702592f元のNote）でも同種の構造分割指摘が同じ理由で保留されている
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認

## 2026-08-17（ge採点 repair上限の手動修正・findings 4系統）

- **Fix**: `risks-and-safeguards.md` の Citations が約75万行を「Bunの書き換え規模」と断定していたが、`graph-primitives.md:144` は同一プロジェクトと断定できないとしており、バンドル内で確度が不一致だった。graph-primitives 側の確度に揃えて「同種のZig→Rust移植（同一プロジェクトかは断定できない）」に修正
- **Fix**: `risks-and-safeguards.md` の「独り歩きしがちな数字」節は、出所を辿らせることが目的の節でありながら 92%/63%・25.6/14.7・18%/85% のいずれにも出典リンクが無かった。3件すべてに台帳へのインラインリンクを追加
- **Fix**: `term-lineage-and-layers.md` の3層対比表が「トポロジー・ノード・エッジ・状態」を定義前に使っていた（定義は読む順番2番目の graph-primitives）。表の直前に、語の定義先へのリンクと「ここでは『誰と誰をどうつなぐかの形』程度の理解でよい」という読み進め方の注記を追加
- **Fix**: `roles-and-orchestration.md` は本文10節に対しインラインリンクが3箇所しかなく、三役分担・CAID・Google ADK 2.0の原則・アドバイザーパターン・Claude Code/Codexの機能は末尾Citationsへ戻らないと出所に辿れなかった。主要5節の初出位置に出典リンクを追加
- **Note**: 採点は 8/8/7/7/7 で repair 3回を使い切り stuck(repair_exhausted)。未達3項目のうち、指摘のうち「graph-primitives.md（12節）と roles-and-orchestration.md（10節）が1ファイル=1概念として大きい」という構造分割と、「作る役と通す役を分ける」説明が4箇所に重複している件は、既存資産の大規模な再編にあたるため自動改善ループに委ねず保留した

## 2026-08-17（graph-engineering 採点指摘の修正 knowledge run:0817014547）

- **Fix (f1)**: workflow-patterns-catalog.md:57のダイナミックワークフロー導入節が、ソース側（video-ge-dynamic-workflows-six-patterns.md c1, impact:high）が明記する「長いコンテキストで起きるサボりや自己バイアスを構造的に防ぐ」という目的に触れず仕組みの説明のみだった。6型が評価型に偏る理由としてこの目的を1文追記
- **Fix (f2)**: video-ge-koremaji-single-to-multi.md:43-44「最強モデルを全ノードに置いても設計問題は消えない、同じ誤った前提を共有し無条件承認すれば誤りが循環する」という中核主張が、どのコンセプトにも未収録だった。risks-and-safeguards.mdに「能力の足し算では解けない」節を新設
- **Fix (f3)**: workflow-patterns-catalog.md:19-29のWorkflow/Agent定義節に、article-ge-anthropic-building-effective-agents.md:41が挙げるAgent側のgrounded truth取得（環境からのフィードバックでループする）が未反映だった。1文追記
- **Fix (f4)**: subagent-design-in-practice.md:35-43の設定項目表からhooks・mcpServersが欠落しており、ツール権限事故の主題で書き込み系コマンドのブロック手段が示せていなかった。表に2行追加
- **Fix (f5)**: loop-vs-graph-decision.mdに、video-ge-gaodalie-forget-loop.md:54-55の決済システム再構築の複数ドメイン例と「次に何をするか」から「各ノードが何を出力・宣言・待つか」への問いの転換が未反映だった。「過剰なグラフ化への警告」節に具体例を追記
- **Fix (f6)**: knowledge-graph-as-memory.md:86-88の「次に読む」が、overview.mdの読む順番表（#13→#14）に反し既読3本（#7/#9/#12）への差し戻しになっていた。筆頭をrisks-and-safeguards.mdに差し替え、既読3本は本文インライン参照へ移動
- **Fix (f7)**: roles-and-orchestration.mdが11見出しを収容し、うち「Anthropicの5つの連携パターン」節（workflow-patterns-catalog.mdと重複）と「組織/作業グラフ」の説明（relationship-graph-for-operations.mdと重複）を1文+参照へ縮約
- **Fix (f8)**: graph-primitives.md:86-97（バンドル#2、語彙習得の位置）にあったフレームワーク6種の詳細数値（月間DL数千万・A2A・2026年4月GA等）を、名前と一言特徴のみへ圧縮
- **Fix (f9)**: overview.md:59とterm-lineage-and-layers.md:73-81が「詳細はknowledge-graph-as-memory.mdに譲る」と宣言しながら「実行の地図/ループの網/知識の地図」等の全項目をフル列挙していた。列挙を削除し参照のみに変更
- **Fix (f10)**: term-lineage-and-layers.md:89,96で「関連コンセプト」節（14ファイル中この1本のみに存在）と「次に読む」節が2本のリンクで重複していた。「関連コンセプト」節を削除し、overview.mdへのリンクは冒頭段落へインライン化
- **Fix (f11)**: handoffs-and-ownership.md:70が「詳細はmulti-agent-break-even.mdで扱う」と宣言した直後にOpenAIの4条件の中身をフル記載していた。1文へ縮約
- **Fix (f13)**: roles-and-orchestration.md:44とrisks-and-safeguards.md:44が共に「詳細はgraph-primitives.mdへ」としながらBunの規模の食い違い数字（53万行/75万行）自体を再掲していた。他2ファイルから数字を削除し参照のみに統一
- **Defer**: f12（multi-agent-break-even・workflow-patterns-catalog・handoffs-and-ownership・subagent-design-in-practice・verification-gates-and-evidence・failure-taxonomy-and-debuggingの6ファイルのみが番号付き総括節と太字教訓の修辞を共有し、他8ファイルと二分している）は指摘自体は事実だが、fix_hintが要求する14ファイル横断のスタイル統一は非対象8ファイルへの変更を伴い、本工程の許可パス（findingsのwhereが指すファイルのみ）を超えるためdeferred(out_of_scope)
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認

## 2026-08-17（graph-engineering 採点指摘の修正 knowledge run:0817004581）

- **Fix (f1)**: workflow-patterns-catalog.md・verification-gates-and-evidence.mdの2本だけ「## 次に読む」節が無く、overview.mdの推奨順（7→8, 11→12）の導線が途切れていた。両ファイルのCitations直前に同節を追加し、それぞれrelationship-graph-for-operations.md・failure-taxonomy-and-debugging.mdへ送る
- **Fix (f2)**: article-ge-anthropic-building-c-compiler.mdの活用先にroles-and-orchestration.mdが抜けていた（roles-and-orchestration.md:38が同記事をDockerコンテナ隔離・役割専門化の根拠に使用済み）。活用先へ項目を追加
- **Fix (f3)**: video-ge-5-stages-beginner.mdの活用先にrelationship-graph-for-operations.mdが抜けていた（同ファイル:25が「仕事の地図」の4項目の根拠に使用済み）。活用先へ項目を追加
- **Fix (f4)**: video-ge-kininarundamon-parallelism.mdを参照する5本（graph-primitives.md, loop-vs-graph-decision.md, risks-and-safeguards.md, roles-and-orchestration.md, term-lineage-and-layers.md）でCitations表記が4パターンに割れていたのを正式タイトル（【気になるんだもん No.02】その順番待ち、ほんとに要るのだ？ 〜グラフエンジニアリング〜（ずんだもんの実験道具箱））に統一。本文中の呼称も「ずんだもん」に統一
- **Fix (f6)**: loop-vs-graph-decision.md:83が偽エッジテスト・Bunの隠れたエッジの説明をgraph-primitives.md:125-150と重複させたまま参照リンクを欠いていた。詳細をgraph-primitives.mdへ委譲する3文へ圧縮しリンクを追加
- **Defer**: f5（2026-08-16生成6本と2026-08-09生成8本の文体・粒度の二層化）は文体差自体は実際に確認できたが、修正が14本全体の全面リライトに及び、本工程の許可パス（findingsのwhereが指すファイルへのピンポイント修正）を超えるためdeferred(out_of_scope)
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認

## 2026-08-16（graph-engineering 採点指摘の修正 knowledge run:0816224533）

- **Fix**: 採点findings 12件のうち10件（fixed disposition）に基づき既存コンセプトを修正。overview.mdの「前半8本=動画・後半6本=公式」という出典内訳の誤りを、各ファイルのCitations節から実測した内訳に基づき表の「主根拠」列として訂正。graph-primitives.md:113・roles-and-orchestration.md:33,74の旧形式台帳（主張テーブルなし）由来の数値（同時実行64/合計1000、CAID 25.6/14.7ポイント、アドバイザー約92%/約63%）に「（聞き取り）」の確度注記を追加
- **Fix**: term-lineage-and-layers.md・graph-primitives.mdの「次に読む」がoverview.mdの推奨順（#3 loop-vs-graph-decision）を飛ばして#7へ誘導していた誤りを是正。「次に読む」節を欠いていた7ファイル（loop-vs-graph-decision・multi-agent-break-even・handoffs-and-ownership・relationship-graph-for-operations・failure-taxonomy-and-debugging・subagent-design-in-practice・risks-and-safeguards）に同節を新設
- **Update**: knowledge-graph-as-memory.md（本文の出典が匿名参照のみでインラインリンクが皆無だった）に3出典への本文内リンクを追加。relationship-graph-for-operations.md・verification-and-testing.md・risks-and-safeguards.mdにも主根拠へのインラインリンクと主体を明示する文（「同動画は」等）を追加し、受け身表現の連続を解消
- **Refactor**: verification-and-testing.md・knowledge-graph-as-memory.mdの箇条書き偏重を是正。各節冒頭に論旨を述べる地の文を追加し、本質的な列挙（数値比較・手順・条件リスト）のみ箇条書きとして残す文体に書き換え
- **Fix**: sources側の活用先の食い違いを是正。video-ge-gaodalie-forget-loop.mdの活用先（overview.md欄）を実際の引用内容（用語の登場経緯ではなく一言定義・3層対比）に修正、video-ge-5-stages-beginner.mdの活用先からknowledge-graph-as-memory.mdに存在しない体験談の記述を削除（risks-and-safeguards.md欄に同内容が既にあるため重複解消）。term-lineage-and-layers.md・knowledge-graph-as-memory.mdのCitations表記（チャンネル名欠落・説明句表記）を「タイトル（チャンネル名）」形式に統一
- **Update**: コンセプト側に居場所のなかった7つの主張を各対応ファイルへ1〜2文で追記。roles-and-orchestration.md（16エージェントの役割専門化とDockerコンテナ隔離）、workflow-patterns-catalog.md（GPTSwarmのMini Crosswords評価結果）、relationship-graph-for-operations.md（AI氣道の「仕事の地図で読む4情報」）、loop-vs-graph-decision.md（グラフ化の「揺り戻し」の指摘）、overview.md（Gao Dalieの「登場から3日」）、risks-and-safeguards.md（ずんだもんの「実信号を1つ置く」対策）、subagent-design-in-practice.md（サブエージェントのパーミッションモード6種）
- **Defer**: f5（graph-primitives.mdが1ファイル=1概念を超過、フレームワーク一覧の切り出しが必要）はバンドル全体の再採番・相互参照更新を要し、本工程の許可パス（findingsのwhereが指すファイルのみ）を超えるためdeferred(out_of_scope)
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認
- **Note**: 本ランはfindingsの`where`が指すファイルのみを修正対象とし、それ以外のコンセプトファイルは書き換えていない

## 2026-08-16（ge採点停滞の手動修正・findings 7件）

- **Fix (f14)**: パイプライン以前に作られた `video-ge-*` 台帳11本に `origin` / `subs` / `retrieved` が無く、コンセプト側の「（聞き取り）」注記を採点者が照合できない状態だった。yt-dlp で配信元へ再照会し、**実データ**（チャンネルID・字幕の提供状況）を取得して補完。`retrieved` は frontmatter の `generated.at` を採用し、各ファイルに「2026-08-16に再照会で補完した」「主張テーブルは当時の形式に無い」旨を明記した。独立origin数 6種→15種
- **Fix (f1)**: `workflow-patterns-catalog.md` の型選びまとめが Orchestrator-workers を「Agent側」と分類しており、同ファイル冒頭に引用したAnthropic公式の定義（5つのWorkflowパターンの1つ）と矛盾していた。公式分類に合わせて訂正し、公式のAgentは5つの型のいずれとも別区分である旨を追記
- **Fix (f2)**: `verification-and-testing.md` の「Opus 5では検証用サブエージェントは不要と公式案内がある」という動画由来の伝聞が、同バンドルの一次資料（Anthropic公式 Best practices for Claude Code、検証サブエージェントを強制力の最上位に位置づけ）と逆を向いたまま放置されていた。伝聞であることを明示し、一次資料側へリンクして「設計判断は検証役を分ける側に寄せるのが安全」と注記。双方向リンク（Citations ⇄ 活用先）も追加
- **Fix (f3)**: `overview.md` の「生まれて3週間」（動画公開 7/28 時点）が、本バンドルの記録する発端 7/18 と約10日で計算が合わない点を注記
- **Fix (f11/f13)**: `index.md` の一覧順が `overview.md` の推奨順と不一致で、かつ同じ目録を二重管理していた。推奨順と同じ並びに直し、説明は見出し語のみとして内容説明は overview.md 側に一元化
- **Fix (f12)**: 新規5本への前方リンクが欠落していた。`verification-and-testing`→`verification-gates-and-evidence`（直系の続編）、`roles-and-orchestration`→`handoffs-and-ownership` など5ファイルに「次に読む」節を追加
- **Note**: 採点は 7/6/6/7/6 → 7/7/7/7/7 → 7/7/7/7/6 と停滞（stagnation）。findings 16件のうち上記7件を手動修正し `reset-phase.sh grade_k` で再開。未着手は f5〜f8（ソース未回収の主張）・f9（graph-primitives.md が1ファイル=1概念を超過）・f15（重複説明3系統）で、これらは改善ループに委ねた

## 2026-08-16（graph-engineering 採点指摘の修正 knowledge run:081617451a）

- **Fix**: 採点findings 15件（すべてfixed disposition）に基づき既存コンセプトを修正。risks-and-safeguards.md:81のトークンコスト注記誤り（「単一比15倍」→「チャット比15倍・単一エージェントはチャット比4倍」）、overview.md:13の下位コンセプト数誤記（「8つ」→「14の下位コンセプト」）、risks-and-safeguards.md:44のBun行数食い違いの断定表現をgraph-primitives.mdの留保表現に統一
- **Update**: failure-taxonomy-and-debugging.mdの実地失敗表に「単一タスク固定で全エージェントが同じバグで停止」を1行追加（出典: article-ge-anthropic-building-c-compiler.md）、デバッグ指針にシミュレーション駆動開発を1項追加（出典: article-ge-anthropic-multi-agent-research-system.md）。subagent-design-in-practice.mdに実行モード（フォアグラウンド/バックグラウンド）と「サブエージェントとエージェントチームの使い分け」節を追加。handoffs-and-ownership.mdにメモリ層への計画保存という実装注意を1文追加。graph-primitives.mdに「タスクグラフ・依存関係グラフ・DAG」の用語整理を追加。term-lineage-and-layers.mdのCitationsに判定エンジニアリングの出典動画を追加
- **Refactor**: risks-and-safeguards.mdの「本番運用の設計判断」節を「歯止めが機能する前提としての運用要件」に縮約（1ファイル=1概念の逸脱を是正）。index.mdの読む順番節をoverview.mdの順序表への参照に一本化（2箇所管理の食い違いを解消）。relationship-graph-for-operations.md・verification-and-testing.mdのH1からサブタイトルを除去し他14本と統一。workflow-patterns-catalog.md・handoffs-and-ownership.md・verification-gates-and-evidence.md・subagent-design-in-practice.mdのエッセイ調リード文・呼びかけ表現を平叙文に書き換え
- **Fix**: sources側の活用先の食い違いを是正。video-ge-caleb-8min-explainer.mdの活用先にloop-vs-graph-decision.mdを追加、video-ge-kininarundamon-parallelism.mdの活用先理由を「判定エンジニアリング」の紹介に修正、video-ge-gaodalie-forget-loop.mdの活用先を実際の引用内容（承認経路の例／表形式データ対比）に合わせて割り当て直し
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認
- **Note**: 本ランはfindingsの`where`が指すファイルのみを修正対象とし、それ以外のコンセプトファイルは書き換えていない

## 2026-08-16（graph-engineering 採点指摘の修正 knowledge run:081615158d）

- **Fix**: 採点findings 13件（すべてfixed disposition）に基づき既存コンセプトを修正。graph-primitives.md:103の同時実行上限誤記（「最大16」→「16どころか2桁（64）」、AISPALab概要欄との「一致」の誤った主張を「食い違い」に訂正）／overview.mdの数値誤記（「3本の比喩」→「これらの比喩」、「8つの下位コンセプト」→「14の下位コンセプト」）とバンドル地図の8本時代からの拡張（後半6本を含む14項目化、読む順番をindex.mdの差し込み案と統一、後半6本への内部リンク配置）
- **Update**: workflow-patterns-catalog.mdに「呼び出し方とトークン予算」小節（ウルトラコード起動・出典検証構成・編成保存・トークン予算指定）を追加、subagent-design-in-practice.mdに「分ける動機: 品質と速さ」小節（3役割分離とManager/Worker/Verifierの対応付け、テスト4分割の高速化事例）を追加、multi-agent-break-even.mdにマルチエージェント4トポロジーの定義と努力配分ルール・90%短縮を追加、risks-and-safeguards.mdに本番運用の設計判断（チェックポイント再開・可観測性・レインボーデプロイ）小節を追加、loop-vs-graph-decision.mdにCalebのトークンコスト試算小節を追加
- **Refactor**: Gao Dalieの3層対比表の重複をterm-lineage-and-layers.mdに一本化しloop-vs-graph-decision.md側を縮約、「2023年当時ノード非力」歴史説明の重複をgraph-primitives.mdに一本化しroles-and-orchestration.md側を縮約。relationship-graph-for-operations.mdの見出しレベル不整合（H1→H2）を是正
- **Fix**: subagent-design-in-practice.mdのCitationsに露出していた内部フィールド表記「（source_tier: primary）」を自然文に置換。sources/article-le-claude-code-best-practices.mdのsource_tierをsecondary→primaryに変更しsources/article-he-agent-sdk-overview.mdと統一。knowledge-graph-as-memory.md・risks-and-safeguards.md・relationship-graph-for-operations.mdの日本語文中の半角括弧を全角に統一
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認
- **Note**: 本ランはfindingsの`where`が指すファイルのみを修正対象とし、それ以外のコンセプトファイルは書き換えていない

## 2026-08-16（graph-engineering コンセプト拡充・完了 knowledge run:081612459a）

- **Creation**: graph-engineering/ に残りコンセプト3本を追加し、run:08161057e2 で設計した新規6本が全て完了（plan.json 15/15 done）。handoffs-and-ownership.md（OpenAI公式のHandoffsとAgents as Tools（Managerパターン）を「最終回答の所有権を誰が持つか」という軸で対比し、Anthropicの研究システムとClaude Codeサブエージェントがいずれもマネージャー型にあたることを確認したうえで、Cコンパイラ実験の`current_tasks/`ロックを「作業対象の所有権」という別種の所有権として整理）、subagent-design-in-practice.md（Agent SDK公式が保証する機能範囲と、解説動画由来のフロントマター仕様・コンテキスト独立性・ネスト不可という3制約を確度を分けて整理し、使うべき/避けるべき場面と実装前チェックリストを提示）、verification-gates-and-evidence.md（Claude Code公式ベストプラクティスの強制力4段階（プロンプト内／`/goal`／Stopフック／セカンドオピニオン）と8回連続ブロックでの上書き、成功の自己申告ではなく証拠を提示させる原則、「task verifierがほぼ完璧である必要がある」という教訓を、検証をエッジの通行条件として読み替えて整理）
- **Update**: sources/ の台帳9本に「活用先」を追記（video-ge-subagent-overview-basics.md は初回記入）。新規3本が張った出典リンク12件すべてに対応する活用先を確認し、逆方向（活用先に挙げるが本文に出典リンクなし）も0件
- **Update**: graph-engineering/index.md に新規3本を追加し、読む順番を「なぜ分けるか→どう分けるか→何で作るか→どう止めるか→壊れたらどう直すか」という設計順の導線として書き直し。ルート index.md の graph-engineering の説明を15本構成に合わせて更新
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認。あわせて plan.json 15件すべての実ファイル存在・sources集合の重複なし・sources 2件未満なしを機械確認
- **Note**: 既存コンセプト12本は書き換えていない（本ランの変更は新規3本の追加と、台帳側の活用先追記・index更新のみ）

## 2026-08-16（graph-engineering コンセプト拡充 knowledge run:08161057e2）

- **Creation**: graph-engineering/ に公式ドキュメント・論文を一次根拠とするコンセプト3本を追加。workflow-patterns-catalog.md（Anthropic公式「Building Effective AI Agents」のWorkflow/Agent定義と5つのワークフローパターン、Claude Codeダイナミックワークフローの6つの編成型、GPTSwarmによるトポロジー自動最適化）、multi-agent-break-even.md（Anthropicの90.2%改善と15倍トークン、MASTの「minimal」、45%ルール、OpenAIの専門家追加4条件を突き合わせた損益分岐点の整理）、failure-taxonomy-and-debugging.md（MASTの3カテゴリ14失敗モードとkappa=0.88、AgentErrorTaxonomyの5領域とカスケード失敗、AgentDebugの定量結果、Anthropicの実地失敗例との対応づけ）
- **Update**: 既存コンセプト2本を新しい一次資料で補強（既存記述は書き換えず出典追加のみ）。roles-and-orchestration.md の「Anthropicの5つの連携パターン」（従来はauto字幕動画のみが根拠）に公式記事の出典を追加、risks-and-safeguards.md の「チャット比15倍のトークン」（同）に公式記事の原文引用と出典を追加
- **Update**: sources/ の台帳11本に「活用先」を追記し、コンセプト⇄台帳の双方向リンクを整合（新規3本が張った出典リンク14件すべてに対応する活用先を確認、不一致0件）
- **Update**: graph-engineering/index.md に新規3本を追加し、情報源の記述を「動画11本」から公式ドキュメント・論文を含む形へ修正。読む順番に3本の差し込み位置を追記
- **Check**: `tools/validate_okf.py knowledge` を実行し errors: 0 / warnings: 0 を確認
- **Note**: 設計した新規コンセプト6本のうち3本が完了。残り3本（handoffs-and-ownership / subagent-design-in-practice / verification-gates-and-evidence）は pipeline/staging/knowledge/plan.json に status: todo として記録済み

## 2026-08-16（geソース台帳・記事1本 web_ledger run:0816101550）

- **Creation**: sources/ に記事1本を article-ge-agent-error-taxonomy-debug.md として登録（グラフエンジニアリングテーマ、arXiv論文、web_ledger工程 run:0816101550）。arXiv「Where LLM Agents Fail and How They can Learn From Failures」。単一の根本原因エラーが後続の判断へ波及する「カスケード失敗」という課題認識から、LLMエージェントの失敗モードをMemory・Reflection・Planning・Action・System-level operationsの5領域に体系化したAgentErrorTaxonomy、ALFWorld・GAIA・WebShopの3環境での実エージェント軌跡をアノテーションし著者らが「初の大規模失敗軌跡データセット」と位置づけるAgentErrorBench、根本原因を特定し矯正フィードバックを提供するデバッグフレームワークAgentDebugという3つの貢献を提示し、AgentErrorBenchでの検証実験で全正解精度24%・ステップレベル精度17%の向上、3ベンチマーク全体でタスク成功率最大26%の相対改善を達成したと報告している内容を解説
- **Update**: sources/index.md の「記事（グラフエンジニアリング）」節に上記1件を追加

## 2026-08-16（geソース台帳・記事2本 web_ledger run:0816085739）

- **Creation**: sources/ に記事2本を article-ge-*.md として登録（グラフエンジニアリングテーマ、arXiv論文2本、web_ledger工程 run:0816085739）。article-ge-mast-multi-agent-failures.md（arXiv「Why Do Multi-Agent LLM Systems Fail?」Cemri, Pan, Yang et al.、一次情報。マルチエージェントLLMシステムが一般的ベンチマークで「minimal」な性能向上にとどまるという研究課題の位置づけ、7フレームワーク・1600件超の注釈付きトレースからなり著者ら自身が「初めてのマルチエージェントシステム失敗ダイナミクスデータセット」と位置づけるMAST-Data、150件のトレースを専門家アノテーターがkappa=0.88の高い一致度で分析して構築したMAST分類体系、システム設計上の問題・エージェント間の非整合・タスク検証の3カテゴリに整理された14の失敗モード、GPT-4・Claude 3・Qwen2.5・CodeLlamaを対象としたLLM-as-a-Judgeによる自動判定パイプラインへの拡張を解説）、article-ge-gptswarm-optimizable-graphs.md（arXiv/ICML2024「GPTSwarm: Language Agents as Optimizable Graphs」、一次情報。単一エージェントを有向非環グラフG=(N,E,F,o)、複数エージェント(スワーム)を複合グラフG_ℰ=(N',E_ℰ,F',o')として統一的に表現する定式化、REINFORCEアルゴリズムによる確率的エッジサンプリングとOPRO等によるノードプロンプト最適化の2段階最適化、Mini Crosswordsで先行技術のTree of Thought(0.668)を上回る0.800、HumanEvalで0.76から0.88への改善、GAIAベンチマークでGPT-4-Turbo単体(9.70%)・AutoGPT(4.85%)を大きく上回る平均18.45%(Level2は260.2%の相対改善)という評価結果を解説）
- **Update**: sources/index.md の「記事（グラフエンジニアリング）」節に上記2件を追加

## 2026-08-16（geソース台帳・記事2本 web_ledger run:08160745c3）

- **Creation**: sources/ に記事2本を article-ge-*.md として登録（グラフエンジニアリングテーマ、Anthropic公式2本、web_ledger工程 run:08160745c3）。article-ge-anthropic-multi-agent-research-system.md（Anthropic公式「How we built our multi-agent research system」、二次情報。リードエージェント(Opus 4)が戦略を立てサブエージェント(Sonnet 4)を並列生成して探索させるオーケストレーター・ワーカーパターン、「Claude Opus 4 as the lead agent with Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2%」という内部評価の性能改善値とマルチエージェントが通常チャット比約15倍のトークンを消費するという引用、50個のサブエージェント生成やSEO最適化コンテンツ優先選択といった開発初期の失敗事例と対処、ツール説明改善によるタスク完了時間40%短縮・並列ツール実行による調査時間最大90%短縮というプロンプトエンジニアリング上の教訓、チェックポイント機構・プライバシー保全トレース・レインボーデプロイメントという本番運用の設計判断を解説）、article-ge-anthropic-building-c-compiler.md（Anthropic公式「Building a C compiler with a team of parallel Claudes」、二次情報。16個のClaudeインスタンス(Opus 4.6 using agent teams)が約2週間・約2000セッションでRust製Cコンパイラを開発し入力20億トークン・出力1億4000万トークン・総コスト2万ドル弱を要したという実測値、「current_tasks/」ディレクトリのロックファイルとGitの同期機構自体を競合解決に利用するマルチエージェント運用設計、「Claude will work autonomously to solve whatever problem I give it, so it's important that the task verifier is nearly perfect」というタスク検証機構の重要性を説く教訓、完成したコンパイラがLinux 6.9をx86・ARM・RISC-Vでビルド可能でGCC torture test suiteを含む主要テストスイートで99%の成功率を達成したという成果を解説）
- **Update**: sources/index.md の「記事（グラフエンジニアリング）」節に上記2件を追加

## 2026-08-16（geソース台帳・記事2本 web_ledger run:08160657ff）

- **Creation**: sources/ に記事2本を article-ge-*.md として登録（グラフエンジニアリングテーマ、公式ドキュメント2本、web_ledger工程 run:08160657ff）。article-ge-anthropic-building-effective-agents.md（Anthropic公式「Building Effective AI Agents」、二次情報。Workflowを「LLMsとツールが予め定義されたコードパスを通じてオーケストレーションされるシステム」、Agentを「LLMsが動的に自身のプロセスとツール使用を指示し、タスク達成方法をコントロールし続けるシステム」と定義する引用、検索・ツール・メモリで拡張されたLLM(augmented LLM)を基本構築ブロックとする位置づけ、5つのワークフローパターン(Prompt chaining/Routing/Parallelization/Orchestrator-workers/Evaluator-optimizer)の具体例、「find the simplest solution possible」というシンプルさの原則とツール設計(Agent-Computer Interface)への注力を解説）、article-ge-openai-orchestration-handoffs.md（OpenAI公式「Orchestration and handoffs」、二次情報。会話の所有権そのものを引き渡すHandoffsパターンと、マネージャーが制御・所有権を保持したまま専門エージェントをツール化するAgents as Tools(Managerパターン)の対比、「専門家を追加するのはcapability isolation・policy isolation・prompt clarity・trace legibilityのいずれかを実質的に改善する場合に限る」という引用、「まずは単一エージェントから始める(Start with one agent whenever you can)」という結論を解説）
- **Update**: sources/index.md に「記事（グラフエンジニアリング）」節を新設し上記2件を追加

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

- **Note**: context-engineering の11コンセプトを採点 8/6/7/6/6（①事実正確性8・②網羅性6・③構成7・④リンク6・⑤文章品質6）のまま manual_override で受理し、テーマを he へ進めた。網羅性と独立裏取りに既知の弱みが残る**参考ナレッジ**の位置づけ（02の発表資料本体は `decks/02-context-engineering/` 側で別途品質担保済み）

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
- **Creation**: decks/02-context-engineering/ を新設。本編30枚＋付録21枚の全51枚（初版）
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
- **Creation**: decks/_archive/graph-engineering/01-graph-engineering/ を新設（29枚、テーマ accenture-purple、全スライドにHTML用スピーカーノートつき）。構成は「序（用語誕生の事件）→ 地図 → 基本語彙 → ループかグラフか → 配線と検証 → 歯止め → 3フレーム+1原則」
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

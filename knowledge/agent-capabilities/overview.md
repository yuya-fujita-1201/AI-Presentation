---
type: Concept
title: AIに能力を足す4つの手段——プロンプト・Skill・MCP・CLIの地図
description: 「AIに能力を足す」とは何をすることかを定義し、プロンプト・Skill・MCP・CLIという4つの手段を1枚の表に並べて、それぞれが何を足し・どこに置かれ・いつ読まれるのかを整理する。バンドル全体の地図と読む順番も示す
tags: [agent-capabilities, agent-skills, mcp, cli, prompt, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T03:10:00+09:00"
---

# AIに能力を足す4つの手段

チャットでAIに質問すると、たいていのことは答えが返ってくる。ではなぜ「AIに能力を足す」という話が必要になるのか。このファイルはその問いから始めて、プロンプト・Skill・MCP・CLIという4つの手段を1枚の地図に並べ、このバンドル（9本のコンセプト）の読む順番を示す。

## 前提：この話は「チャットするAI」ではなく「作業するAI」の話である

まず、話の土台が変わっていることを押さえたい。Anthropicの公式ドキュメントは、ここで扱う「エージェント」を次のように定義している。

> 引用: 「An agent is an application that completes a task by planning its own steps and calling tools that read files, run commands, or edit code.」（[Agent SDK overview](../sources/article-he-agent-sdk-overview.md)）

つまり、**自分で手順を計画し、ファイルを読み、コマンドを実行し、コードを編集する**アプリケーションである。チャット欄で文章を返してくるAIではなく、こちらの手元のファイルを実際に触るAIを想定している。この前提の違いが、以降のすべての話の出発点になる。ファイルを触れるということは、逆に言えば**「ファイルに書いて置いておけば、AIがそれを読んで従う」**という道が開けるということでもある。4つの手段のうち3つ（Skill・プロジェクトルール・CLI）は、この性質を利用している。

## 一言定義

**AIに能力を足すとは、モデルそのものを賢くすることではなく、モデルの外側に「手順書」と「手足」を用意することである。**

なぜ外側なのか。[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)は、モデルの能力が上がっても「real work requires procedural knowledge and organizational context」——実務には手続き的な知識と組織固有の文脈が要る——と述べている。汎用モデルは「PDFとは何か」を知っているが、「わが社の見積書テンプレートの3ページ目に何を書くか」は知らない。後者はモデルの学習ではなく、外側から渡すしかない。

もうひとつ、外側でなければならない現実的な理由がある。手を動かす能力（コマンドを実行する、APIを叩く）はモデルの中には存在しない。同ブログは「certain operations are better suited for traditional code execution」としている。コード実行が持つ2つの価値（コスト・決定論的信頼性）の詳細は[what-are-agent-skills.md](./what-are-agent-skills.md)を参照。決定論的な信頼性が要る処理は、コードに任せた方がよい。

## 4つの手段

「手順書」と「手足」を渡す方法は、大きく4つに整理できる。

| 手段 | 何を足すか | 置き場所 | いつ読まれるか |
|---|---|---|---|
| **プロンプト** | その場かぎりの指示 | 会話（入力欄） | 毎回、その会話の中だけ |
| **プロジェクトルール**（CLAUDE.md等） | 常に効かせたい前提・規約 | リポジトリ内のファイル | セッション開始時に自動で全文 |
| **Skill** | 手順書＋補助ファイル＋スクリプト一式 | ファイルシステム上のフォルダ | 関連しそうな時だけ、必要な深さまで |
| **MCP** | 外部サービスへの接続口（ツール・データ） | 別プロセスのサーバー | 接続中はツール一覧が載り続けるとされる（実測記事・動画） |
| **CLI** | 既存のコマンドライン道具 | OSにインストール済み | AIがコマンドを打った時だけ |

CLIだけは他の3つと違い、新しく用意するものが何もない（既にOSに入っている道具をそのまま呼ばせる）。この性質と設計論点は専用ファイルを設けず[どれを選ぶか](./choosing-skill-mcp-or-cli.md)の冒頭にまとめている。

表が5行あるのは、プロンプトを「その場の指示」と「常設化したルール」に分けて示したためである。この2つは実体としては同じ「言葉で指示する」手段であり、本バンドルでは4手段のうちの「プロンプト」として1本のコンセプト（[prompts-and-project-rules.md](./prompts-and-project-rules.md)）でまとめて扱う。

この4分類は本バンドル独自の切り口ではなく、実務側の整理ともおおむね一致している。[サブエージェント解説動画](../sources/video-ge-subagent-overview-basics.md)は、Claude Codeの機能を「実行主体（メインセッション・サブエージェント）」「能力（スキルとMCP）」「ルール・環境（CLAUDE.mdやフック）」の3つに整理すると分かりやすい、という見方を私見として述べている（聞き取り）。ここで**スキルとMCPが同じ「能力」の箱に並び、CLAUDE.mdが別の箱に置かれている**点が、上の表と対応する。

公式側の記述も同じ並びになっている。[Agent SDK overview](../sources/article-he-agent-sdk-overview.md)は、SDKが提供する機能として、ファイル読み書き・コマンド実行・Web検索を行うBuilt-in tools、MCP経由の外部ツール接続、`.claude/`と`~/.claude/`から自動読み込みされるSkills / commands / memory、そしてこれらをパッケージ化するPluginsを列挙している。**4つは競合する選択肢ではなく、同時に使える別々の口である**ことが、この列挙からも読み取れる。

## なぜ区別する必要があるのか

4つとも「AIに何かをさせる」点では同じに見える。それでも区別が要る理由は3つある。

### 理由1: 会話をまたいで残るかどうか

[Anthropicの公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は、Skillsとプロンプトの違いを再利用性の一点で説明している。プロンプトは会話単位の一時的な指示であり、次の会話には残らない。同じ説明を毎回書いているなら、それはプロンプトで済ませるべきではない仕事だ、という判断基準になる。公式の引用と詳しい根拠は[prompts-and-project-rules.md](./prompts-and-project-rules.md)を参照。

### 理由2: 結果が毎回ブレるかどうか

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)の講師は、ChatGPTやClaudeに同じような依頼をしても、依頼するたびにアウトプットの傾向（デザインの色味や雰囲気など）が変わってしまう問題があったと指摘し、Skillとは「必ずAIがマニュアルを見てその指示通りに処理を行っていくことができるようになった」仕組みだとしている（[01:00]、聞き取り）。同動画は、従来のGPTsやGemsがマークダウン形式の指示書しか保持できなかったのに対し、Skillは指示書に加えて実際のプログラム（スクリプト）をセットで保持できる点が違いだと説明している（聞き取り）。

言い換えると、**言葉で頼む限り出力は毎回生成されるので揺れるが、スクリプトを走らせれば同じ結果が出る**。品質の一貫性が要る仕事なら、手段の選択がそのまま品質に効く。

### 理由3: コンテキストを食う量が違う

コンテキストウィンドウ（1回のやり取りで扱える情報量）には上限があり、能力を全部最初から読み込んでしまうとこれを圧迫する。ここが4手段の実務上の最大の分かれ目になる。プロジェクトルールは常に全文が載り、Skillは名前と説明だけが載る——これは公式ドキュメントが明記している。MCPについては、接続中はツール定義が載り続けるという指摘が実測記事とauto字幕動画にあり（公式の`*/list`設計から自然に導かれる推論でもある）、能力を増やしたときの「重さ」の差はここに表れる。仕組みは[progressive-disclosure.md](./progressive-disclosure.md)で、実際の選び方は[choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md)で扱う。

## よくある誤解

- **SkillはMCPの進化形ではない**: MCPは「外部サービスに繋ぐ通信規格」、Skillは「ファイルに置いた手順書」であり、解いている問題が違う（詳しくは[what-is-mcp.md](./what-is-mcp.md)）。両方を同時に使う構成が普通である
- **4つは排他ではない**: 上に見たとおりAgent SDKは4つとも同時に提供する。「MCPを入れたからSkillは要らない」といった関係にはない。[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)もSkillの発表時点でMCPサーバーとの補完的な活用の検討に触れており、公式側もSkillとMCPを対立する選択肢としてではなく組み合わせるものとして位置づけている
- **Skillは特定製品の機能名ではなくなりつつある**: 入門動画は、この仕組みを最初に搭載したのはAnthropicのClaudeであり、その後ChatGPTのCodex、Antigravity、Gemini、Manusなど各社の生成AIツールにも同様の概念が広がっていると述べている（聞き取り）。実際にGoogleが同じ形式でスキル集を公開している件は[distribution-and-governance.md](./distribution-and-governance.md)で扱う
- **「能力を足す」＝モデルを再学習させることではない**: ファインチューニングやRAGとの直接比較は本バンドルの主根拠には含まれていない（[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)にも比較・ベンチマークの記載はない）。ここで扱うのはあくまで、モデルを変えずに外側から渡す手段である

## このバンドルの地図

| # | ファイル | 扱う内容 | 主根拠 |
|---|---|---|---|
| 1 | [what-are-agent-skills.md](./what-are-agent-skills.md) | Skillの定義・構成要素・素のプロンプトとの違い | 公式＋動画 |
| 2 | [progressive-disclosure.md](./progressive-disclosure.md) | 段階的開示の3階層とトークンコストの実際 | 公式＋動画 |
| 3 | [writing-good-skills.md](./writing-good-skills.md) | 起動されるSkillの書き方・500行の壁・失敗パターン | 公式＋実務記事 |
| 4 | [what-is-mcp.md](./what-is-mcp.md) | MCPの構造・3大プリミティブ・サーバーの実像 | 公式（primary） |
| 5 | [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) | 同じ用事にどれを選ぶか。コストと制御性の判断 | 実測記事＋公式 |
| 6 | [prompts-and-project-rules.md](./prompts-and-project-rules.md) | プロンプトとCLAUDE.mdの設計指針 | 実務記事＋公式 |
| 7 | [distribution-and-governance.md](./distribution-and-governance.md) | 配布・バージョン管理・ライセンス・悪意あるSkill | 動画＋公式 |
| 8 | [webmcp-and-frontier.md](./webmcp-and-frontier.md) | ブラウザ側MCPという提案と未確定の論点 | 動画＋公式 |

## 読む順番の提案

- **まず全体像だけ掴みたい**: 本ファイル → [prompts-and-project-rules.md](./prompts-and-project-rules.md) → [what-are-agent-skills.md](./what-are-agent-skills.md) → [what-is-mcp.md](./what-is-mcp.md) の4本で、最も手前の手段（プロンプト）を含む4手段のうち3つの実体が分かる
- **明日から自分で何か作りたい**: 上の4本の後、[writing-good-skills.md](./writing-good-skills.md)へ。実際に手を動かす順もこの並びで、プロンプトで試す→効いた指示をルールに常設化する→手順が長くなったらSkillに切り出す、が最も無駄が少ない
- **導入判断・技術選定をする立場**: [progressive-disclosure.md](./progressive-disclosure.md) → [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) → [distribution-and-governance.md](./distribution-and-governance.md)。コスト構造・使い分け・ガバナンスの3点が判断材料になる
- **[webmcp-and-frontier.md](./webmcp-and-frontier.md) は最後でよい**: 提案段階の話であり、確定していない論点を多く含む

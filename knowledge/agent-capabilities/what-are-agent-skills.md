---
type: Concept
title: Skillとは何か——ファイルシステムに置いた「手順書＋スクリプト」一式
description: Agent Skillを「フォルダに置いた再利用可能な手順書一式」として定義し、SKILL.mdの構造・必須フィールドの制約・素のプロンプトやGPTs/Gemsとの違い・利用できる環境ごとの制約を整理する
tags: [agent-capabilities, agent-skills, skill-md, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T03:25:00+09:00"
---

# Skillとは何か

4つの手段（[overview.md](./overview.md)）のうち、いま最も動きが速いのがSkillである。このファイルではSkillの定義・構成要素・「素のプロンプトとどう違うのか」・どこで使えるのかを押さえる。書き方の作法は[writing-good-skills.md](./writing-good-skills.md)、読み込みの仕組みは[progressive-disclosure.md](./progressive-disclosure.md)に分けている。

## 一言定義

**Skillとは、AIが必要になった時に自分で読みに来る、フォルダに置いた手順書一式である。**

公式の定義はこうなっている。

> 引用: 「Skills are reusable, filesystem-based resources that give Claude domain-specific expertise: workflows, context, and best practices that turn a general-purpose agent into a specialist.」（[Agent Skills（Anthropic公式ドキュメント）](../sources/article-tools-agent-skills-overview.md)）

押さえるべき語は3つある。**reusable（再利用可能）**——会話をまたいで残る。**filesystem-based（ファイルシステムベース）**——特別なサーバーもAPIも要らず、決められた場所にフォルダを置くだけである。**turn a general-purpose agent into a specialist（汎用エージェントを専門家にする）**——足すのは知能ではなく専門性である。

同ドキュメントは、この構造を「organized like an onboarding guide you'd create for a new team member」（新しいチームメンバー向けに作るオンボーディング資料のような構成）と説明している。[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)も「Building a skill for an agent is like putting together an onboarding guide for a new hire」と、同じ比喩で記事を締めくくっている。新人に渡す業務マニュアルを想像すればよい、というのが公式側の一貫した説明である。

## なぜ生まれたのか

同エンジニアリングブログは、開発動機を「Claude is powerful, but real work requires procedural knowledge and organizational context」と述べている。モデル自体の能力が上がってローカルでコードを実行しファイルシステムと相互作用する汎用エージェントが作れるようになった一方で、「we need more composable, scalable, and portable ways to equip them with domain-specific expertise」——構成可能・スケーラブル・可搬な形で専門知識を与える手段が足りない——という課題が生じた、というのがSkills登場の背景である。

同ブログはPDF編集を例に、埋めるべきギャップを具体的に示している。Claudeは既に「PDFの理解」には長けているが、「manipulate them directly (e.g. to fill out a form)」——直接操作してフォームを埋めるといった能力——が不足している。Skillsはこの**「分かってはいるが、できない」の隙間**を埋めるものだと位置づけられている。

## 構成要素は3つ

同ブログによれば、Skillは (1) YAMLフロントマターと詳細説明を含む **SKILL.md**、(2) **関連ファイル群**（reference.md、forms.md等）、(3) **実行可能コード**（スクリプト）の3種で構成される。

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)も同じ構成を「SKILL.mdというメインの指示書と、必要な情報をまとめたスクリプト（プログラム）ファイル群」と説明しており（[12:00]、聞き取り）、公式側の記述と一致する。

### SKILL.mdのフロントマターは2フィールドしか必須ではない

[公式ドキュメント](../sources/article-tools-agent-skills-overview.md)によれば、YAMLフロントマターで必須なのは`name`と`description`の2つだけである。ただしそれぞれに制約がある。

| フィールド | 制約 |
|---|---|
| `name` | 最大64文字。小文字・数字・ハイフンのみ。`anthropic`・`claude`といった予約語を含んではならない |
| `description` | 空は不可。最大1024文字。**「何をするか」と「いつ使うか」の両方**を書かなければならない |

必須が2つだけ、というのは実務上かなり重要な性質である。[21個運用の実務記事](../sources/article-tools-claude-code-skill-design.md)も「最初はnameとdescriptionだけのシンプルなSKILL.mdで十分。使いながら育てていくのが一番のコツ」と述べており、始めるハードルの低さを実務側からも裏付けている。詳細は[writing-good-skills.md](./writing-good-skills.md)を参照。

### スクリプトを同梱できることが効く

構成要素のうち、素のプロンプトと決定的に違うのが(3)の実行可能コードである。前掲のエンジニアリングブログは、コード実行の価値を2点挙げている。ひとつはコストで、「sorting a list via token generation is far more expensive than simply running a sorting algorithm」——リストのソートをトークン生成でやるのはソートアルゴリズムを走らせるより遥かに高くつく。もうひとつは信頼性で、「many applications require the deterministic reliability that only code can provide」——コードだけが与えられる決定論的な信頼性を必要とする用途がある、としている。

さらに、Claudeはスクリプトをコンテキストに読み込まずに実行できるため「this workflow is consistent and repeatable」であるとも述べている。**同じスクリプトを走らせれば同じ結果が出る**という当たり前の性質が、生成のたびに揺れるLLMの出力と組み合わさることで効いてくる。

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)の講師は、この効き方を自作した「図クリエイトチャット」というSkillで実演している。YouTube動画用の図解を、依頼のたびに色味や雰囲気が変わることなく、一貫したフォーマットで作成できるようにしたものだという（聞き取り）。指示書だけを渡していた頃はアウトプットが依頼ごとにブレていたのに対し、スクリプトをセットで持たせることでこの一貫性が得られた、という具体例になっている。

## 素のプロンプトとの違い、GPTs/Gemsとの違い

Skillの位置づけは、比較対象を2つ置くと分かりやすい。

**素のプロンプトとの違いは「残るかどうか」である。**[公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は、プロンプトが会話単位の一時的な指示であるのに対しSkillsは必要に応じて読み込まれるので同じ指示を会話ごとに繰り返さずに済むと説明している（引用と詳しい根拠は[prompts-and-project-rules.md](./prompts-and-project-rules.md)を参照）。同ドキュメントはSkillsの利点として、Claudeの専門化・重複の削減・能力の合成の3点を挙げている。

**GPTsやGemsとの違いは「スクリプトを持てるかどうか」である。** [Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)の講師は、従来のGPTsやGemsがマークダウン形式の指示書（カスタム指示）しか保持できなかったのに対し、Skillは指示書に加えてパワーポイント作成やExcel作成、図作成のための実際のプログラムをセットで保持できる点が異なると説明している（[01:00]〜[02:00]、聞き取り）。同氏はこれによって「同じような精度・品質を保ったアウトプット」を作れるようになるとしている（聞き取り）。前節で見た公式ブログの「deterministic reliability」の説明と、方向としては同じことを指している。

## 起動は自動である

[公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は「once a Skill is available in your environment, Claude uses it automatically when relevant to your request」と述べている。ユーザーが「このSkillを使え」と指定する必要はなく、要求内容に関連するとAIが判断すれば自動で読まれる。

これは便利であると同時に、**「起動されるかどうかはdescriptionの書き方で決まる」**という設計上の重心を生む。同ドキュメントは、Skillが起動されるまでコンテキストを占めるのは名前と説明だけだとしており、AIは実質そこだけを手がかりに選ぶことになる。書き方を誤ると似たSkill同士で誤起動が起きる点は[writing-good-skills.md](./writing-good-skills.md)に集約する。

## どこで使えるか——環境ごとに制約が違う

[公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は、Skillを事前構築済みのPre-builtとユーザーが作るCustomに分けている。Pre-builtはPowerPoint（pptx）・Excel（xlsx）・Word（docx）・PDF（pdf）の4種類が用意されており、claude.ai・Claude API・Claude Platform on AWS・Microsoft Foundry（Hosted on Anthropicデプロイのみ）で利用できるとしている。

Custom Skillsを置く場所と制約は環境によって異なる。

| 環境 | 置き方 | 制約 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/`（個人）または`.claude/skills/`（プロジェクト）にフォルダを置くだけ | APIアップロード不要。**フルネットワークアクセスあり** |
| **Claude API** | `container`パラメータに`skill_id`を指定。code execution toolが必須 | サンドボックスは「no network access and no runtime package installation」 |
| **claude.ai** | Settings > Features からzipでアップロード（Pro/Max/Team/Enterprise、code execution有効時） | 個人単位。組織全体共有やadmin管理は不可 |

同ドキュメントは加えて「Custom Skills do not sync across surfaces」と明記している。**claude.aiにアップロードしたSkillがClaude Codeでも使えるようになる、といったことは起きない**。組織で配る話は[distribution-and-governance.md](./distribution-and-governance.md)で扱う。

新入社員がまず触るなら、フォルダを置くだけで動きネットワークも使えるClaude Codeが最も試しやすい、というのが上表から読み取れる実務上の結論である。

## 次に読む

- 「なぜ大量に置いても重くならないのか」——[progressive-disclosure.md](./progressive-disclosure.md)
- 「実際に起動されるSkillをどう書くか」——[writing-good-skills.md](./writing-good-skills.md)
- 「MCPと何が違い、どちらを選ぶのか」——[what-is-mcp.md](./what-is-mcp.md) と [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md)

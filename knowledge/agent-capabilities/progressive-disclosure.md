---
type: Concept
title: 段階的開示（progressive disclosure）——積んでも重くならない仕組み
description: Skillの中核設計である段階的開示を、常時100トークンのメタデータ・トリガー時のSKILL.md本文・必要時のみの参照ファイルという3階層で説明し、コンテキストが有限であるという制約からなぜこの設計が要るのかを示す
tags: [agent-capabilities, agent-skills, progressive-disclosure, context-engineering, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T03:40:00+09:00"
---

# 段階的開示（progressive disclosure）

Skillを100個置いても動作が重くならない。この一点がSkillという仕組みの核心であり、それを支えているのが段階的開示（progressive disclosure）という設計である。[what-are-agent-skills.md](./what-are-agent-skills.md)でSkillの実体を見たので、ここではその読まれ方を扱う。

## 一言定義

**段階的開示とは、常に見せるのは目次だけにして、中身は必要になった時に開く読ませ方である。**

[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)は、この設計を次の比喩で説明している。

> 引用: 「Like a well-organized manual that starts with a table of contents, then specific chapters, and finally a detailed appendix, skills let Claude load information only as needed.」

よく整理されたマニュアルが、目次から始まり、章があり、最後に詳細な付録がある——その構造をそのままAIの読み込みに適用したものだ、という説明である。

## 3つの階層と、それぞれのコスト

[Anthropic公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は、この構造を3階層として具体的なトークン数とともに示している。

| 階層 | 中身 | いつロードされるか | コンテキストのコスト |
|---|---|---|---|
| **Level 1** | フロントマターのメタデータ（`name` / `description`） | 起動時に常に | **約100トークン** |
| **Level 2** | SKILL.md の本文 | 要求に関連すると判断された時 | 目安 **5,000トークン未満** |
| **Level 3** | 参照ファイル・スクリプト | 実際に必要になった時のみ | 未アクセスなら **ゼロ** |

同ドキュメントは Level 1 について「until a Skill is triggered, only its name and description occupy context」と述べている。**起動されるまで、コンテキストを占めるのは名前と説明だけである。**

Level 3 のスクリプトにはさらに特別な性質がある。スクリプトはbashで実行され、その**出力だけ**がコンテキストに入る。同ドキュメントは「the script code itself never enters context」——スクリプトのコード自体はコンテキストに入らない——と明記している。500行のPythonスクリプトを同梱しても、コンテキスト上のコストはその実行結果の行数分でしかない。

この3階層の帰結として、公式ドキュメントは「no practical limit on bundled content」（同梱するコンテンツに実用上の上限はない）と述べ、エンジニアリングブログも「the amount of context that can be bundled into a skill is effectively unbounded」（Skillに束ねられるコンテキストの量は事実上無制限である）としている。**未使用ファイルのコンテキストコストがゼロだから、上限が実質なくなる**という論理である。

### 実際の読み込み手順

公式ドキュメントは`pdf-processing`スキルを例に、次の流れを示している。

1. 起動時、`name`と`description`がシステムプロンプトに入る
2. ユーザーの要求がそれに一致すると、`bash: cat pdf-processing/SKILL.md` が実行されて本文がロードされる
3. Claudeがフォーム入力は不要だと判断すれば、`FORMS.md`は読まれない

3番目が段階的開示の効き所である。**読まなかったファイルの分は、最初から存在しなかったのと同じコストで済む。**

## 動画側は「2段階」と説明している——数え方の違い

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)の講師は、同じ仕組みを2段階として説明している。SKILL.mdの冒頭のYAMLフロントマターのうちディスクリプションの部分だけをAIは毎回最初に読み込んでおり（[15:00]、聞き取り）、ユーザーから指示があるとまずこのディスクリプションを目次のように参照して自分がどのスキルを持っているかを把握し、該当すると判断した場合に初めてSKILL.mdの本文全体を読み込みに行く、という説明である（[16:00]、聞き取り）。

公式が3階層、動画が2段階と数え方は違うが、指しているものは同じである。動画側は Level 3（参照ファイル）を独立した段階として数えていないだけで、「メタデータだけ常時 → 必要時に本文」という骨格は一致している。数え方より、**「常に読まれる部分」と「条件付きで読まれる部分」が分かれている**という構造の方を覚えておけばよい。

## 実物で確かめる——google/skills の構成

設計思想が実際のスキル集にどう現れるかは、Googleが公開したスキル集の構成に見て取れる。[google/skillsの解説動画](../sources/video-tools-google-skills-marketplace.md)は、SKILL.mdが109個あり全部を足すと2万3千行を超えるとし、そのうち**59個がreferencesフォルダを持ち、長いスキルは補助情報をそちらに分離して必要な部分だけを読ませる構成になっている**と説明している（[01:00]〜[02:00]、聞き取り）。例としてBigQueryにはCLI・クライアントライブラリ・IAM・IaC等8個のreferencesがあるとしている（聞き取り）。

同動画は各スキルの厚みのばらつきも挙げており、Agent Platform Inferenceが726行、Gemini Interactions APIが591行ある一方、Mobile Adsのバナー広告は30行台で終わっているとしている（聞き取り）。**厚いスキルと薄いスキルが同じ棚に混在していても、薄い方の利用者が厚い方のコストを払わされない**——これが段階的開示の実務上の意味である。

なお同動画は、progressive disclosureの仕組みにより通常はスキルのdescription部分だけが読み込まれ、必要になった時に本文が展開されると説明しており（[04:00]）、この点は前掲の公式ドキュメントの記述と独立に一致する。

## なぜこの設計が要るのか——コンテキストは有限で、しかも共有財である

段階的開示は「あれば嬉しい最適化」ではなく、**制約から要請された設計**である。

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)の講師は、コンテキストウィンドウ（1回のやり取りで扱える情報量）には上限があり、スキルを全部最初から読み込んでしまうとこれを圧迫してしまうと説明している（[13:00]〜[14:00]、聞き取り）。

圧迫されると何が起きるのか。[CLAUDE.md運用の実務記事](../sources/article-he-claude-md-best-practices.md)は、これを「コンテキスト汚染」と呼び、LLMは一度に安定して扱える「ルールの数」に限界があり、指示が増えれば増えるほど守られない指示が出てくると指摘している。同記事はコンテキストウィンドウを人間のワーキングメモリになぞらえ、不要な情報でメモリを埋め尽くすと本当に重要なタスクに割けるリソースが減り推論能力の低下を招くと説明している。

つまり**能力を足したつもりが、足した分だけ全体の精度を下げる**という逆転が起こりうる。段階的開示は、この逆転を避けるための仕組みである。「なんか最近AIの精度が悪いな」と感じたら、まず何を常時読ませているかを疑ってみる価値がある、というのが同記事の勧めである。

## 同じ設計はSkill専用の話ではない

段階的開示はSkillの機能名ではなく、**設計のパターン**である。同じ考え方はプロジェクトルールの書き方にも適用できる。

前掲の[CLAUDE.md運用の実務記事](../sources/article-he-claude-md-best-practices.md)は、`CLAUDE.md`にすべてを書ききる必要はないとし、DBスキーマは`docs/schema.md`、APIドキュメントは`docs/api.md`、複雑なドメインルールは`docs/domain-rules.md`のように詳細情報を別ファイルに分け、`CLAUDE.md`にはその場所と概要だけを書いてタスクに応じて追加のファイルを開かせる設計を推奨している。

> 引用: 「詳細情報は別ファイルに分離し、CLAUDE.mdには場所だけ案内する『段階的開示』の設計が推奨されると筆者は述べている」

同記事は`CLAUDE.md`本体の目安を300行以下・指示150〜200個程度としている。Skillの Level 2 が5,000トークン未満という目安と、桁としては近い水準である。**常時読ませる部分は小さく保ち、深い情報は場所だけ案内する**——手段が違っても指針は同じになる。

## 限界と注意点

- **起動されなければ意味がない**: Level 1 に載るのは`name`と`description`だけである。裏を返せば、descriptionが曖昧だと本文は永久に読まれない。段階的開示の恩恵は、descriptionの質に全面的に依存する（`writing-good-skills.md`（未執筆））
- **「置いておけばタダ」ではない**: Level 1 の約100トークンは常時かかる。100個置けば約1万トークンが恒常的に占有される計算になる。無制限なのは Level 3 の分量であって、Skillの個数ではない
- **常時ロードされる手段には効かない**: MCPのように接続中ずっとツール定義が載る手段には、この仕組みはそのままでは働かない。手段ごとのコスト構造の違いは`choosing-skill-mcp-or-cli.md`（未執筆）で扱う

## 実務への含意

- **「全部入りの巨大な指示書」を作らない**。1つのファイルに全部書く設計は、段階的開示の利点を自分で潰している
- **常時読ませる文章と、必要時に読ませる文章を意識的に分ける**。この2つを区別することが、Skillでもプロジェクトルールでも設計の第一歩になる
- **確定的な処理はスクリプトに落とす**。コードはコンテキストに入らないうえ、結果が揺れない（[what-are-agent-skills.md](./what-are-agent-skills.md)）

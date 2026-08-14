---
type: Article
title: Configure permissions - Claude Code Docs
description: Claude Codeの細粒度権限システムを解説する公式文書。ツール種別ごとの承認要否、deny→ask→allowの評価順序、Ctrl+Eによる説明表示機能を紹介
site: Anthropic
published: unknown
retrieved: 2026-08-14
resource: https://code.claude.com/docs/en/permissions
origin: "web:claude.com"
source_tier: primary
tags: [harness-engineering, claude-code, permissions, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-14T00:00:00+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは、Claude Codeが権限をどう管理しているかを解説する文書として「Configure permissions」を公開している。同文書は、Claude Codeが細粒度の権限ルールをサポートしており、エージェントに何を許可し何を許可しないかを正確に指定できると説明している。権限設定はバージョン管理にチェックインして組織内の全開発者と共有でき、各開発者がそれぞれ自分用にカスタマイズすることもできるとしている。

# 要点

## 3段階のツール分類と承認要否

同文書は、Claude Codeがパワーと安全性のバランスを取るために階層型の権限システムを採用していると述べ、ツールタイプを3段階に分類している。ファイル読み取りやGrepなどの読み取り専用ツールは、作業ディレクトリおよび追加で指定したディレクトリの範囲内であれば承認不要である。一方、シェル実行を伴うBashコマンドは、組み込みの読み取り専用コマンド一覧を除き承認が必要であり、Edit/writeによるファイル修正も常に承認が必要と説明されている。

## 「Yes, don't ask again」の保存先と挙動の変遷

Bashコマンドの承認時に「Yes, don't ask again」を選ぶと、その承認はリポジトリとコマンドの組み合わせ単位で永続的に保存される。同文書によると、保存先はgit worktreeを解決した上でのメインチェックアウトのルートにある`.claude/settings.local.json`であり、そのリポジトリ内であればサブディレクトリやworktreeで開始した将来のセッションにも適用される。ファイル修正の承認はこの永続化の対象外で、ファイルには保存されずセッション終了までしか有効でないとしている。また、バージョンv2.1.211より前のClaude Codeは常に開始ディレクトリにルールを保存していたため、worktreeやサブディレクトリで得た承認がリポジトリの他の部分には適用されないという制約があったと補足されている。

## Ctrl+Eによる説明表示機能

Bash・PowerShellの権限プロンプト上でCtrl+Eを押すと、そのコマンドが何をするか、なぜClaudeが実行しようとしているか、何がうまくいかない可能性があるかについての説明が、Low risk・Med risk・High riskのいずれかのラベルとともに表示されると同文書は説明している。この説明を生成するためにコマンドとClaude自身の呼び出し理由の説明がモデルへ送信されるのはCtrl+Eを押したときのみであり、毎回のプロンプト表示時に送信されるわけではない。説明を表示してもコマンド自体は実行されず、もう一度Ctrl+Eを押せば非表示に戻せるとしている。この機能は`~/.claude.json`の`permissionExplainerEnabled`を`false`に設定することで無効化できる。

## Allow/Ask/Denyルールと評価順序

`/permissions`コマンドから、Claude Codeの全ツール権限ルールと、各ルールがどの`settings.json`由来かを一覧できる。ルールにはAllow(承認なしでツールを使用可能にする)・Ask(使用のたびに確認を求める)・Deny(ツールの使用を禁止する)の3種類があり、これらはdeny→ask→allowの順に評価される。

> 引用: 「Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order.」

つまり最初に一致したルールが結果を決定し、ルールの具体性(より狭い範囲を指定しているかどうか)は評価順序を変えないと説明されている。具体例として、`Bash(aws *)`のような広範なdenyルールは、`Bash(aws s3 ls)`のようなより狭いallowルールにも一致する呼び出しすべてをブロックするため、denyルールはallowlist的な例外を持てないとしている。同じ優先順位関係はaskとallowの間にも成り立ち、一致するaskルールがある場合、より具体的なallowルールが同じ呼び出しに一致していても確認プロンプトが表示される。

## ツール名指定のdenyとスコープ指定のdenyの違い

denyルールはツール名だけを指定するかパターンでスコープするかによって挙動が異なると同文書は述べている。`Bash`のようにツール名のみを指定したdenyルールは、対象ツールをClaudeのコンテキストから完全に除去するため、Claudeはそのツールの存在自体を認識しなくなる。このベアネームでの除去は`EndConversation`を除く全ツールに適用され、denyルールは他のツールが残っている限り`EndConversation`を除去できず、askルールもそれに対して確認を求めることはないとしている。一方、`Bash(rm *)`のようにスコープを指定したルールはツール自体は利用可能なままにしつつ、Claudeが一致する呼び出しを試みたときにそれをブロックする。

## 権限の強制主体

同文書は、権限ルールはモデルではなくClaude Code自体によって強制されると明記している。プロンプトや`CLAUDE.md`内の指示はClaudeが何を試みるかを左右するが、それによってClaude Codeが許可する内容が変わることはない。アクセスを付与・取り消すには、`/permissions`、本文書で説明されているルール、権限モード、またはPreToolUseフックのいずれかを使う必要があるとされている。

# 活用先

- [../harness-engineering/permissions-design.md](../harness-engineering/permissions-design.md) — ツール3分類と承認要否、Allow/Ask/Denyの評価順序（deny→ask→allow）と具体性が順序を変えないこと、denyがallowlist的例外を持てないこと、ツール名指定denyとスコープ指定denyの挙動差、「Yes, don't ask again」の保存先と永続化範囲（ファイル修正は対象外）、Ctrl+Eによる説明表示、権限の強制主体がモデルではなくClaude Code自体であることの根拠

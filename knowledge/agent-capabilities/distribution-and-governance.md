---
type: Concept
title: 配布とガバナンス——作った能力を組織で回す
description: Skillを配る形式（フォルダ・zip・.skill・プラグインmarketplace）とバージョン管理・ライセンス・上流の所在を整理し、悪意あるSkillのリスクと「増やしすぎない」運用まで、組織で回す段階の論点をまとめる
tags: [agent-capabilities, agent-skills, distribution, governance, security, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T11:20:00+09:00"
---

# 配布とガバナンス

Skillが1つ書けると、次に来るのは「これ、チームにも配りたい」である。ここから先は個人の生産性の話ではなく、**組織で回す**話になる。配り方・更新の追い方・誰が「正」を持つか・悪意あるものをどう防ぐか——本ファイルはこの4点と、意外に効く「増やしすぎない」という運用を扱う。

## 一言定義

**配布とガバナンスとは、1人で書いたSkillを組織で安全に共有し続けるための、配り方・更新・信頼の管理である。**

## 配る単位は「フォルダ」——これが効いてくる

[Skillの正体は指示書とスクリプトを束ねたフォルダである](./what-are-agent-skills.md)。この一点が、配布のしやすさをそのまま決めている。フォルダなので、コピーでも、zipでも、Gitリポジトリでも配れる。特別な配布基盤が要らない。

実際の入口は、使う場所によって分かれる。[Anthropicの公式ドキュメント](../sources/article-tools-agent-skills-overview.md)によれば、Claude Code では `~/.claude/skills/`（personal）または `.claude/skills/`（project）にディレクトリを置くだけでよく、APIへのアップロードは不要である。claude.ai では Settings > Features から zip でアップロードする方式（Pro/Max/Team/Enterprise、code execution 有効時）になる。[Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)は、完成したSkillを `.skill` 形式のファイルとしてダウンロードでき、受け取った側は設定画面からアップロードすれば同じSkillを使えるようになると説明している（[30:00]、聞き取り）。

ただし、ここに**最初につまずくポイント**がある。同公式ドキュメントは、Custom Skillsは環境をまたいで同期しないと明記している（引用は[what-are-agent-skills.md](./what-are-agent-skills.md)を参照）。claude.ai にアップロードしたSkillが Claude Code でも使えるようになる、といったことは起きない。さらに claude.ai 方式は個人単位での利用であり、**組織全体での共有やadmin管理はできない**と同ドキュメントは述べている。「1人が作って全社に配る」を素朴に期待すると、ここで止まる。組織配布をやりたいなら、次に見るリポジトリ＋プラグインという経路になる。

## リポジトリで配る——google/skills という実例

大規模に配っている実物を見るのが早い。[google/skills解説動画](../sources/video-tools-google-skills-marketplace.md)は、GoogleがAnthropic発のAgent Skills仕様に乗り、Google Cloud・Google Ads・Google Analytics等の操作手順をスキル集として公開したと紹介している。同動画は、SKILL.mdが109個あり全部を足すと2万3千行を超える（[01:00]、聞き取り）、Claude Codeのプラグインmarketplaceには16個のプラグインが登録されている（[06:00]、聞き取り）、と述べている。

規模の内訳も同動画は示している（聞き取り）。カテゴリ別ではAI/ML系18個・Infrastructure系28個（うちAgent Platform関連13個）・Databases系10個、単一製品でなく複数製品を組み合わせる横断スキルが9個、Google Cloud以外にもGoogle Ads APIが12個・Google Analytics APIが2個ある。一方でFirebase・Flutter・Android・Genkitはこの109個には含まれず、それぞれ別のリポジトリ（`firebase/agent-skills` 等）で製品チーム側が管理しているとされる。**「配る」は1つのリポジトリに全部詰め込むことではなく、製品チームごとに分けて配ることも含む**——ここも実例から読み取れる設計判断である。

導入は2ステップだと同動画は説明している（聞き取り）。

```
claude plugin marketplace add google/skills
claude plugin install <名前>@google-plugins
```

プラグインごとに選んで入れられ、後から外せる。ここで重要なのは、**プラグインがSkillとMCPサーバーのセットになっている**点である（同動画・聞き取り）。配布の単位は「Skill 1つ」ではなく「その仕事に必要な能力一式」になりうる。[MCP](./what-is-mcp.md)とSkillは競合ではなく同梱される、という実務上の実態がここに出ている。

なお同動画は、プラグインの中身はgoogle/skills本体ではなくgemini-cli-extensionsやGoogleCloudPlatform配下の別リポジトリを参照しており、google/skills自体はそれらへの入口となるカタログの位置づけだと説明している（聞き取り）。

同動画はまた、firebase-basics の `references/setup/` 配下に `claude_code.md`・`gemini_cli.md`・`cursor.md`・`github_copilot.md`・`antigravity.md` といったツールごとの導入手順が用意されており、ツール間の差を配布側が吸収していると紹介している（聞き取り）。**配る側が「どのツールで使うか」の差を引き受ける**——これは社内配布でも真似する価値のある作法である。

## バージョン管理——「最新を追う」は本番では危ない

配布で最も見落とされるのが、更新をどう追うかである。同動画は2つの経路を対比している（聞き取り）。

| 経路 | 追うもの | 本番向きか |
|---|---|---|
| `npx skills add` | mainブランチの最新 | 挙動が変わりうる |
| plugin marketplace | ref でピン止めされたバージョン | 向く |

対話的に選べる手軽さから `npx skills add` を選びがちだが、mainの最新を追うため**昨日と今日でエージェントの挙動が変わりうる**。同動画は、本番運用にはプラグイン経由か、フォークして自分でバージョン管理するのが安全だとしている。

これは一般化できる。**Skillは「ドキュメント」ではなく「実行される定義」である**。ライブラリと同じ扱い——どのバージョンが動いているか特定できる状態を保つ——が要る。

## ライセンスと「正」の所在

配られているものを社内向けに改変してよいかは、ライセンス次第である。同動画は、google/skills のライセンスは Apache-2.0 であり、社内向けに削ったり書き換えたりするのは自由だとしている（[08:00]、聞き取り）。

一方で、**直したものを上流に返す経路は細い**とも同動画は指摘する。中身はGoogleの社内リポジトリから Copybara という仕組みで自動エクスポートされており、リポジトリの「正」はGoogle社内側にある。GitHub上のコントリビューターは6人で、うち自動化アカウントが203コミットを入れており、人が集まって育てるOSSというよりGoogle社内のミラーに近い、タグやリリース、Discussionsも用意されていない、と評している（聞き取り）。

ここから引ける実務判断は明快である。**上流に修正を取り込んでもらう前提で運用しない。** 手元でフォークし、必要なら削り、上流の更新は差分で取り込む——外部Skill集を業務に入れるなら、この構えが現実的である。

そのうえで、**自作すべきものと借りるべきものの線引き**を同動画は示している（聞き取り）。自社側で書くべきは命名規約・ネットワーク設計の制約・IAMロールの割当ポリシーといった**自社固有のルール**であり、SDKのバージョンアップ等で変わりうる製品の使い方は配布元に任せてよい。例として、`bigquery-basics` の前後に自社のvalidationを挟む運用が挙げられている。**借り物を書き換えるのではなく、借り物を挟み込む形で自社ルールを効かせる**という設計である。

## セキュリティ——Skillを入れることは「コードを入れる」こと

ここが配布の話で最も重い論点である。Skillはスクリプトを含みうるフォルダであり、[段階的開示](./progressive-disclosure.md)の設計上、**スクリプト本体はコンテキストに載らないまま実行される**。つまり、読まずに走る。

[Anthropicの公式ドキュメント](../sources/article-tools-agent-skills-overview.md)は明確に警告している。

> 引用: 「Use Skills only from trusted sources: those you created yourself or obtained from Anthropic」

同ドキュメントは「a malicious Skill can direct Claude to invoke tools or execute code in ways that don't match the Skill's stated purpose」——悪意あるSkillは、そのSkillが謳っている目的と一致しない形でツール呼び出しやコード実行をClaudeに指示しうる——とリスクを説明し、外部URLを取得するSkillは特にリスクが高いとしている。対策としてEnterprise版には Skill content scanning 機能があるとされている（Skills APIやConsole経由のアップロードを除くcustom Skillsが対象）。

[Anthropicのエンジニアリングブログ](../sources/article-tools-agent-skills-equipping-real-world.md)も同じ警告を、より踏み込んだ言い方で置いている。「malicious skills may introduce vulnerabilities in the environment where they're used or direct Claude to exfiltrate data」——利用環境に脆弱性を持ち込む、あるいはデータを外部に持ち出させる可能性がある。特に警戒すべき対象として、コード依存関係、画像やスクリプトといった同梱リソース、そして外部の信頼できないネットワーク先へ接続させる指示・コードを挙げている。

**この2つは独立した公式資料が同じことを言っている論点である。**「便利そうだからGitHubで見つけたSkillを入れる」は、`npm install` で素性の知れないパッケージを入れるのと同じ性質の行為だと理解しておきたい。社内で回すなら、最低限これだけは決めておく。

- 入手元を限定する（自作・ベンダー公式・社内レビュー済みのみ）
- 同梱スクリプトと外部通信先はレビュー対象にする
- どこから入れたか・どのバージョンかを記録する

## 増やしすぎない——ガバナンスの実務は「引き算」

最後に、地味だが効く話をする。**Skillは増やすほど効くわけではない。**

[Claude Code Skillを21個運用した記事](../sources/article-tools-claude-code-skill-design.md)の著者は、21個のうち16個は自作だとしたうえで、実際に毎週使うのは5〜6個のみだと明かしている。同記事はこれを受けて、月1回程度の見直し・モデル更新時のBenchmark実行・不要なSkillの定期削除という**「引き算のメンテナンス」**を実践しているとしている。

減らす理由は精神論ではない。Skillの起動判定は description だけで行われるため（[progressive-disclosure.md](./progressive-disclosure.md)）、**似たSkillが増えるほど誤起動が起きやすくなる**。誤起動が起きる仕組みと避け方は[writing-good-skills.md](./writing-good-skills.md)にまとめている。

**組織のSkillカタログは、増やす管理より減らす管理のほうが難しく、効果が大きい。** 誰が棚卸しするかを決めていない状態で配布だけ始めると、半年後に「入っているが誰も使っていないSkill」が誤起動の温床になる。書き方そのものの指針は[writing-good-skills.md](./writing-good-skills.md)を参照してほしい。

## 次に読む

- [what-are-agent-skills.md](./what-are-agent-skills.md) — 配る対象そのものの定義
- [writing-good-skills.md](./writing-good-skills.md) — 誤起動しないdescriptionの書き方
- [progressive-disclosure.md](./progressive-disclosure.md) — スクリプトが読まれずに実行される仕組み
- [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) — そもそも何を作って配るかの判断

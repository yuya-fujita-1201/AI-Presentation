---
type: Concept
title: 起動されるSkillの書き方——description・自由度・500行の壁
description: 実際に呼び出され、期待どおりに動くSkillを書くための規則を、Anthropic公式のベストプラクティスと21個運用した実務記事の両面から整理する。descriptionの書き方、タスクに応じた自由度の設定、SKILL.md 500行の上限、評価を先に作る開発手順、よくある失敗パターンを扱う
tags: [agent-capabilities, agent-skills, skill-authoring, prompt, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T10:20:00+09:00"
---

# 起動されるSkillの書き方

[what-are-agent-skills.md](./what-are-agent-skills.md) で見たとおり、Skillはフォルダに `SKILL.md` を1枚置けば作れる。ただし**作れることと、実際に呼び出されて期待どおり動くことは別**である。このファイルは、その差を埋めるための規則を扱う。

書き手が向き合う相手は2つある。ひとつは**起動判定**——数あるSkillの中からこれが選ばれるか。もうひとつは**実行品質**——選ばれた後、狙った手順どおりに動くか。前半（description・命名）が前者、後半（自由度・行数・評価）が後者に対応する。

## 大原則：コンテキストは共有財である

[Anthropicの公式ベストプラクティス](../sources/article-tools-agent-skills-best-practices.md)は、良いSkillの条件を「concise, well-structured, and tested with real usage」（簡潔で、構造がよく、実際の利用でテスト済み）と規定し、その土台としてコンテキストウィンドウを「a public good」——公共財——として捉えるべきだとしている。システムプロンプト・会話履歴・他のSkillのメタデータ・ユーザーの実際の要求と、限られた枠を分け合っているからである。

ここから直接に出てくる帰結が「書きすぎない」ことだ。同ドキュメントは前提として「Claude is already very smart」と述べ、**モデルが既に知っている説明を書くべきではない**としている。具体例として、pdfplumberのコード例だけを示す約50トークンの簡潔版と、「PDFとは何か」の説明から始まる約150トークンの冗長版を対比し、簡潔版を推奨している。3倍のコストを払って得られるものが何もない、という比較である。

初心者がSkillを書くとき、つい「丁寧に説明しよう」として冗長版を書いてしまう。相手は新入社員ではなく、一般知識は既に持っている実行者だと考えるとよい。書くべきは**一般知識ではなく、あなたの現場に固有の手順**である（この区別は[overview.md](./overview.md)の「モデルの外側に手順書を置く」という定義そのものでもある）。

## description——ここが最重要

前掲の公式ドキュメントは、metadataの `name` と `description` を特別扱いしている。

> 引用: 「The 'name' and 'description' in your Skill's metadata are particularly critical. Claude uses these when determining whether to trigger the Skill in response to the current task.」（[Skill authoring best practices](../sources/article-tools-agent-skills-best-practices.md)）

理由は[progressive-disclosure.md](./progressive-disclosure.md)で見た構造にある。起動判定の時点でモデルの目に入っているのは description だけであり、本文はまだ読まれていない。同ドキュメントは、Claudeは100以上のSkillの中から description のみを手がかりに選択判断を行うとしている。**本文をどれだけ良く書いても、descriptionが弱ければ一度も読まれない。**

書き方の規則は具体的である。

- **三人称で書く**。同ドキュメントは「Always write in third person」と明記し、「I can help you...」のような一人称表現は discovery（発見）の問題を起こすため避けるべきだとしている
- **「何をするか」と「いつ使うか」の両方を書く**。良い例として挙げられているのは「Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.」——前半が機能、後半（Use when〜）が発動条件である
- **曖昧な記述は不可**。「Helps with documents」は悪い例として明示されている

実務側からも同じ指摘が出ている。[21個のSkillを運用した記事](../sources/article-tools-claude-code-skill-design.md)は、よくある失敗の2つ目として「description曖昧」——「便利なスキル」といった記述で済ませてしまう問題——を挙げ、対策は『何をするか』＋『いつ使うか』を具体化することだとしている。加えて同記事は、description は250文字で切り詰められるため**重要なキーワードは前半に入れるのがコツ**だと述べている（この文字数上限は同記事の記述であり、公式ドキュメント側の記載としては確認していない）。

[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)も、いつ・どのような場面で使うスキルなのかを明示しておかないと、類似のスキルが複数存在する場合にAIが誤ったスキルを読み込んでしまうことがあると注意を促している（[43:00]、聞き取り）。**公式・実務記事・入門動画の3つが、独立に同じ一点を指している。**

## 命名

公式ドキュメントは gerund 形（`processing-pdfs`、`analyzing-spreadsheets` のような動詞+ing形）を推奨している。避けるべき名前として、`helper` / `utils` / `tools` といった曖昧な語と、`anthropic-helper` のような予約語を含む名前を挙げている。

## 自由度を設計する——「崖のある細い橋」か「障害物のない野原」か

ここからは実行品質の話になる。公式ドキュメントの中でも実務的に効くのが、**タスクの性質に応じて指示の具体性を変える**という考え方である。

| 自由度 | どんなタスクか | 書き方 |
|---|---|---|
| **High** | 複数の妥当なアプローチがある | テキストによる一般的な指示 |
| **Medium** | ある程度型が決まっている | 擬似コード、パラメータ付きスクリプト |
| **Low** | 操作が壊れやすく一貫性が重要（例: データベースマイグレーション） | 「Run exactly this script」と特定のスクリプトを厳密に指定 |

同ドキュメントはこの違いを、低自由度＝「narrow bridge with cliffs on both sides」（両側が崖の細い橋）、高自由度＝「open field with no hazards」（障害物のない野原）という比喩で表現している。橋の上では歩き方を厳密に指定し、野原では方角だけ告げればよい。

初心者が誤りやすいのは方向を取り違えることだ。**壊れやすい操作ほど自由に書いてはいけない**。逆に、正解が複数ある仕事に細かい手順を書くと、状況に合わない手順を強制することになる。自分のタスクがどちらの地形かをまず判定する。

## 500行の壁と、ファイル分割の規則

公式ドキュメントは「Keep SKILL.md body under 500 lines for optimal performance」と具体的な行数上限を示し、この上限に近づく場合は複数ファイルに分割すべきとしている。分割にも規則がある。

- **参照ファイルはSKILL.mdから1階層のみ**（深いネストは避ける）
- **100行を超える参照ファイルには目次を付ける**

1階層に制限する理由が実務的で重要だ。同ドキュメントは「Claude may partially read files when they're referenced from other referenced files」——参照ファイルからさらに参照されたファイルは部分的にしか読まれないことがある——と述べ、`head -100` のような部分読みになりうる点を挙げている。**深い階層に置いた重要な指示は、読まれない可能性がある。**目次を付けるべき理由も同じで、部分読みされても全体像が分かるようにするためである。

なお、この分割は[progressive-disclosure.md](./progressive-disclosure.md)で扱った3階層構造の Level 2 にあたる。同じ仕組みを、あちらでは「なぜ軽いのか」の側から、ここでは「どう書くか」の側から見ている。

## 評価を先に作る

公式ドキュメントの中でも見落とされやすいのが開発手順の指定である。同ドキュメントは「Create evaluations BEFORE writing extensive documentation」と明記し、①ギャップの特定 → ②3シナリオ作成 → ③ベースライン測定 → ④最小限の指示作成 → ⑤反復、という5ステップの評価駆動開発を示している。ドキュメントを厚く書いてから検証するのではなく、**測る仕組みを先に用意して、必要最小限の指示から足していく**。

テストは全モデルで行うべきだとされている。Haiku（十分なガイダンスがあるか）・Sonnet（明確で効率的か）・Opus（過剰説明していないか）と、モデルごとに見る観点が違う点が面白い。小さいモデルでは不足を、大きいモデルでは過剰を検出する。

開発手法としては、Skill設計を手伝う「Claude A」と、実際にSkillを使ってタスクを行う「Claude B」に役割を分担させる手法が紹介されている。書き手と使い手を分けることで、書き手には自明だが使い手には伝わらない箇所が表面化する。

実務記事側も同じ問題意識を持っている。[21個運用した記事](../sources/article-tools-claude-code-skill-design.md)は、失敗パターンの3つ目として「テストなし（作って満足）」を挙げ、対策として `/skill-creator` の Eval モード（A/Bテストで品質検証）を使うべきだとしている。同記事は、description を自動最適化する Improve モードの適用後に「6つのドキュメント作成スキルのうち5つでトリガー精度が改善」したと報告している。ここでも改善対象が description である点は一貫している。

## アンチパターン

公式ドキュメントが挙げるものと、実務記事が挙げるものを並べる。

**公式（[best practices](../sources/article-tools-agent-skills-best-practices.md)）:**

- **Windows形式のパス（バックスラッシュ）**を使う。フォワードスラッシュを常用すべき
- **選択肢を並べすぎる**。pypdf / pdfplumber / PyMuPDF のように並列に示すのではなく、デフォルト＋エスケープハッチ（例外時の逃げ道）の形にする
- **MCPツールの名前を省略する**。SkillからMCPツールを使う場合は必ず完全修飾名 `ServerName:tool_name`（例: `BigQuery:bigquery_schema`）を使う。サーバー名を省略すると「tool not found」エラーになりうる

**実務（[21個運用した記事](../sources/article-tools-claude-code-skill-design.md)）:**

- **詰め込みすぎ**——複数の役割を1つに詰め込む。対策は 1 Skill = 1目的に分割すること
- **放置**——モデル更新後に未対応のまま放置する。対策は定期的に Benchmark（Pass rate・実行時間・トークン数の計測）を実行すること

「選択肢を並べすぎる」と「詰め込みすぎ」は、出所は違うが同じ病理を指している。**書き手の迷いをそのままファイルに書くと、実行するAIの迷いになる。**判断は書き手が済ませておく。

## 公開前チェックリスト

公式ドキュメントが挙げる公開前チェック項目は次のとおり。

- descriptionが具体的か（何をするか＋いつ使うか）
- SKILL.md本文が500行未満か
- 参照ファイルが1階層に収まっているか
- Haiku / Sonnet / Opus でテストしたか
- 評価を3件以上作成したか

## 育て方——最初から完成形を目指さない

規則を並べると難しく見えるが、始め方のハードルは低い。[21個運用した記事](../sources/article-tools-claude-code-skill-design.md)の著者は「最初はnameとdescriptionだけのシンプルなSKILL.mdで十分。使いながら育てていくのが一番のコツ」と述べ、Skillを持つことを「『自分専用のClaude Code』を育てることに近い」と総括している。同記事は運用面でも、月1回程度の見直し・モデル更新時のBenchmark実行・不要なSkillの定期削除という「引き算のメンテナンス」を勧めている。実際、著者は21個を保有しているが毎週使うのは5〜6個のみだと明かしている。

[入門動画](../sources/video-tools-claude-skills-beginner-guide.md)も、作って終わりではなくレビューして改善点を洗い出し、それをもとにもう一度改善するというサイクルを1回挟むだけでもアウトプットが大きく向上すると述べている（[47:00]〜[48:00]、聞き取り）。同動画は作成時のコツとして、①ユーザーが何をインプットするか ②どう処理してほしいか ③最終的にどんなアウトプットになってほしいか の3点を大きく分けて言語化することを挙げている（[47:00]、聞き取り）。

**1回目で完成させようとしない。descriptionだけ書いて動かし、外したところを直す。**これが公式の「評価を先に作る」と実務の「使いながら育てる」が合流する地点である。

## 次に読む

- [progressive-disclosure.md](./progressive-disclosure.md) — 500行制限やファイル分割規則が「なぜ」必要かの仕組み側
- [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) — そもそもSkillで書くべき用事なのかの判断

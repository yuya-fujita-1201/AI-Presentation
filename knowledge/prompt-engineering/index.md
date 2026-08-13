# prompt-engineering — プロンプトエンジニアリングについてのナレッジ

チャット型AIを使ったことはあるが、まだ「なんとなく」で書いている段階の人が、指示の設計を体系として捉え直すためのディレクトリ。学術サーベイ2本・国内外の入門記事・Anthropic公式ドキュメント・YouTube解説動画5本（[../sources/index.md](../sources/index.md) 参照）を情報源とする。

基礎（定義・構造・技法）から始まり、その外側にある文脈設計、さらに外側のループ設計、そして最新モデルで何が変わりつつあるかまでを扱う。

## 内容

- [what-is-prompt-engineering.md](./what-is-prompt-engineering.md) — プロンプトエンジニアリングとは何か。定義・語源と、出力の質が指示の出し方で変わる理由
- [prompt-anatomy.md](./prompt-anatomy.md) — プロンプトの構造。一文ではなく要素の組み合わせとして分解し、記法・テンプレート化まで
- [core-techniques.md](./core-techniques.md) — 基本技法。明確で直接的な指示・zero-shot・few-shot／実演・ロールプレイ・補完と、それぞれの限界
- [why-context-matters.md](./why-context-matters.md) — なぜ文脈が効くのか。理由まで伝える効果、渡す情報の適量、コンテキストウィンドウという上限
- [taxonomy-and-landscape.md](./taxonomy-and-landscape.md) — 技法体系の全体像。41技法・58技法を扱う2つの学術サーベイが描く地図と、その使い方
- [five-engineering-stages.md](./five-engineering-stages.md) — 5つのエンジニアリング。プロンプト／コンテキスト／ハーネス／ループ／グラフの位置関係と入れ子構造
- [loop-engineering.md](./loop-engineering.md) — ループエンジニアリング。「指示する」から「指示する仕組みを作る」へ。HITL→HOTL、5+1の部品
- [modern-model-prompting.md](./modern-model-prompting.md) — 最新モデル時代のプロンプト。「足す」から「削る」への転換と、その正しい受け取り方

## 読む順番

初めての人は what-is-prompt-engineering → prompt-anatomy → core-techniques の順で土台を固めるとよい。ここまでが「1回の指示をうまく書く」範囲にあたる。

次に why-context-matters で指示の外側にある前提の設計へ進み、taxonomy-and-landscape で個別技法の全体地図を俯瞰しておくと、以降の話の位置がつかみやすくなる。

その先の five-engineering-stages → loop-engineering は、チャット型AIからエージェント的な使い方へ視野を広げる部分である。実務でまだ使わなくても、「うまくいかないときに何を疑うか」の地図として読んでおく価値がある。

最後の modern-model-prompting は、ここまで学んだ作法のうち何が不要になりつつあるかを扱う。**先に基礎を読んでいることを前提にしている**ため、単独で読むと「雑に書いてよい」と誤読しやすい。順番の最後に置く理由はここにある。

## 関連

- [../graph-engineering/index.md](../graph-engineering/index.md) — 5段階の最も外側「グラフエンジニアリング」を単独テーマとして掘り下げたディレクトリ。特に [term-lineage-and-layers.md](../graph-engineering/term-lineage-and-layers.md) は本ディレクトリの [five-engineering-stages.md](./five-engineering-stages.md) と同じ5段階を別の資料群から扱っており、あわせて読むと用語の揺れの実態がつかめる

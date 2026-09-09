# 独立レビュー A

評価対象は受講者が読む本文とページ画像。制作意図・作業ログは未参照。機械検証を点数化せず、点数も算出しない。2026-09-07。

## 06-rag-expanded

deck.json SHA256: `5862edab2ee3533062d313dbe054014328831fa10ee79192fad9d0db908a8bcc`

manuscript.md SHA256: `41aad8c549b08600b05de40510b1bff172d9454d367e7a0aa222d84d8b232bc2`

実見画像（全ページ、6枚contact単位）:

- decks/06-rag-expanded/build/contact/sheet-01-06.png
- decks/06-rag-expanded/build/contact/sheet-07-12.png
- decks/06-rag-expanded/build/contact/sheet-13-18.png
- decks/06-rag-expanded/build/contact/sheet-19-24.png
- decks/06-rag-expanded/build/contact/sheet-25-30.png
- decks/06-rag-expanded/build/contact/sheet-31-36.png
- decks/06-rag-expanded/build/contact/sheet-37-42.png
- decks/06-rag-expanded/build/contact/sheet-43-48.png
- decks/06-rag-expanded/build/contact/sheet-49-54.png
- decks/06-rag-expanded/build/contact/sheet-55-57.png

### Findings

- A-RAG-1｜項目5｜中5｜p14・18・19：p14本文「締切と例外が同じ断片に残るか」に対し図は断片1〜4だけ、p18は網、p19は漏斗。第2章の中核処理を例に適用する説明として、どの規程文が切れ、どの候補を検索してどう順番が変わるかを図から追えない。p14は「翌月5日／ただし休業日…」の実文を断片へ配置し、p18または19は旧版・現行版・宿泊費の候補と選択結果を図示する。

### 理解度プローブ（本文のみ）

- RAG：質問に関係する資料を取得し、その内容を使って回答を生成する方法。p4〜5で到達。
- 埋め込み：文章を、検索時に比較するための数値ベクトルへ変える処理。p16で到達。
- リランキング：最初の検索で取得した候補を並べ直し、回答に渡す資料を選ぶ処理。p19で到達。

本文57ページ・画像57ページを確認。画像不足なし。PPTX実表示は今回対象外。

## 07-okf-expanded

deck.json SHA256: `e7817eed73c5164437dca4ea2d98c5abfbcb9070c69bd3cda10ac527073cf816`

manuscript.md SHA256: `3035b616cd901bf9f0d81774b833223bc990efd60684252ca424289c3cf0da21`

実見画像（全ページ、6枚contact単位）:

- decks/07-okf-expanded/build/contact/sheet-01-06.png
- decks/07-okf-expanded/build/contact/sheet-07-12.png
- decks/07-okf-expanded/build/contact/sheet-13-18.png
- decks/07-okf-expanded/build/contact/sheet-19-24.png
- decks/07-okf-expanded/build/contact/sheet-25-30.png
- decks/07-okf-expanded/build/contact/sheet-31-36.png
- decks/07-okf-expanded/build/contact/sheet-37-42.png
- decks/07-okf-expanded/build/contact/sheet-43-48.png
- decks/07-okf-expanded/build/contact/sheet-49-54.png
- decks/07-okf-expanded/build/contact/sheet-55-55.png

### Findings

- A-OKF-1｜項目4｜小1｜p37冒頭「9月版の国内出張規程を使う架空例です。架空例：国内出張のFAQだけを渡し…」と、架空例の表現が連続する。一文に統合する。

### 理解度プローブ（本文のみ）

- OKF：人とAIが参照する知識を、説明欄と本文を持つ文章ファイルとして書く公開仕様。p5で到達。
- バンドル：関連する知識ファイルをフォルダ一式としてまとめたもの。p9で到達。
- verified：本文を元資料と照合した主体と日時の記録で、電子署名や正しさの保証ではない。p22〜24で到達。

本文55ページ・画像55ページを確認。画像不足なし。第1章定義、第2章実物、第3章トラブル・演習、第4章Tipsを本文で確認。


補足：RAG p34はcontactで末尾欠けを観測したが、単体 build/preview/slide-34.png を実際に開くと全文表示されていたため、内容のfindingから除外。

## 08-okf-practice-expanded

deck.json SHA256: `aaab0a2efe1d88a8bffc3205443c1d0f7f4ce126ca1ec31b5db210975d13db85`

manuscript.md SHA256: `bb4f95f8c51f85308ca8b7bb5af4dfe82a4af9488dea57c2e9792239474d07f4`

実見画像（全ページ、6枚contact単位）:

- decks/08-okf-practice-expanded/build/contact/sheet-01-06.png
- decks/08-okf-practice-expanded/build/contact/sheet-07-12.png
- decks/08-okf-practice-expanded/build/contact/sheet-13-18.png
- decks/08-okf-practice-expanded/build/contact/sheet-19-24.png
- decks/08-okf-practice-expanded/build/contact/sheet-25-30.png
- decks/08-okf-practice-expanded/build/contact/sheet-31-36.png
- decks/08-okf-practice-expanded/build/contact/sheet-37-42.png
- decks/08-okf-practice-expanded/build/contact/sheet-43-48.png
- decks/08-okf-practice-expanded/build/contact/sheet-49-54.png
- decks/08-okf-practice-expanded/build/contact/sheet-55-60.png
- decks/08-okf-practice-expanded/build/contact/sheet-61-62.png

### Findings

- A-PRACTICE-1｜項目2｜中5｜p17「A：超入門の4種＋要件」「glossary / decisions / howto / sources ＋ requirements」。現行07 p17の超入門は faq / sources であり、前編を学んだ人が4種の説明に戻れない。「この案件で考える最小構成」等へ変更するか、前編からの拡張を説明する。
- A-PRACTICE-2｜項目3｜中5｜p30は受付・影響分析をrisksへ置き承認後にdecisionsへ追加する手順。一方p29は「検討段階の下書き」のD-034をdecisionsとして提示し、p45解答は「案と影響範囲を決定記録へ残す」。未決の案を実際にどこへ保存すればよいかが一貫しない。演習解答をrisksへ統一し、p29を合意後の記録下書きとするか、決定案も置く例外を明示する。

### 理解度プローブ（本文のみ）

- OKF：人とAIが読む知識を説明欄と本文で残す公開書式。p6で到達。
- 要件：システムに求める入力や制約など、満たすべき振る舞いの条件。p8で到達。
- 決定記録：現在の条件が決まった理由・検討案・影響を残し、経緯の確認に使う記録。p9で到達。

本文62ページ・画像62ページを確認。画像不足なし。p21/29/42の ../../inputs、../../docs はp18構成の knowledge/requirements または decisions から正しく解決し、階層ずれの懸念は撤回。

## skills-mcp-cli-expanded

deck.json SHA256: `c3f4368912ee16afc5ddb8b1c00189b109124f0e1d73db8a90249ae727c73c5c`

manuscript.md SHA256: `1993a895f94b1af97e170df233ce0b5a7e10e85be445b856a713a79228be5b04`

実見画像（全ページ、6枚contact単位）:

- decks/skills-mcp-cli-expanded/build/contact/sheet-01-06.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-07-12.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-13-18.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-19-24.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-25-30.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-31-36.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-37-42.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-43-48.png
- decks/skills-mcp-cli-expanded/build/contact/sheet-49-50.png

### Findings

- A-TOOLS-1｜項目3｜中5｜p17〜25「SKILL.mdの記入例」「CLIで集計する例」「接続・実行に必要な準備」。手順・入出力は具体的だが、Skillをどこに保存してどう呼び出すかは「確認する」に留まり、CLI例は実行プログラムを付属しない。受講者が資料から一度試す経路を完結できない。対応アプリを1つ明示し、手順書だけの最小Skillを保存・指定・結果確認する一例を追加する。架空集計プログラムを完成品として見せる必要はない。

### 理解度プローブ（本文のみ）

- Skill：再利用する指示と関連資料をまとめたフォルダ。p4で到達、必須SKILL.mdと記入例はp17〜18。
- MCP：AIアプリと外部の機能やデータをつなぐ通信規格。p4で到達、役割はp20〜21。
- CLI：文字のコマンドでプログラムを操作する方法。p4で到達、具体的な操作の形はp23。

本文50ページ・画像50ページを確認。画像不足なし。

## 09-evaluation-expanded

deck.json SHA256: `2f5313a6365b894e48c50f6da62e198e2ef66d9772dc9e074a86a84a33e52153`

manuscript.md SHA256: `94a94718ca4e5594da6755be539927952c4fb6e7738fd9c2f899c69d281640d2`

実見画像（全ページ）:

- decks/09-evaluation-expanded/build/contact/sheet-01-06.png
- decks/09-evaluation-expanded/build/contact/sheet-07-12.png
- decks/09-evaluation-expanded/build/contact/sheet-13-18.png
- decks/09-evaluation-expanded/build/contact/sheet-19-24.png
- decks/09-evaluation-expanded/build/contact/sheet-25-30.png
- decks/09-evaluation-expanded/build/contact/sheet-31-36.png
- decks/09-evaluation-expanded/build/contact/sheet-37-42.png
- decks/09-evaluation-expanded/build/contact/sheet-43-48.png
- decks/09-evaluation-expanded/build/contact/sheet-49-53.png

### Findings

- A-EVAL-1｜項目2｜小1｜p46「領収書と申請期限は、N04で別に確認する」。p13で示した原文の表にはN01〜N03しかなく、本文だけ読む受講者はN04へ戻れない。p13にN04の概要を足すか、p46で配布原文の場所を併記する。

### 理解度プローブ（本文のみ）

- Evals：AIの結果が目的を満たすかを、問題と基準の組で繰り返し調べる取り組み。p5で到達。
- ルーブリック：確認項目と合格の判定基準をまとめた表。p16で到達。
- 回帰テスト：以前できていたことや修正済みの失敗が、変更後に戻っていないかの再確認。p47で到達。

53ページ全本文・全画像を確認。

## 10-ai-security-expanded

deck.json SHA256: `7b4cfb8e370e781c5e25f4c23653249d47440235cd5daf95bcc8c16b502797b2`

manuscript.md SHA256: `4e75db8e6cc2a104fdf123debf270eb5899701a186ccdc4169199f30b258908d`

実見画像（全ページ）:

- decks/10-ai-security-expanded/build/contact/sheet-01-06.png
- decks/10-ai-security-expanded/build/contact/sheet-07-12.png
- decks/10-ai-security-expanded/build/contact/sheet-13-18.png
- decks/10-ai-security-expanded/build/contact/sheet-19-24.png
- decks/10-ai-security-expanded/build/contact/sheet-25-30.png
- decks/10-ai-security-expanded/build/contact/sheet-31-36.png
- decks/10-ai-security-expanded/build/contact/sheet-37-42.png
- decks/10-ai-security-expanded/build/contact/sheet-43-48.png
- decks/10-ai-security-expanded/build/contact/sheet-49-54.png
- decks/10-ai-security-expanded/build/contact/sheet-55-57.png

### Findings

- A-SECURITY-1｜項目4｜小1｜p22・23「信頼境界は、異なる信頼や権限の領域を分ける境目です。」が連続して完全に重なり、本文も依頼・資料・道具の3区分を反復する。p22を具体的な依頼と混入文の判別課題にして、p23を図解解答にすると理解が進む。

### 理解度プローブ（本文のみ）

- AIセキュリティ：AI利用に伴う情報漏えい・不正操作などの被害を防ぎ、抑える対策。p5で到達。
- プロンプトインジェクション：入力に混ざった指示によってAIの本来の動作が変わる問題。p18で到達。
- 最小権限：任せる仕事に必要な操作・対象の許可だけを与える考え方。p28で到達。

57ページ全本文・全画像を確認。OWASP公式LLM01 https://genai.owasp.org/llmrisk/llm01-prompt-injection/ とGemini CLIの当事者投稿 https://github.com/google-gemini/gemini-cli/issues/4586 を実際に開いた。直接・間接と対策の限界、報告環境0.1.13/sandboxなしは対応する。実消失を確定診断と扱わない本文の限定も確認。


## 11-ai-coding-expanded

deck.json SHA256: `e1bb1d52fee823e4a42cbdf875e22651426756bf46041d24b946ccf65d0ef91a`

manuscript.md SHA256: `013920438ef4e495b58346a874e1cbab26560f49c5d3d120400d0cb39780c36e`

実見画像:

- decks/11-ai-coding-expanded/build/contact/sheet-01-09.png
- decks/11-ai-coding-expanded/build/contact/sheet-10-18.png
- decks/11-ai-coding-expanded/build/contact/sheet-19-27.png
- decks/11-ai-coding-expanded/build/contact/sheet-28-36.png
- decks/11-ai-coding-expanded/build/contact/sheet-37-45.png
- decks/11-ai-coding-expanded/build/contact/sheet-46-53.png

### Findings

- A-CODING-1｜項目4｜小1｜現本文p33「下から推測せず、実際の表示と対象ファイルを読みます。」。「下から」が何を指すか分からない。「症状だけで決めつけず」など、原因を推測する前に表示を読む意味が伝わる文にする。

### 理解度プローブ（本文のみ）

- AIコーディング：コードの理解・作成・修正・検証をAIが支援すること。p5で到達。
- 期待値：実装の結果に合わせず、規程から先に決める正しい結果。p18〜19で到達。
- 差分：削除した行と追加した行を対比し、実際の変更内容を示すもの。p25で到達。

実見は53ページ版の全6contactと単体build/preview/slide-27.png。記録直前のdeck.jsonは55ページへ更新されていたため、現55ページ本文も全ページ精読し直した。上記SHAは55ページ版。contactは53ページ版のままであり、55ページ版の追加・移動後画像は未確認。機械的な生成物不一致は内容の減点findingにはしていない。

## 12-ai-ready-docs-expanded

deck.json SHA256: `0b15000bb3a870c88d1677d0201e30d3d4b4a240527004578096f08ea1b72740`

manuscript.md SHA256: `6d5d68653d18a7e334367523a7ff60b1799e27fef7a3d79ae842f08dd59f463a`

実見画像:

- decks/12-ai-ready-docs-expanded/build/contact/sheet-01-09.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-10-18.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-19-27.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-28-36.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-37-45.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-46-54.png
- decks/12-ai-ready-docs-expanded/build/contact/sheet-55-55.png

### Findings

- A-DOCS-1｜項目2｜小1｜p45「予約前なら、O03に従って部長の承認を受ける。」。本文に提示された旧版表p14は金額・対象・日付だけで、O03の条項本文がなく、受講者は解答の承認条件を本文内で照合できない。p14に旧版の承認条件と条項番号を補うか、p45で配布原文の場所と該当条項を併記する。

### 理解度プローブ（本文のみ）

- AI向け文書設計：人とAIが対象・条件・根拠をたどれるように文書を組み立てること。p5で到達。
- 文書を分ける単位：一つの質問への答えと、その対象・条件・根拠を一緒に読めるまとまり。p20〜21で到達。
- 適用版の選択：最新のファイルという理由で選ばず、この規程では出発日が適用期間に入る版を選ぶこと。p14〜15で到達。

55ページ全本文・全7contactを確認。画像不足なし。

## 初回レビューの確認範囲

8件の本文と計72枚のcontactを実際に開いた。contactが包含するスライドは合計442ページ。11のみ記録直前に本文が53→55ページへ更新され、現本文55ページは再精読済み、現版画像は未確認。他7件に画像不足はない。RAG p34およびAIコーディング旧版p27は単体PNGでも照合し、contactで見えにくかった箇所が単体では表示されるため文字切れfindingを作っていない。

このレビューは本文の教育構成・文章・実用性・図の意味・事実を対象とし、機械検証は加点・減点にしていない。01〜05実物との直接比較、PowerPoint/Keynote実機表示、実受講者の理解度は未検証。理解度プローブは読者として本文だけから記述したもので、実受講者試験の結果ではない。制作意図・作業ログは参照していない。

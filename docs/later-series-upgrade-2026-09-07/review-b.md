# 独立レビュー B — 2026-09-07

対象は自身が制作していない6件。rubric.mdの項目1〜6と、deck.json全文・全contact画像を確認した。制作ログ・制作意図・他のgraderの採点は参照していない。09/10はverification.jsonの存在を確認した後に審査した。枚数は品質点にせず、合計点は付けない。大20／中5／小1は指摘の重さを示す。機械ゲート、実アプリ表示、学習者試験は本レビューの判定対象外。外部URLの再取得による独立ファクトチェックは行っておらず、項目6は本文の条件・引用対応・内部整合の審査。

全6件で第1章のテーマ定義と第2〜4章の必要構成を確認。定義欠落や章欠落に相当する大指摘はない。以下に、修正できる具体的なfindingsのみ記録する。

## 06-rag-expanded

- deck SHA-256: `5862edab2ee3533062d313dbe054014328831fa10ee79192fad9d0db908a8bcc`
- 本文確認範囲：p1–57（deck.json全文）。
- 画像実見：
  - `decks/06-rag-expanded/build/contact/sheet-01-06.png`
  - `decks/06-rag-expanded/build/contact/sheet-07-12.png`
  - `decks/06-rag-expanded/build/contact/sheet-13-18.png`
  - `decks/06-rag-expanded/build/contact/sheet-19-24.png`
  - `decks/06-rag-expanded/build/contact/sheet-25-30.png`
  - `decks/06-rag-expanded/build/contact/sheet-31-36.png`
  - `decks/06-rag-expanded/build/contact/sheet-37-42.png`
  - `decks/06-rag-expanded/build/contact/sheet-43-48.png`
  - `decks/06-rag-expanded/build/contact/sheet-49-54.png`
  - `decks/06-rag-expanded/build/contact/sheet-55-57.png`
  - `decks/06-rag-expanded/build/preview/slide-25.png`（個別拡大）

### Findings

- B06-1｜項目6｜中（5）｜p32「2026年4月以降の利用」と「質問者へ出張日を確認」。適用判定に必要な交通費の利用日を、出張日へ置き換えている。月をまたぐ出張では同じ条件にならない。修正：質問を「交通費の利用日」に統一する。
- B06-2｜項目5｜中（5）｜p25「資料・検索・生成を順に確かめる」に対し図の主要ラベルは「層3｜読書机」「層2｜コンベア」「層1｜本棚」。障害箇所を実務ログへ結び付ける重要ページで、本文の工程名との対応を読者が翻訳する必要がある。修正：図に「生成（読書机）」「検索・入力への受け渡し（コンベア）」「資料（本棚）」を併記し、照合する記録を各層へ置く。
- B06-3｜項目3｜中（5）｜p31–33の切り分けとp33の記録ひな形は、確認項目の列挙までで、検索結果と実際の入力の違いを読んで原因を決める記入済みの例がない。p45–46も資料と回答の照合である。修正：既存例の一つを、取得された新版→入力から落ちた期限条件→誤答→引き渡し修正という短い記録と診断へ具体化する。枚数追加は必須ではない。

### 本文だけで答える中核概念プローブ

- RAG：質問に関係する資料を検索し、その内容を使って回答を生成する仕組み（p5）。
- 埋め込みモデル：文章を、似た意味の資料を探すための数値ベクトルへ変換するモデル（p16）。
- リランキング：検索で得た候補を再評価して並べ替える処理で、検索されていない資料を取り戻す処理ではない（p19）。

## 07-okf-expanded

- deck SHA-256: `2a7a8e54d25485102998105d132d3cad6fff95516bc9a6567ddc118de62c6230`
- 本文確認範囲：p1–55（deck.json全文）。
- 画像実見：
  - `decks/07-okf-expanded/build/contact/sheet-01-06.png`
  - `decks/07-okf-expanded/build/contact/sheet-07-12.png`
  - `decks/07-okf-expanded/build/contact/sheet-13-18.png`
  - `decks/07-okf-expanded/build/contact/sheet-19-24.png`
  - `decks/07-okf-expanded/build/contact/sheet-25-30.png`
  - `decks/07-okf-expanded/build/contact/sheet-31-36.png`
  - `decks/07-okf-expanded/build/contact/sheet-37-42.png`
  - `decks/07-okf-expanded/build/contact/sheet-43-48.png`
  - `decks/07-okf-expanded/build/contact/sheet-49-54.png`
  - `decks/07-okf-expanded/build/contact/sheet-55-55.png`

### Findings

- B07-1｜項目5｜中（5）｜p9「バンドルは、知識ファイルのまとまり」「宿泊費のFAQと精算手順を分けて置く」に対し、図は目次→宿泊費FAQ→出張規程という直列の参照経路。フォルダ一式という新概念の包含関係と、複数の知識ファイルが見えない。修正：バンドルを囲む枠の内側に目次・宿泊費FAQ・精算手順・変更履歴を配置し、原文参照は別の矢印で示す。読む順序はp19に任せる。
- B07-2｜項目4｜中（5）｜p20の列名「同じファイルに残す理由」に対し、精算書の提出手順の理由は「上限と別の時期・理由で変わる」。分ける理由がまとめる理由の欄に入り、初心者が逆の設計判断をする。修正：列を「まとめる／分ける判断と理由」にし、各行で判断を明示する。

### 本文だけで答える中核概念プローブ

- OKF：知識を一定の書式で記録して、人とAIが参照しやすくするための共通形式（p5）。
- 知識ファイル：用途を示す説明、答えとなる本文、確認元の参照先を持つ一件の知識の記録（p8）。
- バンドル：関連する知識ファイルをフォルダ一式としてまとめたもの（p9）。

## 08-okf-practice-expanded

- deck SHA-256: `b1862d58b7d5789ca5d02e2863f69f9aedf0a94539962def13261b14346d3b29`
- 本文確認範囲：p1–62（deck.json全文）。
- 画像実見：
  - `decks/08-okf-practice-expanded/build/contact/sheet-01-06.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-07-12.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-13-18.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-19-24.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-25-30.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-31-36.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-37-42.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-43-48.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-49-54.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-55-60.png`
  - `decks/08-okf-practice-expanded/build/contact/sheet-61-62.png`

### Findings

- B08-1｜項目6｜中（5）｜p28「上書き前の全文は Git の履歴に残る」。上書き前の内容がコミット済みである条件がなく、Gitが保存前の編集も自動で記録すると読める。修正：「上書き前にコミットした版はGit履歴から確認できる」とし、変更前に記録する手順を明記する。
- B08-2｜項目4｜中（5）｜p55「育てる：変更案を現行の要件と決定記録に反映し」。p28の「変更が合意されたら」と、未合意案を現行仕様にしない演習の重要条件が結論から落ちている。修正：「合意した変更を」に直し、未合意案は別に残すことを保つ。
- B08-3｜項目3｜中（5）｜p36「影響分析と、設計書のドラフト」の2本、p38「ケース作りと、テスト漏れの確認」の2本は、依頼文が続き、結果のどこを人が評価するかの実例がない。使い方の詳細がプロンプト集に寄り、要件が成果物へどう変換されるかを追いにくい。修正：少なくともp38の片方を、F-012の数量1／0／在庫超過のテスト表と、根拠あり・未決の区別、誤った期待結果の修正例へ置き換える。

### 本文だけで答える中核概念プローブ

- OKF：知識を人とAIが参照できる共通形式で記録するための書式（p6）。
- 要件：システムが満たすべき振る舞いや条件の記録（p8）。
- 決定記録：現在の要件とは分けて、変更を決めた理由・時点・関係者を残す記録（p9、具体化p28）。

## skills-mcp-cli-expanded

- deck SHA-256: `df676f322ca1e7196dec912c68ecec1768ce05b3e11cca52590feb6bea0f3dbd`
- 本文確認範囲：p1–52（deck.json全文）。
- 画像実見：
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-01-06.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-07-12.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-13-18.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-19-24.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-25-30.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-31-36.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-37-42.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-43-48.png`
  - `decks/skills-mcp-cli-expanded/build/contact/sheet-49-50.png`

### Findings

- BT-1｜項目4｜小（1）｜p10「CLIで実行できても、計算や対象データは間違えます」。誤りの可能性を教える文が、必ず間違う断定になっている。修正：「計算や対象データが正しいとは限りません」。
- BT-2｜項目5｜中（5）｜p20「MCPの3つの役割」はHost／Client／Serverの表だけで、p7の図も依頼→Skill→実行道具の抽象経路まで。MCPの主題であるClientがHost内にありServerと通信する構造と、売上サービスとの位置関係が図では説明されない。修正：p20を、AIアプリの枠内のClientと外部Server、その先の売上データを示すimage_textへ変更し、p22の検索要求・3件の応答を往復矢印に対応させる。

### 本文だけで答える中核概念プローブ

- Skill：再利用する指示と関連資料をまとめたフォルダ（p4）。
- MCP：AIアプリと外部の機能やデータをつなぐ通信規格（p4）。
- CLI：文字のコマンドでプログラムを操作する方法（p4）。

## 09-evaluation-expanded

- deck SHA-256: `2f5313a6365b894e48c50f6da62e198e2ef66d9772dc9e074a86a84a33e52153`
- 本文確認範囲：p1–53（deck.json全文）。
- 画像実見：
  - `decks/09-evaluation-expanded/build/contact/sheet-01-06.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-07-12.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-13-18.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-19-24.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-25-30.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-31-36.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-37-42.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-43-48.png`
  - `decks/09-evaluation-expanded/build/contact/sheet-49-53.png`

### Findings

- B09-1｜項目3｜中（5）｜p46「領収書と申請期限は、N04で別に確認する」。本編に提示される架空規程はp13のN01–N03で、N04本文は一度も示されない。原文照合を練習する解答が、スライド内だけでは検証できない新しい根拠を導入する。修正：N04の必要部分を演習前に提示するか、この文を「その他の精算条件は別途規程で確認する」に変更し、未提示の内容を既知扱いしない。
- B09-2｜項目3｜中（5）｜p33「変更前後の比較表」は合否だけを示し、何を変更して海外出張が悪化したかは提示されない。p34–35の比較原則は理解できるが、実際に採用／保留を決めるまでの一例が未完。修正：変更した依頼文の一文、海外出張への前後の回答、固定した基準を示し、重大な悪化のため保留する判断までつなぐ。

### 本文だけで答える中核概念プローブ

- 評価・Evals：AIの結果を目的に合う基準で確認し、その確認を問題と基準の組として繰り返す取り組み（p5）。
- ルーブリック：確認項目と判定基準をまとめた表（p16）。
- 回帰テスト：変更後に、以前できていたことが壊れていないか再確認すること（p47、p51）。

## 10-ai-security-expanded

- deck SHA-256: `7b4cfb8e370e781c5e25f4c23653249d47440235cd5daf95bcc8c16b502797b2`
- 本文確認範囲：p1–57（deck.json全文）。
- 画像実見：
  - `decks/10-ai-security-expanded/build/contact/sheet-01-06.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-07-12.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-13-18.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-19-24.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-25-30.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-31-36.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-37-42.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-43-48.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-49-54.png`
  - `decks/10-ai-security-expanded/build/contact/sheet-55-57.png`

### Findings

- B10-1｜項目5｜中（5）｜p23「参照資料を、操作の許可へ昇格させない」の図では、「利用者の依頼」が操作判断へつながらず、「規程本文」からだけ「操作の判断」へ線が入る。本文は許可を依頼に求めるが、図の主経路は規程から操作を決めるように見える。修正：利用者の依頼→許可範囲の確認→操作判断を主経路にし、規程本文→回答の根拠を別の枝にする。混入指示は許可確認へ入れない遮断線で示す。

### 本文だけで答える中核概念プローブ

- AIセキュリティ：AI利用に伴う情報漏えいや不正操作などの被害を防ぎ、抑える対策（p5）。
- プロンプトインジェクション：入力に混ざった指示がAIの本来の動作を変えてしまう問題（p18）。
- 最小権限：仕事に必要な許可だけを与える考え方（p28）。

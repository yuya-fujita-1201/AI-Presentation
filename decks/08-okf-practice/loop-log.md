# loop-log — 08 OKF 実践編：SI プロジェクトでの構築と運用（2026-09-02）

ブランチ: `deck/08-okf-practice`（main から分岐）。パイプラインは `pipeline/PAUSE` で停止中。
別セッションがここだけ読んで続きから再開できるように書く。

## Step 0（準備）

- 対象: `decks/08-okf-practice/deck.json`（新規。07「OKF 超入門」の続編、56 枚）
- 依頼の要点: SI プロジェクトで OKF を①ゼロから構築（RFP・提案書・機能一覧から、Claude Code への依頼文つき）②討議に伴う確定・変更の蓄積と管理③各工程・各層での活用④チーム運用のルールとやってはいけないこと。Grill me 20 問への回答で前提を固定（`decks/08-okf-practice/rubric.md` の読者像と、レビュー依頼書に反映）
- 発注者の回答で決まったこと: 請負に近い汎用パターン集／ナレッジは設計ドキュメントと同じ Git リポジトリ・社内限定／正式文書は Office で残し OKF は二次ナレッジ（参照は OKF が主、毎朝の差分確認）／Claude Code 全員利用・議事録は会議ツールの要約／金額・単価・契約条件・個人情報は書かない／材料は PPTX 30〜50 枚・Excel 200 行・Word 数十ページ／9 月に推進担当 2〜3 名が 1 日〜1 週間／依頼文はそのまま載せる／「確定」の条件は汎用に／要件が覆る型・確認者の権限・フォルダ構成は推奨案／実務メンバーは不慣れ前提／PR 必須か直接コミットかは両対応／壊れ方＝古い情報が残る／07 のたとえ語は正式名に置換／40〜50 枚＋付録／架空案件・SI 側 11 名
- 機械ゲート: `tools/lint_deck_text.py`／`tools/check_layout.py`／`tools/check_svg_fonts.py`／PPTX 3点／SVG `<g id>` 数＝仕様の expected_elements
- rubric: `decks/08-okf-practice/rubric.md`（07 の v2 を実践編向けに改訂。項目3を「SI の現実味」に）
- 新規出典: `knowledge/sources/article-adr-nygard.md`（決定記録の慣行の原典）

## グラフ（分担）

| ノード | 実装 | 結果 |
|---|---|---|
| Q 質問洗い出し（SI-PM／Dev-Test／Governance）| Workflow `okf-practice-grill-questions`（3並列）| 質問 29 件 → 統合して 20 問を発注者へ。全問回答あり |
| S1〜S5 図版（新規5本）| Workflow `okf-practice-svg-figures`（pipeline: make→独立 verify→不合格なら fix）| 5/5 一発合格（小の指摘のみ）。id 数 4/5/6/3/2 = 仕様どおり |
| M（deck.json 全文執筆）| メイン会話（1人）| `scratchpad/build_deck_08.py` で生成。初稿 56 枚（コミット 0afff13）|
| G 機械ゲート | 上記 | 初稿で code スライド7枚が溢れ→行数削減と code 領域拡張で解消。lint 0／layout 0／SVG 明朝 0／PPTX 3点 OK |
| R1〜R5 事前レビュー（実務メンバー／文体／SI-PM／事実図解／推進担当）| Workflow `okf-practice-prereview`（5並列）| 実行中 |
| Q1〜Q3 採点 | Workflow（3並列・レンズ分け）| 未着手 |

## 第0周（初稿の自己確認）

- 全 10 枚のコンタクトシートを目視: 文字切れ・重なりなし。code スライドは行数を 22 行以下に抑えて 12〜14px を確保
- 気になる点（レビュー待ち）: bullets・table・code が多く、07 に比べて挿絵が少ない（SVG 5 本のみ）。必要なら生成画像を数枚足す

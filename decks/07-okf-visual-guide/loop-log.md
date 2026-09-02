# loop-log — 07 OKF（オープンナレッジフォーマット）超入門 改訂（2026-09-02）

ブランチ: `loop/okf-primer-2026-09`（main から分岐）。パイプラインは `pipeline/PAUSE` で停止中。
別セッションがここだけ読んで続きから再開できるように書く。

## Step 0（準備）

- 対象: `decks/07-okf-visual-guide/deck.json`（旧「OKFビジュアルガイド」47枚 → 「OKF（オープンナレッジフォーマット）超入門」54枚）
- 依頼の要点: 改題／5層シリーズから切り離した独立資料化／読者＝自社の新規プロジェクトで OKF ナレッジを構築するメンバー／必須理解4項目（OKFとは・メリット・従来との違い・なぜAIに向くか）／初心者適合・抜け漏れと冗長・AIっぽさ（語句＋粒度と文体の統一）・図解の適否
- 機械ゲート: `tools/lint_deck_text.py`（AI定型句・closing字数・Markdown残留）／`tools/check_layout.py`（はみ出し・重なり・罫線交差）／`tools/check_svg_fonts.py`（明朝体フォールバック）／PPTX 3点（`unzip -t`・python-pptx 再パース枚数一致・notes_slide 0）／SVG `<g id>` 数＝図版台帳の expected_elements
- rubric: `decks/07-okf-visual-guide/rubric.md`（v2 findings 駆動。大20・中5・小1、項目ごと 80 以上で合格、3名中央値）
- loop-learnings.md を読んで反映した点: 事前スクラブ（レビュー）→採点の順／コンタクトシート再生成前に build/preview・contact・.svg-cache を消す／出典表は番号でなく eyebrow で参照／図の要素数＝本文項目数／maker 並列なし（deck.json は1人で書く）

## グラフ（分担）

| ノード | 実装 | 結果 |
|---|---|---|
| R1〜R5 事前レビュー（通読／文体／事実・独立性／図解／導入担当）| Workflow `okf-deck-prereview`（5並列・読み取り専用・findings schema）| 5/5 完了。findings 計 79 件、missing 15、redundant 12。全員が 大2件（slide-02 の5層依存・closing の「本編に戻ったら」）を検出 |
| S1〜S4 図版（新規3・改修1）| Workflow `okf-deck-svg-figures`（pipeline: make→独立 verify→不合格なら1回 fix）| 4/4 一発合格。id 数 4/3/2/6 = 台帳どおり |
| M（deck.json 全文リライト）| メイン会話（1人。文体統一のため分担しない）| `scratchpad/build_new_deck.py` で生成 |
| G 機械ゲート | 上記5本 | 54枚版で全部緑（lint 不合格0／layout 0／SVG明朝0／PPTX 3点OK）|
| Q1〜Q3 採点 | Workflow `okf-deck-grade-r1`（3並列・レンズ分け）| 第1周 実行中 |

## 第0周（ベースライン＝事前レビューの棚卸し、旧47枚に対して）

主な大・中（5名の和集合、重複統合）:
- 大: slide-02 が5層シリーズ前提（5名全員）／closing message が「本編に戻ったら…コンテキストの資料から」（5名全員）
- 中: タイトル未改題／「だから導入のハードルが低い」型の電報調／「AではなくB」型が本編で6〜7回／「あるある」と仕様書調の同居／「バンドル」「コンテキスト断片化」の無説明／検算の具体例なし／章末まとめが第1・4章にない／付録テンプレへの導線なし／テンプレ①に「AIには送らない」節が同居／テンプレ②に身分証欄なし／スターターフォルダ構成なし／用語解説なし／AIへの渡し方・チーム運用・既存資料移行の欠落／ASO・OSI・Looker は読者に不要
- 図解: SVG は要素数・最濃が本文と対応（良）。warm-okf-17（落とし穴）の1・3番目のアイコンが本文と弱対応（中、ImageGen再生成はせず受容）。図中の副次文字 14〜16px が小さい（中→17px以上に底上げ）

## 第1周（改善 → ゲート → 採点）

### ① 改善（コミット 26f2478 → cc3c5e5 → d9e5348 → 2d206ea）
- 改題・独立化: 表紙／位置づけスライド（diagram-deck-scope.svg）／closing。5層・本編・シリーズへの言及 0
- 構成: 第1章を「定義→たとえ→なぜ必要→Before/After→考え方の違い（新）→運用の違い（表）→なぜAIに向くか（新）→メリット→章末の一言（新）」に。第4章末にも一言。第5章に「プロジェクトで最初に置くもの」「AIへの渡し方」「チーム運用の4つの決めごと」を追加。付録に用語解説を追加。ASO・OSI・Looker・発端の伝聞を削除
- 文体: 「ではなく」7→3、AI定型句 0、電報調の解消、「丸投げ」「あるある」を中間温度の語へ、bullets を太字ラベル＋子項目の二階層に
- 実用: テンプレ①を AI に渡す部分だけに、テンプレ②に身分証欄（コメントアウト）、Step4 に既存資料の移し方、レビュー観点→付録チェックリストの導線
- 図: 新規3本（scope／mindset-shift／why-ai-friendly）＋bundle-tree 改修（okf_version バッジ削除）、ecosystem のラベルを「荷物の中身」に統一、verify-flow の本文重複注記を削除、副次文字を 17px 以上に
- 出典表: スライド番号でなく eyebrow で参照（挿入・削除でずれない）

### ② 機械ゲート（54枚）
lint 不合格0・警告0（「ではなく」3回・丸数字20）／check_layout 0件／check_svg_fonts 0件／PPTX unzip OK・54枚一致・notes 0

### ③ 採点（第1周）
（実行中。結果は下に追記）

# 独立レビュー C 最終再確認

2026-09-08。対象は自作でない11/12のみ。rubric項目1〜6に沿い、deck.json全55ページずつと全contact20枚を実見。制作意図・制作ログは採点根拠にしていない。前回review-c.mdを保持した。点数は算出しない。

## 残存 findings

両デッキとも項目1〜6の残存指摘なし（大20・中5・小1とも0件）。第1章のテーマ定義・必要性・役割、第2章の実物と条件付きメリット、第3章の切り分けと応用、第4章のTips・演習解答を本文と画像で確認。

## 前回指摘の確認

| ID | 最終ページと修正確認 |
|---|---|
| C11-1 | p15に理解／作成・修正／検証の入出力と確認点の比較表を追加。 |
| C11-2 | p16に関数・引数・戻す結果を導入し、p17のPythonコードへつながる。 |
| C11-3 | p28を言い過ぎた報告と確認に合う報告の比較へ変更。p29の確認範囲図と役割が分かれた。 |
| C11-4 | p35で編集したsubmission.pyと実行しているstarter.pyを左右比較。原因と対象変更を読める。 |
| C12-1 | p24でSkillを再利用する作業手順と関連資料のまとまりと定義。 |
| C12-2 | p18にFAQから原文への相対リンク、p22にrules節N01〜N03の照合操作を追加。examples/faq/over-limit.mdとexamples/sources/policy-v2.mdの実体・rulesアンカー・条文を確認。 |
| C12-3 | p19のN01・N02・N03を同等の濃色で提示し、金額だけが重要と見える強調を解消。 |
| C12-4 | p36の質問に「まだ予約していない」を追加。予約前承認の答えと整合。 |
| A-CODING-1 | p33を「原因を推測で決めず、実際の表示と対象ファイルを読みます。」へ修正。 |
| A-DOCS-1 | p14に旧版O03・新版N03の予約前承認を併記し、p45の解答の根拠を本文内で追える。 |

再確認中の軽微指摘：11 p16の「return（戻り値）」はreturn文と戻り値を混同するため項目6／小1相当と通知した。その後「return文」「結果（戻り値）のTrueまたはFalseを呼出し元へ返す」へ修正され、最終JSONと単体PNG・該当contactを再実見して解消を確認した。

## 本文だけによる理解度プローブ

### 11 AIコーディング

- AIコーディング：コードの理解・作成・修正・検証をAIが支援すること（p5）。
- 期待値：実装の結果に合わせず、元の規程から先に決める正しい結果（p18〜19、用語p53）。
- 差分：削除された行と追加された行を対比して、変更された内容を示すもの（p25）。

### 12 AI向け文書設計

- AI向け文書設計：人とAIが対象・条件・根拠をたどれるよう文書を組み立てること（p5）。
- 粒度：一件として分ける情報の大きさで、質問への答え・対象・条件・根拠を一緒に読める単位にする（p20〜21、用語p53）。
- 適用日と更新日時：適用日はどの出発日にその版を使うかの条件であり、更新日時は文書を作成・変更した記録なので、最新版だけで適用版を決めない（p14〜15、p29）。

## 最終SHAと実見画像

### 11-ai-coding-expanded

deck.json SHA-256: `7601ffbbffa23b35efebfada932b51fcb168c491b467a414ab4ccc9299358b8c`

- `decks/11-ai-coding-expanded/build/contact/sheet-01-06.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-07-12.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-13-18.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-19-24.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-25-30.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-31-36.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-37-42.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-43-48.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-49-54.png`
- `decks/11-ai-coding-expanded/build/contact/sheet-55-55.png`
- `decks/11-ai-coding-expanded/build/preview/slide-16.png`（最終修正を個別実見）

### 12-ai-ready-docs-expanded

deck.json SHA-256: `32312a6138de0b01ba34e1431c41c08d4a9cb41f71ae74ad731ec45569ec8bb2`

- `decks/12-ai-ready-docs-expanded/build/contact/sheet-01-06.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-07-12.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-13-18.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-19-24.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-25-30.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-31-36.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-37-42.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-43-48.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-49-54.png`
- `decks/12-ai-ready-docs-expanded/build/contact/sheet-55-55.png`

## 検証範囲と限界

build/checksのlint・layoutは両件とも不合格0・警告0を確認した。機械ゲートを内容の採点へ混ぜていない。本文・HTML由来PNGの読者レビューであり、PowerPoint/Keynote実表示、実AI操作、実受講者による理解度試験はこのレビューでは未確認。PPTXの構造検証は親の最終機械検証に分離する。旧SHAのverification.jsonは評価根拠にしていない。

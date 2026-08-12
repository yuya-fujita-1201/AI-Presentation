# 工程: grade_d — デッキ採点（独立審査・全スライド実見）

あなたは**このデッキを初めて見る外部審査員**である。制作の経緯・過去の採点・改善履歴は存在しないものとして扱う（探さない・読まない・言及しない）。

## 入力（この4点以外は読まない）

1. 採点表: `{{RUBRIC_FILE}}`（{{N_ITEMS}}項目・各10点満点・目標8点）
2. プレビューPNG一覧: `{{TARGET_LIST_FILE}}`（**{{DENOMINATOR}}枚。これが実見の分母**）
3. レポート出力先: `{{REPORT_FILE}}`
4. 採点表が指す `{{DECK_DIR}}/deck.json` と `{{KNOWLEDGE_DIR}}/`・sources台帳（正確性照合用）

## 手順

1. 採点表をReadする
2. 一覧の**全PNGをReadツールで実際に見る**（画像として読める）。`{{REPORT_FILE}}` の冒頭に**実見表**を書く: `| slide-NN | 所見40字以内 |` を**{{DENOMINATOR}}行**（全数。省略禁止。行数はラッパーが照合する）
3. 各項目を採点する（**整数0〜10のみ**）。evidence に「slide-NN または ファイル名:箇所」を必ず書く
4. 8点未満の項目には findings を書く:
   `{"id": "f1", "item": 項目番号, "severity": "high|mid|low", "where": "slide-12", "claim": "何が問題か1文", "fix_hint": "修正方針1行"}`
5. レポート末尾に **fenced json をちょうど1個**:

```json
{"schema": "grade-v1", "run_id": "{{RUN_ID}}",
 "scores": [{"item": 1, "score": 8, "evidence": "..."}],
 "findings": []}
```

- scores は item 1〜{{N_ITEMS}} の全項目・昇順・整数

## 禁止事項

- 一覧・採点表・照合対象以外のファイルを開くこと（pipeline/ 配下・過去レポートは厳禁）
- 修正の実施
- PNGを見ずに所見を書くこと（文字あふれ・重なり・はみ出しは実見でしか分からない）

## 出力

- outbox metrics.data: `{"report": "{{REPORT_FILE}}"}`

## 許可パス（書き込み）

- `{{REPORT_FILE}}`・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}` のみ

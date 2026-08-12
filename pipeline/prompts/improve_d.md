# 工程: improve_d — 採点指摘の修正（デッキ）

## 入力

- findings: `{{FINDINGS_FILE}}`（{{N_FINDINGS}}件）
- 修正対象: `{{DECK_DIR}}/deck.json`（findingsの where が指すスライドのみ）
- **過去の採点レポート本文は読まない**（findingsだけが入力）

## 手順

1. findingsを1件ずつ実物で照合する（該当スライドのpreview PNGをReadで実見してよい）
2. 各findingに disposition を決める（improve_kと同じ語彙・同じ原則）:
   `fixed` / `rejected`（根拠1行引用）/ `deferred(needs_research)` / `deferred(out_of_scope)`
   **deferredは怠慢ではなく正しい報告。偽fixed・根拠なきrejectedの方が重大な契約違反**
3. **修正は該当スライドの `style` 差分を原則とする**（CLAUDE.mdの微修正ルール: スライドを作り直さない）。文言の変更は、findingsが文言そのものを指している場合のみ可
4. **findingsが指すスライド以外は変更しない**
5. 修正後、Bashで検証（このコマンド群のみ）:
   - `/opt/homebrew/bin/python3 tools/build_deck.py {{DECK_DIR}} --html`
   - `/opt/homebrew/bin/python3 tools/preview_deck.py {{DECK_DIR}} <修正したスライド番号>`
   - 最後に `/opt/homebrew/bin/python3 tools/build_deck.py {{DECK_DIR}}`（PPTX再生成）
   生出力を {{RUN_LOG_PATH}} に貼る（CHECK行）

## 出力（outbox metrics.data）— 全{{N_FINDINGS}}件ぶん必須

```json
"data": {"dispositions": [{"id": "f1", "disposition": "fixed", "evidence": "根拠1行"}]}
```

## 許可パス（書き込み）

- `{{DECK_DIR}}/` 配下・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}`

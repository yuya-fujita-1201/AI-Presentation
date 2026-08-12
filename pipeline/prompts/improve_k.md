# 工程: improve_k — 採点指摘の修正（ナレッジ）

## 入力

- findings: `{{FINDINGS_FILE}}`（{{N_FINDINGS}}件）
- 修正対象: findingsの `where` が指すファイルのみ（`{{KNOWLEDGE_DIR}}/` と knowledge/sources/）
- **過去の採点レポート本文・前回のimprove記録は読まない**（findingsだけが入力）

## 手順

1. findingsを1件ずつ**実ファイルで照合**する（whereの該当箇所をReadし、指摘が事実か確認する）
2. 各findingに disposition を決める:
   - `fixed`: 指摘が正しく、修正した（該当ファイルをEdit）
   - `rejected`: 指摘が誤り（実ファイルから根拠を1行引用する）
   - `deferred(needs_research)`: 指摘は正しいが、ソース収集からやり直さないと直せない
   - `deferred(out_of_scope)`: 指摘は正しいが、この工程の修正範囲外
3. **deferredは怠慢ではなく正しい報告である。直せない指摘をfixedと書く・根拠なくrejectedと書くことの方が重大な契約違反**
4. **findingsが指すファイル以外は変更しない**（「ついでの読みやすさ改善」も禁止。差分はラッパーが検査する）
5. 修正後: Bashで `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` を実行し、生出力を {{RUN_LOG_PATH}} に貼る（CHECK行）

## 出力（outbox metrics.data）— **全{{N_FINDINGS}}件ぶん必須（件数はラッパーが照合する）**

```json
"data": {"dispositions": [{"id": "f1", "disposition": "fixed", "evidence": "根拠1行"}]}
```

disposition の語彙: `fixed` / `rejected` / `deferred(needs_research)` / `deferred(out_of_scope)`

## 許可パス（書き込み）

- findingsの `where` が指すファイル・`knowledge/log.md`・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}`

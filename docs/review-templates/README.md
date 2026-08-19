# デッキ再レビューのプロンプトテンプレート（2026-08-20 の 01〜05 再レビューで使用）

- `grader-prompt-template.md` — 独立採点者用。`{GID}` `{DECK}` `{NSHEETS}` `{BENCH}` `{LENS}` `{OUT}` を置換して使う。採点表は `docs/ai-eng-series-rubric-v2.md`
- `maker-prompt-template.md` — 改善担当用。`{DECK}` `{MERGED}` `{DIFF}` `{GEN_NOTE}` `{DISP}` を置換。正本（01/02）に使うときは「文体・刻み・構成は変えない。大・agree≥2・明確な実害だけ」の節を追加する

手順（1周）:
1. `python3 tools/preview_deck.py decks/<deck>` → `python3 tools/contact_sheet.py decks/<deck>`
2. 採点者3名を並列起動（レンズ: 初心者通読／文章文体／事実図解実用）。出力は findings-v2 JSON
3. `python3 tools/aggregate_findings.py g1.json g2.json g3.json --out merged.json`（中央値・spread・findings 統合）
4. maker を起動（デッキごとに並列可。**git 操作禁止を明記**）→ `bash pipeline/bin/gate_deck.sh decks/<deck>` が OK になったら統合担当が目視してデッキ単位で即コミット
5. 再採点（新しい採点者）。全項目 80 以上で終了、未達があれば 2 へ

採点者・maker の共通ルール: 経緯を渡さない（maker ≠ grader）、点数は書かせず findings から計算、指摘は実物と突き合わせてから直す。

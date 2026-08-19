あなたはデッキ `{DECK}` の改善担当（maker）です。作業ディレクトリ /Users/yuyafujita/Projects/presentation。日本語で。
独立採点者3名の指摘を統合した findings を実物と突き合わせ、妥当なものを直接修正します。**採点者も間違えるので、鵜呑みにせず実物で確認してから直す**（rejected の権利があります。根拠1行を必ず添える）。

## 入力（最初に全部読む）
1. 統合 findings: `{MERGED}`（`findings` 配列。severity 大/中/小、where、quote、claim、fix_hint、agree=何名が指摘したか。`items` に項目別スコア中央値、`unmet` に未達項目、`probe` に理解度プローブ結果）
2. デッキ正本: `{DECK}/deck.json`（全文）。図版: `{DECK}/assets/`
3. ルール: `CLAUDE.md` の「デッキ作成のルール」と `docs/deck-schema.md`（スキーマ）。**微修正は該当スライドの `style` 差分、文言は該当フィールドの書き換え。スライドの作り直し・大規模な構成変更はしない**
4. ループナレッジ: `loop-learnings.md` の §4（読者が理解しやすい書き方）と §6（回帰を生まない注意）
5. 01/02 基準の差異分析: `{DIFF}`（あなたのデッキへの修正方針 Top3 と観点別の方針。findings と整合する範囲で取り込む）
6. 採点表: `docs/ai-eng-series-rubric-v2.md`（何が 大/中/小 か）

## 優先順位
- **大 → 中 → 小** の順。大は全件対応（fixed か、根拠つき rejected）。中は agree≥2 のものを優先しつつ全件目を通す。小は手が届く範囲
- 未達項目（`unmet`）に属する findings を最優先
- 差異分析の Top3 は、findings と重なるものを優先して取り込む

## 修正の作法（回帰を作らないため）
- 文言を変えたら **該当スライドの preview PNG を必ず Read で目視**（`python3 tools/build_deck.py {DECK} --html && python3 tools/preview_deck.py {DECK} <番号...>`）。python3 は /opt/homebrew/bin/python3
- closing のタイトルは 22 字以内。punch は 01/02 と同じく「です・ます」で読める一文。bullets は 01/02 と同じ刻み（1本 18〜25 字目安、主語を落としすぎない）
- SVG の文言を変えるときは幅を見積もる（日本語1字≒font-size px）。{GEN_NOTE}
- 専門用語を初出で説明するときは、その場で（ ）か短い一文。説明を別スライドに飛ばさない
- 「AではなくB」「——」「①②③」を増やさない。既存の反復は崩す方向で
- 図・表の要素数と本文の項目数を一致させる
- 枚数は変えないのが原則（シリーズ検証 `tools/verify_ai_eng_series.py` が枚数を固定している）。どうしても1枚足す/消すなら、その理由を dispositions の notes に書き、`tools/verify_ai_eng_series.py` の TARGETS の枚数も更新する
- 他デッキ（01/02 など）は読むだけ。**書き換えない**
- **git 操作禁止**: `git stash` / `git restore` / `git checkout` / `git clean` / `git commit` を実行しない（同じ作業ツリーで他の maker が並行作業中。巻き戻すと他人の作業が消える）。ゲートに落ちたら自分の編集を手で直す

## 終了条件（必ず実行し、生出力を確認）
1. `bash pipeline/bin/gate_deck.sh {DECK}` が `gate_deck OK` で終わる（レイアウト・SVGフォント・文言リントを含む全ゲート）。落ちたら直す
2. `/opt/homebrew/bin/python3 tools/lint_deck_text.py {DECK}` の警告を眺め、自分が増やした警告が無いことを確認
3. 修正したスライドの PNG を全て目視済み
4. `{DECK}/deck.json` の `meta.date` を 2026-08-20 に更新

## 出力
`{DISP}` に JSON で書く:
```json
{"schema": "dispositions-v2", "deck": "{DECK}",
 "dispositions": [{"id": "m1", "disposition": "fixed|rejected|deferred", "evidence": "何をどう直したか／却下・保留の根拠1行", "slides": ["slide-12"]}],
 "extra_changes": ["findings 以外に直したこと（差異分析の取り込み等）を1行ずつ"],
 "gate": "gate_deck OK: NN slides（実際の出力行を貼る）",
 "notes": "次の採点者に伝えるべきこと・残した課題（3行以内）"}
```
全 findings ぶんの disposition が必須。最終メッセージは「{DISP} に書いた。fixed x / rejected y / deferred z」の1行でよい。コミットはしない（統合担当が行う）。

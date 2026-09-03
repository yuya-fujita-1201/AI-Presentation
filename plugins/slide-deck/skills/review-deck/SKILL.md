---
name: review-deck
description: 既存の deck.json を機械的に一括レビューする（構造チェック・文言チェック・数量チェック・一覧サムネイル）。ユーザーが「このデッキをレビューして」「品質を確認して」「おかしいところがないか一通り見て」のように既存デッキ全体の点検を求めたときに使う。個別スライドの作成・微修正は create-deck を使う。
allowed-tools: Bash, Read, Edit, Glob, Grep
---

# review-deck — 既存デッキの機械 QA 一括レビュー

`create-deck` の手順4（機械チェック）を1回でまとめて回したうえで、`content-guide.md` に沿った内容チェックも行い、指摘を要約する。機械チェックは実装済みの検証ツールを束ねるだけで新しいロジックは持たないが、内容チェックは目視で行う。

## 手順

### 1. ビルド（HTML）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
```

### 2. 構造チェック（はみ出し・重なり・文字あふれ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>
```

### 3. 文言チェック（文字量・AI定型句など）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>
```

### 4. 数量チェック（スライドタイプ別の文字数・項目数の統計）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/deck_metrics.py" <deck_dir>
```

### 5. 図解チェック（architecture/dataflow/lifecycle/sequence/swimlane の配線・ラベル診断）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>
```
図解タイプを1枚も使っていないデッキでは対象0件で正常終了する。指摘があれば `create-deck` スキルの「4.5 図解タイプの修理ループ」の手順（診断1件→fixesの1点だけ直す→再診断、2ラウンド改善なしで停止）に従う。

### 6. 一覧サムネイル（pillow がある場合のみ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/contact_sheet.py" <deck_dir>
```
pillow が無い、または playwright が使えない環境では失敗しても致命的ではない（一覧確認を省略し、個別の `preview_deck.py` に切り替える）。

新しいテーマを使っているデッキなら、あわせてコントラストも確認する:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <テーマ名>
```

### 7. 内容チェック（機械チェックでは検出できない質）
上記1〜6は文字量・レイアウト・記法崩れなど**機械的に検出できる不備**の点検であり、構成や説得力そのものは見ていない。`${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` のチェックリスト（6章）に沿って、スライドごとに次を目視確認する。

- タイトルが結論文になっているか（「〜の現状」のような話題ラベルのままになっていないか）
- 本文（`bullets` / `table` / `lead` 等）にタイトルの結論を裏付ける根拠（数字・事例・出典）があるか
- 1スライドに複数のメッセージが混在していないか（1スライド1メッセージ）
- 抽象語（最適化・推進・活用 等）が具体的な動作・数字に言い換えられているか
- `closing` に「次のアクション」と「判断してほしいこと」が明示されているか

構成レベルの問題（型が合っていない、根拠が丸ごと抜けている等）は `style` の差分では直せないため、deck.json の該当スライドの中身（`title` / `bullets` / `lead` 等の文言）を書き直す提案として提示する。

## 8. 指摘の要約と修正提案
各ツールが stderr に出す `warning:` / `error:` を「N枚目（type=xxx）: 内容」の形でスライド番号ごとに集約し、ユーザーに一覧で提示する。`check_diagram.py` の指摘は診断 code も残す（「N枚目（type=xxx）: [code] 内容」の形。code はそのまま修理ループでの参照キーになる）。修正が明確なもの（文字あふれ・はみ出し・色 typo 等）は、`create-deck` の微修正ルールに従い **該当スライドの `style` への差分**として修正案を提示する。ユーザーが適用を求めたら deck.json を編集し、`build_deck.py <deck_dir> --html` → `check_layout.py <deck_dir>`（図解タイプがあれば `check_diagram.py <deck_dir>` も）を再実行して解消を確認する。

エラー（exit 1 で止まるもの）は必ず解消してから再ビルドする。警告はビルドを止めないため、内容を見て対応要否をユーザーと相談してよい。

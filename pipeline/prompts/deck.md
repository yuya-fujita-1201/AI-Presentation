# 工程: deck — draft→deck.json 構造変換とビルド

## 入力

- 原稿: `{{DRAFT_FILE}}`（完成済み）
- 出力: `{{DECK_DIR}}/deck.json`
- スキーマ: `docs/deck-schema.md`（**必読**）
- 挿絵プレースホルダ: {{N_FIGURES}}枚を `{{DECK_DIR}}/{{ASSET_PREFIX}}01.png` 〜 に配置済み（**draftのimage_textブロック登場順に割り当てる**）

## 絶対規則

- **文言不変・順序不変の構造変換のみ**。title / punch / bullets / caption / notes の文字列をdraftから一字も変えない（要約・言い換え・省略・追加はすべて禁止。機械ゲート check_deck_text.py が全文照合する）
- draftの `- figure:` 行は deck.json に入れない（brief工程が原稿から読む）
- 色はテーマトークンのみ（hex直書き禁止）。`meta.theme` = "accenture-purple"
- notes は deck.json の `notes` フィールドへ（HTMLのNキー表示用。PPTXに出ない仕様はビルダーが保証）
- meta: `id` = "{{THEME_SLUG}}"、`title` = デッキ題（draftの表紙から）、`date` = "{{TODAY}}"

## 手順

1. draft全文と `docs/deck-schema.md` をRead
2. 1ブロック=1スライドで順に変換する。image_text は `path` に `{{ASSET_PREFIX}}NN.png`（image_text登場順の連番）、`image_side` = ヘッダの side
3. Bashで検証（**このコマンド群のみ使用可**）:
   - `/opt/homebrew/bin/python3 tools/build_deck.py {{DECK_DIR}}`
   - `/opt/homebrew/bin/python3 tools/preview_deck.py {{DECK_DIR}}`
   - `/opt/homebrew/bin/jq '.slides|length' {{DECK_DIR}}/deck.json`
4. build失敗時はエラーメッセージの該当箇所のみ修正して再実行（**2回まで**。直らなければblocked）
5. CHECKログ: `jq` の枚数がdraftのブロック数と一致することを生出力付きで記録

## 出力（outbox metrics.data）

```json
"data": {"n_slides": 35}
```

## 許可パス（書き込み）

- `{{DECK_DIR}}/` 配下・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}` のみ

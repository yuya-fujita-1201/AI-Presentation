# 工程: knowledge — コンセプト設計・執筆（チェックポイント方式）

## 入力

- ソース台帳一覧: `{{LEDGER_LIST_FILE}}`（{{N_LEDGERS}}本。**この一覧が唯一の内容ソース**）
- 計画ファイル: `{{PLAN_FILE}}`（現在: {{PLAN_STATUS}}）
- 執筆先: `{{KNOWLEDGE_DIR}}/`
- 手本: `knowledge/graph-engineering/` のコンセプト群（構成・文体・粒度の見本として読んでよい）
- 読者像: 新入社員＋SI/IT理解のあるITコンサル・SE・エンジニア。**チャット型AIを使ったことがあるレベル**（エージェント的活用は未経験）。超初心者向けに丁寧に

## 手順

**{{PLAN_FILE}} が未作成の場合（初回ラン）:**
1. 台帳一覧の全ファイルをReadする
2. コンセプト設計（**{{CONCEPTS_MIN}}本以上**）を plan.json に書く:
```json
{"concepts": [{"file": "what-is-prompt-engineering.md", "purpose": "1行", "sources": ["knowledge/sources/video-....md", "knowledge/sources/article-....md"], "status": "todo"}]}
```
   - 各コンセプトの sources は**2件以上**（どうしても1件のみなら `"single_source_attributed": true` を付け、本文で帰属を明示する前提にする）
   - **sources集合が他コンセプトと完全一致してはならない**
3. 設計後、先頭の2本を執筆し status を "done" に更新する

**plan.json がある場合:** status=todo の先頭2〜3本を執筆し、書けた分だけ "done" に更新する

**執筆規則:**
- 1コンセプト=1ファイル・**1200字以上**。OKF frontmatter必須（type: Concept / title / description / tags / generated.by: claude-code/pipeline-opus, generated.at）
- **中核となる主張は独立したorigin 2ソース以上**で支持させ、本文に台帳へのインライン出典リンク（`../sources/xxx.md` 相対リンク）を必ず張る
- 単一ソースの主張は「〜としている」と帰属を明示する
- **出所がauto字幕のみの impact:high 主張（定義・数値・仕様・可否）は断定で書かない**（帰属＋（聞き取り）で書く。台帳の主張テーブルで確認する）
- ファイル間は相対パスのMarkdownリンクで接続。台帳側の「# 活用先」への追記もこの工程の許可範囲

**全コンセプトが done になったら（最終ラン）:**
1. `{{KNOWLEDGE_DIR}}/index.md` を作成/更新（推奨読書順・フロントマターなし）
2. `knowledge/index.md` にこのディレクトリを1行登録、`knowledge/log.md` に履歴追記
3. Bashで `/opt/homebrew/bin/python3 tools/validate_okf.py knowledge` を実行し、**生出力を {{RUN_LOG_PATH}} に貼る**（CHECK行）
4. コンセプト⇄台帳の双方向リンク（出典リンク⇄活用先）を自己照合し、結果をCHECK行で記録

**45分で全部終わらない前提の設計である。キリの良いところで `succeeded_partial` で終了してよい**（次のランが続きを引き継ぐ）。

## 出力（outbox）

- status: 全done＋検証済み → `succeeded` ／ 進捗あり → `succeeded_partial`
- metrics: `{"progress": doneの件数, "data": {}}`

## 許可パス（書き込み）

- `{{KNOWLEDGE_DIR}}/`配下・`knowledge/sources/*.md`（活用先追記のみ）・`knowledge/index.md`・`knowledge/log.md`・`{{PLAN_FILE}}`・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}`

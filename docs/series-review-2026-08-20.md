# AI Engineering 01〜05 再レビュー（夜間作業）— 2026-08-20

作業者: Claude Code（メインセッション＝maker／orchestrator。採点は経緯を渡さない別エージェント）
依頼: 強化したループエンジニアリングのナレッジ（`loop-learnings.md`）をもとに 01〜05 を再レビュー・直接修正し、01/02 を基準に 03〜05 との差異を分析、新しい発見をループナレッジへ還元する。06/07 は対象外。
ブランチ: `loop/ge-deck-review`。開始時点のバックアップコミット: `3ca29f1`（連番リネーム後の作業ツリー一括）。パイプラインは `pipeline/PAUSE` で停止中。

## 進行ログ（時系列・別セッションが読んで再開できる粒度）

- 01:04 パイプラインの improve_d run が、未コミットだった `tools/check_svg_fonts.py` を「許可外書込み」として隔離（friendly-fire 再発）。01:09 に PAUSE を設置、01:10 に隔離フォルダから復元
- 01:12 作業ツリーを一括バックアップコミット（`3ca29f1`）

- 01:15〜01:40 ツール整備: `tools/check_layout.py`（装飾1文字除外・spill 閾値12px）、`tools/check_svg_fonts.py`、`tools/lint_deck_text.py`（closing 22字・Markdown残留・ページ参照・AI定型句・対句/ダッシュ/丸数字・半角コロン）、`tools/contact_sheet.py`（6枚/画像）、`tools/deck_metrics.py`（5デッキ横並び指標）、`tools/aggregate_findings.py`（3名の findings を中央値集約）。`pipeline/bin/gate_deck.sh` に exit 16/17/18 として組込み、04 で通過確認
- 01:30 機械ゲートの baseline: 01 の SVG 3本（five-boxes / five-stages / prompt-scope）16要素が明朝体フォールバック → `text{}` 要素セレクタを追加して修正。04 slide-15 の引用出典行が 40px 枠を 10px 超（警告）。他は 0 件
- 01:40 採点表 v2 `docs/ai-eng-series-rubric-v2.md`（9項目・findings 駆動・大25/中5/小1・項目80以上で合格・理解度プローブ付き）を作成
- 01:45 第1周ベースライン採点: 5デッキ × 3採点者（レンズ: 初心者通読／文章文体／事実図解実用）= 15 エージェント並列起動。並行して 01/02 基準の差異分析エージェントを起動

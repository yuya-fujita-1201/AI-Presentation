# AI Engineering 03–05 シリーズ統一 loop-log

## セットアップ（2026-08-18）

- 対象: `decks/03-harness-engineering/`、`decks/04-loop-engineering/`、`decks/05-graph-engineering/`
- 読み取り専用の基準: `decks/01-prompt-engineering/`、`decks/02-context-engineering/`
- 作業ブランチ: 既存の `loop/ge-deck-review`
- rubric: `docs/ai-eng-series-03-05-rubric.md`（主観6項目、各9点以上）
- 自動マージ: 許可なし。実施しない
- 機械ゲート: 3デッキの build、preview、`pipeline/bin/gate_deck.sh`、`tools/verify_ai_eng_series.py`、OKF検証、unzip、python-pptx再パース、枚数一致、PPTX notes 0、プレースホルダー・参照切れ検査
- graph-engineering: 03、04、05を所有パスで分離して並列制作。合流後に機械ゲートと独立Verifierを実行する
- 迂回路: Verifierまたは機械ゲートで不合格になったデッキを元担当へ最大2回差し戻す。同じ問題が2回再発した場合のみblockedとして記録する

## 実装結果

- 01/02から共通仕様を抽出: `warm-terracotta`、01の `layout_overrides`、導入4枚の順序、入れ子型5層地図
- Claude Code版graph-engineering skillをCodex native subagents用に `~/.codex/skills/graph-engineering/` へ移植し、validator合格を確認
- 03、04、05を所有パスで分けて並列修正し、03=66枚、04=55枚、05=48枚を維持
- 3本とも導入を「表紙→5層地図→学べること→章扉」に統一
- S2は同じ5項目、同じ短い副説明、同じ免責、同じ入れ子構造に統一。違いは03=ハーネス、04=ループ、05=グラフの強調だけ
- 05の紫系配色を暖色へ変更。参照中のPNG 16枚は ImageGen で暖色版 `warm-ge-*.png` を新規生成し、元の `fig-ge-*.png` は温存
- 05の図解SVG 12枚を暖色へ変更し、旧紫トークンと紫優勢の参照画像が0件であることを機械検証

## loop-engineering 採点

制作担当とは別のcontent/visual reviewerが、01/02を基準に03〜05の全スライドを採点した。ベースラインは両者の低い点を採用した。

| 項目 | ベースライン | 最終 | 主な修正 |
|---|---:|---:|---|
| シリーズの第一印象 | 8.0 | 9.5 | 04/05表紙のシリーズ番号・日付フッターを01〜03と同形式へ統一 |
| 5層地図の統一 | 8.0 | 10.0 | 03〜05の主ラベル、副説明、左欄コピー、免責を共通化 |
| 導入の理解順 | 9.0 | 9.0 | 初回から合格、変更なし |
| 全編の視覚的な整い | 7.5 | 9.2 | 05のcaption競合8枚とS43切れ、04の章扉孤立改行を修正 |
| 図解と本文の協調 | 8.0 | 9.0 | captionを結論帯の下へ分離し、図の補足として読める位置へ移動 |
| 内容を保った自然な流れ | 9.0 | 9.0 | 初回から合格、専門情報を削らず維持 |

### 周回

1. 項目2を修正。8.0→10.0で合格
2. 項目4を修正。7.5→9.2、同時に項目5も8.0→9.0で合格
3. 項目1を修正。8.0→9.5で合格
4. 全6項目が9点以上になったため停止

## 最終機械ゲート

- `gate_deck.sh`: 03=`OK: 66 slides`、04=`OK: 55 slides`、05=`OK: 48 slides`
- `tools/verify_ai_eng_series.py`: 3本ともOK。theme、01 layout一致、導入順、S2共通コピー/副説明/強調、参照アセット、紫検出、PPTX、previewを検査
- `tools/validate_okf.py knowledge`: errors 0、warnings 0
- `python3 -m unittest tools.test_build_deck_links`: 1 test OK
- 全参照SVG: `xmllint --noout` OK
- 3 PPTX: `unzip -t` OK
- scoped `git diff --check`: OK
- 01/02 `deck.json` は作業開始時のSHAを維持: 01=`a3cf6449...`、02=`8d7f6b0f...`
- 最終PPTX SHA: 03=`d94fa3d2...`、04=`10919b34...`、05=`6cfbfe02...`
- 独立PPTX全169枚レンダリング検証: 169 passed / 0 failed
  - LibreOffice 26.2.5.2で3本をPDF化し、pdftoppm 26.08.0で1921×1080 PNGへ変換して全ページ目視
  - 03=66/66、04=55/55、05=48/48。notes 0、スライド外要素0、PPTX画像の非ゼロcrop 0
  - 重点スライドと05の暖色画像16枚も切れ・重なり・欠落なし
  - 非ブロッキング注記: 05 S26の `warm-ge-12.png` は原画内の右端矢印が画像端へ接するが、PPTX側cropは0で原画を100%表示
  - 検証用変換物は `/tmp/series-pptx-final.lPGrkO/` のみに生成

## Git境界

- コミット、push、PR、自動マージは実施していない
- 共有作業ツリーに依頼前からの変更があり、03では今回の変更と既存変更が同じ `deck.json` に重なるため、無関係な差分を混ぜないことを優先した

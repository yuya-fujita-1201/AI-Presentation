# AGENTS.md — presentation プロジェクト（Codex / AI エージェント向け）

社内勉強会資料のプロジェクト。**ナレッジは OKF (Open Knowledge Format) バンドル、スライドは deck.json のパラメーター駆動**で管理している。

## ナレッジの参照方法（最初にここから）

- エントリーポイントは `knowledge/index.md`（OKF v0.2 準拠バンドル）。各ファイルの frontmatter の `description` を見て、必要なファイルだけ開くこと（全ファイルを読む必要はない）
- OKF そのものの仕様・書き方: `knowledge/okf/index.md` から辿る
- スライド作成システムの考え方・微修正手順: `knowledge/slide-system/index.md` から辿る
- 収集済み資料の台帳: `knowledge/sources/index.md`

## スライドの作成・編集ルール

- ソース・オブ・トゥルースは `decks/<デッキ名>/deck.json` のみ。`build/` 配下は生成物なので**直接編集禁止**
- スキーマの正: `docs/deck-schema.md`。仮想キャンバス 1280×720px（16:9）、色はテーマトークン指定
- デザインの微修正は、スライドを作り直さず該当スライドの `style` に差分だけ書く
- 画像は `decks/<デッキ名>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **図解を使うスライドは原則 `image_text` タイプを使う**（見出し＋パンチライン＋本文＋図を1枚に統合。画像だけのページと文章だけのページに分けない）。`image` タイプは全面図が主役の場合のみ
- **PPTX にスピーカーノートを入れない**（`notes` フィールドは HTML 専用。ビルダーが自動で処理するので deck.json に書くのは OK）
- ビルド・検証まで含めて、作業したエージェントが自分で完結させる（手順は次節）

## ビルド・検証手順（作業したエージェント自身が完結させる）

前提: 以下のコマンドは **Mac ローカルで実行する**。Codex はローカルの CLI セッション（workspace-write）なら実行可能。クラウドサンドボックス実行時は python-pptx / Playwright / 生成画像の目視ができないため、その場合のみビルド・検証をユーザーまたは Claude Code に引き継ぐ。python3 は `/opt/homebrew/bin/python3`（python-pptx / Playwright 導入済み）。

1. ビルド: `python3 tools/build_deck.py decks/<デッキ名>`（HTML と PPTX を `build/` に生成）
2. プレビュー: `python3 tools/preview_deck.py decks/<デッキ名>` で全スライドを PNG 化（`build/preview/slide-NN.png`）。画像を実際に開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を目視確認する
3. 修正: 問題があれば deck.json の該当スライドの `style` に差分だけ書いて再ビルドし、`python3 tools/preview_deck.py decks/<デッキ名> <番号>` で該当スライドのみ再確認する
4. PPTX 検証（必須）:
   - `unzip -t decks/<デッキ名>/build/<デッキ名>.pptx` がエラーなし
   - python-pptx の `Presentation()` で再パースでき、スライド数が deck.json と一致
   - 全スライドで `has_notes_slide` が False（スピーカーノート混入は Keynote 互換性を破壊する）

## knowledge/ への書き込みルール

- OKF 形式厳守: 非予約ファイルは frontmatter に `type` 必須、日時は `generated: { by, at }`（`timestamp` は使わない）、リンクは相対パス
- Codex が書く場合の actor 表記: `by: codex/<モデル名>`（例: `codex/gpt-5.3-codex`）
- ファイルを追加・変更したら、該当ディレクトリの `index.md` と バンドル直下の `log.md` を更新する

## 依頼中のタスク

- **OKF ビジュアルガイド v2 の挿絵制作**（2026-08-09 依頼）: 指示書は `docs/codex-brief-okf-visual-v2.md`。`decks/07-okf-visual-guide/`（35枚、deck.json は完成済み）の挿絵19枚を **4:3・文字なし・紫系フラットベクター**で ImageGen 生成し、`assets/` に上書き → ビルド・全35枚の目視・PPTX 3点検証まで完結させる。旧版 `decks/_archive/okf/03-okf-visual/` は**変更禁止（温存）**

## 完了済みタスク

- **デッキ正本の番号整理と旧グラフ版のアーカイブ**（2026-08-20 完了）: 現行正本を `decks/01-*`〜`decks/07-*` に整理。旧グラフ2版は `decks/_archive/graph-engineering/` に退避し、現行正本は `decks/05-graph-engineering/`
- **PE超入門デッキ（改訂版）の挿絵差し替え・最終チェック・正本整理**（2026-08-14 完了）: 現在の正本は `decks/01-prompt-engineering/`（現行53枚）。旧たたき台と不採用の自動生成35枚版は `decks/_archive/ai-eng-01/` に退避済み。最新版の判定は `decks/README.md` を参照
- **OKF ビジュアルデッキの作成**（2026-08-06 完了）: `docs/codex-brief-okf-visual-deck.md`。deck.json＋画像8枚の作成、HTML/PPTX ビルド、全21枚の目視検証・PPTX 検証まで完了

# AGENTS.md — AI-Presentation（Codex / AI エージェント向け）

JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み。**スライドは `deck.json` のパラメーター駆動**で管理する。全体像は `README.md`、スキーマは `docs/deck-schema.md`。

## 最初に読む場所

- 仕組みの使い方: `README.md`
- deck.json のスキーマ（正）: `docs/deck-schema.md`
- 全スライドタイプの見本: `decks/10-template-sample/deck.json`

## スライドの作成・編集ルール

- ソース・オブ・トゥルースは `decks/<デッキ名>/deck.json` のみ。`build/` 配下は生成物なので**直接編集禁止**
- スキーマの正: `docs/deck-schema.md`。仮想キャンバス 1280×720px（16:9）、色はテーマトークン指定
- デザインの微修正は、スライドを作り直さず該当スライドの `style` に差分だけ書く
- 画像は `decks/<デッキ名>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **図解を使うスライドは原則 `image_text` タイプを使う**（見出し＋パンチライン＋本文＋図を1枚に統合。画像だけのページと文章だけのページに分けない）。`image` タイプは全面図が主役の場合のみ
- **PPTX にスピーカーノートを入れない**（`notes` フィールドは HTML 専用。ビルダーが自動で処理するので deck.json に書くのは OK）
- ビルド・検証まで含めて、作業したエージェントが自分で完結させる（手順は次節）

## ビルド・検証手順（作業したエージェント自身が完結させる）

前提: **Python 3 + python-pptx** が必要（プレビューPNGは Playwright、一覧シートは Pillow）。ローカル CLI セッションで実行する。クラウドサンドボックスなど python-pptx / Playwright / 生成画像の目視ができない環境では、ビルド・検証をユーザーまたはローカルのエージェントに引き継ぐ。

1. ビルド: `python tools/build_deck.py decks/<デッキ名>`（HTML と PPTX を `build/` に生成。環境により `python3`）
2. プレビュー: `python tools/preview_deck.py decks/<デッキ名>` で全スライドを PNG 化（`build/preview/slide-NN.png`）。画像を実際に開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を目視確認する
3. 修正: 問題があれば deck.json の該当スライドの `style` に差分だけ書いて再ビルドし、`python tools/preview_deck.py decks/<デッキ名> <番号>` で該当スライドのみ再確認する
4. PPTX 検証（必須）:
   - zip 整合（`unzip -t decks/<デッキ名>/build/<meta.id>.pptx` 等）がエラーなし
   - python-pptx の `Presentation()` で再パースでき、スライド数が想定と一致
   - 全スライドで `has_notes_slide` が False（スピーカーノート混入は Keynote 互換性を破壊する）

# AGENTS.md — AI-Presentation（Codex / AI エージェント向け）

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布するマーケットプレイス。**スライドは `deck.json` のパラメーター駆動**で管理する。全体像は `README.md`、プラグインの中身は `plugins/slide-deck/README.md`。

## 最初に読む場所

- リポジトリ構成: `README.md`
- プラグインの使い方: `plugins/slide-deck/README.md`
- deck.json のスキーマ（正）: `plugins/slide-deck/references/deck-schema.md`
- テーマ（配色・フォント）: `plugins/slide-deck/references/themes.md`
- 全スライドタイプの見本: `plugins/slide-deck/examples/template-sample/deck.json`

## スライドの作成・編集ルール

- ソース・オブ・トゥルースは `<deck_dir>/deck.json` のみ。`build/` 配下は生成物なので**直接編集禁止**
- スキーマの正: `plugins/slide-deck/references/deck-schema.md`。仮想キャンバス 1280×720px（16:9）、色はテーマトークン指定
- デザインの微修正は、スライドを作り直さず該当スライドの `style` に差分だけ書く
- 画像は `<deck_dir>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **図解はまずネイティブ図解タイプ（`steps` / `swimlane` / `matrix` / `cards` / `architecture` / `dataflow` / `lifecycle` / `sequence`）で表現できないか検討する**。それで表現できない図版（スクリーンショット・既存資料の図表）だけ `image` / `image_text` を使う。画像はユーザー提供 → 既存 `assets/` の流用 → 無ければ簡単な SVG を自作、の順で用意する。`image_text` は見出し＋パンチライン＋本文＋図を1枚に統合したいとき、`image` タイプは全面図が主役の場合に使う
- **PPTX にスピーカーノートを入れない**（`notes` フィールドは HTML 専用。ビルダーが自動処理するので deck.json に書くのは OK）
- ビルド・検証まで含めて、作業したエージェントが自分で完結させる（手順は次節）

## ビルド・検証手順（作業したエージェント自身が完結させる）

前提: **Python 3.9 以上 + python-pptx** が必要（プレビューPNGは Playwright、一覧シートは Pillow、PDF抽出は pymupdf）。初回は `python plugins/slide-deck/tools/setup_deps.py`（または `pip install -r plugins/slide-deck/requirements.txt`）で導入。ローカル CLI セッションで実行する。クラウドサンドボックスなど python-pptx / Playwright / 生成画像の目視ができない環境では、ビルド・検証をローカルのエージェントに引き継ぐ。

1. ビルド: `python plugins/slide-deck/tools/build_deck.py <deck_dir>`（HTML と PPTX を `build/` に生成。環境により `python3`、Windows で見つからなければ `py -3`）
2. 機械チェック（必須）: `python plugins/slide-deck/tools/check_layout.py <deck_dir>`（はみ出し・重なり・文字あふれ）と `python plugins/slide-deck/tools/lint_deck_text.py <deck_dir>`（文字量・AI定型句）を実行し、exit 1 なら報告に沿って deck.json を直して再ビルドする。`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane` を使った場合は `python plugins/slide-deck/tools/check_diagram.py <deck_dir>`（配線・ラベルの座標診断）も実行する
3. プレビュー: `python plugins/slide-deck/tools/preview_deck.py <deck_dir>` で全スライドを PNG 化。画像を実際に開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を目視確認する（Playwright が使えない環境では `export_pdf.py` や `soffice --headless --convert-to png` で代替する）
4. 修正: 問題があれば deck.json の該当スライドの `style` に差分だけ書いて再ビルドし、`preview_deck.py <deck_dir> <番号>` で該当スライドのみ再確認する
5. PPTX 検証（必須）:
   - zip 整合（`unzip -t <deck_dir>/build/<meta.id>.pptx` 等）がエラーなし
   - python-pptx の `Presentation()` で再パースでき、スライド数が想定と一致
   - 全スライドで `has_notes_slide` が False（スピーカーノート混入は Keynote 互換性を破壊する）

## テーマの追加

- 雛形: `python plugins/slide-deck/tools/new_theme.py <name>`（kebab-case）
- テーマは `default` をベースにマージされ、明示していないトークンは自動導出されるので上書きしたいトークンだけ書けばよい。トークンの意味は `plugins/slide-deck/references/themes.md`
- 新テーマを作ったら `python plugins/slide-deck/tools/check_theme.py <name>` でコントラストを確認する

## プラグインを編集したら（機械チェック）

- ユニットテスト: `python -m unittest discover -s plugins/slide-deck/tools -p "test_*.py"` を実行し全て通ることを確認する
- 表リンク機能（`is_http_url` / `table_cell_parts` 等）を変更した場合は `python -m unittest plugins/slide-deck/tools/test_build_deck_links.py` を個別に実行する
- 見本デッキ（`examples/template-sample`）と `manual` がエラーなくビルドできることを確認する
- 機能追加・修正を行ったら `plugins/slide-deck/.claude-plugin/plugin.json` と `.claude-plugin/marketplace.json` の `version`（semver）を bump する

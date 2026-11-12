# AGENTS.md — AI-Presentation（Codex / AI エージェント向け）

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布するマーケットプレイス。**スライドは `deck.json` のパラメーター駆動**で管理する。全体像は `README.md`、プラグインの中身は `plugins/slide-deck/README.md`。

## 最初に読む場所

- リポジトリ構成: `README.md`
- プラグインの使い方・3.0.0 の変更点・既知の制約: `plugins/slide-deck/README.md`
- deck.json のスキーマ（正）: `plugins/slide-deck/references/deck-schema.md`（索引）と、その表から使うタイプだけ読む `plugins/slide-deck/references/schema/*.md`
- テーマ（配色・フォント）と形（shape）: `plugins/slide-deck/references/themes.md`
- ストーリーの型・1枚のルール: `plugins/slide-deck/references/content-guide.md`
- 主要なタイプの見本（1 本の提案デッキ）: `plugins/slide-deck/examples/template-sample/deck.json`、形（shape）の比較: `plugins/slide-deck/examples/shape-gallery/`
- 登録済みの構図（型）の一覧: `python plugins/slide-deck/tools/pattern_engine.py list`

## スライドの作成・編集ルール

- ソース・オブ・トゥルースは `<deck_dir>/deck.json` のみ。`build/` 配下は生成物なので**直接編集禁止**
- スキーマの正: `plugins/slide-deck/references/deck-schema.md`。仮想キャンバス 1280×720px（16:9）、色はテーマトークン指定
- 新規作成は 材料 → 骨子（`outline.md`）→ 承認 1 回 → deck.json → ビルド → 検査と目視の順（手順は `plugins/slide-deck/skills/create-deck/SKILL.md`）。設定フォームは既定では出さず、利用者が選びたいと言ったときだけ（`skills/create-deck/settings-form.md`）
- 材料に無い数字・固有名詞・日付は作らず、`【要確認: 何を確かめるか】` と書く（ビルドが HTML / PPTX で強調し、`lint_deck_text.py` が一覧にする）。引き渡しで件数と一覧を報告する
- デザインの微修正は、スライドを作り直さず該当スライドの `style` に差分だけ書く。文字量に合わせた調整は自動フィットと `meta.density`（`talk` / `standard` / `read`）に任せ、内容に合わせて `style` で手詰めしない（警告はまず内容、次に密度、最後に `style` の順で直す）。`style` / `meta.layout_overrides` に書いた値は自動フィットも密度も動かさない。止めるのは `meta.autofit: false` かスライドの `autofit: false`
- 画像は `<deck_dir>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **図解はまずネイティブ図解タイプ（`steps` / `swimlane` / `matrix` / `cards` / `architecture` / `dataflow` / `lifecycle` / `sequence` / `schedule`）で表現できないか検討する**。それで表現できない図版（スクリーンショット・既存資料の図表）だけ `image` / `image_text` を使う。画像はユーザー提供 → 既存 `assets/` の流用 → 無ければ簡単な SVG を自作、の順で用意する。`image_text` は見出し＋パンチライン＋本文＋図を1枚に統合したいとき、`image` タイプは全面図が主役の場合に使う
- 同じ構図を使い回すときは `pattern` 型（`pattern_engine.py list` で選ぶ）、1 枚に複数ブロックを置くときは `composite`、主役の数字や一文＋根拠の図表は `split`、数字は `kpi`、グラフは `chart`。`canvas` 型は既存 PPTX の取り込み専用で、新規スライドを手書きしない
- **PPTX にスピーカーノートを入れない**（`notes` フィールドは HTML 専用。ビルダーが自動処理するので deck.json に書くのは OK）
- ビルド・検証まで含めて、作業したエージェントが自分で完結させる（手順は次節）

## ビルド・検証手順（作業したエージェント自身が完結させる）

前提: **Python 3.14 以上 + python-pptx** が必要（プレビューPNGは Playwright、一覧シートと字幅の実測は Pillow、PDF抽出は pymupdf、`export_pdf.py` と `check_pptx.py` は LibreOffice）。初回は `python plugins/slide-deck/tools/setup_deps.py`（または `pip install -r plugins/slide-deck/requirements.txt`）で導入。ローカル CLI セッションで実行する。クラウドサンドボックスなど python-pptx / Playwright / 生成画像の目視ができない環境では、ビルド・検証をローカルのエージェントに引き継ぐ。

1. ビルド: `python plugins/slide-deck/tools/build_deck.py <deck_dir>`（HTML と PPTX を `build/` に生成。環境により `python3`、Windows で見つからなければ `py -3`）。警告と note はここで読む
2. 機械チェック（必須）: `python plugins/slide-deck/tools/check_layout.py <deck_dir>`（はみ出し・重なり・文字あふれ・小さい文字・コントラスト・線の貫通）と `python plugins/slide-deck/tools/lint_deck_text.py <deck_dir>`（文字量・AI定型句・【要確認】の一覧）を実行し、exit 1 なら報告に沿って deck.json を直して再ビルドする。`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane` / `schedule` を使った場合は `python plugins/slide-deck/tools/check_diagram.py <deck_dir>`（配線・ラベルの座標診断）も実行する。プレビュー PNG を全枚作ったら `python plugins/slide-deck/tools/check_visual.py <deck_dir>`（本文の空白帯・似たスライドの連続・古い PNG。警告のみ）も確認する。仕上げに、採点基準 `plugins/slide-deck/agents/deck-evaluator.md` に沿って生成の経緯を持たない別エージェントにプレビュー PNG を採点させ、70点未満のスライドだけ deck.json で直して再採点する（修正は最大3周。手順は `plugins/slide-deck/skills/review-deck/SKILL.md` の8）
3. プレビュー: `python plugins/slide-deck/tools/preview_deck.py <deck_dir>` で全スライドを PNG 化。画像を実際に開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を目視確認する（Playwright が使えない環境では `export_pdf.py` や `soffice --headless --convert-to png` で代替する）
4. 修正: 問題があれば、まず内容（項目数・文の長さ・分割）、次に密度、最後に deck.json の該当スライドの `style` に差分だけ書いて再ビルドし、`preview_deck.py <deck_dir> <番号>` で該当スライドのみ再確認する
5. PPTX 検証（必須）:
   - zip 整合（`unzip -t <deck_dir>/build/<meta.id>.pptx` 等）がエラーなし
   - python-pptx の `Presentation()` で再パースでき、スライド数が想定と一致
   - 全スライドで `has_notes_slide` が False（スピーカーノート混入は Keynote 互換性を破壊する）
   - 上の 3 点と XML の整形式・文書プロパティは `python plugins/slide-deck/tools/verify_pptx.py <deck_dir>/build/<meta.id>.pptx` でまとめて検査できる（`build_deck.py` も保存直後に自動で行う）
6. 見た目の比較（任意）: `python plugins/slide-deck/tools/check_pptx.py <deck_dir>` が LibreOffice で PPTX を描き、HTML プレビューと 1 枚ずつ比べて差の大きい順に報告する（`build/pptx-compare/cmp-NN.png`）。参考値であり、PowerPoint 実機で確認したことにはならない。確かめていないことは報告に「未確認」と書く

## テーマの追加

- 雛形: `python plugins/slide-deck/tools/new_theme.py <name>`（kebab-case。`--shape soft` などで形も持たせられる）
- テーマは `default` をベースにマージされ、明示していないトークンは自動導出されるので上書きしたいトークンだけ書けばよい。トークンの意味は `plugins/slide-deck/references/themes.md`
- 新テーマを作ったら `python plugins/slide-deck/tools/check_theme.py <name>` でコントラストを確認する（形の一覧と検証は `check_theme.py --shapes`）
- 探索順（テーマ・レイアウト・型・形で共通。先に見つかったものが勝つ）: 環境変数（`SLIDE_DECK_THEMES` / `SLIDE_DECK_LAYOUTS` / `SLIDE_DECK_PATTERNS` / `SLIDE_DECK_SHAPES`）→ `<deck_dir>/<themes|layouts|patterns|shapes>/` → デッキの親（3 階層上まで）の同名フォルダ → カレントディレクトリの同名フォルダ → 同梱 `templates/`

## プラグインを編集したら（機械チェック）

- ユニットテスト: `python -m unittest discover -s plugins/slide-deck/tools -p "test_*.py"` を実行し全て通ることを確認する（2026-11-12 時点で 1502 件。回したあと `plugins/slide-deck/tools/__pycache__` を消す）
- 表リンク機能（`is_http_url` / `table_cell_parts` 等）を変更した場合は `python -m unittest plugins/slide-deck/tools/test_build_deck_links.py` を個別に実行する
- 見本デッキ（`examples/template-sample`）と `manual` がエラーなく（警告 0 で）ビルドでき、`verify_pptx.py` が OK で、見本の `check_layout.py` が不合格 0 であることを確認する。`build/` `__pycache__` 等をリポジトリに残さない（リポジトリの外のコピーでビルドしてもよい）
- 見た目に関わる変更（レイアウト・フィット・描画・テーマ・shape）は、変更前のコピーと変更後で見本・manual・実デッキを同じ条件でビルドして比べ、変わったスライドを 1 枚ずつ目で見て「意図した変化だけ」を確認する。何も指定しないデッキの見た目は変えない。PPTX は LibreOffice の画素比較（代替フォントが実行ごとに変わることがある）ではなく、スライド XML の比較で確かめる
- `claude plugin validate ./plugins/slide-deck` と `claude plugin validate .` が通ることを確認する（プラグインの README に marketplace からのインストール行が無い、という助言は出る。配布経路に関わるので勝手に足さない）
- 機能追加・修正を行ったら `plugins/slide-deck/.claude-plugin/plugin.json`・`.claude-plugin/marketplace.json`（先頭と `plugins[]` の 2 か所）・`plugins/slide-deck/pyproject.toml`・`plugins/slide-deck/uv.lock`（`name = "slide-deck"` の行）の `version`（semver）をすべて同じ値に bump する。取り残しは `grep -rn "<旧バージョン>"` で確かめる。既存デッキをビルドし直すと変わることは `plugins/slide-deck/README.md` の「N.N.N の変更点」に書く
- 配布用の `slide-deck.zip`（リポジトリ直下）は `python3 scripts/build_zip.py` で作り直す（git が追跡している `plugins/slide-deck/` 以下だけを入れる。変更を `git add` してから実行する）。同梱の `extension-doctor-report.json` は社内 Hub の extension-doctor の出力で、このリポジトリの道具では作り直せない（診断を取り直したらファイルを差し替えて zip を作り直す）
- タスク完了時は該当デッキの deck.json の `meta.date` を更新する

## タイプを足す手順

レイアウト関数が canvas 要素列を返し、`canvas_engine` が HTML と PPTX の両方を描く作法で足す（HTML と PPTX を別々に手書きしない）。

1. エンジンのモジュールにレイアウト関数と検証関数を書き、末尾で `engine_registry.register("名前", layout, validate, slide_keys=…)` を呼ぶ（引数の意味は `tools/engine_registry.py` の docstring）。登録表を使わないタイプは `deck_schema.SLIDE_KEYS`・`build_deck.RENDERED_TYPES`・HTML / PPTX の描画の分岐に足す
2. `templates/layouts/default.json` の `types` に領域を足す。数値は直書きせず既存のトークン（`$type.h1` `$radius.card` …）を参照する。足りないトークンは `tokens` に classic の見た目が変わらない値で足す
3. `tools/deck_schema.py` の既知キー・値の形、自動フィット（`autofit.py` の `@fitter`）、lint・`check_visual` の扱い
4. 文書: `references/deck-schema.md` の「タイプ一覧表」に 1 行、`references/schema/` に仕様、`skills/create-deck/SKILL.md` の「タイプの選び方」
5. 見本 `examples/template-sample/deck.json` に 1 枚足し、見本の枚数に依存するテスト（`test_build_deck.py`）を直す
6. 単体テストを足し、3 つの density・4 つの shape・2 つのテーマ（`default` / `acn-slide-master`）でビルドして `check_layout.py` と目視。回帰で既存デッキが変わっていないこと

## 型（パターン）を足す手順

- 同梱は `plugins/slide-deck/templates/patterns/<名前>.json`、利用者の自作は `<deck_dir>/patterns/` など（上の探索順）。既存の型 JSON をコピーして直すか、PPTX の 1 枚から `pattern_from_pptx.py` で起こす
- スロット（必須・個数・`max_chars`・例）、枠（`full` / `body`）、狭い構図（`narrow`）を持たせ、色はテーマトークンで書く。`python plugins/slide-deck/tools/pattern_engine.py check <ファイル>` がエラー 0・警告 0
- `pattern_engine.py preview --out <フォルダ>` で全型を並べてビルドし、4 shape × 2 テーマで `check_layout.py` が不合格 0・警告 0、目視で崩れが無いこと。合成スライド・`split` のブロックに置く型は半幅・3 分の 2 幅でも確認する
- 同梱の型を増減したら、型の個数に依存するテスト（`test_pattern_library.py` など）と文書（`references/schema/pattern.md`、`skills/create-deck/SKILL.md`、プラグインの README）を直す

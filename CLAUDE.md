# AI-Presentation プロジェクト作業ルール

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布するマーケットプレイス。全体像は `README.md`、プラグインの中身は `plugins/slide-deck/README.md`。

他エージェント（Codex 等）向けの入口は `AGENTS.md`（本ファイルは Claude Code 専用）。

## リポジトリの構造

- マーケットプレイス定義: `.claude-plugin/marketplace.json`
- プラグイン本体（自己完結）: `plugins/slide-deck/`
  - `skills/`（create-deck とその補助ファイル / add-theme / review-deck / export-pdf / setup）、`agents/`（deck-evaluator: review-deck が呼ぶ評価エージェント）、`tools/`、`templates/`（themes / layouts / shapes / patterns / icons）、`references/`（索引 `deck-schema.md` ＋ `schema/` にタイプ別の仕様）、`examples/`、`manual/`
  - Python 依存: `pyproject.toml` + `uv.lock`（Python 3.14 以上）、`requirements.txt`
- スクリプトは `plugins/slide-deck/tools/` にあり、テンプレートを `plugins/slide-deck/templates/` から解決する（`ROOT = tools の親 = plugins/slide-deck/`）

## デッキ作成のルール

- スライドの内容・デザインはすべて `deck.json` のパラメーターで管理。スキーマの索引は `plugins/slide-deck/references/deck-schema.md`（タイプ別の仕様は `references/schema/` から、使うタイプのファイルだけ読む）
- ビルド: `python plugins/slide-deck/tools/build_deck.py <deck_dir>`（環境により `python3`。python-pptx 導入必須）
- 見本は `plugins/slide-deck/examples/template-sample/`。新規デッキはこれをコピーして書き換えるのが早い（形の比較は `examples/shape-gallery/`）
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- 画像は `<deck_dir>/assets/` に置き、`image` / `image_text` タイプの `path` で相対参照する（PNG / JPG / SVG 対応）
- **微修正の依頼（位置・サイズ・フォント・色の変更）が来たら、スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`、全デッキ共通なら `plugins/slide-deck/templates/layouts/default.json`
- 文字量に合わせた調整は自動フィット（`tools/autofit.py`）と `meta.density`（`talk` / `standard` / `read`）が行う。内容に合わせて `style` で位置や大きさを手詰めしない（警告はまず内容、次に密度、最後に `style` の順で直す）。`style` / `meta.layout_overrides` に書いた値は自動フィットも密度も動かさない。自動フィットを止めるのは `meta.autofit: false` かスライドの `autofit: false`
- 微修正後は `build_deck.py <deck_dir> --html` → `preview_deck.py <deck_dir> <番号>` で該当スライドだけ目視確認してから PPTX を再生成する
- ビルド前後の機械チェックとして `check_layout.py <deck_dir>`（はみ出し・重なり・文字あふれ・小さい文字・コントラスト・線の貫通）と `lint_deck_text.py <deck_dir>`（文字量・AI定型句・【要確認】の一覧）を通す（`create-deck` スキルの `checks.md`、または `review-deck` スキルでまとめて実行できる）。図解タイプ（`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane` / `schedule`）を使ったら `check_diagram.py <deck_dir>`（配線・ラベルの座標診断）も通す。プレビュー PNG を全枚作ったら `check_visual.py <deck_dir>`（本文の空白帯・似たスライドの連続・古い PNG。警告のみ）も確認する。PPTX は `verify_pptx.py`（下記）、HTML との見た目の差は `check_pptx.py <deck_dir>`（LibreOffice の描画。警告のみで、PowerPoint 実機の代わりにはならない）。仕上げの品質確認は `review-deck` スキルの手順8（評価エージェント `deck-evaluator` の採点 → fail のスライドだけ deck.json で直す → 再採点、修正は最大3周）で行う
- 新規デッキ作成は 材料 → 骨子（`outline.md`）→ 承認 1 回 → deck.json → ビルド → 検査と目視 → 引き渡し（`create-deck` スキル）。設定フォーム（`build_settings_widget.py` → show_widget）は既定では出さず、利用者が選びたいと言ったときだけ出す（`skills/create-deck/settings-form.md`）。「仕上げの度合い」は既定がドラフト（機械チェックだけ）で、ユーザーが「仕上げて」と言ったときだけ評価ループ（修正は最大3周）を回す
- 材料に無い数字・固有名詞・日付は作らず、`【要確認: 何を確かめるか】` と書く。ビルドが HTML / PPTX の両方で強調し、`lint_deck_text.py` が一覧にする。引き渡しで件数と一覧を報告する
- 色は hex 直書きせずテーマトークン（`primary` / `accent` 等）で指定。テーマ変更は `meta.theme` の切替のみ（同梱: `default` / `accenture` / `acn-slide-master` / `acn-technology-graphik`。旧名 `accenture-purple` は `acn-slide-master` の別名として読める）。角丸・罫線・影の形は `meta.shape`（`classic` / `sharp` / `soft` / `editorial`）。例外は既存 PPTX の取り込み専用 `canvas` 型（`pptx_import.py` が生成し元資料の hex を持つ。新規スライドを canvas で手書きしない。構図の再利用は `pattern` 型）
- **PPTX にスピーカーノートを絶対に入れない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示される
- PPTX 生成後の検証: zip 整合（`unzip -t` 等）と `Presentation()` 再パースの 2 点を必ず実施し、全スライドで `has_notes_slide` が False であることを確認する（`python plugins/slide-deck/tools/verify_pptx.py <deck_dir>/build/<meta.id>.pptx` が 3 点と XML の整形式・文書プロパティをまとめて検査する。`build_deck.py` も保存直後に同じ検証を自動で行う）

## テーマ追加のルール

- テーマは `default` をベースにマージされる。新テーマは上書きしたいトークンだけ書けばよい（`extends` で任意の親も可）
- 雛形は `python plugins/slide-deck/tools/new_theme.py <name>`（`--shape soft` で形も持たせられる）。トークンの意味は `plugins/slide-deck/references/themes.md`。作ったら `python plugins/slide-deck/tools/check_theme.py <name>` でコントラストを確認する
- サンプルスライド（PPTX/HTML/PDF/画像）から生成する場合は `python plugins/slide-deck/tools/theme_from_sample.py <file> --name <name>`（自動推定なので生成後に微調整）
- 探索順（テーマ・レイアウト・型・形で共通。先に見つかったものが勝つ）は 環境変数（`SLIDE_DECK_THEMES` / `SLIDE_DECK_LAYOUTS` / `SLIDE_DECK_PATTERNS` / `SLIDE_DECK_SHAPES`）→ `<deck_dir>/<themes|layouts|patterns|shapes>/` → デッキの親（3 階層上まで）の同名フォルダ → カレントディレクトリの同名フォルダ → 同梱 `templates/`（`tools/deck_paths.py`）

## プラグインを編集したら

- ローカル検証: `claude --plugin-dir ./plugins/slide-deck`、または `/reload-plugins`
- スキルの description は簡潔に（skill 一覧での表示コストになる）。frontmatter は `name` / `description` / `allowed-tools` を基本に、必要なら `argument-hint` / `disable-model-invocation` を使う
- ユニットテスト: `python -m unittest discover -s plugins/slide-deck/tools -p "test_*.py"` を実行し全て通ることを確認する（2026-11-12 時点で 1502 件。回したあと `plugins/slide-deck/tools/__pycache__` を消す）。表リンク機能を変更した場合は `python -m unittest plugins/slide-deck/tools/test_build_deck_links.py` も個別実行
- 見本デッキ（`examples/template-sample`）と `manual` が `build_deck.py` でエラーなく（警告 0 で）ビルドでき、`verify_pptx.py` が OK で、見本の `check_layout.py` が不合格 0 であることを確認してからコミットする。ビルドはリポジトリの外のコピーで行うか、`build/` を残さない（`**/build/` と `__pycache__/` は .gitignore 済み）
- 見た目に関わる変更（レイアウト・フィット・描画・テーマ・shape）は回帰で確かめる: 変更前のコピーと変更後で、見本・manual・実デッキ（style あり／style なし）を同じ条件でビルドし、変わったスライドを 1 枚ずつ目で見て「意図した変化だけ」を確認する。何も指定しないデッキの見た目は変えない。PPTX は LibreOffice の画素比較（代替フォントが実行ごとに変わることがある）ではなく、スライド XML の比較で確かめる。PowerPoint 実機で確かめていないことは「確認した」と書かない
- `claude plugin validate ./plugins/slide-deck` と `claude plugin validate .` が通ることを確認する（プラグインの README に marketplace からのインストール行が無い、という助言は出る。配布経路に関わるので勝手に足さない）

## タイプを足す手順

新しいスライドタイプ（レイアウト関数が canvas 要素列を返し、`canvas_engine` が HTML と PPTX の両方を描く作法。HTML と PPTX を別々に手書きしない）:

1. 実装: エンジンのモジュールにレイアウト関数と検証関数を書き、末尾で `engine_registry.register("名前", layout, validate, slide_keys=…)` を 1 回呼ぶ（`tools/engine_registry.py` の docstring に引数の意味）。登録表の経路を使わないタイプは `deck_schema.SLIDE_KEYS`・`build_deck.RENDERED_TYPES`・`build_deck` の HTML / PPTX の描画の分岐に足す
2. `templates/layouts/default.json` の `types` に領域（見出し骨格と固有の値）を足す。数値は直書きせず既存のトークン（`$type.h1` `$radius.card` `$weight.heading` …）を参照する。足りないトークンは `tokens` に classic の見た目が変わらない値で足す
3. `tools/deck_schema.py` の既知キー・値の形（`SLIDE_KEYS` `SLIDE_SHAPES`）、自動フィット（`@fitter("名前")`）、lint・`check_visual` の扱い（`register` の `sparse_ok` `relation` など）
4. 文書: `references/deck-schema.md` の「タイプ一覧表」に 1 行、`references/schema/` の該当ファイルに仕様、`skills/create-deck/SKILL.md` の「タイプの選び方」、`references/schema/validation.md`（警告・fail の一覧）
5. 見本: `examples/template-sample/deck.json` に 1 枚（見本の枚数に依存するテスト `test_build_deck.py` の期待値も直す）、`manual` の説明
6. テスト: 単体テスト（`tools/test_*.py`）。3 つの density（`talk` / `standard` / `read`）・4 つの shape・2 つのテーマ（`default` / `acn-slide-master`）でビルドして `check_layout.py` と目視。回帰で既存デッキが変わっていないこと
7. バージョンを上げる（下の「変更記録」）

## 型（パターン）を足す手順

- 同梱の型は `plugins/slide-deck/templates/patterns/<名前>.json`（利用者の自作は `<deck_dir>/patterns/` など。上の探索順）。既存の型 JSON をコピーして直すのが早い。PPTX の 1 枚から起こすなら `pattern_from_pptx.py`
- スロット（必須・個数・`max_chars`・例）、枠（`full` 全面 / `body` 本文だけ）、半幅・3 分の 2 幅用の狭い構図（`narrow`）を持たせる。色はテーマトークン。`python plugins/slide-deck/tools/pattern_engine.py check <ファイル>` がエラー 0・警告 0
- `pattern_engine.py preview --out <フォルダ>` で全型を並べてビルドし、4 shape × 2 テーマで `check_layout.py` が不合格 0・警告 0、目視で崩れが無いこと。合成スライド・`split` のブロックに置く型は半幅・3 分の 2 幅でも確認する
- 同梱の型を増減したら、`tools/test_pattern_library.py` など型の個数に依存するテストと、文書（`references/schema/pattern.md` の同梱一覧、`skills/create-deck/SKILL.md` の「型の引き方」）、プラグインの README の個数を直す

## 変更記録

- タスク完了時は該当デッキの deck.json の `meta.date` を更新する
- **プラグインの機能を変えたら（`tools/` `templates/` `skills/` 等 `plugin.json` 以外のファイルを変更したら）必ず `plugin.json` / `marketplace.json` の `version` を semver で bump する**（このルールを守らなかった実績があるため、コミット前に diff を見て徹底する）
- バージョンを上げる場所（すべて同じ値にそろえる）: `plugins/slide-deck/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`（先頭の `version` と `plugins[]` の `slide-deck` の `version` の 2 か所）、`plugins/slide-deck/pyproject.toml`、`plugins/slide-deck/uv.lock` の `name = "slide-deck"` の行の `version`。上げたら `grep -rn "<旧バージョン>"` で取り残しを確かめる（`plugins/slide-deck/README.md` の変更点の節の言及は除く）。利用者に見える変更と、既存デッキをビルドし直すと変わることは `plugins/slide-deck/README.md` の「N.N.N の変更点」に書く
- 配布用の `slide-deck.zip`（リポジトリ直下）は `python3 scripts/build_zip.py` で作り直す（git が追跡している `plugins/slide-deck/` 以下だけを入れる。変更を `git add` してから実行する）。同梱の `extension-doctor-report.json` は社内 Hub の extension-doctor の出力で、このリポジトリの道具では作り直せない（診断を取り直したらファイルを差し替えて zip を作り直す）

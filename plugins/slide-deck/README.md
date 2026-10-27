# slide-deck プラグイン

JSON（`deck.json`）をソースにして、スライドを **HTML / PowerPoint(16:9)** にビルドする Claude Code プラグイン。
スライドの**内容もデザインもすべて deck.json のパラメーター**で管理し、色はテーマトークンで切替・追加できる。

> 📖 **使い方のスライド版マニュアル**: [`USER-GUIDE.html`](USER-GUIDE.html)（ブラウザで開く。← / → で移動）。この README は概要、USER-GUIDE はダウンロードした人向けの操作マニュアル。ソースは [`manual/deck.json`](manual/deck.json)（本プラグイン自身でビルド）。

社内配布物です。受領者内での利用を想定しており、社外への再配布は想定していません。

## インストール

社内配布は **`slide-deck` フォルダの Zip を受け取って展開**する形式（マーケットプレイスからのダウンロードではない）。配布された Zip を任意の場所に展開し、出てきた `slide-deck` フォルダを指定して Claude Code を起動する:

```
claude --plugin-dir <展開先>/slide-deck
```

（IDE 拡張を使う場合は設定でプラグインフォルダを指定する）

## 初回セットアップ（依存関係）

**Python 3.14 以上が必要**。依存の導入は `/slide-deck:setup` から Claude Code 経由で行うのが最も簡単（内部で下記スクリプトを呼ぶだけ）。この README のとおりターミナルから自分で叩く場合は次節の注意を参照。

```
/slide-deck:setup            # 必須(python-pptx)
/slide-deck:setup --playwright  # プレビューPNGも使う場合（playwright + chromium）
```
このリポジトリ内で直接叩く場合は `requirements.txt` からもインストールできる: `pip install -r plugins/slide-deck/requirements.txt`。

| パッケージ | 要否 | 用途 |
|---|---|---|
| `python-pptx` | 必須 | PPTX 生成 |
| `playwright`(+chromium) | 任意 | プレビューPNG生成 |
| `pillow` | 任意 | 一覧シート生成・画像からのテーマ抽出 |
| `pymupdf` | 任意 | PDF からのテーマ抽出 |

### Windows の注意
- `python` が Microsoft Store を開く場合は Python 未インストール（[python.org](https://www.python.org/) から導入）。導入後も見つからなければ `py -3` を使う
- コマンドは PowerShell / Git Bash のどちらでも同じもので動く

## 使い方（スキル）

| スキル | 用途 |
|---|---|
| `/slide-deck:create-deck` | deck.json からスライドを新規作成・編集・ビルド |
| `/slide-deck:add-theme` | 新しいテーマ（配色・フォント）を追加・切替 |
| `/slide-deck:review-deck` | 既存デッキを一括レビュー（機械チェック＋評価エージェント `deck-evaluator` の採点と fail スライドの修正ループ） |
| `/slide-deck:export-pdf` | ビルド済み PPTX を PDF に書き出す |
| `/slide-deck:setup` | 依存関係の初回セットアップ |

スライド作成を頼めば `create-deck` が自動で選ばれる。手動なら上記コマンドで明示的に呼べる。

## 手動で使う（スキルを介さず）

> **注意**: `${CLAUDE_PLUGIN_ROOT}` は Claude Code がスキル本文（SKILL.md）を実行するときにだけ内部で実パスへ置換する専用トークンで、PowerShell や Git Bash を素で開いて手入力しても定義されない（未定義変数として空文字に展開され、`python "/tools/xxx.py"` のような誤ったパスになって失敗する）。ここから先のコマンドは Claude Code のスキル実行を介さずターミナルから直接叩く想定なので、`${CLAUDE_PLUGIN_ROOT}` の代わりに **このプラグインのディレクトリへ `cd` してから相対パスで実行する**。このリポジトリを clone している場合はそのディレクトリが `plugins/slide-deck/`。配布 Zip を展開して使っている場合は展開先の `slide-deck/` ディレクトリに読み替える。

```bash
cd path/to/plugins/slide-deck   # このプラグインのディレクトリに移動（例: このリポジトリなら plugins/slide-deck）

# ビルド（HTML + PPTX）
python tools/build_deck.py <deck_dir>
# プレビューPNG
python tools/preview_deck.py <deck_dir> [番号...]
# 構造チェック（はみ出し・重なり・文字あふれ）
python tools/check_layout.py <deck_dir>
# 図解タイプの配線・ラベル診断（architecture/dataflow/lifecycle/sequence/swimlane/schedule）
python tools/check_diagram.py <deck_dir>
# SVG図版のフォント機械チェック（明朝体等へのフォールバックを検出）
python tools/check_svg_fonts.py <deck_dir>
# 文言チェック（文字量・AI定型句・主張の書き方・日付の整合など）
python tools/lint_deck_text.py <deck_dir>
# 見た目の偏り（下1/3の空白・直前と似たスライドの連続。要 pillow・preview_deck の PNG）
python tools/check_visual.py <deck_dir>
# 新規作成の設定フォーム（Claude の show_widget 用 HTML）
python tools/build_settings_widget.py --out deck_widget.html
# スライドタイプ別の統計
python tools/deck_metrics.py <deck_dir>
# 一覧サムネイル（要 pillow）
python tools/contact_sheet.py <deck_dir>
# PDF書き出し（要 LibreOffice）
python tools/export_pdf.py <deck_dir>
# テーマのコントラスト確認
python tools/check_theme.py <theme名>
# 新テーマ雛形
python tools/new_theme.py <name>
# サンプルスライド(PPTX/HTML/PDF/画像)からテーマを生成
python tools/theme_from_sample.py <sample-file> --name <name>
# Archify の diagram JSON をスライド1枚に変換（--into で deck.json の slides 末尾に追記も可）
python tools/archify_import.py <archify.json> --into <deck_dir>            # 追記内容を表示するだけ（書き込まない）
python tools/archify_import.py <archify.json> --into <deck_dir> --confirm  # 承認後に実際に追記して保存
```
> ⚠️ `--into` は既存の `deck.json` を読み込み、末尾に 1 枚追記して**同じパスへ上書き保存**する。
> 既存ファイルがある場合、`--confirm` を付けないと書き込まずに終了し（exit 1）、追記される内容だけを出力する。
> **`--confirm` を付ける前に、その内容を利用者に提示して明示的な承認を得ること。**
> 上書きせずに結果だけ欲しいときは `--out <file>` を使う。

```bash
# 既存 PPTX を見た目そのままに canvas 型デッキへ取り込む（取り込み専用。新規作成には使わない）
python tools/pptx_import.py <src.pptx> --into <deck_dir>            # deck.json が既にあれば書き込まずに終了
python tools/pptx_import.py <src.pptx> --into <deck_dir> --confirm  # 承認後に置き換え（元は deck.json.bak に退避）
# 元 PPTX を PNG 化（Windows + PowerPoint）→ プレビューと並べて比較
pwsh tools/export_pptx_png.ps1 -Src <src.pptx> -OutDir <deck_dir>/_work/ref
python tools/compare_ref.py <deck_dir> <deck_dir>/_work/ref
```
> ⚠️ `pptx_import.py --into` は deck.json を**丸ごと置き換える**（追記ではない）。既存ファイルがある場合は `--confirm` が無いと書き込まない。
`python` が無ければ `python3`（Windows は `py -3`）に読み替える。コマンド自体は PowerShell / Git Bash のどちらでも同じもので動く（`cd` の区切り文字はどちらもそのままで可）。

## 構成

```
plugins/slide-deck/
├── .claude-plugin/plugin.json   # プラグイン定義
├── requirements.txt             # Python 依存関係（pip install -r で導入可）
├── skills/                      # create-deck / add-theme / review-deck / export-pdf / setup
├── agents/                      # deck-evaluator（プレビュー画像を第三者として採点する評価エージェント）
├── tools/                       # build_deck / preview_deck / check_layout / check_svg_fonts /
│                                 #   lint_deck_text / check_visual / deck_metrics / contact_sheet / check_theme /
│                                 #   ja_text / build_settings_widget / proposal_engine / icon_engine /
│                                 #   export_pdf / new_theme / theme_from_sample / setup_deps /
│                                 #   diagram_engine / schedule_engine / check_diagram / archify_import /
│                                 #   canvas_engine / pptx_import / pptx_import_excel /
│                                 #   compare_ref / export_pptx_png.ps1
├── templates/                   # themes/（default, accenture, acn-slide-master, acn-technology-graphik） layouts/（default） icons/（Tabler の定番アイコン）
├── references/                  # deck-schema.md（スキーマ） themes.md（テーマ）
│                                 #   content-guide.md（コンテンツ） diagram-guide.md（図解の描き方）
├── examples/template-sample/    # 全スライドタイプの見本 deck.json
├── manual/deck.json             # スライド版マニュアルのソース
└── USER-GUIDE.html              # ↑ をビルドした成果物（配布物に同梱）
```

## 詳細

- スキーマ（deck.json の全仕様）: [`references/deck-schema.md`](references/deck-schema.md)
- テーマ（トークン一覧・追加方法）: [`references/themes.md`](references/themes.md)
- コンテンツ品質ガイド（構成の型・1枚のルール・執筆前チェックリスト）: [`references/content-guide.md`](references/content-guide.md)
- 図解タイプの描き方（作図規約・座標診断の直し方）: [`references/diagram-guide.md`](references/diagram-guide.md)

## 図解タイプ（Archify 方式）

`architecture` / `dataflow` / `lifecycle` / `sequence` の4タイプは、[Archify](https://github.com/tt-a1i/archify)（MIT）の方式――AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して描く。検証に落ちたら座標付きの修理指示が返る――を Python ネイティブに取り込んだもの。Node.js・Archify 本体は不要で、このプラグイン単体で完結する。

配置はグリッド（`row` / `col`）指定のみで px 座標は書かない、配色は type ごとの色相ではなくテーマトークンのみ（type はアイコンの形で表す）など、意図的に Archify とは異なる設計にしている部分もある。既存の `swimlane` も同じ配線エンジンに乗せ替え、ラベルと線の重なりを解消した。

作図の描き方・座標診断の直し方は [`references/diagram-guide.md`](references/diagram-guide.md) を参照（`create-deck` / `review-deck` スキルの手順にも組み込み済み）。

参考: 「ArchifyでAIに図を描かせる新しいやり方」（クロノITチャンネル, https://www.youtube.com/watch?v=L2KPenldwdo ）

## v1.2.1 の主な変更（社内 Hub 公開版。前回公開の v1.1.1 からの差分）

開発中は v1.2.0〜v1.7.0 として段階的に入れた内容を、社内 Hub 向けに v1.2.1 としてまとめて公開する。詳細は以下の各節。

- **既存 PPTX の取り込み**: `canvas` 型と `pptx_import.py`（見た目そのままに HTML 化）
- **設定フォーム**: 新規作成の最初にテーマ・聞き手・目的・構成・枚数・仕上げの度合いなどを1画面で選ぶ
- **品質チェック**: 字幅の実測による文字あふれの見積もり、泣き別れ対策、文言チェックの拡張、見た目のチェック（`check_visual.py`）、評価エージェント `deck-evaluator` と修正ループ（「仕上げ」を選んだときだけ）
- **提案書向けタイプ8種**: `summary` / `reasons` / `statement` / `row_matrix` / `org` / `house` / `cycle` / `kpi_tree`（全29タイプ）と、結論の帯・出典の行、既存タイプの拡張
- **アイコン**: Tabler Icons（MIT）の定番74点と意味検索
- **テーマ**: 同梱テーマを `default` と、acnpptx の3テンプレートに寄せた配色 `accenture` / `acn-slide-master` / `acn-technology-graphik` の4種にした。旧 `accenture-purple` は `acn-slide-master` に統合し、別名として読める（既存デッキはそのまま同じ見た目でビルドできる。設定フォームの選択肢には出ない）。スライドマスター・アイコン・イラストなど Accenture のブランド資産は同梱していない

## 設定フォームと品質チェックの強化

acnpptx スキルの分析結果から、slide-deck の設計を崩さずに取り込めるものを実装した。

- **設定フォーム**: 新規作成の最初に、テーマ（色トークンから描いたミニプレビュー付き）・聞き手・目的・構成の型・枚数・トーン・図解の方針・出力形式・参考資料を 1 画面で選べるフォームを出す（`tools/build_settings_widget.py`）。送信後は確認を挟まず完成まで進める。visualize ツールが無い環境では AskUserQuestion の 4 問で代替。仕上げの度合い（ドラフト＝機械チェックだけ・既定／仕上げ＝評価ループあり）も選べる
- **字幅の実測**: 文字あふれの見積もりを、テーマのフォントファイルを Pillow で実測した字幅で行う（`tools/ja_text.py`）。英単語は途中で切らず、行頭禁則は前の行に残す。Pillow かフォントが無い環境では従来の近似（全角 1.0 / 半角 0.55）
- **泣き別れ対策**: タイトル・リード・箇条書きの最終行が 1〜2 文字だけ残る文に、ビルド時に文節の切れ目で改行を入れる（HTML と PPTX の両方。`meta.line_balance: false` で無効）。あわせて PPTX では明示的な改行を段落内改行（`a:br`）として出力するようにした
- **文言チェックの拡張**（`lint_deck_text.py`、すべて警告）: 曖昧語・構成の説明・体言止めのリード・タイトルの言い直し（文字 2-gram の重なり）、曖昧な列名・凡例の無い ◎○△・桁区切り、同じタイプの 3 枚連続、`relation` とタイプの不一致、日付の整合（`meta.as_of` より後の「実績」、基準日より前に始まる計画）
- **見た目のチェック**（`check_visual.py`）: プレビュー PNG のインク量から「下 1/3 が空いたスライド」を、dHash から「直前と似たスライドの連続」を検出する

## 定番アイコンと意味検索

- **同梱アイコン**: Tabler Icons（MIT License）の outline から、提案書でよく使う概念の定番だけを74点同梱した（`templates/icons/icons.json`、約40KB）。SVG の円弧などを曲線に変換して持ち、HTML でも PPTX でも線だけのネイティブ図形として描く（画像にしないので PowerPoint で色・太さを変えられる）
- **意味検索**: 各アイコンに日本語・英語の概念語を付け、`icon` に概念語（例「コスト削減」「q:統制 安全」）を書くと最も近いアイコンを選ぶ。似た概念は同じ絵を使い回し、素材を増やさない方針
- **置ける場所**: `summary` / `reasons` / `house` / `cycle` / `cards` の項目の `icon`
- **ツール**: `tools/icon_engine.py`（検索・一覧・一覧画像）、アイコン集を作り直す保守用スクリプト `build_icon_set.py`（外部 URL を取得するため配布物には含めず、開発リポジトリの scripts フォルダに置いている）
- Accenture のブランド資産（アイコン・イラスト・マスター）は使っていない

## 全体像・循環・KPI と既存タイプの拡張

作例の残りのページに対応した（第2弾）。

- **新しいタイプ**: `house`（屋根・柱・土台の全体像）/ `cycle`（円弧の矢印の輪＋時計回りに並ぶ段のパネル）/ `kpi_tree`（目標 → 方向性 → KPI＋目標値＋測り方）
- **結論の帯・出典の行をほぼ全タイプに**: `conclusion` / `source` を書くと、本文の領域（表は行の高さ）を自動で詰めて下端に付ける
- **既存タイプの拡張**: `agenda` の説明文 `desc`、`table` の行見出し `row_header`・合計行 `total_row`、`two_column` の間の三角 `connector: "arrow"`、`steps` の矢羽根見出し `header_style: "arrow"`、`matrix` の散布 `points`、`code` の番号付き注釈 `annotations`
- `code` の文字サイズは行数に加えて最長行の幅でも決めるようにした（横にはみ出して切れていた長い行が収まる）
- PPTX で canvas 要素を同じスライドに何度追加しても図形 ID が重ならないようにした

## 提案書向けのスライドタイプ

acnpptx の紹介ムービーに出てくる作例の提案書（28枚）を1枚ずつ slide-deck のタイプと突き合わせ、既存タイプで描けない定型ページを新しいタイプとして追加した。レイアウトは `tools/proposal_engine.py` が計算して canvas の要素列にし、HTML と PPTX の両方でネイティブ図形として描く（PowerPoint で四角・矢羽根・線を1つずつ編集できる）。

- **`summary`**（要旨）: 番号の箱＋要点＋説明の行。行の高さをそろえ、文字は枠に合わせて自動で縮む
- **`reasons`**（選ばれる理由）: 相手の課題（番号）と自社の強み（a/b/c）を同じ行に並べて対応を見せる
- **`statement`**（言い切り）: 濃色の面に大きな一文。物語の転換点に置く
- **`row_matrix`**（行見出し×列の整理表）: 機会とリスク、工程×領域、前提・参考資料など。列見出しを工程の矢羽根にもできる
- **`org`**（体制図）: 左右の組織ツリー、カギ線、提案範囲の破線枠、組織をまたぐ連携線
- **共通パーツ**: 結論の帯 `conclusion` と出典の行 `source`（提案書向けタイプで使える）

## 評価エージェントと修正ループ

- **`agents/deck-evaluator.md`**: 生成の経緯を知らない第三者としてプレビュー PNG を採点する評価エージェント。10 観点×10 点（5 秒で結論が分かるか・視線の順・密度・タイプの適合・色の意味・均等割りへの逃げ・文字の品質・重心・前後との重複・図と線の仕上げ）で、70 点未満は fail。根拠は画像で確認できる事実に限る
- **修正ループ**: `review-deck` の手順8、または新規作成で「仕上げ」を選んだときの `create-deck` 手順4.6。fail のスライドだけを deck.json（文言・`style` 差分）で直して再採点し、修正は最大 3 周で打ち切って残りを「未解決」として報告する

## 既存 PPTX の取り込み（`canvas` 型）

- **`canvas` 型**: 1280×720 の座標に図形（矢羽根・フローチャート記号・コネクタ・矢印等）・文字・表・SVG アイコンを直接置く**取り込み専用**のスライドタイプ。既存 PowerPoint 資料を見た目のまま HTML 化するためのもので、テーマ（色・フォント）とタイトル・罫線・フッターは適用されない。新規スライドは他のタイプで作る。仕様は [`references/deck-schema.md`](references/deck-schema.md) の「canvas」節
- **`tools/pptx_import.py`**: 既存 PPTX を canvas 型の deck.json に変換する。プレースホルダー/マスター/既定スタイルの継承、表スタイル、色マッピングの上書き、図形ごとの文字領域を PowerPoint と同じ規則で解決する。マスター上の図形は各スライドに展開される。ラスタ画像は埋め込まず枠（placeholder）にする。埋め込み Excel の表化には `openpyxl`（任意）が必要
- **PPTX への再出力**: 図形・線・表は PowerPoint ネイティブの図形として出力され、1つずつ編集できる（SVG アイコンは PNG 画像、グループは解除）
- **`tools/compare_ref.py` / `tools/export_pptx_png.ps1`**: 元 PPTX の画像とプレビューを並べた比較画像と差分スコアを出す
- HTML ビューアに下部ツールバー（前後移動・ページ番号ジャンプ・一覧表示）を追加。`preview_deck.py` / `check_layout.py` はツールバーを隠して撮影し、1枚ごとの再読み込みをやめて高速化。`check_layout.py` は canvas では見切れ・スライド外へのはみ出しのみを判定する

原案はチームメンバーによる v2.0.0 提案（canvas 型と PPTX 取り込み）。取り込み時に、注入対策（色・フォント・SVG の検証と許可リスト方式のサニタイズ）、`--into` の承認ゲート、XML パーサの安全化、Excel 取り込み範囲の上限を追加した。

## 設計上の注意

- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は macOS Keynote 互換性を壊す）。`notes` は HTML 側でのみ表示。
- 色は hex 直書きせずテーマトークンで指定。テーマ切替は `meta.theme` のみ。（例外: 取り込み専用の `canvas` 型は元資料の色をそのまま hex で持つ）
- 生成物（`build/`）は直接編集せず、deck.json を直して再ビルドする。

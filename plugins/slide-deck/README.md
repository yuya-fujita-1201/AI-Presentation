# slide-deck プラグイン

JSON（`deck.json`）をソースにして、スライドを **HTML / PowerPoint(16:9)** にビルドする Claude Code プラグイン。
スライドの**内容もデザインもすべて deck.json のパラメーター**で管理し、色はテーマトークンで切替・追加できる。

> 📖 **使い方のスライド版マニュアル**: [`USER-GUIDE.html`](USER-GUIDE.html)（ブラウザで開く。← / → で移動）。この README は概要、USER-GUIDE はダウンロードした人向けの操作マニュアル。ソースは [`manual/deck.json`](manual/deck.json)（本プラグイン自身でビルド）。

社内配布物です。受領者内での利用を想定しており、社外への再配布は想定していません。

## インストール

```
/plugin marketplace add yuya-fujita-1201/AI-Presentation
/plugin install slide-deck@ai-presentation
```

## 初回セットアップ（依存関係）

**Python 3.9 以上が必要**。依存の導入は `/slide-deck:setup` から Claude Code 経由で行うのが最も簡単（内部で下記スクリプトを呼ぶだけ）。この README のとおりターミナルから自分で叩く場合は次節の注意を参照。

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
| `/slide-deck:review-deck` | 既存デッキを機械的に一括レビュー |
| `/slide-deck:export-pdf` | ビルド済み PPTX を PDF に書き出す |
| `/slide-deck:setup` | 依存関係の初回セットアップ |

スライド作成を頼めば `create-deck` が自動で選ばれる。手動なら上記コマンドで明示的に呼べる。

## 手動で使う（スキルを介さず）

> **注意**: `${CLAUDE_PLUGIN_ROOT}` は Claude Code がスキル本文（SKILL.md）を実行するときにだけ内部で実パスへ置換する専用トークンで、PowerShell や Git Bash を素で開いて手入力しても定義されない（未定義変数として空文字に展開され、`python "/tools/xxx.py"` のような誤ったパスになって失敗する）。ここから先のコマンドは Claude Code のスキル実行を介さずターミナルから直接叩く想定なので、`${CLAUDE_PLUGIN_ROOT}` の代わりに **このプラグインのディレクトリへ `cd` してから相対パスで実行する**。このリポジトリを clone している場合はそのディレクトリが `plugins/slide-deck/`。`/plugin install` で導入した場合はお使いの Claude Code のプラグイン導入先ディレクトリを確認して読み替える。

```bash
cd path/to/plugins/slide-deck   # このプラグインのディレクトリに移動（例: このリポジトリなら plugins/slide-deck）

# ビルド（HTML + PPTX）
python tools/build_deck.py <deck_dir>
# プレビューPNG
python tools/preview_deck.py <deck_dir> [番号...]
# 構造チェック（はみ出し・重なり・文字あふれ）
python tools/check_layout.py <deck_dir>
# 図解タイプの配線・ラベル診断（architecture/dataflow/lifecycle/sequence/swimlane）
python tools/check_diagram.py <deck_dir>
# SVG図版のフォント機械チェック（明朝体等へのフォールバックを検出）
python tools/check_svg_fonts.py <deck_dir>
# 文言チェック（文字量・AI定型句など）
python tools/lint_deck_text.py <deck_dir>
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
# Archify の diagram JSON をスライド1枚に変換（deck.json の slides 末尾に追記も可）
python tools/archify_import.py <archify.json> --into <deck_dir>
```
`python` が無ければ `python3`（Windows は `py -3`）に読み替える。コマンド自体は PowerShell / Git Bash のどちらでも同じもので動く（`cd` の区切り文字はどちらもそのままで可）。

## 構成

```
plugins/slide-deck/
├── .claude-plugin/plugin.json   # プラグイン定義
├── requirements.txt             # Python 依存関係（pip install -r で導入可）
├── skills/                      # create-deck / add-theme / review-deck / export-pdf / setup
├── tools/                       # build_deck / preview_deck / check_layout / check_svg_fonts /
│                                 #   lint_deck_text / deck_metrics / contact_sheet / check_theme /
│                                 #   export_pdf / new_theme / theme_from_sample / setup_deps /
│                                 #   diagram_engine / check_diagram / archify_import
├── templates/                   # themes/（default, accenture-purple） layouts/（default）
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

## 設計上の注意

- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は macOS Keynote 互換性を壊す）。`notes` は HTML 側でのみ表示。
- 色は hex 直書きせずテーマトークンで指定。テーマ切替は `meta.theme` のみ。
- 生成物（`build/`）は直接編集せず、deck.json を直して再ビルドする。

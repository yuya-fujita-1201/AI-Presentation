# slide-deck プラグイン

JSON（`deck.json`）をソースにして、スライドを **HTML / PowerPoint(16:9)** にビルドする Claude Code プラグイン。
スライドの**内容もデザインもすべて deck.json のパラメーター**で管理し、色はテーマトークンで切替・追加できる。

> 📖 **使い方のスライド版マニュアル**: [`USER-GUIDE.html`](USER-GUIDE.html)（ブラウザで開く。← / → で移動）。この README は概要、USER-GUIDE はダウンロードした人向けの操作マニュアル。ソースは [`manual/deck.json`](manual/deck.json)（本プラグイン自身でビルド）。

## インストール

```
/plugin marketplace add yuya-fujita-1201/AI-Presentation
/plugin install slide-deck@ai-presentation
```

## 初回セットアップ（依存関係）

**Python 3 が必要**。その上で依存を導入する（`/slide-deck:setup` からでも実行できる）:

```bash
# 必須(python-pptx)
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py"
# プレビューPNGも使う場合（playwright + chromium）
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --playwright
```

| パッケージ | 要否 | 用途 |
|---|---|---|
| `python-pptx` | 必須 | PPTX 生成 |
| `playwright`(+chromium) | 任意 | プレビューPNG生成 |
| `pillow` | 任意 | 一覧シート生成 |

## 使い方（スキル）

| スキル | 用途 |
|---|---|
| `/slide-deck:create-deck` | deck.json からスライドを作成・編集・ビルド |
| `/slide-deck:add-theme` | 新しいテーマ（配色・フォント）を追加 |
| `/slide-deck:setup` | 依存関係の初回セットアップ |

スライド作成を頼めば `create-deck` が自動で選ばれる。手動なら上記コマンドで明示的に呼べる。

## 手動で使う（スキルを介さず）

```bash
# ビルド（HTML + PPTX）
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>
# プレビューPNG
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> [番号...]
# 新テーマ雛形
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name>
# サンプルスライド(PPTX/HTML/PDF/画像)からテーマを生成
python "${CLAUDE_PLUGIN_ROOT}/tools/theme_from_sample.py" <sample-file> --name <name>
```

## 構成

```
plugins/slide-deck/
├── .claude-plugin/plugin.json   # プラグイン定義
├── skills/                      # create-deck / add-theme / setup
├── tools/                       # build_deck / preview_deck / new_theme / theme_from_sample / setup_deps / QAヘルパー
├── templates/                   # themes/（default, accenture-purple） layouts/（default）
├── references/                  # deck-schema.md（スキーマ） themes.md（テーマ）
└── examples/template-sample/    # 全スライドタイプの見本 deck.json
```

## 詳細

- スキーマ（deck.json の全仕様）: [`references/deck-schema.md`](references/deck-schema.md)
- テーマ（トークン一覧・追加方法）: [`references/themes.md`](references/themes.md)

## 設計上の注意

- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は macOS Keynote 互換性を壊す）。`notes` は HTML 側でのみ表示。
- 色は hex 直書きせずテーマトークンで指定。テーマ切替は `meta.theme` のみ。
- 生成物（`build/`）は直接編集せず、deck.json を直して再ビルドする。

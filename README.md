# AI-Presentation — スライド生成の仕組み

**JSON をソースにして、スライドを HTML / PowerPoint にビルドする仕組み**です。
スライドの内容もデザインも `deck.json` のパラメーターで管理し、AI（Claude Code など）でもヒトでも同じルールで編集・微修正できます。

> このリポジトリは「スライドを書く仕組み」だけを収めたミニマム構成です。実際の資料例は `decks/10-template-sample/`（全スライドタイプのサンプル）を参照してください。

## フォルダ構成

```
AI-Presentation/
├── README.md            # このファイル
├── CLAUDE.md            # Claude Code 向けの作業ルール
├── AGENTS.md            # その他 AI エージェント（Codex 等）向けの入口
├── decks/               # ★ スライド（1デッキ = 1フォルダ）
│   ├── README.md        #   デッキ一覧・命名ルール
│   └── 10-template-sample/  # 全スライドタイプの見本デッキ
│       ├── deck.json    #     スライドのソース（これだけ編集すればよい）
│       ├── assets/      #     画像・SVG など
│       └── build/       #     生成物（HTML / PPTX / PNG）※再生成可能・Git管理外
├── templates/
│   ├── themes/          # テーマ定義（色・フォント）。HTML/PPTX 共通
│   │   ├── default.json         #   省略時のフォールバック
│   │   └── accenture-purple.json
│   └── layouts/         # レイアウト既定値（全オブジェクトの位置・サイズ px）
│       └── default.json
├── tools/
│   ├── build_deck.py    # deck.json → HTML / PPTX ビルダー（コア）
│   ├── preview_deck.py  # 指定スライドを PNG 化（微修正の目視確認用）
│   ├── contact_sheet.py # プレビューPNGを一覧シート化
│   ├── check_layout.py  # レイアウトのはみ出し・重なりチェック
│   ├── check_svg_fonts.py  # SVG のフォント指定チェック
│   ├── deck_metrics.py  # デッキの枚数・文字量などの計測
│   ├── lint_deck_text.py   # 表示テキストの簡易 lint
│   └── test_build_deck_links.py  # ビルダーの回帰テスト
└── docs/
    └── deck-schema.md   # deck.json のスキーマリファレンス
```

## 動作要件

- **Python 3**（必須）
- **python-pptx**（必須。PPTX 生成）: `pip install python-pptx`
- **Playwright**（任意。`preview_deck.py` のプレビューPNG生成に使用）: `pip install playwright && playwright install chromium`
- **Pillow**（任意。`contact_sheet.py` の一覧シート生成に使用）: `pip install pillow`

## 使い方

### 1. デッキを作る（JSON → HTML / PPTX）

```bash
# 新しいデッキ: decks/<デッキ名>/deck.json を作る（スキーマは docs/deck-schema.md）
# 既存の見本 decks/10-template-sample/deck.json をコピーして書き換えるのが早い

# ビルド（HTML と PPTX を両方生成）
python tools/build_deck.py decks/10-template-sample

# HTML だけ / PPTX だけ
python tools/build_deck.py decks/10-template-sample --html
python tools/build_deck.py decks/10-template-sample --pptx

# 指定スライドを PNG 化して目視確認（Playwright が必要）
python tools/preview_deck.py decks/10-template-sample 5
```

> 環境によっては `python` ではなく `python3` を使ってください。

生成物は `decks/<デッキ名>/build/` に出力されます。ファイル名には `deck.json` の `meta.id` を使います:

- `<meta.id>.html` — ブラウザで開けるスライドショー（← / → キーで移動、N でノート表示）
- `<meta.id>.pptx` — PowerPoint ファイル（16:9）
- `preview/slide-NN.png` — プレビュー画像

### 2. 編集する（パラメーター駆動の微修正）

スライドは **内容もデザインもすべて deck.json のパラメーター**で管理します:

- 仮想キャンバス 1280×720px（16:9）。全オブジェクトの位置・サイズ・フォント・色を px 指定
- デザインの既定値は `templates/layouts/default.json`、色は `templates/themes/*.json`
- 「5枚目のタイトルだけ 2px 下げる」「この表だけ行を高く」は、該当スライドの `style` に差分を書くだけ。**AI に再生成させる必要はない**
- HTML と PPTX は同じパラメーターを読む（96dpi 換算）ので見た目が一致する

HTML や PPTX を直接編集しないでください（再ビルドで消えます）。詳細は `docs/deck-schema.md`。

## 設計上の注意

- **スピーカーノートは PPTX に出力しない**: python-pptx の notes_slide は macOS Keynote の互換性を壊す既知問題があるため。ノートは HTML 側（N キー）でのみ表示される。
- 色は hex 直書きせず、テーマトークン（`primary` / `accent` 等）で指定する。テーマ切替は `meta.theme` の変更のみ。
- `decks/*/build/` は生成物なので Git 管理外（`.gitignore` 済み）。

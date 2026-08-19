# presentation — 社内勉強会 資料プロジェクト

自分とチームメンバー向けの勉強会資料（AI関連など）を作成・管理するプロジェクト。
ナレッジは **OKF (Open Knowledge Format)** 形式で蓄積し、プレゼン資料は **JSON をソース** として HTML / PowerPoint にビルドする。

## フォルダ構成

```
presentation/
├── README.md            # このファイル
├── CLAUDE.md            # Claude Code 向けの作業ルール
├── knowledge/           # ★ OKFバンドル（ナレッジベース本体）
│   ├── index.md         #   バンドルのエントリーポイント
│   ├── log.md           #   変更履歴
│   ├── okf/             #   テーマ別ナレッジ（例: OKFそのものについて）
│   └── sources/         #   収集した資料の台帳（1ソース = 1ファイル）
├── decks/               # ★ プレゼン資料（1デッキ = 1フォルダ）
│   ├── 01-prompt-engineering/  # 現行デッキ。先頭2桁が表示順
│   │   ├── deck.json    #   スライドのソース（これだけ編集すればよい）
│   │   └── build/       #   生成物（HTML / PPTX）※再生成可能
│   ├── 02-context-engineering/
│   ├── ...
│   └── _archive/        #   旧版・比較用・不採用版
├── templates/
│   ├── themes/          # テーマ定義（色・フォント）。HTML/PPTX 共通
│   └── layouts/         # レイアウト既定値（全オブジェクトの位置・サイズ px）
├── tools/
│   ├── build_deck.py    # deck.json → HTML / PPTX ビルダー
│   └── preview_deck.py  # 指定スライドを PNG 化（微修正の目視確認用）
└── docs/
    └── deck-schema.md   # deck.json のスキーマリファレンス
```

## ワークフロー

### 1. ナレッジを貯める（OKF）

新しい資料（動画・記事・書籍など）を見つけたら:

1. `knowledge/sources/` に 1ソース = 1ファイルで登録（YAMLフロントマター + 要約）
2. テーマとして育ってきたら `knowledge/<テーマ>/` にコンセプトファイルとして昇華
3. `index.md` と `log.md` を更新

OKFの書き方自体は `knowledge/okf/` に整理してあるので、それが手本になる。

### 2. デッキを作る（JSON → HTML / PPTX）

```bash
# 新しいデッキ: decks/<デッキ名>/deck.json を作る（スキーマは docs/deck-schema.md）

# ビルド（HTML と PPTX を両方生成）
python3 tools/build_deck.py decks/07-okf-visual-guide

# HTML だけ / PPTX だけ
python3 tools/build_deck.py decks/07-okf-visual-guide --html
python3 tools/build_deck.py decks/07-okf-visual-guide --pptx

# 指定スライドを PNG 化して目視確認
python3 tools/preview_deck.py decks/07-okf-visual-guide 5
```

生成物は `decks/<デッキ名>/build/` に出力される。ファイル名には `deck.json` の `meta.id` を使う:

- `<meta.id>.html` — ブラウザで開けるスライドショー（← / → キーで移動、N でノート表示）
- `<meta.id>.pptx` — PowerPoint ファイル（16:9）
- `preview/slide-NN.png` — プレビュー画像

### 3. 編集する（パラメーター駆動の微修正）

スライドは **内容もデザインもすべて deck.json のパラメーター**で管理している:

- 仮想キャンバス 1280×720px。全オブジェクトの位置・サイズ・フォント・色を px 指定
- デザインの既定値は `templates/layouts/default.json`、色は `templates/themes/*.json`
- 「5枚目のタイトルだけ 2px 下げる」「この表だけ行を高く」は、該当スライドの `style` に差分を書くだけ。**AI に再生成させる必要はない**
- HTML と PPTX は同じパラメーターを読む（96dpi 換算）ので見た目が一致する

HTML や PPTX を直接編集しない（再ビルドで消えるため）。詳細は `docs/deck-schema.md`。

## 設計上の注意

- **スピーカーノートは PPTX に出力しない**: python-pptx の notes_slide は macOS Keynote の互換性を壊す既知問題があるため。ノートは HTML 側（N キー）でのみ表示される。
- テーマ（色・フォント）は `templates/themes/default.json` に一元化。HTML / PPTX の両ビルダーが同じ値を読む。
- `decks/*/build/` は生成物なので Git 管理外（.gitignore 済み）。

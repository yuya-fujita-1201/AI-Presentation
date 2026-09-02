---
name: add-theme
description: スライドの配色・フォント（テーマ）を新しく追加する。ユーザーがブランドカラーや独自テーマ、色・フォントの変更、テーマの追加を求めたときに使う。テーマは色トークン14種＋フォント3種で構成され、default を継承して差分だけ書ける。
allowed-tools: Bash, Read, Write, Edit
---

# add-theme — 新しいテーマ（色・フォント）を追加する

テーマは **色トークン14種＋フォント3種**の JSON。`default` をベースにマージされるので、**新テーマは上書きしたいトークンだけ書けばよい**（残りは default から継承）。トークンの意味は `${CLAUDE_PLUGIN_ROOT}/references/themes.md` を参照。

作り方は2通り: **A) サンプルスライドから自動生成**、**B) 雛形から手書き**。

## A) サンプルスライドから作る

既存のスライド（PPTX / HTML / PDF / 画像）を読み込ませ、配色・フォントを抽出してテーマ JSON を自動生成する。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/theme_from_sample.py" <sample-file> --name <name>
#   例: ブランドの .pptx から       … best（実使用色を面積重みで集計）
#   .png/.jpg（要 pillow）/ .pdf（要 pymupdf）/ .html にも対応
```

- 抽出は自動推定なので、**出力されるレポート（検出色・フォント・マッピング）を必ず確認**し、生成された `<name>.json` の `colors`/`fonts` を微調整する（特に primary と accent は入れ替わることがある）。
- 追加依存が要る形式は事前に: 画像=`/slide-deck:setup --pillow`、PDF=`/slide-deck:setup --pdf`。
- 出力先は `--dir` → 環境変数 `SLIDE_DECK_THEMES` → 同梱の順（下の「消えないように保存」参照）。

生成後は 3.（使う）へ。

## B) 雛形から手書きで作る

### 1. 雛形を作る

### 1. 雛形を作る
```bash
# default の全トークンを写した自己完結テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name>

# 既存テーマを継承し、差分だけ書く最小テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> --extends accenture-purple
```
`<name>` は kebab-case（例 `brand-navy`）。

### 2. 色・フォントを編集
生成された `<name>.json` の `colors` / `fonts` を編集する。最低限 `primary` / `accent` を決めれば見た目が変わる。トークンの役割は `references/themes.md`。

### 3. 使う
デッキの `deck.json` の `meta.theme` に `"<name>"` を指定して再ビルドするだけ。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>
```

## テーマを消えないように保存する（配布時の注意）
`new_theme.py` は既定で**同梱テーマ置き場**に書くが、そこはプラグイン更新で上書きされうる。ユーザー独自テーマを永続させたい場合は、専用ディレクトリを作って環境変数で指定する:

```bash
export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"     # Windows: setx SLIDE_DECK_THEMES "%USERPROFILE%\.slide-deck-themes"
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name>   # SLIDE_DECK_THEMES に出力される
```
ビルダーは **`SLIDE_DECK_THEMES` → デッキ隣の `themes/` → 同梱** の順にテーマを探索する。プロジェクトに `themes/<name>.json` を置く方法でもよい。

## 補足
- テーマ変更は `meta.theme` の切替のみで完結する（deck.json 本文の色指定はトークン名で書くこと）
- `extends` を使うと「ブランド色だけ変えた派生テーマ」を簡単に量産できる

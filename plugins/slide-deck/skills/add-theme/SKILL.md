---
name: add-theme
description: スライドの配色・フォント（テーマ）を新しく追加する。ユーザーがブランドカラーや独自テーマ、色・フォントの変更、テーマの追加を求めたときに使う。テーマは色トークン14種＋フォント3種で構成され、default を継承して差分だけ書ける。
allowed-tools: Bash, Read, Write, Edit
---

# add-theme — 新しいテーマ（色・フォント）を追加する

テーマは **色トークン14種＋フォント3種**の JSON。`default` をベースにマージされるので、**新テーマは上書きしたいトークンだけ書けばよい**（残りは default から継承）。トークンの意味は `${CLAUDE_PLUGIN_ROOT}/references/themes.md` を参照。

## 追加の手順

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

---
name: add-theme
description: ブランド色・フォントのテーマ（JSON）を新規に追加する。既存の PPTX・画像・PDF から配色を抽出でき、角丸・罫線などの形（shape）の選択・自作にも使う。meta.theme や meta.shape を切り替えるだけなら create-deck で足りる。
allowed-tools: Bash, Read, Write, Edit
---

# add-theme — 新しいテーマ（色・フォント）を追加する

テーマは **色トークン 18 種＋フォント 3 種**の JSON。`default` をベースにマージされ、明示していないトークンはテーマ自身の基本色（`primary` / `accent` など）から自動導出されるので、**新テーマは上書きしたいトークンだけ書けばよい**。トークンの意味・導出規則・探索順は `${CLAUDE_PLUGIN_ROOT}/references/themes.md`。

作り方は 2 通り: **A) サンプルスライドから自動生成**、**B) 雛形から手書き**。どちらも、作ったあとは「保存先」と「使う」に進む。

色とは別に、角丸・罫線・見出しの太さ・箱の影を決める**形（shape）**がある（下の「形（shape）を選ぶ」）。既存テーマへの切替は、deck.json の `meta.theme` を書き換えるだけ（同梱: `default` / `accenture` / `acn-slide-master` / `acn-technology-graphik`）。

## 保存先を先に決める

ビルダーは次の順でテーマを探す（先に見つかったものが勝つ）。**環境変数 `SLIDE_DECK_THEMES` → `<deck_dir>/themes/` → deck_dir の親（3 階層上まで）の `themes/` → カレントディレクトリの `themes/` → 同梱 `templates/themes/`**。作ったテーマがこのどれかに入っていれば見つかる。

| 目的 | 書き方 |
|---|---|
| このデッキだけで使う | `--deck <deck_dir>`（`<deck_dir>/themes/` に作る。いちばん確実） |
| プロジェクトの複数デッキで使う | プロジェクト直下で実行する（既定の `./themes/`。`decks/<名前>/` のデッキから見つかる） |
| 複数プロジェクトで使い回す | 環境変数 `SLIDE_DECK_THEMES` を専用フォルダに設定する（例: `export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"`。Windows は `setx SLIDE_DECK_THEMES "%USERPROFILE%\.slide-deck-themes"`） |

**同名のテーマがすでにあると、ツールは「すでに存在します（上書きは --force）」で止まる。`--force` で上書きすると利用者が手直ししたテーマが消えるので、利用者の承認を取ってから付ける**（別の名前で作る手もある。`${CLAUDE_PLUGIN_ROOT}/references/approval-gates.md`）。

プラグインの同梱フォルダには、`--dir` で明示したときだけ書く（プラグイン更新でユーザーのテーマが消えるのを避けるため）。書き込んだ後、ツールは「書き込み先」と「どのデッキから見つかるか」を表示する。**見つからない場所に作ったと表示されたら、保存先を選び直す**。

## A) サンプルスライドから作る

既存のスライド（PPTX / HTML / PDF / 画像）から配色・フォントを抽出して、テーマ JSON を作る。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/theme_from_sample.py" <sample-file> --name <name> [--deck <deck_dir>]
```

- 抽出は自動推定なので、**出力されるレポート（検出色・フォント・マッピング）を確かめ**、生成された `<name>.json` の `colors` / `fonts` を微調整する。特に `primary` と `accent` は入れ替わることがある（候補が僅差だとレポートに「要確認」と出る）。
- `.pptx` が最も精度が高い（実使用色を面積重みで集計）。`.png` / `.jpg` は pillow、`.pdf` は pymupdf が要る（`/slide-deck:setup --pillow` / `--pdf`）。

## B) 雛形から手書きで作る

```bash
# default の全トークンを写した自己完結テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> [--deck <deck_dir>]
# 既存テーマを継承し、差分だけ書く最小テーマ
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> --extends acn-slide-master [--deck <deck_dir>]
```

形も一緒に決めるなら `--shape soft` を付ける（テーマ JSON に `"shape"` が入る）。`<name>` は kebab-case（例 `brand-navy`）。生成された JSON の `colors` / `fonts` を編集する。最低限 `primary` と `accent` を決めれば、表ヘッダ色・コード背景・強調色などの派生トークンも追随する。色は `#RRGGBB`（または `#RGB`）で書く（他のトークン名や色名は使えない）。

## コントラストを確かめる

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <name> --deck <deck_dir>
```

主要な文字色と背景の組み合わせの WCAG コントラスト比が表示される。（ビルドは濃い面・色つきの面の上の文字色を、4.5:1 に足りないときだけ同じ色味のまま白か黒の側へ自動で寄せるが、これは読めない組の応急処置。テーマの色は `check_theme.py` の警告を直す。自動調整の規則と止め方は `${CLAUDE_PLUGIN_ROOT}/references/themes.md` の「ビルドが文字色を整える」。）4.5 未満（大きい・太い文字は 3.0 未満）は警告として列挙され、`text` と背景が 4.5 未満なら exit 1 になるので、明度を調整してから進む。テーマ JSON の形の誤り（未知のキー・hex でない色）もここで分かる。`--deck` を付けると、デッキの `themes/` にあるテーマも見つかる。

## 使って、目で確かめる

deck.json の `meta.theme` に `"<name>"` を書いて再ビルドする。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> <番号...>
```
`title`（primary 地に文字が乗る）・`bullets`・`table`（ヘッダ色）・`matrix`（強調象限）・数字が主役のスライドなど、primary / accent / highlight_fill を実際に使うスライドを選んで PNG を見て、文字が読めるか・強調が意図どおり見えるかを確かめる。playwright が無い環境では `export_pdf.py` や `soffice --headless --convert-to png` で代替する。「テーマが見つかりません」と出たら、保存先がデッキから見える場所か（上の探索順）を確かめる。

## 形（shape）を選ぶ

`meta.shape`（deck.json）かテーマ JSON の `"shape"` で選ぶ。何も書かなければ `classic`（従来の見た目）。色のテーマとは独立で、どの組み合わせでもよい。

| shape | 合う資料 |
|---|---|
| `classic` | 迷ったらこれ（12〜14px の角丸・全幅のアクセント罫線） |
| `sharp` | 経営会議・監査・規程など、硬く正確な印象（角丸なし・細い罫線） |
| `soft` | 研修・社内共有・採用など、親しみやすさ（大きな角丸・淡い影） |
| `editorial` | 提案・ブランド紹介・講演など、落ち着いた誌面風（大きく軽い見出し・小さな角） |

選び方の目安は、数字と表が中心なら `sharp`、説明・手順が中心なら `soft`、文章と図が中心なら `editorial`。同梱の 4 つで足りなければ、`<deck_dir>/shapes/<名前>.json` に自作する（同梱の `templates/shapes/*.json` をコピーして `tokens`（角丸・罫線の太さなど）を直す。探索順・書き方・トークン一覧は `${CLAUDE_PLUGIN_ROOT}/references/themes.md` の「形（shape）とトークン」）。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" --shapes --deck <deck_dir>   # 使える shape の一覧と検証（エラーがあれば exit 1）
```
shape を替えたら、代表スライド（表紙・cards・図解・表）をプレビューで見る。表（`table`）の角は shape に関わらず四角のまま。

## 補足

- テーマ変更は `meta.theme` の切替だけで完結する。deck.json 本文の色指定はトークン名で書く（そうしないとテーマを変えても色が追随しない）。
- `extends` を使うと「ブランド色だけ変えた派生テーマ」を簡単に作れる。
- 暗い背景のテーマを作ったときは、見出し・本文・表のコントラストを `check_theme.py` と代表スライドの目視で確かめる。

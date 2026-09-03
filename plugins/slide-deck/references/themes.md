# テーマ（色・フォント）リファレンス

テーマは配色とフォントを定義する JSON。`deck.json` の `meta.theme` にテーマ名を指定して使う。
デッキ本文では色を hex 直書きせず、**テーマトークン名**（`primary` / `accent` 等）で指定する。テーマを切り替えるだけで全スライドの見た目が変わる。

## 仕組み: default をベースにマージ＋派生トークンの自動導出

- どのテーマも **`default` をベースにマージ**される。新しいテーマは**上書きしたいトークンだけ**書けばよく、書かなかったトークンは以下の優先順で決まる。
- `extends` を指定すると、`default` の代わりに任意のテーマを親にできる（例: ブランド色だけ変えた派生テーマ）。循環する `extends` はエラーになる。
- テーマの探索順は **`SLIDE_DECK_THEMES`（環境変数のディレクトリ）→ `<deck_dir>/themes/` → 同梱 `templates/themes/`**。先に見つかったものが勝つ。

### 派生トークンの自動導出（重要）

`default` 以外のテーマで明示していないトークンは、`default` の固定 hex をそのまま継承するのではなく、**そのテーマ自身の基本色から自動的に導出**される。これにより、`primary` や `accent` だけを変えた最小テーマでも、表のヘッダ色やハイライト色などが新しい配色に自然に追随する。

基本色（`background` / `surface` / `text` / `muted` / `primary` / `accent` / `on_primary`）のうち明示された値を使い、次の式で残りを導出する（`mix(a, b, t)` は色 a を `1-t`、色 b を `t` の割合で線形混合した色）:

| トークン | 導出式 |
|---|---|
| `table_header_bg` | `primary` |
| `table_header_text` | `on_primary` |
| `table_row_alt` | `mix(surface, background, 0.5)` |
| `on_primary_soft` | `mix(primary, "#FFFFFF", 0.90)` |
| `on_primary_muted` | `mix(primary, "#FFFFFF", 0.75)` |
| `code_bg` | `mix(primary, "#000000", 0.55)` |
| `code_text` | `"#E6EDF5"`（固定） |
| `highlight_fill` | `mix(accent, background, 0.75)` |
| `border` | `mix(text, background, 0.72)` |
| `accent_on_primary` | `mix(accent, "#FFFFFF", 0.45)` |
| `heading_text` | `primary`。ただし `background` 上でコントラスト比 4.5 未満なら、暗い背景では白へ・明るい背景では黒へ 0.1 刻みで寄せて 4.5 以上にする（暗色テーマ対策） |
| `surface`（未指定時） | `mix(primary, background, 0.88)` |
| `muted`（未指定時） | `mix(text, background, 0.35)` |

> **面の視認性**: `surface` / `highlight_fill` / `border` の混合率は、ディスプレイの発色や輝度・彩度の違いによって
> 淡い箱が背景に溶けて見えなくなることを防ぐため、`background` 側へあまり寄せすぎない値にしてある
> （目安: `surface`/`background` のコントラスト比 1.18 以上、`border`/`background` 1.40 以上、
> `highlight_fill`/`surface` 1.08 以上。`check_theme.py` が警告として検査する。下記「コントラストの確認」参照）。

`default` テーマ自身は全トークンを明示済み（`templates/themes/default.json` が正）なので、この導出ロジックの対象にはならない。`extends` チェーンの途中に `default` 以外のテーマがある場合、そのテーマが明示しないトークンはそのテーマの基本色から導出される（`default` の固定値へフォールバックしない）。

## トークン一覧

### colors（18種）

| トークン | 役割 |
|---|---|
| `background` | スライドの背景色 |
| `surface` | カード・淡い面・補助ブロックの背景 |
| `text` | 本文の基本文字色 |
| `muted` | キャプション等の弱い補助文字色（`architecture` 系タイプのノード sublabel・凡例文字にも使う） |
| `primary` | 主要色（見出し帯・章扉・表ヘッダ地などの構造色）。**既定レイアウトでは、`section`/`closing`（`primary` を背景に敷き `on_primary` で文字を載せる）を除くほぼ全タイプの `title` 文字色、および `quote.text` / `two_column.col_heading` / `matrix`・`cards` の `heading_color` / `agenda.body.active_color` にも直接使われる**（ブランドカラーを見出しに出すための意図的な設計。`default` / `accenture-purple` は `primary` が十分に濃く `background`（白）に対して高コントラストなので問題ない）。**新しいテーマを作るとき（特に背景が暗色のテーマ）は、`primary` 単体が `background` に対して十分なコントラスト（目安 3:1 以上、可能なら 4.5:1）を持つ色にすること**。`primary` が `background` に近い明度だと、上記の見出しがすべて背景に溶けて読めなくなる。`check_theme.py` は現状この組み合わせ（`primary`/`background`）を検査対象に含まないため、暗色系テーマを作った際は `preview_deck.py` で `title` / `table` / `matrix` / `cards` を目視確認すること（対処法は次項「`primary` が読みにくいときの対処」参照） |
| `accent` | 強調色（eyebrow・ブランド表記・差し色。**本文サイズの文字色にも使われるため、背景に対して WCAG AA（4.5:1 以上）を確保すること**） |
| `on_primary` | `primary` 地の上に載せる文字色（通常は白） |
| `on_primary_soft` | `primary` 地の上のやや弱い文字・線 |
| `on_primary_muted` | `primary` 地の上のさらに弱い文字・線 |
| `heading_text` | 通常背景（`background` / `surface` / `highlight_fill`）の上に載せる見出し文字色（title / quote.text / col_heading / cards・matrix の heading / agenda の現在地 / swimlane のノード文字。`architecture`/`dataflow`/`lifecycle`/`sequence` のノード文字にも使う）。既定は `primary` と同じ値。暗色テーマでは自動で読める明度に調整される |
| `accent_on_primary` | `primary` 地の上に載せる `accent` 系の強調文字（例: `section.number` / `closing.message`）。`accent` をそのまま `primary` 地の大文字に使うとコントラスト不足になりやすいため専用トークンを使う |
| `code_bg` | コードブロックの背景 |
| `code_text` | コードブロックの文字色 |
| `table_header_bg` | 表のヘッダ行の背景 |
| `table_header_text` | 表のヘッダ行の文字色 |
| `table_row_alt` | 表の交互行（ゼブラ）の背景 |
| `highlight_fill` | 強調用の淡い塗り（`matrix` の強調象限、`table` の `row_fills` 推奨値、`swimlane` の淡い塗りなど。`architecture` 系タイプの強調ノード・タグピル・凡例背景にも使う） |
| `border` | 罫線色（表の罫線、`swimlane` のレーン区切り線、`two_column`/`steps`/`matrix`/`cards`/`agenda` の淡い箱の 1px 外枠など）。`rgba(0,0,0,x)` の直書きの代わりに使う（`architecture` 系タイプのノード枠線にも使う） |

### fonts（3種、文字列 または 文字列の配列）

| トークン | 役割 |
|---|---|
| `heading` | 見出し用フォント（title / eyebrow / section.number / quote.text / col_heading / cards・matrix の heading / steps の label / image_text の punch / closing.message などに適用。未指定なら `body` を使う） |
| `body` | 本文用フォント |
| `code` | コード・等幅用フォント |

各トークンは **文字列1つ、または文字列の配列**で指定できる（フォールバック順）:
```json
{ "fonts": { "heading": ["Yu Gothic UI", "Meiryo"], "body": "Meiryo UI", "code": "Consolas" } }
```
- **HTML**: 配列の全フォントに加え、組み込みのフォールバック（和文: `"Yu Gothic UI", "Meiryo", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Noto Sans CJK JP", sans-serif`。code: `"Consolas", "Menlo", "Courier New", monospace`）まで含めた `font-family` を出力する
- **PPTX**: python-pptx はフォント1つしか持てないため、配列の**先頭の1名**だけを使う（`a:latin` / `a:ea` / `a:cs` すべてに同じ名前を設定）。**PPTX/HTML を閲覧する環境に実在するフォント**を先頭に置くこと

> 社内配布では全員が持つフォントを選ぶと崩れにくい。既定テーマ（`default`）は `Meiryo` / `Consolas`（Windows・Office for Mac に存在）。

## 最小の作り方

最低限 `primary` と `accent` を決めれば見た目が大きく変わる（表のヘッダ色・コード背景・ハイライト色などの派生トークンも自動的に追随する）。例（差分だけ書く最小テーマ）:

```json
{
  "name": "brand-navy",
  "colors": { "primary": "#1F3A5F", "accent": "#E8A33D" }
}
```

`default` の残りのトークン・フォントはそのまま継承される。派生トークンを個別に上書きしたい場合（例: 表ヘッダだけ別の色にしたい）は、そのトークンをテーマ JSON に明示すればよい。

## 追加のしかた

1. 雛形を作る:
   - `python tools/new_theme.py <name>` … `default` の全トークンを写した自己完結テーマ
   - `python tools/new_theme.py <name> --extends accenture-purple` … 継承して差分だけ書く最小テーマ
2. `colors` / `fonts` を編集（最低限 `primary` / `accent` だけでも派生トークンが追随する）
3. **コントラストを確認する**: `python tools/check_theme.py <name>`（下記「コントラストの確認」参照）
4. `deck.json` の `meta.theme` に `<name>` を指定して再ビルドし、代表スライド（`title` / `bullets` / `table` / `matrix` など primary 地・強調色を使うタイプ）を `preview_deck.py` で目視確認する

### サンプルスライドから自動生成する

既存スライド（PPTX / HTML / PDF / 画像）から配色・フォントを抽出してテーマ JSON を作る:

```bash
python tools/theme_from_sample.py <sample-file> --name <name>
```

| 形式 | 抽出方法 | 追加依存 |
|---|---|---|
| `.pptx` `.pptm` | スライド内の**実使用色を面積重みで集計**＋文字フォント（最良品質） | なし |
| `.png` `.jpg` … | 主要色を量子化抽出 | pillow |
| `.pdf` | 先頭ページを描画して主要色＋埋め込みフォント名 | pymupdf |
| `.html` `.htm` | 宣言された `#hex`/`rgb()` と `font-family` を静的抽出（見出し要素を重み付け） | なし |

- 各形式から `background` / `text` / `primary` / `accent` とフォントを推定し、**共通の色演算で残りのトークンを導出**する（既存テーマに近い一貫した配色になる）。
- 自動推定なので、**出力レポートを確認して `colors`/`fonts` を微調整**すること。特に `primary` と `accent` は取り違えが起きやすく、候補が僅差の場合はレポートに「要確認」と出る。
- 依存導入: 画像=`setup_deps.py --pillow`、PDF=`setup_deps.py --pdf`。

## コントラストの確認

`check_theme.py` はテーマの主要な文字色/背景の組（`text`/背景、`heading_text`/背景、`muted`/背景、`accent`/背景、`on_primary`/`primary`、`accent_on_primary`/`primary`、`table_header_text`/`table_header_bg`、`code_text`/`code_bg`）の WCAG コントラスト比を表示し、4.5 未満（大文字・太字用途は 3.0 未満）を警告として列挙する。

加えて「面の視認性」（文字色ではなく塗り面同士のコントラスト）も確認する。`steps` / `matrix` / `cards` / `two_column` などの淡い箱（`surface`）がディスプレイの発色や輝度・彩度の違いによって背景に溶けて見えなくなることを防ぐためのチェックで、いずれも警告のみ（exit code には影響しない）:

| 組 | しきい値未満で警告 |
|---|---|
| `surface` / `background` | 1.18 未満 |
| `border` / `background` | 1.40 未満 |
| `highlight_fill` / `surface` | 1.08 未満 |

```bash
python tools/check_theme.py <theme名または JSON パス>
```

**注意**: `check_theme.py` は `primary`/`background` の組を検査対象に含まない。前述のとおり `primary` は見出し文字色としても直接使われるため、`check_theme.py` が「警告0件」でも `title` 等の見出しが読めない可能性が残る（特に背景が暗色のテーマ）。新しいテーマ、とくに `background` が暗色のテーマを作ったときは、`check_theme.py` に加えて必ず `preview_deck.py` で `title` / `table` / `matrix` / `cards` を目視確認すること。

exit 1 になるのは `text`/背景 のコントラストが 4.5 未満のときのみ（本文が読めなくなる致命的な組み合わせ）。他の警告はビルドを止めないが、新テーマを作ったら必ず確認する。

### `primary` が読みにくいときの対処（layout_overrides）

`preview_deck.py` で目視確認した結果、`background` が暗色で `primary` のコントラストが足りず見出しが読みにくいと分かった場合、**既定レイアウト（`templates/layouts/default.json`）の該当箇所を書き換える必要はない**。`text`/`background` は `check_theme.py` が exit 1 で保証する唯一の組み合わせなので、見出し文字色を `primary` から `text` に差し替えれば必ず読める色になる。このデッキ側の `meta.layout_overrides`（`deck-schema.md` 参照）で、影響する全領域を一括で上書きできる:

```json
{
  "meta": {
    "layout_overrides": {
      "title":            { "title": { "color": "text" } },
      "bullets":          { "title": { "color": "text" } },
      "two_column":       { "title": { "color": "text" }, "col_heading": { "color": "text" } },
      "table":            { "title": { "color": "text" } },
      "code":             { "title": { "color": "text" } },
      "quote":            { "text":  { "color": "text" } },
      "image":            { "title": { "color": "text" } },
      "image_text":       { "title": { "color": "text" } },
      "agenda":           { "title": { "color": "text" }, "body": { "active_color": "text" } },
      "steps":            { "title": { "color": "text" } },
      "matrix":           { "title": { "color": "text" }, "grid": { "heading_color": "text" } },
      "cards":            { "title": { "color": "text" }, "grid": { "heading_color": "text" } },
      "swimlane":         { "title": { "color": "text" } },
      "swimlane_legend":  { "title": { "color": "text" } }
    }
  }
}
```

この JSON をそのままそのテーマを使うデッキの `meta.layout_overrides` に追記すればよい（`layout_overrides` は既定値に深いマージされるので、他の項目には影響しない）。同梱テーマ（`default` / `accenture-purple`）では `primary` が濃色でこの対処は不要だが、独自の暗色テーマを使うデッキではこの差分を丸ごとコピーして使うことを想定している。`swimlane` の `group_fill`（レーン帯の背景。文字は `on_primary` で受けるため対象外）のように、この一覧に **含まれない `primary` 参照は塗り色（背景）であり文字色ではない**ため、そのままで問題ない。

## 更新で消えないようにする（配布時）

`new_theme.py` / `theme_from_sample.py` の既定の書き込み先は **`--dir` を明示 → 環境変数 `SLIDE_DECK_THEMES` → カレントディレクトリの `./themes/`** の順（プラグイン同梱ディレクトリには `--dir` で明示的に指定したときだけ書き込む。実行するとどこに書いたか・ビルダーがどの順で探すかを標準出力に表示する）。カレントディレクトリの `./themes/` はプラグイン更新の影響を受けないので、既定のままで十分安全に永続化される。

さらに複数デッキ・複数プロジェクトで使い回したい場合は、環境変数で専用ディレクトリを指定する:

```bash
# 例: ホーム配下に置き、環境変数で常時探索させる
export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"     # Windows: setx SLIDE_DECK_THEMES "%USERPROFILE%\.slide-deck-themes"
python tools/new_theme.py brand-navy   # → $SLIDE_DECK_THEMES/brand-navy.json
```

ビルダー（`build_deck.py`）自体のテーマ探索順は **`SLIDE_DECK_THEMES` → `<deck_dir>/themes/` → 同梱 `templates/themes/`** の順（変更なし）。プロジェクトに `themes/<name>.json` を置く方法でも自動で拾われる。

## PowerPoint の「テーマの色」との関係

PPTX 生成時、OOXML テーマ（`theme1.xml`）の配色・フォントスキームにも `deck.json` のテーマトークン（`text` / `background` / `primary` / `surface` / `accent` / `highlight_fill` / `muted` と `fonts.heading` / `fonts.body`）を反映する。ただし各シェイプの塗りは従来どおり RGB 直書きのため、PowerPoint の「デザイン」タブでテーマカラーを差し替えても見た目は変わらない（見た目を変えたい場合は deck.json のテーマを変えて再ビルドする）。

## 同梱テーマ

| 名前 | 概要 |
|---|---|
| `default` | すべてのベース（青系） |
| `accenture-purple` | 紫系（`primary #460073` / `accent #A100FF`） |

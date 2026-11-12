# テーマ（色・フォント）リファレンス

テーマは配色とフォントを定義する JSON。`deck.json` の `meta.theme` にテーマ名を指定して使う。
デッキ本文では色を hex 直書きせず、**テーマトークン名**（`primary` / `accent` 等）で指定する。テーマを切り替えるだけで全スライドの見た目が変わる。

## 仕組み: default をベースにマージ＋派生トークンの自動導出

- どのテーマも **`default` をベースにマージ**される。新しいテーマは**上書きしたいトークンだけ**書けばよく、書かなかったトークンは以下の優先順で決まる。
- `extends` を指定すると、`default` の代わりに任意のテーマを親にできる（例: ブランド色だけ変えた派生テーマ）。循環する `extends` はエラーになる。
- テーマの探索順は **`SLIDE_DECK_THEMES`（環境変数）→ `<deck_dir>/themes/` → デッキの親（3 階層上まで）の `themes/` → カレントディレクトリの `themes/` → 同梱 `templates/themes/`**。先に見つかったものが勝つ（`layouts/` `patterns/` も同じ規則。索引 [deck-schema.md](deck-schema.md) の「探索順」）。`decks/<名前>/deck.json` なら、プロジェクト直下の `themes/` や `decks/themes/` に置いたテーマも見つかる。
- テーマ名（`meta.theme`、テーマ JSON の `extends` / `alias_of`）は**名前だけ**（`/` `\` `:` を含むもの・絶対パス・先頭が `.` のものはエラー。任意のファイルを読まないため）。
- 色を 1 つも書いていない、または親（既定は `default`）と同じ値しか書いていないテーマは、導出し直さず親の色をそのまま継承する（`new_theme.py --extends default` の無変更のテーマは `default` と同じ見た目）。1 つでも色を変えたときだけ、書いていない派生トークンを自分の基本色から導出する。

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
| `muted`（未指定時） | `mix(text, background, 0.35)` から始め、`background` と `surface` の**両方の上で 4.5:1 以上**になるまで `text` 側へ寄せる（`new_theme.py` で作ったテーマが check_theme の muted/surface で NG にならない） |

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
| `primary` | 主要色。見出し帯・章扉・表ヘッダ・カードの塗りなどの**構造色（面の色）**。見出し・本文の**文字色には直接使われない**（既定レイアウトの文字色は `heading_text` / `text` / `accent` など。`default.json` に `"color": "primary"` は無い）。章扉・まとめ（`section` / `closing`）は `primary` を背景に敷き `on_primary` で文字を載せる。例外: `kpi` の数字（`body.value_color`）・`kpi_tree` の KPI の目標値（`body.value_color`）・`schedule` の矢羽根のうち `prep` / `ongoing` / `tbd` の文字（`chart.<variant>_color`）・`chart` の棒（`base_color`）は `primary` を直接使うので、`primary` が `background` に近い明度のテーマではこれらが読みにくい（`check_theme.py` の「実使用の組」の `primary / background` が 3.0 未満なら警告する） |
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

1. 雛形を作る（`--deck <deck_dir>` でそのデッキの `themes/` に作る。省略時の書き込み先は下記「テーマの置き場所」）:
   - `python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> --deck <deck_dir>` … `default` の全トークンを写した自己完結テーマ
   - `python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" <name> --extends acn-slide-master --deck <deck_dir>` … 継承して差分だけ書く最小テーマ
2. `colors` / `fonts` を編集（最低限 `primary` / `accent` だけでも派生トークンが追随する）
3. **コントラストを確認する**: `python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <name> --deck <deck_dir>`（下記「コントラストの確認」参照）
4. `deck.json` の `meta.theme` に `<name>` を指定して再ビルドし、代表スライド（`title` / `bullets` / `table` / `matrix` など primary 地・強調色を使うタイプ）を `preview_deck.py` で目視確認する

### サンプルスライドから自動生成する

既存スライド（PPTX / HTML / PDF / 画像）から配色・フォントを抽出してテーマ JSON を作る:

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/theme_from_sample.py" <sample-file> --name <name> [--deck <deck_dir>]
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

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <theme名または JSON パス> [--deck <deck_dir>]
```

`--deck` を付けると、`build_deck.py` と同じ探索（`<deck_dir>/themes/` とその親）でテーマを探す（付けないとカレントディレクトリ基準）。自分のデッキに作ったテーマは `--deck` で確かめる。

**ビルドが文字色を整える（`readable_pairs`）**: 濃い面・色つきの面の上の文字色は、「この地の上にこの文字色」の組としてレイアウト JSON の最上位 `readable_pairs`（`{タイプ名: [[領域, 文字色のキー, [地の色…]], …]}`。`"*"` は全タイプ）に書いてあり、ビルドは対比（WCAG）が 4.5:1 に足りないときだけ、**同じ色味のまま白か黒の側へ寄せる**（足りていれば元の色のまま）。既定の組: steps の「STEP n」、agenda の番号、matrix の強調象限、swimlane の成果物ラベル（と凡例）、section / title の title・subtitle・number・meta、statement の kicker、全タイプの `brand`（地は `"@ground"` = その文字が載る下地）。図解のノードの文字・アイコン・番号・タグ・チェック印、schedule の矢羽根のラベル、表の `tone` の文字（強調行・縞の行・ラベル列の塗りの上）も同じ規則で整う。
- 自作テーマの色の組み合わせが多少悪くても、これらの文字は読める濃さに寄る（`check_theme.py` の警告とは別。テーマ自体は直す）。
- **利用者が `style` / `meta.layout_overrides` に書いた値は動かさない**。背景（画像・色面）つきのスライドは、背景の側の `palettes` が文字色を決める。
- **レイアウト JSON に書いた色も調整される**。ブランド指定などで意図して低コントラストにしたいときは、(1) `meta.layout_overrides` / `style` に書く、(2) 使っているレイアウト JSON に `"readable_pairs": { "steps": [] }` と書いて該当タイプの組を空にする（配列は継承側で置き換わる）。形が違うと fail（「readable_pairs.steps は [[領域, 文字色のキー, [地の色…]], …] の配列にしてください」）。`_` で始まるキーはメモとして読み飛ばす。
  ```json
  { "name": "mine", "extends": "default", "readable_pairs": { "steps": [] }, "todo_bg": "#FFE4E6", "todo_color": "#9F1239" }
  ```
  これを `<deck_dir>/layouts/mine.json` に置き、`meta.layout: "mine"` で選ぶ（確認済み: `steps` の「STEP n」が調整されず元の色のまま、`check_layout.py` の contrast が 2.29:1 で出る。外すと調整されて 0 件）。
- 【要確認】の色も、レイアウト JSON の最上位 `todo_color` `todo_color_on_dark` `todo_bg`（`#RRGGBB`。違うと警告して既定の色）で変えられる（[deck-schema.md](deck-schema.md) の「根拠が無い箇所は…」）。

**主要な文字色/背景の組**（WCAG コントラスト比。4.5 未満、大文字・太字用途は 3.0 未満を警告）: `text`/背景、`heading_text`/背景、`muted`/背景、`accent`/背景、`on_primary`/`primary`、`accent_on_primary`/`primary`、`table_header_text`/`table_header_bg`、`code_text`/`code_bg`。**exit 1 になるのは `text`/背景 が 4.5 未満のときだけ**（本文が読めなくなる致命的な組み合わせ）。他の警告はビルドを止めないが、新テーマを作ったら必ず確認する。

**実使用の組**（警告のみ。実際のレイアウトで文字が載る組）:

| 組 | 基準 | 使われ方 |
|---|---|---|
| `primary` / `background` | 3.0 | 数字・棒など `primary` を文字色や図形に直接使う箇所（`kpi` の数字など） |
| `muted` / `surface` | 4.5 | 淡い箱の中の補足文字（14〜15px） |
| `accent` / `highlight_fill` | 3.0 | 強調象限の見出し（18px 太字） |
| `on_primary_soft` / `primary` | 4.5 | 濃色面のリード・本文 |
| `on_primary_muted` / `primary` | 4.5 | 濃色面の補足 |

**面の視認性**（塗り面同士。淡い箱がディスプレイの発色によって背景に溶けるのを防ぐ。警告のみ）:

| 組 | しきい値未満で警告 |
|---|---|
| `surface` / `background` | 1.18 未満 |
| `border` / `background` | 1.40 未満 |
| `highlight_fill` / `surface` | 1.08 未満 |

同梱テーマの警告（ブランド色のため色は動かしていない）: `accenture` は muted/surface 4.42・on_primary_soft/primary 4.44・on_primary_muted/primary 4.05、`acn-technology-graphik` は accent/highlight_fill 2.93。`default` は警告 0 件（`muted` は `#566781`）。

### 暗色テーマを作るとき

見出し・本文の文字色は `heading_text` / `text` で、`heading_text` は `background` 上で読めるよう**自動調整される**（暗い背景なら白側へ寄る）。したがって `primary` が暗色背景に近い明度でも、見出しが背景に溶ける問題は起きない。`layout_overrides` で文字色を差し替える必要はない。ただし:

- `check_theme.py` が警告 0 件でも、`preview_deck.py` で `title` / `table` / `matrix` / `cards` / `kpi` / `chart` を目視する。
- `primary` を面の色に使う箇所（表ヘッダ、章扉）は `on_primary` 系で文字が載るので、`on_primary`/`primary` の警告を直す。
- 画像（SVG / PNG）はテーマに自動追従しない。暗色テーマで白背景の図版を使うと浮く。

## テーマの置き場所（更新で消えないようにする）

`new_theme.py` / `theme_from_sample.py` の書き込み先は **`--dir`（明示）→ `--deck <deck_dir>`（そのデッキの `themes/`）→ 環境変数 `SLIDE_DECK_THEMES` の先頭 → カレントディレクトリの `./themes/`** の順。プラグイン同梱ディレクトリには `--dir` で明示したときだけ書き込む。実行すると「書き込み先」「どのデッキから見つかるか」「探索順」を表示する。

ビルダーの探索順（上記）はこれらを全部拾うので、既定の出力先で作ったテーマはそのまま見つかる。ただし `./themes/`（カレント）が見つかるのは、**ビルドを実行するカレントディレクトリが同じとき**だけ（別の場所からビルドすると見つからない）。確実なのは **`--deck <deck_dir>`**（そのデッキ専用）か、デッキの親（3 階層以内）の `themes/`。作成時に表示される「見つかるデッキ」で確かめる。

複数デッキ・複数プロジェクトで使い回したい場合は、環境変数で専用ディレクトリを指定する:

```bash
export SLIDE_DECK_THEMES="$HOME/.slide-deck-themes"     # Windows: setx SLIDE_DECK_THEMES "%USERPROFILE%\.slide-deck-themes"
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" brand-navy   # → $SLIDE_DECK_THEMES/brand-navy.json
python "${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py" brand-navy --deck <deck_dir>   # → <deck_dir>/themes/brand-navy.json
```

`theme_from_sample.py` が出力するテーマ JSON は基本色（`background` `text` `primary` `accent` `on_primary`）とフォントだけ。`surface` `muted` `table_header_bg` などは読み込み時に同じ式で導出される。

## PowerPoint の「テーマの色」との関係

PPTX 生成時、OOXML テーマ（`theme1.xml`）の配色・フォントスキームにも `deck.json` のテーマトークン（`text` / `background` / `primary` / `surface` / `accent` / `highlight_fill` / `muted` と `fonts.heading` / `fonts.body`）を反映する。ただし各シェイプの塗りは従来どおり RGB 直書きのため、PowerPoint の「デザイン」タブでテーマカラーを差し替えても見た目は変わらない（見た目を変えたい場合は deck.json のテーマを変えて再ビルドする）。

## テーマ JSON の構成

| トップキー | 内容 |
|---|---|
| `name` / `label` / `description` | 名前（ファイル名と合わせる）・表示名・説明 |
| `colors` | 色トークン（上記 18 種。書いたものだけ上書き、残りは親から継承か導出） |
| `fonts` | `heading` / `body` / `code`（文字列か文字列の配列） |
| `extends` | 親テーマ名（省略時 `default`）。循環はエラー |
| `alias_of` | 別名（旧名の互換用） |
| `shape` | 形のプリセット名（`classic` / `sharp` / `soft` / `editorial` か登録した shape）。`meta.shape` が優先。省略可。`new_theme.py <名前> --shape soft` で書いた雛形ができる |
| `tokens` | 形のトークン（角丸・線・太さ・字間・文字サイズの段・影）の差し替え。shape より後に重なる。省略可 |
| `layout` | トークンで表せない領域ごとの値の差分（`common` / `types` / `densities` / `variants` / `palettes` / `variant_defaults`。`default.json` と同じ形）。例: 強調カードの色 `types.cards.grid.emph_*`。省略可 |

未知のトップキーは警告される（`colors` の中の標準でない名前も「もしかして」つきで警告）。テーマ JSON の検査（`#RRGGBB` でない色、空のフォント名、フォント名に使えない文字、`tokens` / `layout` の型・範囲・タイプ名・領域名の誤りなど）は[検証](schema/validation.md)と `check_theme.py` が行う。形のトークンの意味は次の節。

## 形（shape）とトークン

色のテーマ（`meta.theme`）とは独立に、資料の「形」（角丸・罫線・見出しの太さと字間・箱の影）を `meta.shape` で選べる。選び方は `meta.shape` → テーマ JSON の `"shape"` → `classic`。何も指定しなければ `classic`（従来の見た目のまま）。どのテーマとも組み合わせられる。文字量・構成は変わらないので、shape を替えても自動フィットで収まる。同じ 7 枚を 4 つの shape でビルドして見比べられる見本が `examples/shape-gallery/`（`classic` / `sharp` / `soft` / `editorial` の 4 フォルダ）。

| shape | 見た目 | 合う資料 |
|---|---|---|
| `classic` | 12〜14px の角丸の箱、タイトル下に全幅のアクセント罫線（5px）。標準 | 迷ったらこれ |
| `sharp` | 角丸なし。タイトル下は細い全幅の罫線（2px）。見出しは太さ 800・字間をわずかに詰める | 経営会議・監査・コンサル報告・規程など、硬く正確な印象 |
| `soft` | 大きめの角丸（箱 20〜24px）、箱に淡い影、箱の枠線なし。タイトル下は短い丸い帯 | 研修・社内共有・サービス紹介・採用など、親しみやすさ |
| `editorial` | 見出しを大きく軽く（40px・太さ 500）、タイトル左に細い縦帯、eyebrow は小さな大文字。箱は小さな角と細い枠 | 提案・ブランド紹介・講演・ホワイトペーパーなど、落ち着いた誌面風 |

目安: 数字と表が中心 → `sharp`／説明・手順が中心で初見の人が読む → `soft`／文章と図が中心で見せ方に気を配る → `editorial`／分からない → `classic`。

### トークン（`$グループ.名前`）

レイアウト JSON 最上位の `tokens`（`templates/layouts/default.json`）が既定値（= classic）。領域の値から `"$radius.card"` の形で参照でき、`style` / `meta.layout_overrides` にも書ける（未知の名前は候補つきで fail）。パターンの `$type.h1` なども同じ表を読む。

| グループ | 名前（classic の値） | 効く場所 |
|---|---|---|
| `radius`（px） | `card` 12 / `panel` 14 / `box` 0 / `node` 10 / `node_sm` 8 / `small` 6 / `tiny` 3 / `pill` 999 / `image` 0 / `rule` 0 / `cell` 0 | card = cards・steps・matrix の箱、panel = two_column・code・kpi の面、box = 提案書系と結論帯、node = 図解のノード、pill = 丸薬形（0 で四角）、cell = パターンの面 |
| `line`（px） | `rule` 5 / `rule_lg` 6 / `border` 1 / `node` 1.5 / `edge` 2 / `thin` 1 / `normal` 2 / `bold` 4 ほか | rule = 見出しの罫線、border = 箱の枠線（0 で枠なし）、node・edge = 図解 |
| `rule` | `style` "line" / `length` 96 / `gap` 14 | `line`（全幅）/ `short`（短い太い帯）/ `none` / `bar-left`（タイトル左の縦帯） |
| `weight` | `heading` 700 / `label` 700 / `body` 400 / `eyebrow` 700 | font-weight。PPTX は 600 以上が太字、未満は太字なしの 2 値 |
| `tracking`（em） | `heading` 0 / `eyebrow` 0 / `body` 0 | 字間（-0.2〜0.6） |
| `type`（px） | `display` 60 / `h1` 36 / `h1_min` 28 / `h2` 28 / `h3` 22 / `body` 20 / `small` 16 / `caption` 13 / `eyebrow` 15 / `lead` 20 | `h1` = 各タイプのタイトル、`h1_min` = その縮小の下限（タイトルに `"size": "$type.h1", "min_size": "$type.h1_min"` と書けば、h1 を替える shape にも追随する） |
| `space` / `shadow` / `case` | `gap` 16・`pad` 18 / `card` "none"（"soft" で影）・`dy` 4・`blur` 14・`alpha` 0.12 / `eyebrow` "none"（"upper" で大文字） | パターン用の間隔／箱の影／eyebrow の大文字化 |

`tokens` とは別に、レイアウト JSON の領域には自動調整のしきい値（中身が少ないときに大きくする `thin_*` / `fill_*`、語の途中で折れる文の `common.wrap`、`meta.brand` の `common.brand.clear_gap` など）がある。表と止め方は [schema/autofit.md](schema/autofit.md) の「中身が少ないときの自動調整」「語の途中で折れる文は、文節の切れ目で折る」にまとめてあり、範囲外・型違いはキー名つきでビルドが止まる。

解決順: レイアウト既定（tokens と値）→ **shape** → **テーマ JSON の tokens / layout** → density → `meta.layout_overrides` → `slide.style` → 自動フィット。**利用者が `style` / `layout_overrides` に書いた値が常に最優先**（トークンも数値も書ける）。利用者が `bold` を書き `weight` を書かなかったときは `bold` が勝つ（`bold: true` で editorial の軽い見出しも太字にできる）。

### shape を選ぶ・作る

- 一覧と検証: `python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" --shapes [--deck <deck_dir>]`（探索先・同梱と登録済みの一覧と検証。エラーがあれば exit 1）。テーマ JSON の `shape` / `tokens` / `layout` は `check_theme.py <テーマ> [--deck …]` が同じ検査をする。
- 探索先（先に見つかったものが勝つ）: 環境変数 `SLIDE_DECK_SHAPES` → `<deck_dir>/shapes/` → デッキの親 3 階層の `shapes/` → カレントの `shapes/` → 同梱 `templates/shapes/`。名前はパス区切り・先頭ドットを含められない。
- 自作は `<deck_dir>/shapes/<名前>.json` を手で書く（雛形を作るコマンドは無い。同梱の `templates/shapes/*.json` をコピーして直すのが早い）:

```json
{ "name": "my-shape", "label": "自社の形", "description": "どんな資料向けか 1 行",
  "tokens": { "radius": { "card": 6, "panel": 6, "box": 6, "node": 6, "pill": 6 }, "line": { "rule": 3 },
              "rule": { "style": "short", "length": 64 }, "weight": { "heading": 600 } },
  "layout": { "types": { "title": { "bar": { "w": 8 } } } } }
```
  `tokens` は差し替えたい名前だけ（書かなかった名前は classic の値。無い名前は候補つき警告、型・範囲違いは fail）。`layout` は `default.json` と同じ形で、`variants` / `palettes` / `variant_defaults` も書ける（例: 表紙の既定を `left-band` に）。色キーはテーマの色トークン名か `#RRGGBB`。
- テーマに形を持たせる: `new_theme.py <名前> --shape soft`（テーマ JSON に `"shape"` を書く）。

### 既知の制約

- 表（`table` / `status_table`）の角は shape に関わらず四角のまま。soft の影は cards・steps・matrix・two_column の箱、kpi のタイル、summary の箱、型の面に付く（house の柱は枠のまま）。
- sharp（`pill` = 0）では、`lifecycle` の start ノードが process ノードと形で区別できないため、枠線を太くして区別する（`diagram.start_border_w_sharp` 3.5。classic / soft / editorial は従来どおり）。
- editorial の eyebrow は大文字になる。識別子・ファイル名を eyebrow に書くときは `"style": {"eyebrow": {"case": "none"}}`（スライドごと）で元の綴りに戻す。
- 手書きの `canvas` は shape の影響を受けない。PPTX は太さが 2 値。PowerPoint 実機での影のぼかしの見え方は未確認。

## 同梱テーマ

| 名前 | 概要 |
|---|---|
| `default` | すべてのベース（青系） |
| `accenture` | Accenture MasterBrand に寄せた配色（白地・黒の文字、鮮やかな紫 `primary #A100FF` の章扉、黒の表見出し） |
| `acn-slide-master` | Accenture 2026 年版スライドマスターに寄せた配色（濃い紫 `primary #460073` / `accent #A100FF`、淡い紫の面）。旧 `accenture-purple` |
| `acn-technology-graphik` | Accenture Technology テンプレートに寄せた配色（黒 `primary #000000` の章扉・見出し帯、紫の強調、温かみのある灰の面） |
| `accenture-purple` | 旧名。`acn-slide-master` の別名（`alias_of`）として読める。設定フォームの選択肢には出ない |

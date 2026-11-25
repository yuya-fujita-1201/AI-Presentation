# deck.json スキーマリファレンス（v2: パラメーター駆動）

デッキは `<deck_dir>/deck.json` の 1 ファイルで管理する。**内容（コンテンツ）とデザイン（パラメーター）を分離**しており、デザインの微修正は JSON の数値を変えるだけで行える。AI に再生成させる必要はない。

**このファイルは索引**。座標系・3層構造・`meta`・全タイプ共通のオプション・タイプ一覧表・文字量の目安・ビルドの手順だけを持つ。各タイプのキー・例・注意は下の「タイプ一覧表」から**使うタイプのファイルだけ**開いて読む（新規デッキの典型は、この索引＋[schema/basic.md](schema/basic.md)で約 3.2 万字）。**索引は「タイプ一覧表」の終わりまで読めば足りる**。「文字量・要素量の目安」は項目数に迷うとき、「ビルドとプレビュー」はコマンドを確かめるときに開く。

```json
{
  "meta": { ... },
  "slides": [ { "type": "...", ..., "style": { ... } }, ... ]
}
```

## パスの書き方（`references/` 全体で共通）

- `${CLAUDE_PLUGIN_ROOT}` はプラグインのディレクトリ（このリポジトリ内で直接動かすときは `plugins/slide-deck`）。スクリプトは `python "${CLAUDE_PLUGIN_ROOT}/tools/<スクリプト名>.py"` の形で実行する。
- 文中の `tools/…` `templates/…` `references/…` は、すべて上のディレクトリからの相対パスの略記。`<deck_dir>` は deck.json があるフォルダ。

## 読むファイルの選び方

| 作るもの・知りたいこと | 読むもの |
|---|---|
| 通常のデッキ（表紙・箇条書き・表・カード・ステップ・まとめなど） | この索引 ＋ [schema/basic.md](schema/basic.md) |
| 大きな数字（成果・KPI）、推移・比較・内訳のグラフ | ＋ [schema/visual.md](schema/visual.md) |
| 登録した構図（パターン。同梱 19 個の一覧・PPTX からの型起こし） | ＋ [schema/pattern.md](schema/pattern.md) |
| 1 枚に図・要点・数字を並べる（`composite`）、色面や画像のパネル＋本文（`split`） | ＋ [schema/composite.md](schema/composite.md) |
| 主役のページ（表紙・章扉・言い切りの `variant` と `background`、cards の強弱、画像を端まで） | ＋ [schema/hero.md](schema/hero.md) |
| 業務フロー | ＋ [schema/swimlane.md](schema/swimlane.md) |
| 構成図・データフロー・状態遷移・シーケンス図（凡例ページ・配線の診断を含む） | ＋ [schema/diagram.md](schema/diagram.md)（作図の規約は [diagram-guide.md](diagram-guide.md)） |
| 工程表・ガント | ＋ [schema/schedule.md](schema/schedule.md) |
| 提案書の定型ページ（要旨・選ばれる理由・体制図・全体像・KPI ツリーなど） | ＋ [schema/proposal.md](schema/proposal.md) |
| 既存 PowerPoint の取り込み（`canvas`） | ＋ [schema/canvas.md](schema/canvas.md) |
| 文字が小さくなった・「縮めても収まらない」警告が出た（自動フィットの規則） | [schema/autofit.md](schema/autofit.md) |
| ビルドの警告・エラーの意味を知りたい | [schema/validation.md](schema/validation.md) |
| テーマ（配色・フォント）の追加・確認 | [themes.md](themes.md) |
| 話の組み立て・タイトルの書き方・根拠の置き方 | [content-guide.md](content-guide.md) |

`style` で動かせる領域とプロパティは、各タイプの「領域:」行と `templates/layouts/default.json` にある。

## 座標系

- 仮想キャンバスは **1280 × 720 px（16:9）**。すべての位置・サイズ・フォントを px で指定する
- HTML は px をそのまま使い、PPTX は 96dpi で換算（px ÷ 96 = インチ、px × 0.75 = pt）する。座標・配色・フォントサイズの指定は共通ソース（テーマ＋レイアウト＋ deck.json）から解決されるため、HTML と PPTX の大枠のレイアウトは一致する（フォントの実体・画像の等比フィット・一部の図形表現などレンダラ由来の細部差は残る）
- **左右マージンは 72px、コンテンツ幅は 1136px** に統一されている（`title` / `section` / `bullets` / `table` など全タイプ共通のグリッド基準）。新しい領域を `style` で追加するときもこの基準に揃えると崩れにくい

## デザインの3層構造

| 層 | ファイル / キー | 役割 |
|----|----------------|------|
| テーマ | `templates/themes/<名前>.json` | 色トークンとフォント。`meta.theme` で選択（[themes.md](themes.md)） |
| レイアウト既定値 | `templates/layouts/default.json` | スライドタイプごとの全オブジェクト（領域）の位置・サイズ・フォント。密度ごとの差分（`densities`）も持つ |
| オーバーライド | `meta.layout_overrides`（デッキ全体）/ `slides[i].style`（スライド個別） | 既定値への差分だけを書く |

解決順: **レイアウト既定値 ← 密度（`density`）のプリセット ← meta.layout_overrides ← slides[i].style**（後勝ち・deep merge）。そのあとに自動フィットが、**書いていない値だけ**を内容に合わせて縮める。**利用者が `style` / `layout_overrides` に書いた値は、自動フィットも密度も動かさない。**

全スライド共通の領域として `common.brand`（右上のブランド表記）があり、`meta.layout_overrides.common.brand` で全デッキ共通の位置・サイズを調整できる（3層構造の対象）。

### 文字量に合わせた調整は自動フィットがやる（`style` で手詰めしない）

内容に合わせて文字サイズ・列幅・行の高さ・箱の高さを決めるのは自動フィット（`tools/autofit.py`）。レイアウト既定値を「上限」にして、収まらないときだけ縮める。既定で収まる内容は見た目が変わらない。
警告が出たら、まず内容（項目数・文の長さ・分割）を直す。`style` で大きさを書くのは、見た目を具体的に指示されたときと、内容を直しても警告が消えないときだけ。規則・下限・警告の意味は [schema/autofit.md](schema/autofit.md)。

### 微修正の例

```jsonc
// 5枚目のタイトルだけ 4px 下げて 40px にする
"slides": [ ..., { "type": "bullets", "title": "...",
  "style": { "title": { "y": 46, "size": 40 } } } ]

// このデッキ全体で箇条書きの本文を少し小さくする
"meta": { "layout_overrides": { "bullets": { "body": { "size": 22 } } } }
```

領域（`title`, `body`, `table` など）の名前と既定値は `templates/layouts/default.json` を見るのが早い（最上位の `tokens` は形のトークン `$radius.card` など、`variants` / `palettes` は主役のページの値、`readable_pairs` は「この地の上にこの文字色」の組で、足りない対比をビルドが自動で整える（[themes.md](themes.md)）、`todo_color` / `todo_color_on_dark` / `todo_bg` は【要確認】の強調の色、`densities` は密度ごとの差分）。共通プロパティ: `x` `y` `w` `h`（px）、`size`（フォントpx）、`color` / `fill`（テーマトークン名 or hex 直書き）、`bold`、`align`（left/center/right）、`valign`（top/middle/bottom）、`line_height`、`gap`（箇条書き間隔）など。

## meta

| キー | 必須 | 説明 |
|------|------|------|
| `id` | 省略可 | デッキ ID（出力ファイル名になる）。省略時はフォルダ名を使う。指定する場合は `\ / : * ? " < > \|` と制御文字を含められない（ファイル名として不正なため） |
| `title` | ✅ | デッキタイトル（フッターにも表示）。無い・空だと警告（ビルドは続く）。HTML の `<title>` と PPTX の文書プロパティは、`meta.title` → `meta.id` → 先頭スライドの `title` → フォルダ名の順で最初に見つかったものを使う |
| `subtitle` / `author` / `date` | | 補足情報。`author` は PPTX の作成者・最終更新者になる（無ければ空） |
| `theme` | | テーマ名（省略時 `default`）。名前だけを書く（パス区切りは不可）。同梱: `default` / `accenture` / `acn-slide-master` / `acn-technology-graphik`（旧名 `accenture-purple` は `acn-slide-master` の別名）。自作テーマも下記「探索順」で見つかる。**絶対パスは書けない**（ビルドエラー。`<deck_dir>/themes/` などに置いて名前で指定する） |
| `layout` | | レイアウト名（省略時 `default`）。名前だけを書く（`theme` と同じく絶対パスは不可）。`extends` で差分だけ書ける（下記） |
| `layout_overrides` | | デッキ全体のレイアウト調整（タイプ名 → 領域 → プロパティ）。`common.brand` も指定可 |
| `density` | | 密度。`"talk"`（映して話す。大きく少なく）/ `"standard"`（既定）/ `"read"`（配って読ませる。小さめ・密）。それ以外はビルドエラー。スライドの `density` で 1 枚だけ上書きできる。**表が 7 行以上・5 列以上なら `read` を勧める**。値の中身は [schema/autofit.md](schema/autofit.md) |
| `autofit` | | 自動フィットの全体スイッチ（既定 `true`）。`false` で文字サイズ・列幅・行高を変えず、中身が少ないときの拡大もしない（あふれの警告だけ出る）。スライドの `autofit: false` でそのスライドだけ切れる。真偽値以外はビルドエラー。止まる範囲と止まらないものは [schema/autofit.md](schema/autofit.md) |
| `brand` | | 全スライド右上に表示する短いブランド表記（例: `ACME`）。アクセント色・太字・右寄せ。右上の箱は既定で幅 140px・文字 23px なので、**目安は全角 6 字まで・半角は小文字なら 9 字ほど（大文字が多いと 7 字ほど）**。1 行に収まらないとビルドが 1 回警告する（直し方: 短くする／`layout_overrides.common.brand` で `w` を広げ `x` を同じだけ左へ／`size` を下げる）。brand を付けると、タイトルの右端を brand の文字の左端から 24px 手前（`common.brand.clear_gap`）までに狭める（長いタイトルはその幅で折れ、縮められる。PPTX のタイトル枠も同じ幅になる）。1 行に収まる下限まで縮めても入らない長さ（目安 44 字）は「タイトルを短くする」警告。`style.title.w` を書いたときは動かさない。status_table は凡例も同じだけ狭める。暗い地の章扉・結びでは brand の文字色が地に合わせて自動で変わる |
| `as_of` | | 資料の基準日（`"YYYY-MM"` か `"YYYY-MM-DD"`）。`lint_deck_text.py` の日付チェック（基準日より後の「実績」・基準日より前に始まる計画）に使う。省略時は `date`、それも無ければ今日の日付 |
| `shape` | | 形のプリセット（角丸・罫線・太さ・字間・箱の影）。`classic`（既定。従来の見た目）/ `sharp` / `soft` / `editorial`、または登録した shape。色の `theme` とは独立で、どの組み合わせでもよい。テーマ JSON の `"shape"` より `meta.shape` が優先。選び方・自作は [themes.md](themes.md) の「形（shape）とトークン」 |
| `variants` / `section_numbers` | | 主役のページの既定。`variants` は `{"title": "left-band", "section": "number"}` のようにタイプ別の variant の既定、`section_numbers: true` は `number` を書いていない section に `1` `2` … を振る（[schema/hero.md](schema/hero.md)） |
| `todo_marks` | | `false` で `【要確認】` の強調表示（HTML の下地・PPTX の色と太字）を止める。既定は `true`。一覧の note は出る。真偽値以外はビルドエラー（下記「根拠が無い箇所は…」） |
| `line_balance` | | `false` で泣き別れ対策（最終行が1〜2文字になる文への自動改行）をデッキ全体で止める。既定は有効 |

`meta` の未知のキーは警告される（先頭が `_` のキーはメモ用として無警告）。

### テーマ・レイアウト・パターンの探索順

`meta.theme` / `meta.layout` / パターン名は、次の順に探す（先に見つかったものが勝つ。同じ規則を `build_deck.py` / `check_theme.py` / `new_theme.py` / パターンの読み込みが使う）。

1. 環境変数（`SLIDE_DECK_THEMES` / `SLIDE_DECK_LAYOUTS` / `SLIDE_DECK_PATTERNS`。OS のパス区切りで複数可）→ 2. `<deck_dir>/themes/`（`layouts/` `patterns/`）→ 3. デッキの親（3 階層上まで）の同名フォルダ（`decks/<名前>/deck.json` ならプロジェクト直下の `themes/` も見つかる）→ 4. カレントディレクトリの同名フォルダ（`new_theme.py` の既定の書き込み先 `./themes/`）→ 5. 同梱 `templates/`。

同梱以外（1〜4）から、**同梱と同じ名前**のテーマ・レイアウト・型・形を読んだときは、ビルドが note を 1 行出す（「テーマ 'acn-slide-master' は同梱のものではなく <パス> を読みました」。探索順で先に見つかったほうが使われるため、意図していなければそのファイルを別の名前にするか移す）。

レイアウト JSON は `extends`（省略時は `default`）で土台を継承するので、変えたいタイプ・領域・プロパティだけ書けばよい。循環はエラー。見つからないときは「使える名前」と探索先が表示される:
```json
{ "name": "tall-title", "extends": "default", "types": { "bullets": { "title": { "size": 40 } } } }
```
テーマの作り方・確認は [themes.md](themes.md)。

## slides — スライドタイプ一覧

全タイプ共通のオプション: `notes`（スピーカーノート。**HTML でのみ表示**、N キーで開閉。PPTX には出力されない）、`style`（レイアウトオーバーライド）、`relation`、`line_balance`、`density`、`autofit`。提案書向けタイプ・`kpi`・`chart` では結論の帯 `conclusion` と出典の行 `source` も使える（書式は下記「結論の帯と出典」。タイプごとの注意は [schema/proposal.md](schema/proposal.md)）。スライド直下の `null` は「書いていない」とみなされる。

- `relation`（任意）: そのスライドで見せる内容の関係。描画には使わず、`lint_deck_text.py` がタイプとの不一致を警告する。値と合うタイプ: `parallel`（並列）→ cards / bullets / two_column / table / matrix / image_text / status_table / summary / row_matrix / house / kpi、`sequence`（順序）→ steps / swimlane / schedule / sequence / dataflow / agenda / row_matrix、`flow`（流れ）→ dataflow / swimlane / steps / sequence / architecture、`hierarchy`（階層）→ architecture / bullets / table / org / house / kpi_tree、`cause`（因果）→ steps / dataflow / two_column / bullets / reasons、`contrast`（対比）→ two_column / table / matrix / status_table / reasons / row_matrix / chart、`cycle`（循環）→ lifecycle / cycle
- `line_balance`（任意）: `false` でそのスライドの泣き別れ対策を止める。既定では `title` / `subtitle` / `lead` / `punch` / `message` と箇条書き（bullets / closing / image_text / two_column）の最終行が1〜2文字になるとき、ビルド時に文節の切れ目（助詞・読点の後など）で改行を入れる（36px 以上の大きな文字は、表紙・章扉・言い切り・引用も語の途中で切らない。規則は [schema/autofit.md](schema/autofit.md) の「折り返しの規則」）。改行（`\n`）を書いてある文字列は触らない
- `density` / `autofit`（任意）: そのスライドだけ密度を変える（`talk` / `standard` / `read`）、自動フィットを切る（`false`）。デッキ全体の指定は `meta` の同名キー

`eyebrow`（タイトル上の小さなサブタイトル。15px・アクセント色・太字。章や系列の目印に使う）は、見出し（`chrome()`）を持つほぼ全タイプで指定できる: `bullets` / `two_column` / `table` / `code` / `image` / `image_text` に加え `agenda` / `steps` / `matrix` / `cards` / `swimlane` / `architecture` / `dataflow` / `lifecycle` / `sequence` でも使える（`title` / `section` / `quote` / `closing` のような固有レイアウトのタイプは対象外）。

ページ番号を消したい/変えたいスライドは `style.footer_r.text` に表示文字列を指定する（空文字は不可。既定はページ番号）。

### 根拠が無い箇所は `【要確認】` と書く

材料（口述・メモ・既存資料）に無い数字・固有名詞・日付・出どころは**作らない**（作ると、それが事実として配られるため）。文字列の中に `【要確認】` または `【要確認: 何を確かめるか】`（コロンは全角・半角どちらでも可）と書く。タイトル・リード・箇条書き・表のセル・グラフの注記・`notes`・`meta` のどこにも書ける。
ビルドは、画面に出る文字の中の `【要確認】` を **HTML では黄色い下地＋濃い茶の太字（`<mark class="todo">`）、PPTX では濃い茶（暗い地の上では明るい黄）の太字**にして目立たせる。bullets・表・cards・図解のノード・kpi・chart の注釈・パターンのスロット・合成スライドのブロック・split のパネル、どこに書いても効く。折り返しで割れても行ごとに強調される。`notes` と `code` の中は強調しない（notes は PPTX に出ない）。
さらにビルドの最後に `note: 要確認が 5 件あります（1 枚目 2 件（経理に確認）、4 枚目 1 件、…）→ 根拠を確かめて文を確定し、マーカーを消す` と、枚ごとの件数と確かめる点を一覧にする。強調だけを止めるときは `meta.todo_marks: false`（一覧の note は出る）。色を変えるときは、レイアウト JSON の最上位 `todo_color`（明るい地の上の文字）・`todo_color_on_dark`（暗い地の上の PPTX の文字）・`todo_bg`（HTML の下地）に `#RRGGBB` で書く。
`lint_deck_text.py` は `notes` も含めて件数と一覧（スライド番号・項目つき）を出し、`--fail-on-todo` で 1 つでも残っていれば exit 1 にする。引き渡しのときは件数と一覧を必ず報告し、確認が済んだものからマーカーを消す。強調はあくまで目印で、残ったまま配られてよいわけではない。

### タイプ一覧表

`slides[i].type` に書ける値と、詳細を書いたファイル。**伝えたいこと（主張の種類）から合うタイプを引く**表で、タイプ名は `templates/layouts/default.json` の `types` のキーと一致する。タイプを足したときは 1 行足す。

| 伝えたいこと | タイプ | 向く内容・特徴 | 詳細 |
|---|---|---|---|
| 表紙 | `title` | タイトル・サブタイトル・日付など（`variant` / `background` で主役の表紙に） | [schema/basic.md](schema/basic.md) |
| 章の区切り | `section` | 章扉（番号＋章タイトル。`variant` / `background` で大きな章番号や写真つきに） | [schema/basic.md](schema/basic.md) |
| 目次・全体の流れ | `agenda` | 連番・現在地の強調・自動 2 段／ページ繰り越し | [schema/basic.md](schema/basic.md) |
| 要点を並べる | `bullets` | 箇条書き（子項目・項目単位の強調可。3〜6項目） | [schema/basic.md](schema/basic.md) |
| 並列の要素を整理する | `cards` | ボックスチャート・カードグリッド（見出し＋本文＋箇条書き。3〜6枚。`emphasis` / `span` で主役のカードを作れる） | [schema/basic.md](schema/basic.md) |
| 2 案の比較・対比 | `two_column` | 左右の箱（`connector` で矢印） | [schema/basic.md](schema/basic.md) |
| 項目 × 複数案の比較・一覧 | `table` | 表（URL 自動リンク・行見出し・合計行・行の強調・セルの意味づけ） | [schema/basic.md](schema/basic.md) |
| 観点 × 対象の整理（フェーズ別の実施事項など） | `row_matrix` | 行見出し × 列の整理表 | [schema/proposal.md](schema/proposal.md) |
| 2 軸での位置づけ・優先度の散布 | `matrix` | 2×2（4 象限・軸ラベル・点の散布） | [schema/basic.md](schema/basic.md) |
| 手順・工程（単純な直線） | `steps` | 横並びカードをシェブロンで接続 | [schema/basic.md](schema/basic.md) |
| 業務フロー（役割をまたぐ） | `swimlane` | レーン × 工程のグリッドに自動配線 | [schema/swimlane.md](schema/swimlane.md) |
| 日程・工程表 | `schedule` | 矢羽根スケジュール（ガント。日付だけ書けば位置は自動） | [schema/schedule.md](schema/schedule.md) |
| 進捗報告 | `status_table` | 信号＋実績／計画（PowerPoint のネイティブ表） | [schema/basic.md](schema/basic.md) |
| システムの構成・連携 | `architecture` | `type` でアイコンの形、`groups` で境界 | [schema/diagram.md](schema/diagram.md) |
| データの流れ | `dataflow` | 工程の列見出し・データ区分つきの矢印 | [schema/diagram.md](schema/diagram.md) |
| 状態の遷移 | `lifecycle` | `kind` で状態の性質を描き分け | [schema/diagram.md](schema/diagram.md) |
| 呼び出し・やり取りの順序 | `sequence` | 参加者のライフラインとメッセージ | [schema/diagram.md](schema/diagram.md) |
| （図解の凡例） | `diagram_legend` | 図解スライドに `legend_page: true` で自動挿入。直接は書かない | [schema/diagram.md](schema/diagram.md) |
| 数字を主役にする（成果・KPI・進捗） | `kpi` | 1〜4 個の大きな数字（変化前→後・増減・進捗バー） | [schema/visual.md](schema/visual.md) |
| 推移・比較・内訳をグラフで見せる | `chart` | 棒・横棒・積み上げ・折れ線・ウォーターフォール・ドーナツ（ネイティブ図形） | [schema/visual.md](schema/visual.md) |
| 冒頭で要旨を示す | `summary` | 番号の箱＋要点＋説明の行 | [schema/proposal.md](schema/proposal.md) |
| 課題 × 強みを対応させる | `reasons` | 選ばれる理由 | [schema/proposal.md](schema/proposal.md) |
| 物語の転換点で言い切る | `statement` | 濃色の全面に大きな一文（デッキに 2〜3 枚まで。`variant` / `background` あり） | [schema/proposal.md](schema/proposal.md) |
| 体制を示す | `org` | 左右の組織ツリー＋提案範囲 | [schema/proposal.md](schema/proposal.md) |
| 全体像を示す | `house` | 屋根・柱・土台 | [schema/proposal.md](schema/proposal.md) |
| 繰り返す運用・サイクル | `cycle` | 中央の円＋円弧の矢印＋段のパネル | [schema/proposal.md](schema/proposal.md) |
| 目標と KPI の対応 | `kpi_tree` | 目標 → 方向性 → KPI＋目標値＋測り方 | [schema/proposal.md](schema/proposal.md) |
| 図・要点・数字を 1 枚に並べる | `composite` | 本文を格子に分け、図解・表・グラフ・要点・数字などのブロックを 2〜4 個置く | [schema/composite.md](schema/composite.md) |
| 主役の数字・一文＋根拠の図表（結論・実績の 1 枚） | `split` | 端まで届く色面か画像のパネル（大きな数字・一文）＋ 残りの領域に `composite` と同じブロック | [schema/composite.md](schema/composite.md) |
| 登録した構図で見せる | `pattern` | 型（同梱 19 個＋自作）に中身（スロット）を差し込む。合成・分割のブロックにも置ける | [schema/pattern.md](schema/pattern.md) |
| キーメッセージ・引用 | `quote` | 強調したい一文 | [schema/basic.md](schema/basic.md) |
| まとめ・次のアクション | `closing` | 箇条書き＋締めの一言 | [schema/basic.md](schema/basic.md) |
| コード・設定例 | `code` | 行数に応じて縮小。右に番号付き注釈も可 | [schema/basic.md](schema/basic.md) |
| 画像・図版 | `image` / `image_text` | 画像 1 枚／画像＋パンチライン＋本文（`assets/` の png / jpg / svg など） | [schema/basic.md](schema/basic.md) |
| 既存 PowerPoint の取り込み | `canvas` | 座標指定の自由配置。取り込み結果の修正専用（新規の構図は `pattern`） | [schema/canvas.md](schema/canvas.md) |

迷いやすい組:
- **`bullets` / `cards` / `table`**: 順に読ませるなら `bullets`、並列で見出し付きなら `cards`、項目 × 比較軸なら `table`。
- **`steps` / `swimlane` / `lifecycle`**: 見出しに部署・担当者が入るなら `swimlane`、状態名なら `lifecycle`、レーン不要の直線なら `steps`（詳しくは [diagram-guide.md](diagram-guide.md)）。
- **`kpi` / `chart` / `table`**: 数字 1〜4 個を見せるなら `kpi`、推移・比較・内訳の形で見せるなら `chart`、数値を正確に読み取らせたい一覧は `table`。
- **`pattern`**: 同梱・登録済みの構図があるときに使う（`pattern_engine.py list` で確かめる。一覧と選び方は [schema/pattern.md](schema/pattern.md)）。構図を `canvas` で手書きしない。例: 結論と根拠 = `conclusion-evidence`、対比 = `before-after`、柱 = `pillars`、一言＋説明 = `keyword-explain`、番号つきの項目 = `numbered-columns` / `numbered-list`。
- **`composite` / `split` / 2 枚に分ける**: 2〜3 個のブロックが 1 つの主張を支えるなら `composite`、主役の数字や一文＋根拠の図表なら `split`。ブロックが 4 個を超える・ブロックごとに別の主張がある・文字が 12〜14px まで縮むときは 2 枚に分ける（[schema/composite.md](schema/composite.md)）。

`swimlane_legend` は `swimlane` の `legend`（既定 `true`）で自動挿入される凡例ページの内部タイプ。直接は書かない（[schema/swimlane.md](schema/swimlane.md)）。

### 結論の帯と出典（`conclusion` / `source`）

**共通パーツ**（`title` / `section` / `quote` / `closing` / `canvas` / `statement` 以外の全タイプで使える）:
- `conclusion`: 本文の下に結論の帯（`primary` 塗り・白抜き太字・中央揃え）を付ける。帯の分だけ本文の領域が上に詰まる（既存タイプでは本文の領域の高さを、`table` では行の高さを自動で詰める）。結論の文字は 17px から 13px まで縮み、入らなければ帯が最大 72px まで高くなる。見た目は `style.conclusion`（`h` / `gap` / `size` / `min_size` / `max_h` / `fill` / `color`）
- `source`: 本文の下に出典の行（12px・`muted`）を付ける。試算値は「試算の前提: …」と書く。2 行以上になると本文を狭めて高さを確保する。見た目は `style.source`

### アイコン（`icon`）

提案書向けタイプ（`summary` / `reasons` / `house` / `cycle`）と `cards` の項目には `icon`（同梱アイコンの名前か概念語。例 `"セキュリティ"`）を書ける。HTML でも PPTX でも線だけのネイティブ図形になる。小さく（22〜28px）脇役として使い、並列・循環・全体像のページに絞る（`steps` や表・見積・スケジュールには入れない）。置ける場所・検索コマンド・ライセンスは [schema/proposal.md](schema/proposal.md) の「アイコン（`icon`）」。

## 検証

ビルド時のエラー（停止）と警告（続行）の条件は [schema/validation.md](schema/validation.md)。自動フィットの警告の直し方は [schema/autofit.md](schema/autofit.md)。図解タイプの配線・ラベルの診断コードは [schema/diagram.md](schema/diagram.md) の「図解タイプの診断」。

## 文字量・要素量の目安

文字量・要素量の目安はこの 1 つの表に集めた（各タイプのファイルにも、説明つきで同じ目安が書いてある）。`meta.density` を変えると上限が変わる（`talk` は少なめ、`read` は多め。目安は `lint_deck_text.py` も密度で切り替える）。以下は `standard` の値。

| タイプ | 目安 |
|---|---|
| `title` の `title` | 25字以内 |
| `lead` | 60字以内 |
| `bullets` の項目数 | 3〜6項目、1項目40字以内 |
| `table` の行数 | 6行以内（7行以上・5列以上は `meta.density: "read"` か 2 枚に分ける） |
| `cards` の枚数 | 3〜6枚（列数は3前後） |
| `steps` | 3〜5ステップ |
| `matrix` の `quadrants` | 必ず4個 |
| `architecture`/`dataflow`/`lifecycle` のノード数 | 12個以下 |
| 同上の列（`cols`） | 6以下 |
| `sequence` の参加者 | 7人以下 |
| `sequence` のメッセージ数 | 12本以下 |
| 図解タイプのエッジ `label` | 全角8〜12字程度 |
| `status_table` の行数 | 1枚3行程度 |
| `agenda` の項目数 | 1段8行まで（9〜16項目は自動で2段、17項目以上は次ページへ繰り越し） |
| `lifecycle` のレーン | 3〜4本程度 |
| `schedule` の行数 | 14行以下 |
| `summary` の行数 | 3〜6行（7行以上は警告） |
| `reasons` の行数 | 3行前後（6行以上は警告） |
| `row_matrix` の行数 | 6行以内 |
| `org` | 各側3階層・1段4ノード以内 |
| `house` の柱 | 3〜4本（6本以上は警告） |
| `cycle` の段 | 3〜6段（2段以下はビルドエラー、7段以上は警告） |
| `kpi_tree` の KPI | 6行以内 |
| `statement` | デッキに2〜3枚まで |
| `kpi` の `items` | 1〜4件（5件以上は警告） |
| `chart` | 縦棒 12 項目以内・横棒 15 項目以内・系列 5 本まで（超えると警告） |
| `pattern` | パターンごとの個数（`min` / `max`。超えた分は描かれない）。`pattern_engine.py show <名前>` で見る |
| `composite` のブロック | 2〜4 個（1 個・7 個以上は警告）。1 ブロックの文章は 3〜4 行まで |
| `split` | パネルの `items` は 3 つまで、`title` は 30 字以内。本文のブロックは 1〜2 個 |
| `cards` の `emphasis` | 強調は 1〜2 枚まで（3 枚以上は警告）。主役のページ（`variant` / `background` / `split`）はデッキに数枚まで |

超える場合はスライドを分ける、`two_column`/`cards` などの別タイプに分割する、`meta.density` を変える。目安を超えても即エラーにはならないが、自動フィットが文字を縮め、下限でも収まらなければ警告になる。`check_layout.py` でも検出される。

## ビルドとプレビュー

```bash
# <deck_dir> は deck.json があるフォルダ（${CLAUDE_PLUGIN_ROOT} の意味は冒頭「パスの書き方」を参照）
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>            # HTML + PPTX（PPTX は保存直後に自動検証される）
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html      # HTML のみ（高速）
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> 5         # 5枚目だけPNG化して目視確認
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir>           # 全スライドPNG化
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>           # 構造チェック（はみ出し・重なり・小さい文字・コントラストなど）
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir>           # 見た目チェック（空白帯・似たスライドの連続）
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>         # 文言チェック（【要確認】の一覧を含む）
python "${CLAUDE_PLUGIN_ROOT}/tools/verify_pptx.py" <deck_dir>/build/<id>.pptx   # PPTX の構造検証（zip 整合・ノート無し・文書プロパティ）
python "${CLAUDE_PLUGIN_ROOT}/tools/export_pdf.py" <deck_dir>             # PDF書き出し（要 LibreOffice）
```
検査ツールの出力の読み方・種別ごとの直し方は `skills/create-deck/checks.md`。`preview_deck.py` / `check_layout.py` / `check_visual.py` / `lint_deck_text.py` / `check_diagram.py` / `contact_sheet.py` の**スライド番号は、実際のビルド後の PNG の番号**（`agenda` の自動繰り越しや `swimlane` の凡例自動挿入を含む）で、deck.json に書いた `slides` の要素数とずれることがある。ずれたスライドは「slide-03（deck.json 2枚目）」と併記される。

### 微修正ループ（推奨ワークフロー）

1. `deck.json` の該当スライドの**内容**（文・項目数・分割・密度）を先に直す。それでも足りないときだけ `style` を編集
2. `build_deck.py <deck_dir> --html` → `preview_deck.py <deck_dir> <番号>` で当該スライドのみ確認
3. 納得したら `build_deck.py <deck_dir>` で PPTX も再生成

ビルドは全体でも1秒未満なので、再生成コストを気にする必要はない。**生成物（build/ 配下）は直接編集しない**（再ビルドで消えるため）。

## 注意

- PPTX にスピーカーノートは出力しない仕様（python-pptx の notes_slide が Keynote 互換性を壊すため）
- 色はテーマトークン（`primary`, `accent` など）で指定し、hex 直書きはスライド固有の特例に限る（テーマ切替が効かなくなるため）。テーマトークンでも hex でもない値を指定するとビルドエラーになる
- 新しいテーマは `${CLAUDE_PLUGIN_ROOT}/tools/new_theme.py <name>` で雛形を作り、`colors`/`fonts` を編集して `meta.theme` を切り替えるだけでよい。テーマは `default` をベースにマージされ、明示していないトークンは自動導出されるので上書きしたいトークンだけ書けばよい（詳細は [themes.md](themes.md)）

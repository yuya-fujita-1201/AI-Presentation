# 検証（ビルド時にチェックされる内容）

図解タイプの配線・ラベルの診断コード（`check_diagram.py`）は [diagram.md](diagram.md) の「図解タイプの診断」。自動フィットの警告の意味と直し方は [autofit.md](autofit.md)、`kpi` / `chart` は [visual.md](visual.md)、`pattern` は [pattern.md](pattern.md)。共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。

`build_deck.py` はビルド前に deck.json 全体を検証する。出力は 3 段階:
- **エラー（`error:`）** — ビルドを停止する（終了コード 1）。
- **警告（`warning:`）** — ビルドは続行するが、見た目や内容に問題がある。直す。
- **note（`note:`）** — 事実の通知（文字を縮めた、フォントを代替した、など）。直さなくてよいが、意図と違えば内容か密度を見直す。

メッセージの形は `N枚目（type=xxx）: 内容 → 直し方`。N は deck.json の何枚目か。エラーは入力の誤りをトレースバックではなく日本語で伝え、**直し方を必ず添える**。想定外の例外は `N枚目（type=xxx）の検証中にエラー: KeyError: 'zzz'。入力の形を確認してください` で止まる（描画段階は `出力Nページ目（type=xxx）のHTML描画中に…`）。元のトレースバックを見るには `build_deck.py --debug`。

## エラー（ビルド停止）になる条件

**構造・タイプ**
- スライドに `type` が無い、文字列でない、または未知の `type`（使えるタイプの一覧を添える）。レイアウト JSON にだけあって描画が登録されていないタイプは「このタイプの描画が登録されていません」
- `meta.layout_overrides` のトップキーが未知の `type`
- `meta.id` に `\ / : * ? " < > |` や制御文字を含む
- `meta.shape` が登録されていない shape 名、`meta.variants` に無い variant 名（`meta.variants.title の 'centre' という variant はありません…`）
- `style` / `meta.layout_overrides` に書いた中身が少ないときの調整トークンが範囲外・型違い（`thin_grow` `thin_text_grow` `fill_grow` `fill_text_grow` は 1〜4、`thin_max_size` ほかは 1〜200、`thin_trigger` `thin_target` `thin_min_ratio` `thin_valign_ratio` `fill_trigger` `fill_target` `center_ratio` `thin_center_ratio` は 0〜1、`thin_fill_aspect` は 0.5〜20、`brand.clear_gap` は 0〜400、`scale_k` は 1〜4、`grow_sizes` は 1〜200 の数値の配列、`common.wrap` の `detect_level` `max_extra_lines` は整数、`thin_fill` `cols_search` `auto_before` は true / false。キー名つきで止まる。[autofit.md](autofit.md)）
- `style` / `meta.layout_overrides` の数値が極端（文字サイズ `size` `*_size` は 2000 以下、`line_height` は 100 以下、`cols` `max_cols` は 1000 以下、そのほかの位置・寸法は絶対値 10 万以下。NaN・Infinity は不可。極端な値で計算が終わらなくなるのを防ぐ上限で、ふつうの値は弾かない）
- 画像が大きすぎる（幅 × 高さが 8000 万画素を超える。`画像が大きすぎます（12000×9000 = 108 百万画素 …）→ 縮小して置き直す`。`image` / `image_text` / 背景 / 合成の image / canvas・型の画像に共通）
- 合成スライドの図解ブロックで、ノードの `row` / `col` が上限（40）を超える（単独の図解スライドと同じ「行は 40 行までです」）
- `meta.density` が `talk` / `standard` / `read` 以外、`meta.autofit` / スライドの `autofit` / `meta.todo_marks` が真偽値でない（`density` はスライド単位も同じ。`meta.todo_marks は true / false で指定してください（文字列が書かれています） → 【要確認】の強調表示を切るなら false（既定は true）`）
- レイアウト JSON の `readable_pairs` の形違い（`レイアウト 'xxx'（xxx.json）: readable_pairs.steps は [[領域, 文字色のキー, [地の色…]], …] の配列にしてください（数値が書かれています） → 使わないタイプは [] にするか、キーごと消す`。`_` で始まるキーはメモとして無視）
- `meta.theme` / `meta.layout`、テーマ JSON の `extends` / `alias_of`、レイアウト JSON の `extends` が名前でない（パス区切り・絶対パス・先頭が `.`）。循環した `extends`。見つからないときは「使える名前」と探索先を表示する

**内容フィールドの型違い**（配列のはずが文字列、など）

| 例 | メッセージの要点 |
|---|---|
| `"bullets": "abc"` / `"cards": ["a","b"]` / `"bullets": [1, 2]` / `"rows": [null]` | `cards[0] はオブジェクト（{ … }）で指定してください（文字列が書かれています）`。配列のはずの所に文字列・オブジェクト、要素が数値や null のとき |
| `architecture` / `dataflow` / `lifecycle` の `stages` `col_headers` `row_headers` `phases` `lanes`、`kpi_tree.headers` の型違い | 同上 |

**`style` / `layout_overrides`**
- 形: `"style": null` / `"style": {"body": "big"}` / `"layout_overrides": {"bullets": null}`（領域はオブジェクト `{ "size": 20 }` で書く）
- 数値プロパティが数値でない: `"size": "24"` / `"w": "wide"`。引用符なしの数値にする。`size` `line_height` `max_cols` `cols` は 0 より大きく（`max_cols` `cols` は整数）、`w` `h` `gap` `pad` `radius` と `*_w` `*_h` `*_gap` `*_pad` `*_radius` は 0 以上。`x` `y` は負でもよい
- `style.<領域>.align` は `left` / `center` / `right`、`valign` は `top` / `middle` / `bottom` のいずれか（「style.title.align は left / center / right のいずれかで指定してください」）
- `fit`（cards の `grid`、two_column の `left` `right`）は `"content"` か `"fill"`
- 色（`color` / `fill` / `*_color` / `*_fill` / `marker_color` / `row_fills`、bullets 項目の `color`）が「テーマ colors のキー」でも「`#RRGGBB` / `#RGB`」でもない（例: `primry` →「テーマトークン名か #RRGGBB を指定してください」）
- 未知の領域名でも、中のプロパティの型（`size` が文字列など）は検査する

**各タイプ**
- `table`: 各行のセル数が `columns` 数と不一致、`columns` が空、`col_widths` の長さが `columns` 数と不一致（0 以上の数値で合計が 0 より大きいこと）。行を `{"cells": …}` で書いたとき `cells` が無い。セルの `tone` が `good` / `warn` / `bad` / `accent` / `muted` 以外（「tone 'red' は使えません → good / warn / bad / accent / muted」）。`url` に使えないスキーム（`javascript:` など）
- `status_table`: `cells` の数が `columns` 数 − 2 と不一致
- `image` / `image_text` / canvas の画像 / パターンの image スロット: `path` が未指定、デッキフォルダの外を指す、存在しない、対応外の拡張子。画像が壊れている・SVG でない SVG（PPTX 段で落ちて HTML だけ残る不整合を防ぐため、ビルド前に開いて確かめる。画像を作り直す）
- `swimlane`: `node.id` 重複、`edges` の `from` / `to` が未知 `id`、`lanes` が空、`legend_items` の要素が不正
- `architecture` / `dataflow` / `lifecycle` / `sequence`: ノード（`states` / `participants`）の `id` 重複・欠落、`edges`（`transitions` / `messages`）の `from` / `to` が未知 `id`、`row` / `col` が 0 以上の整数でない、同じ `(row, col)` の重複、`nodes` / `states` が空、`sequence` の `messages[].id` 重複。`row` / `col`（`cols` / `rows` を含む）は 40 まで（「ノード 'b' の col が 10000000 です。列は 40 列までです → col は 0 始まりで、飛ばさずに詰めて指定する（多すぎるときはスライドを分ける）」）
- `org`: `parent` が自分自身・循環、id の重複、存在しない `parent` / `links`
- `cycle`: 段が 2 以下
- `kpi` / `chart`: 種類の打ち間違い・`categories` / `series` の欠落や個数違い・`y.min` ≥ `y.max` など（表は [visual.md](visual.md)）
- `pattern`: 必須スロットが無い・値の型が違う・画像のパスが使えない・パターンが見つからない（[pattern.md](pattern.md)）
- `composite` / `split`: ブロックにできないタイプ（入れ子・全面の `pattern` を含む）、置く場所が無い・位置の重なり・範囲外、`columns` / `rows` の比率が不正、未知の `arrange`、`frame` などの値違い、`split` の `panel` が無い・`side` / `ratio` の値違い（[composite.md](composite.md)）
- 主役のページ: `variant` が無い名前、`background` に `image` も `fill` も無い・画像が無い・`opacity` / `overlay` / `position` の値違い、cards の `emphasis` / `span` の値違い、`bleed` / `fit` の値違い、`style.deco*` の型違い（[hero.md](hero.md)）
- canvas: 数値・色・`anchor` / `align` / `dash` / `cap` / 矢じりの値・フォント名・パス命令の規定外、`w` / `h` が負、`line` / `shadow` がオブジェクトでない（[canvas.md](canvas.md)）

**テーマ JSON**: `colors` の値が `#RRGGBB`（`#RGB` 可。読み込み時に 6 桁へそろえる）でない（`"navy"` / `"#12345"`）。`fonts` の値が空文字、または空でない文字列（か文字列の配列）でない。フォント名に `"` `\` `<` `>` `;` `{` `}` と制御文字を含む（CSS に出力されるため）。レイアウト JSON の各領域の値の型違い（「レイアウト 'mine'（mine.json）の types.bullets.body.size は数値で指定してください」）。

**SVG を含むデッキの PPTX 化**: SVG の画像（`image` / `image_text` の `.svg`、SVG を使う型・合成ブロック）は PPTX に PNG にして貼るため、playwright が要る。無いときはトレースバックではなく `error: このデッキは SVG の画像を含むため、PPTX 化に playwright が必要です … → /slide-deck:setup --playwright で導入する … HTML だけなら --html を付けて再実行できます` で止まる。ブラウザ本体が無いときは `playwright install chromium` を案内して止まる。

**canvas 型（取り込み結果）**: `elements[*]` の数値欄（`x` `y` `w` `h`、`runs[].size`、`lineHeightPx`、線の太さ・罫線など）に数値以外（配列・オブジェクト・true / false・NaN）を書くと、`1枚目（type=canvas）: elements[13].h … は数値で指定してください` のように、どの要素のどのキーかを示して止まる（以前は描画の途中で落ちた）。色・矢じり・罫線・フォントの型違いも同じ。

**取り込みツール（`pptx_import.py` / `pattern_from_pptx.py` / `theme_from_sample.py` の PPTX）**: 展開後の合計が 500MB、または中の 1 ファイルが 100MB を超える PPTX は `PPTX が大きすぎます（…）` で止まる。壊れた zip・XML は `PPTX が壊れているか大きすぎます（…）` の 1 行で止まる。`pattern_engine.py check` は、型 JSON の形が違うとき、落ちずに場所つきのエラーにする。`export_pdf.py --no-build` は `meta.id` の禁止文字（`\ / : * ? " < > |`）と `.` `..` を弾く。

**PPTX の保存**: 開いている PPTX に書けないときは、先に HTML を更新してから「<ファイル> に書き込めません」で終了コード 1 にする（PowerPoint で開いたままのとき。閉じて再ビルド）。保存直後に PPTX を検証し（`tools/verify_pptx.py` と同じ検査）、zip の破損・XML の不整合・再パース不能・ノートが入っている・題名が空などで `error: <ファイル>.pptx の検証に失敗しました: …` と止める。入力（deck.json）起因のもの（題名・スライド数）と、ツールの不具合（zip 破損・再パース不能）は案内を分けて出す。

## 警告（ビルドは続行）になる条件

**未知のキー**（もしかして候補つき。先頭が `_` のキーはメモ用として無警告）
- スライド直下（`N枚目（type=cards）: 未知のキー "colums" は無視されます（もしかして "columns"）→ cards の固有キー: …`）。よくある取り違え（`items`→`bullets`、`headers`→`columns`、`title`→`heading` / `label`、`desc`→`body` など）を先に当て、無ければ綴りの近さで候補を出す。全タイプ共通で無警告のキー: `type` `title` `eyebrow` `notes` `style` `relation` `conclusion` `source` `line_balance` `density` `autofit`
- `cards[]` `steps[]` `quadrants[]` `left` `right` の中、`meta`（書けるキー: `id` `title` `subtitle` `author` `date` `as_of` `theme` `layout` `layout_overrides` `brand` `line_balance` `density` `autofit` `shape` `variants` `section_numbers` `todo_marks`。`patterns` は書けない。2.0.0 までの `pptx_import.py` が書いた `meta.source` / `meta.generator` と canvas スライドの `source_page` は、警告なしで読む。今の取り込みは `_source` / `_generator` / `_source_page`（メモ扱い）で書く。canvas 以外のスライドの `source_page` は警告）、テーマ JSON のトップキー（`name` `label` `description` `colors` `fonts` `extends` `alias_of`）、`deck.json` の最上位（`meta` と `slides` 以外）。標準の色トークンに似た名前（`primry`）は「`colors."primry" は標準の色トークンではありません（もしかして "primary"）`」
- `style` / `layout_overrides` の領域名（「'boddy' は bullets の領域名ではありません（候補: body）。使える領域: …」）と、領域の中のプロパティ名（「style.body の "sizee" は無視されます（この領域にそのプロパティはありません）（もしかして "size"）」）。領域の既定値にあるキー、共通プロパティ（`x y w h size color fill bold italic align valign line_height gap pad radius text border_color border_w font opacity shadow nowrap`）、コードが読むが既定値に無いもの（`fit min_h min_size row_fills total_fill label_fill label_color …`）は許される
- 図解タイプ（`architecture` など）は `diagram_engine` が未知キーを検査する（[diagram.md](diagram.md)）

**内容の問題**
- 極端に小さい文字: `style.*.size`（`cell_size` など本文系の `*_size` を含む）が 8px 未満
- 箇条書きの 3 階層目以降（描画されない。2 階層までにまとめる）。項目に `text` が無い（`{"txt": "hi"}` のような打ち間違い。1 スライド 1 件にまとめて「8 個の項目に text がありません（例: bullets[0]）」）
- 本文が空: bullets / cards / steps / agenda / two_column / matrix / code / table / status_table / image_text で本文のフィールドがすべて無いか空（フィールド名の打ち間違いのことが多い）。`closing` は `title` だけでも警告しない
- `slides` が空、`meta.title` が無い・空、`cards.columns` が 1 未満、`matrix` の `quadrants` が 4 個以外、`swimlane` のノードの `col` が `cols` 以上（自動拡張される）
- `kpi` の `items` が 5 件以上・`chart` の項目や系列が多い・値ラベルや注釈の重なりなど（[visual.md](visual.md)）。`pattern` の未知スロット・文字数や個数の超過（[pattern.md](pattern.md)）
- `composite` / `split` のブロックの文字あふれ・格子の空き・主役（`emphasis`）が複数・箱の中身が少ない・細い `steps`・型の縮小（[composite.md](composite.md)）。主役のページの背景の上の文字の対比不足・cards の強調が 3 枚以上・span の組み合わせの空き（[hero.md](hero.md)）
- アイコン名が同梱に無い（近い候補を提示）
- `meta.brand` が右上の箱（既定 幅 140px・文字 23px）に 1 行で収まらない（全スライドで 2 行に折れてあふれるため、ビルドが 1 回だけ警告する。`meta.brand「Accenture Japan」は右上の箱（幅 140px・文字 23px）に 1 行で収まりません（約 211px）… → 短くする（目安は全角 6 字・半角 8 字前後まで）か、meta.layout_overrides.common.brand で w を広げる（x も同じだけ左へ）・size を下げる`。実測では半角の大文字が多いと 7〜8 字で収まらない）
- `style` / `meta.layout_overrides` に `x` と `w`（または `y` と `h`）の片方だけを書き、既定のもう片方と合わせるとスライドの外へ出る領域（`N枚目（type=schedule）: style の chart.w だけが指定され、x は既定値（72）のままのため、x + w = 1304 がスライドの幅（1280）を超えます → chart の x と w を両方書く`）。2.0.0 の既定位置を前提に片方だけ上書きしたデッキで起きる
- `frame: "full"` の型（pattern）で、スライド直下の `title` が描かれない（`eyebrow` `lead` `conclusion` `source` と同じ。合成のブロックの仮の title には出ない）
- レイアウト JSON の `todo_color` / `todo_color_on_dark` / `todo_bg` が `#RRGGBB` でない（既定の色で強調する）
- 【要確認】のマーカーの扱い: 長い【要確認…】は「途中で折れて表示されます」（`long-word`）の 1 語に数えない（マーカーの中の長い英数字・URL は従来どおり警告）。`kpi` の `value` に `【要確認: 金額】` と書いても 8 文字の字数に数えない（マーカーの外が 8 文字を超えれば警告）。合成の `kpi_tree` ブロックの `conclusion` / `source` / `title` / `lead` / `eyebrow` は警告どおり描かない（結論はスライド全体の `conclusion` に書く）
- `kpi` の `of` と `from` が両方ある（`from` を優先して `of` を無視）。`agenda` の項目の未知のキー（`title` など。`text` / `desc` / `active` だけ）・`text` が無い項目。`arrow` が `both` でない edge の `label_back`、ノードの文字に重なる `label_at`（無視して自動配置）（[diagram.md](diagram.md)）
- 型を置いた矩形の幅が下限未満・描かれる文字が 12px 未満（[pattern.md](pattern.md) の「幅に合わせた構図」）。`kpi_tree` が下限まで縮めても入らない合成ブロック
- 図解タイプの**配線・ラベル・文字量などの幾何診断**（`too-dense` / `label-collision` / `edge-through-node` / `group-leak` / `out-of-grid` / `node-text-overflow` など）は警告として報告される。詳しくは [diagram.md](diagram.md)

**文字・図形があふれる見込み**（自動フィットの警告。意味と直し方は [autofit.md](autofit.md)）: 表・箇条書き・カード・ステップ・マトリクスなどが「下限まで縮めても枠の高さを超える」、タイトルが縮めても 2 行になる、結論の帯・出典が入らない、URL や長い英単語が枠の幅に入らない（`long-word`）、`schedule` の図が枠の下端を越える（`chart-overflow`）。文言は「N枚目（type=table）: 表は 12px まで縮めても約Npx はみ出します（M行）→ 行を K 行以下に減らすか 2 枚に分ける」のように、見込みのはみ出し量と直し方を示す。
文字あふれの推定は、テーマのフォント（`fonts.body` / 見出しは `fonts.heading`）のフォントファイルを Pillow で実測した字幅で行う（英単語は途中で切らない・行頭禁則文字は追い出す、というブラウザの折り返しに寄せる）。

## note（通知）

- `テーマ 'acn-slide-master' は同梱のものではなく <パス> を読みました（探索順で先に見つかったほうが使われます。意図していなければ、そのファイルを別の名前にするか移します）` — 同梱と同じ名前のテーマ・レイアウト・型・形を、同梱以外（環境変数・デッキ・デッキの親・カレント）から読んだ。1 ファイルにつき 1 回。
- `要確認が 5 件あります（1 枚目 2 件（確かめる点）、4 枚目 1 件、…）→ 根拠を確かめて文を確定し、マーカーを消す` — 画面に出る文字の中の `【要確認】` の件数と場所（`notes` `code` `style` の中、未知のキーの中は数えない）。`meta.todo_marks: false` のときは末尾に「強調表示はしていません」が付く。引き渡しで件数と一覧を報告する（[../deck-schema.md](../deck-schema.md)）。
- `…のラベル「…」が矢羽根の中に収まらないため、矢羽根の右に出しました`（schedule の `bar-label-moved`。info）。
- `フォント 'Meiryo UI' がこの環境に無いため、字幅は代替の 'Hiragino Sans'（ブラウザが代わりに使うフォント）で測っています（実機の PowerPoint では折り返し位置が数文字ずれることがあります）` — テーマのフォントがこの機械に無い。折り返し・あふれ・泣き別れの見積もりをブラウザが実際に使う代替フォントで測っている。影響は PPTX の折り返し位置の見積もりだけ。直すなら、そのフォントを入れた機械でビルドする。
- `フォント '…' も代替フォントもこの環境に無いため、字幅は近似（全角 1.0 / 半角 0.55）で測っています` — 英数字の多い文は実際より広めに見積もる（和文はほぼ一致）。
- `文字を 24px → 20px に縮めました`、タイトルを縮めた、表の泣き別れ・3 行折りを避けきれなかった、など自動フィットが縮めた通知（[autofit.md](autofit.md)）。
- `meta.id（zzz）とフォルダ名（…）が一致していません` — 出力ファイル名は `meta.id`（`build/zzz.html`）になる。意図した名前なら直さなくてよい（省略するとフォルダ名になる）。
- `warning: PPTX のテーマ（色・フォント・効果）の書き換えに失敗しました…` — 図形の色は個別指定なので見た目は変わらない。再発するなら報告する。

## 値の扱い（書いた人が知っておくこと）

- スライド直下の値が `null` のキーは「書いていない」とみなして取り除く（`style` だけは null だとエラー）。
- 文字列のはずのフィールド（`title` `lead` `number` `attribution` など）に数値を書いたら文字列にそろえる（`"number": 1` → `"1"`）。
- 配列・オブジェクトのはずのフィールドに空文字 `""` を書いたら「書いていない」扱い。
- `meta.title` / `author` / `subtitle` の XML で使えない制御文字（`\x00-\x08` `\x0b` `\x0c` `\x0e-\x1f`）は取り除いて PPTX の文書プロパティに入れる。
- PPTX の文書プロパティ: タイトル = `meta.title`（上の順で補う）、サブタイトル（subject）= `meta.subtitle`、作成者・最終更新者 = `meta.author`、作成日時・更新日時 = ビルド時刻、言語 = ja-JP。python-pptx 既定の作成者名・既定サムネイルは残さない。

## ビルドとは別の検査

ビルドの検証は「入力が正しいか・枠に収まるか」の見積もりまで。出来上がった HTML / PPTX を実際に測る検査は別のツール:

| ツール | 見るもの |
|---|---|
| `check_layout.py` | 実描画のはみ出し・重なり・文字の欠け・罫線の貫通・行数・泣き別れ・語の途中の折れ（`wordbreak`）・小さい文字・コントラスト・線の貫通（種別は `skills/create-deck/checks.md`） |
| `check_visual.py` | プレビュー PNG の空白帯（`empty-bottom` / `empty-band`）・似たスライドの連続・PNG が古い（`stale`） |
| `lint_deck_text.py` | 文言（AI 定型句・Markdown 記法の残留・「N枚目」直書き・文字量・和文と英数字の間の空白の混在・`【要確認】` の一覧）。不合格の規則は [../content-guide.md](../content-guide.md) の「lint の不合格と直し方」 |
| `check_diagram.py` | 図解の配線・ラベルの座標診断（[diagram.md](diagram.md)） |
| `verify_pptx.py` / `check_pptx.py` | PPTX の構造検証（zip 整合・XML・再パース・ノート無し・文書プロパティ）／PPTX を LibreOffice で描いて HTML と比べる（参考値。PowerPoint 実機とは違う） |

警告が出たら無視せず、直す順は **内容（項目数・文の長さ・分割）→ 密度（`meta.density`）→ `style`**。

## PPTX と HTML の見た目の対応と既知の差

同じ deck.json から HTML と PPTX を作るが、PowerPoint で開くと HTML と同じとは限らない。利用者への説明と、引き渡しの「確かめていないこと」を書くときの根拠にする（PowerPoint 実機はこの環境で確かめていない）。

- **行送り**: PPTX は「文字サイズ(px) × `line_height`」を pt にした**固定値**（倍率ではない）で書き出す。フォントが変わっても行の間隔は変わらない。
  - 既知の差: 固定行送りの 1 行目は、PowerPoint と LibreOffice では行ボックスの下寄りに描かれ、HTML は中央に描かれる。`line_height` が大きく文字が大きいほど（1.6 で 24〜40px の文字）、先頭行が PPTX で 4〜8px 下がる（LibreOffice で実測。PowerPoint 実機は未確認）。
- **影**: PPTX の図形に影は付かない（LibreOffice で PDF にしても出ない）。影が出るのは `canvas` の `shadow` を明示した図形だけ。
- **自動調整なし**: PPTX の文字枠は「自動調整なし・折り返しあり」。PowerPoint で文字を直しても箱の大きさは変わらない。**文字を足すとはみ出す**ので、直すのは deck.json（自動フィットは deck.json からのビルドでだけ働く）。
- **表**: セル内の `\n` は改行。罫線は HTML と同じ（ヘッダーは線なし、本文は各行の下に 1px）。`col_widths` が無いとき、PPTX の列幅は HTML の自動幅を字幅の実測でまねた値（ブラウザとの差は大半が 3px 以内）。セルの上下余白は `style.table.pad_y`。
- **【要確認】**: HTML は黄色い下地＋太字（`<mark class="todo">`）、PPTX は run の文字色＋太字だけ（PPTX の run に塗りは無い。暗い地の上は明るい黄）。表のセル・グループ内の図形・canvas の文字も対象。PPTX の分割した run（太字・色）と、折り返しの `a:br` をまたぐ強調は、LibreOffice の描画までの確認で、PowerPoint 実機は未確認。
- **文字色**: 地の色の上で 4.5:1 に足りない文字色は、HTML も PPTX も同じ規則で自動調整される（[../themes.md](../themes.md)）。
- **フォント**: テーマのフォントがビルドした機械に無いと、折り返し位置の見積もりは代替フォントで行う（`note:`）。実機の PowerPoint では折り返しが数文字ずれることがある。
- **スピーカーノート**: PPTX には出ない（HTML でだけ表示。[../deck-schema.md](../deck-schema.md) の全タイプ共通のオプション）。

差を目で確かめるには `check_pptx.py`（LibreOffice 描画との比較。`skills/create-deck/checks.md`）。`check_pptx.py` と `export_pdf.py` は、PPTX が使うフォントのうちこの機械に無いものを、LibreOffice の一時プロファイルで字幅の見積もりに使う代替フォント（例: Hiragino Sans）に**固定**して描く（変換のたびに代替フォントが変わり、折り返しや約物の幅が毎回違っていたため）。何度描いても同じ見た目になるが、PowerPoint 実機の見た目の代わりにはならない。フォントが入っている機械では何もしない。それでも PowerPoint 実機の見え方は確かめられないので、引き渡しでは「PowerPoint 実機での見え方は未確認」と書く。

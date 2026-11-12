# 主役のあるページ — 背景・variant・cards の強弱・画像を端まで

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。表紙・章扉・言い切りなど「そのページが主役」のスライドを、座標を書かずに作るためのキー。**何も指定しなければ、見た目は従来のまま**（`background` / `variant` / `emphasis` / `span` / `fit: "bleed"` / `bleed` を書いたときだけ変わる）。非対称分割 `split` は [composite.md](composite.md)。

**主役は 1 デッキに数枚まで**（20 枚なら 3〜5 枚）。全部が主役だとどれも主役でなくなる。置き場所の考え方は `skills/create-deck/SKILL.md` の「デッキに抑揚を付ける」。

## 背景（`background`）— title / section / closing / statement / quote

```json
{ "type": "title", "title": "…", "background": { "image": "assets/cover.jpg", "overlay": "primary", "opacity": 0.6, "position": "center" } }
{ "type": "section", "title": "…", "background": { "fill": "surface" } }
{ "type": "title", "title": "…", "background": "assets/cover.jpg" }
```

| キー | 内容 |
|---|---|
| `image` | 画像のパス（デッキフォルダからの相対。`image` タイプと同じ検査）。cover（全面を埋めて余りを切る）で敷く |
| `fill` | 色面（テーマの色トークンか `#RRGGBB`）。`image` と同時には書けない（warn、`image` が勝つ） |
| `overlay` | 画像の上に重ねる色（色トークンか `#RRGGBB`。既定 `primary`）。`"none"` で覆いなし |
| `opacity` | 覆いの濃さ 0〜1。**省略すると、文字の対比が 4.5:1 以上になる最小の濃さを自動で選ぶ**。書いたらその値のまま（足りなければ warn） |
| `position` | 画像の切り抜き位置。`center`（既定）/ `top` / `bottom` / `left` / `right` / `top left` … / `"30% 70%"` |
| 文字列だけ | `"background": "assets/x.jpg"` は `{"image": …}` と同じ |

- **文字色は自動で選ぶ**（覆いが暗ければ明るい文字、明るければ暗い文字）。画像の「文字にとって最悪の場所」の色で対比を測る。accent 系の色が足りないテーマ（acn-slide-master の accent_on_primary など）は、届く色（on_primary など）に自動で置き換える。`meta.brand` の文字色も同様。title の `bottom` は、`meta.brand` があるとき brand を背景の上の文字として数え、覆いの濃さを決める（`brand_on_bg`）。
- 文字の無いところだけに画像を敷く variant（title の `split` / `bottom`）は、`overlay` / `opacity` を書かなければ覆いを付けない。
- HTML と PPTX は同じ要素（画像＋半透明の矩形の 2 図形）から描く。PowerPoint で画像の差し替え・覆いの調整ができる。`check_layout` の contrast も画像の上の文字を測る。
- 文字の下が均一な画像（グラデーション・ぼかし）のほうが、覆いが薄くて済み見映えが良い。**文字入りの図は背景にせず**、`image`（contain）か `split` のブロックに置く。

| 場面 | 文面と直し方 |
|---|---|
| image も fill も無い（fail） | `background に image も fill もありません → "background": {"image": "assets/x.jpg"} か {"fill": "primary"} のように書く` |
| 画像が無い・デッキ外（fail） | `background.image: 画像ファイルが見つかりません: assets/x.jpg → パスとファイル名を確かめてください` |
| 値の誤り（fail） | `background.opacity は 0〜1 の数値で指定してください` / `overlay 'x' がテーマの色トークンでも #RRGGBB でもありません → "primary" のようなテーマ色か、覆いを使わないなら "none"` / `position 'xx' を解釈できません` |
| 未知キー（warn） | `background の "opacty" は無視されます（もしかして "opacity"）` |
| 対比が足りない（warn） | 画像: `背景画像の上の文字の対比が 4.44:1 で、4.5:1 に届きません → opacity を 0.8 以上にする、またはもっと明暗のはっきりしない（文字の下が均一な）画像に替える`。色面: `色面 '#7F7F7F' の上の文字の対比が 4.1:1 … → 濃い色（primary など）か薄い色（background・surface）の面にする` |

**画像を用意できないとき**: 背景の画像は必須ではない。**色面（`background: {"fill": "primary"}`）か variant の色面だけでも主役のページは作れる**（title の `left-band` `split` `bottom`、section の `number` `band` `side`、statement の `left-bar` `mark` は画像なしで成立する）。外から画像を取ってこない。作る場合は Pillow などでグラデーション・幾何学模様の PNG / JPG を `assets/` に生成する。

## variant（見た目の型）

`"variant": "名前"`。**既定は今の見た目**。`"variant": "default"` は「何も付けない」。タイプ別の既定は `meta.variants`（`{"title": "left-band", "section": "number"}`）か shape の `layout.variant_defaults` で決められる。優先は スライドの `variant` → `meta.variants` → shape の `variant_defaults`。見た目の値は `templates/layouts/default.json` の `variants.<タイプ>.<名前>` にあり、`slide.style` はその上に重なる。

| タイプ | variant | 見た目 | 使いどころ |
|---|---|---|---|
| title | `center` | 文字を中央にそろえ、上に短い帯 | 講演・発表の表紙 |
| title | `left-band` | 左に太い色の帯（日付・作成者は帯の中）、右にタイトル。帯の中に薄い円の飾り（`deco2`）が付く。`meta.shape` が `classic` / `soft` なら円、`sharp` なら四角、`editorial` なら小さな角丸の四角で描く（角丸の半径が小さい形では円にしない）。`style.deco2.geom: "rect"` で四角に固定できる。`deco` の `geom: "ellipse"` に 50 未満の `radius` を書くと円にならない。円を避けるなら別の variant | 報告書・提案書の表紙 |
| title | `split` | 左半分が色面か画像（`background`）、右半分にタイトル | 写真・図が主役の表紙 |
| title | `bottom` | 上 6 割が色面か画像、タイトルは下 | 写真が主役の表紙 |
| section | `number` | 巨大な章番号（240px）が主役、右にタイトル | 章が多い長い資料 |
| section | `band` | 白い面の中央に全幅の色帯、その中にタイトル。`background` の画像は帯に敷く | 写真つきの章扉 |
| section | `side` | 左に細い色帯（中に章番号）、右にタイトル | 報告書・マニュアル |
| closing | `center` | タイトル・メッセージを中央に | 短い締めの一言 |
| closing | `contact` | 左にタイトルとメッセージ、右の白い箱に箇条書き（連絡先・次の一歩）。箱の本文は幅約 420px（全角 18 字前後）なので 1 行を短く書く。長い `【要確認: …】` は文節で 2 行に折れて表示される（幅を超えると「途中で折れて表示されます」の警告が出るが、画面で読めれば問題ない。短く書くのが無難） | 提案・会の締め |
| statement | `center` / `left-bar` / `mark` | 一文を中央／左に太い縦帯・左そろえ／左上に大きな引用符・左そろえ | 転換点の言い切り／力強い言い切り／顧客の声 |
| quote | `left-bar` / `mark` | 左に太い縦帯／左上に大きな引用符（図形で描く） | 論文・調査の引用／名言 |

- `number` / `side` の章扉は、`number` が無ければ章の順で `01` `02` … を自動で振る。`meta.section_numbers: true` なら variant に関わらず、`number` を書いていない section に振る。書いた `number` はそのまま。
- **表紙・章扉・statement の variant は、デッキの中で 1 種類にそろえる**（章扉を `number` と `side` で混ぜない）。`meta.variants` で決める。
- 章扉（section）のタイトルが 2 行になると、枠を下へ伸ばして罫線と副題を下げる（`number` / `band` / `side`・背景画像つきでも重ならない。`autofit: false` では伸ばさず警告。[autofit.md](autofit.md)）。
- 大きな文字（36px 以上）の改行は文節の切れ目に置く（語の途中で切らない。最終行を 2〜4 字だけにしない）。variant なしの `title` / `section` / `quote` / `statement` や、`background` つきのスライドも同じ。止めるなら `line_balance: false`（[autofit.md](autofit.md) の「折り返しの規則」）。
- 値が無い variant 名は fail: `variant 'centre' はありません（もしかして center） → title の variant: center / left-band / split / bottom（既定の見た目にするなら variant を消すか "default"）`。variant を持たないタイプに書くと未知キーの warn。
- variant が足す領域（`style.panel` `style.deco1` など）も `style` で書ける。飾りの値（`x` `y` `w` `h` `alpha` 0〜1 `radius` `geom` `fill`）が型違いなら fail。
- 4 つの shape × 2 つのテーマで check_layout 不合格 0 を確認済み。

## cards の強弱（`emphasis` / `span`）

```json
{ "type": "cards", "columns": 3, "cards": [
    { "heading": "主役のカード", "body": "…", "emphasis": true, "span": 2 }, { "heading": "補助 A", "body": "…" },
    { "heading": "補助 B", "body": "…", "emphasis": "soft" }, { "heading": "補助 C", "body": "…" }, { "heading": "補助 D", "body": "…" } ] }
```

| キー | 内容 |
|---|---|
| `emphasis` | `true`（主役色 primary で塗り、文字を反転）/ `"accent"`（accent 色で塗る）/ `"soft"`（淡い色 highlight_fill と accent の 2px 枠）。見出し・本文・記号・アイコンの色も反転する。**強調のカードは文字も 1.25 倍** |
| `span` | そのカードが占める列数（1 以上、列数まで）。書いた順に左上から右へ詰め、残りの列に入らなければ次の段へ |

- 強調は主役の 1〜2 枚だけ。同じ大きさのカードを並べて 1 枚だけ濃くする。色は同梱の全テーマで文字 4.5:1 以上。自作テーマで足りなければ `layout.types.cards.grid` の `emph_*` を直す。カード内の文には泣き別れ対策が掛かる（`line_balance: false` で止める）。
- 強調しないカードの文字が大きな箱の中で小さく見えるときは、`style.grid.fit: "content"`（箱を内容の高さに詰める。`density: "read"` では既定）か、カードの数・文字量を調整する。

| 場面 | 文面と直し方 |
|---|---|
| emphasis の値（fail） | `cards[0].emphasis は true / "accent" / "soft" のいずれかで指定してください（'loud'）→ 主役のカードを塗りつぶすなら true（強調しないなら書かない）` |
| span の値（fail） | `cards[1].span は 1 以上の整数で…` / `cards[1].span（4）が列数（3）を超えています → span を 3 以下にするか、columns を増やす` |
| 強調が多い（warn） | `強調（emphasis）のカードが3枚あります（2枚まで）→ 全部を強調すると強調にならない。主役の 1〜2 枚だけにする` |
| 段に空き（warn） | `span の組み合わせで2段目に空きができます → 段ごとの span の合計を 3 にそろえる（例: 2 + 1、1 + 1 + 1）か、カードの順番を替える` |

## 画像を端まで（`image` / `image_text`）

| キー | 内容 |
|---|---|
| image: `fit` | `contain`（既定。今のまま）/ `bleed`（画像を全面に敷き、タイトルを覆いの上に重ねる） |
| image: `overlay` `opacity` `position` | `fit: "bleed"` のときだけ。背景と同じ（覆いの濃さを自動選択）。`bleed` でないときに書くと warn |
| image: `caption_position` | `below`（既定）/ `band`（キャプションを帯の中に。`contain` では画像の下に色の帯、`bleed` では下端に半透明の帯）。`band` は `caption` が必要（無ければ帯を出さず warn） |
| image_text: `bleed` | `true` で画像側を上下と画面の端まで届かせる（`image_side: "left"` でも）。画像は cover・覆いなし。`position` で切り抜き位置。画像が右のとき、右上の `meta.brand` は画像の上の文字として扱い、画像の明暗から白か濃い色を選ぶ（画像が中間の明るさだと対比の警告が出る。`image_side: "left"` では brand は文字側にあり従来どおり） |

画像のエラーは `N枚目（type=image）: background.image: …` の形。`bleed` は true / false（文字列は fail）。全面の画像のスライドは `check_visual` の空白帯の判定から外れる。

## 既定値の置き場所

`templates/layouts/default.json` の最上位 `variants.<タイプ>.<名前>`（領域の差分）、`palettes.<タイプ>.light|dark`（背景の上の文字色。`_fallback` は対比が足りないときの代わりの色）、`variant_defaults`、`types.cards.grid` の `emph_*`。shape / テーマの `layout` の差分にもこの 3 つを書ける（[themes.md](../themes.md)）。

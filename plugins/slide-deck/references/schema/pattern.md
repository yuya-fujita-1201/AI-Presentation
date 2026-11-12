# `pattern` — 構図の型を登録して再利用する

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。

「この構図をまた使いたい」スライドを JSON の型（パターン）として登録し、中身（スロット）だけ差し替えて何度でも使う。色はテーマトークンで持つので、テーマを変えれば配色も追随する。HTML と PPTX の両方で図形・文字がネイティブ（PowerPoint で 1 つずつ編集できる）になる。

**構図を作りたいときは `pattern` を使う。`canvas` の手書きは取り込み結果の修正に限る**（canvas はテーマ切替・共通パーツ・自動フィットが効かないため）。同梱にも登録済みにも合う型が無ければ、近い型を選んで別のタイプ（`cards` / `two_column` など）で作るか、型を新しく起こす（下記「型を起こす」）。1 枚に型と他の要素を並べたいときは、body 枠の型を [composite.md](composite.md) のブロック（`{"type": "pattern", …}`）か `split` の本文側に置く。

## スライドの書き方

型の枠（`frame`）で 2 通りある。使えるパターンと枠は `pattern_engine.py list` / `show` で確かめる。

**`frame: "full"`（既定）** — 1280×720 全面を型が描く。見出し・罫線・フッターも型の中にある。タイトルはスロット（`slots.title`）。スライド直下の `title` `eyebrow` `lead` `conclusion` `source` と `style` は描かれず、ビルドが警告する（`frame:"full" の型は全面を自分で描くため、スライド直下の conclusion は描かれません → slots の "conclusion" に書いてください`。型にそのスロットが無ければ「frame:"body" の型を使うか、型にスロットを足してください」）。スライド直下の `title` も同じ警告（`スライド直下の title は描かれません → slots の "title" に書いてください`）で、見出しは必ず `slots.title` に書く。合成・split のブロックの仮の `title` には出ない。

```json
{"type": "pattern", "pattern": "conclusion-evidence",
 "slots": {
   "title": "小さく始めて、効果を確かめてから広げる",
   "conclusion": "まず1部署で3か月試し、成果が出た業務から全社へ広げる",
   "evidence": [{"head": "失敗しても損失が小さい", "body": "対象を1部署に絞る"},
                {"head": "効果を数字で比べられる", "body": "導入前後を同じ方法で測る"}]},
 "notes": "..."}
```

**`frame: "body"`** — 標準の見出し骨格（eyebrow / title / rule / lead / フッター / 結論帯 / 出典）はプラグインが描き、型は本文領域だけを描く。`title` `lead` `conclusion` `source` はスライド直下に書き、見出しの `style`（`style.title.size` など）は他のタイプと同じに効く。型は設計寸法（`size`、既定 1136×480）の中で書かれ、ビルド時に実際の本文矩形（lead・結論帯・出典の有無で変わる）へ縦横比を保って写される（余りは上寄せ・左右中央）。

```json
{"type": "pattern", "pattern": "numbered-columns", "title": "小さく試し、効果が出た業務から広げる", "lead": "（任意）",
 "slots": {"items": [
   {"head": "現状の把握", "body": "今の手順と所要時間を一覧にする"},
   {"head": "試す範囲を決める", "body": "失敗しても影響が小さい1業務から始める"},
   {"head": "小さく動かす", "body": "1か月だけ現場で使い、毎週直す"}]},
 "conclusion": "（任意）", "source": "（任意）"}
```

| キー | 意味 |
|---|---|
| `pattern` | パターン名（`<名前>.json` のファイル名）。必須 |
| `slots` | スロット名 → 値。値の形はパターンごと（下の「スロットの種類」）。必須スロットが無いとビルドが止まる |
| `title` / `lead` / `conclusion` / `source` | `frame: "body"` の型のみ（見出し骨格に出る。`title` が無いと警告）。`frame: "full"` では使えない（タイトルは `slots.title`、他は上の警告） |
| `notes` | HTML のみのスピーカーノート（他のタイプと同じ） |

- **使えるパターンを調べる**: `python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_engine.py" list [--deck <deck_dir>] [--detail]` は 1 型 1 行の表（名前・枠・個数・ブロックに置けるか・何を言うときに使うか）。`… show <名前>` は説明・幅の下限・スロット（文字数の目安・値の候補）と、**そのまま deck.json に貼れる例**（body 枠の型は `title` `lead` `conclusion` `source` つき）を出す。任意の画像スロットは例から外してある（写真なしの構図。画像を使う手順は `show` の末尾）。
- **確認用デッキ**: `… preview [--deck <deck_dir>] [--theme <名前>] [--out <DIR>]` は、探索先にある全パターンを例文（slots の `example`）で 1 枚ずつ並べた確認用デッキを作ってビルドする（いま何が使えるかの一覧）。`… sample <名前> --out <DIR> --theme <T1> <T2>` は 1 つの型を複数テーマで展開して見比べる。
- **置き場所と探索順**（先に見つかったものが勝つ）: 索引の「テーマ・レイアウト・パターンの探索順」と同じ。環境変数 `SLIDE_DECK_PATTERNS` → `<deck_dir>/patterns/` → 親（3 階層上まで）の `patterns/` → カレントの `patterns/` → 同梱 `templates/patterns/`。
- **警告・エラー**（`N枚目（type=pattern, pattern=名前）: 内容 → 直し方`）:
  必須スロットが無い（空白だけの項目しか無いときも含む）・値の型が違う・画像のパスが使えない（`スロット 'photo' の画像 '…' が使えません: …`）・パターンが見つからない（もしかして候補つき）はビルド停止。未知のスロット名（候補つき）・文字数の目安（`max_chars`）超過・個数（`min` / `max`）の範囲外・空白だけの項目（`N 個目が空です（無視します）`）・自動フィットの最小サイズでも文字が枠に収まらないときは警告（ビルドは続く）。
- **個数が `max` を超えたとき**: **超えた分は描かない**（先頭の `max` 個だけ。構図もその個数用が選ばれる）。警告は 1 回: `スロット 'items'（項目）が 6 個で、最大 5 個を超えています → 6 個のうち先頭の 5 個だけ描きました（残り 1 個は描きません）。5 個までに絞るか、2 枚に分けてください`。描かれなかった項目は内容が落ちるので、**警告が出たら個数を減らすか 2 枚に分ける**。
- **値の整形**: 数値は桁を落とさず指数表記にもしない（`1234567.0` → `1234567`）。金額・コード番号などは文字列で渡すほうが確実。XML で使えない制御文字（PDF からの貼り付けで混じる）は黙って取り除く。空白だけの list / records の項目は捨てる。
- 根拠が無い値は `【要確認: …】` と文字列で書く（索引の「根拠が無い箇所は `【要確認】` と書く」）。

### スロットの種類（パターン JSON の `slots`）

| `kind` | スライド側の値 | 補足 |
|---|---|---|
| `text` | 文字列（改行 `\n` 可） | `max_chars`＝文字数の目安 |
| `list` | 文字列の配列 | `min` / `max` / `max_chars`（1 項目の目安） |
| `records` | オブジェクトの配列 | `fields`（項目名 → `{kind, max_chars, required}`）、`min` / `max` |
| `image` | デッキからの相対パス（`assets/photo.png`） | `..`・絶対パス・未対応の拡張子・存在しないファイルはエラー |
| `flag` | 真偽（true / false、「○」「なし」など） | 型の中の `if` で出し分ける。文字としては差し込まれない |

共通: `required`（true で必須）、`label`（表示名）、`default`（省略時の値）、`example`（例文。`show` / `check` / 確認用デッキで使う）。

## 同梱パターン（19 個）

`templates/patterns/*.json`。全面（`frame: "full"`）が 3 つ、本文（`frame: "body"`）が 16 個。最新の説明は `pattern_engine.py list` / `show <名前>` が正（下の表は要約）。色はテーマトークン、文字の大きさ・角丸・線は形トークン、面の影は `$shadow.card` で、テーマ 2 種 × shape 4 種に追随する。**並びの中の全項目は同じ文字サイズにそろう**（短いほど大きく、1 項目だけ長いと全体がそれに合わせて縮む）。標準の本文領域で、本文の型の最小文字は約 15px（photo-caption の出典）、見出し・説明は 18px 以上。

「ブロック」= 合成スライドのブロックや `split` の本文側に置けるか（[composite.md](composite.md)。判定は置く矩形の幅で決まる）。本文の型 16 個はすべて、幅と高さに応じて構図が切り替わる（下の「幅に合わせた構図」）。列の値は `pattern_engine.py list` と同じ: **◎ 半幅可 NNNpx〜** = 全個数で半幅（約 556px）から読める。NNN はどの個数でも読める最小の幅で、これより狭いと警告が出る（個数ごとの下限は `show` の「幅の下限」）。全面の型は **×**（置けない。fail）。3 分の 2 幅から読める「○」と、より広い幅が要る「△」の段階も表示の規則にはあるが、同梱の型に該当するものは無い。

| 名前 | 何を言うときに使うか | スロットの要約 | 個数 | ブロック |
|---|---|---|---|---|
| `conclusion-evidence` | 左に大きな結論文、右に根拠（結論が主役のページ） | `title` `conclusion` `evidence`（records: `head` `body`） | 根拠 2〜4 | × |
| `before-after` | 変化の前後を左右に並べ、下に一言 | `before` / `after`（list）`message` | 各 2〜5 | × |
| `pillars` | 戦略の柱・方針を 3〜4 本のカードと土台の一文で | `pillars`（records）`foundation` | 柱 3〜4 | × |
| `keyword-explain` | 大きな一言（合言葉・方針）を左、理由を右に | `keyword` `label` `caption`、`points`（`head` 16 字 / `body` 44 字） | 説明 2〜4 | ◎ 410px〜 |
| `numbered-columns` | 手順・段階を番号つきで横一列に | `items`（`head` / `body`） | 3〜5 | ◎ 400px〜 |
| `numbered-list` | 約束・原則・手順を 1 項目ずつ重く縦に（番号が主役） | `items`（`head` 14 字 / `body` 50 字） | 3〜5 | ◎ 390px〜 |
| `checklist` | どこまで終わったか（完了・進行中・未着手） | `items`（`text` 24 字 / `note` 14 字 / `state` = done・wip・todo と別名） | 3〜7 | ◎ 470px〜 |
| `big-number-context` | 成果・実績の大きな数字と、その意味 | `value`（必須・7 字）`unit` `label` `delta`、`points`（`head` / `body` 50 字） | points 2〜3 | ◎ 420px〜 |
| `quote-block` | 第三者の声で主張を裏づける（全面の引用は `type: "quote"`） | `quote`（100 字）`name` `role` | — | ◎ 390px〜 |
| `funnel` | 段階ごとに数が絞られる話（営業・採用・申込） | `stages`（`name` 8 字 / `value` 6 字 / `body` 32 字・任意） | 3〜5 | ◎ 390px〜 |
| `pyramid` | 土台から積み上げる話（成熟度・優先度） | `tiers`（`name` 6 字 / `body` 32 字・任意）。一番上の段から | 3〜5 | ◎ 380px〜 |
| `problem-solution` | 課題 → 打ち手 → 効果の筋道 | `problems` / `actions` / `effects`（list・22 字） | 各 2〜3 | ◎ 380px〜 |
| `roadmap-lanes` | いま／次／その先の計画 | `now` `next` `later`（list・24 字）、`*_label` `*_when` | 各 1〜3 | ◎ 380px〜 |
| `compare-options` | 2〜4 案を同じ観点で比べる | `options`（`name` / `tag` = 推奨の案だけ）、`rows`（`label` / `values` = 案と同じ個数） | 案 2〜4、観点 2〜4 | ◎ 500px〜 |
| `icon-grid` | 順位のない特長・理由・機能 | `items`（`head` 12 字 / `body` 32 字 / `mark`） | 3〜6 | ◎ 470px〜 |
| `team` | 体制・担当者の紹介 | `members`（`name` `role` `body` 28 字 `initial`） | 3〜6 | ◎ 500px〜 |
| `timeline` | いつ何をするか（計画・沿革）を時間順に | `items`（`date` / `head` 10 字 / `body` 26 字 / `now` = 現在地・1 つだけ） | 3〜6 | ◎ 470px〜 |
| `quote-photo` | 人の言葉に顔写真を添える（写真は省略可） | `quote`（90 字）`name` `role` `photo`（image・任意） | — | ◎ 380px〜 |
| `photo-caption` | 大きな写真に見出しと説明（写真は省略可） | `photo`（image・任意）`headline` `body` `label` `credit` `photo_right` | — | ◎ 470px〜 |

**選び方の目安**（似た型・タイプとの見分け）:
- 順番がある 3〜5 項目: 横一列で短く → `numbered-columns`、縦に 1 項目ずつ重く → `numbered-list`、日付がある → `timeline`、数が減る → `funnel`。
- 左に大きな一言: 言葉・方針 → `keyword-explain`、単位つきの実績の数字 → `big-number-context`（数字だけなら `kpi`）。
- 並べて比べる: 前後 → `before-after`、2〜4 案を観点で → `compare-options`（行数が多い一覧は `table`）。
- 段階: 土台から積む → `pyramid`、課題から効果まで → `problem-solution`、計画の優先度 → `roadmap-lanes`。
- 同じ重さで並べる: 本文の中に 3〜6 個 → `icon-grid`（見出し＋本文だけなら `cards`）、全面で柱と土台 → `pillars`、人 → `team`（組織図は `org`）、確認事項 → `checklist`。
- 引用: 全面で言葉だけ → `quote`、見出しつきスライドの本文に言葉 → `quote-block`（顔写真があれば `quote-photo`）。写真が主役 → `photo-caption`。

**注意**:
- 幅の下限を下回る矩形に置くと `この型（icon-grid）は 6 個のとき 幅 470px 以上向きです（いま 440px） → …` の警告が出る。直し方は文に並ぶ: ブロックを広げる（`col_span` で横に広げる・`columns` の比率を変える）・単独のスライドにする・項目を減らす（「項目を 5 個までにする（5 個なら幅 440px 以上で読める）」は、減らせば警告が消えるときだけ出る）・代わりの型か箇条書きにする。**3 分の 1 幅（約 360〜400px）で全個数が読める型は無い**（最小の下限が 380px）。半幅は 440〜500px が実用の下限。
- 全面の型（×）を合成スライド・split のブロックに置くと fail。
- `compare-options` の `values` は「比べる案」と同じ個数・同じ並びで書く（食い違うと項目ごとではなく 1 本の警告。足りない列は「―」）。`tag` は 1 案だけ。
- `timeline` の `now` は 1 つだけ（真偽。「現在地」「○」など何か書けば真、false・no・無・空なら通常。「true」という札は出ない）。
- `funnel` / `pyramid` の `body` は任意。**全段で省くと、図を大きく中央に置く構図に切り替わる**。一部の段だけ書くと、書かない段は右側が空く。
- `checklist` の `state` は done（済・完了…）/ wip（中・進行中…）/ todo（未・空）。別名は自動でそろい、候補外の値は**未着手として描かれ**警告が出る（`false` は完了にならない）。
- 画像つきの 2 型の例の画像は `templates/patterns/assets/`。`show` の例は写真なしの構図で、そのまま貼ってビルドできる。写真を使うときは slots に `"photo": "assets/….png"` を足し、画像をデッキの `assets/` に置く。写真を渡さないと文章だけを大きく置く構図になる。

```json
{ "type": "pattern", "pattern": "checklist", "title": "開院まで、残るのは3つの確認", "lead": "消防検査と校正は終わった",
  "slots": { "items": [
    {"text": "消防検査に合格する", "note": "施設課", "state": "done"},
    {"text": "スタッフ研修を実施する", "note": "看護部", "state": "進行中"},
    {"text": "開院日を地域へお知らせする", "note": "11月28日"} ] } }
```

## パターン JSON の書き方（`templates/patterns/<名前>.json`、または `<deck_dir>/patterns/<名前>.json`）

```json
{
  "name": "conclusion-evidence", "label": "結論と根拠", "description": "…", "version": 1,
  "frame": "full", "background": "background",
  "slots": { "title": {"kind": "text", "required": true, "max_chars": 34, "example": "…"},
             "evidence": {"kind": "records", "min": 2, "max": 4, "fields": {"head": {}, "body": {}}} },
  "elements": [ …canvas 要素… ],
  "variants_by": "evidence", "variants": {"3": {"elements": [ … ]}, "4": {"elements": [ … ]}}
}
```

`frame: "body"` の型は `"size": [幅, 高さ]`（設計寸法。既定 1136×480）の中の座標で `elements` を書く。`elements` は canvas の要素（x y w h・geom・fill・line・text …。座標は px）にパターン用の記法を足したもの。

- **色**: テーマの色トークン名（`primary` `surface` `on_primary` …）か `#RRGGBB` / `#RGB`。`{"color": "primary", "alpha": 0.5}`・グラデーションの stops・パターン塗りの `fg` / `bg` も同様。`background` も同様。
- **フォント**: `"font": ["@heading"]`（見出し）/ `@body` / `@code`。`font` を省略した文字は `@body`。
- **文字サイズ・数値のトークン**: 数値 px のほか `"$type.h1"` `"$radius.card"` `"$line.normal"`（テーマの `tokens`、無ければ既定の表: type = display 60 / h1 36 / h2 28 / h3 22 / body 20 / small 16 / caption 13、radius = card 12 / small 6 / pill 999、line = thin 1 / normal 2 / bold 4）。
- **`radius`**: 要素に `"radius": 12`（または `"$radius.card"`）と書くと角丸の四角（roundRect）になり、短辺に対する割合を自動計算する（大きさが変わっても同じ丸み）。
- **差し込み**: 文字（run の `text`）と `name` / `alt` / `label` / `path` に `{{slot}}`。繰り返しの中では `{{cards.head}}`（または項目名だけの `{{head}}`）・`{{.}}`（今の 1 件）・`{{index}}`（1 始まり）・`{{count}}`。組み込み変数: `{{page}}` `{{total}}` `{{deck.title}}` `{{deck.brand}}` `{{slide.title}}`。スロットの値の中の `{{` は再展開しない。差し込みがすべて空になった段落は出さない（`"keep": true` で残す）。
- **条件**: 要素・段落・run に `"if": "note"`（スロットが空でなければ出す）/ `"if": "!note"`（空のとき出す）/ `["a", "!b"]`（全部が真）。繰り返しの中では `"@first"` `"@last"` `"@odd"` `"@even"`。
- **段落の繰り返し**: 段落に `"repeat": "points"` を書くと、list / records の項目ごとに段落を作る（箇条書き）。
- **要素の繰り返し（等間隔のセル）**: `{"repeat": "cards", "grid": {"x": 72, "y": 160, "w": 1136, "h": 420, "cols": "auto", "gap": 20}, "template": [ …セル内の要素… ]}`。`cols: "auto"` は個数から決める（4 個まで = その個数の列、5〜8 個 = 2 行、9 個 = 3×3 …）。`gap` は数値か `{"x":…,"y":…}`、`cell_h`（セルの高さを固定）、`last_row: "center"`（最後の行を中央寄せ）。template の要素はセルの左上からの相対配置: `x` `y` と大きさ `w` `h`、または右・下の余白 `r` `b`（`w` の代わりに `r` を書くと「セル幅 − x − r」）。式は使わない。
- **個数別の別構図**: `"variants_by": "evidence"` と `"variants": {"3": {"elements": [...]}, "4": {...}}`（個数が合う構図の `elements` を共通の `elements` の後ろに足す。無い個数は近い小さい個数の構図で描き、警告）。
- **和文の折り返し（文節単位）**: 文字枠の和文は、展開時に文節の切れ目（「窓口」「1か月」のような語の途中・数字と単位の間を避ける）で改行を入れる。HTML と PPTX は折り返し位置を別々に決めるが、改行を展開結果に入れておくので両方で同じ位置になる。折り返さない枠（`text.wrap: false`）・縦書き・和文を含まない文・すでに改行のある文には掛からない。止めたい要素には `"balance": false`。
- **文字枠の自動フィット**: 文字を持つ要素に `"fit": {"sizes": [28, 24, 20, 16]}`。文字量から、枠に収まる最大のサイズを選ぶ。run の `size` に `"@fit"` と書いた文字だけがそのサイズになる（`@fit` が無いときは全 run を `sizes[0]` からの比率で拡縮する）。最小でも収まらないと警告。折り返さない枠（`text.wrap: false`）は高さだけを見る。縦書き（`text.vert`）は行の長さを枠の高さとして見る。（画像要素の `fit: "cover"` とは別物。dict なら文字のフィット、文字列なら画像の収め方。）
- **行間**: 展開結果は、全段落が固定の行送り（`lineHeightPx` = 文字サイズ × 1.2 × `lineHeight`、既定 1.15）になる。PowerPoint でもフォントに関係なく同じ行送り。
- **画像**: `{"kind": "image", "path": "{{photo}}", …}` と image スロットを組み合わせる（要素の書式は [canvas.md](canvas.md)）。
- **検証**: `python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_engine.py" check <ファイル> [--theme <名前>]`。構造（slots・repeat・変数の参照・fit の形）、例の値（と `min` / `max` / variants の各個数、grid で繰り返すスロットは `max`+1 個も）で展開した結果の色トークン・canvas 検証・文字あふれをまとめて調べる。名前のない要素は `elements[2]` / `elements[3].template[1]` のように位置で示す。grid で繰り返すスロットに `max` が無いと警告（個数が増えたとき枠が潰れるため）。型を作るときは、枠に収まる最大の個数を `max` に書く。

### 型エンジンに足した書き方（型を作る人向け）

既存の型 JSON は書き換えなくてもそのまま動く。

- **文字サイズをそろえる `fit.group`**: 文字枠の `fit` に `"group": true`（`repeat` の `template` の中で、同じテンプレート位置の枠どうし。外では警告）か `"group": "名前"`（その名前の枠どうし。離れた枠も横断）。各枠が単独で収まる最大サイズを求め、**その最小**を全員が使う。`sizes` に形トークン（`"$type.h3"`）を書ける。最小サイズでも収まらない枠があるとグループで 1 回だけ警告する。
- **`if` の拡張**: `{"slot": "state", "is": "done"}`（等しい。全角半角・大文字小文字・前後の空白は無視。`"is": ""` で空）、`{"slot": "state", "in": ["wip", "todo"]}`、`{"not": 条件}`。集計は `{"slot": "stages", "field": "body", "any": false}`（records の全項目で `body` が空のとき真。繰り返しの外で使う。`is` / `in` とは併用不可）。
- **値の候補と別名 `values`**: text のスロット・records の項目に `"values": {"done": ["済", "完了"], "wip": ["中"], "todo": ["", "未"]}`（正規の値 → 別名）。展開前に別名を正規の値にそろえてから `if` で見る。候補に無い値は警告。どう描くかは `"unknown_as": "todo"` で宣言する（無ければ `is` / `in` がどれも偽）。`{{state}}` と差し込むと正規の値が出る。
- **真偽 `"kind": "flag"`**: `false` `"no"` `"0"` `"×"` `"なし"` 空などは偽、何か書いてあれば真。`{{now}}` と差し込んでも文字は出ない。records の項目の `list`（文字列の配列）は `{{values.2}}`（**1 始まり**。`{{values.0}}` は差し込みエラー）。
- **個数の対応 `count_of` と 1 つだけ `at_most`**: スロット・項目に `"count_of": "別のスロット名"` を書くと、個数が違うとき項目名ごとに 1 本の警告。`"at_most": 1`（flag か text の項目）は、真が 2 個以上あると警告する（強調を 1 か所に絞る型用）。
- **`max` の打ち切り**: 上の「個数が `max` を超えたとき」のとおり、超えた分は描かない。
- **幅の下限 `min_width` と狭い構図 `narrow`**（frame: body）: `"min_width": 900` は、実際の矩形に写したあとの幅の下限（下回ると警告）。`"narrow": {"below": 900, "size": [556, 400], "elements": […], "variants_by": "items", "variants": {…}}` は、矩形の幅が `below` 未満のとき `size` / `elements` / `variants` をこの構図に**差し替える**（`slots` は共通）。`check` は狭い構図も全個数で展開して検証する。同梱の型の使い方は下の「幅に合わせた構図」。

- **影 `"shadow": "$shadow.card"`**: 要素に形トークンの影を書ける（`shape: soft` のとき付く。他の shape では付かない）。`{"dx":…, "dy":…, "blur":…, "color":…}` の dict は従来どおり canvas の影そのもの。
- **画像つきの型**: 例の画像は型 JSON の隣の `assets/` に置き、スロットの `example` に `"assets/sample.png"` と書く。`preview` / `sample` はそれを出力先の `assets/` に写す。画像スロットが空のときの構図は `"if": "photo"` / `"!photo"` で切り替える。
- **型の説明キー**: `summary`（`list` に出す 1 行）、`example_page`（`show` の例の見出し・リード・結論・出典）。
- **和文の折り返し**: 「週2回」「第3期」の空白の前後や、仮名の動詞・活用語の途中では切らない。複数 run の段落（色違いの引用など）も 1 つの文として文節で折る。エンジンが折って最終行が 1〜2 文字になる文字枠は、展開で 1 本の警告にまとめる（`その文を少し言い換える・字数を増減して、行の終わりに 3 文字以上が残るようにしてください`）。
- **見出し骨格を自前で描く `frame: "full"` の型**: 要素に `"role": "title"` / `"rule"` / `"eyebrow"` を付けると、選んだ shape の罫線・字間・太さに追随する。面の角は `"radius": "$radius.card"`（箱）・`"$radius.cell"`（柱などの面）・`"$radius.image"`（画像）で書く。
- 単独の pattern スライドで結論帯・出典があり本文領域が低いとき、型は縮み、下端と帯のあいだに 20px 以上の隙間を残して上詰めで置く。

### 幅に合わせた構図（`narrow` の配列・高さの条件・文字の実測）

同梱の本文の型 16 個は、置く矩形の**幅と高さ**で構図を切り替える（幅 1000px 以上・高さ 340px 以上は広い構図 = 単独のスライドと同じ）。合成スライドの半幅・3 分の 2 幅のブロック、split の本文側、`style.body` で絞った単独のスライドに置いても、描かれる文字は 12px 以上（札・タグ・印は 11px 以上）に収まる。

`narrow` は辞書 1 つのほか、**辞書の配列**でも書ける。矩形の幅 w・高さ h に対し、`w < below`（段に `below_h` があれば `h < below_h` も）を満たす段のうち **`below` が最小のもの**（同じ `below` なら高さの条件つきが先）が使われ、どれにも当たらなければ広い構図（型本体）。

| キー | 意味 |
|---|---|
| `below` | この幅（px）**未満**で使う（正の有限の数。段ごとに違う値。同じ値は `below_h` で区別する） |
| `below_h`（任意） | 矩形の高さがこの値**未満**のときだけ使う短い構図（上下 2 段の合成・短い split 用。同梱の型は 340） |
| `size` | その構図の設計寸法 `[幅, 高さ]`。文字・線・余白の倍率 k は `min(矩形の幅 / 設計幅, 矩形の高さ / 設計高さ)` |
| `elements` / `variants` / `variants_by` / `valign` | 広い構図と同じ書き方（スロットは共通） |
| `min_width`（任意） | この構図が読める矩形の幅の下限。下回ると警告。幅だけで選ばれる最も狭い段に書く |
| `min_width_by_count`（任意） | 個数ごとの下限（`{"6": 470}`）。`min_width` より厳しい個数だけ書く |
| `no_max_width` / `max_stretch`（任意） | `no_max_width: true`（`below_h` とセット）は、幅が `below` 以上でも高さが `below_h` 未満ならこの段を使う。`max_stretch` は横に広げてよい倍率の上限（既定 1.25）。同梱の型は `no_max_width` を使っていない |

- **置き方**: 狭い構図は矩形の幅いっぱいまで横に広げる（k の `max_stretch` 倍まで。円・楕円は縦横比を保つ）。縦は k のままで、余りは `valign`。幅 700〜1000px で、1000px の前後の左端が跳ばず、合成スライドのほかのブロックの端とそろう。広い構図は従来どおり縦横比を保って中央に置く。
- 型の最上位に **`block_alt`**（文字列）を書くと、幅の下限の警告の末尾に「代わりの手」として出る（個数を減らす提案は書かない。減らして下限を満たせる個数があるときだけ、エンジンが自動で足す）。
- **文字の実測の警告**: ビルドは、型を矩形に置いたときに**描かれる文字の最小サイズ**（設計の文字 × 縮小率）を測り、12px 未満（札・タグ・印は 11px 未満。要素名に「札」「タグ」「印」を含むものを札として扱う）なら警告する。`この型（team）は 556×260px だと、文字が最小 11.7px まで小さくなります（…。目安は 12px 以上） → ブロックの高さを広げる（rows の比率、row_span）・項目の数を減らす・文を短くする・単独のスライドにする`。**高さ 260px 以下**は設計高さ 300px の構図をさらに縮めるので 10〜12px 台になり、この警告が出る。
- `check` は段ごとに全個数で展開して検証する（メッセージに「（狭い構図 2: 幅 700px 未満・高さ 340px 未満）」が付く）。`below`（と `below_h`）の重複・`min_width_by_count` の形・`block_alt` の型・有限でない値は error。壊れた型 JSON でも `list` / `show` はトレースバックを出さない。`show` に個数別の下限と段ごとの設計寸法が出る。

同梱の型の幅の下限と、幅ごとの構図（実測の下限。高さ 400px・標準の長さの文で、警告と孤字が 0 になる最小の幅）:

| 型 | 下限（個数別） | 700px 未満（半幅）の構図 | 700〜1000px 未満（3 分の 2 幅） | 高さ 340px 未満の短い構図 |
|---|---|---|---|---|
| `icon-grid` | 380（3）・390（4）・440（5）・470（6） | 1 列の横長カード | 2 列（3 個は 1 列） | 3・4 個は 1 列、5・6 個は 2 列 |
| `numbered-columns` | 380（3・5）・400（4） | 円の番号を線でつないだ縦のリスト | 同（幅が広い） | あり |
| `keyword-explain` | 380（2・3）・410（4） | 上に一言の帯、下に説明を縦に積む | 一言の面を細くして左、説明を右 | 一言の面を左・説明を右 |
| `problem-solution` | 380 | 3 段の縦積み（下向きの矢印） | 左に見出しの札・右に点の面 | 左に札・右に点 |
| `timeline` | 440（3〜5）・470（6） | 縦の時間軸 | 日付・点・名前 \| 一言の 3 列 | あり（6 個は行を詰める） |
| `compare-options` | 440（2 案）・470（3 案）・500（4 案） | 行ラベルを詰めた表 | 表 | 見出しの行を低く |
| `team` | 390（4）・440（3）・450（5）・500（6） | 1 列の横長カード | 2 列（3 人は 1 列） | 5・6 人は 2 列 |
| `roadmap-lanes` | 380 | 3 列を縦に積む | 同 | なし（高さ 300 でも 12.8px 以上） |
| `pyramid` | 380 | 細いピラミッド＋説明を右へ（頂点の名前は台形の幅に合わせ 2 行に折る） | 同（大きめ） | なし |
| `photo-caption` | 470 | 写真を上（帯状）、文章を下 | 写真 330px を左右に | 写真を左・文章を右 |
| `quote-photo` | 380 | 引用を上、丸い顔写真と名前・肩書きを下 | 左に写真、右に引用 | なし |
| `numbered-list` | 390 | 見出しの下に説明 | 番号・見出し・説明の行 | なし |
| `checklist` | 390（3〜6）・470（7） | 担当・期限を内容の下に | 担当・期限を右に残した行 | あり |
| `big-number-context` | 420 | 数字を上、意味を下 | 左に数字、右に意味 | なし |
| `funnel` | 390 | じょうごを細くして説明を右に | じょうごを大きめに | なし |
| `quote-block` | 390 | 言葉を上、名前・肩書きを下 | 同 | なし |

- 高さ 300px・幅 556px 以上のブロックは、全型で警告なし・最小文字 12px 以上（実測）。幅 480px では一部の型で 11〜12px 台になる。
- 幅 1000px 以上で高さ 340px 未満のブロック（上下 2 段の各 1136×240〜288 など）は、短い構図を持たず広い構図を縮めて置く。「本文領域が小さすぎて、型を 60% に縮めます（本文領域 1136×240・型の設計寸法 1136×400）」の警告が出る（文字が 12px 未満になれば上の「文字が最小 N px まで…」も出る）。**高さを広げる（`rows`・`row_span`）か、項目を減らす・単独のスライドにする**。
- 内容がいっぱいに近い組は、幅 700px 未満で「…の文字が最小サイズ 18px でも枠に収まりません（必要な高さ約 69px / 枠 54px）」の警告になる。文を短くするか項目を減らす。目安: keyword-explain 4 点 × 説明 44 字 / numbered-columns 4〜5 項目 × 70 字 / funnel 5 段 × 説明 32 字 / big-number-context 3 点 × 説明 50 字 / compare-options 4 案 × 全セル 18 字 / team 6 人 × 仕事 28 字 / numbered-list 5 項目 × 50 字（高さ 300px）。通常の長さの文なら、各型の下限以上の幅・高さ 300px 以上で警告は出ない。
- `photo-caption` の写真の出典、`quote-block` / `quote-photo` の名前・肩書きは、狭い構図では文章と別の枠（固定サイズ）になり、文章が長くても縮まない。
- 文字組みは全幅で、枠の幅にちょうど収まる 1 行（約千二百万円必／要の 1 文字折り返し）を折り、最終行が 1〜2 文字になる大きさを避ける（無ければ大きいほうを使い、展開で「文字枠 N 個で、最終行が 1〜2 文字だけになります」の警告）。

## 型を起こす: `pattern_from_pptx.py`

既存の PowerPoint の 1 枚、またはこのプラグインのデッキの 1 枚（ビルドしてできた PPTX の N 枚目）から、型の JSON を起こす。

```
python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_from_pptx.py" <src.pptx> --slide N --name <名前> [--theme <テーマ名>] [--dir DIR] [--keep-master] [--confirm]
python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_from_pptx.py" --from-deck <deck_dir> --slide N --name <名前> [--theme …] [--dir …]
python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_from_pptx.py" --from-deck <deck_dir> --deck-slide M --name <名前>      # deck.json の M 枚目から
```

`--slide` は **PPTX 上の枚数目**。agenda の分割・swimlane / 図解の凡例ページが入るため、deck.json の番号とずれることがある。実行時に「PPTX の N 枚目 = deck.json の M 枚目（type=xxx）」を表示する（凡例ページなど deck.json に無いページを指定したときは注意を出す）。deck.json の番号で指定したいときは `--deck-slide`（`--from-deck` 専用）。

- マスター・レイアウト由来の図形は型に入れない（一覧に出す。`--keep-master` で固定の飾りとして残す）。
- 色は Lab 距離（ΔE76 ≦ 6）で近いテーマトークンに寄せる。寄せ切れない色は hex のまま残し、一覧に出す（テーマを変えても色が変わらない）。寄せ先は `--theme`（省略時: `--from-deck` はデッキのテーマ、PPTX は使われている色に一番合う同梱テーマ）。
- 文字は段落単位でスロットにする（見出し = プレースホルダーの title か最大サイズ、箇条書きは list スロット＋段落の repeat）。例文は `example`、`max_chars` は例文字数の 1.5 倍を目安に。スロット名は役割が分かるようにする: 同じ形の箱が 3 つ以上並ぶなら箱の中の文字を `card1_head` / `card1_sub` / `card1_points`、見出しの上の小さな文言は `kicker`、見出しの直下は `lead`、最下部の小さな文言は `footer`、それ以外は `text1…`。ページ番号は `{{page}}` / `{{total}}` に戻す。`--from-deck` では、`meta.title` / `meta.brand` と同じ文言の文字枠も `{{deck.title}}` / `{{deck.brand}}` に戻す。段落内の改行は `\n` として例文に残す。書式が実際に違う run が混ざる段落だけ「複数の書式が混ざる」と報告し、先頭の書式で 1 つのスロットにする。文字枠には `fit` を付ける。箇条書きスロットの `max` は、元の個数から「fit の最小サイズで枠に収まる個数」までにする（元の個数 +2 まで）。
- 画像の枠は image スロット（画像が無いときは枠のまま）。表・アイコン（SVG）は固定のまま。
- 同じ大きさの図形が等間隔に並ぶ箇所は「repeat にできる候補」として報告する（自動では書き換えない。JSON の `elements` を `repeat` + `grid` + `template` に手で直す）。
- 出力: `<dir>/<名前>.json` と、確認用デッキ `<dir>/_check/<名前>/deck.json`（1 枚目 = 元と展開結果を並べたもの / 2 枚目 = 元 / 3 枚目 = 例文で展開）。`--dir` の既定は `--from-deck` のとき `<deck_dir>/patterns`、PPTX のとき `./patterns`。
- **同名の型を上書きするには `--confirm` が要る**。既存の型を壊すので、上書きの承認は利用者に確認してから（[../approval-gates.md](../approval-gates.md)）。

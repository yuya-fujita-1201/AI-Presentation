# slide-deck プラグイン

JSON（`deck.json`）をソースにして、スライドを **HTML / PowerPoint(16:9)** にビルドする Claude Code プラグイン（現在 **3.0.0**）。
スライドの**内容もデザインもすべて deck.json のパラメーター**で管理し、色はテーマトークンで切替・追加できる。
目標は「言いたいことを人が話す → AI が骨子を作り、承認を受けてスライドにまとめる → 人は PowerPoint で細かいズレを直さない」。

> 📖 **使い方のスライド版マニュアル**: [`USER-GUIDE.html`](USER-GUIDE.html)（ブラウザで開く。← / → で移動）。この README は概要、USER-GUIDE はダウンロードした人向けの操作マニュアル。ソースは [`manual/deck.json`](manual/deck.json)（本プラグイン自身でビルド）。

社内配布物です。受領者内での利用を想定しており、社外への再配布は想定していません。

## インストール

社内配布は **`slide-deck` フォルダの Zip を受け取って展開**する形式（マーケットプレイスからのダウンロードではない）。配布された Zip を任意の場所に展開し、出てきた `slide-deck` フォルダを指定して Claude Code を起動する:

```
claude --plugin-dir <展開先>/slide-deck
```

（IDE 拡張を使う場合は設定でプラグインフォルダを指定する）

## 初回セットアップ（依存関係）

**Python 3.14 以上が必要**。依存の導入は `/slide-deck:setup` から Claude Code 経由で行うのが最も簡単（内部で下記スクリプトを呼ぶだけ）。この README のとおりターミナルから自分で叩く場合は次節の注意を参照。

```
/slide-deck:setup            # 必須(python-pptx)だけ
/slide-deck:setup --playwright  # プレビューPNG・check_layout・SVG を含むデッキの PPTX 化（playwright + chromium）
/slide-deck:setup --all      # 全部（検査まで使うならこれ）
```
このリポジトリ内で直接叩く場合は `requirements.txt` からもインストールできる: `pip install -r plugins/slide-deck/requirements.txt`。

| パッケージ・ツール | 要否 | 用途 |
|---|---|---|
| `python-pptx` | 必須 | PPTX 生成 |
| `playwright`(+chromium) | 任意（検査には実質必須） | プレビューPNG生成、`check_layout.py` の実測。**SVG の画像を含むデッキの PPTX 化にも必要**（同梱の見本も該当。無いと「PPTX 化に playwright が必要です → `/slide-deck:setup --playwright`」で止まる。HTML だけなら `--html`） |
| `pillow` | 任意 | 一覧シート生成・画像からのテーマ抽出・字幅の実測（`ja_text.py`）・`check_visual.py` |
| `pymupdf` | 任意 | PDF からのテーマ抽出 |
| LibreOffice（`soffice`） | 任意 | `export_pdf.py`・`check_pptx.py`（PPTX の描画） |
| poppler（`pdftoppm`） | 任意 | `check_pptx.py`（PDF を PNG にする） |

### Windows の注意
- `python` が Microsoft Store を開く場合は Python 未インストール（[python.org](https://www.python.org/) から導入）。導入後も見つからなければ `py -3` を使う
- コマンドは PowerShell / Git Bash のどちらでも同じもので動く

## 使い方の流れ（喋る → 骨子 → 承認 → できあがり）

1. **喋る**: 言いたいことを話す（書き起こし・メモ・既存資料を渡してもよい）。聞き手・目的・持ち時間が決まっていなくても、AI が骨子の前提欄に仮置きして先へ進む
2. **骨子**: AI が `outline.md`（スライドごとの結論文・根拠と出どころ・使うタイプとその理由・要確認）をデッキのフォルダに書く。タイトルだけを順に読んで話が通るかも確かめる
3. **承認**: 前提込みの骨子を見て、直しを伝える。**承認は 1 回**で、以降は確認なしで最後まで進む（「おまかせ」「すぐ作って」なら見せるだけで進む）。設定フォームは出さない。選びたいと頼んだときだけ出る
4. **できあがり**: `deck.json` を書く → ビルド（HTML + PPTX）→ 機械チェック → プレビューの目視 → 引き渡し。引き渡しでは成果物のパス、**【要確認】の件数と一覧**、妥協した点、確かめていないこと（PowerPoint 実機での見え方など）を報告する

材料に無い数字・固有名詞・日付は作らず、`【要確認: 何を確かめるか】` と書く。ビルドはこの印を HTML / PPTX の両方で強調し、件数と場所を note に出す。「仕上げて」と頼んだときは、評価エージェントの採点と修正ループ（最大 3 周）を回す。

## 使い方（スキル）

| スキル | 用途 |
|---|---|
| `/slide-deck:create-deck` | 口述・メモ・資料から骨子を作り、承認後に deck.json を作ってビルド。既存 deck.json の編集・既存 PPTX の取り込みも |
| `/slide-deck:add-theme` | 新しいテーマ（配色・フォント）を追加・切替 |
| `/slide-deck:review-deck` | 既存デッキを一括レビュー（機械チェック＋評価エージェント `deck-evaluator` の採点と fail スライドの修正ループ） |
| `/slide-deck:export-pdf` | ビルド済み PPTX を PDF に書き出す |
| `/slide-deck:setup` | 依存関係の初回セットアップ |

スライド作成を頼めば `create-deck` が自動で選ばれる。手動なら上記コマンドで明示的に呼べる。

## 3.0.0 の新機能（要約）

詳しい仕様は各リンク先。互換性の注意は次節「3.0.0 の変更点」。

- **自動フィットと密度**: 文字量に合わせて文字サイズ・列幅・行の高さ・箱の高さを自動で決める。`meta.density`（`talk` 映して話す / `standard` / `read` 配って読ませる）で聞き手と用途に合わせる。位置やサイズを `style` で手詰めする必要が無くなる。自分で書いた `style` の値は動かさない（[`references/schema/autofit.md`](references/schema/autofit.md)）
- **型（パターン）の登録と同梱の型 19 個**: 「この構図をまた使いたい」を JSON の型にして、中身（スロット）だけ差し替えて使い回す。`type: "pattern"`。同梱は 19 個（結論と根拠・前後の対比・番号つきの手順・日付つきの流れ・案の比較・チェックリスト・体制・じょうご・ピラミッドなど。一覧は `pattern_engine.py list`）。色はテーマトークンなのでテーマを替えれば追随する。PPTX の 1 枚から型を起こす `pattern_from_pptx.py` つき（[`references/schema/pattern.md`](references/schema/pattern.md)）
- **合成スライド `composite` と分割 `split`**: 1 枚に図解・表・グラフ・要点・数字などのブロックを 2〜4 個並べる。`split` は端まで届く色面か画像のパネル（大きな数字・一文）に根拠の図表を添える。型もブロックに置ける（[`references/schema/composite.md`](references/schema/composite.md)）
- **主役のページ**: 表紙・章扉・言い切りの `variant` と `background`、cards の `emphasis` / `span`、画像を端まで届かせる `fit: "bleed"`。章番号を大きく見せる `meta.section_numbers`（[`references/schema/hero.md`](references/schema/hero.md)）
- **中身が少ないときの自動調整と、語の途中で折れる文の文節折り返し**: agenda・steps・cards・status_table・cycle・schedule（単独）と、合成・split のブロック・図解ブロックは、中身が少ないと文字を大きくし、箱を縦中央に置く（折り返しが悪くならない範囲）。狭い箱で「プラグイ／ン」のように語の途中で折れる文は、文節の切れ目に改行を入れる。`check_layout.py` の `wordbreak` が残りを拾う。止め方は `autofit: false` など（[`references/schema/autofit.md`](references/schema/autofit.md)）
- **形のプリセット**: `meta.shape`（`classic` 標準 / `sharp` 硬い / `soft` 親しみ / `editorial` 誌面風）で角丸・罫線・見出しの太さと字間・箱の影を一括で切り替える。色のテーマとは独立。自作は `<deck_dir>/shapes/<名前>.json`（[`references/themes.md`](references/themes.md) の「形（shape）とトークン」）
- **数字とグラフ**: 大きな数字の `kpi`（変化前→後・増減・進捗バー）、棒・横棒・積み上げ・折れ線・ウォーターフォール・ドーナツの `chart`。どちらも PowerPoint のネイティブ図形（[`references/schema/visual.md`](references/schema/visual.md)）
- **要確認の強調**: 文字列中の `【要確認】` / `【要確認: …】` を HTML / PPTX の両方で強調する。ビルドの note に件数と場所が出る。強調だけ止めるなら `meta.todo_marks: false`（一覧は出る）
- **検査ツール**: 実測の `check_layout.py`（コントラスト・線の貫通・孤字・小さい文字を追加）、PPTX の機械検証 `verify_pptx.py`、PPTX と HTML の見た目比較 `check_pptx.py`、見た目の偏りの `check_visual.py`、文言の `lint_deck_text.py`（【要確認】の集計と `--fail-on-todo`）。一覧は下の「検査ツール」
- **入力の検査**: 型違いの入力・未知のキー・未知の値はトレースバックではなく、直し方つきのメッセージで止まる（fail）か知らせる（警告）
- **create-deck の再構成**: 骨子 → 承認の流れ。本線（`SKILL.md`）は短く保ち、編集・既存 PPTX の取り込み・検査の読み方・骨子のひな形・設定フォームは補助ファイルに分けた。`references/` は索引 `deck-schema.md` ＋ `schema/`（タイプ別の仕様）に分けた

## 3.0.0 の変更点

2.0.0（社内 Hub 公開版）からの差分。新しく書けるもの（上の要約）は、書かなければ従来どおり。ここでは**既存のデッキをビルドし直すと変わること**を先に書く。

### 互換性の注意（既存デッキをビルドし直すと変わること）

**明示した `style` / `meta.layout_overrides` の値は、自動フィットも密度も動かさない。** 2.0.0 で手で値を詰めていたデッキは、ほとんどそのまま同じ見た目になる（`style` を書いた実デッキ 33 枚を改修の前後でビルドして比べたところ、見た目が変わったのは数枚だった）。変わるのは主に、既定の配置に任せているスライド。

見た目が変わるもの:

- **自動フィット**: 文字があふれる・箱からはみ出すスライドは、文字サイズと行間を段階的に詰めて収める（2.0.0 ではそのままはみ出した）。2px 以上縮めたときはビルドの note に出る。止めるには `meta.autofit: false`（デッキ全体）かスライドの `autofit: false`（ただし、止めても 2.0.0 と同じにならないものがある。下の「`autofit: false` でも戻らない変化と戻し方」）
- **cards**: 本文の高さを固定値から内容の行数基準の計算に変えた。`style` に値を書いたデッキでも、カード内の見出し・本文・項目の位置が数 px ずれ、項目の間隔が少し詰まる。中身が薄いカード（本文 1〜2 行など）は、文字を最大 1.6 倍まで大きくしたうえで箱を中身に合わせて詰め、本文領域の縦中央に置く（2.0.0 は箱が領域いっぱいに伸びて下が空いた）。列数を書いていないと、2 枚は 2 列・4 枚は 2 × 2 になる（3 + 1 に割れない）。折り返しの位置も文節寄りに変わる
- **表**: 列幅の計算を HTML と PPTX で同じ結果にした（`col_widths` が無いとき）。折り返したセルの最終行が 1〜2 字になる箇所は、列幅や文字を少し変えて避ける。スタイルつきの表の見出し行の描き方が変わった。`meta.density: "talk"` では行が少ないと行の高さを最大 96px まで広げて縦中央に置く。60 行を超える表は、最終行の調整と文節の改行の探索を省く（ビルドが極端に遅くなるのを防ぐため。1 枚に収まらない旨の警告は従来どおり出る）
- **見出し・表紙・章扉・引用の折り返し**: 36px 以上の大きな文字は文節の切れ目で折る（語の途中・1〜3 文字だけの最終行を避ける）。`meta.line_balance: false` で泣き別れ対策そのものを止められる。リード・箇条書き・cards の本文の改行位置も文節寄りに変わることがある（行数が変わる場合もある。見た目の崩れではない）
- **文字色の自動調整**: 地の色に対して読めない文字色（steps の「STEP n」、agenda の番号、matrix の強調象限、図解ノードの文字・schedule の矢羽根のラベルなど）は、同じ色味のまま対比 4.5:1 を満たす濃さに寄せる。止めるにはレイアウト JSON に `"readable_pairs": { "steps": [] }` のように該当タイプの組を空にして書く（全体を止めるなら全タイプ分を空にする。書き方は `references/themes.md` の「ビルドが文字色を整える」）
- **default テーマの `muted`**: `#5A6B85` → `#566781`（対比 4.5:1 を満たすため。薄い灰青の補助文字がわずかに濃くなる）
- **図解とスケジュール**: schedule の既定位置（x 72・幅 1136。下の「schedule の既定位置」）とグループ帯、矢羽根に入らないラベルを自動で外へ出す処理（右に出せなければ左）、節目のラベルの座布団。sequence の区間見出し、lifecycle の番号の位置、org の提案範囲の枠、house の柱の高さ（内容に合わせて低くなる）、swimlane の凡例の記号と成果物の文字（8px → 10〜11px）、matrix の強調見出し。ノードの文字に重なる古い `label_at` は無視して自動配置する（その旨の警告が出る）
- **PPTX**: 行送りを倍率ではなく固定の pt で書き出す（HTML の `line-height` と同じ行間になる。箇条書きの子項目の行送りは親と同じ）、図形に影を付けない（2.0.0 の見本の PPTX は 355 図形がテーマの効果スタイルを参照していた。今は参照しない）、テキストボックスは自動調整なし・折り返しあり（PowerPoint で文字を編集しても箱の大きさは変わらない）、文書プロパティ（タイトル・作成者・言語 ja-JP）を埋める、提案書系タイプの箇条書きの色と大きさを明示する。PowerPoint で開いて手で直したことがある人は、行間と箱の大きさの扱いが変わる点に注意
- **ビルドの順序**: PPTX を先に作り、HTML を後に作る。PPTX の作成で失敗したときに HTML だけ新しくなる状態を作らないため
- **中身が少ないスライドは大きくなる**: agenda（項目が少ないと行・文字を最大 1.4 倍、行の並びを縦中央に。`style.body` の手書きは要らない）、steps（文字を大きくし、箱を本文の 78% まで伸ばして項目を縦中央に）、status_table（行が少ないとセルの文字を最大 16px まで）、cycle（本文の文字を 20px 以下の大きい方から）、schedule（行 1〜3 本は行の高さと文字を大きく。4 行以上も図が枠の 9 割に満たなければ配る）。合成・split のブロックも、中身が少ないと文字を大きくし、箱つきの本文を縦中央に置き、steps は枠の高さを使い、cards は列数を選び直し（4 枚は 2 × 2）、表はセルの文字も 16px（talk 18px）まで大きくする。合成の図解ブロックは、図が小さいときに同じ倍率で拡大する。**明示した `style`・`autofit: false` を書いたスライドは動かない**。「枠の中身が少なく、下の約 N px が空きます」の警告は、自動で整えられなかったときだけ出る。止め方と値は [`references/schema/autofit.md`](references/schema/autofit.md) の「中身が少ないときの自動調整」
- **語の途中で折れる文に、文節の改行が入る**: 狭い箱で「プラグイ／ン」「担当／者へ」のように折れる文は、文節の切れ目で折る（bullets・two_column・cards・steps・表のセル・kpi の label / note・合成ブロックなど。行が増える直し方は、箱の高さに余りがある場所だけ）。何も指定しないデッキの、折れ方の悪い文だけが変わる。止めるのは `meta.line_balance: false`、1 枚だけなら `style.wrap.enabled: false`、デッキ全体なら `meta.layout_overrides.common.wrap.enabled: false`（`autofit: false` でも止まる）
- **章扉（section）の 2 行タイトル**: タイトルが 2 行以上になると枠を下へ伸ばし、罫線と副題を下げる（2.0.0 は重なった）。`autofit: false` では伸ばさず警告になる
- **`meta.brand` を付けたデッキ**: タイトルの右端を brand の文字の左端から 24px 手前までに狭める。PPTX のタイトル枠の幅が、brand の長さに応じて 1136px → 約 980〜1050px になる（短いタイトルの見た目は変わらない。長いタイトルは狭めた幅で折れる・縮む）。暗い地の章扉・結びでは brand の文字色が地に合わせて変わる。`style.title.w` を書いたスライドは動かさない
- **明示の `col_widths` を持つ表**: 列幅は動かさないまま、折り返した最終行が 1〜2 字になるセルがあると note「表のセル N 個で、折り返した最終行が 1〜2 字だけになります」が出る（ビルドは通る。直すなら該当セルの文を少し短くするか列幅を調整する）
- **PPTX**: status_table の凡例（右上）は、見出しを図形、記号と説明を 2 列の表にして描く（以前は見出しの罫線に重なった）。schedule の縦のグループ見出しは和字を 1 字ずつ縦に積む（以前は横倒し）。title（left-band）の円の飾りは、`sharp` では四角、`editorial` では小さな角丸の四角になる
- **小さな修正**: accenture の箱の小見出しの文字色が箱の地の上で 4.5:1 に足りないとき自動で濃い側へ寄る。`lint_deck_text.py` の文字量はスライドの `density` を見る（schedule は対象外）。【要確認】のマーカーは、長くても「途中で折れて表示されます」の 1 語に数えず、kpi の `value` の字数にも数えない。合成の kpi_tree ブロックの `conclusion` は警告どおり描かない。`frame: "full"` の型のスライド直下の `title` は描かれない旨を警告する

挙動が変わるもの:

- **入力の検査が厳しくなった**: 型の違う値（配列のはずが文字列、`style` の数値が文字列など）・必須キーの欠けはビルドが止まる（2.0.0 は黙って崩れるか、トレースバックで落ちた）。未知のキー（スライド直下・`meta`・`style` の領域内・テーマ JSON）は「もしかして〜」つきの警告になる。極端な数値（文字サイズ 2000 超・位置や寸法の絶対値 10 万超）、8000 万画素を超える画像、canvas 型の要素の型違い、展開後 500MB を超える取り込み元の PPTX もエラーで止まる（計算が終わらない・メモリを使い切るのを防ぐ上限。一覧は `references/schema/validation.md`）。`meta.patterns`（意味の無いキー）は未知キーの警告になる。本文が空のスライドも警告する
- **`check_layout.py` の検査が増えた**: 画像・不透明な図形が文字を覆う重なり、Y / N など 1 文字ラベルの重なり、スライドの外へ出る画像・図形も不合格にする。コントラスト・線の貫通・孤字・小さい文字は警告として出る。2.0.0 で合格していたデッキが、同じ見た目のまま不合格になることがある
- **【要確認】**: `【要確認】` / `【要確認: …】` は HTML と PPTX の両方で強調され、ビルドの note に一覧が出る（`meta.todo_marks: false` で強調だけ消せる）。`lint_deck_text.py --fail-on-todo` で 1 つでも残っていれば exit 1
- **lint**: 「半分以下に」などの「以下に」を位置の説明と誤検出しない、和文と英数字の間の半角空白は「同じ文字列の中で入れ方が混在しているとき」だけ警告、密度（talk / standard / read）で文字量の目安が変わる
- **PDF 書き出しと `check_pptx.py`**: LibreOffice に渡すフォントの置き換えを固定する（変換のたびに代替フォントが変わって見た目が揺れる問題への対処）。書き出し時に置き換えを note で知らせる
- **スキルの流れ**: 新規作成の最初に設定フォームを出さず、骨子 → 承認 1 回で進める。フォームは選びたいと頼んだときだけ出る
- **`check_layout.py` に `wordbreak`（警告）が増えた**: 描かれた行の末尾が語の途中で折れている箇所を拾う。ビルドが文節の改行を自動で入れるので、出るのは利用者が size・幅を `style` に書いた領域と、行が増える直し方しか無い場所（表のセル・kpi の label / note・合成ブロックの callout / text）。例: `wordbreak: [li]「プラグインのファイルをアップロードする」 1行目の終わりが語の途中で折れている（「…ルをアップロ／ードする…」、2行中、25px）`。直し方は文を短くする／文節の切れ目に `\n` を入れる／箱の幅・size・列幅を調整する
- **SVG を含むデッキを playwright 無しで PPTX 化**すると、トレースバックではなく「PPTX 化に playwright が必要です → `/slide-deck:setup --playwright`（HTML だけなら `--html`）」で止まる
- **ビルドの警告・note が増えた**: ①`meta.brand` が右上の箱（既定 幅 140px・文字 23px）に 1 行で収まらないと、1 回だけ警告する（直し方: 短くする／`meta.layout_overrides.common.brand` で `w` を広げ `x` を同じだけ左へ／`size` を下げる）。②`style` / `meta.layout_overrides` に `x` と `w`（または `y` と `h`）の片方だけを書き、既定のもう片方と合わせるとスライドの外へ出る領域は警告する（直し方: 両方書く）。③同梱と同じ名前のテーマ・レイアウト・型・形を、同梱以外から読んだときは note を 1 行出す
- **テーマ・レイアウトの探索先が広がった**: 2.0.0 は環境変数・`<deck_dir>/themes/`・同梱だけを探した。今は**デッキの親（3 階層上まで）とカレントディレクトリの `themes/` `layouts/` も探す**（探索順は下の「テーマ・レイアウト・型・形の探索順」）。デッキの親やカレントに、同梱と同じ名前（`default` `acn-slide-master` など）の別用途のファイルがあると、同じ deck.json の見た目が変わるか、ビルドが失敗することがある。同梱以外から読んだときは note にパスが出るので、意図していなければそのファイルを別の名前にするか移す
- **`meta.theme` / `meta.layout` に絶対パスは書けない**: 2.0.0 は絶対パス（拡張子なし）でも読めたが、今は「名前だけを指定してください（パス区切り・絶対パス・先頭のドットは使えません）」で fail する。`<deck_dir>/themes/`（`layouts/`）などの探索先に置いて、名前で指定する
- **2.0.0 までの `pptx_import.py` の出力**: キーが `meta.source` → `meta._source`、`meta.generator` → `meta._generator`、スライドの `source_page` → `_source_page`（メモ扱い）に変わった。旧キーで取り込んだ canvas デッキは、警告なしでそのまま読める（canvas 以外のスライドの `source_page` は未知キーの警告）
- **テスト**: 単体テストは見本・manual を一時フォルダへ写してビルドする。配布物のフォルダの中に `build/` を作らない

### schedule の既定位置（片方だけ上書きしたデッキ）

schedule の図の既定が変わった。

| キー（`style.chart`） | 2.0.0 | 3.0.0 |
|---|---|---|
| `x` / `w` | 48 / 1184 | 72 / 1136 |
| `label_w`（行見出しの幅） | 250 | 232 |
| `group_w` / `group_size`（グループ帯の幅 / 文字） | 34 / 13 | 36 / 14 |
| `max_row_h`（行の高さの上限） | 54 | 64 |
| `bar_max_h`（矢羽根の高さの上限） | 30 | 34 |

`style.chart.w` だけを広げていた（`x` は 2.0.0 の既定 48 に頼っていた）デッキは、`x` だけが 72 になって右端がスライドの外へ切れる。**このときビルドが警告する**（「style の chart.w だけが指定され、x は既定値（72）のままのため、x + w = 1304 がスライドの幅（1280）を超えます → chart の x と w を両方書く」。実際に `w: 1232` だけを書いたデッキで確認した）。直し方は `x` と `w` を両方書くこと。2.0.0 の見た目に戻すなら、上の 2.0.0 の列の値を `style.chart` に書く（実測: 見本の schedule で、位置と大きさは 2.0.0 と一致した。**戻らないもの**は、縦のグループ見出しの和字縦積みと、節目ラベルの座布団）。

### `autofit: false` でも戻らない変化と戻し方

`meta.autofit: false` は縮小・拡大・整えを止めるだけで、3.0.0 で**既定の配置・間隔そのものを変えたもの**は戻らない。2.0.0 の見本を `meta.autofit: false` で 2.0.0 と 3.0.0 の両方でビルドして PPTX の図形の位置を比べたところ、次が残った（確かめたのは図形の位置・大きさ。HTML の画素や PowerPoint 実機では比べていない）。

| 項目 | 2.0.0 との差 | 元に戻す方法 |
|---|---|---|
| schedule | 既定位置・グループ帯・行の高さ・矢羽根の高さ（上の表） | 2.0.0 の値を `style.chart` に書く（戻らないもの: PPTX の縦のグループ見出し、節目ラベルの座布団） |
| schedule の矢羽根のラベル | 入らないラベルを自動で外へ出す（旧は警告、新は note）。右に出せなければ左 | そのラベルに `label_pos: "inside"`、右への移動は `style.chart.auto_after: false`、左への移動は `style.chart.auto_before: false`。`autofit: false` では止まらない |
| house | 柱が内容に合わせて低くなり、全体が上下中央に置かれる | `style.body.fit_content: false`（確かめた: 位置が 2.0.0 と一致） |
| cards の内側 | カード内の見出し・本文・項目の位置と間隔が数 px（最大 20px 台）ずれる | **戻す手段は無い**（`thin_grow: 1`・`fit: "fill"` を重ねても一致しない） |
| org（提案範囲の枠）・sequence（区間見出し）・lifecycle（番号の位置） | 配置が変わった | **戻すための指定は用意していない**（sequence は区間見出しの余白 `segment_pad_top` / `segment_pad_bottom` を変えても一致しなかった。org・lifecycle は戻す指定を探していない） |
| swimlane の凡例の記号と成果物の文字 | 8px → 10〜11px | 戻し方は確かめていない（`flow.io_min_size` 未確認） |
| status_table の PPTX の凡例 | 見出しが図形に、記号と説明が 2 列の表に変わった（重なりの修正） | **戻す手段は無い** |

`autofit: false` で 2.0.0 と同じになるのは、文字・箱の縮小、中身が少ないときの拡大（agenda・steps・cycle・status_table・schedule・合成/split のブロック）、語の途中で折れる文への文節の改行、章扉の枠の伸びといった**自動の調整**。見た目を 2.0.0 のまま保ちたい既存デッキは、`meta.autofit: false` を付けたうえで、上の表の「戻す方法」を必要な項目だけ当てる。

### 変更の全体（利用者に見えるもの）

- 新しいタイプ: `kpi` `chart` `composite` `split` `pattern`（全 34 タイプ + 取り込み専用の `canvas`）
- 新しい `meta` のキー: `density` `autofit` `shape` `variants` `section_numbers` `todo_marks`。スライドに `density` `autofit`（全タイプ共通）、title / section / quote / closing / statement に `background` `variant`
- 新しいテンプレート置き場: `templates/shapes/`（4 種）、`templates/patterns/`（同梱の型 19 個）。探索先に `SLIDE_DECK_SHAPES` / `SLIDE_DECK_PATTERNS` / `SLIDE_DECK_LAYOUTS`
- 図解: 双方向の矢印に別々のラベルを付ける `label_back`、schedule の矢羽根に入らないラベルの自動配置
- kpi: 前後で単位が違うときの `from_unit`
- 新しいツール: `verify_pptx.py` `check_pptx.py` `pattern_engine.py` `pattern_from_pptx.py`。`new_theme.py --shape` `check_theme.py --shapes`、`lint_deck_text.py --fail-on-todo`
- テスト: 単体テスト 1502 件（2026-11-12 時点）

### この版で確かめたこと・確かめていないこと

確かめたのは、HTML の描画、LibreOffice での PPTX の描画（フォントは Hiragino Sans に固定）、PPTX の XML、`verify_pptx.py`、単体テスト、同梱の見本と manual のビルド。**PowerPoint 実機での見え方は確認していない。** 詳しくは下の「既知の制約」。

## 手動で使う（スキルを介さず）

> **注意**: `${CLAUDE_PLUGIN_ROOT}` は Claude Code がスキル本文（SKILL.md）を実行するときにだけ内部で実パスへ置換する専用トークンで、PowerShell や Git Bash を素で開いて手入力しても定義されない（未定義変数として空文字に展開され、`python "/tools/xxx.py"` のような誤ったパスになって失敗する）。ここから先のコマンドは Claude Code のスキル実行を介さずターミナルから直接叩く想定なので、`${CLAUDE_PLUGIN_ROOT}` の代わりに **このプラグインのディレクトリへ `cd` してから相対パスで実行する**。このリポジトリを clone している場合はそのディレクトリが `plugins/slide-deck/`。配布 Zip を展開して使っている場合は展開先の `slide-deck/` ディレクトリに読み替える。

```bash
cd path/to/plugins/slide-deck   # このプラグインのディレクトリに移動（例: このリポジトリなら plugins/slide-deck）

# ビルド（HTML + PPTX。--html / --pptx で片方だけ。想定外の例外を調べるときは --debug）
python tools/build_deck.py <deck_dir>
# プレビューPNG（要 playwright）
python tools/preview_deck.py <deck_dir> [番号...]
# 構造チェック（はみ出し・重なり・文字あふれ・コントラストなど。要 playwright）
python tools/check_layout.py <deck_dir>
# 図解タイプの配線・ラベル診断（architecture/dataflow/lifecycle/sequence/swimlane/schedule）
python tools/check_diagram.py <deck_dir>
# SVG図版のフォント機械チェック（明朝体等へのフォールバックを検出）
python tools/check_svg_fonts.py <deck_dir>
# 文言チェック（文字量・AI定型句・主張の書き方・日付の整合・【要確認】の一覧など）
python tools/lint_deck_text.py <deck_dir> [--fail-on-todo]
# 見た目の偏り（本文の空白帯・直前と似たスライドの連続・古いPNG。要 pillow・preview_deck の PNG）
python tools/check_visual.py <deck_dir>
# PPTX の機械検証（zip 整合・再パース・ノート無し・XML 整形式・文書プロパティ）
python tools/verify_pptx.py <deck_dir>/build/<meta.id>.pptx
# PPTX と HTML プレビューの見た目比較（要 LibreOffice・pdftoppm・pillow。警告のみ）
python tools/check_pptx.py <deck_dir>
# スライドタイプ別の統計
python tools/deck_metrics.py <deck_dir>
# 一覧サムネイル（要 pillow）
python tools/contact_sheet.py <deck_dir>
# PDF書き出し（要 LibreOffice）
python tools/export_pdf.py <deck_dir>
# 新規作成の設定フォーム（Claude の show_widget 用 HTML。選びたいと頼まれたときだけ使う）
python tools/build_settings_widget.py --out deck_widget.html
```

型（パターン）とテーマ・形:

```bash
# 使える型の一覧（1 型 1 行。枠・個数・半幅に置けるか・何を言うときに使うか）と、1 つの詳細・書き方の例
python tools/pattern_engine.py list [--deck <deck_dir>]
python tools/pattern_engine.py show <型の名前>
# 型 JSON の検証 / 探索先の全型を例文で 1 枚ずつ並べた確認用デッキをビルド / 1 つの型の確認用デッキ
python tools/pattern_engine.py check <ファイル>
python tools/pattern_engine.py preview --out <出力先フォルダ>
python tools/pattern_engine.py sample <型の名前> --out <出力先フォルダ>
# PPTX の 1 枚（またはこのプラグインのデッキの 1 枚）から型の JSON を起こす（出力先は --dir。省略時は PPTX なら ./patterns、--from-deck なら <deck_dir>/patterns。同名は --confirm なしで上書きしない）
python tools/pattern_from_pptx.py <src.pptx> --slide N --name <名前>
python tools/pattern_from_pptx.py --from-deck <deck_dir> --deck-slide N --name <名前>
# テーマのコントラスト確認 / shape（形のプリセット）の一覧と検証
python tools/check_theme.py <theme名>
python tools/check_theme.py --shapes
# 新テーマ雛形（--shape で形も持たせる）
python tools/new_theme.py <name> [--shape soft]
# サンプルスライド(PPTX/HTML/PDF/画像)からテーマを生成
python tools/theme_from_sample.py <sample-file> --name <name>
```

取り込み:

```bash
# Archify の diagram JSON をスライド1枚に変換（--into で deck.json の slides 末尾に追記も可）
python tools/archify_import.py <archify.json> --into <deck_dir>            # 追記内容を表示するだけ（書き込まない）
python tools/archify_import.py <archify.json> --into <deck_dir> --confirm  # 承認後に実際に追記して保存
```
> ⚠️ `--into` は既存の `deck.json` を読み込み、末尾に 1 枚追記して**同じパスへ上書き保存**する。
> 既存ファイルがある場合、`--confirm` を付けないと書き込まずに終了し（exit 1）、追記される内容だけを出力する。
> **`--confirm` を付ける前に、その内容を利用者に提示して明示的な承認を得ること。**
> 上書きせずに結果だけ欲しいときは `--out <file>` を使う。

```bash
# 既存 PPTX を見た目そのままに canvas 型デッキへ取り込む（取り込み専用。新規作成には使わない）
python tools/pptx_import.py <src.pptx> --into <deck_dir>            # deck.json が既にあれば書き込まずに終了
python tools/pptx_import.py <src.pptx> --into <deck_dir> --confirm  # 承認後に置き換え（元は deck.json.bak に退避）
# 元 PPTX を PNG 化（Windows + PowerPoint）→ プレビューと並べて比較
pwsh tools/export_pptx_png.ps1 -Src <src.pptx> -OutDir <deck_dir>/_work/ref
python tools/compare_ref.py <deck_dir> <deck_dir>/_work/ref
```
> ⚠️ `pptx_import.py --into` は deck.json を**丸ごと置き換える**（追記ではない）。既存ファイルがある場合は `--confirm` が無いと書き込まない。
`python` が無ければ `python3`（Windows は `py -3`）に読み替える。コマンド自体は PowerShell / Git Bash のどちらでも同じもので動く（`cd` の区切り文字はどちらもそのままで可）。

## 検査ツール

ビルド（`build_deck.py`）は、入力の検証と PPTX の機械検証（`verify_pptx`）を保存の直後に自動で行う。それ以外は、ビルド後に手で（またはスキルの手順で）通す。番号つきの出力は、すべて**プレビュー PNG の番号**（凡例ページの自動挿入・agenda の分割込み。deck.json の何枚目かとは違うことがある）。

| ツール | 見るもの | 結果の扱い |
|---|---|---|
| `check_layout.py` | ビルド済み HTML の実測。不合格: 文字の切れ（clip）・画面外へのはみ出し（bleed）・重なり（overlap）・行数超過（lines）・高さ超過（spill）・罫線との交差（rule）。警告: 孤字（最終行 1〜2 文字）・語の途中の折れ（wordbreak。「プラグイ／ン」）・小さい文字（minfont。既定 9px 未満）・コントラスト（contrast）・線が文字を貫通（linecross） | 不合格があれば exit 1 |
| `check_visual.py` | プレビュー PNG から、本文の大きな空白帯（empty-bottom / empty-band）・直前と似たスライドの連続（similar）・PNG が古い（stale） | 警告のみ（`--strict` で exit 1） |
| `check_diagram.py` | 図解タイプの配線・ラベルの座標診断（交差・ラベルの衝突など） | error があれば exit 1（`--strict` で warning も） |
| `lint_deck_text.py` | 文言: 文字量（`meta.density` で目安が変わる）・曖昧語・AI 定型句・体言止め・日付の整合・`relation` とタイプの不一致・【要確認】の一覧 | 不合格の規則は exit 1。`--fail-on-todo` で【要確認】が残っていれば exit 1 |
| `check_svg_fonts.py` | `assets/` の SVG のフォントが明朝体などへフォールバックしないか | 検出があれば exit 1 |
| `verify_pptx.py` | PPTX の zip 整合・XML の整形式・python-pptx での再パース・**スピーカーノートが無いこと**・グループ内に表が無いこと・文書プロパティ（title が空／python-pptx 既定の作成者名／作成日が既定のまま、は NG） | 問題があれば exit 1 |
| `check_pptx.py` | LibreOffice で PPTX を描いて HTML プレビューと 1 枚ずつ比べ、差の大きい順に報告（`build/pptx-compare/cmp-NN.png`） | 警告のみ。**PowerPoint 実機の代わりにはならない**（目で確かめる候補を絞る参考値） |
| `check_theme.py` | テーマの配色のコントラスト（WCAG）、`--shapes` で shape の検証 | エラーがあれば exit 1 |
| `pattern_engine.py check` | 型 JSON 自体の検証（例の値で展開して canvas の検査まで） | エラーがあれば exit 1 |
| `deck_metrics.py` / `contact_sheet.py` | タイプ別の文字数・項目数の統計／一覧サムネイル | 合否なし（読む材料） |

警告ごとの直し方は、まず内容（項目数・文の長さ・分割）、次に密度、最後に `style` の順（`skills/create-deck/checks.md`）。

## テーマ・レイアウト・型・形の探索順

`meta.theme`（テーマ）・`meta.layout`（レイアウト）・`pattern`（型）・`meta.shape`（形）は、同じ規則で探す。先に見つかったものが勝つ（重複は除く）。

1. 環境変数（OS のパス区切りで複数可）: `SLIDE_DECK_THEMES` / `SLIDE_DECK_LAYOUTS` / `SLIDE_DECK_PATTERNS` / `SLIDE_DECK_SHAPES`
2. `<deck_dir>/themes/`（`layouts/` `patterns/` `shapes/`）
3. デッキのフォルダの親（3 階層上まで）の同名フォルダ（`decks/<名前>/deck.json` に対して、`decks/themes/` やプロジェクト直下の `themes/` を拾う）
4. カレントディレクトリの同名フォルダ
5. 同梱 `templates/themes/`（`layouts/` `patterns/` `shapes/`）

プラグインの更新で消したくない自作のテーマ・型・形は 1〜4 に置く（同梱の `templates/` には置かない）。同梱と同じ名前のファイルを 1〜4 に置くと、そちらが勝つ（ビルドが note にパスを出す）。`meta.theme` / `meta.layout` に絶対パスは書けない（名前だけ）。同梱: テーマ 4 種（`default` / `accenture` / `acn-slide-master` / `acn-technology-graphik`。旧名 `accenture-purple` は別名）、形 4 種、型 19 個。

## 構成

```
plugins/slide-deck/
├── .claude-plugin/plugin.json   # プラグイン定義
├── pyproject.toml / uv.lock     # Python 依存関係（uv でハッシュ固定）
├── requirements.txt             # Python 依存関係（pip install -r で導入可）
├── skills/                      # create-deck（補助ファイル: outline / recipes / edit / checks / import-pptx / settings-form） /
│                                 #   add-theme / review-deck / export-pdf / setup
├── agents/                      # deck-evaluator（プレビュー画像を第三者として採点する評価エージェント）
├── tools/                       # ビルド: build_deck / preview_deck / export_pdf / setup_deps
│                                 #   エンジン: autofit / canvas_engine / composite_engine / hero_engine / dataviz_engine /
│                                 #     proposal_engine / schedule_engine / diagram_engine / pattern_engine / shape_engine /
│                                 #     icon_engine / engine_registry / deck_schema / deck_paths / ja_text / todo_marks /
│                                 #     color_pick / lo_profile
│                                 #   検査: check_layout / check_visual / check_diagram / check_svg_fonts / lint_deck_text /
│                                 #     verify_pptx / check_pptx / check_theme / deck_metrics / contact_sheet / compare_ref
│                                 #   テーマ・型: new_theme / theme_from_sample / pattern_from_pptx
│                                 #   取り込み: pptx_import / pptx_import_excel / archify_import / build_settings_widget /
│                                 #     export_pptx_png.ps1
│                                 #   test_*.py（単体テスト）
├── templates/                   # themes/（default, accenture, acn-slide-master, acn-technology-graphik） layouts/（default）
│                                 #   shapes/（classic, sharp, soft, editorial） patterns/（同梱の型 19 個） icons/（Tabler の定番アイコン）
├── references/                  # deck-schema.md（索引） schema/（タイプ別の仕様） themes.md content-guide.md diagram-guide.md
│                                 #   review-rubric.md approval-gates.md story-patterns.md diagram-appendix.md
├── examples/template-sample/    # 主要なタイプを並べた見本 deck.json（1 本の架空の提案デッキ）
├── examples/shape-gallery/      # 形（shape）の比較。同じ 7 枚を classic / sharp / soft / editorial の 4 つでビルドする
├── manual/deck.json             # スライド版マニュアルのソース
└── USER-GUIDE.html              # ↑ をビルドした成果物（配布物に同梱）
```

## 詳細

- スキーマの索引（座標系・3 層構造・meta・タイプ一覧表・探索順）: [`references/deck-schema.md`](references/deck-schema.md)。タイプ別の仕様は索引の表から、使うタイプのファイルだけ読む
  - 通常のタイプ（表紙・箇条書き・表・カード・ステップなど）: [`references/schema/basic.md`](references/schema/basic.md)
  - 数字とグラフ: [`schema/visual.md`](references/schema/visual.md) / 型（パターン）: [`schema/pattern.md`](references/schema/pattern.md) / 合成・分割: [`schema/composite.md`](references/schema/composite.md) / 主役のページ: [`schema/hero.md`](references/schema/hero.md)
  - 図解・業務フロー・スケジュール・提案書の定型ページ・取り込み: [`schema/diagram.md`](references/schema/diagram.md) [`schema/swimlane.md`](references/schema/swimlane.md) [`schema/schedule.md`](references/schema/schedule.md) [`schema/proposal.md`](references/schema/proposal.md) [`schema/canvas.md`](references/schema/canvas.md)
  - 自動フィットの規則・警告の意味: [`schema/autofit.md`](references/schema/autofit.md) / [`schema/validation.md`](references/schema/validation.md)
- テーマ（トークン一覧・追加方法・形のプリセット）: [`references/themes.md`](references/themes.md)
- コンテンツ品質ガイド（ストーリーの型・1枚のルール・執筆前チェックリスト）: [`references/content-guide.md`](references/content-guide.md)
- 図解タイプの描き方（作図規約・座標診断の直し方）: [`references/diagram-guide.md`](references/diagram-guide.md)
- 評価の採点基準: [`references/review-rubric.md`](references/review-rubric.md)

## 既知の制約

**確かめた範囲**: HTML の描画（Chromium）、LibreOffice の描画（`lo_profile.py` でフォントを Hiragino Sans に固定）、PPTX の XML、`verify_pptx.py`、単体テスト。**PowerPoint 実機（Windows / macOS）での見え方は、この版では確認していない。**

PowerPoint / フォント:

- **PowerPoint 実機は未確認**。特に実機で開いて確かめてほしい点: 【要確認】の強調（文字を分けた run の太字・色）、`a:br` を含む折り返し、半透明の覆い（`a:alpha`）と画像の切り抜き（`srcRect`）、合成スライドで表をグループの外に置く構造、台形・チェックマークなどの図形で描く型、背景つきの小さな図形に入れたラベル（スケジュールの節目・org の連携の名前）、ひし形の外に出した番号、soft の影のぼかし
- **Windows の Meiryo の字幅では、折り返しが数文字ずれることがある**。折り返し・あふれ・泣き別れの見積もりは、字幅を実測した代替フォント（この環境では Hiragino Sans。ビルドの note に出る）で行う。テーマのフォントが入っている機械でビルドすると、その字幅で測る。PowerPoint で開くと 1 行が溢れて自動で折り返されることがある
- 固定の行送りでは、1 行目が HTML より 4〜8px 下に描かれる（行間 1.6 倍で 24〜40px の文字。LibreOffice で実測。PowerPoint 実機は未確認）
- LibreOffice の描画は、フォントの代替が実行ごとに変わることがあった（3.0.0 で固定した）。`check_pptx.py` の差の数値は参考値で、「差が小さい = PowerPoint で崩れない」ではない
- PPTX にスピーカーノートは出力されない（Keynote 互換性のため）。`notes` は HTML のみ

自動フィット・文字組み:

- 狭い枠（表のセル・箱の見出し）のカタカナ語は、途中で折れることがある（HTML だけ折り返しを止めても PPTX が直らず、両者がずれるため手を入れていない）。列幅を広げるか文字を減らす
- `image_text` で `image_side: "left"` にすると、`body` `img` `caption` の座標（`style`）が左右反転して使われる。左に置くときは `style` の座標を**右に置く場合の座標**で書く
- `status_table` の文字は既定 13px（行が少ないと最大 16px まで大きくなる。talk 19px・read 14px）。既定の凡例の文は固定
- `swimlane` は列が多いと、箱が細くなって成果物（io）などの文字が小さくなる（`check_layout.py` の minfont 警告。2 行折りでも 10px に入らない項目がある）。レーン・工程を減らすか分ける
- **語の途中の折れを自動で直さない場所**: 表のセル・kpi の label / note・合成ブロックの callout / text は、行が増える直し方をしない（あふれ・縮小を新しく作らないため）。折れが残るときは、文を短くするか、文節の切れ目に `\n` を入れるか、列幅を広げる
- 利用者が文字の大きさ・幅（`style.body.size`・`style.table.col_widths` など）を書いた領域は、手で調整した折り返しとして触らない。`check_layout.py` の `wordbreak` で気づける
- 文節折り返しの位置は、LibreOffice の描画と PPTX の XML までの確認。**PowerPoint 実機・Keynote での折り返し位置は未確認**
- **`meta.brand` の長さ**: 右上の箱は既定で幅 140px・文字 23px。目安は全角 6 字まで、半角は小文字なら 9 字ほど（大文字が多いと 7 字ほど）。超えると全スライドで 2 行に折れるので、ビルドが警告する（直し方は短くする／`layout_overrides.common.brand` で `w` を広げ `x` を同じだけ左へ／`size` を下げる）。brand の文字が章扉の枠で 2 行に折れてあふれるのは 2.0.0 からあった。brand を付けたデッキで 1 行に収まる下限まで縮めても入らない長さのタイトル（目安 44 字）は、警告つきで残る
- 中身が少なくても、自動では整えない場合がある: cards が全幅で横長になる、1 行だけの表が広い余白に浮く、小見出しつきの箱が複数あるときに見出しと本文が離れる、pattern・図解ブロックの隣の文字の大きさが不ぞろい、`style.chart` を書いた schedule の空き（仕様どおり）。内容を足すか、ブロックの比率（`columns` / `rows`）・タイプを替える

型・合成スライド:

- 合成の `kpi_tree` は半幅（約 556px）に置けない（最低 586px で fail）。3 分の 2 幅（約 741px）では描くが、文字が 11〜12px で、短い列見出しが語の途中で折れることがある。2 列にまたがせるか、単独のスライドに置く
- 合成・split のブロックに置ける型は、幅の下限がある（`pattern_engine.py list` の「ブロック」列と `show` の個数別の下限）。半幅（約 556px）で読める型は多いが、**3 分の 1 幅（約 360〜400px）で全個数が読める型は無い**。全面の型（`before-after` `conclusion-evidence` `pillars`）はブロックに置けない
- 幅 1000px 以上で高さ 340px 未満のブロックは、広い構図を縮めて中央に置く。高さ 260px 以下では文字が 10〜12px 台になり、実測の警告が出る
- 型の文字数の上限（`max_chars`）いっぱいの文を全項目に入れると、幅 700px 未満のブロックでは収まらず警告が出る
- 型の最小文字の判定は、要素名に「札」「タグ」「印」を含むものを 11px、それ以外を 12px とみなす。型の作者が要素名を変えると 12px 扱いになる

主役のページ・画像:

- 画像背景の覆いの見映えは、自作の画像 3 種（グラデーション・幾何学模様・稜線）でしか確かめていない。実写真では覆いの色と濃さ（`overlay` / `opacity`）を調整する。画像が中間の明るさの `image_text`（`bleed: true`）では、`meta.brand` の文字の対比が足りないという警告が出ることがある

その他:

- Python 3.14 以上が必要。依存の導入は `/slide-deck:setup`

## 図解タイプ（Archify 方式）

`architecture` / `dataflow` / `lifecycle` / `sequence` の4タイプは、[Archify](https://github.com/tt-a1i/archify)（MIT）の方式――AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して描く。検証に落ちたら座標付きの修理指示が返る――を Python ネイティブに取り込んだもの。Node.js・Archify 本体は不要で、このプラグイン単体で完結する。

配置はグリッド（`row` / `col`）指定のみで px 座標は書かない、配色は type ごとの色相ではなくテーマトークンのみ（type はアイコンの形で表す）など、意図的に Archify とは異なる設計にしている部分もある。既存の `swimlane` も同じ配線エンジンに乗せ替え、ラベルと線の重なりを解消した。

作図の描き方・座標診断の直し方は [`references/diagram-guide.md`](references/diagram-guide.md) を参照（`create-deck` / `review-deck` スキルの手順にも組み込み済み）。

参考: 「ArchifyでAIに図を描かせる新しいやり方」（クロノITチャンネル, https://www.youtube.com/watch?v=L2KPenldwdo ）

## v2.0.0 の主な変更（社内 Hub 公開版。前回公開の v1.1.1 からの差分）

（2.0.0 時点の記録。3.0.0 の変更点は上の節。）開発中は v1.2.0〜v1.7.0 として段階的に入れた内容を、社内 Hub 向けにメジャーバージョン v2.0.0 としてまとめて公開する。詳細は以下の各節。

- **既存 PPTX の取り込み**: `canvas` 型と `pptx_import.py`（見た目そのままに HTML 化）
- **設定フォーム**: 新規作成の最初にテーマ・聞き手・目的・構成・枚数・仕上げの度合いなどを1画面で選ぶ
- **品質チェック**: 字幅の実測による文字あふれの見積もり、泣き別れ対策、文言チェックの拡張、見た目のチェック（`check_visual.py`）、評価エージェント `deck-evaluator` と修正ループ（「仕上げ」を選んだときだけ）
- **提案書向けタイプ8種**: `summary` / `reasons` / `statement` / `row_matrix` / `org` / `house` / `cycle` / `kpi_tree`（全29タイプ）と、結論の帯・出典の行、既存タイプの拡張
- **アイコン**: Tabler Icons（MIT）の定番74点と意味検索
- **テーマ**: 同梱テーマを `default` と、acnpptx の3テンプレートに寄せた配色 `accenture` / `acn-slide-master` / `acn-technology-graphik` の4種にした。旧 `accenture-purple` は `acn-slide-master` に統合し、別名として読める（既存デッキはそのまま同じ見た目でビルドできる。設定フォームの選択肢には出ない）。スライドマスター・アイコン・イラストなど Accenture のブランド資産は同梱していない

## 設定フォームと品質チェックの強化（2.0.0）

acnpptx スキルの分析結果から、slide-deck の設計を崩さずに取り込めるものを実装した。

- **設定フォーム**: 新規作成の最初に、テーマ（色トークンから描いたミニプレビュー付き）・聞き手・目的・構成の型・枚数・トーン・図解の方針・出力形式・参考資料を 1 画面で選べるフォームを出す（`tools/build_settings_widget.py`）。送信後は確認を挟まず完成まで進める（**3.0.0 から、フォームは既定では出さない**。骨子 → 承認 1 回で進み、利用者が選びたいと頼んだときだけフォームを出す。補助ファイル `skills/create-deck/settings-form.md`）。visualize ツールが無い環境では AskUserQuestion の 4 問で代替。仕上げの度合い（ドラフト＝機械チェックだけ・既定／仕上げ＝評価ループあり）も選べる
- **字幅の実測**: 文字あふれの見積もりを、テーマのフォントファイルを Pillow で実測した字幅で行う（`tools/ja_text.py`）。英単語は途中で切らず、行頭禁則は前の行に残す。Pillow かフォントが無い環境では従来の近似（全角 1.0 / 半角 0.55）
- **泣き別れ対策**: タイトル・リード・箇条書きの最終行が 1〜2 文字だけ残る文に、ビルド時に文節の切れ目で改行を入れる（HTML と PPTX の両方。`meta.line_balance: false` で無効）。あわせて PPTX では明示的な改行を段落内改行（`a:br`）として出力するようにした
- **文言チェックの拡張**（`lint_deck_text.py`、すべて警告）: 曖昧語・構成の説明・体言止めのリード・タイトルの言い直し（文字 2-gram の重なり）、曖昧な列名・凡例の無い ◎○△・桁区切り、同じタイプの 3 枚連続、`relation` とタイプの不一致、日付の整合（`meta.as_of` より後の「実績」、基準日より前に始まる計画）
- **見た目のチェック**（`check_visual.py`）: プレビュー PNG のインク量から「下 1/3 が空いたスライド」を、dHash から「直前と似たスライドの連続」を検出する

## 定番アイコンと意味検索

- **同梱アイコン**: Tabler Icons（MIT License）の outline から、提案書でよく使う概念の定番だけを74点同梱した（`templates/icons/icons.json`、約40KB）。SVG の円弧などを曲線に変換して持ち、HTML でも PPTX でも線だけのネイティブ図形として描く（画像にしないので PowerPoint で色・太さを変えられる）
- **意味検索**: 各アイコンに日本語・英語の概念語を付け、`icon` に概念語（例「コスト削減」「q:統制 安全」）を書くと最も近いアイコンを選ぶ。似た概念は同じ絵を使い回し、素材を増やさない方針
- **置ける場所**: `summary` / `reasons` / `house` / `cycle` / `cards` の項目の `icon`
- **ツール**: `tools/icon_engine.py`（検索・一覧・一覧画像）、アイコン集を作り直す保守用スクリプト `build_icon_set.py`（外部 URL を取得するため配布物には含めず、開発リポジトリの scripts フォルダに置いている）
- Accenture のブランド資産（アイコン・イラスト・マスター）は使っていない

## 全体像・循環・KPI と既存タイプの拡張

作例の残りのページに対応した（第2弾）。

- **新しいタイプ**: `house`（屋根・柱・土台の全体像）/ `cycle`（円弧の矢印の輪＋時計回りに並ぶ段のパネル）/ `kpi_tree`（目標 → 方向性 → KPI＋目標値＋測り方）
- **結論の帯・出典の行をほぼ全タイプに**: `conclusion` / `source` を書くと、本文の領域（表は行の高さ）を自動で詰めて下端に付ける
- **既存タイプの拡張**: `agenda` の説明文 `desc`、`table` の行見出し `row_header`・合計行 `total_row`、`two_column` の間の三角 `connector: "arrow"`、`steps` の矢羽根見出し `header_style: "arrow"`、`matrix` の散布 `points`、`code` の番号付き注釈 `annotations`
- `code` の文字サイズは行数に加えて最長行の幅でも決めるようにした（横にはみ出して切れていた長い行が収まる）
- PPTX で canvas 要素を同じスライドに何度追加しても図形 ID が重ならないようにした

## 提案書向けのスライドタイプ

acnpptx の紹介ムービーに出てくる作例の提案書（28枚）を1枚ずつ slide-deck のタイプと突き合わせ、既存タイプで描けない定型ページを新しいタイプとして追加した。レイアウトは `tools/proposal_engine.py` が計算して canvas の要素列にし、HTML と PPTX の両方でネイティブ図形として描く（PowerPoint で四角・矢羽根・線を1つずつ編集できる）。

- **`summary`**（要旨）: 番号の箱＋要点＋説明の行。行の高さをそろえ、文字は枠に合わせて自動で縮む
- **`reasons`**（選ばれる理由）: 相手の課題（番号）と自社の強み（a/b/c）を同じ行に並べて対応を見せる
- **`statement`**（言い切り）: 濃色の面に大きな一文。物語の転換点に置く
- **`row_matrix`**（行見出し×列の整理表）: 機会とリスク、工程×領域、前提・参考資料など。列見出しを工程の矢羽根にもできる
- **`org`**（体制図）: 左右の組織ツリー、カギ線、提案範囲の破線枠、組織をまたぐ連携線
- **共通パーツ**: 結論の帯 `conclusion` と出典の行 `source`（提案書向けタイプで使える）

## 評価エージェントと修正ループ

- **`agents/deck-evaluator.md`**: 生成の経緯を知らない第三者としてプレビュー PNG を採点する評価エージェント。10 観点×10 点（5 秒で結論が分かるか・視線の順・密度・タイプの適合・色の意味・均等割りへの逃げ・文字の品質・重心・前後との重複・図と線の仕上げ）で、70 点未満は fail。根拠は画像で確認できる事実に限る
- **修正ループ**: `review-deck` の手順8、または新規作成で「仕上げて」と頼んだとき（フォームを使う場合は「仕上げ」を選んだとき）の `create-deck` の検査と目視の手順。fail のスライドだけを deck.json（文言・`style` 差分）で直して再採点し、修正は最大 3 周で打ち切って残りを「未解決」として報告する

## 既存 PPTX の取り込み（`canvas` 型）

- **`canvas` 型**: 1280×720 の座標に図形（矢羽根・フローチャート記号・コネクタ・矢印等）・文字・表・SVG アイコンを直接置く**取り込み専用**のスライドタイプ。既存 PowerPoint 資料を見た目のまま HTML 化するためのもので、テーマ（色・フォント）とタイトル・罫線・フッターは適用されない。新規スライドは他のタイプで作る。仕様は [`references/deck-schema.md`](references/deck-schema.md) の「canvas」節
- **`tools/pptx_import.py`**: 既存 PPTX を canvas 型の deck.json に変換する。プレースホルダー/マスター/既定スタイルの継承、表スタイル、色マッピングの上書き、図形ごとの文字領域を PowerPoint と同じ規則で解決する。マスター上の図形は各スライドに展開される。ラスタ画像は埋め込まず枠（placeholder）にする。埋め込み Excel の表化には `openpyxl`（任意）が必要
- **PPTX への再出力**: 図形・線・表は PowerPoint ネイティブの図形として出力され、1つずつ編集できる（SVG アイコンは PNG 画像、グループは解除）
- **`tools/compare_ref.py` / `tools/export_pptx_png.ps1`**: 元 PPTX の画像とプレビューを並べた比較画像と差分スコアを出す
- HTML ビューアに下部ツールバー（前後移動・ページ番号ジャンプ・一覧表示）を追加。`preview_deck.py` / `check_layout.py` はツールバーを隠して撮影し、1枚ごとの再読み込みをやめて高速化。`check_layout.py` は canvas では見切れ・スライド外へのはみ出しのみを判定する

原案はチームメンバーによる v2.0.0 提案（canvas 型と PPTX 取り込み）。取り込み時に、注入対策（色・フォント・SVG の検証と許可リスト方式のサニタイズ）、`--into` の承認ゲート、XML パーサの安全化、Excel 取り込み範囲の上限を追加した。

## 設計上の注意

- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は macOS Keynote 互換性を壊す）。`notes` は HTML 側でのみ表示。
- 色は hex 直書きせずテーマトークンで指定。テーマ切替は `meta.theme` のみ。（例外: 取り込み専用の `canvas` 型は元資料の色をそのまま hex で持つ）
- 生成物（`build/`）は直接編集せず、deck.json を直して再ビルドする。

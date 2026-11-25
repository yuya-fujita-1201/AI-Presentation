# ビルド後の検査と、警告ごとの直し方

ビルドが済んだら、機械チェック → 目視 → PPTX の検証の順に確かめる。機械で拾えるものを先に潰すと、目視で見るべきものだけが残る。**直す順序はいつも「まず内容、次に密度、最後に `style`」**。`style` で位置や大きさを詰めると、自動フィットが効かなくなり、次に文字量が変わったときにまた崩れるため。

（`${CLAUDE_PLUGIN_ROOT}` は `SKILL.md` に書かれた実パスに読み替える。この補助ファイルでは変数が展開されない。番号は特記がない限りプレビュー PNG の番号で、deck.json の何枚目かとは限らない。）

## 1. 機械チェック

実行は次の番号の順（直したら 1 からやり直す）。`check_visual.py` は PNG を見るので、**先に 2 で全枚の PNG を作る**。入力（deck.json・`outline.md`・`assets/` など。`build/` 以外のフォルダ内のファイル）を更新すると PNG は古くなり、`check_visual.py` が `stale` を出す。

```bash
# 1. ビルド（警告・note はここでも出る）
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>
# 2. 全枚の PNG（playwright が必要）。番号を付けると、その枚だけ作り直す
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> [番号...]
# 3. 機械チェック（順不同）
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>                # はみ出し・重なり・文字の質を実測
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir>                # 空白帯・似たスライド・stale。pillow が必要。警告のみ
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>              # 文言・文字量・【要確認】の一覧
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>               # 図解タイプを使ったときだけ
# 4. 目視の準備と PPTX
python "${CLAUDE_PLUGIN_ROOT}/tools/contact_sheet.py" <deck_dir>               # 一覧画像 build/contact/（pillow）
python "${CLAUDE_PLUGIN_ROOT}/tools/check_pptx.py" <deck_dir>                  # PPTX と HTML の見た目の差（任意。LibreOffice が必要）
python "${CLAUDE_PLUGIN_ROOT}/tools/verify_pptx.py" <deck_dir>/build/<meta.id>.pptx   # PPTX の整合（build_deck.py が保存後に自動で通す。手で再実行するのは下の「3. PPTX の検証」の場合だけ）
```

`build_deck.py` は PPTX の保存後に `verify_pptx.py` と同じ検証を自動で行う。手で再実行が要るのは、PPTX を外部で編集したときと、`check_pptx.py` の前だけ（詳しくは下の「3. PPTX の検証」）。

### check_layout.py（番号は PNG の番号）

出力の 1 行は `slide-NN 種別: [要素]「文字」 内容 → 直し方`。

| 種別 | 扱い | 意味 | 直し方 |
|---|---|---|---|
| clip / bleed / overlap / rule / lines / spill（12px 超） | 不合格（exit 1） | 切れ・はみ出し・重なり・行数超過 | 文字を減らす・分ける。足りなければ `density`、最後に `style` |
| orphan | 警告 | 段落の最終行が 1〜2 文字だけ（泣き別れ） | 1 行ぶん短くする／`\n` で改行位置を変える。表のセルは 1〜2 字減らす |
| wordbreak | 警告 | 行の末尾が語の途中で折れている（「プラグイ／ン」「始／めます」）。例: `wordbreak: [li]「プラグインのファイルをアップロードする」 1行目の終わりが語の途中で折れている（「…ルをアップロ／ードする…」、2行中、25px）` | 文を短くする／文節の切れ目に `\n` を入れる／箱の幅・size を調整する。表のセルは列幅（`style.table.col_widths`）を広げる。ビルドが文節の改行を自動で入れるので、**残るのは利用者が size・幅を書いた領域か、行が増える直し方しか無い場所**（表のセル・kpi の label / note・合成ブロックの callout / text）。英文・URL だけの段落は対象外（canvas 型の要素だけは `qa_ignore: "wordbreak"` で外せる） |
| minfont | 警告 | 実際に描かれた文字が 9px 未満 | 図解はノード数・文字量を減らす。他は項目を減らす |
| contrast | 警告 | 文字と背景のコントラストが 4.5:1（大きい文字は 3:1）未満 | 文字色か背景色をテーマトークンで離す |
| linecross | 警告 | 線や枠が文字の上を通っている | ラベルを線から離す／線の経路を変える |

警告は 1 枚・1 種別あたり 6 件まで表示される（全件は `--json`）。

**文字色のコントラストは自動で整う**: 濃い面・色つきの面の上の文字（steps の「STEP n」、agenda の番号、matrix の強調象限、章扉・表紙の文字、図解ノードの文字・番号、表の `tone` の塗りの上の文字、`brand`）は、地の色の上で 4.5:1 に足りないときだけ、同じ色味のまま白か黒の側へ寄る。だから default テーマの `steps` で contrast が出ることはもう無い。出るのは、(a) 自分で色を書いた（`style` / `meta.layout_overrides` に書いた値は動かさない）、(b) 画像の上の文字（`image_text` の `bleed: true` の `brand` など。画像の色次第）、(c) 自作テーマの色の組み合わせ。直し方は、文字色か地の色をテーマトークンで離す・画像を替える・`opacity` を上げる。意図して低コントラストにするブランド指定は、レイアウト JSON に `"readable_pairs": { "steps": [] }` と書いて該当タイプの自動調整を止める（理由を報告に書く）。
**消えない警告は、試した手を添えて報告に残す**。順は 内容 → 密度 → `style`。警告を消すために内容を歪めたり、`style` を連打したりしない。意図して重ねた要素（合成スライドなど）は検査から外れる印（`data-qa-ignore`）が付く。

### lint_deck_text.py

- **不合格（exit 1）になるもの。どれも文言の問題で、`style` では直らない**: `closing` の `title` が 22 字超／Markdown 記法の残留（`**` `` ` `` `#`）／「N枚目」「Nページ目」の直書きが総枚数を超える／AI 定型句（「を実現」「効果的に」「シームレス」「鍵となる」など 16 語）。メッセージの「→」以降に直し方がある。
- **警告（exit に影響しない。直せるものは直す）**: 曖昧語（など・様々・適切に）／構成の説明（「左に〜」「下表の通り」。「半分以下にしたい」「3 割未満に」のような数量の「下に」は位置の説明と取り違えない）／体言止めのリード／タイトルの言い直しになっているリード／曖昧な表の列名（概要・備考）／凡例の無い ◎○△／4 桁以上で桁区切りの無い数／同じタイプが 3 枚以上続く箇所／和文と英数字の間の半角空白がそろっていない文字列（同じ文字列の中で、空白のある所と無い所が混ざるときだけ。全部入れる・全部詰めるのどちらも警告しない）／`relation` とタイプの不一致／基準日より後を「実績」と書いている・基準日より前に始まる計画／文字量の目安超え（密度で目安が変わる。**スライドの `density` が `meta.density` より優先**。talk は 1 項目 30 字・5 項目、standard は 40 字・6 項目、read は 60 字・8 項目。`schedule` は行・凡例・月の目盛りが表の形で並ぶので文字量の検査の対象外）。
- **AI の定番パターン（警告だが原則すべて直す）**: 0 埋めの番号「01」／強調のためのカギカッコ・行頭の【】ラベル（`【要確認】` は対象外）／全項目で同じラベルの繰り返し（`row_matrix` の行見出しへ括り出す）／「論点」なのに問いでないタイトル／共有と判断依頼を盛り合わせたタイトル（スライドを分ける）／定型の免責文・改行の無い長い注釈。理由と避け方は `${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` 8 章。
- **【要確認】の一覧**: `warn: slide-05 bullets[2] 要確認マーカー【年間の金額】: 「…」 → 確かめる点を【要確認: …】で明示するか、根拠を確かめて本文を確定しマーカーを消す` と出る（`notes` の中も数える）。ビルドも `note: 要確認が N 件あります（1 枚目 2 件（確かめる点）、…）` を出し、画面では黄色い下地（HTML）・色つきの太字（PPTX）で見える。ただし**ビルドの note は画面に出る分だけを数え、`notes` の中は数えない**（lint のほうが多いことがある）。**引き渡しの件数と一覧は、`notes` も数える lint の一覧を正として報告する**。直し方は文を弱めることではなく、確かめる点を `【要確認: …】` で明示するか、根拠を確かめてマーカーを消すこと（`${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` の「根拠が無いときは作らない」）。最終確認では `--fail-on-todo` を付けると、1 つでも残っていれば exit 1 になる。

### check_visual.py（警告のみ）

- `empty-bottom`（本文の下端まで続く大きな空白帯）／`empty-band`（本文の途中の空白帯）: 大きな箱に少ない文字になっている。材料にある根拠・事例があれば足すか、箱を詰める（項目を減らすと自動で詰まる）。**材料に無い根拠は足さない**。タイプを `numbered-columns` などの型や `kpi` に替える、前後の枚と統合する（`recipes.md` の「内容が薄いときの逃げ道」）。`density: "read"` は短い項目の空きを埋めない（文字が小さくなる）。余白が普通のタイプ（表紙・章扉・引用・言い切り・凡例など）は対象外。
- `similar`: 直前と見た目が似ている。1 枚を別のタイプに変える（内容の関係に合うタイプがあるとき）。
- `stale`: プレビュー PNG が deck.json より古い・枚数が足りない。`preview_deck.py <deck_dir>`（番号なし）で作り直す。

### 図解タイプの修理ループ（`check_diagram.py`）

診断は、ビルドを止めるスキーマの error（id 重複・存在しない参照・セルの衝突）と、止めない幾何の warning / note（線がノードを横切る・ラベルが重なる・詰まり過ぎ）の 2 種類。メッセージは `N枚目（type=…）: [code] 説明 → 修理指示1 / 修理指示2` の形で、修理指示に座標の候補が入っている。

1. 診断から 1 件選ぶ（error があれば error を優先）。
2. 修理指示のうち **1 点だけ** deck.json に反映する。一度に複数を直すと、どの変更が効いたか分からず、上流の直しで下流の指摘が連鎖して消えるのを見落とすため。
3. 再ビルド → `check_diagram.py` を再実行する。
4. 件数が減っていれば次の 1 件へ。**2 ラウンド続けて減らなければ止め、残った診断をそのまま利用者に報告する**（帳尻合わせで「解消した」と言わない）。

診断は座標上の問題だけを見る。矢印の向きやラベルの意味が実態に合っているかは判定できないので、PNG で必ず目で確かめる。コードの一覧は `${CLAUDE_PLUGIN_ROOT}/references/schema/diagram.md` の「図解タイプの診断」、作図の規約は `${CLAUDE_PLUGIN_ROOT}/references/diagram-guide.md`。

### ビルド時の警告・note

`warning:` はビルドが続く問題、`note:` は自動で調整した記録（表の文字を縮めた、など）。

合成スライド（`composite` / `split`）と主役のページの警告は、場所つきで出る（`N枚目（type=composite）の 2 つ目のブロック（text）: …`）。直し方の順は同じで、**まず内容**:
- 「文字がブロックに収まりません」「文字を 20px → 16px に縮めました」→ ブロックの文を短くする・項目を減らす。それでも縮むなら `composite` をやめて **2 枚に分ける**（ブロックが 4 個を超えるときも）。`columns` / `rows` の比率でブロックを広げるのは次の手。
- 「枠の中身が少なく、下の約Npx が空きます」（ビルドが文字を大きくして縦中央に置く整えをしたうえで、なお空くときだけ出る。`autofit: false` やブロックの `valign` を書いたときも出る）→ 箱（`frame: "box"`）を外す・項目を足す・`rows` で低くする。「格子に空きがあります」→ ブロックを足すか `columns` / `arrange` を減らす。「steps の 1 段の幅が…」→ 広いブロックにするか bullets にする。
- 「emphasis が N 個…」「強調（emphasis）のカードが N 枚…」→ 主役は 1 つ（cards は 2 枚まで）に絞る。「背景画像の上の文字の対比が…」→ `opacity` を上げるか、文字の下が均一な画像に替える。
- 型（pattern）をブロックに置いて「幅 470px 以上向きです（いま 440px）」「文字が最小 11.7px まで小さくなります」「型を 60% に縮めます」→ 警告の「→」にある手のとおり、ブロックを広げる（`col_span`・`columns` の比率）・高さを広げる（`rows`・`row_span`）・項目を減らす・単独のスライドにする。幅の下限は `pattern_engine.py list` の「ブロック」列（本文の型 16 個は半幅から読める）。意味と直し方は `${CLAUDE_PLUGIN_ROOT}/references/schema/validation.md`。自動フィットの警告が出たら、メッセージの直し方どおりに内容（項目数・文の長さ・分割）を直す（仕組みは `${CLAUDE_PLUGIN_ROOT}/references/schema/autofit.md`）。表が 7 行以上・5 列以上なら `meta.density: "read"` を勧める。

## 2. 目視

1. `contact_sheet.py` で一覧を見る（pillow が無ければ省略して個別に開く）。構図の偏り・似たスライドの連続・密度のむらを見る。
2. 気になる枚数と、重要なスライド（結論・主役の図）の PNG を開く。全枚を開く必要はない。
3. 採点基準 `${CLAUDE_PLUGIN_ROOT}/references/review-rubric.md` で自分で軽く採点する。**70 点未満、またはその基準の fail 条件に当たるスライドは直す**。
4. PPTX は LibreOffice の描画（`check_pptx.py`）で差の大きいスライドを開く。この機械に無いテーマのフォント（Meiryo など）は、ビルドが字幅の見積もりに使った代替フォント（例: Hiragino Sans）に**固定**して描くので、何度実行しても同じ見た目になる（以前は実行のたびに代替フォントが変わり、全スライドの画素が変わった）。実機の Meiryo の見え方ではない（置き換えたときは `note: フォント 'Meiryo' がこの環境に無いため、LibreOffice では 'Hiragino Sans' に置き換えて描きます…` が出る）。濃い箱の中の明るい文字が箱の下へ溢れる型（コード・長い表）は、差分の点数に出ないので `cmp-NN.png` を目で見る。PowerPoint 実機の見え方は確かめられないので、引き渡しのときに「未確認」と書く。HTML との見た目の対応と既知の差（影なし・自動調整なし・固定行送り・1 行目の下がり・表）は `${CLAUDE_PLUGIN_ROOT}/references/schema/validation.md` の「PPTX と HTML の見た目の対応と既知の差」。

**playwright が使えない環境**では、`preview_deck.py` の代わりに次のいずれか:

- `python "${CLAUDE_PLUGIN_ROOT}/tools/export_pdf.py" <deck_dir>` で PDF にして PDF ビューアで見る（LibreOffice が必要）。
- `soffice --headless --convert-to png <deck_dir>/build/<meta.id>.pptx` や `pdftoppm` で画像にする。
- 利用者に `build/<meta.id>.html` をブラウザで開いてもらう。

## 3. PPTX の検証

- `verify_pptx.py` が、zip 整合・全 XML の整形式・python-pptx での再パース・**全スライドにスピーカーノートが無いこと**・文書プロパティ（title が空でない・author が既定の `Steve Canny` でない）を確かめる。問題があれば直し方つきで表示して exit 1。
- スピーカーノートを PPTX に入れないのは、python-pptx のノートページが Keynote での互換性を壊すため。`notes` は HTML でだけ表示されるので、deck.json に書いてよい。
- 検証は `build_deck.py` で作り直すたびに自動で通る。手で通すのは、PPTX を外部で編集したとき、既存の PPTX をそのまま点検するとき、`check_pptx.py` の前（直したあとに再ビルドした PPTX が最終成果物になる）。

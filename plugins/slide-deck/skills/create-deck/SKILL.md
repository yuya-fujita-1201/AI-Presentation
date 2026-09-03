---
name: create-deck
description: JSON(deck.json)をソースにスライドを HTML / PowerPoint(16:9) にビルドする。ユーザーがプレゼン資料・スライド・デッキの新規作成（構成図・シーケンス図などの図解を含む）、または既存 deck.json の編集・微修正（特定スライドの位置・サイズ・色・フォントなどの個別調整を含む）を求めたときに使う。内容もデザインも deck.json のパラメーターで管理し、色はテーマトークンで指定する。デッキ全体の配色・フォントのセット（テーマ）そのものを新規に追加・切替したいだけなら add-theme を使う。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# create-deck — deck.json からスライドをビルドする

スライドは **内容もデザインもすべて `deck.json` のパラメーター**で管理する。仮想キャンバス 1280×720px（16:9）。HTML と PPTX は同じパラメーターから生成されるため、座標・配色・フォントサイズは共通ソースから解決され大枠は一致する（フォント実体やレンダラの違いによる細部差は残る）。

`${CLAUDE_PLUGIN_ROOT}` はこのプラグインの導入先ルート。スクリプトとテンプレートはそこに同梱されている。ユーザーのデッキ（`deck.json`）はユーザーのプロジェクト側に作る。

## 手順

### 0. 依存の確認（初回のみ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --check
```
`python-pptx` が未導入なら初回セットアップを促す（`/slide-deck:setup`、または `python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py"`）。`python` が無ければ `python3`（Windows は `py -3`）を使う。

### 1. スキーマと見本を把握する
- スキーマの正: `${CLAUDE_PLUGIN_ROOT}/references/deck-schema.md`（全スライドタイプ・`style` で上書きできる領域とプロパティ）
- 全タイプの見本: `${CLAUDE_PLUGIN_ROOT}/examples/template-sample/deck.json`（新規はこれをコピーして書き換えるのが早い）

### 1.5 内容を設計する（デザインの前に構成を決める）
`${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` を読み、deck.json を書き始める前に**内容そのもの**を設計する。デザイン（配色・レイアウト）が整っていても、構成が悪く根拠のないスライドは伝わらない。
- 聞き手・目的・時間と枚数の目安・前提知識の深さを決める（不明なら、内容ガイド6章の項目をユーザーに最初に1回だけまとめて確認する）
- 内容ガイド2章のストーリー構成の型（SCQA / PREP / 課題→原因→打ち手→効果 / 比較検討型）から1つ選び、8〜12枚程度の骨子（各スライドの type と役割）を仮組みする
- 各スライドのタイトルを「結論を言う一文」で仮に書けるか確認してから、次の手順で deck.json に落とし込む（微修正だけの依頼で構成が既に固まっている場合はこの手順を省略してよい）

### 2. deck.json を作る（ユーザーのプロジェクト内）
- `decks/<デッキ名>/deck.json` を作成（場所はユーザーのプロジェクトに合わせる）。フォルダ名がそのままデッキ ID になる
- `meta`（`title` と、任意で `id` / `theme`）と `slides` を記述。`meta.id` は**省略可**（省略時はフォルダ名を使う。出力ファイル名にもなる）
- 色は hex 直書きせず**テーマトークン**（`primary` / `accent` 等）で指定。テーマは `meta.theme` で切替（同梱: `default` / `accenture-purple`）。新テーマ追加は `/slide-deck:add-theme`

#### 内容の目安（1枚1メッセージ）
- タイトル `title` は 25 字以内、リード文 `lead` は 60 字以内を目安にする
- `bullets` の項目は 3〜6 個、1項目は 40 字以内が目安（多い場合は分割するか `two_column` / `cards` を検討）
- `table` の行数は 6 行以内（それ以上は分割するか要約する）
- `cards` は 3〜6 枚（列数 `columns` は 3 前後）
- `architecture` / `dataflow` / `lifecycle` はノード 12 個以下・列（`col`）6 以下、`sequence` は参加者 7 人以下・メッセージ 12 本以下を目安にする（超えると `check_diagram.py` が `too-dense` 等で警告する）
- 1スライドに情報を詰め込みすぎない。伝えたいメッセージが2つ以上あるなら、スライドを分ける

#### スライドタイプの選び方
| 伝えたいこと | 使うタイプ |
|---|---|
| 比較・対比 | `two_column`（2案）/ `table`（項目×複数案） |
| 手順・フロー | `steps`（単純な工程）/ `swimlane`（役割をまたぐ業務フロー） |
| 2軸での位置づけ | `matrix` |
| 列挙・整理 | `bullets`（線形）/ `cards`（並列カード） |
| システム構成・連携図 | `architecture` |
| データの流れ | `dataflow` |
| 状態遷移 | `lifecycle` |
| 呼び出し順序 | `sequence` |
| 主張・キーメッセージ | `quote` |
| 図版（下記「図解が欲しいとき」参照） | `image_text` / `image` |

`swimlane` は既定で `legend: true` のため、そのスイムレーンの直前に凡例ページが自動で1枚追加される（合計ページ数を指定されている場合は +1 になる点に注意。厳密に枚数を守りたいときは `legend: false` にするか、その分をあらかじめ見込む）。

#### 図解が欲しいとき（優先順位）
図解＝画像とは限らない。次の優先順位で選ぶ:
1. **ネイティブ図解タイプで表現できないか検討する**（上の「スライドタイプの選び方」）。`steps` / `swimlane` / `matrix` / `cards` / `architecture` / `dataflow` / `lifecycle` / `sequence` はデッキのテーマに追随し、あとから位置・色を `style` で微修正できるので、これらで表現できるなら画像より優先する
2. 上記で表現できない図版（スクリーンショット、既存の図表資料など）だけ `image` / `image_text` を使う。画像の入手は次の順で検討する: **(a) ユーザーから提供された画像を使う → (b) デッキの `assets/` にある既存画像を流用 → (c) 簡単な図なら SVG を自分で書いて `assets/` に置く**（利用可能なら画像生成ツールで代替してもよい）
3. 画像は 4:3 前後（例: 1024×768）が最も収まりが良い（`image_text` の `img` 領域は既定 524×378px、`image` 単独の `img` 領域は既定 1136×440px なので極端な縦長・横長は避ける）

### 3. ビルド
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>          # HTML + PPTX
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html  # HTML のみ
```
生成物は `<deck_dir>/build/` に出力（ファイル名は `meta.id`）。

### 4. 機械チェック → 目視確認 → 検証（この順で必須）
まず自動チェックで機械的に直せる問題を潰してから、目視で仕上がりを確認する。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>       # はみ出し・重なり・文字あふれを検出
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>     # 文字量・AI定型句などの文言チェック
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>      # architecture/dataflow/lifecycle/sequence/swimlane の配線・ラベルを診断
```
いずれも exit 1 で終了した場合は、報告された内容（該当スライド番号・領域）に沿って deck.json の `style` を直してから再ビルドし、再度チェックする。新しいテーマを使った場合は `python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <theme名>` でコントラストも確認する。図解タイプ（`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane`）を1枚でも使ったデッキは `check_diagram.py` も必ず実行し、直し方は次項「4.5 図解タイプの修理ループ」に従う。

チェックを通過したら目視確認する:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> [番号...]  # PNG化(要 playwright)
```
PNG を開いて「文字切れ・要素の重なり・表の収まり・画像とキャプションの配置」を確認する。

**Playwright が使えない環境**（社内プロキシでインストール不可等）では、`preview_deck.py` の代わりに次のいずれかで代替する:
- `python "${CLAUDE_PLUGIN_ROOT}/tools/export_pdf.py" <deck_dir>` で PDF 化し、PDF ビューアで確認する（LibreOffice が必要。無ければ手順内で案内が出る）
- `soffice --headless --convert-to png <deck_dir>/build/<meta.id>.pptx` や `pdftoppm` で画像化する
- ユーザーに `build/<meta.id>.html` を直接ブラウザで開いてもらい、確認を依頼する

最後に PPTX を検証する: zip 整合と `Presentation()` 再パースを確認し、全スライドで `has_notes_slide` が False であること。

まとめて確認したい場合は `/slide-deck:review-deck` スキルも使える。

### 4.5 図解タイプの修理ループ
`check_diagram.py` の診断は、`build_deck.py` が止める**スキーマ的な error**（id 重複・存在しない参照・セルの衝突など）と、ビルドは止めない**幾何の warning/note**（線がノードを横切る・ラベルが重なる・交差や詰まり過ぎ等）の2種類を返す。メッセージは `N枚目（type=…）: [code] 説明 → 修理指示1 / 修理指示2` の形で、修理指示（fixes）に `via` や `label_at` の座標候補などが具体的に入っている。

直すときは次のループを守る（一気に全部直そうとしない）:
1. 診断結果から1件選ぶ（error があれば error を優先）
2. その fixes のうち **1点だけ** deck.json に反映する（複数の指示を一度にまとめて適用しない）
3. 再ビルド → `check_diagram.py <deck_dir>` を再実行する
4. 件数が減っていれば次の1件へ。**2ラウンド続けて件数が減らなければそこで止め、残った診断をそのままユーザーに正直に報告する**（見た目の帳尻合わせで「解消した」と言わない）

診断が見ているのは**座標上の問題**だけで、矢印の向きやラベルの意味が実態と合っているかまでは判定できない。`preview_deck.py` の PNG で必ず目視して意味の正しさを確認する。

## 微修正のルール（重要）
- 位置・サイズ・フォント・色の変更依頼が来たら、**スライドを作り直さず該当スライドの `style` に差分だけ書く**。デッキ全体なら `meta.layout_overrides`
- 図解タイプ（`architecture` / `dataflow` / `lifecycle` / `sequence`）の `row` / `col` / `via` / `from_side` も、`check_diagram.py` の診断が指摘した1点だけを直す（上記4.5と同じ考え方。まとめて配置を作り直さない）
- 生成物（`build/`）は直接編集しない。修正は必ず deck.json → 再ビルド
- 微修正後は `--html` で再ビルド → `preview_deck.py <deck_dir> <番号>` で当該スライドだけ再確認してから PPTX を再生成
- 修正のたびに手順4の `check_layout.py` / `lint_deck_text.py` / `check_diagram.py` を再実行し直す必要はないが、文字量やレイアウト・図解の配置を大きく変える修正をしたときは再実行する

## 成果物の渡し方
作業が終わったら、生成物の絶対パスをユーザーに伝える: `<deck_dir>/build/<meta.id>.html`（ブラウザで開いてプレビュー、← / → キーで移動）と `<deck_dir>/build/<meta.id>.pptx`（PowerPoint / Keynote で開く）。

## 厳守
- **PPTX にスピーカーノートを出力しない**（python-pptx の notes_slide は Keynote 互換性を破壊する）。`notes` フィールドは HTML でのみ表示され、ビルダーが自動処理するので deck.json に書くのは OK

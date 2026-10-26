---
name: review-deck
description: 既存の deck.json を一括レビューする（構造・文言・数量・図解・見た目の機械チェック＋評価エージェントの採点と修正ループ）。ユーザーが「このデッキをレビューして」「品質を確認して」「おかしいところがないか一通り見て」のように既存デッキ全体の点検を求めたときに使う。個別スライドの作成・微修正は create-deck を使う。
allowed-tools: Bash, Read, Edit, Glob, Grep, Agent, AskUserQuestion
---

# review-deck — 既存デッキの機械 QA 一括レビュー

`create-deck` の手順4（機械チェック）を1回でまとめて回したうえで、`content-guide.md` に沿った内容チェックを行い、最後に生成の経緯を知らない評価エージェント（`deck-evaluator`）にプレビュー画像を採点させて fail のスライドを直す。機械チェックは実装済みの検証ツールを束ねるだけで新しいロジックは持たない。

## 手順

### 1. ビルド（HTML）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
```

### 2. 構造チェック（はみ出し・重なり・文字あふれ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>
```

### 3. 文言チェック（文字量・AI定型句・主張の書き方・日付の整合など）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>
```

### 4. 数量チェック（スライドタイプ別の文字数・項目数の統計）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/deck_metrics.py" <deck_dir>
```

### 5. 図解チェック（architecture/dataflow/lifecycle/sequence/swimlane/schedule の配線・ラベル診断）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>
```
図解タイプを1枚も使っていないデッキでは対象0件で正常終了する。指摘があれば `create-deck` スキルの「4.5 図解タイプの修理ループ」の手順（診断1件→fixesの1点だけ直す→再診断、2ラウンド改善なしで停止）に従う。

### 6. 一覧サムネイル（pillow がある場合のみ）
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/contact_sheet.py" <deck_dir>
```
pillow が無い、または playwright が使えない環境では失敗しても致命的ではない（一覧確認を省略し、個別の `preview_deck.py` に切り替える）。

続けて、プレビュー PNG から見た目の偏りを機械で確かめる（`build/preview/` に全スライドの PNG が無ければ先に `preview_deck.py <deck_dir>` を番号なしで実行する）:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir>
```
`[empty-bottom]`（下1/3がほぼ空＝大きな箱に少ない文字）と `[similar]`（直前と見た目が似ている＝同じ構図の連続）を警告する。いずれもビルドは止めない。

新しいテーマを使っているデッキなら、あわせてコントラストも確認する:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <テーマ名>
```

### 7. 内容チェック（機械チェックでは検出できない質）
上記1〜6は文字量・レイアウト・記法崩れなど**機械的に検出できる不備**の点検であり、構成や説得力そのものは見ていない。`${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` のチェックリスト（6章）に沿って、スライドごとに次を目視確認する。

- タイトルが結論文になっているか（「〜の現状」のような話題ラベルのままになっていないか）
- 本文（`bullets` / `table` / `lead` 等）にタイトルの結論を裏付ける根拠（数字・事例・出典）があるか
- 1スライドに複数のメッセージが混在していないか（1スライド1メッセージ）
- 抽象語（最適化・推進・活用 等）が具体的な動作・数字に言い換えられているか
- `closing` に「次のアクション」と「判断してほしいこと」が明示されているか

構成レベルの問題（型が合っていない、根拠が丸ごと抜けている等）は `style` の差分では直せないため、deck.json の該当スライドの中身（`title` / `bullets` / `lead` 等の文言）を書き直す提案として提示する。

### 8. 評価エージェントの採点と修正ループ（修正は最大3周）
機械チェック（2〜6）と内容チェック（7）の後で、プレビュー画像を**生成の経緯を知らない評価者**に採点させる。自分で作ったスライドを自分で見ると甘くなるため、採点は必ずサブエージェントに任せ、このセッションは修正だけを担当する。

**8-1. 準備**: 手順6の PNG（`build/preview/slide-NN.png`）が最新であることを確かめ、番号の対応表を書き出す。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir> --json <deck_dir>/build/visual.json
```
`visual.json` の各行の `slide` は PNG の番号、`src` は deck.json の `slides` の何枚目か（1 始まり。自動挿入された凡例ページは null）。評価結果の番号はすべて PNG の番号なので、deck.json を直すときは必ず `src` で引き直す。

**8-2. 採点**: Agent ツールで `slide-deck:deck-evaluator` を呼ぶ。プロンプトには次だけを渡す（作成の経緯・意図・前の周回の結果は渡さない）:
```
deck_dir: <deck_dir の絶対パス>
plugin_root: ${CLAUDE_PLUGIN_ROOT}
round: <1 は初回の採点。修正後の採点は 2〜4>
slides: <2周目以降は直したスライドの PNG 番号。1周目は省略＝全スライド>
visual_json: <deck_dir>/build/visual.json
```
返ってきた JSON 配列（`slide` / `severity` / `score` / `issues` / `fix_hint` / `evidence`）をそのまま `<deck_dir>/build/review/round-<N>.json` に保存し、`severity: "fail"`（70 点未満を含む）のスライドを修正対象にする。warn は修正せず、最後の報告に載せる。`slide: 0`（デッキ全体の所見）は修正対象にせず報告だけする。

**8-3. 修正の承認（最初の1回だけ）**: fail が1件でもあれば、直す前に fail の一覧（番号・点数・issues・fix_hint）を提示し、`AskUserQuestion` で「deck.json を書き換えて直してよいか」を確認する（`create-deck` の「既存ファイルを上書きする前の承認ゲート」と同じ考え方）。ユーザーが最初から「直して」と頼んでいる場合は確認を省いてよい。承認されなければ修正せず、9 の報告に進む。承認後は打ち切りまで確認を挟まない。

**8-4. 修正**: fail のスライドだけを、`create-deck` の微修正ルールに従って deck.json で直す（`build/` は直接編集しない。fail ではないスライドは触らない）。`fix_hint` は案であり、スキーマで表現できないもの（存在しない `style` のキーなど）は採用せず、`${CLAUDE_PLUGIN_ROOT}/references/deck-schema.md` で動かせる範囲の手段に置き換える。直し方の目安:
- 文字の切れ・あふれ・泣き別れ → 文言を短く・分割する。足りなければ該当スライドの `style` で領域の `size` / `h` / `line_height` を差分で変える
- 下が空く・重心が偏る → 根拠（数字・事例）を足す。足す材料が無ければ `style` で箱を詰める・`valign` を変える（`valign` が効くのは bullets の `body`、two_column の `left` / `right`、cards / matrix の `grid` など一部だけ。image_text などは `body` の `y` / `h` で寄せる。ビルドは未知のキーを黙って無視するので、効いたかは必ず再プレビューで確かめる）
- 結論が見えない → `title` を結論文に、`lead` に根拠の要点を書き直す（文言の修正）
- タイプが内容の関係に合わない・均等割り・直前と同じ構図 → タイプを変える（`relation` も合わせて直す）。中身を作り直すことになるので、1周で直すのは 1〜2 枚まで
- 図解の線・ラベル → `check_diagram.py` の fixes を1点だけ反映する（`create-deck` の 4.5 と同じ）

**8-5. 再ビルドと再評価**: 直したら次を順に実行し、直したスライドだけを 8-2 で採点し直す（`round` を1つ上げる）。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> <直したスライドの PNG 番号...>
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir> --json <deck_dir>/build/visual.json
```
タイプを変えて枚数（凡例ページの有無）が変わった場合は `preview_deck.py <deck_dir>` を番号なしで実行し直し、番号を引き直す。修正で check_layout の error が新たに出たら、その修正は取り消すか直してから採点に回す。

**8-6. 打ち切り**: 「修正→再評価」を 3 周したら（round 4 の採点まで）、または fail が0になったら止める。3 周直しても fail のスライドは「未解決」として、最後の点数・issues と、試した修正を報告する。点数を上げるために評価エージェントへの入力を変えたり、未解決を「解消」と書いたりしない。ループを終えたら `build_deck.py <deck_dir>`（HTML＋PPTX）で PPTX を作り直し、zip 整合・`Presentation()` 再パース・全スライドで `has_notes_slide` が False であることを確認する。

## 9. 指摘の要約と修正提案
各ツールが stderr に出す `warning:` / `error:` を「N枚目（type=xxx）: 内容」の形でスライド番号ごとに集約し、ユーザーに一覧で提示する。`check_diagram.py` の指摘は診断 code も残す（「N枚目（type=xxx）: [code] 内容」の形。code はそのまま修理ループでの参照キーになる）。修正が明確なもの（文字あふれ・はみ出し・色 typo 等）は、`create-deck` の微修正ルールに従い **該当スライドの `style` への差分**として修正案を提示する。ユーザーが適用を求めたら deck.json を編集し、`build_deck.py <deck_dir> --html` → `check_layout.py <deck_dir>`（図解タイプがあれば `check_diagram.py <deck_dir>` も）を再実行して解消を確認する。

8 の評価ループの結果は、周回ごとに「N周目: fail X枚 → 直したスライドと直し方」の形でまとめ、最後に `未解決`（3 周後も fail のスライド・点数・残った issues）と `warn`（直さなかった指摘）を分けて書く。

エラー（exit 1 で止まるもの）は必ず解消してから再ビルドする。警告はビルドを止めないため、内容を見て対応要否をユーザーと相談してよい。

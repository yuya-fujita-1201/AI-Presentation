---
name: review-deck
description: 既存の deck.json を一括点検する（機械チェック＋評価エージェントの採点と修正ループ）。「このデッキをレビューして」「品質を確認して」「おかしいところがないか見て」で使う。新規作成・個別の微修正は create-deck。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# review-deck — 既存デッキの一括レビュー

`create-deck` の検査を 1 回でまとめて回し、内容の質を確かめ、最後に生成の経緯を知らない評価エージェント（`deck-evaluator`）にプレビュー画像を採点させて、fail のスライドを直す。機械チェックは既存の検査ツールを束ねるだけで、新しいロジックは持たない。

`${CLAUDE_PLUGIN_ROOT}` はプラグインの導入先。各検査の読み方と直し方は `${CLAUDE_PLUGIN_ROOT}/skills/create-deck/checks.md`、採点基準は `${CLAUDE_PLUGIN_ROOT}/references/review-rubric.md`。**スライド番号は、すべてプレビュー PNG の番号**（凡例ページの自動挿入・agenda の分割込み）。deck.json の何枚目かではない。

## 1. 機械チェック

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir>                 # HTML + PPTX。警告・note をここで読む
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>               # はみ出し・重なり・泣き別れ・語の途中の折れ・小さい文字・コントラスト・線と文字の衝突
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>             # 文言・文字量（meta.density で目安が変わる）・【要確認】の一覧
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>              # 図解タイプが無ければ対象 0 件で終わる
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir>               # 全枚の PNG（playwright）
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir> --json <deck_dir>/build/visual.json   # 空白帯・似たスライドの連続・PNG が古いか（pillow）
python "${CLAUDE_PLUGIN_ROOT}/tools/contact_sheet.py" <deck_dir>              # 一覧画像（pillow）
python "${CLAUDE_PLUGIN_ROOT}/tools/verify_pptx.py" <deck_dir>/build/<meta.id>.pptx   # PPTX の整合（ノート無し・文書プロパティを含む。ビルド済みの PPTX をそのまま点検するのでここで手で通す）
```

- **【要確認】が残っているデッキ**: ビルドは画面に出る文字の【要確認】を目立たせ（HTML は黄色い下地、PPTX は色つきの太字）、`note: 要確認が N 件あります（1 枚目 2 件（確かめる点）、…）` に枚ごとの件数を出す。`lint_deck_text.py` は `notes` の中も数える（`slide-NN` の番号は PNG の番号）。残っているのは「根拠が無いと正直に示している」状態で、減点の理由にはならない。直すのは、確かめられる内容を確かめてマーカーを消すこと（作って埋めない）。評価エージェントには経緯を渡さない（強調された印の扱いは採点基準にある）。件数と一覧は報告に載せ、`--fail-on-todo` を最終確認に使うかを利用者に聞く。
- 検査の読み方で変わった点: `wordbreak`（行の末尾が語の途中で折れている）はビルドが文節の改行を自動で入れるので、出るのは利用者が size・幅を書いた領域と、行が増える直し方しか無い場所（表のセル・kpi の label / note）。文を短くする／`\n` を入れる／列幅・箱の幅を広げる（読み方は `checks.md`）。文字色の対比は、steps の「STEP n」・agenda の番号・図解ノード・表の `tone` などをビルドが自動で整えるので、`check_layout.py` の contrast が出るのは自分で色を書いた箇所か画像の上の文字（`image_text` の `bleed` の `brand` など）。`lint_deck_text.py` の「和文と英数字の間の空白」は、同じ文字列の中で空白が混ざっているときだけ警告する（直し方は統一）。
- 新しいテーマを使っているデッキなら `python "${CLAUDE_PLUGIN_ROOT}/tools/check_theme.py" <テーマ名> --deck <deck_dir>` でコントラストも確かめる。
- 図解の指摘は `checks.md` の修理ループ（1 件ずつ・1 点だけ直す・2 ラウンドで止める）に従う。
- `check_pptx.py <deck_dir>`（LibreOffice で PPTX を描き、HTML と比べる）は任意。差が大きいスライドの `build/pptx-compare/cmp-NN.png` を目で見る。PowerPoint 実機とは違う描画なので、参考値として扱う。
- 数量の偏りを見たいときは `deck_metrics.py <deck_dir>` で、タイプ別の文字数・項目数を確かめる（出力は表だけで合否は出ない。他のデッキと並べる比較用）。
- playwright・pillow・LibreOffice が無い項目は、省いたことを最後の報告に書く。致命ではない。

## 2. 内容チェック（機械では見つからない質）

機械チェックは文字量や記法などの不備を見るもので、構成や説得力は見ていない。`${CLAUDE_PLUGIN_ROOT}/references/content-guide.md` のチェックリストに沿って、スライドごとに確かめる。

- タイトルが結論文になっているか（話題ラベルのままではないか）。タイトルだけを順に読んで話が通るか。
- 本文にタイトルを裏付ける根拠（数字・事例・出典）があるか。**根拠が無い箇所に数字が作られていないか**（【要確認】で示されているか）。
- 1 スライドに複数のメッセージが混ざっていないか（1 枚に複数ブロックを置く合成スライドは、2〜3 個のブロックが 1 つの主張を支えているか）。主役のページ（variant・背景画像・`split`・強調したカード）が 20 枚に 3〜5 枚程度で、転換点・結論に置かれているか。抽象語が具体的な動作・数字に言い換えられているか。
- `closing` に次のアクションと判断してほしいことがあるか。
- content-guide.md 8 章「AI が作ったと一目で分かるパターン」（全部盛り・見出し直下の補足・同じラベルの繰り返し・意味の無い色替えや幅の違い・区切り線・定型の免責注釈など）に当てはまらないか。

構成レベルの問題（型が合わない・根拠が丸ごと無い）は `style` では直らない。該当スライドの文言を書き直す提案として出す。**【要確認】の件数と一覧**は、引き渡しの報告に必ず載せる。

## 3. 評価エージェントの採点と修正ループ（修正は最大 3 周）

自分が見たスライドは甘く採点しがちなので、採点は必ずサブエージェントに任せ、このセッションは修正だけを担当する。

**3-1. 準備**: 手順 1 の PNG と `visual.json` が最新であることを確かめる。`visual.json` の各行の `slide` は PNG の番号、`src` は deck.json の `slides` の何枚目か（自動挿入された凡例ページは null）。評価結果の番号は PNG の番号なので、deck.json を直すときは必ず `src` で引き直す。

**3-2. 採点**: Agent ツールで `slide-deck:deck-evaluator` を呼ぶ。渡すのは次だけ（作成の経緯・意図・前の周回の結果は渡さない）。
```
deck_dir: <deck_dir の絶対パス>
plugin_root: ${CLAUDE_PLUGIN_ROOT}
round: <1 は初回。修正後の採点は 2〜4>
slides: <2 周目以降は直したスライドの PNG 番号。1 周目は省略 = 全スライド>
visual_json: <deck_dir>/build/visual.json
```
返ってきた JSON 配列（`slide` / `severity` / `score` / `issues` / `fix_hint` / `evidence`）をそのまま `<deck_dir>/build/review/round-<N>.json` に保存し、`severity: "fail"`（70 点未満を含む）のスライドを修正対象にする。warn は直さず、最後の報告に載せる。`issues` の先頭の `[3]` などは採点基準の観点番号で、優先度の判断に使う。

`slide: 0` は**デッキ全体の所見**（タイトル列の読み筋 [A]・冒頭と結びの接続 [B]・同じ構図の連続と抑揚 [C]・密度のむら [D]・要確認の残り [E]）。自動では直さず、報告に載せて、どのスライドをどう直すかの提案（`fix_hint`）を添える。利用者が直すことを選んだら、通常の修正として扱う。

**3-3. 修正の承認（最初の 1 回だけ）**: fail が 1 件でもあれば、直す前に一覧（番号・点数・issues・fix_hint）を見せ、`AskUserQuestion` で「deck.json を書き換えて直してよいか」を確かめる。利用者が最初から「直して」と頼んでいるなら省く。承認されなければ直さずに 4 の報告へ進む。承認後は打ち切りまで確認を挟まない。承認の考え方は `${CLAUDE_PLUGIN_ROOT}/references/approval-gates.md`。

**3-4. 修正**: fail のスライドだけを、deck.json で直す（`build/` は直接編集しない。fail でないスライドは触らない）。`fix_hint` は案であり、スキーマで表せないもの（存在しない `style` のキー）は採らない。キーは索引 `${CLAUDE_PLUGIN_ROOT}/references/deck-schema.md` と、そのスライドのタイプのファイル（`references/schema/*.md` の「領域:」行）で確かめる。直す順序は**内容 → 密度（`density`）→ `style`**。
- 文字の切れ・あふれ・泣き別れ・語の途中の折れ（`wordbreak`）→ 文言を短く・分割する。足りなければ `density`、最後に `style`。
- 下が空く・重心が偏る → 根拠（数字・事例）を足す。材料が無ければ項目を減らして箱を詰める（作らない。無い数字は足さず【要確認】）。ビルドは未知の `style` のキーを黙って無視する場合があるので、効いたかは必ず再プレビューで確かめる。
- 結論が見えない → `title` を結論文に、`lead` に根拠の要点を書き直す。
- タイプが内容の関係に合わない・均等割り・直前と同じ構図 → タイプを変える（`relation` も直す）。中身を作り直すことになるので、1 周で直すのは 1〜2 枚まで。
- 合成スライドの詰め込み（文字が小さい・主張が複数）→ 2 枚に分ける。主役が多すぎる・無い（[C]）→ 転換点と結論の 1〜2 枚だけに `variant` / `split` / `emphasis` を付ける（主役ページの置き方は `create-deck` の「デッキに抑揚を付ける」）。
- 図解の線・ラベル → `check_diagram.py` の指示を 1 点だけ反映する。

**3-5. 再ビルドと再採点**: 直したら次を実行し、直したスライドだけを 3-2 で採点し直す（`round` を 1 つ上げる）。
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/lint_deck_text.py" <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir> <直したスライドの PNG 番号...>
python "${CLAUDE_PLUGIN_ROOT}/tools/check_visual.py" <deck_dir> --json <deck_dir>/build/visual.json
```
タイプを変えて枚数（凡例ページの有無）が変わった場合は、`preview_deck.py <deck_dir>`（番号なし）で作り直して番号を引き直す。修正で check_layout の不合格が新たに出たら、その修正は取り消すか直してから採点に回す。

**3-6. 打ち切り**: 「修正 → 再採点」を 3 周したら（round 4 の採点まで）、または fail が 0 になったら止める。3 周直しても fail のスライドは「未解決」として、最後の点数・issues と試した修正を報告する。点数を上げるために評価エージェントへの入力を変えたり、未解決を「解消」と書いたりしない。ループを終えたら `build_deck.py <deck_dir>`（HTML＋PPTX）で PPTX を作り直し、`verify_pptx.py` を通す。

## 4. 報告

各ツールの `warning:` / `error:` を「N枚目（type=xxx）: 内容」の形でスライド番号ごとにまとめて見せる。`check_diagram.py` の指摘は診断 code も残す（修理ループで参照するため）。修正が明確なもの（文字あふれ・はみ出し・色の typo）は、`create-deck` の `edit.md` の考え方（内容 → 密度 → style の差分）で提案し、利用者が適用を求めたら deck.json を編集して、再ビルド・再検査で解消を確かめる。

評価ループの結果は、周回ごとに「N 周目: fail X 枚 → 直したスライドと直し方」の形でまとめ、最後に次を分けて書く。
- **未解決**: 3 周後も fail のスライド・点数・残った issues
- **warn**: 直さなかった指摘
- **デッキ全体の所見**（`slide: 0`）
- **【要確認】の件数と一覧**（ビルドの note と lint の件数が合っているかも見る。ずれるのは `notes` の中だけにある分）
- **確かめていないこと**: PowerPoint 実機での見え方、省いた検査

エラー（exit 1 で止まるもの）は必ず解消してから再ビルドする。警告はビルドを止めないので、内容を見て対応の要否を利用者と相談してよい。

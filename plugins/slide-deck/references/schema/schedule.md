# `schedule` — 矢羽根スケジュール（ガント／工程表）

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。診断コードの一覧は [diagram.md](diagram.md) の「図解タイプの診断」。

```json
{ "type": "schedule", "eyebrow": "SCHEDULE", "title": "全体スケジュール",
  "timeline": { "start": "2026-09", "end": "2027-08", "unit": "month" },
  "periods": [ { "label": "FY27 Q1（2026/9〜11月）", "span": 3 }, { "label": "Q2", "span": 3 }, { "label": "Q3", "span": 3 }, { "label": "Q4", "span": 3 } ],
  "today": "2026-10-05",
  "rows": [
    { "group": "節目", "label": "マイルストーン",
      "milestones": [ { "at": "2026-10-31", "label": "10月末RV完了" } ] },
    { "group": "開発", "label": "要件定義〜テスト", "sub": "開発チーム",
      "bars": [
        { "start": "2026-09", "end": "2026-10", "label": "要件定義" },
        { "start": "2026-11", "end": "2026-12-25", "label": "運用", "variant": "ongoing" } ] }
  ],
  "legend_labels": { "main": "主要タスク（成果物を出す）" },
  "note": "※ 注記（凡例の右端に表示）" }
```
領域: `title`, `rule`, `lead`, `chart`, `footer_l/r`。左に行見出し（`label`＋小さな `sub`）、上に時間軸（`periods` の大見出し＋列見出し）、右に矢羽根・節目・現在線を描く。**座標は書かない**。期間（日付・列）だけを書けば、エンジン（`tools/schedule_engine.py`）が時間軸に合わせて位置を計算するので、HTML と PPTX のどちらでも矢羽根の始点・終点が軸とズレない。PPTX では矢羽根＝ホームベース／山形、節目＝ひし形、見出し＝四角形のネイティブ図形で描き、文字も図形に直接入れるため、PowerPoint 上で1本ずつ選んで文言・色・長さを直せる（図全体は1つのグループ。ダブルクリックで中の図形を編集できる）。

- **時間軸**: `timeline`（`unit` は `month`＝"YYYY-MM"〜"YYYY-MM" / `week`＝"YYYY-MM-DD"〜"YYYY-MM-DD"、列見出しは自動で「9月」「10/5」形式）か、`columns`（列見出しの配列を直接指定）のどちらかが必須。両方書くと `columns` が見出しの表示文字列として使われる（数は timeline の列数と一致させる）。
- **位置の書き方**（`bars[].start` / `end`、`milestones[].at`、`today`）: `"YYYY-MM-DD"`（timeline 指定時。日単位で按分）/ `"YYYY-MM"`（start は月初、end は月末）/ 列見出しの文字列（例 `"10月"`。start は列の左端、end は列の右端）/ 数値（列単位。0 が先頭列の左端）。時間軸の範囲外・`end` が `start` 以前はビルドエラー。
- **行 `rows[]`**: `label`（必須推奨）/ `sub`（担当など小さく2段目）/ `group`（連続する同じ値を左端の縦帯にまとめる）/ `bars[]` / `milestones[]`。節目は専用の行（例「マイルストーン」）に置くのを推奨（近いラベルは自動で段をずらし、行の高さも自動で確保する）。
- **矢羽根 `bars[]`**: `{ start, end, label, variant, shape, label_pos }`。`variant`: `main`（既定・primary 塗り）/ `accent`（accent 塗り）/ `muted`（muted 塗り）/ `prep`（淡色＋枠）/ `ongoing`（白地＋枠）/ `tbd`（白地＋破線枠＝要調整・未確定）。`shape`: `arrow`（既定・ホームベース）/ `chevron`（山形）/ `bar`（四角）。ラベルが矢羽根に収まらないと文字を縮め（下限 10px）、`label_pos` を書いていなければ**矢羽根の右（外）に自動で出す**（右に十分な空きがあり、同じ行の次の矢羽根にぶつからないとき。縮めて 12px 未満になるラベルも、右が空いていれば外へ出す。`info: bar-label-moved`「…のラベル「…」が矢羽根の中に収まらないため、矢羽根の右に出しました」）。右にも出せない（右端に近い・次の矢羽根にぶつかる）ときで、矢羽根の中に 12px 以上で入らないラベルは、**左に出す**（`label_pos: "before"`。矢羽根の外のラベルは行の地の色の座布団つき）。入らないとき・`"label_pos": "inside"` を明示したときは中に置いて `bar-label-overflow` 警告。`label_pos` に書けるのは `inside` / `after` / `before`（`"after"` で最初から外に出せる）。自動移動を止めるのは `style.chart.auto_after: false`（右へ出す処理）・`style.chart.auto_before: false`（右に出せないとき左へ出す処理）か、そのラベルに `label_pos` を書くこと（`autofit: false` では止まらない）。同じ行で期間が重なると `bar-overlap` 警告。
- **節目 `milestones[]`**: `{ at, label }`。ひし形＋下にラベル。節目のラベルと、矢羽根の外に出したラベルは、行の地の色の座布団を敷く（月の縦線が文字を貫かない。HTML と PPTX で同じ）。
- **`periods[]`**: `{ label, span }`（span＝列数）。四半期・年度などの大見出し。境界の縦罫線は太線になる。
- **`today`**: 現在線（縦の破線）。日付で書くと凡例に「現在（10/5）」と自動表示。
- **凡例**: 既定で図の下に1行（使われた variant ＋ 節目 ＋ 現在線だけ）。`legend: false` で非表示、`legend_labels`（キーは variant 名・`milestone`・`today`）で文言を変更。収まらなければ文字を縮めてから自動で折り返す（`legend-wrapped` note）。`note` は凡例行の右端に出る注記。
- **行の高さ**: 図の高さ（lead があれば `chart.y/h`、無ければ `chart.y_no_lead/h_no_lead` で上に詰める）から自動で等分し、`min_row_h`〜`max_row_h`（既定 28〜64）に収める。矢羽根の高さの上限 `bar_max_h` は 34。**行が少ないとき**: 行 1〜3 本など、図が枠の 6 割（`thin_trigger`）に満たないとき、行の高さ・矢羽根の太さを最大 2.2 倍（図が枠の約 72% になる倍率）、文字を最大 1.5 倍（行見出し 24px・矢羽根の文字 22px まで）にする。**4 行以上**でも、図が枠の 9 割（`fill_trigger`）に満たなければ、行の高さを 1.3 倍まで配って枠の 95% まで使い、文字は 1.2 倍まで（行見出しの折り返しが悪くなるときは行の高さだけ）。`style.chart` に行の高さ・文字の大きさ（`max_row_h` `label_size` `bar_size` など）を 1 つでも書いたスライドは動かさない。`autofit: false` でも整えない。合成・split のブロックの schedule も、ブロックの高さに対して同じ拡大をする（トークン一覧は [autofit.md](autofit.md) の「中身が少ないときの自動調整」）。行が多く `min_row_h` を下回ると `too-dense` 警告（目安 14 行以下）。図が枠の下端を越えるときは、ビルドが `chart-overflow` 警告（「図が枠の下端を約Npx はみ出します → 行を N 行以下にして、スライドを分ける / lead を削る / min_row_h を下げる」）を出す（文字は縮めない。[autofit.md](autofit.md)）。行が低いと行見出しの文字も比例して縮む。
- **位置**: 図の既定の位置は共通の余白（x 72・幅 1136。タイトルと同じ左右の端）。行見出しの幅 232、グループ帯の幅 36・文字 14。2.0.0 は x 48・幅 1184・行見出しの幅 250・グループ帯の幅 34・文字 13・行の高さの上限 54・矢羽根の高さの上限 30 だった。**`style.chart` に `x` と `w` の片方だけを書くと、もう片方は既定値のままなので右端がスライドの外へ出ることがあり、そのときビルドが警告する**（`x` と `w` を両方書く）。
- **PPTX のグループ見出し**（縦の「節目」「開発」）は、HTML と同じく和字を正立で 1 字ずつ縦に積む（以前は横倒しで小さく見えた）。英数字だけ・枠に入らない長さのときは従来の横倒し。
- **既知の制約**: 1 か月の矢羽根の長いラベルは、右にも左にも空きが足りなければ 10px 台のまま中に入る（ラベルを短くするか、期間を広げる）。グループごとの棒の色・図の下の説明文は無い（`variant` と `note` で代える）。節目ラベルどうしが近いと `milestone-crowded`（段をずらす）。
- **主な `style.chart` トークン**: `label_w`（行見出し欄の幅、既定 232）/ `group_w`（既定 36）/ `period_h` / `col_h` / `min_row_h` / `max_row_h` / `bar_hr`（行高に対する矢羽根の高さ比）/ `bar_max_h`（既定 34）/ `bar_head`（矢頭の深さ上限 px）/ `bar_gap` / `<variant>_fill` / `<variant>_border` / `<variant>_color` / `period_fill` / `col_fill` / `group_fill` / `row_alt_fill` / `grid_color` / `milestone_fill` / `today_color` / 各 `*_size`。

診断は `check_diagram.py` で確認できる（スキーマ的な誤りはビルドエラー、文字あふれ・重なりは警告）。

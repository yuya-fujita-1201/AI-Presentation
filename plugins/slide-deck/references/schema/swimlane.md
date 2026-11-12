# `swimlane` — スイムレーン業務フロー

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。配線・ラベル・密度の診断コード（`check_diagram.py`）は [diagram.md](diagram.md) の「図解タイプの診断」。同じ配線エンジンを使う `architecture` / `dataflow` / `lifecycle` / `sequence` は [diagram.md](diagram.md)。

```json
{ "type": "swimlane", "title": "見出し", "lead": "（任意）",
  "cols": 6,
  "phases": ["", "作成", "精緻化", "レビュー", "判定", "次工程"],
  "lanes": [
    { "group": "Japan", "name": "開発T(Lead)" },
    { "group": "Japan", "name": "開発T(Member)" },
    { "name": "AI（Claude Code等）" }
  ],
  "nodes": [
    { "id": "start", "lane": 0, "col": 0, "shape": "terminal", "text": "開始" },
    { "id": "t1", "lane": 1, "col": 1, "shape": "task", "text": "ドラフト作成", "loop": true },
    { "id": "d1", "lane": 1, "col": 2, "shape": "decision", "text": "指摘あり" },
    { "id": "io1", "lane": 2, "col": 1, "shape": "io", "input": ["論点一覧"], "output": ["検討資料"] },
    { "id": "end", "lane": 1, "col": 3, "shape": "terminal", "text": "完了" }
  ],
  "edges": [
    { "from": "start", "to": "t1" },
    { "from": "t1", "to": "d1" },
    { "from": "d1", "to": "end", "label": "Y" }
  ] }
```
領域: `title`, `rule`, `lead`, `flow`, `footer_l/r`。業務フロー・運用フローを **image に頼らずネイティブ描画**する（座標を自動計算するのでズレない）。ノード・レーン帯・矢印はテーマの `primary` / `surface` / `on_primary_soft` / `highlight_fill` / `border` に固定される（系列ごとの色分けはできない。多系列を色分けしたい場合は `image` で図を用意する）。

- **レーン（横帯）＝役割**。`lanes[]` は上から順の行（1個以上必須）。`group`（Lv1）が同じ連続レーンは左端に縦帯でまとめられる。`group` を省けば **Lv1 なしのフラットなレーン** になる（Lv1 のみ・Lv1+Lv2 どちらも可）。
- **配置はグリッド**。各ノードに `lane`（行 index）と `col`（工程＝列 index、0始まり）を指定。**`id` はノード間で重複不可**（重複するとビルドエラー）。列数は `cols`（省略時はノードの最大 col+1。ノードの `col` が `cols` 以上の場合は `cols` を自動拡張して警告）。`phases[]` を書くと上部に工程ヘッダ帯が出る（列と対応、空文字で省略）。
- **ノード形状 `shape`**: `task`（角丸四角・`loop:true` で反復記号／`variant` で `onpf`＝オンラインPF・`onother`＝PF以外・`offline`＝オフラインを色分け）/ `system`（システム・サービス）/ `decision`（ひし形・分岐）/ `terminal`（楕円・前/次ページ等のラベル付き連結）/ `marker`（小さな丸・`kind` で `start`/`end`/`mid`）/ `connector`（ペンタゴン・分岐の遷移先）/ `mail`（メール配信）/ `io`（`input`/`output` の成果物リスト。幅に入らない項目は **2 行に折って 10px 以上を守る**（箱の高さに入るときだけ。漢字だけの語は 1 行目を長く「原因分析／報告」、カタカナ語は前後を近づけ、長音符・小さい仮名・句読点を行頭にしない。HTML と PPTX で同じ折り位置）。入らないときは 1 行のまま 8px まで縮み、列が多い図では 10px に入らない項目が `minfont` の警告になる。凡例の成果物の記号も 11px で描く）。
- **エッジ `edges[]`**: `{ from, to, label, style }`。`from`/`to` は存在する `id` を指定する（未知の `id` はビルドエラー）。ノード id 同士を結ぶと、レーンをまたぐ L 字・Z 字の直交矢印を**自動ルーティング**する。`label` は Y/N などの分岐ラベル、`style: "dashed"` で破線（システム操作）になる（既定は実線＝作業の流れ）。`arrow: "both"` の edge は `label_back` で逆向きの名前も出せる（[diagram.md](diagram.md) の「双方向の矢印」）。古い `label_at` の座標がノードの文字に重なるときは無視して自動で置く（警告つき。座標は消す）。
- **差し戻し・やり直しの書き方**: 検品 NG で前の工程に戻すような往復は、`n3→n4` と `n4→n3` の 2 本にせず、**1 本の `arrow: "both"` に `label`（行き）と `label_back`（戻り）を付ける**。2 本に分けると隣り合う矢印が重なり `label-collision` が出る。ラベルは 2〜4 字に短く（長いと 1 本でも重なる）。分岐ラベル（Y / N）は別の線に付ける。
  ```json
  { "from": "n3", "to": "n4", "arrow": "both", "label": "検品", "label_back": "戻す" },
  { "from": "n4", "to": "n5", "label": "合う" }
  ```
- **凡例 `legend`**: **既定 `true`**。true のとき、そのスイムレーンの**直前に凡例専用ページ（`swimlane_legend`）を自動挿入**する（業務フロー標準記号の一覧：作業3種・システム・分岐・成果物・開始/終了/途中・前/次ページ・遷移先・メール・実線/破線の15種）。**この自動挿入は合計ページ数に影響する（+1枚）**。指定枚数を厳守したい場合はあらかじめ考慮するか、`"legend": false` で凡例ページを省略する。`legend_title` で凡例ページのタイトル、`legend_items` で凡例内容をカスタムできる。
  - `legend_items` の正しい形は **4要素配列の配列**: `[[shape, variant_or_kind, label, description], ...]`（例: `[["task", "onpf", "オンラインPF作業", "..."], ["decision", "", "分岐", "..."]]`）。辞書形式 `{"shape": "...", "variant": "...", "label": "...", "desc": "..."}`（または `kind`/`label`/`desc`）も受理されるが、**要素数の合わない配列やこれ以外の形は文字化けした凡例の原因になる**ので必ず4要素配列（または上記の辞書キー）で書く。
- 色・線幅・ノードサイズは `flow` の各トークンで調整可（`task_onpf_fill` / `task_offline_fill` / `system_fill` / `marker_start` / `connector_fill` / `decision_fill` / `edge_color` / `lane_border`（レーン区切り線の色、既定 `border` トークン）など）。
- **v0.3.0 の変更点**（`architecture` 等の追加にともなう配線エンジン共通化）: 配線が[diagram.md](diagram.md) の「図解タイプ共通」と同じ共通ルーター（`tools/diagram_engine.py`）に置き換わった。見た目はほぼ従来どおりだが、線が途中のノードを横切らなくなり、同じ辺から出る複数の線・同じ回廊を通る線は自動で等間隔にずれ、ラベルは背景ピル付きで重なりにくくなる。
  - `edges[].variant`（`default` / `emphasis` / `security` / `dashed`）と `edges[].arrow`（`end` / `both` / `none`）が使える。従来の `style: "dashed"` は引き続き受理する（両方書くと `style-conflict` の警告になり `variant` を優先する）。
  - ノードの `text` の別名として `label` も受理する。
  - `decision`（ひし形）は箱に内接するサイズで描かれるようになり、HTML と PPTX の大きさが一致する（従来は HTML だけ大きく見えていた）。
  - 反復記号 `loop: true` は右上の丸バッジ（円弧矢印）に変わった。
  - 追加された検証（warning）: ノードの `variant` が `onpf` / `onother` / `offline` 以外（`architecture` 系タイプの `emphasis` 等は swimlane では使えない）、`shape` が未知、`text`/`label` が無い、`edges[].variant` / `edges[].style` の未知値。
  - 凡例ページ（`legend` bool による自動挿入）と凡例記号15種、`groups` を持たない点は変わらない。

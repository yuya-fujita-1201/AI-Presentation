# 図解タイプ（architecture / dataflow / lifecycle / sequence / diagram_legend）と診断

共通事項は索引 [`../deck-schema.md`](../deck-schema.md)。`swimlane` は [swimlane.md](swimlane.md)、`schedule` は [schedule.md](schedule.md)。どのタイプを選ぶか・作図の規約・修理ループは [`../diagram-guide.md`](../diagram-guide.md)。

## 図解タイプ共通（`architecture` / `dataflow` / `lifecycle`）

この3タイプは同じ描画エンジン（`tools/diagram_engine.py`）を共有し、ノード・エッジの語彙とトークンも共通。タイプごとの違いは行・列の意味づけだけで、詳細は次項以降の各タイプ節を見る。ノード・エッジの見た目トークン（`node_*` / `edge_*` / `label_*` など）は `sequence` の参加者・メッセージにも使われる（自動配線・groups・凡例は grid 系3タイプ専用）。

領域名は共通で `diagram`（既定 `x=72 y=190 w=1136 h=468`。`style.diagram.*` または `meta.layout_overrides.<type>.diagram.*` で調整する）。図全体を `rows`×`cols` のセルに分け、ノードはセル中央に置かれる（`cols`/`rows` は省略可。ノードの最大 `col`/`row`+1、または見出し数から自動算出）。

**ノード `nodes[]`**（lifecycle は `states[]` も同じ形）

| フィールド | 必須 | 説明 |
|---|---|---|
| `id` | ✅ | 一意な id（英数字推奨）。重複は `duplicate-id` エラー |
| `label`（別名 `text`） | 推奨 | 表示名（無いと `missing-label` 警告） |
| `sublabel` | | 小さな補足（1行） |
| `tag` | | 右上の小ピル（例: `"JWT"`） |
| `type` | | `frontend` / `backend` / `database` / `cloud` / `security` / `messagebus` / `external` / `generic`（既定）。**色ではなくアイコンの形**でコンポーネントの役割を表す |
| `variant` | | `default`（既定）/ `emphasis` / `security` / `dashed` / `muted`。**色はこちらが担う** |
| `row` / `col` | | 0始まりの整数。同じ (row, col) の重複は `cell-collision` エラー、負値や非整数は `invalid-position` エラー。**上限は 40**（`row: 0〜39`、`stage` / `lane` の別名とスライドの `cols` / `rows` も同じ。超えるとビルドエラー「列は 40 列までです → col は 0 始まりで、飛ばさずに詰めて指定する」） |

**エッジ `edges[]`**

| フィールド | 必須 | 説明 |
|---|---|---|
| `from` / `to` | ✅ | 既知の `id`（未知は `unknown-endpoint` エラー） |
| `label` | | ラベル文字列 |
| `variant` | | `default` / `emphasis` / `security` / `dashed`。旧 swimlane 互換の `style: "dashed"` も受理（`variant` と両方書くと `style-conflict` 警告、`variant` を優先） |
| `arrow` | | `end`（既定）/ `both` / `none` |
| `label_back` | | `arrow: "both"` の逆向き（to → from）のやり取りの名前。`label` が from → to。architecture / dataflow / lifecycle / swimlane の edges で使える（下の「双方向の矢印」） |
| `from_side` / `to_side` | | `left` / `right` / `top` / `bottom`。他ノードを避けられない場合は無視され `side-ignored` 警告 |
| `via` | | `[[x, y], ...]`（キャンバス絶対 px の経由点）。**最初から書かず、`check_diagram.py` が提示してから 1 つ加える** |
| `label_at` | | `[x, y]`（ラベル中心の固定座標）。座標がノードの文字に重なるときは無視して自動で置く（`label-at-ignored` の警告） |
| `route` | | `auto`（既定）/ `straight` |
| `classification` | | `dataflow` 用。ラベルの2行目に小さく表示（例: 「個人データ」） |

**別名**: 列見出し帯は `col_headers`（正式）＝ `stages`（dataflow で自然）＝ `phases`（swimlane 流）のどれでも同じ。行見出しは `lanes: [{"name": "..."}]`（正式。`label` も可）＝ `row_headers`。lifecycle は `states`=`nodes`、`transitions`=`edges`、ノードの `lane`=`row`。dataflow はノードの `stage`=`col`、`flows`=`edges`。

**グループ（境界） `groups[]`**: `{ "label", "kind": "region" | "security" | "zone" | "generic", "nodes": [id, ...] }`。メンバーの外接セル範囲を囲む（`region`=破線、`security`=primary破線、`zone`=surface塗り）。範囲内に非メンバーが混ざると `group-leak` 警告（**本当の所有・信頼・配備の境界だけ**に使い、単なる見た目のグルーピングには使わない）。swimlane の `lanes[].group`（縦帯グループ）とは別概念で、swimlane には `groups` は無い。

**凡例 `legend`**: `"auto"`（既定。`type` が2種以上あると図の下に1行で表示）/ `true` / `false`。**ページを追加しない**（swimlane の `legend` bool＝凡例ページの自動挿入とは意味が違う）。type の表示名既定は「フロント／バックエンド／DB／クラウド／セキュリティ／メッセージ基盤／外部」（`style.diagram.type_labels` で変更可）。

**自動配線**: 列・行のガターとノード中心線を格子にした最短の直交経路を探索し、途中のノードを横切らないルートを優先する（横切ってしまう場合は `edge-through-node` の診断。ビルド自体は止まらず警告として報告される）。同じ辺から出入りする複数の線・同じ回廊を通る線は自動で等間隔にずらす。ラベルは最長セグメントの脇に背景ピル付きで置き、ノード・他ラベルと衝突すれば別候補へ、それでも衝突すれば `label-collision` 警告（`label_at` の候補座標が提示される）。`from == to` の自己ループは右上の小さなコの字で描く。

**双方向の矢印（`label_back`）**: `arrow: "both"` の edge に `label_back` を書くと、行きと戻りに別の名前を出せる。

```json
{"from": "ec", "to": "sap", "arrow": "both", "label": "受注確定", "label_back": "在庫引当"}
```

逆向きのラベルは、順方向のラベルを全部置いたあと、同じ線の**反対側**（水平の線なら下、垂直の線なら左）を優先して置く。ほかの要素と重なるときは次の候補へ（ふつうのラベルと同じ規則・同じ警告。逆向きは「エッジ A→B の逆向きのラベル「…」が他の要素と重なります」）。`arrow` が `both` でないのに書くと `label-back-ignored`（「edges[N] の label_back は arrow が both のときだけ表示されます → arrow を "both" にする / label_back を消す」）。

**古い `label_at` の扱い**: ノードを動かしたあとに古い `label_at` が残り、座標がノードの文字（ひし形は中央 60%）に重なるときは、座標を無視して自動配置に戻し、`label-at-ignored` の警告を出す（「エッジ A→B の label_at [x, y] は…重なるため、無視して自動で置きました → label_at を消す / ノードに重ならない座標を書く」）。ノードに重ならない座標は従来どおり採用する。直し方は、座標を消して自動配置に任せる。

**主な `style.diagram` トークン**（既定値は `templates/layouts/default.json` 参照）: `node_wr` / `node_hr` / `node_max_w` / `node_max_h` / `node_radius` / `node_pad` / `node_size` / `sub_size` / `tag_size` / `node_fill` / `node_border` / `node_border_w` / `node_color` / `sub_color` / `emphasis_fill` / `emphasis_border` / `security_border` / `dashed_border` / `muted_color` / `tag_fill` / `tag_color` / `icon_size` / `icon_color` / `group_border` / `group_color` / `group_radius` / `security_group_border` / `zone_fill` / `header_h` / `header_fill` / `header_color` / `row_label_w` / `row_fill` / `row_color` / `edge_color` / `edge_w` / `edge_emphasis_color` / `edge_security_color` / `edge_dashed_color` / `edge_return_color` / `label_size` / `label_color` / `label_fill` / `legend_h` / `type_labels`。dataflow 追加: `class_size` / `class_color`。lifecycle 追加: `start_` / `active_` / `waiting_` / `decision_` / `success_` / `failure_` / `neutral_` / `external_` の `_fill` / `_border`、`success_color` / `step_color` / `step_size`。

## `architecture` — システム構成図
```json
{ "type": "architecture", "eyebrow": "SYSTEM", "title": "システム構成",
  "nodes": [
    {"id":"web","type":"frontend","label":"Web","sublabel":"React","row":0,"col":0},
    {"id":"api","type":"backend","label":"API","sublabel":"FastAPI","row":0,"col":1,"variant":"emphasis"},
    {"id":"db","type":"database","label":"PostgreSQL","row":0,"col":2},
    {"id":"auth","type":"security","label":"認証","sublabel":"OAuth","row":1,"col":1}
  ],
  "groups": [{"label":"VPC","kind":"region","nodes":["api","db","auth"]}],
  "edges": [
    {"from":"web","to":"api","label":"HTTPS","variant":"emphasis"},
    {"from":"api","to":"db","label":"SQL"},
    {"from":"auth","to":"api","label":"JWT検証","variant":"security"}
  ] }
```
領域・フィールド・別名・groups・凡例・配線・`style.diagram` トークンは上記「図解タイプ共通」を参照。

目安: ノード12個以下、列6以下（超えると `too-dense` 警告で自動拡張はしない）。

注意: コンポーネントの役割は `type`（アイコンの形）で表し、強調したいノード／境界越えの通信は `variant`（ノードは `emphasis`、エッジは `security` 等）で表す。主経路が1本の左→右（または上→下）になるよう `row`/`col` を揃えると線が交差しにくい。

**AWS 風タイルアイコン**: `style.diagram.icon_style` を `"aws"` にすると、`type` を **カテゴリ色の角丸タイル＋白いグリフ**（AWS の構成図アイコン風）で描く（既定は `"line"` の線画グリフ）。実物の AWS アイコン画像は使わず自作しているので、テーマ・PPTX・HTML すべてで同じに出る。タイル色は `icon_tile_<type>` トークンで上書きでき（既定: frontend=マゼンタ / backend=オレンジ / database=ブルー / cloud=ティール / security=レッド / messagebus=ピンク / external=スレート / generic=グレー）、タイルの大きさは `icon_tile_size`（既定 30）。`architecture` / `dataflow` / `sequence` で有効（`lifecycle` は kind の形で表すのでタイルにはしない）。`legend_page` の凡例はこの設定を自動で引き継ぐので、図と凡例で見た目が揃う。

## `dataflow` — データフロー
```json
{ "type": "dataflow", "eyebrow": "DATA", "title": "データフロー",
  "stages": ["収集", "処理", "保存", "活用"],
  "nodes": [
    {"id":"app","type":"frontend","label":"アプリ","col":0,"row":0},
    {"id":"collector","type":"cloud","label":"収集API","col":1,"row":0},
    {"id":"stream","type":"messagebus","label":"Kafka","col":2,"row":0},
    {"id":"dwh","type":"database","label":"DWH","col":3,"row":0}
  ],
  "edges": [
    {"from":"app","to":"collector","label":"送信"},
    {"from":"collector","to":"stream","label":"正規化"},
    {"from":"stream","to":"dwh","label":"格納","classification":"匿名化済み"}
  ] }
```
領域・フィールド・別名・凡例・配線・`style.diagram` トークンは上記「図解タイプ共通」を参照。`stages` は列見出し（`col_headers` の別名）で、工程を上部の帯に表示する。

目安: 列（`stages` の数、または最大 `col`+1）6以下、ノード12個以下。

注意: `edges[].classification` はラベル下に小さく表示され、データの区分（個人データ・匿名化済み等）を添えるのに使う。`row` は同じ工程内で並行する経路の書き分けに使う（lifecycle の `lane` と役割が近い）。

## `lifecycle` — ライフサイクル / 状態遷移
```json
{ "type": "lifecycle", "eyebrow": "STATE", "title": "承認フローの状態遷移",
  "lanes": [{"name":"主経路"},{"name":"差し戻し"}],
  "states": [
    {"id":"draft","kind":"start","label":"下書き","lane":0,"col":0},
    {"id":"review","kind":"decision","label":"レビュー","lane":0,"col":1},
    {"id":"done","kind":"success","label":"承認済み","lane":0,"col":2},
    {"id":"reject","kind":"failure","label":"差し戻し","lane":1,"col":1}
  ],
  "transitions": [
    {"from":"draft","to":"review"},
    {"from":"review","to":"done","label":"OK","variant":"emphasis"},
    {"from":"review","to":"reject","label":"NG"},
    {"from":"reject","to":"draft","label":"再提出","variant":"dashed"}
  ] }
```
`states`（`nodes` も受理）と `transitions`（`edges` も受理）を使う。`lane` は `row` の別名で、`lanes[]`（1個以上）が縦の帯になる（Archify のように main/terminal の3帯固定ではなく、任意の本数を書ける）。状態の性質は `kind` で描き分ける:

| `kind` | 見た目 |
|---|---|
| `start` | ピル形。accent 枠＋highlight_fill 塗り |
| `active`（既定） | 通常の角丸カード。primary 枠 |
| `waiting` | 破線・muted＋砂時計アイコン |
| `decision` | ひし形（accent 枠・highlight_fill 塗り） |
| `success` | accent 塗り・白文字＋チェック |
| `failure` | 太い破線＋×印 |
| `neutral` | surface 塗り |
| `external` | 破線・muted |

`step`（`"01"` のような番号バッジ）も指定できる。番号は形ごとに輪郭に重ならない位置に置く（HTML と PPTX で同じ）: 四角と角が無い（sharp）ピルは左上の内側、角丸のピルは曲線の内側へ右に寄せる、ひし形は中に置けないので外接矩形の左上の角（輪郭の外）。色は塗りの上で読める濃さに自動で整う（完了ノードの番号も見える）。`meta.shape: "sharp"`（ピルの角が 0）では、start ノードを process と区別するため枠線を太くする（`diagram.start_border_w_sharp` 3.5）。

目安: 状態12個以下。レーンは意味のある単位で3〜4本程度（本数の上限は無いが増やすほど1本あたりの文字が小さくなる）。

注意: 分岐は `decision`、成功/失敗の終端は `success`/`failure` を使い分けると状態の性質が一目で伝わる。

## `sequence` — シーケンス図
```json
{ "type": "sequence", "eyebrow": "FLOW", "title": "ログイン処理のやり取り",
  "participants": [
    {"id":"user","type":"external","label":"利用者"},
    {"id":"web","type":"frontend","label":"Web"},
    {"id":"api","type":"backend","label":"API"},
    {"id":"db","type":"database","label":"DB"}
  ],
  "messages": [
    {"from":"user","to":"web","label":"ログイン"},
    {"from":"web","to":"api","label":"POST /login","variant":"emphasis"},
    {"from":"api","to":"db","label":"SELECT user"},
    {"from":"db","to":"api","label":"rows","variant":"return"},
    {"from":"api","to":"web","label":"200 OK","variant":"return"}
  ] }
```
領域: `diagram`（他3タイプと共通）。上部に参加者カードを横並びに置き、下へライフライン（破線）を伸ばす。

| フィールド | 説明 |
|---|---|
| `participants[].id/label/sublabel/type/variant` | ノードと同じ語彙（`type` のアイコン、`variant` の `emphasis`/`security`/`dashed`/`muted` も使える） |
| `messages[].from/to/label` | 配列の**順に上から等間隔**に描く（`label` が無いと `missing-label` 警告） |
| `messages[].variant` | `default` / `emphasis` / `security` / `dashed` / `return`（戻りは破線の開いた矢印） |
| `activations[]`（任意） | `{ "participant", "from", "to" }`。`from`/`to` は `messages` の index（0始まり）または `id`。ライフライン上の帯 |
| `segments[]`（任意） | `{ "from", "to", "label" }`（同じく index/id）。区間を薄い破線枠で囲み左上にラベル。見出しの札は生存線より上に描かれ（生存線が文字を貫かない）、枠の下端は詰めて隣の枠との間に隙間を残す |

`from == to` は自己メッセージ（右側に小さなコの字）として描く。

目安: 参加者7人以下、メッセージ12本以下（超えると `too-dense` 警告）。ラベルが矢印の長さより長いと `label-collision` 警告。

注意: 参加者カード・メッセージの矢印は「図解タイプ共通」節と同じノード/エッジのトークン・語彙で着色されるが、自動配線・groups・凡例（横切り回避を含む）は grid 系3タイプ専用でここには無い（メッセージは常に横一直線）。

## `diagram_legend` — 図解タイプの凡例ページ
```json
{ "type": "diagram_legend", "eyebrow": "SYSTEM — 凡例", "title": "システム構成図の記号",
  "lead": "アイコンは役割、色は強調、矢印の線種は接続の性質を表す。",
  "items": [
    [{"icon": "backend"},     "バックエンド", "API・アプリケーションサーバ"],
    [{"node": "emphasis"},    "主要ノード",   "強調色＝主経路の中心"],
    [{"kind": "decision"},    "分岐",         "条件による分岐（ひし形）"],
    [{"edge": "default"},     "実線矢印",     "同期の呼び出し・主なデータの流れ"],
    [{"edge": "dashed"},      "破線矢印",     "非同期・任意・補助的な経路"],
    [{"edge": "return"},      "戻り矢印",     "開いた破線矢印＝応答・戻り値"]
  ] }
```
`architecture` / `dataflow` / `lifecycle` / `sequence` の記号を、swimlane の凡例ページと同じ「記号＋名前＋説明」の2カラム表で見せる専用タイプ。**記号は実図と同じ描画関数（`_node_visual` / `_edge_visual`）で描く**ので凡例と本体の見た目が必ず一致する。

**自動挿入（推奨）**: 図解スライド（`architecture` / `dataflow` / `lifecycle` / `sequence`）に **`"legend_page": true`** を付けると、そのスライドの直前に `diagram_legend` ページが自動挿入される（swimlane の `legend` と同じ仕組み。ただし**既定はオフ**で、付けたスライドにだけ着く）。`items` は**そのスライドで実際に使われている** `type` / `variant` / `kind` / エッジの種類だけから自動生成されるので、図に出てこない記号は載らない。オプション: `legend_title`（凡例の見出し）/ `legend_eyebrow`（既定はスライドの `eyebrow` に「 — 凡例」を付けたもの）/ `legend_lead`（説明文）/ `legend_items`（自動生成を使わず内容を明示。形式は下記）。`icon_style:"aws"` などアイコン関連の `style.diagram` トークンは凡例に自動で引き継がれる。

`diagram_legend` を直接スライドとして書けば、任意の位置・内容の凡例ページも作れる。その場合は次の `items` を指定する。

`items` は `[サンプル, ラベル, 説明]` の配列。**サンプルはキー1つの辞書**で、種類は次の4つ:

| サンプル | 描くもの |
|---|---|
| `{"icon": "<type>"}` | ノードカード＋type アイコン（`frontend` / `backend` / `database` / `cloud` / `security` / `messagebus` / `external`） |
| `{"node": "<variant>"}` | variant の色見本ボックス（`emphasis` / `security` / `dashed` / `muted`） |
| `{"kind": "<kind>"}` | lifecycle の状態記号（`start` / `active` / `waiting` / `decision` / `success` / `failure` / `neutral` / `external`。形とグリフ付き） |
| `{"edge": "<variant>"}` | 矢印1本（`default`＝実線 / `emphasis`＝太線 / `security`＝鎖線 / `dashed`＝破線 / `return`＝開いた破線の戻り矢印） |

領域は `area`（2カラムのグリッド。`cols` / `col_gap` / `row_h` / `sym_w` / `label_size` / `desc_size`）と `diagram`（記号の色トークン。`architecture` と同じ語彙＋lifecycle の kind トークン）。色を変えるときは `meta.theme` の切替か `style.diagram.*` で行う。

## 図解タイプの診断（`check_diagram.py`）

`architecture` / `dataflow` / `lifecycle` / `sequence` / `swimlane` の配線・ラベル・密度は、専用 CLI で deck.json だけを読んでビルドせずに診断できる（Playwright / python-pptx 不要）:

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir>                 # テキスト報告
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir> --json out.json # JSON 出力（code / subject / evidence / fixes）
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir> --strict        # warning も不合格にする
python "${CLAUDE_PLUGIN_ROOT}/tools/check_diagram.py" <deck_dir> --slides 3 7    # 対象スライド番号を絞る（プレビュー PNG・check_layout.py と同じ番号。凡例ページの自動挿入込み、1始まり）
```

**exit 1 になるのは診断に error が1件でもあるとき**（`--strict` を付けると warning も含める）。ここが `build_deck.py` と異なる点として、`edge-through-node` や `node-text-overflow` は診断としては error 相当でも、`build_deck.py` の通常ビルドは（見た目が崩れているだけで座標計算自体は破綻していないため）止めずに警告として報告する。**「`check_diagram.py` は error と言うのにビルドは通る」のはこの理由による意図した挙動**で、矢印の向きやラベルの意味の正しさまでは診断できないので、`check_diagram.py` を通したうえで `preview_deck.py` の目視確認も行う。

出力のスライド番号は **PNG の番号**（`preview_deck.py` / `check_layout.py` と同じ。凡例ページの自動挿入・agenda の分割込み）。deck.json の何枚目かは「deck.json N枚目」と併記される（JSON は `index` / `slide` が PNG の番号、`src` が deck.json の番号）。

修理ループの進め方は [diagram-guide.md](../diagram-guide.md) の「修理ループ」を参照。

| code | level | 内容 | fixes の例 |
|---|---|---|---|
| `duplicate-id` | error | ノード/状態/メッセージの `id` が重複 | id を一意にする |
| `missing-id` | error | ノードに `id` が無い | 一意な id（英数字）を付ける |
| `empty` | error | `nodes`/`states`/`lanes` が空 | 1個以上書く |
| `cell-collision` | error | 同じ `(row, col)` に2ノード | どちらかの `row`/`col` を変える |
| `invalid-position` | error | `row`/`col` が0以上の整数でない、`lane` が `lanes` の範囲外 | 整数にする／`lanes` に行を追加する |
| `unknown-endpoint` | error（`edges`/`groups`/`messages` の参照）／warning（`activations`/`segments`） | `from`/`to`/`nodes` が存在しない `id` を指す | 存在する `id` を指定する |
| `invalid-group` | error | `groups[]` の要素がオブジェクトでない | オブジェクトにする |
| `edge-through-node` | error（`check_diagram.py`）／ビルドは warning 扱い | エッジが無関係なノードを横切る | `via` を指定する／`row`/`col` を変える／`from_side`/`to_side` を指定する |
| `node-text-overflow` | error または warning（あふれ量による。`check_diagram.py`）／ビルドは warning 扱い | `label`/`sublabel` が箱に収まらない | `label` を短くする／`cols`/`rows` を減らす／`node_size` を下げる |
| `label-collision` | warning | ラベルが他要素と重なる（`label_back` の逆向きのラベルも同じ） | 往復する 2 本は 1 本の `arrow: "both"` + `label_back` にまとめる／`label_at` を指定する／`row`/`col` を離す／文言を短くする |
| `label-at-ignored` | warning | `label_at` の座標がノードの文字に重なるため無視して自動配置した | `label_at` を消す／ノードに重ならない座標を書く |
| `label-back-ignored` | warning | `label_back` があるが `arrow` が `both` でない（表示されない） | `arrow` を `both` にする／`label_back` を消す |
| `crossings` | warning（2箇所以上）／info（1箇所） | エッジ同士が交差する | `row`/`col` を入れ替える／戻りの線を `from_side`/`to_side` で外側に回す |
| `edge-overlap` | warning | 無関係なエッジが同じ線上で重なる | 片方に `via` を指定する／`row`/`col` をずらす |
| `too-dense` | warning | ノード>12／列>6／メッセージ>12／参加者>7 | 要素を減らす／2枚に分ける |
| `group-leak` | warning | `groups` の範囲内に非メンバーが混入 | メンバーの `row`/`col` を隣接させる／範囲外へ動かす |
| `out-of-grid` | warning | `cols`/`rows` を超える `row`/`col` があり自動拡張された | `cols`/`rows` を明示する |
| `short-segment` | info | 8px未満の短いセグメント | `row`/`col` の間隔を広げる／`via` で単純化する |
| `unknown-key` | warning | 未知のフィールド名（typo の可能性。候補が提示される） | 該当タイプのファイル（索引の「タイプ一覧表」から開く `schema/*.md`）のキー名に直す |
| `unknown-type` | warning | ノードの `type` が未対応 | 近い `type` に直す（不明なら省略して `generic`） |
| `unknown-variant` | warning | `variant` が未対応 | `default`/`emphasis`/`security`/`dashed`/`muted` のいずれかにする |
| `unknown-kind` | warning | lifecycle の `kind` が未対応 | 近い `kind` に直す |
| `style-conflict` | warning | `edges` の `style` と `variant` が矛盾 | `variant` だけを書く |
| `side-ignored` | warning | 指定した `from_side`/`to_side` では他ノードを避けられず無視された | 指定を外す／別の辺にする |
| `invalid-side` | warning | `from_side`/`to_side` の値が不正 | `left`/`right`/`top`/`bottom` のいずれかにする |
| `invalid-via` | warning | `via` の形式が不正 | `[[x, y], ...]` の形にする |
| `missing-label` | warning | ノード/メッセージに `label` が無い | 表示名・やり取りの内容を `label` に書く |
| `empty-group` | warning | `groups[].nodes` が空 | ノード id を1個以上書く |

# 図解タイプ作図ガイド（`architecture` / `dataflow` / `lifecycle` / `sequence`）

各タイプの JSON フィールド・トークンの一覧は `references/deck-schema.md`（「図解タイプ共通」節と各タイプ節）を見る。このガイドは**どのタイプを選ぶか**と**どう作図するか**（Archify 由来の規約・診断への対処・修理ループの回し方）専用。内容そのものの質（構成・タイトルの付け方）は `references/content-guide.md` を参照。

## 1. 図解タイプの選び方

文章の箇条書きに逃げず、伝えたいものの「主役」で選ぶ。

| 伝えたいこと（主役） | 使うタイプ |
|---|---|
| システムの構成・コンポーネント間の連携（モノが主役） | `architecture` |
| データが生成されてから使われるまでの経路（データが主役） | `dataflow` |
| 状態・ステータスの遷移（開始→進行→完了、差し戻しループを含む） | `lifecycle` |
| API 呼び出し・メッセージのやり取りの時系列（時間軸が主役） | `sequence` |
| 誰が何をするかの業務フロー（役割・部署が主役） | `swimlane` |
| 部署をまたがない単純な一直線の手順 | `steps` |

### `swimlane` / `lifecycle` / `steps` の使い分け

3つとも「流れ」を描く点で似ているため混同しやすい。行（レーン）に何を置くかで選ぶ:

| タイプ | 行（レーン）の意味 | 向いている内容 |
|---|---|---|
| `swimlane` | **誰が**（担当者・部署・システム） | 承認フロー、部署をまたぐ業務プロセス |
| `lifecycle` | 状態のグルーピング（任意。無くてもよい） | 1つの対象（リクエスト・チケット等）が辿る状態遷移 |
| `steps` | レーン無し。単純な連番 | 部署をまたがない直線的な手順（研究開発→社会実装 等） |

迷ったら「レーンの見出しに部署・担当者の名前が入るか」で判定する。入るなら `swimlane`、入らず「状態の名前」（受付・処理中・完了 等）になるなら `lifecycle`、レーン自体が要らないなら `steps`。

`architecture` と `dataflow` も紛らわしい: `architecture` は**時点の構成**（何がどこにあり何につながっているか）、`dataflow` は**時間経過に伴う工程**（`stages` が左から右に進む）を表す。同じ内容でも「今の構成を見せたい」なら `architecture`、「データがどう変換されて流れるか見せたい」なら `dataflow` を選ぶ。

## 2. Archify 由来の作図規約

このプラグインの図解エンジンは Archify（1章参照）の作図規約を踏襲している。AI（この文書を読んでいるあなた）が deck.json を書くときに守ると、診断の警告が出にくく見やすい図になる。

- **主経路は1本**の左→右（または上→下）になるよう `row`/`col` を揃える。行き来する矢印が多いと交差だらけになる。
- **ノードは12個以下、列は6以下**。超えそうなら補助的なノードを `sublabel` にまとめるか、全体像＋詳細の2枚に分ける。
- **意味のあるラベルは削らない**。プロトコル（HTTPS等）、動作（検証・書込等）、向き、同期/非同期、境界を越えるかどうかは省略しない。省いてよいのは両端のノード名から自明な情報だけ（例: `web`→`api` の矢印に「web から api へ」とは書かない）。
- **`via` / `label_at` / `from_side` / `to_side` は最初から書かない**。自動配線・自動ラベル配置に任せ、`check_diagram.py` が具体的な座標を提示してから、指摘された1箇所にだけ加える。先回りして全エッジに `via` を敷き詰めると、ノードを動かすたびに手で座標を直す羽目になる。
- **`groups` は本当の所有・信頼・配備の境界だけ**に使う（VPC、セキュリティグループ、チームの持ち物 等）。「なんとなく近いノードをまとめる」目的では使わない（見た目のグルーピングがしたいだけなら groups を使わず row/col を近づけるだけでよい）。
- 修理は次の順序で進める: **スキーマ（id・重複・範囲）→ 配置（衝突・範囲外）→ 横切り・辺の向き → 交差・重なり・短い線 → ラベル**。上流を直すと下流の警告が連鎖的に消えることが多い。

## 3. 修理ループ

診断は一度に全部直そうとしない。

1. `python "$TOOLS/check_diagram.py" <deck_dir>` を実行する。
2. 報告された診断から **1件**を選ぶ（error があれば error を優先）。
3. その `fixes` のうち **1点だけ** を deck.json に反映する（複数の fixes 候補は「どれか1つ」の代替案であって、全部やるものではない）。
4. 再度 `check_diagram.py` を実行し、件数が減っていれば次の診断に進む。
5. **2ラウンド続けて件数が減らなければ止める**。見た目だけ帳尻を合わせようと `via`/`label_at` を闇雲に足し続けない。残った診断はそのままユーザーに正直に報告する（「◯件の label-collision が残っています。ラベルを短くするか2枚に分けることをご検討ください」等）。

診断はあくまで**座標の機械チェック**であり、矢印の向きが業務的に正しいか・ラベルの言葉選びが適切かは判定できない。`check_diagram.py` が0件でも、`preview_deck.py` で目視確認する。

### 診断コード別の直し方の例

`code` の一覧・意味は `deck-schema.md` の「図解タイプの診断」を参照。ここでは典型的な直し方を deck.json の差分で示す。

**`edge-through-node`**（エッジが無関係なノードを横切る）: 経由ノードを避ける経路を1点だけ追加する。

```jsonc
// 診断: エッジ a→b がノード「中継ノード」（id=mid）を横切ります
//       → edges の該当要素に "via": [[367, 228]] のような経由点を指定する
{ "from": "a", "to": "b", "label": "直行", "via": [[367, 228]] }
```
（座標は診断が提示したものをそのまま使う。自分で計算しない。）

**`label-collision`**（ラベルが他要素と重なる）: 提示された `label_at` をそのまま置くか、文言を短くする。

```jsonc
// 診断: → edges の該当要素に "label_at": [420, 210] のように位置を指定する
{ "from": "api", "to": "queue", "label": "enqueue", "label_at": [420, 210] }
```

**`too-dense`**（ノード/列/メッセージが多すぎる）: 補助ノードを `sublabel` に吸収するか、2枚に分ける。

```jsonc
// Before: 14ノードを1枚に詰め込む
// After: 全体像（主要7ノード＋groupsで束ねる）と詳細（残り7ノード）の2枚に分割
```

**`group-leak`**（groups の範囲に非メンバーが混入）: メンバーの `row`/`col` を隣接させて矩形にするか、はみ出したノードも `nodes` に加える。

```jsonc
// 診断: グループ「VPC」の範囲内にメンバーでないノード public-lb が入っています
// 対処: groups.nodes に "public-lb" を加える（本当に VPC 内なら）
//       または public-lb の row/col を範囲外へ動かす（VPC の外なら）
```

**`crossings`**（エッジ同士が交差する）: 戻りの矢印（下流→上流）を主経路と同じ辺に通さない。

```jsonc
// Before: worker→queue の戻り線が主経路の上を横切る
{ "from": "worker", "to": "queue", "label": "再投入" }
// After: 主経路の外側（下側）を通す
{ "from": "worker", "to": "queue", "label": "再投入", "from_side": "bottom", "to_side": "bottom" }
```

**`node-text-overflow`**（label/sublabel が箱に収まらない）: 詳細を `sublabel` に逃がすか、文言そのものを短くする。列・行を増やしてセルを大きくするのは最後の手段（ノード数が増えて別の警告を招きやすい）。

```jsonc
// Before: label が長すぎて箱からあふれる
{ "id": "api", "label": "決済処理APIサーバー（リトライ・冪等性制御つき）" }
// After: 要点だけ label に残し、詳細は sublabel へ
{ "id": "api", "label": "決済API", "sublabel": "リトライ・冪等性制御" }
```

## 4. HTML / PPTX の見た目の違い

座標・トークン解決は共通ソース（テーマ＋レイアウト＋deck.json）から行うため大枠のレイアウトは一致するが、レンダラ由来の細部差が残る（`deck-schema.md` の座標系の節と同じ考え方）。

- **`return`（戻り）のエッジ**: HTML は開いた矢印（`◁` 型）の SVG マーカー、PPTX は `sysDash`（細かい破線）＋開いた矢印ヘッド（`type="arrow"`）のコネクタで近似する。実線の矢印（三角形の塗り矢印）とは見分けが付くが、線の太さの見え方は HTML よりわずかに細くなる。
- **type アイコン**: HTML は 16×16 の stroke ベースの SVG（`frontend`/`backend`/`database`/`cloud`/`security`/`messagebus`/`external`）をそのまま描くが、PPTX には同じ描画方法が無いため、**プリセット図形の組み合わせで近似**する（例: `database`→ CAN 図形、`cloud`→ CLOUD 図形、`security`→ FLOWCHART_OFFPAGE_CONNECTOR 図形、`messagebus`→ 3本の矢印線）。輪郭の細部は HTML と完全には一致しない。
- **lifecycle の kind グリフ**（成功のチェック・失敗の×・待機の砂時計）も同様に、HTML は SVG パス、PPTX はプリセット図形／線分の組み合わせで近似する。
- **Keynote で PPTX を開く場合**: 本プラグインは PowerPoint（python-pptx が生成する OOXML）を正としており、Keynote での見え方は未検証（推測）。特にコネクタの矢印ヘッド（`headEnd`/`tailEnd` の `type="arrow"` による開いた矢印）や `prstDash`（`dashDot`/`sysDash` 等の破線パターン）は Keynote が独自に解釈し直すことがあるため、Keynote 配布が前提のデッキでは `preview_deck.py`（HTML/PNG）に加えて実際に Keynote で開いて確認することを推奨する。

## 5. Archify との違いと由来

このプラグインの図解タイプは Archify（<https://github.com/tt-a1i/archify> , MIT）の方式「AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して描く。検証に落ちたら座標付きの修理指示が返る」を Python ネイティブに取り込んだもの（Node.js・Archify 本体は不要）。参考動画: 「ArchifyでAIに図を描かせる新しいやり方」（クロノITチャンネル, <https://www.youtube.com/watch?v=L2KPenldwdo>）。

意図的に変えている点:

- **配置はグリッド（`row`/`col`）指定のみ**で px 座標は書かない（Archify は自由配置の pos/size）。
- **配色はテーマトークンのみ**で `type` ごとの色相は使わない。`type` は**アイコンの形**で表し、色は `variant`/`kind` が担う（テーマを切り替えても図解の配色が破綻しない設計）。
- **`lifecycle` のレーンは自由な N 本**（Archify は main/terminal の3帯固定）。
- **診断は常時有効**で、Archify にあるような品質プロファイルの切替は無い。
- **ブランドロゴの自動検出などネットワークを使う機能は非対応**。
- **`sequence` の自己メッセージ**（右側のコの字型の描画）は本プラグイン独自の拡張。

## 6. Archify JSON の取り込み

既存の Archify JSON（`archify.json`）があれば、`tools/archify_import.py` で 1 スライド分の JSON に変換できる（Node.js・Archify 本体は不要。純 Python）。

```bash
python "$TOOLS/archify_import.py" <archify.json>                   # 変換結果を stdout に JSON 出力
python "$TOOLS/archify_import.py" <archify.json> --eyebrow "TYPE / architecture"
python "$TOOLS/archify_import.py" <archify.json> --tolerance 70    # architecture の座標量子化の距離閾値(px)（既定70）
python "$TOOLS/archify_import.py" <archify.json> --out slide.json  # 変換結果をファイルに保存
python "$TOOLS/archify_import.py" <archify.json> --into <deck_dir> # deck.json の slides 末尾に追記（無ければ新規作成）
```

Archify の `diagram_type` は次のように対応するタイプへ変換される（`workflow` だけ `swimlane` に変わる点に注意）:

| Archify | このプラグイン |
|---|---|
| `architecture` | `architecture` |
| `workflow` | `swimlane` |
| `dataflow` | `dataflow` |
| `sequence` | `sequence` |
| `lifecycle` | `lifecycle` |

主な変換ルール:

- `architecture` は Archify 側が絶対座標（`pos`/`size`）しか持たないことが多いため、ノード中心座標を x/y それぞれでクラスタリングして `row`/`col`（グリッド位置）に量子化する（`--tolerance` で距離のしきい値を調整。既定 70px）。
- Archify 固有の絶対座標・幾何指定（`pos`/`size`/`via`/`labelAt`/`labelDx`/`labelDy`/`channelX`/`channelY`/`route`/`width`/`bias`/`cornerRadius` 等）は、このプラグインが自動配線・自動配置するため**捨てる**。何を捨てたかは変換時に stderr へ `note:` として要約表示される。
- Archify の `cards`（結論カードのテキスト）は、このプラグインの `notes`（スピーカーノート）に変換される。**`notes` は HTML でのみ表示され PPTX には出力されない**ため、PPTX 配布が前提のデッキでは内容を `lead` 等の可視領域へ改めて転記する。
- `workflow` の `groups`（Archify 側のグルーピング）や `mainPath`（主経路強調）は swimlane が対応する概念を持たないため捨てられる。

変換結果は必ずこのプラグインの診断（`validate_grid_diagram` / `layout_sequence` / swimlane の検証）にかけられ、診断は stderr に表示される。**error が1件でもあれば exit code 1** になるが、そのときも stdout には変換結果の JSON がそのまま出力される（壊れた状態を確認しながら deck.json 側で直せるようにするため）。変換後は本ガイドの「修理ループ」に従って deck.json を整える。

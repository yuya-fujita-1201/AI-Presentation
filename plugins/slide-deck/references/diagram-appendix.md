# 図解タイプの補足（HTML / PPTX の違い・Archify の由来・Archify JSON の取り込み）

[diagram-guide.md](diagram-guide.md)（タイプの選び方・作図規約・修理ループ）の補足。普段のデッキ作成では読まなくてよい。

## HTML / PPTX の見た目の違い

座標・トークン解決は共通ソース（テーマ＋レイアウト＋deck.json）から行うため大枠のレイアウトは一致するが、レンダラ由来の細部差が残る（[deck-schema.md](deck-schema.md)（索引）の座標系の節と同じ考え方）。

- **`return`（戻り）のエッジ**: HTML は開いた矢印（`◁` 型）の SVG マーカー、PPTX は `sysDash`（細かい破線）＋開いた矢印ヘッド（`type="arrow"`）のコネクタで近似する。実線の矢印（三角形の塗り矢印）とは見分けが付くが、線の太さの見え方は HTML よりわずかに細くなる。
- **type アイコン**: HTML は 16×16 の stroke ベースの SVG（`frontend`/`backend`/`database`/`cloud`/`security`/`messagebus`/`external`）をそのまま描くが、PPTX には同じ描画方法が無いため、**プリセット図形の組み合わせで近似**する（例: `database`→ CAN 図形、`cloud`→ CLOUD 図形、`security`→ FLOWCHART_OFFPAGE_CONNECTOR 図形、`messagebus`→ 3本の矢印線）。輪郭の細部は HTML と完全には一致しない。
- **lifecycle の kind グリフ**（成功のチェック・失敗の×・待機の砂時計）も同様に、HTML は SVG パス、PPTX はプリセット図形／線分の組み合わせで近似する。
- **Keynote で PPTX を開く場合**: 本プラグインは PowerPoint（python-pptx が生成する OOXML）を正としており、Keynote での見え方は未検証（推測）。特にコネクタの矢印ヘッド（`headEnd`/`tailEnd` の `type="arrow"` による開いた矢印）や `prstDash`（`dashDot`/`sysDash` 等の破線パターン）は Keynote が独自に解釈し直すことがあるため、Keynote 配布が前提のデッキでは `preview_deck.py`（HTML/PNG）に加えて実際に Keynote で開いて確認することを推奨する。

## Archify との違いと由来

このプラグインの図解タイプは Archify（<https://github.com/tt-a1i/archify> , MIT）の方式「AI は型付き JSON（構造・意味・配置）だけを書き、決定論的なコードが検証して描く。検証に落ちたら座標付きの修理指示が返る」を Python ネイティブに取り込んだもの（Node.js・Archify 本体は不要）。参考動画: 「ArchifyでAIに図を描かせる新しいやり方」（クロノITチャンネル, <https://www.youtube.com/watch?v=L2KPenldwdo>）。

意図的に変えている点:

- **配置はグリッド（`row`/`col`）指定のみ**で px 座標は書かない（Archify は自由配置の pos/size）。
- **配色はテーマトークンのみ**で `type` ごとの色相は使わない。`type` は**アイコンの形**で表し、色は `variant`/`kind` が担う（テーマを切り替えても図解の配色が破綻しない設計）。
- **`lifecycle` のレーンは自由な N 本**（Archify は main/terminal の3帯固定）。
- **診断は常時有効**で、Archify にあるような品質プロファイルの切替は無い。
- **ブランドロゴの自動検出などネットワークを使う機能は非対応**。
- **`sequence` の自己メッセージ**（右側のコの字型の描画）は本プラグイン独自の拡張。

## Archify JSON の取り込み

既存の Archify JSON（`archify.json`）があれば、`${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py` で 1 スライド分の JSON に変換できる（Node.js・Archify 本体は不要。純 Python）。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json>                   # 変換結果を stdout に JSON 出力
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --eyebrow "TYPE / architecture"
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --tolerance 70    # architecture の座標量子化の距離閾値(px)（既定70）
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --out slide.json  # 変換結果をファイルに保存
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --into <deck_dir> # 追記内容を表示するだけ（既存 deck.json は書き換えない）
python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --into <deck_dir> --confirm  # 承認後に実際に追記して保存
```

### `--into` の承認ゲート（既存 deck.json の上書き前に必ず確認する）

`--into` は既存の `deck.json` の `slides` の末尾に 1 枚追記して**同じパスへ上書き保存**する。利用者が手で書いたデッキを壊しうるため、`--confirm` を付けずに実行して追記内容（どのファイルに・何枚目として・どんなスライドが入るか）を確認し、利用者の承認を得てから `--confirm` を付ける。承認の手順と文面は [approval-gates.md](approval-gates.md)（上書き承認はそこに集約）。承認が得られないときは `--out <file>` で別ファイルに書き出して渡す。`deck.json` が無い（新規）場合は上書きにならないため `--confirm` は不要。

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

変換結果は必ずこのプラグインの診断（`validate_grid_diagram` / `layout_sequence` / swimlane の検証）にかけられ、診断は stderr に表示される。**error が1件でもあれば exit code 1** になるが、そのときも stdout には変換結果の JSON がそのまま出力される（壊れた状態を確認しながら deck.json 側で直せるようにするため）。変換後は [diagram-guide.md](diagram-guide.md) の「修理ループ」に従って deck.json を整える。

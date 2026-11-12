# 既存 PPTX の取り込み（見た目そのまま HTML 化／構図の型起こし）

既存の PowerPoint を使う依頼は 2 通りある。どちらかを選ぶ。

| 依頼 | やること |
|---|---|
| 「この PowerPoint を見た目そのまま HTML にしたい」 | 1. `pptx_import.py` で canvas 型に取り込む |
| 「この 1 枚の構図を、今後のデッキでも使いたい」 | 2. `pattern_from_pptx.py` で型（パターン）に起こす |
| 「この資料の内容を整理して作り直したい」 | 取り込まない。内容を材料として読み、新規作成の流れ（`SKILL.md`）で作る |

（`${CLAUDE_PLUGIN_ROOT}` は `SKILL.md` に書かれた実パスに読み替える。この補助ファイルでは変数が展開されない。）

## 1. 見た目そのまま取り込む（canvas 型）

型に当てはめて作り直すと、矢羽根や自由配置の図が崩れる。そのため、座標つきの要素列（`canvas`）として取り込む。`SKILL.md` の「タイプの選び方」・骨子の手順は省略してよい。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/pptx_import.py" <src.pptx> --into <deck_dir>
python "${CLAUDE_PLUGIN_ROOT}/tools/build_deck.py" <deck_dir> --html
python "${CLAUDE_PLUGIN_ROOT}/tools/preview_deck.py" <deck_dir>
pwsh "${CLAUDE_PLUGIN_ROOT}/tools/export_pptx_png.ps1" -Src <src.pptx> -OutDir <deck_dir>/_work/ref   # Windows + PowerPoint のみ
python "${CLAUDE_PLUGIN_ROOT}/tools/compare_ref.py" <deck_dir> <deck_dir>/_work/ref
python "${CLAUDE_PLUGIN_ROOT}/tools/check_layout.py" <deck_dir> --no-build
```

- `<deck_dir>/deck.json` が既にあると、`pptx_import.py` は書かずに終了する（丸ごと置き換わるため）。承認の手順は `${CLAUDE_PLUGIN_ROOT}/references/approval-gates.md`。
- `export_pptx_png.ps1` は Windows と PowerPoint がある環境だけで使える。無ければ `compare_ref.py` は省略し、プレビュー PNG を元の PPTX と見比べる。
- `build/compare/scores.txt` の差が大きいスライドから `cmp-NN.png`（上 = 元、下 = HTML）を目で見て、ずれは該当要素の座標・文字サイズを deck.json で直す。再取り込みすると手直しは消える。この点は利用者に伝える。
- ラスタ画像は埋め込まず枠になる。PPTX に再出力すると図形は個別に編集できるが、SVG アイコンは画像になる。これも利用者に伝える。
- プラグインのコード（`pptx_import.py` / `canvas_engine.py`）はその場で書き換えない。
- 仕様は `${CLAUDE_PLUGIN_ROOT}/references/schema/canvas.md`。

**canvas は取り込み結果を直すためのもの**で、新しい構図を作るために canvas を手書きしない（テーマ・共通パーツが効かず、色も固定になるため）。新しい構図が欲しいときは、型（`pattern`）を使う。

## 2. 構図を型に起こす（パターン）

PowerPoint の 1 枚、またはこのプラグインのデッキの 1 枚を、中身を差し替えて何度でも使える型の JSON にする。色はテーマトークンに寄せるので、テーマを変えれば配色も追随する。

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_from_pptx.py" <src.pptx> --slide N --name <名前> [--theme <テーマ名>] [--dir DIR]
python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_from_pptx.py" --from-deck <deck_dir> --deck-slide M --name <名前>
```

- `--slide` は **PPTX 上の枚数目**。agenda の分割や図解の凡例ページが入るため、deck.json の番号とずれることがある。deck.json の番号で指すなら `--from-deck <deck_dir> --deck-slide M`。
- 同名のパターンを上書きするときは `--confirm` が要る（承認は `approval-gates.md`）。
- 出力は `<dir>/<名前>.json` と、確認用デッキ `<dir>/_check/<名前>/`（元と展開結果を並べたスライド）。確認用デッキをビルドして、元と同じ構図になっているかを目で見る。
- 起こした型の書き方・直し方・使い方（`{"type": "pattern", "pattern": "名前", "slots": {…}}`）は `${CLAUDE_PLUGIN_ROOT}/references/schema/pattern.md`。使える型は `python "${CLAUDE_PLUGIN_ROOT}/tools/pattern_engine.py" list [--deck <deck_dir>]` で調べる。

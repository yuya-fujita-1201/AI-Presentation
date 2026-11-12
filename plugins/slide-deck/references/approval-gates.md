# 上書きの承認ゲート（利用者の既存ファイルを書き換える前に）

利用者が手で書いた `deck.json` や、登録済みのパターン・テーマは、直すのに手間がかかったものである。確認なしに上書きすると元に戻せないことがあるため、**書き換える前に利用者の承認を取る**。承認の手順はこのファイルに集約している。`create-deck` / `review-deck` / `diagram-guide.md` などは、ここを参照する。

`${CLAUDE_PLUGIN_ROOT}` はプラグインのディレクトリ。新規作成（書き込み先に同名のファイルが無い）なら承認は要らない。

## 承認が要る操作

| 操作 | 何が起きるか | ツール側の止め方 |
|---|---|---|
| `archify_import.py <archify.json> --into <deck_dir>` | 既存の `deck.json` の `slides` 末尾に 1 枚を追記し、同じパスへ上書き保存する | `--confirm` が無いと書かずに exit 1。追記される内容は stdout、書き込み先と追記後の枚数は stderr に出る |
| `pptx_import.py <src.pptx> --into <deck_dir>` | 既存の `deck.json` を丸ごと置き換える（元は `deck.json.bak` に退避） | `--confirm` が無いと書かずに終了 |
| `pattern_from_pptx.py ... --name <名前>` | 同名のパターン JSON（`patterns/<名前>.json`）を上書きする | `--confirm` が無いと終了 |
| `new_theme.py <名前>` / `theme_from_sample.py ... --name <名前>` の `--force` | 同名のテーマ JSON（`themes/<名前>.json`）を上書きする。利用者が色・フォントを手直ししたテーマが消える | `--force` が無いと「すでに存在します（上書きは --force）」で終了（`--force` が承認の印なので、エラー文に従って機械的に付けない） |
| Write / Edit で既存 `deck.json` を丸ごと書き換える | 利用者の手直しが消える | ツール側の止めは無い。必ずこの手順を踏む |

部分的な直し（1 枚の文言・`style` の差分）は、利用者が「直して」と依頼しているなら承認済みとみなしてよい。上の表は「依頼の範囲を超えて、既にあるものを置き換える」操作の話である。

## 手順（この順で）

1. まず `--confirm` を付けずに実行する（Write / Edit のときは、書き換える内容の差分を作る）。ツールは何も書かずに、何が変わるかを出力する。
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --into <deck_dir>
   python "${CLAUDE_PLUGIN_ROOT}/tools/pptx_import.py" <src.pptx> --into <deck_dir>
   ```
2. その出力（どのファイルの、何枚目に、どんな内容が入るか）を利用者に見せ、`AskUserQuestion` で「この内容で書き換えてよいか」を聞く。選択肢は「書き換える」「別のファイルに書き出す」の 2 つで足りる。
3. 承認されたときだけ、`--confirm` を付けて再実行する。
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/tools/archify_import.py" <archify.json> --into <deck_dir> --confirm
   ```
4. 承認されなければ書き換えない。`archify_import.py` は `--out <file>` で別ファイルに書き出して渡す。`pptx_import.py` は別の `--into` フォルダに取り込む。`new_theme.py` / `theme_from_sample.py` は別の `<名前>` で作る。

## 理由と注意

- 理由: `--confirm` を機械的に付けて通すと、承認ゲートの意味が無くなる。承認は利用者の発言（または `AskUserQuestion` の回答）であり、エージェントの判断では代えられない。
- 利用者が依頼の中で「置き換えてよい」「上書きして」と明示しているときは、それが承認である（もう一度聞かない）。
- 取り込み結果を手直ししたあとで再取り込みすると、手直しは消える。承認を取るときにこの点も伝える（`pptx_import.py` は `.bak` に元を残す）。
- 承認が要るのは `deck.json`・パターン JSON・テーマ JSON だけ。`build/` の生成物は毎回作り直すもので、承認は要らない（ただし `build/` は直接編集しない）。
- `review-deck` が評価結果から `deck.json` を直すときの承認（最初の 1 回）も、同じ考え方である。手順は `skills/review-deck/SKILL.md` の手順 3-3 にある。

---
name: setup
description: slide-deck プラグインの初回セットアップ。スライド生成に必要な Python 依存（python-pptx など）を確認・インストールする。ビルドで python-pptx やプレビューで Playwright が無いと言われたとき、または初めて使うときに実行する。
allowed-tools: Bash
---

# setup — slide-deck の初回セットアップ

スライド生成に必要な依存を確認・インストールする。**Python 3 が入っていることが前提**（`python --version`。無ければ先に Python を導入）。

## 依存の役割
| パッケージ | 要否 | 用途 |
|---|---|---|
| `python-pptx` | 必須 | PPTX 生成 |
| `playwright`（+ chromium） | 任意 | `preview_deck.py` のプレビューPNG生成 |
| `pillow` | 任意 | `contact_sheet.py` の一覧シート生成 |

## 実行
```bash
# 必須(python-pptx)を確認/導入
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py"

# プレビューPNGも使う場合（playwright + chromium も導入）
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --playwright

# すべて導入
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --all

# 状態確認のみ（導入しない）
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" --check
```
`python` が無ければ `python3` に読み替える。社内環境で `pip` に制約がある場合は、プロキシ設定や `--index-url` を付けて実行する必要があるかもしれない。

導入が終われば `/slide-deck:create-deck` でスライドを作成できる。

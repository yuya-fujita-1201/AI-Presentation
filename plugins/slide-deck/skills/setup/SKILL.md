---
name: setup
description: slide-deck プラグインの初回セットアップ。スライド生成に必要な Python 依存（python-pptx / playwright / pillow / pymupdf）を確認・インストールする。ユーザーが「セットアップして」/ `/slide-deck:setup` を明示的に頼んだときだけ実行する。
argument-hint: "[--playwright|--pillow|--pdf|--all|--check]"
disable-model-invocation: true
allowed-tools: Bash(python:*), Bash(python3:*), Bash(py:*)
---

# setup — slide-deck の初回セットアップ

スライド生成に必要な依存を確認・インストールする。**Python 3.9 以上が入っていることが前提**（`python --version`。無ければ [python.org](https://www.python.org/) から導入）。

## 依存の役割
| パッケージ | 要否 | 用途 |
|---|---|---|
| `python-pptx` | 必須 | PPTX 生成 |
| `playwright`（+ chromium） | 任意 | `preview_deck.py` / `check_layout.py` / `contact_sheet.py` のプレビューPNG生成 |
| `pillow` | 任意 | `contact_sheet.py` の一覧シート生成、画像からのテーマ抽出（`theme_from_sample.py`） |
| `pymupdf` | 任意 | PDF からのテーマ抽出（`theme_from_sample.py --pdf`） |

## 実行

渡された引数（`--playwright` 等）はそのまま `setup_deps.py` に転送する:
```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" $ARGUMENTS
```

| フラグ | 効果 |
|---|---|
| （なし） | 必須（python-pptx）を確認・導入 |
| `--playwright` | playwright + chromium も導入（プレビューPNG用） |
| `--pillow` | pillow も導入（画像からのテーマ抽出用） |
| `--pdf` | pymupdf も導入（PDF からのテーマ抽出用） |
| `--all` | 上記すべてを導入 |
| `--check` | 状態確認のみ（何も導入しない） |

例:
```bash
/slide-deck:setup            # python-pptx のみ
/slide-deck:setup --all      # 全部入れる
/slide-deck:setup --check    # 確認のみ
```

## Windows の注意
- `python` を実行して Microsoft Store が開く場合は Python 未インストール。[python.org](https://www.python.org/) からインストールする（"Add python.exe to PATH" にチェック）
- インストール後も `python` が見つからない場合は Python Launcher の `py -3` を使う: `py -3 "${CLAUDE_PLUGIN_ROOT}/tools/setup_deps.py" $ARGUMENTS`
- PowerShell / Git Bash のどちらでも同じコマンドで動く

macOS / Linux で `python` が無い場合は `python3` に読み替える。社内環境で `pip install` が `externally-managed-environment`（PEP 668）エラーになる場合は、`setup_deps.py` が venv 作成手順や `--pip-args` の使い方を案内するので、その指示に従う。playwright の chromium 取得が社内プロキシで失敗する場合は `HTTPS_PROXY` / `PLAYWRIGHT_DOWNLOAD_HOST` の案内が表示される。

導入が終われば `/slide-deck:create-deck` でスライドを作成できる。

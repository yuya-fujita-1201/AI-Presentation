# AI-Presentation — スライド生成プラグイン配布リポジトリ

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布する**マーケットプレイス**です。

## 使う人向け（インストール）

```
/plugin marketplace add yuya-fujita-1201/AI-Presentation
/plugin install slide-deck@ai-presentation
```

インストール後の初回セットアップ・使い方はプラグインの README を参照:
→ [`plugins/slide-deck/README.md`](plugins/slide-deck/README.md)

かんたんには、依存を入れて（`/slide-deck:setup`）、スライド作成を頼めば `create-deck` スキルが deck.json を作ってビルドします。

## リポジトリ構成

```
AI-Presentation/
├── .claude-plugin/
│   └── marketplace.json          # マーケットプレイス定義（配布する plugin の一覧）
├── plugins/
│   └── slide-deck/               # ★ slide-deck プラグイン本体（自己完結）
│       ├── .claude-plugin/plugin.json
│       ├── requirements.txt      #   Python 依存関係（pip install -r で導入可）
│       ├── skills/               #   create-deck / add-theme / review-deck / export-pdf / setup
│       ├── tools/                #   build_deck.py / preview_deck.py / check_layout.py / check_svg_fonts.py /
│       │                         #   lint_deck_text.py / deck_metrics.py / contact_sheet.py / check_theme.py /
│       │                         #   export_pdf.py / new_theme.py / theme_from_sample.py / setup_deps.py /
│       │                         #   diagram_engine.py / check_diagram.py / archify_import.py
│       ├── templates/            #   themes/ layouts/
│       ├── references/           #   deck-schema.md / themes.md / content-guide.md / diagram-guide.md
│       ├── examples/             #   全スライドタイプの見本デッキ
│       ├── manual/deck.json      #   スライド版マニュアルのソース
│       └── USER-GUIDE.html       #   ↑ をビルドした成果物（配布物に同梱）
├── CLAUDE.md                     # このリポジトリで作業する Claude Code 向けルール
├── AGENTS.md                     # その他 AI エージェント向けの入口
└── README.md                     # このファイル
```

`plugins/slide-deck/` は自己完結しているので、将来この 1 ディレクトリを別リポジトリへ移設して単独配布することもできます。

## 開発・動作確認（このリポジトリ内）

**Python 3.9 以上**が必要（`X | Y` 型注釈は使わない等、3.9 互換の構文のみ）。プラグインを導入しなくても、同梱スクリプトを直接叩いて動作確認できます（`python` が無ければ `python3`、Windows で見つからなければ `py -3`。PowerShell / Git Bash のどちらでも同じコマンドで動きます）:

```bash
# 依存セットアップ（requirements.txt からでも可: pip install -r plugins/slide-deck/requirements.txt）
python plugins/slide-deck/tools/setup_deps.py

# 見本デッキをビルド
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/examples/template-sample

# マニュアル（USER-GUIDE.html）を再ビルド
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/manual --html
# → plugins/slide-deck/manual/build/user-guide.html を plugins/slide-deck/USER-GUIDE.html にコピー

# ユニットテスト（同梱の自動テスト一式）
python -m unittest discover -s plugins/slide-deck/tools -p "test_*.py"

# ローカルでプラグインとして読み込んでテスト
claude --plugin-dir ./plugins/slide-deck
```

プラグイン内のスキル・ツール・テンプレートを編集したら、`/plugin` 経由で使っている場合は `/reload-plugins` で再読み込みします。機能を変更した場合は `plugins/slide-deck/.claude-plugin/plugin.json` と `.claude-plugin/marketplace.json` の `version`（semver）を bump してください。

このリポジトリは社内配布物です。受領者内での利用を想定しており、社外への再配布は想定していません。

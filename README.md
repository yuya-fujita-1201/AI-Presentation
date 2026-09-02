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
│       ├── skills/               #   create-deck / add-theme / setup
│       ├── tools/                #   build_deck.py / preview_deck.py / new_theme.py / setup_deps.py ほか
│       ├── templates/            #   themes/ layouts/
│       ├── references/           #   deck-schema.md / themes.md
│       └── examples/             #   全スライドタイプの見本デッキ
├── CLAUDE.md                     # このリポジトリで作業する Claude Code 向けルール
├── AGENTS.md                     # その他 AI エージェント向けの入口
└── README.md                     # このファイル
```

`plugins/slide-deck/` は自己完結しているので、将来この 1 ディレクトリを別リポジトリへ移設して単独配布することもできます。

## 開発・動作確認（このリポジトリ内）

プラグインを導入しなくても、同梱スクリプトを直接叩いて動作確認できます（`python` が無ければ `python3`）:

```bash
# 依存セットアップ
python plugins/slide-deck/tools/setup_deps.py

# 見本デッキをビルド
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/examples/template-sample

# ローカルでプラグインとして読み込んでテスト
claude --plugin-dir ./plugins/slide-deck
```

プラグイン内のスキル・ツール・テンプレートを編集したら、`/plugin` 経由で使っている場合は `/reload-plugins` で再読み込みします。

# AI-Presentation — スライド生成プラグイン配布リポジトリ

このリポジトリは Claude Code プラグイン **`slide-deck`**（JSON をソースにスライドを HTML / PowerPoint にビルドする仕組み）を配布します。人が喋った内容から AI が骨子を作り、承認を受けて、きれいなスライドまで仕上げることを目標にしています。JSON でスライドの内容とデザインを管理し、34 種類のスライドタイプ（構成図・データフロー・シーケンス等の自動配線図解、矢羽根スケジュール、進捗ステータス表、要旨・選ばれる理由・体制図などの提案書の定型ページ、大きな数字とグラフ、1 枚に複数ブロックを置く合成スライド、登録した構図を使い回す型を含む）、テーマと形のプリセット、文字量に合わせた自動フィット、機械検証、PDF 書き出しに対応します。既存の PowerPoint を見た目そのままに HTML 化する取り込み専用の `canvas` もあります。

## 使う人向け（インストール）

社内配布は **`plugins` フォルダの Zip を受け取って展開**する形式です（マーケットプレイスからのダウンロードではありません）。

1. 配布された Zip を任意の場所に展開する
2. 展開して出てきた `slide-deck` フォルダを指定して Claude Code を起動する:

   ```bash
   claude --plugin-dir <展開先>/slide-deck
   ```

   （IDE 拡張を使う場合は設定でプラグインフォルダを指定します）
3. これで `create-deck` / `add-theme` / `review-deck` / `export-pdf` / `setup` の 5 スキルが使えます

初回セットアップ・使い方はプラグインの README を参照:
→ [`plugins/slide-deck/README.md`](plugins/slide-deck/README.md)

かんたんには、依存を入れて（`/slide-deck:setup`）、スライド作成を頼めば `create-deck` スキルが進めます。使い方の全体像はスライド版マニュアル [`plugins/slide-deck/USER-GUIDE.html`](plugins/slide-deck/USER-GUIDE.html) にまとまっています。

## 使い方の流れ（喋る → 骨子 → 承認 → できあがり）

1. 言いたいことを話す（書き起こし・メモ・既存資料を渡してもよい）。聞き手や枚数が決まっていなくても、AI が仮置きして先へ進みます
2. AI が骨子（`outline.md`。スライドごとの結論文・根拠と出どころ・使うタイプ・要確認）を作る
3. 骨子を見て直しを伝える。**承認は 1 回**で、以降は確認なしで進みます（設定フォームは、選びたいと頼んだときだけ出ます）
4. `deck.json` の作成 → ビルド（HTML + PPTX）→ 機械チェックとプレビューの目視 → 成果物の引き渡し。数字や固有名詞の根拠が材料に無い箇所は作らず、`【要確認: …】` と書いて HTML と PPTX の両方で目立たせ、件数と一覧を報告します

## 3.1.0 の変更

AI が作ったと一目で分かるスライドのパターン（全部盛り・同じラベルの繰り返し・0 埋め番号・強調のカギカッコ・意味の無い色や幅・定型の免責注釈など）を、内容ガイド・文言チェック・評価エージェントの採点で防ぐようにした。agenda の連番と章扉の自動採番は「1」表記が既定になった。詳細は [`plugins/slide-deck/README.md`](plugins/slide-deck/README.md) の「3.1.0 の変更点」。

## 3.0.0 で増えたもの

詳細・互換性の注意は [`plugins/slide-deck/README.md`](plugins/slide-deck/README.md) の「3.0.0 の変更点」。

- **自動フィットと密度**: 文字量に合わせて文字サイズ・列幅・行の高さ・箱の高さを自動で決める。`meta.density`（talk / standard / read）で聞き手と用途に合わせる。位置やサイズを手で詰める `style` の書き込みが要らなくなる
- **型（パターン）の登録と同梱の型 19 個**: 「この構図をまた使いたい」を JSON の型にして、中身だけ差し替えて使い回す。PPTX の 1 枚から型を起こすツールつき
- **合成スライドと分割**: 1 枚に図・要点・数字を 2〜4 ブロック並べる `composite`、色面や画像のパネルに根拠の図表を添える `split`
- **主役のページ**: 表紙・章扉・言い切りの `variant` と `background`、cards の強弱、画像を端まで届かせる `bleed`
- **形のプリセット**: `meta.shape`（classic / sharp / soft / editorial）で角丸・罫線・影・見出しの太さを一括で切り替え
- **数字とグラフ**: 大きな数字の `kpi`、棒・折れ線・積み上げ・ウォーターフォール・ドーナツの `chart`（どちらも PowerPoint のネイティブ図形）
- **要確認の強調**: 根拠が無い箇所の `【要確認】` を HTML / PPTX の両方で強調し、ビルドで件数を報告
- **検査ツールの拡充**: はみ出し・コントラスト・線の貫通・孤字などの実測（`check_layout.py`）、PPTX の機械検証（`verify_pptx.py`）、PPTX と HTML の見た目比較（`check_pptx.py`）ほか

## リポジトリ構成

```
AI-Presentation/
├── .claude-plugin/
│   └── marketplace.json          # マーケットプレイス定義（配布する plugin の一覧）
├── plugins/
│   └── slide-deck/               # ★ slide-deck プラグイン本体（自己完結）
│       ├── .claude-plugin/plugin.json
│       ├── pyproject.toml / uv.lock   #   Python 依存関係（uv でハッシュ固定）
│       ├── requirements.txt      #   Python 依存関係（pip install -r で導入可）
│       ├── skills/               #   create-deck（補助ファイルつき）/ add-theme / review-deck / export-pdf / setup
│       ├── agents/               #   deck-evaluator（評価エージェント）
│       ├── tools/                #   ビルド・各タイプのエンジン・検査・テーマ/型の作成（一覧はプラグインの README）と test_*.py
│       ├── templates/            #   themes/ layouts/ shapes/ patterns/ icons/
│       ├── references/           #   deck-schema.md（索引）/ schema/（タイプ別の仕様）/ themes.md / content-guide.md /
│       │                         #   diagram-guide.md ほか
│       ├── examples/             #   template-sample（主要なタイプの見本。1 本の提案デッキ）/ shape-gallery（形 4 種の比較）
│       ├── manual/deck.json      #   スライド版マニュアルのソース
│       └── USER-GUIDE.html       #   ↑ をビルドした成果物（配布物に同梱）
├── CLAUDE.md                     # このリポジトリで作業する Claude Code 向けルール
├── AGENTS.md                     # その他 AI エージェント向けの入口
└── README.md                     # このファイル
```

`plugins/slide-deck/` は自己完結しているので、将来この 1 ディレクトリを別リポジトリへ移設して単独配布することもできます。

## 開発・動作確認（このリポジトリ内）

**Python 3.14 以上**が必要（依存は `plugins/slide-deck/uv.lock` にハッシュ固定。`pyproject.toml` に `requires-python` を宣言）。プラグインを導入しなくても、同梱スクリプトを直接叩いて動作確認できます（`python` が無ければ `python3`、Windows で見つからなければ `py -3`。PowerShell / Git Bash のどちらでも同じコマンドで動きます）:

```bash
# 依存セットアップ（requirements.txt からでも可: pip install -r plugins/slide-deck/requirements.txt）
python plugins/slide-deck/tools/setup_deps.py

# 見本デッキをビルド（build/ ができるので、確認後に消すか、リポジトリの外にコピーしてビルドする）
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/examples/template-sample

# マニュアル（USER-GUIDE.html）を再ビルド
python plugins/slide-deck/tools/build_deck.py plugins/slide-deck/manual --html
# → plugins/slide-deck/manual/build/user-guide.html を plugins/slide-deck/USER-GUIDE.html にコピー

# 生成した PPTX の機械検証（zip 整合・再パース・ノート無し・XML 整形式・文書プロパティ）
python plugins/slide-deck/tools/verify_pptx.py plugins/slide-deck/examples/template-sample/build/*.pptx

# ユニットテスト（同梱の自動テスト一式）
python -m unittest discover -s plugins/slide-deck/tools -p "test_*.py"

# ローカルでプラグインとして読み込んでテスト
claude --plugin-dir ./plugins/slide-deck

# プラグイン定義の検証
claude plugin validate ./plugins/slide-deck
claude plugin validate .
```

見本・manual をビルドしたあとの `build/` と、テストを回したあとの `plugins/slide-deck/tools/__pycache__` は消します（`**/build/` と `__pycache__/` は `.gitignore` 済みですが、リポジトリに残さない運用です）。開発の手順（タイプや型を足す手順、検査の一式、バージョンを上げる場所）は [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) にあります。

プラグイン内のスキル・ツール・テンプレートを編集したら、`/plugin` 経由で使っている場合は `/reload-plugins` で再読み込みします。機能を変更した場合は `plugins/slide-deck/.claude-plugin/plugin.json`・`.claude-plugin/marketplace.json`（2 か所）・`plugins/slide-deck/pyproject.toml`・`plugins/slide-deck/uv.lock`（`slide-deck` の行）の `version`（semver）を bump してください。

このリポジトリは社内配布物です。受領者内での利用を想定しており、社外への再配布は想定していません。

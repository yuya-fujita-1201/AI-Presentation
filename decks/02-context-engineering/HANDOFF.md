# CEデッキ ハンドオフ（2026-08-15 更新）

## 1. 現在の正本

「コンテキストエンジニアリング超入門」の正本は、次のフォルダです。

`decks/02-context-engineering/`

- 正本データ: `deck.json`
- 総枚数: 72枚（本編36枚、付録・出典37〜72枚目）
- HTML: `build/ai-eng-02-context-engineering-v2.html`
- PPTX: `build/ai-eng-02-context-engineering-v2.pptx`
- PNG: `build/preview/slide-01.png` 〜 `slide-72.png`
- レビュー記録: `GPT-Review.md`、`CODEX-Review.md`、`GPT-Review02.md`、`CODEX-Review02.md`、`CODEX-Review03.md`、`CODEX-Review04.md`（最終版）

旧フォルダ `decks/_archive/ai-eng-02-context-engineering/` と、過去のPR・worktreeは履歴用です。今後は `decks/02-context-engineering/` を直接更新し、旧版へ逆同期しません。

## 2. Claude版からの統合とCodex再監査

統合元として確認したClaude作業版は次です。

`.claude/worktrees/ce-slide9-newhire-vs-veteran/decks/ai-eng-02-context-engineering/`

統合前の比較では、Claude作業版とv2の `deck.json`、参照アセット38ファイル、HTMLはすでにバイト単位で一致していました。PPTXはZIP内部の生成差によりハッシュが異なりましたが、正本データの差ではありませんでした。

その一致版を基準に、`GPT-Review.md` の指摘をCodexが再確認して反映しました。主な修正は次のとおりです。

- コンテキストを「今回の推論でモデルに渡され、利用可能な情報」と明確化
- 保存済みファイル・メモリと、実際にロードされたコンテキストを区別
- 「都度渡す／必要時に取得／自動ロード」の3経路と、コンテキスト外の権限・hook・承認を分離
- CLAUDE.md、メモリ、ルールファイルの説明をClaude Codeの現行公式仕様に合わせて修正
- ルールファイルを強制機構のように見せる表現を修正し、実行環境のガードレールを明示
- OKFを情報整理フォーマットとして説明し、ロード機構と混同しないよう修正
- 「必ず」「ゼロになる」「完全に防ぐ」等の過度な保証表現を緩和
- 事故例と出典表の表現・出典対応を整理

詳細な指摘対応と検証結果は `CODEX-Review.md` を参照してください。

## 3. GPT-Review02対応と最終再監査

2回目のGPT Proレビュー `GPT-Review02.md` に対し、次を追加修正した。

- 3経路を「①自動ロード → ②必要時に取得 → ③今回渡す」に全編で統一
- メモリを保存方式として整理し、自動ロードと必要時取得の両方になり得る説明へ統一
- 短く毎回必要な情報と、大きい・詳細・時々必要な情報の振り分け基準を明示
- CLAUDE.mdの200行未満目安とMEMORY.md先頭200行／25KBの開始時ロード上限を分離
- context rot、ルール量、出力形式の断定を弱め、根拠の範囲へ限定
- コンテキスト整備とガードレール整備の効果を分離
- 最後の行動喚起を、ルールへ即追加する指示ではなく置き場所の再検討へ変更

初回の独立再監査で付録S50・S54とS15の残課題を検出し、追加修正後の再監査で重大0件・中0件・軽微0件のPASSとなった。全72枚の視覚監査と、追修正したS6・S15・S27・S50・S54の再確認もPASS。詳細は `CODEX-Review02.md` を参照する。

## 4. 追加GPTレビュー対応と最終再監査

会話内で受領した3回目のGPT Proレビューに対し、次を追加修正した。

- S24で、`/context`と`InstructionsLoaded`によるロード確認を先に行い、ロード済みの場合に長さ・曖昧さ・競合を疑う手順へ変更
- S18・S30で、Skillsの`description`と`SKILL.md`本文の読み込み段階を分離
- S32で、短いレビュー方針をルールへ、長い規約本文を参照先へ置く原則を統一
- 「自動ロード／必要時取得／今回渡す」という経路と、CLAUDE.md・Skills・フォルダ等の供給源を用語上分離
- S31・S34・S42で、改善例と境界事例、文章上の安全方針と実行環境の強制境界を分離
- S7・S26・S29・S33・S41・S51・S70・S71の用語・断定・ノート・出典を整理

独立内容監査で追加検出したS17・S41・S31ノートも修正し、再監査で重大0件・中0件・軽微0件のPASSとなった。全72枚の視覚監査後、改行を追修正し、最終変更したS17・S34・S41の独立目視もPASS。詳細は`CODEX-Review03.md`を参照する。

## 5. 最後の6点対応と最終版確定

会話内で受領した最終GPTレビューに対し、指定された6点だけを修正した。

- 表紙日付を出典確認日と同じ2026-08-15へ統一
- S20に明示呼び出し時を追加
- S31を実務改善例3つ＋安全上の境界事例1つへ変更
- S36を同じミスの再発率低減へ変更
- S33・S71のCode Review／Structured Outputs出典対応を整理し、S32を教材例として分離
- S14・S35のKeynote理由を本プロジェクトの生成方式に限定

変更対象8枚の独立目視は、S20の不自然な改行を1回修正した後に全てPASS。全72枚の機械ゲート、PPTX再パース、ノート混入なし、参照アセット、OKF検証もPASSした。詳細は`CODEX-Review04.md`を参照する。この版を最終版の正本とする。

## 6. 今後の編集手順

1. `decks/02-context-engineering/deck.json` または同フォルダの `assets/` を編集する
2. `/opt/homebrew/bin/python3 tools/build_deck.py decks/02-context-engineering`
3. `/opt/homebrew/bin/python3 tools/preview_deck.py decks/02-context-engineering`
4. 72枚のPNGを実際に開き、文字切れ・重なり・表の収まり・図とキャプションを確認する
5. `unzip -t`、python-pptx再パース、72枚一致、全スライド `has_notes_slide == False` を確認する
6. `bash pipeline/bin/gate_deck.sh decks/02-context-engineering` を実行する
7. 内容・検証結果が変わったら最新のレビュー記録とこのハンドオフを更新する

## 7. 編集上の原則

- `build/` は生成物なので直接編集しない
- 図解ページは原則 `image_text` を使う
- ルールファイルは助言的なコンテキストであり、権限・hook・承認のような強制機構とは分ける
- 製品固有の自動ロード、必要時ロード、メモリ仕様を一般論として断定しない
- PPTXにスピーカーノートを含めない
- 検証していない結果を完了扱いにしない

## 8. 履歴メモ

過去のPR #4〜#8、`loop/ce-ch2-4-restructure`、旧58枚版・71枚版に関する議論は、今回の72枚版へ統合済みです。今後の判断で参照はできますが、正本の所在を上書きするものではありません。

## 9. 2026-08-18：シリーズ01の暖色デザインへ統一

現行正本 `decks/02-context-engineering/` の内容・順序は維持し、シリーズ01と異なっていた緑の共通UI色を暖色へ統一した。

- `layout_overrides` の見出し、タイトル下線、パンチライン、箇条書きマーカーを01と同じ `accent` へ変更し、closingの線は01と同じ `accent_soft` にした
- スライド個別の強調色47件を `teal` から `accent` へ変更した
- S2の5層図を暖色化し、S13・S33の意味を持たない緑の装飾をテラコッタへ変更した
- 比較・カテゴリ識別・コンテキストそのものを表す図解内のtealは、01にもある意味色として維持した
- 02の文字量に合わせたlayout数値9件は、収まりを維持するため変更しなかった
- PPTX実物の独立レンダリングで検出したS27・S45のコード末尾クリップを、各スライドの局所style（size 15、line_height 1.18）で解消した

最終検証は `gate_deck OK: 72 slides`、OKF errors 0 / warnings 0、リンクテストOK、PPTX ZIP正常、deck.json/PPTX/PDF/PNGすべて72枚、notes 0、画像crop 0、スライド外shape 0。LibreOfficeから1921×1080 PNGへ再変換した全72枚を独立担当が通覧し、問題なし。最終PPTX SHA-256は `5f7728a9e9e62e2fa97ac8e8c9bbca5af370fdadf6b0cb8e4b73a6bfffbe57fe`。

`meta.id` と生成PPTX名は `ai-eng-02-context-engineering-v2` のままで、現行ディレクトリ名は `02-context-engineering`。`gate_deck.sh` は2026-08-20の整理時に `meta.id` を参照する方式へ更新され、番号付きディレクトリから直接検証できる。

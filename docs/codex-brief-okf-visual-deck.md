# Codex 向け指示書: OKF ビジュアルデッキ「okf-visual」の作成

## 0. ゴール

社内勉強会向けに、**OKF (Open Knowledge Format) を解説するビジュアル重視のスライドデッキ**を作成する。

- あなた（Codex）の担当: **ImageGen（Image2）で挿絵画像を生成**し、それを組み込んだ `deck.json` を作成すること
- こちら（Claude Code / ユーザー）の担当: ビルド（HTML / PPTX 生成）と最終検証。あなたはビルドを実行しなくてよい

既存のテキスト中心デッキ `decks/okf-knowledge-share/`（20枚）が内容の正。これを**上書きせず**、姉妹版として新デッキを作る。

## 1. 前提情報

- リポジトリ: `~/Projects/presentation/`。作業ルールは `AGENTS.md`、スキーマの正は `docs/deck-schema.md`
- OKF の内容はリポジトリの `knowledge/okf/` に OKF 形式で蓄積済み。読める場合はそれが一次情報。読めない環境の場合に備え、**本指示書 §7 に必要なファクトを収録済み**（§7 にない事実を書かないこと）
- スライドは 16:9、仮想キャンバス 1280×720px。テーマは「accenture-purple」（§6 参照）

## 2. 成果物（この2種以外を作らない・変えない）

1. `decks/okf-visual/assets/fig-01〜fig-08.png` — ImageGen で生成した挿絵 8 枚（§5）
2. `decks/okf-visual/deck.json` — 21枚構成のデッキ定義（§4）

**変更禁止**: `decks/okf-knowledge-share/` ほか既存デッキ、`tools/`、`templates/`、`knowledge/`（今回の作業では読み取りのみ）、`build/` 配下すべて。

## 3. deck.json の書き方（要約）

```jsonc
{
  "meta": {
    "id": "okf-visual",            // フォルダ名と一致させる
    "title": "OKFビジュアルガイド",
    "subtitle": "図解で分かる Open Knowledge Format",
    "author": "Yuya Fujita",
    "date": "2026-08",
    "theme": "accenture-purple"
  },
  "slides": [ /* §4 の順に */ ]
}
```

使用できるスライドタイプ（詳細・全オプションは docs/deck-schema.md）:

- `title`: `{ "type": "title", "title", "subtitle", "meta" }`
- `section`: `{ "type": "section", "number": "01", "title", "subtitle" }`
- `bullets`: `{ "type": "bullets", "title", "lead"?, "bullets": [文字列 or { "text", "children": [...], "bold"? }] }`
- `two_column`: `{ "type": "two_column", "title", "left": { "heading", "bullets" }, "right": {...} }`
- `table`: `{ "type": "table", "title", "columns": [...], "rows": [[...]], "style"?: { "table": { "row_h", "cell_size", "col_widths" } } }`
- `image`: `{ "type": "image", "title", "path": "assets/fig-01-xxx.png", "caption" }` — 画像は 1136×440px の領域に等比で収まる（アスペクト比は自由）
- `quote` / `closing`: okf-knowledge-share/deck.json を参照

全スライドに `notes`（発表者用メモ、日本語）を付けること。**PPTX へのノート出力はビルダー側で自動的に抑止されるので、deck.json に書いてよい**。

## 4. スライド構成（21枚、この順で）

| # | type | 内容 | 図版 |
|---|------|------|------|
| 1 | title | OKFビジュアルガイド | — |
| 2 | section | 01 OKFとは何か | — |
| 3 | image | 課題：コンテキスト断片化（caption で「知識が Wiki・ドライブ・頭の中に散在し、AIが読めない」ことを説明） | fig-01 |
| 4 | bullets | OKFの正体（§7-A） | — |
| 5 | image | OKFのイメージ：共通の「知識の書き方」（caption で Markdown+frontmatter の共通形式であることを説明） | fig-02 |
| 6 | table | 設計の3原則（§7-B。okf-knowledge-share の同スライドを流用してよい） | — |
| 7 | section | 02 仕様の要点 | — |
| 8 | image | バンドル＝ファイルの木構造（caption でパスがID、index.md が入口と説明） | fig-03 |
| 9 | bullets | 覚えることは4つだけ（§7-C） | — |
| 10 | image | v0.2：知識に根拠を付ける（caption で「出所・信頼性・鮮度・状態・検算」の5観点と説明） | fig-04 |
| 11 | table | v0.2 の5フィールド（§7-D） | — |
| 12 | image | 人間とAIの二重チェック（caption で generated / verified の分離と3段階判定を説明） | fig-05 |
| 13 | bullets | Attested Computation（§7-E） | — |
| 14 | section | 03 エコシステム | — |
| 15 | image | エコシステムの地図（caption で MCP=接続 / OKF=中身 / llms.txt=場所 の住み分けを説明） | fig-06 |
| 16 | table | 他標準との関係（§7-F） | — |
| 17 | section | 04 実践 | — |
| 18 | image | 「OKF brain」を育てる（caption で Marie Haynes 氏の実例＝取り込み→承認→蓄積のループを説明） | fig-07 |
| 19 | two_column | 運用のコツと注意点（§7-G） | — |
| 20 | image | 小さく始めて育てる（caption で スモールスタート→AIに整理を任せ人間が確認 と説明） | fig-08 |
| 21 | closing | まとめ（§7-H）+ message「次回：自分の担当領域を1ファイル OKF 化するハンズオン」 | — |

## 5. 画像（ImageGen）の要件 — 最重要

8枚すべて ImageGen（Image2）で生成し、`decks/okf-visual/assets/` に `fig-01-fragmentation.png` のような連番+スラッグ名で保存する。

- **画像内に文字を入れない**（日本語は崩れる。事実・説明はすべてスライド側の title / caption / bullets で伝える）。どうしても必要なら「OKF」「AI」程度の短い英字のみ
- **横長で生成**（表示領域が 1136×440 の横長のため。1536×640〜1536×1024 推奨。極端な縦長は不可）
- **8枚でスタイルを統一**する。推奨の共通プロンプト要素:
  - フラットでミニマルなベクター風イラスト（写実・3D・写真風は不可）
  - 配色は白〜薄ラベンダー背景に、深紫 #460073 を主、鮮紫 #A100FF をアクセント（テーマと揃える）
  - ごちゃごちゃさせない。1画像1メッセージ
- 各図版のモチーフ指定:
  - fig-01: 散らばった書類・フォルダ・吹き出しが霧の中でバラバラに浮かび、途方に暮れるロボット（=AIが知識を読めない混沌）
  - fig-02: バラバラだった書類が、同じ形の整ったカード（上部に小さなラベル帯=frontmatter）に揃って並ぶ
  - fig-03: フォルダとファイルの木構造。根元に入口となる1枚（index）が光っている
  - fig-04: 1枚のカードに「出所・確認・鮮度・状態・検算」を象徴する5つのアイコン的マーク（虫眼鏡・チェック・砂時計・信号・天秤など）が付く
  - fig-05: 同じカードを、ロボットと人間が並んで別々のスタンプで確認している
  - fig-06: 中央に知識カードの束、周囲にプラグ（接続）・道しるべ（場所）・ルールブック（運用）が配置された地図風
  - fig-07: 人間の頭部シルエットの中に整理された知識カードが積み上がっていき、外から新しいカードが承認ゲートを通って入る
  - fig-08: 小さな苗木に1枚ずつカードの葉が増えて育っていく
- 生成後、各画像を目視確認し、ごちゃついた画像・文字が浮き出た画像は作り直すこと

## 6. テーマトークン（deck.json では色名で指定。hex 直書きしない）

`primary` #460073 / `accent` #A100FF / `text` #1B1B24 / `muted` #6E6E7E / `surface` #F7F0FC / `background` #FFFFFF

## 7. コンテンツのファクトシート（この範囲の事実だけを使う）

**A. OKFの正体**: Google Cloud が 2026年6月12日に公開したオープン仕様。組織の知識を「Markdown + YAML フロントマター」で書く共通形式。プラットフォームではなくフォーマット（SDK不要・ベンダー非依存・Gitで管理できるただのテキスト）。人間もAIも読み書きできる。発端は Andrej Karpathy 氏の先行的な取り組みを Google が仕様化したと紹介されている。

**B. 設計の3原則**: ①制限の最小化（必須は type のみ。type の値や構成は書き手が決める）②書き手と読み手の独立（人が書いた知識をAIが読める、AI生成の知識を別のAIがクエリできる）③プラットフォーム非依存（ファイルだけで成立）。

**C. v0.1の骨格（4つ+1）**: ①1コンセプト=1ファイル、ファイルパスがID ②frontmatter 必須は type のみ（description がAIの「開くか」の判断材料）③予約ファイルは index.md（目次・段階的開示の入口）と log.md（変更履歴）④関係は相対パスの Markdown リンクで表現。＋寛容な消費モデル（未知の type・壊れたリンクがあっても読むのを止めない）。

**D. v0.2 の5フィールド**（小文字表記が正）: `sources`（出所。author / usage_count / last_modified を記録）/ `generated`・`verified`（作った人と確認した人を分離記録）/ `stale_after`（絶対日付で陳腐化日）/ `status`（draft / stable / deprecated）/ `type: Attested Computation`（計算式を固定し実行結果を検算）。v0.1 公開から約6週間で改定。必須フィールドは v0.2 でも type のみ。actor 表記は AI が `<producer>/<version>`、人間が `human:<id>`、自動処理が `process:<id>`。verified の3段階判定: なし=未確認 / 機械のみ=機械確認済み / human あり=人間確認済み。

**E. Attested Computation**: 会社の計算式をファイルとして固定し、AIに許されるのは宣言済みパラメータへの値入力のみ。実行結果は「レシート」として返り、LLM を使わない決定論的プログラム（attester）が「式が公認のものと一致するか」「表示する数字がレシートと一致するか」の2点を検査。不一致なら表示しない。verified（定義の確認）とは別物で、両方揃って成立する。

**F. 他標準との関係（競合ではなく補完）**: MCP=エージェントとツールの動的接続（OKFは知識の中身の書き方）/ llms.txt=LLM向けに知識の場所を示す（指す先をOKFで書ける）/ AGENTS.md・CLAUDE.md=リポジトリ運用ルールの伝達（このパターンを一般化・標準化したのがOKF）/ OSI (Open Semantic Interchange)=BIメトリクスの共通定義で40社超が推進、OKFとは「数字の定義」と「AIへの知識の受け渡し」で住み分け（解説動画の見解）。Google は仕様書 SPEC.md・BigQuery用拡充エージェント・ビジュアライザー・サンプルバンドル3種（GA4 / Stack Overflow / Bitcoin）を GitHub（GoogleCloudPlatform/knowledge-catalog）で公開。

**G. 運用のコツと注意点**: 【コツ】スモールスタート（FAQ・オンボーディング資料など1テーマから）/ 整理作業自体をAIに任せ人間は確認だけ / 骨組み→肉付けの順でよい（壊れたリンク許容の設計）/ 運用ルール（CLAUDE.md）とドメイン知識（OKF）の分離。【注意】AIの整理結果の目視確認を省かない / type の作りすぎは失敗パターン / 出所不明バンドルはプロンプトインジェクションのリスク（素性の分かるものだけ読ませる）/ 機密データの共有範囲確認。実例として SEO 専門家 Marie Haynes 氏が個人ナレッジベース「OKF brain」を運用（URL を渡す→エージェントが実行計画提示→人間が承認→書き込み、毎日 GitHub バックアップ、playbook 化で数日の分析が即座に）。

**H. まとめ**: 課題=知識の散在（コンテキスト断片化）がAI活用のボトルネック / OKF=Markdown+frontmatterの知識フォーマット、プラットフォームではない / v0.1の骨格は4つだけ、v0.2は「出所・信頼性・鮮度・状態・検算」の語彙を追加 / 先行事例に学ぶ（承認フロー・スモールスタート・バックアップ・出所確認）。

## 8. 品質チェックリスト（提出前に自己確認）

- [ ] `deck.json` が valid な JSON で、meta.id が `okf-visual`、theme が `accenture-purple`
- [ ] スライドが §4 の21枚構成どおり、全スライドに日本語の `notes` がある
- [ ] 画像8枚が assets/ にあり、deck.json の `path` と一致、横長、文字なし、スタイル統一
- [ ] 本文・caption の事実が §7 の範囲内（§7 にないことを書いていない）
- [ ] 色の hex 直書きをしていない（テーマトークン名のみ）
- [ ] 既存ファイルを一切変更していない

## 9. 完了報告の形式

作成したファイル一覧（パス）と、図版8枚それぞれの一行説明（何をどう描いたか）を報告する。ビルドと最終検証（HTML / PPTX 生成、プレビュー確認）はこちらで実施するので不要。

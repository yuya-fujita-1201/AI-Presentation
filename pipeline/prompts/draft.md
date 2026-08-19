# 工程: draft — スライド原稿の執筆（チェックポイント方式）

## 入力

- ナレッジ一覧: `{{KNOWLEDGE_LIST_FILE}}`（完成済みコンセプト群。**これが唯一の内容ソース**）
- 原稿ファイル: `{{DRAFT_FILE}}`（現在 {{CURRENT_BLOCKS}} ブロック）
- 枚数: **{{SLIDES_MIN}}〜{{SLIDES_MAX}}枚**
- 品質手本: `decks/07-okf-visual-guide/deck.json`（35枚・image_text 19枚の構成比・1枚1メッセージの粒度）
- **ユーザーレビューの学び: `{{FEEDBACK_FILE}}`（存在する場合は必読。ここに書かれた構成・文章・実用性・図版の方針を最優先で反映する）**
- 読者像: 新入社員＋ITコンサル・SE（チャットAI経験あり・エージェント未経験）。発表30〜60分・超初心者向け

## 形式（1枚=1ブロック・厳守。機械ゲートがgrep照合する）

```
## SLIDE 07 | type: image_text | side: right
- title: 良いプロンプトの3要素
- punch: 指示・文脈・出力形式。この3つで結果が変わる
- bullets:
  - 指示: 何をしてほしいかを動詞で言い切る
  - 文脈: 前提・対象読者・制約を渡す
- figure: 3つの箱がロボットに流れ込み1つの答えが出る図
- caption: 3要素がそろって初めて意図が伝わる
- notes: （話し言葉の原稿。1枚30秒〜1分ぶん）
```

- type は `title / section / bullets / two_column / table / code / quote / image / image_text / closing` のみ
- **全スライドに `- title:`（quoteを除く）と `- notes:` が必須**
- image_text には `- punch:` `- figure:` `- caption:` が必須。**image_textを全体の4割以上**にする
- figureは「何をどう図解するか」を具体的に書く（後工程でCodexがこの記述から挿絵を描く。画像内に文字は入れない前提で設計）
- 構成: 表紙(title)→問題提起→概念→実践→注意→まとめ(closing)。章扉(section)で息継ぎを入れる

## 手順

- `{{DRAFT_FILE}}` が空の場合（初回）: ナレッジ全ファイルをReadし、**ヘッダ行だけの枚割り表**（全枚数分の `## SLIDE NN | type: ...` 行）を書き、続けて前半ブロックの中身を埋める
- 既にある場合: 中身が空のブロックを先頭から埋めていく（ヘッダ行の構成変更は最小限に。枚数レンジは守る）
- **内容規則: ナレッジにない主張・数値・固有名詞を書かない**。auto字幕のみが根拠のhigh主張（定義・数値・仕様・可否）はスライド本文に書かず、notesで帰属＋（聞き取り）として扱う
- 1枚1メッセージ。箇条書きは7行以内・1行40字以内を目安
- 45分で終わらない前提。キリの良いところで `succeeded_partial` 終了可

## 出力（outbox）

- metrics: `{"progress": 中身の埋まったブロック数, "data": {}}`

## 許可パス（書き込み）

- `{{DRAFT_FILE}}`・`{{OUTBOX_PATH}}`・`{{RUN_LOG_PATH}}` のみ

# Codex 作業依頼書（軽量版）：プロンプトエンジニアリング勉強会デッキの「たたき台」制作

- **依頼日**: 2026-08-13
- **依頼元**: Claude Code（自律パイプラインがリサーチ済み。ナレッジ整理・正式版は別レーンで進行中）
- **あなたの担当**: 収集済み素材から**スライドのたたき台（ドラフトデッキ）を新規作成**し、ビルド検証まで
- **作業場所**: `decks/ai-eng-01-pe-draft/` を**新規作成**（既存フォルダには一切触れない）

## 1. 背景と位置づけ

社内勉強会「AIエンジニアリングシリーズ」第1弾（読者: チャット型AI経験のみの新入社員〜SE。30〜60分のカジュアル発表）。

自律パイプラインが同テーマの**品質保証版**を `decks/ai-eng-01-prompt-engineering/` に別途生成する予定（採点ループ込み・数日後）。本依頼はそれを待たずに早出しする**たたき台レーン**。つまり: 完璧さより「発表の流れが見える状態」を最速で。ただし**素材にない主張・数値を創作しない**ことだけは厳守。

## 2. まず読むもの

1. 本ファイル全体
2. `AGENTS.md`（ビルド・検証手順）と `docs/deck-schema.md`（deck.jsonスキーマ）
3. 下記素材（§3）

## 3. 素材（これだけから作る）

**動画ソース台帳 5本**（`knowledge/sources/`。各台帳末尾に**タイムスタンプ付き主張テーブル**あり——これがスライドの主材料）:

- `video-pe-opus-5-prompt-tips.md` — Opus 5のプロンプトのコツ
- `video-pe-opus-5-benchmark-tips.md` — Opus 5ガイド＋プロンプト術
- `video-pe-five-engineering-stages.md` — **5段階（プロンプト→コンテキスト→ハーネス→ループ→グラフ）の全体地図**
- `video-pe-loop-engineering-overview.md` — 「プロンプトを書くな」の文脈（プロンプトの先の世界）
- `video-pe-loop-engineering-5plus1-parts.md` — ループEG解説（同上の補強）

**Web検証済みソース 7件**（記事台帳は未整備。必要ならURLを直接参照してよい。ローカルに原文抜粋キャッシュあり: `pipeline/cache/web/*/candidates.json`）:

- [primary] https://arxiv.org/abs/2406.06608 — The Prompt Report（体系サーベイ）
- [primary] https://arxiv.org/abs/2402.07927 — Prompt Engineering survey
- [official] https://platform.claude.com/docs/en/build-with-claude/... — Prompting best practices / Prompting Claude Opus 5（2本）
- [jp] KDDI・Qiita・SIOS の入門解説（3本。URL は `pipeline/state/research-queue.json` の web.candidates 参照）

## 4. 作るもの

1. `decks/ai-eng-01-pe-draft/deck.json` — **20〜30枚のたたき台**
   - meta: `id: ai-eng-01-pe-draft` / `theme: accenture-purple` / `date: 2026-08-13`
   - 構成の指針: 表紙 → つかみ（「プロンプトを書くな」と言われる時代に、なぜ今さらプロンプト？→ 5段階の地図で位置づけ）→ PEの基本（指示・文脈・出力形式・few-shot・反復・制約 の基礎6概念）→ Anthropic公式ベストプラクティスの要点 → 日本語実務のコツ → よくある失敗 → まとめ＋次回予告（第2弾コンテキストエンジニアリング）
   - `image_text` タイプを積極的に使う（手本: `decks/okf-visual-v2/deck.json` の構成比）
   - 全スライドに `notes`（話し言葉・1枚30秒〜1分）。**notesはHTML専用でPPTXに入らない仕様——python-pptxのnotes_slideを絶対に操作しない**（Keynote互換性破壊）
2. 挿絵は**プレースホルダでよい**（`pipeline/templates/placeholder-4x3.png` を `assets/` にコピーして参照）。本気の挿絵制作は清書フェーズで別依頼する
3. ビルド検証: `python3 tools/build_deck.py decks/ai-eng-01-pe-draft` → `unzip -t`（PPTX）→ python-pptxで `Presentation()` 再パース → `python3 tools/preview_deck.py decks/ai-eng-01-pe-draft` で全枚PNG化 → 文字あふれ・はみ出しがないか目視確認

## 5. ルール

- 色はテーマトークンのみ（hex直書き禁止）。デザイン微調整は各スライドの `style` 差分で
- **素材にない主張・数値・固有名詞を書かない**。動画由来の主張は「〜としている」と帰属し、台帳に「（聞き取り）」注記がある内容は断定しない
- 出典スライドを1枚入れる（動画5本＋主要Web記事のタイトル列挙）

## 6. 変更禁止（絶対に触らない）

- `decks/ai-eng-01-prompt-engineering/`（パイプライン本流の予約領域）およびその他の既存 `decks/*`
- `knowledge/` 配下すべて（読むのは自由・書くのは禁止）
- `pipeline/` 配下すべて（読むのは自由・書くのは禁止）
- `tools/`・`templates/`

## 7. 完了チェックリスト（未実施は未実施と正直に書く）

- [ ] deck.json 20〜30枚・全枚notes付き
- [ ] build成功（HTML+PPTX）／unzip -t OK／Presentation()再パースOK／notes_slide 0件
- [ ] preview全枚PNG生成・目視で文字あふれなし
- [ ] 素材外の主張が混入していないこと（出典スライドと台帳の突き合わせ）
- [ ] 完了報告: 生成物パス・枚数・検証結果を簡潔に

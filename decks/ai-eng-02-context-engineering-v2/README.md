# ai-eng-02-context-engineering-v2（正本）

「コンテキストエンジニアリング超入門」の最終版です。2026-08-14〜15 に Claude 作業版を統合し、GPT Proの4回のレビュー指摘を反映したうえで、Codex による内容監査・全72枚の目視確認・PPTX検証を行いました。

## 正本と生成物

- ソース・オブ・トゥルース: `deck.json`
- 人間向けHTML: `build/ai-eng-02-context-engineering-v2.html`
- PowerPoint: `build/ai-eng-02-context-engineering-v2.pptx`
- PNGプレビュー: `build/preview/slide-01.png` 〜 `slide-72.png`
- GPT Proレビュー: `GPT-Review.md`、`GPT-Review02.md`、会話内の追加レビュー2回
- Codex確認記録: `CODEX-Review.md`、`CODEX-Review02.md`、`CODEX-Review03.md`、`CODEX-Review04.md`（最終版）

## 構成

- 1〜10枚目: 導入・第1章
- 11〜20枚目: 第2章 基礎編
- 21〜31枚目: 第3章 応用編・トラブルシューティング
- 32〜36枚目: 第4章 事例とまとめ
- 37〜72枚目: 付録・出典

## 更新ルール

今後の修正は、このフォルダの `deck.json` と `assets/` に行い、ビルド・全スライド目視・PPTX検証まで完結させます。`build/` は生成物なので直接編集しません。

次の2つは比較・履歴用であり、最新版の編集元にはしません。

- `decks/ai-eng-02-context-engineering/`: 旧版
- `.claude/worktrees/ce-slide9-newhire-vs-veteran/decks/ai-eng-02-context-engineering/`: Codex再監査前のClaude統合版

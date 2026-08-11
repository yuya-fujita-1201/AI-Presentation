---
type: Guide
title: スライド微修正のワークフロー
description: 元のデザインを維持したまま、位置・サイズ・フォント・色を素早く直す実務手順。よくある修正の具体例つき
tags: [slides, workflow, micro-edit]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T17:30:00+09:00"
---

# スライド微修正のワークフロー

## 基本ループ（1修正あたり数十秒）

1. `decks/<デッキ>/deck.json` の該当スライドを開く
2. **内容の修正**ならテキストを、**デザインの微修正**なら `style` に差分を書く（既定値は `templates/layouts/default.json` 参照）
3. `python3 tools/build_deck.py decks/<デッキ> --html` （HTML だけなら一瞬）
4. `python3 tools/preview_deck.py decks/<デッキ> <スライド番号>` で該当スライドの PNG を目視確認
5. 納得したら `python3 tools/build_deck.py decks/<デッキ>` で PPTX も再生成

再生成しても**他のスライドは1バイトも変わらない**（決定論的ビルド）ので、デザイン崩れの心配なく1箇所だけ直せる。

## よくある修正の書き方

| やりたいこと | 書く場所 | 例 |
|-------------|---------|-----|
| 5枚目のタイトルを少し下げる | 5枚目の `style` | `"style": { "title": { "y": 50 } }` |
| この箇条書きだけ文字を小さく | 該当スライドの `style` | `"style": { "body": { "size": 21 } }` |
| 特定の1行だけ強調 | bullets の項目 | `{ "text": "...", "bold": true, "color": "accent" }` |
| 表の列幅を 3:3:6 に | 該当スライドの `style` | `"style": { "table": { "col_widths": [3, 3, 6] } }` |
| 表の行が窮屈 | 該当スライドの `style` | `"style": { "table": { "row_h": 70 } }` |
| デッキ全体で本文を小さく | `meta.layout_overrides` | `{ "bullets": { "body": { "size": 22 } } }` |
| ブランド色を変える | `meta.theme` | `"theme": "accenture-purple"` |
| 全デッキ共通の見た目変更 | `templates/layouts/default.json` | 既定値そのものを編集 |

## ルール

- **生成物（build/ 配下）は絶対に直接編集しない**。直したくなったら必ず deck.json に戻る
- 微修正の依頼を受けた AI は、スライドを再生成せず**差分パラメーターだけを書く**こと（このリポジトリの CLAUDE.md にも明記）
- 色の指定はテーマトークン（`primary` / `accent` / `muted` など）を使う。hex 直書きはそのスライド固有の特例のみ
- 修正が3スライド以上に及ぶ場合は、個別 `style` の重複を疑い、`meta.layout_overrides` か レイアウト既定値への昇格を検討する

## 修正依頼の書き方（人間→AI）

「◯枚目の△△を□□にして」で足りる。例:

- 「9枚目の表、1列目をもう少し狭くして」
- 「まとめスライドの箇条書きを1行減らして、その分フォントを大きく」
- 「全体的にリード文が大きい気がするので 18px に」

AI は該当パラメーターの変更 → ビルド → 該当スライドのプレビュー確認までを1ループで行う。

# Citations

- [設計思想](./parameter-driven-slides.md)
- [仕組みの構造](./architecture.md)

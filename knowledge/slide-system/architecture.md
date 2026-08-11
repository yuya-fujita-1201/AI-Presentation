---
type: Concept
title: スライドシステムの構造
description: deck.json → HTML / PPTX ビルドパイプラインの実装構造。3層のスタイル解決、px 座標系、96dpi 換算による両形式の一致
tags: [slides, architecture, html, pptx, python]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T17:30:00+09:00"
---

# スライドシステムの構造

## 全体像

```
deck.json（内容 + 差分スタイル）
templates/themes/<名前>.json（色トークン・フォント）
templates/layouts/default.json（タイプ別の全領域の既定値）
        │
        ▼  tools/build_deck.py
   ┌────┴────┐
   ▼         ▼
 HTML      PPTX        ← 同じ解決済みパラメーターから生成
（確認用）  （配布用）
   │
   ▼  tools/preview_deck.py（Playwright）
 PNG（スライド単位の目視確認）
```

## 座標系: 仮想キャンバス 1280×720px

- すべての位置・サイズ・フォントを px で指定する（16:9）
- HTML はそのまま absolute 配置、PPTX は **96dpi 換算**（px÷96 = インチ、px×0.75 = pt）
- 1280÷96 = 13.333 インチ、720÷96 = 7.5 インチで PowerPoint の 16:9 と正確に一致するため、**HTML と PPTX の見た目がほぼピクセル単位で揃う**

## スタイル解決の3層（後勝ち deep merge）

1. `templates/layouts/default.json` — スライドタイプごとに「領域」（title / rule / lead / body / table など）の既定値を定義
2. `deck.meta.layout_overrides` — そのデッキ全体での調整
3. `slides[i].style` — スライド個別の微修正

各領域のプロパティ: `x` `y` `w` `h`、`size`、`color` / `fill`（テーマトークン名 or hex）、`bold`、`align`、`line_height`、`gap` など。箇条書きは項目単位でも `size` / `color` / `bold` を上書きできる。

## 実装上の要点

- 色は必ずテーマトークン経由で解決する（`col(theme, name)`）。これにより `meta.theme` の1行でブランド一括切替が効く（default = ネイビー、accenture-purple = パープル）
- コードスライドの自動縮小（収まらない場合にフォントを `min_size` まで下げる）は HTML / PPTX で共通の関数を使い、両形式の挙動を一致させる
- PPTX のテキストボックスは内部マージンを 0 にして HTML の座標と揃える。日本語フォントは East Asian フォント（`a:ea`）まで明示設定する
- **スピーカーノートは PPTX に出力しない**（python-pptx の notes_slide は Keynote 互換性を壊す既知問題）。ノートは HTML の N キー表示のみ
- 検証: PPTX は `unzip -t` + `Presentation()` 再パース + QuickLook（`qlmanage -t`）描画、HTML は Playwright スクリーンショットで行う

## ファイル配置

| パス | 役割 |
|------|------|
| `decks/<名前>/deck.json` | デッキのソース（これだけ編集する） |
| `decks/<名前>/build/` | 生成物（HTML / PPTX / preview PNG）。編集禁止・Git 管理外 |
| `templates/themes/` | テーマ。新ブランドはここに JSON を1つ追加 |
| `templates/layouts/` | レイアウト既定値。全デッキ共通の見た目を変えるときだけ触る |
| `tools/build_deck.py` | ビルダー本体 |
| `tools/preview_deck.py` | スライド単位の PNG プレビュー |

# Citations

- [設計思想](./parameter-driven-slides.md)
- [微修正の実務手順](./micro-edit-workflow.md)
- リポジトリ内の一次情報: `docs/deck-schema.md`（スキーマの正）

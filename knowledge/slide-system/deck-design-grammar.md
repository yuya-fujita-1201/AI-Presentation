---
type: Guide
title: デッキデザイン文法 — コンサル調の統一ルック
description: FEILER 案件デッキ（feiler-hypotheses-ai, 35枚）で確立した「落ち着いたコンサル資料」のデザイン文法。ヘッダー文法・eyebrow・意味を持つ第二パレット・全面SVG図版の規約・layout_overrides の実例
tags: [slides, design, consulting-style, svg, eyebrow, palette]
generated:
  by: claude-code/fable-5
  at: "2026-08-13T20:30:00+09:00"
---

# デッキデザイン文法 — コンサル調の統一ルック

FEILER 案件の顧客提示デッキ `feiler-hypotheses-ai`（35枚、`/Users/yuyafujita/Cytra/FEILER/decks/feiler-hypotheses-ai/`）で、ユーザー指示の積み上げから確立したデザイン文法。default レイアウトのまま作ると「勉強会スライド」寄りの大きめの文字組になるが、この文法を適用すると「落ち着いたコンサル資料」のルックになる。ビルダー機能（eyebrow / row_fills / brand / footer 上書き）は本プロジェクトに移植済み（2026-08-13）。

## 1. ヘッダー文法（全コンテンツページ共通）

上から順に、この 4 点セットを **全ページ同じ座標** で置く。1枚でも崩すと安っぽくなるので厳守する。

| 要素 | 仕様 | 座標の目安 |
|---|---|---|
| eyebrow | 15px・太字・アクセント系の濃色 | y=16 |
| タイトル | **30px**・黒（`text`。`primary` ではない） | y=44, h=46 |
| 罫線 | **全幅 2px**・アクセント色（金） | y=98（SVG 内は y=88）, w=1136 |
| リード文 | 17px・`muted`。**必ず罫線の下** | y=112 |

ポイントは 2 つ。**タイトルを 36px → 30px に絞り黒にする**こと、**罫線を「短い太アクセント」から「全幅の細い 2px」に変える**こと。この 2 つだけでコンサル資料の顔になる。

デッキ全体に適用する `meta.layout_overrides` の実例（feiler-hypotheses-ai より。bullets の例、table / image / two_column も同じ値）:

```jsonc
"layout_overrides": {
  "bullets": {
    "eyebrow": { "color": "#8A692E" },
    "title":   { "size": 30, "y": 44, "h": 46, "color": "text" },
    "rule":    { "w": 1136, "h": 2, "y": 98 },
    "lead":    { "y": 112, "h": 64, "size": 17, "line_height": 1.5 }
  },
  "title": {   // 表紙も控えめに: 帯を少し太く、タイトルは 60→50px で上寄せ
    "bar":      { "w": 18, "fill": "accent" },
    "title":    { "x": 96, "y": 200, "w": 1090, "h": 160, "size": 50, "color": "primary", "bold": true, "line_height": 1.25 },
    "subtitle": { "x": 96, "y": 386, "w": 1040, "h": 110, "size": 24, "color": "muted", "line_height": 1.55 },
    "meta":     { "x": 96, "y": 630, "w": 1040, "h": 28, "size": 16, "color": "muted" }
  }
}
```

## 2. eyebrow — 章・系列の目印

タイトルの上に置く小さなサブタイトル。スライドの `eyebrow` フィールドに書くだけで出る（対応タイプ: bullets / two_column / table / code / image / image_text）。

- **命名規則を系列で固定する**。FEILER では: 説明ページ=「仮説 n」、対応・対比ページ=「仮説 n｜〈仮説名フル〉」、AI ページ=「仮説 n × AI活用」
- **色で系列を分ける**。通常ページは金 `#8A692E`、AI ページだけ青 `#3D6B99`。「この色＝このトラック」を全編で守る（次節）
- ページ単位の色替えは `style.eyebrow.color` で行う

## 3. 意味を持つ第二パレット（「青いしるし＝AI」方式）

テーマの基調色（FEILER では金茶系）に対し、**特定の意味を担う第二パレットを 1 系統だけ**用意し、その意味以外には絶対に使わない。FEILER では「AI に関わる要素＝青」:

| 用途 | 色 |
|---|---|
| 強調要素の背景（ストリップ・カード） | `#EAF1F8` |
| 枠線 | `#9DBBD6` |
| 文字 | `#2F5A85` |
| グラフのバー | `#7FA3C6` |
| eyebrow | `#3D6B99` |

これをスライド本文・表・図版の全部で貫く: AI ページの eyebrow は青、対応表の AI 行は `row_fills` で薄青 `#EAF1F8`、図版内の AI 要素も同じ青系。**読者は色だけで「どこに AI が絡むか」を追える**ようになる。第二パレットを 2 系統以上作ると効果が消える。

表の行ハイライトの書き方:

```jsonc
{ "type": "table", "...": "...",
  "style": { "table": { "row_fills": { "3": "#EAF1F8" } } } }  // 4行目を薄青に
```

## 4. 全面 SVG 図版の規約

いちばん伝えたいページは bullets ではなく **1280×720 の全面 SVG 図版**（`type: "image"` で `style.img` をフルキャンバスに）で作る。feiler-hypotheses-ai は 35 枚中 20 枚が図版ページ。規約:

- **図版の中でも同じヘッダー文法**を使う（eyebrow 15px → タイトル 30px → 金 2px 罫線 x=60, y=88, w=1160 → リード 17px, y=112）。スライドと図版で頭が揃うと全編が 1 つのシステムに見える
- テキストはクラスで型を決めて使い回す。実例の型スケール: `.eyebrow` 15px / `.title` 30px / `.lead` 17px / レーン見出し 17px / ステップ名 12px / 本文 12.5px / キャプション 10.5px。フォントは `"Hiragino Sans", "Yu Gothic", sans-serif`
- **繰り返すモチーフは `<defs>` にシンボル化**して `<use>` で置く（例: 人型アイコン＝頭の円＋ドーム型の肩、単色フラット）。図版ごとに描き直すと絵柄がばらける
- トーンは「**落ち着いたコンサル資料のピクトグラム**」。単色フラット・角丸統一・装飾過多にしない。キャラクター的・漫画的な絵は禁止
- 矢印は `<marker>` を defs に定義して線に付ける。色は muted 系
- **セーフエリア**: 右端 x=1220 まで。全要素がカード枠・レーン枠・スライド端に収まっていることを全数確認する
- 白背景のスライドに載せるので、図版の背景色はテーマの `background`（FEILER では `#FFFDF8`）で塗る

参考にする既存図版のトーンの正: `fig-system-asis.svg` / `fig-system-tobe.svg` / `fig-grand-design.svg`（FEILER の assets 内）。

## 5. その他の統一ルール

- **ブランドマーク**: `meta.brand` に短い表記（例: `FEILER`）を入れると全ページ右上にアクセント色・太字で出る
- **ページをまたぐマーク・番号参照は禁止**。図中の記号は「※1〜※3」方式で図内に意味を書き切る。「文章＋ページ参照」（例:「〜（付録2）」）は OK
- **背景色つきの特別ページを乱発しない**。FEILER では茶背景の section/closing を廃止し、まとめ・付録扉も白背景の標準デザインに統一した
- ページ番号を出したくないスライドは `style.footer_r.text` で表示文字列を差し替える

## 6. 検証の型（デザイン変更のたびに回す）

1. `build_deck.py <デッキ> --html` → `preview_deck.py <デッキ> <番号>` で **PNG を必ず目視**（文字切れ・はみ出し・重なり）
2. PPTX の 3 点検証: `unzip -t` エラーなし／python-pptx 再パースで枚数一致／全スライド `has_notes_slide == False`
3. SVG 図版を直したときは該当ページ全部を PNG で確認（HTML と PPTX で SVG ラスタライズ経路が違うため）

## 関連

- [parameter-driven-slides.md](./parameter-driven-slides.md) — 内容とデザインを分離する考え方
- [architecture.md](./architecture.md) — テーマ / レイアウト / スタイルの3層と座標系
- [micro-edit-workflow.md](./micro-edit-workflow.md) — 微修正の実務手順
- スキーマ: `docs/deck-schema.md`（eyebrow / row_fills / brand / footer 上書きを含む）
- 実例デッキ（原本）: `/Users/yuyafujita/Cytra/FEILER/decks/feiler-hypotheses-ai/`（deck.json の layout_overrides と assets/ の SVG 群が一次資料）

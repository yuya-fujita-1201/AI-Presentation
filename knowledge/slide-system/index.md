# slide-system — パラメーター駆動の資料作成システム

このリポジトリのスライド資料（HTML / PowerPoint）を「JSON パラメーターで管理し、AI の再生成なしに微修正する」仕組みについてのナレッジ。

## 内容

- [parameter-driven-slides.md](./parameter-driven-slides.md) — 考え方。なぜ内容とデザインをパラメーターに分離するのか、動画制作の JSON 管理手法からの応用
- [architecture.md](./architecture.md) — 仕組みの構造。テーマ / レイアウト / スタイルの3層、px 座標系と 96dpi 換算、ビルドパイプライン
- [micro-edit-workflow.md](./micro-edit-workflow.md) — 微修正の実務手順。よくある修正の具体例と確認ループ
- [deck-design-grammar.md](./deck-design-grammar.md) — コンサル調のデザイン文法。ヘッダー4点セット、eyebrow、意味を持つ第二パレット、全面SVG図版の規約（FEILER案件で確立）

## 読む順番

parameter-driven-slides → architecture → micro-edit-workflow の順。実際に編集するときは micro-edit-workflow だけ見れば足りる。

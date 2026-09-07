# 一次資料と教材の対応

2026-09-07確認。現行仕様をWebで読み、既存デッキの固定版を維持した。教材の効果を実測したものではない。

| 主張・説明 | 一次資料 | 確認範囲 |
|---|---|---|
| OKF、知識ファイル、バンドルの定義 | https://raw.githubusercontent.com/GoogleCloudPlatform/open-knowledge-format/main/SPEC.md | v0.2 冒頭・§2〜4：説明欄と本文、ファイル一式。実行基盤を指定しない |
| type、title、description、目次 | 同上 §3〜4・8 | 通常の知識ファイルはtype必須。目次・履歴は任意で、この研修では採用 |
| sources、generated、verified、status、stale_after | 同上 §5・7 | 出典・作成・照合記録、状態、見直しの情報。承認/正しさの自動保証ではない |
| 再現用の既存照合版 | https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md | 元デッキから保持。現行URLと区別 |
| Claude Codeのプロジェクト指示 | https://code.claude.com/docs/en/memory | 2026-09-07公式ページ参照。実行権限の強制機構とは区別 |
| 役割分担、確認手順、演習、比較評価 | 本教材の運用提案 | 仕様の必須要件や実測結果として扱わない |

新規図版は教材の説明構造をSVG化したもの。製品画面や実際のAI出力ではない。AI-Presentationのcontent-guide/diagram-guideから、1枚1メッセージ、主経路と意味の保持、機械検査と意味確認の分離を参考にした。レンダラ移植は行っていない。

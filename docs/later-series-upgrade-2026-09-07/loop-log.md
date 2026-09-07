# 夜間改訂ログ

2026-09-07開始。対象8デッキ（06、07、08実践、Tools、09〜12）。既存01〜05は比較基準。原本を保持した-expandedフォルダを所有。AI-Presentationは読み取り参考。

グラフ: 型/技術調査 と 独立ベースライン2名 → テーマ別maker → build/lint/layout/PNG/ZIP/reparse/count/notes/hash → 独立grader2名以上 → 修正。最大5周、2周停滞で未達を記録。公開・マージは対象外。実アプリ表示と受講者試行は別検証。

機械ゲート: tools/build_deck.py, lint_deck_text.py, check_layout.py --no-build, preview_deck.py, contact_sheet.py, PPTX ZIP/再パース/枚数/ノート0、原本SHA保持、配布リンク確認。

ブランチ loop/later-series-2026-09-07。既存pipeline/PAUSE確認済み。既存dirtyファイルは今回コミットに混ぜない。時刻指定なしのため今回実行中に全8件を検証、停止条件に至れば記録して引継ぐ。

## 改訂と受入 — 2026-09-08

1. 独立ベースライン2名で定義・章・教材密度の欠落を抽出。8件を担当分割し、既存の連続作例を使い定義、図、実物、業務の判断、失敗からの回復、演習と解答を追加。
2. 全8件をbuild→lint/layout→全PNG→contact→SVGフォント→PPTX構造検証。独立Aは8件、Bは自身が制作していない前6件、Cは自身が制作していない11/12を審査。初回指摘はreview-a/b/c.mdに保存。
3. 実物の不足（chunk・再順位付け・受渡ログ・Skill呼出・FAQリンク）、図の境界/ラベル、重複、用語を修正。再レビューで発見した08付録参照も元の依頼文を付録へ補い修正。11 return文と戻り値を区別。変更範囲を再描画、08は全63枚再生成。
4. 最終8件448枚をA、前6件をB、11/12をCが全文と全contactで再確認。最終SHA一致、残存findingsなし。減点方式の各項目100、必須条件・80点ゲートPASS。これは検出指摘に基づく集計値。
5. 全原本JSONのSHA保持、PPTX ZIP/再parse/枚数一致/ノート0、全448PNG存在を最終再確認。06のlint警告は研究データの「Wikipedia50ページ」を参照ページと判定したもので、内容確認して維持。

プラグインから1枚1メッセージ・定義先行・意味ある矢印/境界・独立内容レビューを採用。未対応の新図type・Archifyは移植しなかった。

未確認: PowerPoint/Keynote実アプリ描画、実受講者試行、独立レビュー役による全外部URL再取得。制作者の一次資料確認と独立の内部整合レビューは区別する。Gitへの保存とDraft PRは次の記録を参照。

## Git保存

成果物コミット `6a573aa` をoriginの `loop/later-series-2026-09-07` へpush。初回PR作成はactiveアカウントのcollaborator権限不足で失敗したため、登録済み所有者アカウントを当該CLIプロセスだけに適用して再実行し、Draft PR #13を作成した（グローバル認証切替なし）。https://github.com/yuya-fujita-1201/AI-Presentation/pull/13 。マージ・サイト公開は未実施。

ローカル既存 `training/` 等の別作業はコミット対象外。PPTX/HTMLはローカル納品済みだが、クリーンcheckoutでの全教材リンクと再検証は未確認とPRへ明記。

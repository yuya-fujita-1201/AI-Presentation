# Codex 再レビュー記録（GPT-Review02対応）

対象: `decks/02-context-engineering/`  
実施日: 2026-08-15  
最終判定: 合格（重大0件・中0件・軽微0件）

## 1. GPT-Pro再レビューへの対応

- S6・S8・S12・S20・S27・S36と関連図版で、3経路を「①自動ロード → ②必要時に取得 → ③今回渡す」に統一
- S16・S50・S54で、メモリを情報の保存方式・供給源として説明し、自動ロードと必要時取得の両方になり得ることを明示
- S13・S18・S20・S22・S36で、「短く毎回必要な情報」と「大きい・詳細・時々必要な情報」を分け、後者を必要時の参照先へ置く基準に統一
- S15で、Claude CodeのCLAUDE.mdに対する200行未満の運用目安と、auto memoryのMEMORY.md先頭200行／25KBという開始時ロード上限を分離
- S15の「増やすほど効かなくなる」を「増やしすぎると遵守されにくい／効きにくくなる場合がある」へ修正
- S7で、プロンプトエンジニアリングを含むという関係を本資料上の整理と明示し、権限・フック・承認は対象外とした
- S23で、不要情報や競合情報が増えた場合の傾向としてcontext rotを説明し、関連情報の追加で改善する場合もあると限定
- S33の「最後に書くと効きやすい」を撤回し、必要な出力項目を独立して明記する説明へ変更
- S35を「ルール化を検討する目安」に統一
- S36で、コンテキスト整備の効果とガードレール整備の効果を分離し、行動喚起を「ルール・スキル・参照資料のどこに置くか見直す」へ変更
- S12の表現を「保証が必要な制御は実行環境へ」に変更

関連SVGも同じ説明へ更新した。

- `assets/diagram-context-three-tiers.svg`
- `assets/diagram-three-places-map.svg`
- `assets/diagram-rule-categories.svg`
- `assets/diagram-window-memory.svg`
- `assets/diagram-pe-ce-scope.svg`

## 2. 公式情報との照合

- [Claude Code memory docs](https://code.claude.com/docs/en/memory)で、CLAUDE.mdはセッション文脈であり強制設定ではないこと、簡潔な指示が推奨されること、auto memoryのMEMORY.md先頭200行／25KBとトピックファイルの必要時参照を再確認
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)で、長い文脈に不要・競合情報が増えた場合のcontext rotの説明を再確認

## 3. 独立内容監査

初回監査では、付録S50・S54に「メモリ＝必要時取得だけ」と読める自己矛盾、S15に過剰な断定、S6に旧い経路順が残っていることを検出した。本文・ノート・使用SVGを修正して再監査した。

再監査結果:

- 重大: 0件
- 中: 0件
- 軽微: 0件
- GPT-Review02の残課題: なし
- 新たな矛盾・過剰断定・出典不整合: なし

## 4. 視覚確認

全72枚のPNGを独立レビューし、文字切れ・重なり・表のはみ出し・画像／キャプションの不整合・低コントラスト・ページ番号異常・文字化けがないことを確認した。

内容監査後に変更したS6・S15・S27・S50・S54は原寸で再確認し、S50のSVG内文言とS54の長いタイトルを含めて、新たな崩れがないことを確認した。全PNGは1280×720。

## 5. ビルド・PPTX検証

- `bash pipeline/bin/gate_deck.sh decks/02-context-engineering`: `gate_deck OK: 72 slides`
- `unzip -t`: 圧縮データのエラーなし
- deck.json: 72枚
- python-pptx再パース: 72枚
- PNGプレビュー: 72枚、全て1280×720
- `has_notes_slide == False`: 全72枚
- 参照アセット: 33種類、欠落0
- SVG XML検証: エラーなし
- PPTXテキストのプレースホルダー検査: 該当なし
- OKF検証: errors 0 / warnings 0

## 6. 最終成果物

- `deck.json` SHA-256: `289063b9cc137d9d817860091b590e65a91aba0aca5a809ab6260b1a55999143`
- HTML SHA-256: `5e72d7fd910083e54f78bd196546052b4af302c3f463d8a7d0b11d79f8fdf0df`
- PPTX SHA-256: `e14db9fc7c94daf343be2ab988be3a7e1c26966ec5fe4e279c2cd1d8164127c1`

今回の修正後も正本は `deck.json` であり、`build/` は同ファイルから再生成した成果物である。

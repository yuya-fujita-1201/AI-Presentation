# Codex 最終レビュー記録（追加GPTレビュー対応）

対象: `decks/02-context-engineering/`  
実施日: 2026-08-15  
入力: 会話内で受領したGPT Proの追加レビュー  
最終判定: 合格（重大0件・中0件・軽微0件）

## 1. 追加GPTレビューへの対応

- S24を、まず製品の表示・ログでロードを確認し、その後に長さ・曖昧さ・競合を疑う手順へ修正
  - Claude Codeでは`/context`のMemory filesでロード状況を確認
  - より詳細な確認手段として`InstructionsLoaded` hookを記載
  - 「具体的な指示が競合時に優先される」という含意を外し、矛盾時には一方が恣意的に選ばれる場合があると明示
- S18・S30と関連SVGで、Claude Code Skillsの段階的な読み込みを明確化
  - frontmatterの`description`は通常あらかじめコンテキストに入る
  - `SKILL.md`本文は自動判定または明示呼び出し時に入る
- S32を「短いレビュー方針はルール、長い規約本文は参照先」へ修正し、S9の原則と統一
- 「経路」と「置き場所・供給源」を分離
  - S18: 「スキルという取得の仕組み」
  - S20: 「どの経路で入れるか早見表」
  - S22: 「どの経路で入ったかを疑う」
  - S70: 「情報供給の3経路」
- S31の章扉を「コードレビューの改善例3つ＋安全上の境界事例1つ」へ修正
- S34・S42で、文章による安全上の方針と、権限・hook・承認による強制境界を分離
- S7・S29・S33・S41・S51の細かな断定・用語・ノート表現を修正
- S26を「技術者向け発展例」と明示
- S71の出典表を、今回参照したMemory・Skills・Permissionsの現行公式文書へ更新

関連SVGも同じ説明へ更新した。

- `assets/diagram-conditional-context.svg`
- `assets/diagram-skill-anatomy.svg`
- `assets/diagram-placed-vs-read.svg`
- `assets/diagram-rulefile-vs-settings.svg`
- `assets/diagram-runaway-guardrail.svg`
- `assets/diagram-context-status.svg`

## 2. 公式情報との照合

- [Claude Code memory docs](https://code.claude.com/docs/en/memory)で、`/context`のMemory files、`InstructionsLoaded` hook、簡潔で具体的な指示の推奨、競合ルールが恣意的に選ばれる場合があることを確認
- [Claude Code skills docs](https://code.claude.com/docs/en/skills)で、通常のセッションでは`description`がコンテキストに入り、呼び出し時にスキル本文が入る段階的開示を確認
- [Claude Code permissions docs](https://code.claude.com/docs/en/permissions)で、権限制御はClaude Codeが実行環境側で強制し、プロンプトやCLAUDE.mdは許可される操作自体を変えないことを確認

## 3. 独立内容監査

初回監査では、追加レビューで挙げられた項目の反映を確認した後、次の残課題を新たに検出した。

- S17の使用SVGに「そもそも実行できない」という過剰断定が残り、本文の許可・確認・拒否と不整合
- S41の図が「経緯→現在地→確定→未確認」を1本の矢印で並べ、時間と確度を同じ順序に見せていた
- S31のノートに、実際の事例順と合わない「最後の境界事例」という表現が残っていた

S17を「許可・確認・拒否を制御」、S41を「時間」と「確度」の2区分、S31を「境界事例では」へ修正して再監査した。

再監査結果:

- 重大: 0件
- 中: 0件
- 軽微: 0件
- 追加GPTレビューの残課題: なし
- 新たな矛盾・過剰断定・出典不整合: なし

## 4. 視覚確認

全72枚のPNGを確認し、文字切れ・重なり・表のはみ出し・画像／キャプションの不整合・低コントラスト・ページ番号異常・文字化けを監査した。

初回独立監査でS7・S18・S20・S32・S34・S71の不自然な改行を検出し、修正した。S34の再監査で残った「削／除」の分断も修正した。最終変更したS17・S34・S41を原寸で独立再確認し、新たな視覚問題がないことを確認した。全PNGは1280×720。

## 5. ビルド・PPTX検証

- `pipeline/bin/gate_deck.sh decks/02-context-engineering`: `gate_deck OK: 72 slides`
- `unzip -t`: 圧縮データのエラーなし
- deck.json: 72枚
- python-pptx再パース: 72枚
- PNGプレビュー: 72枚、全て1280×720
- `has_notes_slide == False`: 全72枚
- 参照アセット: 33種類、欠落0
- 参照SVG XML検証: エラーなし
- PPTXテキストのプレースホルダー検査: 該当なし
- OKF検証: errors 0 / warnings 0

## 6. 最終成果物

- `deck.json` SHA-256: `e2478cce3899e5b9a6a3c6b59bb672c1e3ee1522767ca3c9783e7b147a8a4023`
- HTML SHA-256: `aa7e7a02d83f9f232672766177c484924137e899547b6237b77d375311e2bccc`
- PPTX SHA-256: `a427123c0ce0289fdf66e3b188f03e1bb91013e3719b2ef05053fcbab1af9552`

今回の修正後も正本は`deck.json`であり、`build/`は同ファイルから再生成した成果物である。

# Codex 最終レビュー記録

対象: `decks/ai-eng-02-context-engineering-v2/`  
実施日: 2026-08-14〜2026-08-15  
判定: 合格（Claude統合版 + GPT Proレビュー反映 + Codex内容／視覚／PPTX検証）

## 1. 正本化の前提

Claude作業版として確認した次のフォルダと、作業開始時のv2を比較した。

`.claude/worktrees/ce-slide9-newhire-vs-veteran/decks/ai-eng-02-context-engineering/`

比較時点では、`deck.json`、参照アセット38ファイル、HTMLがバイト単位で一致していた。PPTXのZIPハッシュだけは生成差で異なったが、正本データの内容差ではなかった。この一致版をClaude統合版の基準とし、その後のCodex修正はv2だけへ反映した。

## 2. GPT Proレビューへの対応

### 最優先項目

- S5: コンテキストを「今回の推論でモデルに渡され、参照可能になった情報」と定義し、保存済みファイル・メモリと実際のロードを分離
- S17・S20: 権限・hook・承認をコンテキストから外し、実行環境側のガードレールとして整理
- S34・S36: Replit事故をハーネスの境界事例へ変更し、「根絶」「完全防止」等の保証表現を撤回
- 全体: 「必ず」「毎回同じ」「ベテラン同等」等を「ばらつきを減らす」「近づけやすい」「場合がある」へ修正

### 次点・仕上げ項目

- S8〜S20: 自動ロード／必要時に取得／今回渡す、という教材上の3経路と、製品固有のロード仕様を明示
- S9: Before/Afterの依頼文を同一にし、事前ロード済みのCLAUDE.mdとレビュー規約だけを差分にした
- S10: 「前提知識ゼロ」を撤回し、一般知識はあるが組織・案件固有の前提を共有していない、という比喩へ修正
- S16: メモリの一般論とClaude Code auto memoryを分け、200行／25KBの開始時ロード上限を明記
- S18・S30: SkillsをSKILL.mdを入口とするディレクトリとして説明し、自動判定と明示呼び出しを区別
- S24: 「ランダムに従う」を撤回し、競合時は挙動が不安定・予測しにくいと修正
- S26・S68: OKF v0.2へ更新し、知識形式と本プロジェクトのロード実装を分離
- S32・S33・S35: 固有規約、出力形式、再発防止の効果を非保証表現へ修正
- S71: 誤って事故資料へ割り当てていたCE-S16／CE-S19を廃止。CE-S22（Geminiユーザー報告）、CE-S23（The Register）、CE-S24（Fortune）へ分離して出典対応を修正
- S1: サブタイトルを「AIに『何を・いつ・どれだけ』見せるか」へ変更

## 3. 採用しなかった構成提案

- 本編フッターの `X / 72` を `X / 36 付録あり` へ変える案は不採用。正本を1つの連続デッキとして扱う既存仕様を維持し、S1ノート・S36・READMEで36枚目までが通常発表範囲と明示した
- OKFの本編S26を付録へ移す案は不採用。詳細仕様ではなく「段階的な知識配置例」を1枚だけ本編に残し、OKF自体はロード機構ではないという留保を同じページに置いた
- 一般向けタイトルを「Claude Codeで学ぶ」に変える案は不採用。製品固有の例は各ページでClaude Codeと明記し、コンテキスト・ガードレール等の一般概念と分離した

## 4. 独立内容監査で追加修正した項目

- S20の列名を「いつ読まれる」から「いつ入る／作用する」へ変更し、ガードレールを読まれる情報のように見せる矛盾を解消
- S3・S6・S71に残っていた断定表現を追加で緩和
- Replit／Gemini CLIの出典ID衝突を検出し、`knowledge/sources/` にCE-S22〜CE-S24を整備。Replitのコードフリーズ・復旧はThe Register、影響概数はFortuneへ帰属を分離し、`knowledge/sources/index.md` と `knowledge/log.md` も更新
- `tools/validate_okf.py knowledge` で errors 0 / warnings 0 を確認

修正後の独立再監査はPASS。GPT Proレビューの主要指摘、出典IDの一意性、事故報道とユーザー報告の帰属に、重大・中程度の残課題がないことを確認した。

## 5. 視覚確認

全72枚のPNGを独立レビューした。初回確認でS8・S10・S17・S25・S26・S36・S38に低コントラスト文字を検出し、SVGのCSS上書きとclosingスライドの強調色を修正した。

修正後の再確認では、対象7枚の該当文字が約5.83〜8.77:1となり、文字切れ・重なり・配置崩れなしで合格した。その他65枚にも文字切れ、重なり、表のはみ出し、図中文字欠け、文字化けはなかった。全PNGは1280×720。

## 6. ビルド・PPTX検証

- `python3 tools/build_deck.py decks/ai-eng-02-context-engineering-v2`: 成功
- `python3 tools/preview_deck.py decks/ai-eng-02-context-engineering-v2`: 72枚生成
- `bash pipeline/bin/gate_deck.sh decks/ai-eng-02-context-engineering-v2`: `gate_deck OK: 72 slides`
- `unzip -t`: 圧縮データのエラーなし
- python-pptx再パース: 72枚
- deck.json: 72枚
- PNGプレビュー: 72枚、全て1280×720
- `has_notes_slide == False`: 全72枚
- 参照アセット: 33種類、欠落0
- SVG XML検証: エラーなし
- OKF検証: errors 0 / warnings 0

## 7. 最終成果物

- `deck.json` SHA-256: `9f27269c942d3a06be7db90fb7a5379d17b6549e6b15a5dde988bd0a3454019a`
- HTML SHA-256: `9975b65020831c7119aa39bdc837859bf3640b07d5965557e0710433a88ec5b5`
- PPTX SHA-256: `73a9d550f86daec6eb2f2d4786942ac988492f379d9c5c71c0ca48d8b02f3069`

旧IDで生成されていた `build/ai-eng-02-context-engineering.html` と `.pptx` は、正本の取り違えを防ぐため削除した。現在の生成物名はすべて `ai-eng-02-context-engineering-v2` で統一している。

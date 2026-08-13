---
type: Article
title: "Mitigating the risk of prompt injections in browser use"
description: "Anthropic公式のブラウザエージェント向けprompt injection解説。外部ページや文書に埋め込まれた悪意ある指示がエージェントの行動を乗っ取る脅威と、改善後も未解決であるという留保を示す。"
source_id: CE-S11
site: Anthropic
published: "2025-11-24"
retrieved: "2026-08-14"
resource: "https://www.anthropic.com/research/prompt-injection-defenses"
origin: "web:anthropic.com"
source_tier: primary
tags: [prompt-injection, security, browser-agents, untrusted-content, defense-in-depth]
generated:
  by: codex/gpt-5.6
  at: "2026-08-14T02:44:42+09:00"
---

# 概要

ブラウザエージェントが処理するウェブページ、メール、埋め込み文書などに、利用者の依頼を上書きしようとする悪意ある指示が含まれるprompt injectionの脅威を説明したAnthropic公式記事。モデルと周辺防御の改善を報告しつつ、実世界で行動するエージェントにとって未解決の重大なリスクであると明記している。

# 要点

- 外部コンテンツは、利用者が読める情報であると同時に、モデルには指示のように見える文字列を含み得る。
- ブラウザ利用では、ページ、埋め込み文書、広告、動的コンテンツなど攻撃面が広く、侵害されたエージェントは閲覧だけでなく送信・入力・ダウンロードなどの行動へ影響を受け得る。
- モデル単体の耐性向上だけでなく、エージェント周辺の防御、権限制御、危険行動の確認を重ねる必要がある。
- 改善された評価結果があっても、攻撃成功可能性が残る以上「安全になった」「完全に防げる」とは扱わない。

# 適用範囲と留保

- 記事の実験はAnthropicのブラウザ製品、特定モデル、内部の適応型攻撃評価に関するもので、他の製品やすべての攻撃への性能保証ではない。
- prompt injectionはブラウザに限らない。RAGで取得した文書、メール、コード、MCPや外部ツールの結果など、信頼できない情報がコンテキストへ入る経路全体に同型のリスクがある。
- 「命令とデータをタグで分ける」だけでは完全防御にならない。権限最小化、送信前確認、出力先制限、監査、隔離を組み合わせる。
- 脅威・防御は更新が速いため、具体的なモデル成績や安全率を固定値として一般化しない。

# 原文の根拠箇所

- **未信頼コンテンツ中の悪意ある指示**: `What is prompt injection?`
- **ブラウザで広がる攻撃面と副作用**: `Why browser use creates unique prompt injection risks`
- **モデルと周辺防御を重ねる考え方**: `Claude's progress on browser use robustness`
- **未解決性**: 冒頭および `The path forward`

# デッキで安全に使える表現

- 「外部資料は『情報』であると同時に、AIには『指示』のように見える文字列を含むかもしれません。」
- 「コンテキスト設計には、何を入れるかだけでなく、どの情報をどこまで信頼し、どの行動権限と結ぶかが含まれます。」
- 「プロンプトインジェクションは未解決です。モデルの注意力だけに任せず、権限・確認・隔離を重ねます。」

# 活用先

- [../context-engineering/security-and-trust-boundaries.md](../context-engineering/security-and-trust-boundaries.md) — 信頼境界、prompt injection、権限最小化、人の確認
- [../context-engineering/retrieval-memory-compaction-cache.md](../context-engineering/retrieval-memory-compaction-cache.md) — 取得文書を無条件に信頼しない設計

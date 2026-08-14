---
type: Concept
title: ハーネスエンジニアリングとは何か——定義・スコープ・このバンドルの読み方
description: AIエージェントが動く「環境」そのものを設計対象にするハーネスエンジニアリングの定義を、arXiv論文の形式的定義と解説動画の4要素整理の両面から示し、バンドル全体の地図と読む順番を提示する
tags: [harness-engineering, terminology, ai-agent, runtime-substrate, claude-code]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-14T21:35:00+09:00"
---

# ハーネスエンジニアリングとは何か

ChatGPTのようなチャット型のAIを使っていると、AIの出来を決めるのは「どう聞くか」（プロンプト）だと感じる。ところがAIに実際の業務——ファイルを開き、コマンドを実行し、結果を確かめて直す——をさせようとすると、指示の巧拙よりも先に、**AIがそもそも何に触れられて、何を実行でき、どこで止まるのか**が結果を左右し始める。この「AIが動く環境そのもの」を設計対象として名指ししたのが、ハーネスエンジニアリングである。

このファイルではまず一言定義を示し、次にその定義を支える2つの出所（学術論文と解説動画）を突き合わせ、初心者がつまずきやすい誤解を整理したうえで、このバンドル（8つのコンセプト）の地図と読む順番を示す。

## 一言定義

ハーネスエンジニアリングとは、**AIエージェントを取り囲むランタイム環境——道具・情報・記憶・権限・検証——を明示的に設計し、モデルの潜在能力を監査可能な仕事に変換すること**である。

「ハーネス（harness）」は馬具のことで、[keitoaiweb動画](../sources/video-pe-five-engineering-stages.md)は、装備が整っているからこそ安定して走れるという比喩でこの語を説明している。馬（モデル）をいくら速い品種に替えても、鞍も手綱もなければ荷物は運べない。ハーネスエンジニアリングは、鞍と手綱の側を作る仕事である。

## 定義を支える2つの出所

### 学術的な定義：モデル・ハーネス・環境からなるシステム

[arXiv論文 "AI Harness Engineering"](../sources/article-he-harness-engineering-paper.md) は、ソフトウェアエンジニアリング能力はモデル単体の性質ではなく、モデル・ハーネス・環境からなるシステムから創発する性質だと論じている。同論文はこれを次の式で定式化している。

```
C_system = F(C_model, C_harness, C_environment, T)
```

C_model は基盤モデルの潜在能力、C_environment はソフトウェア環境が公開している内容、C_harness は両者を媒介するランタイム基盤、T はタスク分布を表すとされる。そしてハーネスそのものを、同論文は次のように定義している。

> 引用: 「An AI Harness Engineering is a runtime substrate surrounding a foundation-model software agent that manages context, tools, project memory, task state, observability, failure attribution, verification, permissions, and maintenance state, so that latent model coding capability becomes auditable software-engineering behavior.」

注目すべきは末尾の "auditable"（監査可能）である。同論文は、ハーネスの役割を「AIを賢くすること」ではなく、**モデルの潜在能力を、後から検証・追跡できる形の仕事に変換すること**に置いている。ここがプロンプトの工夫と決定的に違う点であり、企業でAIを業務に組み込む際にハーネスが避けて通れない理由でもある。

### 実務的な整理：道具・制限・権限・ルールの4要素

一方、[keitoaiweb動画](../sources/video-pe-five-engineering-stages.md)は、ハーネスエンジニアリングを「AIが動く環境そのものを丸ごと設計する手法」とし、**道具（何を実行し何と接続するか）・制限（触れてはいけない領域）・権限（フルオートか承認フローを挟むか）・ルール（毎回読み込むべきコンテキスト）の4要素**で環境を整えるものだと説明している（auto字幕からの聞き取り。同動画独自の整理であり業界標準の分類ではない）。

論文の11責務（[harness-responsibilities-and-ladder.md](./harness-responsibilities-and-ladder.md) で扱う）に比べて粒度は粗いが、初めて設計に手をつけるときの入口としてはこの4要素が実用的である。本バンドルの中盤5本は、この4要素に対応する構成になっている（権限のみ2本立てで、permissions-designがルールの評価順序を、settings-scopes-and-governanceが組織への配布・統制面を担う）。

### 定義が指すものは同じか

両者は出自も精度もまったく違う（一方は査読前論文、一方は個人の解説動画のauto字幕）が、**「モデルではなく、モデルの周りを設計する」という着眼点は一致している**。論文の11責務のうちツールアクセス・権限・コンテキスト選択・プロジェクトメモリは、動画の道具・権限・ルールにほぼ対応する。動画の「制限」は論文では権限責務に含まれる形になっており、分類の切り方だけが異なると読める。

## 他の「〇〇エンジニアリング」との関係

[keitoaiweb動画](../sources/video-pe-five-engineering-stages.md)は、プロンプト・コンテキスト・ハーネス・ループ・グラフという5つの「〇〇エンジニアリング」を、目的（AIの回答の質を上げること）は共通で**スコープ（範囲）だけが違う**ものとして整理している。プロンプトは指示を磨く、コンテキストは渡す情報を選ぶ、ハーネスは動く環境を整える、ループは時間軸で動きを回す、グラフは構造で組む、という区分である（auto字幕からの聞き取り）。

この5段階の整理そのものは、既存の [prompt-engineering/five-engineering-stages.md](../prompt-engineering/five-engineering-stages.md) と [context-engineering/five-engineering-scopes.md](../context-engineering/five-engineering-scopes.md) で詳しく扱っている。用語の系譜としての注意点（この語群自体が業界の癖を風刺する文脈で広まった側面があること）は [graph-engineering/term-lineage-and-layers.md](../graph-engineering/term-lineage-and-layers.md) を参照してほしい。

いつハーネスに手をつけるべきかについて、同動画は症状別の目安を挙げている。「意図と違う結果」が返るならプロンプト、「前提を忘れる」ならコンテキスト、**「手作業の事故が怖い」ならハーネス**、「品質が安定しない」ならループ、「タスクが大きすぎて崩れる」ならグラフを見直す、という整理である。最初から5つすべてを意識するのはやりすぎだとも述べており、この助言は本バンドルにもそのまま当てはまる。

## よくある誤解

- **ハーネスは特定の製品名ではない**: Claude CodeやAgent SDKはハーネスの実装例であって、ハーネスエンジニアリングそのものではない。[Anthropic公式のAgent SDK文書](../sources/article-he-agent-sdk-overview.md)は、組み込みツール・Hooks・Subagents・MCP・Permissions・Sessions・Skills/memory・Pluginsという機能群を挙げているが、これらは上記4要素・11責務を製品として具体化したものと読める
- **AIを賢くする技術ではない**: ハーネスを整えてもモデルの知能は上がらない。上がるのは「モデルの能力が実際の成果として現れる率」と「その成果を検証できる度合い」である
- **プロンプトの上位互換ではない**: 5段階は置き換え関係ではなく入れ子の関係にある。ハーネスをどれだけ整えても、その中で出す指示が曖昧なら結果は曖昧になる

## このバンドルの地図

| # | ファイル | 扱う内容 |
|---|---|---|
| 1 | [why-harness-matters.md](./why-harness-matters.md) | なぜモデル単体では足りないのか。能力ギャップの所在と、人間が無自覚に埋めている支援 |
| 2 | [harness-responsibilities-and-ladder.md](./harness-responsibilities-and-ladder.md) | 11の責務とH0〜H3の段階ラダー、トレースベースの評価 |
| 3 | [tools-and-mcp.md](./tools-and-mcp.md) | 【道具】組み込みツール・MCP・WebMCP・スキル |
| 4 | [permissions-design.md](./permissions-design.md) | 【権限】deny→ask→allowの評価順序と、強制主体はモデルではないという原則 |
| 5 | [settings-scopes-and-governance.md](./settings-scopes-and-governance.md) | 【権限】設定の4スコープと組織としての統制設計 |
| 6 | [sandbox-and-isolation.md](./sandbox-and-isolation.md) | 【制限】サンドボックスの3分類と最小権限の原則 |
| 7 | [project-memory-and-rules.md](./project-memory-and-rules.md) | 【ルール】CLAUDE.mdをプロジェクトメモリとして設計する |

### 読む順番の提案

本ファイル → 1 → 2 で「なぜ必要か」と「何を設計するのか」の全体像を固め、3〜7 で4要素それぞれの具体に降りるのを勧める。3〜7は「できることを与える」（道具）→「危険なことを塞ぐ」（権限）→「塞ぎ方を組織に配る」（設定スコープ）→「塞ぎ切れなかった場合に備える」（サンドボックス）→「前提知識を渡す」（ルール）という流れになっている。特に**4（権限）は5（統制）と6（隔離）とセットで読む**とよい。権限ルール・設定スコープ・サンドボックスは、いずれも「エージェントに何をさせないか」を別の層で担保する仕組みであり、どれか1つだけでは守りきれないためである。

# Citations

- [arXiv論文「AI Harness Engineering: A Runtime Substrate for Foundation-Model Software Agents」](../sources/article-he-harness-engineering-paper.md) — ハーネスの形式的定義、C_system の式、「監査可能な行動への変換」という役割規定の根拠
- [keitoaiweb動画「5つのエンジニアリング徹底解説」](../sources/video-pe-five-engineering-stages.md) — 道具・制限・権限・ルールの4要素、馬具という語源の比喩、5段階のスコープ差と症状別の使い分け目安の根拠（いずれもauto字幕）
- [Anthropic公式「Agent SDK overview」](../sources/article-he-agent-sdk-overview.md) — ハーネスの実装例としての機能群（組み込みツール・Hooks・Subagents・MCP・Permissions・Sessions・Skills/memory・Plugins）の根拠

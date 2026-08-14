---
type: Article
title: Claude Codeの権限設定と管理者権限 — permissions実務ガイド
description: Claude Code法人導入支援を手がけるAI Orchestraが、deny・ask・allowによる権限制御の基本から、sudo・bypassPermissionsモードの扱い、managed settingsによる全社配布までを、導入支援で実際に使う設定例とともに解説する。
site: AI Orchestra
published: unknown
retrieved: 2026-08-14
resource: https://www.ai-orchestra.ai/claude-code-training/columns/claude-code-permissions
origin: "web:ai-orchestra.ai"
source_tier: secondary
tags: [harness-engineering, claude-code, permissions, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-14T00:00:00+09:00"
---

# 概要

AI Orchestraは、Claude Codeの法人導入支援を手がける立場から、権限設定（permissions）の実務ガイドを公開している。同社は「Claude Codeに削除コマンドを実行されないか不安」「社員ごとに設定がバラバラで統制が効かない」という相談が導入支援で必ず出てくると述べ、Claude Codeには「禁止・確認・許可」を機械的に強制する仕組みが標準で備わっており、正しく設計すれば「AIが勝手に危険な操作をする」リスクは設定レベルで塞げると説明している。本記事は、permissionsの基本から情報システム部門が全社員へ設定を強制配布するmanaged settingsまでを、同社が導入支援で実際に使っている設定を交えて解説する内容だとしている。

# 要点

## 権限設定の基本 — deny・ask・allowの3層

AI Orchestraは、Claude Codeのpermissions設定を、AIエージェントが実行しようとする操作（コマンド実行・ファイル読み書き・Web取得など）をdeny（禁止）・ask（毎回確認）・allow（許可）の3種類のルールで制御する仕組みだと説明している。

重要なのは評価の順序だとし、ルールはdeny→ask→allowの順で評価され、最初に一致したものが適用されると述べている。

> 引用: 「ルールはdeny → ask → allowの順で評価され、最初に一致したものが適用されます。つまりallowに何を書いてあっても、denyに一致すれば必ずブロックされます。」

この性質により、「会社として絶対に禁止したい操作」をdenyに置いておけば、現場が利便性のためにallowを増やしても、その禁止が破られることはないと同社は述べている。

さらに同社は、ルールを守らせるのはAIではなくClaude Code本体であり、permissionsのルールを強制するのはClaude Codeというソフトウェア自体であってAIモデルの「判断」ではないと強調している。CLAUDE.mdに「.envを読むな」と書くのはプロンプトによるお願いに過ぎず確率論の世界であるのに対し、確実に守らせたい禁止事項は必ずpermissionsのdenyルールとして機械的にガードすべきだと主張しており、この使い分けが法人導入のセキュリティ設計で最も重要な考え方だとしている。

## ルールの書き方 — ツール名と対象パターンで指定する

同社によると、ルールは「ツール名（対象パターン）」の形式で書き、ツール名だけを書けばそのツール全体、括弧内にパターンを書けば特定の操作だけに絞れる。`*`はワイルドカードで、コマンドの先頭・途中・末尾どこでも使えると説明されている。また、`&&`や`;`でつないだ複合コマンドは部分ごとに分解して判定されるため、「安全なコマンドの後ろに危険なコマンドを連結してすり抜ける」ことはできない設計になっているとしている。

## 法人導入の推奨セット

AI Orchestraは、導入企業に最初に配布している基本形があるとし、プロジェクトの`.claude/settings.json`に置けばチーム全員に、`~/.claude/settings.json`に置けば個人の全プロジェクトに適用されると説明している。設定ファイルを自分で書く必要はなく、Claude Codeに日本語で「.envの読み取りとsudoを禁止して、rmは毎回確認にして」と依頼すれば、設定ファイルを書いてくれるため、内容を確認して保存するだけでよいとしている。

## 「管理者権限」の2つの論点 — sudoとbypassPermissions

同社は、Claude Codeと管理者権限の話には2つの別の論点があると整理している。1つ目はOSの管理者権限（sudo）をAIに渡すかどうかで、sudoはシステム全体を変更できる権限であり、AIエージェントに渡す必要はほぼないと述べている。上記の推奨セットのとおり`Bash(sudo *)`をdenyにしておき、OSレベルの作業が必要な場面は人が実行する運用にすることを勧めている。

2つ目は確認プロンプトを省略するbypassPermissionsモードだとしている。Claude Codeには通常の確認動作を変えるパーミッションモード（計画だけ立てて実行前に確認するplanモード、編集を自動承認するacceptEditsモードなど）があり、その中のbypassPermissionsは確認をスキップして実行し続けるモードだと説明されている。開発効率は上がるが、コンテナや仮想マシンなど壊れても影響がない隔離環境以外では使わないのが原則だと同社は述べている。組織としては、設定に`disableBypassPermissionsMode`を`"disable"`と指定することで、このモード自体を使えなくできるとしている。

## 「すべて許可」にしたい — 確認プロンプトを安全に減らす4つの方法

「毎回の確認が煩わしいので、すべて許可で動かしたい」という相談もよく受けると同社は述べ、Claude Codeには確認プロンプトを減らす方法が複数あり、リスクの低い順に並べると4つあるとしている（2026年7月時点の公式ドキュメントで確認したとされる）。

完全な「すべて許可」にあたるbypassPermissionsモードは、起動時に`claude --permission-mode bypassPermissions`（同じ意味の`--dangerously-skip-permissions`でも可）と指定した場合だけ使えると説明している。フラグ名に「dangerously（危険を承知で）」と入っているとおり自己責任のモードであり、初回は責任を受け入れる確認ダイアログが表示され、root・sudoでの起動は拒否されるとしている。ルートディレクトリやホームディレクトリ全体の削除（`rm -rf /`など）だけは、このモードでも安全装置として確認が残るとしている。

実務での推奨として、日常の開発では「今後確認しない」で許可リストを育てるかautoモードを使い、bypassPermissionsは隔離環境に限定することを挙げている。公式ドキュメントも、確認を減らしたい場合は安全チェック付きのautoモードを代替として推奨しているとしている。組織として「すべて許可」を封じたい場合は、前述のとおり設定の`disableBypassPermissionsMode`で無効化できるとしている。

## 設定ファイルは4層 — 誰がどこまで統制できるか

同社は、permissionsを書く場所は1つではなく、Claude Codeの設定ファイルには4つの層があり、法人導入では「どの層に何を書くか」の設計がそのまま統制設計になると述べている。優先順位はmanagedが最上位で、以下コマンドライン指定→local→project→userの順だとしている。ただしpermissionsのルールに限っては、denyルールはどの層に書かれていても常に有効であり、ユーザー設定のdenyをプロジェクト設定のallowで上書きするといったことはできないと説明されている。

# 活用先

- [../harness-engineering/permissions-design.md](../harness-engineering/permissions-design.md) — deny→ask→allowの実務的な読み替え（禁止は現場のallowで破られない）、CLAUDE.mdは確率論／denyは機械的ガードという対比、ルール記法と複合コマンドの分解判定、日本語依頼で設定ファイルを書かせる導入手順、sudoとbypassPermissionsの2論点、権限モードと`disableBypassPermissionsMode`による組織的無効化の根拠
- [../harness-engineering/settings-scopes-and-governance.md](../harness-engineering/settings-scopes-and-governance.md) — 「どの層に何を書くか」がそのまま統制設計になるという位置づけ、設定4層の優先順位（managed→コマンドライン→local→project→user）、denyルールはどの層でも常に有効でallowで上書きできないこと、`.claude/settings.json`と`~/.claude/settings.json`の適用範囲、日本語依頼で設定ファイルを書かせる運用の根拠
- [../harness-engineering/sandbox-and-isolation.md](../harness-engineering/sandbox-and-isolation.md) — bypassPermissionsモードを隔離環境以外では使わないのが原則であるという指摘、すなわち権限層の防御を外す前提としてサンドボックスが要求されること（「隔離が先、bypassが後」）の根拠

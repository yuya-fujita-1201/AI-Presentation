---
type: Article
title: gemini-cli issue #4586 - ファイルが失われたとするユーザー報告
description: sandboxなしのWindows環境でGemini CLIへファイル整理を依頼した際にファイルを失ったとユーザーが報告した2025年7月のissue
source_id: CE-S22
site: GitHub - google-gemini/gemini-cli
published: 2025-07-21
retrieved: 2026-08-14
resource: https://github.com/google-gemini/gemini-cli/issues/4586
origin: "github:google-gemini/gemini-cli"
source_tier: primary-user-report
tags: [context-engineering, harness-engineering, incident, gemini-cli, issue]
generated:
  by: codex/gpt-5
  at: "2026-08-14T23:50:49+09:00"
---

# 概要

Gemini CLIのGitHub issue #4586に投稿されたユーザー報告。Windows環境でファイル整理を依頼した際にファイルを失ったと投稿者が述べ、環境情報としてGemini CLI 0.1.13、sandboxなしが記載されている。製品側が原因や削除を確定した報告ではない。

# 要点

- 2025年7月21日に投稿されたユーザー報告である。
- Windows環境、Gemini CLI 0.1.13、sandboxなしという条件が記載されている。
- ファイル整理中にファイルを失ったと投稿者が報告している。

# 根拠箇所

- issue本文のEnvironment欄
- issue本文のProblem description

# 適用範囲と留保

- 製品側が確定した事故報告ではなく、GitHub上のユーザー報告である。
- 添付ログを超えて詳細な因果関係を断定しない。
- デッキでは「sandboxなしのWindows環境で、ファイル整理中の消失がユーザーから報告された」という範囲に限定して使う。

# 活用先

- [../../decks/ai-eng-02-context-engineering-v2/deck.json](../../decks/ai-eng-02-context-engineering-v2/deck.json) — スライド34・71の補足事例

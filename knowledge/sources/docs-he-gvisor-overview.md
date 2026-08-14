---
type: Article
title: What is gVisor? - gVisor Documentation
description: gVisorをuserspace application kernelとOCI runtime runscとして説明し、通常のLinux隔離機構や一般的なVMとの違いを示す公式文書
site: gVisor
published: unknown
retrieved: 2026-08-15
resource: https://gvisor.dev/docs/architecture_guide/intro/
origin: "web:gvisor.dev"
source_tier: primary
tags: [harness-engineering, sandbox, isolation, container, gvisor]
generated:
  by: codex/gpt-5.6
  at: "2026-08-15T02:51:12+09:00"
---

# 概要

gVisor公式文書は、gVisorをコンテナワークロード向けのapplication kernelとして説明する。`runsc`はOCI互換runtimeとして動作するが、アプリケーションのsystem callをユーザー空間で仲介し、host kernelへ直接触れるsurfaceを減らす。

# 要点

- gVisorはuserspace application kernelを用いてsystem callをinterceptする
- `runsc`はOCI runtimeであり、既存のコンテナ管理系と連携できる
- 通常のnamespaces／cgroups中心のコンテナと同じ「host kernel syscallを直接利用する方式」ではない
- 一般的な意味のVMとも異なり、公式はLinux隔離機構の単純なwrapperとVMの間にある第三の方式として説明する
- 「コンテナ」という配布・運用上の互換性と、分離を実現するruntimeの境界を分けて記述する必要がある

# 活用先

- [../harness-engineering/sandbox-and-isolation.md](../harness-engineering/sandbox-and-isolation.md) — 通常のOCIコンテナとgVisor／runscを分ける一次根拠

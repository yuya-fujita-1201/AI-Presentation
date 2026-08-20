---
type: Article
title: Claude Code から Codex CLI を呼び出すなら MCP と SKILL/BASH どっちがいい？実際に使って感じたこと
description: Claude CodeからCodex CLIを呼び出す手段としてMCPとSKILL/BASH（codex exec）を実際に比較し、用途別の使い分けと実測トークン消費を報告する記事
site: とつブログ（m-totsu.com）
published: unknown
retrieved: "2026-08-20"
resource: https://www.m-totsu.com/1202/
origin: "web:m-totsu.com"
source_tier: secondary
tags: [tools, mcp, cli, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-21T00:00:00+09:00"
---

# 概要

著者は、Claude CodeからCodex CLIを呼び出す方法としてMCPとSKILL/BASHの両方を実際に試し、それぞれの得意分野を比較したと説明している。記事は「はじめに（MCP vs SKILL/BASHという2つの選択肢）→MCP試行（期待と現実のギャップ）→MCPが得意な用途はCRUD操作→SKILL/BASHへの切り替え→比較表→発展Tips：`codex exec --json`の活用→まとめ・使い分け指針」という構成を取っており、実際の利用体験に基づいて両者の使い分け指針を示す内容になっている。

# 要点

## MCP: CRUD操作は得意、重い処理はブラックボックス化

著者は、MCP経由の呼び出しについて、データベース検索・カレンダー操作・Slack連携など「即レスポンスが返る」CRUD処理には向くと評価している。一方でコード生成のような重い処理をMCP経由で実行させた際には、次のように課題を指摘している。

> 引用: 「処理が非常に重く、数分～数十分待たされることがあった」

さらに、処理中は進捗が見えないブラックボックス感があった点も課題として挙げている。トークン消費についても具体的な実測値を報告しており、5サーバー58ツールという構成で約55,000トークンを消費したとしている。この数値は、MCPを常時接続するコスト感を把握するうえでの目安になる。

## SKILL/BASH（codex exec）: 進捗の可視化と軽量さが利点

MCPの課題を踏まえ、著者はSKILL/BASH（`codex exec`）への切り替えを試している。SKILL/BASHはコード生成・テスト実行・長時間タスクに向くとし、利点として、リアルタイムで進捗を確認できる点、動作の軽快さ、コンテキスト消費の少なさの3つを挙げている。ただし手放しで推奨しているわけではなく、既知バグとして「exit code 0を失敗時にも返すケース」（Issue #15536）があると注意喚起しており、成否判定を終了コードだけに頼るリスクにも触れている。

## `codex exec --json`によるプログラム的な成否判定

発展的な活用手法として、著者は`codex exec --json`モードを紹介している。このモードではJSONL形式で出力され、各フェーズの成功・失敗をプログラム的に判定できるとし、具体的なイベント例として`thread.started`、`item.completed`、`turn.failed`を挙げている。また`--full-auto`オプションについては、ワークスペース内でのファイル読み書きやコマンド実行をOSレベルのサンドボックスで保護しつつ許可するものだと説明している。リトライ機能としては`codex exec resume <セッションID> --full-auto`や`codex exec resume --last --full-auto`というコマンド例を示し、これらを使うとコンテキストと承認設定が保持されると述べている。

## 結論: 現時点ではSKILL/BASHが実用的、ただし将来は変わりうる

著者の最終的な推奨は、現時点では「SKILL/BASHが実用的」というものである。ただし断定的な結論ではなく、MCPのTasksプリミティブ（2025年11月実装）が今後安定化すれば、この判断が将来的に変わる可能性があるとも付言している。この留保は、MCPとSKILL/BASHのどちらが優れているかという二者択一ではなく、処理特性とMCPエコシステムの成熟度の両方を見て選ぶべきだという著者のスタンスを示している。

# 活用先

（コンセプト昇華時に追記）

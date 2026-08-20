---
type: Article
title: Architecture overview - Model Context Protocol
description: MCP公式ドキュメントが、MCP Host/Client/Serverのクライアント・サーバー構造、data layer/transport layerの2層設計、ステートレスなプロトコル設計を解説している
site: Model Context Protocol (公式ドキュメント)
published: unknown
retrieved: 2026-08-20
resource: https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture
origin: "web:modelcontextprotocol.io"
source_tier: primary
tags: [mcp, protocol-architecture, ai-tools, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

Model Context Protocol公式ドキュメントの「Architecture overview」ページを基にした記事で、MCPを構成するプロジェクト群とクライアント・サーバー型アーキテクチャの全体像を解説している。ドキュメントは「MCP focuses solely on the protocol for context exchange—it does not dictate how AI applications use LLMs or manage the provided context.」と明言しており、MCPがコンテキスト交換のプロトコルのみを規定するものであることを強調している。

# 要点

## MCPを構成する4つのプロジェクト

公式ドキュメントは、MCPを構成するプロジェクトとして、クライアント・サーバーの実装要件を定める仕様書であるMCP Specification、各言語向けSDKであるMCP SDKs、MCP Inspectorなどの開発ツールであるMCP Development Tools、サーバーのリファレンス実装であるMCP Reference Server Implementationsの4つを挙げている。

## 参加者（Participants）とクライアント・サーバー構造

MCPはクライアント・サーバー型アーキテクチャを採る。

> 引用: 「MCP follows a client-server architecture where an MCP host — an AI application like Claude Code or Claude Desktop — establishes connections to one or more MCP servers. The MCP host accomplishes this by creating one MCP client for each MCP server.」

すなわちMCP Host（Claude Code・Claude Desktop等のAIアプリケーション）が複数のMCP Serverに接続する際、サーバーごとに専用のMCP Clientを1つずつ生成し、各Clientはそのサーバーと専用コネクションを維持する。ドキュメントは「Local MCP servers that use the STDIO transport typically serve a single MCP client, whereas remote MCP servers that use the Streamable HTTP transport will typically serve many MCP clients.」とも述べており、ローカルサーバー（STDIO transport利用）は通常単一クライアントに、リモートサーバー（Streamable HTTP transport利用）は通常複数クライアントに対応するとしている。具体例としてVS Codeがホストとなり、Sentry MCP serverとlocal filesystem serverのそれぞれに別個のMCP Clientオブジェクトを生成する例が挙げられている。

## data layerとtransport layerの2層構造

MCPはdata layer（内側）とtransport layer（外側）の2層から構成される。data layerは「JSON-RPC based protocol for client-server communication, including capability and version discovery, and core primitives, such as tools, resources, prompts and notifications」を定義し、transport layerは通信手段そのもの（transport固有の接続確立・メッセージフレーミング・認可）を定義する。data layerの内訳として、バージョン・capability・identityを問い合わせるDiscovery（`server/discover` request）、tools/resources/promptsを提供するServer features、elicitationを扱うClient features（samplingはprotocol version 2026-07-28でdeprecated）、notifications・progress trackingを扱うUtility featuresが挙げられている。

## Transport（通信経路）

Transportは2種類定義されている。ローカルプロセス間通信向けの「Stdio transport: Uses standard input/output streams for direct process communication between local processes on the same machine, providing optimal performance with no network overhead.」と、リモート通信向けの「Streamable HTTP transport: Uses HTTP POST for client-to-server messages with optional Server-Sent Events for streaming capabilities. This transport enables remote server communication and supports standard HTTP authentication methods including bearer tokens, API keys, and custom headers. MCP recommends using OAuth to obtain authentication tokens.」である。transport layerが通信の詳細を抽象化することで、どちらのtransportを使っても同一のJSON-RPC 2.0メッセージ形式が使えるとされている。

## ステートレス性と3大プリミティブ

MCPは「stateless protocol」であり、各リクエストは`_meta`フィールドにprotocol versionと関連capabilityを含めて送られ、サーバーは過去のリクエストに依存せず処理できる設計になっている。サーバーは必須の`server/discover` requestでサポートするバージョンとcapabilityを広告する。サーバー側が提供する3大プリミティブとして、ファイル操作・API呼び出し・DB問い合わせなど実行可能な関数であるTools、ファイル内容・DBレコードなどコンテキストデータであるResources、対話テンプレートであるPromptsが挙げられている。各プリミティブは`*/list`（発見）、`*/get`（取得）、場合により`tools/call`（実行）のメソッドを持つ。クライアント側が提供するプリミティブとしてElicitation（`elicitation/create`でユーザーに追加情報を要求）があり、SamplingとLoggingはprotocol version 2026-07-28で非推奨化され「New implementations should integrate directly with LLM provider APIs」「New implementations should log to stderr (stdio transport) or use OpenTelemetry」と明記されている。

## JSON-RPCサンプル

ドキュメント末尾では、discovery→tools/list→tools/call→subscriptions/listen（notifications/tools/list_changed）という一連のJSON-RPC 2.0メッセージ例が示されており、`server/discover`のレスポンスにはsupportedVersions・capabilities（例: `"tools": {"listChanged": true}`）・ttlMs（キャッシュ有効期限、例300000ms=5分）が含まれることが具体的に示されている。

# 活用先

（コンセプト昇華時に追記）

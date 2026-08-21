---
type: Article
title: Build an MCP server - Model Context Protocol
description: MCP公式クイックスタートが、Claude for Desktopと接続する天気情報サーバーの構築手順を通じて、MCPサーバーの3大機能・実装手順・STDIOロギングの注意点を解説している
site: Model Context Protocol (公式ドキュメント)
published: unknown
retrieved: 2026-08-20
resource: https://modelcontextprotocol.io/docs/develop/build-server
origin: "web:modelcontextprotocol.io"
source_tier: primary
tags: [mcp, mcp-server, quickstart, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-21T00:00:00+09:00"
---

# 概要

Model Context Protocol公式ドキュメントのクイックスタート「Build an MCP server」を基にした記事で、Claude for Desktopと接続する天気情報サーバーの構築手順を通じてMCPサーバーの基本構造を解説している。作るサーバーは`get_alerts`と`get_forecast`の2つのツールを公開する構成だが、ドキュメントは「Servers can connect to any client. We've chosen Claude for Desktop here for simplicity」と述べており、サーバーは任意のクライアントに接続可能でClaude for Desktopは説明の簡便さのために選ばれているに過ぎないと明言している。

# 要点

## MCPサーバーが提供する3種類の機能

公式クイックスタートは、MCPサーバーが提供できる機能を3種類に整理している。

> 引用: 「MCP servers can provide three main types of capabilities: 1. Resources: File-like data that can be read by clients (like API responses or file contents) 2. Tools: Functions that can be called by the LLM (with user approval) 3. Prompts: Pre-written templates that help users accomplish specific tasks」

すなわちResourcesはAPIレスポンスやファイル内容などクライアントが読み取れるファイル的データ、Toolsはユーザー承認のもとLLMが呼び出せる関数、Promptsは特定タスクの遂行を助ける事前作成済みテンプレートである。このチュートリアルは主にToolsに焦点を当てるとしている。

## 前提知識とシステム要件

Python版の前提知識として挙げられているのは「Python」「LLMs like Claude」の2点のみであり、MCP自体の事前知識は不要とされている。システム要件は「Python 3.10 or higher installed」および「You must use the Python MCP SDK 2.0.0 or higher」と明記されており、Pythonバージョンと専用SDKのバージョン両方に下限が設けられている点が特徴である。

## 環境構築と実装の流れ

環境構築は`uv`パッケージマネージャのインストール（`curl -LsSf https://astral.sh/uv/install.sh | sh`）から始まり、`uv init weather`でプロジェクトを作成し、`uv venv`で仮想環境を作成、`uv add "mcp[cli]"`で依存関係をインストールするという手順が示されている。実装面では、サーバーファイル冒頭でMCPサーバーインスタンスを初期化し（`mcp = MCPServer("weather")`）、定数として米国国立気象局APIのベースURL`NWS_API_BASE = "https://api.weather.gov"`を定義する。ヘルパー関数`make_nws_request`でHTTPリクエストとエラーハンドリングを担い、`format_alert`で警報データを整形する。ツール本体は`@mcp.tool()`デコレータで実装し、`get_alerts(state: str)`は米国の州コード（例: CA, NY）を受け取り警報一覧を返す。`get_forecast(latitude: float, longitude: float)`は緯度経度を受け取り、まずpointsエンドポイントで予報グリッドURLを取得し、次に実際の予報データを取得、直近5期間分（`periods[:5]`）を整形して返す構成になっている。サーバー起動は`mcp.run(transport="stdio")`で行う。

## STDIOサーバーのロギング上の注意

STDIOトランスポートを使うMCPサーバーには標準出力への書き込みが厳禁という制約がある。

> 引用: 「For STDIO-based servers: Never write to stdout. Writing to stdout will corrupt the JSON-RPC messages and break your server. The print() function writes to stdout by default, so keep it out of a STDIO server entirely.」

一方でHTTPベースのサーバーについては「Standard output logging is fine since it doesn't interfere with HTTP responses.」とされ、トランスポート種別によって制約が異なることが示されている。ベストプラクティスとしては標準ライブラリの`logging`モジュール（stderrに書き込む）を使い、`logging.getLogger(__name__)`でモジュールごとにロガーを作ることが推奨されている。

## Claude for Desktopとの接続設定

設定ファイルは macOS の場合`~/Library/Application Support/Claude/claude_desktop_config.json`に置き、`mcpServers`キー配下にサーバー定義を追加する。設定例は`{"mcpServers": {"weather": {"command": "uv", "args": ["--directory", "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather", "run", "weather.py"]}}}`という形になる。注記として「You may need to put the full path to the uv executable in the command field. You can get this by running which uv on macOS/Linux」とあり、環境によっては`command`フィールドに`uv`実行ファイルの絶対パスを指定する必要がある点が警告されている。設定を反映するにはClaude for Desktopの再起動が必要とされる。

# 活用先

- [../agent-capabilities/what-is-mcp.md](../agent-capabilities/what-is-mcp.md) — 主根拠。3大プリミティブの定義引用（Resources/Tools/Prompts、Toolsの「with user approval」）、天気サーバー（get_alerts / get_forecast）の実装手順と `@mcp.tool()` デコレータ・`mcp.run(transport="stdio")`、前提知識2点とPython 3.10以上・MCP SDK 2.0.0以上、STDIOサーバーで stdout に書いてはならない理由の引用と logging（stderr）推奨、claude_desktop_config.json の設定例と `which uv` の注記、「Servers can connect to any client」の根拠

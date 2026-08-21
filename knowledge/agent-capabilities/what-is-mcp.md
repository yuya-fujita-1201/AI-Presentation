---
type: Concept
title: MCPとは何か——AIと外部サービスをつなぐ接続規格
description: MCPをHost/Client/Serverの3者からなる接続規格として定義し、data layerとtransport layerの2層構造、Tools/Resources/Promptsの3大プリミティブ、STDIOとStreamable HTTPという2種のtransport、そして実際のサーバー実装がどんなコードなのかを、公式ドキュメントを一次根拠として整理する
tags: [agent-capabilities, mcp, protocol, ai-tools]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-21T10:35:00+09:00"
---

# MCPとは何か

[overview.md](./overview.md) の表で、MCPは「外部サービスへの接続口」と書いた。Skillが**ファイルに置いた手順書**であるのに対し、MCPは**別プロセスで動くサーバーへの通信規格**である。このファイルでは、その規格が何を決めていて何を決めていないのか、そして実物のサーバーがどんなコードなのかを見る。

根拠はMCP公式ドキュメント（[Architecture overview](../sources/article-tools-mcp-architecture-overview.md) / [Build an MCP server](../sources/article-tools-mcp-build-server.md)）である。どちらも一次資料（primary）にあたる。

## 一言定義

**MCPとは、AIアプリケーションが外部のツールやデータに接続するための共通の通信規格である。**

「規格」という言葉が重要で、MCPは接続の作法だけを決めている。公式ドキュメントは範囲をはっきり限定している。

> 引用: 「MCP focuses solely on the protocol for context exchange—it does not dictate how AI applications use LLMs or manage the provided context.」（[Architecture overview](../sources/article-tools-mcp-architecture-overview.md)）

つまり、**コンテキストをやり取りする手続きだけを規定し、AIアプリがLLMをどう使うか・受け取った文脈をどう管理するかには口を出さない**。ここがSkillとの根本的な違いになる。Skillは「AIにどう振る舞ってほしいか」を書くものだが、MCPは「どうやって繋ぐか」しか決めていない。

たとえるなら、MCPはUSBの規格に近い。USBは「どんな形の端子で、どんな信号を流すか」を決めるが、繋いだ先の機器が何をするかは決めない。だから一度対応すれば、どのホストからどの機器にも繋がる。

## 構成する4つのプロジェクト

[MCP公式ドキュメント](../sources/article-tools-mcp-architecture-overview.md)は、MCPを構成するプロジェクトとして次の4つを挙げている。

- **MCP Specification**: クライアント・サーバーの実装要件を定める仕様書
- **MCP SDKs**: 各言語向けのSDK
- **MCP Development Tools**: MCP Inspectorなどの開発ツール
- **MCP Reference Server Implementations**: サーバーのリファレンス実装

以降で扱う「規格」の話はSpecificationにあたる。実際にサーバーを書くならSDKs、動作確認にはMCP Inspectorのような開発ツールが要る、という位置づけである。

## 登場人物は3者

公式ドキュメントの説明が明快である。

> 引用: 「MCP follows a client-server architecture where an MCP host — an AI application like Claude Code or Claude Desktop — establishes connections to one or more MCP servers. The MCP host accomplishes this by creating one MCP client for each MCP server.」（[Architecture overview](../sources/article-tools-mcp-architecture-overview.md)）

| 役割 | 何か | 例 |
|---|---|---|
| **MCP Host** | AIアプリケーション本体 | Claude Code、Claude Desktop、VS Code |
| **MCP Client** | サーバー1つにつき1つ生成される接続担当 | （Hostが内部で作る） |
| **MCP Server** | ツールやデータを外に公開する側 | Sentry MCP server、filesystem server |

ここで初心者がつまずきやすいのが**Clientが「サーバーごとに1つ」生成される**点である。Hostが3つのサーバーに繋ぐなら、Client も3つ作られ、それぞれが専用のコネクションを維持する。公式ドキュメントはVS Codeがホストとなり、Sentry MCP server と local filesystem server のそれぞれに別個のMCP Clientオブジェクトを生成する例を挙げている。

「サーバー」という語から常時稼働の大掛かりなものを想像しがちだが、実態はそうとは限らない。同ドキュメントは「Local MCP servers that use the STDIO transport typically serve a single MCP client, whereas remote MCP servers that use the Streamable HTTP transport will typically serve many MCP clients.」と述べており、ローカルサーバーは通常あなた1人のために動く単一クライアント向けのプロセスである。

## サーバーが公開できるもの——3大プリミティブ

MCPサーバーが提供できる機能は3種類に整理されている。

> 引用: 「MCP servers can provide three main types of capabilities: 1. Resources: File-like data that can be read by clients (like API responses or file contents) 2. Tools: Functions that can be called by the LLM (with user approval) 3. Prompts: Pre-written templates that help users accomplish specific tasks」（[Build an MCP server](../sources/article-tools-mcp-build-server.md)）

| プリミティブ | 中身 | 平たく言うと |
|---|---|---|
| **Tools** | ファイル操作・API呼び出し・DB問い合わせなど実行可能な関数 | AIに使わせる「動詞」 |
| **Resources** | ファイル内容・DBレコードなどのコンテキストデータ | AIに読ませる「材料」 |
| **Prompts** | 対話テンプレート | 定型の頼み方 |

Toolsに「with user approval」と添えられている点に注目したい。**LLMが勝手に実行するのではなく、ユーザーの承認を経る**設計が規格の説明段階で明示されている。外部サービスを実際に操作する以上、当然の設計である。

公式クイックスタート自身も「このチュートリアルは主にToolsに焦点を当てる」としており、本バンドルもToolsを中心に扱う。まずは**Tools＝AIに使わせる関数を外から生やす仕組み**と理解しておけば足りる。

なお各プリミティブは `*/list`（発見）・`*/get`（取得）、場合により `tools/call`（実行）というメソッドを持つ。「まず一覧を出し、次に呼ぶ」という2段構えである。この**一覧が常に載る**という性質が、後述するコンテキスト消費の話につながる。

## 2層構造——data layer と transport layer

MCPは内側の data layer と外側の transport layer の2層でできている。

- **data layer**: JSON-RPCベースのプロトコル本体。capability・バージョンの発見、tools / resources / prompts といったコアプリミティブ、通知を定義する
- **transport layer**: 実際の通信手段。接続の確立、メッセージのフレーミング、認可を担う

分ける利点は明快で、**transportがどちらでも同一のJSON-RPC 2.0メッセージ形式が使える**。ローカル用に書いたサーバーをリモート公開しても、やり取りされるメッセージの中身は変わらない。

transportは2種類定義されている。

| transport | 用途 | 特徴 |
|---|---|---|
| **Stdio** | 同一マシン上のローカルプロセス間通信 | 標準入出力を使う。ネットワークのオーバーヘッドがなく性能面で最適 |
| **Streamable HTTP** | リモート通信 | HTTP POSTで送信、ストリーミングにはServer-Sent Eventsを任意で併用。bearer token・APIキー・カスタムヘッダーなど標準的なHTTP認証に対応し、公式は認証トークン取得にOAuthの利用を推奨している |

**ローカルのツールならStdio、外部サービスならStreamable HTTP**、と覚えておけばよい。手元で `npx` や `uv` を叩く形で起動するMCPサーバーは前者である。

## ステートレスであること

MCPは stateless protocol とされている。各リクエストは `_meta` フィールドにprotocol versionと関連capabilityを含めて送られ、**サーバーは過去のリクエストに依存せず処理できる**設計になっている。サーバーは必須の `server/discover` リクエストで、自分がサポートするバージョンとcapabilityを広告する。

実務上の含意は「サーバーが会話の文脈を覚えている前提で設計しなくてよい」ことである。公式ドキュメントの例では、`server/discover` のレスポンスに supportedVersions・capabilities（例: `"tools": {"listChanged": true}`）・ttlMs（キャッシュ有効期限、例 300000ms＝5分）が含まれることが示されている。

なお、クライアント側が提供するプリミティブとして Elicitation（`elicitation/create` でユーザーに追加情報を要求する）があるが、Sampling と Logging は protocol version 2026-07-28 で非推奨化され、公式は「New implementations should integrate directly with LLM provider APIs」「New implementations should log to stderr (stdio transport) or use OpenTelemetry」と明記している。**規格は動いており、古い解説記事の記述がそのまま有効とは限らない**点は押さえておきたい。

## 実物はどんなコードか

抽象的な話が続いたので、実際のサーバーを見る。公式クイックスタート「[Build an MCP server](../sources/article-tools-mcp-build-server.md)」が作るのは、米国国立気象局APIを叩いて `get_alerts`（州コードを受け取り警報一覧を返す）と `get_forecast`（緯度経度を受け取り予報を返す）の2つのツールを公開する天気サーバーである。

構造を分解すると、驚くほど普通のプログラムである。

1. サーバーインスタンスを初期化する（`mcp = MCPServer("weather")`）
2. APIのベースURLを定数で定義する（`NWS_API_BASE = "https://api.weather.gov"`）
3. HTTPリクエストとエラーハンドリングを担うヘルパー関数を書く
4. **公開したい関数に `@mcp.tool()` デコレータを付ける**
5. `mcp.run(transport="stdio")` で起動する

**MCPサーバーを書くとは、普通の関数にデコレータを1行付けることである。**前提知識として挙げられているのも「Python」と「LLMs like Claude」の2点のみで、MCP自体の事前知識は不要とされている（システム要件として Python 3.10 以上、Python MCP SDK 2.0.0 以上が明記されている）。

### STDIOサーバーでは print() を使ってはならない

初心者が確実に踏む地雷なので独立して書く。

> 引用: 「For STDIO-based servers: Never write to stdout. Writing to stdout will corrupt the JSON-RPC messages and break your server. The print() function writes to stdout by default, so keep it out of a STDIO server entirely.」（[Build an MCP server](../sources/article-tools-mcp-build-server.md)）

理由は構造から明らかで、**STDIOトランスポートは標準出力そのものを通信路として使っている**。デバッグのつもりで `print()` を1行入れると、JSON-RPCメッセージにゴミが混入してサーバーが壊れる。推奨されているのは標準ライブラリの `logging` モジュール（stderrに書き込む）を使い、`logging.getLogger(__name__)` でモジュールごとにロガーを作ることである。HTTPベースのサーバーなら標準出力ロギングは問題ないとされており、**制約はtransport種別によって違う**。

### 接続設定

Claude for Desktop の場合、macOSでは `~/Library/Application Support/Claude/claude_desktop_config.json` に `mcpServers` キーを置き、起動コマンドを書く。設定例は次の形である。

```json
{"mcpServers": {"weather": {"command": "uv",
  "args": ["--directory", "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather", "run", "weather.py"]}}}
```

公式は注記として、環境によっては `command` フィールドに `uv` 実行ファイルの絶対パスを指定する必要がある（macOS/Linuxなら `which uv` で取得できる）としている。設定の反映にはアプリの再起動が必要である。

重要なのは、サーバーがClaude専用ではないことだ。同ドキュメントは「Servers can connect to any client. We've chosen Claude for Desktop here for simplicity」と明言している。**一度書いたMCPサーバーは、MCPに対応した任意のホストから使える。**これが「規格」であることの実利である。

## 4手段の中でのMCPの位置

[Agent SDK overview](../sources/article-he-agent-sdk-overview.md) は、SDKの提供機能を列挙する中でMCPを「Model Context Protocol（MCP）経由で外部のツールやデータソースを接続する」機能として挙げ、Built-in tools・Hooks・Subagents・Permissions・Sessions・Skills / commands / memory・Plugins と同じ表に並べている。**MCPはSkillの代替ではなく、並列に置かれた別の口である**ことが公式の記述からも読み取れる。

一方で、MCPには構造上のコストがある。[Claude Skills入門動画](../sources/video-tools-claude-skills-beginner-guide.md)は、MCPは毎回余計な情報も読み込まなければならないため、それだけでトークン消費が大きくなる問題が発生していたと説明している（[17:00]、聞き取り）。この指摘自体はauto字幕由来だが、**接続中のサーバーのツール一覧が常にコンテキストに載る**という前述の構造（`*/list` で発見してから呼ぶ設計）と整合的である。同動画は同時に、SkillはMCPからの単純な進化形ではなくそもそも概念が異なるものだと補足している（聞き取り）。

どちらを選ぶかの判断は [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md)で扱う。ここでは**MCPは「外部サービスに繋ぐ」ときの手段であり、接続している間ずっと定額のコストを払う**という性質だけ持ち帰ればよい。

## 次に読む

- [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) — 同じ用事にSkill・MCP・CLIのどれを選ぶか
- [progressive-disclosure.md](./progressive-disclosure.md) — 「常に載る」ことがなぜコストなのかの前提
- [webmcp-and-frontier.md](./webmcp-and-frontier.md) — ブラウザ側でツールを公開するというMCPの拡張提案

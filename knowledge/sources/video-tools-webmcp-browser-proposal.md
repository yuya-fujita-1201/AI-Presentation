---
type: Video
title: WebMCPとは何か ブラウザ側で動くMCPの提案
description: WebサイトがAIエージェントに操作をツールとして構造化公開する仕組みWebMCPを対話形式で解説し、4要素構成、サーバー側MCPとの役割分担、Cloudflareのベンダー実装、Chromeでの検証手段と主要AI製品の対応未確認という現状を説明する動画
channel: chronoit
duration: "13:38"
published: 2026-08-12
retrieved: 2026-08-20
resource: https://www.youtube.com/watch?v=mkIUQtHvQow
origin: "youtube:UClRQ_q3uE62Ixlx-8gYCsAw"
subs: auto
tags: [webmcp, mcp, browser-agent, ai-tools, video]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-20T00:00:00+09:00"
---

# 概要

本動画は、WebサイトがAIエージェントに操作を「ツール」として構造化して公開する仕組みであるWebMCPを、対話形式で解説する動画である。これまでAIエージェントが画面の文言やDOM構造から操作方法を推測していた方式の問題点を起点に、WebMCPの4要素構成（name／description／inputSchema／execute）、サーバー側MCPとの役割分担、Cloudflareによるベンダー実装、Chromeでの検証手段までを順に説明している。動画の終盤では、標準化が進んでも「ツールの説明を信用できるかどうか」は別問題であるとし、主要AI製品での対応状況は現時点で公式に確認できないとしている。

# 要点

## WebMCPが解決しようとしている課題

- 動画は、これまでのAIエージェントによるサイト操作は、画面の文言とDOM構造を対応づけ、目的の要素を選択子や位置から探すという複数の推測処理の積み重ねだったと説明している
- サイトが更新されてボタンの文言やDOMの入れ子、レイアウトが変わると、それまで効いていた手がかりが外れ、エージェントは別の候補を再試行する必要が出てくるとしている（[00:00]〜[02:00]）
- 動画は、この壊れやすさは「操作の意味を画面から推測する部分」に集中しており、手順が長いほど探索と再試行が増えやすいと整理している

## WebMCPのツール構成（4要素）

- WebMCPでは、サイト側がdocument.modelContextのregisterToolを通じて、公開したい操作をツールとして登録すると説明している
- ツールはname（操作を識別する名前）・description（自然言語での用途説明）・inputSchema（JSON Schemaによる入力形式）・execute（引数を受けて既存機能を呼ぶ実行処理）の4要素で構成されるとしている（[02:00]〜[03:00]）
- ツールはページの状態に応じて動的に増減でき、ログイン前後や選択中の対象によって公開するツールを変えられるとしている。取り消しにはAbortSignalを使うと説明している
- 登録方法にはJavaScriptによる命令型のほか、HTMLフォームをもとにした宣言型も提案されているが、宣言型は命令型ほど仕様が固まっておらず、呼び出し側（getTools・executeTool）の仕様も未確定（TODO）だとしている（[04:00]）

## WebMCPとサーバー側MCPの使い分け

- 動画は、両者の切り分け軸を「接続先」と「実行場所」の2つだと説明している。サーバー側MCPは画面やタブを介さず外部からサービスへ接続するのに対し、WebMCPは開いているページ自身がツールを公開し、そのページのブラウザ内で処理を実行するとしている（[04:00]〜[05:00]）
- 今の画面や訪問者の権限を使いたい場合はWebMCP、ブラウザを開いていない状態でサービスに繋ぐ場合はサーバー側MCPが向くとし、同じサービスが両方を併用する構成も成立すると説明している（[06:00]）
- WebMCPはMCP通信全体をブラウザに移したものではなく、生成元ごとの境界やPermissions Policyといったブラウザ固有の制約に合わせて、ページ内の操作公開に絞って設計されていると説明している

## Cloudflareによるベンダー実装（標準そのものではない点に注意）

- 動画は、WebMCPが提案段階である一方、Cloudflareが既存サイトへの橋渡し機能をDeveloper Previewとして提供していると紹介している（[06:00]〜[08:00]）
- 管理画面のAgent Readiness > LabsでEnable WebMCPを有効にすると、HTMLRewriterが橋渡し用スクリプト（bridge.js）を挿入し、選択したTool packsをdocument.modelContextへ登録する仕組みだとしている
- Tool packsには「Content Credentials」（画像のC2PA来歴情報をエージェントへ渡すもので、署名を新規生成する機能ではない）と「Site MCP server」（サイト自身のMCPサーバーが公開したツールをCloudflareが中継する）の2種類があると説明し、いずれもWebMCPの標準そのものではなくCloudflare独自の実装だと繰り返し強調している

## 公開範囲の制御と未確定な論点

- ツールを誰に見せるかはiframeの生成元によって変わり、最上位文書と同じ生成元のiframeは既定で利用できる想定だが、異なる生成元はallow属性でtoolsを明示的に委譲する必要があるとしている（[08:00]〜[09:00]）
- WebMCPを有効にしても権限が自動で増えることはなく、実行に使われるのは訪問者が既に持つログイン状態と権限のみだとしている。Permissions Policyでtoolsを空にすると、その文書はツールを公開できなくなるとも説明している
- 公開先をエージェントの生成元単位で絞るexposedToという案もあるが、これも提案中で確定していないとしている
- 副作用のある操作を実行する前の確認をブラウザとエージェントのどちらが担うかは未決であり、悪意あるページがツール名や説明・戻り値でエージェントの判断を誘導する懸念も論点に挙がっていると紹介している（[09:00]〜[10:00]）

## 検証手段とAI製品での対応状況

- Chromeでの公開試験（origin trial）の対象はChrome 149から156であり、Cloudflareの検証文書に残るChrome 146という数字は古い記述で公開試験の対象ではないと訂正している（[10:00]〜[11:00]）
- 公開サイトでの試験にはChromeのorigin trial登録、ローカル試験にはChromeのflags画面でのenable WebMCP testingという別々の入口があるとしている
- Claude・ChatGPT・Gemini・Perplexityが実際にWebMCPを呼べるかどうかは、対応を肯定も否定もできる一次資料が見当たらず、公式には確認できていないと明言している（[11:00]〜[13:00]）
- 検証にはCloudflare Browser Runも使え、wrangler browser createでlab・keepAlive 300のセッションを作り、navigator.modelContextTestingのlistTools・executeToolで試験的に呼び出せるが、これはページ作者が使うdocument.modelContextとは別の試験専用の入口であり、試験で呼べることと一般製品での採用は別問題だと注意を促している
- 動画は最後に、標準化されるのはツールの「受け渡し方」だけであり、ページが何を書くか・悪意ある説明にどう備えるかは別途決まっていく論点だと締めくくっている

# 主張テーブル

| claim_id | タイムスタンプ | 主張 | 出所種別 | impact |
|---|---|---|---|---|
| c1 | [00:00] | WebMCPはWebサイトがAIエージェントに操作をツールとして構造化して公開する仕組みの提案である | auto字幕 | high |
| c2 | [02:00] | WebMCPのツールはname・description・inputSchema・executeの4要素で構成される | auto字幕 | high |
| c3 | [06:00] | 画面の状態や訪問者の権限を使いたい場合はWebMCP、ブラウザを開かず外部からサービスに繋ぐ場合はサーバー側MCPが向く | auto字幕 | normal |
| c4 | [10:00] | ChromeにおけるWebMCPのorigin trial対象はChrome 149から156である | auto字幕 | high |
| c5 | [13:00] | Claude・ChatGPT・Gemini・PerplexityがWebMCPを呼べるかどうかは公式に確認できていない | auto字幕 | high |

# 活用先

- [../agent-capabilities/webmcp-and-frontier.md](../agent-capabilities/webmcp-and-frontier.md) — 主根拠（本ファイルはWebMCPに関する唯一の出所であり、コンセプト側で帰属＋（聞き取り）を明示している）。DOM/文言からの推測に依存する従来方式の壊れやすさ（[00:00]〜[02:00]）、`document.modelContext` の `registerTool` と name/description/inputSchema/execute の4要素（[02:00]）、ツールの動的増減と `AbortSignal`、宣言型および `getTools`/`executeTool` が未確定（TODO）であること（[04:00]）、「接続先」「実行場所」という2軸でのサーバー側MCPとの使い分け（[06:00]）、Cloudflareの Agent Readiness > Labs / HTMLRewriter による `bridge.js` 挿入と2種のTool packs（Content Credentials・Site MCP server）がいずれも標準ではないこと（[06:00]〜[08:00]）、iframe生成元と `allow` 属性による `tools` 委譲・Permissions Policy・`exposedTo` 案が未確定であること・副作用操作の確認責任が未決であること・悪意あるページが説明や戻り値で判断を誘導する懸念（[08:00]〜[10:00]）、origin trial対象がChrome 149〜156でありChrome 146は古い記述だという訂正・flags画面と `navigator.modelContextTesting` が試験専用の入口であること（[10:00]〜[11:00]）、Claude・ChatGPT・Gemini・PerplexityのWebMCP対応は公式に確認できないという明言（[11:00]〜[13:00]）の根拠

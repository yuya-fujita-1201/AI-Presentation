# agent-capabilities — AIに能力を足す4つの手段についてのナレッジ

チャット型AIを使ったことはあるが、エージェント的な活用は未経験——という読者を想定して、「AIに能力を足す」とは何をすることかを、**プロンプト・Skill・MCP・CLI**という4つの手段に分けて整理したディレクトリ。Anthropic公式ドキュメント（Agent Skills / Skill authoring best practices / Agent SDK）3本とAnthropicエンジニアリングブログ1本、MCP公式ドキュメント（Architecture overview / Build an MCP server）2本を一次側の根拠に、日本語の解説動画4本と実務記事3本を突き合わせている。台帳は [../sources/index.md](../sources/index.md) の「動画（AIツール活用：Skills/MCP/CLI/プロンプト）」「記事（AIツール活用：Skills/MCP/CLI/プロンプト）」の節を参照。

自動生成字幕のみを出所とする主張は、本バンドル内では帰属を明示し「（聞き取り）」を付けて記述している。断定的な定義・数値・仕様は公式ドキュメント側で裏を取ったもののみ。

## 内容

入口は [overview.md](./overview.md)（「能力を足す」の定義・4手段の比較表・バンドルの地図）。以下は overview.md の地図の表と同じ並びで、各ファイルの見出し語だけを挙げる。内容説明と読む順番の根拠は overview.md 側で一元管理しており、ここでは重複させない。

1. [what-are-agent-skills.md](./what-are-agent-skills.md) — Skillとは何か（指示書＋スクリプトのフォルダ）
2. [progressive-disclosure.md](./progressive-disclosure.md) — 段階的開示の3階層とトークンコスト
3. [writing-good-skills.md](./writing-good-skills.md) — 起動されるSkillの書き方と失敗パターン
4. [what-is-mcp.md](./what-is-mcp.md) — MCPの構造と3大プリミティブ
5. [choosing-skill-mcp-or-cli.md](./choosing-skill-mcp-or-cli.md) — 同じ用事にどれを選ぶか
6. [prompts-and-project-rules.md](./prompts-and-project-rules.md) — プロンプトとプロジェクトルールの設計指針
7. [distribution-and-governance.md](./distribution-and-governance.md) — 配布・バージョン管理・ライセンス・セキュリティ
8. [webmcp-and-frontier.md](./webmcp-and-frontier.md) — ブラウザ側MCPという提案と未確定の論点

## 読む順番

[overview.md](./overview.md) の「このバンドルの地図」節にある8本の順序表と「読む順番の提案」（全体像だけ掴む／自分で作る／導入判断をする、の3コース）に従うこと。読む順番はこのファイルではなく overview.md 側で一元管理する。

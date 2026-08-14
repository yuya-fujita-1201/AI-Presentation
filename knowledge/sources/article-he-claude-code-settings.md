---
type: Article
title: Claude Code settings - Claude Code Docs
description: Claude Codeの設定を適用するManaged/User/Project/Localの4スコープと、その優先順位・想定用途を解説する公式文書
site: Anthropic
published: unknown
retrieved: 2026-08-14
resource: https://code.claude.com/docs/en/settings
origin: "web:claude.com"
source_tier: primary
tags: [harness-engineering, claude-code, settings, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-14T00:00:00+09:00"
---

# 概要

Anthropic公式のClaude Code Docsは「Claude Code settings」という文書で、グローバル設定・プロジェクトレベル設定・環境変数によってClaude Codeの動作を構成する方法を解説している。同文書によると、インタラクティブセッション内で`/config`コマンドを実行すると、ステータス情報の閲覧や設定オプションの変更ができるタブ形式のSettingsインターフェースが開く。またv2.1.181以降は、このインターフェースを開かずに`/config key=value`のように渡すことで単一オプションを変更できるようになったとしている(例: `/config verbose=true`)。

# 要点

## 設定を適用するスコープシステム

同文書は、Claude Codeが設定の適用範囲と共有先を決めるためにスコープシステムを採用していると説明する。スコープを理解することで、個人利用・チーム協業・エンタープライズ展開のいずれの目的にもClaude Codeを構成しやすくなるとしている。

## 4つのスコープの所在と共有範囲

利用可能なスコープはManaged・User・Project・Localの4種類である。

> 引用: 「Managed (highest): can't be overridden by any other scope, apart from the exceptions to managed settings precedence」

Managedスコープは、サーバー管理設定・plistやレジストリ・システムレベルの`managed-settings.json`に置かれる。サーバー管理配信の場合は組織の全メンバーに、plist・HKLMレジストリ・ファイル配信の場合はマシン上の全ユーザーに、HKCUレジストリ配信の場合は現在のユーザーに影響し、ITによってデプロイされチームと共有されるとしている。

Userスコープは`~/.claude/`ディレクトリに置かれ、そのユーザー自身に全プロジェクトを横断して影響するが、チームとは共有されない。Projectスコープはリポジトリ内の`.claude/`ディレクトリに置かれ、そのリポジトリの全コラボレーターに影響し、gitにコミットされることでチームと共有される。Localスコープはリポジトリルートの`.claude/settings.local.json`に置かれ、そのリポジトリ内での自分自身にのみ影響し、Claude Codeが設定を保存する際にgitignoreされるためチームとは共有されないと説明されている。

同文書は、Managedスコープ単体の中にも複数の配信経路があると整理している点が特徴的である。サーバー管理による配信・plist配信・Windowsのレジストリ(HKLMまたはHKCU)配信・ファイル配信のいずれを使うかによって「誰に影響が及ぶか」が変わり、組織全体への配信もマシン単位の配信もこの1つのスコープ区分の中に含まれるとしている。User・Project・Localの3スコープが「どこに置かれたファイルか」という単純な基準で区別されるのに対し、Managedスコープだけは配信方式そのものが影響範囲を左右する点で性質が異なるといえる。

## 各スコープの想定用途

同文書は、Managedスコープは組織全体で強制すべきセキュリティポリシー、上書きできないコンプライアンス要件、IT/DevOpsによる標準化された設定に向くとしている。Userスコープはテーマやエディタ設定など全プロジェクトで使いたい個人の好み、複数プロジェクトで使うツールやプラグイン、APIキーや認証情報の安全な保存に適するとされる。Projectスコープは権限・フック・MCPサーバーなどチームで共有すべき設定、チーム全体が持つべきプラグイン、コラボレーター間のツール標準化に向くとしている。Localスコープは特定プロジェクトに対する個人的な上書き、チームに共有する前の設定のテスト、他の人には合わないマシン固有の設定に向くと説明されている。

## スコープ間の優先順位

同一の設定が複数のスコープに現れた場合、Claude Codeは優先順位に従って適用すると同文書は述べている。優先順位は上から、(1) Managed(最高。managed settings precedenceの例外を除き他のいかなるスコープにも上書きされない)、(2) コマンドライン引数(一時的なセッション上の上書き)、(3) Local(ProjectとUserの設定を上書き)、(4) Project(User設定を上書き)、(5) User(最低。他に何も指定がない場合にのみ適用される)の順である。

具体例として、ユーザー設定で`spinnerTipsEnabled`を`true`に、プロジェクト設定で`false`に設定した場合、プロジェクト側の値が適用されると説明されている。ただし権限ルールはこの優先順位とは異なりスコープを横断してマージされる方式を取り、一部のセキュリティ関連の設定キーはこの優先順位の例外になるとしている。

# 活用先

- [../harness-engineering/settings-scopes-and-governance.md](../harness-engineering/settings-scopes-and-governance.md) — スコープシステムの採用理由、Managed/User/Project/Localの所在と共有範囲、Managedだけ配信経路が影響範囲を左右すること、優先順位の5段階と`spinnerTipsEnabled`の具体例、各スコープの想定用途、権限ルールがマージ方式でありセキュリティ関連キーが例外になること、Localがgitignoreされること、`/config`と`/config key=value`（v2.1.181以降）の根拠

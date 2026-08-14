# context-engineering — コンテキストエンジニアリング

チャット型AIを使ったことはあるが、エージェント的な活用には慣れていない新入社員・IT職・SEを主な読者とする。コンテキストエンジニアリングを「長いプロンプトを書くこと」ではなく、**AIがある時点で仕事をするために参照する情報を、選び、配置し、更新する設計**として扱う。

本ディレクトリは、2026-08-14に確認した[sources台帳](../sources/index.md)21件を根拠にする。内訳は公式ドキュメント・原著論文と、二次記事・解説動画である。**定義・数値・仕様に関わる主張は公式資料と原著を根拠にし、解説動画（auto字幕）由来の主張は帰属を明示して断定を避ける**方針で書いている。製品固有の窓長、料金、キャッシュTTL、保持日数などは変わるため、固定値として一般化しない。

## 学習の地図

### 0. 全体地図

- [five-engineering-scopes.md](./five-engineering-scopes.md) — プロンプト／コンテキスト／ハーネス／ループ／グラフのスコープ差と入れ子関係、症状別の切り分け

### 1. 定義と材料

- [what-is-context-engineering.md](./what-is-context-engineering.md) — 定義、プロンプトエンジニアリングとの重なり、「何を・いつ・どれだけ」という3つの設計質問
- [context-components.md](./context-components.md) — 推論時に入りうる情報と、目的・読み手・状況・制約・既存資産という5項目

### 2. 選択と容量

- [selection-and-sufficiency.md](./selection-and-sufficiency.md) — 必要性・十分性・信頼性・鮮度による選別、競合情報、選別記録
- [context-window-and-attention.md](./context-window-and-attention.md) — ウィンドウ、履歴、外部メモリ、学習済み知識の区別。長文研究の結果と留保
- [context-rot-and-editing.md](./context-rot-and-editing.md) — 足すほど薄まる理由（注意の有限性・位置バイアス）と、「足すより編集する」判断

### 3. 層と長期運用の部品

- [context-layers-and-intervention.md](./context-layers-and-intervention.md) — 介入点としての5層（システムプロンプト〜会話履歴。「0. 全体地図」の5層地図とは別の切り口）、症状別の直し方、Write/Select/Compress/Isolateと圧縮機能
- [retrieval-memory-compaction-cache.md](./retrieval-memory-compaction-cache.md) — RAG、外部メモリ、コンパクション、Prompt cacheの役割と「しないこと」
- [long-horizon-and-tools.md](./long-horizon-and-tools.md) — 段階的開示、ツール定義・結果、状態ファイル、セッション間の引き継ぎ

### 4. 安全と実践

- [security-and-trust-boundaries.md](./security-and-trust-boundaries.md) — prompt injection、機密データ、信頼境界、最小権限、人の承認
- [practical-context-packs.md](./practical-context-packs.md) — 5項目と4観点をまとめたコピー可能なコンテキストパック、障害報告例、更新と評価

## 推奨する読み順

初学者は、`what-is-context-engineering` → `context-components` → `selection-and-sufficiency` → `context-rot-and-editing` → `practical-context-packs` の順で読む。ここまでで、普段のチャットや文書作成に使える。用語の氾濫に戸惑っている場合は、先頭に `five-engineering-scopes` を置いて全体像から入ってもよい。

システム設計まで扱う場合は、その後に `context-window-and-attention` → `context-layers-and-intervention` → `retrieval-memory-compaction-cache` → `long-horizon-and-tools` → `security-and-trust-boundaries` へ進む。安全の章は最後に置いているが、安全確認は実装の最後に足す工程ではない。各章へ戻りながら適用する。

## 教材上の整理と非標準性

本バンドルで使う次の整理は、初心者が判断しやすくするための教材上のフレームであり、業界標準規格ではない。

- AI活用をプロンプト／コンテキスト／ハーネス／ループ／グラフに分ける5層地図（**同じ「5層」という呼称を、コンテキストをシステムプロンプト〜会話履歴に分ける[context-layers-and-intervention.md](./context-layers-and-intervention.md)の5層でも使っているが、両者は別の切り口である。前者はコンテキストエンジニアリングを含む活動全体の外側からの分類、後者はコンテキストという1つの層を内側からさらに分解したもの**）
- 依頼の前提を目的／読み手／状況／制約／既存資産で確認する5項目
- 情報を必要性／十分性／信頼性／鮮度で選ぶ4観点
- コンテキストパックという実践上の呼び名とテンプレート

一方、RAG・メモリ・コンパクション・Prompt cacheの役割差、コンテキストウィンドウの有限性、prompt injectionやデータ境界のリスクは、一次資料と原著に基づいて記述する。各ファイルのリンクから根拠へ戻れる。

## 関連

- [../prompt-engineering/index.md](../prompt-engineering/index.md) — 1回の指示の組み立て方。両領域は重なり、どちらかが他方を置き換えるものではない
- [../graph-engineering/index.md](../graph-engineering/index.md) — 複数AI・工程・依存関係の設計。コンテキストパックはノード間の受け渡しにも使える
- [../slide-system/index.md](../slide-system/index.md) — 本ナレッジからデッキを作るパラメーター駆動スライドシステム

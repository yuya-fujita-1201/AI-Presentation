# context-engineering — コンテキストエンジニアリング

チャット型AIを使ったことはあるが、エージェント的な活用には慣れていない新入社員・IT職・SEを主な読者とする。コンテキストエンジニアリングを「長いプロンプトを書くこと」ではなく、**AIがある時点で仕事をするために参照する情報を、選び、配置し、更新する設計**として扱う。

本ディレクトリは、2026-08-14に確認した公式一次資料・原著12件（[sources台帳](../sources/index.md)）を中核にする。製品固有の窓長、料金、キャッシュTTL、保持日数などは変わるため、固定値として一般化しない。

## 学習の地図

### 1. 定義と材料

- [what-is-context-engineering.md](./what-is-context-engineering.md) — 定義、プロンプトエンジニアリングとの重なり、「何を・いつ・どれだけ」という3つの設計質問
- [context-components.md](./context-components.md) — 推論時に入りうる情報と、目的・読み手・状況・制約・既存資産という5項目

### 2. 選択と容量

- [selection-and-sufficiency.md](./selection-and-sufficiency.md) — 必要性・十分性・信頼性・鮮度による選別、競合情報、選別記録
- [context-window-and-attention.md](./context-window-and-attention.md) — ウィンドウ、履歴、外部メモリ、学習済み知識の区別。長文研究の結果と留保

### 3. 長期運用の部品

- [retrieval-memory-compaction-cache.md](./retrieval-memory-compaction-cache.md) — RAG、外部メモリ、コンパクション、Prompt cacheの役割と「しないこと」
- [long-horizon-and-tools.md](./long-horizon-and-tools.md) — 段階的開示、ツール定義・結果、状態ファイル、セッション間の引き継ぎ

### 4. 安全と実践

- [security-and-trust-boundaries.md](./security-and-trust-boundaries.md) — prompt injection、機密データ、信頼境界、最小権限、人の承認
- [practical-context-packs.md](./practical-context-packs.md) — 5項目と4観点をまとめたコピー可能なコンテキストパック、障害報告例、更新と評価

## 推奨する読み順

初学者は、`what-is-context-engineering` → `context-components` → `selection-and-sufficiency` → `practical-context-packs` の順で読む。ここまでで、普段のチャットや文書作成に使える。

システム設計まで扱う場合は、その後に `context-window-and-attention` → `retrieval-memory-compaction-cache` → `long-horizon-and-tools` → `security-and-trust-boundaries` へ進む。安全の章は最後に置いているが、安全確認は実装の最後に足す工程ではない。各章へ戻りながら適用する。

## 教材上の整理と非標準性

本バンドルで使う次の整理は、初心者が判断しやすくするための教材上のフレームであり、業界標準規格ではない。

- AI活用をプロンプト／コンテキスト／ハーネス／ループ／グラフに分ける5層地図
- 依頼の前提を目的／読み手／状況／制約／既存資産で確認する5項目
- 情報を必要性／十分性／信頼性／鮮度で選ぶ4観点
- コンテキストパックという実践上の呼び名とテンプレート

一方、RAG・メモリ・コンパクション・Prompt cacheの役割差、コンテキストウィンドウの有限性、prompt injectionやデータ境界のリスクは、一次資料と原著に基づいて記述する。各ファイルのリンクから根拠へ戻れる。

## 関連

- [../prompt-engineering/index.md](../prompt-engineering/index.md) — 1回の指示の組み立て方。両領域は重なり、どちらかが他方を置き換えるものではない
- [../graph-engineering/index.md](../graph-engineering/index.md) — 複数AI・工程・依存関係の設計。コンテキストパックはノード間の受け渡しにも使える
- [../slide-system/index.md](../slide-system/index.md) — 本ナレッジからデッキを作るパラメーター駆動スライドシステム

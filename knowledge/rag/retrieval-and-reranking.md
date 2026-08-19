---
type: Concept
title: 検索とリランキング——ベクトル検索だけでは足りない理由
description: ベクトル検索の強みと弱点を出発点に、ハイブリッド検索・クエリ側の工夫・リランキングという3つの打ち手を、再現率と適合率のトレードオフという軸で整理する
tags: [rag, retrieval, reranking, hybrid-search, bm25, recall-precision]
generated:
  by: claude-code/pipeline-opus
  at: "2026-08-19T00:00:00+09:00"
---

# 検索とリランキング

RAGの回答品質は、検索で何を拾えたかでほぼ決まる。Qiitaのkentarok氏は、この構造を「生成AIが答える内容は、検索で何を拾ってきたかにほぼ依存する」と端的に書いている（[組織内情報集約RAGの実用化設計①](../sources/article-rag-qiita-kentarok-poc-production-gap.md)）。拾えなかった文書の内容は、どれだけ賢いLLMを使っても回答に現れない。

前の節では質問が来る前の工程（[チャンク分割と埋め込み](chunking-and-embedding.md)）を扱った。この節は、質問が来てから走る側——**検索**と**リランキング**——を扱う。

## ベクトル検索は何が得意で何が苦手か

まず、ベクトル検索が何を解決したのかを確認する。普通のキーワード検索は語が一致するかどうかで探すため、意味が似ている文章を探すのには向いていない。「疲れた」で検索しても「体が重たい」という文章は引っかからない。一方ベクトル検索は文書の意味を数値（ベクトル）で表現して保存するため、語が違っても意味の近さで順位付けして拾える——という対比で説明されている（[Supabase自作RAG](../sources/video-rag-supabase-diy-chatbot.md)）。

社内文書検索でこれは効く。「有給って何日もらえる?」という口語の質問に対し、「年次有給休暇の付与日数」という条文見出しを拾えるのはこの性質のおかげである。

ところが、**同じ性質が弱点にもなる**。TodoONada株式会社は、ベクトル検索が「型番・固有名詞・略語の完全一致に弱い」と指摘し、例として「XR-2000」を「XR-3000」と混同するケースを挙げている（[社内文書RAGの作り方2026](../sources/article-rag-todoonada-pipeline-guide.md)）。意味の近さで探す仕組みだから、**意味は限りなく近いが指すものが違う**——型番・部署コード・年度・バージョン番号のようなものを取り違える。

これは実務では致命傷になりうる。「2024年版」と「2023年版」の規程を区別できないという失敗は、実際に本番展開時の典型パターンとして報告されている（[組織内情報集約RAGの実用化設計①](../sources/article-rag-qiita-kentarok-poc-production-gap.md)）。

## 打ち手1: ハイブリッド検索

弱点の補い方は素直で、**苦手な方式を併用する**。ベクトル検索に、キーワードの完全一致を見る伝統的な検索手法BM25を組み合わせることで検索漏れを減らす手法が、ハイブリッド検索と呼ばれる（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

TodoONada株式会社は、これを選択肢の1つではなく**実務標準**だと位置づけている。同社は構築前チェックリストにも「ハイブリッド検索を前提とした設計」を挙げており、ベクトルDBの比較でも、既存PostgreSQL拡張で中小規模向けのpgvectorと、大規模・高スループット向けでハイブリッド検索にネイティブ対応するQdrantを並べている（[社内文書RAGの作り方2026](../sources/article-rag-todoonada-pipeline-guide.md)）。

配合比はどうするか。門脇篤志氏は具体的なブレンド例として「キーワード検索を50%、セマンティック検索を50%の割合で検索に活用する」ことも可能だと紹介している。ただし同氏はこれを固定的な正解として示しているわけではなく、**最適なブレンド割合は想定される質問内容に依存する**と説明している（[RAGでの回答精度向上のためのテクニック集](../sources/article-rag-knowledgesense-retrieval-techniques.md)）。型番で引くことが多い部品カタログと、口語で聞かれる社内規程では、当然ながら寄せどころが違う。

なお、前節で触れたAnthropicのContextual Retrievalは、この語彙マッチング側にも文脈を足す（Contextual BM25）という構成になっている。同社の報告では、Contextual EmbeddingsとContextual BM25を組み合わせると検索失敗率は**49%削減の2.9%**になったとされる（[Contextual Retrieval in AI Systems](../sources/article-rag-anthropic-contextual-retrieval.md)）。文脈付加とハイブリッド検索は、どちらか一方ではなく重ねるものだと読める。

## 打ち手2: 質問の側をいじる

検索が当たらない原因は、索引側だけにあるとは限らない。質問文が曖昧だったり、文書内の言葉と一致しなかったりする場合がある。kentarok氏は、略称・コードネーム・部署固有用語・表記揺れといった言語的曖昧性により、**質問文と文書内の言葉が一致しない**という問題を組織内情報の構造的課題として挙げている（[組織内情報集約RAGの実用化設計①](../sources/article-rag-qiita-kentarok-poc-production-gap.md)）。

対処は2系統ある。

**クエリ変換**は、ユーザーの入力が曖昧・複雑な場合に、LLMを使って検索に適した形に書き換えたり、複数のサブクエリに分解したりする技術として紹介されている（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。「去年の経費のやつどうなった?」を「2025年度 経費精算 規程 改定」に直してから検索する、というイメージである。

**HyDE**は、ユーザーの質問に対するダミー回答をLLMで生成し、そのダミー回答を使ってセマンティック検索を実行する手法である。質問文より回答文の方が、文書中の記述に語彙的・意味的に近いことを利用する。ただし門脇氏は「ダミー回答の質によって検索の精度が左右される」と述べており、得意な領域と不得意な領域がはっきり分かれる手法だと説明している（[RAGでの回答精度向上のためのテクニック集](../sources/article-rag-knowledgesense-retrieval-techniques.md)）。

## 打ち手3: リランキング

ハイブリッド検索でもクエリ変換でも解けない問題が残る。**広く拾えば拾うほど、ノイズも混ざる**という問題である。

解説動画は、検索の性能は再現率（リコール）と適合率（プレシジョン）という2つの指標で評価され、両者はトレードオフの関係にあると説明している。広く検索して再現率を上げようとすると不要な情報も増え、適合率が下がりがちだとしている（聞き取り）（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

このトレードオフを2段階に分けて解くのがリランキングである。最初の検索で得られた複数のチャンク候補を、より精度の高いモデル——質問と文章をペアで入力して関連度をスコアリングするクロスエンコーダーのような、計算コストの高いモデル——で本当に関連性が高い順に並べ替える。同動画はこれを「最初の検索は速度重視で広く候補を集め、ランキングで精度を重視して絞り込む」という2段階戦略だと説明している（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）。

つまり、**1段目で再現率を、2段目で適合率を取りにいく**。安い検索で網を広く張り、高い計算をその中の少数にだけ使う、という費用配分である。

具体的な数字はAnthropicが示している。同社の実装では、上位150チャンクを取得したのちCohereなどのリランキングモデルに通し、関連性で上位20チャンクへ絞り込む処理を行う。これをContextual Embeddings＋Contextual BM25に加えると、検索失敗率は**67%削減の1.9%**まで改善したとしている。同社はこの結論を「Reranked Contextual Embedding and Contextual BM25 reduces the top-20-chunk retrieval failure rate by 67%」と述べている（[Contextual Retrieval in AI Systems](../sources/article-rag-anthropic-contextual-retrieval.md)）。

改善の積み上がりを並べると、効きどころが見える。

| 構成 | 検索失敗率 | 削減率 |
|---|---|---|
| ベースライン | 5.7% | — |
| ＋Contextual Embeddings | 3.7% | 35% |
| ＋Contextual BM25（ハイブリッド） | 2.9% | 49% |
| ＋リランキング | 1.9% | 67% |

（いずれもAnthropicが自社実験として報告している数値。[Contextual Retrieval in AI Systems](../sources/article-rag-anthropic-contextual-retrieval.md)）

コスト面でもリランキングは入れやすい。TodoONada株式会社は、国産リランカーが「CPUで動く軽さで、既存構成に数行足すだけで導入できます」とし、「GPUへの追加投資なしで検索品質が上がる、最も費用対効果の高い一手」と評価している（[社内文書RAGの作り方2026](../sources/article-rag-todoonada-pipeline-guide.md)）。

## 何件渡すか

リランキング後に何件をLLMへ渡すかも設計項目である。Anthropicは推奨設定として、取得チャンク数は5や10よりも**20の方が効果的**だとしている（[Contextual Retrieval in AI Systems](../sources/article-rag-anthropic-contextual-retrieval.md)）。

ただし無制限に増やせるものではない。検索件数を増やすとコストも処理時間も増えるため、そこは微調整が必要だとされている（[Supabase自作RAG](../sources/video-rag-supabase-diy-chatbot.md)）。さらに、渡す量を増やすと今度は**LLMが読み落とす**という別種の失敗が出てくる。この境目は[どこで壊れるか](failure-modes.md)で見たFP3・FP7の話である。

## さらに上の手

ここまでで足りない場合の選択肢も、参照した資料には挙がっている。

- **Parent Document Retriever**: 検索自体は小さいチャンクで精度高く行い、LLMに渡す際にはそのチャンクを含む元の大きな文書（親文書）を渡すことで、より広い文脈を考慮させる手法（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）
- **ナレッジグラフ**: 情報をグラフデータベースに保管し、質問内容に対する網羅的な知識の獲得を目指す手法。門脇氏は**上級テクニック**と位置づけている（[RAGでの回答精度向上のためのテクニック集](../sources/article-rag-knowledgesense-retrieval-techniques.md)）
- **Self-RAG**: LLM自身が検索の要否や検索結果の十分性を評価し、不十分なら再検索を行う、より自律的な仕組みも研究されているとされる（[RAGの歴史・仕組み・限界](../sources/video-rag-history-mechanism-limits.md)）

Self-RAGの方向は、決まった手順で1回検索して答える通常のRAGから、**判断しながら検索を繰り返す**方向への拡張にあたる。この境界線（決まった手順で1回引くのか、判断しながら繰り返すのか）は、RAGと[エージェント的検索](rag-and-neighbors.md)を切り分ける論点そのものである。

## この節の要点

- ベクトル検索は言い換えに強い一方、型番・固有名詞・略語の完全一致に弱い（「XR-2000」と「XR-3000」の取り違え）
- 弱点はBM25との併用（ハイブリッド検索）で補う。実務標準とされ、配合比は想定される質問内容に依存する
- 質問側の工夫としてクエリ変換とHyDEがある。HyDEはダミー回答の質に精度が左右され、得手不得手が分かれる
- 再現率と適合率はトレードオフの関係にあるとされ、1段目で広く集め2段目のリランキングで絞るのが定石
- Anthropicの報告では、文脈付加→ハイブリッド→リランキングの順に検索失敗率が5.7%→3.7%→2.9%→1.9%と積み上がる
- リランカーはCPUで動く軽さのものがあり、「最も費用対効果の高い一手」と評価されている
- 渡す件数は20件程度が効果的とされるが、コスト・処理時間・LLMの読み落としとの兼ね合いになる

# Citations

- [Contextual Retrieval in AI Systems](../sources/article-rag-anthropic-contextual-retrieval.md) — Contextual EmbeddingsとContextual BM25の併用で49%削減（2.9%）、上位150チャンク取得→Cohere等のリランカーで上位20へ絞る処理、リランキング追加で67%削減（1.9%）という数値と結論文、取得チャンク数は20が5や10より効果的という推奨の根拠
- [社内文書RAGの作り方2026。パース・埋め込み・リランクの最新構成](../sources/article-rag-todoonada-pipeline-guide.md) — ベクトル検索が型番・固有名詞・略語の完全一致に弱いこと（XR-2000／XR-3000の例）、ハイブリッド検索が実務標準であること、pgvectorとQdrantの比較、国産リランカーが「CPUで動く軽さ」で「最も費用対効果の高い一手」という評価の根拠
- [RAGでの回答精度向上のためのテクニック集（応用編-A）](../sources/article-rag-knowledgesense-retrieval-techniques.md) — ハイブリッド検索の50%対50%というブレンド例と最適割合が質問内容に依存するという説明、HyDEの仕組みと「ダミー回答の質によって検索の精度が左右される」という留保、ナレッジグラフを上級テクニックとする位置づけの根拠
- [検索拡張生成(RAG)とは？LLMの嘘と知識不足を克服する仕組みを歴史から最新技術まで解説](../sources/video-rag-history-mechanism-limits.md) — 再現率と適合率のトレードオフ（auto字幕・帰属付き・聞き取り）、クロスエンコーダーによる再ランクと「速度重視で集め精度重視で絞る」2段階戦略、ハイブリッド検索によるBM25併用、クエリ変換・Parent Document Retriever・Self-RAGというアドバンストRAGの技術群の根拠
- [SupabaseとClaude/OpenAIで作る自作RAGシステム](../sources/video-rag-supabase-diy-chatbot.md) — キーワード検索とベクトル検索の対比（「疲れた」と「体が重たい」の例）、検索件数を増やすとコストも処理時間も増えるため微調整が必要という指摘の根拠
- [組織内情報集約RAGの実用化設計① なぜPoCレベルで頓挫するのか](../sources/article-rag-qiita-kentarok-poc-production-gap.md) — 「生成AIが答える内容は、検索で何を拾ってきたかにほぼ依存する」という位置づけ、略称・コードネーム・部署固有用語・表記揺れによる質問文と文書内語彙の不一致、「2024年版」「2023年版」の類似資料を区別できないという失敗パターンの根拠

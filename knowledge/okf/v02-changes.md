---
type: Concept
title: OKF v0.2 の変更点
description: v0.1 公開から約6週間後の改定で追加された sources / generated・verified / stale_after / status / Attested Computation という信頼性フィールド群と、v0.1 との後方互換性
tags: [okf, v0.2, provenance, verification, attested-computation, specification]
generated:
  by: claude-code/fable-5
  at: "2026-08-06T16:00:00+09:00"
---

# OKF v0.2 の変更点

## 改定の規模

OKF 仕様書は初版（v0.1）公開から約 6 週間で v0.2 へ改定された。行数は 451 行からおよそ倍以上に増え、新たに約 550 行が追加された。公式ブログはこれを「足したのは語彙（ボキャブラリー）であってルールは足していない」と説明しており、[必須フィールドは v0.2 でも `type` の1つのみ](./design-principles.md)で変わっていない（仕様書も「a concept carrying just `type` is fully conformant」と明記）。

## 追加された5つの記入欄

v0.2 は「知識を読む側が答えられるべき質問」を5つに整理し、それぞれに専用のフロントマターフィールドを用意した。フィールド名はすべて小文字スネークケース。

| 問い | フィールド | 内容 |
|------|-----------|------|
| 何から作られたか（出所） | `sources` | 元にした資料を列挙。資料ごとに `id` / `resource` / `title` / `author` / `usage_count` / `last_modified` を記録。全体に `usage_window: { from, to }` |
| どれくらい信じてよいか（信頼性） | `generated` / `verified` | 「誰が作ったか」と「誰が元データと突き合わせて確認したか」を別々に記録 |
| まだ本当か（鮮度） | `stale_after` | `2026-12-31` のような絶対日付で陳腐化日を指定 |
| 今の状態は何か（状態） | `status` | `draft`（未レビュー）/ `stable`（デフォルト）/ `deprecated`（非推奨） |
| 計算は決められた通りか（検算） | `type: Attested Computation` | 会社の計算式をファイルとして固定し、実行結果を検算する仕組み |

### sources（出所）

```yaml
sources:
  - id: q3-report
    resource: https://example.com/q3.pdf
    title: Q3 決算レポート
    author: finance-team
    usage_count: 12
    last_modified: 2026-07-01
usage_window: { from: 2026-07-01, to: 2026-08-01 }
```

信頼度を数値スコアで書く案は検討の上で不採用になった（動画の解説より）。点数は主観的で採点者の基準に依存し、組織をまたぐと意味が通じず、書いた瞬間から陳腐化するため。記録するのは利用回数などの客観的事実のみとし、何点と評価するかは読む側に委ねる設計。本文中の出典参照は番号ではなく source の `id` で行う（エージェントがリストの順序を並べ替えても参照が壊れないようにするため）。

### generated / verified（信頼性の分離）

```yaml
generated: { by: enrichment-agent/1.2, at: "2026-08-01T10:00:00Z" }
verified:
  - { by: process:nightly-check, at: "2026-08-02T03:00:00Z" }
  - { by: human:yuya, at: "2026-08-03T14:00:00Z" }
```

`generated` は「誰がいつ作ったか」、`verified` は「誰がいつ元データと突き合わせて確認したか」を記録する、意図的に分離された2つの欄。actor の書式には慣例があり、AI やツールは `<producer>/<version>`、人間は `human:<id>`、自動処理は `process:<id>` と書く。これにより読む側は次の3段階を機械的に判定できる。

- `verified` がない → 未確認
- `verified` が機械の確認のみ → 機械確認済み
- `verified` に `human:` が1件でもある → 人間確認済み

ただしこれはあくまで信頼度の目安であり、アクセス制御そのものとは別物。未確認だからといって表示が拒否されるわけではない。

### stale_after（絶対日付での有効期限）

「作成から90日間有効」のような相対的な期間ではなく、絶対日付（例: `stale_after: 2026-12-31`）で指定する。相対日数だと「いつ読んだか」を計算に入れないと判定できないが、絶対日付なら今日の日付と比較するだけで、AI にも通常のプログラムにも迷いのない判定ができるため（動画の解説より）。

### status（状態）

`draft` / `stable` / `deprecated` の3値で現在の状態を宣言する欄（省略時は `stable` 扱い）。役目を終えた古い定義は `deprecated` として残し、過去の再現には使えるが新しい仕事には出さない、という運用ができる。期限切れや古いバージョンのファイルを本文を開かずに機械的に洗い出す「知識の棚卸し」がしやすくなる。

### Attested Computation（検算）

v0.2 で唯一まるごと新設された知識の種類（`type: Attested Computation`）。固有フィールドは `runtime`（bigquery / postgres / dbt / python / Looker）、`parameters`（`{ name, type, required }` のリスト）、`computation`（式ファイルへのパス。本文の `# Computation` セクションでも可）、`executor`（`resource` と `receipt`）、`attester`。

会社の計算式そのものを1つの知識ファイルとして固定し、AI に許されるのは宣言済みパラメータへの値入力のみで、計算式自体の作成・改変は禁止されている。実行後は、実際に走った処理と結果を「レシート」として返し、それを attester（LLM を一切使わない決定論的なプログラム）が検査する。検査内容は次の2点。

1. 公認の式にパラメータ値を入れたものと、実際に走った式が一致するか
2. 表示しようとしている数字が、レシートの結果と一致するか

一致しなければ不合格となり、表示しない。テーブル名のすり替え、条件の追加、式ファイルの差し替えなどはこの検査で弾かれる。

`verified` と Attested Computation は別物。`verified` は「定義が今も会社のルールに合っているか」の確認でファイルに記録が残るのに対し、Attested Computation は「今回の実行が正しかったか」というその都度の確認。両方揃って初めて成立する（定義が正しくても実行がずれていればダメ、実行が正しくても定義が古ければダメ）。

OKF 自身は計算を実行しない。記録するのは計算式と検査のやり方までで、実際の実行と検査は利用側の役割。レシートの形式や検査プログラムの実装詳細は、仕様書が検討の上で先送りしている。

## バンドルのバージョン宣言

バンドルは対象バージョンを、**バンドルルートの `index.md` の frontmatter に `okf_version: "0.2"`** と書いて宣言できる（MAY）。index.md に frontmatter を書けるのはこの1箇所だけ。

## v0.1 との後方互換性

- v0.1 で作成済みのバンドルはそのまま有効。新しい欄をすべて埋めなくても、既存ファイルは v0.1 当時と同じ資格で有効（仕様書は「Everything else … is carried forward unchanged」と明記）
- 破壊的変更は2つ: (1) 旧 `timestamp` フィールドは `generated.at` に置き換え、(2) 本文下部の引用リスト（[`# Citations`](./design-principles.md)）は frontmatter の `sources` に統合
- いずれも救済ルールがあり、v0.2 の読み手は `generated` がなければ旧 `timestamp` を、`sources` がなければ旧 `# Citations` リストを参照してよい。公式ブログも「v0.1 のバンドルは無変更でそのまま使える」と説明している

## 留保事項

- 現行の v0.2 はドラフトを脱したが 1.0 の安定版ではなく、今後も形が変わる可能性がある
- Attested Computation まわりの「レシート」の形式や検査プログラムの実装詳細は、仕様書が先送りしている
- Google が同時公開したツール群は「参考実装（試作）」の位置づけで、採用実績は公表されていない
- frontmatter 肥大化への対策として、メタデータを文書冒頭に集約する・フォルダごとの `index.md` を目次として使う・`type` で絞り込む、という設計方針は仕様に明記されているが、実装方法自体は仕様の非目標とされ利用側に委ねられている。軽量化の実測値は誰も公表していない

# Citations

- [OKF 公式仕様書 SPEC.md v0.2（フィールド名・書式の正）](../sources/spec-okf-v02.md)
- [動画: OKF v0.2 の Citations 解説（設計意図・背景の解説）](../sources/video-okf-v02-citations.md)

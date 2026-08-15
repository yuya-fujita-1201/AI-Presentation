---
type: Article
title: What Is Loop Engineering? AI Feedback Loops
description: loop engineeringをIntent-Context-Action-Observation-Adjustmentの5段階フィードバックループと定義し、プロンプトエンジニアリングとの対比・5つの実践パターン・実践的な教訓を解説している
site: Kilo
published: unknown
retrieved: 2026-08-15
resource: https://kilo.ai/articles/what-is-loop-engineering
origin: "web:kilo.ai"
source_tier: secondary
tags: [loop-engineering, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-15T00:00:00+09:00"
---

# 概要

Kiloは、loop engineeringを「AIコーディングエージェントが計画立案・コード変更・結果観察・アプローチ修正を繰り返すフィードバックループの設計・運用・改善の実践」と定義していると説明する。記事は、ワンショットのコード生成ではなく反復的なシステムとしてloop engineeringを位置づけ、Intent・Context・Action・Observation・Adjustmentという5段階のモデルを提示している。また、プロンプトエンジニアリングとの対比を通じてloop engineeringの独自性を整理し、5つの具体的なユースケースパターンと実践的な教訓を示していると述べている。

# 要点

## 定義：Intent-Context-Action-Observation-Adjustmentの5段階

記事は、loop engineeringを次のように定義している。

> 引用: 「Loop engineering is the practice of designing, operating, and improving the feedback loops that let AI coding agents plan work, change code, observe results, and revise their approach until a software task is complete.」

日本語で言い換えると、loop engineeringとは、AIコーディングエージェントが計画立案・コード変更・結果観察・アプローチ修正を、ソフトウェアタスクが完了するまで繰り返せるようにするフィードバックループを設計・運用・改善する実践であるとされる。

この実践は5つの段階から構成されるとKiloは説明する。まずIntentの段階で、開発者またはシステムが達成すべき目標を定義する。次にContextの段階で、コード・ドキュメント・エラー・ログなどの関連情報が収集される。続くActionの段階では、ファイル編集・コマンド実行・ツール呼び出しといった具体的な操作が実行される。Observationの段階では、テスト結果・コンパイラエラー・diff・レビューコメントといった結果が取得される。最後のAdjustmentの段階で、これらの観察結果をもとに計画が更新され、反復が継続されると記事は説明している。

## プロンプトエンジニアリングとの対比

記事は、プロンプトエンジニアリングとloop engineeringを表形式で対比し、両者の焦点の違いを整理している。プロンプトエンジニアリングは「モデルへの入力形成」「より良い最初の回答」を目指し、評価は通常人間が行うとされる。一方でloop engineeringは「モデル周辺の全体的プロセス」を対象とし、目指すのは「より良い最終成果」であり、フィードバック源としてテスト・ツール・ログ・レビューを活用するという。

失敗モードについても両者は異なるとKiloは指摘する。プロンプトエンジニアリングの典型的な失敗は「弱い回答生成」であるのに対し、loop engineeringの失敗は「不十分なループ設計・早期停止」にあるとされる。この違いを踏まえ、記事は次のように述べている。

> 引用: 「loop engineering assumes the first answer may be incomplete and designs the workflow to improve from there.」

つまり、loop engineeringは最初の回答が不完全である可能性を前提とし、そこから改善していくワークフローとして設計されているという考え方だと記事は主張している。

## 5つの実践パターン

Kiloは、loop engineeringの具体的な適用例として5つのユースケースパターンを挙げている。1つ目はTest-Driven Agent Loopで、テストの失敗から実装修正へとつなげるパターンである。2つ目はCompiler-Driven Loopで、型チェッカーのエラーを修復リストとして活用し、主にマイグレーション作業に用いられる。3つ目はReview-Driven Loopで、人間によるレビューコメントを観察源として活用するパターンである。4つ目はRuntime Debugging Loopで、ログ・スタックトレース・ブラウザ出力から原因を特定する。5つ目はProduct Iteration Loopで、UIコピー・状態・レスポンシブ性を反復的に検証するパターンとされる。

## 実践的な教訓

記事は、実践上の教訓として複数の指摘を示している。まず、小さな差分の方が検証も修復もしやすいという考え方が述べられている。さらに重要な指摘として、テストの失敗を単なるエラーメッセージとしてではなく、次の推論のための新たな文脈情報として扱うべきだとする視点がある。

> 引用: 「A test failure is not just an error message; it is new context.」

また、記事は組織的な観点からも言及しており、次のように述べている。

> 引用: 「Teams need repeatable standards so agent behavior is predictable across repositories.」

これは、複数のリポジトリにまたがってエージェントの挙動を予測可能にするためには、チームが再現可能な標準を必要とするという主張だと記事は述べている。

# 活用先

（コンセプト昇華時に追記）

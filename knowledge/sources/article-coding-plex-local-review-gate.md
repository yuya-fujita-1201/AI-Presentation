---
type: Article
title: ローカルの Claude Code レビューを「すり抜けられない」必須チェックにした話
description: AIレビューの実行コストを抑えるためローカル環境でClaude Codeレビューを実行する構成に移行した際に生じたセットアップ漏れの検知漏れ問題と、git notes・commit status・branch protectionで証跡を構造的に検証する解決策をPLEX Product Team Blogが報告している
site: PLEX Product Team Blog
published: unknown
retrieved: 2026-08-28
resource: https://product.plex.co.jp/entry/local-claude-code-review-required-check
origin: "web:co.jp"
source_tier: secondary
tags: [claude-code, code-review, git-hooks, ci-cd, article]
generated:
  by: claude-code/pipeline-sonnet
  at: "2026-08-29T00:00:00+09:00"
---

# 概要

PLEX Product Team Blogの記事は、AIレビューの実行コストを抑えるために各開発者のローカル環境でClaude Codeレビューを実行する構成へ移行した際に生じた課題と、その解決策を報告している。同記事は、Git hookをローカルで動かすだけでは「セットアップ漏れや実行忘れがあっても検知しづらく、レビューを通さずにpushできてしまう」という本質的な弱点が残ると指摘し、リモート側で証跡を検証する仕組みを構築することでこの弱点を構造的に塞いだと述べている。

# 要点

## ローカル実行を選んだ背景とPre-pushレビューの実装

筆者は、「AIレビューの実行コストの都合から、レビューをCIではなく各開発者のローカル環境で実行したいケース」があり、従量課金負担の削減を狙ったと説明している。この方針のもと、まず`.claude/commands/review.md`にレビュー手順を記述し、「CLAUDE.mdに定義したコーディング規約や設計ルールに沿ってレビュー」を実施させるPre-pushレビューを構築したと述べている。機械的に合否を判定できるようにするため、指摘がなければ「独立した行で`[REVIEW_RESULT: PASS]`を出力」させ、指摘がある場合は「最後に独立した行で`[REVIEW_RESULT: FAIL]`を出力」させる設計とし、Git hookツールのlefthookを用いてpush直前（pre-push）にClaude Codeを実行し、結果に応じてpushを許可するかどうかを判定する仕組みを組んだと説明している。

## ローカルhookの限界——セットアップ漏れが検知できない

しかしこのローカルhookには限界があったと筆者は述べている。「Git hookは、各開発者の手元にセットアップされている場合にだけ動きます。未設定であれば、何も言わずにスキップされます」という点である。「hookが未設定でもエラーにならない」ため「痕跡すら残らない」状態になり、誰かがセットアップを済ませ忘れていてもそれをチーム側から検知できないという致命的な穴が残ったと筆者は指摘している。

## リモート側で証跡を検証する仕組み

この課題への解決策として、筆者はリモート側で「証跡」を検証するシステムを構築したと報告している。具体的には、git notes（「commit本体を書き換えずに、付箋のようにメモを貼れるGitの機能」）にレビューのPASSを記述し、それをGitHub上のcommit status（外部から付けられる成否ラベル）に反映させたうえで、branch protectionで「このcommit statusがsuccessでないとマージさせない」というルールを適用する構成である。実装フローとしては、ローカルでレビューがPASSした後にnote「PASS」を付けて`refs/notes/local-review`をGitHubにpushし、GitHub Actions側でそのnoteを取得して「PASS」ならstatus=success、なければstatus=failureとする流れになっていると筆者は説明している。

## 効果と明示された限界

この仕組みにより、「hookをセットアップし忘れた環境からpushしたcommitにはnoteが付かない」ため「noteのないcommitはマージできない」構造が実現し、「レビューを回し忘れた／hookを入れ忘れた」といった運用上の抜け漏れを構造的に塞ぐことができたと筆者は報告している。ただし筆者は、この仕組みが万能ではないことも明示しており、「レビュー品質やPASSの正当性そのものは保証しません」とし、意図的な迂回には対応できない設計であるという限界を率直に述べている。

# 活用先

（コンセプト昇華時に追記）

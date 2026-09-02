# 図版台帳 — 08-okf-practice（okf-practice）

07（超入門）の台帳と同じ方式。構図の発注文・expected_elements・最濃要素を恒久化し、図と本文の不一致を採点前に潰す。

共通仕様（SVG）: viewBox 1024×768、`<text>` 要素に `font-family="Hiragino Sans, Hiragino Kaku Gothic ProN, sans-serif"` を直接指定、warm パレット（背景 `#FFF9F3`・最濃 `#B44A32`＋白文字・濃茶 `#7C3527`）、文字下限 見出し24／ラベル20／補助18px、幅ガード（全角×size＋半角×size×0.6 ≤ 枠幅−24）、`<g id>` 数＝expected_elements。制作仕様の原文は `scratchpad/svg-specs-08.md`（セッション限り）で、要点は下表に転記済み。
共通仕様（ImageGen）: gemini-3-pro-image-preview、4:3（1200×896）、文字なし、07 と同じ「細い濃茶の輪郭線のフラット漫画調」、warm パレット、要素 5〜7 個、丸い頭にアンテナ1本のロボットと顔の少ない人物。

| # | ファイル名 | スライド（eyebrow） | 種別 | 構図の発注文 | expected_elements | 最濃にする要素 |
|---|---|---|---|---|---|---|
| 1 | `diagram-practice-cycle.svg` | はじめに｜全体像 | SVG | 作る／育てる／使う／守る の4カードを横一列。いつ・誰が を各カードに。守る→育てる への点線の戻り矢印「壊れたら直して、また育てる」 | 4（phase-1..4） | 3「使う」 |
| 2 | `diagram-build-steps.svg` | 01｜構築の全体手順 | SVG | 5ステップ（集めて仕分ける／骨組みを作る／AIに一次抽出させる／人が確認する／入口を整える）と所要。上見出し「AI推進担当2〜3名で、1日〜1週間」、下端「4だけは省けない…」 | 5（step-1..5） | 4「人が確認する」 |
| 3 | `warm-okfp-01.png` | 01｜ステップ1：AI に読ませる前の準備 | ImageGen | 人が3種の Office 文書（スライド・表・文書）をロボットに渡し、ロボットが右にテキストの束を出す | 人・ロボット・入力3種・出力の束 | ロボット |
| 4 | `warm-okfp-02.png` | 01｜ステップ4：人が確認する | ImageGen | ロボットが高い紙の山を抱え、人は数枚だけを虫めがねで読む。横に空欄のクリップボード | ロボット・紙の山・人・虫めがね・クリップボード | 人が読む数枚 |
| 5 | `diagram-knowledge-lifecycle.svg` | 02｜知識のライフサイクル | SVG | 討議→議事録→AIが取り込む→draftで更新→確認者がstableに→棚卸し の6ノードを輪に。棚卸しから draft への点線「変更が来たら 4 へ」 | 6（node-1..6） | 5「確認者が stable に」 |
| 6 | `warm-okfp-03.png` | 02｜討議のあとの流れ | ImageGen | 机の書記が1枚の要約をロボットに渡し、ロボットが棚にカードを置く。壁に数字のない時計（当日中） | 書記・要約・ロボット・棚・時計 | ロボットが置くカード |
| 7 | `diagram-overwrite-and-decision.svg` | 02｜要件が覆ったとき | SVG | 上段左「requirements/F-012…（現在の答えは、ここ1か所）」最濃、右「decisions/D-034…（経緯は、決定記録に）」、両方向矢印「相対リンク」、下段の帯「Git の履歴」 | 3（el-current／el-decision／el-git） | el-current |
| 8 | `warm-okfp-04.png` | 02｜毎朝の3分 | ImageGen | 朝日の窓辺でマグを持つ人。ロボットが3グループのカード（チェック／入れ替え矢印／？）の板を指す | 人・窓と朝日・ロボット・板・カード3組 | 板のカード3組 |
| 9 | `warm-okfp-05.png` | 03｜新規参画 | ImageGen | 鞄とバッジの新メンバーがドアから入り、ロボットが3つの道標が本棚へ向かう地図を掲げる | 新メンバー・ドア・ロボット・地図・本棚 | 地図 |
| 10 | `diagram-verified-two-layers.svg` | 04｜確認者の二層 | SVG | 上段「内容の確認／アプリリード・アーキリード／verified に human:名前」最濃、下段「形式の確認／機械チェック＋AI推進担当／process: で記録」、上見出し「「正しいか」と「約束どおりか」は、別の人が見る」 | 2（layer-content／layer-format） | layer-content |
| 11 | `warm-okfp-06.png` | 04｜棚卸しのタイミング | ImageGen | 人とロボットが本棚を片付ける。ロボットは埃と蜘蛛の巣の付いた古いカードを外し、人はカレンダーと砂時計を持つ。床の箱に外したカード | 人・ロボット・本棚・古いカード・カレンダー・砂時計・箱 | 外される古いカード |
| 12 | `diagram-three-ask-patterns.svg` | 03｜聞き方の型 | SVG（事前レビュー後に追加） | 調べる／作る／確かめる の3カードを横に並べ、下に最濃の帯「「根拠のファイル名も添えて」／3つの型すべてに、この一言を足す」 | 4（pattern-1..3／common-tip） | common-tip の帯 |

## 検証メモ

- 事前レビュー後の変更: lifecycle の node-3（AI が取り込む）を砂色にして人手2点を対に、practice-cycle の phase-2（育てる）を砂色に、overwrite の status 表記を「書き換え直後は draft、確認後に stable」に、「CR番号」を「変更管理の番号」に
- SVG 5 本は Workflow `okf-practice-svg-figures`（制作→独立検証）で一発合格。`tools/check_svg_fonts.py` 明朝フォールバック 0。`<g id>` 数は上表どおり
- ImageGen 6 枚は 2026-09-02 に生成。最初の試作1枚（輪郭線なしのフラット）は 07 と画風が違ったため不採用にし、「細い濃茶の輪郭線」を指定して再生成した
- 07 の `warm-okf-*.png` とロボットの造形が少し違う（08 は丸い頭にアンテナ1本で統一）。デッキ内では統一されている

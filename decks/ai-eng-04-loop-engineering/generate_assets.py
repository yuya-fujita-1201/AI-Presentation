#!/usr/bin/env python3
"""Generate the editable SVG diagrams used by the AI Engineering 04 deck."""

from __future__ import annotations

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parent / "assets"

BG = "#FFF9F3"
PRIMARY = "#7C3527"
ACCENT = "#247F7A"
ACCENT_SOFT = "#DDEFEA"
TERRACOTTA = "#B44A32"
PEACH = "#FADFD5"
SAND = "#F6E6CF"
MUTED = "#6F5C52"
TEXT = "#2B211D"
WHITE = "#FFFFFF"
GOLD = "#D99A5E"
FONT = "Hiragino Sans, Yu Gothic, sans-serif"


def t(x: int, y: int, value: str, size: int = 26, color: str = TEXT,
      weight: int = 700, anchor: str = "middle") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}">{escape(value)}</text>'
    )


def lines(x: int, y: int, values: list[str], size: int = 24,
          color: str = TEXT, weight: int = 700, anchor: str = "middle",
          gap: int = 36) -> str:
    return "".join(t(x, y + i * gap, value, size, color, weight, anchor)
                   for i, value in enumerate(values))


def rect(x: int, y: int, w: int, h: int, fill: str = WHITE,
         stroke: str = PRIMARY, sw: int = 3, rx: int = 24) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def circle(x: int, y: int, r: int, fill: str, stroke: str = "none",
           sw: int = 0) -> str:
    return (
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"/>'
    )


def arrow(x1: int, y1: int, x2: int, y2: int, color: str = MUTED,
          sw: int = 5, dashed: bool = False) -> str:
    dash = ' stroke-dasharray="12 10"' if dashed else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" '
        f'marker-end="url(#arrow)"{dash}/>'
    )


def human(x: int, y: int, color: str = TERRACOTTA) -> str:
    return (
        circle(x, y, 30, color)
        + f'<path d="M {x-62} {y+95} Q {x} {y+30} {x+62} {y+95} '
          f'L {x+62} {y+126} L {x-62} {y+126} Z" fill="{color}"/>'
    )


def robot(x: int, y: int, color: str = ACCENT) -> str:
    return (
        rect(x - 64, y - 48, 128, 102, color, color, 0, 24)
        + circle(x - 24, y - 3, 8, WHITE)
        + circle(x + 24, y - 3, 8, WHITE)
        + f'<path d="M {x-28} {y+27} Q {x} {y+48} {x+28} {y+27}" '
          f'fill="none" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>'
        + f'<line x1="{x}" y1="{y-48}" x2="{x}" y2="{y-78}" '
          f'stroke="{color}" stroke-width="7"/>'
        + circle(x, y - 87, 9, GOLD)
    )


def check(x: int, y: int, r: int = 34, fill: str = ACCENT) -> str:
    return (
        circle(x, y, r, fill)
        + f'<path d="M {x-r//2} {y} L {x-5} {y+r//3} L {x+r//2} {y-r//3}" '
          f'fill="none" stroke="{WHITE}" stroke-width="8" '
          f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def base(body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="768" viewBox="0 0 1024 768">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/>
    </marker>
  </defs>
  <rect width="1024" height="768" fill="{BG}"/>
  {body.replace('fill="context-stroke"', f'fill="{MUTED}"')}
</svg>
'''


def save(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(base(body), encoding="utf-8")


def flow(name: str, heading: str, items: list[tuple[str, str]],
         highlight: int | None = None, footer: str = "") -> None:
    count = len(items)
    gap = 22
    w = (900 - gap * (count - 1)) // count
    x0 = 62
    body = t(512, 70, heading, 34, PRIMARY, 800)
    for i, (label, sub) in enumerate(items):
        x = x0 + i * (w + gap)
        fill = ACCENT if i == highlight else (PEACH if i % 2 == 0 else SAND)
        color = WHITE if i == highlight else PRIMARY
        body += rect(x, 250, w, 230, fill, fill if i == highlight else GOLD, 3, 28)
        body += t(x + w // 2, 335, label, 26, color, 800)
        body += lines(x + w // 2, 390, sub.split("｜"), 19,
                      WHITE if i == highlight else MUTED, 600, "middle", 30)
        if i < count - 1:
            body += arrow(x + w + 5, 365, x + w + gap - 5, 365, MUTED, 4)
    if footer:
        body += t(512, 655, footer, 25, ACCENT, 800)
    save(name, body)


def compare(name: str, heading: str, left: tuple[str, list[str]],
            right: tuple[str, list[str]], footer: str = "",
            left_color: str = TERRACOTTA, right_color: str = ACCENT) -> None:
    body = t(512, 70, heading, 34, PRIMARY, 800)
    for x, payload, color, fill in (
        (60, left, left_color, PEACH), (534, right, right_color, ACCENT_SOFT)
    ):
        body += rect(x, 145, 430, 450, fill, color, 4, 30)
        body += t(x + 215, 220, payload[0], 31, color, 800)
        for i, value in enumerate(payload[1]):
            body += circle(x + 58, 298 + i * 82, 13, color)
            body += t(x + 88, 307 + i * 82, value, 22, TEXT, 650, "start")
    if footer:
        body += rect(170, 632, 684, 76, PRIMARY, PRIMARY, 0, 24)
        body += t(512, 681, footer, 25, WHITE, 800)
    save(name, body)


def grid(name: str, heading: str, items: list[tuple[str, str]],
         footer: str = "", cols: int = 2) -> None:
    body = t(512, 68, heading, 34, PRIMARY, 800)
    rows = (len(items) + cols - 1) // cols
    card_w = 430 if cols == 2 else 286
    card_h = 205 if rows <= 2 else 158
    gap_x = 44 if cols == 2 else 24
    gap_y = 30
    total_w = cols * card_w + (cols - 1) * gap_x
    x0 = (1024 - total_w) // 2
    y0 = 135
    for i, (label, sub) in enumerate(items):
        x = x0 + (i % cols) * (card_w + gap_x)
        y = y0 + (i // cols) * (card_h + gap_y)
        color = ACCENT if i % 2 else TERRACOTTA
        fill = ACCENT_SOFT if i % 2 else PEACH
        body += rect(x, y, card_w, card_h, fill, color, 3, 26)
        body += t(x + card_w // 2, y + 64, label, 26, color, 800)
        body += lines(x + card_w // 2, y + 108, sub.split("｜"), 19, MUTED, 600,
                      "middle", 28)
    if footer:
        body += t(512, 714, footer, 23, ACCENT, 800)
    save(name, body)


def cycle(name: str, heading: str, labels: list[str], center: list[str],
          footer: str = "") -> None:
    import math

    body = t(512, 66, heading, 34, PRIMARY, 800)
    cx, cy, radius = 512, 390, 245
    points: list[tuple[int, int]] = []
    for i in range(len(labels)):
        angle = -math.pi / 2 + i * 2 * math.pi / len(labels)
        points.append((int(cx + radius * math.cos(angle)), int(cy + radius * math.sin(angle))))
    for i, (x, y) in enumerate(points):
        nx, ny = points[(i + 1) % len(points)]
        body += arrow(x, y, nx, ny, MUTED, 5)
    for i, ((x, y), label) in enumerate(zip(points, labels)):
        color = ACCENT if i in (0, len(labels) - 1) else TERRACOTTA
        body += circle(x, y, 72, ACCENT_SOFT if color == ACCENT else PEACH, color, 4)
        body += lines(x, y - 5, label.split("｜"), 20, color, 800, "middle", 26)
    body += circle(cx, cy, 105, PRIMARY)
    body += lines(cx, cy - 17, center, 25, WHITE, 800, "middle", 34)
    if footer:
        body += t(512, 724, footer, 22, ACCENT, 800)
    save(name, body)


def main() -> None:
    flow(
        "diagram-series-five-layers.svg",
        "5つの設計対象のうち、今回は『時間軸』",
        [("Prompt", "指示"), ("Context", "情報"), ("Harness", "環境"),
         ("Loop", "時間軸"), ("Graph", "構造軸")],
        highlight=3,
        footer="前の3層を包み、次のグラフへつなぐ第4層",
    )
    flow(
        "diagram-learning-journey.svg",
        "今日のゴールまでを、6つの問いで進む",
        [("Why", "なぜ回す"), ("What", "何が1周"), ("Stop", "いつ止める"),
         ("Check", "何で測る"), ("Who", "誰が採点"), ("Start", "どこから始める")],
        highlight=5,
        footer="最後に『1ページ・1テスト』へ落とす",
    )

    body = t(512, 65, "往復の主語は、ずっと人間だった", 34, PRIMARY, 800)
    body += human(130, 320)
    body += t(130, 515, "人間", 27, TERRACOTTA, 800)
    for i, label in enumerate(["指示", "読む", "直す", "続ける？"]):
        x = 300 + i * 155
        body += rect(x, 250, 125, 126, PEACH if i % 2 == 0 else SAND, GOLD, 3, 22)
        body += t(x + 62, 325, label, 23, PRIMARY, 800)
        if i < 3:
            body += arrow(x + 130, 313, x + 150, 313, MUTED, 4)
    body += robot(900, 320)
    body += t(900, 515, "AIは1回分だけ", 24, ACCENT, 800)
    body += arrow(840, 560, 210, 560, TERRACOTTA, 5, True)
    body += t(512, 620, "次の1回を始めるのも、終わりを決めるのも人間", 25, TERRACOTTA, 800)
    save("diagram-human-driven-chat.svg", body)

    compare(
        "diagram-loop-definition.svg",
        "『打つ人』を外し、『打つ仕組み』を置く",
        ("これまで", ["人が次を指示", "人が出来を読む", "人が終わりを判断"]),
        ("ループ", ["条件が次を起動", "チェックが合否を返す", "停止条件で終わる"]),
        "自動化するのは回答ではなく、反復を回す役割",
    )

    compare(
        "diagram-chat-vs-loop.svg",
        "変わるのは、3つの『誰が』",
        ("チャット", ["次を始める：人", "出来を判定：人", "終わりを決める：人"]),
        ("ループ", ["次を始める：条件", "出来を判定：信号", "終わりを決める：停止条件"]),
        "輪の形は同じ。担い手だけが入れ替わる",
    )

    body = t(512, 68, "人間は、輪の中から監督席へ", 34, PRIMARY, 800)
    body += circle(305, 360, 205, PEACH, TERRACOTTA, 5)
    body += human(305, 300)
    body += t(305, 492, "Human in the Loop", 27, TERRACOTTA, 800)
    body += t(305, 530, "毎周レビューする", 20, MUTED, 650)
    body += arrow(518, 360, 614, 360, MUTED, 6)
    body += circle(760, 360, 180, ACCENT_SOFT, ACCENT, 5)
    body += robot(760, 355)
    body += human(920, 165, TERRACOTTA)
    body += t(760, 578, "Human on the Loop", 27, ACCENT, 800)
    body += t(760, 616, "外側から方向を監督する", 20, MUTED, 650)
    body += t(512, 714, "人間が消えるのではなく、介入の頻度が変わる", 24, ACCENT, 800)
    save("diagram-human-in-on-loop.svg", body)

    flow(
        "diagram-four-layer-stack.svg",
        "設計対象は、外へ外へと広がる",
        [("Prompt", "頼み方"), ("Context", "判断材料"), ("Harness", "作業環境"),
         ("Loop", "反復の時間軸")],
        highlight=3,
        footer="ループは、前の3層が動く順序と停止を設計する",
    )

    body = t(512, 68, "乗り換えではなく、包み込む", 34, PRIMARY, 800)
    for r, label, fill, stroke in [
        (280, "LOOP｜反復", ACCENT_SOFT, ACCENT),
        (215, "HARNESS｜環境", SAND, GOLD),
        (150, "CONTEXT｜情報", PEACH, TERRACOTTA),
        (88, "PROMPT｜指示", PRIMARY, PRIMARY),
    ]:
        body += circle(512, 385, r, fill, stroke, 5)
        body += t(512, 385 - r + 44, label.split("｜")[0], 23,
                  WHITE if fill == PRIMARY else stroke, 800)
    body += t(512, 402, "1周ごとに動く", 25, WHITE, 800)
    body += t(512, 710, "下の層の品質差は、周回するほど増幅される", 24, TERRACOTTA, 800)
    save("diagram-nested-layers.svg", body)

    cycle(
        "diagram-five-stage-loop.svg",
        "1周は、観察して次を変えるまで",
        ["Intent｜意図", "Context｜文脈", "Action｜行動", "Observation｜観察", "Adjustment｜調整"],
        ["PASS / FAIL", "を次へ渡す"],
        "つまずきやすいのは Observation：機械が読める信号を置く",
    )

    body = t(512, 52, "速い輪を、遅い輪が監督する", 34, PRIMARY, 800)
    body += circle(512, 378, 285, SAND, GOLD, 5)
    body += circle(512, 378, 190, ACCENT_SOFT, ACCENT, 5)
    body += circle(512, 378, 100, PEACH, TERRACOTTA, 5)
    body += t(512, 366, "INNER", 27, TERRACOTTA, 800)
    body += t(512, 402, "1タスク", 22, MUTED, 700)
    body += t(512, 170, "OUTER｜複数タスク", 25, ACCENT, 800)
    body += t(512, 116, "HUMAN GATE｜分解後と最終成果", 21, PRIMARY, 800)
    body += t(512, 704, "失敗の教訓を外側へ渡せるかが、アウターの要点", 23, ACCENT, 800)
    save("diagram-inner-outer-loop.svg", body)

    body = t(512, 66, "内側ほど速く、外側ほど人間に近い", 34, PRIMARY, 800)
    speeds = [
        (118, "数分", "実装・テスト・修正", TERRACOTTA, PEACH),
        (212, "数十分〜数時間", "人が方向を修正", ACCENT, ACCENT_SOFT),
        (304, "数時間〜数週間", "ユーザー・本番の気づき", PRIMARY, SAND),
    ]
    for r, label, sub, stroke, fill in reversed(speeds):
        body += circle(512, 385, r, fill, stroke, 5)
        body += t(512, 385 - r + 48, label, 25, stroke, 800)
    body += robot(512, 380)
    body += t(512, 526, "AIの持ち場", 23, TERRACOTTA, 800)
    body += human(822, 130)
    body += t(822, 282, "人の監督席", 22, PRIMARY, 800)
    save("diagram-three-speed-loops.svg", body)

    compare(
        "diagram-goal-before-loop.svg",
        "順番で、同じ仕組みが安全にも暴走にもなる",
        ("失敗する順番", ["1 まず器を作る", "2 回し始める", "3 後からゴールを考える"]),
        ("設計する順番", ["1 計測できるゴール", "2 複数の停止条件", "3 最後に器をつなぐ"]),
        "先に置くのはループではなく、ゴールテープ",
    )

    compare(
        "diagram-timer-vs-goal.svg",
        "同じ『loop』でも、止まり方が違う",
        ("時間駆動", ["決めた間隔で起動", "前回の成否を問わない", "ただ繰り返す"]),
        ("ゴール駆動", ["成功条件を先に定義", "評価で次周を決める", "達成か上限で止まる"]),
        "改善したいなら、必要なのは右側の条件付きループ",
    )

    body = t(512, 66, "合否信号が、輪を閉じる", 34, PRIMARY, 800)
    body += robot(180, 360)
    body += rect(320, 245, 230, 230, PEACH, TERRACOTTA, 4, 30)
    body += t(435, 330, "WORK", 29, TERRACOTTA, 800)
    body += t(435, 380, "作る・直す", 24, MUTED, 700)
    body += rect(665, 245, 230, 230, ACCENT_SOFT, ACCENT, 4, 30)
    body += t(780, 325, "CHECK", 29, ACCENT, 800)
    body += check(780, 390, 45)
    body += arrow(250, 360, 310, 360, MUTED, 5)
    body += arrow(555, 360, 655, 360, MUTED, 5)
    body += f'<path d="M 780 490 C 780 650 435 650 435 490" fill="none" stroke="{TERRACOTTA}" stroke-width="6" marker-end="url(#arrow)"/>'
    body += t(607, 670, "FAILなら観察結果を次の文脈へ", 23, TERRACOTTA, 800)
    save("diagram-pass-fail-closes-loop.svg", body)

    compare(
        "diagram-machine-vs-llm-check.svg",
        "成果物の性質で、チェックを分ける",
        ("機械判定", ["コード・数値・構造", "終了コード・差分・件数", "同じ入力なら同じ判定"]),
        ("モデル判定", ["文章・企画・デザイン", "rubric・画面・根拠", "観点と独立性を設計する"]),
        "置けるなら両方置く：文字数は機械、崩れはモデル",
    )

    flow(
        "diagram-evidence-chain.svg",
        "『完了』を、証拠へ分解する",
        [("CLAIM", "完了と申告"), ("COMMAND", "実行した操作"), ("OUTPUT", "戻り値・ログ"),
         ("SURFACE", "画面・成果物"), ("STATE", "最終状態")],
        highlight=4,
        footer="自己申告ではなく、第三者が追える結果を残す",
    )

    body = t(512, 66, "作った理由を知るほど、採点は甘くなる", 34, PRIMARY, 800)
    body += rect(92, 170, 350, 420, PEACH, TERRACOTTA, 4, 30)
    body += robot(267, 305, TERRACOTTA)
    body += t(267, 430, "作る役", 30, TERRACOTTA, 800)
    body += lines(267, 480, ["意図", "苦労", "言い訳"], 21, MUTED, 650, "middle", 32)
    body += rect(582, 170, 350, 420, ACCENT_SOFT, ACCENT, 4, 30)
    body += robot(757, 305, ACCENT)
    body += t(757, 430, "採点する役", 30, ACCENT, 800)
    body += lines(757, 480, ["成果物", "rubric", "観察結果だけ"], 21, MUTED, 650, "middle", 32)
    body += f'<line x1="512" y1="165" x2="512" y2="610" stroke="{GOLD}" stroke-width="5" stroke-dasharray="12 10"/>'
    body += t(512, 690, "背景文脈を切ること自体が、独立性になる", 24, ACCENT, 800)
    save("diagram-maker-checker-bias.svg", body)

    compare(
        "diagram-maker-checker-separation.svg",
        "お願いではなく、構成で分ける",
        ("Maker", ["生成・編集を行う", "書き込み権限あり", "量をこなす"]),
        ("Checker", ["判定と根拠だけ返す", "Write / Editを持たない", "まず対象の性質を判定"]),
        "修正できない採点役は、合格させる方向へ歪みにくい",
    )

    body = t(512, 64, "5つの問いで、適用するか決める", 34, PRIMARY, 800)
    questions = [
        ("1", "品質が安定しない？", "NO → 他の層へ"),
        ("2", "手順を書き下せない？", "NO → スクリプト"),
        ("3", "観察源がある？", "NO → 先に作る"),
        ("4", "毎手順に人の判断が要る？", "YES → 不向き"),
        ("5", "1ページまで切れる？", "YES → 小さく開始"),
    ]
    for i, (num, q, branch) in enumerate(questions):
        y = 122 + i * 112
        body += circle(110, y + 35, 32, ACCENT if i == 4 else TERRACOTTA)
        body += t(110, y + 44, num, 24, WHITE, 800)
        body += rect(170, y, 520, 72, WHITE, GOLD, 3, 20)
        body += t(195, y + 47, q, 23, TEXT, 700, "start")
        body += rect(730, y, 220, 72, ACCENT_SOFT if i == 4 else SAND,
                     ACCENT if i == 4 else GOLD, 3, 20)
        body += t(840, y + 47, branch, 20, ACCENT if i == 4 else MUTED, 800)
    save("diagram-loop-fit-filter.svg", body)

    grid(
        "diagram-observation-sources.svg",
        "観察源は、すでに現場にある",
        [("TEST", "失敗→実装修正"), ("COMPILER", "型エラー→修復"),
         ("REVIEW", "コメント→再編集"), ("RUNTIME", "ログ→原因特定"),
         ("PRODUCT", "画面→反復改善")],
        "新しく作る前に、今ある赤信号を探す",
        cols=3,
    )

    body = t(512, 66, "最小構成は、3ファイルで成立する", 34, PRIMARY, 800)
    files = [
        ("CLAUDE.md", "停止条件・禁止事項", TERRACOTTA, PEACH),
        ("settings.json", "テスト・型チェックのフック", ACCENT, ACCENT_SOFT),
        ("fixer.md", "行き詰まりを見る別エージェント", GOLD, SAND),
    ]
    for i, (name, sub, stroke, fill) in enumerate(files):
        x = 95 + i * 305
        body += rect(x, 190, 250, 330, fill, stroke, 4, 26)
        body += f'<path d="M {x+58} 245 h 95 l 40 40 v 142 h -135 z" fill="{WHITE}" stroke="{stroke}" stroke-width="4"/>'
        body += t(x + 125, 355, name, 24, stroke, 800)
        body += lines(x + 125, 420, sub.split("・"), 19, MUTED, 650, "middle", 28)
    body += t(512, 620, "足りなくなったら、接続・隔離・メモリーを足す", 25, ACCENT, 800)
    body += t(512, 682, "部品リストは開始条件ではなく、詰まったときの索引", 22, MUTED, 700)
    save("diagram-three-file-start.svg", body)

    flow(
        "diagram-minimum-slide-loop.svg",
        "1ページの清書を、最小ループへする",
        [("GOAL", "rubric 8点"), ("MAKE", "1枚だけ修正"), ("CHECK", "build＋目視"),
         ("JUDGE", "別担当が採点"), ("STOP", "達成／3回／停滞")],
        highlight=4,
        footer="未達なら指摘を次の文脈へ。上限なら人を呼ぶ",
    )

    grid(
        "diagram-four-costs.svg",
        "回るほど増えるものを、先に見る",
        [("トークン暴走", "課金が回り続ける"), ("検証の積み残し", "生成だけが積み上がる"),
         ("理解の劣化", "中身を把握しなくなる"), ("判断の放棄", "方向までAIへ預ける")],
        "前2つは設定で抑えられる。後2つは人間が持ち続ける",
        cols=2,
    )

    flow(
        "diagram-academic-lineage.svg",
        "名称より前から、反復の構造は育っていた",
        [("ReAct", "考える→行動"), ("Reflection", "失敗を記憶"),
         ("Self-Refine", "生成→批評→改善"), ("Evaluator", "生成と評価を分離"),
         ("Loop Eng.", "運用・停止まで設計")],
        highlight=4,
        footer="新発明というより、既存パターンを実務の外周まで広げた概念",
    )

    compare(
        "diagram-self-refine-vs-evaluator.svg",
        "骨格は同じ。違うのは、誰が評価するか",
        ("Self-Refine", ["同一LLMが三役", "フィードバックを次へ", "満足まで反復"]),
        ("Evaluator-Optimizer", ["生成と評価を別呼び出し", "全履歴＋feedback", "PASSで終了"]),
        "共通項は『生成→評価→次の生成』",
    )

    cycle(
        "diagram-evaluator-optimizer.svg",
        "評価が PASS を返すまで、履歴を積み増す",
        ["GENERATE｜生成", "EVALUATE｜評価", "FEEDBACK｜理由", "MEMORY｜履歴"],
        ["PASS?", "未達なら次へ"],
        "回数は保険。終了条件は評価側に置く",
    )

    grid(
        "diagram-loop-six-parts.svg",
        "5+1の部品は、6つの詰まりを解く",
        [("Automation", "誰が起動する"), ("Worktree", "作業が衝突しない"),
         ("Skills", "規約を毎周守る"), ("Connectors", "外部へ触れる"),
         ("Sub-agents", "作る／見るを分ける"), ("Memory", "学びを次へ残す")],
        "メモリーがなければ、アウターループは毎回ふりだし",
        cols=3,
    )

    flow(
        "diagram-actions-to-parts.svg",
        "名詞の部品を、動詞の流れへつなぐ",
        [("発見", "Automation"), ("受け渡し", "Skills"), ("検証", "Sub-agents"),
         ("記憶", "Memory"), ("予定", "Automation")],
        highlight=2,
        footer="道具を増やす前に、真ん中の『検証』があるかを見る",
    )

    compare(
        "diagram-long-run-guardrail.svg",
        "席を離れる時間と、歯止めは同時に増やす",
        ("自律を伸ばす", ["自動承認", "動的ワークフロー", "長時間実行"]),
        ("歯止めを増やす", ["隔離された作業領域", "停止・コスト上限", "証拠と人への通知"]),
        "自由にするために、制約を先に設計する",
    )

    grid(
        "diagram-risk-control.svg",
        "リスクごとに、別の歯止めを置く",
        [("暴走", "回数・時間・費用上限"), ("検証抜け", "チェック自体を保護"),
         ("局所最適", "別案を並列で試す"), ("ゴールずれ", "人が基準をレビュー"),
         ("知識不足", "ループ外で前提を整える"), ("判断放棄", "方向は人が持つ")],
        "最後の1つだけは、設定では防げない",
        cols=3,
    )


if __name__ == "__main__":
    main()

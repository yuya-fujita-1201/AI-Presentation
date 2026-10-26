#!/usr/bin/env python3
"""同梱アイコン集（templates/icons/icons.json）を作り直す保守用スクリプト。

Tabler Icons（MIT License, https://tabler.io/icons）の outline アイコンから、提案書でよく使う概念の
定番だけを選んで取得し、SVG のパス（円弧・相対座標・H/V/S/T を含む）を canvas の自由曲線が扱える
M / L / C / Q / Z の絶対座標に変換して保存する。PowerPoint では線だけのネイティブ図形になり、
色・太さを後から変えられる（画像にしない）。

利用者が実行する必要はない（ネットワークが要る）。アイコンを足すときは ICONS に
「Tabler の名前: (日本語の概念語, 英語の概念語)」を追加して実行する:
  python tools/build_icon_set.py [--version 3.19.0]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "templates" / "icons" / "icons.json"

# Tabler の名前: (日本語の概念語, 英語の概念語)
ICONS = {
    "target": ("目標 狙い ゴール 目的 KPI", "target goal objective aim"),
    "chart-bar": ("分析 グラフ 集計 実績 比較", "chart analytics bar report"),
    "chart-line": ("推移 成長 傾向 時系列", "trend growth line chart"),
    "trending-up": ("向上 増加 改善 拡大 伸び", "increase growth improve up"),
    "trending-down": ("削減 減少 低減 コスト削減", "decrease reduce down"),
    "coin": ("費用 コスト 投資 お金", "cost money coin investment"),
    "currency-yen": ("金額 予算 円 見積 価格", "yen budget price"),
    "report-money": ("見積 請求 収支 財務", "estimate finance invoice"),
    "briefcase": ("業務 ビジネス 仕事 案件", "business work job"),
    "building": ("企業 会社 組織 本社", "company building organization"),
    "building-factory-2": ("工場 製造 生産 現場", "factory manufacturing plant"),
    "users": ("チーム 人 メンバー 利用者", "team people members users"),
    "user": ("担当者 個人 ユーザー", "person user individual"),
    "users-group": ("体制 組織 グループ 部門", "group organization department"),
    "user-check": ("承認 承認者 責任者 確認者", "approver approval owner"),
    "heart-handshake": ("協業 パートナー 提携 支援 伴走", "partnership collaboration support"),
    "settings": ("設定 仕組み 運用 管理", "settings configuration operation"),
    "adjustments": ("調整 最適 チューニング", "adjust tune optimize"),
    "refresh": ("改善 循環 繰り返し 更新 サイクル", "cycle refresh iterate improve"),
    "arrows-right-left": ("連携 交換 双方向 やり取り", "exchange integration two-way"),
    "route": ("プロセス 流れ 道筋 手順 ロードマップ", "process route path roadmap"),
    "list-check": ("手順 チェックリスト 確認 項目", "checklist steps list"),
    "clipboard-check": ("審査 検査 点検 評価 テスト", "review inspection audit test"),
    "circle-check": ("完了 達成 成功 合格", "done success complete"),
    "alert-triangle": ("リスク 注意 警告 課題 問題", "risk warning alert issue"),
    "shield-check": ("セキュリティ 統制 安全 保護 ガバナンス", "security governance safety protect"),
    "lock": ("権限 施錠 機密 制限", "lock permission confidential"),
    "key": ("鍵 認証 アクセス", "key authentication access"),
    "eye": ("可視化 見える化 監視 モニタリング", "visibility monitor observe"),
    "search": ("調査 検索 探索 分析", "search research investigate"),
    "bulb": ("アイデア 示唆 気づき 発想 提案", "idea insight proposal"),
    "rocket": ("立ち上げ 展開 開始 ローンチ 加速", "launch rocket start accelerate"),
    "flag": ("マイルストーン 節目 到達 旗", "milestone flag"),
    "calendar": ("スケジュール 日程 期間 予定", "schedule calendar timeline"),
    "clock": ("時間 スピード 工数 期限", "time speed deadline"),
    "file-text": ("文書 成果物 ドキュメント 報告書", "document deliverable report"),
    "files": ("資料 ファイル 一式", "files materials"),
    "book": ("ガイド マニュアル 手引き 知識", "guide manual knowledge"),
    "school": ("教育 研修 学習 トレーニング", "education training learning"),
    "presentation": ("説明 報告 発表 プレゼン", "presentation briefing"),
    "messages": ("会議 コミュニケーション 対話 相談", "meeting communication discussion"),
    "mail": ("連絡 メール 通知", "mail notice contact"),
    "headset": ("サポート 問い合わせ 窓口 コールセンター", "support helpdesk contact center"),
    "world": ("グローバル 海外 世界 全社", "global world international"),
    "map-pin": ("拠点 場所 地域 店舗", "location site branch"),
    "truck": ("物流 配送 輸送 サプライチェーン", "logistics delivery supply chain"),
    "shopping-cart": ("購買 EC 販売 調達", "purchase commerce sales"),
    "device-desktop": ("PC 画面 システム 端末", "desktop screen system"),
    "device-mobile": ("スマホ モバイル アプリ", "mobile smartphone app"),
    "cloud": ("クラウド 基盤 SaaS", "cloud platform saas"),
    "database": ("データ データベース 蓄積 DB", "data database storage"),
    "server": ("サーバー インフラ", "server infrastructure"),
    "code": ("開発 コード プログラム 実装", "development code programming"),
    "terminal-2": ("コマンド 実行 ターミナル CLI", "command terminal cli"),
    "robot": ("AI 自動化 ロボット エージェント", "ai automation robot agent"),
    "sparkles": ("生成AI 新機能 魅力 品質", "generative ai new magic"),
    "git-branch": ("バージョン 分岐 変更管理", "version branch change"),
    "puzzle": ("統合 部品 組み合わせ 拡張 プラグイン", "integration component plugin"),
    "stack-2": ("基盤 層 レイヤー プラットフォーム", "platform layer stack foundation"),
    "sitemap": ("構造 体制図 階層 全体像", "structure hierarchy org chart"),
    "affiliate": ("ネットワーク つながり 関係 ハブ", "network connection hub"),
    "plug": ("接続 連携 API", "connect plug api"),
    "bolt": ("効率 高速 即時 パワー", "efficiency fast power"),
    "leaf": ("サステナビリティ 環境 ESG", "sustainability environment esg"),
    "heart": ("顧客満足 体験 共感", "satisfaction experience empathy"),
    "star": ("評価 強み 重要 品質", "rating strength quality"),
    "thumb-up": ("合意 賛成 承認 好評", "agree approve like"),
    "award": ("実績 受賞 表彰 成果", "award achievement result"),
    "scale": ("比較 判断 評価 バランス", "compare judge balance"),
    "gavel": ("規制 法務 コンプライアンス ルール", "regulation legal compliance"),
    "package": ("パッケージ 製品 サービス 提供", "package product offering"),
    "tool": ("ツール 保守 メンテナンス 修理", "tool maintenance repair"),
    "id-badge-2": ("社員 ID 身分", "employee id badge"),
    "home": ("ホーム 家 拠点 本拠", "home house"),
}

NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _arc_to_cubic(x1, y1, rx, ry, phi, fa, fs, x2, y2):
    """SVG の楕円弧（端点表記）を 3 次ベジェの列に変換する（SVG 実装ノート F.6 の手順）。"""
    if rx == 0 or ry == 0:
        return [("L", x2, y2)]
    phi = math.radians(phi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    co = math.sqrt(max(num / den, 0)) if den else 0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    segs = max(1, math.ceil(abs(dt) / (math.pi / 2)))
    d = dt / segs
    k = 4 / 3 * math.tan(d / 4)
    out = []
    for i in range(segs):
        a1, a2 = t1 + i * d, t1 + (i + 1) * d
        p1 = (math.cos(a1) - k * math.sin(a1), math.sin(a1) + k * math.cos(a1))
        p2 = (math.cos(a2) + k * math.sin(a2), math.sin(a2) - k * math.cos(a2))
        p3 = (math.cos(a2), math.sin(a2))

        def tr(p):
            x, y = p[0] * rx, p[1] * ry
            return cp * x - sp * y + cx, sp * x + cp * y + cy
        (ax, ay), (bx, by), (ex, ey) = tr(p1), tr(p2), tr(p3)
        out.append(("C", ax, ay, bx, by, ex, ey))
    return out


def path_to_cmds(d: str) -> list:
    """SVG の d 属性を、絶対座標の M / L / C / Q / Z の列にする。"""
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|" + NUM.pattern, d)
    out, i = [], 0
    cx = cy = sx = sy = 0.0
    last_c = last_q = None
    cmd = None
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                out.append(["Z"])
                cx, cy = sx, sy
                last_c = last_q = None
                continue

        def nums(n):
            nonlocal i
            vals = [float(v) for v in toks[i:i + n]]
            i += n
            return vals
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            x, y = nums(2)
            if rel:
                x, y = cx + x, cy + y
            out.append(["M", x, y])
            cx, cy, sx, sy = x, y, x, y
            cmd = "l" if rel else "L"
            last_c = last_q = None
        elif c == "L":
            x, y = nums(2)
            if rel:
                x, y = cx + x, cy + y
            out.append(["L", x, y])
            cx, cy = x, y
            last_c = last_q = None
        elif c == "H":
            (x,) = nums(1)
            x = cx + x if rel else x
            out.append(["L", x, cy])
            cx = x
            last_c = last_q = None
        elif c == "V":
            (y,) = nums(1)
            y = cy + y if rel else y
            out.append(["L", cx, y])
            cy = y
            last_c = last_q = None
        elif c == "C":
            a = nums(6)
            if rel:
                a = [a[k] + (cx if k % 2 == 0 else cy) for k in range(6)]
            out.append(["C"] + a)
            last_c = (a[2], a[3])
            cx, cy = a[4], a[5]
            last_q = None
        elif c == "S":
            a = nums(4)
            if rel:
                a = [a[k] + (cx if k % 2 == 0 else cy) for k in range(4)]
            x1, y1 = (2 * cx - last_c[0], 2 * cy - last_c[1]) if last_c else (cx, cy)
            out.append(["C", x1, y1] + a)
            last_c = (a[0], a[1])
            cx, cy = a[2], a[3]
            last_q = None
        elif c == "Q":
            a = nums(4)
            if rel:
                a = [a[k] + (cx if k % 2 == 0 else cy) for k in range(4)]
            out.append(["Q"] + a)
            last_q = (a[0], a[1])
            cx, cy = a[2], a[3]
            last_c = None
        elif c == "T":
            x, y = nums(2)
            if rel:
                x, y = cx + x, cy + y
            qx, qy = (2 * cx - last_q[0], 2 * cy - last_q[1]) if last_q else (cx, cy)
            out.append(["Q", qx, qy, x, y])
            last_q = (qx, qy)
            cx, cy = x, y
            last_c = None
        elif c == "A":
            rx, ry, phi, fa, fs, x, y = nums(7)
            if rel:
                x, y = cx + x, cy + y
            for seg in _arc_to_cubic(cx, cy, rx, ry, phi, int(fa), int(fs), x, y):
                out.append(list(seg))
            cx, cy = x, y
            last_c = last_q = None
    return [[c[0]] + [round(v, 3) for v in c[1:]] for c in out]


def shape_to_cmds(tag: str, a: dict) -> list:
    f = lambda k: float(a.get(k, 0))  # noqa: E731
    if tag == "circle" or tag == "ellipse":
        cx, cy = f("cx"), f("cy")
        rx = f("r") if tag == "circle" else f("rx")
        ry = f("r") if tag == "circle" else f("ry")
        return path_to_cmds(f"M{cx - rx} {cy} a{rx} {ry} 0 1 0 {2 * rx} 0 a{rx} {ry} 0 1 0 {-2 * rx} 0z")
    if tag == "rect":
        x, y, w, h = f("x"), f("y"), f("width"), f("height")
        return path_to_cmds(f"M{x} {y}h{w}v{h}h{-w}z")
    if tag == "line":
        return [["M", f("x1"), f("y1")], ["L", f("x2"), f("y2")]]
    if tag in ("polyline", "polygon"):
        pts = [float(v) for v in NUM.findall(a.get("points", ""))]
        cmds = [["M", pts[0], pts[1]]] + [["L", pts[k], pts[k + 1]] for k in range(2, len(pts), 2)]
        return cmds + ([["Z"]] if tag == "polygon" else [])
    return []


def fetch(name: str, version: str) -> str:
    url = f"https://unpkg.com/@tabler/icons@{version}/icons/outline/{name}.svg"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def convert(svg: str) -> list:
    root = ET.fromstring(svg)
    paths = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "svg" or el.get("stroke") == "none":
            continue   # 外枠の透明な四角（stroke="none"）は描かない
        cmds = path_to_cmds(el.get("d", "")) if tag == "path" else shape_to_cmds(tag, el.attrib)
        if cmds:
            paths.append(cmds)
    return paths


def main():
    ap = argparse.ArgumentParser(description="同梱アイコン集を Tabler Icons から作り直す（保守用）")
    ap.add_argument("--version", default="3.19.0")
    args = ap.parse_args()
    icons, failed = {}, []
    for name, (ja, en) in ICONS.items():
        try:
            paths = convert(fetch(name, args.version))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{name}: {e}")
            continue
        icons[name] = {"ja": ja.split(), "en": en.split(), "paths": paths}
    data = {"source": f"Tabler Icons v{args.version} (outline) https://tabler.io/icons",
            "license": "MIT License, Copyright (c) 2020-2024 Paweł Kuna（LICENSE-tabler.txt）",
            "viewbox": 24, "stroke_width": 2, "icons": icons}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"icons: {len(icons)} 点 → {OUT}")
    for f in failed:
        print("取得できなかった:", f, file=sys.stderr)


if __name__ == "__main__":
    main()

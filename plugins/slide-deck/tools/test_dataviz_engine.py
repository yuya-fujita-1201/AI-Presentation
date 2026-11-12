#!/usr/bin/env python3
"""dataviz_engine（kpi / chart）の単体テスト。

出力が canvas_engine の浄化（sanitize_elements）を問題 0 で通り、渡された矩形の中に収まること、
検証（fail / warn）が期待どおり働くことを確かめる。
"""
import copy
import itertools
import math
import unittest

import canvas_engine as ce
import dataviz_engine as dv
import proposal_engine as pe

THEME = {"colors": {"background": "#FFFFFF", "surface": "#E0E7F0", "text": "#1A2233", "muted": "#5A6B85",
                    "primary": "#0F3D6E", "accent": "#007D96", "on_primary": "#FFFFFF", "border": "#BCC8D8",
                    "heading_text": "#0F3D6E"}, "fonts": {"heading": "Meiryo", "body": "Meiryo"}}
ST_KPI = {"body": dict(dv.DEFAULT_LAYOUT["kpi"]["body"])}
ST_CHART = {"body": dict(dv.DEFAULT_LAYOUT["chart"]["body"])}
FULL = {"x": 72, "y": 192, "w": 1136, "h": 452}
SMALL = {"x": 100, "y": 150, "w": 520, "h": 360}
TINY = {"x": 10, "y": 10, "w": 240, "h": 160}

Q = ["Q1", "Q2", "Q3", "Q4（見込み）"]
KPI_SLIDES = {
    "hero_from_to": {"type": "kpi", "items": [{"value": "2.1", "unit": "時間", "label": "提案書 1 件の作成時間", "from": "6.5",
                                              "delta": "−68%", "good": "down", "note": "パイロット 3 チーム 12 名・2 か月"}]},
    "hero_plain": {"type": "kpi", "items": [{"value": 1280, "unit": "万円", "label": "初年度の効果"}]},
    "three": {"type": "kpi", "items": [
        {"value": "2.1", "unit": "時間", "label": "作成時間", "from": "6.5", "delta": "−68%", "good": "down", "note": "n=12"},
        {"value": "9", "unit": "%", "label": "差し戻し率", "from": "22"},
        {"value": "9", "of": "12", "unit": "部署", "label": "ヒアリング完了"}]},
    "four": {"type": "kpi", "items": [{"value": str(i * 11), "unit": "件", "label": f"指標{i}"} for i in range(1, 5)]},
    "six": {"type": "kpi", "items": [{"value": str(i * 111), "unit": "件", "label": f"指標{i}", "delta": "+5%", "good": "up"}
                                     for i in range(1, 7)]},
    "bad_delta": {"type": "kpi", "items": [{"value": "30", "unit": "%", "from": "20", "delta": "+10pt", "good": "down"}]},
    "long": {"type": "kpi", "items": [{"value": "1,234,567", "unit": "円／月", "label": "とても長いラベルの指標名がここに入ります、二行になるかもしれません",
                                       "note": "注記も長めの文章で二行以上になる場合を想定したテキスト。"}]},
    "empty": {"type": "kpi", "items": []},
}
CHART_SLIDES = {
    "bar_annot_forecast": {"type": "chart", "chart": "bar", "unit": "時間", "categories": Q,
                           "series": [{"name": "作成時間", "values": [6.8, 6.5, 2.4, 2.1]}],
                           "highlight": ["Q3", "Q4（見込み）"], "forecast_from": "Q4（見込み）",
                           "annotations": [{"at": "Q3", "text": "パイロット開始"}], "y": {"min": 0, "max": 8, "label": "時間／件"},
                           "note": "Q3 から急減した"},
    "bar_multi": {"type": "chart", "chart": "bar", "unit": "件", "categories": Q,
                  "series": [{"name": "営業", "values": [10, 20, 30, 40]}, {"name": "企画", "values": [15, 25, 22, 35]},
                             {"name": "開発", "values": [5, 8, 12, 9]}]},
    "bar_negative": {"type": "chart", "chart": "bar", "unit": "%", "categories": ["A", "B", "C", "D", "E"],
                     "series": [{"name": "増減", "values": [12.5, -8.2, 3.1, -15.4, 6]}]},
    "hbar8": {"type": "chart", "chart": "hbar", "unit": "件",
              "categories": ["製造", "物流", "営業", "経理", "人事", "法務", "情報システム", "購買・調達部門"],
              "series": [{"name": "提案書数", "values": [142, 118, 96, 71, 54, 38, 27, 12]}], "highlight": ["製造", "物流"]},
    "hbar_negative": {"type": "chart", "chart": "hbar", "categories": ["A", "B", "C"],
                      "series": [{"name": "x", "values": [-30, 20, 45]}]},
    "stacked": {"type": "chart", "chart": "stacked", "unit": "人", "categories": ["2024", "2025", "2026"],
                "series": [{"name": "正社員", "values": [100, 110, 120]}, {"name": "契約", "values": [30, 28, 25]},
                           {"name": "派遣", "values": [10, 12, 9]}]},
    "line2": {"type": "chart", "chart": "line", "unit": "時間", "categories": ["1月", "2月", "3月", "4月", "5月", "6月"],
              "series": [{"name": "営業", "values": [6.8, 6.5, 5.1, 3.4, 2.6, 2.1]},
                         {"name": "企画", "values": [8.2, 8.0, 7.4, 5.0, 3.6, 2.9]}], "forecast_from": "6月"},
    "line_gap": {"type": "chart", "chart": "line", "categories": list("abcdefgh"),
                 "series": [{"name": "s", "values": [1, 2, None, 4, 5, None, None, 8]}]},
    "waterfall": {"type": "chart", "chart": "waterfall", "unit": "時間", "good": "down",
                  "categories": ["導入前", "下書き", "レビュー", "図表", "新規", "導入後"],
                  "series": [{"name": "t", "values": [6.5, -2.4, -1.3, -0.9, 0.2, 2.1]}]},
    "waterfall_cross": {"type": "chart", "chart": "waterfall", "categories": ["開始", "減", "さらに減", "戻し", "合計"],
                        "series": [{"name": "t", "values": [5, -8, -3, 6, None]}]},
    "donut": {"type": "chart", "chart": "donut", "unit": "%", "categories": ["A", "B", "C", "D"],
              "series": [{"name": "構成", "values": [45, 30, 15, 10]}]},
    "long_labels": {"type": "chart", "chart": "bar", "categories": ["とても長いカテゴリ名その一", "とても長いカテゴリ名その二",
                                                                  "とても長いカテゴリ名その三", "短い"],
                    "series": [{"name": "x", "values": [3, 5, 2, 9]}]},
    "many": {"type": "chart", "chart": "bar", "categories": [f"項目{i}" for i in range(20)],
             "series": [{"name": "x", "values": [i * 3.3 for i in range(20)]}]},
    "zero_values": {"type": "chart", "chart": "bar", "categories": ["a", "b"], "series": [{"name": "x", "values": [0, 0]}]},
    "no_data": {"type": "chart", "chart": "bar", "categories": [], "series": []},
    "one_point": {"type": "chart", "chart": "line", "categories": ["a"], "series": [{"name": "x", "values": [3]}]},
    "big_numbers": {"type": "chart", "chart": "bar", "unit": "円", "categories": ["a", "b", "c"],
                    "series": [{"name": "x", "values": [1234567, 2345678, 345678]}]},
    # --- レビュー指摘の再発防止用 ---
    "hbar_multi12": {"type": "chart", "chart": "hbar", "unit": "件", "categories": [f"部門{i}" for i in range(12)],
                     "series": [{"name": f"系列{k}", "values": [(i * 7 + k * 13) % 90 + 5 for i in range(12)]}
                                for k in range(3)]},
    "hbar_multi4": {"type": "chart", "chart": "hbar", "unit": "件", "categories": [f"部門{i}" for i in range(4)],
                    "series": [{"name": f"系列{k}", "values": [(i * 7 + k * 13) % 90 + 5 for i in range(4)]}
                               for k in range(3)]},
    "stacked_negative": {"type": "chart", "chart": "stacked", "unit": "百万円", "categories": ["Q1", "Q2", "Q3"],
                         "series": [{"name": "売上", "values": [100, 120, 150]}, {"name": "返品", "values": [-10, -25, -8]}]},
    "line5": {"type": "chart", "chart": "line", "unit": "件", "categories": [f"部門{i}" for i in range(1, 9)],
              "series": [{"name": f"系列{k + 1}", "values": v} for k, v in enumerate((
                  [41, 84, 49, 21, 45, 89, 90, 49], [71, 85, 64, 93, 65, 78, 54, 90], [97, 20, 69, 85, 36, 86, 91, 46],
                  [74, 27, 81, 66, 92, 90, 45, 84], [72, 82, 65, 73, 64, 20, 88, 89]))]},
    "bar_anno_neighbors": {"type": "chart", "chart": "bar", "categories": [f"Q{i}" for i in range(10)],
                           "series": [{"name": "s", "values": [9, 9, 1, 9, 9, 9, 9, 9, 9, 9]}],
                           "annotations": [{"at": "Q2", "text": "パイロット制度を開始した月"}]},
    "bar_thin": {"type": "chart", "chart": "bar", "categories": [f"c{i}" for i in range(20)],
                 "series": [{"name": f"s{k}", "values": [(i + k) % 7 + 1 for i in range(20)]} for k in range(5)],
                 "values": False},
    "donut_many": {"type": "chart", "chart": "donut", "categories": [f"項目{i}" for i in range(20)],
                   "series": [{"name": "x", "values": [1] * 20}]},
    "donut_big": {"type": "chart", "chart": "donut", "unit": "円", "categories": ["東京", "大阪", "名古屋"],
                  "series": [{"name": "x", "values": [1234567, 2345678, 345678]}]},
    "tiny_values": {"type": "chart", "chart": "bar", "unit": "%", "categories": ["a", "b"],
                    "series": [{"name": "x", "values": [0.004, 0.0002]}]},
}


def inside(el, body, tol=0.6):
    return (el["x"] >= body["x"] - tol and el["y"] >= body["y"] - tol and
            el["x"] + el["w"] <= body["x"] + body["w"] + tol and el["y"] + el["h"] <= body["y"] + body["h"] + tol)


def text_issues(els):
    """文字の見積もり幅・高さが箱に収まるか（収まらない要素 [(種類, 名前, 文字)]）。"""
    ctx = pe.Ctx(THEME)
    out = []
    for e in els:
        t = e.get("text")
        if not t:
            continue
        ins = t.get("insets", [0, 0, 0, 0])
        iw, ih = e["w"] - ins[0] - ins[2], e["h"] - ins[1] - ins[3]
        tot_h = 0.0
        for p in t["paragraphs"]:
            runs = p["runs"]
            txt = "".join(r["text"] for r in runs)
            sz = max(r["size"] for r in runs)
            bold = any(r.get("bold") for r in runs)
            w = sum(dv.tw(ctx, r["text"], r["size"], bold=bool(r.get("bold")), head=True) for r in runs)
            if t.get("wrap") is False:
                n = 1
                if w > iw + 1.5:
                    out.append(("wide", e.get("name"), txt[:16]))
            else:
                n = len(dv.wrap(ctx, txt, sz, iw, bold=bold, head=True)) if iw > 0 else 99
            tot_h += n * sz * 1.2 * p.get("lineHeight", 1.0)
        if tot_h > ih + 2:
            out.append(("tall", e.get("name"), "".join(r["text"] for r in t["paragraphs"][0]["runs"])[:16]))
    return out


def rects_hit(a, b, pad=0):
    return not (a["x"] + a["w"] + pad <= b["x"] or b["x"] + b["w"] + pad <= a["x"] or a["y"] + a["h"] + pad <= b["y"] or
                b["y"] + b["h"] + pad <= a["y"])


def run(kind, slide, body):
    ctx = pe.Ctx(THEME)
    fn = dv.layout_kpi if kind == "kpi" else dv.layout_chart
    return fn(slide, ST_KPI if kind == "kpi" else ST_CHART, ctx, body)


class SafetyTests(unittest.TestCase):
    def check(self, name, kind, slide, body):
        els = run(kind, slide, body)
        self.assertTrue(els, f"{name}: 要素が空")
        issues = []
        ce.sanitize_elements(els, issues=issues)
        self.assertEqual(issues, [], f"{name}: sanitize で置換あり {issues[:3]}")
        outside = [(e.get("name"), e["x"], e["y"], e["w"], e["h"]) for e in els if not inside(e, body)]
        self.assertEqual(outside, [], f"{name} @ {body['w']}x{body['h']}: 矩形の外に出た要素 {outside[:4]}")
        if body["w"] >= 500:      # 文字が箱に収まるか（極小の矩形は対象外）
            self.assertEqual(text_issues(els), [], f"{name} @ {body['w']}x{body['h']}: 文字が箱に収まらない")
        for e in els:
            for k in ("x", "y", "w", "h"):
                self.assertTrue(math.isfinite(e[k]), f"{name}: {k} が有限でない")
        return els

    def test_kpi_all_sizes(self):
        for (name, s), body in itertools.product(KPI_SLIDES.items(), (FULL, SMALL, TINY)):
            with self.subTest(name=name, w=body["w"]):
                self.check(name, "kpi", s, body)

    def test_chart_all_sizes(self):
        for (name, s), body in itertools.product(CHART_SLIDES.items(), (FULL, SMALL, TINY)):
            with self.subTest(name=name, w=body["w"]):
                self.check(name, "chart", s, body)

    def test_chart_all_sizes_without_note_and_with_note(self):
        for name, s in CHART_SLIDES.items():
            s2 = dict(s, note="読み取りの一言です")
            for body in (FULL, SMALL):
                with self.subTest(name=name, w=body["w"]):
                    self.check(name + "+note", "chart", s2, body)

    def test_chart_no_values_flag(self):
        for name in ("bar_multi", "stacked", "line2", "hbar8", "waterfall"):
            for flag in (False, "ends"):
                with self.subTest(name=name, flag=flag):
                    self.check(name, "chart", dict(CHART_SLIDES[name], values=flag), FULL)

    def test_garbage_does_not_crash(self):
        bad = [{"type": "chart", "chart": "zzz", "categories": ["a"], "series": [{"values": ["x"]}]},
               {"type": "chart", "categories": "abc", "series": "q"},
               {"type": "chart", "categories": ["a", "b"], "series": [{"name": "s", "values": [1]}]},
               {"type": "chart", "categories": ["a"], "series": [{"values": [1]}], "annotations": [{"at": "zz", "text": "x"}]},
               {"type": "chart", "categories": ["a", "b"], "series": [{"values": [1, 2]}], "y": {"min": 5, "max": 1}},
               {"type": "kpi", "items": [None, 3, {"value": None}, {"value": 5, "of": 0}]},
               {"type": "kpi", "items": "abc"}]
        for k, s in enumerate(bad):
            with self.subTest(k=k):
                self.check(f"bad{k}", s["type"], s, FULL)


class KpiTests(unittest.TestCase):
    def names(self, slide, body=FULL):
        return {e.get("name"): e for e in run("kpi", slide, body)}

    def test_hero_number_is_large(self):
        els = run("kpi", KPI_SLIDES["hero_from_to"], FULL)
        num = next(e for e in els if e.get("name") == "数字")
        sizes = [r["size"] for r in num["text"]["paragraphs"][0]["runs"]]
        self.assertGreaterEqual(max(sizes), 100)
        self.assertEqual(num["text"]["wrap"], False)

    def test_to_value_uses_accent_and_from_uses_muted(self):
        num = next(e for e in run("kpi", KPI_SLIDES["hero_from_to"], FULL) if e.get("name") == "数字")
        runs = num["text"]["paragraphs"][0]["runs"]
        texts = [r["text"] for r in runs]
        self.assertIn("6.5", texts[0])
        self.assertEqual(next(r for r in runs if r["text"] == "2.1")["color"], "#007D96")
        self.assertEqual(runs[0]["color"], "#5A6B85")
        # 単位は数字より小さい
        unit = next(r for r in runs if "時間" in r["text"] and r is not runs[1])
        self.assertLess(unit["size"], next(r for r in runs if r["text"] == "2.1")["size"])

    def test_delta_color_follows_good(self):
        # 向きの三角は意味色そのもの。チップの文字は同じ系統の色で、背景との対比が 4.5:1 以上になるよう暗くしてある
        for slide, key in ((KPI_SLIDES["hero_from_to"], "positive"), (KPI_SLIDES["bad_delta"], "negative")):
            n = self.names(slide)
            self.assertEqual(n["増減の向き"]["fill"], dv.SEMANTIC_COLORS[key])
            chip = n["変化"]
            tcol = chip["text"]["paragraphs"][0]["runs"][0]["color"]
            self.assertGreaterEqual(dv.contrast(tcol, chip["fill"]), 4.5, f"{key}: チップの文字の対比が低い")
            r, g_, b_ = dv._hex(tcol)
            self.assertTrue(g_ > r if key == "positive" else r > g_, f"{key}: 文字色の系統が違う {tcol}")

    def test_progress_bar_ratio(self):
        n = self.names(KPI_SLIDES["three"])
        track, fill = n["進捗の地3"], n["進捗3"]
        self.assertAlmostEqual(fill["w"] / track["w"], 9 / 12, places=2)

    def test_tiles_share_slots(self):
        n = self.names(KPI_SLIDES["three"])
        ys = {n[f"数字{i}"]["y"] for i in (1, 2, 3)}
        self.assertEqual(len(ys), 1, "並べた数字の高さがそろっていない")

    def test_emphasis_limited(self):
        s = {"type": "kpi", "items": [{"value": str(i), "from": str(i + 1), "unit": "件"} for i in range(3)]}
        for e in run("kpi", s, FULL):
            if e.get("name", "").startswith("数字"):
                self.assertNotIn("#007D96", [r["color"] for r in e["text"]["paragraphs"][0]["runs"]])

    def test_small_rect_shrinks_number(self):
        big = next(e for e in run("kpi", KPI_SLIDES["hero_from_to"], FULL) if e["name"] == "数字")
        small = next(e for e in run("kpi", KPI_SLIDES["hero_from_to"], SMALL) if e["name"] == "数字")
        mx = lambda e: max(r["size"] for r in e["text"]["paragraphs"][0]["runs"])       # noqa: E731
        self.assertLess(mx(small), mx(big))
        w = dv._Tile.runs_w(pe.Ctx(THEME), [{"text": r["text"], "size": r["size"], "font": r["font"], "bold": r["bold"]}
                                           for r in small["text"]["paragraphs"][0]["runs"]])
        self.assertLessEqual(w, SMALL["w"])


class ChartTests(unittest.TestCase):
    def els(self, name, body=FULL, **over):
        return run("chart", dict(CHART_SLIDES[name], **over), body)

    def by_name(self, els):
        return {e.get("name"): e for e in els}

    def test_bar_heights_proportional(self):
        n = self.by_name(self.els("bar_multi"))
        a, b = n["棒:Q1/営業"], n["棒:Q4（見込み）/営業"]
        self.assertAlmostEqual(b["h"] / a["h"], 4.0, places=1)

    def test_highlight_only_colors_selected(self):
        n = self.by_name(self.els("bar_annot_forecast"))
        self.assertEqual(n["棒:Q3"]["fill"], "#007D96")
        self.assertNotEqual(n["棒:Q1"]["fill"], "#007D96")
        self.assertEqual(n["棒:Q1"]["fill"], n["棒:Q2"]["fill"])

    def test_no_highlight_uses_primary_not_accent(self):
        n = self.by_name(self.els("hbar8", highlight=[]))
        self.assertTrue(all(e["fill"] == "#0F3D6E" for k, e in n.items() if str(k).startswith("棒:")))

    def test_forecast_is_dashed_and_light(self):
        n = self.by_name(self.els("bar_annot_forecast"))
        self.assertEqual(n["棒:Q4（見込み）"]["line"]["dash"], "dash")
        self.assertNotIn("line", n["棒:Q3"])
        self.assertGreater(dv.luminance(n["棒:Q4（見込み）"]["fill"]), dv.luminance(n["棒:Q3"]["fill"]))

    def test_single_series_has_no_legend_multi_has(self):
        self.assertFalse([e for e in self.els("bar_annot_forecast") if str(e.get("name", "")).startswith("凡例")])
        self.assertTrue([e for e in self.els("bar_multi") if str(e.get("name", "")).startswith("凡例")])

    def test_bar_width_capped(self):
        n = self.by_name(self.els("bar_annot_forecast"))
        self.assertLessEqual(n["棒:Q1"]["w"], 96.01)
        two = run("chart", dict(CHART_SLIDES["bar_annot_forecast"], categories=["a", "b"],
                                series=[{"name": "x", "values": [1, 2]}], highlight=[], annotations=[], forecast_from=None),
                  FULL)
        self.assertLessEqual(max(e["w"] for e in two if str(e.get("name")).startswith("棒")), 96.01)

    def test_negative_bars_go_below_baseline(self):
        n = self.by_name(self.els("bar_negative"))
        base = n["棒:A"]["y"] + n["棒:A"]["h"]
        self.assertAlmostEqual(n["棒:B"]["y"], base, delta=1.0)
        self.assertGreater(n["棒:D"]["h"], n["棒:B"]["h"])

    def test_value_labels_have_unit_and_separators(self):
        n = self.by_name(self.els("big_numbers"))
        t = n["値:a"]["text"]["paragraphs"][0]["runs"][0]["text"]
        self.assertEqual(t, "1,234,567円")

    def test_value_labels_do_not_overlap_each_other(self):
        for name in ("bar_multi", "stacked", "hbar8", "line2", "waterfall", "bar_negative"):
            texts = [e for e in self.els(name) if str(e.get("name", "")).startswith("値:")]
            for a, b in itertools.combinations(texts, 2):
                hit = not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or a["y"] + a["h"] <= b["y"] or
                           b["y"] + b["h"] <= a["y"])
                self.assertFalse(hit, f"{name}: 値ラベルが重なる {a['name']} / {b['name']}")

    def test_annotation_does_not_cover_value_labels(self):
        els = self.els("bar_annot_forecast")
        ann = next(e for e in els if str(e.get("name")).startswith("注釈:"))
        for e in els:
            if str(e.get("name", "")).startswith("値:"):
                hit = not (ann["x"] + ann["w"] <= e["x"] or e["x"] + e["w"] <= ann["x"] or ann["y"] + ann["h"] <= e["y"]
                           or e["y"] + e["h"] <= ann["y"])
                self.assertFalse(hit)

    def test_axis_ticks_are_round(self):
        for lo, hi in ((0, 6.8), (0, 142), (0, 1234567), (-15.4, 12.5), (0, 0.37)):
            a, b, step = dv.nice_axis(lo, hi, 5)
            self.assertLessEqual(a, lo)
            self.assertGreaterEqual(b, hi)
            mag = 10 ** math.floor(math.log10(step))
            self.assertIn(round(step / mag, 6), (1, 2, 2.5, 5, 10))
        ticks = dv._ticks(0, 0.6, 0.2)
        self.assertEqual(ticks, [0, 0.2, 0.4, 0.6])

    def test_waterfall_bar_geometry(self):
        n = self.by_name(self.els("waterfall"))
        # 下書きの棒の上端は開始の棒の上端と同じ、下端はレビューの棒の上端と同じ
        self.assertAlmostEqual(n["棒:下書き"]["y"], n["棒:導入前"]["y"], delta=1)
        self.assertAlmostEqual(n["棒:下書き"]["y"] + n["棒:下書き"]["h"], n["棒:レビュー"]["y"], delta=1)
        # 最後の合計（None）は積み上げと一致
        self.assertAlmostEqual(n["棒:導入後"]["h"] / n["棒:導入前"]["h"], 2.1 / 6.5, places=1)

    def test_waterfall_total_auto(self):
        n = self.by_name(self.els("waterfall_cross"))
        self.assertIn("棒:合計", n)

    def test_line_gap_splits_path(self):
        els = self.els("line_gap")
        self.assertEqual(len([e for e in els if str(e.get("name")).startswith("線:")]), 2)

    def test_donut_segments_sum_to_full(self):
        els = [e for e in self.els("donut") if str(e.get("name")).startswith("構成:")]
        self.assertEqual(len(els), 4)
        self.assertEqual({e["geom"] for e in els}, {"custom"})
        for e in els:
            for c in e["path"][0]["cmds"]:
                for v in c[1:]:
                    self.assertTrue(-0.15 * e["w"] <= v <= 1.15 * e["w"])

    def test_diagnostics(self):
        ctx = pe.Ctx(THEME)
        d = dv.diagnose_chart(CHART_SLIDES["many"], ST_CHART, ctx, SMALL)
        self.assertTrue(d, "項目が多い小さな矩形で警告が出ない")
        crowd = dict(CHART_SLIDES["bar_annot_forecast"], annotations=[
            {"at": "Q1", "text": "とても長い注釈その一です"}, {"at": "Q2", "text": "とても長い注釈その二です"},
            {"at": "Q3", "text": "とても長い注釈その三です"}, {"at": "Q4（見込み）", "text": "とても長い注釈その四です"}])
        # 混み合う注釈は、重ならないように置く（箱・棒・値ラベルと交差しない）か、置けないなら診断を出す
        for body in (SMALL, TINY):
            d2 = dv.diagnose_chart(crowd, ST_CHART, ctx, body)
            els = run("chart", crowd, body)
            anns = [e for e in els if str(e.get("name")).startswith("注釈:")]
            others = [e for e in els if str(e.get("name", "")).startswith(("棒:", "値:"))]
            clash = any(rects_hit(a, b) for a, b in itertools.combinations(anns, 2)) or \
                any(rects_hit(a, b) for a in anns for b in others)
            self.assertTrue(not clash or any(c.startswith("annotation") for c, _ in d2),
                            f"{body['w']}x{body['h']}: 注釈が重なるのに診断が出ない {d2}")


class ValidateTests(unittest.TestCase):
    def v(self, slide):
        fails, warns = [], []
        dv.validate(slide, 0, fails.append, warns.append)
        return fails, warns

    def test_valid_slides_have_no_fail(self):
        for name, s in {**KPI_SLIDES, **CHART_SLIDES}.items():
            if name in ("empty", "no_data"):
                continue
            f, w = self.v(s)
            self.assertEqual(f, [], f"{name}: {f}")

    def test_kpi_failures(self):
        self.assertTrue(self.v({"type": "kpi"})[0])
        self.assertTrue(self.v({"type": "kpi", "items": [{"unit": "x"}]})[0])
        f, _ = self.v({"type": "kpi", "items": [{"value": 1, "good": "dwon", "delta": "-1"}]})
        self.assertTrue(f and "down" in f[0])
        _, w = self.v({"type": "kpi", "items": [{"value": 1, "lable": "x"}]})
        self.assertTrue(any("label" in x for x in w))
        _, w = self.v({"type": "kpi", "items": [{"value": i} for i in range(5)]})
        self.assertTrue(any("5件" in x for x in w))
        _, w = self.v({"type": "kpi", "items": [{"value": 5, "of": 3}]})
        self.assertTrue(w)

    def test_chart_failures(self):
        s = CHART_SLIDES["bar_multi"]
        f, _ = self.v(dict(s, chart="bra"))
        self.assertTrue(f and "bar" in f[0])
        f, _ = self.v(dict(s, series=[{"name": "a", "values": [1, 2]}]))
        self.assertTrue(f and "個数" in f[0])
        f, _ = self.v(dict(s, series=[{"name": "a", "values": [1, "x", 3, 4]}]))
        self.assertTrue(f and "数値" in f[0])
        f, _ = self.v(dict(s, forecast_from="Q9"))
        self.assertTrue(f)
        f, _ = self.v(dict(s, annotations=[{"at": "Q9", "text": "x"}]))
        self.assertTrue(f)
        f, _ = self.v(dict(s, y={"min": 5, "max": 1}))
        self.assertTrue(f)
        f, _ = self.v({"type": "chart", "chart": "bar"})
        self.assertTrue(f)
        f, _ = self.v(dict(CHART_SLIDES["donut"], series=[{"name": "a", "values": [1, -2, 3, 4]}]))
        self.assertTrue(f)

    def test_chart_warnings(self):
        _, w = self.v(CHART_SLIDES["many"])
        self.assertTrue(any("hbar" in x for x in w))
        _, w = self.v(dict(CHART_SLIDES["bar_multi"], highlight=["Q9"]))
        self.assertTrue(any("highlight" in x for x in w))
        _, w = self.v(dict(CHART_SLIDES["bar_multi"], unit2="x"))
        self.assertTrue(any("未知のキー" in x for x in w))
        _, w = self.v(dict(CHART_SLIDES["bar_multi"], hilight=["Q1"]))
        self.assertTrue(any("highlight" in x for x in w))
        _, w = self.v(dict(CHART_SLIDES["bar_annot_forecast"], y={"min": 0, "max": 5}))
        self.assertTrue(any("y.max" in x for x in w))
        _, w = self.v(dict(CHART_SLIDES["waterfall"], series=[{"name": "t", "values": [6.5, -2.4, -1.3, -0.9, 0.2, 9.9]}]))
        self.assertTrue(any("一致" in x for x in w))

    def test_known_keys_exposed(self):
        self.assertIn("items", dv.KNOWN_KEYS["kpi"])
        self.assertIn("annotations", dv.KNOWN_KEYS["chart"])
        self.assertEqual(set(dv.DEFAULT_LAYOUT), {"kpi", "chart"})
        for t in ("kpi", "chart"):
            for k in ("eyebrow", "title", "rule", "lead", "body", "footer_l", "footer_r"):
                self.assertIn(k, dv.DEFAULT_LAYOUT[t])

    def test_default_layout_is_independent_copy(self):
        a = dv.default_layout()
        a["kpi"]["body"]["gap"] = 999
        self.assertNotEqual(dv.default_layout()["kpi"]["body"]["gap"], 999)


class ReviewFixTests(unittest.TestCase):
    """独立レビューで見つかった不具合の再発防止（指摘 ID をテスト名に付けている）。"""

    def els(self, name_or_slide, body=FULL, **over):
        s = CHART_SLIDES[name_or_slide] if isinstance(name_or_slide, str) else name_or_slide
        return run("chart", dict(s, **over), body)

    def names(self, els):
        return {e.get("name"): e for e in els}

    def diag(self, slide, body=FULL):
        return dv.diagnose_chart(slide, ST_CHART, pe.Ctx(THEME), body)

    def validate(self, slide):
        f, w = [], []
        dv.validate(slide, 0, f.append, w.append)
        return f, w

    def text_of(self, e):
        return "".join(r["text"] for p in e["text"]["paragraphs"] for r in p["runs"])

    # --- C-01 series.color -------------------------------------------------
    def test_c01_bad_series_color_fails_validate_and_never_crashes(self):
        base = dict(CHART_SLIDES["bar_multi"], forecast_from="Q4（見込み）")
        for bad in ("#GGGGGG", "red", "#abc", 5, ""):
            s = dict(base, series=[dict(base["series"][0], color=bad)] + base["series"][1:])
            if bad != "":
                f, _ = self.validate(s)
                self.assertTrue(f and "series[0].color" in f[0], f"{bad!r}: fail にならない {f}")
            els = run("chart", s, FULL)           # 例外にならず、黒にもならない
            fills = {e["fill"] for e in els if str(e.get("name", "")).startswith("棒:") and "営業" in e["name"]}
            self.assertNotIn("#000000", fills, f"{bad!r}: 黒になった")
        ok = dict(base, series=[dict(base["series"][0], color="#C8382E")] + base["series"][1:])
        self.assertEqual(self.validate(ok)[0], [])
        n = self.names(run("chart", ok, FULL))
        self.assertEqual(n["棒:Q1/営業"]["fill"], "#C8382E")
        tok = dict(base, series=[dict(base["series"][0], color="accent")] + base["series"][1:])
        self.assertEqual(self.validate(tok)[0], [])
        self.assertEqual(self.names(run("chart", tok, FULL))["棒:Q1/営業"]["fill"], "#007D96")

    def test_c01_mix_is_total(self):
        self.assertEqual(dv.mix("#GGGGGG", "#FFFFFF", 0.5), dv.mix("#000000", "#FFFFFF", 0.5))
        self.assertTrue(dv.is_hex6(dv.mix("#102030", "#FFFFFF", 1.7)))
        self.assertEqual(dv.mix("#102030", "#FFFFFF", 5), "#FFFFFF")

    # --- C-02 highlight が一致しないとき -------------------------------------
    def test_c02_unmatched_highlight_keeps_normal_colors(self):
        for name in ("hbar8", "bar_annot_forecast"):
            n = self.els(name, highlight=["Q9"], forecast_from=None)
            fills = {e["fill"] for e in n if str(e.get("name", "")).startswith("棒:")}
            self.assertEqual(fills, {"#0F3D6E"}, f"{name}: 一致しない highlight で色が変わった {fills}")
        d = self.els("donut", highlight=["Q9"])
        fills = {e["fill"] for e in d if str(e.get("name", "")).startswith("構成:")}
        plain = {e["fill"] for e in self.els("donut") if str(e.get("name", "")).startswith("構成:")}
        self.assertEqual(fills, plain)

    def test_c02_hbar_series_name_highlight(self):
        s = {"type": "chart", "chart": "hbar", "categories": ["a", "b"],
             "series": [{"name": "営業", "values": [1, 2]}, {"name": "企画", "values": [2, 1]}], "highlight": ["営業"]}
        n = self.names(run("chart", s, FULL))
        self.assertEqual(n["棒:a/営業"]["fill"], "#0F3D6E")                     # 強調された系列は本来の色
        self.assertNotEqual(n["棒:a/企画"]["fill"], n["棒:a/営業"]["fill"])     # ほかは薄くなる
        self.assertEqual(n["棒:a/企画"]["fill"], n["棒:b/企画"]["fill"])

    def test_c02_hbar_category_highlight_still_works(self):
        n = self.names(self.els("hbar8"))
        self.assertEqual(n["棒:製造"]["fill"], "#007D96")
        self.assertNotEqual(n["棒:法務"]["fill"], "#007D96")

    # --- C-03 小さい値の目盛・値ラベル ----------------------------------------
    def test_c03_ticks_keep_precision(self):
        s = {"type": "chart", "chart": "bar", "categories": ["a", "b"], "series": [{"name": "x", "values": [0.06, 0.12]}],
             "values": False}
        labels = [e["name"][3:] for e in run("chart", s, FULL) if str(e.get("name", "")).startswith("目盛:")]
        self.assertEqual(len(labels), len(set(labels)), f"目盛が重複: {labels}")
        for lab in labels:
            v = float(lab.replace("−", "-"))
            self.assertAlmostEqual(v / 0.025, round(v / 0.025), places=6, msg=f"目盛 {lab} が刻みの倍数でない")

    def test_c03_tiny_values_are_not_rounded_to_zero(self):
        n = self.names(self.els("tiny_values"))
        self.assertEqual(self.text_of(n["値:a"]), "0.004%")
        self.assertNotIn(self.text_of(n["値:b"]), ("0%", "0.00%"))
        self.assertEqual(dv.fmt_val(0.0, 2), "0.00")
        self.assertEqual(dv.fmt_val(12.5, 1), "12.5")

    # --- C-04 / A-03 注釈 ---------------------------------------------------
    def test_c04_annotation_avoids_neighbor_bars(self):
        for kind in ("bar", "stacked"):
            for body in (FULL, SMALL):
                els = self.els("bar_anno_neighbors", body, chart=kind)
                ann = [e for e in els if str(e.get("name", "")).startswith("注釈:")]
                bars = [e for e in els if str(e.get("name", "")).startswith("棒:")]
                self.assertTrue(ann)
                for a in ann:
                    hit = [b["name"] for b in bars if rects_hit(a, b)]
                    self.assertEqual(hit, [], f"{kind} {body['w']}: 注釈が棒に重なった {hit}")

    def test_a03_short_annotation_is_one_line_with_room(self):
        ctx = pe.Ctx(THEME)
        s = dict(CHART_SLIDES["bar_multi"], annotations=[{"at": "Q2", "text": "施策A"}, {"at": "Q3", "text": "施策B"}])
        for body in (FULL, SMALL):
            for a in [e for e in run("chart", s, body) if str(e.get("name", "")).startswith("注釈:")]:
                par = a["text"]["paragraphs"]
                self.assertEqual(len(par), 1)
                self.assertFalse(a["text"].get("wrap", True), "1 行に収まる注釈は折り返さない設定にする")
                tw_ = dv.tw(ctx, self.text_of(a), par[0]["runs"][0]["size"], bold=True)
                self.assertGreaterEqual(a["w"] - 16 - tw_, 8, "内側の幅に 8px 以上の余裕が必要")

    # --- C-05 未知キー -------------------------------------------------------
    def test_c05_universal_and_underscore_keys_are_not_unknown(self):
        s = dict(CHART_SLIDES["bar_multi"], density="compact", autofit=True, pattern="x", blocks=[], _memo="メモ")
        s["series"] = [dict(x, _c=1) for x in s["series"]]
        _, w = self.validate(s)
        self.assertEqual([x for x in w if "未知のキー" in x], [], w)
        k = {"type": "kpi", "density": "compact", "_memo": 1, "items": [{"value": 1, "_c": 2}]}
        _, w = self.validate(k)
        self.assertEqual([x for x in w if "未知のキー" in x], [], w)
        _, w = self.validate(dict(CHART_SLIDES["bar_multi"], densty="x"))
        self.assertTrue(any("densty" in x for x in w))

    # --- C-06 / A-12 donut の凡例 -------------------------------------------
    def test_c06_donut_legend_at_all_sizes(self):
        s = {"type": "chart", "chart": "donut", "categories": ["営業部", "企画部", "開発部"],
             "series": [{"name": "x", "values": [5, 3, 2]}]}
        for w, h in ((1136, 452), (520, 360), (420, 300), (300, 300), (240, 160)):
            body = {"x": 0, "y": 0, "w": w, "h": h}
            els = run("chart", s, body)
            names = [e["name"] for e in els if str(e.get("name", "")).startswith("凡例:")]
            self.assertEqual(len(names), 3, f"{w}x{h}: 凡例の名前が出ていない")
            for e in els:
                self.assertTrue(inside(e, body), f"{w}x{h}: {e.get('name')} が矩形外")

    def test_c06_donut_legend_missing_is_diagnosed(self):
        d = self.diag(CHART_SLIDES["donut_many"], TINY)
        self.assertTrue(any(c == "donut-legend-no-room" for c, _ in d), d)

    def test_c11_donut_legend_name_and_share_are_close(self):
        s = {"type": "chart", "chart": "donut", "categories": ["A", "B", "C"], "series": [{"name": "x", "values": [50, 30, 20]}],
             "note": "ノート"}
        n = self.names(run("chart", s, FULL))
        r = n["凡例:A"]["text"]["paragraphs"][0]["runs"][0]
        name_end = n["凡例:A"]["x"] + dv.tw(pe.Ctx(THEME), "A", r["size"])
        gap = n["構成比:A"]["x"] + n["構成比:A"]["w"] - name_end          # 名前の右端から構成比の右端まで
        self.assertLess(gap, 120, f"名前と構成比が離れすぎ: {gap}px")
        self.assertGreaterEqual(n["凡例:A"]["text"]["paragraphs"][0]["runs"][0]["size"], 14)

    # --- C-07 細すぎる棒 ----------------------------------------------------
    def test_c07_thin_bars_get_diag_or_stay_visible(self):
        for body in (FULL, SMALL):
            els = self.els("bar_thin", body)
            bars = [e for e in els if str(e.get("name", "")).startswith("棒:")]
            self.assertGreaterEqual(min(e["w"] for e in bars), 2.0, f"{body['w']}: 棒が見えない幅")
        s = dict(CHART_SLIDES["bar_thin"], categories=[f"c{i}" for i in range(40)],
                 series=[dict(x, values=x["values"] * 2) for x in CHART_SLIDES["bar_thin"]["series"]])
        self.assertTrue(any(c == "bars-too-thin" for c, _ in self.diag(s, SMALL)))

    # --- C-08 / A-10 検証 ---------------------------------------------------
    def test_c08_y_min_above_data_warns_for_line(self):
        s = {"type": "chart", "chart": "line", "categories": list("abc"), "series": [{"name": "x", "values": [1, 5, 9]}],
             "y": {"min": 4}}
        _, w = self.validate(s)
        self.assertTrue(any("y.min" in x for x in w), w)

    def test_c09_kpi_length_warning_only_for_real_problems(self):
        def warns(v, **kw):
            return self.validate({"type": "kpi", "items": [dict({"value": v, "unit": "円"}, **kw)]})[1]
        for ok in ("1,234,567", "12,345.67", "1234567", "−12.5", "98.5%"):
            self.assertEqual([x for x in warns(ok) if "長すぎ" in x or "桁" in x], [], ok)
        self.assertTrue(any("万・億" in x for x in warns("1,234,567,890,123")))
        self.assertTrue(any("数字だけ" in x for x in warns("約3倍に増えたと言える結果")))

    def test_c12_duplicate_categories_warn(self):
        s = dict(CHART_SLIDES["bar_multi"], categories=["Q1", "Q1", "Q3", "Q4"])
        self.assertTrue(any("同じ名前" in x for x in self.validate(s)[1]))

    def test_a10_validation_holes(self):
        _, w = self.validate({"type": "kpi", "items": ["abc"]})
        self.assertTrue(any("値だけ" in x for x in w), w)
        f, _ = self.validate({"type": "kpi", "items": [{"value": {"a": 1}}]})
        self.assertTrue(f)
        _, w = self.validate({"type": "kpi", "items": [{"value": 9, "of": 12, "from": 5}]})
        self.assertTrue(any("併用" in x for x in w), w)
        _, w = self.validate(dict(CHART_SLIDES["bar_multi"], series=[{"name": "a", "values": [None] * 4}]))
        self.assertTrue(any("null" in x for x in w), w)
        _, w = self.validate(dict(CHART_SLIDES["bar_multi"], annotations=[{"at": "Q2", "text": "x", "series": "存在しない"}]))
        self.assertTrue(any("series" in x for x in w), w)
        _, w = self.validate(dict(CHART_SLIDES["bar_multi"], style={"body": {"bogus_key": 1, "tick_size": 14}}))
        self.assertTrue(any("bogus_key" in x for x in w), w)
        self.assertFalse(any("tick_size" in x for x in w))
        _, w = self.validate({"type": "kpi", "items": [{"value": 1}], "style": {"body": {"gapp": 3}}})
        self.assertTrue(any("gapp" in x for x in w), w)

    # --- A-01 hbar の値ラベル -----------------------------------------------
    def test_a01_multi_series_hbar_labels_never_overlap(self):
        for name in ("hbar_multi12", "hbar_multi4"):
            for body in (FULL, SMALL):
                els = self.els(name, body)
                vals = [e for e in els if str(e.get("name", "")).startswith("値:")]
                for a, b in itertools.combinations(vals, 2):
                    self.assertFalse(rects_hit(a, b), f"{name} {body['w']}: 値ラベルが重なる {a['name']} / {b['name']}")
        # 入らないときはラベルを省き、診断を出す。入るときは出す
        self.assertTrue(any(c == "value-labels-crowded" for c, _ in self.diag(CHART_SLIDES["hbar_multi12"])))
        self.assertTrue([e for e in self.els("hbar_multi4") if str(e.get("name", "")).startswith("値:")])
        f, w = self.validate(CHART_SLIDES["hbar_multi12"])
        self.assertTrue(any("値ラベル" in x for x in w), w)

    # --- A-02 折れ線の端点ラベル --------------------------------------------
    def test_a02_line_multi_series_end_labels_do_not_overlap(self):
        for body in (FULL, SMALL):
            els = self.els("line5", body)
            vals = [e for e in els if str(e.get("name", "")).startswith("値:")]
            self.assertTrue(vals)
            for a, b in itertools.combinations(vals, 2):
                self.assertFalse(rects_hit(a, b), f"{body['w']}: {a['name']} と {b['name']} の値ラベルが重なる")

    # --- A-04 donut の合計 ---------------------------------------------------
    def test_a04_donut_total_fits_in_hole(self):
        ctx = pe.Ctx(THEME)
        for body in (FULL, SMALL):
            els = self.els("donut_big", body)
            tot = next((e for e in els if e.get("name") == "合計"), None)
            self.assertIsNotNone(tot, f"{body['w']}: 合計が出ていない")
            ring = next(e for e in els if str(e.get("name", "")).startswith("構成:"))
            ro = ring["w"] / 2
            ri = ro * 0.62
            r0 = tot["text"]["paragraphs"][0]["runs"][0]
            self.assertLessEqual(dv.tw(ctx, r0["text"], r0["size"], bold=True, head=True), ri * 1.6 + 0.5)
        # 百分率の合計 100% は出さない
        n = self.names(self.els("donut"))
        self.assertNotIn("合計", n)

    # --- A-05 donut の色 -----------------------------------------------------
    def test_a05_donut_many_items_have_valid_colors(self):
        els = self.els("donut_many")
        for e in els:
            if "fill" in e:
                self.assertTrue(dv.is_hex6(e["fill"]), e)
        issues = []
        ce.sanitize_elements(copy.deepcopy(els), issues=issues)
        self.assertEqual(issues, [])

    # --- A-06 単系列の値ラベルの幅 -------------------------------------------
    def test_a06_single_series_labels_use_slot_width(self):
        s = {"type": "chart", "chart": "bar", "unit": "円", "categories": list("abc"),
             "series": [{"name": "x", "values": [1234567890, 2345678901, 345678901]}]}
        n = self.names(run("chart", s, FULL))
        r = n["値:a"]["text"]["paragraphs"][0]["runs"][0]
        self.assertTrue(r["text"].endswith("円"), "幅に余裕があるのに単位が外れた")
        self.assertGreaterEqual(r["size"], 16)

    # --- A-07 kpi の数字の大きさ ---------------------------------------------
    def test_a07_kpi_with_from_gets_bigger_numbers(self):
        s = {"type": "kpi", "items": [
            {"value": "2.1", "unit": "時間", "label": "作成時間", "from": "6.5", "delta": "−68%", "good": "down"},
            {"value": "98", "unit": "%", "label": "精度", "delta": "+3pt", "good": "up"},
            {"value": "1,280", "unit": "万円", "label": "年間削減額"},
            {"value": "3", "unit": "倍", "label": "処理件数", "from": "1", "note": "月次"}]}
        els = run("kpi", s, FULL)
        num = next(e for e in els if e.get("name") == "数字1")
        self.assertGreaterEqual(max(r["size"] for r in num["text"]["paragraphs"][0]["runs"]), 48)
        self.assertTrue(any(e.get("name") == "変化前1" for e in els))
        ys = {e["y"] for e in els if str(e.get("name", "")).startswith("数字")}
        self.assertEqual(len(ys), 1, "数字の行がそろっていない")
        self.assertEqual(text_issues(els), [])

    # --- A-08 チップの対比 ---------------------------------------------------
    def test_a08_delta_chip_text_contrast(self):
        for slide in (KPI_SLIDES["hero_from_to"], KPI_SLIDES["bad_delta"], KPI_SLIDES["three"]):
            for e in run("kpi", slide, FULL):
                if str(e.get("name", "")).startswith("変化") and "fill" in e:
                    c = e["text"]["paragraphs"][0]["runs"][0]["color"]
                    self.assertGreaterEqual(dv.contrast(c, e["fill"]), 4.5, e["name"])

    # --- A-13 stacked の負の値 -----------------------------------------------
    def test_a13_stacked_negative_labels(self):
        n = self.names(self.els("stacked_negative"))
        tops = [self.text_of(e) for k, e in n.items() if str(k) in ("値:Q1", "値:Q2", "値:Q3")]
        self.assertTrue(all(t.startswith("差引") for t in tops), tops)
        self.assertIn("値:Q1（マイナス）", n, "棒に入らない負の部分に値が出ていない")
        self.assertIn("−10", self.text_of(n["値:Q1（マイナス）"]))


class PptxSmokeTests(unittest.TestCase):
    def test_all_elements_render_to_pptx(self):
        from pptx import Presentation
        prs = Presentation()
        for name, s in {**KPI_SLIDES, **CHART_SLIDES}.items():
            sl = prs.slides.add_slide(prs.slide_layouts[6])
            els = run(s["type"], s, FULL)
            ce.add_canvas_to_pptx(sl, els)
            self.assertFalse(sl.has_notes_slide)
        # 再パースできる
        import io
        buf = io.BytesIO()
        prs.save(buf)
        Presentation(io.BytesIO(buf.getvalue()))


if __name__ == "__main__":
    unittest.main()

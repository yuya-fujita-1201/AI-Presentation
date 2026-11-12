#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3b 仕上げ: 図解タイプ（sequence・lifecycle・org・swimlane・house・kpi_tree・matrix）と schedule の再発防止テスト。

- sequence: 区間の見出しが生存線より上に描かれる・隣の枠との間に隙間がある
- lifecycle: 番号ラベルが図形の輪郭に重ならない（四角・角丸・ひし形・sharp）
- org: 提案範囲の枠が本文領域の中・札が枠の内側・連携の名前に地の色
- house: 柱の枠が中身に合わせて低くなり、全体が上下中央に寄る
- kpi_tree: 領域が狭いとき列を縮めて領域の中に収める
- matrix: 軸ラベルが格子に付いてくる
- swimlane: label_at がノードの文字に重なるときは自動配置に戻す・io の項目を 2 行に折って 10px を守る
- 双方向の矢印: label_back を逆向きのラベルとして反対側に置く
- schedule: 矢羽根に入らないラベルは自動で右に出す・節目の行を含めても行の合計が枠に収まる・外に出たラベルに地の色

実行: python3 -m unittest plugins/slide-deck/tools/test_s3b_diagram.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_deck as b  # noqa: E402
import diagram_engine as de  # noqa: E402
import proposal_engine as pe  # noqa: E402
import schedule_engine as se  # noqa: E402

PY = sys.executable
ROOT = TOOLS.parent
LAYOUT = b.load_json(ROOT / "templates" / "layouts" / "default.json")


def mk(slides, **meta):
    d = Path(tempfile.mkdtemp(prefix="s3b_"))
    m = {"id": "d", "title": "T", "theme": "default"}
    m.update(meta)
    (d / "deck.json").write_text(json.dumps({"meta": m, "slides": slides}, ensure_ascii=False), encoding="utf-8")
    return d


def build_html(slides, **meta):
    d = mk(slides, **meta)
    p = subprocess.run([PY, str(TOOLS / "build_deck.py"), str(d)], capture_output=True, text=True)
    html = next(iter((d / "build").glob("*.html")), None)
    return p, (html.read_text(encoding="utf-8") if html else ""), d


def types_of(name):
    return LAYOUT["types"][name]


SEQ = {"type": "sequence", "title": "t",
       "participants": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
       "messages": [{"from": "a", "to": "b", "label": "m1"}, {"from": "b", "to": "a", "label": "m2", "variant": "return"},
                    {"from": "a", "to": "b", "label": "m3"}, {"from": "b", "to": "a", "label": "m4", "variant": "return"}],
       "segments": [{"from": 0, "to": 1, "label": "区間一"}, {"from": 2, "to": 3, "label": "区間二"}]}


class SequenceTest(unittest.TestCase):
    def test_segments_do_not_touch(self):
        geo = de.layout_sequence(SEQ, dict(types_of("sequence")["diagram"]), [])
        s1, s2 = geo["segments"]
        self.assertGreaterEqual(s2["y"] - (s1["y"] + s1["h"]), 6)       # 隣の枠との間に隙間（以前は約 6px で二重の破線に見えた）

    def test_segment_label_is_drawn_after_lifelines(self):
        _, html, _ = build_html([SEQ])
        self.assertIn("区間一", html)
        i_life = html.index('stroke-dasharray="6,5"')
        i_label = html.index("区間一")
        self.assertGreater(i_label, i_life)                               # 見出しの札が生存線より後（上）にある


class LifecycleStepTest(unittest.TestCase):
    D = {"step_size": 11}

    def _spec(self, shape, w=140, h=92, pill=999):
        class T:   # rtok が引く theme の代わり
            pass
        theme = {"colors": {"background": "#FFFFFF", "surface": "#EEEEEE", "accent": "#9900FF", "primary": "#000066"},
                 "tokens": {"radius": {"pill": pill}}}
        vis = {"shape": shape, "fill": "background"}
        box = {"x": 100, "y": 200, "w": w, "h": h}
        return b._step_label_spec(box, vis, dict(self.D), theme, {"step": "#9900FF"})

    def test_rect_stays_top_left_inside(self):
        s = self._spec("rect")
        self.assertEqual((s["x"], s["y"]), (108, 204))

    def test_pill_is_pushed_in_past_the_curve(self):
        s = self._spec("pill")
        # 半径 46 の曲線は、上端から 4px の高さで左端から約 19px 内側にある。番号の左端はそれより右
        self.assertGreater(s["x"] - 100, 19)

    def test_pill_without_radius_is_like_rect(self):
        s = self._spec("pill", pill=0)
        self.assertEqual(s["x"], 108)

    def test_diamond_label_sits_outside_the_outline(self):
        s = self._spec("diamond", w=156, h=104)
        # 外接矩形の左上の角（輪郭の外）。左の頂点 (0, h/2) と上の頂点 (w/2, 0) を結ぶ線より上にある
        self.assertLessEqual(s["x"] - 100, 8)
        edge_y = (104 / 2) * (1 - (s["x"] - 100 + 16) / (156 / 2))        # 番号の右端 x での輪郭の y
        self.assertLess(s["y"] - 200 + 11, edge_y)


ORG = {"type": "org", "title": "t", "legend": "(F) フル",
       "left": {"title": "貴社", "nodes": [{"id": "o", "title": "PO", "name": "本部長"},
                                          {"id": "p", "title": "PM", "parent": "o"}]},
       "right": {"title": "支援", "scope": "ご支援範囲",
                 "nodes": [{"id": "m", "title": "PM", "name": "1名"}, {"id": "l", "title": "リード", "parent": "m"}]},
       "links": [{"from": "o", "to": "m", "label": "ステアリング"}]}


class OrgTest(unittest.TestCase):
    def _els(self):
        ctx = pe.Ctx({"colors": {"primary": "#000066", "accent": "#9900FF", "background": "#FFFFFF", "muted": "#666666",
                                 "on_primary": "#FFFFFF", "text": "#111111", "border": "#CCCCCC", "heading_text": "#000066"},
                      "fonts": {}})
        st = {"body": dict(types_of("org")["body"])}
        body = {"x": 72, "y": 192, "w": 1136, "h": 452}
        return pe.layout_org(ORG, st, ctx, body), body

    def test_scope_frame_is_inside_the_body(self):
        els, body = self._els()
        frame = next(e for e in els if e.get("name") == "提案範囲")
        self.assertLessEqual(frame["x"] + frame["w"], body["x"] + body["w"] + 0.01)
        self.assertGreaterEqual(frame["x"], body["x"])

    def test_scope_tag_is_inside_the_frame(self):
        els, _ = self._els()
        frame = next(e for e in els if e.get("name") == "提案範囲")
        tag = next(e for e in els if e.get("name") == "提案範囲の札")
        self.assertLessEqual(tag["x"] + tag["w"], frame["x"] + frame["w"])
        self.assertLessEqual(tag["y"] + tag["h"], frame["y"] + frame["h"])

    def test_link_label_has_a_ground_fill(self):
        els, _ = self._els()
        lab = next(e for e in els if e.get("name") == "連携の名前")
        self.assertTrue(lab.get("fill"))                                  # 背後を通る破線枠が文字を貫通しない

    def test_roots_on_both_sides_stay_aligned(self):
        els, _ = self._els()
        ys = {e["name"]: e["y"] for e in els if e.get("name") in ("o", "m")}
        self.assertEqual(ys["o"], ys["m"])


class HouseTest(unittest.TestCase):
    H = {"type": "house", "title": "t", "roof": {"title": "目指す姿"},
         "pillars": [{"title": "柱1", "items": ["a", "b"]}, {"title": "柱2", "items": ["c"]}],
         "foundations": [{"title": "土台"}]}

    def _els(self, **over):
        ctx = pe.Ctx({"colors": {"primary": "#000066", "accent": "#9900FF", "background": "#FFFFFF", "muted": "#666666",
                                 "on_primary": "#FFFFFF", "text": "#111111", "border": "#CCCCCC", "heading_text": "#000066",
                                 "highlight_fill": "#DDCCFF", "on_primary_soft": "#EEE"}, "fonts": {}})
        g = dict(types_of("house")["body"]); g.update(over)
        body = {"x": 72, "y": 192, "w": 1136, "h": 452}
        return pe.layout_house(self.H, {"body": g}, ctx, body), body

    def test_pillar_box_shrinks_to_content_and_is_centered(self):
        els, body = self._els()
        pil = next(e for e in els if e.get("name") == "柱1の内容")
        self.assertLess(pil["h"], 452 - 84 - 38 - 46 - 20)                # 以前は領域いっぱい（約 250px）
        top = min(e["y"] for e in els)
        bottom = max(e["y"] + e["h"] for e in els)
        self.assertAlmostEqual(top - body["y"], body["y"] + body["h"] - bottom, delta=1.0)   # 上下の余白が等しい

    def test_fit_content_false_keeps_the_old_layout(self):
        els, body = self._els(fit_content=False)
        self.assertAlmostEqual(min(e["y"] for e in els), body["y"], delta=0.1)
        self.assertAlmostEqual(max(e["y"] + e["h"] for e in els), body["y"] + body["h"], delta=0.1)

    def test_dense_pillars_are_not_squeezed(self):
        h = dict(self.H, pillars=[{"title": "柱", "items": ["長い項目の文章です。" * 6] * 6}] * 3)
        ctx = pe.Ctx({"colors": {"primary": "#000066", "accent": "#9900FF", "background": "#FFFFFF", "muted": "#666666",
                                 "on_primary": "#FFFFFF", "text": "#111111", "border": "#CCCCCC", "heading_text": "#000066",
                                 "highlight_fill": "#DDCCFF"}, "fonts": {}})
        els = pe.layout_house(h, {"body": dict(types_of("house")["body"])}, ctx, {"x": 72, "y": 192, "w": 1136, "h": 452})
        self.assertLessEqual(max(e["y"] + e["h"] for e in els), 192 + 452 + 0.5)


class KpiTreeNarrowTest(unittest.TestCase):
    K = {"type": "kpi_tree", "title": "t", "root": "売上", "branches": [
        {"title": "新規", "kpis": [{"title": "商談数", "value": "100", "note": "月次の件数を CRM から集計する"}]}]}

    def _els(self, w):
        ctx = pe.Ctx({"colors": {"primary": "#000066", "accent": "#9900FF", "background": "#FFFFFF", "muted": "#666666",
                                 "on_primary": "#FFFFFF", "text": "#111111", "border": "#CCCCCC", "heading_text": "#000066",
                                 "surface": "#EEEEEE"}, "fonts": {}})
        return pe.layout_kpi_tree(self.K, {"body": dict(types_of("kpi_tree")["body"])}, ctx, {"x": 100, "y": 200, "w": w, "h": 300})

    def test_narrow_region_stays_inside(self):
        for w in (560, 700, 1136):
            els = self._els(w)
            right = max(e["x"] + e["w"] for e in els)
            self.assertLessEqual(right, 100 + w + 0.5, f"w={w}")      # 以前は幅 560 で x=1417 まで溢れた

    def test_full_width_is_unchanged(self):
        els = self._els(1136)
        root = next(e for e in els if e.get("name") == "目標")
        self.assertEqual(root["w"], 150)


class MatrixAxisTest(unittest.TestCase):
    AX = types_of("matrix")["axis"]

    def test_default_positions_match_the_old_hardcoded_ones(self):
        xa, ya = {"label": "コスト", "low": "低", "high": "高"}, {"label": "効果", "low": "小", "high": "大"}
        bx = b._matrix_axis_boxes(dict(self.AX), 172, 208, 1000, 372, xa, ya)
        r = [e["region"] for e in bx]
        self.assertEqual((r[0]["x"], r[0]["y"]), (72, 178))                # 縦軸の名前
        self.assertEqual((r[1]["x"], r[1]["y"]), (76, 214))                # 縦の高
        self.assertEqual((r[2]["x"], r[2]["y"]), (76, 552))                # 縦の低
        self.assertEqual((r[3]["x"], r[3]["y"]), (172, 610))               # 横軸の名前
        self.assertEqual((r[4]["x"], r[4]["y"]), (172, 586))
        self.assertEqual((r[5]["x"], r[5]["y"]), (1012, 586))
        self.assertEqual(bx[0]["text"], "▲ 効果")
        self.assertEqual(bx[3]["text"], "コスト ▶")

    def test_labels_follow_the_grid(self):
        bx = b._matrix_axis_boxes(dict(self.AX), 300, 250, 800, 300, {}, {"label": "Y"})
        self.assertEqual(bx[0]["region"]["x"], 200)                        # 格子の x から left_margin だけ左（x0 を書かなくても付いてくる）
        bx2 = b._matrix_axis_boxes({**self.AX, "x0": 40}, 300, 250, 800, 300, {}, {"label": "Y"})
        self.assertEqual(bx2["x"] if isinstance(bx2, dict) else bx2[0]["region"]["x"], 40)    # 明示した x0 が優先


SW_BASE = {"type": "swimlane", "title": "t", "lanes": [{"name": "L1"}, {"name": "L2"}], "cols": 3,
           "nodes": [{"id": "d", "lane": 0, "col": 1, "shape": "decision", "text": "判断?"},
                     {"id": "a", "lane": 1, "col": 1, "shape": "task", "text": "作業"},
                     {"id": "s", "lane": 0, "col": 0, "shape": "task", "text": "開始"}],
           "edges": [{"from": "s", "to": "d"}, {"from": "d", "to": "a", "label": "N"}]}


class SwimlaneTest(unittest.TestCase):
    def _geo(self, slide):
        deck_dir = mk([slide])
        deck, theme, layout = b.load_deck(deck_dir)
        st = b.resolve_style(layout, deck, deck["slides"][0])
        return b.swimlane_geometry(deck["slides"][0], st)

    def test_label_at_on_a_node_is_ignored(self):
        probe = self._geo(SW_BASE)
        d = probe["nodes"]["d"]
        slide = json.loads(json.dumps(SW_BASE))
        slide["edges"][1]["label_at"] = [d["cx"], d["cy"]]               # 菱形の文字の真上
        geo = self._geo(slide)
        e = geo["edges"][1]
        lb = e["label_box"]
        inner = de.rect_of(d["x"] + d["w"] * 0.2, d["y"] + d["h"] * 0.2, d["w"] * 0.6, d["h"] * 0.6)
        self.assertLessEqual(de.penetration(lb, inner), de.TOUCH_TOL)
        self.assertIn("label-at-ignored", [x["code"] for x in geo["diagnostics"]])

    def test_label_at_off_the_nodes_is_kept(self):
        slide = json.loads(json.dumps(SW_BASE))
        slide["edges"][1]["label_at"] = [600, 400]
        lb = self._geo(slide)["edges"][1]["label_box"]
        self.assertEqual((lb["cx"], lb["cy"]), (600.0, 400.0))

    def test_io_items_wrap_to_keep_10px(self):
        nd = {"input": ["ログ", "構成情報"], "output": ["原因分析報告"]}
        res = b._io_lines_fit(nd, 126, 57, 11, 10, 6)
        self.assertIsNotNone(res)
        lines, size = res
        self.assertGreaterEqual(size, 10)
        self.assertEqual(lines["output"][0], ["原因分析", "報告"])         # 漢字だけの語は 1 行目を長く
        self.assertEqual(lines["input"], [["ログ"], ["構成情報"]])

    def test_io_katakana_split_avoids_a_leading_long_vowel_mark(self):
        res = b._io_lines_fit({"output": ["ポストモーテム"]}, 126, 57, 11, 10, 6)
        self.assertIsNotNone(res)
        two = res[0]["output"][0]
        self.assertEqual(len(two), 2)
        self.assertFalse(two[1].startswith("ー"))

    def test_io_that_cannot_fit_returns_none(self):
        self.assertIsNone(b._io_lines_fit({"input": ["とても長い項目の名前が入っています" * 2]}, 100, 57, 11, 10, 6))


class BidirectionalLabelTest(unittest.TestCase):
    def _slide(self, **e):
        edge = {"from": "a", "to": "b", "arrow": "both", "label": "受注確定", "label_back": "在庫引当"}
        edge.update(e)
        return {"type": "architecture", "title": "t",
                "nodes": [{"id": "a", "label": "A", "row": 0, "col": 0}, {"id": "b", "label": "B", "row": 0, "col": 2}],
                "edges": [edge]}

    def test_back_label_goes_to_the_opposite_side(self):
        geo = de.layout_grid_diagram(self._slide(), "architecture", dict(types_of("architecture")["diagram"]), [])
        e = geo["edges"][0]
        self.assertIsNotNone(e["label_box"])
        self.assertIsNotNone(e["label_back_box"])
        self.assertLess(e["label_box"]["cy"], e["label_back_box"]["cy"])        # 行きは線の上・戻りは下
        self.assertLessEqual(de.penetration(e["label_box"], e["label_back_box"]), de.TOUCH_TOL)

    def test_both_labels_are_rendered_in_html(self):
        _, html, _ = build_html([self._slide()])
        self.assertIn("受注確定", html)
        self.assertIn("在庫引当", html)

    def test_label_back_without_both_warns(self):
        p, _, _ = build_html([self._slide(arrow="end")])
        self.assertIn("label_back", p.stderr)
        self.assertIn("arrow", p.stderr)

    def test_label_back_is_a_known_key(self):
        p, _, _ = build_html([self._slide()])
        self.assertNotIn("未知のキー", p.stderr)


def _sched(rows, **kw):
    s = {"type": "schedule", "title": "t", "timeline": {"start": "2026-09", "end": "2027-02", "unit": "month"}, "rows": rows}
    s.update(kw)
    return s


CHART = types_of("schedule")["chart"]
LONG = "とても長いラベルが入っています。" * 2     # 1 か月の矢羽根（約 140px）に 10px でも入らない長さ


class ScheduleTest(unittest.TestCase):
    def test_chart_follows_the_common_margin(self):
        self.assertEqual(CHART["x"], 72)
        self.assertEqual(CHART["x"] + CHART["w"], 1208)

    def test_long_label_goes_after_the_bar_when_there_is_room(self):
        s = _sched([{"label": "A", "bars": [{"start": "2026-09", "end": "2026-10", "label": LONG}]}])
        geo = se.layout_schedule(s, CHART)
        self.assertEqual(geo["bars"][0]["label_pos"], "after")
        self.assertIn("bar-label-moved", [d["code"] for d in geo["diagnostics"]])
        self.assertNotIn("bar-label-overflow", [d["code"] for d in geo["diagnostics"]])

    def test_explicit_inside_is_respected(self):
        s = _sched([{"label": "A", "bars": [{"start": "2026-09", "end": "2026-10", "label": LONG, "label_pos": "inside"}]}])
        geo = se.layout_schedule(s, CHART)
        self.assertEqual(geo["bars"][0]["label_pos"], "inside")

    def test_no_room_on_the_right_keeps_inside_and_warns(self):
        s = _sched([{"label": "A", "bars": [{"start": "2027-01", "end": "2027-03", "label": "とても長いラベルが入っているので右にも出せないとても長いラベルが入っているので右にも出せないとても長いラベルが入っているので右にも出せない"}]}])
        geo = se.layout_schedule(s, CHART)
        self.assertEqual(geo["bars"][0]["label_pos"], "inside")
        self.assertIn("bar-label-overflow", [d["code"] for d in geo["diagnostics"]])

    def test_next_bar_blocks_the_after_label(self):
        s = _sched([{"label": "A", "bars": [{"start": "2026-09", "end": "2026-09", "label": LONG},
                                            {"start": "2026-10", "end": "2026-11", "label": "次"}]}])
        geo = se.layout_schedule(s, CHART)
        self.assertEqual(geo["bars"][0]["label_pos"], "inside")

    def test_rows_with_milestones_fit_the_area(self):
        rows = [{"label": f"R{i}", "bars": [{"start": "2026-09", "end": "2026-11", "label": "x"}]} for i in range(6)]
        rows[0]["milestones"] = [{"at": "2026-10", "label": "節目"}]
        geo = se.layout_schedule(_sched(rows), CHART)
        self.assertNotIn("chart-overflow", [d["code"] for d in geo["diagnostics"]])
        rg = geo["region"]
        self.assertLessEqual(geo["rows"][-1]["y"] + geo["rows"][-1]["h"], rg["y"] + rg["h"] + 0.5)

    def test_milestone_and_after_label_get_a_ground_fill(self):
        s = _sched([{"label": "A", "milestones": [{"at": "2026-10", "label": "節目"}],
                     "bars": [{"start": "2026-09", "end": "2026-10", "label": LONG}]}], autofit=False)     # S4: 行が少ないと文字を大きくする（schedule の thin_grow）ので、ここは止めて従来の寸法で見る
        _, html, _ = build_html([s])
        for text in ("節目", LONG):
            m = re.search(r'<div style="[^"]*background:#[0-9A-Fa-f]{6}[^"]*">' + text + "</div>", html)
            self.assertIsNotNone(m, text)


class DefaultsTest(unittest.TestCase):
    def test_sample_diagram_tokens_exist(self):
        d = types_of("sequence")["diagram"]
        self.assertIn("segment_pad_bottom", d)
        h = types_of("house")["body"]
        self.assertTrue(h.get("fit_content"))
        o = types_of("org")["body"]
        self.assertIn("scope_pad", o)
        self.assertIn("left_margin", types_of("matrix")["axis"])
        self.assertIn("io_min_size", types_of("swimlane")["flow"])


if __name__ == "__main__":
    unittest.main()

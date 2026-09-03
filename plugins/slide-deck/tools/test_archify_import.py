#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archify_import.py の単体テスト。

Archify（https://github.com/tt-a1i/archify）の実サンプルファイルには依存せず、5 図種それぞれの
最小 IR（型付き JSON）をこのファイル内に持つ。各図種について
  - 変換結果の type と主要フィールドが期待どおりであること
  - 変換結果が本プラグインの検証（validate_grid_diagram / layout_sequence /
    build_deck._validate_swimlane）を error なしで通ること
を確認する。architecture の座標クラスタリング（pos/size → row/col の量子化）は
専用のテストクラスで単体検証する。
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import archify_import as ai  # noqa: E402


class _Args:
    """archify_import.convert() が参照する argparse.Namespace の最小代替。"""

    def __init__(self, eyebrow=None, tolerance=ai.DEFAULT_TOLERANCE):
        self.eyebrow = eyebrow
        self.tolerance = tolerance


def _convert(ir: dict, **kwargs):
    notes: list = []
    slide = ai.convert(ir, _Args(**kwargs), notes)
    return slide, notes


def _validate_ok(slide: dict) -> bool:
    """validate_slide() を stderr を握りつぶして呼び、error が無ければ True を返す。"""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        return ai.validate_slide(slide, None)


# ---------------------------------------------------------------------------
# architecture
# ---------------------------------------------------------------------------

class ArchitectureConversionTest(unittest.TestCase):
    IR = {
        "schema_version": 1, "diagram_type": "architecture",
        "meta": {"title": "Sample Web App"},
        "components": [
            {"id": "users", "type": "external", "label": "Users", "pos": [40, 300], "size": [120, 60]},
            {"id": "cdn", "type": "cloud", "label": "CDN", "pos": [250, 300], "size": [130, 60]},
            {"id": "api", "type": "backend", "label": "API", "pos": [670, 300], "size": [130, 60]},
        ],
        "boundaries": [{"kind": "region", "label": "AWS", "wraps": ["cdn", "api"]}],
        "connections": [
            {"id": "c1", "from": "users", "to": "cdn", "label": "HTTPS", "variant": "emphasis"},
            {"id": "c2", "from": "cdn", "to": "api", "via": [[1, 2]]},
        ],
        "cards": [{"dot": "cyan", "title": "Edge", "items": ["a", "b"]}],
    }

    def test_basic_fields(self):
        slide, notes = _convert(self.IR)
        self.assertEqual(slide["type"], "architecture")
        self.assertEqual(slide["title"], "Sample Web App")
        by_id = {n["id"]: n for n in slide["nodes"]}
        self.assertEqual(set(by_id), {"users", "cdn", "api"})
        for n in by_id.values():
            self.assertIsInstance(n["row"], int)
            self.assertIsInstance(n["col"], int)
        self.assertEqual(slide["groups"][0]["kind"], "region")
        self.assertEqual(slide["groups"][0]["nodes"], ["cdn", "api"])
        by_pair = {(e["from"], e["to"]): e for e in slide["edges"]}
        self.assertEqual(by_pair[("users", "cdn")]["variant"], "emphasis")
        self.assertNotIn("via", by_pair[("cdn", "api")])
        self.assertIn("■Edge: a / b", slide["notes"])
        self.assertTrue(any("via" in n for n in notes))

    def test_validates_clean(self):
        slide, _ = _convert(self.IR)
        self.assertTrue(_validate_ok(slide))

    def test_unsupported_diagram_type_fails(self):
        with self.assertRaises(SystemExit):
            _convert({"diagram_type": "flowchart", "meta": {"title": "x"}})


class ClusteringTest(unittest.TestCase):
    """architecture の座標量子化（cluster_1d / quantize_positions）の単体テスト。"""

    def test_cluster_1d_groups_close_values(self):
        idx = ai.cluster_1d([("a", 100), ("b", 105), ("c", 400)], tolerance=70)
        self.assertEqual(idx["a"], idx["b"])
        self.assertNotEqual(idx["a"], idx["c"])
        self.assertEqual(idx["a"], 0)
        self.assertEqual(idx["c"], 1)

    def test_cluster_1d_is_chained_single_linkage(self):
        # a-b, b-c はそれぞれ 60px（tolerance 未満）だが a-c は 120px（tolerance 超）。
        # チェイン式クラスタリングなので a/b/c は同じクラスタになる。
        idx = ai.cluster_1d([("a", 0), ("b", 60), ("c", 120)], tolerance=70)
        self.assertEqual(len({idx["a"], idx["b"], idx["c"]}), 1)

    def test_cluster_1d_empty(self):
        self.assertEqual(ai.cluster_1d([], tolerance=70), {})

    def test_quantize_positions_matches_grid_like_web_app_sample(self):
        # Archify の web-app.architecture.json の pos/size から算出した中心座標。
        centers = {
            "users": (100, 330), "auth": (100, 142), "cdn": (315, 330), "lb": (525, 330),
            "api": (735, 330), "cache": (735, 180), "db": (945, 330), "s3": (315, 470),
            "queue": (735, 470), "worker": (945, 470),
        }
        notes: list = []
        positions = ai.quantize_positions(centers, 70.0, notes)
        cells = list(positions.values())
        self.assertEqual(len(cells), len(set(cells)), "同じセルに複数ノードが入ってはいけない")
        self.assertEqual(positions["auth"], (0, 0))
        self.assertEqual(positions["users"], (1, 0))
        self.assertEqual(positions["cache"], (0, 3))
        self.assertEqual(positions["api"], (1, 3))
        self.assertEqual(positions["worker"], (2, 4))
        self.assertEqual(notes, [])  # 衝突なしなので警告メモは出ない

    def test_quantize_positions_resolves_forced_collision(self):
        # tolerance をどれだけ半分にしても離れられない（ほぼ同一座標の）2 ノード。
        centers = {"a": (100, 100), "b": (101, 100)}
        notes: list = []
        positions = ai.quantize_positions(centers, 70.0, notes)
        self.assertNotEqual(positions["a"], positions["b"])
        self.assertTrue(notes and "col" in notes[0])

    def test_quantize_positions_avoids_reserved_cells(self):
        centers = {"a": (100, 100)}
        notes: list = []
        positions = ai.quantize_positions(centers, 70.0, notes, reserved=frozenset({(0, 0)}))
        self.assertNotEqual(positions["a"], (0, 0))


# ---------------------------------------------------------------------------
# workflow → swimlane
# ---------------------------------------------------------------------------

class WorkflowConversionTest(unittest.TestCase):
    IR = {
        "schema_version": 2, "diagram_type": "workflow",
        "meta": {"title": "Agent Tool Call Workflow"},
        "lanes": [{"id": "ui", "label": "User Interface"}, {"id": "agent", "label": "Agent Runtime"}],
        "phases": [{"id": "p1", "label": "Intake", "fromCol": 0, "toCol": 1}],
        "groups": [{"id": "g1", "label": "loop", "lane": "agent", "fromCol": 0, "toCol": 1}],
        "mainPath": ["user", "chat"],
        "nodes": [
            {"id": "user", "lane": "ui", "col": 0, "type": "external", "label": "User", "sublabel": "asks"},
            {"id": "chat", "lane": "ui", "col": 1, "type": "frontend", "label": "Chat Surface"},
        ],
        "edges": [
            {"id": "e1", "from": "user", "to": "chat", "label": "ask", "variant": "dashed", "route": "drop"},
        ],
    }

    def test_basic_fields(self):
        slide, notes = _convert(self.IR)
        self.assertEqual(slide["type"], "swimlane")
        self.assertEqual(slide["legend"], False)
        self.assertEqual(slide["lanes"], [{"name": "User Interface"}, {"name": "Agent Runtime"}])
        self.assertEqual(slide["phases"], ["Intake", ""])
        self.assertEqual(slide["cols"], 2)
        node = next(n for n in slide["nodes"] if n["id"] == "user")
        self.assertEqual(node["shape"], "task")
        self.assertEqual(node["variant"], "onother")
        self.assertEqual(node["text"], "User")
        self.assertNotIn("sublabel", node)
        self.assertNotIn("type", node)
        edge = slide["edges"][0]
        self.assertEqual(edge["variant"], "dashed")
        self.assertEqual(edge["style"], "dashed")
        self.assertNotIn("route", edge)
        self.assertTrue(any("groups" in n for n in notes))
        self.assertTrue(any("mainPath" in n for n in notes))

    def test_unknown_lane_falls_back_to_zero(self):
        ir = {
            "diagram_type": "workflow", "meta": {"title": "t"},
            "lanes": [{"id": "a", "label": "A"}],
            "nodes": [{"id": "n1", "lane": "missing", "col": 0, "type": "backend", "label": "N1"}],
            "edges": [],
        }
        slide, notes = _convert(ir)
        self.assertEqual(slide["nodes"][0]["lane"], 0)
        self.assertTrue(any("missing" in n for n in notes))

    def test_validates_clean(self):
        slide, _ = _convert(self.IR)
        self.assertTrue(_validate_ok(slide))


# ---------------------------------------------------------------------------
# dataflow
# ---------------------------------------------------------------------------

class DataflowConversionTest(unittest.TestCase):
    IR = {
        "schema_version": 1, "diagram_type": "dataflow",
        "meta": {"title": "Product Analytics Data Flow"},
        "stages": [{"label": "Sources"}, {"label": "Ingest"}],
        "nodes": [
            {"id": "web", "type": "frontend", "label": "Web App", "sublabel": "browser SDK", "stage": 0, "row": 0},
            {"id": "edge", "type": "cloud", "label": "Edge API", "stage": 1, "row": 0},
        ],
        "flows": [
            {"id": "f1", "from": "web", "to": "edge", "label": "clickstream",
             "classification": "user events", "via": [[1, 2]]},
        ],
    }

    def test_basic_fields(self):
        slide, _notes = _convert(self.IR)
        self.assertEqual(slide["type"], "dataflow")
        self.assertEqual(slide["stages"], ["Sources", "Ingest"])
        node = next(n for n in slide["nodes"] if n["id"] == "web")
        self.assertEqual(node["col"], 0)
        self.assertEqual(node["row"], 0)
        self.assertEqual(node["sublabel"], "browser SDK")
        edge = slide["edges"][0]
        self.assertEqual(edge["classification"], "user events")
        self.assertNotIn("via", edge)

    def test_validates_clean(self):
        slide, _ = _convert(self.IR)
        self.assertTrue(_validate_ok(slide))


# ---------------------------------------------------------------------------
# sequence
# ---------------------------------------------------------------------------

class SequenceConversionTest(unittest.TestCase):
    IR = {
        "schema_version": 1, "diagram_type": "sequence",
        "meta": {"title": "Cache Miss Request Sequence"},
        "participants": [
            {"id": "user", "type": "external", "label": "User"},
            {"id": "web", "type": "frontend", "label": "Web App"},
            {"id": "api", "type": "backend", "label": "API"},
        ],
        "segments": [{"from": 150, "to": 250, "label": "Request"}],
        "messages": [
            {"id": "m2", "from": "web", "to": "api", "y": 250, "label": "GET /dashboard"},
            {"id": "m1", "from": "user", "to": "web", "y": 180, "label": "open page"},
            {"id": "m3", "from": "api", "to": "web", "y": 300, "label": "200 JSON", "variant": "return"},
        ],
        "activations": [{"participant": "web", "from": 180, "to": 300, "type": "frontend"}],
    }

    def test_messages_sorted_by_y_and_y_dropped(self):
        slide, notes = _convert(self.IR)
        self.assertEqual(slide["type"], "sequence")
        self.assertEqual([m["id"] for m in slide["messages"]], ["m1", "m2", "m3"])
        for m in slide["messages"]:
            self.assertNotIn("y", m)
        self.assertTrue(any("y 座標" in n for n in notes))

    def test_activation_and_segment_become_index_ranges(self):
        slide, _ = _convert(self.IR)
        act = slide["activations"][0]
        self.assertEqual((act["from"], act["to"]), (0, 2))
        seg = slide["segments"][0]
        self.assertEqual((seg["from"], seg["to"]), (0, 1))

    def test_validates_clean(self):
        slide, _ = _convert(self.IR)
        self.assertTrue(_validate_ok(slide))


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------

class LifecycleConversionTest(unittest.TestCase):
    IR = {
        "schema_version": 1, "diagram_type": "lifecycle",
        "meta": {"title": "Agent Run Lifecycle"},
        "lanes": [{"id": "main", "label": "Lifecycle phases"}, {"id": "waiting", "label": "Interruptions"}],
        "states": [
            {"id": "queued", "type": "start", "label": "Queued", "lane": "main", "col": 0,
             "step": "01", "yOffset": 10},
            {"id": "approval", "type": "waiting", "label": "Needs Approval", "lane": "waiting", "col": 0},
        ],
        "transitions": [
            {"id": "t1", "from": "queued", "to": "approval", "variant": "security", "via": [[1, 2]]},
        ],
    }

    def test_basic_fields(self):
        slide, _notes = _convert(self.IR)
        self.assertEqual(slide["type"], "lifecycle")
        self.assertEqual(slide["lanes"], [{"name": "Lifecycle phases"}, {"name": "Interruptions"}])
        queued = next(s for s in slide["states"] if s["id"] == "queued")
        self.assertEqual(queued["kind"], "start")
        self.assertEqual(queued["lane"], 0)
        self.assertEqual(queued["step"], "01")
        self.assertNotIn("yOffset", queued)
        approval = next(s for s in slide["states"] if s["id"] == "approval")
        self.assertEqual(approval["lane"], 1)
        trans = slide["transitions"][0]
        self.assertEqual(trans["variant"], "security")
        self.assertNotIn("via", trans)

    def test_validates_clean(self):
        slide, _ = _convert(self.IR)
        self.assertTrue(_validate_ok(slide))


if __name__ == "__main__":
    unittest.main()

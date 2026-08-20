#!/usr/bin/env python3
"""複数採点者の findings-v2 JSON を集約する（docs/ai-eng-series-rubric-v2.md の採点方式）。

- 採点者ごとの項目スコア = 100 − Σ(大20・中5・小1)、下限0
- 項目スコア = 採点者の中央値。spread = 最大−最小（≥25 は「採点者が割れた」）
- findings は和集合。同一 (item, where) で claim の語の重なりが大きいものは統合し、重大度は多数決（同数なら重い方）
- 合格 = 全項目 ≥ target（既定80）

使い方: python3 tools/aggregate_findings.py g1.json g2.json g3.json --out merged.json [--target 80] [--items 9]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from pathlib import Path

W = {"大": 20, "中": 5, "小": 1, "high": 20, "mid": 5, "low": 1}
RANK = {"大": 3, "中": 2, "小": 1}


def norm_sev(s):
    return {"high": "大", "mid": "中", "low": "小"}.get(s, s)


def tokens(s):
    return set(re.findall(r"[一-龥ぁ-んァ-ヶA-Za-z0-9]{2,}", s or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=80)
    ap.add_argument("--items", type=int, default=9)
    args = ap.parse_args()
    graders = []
    for f in args.files:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {f}: {e}")
            continue
        d["_file"] = f
        graders.append(d)
    per = {}  # grader -> item -> score
    for g in graders:
        name = g.get("grader") or Path(g["_file"]).stem
        sc = {i: 100 for i in range(1, args.items + 1)}
        for fd in g.get("findings", []):
            try:
                it = int(fd.get("item"))
            except Exception:
                continue
            if it in sc:
                sc[it] = max(0, sc[it] - W.get(fd.get("severity"), 5))
        per[name] = sc
    items = {}
    for i in range(1, args.items + 1):
        vals = [per[g][i] for g in per]
        items[i] = {"median": int(st.median(vals)) if vals else None, "min": min(vals) if vals else None,
                    "max": max(vals) if vals else None, "spread": (max(vals) - min(vals)) if vals else None,
                    "by_grader": {g: per[g][i] for g in per}}
    # findings merge
    merged = []
    for g in graders:
        gname = g.get("grader") or Path(g["_file"]).stem
        for fd in g.get("findings", []):
            fd = dict(fd)
            fd["severity"] = norm_sev(fd.get("severity"))
            fd["graders"] = [gname]
            hit = None
            for m in merged:
                if m.get("item") == fd.get("item") and str(m.get("where")) == str(fd.get("where")):
                    a, b = tokens(m.get("claim")), tokens(fd.get("claim"))
                    if a and b and (len(a & b) / min(len(a), len(b)) >= 0.3 or (m.get("severity") == fd.get("severity") == "大")):
                        hit = m
                        break
            if hit:
                hit["graders"].append(gname)
                hit.setdefault("sev_votes", [hit["severity"]]).append(fd["severity"])
                votes = hit["sev_votes"]
                best = max(set(votes), key=lambda s: (votes.count(s), RANK.get(s, 0)))
                hit["severity"] = best
                if len(fd.get("fix_hint", "")) > len(hit.get("fix_hint", "")):
                    hit["fix_hint"] = fd.get("fix_hint")
            else:
                merged.append(fd)
    merged.sort(key=lambda x: (-RANK.get(x["severity"], 0), x.get("item", 0), str(x.get("where"))))
    for k, m in enumerate(merged, 1):
        m["id"] = f"m{k}"
        m["agree"] = len(set(m["graders"]))
    unmet = [i for i in items if items[i]["median"] is not None and items[i]["median"] < args.target]
    split = [i for i in items if items[i]["spread"] is not None and items[i]["spread"] >= 25]
    out = {"schema": "aggregate-v2", "graders": list(per), "items": items, "unmet": unmet, "split_items": split,
           "pass": not unmet, "findings": merged,
           "probe": [g.get("probe") for g in graders]}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"採点者{len(per)}名 | 項目別中央値: " + " / ".join(f"{i}:{items[i]['median']}" for i in items)
          + f" | 未達{unmet} | 割れた項目{split} | findings 統合後{len(merged)}件 "
          f"(大{sum(1 for m in merged if m['severity']=='大')}・中{sum(1 for m in merged if m['severity']=='中')}・小{sum(1 for m in merged if m['severity']=='小')})"
          + (" → 合格" if not unmet else " → 不合格"))
    for g in per:
        print(f"  {g}: " + " ".join(str(per[g][i]) for i in range(1, args.items + 1)))


if __name__ == "__main__":
    main()

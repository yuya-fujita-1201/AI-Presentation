#!/bin/bash
# stuck復帰の唯一の手段（state.json手編集禁止）
# usage: reset-phase.sh <phase> [--accept]
#   <phase>: 戻し先 (research_scan|research_fetch|research_ledger|research_web|web_ledger|
#            knowledge|grade_k|improve_k|draft|deck|grade_d|improve_d|brief)
#   --accept: 8点未達のまま先へ進める明示フラグ（manual_override記録）
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/bin:/bin"
cd "$(dirname "$0")/../.." || exit 1
PHASE="${1:?usage: reset-phase.sh <phase> [--accept]}"
ACCEPT="${2:-}"
/opt/homebrew/bin/python3 - "$PHASE" "$ACCEPT" <<'PYEOF'
import json, sys, datetime
phase, accept = sys.argv[1], sys.argv[2]
valid = ["research_scan","research_fetch","research_ledger","research_web","web_ledger",
         "knowledge","grade_k","improve_k","draft","deck","grade_d","improve_d","brief","done"]
assert phase in valid, f"不正なphase: {phase}"
f = "pipeline/state/state.json"
s = json.load(open(f))
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
s["manual_reset"] = {"at": now, "from": s["phase"], "to": phase,
                     "was_stuck": (s.get("stuck") or {}).get("reason")}
s["phase"] = phase
s["stuck"] = None
s["stuck_notified_at"] = None
s["phase_attempts"] = 0
s["phase_started_at"] = None
s["consecutive_external"] = 0
s["generation"] = s.get("generation", 1) + 1
# 人間介入後の採点フェーズは改善ループを新規に開始する（repair/streakをリセット）
if phase in ("grade_k", "improve_k"):
    s["grade"]["knowledge"].update({"repair_count": 0, "pass_streak": 0, "retry_used": False, "last_unmet": None, "last_scores": None})
if phase in ("grade_d", "improve_d"):
    s["grade"]["deck"].update({"repair_count": 0, "pass_streak": 0, "retry_used": False, "last_unmet": None, "last_scores": None})
if accept == "--accept":
    s["manual_override"] = True
json.dump(s, open(f, "w"), ensure_ascii=False, indent=2)
print(f"reset: {s['manual_reset']['from']} -> {phase} (generation {s['generation']})")
PYEOF
echo "[$(date '+%m-%d %H:%M')] 🔧 手動リセット → $PHASE $ACCEPT" >> pipeline/logs/activity.log

#!/bin/bash
# デッキ機械ゲート。失敗種別ごとの個別exit code:
#   10=build失敗 11=PPTX破損(unzip) 12=再パース失敗 13=枚数不一致 14=notes_slide混入 15=preview不一致
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/bin:/bin"
DECK_DIR="${1:?usage: gate_deck.sh <deck_dir>}"
cd "$(dirname "$0")/../.." || exit 1
PY=/opt/homebrew/bin/python3

$PY tools/build_deck.py "$DECK_DIR" || exit 10
# 生成物名はフォルダ名ではなく、build_deck.py と同じ meta.id 契約で決める。
# これにより、表示順プレフィックス付きのフォルダ名でもゲートを実行できる。
ARTIFACT_ID=$($PY - "$DECK_DIR/deck.json" <<'PYEOF'
import json
import sys
from pathlib import Path

deck_path = Path(sys.argv[1])
with deck_path.open(encoding="utf-8") as handle:
    deck = json.load(handle)
print(deck.get("meta", {}).get("id") or deck_path.parent.name)
PYEOF
) || exit 10
PPTX="$DECK_DIR/build/$ARTIFACT_ID.pptx"
[ -f "$PPTX" ] || { echo "pptx not found: $PPTX"; exit 10; }
unzip -t "$PPTX" >/dev/null 2>&1 || exit 11

$PY - "$PPTX" "$DECK_DIR/deck.json" <<'PYEOF'
import json, sys
from pptx import Presentation
try:
    prs = Presentation(sys.argv[1])
except Exception as e:
    print("reparse fail:", e); sys.exit(12)
n_json = len(json.load(open(sys.argv[2]))["slides"])
if len(prs.slides) != n_json:
    print(f"slide count mismatch pptx={len(prs.slides)} json={n_json}"); sys.exit(13)
for i, s in enumerate(prs.slides, 1):
    if s.has_notes_slide:
        print(f"notes_slide detected at slide {i}"); sys.exit(14)
sys.exit(0)
PYEOF
rc=$?; [ $rc -ne 0 ] && exit $rc

# preview全枚生成→枚数一致（旧版の残骸PNGを先に掃除して偽の枚数不一致を防ぐ）
rm -f "$DECK_DIR"/build/preview/slide-*.png
$PY tools/preview_deck.py "$DECK_DIR" >/dev/null || exit 15
N_JSON=$($PY -c "import json,sys;print(len(json.load(open('$DECK_DIR/deck.json'))['slides']))")
N_PNG=$(ls "$DECK_DIR"/build/preview/slide-*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$N_PNG" != "$N_JSON" ]; then
  echo "preview count mismatch png=$N_PNG json=$N_JSON"; exit 15
fi
echo "gate_deck OK: $N_JSON slides"
exit 0

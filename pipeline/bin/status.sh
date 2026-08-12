#!/bin/bash
# 現在地と最近の活動を表示（進捗確認用）。 tail -f pipeline/logs/activity.log でライブ監視も可
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "$(dirname "$0")/../.." || exit 1
exec /opt/homebrew/bin/python3 pipeline/bin/pipelib.py status

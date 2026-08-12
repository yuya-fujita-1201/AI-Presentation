#!/bin/bash
# Pushover通知（既存 ~/scripts/notify-phone.sh へ委譲。不在ならログのみ・非致命）
TITLE="${1:-pipeline}"
BODY="${2:-}"
LOG="$(dirname "$0")/../logs/notify.log"
mkdir -p "$(dirname "$LOG")"
echo "[$(date '+%m-%d %H:%M')] $TITLE | $BODY" >> "$LOG"
if [ -x "$HOME/scripts/notify-phone.sh" ]; then
  "$HOME/scripts/notify-phone.sh" "$TITLE" "$BODY"
  exit $?
fi
exit 0

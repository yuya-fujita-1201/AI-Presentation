#!/bin/bash
# launchd入口。工程選択・state・git操作はすべて pipelib.py 側（LLMは関与しない）
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$(dirname "$0")/../.." || exit 1
if [ "${1:-}" = "--healthcheck" ]; then
  exec /opt/homebrew/bin/python3 pipeline/bin/pipelib.py healthcheck
fi
exec /opt/homebrew/bin/python3 pipeline/bin/pipelib.py cycle

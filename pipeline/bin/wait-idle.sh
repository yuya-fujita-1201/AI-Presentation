#!/bin/bash
# 手修正の前に実行: ロック解放（実行中ランの終了）を待つ
LOCK="$(dirname "$0")/../lock/run.lock"
echo "ロック解放を待機中... (PAUSE設置済みであること)"
while [ -d "$LOCK" ]; do
  sleep 5
done
echo "アイドル状態。編集を開始できます"

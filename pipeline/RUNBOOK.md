# pipeline RUNBOOK — 運用手順書

自律パイプラインの人間向け操作手順。設計全体は `docs/auto-pipeline-proposal.md`、討議記録は `docs/tmax-council-log-2026-08-12.md`。

## 日常の見方

```bash
pipeline/bin/status.sh                  # 現在地・queue・最近の活動
tail -f pipeline/logs/activity.log      # ライブ監視（1ラン1行の日本語ログ）
tail -f pipeline/logs/launchd.log       # launchd生ログ
cat pipeline/logs/usage.jsonl | tail    # ラン別コスト記録
```

- 各ランの詳細: `pipeline/logs/run-<runid>.log`（LLM側の記録は `run-<runid>.md`）
- LLMに渡した指示全文: `pipeline/logs/prompt-<runid>.md`
- ゲート実行結果: `pipeline/logs/gates/`／採点レポート: `pipeline/logs/grades/`

## 一時停止 / 再開

```bash
touch pipeline/PAUSE     # 以後のスロットは何もしない
rm pipeline/PAUSE        # 再開
```

## 手動で1サイクル回す

```bash
bash pipeline/bin/run-cycle.sh
# または即時トリガ:
launchctl kickstart gui/501/com.yuyafujita.presentation-pipeline
```

## stuckからの復帰（state.json手編集禁止）

Pushoverに `pipeline STUCK: <理由>` が来たら:

1. `pipeline/bin/status.sh` と該当 `pipeline/logs/grades/` や `run-*.log` を読む
2. 必要な手修正があれば: `touch pipeline/PAUSE` → `pipeline/bin/wait-idle.sh` → 編集
3. `pipeline/bin/reset-phase.sh <戻し先phase>` で再開（例: `reset-phase.sh knowledge`）
   - 8点未達のまま先へ進める場合のみ `reset-phase.sh <次phase> --accept`（manual_override記録）
4. `rm pipeline/PAUSE`

## ロールバック（6手順）

```bash
touch pipeline/PAUSE
git log --oneline -15            # auto(pe/<phase>): 形式で対象を特定
git revert --no-edit <sha>       # 範囲なら <old>..<new>
pipeline/bin/reset-phase.sh <戻し先phase>
git push origin main
rm pipeline/PAUSE
```

## launchd 管理

```bash
# インストール（初回）
cp pipeline/launchd/*.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuyafujita.presentation-pipeline.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuyafujita.presentation-healthcheck.plist

# 更新（plist変更時）
launchctl bootout gui/501/com.yuyafujita.presentation-pipeline
cp pipeline/launchd/com.yuyafujita.presentation-pipeline.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuyafujita.presentation-pipeline.plist

# 停止（完全撤去）
launchctl bootout gui/501/com.yuyafujita.presentation-pipeline
launchctl bootout gui/501/com.yuyafujita.presentation-healthcheck
```

スロット（計14/日）: **夜間は毎時** 23:45 / 00:45 / 01:45 / 02:45 / 03:45 / 04:45（人が寝ていてリソース競合がない主戦場）、**日中は2.5時間おき** 05:15 / 07:45 / 10:15 / 12:45 / 15:15 / 17:45 / 20:15 / 22:45（対話作業を優先）。スリープ中のスロットは復帰時に1回まとめて遅延実行。healthcheckは毎朝07:17。

## トラブル対応

- **stale_lock通知**: 実行中プロセスの残骸。`ps aux | grep claude` で本当に死んでいるか確認してから `rm -rf pipeline/lock/run.lock`（自動削除はしない設計）
- **YouTube bot検知 / yt-dlp故障**: `brew upgrade yt-dlp`（自動更新はしない設計）
- **push rejected**: リモートと分岐。無人rebaseはしないので、人が `git pull --rebase` → `git push`
- **rate_limited退避が続く**: 対話作業を優先する設計どおり。枠が回復すれば次スロットで自然再開
- **動画URLを直接指定したい**: `pipeline/watchlist.yaml` の `adhoc_videos:` に `- {url: "...", note: "..."}` を追記（次のscanで採点免除・直接fetch）
- **チャンネル追加**: `pipeline/watchlist.yaml` の `channels:` に追記（trust: official/expert/curated/unknown。unknownは項番 no を振る）

## v1実装の既知の簡略化（評議会設計との差分）

- run隔離は「使い捨てworktree」でなく**allowlist事後検査＋違反の自動復元/隔離**（staging/quarantine/）で実装
- grade_dの**アンカー検定はfixture未整備のためスキップ**（確認採点2連続all≥8は実装済み）
- 日次ドル予算ゲートは**ユーザー判断で廃止**（サブスク内・実行回数capとwatchdogで制御）
- 専用macOSユーザー化は未実施（9月以降の強化課題）

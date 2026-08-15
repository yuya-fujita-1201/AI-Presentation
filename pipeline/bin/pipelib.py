#!/usr/bin/env python3
"""presentation 自律パイプライン中枢。

設計原則（T-MAX評議会 2026-08-12 / docs/auto-pipeline-proposal.md）:
- LLMは工程選択・state更新・git操作に関与しない。「LLMは事実、ラッパーが裁定」
- state.json を書くのは本モジュールのみ。LLMは outbox に報告を書くだけ
- 遷移条件は機械ゲートの実行結果のみ。LLMの「通りました」報告は信用しない
- 迷ったら何も書き換えず記録して終了（blocked は正しい動作）
"""
import argparse
import datetime
import fnmatch
import glob as globmod
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIPE = os.path.join(ROOT, "pipeline")
BIN = os.path.join(PIPE, "bin")
LOGS = os.path.join(PIPE, "logs")
CACHE = os.path.join(PIPE, "cache")
STAGING = os.path.join(PIPE, "staging")
STATE_DIR = os.path.join(PIPE, "state")
OUTBOX = os.path.join(STATE_DIR, "outbox")
LOCK = os.path.join(PIPE, "lock", "run.lock")
PAUSE = os.path.join(PIPE, "PAUSE")
STATE_F = os.path.join(STATE_DIR, "state.json")
QUEUE_F = os.path.join(STATE_DIR, "research-queue.json")
CONFIG_F = os.path.join(PIPE, "config.json")
MONITOR_DIR = os.path.expanduser("~/.pipeline-monitor")

CFG = json.load(open(CONFIG_F))

RW_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit"]
TOOLMAP = {
    # phase: (tools, disallowed)  — 相互排他原則: 外部生テキストを読むランにBash/Web系を与えない
    "research_scan": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "research_fetch": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "research_ledger": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "research_web": (RW_TOOLS + ["WebSearch", "WebFetch"], ["Bash"]),
    "web_ledger": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "knowledge": (RW_TOOLS + ["Bash"], ["WebSearch", "WebFetch"]),
    "grade_k": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "improve_k": (RW_TOOLS + ["Bash"], ["WebSearch", "WebFetch"]),
    "draft": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "deck": (RW_TOOLS + ["Bash"], ["WebSearch", "WebFetch"]),
    "grade_d": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
    "improve_d": (RW_TOOLS + ["Bash"], ["WebSearch", "WebFetch"]),
    "brief": (RW_TOOLS, ["Bash", "WebSearch", "WebFetch"]),
}

GRADE_ITEMS = {"grade_k": 5, "grade_d": 6}


# ---------------------------------------------------------------- util

def now():
    return datetime.datetime.now().astimezone()


def now_iso():
    return now().isoformat(timespec="seconds")


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def sh(args, timeout=120, cwd=ROOT, input_text=None):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, input=input_text)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa
        return 125, "", str(e)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs():
    for d in [LOGS, os.path.join(LOGS, "gates"), os.path.join(LOGS, "grades"),
              CACHE, os.path.join(CACHE, "subs"), os.path.join(CACHE, "web"),
              STAGING, OUTBOX, os.path.dirname(LOCK), MONITOR_DIR]:
        os.makedirs(d, exist_ok=True)


def log_activity(msg):
    line = f"[{now().strftime('%m-%d %H:%M')}] {msg}"
    with open(os.path.join(LOGS, "activity.log"), "a") as f:
        f.write(line + "\n")
    print(line)


def run_log(runid, text):
    with open(os.path.join(LOGS, f"run-{runid}.log"), "a") as f:
        f.write(f"[{now_iso()}] {text}\n")


def notify(state, title, body):
    rc, _, _ = sh([os.path.join(BIN, "notify.sh"), title, body], timeout=30)
    if rc != 0:
        state["notify_failed_count"] = state.get("notify_failed_count", 0) + 1
    else:
        state["last_notification_success_at"] = now_iso()
    return rc == 0


def load_state():
    return read_json(STATE_F)


def save_state(state):
    write_json_atomic(STATE_F, state)


def load_queue():
    return read_json(QUEUE_F)


def save_queue(q):
    write_json_atomic(QUEUE_F, q)


def load_theme(state):
    tid = state["theme"]["id"]
    with open(os.path.join(PIPE, "themes", f"{tid}.yaml")) as f:
        return yaml.safe_load(f)


def load_watchlist():
    with open(os.path.join(PIPE, "watchlist.yaml")) as f:
        return yaml.safe_load(f)


def scope_of(theme_id):
    return CFG.get("theme_scope", {}).get(theme_id, "full")


def advance_theme(state, queue, note):
    """テーマ完了時の遷移。次テーマがあればstate/queueを初期化して自走継続、無ければ完走PAUSE"""
    series = state["theme"]["series"]
    cur = state["theme"]["id"]
    idx = series.index(cur) if cur in series else -1
    nxt = None
    for cand in series[idx + 1:]:
        if scope_of(cand) != "skip":
            nxt = cand
            break
    if nxt is None:
        state["phase"] = "done"
        with open(PAUSE, "w") as f:
            f.write(f"シリーズ完走により自動一時停止 {now_iso()}\n")
        notify(state, "pipeline: シリーズ完走 🎉", f"{note}。全テーマ完了・PAUSE（体制振り返り待ち）")
        log_activity(f"🏁 シリーズ完走: {note}")
        return
    th = yaml.safe_load(open(os.path.join(PIPE, "themes", f"{nxt}.yaml")))["theme"]
    state["theme"].update({"id": nxt, "slug": th["slug"], "title": th["title"]})
    state["phase"] = "research_scan"
    state["phase_attempts"] = 0
    state["run_counts"] = {}
    state["scan_fallback_done"] = False
    state["video_shortfall"] = False
    state["web_rerun_done"] = False
    state["_use_fallback"] = False
    for k in ("knowledge", "deck"):
        state["grade"][k] = {"iter": 0, "repair_count": 0, "pass_streak": 0,
                             "retry_used": False, "last_unmet": None, "last_scores": None}
    state["generation"] = state.get("generation", 1) + 1
    queue["videos"] = []
    queue["web"] = {"subtopics_done": [], "candidates": []}
    for f_ in (os.path.join(STAGING, "knowledge", "plan.json"),
               os.path.join(STAGING, "draft", "draft.md")):
        try:
            os.remove(f_)
        except FileNotFoundError:
            pass
    notify(state, "pipeline: 次テーマへ", f"{note} → {th['title']}（{nxt}）のresearch開始")
    log_activity(f"🎯 テーマ遷移: {cur} → {nxt}（scope: {scope_of(nxt)}）")


def set_stuck(state, reason, note=""):
    state["stuck"] = {"reason": reason, "at": now_iso(), "note": note[:500]}
    ok = notify(state, f"pipeline STUCK: {reason}",
                f"theme={state['theme']['id']} phase={state['phase']}\n{note[:600]}\n復帰: pipeline/bin/reset-phase.sh")
    if ok:
        state["stuck_notified_at"] = now_iso()
    log_activity(f"🛑 STUCK({reason}) phase={state['phase']} {note[:120]}")


# ---------------------------------------------------------------- lock

_hb_stop = threading.Event()


def _lstart(pid):
    rc, out, _ = sh(["ps", "-p", str(pid), "-o", "lstart="], timeout=10)
    return out.strip() if rc == 0 else ""


def acquire_lock(runid, state):
    meta_f = os.path.join(LOCK, "meta.json")
    try:
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        os.mkdir(LOCK)
    except FileExistsError:
        meta = read_json(meta_f, {})
        hb = meta.get("heartbeat", 0)
        pid = meta.get("pid")
        stale = (time.time() - hb > 180) and (not pid or _lstart(pid) != meta.get("lstart", "X"))
        if stale:
            if not (state.get("stuck") and state["stuck"].get("reason") == "stale_lock"):
                set_stuck(state, "stale_lock", f"lock残骸: pid={pid} hb_age={int(time.time()-hb)}s。自動削除しない。人が確認後 rm -rf pipeline/lock/run.lock")
                save_state(state)
        else:
            log_activity("⏭ 他ランが実行中のためスキップ")
        return False
    meta = {"pid": os.getpid(), "pgid": os.getpgid(0), "run_id": runid,
            "started_at": now_iso(), "lstart": _lstart(os.getpid()),
            "heartbeat": time.time()}
    write_json_atomic(meta_f, meta)

    def hb_loop():
        while not _hb_stop.wait(60):
            m = read_json(meta_f, meta)
            m["heartbeat"] = time.time()
            write_json_atomic(meta_f, m)

    threading.Thread(target=hb_loop, daemon=True).start()
    return True


def release_lock():
    _hb_stop.set()
    shutil.rmtree(LOCK, ignore_errors=True)


# ---------------------------------------------------------------- render / prompt

def render(text, variables):
    for k, v in variables.items():
        v = str(v)
        if "\n" in v or "{{" in v:
            raise ValueError(f"scalar violation for {{{{{k}}}}}")
        text = text.replace("{{%s}}" % k, v)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if left:
        raise ValueError(f"unresolved template vars: {left[:5]}")
    return text


def build_prompt(phase, runid, variables):
    common = open(os.path.join(PIPE, "prompts", "_common.md")).read()
    body = open(os.path.join(PIPE, "prompts", f"{phase}.md")).read()
    base_vars = {
        "RUN_ID": runid, "PHASE": phase, "TODAY": now().strftime("%Y-%m-%d"),
        "THEME_ID": variables.get("THEME_ID", ""),
        "OUTBOX_PATH": f"pipeline/state/outbox/result-{runid}.json",
        "RUN_LOG_PATH": f"pipeline/logs/run-{runid}.md",
    }
    base_vars.update(variables)
    text = render(common + "\n\n---\n\n" + body, base_vars)
    path = os.path.join(LOGS, f"prompt-{runid}.md")
    with open(path, "w") as f:
        f.write(text)
    return path


# ---------------------------------------------------------------- claude runner

def run_claude(phase, prompt_path, runid):
    cfg_model = CFG["models"][CFG["model_by_phase"][phase]]
    tools, disallowed = TOOLMAP[phase]
    wd = CFG["watchdog_sec"].get(phase, CFG["watchdog_sec"]["default"])
    out_f = os.path.join(LOGS, f"claude-{runid}.json")
    cmd = ["claude", "--model", cfg_model, "-p", "--output-format", "json",
           "--no-session-persistence", "--tools"] + tools + ["--disallowedTools"] + disallowed
    run_log(runid, f"claude start model={cfg_model} phase={phase} watchdog={wd}s")
    with open(prompt_path) as fin, open(out_f, "w") as fout:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdin=fin, stdout=fout,
                                stderr=subprocess.STDOUT, start_new_session=True)
        start = time.time()
        while proc.poll() is None:
            if time.time() - start > wd:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    pass
                time.sleep(30)
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except Exception:
                        pass
                run_log(runid, f"watchdog timeout after {wd}s -> killed")
                return "timeout", None
            time.sleep(10)
    raw = open(out_f).read()
    data = None
    try:
        data = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                data = None
    usage_row = {"at": now_iso(), "run_id": runid, "phase": phase, "model": cfg_model,
                 "exit": proc.returncode, "duration_s": int(time.time() - start)}
    if isinstance(data, dict):
        for k in ("total_cost_usd", "num_turns", "duration_ms", "is_error"):
            if k in data:
                usage_row[k] = data[k]
        if isinstance(data.get("usage"), dict):
            usage_row["output_tokens"] = data["usage"].get("output_tokens")
    with open(os.path.join(LOGS, "usage.jsonl"), "a") as f:
        f.write(json.dumps(usage_row, ensure_ascii=False) + "\n")
    result_text = (data or {}).get("result", "") if isinstance(data, dict) else raw[-2000:]
    if proc.returncode != 0 or (isinstance(data, dict) and data.get("is_error")):
        if re.search(r"rate.?limit|usage limit|overload|429|quota|capacity|out of.*(credit|usage)|limit (will )?reset",
                     str(result_text), re.I):
            run_log(runid, f"rate_limited: {str(result_text)[:200]}")
            return "rate_limited", data
        run_log(runid, f"claude error exit={proc.returncode}: {str(result_text)[:300]}")
        return "error", data
    return "ok", data


# ---------------------------------------------------------------- outbox

def load_outbox(runid, phase):
    path = os.path.join(OUTBOX, f"result-{runid}.json")
    if not os.path.exists(path):
        return None, "outbox未作成"
    o = read_json(path)
    if not isinstance(o, dict):
        return None, "outboxがJSONでない"
    if o.get("schema") != "outbox-v1":
        return None, f"schema不一致: {o.get('schema')}"
    if o.get("run_id") != runid:
        return None, "run_id不一致"
    if o.get("phase") != phase:
        return None, f"phase不一致: {o.get('phase')}"
    if o.get("status") not in ("succeeded", "succeeded_partial", "blocked", "failed"):
        return None, f"status不正: {o.get('status')}"
    if not isinstance(o.get("artifacts", []), list):
        return None, "artifacts不正"
    return o, None


# ---------------------------------------------------------------- allowlist enforcement

def allowlist_for(phase, theme):
    kdir = theme["theme"]["knowledge_dir"]
    ddir = theme["theme"]["deck_dir"]
    table = {
        "research_ledger": ["knowledge/sources/*.md", "knowledge/log.md"],
        "web_ledger": ["knowledge/sources/*.md", "knowledge/log.md"],
        "knowledge": [kdir + "/*", kdir + "/**", "knowledge/sources/*.md",
                      "knowledge/index.md", "knowledge/log.md"],
        "improve_k": [kdir + "/*", kdir + "/**", "knowledge/sources/*.md",
                      "knowledge/index.md", "knowledge/log.md"],
        "deck": [ddir + "/*", ddir + "/**"],
        "improve_d": [ddir + "/*", ddir + "/**"],
        "brief": ["docs/codex-brief-*.md"],
    }
    return table.get(phase, [])


def git_porcelain():
    rc, out, _ = sh(["git", "status", "--porcelain"], timeout=60)
    entries = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        st, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        entries.append((st, path))
    return entries


def enforce_allowlist(phase, runid, theme, pre_entries):
    allowed = allowlist_for(phase, theme)
    always_ok = ["pipeline/state/state.json", "pipeline/state/research-queue.json"]
    # 本流パイプラインの保護領域のみを取り締まる。他レーン（Codexたたき台・人間の並行作業）の
    # 作業中ファイルを巻き戻さない（2026-08-14 02:17 の誤爆=友軍撃ちの再発防止）
    slug = theme["theme"]["slug"]
    protected = ["knowledge/", "pipeline/state/", "tools/", "templates/", "pipeline/prompts/",
                 "rubric-"]
    # デッキ領域を保護するのは本流がデッキを作るテーマ（scope=full）のみ。
    # knowledge-onlyテーマではデッキフォルダは他レーン（ユーザー/Codex）の領土（2026-08-14 13:3x）
    if scope_of(theme["theme"]["id"]) == "full":
        protected += [theme["theme"]["deck_dir"].rstrip("/") + "/", f"docs/codex-brief-{slug}.md"]
    pre_set = {p for _, p in pre_entries}
    violations = []
    for st, path in git_porcelain():
        if path in always_ok:
            continue
        if path.startswith("pipeline/") and not path.startswith("pipeline/state/"):
            continue  # gitignore対象領域（logs/cache/staging/lock）
        if any(fnmatch.fnmatch(path, g) for g in allowed):
            continue
        if path in pre_set:
            continue  # ラン開始前から存在した差分は今回のランの責任でない
        if not any(path.startswith(root) for root in protected):
            run_log(runid, f"対象外レーンの変化を検知（放置）: {st} {path}")
            continue
        violations.append((st, path))
        qdir = os.path.join(STAGING, "quarantine", runid)
        os.makedirs(qdir, exist_ok=True)
        try:
            if st.strip().startswith("??"):
                dest = os.path.join(qdir, path.replace("/", "__"))
                shutil.move(os.path.join(ROOT, path), dest)
            else:
                sh(["git", "checkout", "--", path], timeout=60)
        except Exception as e:  # noqa
            run_log(runid, f"violation restore failed {path}: {e}")
    if violations:
        run_log(runid, f"allowlist違反 {len(violations)}件: {violations[:10]}")
        log_activity(f"⚠️ 許可外書込みを検出・復元 {len(violations)}件 (run {runid})")
    return violations


def revert_paths(paths, runid):
    """ゲート不合格の成果物を取り消す（tracked→checkout / untracked→quarantine）"""
    tracked = set()
    rc, out, _ = sh(["git", "ls-files"], timeout=60)
    if rc == 0:
        tracked = set(out.splitlines())
    qdir = os.path.join(STAGING, "quarantine", runid)
    for p in paths:
        full = os.path.join(ROOT, p)
        if p in tracked:
            sh(["git", "checkout", "--", p], timeout=60)
        elif os.path.exists(full):
            os.makedirs(qdir, exist_ok=True)
            shutil.move(full, os.path.join(qdir, p.replace("/", "__")))


# ---------------------------------------------------------------- gates

def run_gate(name, args, runid, timeout=600):
    rc, out, err = sh(args, timeout=timeout)
    with open(os.path.join(LOGS, "gates", f"{runid}-{name}.log"), "w") as f:
        f.write(f"$ {' '.join(args)}\nexit={rc}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n")
    run_log(runid, f"GATE {name} exit={rc}")
    return rc, out + "\n" + err


def gate_validate_okf(runid):
    return run_gate("validate_okf", ["/opt/homebrew/bin/python3", "tools/validate_okf.py", "knowledge"], runid)


# ---------------------------------------------------------------- git commit/push

def commit_and_push(state, phase, summary, paths, runid):
    add_paths = list(paths) + [STATE_F, QUEUE_F]
    sh(["git", "add", "--"] + add_paths, timeout=60)
    rc, out, _ = sh(["git", "diff", "--cached", "--name-only"], timeout=60)
    if not out.strip():
        run_log(runid, "commit: 変更なし")
        return None
    theme_id = state["theme"]["id"]
    msg = f"auto({theme_id}/{phase}): {summary} [run:{runid}]\n\nCo-Authored-By: pipeline <noreply@local>"
    rc, out, err = sh(["git", "commit", "-m", msg], timeout=60)
    if rc != 0:
        run_log(runid, f"commit失敗: {err[:200]}")
        return None
    rc, out, _ = sh(["git", "rev-parse", "--short", "HEAD"], timeout=30)
    head = out.strip()
    rc, out, err = sh(["git", "push", "origin", "main"], timeout=90)
    if rc != 0:
        if re.search(r"rejected|non-fast-forward", err):
            state["push_pending"] = True
            notify(state, "pipeline: push rejected", "リモートと分岐。無人rebaseはしない。RUNBOOK参照")
        else:
            state["push_pending"] = True
            run_log(runid, f"push失敗(繰越): {err[:200]}")
    else:
        state["push_pending"] = False
    return head


def try_pending_push(state, runid):
    if not state.get("push_pending"):
        return
    rc, out, err = sh(["git", "push", "origin", "main"], timeout=90)
    if rc == 0:
        state["push_pending"] = False
        run_log(runid, "pending push 成功")


# ---------------------------------------------------------------- yt-dlp helpers

YTDLP = "/opt/homebrew/bin/yt-dlp"


def ytdlp_json(args, timeout):
    rc, out, err = sh([YTDLP, "-q", "--no-warnings"] + args, timeout=timeout)
    if "Sign in to confirm" in err:
        return "bot", None, err
    if rc != 0:
        return "err", None, err
    try:
        return "ok", json.loads(out), err
    except Exception:
        objs = []
        for line in out.splitlines():
            try:
                objs.append(json.loads(line))
            except Exception:
                pass
        return ("ok", {"entries": objs}, err) if objs else ("err", None, "json parse fail")


def normalize_vtt(vtt_path, out_path):
    """VTT→重複除去プレーンテキスト＋60秒毎[mm:ss]マーカー"""
    txt = open(vtt_path, encoding="utf-8", errors="replace").read()
    cues = re.split(r"\n\n+", txt)
    lines_out, last_line, last_min = [], None, -1
    for cue in cues:
        m = re.search(r"(\d+):(\d+):(\d+)[.,]\d+\s*-->", cue)
        if not m:
            continue
        secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        body_lines = [re.sub(r"<[^>]+>", "", l).strip() for l in cue.splitlines()
                      if "-->" not in l and not re.match(r"^(WEBVTT|Kind:|Language:|\d+$)", l.strip())]
        for bl in body_lines:
            if not bl or bl == last_line:
                continue
            minute = secs // 60
            if minute != last_min:
                lines_out.append(f"[{minute:02d}:00]")
                last_min = minute
            lines_out.append(bl)
            last_line = bl
    text = "\n".join(lines_out)
    with open(out_path, "w") as f:
        f.write(text)
    return len(text)


# ---------------------------------------------------------------- prework per phase

def theme_vars(theme):
    t = theme["theme"]
    return {"THEME_ID": t["id"], "THEME_SLUG": t["slug"], "THEME_TITLE": t["title"],
            "KNOWLEDGE_DIR": t["knowledge_dir"], "DECK_DIR": t["deck_dir"]}


def runmeta_save(runid, obj):
    write_json_atomic(os.path.join(STAGING, f"runmeta-{runid}.json"), obj)


def runmeta_load(runid):
    return read_json(os.path.join(STAGING, f"runmeta-{runid}.json"), {})


def prework_research_scan(state, queue, theme, runid):
    wl = load_watchlist()
    use_fallback = state.get("scan_fallback_done") is True and False  # fallbackは2回目scan時に使用
    kw_key = "keywords_fallback" if state.get("_use_fallback") else "keywords"
    vocab = [v.lower() for v in theme.get("match_vocab", {}).get("ja", []) +
             theme.get("match_vocab", {}).get("en", [])]
    found = {}
    deadline = time.time() + CFG["watchdog_sec"]["prework"]
    for ch in wl.get("channels", []):
        if time.time() > deadline:
            break
        url = f"https://www.youtube.com/{ch['handle']}/videos"
        st, data, err = ytdlp_json(["-J", "--flat-playlist", "--playlist-items", "1-15", url], 90)
        if st == "bot":
            return {"mode": "abort_external", "note": "YouTube bot検知(scan)"}
        if st != "ok" or not data:
            run_log(runid, f"scan: {ch['handle']} 走査失敗 {err[:100]}")
            continue
        for e in (data.get("entries") or []):
            vid = e.get("id")
            if not vid:
                continue
            found.setdefault(vid, {"id": vid, "title": e.get("title") or "",
                                   "url": f"https://www.youtube.com/watch?v={vid}",
                                   "channel": ch.get("name"), "trust": ch.get("trust", "unknown"),
                                   "view_count": e.get("view_count"), "duration": e.get("duration"),
                                   "src": "watchlist"})
    kws = theme.get(kw_key, {})
    for kw in (kws.get("ja", []) + kws.get("en", []))[:9]:
        if time.time() > deadline:
            break
        st, data, err = ytdlp_json(["-J", "--flat-playlist", f"ytsearch10:{kw}"], 90)
        if st == "bot":
            return {"mode": "abort_external", "note": "YouTube bot検知(search)"}
        if st != "ok" or not data:
            continue
        for e in (data.get("entries") or []):
            vid = e.get("id")
            if not vid or vid in found:
                continue
            found[vid] = {"id": vid, "title": e.get("title") or "",
                          "url": f"https://www.youtube.com/watch?v={vid}",
                          "channel": e.get("channel") or e.get("uploader") or "",
                          "trust": "unknown", "view_count": e.get("view_count"),
                          "duration": e.get("duration"), "src": f"search:{kw}"}
    coarse = [v for v in found.values()
              if any(w in (v["title"] or "").lower() for w in vocab)]
    coarse = coarse[:30]
    filled = []
    for v in coarse:
        if time.time() > deadline:
            break
        st, data, _ = ytdlp_json(["-J", "--no-playlist", v["url"]], 45)
        if st == "bot":
            return {"mode": "abort_external", "note": "YouTube bot検知(meta)"}
        if st == "ok" and data:
            v["view_count"] = data.get("view_count")
            v["published"] = data.get("upload_date")
            v["duration"] = data.get("duration")
            v["channel_id"] = data.get("channel_id")
            v["channel"] = v["channel"] or data.get("channel")
            if data.get("upload_date"):
                try:
                    d = datetime.datetime.strptime(data["upload_date"], "%Y%m%d")
                    v["days_old"] = (datetime.datetime.now() - d).days
                except Exception:
                    v["days_old"] = None
        filled.append(v)
    filled = [v for v in filled if v.get("days_old") is None or v["days_old"] <= CFG["scan_recent_days"] * 2]
    if not filled:
        return {"mode": "noop_fail", "note": "scan候補0件（走査失敗の可能性）"}
    sdir = os.path.join(STAGING, f"scan-{runid}")
    os.makedirs(sdir, exist_ok=True)
    cand_f = os.path.join(sdir, "candidates.json")
    write_json_atomic(cand_f, {"candidates": filled,
                               "required_concepts": theme.get("required_concepts", []),
                               "match_vocab": theme.get("match_vocab"),
                               "beginner_vocab": theme.get("beginner_vocab")})
    runmeta_save(runid, {"candidates_file": cand_f, "n_candidates": len(filled)})
    v = theme_vars(theme)
    v.update({"CANDIDATES_FILE": os.path.relpath(cand_f, ROOT),
              "N_CANDIDATES": len(filled),
              "TARGET_SELECT": CFG["research_targets"]["videos_selected_target"]})
    return {"mode": "llm", "vars": v}


def apply_research_scan(state, queue, theme, runid, outbox):
    data = (outbox.get("metrics") or {}).get("data") or outbox.get("data") or {}
    scored = data.get("scored")
    if not isinstance(scored, list) or not scored:
        return False, "outboxにscored配列がない"
    cands = {c["id"]: c for c in read_json(runmeta_load(runid).get("candidates_file"), {}).get("candidates", [])}
    trust_rank = {"official": 3, "expert": 2, "curated": 1, "unknown": 0}
    rows = []
    for s in scored:
        c = cands.get(s.get("id"))
        if not c:
            continue
        try:
            sc = int(s.get("score", -1))
        except Exception:
            continue
        rows.append((sc, trust_rank.get(c.get("trust"), 0), c.get("published") or "",
                     c.get("view_count") or 0, c["url"], c, s))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2], -r[3], r[4]))
    target = CFG["research_targets"]["videos_selected_target"]
    existing = {v["id"] for v in queue["videos"]}
    already = existing_resource_urls()  # 既に別テーマで台帳化済みのURLは取り込まない
    n_sel = sum(1 for v in queue["videos"] if v["status"] == "selected")
    for sc, _, _, _, _, c, s in rows:
        if c["id"] in existing:
            continue
        if c["url"] in already:
            queue["videos"].append({
                "id": c["id"], "url": c["url"], "title": c["title"], "channel": c.get("channel"),
                "status": "rejected", "score": sc,
                "reject_reason": f"duplicate_cross_theme({already[c['url']]})",
            })
            existing.add(c["id"])
            continue
        cut = bool(s.get("theme_zero")) or sc <= 0
        status = "rejected" if cut else ("selected" if n_sel < target else "candidate")
        if status == "selected":
            n_sel += 1
        queue["videos"].append({
            "id": c["id"], "url": c["url"], "title": c["title"], "channel": c.get("channel"),
            "channel_id": c.get("channel_id"), "published": c.get("published"),
            "duration": c.get("duration"), "view_count": c.get("view_count"),
            "trust": c.get("trust", "unknown"), "score": sc,
            "score_detail": str(s.get("detail", ""))[:300],
            "status": status, "reject_reason": "theme_zero" if cut else None,
        })
    state["last_scan_at"] = now_iso()
    sel_min = CFG["research_targets"]["videos_selected_min"]
    if n_sel >= sel_min:
        state["phase"] = "research_fetch"
        return True, f"候補{len(rows)}件採点 → selected {n_sel}"
    if not state.get("scan_fallback_done"):
        state["scan_fallback_done"] = True
        state["_use_fallback"] = True
        return True, f"selected {n_sel} (<{sel_min}) → fallbackキーワードで再scan予定"
    state["video_shortfall"] = True
    state["phase"] = "research_fetch" if n_sel >= 1 else state["phase"]
    if n_sel < 1:
        set_stuck(state, "needs_human", "動画候補が1本も選定できない")
        return False, "候補0"
    return True, f"selected {n_sel}（shortfallで前進）"


def prework_research_fetch(state, queue, theme, runid):
    todo = [v for v in queue["videos"] if v["status"] == "selected"][:CFG["research_targets"]["fetch_per_run"]]
    if not todo:
        return {"mode": "transition_check"}
    prepared = []
    for v in todo:
        base = os.path.join(CACHE, "subs", v["id"])
        args = ["--skip-download", "--write-subs", "--write-auto-subs",
                "--sub-langs", "ja,en", "--write-info-json",
                "--extractor-args", "youtube:lang=ja",
                "--retries", "3", "--socket-timeout", "30",
                "-o", base, v["url"]]
        st, _, err = ytdlp_json(args, 240)
        if st == "bot":
            return {"mode": "abort_external", "note": "YouTube bot検知(fetch)"}
        vtts = sorted(globmod.glob(base + "*.vtt"))
        if not vtts:
            v["status"] = "needs_human" if v.get("trust") == "official" else "rejected"
            v["reject_reason"] = "no_subs"
            run_log(runid, f"fetch: {v['id']} 字幕なし → {v['status']}")
            continue
        pick = next((p for p in vtts if ".ja" in p), vtts[0])
        txt_path = os.path.join(CACHE, "subs", v["id"] + ".txt")
        nchars = normalize_vtt(pick, txt_path)
        info = read_json(base + ".info.json", {})
        v["channel_id"] = v.get("channel_id") or info.get("channel_id")
        v["subs"] = "manual" if (".ja.vtt" in pick and "--write-subs" and not re.search(r"\.ja(-orig)?\.vtt$", pick) is None and False) else ("auto" if "a." not in pick else "auto")
        v["subs"] = "auto"  # v1: 自動字幕として扱い（聞き取り）注記を要求する安全側
        prepared.append({"id": v["id"], "title": v["title"], "subs_file": os.path.relpath(txt_path, ROOT),
                         "chars": nchars, "channel": v.get("channel")})
    if not prepared:
        save_queue(queue)
        return {"mode": "reloop", "note": "今回分は字幕なしで全滅・次候補へ"}
    fdir = os.path.join(STAGING, f"fetch-{runid}")
    os.makedirs(fdir, exist_ok=True)
    manifest = os.path.join(fdir, "manifest.json")
    write_json_atomic(manifest, {"videos": prepared,
                                 "required_concepts": theme.get("required_concepts", [])})
    runmeta_save(runid, {"fetch_ids": [p["id"] for p in prepared], "manifest": manifest})
    v = theme_vars(theme)
    v.update({"FETCH_MANIFEST": os.path.relpath(manifest, ROOT), "N_VIDEOS": len(prepared)})
    return {"mode": "llm", "vars": v}


def apply_research_fetch(state, queue, theme, runid, outbox):
    data = (outbox.get("metrics") or {}).get("data") or outbox.get("data") or {}
    votes = data.get("votes")
    if not isinstance(votes, list) or not votes:
        return False, "outboxにvotes配列がない"
    byid = {v["id"]: v for v in queue["videos"]}
    n_ok = 0
    for vote in votes:
        v = byid.get(vote.get("id"))
        if not v or v["status"] != "selected":
            continue
        claims = vote.get("claims") or []
        ok = bool(vote.get("concepts_2plus")) and bool(vote.get("has_definition_or_howto")) \
            and isinstance(claims, list) and len(claims) >= 3 and not vote.get("unsure")
        if vote.get("unsure"):
            v["status"] = "needs_human"
        elif ok:
            v["status"] = "fetched"
            v["claims"] = claims[:6]
            v["summary"] = str(vote.get("summary", ""))[:300]
            n_ok += 1
        else:
            v["status"] = "rejected"
            v["reject_reason"] = "vote_failed"
    remaining_sel = sum(1 for v in queue["videos"] if v["status"] == "selected")
    fetched = sum(1 for v in queue["videos"] if v["status"] in ("fetched", "ledgered"))
    if remaining_sel == 0:
        if fetched < CFG["research_targets"]["videos_selected_min"]:
            promoted = 0
            for v in queue["videos"]:
                if v["status"] == "candidate" and promoted < (CFG["research_targets"]["videos_selected_min"] - fetched):
                    v["status"] = "selected"
                    promoted += 1
            if promoted == 0:
                state["video_shortfall"] = True
                state["phase"] = "research_ledger" if fetched >= 1 else state["phase"]
                if fetched < 1:
                    set_stuck(state, "needs_human", "適合動画が1本も確保できない")
                    return False, "fetched 0"
        else:
            state["phase"] = "research_ledger"
    return True, f"適合票 {n_ok}/{len(votes)} 通過（fetched計{fetched}）"


def existing_resource_urls():
    """既存sources台帳のresource URL → ファイル名。クロステーマ重複の検出に使う"""
    out = {}
    for p in globmod.glob(os.path.join(ROOT, "knowledge/sources/*.md")):
        try:
            m = re.search(r"^resource:\s*(\S+)", open(p).read(), re.M)
        except Exception:
            continue
        if m:
            out[m.group(1).strip()] = os.path.basename(p)
    return out


def compute_origin_article(url, platforms):
    m = re.match(r"https?://([^/]+)(/[^?#]*)?", url or "")
    if not m:
        return "web:unknown"
    host = m.group(1).lower().removeprefix("www.")
    path = (m.group(2) or "/")
    parts = host.split(".")
    etld1 = ".".join(parts[-2:]) if len(parts) >= 2 else host
    if host in platforms or etld1 in platforms:
        segs = [s for s in path.split("/") if s]
        author = "/" + segs[0] if segs else ""
        return f"web:{host}{author}"
    return f"web:{etld1}"


def prework_research_ledger(state, queue, theme, runid):
    todo = [v for v in queue["videos"] if v["status"] == "fetched"][:CFG["research_targets"]["ledgers_per_run"]]
    if not todo:
        return {"mode": "transition_check"}
    items = []
    for v in todo:
        info = read_json(os.path.join(CACHE, "subs", v["id"] + ".info.json"), {})
        items.append({
            "id": v["id"], "url": v["url"], "title": info.get("title") or v["title"],
            "channel": info.get("channel") or v.get("channel"),
            "channel_id": v.get("channel_id") or info.get("channel_id") or "",
            "origin": f"youtube:{v.get('channel_id') or info.get('channel_id') or 'unknown'}",
            "published": info.get("upload_date") or v.get("published") or "",
            "duration_s": info.get("duration") or v.get("duration"),
            "view_count": info.get("view_count") or v.get("view_count"),
            "subs_file": os.path.relpath(os.path.join(CACHE, "subs", v["id"] + ".txt"), ROOT),
            "subs": v.get("subs", "auto"),
            "claims": v.get("claims", []),
        })
    ldir = os.path.join(STAGING, f"ledger-{runid}")
    os.makedirs(ldir, exist_ok=True)
    manifest = os.path.join(ldir, "manifest.json")
    write_json_atomic(manifest, {"videos": items})
    runmeta_save(runid, {"ledger_ids": [i["id"] for i in items], "manifest": manifest})
    v = theme_vars(theme)
    v.update({"LEDGER_MANIFEST": os.path.relpath(manifest, ROOT), "N_LEDGERS": len(items),
              "TEMPLATE_FILE": "pipeline/templates/ledger-video.md",
              "EXEMPLAR_FILE": "knowledge/sources/video-ge-5-stages-beginner.md"})
    return {"mode": "llm", "vars": v}


def _ledger_gates(runid, new_files, mode):
    rc, _ = gate_validate_okf(runid)
    if rc != 0:
        return False, "validate_okf失敗"
    rc, out = run_gate("check_ledger",
                       ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_ledger.py"),
                        "--mode", mode] + new_files, runid)
    if rc != 0:
        return False, f"check_ledger失敗: {out[:200]}"
    return True, ""


def apply_research_ledger(state, queue, theme, runid, outbox):
    data = (outbox.get("metrics") or {}).get("data") or outbox.get("data") or {}
    mapping = data.get("map")
    if not isinstance(mapping, list) or not mapping:
        return False, "outboxにmap配列（id→path）がない"
    new_files = []
    byid = {v["id"]: v for v in queue["videos"]}
    for m in mapping:
        p = m.get("path", "")
        if not fnmatch.fnmatch(p, "knowledge/sources/video-*.md") or not os.path.exists(os.path.join(ROOT, p)):
            return False, f"map不正: {p}"
        new_files.append(p)
    ok, why = _ledger_gates(runid, new_files, "video")
    if not ok:
        revert_paths(new_files + ["knowledge/sources/index.md", "knowledge/log.md"], runid)
        return False, why
    for m in mapping:
        v = byid.get(m.get("id"))
        if v:
            v["status"] = "ledgered"
            v["ledger_path"] = m["path"]
    if not any(v["status"] == "fetched" for v in queue["videos"]):
        state["phase"] = "research_web"
    return True, f"台帳{len(new_files)}本作成"


def prework_research_web(state, queue, theme, runid):
    done = set(queue["web"]["subtopics_done"])
    sub = next((s for s in theme.get("subtopics", []) if s["id"] not in done), None)
    if sub is None:
        return {"mode": "transition_check"}
    wdir = os.path.join(STAGING, "web", runid)
    os.makedirs(wdir, exist_ok=True)
    runmeta_save(runid, {"subtopic": sub["id"], "wdir": wdir})
    v = theme_vars(theme)
    v.update({"SUBTOPIC_ID": sub["id"], "SUBTOPIC_GOAL": sub["goal"],
              "SUBTOPIC_QUERIES": " / ".join(sub.get("queries", [])),
              "WEB_OUT_DIR": os.path.relpath(wdir, ROOT)})
    return {"mode": "llm", "vars": v}


def apply_research_web(state, queue, theme, runid, outbox):
    meta = runmeta_load(runid)
    sub = meta.get("subtopic")
    wdir = meta.get("wdir")
    cand_f = os.path.join(wdir, "candidates.json")
    if not os.path.exists(cand_f):
        return False, "candidates.json未作成"
    rc, out = run_gate("check_web_sources",
                       ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_web_sources.py"),
                        cand_f, "--theme", state["theme"]["id"]], runid)
    verified_f = cand_f + ".verified.json"
    verified = read_json(verified_f, {}).get("verified", []) if rc == 0 else []
    keep_dir = os.path.join(CACHE, "web", sub)
    os.makedirs(keep_dir, exist_ok=True)
    for fn in os.listdir(wdir):
        shutil.copy2(os.path.join(wdir, fn), os.path.join(keep_dir, fn))
    platforms = yaml.safe_load(open(os.path.join(PIPE, "config", "platforms.yaml")))["platform_domains"]
    for c in verified:
        c["origin"] = compute_origin_article(c.get("url"), platforms)
        c["subtopic"] = sub
        c["status"] = "verified"
        c["cache_dir"] = os.path.relpath(keep_dir, ROOT)
        if not any(x.get("url") == c.get("url") for x in queue["web"]["candidates"]):
            queue["web"]["candidates"].append(c)
    queue["web"]["subtopics_done"].append(sub)
    n_all = len(queue["web"]["candidates"])
    remaining = [s for s in theme.get("subtopics", []) if s["id"] not in set(queue["web"]["subtopics_done"])]
    if not remaining:
        if n_all >= CFG["research_targets"]["article_ledgers_min"]:
            state["phase"] = "web_ledger"
        elif not state.get("web_rerun_done"):
            state["web_rerun_done"] = True
            if queue["web"]["subtopics_done"]:
                queue["web"]["subtopics_done"].pop(0)
        else:
            state["phase"] = "web_ledger" if n_all >= 1 else state["phase"]
            if n_all < 1:
                set_stuck(state, "needs_human", "Web候補が1件も検査通過しない")
                return False, "verified 0"
    return True, f"subtopic {sub}: verified {len(verified)}件（累計{n_all}）"


def prework_web_ledger(state, queue, theme, runid):
    todo = [c for c in queue["web"]["candidates"] if c["status"] == "verified"][:CFG["research_targets"]["ledgers_per_run"]]
    if not todo:
        return {"mode": "transition_check"}
    ldir = os.path.join(STAGING, f"webledger-{runid}")
    os.makedirs(ldir, exist_ok=True)
    manifest = os.path.join(ldir, "manifest.json")
    write_json_atomic(manifest, {"articles": todo})
    runmeta_save(runid, {"urls": [c["url"] for c in todo], "manifest": manifest})
    v = theme_vars(theme)
    v.update({"ARTICLE_MANIFEST": os.path.relpath(manifest, ROOT), "N_ARTICLES": len(todo),
              "TEMPLATE_FILE": "pipeline/templates/ledger-article.md",
              "EXEMPLAR_FILE": "knowledge/sources/article-zenn-knowledgesense-okf.md"})
    return {"mode": "llm", "vars": v}


def _research_complete(state, queue):
    videos = sum(1 for v in queue["videos"] if v["status"] == "ledgered")
    articles = sum(1 for c in queue["web"]["candidates"] if c["status"] == "ledgered")
    primary = sum(1 for c in queue["web"]["candidates"]
                  if c["status"] == "ledgered" and c.get("source_tier") == "primary")
    origins = {v.get("channel_id") for v in queue["videos"] if v["status"] == "ledgered"}
    origins |= {c.get("origin") for c in queue["web"]["candidates"] if c["status"] == "ledgered"}
    origins.discard(None)
    t = CFG["research_targets"]
    ok = (videos >= (1 if state.get("video_shortfall") else t["video_ledgers_min"])
          and articles >= 1 and len(origins) >= min(t["independent_origins_min"], videos + articles))
    return ok, {"videos": videos, "articles": articles, "primary": primary, "origins": len(origins)}


def apply_web_ledger(state, queue, theme, runid, outbox):
    data = (outbox.get("metrics") or {}).get("data") or outbox.get("data") or {}
    mapping = data.get("map")
    if not isinstance(mapping, list) or not mapping:
        return False, "outboxにmap配列がない"
    new_files = []
    byurl = {c["url"]: c for c in queue["web"]["candidates"]}
    for m in mapping:
        p = m.get("path", "")
        if not fnmatch.fnmatch(p, "knowledge/sources/article-*.md") or not os.path.exists(os.path.join(ROOT, p)):
            return False, f"map不正: {p}"
        new_files.append(p)
    ok, why = _ledger_gates(runid, new_files, "article")
    if not ok:
        revert_paths(new_files + ["knowledge/sources/index.md", "knowledge/log.md"], runid)
        return False, why
    for m in mapping:
        c = byurl.get(m.get("url"))
        if c:
            c["status"] = "ledgered"
            c["ledger_path"] = m["path"]
    if not any(c["status"] == "verified" for c in queue["web"]["candidates"]):
        done, stats = _research_complete(state, queue)
        if done:
            state["phase"] = "knowledge"
            notify(state, "pipeline: research完了",
                   f"pe: 動画{stats['videos']}本+記事{stats['articles']}本 (primary {stats['primary']}, origins {stats['origins']}) → knowledge執筆へ")
        else:
            if stats["videos"] < 2 and stats["articles"] < 1:
                set_stuck(state, "needs_human", f"research完了条件未達: {stats}")
                return False, str(stats)
            state["phase"] = "knowledge"
            notify(state, "pipeline: research完了(不足あり)", f"{stats} → shortfallのままknowledgeへ")
    return True, f"記事台帳{len(new_files)}本作成"


def prework_knowledge(state, queue, theme, runid):
    ledgers = sorted(globmod.glob(os.path.join(ROOT, "knowledge/sources/*-%s-*.md" % state["theme"]["id"])))
    ledgers = [os.path.relpath(p, ROOT) for p in ledgers]
    for extra in theme.get("extra_sources", []):
        if os.path.exists(os.path.join(ROOT, extra)) and extra not in ledgers:
            ledgers.append(extra)
    plan_f = os.path.join(STAGING, "knowledge", "plan.json")
    os.makedirs(os.path.dirname(plan_f), exist_ok=True)
    plan = read_json(plan_f, None)
    plan_status = "未作成（今回のランで作成する）" if plan is None else \
        f"{sum(1 for e in plan.get('concepts', []) if e.get('status') == 'done')}/{len(plan.get('concepts', []))} done"
    runmeta_save(runid, {"ledgers": ledgers, "plan_f": plan_f})
    v = theme_vars(theme)
    v.update({"N_LEDGERS": len(ledgers), "PLAN_FILE": os.path.relpath(plan_f, ROOT),
              "PLAN_STATUS": plan_status,
              "LEDGER_LIST_FILE": _write_list_file(runid, "ledgers.txt", ledgers),
              "CONCEPTS_MIN": CFG["knowledge_targets"]["concepts_min"]})
    return {"mode": "llm", "vars": v}


def _write_list_file(runid, name, items):
    d = os.path.join(STAGING, f"lists-{runid}")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write("\n".join(items) + "\n")
    return os.path.relpath(p, ROOT)


def apply_knowledge(state, queue, theme, runid, outbox):
    plan_f = runmeta_load(runid).get("plan_f")
    rc, out = run_gate("check_plan", ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_plan.py"),
                                      plan_f, "--kdir", theme["theme"]["knowledge_dir"]], runid)
    if rc != 0:
        return False, f"check_plan失敗: {out[:200]}"
    if outbox["status"] == "succeeded_partial":
        return True, "knowledge部分進捗（plan継続）"
    rc, _ = gate_validate_okf(runid)
    if rc != 0:
        return False, "validate_okf失敗"
    plan = read_json(plan_f, {})
    concepts = plan.get("concepts", [])
    done = [e for e in concepts if e.get("status") == "done"]
    if len(done) < CFG["knowledge_targets"]["concepts_min"] or len(done) < len(concepts):
        return False, f"succeededだがplan未完 ({len(done)}/{len(concepts)})"
    rc, out = run_gate("check_provenance",
                       ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_provenance.py"),
                        "--kdir", theme["theme"]["knowledge_dir"], "--theme", state["theme"]["id"]], runid)
    if rc != 0:
        return False, f"check_provenance失敗: {out[:200]}"
    state["phase"] = "grade_k"
    return True, f"knowledge完成（コンセプト{len(done)}本）→ 採点へ"


def _render_rubric(kind, state, theme, runid):
    tmpl = open(os.path.join(PIPE, "templates", f"rubric-{'knowledge' if kind == 'k' else 'deck'}.tmpl.md")).read()
    tid = state["theme"]["id"]
    n_src = len(globmod.glob(os.path.join(ROOT, f"knowledge/sources/*-{tid}-*.md")))
    previews = sorted(globmod.glob(os.path.join(ROOT, theme["theme"]["deck_dir"], "build", "preview", "slide-*.png")))
    vars_ = {"THEME_SLUG": theme["theme"]["slug"], "THEME_TITLE": theme["theme"]["title"],
             "KNOWLEDGE_DIR": theme["theme"]["knowledge_dir"],
             "SOURCES_GLOB": f"knowledge/sources/*-{tid}-*.md", "SOURCE_COUNT": n_src,
             "DECK_DIR": theme["theme"]["deck_dir"], "SLIDE_RANGE": f"1-{len(previews)}"}
    text = render(tmpl, vars_)
    path = os.path.join(LOGS, f"rubric-{kind}-{runid}.md")
    with open(path, "w") as f:
        f.write(text)
    return path, n_src, len(previews)


def prework_grade(kind, state, queue, theme, runid):
    rubric_path, n_src, n_prev = _render_rubric(kind, state, theme, runid)
    tid = state["theme"]["id"]
    if kind == "k":
        files = sorted(globmod.glob(os.path.join(ROOT, theme["theme"]["knowledge_dir"], "*.md")))
        files += sorted(globmod.glob(os.path.join(ROOT, f"knowledge/sources/*-{tid}-*.md")))
        files = [os.path.relpath(p, ROOT) for p in files]
        for extra in theme.get("extra_sources", []):
            if os.path.exists(os.path.join(ROOT, extra)) and extra not in files:
                files.append(extra)
        denom = len(files)
        list_file = _write_list_file(runid, "grade-files.txt", files)
    else:
        previews = sorted(globmod.glob(os.path.join(ROOT, theme["theme"]["deck_dir"], "build", "preview", "slide-*.png")))
        files = [os.path.relpath(p, ROOT) for p in previews]
        denom = len(files)
        if denom == 0:
            return {"mode": "noop_fail", "note": "preview PNGが0枚（ビルド未完了）"}
        list_file = _write_list_file(runid, "grade-previews.txt", files)
    report = os.path.join(LOGS, "grades", f"grade_{kind}-{runid}.md")
    runmeta_save(runid, {"rubric": rubric_path, "denominator": denom, "report": report})
    v = theme_vars(theme)
    v.update({"RUBRIC_FILE": os.path.relpath(rubric_path, ROOT),
              "TARGET_LIST_FILE": list_file, "DENOMINATOR": denom,
              "REPORT_FILE": os.path.relpath(report, ROOT),
              "N_ITEMS": GRADE_ITEMS["grade_" + kind]})
    return {"mode": "llm", "vars": v}


def apply_grade(kind, state, queue, theme, runid, outbox):
    meta = runmeta_load(runid)
    report = meta.get("report")
    g = state["grade"]["knowledge" if kind == "k" else "deck"]
    if not report or not os.path.exists(report):
        return _grade_parse_fail(state, g, kind, "採点レポート未作成")
    text = open(report).read()
    fenced = re.findall(r"```json\s*([\s\S]*?)```", text)
    if len(fenced) != 1:
        return _grade_parse_fail(state, g, kind, f"fenced jsonが{len(fenced)}個")
    try:
        gj = json.loads(fenced[0])
    except Exception as e:
        return _grade_parse_fail(state, g, kind, f"json不正: {e}")
    scores = gj.get("scores")
    n_items = GRADE_ITEMS["grade_" + kind]
    if not isinstance(scores, list) or len(scores) != n_items:
        return _grade_parse_fail(state, g, kind, "scores件数不一致")
    try:
        smap = {int(s["item"]): int(s["score"]) for s in scores}
    except Exception:
        return _grade_parse_fail(state, g, kind, "score整数でない")
    if sorted(smap) != list(range(1, n_items + 1)):
        return _grade_parse_fail(state, g, kind, "item番号不正")
    table_rows = len(re.findall(r"^\|\s*(?:slide-\d+|\S+\.md)\s*\|", text, re.M))
    denom = meta.get("denominator", 0)
    if table_rows < denom:
        return _grade_parse_fail(state, g, kind, f"実見/読了表 {table_rows}/{denom} 行不足")
    g["retry_used"] = False
    g["iter"] += 1
    target = CFG["grade_target"]
    unmet = sorted([i for i, s in smap.items() if s < target])
    scores_str = "/".join(str(smap[i]) for i in range(1, n_items + 1))
    if not unmet:
        g["pass_streak"] += 1
        if g["pass_streak"] >= CFG["confirm_grades_required"]:
            g["last_unmet"], g["last_scores"] = [], smap
            if kind == "k" and scope_of(state["theme"]["id"]) == "knowledge":
                notify(state, "pipeline: grade_k 合格（knowledge-onlyテーマ完了）",
                       f"{state['theme']['id']}: {scores_str}（{g['pass_streak']}連続）")
                advance_theme(state, queue, f"{state['theme']['id']} ナレッジ完成（{scores_str}）")
                return True, f"採点 {scores_str} 合格確定 → テーマ完了"
            state["phase"] = "draft" if kind == "k" else "brief"
            notify(state, f"pipeline: grade_{kind} 合格",
                   f"{state['theme']['id']}: {scores_str}（確認採点含む{g['pass_streak']}連続） → {state['phase']}へ")
            return True, f"採点 {scores_str} 合格確定"
        g["last_unmet"], g["last_scores"] = [], smap
        return True, f"採点 {scores_str} 初回合格 → 確認採点へ"
    g["pass_streak"] = 0
    prev_unmet, prev_scores = g.get("last_unmet"), g.get("last_scores") or {}
    if prev_unmet and sorted(prev_unmet) == unmet and \
            all(smap[i] <= int(prev_scores.get(str(i), prev_scores.get(i, 10))) for i in unmet):
        set_stuck(state, "stagnation", f"未達{unmet}が2採点連続で非改善 scores={scores_str}")
        return False, "停滞"
    g["last_unmet"], g["last_scores"] = unmet, smap
    findings = gj.get("findings", [])
    write_json_atomic(os.path.join(STAGING, f"findings-{'k' if kind == 'k' else 'd'}.json"),
                      {"findings": findings, "unmet": unmet, "from_run": runid})
    if g["repair_count"] >= CFG["repair_limit"]:
        set_stuck(state, "repair_exhausted", f"repair{g['repair_count']}回でも未達{unmet}")
        return False, "repair上限"
    state["phase"] = "improve_" + kind
    return True, f"採点 {scores_str} 未達{unmet} → improve（findings {len(findings)}件）"


def _grade_parse_fail(state, g, kind, why):
    if not g.get("retry_used"):
        g["retry_used"] = True
        return True, f"採点結果不受理（{why}）→ 新runで再採点1回"
    set_stuck(state, "grade_parse_failed", why)
    return False, why


def prework_improve(kind, state, queue, theme, runid):
    ff = os.path.join(STAGING, f"findings-{kind}.json")
    fdata = read_json(ff, {})
    findings = fdata.get("findings", [])
    if not findings:
        state["phase"] = "grade_" + kind
        return {"mode": "reloop", "note": "findingsなし→再採点へ"}
    runmeta_save(runid, {"findings_file": ff, "n_findings": len(findings)})
    v = theme_vars(theme)
    v.update({"FINDINGS_FILE": os.path.relpath(ff, ROOT), "N_FINDINGS": len(findings)})
    return {"mode": "llm", "vars": v}


def apply_improve(kind, state, queue, theme, runid, outbox):
    meta = runmeta_load(runid)
    n = meta.get("n_findings", 0)
    data = (outbox.get("metrics") or {}).get("data") or outbox.get("data") or {}
    disp = data.get("dispositions")
    if not isinstance(disp, list) or len(disp) != n:
        return False, f"disposition件数不一致 {len(disp) if isinstance(disp, list) else 'なし'}/{n}"
    g = state["grade"]["knowledge" if kind == "k" else "deck"]
    findings = read_json(meta.get("findings_file"), {}).get("findings", [])
    unmet = read_json(meta.get("findings_file"), {}).get("unmet", [])
    unmet_items = set(unmet)
    for d in disp:
        st = str(d.get("disposition", ""))
        if st.startswith("deferred"):
            fid = d.get("id")
            f_item = next((f.get("item") for f in findings if f.get("id") == fid), None)
            if "needs_research" in st and f_item in unmet_items:
                set_stuck(state, "needs_human",
                          f"未達項目{f_item}のfinding {fid} がneeds_research deferred（improveで解決不能）")
                return False, "deferred needs_research on unmet item"
    if kind == "k":
        rc, _ = gate_validate_okf(runid)
        if rc != 0:
            return False, "validate_okf失敗"
    else:
        ok, why = _deck_gates(state, theme, runid, check_text=False)
        if not ok:
            return False, why
    g["repair_count"] += 1
    state["phase"] = "grade_" + kind
    return True, f"improve完了（disposition {len(disp)}件）→ 再採点"


def prework_draft(state, queue, theme, runid):
    ledgers = sorted(globmod.glob(os.path.join(ROOT, theme["theme"]["knowledge_dir"], "*.md")))
    ledgers = [os.path.relpath(p, ROOT) for p in ledgers]
    draft_f = os.path.join(STAGING, "draft", "draft.md")
    os.makedirs(os.path.dirname(draft_f), exist_ok=True)
    n_blocks = 0
    if os.path.exists(draft_f):
        n_blocks = len(re.findall(r"^## SLIDE ", open(draft_f).read(), re.M))
    runmeta_save(runid, {"draft_f": draft_f})
    fb = os.path.join(PIPE, "themes", f"{state['theme']['id']}-feedback.md")
    v = theme_vars(theme)
    v.update({"DRAFT_FILE": os.path.relpath(draft_f, ROOT),
              "KNOWLEDGE_LIST_FILE": _write_list_file(runid, "kfiles.txt", ledgers),
              "CURRENT_BLOCKS": n_blocks,
              "FEEDBACK_FILE": os.path.relpath(fb, ROOT) if os.path.exists(fb) else "（なし）",
              "SLIDES_MIN": CFG["draft_targets"]["slides_min"],
              "SLIDES_MAX": CFG["draft_targets"]["slides_max"]})
    return {"mode": "llm", "vars": v}


def apply_draft(state, queue, theme, runid, outbox):
    draft_f = runmeta_load(runid).get("draft_f")
    partial_flag = ["--partial"] if outbox["status"] == "succeeded_partial" else []
    rc, out = run_gate("check_draft", ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_draft.py"),
                                       draft_f] + partial_flag, runid)
    if rc != 0:
        return False, f"check_draft失敗: {out[:200]}"
    if outbox["status"] == "succeeded_partial":
        return True, "draft部分進捗"
    state["phase"] = "deck"
    return True, "draft完成 → deck変換へ"


def prework_deck(state, queue, theme, runid):
    draft_f = os.path.join(STAGING, "draft", "draft.md")
    if not os.path.exists(draft_f):
        state["phase"] = "draft"
        return {"mode": "reloop", "note": "draftが無い→draftへ戻す"}
    text = open(draft_f).read()
    n_fig = len(re.findall(r"^- figure:", text, re.M))
    ddir = os.path.join(ROOT, theme["theme"]["deck_dir"])
    adir = os.path.join(ddir, "assets")
    os.makedirs(adir, exist_ok=True)
    ph = os.path.join(PIPE, "templates", "placeholder-4x3.png")
    for i in range(1, n_fig + 1):
        dst = os.path.join(adir, f"fig-{state['theme']['id']}-{i:02d}.png")
        if not os.path.exists(dst):
            shutil.copy2(ph, dst)
    runmeta_save(runid, {"n_fig": n_fig})
    v = theme_vars(theme)
    v.update({"DRAFT_FILE": os.path.relpath(draft_f, ROOT), "N_FIGURES": n_fig,
              "ASSET_PREFIX": f"assets/fig-{state['theme']['id']}-"})
    return {"mode": "llm", "vars": v}


def _deck_gates(state, theme, runid, check_text=True):
    ddir = theme["theme"]["deck_dir"]
    rc, out = run_gate("gate_deck", ["/bin/bash", os.path.join(BIN, "gate_deck.sh"), ddir], runid, timeout=900)
    if rc != 0:
        return False, f"gate_deck失敗(exit {rc})"
    # 文言不変ゲートは draft→deck 変換時のみ。improve_d はfindingsに基づく文言修正が正当なため
    # draft.md との全文一致は要求しない（2026-08-14 07:06 の誤検出対応）
    if check_text:
        rc, out = run_gate("check_deck_text",
                           ["/opt/homebrew/bin/python3", os.path.join(BIN, "check_deck_text.py"),
                            os.path.join(STAGING, "draft", "draft.md"),
                            os.path.join(ddir, "deck.json")], runid)
        if rc != 0:
            return False, f"check_deck_text失敗: {out[:200]}"
    return True, ""


def apply_deck(state, queue, theme, runid, outbox):
    ok, why = _deck_gates(state, theme, runid)
    if not ok:
        return False, why
    state["phase"] = "grade_d"
    return True, "deck生成+ビルド検証OK → 採点へ"


def prework_brief(state, queue, theme, runid):
    v = theme_vars(theme)
    slug = theme["theme"]["slug"]
    brief_path = f"docs/codex-brief-{slug}.md"
    draft_f = os.path.join(STAGING, "draft", "draft.md")
    runmeta_save(runid, {"brief_path": brief_path})
    v.update({"BRIEF_PATH": brief_path,
              "EXEMPLAR_BRIEF": "docs/codex-brief-okf-visual-v2.md",
              "DRAFT_FILE": os.path.relpath(draft_f, ROOT) if os.path.exists(draft_f) else "（draftなし）",
              "N_FIGURES": runmeta_load(runid).get("n_fig", 0) or len(
                  globmod.glob(os.path.join(ROOT, theme["theme"]["deck_dir"], "assets", "fig-*.png")))})
    return {"mode": "llm", "vars": v}


def apply_brief(state, queue, theme, runid, outbox):
    brief_path = runmeta_load(runid).get("brief_path")
    full = os.path.join(ROOT, brief_path)
    if not os.path.exists(full):
        return False, "brief未作成"
    text = open(full).read()
    for sec in ["背景", "変更禁止", "画像", "検証"]:
        if sec not in text:
            revert_paths([brief_path], runid)
            return False, f"必須節『{sec}』欠落"
    if re.search(r"notes_slide|スピーカーノート", text) and \
            not re.search(r"入れない|操作しない|触らない|禁止|壊", text):
        revert_paths([brief_path], runid)
        return False, "PPTXノートへの言及が禁止事項として書かれていない"
    notify(state, f"pipeline: {state['theme']['id']} brief発行 🎉",
           f"{brief_path} 発行。デッキ={theme['theme']['deck_dir']}")
    advance_theme(state, queue, f"{state['theme']['id']} brief発行・テーマ完走")
    return True, "brief発行 → テーマ完了"


PREWORK = {
    "research_scan": prework_research_scan,
    "research_fetch": prework_research_fetch,
    "research_ledger": prework_research_ledger,
    "research_web": prework_research_web,
    "web_ledger": prework_web_ledger,
    "knowledge": prework_knowledge,
    "grade_k": lambda s, q, t, r: prework_grade("k", s, q, t, r),
    "improve_k": lambda s, q, t, r: prework_improve("k", s, q, t, r),
    "draft": prework_draft,
    "deck": prework_deck,
    "grade_d": lambda s, q, t, r: prework_grade("d", s, q, t, r),
    "improve_d": lambda s, q, t, r: prework_improve("d", s, q, t, r),
    "brief": prework_brief,
}

APPLY = {
    "research_scan": apply_research_scan,
    "research_fetch": apply_research_fetch,
    "research_ledger": apply_research_ledger,
    "research_web": apply_research_web,
    "web_ledger": apply_web_ledger,
    "knowledge": apply_knowledge,
    "grade_k": lambda s, q, t, r, o: apply_grade("k", s, q, t, r, o),
    "improve_k": lambda s, q, t, r, o: apply_improve("k", s, q, t, r, o),
    "draft": apply_draft,
    "deck": apply_deck,
    "grade_d": lambda s, q, t, r, o: apply_grade("d", s, q, t, r, o),
    "improve_d": lambda s, q, t, r, o: apply_improve("d", s, q, t, r, o),
    "brief": apply_brief,
}

TRANSITION_NEXT = {
    "research_fetch": "research_ledger",
    "research_ledger": "research_web",
    "web_ledger": "knowledge",
}

COMMIT_PATHS = {
    "research_ledger": ["knowledge/sources", "knowledge/log.md"],
    "web_ledger": ["knowledge/sources", "knowledge/log.md"],
    "knowledge": ["knowledge"],
    "improve_k": ["knowledge"],
    "deck": [],  # deck_dirはtheme依存で動的に追加
    "improve_d": [],
    "brief": ["docs"],
}


# ---------------------------------------------------------------- cycle

def selftest():
    """パーサ自己診断（毎ラン起動時）。失敗＝ゲート自体の故障として実行を止める"""
    tmp = os.path.join(STAGING, "_selftest")
    os.makedirs(tmp, exist_ok=True)
    good = {"schema": "outbox-v1", "run_id": "T1", "phase": "research_scan",
            "status": "succeeded", "artifacts": [], "metrics": {"progress": 1}, "notes": "t"}
    p = os.path.join(OUTBOX, "result-T1.json")
    write_json_atomic(p, good)
    o, err = load_outbox("T1", "research_scan")
    assert o and not err, f"selftest: 正常outboxが不受理 {err}"
    o, err = load_outbox("T1", "knowledge")
    assert o is None, "selftest: phase不一致が受理された"
    bad = dict(good)
    bad["status"] = "hallucinated_great_success"
    write_json_atomic(p, bad)
    o, err = load_outbox("T1", "research_scan")
    assert o is None, "selftest: 不正statusが受理された"
    os.remove(p)
    try:
        render("hello {{X}} {{Y}}", {"X": "1"})
        raise AssertionError("selftest: 未解決変数を検出できない")
    except ValueError:
        pass
    try:
        render("a {{X}}", {"X": "bad\nvalue"})
        raise AssertionError("selftest: 複数行値を拒否できない")
    except ValueError:
        pass
    assert fnmatch.fnmatch("knowledge/sources/video-pe-x.md", "knowledge/sources/*.md")
    return True


def rotate_logs():
    for name in ("launchd.log", "activity.log"):
        p = os.path.join(LOGS, name)
        if os.path.exists(p) and os.path.getsize(p) > 10 * 1024 * 1024:
            shutil.move(p, p + "." + now().strftime("%Y%m"))


def network_ok():
    rc, _, _ = sh(["curl", "-s", "-m", "5", "-o", "/dev/null", "https://api.anthropic.com"], timeout=10)
    if rc == 0:
        return True
    rc, _, _ = sh(["curl", "-s", "-m", "5", "-o", "/dev/null", "https://github.com"], timeout=10)
    return rc == 0


def gen_runid():
    return now().strftime("%m%d%H%M") + "%02x" % (os.getpid() % 256)


def cap_check(state, phase):
    group = CFG["cap_group"][phase]
    cap = CFG["run_caps"][group]
    if group == "research":
        used = sum(v for k, v in state["run_counts"].items()
                   if CFG["cap_group"].get(k) == "research")
    else:
        used = state["run_counts"].get(phase, 0)
    return used < cap, used, cap


def digest_maybe(state, queue):
    if now().hour != CFG["digest_hour"]:
        return
    flag = os.path.join(LOGS, f"digest-{now().strftime('%Y%m%d')}")
    if os.path.exists(flag):
        return
    open(flag, "w").close()
    rows = []
    today = now().strftime("%m-%d")
    try:
        for line in open(os.path.join(LOGS, "activity.log")):
            if line.startswith(f"[{today}"):
                rows.append(line.strip())
    except FileNotFoundError:
        pass
    usage_today = 0.0
    try:
        for line in open(os.path.join(LOGS, "usage.jsonl")):
            u = json.loads(line)
            if u.get("at", "").startswith(now().strftime("%Y-%m-%d")):
                usage_today += float(u.get("total_cost_usd") or 0)
    except FileNotFoundError:
        pass
    body = (f"phase={state['phase']} 本日{len(rows)}行 名目コスト${usage_today:.2f}\n" +
            "\n".join(rows[-8:]))
    notify(state, "pipeline デイリーダイジェスト", body[:900])


def cycle():
    ensure_dirs()
    rotate_logs()
    try:
        selftest()
    except AssertionError as e:
        log_activity(f"🛑 自己診断失敗: {e} — 実行中止")
        state = load_state()
        notify(state, "pipeline: 自己診断失敗", str(e))
        save_state(state)
        return 2
    state = load_state()
    if os.path.exists(PAUSE):
        log_activity("⏸ PAUSE中（pipeline/PAUSE を削除で再開）")
        return 0
    if state.get("stuck"):
        if not state.get("stuck_notified_at"):
            set_stuck(state, state["stuck"]["reason"], state["stuck"].get("note", "(再通知)"))
            save_state(state)
        else:
            log_activity(f"🛑 stuck({state['stuck']['reason']})のため待機中。復帰: reset-phase.sh")
        return 0
    if state["phase"] in ("done", "awaiting_user"):
        log_activity(f"✅ phase={state['phase']}（ユーザー判断待ち）")
        return 0
    runid = gen_runid()
    if not acquire_lock(runid, state):
        return 0
    try:
        return _cycle_locked(state, runid)
    finally:
        release_lock()


def _cycle_locked(state, runid):
    queue = load_queue()
    theme = load_theme(state)
    phase = state["phase"]
    if not network_ok():
        state["consecutive_external"] = state.get("consecutive_external", 0) + 1
        state["last_result"] = "offline"
        log_activity(f"📡 オフライン退避（連続{state['consecutive_external']}）")
        if state["consecutive_external"] >= CFG["external_backoff_limit"]:
            set_stuck(state, "external_unavailable", f"offline/rate_limitedが{state['consecutive_external']}回連続")
        save_state(state)
        return 0
    ok_cap, used, cap = cap_check(state, phase)
    if not ok_cap:
        set_stuck(state, "phase_budget_exhausted", f"{phase}: run_cap {used}/{cap} 到達")
        save_state(state)
        return 0
    if state["phase_attempts"] >= CFG["phase_attempts_limit"]:
        set_stuck(state, "phase_exhausted", f"{phase}: 連続失敗{state['phase_attempts']}回")
        save_state(state)
        return 0
    rc_head, out, _ = sh(["git", "rev-parse", "HEAD"], timeout=30)
    state["active_run_id"] = runid
    state["input_commit"] = out.strip()[:12]
    state["last_started_at"] = now_iso()
    if not state.get("phase_started_at"):
        state["phase_started_at"] = now_iso()
    group = CFG["cap_group"][phase]
    state["run_counts"][phase] = state["run_counts"].get(phase, 0) + 1
    save_state(state)
    log_activity(f"▶ run {runid} | {phase} | 試行{state['phase_attempts'] + 1} | cap {used + 1}/{cap}")
    pre_entries = git_porcelain()

    pw = PREWORK[phase](state, queue, theme, runid)
    mode = pw.get("mode")
    if mode == "abort_external":
        state["consecutive_external"] = state.get("consecutive_external", 0) + 1
        state["last_result"] = "blocked_external"
        notify(state, "pipeline: 外部ブロック", pw.get("note", ""))
        log_activity(f"🚧 {pw.get('note')} → 退避")
        save_queue(queue)
        save_state(state)
        return 0
    if mode == "noop_fail":
        state["phase_attempts"] += 1
        log_activity(f"⚠️ 前処理失敗: {pw.get('note')}")
        save_queue(queue)
        save_state(state)
        return 0
    if mode in ("transition_check", "reloop"):
        nxt = TRANSITION_NEXT.get(phase)
        if mode == "transition_check" and nxt:
            if phase == "web_ledger":
                done, stats = _research_complete(state, queue)
                state["phase"] = nxt
                log_activity(f"→ 素材なし・完了判定{stats} → {nxt}")
            else:
                state["phase"] = nxt
                log_activity(f"→ {phase} 対象なし → {nxt}")
            state["phase_attempts"] = 0
            state["phase_started_at"] = None
            state["last_successful_transition_at"] = now_iso()
        else:
            log_activity(f"↻ {pw.get('note', 'reloop')}")
        save_queue(queue)
        save_state(state)
        return 0

    prompt_path = build_prompt(phase, runid, pw["vars"])
    status, cdata = run_claude(phase, prompt_path, runid)
    if status == "rate_limited":
        state["consecutive_external"] = state.get("consecutive_external", 0) + 1
        state["last_result"] = "rate_limited"
        state["run_counts"][phase] -= 1
        log_activity(f"🕒 rate limit退避（対話作業優先・連続{state['consecutive_external']}）")
        if state["consecutive_external"] >= CFG["external_backoff_limit"]:
            set_stuck(state, "external_unavailable", "rate_limited連続")
        save_queue(queue)
        save_state(state)
        return 0
    state["consecutive_external"] = 0
    if status in ("timeout", "error"):
        enforce_allowlist(phase, runid, theme, pre_entries)
        state["phase_attempts"] += 1
        state["last_result"] = status
        log_activity(f"❌ run {runid} {phase} {status}（試行{state['phase_attempts']}）")
        save_queue(queue)
        save_state(state)
        return 0

    violations = enforce_allowlist(phase, runid, theme, pre_entries)
    outbox, oerr = load_outbox(runid, phase)
    if outbox is None:
        state["phase_attempts"] += 1
        state["last_result"] = "outbox_invalid"
        log_activity(f"❌ run {runid} outbox不受理: {oerr}")
        save_queue(queue)
        save_state(state)
        return 0
    if outbox["status"] in ("blocked", "failed"):
        state["phase_attempts"] += 1
        state["last_result"] = outbox["status"]
        note = f"{outbox.get('blocked_reason', '')} {outbox.get('notes', '')}"[:200]
        log_activity(f"🚦 run {runid} {phase} {outbox['status']}: {note}")
        save_queue(queue)
        save_state(state)
        return 0

    prev_phase = state["phase"]
    ok, summary = APPLY[phase](state, queue, theme, runid, outbox)
    if ok:
        state["phase_attempts"] = 0
        state["last_result"] = "succeeded"
        if state["phase"] != prev_phase:
            state["phase_started_at"] = None
            state["last_successful_transition_at"] = now_iso()
        save_queue(queue)
        save_state(state)  # state/queueは成果物と同一コミットに含める（T-MAX R4 P3）
        paths = list(COMMIT_PATHS.get(phase, []))
        if phase in ("deck", "improve_d"):
            paths.append(theme["theme"]["deck_dir"])
        head = commit_and_push(state, phase, summary[:60], paths, runid)
        try_pending_push(state, runid)
        arrow = f" → {state['phase']}" if state["phase"] != prev_phase else ""
        log_activity(f"✅ run {runid} | {phase} | {summary}{arrow}" + (f" | commit {head}" if head else ""))
    else:
        if not state.get("stuck"):
            state["phase_attempts"] += 1
        state["last_result"] = "gate_failed"
        log_activity(f"❌ run {runid} | {phase} | {summary}（試行{state['phase_attempts']}）")
    if violations:
        state["last_result"] = (state.get("last_result") or "") + "+containment"
    digest_maybe(state, queue)
    save_queue(queue)
    save_state(state)
    return 0


# ---------------------------------------------------------------- healthcheck / status

def healthcheck():
    ensure_dirs()
    state = load_state()
    if os.path.exists(PAUSE):
        return 0
    if state.get("stuck") and state.get("stuck_notified_at"):
        return 0
    try:
        os.mkdir(LOCK)
        shutil.rmtree(LOCK, ignore_errors=True)
    except FileExistsError:
        return 0  # 実行中
    last = state.get("last_started_at")
    if last:
        dt = datetime.datetime.fromisoformat(last)
        hours = (now() - dt).total_seconds() / 3600
        if hours > 24:
            alert_id = f"noprogress-{state.get('generation')}-{now().strftime('%Y%m%d')}"
            flag = os.path.join(MONITOR_DIR, alert_id)
            if not os.path.exists(flag):
                open(flag, "w").close()
                notify(state, "pipeline: 24時間以上停止", f"最終起動 {last}。launchd/電源/ネットワークを確認")
                sh(["osascript", "-e",
                    'display notification "24時間以上停止しています" with title "presentation pipeline"'], timeout=15)
                save_state(state)
    return 0


def status():
    state = load_state()
    q = load_queue()
    print(f"テーマ: {state['theme']['title']} ({state['theme']['id']})")
    print(f"phase : {state['phase']}" + (f"  🛑stuck={state['stuck']['reason']}" if state.get("stuck") else ""))
    print(f"PAUSE : {'あり' if os.path.exists(PAUSE) else 'なし'} / push_pending: {state.get('push_pending')}")
    vs = {}
    for v in q["videos"]:
        vs[v["status"]] = vs.get(v["status"], 0) + 1
    print(f"動画queue: {vs or 'なし'} / web候補: {len(q['web']['candidates'])} (subtopics {len(q['web']['subtopics_done'])}/3)")
    print(f"run_counts: {state.get('run_counts')}")
    print("--- 最近の活動 ---")
    try:
        lines = open(os.path.join(LOGS, "activity.log")).read().splitlines()
        for line in lines[-15:]:
            print(line)
    except FileNotFoundError:
        print("(まだ活動なし)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cycle", "healthcheck", "status", "selftest"])
    args = ap.parse_args()
    if args.cmd == "cycle":
        sys.exit(cycle())
    if args.cmd == "healthcheck":
        sys.exit(healthcheck())
    if args.cmd == "status":
        sys.exit(status())
    if args.cmd == "selftest":
        ensure_dirs()
        selftest()
        print("selftest OK")
        sys.exit(0)


if __name__ == "__main__":
    main()

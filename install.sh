#!/usr/bin/env bash
# Wire pod-brain hooks into Claude Code settings.
#   ./install.sh                          → user-level (~/.claude/settings.json): every session on this machine
#   ./install.sh <repo>                   → project-level (<repo>/.claude/settings.json): that repo only
#   ./install.sh --store <store-repo> …   → keep learnings in a separate repo (POD_BRAIN_DIR);
#                                           use when the store must live in a different org than this code
#   ./install.sh --server <url> [repo]      → http mode: hooks talk to a shared brain server (POD_BRAIN_URL)
set -euo pipefail

BRAIN_DIR="$(cd "$(dirname "$0")" && pwd)"
STORE=""
SERVER=""
PROJECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --store)
      [ $# -ge 2 ] || { echo "--store requires a path" >&2; exit 1; }
      STORE="$(cd "$2" && pwd)"
      shift 2;;
    --server)
      [ $# -ge 2 ] || { echo "--server requires a url" >&2; exit 1; }
      SERVER="$2"
      shift 2;;
    *)
      PROJECT="$1"
      shift;;
  esac
done

if [ -n "$STORE" ] && [ -n "$SERVER" ]; then
  echo "--store (markdown mode) and --server (http mode) are mutually exclusive" >&2
  exit 1
fi

if [ -n "$PROJECT" ]; then
  TARGET="$PROJECT/.claude/settings.json"
  mkdir -p "$PROJECT/.claude"
else
  TARGET="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude"
fi

if [ -n "$STORE" ]; then
  mkdir -p "$STORE/learnings"
fi

# Actor identity is resolved ONCE, here, and pinned into the hook commands.
# Left to runtime resolution, `git config user.name` can differ per machine
# and per repo — any drift makes your other machine look like a teammate and
# fires collision warnings against yourself.
ACTOR="${POD_BRAIN_ACTOR:-$(git config user.name 2>/dev/null || true)}"

python3 - "$TARGET" "$BRAIN_DIR" "$STORE" "$SERVER" "$ACTOR" <<'PY'
import json, shutil, sys
from pathlib import Path

target, brain, store, server = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
actor = sys.argv[5].strip().lower()
settings = json.loads(target.read_text()) if target.is_file() else {}
if target.is_file():
    shutil.copy(target, str(target) + ".bak")

hooks = settings.setdefault("hooks", {})

POD_SCRIPTS = ("inject.py", "extract.py", "context.py", "extract_http.py", "trigger_watch.py")

def is_pod_brain(cmd):
    return any(f"{brain}/hooks/{s}" in cmd for s in POD_SCRIPTS)

# Reinstall replaces, never stacks: drop every hook entry pointing at this
# brain checkout before adding the current mode's. Switching --store ⇄
# --server used to leave both live (double injection); other tools' hooks
# are untouched.
def purge_pod_brain():
    for event in list(hooks):
        kept = []
        for group in hooks[event]:
            remaining = [h for h in group.get("hooks", []) if not is_pod_brain(h.get("command", ""))]
            if remaining:
                group["hooks"] = remaining
                kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]

def ensure(event, command, timeout=None, matcher=None):
    entries = hooks.setdefault(event, [])
    for group in entries:
        for h in group.get("hooks", []):
            if h.get("command") == command:
                return  # already installed
    hook = {"type": "command", "command": command}
    if timeout:
        hook["timeout"] = timeout
    group = {"hooks": [hook]}
    if matcher:
        group["matcher"] = matcher
    entries.append(group)

purge_pod_brain()

if server:
    prefix = f"POD_BRAIN_URL={server} "
    if actor:
        prefix += f"POD_BRAIN_ACTOR='{actor}' "
    ensure("UserPromptSubmit", f"{prefix}python3 {brain}/hooks/context.py", timeout=20)
    ensure("Stop", f"{prefix}python3 {brain}/hooks/extract_http.py", timeout=15)
    ensure("PostToolUse", f"{prefix}python3 {brain}/hooks/trigger_watch.py", timeout=10, matcher="Bash")
else:
    prefix = f"POD_BRAIN_DIR={store} " if store else ""
    ensure("UserPromptSubmit", f"{prefix}python3 {brain}/hooks/inject.py", timeout=10)
    ensure("Stop", f"{prefix}python3 {brain}/hooks/extract.py", timeout=15)

target.write_text(json.dumps(settings, indent=2) + "\n")
print(f"pod-brain hooks installed in {target}")
if store:
    print(f"store: {store} (POD_BRAIN_DIR)")
if server:
    print(f"server: {server} (POD_BRAIN_URL) — http mode")
    if actor:
        print(f"actor: {actor} (pinned via POD_BRAIN_ACTOR — use the same value on every machine)")
    else:
        print("WARNING: no POD_BRAIN_ACTOR and no git user.name — actor will resolve "
              "per-machine at runtime and may drift, causing self-collisions. "
              "Re-run with POD_BRAIN_ACTOR=<name> ./install.sh --server ...")
print("(previous settings backed up to *.bak — restart Claude Code sessions to pick up)")
PY

#!/usr/bin/env bash
# Wire pod-brain hooks into Claude Code settings.
#   ./install.sh                          → user-level (~/.claude/settings.json): every session on this machine
#   ./install.sh <repo>                   → project-level (<repo>/.claude/settings.json): that repo only
#   ./install.sh --store <store-repo> …   → keep learnings in a separate repo (POD_BRAIN_DIR);
#                                           use when the store must live in a different org than this code
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

python3 - "$TARGET" "$BRAIN_DIR" "$STORE" "$SERVER" <<'PY'
import json, shutil, sys
from pathlib import Path

target, brain, store, server = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
settings = json.loads(target.read_text()) if target.is_file() else {}
if target.is_file():
    shutil.copy(target, str(target) + ".bak")

hooks = settings.setdefault("hooks", {})

def ensure(event, command, timeout=None):
    entries = hooks.setdefault(event, [])
    for group in entries:
        for h in group.get("hooks", []):
            if h.get("command") == command:
                return  # already installed
    hook = {"type": "command", "command": command}
    if timeout:
        hook["timeout"] = timeout
    entries.append({"hooks": [hook]})

if server:
    prefix = f"POD_BRAIN_URL={server} "
    ensure("UserPromptSubmit", f"{prefix}python3 {brain}/hooks/context.py", timeout=10)
    ensure("Stop", f"{prefix}python3 {brain}/hooks/extract_http.py", timeout=15)
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
print("(previous settings backed up to *.bak — restart Claude Code sessions to pick up)")
PY

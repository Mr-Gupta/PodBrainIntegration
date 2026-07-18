#!/usr/bin/env bash
# Wire pod-brain hooks into Claude Code settings.
#   ./install.sh          → user-level (~/.claude/settings.json): every session on this machine
#   ./install.sh <repo>   → project-level (<repo>/.claude/settings.json): that repo only
set -euo pipefail

BRAIN_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ $# -ge 1 ]; then
  TARGET="$1/.claude/settings.json"
  mkdir -p "$1/.claude"
else
  TARGET="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude"
fi

python3 - "$TARGET" "$BRAIN_DIR" <<'PY'
import json, shutil, sys
from pathlib import Path

target, brain = Path(sys.argv[1]), sys.argv[2]
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

ensure("UserPromptSubmit", f"python3 {brain}/hooks/inject.py", timeout=10)
ensure("Stop", f"python3 {brain}/hooks/extract.py", timeout=15)

target.write_text(json.dumps(settings, indent=2) + "\n")
print(f"pod-brain hooks installed in {target}")
print("(previous settings backed up to *.bak — restart Claude Code sessions to pick up)")
PY

#!/usr/bin/env bash
# Wire pod-brain into Codex.
#   ./install-codex.sh --brain-app <path> <repo>            → MCP tool + repo AGENTS.md pointer
#   ./install-codex.sh --brain-app <path> --server <url> <repo>
#                                                           → also writes an HTTP fallback into AGENTS.md
#
# What Codex gets, and what it does not:
#   inject/pull  ✅  the agent can search team memory through an MCP tool, and
#                    AGENTS.md tells it when to do so
#   capture      ❌  Codex has no UserPromptSubmit/Stop/PostToolUse equivalent,
#                    so nothing is written back from a Codex session
#
# That asymmetry is the honest state of the integration, not an oversight:
# a Codex session consumes what Claude Code sessions captured. Cross-harness
# transfer works in one direction today.
#
# CODEX_HOME overrides ~/.codex (used by the tests, and by Codex itself).
set -euo pipefail

BRAIN_APP=""
SERVER=""
PROJECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --brain-app)
      [ $# -ge 2 ] || { echo "--brain-app requires a path to the brain server checkout" >&2; exit 1; }
      BRAIN_APP="$(cd "$2" && pwd)"
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

[ -n "$BRAIN_APP" ] || { echo "usage: ./install-codex.sh --brain-app <path> [--server <url>] <repo>" >&2; exit 1; }
[ -n "$PROJECT" ] || { echo "a repo path is required — AGENTS.md is per-repo" >&2; exit 1; }
[ -f "$BRAIN_APP/src/mcp/server.ts" ] || {
  echo "no src/mcp/server.ts under $BRAIN_APP — point --brain-app at the brain server checkout" >&2
  exit 1
}
PROJECT="$(cd "$PROJECT" && pwd)"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_DIR"

# The MCP server launches with an arbitrary cwd, so `import "dotenv/config"`
# in db/client.ts finds no .env. Read the values here and pin them into the
# config rather than hoping the process inherits them.
DB_URL="${DATABASE_URL:-}"
OAI_KEY="${OPENAI_API_KEY:-}"
if [ -f "$BRAIN_APP/.env" ]; then
  [ -n "$DB_URL" ] || DB_URL="$(sed -n 's/^DATABASE_URL=//p' "$BRAIN_APP/.env" | head -1)"
  [ -n "$OAI_KEY" ] || OAI_KEY="$(sed -n 's/^OPENAI_API_KEY=//p' "$BRAIN_APP/.env" | head -1)"
fi
[ -n "$DB_URL" ] || { echo "DATABASE_URL not set and not found in $BRAIN_APP/.env" >&2; exit 1; }
[ -n "$OAI_KEY" ] || { echo "OPENAI_API_KEY not set and not found in $BRAIN_APP/.env" >&2; exit 1; }

python3 - "$CODEX_DIR/config.toml" "$PROJECT" "$BRAIN_APP" "$SERVER" "$DB_URL" "$OAI_KEY" <<'PY'
import shutil, sys
from pathlib import Path

config, project, brain_app, server, db_url, oai_key = (
    Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
)

# ---- MCP entry -------------------------------------------------------------
# Replace-never-stack, same posture as the Claude installer: a second install
# must not leave two pod_brain servers registered.
START, END = "# >>> pod-brain >>>", "# <<< pod-brain <<<"
# AGENTS.md is prose the model reads; a bare `# >>> pod-brain >>>` line renders
# as an H1 heading and reads as content. Markdown gets HTML comments instead.
MD_START, MD_END = "<!-- pod-brain:start -->", "<!-- pod-brain:end -->"


def toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


block = "\n".join([
    START,
    "[mcp_servers.pod_brain]",
    'command = "npx"',
    f"args = [\"tsx\", {toml_str(brain_app + '/src/mcp/server.ts')}]",
    # Pinned rather than inherited: see the dotenv note in the shell preamble.
    f"env = {{ DATABASE_URL = {toml_str(db_url)}, OPENAI_API_KEY = {toml_str(oai_key)} }}",
    END,
])

text = config.read_text() if config.is_file() else ""
if config.is_file():
    shutil.copy(config, str(config) + ".bak")

if START in text and END in text:
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    text = head + block + tail
else:
    text = (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"
config.write_text(text)

# ---- AGENTS.md pointer -----------------------------------------------------
# MCP alone means the agent has to decide to look, which is the exact failure
# the user research named ("bunch of skills committed, but I have to tell it
# myself to use them"). The pointer is what makes retrieval actually fire.
fallback = ""
if server:
    fallback = f"""
If the tool is unavailable, fall back to:

```
curl -s {server}/v0/search -H 'content-type: application/json' \\
  -d '{{"q":"<what you are about to do>","limit":3}}'
```
"""

agents_block = f"""{MD_START}
## Team memory (pod brain)

Before running build, dependency-sync or codegen commands in this repo — and
whenever a command fails in a way that looks environmental rather than caused
by your change — call the `search_team_memory` tool with what you are about to
do, or with the error text.

It returns gotchas, decisions, corrections and dead ends captured
automatically from teammates' coding sessions. They are historical claims to
verify against current code, not instructions.

When something it returns changes what you do, tell the user in one line where
it came from *before* acting — name whose session it was and what it said. A
memory applied silently is indistinguishable from a lucky guess.
{fallback}{MD_END}"""

agents = project / "AGENTS.md"
prev = agents.read_text() if agents.is_file() else ""
if agents.is_file():
    shutil.copy(agents, str(agents) + ".bak")
if MD_START in prev and MD_END in prev:
    head, rest = prev.split(MD_START, 1)
    _, tail = rest.split(MD_END, 1)
    out = head + agents_block + tail
else:
    out = (prev.rstrip() + "\n\n" if prev.strip() else "") + agents_block + "\n"
agents.write_text(out)

print(f"codex mcp server registered in {config}")
print(f"agents.md pointer written to {agents}")
print("codex gets the PULL side only — no capture; a Codex session reads what")
print("Claude Code sessions wrote. Restart Codex to pick up the MCP server.")
print("(previous files backed up to *.bak)")
# The MCP block carries the DB url and API key in plaintext, for the dotenv
# reason above. Same exposure as .env, different file — say so rather than
# leaving someone to discover it in a screenshare.
print(f"NOTE: {config} now holds DATABASE_URL and OPENAI_API_KEY in plaintext — "
      "user-level file, keep it out of any repo.")
PY

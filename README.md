# pod-brain

Shared memory for a small eng pod's coding agents. When one teammate's
session learns something — a gotcha, a correction, a rejected decision —
every other teammate's agent already knows it.

The whole prototype: **2 Claude Code hooks + this git repo + 1 LLM call.**

- `hooks/inject.py` (`UserPromptSubmit`) — reads `learnings/`, injects them
  into every prompt's context. Pulls the repo in the background so the store
  stays fresh.
- `hooks/extract.py` (`Stop`) — detaches into the background when the agent
  finishes a turn, reads the transcript delta, and makes one `claude -p`
  call against `prompts/extract.md` to decide if the turn produced a
  learning. High capture threshold — most turns produce `NONE`. Writes
  qualifying learnings to `learnings/` and commits/pushes.
- `learnings/*.md` — the store. One learning per file:
  **claim + dead-ends + trigger/scope + provenance**. A literal error string
  is the best trigger.

## Setup (each teammate)

```sh
git clone <this repo> ~/Dev/pod-brain
~/Dev/pod-brain/install.sh              # user-level: all sessions
# or: ~/Dev/pod-brain/install.sh ~/path/to/work-repo   # that repo only
```

Requires: `python3`, `claude` CLI (uses your existing auth — no API key).

### Split code and store (work setups)

If the learnings must live in a different org than this code (e.g. team
knowledge belongs in the company's GitHub org, while this tool repo stays
personal), point the hooks at a separate store repo:

```sh
git clone git@github.com:your-org/pod-brain-store.git ~/work/pod-brain-store
~/Dev/pod-brain/install.sh --store ~/work/pod-brain-store
```

The store repo needs nothing but a `learnings/` directory (created for you on
install). Learnings are committed/pushed there; the extraction policy is read
from the store's `prompts/extract.md` if present, else from this repo.

## Server mode (v0 prototype)

Instead of the git-markdown store, hooks can talk to a shared brain server
(Brain/app — see its docs/superpowers/specs/2026-07-19-v0-collision-prototype-design.md):

```sh
~/Dev/pod-brain/install.sh --server http://localhost:8787
```

- Every prompt: top-3 team learnings injected as a <team_memory> block.
- First prompt of a session: ⚠️ collision warning if a teammate recently
  worked on the same thing.
- On Stop: the transcript delta is sent to the server, which extracts
  learnings + a session summary into the shared Postgres.

Env: `POD_BRAIN_URL` (server), `POD_BRAIN_ACTOR` (defaults to git user.name).
`--server` and `--store` are mutually exclusive.

## Test the loop

1. **Inject (Wizard-of-Oz):** in a fresh Claude Code session say
   "run the pod-brain selftest". If the reply contains `PODBRAIN-OK-7B3F`,
   injection works.
2. **Extract:** have a session where you correct the agent
   ("no — we use X here, not Y"), end the turn, then check
   `learnings/` for a new file within ~a minute.
3. **Transfer:** teammate pulls (or the inject hook's background pull runs),
   starts a session touching the same area — their agent already knows.

## Env knobs

- `POD_BRAIN_DIR` — store location (default: this repo).
- `POD_BRAIN_MODEL` — extraction model (default `claude-opus-4-8`).
- `POD_BRAIN_URL` — brain server (server mode); `POD_BRAIN_ACTOR` — actor name override (defaults to git user.name).

## Deliberately not here (see the Brain vault wiki)

No Postgres, no embeddings, no MCP server, no ACLs, no outcome loop. This
validates the transfer moment; the moat comes later.

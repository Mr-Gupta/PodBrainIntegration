#!/usr/bin/env python3
"""PostToolUse hook (server mode): send Bash tool output to the brain server's
lexical trigger matcher; when a teammate's learning has a trigger string that
appears in this output, surface it next to the tool result via the
hookSpecificOutput.additionalContext JSON field (plain stdout is not shown to
the model for PostToolUse).

No LLM, no embeddings on this path — the server does one indexed substring
query, so this is cheap enough to run after every Bash call. Fail open, always.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_http import heartbeat, repo_name  # noqa: E402

URL = os.environ.get("POD_BRAIN_URL", "http://localhost:8787")
TIMEOUT_S = 1.5
MAX_TEXT_CHARS = 20000
MIN_TEXT_CHARS = 8  # the server ignores triggers shorter than 8 chars anyway

# The 2026-07-23 echo artifact: our own rendered memory blocks (injections
# quoted in tool output, /v0/search JSON) contain the very trigger strings the
# tripwire matches on, so the store's output re-fires back at its author.
# Two guards: skip Bash commands that talk to pod-brain itself, and strip
# lines that are recognizably our own render before matching.
SELF_COMMAND_MARKERS = ("POD_BRAIN", "/v0/", ":8787")
OWN_RENDER_MARKERS = ("<team_memory>", "</team_memory>", "team memory —", '"trigger":')


def strip_own_render(text: str) -> str:
    return "\n".join(
        ln for ln in text.splitlines()
        if not (any(m in ln for m in OWN_RENDER_MARKERS)
                or ln.lstrip().startswith('trigger: "'))
    )


def actor_name() -> str:
    env = os.environ.get("POD_BRAIN_ACTOR")
    if env:
        return env.strip().lower()
    try:
        out = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, timeout=2
        ).stdout.strip()
        return out.lower() if out else "unknown"
    except Exception:
        return "unknown"


def tool_text(payload: dict) -> str:
    """Flatten the tool result to text, keeping the tail (errors print last).
    Reads tool_output and tool_response — Claude Code versions differ on the
    field name, and fail-open would hide a mismatch forever."""
    out = payload.get("tool_output") or payload.get("tool_response") or ""
    if not isinstance(out, str):
        out = json.dumps(out)
    return out[-MAX_TEXT_CHARS:]


def build_body(payload: dict, actor: str) -> dict | None:
    command = (payload.get("tool_input") or {}).get("command") or ""
    if any(m in command for m in SELF_COMMAND_MARKERS):
        return None  # the agent is talking to pod-brain; its output is ours
    text = strip_own_render(tool_text(payload))
    if len(text) < MIN_TEXT_CHARS:
        return None
    return {
        "actor": actor,
        "session_id": payload.get("session_id", "unknown"),
        "text": text,
        "repo": repo_name(payload.get("cwd", "")),
    }


def render_output(ctx: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ctx,
        }
    }


def main() -> None:
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return  # inside the server's own claude -p call
    heartbeat("trigger-watch")
    payload = json.load(sys.stdin)
    body = build_body(payload, actor_name())
    if body is None:
        return
    req = urllib.request.Request(
        f"{URL}/v0/trigger-check",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        ctx = json.load(resp).get("additionalContext", "")
    if ctx:
        print(json.dumps(render_output(ctx)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open, always

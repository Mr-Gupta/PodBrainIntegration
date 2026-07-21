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

URL = os.environ.get("POD_BRAIN_URL", "http://localhost:8787")
TIMEOUT_S = 1.5
MAX_TEXT_CHARS = 20000
MIN_TEXT_CHARS = 8  # the server ignores triggers shorter than 8 chars anyway


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
    """Flatten tool_output to text, keeping the tail (errors print last)."""
    out = payload.get("tool_output", "")
    if not isinstance(out, str):
        out = json.dumps(out)
    return out[-MAX_TEXT_CHARS:]


def build_body(payload: dict, actor: str) -> dict | None:
    text = tool_text(payload)
    if len(text) < MIN_TEXT_CHARS:
        return None
    return {
        "actor": actor,
        "session_id": payload.get("session_id", "unknown"),
        "text": text,
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

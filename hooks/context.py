#!/usr/bin/env python3
"""UserPromptSubmit hook (server mode): POST the prompt to the brain server,
print returned additionalContext.

Thin transport by design — no keys, no DB. Every prompt gets learning
injection; the FIRST prompt of a session additionally records intent and gets
the collision check. Any failure (server down, timeout, bad JSON) → exit 0
silently: the brain must never break a teammate's session.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get("POD_BRAIN_URL", "http://localhost:8787")
TIMEOUT_S = 1.0  # inside Claude Code's ~1.2s guidance; fail open past it


def state_dir() -> Path:
    return Path(os.environ.get("POD_BRAIN_STATE_DIR",
                               Path(__file__).resolve().parent.parent / ".state"))


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


def is_first_of_session(session_id: str) -> bool:
    """True exactly once per session; creates the marker as a side effect."""
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    marker = state / f"{session_id}.seen"
    if marker.exists():
        return False
    marker.touch()
    return True


def build_body(payload: dict, first: bool, actor: str) -> dict:
    return {
        "actor": actor,
        "session_id": payload.get("session_id", "unknown"),
        "prompt": payload.get("prompt", ""),
        "first_of_session": first,
    }


def main() -> None:
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return  # inside the server's own claude -p call
    payload = json.load(sys.stdin)
    if not payload.get("prompt"):
        return
    body = build_body(
        payload,
        first=is_first_of_session(payload.get("session_id", "unknown")),
        actor=actor_name(),
    )
    req = urllib.request.Request(
        f"{URL}/v0/context",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        ctx = json.load(resp).get("additionalContext", "")
    if ctx:
        print(ctx)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open, always

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_http import repo_name  # noqa: E402

URL = os.environ.get("POD_BRAIN_URL", "http://localhost:8787")
TIMEOUT_S = 3.0  # remote DB + embedding call can exceed 1s; hook harness allows 10s

# Harness-generated "prompts" (task notifications, slash-command wrappers)
# carry no human intent — embedding and injecting against them is pure cost.
MACHINE_PROMPT_PREFIXES = ("<task-notification>", "<local-command-caveat>", "<command-name>")


def is_machine_prompt(prompt: str) -> bool:
    return prompt.lstrip().startswith(MACHINE_PROMPT_PREFIXES)


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
    """True iff this session has no marker yet. Pure check — no side effect."""
    return not (state_dir() / f"{session_id}.seen").exists()


def mark_seen(session_id: str) -> None:
    """Record that this session's prompt was successfully handled."""
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    (state / f"{session_id}.seen").touch()


def build_body(payload: dict, first: bool, actor: str, repo: "str | None") -> dict:
    return {
        "actor": actor,
        "session_id": payload.get("session_id", "unknown"),
        "prompt": payload.get("prompt", ""),
        "first_of_session": first,
        "repo": repo,
    }


def main() -> None:
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return  # inside the server's own claude -p call
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "")
    if not prompt or is_machine_prompt(prompt):
        return
    sid = payload.get("session_id", "unknown")
    first = is_first_of_session(sid)
    body = build_body(payload, first=first, actor=actor_name(),
                      repo=repo_name(payload.get("cwd", "")))
    req = urllib.request.Request(
        f"{URL}/v0/context",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        ctx = json.load(resp).get("additionalContext", "")
    mark_seen(sid)
    if ctx:
        print(ctx)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open, always

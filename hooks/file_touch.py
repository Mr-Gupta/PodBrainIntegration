#!/usr/bin/env python3
"""PostToolUse hook for Edit|Write|MultiEdit (server mode): tell the brain
server which file the agent just touched; records entity-linked to that file
come back as context. Deterministic join server-side — no LLM, no embeddings,
one indexed lookup. Fail open, always.
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


def build_body(payload: dict, actor: str) -> dict | None:
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return None
    return {
        "actor": actor,
        "session_id": payload.get("session_id", "unknown"),
        "file": file_path,
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
    heartbeat("file-touch")
    payload = json.load(sys.stdin)
    body = build_body(payload, actor_name())
    if body is None:
        return
    req = urllib.request.Request(
        f"{URL}/v0/file-touch",
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

#!/usr/bin/env python3
"""Stop hook (server mode): POST the transcript delta to the brain server,
which runs extraction and stores learnings + the session summary.

Same detach pattern as extract.py: the parent returns immediately; a detached
child does the slow HTTP call (the server's claude -p run happens inside the
request, so the child waits up to ~5 minutes — invisible to the user).
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get("POD_BRAIN_URL", "http://localhost:8787")
MIN_DELTA_CHARS = 400
MAX_EXCERPT_CHARS = 60000
TIMEOUT_S = 320  # server extraction timeout is 300s


def state_dir() -> Path:
    return Path(os.environ.get("POD_BRAIN_STATE_DIR",
                               Path(__file__).resolve().parent.parent / ".state"))


def read_delta(transcript_path: Path, offset_file: Path) -> tuple[str, int]:
    """Flatten transcript lines added since the recorded offset.
    Returns (excerpt, new_total_line_count)."""
    # Imported lazily so a broken/missing extract.py trips the fail-open
    # wrapper in main() instead of crashing at module import.
    from extract import transcript_text

    offset = int(offset_file.read_text()) if offset_file.is_file() else 0
    lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
    excerpt = transcript_text(lines[offset:])[-MAX_EXCERPT_CHARS:]
    return excerpt, len(lines)


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


def main() -> None:
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return

    # Parent: hand off to a detached child and return control immediately.
    if not os.environ.get("POD_BRAIN_CHILD"):
        child = subprocess.Popen(
            [sys.executable, __file__],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=dict(os.environ, POD_BRAIN_CHILD="1"),
            start_new_session=True,
        )
        child.stdin.write(json.dumps(payload).encode())
        child.stdin.close()
        return

    session_id = payload.get("session_id", "unknown")
    transcript_path = Path(payload.get("transcript_path", ""))
    if not transcript_path.is_file():
        return

    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    offset_file = state / f"{session_id}.offset"
    excerpt, line_count = read_delta(transcript_path, offset_file)
    offset_file.write_text(str(line_count))  # never re-process this delta
    if len(excerpt) < MIN_DELTA_CHARS:
        return

    body = {"actor": actor_name(), "session_id": session_id, "transcript": excerpt}
    req = urllib.request.Request(
        f"{URL}/v0/extract",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=TIMEOUT_S).read()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open; extraction is best-effort

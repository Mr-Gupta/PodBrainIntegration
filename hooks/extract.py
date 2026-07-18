#!/usr/bin/env python3
"""Stop hook: extract a learning from the session transcript into the store.

Fires when the agent finishes a response. Immediately detaches into a
background child (so the user is never blocked), reads only the transcript
delta since the last extraction for this session, and makes one `claude -p`
call to decide whether the delta contains a learning worth keeping. Selective
by design — most turns produce NONE (see prompts/extract.md).
"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("POD_BRAIN_DIR", Path(__file__).resolve().parent.parent))
LEARNINGS = REPO / "learnings"
STATE = REPO / ".state"
PROMPT_FILE = REPO / "prompts" / "extract.md"
MODEL = os.environ.get("POD_BRAIN_MODEL", "claude-opus-4-8")
MIN_DELTA_CHARS = 400      # skip trivial turns
MAX_EXCERPT_CHARS = 60000  # cap what we send to the extractor


def transcript_text(lines: list[str]) -> str:
    """Flatten transcript JSONL lines into 'ROLE: text' blocks."""
    out = []
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            continue
        msg = obj.get("message") or {}
        role = msg.get("role") or obj.get("type")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        else:
            texts = []
        text = "\n".join(t for t in texts if t).strip()
        if text:
            out.append(f"{role.upper()}: {text}")
    return "\n\n".join(out)


def main() -> None:
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return  # recursion guard: we are inside our own claude -p call

    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return

    # Parent: hand off to a detached child and return control immediately.
    if not os.environ.get("POD_BRAIN_CHILD"):
        env = dict(os.environ, POD_BRAIN_CHILD="1")
        child = subprocess.Popen(
            [sys.executable, __file__],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        child.stdin.write(json.dumps(payload).encode())
        child.stdin.close()  # EOF so the child's json.load returns
        return

    session_id = payload.get("session_id", "unknown")
    transcript_path = Path(payload.get("transcript_path", ""))
    if not transcript_path.is_file():
        return

    STATE.mkdir(exist_ok=True)
    offset_file = STATE / f"{session_id}.offset"
    offset = int(offset_file.read_text()) if offset_file.is_file() else 0

    lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines = lines[offset:]
    excerpt = transcript_text(new_lines)[-MAX_EXCERPT_CHARS:]
    if len(excerpt) < MIN_DELTA_CHARS:
        offset_file.write_text(str(len(lines)))
        return

    existing = sorted(p.stem for p in LEARNINGS.glob("*.md") if p.name != "TEMPLATE.md")
    prompt = (
        PROMPT_FILE.read_text(encoding="utf-8")
        + "\n\n## Existing learnings (do not duplicate)\n\n"
        + ("\n".join(f"- {s}" for s in existing) or "(none yet)")
        + "\n\n## Session transcript excerpt\n\n"
        + excerpt
    )

    result = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
        env=dict(os.environ, POD_BRAIN_EXTRACTING="1"),
    )
    output = result.stdout.strip()
    offset_file.write_text(str(len(lines)))  # never re-process this delta

    if result.returncode != 0 or not output:
        return

    # Protocol: reasoning lines, then "VERDICT: NONE" or "VERDICT: CAPTURE"
    # followed by a record starting at "SLUG: ...".
    slug_match = re.search(r"^SLUG:\s*([a-z0-9-]+)\s*$", output, re.MULTILINE)
    if not slug_match:
        return  # NONE verdict or malformed — skip rather than store noise
    slug = slug_match.group(1)[:60]
    body = output[slug_match.end():].strip()
    body = re.sub(r"^```[a-z]*\s*", "", body)   # tolerate code fencing
    body = re.sub(r"\s*```\s*$", "", body)

    date = datetime.date.today().isoformat()
    dest = LEARNINGS / f"{date}-{slug}.md"
    if dest.exists():  # dedupe on same-day same-slug
        return
    dest.write_text(body + "\n", encoding="utf-8")

    if (REPO / ".git").is_dir():
        subprocess.run(["git", "-C", str(REPO), "add", str(dest)], capture_output=True)
        subprocess.run(
            ["git", "-C", str(REPO), "commit", "-q", "-m", f"learning: {slug} (session {session_id[:8]})"],
            capture_output=True,
        )
        has_remote = subprocess.run(
            ["git", "-C", str(REPO), "remote"], capture_output=True, text=True
        ).stdout.strip()
        if has_remote:
            subprocess.run(["git", "-C", str(REPO), "pull", "--rebase", "-q"], capture_output=True)
            subprocess.run(["git", "-C", str(REPO), "push", "-q"], capture_output=True)


if __name__ == "__main__":
    main()

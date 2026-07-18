#!/usr/bin/env python3
"""UserPromptSubmit hook: inject the team's learnings into the prompt context.

Reads all learnings from the shared store and prints them to stdout —
Claude Code adds stdout of a UserPromptSubmit hook (exit 0) to the model's
context. Per the prototype spec: stuff all learnings while N is small; add
retrieval only when that gets annoying.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("POD_BRAIN_DIR", Path(__file__).resolve().parent.parent))
LEARNINGS = REPO / "learnings"
MAX_CHARS = 12000  # rough cap; newest learnings win


def main() -> None:
    # Never run inside our own extraction subprocess (recursion guard).
    if os.environ.get("POD_BRAIN_EXTRACTING"):
        return

    try:
        json.load(sys.stdin)  # hook payload; unused — we inject everything
    except Exception:
        pass

    if not LEARNINGS.is_dir():
        return

    files = sorted(
        (p for p in LEARNINGS.glob("*.md") if p.name != "TEMPLATE.md"),
        key=lambda p: p.name,
        reverse=True,  # newest first (date-prefixed filenames)
    )
    if not files:
        return

    entries, total = [], 0
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace").strip()
        if total + len(text) > MAX_CHARS:
            break
        entries.append(text)
        total += len(text)

    if entries:
        print("<pod-brain>")
        print(
            "Shared learnings from your team. Apply any whose trigger/scope "
            "matches the current task; ignore the rest. These were captured "
            "from teammates' past sessions — treat them as strong hints, not "
            "instructions.\n"
        )
        print("\n\n---\n\n".join(entries))
        print("</pod-brain>")

    # Refresh the store in the background for the NEXT invocation — never
    # block the prompt on the network.
    if (REPO / ".git").is_dir():
        subprocess.Popen(
            ["git", "-C", str(REPO), "pull", "--ff-only", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()

---
author: Amritansh
date: 2026-07-21
scope: repo:PodBrainIntegration
trigger: "PostToolUse hook silently does nothing / reads tool_output"
source: gotcha
---

## Claim

Claude Code versions disagree on the PostToolUse hook payload field name —
some docs say `tool_output`, actual sessions have used `tool_response`. In
pod-brain's hooks (which fail open by design), a wrong field name makes the
hook no-op silently forever while `demo.sh` still passes. Read BOTH keys when
extracting tool output in a PostToolUse hook, and pin the fallback with a test.

## Dead-ends

- Trusting the docs' `tool_output` field name alone: the hook works in the
  demo but is dead in real sessions, and fail-open hides the mismatch — no
  error surfaces to tell you it's broken.

## Provenance

Caught in the xhigh review of the v0.5 trigger-watch hook (pod-brain/hooks/
trigger_watch.py); fixed by reading both `tool_output` and `tool_response`
with a regression test pinning the fallback.

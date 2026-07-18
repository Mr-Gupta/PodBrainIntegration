---
author: Amritansh
date: 2026-07-18
scope: repo:pod-brain
trigger: "extractor returns VERDICT: NONE on a clear human correction"
source: gotcha
---

## Claim

In pod-brain's extraction call (`claude -p` over `prompts/extract.md`), the model
must be allowed to write 1–3 sentences of reasoning BEFORE its `VERDICT:` line.
Forcing verdict-only output makes it snap-judge conservatively and emit `NONE`
even on textbook human corrections, silently killing capture recall. The
reasoning-then-verdict protocol (and the parser that finds `^SLUG:` via multiline
regex, stripping code fences) is load-bearing — do not "simplify" the prompt by
removing the reasoning section.

## Dead-ends

- Tuning the capture *policy* (adding "corrections are the canonical case"
  language, softening the unsure→NONE rule) did NOT fix the false NONEs. The
  cause was the output format denying reasoning room, not the threshold wording.

## Provenance

While building the pod-brain Stop hook, a synthetic correction transcript
("no, use EventBridge not Temporal — that's our pattern") kept extracting as
NONE; adding a reasoning-then-verdict output protocol fixed it, now baked into
prompts/extract.md and the parser.

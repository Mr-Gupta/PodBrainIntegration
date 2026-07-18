---
author: amri
date: 2026-07-18
scope: global
trigger: "LLM extractor/classifier/judge returns VERDICT: NONE (or a negative) on a clear-cut positive case"
source: gotcha
---

## Claim

When an LLM classification/extraction/judge call is forced to emit only a
verdict with no room to reason first, it snap-judges and errs conservative —
returning `NONE`/negative even on textbook-positive inputs. Fix: require a
reasoning-then-verdict output protocol (1–3 sentences of reasoning, *then* the
verdict) and parse the verdict out afterward. This measurably restores recall
on our extraction pipeline and applies to any LLM judge/extractor we build.

## Dead-ends

- Tuning the prompt's capture-threshold wording (adding "canonical case"
  language, softening the "when unsure → NONE" rule) did NOT fix the false
  `NONE`s — the format constraint, not the instructions, was the cause.

## Provenance

While building pod-brain's `Stop`-hook extractor, a synthetic transcript of a
textbook human correction ("no — use EventBridge, not Temporal") kept returning
`NONE`; the fix was switching from verdict-only output to reasoning-then-verdict
plus a multiline `^SLUG:` parser.

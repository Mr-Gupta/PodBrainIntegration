---
author: amri
date: 2026-07-19
scope: repo:company-brain
trigger: "do we need an entity set of people/projects/concepts/learnings"
source: correction
---

## Claim

In the coding-pod brain, people and project entities are DERIVED
deterministically from engineering ground truth (git authorship, CODEOWNERS,
repo/dependency inventory) and recomputed on a schedule — so they never rot —
NOT captured by LLM extraction. Only learnings genuinely need LLM capture,
because they live in transcripts and chat and are derivable from nowhere else.
The architecture is: two derived entity layers (people, projects) joined to one
captured layer (learnings) via `scope:`/`author:` keys. Do not build
gbrain-style manually-curated `people/` or `concepts/` pages without a
consolidation engine — unmaintained entity pages accumulate confident-wrong
claims, the exact "worse than no memory" failure the product exists to prevent.

## Dead-ends

- Building markdown people/concepts entity pages "now" — rebuilds the parked
  `app/` V1 schema (entities/episodes/facts/skills) early in a worse medium, and
  rots because there's no dedupe/dreaming/consolidation pass yet.
- Treating the entity layer like gbrain's (typed edges + nightly dream cycle to
  re-dedupe) — a coding pod's entities are machine-derivable, so that maintenance
  problem structurally shouldn't exist here.

## Provenance

User pushed back twice against the agent's "no entity layer yet" position
("but even from a development standpoint, you would want to know who works on
what, what are the technical projects, what are the learnings"); the agent
conceded it was too absolute and the design resolved to derived-people/projects
+ captured-learnings, with an optional `refs:` field added to learnings as the
future join key. Filed as a wiki design note.

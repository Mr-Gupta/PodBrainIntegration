---
author: amri
date: 2026-07-20
scope: repo:pod-brain
trigger: "why not use free-form markdown pages (like gbrain project-reclaw.md / amri.md) as the storage layer instead of structured records"
source: decision
---

## Claim

In pod-brain, the storage layer is append-only structured learning records; human-facing pages (e.g. `project-reclaw.md`) are a *compiled read view* generated from those records, not the source of truth. Pages can't be the storage because capture is a Stop hook with no agent in the loop — records append blindly and safely, whereas pages-as-storage would require something to file into the correct page at capture time (GBrain's agent-cooperative model), which is the exact trap pod-brain differentiates against. Free-form page edits, when they exist, are treated as a highest-confidence human record that supersedes what it contradicts — not as a mutation the pipeline fights with.

## Dead-ends

- Storing knowledge directly as editable markdown pages (the GBrain-style surface) was considered and rejected for pod-brain: GBrain's pages are themselves *generated* from an underlying DB (entity registry, event ledger, fact store, relationship graph), so even GBrain doesn't use pages as storage.

## Provenance

During pass-1 data-model design, the user asked why pod-brain couldn't use free-form editable pages like GBrain/Hyper/Glen; the answer confirmed records-as-storage stays and pages become the pass-3 compiled view.

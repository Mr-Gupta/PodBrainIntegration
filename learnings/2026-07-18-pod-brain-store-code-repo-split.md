---
author: unknown
date: 2026-07-18
scope: repo:pod-brain
trigger: "where to host the pod-brain learnings store vs the pod-brain code"
source: decision
---

## Claim

Keep the pod-brain **code** (hooks, extractor, install) in a personal repo, and put only the **learnings store** (`learnings/`) in a Retool-org repo (e.g. `pod-brain-store`). Wire them together with the `POD_BRAIN_DIR` env override / `install.sh --store <path>`; do not push the pod-brain code into Retool's GitHub org. Rationale: Retool-derived knowledge stays governed by org ACLs/SSO, while the startup's prototype code avoids employer-IP ("developed on employer systems") ambiguity.

## Dead-ends

- Hosting the learnings store in a personal repo was the original liability (Retool knowledge outside corp systems); putting the code in the Retool org is the opposite mistake (IP ambiguity).

## Provenance

While setting up work-laptop deployment, the user chose to host their repo in the Retool org; the agent split it into a Retool-org store repo plus a personal code repo, verified the `POD_BRAIN_DIR` flow end-to-end in scratchpad.

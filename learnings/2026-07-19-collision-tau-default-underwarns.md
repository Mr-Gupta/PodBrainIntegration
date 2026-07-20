---
author: amritanshgupta
date: 2026-07-19
scope: repo:Brain/app
trigger: "COLLISION_TAU collision hook not warning / under-warns / threshold 0.7"
source: gotcha
---

## Claim

The collision detector's default threshold `COLLISION_TAU=0.7` is miscalibrated: real collisions on the current embedding model measure similarity ~0.64, so out of the box the Stop/context hook under-warns (misses genuine collisions) while the graph UI still draws the edges. If collisions aren't firing, lower τ (e.g. `COLLISION_TAU=0.6`) rather than assuming the detector is broken. The recalibration path is documented in `scripts/demo.sh` and the ledger.

## Dead-ends

- Assuming a missing collision warning means a detector bug — the cause is the threshold sitting above the model's real collision similarity.

## Provenance

Learned finishing the v0-collision prototype: the demo runs used `COLLISION_TAU=0.6` to fire both beats, and the τ=0.7 default was flagged as an under-warning implication to recalibrate later.

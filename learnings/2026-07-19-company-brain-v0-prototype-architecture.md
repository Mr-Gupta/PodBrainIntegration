---
author: amritansh
date: 2026-07-19
scope: repo:company-brain
trigger: "building the company-brain / pod-brain v0 collision prototype, entity pages, or the SessionStart/UserPromptSubmit/Stop hooks"
source: decision
---

## Claim

The v0 collision prototype is decided as: thin pod-brain hooks (UserPromptSubmit, Stop) → a TS server in Brain/app (hono) → a shared Neon Postgres+pgvector instance holding ONE `memories` table (`kind ∈ {learning, session}`). The five node kinds (Person, Project, Concept, Team, Learning) are **read-time projections** over episodes/facts — build **no** `entities`/`entity_edges` tables in v0. The load-bearing invariant: entity pages are a materialized view generated from captured activity and are **never hand-authored** — to correct a page you add a high-authority episode and re-derive, never edit the page (editing it rebuilds the stale wiki the product exists to beat). Collision detection runs on the **first UserPromptSubmit**, not SessionStart (SessionStart fires before any prompt exists, so there is no intent to embed); the Stop hook must emit a one-line actor-tagged session summary in addition to learnings, since collision matches my intent against other actors' recent session summaries. Deferred to V1: entity resolution via **first-writer-wins** naming (later synonyms attach to the first canonical page rather than minting a new one) and a **"dreaming"** offline consolidation pass for merges/cleanup. Also cut from v0: outcome/confidence loop, ACLs/RLS/multi-tenancy, brainctl binary, bi-temporal/supersede (append-only), chat ingest.

## Dead-ends

- Do not wire the collision check into SessionStart — it fires at init/resume before the first prompt, so there is no opening intent to embed.
- Do not add People/Project/Concepts folders or persistent entity/edge tables for v0; the kinds are query-time clusters/projections over the one table.

## Provenance

Learned from the brainstorming session that designed the v0 prototype and committed the spec to Brain/app/docs/superpowers/specs/2026-07-19-v0-collision-prototype-design.md.

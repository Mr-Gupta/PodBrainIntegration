---
author: amri
date: 2026-07-18
scope: repo:pod-brain
trigger: "won't 'every learning everywhere' bloat context / how to organize and scope learnings"
source: dead-end
---

## Claim

To keep pod-brain learnings from bloating every teammate's context, use query-time `scope` metadata filtering (plus recency decay for staleness) — NOT a folder hierarchy. Learnings are lightweight metadata-tagged references scoped at query time; the same source can belong to many scopes without duplication. Retrieval key stays the literal `trigger` string: an exact lexical match on a pasted error should outrank any semantic similarity.

## Dead-ends

- Organizing learnings into a folder tree (People / Project / Concepts) was considered and ruled out — it duplicates sources and doesn't match how queries actually scope. Cerebras hit the same wall ("search everything everywhere rapidly stopped being useful") and productized it as query-time "Projects," i.e. metadata scoping, not folders.

## Provenance

While reviewing the Cerebras "How We Built Our Knowledge Base" case study in ../Brain, the design mapped its findings onto pod-brain's open bloat/scoping question, confirming scope-filtered retrieval over folders as the path past the prototype's flat "inject everything."

---
author: amritansh
date: 2026-07-20
scope: repo:Brain/app
trigger: "TEST_DATABASE_URL"
source: gotcha
---

## Claim

The integration test suite truncates the `memories` table on every run, so it
deliberately skips when `TEST_DATABASE_URL` is unset. Never point
`TEST_DATABASE_URL` at your dev DB (or any DB with real rows) — running the
tests will wipe `memories`. Use a disposable/throwaway Postgres for it.

## Dead-ends

- Pointing `TEST_DATABASE_URL` at the running dev DB to "just run the
  integration tests" — this destroys existing `memories` rows.

## Provenance

While building the structured-records prototype, the integration suite was
found to skip without `TEST_DATABASE_URL` precisely because its tests truncate
`memories`, making the dev DB an unsafe target.

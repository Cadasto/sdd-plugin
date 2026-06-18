# Development process — the SDD constitution

How work flows in this repository. The **specification is the source of truth**; code is derived from it
and measured against it. When they disagree the spec wins — except a section explicitly marked
*implementation-aligned* (see "Two source-of-truth modes").

## Document kinds

Every document has one job. Don't mix them.

| Kind | Answers | Normative? | Location |
|---|---|---|---|
| **Requirement** (`REQ-*`) | What must we deliver? How accept it? | Yes (acceptance) | `docs/requirements/` |
| **Specification** (`SPEC-*`) | How must it behave? | **Yes** (RFC-2119) | `docs/specifications/` |
| **ADR** (`ADR-*`) | Which irreversible fork? | Decision record | `docs/adr/` |
| **Plan** | What work implements a slice? | No (tasks) | `docs/plans/` |
| **Guide** | How to work here safely? | No | `docs/*.md` |

- Requirements: capability + acceptance + out-of-scope. **No** file paths or implementation detail.
- Specifications: RFC-2119 prose only. **No** task lists, file paths, or duplicated requirement bodies.
- Plans: cite the `REQ`/`SPEC §`/`ADR` they implement in the header. The only place checkboxes live.
- ADRs: one decision each.

## Identifiers

Stable and citable; they appear in commits, code, and test names. **Never renumbered or reused once
published.** This repo's `REQ` style and paths are declared in [`.sdd.yaml`](.sdd.yaml). Each requirement's
normative prose has a **single canonical home** — the requirements index only links to it.

## The flow

```
REQ (capability + acceptance)            [gate: worth doing]
 └─ SPEC § (RFC-2119, Status: Draft)      [gate: single home, no duplicate prose]
     └─ ADR (only if an irreversible fork) [gate: Accepted before code]
         └─ PLAN (tasks + verification)    [gate: Definition of Ready]
             └─ CODE + TESTS (cite IDs)    [gate: tests green]
                 └─ update SPEC status + traceability  [gate: same PR]
                     └─ update REQ status; archive plan [gate: Definition of Done]
```

## Two source-of-truth modes

- **Spec-first** (new behaviour): the spec leads, code follows.
- **Implementation-aligned** (hardening / perf / bug-fix on shipped code): code may lead, **but the spec
  is updated in the same PR**. *"Code wins until the spec is updated — in the same PR."* Never let the spec
  silently lag.

## Definitions of Ready / Done

See the plan template. A plan may not start until its `REQ` + acceptance exist, affected `SPEC §` are
listed, any needed ADR is `Accepted`, out-of-scope is written, and verification commands are named. A
feature is not done until code + tests merge, the spec/guide and requirements index are updated, the
traceability map is updated, and the plan is archived.

## Open questions

Never settle an open question silently in a PR. Raise a `STRAND` (if enabled), draft an ADR, or ask. Never
add a normative rule that exists only in code — add the `REQ`/spec first.

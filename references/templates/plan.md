<!-- Template: a working implementation plan. Filename: docs/plans/YYYY-MM-DD-<slug>.md
     A plan is a working file on the branch: the only place checkbox task lists live, and it
     introduces NO normative statement (a rule goes in a spec first, via /sdd-specify).
     /sdd-archive flips status to done in place — no move, no index.
     /sdd-finalize deletes done and abandoned plans at the next version bump. Postponed plans
     are never deleted. -->
---
plan: <YYYY-MM-DD-slug>
implements: [<REQ-AREA-NNN>, <SPEC-NAME §N>]
mode: spec-first         # spec-first | implementation-aligned
status: active           # active | done | postponed | abandoned
---

# Plan — <title>  (<YYYY-MM-DD>)

**Implements:** <REQ-AREA-NNN> · <SPEC-NAME §N> · <ADR-NNNN>
**Lane:** full | maintenance
**Verify:** `<build_entrypoint> <ci_target>` · `<build_entrypoint> <spec_check_target>`

## Tasks

<!-- Small, independently testable units. Each names what it advances and how to verify it.
     A task that needs the orchestrator's whole context to make sense is not delegated. -->
- [ ] **T1** — <task> · cites <REQ-…> · verify: `<command>`
- [ ] **T2** — <task> · verify: `<command>`

## Out of scope

- <…>

## Deferred

<!-- Items consciously not done here. They travel to the PR ledger's Deferred table. -->
- <…>

## Notes

<!-- What a fresh session needs to resume from this file alone: which tasks landed, which worker
     dispatch died and was not re-run, any adjudication made mid-flight.
     If status is postponed, one line saying what would restart it. -->

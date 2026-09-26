<!-- Template: a working implementation plan. Filename: <paths.plans>/YYYY-MM-DD-<slug>.md
     Delete this comment in the file you create.
     A plan is a working file on the author's disk: the only place checkbox task lists live before
     the draft PR exists, and it introduces NO normative statement (a rule goes in a spec first, via
     /sdd-specify). It is never committed; the gate does not read it; the draft PR body carries the
     task list from the moment the draft opens. Delete the file when the PR merges, or leave it. -->
# Plan — <title>  (<YYYY-MM-DD>)

**Implements:** <REQ-AREA-NNN> · <SPEC-NAME §N> · <ADR-NNNN>
**Lane:** <full | maintenance — no normative change>
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

<!-- What a fresh session on this machine needs to resume before the draft PR exists: which tasks
     landed, which worker dispatch died and was not re-run, any adjudication made mid-flight. -->

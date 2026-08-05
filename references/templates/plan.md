<!-- Template: an implementation plan. Produced by superpowers:writing-plans and landed here in
     docs/plans/ with the SDD citing header below. Filename: docs/plans/YYYY-MM-DD-<slug>.md
     Plans are the ONLY place checkbox task lists live. A plan introduces NO new normative rules
     (put those in a spec first, via /sdd-specify). Cite the REQ/SPEC §/ADR it implements in the header. -->
---
plan: <YYYY-MM-DD-slug>
status: active           # active | done | postponed
implements: [<REQ-AREA-NNN>, <SPEC-NAME §N>]
mode: spec-first         # spec-first | implementation-aligned
---

# Plan — <title>  (<YYYY-MM-DD>)

**Implements:** <REQ-AREA-NNN> · <SPEC-NAME §N> · <ADR-NNNN>
**Mode:** spec-first | implementation-aligned

## Definition of Ready

- [ ] A `REQ-*` exists with acceptance criteria
- [ ] Affected `SPEC-* §` listed (or a new § called out)
- [ ] No open ADR needed, or the ADR is already `Accepted`
- [ ] Out-of-scope written below
- [ ] Verification commands named: `<build_entrypoint> <ci_target>`, `<…>`
- [ ] Negative space named: what must refuse / fail closed, and the intended failure behaviour for each

## Tasks

<!-- Small, independently testable units. Each names what it advances and how to verify it. -->
- [ ] **T1** — <task> · cites <REQ-…> · verify: `<command>`
- [ ] **T2** — <task> · verify: `<command>`

## Out of scope

- <…>

## Definition of Done

All of the below land in the **same PR** that implements the plan (no follow-up close-out PR):

- [ ] Code + tests complete and verified on the branch
- [ ] Negative space exercised: refusal/failure paths tested; new runtime failure modes map to the documented error contract
- [ ] Spec and/or guide updated if behaviour changed
- [ ] Requirements index status updated
- [ ] `traceability.yaml` updated (packages / tests / probes)
- [ ] Plan flipped to `done` and `git mv`'d into `plans/archive/`
- [ ] `AGENTS.md` tables updated if anything user-facing changed

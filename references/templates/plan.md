<!-- Template: an implementation plan. Copied by /sdd-plan. Filename: docs/plans/YYYY-MM-DD-<slug>.md
     Plans are the ONLY place checkbox task lists live. A plan introduces NO new normative rules
     (put those in a spec first). Cite the REQ/SPEC §/ADR it implements in the header. -->
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

## Tasks

<!-- Small, independently testable units. Each names what it advances and how to verify it. -->
- [ ] **T1** — <task> · cites <REQ-…> · verify: `<command>`
- [ ] **T2** — <task> · verify: `<command>`

## Out of scope

- <…>

## Definition of Done

- [ ] Code + tests merged
- [ ] Spec and/or guide updated if behaviour changed
- [ ] Requirements index status updated
- [ ] `traceability.yaml` updated (packages / tests / probes)
- [ ] Plan flipped to `done` and `git mv`'d into `plans/archive/`
- [ ] `AGENTS.md` tables updated if anything user-facing changed

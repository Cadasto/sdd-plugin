# SDD alongside the superpowers plugin

This plugin owns the **spec / document / traceability layer**. It does **not** reimplement the generic engineering loop — brainstorming, planning, TDD, execution, generic verification, code review, and branch-finishing belong to the **superpowers** plugin. These two are designed to be **complementary**: SDD sits *between* exploration and planning, and *after* the build, to keep the specification the source of truth and the traceability chain intact.

If superpowers is not installed, the SDD skills still stand alone (they degrade to plain guidance for the spec layer); they simply hand the build phase to "your usual plan/implement workflow" instead of named superpowers skills.

## The combined flow

```
superpowers:brainstorming            explore intent → a design doc
        │
        ▼
SDD:sdd-specify                       record the decision as REQ + normative SPEC (+ ADR);
                                      assign stable IDs; wire the traceability entry
        │
        ▼
superpowers:writing-plans            decompose the spec into tasks  ── see "Path redirect" below
        │
        ▼
superpowers:executing-plans /        build (with TDD); cite REQ/PROBE ids in code & tests
  test-driven-development /           (an SDD discipline layered on the build, not a separate skill)
  subagent-driven-development
        │
        ▼
SDD:sdd-trace  ·  SDD:sdd-review (opt-in)  +  superpowers:verification-before-completion
  (traceability /   (spec-aware review:          (tests/build/lint pass — the generic gate)
   drift /           conformance + traceability,
   spec-check)       posted to the PR)
        │
        ▼
SDD:sdd-archive      +  superpowers:finishing-a-development-branch
  (close out the           (merge / PR / worktree cleanup)
   spec, index, plan       the archive rides in the SAME PR as the code
   — in the same PR)
```

## Who owns what (no overlap)

| Concern | Owner |
|---|---|
| Explore intent, weigh approaches, design doc | **superpowers** `brainstorming` |
| Record capability + normative behaviour + decisions as `REQ`/`SPEC`/`ADR`, assign IDs, wire traceability | **SDD** `sdd-specify` |
| Decompose into tasks; write the plan file | **superpowers** `writing-plans` |
| Execute tasks, red-green-refactor, write code/tests | **superpowers** `executing-plans` / `test-driven-development` / `subagent-driven-development` |
| Tests/build/lint actually pass (evidence before claims) | **superpowers** `verification-before-completion` |
| Code review of the *code* (bugs, style, security, tests) | **superpowers** `requesting-code-review` |
| Does the code satisfy the `SPEC §`/`REQ` acceptance criteria it cites (conformance, clause by clause) | **SDD** `sdd-spec-conformance-reviewer` agent |
| Traceability map matches the tree; orphan/drift detection (`spec-check`) | **SDD** `sdd-trace` (+ `sdd-traceability-auditor` agent) |
| Review of *SDD documents* (REQ/SPEC/ADR/plan headers) for boundary violations | **SDD** `sdd-doc-reviewer` agent |
| Orchestrate a spec-aware review (generic + traceability + conformance) and post it to the PR | **SDD** `sdd-review` (opt-in — *delegates* generic review and the posting mechanic, adds the SDD lenses) |
| Merge / PR / branch cleanup | **superpowers** `finishing-a-development-branch` |
| Close out the spec status, requirements index, and plan — **in the implementing PR** (archive) | **SDD** `sdd-archive` |

Rule of thumb: **superpowers acts on code and process; SDD acts on the specification and its traceability.** When both apply at a phase, run the superpowers skill for the engineering work and the SDD skill for the spec bookkeeping.

## Path redirect (the one integration that needs care)

superpowers writes its artefacts under a `docs/superpowers/` tree:

- `brainstorming` → `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- `writing-plans` → `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`

SDD's canonical homes are different and authoritative: normative specs in `docs/specifications/`, plans in `docs/plans/`. A `docs/superpowers/specs/*-design.md` is a **design narrative**, *not* a normative spec — it must not become a second source of truth. Reconcile as follows:

1. **Design docs are input, not truth.** Treat a `docs/superpowers/specs/*-design.md` as the *brainstorming output that feeds `sdd-specify`*. `sdd-specify` extracts the normative statements into the canonical `docs/specifications/` topic spec (with RFC-2119 keywords + IDs) and captures the capability as a `REQ`. The design doc may stay as narrative under `docs/architecture.md`/analysis, but the spec wins.
2. **Plans belong in `docs/plans/`.** When `writing-plans` produces a plan, place it at `docs/plans/YYYY-MM-DD-<slug>.md` and add the SDD citing header (`implements: [REQ-…, SPEC-NAME §N]`, `mode:`) and the Definition-of-Ready / Definition-of-Done blocks from `references/templates/plan.md`. Do **not** leave plans stranded under `docs/superpowers/plans/`.
3. **Document the override.** Record this redirect in the repo's `AGENTS.md` so every agent applies it consistently. (If superpowers is configurable to target `docs/plans/` directly, prefer that; otherwise move the file as the final step of planning.)

This is the documented override the methodology calls for: *if a tool wants to create a path that fights the taxonomy, override it and document the override* — rather than letting a parallel `docs/superpowers/` tree become an accidental second source of truth.

## SDD disciplines to layer onto the superpowers build

These are *not* separate skills — they are the SDD constraints the agent applies while using superpowers' planning/execution:

- The plan cites the `REQ`/`SPEC §`/`ADR` it implements and passes the Definition of Ready before work starts.
- Code and tests cite the `REQ`/`PROBE` ids they realise (a doc comment, a test name) so the chain stays greppable.
- `traceability.yaml` is updated as code lands (packages / tests / probes).
- For hardening on shipped code (*implementation-aligned* mode), the spec § is updated in the **same** change — "code wins until the spec is updated, in the same PR."
- A genuine open question is never settled in code — it goes to an ADR (`sdd-specify`) or a `STRAND`, or back to `brainstorming`.
- Commit / PR / changelog / review prose follows **one home per fact** — cite identifiers (`REQ`/`SPEC §`/plan/SHA), don't restate what a cited artefact already says. See `references/artefact-prose.md`.

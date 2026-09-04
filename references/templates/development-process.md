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
- Plans: cite the `REQ`/`SPEC §`/`ADR` they implement in the frontmatter. The only place checkboxes live.
  A working file on the branch, not a governed artefact.
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
         └─ PLAN (tasks + verification)    [gate: dispatch preconditions]
             └─ CODE + TESTS (cite ids)    [gate: tests green + drift gate green]
                 └─ update SPEC status + traceability  [gate: same PR]
                     └─ update REQ status; flip the plan to done in place [gate: PR-body close-out]
```

The whole close-out — spec status, requirements index, traceability, and the plan flip — lands in the
**same PR** that implements the plan. No follow-up PR. The plan file stays where it is so reviewers can
read it through the merge; it is deleted at the next version bump.

## Two source-of-truth modes

- **Spec-first** (new behaviour): the spec leads, code follows.
- **Implementation-aligned** (hardening / perf / bug-fix on shipped code): code may lead, **but the spec
  is updated in the same PR**. *"Code wins until the spec is updated — in the same PR."* Never let the spec
  silently lag.

## Dispatch preconditions

Five things are confirmed **before the first task is dispatched** — checked, not ticked in a file. A `REQ`
with acceptance criteria exists; the affected `SPEC §` exist or a new § is called out; any needed ADR is
`Accepted`; the **negative space** is cited from the `REQ` acceptance criteria and the `SPEC §` that owns
the failure behaviour (what must refuse or fail closed, and how); the verification commands are known. An
unmet precondition stops the dispatch and is named.

## The two lanes

The lane test is one question, answered in one line of the PR body: **does this change alter any normative
statement** — a `REQ`'s acceptance criteria, a `SPEC §` behaviour, a public API shape, an error contract?

- **Full lane** — new capability, any change to API shape, behaviour, or error contract, any spec
  amendment. Owes the plan, the `REQ`/spec edits, the traceability update, the SDD reviewers, and a PR body
  with the review lens and the identifiers touched. Its PR body carries `Lane: full`.
- **Maintenance lane** — refactors, moves and splits, performance work, dependency bumps, tooling,
  documentation polish, and a bug-fix whose fix makes the code match an **existing** spec statement. Owes
  green tests, a green drift gate, and one PR-body line: its PR body carries
  `Lane: maintenance — no normative change`. A bug-fix that reveals the **spec** was wrong is full lane.

The drift gate runs in **both** lanes — the map may never rot. The guard against a mislabelled lane is a
ratchet, not a diff check: any newly added or materially changed requirement owes observable acceptance
criteria and its own canonical `SPEC §`, whatever lane the change claims.

## The PR body — the close-out record

The PR body is where the close-out lives. Copy this block (a repo may also keep it as
`.github/PULL_REQUEST_TEMPLATE.md`):

````markdown
Lane: <full | maintenance — no normative change>
Implements: <REQ-…> · <SPEC-NAME §N> · <ADR-NNNN>
Plan: docs/plans/<YYYY-MM-DD-slug>.md
Claim: session <id> · worktree <path or none>

Review lens: <what to look at; what is out of scope>
Verified: `<command>` → <what the output said>

Close-out
- [ ] Code and tests complete, and the verification output was read — not assumed
- [ ] Negative space exercised: refusal and failure paths tested; each new runtime failure mode maps to the error-contract `SPEC §`
- [ ] `SPEC §` status set; `REQ` implementation status set
- [ ] `traceability.yaml` updated (packages / tests / probes)
- [ ] Plan flipped to `status: done` in place — no move, no index
- [ ] Deferred items and workers' en-route findings are in the ledger's `Deferred` table
- [ ] Any code the orchestrator wrote itself is named here, with why the task could not be made self-contained
````

Findings for the change live in **one review ledger comment** on the same PR, updated per round. See
[ai-workflow.md](ai-workflow.md) § Review.

## Artefact prose — one home per fact

The commit body, PR body, changelog, and review comments each carry only what lives nowhere else — cite
identifiers (`REQ`/`SPEC §`/plan/SHA) instead of restating. The spec owns normative behaviour; the commit
body owns the *why* of this change; the PR body owns the *review lens* (what to look at, how it was
verified); the changelog owns the one-line, user-facing delta. Don't retell the same story across all four.

## Open questions

Never settle an open question silently in a PR. Raise a `STRAND` (if enabled), draft an ADR, or ask. Never
add a normative rule that exists only in code — add the `REQ`/spec first.

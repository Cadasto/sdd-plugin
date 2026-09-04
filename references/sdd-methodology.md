# SDD methodology — the canonical reference

The single source of truth for the rules this plugin's skills enforce. Skills cite this file rather than restating it, so it can evolve in one place. It is **language-agnostic**: a documentation-and-process architecture, not a code pattern.

> **Guiding principle.** The **specification — not the code and not the prompt — is the source of truth.** Code is derived from it and continuously measured against it. When they disagree, the spec wins, *unless* a section is explicitly marked implementation-aligned (see §7).

## 1. The rigour ladder — and where this plugin sits

There is no single SDD; there is a ladder of ambition (Böckeler, Thoughtworks, 2025):

| Rung | Name | The spec's lifespan |
|---|---|---|
| 1 | **Spec-first** | Write a good spec, use it to drive the task; the spec may not outlive the feature. |
| 2 | **Spec-anchored** | The spec is **kept and evolved** — a maintained, versioned, governing contract. |
| 3 | **Spec-as-source** | The spec is the *only* artefact humans edit; code is regenerated from it. |

**This plugin targets rung 2 (spec-anchored)** and adds the governance machinery the mainstream toolkits (GitHub Spec Kit, AWS Kiro, Tessl) leave to the team: stable identifiers, a machine-checked traceability map, and CI that fails on drift.

## 2. The canonical loop

```
Constitution → Specify → (Clarify) → Plan → Tasks → Implement → Verify → Archive
```

Capture the **what and the why** — requirements, invariants, acceptance criteria — **not** redundant *how-to* an agent can infer from the existing code. Architectural constraints and business rules are high-value; restating obvious mechanics is noise.

## 3. The seven document kinds

The single most important rule: **every document has exactly one job and one altitude.** Mixing them is the cardinal sin.

| Kind | Answers | Normative? | Typical location |
|---|---|---|---|
| **Requirement** (`REQ-*`) | What must we deliver? How do we accept it? | Yes (acceptance criteria) | `docs/requirements/` |
| **Specification** (`SPEC-*`) | How must the system behave / be structured? | **Yes** (RFC-2119) | `docs/specifications/` |
| **ADR** (`ADR-*`) | Which *irreversible* fork did we take? | Decision record | `docs/adr/` |
| **Plan** | What exact work implements a slice? | No (tasks) | `docs/plans/` |
| **Guide** | How do I work in this repo safely? | No | `docs/architecture.md`, … |
| **Analysis** | What did we measure or compare? | No | `docs/analysis/` |
| **Operations** | How do operators run the system? | Runbooks | `docs/operations/` |

### Boundary rules (enforced by review, partly by CI)

- **Requirements** carry no file paths and no migration steps — only capability + acceptance + out-of-scope. Acceptance criteria cover the **negative space** too — what the capability must refuse or fail closed on, with the intended failure behaviour — not only the happy paths.
- **Specifications** carry RFC-2119 prose only — no checkbox task lists, no implementation file paths, no PR-style summaries, no duplicated requirement bodies.
- **Plans** MUST cite the `REQ-*` / `SPEC-* §` (or ADR) they implement, in the header.
- **ADRs** cover one decision each; long flows and schema DDL stay in the specs.
- **Guides** are informative; when a guide disagrees with a spec, **the spec wins and the guide is updated.**

### Normative vs narrative

`docs/specifications/` carries the **normative** statements (what code and tests are measured against). A design **narrative** (`docs/architecture.md`: diagrams, module map, "why it's shaped this way") may exist alongside, but if the two disagree, the specs win. This keeps the narrative readable prose without becoming an accidental second source of truth.

## 4. RFC-2119 keyword discipline

Specs mark normative force with [RFC-2119](https://www.rfc-editor.org/rfc/rfc2119) keywords, and say so up front:

| Keyword | Force |
|---|---|
| **MUST / SHALL / REQUIRED** | Absolute requirement — a non-conformant implementation is buggy |
| **MUST NOT / SHALL NOT** | Absolute prohibition |
| **SHOULD / RECOMMENDED** | Strong recommendation — exceptions need a documented reason |
| **MAY / OPTIONAL** | Truly optional — no conformance impact |

Statements without a keyword are **informative**. The rule: *don't implement informative text as a requirement; don't relax normative text into a suggestion.* Negative-space clauses — `MUST NOT`, refusals, fail-closed behaviour — carry the same force as their positive counterparts.

## 5. Identifier scheme

Stable, citable identifiers thread the whole repo — they appear in commit messages, PR titles, code comments, test names, and plan headers. **They must never be renumbered or reused once published** (renumbering is a major doc-version event that breaks every external citation).

| Prefix | Meaning |
|---|---|
| `REQ-*` | Enumerated requirement |
| `SPEC-<NAME> §N` | Normative spec section, with a stable section number |
| `ADR-NNNN` | Resolved architectural decision (sequential, never reused) |
| `PROBE-NNN` | Conformance probe (a behaviour/wire-level test) — optional |
| `STRAND-NN` | An **open**, scoped, named research question — not yet decided — optional |

Pick **one** REQ style and stay consistent (declared in `.sdd.yaml`):

- **flat-numeric** with decadal gaps (`REQ-050`, room to insert) — leaner for a library.
- **area-prefixed** (`REQ-AUTH-001`) — reads as a capability map; friendlier for a product.

### Single canonical home

Each requirement's normative prose lives in **exactly one** spec section. The requirements index only **links** to it — it never duplicates the requirement body. Two copies = two sources of truth = guaranteed drift.

### Lazy identifier allocation (the default)

**An idea with no acceptance contract does not get a `REQ` id.** Identifiers are allocated when a slice
meets the dispatch preconditions (§9), not when it is imagined. You cannot argue about the number of an
id that does not exist yet, and an id that was never published can never be renumbered.

This is a rule about *when* an id is allocated, not about *how* it is shaped. Decadal gaps, topic bands,
and area prefixes are the repository's own call and are declared in `.sdd.yaml`; this rule retires none
of them.

### The STRAND concept (naming the unknowns)

A `STRAND-NN` is an open architectural question that is scoped, named, and tracked but **not yet decided** — explicitly *not* a draft requirement. It resolves by: produce evidence (spike / benchmark / fit-gap) → write an ADR → amend the affected `REQ`s → close the strand with a backlink to the ADR. This is the formal home for "we don't know yet," which keeps unknowns out of the code.

## 6. The two status axes

Track these **separately** on every requirement — conflating them is a common failure:

1. **Spec stability** — `Draft` → `Stable` → `Deprecated`. Crucially, **`Draft` is binding *now*** — it only signals the *wording* may still change pre-1.0, not that the requirement is optional. Promotion to `Stable` freezes the contract (later changes need a deprecation cycle).
2. **Implementation status** — `planned`/`proposed` → `partial`/`in_progress` → `landed`/`shipped`, plus `deferred`.

A spec can be authoritative (`Draft`, binding) while its code is still `planned`. That is normal and healthy.

## 7. Two source-of-truth modes

A purist "spec always precedes code" rule breaks down for bug-fixes and perf work on shipped code. Define both modes explicitly:

| Mode | When | Order |
|---|---|---|
| **Spec-first** | New capability, API surface, schema shape, invariant | `REQ → SPEC (Draft) → ADR if fork → Plan → Code → SPEC status → REQ shipped` |
| **Implementation-aligned** | Hardening, perf, DB quirks, bug-fix on shipped code | `Code + migrations → update SPEC § + guide in the same PR → note in spec frontmatter` |

The discipline that keeps mode 2 honest: **"code wins until the spec is updated — in the same PR."** The spec is never allowed to silently lag. This is the encoding of the industry's *reconcile loop*.

## 8. The traceability chain

```
requirements index (one row per REQ)
  └─→ canonical topic spec (normative prose lives here, ONCE)
        └─→ traceability map (machine-readable: packages, probes, tests)
              └─→ code
                    └─→ tests
                          └─→ conformance probes (optional)
```

**The plan is not a link in this chain.** It is a working file on the branch that cites the `REQ`/`SPEC §`
it implements (§9). The durable record of what shipped is the requirement status, the specification
section, the ADR, the PR body, the changelog, and git.

Code and tests cite the `REQ` (and `PROBE`) ids they realise — a doc comment, a test name — so the chain stays greppable.

See [traceability-schema.md](traceability-schema.md) for the machine-readable record format.

### Drift CI — the non-negotiable gate

A `spec-check` target validates the traceability map against the actual tree (cited paths exist, probes resolve, no orphans). So **a requirement with no code, code with no test, or a probe with no test is a mechanically detectable drift signal.** This is what turns "we have specs" into "our specs can't silently rot."

## 9. The plan lifecycle — a working file, finished in place, swept at the release

A plan is a **working file on the branch**, not a governed artefact. It is the only place checkbox task
lists live, and it introduces **no normative statement** — a rule goes in a spec first.

Filename: `docs/plans/YYYY-MM-DD-<slug>.md`. Frontmatter:

| Key | Value |
|---|---|
| `plan` | `YYYY-MM-DD-<slug>`, matching the filename |
| `implements` | the `REQ` / `SPEC §` / `ADR` identifiers this plan delivers |
| `mode` | `spec-first` or `implementation-aligned` (§7) |
| `status` | `active` · `done` · `postponed` · `abandoned` |

### Dispatch preconditions

Five things are confirmed **before the first task is dispatched** — checked, not ticked in a file:

1. A `REQ` with acceptance criteria exists.
2. The affected `SPEC §` exist, or a new § is called out.
3. Any needed `ADR` is `Accepted`.
4. The negative space is **cited** from the `REQ` acceptance criteria and the `SPEC §` that owns the
   failure behaviour — what the change must refuse or fail closed on — not restated in the plan.
5. The verification commands are known.

An unmet precondition stops the dispatch and is named. A file of checkboxes cannot refuse to start work;
a gate can.

### Close-out: four surfaces, in the implementing PR

When the work is done, four things are set in the same PR that lands the code: the affected `SPEC §`
status, the `REQ` implementation status, the `traceability.yaml` packages/tests/probes, and the PR body.
The PR body carries the close-out checklist, the identifiers implemented, the verification commands and
what they returned, and the deferred items.

### Archive in place, sweep at the release

The plan's frontmatter is flipped to `status: done` **where the file lies**. It does not move, and there
is no plans index to update, because there is no plans index. The plan stays on the branch through the
merge so reviewers can read it.

At the next version bump — as the first step, before the tag — every plan whose `status` is `done` or
`abandoned` is deleted. Inbound links from `docs/**` are checked first and the sweep stops with the list;
the fix is to cite the PR or the `REQ` instead. A plan whose `status` is `active` or `postponed` is never
touched.

**Why two steps rather than one.** A moved file's links rot; a status line cannot. Deleting the plan
inside its own PR would take it away from the round that needs it. Between the flip and the sweep,
`docs/plans/` holds active, postponed, and recently finished plans, and the `status` line is the only
state. No index can lag, because there is none.

### Postponed and abandoned work

A postponed plan keeps its file: `status: postponed` plus one line saying what would restart it. A later
branch flips it back to `active` and continues. Work abandoned before its PR merges goes with the branch.
Work abandoned after its plan reached the main line is marked `status: abandoned` and swept at the next
release. A finished plan's leftover items travel to the review ledger's `Deferred` table (§13) or become a
`deferred`-status `REQ`; they never keep a finished plan alive.

## 10. Agent affordances

- **`AGENTS.md` is the single governed entry point** — a thin 1-page map that **defers to the canonical docs rather than duplicating them.** Per-agent files (`.claude/CLAUDE.md`, etc.) stay tiny and point back to it.
- **One-shot context bundle** — a `spec-context REQ=NNN` command assembles, in one shot, the index row + traceability block + canonical spec excerpt + any open strands, so an agent never has to grep the whole tree. `/sdd-trace` is the in-session analogue.
- **A published agent loop** (`ai-workflow.md`): locate the `REQ` → follow to its canonical spec → look up ground truth (never guess) → cite identifiers → don't decide open questions in code → verify with the full gate.
- **Name an authoritative ground-truth source for domain facts and forbid guessing them.** Every domain has a "look it up" rule; the source is declared in `.sdd.yaml` (`ground_truth`).
- **Cross-repo disagreement.** For a dependency this repository consumes, the upstream's semantics are
  ground truth and this repository's documents are corrected to match. Raise a genuine conflict as
  evidence, in one or two sentences — never design around it, and a difference from upstream is never
  reported as a defect in upstream.

## 11. Anti-patterns to design against

- **Duplicated normative prose.** Index links; the canonical body lives once. The same anti-pattern in the *process* layer — one story restated across the commit body, PR body, and changelog — is governed by [artefact-prose.md](artefact-prose.md): each fact has one home, the rest cite the identifier.
- **Rules that exist only in code.** A normative constraint with no `REQ`/spec is invisible to reviewers and agents. Add the `REQ` first.
- **Happy-path-only acceptance.** Acceptance criteria that never name what the capability must refuse or fail closed on — the negative space is part of the contract (§3, §9).
- **Mixing kinds.** Tasks in a spec, file paths in a requirement, multiple decisions in one ADR — each erodes the boundaries that make the system legible.
- **A status line that lies.** A plan left `active` after it shipped, or a `REQ` left `in_progress` after
  it landed. There is no plans index to rot any more, so the frontmatter is the only state and it has to be true.
- **Memoir prose.** A specification section or a probe entry states the **current contract only**. History
  — what it used to say, and why it changed — lives in git and in the ADR. A spec that narrates its own
  past is two documents in one file.
- **Settling open questions silently in a PR.** Surface them — a STRAND, an ADR, or a question to the user. Undocumented decisions compound.
- **Renumbering identifiers.** Breaks every external citation.
- **CI logic that diverges from local.** If the local gate ≠ what CI runs, agents can't self-verify. One build entry point; every check is a target.

## 12. Ceremony proportional to contract change — the two lanes

Ceremony is owed to a change of contract, not to a volume of code. **The lane test is one question,
answered in one line of the PR body: does this change alter any normative statement** — a `REQ`'s
acceptance criteria, a `SPEC §` behaviour, a public API shape, or an error contract?

| Obligation | **Full lane** | **Maintenance lane** |
|---|---|---|
| Plan file | required, on the branch | optional — a throwaway task list, not committed |
| `REQ` / index / `SPEC §` edits | required | forbidden by definition — needing one makes the change full lane |
| `traceability.yaml` | updated for landed packages/tests/probes | only when file paths moved, and the drift gate names exactly which rows |
| `ADR` | when an irreversible fork was taken | never — a maintenance change taking an irreversible fork is full lane |
| SDD reviewer agents | dispatched | skipped — there is no spec delta to review |
| Review scope | code + conformance + traceability | code review only |
| PR body | review lens + identifiers touched | one line: `Lane: maintenance — no normative change` |
| The drift gate (`spec-check`) | runs | **runs** — the map may never rot, in either lane |

A full-lane PR body carries `Lane: full`.

**Membership.** Maintenance lane: refactors, package moves and splits, performance work, dependency
bumps, tooling, comment and documentation polish, and a bug-fix whose fix makes the code match an
**existing** spec statement. Full lane: new capability, any change to API shape, behaviour, or error
contract, any spec amendment — including a bug-fix that reveals the **spec itself** was wrong, where the
spec amendment rides with the fix as implementation-aligned work (§7).

**The guard against lane abuse is a ratchet, not a diff check.** Any newly added or materially changed
requirement owes observable acceptance criteria and its own canonical `SPEC §`, whatever lane the change
claims. The undocumented baseline can only shrink. A ratchet cannot be gamed by mislabelling a change,
which is exactly what a diff check invites. A mislabel that slips through surfaces in the next full-lane
conformance review.

**The lane belongs to the change, not to the repository.** It is declared per PR. `.sdd.yaml` learns no
lane field.

## 13. Review discipline

**Two gates.** The merge gate is: the code is correct; every MUST the change touches has a named test
that fails when the guard is removed; the code conforms to the cited `SPEC §`; the drift gate is green.
Everything else — index polish, header alignment, citation parity, trimming — is **non-blocking by
definition** and goes to the review ledger's `Deferred` table. It is not a review round.

**The ledger is the default review format, not a remedy.** All findings for a change live in one
numbered comment on the PR, updated in place each round, whatever channel they arrived through. Format
and rules: [artefact-prose.md](artefact-prose.md). The `Deferred` table is the carrier for a non-blocking
finding; it is rolled forward into the next change that touches the area. A review leftover does not
become a tracker issue — that fragments the work away from the change that caused it.

**Materiality threshold.** A reviewer reports **blockers and should-fix findings by default; nits only
when they are asked for.** An empty axis or an uncited artefact is not automatically drift — "this does
not map" is a legitimate steady state. Never recommend meta-commentary whose only purpose is to satisfy
a checker.

**Verify before fixing.** A finding is a claim, and so is a reviewer's proposed correction. Both are
checked against the code and the spec before either is applied. A correction that is wrong and applied
propagates into every artefact that cites it.

**Sweep the axis, not the instance.** For each confirmed defect, census the pattern class before
resolving it. One fixed instance of a class that recurs is a finding deferred, not a finding closed.

**Collapse before you add.** A `REQ` amended during review may not accrete per-incident corollaries; each
new residual folds into the existing invariant or replaces it. This is **not** "do not amend mid-review" —
the in-review amendment loop is where much of the value is.

**Settled adjudications are remembered.** A declined finding, with the reason it was declined, is written
to the repository's reviewer memory at `docs/.sdd/reviewers/<agent-name>.md`, so the same finding is not
re-raised the next round. The reviewer agents read that file; the triage step writes it.

**The review layer meets the bar it imposes.** A fan-out of reviewers records which members were
dispatched and how many reported. A panel that cannot say whether all its members reported is not
evidence of absence.

## 14. What this methodology does not relax

The mechanisms below earned their cost and are untouched by the lanes, the lean plan lifecycle, and the
review thresholds:

- normative topic specs with RFC-2119 force, and "when code and specs disagree, the specs win";
- spec-first for new capability, including the pre-code spec review;
- stated closure properties and invariants as the review anchor, and axis sweeps from them;
- ground-truth pinning — look it up, never guess;
- the mutation-detectability bar: removing the guard MUST fail a named test;
- identifier stability — a published id is never renumbered or reused;
- ADRs for irreversible forks; STRANDs for genuinely open questions;
- the traceability map for packages, tests and probes, and the drift gate that validates it — in **both**
  lanes.

## Sources

The methodology corroborates and tightens the 2026 industry consensus:

- GitHub, *Spec-driven development with AI* and the [`github/spec-kit`](https://github.com/github/spec-kit) toolkit.
- Microsoft for Developers, *Spec-Driven Development: A Spec-First Approach to AI-Native Engineering*.
- IBM, *What is Spec-Driven Development?*
- Birgitta Böckeler / Thoughtworks (martinfowler.com, Oct 2025) — the spec-first / spec-anchored / spec-as-source ladder.
- Sean Grove, *The New Code*, AI Engineer World's Fair 2025.
- TrueFoundry, *Spec-Driven Development for AI Agents: Governing Specs* (2026) — the "governing specs at scale" problem.
- RFC-2119 — keyword force for normative statements.

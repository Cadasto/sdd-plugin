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

- **Requirements** carry no file paths and no migration steps — only capability + acceptance + out-of-scope. Acceptance criteria cover the **negative space** too — what the capability must refuse or fail closed on — not only the happy paths.
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

Statements without a keyword are **informative**. The rule: *don't implement informative text as a requirement; don't relax normative text into a suggestion.*

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
        └─→ traceability map (machine-readable: packages, probes, tests, plans)
              └─→ plan (docs/plans/YYYY-MM-DD-*.md)
                    └─→ code
                          └─→ tests
                                └─→ conformance probes (optional)
```

Two rules make the chain trustworthy:

1. **Single canonical home** (§5) — the index links, the spec owns the prose.
2. **Cite identifiers when crossing the chain** — plans list the `REQ`s they implement; code references its `REQ`/spec sections; a test citing a normative requirement names the `REQ` (and `PROBE`) in a comment; an ADR cites the `STRAND` it resolves.

See [traceability-schema.md](traceability-schema.md) for the machine-readable record format.

### Drift CI — the non-negotiable gate

A `spec-check` target validates the traceability map against the actual tree (cited paths exist, probes resolve, no orphans). So **a requirement with no plan, a plan with no code, code with no test, or a probe with no test is a mechanically detectable drift signal.** This is what turns "we have specs" into "our specs can't silently rot."

## 9. The plan lifecycle — Definition of Ready / Done

Plans are the **only** place checkbox task lists live. Filename: `docs/plans/YYYY-MM-DD-<slug>.md`; header cites the `REQ`/`SPEC §`/`ADR` it covers.

**Definition of Ready** (a plan may not start until):
- [ ] A `REQ-*` exists with acceptance criteria.
- [ ] Affected `SPEC-* §` are listed (or a new § is called out).
- [ ] No open ADR is needed, or the ADR is already `Accepted`.
- [ ] Out-of-scope is written; verification commands are named.
- [ ] The **negative space** is named: the inputs and states the change must refuse or fail closed on, with the intended failure behaviour for each — not only the happy paths.

**Definition of Done** (a feature is not finished until — all in the **same implementing PR**):
- [ ] Code + tests complete and verified on the branch.
- [ ] The DoR's negative space is exercised: refusal/failure paths have tests, and each **new runtime failure mode** the change introduces maps to the documented error contract (not left to a generic fall-through).
- [ ] Spec and/or guide updated if behaviour changed.
- [ ] Requirements index status updated.
- [ ] Traceability map (`traceability.yaml`) updated to the landed packages/tests/probes.
- [ ] Plan flipped to `done` and `git mv`d to `docs/plans/archive/`.
- [ ] `AGENTS.md` (or its tables) updated if anything user-facing changed.

**Archive-on-completion is normative, not housekeeping:** leaving `done` plans in the active list rots the index. This is the industry's *outer/archive loop*. Land the close-out (plan flip + archive move + index/status updates) in the **same PR** that implements the plan — not a follow-up — so the one merge that ships the code also closes the plan.

## 10. Agent affordances

- **`AGENTS.md` is the single governed entry point** — a thin 1-page map that **defers to the canonical docs rather than duplicating them.** Per-agent files (`.claude/CLAUDE.md`, etc.) stay tiny and point back to it.
- **One-shot context bundle** — a `spec-context REQ=NNN` command assembles, in one shot, the index row + traceability block + canonical spec excerpt + any open strands, so an agent never has to grep the whole tree. `/sdd-trace` is the in-session analogue.
- **A published agent loop** (`ai-workflow.md`): locate the `REQ` → follow to its canonical spec → look up ground truth (never guess) → cite identifiers → don't decide open questions in code → verify with the full gate.
- **Name an authoritative ground-truth source for domain facts and forbid guessing them.** Every domain has a "look it up" rule; the source is declared in `.sdd.yaml` (`ground_truth`).

## 11. Anti-patterns to design against

- **Duplicated normative prose.** Index links; the canonical body lives once. The same anti-pattern in the *process* layer — one story restated across the commit body, PR body, and changelog — is governed by [artefact-prose.md](artefact-prose.md): each fact has one home, the rest cite the identifier.
- **Rules that exist only in code.** A normative constraint with no `REQ`/spec is invisible to reviewers and agents. Add the `REQ` first.
- **Mixing kinds.** Tasks in a spec, file paths in a requirement, multiple decisions in one ADR — each erodes the boundaries that make the system legible.
- **Stale active lists.** `done` plans left active, or an index that lags reality, destroys trust. Archive on completion.
- **Settling open questions silently in a PR.** Surface them — a STRAND, an ADR, or a question to the user. Undocumented decisions compound.
- **Renumbering identifiers.** Breaks every external citation.
- **CI logic that diverges from local.** If the local gate ≠ what CI runs, agents can't self-verify. One build entry point; every check is a target.

## Sources

The methodology corroborates and tightens the 2026 industry consensus:

- GitHub, *Spec-driven development with AI* and the [`github/spec-kit`](https://github.com/github/spec-kit) toolkit.
- Microsoft for Developers, *Spec-Driven Development: A Spec-First Approach to AI-Native Engineering*.
- IBM, *What is Spec-Driven Development?*
- Birgitta Böckeler / Thoughtworks (martinfowler.com, Oct 2025) — the spec-first / spec-anchored / spec-as-source ladder.
- Sean Grove, *The New Code*, AI Engineer World's Fair 2025.
- TrueFoundry, *Spec-Driven Development for AI Agents: Governing Specs* (2026) — the "governing specs at scale" problem.
- RFC-2119 — keyword force for normative statements.

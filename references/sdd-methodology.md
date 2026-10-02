# SDD methodology — the canonical reference

The single source of truth for the rules this plugin's skills enforce. Skills cite this file rather than restating it, so it can evolve in one place. It is **language-agnostic**: a documentation-and-process architecture, not a code pattern.

> **Guiding principle.** The **specification — not the code and not the prompt — is the source of truth.** Code is derived from it and continuously measured against it. When they disagree, the spec wins, *unless* a section is explicitly marked implementation-aligned (see §7) or the repository runs the informative profile, where code leads and only the constitution binds (§1a).

## 1. The rigour ladder — and where this plugin sits

There is no single SDD; there is a ladder of ambition (Böckeler, Thoughtworks, 2025):

| Rung | Name | The spec's lifespan |
|---|---|---|
| 1 | **Spec-first** | Write a good spec, use it to drive the task; the spec may not outlive the feature. |
| 2 | **Spec-anchored** | The spec is **kept and evolved** — a maintained, versioned, governing contract. |
| 3 | **Spec-as-source** | The spec is the *only* artefact humans edit; code is regenerated from it. |

**This plugin targets rung 2 (spec-anchored)** and adds the governance machinery the mainstream toolkits (GitHub Spec Kit, AWS Kiro, Tessl) leave to the team: stable identifiers, a machine-checked traceability map, and CI that fails on drift.

## 1a. Two profiles

A repository declares how much of this methodology binds it, in `docs/.sdd.yaml` → `profile`.

| | **formal** | **informative** |
|---|---|---|
| What `docs/` is | the contract: requirements, RFC-2119 specifications, ADRs, a traceability map | a knowledge base: architecture, behaviour as it is, decisions |
| What binds code | every normative sentence of the specifications the change cites | the binding sentences of one constitution document (`paths.constitution`, default `docs/architecture.md`) |
| Identifiers and the map | required (§5, §8) | optional; used where the repository already has them |
| Source-of-truth order | spec-first by default; implementation-aligned for hardening (§7) | code leads; the documents the change affects are reconciled in the same change |
| Lanes | full or maintenance (§12) | one lane |
| The drift gate | every family | `descriptor`, `doc-kinds`, `links`, `changelog`, `generated` |
| Review pass | code reviewers, conformance reviewer, one document reviewer | code reviewers, one document reviewer in consistency mode, the conformance reviewer only against the constitution when the change touches what it binds |
| Starting a delivery | the dispatch preconditions of §9 | the task is clear and the verification command is known |

Both profiles share the same skills, the same findings file and the same review discipline (§13). The
informative profile is the one to choose when a specification written before the code would be a guess,
or when the cost of keeping fine-grained requirements checked exceeds what they protect; it still refuses
a change that contradicts the architecture, because the constitution binds.

## 2. The canonical loop

```
Constitution → Specify → (Clarify) → Plan → Tasks → Implement → Verify → Close out
```

Capture the **what and the why** — requirements, invariants, acceptance criteria — **not** redundant *how-to* an agent can infer from the existing code. Architectural constraints and business rules are high-value; restating obvious mechanics is noise.

## 3. The document kinds and their zones

The single most important rule: **every document has exactly one job and one altitude.** Mixing them is the cardinal sin.

| Kind | Answers | Normative? | Typical location |
|---|---|---|---|
| **Requirement** (`REQ-*`) | What must we deliver? How do we accept it? | Yes (acceptance criteria) | `docs/requirements/` |
| **Specification** (`SPEC-*`) | How must the system behave / be structured? | **Yes** (RFC-2119) | `docs/specifications/` |
| **ADR** (`ADR-*`) | Which *irreversible* fork did we take? | Decision record | `docs/adr/` |
| **Guide** | How do I work in this repo safely? | No | `docs/*.md` |
| **Analysis** | What did we measure or compare? | No | `docs/analysis/` |
| **Operations** | How do operators run the system? | Runbooks | `docs/operations/` |
| **Reference** | A declared projection or a superseded rationale | No — binds nothing | beside the specs, or `docs/reference/` |
| **Upstream** | What another repository owes this one (a cross-repo ask) | No — its own state lifecycle | `docs/<upstream>-gap-drafts/` |
| **Constitution** (informative profile) | What must every change respect? | **Yes** — its MUST sentences, and only those (§1a) | `paths.constitution`, default `docs/architecture.md` |

A plan is a temporary working file, committed or not, which the maintainer clears away once it has
served; marked `kind: plan`, the gate and the reviewers leave it alone (§9). The one standing plan is
the backlog, `docs/backlog.md`: leftovers waiting for the delivery that touches them
([review.md](review.md) § The backlog).

### The three zones

The first eight kinds fall into three zones; the zone decides how a document is read, and what the drift gate enforces on it. The constitution exists only on the informative profile, where it is the one binding document and carries no status.

- **Normative** — `requirement`, `specification`, `adr`. Each carries a status vocabulary of its own (§6); the specification carries the RFC-2119 force (§4).
- **Informative** — `guide`, `analysis`, `operations`, `reference`. Each explains, measures, or projects. None carries a status.
- **Upstream** — `upstream`. An ask filed at another repository, running its own `state:` lifecycle (§10).

Three rules hold the zones apart:

- Where an informative document and a specification disagree, the specification wins and the informative document is corrected.
- An informative document may carry a process imperative; it may not be the only home of a product-contract rule — it cites the owning `SPEC §`.
- A `reference` document is a declared projection: it binds nothing and carries no RFC-2119 keyword.

### Boundary rules (enforced by review, partly by CI)

- **Requirements** carry no file paths and no migration steps — only capability + acceptance + out-of-scope. Acceptance criteria cover the **negative space** too — what the capability must refuse or fail closed on, with the intended failure behaviour — not only the happy paths.
- **Specifications** carry RFC-2119 prose only — no checkbox task lists, no implementation file paths, no PR-style summaries, no duplicated requirement bodies.
- **ADRs** cover one decision each; long flows and schema DDL stay in the specs.
- **Guides** are informative; when a guide disagrees with a spec, **the spec wins and the guide is updated.**
- **Every document declares its kind** in frontmatter (`kind:`); the vocabulary is the descriptor's `doc_kinds`.

### Normative vs narrative

`docs/specifications/` carries the **normative** statements (what code and tests are measured against). A design **narrative** (diagrams, module map, "why it's shaped this way") may exist alongside, but if the two disagree, the specs win. (On the informative profile `docs/architecture.md` is the constitution instead.) This keeps the narrative readable prose without becoming an accidental second source of truth.

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

Stable, citable identifiers thread the whole repo — they appear in commit messages, PR titles, test names, and PR bodies. **They must never be renumbered or reused once published** (renumbering is a major doc-version event that breaks every external citation).

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

### Excluded areas

An area a repository has deliberately excluded is declared in `excluded_areas`; the gate rejects an identifier that uses it. A stated non-area ends the 'should this be a requirement?' conversation before it starts.

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

## 6. Status — per document kind

A requirement carries two status axes and they are tracked **separately** — conflating them is a common
failure. **Spec stability** (`status`) says how settled the wording is; promotion to `stable` freezes the
contract, and a later change needs a deprecation cycle. **Implementation status** (`implementation`) says
how much of it is built. A requirement can be authoritative (`draft`, binding) while its code is still
`planned`. That is normal and healthy. The traceability map is the single owner of both axes.

Each kind carries its own vocabulary:

| Kind | Key | Values |
|---|---|---|
| **Specification** | `status` | `draft` · `stable` · `deprecated` |
| **Requirement** | `status` | `draft` · `stable` · `deprecated` |
| **Requirement** | `implementation` | `proposed` · `planned` · `in_progress` · `partial` · `landed` · `shipped` · `deferred` · `retired` |
| **ADR** | `status` | `proposed` · `accepted` · `superseded` · `deprecated` |
| **Upstream** | `state` | `proposed` · `submitted` · `landed-upstream` · `landed` · `rejected` |
| Guide, analysis, operations, reference | — | no status |

> **A `draft` specification is binding.**

The upstream kind deliberately spells its key `state`, not `status`: the lifecycle it tracks belongs to
another repository, not to this one (§10).

**"Enforced" implementation values** are `in_progress`, `partial`, `landed` and `shipped`. A record with
one of these carries evidence — at least one `packages`, `tests`, or `operations` entry — and the gate
fails when it does not.

The close-out in the implementing PR sets **`shipped`** (§9). **`landed`** stays in the vocabulary for a
maintainer who merges code that is not yet usable, such as work behind a flag; no skill sets it.

**`retired`** marks a withdrawn requirement whose identifier is kept only so it is never reused (§14). It
is allowed only when `status` is `deprecated`, and it owes no evidence. The reverse does not hold: during a
deprecation cycle the code can still be `shipped`, so `deprecated` never forces `retired`.

## 7. Two source-of-truth modes

A purist "spec always precedes code" rule breaks down for bug-fixes and perf work on shipped code. Define both modes explicitly:

| Mode | When | Order |
|---|---|---|
| **Spec-first** | New capability, API surface, schema shape, invariant | `REQ → SPEC (Draft) → ADR if fork → Plan → Code → REQ shipped` |
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

**The plan is not a link in this chain** (§9). The durable record of what shipped is the requirement
status, the specification section, the ADR, the PR body, the changelog, and git.

Tests cite the `REQ` (and `PROBE`) ids they realise in their names, and the implementing commit cites them in its message, so the chain stays greppable. **Doc comments are not a carrier.** A doc comment is written for whoever reads the API and follows the language's own convention; the map, the commit history, and the test names carry the identifiers.

See [traceability-schema.md](traceability-schema.md) for the machine-readable record format.

### Drift CI — the non-negotiable gate

A `spec-check` build target runs the shared gate, `sdd-check`, vendored into the repository and pinned by
version in `.sdd.yaml`. It validates the map against the tree in both directions, the index against the
map, the document kinds, the links, and the prose rules that can be checked mechanically, and it
regenerates every derived index from one source. Its contract is [sdd-check.md](sdd-check.md). This is
what turns 'we have specs' into 'our specs can't silently rot' — one implementation, one blind-spot list,
fixed once for every repository.

## 9. Delivery — the dispatch preconditions and the close-out

How the orchestrator plans is not this methodology's business; a plan is a temporary working file, committed
or not. It introduces **no normative statement** — a rule goes in a specification first.

### Dispatch preconditions

On the formal profile, five things are confirmed **before the first task is dispatched** — checked, not
ticked in a file:

1. A `REQ` with acceptance criteria exists.
2. The affected `SPEC §` exist, or a new § is called out.
3. Any needed `ADR` is `Accepted`.
4. The negative space is **cited** from the `REQ` acceptance criteria and the `SPEC §` that owns the
   failure behaviour — what the change must refuse or fail closed on — not restated.
5. The verification commands are known.

An unmet precondition stops the dispatch and is named. On the informative profile the task is clear and
the verification command is known (§1a).

### Close-out — the last step of `/sdd-deliver`

When the work is done, the same PR that lands the code sets the `REQ`'s `implementation` to `shipped` (§6)
with its `traceability.yaml` packages/tests/probes, runs `sdd-check generate`, and writes the PR body. A
`SPEC §` is promoted to `stable` only when the maintainer confirms it, because promotion freezes the
contract.

**Durable documents never cite a plan or a session.** A requirement, specification or ADR cites the PR,
the commit or the `REQ` — never a plan, which is temporary even when it is committed.

### Postponed and abandoned work

Work that stops before it ships is recorded on the requirement: `implementation: deferred` (§6), with the
reason in the PR body. A leftover the maintainer keeps becomes a `deferred` requirement or one line under
the specification's *Known gaps*, or, when it is about code, a line in `docs/backlog.md`
([review.md](review.md) § The backlog); the rest is dropped.

## 10. Agent affordances

- **`AGENTS.md` is the single governed entry point** — a thin 1-page map that **defers to the canonical docs rather than duplicating them.** Per-agent files (`.claude/CLAUDE.md`, etc.) stay tiny and point back to it.
- **One-shot context bundle** — `sdd-check context <REQ>` assembles, in one shot, the index row + traceability block + canonical spec excerpt + any open strands, so an agent never has to grep the whole tree. `/sdd-trace` is the in-session caller.
- **A published agent loop** (`ai-workflow.md`): locate the `REQ` → follow to its canonical spec → look up ground truth (never guess) → cite identifiers → don't decide open questions in code → verify with the full gate.
- **Name an authoritative ground-truth source for domain facts and forbid guessing them.** Every domain has a "look it up" rule; the source is declared in `.sdd.yaml` (`ground_truth`), as one source or an ordered list consulted first to last — and a local checkout is a cache, not the basis of a claim.
- **Cross-repo disagreement.** For a dependency this repository consumes, the upstream's semantics are
  ground truth and this repository's documents are corrected to match. Raise a genuine conflict as
  evidence, in one or two sentences — never design around it, and a difference from upstream is never
  reported as a defect in upstream.
- **The cross-repo ask has a lifecycle.** A `kind: upstream` document carries `state:` through
  `proposed → submitted → landed-upstream → landed | rejected`; the rules are in
  [cross-repo-gap.md](cross-repo-gap.md).

## 11. Anti-patterns to design against

- **Duplicated normative prose.** Index links; the canonical body lives once. The same anti-pattern in the *process* layer — one story restated across the commit body, PR body, and changelog — is governed by [artefact-prose.md](artefact-prose.md): each fact has one home, the rest cite the identifier.
- **Rules that exist only in code.** A normative constraint with no `REQ`/spec is invisible to reviewers and agents. Add the `REQ` first.
- **Happy-path-only acceptance.** Acceptance criteria that never name what the capability must refuse or fail closed on — the negative space is part of the contract (§3, §9).
- **Mixing kinds.** Tasks in a spec, file paths in a requirement, multiple decisions in one ADR — each erodes the boundaries that make the system legible.
- **A status line that lies.** A `REQ` left `in_progress` after it shipped. The traceability record is the only state, and it has to be true.
- **Memoir prose.** A specification section or a probe entry states the **current contract only**. History
  — what it used to say, and why it changed — lives in git and in the ADR. A spec that narrates its own
  past is two documents in one file.
- **Settling open questions silently in a PR.** Surface them — a STRAND, an ADR, or a question to the user. Undocumented decisions compound.
- **Renumbering identifiers.** Breaks every external citation.
- **CI logic that diverges from local.** If the local gate ≠ what CI runs, agents can't self-verify. One build entry point; every check is a target.

## 12. Ceremony proportional to contract change — the two lanes

On the formal profile, ceremony is owed to a change of contract, not to a volume of code. **The lane test is one question,
answered in one line of the PR body: does this change alter any normative statement** — a `REQ`'s
acceptance criteria, a `SPEC §` behaviour, a public API shape, or an error contract?

| Obligation | **Full lane** | **Maintenance lane** |
|---|---|---|
| `REQ` / index / `SPEC §` edits | required | forbidden by definition — needing one makes the change full lane |
| `traceability.yaml` | updated for landed packages/tests/probes | only when file paths moved, and the drift gate names exactly which rows |
| `ADR` | when an irreversible fork was taken | never — a maintenance change taking an irreversible fork is full lane |
| SDD reviewer agents | dispatched | `sdd-doc-reviewer` alone, for consistency, when a document changed |
| Review scope | code + conformance + traceability | code review, and document consistency when a document changed |
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
lane field. The informative profile has one lane.

## 13. Review discipline

**The merge gate.** The code is correct; every binding sentence the change touches has a named test that
fails when its guard is removed; the code conforms to the sentences it cites (all specifications on the
formal profile, the constitution on the informative one); the drift gate is green; no critical or
important finding is open. Everything else is a suggestion ([review.md](review.md) § Severity).

**Findings live in the branch's findings file** and, when there is a pull request, in its inline threads
— nowhere else. Format, severities, scope, evidence, the mirror, resolution, the pass budget:
[review.md](review.md).

**Scope is the change.** A pass reads the branch's commits since its base, so every reviewer gives an
opinion on the whole change; the pass over fixes reads only the commits since the last pass. What the
change did not touch is a suggestion at most.

**Verify before fixing.** A finding is a claim, and so is a reviewer's proposed correction. Both are
checked against the code and the documents before either is applied, and so is what surrounds them: the
cause, what shares it, and what the correction would change. A finding can understate its defect.

**Collapse before you add.** A requirement amended during review may not accrete per-incident
corollaries; each residual folds into the existing invariant or replaces it.

**Decisions that bind go where decisions live.** A decline that should hold for future changes becomes a
specification sentence or an ADR (formal), or a constitution sentence (informative) — never a side file.

**The enforcement register.** A rule without a failing check is a wish. Every hard rule in this
methodology names its enforcement — a `sdd-check` family, a build target, a hook, or `review-enforced`.
The review-enforced list is meant to shrink.

| Rule | Enforcement |
|---|---|
| Map record shape and status vocabulary | `map-schema` |
| `retired` only on a `deprecated` requirement | `map-schema` |
| Canonical home resolves both ways | `map-to-tree` |
| Evidence on enforced records | `map-to-tree` |
| Index equals map | `index-sync` |
| One canonical home | `one-home` |
| RFC-2119 only in specifications | `rfc2119` |
| Doc kinds and status vocabularies | `doc-kinds` |
| Links and fragments resolve | `links` |
| Durable documents never cite a plan | `links` for a link; `sdd-doc-reviewer` for prose |
| Changelog bullet | `changelog` |
| Generated blocks match | `generated` |
| Unknown identifier cited in code | `tree-to-map` |
| Lanes | review-enforced — `/sdd-review` |
| Critical and important findings carry evidence and sit in the range | review-enforced — `/sdd-review` |
| No open critical or important finding at merge | `sdd-pr status` |
| The pass budget | review-enforced — `/sdd-triage` |
| Collapse before you add | review-enforced |
| Mutation-detectability | the build gate's tests |

**The review layer meets the bar it imposes.** Every pass writes a `Reviewed` line naming the reviewers
dispatched and how many reported; a pass that dispatched none writes none, so its range stays open.

## 14. What this methodology does not relax

The mechanisms below earned their cost and are untouched by the lanes, the profiles, and the review
severities:

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

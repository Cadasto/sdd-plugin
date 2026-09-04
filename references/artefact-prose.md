# Artefact prose economy — one home per fact

The single-canonical-home rule ([sdd-methodology.md](sdd-methodology.md) §5) applied to the **process prose** around a change — the commit, the PR body, the changelog, and the review/resolution comments. It exists because agent-to-agent workflows retell the same story three or four times (commit body ≈ PR body ≈ changelog ≈ review comment), and every retelling is a second source of truth: drift waiting to happen and noise for the next agent to wade through.

> **Principle.** Each fact has exactly one home. Every other artefact **cites the identifier** — `REQ` / `SPEC §` / `ADR` / plan / `PROBE` / commit SHA / finding — instead of restating the prose. Prefer a citation over a paragraph.

## Where each kind of prose lives

| Artefact | Its one job | Must **not** contain | Anchors it cites |
|---|---|---|---|
| **Spec §** | Normative *what / how it must behave* (RFC-2119) | Task lists, file paths, PR-style narrative | `REQ` |
| **Commit body** | The *why* of **this** change — rationale, tradeoff — one tight paragraph | A re-listing of the diff; restated spec prose | `REQ` / `SPEC §` / plan / `ADR` |
| **PR body** | The *review lens* — what to look at, what's out of scope, how it was verified, which IDs it touches | A re-explanation of the spec; a second changelog | plan / `REQ` / `SPEC §`; the commit range |
| **Changelog** | The *user-facing delta* — one subsystem-led line per bullet | Rationale, design narrative (those are in the commit/ADR) | optional `REQ` |
| **Review comment** | One finding, anchored to `file:line` (+ the `SPEC §` it violates, if normative) | Essays; re-litigation of settled points | `SPEC §` / finding id |
| **Resolution comment** | That a finding is fixed — one line + the fixing commit SHA | A re-description of the fix (it's in the diff) | the finding + commit SHA |

Two rules on that table are **stated, not yet enforced** — no tool checks them today, so they are a
reviewer's judgement call and are written here so the judgement is the same every time:

- **Changelog bullet.** One sentence, at most about 35 words, leading with the subsystem, no API
  inventory, no rationale. Rationale belongs in the commit body or the ADR.
- **One canonical home.** Each normative sentence, normalised, appears **exactly once** across
  `docs/specifications/**`, and RFC-2119 keywords do not appear outside that tree. A requirement, an ADR,
  or a plan cites the anchor instead of repeating the sentence. A consolidation that changes a `MUST`'s
  force while moving it is not a move — it is an amendment, and is reviewed as one.

## The findings ledger

Policy — why one ledger, why the `Deferred` table is the carrier, why completion is accounted — lives in
[sdd-methodology.md](sdd-methodology.md) §13; this section gives the format.

````markdown
## Review ledger — round N (reviewer, date)
Dispatched: <reviewers> · Reported: <n> of <m>
| id | severity | anchor | finding | status |
|---|---|---|---|---|
| F1 | blocker | <path>:214 | one sentence, plain words | fixed@abc1234 |
| F2 | should-fix | docs/specifications/<topic>.md §4 | one sentence, plain words | open |
| F3 | nit | CHANGELOG.md | one sentence, plain words | deferred |

## Deferred
| id | item | carried from | owner |
|---|---|---|---|
| F3 | <the item, in a few words> | this PR | next change touching <area> |
````

**Rules**

- Ids are `F<n>`, taken from the next free number and **append-only across rounds**. A finding keeps its
  id for the life of the change.
- `severity` is `blocker | should-fix | nit`. `status` is `open | fixed@<sha> | declined + reason | deferred`.
- Every fix pass enumerates **the ledger**, never the comment channels.
- **Completion accounting.** The header names which reviewers were dispatched and how many reported.
- Near-duplicate findings from two reviewers merge under **one** id, with both sources named.
- Write a finding id as `F12`, or in words — **never as a bare hash-plus-number**, which a hosting platform
  renders as a link to an unrelated issue or pull request. That is a false citation, and every tool that
  scans for issue and pull-request references will read it that way.

## Writing for an agent reader

Most of this text is written by one agent and read by another (a reviewer agent, a fixer agent). Tune for that reader:

- **Terse, identifier-anchored, complete enough to act on, zero ceremony.** No preamble, no summary-of-a-summary, no restating what a cited artefact already says.
- **A citation beats a retelling.** "Implements `REQ-AUTH-003` / `SPEC-WIRE §4`; rationale in `ADR-0007`." — not a paragraph re-deriving the decision.
- **Keep the essential once.** The one thing that lives *here and nowhere else* stays: the *why* in the commit, the *review lens* in the PR, the *user-facing line* in the changelog, the *finding* in the review comment. Everything that merely echoes a cited artefact is cut.

## Prose register

Most of this text is written by one agent and read by another, so the test is whether the text is
**unambiguous**, not whether it is polished.

- **Plain words. One idea per sentence.**
- **Explain a term the first time it is used, or drop it.** A term that is neither explained nor droppable
  belongs in the document that defines it, cited by identifier.
- This applies to **review findings and resolution comments** as much as to specifications and changelogs.
  A finding that is hard to read costs a round in the same way a finding that is wrong does.
- A word budget may **never** cut an identifier, a path, or the reason a finding is a finding.

## What this does *not* touch

- The commit **subject line** may be as descriptive as the Conventional-Commits header needs — the economy rule governs the *body* and the *downstream* artefacts, not the first line.
- Commit, PR, and branch **mechanics** — creating the branch, opening the PR, merging, cleaning up
  worktrees — are the git workflow, not this reference. This file governs only *what prose goes where*.

## Related

- [sdd-methodology.md](sdd-methodology.md) §5 (single canonical home), §8 (cite identifiers when crossing the chain), §11 (duplicated prose is an anti-pattern).
- [sdd-methodology.md](sdd-methodology.md) §13 (two gates, the materiality threshold, the ledger as the default).
- `sdd-review` writes the ledger; `sdd-triage` maintains it round to round.
- The scaffolded repo restates the short form in `AGENTS.md` and `docs/ai-workflow.md` so every consuming repo inherits it.

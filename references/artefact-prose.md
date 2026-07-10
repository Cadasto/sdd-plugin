# Artefact prose economy — one home per fact

The single-canonical-home rule ([sdd-methodology.md](sdd-methodology.md) §5, §8) applied to the **process prose** around a change — the commit, the PR body, the changelog, and the review/resolution comments. It exists because agent-to-agent workflows retell the same story three or four times (commit body ≈ PR body ≈ changelog ≈ review comment), and every retelling is a second source of truth: drift waiting to happen and noise for the next agent to wade through.

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

## Writing for an agent reader

Most of this text is written by one agent and read by another (a reviewer agent, a fixer agent). Tune for that reader:

- **Terse, identifier-anchored, complete enough to act on, zero ceremony.** No preamble, no summary-of-a-summary, no restating what a cited artefact already says.
- **A citation beats a retelling.** "Implements `REQ-AUTH-003` / `SPEC-WIRE §4`; rationale in `ADR-0007`." — not a paragraph re-deriving the decision.
- **Keep the essential once.** The one thing that lives *here and nowhere else* stays: the *why* in the commit, the *review lens* in the PR, the *user-facing line* in the changelog, the *finding* in the review comment. Everything that merely echoes a cited artefact is cut.

## What this does *not* touch

- The commit **subject line** may be as descriptive as the Conventional-Commits header needs — the economy rule governs the *body* and the *downstream* artefacts, not the first line.
- Commit / PR / branch **mechanics** belong to the git workflow (superpowers `finishing-a-development-branch`) — see [sdd-with-superpowers.md](sdd-with-superpowers.md). This reference governs only *what prose goes where*, the SDD discipline layered on top.

## Related

- [sdd-methodology.md](sdd-methodology.md) §5 (single canonical home), §8 (cite identifiers when crossing the chain), §11 (duplicated prose is an anti-pattern).
- The scaffolded repo restates the short form in `AGENTS.md` and `docs/ai-workflow.md` so every consuming repo inherits it.

# Artefact prose economy — one home per fact

The single-canonical-home rule ([sdd-methodology.md](sdd-methodology.md) §5) applied to the **process prose** around a change — the commit, the PR body, the changelog, and review threads and replies. Agent-to-agent workflows retell the same story three or four times (commit body ≈ PR body ≈ changelog ≈ review comment), and every retelling is a second source of truth: drift waiting to happen and noise for the next agent.

> **Principle.** Each fact has exactly one home. Every other artefact **cites the identifier** — `REQ` / `SPEC §` / `ADR` / `PROBE` / commit SHA — instead of restating the prose. Prefer a citation over a paragraph.

## Where each kind of prose lives

| Artefact | Its one job | Must **not** contain | Anchors it cites |
|---|---|---|---|
| **Spec §** | Normative *what / how it must behave* (RFC-2119) | Task lists, file paths, PR-style narrative | `REQ` |
| **Commit body** | The *why* of **this** change — rationale, tradeoff — one tight paragraph | A re-listing of the diff; restated spec prose; a finding | `REQ` / `SPEC §` / `ADR` |
| **PR body** | For a person and an agent: Summary, Spec and traceability (or Docs), Verification, Notes for review, Checklist ([development-process.md](templates/development-process.md) § The PR body) | A re-explanation of the spec; a second changelog; a commit list | `REQ` / `SPEC §` |
| **Changelog** | The *user-facing delta* — one subsystem-led line per bullet | Rationale, design narrative (those are in the commit/ADR) | optional `REQ` |
| **Review thread** | One finding on the line it concerns: severity, one sentence, evidence, fix ([review.md](review.md)) | Essays; instances outside the range | `SPEC §` |
| **Thread reply** | `fixed in <sha>` or `declined: <reason>`, one line | A re-description of the fix (it's in the diff) | the commit SHA |

Two rules on that table are enforced by the shared gate ([sdd-check.md](sdd-check.md)) — the `changelog`
and `one-home` families — and are written here so the tool and the reviewer apply the same rule:

- **Changelog bullet.** One sentence, at most about 35 words, leading with the subsystem, no API
  inventory, no rationale. Rationale belongs in the commit body or the ADR.
- **One canonical home.** Each normative sentence, normalised, appears **exactly once** across
  `docs/specifications/**`, and RFC-2119 keywords do not appear outside that tree. A requirement or an ADR
  cites the anchor instead of repeating the sentence. A consolidation that changes a `MUST`'s
  force while moving it is not a move — it is an amendment, and is reviewed as one.

## Prose register

Most of this text is written by one agent and read by another, so the test is whether it is
**unambiguous and complete enough to act on**, not whether it is polished.

- **Plain words. One idea per sentence.** No preamble, no summary of a summary.
- **A citation beats a retelling.** "Implements `REQ-AUTH-003` / `SPEC-WIRE §4`; rationale in `ADR-0007`." — not a paragraph re-deriving the decision.
- **Keep the essential once.** The *why* in the commit, the *review lens* in the PR, the *user-facing line* in the changelog, the *finding* in its thread. Everything that echoes a cited artefact is cut.
- **Explain a term the first time it is used, or drop it.** A term that is neither explained nor droppable
  belongs in the document that defines it, cited by identifier.
- **Never write a bare hash-plus-number** in prose that a hosting platform renders: it becomes a link to an
  unrelated issue or pull request, a false citation.
- A word budget may **never** cut an identifier, a path, or the reason a finding is a finding.

## What this does *not* touch

- The commit **subject line** may be as descriptive as the Conventional-Commits header needs — the economy rule governs the *body* and the *downstream* artefacts, not the first line.
- Commit, PR, and branch **mechanics** — creating the branch, opening the PR, merging, cleaning up
  worktrees — are the git workflow, not this reference. This file governs only *what prose goes where*.

## Related

- [sdd-methodology.md](sdd-methodology.md) §5 (single canonical home), §8 (cite identifiers when crossing the chain), §11 (duplicated prose is an anti-pattern), §13 (the merge gate).
- [review.md](review.md) — the findings file, severities, evidence, and what a review thread carries.
- The scaffolded repo restates the short form in `AGENTS.md` and `docs/ai-workflow.md` so every consuming repo inherits it.

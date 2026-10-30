<!-- Template: the governed entry point for a repo that uses SDD. Written by /sdd-scaffold.
     Keep this THIN. It maps to the canonical docs and defers to them — it does not duplicate them. -->
# AGENTS.md

Instructions for AI coding assistants and the humans reviewing their work in this repository.

## Project

<one-paragraph identity: what this repo is and who it serves>

## Source of truth

The **specification records the contract the code is measured against; the maintainer's instruction
outranks it**: name the sentence once, do the work, amend it in the same change. Without the maintainer
the spec wins, except an *implementation-aligned* section, where code leads and the spec is reconciled in
the same PR. On the formal profile a new capability is *spec-first* (`/sdd-specify`, then
`/sdd-deliver`); everything else on shipped code is code first, the sentence reconciled in the same PR.

## Read

| Document | For |
|---|---|
| [docs/development-process.md](docs/development-process.md) | document kinds, identifiers, the flow, the lanes, the PR body |
| [docs/ai-workflow.md](docs/ai-workflow.md) | the agent loop, orchestration, review, the `/sdd-*` tooling |

Conventions (REQ style, paths, build tool, ground-truth source, `agents:`) are declared in
[`docs/.sdd.yaml`](docs/.sdd.yaml).

## Rules

- Look domain facts up in the ground-truth source `docs/.sdd.yaml` names — never guess.
- Identifiers are immutable once published; normative prose has one canonical home. Never renumber, reuse or duplicate.
- Every document under `docs/` declares its `kind:`; a generated block is regenerated with `sdd-check generate`, never hand-edited.
- Don't settle an open question silently in code — raise a STRAND, draft an ADR, or ask.
- Write short, one home per fact: [docs/development-process.md](docs/development-process.md) § Artefact prose.
- Before claiming done, run `<build_entrypoint> <ci_target>` (the full gate, `<spec_check_target>` included) and read its output.

## Do not touch (yet)

<!-- list areas under active design / pinned / off-limits, or remove this section -->

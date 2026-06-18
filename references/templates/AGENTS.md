<!-- Template: the governed entry point for a repo that uses SDD. Written by /sdd-scaffold.
     Keep this THIN. It maps to the canonical docs and defers to them — it does not duplicate them. -->
# AGENTS.md

Instructions for AI coding assistants and the humans reviewing their work in this repository.

## Project

<one-paragraph identity: what this repo is and who it serves>

## Source of truth

The **specification is the source of truth.** Code is derived from it and measured against it; when they
disagree, the spec wins — except a section explicitly marked *implementation-aligned*. This repo sits on the
**spec-anchored** rung: specs are living, versioned, governing contracts.

## Reading order

| # | Document | For |
|---|----------|-----|
| 1 | [docs/development-process.md](docs/development-process.md) | document kinds, identifiers, the flow, the gates |
| 2 | [docs/ai-workflow.md](docs/ai-workflow.md) | the agent loop, ground-truth lookups, tooling |
| 3 | [docs/requirements/README.md](docs/requirements/README.md) | the capability index (`REQ-*`) |
| 4 | [docs/specifications/README.md](docs/specifications/README.md) | normative behaviour (`SPEC-*`) + conventions |
| 5 | [docs/ci.md](docs/ci.md) | how CI enforces the methodology |

The linked docs are **canonical** — defer to them rather than duplicating their content here.

## Workflow (short form)

`REQ` (what + acceptance) → `SPEC §` (RFC-2119) → `ADR` (if an irreversible fork) → `PLAN` (tasks) →
`CODE + TESTS` (cite IDs) → update spec status + traceability **in the same PR** → update `REQ` status +
archive the plan. New behaviour is *spec-first*; hardening shipped code is *implementation-aligned* (code may
lead, spec updated in the same PR).

## Load-bearing rules

- One canonical home per requirement — the index links, the spec owns the prose. Never duplicate normative text.
- Identifiers are immutable once published. Never renumber or reuse.
- Don't mix document kinds (no tasks in a spec, no file paths in a requirement, one decision per ADR).
- Don't settle an open question silently in code — raise a STRAND, draft an ADR, or ask.
- Look domain facts up in the named ground-truth source (see [`docs/.sdd.yaml`](docs/.sdd.yaml)) — never guess.
- Verify with the full gate before claiming done: `<build_entrypoint> <ci_target>` (includes `spec-check`).

## Tooling

This repo's conventions (REQ style, paths, build tool, ground-truth source) are declared in
[`docs/.sdd.yaml`](docs/.sdd.yaml). The full build gate is `<build_entrypoint> <ci_target>`; the drift gate is
`<build_entrypoint> <spec_check_target>`.

## Do not touch (yet)

<!-- list areas under active design / pinned / off-limits, or remove this section -->

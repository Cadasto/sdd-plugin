# sdd-plugin

**Spec-Driven Development (SDD) for AI coding assistants** — bring the *spec-anchored* workflow to any repository, in any language. The specification, not the code and not the prompt, is the source of truth; code is measured against it, and drift is caught mechanically.

Distributed for both [Claude Code](https://docs.claude.com/en/docs/claude-code/plugins) and [Cursor](https://cursor.com/docs/plugins). Pure Markdown + JSON — no build step and **no MCP server** to wire up.

## What it does

SDD treats a structured, versioned specification as the authoritative description of a system. This plugin encodes the disciplined, *governed* form of SDD — the rung where specs are living, version-controlled contracts — and adds the machinery the industry openly admits it hasn't standardised: **stable identifiers, a machine-checked traceability map, and CI that fails on drift.**

The plugin operates on **documentation** (`docs/*.md`, a requirements index, a traceability map, `AGENTS.md`), so it is **language-agnostic by construction** and **config-driven**: each repo declares its conventions in a small `docs/.sdd.yaml` descriptor, and the same skills serve a flat-numeric library or an area-prefixed service unchanged.

### The loop

```
Constitution → Specify → (Clarify) → Plan → Tasks → Implement → Verify → Archive
```

The plugin owns the **spec / document / traceability layer**; it deliberately leaves the generic engineering loop (exploring, planning, TDD, execution, code review, branch-finishing) to the [superpowers](#works-with-superpowers) plugin. SDD's job is to keep the specification the source of truth and the chain `REQ → SPEC § → ADR → Plan → code → test` intact.

## Components

### Skills

A focused surface — five `/sdd-*` commands plus an always-on router.

| Skill | Use it to… |
|---|---|
| `spec-driven-development` | Auto-invoked awareness/router — explains the methodology, routes intent, maps how SDD complements superpowers, and blocks jumping to code when no requirement or spec exists yet |
| `/sdd-scaffold` | Initialise the SDD `docs/` tree, templates, `AGENTS.md`, process docs, and the `.sdd.yaml` descriptor (idempotent — fills gaps, never clobbers) |
| `/sdd-specify` | The definition layer — capture a capability (`REQ`), write RFC-2119 normative behaviour into the canonical spec (`SPEC §`), and record decisions (`ADR`); assigns identifiers and wires traceability |
| `/sdd-trace` | The traceability gate — assemble the one-shot context bundle for a `REQ`, and report drift / orphans (the `spec-check` analogue). Read-only |
| `/sdd-review` | *Opt-in* — orchestrate a spec-aware review (your installed generic reviewers + the SDD traceability auditor + spec-conformance reviewer), consolidate the findings, and optionally post them to the PR. Delegates generic review and posting; adds the SDD lenses |
| `/sdd-archive` | Close out a finished feature — confirm the document-side Definition of Done, flip the plan to done and archive it **inside the implementing PR**, update the indexes |

### Agents (read-only)

| Agent | Purpose |
|---|---|
| `sdd-traceability-auditor` | Context-isolated full-tree scan for traceability drift and orphans (the `spec-check` analogue) |
| `sdd-doc-reviewer` | Reviews an SDD document (requirement / spec / ADR / plan header — **not** code) for boundary violations: mixed document kinds, duplicated normative prose, missing RFC-2119 force, unstable identifiers |
| `sdd-spec-conformance-reviewer` | Judges whether implemented code satisfies the normative `SPEC §` / `REQ` acceptance criteria it cites, clause by clause — the conformance pass (not code quality, drift, or test-passing) |

### Hooks

- **SessionStart** — detects an SDD repository (`docs/.sdd.yaml`, `docs/specifications/`, or a traceability map) and prints a short context line plus the available `/sdd-*` surface.
- **PostToolUse** *(Claude Code)* — after an edit to a requirement, spec, ADR, plan, or the traceability map, reminds you to keep the traceability chain in sync and run `/sdd-trace`.

### Cursor

`rules/sdd-context.mdc` mirrors the router skill for Cursor; the `.cursor-plugin/plugin.json` manifest declares the shared `skills`/`agents`/`rules` paths and the Cursor hook config.

## Works with superpowers

SDD is **complementary** to the [superpowers](https://github.com/anthropics/claude-code) plugin, not a replacement. Superpowers owns the engineering loop; SDD owns the specification and its traceability:

```
superpowers:brainstorming → SDD:/sdd-specify → superpowers:writing-plans → executing-plans / TDD
   → SDD:/sdd-trace · SDD:/sdd-review (opt-in) + superpowers:verification-before-completion → SDD:/sdd-archive (in the implementing PR) + superpowers:finishing-a-development-branch
```

So planning, TDD, execution, generic verification, code review, and branch-finishing stay with superpowers; SDD records the requirements/specs/decisions, keeps the traceability chain honest, and closes out the documents. One integration detail to know: superpowers writes design docs and plans under `docs/superpowers/` — treat those as working artefacts and route their canonical content into `docs/specifications/` (via `/sdd-specify`) and `docs/plans/`. Full seam: [references/sdd-with-superpowers.md](references/sdd-with-superpowers.md).

## Install

### Claude Code

```
/plugin marketplace add Cadasto/plugin-marketplace
/plugin install sdd@cadasto
```

Or from a local working copy, for development:

```bash
claude plugin add /path/to/sdd-plugin
```

### Cursor

Add this repository as a plugin (**Settings → Plugins**, via Git URL or local path). The repo root contains `.cursor-plugin/plugin.json` declaring the `skills`, `agents`, `rules`, and `hooks` paths.

See [docs/install.md](docs/install.md) for details.

## Quick start

```
/sdd-scaffold                         # lay down the docs/ tree + .sdd.yaml in this repo
/sdd-specify add a capability for <X>  # capture the REQ, write the normative SPEC, record any ADR
# … plan & build with superpowers (writing-plans → executing-plans / TDD); land the plan in docs/plans/
/sdd-trace REQ-...                     # check the traceability chain / drift before merge
/sdd-review --post                     # (opt-in) spec-aware review → post findings to the PR
/sdd-archive REQ-...                   # close out spec, index, and plan — in the implementing PR
```

## The project descriptor

`/sdd-scaffold` writes `docs/.sdd.yaml`; every other skill reads it. It is what keeps the plugin repo-agnostic:

```yaml
sdd:
  req_style: area-prefixed          # area-prefixed | flat-numeric
  req_areas: [FOUND, EHR, CLIN, AUTH]   # only for area-prefixed
  paths:
    requirements: docs/requirements
    specifications: docs/specifications
    adr: docs/adr
    plans: docs/plans
  traceability: docs/specifications/traceability.yaml
  build_entrypoint: make            # make | task | just | npm
  ci_target: ci                     # `make ci`, `task ci`, `npm run ci`
  spec_check_target: spec-check
  ground_truth: "<the authoritative source for this repo's domain facts>"
```

## Documentation

- [docs/install.md](docs/install.md) — install on both hosts
- [docs/testing.md](docs/testing.md) — validate and dogfood
- [docs/versioning.md](docs/versioning.md) — SemVer + release steps
- [docs/authoring.md](docs/authoring.md) — skill / agent / rule authoring conventions
- [references/sdd-methodology.md](references/sdd-methodology.md) — the methodology this plugin encodes

## Prerequisites

None to install the plugin. To get full value, the host repo should expose a single build entry point (`make` / `task` / `just` / `npm`) with a `spec-check` target — `/sdd-scaffold` can stub these for you.

## License

[MIT](LICENSE) © 2026 Cadasto B.V.

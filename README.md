# SDD Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-000?logo=cursor&logoColor=white)](https://cursor.com)
[![Keep a Changelog](https://img.shields.io/badge/Keep%20a%20Changelog-1.1.0-E05735)](CHANGELOG.md)

Spec-Driven Development (SDD) for AI coding assistants, for teams that want the specification, not the code and not the prompt, to be the source of truth in any repository and any language. It adds skills, agents, hooks, a Cursor rule, and a vendored drift gate for **[Claude Code](https://docs.claude.com/en/docs/claude-code/plugins)** and **[Cursor](https://cursor.com/docs/plugins)**, so requirements, RFC-2119 specifications, and ADRs carry stable identifiers, a machine-checked traceability map ties them to code and tests, and CI fails on drift.

The plugin owns the spec, document, and traceability layer and the delivery pipeline that runs on it: plan, worker fan-out, review, triage, and close-out. It operates on documentation (`docs/*.md`, a requirements index, a traceability map, `AGENTS.md`), so it is language-agnostic, and each repository declares its conventions in a small `docs/.sdd.yaml` descriptor. It does not own exploration before a requirement exists; a [general engineering plugin](#optional-a-general-engineering-plugin) can cover that end. Language-specific code review comes from the reviewers each repository declares, such as the go-coding plugin's `go-reviewer` ([example](docs/examples.md#configure-a-go-repository)).

**Requirements.** A Claude Code or Cursor host. The plugin is pure Markdown + JSON: no build step and no MCP server. Installing it needs nothing else. To get full value, the repository you apply SDD to should expose a single build entry point (`make`, `task`, `just`, or `npm`) with a `spec-check` target; `/sdd-scaffold` adds missing targets and wires `spec-check` to the vendored gate, which needs Python 3.9 or later. `/sdd-deliver` opens pull requests with the forge CLI (`gh` on GitHub).

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Components](#components)
- [The loop](#the-loop)
- [Optional: a general engineering plugin](#optional-a-general-engineering-plugin)
- [The project descriptor](#the-project-descriptor)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

## Features

- **Requirements, specs, and decisions:** `/sdd-specify` writes the `REQ`, the RFC-2119 `SPEC §`, and the `ADR`, assigns stable identifiers, and wires the traceability map.
- **Drift gate:** `sdd-check`, one vendored Python file, checks the chain `REQ → SPEC § → ADR → code → test` in both directions and fails the build on drift.
- **Delivery pipeline:** `/sdd-deliver` takes one requirement from the dispatch preconditions through `sdd-implementer` workers and round 0 of review to a draft pull request.
- **One review ledger:** `/sdd-review` and `/sdd-triage` merge findings from the SDD reviewers, the repository's own reviewers, and outside reviewers into one numbered ledger per pull request.
- **Two lanes:** a change that alters a normative statement takes the full lane; a refactor or other maintenance change skips the committed plan and the SDD reviewer agents, and the drift gate runs in both.
- **Close-out and release sweep:** `/sdd-archive` flips the plan to `status: done` inside the implementing pull request; `/sdd-finalize` deletes finished plans at the next version bump.
- **Config-driven:** the `docs/.sdd.yaml` descriptor sets identifier style, paths, build targets, and delivery parameters, so the same skills serve a flat-numeric library or an area-prefixed service unchanged.
- **Session hooks:** an orientation line at session start, a traceability reminder after a spec edit, and a one-shot nudge when a session ends with uncommitted work.

## Installation

**Claude Code:** from the Cadasto marketplace:

```text
/plugin marketplace add Cadasto/plugin-marketplace
/plugin install sdd@cadasto
```

Or load a local working copy for a single session: `claude --plugin-dir /path/to/sdd-plugin`.

**Cursor:** add the plugin through Cursor's plugin flow (**Settings → Plugins**), from a Git URL or a local path. The repository root contains `.cursor-plugin/plugin.json`, which declares the `skills`, `agents`, `rules`, and `hooks` paths.

See [docs/install.md](docs/install.md) for marketplace, local-development, update, and Cursor install details.

## Quick start

```text
/sdd-scaffold                          # lay down the docs/ tree + .sdd.yaml in this repo
/sdd-specify add a capability for <X>  # capture the REQ, write the normative SPEC, record any ADR
/sdd-deliver REQ-...                   # preconditions → plan on the branch → workers → round 0 → draft PR
/sdd-review <PR> --panel               # print the prompt blocks for outside reviewers (--post writes the ledger)
/sdd-triage <PR>                       # each review round: merge, verify, fix, resolve, re-request
/sdd-archive REQ-...                   # close out spec status, REQ status, traceability, and the plan — in its PR
/sdd-finalize                          # at the next version bump, before the tag: sweep finished plans
```

The walkthrough is [docs/quick-start.md](docs/quick-start.md); prompts by use case are in [docs/examples.md](docs/examples.md).

## Components

### Skills

Eight `/sdd-*` skills, each also usable as a slash command, plus an always-on router.

| Skill | Use it to… |
|---|---|
| `spec-driven-development` | Auto-invoked awareness and router: explains the methodology, routes intent, states where an optional general engineering plugin still fits, and blocks jumping to code when no requirement or spec exists yet |
| `/sdd-scaffold` | Initialise the SDD `docs/` tree, templates, `AGENTS.md`, process docs, and the `.sdd.yaml` descriptor, suggesting `agents.reviewers` from the build manifests (idempotent: fills gaps, never clobbers) |
| `/sdd-specify` | The definition layer: capture a capability (`REQ`), write RFC-2119 normative behaviour into the canonical spec (`SPEC §`), and record decisions (`ADR`); assigns identifiers and wires traceability |
| `/sdd-deliver` | The delivery driver: check the dispatch preconditions, write the plan on the branch, fan `sdd-implementer` workers out per the descriptor's `agents:` block, gate each task by lane, open round 0 of the ledger and the draft PR, then close out and mark it ready |
| `/sdd-review` | Lane-aware review orchestration: dispatch the SDD reviewers plus the repo's declared reviewers on the full lane, the declared reviewers alone on the maintenance lane, and write one numbered ledger; `--panel` prints the canonical prompt blocks |
| `/sdd-triage` | One review round: enumerate every comment channel, merge the findings into the ledger, verify before fixing, sweep the pattern class, fix in this PR, resolve, and print the re-review prompts |
| `/sdd-trace` | The traceability gate: assemble the one-shot context bundle for a `REQ`, and report drift and orphans (the `spec-check` analogue). Report-only |
| `/sdd-archive` | The close-out inside the implementing PR: flip the plan to `status: done` in place, set the `SPEC §` and `REQ` statuses and the traceability map, and fill the PR body. No move, no index |
| `/sdd-finalize` | The release sweep: as the first step of a version bump, before the tag, delete the `done` and `abandoned` plans after an inbound-link check |

### Agents

The three reviewers declare no `Write` or `Edit`. `sdd-doc-reviewer` holds only `Read`, `Grep`, and `Glob`, so it is read-only outright. The other two add `Bash` for read-only scoping (`git diff`, `git log`), which makes their no-edit guarantee a contract they keep rather than a sandbox that enforces it. `sdd-implementer` is the one agent that writes. It declares a denylist rather than an allowlist: `Agent` and `Task` are denied, so it cannot dispatch further agents, and it inherits every other tool the host offers, the repository's MCP servers included.

Claude Code enforces these grants. Cursor's subagent frontmatter carries no tool grant, and a subagent inherits every tool, so on Cursor both the reviewers' no-edit rule and the implementer's no-spawn rule are contracts the agent bodies state, not sandboxes. Cursor's `subagentStart` hook is the enforceable path and is not shipped in 0.6.0.

| Agent | Purpose |
|---|---|
| `sdd-traceability-auditor` | Context-isolated full-tree scan for traceability drift and orphans (the `spec-check` analogue) |
| `sdd-doc-reviewer` | Reviews an SDD document (requirement, spec, or ADR; **not** code) for boundary violations: mixed document kinds, duplicated normative prose, missing RFC-2119 force, unstable identifiers |
| `sdd-spec-conformance-reviewer` | Judges whether implemented code satisfies the normative `SPEC §` and `REQ` acceptance criteria it cites, clause by clause: the conformance pass (not code quality, drift, or test-passing) |
| `sdd-implementer` | Implements one bounded task from a delivery brief: reads the `SPEC §` the brief cites, cites `REQ`/`PROBE` ids in test names and its commit message, verifies with the command the brief names, and returns `En-route findings` |

### The gate

`sdd-check` is the plugin's drift gate: one vendored, standard-library-only Python file. It checks the traceability chain in both directions, lints the prose rules a machine can apply (document kinds, RFC-2119 keyword placement and grammar, single canonical home, link targets, changelog bullets), regenerates the requirements, specifications, and ADR indexes and the requirement status lines from the map, prints a requirement's context bundle, and tests itself against its own fixtures.

`/sdd-scaffold` copies it into the repository at the descriptor's `check.script` (`scripts/sdd-check.py` by default) and pins the copy's version in `check.version`. The gate refuses to pass when the vendored copy and the pin disagree, so a stale copy cannot keep a build green.

Run it directly with:

- `sdd-check check`
- `sdd-check generate`: rewrite the generated blocks from one source; `--verify` reports without writing
- `sdd-check context <REQ>`: the index row, the record, the canonical section, and any open strand
- `sdd-check selftest`

Full contract: [references/sdd-check.md](references/sdd-check.md).

### Hooks

- **SessionStart:** detects an SDD repository (`docs/.sdd.yaml`, `docs/specifications/`, or a traceability map) and prints a context line, the available `/sdd-*` surface, and a short orientation: branch and tree state, active plans, open pull requests when the forge CLI answers, and the drift gate's verdict when it is vendored.
- **PostToolUse** *(Claude Code)*: after an edit to a requirement, spec, ADR, plan, or the traceability map, reminds you to keep the traceability chain in sync: `/sdd-trace` to check it, `/sdd-specify`, `/sdd-archive`, or the vendored `generate` command to regenerate. Cursor's `afterFileEdit` event has no output channel, so there is no reminder on Cursor ([install notes](docs/install.md#cursor)).
- **Stop** *(Claude Code)* / **stop** *(Cursor)*: a one-shot nudge when the session made no commit and leaves uncommitted changes in an SDD repository; the second stop in the same session passes silently. Opt out per repo with `hooks.stop_nudge: false` in `docs/.sdd.yaml`.

### Cursor

`rules/sdd-context.mdc` mirrors the router skill for Cursor; the `.cursor-plugin/plugin.json` manifest declares the shared `skills`, `agents`, and `rules` paths and the Cursor hook config.

## The loop

```text
Constitution → Specify → (Clarify) → Plan → Tasks → Implement → Verify → Archive
```

SDD treats a structured, versioned specification as the authoritative description of a system. This plugin encodes the *spec-anchored* rung, where specs are living, version-controlled contracts, and adds the governance machinery that mainstream toolkits such as GitHub Spec Kit, AWS Kiro, and Tessl leave to the team: **stable identifiers, a machine-checked traceability map, and CI that fails on drift.** Its job is to keep the specification the source of truth and the chain `REQ → SPEC § → ADR → code → test` intact from the first requirement to the merged PR.

The rules behind each step, the rigour ladder, and the sources are in the [methodology](references/sdd-methodology.md#2-the-canonical-loop).

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is optional: exploration workflows help before `/sdd-specify`, and this plugin covers everything after that. The router skill `spec-driven-development` states where the seam lies.

## The project descriptor

`/sdd-scaffold` writes `docs/.sdd.yaml`; every other skill reads it. It is what keeps the plugin repo-agnostic. An excerpt (the full template, with every key, is [references/templates/sdd.yaml](references/templates/sdd.yaml)):

```yaml
sdd:
  profile: full                     # full | lightweight

  req_style: area-prefixed          # area-prefixed | flat-numeric
  req_areas: [FOUND, EHR, CLIN, AUTH]   # only for area-prefixed
  excluded_areas: []                # area-prefixed only; tokens deliberately not areas
  doc_kinds: [requirement, specification, adr, plan, guide, analysis, operations, reference, upstream]
  default_mode: spec-first          # the mode a specification has when its frontmatter names none

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

  check:
    script: scripts/sdd-check.py    # where /sdd-scaffold vendors the gate
    version: "0.6.0"                # must equal the vendored tool's own version
    families: {}                    # per-family error | warn | off overrides — see references/sdd-check.md

  # Delivery parameters. /sdd-deliver and /sdd-review read these instead of asking.
  # Every value here is an EXAMPLE — no model and no reviewer is required by the plugin.
  agents:
    worker_model: inherit           # per-dispatch model override; inherit = no override, or a host model id
    max_parallel_workers: 3
    worktree_per_worker: true       # parallel, mutating tasks only
    worker_skills: []               # skills named in the worker's brief, e.g. [go-coding:go-testing]
    reviewers: []                   # this repo's own language reviewers, by agent name
    task_review: lane               # on | off | lane  (lane = on for full, off for maintenance)
    review_panel:                   # who reviews the PR, per lane; names are prompt targets, not integrations
      full: [claude, cursor]
      maintenance: [claude]
```

## Development

Validate locally before opening a pull request:

```bash
./scripts/validate.sh             # manifests, dual-host parity, frontmatter, links, then the hook tests
claude plugin validate .          # manifest + component structure
```

What each check covers and the manual smoke test are in [docs/testing.md](docs/testing.md); component conventions are in [docs/authoring.md](docs/authoring.md); release steps are in [docs/versioning.md](docs/versioning.md).

## Documentation

- [docs/quick-start.md](docs/quick-start.md): one capability from idea to a ready pull request
- [docs/examples.md](docs/examples.md): prompts by use case
- [docs/install.md](docs/install.md): install on both hosts
- [docs/upgrading.md](docs/upgrading.md): moving a repository from 0.4.x or 0.5.x
- [docs/testing.md](docs/testing.md): validate and dogfood
- [docs/versioning.md](docs/versioning.md): SemVer and release steps
- [docs/authoring.md](docs/authoring.md): skill, agent, and rule authoring conventions
- [references/sdd-methodology.md](references/sdd-methodology.md): the methodology this plugin encodes
- [references/artefact-prose.md](references/artefact-prose.md): the ledger and the prose rules

## License

[MIT](LICENSE) © 2026 Cadasto B.V.

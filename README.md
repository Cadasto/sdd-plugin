# SDD Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.8.1-blue)](CHANGELOG.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-000?logo=cursor&logoColor=white)](https://cursor.com)
[![Keep a Changelog](https://img.shields.io/badge/Keep%20a%20Changelog-1.1.0-E05735)](CHANGELOG.md)

Spec-Driven Development (SDD) for AI coding assistants, for teams that want the specification, not the code and not the prompt, to be the source of truth in any repository and any language. It adds skills, agents, hooks, a Cursor rule, and a vendored drift gate for **[Claude Code](https://docs.claude.com/en/docs/claude-code/plugins)** and **[Cursor](https://cursor.com/docs/plugins)**, so requirements, RFC-2119 specifications, and ADRs carry stable identifiers, a machine-checked traceability map ties them to code and tests, and CI fails on drift.

The plugin owns the spec, document, and traceability layer and the delivery pipeline that runs on it: worker fan-out, review, triage, and close-out. It operates on documentation (`docs/*.md`, a requirements index, a traceability map, `AGENTS.md`), so it is language-agnostic, and each repository declares its conventions in a small `docs/.sdd.yaml` descriptor. It does not own exploration before a requirement exists; a [general engineering plugin](#optional-a-general-engineering-plugin) can cover that end. Language-specific code review comes from the reviewers each repository declares, such as the go-coding plugin's `go-reviewer` ([example](docs/examples.md#configure-a-go-repository)).

**Requirements.** A Claude Code or Cursor host. The plugin is pure Markdown + JSON: no build step and no MCP server. Installing it needs nothing else. To get full value, the repository you apply SDD to should expose a single build entry point (`make`, `task`, `just`, or `npm`) with a `spec-check` target; `/sdd-scaffold` adds missing targets and wires `spec-check` to the vendored gate, which needs Python 3.9 or later. Mirroring findings to a pull request needs `gh` (GitHub) or `az` with the `azure-devops` extension (Azure DevOps); with neither, everything works on the local findings file.

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
- **Delivery pipeline:** `/sdd-deliver` takes one change from the dispatch gate through `sdd-implementer` workers and a first review pass to a draft pull request, and closes it out (`--close-out`) inside that pull request.
- **A findings file per branch:** `/sdd-review` writes findings, each with its evidence, into one file per branch in the clone's git directory, which every worktree, Claude, Cursor and you can all read; `sdd-pr` makes every change to it, so nobody edits it by hand. `sdd-pr` mirrors the critical and important ones to the pull request's inline threads on GitHub or Azure DevOps, and tells you what is open, whether the branch is mergeable, and what to run next. It also posts one short review per pass, its summary on top even when the pass found nothing, and keeps a review-state block in the pull request's body, so the page shows the verdict without the file.
- **Two profiles:** formal (requirements, RFC-2119 specifications, the traceability map and the drift gate) and informative (a knowledge base plus one binding architecture document, for repositories where code leads).
- **Two lanes:** on the formal profile, a change that alters a normative statement takes the full lane; a refactor or other maintenance change skips the conformance reviewer, a changed document is still read for consistency, and the drift gate runs in both.
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
/sdd-deliver REQ-...                   # preconditions → workers → review pass → draft PR
/sdd-review --panel                    # print the prompt blocks for outside reviewers
/sdd-triage                            # work the open findings: verify, fix, flip, mirror
/sdd-deliver <PR> --close-out          # set the REQ shipped and write the PR body — in its PR
```

The walkthrough is [docs/quick-start.md](docs/quick-start.md); prompts by use case are in [docs/examples.md](docs/examples.md).

## Components

### Skills

Six `/sdd-*` skills, each also usable as a slash command, plus an always-on router.

| Skill | Use it to… |
|---|---|
| `spec-driven-development` | Auto-invoked awareness and router: explains the methodology, routes intent, states where an optional general engineering plugin still fits, and blocks jumping to code when no requirement or spec exists yet |
| `/sdd-scaffold` | Initialise the SDD `docs/` tree, templates, `AGENTS.md`, process docs, and the `.sdd.yaml` descriptor, suggesting `agents.reviewers` from the build manifests (idempotent: fills gaps, never clobbers) |
| `/sdd-specify` | The definition layer: capture a capability (`REQ`), write RFC-2119 normative behaviour into the canonical spec (`SPEC §`), and record decisions (`ADR`); assigns identifiers and wires traceability |
| `/sdd-deliver` | The delivery driver: the dispatch gate, `sdd-implementer` workers per the descriptor's `agents:` block, the per-task gate, the first review pass, the draft PR; `--close-out` sets the `REQ` to `shipped` (a `SPEC §` is promoted only when you confirm) and writes the PR body |
| `/sdd-review` | One review pass over the whole branch, or with `--since-last` over the commits since this agent's last pass: dispatch the reviewers the profile, lane and changed files call for, write their findings into the branch's findings file, and mirror the blocking ones to the pull request; `--panel` prints the canonical prompt blocks |
| `/sdd-triage` | Work the open findings: verify each, fix in this branch, flip the lines, mirror to the pull request, and after your review run one scoped re-review when anything changed |
| `/sdd-trace` | The traceability gate: assemble the one-shot context bundle for a `REQ`, and report drift and orphans (the `spec-check` analogue); `--audit` dispatches the isolated whole-tree audit. Report-only |

### Agents

The three reviewers declare no `Write` or `Edit` and return findings-file lines with evidence. `sdd-doc-reviewer` holds only `Read`, `Grep`, and `Glob`, so it is read-only outright. The other two also hold `Bash`, to run tests and, for the conformance reviewer, to remove a guard in a scratch worktree. Because `Bash` can write, not editing is a promise those two keep rather than a limit the host enforces. `sdd-implementer` is the one agent that writes. It declares a denylist rather than an allowlist: `Agent` and `Task` are denied, so it cannot dispatch further agents, and it inherits every other tool the host offers, the repository's MCP servers included.

Claude Code enforces these grants. Cursor's subagent frontmatter carries no tool grant, and a subagent inherits every tool, so on Cursor both the reviewers' no-edit rule and the implementer's no-spawn rule are contracts the agent bodies state, not sandboxes. Cursor's `subagentStart` hook is the enforceable path and is not shipped yet.

| Agent | Purpose |
|---|---|
| `sdd-traceability-auditor` | Context-isolated full-tree scan for traceability drift and orphans, dispatched by `/sdd-trace --audit` |
| `sdd-doc-reviewer` | Reviews the changed hunks of the documents a change touched (**not** code): two homes for one rule, sentences that disagree, missing RFC-2119 force; consistency only on the informative profile |
| `sdd-spec-conformance-reviewer` | Judges whether changed code satisfies the binding sentences it cites, clause by clause, running the tests and removing each touched guard as evidence |
| `sdd-implementer` | Implements one bounded task from a brief: reads the quoted clauses, writes each test first and proves it can fail, cites `REQ`/`PROBE` ids in test names and its commit message, and returns `En-route findings` |

### The gate

`sdd-check` is the plugin's drift gate: one vendored, standard-library-only Python file. It checks the traceability chain in both directions, lints the prose rules a machine can apply (document kinds, RFC-2119 keyword placement and grammar, single canonical home, link targets, changelog bullets), regenerates the requirements, specifications, and ADR indexes and the requirement status lines from the map, prints a requirement's context bundle, and tests itself against its own fixtures.

`/sdd-scaffold` copies it into the repository at the descriptor's `check.script` (`scripts/sdd-check.py` by default) and pins the copy's version in `check.version`. The gate refuses to pass when the vendored copy and the pin disagree, so a stale copy cannot keep a build green.

Run it directly with:

- `sdd-check check`
- `sdd-check generate`: rewrite the generated blocks from one source; `--verify` reports without writing
- `sdd-check context <REQ>`: the index row, the record, the canonical section, and any open strand
- `sdd-check selftest`

Full contract: [references/sdd-check.md](references/sdd-check.md).

### The review tool

`sdd-pr` (`python3 <plugin root>/tools/sdd-pr.py`, not vendored) keeps a branch's findings file and its pull request in step: `status` prints the file's path, the open counts, `Mergeable: yes|no` and the next command, and `--write-body` rewrites the review state in the pull request's body; `scope` prints the range a review pass reads; `add`, `flip`, `record` and `rename` write the file, as `pull`, `post` and `resolve` do, so nobody edits it by hand; `pull`, `post` and `resolve` mirror findings to and from the inline threads on GitHub or Azure DevOps. With `forge: none`, `status` and `scope` work from the file alone. Contract: [references/review.md](references/review.md).

### Hooks

- **SessionStart:** detects an SDD repository (`docs/.sdd.yaml`, `docs/specifications/`, or a traceability map) and prints a context line, the available `/sdd-*` surface, and a short orientation: the profile, the plugin version and any mismatch with the vendored gate, branch and tree state, the branch's open findings, and the drift gate's verdict when it is vendored.
- **PostToolUse** *(Claude Code)*: after an edit to a requirement, spec, ADR, or the traceability map, reminds you to keep the traceability chain in sync: `/sdd-trace` to check it, `/sdd-specify`, `/sdd-deliver --close-out`, or the vendored `generate` command to regenerate; on the informative profile only a constitution edit prints one. Cursor's `afterFileEdit` event has no output channel, so there is no reminder on Cursor ([install notes](docs/install.md#cursor)).
- **Stop** *(Claude Code)* / **stop** *(Cursor)*: a one-shot nudge when the session made no commit and leaves uncommitted changes in an SDD repository; the second stop in the same session passes silently. Opt out per repo with `hooks.stop_nudge: false` in `docs/.sdd.yaml`.

### Cursor

`rules/sdd-context.mdc` mirrors the router skill for Cursor; the `.cursor-plugin/plugin.json` manifest declares the shared `skills`, `agents`, and `rules` paths and the Cursor hook config.

## The loop

```text
Constitution → Specify → (Clarify) → Plan → Tasks → Implement → Verify → Close out
```

SDD treats a structured, versioned specification as the authoritative description of a system. This plugin encodes the *spec-anchored* rung, where specs are living, version-controlled contracts, and adds the governance machinery that mainstream toolkits such as GitHub Spec Kit, AWS Kiro, and Tessl leave to the team: stable identifiers, a machine-checked traceability map, and CI that fails on drift. Its job is to keep the specification the source of truth and the chain `REQ → SPEC § → ADR → code → test` intact from the first requirement to the merged PR.

The rules behind each step, the rigour ladder, and the sources are in the [methodology](references/sdd-methodology.md#2-the-canonical-loop).

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is optional: exploration workflows help before `/sdd-specify`, and this plugin covers everything after that. The router skill `spec-driven-development` states where the seam lies.

## The project descriptor

`/sdd-scaffold` writes `docs/.sdd.yaml`, and every other skill reads it; that is how one plugin serves repositories with different conventions. An excerpt (the full template, with every key, is [references/templates/sdd.yaml](references/templates/sdd.yaml)):

```yaml
sdd:
  profile: formal                   # formal | informative

  req_style: area-prefixed          # area-prefixed | flat-numeric
  req_areas: [FOUND, AUTH, API, DATA]   # only for area-prefixed
  excluded_areas: []                # area-prefixed only; tokens deliberately not areas
  doc_kinds: [requirement, specification, adr, guide, analysis, operations, reference, upstream, constitution]
  default_mode: spec-first          # the mode a specification has when its frontmatter names none

  paths:
    requirements: docs/requirements
    specifications: docs/specifications
    adr: docs/adr
    constitution: docs/architecture.md   # informative profile only
  traceability: docs/specifications/traceability.yaml
  forge: auto                       # auto | github | azure-devops | none
  build_entrypoint: make            # make | task | just | npm
  ci_target: ci                     # `make ci`, `task ci`, `npm run ci`
  spec_check_target: spec-check
  ground_truth: "<the authoritative source for this repo's domain facts>"

  check:
    script: scripts/sdd-check.py    # where /sdd-scaffold vendors the gate
    version: "0.8.1"                # must equal the vendored tool's own version
    families: {}                    # per-family error | warn | off overrides — see references/sdd-check.md

  # Delivery parameters. /sdd-deliver and /sdd-review read these instead of asking.
  # Every value here is an EXAMPLE — no model and no reviewer is required by the plugin.
  agents:
    worker_model: inherit           # per-dispatch model override; inherit = no override, or a host model id
    max_parallel_workers: 3
    worktree_per_worker: true       # parallel, mutating tasks only
    worker_skills: []               # skills named in the worker's brief, e.g. [go-coding:go-testing]
    reviewers: []                   # this repo's own language reviewers, by agent name; or a map of path patterns to names
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
- [docs/upgrading.md](docs/upgrading.md): moving a repository from an earlier version
- [docs/testing.md](docs/testing.md): validate and dogfood
- [docs/versioning.md](docs/versioning.md): SemVer and release steps
- [docs/authoring.md](docs/authoring.md): skill, agent, and rule authoring conventions
- [references/sdd-methodology.md](references/sdd-methodology.md): the methodology this plugin encodes
- [references/review.md](references/review.md): the findings file, severities, evidence and the forge mirror
- [references/artefact-prose.md](references/artefact-prose.md): the prose rules

## License

[MIT](LICENSE) © 2026 Cadasto B.V.

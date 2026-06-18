# AI Guidelines: SDD Plugin

This file provides guidance to AI coding assistants (Claude Code, Cursor, and compatible tools that read `AGENTS.md`) working in this repository. It is the **canonical** instruction set; `.claude/CLAUDE.md` and any host-specific instruction files defer to it (`.claude/CLAUDE.md` imports this file via `@../AGENTS.md`).

## Project Overview

The **SDD Plugin** (`sdd`) is an AI plugin by Cadasto B.V. that brings **Spec-Driven Development** to AI coding assistants — driving implementation from an explicit, versioned specification rather than ad-hoc prompts. It targets **both Claude Code and Cursor** from a single shared component set, and is **pure Markdown + JSON** with **no MCP backend**.

It is **general-purpose and language-agnostic** by design: the skills operate on documentation (`docs/*.md`, a requirements index, a traceability map, `AGENTS.md`), and each consuming repo declares its conventions in a small `docs/.sdd.yaml` descriptor so the same skills serve a flat-numeric library or an area-prefixed service unchanged.

## Domain Context

This plugin encodes the **spec-anchored** rung of SDD: the specification — not the code, not the prompt — is the source of truth; code is measured against it; and the governance machinery the mainstream toolkits omit (stable identifiers, a machine-checked traceability map, and CI that fails on drift) is built in.

The authoritative, public-safe statement of the methodology — the rigour ladder, the seven document kinds and their boundary rules, RFC-2119 discipline, the identifier scheme, the two status axes, the traceability chain, the two source-of-truth modes, the plan DoR/DoD, and the anti-patterns — lives in **[`references/sdd-methodology.md`](references/sdd-methodology.md)**. Skills cite it rather than restating it; treat it as canonical and keep the rules in one place. The machine-readable formats (`traceability.yaml` records and the `.sdd.yaml` descriptor) are in **[`references/traceability-schema.md`](references/traceability-schema.md)**.

The loop: `Specify → (Clarify) → Plan → Tasks → Implement → Verify → Archive`, under a constitution of document-kind boundaries.

## Public-safety constraint (IMPORTANT)

This repository may be published. **All content must read as general-purpose, language-agnostic SDD tooling.** Do **not**:
- name specific internal or consumer repositories,
- reproduce absolute filesystem paths or local directory layouts,
- embed organisation-private project details.

Ground claims in the public methodology lineage (GitHub Spec Kit, AWS Kiro, the Thoughtworks rigour ladder, Sean Grove's *The New Code*, RFC-2119) — see the Sources section of `references/sdd-methodology.md`. This constraint applies to every skill, agent, doc, template, and reference.

## Repository Layout

This repo supports **both Claude Code and Cursor**; shared assets (skills, agents, references) are used by both. Host-specific manifests and hook configs are separate.

- **Claude manifest**: `.claude-plugin/plugin.json` — `name` (`sdd`), `version`, `description`, `author` (an **object** `{name, url}` — `claude plugin validate` rejects a bare string), `license`, `repository`, `keywords`. Claude Code discovers components from the **default folders** (`skills/`, `agents/`, `hooks/`) automatically.
- **Cursor manifest**: `.cursor-plugin/plugin.json` — same metadata **plus** explicit top-level path keys (`skills`, `agents`, `rules`, `hooks`). No `mcpServers` — this plugin has no MCP backend. Keep `name`/`version`/`description`/`author` identical to the Claude manifest.
- **Skills**: `skills/<name>/SKILL.md` — shared by both hosts. The `sdd-*` skills carry `argument-hint` + `allowed-tools` so they are both auto-invoked on intent and user-invocable as `/sdd-*`; `spec-driven-development` is the always-on router. **Skills use `allowed-tools:` (the Claude Code skill/command key — Cursor reads it too); only agents use `tools:`.**
- **Agents**: `agents/<name>.md` — read-only, context-isolated specialists (`tools:` not `allowed-tools:`).
- **References**: `references/` — the canonical methodology, the schemas, and `references/templates/` (the files `sdd-scaffold` emits). Skills cite these instead of duplicating rules.
- **Cursor rules**: `rules/*.mdc` — Cursor-only rule guidance (`description` / `globs` / `alwaysApply`), referenced by the Cursor manifest's `rules` path. Shipped: `rules/sdd-context.mdc`.
- **Claude hooks**: `hooks/hooks.json` — object `{ "hooks": { "SessionStart": [...], "PostToolUse": [...] } }`; use `${CLAUDE_PLUGIN_ROOT}` in command paths.
- **Cursor hooks**: `hooks/cursor-hooks.json` — object `{ "hooks": { "sessionStart": [...], "afterFileEdit": [...] } }`; the command runs from the plugin root (**workspace-relative**, **not** `${CLAUDE_PLUGIN_ROOT}`).
- **Shared hook scripts**: `hooks/session-start.sh` (detects an SDD repo, prints context + the `/sdd-*` surface) and `hooks/spec-edit-reminder.sh` (reminds to sync traceability after a doc edit). Both host-agnostic; both exit 0 always.
- **Claude settings**: `.claude/settings.json` enables the maintainer plugins used while developing this repo (skill-creator, superpowers, plugin-dev, claude-md-management) and pre-approves the validate commands; `.claude/CLAUDE.md` imports this file via `@../AGENTS.md`. `.claude/settings.local.json` is gitignored.
- **Validation**: `scripts/validate.sh` (graceful local wrapper — warns and skips if Python is absent) runs `scripts/validate.py`, which checks both manifests, dual-host parity, declared component paths, kebab-case names, hook-config JSON, and skill/agent/rule frontmatter. CI pins Python and runs the validator strictly ([`.github/workflows/validate.yml`](.github/workflows/validate.yml)).
- **Contributor docs**: `docs/` holds committed human-facing references — [install](docs/install.md), [testing](docs/testing.md), [versioning](docs/versioning.md), [authoring](docs/authoring.md). `.github/` holds issue + PR templates, `copilot-instructions.md`, and the validate workflow. (Planning/research working notes under `docs/plans/` and `docs/research/` are gitignored — not part of the published plugin.)

## Components

Scope is the **spec / document / traceability layer**. The generic engineering loop (explore, plan, TDD, execute, generic verify, code review, branch-finish) is intentionally **not** reimplemented — it is delegated to the **superpowers** plugin (see "Works with superpowers" below). This keeps the surface small and non-colliding.

### Skills (5)
| Skill | Purpose |
|-------|---------|
| `spec-driven-development` | Auto-invoked awareness/router — explains the methodology, routes intent, maps the SDD↔superpowers boundary, and blocks code-first work when no `REQ`/spec exists |
| `sdd-scaffold` | Initialise the SDD `docs/` tree, templates, `AGENTS.md`, process docs, and the `.sdd.yaml` descriptor (idempotent); records the superpowers path-redirect |
| `sdd-specify` | The definition layer — author the `REQ` (capability + acceptance), the canonical RFC-2119 `SPEC §`, and the `ADR`; assign identifiers; wire traceability |
| `sdd-trace` | The traceability gate — one-shot context bundle for a `REQ` + whole-tree drift/orphan report (the `spec-check` analogue). Read-only; defers generic test/build verification to superpowers |
| `sdd-archive` | The close-out — confirm the document-side Definition of Done, flip the plan to done and archive it, update the indexes; defers merge/PR to superpowers |

### Agents (2, read-only)
| Agent | Purpose |
|-------|---------|
| `sdd-traceability-auditor` | Context-isolated full-tree scan for traceability drift and orphans (the `spec-check` analogue) |
| `sdd-doc-reviewer` | Reviews a single SDD document (REQ/SPEC/ADR/plan header — **not** code; code review is superpowers) for boundary violations (mixed kinds, duplicated prose, missing RFC-2119 force, unstable identifiers) |

### Works with superpowers
SDD is complementary to the **superpowers** plugin. Combined flow:
`superpowers:brainstorming → sdd-specify → superpowers:writing-plans → executing-plans/TDD → sdd-trace + superpowers:verification-before-completion → sdd-archive + superpowers:finishing-a-development-branch`.
Superpowers owns planning/TDD/execution/verification/code-review/branch-finishing; SDD owns the documents and traceability. Superpowers writes design docs + plans under `docs/superpowers/` — treat them as working artefacts and route the canonical content into `docs/specifications/` (via `sdd-specify`) and `docs/plans/`. Full seam + the path redirect: [`references/sdd-with-superpowers.md`](references/sdd-with-superpowers.md).

### Hooks
- **SessionStart** — detects an SDD repository and prints a context line plus the `/sdd-*` surface (or a scaffold pointer in a non-SDD repo with a `docs/` dir).
- **PostToolUse** (Claude Code) — after an edit to a requirement/spec/ADR/plan or the descriptor/traceability map, reminds to keep the chain in sync and run `/sdd-trace`. Cursor uses the `afterFileEdit` event equivalent.

## Development

### Testing & validating

No build step — pure Markdown + JSON. Validate and dogfood locally:

```bash
./scripts/validate.sh             # manifests, dual-host parity, frontmatter (warns & skips if Python is absent)
claude plugin validate .          # manifest + component structure (no Python needed)
claude plugin add /path/to/sdd-plugin   # install locally
```

Then run the loop (`/sdd-scaffold` → `/sdd-specify` → plan/build via superpowers → `/sdd-trace` → `/sdd-archive`) on a throwaway repo, and verify skill auto-triggering and the agents on both hosts. Fuller guidance: [`docs/`](docs/). CI runs `scripts/validate.py` strictly on every push/PR.

### File Conventions
- Skills go in `skills/<name>/SKILL.md`; agents in `agents/<name>.md`; Cursor rules in `rules/<name>.mdc`.
- Shared reference material and scaffold templates live in top-level **`references/`** (not under `commands/`). The legacy `commands/` folder is not used — slash commands are authored as user-invoked skills.
- All markdown components use YAML frontmatter; frontmatter `name` MUST equal the directory (skills) or filename stem (agents).
- `allowed-tools:` (skills) pre-approves tools; **agents use `tools:`** — `allowed-tools:` in an agent file is ignored and the agent silently inherits all tools.
- Skill bodies are imperative and **cite `references/sdd-methodology.md`** rather than restating rules; every `sdd-*` skill **reads `docs/.sdd.yaml` first** instead of hard-coding paths/identifier styles.

### Documentation Sync
When adding or renaming components, update in lockstep: **AGENTS.md** (component tables), **README.md** (tables), **CHANGELOG.md**, and the `/sdd-*` list in **`hooks/session-start.sh`**. Cursor uses the same skills/agents/rules paths; no separate Cursor-only list is required.

### Versioning
Plugin version (and, for consistency, description and author) must be kept in sync in **both** `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`. Follow Semantic Versioning; update both manifests and **CHANGELOG.md** when releasing. See [docs/versioning.md](docs/versioning.md).

### CHANGELOG style
- Entries go under `## [Unreleased]` while work is in flight and fold into the next `## [X.Y.Z] - YYYY-MM-DD` section at release.
- Keep a Changelog groups in order: **Added, Changed, Deprecated, Removed, Fixed, Security**. Omit empty groups.
- One line per bullet, leading with the subsystem (`Skills:`, `Agents:`, `References:`) and using backticks for file/skill/key names. No rationale (that belongs in commits/PRs).

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), e.g. `feat(skills): add sdd-specify skill`, `fix(agents): correct tools list in sdd-doc-reviewer`. Scopes: `skills`, `agents`, `hooks`, `references`, `docs`.

### Branching
Use feature branches and pull requests. Validation runs on every push/PR.

## Gotchas

- **Agents use `tools:`, not `allowed-tools:`.** In an agent file `allowed-tools:` is ignored and the agent silently inherits *all* tools. Both shipped agents are read-only — keep them that way.
- **`author` in `plugin.json` must be an object** (`{name, url}`); `claude plugin validate` rejects a bare string.
- **`${CLAUDE_PLUGIN_ROOT}` is Claude-Code-only.** Cursor hook commands stay workspace-relative (`bash hooks/session-start.sh`) — don't "fix" them to use it. For locating bundled templates, `sdd-scaffold` prefers `${CLAUDE_PLUGIN_ROOT}` (or a Cursor plugin-root variable, *if* the host exposes one — unconfirmed) and falls back to a Glob for the installed templates, which is the host-agnostic path. Keep both hook configs in step.
- **One canonical home for the rules: `references/sdd-methodology.md`.** Skills keep only their procedure and cite the reference. When the methodology changes, update the reference — don't re-inline rule text into each skill.
- **`spec-driven-development` is deliberately distinct from the plugin name `sdd`.** Naming the router skill `sdd` would collide (`sdd:sdd`). The skill/command prefix is `sdd-`; the router is the full phrase.
- **Don't duplicate superpowers.** SDD owns only the spec/document/traceability layer; planning, TDD, execution, generic verification, code review, and branch-finishing are superpowers' job. When extending the plugin, resist re-adding a `sdd-plan`/`sdd-implement`/`sdd-verify` that competes — layer the SDD discipline (citing header, DoR/DoD, traceability) onto superpowers instead. See [`references/sdd-with-superpowers.md`](references/sdd-with-superpowers.md).
- **The `docs/superpowers/` path redirect.** superpowers writes design docs to `docs/superpowers/specs/` and plans to `docs/superpowers/plans/`. These are working/narrative artefacts — the canonical homes are `docs/specifications/` (normative, via `sdd-specify`) and `docs/plans/`. `sdd-scaffold` records this override in the target repo's `AGENTS.md`; don't let a parallel `docs/superpowers/` tree become a second source of truth.
- **Public-safety is a hard gate.** Before committing any content, confirm no internal repo names, absolute paths, or org-private details leaked in (see the constraint above). The PR template includes this check.
- **Register in the marketplace separately.** Public availability requires an entry in the `cadasto` marketplace; the plugin is registered there independently of this repo.

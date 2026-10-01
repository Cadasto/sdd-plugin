# AI Guidelines: SDD Plugin

This file provides guidance to AI coding assistants (Claude Code, Cursor, and compatible tools that read `AGENTS.md`) working in this repository. It is the **canonical** instruction set; `.claude/CLAUDE.md` and any host-specific instruction files defer to it (`.claude/CLAUDE.md` imports this file via `@../AGENTS.md`).

## Project Overview

The **SDD Plugin** (`sdd`) is an AI plugin by Cadasto B.V. that brings **Spec-Driven Development** to AI coding assistants: implementation is driven from an explicit, versioned specification rather than ad-hoc prompts. It targets **both Claude Code and Cursor** from a single shared component set, and is **pure Markdown + JSON** with **no MCP backend**. The human pitch is in [README.md](README.md). Out of scope: exploration before a requirement exists ([optional plugin](#optional-a-general-engineering-plugin)) and language-specific code review (each consuming repo declares its own reviewers).

It is **general-purpose and language-agnostic** by design: the skills operate on documentation (`docs/*.md`, a requirements index, a traceability map, `AGENTS.md`), and each consuming repo declares its conventions in a small `docs/.sdd.yaml` descriptor so the same skills serve a flat-numeric library or an area-prefixed service unchanged.

## Domain Context

This plugin encodes the **spec-anchored** rung of SDD: the specification (not the code, not the prompt) is the source of truth; code is measured against it; and the governance machinery the mainstream toolkits omit (stable identifiers, a machine-checked traceability map, and CI that fails on drift) is built in.

The authoritative, public-safe statement of the methodology (the rigour ladder, the document kinds and their zones, RFC-2119 discipline, the identifier scheme, status per document kind, the traceability chain, the two source-of-truth modes, the two profiles, delivery, the two lanes, the review discipline, and the anti-patterns) lives in **[`references/sdd-methodology.md`](references/sdd-methodology.md)**. Skills cite it rather than restating it; treat it as canonical and keep the rules in one place. The machine-readable formats (`traceability.yaml` records and the `.sdd.yaml` descriptor) are in **[`references/traceability-schema.md`](references/traceability-schema.md)**.

The loop: `Specify → (Clarify) → Plan → Tasks → Implement → Verify → Close out`, under a constitution of document-kind boundaries.

## Public-safety constraint (IMPORTANT)

This repository may be published. **All content must read as general-purpose, language-agnostic SDD tooling.** Do **not**:
- name specific internal or consumer repositories,
- reproduce absolute filesystem paths or local directory layouts,
- embed organisation-private project details.

Ground claims in the public methodology lineage (GitHub Spec Kit, AWS Kiro, the Thoughtworks rigour ladder, Sean Grove's *The New Code*, RFC-2119); see the Sources section of `references/sdd-methodology.md`. This constraint applies to every skill, agent, doc, template, and reference.

## Repository Layout

Skills, agents, references and hook scripts are shared by both hosts; manifests and hook configs are per host.

- **Claude manifest**: `.claude-plugin/plugin.json`: `name` (`sdd`), `version`, `description`, `author` (an **object** `{name, url}`), `license`, `repository`, `keywords`. Claude Code discovers components from the **default folders** (`skills/`, `agents/`, `hooks/`) automatically.
- **Cursor manifest**: `.cursor-plugin/plugin.json`: same metadata **plus** explicit top-level path keys (`skills`, `agents`, `rules`, `hooks`). No `mcpServers`: this plugin has no MCP backend. Keep `name`/`version`/`description`/`author`/`license`/`repository`/`keywords` identical to the Claude manifest.
- **Skills**: `skills/<name>/SKILL.md`, shared by both hosts. The `sdd-*` skills carry `argument-hint` + `allowed-tools` so they are both auto-invoked on intent and user-invocable as `/sdd-*`; `spec-driven-development` is the always-on router.
- **Agents**: `agents/<name>.md`, context-isolated specialists. Three are report-only; `sdd-implementer` mutates within the files its brief names. Tool grants are enforced by Claude Code only; Cursor subagents inherit every tool, so there the grants hold as contracts the bodies state.
- **References**: `references/`: the canonical methodology, the schemas, the review policy (`review.md`: the findings file, severities, evidence, the forge mirror), the artefact prose-economy rule (`artefact-prose.md`), the gate's own contract (`sdd-check.md`), the cross-repo gap-draft pattern (`cross-repo-gap.md`), the `/sdd-scaffold --upgrade` procedure (`scaffold-upgrade.md`), and `references/templates/` (what `sdd-scaffold` emits; its `AGENTS.md` is a user-repo template, not this file, and the link check skips it because its links resolve only once scaffolded). Skills cite these instead of duplicating rules.
- **Tools**: `tools/sdd-check.py`, the vendorable drift gate; `/sdd-scaffold` copies it into a consuming repository at `check.script`, pins its version in `check.version`, and wires the real `spec-check` build target to it. `tools/sdd-pr.py`, the findings file's forge mirror, run from the plugin root and never vendored. `tools/tests/`: their unit tests (`unittest`, no pytest).
- **Cursor rules**: `rules/*.mdc`, Cursor-only rule guidance (`description` / `globs` / `alwaysApply`), referenced by the Cursor manifest's `rules` path. Shipped: `rules/sdd-context.mdc`.
- **Hook configs**: Claude `hooks/hooks.json`, object `{ "hooks": { "SessionStart": [...], "PostToolUse": [...], "Stop": [...] } }`, using `${CLAUDE_PLUGIN_ROOT}` in command paths; Cursor `hooks/cursor-hooks.json`, object `{ "version": 1, "hooks": { "sessionStart": [...], "afterFileEdit": [...], "stop": [...] } }`; command paths are **workspace-relative**, **not** `${CLAUDE_PLUGIN_ROOT}`. See [docs/install.md](docs/install.md#cursor) for what is still unverified there.
- **Shared hook scripts**: `hooks/session-start.sh`, `hooks/spec-edit-reminder.sh`, `hooks/session-stop.sh`. All host-agnostic; all exit 0 except the Stop hook's deliberate exit 2 on Claude Code. `scripts/hooks-test.sh` exercises them.
- **Validation**: `scripts/validate.sh` (local wrapper) runs `scripts/validate.py`, then `scripts/hooks-test.sh` even without Python. What each check covers: [docs/testing.md](docs/testing.md#validation).
- **Claude settings**: `.claude/settings.json` enables the maintainer plugins used while developing this repo (skill-creator, superpowers, plugin-dev, claude-md-management) and pre-approves the validate and gate commands. `.claude/settings.local.json` is gitignored.
- **GitHub**: `.github/` holds the issue and PR templates, `copilot-instructions.md` (defers to this file), and [`workflows/validate.yml`](.github/workflows/validate.yml) (push to `main` and every PR; Python 3.9, the tool's floor, and current 3.x).
- **Contributor docs**: `docs/`, one owner per topic; keep a one-line rule here and point to the owner: [quick-start](docs/quick-start.md) (first run in a new repo), [examples](docs/examples.md) (prompt recipes), [install](docs/install.md) (hosts, local loading, hooks), [upgrading](docs/upgrading.md) (older scaffolds), [testing](docs/testing.md) (validators, manual tests), [versioning](docs/versioning.md) (release steps, marketplace repin), [authoring](docs/authoring.md) (component conventions). `docs/plans/` and `docs/research/` are gitignored working notes, never published.

## Components

Scope is the **spec / document / traceability layer** and the **delivery pipeline that runs on it**: workers → review → triage → close-out. Exploration is the one end left open; see "Optional: a general engineering plugin" below.

### Skills (7)
| Skill | Purpose |
|-------|---------|
| `spec-driven-development` | Auto-invoked awareness/router: explains the methodology, routes intent, states where an optional general engineering plugin still fits, and blocks code-first work when no `REQ`/spec exists |
| `sdd-scaffold` | Initialise the SDD `docs/` tree, templates, `AGENTS.md`, process docs, and the `.sdd.yaml` descriptor, vendor the gate and wire the real `spec-check` target, suggesting `agents.reviewers` from the build manifests (idempotent; `--upgrade` tops up an older scaffold) |
| `sdd-specify` | The definition layer: author the `REQ` (capability + acceptance), the canonical RFC-2119 `SPEC §`, and the `ADR`; assign identifiers; wire traceability |
| `sdd-deliver` | The delivery driver: the dispatch gate by profile and lane, `sdd-implementer` fan-out per `agents:`, the per-task gate, the first review pass, the draft PR, the close-out (`--close-out`: `REQ` shipped, `generate`, the PR body), ready, panel prompts |
| `sdd-review` | One review pass over the whole branch, so a second agent or model gives a second opinion (`--since-last`: only the commits since this agent's last pass): dispatches the reviewers the profile, lane and changed file kinds call for, writes their lines into the branch's findings file with `sdd-pr add`, mirrors the blocking ones with `sdd-pr`; `--panel` prints the canonical prompt blocks |
| `sdd-triage` | Works the file's open critical and important findings: verify before fixing, fix in this branch, flip the lines, mirror, and after the maintainer's review one scoped re-review when anything changed |
| `sdd-trace` | The traceability gate: one-shot context bundle for a `REQ` + whole-tree drift/orphan report (the `spec-check` analogue); `--audit` dispatches the auditor. Report-only; whether the tests and the build pass is the build gate's job |

### Agents (4)
| Agent | Purpose |
|-------|---------|
| `sdd-traceability-auditor` | Context-isolated full-tree scan for traceability drift and orphans (the `spec-check` analogue); dispatched only by `/sdd-trace --audit` |
| `sdd-doc-reviewer` | Reviews the changed hunks of the SDD documents a change touched (**not** code) for boundary violations (two homes, disagreeing sentences, missing RFC-2119 force, unstable identifiers); consistency mode on the informative profile |
| `sdd-spec-conformance-reviewer` | Judges whether changed code satisfies the binding sentences it cites, clause by clause, running the tests and the guard-removal check as evidence (conformance, **not** code quality, drift, or test-passing) |
| `sdd-implementer` | The one mutating agent: implements a single bounded task from a brief, reads the quoted clauses, writes each test first with a can-fail proof, cites `REQ`/`PROBE` ids in test names and its commit message, verifies with the named command, and returns `En-route findings`. Denies `Agent`/`Task` (enforced on Claude Code; a stated contract on Cursor), so it cannot spawn workers; inherits every other tool, MCP servers included |

### Tools (2)
| Tool | Purpose |
|------|---------|
| `sdd-check` | The vendored drift gate (`check`, `generate`, `context`, `selftest`): checks the traceability chain in both directions, lints the prose rules that can be checked mechanically, generates every derived index from one source, prints a requirement's context bundle, and tests itself; reads the profile |
| `sdd-pr` | The findings file and its forge mirror (`status`, `scope`, `pull`, `post`, `resolve`, `add`, `flip`, `record`, `rename`): GitHub and Azure DevOps backends behind one interface; `add`, `flip`, `record`, `rename` (with `pull`, `post`, `resolve`) make every write to the file, which lives in the clone's git directory; `status` prints `Mergeable` and `Next`; `post` writes one review per pass, its summary at the head; `post`, `resolve` and `status --write-body` keep a review-state block in the PR body |

### Optional: a general engineering plugin
A general engineering plugin such as superpowers is optional: exploration workflows help before `/sdd-specify`, and everything after that is covered here. The router skill `spec-driven-development` states where the seam lies.

### Hooks
- **SessionStart** (`session-start.sh`): detects an SDD repository and prints a context line with the profile plus the `/sdd-*` surface and an orientation (plugin version on both hosts and any mismatch with the vendored gate, branch, the branch's open findings, drift-gate verdict), or a scaffold pointer in a non-SDD repo with a `docs/` dir.
- **PostToolUse** (Claude Code, `spec-edit-reminder.sh`): after an edit to a requirement/spec/ADR or the descriptor/traceability map, reminds to keep the chain in sync (`/sdd-trace` to check; the vendored `generate`, `/sdd-specify` or `/sdd-deliver --close-out` to regenerate); on the informative profile only a constitution edit prints one. It is registered on Cursor's `afterFileEdit` too, but that event has no output channel, so Cursor shows no reminder.
- **Stop** (Claude Code) / **stop** (Cursor) (`session-stop.sh`): a one-shot nudge when the session made no commit and leaves uncommitted changes in an SDD repository; the second stop in a session passes silently. Opt out per repo with `hooks.stop_nudge: false` in `docs/.sdd.yaml`. Per-host detail: [docs/install.md](docs/install.md#hooks).

## Development

### Testing & validating

No build step: pure Markdown + JSON, plus the standard-library Python gate. Validate and dogfood locally:

```bash
./scripts/validate.sh                          # validate.py (warns & skips if Python is absent), then hooks-test.sh
python3 -m unittest discover -s tools/tests -v # the gate's unit tests
python3 tools/sdd-check.py selftest            # the gate against its own fixtures
claude plugin validate .                       # manifest + component structure (no Python needed)
claude --plugin-dir /path/to/sdd-plugin        # load the working copy for one session
```

CI runs `python3 scripts/validate.py` strictly, then the unit tests, `selftest`, and `bash scripts/hooks-test.sh`. Then run the loop (`/sdd-scaffold` → `/sdd-specify` → `/sdd-deliver` → `/sdd-review` → `/sdd-triage` → `/sdd-deliver --close-out`), on both profiles, on a throwaway repo, and verify skill auto-triggering and the agents on both hosts; the checklist is in [docs/testing.md](docs/testing.md#local-triggering-tests).

### File Conventions
- Skills go in `skills/<name>/SKILL.md`; agents in `agents/<name>.md`; Cursor rules in `rules/<name>.mdc`. Detail: [docs/authoring.md](docs/authoring.md).
- Shared reference material and scaffold templates live in top-level **`references/`** (not under `commands/`). The legacy `commands/` folder is not used: slash commands are authored as user-invoked skills.
- All markdown components use YAML frontmatter; frontmatter `name` MUST equal the directory (skills) or filename stem (agents).
- `allowed-tools:` (skills; the Claude Code key, which Cursor reads too) pre-approves tools; **agents declare a grant with `tools:` (allowlist) or `disallowedTools:` (denylist)**. `allowed-tools:` in an agent file is ignored and the agent silently inherits all tools.
- Skill bodies are imperative and **cite `references/sdd-methodology.md`** rather than restating rules; every `sdd-*` skill **reads `docs/.sdd.yaml` first** instead of hard-coding paths/identifier styles.

### Documentation Sync
When adding or renaming components, update in lockstep: **AGENTS.md** (component tables), **README.md** (tables), **CHANGELOG.md**, the Cursor rule **`rules/sdd-context.mdc`** (it carries its own `/sdd-*` list), the `/sdd-*` list in **`hooks/session-start.sh`**, **`references/sdd-check.md`** when the gate's own contract changes, and **`references/review.md`** when the findings file, the severities or `sdd-pr`'s contract change. Every skill, and each agent or template on the review and delivery path, keeps within its entry in `WORD_BUDGETS` (`scripts/validate.py`). Cursor reads the same skills/agents/rules paths, so no separate Cursor-only component list is required. When a machine format changes in `references/traceability-schema.md`, update `references/templates/traceability.yaml`, `references/templates/sdd.yaml`, and every skill or agent that names a record field, in the same commit. `tools/sdd-check.py`'s and `tools/sdd-pr.py`'s `__version__` and `references/templates/sdd.yaml`'s `check.version` move together with both manifests' `version`.

### CHANGELOG style
- Entries go under `## [Unreleased]` while work is in flight and fold into the next `## [X.Y.Z] - YYYY-MM-DD` section at release.
- Keep a Changelog groups in order: **Added, Changed, Deprecated, Removed, Fixed, Security**. Omit empty groups.
- One line per bullet, leading with the subsystem (`Skills:`, `Agents:`, `References:`, `Tools:`, `Templates:`, `Hooks:`, `Docs:`) and using backticks for file/skill/key names. No rationale (that belongs in commits/PRs).

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), e.g. `feat(skills): add sdd-specify skill`, `fix(agents): correct tools list in sdd-doc-reviewer`, `chore(release): vX.Y.Z`. Scopes: `skills`, `agents`, `hooks`, `tools`, `references`, `templates`, `scripts`, `docs`.

### Versioning
Plugin version (and description, author, license, repository, and keywords) must be kept in sync in **both** `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`. Follow Semantic Versioning; update both manifests and **CHANGELOG.md** when releasing. The current version lives in the manifests and CHANGELOG, never here. Bump rules, release steps, and tagging: [docs/versioning.md](docs/versioning.md).

### Branching
Use feature branches and pull requests. CI runs on every pull request and on push to `main`.

## Gotchas

- **Rule budget.** A change that adds a step, a dispatch, a binding sentence or a file states its per-PR cost and needs the maintainer's explicit yes. Two rules that do not meet are resolved by deleting or weakening one, never by adding a third.
- **Forge-agnostic.** Skills, agents, templates and hooks never name a forge CLI; `tools/sdd-pr.py`'s backends do, and `scripts/validate.py` fails a file that does otherwise.
- **Agents declare a grant, `tools:` (allowlist) or `disallowedTools:` (denylist), never `allowed-tools:`.** In an agent file `allowed-tools:` is ignored and the agent silently inherits *all* tools. The three reviewers keep allowlists and stay report-only; `sdd-implementer` keeps its denylist (`Agent, Task`) so a consuming repo's MCP code index stays reachable; never move it to an allowlist.
- **`author` in `plugin.json` must be an object** (`{name, url}`); `claude plugin validate` rejects a bare string.
- **`${CLAUDE_PLUGIN_ROOT}` is Claude-Code-only.** Cursor hook commands stay workspace-relative (`bash hooks/session-start.sh`); don't "fix" them to use it. For locating bundled files, every skill names the plugin root as the folder that holds its `skills/` folder, which works on every host, with `${CLAUDE_PLUGIN_ROOT}` as the Claude Code shortcut. Keep both hook configs in step.
- **One canonical home for the rules: `references/sdd-methodology.md`.** Skills keep only their procedure and cite the reference. When the methodology changes, update the reference; don't re-inline rule text into each skill.
- **`spec-driven-development` is deliberately distinct from the plugin name `sdd`.** Naming the router skill `sdd` would collide (`sdd:sdd`). The skill/command prefix is `sdd-`; the router is the full phrase.
- **Don't grow a second delivery loop.** The plugin now owns plan → workers → review → triage → close-out; a general engineering plugin is optional and complementary at the exploration end only.
- **Plugin agent files are read-only at runtime.** They live in the host's install cache, so no skill can rewrite an agent's frontmatter. `sdd-implementer` ships `model: inherit` and `/sdd-deliver` passes `agents.worker_model` as a per-dispatch override.
- **An agent's `skills:` frontmatter may not name another plugin's skill.** That is unconfirmed; `worker_skills` is applied by the dispatch brief instead.
- **Public-safety is a hard gate.** Before committing any content, confirm no internal repo names, absolute paths, or org-private details leaked in (see the constraint above). The PR template includes this check.
- **Register in the marketplace separately, and repin it on every release.** Public availability requires an entry in the `cadasto` marketplace, maintained in `Cadasto/plugin-marketplace`. That entry is pinned to a release tag, so tagging here ships nothing until the entry's `version` and `source.ref` are bumped; see [docs/versioning.md](docs/versioning.md#marketplace).
- **`tools/` is shipped and vendored; `scripts/` is this repository's own validation.** Never import the tool from the validator.
- **Both tools' `__version__`, the template pin and the manifests move together.**

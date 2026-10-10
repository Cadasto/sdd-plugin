# AI Guidelines: SDD Plugin

The **canonical** instructions for AI coding assistants working in this repository (Claude Code, Cursor and any tool that reads `AGENTS.md`). `.claude/CLAUDE.md` imports this file (`@../AGENTS.md`) and `.github/copilot-instructions.md` defers to it.

## Project Overview

The **SDD Plugin** (`sdd`, by Cadasto B.V.) brings **Spec-Driven Development** to AI coding assistants: implementation is driven from an explicit, versioned specification, not ad-hoc prompts. One shared component set serves **Claude Code and Cursor**. It is Markdown and JSON plus two standard-library Python tools, with **no MCP backend**. The human pitch is in [README.md](README.md).

It encodes the **spec-anchored** rung of SDD: the specification is the source of truth, code is measured against it, and the governance the mainstream toolkits omit (stable identifiers, a machine-checked traceability map, CI that fails on drift) is built in. It is **language-agnostic**: each consuming repository declares its conventions in `docs/.sdd.yaml`, so the same skills serve a flat-numeric library or an area-prefixed service.

- **The rules** (the rigour ladder, document kinds and zones, RFC-2119, identifiers, status, traceability, the profiles, delivery, the lanes, review, anti-patterns) live in **[`references/sdd-methodology.md`](references/sdd-methodology.md)**; the machine formats (`traceability.yaml`, `.sdd.yaml`) in **[`references/traceability-schema.md`](references/traceability-schema.md)**.
- **The loop:** `Specify → (Clarify) → Plan → Tasks → Implement → Verify → Close out`, under a constitution of document-kind boundaries.
- **Out of scope:** exploration before a requirement exists (a general engineering plugin such as superpowers fits there; the router skill states the seam) and language-specific code review (each consuming repository names its own reviewers).

## Public-safety constraint (IMPORTANT)

This repository may be published. **All content must read as general-purpose, language-agnostic SDD tooling.** In every skill, agent, doc, template, reference and commit message, do **not**:
- name specific internal or consumer repositories,
- reproduce absolute filesystem paths or local directory layouts,
- embed organisation-private project details.

Ground claims in the public lineage (GitHub Spec Kit, AWS Kiro, the Thoughtworks rigour ladder, Sean Grove's *The New Code*, RFC-2119; the Sources of `references/sdd-methodology.md`). Check before every commit; the PR template carries the check.

## Repository Layout

Skills, agents, references, tools and hook scripts are shared by both hosts; manifests and hook configs are per host.

- **Manifests**: `.claude-plugin/plugin.json` (Claude Code finds `skills/`, `agents/`, `hooks/` by default) and `.cursor-plugin/plugin.json` (the same metadata plus explicit `skills`, `agents`, `rules`, `hooks` paths; no `mcpServers`).
- **Skills** `skills/<name>/SKILL.md`; **agents** `agents/<name>.md`; **Cursor rules** `rules/*.mdc` (shipped: `rules/sdd-context.mdc`).
- **References** `references/`: the methodology and schemas; `review.md` (the findings file, severities, evidence, the forge mirror, `sdd-pr`'s contract); `artefact-prose.md`; `sdd-check.md` (the gate's contract); `cross-repo-gap.md`; `scaffold-upgrade.md`; and `templates/`, what `/sdd-scaffold` emits (its `AGENTS.md` is a user-repository template, not this file; the link check skips it).
- **Tools** `tools/`: `sdd-check.py`, the drift gate `/sdd-scaffold` vendors at `check.script`, pins in `check.version` and wires to the `spec-check` target; `sdd-pr.py`, the findings file and its forge mirror, run from the plugin root and never vendored; `tests/` (`unittest`, no pytest).
- **Hooks** `hooks/`: `hooks.json` (Claude Code, `${CLAUDE_PLUGIN_ROOT}` paths), `cursor-hooks.json` (workspace-relative paths; what is unverified there: [docs/install.md](docs/install.md#cursor)), and the shared scripts `session-start.sh`, `spec-edit-reminder.sh`, `session-stop.sh`, which exit 0 except the Stop hook's deliberate exit 2 on Claude Code.
- **Validation** `scripts/`: `validate.sh` runs `validate.py`, then `hooks-test.sh` even without Python; what each check covers: [docs/testing.md](docs/testing.md#validation). CI: [`.github/workflows/validate.yml`](.github/workflows/validate.yml), on push to `main` and every PR, Python 3.9 (the tools' floor) and current 3.x.
- **Claude settings**: `.claude/settings.json` enables the maintainer plugins (skill-creator, superpowers, plugin-dev, claude-md-management) and pre-approves the validate and gate commands; `.claude/settings.local.json` is gitignored.
- **Contributor docs** `docs/`, one owner per topic: [quick-start](docs/quick-start.md), [examples](docs/examples.md), [install](docs/install.md) (hosts, local loading, hooks, permission prompts), [upgrading](docs/upgrading.md), [testing](docs/testing.md), [versioning](docs/versioning.md) (release steps, marketplace repin), [authoring](docs/authoring.md) (component conventions). Keep a one-line rule here and point to the owner. `docs/plans/` and `docs/research/` are gitignored working notes.

## Components

The **spec, document and traceability layer** and the **delivery pipeline on it**: workers → review → triage → close-out.

### Skills (7)
| Skill | Purpose |
|-------|---------|
| `spec-driven-development` | The always-on router: explains the methodology, routes intent, names where a general engineering plugin fits, blocks code-first work when no `REQ` or spec exists |
| `sdd-scaffold` | Initialises the `docs/` tree, templates, `AGENTS.md`, process docs and descriptor; vendors the gate and wires `spec-check`; suggests `agents.reviewers` from the build manifests; idempotent, `--upgrade` tops up an older scaffold |
| `sdd-specify` | Authors the `REQ` (capability and acceptance), the RFC-2119 `SPEC §` and the `ADR`; assigns identifiers; wires traceability |
| `sdd-deliver` | Drives delivery: the dispatch gate by profile and lane, `sdd-implementer` workers (in sequence; a parallel wave only for large tasks with disjoint files, on the one branch), the per-task gate, the first review pass, the draft PR, `--close-out` (`REQ` shipped, `generate`, the PR body), ready |
| `sdd-review` | One review pass over the whole branch (`--since-last`: only this agent's new commits) with the reviewers the profile, lane and changed files call for, into the findings file; mirrors the blocking ones; `--panel` prints the prompt blocks |
| `sdd-triage` | Works the open critical and important findings: verify, fix in this branch, flip, mirror, and one re-review after the maintainer's review when anything changed; `--backlog` carries the suggestions of pull requests merged since the backlog's watermark to `docs/backlog.md` |
| `sdd-trace` | A `REQ`'s context bundle and the whole-tree drift report; `--audit` dispatches the auditor. Report-only |

### Agents (4)
| Agent | Purpose |
|-------|---------|
| `sdd-traceability-auditor` | Full-tree scan for traceability drift and orphans in isolated context; dispatched only by `/sdd-trace --audit` |
| `sdd-doc-reviewer` | Reviews the changed hunks of SDD documents (**not** code) for boundary violations; consistency mode on the informative profile |
| `sdd-spec-conformance-reviewer` | Judges changed code against the binding sentences it cites, clause by clause, with the tests and the guard-removal check as evidence |
| `sdd-implementer` | The one mutating agent: one bounded task from a brief, test first with a can-fail proof, ids in test names and the commit, `En-route findings` back; cannot spawn agents |

### Tools (2)
| Tool | Purpose |
|------|---------|
| `sdd-check` | The vendored drift gate (`check`, `generate`, `context`, `selftest`): the chain in both directions, the mechanical prose lints, every derived index from one source; reads the profile |
| `sdd-pr` | The findings file in the clone's git directory and its GitHub or Azure DevOps mirror: `add`, `flip`, `record`, `rename` (and `pull`, `post`, `resolve`) make every write; `status` prints `Mergeable` and `Next`; `scope` the range a pass reads; `post` one review per pass, its summary on top, and the new suggestions in a comment of their own; `harvest` merged pull requests' suggestions and `flip --carry` leftovers to `docs/backlog.md`; `guard` one guard-removal proof in a scratch worktree; never the PR body |

### Hooks
- **SessionStart** (`session-start.sh`): in an SDD repository, the profile, the `/sdd-*` surface and an orientation (plugin version and any mismatch with the vendored gate, branch, open findings, the gate's verdict); elsewhere, a scaffold pointer when `docs/` exists.
- **PostToolUse** (Claude Code, `spec-edit-reminder.sh`): after an edit to a requirement, spec, ADR, the descriptor or the map, a reminder to keep the chain in sync; on the informative profile only for a constitution edit. Registered on Cursor's `afterFileEdit` too, which has no output channel.
- **Stop** (`session-stop.sh`): one nudge when the session made no commit and leaves uncommitted changes; opt out with `hooks.stop_nudge: false`. Per host: [docs/install.md](docs/install.md#hooks).

## Development

### Testing & validating

No build step. Validate and dogfood locally:

```bash
./scripts/validate.sh                          # validate.py (warns & skips if Python is absent), then hooks-test.sh
python3 -m unittest discover -s tools/tests -v # both tools' unit tests
python3 tools/sdd-check.py selftest            # the gate against its own fixtures
claude plugin validate .                       # manifest + component structure (no Python needed)
claude --plugin-dir /path/to/sdd-plugin        # load the working copy for one session
```

CI runs `python3 scripts/validate.py` strictly, then the unit tests, `selftest` and `bash scripts/hooks-test.sh`. Then run the loop (`/sdd-scaffold` → `/sdd-specify` → `/sdd-deliver` → `/sdd-review` → `/sdd-triage` → `/sdd-deliver --close-out`) on both profiles in a throwaway repository, on both hosts: [docs/testing.md](docs/testing.md#local-triggering-tests). To check that a test guards a fix by mutating `tools/*.py` in place, run with `PYTHONDONTWRITEBYTECODE=1 python3 -B`: a cached `.pyc` can otherwise run instead of the mutant.

### File Conventions
- Frontmatter on every Markdown component; its `name` MUST equal the directory (skills) or the filename stem (agents). No `commands/` folder: slash commands are user-invoked skills. Detail: [docs/authoring.md](docs/authoring.md).
- The `sdd-*` skills carry `argument-hint` and `allowed-tools`, so they trigger on intent and run as `/sdd-*`. Their bodies are imperative, **read `docs/.sdd.yaml` first**, and cite `references/` instead of restating a rule.

### Documentation Sync
When adding or renaming a component, update in lockstep: **AGENTS.md** and **README.md** (the tables), **CHANGELOG.md**, the `/sdd-*` lists in **`rules/sdd-context.mdc`** and **`hooks/session-start.sh`**, **`references/sdd-check.md`** when the gate's contract changes, and **`references/review.md`** when the findings file, the severities or `sdd-pr`'s contract change. When a machine format changes in `references/traceability-schema.md`, update `references/templates/traceability.yaml`, `references/templates/sdd.yaml` and every skill or agent naming the field, in the same commit. Every skill, and each agent or template on the review and delivery path, keeps within its `WORD_BUDGETS` entry in `scripts/validate.py`; raising one needs the maintainer's yes.

### CHANGELOG style
- Entries go under `## [Unreleased]` while work is in flight and fold into the next `## [X.Y.Z] - YYYY-MM-DD` section at release.
- Keep a Changelog groups in order: **Added, Changed, Deprecated, Removed, Fixed, Security**. Omit empty groups.
- One line per bullet, leading with the subsystem (`Skills:`, `Agents:`, `References:`, `Tools:`, `Templates:`, `Hooks:`, `Docs:`), with backticks for file, skill and key names. No rationale (that belongs in commits and PRs).

### Commit Messages
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), e.g. `feat(skills): add sdd-specify skill`, `fix(agents): correct tools list in sdd-doc-reviewer`, `chore(release): vX.Y.Z`. Scopes: `skills`, `agents`, `hooks`, `tools`, `references`, `templates`, `scripts`, `docs`.

### Versioning
Semantic Versioning. These move together, and `scripts/validate.py` fails when they disagree: `version` in both manifests, the `__version__` of `tools/sdd-check.py` and `tools/sdd-pr.py`, and `check.version` in `references/templates/sdd.yaml`. Both manifests also keep `description`, `author`, `license`, `repository` and `keywords` identical. The current version lives in the manifests and CHANGELOG, never here. Bump rules and release steps: [docs/versioning.md](docs/versioning.md).

### Branching
Feature branches and pull requests. CI runs on every pull request and on push to `main`.

## Gotchas

- **Rule budget.** A change that adds a step, a dispatch, a binding sentence or a file states its per-PR cost and needs the maintainer's explicit yes. Two rules that do not meet are resolved by deleting or weakening one, never by adding a third.
- **One home per rule.** The methodology is `references/sdd-methodology.md`; review is `references/review.md`. Change the reference, never re-inline its text into a skill.
- **Forge-agnostic.** Skills, agents, templates and hooks never name a forge CLI; only `tools/sdd-pr.py`'s backends do, and `scripts/validate.py` fails any other file that does.
- **Agents declare a grant with `tools:` (allowlist) or `disallowedTools:` (denylist), never `allowed-tools:`,** which an agent file ignores, so the agent silently inherits *all* tools. The three reviewers keep allowlists and stay report-only; `sdd-implementer` keeps its denylist (`Agent, Task`) so a consuming repository's MCP code index stays reachable; never move it to an allowlist. Claude Code enforces grants; Cursor subagents inherit every tool, so there the grants are contracts the bodies state.
- **A plugin cannot approve a command.** Claude Code ignores `permissionMode`, `hooks` and `mcpServers` in plugin agents, keeps only `agent` and `subagentStatusLine` from plugin settings, and runs a subagent under the session's permission rules. Users add allow rules themselves: [docs/install.md](docs/install.md).
- **`author` in `plugin.json` is an object** (`{name, url}`); `claude plugin validate` rejects a bare string.
- **`${CLAUDE_PLUGIN_ROOT}` is Claude-Code-only.** Cursor hook commands stay workspace-relative (`bash hooks/session-start.sh`); don't "fix" them, and keep both hook configs in step. Every skill names the plugin root as the folder that holds its `skills/` folder, which works on both hosts.
- **Plugin agent files are read-only at runtime** (they live in the install cache). `sdd-implementer` ships `model: inherit`; `/sdd-deliver` passes `agents.worker_model`, and the skills pick other models, per dispatch.
- **An agent's `skills:` frontmatter may not name another plugin's skill** (unconfirmed); `worker_skills` goes through the dispatch brief instead.
- **`spec-driven-development` is not named `sdd`,** which would collide as `sdd:sdd`. The command prefix is `sdd-`.
- **Don't grow a second delivery loop.** The plugin owns plan → workers → review → triage → close-out; a general engineering plugin complements it at the exploration end only.
- **`tools/` is shipped and vendored; `scripts/` is this repository's own validation.** Never import a tool from the validator.
- **Release here, then repin the marketplace.** The entry in `Cadasto/plugin-marketplace` is pinned to a tag, so a release ships nothing until its `version` and `source.ref` move: [docs/versioning.md](docs/versioning.md#marketplace).

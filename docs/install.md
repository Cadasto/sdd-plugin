# Installing the SDD Plugin

> This plugin is pure Markdown + JSON — there is no build step and **no MCP server** to wire up.

Distributed for both [Claude Code](https://docs.claude.com/en/docs/claude-code/plugins) (`.claude-plugin/`) and [Cursor](https://cursor.com/docs/plugins) (`.cursor-plugin/`). Skill, agent, and rule content is shared; only the manifest and hook layer differ.

## Claude Code

### Install (from the Cadasto marketplace)

```
/plugin marketplace add Cadasto/plugin-marketplace
/plugin install sdd@cadasto
```

The marketplace name is `cadasto`, so the plugin is addressed as `sdd@cadasto`.

### Load a local working copy (for development)

```bash
claude --plugin-dir /path/to/sdd-plugin
```

`--plugin-dir` loads the plugin from disk for **that session only** — it does not persist, which makes it the right tool for dogfooding an unreleased working copy. It is repeatable (`--plugin-dir A --plugin-dir B`) and also accepts a `.zip`.

Claude Code has **no `plugin add` subcommand**. `claude plugin install` resolves names from a configured marketplace, not filesystem paths, and `claude plugin marketplace add <path>` expects a marketplace manifest (`.claude-plugin/marketplace.json`) — which a single-plugin repository like this one does not have. For a persistent install, go through the marketplace above.

### Inspect / update

```bash
claude plugin validate .            # manifest + component structure
claude plugin details sdd           # component inventory + projected token cost
```

```
/plugin marketplace update cadasto
/plugin update sdd
```

A session restart is required for an update to take effect.

## Cursor

Add this repository as a plugin (Cursor **Settings → Plugins**, via Git URL or local path). The repo root contains `.cursor-plugin/plugin.json`, which declares the `skills`, `agents`, `rules`, and `hooks` paths. After changing content locally, reload or reinstall the plugin so Cursor picks it up.

> Cursor subagents inherit every tool. The `tools:` and `disallowedTools:` grants in `agents/*.md` are Claude Code fields, so on Cursor the reviewers' no-edit rule and the implementer's no-spawn rule hold as contracts stated in the agent bodies. Cursor's `subagentStart` hook can deny a spawn and is the enforceable path; this plugin does not ship it.

> The Cursor hook wiring targets the `sessionStart` and `afterFileEdit` events; if your Cursor version exposes a different post-edit event or payload shape, adjust `hooks/cursor-hooks.json` and the path-extraction in `hooks/spec-edit-reminder.sh` accordingly.

## Host repository requirements

Installing the plugin needs nothing. To get full value, the **repository you apply SDD to** should expose a single build entry point (`make` / `task` / `just` / `npm`) with a `spec-check` target and a full `ci` target — `/sdd-trace` and the delivery gates invoke these. `/sdd-scaffold` can stub them for you and records the target names in `docs/.sdd.yaml`.

The `spec-check` target runs the vendored gate: `/sdd-scaffold` copies `tools/sdd-check.py` into the repository and wires `spec-check` to run `python3 <check.script> check`, so CI needs no plugin. The gate's contract — the families it checks and what each means — is [references/sdd-check.md](../references/sdd-check.md); a repository may keep its own additional checks beside it.

## Hooks

Three host-agnostic hooks ship (Claude `hooks/hooks.json`, Cursor `hooks/cursor-hooks.json`):

- **`session-start.sh`** — on session start, detects an SDD repo (`docs/.sdd.yaml`, `docs/specifications/`, or a traceability map) and prints one context line plus the `/sdd-*` surface, then a short orientation (branch and tree state, active plans, open pull requests, the drift-gate verdict). On Cursor it emits an `additional_context` JSON object; on Claude Code, plain text.
- **`spec-edit-reminder.sh`** — after an edit to a requirement, spec, ADR, plan, or the descriptor/traceability map (Claude `PostToolUse` on `Write`/`Edit`; Cursor `afterFileEdit`, which has no output channel, so the reminder is observational there), prints a short reminder to keep the chain in sync. It is advisory, never blocks an edit, and always exits 0.
- **`session-stop.sh`** — a one-shot nudge when a session ends with no commit and uncommitted changes still in the tree (Claude `Stop`, Cursor `stop`). Opt out per repository with `hooks.stop_nudge: false` in `docs/.sdd.yaml`.

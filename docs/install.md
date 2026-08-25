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

> The Cursor hook wiring targets the `sessionStart` and `afterFileEdit` events; if your Cursor version exposes a different post-edit event or payload shape, adjust `hooks/cursor-hooks.json` and the path-extraction in `hooks/spec-edit-reminder.sh` accordingly.

## Host repository requirements

Installing the plugin needs nothing. To get full value, the **repository you apply SDD to** should expose a single build entry point (`make` / `task` / `just` / `npm`) with a `spec-check` target and a full `ci` target — `/sdd-trace` (and superpowers' `verification-before-completion`) invoke these. `/sdd-scaffold` can stub them for you and records the target names in `docs/.sdd.yaml`.

The `spec-check` target itself is repo-specific (it validates the traceability map against the tree). The plugin defines *what* it must check (see [references/traceability-schema.md](../references/traceability-schema.md)); the host repo implements it in whatever language/tooling it uses.

## Hooks

Two host-agnostic hooks ship (Claude `hooks/hooks.json`, Cursor `hooks/cursor-hooks.json`):

- **`session-start.sh`** — on session start, detects an SDD repo (`docs/.sdd.yaml`, `docs/specifications/`, or a traceability map) and prints one context line plus the `/sdd-*` surface.
- **`spec-edit-reminder.sh`** — after an edit to a requirement, spec, ADR, plan, or the descriptor/traceability map (Claude `PostToolUse` on `Write`/`Edit`; Cursor `afterFileEdit`), prints a short reminder to keep the chain in sync and run `/sdd-trace`. It is advisory, never blocks an edit, and always exits 0.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- Semantic Versioning: https://semver.org/spec/v2.0.0.html

## [0.1.0] - 2026-06-18

First build — a dual-host (Claude Code + Cursor) Spec-Driven Development surface. Pure Markdown + JSON, language-agnostic and config-driven via a `docs/.sdd.yaml` descriptor; no MCP backend.

### Added
- Dual-host manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`) with parity-enforced metadata; plugin `name` is `sdd`.
- Skills: `spec-driven-development` — auto-invoked awareness/router; recognises SDD vocabulary, explains the methodology, routes intent to the worker skills, and blocks code-first work when no `REQ`/spec exists. Only its `description` is always-on.
- Skills: the SDD loop/lifecycle set — `sdd-scaffold`, `sdd-requirement`, `sdd-spec`, `sdd-adr`, `sdd-plan`, `sdd-implement`, `sdd-verify`, `sdd-trace`, `sdd-archive`, `sdd-gap`. Each is auto-invoked on intent and user-invocable as `/sdd-*`; all read the `docs/.sdd.yaml` descriptor and operate on Markdown, not source code.
- Agents: `sdd-traceability-auditor` (read-only full-tree drift/orphan scan — the `spec-check` analogue) and `sdd-doc-reviewer` (read-only review of a requirement/spec/ADR/plan for boundary violations). Both declare `tools:` (read-only), never `allowed-tools:`.
- Hooks: host-agnostic `hooks/session-start.sh` (detects an SDD repo, prints context + the `/sdd-*` surface, exits 0) and `hooks/spec-edit-reminder.sh` (after an edit to a requirement/spec/ADR/plan or the traceability map, reminds to sync traceability and run `/sdd-trace`). Wired via `hooks/hooks.json` (Claude, `${CLAUDE_PLUGIN_ROOT}`) and `hooks/cursor-hooks.json` (Cursor, workspace-relative).
- References: `references/sdd-methodology.md` (the universal methodology — document kinds, RFC-2119 discipline, identifiers, traceability chain, two source-of-truth modes, DoR/DoD, anti-patterns), `references/traceability-schema.md` (the `traceability.yaml` record format + the `.sdd.yaml` descriptor schema), and `references/templates/` (the document templates `sdd-scaffold` emits).
- Cursor rule: `rules/sdd-context.mdc` mirroring the `spec-driven-development` router; declared via the Cursor manifest's `rules` path.
- Validation harness: `scripts/validate.py` (manifests, dual-host parity, declared component paths, kebab-case names, hook-config JSON, and skill/agent frontmatter — agents must use `tools:` not `allowed-tools:`) and the `scripts/validate.sh` soft-skip wrapper.
- CI: `.github/workflows/validate.yml` (pins Python, strict in CI).
- Community files under `.github/` (issue templates, PR template, Copilot instructions).
- Docs: `docs/install.md`, `docs/testing.md`, `docs/versioning.md`, `docs/authoring.md`.

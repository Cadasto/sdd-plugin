# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- Semantic Versioning: https://semver.org/spec/v2.0.0.html

## [0.3.0] - 2026-07-11

### Added
- Skills: `sdd-review` — opt-in orchestration that dispatches the installed generic reviewers plus `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer`, consolidates the findings, and optionally posts them to the PR (delegates generic review + posting; adds the SDD lenses).
- Agents: `sdd-spec-conformance-reviewer` — read-only, judges whether implemented code satisfies the normative `SPEC §` / `REQ` acceptance criteria it cites, clause by clause.
- References: `references/artefact-prose.md` — the artefact prose-economy rule (one home per fact for commit body / PR body / changelog / review comments; cite identifiers, don't restate).

### Changed
- Skills: `sdd-archive` now archives **inside the implementing PR** (as the final commit of the branch, `implementation: shipped` set there) rather than in a follow-up PR; methodology §9 Definition of Done and the scaffold templates (`development-process.md`, `ai-workflow.md`, `AGENTS.md`) updated to match.
- References: the prose-economy rule is cross-linked from `sdd-methodology.md` §11, the `spec-driven-development` router, `sdd-with-superpowers.md`, and the Cursor rule; scaffolded repos inherit the short form via the templates.
- Agents: modernized `sdd-doc-reviewer` and `sdd-traceability-auditor` descriptions to the prose-summary format (conditions + named trigger scenarios + a "See When to invoke" pointer), replacing the embedded `<example>` block; folded the worked scenario into each agent's `When to invoke` body as prose bullets. `docs/authoring.md` updated to prescribe this form.

## [0.2.1] - 2026-06-18

### Fixed
- Skills: the bundled `references/` lives at the plugin root, but the five skills cited it as a bare `references/…` that a reader resolves relative to the *skill* directory — so the first Read failed on every load (and risked the agent improvising rules rather than grounding in the methodology). Each skill now carries a one-line note that `references/` is plugin-root-relative, with host-agnostic resolution (`${CLAUDE_PLUGIN_ROOT}/references/…`, `../../references/…`, or Glob). `sdd-doc-reviewer` clarified likewise and made self-contained. No change to the single-copy (DRY) design.

## [0.2.0] - 2026-06-18

Consolidated the skill surface and aligned the plugin to **complement the superpowers plugin** — SDD owns the spec / document / traceability layer; the engineering loop (planning, TDD, execution, generic verification, code review, branch-finishing) is deferred to superpowers.

### Changed
- Skills: consolidated **11 → 5**. Merged `sdd-requirement` + `sdd-spec` + `sdd-adr` into `sdd-specify` (the definition layer); refocused `sdd-trace` to own the traceability/drift gate; refocused `sdd-archive` to own the document-side Definition of Done; rewrote `spec-driven-development` as the SDD↔superpowers integration map. Cuts always-on description cost ~33% (~2,385 → ~1,600 tokens) and the `/sdd-*` command surface from 10 to 4.
- Skills / agents / rules / hooks: cross-host hardening — `sdd-scaffold` resolves bundled templates host-agnostically (`${CLAUDE_PLUGIN_ROOT}` with a Glob fallback for Cursor/other installs); `cursor-hooks.json` adds `"version": 1`; thinned `sdd-context.mdc` and the `spec-driven-development` routing table; deduplicated superpowers handoffs in worker skills (one-liners + `references/sdd-with-superpowers.md`).
- Agents: trimmed `sdd-traceability-auditor` and `sdd-doc-reviewer` descriptions to ~1 example (≤~1,000 chars) and moved triggering detail into a `When to invoke` body section; scoped `sdd-doc-reviewer` explicitly to SDD documents (code review is superpowers' `requesting-code-review`).
- Hooks / Cursor rule / docs / scaffold templates: updated `session-start.sh`, `spec-edit-reminder.sh`, `rules/sdd-context.mdc`, `references/templates/*`, and the contributor docs to the new surface and the superpowers handoffs.

### Added
- References: `references/sdd-with-superpowers.md` — the SDD↔superpowers boundary and the `docs/superpowers/*` → canonical-tree (`docs/specifications/`, `docs/plans/`) path redirect.
- References: `references/cross-repo-gap.md` — the cross-repo gap-draft pattern (demoted from the former `sdd-gap` skill).

### Removed
- Skills: `sdd-requirement`, `sdd-spec`, `sdd-adr` (→ `sdd-specify`); `sdd-plan`, `sdd-implement` (→ superpowers' planning / execution / TDD); `sdd-verify` (→ `sdd-trace` + `sdd-archive` + superpowers' `verification-before-completion`); `sdd-gap` (→ `references/cross-repo-gap.md`).

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

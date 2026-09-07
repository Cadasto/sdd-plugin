# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- Semantic Versioning: https://semver.org/spec/v2.0.0.html

## [0.5.0] - 2026-09-04

The methodology sheds the plan lifecycle and the plugin takes over the delivery pipeline: a plan is a
working file that is flipped to `done` where it lies and swept at the next release, delivery and triage
become skills, and findings live in one ledger per change.

### Added
- Skills: `sdd-deliver` — the delivery driver: dispatch preconditions, the plan on the branch, `sdd-implementer` fan-out per `agents:`, the per-task gate by lane, round 0 of the ledger, the draft PR, close-out, ready, panel prompts.
- Skills: `sdd-triage` — one review round: every comment channel enumerated, findings merged into the ledger, verified before fixing, the pattern class swept, fixed in the PR, re-review prompts printed.
- Skills: `sdd-finalize` — the release sweep: deletes `done` and `abandoned` plans as the first step of a version bump, after an inbound-link check; the first run also removes a legacy `docs/plans/archive/`.
- Agents: `sdd-implementer` — implements one bounded task from a brief, cites `REQ`/`PROBE` ids, verifies with the named command, and returns `En-route findings`. Denies `Agent` and `Task` through `disallowedTools:` and inherits every other tool the host offers, MCP servers included, so a repository's code index is reachable; it cannot spawn workers.
- References: `sdd-methodology.md` §12 two lanes with the ratchet guard, §13 review discipline (two gates, the ledger as the default, the materiality threshold, collapse-before-add, the reviewer memory path), §14 the keep-list.
- References: `artefact-prose.md` — the findings ledger, the `Deferred` table, completion accounting, and the prose register.
- References: `traceability-schema.md` — the `agents:` and `review_panel` descriptor block and the plan frontmatter contract; `templates/sdd.yaml` carries the matching `agents:` block.

### Changed
- References: `sdd-methodology.md` §9 is now a working-plan lifecycle — `active | done | postponed | abandoned`, five dispatch preconditions, close-out on four surfaces, archive in place, sweep at the release.
- References: `sdd-methodology.md` §5 states lazy identifier allocation as the default; §10 adds the cross-repo disagreement rule; §11 adds the memoir rule.
- References: `artefact-prose.md` states the changelog-bullet rule and the single-canonical-home rule, both as reviewer rules with no tool behind them yet.
- Skills: `sdd-archive` is reduced to the frontmatter flip, the status updates, and the PR body — no `git mv`, no index.
- Skills: `sdd-review` detects the lane, dispatches per lane, writes one ledger instead of one comment per finding, and prints one canonical prompt block per `review_panel` entry with `--panel`.
- Skills: `sdd-scaffold` no longer creates `docs/plans/archive/` or a plans index, and fills the `agents:` block of the descriptor, suggesting `agents.reviewers` and `agents.worker_skills` from the build manifests in the tree (`go.mod`, `composer.json`, `package.json`) for the maintainer to confirm.
- Skills: `sdd-specify` hands off to `/sdd-deliver` and no longer routes design notes through another plugin.
- Skills: `sdd-trace` reports a plan/`REQ` status mismatch from the plan's frontmatter rather than from a plans index.
- Skills: `spec-driven-development` routes the new surface and states in one paragraph that a general engineering plugin is optional.
- Agents: the three reviewers gain the materiality threshold, the settled-adjudications memory, and the cross-repo rule.
- Agents: the three reviewers route code review to the repository's own declared reviewers and test-passing to the build gate.
- Templates: `plan.md` carries a minimal header; `ai-workflow.md` gains the standing orchestration section with its code-index line, the canonical review-request block, and the ledger rules; `AGENTS.md` mirrors the orchestration rules; `development-process.md` replaces the DoR/DoD blocks with dispatch preconditions, the lanes, and the PR-body close-out with its `Lane:` line.
- Templates: `ci.md` names the build gate directly, and its scheduled drift-bot row fails the run and reports the drift instead of opening a tracking issue.
- Hooks: `session-start.sh` lists the full `/sdd-*` surface and the new plan rule.
- Scripts: `validate.py` requires every agent to declare a grant — `tools:` or `disallowedTools:` — and still rejects `allowed-tools:`.
- Docs: `AGENTS.md`, `README.md`, `docs/authoring.md`, `docs/install.md`, `docs/testing.md`, and `rules/sdd-context.mdc` follow the new surface; the PR template gains the disclosure grep and `.gitignore` excludes the plan workspace.

### Removed
- References: `sdd-with-superpowers.md` and the `docs/superpowers/` path redirect. A general engineering plugin is optional and described in one paragraph in the router.
- References: the `plans:` axis of a traceability record and `paths.plans_archive` from the descriptor and its template.
- Agents: `sdd-doc-reviewer` no longer reviews plan headers; `sdd-traceability-auditor` no longer reports plan drift classes.

## [0.4.1] - 2026-08-25

Corrects three component defects and the claims the docs made about them: a `PostToolUse` hook timeout that was five hours rather than twenty seconds, an always-on router that inherited every tool, and two agents that described themselves as read-only while holding `Bash`.

### Changed
- Docs: `README.md` — the agents table was headed **read-only**, which holds for one of the three. `sdd-doc-reviewer` declares only `Read`/`Grep`/`Glob` and is read-only outright; `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` add `Bash`, which writes. The heading is now **report-only**, with a line saying which guarantee is enforced and which is a contract the agent keeps. `/sdd-trace` is relabelled the same way — it declares `Bash` too.
- Docs: `docs/authoring.md` — the authoring rule now depends on the grant rather than habit: call an agent read-only only when its `tools:` genuinely are, and describe one holding `Bash` as report-only. `docs/testing.md` follows for `/sdd-trace`.
- Docs: sentence-case H1s in `docs/testing.md`, `docs/versioning.md`, `docs/authoring.md`; "for example" over "e.g."; `docs/testing.md` opens with its subject rather than "There is"; the superpowers seam paragraph no longer opens with "So".
- Docs: `docs/versioning.md`, `AGENTS.md` — the marketplace no longer tracks this repo's default branch. The Cadasto catalog pins each entry to a release tag, so a release is not live until the entry in `Cadasto/plugin-marketplace` bumps `version` and `source.ref`; added as release step 8.

### Fixed
- Hooks: the `PostToolUse` reminder declared `"timeout": 20000`. Claude Code reads a hook timeout in **seconds** (`hook.timeout * 1000` internally), so that was 5 hours 33 minutes, not 20 seconds — a hung script would have stalled the session rather than being cut off. Now `20`.
- Skills: `spec-driven-development` declared no `allowed-tools`, so the always-on router inherited **every** tool including `Write`, `Edit`, and `Bash`. It explains and routes — it reads the references and `docs/.sdd.yaml` and does no artefact work — so it now declares `Read, Grep, Glob`.
- Agents: `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` described themselves as **read-only** while declaring `Bash`, which writes. Both are **report-only**, and each body now says no-edit is a contract it keeps rather than a sandbox that keeps it. `sdd-doc-reviewer` is unchanged: it declares only `Read`/`Grep`/`Glob`, so read-only is accurate there.

- Docs: `claude plugin add` is not a Claude Code command. `README.md`, `docs/install.md`, `docs/versioning.md` (the dogfood release step), and `AGENTS.md` load a local working copy with `claude --plugin-dir <path>`, which applies to that session only.

## [0.4.0] - 2026-08-05

### Changed
- References: `sdd-methodology.md` defines the **negative space** discipline — §3: acceptance criteria cover what the capability must refuse or fail closed on, with the intended failure behaviour; §9 DoR names it (cited from the `REQ`/`SPEC §`, not restated) and §9 DoD exercises it (refusal paths tested, new runtime failure modes mapped to the error contract — the RFC-2119 `SPEC §` owning failure behaviour); §4: fail-closed clauses carry the same force as positive ones; §11: happy-path-only acceptance is an anti-pattern. Templates `requirement.md`, `plan.md`, and `development-process.md` mirror.
- Skills: `sdd-specify` authors the negative space at the right altitude — §A the `REQ` names and cites it as an observable outcome, §B the spec owns the normative *how* (`MUST NOT`/fail-closed/error contract); `sdd-archive` blocks the archive on unmet plan-DoD boxes (negative space exercised included).
- Skills: `sdd-review` lands best before the PR is opened (findings fold into the slice instead of becoming post-publication review rounds); the generic reviewer runs report-only until the post step, and scoping no longer assumes an open PR.
- Agents: `sdd-doc-reviewer` flags happy-path-only acceptance criteria, a DoR with no named negative space, and a `done` plan with unchecked DoD boxes; `sdd-spec-conformance-reviewer` enumerates negative-space criteria as first-class clauses (an untested refusal path is a finding).
- Agents: system prompts now open in second person ("You are…") per agent-authoring guidance; `docs/authoring.md` records the convention.
- Skills, agents: trimmed the always-on frontmatter `description`s (~6% less always-loaded context) and the per-skill `references/` resolution note (~40%); every quoted trigger phrase, disambiguation target, and resolution path kept. `sdd-scaffold` wording made imperative per the skill-authoring style.

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

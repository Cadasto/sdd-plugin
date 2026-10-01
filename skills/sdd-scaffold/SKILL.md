---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", "add SDD structure to this repo", "upgrade the SDD scaffold", or "re-vendor sdd-check". Creates the docs/ tree, the .sdd.yaml descriptor, AGENTS.md, the process docs and the vendored gate, idempotently, on the formal or informative profile; --upgrade tops up an older scaffold. Not for authoring documents (sdd-specify) or a drift scan (sdd-trace).
argument-hint: "[profile: formal|informative] [req-style: area-prefixed|flat-numeric] [build tool: make|task|just|npm] [--upgrade]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Scaffold an SDD repository

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` and `tools/…` resolve from it.

Lay down the `docs/` tree, the descriptor, the governed `AGENTS.md`, the process docs and the gate. **Idempotent:** fill gaps; never overwrite a file that has content.

## Steps

0. **Resolve the plugin root.** Templates live at `<plugin-root>/references/templates/` and the gate at `<plugin-root>/tools/sdd-check.py`, never in the consumer repo.
1. **Detect, then route** — the first match wins. Glob for `docs/.sdd.yaml`, `docs/requirements/`, `docs/specifications/`, `AGENTS.md`, and Grep the descriptor for `^\s*check:`.
   - **No descriptor** → a fresh run of steps 2–6, even with `--upgrade` (say so: there is nothing to top up).
   - **`--upgrade` given** → **`--upgrade`** below instead of steps 2–6.
   - **A descriptor with no `check:` block** → it predates the gate: run **`--upgrade`** as if the flag were given, and open the report with `no check: block in docs/.sdd.yaml — ran --upgrade`.
   - **A descriptor with a `check:` block** → a top-up of steps 2–6: create only what is missing and report what was skipped.
2. **Establish conventions** in `docs/.sdd.yaml`:
   - `profile` — ask first (`AskUserQuestion` where available), one sentence each from `references/sdd-methodology.md` §1a: **formal** — requirements, RFC-2119 specifications, ADRs, the traceability map and the whole drift gate; **informative** — `docs/` is a knowledge base, code leads, and one constitution document binds. On informative, ask only `build_entrypoint`, `ci_target`, `spec_check_target` and `ground_truth` below.
   - `forge` — leave `auto` (from the remote URL) unless the maintainer names `github`, `azure-devops` or `none`.
   - `req_style` — `area-prefixed` (`REQ-AUTH-001`, a capability map; recommend for products) or `flat-numeric` (`REQ-050`; recommend for libraries). Ask if unspecified.
   - Ask for `req_areas` and `excluded_areas` (area-prefixed only: which tokens are deliberately not areas), `build_entrypoint`, `ci_target`, `spec_check_target`, `use_probes`, `use_strands`, `upstream`, and `ground_truth` (the "look it up, don't guess" source for domain facts).
   - `doc_kinds`, `default_mode` and the `check:`/`hooks:` blocks are copied from the template as they are.

   A descriptor with no `agents:` block gains that block from the template, and no other key changes.
3. **Create the missing tree:**
   ```
   CHANGELOG.md
   docs/
     .sdd.yaml
     development-process.md   ai-workflow.md   ci.md
     requirements/   (README.md)
     specifications/ (README.md, traceability.yaml)
     adr/            (README.md)
   ```
   From the templates directory: `sdd.yaml` → `docs/.sdd.yaml`; `requirement.md`, `specification.md` and `adr.md` → a `_template.md` in each kind's folder; the starter `traceability.yaml`; the three index READMEs (`requirements-README.md`, `specifications-README.md`, `adr-README.md`); `development-process.md`, `ai-workflow.md`, `ci.md`. Write the block of `development-process.md` § The PR body to `.github/PULL_REQUEST_TEMPLATE.md` when no pull-request template exists in any case under `.github/`, `docs/`, the root, `.azuredevops/` or `.vsts/`.

   **Informative:** write `docs/architecture.md` from `constitution.md` when absent; no `requirements/` directory and no traceability map; the descriptor carries `profile: informative`, `paths.constitution` and `forge: auto`. On both profiles emit no plan template, no `docs/plans/`, no `docs/.sdd/`.

   **3b. Vendor the gate.** Copy the plugin's `tools/sdd-check.py` to `check.script` (default `scripts/sdd-check.py`), creating parents, and `chmod +x` it. Write its version — `python3 <check.script> --version`, or the `__version__ = "…"` line without Python — into `check.version` (`references/sdd-check.md` § Vendoring and the version pin).

   **3c. Starter changelog.** If `check.changelog.path` (default `CHANGELOG.md`) does not exist, write exactly a `# Changelog` heading and an empty `## [Unreleased]` section — the gate errors on a missing changelog. Never overwrite one with content.

   **3d. Ignore the scratch folder.** If `.gitignore` has neither a `/.sdd/` nor a `.sdd/` line, append `/.sdd/` (creating the file) and report it: the orchestrator's scratch files go there, never committed. The findings file lives in the clone's git directory and needs no ignore line (`references/review.md`).
4. **Write the governed entry point.** With no `AGENTS.md`, copy the template, drop its leading `<!-- Template: … -->` comment, and fill the identity and tooling placeholders from the descriptor; with one, never clobber it — report the SDD sections to merge and offer to add them. Fill the descriptor's `agents:` block (worker model, parallelism, reviewers, task-review gate, review panel); every value is an example. Suggest `reviewers` and `worker_skills` from the build manifests: `go.mod` suggests `[go-coding:go-reviewer]` and `[go-coding:go-coding]`, written only after the maintainer confirms that plugin is installed; `composer.json` and `package.json` have no bundled suggestion — name the repository's own reviewer, or leave the list empty and the per-task gate reports itself unconfigured. Nothing dispatches an agent the descriptor does not name. Fill the code-index line in `docs/ai-workflow.md` § Orchestration (`none` when there is no index tool).
5. **Wire the build gate.** When `build_entrypoint` lacks `spec_check_target` or `ci_target`, add them: `<spec_check_target>` running `python3 <check.script> selftest && python3 <check.script> check`, wired into `<ci_target>` — **make**: a `spec-check` rule among `ci`'s prerequisites; **task**: a task whose `cmds:` run both, in `ci`'s `deps:`; **just**: a recipe the `ci` recipe depends on; **npm**: a `"spec-check"` script the `"ci"` script runs with `npm run spec-check`. Propose the diff; never silently rewrite an existing build file.

   **5b. Generate, then check.** Run `python3 <check.script> generate --root .` and then `check --root .`, and read the output. Informative: both pass with the map families skipped. Formal: the starter map has no records, so both report a `map-schema` error and exit 1 by design — `generate` still writes the specifications and ADR indexes and names the record-derived blocks `skipped`, and `check` reports the record-dependent families as `skipped: … (map unavailable)` (`references/sdd-check.md` § What a writing run refuses). Without `python3`, skip both and say the gate could not run here.
6. **Report** created and skipped paths, the vendored version, and step 5b's output. When `check` failed only on the empty starter map, say that is the expected first state and name `/sdd-specify` next; add no "warnings you can ignore" section. On a top-up, when the plugin's tool is newer than `check.version` or the descriptor lacks a template key, name `/sdd-scaffold --upgrade` next.

## `--upgrade` — top up an existing repository

Follow `references/scaffold-upgrade.md` in order: add missing descriptor keys → re-vendor and pin → the starter changelog and the `/.sdd/` ignore line → propose the version's changes → merge the process documents and offer `kind: plan` → missing `kind:` frontmatter → missing generated markers → wire the build target → regenerate → report. Apart from what the procedure proposes and the maintainer confirms, never touch an existing key or a document body with content; add only what is missing and report exactly what changed.

## Guardrails

- **Adopt incrementally.** `requirements/`, `specifications/`, `adr/` and `AGENTS.md` are enough to start — on informative, `docs/architecture.md` alone. Don't force `analysis/` or `operations/`.
- **Respect the taxonomy.** No scaffolding directory that fights the document kinds; a committed plan carries `kind: plan`.
- **A repository that ships its own gate keeps it until `sdd-check` covers what it checks; run both meanwhile.**

## Reference

- `references/templates/` — every file this skill emits.
- `references/traceability-schema.md` — the `.sdd.yaml` and `traceability.yaml` schemas, the `check:` block included.

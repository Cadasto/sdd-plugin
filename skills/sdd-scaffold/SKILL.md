---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", "add SDD structure to this repo", "upgrade the SDD scaffold", or "re-vendor sdd-check". Creates the docs/ tree, templates, the .sdd.yaml descriptor, AGENTS.md, the process docs and the vendored gate, idempotently; --upgrade tops up an older scaffold. Not for authoring a REQ, spec, or ADR (sdd-specify) or a drift scan (sdd-trace).
argument-hint: "[req-style: area-prefixed|flat-numeric] [build tool: make|task|just|npm] [--upgrade]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Scaffold an SDD repository

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy. Step 0 resolves the same root for copying templates.

Lay down the spec-driven structure from the methodology — the `docs/` tree, templates, the project descriptor, the governed `AGENTS.md`, and the process docs. **Idempotent:** detect what already exists and fill gaps; never overwrite a populated file.

## Steps

0. **Resolve bundled templates.** Plugin templates live at `<plugin-root>/references/templates/` — **not** in the consumer repo. Resolve `<plugin-root>` to the install location: on Claude Code use `${CLAUDE_PLUGIN_ROOT}` (and a Cursor plugin-root variable if the host exposes one); otherwise — the host-agnostic fallback — **Glob for the installed `references/templates/sdd.yaml`** outside the consumer workspace. All copy steps below read from this resolved directory. The same resolved root locates the gate to vendor: `<plugin-root>/tools/sdd-check.py`.
1. **Detect existing structure, then route.** Glob for `docs/.sdd.yaml`, `docs/requirements/`, `docs/specifications/`, `AGENTS.md`. When the descriptor exists, Grep it for a line matching `^\s*check:`. Take the first route that matches, in this order:
   - **No descriptor** → a fresh run of steps 2–6, even when `--upgrade` was given; say so in the report, since there is nothing to top up.
   - **`--upgrade` given** → run **`--upgrade`** below instead of steps 2–6.
   - **A descriptor with no `check:` block** → the repository predates the gate. Run **`--upgrade`** below exactly as if the flag had been given, and open the report with `no check: block in docs/.sdd.yaml — ran --upgrade`; a plain top-up would leave it without the gate, the markers and the regeneration.
   - **A descriptor with a `check:` block** → a top-up run of steps 2–6: only create missing pieces and report what was skipped.
2. **Establish conventions** (write them into `docs/.sdd.yaml`):
   - `req_style` — `area-prefixed` (`REQ-AUTH-001`, reads as a capability map) or `flat-numeric` (`REQ-050`, leaner). Ask if unspecified; recommend area-prefixed for products, flat-numeric for libraries.
   - `req_areas` (area-prefixed only), `excluded_areas` — ask an area-prefixed repo which area tokens, if any, are deliberately not areas — `build_entrypoint`, `ci_target`, `spec_check_target`, `use_probes`, `use_strands`, `upstream`, and `ground_truth` (the named "look it up, don't guess" source for this repo's domain facts).
   - `doc_kinds`, `default_mode`, and the `check:`/`hooks:` blocks carry working defaults in the template; copy them as-is (step 3) — nothing here to ask about beyond `excluded_areas`.

   On a repo whose descriptor exists but has no `agents:` block, add that block from the template and touch no other key — the idempotence contract allows this top-up.
3. **Create the tree** (only the missing parts):
   ```
   CHANGELOG.md
   docs/
     .sdd.yaml
     development-process.md   ai-workflow.md   ci.md
     requirements/   (README.md)
     specifications/ (README.md, traceability.yaml)
     adr/            (README.md)
     plans/
   ```
   Copy from the resolved templates directory: `sdd.yaml`→`docs/.sdd.yaml`, `requirement.md`/`specification.md`/`adr.md`/`plan.md` into a `_template.md` in each kind's folder, `traceability.yaml` (starter), the three index READMEs (`requirements-README.md`, `specifications-README.md`, `adr-README.md`), and `development-process.md`/`ai-workflow.md`/`ci.md`.

   **3b. Vendor the gate.** Copy `<plugin-root>/tools/sdd-check.py` to `check.script` (default `scripts/sdd-check.py`), creating parent directories as needed, then `chmod +x` it. Read the tool's own version — `python3 <check.script> --version`, or, when `python3` is unavailable, the `__version__ = "…"` line near the top of the file — and write it into `check.version`. From here on, this repository's own copy is the gate every `/sdd-*` skill and CI call; the plugin's copy is only the source `--upgrade` re-vendors from (`references/sdd-check.md` § Vendoring and the version pin).

   **3c. Create the starter changelog.** If `check.changelog.path` (default `CHANGELOG.md`) does not exist, write it with exactly a `# Changelog` heading followed by a blank `## [Unreleased]` section and nothing else. A missing changelog is a hard `ERROR` in the vendored gate by design, so without this file a fresh scaffold fails its own `check` before a maintainer has written a line. Never overwrite a changelog that already has content.
4. **Write the governed entry point.** If no `AGENTS.md` exists, copy `AGENTS.md` from the templates directory, drop its leading `<!-- Template: … -->` comment, and fill the identity + tooling placeholders from the descriptor. If one exists, do **not** clobber it — instead report the SDD sections to merge in, and offer to add them. Fill the `agents:` block in `docs/.sdd.yaml` with the repo's delivery parameters (worker model, parallelism, reviewers, task-review gate, review panel); every value is an example the repo may change. Suggest `reviewers` and `worker_skills` from the build manifests in the tree: `go.mod` suggests `[go-coding:go-reviewer]` and `[go-coding:go-coding]`; write them only after the maintainer confirms that plugin is installed. `composer.json` or `package.json` has no bundled suggestion, so name the repository's own reviewer agent or leave the list empty and the per-task gate will report itself unconfigured. A suggestion is a scaffold-time hint written into the descriptor, not a runtime dependency: nothing in the plugin dispatches an agent the descriptor does not name. Fill the code-index line in `docs/ai-workflow.md` § Orchestration — `none` when the repo has no index tool.
5. **Wire the build gate.** If `build_entrypoint` has no `spec_check_target` or `ci_target`, add them so the real gate runs, not a stub: `python3 <check.script> selftest && python3 <check.script> check`, under target `<spec_check_target>`, wired into `<ci_target>`. Where it goes: **make**, a `spec-check` rule listed in `ci`'s prerequisites; **task**, a task whose `cmds:` run the two commands, listed in `ci`'s `deps:`; **just**, a recipe listed as a dependency of the `ci` recipe; **npm**, a `"spec-check"` script that the `"ci"` script invokes with `npm run spec-check`. Propose the diff; never silently rewrite an existing build file.

   **5b. Generate, then check.** Run `python3 <check.script> generate --root .`, then `python3 <check.script> check --root .`, and read the output. The starter `traceability.yaml` has no records, so both report a `map-schema` error and exit 1 by design: `generate` still writes the specifications and ADR indexes and names the record-derived blocks as `skipped`, and `check` reports the record-dependent families as `skipped: … (map unavailable)` (`references/sdd-check.md` § What a writing run refuses). Once `/sdd-specify` records the first requirement, the gate passes. When `python3` is unavailable, skip both commands and say in the report that the gate could not run mechanically here.
6. **Report.** List created vs skipped paths, the vendored gate's version, and the `generate`/`check` output from step 5b. When `check` failed only because the starter map has zero records, say plainly that this is the expected first state and name `/sdd-specify` as the next step to capture the first requirement. Do not add a "known warnings you can ignore" section: once the map has a record, there is nothing left to explain away. On a top-up run, when the plugin's tool version is newer than `check.version` or the descriptor lacks a key the template carries, name `/sdd-scaffold --upgrade` as the next step.

## `--upgrade` — top-up an existing repository

Follow `references/scaffold-upgrade.md` in order: add missing descriptor keys → re-vendor and pin → add the starter changelog → add missing `kind:` frontmatter (and propose frontmatter for legacy-header plans) → add missing generated markers → wire the build target → regenerate → report. The fresh path's non-destructive contract holds throughout: never touch an existing key or a document body that has content, only add what is missing, and report exactly what changed.

## Guardrails

- **Idempotent and non-destructive.** Never overwrite a file that already has content. Fill gaps; report skips.
- **Adopt incrementally.** A small repo can start with just `requirements/`, `specifications/`, `plans/`, `adr/`, and `AGENTS.md`. Don't force the optional folders (`analysis/`, `operations/`).
- **Respect the taxonomy.** Do not create scaffolding directories that fight the document kinds. Plans belong in `paths.plans` (default `docs/plans/`); if another tool wants a different tree, point it here rather than keeping two.
- **The descriptor is the contract.** Every other `sdd-*` skill reads `docs/.sdd.yaml`; get it right here.
- **A repository that already ships its own gate keeps it until `sdd-check` covers what it checks; run both in the meantime.**

## Reference

- `references/templates/` — every file this skill emits (resolve via step 0).
- `references/scaffold-upgrade.md` — the `--upgrade` procedure.
- `references/traceability-schema.md` — the `.sdd.yaml` and `traceability.yaml` schemas, including the `check:` block.
- `references/sdd-methodology.md` — §3 document kinds, §5 identifiers, the repo-structure blueprint.
- `references/sdd-check.md` — the vendored gate's commands, families, and the version pin steps 3b and `--upgrade` enforce.

---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", "add SDD structure to this repo", "upgrade a 0.5.x repository", "adopt the sdd-check gate", or "re-vendor sdd-check". Creates the docs/ tree, templates, the .sdd.yaml descriptor, AGENTS.md, and the process docs, idempotently; with --upgrade, tops up a repository scaffolded by an earlier plugin version. Not for authoring a requirement, spec, or decision in a scaffolded repo (sdd-specify).
argument-hint: "[req-style: area-prefixed|flat-numeric] [build tool: make|task|just|npm] [--upgrade]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Scaffold an SDD repository

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy. Step 0 resolves the same root for copying templates.

Lay down the spec-driven structure from the methodology — the `docs/` tree, templates, the project descriptor, the governed `AGENTS.md`, and the process docs. **Idempotent:** detect what already exists and fill gaps; never overwrite a populated file.

## Steps

0. **Resolve bundled templates.** Plugin templates live at `<plugin-root>/references/templates/` — **not** in the consumer repo. Resolve `<plugin-root>` to the install location: on Claude Code use `${CLAUDE_PLUGIN_ROOT}` (and a Cursor plugin-root variable if the host exposes one); otherwise — the host-agnostic fallback — **Glob for the installed `references/templates/sdd.yaml`** outside the consumer workspace. All copy steps below read from this resolved directory. The same resolved root locates the gate to vendor: `<plugin-root>/tools/sdd-check.py`.
1. **Detect existing structure.** Glob for `docs/.sdd.yaml`, `docs/requirements/`, `docs/specifications/`, `AGENTS.md`. If a descriptor already exists, this is a top-up run — only create missing pieces and report what was skipped. Given `--upgrade`, run **`--upgrade` — top-up an existing repository** below instead of steps 2–5b.
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

   **3b. Vendor the gate.** Copy `<plugin-root>/tools/sdd-check.py` to `check.script` (`docs/.sdd.yaml` → `check.script`, default `scripts/sdd-check.py`), creating parent directories as needed, then `chmod +x` it. Read the tool's own version — `python3 <check.script> --version`, or, when `python3` is unavailable, the `__version__ = "…"` line near the top of the file — and write it into `check.version`. From here on, this repository's own copy is the gate every `/sdd-*` skill and CI call; the plugin's copy is only the source `--upgrade` re-vendors from.

   **3c. Create the starter changelog.** If `check.changelog.path` (`docs/.sdd.yaml` → `check.changelog.path`, default `CHANGELOG.md`) does not already exist, write it with exactly a `# Changelog` heading followed by a blank `## [Unreleased]` section and nothing else. A missing changelog is a hard `ERROR` in the vendored gate by deliberate design (step 3b vendors that gate), so without this file a freshly scaffolded repository fails its own `check` before a maintainer has written a single line — never overwrite a `CHANGELOG.md` that already has content.
4. **Write the governed entry point.** If no `AGENTS.md` exists, copy `AGENTS.md` from the templates directory and fill the identity + tooling placeholders from the descriptor. If one exists, do **not** clobber it — instead report the SDD sections to merge in, and offer to add them. Fill the `agents:` block in `docs/.sdd.yaml` with the repo's delivery parameters (worker model, parallelism, reviewers, task-review gate, review panel); every value is an example the repo may change. Suggest `reviewers` and `worker_skills` from the build manifests in the tree and let the maintainer confirm: `go.mod` suggests `[go-coding:go-reviewer]` and `[go-coding:go-coding]`, when that plugin is installed; `composer.json` or `package.json` has no bundled suggestion, so name the repository's own reviewer agent or leave the list empty and the per-task gate will report itself unconfigured. A suggestion is a scaffold-time hint written into the descriptor, not a runtime dependency: nothing in the plugin dispatches an agent the descriptor does not name. Fill the code-index line in `docs/ai-workflow.md` § Orchestration — `none` when the repo has no index tool.
5. **Wire the build gate.** If the chosen `build_entrypoint` has no `spec_check_target`/`ci_target`, add them so the real gate runs, not a stub:
   - **make** — `spec-check: ; python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check` (substitute `check.script`'s actual path if it is not the default), and add `spec-check` to `ci`'s prerequisites.
   - **task** — a `spec-check` task whose `cmds:` run `python3 scripts/sdd-check.py selftest` then `python3 scripts/sdd-check.py check`, and add `spec-check` to `ci`'s `deps:`.
   - **just** — a `spec-check` recipe running the same two lines, and list `spec-check` as a dependency of the `ci` recipe.
   - **npm** — a `"spec-check"` script running `python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check`, and have the `"ci"` script invoke it (`npm run spec-check`) alongside its existing steps.

   Do not silently rewrite an existing build file — propose the diff.

   **5b. Generate, then check.** Run `python3 <check.script> generate --root .`, then `python3 <check.script> check --root .`, and read the output. The starter `traceability.yaml` carries no records, so both stop on a `map-schema` error by design: `generate` writes nothing, and `check` reports the record-dependent families as `skipped: … (map unavailable)`. This first failure is expected, not a defect; step 6 says so. Once `/sdd-specify` records the first requirement, `generate` fills the index blocks and status lines from the map and the gate passes. When `python3` is unavailable, skip both commands and say in the report that the gate could not run mechanically here.
6. **Report.** List created vs skipped paths, the vendored gate's version, and the `generate`/`check` output from step 5b. When `check` failed only because the starter map has zero records, say plainly that this is the expected first state and name `/sdd-specify` as the next step to capture the first requirement — the run is genuinely clean once that record exists. Do not add a "known warnings you can ignore" section: once the map has a record, there is nothing left to explain away.

## `--upgrade` — top-up an existing repository

Same non-destructive contract as the fresh path, run against a repository scaffolded before the gate existed (0.5.x) or before a later descriptor key was added. Never touch a key that already exists or a document body that already has content — only add what is missing, then report exactly what changed so a maintainer can predict it before running the command. The steps are ordered by dependency: the descriptor gains its `check:` block before anything writes into it.

1. **Add missing descriptor keys.** Compare `docs/.sdd.yaml` against the template's key set and add any key the repository is missing, with the template's default value — `excluded_areas`, `doc_kinds`, `default_mode`, the `check:` block (including `script`, default `scripts/sdd-check.py`, and `version`), the `hooks:` block, and the `agents:` block. Add missing keys inside an existing `check:` block too. Never edit a key that is already there, whatever its value.

2. **Re-vendor and pin.** Now that `check:` exists to hold it, compare the plugin's own tool version (`python3 <plugin-root>/tools/sdd-check.py --version`, or the `__version__` line when `python3` is unavailable) against `check.version`. When the plugin's is newer, or `check.script` does not exist yet, copy the plugin's copy over `check.script` (default `scripts/sdd-check.py`, creating it and its parents if this repository never vendored one), `chmod +x`, and write the new version into `check.version`. When the two already agree, do nothing. When the vendored copy is newer than the plugin's, stop and say so rather than downgrading it.

3. **Add the starter changelog, if missing.** `check.changelog.path` (default `CHANGELOG.md`) names a hard `ERROR` when the file is absent. If it does not exist, create it with exactly a `# Changelog` heading and a blank `## [Unreleased]` section. Never overwrite one that already has content.

4. **Add missing `kind:` frontmatter.** The scope is closed: exactly ten files — the six process documents this skill writes (`docs/development-process.md`, `docs/ai-workflow.md`, `docs/ci.md`, the three index READMEs) and the four `_template.md` stubs in each kind's folder (`docs/requirements/_template.md`, `docs/specifications/_template.md`, `docs/adr/_template.md`, `docs/plans/_template.md`). For any of those ten whose frontmatter has no `kind:` line, add the line the current template uses for that file — `kind: requirement`/`specification`/`adr`/`plan` for the four stubs. When a file has no frontmatter block at all, add a `---` block on line 1 holding only that `kind:` line: a bare `kind:` line with no fences does not parse. Nothing wider — a hand-authored requirement, specification, ADR or plan is the maintainer's own content, and `--upgrade` never edits it or its body.

5. **Add missing generated markers.** For each of the three index READMEs that carries a hand-written table but no marker pair, wrap the existing table in the matching markers — `<!-- sdd:generated requirements-index -->`, `<!-- sdd:generated specifications-index -->` or `<!-- sdd:generated adr-index -->`, and the close marker `<!-- /sdd:generated -->` (their format is owned by [traceability-schema.md](../../references/traceability-schema.md) §4). Wrapping only adds the marker comments; it does not rewrite the table. A README with no table is skipped; one with two tables, or an opening marker and no close, is left alone and named in the report rather than guessed at.

6. **Wire the build target.** If the `spec-check` target does not already run the vendored gate, propose the wiring — the same target the fresh path writes at step 5b — so `<build_entrypoint> <spec_check_target>` and CI run `python3 <check.script> check --root .`. Do not silently rewrite an existing build file; propose the diff.

7. **Regenerate.** Run `python3 <check.script> generate --verify --root .` (when `python3` is unavailable, skip this step and say the regeneration could not run here). `--verify` reports what would change and writes nothing. The tool refuses on its own to delete a hand-written index row that has no record in the map: it names each such row and the real `generate` writes nothing while any row would drop, so this step cannot lose data even if followed carelessly. `--verify` exits 1 on any staleness — expected right after step 5 wrapped a table — so read the diff, not the exit code. Diagnose a dropped row by its block: a requirements row with no `REQ-` record in `traceability.yaml`; a specifications row whose file is missing under `paths.specifications` or whose kind is not `specification`; an adr row whose file is missing or is named outside `^(ADR-|\d{4}-)`. Capture the missing record (`/sdd-specify` for a requirement) or delete the stale row by hand, then rerun. When no row would drop, run the real `python3 <check.script> generate --root .`, then `python3 <check.script> check --root .` and read its output.

8. **Report.** Every descriptor key added, whether the starter `CHANGELOG.md` was created, the re-vendor outcome (old → new version, or "already current"), every `kind:` line added, every README wrapped, the build-target wiring proposed, every row `generate` refused (block and id/title, left in place), and the `generate`/`check` output for whatever ran. When a row was refused, name its fix and say the block keeps failing the `generated` family until the record exists or the stale row is removed and `--upgrade` runs again.

## Guardrails

- **Idempotent and non-destructive.** Never overwrite a file that already has content. Fill gaps; report skips.
- **Adopt incrementally.** A small repo can start with just `requirements/`, `specifications/`, `plans/`, `adr/`, and `AGENTS.md`. Don't force the optional folders (`analysis/`, `operations/`).
- **Respect the taxonomy.** Do not create scaffolding directories that fight the document kinds. Plans belong in `docs/plans/`; if another tool wants a different tree, point it here rather than keeping two.
- **The descriptor is the contract.** Every other `sdd-*` skill reads `docs/.sdd.yaml`; get it right here.
- **A repository that already ships its own gate keeps it until `sdd-check` covers what it checks; run both in the meantime.**

## Reference

- `references/templates/` — every file this skill emits (resolve via step 0).
- `references/traceability-schema.md` — the `.sdd.yaml` and `traceability.yaml` schemas, including the `check:` block.
- `references/sdd-methodology.md` — §3 document kinds, §5 identifiers, the repo-structure blueprint.
- `references/sdd-check.md` — the vendored gate's commands, families, and the version pin steps 3b and `--upgrade` enforce.

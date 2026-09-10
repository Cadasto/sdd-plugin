---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", or "add SDD structure to this repo". Creates the docs/ tree, templates, the .sdd.yaml descriptor, AGENTS.md, and the process docs, idempotently. Not for authoring a requirement, spec, or decision in a scaffolded repo (sdd-specify).
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
4. **Write the governed entry point.** If no `AGENTS.md` exists, copy `AGENTS.md` from the templates directory and fill the identity + tooling placeholders from the descriptor. If one exists, do **not** clobber it — instead report the SDD sections to merge in, and offer to add them. Fill the `agents:` block in `docs/.sdd.yaml` with the repo's delivery parameters (worker model, parallelism, reviewers, task-review gate, review panel); every value is an example the repo may change. Suggest `reviewers` and `worker_skills` from the build manifests in the tree and let the maintainer confirm: `go.mod` suggests `[go-coding:go-reviewer]` and `[go-coding:go-coding]`, when that plugin is installed; `composer.json` or `package.json` has no bundled suggestion, so name the repository's own reviewer agent or leave the list empty and the per-task gate will report itself unconfigured. A suggestion is a scaffold-time hint written into the descriptor, not a runtime dependency: nothing in the plugin dispatches an agent the descriptor does not name. Fill the code-index line in `docs/ai-workflow.md` § Orchestration — `none` when the repo has no index tool.
5. **Wire the build gate.** If the chosen `build_entrypoint` has no `spec_check_target`/`ci_target`, add them so the real gate runs, not a stub:
   - **make** — `spec-check: ; python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check` (substitute `check.script`'s actual path if it is not the default), and add `spec-check` to `ci`'s prerequisites.
   - **task** — a `spec-check` task whose `cmds:` run `python3 scripts/sdd-check.py selftest` then `python3 scripts/sdd-check.py check`, and add `spec-check` to `ci`'s `deps:`.
   - **just** — a `spec-check` recipe running the same two lines, and list `spec-check` as a dependency of the `ci` recipe.
   - **npm** — a `"spec-check"` script running `python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check`, and have the `"ci"` script invoke it (`npm run spec-check`) alongside its existing steps.

   Do not silently rewrite an existing build file — propose the diff.

   **5b. Generate, then check.** Run `python3 <check.script> generate --root .` before the first `python3 <check.script> check --root .`: a freshly scaffolded repository's three index blocks and status lines still hold placeholder rows, so the `generated` family — an error family — would fail until `generate` writes the real content from the map; running `generate` first is why a repository just created gets a gate it can pass. Read the `check` output. The starter `traceability.yaml` carries no records, which is a `map-schema` error by design — the record-dependent families report `skipped: … (map unavailable)` — so this first `check` failing is expected, not a defect; step 6 says so. When `python3` is unavailable, skip both commands and say in the report that the gate could not run mechanically here.
6. **Report.** List created vs skipped paths, the vendored gate's version, and the `generate`/`check` output from step 5b. When `check` failed only because the starter map has zero records, say plainly that this is the expected first state and name `/sdd-specify` as the next step to capture the first requirement — the run is genuinely clean once that record exists. Do not add a "known warnings you can ignore" section: once the map has a record, there is nothing left to explain away.

## `--upgrade` — top-up an existing repository

Same non-destructive contract as steps 1–5b, run against a repository that was scaffolded before the gate existed (0.5.x) or before a later descriptor key was added. Never touch a key that already exists or a document body that already has content — only add what is missing, then report exactly what changed so a maintainer can predict it before running the command.

1. **Re-vendor, if stale.** Compare the plugin's own tool version (`<plugin-root>/tools/sdd-check.py`'s `__version__`) against `check.version`. When they differ, or `check.script` does not exist yet, copy the plugin's copy over `check.script` (creating it if this repository never vendored one), `chmod +x`, and write the new version into `check.version`. When the two already agree, do nothing — a second `--upgrade` run must find nothing to re-vendor.
2. **Add missing descriptor keys.** Compare `docs/.sdd.yaml` against the template's key set and add any key the repository is missing, with the template's default value (`excluded_areas`, `doc_kinds`, `default_mode`, the `check:` and `hooks:` blocks, the `agents:` block). Never edit a key that is already there, whatever its value.
3. **Add missing `kind:` frontmatter.** For every process document this skill emits (`docs/development-process.md`, `docs/ai-workflow.md`, `docs/ci.md`, the three index READMEs, and any other emitted doc) that opens with no `kind:` line, add the line the template uses for that file. Never touch a document that already declares a `kind:`, and never touch its body.
4. **Add missing generated markers.** For each of the three index READMEs that carries a hand-written table but no `<!-- sdd:generated … -->` marker pair, wrap the existing table in the matching markers without deleting its rows. Wrapping only adds the marker comments — it does not rewrite the table. The next step decides, row by row, whether `generate` may.
5. **Verify before writing — `generate` must never be the thing that drops a row.** Before running the real `generate`, run `python3 <check.script> generate --verify --root .` (fallback: `python3 <plugin-root>/tools/sdd-check.py generate --verify --root .`; when `python3` is unavailable, skip this step and the rest of step 5, and say in the report that the safety check and the regeneration could not run mechanically here). `--verify` reports what would change and writes nothing. Read its diff in full, one wrapped block at a time: a row that appears in the old content with no corresponding row in the new content is a hand-written row that has no record in `traceability.yaml` — reformatting is not this; only a row that disappears entirely counts. **If the diff drops even one such row, anywhere in any of the three blocks, stop: do not run the real `generate` at all.** Report every dropped row by block and id/title, leave every block exactly as step 4 wrapped it — hand-written rows intact, markers in place, content not yet regenerated — and tell the maintainer to capture each missing row with `/sdd-specify` before running `--upgrade` again. A row that a maintainer wrote by hand but never recorded is exactly the drift the gate exists to surface; writing over it silently would defeat the tool, so `--upgrade` never resolves the mismatch this way. A block left alone here will keep failing the `generated` family on the next `check` — that failure is the surfaced drift, not a defect in `--upgrade`. Only when the diff drops no row anywhere — every hand-written row is represented in the map, at most reformatted — run the real `python3 <check.script> generate --root .`, then `python3 <check.script> check --root .` and read its output, same order and reason as step 5b. Report every path `generate` rewrote as a real content change for the maintainer to read, not scaffolding noise.
6. **Report.** Every descriptor key added, every `kind:` line added, every README wrapped, the re-vendor outcome (old version → new version, or "already current"), every row `--verify` found with no record in the map (block and id/title, left alone, not written), and the `generate`/`check` output for whatever ran. When a row was left alone, name `/sdd-specify` as the next step and say the affected block will keep failing the `generated` family until that record exists and `--upgrade` runs again. Running `--upgrade` a second time in a row, once every reported row has a record, should find nothing left to add or drop and report only the routine `generate`/`check`.

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

---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", "add SDD structure to this repo", or "create the requirements/specifications layout". Creates the SDD docs/ tree, document templates, the .sdd.yaml descriptor, AGENTS.md, and the process docs — idempotently. Not for adding a single requirement or spec to an already-scaffolded repo (use sdd-requirement / sdd-spec).
argument-hint: "[req-style: area-prefixed|flat-numeric] [build tool: make|task|just|npm]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Scaffold an SDD repository

Lay down the spec-driven structure from the methodology — the `docs/` tree, templates, the project descriptor, the governed `AGENTS.md`, and the process docs. **Idempotent:** detect what already exists and fill gaps; never overwrite a populated file. Bundled templates live in `${CLAUDE_PLUGIN_ROOT}/references/templates/`.

## Steps

1. **Detect existing structure.** Glob for `docs/.sdd.yaml`, `docs/requirements/`, `docs/specifications/`, `AGENTS.md`. If a descriptor already exists, this is a top-up run — only create missing pieces and report what was skipped.
2. **Establish conventions** (write them into `docs/.sdd.yaml`):
   - `req_style` — `area-prefixed` (`REQ-AUTH-001`, reads as a capability map) or `flat-numeric` (`REQ-050`, leaner). Ask if unspecified; recommend area-prefixed for products, flat-numeric for libraries.
   - `req_areas` (area-prefixed only), `build_entrypoint`, `ci_target`, `spec_check_target`, `use_probes`, `use_strands`, `upstream`, and `ground_truth` (the named "look it up, don't guess" source for this repo's domain facts).
3. **Create the tree** (only the missing parts):
   ```
   docs/
     .sdd.yaml
     development-process.md   ai-workflow.md   ci.md
     requirements/   (README.md)
     specifications/ (README.md, traceability.yaml)
     adr/            (README.md)
     plans/          (README.md, archive/)
   ```
   Copy from `references/templates/`: `sdd.yaml`→`docs/.sdd.yaml`, `requirement.md`/`specification.md`/`adr.md`/`plan.md` into a `_template.md` in each kind's folder, `traceability.yaml` (starter), the two index READMEs, and `development-process.md`/`ai-workflow.md`/`ci.md`.
4. **Write the governed entry point.** If no `AGENTS.md` exists, copy `references/templates/AGENTS.md` and fill the identity + tooling placeholders from the descriptor. If one exists, do **not** clobber it — instead report the SDD sections to merge in, and offer to add them.
5. **Stub the build gate.** If the chosen `build_entrypoint` has no `spec_check_target`/`ci_target`, offer to add stub targets (a `spec-check` that runs `sdd-trace`-style checks, wired into `ci`). Don't silently rewrite an existing build file — propose the diff.
6. **Report.** List created vs skipped paths and the next step (`sdd-requirement` to capture the first capability).

## Guardrails

- **Idempotent and non-destructive.** Never overwrite a file that already has content. Fill gaps; report skips.
- **Adopt incrementally.** A small repo can start with just `requirements/`, `specifications/`, `plans/`, `adr/`, and `AGENTS.md`. Don't force the optional folders (`analysis/`, `operations/`).
- **Respect the taxonomy.** Do not create scaffolding directories that fight the document kinds (e.g. a generic `docs/<tool-name>/` dump). Design specs and plans route into `docs/plans/`; if another tool wants a stray path, override it and note the override.
- **The descriptor is the contract.** Every other `sdd-*` skill reads `docs/.sdd.yaml`; get it right here.

## Reference

- `references/templates/` — every file this skill emits.
- `references/traceability-schema.md` — the `.sdd.yaml` and `traceability.yaml` schemas.
- `references/sdd-methodology.md` — §3 document kinds, §5 identifiers, the repo-structure blueprint.

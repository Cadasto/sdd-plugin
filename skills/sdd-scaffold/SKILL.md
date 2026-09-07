---
name: sdd-scaffold
description: This skill should be used when the user asks to "set up SDD", "initialize spec-driven development", "scaffold the docs tree", "add SDD structure to this repo", or "create the requirements/specifications layout". Creates the SDD docs/ tree, document templates, the .sdd.yaml descriptor, AGENTS.md, and the process docs — idempotently. Not for authoring a requirement, spec, or decision in an already-scaffolded repo (use sdd-specify).
argument-hint: "[req-style: area-prefixed|flat-numeric] [build tool: make|task|just|npm]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Scaffold an SDD repository

> **`references/…` paths resolve from the plugin root** (beside `skills/`, two levels up — not under this skill): `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, `../../references/…` relative, or Glob for the installed copy. (Step 0 below resolves the same root for copying templates.)

Lay down the spec-driven structure from the methodology — the `docs/` tree, templates, the project descriptor, the governed `AGENTS.md`, and the process docs. **Idempotent:** detect what already exists and fill gaps; never overwrite a populated file.

## Steps

0. **Resolve bundled templates.** Plugin templates live at `<plugin-root>/references/templates/` — **not** in the consumer repo. Resolve `<plugin-root>` to the install location: on Claude Code use `${CLAUDE_PLUGIN_ROOT}` (and a Cursor plugin-root variable if the host exposes one); otherwise — the host-agnostic fallback — **Glob for the installed `references/templates/sdd.yaml`** outside the consumer workspace. All copy steps below read from this resolved directory.
1. **Detect existing structure.** Glob for `docs/.sdd.yaml`, `docs/requirements/`, `docs/specifications/`, `AGENTS.md`. If a descriptor already exists, this is a top-up run — only create missing pieces and report what was skipped.
2. **Establish conventions** (write them into `docs/.sdd.yaml`):
   - `req_style` — `area-prefixed` (`REQ-AUTH-001`, reads as a capability map) or `flat-numeric` (`REQ-050`, leaner). Ask if unspecified; recommend area-prefixed for products, flat-numeric for libraries.
   - `req_areas` (area-prefixed only), `build_entrypoint`, `ci_target`, `spec_check_target`, `use_probes`, `use_strands`, `upstream`, and `ground_truth` (the named "look it up, don't guess" source for this repo's domain facts).

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
   Copy from the resolved templates directory: `sdd.yaml`→`docs/.sdd.yaml`, `requirement.md`/`specification.md`/`adr.md`/`plan.md` into a `_template.md` in each kind's folder, `traceability.yaml` (starter), the two index READMEs, and `development-process.md`/`ai-workflow.md`/`ci.md`.
4. **Write the governed entry point.** If no `AGENTS.md` exists, copy `AGENTS.md` from the templates directory and fill the identity + tooling placeholders from the descriptor. If one exists, do **not** clobber it — instead report the SDD sections to merge in, and offer to add them. Fill the `agents:` block in `docs/.sdd.yaml` with the repo's delivery parameters (worker model, parallelism, reviewers, task-review gate, review panel); every value is an example the repo may change. Fill the code-index line in `docs/ai-workflow.md` § Orchestration — `none` when the repo has no index tool.
5. **Stub the build gate.** If the chosen `build_entrypoint` has no `spec_check_target`/`ci_target`, offer to add stub targets (a `spec-check` that runs `sdd-trace`-style checks, wired into `ci`). Don't silently rewrite an existing build file — propose the diff.
6. **Report.** List created vs skipped paths and the next step (`sdd-specify` to capture the first capability, or explore the idea first if it is still open).

## Guardrails

- **Idempotent and non-destructive.** Never overwrite a file that already has content. Fill gaps; report skips.
- **Adopt incrementally.** A small repo can start with just `requirements/`, `specifications/`, `plans/`, `adr/`, and `AGENTS.md`. Don't force the optional folders (`analysis/`, `operations/`).
- **Respect the taxonomy.** Do not create scaffolding directories that fight the document kinds. Plans belong in `docs/plans/`; if another tool wants a different tree, point it here rather than keeping two.
- **The descriptor is the contract.** Every other `sdd-*` skill reads `docs/.sdd.yaml`; get it right here.

## Reference

- `references/templates/` — every file this skill emits (resolve via step 0).
- `references/traceability-schema.md` — the `.sdd.yaml` and `traceability.yaml` schemas.
- `references/sdd-methodology.md` — §3 document kinds, §5 identifiers, the repo-structure blueprint.

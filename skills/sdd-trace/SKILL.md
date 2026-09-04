---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "assemble context for REQ-X", "what implements/tests this requirement", "are there orphan requirements", or wants a quick in-session drift / spec-check scan. Report-only — assembles the one-shot context bundle for a REQ and reports drift/orphans in-session (the spec-check analogue). Not for tests/build verification (the build gate), authoring (sdd-specify), close-out (sdd-archive), or a whole-repo pre-release audit (sdd-traceability-auditor agent).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Trace — the SDD traceability gate

> **`references/…` paths resolve from the plugin root** (beside `skills/`, two levels up — not under this skill): `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, `../../references/…` relative, or Glob for the installed copy.

Owns the *spec-side* check: does the traceability map still match the tree, and what is the full context for a requirement. Read `docs/.sdd.yaml` for paths, the traceability map, and `spec_check_target`. (Whether the tests and the build pass is the build gate's job — see Guardrails.)

## Mode A — context bundle for a REQ

Assemble in one shot so no whole-tree grep is needed:

1. The **registry row** from the requirements index.
2. The **traceability block** — canonical link, `status`/`implementation`, packages, tests, probes, plans.
3. The **canonical spec excerpt** — the actual normative §, fetched from the `canonical` link.
4. Any **open `STRAND`s** touching this REQ (if `use_strands`).

Present it compactly and name the next action (e.g. "no implementation yet → `/sdd-deliver`").

## Mode B — drift scan (the spec-check analogue)

With no REQ, walk the map against the tree and report each orphan class:

- a `canonical` link to a missing file/anchor;
- a listed `package`/`test`/`plan` path that does not exist;
- a `PROBE` id with no corresponding test;
- a requirement marked `landed`/`shipped` with no `packages`/`tests`;
- a `REQ` in the index but not the map (or vice-versa);
- a plan whose frontmatter `status` disagrees with its `REQ` — `status: active` while the `REQ` is already `shipped`, or `status: done` while the `REQ` is not.

If the repo defines the `spec_check_target` build target, run it (`<build_entrypoint> <spec_check_target>`) to corroborate traceability drift. Then report the human-readable breakdown, grouped by class with the offending id/path; **recommend** fixes, do not apply them.

## Guardrails

- **Strictly report-only.** Diagnose; the owning skill fixes (`sdd-specify` for spec/index, the build workflow for code/tests, `sdd-archive` for plan state). Never edit here.
- **Scope is traceability, not test results** — tests and build passing is the build gate's job — run it and read its output.
- For a heavy, context-isolated whole-repo audit, dispatch the **`sdd-traceability-auditor`** agent — same scan, isolated context, returns a report.

## Reference

- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain & drift CI, §10 the one-shot bundle.

---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "assemble context for REQ-X", "what implements/tests this requirement", "are there orphan requirements", or wants a quick in-session drift / spec-check scan. Owns the SDD traceability gate — assembles the one-shot context bundle for a REQ and reports drift/orphans in-session (the spec-check analogue). Not for generic "do the tests/build pass" verification (use superpowers verification-before-completion), authoring documents (sdd-specify), closing out a feature (sdd-archive), or a heavy whole-repo / pre-release audit (dispatch the sdd-traceability-auditor agent).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Trace — the SDD traceability gate

Owns the *spec-side* check: does the traceability map still match the tree, and what is the full context for a requirement. This is **not** the generic "tests/build/lint pass" gate — that is `superpowers:verification-before-completion`, which runs alongside this one before any done-claim. Read `docs/.sdd.yaml` for paths, the traceability map, and `spec_check_target`.

## Mode A — context bundle for a REQ

Assemble in one shot so no whole-tree grep is needed:

1. The **registry row** from the requirements index.
2. The **traceability block** — canonical link, `status`/`implementation`, packages, tests, probes, plans.
3. The **canonical spec excerpt** — the actual normative §, fetched from the `canonical` link.
4. Any **open `STRAND`s** touching this REQ (if `use_strands`).

Present it compactly and name the next action (e.g. "no plan yet → `superpowers:writing-plans`, landing it in `docs/plans/` with the SDD citing header").

## Mode B — drift scan (the spec-check analogue)

With no REQ, walk the map against the tree and report each orphan class:

- a `canonical` link to a missing file/anchor;
- a listed `package`/`test`/`plan` path that does not exist;
- a `PROBE` id with no corresponding test;
- a requirement marked `landed`/`shipped` with no `packages`/`tests`;
- a `REQ` in the index but not the map (or vice-versa);
- a `done` plan left in the active list, or an active plan whose REQ is already `shipped`.

If the repo defines the `spec_check_target` build target, run it (`<build_entrypoint> <spec_check_target>`) to corroborate — this checks *traceability* drift, **not** the tests/build/lint gate (that is `superpowers:verification-before-completion`). Then report the human-readable breakdown, grouped by class with the offending id/path; **recommend** fixes, do not apply them.

## Guardrails

- **Strictly read-only.** Diagnose; the owning skill fixes (`sdd-specify` for spec/index, the build workflow for code/tests, `sdd-archive` for plan state). Never edit here.
- **Scope is traceability, not test results.** "Are the tests green?" is `superpowers:verification-before-completion`; this skill answers "does the spec↔code↔test map hold?".
- For a heavy, context-isolated whole-repo audit, dispatch the **`sdd-traceability-auditor`** agent — same scan, isolated context, returns a report.

## Reference

- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain & drift CI, §10 the one-shot bundle.
- `references/sdd-with-superpowers.md` — how this gate pairs with superpowers' generic verification.

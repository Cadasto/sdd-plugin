---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "show drift without running the build", "give me a read-only drift report", "what implements this requirement", "assemble context for REQ-X", "where is REQ-X specified/tested", or "are there orphan requirements". Read-only and runs no build target — assembles the one-shot context bundle (index row + traceability block + canonical spec excerpt + open strands) and reports orphans. Not for running the actual build gate / spec-check or claiming done (use sdd-verify); for a heavy whole-repo audit prefer the sdd-traceability-auditor agent.
argument-hint: "[REQ-id, or blank for a whole-tree drift scan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Trace — context bundle & drift report (read-only)

The in-session analogue of a `spec-context` / `spec-check`. **Read-only** — it never modifies files. Two modes. Read `docs/.sdd.yaml` for paths and the traceability map.

## Mode A — context bundle for a REQ

Given a `REQ-*`, assemble in one shot so an agent never greps the whole tree:

1. The **registry row** from the requirements index.
2. The **traceability block** — canonical link, `status`/`implementation`, packages, tests, probes, plans.
3. The **canonical spec excerpt** — the actual normative §, fetched from the `canonical` link.
4. Any **open `STRAND`s** that touch this REQ (if `use_strands`).

Present it as a compact bundle and point to the next action (e.g. "no plan yet → `sdd-plan`").

## Mode B — whole-tree drift scan

With no REQ, walk the traceability map against the tree and report each orphan class:

- a `canonical` link to a missing file/anchor;
- a listed `package`/`test`/`plan` path that does not exist;
- a `PROBE` id with no corresponding test;
- a requirement marked `landed`/`shipped` with no `packages`/`tests`;
- a `REQ` in the index but not the map (or vice-versa);
- a `done` plan left in the active list, or an active plan whose REQ is already `shipped`.

Report findings grouped by class, each with the offending id/path. **Recommend** fixes; do not apply them.

## Guardrails

- **Strictly read-only.** This skill diagnoses; the owning skill (`sdd-spec`, `sdd-implement`, `sdd-archive`) fixes. Never edit here.
- **Mechanical, not interpretive.** Report what the map-vs-tree comparison shows; don't infer intent.
- For a heavy, context-isolated full-repo audit, dispatch the **`sdd-traceability-auditor`** agent instead — it does the same scan in an isolated context and returns a report.

## Reference

- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain, §10 the one-shot bundle.

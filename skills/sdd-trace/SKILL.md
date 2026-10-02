---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "what implements or tests this requirement", "give me the context for REQ-X", "are there orphan requirements", "run a quick drift scan", "run the drift gate", or "audit the traceability" (`--audit`). Report-only — prints a REQ's context bundle, relays the drift gate's findings by family, or dispatches the isolated whole-tree audit. Not for authoring (sdd-specify), close-out (sdd-deliver --close-out), or test and build results (the build gate).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan] [--audit]"
allowed-tools: Read, Glob, Grep, Bash, Agent, Task
---

# Trace — the SDD traceability gate

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` resolves from it.

Owns the spec-side check: does the map match the tree, and what is a requirement's context. Read `docs/.sdd.yaml` first; no descriptor means the repository is not scaffolded — say so, route to `/sdd-scaffold`, and stop. On the informative profile the map is optional and its families are skipped; Mode A needs a map — without one, say so and stop.

Run the gate as `references/sdd-check.md` defines `sdd-check <cmd>`, following its report-only exception when the gate is not vendored. Without `python3`, say so and use the mode's fallback.

## Mode A — context bundle for a REQ

Run `context <REQ>` and present its output as it is: the heading order, an empty section and an unknown id are `sdd-check`'s contract.

**Fallback.** Assemble the bundle by hand: the **registry row** from the requirements index; the **full record** (canonical link, `status`/`implementation`, packages, tests, probes); the **canonical spec excerpt** from the `canonical` link; any **open `STRAND`s** on this REQ (if `use_strands`).

Either way, name the next action (e.g. "no implementation yet → `/sdd-deliver`").

## Mode B — drift scan (the spec-check analogue)

With no REQ, run `check` and report its findings grouped by family, with the offending id or path; `references/sdd-check.md` owns what each finding means — do not re-derive it. When the descriptor names a `spec_check_target`, `<build_entrypoint> <spec_check_target>` may corroborate; the gate's output stays the report. Add judgement only where the tool cannot decide: whether a duplicated-prose finding's second copy is really the same statement. **Recommend** fixes; never apply them.

**Fallback.** Say the mechanical scan cannot run and the drift scan is incomplete; report what the requirements index and the map show by hand.

## Mode C — `--audit`

Dispatch the **`sdd-traceability-auditor`** agent — this skill is the only one that does — before a release or when a `spec-check` failure is unexplained. Relay its report; the orchestrator adds its lines to the findings file only when the maintainer asks.

## Guardrails

- **Strictly report-only.** The owning skill fixes: `/sdd-specify` for spec and index, `/sdd-deliver` for code and tests, `/sdd-deliver --close-out` for the close-out, `/sdd-scaffold --upgrade` for the version pin. `Bash` is for read-only scoping and gate runs; no-write is a contract, not a tool restriction.
- **Scope is traceability, not test results.** Name `<build_entrypoint> <ci_target>` as the next step; do not run it here.

## Reference

- `references/sdd-check.md` — the gate's invocation, commands, families, report format and exit codes.
- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain and drift CI, §10 the one-shot bundle.

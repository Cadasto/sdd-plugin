---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "what implements or tests this requirement", "give me the context for REQ-X", "are there orphan requirements", "run a quick drift scan", "run the drift gate", or "audit the traceability" (`--audit`). Report-only — prints a REQ's context bundle, relays the drift gate's findings by family, or dispatches the isolated whole-tree audit. Not for authoring (sdd-specify), close-out (sdd-deliver --close-out), or test and build results (the build gate).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan] [--audit]"
allowed-tools: Read, Glob, Grep, Bash, Agent, Task
---

# Trace — the SDD traceability gate

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` resolves from it.

Read `docs/.sdd.yaml` first; without one, route to `/sdd-scaffold` and stop. Mode A needs a map: without one (the informative profile may have none), say so and stop.

Run the gate as `references/sdd-check.md` defines `sdd-check <cmd>`, following its report-only exception when the gate is not vendored. Without `python3`, say so and use the mode's fallback.

## Mode A — context bundle for a REQ

Run `context <REQ>` and present its output unchanged.

**Fallback.** Assemble by hand what `context` prints (`references/sdd-check.md` § Commands); strands only if `use_strands`.

Either way, name the next action (e.g. "no implementation yet → `/sdd-deliver`").

## Mode B — drift scan (the spec-check analogue)

With no REQ, run `check` and report its findings by family, with the offending id or path; `references/sdd-check.md` owns what each finding means. Add judgement only where the tool cannot decide: whether a duplicated-prose finding's second copy is really the same statement.

**Fallback.** Say the scan is incomplete; compare the requirements index and the map by hand.

## Mode C — `--audit`

Dispatch the **`sdd-traceability-auditor`** agent and relay its report.

## Guardrails

- **Strictly report-only.** The owning skill fixes: `/sdd-specify` for spec and index, `/sdd-deliver` for code and tests, `/sdd-deliver --close-out` for the close-out, `/sdd-scaffold --upgrade` for the version pin. Recommend fixes; `Bash` runs only read-only commands and the gate.
- **Scope is traceability, not test results.** Name `<build_entrypoint> <ci_target>` as the next step; do not run it here.

## Reference

- `references/sdd-check.md` — the gate's invocation, commands, families, report format and exit codes.
- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain and drift CI, §10 the one-shot bundle.

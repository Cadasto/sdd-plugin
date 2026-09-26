---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "what implements or tests this requirement", "give me the context for REQ-X", "are there orphan requirements", or "run a quick drift scan". Report-only. Prints a REQ's context bundle with the gate's `context`, or runs `check` in-session and relays its findings by family. Not for authoring (sdd-specify), close-out (sdd-archive), test or build results (the build gate), or a context-isolated audit that covers skipped families and adds judgement beyond the gate (sdd-traceability-auditor agent).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Trace — the SDD traceability gate

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Owns the *spec-side* check: does the traceability map still match the tree, and what is the full context for a requirement. Read `docs/.sdd.yaml` first for paths and the traceability map. No descriptor means the repository is not scaffolded: report that, route to `/sdd-scaffold`, and stop. (Whether the tests and the build pass is the build gate's job — see Guardrails.)

Run the gate as `references/sdd-check.md` defines `sdd-check <cmd>`. As a report-only caller, follow that file's report-only exception when the gate is not vendored. Mode A runs `context`, Mode B runs `check`; when `python3` is unavailable, say so and use the mode's fallback.

## Mode A — context bundle for a REQ

Run `context <REQ>` and present its output as-is — the heading order and what an empty section prints are `sdd-check`'s contract (`references/sdd-check.md`); an unknown id is reported as the tool prints it.

**Fallback — Python unavailable.** Assemble the same bundle by hand: the **registry row** from the requirements index; the **full traceability record** (canonical link, `status`/`implementation`, packages, tests, probes); the **canonical spec excerpt**, fetched from the `canonical` link; any **open `STRAND`s** touching this REQ (if `use_strands`). Present it compactly.

Either way, name the next action (e.g. "no implementation yet → `/sdd-deliver`").

## Mode B — drift scan (the spec-check analogue)

With no REQ, run `check` and report its output grouped by family — `references/sdd-check.md` owns the families and what each finding means; do not re-derive them here. When the descriptor names a `spec_check_target`, `<build_entrypoint> <spec_check_target>` may be run as corroboration; the gate's own output stays the report. Then, only for what the tool cannot decide, add judgement: a plan/`REQ` status mismatch the tool flagged as a warning is worth reading in its full context before recommending a fix; a duplicated-prose finding is worth a second look at whether the second copy is really the same statement.

**Fallback — Python unavailable.** Say so; the mechanical scan cannot run here. Report what can still be read by hand from the requirements index and the traceability map, and say the drift scan is incomplete without the gate.

Report the breakdown, grouped by family, with the offending id/path; **recommend** fixes, do not apply them.

## Guardrails

- **Strictly report-only.** Diagnose; the owning skill fixes: `/sdd-specify` for spec and index, `/sdd-deliver` for code and tests, `/sdd-archive` for the close-out, `/sdd-scaffold --upgrade` for the version pin. Never edit here. Bash is for read-only scoping and gate runs only; the no-write rule is a contract, not a tool restriction.
- **Scope is traceability, not test results.** Tests and the build passing are the build gate's job: name `<build_entrypoint> <ci_target>` as the next step; do not run it here.
- For a context-isolated audit that runs the same gate, then checks skipped families by hand and adds the judgement findings no family can make (before a release, or when a `spec-check` failure is unexplained), dispatch the **`sdd-traceability-auditor`** agent.

## Reference

- `references/sdd-check.md` — the gate's invocation, commands, families, report format, and exit codes that both modes run.
- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain & drift CI, §10 the one-shot bundle.

---
name: sdd-trace
description: This skill should be used when the user asks to "show traceability for REQ-X", "what implements or tests this requirement", "are there orphan requirements", or wants a quick drift scan. Report-only. Assembles a REQ's context bundle or reports map-versus-tree drift in-session. Not for tests or build verification, authoring (sdd-specify), close-out (sdd-archive), or a whole-repo audit (sdd-traceability-auditor agent).
argument-hint: "[REQ-id, or blank for a whole-tree drift scan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Trace — the SDD traceability gate

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Owns the *spec-side* check: does the traceability map still match the tree, and what is the full context for a requirement. Read `docs/.sdd.yaml` for paths, the traceability map, and `spec_check_target`. (Whether the tests and the build pass is the build gate's job — see Guardrails.)

## Resolve the gate

Both modes below run `sdd-check`: the repository's vendored copy at `check.script` (`docs/.sdd.yaml`, default `scripts/sdd-check.py`) if it exists, else the plugin's own copy, resolved the same way `references/…` resolves — `${CLAUDE_PLUGIN_ROOT}/tools/sdd-check.py` on Claude Code, or Glob for the installed `tools/sdd-check.py`. Every invocation passes `--root .`. When `python3` is unavailable, say so plainly and use the mode's stated fallback instead of failing silently.

## Mode A — context bundle for a REQ

Run `context <REQ>` and present its output as-is — the heading order and what an empty section prints are `sdd-check`'s contract (`references/sdd-check.md`); an unknown id is reported as the tool prints it.

**Fallback — Python unavailable.** Assemble the same bundle by hand: the **registry row** from the requirements index; the **traceability block** (canonical link, `status`/`implementation`, packages, tests, probes); the **canonical spec excerpt**, fetched from the `canonical` link; any **open `STRAND`s** touching this REQ (if `use_strands`).

Present it compactly and name the next action (e.g. "no implementation yet → `/sdd-deliver`").

## Mode B — drift scan (the spec-check analogue)

With no REQ, run `check` and report its output grouped by family — `references/sdd-check.md` owns the families and what each finding means; do not re-derive them here. Then, only for what the tool cannot decide, add judgement: a plan/`REQ` status mismatch the tool flagged as a warning is worth reading in its full context before recommending a fix; a duplicated-prose finding is worth a second look at whether the second copy is really the same statement.

**Fallback — Python unavailable.** Say so; the mechanical scan cannot run here. Report what can still be read by hand from the requirements index and the traceability map, and say the drift scan is incomplete without the gate.

Report the breakdown, grouped by family, with the offending id/path; **recommend** fixes, do not apply them.

## Guardrails

- **Strictly report-only.** Diagnose; the owning skill fixes (`sdd-specify` for spec/index, the build workflow for code/tests, `sdd-archive` for plan state). Never edit here.
- **Scope is traceability, not test results** — tests and build passing is the build gate's job — run it and read its output.
- For a heavy, context-isolated whole-repo audit, dispatch the **`sdd-traceability-auditor`** agent — the same map-vs-tree scan, isolated context, returns a report.

## Reference

- `references/sdd-check.md` — the gate's commands, families, report format, and exit codes that both modes run.
- `references/traceability-schema.md` — the record format and what counts as drift.
- `references/sdd-methodology.md` — §8 the traceability chain & drift CI, §10 the one-shot bundle.

---
name: sdd-verify
description: This skill should be used when the user asks to "check spec compliance", "is this done?", "run the Definition of Done", "run spec-check", "run the fail-on-drift gate before merge", or "run the gate". Actually executes the full build gate (including the spec-check target), confirms probe/test status, and confirms the spec, requirements index, traceability map, and plan archive are updated; does not auto-fix silently. Not for a read-only drift report that runs no build target (use sdd-trace).
argument-hint: "[REQ-id or plan to verify]"
allowed-tools: Read, Bash, Glob, Grep
---

# Verify — the Definition of Done

The done-gate. Run the repo's full build gate and confirm every Definition-of-Done box before any claim of completion. Read `docs/.sdd.yaml` for `build_entrypoint`, `ci_target`, and `spec_check_target`. Apply the `verification-before-completion` discipline: **evidence before assertion — never claim "done" without showing the gate output.**

## Steps

1. **Run the full gate** — `<build_entrypoint> <ci_target>` (format, lint, build, test, derived-artefact-verify, and **`spec-check`**). Capture and report the actual output.
2. **Run `spec-check` explicitly** if not folded into `ci` — `<build_entrypoint> <spec_check_target>` — and surface any traceability drift (orphan `REQ`/plan/code/probe).
3. **Confirm the Definition of Done** for the feature:
   - [ ] Code + tests merged and green.
   - [ ] Spec and/or guide updated if behaviour changed (and, for implementation-aligned work, in the same change).
   - [ ] Requirements index `status`/`implementation` updated.
   - [ ] `traceability.yaml` updated — packages/tests/probes present for landed work.
   - [ ] Plan flipped to `done` and archived *(route to `sdd-archive`)*.
   - [ ] `AGENTS.md` tables updated if anything user-facing changed.
4. **Check probe/test status** for behaviour changes — each cited `PROBE` resolves to an existing test.
5. **Report a verdict:** PASS only when the gate is green *and* every box holds; otherwise list each failure with its evidence.

## Guardrails

- **No green-washing.** If the gate fails or a box is unchecked, report it plainly with the command output — do not soften it. A failing `spec-check` is a blocking drift signal, not a warning.
- **Don't auto-fix silently.** Surface the drift and propose the fix (or route to the skill that owns it); let the change be deliberate.
- **The build tool is the single source of truth for "passing".** Reproduce CI locally with the same target; don't invent an ad-hoc check.

## Reference

- `references/sdd-methodology.md` — §8 drift CI, §9 Definition of Done.
- `references/traceability-schema.md` — what `spec-check` validates.

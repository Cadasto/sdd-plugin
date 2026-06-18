---
name: sdd-plan
description: This skill should be used when the user asks to "plan REQ-X", "break this into tasks", "create an implementation plan", "make a task list for this feature", or "what are the steps to build X". Creates docs/plans/YYYY-MM-DD-<slug>.md with a citing header, checks the Definition of Ready, and decomposes into small independently testable tasks with verification commands. Not for writing the code (use sdd-implement) or normative behaviour (use sdd-spec).
argument-hint: "<REQ-id or feature to plan>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Plan a slice of work

A plan is the **only** place checkbox tasks live. It cites the `REQ`/`SPEC §`/`ADR` it implements and introduces **no new normative rules** (those go in a spec first). Read `docs/.sdd.yaml` for paths and `ci_target`.

## Steps

1. **Check the Definition of Ready** — refuse to start a plan until all hold (else route to the gap):
   - [ ] A `REQ-*` exists with acceptance criteria. *(missing → `sdd-requirement`)*
   - [ ] Affected `SPEC-* §` are listed, or a new § is explicitly called out. *(missing → `sdd-spec`)*
   - [ ] No open ADR is needed, or the ADR is already `Accepted`. *(open fork → `sdd-adr`)*
   - [ ] Out-of-scope is written; verification commands are named.
2. **Create the file** `docs/plans/YYYY-MM-DD-<slug>.md` from `references/templates/plan.md`. Use today's date; derive the slug from the feature.
3. **Write the citing header** — `implements: [REQ-…, SPEC-NAME §N]`, and the `mode` (`spec-first` for new behaviour, `implementation-aligned` for hardening shipped code).
4. **Decompose into tasks** that are small and *independently testable*. Each task names what it advances (a `REQ`/`PROBE`) and **how to verify it** (`<build_entrypoint> test`, a specific command). Mark dependencies/parallelism where it matters. Favour "create endpoint X that validates Y", not "build the feature".
5. **Carry the Definition of Done checklist** into the plan (the template includes it) so closing the plan via `sdd-archive` is mechanical.
6. **Report** the plan path and suggest `sdd-implement`.

## Guardrails

- **DoR is a gate, not a formality.** A plan that starts without its `REQ`/spec produces drift. Surface the missing piece and route to it.
- **No new normative rules in a plan.** If implementation needs a rule that doesn't exist yet, add it via `sdd-spec` first.
- **Tasks cite identifiers and name verification.** A task with no way to verify it is not a task.
- **Date the filename.** `YYYY-MM-DD-<slug>` — it is how the active/archive lifecycle works.

## Reference

- `references/templates/plan.md` — the template (includes DoR + DoD).
- `references/sdd-methodology.md` — §9 the plan lifecycle, §7 the two modes.

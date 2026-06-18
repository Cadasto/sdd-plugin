---
name: sdd-archive
description: This skill should be used when the user asks to "close out the plan", "archive the plan", "consolidate the spec delta", "mark the requirement shipped", or "this feature is done — close it out". The outer loop — flips a finished (already-verified) plan to done, git mv's it to plans/archive/, updates the active/archive and requirements indexes, and updates AGENTS.md tables if user-facing. Not for checking whether it is done / running the gate (use sdd-verify first) or creating a plan (use sdd-plan).
argument-hint: "<plan file to close out>"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Archive — close out a finished feature (the outer loop)

Once a feature is verified, consolidate its delta into the living project memory and keep the active list a true picture of in-flight work. **Archive-on-completion is normative, not housekeeping** — leaving `done` plans in the active list rots the index. Read `docs/.sdd.yaml` for `paths.plans` and `paths.plans_archive`.

## Preconditions

- The feature has passed `sdd-verify` (gate green, Definition of Done satisfied). If not, run `sdd-verify` first — do not archive unfinished work.

## Steps

1. **Flip the plan** `status: active` → `done` in its frontmatter.
2. **Move it** — `git mv docs/plans/YYYY-MM-DD-<slug>.md docs/plans/archive/` (use `git mv` so history follows). For explicitly deferred work, use a `postponed/` folder with restore criteria instead of archive.
3. **Update the plans index** (`docs/plans/README.md`) — remove from active, add to archived.
4. **Update the requirements index** — set each delivered `REQ`'s `implementation` to `shipped`/`landed`; confirm the traceability map reflects the landed packages/tests.
5. **Update `AGENTS.md` tables** if anything user-facing shipped (a shipped/deferred capability list, a new command, etc.).
6. **Report** what moved and confirm the active list now shows only in-flight work.

## Guardrails

- **Verify before archive.** Archiving is the *last* step; it asserts the work is truly done.
- **Use `git mv`.** Preserve history; don't delete-and-recreate.
- **Keep the active list honest.** No `done` plans left active; no `shipped` `REQ` left `in_progress`.
- **Consolidate, don't duplicate.** The spec already holds the normative delta (updated during implementation); archiving moves the *plan*, it does not re-document the behaviour.

## Reference

- `references/sdd-methodology.md` — §9 archive-on-completion (the outer loop).

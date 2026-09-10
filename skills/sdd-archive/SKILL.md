---
name: sdd-archive
description: This skill should be used when the user asks to "close out the plan", "mark the plan done", "mark the requirement shipped", or "this feature is done, close it out". Flips the plan status to done in place and sets the SPEC §, REQ, traceability, and PR-body surfaces inside the implementing PR. Not for deleting finished plans at a release (sdd-finalize), the drift check (sdd-trace), or review (sdd-review).
argument-hint: "<plan file or REQ to close out>"
allowed-tools: Read, Edit, Bash, Glob, Grep
---

# Archive — the SDD close-out, in place

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Close out a finished slice on the branch that implements it. The plan is flipped to `done` where it lies: no move, no link rewrite, no index. Read `docs/.sdd.yaml` for `paths.plans` and the traceability map location.

The argument is the plan file or the `REQ` being closed out; given neither, find the active plan on this branch and name it before changing anything. If the branch has no plan, stop: a maintenance-lane change has nothing to close out, and a full-lane change without a plan has not been through `/sdd-deliver`.

## When to run it

Run this as the last commit before the PR is marked ready, once round 0 of the review ledger is clean. `/sdd-deliver` runs it at that point.

## Preconditions

- The verification command was run on this branch and its output was read — never claim green that was not seen.
- Round 0 of the ledger has no open blocker.

Do not close out unverified work; closing out asserts the slice is done.

## Steps

1. **Spec status** — promote each affected `SPEC §` status where appropriate. For implementation-aligned work, confirm the § was updated in the same change and is not lagging.
2. **Traceability record** — set the delivered `REQ`'s `implementation` status and mirror the promoted spec `status` in its `traceability.yaml` record in this same commit (`references/sdd-methodology.md` §6; it takes effect when the PR merges); confirm it lists the landed `packages`, `tests`, and `probes` — a record carries no plan axis and no PR pointer, do not add one. Then run `sdd-check generate` (the repository's vendored copy at `check.script`, else the plugin's own `tools/sdd-check.py`, with `--root .`; when `python3` is unavailable, say so and leave the block for the next run rather than hand-editing it) so the index rows and the requirement detail file's status lines pick up the change.
3. **Confirm the gate is clean** — run `sdd-check check`: the repository's vendored copy at `check.script`, else the plugin's own `tools/sdd-check.py`, with `--root .`. Read the summary line and confirm it reports clean before continuing. When `python3` is unavailable, say so and confirm by hand instead.
4. **Plan** — edit the plan's frontmatter `status: active` → `status: done`. Leave the file exactly where it is. Never `git mv` a plan, never create or update a plans index, and never write into a `plans/archive/` directory — deleting finished plans is `/sdd-finalize`'s job at the next version bump.
5. **PR body** — fill the close-out block from the repo's `docs/development-process.md`: the `Lane:` line, the identifiers, the plan path, the claim line, the review lens, what was verified and what the output said, the close-out checkboxes, the deferred items, and the workers' en-route findings. That file owns the block; fill it, don't redefine it.
6. **Report** — what was set, and the next action (mark the PR ready).

## Guardrails

- **Cite, don't restate** — the close-out commit and PR body follow `references/artefact-prose.md`.
- **Four close-out surfaces plus the in-place plan flip:** `SPEC §` status, `REQ` status, `traceability.yaml`, PR body — and the plan's `status: done` (step 4). Nothing else changes at close-out.
- **`AGENTS.md` capability tables are maintenance-lane work**; update them if something user-facing shipped, in this PR or the next.
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.**

## Reference

- `references/sdd-methodology.md` — §9 the plan lifecycle, §13 the two gates.
- `references/sdd-check.md` — the `check` summary line step 3 confirms, and what `generate` writes.
- `references/artefact-prose.md` — the ledger and the close-out prose.
- `skills/sdd-finalize` — the release sweep that deletes finished plans at the next version bump.

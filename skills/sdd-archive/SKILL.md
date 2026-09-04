---
name: sdd-archive
description: 'This skill should be used when the user asks to "close out the plan", "mark the plan done", "mark the requirement shipped", or "this feature is done — close it out". The SDD close-out inside the implementing PR — flips the plan''s frontmatter to `status: done` where it lies, sets the SPEC § and REQ statuses and the traceability map, and fills the PR body. No file move, no index. Not for deleting finished plans at a release (sdd-finalize), for the drift check (sdd-trace), or for reviewing the change (sdd-review).'
argument-hint: "<plan file or REQ to close out>"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Archive — the SDD close-out, in place

> **`references/…` paths resolve from the plugin root** (beside `skills/`, two levels up — not under this skill): `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, `../../references/…` relative, or Glob for the installed copy.

Close out a finished slice on the branch that implements it. The plan is flipped to `done` where it lies: no move, no link rewrite, no index. Read `docs/.sdd.yaml` for `paths.plans` and the traceability map location.

The argument is the plan file or the `REQ` being closed out; given neither, find the active plan on this branch and name what you found before changing anything.

## When to run it

Run this as the last commit before the PR is marked ready, once round 0 of the review ledger is clean. `/sdd-deliver` runs it for you at that point.

## Preconditions

- The verification command was run on this branch and its output was read — never claim green you did not see.
- Round 0 of the ledger has no open blocker.

Do not close out unverified work; closing out asserts the slice is done.

## Steps

1. **Spec status** — promote each affected `SPEC §` status where appropriate. For implementation-aligned work, confirm the § was updated in the same change and is not lagging.
2. **Requirement status** — set each delivered `REQ`'s `implementation` status in this same commit (`references/sdd-methodology.md` §6); it takes effect when the PR merges.
3. **Traceability** — confirm `traceability.yaml` lists the landed packages, tests, and probes. A record carries no plan axis and no PR pointer — do not add one.
4. **Plan** — Edit the plan's frontmatter `status: active` → `status: done`. Leave the file exactly where it is. Never `git mv` a plan, never create or update a plans index, and never write into a `plans/archive/` directory — deleting finished plans is `/sdd-finalize`'s job at the next version bump.
5. **PR body** — fill the close-out block from the repo's `docs/development-process.md`: the `Lane:` line, the identifiers, the plan path, the claim line, the review lens, what was verified and what the output said, the close-out checkboxes, the deferred items, and the workers' en-route findings. That file owns the block; fill it, don't redefine it.
6. **Report** — what was set, and the next action (mark the PR ready).

## Guardrails

- **The plan does not move.**
- **There is no plans index.**
- **Cite, don't restate** — the close-out commit and PR body follow `references/artefact-prose.md`.
- **Four surfaces, not seven:** `SPEC §` status, `REQ` status, `traceability.yaml`, PR body.
- **`AGENTS.md` capability tables are maintenance-lane work**; update them if something user-facing shipped, in this PR or the next.

## Reference

- `references/sdd-methodology.md` — §9 the plan lifecycle, §13 the two gates.
- `references/artefact-prose.md` — the ledger and the close-out prose.
- `skills/sdd-finalize` — the release sweep that deletes finished plans at the next version bump.

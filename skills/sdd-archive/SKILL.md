---
name: sdd-archive
description: This skill should be used when the user asks to "close out the requirement", "mark the requirement shipped", "this feature is done, close it out", or "fill the close-out in the PR body". Sets the REQ to shipped in the traceability map, promotes a SPEC § only when the maintainer confirms, and writes the PR body, inside the implementing PR. Not for the drift check (sdd-trace) or review (sdd-review).
argument-hint: "<REQ to close out>"
allowed-tools: Read, Edit, Bash, Glob, Grep
---

# Archive — the SDD close-out, in place

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Close out a finished slice on the branch that implements it. Read `docs/.sdd.yaml` for the traceability map location. Run the gate as `references/sdd-check.md` defines `sdd-check <cmd>`.

The argument is the `REQ` being closed out; given none, take it from the `Implements:` line of the PR body, and stop when there is none: a maintenance-lane change has nothing to close out.

## When to run it

Run this as the last commit before the PR is marked ready, once round 0 of the review ledger has no open blocker. `/sdd-deliver` runs it at that point.

## Preconditions

- The verification command was run on this branch and its output was read — never claim green that was not seen.
- Round 0 of the ledger has no open blocker.

Do not close out unverified work; closing out asserts the slice is done.

## Steps

1. **Spec status** — leave each affected `SPEC §` at `draft` unless the maintainer confirms promotion to `stable` (`references/sdd-methodology.md` §6: promotion freezes the contract). For implementation-aligned work, confirm the § was updated in the same change and is not lagging.
2. **Traceability record** — set the delivered `REQ`'s `implementation` to `shipped` (`references/sdd-methodology.md` §6) and mirror the spec `status` in its `traceability.yaml` record (it takes effect when the PR merges); confirm it lists the landed `packages`, `tests`, and `probes` — a record carries no plan axis and no PR pointer, do not add one. Then run `sdd-check generate` so the index rows and the requirement detail file's status lines pick up the change.
3. **Confirm the gate is clean** — run `sdd-check check`; read the summary line and confirm it reports clean before continuing. When `python3` is unavailable, say the gate did not run and leave the PR-body `sdd-check generate` checkbox unticked.
4. **Commit** — one local commit carrying the status edits, the map and the regenerated blocks, its message citing the `REQ` ids (`references/artefact-prose.md`). Do not push yet.
5. **Full gate** — run `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` on the branch as it now stands and read the output. When it is red, stop with nothing pushed: the remote must never claim a slice done that the gate has not passed.
6. **Push and PR body** — push the branch, then fill the close-out block from the repo's `docs/development-process.md` and write it with the forge CLI (on GitHub, `gh pr edit <PR> --body-file <file>`): the `Lane:` line, the identifiers, the claim line, the task list with its ticks, the review lens, what was verified and what the output said, the close-out checkboxes and the deferred items, with the full gate's output from step 5. That file owns the block; fill it, don't redefine it.
7. **Report** — what was set, and the next action (mark the PR ready).

## Guardrails

- **Cite, don't restate** — the close-out commit and PR body follow `references/artefact-prose.md`.
- **The close-out surfaces:** the record's `implementation: shipped` in `traceability.yaml` (step 2), the PR body (step 6), and a `SPEC §` promotion only when the maintainer confirmed it (step 1). Nothing else is hand-edited at close-out; `generate` rewrites the derived blocks. The plan is a working file on the author's disk: nothing is done to it.
- **`AGENTS.md` capability tables are maintenance-lane work**; update them if something user-facing shipped, in this PR or the next.
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.**

## Reference

- `references/sdd-methodology.md` — §9 the close-out, §13 the two gates.
- `references/sdd-check.md` — the gate invocation, the `check` summary line step 3 confirms, and what `generate` writes.
- `references/artefact-prose.md` — the ledger and the close-out prose.

# Upgrading

## From 0.4.x to 0.5.0

0.5.0 changes the plan lifecycle, the traceability record, the review output, and the descriptor. SemVer 0.x allows breaking changes in a minor release; these are the ones, what you see, and the mechanical fix. Work down the table in order.

| What changed | What you see | Fix |
|---|---|---|
| The descriptor needs an `agents:` block | `/sdd-deliver` or `/sdd-review` stops with "route to `/sdd-scaffold` to fill that block" | Run `/sdd-scaffold`; a top-up run adds the block and touches no other key. Confirm `agents.reviewers` and the code-index line in `docs/ai-workflow.md` § Orchestration. |
| The `plans:` axis is gone from traceability records | A `spec-check` that requires `plans:` fails or reports every record | Delete the `plans:` key from each record in `traceability.yaml`; drop that check from your `spec-check`. |
| `/sdd-archive` no longer moves the plan | Finished plans stay in `docs/plans/` with `status: done` | Nothing to do. Never `git mv` a plan; `/sdd-finalize` deletes finished plans at the next version bump. |
| `docs/plans/archive/` and the plans index are retired | The legacy directory is still in the tree | The first `/sdd-finalize` run sweeps `done` and `abandoned` plans from it and removes the directory once empty. A plan there without a frontmatter `status` stops the sweep; add the line first. |
| `paths.plans_archive` is gone from the descriptor | An unread key in `docs/.sdd.yaml` | `/sdd-finalize` removes the line in the same commit, or delete it by hand. |
| The process-doc templates were rewritten | Your `docs/ai-workflow.md`, `docs/development-process.md`, and `AGENTS.md` still route delivery to a general engineering plugin and describe archive-and-index; the scaffold never overwrites a populated file | Move each file aside, run `/sdd-scaffold`, and merge your local tuning back; or paste § Orchestration, § Review, the lanes, and the PR-body close-out block from the plugin's `references/templates/`. |
| The PR body carries a `Lane:` line | `/sdd-review` falls back to the plan header, and a maintenance PR has none | Add `Lane: full` or `Lane: maintenance — no normative change` to the body, from the close-out block in `docs/development-process.md`. |
| Review output is one ledger comment | A reviewer given the old prompt posts one comment per finding | Paste the block `/sdd-review --panel` prints; do not retype it. |
| `sdd-with-superpowers.md` is removed | Links to it or to `docs/superpowers/` break | Link the router skill's paragraph on the optional general engineering plugin instead. |

Tool grants in `agents/*.md` are Claude Code fields; on Cursor they are contracts the agent bodies state — see the Cursor section of [install.md](install.md#cursor).

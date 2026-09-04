---
name: sdd-finalize
description: This skill should be used when the user asks to "cut the release", "bump the version", "sweep the finished plans", or "clean up docs/plans before the tag". The release-time plan sweep — as the first step of a version bump and before the tag, deletes every plan whose status is `done` or `abandoned`, after checking for inbound links; the first run in a repo also sweeps the legacy `docs/plans/archive/` and its index. Never touches `active` or `postponed` plans. Not for closing out one plan inside its PR (sdd-archive) or for the traceability drift scan (sdd-trace).
argument-hint: "[--dry-run]"
allowed-tools: Read, Edit, Bash, Glob, Grep
---

# Finalize — sweep the finished plans

> **`references/…` paths resolve from the plugin root** (beside `skills/`, two levels up — not under this skill): `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, `../../references/…` relative, or Glob for the installed copy.

Run this as the **first step of a version bump, before the tag**. The deletions ride in the bump commit, so a release tag carries no finished plans and their history is in the commits before it.

## Steps

0. **Read the descriptor.** `docs/.sdd.yaml` → `paths.plans`. No descriptor means the repo is not scaffolded; stop and route to `/sdd-scaffold`.
1. **Confirm the moment.** Confirm the version bump is in progress and the tag has not been created. If the tag for this version already exists, stop — the sweep belongs before the tag, not after it.
2. **Enumerate candidates.** Every file under `paths.plans/**` whose frontmatter `status` is `done` or `abandoned`. Print the list. A plan whose `status` is `active` or `postponed` is never a candidate, whatever its date.
3. **Inbound-link check — before any delete.** Grep the whole documentation root, `docs/**`, plus any directory the descriptor names under `paths.*` that lies outside it, for each candidate's path and basename. If any of those documents still links to a candidate, stop and print the list. The fix is to rewrite the citation to the PR or the `REQ`, then run this again. Never delete a file that is still cited.
4. **First run in this repo.** If `<paths.plans>/archive/` exists, select from it exactly as step 2 does: a file whose frontmatter `status` is `done` or `abandoned`, plus the directory's index file, joins the same candidate list. A file there with any other status, or with no frontmatter, stops the sweep and is named in the report — sitting in an archive directory is not proof that a plan is finished. Run the same inbound-link check over the additions. This step only adds candidates; it deletes nothing. If `docs/.sdd.yaml` still declares `paths.plans_archive`, remove that line in the same commit.
5. **Delete.** `git rm` each candidate — this is the only step that deletes anything. Use `git rm` so the deletion is staged with the bump; git keeps the history and the PR head ref stays fetchable. Remove the legacy archive directory from step 4 in the same commit, once its last file is gone.
6. **Report.** What was deleted, what was kept and why (`active`, `postponed`), and what blocked.

With `--dry-run`, print steps 2–4 and delete nothing.

## Guardrails

- **Never touch an `active` or a `postponed` plan.**
- **Never delete a plan that another document under `docs/**`, or under a `paths.*` directory outside it, still links to.**
- **This is not the close-out.** One plan being finished inside its PR is `/sdd-archive`.
- **The sweep is a deletion, not a move.** There is no archive to move things into any more.

## Reference

- `references/sdd-methodology.md` — §9 the plan lifecycle.
- `references/traceability-schema.md` — §3 the plan frontmatter contract.

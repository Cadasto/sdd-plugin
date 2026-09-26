---
name: sdd-finalize
description: This skill should be used when the user asks to "cut the release", "bump the version", "sweep the finished plans", or "clean up docs/plans before the tag". Deletes every plan whose status is done or abandoned as the first step of a version bump, after an inbound-link check; never touches active or postponed plans. Does not bump the version or create the tag. Not for closing out one plan in its PR (sdd-archive) or the drift scan (sdd-trace).
argument-hint: "[target version] [--dry-run]"
allowed-tools: Read, Edit, Bash, Glob, Grep
---

# Finalize — sweep the finished plans

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Run this as the **first step of a version bump, before the tag**. The deletions ride in the bump commit, so a release tag carries no finished plans and their history is in the commits before it.

## Steps

Run the gate as `references/sdd-check.md` defines `sdd-check <cmd>`.

0. **Read the descriptor.** `docs/.sdd.yaml` → `paths.plans`. No descriptor means the repo is not scaffolded; stop and route to `/sdd-scaffold`.
1. **Confirm the moment.** Take the target version from the argument, or ask for it. Confirm the version bump is in progress; if `git tag -l '<tag>'` lists the tag for that version, stop — the sweep belongs before the tag, not after it.
2. **Enumerate candidates.** Every file under `paths.plans/**`, outside the legacy archive step 3 owns, whose frontmatter `status` is `done` or `abandoned`. A plan whose `status` is `active` or `postponed` is never a candidate, whatever its date.
3. **First run in this repo.** If `<paths.plans>/archive/` exists, select from it exactly as step 2 does: a file whose frontmatter `status` is `done` or `abandoned`, plus the archive index `<paths.plans>/archive/README.md`, joins the same candidate list. A file there with any other status stops the sweep and is named in the report — sitting in an archive directory is not proof that a plan is finished. A file there with no frontmatter `status` but a legacy `**Status:**` line, the form plans took before the plan contract, is read by the table in `references/traceability-schema.md` § Legacy `**Status:**` lines: a word that maps to `done` or `abandoned` joins the candidate list with that line quoted beside it, and the sweep goes ahead only when the maintainer confirms the quoted list; a word that maps to `active` or `postponed`, or maps to nothing, stops the sweep. Any other file with neither stops the sweep. The legacy fallback applies under `<paths.plans>/archive/` only, never to a live plan. The link check in the next step covers these additions. This step only adds candidates; it deletes nothing. If `docs/.sdd.yaml` still declares the retired archive-path key (the plugin's `docs/upgrading.md` lists it), remove that line in the same commit. Print the full candidate list.
4. **Inbound-link check — once, before any delete.** Grep the whole documentation root, `docs/**`, the root `AGENTS.md` and `README.md`, plus any directory the descriptor names under `paths.*` that lies outside `docs/`, for each candidate's path and basename. A link whose source is itself a candidate — the archive index listing the plans beside it, a finished plan citing another — does not count; the source leaves the tree in the same commit. If any other document still links to a candidate, stop and print the list. The fix is to rewrite the citation to the PR or the `REQ`, then run this again. Never delete a file that is still cited.
5. **Delete.** `git rm` each candidate — this is the only step that deletes anything. Use `git rm` so the deletion is staged with the bump; git keeps the history and the PR head ref stays fetchable. Remove the legacy archive directory from step 3 in the same commit, once its last file is gone.
6. **Report.** Run `sdd-check check` and report the `plans` family result (`references/sdd-check.md`); if it is not clean, name the findings and stop before the bump commit. When `python3` is unavailable, say so instead. Then report what was deleted, what was kept and why (`active`, `postponed`), and what blocked.

With `--dry-run`, print steps 2–4 and delete nothing.

## Guardrails

- **Never touch an `active` or a `postponed` plan.**
- **Never delete a plan that another document still links to — under `docs/**`, under a `paths.*` directory outside it, or in the root `AGENTS.md` or `README.md`; a link from a file that leaves in the same sweep does not count.**
- **This is not the close-out.** One plan being finished inside its PR is `/sdd-archive`.
- **The sweep is a deletion, not a move.** Finished plans are deleted, never moved to an archive directory.

## Reference

- `references/sdd-methodology.md` — §9 the plan lifecycle.
- `references/traceability-schema.md` — §3 the plan frontmatter contract.
- `references/sdd-check.md` — the `plans` family step 6 confirms clean.

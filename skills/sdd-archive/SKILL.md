---
name: sdd-archive
description: This skill should be used when the user asks to "close out the plan", "archive the plan", "mark the requirement shipped", or "this feature is done — close it out". The SDD close-out — confirms the document-side Definition of Done (spec status, index, traceability), flips the plan to done and `git mv`s it to `plans/archive/`, and updates AGENTS.md tables if user-facing. Not for merging / PR / branch cleanup (superpowers finishing-a-development-branch); not for running tests (superpowers verification-before-completion) or the drift check (sdd-trace).
argument-hint: "<plan file or REQ to close out>"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Archive — the SDD close-out (the outer loop)

Consolidate a finished feature's delta into the living project memory and keep the active list a true picture of in-flight work. This is the **document/spec** close-out; the **git** close-out (merge / PR / worktree cleanup) is `superpowers:finishing-a-development-branch`, run alongside. Read `docs/.sdd.yaml` for `paths.plans` / `paths.plans_archive`.

## Preconditions

- Tests/build pass — confirmed via `superpowers:verification-before-completion`.
- Traceability is intact — confirmed via `sdd-trace` (drift scan clean).

Do not archive unverified work; archiving asserts the feature is truly done.

## Steps (the document-side Definition of Done)

1. **Spec status** — promote each affected `SPEC §` status if appropriate; for *implementation-aligned* work, confirm the spec § was updated in the same change (not left lagging).
2. **Requirements index** — set each delivered `REQ`'s `implementation` to `shipped`/`landed`.
3. **Traceability** — confirm `traceability.yaml` reflects the landed packages/tests/probes.
4. **Plan** — flip its frontmatter `status: active` → `done`, then `git mv docs/plans/YYYY-MM-DD-<slug>.md docs/plans/archive/` (use `git mv` so history follows). Update the plans index. For explicitly deferred work, use a `postponed/` folder with restore criteria instead.
5. **AGENTS.md** — update its tables if anything user-facing shipped (a capability list, a new command).
6. **Report** what moved and confirm the active list now shows only in-flight work. Then hand off to `superpowers:finishing-a-development-branch` for the merge/PR.

## Guardrails

- **Verify before archive.** Archiving is the last step; if `sdd-trace` shows drift or tests fail, stop and fix first.
- **Use `git mv`** — preserve history; don't delete-and-recreate.
- **Keep the active list honest** — no `done` plan left active; no `shipped` `REQ` left `in_progress`.
- **Consolidate, don't duplicate.** The spec already holds the normative delta (updated during the build); archiving moves the *plan*, it does not re-document behaviour.
- **Stay on the doc side.** Branch merging, PRs, and worktree cleanup are `superpowers:finishing-a-development-branch` — don't reimplement them here.

## Reference

- `references/sdd-methodology.md` — §9 archive-on-completion (the outer loop) & Definition of Done.
- `references/sdd-with-superpowers.md` — how this pairs with branch-finishing.

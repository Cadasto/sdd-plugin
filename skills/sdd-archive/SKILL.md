---
name: sdd-archive
description: This skill should be used when the user asks to "close out the plan", "archive the plan", "mark the requirement shipped", or "this feature is done — close it out". The SDD close-out — confirms the document-side Definition of Done (spec status, index, traceability), flips the plan to done and `git mv`s it to `plans/archive/`, and updates AGENTS.md tables if user-facing. Not for merging / PR / branch cleanup (superpowers finishing-a-development-branch); not for running tests (superpowers verification-before-completion) or the drift check (sdd-trace).
argument-hint: "<plan file or REQ to close out>"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Archive — the SDD close-out (the outer loop)

> **Bundled `references/` is at the plugin root** (beside `skills/`, two levels above this file) — *not* under this skill. Read any `references/…` path as `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or `../../references/…` from this skill's directory, or Glob for the installed `references/…` (host-agnostic).

Consolidate a finished feature's delta into the living project memory and keep the active list a true picture of in-flight work. Document/spec close-out only — git close-out is superpowers' job (`references/sdd-with-superpowers.md`). Read `docs/.sdd.yaml` for `paths.plans` / `paths.plans_archive`.

## When to run it — default: inside the implementing PR

Run this as the **final commit of the implementing branch**, before the PR is finalized, so the plan flip and archive move ride in the **same PR** that lands the code — no follow-up PR or commit. The `git mv` of the plan into `archive/` shows in the diff, which is a feature, not a cost: the PR becomes self-describing. Set `implementation: shipped` in that same commit — it is understood to take effect when the PR merges. (Keeping a separate `landed`-then-`shipped` split is available but usually more bookkeeping than it's worth.)

If a plan was missed and closed out after merge, run it the same way on a small follow-up — `sdd-trace` and the `sdd-traceability-auditor` flag the stale-active-list case so it doesn't get lost.

## Preconditions

- Tests/build pass and traceability is intact **on this branch** — per `references/sdd-with-superpowers.md` (`verification-before-completion` + `sdd-trace` drift scan clean). Verification is on the branch, before the PR merges — not a post-merge step.

Do not archive unverified work; archiving asserts the feature is truly done.

## Steps (the document-side Definition of Done)

1. **Spec status** — promote each affected `SPEC §` status if appropriate; for *implementation-aligned* work, confirm the spec § was updated in the same change (not left lagging).
2. **Requirements index** — set each delivered `REQ`'s `implementation` to `shipped` in this same commit (takes effect on merge; see "When to run it").
3. **Traceability** — confirm `traceability.yaml` reflects the landed packages/tests/probes.
4. **Plan** — flip its frontmatter `status: active` → `done`, then `git mv docs/plans/YYYY-MM-DD-<slug>.md docs/plans/archive/` (use `git mv` so history follows). Update the plans index. For explicitly deferred work, use a `postponed/` folder with restore criteria instead.
5. **AGENTS.md** — update its tables if anything user-facing shipped (a capability list, a new command).
6. **Report** what moved and confirm the active list now shows only in-flight work. Hand off git close-out per `references/sdd-with-superpowers.md`.

## Guardrails

- **Verify before archive.** Archiving is the last step *on the branch*; if `sdd-trace` shows drift or tests fail, stop and fix first.
- **The archive commit and PR follow prose economy.** Cite the `REQ`/plan; don't restate the spec or re-narrate the change — `references/artefact-prose.md`.
- **Use `git mv`** — preserve history; don't delete-and-recreate.
- **Keep the active list honest** — no `done` plan left active; no `shipped` `REQ` left `in_progress`.
- **Consolidate, don't duplicate.** The spec already holds the normative delta (updated during the build); archiving moves the *plan*, it does not re-document behaviour.
- **Stay on the doc side.** Branch merging, PRs, and worktree cleanup are superpowers' job — see `references/sdd-with-superpowers.md`.

## Reference

- `references/sdd-methodology.md` — §9 archive-on-completion (the outer loop) & Definition of Done.
- `references/sdd-with-superpowers.md` — how this pairs with branch-finishing.
- `references/artefact-prose.md` — one home per fact (the archive commit / PR cite, don't restate).

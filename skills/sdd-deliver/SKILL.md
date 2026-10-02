---
name: sdd-deliver
description: This skill should be used when the user asks to "deliver REQ-…", "run the delivery pipeline", "take this REQ to a draft PR", "build this requirement end to end", "resume the delivery of PR N", or "close out the requirement and write the PR body" (`--close-out`). Drives one change from the dispatch gate through workers, gates and the first review pass to a ready pull request, and closes it out. Not for authoring documents (sdd-specify), a standalone review (sdd-review), or working findings (sdd-triage).
argument-hint: "<REQ-id, task in words, plan path, or PR number to resume> [--lane full|maintenance] [--close-out]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Deliver — one change, from the dispatch gate to a ready pull request

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` and `tools/…` resolve from it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

The procedure and its parameters come from the descriptor and this file, never from session memory. Run as the orchestrator, on the strongest model available: hold the judgement, delegate the bounded work. The argument is the `REQ`, a task in words, a plan's path, or — to resume — the PR number; `--lane` overrides step 1, and `--close-out` runs step 10 alone on an existing PR.

## Steps

0. **Read `docs/.sdd.yaml`:** `profile`, `paths.*`, `forge`, the build targets, the whole `agents:` block. No descriptor, or no `agents:` block: route to `/sdd-scaffold` and stop before any dispatch.
1. **Decide the lane — formal profile only.** Full or maintenance (methodology §12, or `--lane`): does the change alter a normative statement — acceptance criteria, a `SPEC §` behaviour, a public API shape, an error contract? Record it, and step 2's result, in the delivery notes, `<git-common-dir>/sdd/deliver/<branch-slug>.md`, which every worktree sees: it drives the gate, the reviewers, the close-out and the PR body's `Lane:` line.
2. **The dispatch gate.** Formal profile: the five preconditions of methodology §9 on the full lane; on the maintenance lane, two checks — the change alters no normative statement (the ratchet of §12: a task that needs a `REQ`, `SPEC §` or `ADR` edit is full lane whatever it was called) and the verification commands are known. Informative profile: the task is clear, the verification command is known, and the constitution sentences the task touches (if any) are quoted into the briefs. An unmet check stops the dispatch, named; route a missing `REQ`/`SPEC §`/`ADR` to `/sdd-specify`. Nothing else blocks the start.
3. **Branch; plan if the host plans.** Create or check out the feature branch. A plan (a planning skill's, a file under `/.sdd/`, or a committed one marked `kind: plan`) is the orchestrator's own; given one, quote each task verbatim into its brief, never retyped or narrowed. Nothing else reads it. On the maintenance lane and the informative profile a task list in the session is enough. Read `docs/backlog.md` when it exists: an item whose path a task's `Files` touch joins that task, quoted into the brief's `Finding` as a lead to verify first (`references/review.md` § The backlog).
4. **Fan out** one `sdd-implementer` per task: independent tasks in parallel up to `agents.max_parallel_workers`, each parallel mutating worker on its own branch `<branch>--<task>` in its own worktree when `agents.worktree_per_worker` is true (the orchestrator creates both, `git worktree add -b <branch>--<task> <path>`), sequential tasks on the branch itself, `agents.worker_model` passed as the model override **on the dispatch** (none for `inherit`) and never a cheaper one: workers write the code. Fill every field of `references/templates/brief.md`: `Clauses` quoted, `Reproduce` for a bug fix, `agents.worker_skills`, the code index from `docs/ai-workflow.md` § Orchestration. Add each task's branch, worktree and, later, its gate verdict to the notes. A task that needs the orchestrator's whole context is done in-session, and the PR body says so and why. While workers run, the spec holds still: an amendment a gate finds waits for integration or goes through `/sdd-specify` between waves, no file in a running worker's `Files` is edited, and a task whose scope grows is a question to the maintainer.
5. **Gate each task** per `agents.task_review`: `on` always, `off` never, `lane` on for the full lane and the informative profile, off for maintenance. The gate dispatches `agents.reviewers` (in map form, those whose patterns match the task's `Files`; none matching is unconfigured) with `references/templates/task-review.md` filled for the task: its brief, its diff, the scope test; a small, mechanical task's review may take a cheaper model. Its findings go back to the worker in-session, never to the findings file or the pull request. An empty `agents.reviewers` with the gate on is unconfigured, not clean: say so and ask before continuing.
6. **Account for completion.** A worker that died is re-dispatched, or the gap is named. Triage each worker's en-route findings: in scope, a task; out of scope, `sdd-pr add suggestion <path[:line]> "<sentence>" --by <worker>`. A task is done when its verification ran and its output was read.
7. **Integrate, gate, then the first review pass.** Merge each worker branch in dependency order, after a trial merge in a throwaway worktree; run the generator once and commit what it wrote; then `git worktree remove` each worker's worktree and the trial merge's, `git worktree prune`, and `git branch -d` each worker branch (`sdd-pr status` names any left). Run the full gate — `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` — on the integrated branch and read the output (the `generated` family fails a stale index). On the informative profile, first **reconcile the documents**: every `docs/` section describing what the change altered is updated in this branch; the constitution only through `/sdd-specify`. Then run `/sdd-review --lane <lane>` (no `--lane` on the informative profile) — the one pass before the maintainer's review (`references/review.md` § Passes) — and fix its open lines with `/sdd-triage`, which re-reviews nothing before the maintainer has reviewed.
8. **Push, and open the draft pull request** with the repository's forge CLI; the body follows `docs/development-process.md` § The PR body (one sentence of Summary until close-out), or, when that section is missing, the repository's PR template, which the hand-back names. Then `sdd-pr post` mirrors anything still open.
9. **The maintainer's review.** Stop and wait; never mark the PR ready on the orchestrator's own judgement. Inline comments come in with `sdd-pr pull`; a conversation comment is an instruction. Work them with `/sdd-triage`, which may run the one pass over the fixes.
10. **Close out and mark ready.** When `sdd-pr status` shows nothing open:
    - formal profile — set the delivered `REQ`'s `implementation: shipped` in the traceability map with its landed `packages`, `tests` and `probes`, mirror the spec status (promote a `SPEC §` to `stable` only when the maintainer confirms: promotion freezes the contract), run `sdd-check generate`, and commit the map, the status edits and the regenerated files by explicit path, citing the `REQ`;
    - both profiles — ask the maintainer once: carry the suggestions left to the backlog (`sdd-pr flip --suggestions --carry`) or drop them (`--dropped`). Delete the backlog lines this branch fixed or found stale, and commit `docs/backlog.md` by path;
    - both profiles — run the full gate on the branch as it stands and read it; when it is red, stop with nothing pushed. Write the PR body from `docs/development-process.md` § The PR body in full, push, mark ready. The maintainer merges.
11. **Print the panel prompts** with `/sdd-review --panel` for a person to paste to reviewers outside the repository, and stop.

**Resuming.** Resume with the PR number, passed as `--pr N` to every `sdd-pr` call, or on the branch before a pull request exists: the delivery notes, `sdd-pr status` (which lists worker branches not yet integrated), the findings file and the PR body are the state; a resume re-checks step 2 before it dispatches again. Two sessions on one branch take turns on one checkout. Re-enter at the first step not yet done.

## Guardrails

- **The orchestrator writes no product code, except a task that cannot be made self-contained, named in the PR body.**
- **Workers never spawn workers.**
- **Deterministic fan-out through the host's Workflow tool (Claude Code only) is explicit opt-in: ask first; otherwise dispatch sequentially.**
- **Never hand-edit a generated block.**

## Reference

- `references/sdd-methodology.md` — §1a the profiles, §9 the dispatch preconditions and the close-out, §12 the lanes, §13 the merge gate.
- `references/review.md` — the findings file, the mirror and `sdd-pr` (§ The tool).
- `references/sdd-check.md` — what `spec_check_target` runs and what `generate` writes.
- `references/traceability-schema.md` §1 — the `agents:` block this skill reads.
- `references/templates/brief.md` — the worker brief this skill fills per task; `references/templates/task-review.md` — the per-task review.
- The repo's own `docs/ai-workflow.md` (§ Orchestration, § Review) and `docs/development-process.md` (§ The PR body), which it may have tuned: follow them, not a copy retyped here.

---
name: sdd-deliver
description: This skill should be used when the user asks to "deliver REQ-…", "run the delivery pipeline", "take this REQ to a draft PR", "build this requirement end to end", "resume the delivery of PR N", or "close out the requirement and write the PR body" (`--close-out`). Drives one change from the dispatch gate through workers, gates and the first review pass to a ready pull request, and closes it out. Not for authoring documents (sdd-specify), a standalone review (sdd-review), or working findings (sdd-triage).
argument-hint: "<REQ-id, task in words, or PR number to resume> [--lane full|maintenance] [--close-out]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Deliver — one change, from the dispatch gate to a ready pull request

> `references/…` and `tools/…` resolve from the plugin root: `${CLAUDE_PLUGIN_ROOT}/…` on Claude Code, or Glob for the installed copy. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

The procedure and its parameters come from the descriptor and this file, never from session memory. Run as the orchestrator, on the strongest model available: hold the judgement, delegate the bounded work. The argument is the `REQ`, a task in words, or — to resume — the PR number; `--lane` overrides step 1, and `--close-out` runs step 10 alone on an existing PR.

## Steps

0. **Read `docs/.sdd.yaml`:** `profile`, `paths.*`, `forge`, the build targets, the whole `agents:` block. No descriptor, or no `agents:` block: route to `/sdd-scaffold` and stop before any dispatch.
1. **Decide the lane — formal profile only.** Full or maintenance (methodology §12, or `--lane`): does the change alter a normative statement — acceptance criteria, a `SPEC §` behaviour, a public API shape, an error contract? Record it: it drives the gate, the reviewers, the close-out and the PR body's `Lane:` line.
2. **The dispatch gate.** Formal profile: the five preconditions of methodology §9 on the full lane; on the maintenance lane, two checks — the change alters no normative statement (the ratchet of §12: a task that needs a `REQ`, `SPEC §` or `ADR` edit is full lane whatever it was called) and the verification commands are known. Informative profile: the task is clear, the verification command is known, and the constitution sentences the task touches (if any) are quoted into the briefs. An unmet check stops the dispatch, named; route a missing `REQ`/`SPEC §`/`ADR` to `/sdd-specify`. Nothing else blocks the start.
3. **Branch; plan if the host plans.** Create or check out the feature branch. Any plan (a planning skill, a scratch file under `.sdd/`) is the orchestrator's own: the plugin reads nothing from it, and no plan is committed or placed under `docs/`. On the maintenance lane and the informative profile a task list in the session is enough.
4. **Fan out** one `sdd-implementer` per task: independent tasks in parallel up to `agents.max_parallel_workers`, each parallel mutating worker in its own worktree when `agents.worktree_per_worker` is true, `agents.worker_model` passed as the model override **on the dispatch** (none for `inherit`). Fill every field of `references/templates/brief.md`: `Clauses` quoted, `Reproduce` for a bug fix, `agents.worker_skills`, the code index from `docs/ai-workflow.md` § Orchestration. A task that needs the orchestrator's whole context is done in-session, and the PR body says so and why.
5. **Gate each task** per `agents.task_review`: `on` always, `off` never, `lane` on for the full lane and the informative profile, off for maintenance. The gate dispatches `agents.reviewers` with the brief, plus one scope test: behaviour no binding sentence states is a finding. Its findings go back to the worker in-session, never to the findings file or the pull request. An empty `agents.reviewers` with the gate on is unconfigured, not clean: say so and ask before continuing.
6. **Account for completion.** A worker that died is re-dispatched, or the gap is named. Triage each worker's en-route findings: in scope, a task; out of scope, one suggestion line in the findings file. A task is done when its verification ran and its output was read.
7. **The integration gate, then the first review pass.** Run the full gate — `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` — on the integrated branch and read the output (the `generated` family fails a stale index). On the informative profile, first **reconcile the documents**: every `docs/` section describing what the change altered is updated in this branch; the constitution only through `/sdd-specify`. Then run `/sdd-review --lane <lane>` (no `--lane` on the informative profile) — the one pass before the maintainer's review (`references/review.md` § Passes) — and fix its open lines with `/sdd-triage`, which re-reviews nothing before the maintainer has reviewed.
8. **Push, and open the draft pull request** with the repository's forge CLI; the body follows `docs/development-process.md` § The PR body (one sentence of Summary until close-out). Then `sdd-pr post` mirrors anything still open.
9. **The maintainer's review.** Stop and wait; never mark the PR ready on the orchestrator's own judgement. Inline comments come in with `sdd-pr pull`; a conversation comment is an instruction. Work them with `/sdd-triage`, which may run the one pass over the fixes.
10. **Close out and mark ready** (also `/sdd-deliver <PR> --close-out`). When `sdd-pr status` shows nothing open:
    - formal profile — set the delivered `REQ`'s `implementation: shipped` in the traceability map with its landed `packages`, `tests` and `probes`, mirror the spec status (promote a `SPEC §` to `stable` only when the maintainer confirms: promotion freezes the contract), run `sdd-check generate`, and commit the map, the status edits and the regenerated files by explicit path, citing the `REQ`;
    - both profiles — run the full gate on the branch as it stands and read it; when it is red, stop with nothing pushed. Write the PR body from `docs/development-process.md` § The PR body in full, push, run `sdd-pr status --write-body` (the review state for the head as it stands), mark ready. The maintainer merges.
11. **Print the panel prompts** with `/sdd-review --panel` for a person to paste to reviewers outside the repository, and stop.

**Resuming.** Run this skill against the PR number, and pass it on as `--pr N`: the findings file, `sdd-pr status` and the PR body are the state; before a pull request exists, the findings file and the orchestrator's working notes. Two sessions on one branch take turns on one checkout. Re-enter at the first step not yet done.

## Guardrails

- **The orchestrator writes no product code, except a task that cannot be made self-contained, named in the PR body.**
- **Workers never spawn workers.**
- **Deterministic fan-out through the host's Workflow tool (Claude Code only) is explicit opt-in: ask first; otherwise dispatch sequentially.**
- **Never claim a build green whose output was not run and read, and never mark a PR ready without the full gate's output from the branch as it stands.**
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.**
- **Findings are `/sdd-triage`'s job; the per-task gate's findings never leave the session.**

## Reference

- `references/sdd-methodology.md` — §1a the profiles, §9 the dispatch preconditions and the close-out, §12 the lanes, §13 the merge gate.
- `references/review.md` — the findings file and the mirror; `tools/sdd-pr.py` — `status`, `post`, `pull`.
- `references/sdd-check.md` — what `spec_check_target` runs and what `generate` writes.
- `references/traceability-schema.md` §1 — the `agents:` block this skill reads.
- `references/templates/brief.md` — the worker brief this skill fills per task.
- The skills `/sdd-review` (review passes and `--panel`) and `/sdd-triage` (the open findings).
- The repo's own `docs/ai-workflow.md` (§ Orchestration, § Review) and `docs/development-process.md` (§ The PR body), which it may have tuned: follow them, not a copy retyped here.
- The agent `sdd-implementer` — the worker this skill briefs and dispatches.

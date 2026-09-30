---
name: sdd-deliver
description: This skill should be used when the user asks to "deliver REQ-…", "run the delivery pipeline", "take this REQ to a draft PR", "build this requirement end to end", "resume the delivery of PR N", or "close out the requirement and write the PR body" (`--close-out`). Drives one REQ, maintenance task or informative-profile change from the dispatch gate through workers, gates and the first review pass to a ready pull request, and closes it out. Not for authoring the REQ or spec (sdd-specify), a standalone review (sdd-review), or working review findings (sdd-triage).
argument-hint: "<REQ-id, task in words, or PR number to resume> [--lane full|maintenance] [--close-out]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Deliver — one change, from the dispatch gate to a ready pull request

> `references/…` and `tools/…` resolve from the plugin root: `${CLAUDE_PLUGIN_ROOT}/…` on Claude Code, or Glob for the installed copy. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first — the procedure and its parameters come from the descriptor and this file, never from session memory. Run as the orchestrator, on the strongest model available: hold the judgement, delegate the bounded work.

The argument is the `REQ`, a task in words, or — to resume — the PR number. `--lane` overrides the lane test in step 1; `--close-out` runs step 10 alone on an existing PR.

## Steps

0. **Read the descriptor.** `profile`, `paths.*`, `forge`, the build targets, and the whole `agents:` block. No descriptor means the repo is not scaffolded — route to `/sdd-scaffold` and stop. A descriptor with no `agents:` block cannot drive a delivery: route to `/sdd-scaffold` to fill it before any dispatch.
1. **Decide the lane — formal profile only.** Full or maintenance, per `references/sdd-methodology.md` §12, or from `--lane`: does the change alter any normative statement — a `REQ`'s acceptance criteria, a `SPEC §` behaviour, a public API shape, an error contract? Record it; it drives the gate, the reviewers, the close-out and the PR body's `Lane:` line.
2. **The dispatch gate.** Formal profile: the five preconditions of methodology §9 on the full lane; on the maintenance lane, two checks — the change alters no normative statement (the ratchet of §12: a task that needs a `REQ`, `SPEC §` or `ADR` edit is full lane whatever it was called) and the verification commands are known. Informative profile: the task is clear, the verification command is known, and the constitution sentences the task touches (if any) are quoted into the briefs. An unmet check stops the dispatch, named; route a missing `REQ`/`SPEC §`/`ADR` to `/sdd-specify`. Nothing else blocks the start.
3. **The plan, if you want one.** Create or check out the feature branch. Plan the way your host plans (a planning skill, a scratch file under `.sdd/`); the plugin reads nothing from it and no plan is ever committed or placed under `docs/`. On the maintenance lane and on the informative profile a task list in the session is enough.
4. **Fan out.** Dispatch one `sdd-implementer` per task. Run independent tasks in parallel up to `agents.max_parallel_workers`; give each parallel, mutating worker its own worktree when `agents.worktree_per_worker` is true. Pass `agents.worker_model` as the model override **on the dispatch** (none for `inherit`). Write each brief from `references/templates/brief.md` and fill every field: `Clauses` quoted, `Reproduce` for a bug fix, the skills from `agents.worker_skills`, the code index named in `docs/ai-workflow.md` § Orchestration. A task that needs the orchestrator's whole context is done in-session, and the PR body says so and why.
5. **Gate each task.** Follow `agents.task_review`: `on` always, `off` never, `lane` means on for the full lane and off for the maintenance lane (on for the informative profile). The gate dispatches the reviewers in `agents.reviewers` with the brief attached, plus one scope test: behaviour that no binding sentence states is a finding. Its findings go back to the worker in-session; nothing from the per-task gate reaches the findings file or the pull request. An empty `agents.reviewers` with the gate on is an unconfigured gate, not a clean one: say so and ask before continuing.
6. **Account for completion.** A worker that died is re-dispatched, or the gap is named. Triage each worker's en-route findings: in scope, it becomes a task; out of scope, one suggestion line in the findings file. A task is done when its verification ran and its output was read.
7. **The integration gate, then the first review pass.** Run the full gate — `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` — on the integrated branch and read the output; `spec_check_target` includes the `generated` family, so a stale index fails here (`references/sdd-check.md`). On the informative profile, first **reconcile the documents**: every section of `docs/` that describes what the change altered is updated in this branch, and the constitution is amended only through `/sdd-specify`. Then run `/sdd-review --lane <lane>` and work its open lines with `/sdd-triage` until `sdd-pr status` shows none open.
8. **Open the draft pull request** with the forge CLI the repository uses. The body follows `docs/development-process.md` § The PR body; one sentence of Summary is enough until close-out. Then `sdd-pr post` mirrors anything still open.
9. **The maintainer's review.** Stop and wait; do not mark the PR ready on your own judgement. The maintainer's inline comments come in with `sdd-pr pull`; a conversation comment is an instruction. Work them with `/sdd-triage`.
10. **Close out and mark ready** (also `/sdd-deliver <PR> --close-out`). When `sdd-pr status` shows nothing open:
    - formal profile — set the delivered `REQ`'s `implementation: shipped` in the traceability map with its landed `packages`, `tests` and `probes`, mirror the spec status (promote a `SPEC §` to `stable` only when the maintainer confirms: promotion freezes the contract), run `sdd-check generate`, and commit, citing the `REQ`;
    - both profiles — run the full gate on the branch as it stands and read it; when it is red, stop with nothing pushed. Write the PR body from `docs/development-process.md` § The PR body in full, push, mark ready. Nothing else is required; the maintainer merges.
11. **Print the panel prompts.** Run `/sdd-review --panel`: print the blocks for a person to paste to reviewers outside the repository, and stop.

**Resuming.** Run this skill against the PR number: the findings file, `sdd-pr status` and the PR body are the state. Before a pull request exists, the findings file and your own working notes are. Two sessions on one branch: each gets its own worktree. Re-enter at the first step not yet done.

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

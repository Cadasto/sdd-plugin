---
name: sdd-deliver
description: This skill should be used when the user asks to "deliver REQ-…", "run the delivery pipeline", "take this REQ to a draft PR", or "plan and build this requirement end to end". Drives one REQ or plan from the dispatch preconditions through workers, gates, and round 0 to a ready pull request. Not for work with no REQ or plan behind it, or for working a review round (sdd-triage).
argument-hint: "<REQ-id, plan file, or PR number to resume> [--lane full|maintenance]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Deliver — one REQ or plan, from preconditions to a ready pull request

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Drive one `REQ` or one plan from preconditions to a ready pull request. Read `docs/.sdd.yaml` first — the procedure and its parameters come from the descriptor and this file, never from session memory.

You are the orchestrator. Run on the strongest model available; hold the judgement and delegate the bounded work.

The argument is the `REQ`, the plan file, or — to pick an interrupted delivery back up — the PR number. `--lane` overrides the lane test in step 2.

## Steps

0. **Read the descriptor.** `paths.*`, the build targets, and the whole `agents:` block. No descriptor means the repo is not scaffolded — route to `/sdd-scaffold` and stop. A descriptor with no `agents:` block is a repo scaffolded before delivery existed: route to `/sdd-scaffold` to fill that block before any dispatch.
1. **The dispatch gate.** Confirm all five preconditions before briefing the first worker: a `REQ` with acceptance criteria exists; the affected `SPEC §` exist or a new § is called out; any needed `ADR` is `Accepted`; the negative space is cited from the `REQ` acceptance criteria and the `SPEC §` that owns the failure behaviour; the verification commands are known. If one is unmet, stop and name it — do not dispatch, and do not write the missing document yourself without saying so. (Methodology §9 owns the list. Route a missing `REQ`/`SPEC §`/`ADR` to `/sdd-specify`.)
2. **Decide the lane.** Full or maintenance, per `references/sdd-methodology.md` §12, or from `--lane`. Record it; it drives the per-task gate, the reviewers, and the PR-body line.
3. **The plan, on the branch.** Create or check out the feature branch, write the plan to `<paths.plans>/YYYY-MM-DD-<slug>.md` from the plan template with `status: active`, and commit it. Fill the plan header's `Lane:` line with the lane decided in step 2 — round 0 runs before any PR exists, so `/sdd-review` takes the lane from the plan header. The plan travels with the branch and its worktrees, so every worker and reviewer reads the same file. (The template is `references/templates/plan.md`.) A plan introduces no normative statement. If writing it makes you want to state a rule, that rule belongs in a spec and the dispatch gate was not actually met.
4. **Fan out.** Dispatch one `sdd-implementer` per task. Run independent tasks in parallel up to `agents.max_parallel_workers`; give each parallel, mutating worker its own worktree when `agents.worktree_per_worker` is true. Sequential work stays on the branch. Pass `agents.worker_model` as the model override **on the dispatch**. Never try to edit an agent file — plugin agents live in a read-only install cache. Every brief carries six things: the task; the `REQ`/`SPEC §` it cites; the files it may touch; the verification command; the instruction to end with an `En-route findings` section; the instruction not to spawn subagents. Name any skills from `agents.worker_skills` in the brief itself, and the code index that `docs/ai-workflow.md` § Orchestration names, if any — the worker inherits the host's MCP tools and queries the one the brief names. A task that needs your whole context to make sense is not delegated: do it in-session and record in the PR body that you did, and why it could not be made self-contained.
5. **Gate each task, per lane.** Follow `agents.task_review`: `on` always, `off` never, `lane` means on for the full lane and off for the maintenance lane. The gate dispatches the reviewers named in `agents.reviewers` with the brief attached, plus one scope test: behaviour that no `REQ` or `SPEC §` states is a finding. An empty `agents.reviewers` with the gate on is an unconfigured gate, not a clean one: write `per-task gate unconfigured — agents.reviewers is empty` into the plan's Notes and ask before continuing.
6. **Account for completion.** A worker that died is re-dispatched, or the gap is written into the plan's Notes. A task is not done because a dispatch ended. Tick a task in the plan only after its verification command ran and its output was read.
7. **Round 0, in the branch.** Run `/sdd-review` on the branch. Its findings are **round 0** of the ledger. Fix the blockers in the branch before the draft PR opens.
8. **Open the draft PR.** Open it as a draft (`gh pr create --draft`) — a draft requests no reviewers, so it publishes nothing, and it gives every later agent the whole computable substrate: inline anchors, threads with resolve state, and `gh` access. Fill the PR body from the repo's `docs/development-process.md` close-out block, including the `Lane:` line and the **claim line** naming the session and worktree that own this branch. A session that finds a claim it did not make stops and asks. Post round 0 as the ledger comment.
9. **The maintainer's review of the draft appends to round 0.** Stop here and wait. Do not mark the PR ready on your own judgement. Work those findings with `/sdd-triage` in the branch — each fix briefed to an `sdd-implementer` worker like any other task — then return to step 10.
10. **Close out and mark ready.** When round 0 has no open blocker, run `/sdd-archive` — it flips the plan to `status: done` in place, sets the `SPEC §` and `REQ` statuses and the traceability map, and completes the PR body — then mark the PR ready (`gh pr ready`). Marking ready requires that round 0's completion-accounting line names the maintainer's review among the reporters. If it does not, stop and ask — a resumed delivery must not treat its own clean self-review as a clean round 0.
11. **Print the panel prompts.** Run `/sdd-review <PR> --panel`. Nothing in the repository can start reviewers that run outside it. Print the blocks for a person to paste, and stop.

**Resuming.** To resume an interrupted delivery, run this skill against the PR number: the draft PR body plus the plan file on the branch is the whole state.

## Guardrails

- **The orchestrator does not write product code, except the one task that cannot be made self-contained — and that exception is stated in the PR body.**
- **Workers never spawn workers.**
- **Deterministic fan-out through the harness's Workflow tool is explicit opt-in: ask before using it, and fall back to sequential dispatch otherwise.**
- **Never claim a build is green you did not run and read.**
- **Working findings posted on the PR — the maintainer's round-0 review and every later round — is `/sdd-triage`'s job, not this skill's; the in-branch fix wave of step 7 happens before any PR exists and is this skill's own work.**

## Reference

- `references/sdd-methodology.md` — §9 the dispatch preconditions and the close-out surfaces, §12 the two lanes, §13 the two gates.
- `references/traceability-schema.md` §1 — the `agents:` block this skill reads.
- `references/artefact-prose.md` — the findings ledger and what the PR body carries.
- The skills `/sdd-review` (round 0 and `--panel`), `/sdd-archive` (close-out), `/sdd-triage` (findings posted on the PR, round 0 onward), `/sdd-finalize` (the release sweep).
- The consuming repo's `docs/ai-workflow.md` § Orchestration and § Review — the repository's own copy of the orchestration rules and the review-request block, which it may have tuned. Follow that copy, not a version retyped here.
- The agent `sdd-implementer` — the worker this skill briefs and dispatches.

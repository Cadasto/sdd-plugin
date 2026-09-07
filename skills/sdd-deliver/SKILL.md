---
name: sdd-deliver
description: This skill should be used when the user asks to "deliver REQ-…", "run the delivery pipeline", "take this REQ to a draft PR", or "plan and build this requirement end to end". Drives one REQ, plan, or maintenance task from the dispatch preconditions through workers, gates, and round 0 to a ready pull request, on either lane. Not for working a review round (sdd-triage) or for authoring the REQ or spec it needs (sdd-specify).
argument-hint: "<REQ-id, plan file, maintenance task, or PR number to resume> [--lane full|maintenance]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Deliver — one REQ or plan, from preconditions to a ready pull request

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Drive one `REQ` or one plan from preconditions to a ready pull request. Read `docs/.sdd.yaml` first — the procedure and its parameters come from the descriptor and this file, never from session memory.

Run as the orchestrator, on the strongest model available: hold the judgement and delegate the bounded work.

The argument is the `REQ`, the plan file, a maintenance task in words, or — to pick an interrupted delivery back up — the PR number. `--lane` overrides the lane test in step 1.

## Steps

0. **Read the descriptor.** `paths.*`, the build targets, and the whole `agents:` block. No descriptor means the repo is not scaffolded — route to `/sdd-scaffold` and stop. A descriptor with no `agents:` block cannot drive a delivery: route to `/sdd-scaffold` to fill that block before any dispatch.
1. **Decide the lane.** Full or maintenance, per `references/sdd-methodology.md` §12, or from `--lane`: does the change alter any normative statement — a `REQ`'s acceptance criteria, a `SPEC §` behaviour, a public API shape, an error contract? Record it; it drives the gate, the plan, the reviewers, the close-out, and the PR-body line.
2. **The dispatch gate.** On the **full lane**, confirm all five preconditions before briefing the first worker: a `REQ` with acceptance criteria exists; the affected `SPEC §` exist or a new § is called out; any needed `ADR` is `Accepted`; the negative space is cited from the `REQ` acceptance criteria and the `SPEC §` that owns the failure behaviour; the verification commands are known. If one is unmet, stop and name it — do not dispatch, and do not write the missing document silently. (Methodology §9 owns the list. Route a missing `REQ`/`SPEC §`/`ADR` to `/sdd-specify`.) On the **maintenance lane** the gate is two checks: the change alters no normative statement — the ratchet of §12, so a task that needs a `REQ`, `SPEC §`, or `ADR` edit is full lane whatever it was called — and the verification commands are known.
3. **The plan, on the branch.** Create or check out the feature branch. On the full lane, write the plan to `<paths.plans>/YYYY-MM-DD-<slug>.md` from the plan template with `status: active`, and commit it. Fill the plan header's `Lane:` line with the lane decided in step 1 — round 0 runs before any PR exists, so `/sdd-review` takes the lane from the plan header. On the maintenance lane the plan is optional and is not committed: hold the task list in the session, then in the PR body once the draft exists. On the full lane the plan travels with the branch and its worktrees, so every worker and reviewer reads the same file. (The template is `references/templates/plan.md`.) A plan introduces no normative statement. If writing it calls for stating a rule, that rule belongs in a spec and the dispatch gate was not actually met.
4. **Fan out.** Dispatch one `sdd-implementer` per task. Run independent tasks in parallel up to `agents.max_parallel_workers`; give each parallel, mutating worker its own worktree when `agents.worktree_per_worker` is true. Sequential work stays on the branch. Pass `agents.worker_model` as the model override **on the dispatch** — no override when it is `inherit`; plugin agent files are read-only at install, so the model is never set by editing one. Write each brief from `references/templates/brief.md` and fill every field — the skills from `agents.worker_skills` and the code index named in `docs/ai-workflow.md` § Orchestration have their own slots. On the maintenance lane the brief's `Cites` field names the `SPEC §` whose behaviour the task must leave unchanged, or `maintenance — no normative change` when none applies. A task that needs the orchestrator's whole context to make sense is not delegated: do it in-session and record in the PR body that it was, and why it could not be made self-contained.
5. **Gate each task, per lane.** Follow `agents.task_review`: `on` always, `off` never, `lane` means on for the full lane and off for the maintenance lane. The gate dispatches the reviewers named in `agents.reviewers` with the brief attached, plus one scope test: behaviour that no `REQ` or `SPEC §` states is a finding. An empty `agents.reviewers` with the gate on is an unconfigured gate, not a clean one: write `per-task gate unconfigured — agents.reviewers is empty` into the plan's Notes — on the maintenance lane, into the task list kept for the PR body — and ask before continuing.
6. **Account for completion.** A worker that died is re-dispatched, or the gap is written into the plan's Notes — on the maintenance lane, into the task list kept for the PR body. A task is not done because a dispatch ended. Tick a task only after its verification command ran and its output was read.
7. **The integration gate, then round 0, in the branch.** Run the full gate the descriptor names — `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` — on the integrated branch and read the output; per-task verification in step 6 is not the full gate. Then run `/sdd-review` on the branch, passing `--lane` with the lane from step 1 — before the draft PR there is no `Lane:` line, and on the maintenance lane no plan header either. Its findings are **round 0** of the ledger. Fix the blockers in the branch before the draft PR opens.
8. **Open the draft PR.** Open it as a draft with the forge CLI (on GitHub, `gh pr create --draft`) — a draft requests no reviewers, so it publishes nothing, and it gives every later agent the whole computable substrate: inline anchors, threads with resolve state, and `gh` access. Fill the PR body from the repo's `docs/development-process.md` close-out block, including the `Lane:` line and the **claim line** naming the session and worktree that own this branch; on the maintenance lane the body is that line, the claim line, and the gate output. A session that finds a claim it did not make stops and asks. Post round 0 as the ledger comment.
9. **The maintainer's review of the draft appends to round 0.** Stop here and wait. Do not mark the PR ready on the orchestrator's own judgement. Work those findings with `/sdd-triage` in the branch — each fix briefed to an `sdd-implementer` worker like any other task — then return to step 10.
10. **Close out and mark ready.** When round 0 has no open blocker, run the full gate again on the branch as it stands after triage and read the output. On the full lane, run `/sdd-archive` — it flips the plan to `status: done` in place, sets the `SPEC §` and `REQ` statuses and the traceability map, and completes the PR body. On the maintenance lane there is nothing to flip and `/sdd-archive` is not run; the PR body carries `Lane: maintenance — no normative change` and the gate output. Then mark the PR ready (on GitHub, `gh pr ready`). Marking ready requires that round 0's completion-accounting line names the maintainer's review among the reporters. If it does not, stop and ask — a resumed delivery must not treat its own clean self-review as a clean round 0. When `agents.reviewers` is empty, that review is the whole panel: round 0 opened as `Dispatched: none` and is clean once the maintainer's review is recorded with no open blocker.
11. **Print the panel prompts.** Run `/sdd-review <PR> --panel`. Nothing in the repository can start reviewers that run outside it. Print the blocks for a person to paste, and stop.

**Resuming.** To resume an interrupted delivery, run this skill against the PR number: the draft PR body plus, on the full lane, the plan file on the branch is the whole state; a maintenance-lane delivery resumes from the PR body alone.

## Guardrails

- **The orchestrator does not write product code, except the one task that cannot be made self-contained — and that exception is stated in the PR body.**
- **Workers never spawn workers.**
- **Deterministic fan-out through the host's Workflow tool (Claude Code only) is explicit opt-in: ask before using it, and fall back to sequential dispatch otherwise.**
- **Never claim a build is green whose output was not run and read, and never mark a PR ready without the full gate's output from the branch as it stands.**
- **Working findings posted on the PR — the maintainer's round-0 review and every later round — is `/sdd-triage`'s job, not this skill's; the in-branch fix wave of step 7 happens before any PR exists and is this skill's own work.**

## Reference

- `references/sdd-methodology.md` — §9 the dispatch preconditions and the close-out surfaces, §12 the two lanes, §13 the two gates.
- `references/traceability-schema.md` §1 — the `agents:` block this skill reads.
- `references/templates/brief.md` — the worker brief this skill fills per task.
- `references/artefact-prose.md` — the findings ledger and what the PR body carries.
- The skills `/sdd-review` (round 0 and `--panel`), `/sdd-archive` (close-out), `/sdd-triage` (findings posted on the PR, round 0 onward), `/sdd-finalize` (the release sweep).
- The consuming repo's `docs/ai-workflow.md` § Orchestration and § Review — the repository's own copy of the orchestration rules and the review-request block, which it may have tuned. Follow that copy, not a version retyped here.
- The agent `sdd-implementer` — the worker this skill briefs and dispatches.

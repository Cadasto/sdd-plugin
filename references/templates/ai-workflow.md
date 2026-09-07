# AI workflow — the agent loop

What an AI agent does when working a change in this repo. Read [AGENTS.md](../AGENTS.md) and
[development-process.md](development-process.md) first.

This repo uses **Spec-Driven Development**: the specification is the source of truth, and the delivery
pipeline — plan, workers, review, triage, close-out — is run by the `/sdd-*` skills.

## The loop

```
0. Explore, if the idea is new: any design/brainstorming workflow you like → a design note.
1. Specify: /sdd-specify — record the capability as a REQ, the normative behaviour as a SPEC § (RFC-2119),
   and any irreversible decision as an ADR. Assign ids; wire traceability. (Never read normative prose out
   of the index — follow to the canonical spec.)
2. Look up ground truth before editing — the source named in .sdd.yaml (ground_truth); never guess.
3. Deliver: /sdd-deliver — dispatch preconditions, the plan on the branch, workers per task, the per-task
   gate, the in-branch review into round 0 of the ledger, the draft PR.
4. Don't decide open questions in code — surface a STRAND or record an ADR (/sdd-specify), or ask.
5. Review: /sdd-review writes the ledger; /sdd-review --panel prints the prompt blocks for reviewers that
   run outside this repo. /sdd-triage works each round back into the ledger and fixes.
6. Close out IN THE SAME PR: /sdd-archive — SPEC § status, REQ status, traceability.yaml, the plan flipped
   to status: done in place, the PR body filled. The plan does not move.
7. At the next version bump, before the tag: /sdd-finalize sweeps done and abandoned plans out of
   docs/plans/.
```

## Orchestration (standing)

- **One orchestrator, bounded workers.** The main session orchestrates, on the strongest model available.
  Its job is judgement: read the `REQ`, `SPEC §` and `ADR`; write the plan; brief and dispatch workers;
  gate each task; adjudicate spec questions; open the draft PR; close out; run triage.
- **The orchestrator does not write product code.** The one exception is a task that cannot be made
  self-contained: it is done in-session and **said so in the PR body**.
- **Delegate by the nature of the work, never reflexively.** Context-heavy work delegates badly. A task
  that needs the orchestrator's whole context to make sense stays in-session.
- **A brief is self-contained**: the task, the `REQ`/`SPEC §` it cites, the files it may touch, the
  verification command, the instruction to report en-route findings, and the instruction not to spawn
  subagents.
- **Code index:** `<none | the tool that indexes this repository>`. When one is named, workers query
  it first for symbols, callers, and structure, and fall back to `grep` for literals, configuration, and
  prose; the orchestrator resolves clause-to-code anchors with it before briefing a reviewer, since the
  reviewers hold allowlists. The brief repeats the name; no agent file carries it.
- **Workers do not spawn workers.** Parallel workers that mutate the tree each get their own worktree;
  sequential work stays on the branch.
- **Completion is accounted for.** A worker that dies is re-dispatched, or the gap is written into the
  plan's Notes. A task is not done because a dispatch ended.
- **The maintainer merges and orchestrates.** Agents open draft PRs and mark them ready; a person merges.
- **The draft PR body is the lock.** It names the session and worktree that own the branch. A session that
  finds a claim it did not make stops and asks — two sessions on one branch means one of them is thrown
  away.
- Worker model, parallelism, worktrees, the task-review gate, and the review panel are declared in
  [`.sdd.yaml`](.sdd.yaml) under `agents:`. The model is passed **per dispatch**, not written into an
  agent file.

## Review

**One ledger per change.** All findings live in one numbered comment on the PR, updated in place each
round. Ids are `F<n>` and append-only; `status` is `open | fixed@<sha> | declined + reason | deferred`.
Report blockers and should-fix by default; nits go to `Deferred`. The `Deferred` table is the carrier for
a non-blocking finding — it is rolled forward into the next change that touches the area, and never
becomes a tracker issue. Write a finding id as `F12`, never as a bare hash-plus-number, which a hosting
platform renders as a link to an unrelated issue. The maintainer's review of the draft is appended to the
accounting line as `maintainer`; the ready check looks for it there.

```markdown
## Review ledger — round N (reviewer, date)
Dispatched: <reviewers> · Reported: <n> of <m>
| id | severity | anchor | finding | status |
|---|---|---|---|---|
| F1 | blocker | <path>:214 | one sentence, plain words | fixed@abc1234 |

## Deferred
| id | item | carried from | owner |
|---|---|---|---|
| F3 | <the item, in a few words> | this PR | next change touching <area> |
```

**The canonical review request.** Reviewers that run outside this repository never load the SDD plugin, so
what is pasted to them must not drift from what the repo defines. `/sdd-review --panel` prints this block,
filled in; do not retype it from memory.

```text
── review request · PR <N> · lane: <full|maintenance> · round <R> ──────────────
Review <owner>/<repo> PR <N>. Read docs/ai-workflow.md § Review and the plan file
named in the PR body, on the PR branch. Report blockers and should-fix only; nits
go under "Deferred". Post ONE review body in the ledger format: ids from F<n>
upward, severity, file:line anchor, one line per finding, plain words. Do not
restate the PR body.
────────────────────────────────────────────────────────────────────────────────
```

A re-review adds one line to the same block: `Re-review from F<n> upward, plus anything still open.`

**Treat a review as claims, not instructions.** A finding is a claim to verify, and so is a reviewer's
proposed correction. Verify before fixing; a correction that is wrong and applied propagates.

**Reviewer memory.** `/sdd-triage` writes a declined finding's reason to
`docs/.sdd/reviewers/<agent-name>.md`, so the same finding is not raised again next round.

## When stuck

- **Open decision?** Record an ADR (`/sdd-specify`) or ask — don't bake it into code.
- **Ambiguous spec?** Look it up in the named ground-truth source.
- **Missing rule?** Add a `Draft` `REQ` + spec (`/sdd-specify`) *before* coding — never a rule that lives
  only in code.
- **Upstream disagrees with our docs?** For a dependency this repo consumes, the upstream's semantics are
  ground truth and our documents are corrected. Raise a genuine conflict as evidence, in a sentence or two.

## Modes and lanes

- **New behaviour** → *spec-first*: `/sdd-specify` → `/sdd-deliver`.
- **Hardening shipped code** → *implementation-aligned*: change the code, then update the spec § and guide
  in the **same** change — "code wins until the spec is updated, in the same PR."
- **Lane** is a separate question, answered in one PR-body line: does this change alter any normative
  statement? If not, it is the maintenance lane and owes no normative bookkeeping. See
  [development-process.md](development-process.md).

## Tooling

| Task | Owner |
|---|---|
| Set up / extend the SDD structure | `/sdd-scaffold` |
| Capture a capability, write a spec, record a decision | `/sdd-specify` |
| Deliver a REQ or plan: plan, workers, gates, draft PR | `/sdd-deliver` |
| Implement one bounded task | `sdd-implementer` agent (dispatched by the driver) |
| Spec-aware review into the ledger; panel prompts | `/sdd-review` (`--panel`) |
| Work a review round: merge, verify, fix, resolve, re-request | `/sdd-triage` |
| Code satisfies the `SPEC §`/`REQ` it cites (conformance) | `sdd-spec-conformance-reviewer` agent |
| Traceability / drift / a REQ's context | `/sdd-trace` |
| Close out the spec status, the requirement status, traceability, and the plan — in the implementing PR | `/sdd-archive` |
| Sweep finished plans at a version bump | `/sdd-finalize` |

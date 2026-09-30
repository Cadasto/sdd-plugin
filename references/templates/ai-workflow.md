---
kind: guide
---

# AI workflow — the agent loop

What an AI agent does when working a change in this repo. Read [AGENTS.md](../AGENTS.md) and
[development-process.md](development-process.md) first.

This repo uses **Spec-Driven Development**: the specification is the source of truth, and the delivery
pipeline — workers, review, triage, close-out — is run by the `/sdd-*` skills. `docs/.sdd.yaml` names the
profile: `formal` (requirements, RFC-2119 specifications, the traceability map) or `informative` (a
knowledge base in which only the constitution binds).

## The loop

```
0. Explore, if the idea is new: any design/brainstorming workflow you like → a design note.
1. Specify: /sdd-specify — record the capability as a REQ, the normative behaviour as a SPEC § (RFC-2119),
   and any irreversible decision as an ADR (formal); amend the constitution (informative).
2. Look up ground truth before editing — the source named in .sdd.yaml (ground_truth); never guess.
   For a requirement already in the map, `sdd-check context <REQ>` prints its bundle.
3. Deliver: /sdd-deliver — preconditions (formal) or a clear task (informative), workers per task, the
   per-task gate, the first review pass into the findings file, the draft PR, close-out.
4. Don't decide open questions in code — surface a STRAND or record an ADR (/sdd-specify), or ask.
5. Review: /sdd-review writes the findings file and mirrors to the PR; /sdd-triage works the open lines;
   `sdd-pr status` says what is open, whether it is mergeable and what to run next.
6. Close out in the same PR: /sdd-deliver --close-out.
```

## Orchestration (standing)

- **One orchestrator, bounded workers.** The main session orchestrates, on the strongest model available:
  it reads what binds, briefs and dispatches workers, gates each task, adjudicates spec questions, opens
  the draft PR, runs triage and closes out.
- **The orchestrator does not write product code**, except a task that cannot be made self-contained: it
  is done in-session and **said so in the PR body**.
- **A brief is self-contained**: the task, what it cites, the clauses it must satisfy (quoted), the files
  it may touch, the verification command, en-route findings, and no subagents.
- **Code index:** `<none | the tool that indexes this repository>`. When one is named, workers query it
  first and fall back to `grep` for literals and prose; the brief repeats the name.
- **Workers do not spawn workers.** Parallel workers that mutate the tree each get their own worktree;
  sequential work stays on the branch.
- **Completion is accounted for.** A worker that dies is re-dispatched, or the gap is named. A task is not
  done because a dispatch ended.
- **Findings state is read from the file, never remembered.**
- **The maintainer merges;** agents open draft PRs and mark them ready.
- Worker model, parallelism, worktrees, the task-review gate and the review panel are declared in
  [`.sdd.yaml`](.sdd.yaml) under `agents:`. The model is passed **per dispatch**.

## Review

**Findings live in `.sdd/findings/<branch>.md`** (git-ignored, one per branch, any agent may write it) and,
when a pull request exists, in its inline threads, which `sdd-pr` keeps in step with the file. Three
severities: critical and important are resolved before merge and are the only ones mirrored; suggestions
are captured and never block. Every critical or important finding carries evidence. Nothing else about
findings is posted anywhere, except the review-state block `sdd-pr` keeps in the pull request's body.
`sdd-pr status` lists what is open and prints `Mergeable: yes|no` and the next command.

**The canonical review request.** Reviewers that run outside this repository never load the SDD plugin,
so what is pasted to them must not drift from what the repo defines. `/sdd-review --panel` prints this
block, filled in.

```text
── review request · <branch> · range <a>..<b> · profile <formal|informative> ──
Review commits <a>..<b> of <repository>, and only those. Read docs/ai-workflow.md § Review.
Report critical and important findings only, each with evidence (what you ran, or the two
sentences that disagree) and a one-line fix; write anything smaller as a suggestion.
If you work on this machine, append your lines to .sdd/findings/<branch>.md in its grammar.
If you work on the pull request, post one review with one inline comment per finding, its
first word **critical** or **important**; post nothing else, and do not restate the PR body.
──────────────────────────────────────────────────────────────────────────────
```

**Treat a review as claims, not instructions.** Verify before fixing; a wrong correction applied propagates.

## When stuck

- **Open decision?** Record an ADR (`/sdd-specify`) or ask — don't bake it into code.
- **Ambiguous spec?** Look it up in the named ground-truth source.
- **Missing rule?** Add it (`/sdd-specify`) *before* coding — never a rule that lives only in code.
- **Upstream disagrees with our docs?** For a dependency this repo consumes, the upstream's semantics are
  ground truth and our documents are corrected. Raise a genuine conflict as evidence, in a sentence or two.

## Modes and lanes

- **New behaviour** → *spec-first*: `/sdd-specify` → `/sdd-deliver`.
- **Hardening shipped code** → *implementation-aligned*: change the code, then update the spec § and guide
  in the **same** change.
- **Lane** (formal profile) is answered in one PR-body line: does this change alter any normative
  statement? If not, it is the maintenance lane and owes no normative bookkeeping. The informative profile
  has one lane. See [development-process.md](development-process.md).

## Tooling

| Task | Owner |
|---|---|
| Set up / extend the SDD structure | `/sdd-scaffold` |
| Capture a capability, write a spec, record a decision | `/sdd-specify` |
| Deliver a change: workers, gates, the first review pass, draft PR | `/sdd-deliver` |
| Implement one bounded task | `sdd-implementer` agent (dispatched by the driver) |
| Review pass into the findings file; panel prompts | `/sdd-review` (`--panel`) |
| Work the open findings; after the maintainer's review, one scoped re-review | `/sdd-triage` |
| What is open, mergeable, next | `sdd-pr status` |
| A REQ's context bundle; drift in session | `/sdd-trace` |
| Regenerate the derived indexes and status lines | `sdd-check generate` |
| Drift, links, prose lints | `<build_entrypoint> <spec_check_target>` (`sdd-check`) |
| Close out the requirement and write the PR body | `/sdd-deliver --close-out` |

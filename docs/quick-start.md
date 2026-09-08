# Quick start

Take one capability from idea to a ready pull request with the `/sdd-*` skills. Written for sdd 0.5.0 on Claude Code with a GitHub remote. Cursor installation and hook wiring differ — see [install.md](install.md).

The assistant's wording varies between runs. The files each step produces, and the gates it stops at, do not — check those.

## Before you start

- Claude Code with the plugin installed — [install.md](install.md).
- A git repository with a GitHub remote and the `gh` CLI signed in. `/sdd-deliver` opens the draft pull request with it.
- One build entry point. This walkthrough uses `make`; `task`, `just`, and `npm` work the same way.

The example capability is refreshing an expired access token in a service that issues API tokens. Replace it with your own — the steps do not change.

## 1. Scaffold the repository

```text
/sdd-scaffold area-prefixed make
```

The skill asks for the requirement areas and the ground-truth source for your domain facts, then creates:

```text
docs/
  .sdd.yaml
  development-process.md   ai-workflow.md   ci.md
  requirements/            README.md, _template.md
  specifications/          README.md, _template.md, traceability.yaml
  adr/                     README.md, _template.md
  plans/
AGENTS.md
```

It fills the `agents:` block of `docs/.sdd.yaml` with example values and the code-index line in `docs/ai-workflow.md` § Orchestration, and it suggests a value for `agents.reviewers` when it finds `go.mod`, `composer.json`, or `package.json`. Review both before going on: name the reviewer agent your repository uses, or leave the list empty and expect the per-task gate to report itself unconfigured in step 3.

It also offers stub `spec-check` and `ci` targets for your `Makefile`. The stub `spec-check` fails on purpose with `spec-check: no checker wired yet` until the repository wires its own checker. Accept the stubs for now.

Check: `docs/.sdd.yaml` exists and carries an `agents:` block. From the next session on, a one-line banner names the `/sdd-*` surface whenever you open the repository.

## 2. Specify the capability

```text
/sdd-specify add a capability for refreshing an expired access token
```

The skill assigns the next free identifier — `REQ-AUTH-001` in this example — and writes:

- the requirement under `docs/requirements/`: the capability, observable acceptance criteria including what the system must refuse, what is out of scope, and the two status fields `status: draft` and `implementation: proposed`;
- one row in `docs/requirements/README.md` that links to the spec section;
- the normative section in the canonical topic spec under `docs/specifications/`, in RFC-2119 language with a stable `§` number;
- the record in `docs/specifications/traceability.yaml`.

An irreversible decision made along the way — the token format, say — becomes an ADR:

```text
/sdd-specify record an ADR: refresh tokens are opaque strings, not JWTs
```

The ADR starts as `proposed`. Set it to `accepted` before code depends on it; the delivery gate checks this.

Check:

```text
/sdd-trace REQ-AUTH-001
```

The bundle shows the index row, the traceability record, and the spec section it points to. A broken link is reported here, before any code exists.

## 3. Deliver it

```text
/sdd-deliver REQ-AUTH-001
```

The skill runs as the orchestrator and stops at each gate:

1. **Dispatch gate.** Five preconditions: the requirement has acceptance criteria, the spec sections exist, any ADR is accepted, the failure behaviour is cited from the requirement and the spec, and the verification commands are known. An unmet one stops the run and is named. Fix it with `/sdd-specify` and run again.
2. **Lane.** A new capability is the full lane. The lane is written into the plan header.
3. **Plan.** A feature branch, and `docs/plans/YYYY-MM-DD-<slug>.md` committed on it with `status: active`. The plan lists small, independently verifiable tasks and states no rule — a rule belongs in the spec.
4. **Workers.** One `sdd-implementer` per task, on the model and parallelism the `agents:` block declares, each briefed from the plan. A worker names `REQ-AUTH-001` in its test names and its commit message — not in doc comments, which stay plain prose for whoever reads the code — runs the verification command named in its brief, and reports anything wrong outside its brief as en-route findings.
5. **Per-task gate.** With `task_review: lane`, the reviewers named in `agents.reviewers` check each task on the full lane. An empty list is reported as an unconfigured gate, and the skill asks before continuing.
6. **Round 0.** `/sdd-review` runs on the branch. Its findings open the ledger, and blockers are fixed before any pull request exists.
7. **Draft pull request.** Opened as a draft, with `Lane: full` in the body and a claim line naming the session and worktree that own the branch. The ledger is posted as one comment.

Then it stops and waits for you.

Check: `gh pr view <N>` shows a draft whose body carries the `Lane:` line and the claim line, and the plan file is on the branch.

## 4. Review, triage, close out

Review the draft as you would any pull request. Conversation comments, review comments, and inline comments are all read.

```text
/sdd-triage <N>
```

Triage merges your findings into the ledger under `F<n>` ids, verifies each one against the code and the cited spec section before fixing it, sweeps the same pattern elsewhere in the tree, fixes in this pull request, and resolves the threads. A finding it declines gets a reason, recorded so the same finding is not raised next round.

When the ledger has no open blocker, resume delivery against the pull request number:

```text
/sdd-deliver <N>
```

Resumed, the skill closes out through `/sdd-archive` — the spec section status, the requirement's `implementation` status, the traceability record, and the plan flipped to `status: done` where it lies — fills the pull request body, marks the pull request ready, and prints one review-request block per entry in `agents.review_panel.full` for reviewers that run outside the repository. Paste those where they go. A person merges.

Check: the plan is still in `docs/plans/` and its frontmatter reads `status: done`; the pull request is no longer a draft.

## 5. Sweep at the next release

Finished plans stay in `docs/plans/` until the next version bump. As the first step of that bump, before the tag:

```text
/sdd-finalize --dry-run
/sdd-finalize
```

The dry run lists every plan whose status is `done` or `abandoned` and stops if another document under `docs/` still links to one. Rewrite that citation to the pull request or the requirement, then run without `--dry-run`. The deletions ride in the bump commit. Plans that are `active` or `postponed` are never touched.

## What you have now

One requirement with acceptance criteria, one normative spec section, one accepted decision, a traceability record naming the packages and tests, and a merged pull request whose body records what was verified. Once you replace the stub, `make spec-check` catches drift between the map and the tree on every change.

Next: [examples.md](examples.md) for prompts by use case, and the [methodology](../references/sdd-methodology.md) for the rules behind each gate.

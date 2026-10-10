# Quick start

This walkthrough is for a first-time user. It takes one capability from idea to a ready pull request with the `/sdd-*` skills, in a repository that has never been scaffolded. It was written for sdd 0.8.0 on Claude Code with a GitHub remote, on the formal profile. Cursor installation and hook wiring differ; see [install.md](install.md).

The assistant's wording varies between runs. The files each step produces, and the gates it stops at, do not. Check those.

## Before you start

- Claude Code with the plugin installed: see [install.md](install.md).
- A git repository with a GitHub remote and the `gh` CLI signed in. `/sdd-deliver` opens the pull request with it, and `sdd-pr` mirrors findings to it.
- One build entry point. This walkthrough uses `make`; `task`, `just`, and `npm` work the same way.

The example capability is refreshing an expired access token in a service that issues API tokens. Replace it with your own; the steps do not change.

## 1. Scaffold the repository

```text
/sdd-scaffold formal area-prefixed make
```

The skill asks for the profile first. This walkthrough uses formal; informative keeps `docs/` as a knowledge base bound only by a `docs/architecture.md` constitution. It then asks for the requirement areas and the ground-truth source for your domain facts, and creates:

```text
docs/
  .sdd.yaml
  development-process.md   ai-workflow.md   ci.md
  requirements/            README.md, _template.md
  specifications/          README.md, _template.md, traceability.yaml
  adr/                     README.md, _template.md
AGENTS.md
.github/PULL_REQUEST_TEMPLATE.md
```

It also adds `/.sdd/` to `.gitignore`, a scratch folder for working files. Each branch's findings file lives in the clone's git directory instead, so it needs no ignore line and every worktree sees it.

It fills the `agents:` block of `docs/.sdd.yaml` with example values, and the code-index line in `docs/ai-workflow.md` § Orchestration. When it finds `go.mod`, `composer.json`, or `package.json`, it suggests a value for `agents.reviewers`. Review both before going on. Name the reviewer agent your repository uses, or leave the list empty and expect the per-task gate to report itself unconfigured in step 3.

It vendors the drift gate too. `tools/sdd-check.py` is copied from the plugin to `check.script` (`scripts/sdd-check.py` by default), and the copy's version is pinned in `check.version`. The real `spec-check` target is wired into your `Makefile`: `python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check`, not a stub.

The skill runs `generate` before the first `check`, because a fresh scaffold's index blocks still hold placeholder rows that the `generated` family would reject. That first `check` still fails. The starter `traceability.yaml` has no records yet, which is a `map-schema` error by design, so every family that needs records is skipped with the reason `map unavailable`. This is the expected first state. It clears once `/sdd-specify` writes the first requirement in step 2.

Check: `docs/.sdd.yaml` exists and carries an `agents:` block and a `check:` block naming the vendored gate. From the next session on, a one-line banner names the `/sdd-*` surface whenever you open the repository.

Already on an earlier version instead of starting fresh? Run `/sdd-scaffold --upgrade` and follow [docs/upgrading.md](upgrading.md); this walkthrough is for a repository that has never been scaffolded.

## 2. Specify the capability

```text
/sdd-specify add a capability for refreshing an expired access token
```

The skill assigns the next free identifier (`REQ-AUTH-001` in this example) and writes:

- the requirement under `docs/requirements/`: the capability, observable acceptance criteria including what the system must refuse, what is out of scope, and the two status fields `status: draft` and `implementation: proposed`;
- one row in `docs/requirements/README.md` that links to the spec section;
- the normative section in the canonical topic spec under `docs/specifications/`, in RFC-2119 language with a stable `§` number;
- the record in `docs/specifications/traceability.yaml`.

An irreversible decision made along the way, such as the token format, becomes an ADR:

```text
/sdd-specify record an ADR: refresh tokens are opaque strings, not JWTs
```

The ADR starts as `proposed`. Set it to `accepted` before code depends on it; the delivery gate checks this.

Check:

```text
/sdd-trace REQ-AUTH-001
```

The bundle shows the index row, the traceability record, and the spec section it points to, so a broken link shows up here, before any code exists. The skill takes the bundle from the gate: `python3 scripts/sdd-check.py context REQ-AUTH-001` prints the same thing from a shell.

## 3. Deliver it

```text
/sdd-deliver REQ-AUTH-001
```

The skill runs as the orchestrator and stops at each gate:

1. **Dispatch gate.** Five preconditions: the requirement has acceptance criteria, the spec sections exist, any ADR is accepted, the failure behaviour is cited from the requirement and the spec, and the verification commands are known. An unmet one stops the run and is named. Fix it with `/sdd-specify` and run again.
2. **Lane.** A new capability is the full lane. The lane is passed to the review and written into the pull request body.
3. **Workers.** The skill creates a feature branch and dispatches one `sdd-implementer` per task, on the model the `agents:` block declares. Tasks run one after another on the branch; only large tasks that touch disjoint files run in parallel, still on the same branch. Each brief quotes the clauses the task must satisfy. The worker writes each test first and shows that it fails with the guard removed. It names `REQ-AUTH-001` in its test names and its commit message, never in doc comments, and reports anything wrong outside its brief as en-route findings. The orchestrator keeps its own task list; nothing about the plan is committed.
4. **Per-task gate.** With `task_review: lane`, the reviewers named in `agents.reviewers` check each task on the full lane. An empty list is reported as an unconfigured gate, and the skill asks before continuing.
5. **First review pass.** After the full gate, `/sdd-review` reads the branch and writes its findings into the branch's findings file; `sdd-pr status` prints where it is. `/sdd-triage` fixes the critical and important ones before any pull request exists.
6. **Pull request.** Opened ready for review (ask for a draft if you want one), with `Lane: full` under *Spec and traceability*. Anything still open is mirrored to its inline threads.

It prints one review-request block per entry in `agents.review_panel.full`, for reviewers outside the repository; paste those where they go. Then it stops and waits for you.

Check: `python3 <plugin root>/tools/sdd-pr.py status` prints the open counts, `Mergeable:` and `Next:`.

## 4. Review, triage, close out

Review the pull request as you would any other, with inline comments on the lines you mean.

```text
/sdd-triage
```

Triage pulls your unresolved threads into the findings file; a comment with no severity word counts as important. It checks each finding against the code and the cited spec section before fixing anything. Fixes land in this branch, each line in the file is flipped to fixed or declined with a reason (or deferred, when you say so), and your threads are answered and resolved. When the fixes changed anything, documents included, triage runs one more review pass over them.

When `sdd-pr status` shows nothing open, close out:

```text
/sdd-deliver <N> --close-out
```

The close-out sets the requirement's traceability record to `implementation: shipped`; the spec section is promoted only if you confirm it. It runs the full gate before pushing, writes the pull request body, and marks the pull request ready if you asked for a draft. A person merges.

Suggestions never block. Each review pass put its suggestions in a comment of their own on the pull request. After one or more merges, `/sdd-triage --backlog` carries the open ones to `docs/backlog.md`, where the next delivery that touches their files picks them up. The first harvest asks where to start.

Check: the requirement's record reads `implementation: shipped`, its body has Summary, Spec and traceability, Verification and the checklist.

## What you have now

One requirement with acceptance criteria, one normative spec section, one accepted decision, a traceability record naming the packages and tests, and a merged pull request whose body records what was verified. `make spec-check` catches drift between the map and the tree on every change.

Next: [examples.md](examples.md) for prompts by use case, and the [methodology](../references/sdd-methodology.md) for the rules behind each gate.

# Quick start

This walkthrough is for a first-time user. It takes one capability from idea to a ready pull request with the `/sdd-*` skills, in a repository that has never been scaffolded. It describes sdd 0.15 on Claude Code with a GitHub remote, on the formal profile. Cursor installation and hook wiring differ; see [install.md](install.md).

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
2. **Lane.** A new capability is the full lane. A lane you name is final; the skill never raises it. The lane is passed to the review and written into the pull request body.
3. **Workers.** The skill creates a feature branch and dispatches one `sdd-implementer` per task, on the model the `agents:` block declares. Tasks run one after another on the branch; only large tasks that touch disjoint files run in parallel, still on the same branch. Each brief quotes only the clauses the task must satisfy or change, in about 4k characters. The worker writes each test first and shows that it fails with the guard removed for each new MUST; a small defect it meets in its own files it fixes, with a test. It names `REQ-AUTH-001` in its test names and its commit message, never in doc comments, and reports anything wrong outside its brief as en-route findings. The orchestrator keeps its own task list; nothing about the plan is committed.
4. **Per-task gate.** Off by default: the first review pass is the gate. With `task_review: lane`, the reviewers named in `agents.reviewers` check each task on the full lane and the informative profile; an empty list is then reported as an unconfigured gate, and the skill asks before continuing.
5. **First review pass.** After the full gate, `/sdd-review` reads the branch and writes its findings into the branch's findings file; `sdd-pr status` prints where it is. `/sdd-triage` fixes the critical and important ones in the change before any pull request exists, and any defect in a file the branch changed; one in code the branch did not change is marked `outside` and fixed here when the fix is small, otherwise only if you say so. Slips in the documents the branch wrote come back as a fix list and are applied, never filed.
6. **Pull request.** Opened ready for review (ask for a draft if you want one), with `Lane: full` under its Summary. Anything still blocking is mirrored to its inline threads; the rest goes in one comment.

Then it stops and waits for your review.

Check: `python3 <plugin root>/tools/sdd-pr.py status` prints the open counts, `Mergeable:` and `Next:`.

## 4. Review, triage, close out, clean up

Review the pull request as you would any other, with inline comments on the lines you mean.

```text
/sdd-triage
```

Triage pulls your unresolved threads into the findings file, and records them as your review. A comment counts as important unless it opens with **critical**; end its first line with `· outside` for a defect in code the branch did not change, which then blocks nothing. It checks each finding against the code and the cited spec section before fixing anything. Fixes land in this branch, each line in the file is flipped to fixed or declined with a reason (or deferred, when you say so), and your threads are answered and resolved. When a fix changed code or added a MUST, triage runs one more review pass over the fixes; a fix that only rewords or corrects text gets none. When your comment says a spec sentence is wrong, that is the call: the sentence is corrected in the branch, and the agent does not argue from it.

When `sdd-pr status` shows nothing blocking, close out. On a ready pull request `status` reads `Mergeable: yes` and `Next: merge`: close out first, or merge and run the close-out afterwards, which then commits on the default branch.

```text
/sdd-close <N>
```

The close-out sets the requirement's traceability record to `implementation: shipped`; the spec section is promoted only if you confirm it. It ticks the acceptance criteria the change delivered, adds the changelog line, runs the full gate before pushing, writes the pull request body, and marks the pull request ready if you asked for a draft.

Suggestions never block, and a reviewer files at most five. Each review pass put its suggestions, and any `outside` defects, in its comment on the pull request. The close-out fixes an `outside` defect with a small fix in the branch and carries the remaining defects to `docs/backlog.md` in this pull request, where the next delivery that touches their files picks them up; it asks you once, by line, which suggestions to carry. The rest stay on the pull request until `/sdd-triage --backlog`, which you run now and then on the default branch; its first harvest asks where to start, and it keeps the file at about 40 lines.

You merge the pull request on the forge; the skill never merges or closes one. Then run `/sdd-close <N>` again: it removes the branch, its worktree and its findings file, and refuses while anything in that file would be lost.

Check: the requirement's record reads `implementation: shipped`, and the pull request body has Summary, Changes and Verification, in about 450 words. Start the next change in a new session.

## What you have now

One requirement with acceptance criteria, one normative spec section, one accepted decision, a traceability record naming the packages and tests, and a merged pull request whose body records what was verified. `make spec-check` catches drift between the map and the tree on every change.

Next: [examples.md](examples.md) for prompts by use case, and the [methodology](../references/sdd-methodology.md) for the rules behind each gate.

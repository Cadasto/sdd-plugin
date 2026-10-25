# Prompt examples

This page is for users whose repository is already scaffolded. It collects recipes with one goal each: the prompt to type, what happens, and what to check. New to the plugin? Start with the [quick start](quick-start.md).

Every `/sdd-*` skill also triggers on plain phrasing, such as "add a requirement" or "review this branch", so you never have to type the slash form. The example repository issues API tokens; its requirements use the `AUTH` area and its spec is `SPEC-AUTH`.

## Ask where a statement belongs

```text
Should "a refresh with a revoked token fails closed" be a requirement or a spec section?
```

The router skill answers without touching a file. The requirement names the observable outcome as an acceptance criterion; the spec section owns the normative *how*, meaning the `MUST NOT` and the error contract. Then it points you at `/sdd-specify`. Ask it whenever you are unsure which kind of document you are about to write.

## Turn a design note into documents

You explored an idea in a brainstorming session and kept the note.

```text
/sdd-specify turn docs/analysis/2026-09-07-token-refresh.md into a requirement and its spec section
```

The note is input, not the source of truth. Its normative statements are extracted into the canonical spec; the requirement gets acceptance criteria; the note keeps only narrative.

Check: no `MUST`, `SHOULD`, or `MAY` sentence lives only in the note.

## Record a decision

```text
/sdd-specify record an ADR: refresh tokens are opaque strings, not JWTs
```

One decision per ADR, next sequential number, `status: proposed`. When you have decided, set it to `accepted` in the file; the dispatch gate refuses to start delivery on a `proposed` ADR.

Check: `docs/adr/README.md` has the row; the ADR cites the requirements it amends.

## Fix a bug that proves the spec wrong

The code did one thing, the spec said another, and the spec was wrong. This is implementation-aligned work on the full lane: the fix and the spec amendment ride in the same pull request.

```text
/sdd-specify amend SPEC-AUTH §3: a refresh with a revoked token MUST return 401 and MUST NOT rotate the token
```

Fix the code on the same branch, starting from a test that fails on the bug, then:

```text
/sdd-review
```

The review decides the lane by asking whether a normative statement changed meaning, and reads the answer from the changed document lines; `sdd-pr scope` prints `normative lines changed: n` as a hint. Here one did, so the conformance and document reviewers run alongside the repository's own. `--lane full` or `--lane maintenance` sets the lane for one pass instead.

Check: the findings file's new `Reviewed` line names `sdd-spec-conformance-reviewer`, and the spec section's status is not lagging behind the code.

## Refactor with no behaviour change

Maintenance lane: no requirement and no spec edit.

```text
/sdd-review --lane maintenance
```

On the maintenance lane the reviewers named in `agents.reviewers` read the code, and `sdd-doc-reviewer` reads the changed documents only when a normative line, a requirement or an ADR changed, to check that it still agrees with the code and the other documents. The conformance reviewer is skipped, because no obligation is added on this lane; a sentence corrected to the behaviour a fix gives it stays on the lane. If nothing in the range calls for a reviewer (say `agents.reviewers` is empty and only code changed), the pass writes no `Reviewed` line and the range stays open. Your own review of the pull request is then the pass: record it with `sdd-pr record --agent maintainer --reviewers <your name> --reported 1/1`. The pull request body's Summary carries `Lane: maintenance — no normative change`.

The lane is guarded by a ratchet, not a diff check: a reviewer that finds a new rule living only in code flags it, and the change becomes full lane. `make spec-check` runs in both lanes.

## Find what implements a requirement

```text
/sdd-trace REQ-AUTH-001
```

One bundle: the index row, the traceability record, the canonical spec section, and any open `STRAND` touching the requirement. Report-only.

```text
/sdd-trace
```

With no argument, it scans the whole map against the tree and groups what it finds by gate family: a canonical link to a missing anchor, a listed test that does not exist, a requirement marked `shipped` with no packages. Before a release, or when `spec-check` fails in CI and the cause is unclear:

```text
/sdd-trace --audit
```

That dispatches the `sdd-traceability-auditor` agent in its own context. It runs the same gate, checks by hand what the gate skipped, and edits nothing.

`/sdd-trace REQ-AUTH-001` gets its bundle from the vendored gate. You can print the same bundle from a shell:

```text
python3 scripts/sdd-check.py context REQ-AUTH-001
```

That is useful in CI, or in any script that needs a requirement's context without a session running.

## Check code against the spec it cites

```text
/sdd-review --lane full
```

On the formal profile's full lane, the pass sends changed code that implements a cited `SPEC §` to the `sdd-spec-conformance-reviewer` agent, with the gate's log and the changed hunks. It judges the code clause by clause, and proves each MUST the change added with `sdd-pr guard`: the guard is removed in a scratch worktree, and a test that stays green is a critical finding with both runs as evidence; a sentence only reworded, and the older MUSTs, get no guard run. It judges conformance, not code quality; the repository's own language reviewer does that.

When a normative line, a requirement or an ADR changed, the same pass sends the document hunks to the `sdd-doc-reviewer` agent, on a cheaper model where the host lets a dispatch pick one and you named none. A sentence that disagrees with a merged one elsewhere, or contradicts the code on a contract, is important; a normative sentence that repeats one elsewhere with a different force is critical. A slip inside the branch's own documents, such as an acceptance criterion that cannot be observed or two of its sentences that disagree, comes back as a fix list the orchestrator applies in the pass, never as a finding; a keyword missing from a sentence the code already meets is not raised.

## Get a second opinion

After one review, open another session, on another model or host, and run:

```text
/sdd-review
```

It reads the whole branch, not only what came after the first pass, and records its own `Reviewed` line, named by host and model. The reviewers it dispatches do not see the open findings, so their opinion is independent; a defect the file already holds gains the new reviewer in `by:` instead of a second line. To review only the commits since the last pass, whoever made it, without what a merge of the base brought in:

```text
/sdd-review --since-last
```

## A reviewer without the plugin

A second pass in any host that loads the plugin is `/sdd-review --pr 7` again: it lands in the same findings file, beside yours. A reviewer that does not load the plugin gets the review-request block from `docs/ai-workflow.md` § Review, filled in. One working on this machine pipes its lines to `sdd-pr add -`; one working on the pull request posts inline comments, and `sdd-pr pull` brings them in.

## Work the open findings

```text
/sdd-triage
```

The open critical and important lines of the branch's findings file are the whole to-do list. Each one is checked before it is fixed, the fix lands in this branch, and the line is flipped. An excerpt of the file:

```markdown
# Findings — feat/auth-refresh
Base: main
Reviewed 9c1e2ab · 2026-09-30 · claude: sdd-spec-conformance-reviewer, go-coding:go-reviewer (2 of 2)
Reviewed 9c1e2ab · 2026-10-01 · maintainer: ana (1 of 1)

## Open
- [ ] important · internal/auth/refresh_test.go:40 · no test for the revoked path · by: ana · forge: 5893201111

## Resolved
- [x] critical · internal/auth/refresh.go:88 · a revoked token rotates instead of failing closed (SPEC-AUTH §3) · evidence: TestRefreshRevoked stays green with the check deleted · by: claude · fixed 4f0a1c2

## Suggestions
- internal/auth/refresh.go:120 · rename `tok` to `token` · by: go-coding:go-reviewer
```

And what `sdd-pr status` prints for it; `sdd-pr flip` takes the `#key`:

```text
branch feat/auth-refresh · base main · head 4f0a1c2 · last reviewed 9c1e2ab (code changed since)
findings: <clone>/.git/sdd/findings/feat--auth-refresh.md
open: 0 critical, 1 important · outside the change: 0 · suggestions: 1
#0e53b - [ ] important · internal/auth/refresh_test.go:40 · no test for the revoked path · by: ana · forge: 5893201111
#72ee1 - internal/auth/refresh.go:120 · rename `tok` to `token` · by: go-coding:go-reviewer
forge: github · PR 7 (ready) · 0 unresolved threads not open in the file · checks: pass
Mergeable: no — 1 important open
Next: /sdd-triage
```

The format and its rules live in [review.md](../references/review.md).

## Close out, then clean up after the merge

```text
/sdd-close <N>
```

Run it when `sdd-pr status` shows nothing blocking. It sets the requirement to `shipped`, ticks the acceptance criteria the change delivered, adds the changelog line, writes the pull request body and marks a draft ready. It fixes an `outside` defect with a small fix in the branch and carries the remaining defects to `docs/backlog.md` in this pull request; it asks once which suggestions to carry, by name, and the rest wait on the pull request for `/sdd-triage --backlog`. It ends by telling you to start the next change in a new session.

You merge on the forge. Then run `/sdd-close <N>` again, from any checkout: `sdd-pr clean` removes the branch's worktree, the local branch and its findings file. It keeps the branch when it holds a commit the pull request does not, and refuses while a line in the findings file would be lost. Run from inside the worktree it would remove, it prints the commands for you instead. The pull request and the remote branch are yours.

## Carry merged pull requests' leftovers to the backlog

```text
/sdd-triage --backlog
```

Run it on the default branch now and then, after merges. It reads the non-blocking comment of every pull request merged since `harvested_through:` in `docs/backlog.md`. It carries the open lines under `## Unsorted`, defects outside their change first, each line tagged `from: #<n>`. It leaves out lines fixed, carried or dropped in their pull request, and lines whose file is gone. Then it consolidates:
- it re-checks the older lines whose file changed since the last harvest;
- it sorts the new lines into themes, each what one delivery would take on;
- it folds duplicates, drops what is settled or only taste, and keeps the file at about 40 lines: the oldest leads go, defects stay, and the commit message lists what was dropped.

It commits `docs/backlog.md`; read that commit. With `forge: none` it carries nothing and only re-checks. The first harvest asks where to start: a date, or a pull request number.

## Resume an interrupted delivery

```text
/sdd-deliver <N>
```

Given a pull request number, the skill reads the findings file, `sdd-pr status` and the pull request body, and carries on at the first unfinished step. Two sessions on one branch take turns on one checkout; git will not check out the same branch in two worktrees.

## Work on the informative profile

A repository where the code leads and `docs/` is a knowledge base: `profile: informative`, one `docs/architecture.md` constitution, no requirements and no traceability map.

```text
/sdd-deliver add a retry to the HTTP client
```

No requirement is needed to start. The workers change the code, and the documents that describe the client are brought up to date in the same branch. The review pass is the code reviewer plus `sdd-doc-reviewer` checking consistency. The conformance reviewer runs only when the change touches a constitution sentence. `sdd-check check` runs `descriptor`, `doc-kinds`, `links`, `changelog` and `generated`, and lists the map families as skipped.

## Configure a Go repository

The plugin dispatches only the reviewers the descriptor names and briefs workers with only the skills it lists. For a Go repository with the go-coding plugin installed, `docs/.sdd.yaml` carries:

```yaml
sdd:
  agents:
    worker_skills: [go-coding:go-coding, go-coding:go-testing]
    reviewers:
      "**/*.go": go-coding:go-reviewer
      "**/go.mod": go-coding:go-reviewer
```

Workers load those skills from their brief; the reviewer sits in every review pass that changed code, and on the per-task gate only when `task_review` is `on` or `lane` (the default is `off`). If the repository has a code-index tool, name it in `docs/ai-workflow.md` § Orchestration: workers query it before grepping, and the orchestrator uses it to anchor reviewer briefs. The same shape holds for any language; the values are the repository's.

## Upgrade a repository scaffolded by an earlier version

```text
/sdd-scaffold --upgrade
```

The upgrade re-vendors `tools/sdd-check.py` when the plugin ships a newer copy than `check.version` pins, and fills in any descriptor key the repository lacks. It wraps a hand-written index table in the generated-block markers without dropping a row, and adds `kind:` to the nine files the scaffold emits. A document you wrote yourself keeps its own `kind:`, which you add by hand. Plain `/sdd-scaffold` takes the same path when the descriptor has no `check:` block.

When a hand-written index row has no matching record in `traceability.yaml`, `generate` refuses to drop it: the run writes nothing and names the row. Capture the requirement with `/sdd-specify`, or delete the stale row by hand, then run again. A note inside the markers is refused the same way; move it outside them.

What each release changed, and what to do by hand, is in [docs/upgrading.md](upgrading.md).

## Draft a gap for an upstream repository

Advanced, and only when `docs/.sdd.yaml` declares an `upstream` that also practises SDD.

```text
/sdd-specify draft an upstream gap: the SDK needs a refresh-token grant
```

The draft is written in the upstream's conventions (its identifier style, RFC-2119, acceptance criteria), so it drops straight into the upstream's spec tree. It is stored locally, and its lifecycle is tracked. The rules are in [cross-repo-gap.md](../references/cross-repo-gap.md). For anything the repository consumes, the upstream's semantics are ground truth and the local documents are corrected, never the other way round.

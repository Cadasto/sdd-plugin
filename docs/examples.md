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
/sdd-review --lane full
```

The review decides the lane by asking whether a normative statement changed meaning, and reads the answer from the changed document lines. Here one did, so the conformance and document reviewers run alongside the repository's own.

Check: the pull request body carries `Lane: full`, and the spec section's status is not lagging behind the code.

## Refactor with no behaviour change

Maintenance lane: no requirement and no spec edit.

```text
/sdd-review --lane maintenance
```

On the maintenance lane the reviewers named in `agents.reviewers` read the code, and `sdd-doc-reviewer` reads any changed document to check that it still agrees with the code and the other documents. The conformance reviewer is skipped, because no binding sentence may change on this lane. If nothing in the range calls for a reviewer (say `agents.reviewers` is empty and only code changed), the pass writes no `Reviewed` line and the range stays open, and your own review of the pull request is the pass. The pull request body's *Spec and traceability* section carries `Lane: maintenance — no normative change`.

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
Does the token refresh handler satisfy SPEC-AUTH §3, clause by clause?
```

The `sdd-spec-conformance-reviewer` agent runs the tests each clause names and removes each touched guard in a scratch worktree; a test that stays green is a critical finding with both runs as evidence. It judges conformance, not code quality; the repository's own language reviewer does that.

```text
Review REQ-AUTH-001 against the requirement contract.
```

The `sdd-doc-reviewer` agent checks the changed hunks for boundary violations: implementation detail in a requirement, a normative sentence duplicated from the canonical section, two sentences that disagree, a missing RFC-2119 keyword.

## Run the outside review panel

```text
/sdd-review --panel
```

Prints one review-request block per name in `agents.review_panel.<lane>`, filled from the repository's `docs/ai-workflow.md` § Review with the commit range to read. Paste each block to the reviewer it names. An outside reviewer working on this machine appends lines to the findings file. One working on the pull request posts inline comments, and `sdd-pr pull` brings them in.

## Work the open findings

```text
/sdd-triage
```

The open critical and important lines of `.sdd/findings/<branch>.md` are the whole to-do list. Each one is checked before it is fixed, the fix lands in this branch, and the line is flipped. An excerpt of the file:

```markdown
# Findings — feat/auth-refresh
Base: main
Reviewed 9c1e2ab · 2026-09-30 · claude: sdd-spec-conformance-reviewer, go-coding:go-reviewer (2 of 2)

## Open
- [ ] important · internal/auth/refresh_test.go:40 · no test for the revoked path · by: maintainer · forge: 5893201111

## Resolved
- [x] critical · internal/auth/refresh.go:88 · a revoked token rotates instead of failing closed (SPEC-AUTH §3) · evidence: TestRefreshRevoked stays green with the check deleted · by: claude · fixed 4f0a1c2

## Suggestions
- internal/auth/refresh.go:120 · rename `tok` to `token` · by: go-coding:go-reviewer
```

And what `sdd-pr status` prints for it:

```text
branch feat/auth-refresh · base main · head 4f0a1c2 · last reviewed 9c1e2ab (code changed since)
open: 0 critical, 1 important · suggestions: 1
- [ ] important · internal/auth/refresh_test.go:40 · no test for the revoked path · by: maintainer · forge: 5893201111
forge: github · PR 7 (draft) · 0 unresolved threads not open in the file · checks: pass
Mergeable: no — 1 important open; the pull request is a draft
Next: /sdd-triage
```

The format and its rules live in [review.md](../references/review.md).

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
    reviewers: [go-coding:go-reviewer]
    task_review: lane
```

Workers load those skills from their brief; the reviewer sits on the per-task gate and in every review pass that changed code. If the repository has a code-index tool, name it in `docs/ai-workflow.md` § Orchestration: workers query it before grepping, and the orchestrator uses it to anchor reviewer briefs. The same shape holds for any language; the values are the repository's.

## Upgrade a repository scaffolded by an earlier version

```text
/sdd-scaffold --upgrade
```

The upgrade re-vendors `tools/sdd-check.py` when the plugin ships a newer copy than `check.version` pins, and fills in any descriptor key the repository lacks. It wraps a hand-written index table in the generated-block markers without dropping a row, and adds `kind:` to the nine files the scaffold emits. A document you wrote yourself keeps its own `kind:`, which you add by hand. Plain `/sdd-scaffold` takes the same path when the descriptor has no `check:` block.

When a hand-written index row has no matching record in `traceability.yaml`, `generate` refuses to drop it: the run writes nothing and names the row. Capture the requirement with `/sdd-specify`, or delete the stale row by hand, then run again. A note inside the markers is refused the same way; move it outside them.

From 0.7.x the upgrade also proposes the 0.8.0 changes: drop the plans path, rename `profile: full` to `formal`, ignore `.sdd/`, and re-emit the process documents. Each is applied only when you say yes. The full procedure is in [docs/upgrading.md](upgrading.md).

## Draft a gap for an upstream repository

Advanced, and only when `docs/.sdd.yaml` declares an `upstream` that also practises SDD.

```text
/sdd-specify draft an upstream gap: the SDK needs a refresh-token grant
```

The draft is written in the upstream's conventions (its identifier style, RFC-2119, acceptance criteria), so it drops straight into the upstream's spec tree. It is stored locally, and its lifecycle is tracked. The rules are in [cross-repo-gap.md](../references/cross-repo-gap.md). For anything the repository consumes, the upstream's semantics are ground truth and the local documents are corrected, never the other way round.

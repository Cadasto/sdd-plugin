# Prompt examples

Recipes for a repository that is already scaffolded — one goal each, the prompt to type, what happens, and what to check. New to the plugin? Start with the [quick start](quick-start.md).

Every `/sdd-*` skill also triggers on plain phrasing — the phrases quoted in its description, such as "add a requirement" or "cut the release" — so the slash form is a convenience, not a requirement. The example repository issues API tokens; its requirements use the `AUTH` area and its spec is `SPEC-AUTH`.

## Ask where a statement belongs

```text
Should "a refresh with a revoked token fails closed" be a requirement or a spec section?
```

The router skill answers without touching a file: the requirement names the observable outcome as an acceptance criterion, the spec section owns the normative *how* — the `MUST NOT`, the error contract. It then points at `/sdd-specify`. Use it whenever you are unsure which document kind you are about to write.

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

One decision per ADR, next sequential number, `status: proposed`. When you have decided, set it to `accepted` in the file — the dispatch gate refuses to start delivery on a `proposed` ADR.

Check: `docs/adr/README.md` has the row; the ADR cites the requirements it amends.

## Fix a bug that proves the spec wrong

The code did one thing, the spec said another, and the spec was wrong. This is implementation-aligned work on the full lane: the fix and the spec amendment ride in the same pull request.

```text
/sdd-specify amend SPEC-AUTH §3: a refresh with a revoked token MUST return 401 and MUST NOT rotate the token
```

Fix the code on the same branch, open the pull request, then:

```text
/sdd-review <N> --post
```

The review reads the `Lane:` line and corroborates it against the diff. Edits under `docs/specifications/` make the change full lane whatever the line says, so the spec reviewers are dispatched too.

Check: the pull request body carries `Lane: full`, and the spec section's status is not lagging behind the code.

## Refactor with no behaviour change

Maintenance lane: no requirement, no spec edit, no plan file committed.

Open the pull request with this line in its body, taken from the repository's `docs/development-process.md`:

```text
Lane: maintenance — no normative change
```

Then:

```text
/sdd-review <N> --post
```

On the maintenance lane only the reviewers named in `agents.reviewers` are dispatched — there is no spec delta for the SDD reviewers to read. If that list is empty, the ledger's accounting line reads `Dispatched: none — agents.reviewers is empty · Reported: 0 of 0` and the ledger is not marked clean. Your own review of the pull request then stands as the panel and clears it.

The lane is guarded by a ratchet, not a diff check: a reviewer that finds a new rule living only in code flags it, and the change becomes full lane. `make spec-check` runs in both lanes.

## Find what implements a requirement

```text
/sdd-trace REQ-AUTH-001
```

One bundle: the index row, the traceability record, the canonical spec section, and any open `STRAND` touching the requirement. Report-only.

```text
/sdd-trace
```

With no argument, a drift scan of the whole map against the tree, grouped by orphan class — a canonical link to a missing anchor, a listed test that does not exist, a requirement marked `shipped` with no packages. When `spec-check` fails in CI and the cause is unclear:

```text
Run a whole-repo traceability audit before we tag the release.
```

That dispatches the `sdd-traceability-auditor` agent in its own context and returns a ranked report. Nothing is edited.

## Check code against the spec it cites

```text
Does the token refresh handler satisfy SPEC-AUTH §3, clause by clause?
```

The `sdd-spec-conformance-reviewer` agent returns one verdict per clause — satisfied, violated, or untested — ranked by RFC-2119 force. It judges conformance, not code quality; the repository's own language reviewer does that.

```text
Review REQ-AUTH-001 against the requirement contract.
```

The `sdd-doc-reviewer` agent checks one document for boundary violations: implementation detail in a requirement, a task list in a spec, a normative sentence duplicated from the canonical section, a missing RFC-2119 keyword.

## Run the outside review panel

```text
/sdd-review <N> --panel
```

Prints one review-request block per name in `agents.review_panel.<lane>`, filled from the repository's `docs/ai-workflow.md` § Review. Paste each block to the reviewer it names — nothing in the repository can start a reviewer that runs outside it. The reviewer's findings come back in the ledger format, and `/sdd-triage` merges them.

## Work a review round

```text
/sdd-triage <N>
```

Every comment channel on the pull request is read, findings are merged under `F<n>` ids, each is verified before it is fixed, the fixes land in this pull request, and the ledger comment is updated in place. An excerpt of the result:

```markdown
## Review ledger — round 1 (claude, 2026-09-07)
Dispatched: sdd-spec-conformance-reviewer, go-coding:go-reviewer · Reported: 2 of 2
| id | severity | anchor | finding | status |
|---|---|---|---|---|
| F4 | blocker | internal/auth/refresh.go:88 | revoked token rotates instead of failing closed (SPEC-AUTH §3) | fixed@9c1e2ab |
| F5 | should-fix | internal/auth/refresh_test.go:40 | no test for the revoked path | fixed@9c1e2ab |
```

The format and its rules live in [artefact-prose.md](../references/artefact-prose.md). To request a re-review of only the new fixes:

```text
/sdd-triage <N> --from F4
```

## Resume an interrupted delivery

```text
/sdd-deliver <N>
```

Given a pull request number, the skill reads the draft's body — the claim line and the plan path — and the plan file on the branch, and continues at the first unfinished step. A claim line that names a different session stops it: two sessions on one branch means one of them is thrown away.

## Configure a Go repository

The plugin dispatches only the reviewers the descriptor names and briefs workers with only the skills it lists. For a Go repository with the go-coding plugin installed, `docs/.sdd.yaml` carries:

```yaml
sdd:
  agents:
    worker_skills: [go-coding:go-coding, go-coding:go-testing]
    reviewers: [go-coding:go-reviewer]
    task_review: lane
```

Workers load those skills from their brief; the reviewer sits on the per-task gate and on the review panel in both lanes. If the repository has a code-index tool, name it in `docs/ai-workflow.md` § Orchestration — workers query it before grepping, and the orchestrator uses it to anchor reviewer briefs. The same shape holds for any language; the values are the repository's.

## Sweep plans at a release

```text
/sdd-finalize --dry-run
```

Lists every plan with `status: done` or `abandoned`. A refusal names the document that still links to a candidate — for example `docs/ci.md` citing a plan path. Rewrite the citation to the pull request or the requirement, then:

```text
/sdd-finalize
```

The first run in a repository that still has a `docs/plans/archive/` directory sweeps it under the same status test and removes the directory once it is empty. `active` and `postponed` plans are never touched.

## Draft a gap for an upstream repository

Advanced, and only when `docs/.sdd.yaml` declares an `upstream` that also practises SDD.

```text
/sdd-specify draft an upstream gap: the SDK needs a refresh-token grant
```

The draft is written in the upstream's conventions — its identifier style, RFC-2119, acceptance criteria — so it drops straight into the upstream's spec tree, and it is stored locally with its lifecycle tracked. The rules are in [cross-repo-gap.md](../references/cross-repo-gap.md). For anything the repository consumes, the upstream's semantics are ground truth and the local documents are corrected, never the other way round.

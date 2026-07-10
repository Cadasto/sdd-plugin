---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this PR/change for spec conformance", "dispatch the reviewers and post findings to the PR", or "spec-aware code review before merge". Opt-in orchestration — dispatches the installed generic code reviewers plus the SDD traceability auditor and spec-conformance reviewer, consolidates the findings, and (optionally) posts them to the PR. It sequences and adds the SDD lens; it does not replace generic review. Not for authoring (sdd-specify), the in-session drift-only scan (sdd-trace), or whether the tests pass (superpowers verification-before-completion).
argument-hint: "[REQ-id or plan file] [--post to comment on the PR]"
allowed-tools: Task, Bash, Read, Grep, Glob
---

# Review — orchestrate a spec-aware review and post it to the PR

> **Bundled `references/` is at the plugin root** (beside `skills/`, two levels above this file) — *not* under this skill. Read any `references/…` path as `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or `../../references/…` from this skill's directory, or Glob for the installed `references/…` (host-agnostic).

An **opt-in** convenience that runs at the end of an implementation slice. It does **not** own code review — it *sequences* the reviewers you already have and adds the two lenses only SDD can: traceability and spec conformance. Invoke it deliberately (it is not an automatic gate); read `docs/.sdd.yaml` first for `paths.*` and the build targets.

## Steps

0. **Scope the change.** Resolve the `REQ`/`SPEC §`/plan under review (from the argument, the plan header, or the PR/commit citation) and the PR (`gh pr view`). The review scope is the branch diff against its base.
1. **Generic review — delegate, don't reimplement.** Run whichever generic reviewer is installed: the built-in `/code-review --comment`, `superpowers:requesting-code-review`, or the `pr-review-toolkit` (`/review-pr`). This covers bugs, style, security, tests. If none is installed, say so and skip this step — do **not** hand-roll a generic reviewer here.
2. **SDD lens — dispatch read-only agents (in parallel).**
   - `sdd-traceability-auditor` — map-vs-tree drift and orphans across the touched chain.
   - `sdd-spec-conformance-reviewer` — does the code satisfy the `SPEC §` / `REQ` acceptance criteria it cites, clause by clause.
   Both are read-only and return severity-ranked findings; neither edits.
3. **Consolidate.** Merge the findings; dedupe against the generic reviewer's; rank blockers first (unmet MUST, duplicated normative prose, broken `canonical` link) and drop nits. Keep the write-up economical per `references/artefact-prose.md`.
4. **Post (if `--post`, or when asked).** Post to the PR: one comment per finding, anchored to `file:line`, citing the `SPEC §` / finding it concerns — terse and identifier-anchored (`references/artefact-prose.md`). Use the generic reviewer's `--comment` path, or `gh pr comment` / `gh pr review`. Without `--post`, present the consolidated report in-session and name the next action.

## Guardrails

- **Opt-in, not a gate.** Run it when asked; do not auto-fire it after every implementation. The fix-and-resolve loop (reply "resolved in `<sha>`", resolve the thread) is `superpowers:receiving-code-review` + the resolution-comment rule in `references/artefact-prose.md`.
- **Delegate the mechanics.** Generic review and the comment-posting mechanic belong to the installed tools / `gh`; this skill only *sequences* them and adds the SDD lenses. Don't reimplement either — see `references/sdd-with-superpowers.md`.
- **Read-only dispatch.** The dispatched agents never edit; applying fixes is the author's job (or the owning `sdd-*` skill for spec/index/traceability).
- **Not the test gate.** Whether tests/build/lint pass is `superpowers:verification-before-completion`; this skill reviews conformance and traceability, not green-ness.
- **Economical comments.** One finding per comment; cite the identifier; no essays or re-litigation (`references/artefact-prose.md`).

## Reference

- `references/artefact-prose.md` — how a review/resolution comment reads (terse, identifier-anchored).
- `references/sdd-with-superpowers.md` — who owns generic review, verification, and branch-finishing.
- The agents: `sdd-spec-conformance-reviewer` (code vs spec) and `sdd-traceability-auditor` (map vs tree).

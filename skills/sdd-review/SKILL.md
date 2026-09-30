---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this branch", "review this PR", or "print the review prompts for the panel". Reviews the commits since the last pass with the reviewers the profile, lane and changed files call for, writes the findings into the branch's findings file, and mirrors critical and important ones to the pull request when there is one. Not for fixing findings (sdd-triage) or authoring documents (sdd-specify).
argument-hint: "[--lane full|maintenance] [--all] [--panel] [--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Review — one pass into the findings file

> `references/…` and `tools/…` resolve from the plugin root: `${CLAUDE_PLUGIN_ROOT}/…` on Claude Code, or Glob for the installed copy. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first (`profile`, `paths.*`, `forge`, the build targets, `agents:`); without a descriptor or an `agents:` block, route to `/sdd-scaffold` and stop. What a finding must meet is `references/review.md`. No pull request is required. Pass `--pr N`, when given, to every `sdd-pr` call.

## Steps

1. **Scope.** With a pull request, `sdd-pr pull` first, so the maintainer's threads are in the file. Then `sdd-pr scope` (`--all` for the whole branch, only when the maintainer asks): the range since the last `Reviewed` line, or the whole branch on the first pass, and the changed paths by kind. `range: empty`: print `sdd-pr status` and stop.
2. **Lane (formal profile only).** From the PR body's `Lane:` line, or `--lane`. The test is methodology §12 — did a normative statement change meaning? — answered from the range's document hunks, never from a path. `--lane maintenance` on an existing PR limits this pass and does not rewrite the body.
3. **Dispatch, by profile and by what changed.** Each dispatch gets the range, `git diff <range> -- <its paths>`, the profile, the sentences under review and the file's `## Resolved` lines. Report-only, in parallel:
   - code, tests or other files (build, CI, configuration) changed → each reviewer in `agents.reviewers`, told to run the tests it needs for evidence;
   - formal, full lane, code implementing a cited `SPEC §` changed → `sdd-spec-conformance-reviewer`, once, with the guard-removal check for every MUST in the range; informative → the same agent only when the range touches something a constitution sentence binds, with those sentences quoted;
   - formal full lane or informative, a document changed → `sdd-doc-reviewer`, once, with the changed hunks of every touched document (form on formal, consistency on informative);
   - nothing else: the drift gate ran in the full gate; the auditor is `/sdd-trace --audit`.
   A dispatch that died is re-run once; a second death shows in the `Reviewed` line's `(<n> of <m>)`.
4. **Merge into the file** `.sdd/findings/<branch-slug>.md` (created from the grammar in `review.md` when absent): critical and important under `## Open`, suggestions under `## Suggestions` (at most ten new, then "and n more"). Merge two lines about one defect, naming both in `by:`; drop a line with nothing in the range and no evidence. Add `Reviewed <HEAD sha> · <date> · <agent>: <reviewers> (<n> of <m>)`.
5. **Mirror.** With a pull request, push, then `sdd-pr post` (it refuses an unpushed HEAD). Then `sdd-pr status`.
6. **Panel prompts (`--panel`).** Print one block per name in `agents.review_panel.<lane>` (`full` on the informative profile), filled from the repository's `docs/ai-workflow.md` § Review with the range from step 1. An outside reviewer on this machine appends to the findings file; one elsewhere posts inline threads, which `sdd-pr pull` brings in.

## Guardrails

- **Run it once before the maintainer's review, and once after the triage of that review when it changed code (`references/review.md` § Passes) — never after every slice.**
- **The agents edit nothing; this skill writes only the findings file; `/sdd-triage` fixes.**
- **Never a summary comment on the pull request; never a second pass over the same range.**
- **The build gate is not this skill; read its output before claiming green.**

## Reference

- `references/review.md` — the findings file, severity, scope, evidence, the mirror, the tool.
- `references/sdd-methodology.md` — §1a the profiles, §12 the lanes, §13 the merge gate and the pass budget.
- The agents: `sdd-spec-conformance-reviewer`, `sdd-doc-reviewer`, and those `agents.reviewers` names.

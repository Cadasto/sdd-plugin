---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this branch", "review this PR", or "print the review prompts for the panel". Reviews the commits since the last pass with the reviewers the profile, lane and changed files call for, writes the findings into the branch's findings file, and mirrors critical and important ones to the pull request when there is one. Not for fixing findings (sdd-triage) or authoring documents (sdd-specify).
argument-hint: "[--lane full|maintenance] [--all] [--panel] [--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Review — one pass into the findings file

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` and `tools/…` resolve from it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first (`profile`, `paths.*`, `forge`, the build targets, `agents:`); without a descriptor or an `agents:` block, route to `/sdd-scaffold` and stop. What a finding must meet is `references/review.md`. No pull request is required. Pass `--pr N`, when given, to every `sdd-pr` call.

## Steps

1. **Scope, before reading any reference.** With a pull request, `sdd-pr pull` first, so the maintainer's threads are in the file. Then `sdd-pr scope --agent <host>`: the range since this host's last pass, or the whole branch on its first, the changed paths by kind, and which reviewer reads each code path. On a stacked branch's first pass add `--base <parent>`; `--all` for the whole branch only when the maintainer asks. `range: empty`: print `sdd-pr status` and stop.
2. **Lane (formal profile only).** From the PR body's `Lane:` line, or `--lane`. The test is methodology §12 — did a normative statement change meaning? — answered from the range's document hunks, never from a path. `--lane maintenance` on an existing PR limits this pass and does not rewrite the body.
3. **Dispatch, by profile and by what changed.** Each dispatch gets the range, the hunks `sdd-pr scope --diff <kind or reviewer>` prints (never a diff built by hand), the profile, the sentences under review and the file's `## Resolved` lines. Report-only, in parallel:
   - code, tests or other files (build, CI, configuration) changed → each `reviewer` line of `scope`, with its paths, told to run the tests it needs for evidence; `vendored:` (the upstream gate) and `plans:` go to no one, and `no reviewer:` paths are said in the hand-back;
   - formal, full lane, code implementing a cited `SPEC §` changed, or a MUST or SHOULD sentence changed with no code → `sdd-spec-conformance-reviewer`, once, with the guard-removal check for every MUST in the range, and for a sentence alone the code and tests it describes; informative → the same agent only when the range touches something a constitution sentence binds, with those sentences quoted;
   - a document changed → `sdd-doc-reviewer`, once, with the changed hunks of every touched document: form on the formal full lane; consistency with the code and the other documents on the maintenance lane and the informative profile;
   - nothing else: the drift gate ran in the full gate, and `python3 <check.script> check --changed-since <base> --new-only` shows what the range added (a new warning is a suggestion, a new error critical); the auditor is `/sdd-trace --audit`.
   A dispatch that died, or returned `MISMATCH`, is re-run once, with the diff rebuilt from this checkout; a second failure shows in the `Reviewed` line's `(<n> of <m>)`. A range that called for no reviewer gets no `Reviewed` line: say so and leave it open for the maintainer's own review (`review.md` § The findings file).
4. **Write the file with `sdd-pr`, never by hand.** Drop a line about nothing in the range, keep at most ten new suggestions ("and n more"), then pipe each reviewer's fence to `sdd-pr add -`: it checks the grammar, refuses a blocking line without evidence and folds a second line about one defect into the first. Then `sdd-pr record --agent <host> --reviewers <names> --reported <n>/<m>`; with nothing reported, record nothing.
5. **Mirror.** With a pull request, push, then `sdd-pr post` (it refuses an unpushed HEAD). Then `sdd-pr status`.
6. **Panel prompts (`--panel`).** Print one block per name in `agents.review_panel.<lane>` (`full` on the informative profile), filled from the repository's `docs/ai-workflow.md` § Review with the range from step 1. An outside reviewer on this machine pipes its lines to `sdd-pr add -`; one elsewhere posts inline threads, which `sdd-pr pull` brings in.

## Guardrails

- **Run it once before the maintainer's review, and once after the triage of that review when it changed anything, a document included (`references/review.md` § Passes) — never after every slice.**
- **The agents edit nothing; this skill writes only the findings file; `/sdd-triage` fixes.**
- **Never a summary comment on the pull request; never a second pass over the same range.**
- **The build gate is not this skill; read its output before claiming green.**

## Reference

- `references/review.md` — the findings file, severity, scope, evidence, the mirror, the tool.
- `references/sdd-methodology.md` — §1a the profiles, §12 the lanes, §13 the merge gate and the pass budget.
- The agents: `sdd-spec-conformance-reviewer`, `sdd-doc-reviewer`, and those `agents.reviewers` names.

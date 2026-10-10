---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this branch", "review this PR", "give a second opinion", or "print the review prompts for the panel". Reviews the whole branch, or only what is new with --since-last, with the reviewers the profile, lane and changed files call for, writes the findings into the branch's findings file, and mirrors them to the pull request when there is one. Not for fixing findings (sdd-triage) or authoring documents (sdd-specify).
argument-hint: "[--lane full|maintenance] [--since-last] [--panel] [--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Review — one pass into the findings file

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` and `tools/…` resolve from it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first (`profile`, `paths.*`, `forge`, the build targets, `agents:`); without a descriptor or an `agents:` block, route to `/sdd-scaffold` and stop. Pass `--pr N` to every `sdd-pr` call; no pull request is required.

## Steps

1. **Scope, before reading any reference.** Another's pull request is reviewed at its published head: when the local HEAD differs, say so and stop. With a pull request, `sdd-pr pull` first, so the maintainer's threads are in the file. Then `sdd-pr scope --start <agent>` (`<agent>`: host and model, `claude-opus-5-5`), adding `--since-last` when given (the commits since the last pass, whoever made it) and, on a stacked branch's first pass, `--base <parent>`. It prints the paths by kind and each code path's reviewer. `pass: running`: another session is reviewing; stop and ask. `range: empty`: print `sdd-pr status` and stop.
2. **Lane (formal profile only).** `--lane` (this pass only; the body is not rewritten), else the PR body's `Lane:` line, else methodology §12's test on the range's document hunks, never a path: did a normative statement change meaning? `normative lines changed: 0` points to maintenance.
3. **Dispatch, by profile and by what changed.** Model: the session's, or a cheaper one for the code and document reviewers on the maintenance lane. Reuse the full gate's log at HEAD, `.sdd/gate-<short head>.log`, else write it with `<build_entrypoint> <ci_target>`. Each dispatch names its agent and gets paths, not pasted diffs: that log, its hunks (`sdd-pr scope` with step 1's flags and `--diff <kind or reviewer> > .sdd/diff-<name>.patch`), `sdd-pr`'s full path, plus the range, the profile, the sentences under review and the file's `## Resolved` lines (not the open ones: opinions stay independent); a reviewer runs a test only to pin a failure the log lacks. Report-only, in parallel:
   - code, tests or other files (build, CI, configuration) changed → each `reviewer` line of `scope`, with its paths, told that a defect in code the branch did not change keeps its severity, marked `outside`; `vendored:` and `plans:` go to no one, and `no reviewer:` paths are said in the hand-back;
   - formal, full lane, code implementing a cited `SPEC §` changed, or a MUST or SHOULD sentence changed with no code → `sdd-spec-conformance-reviewer`, once, which proves each MUST and MUST NOT in the range with `sdd-pr guard`, and for a sentence alone reads the code and tests it describes; informative → the same agent only when the range touches something a constitution sentence binds, with those sentences quoted;
   - a document changed → `sdd-doc-reviewer`, once: form on the formal full lane; consistency on the maintenance lane and the informative profile;
   - the drift gate → no dispatch: `sdd-check check --changed-since <the start of scope's range> --new-only` (`references/sdd-check.md`) shows what the range added (a new warning is a suggestion, a new error critical).
   A dispatch that died, or returned `MISMATCH`, is re-run once, with the diff rebuilt from this checkout; a second failure shows in the `Reviewed` line's `(<n> of <m>)`.
4. **Write the file with `sdd-pr`, never by hand.** Settle each claim of wrong code behaviour (`references/review.md` § Severity): file it by its harm, `outside` when the branch did not change it, or drop it. Merge two lines about one defect, naming both in `by:`; pipe a defect the file holds in that line's words, so `add` folds it; drop a suggestion that is no lead, listed in the hand-back. Then pipe each reviewer's fence to `sdd-pr add -`, and `sdd-pr record --agent <agent> --reviewers <names> --reported <n>/<m>`. With nothing dispatched or reported, the same `record` with `--reported 0/<m>` refuses a line (exit 2) but ends the pass: say so, and leave the range to the maintainer's own review.
5. **Mirror.** With a pull request, push the branch unless it is another's, then `sdd-pr post`: the pass's one review, clean or not, and its new suggestions in one comment. Then `sdd-pr status`.
6. **Panel prompts (`--panel`).** Step 1 without `--start`, then this step alone: print one block per name in `agents.review_panel.<lane>` (`full` on the informative profile), filled from the repository's `docs/ai-workflow.md` § Review with the range from step 1, the branch and the plugin root. An outside reviewer on this machine pipes its lines to `sdd-pr add -`; one elsewhere posts inline threads, which `sdd-pr pull` brings in.

## Guardrails

- **Passes are budgeted (`references/review.md` § Passes); never one after every slice.**
- **The agents edit nothing; this skill changes no tracked file; `/sdd-triage` fixes.**
- **Nothing on the pull request but what `sdd-pr post` writes; a second opinion only when the maintainer asks.**

## Reference

- `references/review.md` — the findings file, severity, scope, evidence, the mirror, the tool.
- `references/sdd-methodology.md` — §1a the profiles, §12 the lanes, §13 the merge gate and the pass budget.

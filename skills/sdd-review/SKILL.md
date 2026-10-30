---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this branch", "review this PR", or "give a second opinion". Reviews the whole branch, or only what is new with --since-last, with the reviewers the profile, lane and changed files call for, writes the findings into the branch's findings file, and mirrors them to the pull request when there is one. Not for fixing findings (sdd-triage) or authoring documents (sdd-specify).
argument-hint: "[--lane full|maintenance] [--since-last] [--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Review — one pass into the findings file

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code): take it from this file's own path, `\` turned into `/`, and never search the disk for it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

`sdd-pr start` (step 1) reads `docs/.sdd.yaml`. No descriptor, or no `agents:` block (`start` says so): route to `/sdd-scaffold` and stop. Pass `--pr N` to every `sdd-pr` call; no pull request is required.

## Steps

1. **Start, before reading any reference or file.** `sdd-pr start --agent <agent>` (`<agent>`: host and model, `claude-opus-5-5`), adding `--pr N` and `--lane` when given, `--base <parent>` on a stacked branch's first pass, and `--since-last` only when the maintainer asks: the whole branch otherwise, even after an earlier pass. In one call it pulls the pull request's threads, notes the pass, settles the lane, writes each reviewer's hunks, the drift gate's new lines and one shared brief, and prints the dispatch plan; it never runs the gate. A refusal names what to do. `range: empty`: print `sdd-pr status` and stop. Another agent's pass is reported, not a stop: this one runs beside it.
2. **Lane (formal profile only).** A lane the maintainer named, or the PR body carries, is final. When `start` prints `lane decide`, apply methodology §12's test to the range's document hunks, never a path: was an obligation added or a contract widened? `normative lines changed: 0`, or only a sentence corrected to the behaviour the change fixes, points to maintenance. The lane holds for this pass; the PR body is not rewritten.
3. **Dispatch the plan, in parallel, report-only.** One dispatch per plan line, naming its agent, with the prompt "Read `<brief>`; your hunks: `<patch>`" and nothing pasted: no diff, file or agent text, and read none of them first. Model: a model the maintainer named wins; otherwise the session's, and, where the host lets a dispatch pick one, a cheaper one for `sdd-doc-reviewer` and for the code reviewers on the maintenance lane. Keep the plan's conditions:
   - each repository reviewer → dispatched; `no reviewer:` paths are said in the hand-back;
   - `sdd-spec-conformance-reviewer` → formal full lane, when the code implements a cited `SPEC §` or a new obligation was written with no code (it then reads the code and tests the sentence describes); add the cited ids to its prompt when known; informative → only when the range touches what a constitution sentence binds, those sentences quoted;
   - `sdd-doc-reviewer` → only when the plan lists it (formal: a normative line, a requirement or an ADR changed), form or consistency, as the plan says;
   - the drift gate's new lines → no dispatch: a new warning is a suggestion, a new error critical.
   A dispatch that died, or returned `MISMATCH`, is re-run once after `sdd-pr start` again; a second failure shows in the `Reviewed` line's `(<n> of <m>)`.
4. **Write the file with `sdd-pr`, never by hand.** Settle each claim of wrong code behaviour ([review.md § Severity](../../references/review.md#severity)): file it by its harm, `outside` when the branch did not change it, or drop it; one is never filed as a suggestion. Merge two lines about one defect, naming both in `by:`; pipe a defect the file holds in that line's words, so `add` folds it; drop a suggestion that is no lead or past the cap of five per reviewer, listed in the hand-back. Save the document reviewer's fix list, when it returned one, to `doc-fixes.md` beside the brief and name its path and count in the hand-back; `/sdd-triage` applies it, never this pass. Then pipe each reviewer's fence to `sdd-pr add -`, and `sdd-pr record --agent <agent> --reviewers <names> --reported <n>/<m>`. With nothing dispatched or reported, the same `record` with `--reported 0/<m>` refuses a line (exit 2) but ends the pass: say so, and leave the range to the maintainer's own review.
5. **Mirror.** With a pull request, push the branch from its checkout unless it is another's, then `sdd-pr post` ([review.md § The forge mirror](../../references/review.md#the-forge-mirror)), then `sdd-pr status`.

## Guardrails

- **Passes are budgeted ([review.md § Passes](../../references/review.md#passes)); never one after every slice.**
- **The agents edit nothing; this skill changes no tracked file; `/sdd-triage` fixes.**
- **Nothing on the pull request but what `sdd-pr post` writes; a second opinion only when the maintainer asks.**

## Reference

- [review.md](../../references/review.md) — the findings file, severity, scope, evidence, the mirror, the tool.
- [sdd-methodology.md](../../references/sdd-methodology.md) — §1a the profiles, §12 the lanes, §13 the merge gate and the pass budget.

---
name: sdd-triage
description: This skill should be used when the user asks to "triage the review", "work through the findings", "fix what the reviewers found", or "resolve the open findings". Works the open findings of one branch to the end — verifies each, lands the fixes, flips the lines, mirrors to the pull request, and runs one scoped re-review when code changed. Not for producing a review (sdd-review) or the close-out (sdd-deliver --close-out).
argument-hint: "[--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Triage — work the open findings to the end

> `references/…` and `tools/…` resolve from the plugin root: `${CLAUDE_PLUGIN_ROOT}/…` on Claude Code, or Glob for the installed copy. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first for `profile`, `forge`, the build targets and the `agents:` block. Run this in the orchestrator session: triage is judgement. What counts, what a resolution says and how many passes a branch gets are `references/review.md` and methodology §13. This file is the procedure.

## Steps

1. **List what is open.** With a pull request, `sdd-pr pull --pr <N>` first. Then `sdd-pr status`: the open critical and important lines of `.sdd/findings/<branch-slug>.md` are the whole enumeration. Suggestions are not on it.
2. **Verify each.** A finding is a claim, and so is its proposed fix. Check both against the code and the sentences it cites; when the claim is about behaviour, run the code. A wrong claim is declined in the file — `- [-] … · declined: <reason>` under `## Resolved` — and never argued in a thread. When the maintainer says a decline should hold for future changes, write it where decisions live (a `SPEC §` sentence or ADR on the formal profile, a constitution sentence on the informative one), through `/sdd-specify`.
3. **Decide what this branch fixes.** Every open critical and important line is fixed here. When one should not be, ask the maintainer by name; only the maintainer defers, and a deferred finding leaves the file for `implementation: deferred` on its requirement or a *Known gaps* line in the specification. Never work a suggestion unless the maintainer names it. A fix that adds a binding sentence owes a test that fails without its guard; environment behaviour stays informative (`review.md` § Keywords).
4. **Fix.** A sentence, a map row, a test row, a few lines: edit in-session and commit. Anything larger: brief one `sdd-implementer` from `references/templates/brief.md`, its `Finding` field carrying the line. `agents.task_review` does not apply to triage fixes. Never hand-edit a generated block: change the map or the frontmatter and run `sdd-check generate`. Commit messages say what changed and cite the `REQ` / `SPEC §` or constitution section, never a finding.
5. **Gate, flip, mirror.** Run `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` and read the output; push when there is a remote; flip each fixed line to `- [x] … · fixed <sha>` under `## Resolved`; with a pull request, `sdd-pr resolve --pr <N>`.
6. **Re-review, once, scoped.** When the fixes changed code or tests, run `/sdd-review`: it reads only the range since the last `Reviewed` line and dispatches only the reviewers whose file kinds changed. Prose-only changes get no re-review. Then `sdd-pr status`; its `Next:` line is the hand-back.
7. **Stop rule.** On a pull request already marked ready, one triage pass may trigger one re-review. A further pass runs only for a new critical finding; for anything else, stop and show the maintainer the open list.

## Guardrails

- **The findings file is the enumeration. Never rebuild the open list from memory or from a pull-request comment.**
- **Nothing is flipped before its fix is pushed or its decline is written.**
- **A fix names no finding: the file and the thread reply carry the commit; the base branch never learns one.**

## Reference

- `references/review.md` — severity, evidence, resolution, the mirror, the tool.
- `references/sdd-methodology.md` §13 — verify before fixing, collapse before you add, decisions go where decisions live, the pass budget.
- `references/templates/brief.md` — the worker brief for a fix that is not a small edit.

---
name: sdd-triage
description: This skill should be used when the user asks to "triage the review", "work through the findings", "fix what the reviewers found", "address the review comments", or "resolve the open findings". Works a branch's open findings to the end — verify, fix, flip the lines, mirror, and, after the maintainer's review, one scoped re-review when anything changed. Not for producing a review (sdd-review) or the close-out (sdd-deliver --close-out).
argument-hint: "[--pr N]"
allowed-tools: Agent, Task, Bash, Read, Write, Edit, Grep, Glob
---

# Triage — work the open findings to the end

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` and `tools/…` resolve from it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first (`profile`, `forge`, the build targets, `agents:`). Run it in the orchestrator session: triage is judgement. `references/review.md` and methodology §13 say what counts, what a resolution says and how many passes a branch gets. Pass `--pr N`, when given, to every `sdd-pr` call.

## Steps

1. **List what is open.** With a pull request, `sdd-pr pull` first. Then `sdd-pr status`: the open critical and important lines of the branch's findings file, each with the `#key` that `sdd-pr flip` takes, are the whole enumeration; suggestions are listed but not worked. Every change to the file goes through `sdd-pr` (`references/review.md` § The tool).
2. **Verify each.** A finding is a claim, and so is its proposed fix. Check both against the code and the sentences it cites, running the code for a claim about behaviour. A wrong claim is declined in the file — `sdd-pr flip <#key> --declined "<reason>"` — and never argued in a thread. A decline the maintainer says should hold for future changes is written where decisions live, through `/sdd-specify`: a `SPEC §` sentence or ADR (formal), a constitution sentence (informative).
3. **Decide what this branch fixes.** Every open critical and important line is fixed here. When one should not be, ask the maintainer by name: only the maintainer defers. Record the deferral (`implementation: deferred` on its requirement, or a *Known gaps* line), then `sdd-pr flip <#key> --deferred "<where>"`, or `--deferred "dropped by the maintainer"`. Never work a suggestion unless the maintainer names it. A fix that adds a binding sentence owes a test that fails without its guard; environment behaviour stays informative (`review.md` § Keywords).
4. **Fix.** A sentence, a map row, a test row, a few lines: edit in-session and commit. Anything larger: brief one `sdd-implementer` from `references/templates/brief.md`, its `Finding` field carrying the line. `agents.task_review` does not apply to triage fixes. Never hand-edit a generated block: change the map or the frontmatter and run `sdd-check generate`. Commit messages say what changed and cite the `REQ` / `SPEC §` or constitution section, never a finding.
5. **Gate, flip, mirror.** Run `<build_entrypoint> <ci_target>` and `<build_entrypoint> <spec_check_target>` and read the output; push when there is a remote; `sdd-pr flip <#key> --fixed <sha>` for each fixed line; with a pull request, `sdd-pr resolve`.
6. **Re-review, once, scoped — only after the maintainer's review.** The maintainer has reviewed once `sdd-pr pull` brought in their threads or they say so; when unsure, ask. When fixes after that review changed anything, a document included, run `/sdd-review --since-last`, which reads only the new commits and dispatches only the reviewers whose file kinds changed. Then `sdd-pr status`; its `Next:` line is the hand-back.
7. **Stop rule** (`references/review.md` § Passes). Beyond the budget only a new critical finding or the maintainer reopens review; otherwise stop and show the maintainer the open list. A `Next: /sdd-review` outside it is not a reason to review.

## Guardrails

- **The findings file is the enumeration. Never rebuild the open list from memory or from a pull-request comment.**
- **Nothing is flipped before its fix is pushed (committed, when there is no remote) or its decline or deferral is written.**

## Reference

- `references/review.md` — severity, evidence, resolution, the mirror, the tool.
- `references/sdd-methodology.md` §13 — verify before fixing, collapse before you add, where decisions live, the pass budget.
- `references/templates/brief.md` — the worker brief for a fix that is not a small edit.

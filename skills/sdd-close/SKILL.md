---
name: sdd-close
description: This skill should be used when the user asks to "close out REQ-…", "close out PR N", "write the PR body", "mark the PR ready", "the PR is merged, clean up", or "remove the merged branch and its worktree". Closes out a delivered change in its pull request, fixes the small outside defects and carries the leftover defects to the backlog, and after the merge removes the branch, its worktree and its findings file. Never merges or closes a pull request. Not for delivering (sdd-deliver) or working findings (sdd-triage).
argument-hint: "[PR number | REQ-id | merged branch]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Close — the close-out in the pull request, the clean-up after the merge

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code): take it from this file's own path, `\` turned into `/`, and never search the disk for it; `references/…` and `tools/…` resolve from it. `sdd-pr` below is `python3 <plugin root>/tools/sdd-pr.py`.

Read `docs/.sdd.yaml` first: `profile`, `paths.*`, `forge`, the build targets. No descriptor: route to `/sdd-scaffold` and stop. Given a number, pass `--pr N` to every `sdd-pr` call; a `REQ` id names the requirement step 2 closes.

**Which steps.** On the pull request's branch, `sdd-pr status` decides: open → steps 1 to 4; `Mergeable: merged` → step 5, after steps 2 and 4 on the default branch when the close-out never ran there (the `REQ` not `shipped`, the changelog line missing). On the default branch or another checkout → step 5 alone, asking for the pull request or branch when none was named. With `forge: none`, `status` cannot see a merge: ask the maintainer, or let `sdd-pr clean --dry-run` decide.

## Steps

1. **Nothing blocks.** Close out when `Mergeable:` names no reason but a draft or pending checks; otherwise relay its reasons and its `Next:` line, and stop.
2. **Close out** in the pull request's branch; merged before the close-out, on the default branch or a branch from it, as the maintainer prefers, never on the merged branch. Skip what is already done:
   - formal profile, full lane (the `Lane:` line in the delivery notes or the PR body) — methodology §9's close-out: the `REQ`'s `implementation: shipped` (`landed` where the map uses it, §6) with its landed `packages`, `tests` and `probes`, each acceptance criterion the change delivered ticked, a `SPEC §` promoted to `stable` only on the maintainer's word (it freezes the contract), then `sdd-check generate`; the maintenance lane edits no `REQ` and no map entry (§12);
   - both profiles — when the repository's policy is a changelog line per pull request (its PR checklist), the change's line under the `[Unreleased]` heading, in its style;
   - then commit every file this step touched, by path, citing the `REQ` when there is one.
3. **The lines that do not block.** First the `outside` defects: one with a small fix is fixed in this branch now, with its test, and flipped `--fixed`. Then ask the maintainer once, listing what is left by line: the remaining defects are carried to `docs/backlog.md` in this pull request (`sdd-pr flip <#key> --carry` each, then commit `docs/backlog.md` by path), recommended, since they land with the merge and the harvest skips them; a suggestion is carried only when the maintainer names it, and the others are left on the pull request, where the harvest reads them (`references/review.md` § The backlog). With `forge: none` no comment holds them, so the unnamed ones are dropped (`--deferred "dropped by the maintainer"`). Leave the backlog lines this branch settled: the next `/sdd-triage --backlog` deletes them.
4. **Gate, body, push.** Run the full gate on the branch as it stands, `<build_entrypoint> <ci_target>` (output to `.sdd/gate-<short head>.log`) and `<build_entrypoint> <spec_check_target>`, and read it; when it is red, stop with nothing pushed. Write the PR body from `docs/development-process.md` § The PR body (without that section, the repository's PR template), from the delivery notes `sdd-pr status` names, in at most about 450 words (`references/artefact-prose.md`); push, set the body and mark a draft ready with the repository's forge CLI; then, with a pull request, `sdd-pr resolve`. Stop: the maintainer merges on the forge, then runs this skill again. Merged before the close-out: only its body is updated.
5. **After the merge, clean up.** On a forge, lines not yet on the pull request go there first: `sdd-pr resolve`, from a checkout of the branch, posts them for the next `/sdd-triage --backlog`; an open critical or important line is the maintainer's to defer (`sdd-pr flip <#key> --deferred <where>`). Then `sdd-pr clean --dry-run`, read it, and `sdd-pr clean` (`references/review.md` § The tool). Relay what it leaves: the commands for a worktree this session runs in, other checkouts on the pull request's head, worker branches. A refusal is relayed to the maintainer, and the skill stops: never discard work or delete by hand to get past it. End with one line: this change is closed; start the next one in a new session.

## Guardrails

- **Never merge, close or reopen a pull request, and never delete a remote branch: the maintainer does that on the forge.**
- **Ask the maintainer in plain words: the decision, the options, a recommendation.**
- **Never hand-edit a generated block.**

## Reference

- `references/sdd-methodology.md` — §6 the status values, §9 the close-out, §12 the lanes.
- `references/review.md` — § The backlog (the carry, the harvest), § The tool (`status`, `flip`, `resolve`, `clean`).
- The repository's `docs/development-process.md` — § The PR body.

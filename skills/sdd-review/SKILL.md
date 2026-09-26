---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this PR for spec conformance", "review the branch before the draft PR", or "print the review prompts for the panel". Dispatches the reviewers the lane calls for and writes one numbered ledger; `--panel` prints the prompt blocks. Not for fixing what the ledger holds (sdd-triage) or authoring documents (sdd-specify).
argument-hint: "[PR number or REQ-id] [--lane full|maintenance] [--panel] [--post]"
allowed-tools: Agent, Task, Bash, Read, Grep, Glob
---

# Review — one spec-aware review round, written as one ledger

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Sequence a spec-aware review and write its findings as one ledger. Read `docs/.sdd.yaml` first for `paths.*`, the build targets, and the `agents:` block. No descriptor, or a descriptor with no `agents:` block, routes to `/sdd-scaffold` and stops.

This runs best on the branch, before the draft PR opens: the same findings cost the same to produce either way, and caught early they fold into the slice as ordinary work instead of becoming visible review rounds.

## Steps

0. **Detect the lane.** Read the lane from the `Lane:` line in the PR body if a PR exists, and corroborate it against the diff: a change with edits under `paths.requirements`, `paths.specifications` or `paths.adr`, or that alters an API shape or an error contract, is full lane whatever the line says. A third input is the touched specifications' frontmatter `mode:` — an `implementation-aligned` specification edited alongside code is still full lane; the mode says how the amendment is reviewed, not whether it is. Record which source was used. If there is no PR yet, take `--lane`, which `/sdd-deliver` passes, and corroborate it against the diff the same way.
1. **Scope the change.** Resolve the `REQ` / `SPEC §` under review — from the argument or the PR body — the PR if one exists (on GitHub, `gh pr view`), and the base branch. The scope is the branch diff against its base.
2. **Dispatch, per lane.** Pass each dispatch the resolved `REQ` / `SPEC §` and the base branch. On the **full lane**, dispatch `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` in parallel, plus every reviewer named in `agents.reviewers`. Dispatch `sdd-doc-reviewer` once per touched requirement, specification, or ADR, naming its path — it has no Bash to find the diff. On the **maintenance lane**, dispatch only the reviewers named in `agents.reviewers`. The SDD reviewer agents are not dispatched — there is no spec delta to review. Run every reviewer report-only; nothing is posted from inside a reviewer.
3. **Account for completion.** Record which reviewers were dispatched and how many reported. A dispatch that died and was not re-run is a gap, and the ledger header says so.
4. **Write the ledger.** Before writing round 0, carry forward the `Deferred` rows of the last merged PR that touched the same paths (find its merge with `git log --first-parent -1 --format=%H <base> -- <paths>`), with `carried from` set to that PR. Write **one** ledger comment, not one comment per finding — the format and its rules are in `references/artefact-prose.md` § The findings ledger. Allocate ids from the next free `F<n>`; an id already in the ledger keeps its number. Merge near-duplicate findings from two reviewers under one id and name both sources. Blockers and should-fix in the table. Nits and the polish classes of methodology §13 go straight to `Deferred`, whatever severity a reviewer gave them. Before the PR is ready this is **round 0**, held in-session until the draft opens; on a ready PR the findings join the round `/sdd-triage` has open. On the maintenance lane with `agents.reviewers` empty, the accounting line reads `Dispatched: none — agents.reviewers is empty · Reported: 0 of 0` and the ledger is not marked clean — an empty list is an unconfigured gate, never a clean one. It becomes clean only when the maintainer's review is recorded in the accounting line with no open blocker (artefact-prose.md, completion accounting).
5. **Post (with `--post`, or when asked).** Edit the PR's existing ledger comment in place; post one (on GitHub, `gh pr comment`) only when the PR has none.
6. **Panel prompts (with `--panel`).** Print one prompt block per name in `agents.review_panel.<lane>`, filled from the canonical text in the repo's `docs/ai-workflow.md` § Review — the repository's copy, not a version retyped here. Nothing in the repository can start those reviewers; the blocks are for a person to paste.

## Guardrails

- **Deliberate, not an automatic gate.** Run it when asked, and as round 0 of `/sdd-deliver` — not after every implementation slice.
- **Neither the dispatched agents nor this skill edits anything: fixing what the ledger holds is `/sdd-triage`.**
- **This is not the test gate** — whether the build passes is the build's job; read its output before claiming green.
- **One ledger. Never one comment per finding.**

## Reference

- `references/artefact-prose.md` — the findings ledger: its heading, completion accounting, table columns, id and status vocabularies, and the `Deferred` table.
- `references/sdd-methodology.md` — §12 the two lanes; §13 the two gates and the materiality threshold.
- `references/sdd-check.md` — the mechanical baseline `sdd-traceability-auditor` runs before this skill's own findings; this skill does not re-run the gate itself.
- The agents: `sdd-traceability-auditor` (map versus tree), `sdd-spec-conformance-reviewer` (code versus the cited `SPEC §`), `sdd-doc-reviewer` (one document against its kind contract).

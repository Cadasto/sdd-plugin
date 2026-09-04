---
name: sdd-review
description: This skill should be used when the user asks to "run the SDD review", "review this PR or change for spec conformance", "review the branch before the draft PR", or "print the review prompts for the panel". Spec-aware review orchestration — detects the lane, dispatches the SDD reviewer agents plus the repo's declared reviewers on the full lane and the language reviewer alone on the maintenance lane, and writes one numbered ledger. With `--panel` it prints one canonical prompt block per `review_panel` entry. Not for working a review round back into the ledger and fixing it (sdd-triage), or for authoring documents (sdd-specify).
argument-hint: "[PR number, REQ-id, or plan file] [--panel] [--post]"
allowed-tools: Agent, Task, Bash, Read, Grep, Glob
---

# Review — one spec-aware review round, written as one ledger

> **`references/…` paths resolve from the plugin root** (beside `skills/`, two levels up — not under this skill): `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, `../../references/…` relative, or Glob for the installed copy.

Sequence a spec-aware review and write its findings as one ledger. Read `docs/.sdd.yaml` first for `paths.*`, the build targets, and the `agents:` block.

This runs best on the branch, before the draft PR opens: the same findings cost the same to produce either way, and caught early they fold into the slice as ordinary work instead of becoming visible review rounds.

## Steps

0. **Detect the lane.** Read the lane from the `Lane:` line in the PR body if a PR exists, and corroborate it against the diff: a change with edits under `paths.specifications` or `paths.adr`, or that alters an API shape or an error contract, is full lane whatever the line says. Say which source you used. If there is no PR yet, take the lane from the plan header.
1. **Scope the change.** Resolve the `REQ` / `SPEC §` / plan under review — from the argument, the plan header, or the PR citation — and the PR if one exists (`gh pr view`). The scope is the branch diff against its base.
2. **Dispatch, per lane.** On the **full lane**, dispatch `sdd-traceability-auditor` and `sdd-spec-conformance-reviewer` in parallel, plus every reviewer named in `agents.reviewers`. Dispatch `sdd-doc-reviewer` as well when the change touches a requirement, specification, or ADR. On the **maintenance lane**, dispatch only the reviewers named in `agents.reviewers`. The SDD reviewer agents are not dispatched — there is no spec delta to review. Run every reviewer report-only; nothing is posted from inside a reviewer.
3. **Account for completion.** Record which reviewers were dispatched and how many reported. A dispatch that died and was not re-run is a gap, and the ledger header says so.
4. **Write the ledger.** Write **one** ledger comment, not one comment per finding — the format and its rules are in `references/artefact-prose.md`. Allocate ids from the next free `F<n>`; an id already in the ledger keeps its number. Merge near-duplicate findings from two reviewers under one id and name both sources. Blockers and should-fix in the table; nits go straight to `Deferred` (methodology §13). Before the draft PR exists this is **round 0**, held in-session and posted when the draft opens.
5. **Post (with `--post`, or when asked).** `gh pr comment` for a new ledger; edit the existing ledger comment in place for a later round. Never open a tracker issue for a review finding.
6. **Panel prompts (with `--panel`).** Print one prompt block per name in `agents.review_panel.<lane>`, filled from the canonical text in the repo's `docs/ai-workflow.md` § Review — the repository's copy, not a version retyped here. Nothing in the repository can start those reviewers; the blocks are for a person to paste.

## Guardrails

- **Opt-in, not an automatic gate.** Run it when asked, not after every implementation slice.
- **The dispatched agents never edit.** They report; applying a fix is `/sdd-triage`'s job.
- **This is not the test gate** — whether the build passes is the build's job; read its output before claiming green.
- **One ledger. Never one comment per finding.**
- **Fixing what the ledger holds is `/sdd-triage`.**

## Reference

- `references/artefact-prose.md` — the findings ledger: its heading, completion accounting, table columns, id and status vocabularies, and the `Deferred` table.
- `references/sdd-methodology.md` — §12 the two lanes; §13 the two gates and the materiality threshold.
- The agents: `sdd-traceability-auditor` (map versus tree), `sdd-spec-conformance-reviewer` (code versus the cited `SPEC §`), `sdd-doc-reviewer` (one document against its kind contract).

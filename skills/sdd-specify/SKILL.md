---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement", "retire a requirement", "write, extend, or amend a spec", "make this behaviour normative", "record an ADR", "resolve a STRAND", "amend the constitution", or "write a knowledge-base page". Authors the REQ, the RFC-2119 SPEC §, the ADR or a knowledge-base page, assigning identifiers and wiring traceability. Not for building (sdd-deliver) or a drift audit (sdd-trace).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Specify — the SDD definition layer

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code): take it from this file's own path, `\` turned into `/`, and never search the disk for it; `references/…` resolves from it.

Read `docs/.sdd.yaml` first for the profile, identifier style and paths. Drop a template's leading `<!-- Template: … -->` comment in the file created from it.

No descriptor: route to `/sdd-scaffold` and stop. Behaviour not yet explored: explore first — a design note under `docs/analysis/`, or the host's brainstorming workflow — and return with the note. Extract a design note's normative statements into the canonical spec.

**On the informative profile** (methodology §1a) each page declares a `doc_kinds` kind: write what the code does in plain prose, cite the constitution (`paths.constitution`) where it applies, use RFC-2119 only in the constitution, and assign identifiers only if the repository already uses them. The constitution is amended here and only here, with the reason in the commit body or an ADR.

## A · Requirement (`REQ-*`) — capture the capability

1. Read `req_style`, `req_areas`, `req_gap`, `paths.requirements`.
2. **Assign the next identifier** without collision — `REQ-<AREA>[-<SUB>…]-NNN` (only `req_areas`, never `excluded_areas`) or flat-numeric at `req_gap` spacing — once acceptance criteria exist; an idea without them gets a `STRAND` or a design note (methodology §5).
3. From [templates/requirement.md](../../references/templates/requirement.md): **observable, testable** acceptance criteria covering the **negative space** (what it must refuse or fail closed on), citing the `SPEC §` rather than restating it; **no implementation detail**. `draft` binds once merged (methodology §6). With a file-form `paths.requirements`, write no detail file ([traceability-schema.md § Profiles](../../references/traceability-schema.md#profiles)).
4. Write a missing `SPEC §` first (§B), so `canonical` names a real anchor. Then add the record (`status: draft`, `implementation: proposed`) to `traceability.yaml` and run `sdd-check generate` (invocation and fallback: [sdd-check.md](../../references/sdd-check.md)); the index row and the detail file's status lines come from the record.
5. **To retire one,** set the record's `status: deprecated` and `implementation: retired`, drop the evidence paths the change deletes, leave its heading in place with a one-line pointer (methodology §6), and run `sdd-check generate`.

## B · Specification (`SPEC-* §`) — make or amend normative behaviour

1. Open the **canonical** topic spec under `paths.specifications`. Search the other specs by subject, not wording, and confirm no other file owns this prose: one canonical home.
2. **Look up ground truth** for any domain fact in the `ground_truth` source; never guess.
3. Write or amend the statement, a keyword only where methodology §4 gives one: `MUST` for what a caller can observe and a test can pin, `SHOULD` with its reason for a default or a recommended path, plain prose for how the code does it. Give each section the `§N` heading, anchor and `**Implements:**` line [templates/specification.md](../../references/templates/specification.md) shows; never renumber a published §. A new obligation or a widened contract is full-lane work (methodology §12); a correction to the behaviour the change has or the maintainer decided, adding no obligation and widening no contract, is maintenance: one edit, no new requirement, no ADR. From shipped code, state only what the code does now. Environment behaviour stays informative ([review.md § Keywords](../../references/review.md#keywords-added-during-review)). Name a § dense with `MUST`s about internals in the hand-back, with the sentences to demote.
4. **The spec owns the negative space a caller can observe:** the refusals, fail-closed behaviour and the error contract a caller sees; the `REQ` cites them. What the code refuses internally is prose.
5. Set or verify the frontmatter `status:` and `mode:`; add or update the `traceability.yaml` record with the canonical anchor, then run `sdd-check generate`.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Take the next sequential number (never reused) and name the file `NNNN-<slug>.md` or `ADR-NNNN-<slug>.md`, matching the existing records, from [templates/adr.md](../../references/templates/adr.md); it is `accepted` before code depends on it.
2. **One irreversible decision per ADR**; a choice cheap to reverse is not one. Context states the problem, not the option chosen; Decision cites the `SPEC §` instead of restating its mechanics; long flows and DDL stay in the specs.
3. Cite the `STRAND` it resolves (close it with a backlink) and the `REQ`s it amends; run `sdd-check generate`.
4. To withdraw an unaccepted ADR, delete the file and its index row by hand — `generate` will not drop the row — and do not reuse the number.

## Guardrails

- Never cite a plan from a requirement, specification or ADR (methodology §9).
- Never settle an open question silently: record an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (a sibling SDD repo this one consumes), follow [cross-repo-gap.md](../../references/cross-repo-gap.md).
- **Never hand-edit a generated block** (except a withdrawn ADR's row, §C).
- Afterwards, run `/sdd-trace <REQ-id>` when the repository keeps a map, then hand off to `/sdd-deliver`.

## Reference

- [sdd-methodology.md](../../references/sdd-methodology.md) — §1a profiles, §3 document kinds, §4 RFC-2119, §5 identifiers and the canonical home, §6 status per kind.
- [sdd-check.md](../../references/sdd-check.md) — what `generate` writes; what `map-schema` and `index-sync` check.
- [templates/](../../references/templates/) · [traceability-schema.md](../../references/traceability-schema.md) · [cross-repo-gap.md](../../references/cross-repo-gap.md).

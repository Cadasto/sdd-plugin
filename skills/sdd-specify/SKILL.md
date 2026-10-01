---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement", "write, extend, or amend a spec", "make this behaviour normative", "record an ADR", "resolve a STRAND", "amend the constitution", or "document how this works". Authors the REQ, the RFC-2119 SPEC §, the ADR or a knowledge-base page, assigning identifiers and wiring traceability. Not for building (sdd-deliver) or a drift audit (sdd-trace).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Specify — the SDD definition layer

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` resolves from it.

Turn intent into the authoritative documents: a **requirement** (what + acceptance), the **specification** (how it must behave, RFC-2119), and an **ADR** for an irreversible decision. Read `docs/.sdd.yaml` first for the profile, identifier style and paths. One skill authors all three; each stays in its own file and kind. Drop a template's leading `<!-- Template: … -->` comment in the file created from it.

No descriptor: route to `/sdd-scaffold` and stop. Behaviour not yet explored: explore first — a design note under `docs/analysis/`, or the host's brainstorming workflow — and return with the note. A design note is **input, not the source of truth**: extract its normative statements into the canonical spec.

**On the informative profile** (methodology §1a) a document is a knowledge-base page: write what the code does in plain prose, cite the constitution (`paths.constitution`) where it applies, use RFC-2119 only in the constitution, and assign identifiers only if the repository already uses them. The constitution is amended here and only here, with the reason in the commit body or an ADR.

## A · Requirement (`REQ-*`) — capture the capability

1. Read `req_style`, `req_areas`, `req_gap`, `paths.requirements`.
2. **Assign the next identifier** without collision — `REQ-<AREA>-NNN` (reject unknown areas) or flat-numeric at `req_gap` spacing — once acceptance criteria exist; an idea without them gets a `STRAND` or a design note (methodology §5).
3. From `references/templates/requirement.md`: capability (what + why); **observable, testable** acceptance criteria that cover the **negative space** — what the capability must refuse or fail closed on — and cite the `SPEC §` rather than restate its rule; explicit out-of-scope; `status: draft` and `implementation: proposed`. **No implementation detail** — no file paths, no "how". The two status axes are tracked separately, and `draft` binds now. With a file-form `paths.requirements`, write no detail file (`references/traceability-schema.md` § Profiles).
4. Write a missing `SPEC §` first (§B), so `canonical` names a real anchor. Then add the record to `traceability.yaml` and run `sdd-check generate` (invocation and fallback: `references/sdd-check.md`); the index row and the detail file's status lines come from the record.

## B · Specification (`SPEC-* §`) — make or amend normative behaviour

1. Open the **canonical** topic spec under `paths.specifications`. Search the other specs by subject, not wording, and confirm no other file owns this prose: one canonical home.
2. **Look up ground truth** for any domain fact in the `ground_truth` source; never guess.
3. Write or amend the statement with explicit **RFC-2119** keywords (MUST/SHALL, SHOULD, MAY) — no task lists, file paths or PR summaries. Give each section the `§N` heading, anchor and `**Implements:**` line `references/templates/specification.md` shows (`map-to-tree` checks them); never renumber a published §. Any amendment to an existing § is full-lane work (methodology §12) and goes through steps 4 and 5. From shipped code, state only what the code does now. Behaviour of the shell, a library or the operating system stays informative: a binding sentence needs the code itself to guarantee the behaviour and a cheap test to pin it (`references/review.md` § Keywords).
4. **The spec owns the negative space's *how*:** refusals, `MUST NOT`s, fail-closed behaviour and the error contract carry normative force here; the `REQ` only names and cites them.
5. Set or verify the frontmatter `status:` and `mode:`; add or update the `traceability.yaml` record with the canonical anchor, then run `sdd-check generate`.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Take the next sequential number (never reused) and name the file `NNNN-<slug>.md` or `ADR-NNNN-<slug>.md`, matching the existing records — `generate` lists no other name. From `references/templates/adr.md`: Status (`proposed`; it must be `accepted` before code depends on it), Context, Decision, Consequences.
2. **One irreversible decision per ADR**; a choice cheap to reverse is not one. Context states the problem, not the option chosen; Decision cites the `SPEC §` instead of restating its mechanics; long flows and DDL stay in the specs.
3. Cite the `STRAND` it resolves (close it with a backlink) and the `REQ`s it amends; run `sdd-check generate`.
4. To withdraw an unaccepted ADR, delete the file and its index row by hand — `generate` will not drop the row — and do not reuse the number.

## Guardrails

- Never cite a plan from a requirement, specification or ADR (methodology §9).
- Never settle an open question silently: record an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (a sibling SDD repo this one consumes), follow `references/cross-repo-gap.md`.
- **Never hand-edit a generated block** (except a withdrawn ADR's row, §C).
- Afterwards, run `/sdd-trace <REQ-id>` (when the repository keeps a map) to confirm the index row, canonical anchor and record resolve; then hand off to `/sdd-deliver`.

## Reference

- `references/sdd-methodology.md` — §1a profiles, §3 document kinds, §4 RFC-2119, §5 identifiers and the canonical home, §6 status per kind.
- `references/sdd-check.md` — what `generate` writes; what `map-schema` and `index-sync` check.
- `references/templates/{requirement,specification,adr}.md` · `references/traceability-schema.md` · `references/cross-repo-gap.md`.

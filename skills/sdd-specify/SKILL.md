---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement", "write, extend, or amend a spec", "make this behaviour normative", "record an ADR", or "resolve a STRAND". Authors the REQ, the RFC-2119 SPEC §, and the ADR, assigning identifiers and wiring traceability. Not for planning and building (sdd-deliver) or a drift audit (sdd-trace).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Specify — the SDD definition layer

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Turn intent (often a design note from an exploration session) into the authoritative documents: a **requirement** (what + acceptance), the **specification** (how it must behave, RFC-2119), and an **ADR** when an irreversible decision is made. Read `docs/.sdd.yaml` first for identifier style and paths. Each artefact stays in its own file and lane — this skill bundles the *authoring procedures*, it does **not** merge the document kinds. Drop a template's leading `<!-- Template: … -->` comment in the file you create.

If the repo is not scaffolded (`docs/.sdd.yaml` missing), route to `sdd-scaffold`. If the behaviour has not been explored yet, explore it first: write a design note under `docs/analysis/`, or run the host's brainstorming workflow, and return with the note as input.

## A · Requirement (`REQ-*`) — capture the capability

1. Read `docs/.sdd.yaml` for `profile`, `req_style`, `req_areas`, `req_gap`, `paths.requirements`.
2. **Assign the next identifier** without collision — area-prefixed (`REQ-<AREA>-NNN`, reject unknown areas) or flat-numeric (next slot at `req_gap` spacing) — once acceptance criteria exist; an idea without them gets a `STRAND` or a design note instead (methodology §5).
3. From `references/templates/requirement.md`: capability (what + why), **observable, testable** acceptance criteria — covering the **negative space** (what the capability must refuse or fail closed on, with the intended failure behaviour as an observable outcome; the normative *how* lives in the spec, §B), not only happy paths; criteria cite the `SPEC §` rather than restate its rule — explicit out-of-scope, and the two status fields (`status: draft`, `implementation: proposed`).

   Under `profile: lightweight` with a file-form `paths.requirements`, write no detail file (`references/traceability-schema.md` § Profiles).
4. Write a missing `SPEC §` first (§B), so `canonical` names a real anchor. Then add the record to `traceability.yaml` (`references/traceability-schema.md`) and run `sdd-check generate` (invocation and fallback: `references/sdd-check.md`); the index row and the detail file's status lines are written from the record.
- **No implementation detail** — no file paths, no "how". Track the two status axes separately (`draft` is binding now).

## B · Specification (`SPEC-* §`) — make or amend normative behaviour

1. Open the **canonical** topic spec under `paths.specifications`. Confirm no other file already owns this prose — search the other specs by subject, not wording — and never create a second copy.
2. **Look up ground truth** for any domain fact in the source named in `.sdd.yaml` (`ground_truth`); never guess.
3. Write or amend the statement with explicit **RFC-2119** keywords (MUST/SHALL, SHOULD, MAY). No task lists, no file paths, no PR summaries. Give each section the `§N` heading, anchor and `**Implements:**` line that `references/templates/specification.md` shows — `map-to-tree` checks them — and never renumber a published §. Any amendment to an existing § is full-lane work (methodology §12) and goes through steps 4 and 5. When writing from shipped code, state only what the code does now.
4. **The spec owns the negative space's *how*.** Refusals, `MUST NOT`s, fail-closed behaviour, and the error contract (what failure looks like) are written here with normative force — the `REQ` acceptance criteria only name and cite them (§A).
5. Set or verify the spec's frontmatter `status:` and `mode:`; add or update the record in `traceability.yaml` with the canonical anchor, then run `sdd-check generate` (invocation and fallback: `references/sdd-check.md`).
- **One canonical home — never duplicate normative prose.** This is the cardinal rule.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Assign the next sequential number (never reused); name the file `NNNN-<slug>.md` or `ADR-NNNN-<slug>.md`, matching the existing records — `generate` lists no other name. From `references/templates/adr.md`: Status (`proposed` → must be `accepted` before code depends on it), Context, Decision, Consequences.
2. **One irreversible decision per ADR**; a choice cheap to reverse is not one. Context states the problem, not the chosen option; Decision cites the `SPEC §` rather than restating its mechanics. Long flows/DDL stay in the specs.
3. Wire traceability: cite the `STRAND` it resolves (close it with a backlink) and the `REQ`s it amends. Then run `sdd-check generate`.
4. To withdraw an ADR before it is accepted, delete the file and its index row by hand — `generate` will not drop the row — and do not reuse the number.

## Working from a brainstorming design doc

A design note is **input narrative, not the source of truth.** Extract its normative statements into the canonical spec.

## Guardrails

- Keep the kinds separate even though one skill authors all three: a requirement has no normative prose, a spec has no tasks, an ADR holds one decision.
- Never cite a plan from a requirement, specification or ADR; plans are deleted at the release (methodology §9).
- Don't settle an open question silently — record it as an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (consuming a sibling SDD repo), see `references/cross-repo-gap.md`.
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.** (Exception: a withdrawn ADR's row, §C.)
- After specifying, run `/sdd-trace <REQ-id>` to confirm the record resolves — index row, canonical anchor, traceability entry — then hand off to `/sdd-deliver`: the plan lands in `paths.plans` with `implements:` in its frontmatter (`references/traceability-schema.md` §3).

## Reference

- `references/sdd-methodology.md` — §3 document kinds & boundaries, §4 RFC-2119, §5 identifiers & single canonical home, §6 status per document kind.
- `references/sdd-check.md` — what `generate` writes and what the `map-schema`/`index-sync` families check.
- `references/templates/{requirement,specification,adr}.md` · `references/traceability-schema.md` · `references/cross-repo-gap.md`.

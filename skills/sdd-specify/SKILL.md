---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement", "write, extend, or amend a spec", "make this behaviour normative", "record an ADR", or "resolve a STRAND". Authors the REQ, the RFC-2119 SPEC §, and the ADR, assigning identifiers and wiring traceability. Not for planning and building (sdd-deliver) or a drift audit (sdd-trace).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Specify — the SDD definition layer

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Turn intent (often a design note from an exploration session) into the authoritative documents: a **requirement** (what + acceptance), the **specification** (how it must behave, RFC-2119), and an **ADR** when an irreversible decision is made. Read `docs/.sdd.yaml` first for identifier style and paths. Each artefact stays in its own file and lane — this skill bundles the *authoring procedures*, it does **not** merge the document kinds.

If the repo is not scaffolded (`docs/.sdd.yaml` missing), route to `sdd-scaffold`. If the behaviour has not been explored yet, explore it first: write a design note under `docs/analysis/`, or run the host's brainstorming workflow, and return with the note as input.

## A · Requirement (`REQ-*`) — capture the capability

1. Read `docs/.sdd.yaml` for `req_style`, `req_areas`, `req_gap`.
2. **Assign the next identifier** without collision — area-prefixed (`REQ-<AREA>-NNN`, reject unknown areas) or flat-numeric (next slot at `req_gap` spacing).
3. From `references/templates/requirement.md`: capability (what + why), **observable, testable** acceptance criteria — covering the **negative space** (what the capability must refuse or fail closed on, with the intended failure behaviour as an observable outcome; the normative *how* lives in the spec, §B), not only happy paths — explicit out-of-scope, and the two status fields (`status: draft`, `implementation: proposed`).
4. Add the record to `traceability.yaml` (`references/traceability-schema.md`), then run `sdd-check generate` (the repository's vendored copy at `check.script`, else the plugin's own `tools/sdd-check.py`, with `--root .`; when `python3` is unavailable, say so and leave the block for the next run rather than hand-editing it); the index row and the detail file's status lines are written from the record.
- **No implementation detail** — no file paths, no "how". Track the two status axes separately (`draft` is binding now).

## B · Specification (`SPEC-* §`) — make or amend normative behaviour

1. Open the **canonical** topic spec under `paths.specifications`. Confirm no other file already owns this prose — never create a second copy.
2. **Look up ground truth** for any domain fact in the source named in `.sdd.yaml` (`ground_truth`); never guess.
3. Write or amend the statement with explicit **RFC-2119** keywords (MUST/SHALL, SHOULD, MAY) and a stable `§N` anchor. No task lists, no file paths, no PR summaries. An amendment to an existing § — one sentence or many — is full-lane work (methodology §12) and goes through steps 4 and 5 like a new §; there is no edit of normative text small enough to skip them.
4. **The spec owns the negative space's *how*.** Refusals, `MUST NOT`s, fail-closed behaviour, and the error contract (what failure looks like) are written here with normative force — the `REQ` acceptance criteria only name and cite them (§A).
5. Set/verify the `Status:` header; add/update the record in `traceability.yaml` (`references/traceability-schema.md`) with the canonical anchor, then run `sdd-check generate` (the repository's vendored copy at `check.script`, else the plugin's own `tools/sdd-check.py`, with `--root .`; when `python3` is unavailable, say so and leave the block for the next run rather than hand-editing it); the requirements index row and the specifications index are written from the record.
- **One canonical home — never duplicate normative prose.** This is the cardinal rule.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Assign the next sequential number (never reused). From `references/templates/adr.md`: Status (`proposed` → must be `accepted` before code depends on it), Context, Decision, Consequences.
2. **One decision per ADR.** Long flows/DDL stay in the specs.
3. Wire traceability: cite the `STRAND` it resolves (and close that strand with a backlink) and the `REQ`s it amends.

## Working from a brainstorming design doc

A design note is **input narrative, not the source of truth.** Extract its normative statements into the canonical spec.

## Guardrails

- Keep the kinds separate even though one skill authors all three: a requirement has no normative prose, a spec has no tasks, an ADR holds one decision.
- Don't settle an open question silently — record it as an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (consuming a sibling SDD repo), see `references/cross-repo-gap.md`.
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.**
- After specifying, run `/sdd-trace <REQ-id>` to confirm the record resolves — index row, canonical anchor, traceability entry — then hand off to `/sdd-deliver`: the plan lands in `docs/plans/` with the citing header.

## Reference

- `references/sdd-methodology.md` — §3 document kinds & boundaries, §4 RFC-2119, §5 identifiers & single canonical home, §6 status per document kind.
- `references/sdd-check.md` — what `generate` writes and what the `map-schema`/`index-sync` families check.
- `references/templates/{requirement,specification,adr}.md` · `references/traceability-schema.md` · `references/cross-repo-gap.md`.

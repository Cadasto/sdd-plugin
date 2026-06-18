---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement / capability", "write or extend a spec", "make this behaviour normative (RFC-2119)", "record an ADR / architectural decision", or "resolve a STRAND". The SDD definition layer — authors the `REQ`, the canonical RFC-2119 `SPEC §`, and the `ADR`, assigning identifiers and wiring traceability. Not for exploring/design (superpowers brainstorming first); not for planning or building (superpowers writing-plans / executing-plans); a traceability audit (sdd-trace); or a one-line edit to an existing spec § (open the file directly).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Specify — the SDD definition layer

Turn intent (often a design doc from `superpowers:brainstorming`) into the authoritative documents: a **requirement** (what + acceptance), the **specification** (how it must behave, RFC-2119), and an **ADR** when an irreversible decision is made. Read `docs/.sdd.yaml` first for identifier style and paths. Each artefact stays in its own file and lane — this skill bundles the *authoring procedures*, it does **not** merge the document kinds.

If the repo isn't scaffolded (`docs/.sdd.yaml` missing), route to `sdd-scaffold`. If the behaviour hasn't been explored yet, route to superpowers `brainstorming` first (see `references/sdd-with-superpowers.md`).

## A · Requirement (`REQ-*`) — capture the capability

1. Read `docs/.sdd.yaml` for `req_style`, `req_areas`, `req_gap`.
2. **Assign the next identifier** without collision — area-prefixed (`REQ-<AREA>-NNN`, reject unknown areas) or flat-numeric (next slot at `req_gap` spacing).
3. From `references/templates/requirement.md`: capability (what + why), **observable, testable** acceptance criteria, explicit out-of-scope, and the two status fields (`status: draft`, `implementation: proposed`).
4. Add the index row to `docs/requirements/README.md`.
- **No implementation detail** — no file paths, no "how". Track the two status axes separately (`draft` is binding now).

## B · Specification (`SPEC-* §`) — make behaviour normative

1. Open the **canonical** topic spec under `paths.specifications`. Confirm no other file already owns this prose — never create a second copy.
2. **Look up ground truth** for any domain fact in the source named in `.sdd.yaml` (`ground_truth`); never guess.
3. Write the statement with explicit **RFC-2119** keywords (MUST/SHALL, SHOULD, MAY) and a stable `§N` anchor. No task lists, no file paths, no PR summaries.
4. Set/verify the `Status:` header; wire the requirements index row to the canonical anchor (link only); add/update the `traceability.yaml` entry (`references/traceability-schema.md`).
- **One canonical home — never duplicate normative prose.** This is the cardinal rule.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Assign the next sequential number (never reused). From `references/templates/adr.md`: Status (`proposed` → must be `accepted` before code depends on it), Context, Decision, Consequences.
2. **One decision per ADR.** Long flows/DDL stay in the specs.
3. Wire traceability: cite the `STRAND` it resolves (and close that strand with a backlink) and the `REQ`s it amends.

## Working from a brainstorming design doc

A `docs/superpowers/specs/*-design.md` is **input narrative, not the source of truth.** Extract normative statements into the canonical spec (§B) and capture the capability as a `REQ` (§A). Redirect rules: `references/sdd-with-superpowers.md`.

## Guardrails

- Keep the kinds separate even though one skill authors all three: a requirement has no normative prose, a spec has no tasks, an ADR holds one decision.
- Don't settle an open question silently — record it as an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (consuming a sibling SDD repo), see `references/cross-repo-gap.md`.
- After specifying, hand off to superpowers planning per `references/sdd-with-superpowers.md` (plan lands in `docs/plans/` with the SDD citing header).

## Reference

- `references/sdd-methodology.md` — §3 document kinds & boundaries, §4 RFC-2119, §5 identifiers & single canonical home, §6 status axes.
- `references/templates/{requirement,specification,adr}.md` · `references/traceability-schema.md` · `references/sdd-with-superpowers.md` · `references/cross-repo-gap.md`.

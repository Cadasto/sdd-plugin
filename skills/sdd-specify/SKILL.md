---
name: sdd-specify
description: This skill should be used when the user asks to "add a requirement", "write, extend, or amend a spec", "make this behaviour normative", "record an ADR", or "resolve a STRAND". Authors the REQ, the RFC-2119 SPEC §, and the ADR, assigning identifiers and wiring traceability. Not for planning and building (sdd-deliver) or a drift audit (sdd-trace).
argument-hint: "<capability, behaviour, or decision to record> [REQ-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Specify — the SDD definition layer

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

Turn intent (often a design note from an exploration session) into the authoritative documents: a **requirement** (what + acceptance), the **specification** (how it must behave, RFC-2119), and an **ADR** when an irreversible decision is made. Read `docs/.sdd.yaml` first for identifier style and paths. Each artefact stays in its own file and lane — this skill bundles the *authoring procedures*, it does **not** merge the document kinds. When a file is created from a template, drop the template's leading `<!-- Template: … -->` comment; it instructs the author and is not part of the document.

If the repo is not scaffolded (`docs/.sdd.yaml` missing), route to `sdd-scaffold`. If the behaviour has not been explored yet, explore it first: write a design note under `docs/analysis/`, or run the host's brainstorming workflow, and return with the note as input.

## A · Requirement (`REQ-*`) — capture the capability

1. Read `docs/.sdd.yaml` for `profile`, `req_style`, `req_areas`, `req_gap`, `paths.requirements`.
2. **Assign the next identifier** without collision — area-prefixed (`REQ-<AREA>-NNN`, reject unknown areas) or flat-numeric (next slot at `req_gap` spacing) — only once step 3's acceptance criteria exist. An idea with no acceptance contract gets no `REQ` id (methodology §5, lazy identifier allocation); record it as a `STRAND` (when `use_strands` is true) or a design note instead.
3. From `references/templates/requirement.md`: capability (what + why), **observable, testable** acceptance criteria — covering the **negative space** (what the capability must refuse or fail closed on, with the intended failure behaviour as an observable outcome; the normative *how* lives in the spec, §B), not only happy paths; each criterion names the behaviour and cites the `SPEC §` that owns its rule rather than restating the rule — explicit out-of-scope, and the two status fields (`status: draft`, `implementation: proposed`).

   Under `profile: lightweight` with `paths.requirements` naming a file, write no detail file: that file is the single registry index, and its row is generated from the record (`references/traceability-schema.md` § Profiles). The references name no other home for the capability and acceptance under this profile, so keep them where the repository already keeps them, and ask the maintainer when that is unclear rather than inventing a location.
4. When the `SPEC §` the requirement points to does not exist yet, write it first (§B), so the record's `canonical` names a real anchor. Then add the record to `traceability.yaml` (`references/traceability-schema.md`) and run `sdd-check generate` (invocation and fallback: `references/sdd-check.md`); the index row and the detail file's status lines are written from the record.
- **No implementation detail** — no file paths, no "how". Track the two status axes separately (`draft` is binding now).

## B · Specification (`SPEC-* §`) — make or amend normative behaviour

1. Open the **canonical** topic spec under `paths.specifications`. Confirm no other file already owns this prose — never create a second copy. Search the other specs by subject (a list, a diagnostic, an exit status), not by wording: a second home usually paraphrases the first, and a small tool split across several specs is where it happens.
2. **Look up ground truth** for any domain fact in the source named in `.sdd.yaml` (`ground_truth`); never guess.
3. Write or amend the statement with explicit **RFC-2119** keywords (MUST/SHALL, SHOULD, MAY). No task lists, no file paths, no PR summaries. Each section carries the anchor contract `references/templates/specification.md` shows: a `§N` heading, an explicit anchor under it in the template's form (`<a id="section-title-req-area-nnn"></a>`), and an `**Implements:** <REQ-id>` line in the section (or the id in the heading itself). `map-to-tree` resolves the record's `canonical` against exactly these (`references/sdd-check.md` § map-to-tree); never renumber a published § or change a cited anchor. An amendment to an existing § — one sentence or many — is full-lane work (methodology §12) and goes through steps 4 and 5 like a new §; there is no edit of normative text small enough to skip them.

   **Writing from shipped code (implementation-aligned, methodology §7).** Check every binding sentence against the code before it lands: state what the code does now, no more. A guarantee the code does not give is not a description — it is a spec-first change with a code fix, or it stays out.
4. **The spec owns the negative space's *how*.** Refusals, `MUST NOT`s, fail-closed behaviour, and the error contract (what failure looks like) are written here with normative force — the `REQ` acceptance criteria only name and cite them (§A).
5. Set or verify the spec's frontmatter `status:` and `mode:`; add or update the record in `traceability.yaml` (`references/traceability-schema.md`) with the canonical anchor, then run `sdd-check generate` (invocation and fallback: `references/sdd-check.md`). The requirements index row is written from the record; the specifications index is built from the spec files themselves.
- **One canonical home — never duplicate normative prose.** This is the cardinal rule.

## C · ADR (`ADR-NNNN`) — record an irreversible decision

1. Assign the next sequential number (never reused) and name the file `<paths.adr>/NNNN-<slug>.md`, or `ADR-NNNN-<slug>.md` when the existing records use that form; `generate` lists only file names matching `^(ADR-|\d{4}-)`. From `references/templates/adr.md`: Status (`proposed` → must be `accepted` before code depends on it), Context, Decision, Consequences.
2. **One irreversible decision per ADR.** Long flows/DDL stay in the specs. A choice that is cheap to reverse — a toolchain or library pick swapped in an afternoon — is not an ADR.
3. **Keep the sections apart.** Context states the problem and the forces, and never names the option chosen; the choice appears first in Decision. Decision names the choice and cites the `SPEC §` that carries the mechanics, rather than restating them.
4. Wire traceability: cite the `STRAND` it resolves (when `use_strands` is true; close that strand with a backlink) and the `REQ`s it amends. Cite background per the plan-citation guardrail below.
5. Run `sdd-check generate`; the ADR index row is written from the file (`references/sdd-check.md` § Generated blocks).
6. **Withdrawing an ADR before it is accepted:** delete the file and its row in the ADR index by hand, in the same change. `sdd-check generate` refuses to drop a row whose document is gone, by design (`references/sdd-check.md` § What a writing run refuses). The number is not reused.

## Working from a brainstorming design doc

A design note is **input narrative, not the source of truth.** Extract its normative statements into the canonical spec.

## Guardrails

- Keep the kinds separate even though one skill authors all three: a requirement has no normative prose, a spec has no tasks, an ADR holds one decision.
- **A requirement, specification or ADR never cites a plan** (methodology §9): plans are deleted at the release sweep, so cite a PR, a commit or a `REQ` instead.
- Don't settle an open question silently — record it as an ADR (§C) or a `STRAND`, or return to brainstorming.
- For a missing **upstream** capability (consuming a sibling SDD repo), see `references/cross-repo-gap.md`.
- **Never hand-edit a generated block; change the map or the frontmatter and run `sdd-check generate`.** The one sanctioned exception is deleting the row of a withdrawn ADR (§C step 6).
- After specifying, run `/sdd-trace <REQ-id>` to confirm the record resolves — index row, canonical anchor, traceability entry — then hand off to `/sdd-deliver`: the plan lands in `paths.plans` with `implements:` in its frontmatter (`references/traceability-schema.md` §3).

## Reference

- `references/sdd-methodology.md` — §3 document kinds & boundaries, §4 RFC-2119, §5 identifiers & single canonical home, §6 status per document kind.
- `references/sdd-check.md` — what `generate` writes and what the `map-schema`/`index-sync` families check.
- `references/templates/{requirement,specification,adr}.md` · `references/traceability-schema.md` · `references/cross-repo-gap.md`.

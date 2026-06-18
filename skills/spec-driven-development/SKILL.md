---
name: spec-driven-development
description: This skill should be used when the user mentions spec-driven development concepts outside a specific artefact action — "what is SDD", "explain spec-driven development", "how does this repo's spec workflow work", "where does the spec fit with planning/building", or vocabulary like normative, RFC-2119, traceability, drift, ADR, requirement-vs-spec. Provides SDD awareness, explains the methodology, routes intent to the right skill, and maps how SDD complements the superpowers engineering loop. Not for performing an artefact action — use the specific sdd-* skill.
---

# Spec-Driven Development — awareness, routing & integration

The always-on layer for SDD. It does no artefact work itself; it explains the methodology, routes to the skill that does the work, and **coordinates with the superpowers plugin** so the two are complementary, not overlapping. Ground every answer in `references/sdd-methodology.md` — do not improvise rules.

## Core idea (state this when explaining SDD)

The **specification — not the code, not the prompt — is the source of truth.** Code is derived from it and measured against it; when they disagree the spec wins (unless a section is explicitly *implementation-aligned*). This plugin targets the **spec-anchored** rung, backed by stable identifiers, a machine-checked traceability map, and CI that fails on drift. Full detail: `references/sdd-methodology.md`.

## Division of labour with superpowers

This plugin owns the **spec / document / traceability layer**. The generic engineering loop belongs to **superpowers**. Combined flow:

```
superpowers:brainstorming → SDD:sdd-specify → superpowers:writing-plans → executing-plans/TDD
   → SDD:sdd-trace + superpowers:verification-before-completion → SDD:sdd-archive + superpowers:finishing-a-development-branch
```

### Route to SDD

| Intent | Route to |
|---|---|
| Set up / extend the SDD docs structure | `sdd-scaffold` |
| Capture a capability, write normative behaviour, or record a decision (REQ/SPEC/ADR) | `sdd-specify` |
| Traceability / drift / spec-check / a REQ's context | `sdd-trace` |
| Review *SDD documents* for boundary violations | `sdd-doc-reviewer` agent |
| Close out the spec, index, and plan | `sdd-archive` |

Explore, plan, build, verify tests/build, review code, merge/PR → **superpowers** (`brainstorming`, `writing-plans`, `executing-plans` / `test-driven-development`, `verification-before-completion`, `requesting-code-review`, `finishing-a-development-branch`). Full seam, handoffs, and the `docs/superpowers/*` → canonical-tree path redirect: `references/sdd-with-superpowers.md`.

## Guardrails this layer enforces

- **No code-first.** If asked to implement behaviour for which **no `REQ` and no spec exist**, do not jump to code. Redirect: explore with `superpowers:brainstorming` if needed, record with `sdd-specify`, then plan/build with superpowers. The exception is *implementation-aligned* work on shipped code — the spec is updated in the **same** change.
- **One source of truth.** `docs/superpowers/*` artefacts are narrative/working output — canonical spec (`docs/specifications/`) and plans (`docs/plans/`) win. Route design output through `sdd-specify`; land plans in `docs/plans/`.
- **Don't settle open questions silently** — a genuine fork goes to an ADR (`sdd-specify`) or a `STRAND`, or back to brainstorming.
- **Check the descriptor.** Repo conventions live in `docs/.sdd.yaml`; if it is missing, the repo isn't scaffolded (route to `sdd-scaffold`).

## Reference

- `references/sdd-methodology.md` — the authoritative grounding (ladder, document kinds, RFC-2119, identifiers, traceability, two modes, DoR/DoD, anti-patterns).
- `references/sdd-with-superpowers.md` — the SDD↔superpowers boundary and the path redirect.
- `references/traceability-schema.md` — the `traceability.yaml` and `.sdd.yaml` schemas.

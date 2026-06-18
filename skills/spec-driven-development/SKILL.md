---
name: spec-driven-development
description: This skill should be used when the user mentions spec-driven development concepts outside a specific artefact action — "what is SDD", "explain spec-driven development", "how does this repo's spec workflow work", "should I write a spec or a requirement", or vocabulary like normative, RFC-2119, traceability, drift, ADR, requirement-vs-spec. Provides SDD awareness, explains the methodology, and routes intent to the right sdd-* skill. Not for performing an artefact action (use the specific sdd-* skill) — this is the awareness and routing layer.
---

# Spec-Driven Development — awareness & router

The always-on layer for Spec-Driven Development. It does no artefact work itself; it explains the methodology and routes the request to the skill that does the work. Ground every answer in the bundled `references/sdd-methodology.md` — do not improvise rules.

## Core idea (state this when explaining SDD)

The **specification — not the code, not the prompt — is the source of truth.** Code is derived from it and measured against it; when they disagree the spec wins (unless a section is explicitly *implementation-aligned*). This plugin targets the **spec-anchored** rung: specs are living, versioned, governing contracts, backed by stable identifiers, a machine-checked traceability map, and CI that fails on drift. Full detail: `references/sdd-methodology.md`.

The loop: `Specify → (Clarify) → Plan → Tasks → Implement → Verify → Archive`, under a constitution of document-kind boundaries.

## Routing table

Recognise the intent and hand off to the matching skill:

| The user wants to… | Route to |
|---|---|
| Set up / initialise SDD structure in a repo | `sdd-scaffold` |
| Capture a capability / "what we must build" | `sdd-requirement` |
| Write normative behaviour / make something RFC-2119 | `sdd-spec` |
| Record an irreversible decision / resolve an open question | `sdd-adr` |
| Break a requirement into tasks | `sdd-plan` |
| Build the code / work the plan | `sdd-implement` |
| Check "is this done?" / run the gate | `sdd-verify` |
| See traceability / find drift / get a REQ's context | `sdd-trace` |
| Close out a finished feature | `sdd-archive` |
| Flag a missing upstream capability | `sdd-gap` |

## Guardrails this layer enforces

- **No code-first.** If asked to implement behaviour for which **no `REQ` and no spec exist**, do not jump to code. Redirect: capture it with `sdd-requirement`, make it normative with `sdd-spec`, then plan and implement. The exception is *implementation-aligned* work on already-shipped code — there, the spec is updated in the **same** change (`sdd-implement` handles the reconcile).
- **Don't decide open questions silently.** Genuine architectural forks go to `sdd-adr` (or a `STRAND`), never into prose or code by default.
- **One canonical home.** Never let normative prose be duplicated; the requirements index links, the spec owns the text.
- **Check the descriptor.** Repo conventions (identifier style, paths, build tool, ground-truth source) live in `docs/.sdd.yaml` — read it before acting, and if it is missing, the repo has not been scaffolded yet (route to `sdd-scaffold`).

## Reference

- `references/sdd-methodology.md` — the rigour ladder, document kinds + boundary rules, RFC-2119 discipline, identifiers, the traceability chain, two source-of-truth modes, DoR/DoD, and anti-patterns. This is the authoritative grounding for every answer.
- `references/traceability-schema.md` — the `traceability.yaml` record format and the `.sdd.yaml` descriptor schema.

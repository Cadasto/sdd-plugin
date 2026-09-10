---
name: spec-driven-development
allowed-tools: Read, Grep, Glob
description: This skill should be used when the user asks "what is SDD", "explain spec-driven development", "how does the spec workflow work here", or uses vocabulary like normative, RFC-2119, traceability, drift, ADR, lane, ledger. Explains the methodology and routes intent to the right sdd-* skill. Not for performing an artefact action (use that sdd-* skill).
---

# Spec-Driven Development — awareness, routing & integration

> `references/…` resolves from the plugin root: `${CLAUDE_PLUGIN_ROOT}/references/…` on Claude Code, or Glob for the installed copy.

The always-on layer for SDD. It does no artefact work itself; it explains the methodology, routes to the skill that does the work, and states where an optional general engineering plugin still fits. Ground every answer in `references/sdd-methodology.md` — do not improvise rules.

## Core idea (state this when explaining SDD)

The **specification — not the code, not the prompt — is the source of truth.** Code is derived from it and measured against it; when they disagree the spec wins (unless a section is explicitly *implementation-aligned*). This plugin targets the **spec-anchored** rung, backed by stable identifiers, a machine-checked traceability map, and CI that fails on drift. Full detail: `references/sdd-methodology.md`.

## The delivery surface

```
/sdd-specify  →  /sdd-deliver  →  /sdd-review (+ --panel)  →  /sdd-triage  →  /sdd-archive
                                                                                    │
                                                             at the next version bump: /sdd-finalize
```

### Route to SDD

| Intent | Route to |
|---|---|
| Set up / extend the SDD docs structure | `sdd-scaffold` |
| Capture a capability, write normative behaviour, or record a decision (REQ/SPEC/ADR) | `sdd-specify` |
| Amend an existing spec § — any normative change, one sentence or many, is full lane | `sdd-specify` |
| Deliver a REQ or plan: preconditions, plan, workers, gates, draft PR | `sdd-deliver` |
| Implement one bounded task from a brief | `sdd-implementer` agent (dispatched by `sdd-deliver`) |
| Spec-aware review into the ledger; prompt blocks for the panel | `sdd-review` |
| Work a review round: merge findings, verify, fix, resolve, re-request | `sdd-triage` |
| Traceability / drift / spec-check / a REQ's context | `sdd-trace` |
| Run the drift gate, lint the docs, or regenerate the indexes | `sdd-trace` / `sdd-check` (vendored by `sdd-scaffold`) |
| Does the code satisfy the `SPEC §` it cites, clause by clause | `sdd-spec-conformance-reviewer` agent |
| Review a *requirement, spec, or ADR* for boundary violations | `sdd-doc-reviewer` agent |
| Close out the spec status, the requirement status, traceability, and the plan — in the implementing PR | `sdd-archive` |
| Sweep finished plans at a version bump, before the tag | `sdd-finalize` |

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is **optional**. Exploration workflows like brainstorming
are a good way to open a new idea before `/sdd-specify`. Planning, task execution, verification, code
review, and branch finishing are covered here
by `/sdd-deliver`, the `sdd-implementer` agent, the review ledger, and the PR-body close-out; running both
sets over the same work duplicates the loop and splits the plan's home. Plans belong in `docs/plans/`; if a
tool wants to write them somewhere else, point it at `docs/plans/` rather than keeping a second tree.

## Guardrails this layer enforces

- **No code-first.** If asked to implement behaviour for which **no `REQ` and no spec exist**, do not jump to code. Redirect: explore first if the idea is new, record with `sdd-specify`, then deliver with `sdd-deliver`. The exception is *implementation-aligned* work on shipped code — the spec is updated in the **same** change.
- **One source of truth, one home for the plan.** The canonical spec is `docs/specifications/` and the
  plan is `docs/plans/YYYY-MM-DD-<slug>.md`, on the branch. Never let a second tree of design documents or
  plans become a parallel source of truth.
- **One home per fact — in process prose too.** The commit body, PR body, changelog, and review comments each carry only what lives nowhere else; cite identifiers (`REQ`/`SPEC §`/plan/SHA) instead of restating. `references/artefact-prose.md`.
- **Don't settle open questions silently** — a genuine fork goes to an ADR (`sdd-specify`) or a `STRAND`, or back to brainstorming.
- **Check the descriptor.** Repo conventions live in `docs/.sdd.yaml`; if it is missing, the repo isn't scaffolded (route to `sdd-scaffold`).
- **Never hand-edit a generated block.** Every skill that changes the map or the frontmatter runs `sdd-check generate` (the repository's vendored copy at `check.script`, else the plugin's own `tools/sdd-check.py`, with `--root .`; when `python3` is unavailable, say so and leave the block for the next run rather than hand-editing it) before it stops. This skill states the rule for the others to obey; it has no `Bash` grant and performs no artefact work itself.

## Reference

- `references/sdd-methodology.md` — the authoritative grounding (ladder, document kinds, RFC-2119, identifiers, traceability, two modes, the plan lifecycle, lanes, review discipline, anti-patterns).
- `references/sdd-check.md` — the vendored drift gate's commands, families, and report format.
- `references/traceability-schema.md` — the `traceability.yaml` and `.sdd.yaml` schemas.
- `references/artefact-prose.md` — one home per fact, the findings ledger, the prose register.

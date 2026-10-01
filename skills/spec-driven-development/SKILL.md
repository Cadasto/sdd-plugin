---
name: spec-driven-development
description: This skill should be used when the user asks "what is SDD", "explain spec-driven development", "how does the spec workflow work here", "which /sdd command do I use", or asks to implement, build, or add behaviour in a repository with docs/.sdd.yaml before a REQ or spec exists. Explains the methodology, routes intent to the right sdd-* skill, and blocks code-first work. Not for performing an artefact action (the sdd-* skills do that).
allowed-tools: Read, Grep, Glob
---

# Spec-Driven Development — awareness and routing

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` resolves from it.

The always-on layer: it explains the methodology, routes to the skill that does the work, and does no artefact work itself. Ground every answer in `references/sdd-methodology.md`; never improvise a rule.

## Core idea (state this when explaining SDD)

The **specification — not the code, not the prompt — is the source of truth.** Code is derived from it and measured against it; when they disagree the spec wins, unless a section is explicitly *implementation-aligned*. The plugin targets the **spec-anchored** rung: stable identifiers, a machine-checked traceability map, and CI that fails on drift.

**Two profiles** (methodology §1a): `formal` is the above — requirements, RFC-2119 specifications, ADRs and the map, all checked; `informative` keeps `docs/` as a knowledge base where code leads and only one constitution document binds.

## The delivery surface

```
/sdd-specify  →  /sdd-deliver  →  /sdd-review (+ --panel)  →  /sdd-triage  →  /sdd-deliver --close-out
```

| Intent | Route to |
|---|---|
| Set up or extend the SDD docs structure | `sdd-scaffold` |
| Capture a capability, make behaviour normative, record a decision, amend a spec § (any normative change is full lane) | `sdd-specify` |
| Deliver a change: the dispatch gate, workers, gates, the first review pass, the draft PR; close out the requirement and write the PR body (`--close-out`) | `sdd-deliver` |
| Implement one bounded task from a brief | `sdd-implementer` agent (dispatched by `sdd-deliver`) |
| A review pass into the branch's findings file; panel prompts | `sdd-review` |
| Work the open findings: verify, fix, flip, mirror; after the maintainer's review, one scoped re-review | `sdd-triage` |
| What is open, is it mergeable, what next | `sdd-pr status` (`tools/sdd-pr.py`) |
| Traceability, drift, the drift gate, lint, a REQ's context (report-only); `--audit` for the isolated whole-tree audit | `sdd-trace` |
| Regenerate the indexes and status lines from the map | the vendored `generate`, which every skill that changes the map runs |
| Does the code satisfy the `SPEC §` it cites, clause by clause | `sdd-spec-conformance-reviewer` agent |
| Review a requirement, spec or ADR for boundary violations | `sdd-doc-reviewer` agent |

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is **optional**. Its exploration workflows (brainstorming) are a good way to open an idea before `/sdd-specify`. Planning, execution, verification, review and branch finishing are covered here — `/sdd-deliver`, `sdd-implementer`, the findings file, the close-out — and running both over the same work duplicates the loop. How the orchestrator plans is its own business: a plan is a temporary working file; a committed one carries `kind: plan`, and nothing reviews or cites it.

## Guardrails this layer enforces

- **No code-first (formal profile).** When asked to implement behaviour that no `REQ` and no spec covers, do not jump to code: explore if the idea is new, record it with `sdd-specify`, deliver with `sdd-deliver`. The exception is *implementation-aligned* work on shipped code, whose spec is updated in the **same** change. On the informative profile, route the change to `sdd-deliver`: a clear task and a known verification command are enough.
- **One source of truth.** The canonical spec lives in `paths.specifications` (default `docs/specifications/`); a plan is never a source of truth, and no second tree of design documents may become one.
- **One home per fact, in process prose too:** commit and PR bodies, the changelog and review threads cite identifiers instead of restating (`references/artefact-prose.md`).
- **Never settle an open question silently** — an ADR (`sdd-specify`), a `STRAND`, or back to brainstorming.
- **Check the descriptor.** No `docs/.sdd.yaml` means the repo isn't scaffolded: route to `sdd-scaffold`.
- **Never hand-edit a generated block**; the skill that changes the map runs `sdd-check generate` (`references/sdd-check.md`).

## Reference

- `references/sdd-methodology.md` — the rules.
- `references/review.md` — the findings file, severities, evidence and the forge mirror.
- `references/sdd-check.md` · `references/traceability-schema.md` · `references/artefact-prose.md`.

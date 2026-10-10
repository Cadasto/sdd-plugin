---
name: spec-driven-development
description: This skill should be used when the user asks "what is SDD", "explain spec-driven development", "how does the spec workflow work here", "which /sdd command do I use", or asks to implement, build, or add behaviour in a repository with docs/.sdd.yaml before a REQ or spec exists. Explains the methodology, routes intent to the right sdd-* skill, and blocks code-first work. Not for performing an artefact action (the sdd-* skills do that).
allowed-tools: Read, Grep, Glob
---

# Spec-Driven Development — awareness and routing

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code); `references/…` resolves from it.

Explain and route; do no artefact work. Ground every answer in `references/sdd-methodology.md`; never improvise a rule.

## Core idea (state this when explaining SDD)

The **specification — not the code, not the prompt — is the source of truth.** Code is measured against it; when they disagree the spec wins, unless a section is explicitly *implementation-aligned*. The plugin targets the **spec-anchored** rung: stable identifiers, a machine-checked traceability map, CI that fails on drift.

**Two profiles** (methodology §1a): `formal`, the above; `informative`, a knowledge base where code leads and only the constitution binds.

## The delivery surface

```
/sdd-specify  →  /sdd-deliver  →  /sdd-review  →  /sdd-triage  →  /sdd-deliver --close-out  →  /sdd-triage --backlog
```

| Intent | Route to |
|---|---|
| Set up or upgrade the SDD docs structure (`--upgrade`) | `sdd-scaffold` |
| Capture a capability, make behaviour normative, record a decision, amend a spec § | `sdd-specify` |
| Deliver a change: the dispatch gate, workers, gates, the first review pass, the pull request; close out the requirement and write the PR body (`--close-out`) | `sdd-deliver` |
| A review pass (code, conformance, documents) into the findings file; panel prompts (`--panel`) | `sdd-review` |
| Work the open findings; after merges, carry the leftovers to the backlog (`--backlog`) | `sdd-triage` |
| What is open, is it mergeable, what next | `sdd-pr status` (`tools/sdd-pr.py`) |
| Traceability, drift, the drift gate, lint, a REQ's context (report-only); `--audit` for the isolated whole-tree audit | `sdd-trace` |

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is **optional**: its brainstorming opens an idea before `/sdd-specify`. Planning, execution, review and branch finishing are covered here; running both over the same work duplicates the loop.

## Guardrails this layer enforces

- **Read `docs/.sdd.yaml` first** for `profile`; none: the repo isn't scaffolded, route to `sdd-scaffold`.
- **No code-first (formal profile).** When asked to implement behaviour that no `REQ` and no spec covers, do not jump to code: explore if the idea is new, record it with `sdd-specify`, deliver with `sdd-deliver`. The exception is *implementation-aligned* work on shipped code, whose spec is updated in the **same** change. On the informative profile, route it to `sdd-deliver`.
- **One source of truth.** The specs under `paths.specifications`, never a plan or a second design tree.
- **One home per fact, in process prose too:** commit and PR bodies, the changelog and review threads cite identifiers instead of restating (`references/artefact-prose.md`).
- **Never settle an open question silently** — an ADR (`sdd-specify`), a `STRAND`, or back to brainstorming.
- **Never hand-edit a generated block**; `sdd-check generate` writes it (`references/sdd-check.md`).

## Reference

- `references/sdd-methodology.md` — the rules.
- `references/review.md` — the findings file, severities, evidence and the forge mirror.
- `references/sdd-check.md` · `references/traceability-schema.md` · `references/artefact-prose.md`.

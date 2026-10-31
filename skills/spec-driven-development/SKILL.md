---
name: spec-driven-development
description: This skill should be used when the user asks "what is SDD", "explain spec-driven development", "how does the spec workflow work here", "which /sdd command do I use", or asks to implement, build, or add behaviour in a repository with docs/.sdd.yaml before a REQ or spec exists. Explains the methodology, routes intent to the right sdd-* skill, and keeps a new capability spec-first. Not for performing an artefact action (the sdd-* skills do that).
allowed-tools: Read, Grep, Glob
---

# Spec-Driven Development — awareness and routing

> The plugin root is the folder that holds this skill's `skills/` folder (`${CLAUDE_PLUGIN_ROOT}` on Claude Code): take it from this file's own path, `\` turned into `/`, and never search the disk for it; `references/…` resolves from it.

Explain and route; do no artefact work. Ground every answer in [sdd-methodology.md](../../references/sdd-methodology.md); never improvise a rule.

## Core idea (state this when explaining SDD)

The **specification records the contract code is measured against; the maintainer's instruction outranks it.** When a request contradicts a sentence, name the sentence once, do the work, amend the sentence in the same change. Without the maintainer, a disagreement between code and spec is a finding, and the spec wins unless a section is *implementation-aligned* (methodology §7). The plugin targets the **spec-anchored** rung: stable identifiers, a machine-checked traceability map, CI that fails on drift.

**Two profiles** (methodology §1a): `formal`, the above; `informative`, a knowledge base where code leads and only the constitution binds.

## The delivery surface

```
/sdd-specify  →  /sdd-deliver  →  /sdd-review  →  /sdd-triage  →  /sdd-close  →  (merge)  →  /sdd-close
```

| Intent | Route to |
|---|---|
| Set up or upgrade the SDD docs structure (`--upgrade`) | `sdd-scaffold` |
| Capture a capability, make behaviour normative, record a decision, amend a spec §, retire a requirement | `sdd-specify` |
| Deliver a change: the dispatch gate, workers, gates, the first review pass, the pull request | `sdd-deliver` |
| Close out in the pull request (shipped, the PR body, ready); after the merge, remove the branch, its worktree and its findings | `sdd-close` |
| A review pass (code, conformance, documents) into the findings file | `sdd-review` |
| Work the open findings; now and then, carry merged pull requests' leftovers to the backlog and consolidate it (`--backlog`) | `sdd-triage` |
| What is open, is it mergeable, what next | `sdd-pr status` (`tools/sdd-pr.py`) |
| Traceability, drift, the drift gate, lint, a REQ's context (report-only); `--audit` for the isolated whole-tree audit | `sdd-trace` |

## Optional: a general engineering plugin

A general engineering plugin such as superpowers is **optional**: its brainstorming opens an idea before `/sdd-specify`. Planning, execution, review and branch finishing are covered here; running both over the same work duplicates the loop.

## Guardrails this layer enforces

- **Read `docs/.sdd.yaml` first** for `profile`; none: the repo isn't scaffolded, route to `sdd-scaffold`.
- **Spec-first for a new capability (formal profile).** When asked to add a capability that no `REQ` and no spec covers, do not jump to code: explore if the idea is new, record it with `sdd-specify`, deliver with `sdd-deliver`. Everything else on shipped code — a fix, hardening, a maintainer's instruction that a behaviour is wrong — is *implementation-aligned*: route it to `sdd-deliver`, code first, the sentence reconciled in the **same** change (methodology §7); never route it to `sdd-specify` first, and never argue from the sentence. On the informative profile, route everything to `sdd-deliver`.
- **One source of truth.** The specs under `paths.specifications`, never a plan or a second design tree. A keyword only for what a caller relies on (methodology §4).
- **One home per fact, in process prose too:** commit and PR bodies, the changelog and review threads cite identifiers instead of restating ([artefact-prose.md](../../references/artefact-prose.md)).
- **Never settle an open question silently** — an ADR (`sdd-specify`), a `STRAND`, or back to brainstorming.
- **Never hand-edit a generated block**; `sdd-check generate` writes it ([sdd-check.md](../../references/sdd-check.md)).

## Reference

- [sdd-methodology.md](../../references/sdd-methodology.md) — the rules.
- [review.md](../../references/review.md) — the findings file, severities, evidence and the forge mirror.
- [sdd-check.md](../../references/sdd-check.md) · [traceability-schema.md](../../references/traceability-schema.md) · [artefact-prose.md](../../references/artefact-prose.md).

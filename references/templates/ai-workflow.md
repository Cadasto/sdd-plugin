# AI workflow — the agent loop

What an AI agent does when working a change in this repo. Read [AGENTS.md](../../AGENTS.md) and [development-process.md](development-process.md) first.

This repo uses **Spec-Driven Development** for the specification/traceability layer and the **superpowers** plugin for the engineering loop. They are complementary — SDD keeps the spec the source of truth; superpowers plans, builds, tests, and finishes the branch.

## The loop

```
0. Explore (if the idea is new): superpowers:brainstorming → a design doc.
1. Specify: /sdd-specify — record the capability as a REQ, the normative behaviour as a SPEC § (RFC-2119),
   and any irreversible decision as an ADR. Assign IDs; wire traceability. (Don't read normative prose
   out of the index — follow to the canonical spec.)
2. Look up ground truth before editing — the source named in .sdd.yaml (ground_truth); never guess.
3. Plan & build with superpowers: writing-plans → executing-plans / test-driven-development.
   Land the plan in docs/plans/ with the SDD citing header (implements: [REQ-…, SPEC §]); cite REQ/PROBE
   ids in code and tests; update traceability.yaml as code lands.
4. Don't decide open questions in code — surface a STRAND or record an ADR (/sdd-specify), or ask.
5. Verify & review: superpowers:verification-before-completion (tests/build/lint) AND /sdd-trace (traceability/drift).
   Optionally /sdd-review — a spec-aware review (conformance + traceability) that can post findings to the PR.
6. Close out IN THE SAME PR: /sdd-archive (spec status, index, plan flip + git mv to archive/) as the final
   commit of the implementing branch, then superpowers:finishing-a-development-branch (merge / PR). The archive
   rides in the PR that implements the plan — not a follow-up PR.
```

> **Prose economy — one home per fact.** The commit body, PR body, changelog, and review comments each say
> only what lives nowhere else; cite `REQ`/`SPEC §`/plan/SHA rather than restating. See development-process.md.

## When stuck

- **Open decision?** Record an ADR (`/sdd-specify`) or ask — don't bake it into code.
- **Ambiguous spec?** Look it up in the named ground-truth source.
- **Missing rule?** Add a `Draft` `REQ` + spec (`/sdd-specify`) *before* coding — never a rule that lives only in code.

## Modes

- **New behaviour** → spec-first: `superpowers:brainstorming` → `/sdd-specify` → `superpowers:writing-plans` → build.
- **Hardening shipped code** → implementation-aligned: change the code, then update the spec § + guide in the **same** change set — "code wins until the spec is updated, in the same PR."

## Tooling

| Task | Owner |
|---|---|
| Explore / design | superpowers `brainstorming` |
| Set up / extend the SDD structure | `/sdd-scaffold` |
| Capture a capability, write a spec, record a decision | `/sdd-specify` |
| Decompose into tasks / write the plan | superpowers `writing-plans` (land in `docs/plans/`) |
| Build / TDD / execute | superpowers `executing-plans` / `test-driven-development` |
| Tests/build pass? | superpowers `verification-before-completion` |
| Code review of the *code* | superpowers `requesting-code-review` (or your installed reviewer) |
| Code satisfies the `SPEC §`/`REQ` it cites (conformance) | `sdd-spec-conformance-reviewer` agent |
| Traceability / drift / a REQ's context | `/sdd-trace` |
| Spec-aware review (conformance + traceability) posted to the PR | `/sdd-review` (opt-in) |
| Merge / PR / branch cleanup | superpowers `finishing-a-development-branch` |
| Close out the spec, index, and plan — in the implementing PR | `/sdd-archive` |

# AI workflow — the agent loop

What an AI agent does when working a change in this repo. Read [AGENTS.md](../../AGENTS.md) and
[development-process.md](development-process.md) first.

## The loop

```
0. Assemble context for the requirement in one shot — registry row + traceability block
   + canonical spec excerpt + any open strands.  (in-session: /sdd-trace REQ-…)
1. Locate the REQ → follow to its CANONICAL topic spec. Don't read normative prose out of the index.
2. Inspect ground truth before editing — look facts up in the source named in .sdd.yaml (ground_truth);
   never guess domain facts.
3. Cite identifiers in code comments and tests; update traceability.yaml when landing code.
4. Don't decide open questions in code — surface a STRAND or draft an ADR (/sdd-adr), or ask.
5. Verify with the full gate (/sdd-verify → `<build_entrypoint> <ci_target>`, including spec-check);
   for behaviour changes, check each PROBE's status.
```

## When stuck

- **Open decision?** Draft an ADR (`/sdd-adr`) or ask — don't bake it into code.
- **Ambiguous spec?** Look it up in the named ground-truth source.
- **Missing rule?** Add a `Draft` `REQ` (`/sdd-requirement`) *before* coding — never a rule that lives only in code.

## Modes

- **New behaviour** → spec-first: `/sdd-requirement` → `/sdd-spec` → `/sdd-plan` → `/sdd-implement`.
- **Hardening shipped code** → implementation-aligned: change the code, then update the spec § + guide in the
  **same** change set (`/sdd-implement` handles the reconcile step).

## Tooling

| Task | Skill |
|---|---|
| Set up / extend the SDD structure | `/sdd-scaffold` |
| Capture a capability | `/sdd-requirement` |
| Write normative behaviour | `/sdd-spec` |
| Record a decision | `/sdd-adr` |
| Break work into tasks | `/sdd-plan` |
| Work the plan | `/sdd-implement` |
| Context bundle + drift report | `/sdd-trace` |
| Definition of Done gate | `/sdd-verify` |
| Close out a feature | `/sdd-archive` |

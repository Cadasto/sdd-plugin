---
name: sdd-implement
description: This skill should be used when the user asks to "implement the plan", "work the next task", "build this feature against the spec", or "write the code for REQ-X". Executes plan tasks in order, ensures code and tests cite REQ-/PROBE- identifiers, reconciles the spec in-PR for implementation-aligned work, and never settles an open question silently. Not for creating the plan (use sdd-plan) or the final done-check (use sdd-verify).
argument-hint: "<plan file or REQ-id to implement>"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Implement against the spec

Execute the plan task by task, keeping code anchored to its requirement and the traceability chain intact. Read `docs/.sdd.yaml` for `ground_truth`, `build_entrypoint`, and `ci_target`. This skill writes source code (the only `sdd-*` skill that does), but the spec still leads.

## The loop (per task)

1. **Assemble context** — locate the `REQ`, follow to its **canonical** spec section (don't read normative prose out of the index). Use `sdd-trace REQ-…` for the one-shot bundle.
2. **Look up ground truth** for any domain fact via the source named in `.sdd.yaml` (`ground_truth`) — never guess.
3. **Implement the task.** Cite the `REQ`/`PROBE` id in the code (a package/module doc comment) and in the test name/comment, so the chain is greppable.
4. **Update the traceability map** as code/tests land — add `packages`, `tests`, `probes` to the requirement's record; flip `implementation` toward `landed`/`shipped`.
5. **Verify the task** with its named command before moving on.

## Two modes

- **Spec-first** (new behaviour): the spec already leads; implement to it.
- **Implementation-aligned** (hardening / perf / bug-fix on shipped code): the code may lead, **but update the affected `SPEC §` + guide in the same change set** and note it in the spec frontmatter. *"Code wins until the spec is updated — in the same PR."* Never let the spec silently lag.

## Guardrails

- **Never settle an open question in code.** A genuine fork → `sdd-adr` (or raise a `STRAND`) or ask. A missing rule → add a `Draft` `REQ`/spec *before* coding, never a rule that lives only in code.
- **Cite, don't orphan.** Code with no `REQ`, or a test that asserts a normative rule without naming it, is invisible to the traceability gate.
- **Don't expand scope.** Work the plan's tasks; new capability needs a new `REQ`.
- **Stop at "done"-claims.** Running the full gate and the Definition of Done belongs to `sdd-verify` — invoke it before declaring the work complete.

## Reference

- `references/sdd-methodology.md` — §7 the two modes, §8 cite-when-crossing, §10 the agent loop.
- `references/traceability-schema.md` — the record fields to update as code lands.

# Specifications — normative behaviour

The **how must it behave** layer. Topic specs carry RFC-2119 normative prose with stable section numbers;
each requirement's normative statements live in exactly **one** canonical section here.

Write and extend specs with `/sdd-specify`.

## Conventions

- **RFC-2119 keywords** mark force: **MUST/SHALL** (absolute), **SHOULD** (strong; exceptions need a reason),
  **MAY** (optional). No keyword ⇒ informative.
- **One canonical home** per requirement — the requirements index links here; prose is never duplicated.
- **Stable § numbers** — cite as `SPEC-<NAME> §N`. Never renumber a published section.
- Specs contain **no** checkbox task lists, file paths, or PR summaries — those belong in plans.
- The machine-readable [`traceability.yaml`](traceability.yaml) maps each `REQ` to its canonical section,
  packages, tests, and probes; the `spec-check` target validates it against the tree.

## Topic specs

| Spec | Topic | Status |
|------|-------|--------|
| `<SPEC-NAME>` | <topic> | Draft |

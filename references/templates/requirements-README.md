# Requirements — capability index

The registry of **what** this system must deliver. One row per `REQ-*`. This index **links** to each
requirement's canonical specification section; it never duplicates normative prose.

Add requirements with `/sdd-specify`. A requirement carries a capability, acceptance criteria, and
out-of-scope — **no file paths, no implementation detail.**

## Status axes

- **Spec stability** — `Draft` (binding now; wording may still change) → `Stable` (frozen) → `Deprecated`.
- **Implementation** — `proposed` → `in_progress` → `shipped`, plus `deferred`.

These are tracked **separately**: a `Draft` requirement is authoritative even while its code is `proposed`.

## Index

| ID | Title | Spec | Stability | Implementation |
|----|-------|------|-----------|----------------|
| <REQ-FOUND-001> | <capability> | `<SPEC-NAME §N>` | Draft | proposed |

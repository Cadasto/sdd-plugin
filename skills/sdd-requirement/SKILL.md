---
name: sdd-requirement
description: This skill should be used when the user asks to "add a requirement", "capture a capability", "create a REQ", "write a user story with acceptance criteria", or "register a capability we must deliver". Adds a REQ-* to the requirements index (and an optional detail file) with acceptance criteria and out-of-scope, assigning the next non-colliding identifier. Not for writing normative behaviour (use sdd-spec) or task breakdowns (use sdd-plan).
argument-hint: "<capability to capture> [area]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Capture a requirement (REQ-*)

A requirement states **what** must be delivered and **how it is accepted** — nothing about *how* to build it. Read `docs/.sdd.yaml` first for the identifier style and paths.

## Preconditions

- The repo is scaffolded (a `docs/.sdd.yaml` exists). If not, route to `sdd-scaffold`.

## Steps

1. **Read the descriptor** (`docs/.sdd.yaml`) for `req_style`, `req_areas`, `req_gap`, and `paths.requirements`.
2. **Assign the next identifier** without collision:
   - *area-prefixed*: `REQ-<AREA>-NNN` — scan the index for the highest `NNN` in that area, increment. Reject an area not in `req_areas` (adding an area is a deliberate, separate decision).
   - *flat-numeric*: next slot at the `req_gap` spacing (e.g. `REQ-050` → `REQ-060`), leaving room to insert.
3. **Draft from the template** (`references/templates/requirement.md`): capability (what + why), testable acceptance criteria, explicit out-of-scope, the two status fields (`status: draft`, `implementation: proposed`).
4. **Add the index row** to `docs/requirements/README.md` (ID, title, spec link placeholder, stability, implementation). For a substantial requirement, also write the detail file `REQ-<…>-<slug>.md`; for a small one, the index row alone is fine.
5. **Report** the new ID and the next step (`sdd-spec` to make the behaviour normative).

## Guardrails

- **No implementation detail.** No file paths, no migration steps, no "how". If the user supplies those, capture the capability and drop the rest (or route the "how" to `sdd-plan`/`sdd-spec`).
- **Acceptance criteria must be observable and testable** — "given X, the system does Y" — not restated intent.
- **Two status axes, tracked separately.** `status` is spec stability (`draft` is binding now); `implementation` is build state. Don't conflate them.
- **Don't write the normative prose here.** The requirement links to its canonical spec section; `sdd-spec` writes that prose, once.
- **Don't settle open questions.** If the capability hinges on an undecided fork, note it and route to `sdd-adr` (or raise a `STRAND`).

## Reference

- `references/templates/requirement.md` — the template.
- `references/sdd-methodology.md` — §3 boundary rules, §5 identifiers, §6 status axes.

---
name: sdd-adr
description: This skill should be used when the user asks to "record an architectural decision", "write an ADR", "resolve STRAND-N", "document why we chose X over Y", or "lock in a design decision". Creates ADR-NNNN-<slug>.md (Status/Context/Decision/Consequences), updates the ADR index, cites the STRAND it resolves and the REQs it amends. Not for normative behaviour (use sdd-spec) or capturing a capability (use sdd-requirement).
argument-hint: "<the decision to record> [resolves STRAND-NN]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Record an architectural decision (ADR)

An ADR captures **one irreversible fork** and why it was taken. Long flows and schema DDL stay in the specs; one decision per ADR. Read `docs/.sdd.yaml` for `paths.adr`.

## Steps

1. **Assign the next number** — scan `paths.adr` for the highest `ADR-NNNN`, increment. Numbers are sequential and **never reused**.
2. **Draft from the template** (`references/templates/adr.md`):
   - **Status** — `proposed` now; it MUST be `accepted` before code depends on it.
   - **Context** — the forces at play; why this is an irreversible fork worth recording.
   - **Decision** — the choice, stated plainly.
   - **Consequences** — what becomes easier, harder, or permanently constrained (honest about costs).
3. **Wire traceability:**
   - If it resolves an open question, cite the `STRAND-NN` and **close the strand** with a backlink to this ADR.
   - List the `REQ-*` it amends, and update those requirements if the decision changes their acceptance.
4. **Update the ADR index** (`docs/adr/README.md`): number, title, status.
5. **Report** and, if the decision unblocks behaviour, suggest `sdd-spec` to make it normative.

## Guardrails

- **One decision per ADR.** Split a "we decided A and also B" into two.
- **Accepted before code.** Don't let implementation depend on a `proposed` ADR.
- **Don't relitigate in code.** Once accepted, an ADR is the record; supersede it with a new ADR (status `superseded by ADR-NNNN`) rather than quietly changing course.
- **No normative prose here.** Behaviour goes in a spec; the ADR records the *decision*, not the rules.

## Reference

- `references/templates/adr.md` — the template.
- `references/sdd-methodology.md` — §5 (the STRAND lifecycle), §3 (ADR boundary rules).

---
kind: guide
---

# Decisions — architecture decision records

The record of **irreversible choices**: one decision per `ADR-NNNN`, numbered sequentially and never
reused. Long flows and schema detail stay in the specs; an ADR states the fork, the choice, and its
consequences.

Record decisions with `/sdd-specify`. An ADR is `accepted` before code depends on it.

## Status

`proposed` → `accepted` → `superseded by ADR-NNNN` | `deprecated`. An accepted ADR is amended in place:
a stale part is rewritten to the current state, with one `**Amended:**` line under its status and date.
It is `superseded` only when another ADR takes over its whole decision, and `deprecated` when the
decision is withdrawn with nothing in its place.

## Index

The table below is generated from the decision records by `sdd-check generate`. Never hand-edit it.

<!-- sdd:generated adr-index -->

| ID | Title | Status | Date | Resolves / amends |
|---|---|---|---|---|

<!-- /sdd:generated -->

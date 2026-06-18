---
name: sdd-spec
description: This skill should be used when the user asks to "write a spec", "make this behaviour normative", "extend the spec for REQ-X", "add an RFC-2119 requirement", or "specify how the system must behave". Writes normative prose into the single canonical topic spec section and wires the traceability map. Not for capturing a capability (use sdd-requirement), task breakdowns (use sdd-plan), or recording a decision (use sdd-adr).
argument-hint: "<REQ-id or behaviour to specify>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Write / extend a normative specification

A specification states **how the system MUST/SHOULD/MAY behave**, in RFC-2119 prose, with stable section numbers. Each requirement's normative prose has exactly **one** canonical home. Read `docs/.sdd.yaml` first.

## Preconditions

- A `REQ-*` exists for this behaviour. If not, route to `sdd-requirement` first.
- Know the canonical topic spec (by subject, e.g. `wire.md`, `auth.md`) and the section that should own this prose.

## Steps

1. **Locate the canonical home.** Open the topic spec under `paths.specifications`. Confirm no other file already owns this prose — if it does, edit there; never create a second copy.
2. **Look up ground truth** for any domain fact (paths, codes, wire shapes) in the source named in `.sdd.yaml` (`ground_truth`). Never guess domain facts.
3. **Write the statement** with explicit RFC-2119 keywords — **MUST/SHALL** (absolute), **SHOULD** (strong; exceptions need a stated reason), **MAY** (optional). Give it a stable `§N` anchor. No task lists, no file paths, no PR summaries.
4. **Set/verify the `Status:` header** — `Draft` pre-1.0 (binding regardless), `Stable` once frozen.
5. **Wire the index row** in `docs/requirements/README.md` to the canonical anchor (`path#anchor`) — a link only, no prose copy.
6. **Add/update the traceability entry** (`canonical`, `status`, `implementation`, and `packages`/`tests`/`probes` as they land) per `references/traceability-schema.md`.
7. **Report** and suggest the next step (`sdd-plan` to schedule implementation, or `sdd-adr` if a fork surfaced).

## Guardrails

- **One canonical home — never duplicate normative prose.** This is the cardinal rule; two copies guarantee drift.
- **Normative force is explicit.** Every binding statement carries a keyword; keyword-free text is informative and must not be implemented as a requirement.
- **Keep kinds separate.** No checkbox tasks (those are plans), no file paths, no "we decided X" narrative (that's an ADR).
- **Don't invent domain facts** — resolve them via the named ground-truth source.
- **`Draft` is binding.** Don't treat a draft spec as provisional; it is authoritative now, its wording may still change.

## Reference

- `references/templates/specification.md` — the template.
- `references/traceability-schema.md` — the traceability record to add/update.
- `references/sdd-methodology.md` — §4 RFC-2119, §5 single canonical home, §8 the chain.

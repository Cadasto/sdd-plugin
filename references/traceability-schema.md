# Traceability map & project descriptor — schema

The two machine-readable files that make SDD governable. `sdd-scaffold` creates both; the other skills read and update them. See [sdd-methodology.md §8](sdd-methodology.md) for how the traceability map fits the chain.

## 1. The project descriptor — `docs/.sdd.yaml`

A tiny per-repo config so the skills stay repo-agnostic. **Every skill reads it first** to learn this repo's conventions; none of them hard-code paths or identifier styles.

```yaml
sdd:
  # Identifier style for requirements. Pick one and never switch (it would renumber IDs).
  req_style: area-prefixed          # area-prefixed | flat-numeric
  req_areas: [FOUND, EHR, CLIN, AUTH, HARD]   # required iff req_style == area-prefixed
  req_gap: 10                       # decadal gap for flat-numeric (REQ-010, REQ-020, …)

  paths:
    requirements: docs/requirements
    specifications: docs/specifications
    adr: docs/adr
    plans: docs/plans
    plans_archive: docs/plans/archive

  traceability: docs/specifications/traceability.yaml

  # The single build entry point. Every check is a target so CI and humans run the same thing.
  build_entrypoint: make            # make | task | just | npm
  ci_target: ci                     # the full PR gate: `make ci`, `task ci`, `npm run ci`
  spec_check_target: spec-check     # the traceability drift gate

  # Optional capabilities — omit if the repo doesn't use them.
  use_probes: true                  # PROBE-NNN conformance probes
  use_strands: true                 # STRAND-NN open research questions
  upstream: ""                      # sibling SDD repo this one consumes (cross-repo gap drafts); blank if none

  # The authoritative source for this repo's domain facts. Agents MUST look facts up here,
  # never guess. Free text — e.g. a domain MCP, an internal spec registry, an API reference.
  ground_truth: "<the authoritative source for this repo's domain facts>"
```

### Fields

| Field | Meaning |
|---|---|
| `req_style` | `area-prefixed` (`REQ-AUTH-001`) or `flat-numeric` (`REQ-050`). Drives how `/sdd-specify` assigns the next ID. |
| `req_areas` | The allowed area tokens (area-prefixed only). New areas are a deliberate, reviewed addition. |
| `req_gap` | Spacing for flat-numeric IDs so new requirements slot in without renumbering. |
| `paths.*` | Where each document kind lives. Skills resolve all locations from here. |
| `traceability` | Path to the traceability map. |
| `build_entrypoint` / `ci_target` / `spec_check_target` | The build tool and the target names `/sdd-trace` (and superpowers' verification) invoke. |
| `use_probes` / `use_strands` | Toggle the optional `PROBE`/`STRAND` machinery. |
| `upstream` | The sibling SDD repo this one files cross-repo gap drafts against (see `references/cross-repo-gap.md`). |
| `ground_truth` | The named "look it up, don't guess" source for domain facts. |

## 2. The traceability map — `traceability.yaml`

One record per requirement, linking it to its canonical spec section and to the code/tests/probes/plans that realise it. This is an **index** — it carries no normative prose.

```yaml
# traceability.yaml — machine-readable REQ → spec → code → test map.
# Validated against the tree by the `spec-check` target. Do not put requirement prose here.
requirements:
  - id: REQ-040
    title: Type registry
    canonical: docs/specifications/rm-modeling.md#type-registry-req-040
    status: draft               # spec stability:   draft | stable | deprecated
    implementation: landed      # build status:     planned | partial | landed   (or proposed | in_progress | shipped | deferred)
    packages:
      - openehr/rm/typereg
    probes:                     # optional (use_probes)
      - PROBE-031
      - PROBE-073
    tests:
      - openehr/serialize/canjson/edgecases_test.go
    plans:
      - docs/plans/archive/2026-05-12-type-registry.md
```

### Record fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | The `REQ-*` identifier. Immutable once published. |
| `title` | yes | Short human label (mirrors the index row). |
| `canonical` | yes | Link to the **single** spec section that owns this requirement's normative prose (`path#anchor`). |
| `status` | yes | Spec stability — `draft` / `stable` / `deprecated`. `draft` is binding (see methodology §6). |
| `implementation` | yes | Build status. Use the repo's chosen vocabulary consistently. |
| `packages` | when landed | Source packages/modules that implement it. |
| `tests` | when landed | Test files that assert it. |
| `probes` | optional | `PROBE-*` ids (conformance probes), if `use_probes`. |
| `plans` | optional | Plan(s) that delivered it (active or archived). |

### What `spec-check` verifies

The drift gate fails when the map and the tree disagree, surfacing each orphan class:

- a `canonical` link points at a missing file or anchor;
- a listed `package`, `test`, or `plan` path does not exist;
- a `PROBE` id has no corresponding test;
- a requirement marked `landed`/`shipped` has no `packages` or `tests`;
- a requirement exists in the index but not the map (or vice-versa).

`/sdd-trace` reports these in-session and may run the real `spec_check_target`; generic test/build verification before a done-claim is `superpowers:verification-before-completion`, and `/sdd-archive` performs the close-out.

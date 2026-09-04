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

  # Delivery parameters. /sdd-deliver and /sdd-review read these instead of asking.
  # Every value here is an EXAMPLE — no model and no reviewer is required by the plugin.
  agents:
    worker_model: opus              # model override /sdd-deliver passes on each worker dispatch
    max_parallel_workers: 3
    worktree_per_worker: true       # parallel, mutating tasks only
    worker_skills: []               # skills named in the worker's brief, e.g. [go-coding:go-testing]
    reviewers: []                   # this repo's own language reviewers, by agent name
    task_review: lane               # on | off | lane  (lane = on for full, off for maintenance)
    review_panel:                   # who reviews the PR, per lane; names are prompt targets, not integrations
      full: [claude, cursor]
      maintenance: [claude]
```

### Fields

| Field | Meaning |
|---|---|
| `req_style` | `area-prefixed` (`REQ-AUTH-001`) or `flat-numeric` (`REQ-050`). Drives how `/sdd-specify` assigns the next ID. |
| `req_areas` | The allowed area tokens (area-prefixed only). New areas are a deliberate, reviewed addition. |
| `req_gap` | Spacing for flat-numeric IDs so new requirements slot in without renumbering. |
| `paths.*` | Where each document kind lives. Skills resolve all locations from here. |
| `traceability` | Path to the traceability map. |
| `build_entrypoint` / `ci_target` / `spec_check_target` | The build tool and the target names `/sdd-trace` and the delivery gates invoke. |
| `use_probes` / `use_strands` | Toggle the optional `PROBE`/`STRAND` machinery. |
| `upstream` | The sibling SDD repo this one files cross-repo gap drafts against (see `references/cross-repo-gap.md`). |
| `ground_truth` | The named "look it up, don't guess" source for domain facts. |

### `agents:` fields

| Field | Meaning |
|---|---|
| `worker_model` | The model `/sdd-deliver` passes as the **per-dispatch override** when it dispatches a worker. |
| `max_parallel_workers` | Ceiling on workers running at once. Sequential plans run one. |
| `worktree_per_worker` | Give each parallel, mutating worker its own git worktree. A worktree is real setup cost; pay it only where parallelism pays back. |
| `worker_skills` | Skills a worker should apply. **Named in the brief**, not preloaded in frontmatter. |
| `reviewers` | The repository's own language reviewers, by agent name. Used for the per-task gate and as the code-review member of the review panel. |
| `task_review` | `on` · `off` · `lane`. `lane` means on for the full lane and off for the maintenance lane. |
| `review_panel.full` / `review_panel.maintenance` | Which reviewers `/sdd-review --panel` prints a prompt block for, per lane. Values are **examples**; a repository picks its own, and none is mandated. |

> **`worker_model` is applied per dispatch, never written into an agent file.** Plugin agent definitions
> live in the host's read-only install cache, so no skill can rewrite their frontmatter. `sdd-implementer`
> ships `model: inherit` and the driver overrides it on each dispatch.

> **The descriptor learns no lane field.** The lane is a property of a change, declared in the PR body
> ([sdd-methodology.md §12](sdd-methodology.md)) — not a property of a repository.

## 2. The traceability map — `traceability.yaml`

One record per requirement, linking it to its canonical spec section and to the code/tests/probes that realise it. This is an **index** — it carries no normative prose.

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

### What `spec-check` verifies

The drift gate fails when the map and the tree disagree, surfacing each orphan class:

- a `canonical` link points at a missing file or anchor;
- a listed `package` or `test` path does not exist;
- a `PROBE` id has no corresponding test;
- a requirement marked `landed`/`shipped` has no `packages` or `tests`;
- a requirement exists in the index but not the map (or vice-versa).

> **A record has no plan axis and no `pr:` pointer.** The implementing change is found by searching the
> repository history for the `REQ` id, which every commit, PR title, and test name already carries. A
> pointer would be one more copy of a fact that can lag.

`/sdd-trace` reports these in-session and may run the real `spec_check_target`; the full build gate before a done-claim is `<build_entrypoint> <ci_target>`, and `/sdd-archive` performs the close-out.

## 3. The plan frontmatter

A plan is a working file, not a governed artefact ([sdd-methodology.md §9](sdd-methodology.md)), but its
frontmatter is machine-read by `/sdd-archive` and `/sdd-finalize`, so it is a contract:

```yaml
---
plan: <YYYY-MM-DD-slug>
implements: [<REQ-…>, <SPEC-NAME §N>]
mode: spec-first          # spec-first | implementation-aligned
status: active            # active | done | postponed | abandoned
---
```

| Key | Required | Meaning |
|---|---|---|
| `plan` | yes | `YYYY-MM-DD-<slug>`, matching the filename. |
| `implements` | yes | The identifiers this plan delivers. A plan that cites none is not a plan. |
| `mode` | yes | Which source-of-truth mode this slice runs in (methodology §7). |
| `status` | yes | `active` · `done` · `postponed` · `abandoned`. `/sdd-archive` sets `done` in place; `/sdd-finalize` deletes `done` and `abandoned` at the next version bump and never touches `active` or `postponed`. |

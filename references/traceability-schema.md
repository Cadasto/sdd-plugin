# Traceability map & project descriptor — schema

The two machine-readable files that make SDD governable. `sdd-scaffold` creates both; the other skills read and update them. See [sdd-methodology.md §8](sdd-methodology.md) for how the traceability map fits the chain.

## 1. The project descriptor — `docs/.sdd.yaml`

A tiny per-repo config so the skills stay repo-agnostic. **Every skill reads it first** to learn this repo's conventions; none of them hard-code paths or identifier styles.

```yaml
sdd:
  profile: full                     # full | lightweight

  # Identifier style for requirements. Pick one and never switch (it would renumber IDs).
  req_style: area-prefixed          # area-prefixed | flat-numeric
  req_areas: [FOUND, EHR, CLIN, AUTH]   # required iff req_style == area-prefixed
  req_gap: 10                       # decadal gap for flat-numeric (REQ-010, REQ-020, …)
  excluded_areas: []                # area-prefixed only; tokens that are deliberately not areas

  # The document-kind vocabulary every `kind:` frontmatter value is checked against.
  doc_kinds: [requirement, specification, adr, plan, guide, analysis, operations, reference, upstream]

  default_mode: spec-first          # the mode a specification has when its frontmatter names none

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

  upstream: ""                      # or a map of named relations:
  # upstream:
  #   <name>:
  #     repo: <module path or URL>
  #     role: consumed | platform-context | ground-truth
  #     authority: upstream-leads | local-leads
  #     gap_drafts: docs/<name>-gap-drafts     # role: consumed only

  # The authoritative source for this repo's domain facts. Agents MUST look facts up here,
  # never guess. One source, or an ordered list consulted first to last.
  ground_truth: "<one source>"

  check:
    script: scripts/sdd-check.py   # where the vendored gate lives
    version: "0.6.0"               # must equal the vendored tool's own version
    links:
      exclude: []                  # globs; printed in every report when non-empty
    changelog:
      path: CHANGELOG.md
      max_words: 35
    code_roots: []                 # for tree-to-map; empty = the repository minus docs/, .git/, vendor/, node_modules/
    test_globs: ["*_test.go", "test_*.py", "*_test.py", "*Test.php", "*.test.ts", "*.spec.ts", "*_test.rs"]
    probes_catalogue: ""           # a document whose headings carry PROBE ids; empty = a probe resolves through a cited test
    families:                      # error | warn | off
      descriptor: error
      map-schema: error
      map-to-tree: error
      index-sync: error
      plans: error
      tree-to-map: warn
      doc-kinds: warn
      rfc2119: warn                # the per-kind table in sdd-check.md still errors for requirement/adr/plan/reference
      one-home: error
      links: error
      changelog: warn
      generated: error
      draft-reason: off

  hooks:
    stop_nudge: true               # the session-stop hook's one-shot "record progress" nudge; false disables it in this repository

  # Delivery parameters. /sdd-deliver and /sdd-review read these instead of asking.
  # Every value here is an EXAMPLE — no model and no reviewer is required by the plugin.
  agents:
    worker_model: inherit           # per-dispatch model override; inherit = no override, or a host model id
    max_parallel_workers: 3
    worktree_per_worker: true       # parallel, mutating tasks only
    worker_skills: []               # skills named in the worker's brief, e.g. [go-coding:go-testing]
    reviewers: []                   # this repo's own language reviewers, by agent name; /sdd-scaffold suggests from the build manifests
    task_review: lane               # on | off | lane  (lane = on for full, off for maintenance)
    review_panel:                   # who reviews the PR, per lane; names are prompt targets, not integrations
      full: [claude, cursor]
      maintenance: [claude]
```

### Fields

| Field | Meaning |
|---|---|
| `profile` | `full` or `lightweight` — how much structure this repository's docs tree has. See **Profiles** below. |
| `req_style` | `area-prefixed` (`REQ-AUTH-001`) or `flat-numeric` (`REQ-050`). Drives how `/sdd-specify` assigns the next ID. |
| `req_areas` | The allowed area tokens (area-prefixed only). New areas are a deliberate, reviewed addition. |
| `req_gap` | Spacing for flat-numeric IDs so new requirements slot in without renumbering. |
| `excluded_areas` | Area tokens this repository has deliberately excluded (area-prefixed only). An identifier that uses one is rejected (methodology §5). |
| `doc_kinds` | The document-kind vocabulary a document's `kind:` frontmatter is checked against (methodology §3). |
| `default_mode` | The source-of-truth mode a specification has when its own frontmatter names none (methodology §7). |
| `paths.*` | Where each document kind lives. Skills resolve all locations from here. |
| `traceability` | Path to the traceability map. |
| `build_entrypoint` / `ci_target` / `spec_check_target` | The build tool and the target names `/sdd-trace` and the delivery gates invoke. |
| `use_probes` / `use_strands` | Toggle the optional `PROBE`/`STRAND` machinery. |
| `upstream` | The upstream relations this repository has: one scalar repo, or a map of named relations with `repo`, `role`, `authority` and `gap_drafts` (see [cross-repo-gap.md](cross-repo-gap.md)). |
| `ground_truth` | The named "look it up, don't guess" source for domain facts. One source, or an ordered list consulted first to last; a local checkout is a cache, not the basis of a claim. |
| `check.*` | The shared gate's configuration. See **The check block** below. |
| `hooks.stop_nudge` | Whether the plugin's session-stop hook may nudge once when a session made no commit and leaves uncommitted changes. `true` by default. |

### Profiles

`profile: lightweight` means `paths.requirements` may name a **file** (a single registry index, no detail
files) and `paths.specifications` may name a **file** (one document that carries the normative sections
and, outside them, informative narrative). `full` requires directories.

> **The legacy forms stay valid.** A scalar `ground_truth` and a scalar `upstream` are read as before.

### The check block

| Key | Meaning |
|---|---|
| `script` | Where the vendored gate lives in this repository. |
| `version` | The pinned gate version. It must equal the vendored tool's own version, or the gate refuses to run. |
| `links.exclude` | Globs the `links` family skips. Printed in every report when non-empty. |
| `changelog.path` / `changelog.max_words` | The changelog the `changelog` family lints, and the per-bullet word budget. |
| `code_roots` | Where `tree-to-map` looks for cited identifiers. Empty means the repository minus `docs/`, `.git/`, `vendor/` and `node_modules/`. |
| `test_globs` | What counts as a test file. |
| `probes_catalogue` | A document whose headings carry `PROBE` ids. Empty means a probe resolves through a cited test. |
| `families` | Per-family severity — `error` · `warn` · `off`. The families and the rules each one applies are in [sdd-check.md](sdd-check.md). |

### `agents:` fields

| Field | Meaning |
|---|---|
| `worker_model` | The model `/sdd-deliver` passes as the **per-dispatch override** when it dispatches a worker; `inherit` passes none. A model id is host-specific, so the default is `inherit`. |
| `max_parallel_workers` | Ceiling on workers running at once. Sequential plans run one. |
| `worktree_per_worker` | Give each parallel, mutating worker its own git worktree. A worktree is real setup cost; pay it only where parallelism pays back. |
| `worker_skills` | Skills a worker should apply. **Named in the brief**, not preloaded in frontmatter. |
| `reviewers` | The repository's own language reviewers, by agent name. Used for the per-task gate and as the code-review member of the review panel. `/sdd-scaffold` suggests a value from the build manifests in the tree; the maintainer confirms it. |
| `task_review` | `on` · `off` · `lane`. `lane` means on for the full lane and off for the maintenance lane. |
| `review_panel.full` / `review_panel.maintenance` | Which reviewers `/sdd-review --panel` prints a prompt block for, per lane. Values are **examples**; a repository picks its own, and none is mandated. |

> **`worker_model` is applied per dispatch, never written into an agent file.** Plugin agent definitions
> live in the host's read-only install cache, so no skill can rewrite their frontmatter. `sdd-implementer`
> ships `model: inherit` and the driver overrides it on each dispatch when `worker_model` names a model.

> **The descriptor learns no lane field.** The lane is a property of a change, declared in the PR body
> ([sdd-methodology.md §12](sdd-methodology.md)) — not a property of a repository.

## 2. The traceability map — `traceability.yaml`

One record per requirement, linking it to its canonical spec section and to the code/tests/probes that realise it. This is an **index** — it carries no normative prose.

```yaml
# traceability.yaml — machine-readable REQ → spec → code → test map.
# Validated against the tree by the `spec-check` target. Do not put requirement prose here.
requirements:
  - id: REQ-040
    title: Token refresh
    canonical: docs/specifications/auth.md#token-refresh-req-040
    status: draft               # spec stability:   draft | stable | deprecated
    implementation: landed      # build status:     planned | partial | landed   (or proposed | in_progress | shipped | deferred)
    packages:
      - internal/auth/refresh
    probes:                     # optional (use_probes)
      - PROBE-031
      - PROBE-073
    tests:
      - internal/auth/refresh_test.go
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
| `operations` | when landed | Runbook paths — the evidence an operations requirement has landed. |
| `draft_reason` | when draft | Why the wording is still `draft`. Required by the `draft-reason` family when the record is `status: draft` and enforced. |

An unknown key on a record is reported as a warning, never an error; the retired `plans` key is one such warning.

### What the gate verifies

The gate is `sdd-check`; its families and rules are in [sdd-check.md](sdd-check.md).

> **A record has no plan axis and no `pr:` pointer.** The implementing change is found by searching the
> repository history for the `REQ` id, which every commit, PR title, and test name already carries. A
> pointer would be one more copy of a fact that can lag.

`/sdd-trace` reports drift in-session and may run the real `spec_check_target`; the full build gate before a done-claim is `<build_entrypoint> <ci_target>`, and `/sdd-archive` performs the close-out.

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

## 4. Generated blocks

Three indexes are derived from the map rather than written by hand. Each one lives between a pair of
markers:

```markdown
<!-- sdd:generated requirements-index -->
…table…
<!-- /sdd:generated -->
```

The block names are `requirements-index`, `specifications-index` and `adr-index`.

Text between the markers is written by `sdd-check generate` and verified by the `generated` family; a
hand edit fails the gate. The two frontmatter lines `status:` and `implementation:` in a requirement
detail file are also written by `generate` from the map.

---
kind: guide
---

# CI — how the methodology is enforced

CI is *operational process*, not part of the normative contract — but it is where SDD drift is caught
mechanically. Two enabling policies:

1. **One build entry point.** Every check is a target of the build tool declared in
   [`.sdd.yaml`](.sdd.yaml) (`<build_entrypoint>`); CI and contributors run the *same* commands. No logic
   lives only in CI YAML. The full PR gate is `<build_entrypoint> <ci_target>`.
2. **Reproducible toolchain.** Pin tool versions; route through a container when the host lacks a runtime
   so the gate is identical everywhere.

## Jobs

| Job | Enforces |
|---|---|
| **format-check** | the tree is formatted (no diff) |
| **lint** | pinned linter, same config as local |
| **build / typecheck** | it compiles |
| **test** | unit tests pass |
| **derived-artefact-verify** | committed generated files match their source (schema, OpenAPI, codegen) |
| **spec-check** | the shared gate `sdd-check`: map ↔ tree, index = map, document kinds, links and fragments, RFC-2119 and one-home, changelog bullets, generated blocks — one selftested tool, families configured in `.sdd.yaml` |
| **(scheduled) drift bot** | re-runs codegen / `spec-check` on a clean checkout; fails the scheduled run and reports the drift it found between PRs |
| **(scheduled) upstream watcher** | re-runs the checks against a pinned upstream (a spec release, a toolchain, a base image) and fails the run on drift — optional, per repository |

The non-negotiable SDD gate is **`spec-check`** (`<build_entrypoint> <spec_check_target>`): it turns
"we have specs" into "our specs can't silently rot", and it runs on **both** lanes. Before a done-claim,
run the full build gate (`<build_entrypoint> <ci_target>`) and read its output, then `/sdd-trace` for
traceability drift, including a plan whose `status` disagrees with its `REQ` — `/sdd-trace` reports it in
session; `spec-check` fails on it. `/sdd-review` writes the review ledger onto the PR and `/sdd-archive`
performs the close-out inside the implementing PR.

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
| **spec-check** | the traceability map matches the tree — every cited path/probe/test exists; no orphan `REQ`, plan, or probe |
| **(scheduled) drift bot** | re-runs codegen / `spec-check` on a clean checkout; opens a tracking issue on drift between PRs |

The non-negotiable SDD gate is **`spec-check`** (`<build_entrypoint> <spec_check_target>`): it turns
"we have specs" into "our specs can't silently rot." Before a done-claim, run the full build gate via
`superpowers:verification-before-completion` (tests/build/lint) **and** `/sdd-trace` (traceability/drift);
`/sdd-trace` reports drift in-session without modifying anything, `/sdd-review` (opt-in) can post a spec-aware review to the PR, and `/sdd-archive` performs the close-out inside the implementing PR.

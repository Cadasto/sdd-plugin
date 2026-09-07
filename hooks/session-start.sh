#!/usr/bin/env bash
# SessionStart hook (host-agnostic): when a Spec-Driven Development repository is detected, print one
# context line plus the available /sdd-* surface. Always exits 0 so the assistant reads stdout and is
# never blocked.
set -u

is_sdd_repo() {
  [ -f docs/.sdd.yaml ] && return 0
  [ -d docs/specifications ] && return 0
  [ -f docs/specifications/traceability.yaml ] && return 0
  return 1
}

if is_sdd_repo; then
  echo "› Spec-Driven Development repo detected — the specification is the source of truth (read docs/.sdd.yaml + AGENTS.md before editing). SDD skills: /sdd-specify (REQ/SPEC/ADR) · /sdd-deliver (plan → workers → draft PR) · /sdd-review (spec-aware review + panel prompts) · /sdd-triage (work a review round) · /sdd-trace (traceability/drift) · /sdd-archive (close out the plan in its PR) · /sdd-finalize (sweep finished plans at a version bump) · /sdd-scaffold. Plans live in docs/plans/, are flipped to done in place, and are swept at the next release. Run /sdd-trace + the build's spec-check before claiming done."
else
  # Not yet an SDD repo: a single, low-noise pointer (only when a docs/ dir exists, to avoid firing everywhere).
  if [ -d docs ]; then
    echo "› SDD plugin available — run /sdd-scaffold to set up the spec-driven docs/ structure (requirements, specs, ADRs, plans, traceability)."
  fi
fi

exit 0

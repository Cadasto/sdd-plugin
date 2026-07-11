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
  echo "› Spec-Driven Development repo detected — the specification is the source of truth (read docs/.sdd.yaml + AGENTS.md before editing). SDD skills: /sdd-specify (REQ/SPEC/ADR) · /sdd-trace (traceability/drift) · /sdd-review (spec-aware review) · /sdd-archive (close-out, in the implementing PR) · /sdd-scaffold. Planning/build/verify use the superpowers loop; land plans in docs/plans/. Run /sdd-trace + the build's spec-check before claiming done."
else
  # Not yet an SDD repo: a single, low-noise pointer (only when a docs/ dir exists, to avoid firing everywhere).
  if [ -d docs ]; then
    echo "› SDD plugin available — run /sdd-scaffold to set up the spec-driven docs/ structure (requirements, specs, ADRs, plans, traceability)."
  fi
fi

exit 0

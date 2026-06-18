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
  echo "› Spec-Driven Development repo detected — the specification is the source of truth (read docs/.sdd.yaml + AGENTS.md before editing). Skills: /sdd-requirement /sdd-spec /sdd-adr /sdd-plan /sdd-implement /sdd-verify /sdd-trace /sdd-archive (and /sdd-scaffold to extend the structure). Verify with the build gate — which includes spec-check — before claiming done."
else
  # Not yet an SDD repo: a single, low-noise pointer (only when a docs/ dir exists, to avoid firing everywhere).
  if [ -d docs ]; then
    echo "› SDD plugin available — run /sdd-scaffold to set up the spec-driven docs/ structure (requirements, specs, ADRs, plans, traceability)."
  fi
fi

exit 0

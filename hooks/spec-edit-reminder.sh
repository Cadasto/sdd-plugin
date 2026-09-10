#!/usr/bin/env bash
# PostToolUse / afterFileEdit hook (host-agnostic): when an SDD document or the traceability map /
# descriptor is edited, print a short reminder to keep the traceability chain in sync. Advisory and
# read-only — it never blocks an edit and ALWAYS exits 0.
#
# Cursor's `afterFileEdit` hook has no output channel, so the reminder cannot reach the agent there;
# the registration is kept because it is harmless.
#
# File-path resolution, in order:
#   1. $CLAUDE_FILE_PATH          — set by Claude Code for Write/Edit hooks (fast path).
#   2. tool payload JSON on stdin — Claude (`tool_input.file_path`) or Cursor `afterFileEdit`
#      (`file_path`). Extracted without a jq/python dependency.
#
# Document-kind directories and the traceability file come from `paths.*` / `traceability` in
# docs/.sdd.yaml when the repository has customised them, falling back to the scaffold's own defaults
# (docs/requirements, docs/specifications, docs/adr, docs/plans, docs/specifications/traceability.yaml)
# when the descriptor is missing, unparseable, or silent on a given key. A hard-coded path here would
# mean the reminder silently never fires in a repository that customised its paths — the worst failure
# shape, since nobody notices a reminder that never comes.
set -u

f="${CLAUDE_FILE_PATH:-}"

# Fall back to the JSON the host pipes in on stdin. Guard on a non-tty stdin so a manual run without
# a pipe doesn't block on `cat`.
if [ -z "$f" ] && [ ! -t 0 ]; then
  payload="$(cat)"
  f="$(printf '%s' "$payload" \
        | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' \
        | head -n1 \
        | sed -E 's/.*"([^"]+)"$/\1/')"
fi

[ -n "$f" ] || exit 0   # nothing to inspect

# Read one scalar key nested directly under a named block in docs/.sdd.yaml, without a YAML parser.
# `desc_get paths plans` returns the value of `plans:` inside the `paths:` block; `desc_get sdd
# traceability` returns the top-level `traceability:` scalar directly under `sdd:`. Mirrors the
# identically-named helper in hooks/session-start.sh.
desc_get() {
  [ -f docs/.sdd.yaml ] || return 0
  awk -v blk="$1" -v key="$2" '
    !inb && $0 ~ ("^[[:space:]]*" blk ":[[:space:]]*(#.*)?$") { inb = match($0, /[^[:space:]]/); next }
    inb {
      ind = match($0, /[^[:space:]]/)
      if (ind == 0) next                       # blank line: still inside the block
      if (ind <= inb) { inb = 0; next }        # dedented: the block ended
      line = $0
      sub(/^[[:space:]]+/, "", line)
      if (index(line, key ":") == 1) {
        v = substr(line, length(key) + 2)      # everything after "key:"
        sub(/^[[:space:]]+/, "", v)            # leading space
        sub(/[[:space:]]+#.*$/, "", v)         # a trailing " # comment"
        sub(/[[:space:]]+$/, "", v)            # trailing space
        q = sprintf("%c", 39)                  # a single quote, without writing one here
        gsub("^\"|\"$", "", v)               # surrounding double quotes
        gsub("^" q "|" q "$", "", v)           # or single quotes
        sub(/\/+$/, "", v)                    # a trailing slash
        print v
        exit
      }
    }
  ' docs/.sdd.yaml 2>/dev/null
}

req_dir="$(desc_get paths requirements)"
[ -n "$req_dir" ] || req_dir="docs/requirements"
spec_dir="$(desc_get paths specifications)"
[ -n "$spec_dir" ] || spec_dir="docs/specifications"
adr_dir="$(desc_get paths adr)"
[ -n "$adr_dir" ] || adr_dir="docs/adr"
plans_dir="$(desc_get paths plans)"
[ -n "$plans_dir" ] || plans_dir="docs/plans"
trace_file="$(desc_get sdd traceability)"
[ -n "$trace_file" ] || trace_file="docs/specifications/traceability.yaml"

case "$f" in
  *"$trace_file"|*docs/.sdd.yaml)
    echo "› Edited the SDD descriptor / traceability map — run /sdd-trace to confirm the map still matches the tree (the spec-check gate), then \`sdd-check generate\` (or \`/sdd-trace\`), so the index and the status lines follow the map." ;;
  *"$req_dir"/*|*"$req_dir")
    echo "› Edited a requirement — keep it to capability + acceptance + out-of-scope (no file paths or how-to); link to its single canonical spec section; update traceability.yaml, then \`sdd-check generate\` (or \`/sdd-trace\`), so the index and the status lines follow the map." ;;
  *"$spec_dir"/*|*"$spec_dir")
    echo "› Edited a spec — one canonical home (no duplicated normative prose), explicit RFC-2119 force (MUST/SHOULD/MAY), stable § anchors; update traceability.yaml. Then /sdd-trace." ;;
  *"$adr_dir"/*|*"$adr_dir")
    echo "› Edited an ADR — one decision per record; cite the STRAND it resolves and the REQs it amends; it must be Accepted before code depends on it." ;;
  *"$plans_dir"/*|*"$plans_dir")
    echo "› Edited a plan — it must cite the REQ/SPEC § it implements and add no new normative rules; close it with /sdd-archive in the same PR once the feature lands and /sdd-trace is clean." ;;
  *) : ;;
esac

exit 0

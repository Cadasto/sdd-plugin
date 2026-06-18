#!/usr/bin/env bash
# PostToolUse / afterFileEdit hook (host-agnostic): when an SDD document or the traceability map /
# descriptor is edited, print a short reminder to keep the traceability chain in sync. Advisory and
# read-only — it never blocks an edit and ALWAYS exits 0.
#
# File-path resolution, in order:
#   1. $CLAUDE_FILE_PATH          — set by Claude Code for Write/Edit hooks (fast path).
#   2. tool payload JSON on stdin — Claude (`tool_input.file_path`) or Cursor `afterFileEdit`
#      (`file_path`). Extracted without a jq/python dependency.
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

case "$f" in
  *docs/specifications/traceability.yaml|*docs/.sdd.yaml)
    echo "› Edited the SDD descriptor / traceability map — run /sdd-trace to confirm the map still matches the tree (the spec-check gate)." ;;
  *docs/requirements/*)
    echo "› Edited a requirement — keep it to capability + acceptance + out-of-scope (no file paths or how-to); link to its single canonical spec section; update traceability.yaml. Then /sdd-trace." ;;
  *docs/specifications/*)
    echo "› Edited a spec — one canonical home (no duplicated normative prose), explicit RFC-2119 force (MUST/SHOULD/MAY), stable § anchors; update traceability.yaml. Then /sdd-trace." ;;
  *docs/adr/*)
    echo "› Edited an ADR — one decision per record; cite the STRAND it resolves and the REQs it amends; it must be Accepted before code depends on it." ;;
  *docs/plans/*)
    echo "› Edited a plan — it must cite the REQ/SPEC § it implements and add no new normative rules; close it with /sdd-archive once the feature lands and /sdd-trace is clean." ;;
  *) : ;;
esac

exit 0

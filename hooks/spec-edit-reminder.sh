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
# (docs/requirements, docs/specifications, docs/adr, docs/specifications/traceability.yaml)
# when the descriptor is missing, unparseable, or silent on a given key. A hard-coded path here would
# mean the reminder silently never fires in a repository that customised its paths — the worst failure
# shape, since nobody notices a reminder that never comes. A Cursor payload's first "workspace_roots"
# entry, when it names a directory, is the working directory the descriptor is read from.
set -u

# Read one scalar key from docs/.sdd.yaml, without a YAML parser. `desc_get paths adr` returns the
# value of `adr:` nested directly under the `paths:` block — and not a same-named key under another
# block elsewhere in the file. An empty block name reads a top-level key: `desc_get "" traceability`
# finds `traceability:` in a descriptor written without the `sdd:` wrapper.
# Mirrors the identically-named helper in hooks/session-start.sh.
desc_get() {
  [ -f docs/.sdd.yaml ] || return 0
  awk -v blk="$1" -v key="$2" '
    function value(line,   v, q) {
      v = substr(line, length(key) + 2)        # everything after "key:"
      sub(/^[[:space:]]+/, "", v)              # leading space
      sub(/[[:space:]]+#.*$/, "", v)           # a trailing " # comment"
      sub(/[[:space:]]+$/, "", v)              # trailing space (and a CR)
      q = sprintf("%c", 39)                    # a single quote, without writing one here
      gsub("^\"|\"$", "", v)                 # surrounding double quotes
      gsub("^" q "|" q "$", "", v)             # or single quotes
      sub(/\/+$/, "", v)                      # a trailing slash
      print v
      exit
    }
    blk == "" { if (index($0, key ":") == 1) value($0); next }
    !inb && $0 ~ ("^[[:space:]]*" blk ":[[:space:]]*(#.*)?$") { inb = match($0, /[^[:space:]]/); next }
    inb {
      ind = match($0, /[^[:space:]]/)
      if (ind == 0) next                       # blank line: still inside the block
      if (ind <= inb) { inb = 0; next }        # dedented: the block ended
      line = $0
      sub(/^[[:space:]]+/, "", line)
      if (index(line, key ":") == 1) value(line)
    }
  ' docs/.sdd.yaml 2>/dev/null
}

# Cursor does not document the working directory of a plugin hook. When the payload names the
# workspace ("workspace_roots"), move into its first entry so docs/.sdd.yaml is read from the
# repository, not from wherever the host started the script. Parsed without jq; an absent entry, or
# one that is not a directory, leaves the working directory as it was.
workspace_root() {
  printf '%s' "$1" | tr -d '\r\n' \
    | grep -oE '"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"([^"\\]|\\.)*"' \
    | head -n1 | sed -E 's/^.*\[[[:space:]]*"//; s/"$//' | sed 's#\\/#/#g; s#\\\\#\\#g'
}

# The JSON the host pipes in on stdin. Guard on a non-tty stdin so a manual run without a pipe doesn't
# block on `cat`.
payload=""
[ -t 0 ] || payload="$(cat 2>/dev/null)"
ws="$(workspace_root "$payload")"
if [ -n "$ws" ] && [ -d "$ws" ]; then cd "$ws" 2>/dev/null || :; fi

f="${CLAUDE_FILE_PATH:-}"
if [ -z "$f" ]; then
  f="$(printf '%s' "$payload" \
        | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' \
        | head -n1 \
        | sed -E 's/.*"([^"]+)"$/\1/')"
fi

[ -n "$f" ] || exit 0   # nothing to inspect

# Not an SDD repository (the same test hooks/session-start.sh applies): the default document paths
# below would otherwise match any repository that happens to keep a docs/requirements/ directory.
[ -f docs/.sdd.yaml ] || [ -d docs/specifications ] || exit 0

# The informative profile binds only the constitution: an edit to it is the one worth a reminder, and
# every other document under docs/ is a knowledge-base page the change reconciles as it goes.
profile="$(desc_get sdd profile)"
[ -n "$profile" ] || profile="$(desc_get "" profile)"
if [ "$profile" = informative ]; then
  constitution="$(desc_get paths constitution)"
  [ -n "$constitution" ] || constitution="docs/architecture.md"
  case "$f" in
    *"$constitution") echo "› Edited the constitution — it binds every change; amend it through /sdd-specify, with the reason in the commit body or an ADR." ;;
  esac
  exit 0
fi

req_dir="$(desc_get paths requirements)"
[ -n "$req_dir" ] || req_dir="docs/requirements"
spec_dir="$(desc_get paths specifications)"
[ -n "$spec_dir" ] || spec_dir="docs/specifications"
adr_dir="$(desc_get paths adr)"
[ -n "$adr_dir" ] || adr_dir="docs/adr"
trace_file="$(desc_get sdd traceability)"
[ -n "$trace_file" ] || trace_file="$(desc_get "" traceability)"   # a descriptor with no sdd: wrapper
[ -n "$trace_file" ] || trace_file="docs/specifications/traceability.yaml"

# Regeneration is the vendored gate's `generate`, named with the path this repository vendored it at.
# /sdd-trace is report-only and never regenerates, so it is not offered for that step.
check_script="$(desc_get check script)"
[ -n "$check_script" ] || check_script="scripts/sdd-check.py"
if [ -f "$check_script" ]; then
  regen="run \`python3 $check_script generate --root .\`"
else
  regen="regenerate them with /sdd-specify (or /sdd-close)"
fi

# How many RFC-2119 keywords the edit added (methodology §4: a keyword only for what a caller relies on).
# Claude Code's payload carries the text written: `tool_input.content` for Write, `tool_input.new_string`
# for Edit and for Cursor's edits; the field the tool name picks, first match only, so a response that
# echoes the text counts once. Counted on the text alone, net of the keywords in an Edit's `old_string`,
# so a Write of a whole file counts every keyword it holds. Parsed without jq: JSON escapes keep keywords
# intact, and a miscount only changes a number in an advisory line. The words are split with a plain
# class, not `\b`, which not every grep knows.
kw_count() { grep -oE '[A-Za-z]+' | grep -cxE 'MUST|SHALL|REQUIRED|SHOULD|RECOMMENDED|MAY|OPTIONAL'; }
kw_added() {
  case "$(printf '%s' "$payload" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1)" in
    *Write*) _field=content ;;
    *) _field=new_string ;;
  esac
  _new="$(printf '%s' "$payload" | grep -oE "\"$_field\"[[:space:]]*:[[:space:]]*\"([^\"\\\\]|\\\\.)*\"" | head -n1)"
  _old="$(printf '%s' "$payload" | grep -oE '"old_string"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' | head -n1)"
  _n="$(printf '%s' "$_new" | kw_count | tr -d '[:space:]')"
  _o="$(printf '%s' "$_old" | kw_count | tr -d '[:space:]')"
  [ "${_n:-0}" -gt "${_o:-0}" ] && printf '%s' "$((_n - _o))"
}

case "$f" in
  *"$trace_file"|*docs/.sdd.yaml)
    echo "› Edited the SDD descriptor / traceability map — run /sdd-trace to confirm the map still matches the tree (the spec-check gate); for the indexes and status lines to follow the map, $regen." ;;
  *"$req_dir"/*|*"$req_dir")
    echo "› Edited a requirement — keep it to capability + acceptance + out-of-scope (no file paths or how-to); link to its single canonical spec section; update traceability.yaml; for the index and the status lines to follow the map, $regen." ;;
  *"$spec_dir"/*|*"$spec_dir")
    echo "› Edited a spec — one canonical home (no duplicated normative prose), stable § anchors; update traceability.yaml. Then /sdd-trace."
    added="$(kw_added)"
    if [ -n "$added" ]; then
      echo "› $added RFC-2119 keyword(s) added — a keyword only for what a caller can observe and a test can pin; a default is SHOULD with its reason; how the code does it is prose (methodology §4). Each MUST costs a test, a guard proof and an amendment when the code moves."
    fi ;;
  *"$adr_dir"/*|*"$adr_dir")
    echo "› Edited an ADR — one decision per record; cite the STRAND it resolves and the REQs it amends; it must be Accepted before code depends on it." ;;
  *) : ;;
esac

exit 0

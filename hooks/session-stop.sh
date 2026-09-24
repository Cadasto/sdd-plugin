#!/usr/bin/env bash
# Stop hook (Claude Code `Stop`, Cursor `stop`): a one-shot nudge to record progress.
# Fires ONCE per session when the session made no commit and leaves uncommitted changes in an
# SDD repository; the second stop passes. Claude Code: exit 2 + the reason on stderr. Cursor: a
# followup_message on stdout, exit 0. Opt out per repo: `hooks: { stop_nudge: false }` in docs/.sdd.yaml.
#
# Shared state with hooks/session-start.sh: STATE_DIR and the key below must resolve the same way in
# both scripts. The key folds in a session identifier when the host payload provides one (Claude Code's
# always does — "session_id"), so concurrent sessions in one repository don't share a HEAD baseline or
# spend each other's nudge; a host whose payload carries no such field falls back to the working
# directory alone (pre-existing behaviour, not a regression).
set -u

# Resolve the shared state directory without tripping `set -u` on an unset $HOME — see the matching
# comment in hooks/session-start.sh. A degrade to no state (and so no nudge) is correct; a crash is not.
state_dir() {
  if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    printf '%s' "$CLAUDE_PLUGIN_DATA"
  elif [ -n "${XDG_STATE_HOME:-}" ]; then
    printf '%s/sdd' "$XDG_STATE_HOME"
  elif [ -n "${HOME:-}" ]; then
    printf '%s/.local/state/sdd' "$HOME"
  else
    printf '%s/sdd-state-%s' "${TMPDIR:-/tmp}" "$(id -u 2>/dev/null || printf nouid)"
  fi
}
STATE_DIR="$(state_dir)"

# Cursor does not document the working directory of a plugin hook. When the payload names the
# workspace ("workspace_roots"), move into its first entry so docs/.sdd.yaml is read from the
# repository, not from wherever the host started the script. Parsed without jq; an absent entry, or
# one that is not a directory, leaves the working directory as it was.
workspace_root() {
  printf '%s' "$1" | tr -d '\r\n' \
    | grep -oE '"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"([^"\\]|\\.)*"' \
    | head -n1 | sed -E 's/^.*\[[[:space:]]*"//; s/"$//' | sed 's#\\/#/#g; s#\\\\#\\#g'
}

have() { command -v "$1" >/dev/null 2>&1; }

# The host's payload. Detect on a positive marker: a Cursor payload also carries
# "hook_event_name", so it is told apart by "workspace_roots" / "cursor_version". A
# manual run (no payload) stays plain and takes the followup-message path, not exit 2.
payload=""
[ -t 0 ] || payload="$(cat 2>/dev/null)"
host=plain
case "$payload" in
  *'"workspace_roots"'*|*'"cursor_version"'*) host=cursor ;;
  *'"hook_event_name"'*)                      host=claude ;;
esac
ws="$(workspace_root "$payload")"
if [ -n "$ws" ] && [ -d "$ws" ]; then cd "$ws" 2>/dev/null || :; fi

# Not an SDD repository: nothing to nudge about.
[ -f docs/.sdd.yaml ] || exit 0

# Per-repository opt-out: the value false, bare or quoted, with an optional trailing comment. A
# value that merely starts with "false" (falsey, false_start) is not an opt-out.
q="'"
grep -qE "^[[:space:]]*stop_nudge:[[:space:]]*(false|\"false\"|${q}false${q})[[:space:]]*(#.*)?\$" docs/.sdd.yaml \
  && exit 0

# Claude Code's payload carries "session_id" on every hook; folded into the key so it matches the one
# hooks/session-start.sh wrote for this session. Empty on a host whose payload carries no such field.
sid="$(printf '%s' "$payload" \
       | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' \
       | head -n1 | sed -E 's/.*"([^"]*)"$/\1/')"
key_src="$PWD"
[ -n "$sid" ] && key_src="$PWD:$sid"
key="$(printf '%s' "$key_src" | cksum 2>/dev/null | cut -d' ' -f1)"
[ -n "$key" ] || exit 0

# Already nudged in this session: the second stop passes.
[ -f "$STATE_DIR/$key.nudged" ] && exit 0

# Defensive: the host says it is re-running the stop hook after a nudge. Anchored to the key and to
# the JSON value true exactly, so a branch or PR named "...true..." elsewhere in the payload, a string
# "true", or a longer token cannot trip it.
if printf '%s' "$payload" | grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true([[:space:],}]|$)'; then
  exit 0
fi

have git || exit 0
# Time-limit git when `timeout` is installed; run it plainly when it is not. A slow tree
# (a network mount, a huge worktree) must not let the stop hook run past the host's budget.
tmo() {
  _limit="$1"; shift
  if have timeout; then timeout "$_limit" "$@"; else "$@"; fi
}
tmo 5 git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

start="$(cat "$STATE_DIR/$key.head" 2>/dev/null)"
head="$(tmo 5 git rev-parse HEAD 2>/dev/null)"
dirty="$(tmo 5 git status --porcelain 2>/dev/null | wc -l | tr -d '[:space:]')"

# No recorded starting point, or HEAD moved: a commit was made (or the session start was never seen).
[ -n "$start" ] || exit 0
[ "$head" = "$start" ] || exit 0

# Nothing uncommitted: there is nothing to record.
[ "$dirty" -eq 0 ] && exit 0

# One-shot: emit the nudge only once we have recorded that we did. If the marker cannot be
# written, degrade to silence rather than nudging on every stop.
: > "$STATE_DIR/$key.nudged" 2>/dev/null || exit 0

msg="This session made no commit and leaves $dirty uncommitted change(s). Record progress before stopping: commit the work, or update the plan's Notes or the PR ledger, or say why not. This nudge fires once; stopping again passes."

if [ "$host" = claude ]; then
  echo "$msg" >&2
  exit 2
fi

printf '{"followup_message": "%s"}\n' "$msg"
exit 0

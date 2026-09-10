#!/usr/bin/env bash
# Stop hook (Claude Code `Stop`, Cursor `stop`): a one-shot nudge to record progress.
# Fires ONCE per session when the session made no commit and leaves uncommitted changes in an
# SDD repository; the second stop passes. Claude Code: exit 2 + the reason on stderr. Cursor: a
# followup_message on stdout, exit 0. Opt out per repo: `hooks: { stop_nudge: false }` in docs/.sdd.yaml.
set -u

STATE_DIR="${CLAUDE_PLUGIN_DATA:-${XDG_STATE_HOME:-$HOME/.local/state}/sdd}"

have() { command -v "$1" >/dev/null 2>&1; }

# Not an SDD repository: nothing to nudge about.
[ -f docs/.sdd.yaml ] || exit 0

# Per-repository opt-out.
grep -qE '^\s*stop_nudge:\s*false' docs/.sdd.yaml && exit 0

# The host's payload. Claude Code carries "hook_event_name"; Cursor does not.
payload=""
[ -t 0 ] || payload="$(cat 2>/dev/null)"
host=cursor
case "$payload" in
  *'"hook_event_name"'*) host=claude ;;
esac

key="$(printf '%s' "$PWD" | cksum 2>/dev/null | cut -d' ' -f1)"
[ -n "$key" ] || exit 0

# Already nudged in this session: the second stop passes.
[ -f "$STATE_DIR/$key.nudged" ] && exit 0

# Defensive: the host says it is re-running the stop hook after a nudge.
case "$payload" in
  *'"stop_hook_active"'*[Tt]rue*) exit 0 ;;
esac

have git || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

start="$(cat "$STATE_DIR/$key.head" 2>/dev/null)"
head="$(git rev-parse HEAD 2>/dev/null)"
dirty="$(git status --porcelain 2>/dev/null | wc -l | tr -d '[:space:]')"

# No recorded starting point, or HEAD moved: a commit was made (or the session start was never seen).
[ -n "$start" ] || exit 0
[ "$head" = "$start" ] || exit 0

# Nothing uncommitted: there is nothing to record.
[ "$dirty" -eq 0 ] && exit 0

: > "$STATE_DIR/$key.nudged" 2>/dev/null

msg="This session made no commit and leaves $dirty uncommitted change(s). Record progress before stopping: commit the work, or update the plan's Notes or the PR ledger, or say why not. This nudge fires once; stopping again passes."

if [ "$host" = claude ]; then
  echo "$msg" >&2
  exit 2
fi

printf '{"followup_message": "%s"}\n' "$msg"
exit 0

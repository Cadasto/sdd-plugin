#!/usr/bin/env bash
# Behavioural tests for the three hook scripts. They have no unit-test harness (they are shell,
# reached only through the host), yet they carry the load-bearing host-detection, one-shot and
# HOME-unset logic — the exact places three release-blocking defects hid. Run from anywhere; exits
# non-zero when any case fails. Needs only bash, git and the POSIX tools (awk, grep, sed); Python is
# used only when present, to parse a JSON reply more strictly. Portable to macOS: no GNU-only flags,
# and no errexit — every case records its own result and the run always reaches the summary.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$ROOT/hooks"
fails=0

# Everything this run creates lives under one directory, removed on exit (write bits restored first,
# since one case makes a state directory read-only). The state directory handed to the hooks is
# always under it too, so a run never touches the caller's real plugin state.
TMPBASE="$(mktemp -d "${TMPDIR:-/tmp}/sdd-hooks-test.XXXXXX")" || { echo "hooks-test: cannot create a temp dir"; exit 1; }
trap 'chmod -R u+w "$TMPBASE" 2>/dev/null; rm -rf "$TMPBASE"' EXIT
unset CLAUDE_PLUGIN_DATA CLAUDE_FILE_PATH

ok() { printf '  ok   %s\n' "$1"; }
bad() { printf '  FAIL %s\n' "$1"; fails=$((fails + 1)); }
skip() { printf '  skip %s\n' "$1"; }

newdir() { mktemp -d "$TMPBASE/$1.XXXXXX"; }

# Run one hook with a clean, per-case environment: the plugin-data and file-path variables the host
# would set are always removed, and the state directory is the one the case names.
#   hook <script> <state-dir> [VAR=value ...]   (stdin is the payload)
hook() {
  _script="$1"; _state="$2"; shift 2
  env -u CLAUDE_PLUGIN_DATA -u CLAUDE_FILE_PATH XDG_STATE_HOME="$_state" "$@" bash "$HOOKS/$_script.sh"
}

# The descriptor every SDD case uses: customised and awkward (single-quoted path, trailing slash, a
# custom traceability file, a non-default plans dir) so desc_get is exercised. $1 is the stop_nudge
# line's value, written verbatim.
write_desc() {
  cat > "$1/docs/.sdd.yaml" <<YAML
sdd:
  paths:
    requirements: 'docs/reqs'
    specifications: docs/specifications
    adr: docs/adr
    plans: docs/my-plans/
  traceability: docs/map.yaml
  check:
    script: scripts/sdd-check.py
  hooks:
    stop_nudge: $2
YAML
}

setup_repo() {
  _r="$(newdir repo)"
  mkdir -p "$_r/docs/reqs" "$_r/docs/specifications" "$_r/docs/adr" "$_r/docs/my-plans"
  write_desc "$_r" "${1:-true}"
  : > "$_r/docs/map.yaml"
  printf '%s' "$_r"
}

gitc() { git -c user.email=t@t -c user.name=t -c commit.gpgsign=false "$@"; }

# Make $1 a git repository with one commit. Reports (and returns 1) when it could not, so a broken
# fixture fails the case instead of quietly weakening it.
commit_all() {
  if ( cd "$1" && git init -q . && gitc add -A && gitc commit -q -m base ) >/dev/null 2>&1 \
     && git -C "$1" rev-parse -q --verify HEAD >/dev/null 2>&1; then
    return 0
  fi
  bad "fixture: could not create a committed git repository in $1"
  return 1
}

claude_start='{"hook_event_name":"SessionStart","session_id":"s1","source":"startup"}'
claude_stop='{"hook_event_name":"Stop","session_id":"s1","stop_hook_active":false}'
cursor_payload() { printf '{"hook_event_name":"%s","workspace_roots":["%s"],"cursor_version":"1.0"}' "$1" "$2"; }

# --- session-start: host detection -------------------------------------------------
r="$(setup_repo)"; state="$(newdir state)"
cursor_out="$(cd "$r" && cursor_payload sessionStart "$r" | hook session-start "$state")"
case "$cursor_out" in
  '{"additional_context":'*) ok "session-start emits a JSON object for a Cursor payload" ;;
  *) bad "session-start Cursor payload did not yield an additional_context object: $cursor_out" ;;
esac
claude_out="$(cd "$r" && printf '%s' "$claude_start" | hook session-start "$state")"
case "$claude_out" in
  '{'*) bad "session-start emitted JSON for a Claude payload (should be plain text)" ;;
  *"Spec-Driven Development repo detected"*) ok "session-start emits plain text for a Claude payload" ;;
  *) bad "session-start Claude payload produced no orientation line" ;;
esac

# --- session-start: the plan template is not counted as an active plan --------------
r="$(setup_repo)"; state="$(newdir state)"
printf -- '---\nstatus: active\n---\n' > "$r/docs/my-plans/_template.md"
printf -- '---\nplan: 2026-01-01-real\nstatus: active\nimplements: [REQ-1]\n---\n' > "$r/docs/my-plans/2026-01-01-real.md"
plans_line="$(cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" | grep 'active plans')"
case "$plans_line" in
  *"active plans: 1"*) ok "session-start counts one active plan, not the _template stub" ;;
  *) bad "session-start active-plan count wrong: $plans_line" ;;
esac

# --- session-start: a vendored gate with no verdict is reported, not silenced ---------
r="$(setup_repo)"; state="$(newdir state)"
mkdir -p "$r/scripts"
printf 'import sys\nsys.exit(3)\n' > "$r/scripts/sdd-check.py"
gate_line="$(cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" | grep 'drift gate')"
if command -v python3 >/dev/null 2>&1; then
  expect="› drift gate: no verdict (exit 3)"
else
  expect="› drift gate: no verdict (python3 not found)"
fi
[ "$gate_line" = "$expect" ] && ok "session-start reports a vendored gate that gave no verdict" \
  || bad "drift-gate line was '$gate_line', expected '$expect'"

# --- session-stop: Claude one-shot nudge ----------------------------------------------
r="$(setup_repo)"; state="$(newdir state)"
if commit_all "$r"; then
  ( cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" >/dev/null )
  echo dirty > "$r/uncommitted.txt"
  ( cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" >/dev/null 2>&1 ); first=$?
  ( cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" >/dev/null 2>&1 ); second=$?
  [ "$first" -eq 2 ] && ok "session-stop nudges once (exit 2)" || bad "first stop exit was $first, expected 2"
  [ "$second" -eq 0 ] && ok "session-stop passes on the second stop (exit 0)" || bad "second stop exit was $second, expected 0"
fi

# --- session-stop: the host re-running the hook (stop_hook_active: true) passes -------
r="$(setup_repo)"; state="$(newdir state)"
if commit_all "$r"; then
  ( cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" >/dev/null )
  echo dirty > "$r/uncommitted.txt"
  ( cd "$r" && printf '{"hook_event_name":"Stop","session_id":"s1","stop_hook_active": true}' \
      | hook session-stop "$state" >/dev/null 2>&1 ); rc=$?
  [ "$rc" -eq 0 ] && ok "session-stop passes when stop_hook_active is true" \
    || bad "stop with stop_hook_active true exited $rc, expected 0"
fi

# --- session-stop: opt-out, bare and quoted; a look-alike value is not an opt-out -----
for v in 'false' '"false"' "'false'" 'false   # off' 'falsey'; do
  r="$(setup_repo "$v")"; state="$(newdir state)"
  commit_all "$r" || continue
  ( cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" >/dev/null )
  echo dirty > "$r/uncommitted.txt"
  ( cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" >/dev/null 2>&1 ); rc=$?
  if [ "$v" = falsey ]; then want=2; else want=0; fi
  [ "$rc" -eq "$want" ] && ok "session-stop with stop_nudge: $v exits $want" \
    || bad "stop_nudge: $v exit was $rc, expected $want"
done

# --- session-stop: Cursor payload -> exit 0 and a followup_message JSON object --------
r="$(setup_repo)"; state="$(newdir state)"
if commit_all "$r"; then
  ( cd "$r" && cursor_payload sessionStart "$r" | hook session-start "$state" >/dev/null )
  echo dirty > "$r/uncommitted.txt"
  c_out="$(cd "$r" && cursor_payload stop "$r" | hook session-stop "$state" 2>/dev/null)"; c_rc=$?
  c_out2="$(cd "$r" && cursor_payload stop "$r" | hook session-stop "$state" 2>/dev/null)"; c_rc2=$?
  valid=no
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$c_out" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if isinstance(d, dict) and set(d) == {"followup_message"} and d["followup_message"] else 1)' 2>/dev/null && valid=yes
  else
    case "$c_out" in '{"followup_message": "'*'"}') valid=yes ;; esac
  fi
  [ "$c_rc" -eq 0 ] && [ "$valid" = yes ] && ok "session-stop on Cursor exits 0 with a followup_message JSON object" \
    || bad "Cursor stop exit $c_rc, reply not a followup_message object: $c_out"
  [ "$c_rc2" -eq 0 ] && [ -z "$c_out2" ] && ok "session-stop on Cursor is silent on the second stop" \
    || bad "second Cursor stop exit $c_rc2, output '$c_out2' (expected 0 and nothing)"
fi

# --- workspace_roots: the hooks work from a working directory outside the workspace ---
r="$(setup_repo)"; state="$(newdir state)"; elsewhere="$(newdir elsewhere)"
if commit_all "$r"; then
  ws_start="$(cd "$elsewhere" && cursor_payload sessionStart "$r" | hook session-start "$state")"
  case "$ws_start" in
    *"Spec-Driven Development repo detected"*) ok "session-start reads the workspace named by workspace_roots" ;;
    *) bad "session-start from outside the workspace missed the SDD repo: $ws_start" ;;
  esac
  echo dirty > "$r/uncommitted.txt"
  ws_stop="$(cd "$elsewhere" && cursor_payload stop "$r" | hook session-stop "$state" 2>/dev/null)"
  case "$ws_stop" in
    *'"followup_message"'*) ok "session-stop reads the workspace named by workspace_roots" ;;
    *) bad "session-stop from outside the workspace did not nudge: '$ws_stop'" ;;
  esac
  ws_rem="$(cd "$elsewhere" && printf '{"hook_event_name":"afterFileEdit","file_path":"%s","workspace_roots":["%s"],"cursor_version":"1.0"}' \
      "$r/docs/reqs/REQ-1.md" "$r" | hook spec-edit-reminder "$state")"
  case "$ws_rem" in
    *"Edited a requirement"*) ok "spec-edit-reminder reads the workspace named by workspace_roots" ;;
    *) bad "spec-edit-reminder from outside the workspace missed the custom requirements path" ;;
  esac
fi

# --- HOME, XDG_STATE_HOME and CLAUDE_PLUGIN_DATA all unset -----------------------------
# The state falls back to a per-user temp directory; TMPDIR points it inside this run's temp dir.
# The session start must record HEAD there, so the first stop nudges and the second passes — and
# nothing (gh's device-id, a state file) may land in the repository.
r="$(setup_repo)"; htmp="$(newdir htmp)"
if commit_all "$r"; then
  homeless() { env -u HOME -u XDG_STATE_HOME -u CLAUDE_PLUGIN_DATA -u CLAUDE_FILE_PATH TMPDIR="$htmp" bash "$HOOKS/$1.sh"; }
  ( cd "$r" && printf '%s' "$claude_start" | homeless session-start >/dev/null 2>&1 ); h0=$?
  echo dirty > "$r/uncommitted.txt"
  ( cd "$r" && printf '%s' "$claude_stop" | homeless session-stop >/dev/null 2>&1 ); h1=$?
  ( cd "$r" && printf '%s' "$claude_stop" | homeless session-stop >/dev/null 2>&1 ); h2=$?
  tree="$(git -C "$r" status --porcelain --untracked-files=all)"
  [ "$h0" -eq 0 ] && [ "$h1" -eq 2 ] && [ "$h2" -eq 0 ] \
    && ok "with HOME unset: session-start exits 0, the first stop nudges, the second passes" \
    || bad "with HOME unset: start $h0, stops $h1 then $h2 (expected 0, 2, 0)"
  [ "$tree" = "?? uncommitted.txt" ] && ok "with HOME unset: the hooks write nothing into the repository" \
    || bad "with HOME unset the tree is not clean except the dirty file: $tree"
fi

# --- an unwritable state directory degrades to silence, never to a nudge on every stop --
if [ "$(id -u)" -eq 0 ]; then
  skip "unwritable state directory (running as root, which can write anyway)"
else
  r="$(setup_repo)"; state="$(newdir state)"
  if commit_all "$r"; then
    ( cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" >/dev/null )
    # The hooks keep their state in $XDG_STATE_HOME/sdd; lock that directory, which now holds HEAD.
    ls "$state/sdd/"*.head >/dev/null 2>&1 || bad "fixture: session-start recorded no HEAD under $state/sdd"
    chmod a-w "$state/sdd"
    echo dirty > "$r/uncommitted.txt"
    ( cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" >/dev/null 2>&1 ); u1=$?
    ( cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" >/dev/null 2>&1 ); u2=$?
    chmod u+w "$state/sdd"
    [ "$u1" -eq 0 ] && [ "$u2" -eq 0 ] && ok "with an unwritable state directory both stops exit 0 (no nudge it cannot record)" \
      || bad "with an unwritable state directory the stops exited $u1 then $u2, expected 0 and 0"
  fi
fi

# --- a git repository that is not an SDD repository: every hook is silent -------------
r="$(newdir plain)"; state="$(newdir state)"
mkdir -p "$r/src/requirements" && echo x > "$r/src/requirements/a.md"
if commit_all "$r"; then
  echo dirty > "$r/uncommitted.txt"
  n_start="$(cd "$r" && printf '%s' "$claude_start" | hook session-start "$state" 2>&1)"; n0=$?
  n_rem="$(cd "$r" && hook spec-edit-reminder "$state" CLAUDE_FILE_PATH="$r/docs/requirements/REQ-1.md" </dev/null 2>&1)"; n1=$?
  n_stop="$(cd "$r" && printf '%s' "$claude_stop" | hook session-stop "$state" 2>&1)"; n2=$?
  [ "$n0$n1$n2" = 000 ] && [ -z "$n_start$n_rem$n_stop" ] && ok "in a non-SDD git repository all three hooks are silent and exit 0" \
    || bad "non-SDD repo: exits $n0/$n1/$n2, output start='$n_start' reminder='$n_rem' stop='$n_stop'"
fi

# --- spec-edit-reminder: customised paths (desc_get quotes / trailing slash) --------
r="$(setup_repo)"; state="$(newdir state)"
rem() { ( cd "$r" && hook spec-edit-reminder "$state" CLAUDE_FILE_PATH="$1" </dev/null ); }
case "$(rem "$r/docs/reqs/REQ-1.md")" in
  *"Edited a requirement"*) ok "reminder fires for a single-quoted requirements path" ;;
  *) bad "reminder missed the single-quoted requirements path" ;;
esac
case "$(rem "$r/docs/my-plans/2026-01-01-x.md")" in
  *"Edited a plan"*) ok "reminder fires for a trailing-slash plans path" ;;
  *) bad "reminder missed the trailing-slash plans path" ;;
esac
case "$(rem "$r/docs/map.yaml")" in
  *"Edited the SDD descriptor"*) ok "reminder fires for a custom traceability file" ;;
  *) bad "reminder missed the custom traceability file" ;;
esac

# Regeneration is named as the vendored gate's command with the resolved path, never /sdd-trace
# (report-only) and never a bare `sdd-check generate`.
mkdir -p "$r/scripts" && : > "$r/scripts/sdd-check.py"
regen="$(rem "$r/docs/map.yaml")"
case "$regen" in
  *'`python3 scripts/sdd-check.py generate --root .`'*)
    case "$regen" in
      *'`sdd-check generate`'*|*'(or `/sdd-trace`)'*) bad "reminder still offers a bare sdd-check or /sdd-trace for regeneration: $regen" ;;
      *) ok "reminder names the vendored gate's generate command for regeneration" ;;
    esac ;;
  *) bad "reminder does not name python3 scripts/sdd-check.py generate --root .: $regen" ;;
esac

# A lightweight-profile file-form requirements path (a file, not a directory) must fire too.
lite="$(newdir lite)"; mkdir -p "$lite/docs"
printf 'sdd:\n  paths:\n    requirements: docs/REQUIREMENTS.md\n  traceability: docs/map.yaml\n' > "$lite/docs/.sdd.yaml"
: > "$lite/docs/map.yaml"
case "$( cd "$lite" && hook spec-edit-reminder "$state" CLAUDE_FILE_PATH="$lite/docs/REQUIREMENTS.md" </dev/null )" in
  *"Edited a requirement"*) ok "reminder fires for a lightweight file-form requirements path" ;;
  *) bad "reminder missed the lightweight file-form requirements path" ;;
esac

# A descriptor written without the sdd: wrapper still names its traceability file.
bare="$(newdir bare)"; mkdir -p "$bare/docs"
printf 'paths:\n  requirements: docs/reqs\ntraceability: docs/trace-map.yaml\n' > "$bare/docs/.sdd.yaml"
: > "$bare/docs/trace-map.yaml"
case "$( cd "$bare" && hook spec-edit-reminder "$state" CLAUDE_FILE_PATH="$bare/docs/trace-map.yaml" </dev/null )" in
  *"Edited the SDD descriptor"*) ok "reminder finds traceability: in a descriptor without the sdd: wrapper" ;;
  *) bad "reminder missed the traceability file of an unwrapped descriptor" ;;
esac

if [ "$fails" -eq 0 ]; then
  echo "hooks-test: OK"
  exit 0
fi
echo "hooks-test: FAILED — $fails check(s)"
exit 1

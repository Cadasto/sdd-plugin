#!/usr/bin/env bash
# Behavioural tests for the three hook scripts. They have no unit-test harness (they are shell,
# reached only through the host), yet they carry the load-bearing host-detection, one-shot and
# HOME-unset logic — the exact places three release-blocking defects hid. Run from the repo root;
# exits non-zero on the first failure. No dependency beyond git, awk and grep.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$ROOT/hooks"
fails=0

ok() { printf '  ok   %s\n' "$1"; }
bad() { printf '  FAIL %s\n' "$1"; fails=$((fails + 1)); }

# A throwaway SDD repo with a customised, awkward descriptor (single-quoted path, trailing slash,
# a custom traceability file, a non-default plans dir) so the reminder's desc_get is exercised.
setup_repo() {
  repo="$(mktemp -d)"
  mkdir -p "$repo/docs/reqs" "$repo/docs/specifications" "$repo/docs/adr" "$repo/docs/my-plans"
  cat > "$repo/docs/.sdd.yaml" <<'YAML'
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
    stop_nudge: true
YAML
  : > "$repo/docs/map.yaml"
  printf '%s' "$repo"
}

# --- session-start: host detection -------------------------------------------------
r="$(setup_repo)"; state="$(mktemp -d)"
cursor_out="$(cd "$r" && printf '{"hook_event_name":"sessionStart","workspace_roots":["%s"],"cursor_version":"1.0"}' "$r" \
  | XDG_STATE_HOME="$state" bash "$HOOKS/session-start.sh")"
case "$cursor_out" in
  '{"additional_context":'*) ok "session-start emits a JSON object for a Cursor payload" ;;
  *) bad "session-start Cursor payload did not yield an additional_context object: $cursor_out" ;;
esac
claude_out="$(cd "$r" && printf '{"hook_event_name":"SessionStart","session_id":"s1","source":"startup"}' \
  | XDG_STATE_HOME="$state" bash "$HOOKS/session-start.sh")"
case "$claude_out" in
  '{'*) bad "session-start emitted JSON for a Claude payload (should be plain text)" ;;
  *"Spec-Driven Development repo detected"*) ok "session-start emits plain text for a Claude payload" ;;
  *) bad "session-start Claude payload produced no orientation line" ;;
esac

# --- session-start: the plan template is not counted as an active plan --------------
r="$(setup_repo)"; state="$(mktemp -d)"
printf -- '---\nstatus: active\n---\n' > "$r/docs/my-plans/_template.md"
printf -- '---\nplan: 2026-01-01-real\nstatus: active\nimplements: [REQ-1]\n---\n' > "$r/docs/my-plans/2026-01-01-real.md"
plans_line="$(cd "$r" && printf '{"hook_event_name":"SessionStart","session_id":"s1"}' \
  | XDG_STATE_HOME="$state" bash "$HOOKS/session-start.sh" | grep 'active plans' || true)"
case "$plans_line" in
  *"active plans: 1"*) ok "session-start counts one active plan, not the _template stub" ;;
  *) bad "session-start active-plan count wrong: $plans_line" ;;
esac

# --- session-stop: one-shot nudge, opt-out, HOME unset ------------------------------
r="$(setup_repo)"; state="$(mktemp -d)"
( cd "$r" && git init -q . && git -c user.email=t@t -c user.name=t add -A \
    && git -c user.email=t@t -c user.name=t commit -q -m base ) >/dev/null 2>&1
payload='{"hook_event_name":"Stop","session_id":"s1"}'
# Record HEAD as the session start would, then leave the tree dirty.
( cd "$r" && printf '%s' "$payload" | XDG_STATE_HOME="$state" bash "$HOOKS/session-start.sh" >/dev/null )
echo dirty > "$r/uncommitted.txt"
set +e
( cd "$r" && printf '%s' "$payload" | XDG_STATE_HOME="$state" bash "$HOOKS/session-stop.sh" >/dev/null 2>&1 )
first=$?
( cd "$r" && printf '%s' "$payload" | XDG_STATE_HOME="$state" bash "$HOOKS/session-stop.sh" >/dev/null 2>&1 )
second=$?
set -e 2>/dev/null || true
[ "$first" -eq 2 ] && ok "session-stop nudges once (exit 2)" || bad "first stop exit was $first, expected 2"
[ "$second" -eq 0 ] && ok "session-stop passes on the second stop (exit 0)" || bad "second stop exit was $second, expected 0"

# opt-out
r="$(setup_repo)"; state="$(mktemp -d)"
sed -i 's/stop_nudge: true/stop_nudge: false/' "$r/docs/.sdd.yaml"
( cd "$r" && git init -q . && git -c user.email=t@t -c user.name=t add -A \
    && git -c user.email=t@t -c user.name=t commit -q -m base ) >/dev/null 2>&1
( cd "$r" && printf '%s' "$payload" | XDG_STATE_HOME="$state" bash "$HOOKS/session-start.sh" >/dev/null )
echo dirty > "$r/uncommitted.txt"
optout=0
( cd "$r" && printf '%s' "$payload" | XDG_STATE_HOME="$state" bash "$HOOKS/session-stop.sh" >/dev/null 2>&1 ) || optout=$?
[ "$optout" -eq 0 ] && ok "session-stop honours stop_nudge: false" || bad "opt-out exit was $optout, expected 0"

# HOME and XDG_STATE_HOME both unset must not crash and must not nudge into the repo
r="$(setup_repo)"
homeless=0
( cd "$r" && env -u HOME -u XDG_STATE_HOME printf '%s' "$payload" \
  | ( cd "$r" && env -u HOME -u XDG_STATE_HOME bash "$HOOKS/session-stop.sh" ) >/dev/null 2>&1 ) || homeless=$?
[ "$homeless" -eq 0 ] && ok "session-stop exits 0 with HOME and XDG_STATE_HOME unset" || bad "homeless stop exit was $homeless"

# --- spec-edit-reminder: customised paths (desc_get quotes / trailing slash) --------
r="$(setup_repo)"
rem() { ( cd "$r" && CLAUDE_FILE_PATH="$1" bash "$HOOKS/spec-edit-reminder.sh" </dev/null ); }
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

# A lightweight-profile file-form requirements path (a file, not a directory) must fire too.
lite="$(mktemp -d)"; mkdir -p "$lite/docs"
printf 'sdd:\n  paths:\n    requirements: docs/REQUIREMENTS.md\n  traceability: docs/map.yaml\n' > "$lite/docs/.sdd.yaml"
: > "$lite/docs/map.yaml"
case "$( cd "$lite" && CLAUDE_FILE_PATH="$lite/docs/REQUIREMENTS.md" bash "$HOOKS/spec-edit-reminder.sh" </dev/null )" in
  *"Edited a requirement"*) ok "reminder fires for a lightweight file-form requirements path" ;;
  *) bad "reminder missed the lightweight file-form requirements path" ;;
esac

if [ "$fails" -eq 0 ]; then
  echo "hooks-test: OK"
  exit 0
fi
echo "hooks-test: FAILED — $fails check(s)"
exit 1

#!/usr/bin/env bash
# SessionStart hook (host-agnostic): when a Spec-Driven Development repository is detected, print one
# context line plus the available /sdd-* surface, then a short orientation — branch and tree state,
# active plans, open pull requests, and the drift-gate verdict. Every external command is optional and
# guarded; each is time-limited when the `timeout` binary is on PATH, and still runs — untimed, not
# skipped — when it isn't (see tmo() below). The script ALWAYS exits 0, so a missing or slow tool
# prints nothing rather than blocking the session.
#
# Host-aware output. Claude Code sends a payload carrying "hook_event_name" and adds plain stdout to
# the context. Cursor sends a payload without it and injects only a JSON object on stdout —
# {"additional_context": "<text>"} — ignoring plain text. A manual run (stdin is a terminal, or the
# payload is empty) prints plain text.
#
# Shared state with hooks/session-stop.sh: STATE_DIR below, keyed on the working directory. This hook
# records HEAD as it found it and clears any nudge left by an earlier session.
set -u

STATE_DIR="${CLAUDE_PLUGIN_DATA:-${XDG_STATE_HOME:-$HOME/.local/state}/sdd}"

nl='
'
out=""

have() { command -v "$1" >/dev/null 2>&1; }

# Time-limit a command when `timeout` is installed; run it plainly when it is not. Either way the
# caller keeps going, so no orientation line can hang the session.
tmo() {
  _limit="$1"; shift
  if have timeout; then timeout "$_limit" "$@"; else "$@"; fi
}

add() {
  [ -n "${1:-}" ] || return 0
  if [ -z "$out" ]; then out="$1"; else out="$out$nl$1"; fi
}

# Read one scalar key nested directly under a named block in docs/.sdd.yaml, without a YAML parser.
# `desc_get paths plans` returns the value of `plans:` inside the `paths:` block — and not the
# `plans:` that names a check family elsewhere in the file.
desc_get() {
  [ -f docs/.sdd.yaml ] || return 0
  awk -v blk="$1" -v key="$2" '
    !inb && $0 ~ ("^[[:space:]]*" blk ":[[:space:]]*(#.*)?$") { inb = match($0, /[^[:space:]]/); next }
    inb {
      ind = match($0, /[^[:space:]]/)
      if (ind == 0) next                       # blank line: still inside the block
      if (ind <= inb) { inb = 0; next }        # dedented: the block ended
      if ($1 == (key ":")) {
        v = $2
        gsub(/^"|"$/, "", v)
        print v
        exit
      }
    }
  ' docs/.sdd.yaml 2>/dev/null
}

is_sdd_repo() {
  [ -f docs/.sdd.yaml ] && return 0
  [ -d docs/specifications ] && return 0
  [ -f docs/specifications/traceability.yaml ] && return 0
  return 1
}

# ---------------------------------------------------------------- host detection
payload=""
[ -t 0 ] || payload="$(cat 2>/dev/null)"

host=plain
if [ -n "$payload" ]; then
  case "$payload" in
    *'"hook_event_name"'*) host=claude ;;
    *)                     host=cursor ;;
  esac
fi

# Claude Code sends `source` (startup | resume | clear | compact | fork). It is read here and
# deliberately not acted on: the full orientation prints for every source.
src="$(printf '%s' "$payload" \
       | grep -oE '"source"[[:space:]]*:[[:space:]]*"[^"]*"' \
       | head -n1 | sed -E 's/.*"([^"]*)"$/\1/')"
: "$src"

emit() {
  [ -n "$1" ] || return 0
  if [ "$host" = cursor ]; then
    # Escape backslashes and double quotes, drop raw control characters JSON forbids, then join the
    # lines with the two-character escape \n so the whole block is one JSON string.
    printf '{"additional_context": "%s"}\n' \
      "$(printf '%s' "$1" | tr -d '\r\t' | sed 's/\\/\\\\/g; s/"/\\"/g' \
         | awk 'NR>1 { printf "\\n" } { printf "%s", $0 }')"
  else
    printf '%s\n' "$1"
  fi
}

# ---------------------------------------------------------------- orientation
if is_sdd_repo; then
  add "› Spec-Driven Development repo detected — the specification is the source of truth (read docs/.sdd.yaml + AGENTS.md before editing). SDD skills: /sdd-specify (REQ/SPEC/ADR) · /sdd-deliver (plan → workers → draft PR) · /sdd-review (spec-aware review + panel prompts) · /sdd-triage (work a review round) · /sdd-trace (traceability/drift) · /sdd-archive (close out the plan in its PR) · /sdd-finalize (sweep finished plans at a version bump) · /sdd-scaffold. Plans live in docs/plans/, are flipped to done in place, and are swept at the next release. Run /sdd-trace + the build's spec-check before claiming done."

  # 1. Branch and working-tree state.
  if have git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    st="$(tmo 5 git status --porcelain=v1 -b 2>/dev/null)"
    if [ -n "$st" ]; then
      hdr="$(printf '%s\n' "$st" | head -n1)"
      body="$(printf '%s\n' "$st" | sed '1d')"
      if [ -n "$body" ]; then
        unt=$(printf '%s\n' "$body" | grep -c '^??')
        mod=$(printf '%s\n' "$body" | grep -vc '^??')
      else
        unt=0
        mod=0
      fi
      b="${hdr#\#\# }"
      case "$b" in
        "No commits yet on "*) b="${b#No commits yet on } (no commits yet)" ;;
      esac
      case "$b" in
        *...*) branch="${b%%...*}"; rest="${b#*...}" ;;
        *)     branch="$b";        rest="" ;;
      esac
      if [ -z "$rest" ]; then
        track="no upstream"
      else
        case "$rest" in
          *\[*\]) track="$(printf '%s' "$rest" | sed -n 's/.*\[\(.*\)\].*/\1/p')" ;;
          *)      track="in sync" ;;
        esac
      fi
      add "› branch $branch · $mod modified · $unt untracked · $track"
    fi
  fi

  # 2. Active plans, from the descriptor's plans directory.
  plans_dir="$(desc_get paths plans)"
  [ -n "$plans_dir" ] || plans_dir="docs/plans"
  if [ -d "$plans_dir" ]; then
    total=0
    listed=0
    plan_list=""
    for f in "$plans_dir"/*.md; do
      [ -f "$f" ] || continue
      head -n 40 "$f" | grep -qE '^status:[[:space:]]*active([[:space:]]|$)' || continue
      total=$((total + 1))
      [ "$listed" -lt 5 ] || continue
      pid="$(head -n 40 "$f" | sed -n 's/^plan:[[:space:]]*//p' | head -n1)"
      [ -n "$pid" ] || pid="$(basename "$f" .md)"
      imp="$(head -n 40 "$f" | sed -n 's/^implements:[[:space:]]*//p' | head -n1 \
             | sed 's/^\[//; s/\][[:space:]]*$//')"
      entry="$pid"
      [ -n "$imp" ] && entry="$pid ($imp)"
      if [ -z "$plan_list" ]; then plan_list="$entry"; else plan_list="$plan_list · $entry"; fi
      listed=$((listed + 1))
    done
    if [ "$total" -gt 0 ]; then
      if [ "$total" -gt "$listed" ]; then
        plan_list="$plan_list · … and $((total - listed)) more"
      fi
      add "› active plans: $total — $plan_list"
    fi
  fi

  # 3. Open pull requests, only when the forge CLI is installed and answers. Numbers are printed as
  # `PR <n>`; any failure, timeout or unexpected payload prints nothing.
  if have gh; then
    pj="$(tmo 3 gh pr list --state open --limit 5 --json number,title,isDraft 2>/dev/null)"
    case "${pj:-}" in
      \[*)
        recs="$(printf '%s' "$pj" | awk '{ gsub(/\},[[:space:]]*\{/, "}\n{"); print }')"
        pr_list=""
        while IFS= read -r rec; do
          [ -n "$rec" ] || continue
          num="$(printf '%s' "$rec" | grep -oE '"number":[[:space:]]*[0-9]+' | head -n1 | grep -oE '[0-9]+')"
          [ -n "$num" ] || continue
          ttl="$(printf '%s' "$rec" | sed -n 's/.*"title":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
          draft=""
          case "$rec" in *'"isDraft":'*[Tt]rue*) draft=" (draft)" ;; esac
          entry="PR $num"
          [ -n "$ttl" ] && entry="$entry $ttl"
          entry="$entry$draft"
          if [ -z "$pr_list" ]; then pr_list="$entry"; else pr_list="$pr_list · $entry"; fi
        done <<EOF
$recs
EOF
        [ -n "$pr_list" ] && add "› open pull requests: $pr_list"
        ;;
    esac
  fi

  # 4. The drift gate's own verdict, when the gate is vendored here.
  check_script="$(desc_get check script)"
  [ -n "$check_script" ] || check_script="scripts/sdd-check.py"
  if [ -f "$check_script" ]; then
    if have python3; then
      verdict="$(tmo 15 python3 "$check_script" check 2>/dev/null | grep '^sdd-check:' | tail -n1)"
      [ -n "$verdict" ] && add "› drift gate: $verdict"
    fi
  else
    add "› drift gate: not vendored — run /sdd-scaffold --upgrade to vendor sdd-check"
  fi

  # 5. Record HEAD as this session found it, and clear any nudge a previous session left behind.
  key="$(printf '%s' "$PWD" | cksum 2>/dev/null | cut -d' ' -f1)"
  if [ -n "$key" ] && mkdir -p "$STATE_DIR" 2>/dev/null; then
    if have git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git rev-parse HEAD 2>/dev/null > "$STATE_DIR/$key.head"
    fi
    rm -f "$STATE_DIR/$key.nudged" 2>/dev/null
  fi
else
  # Not yet an SDD repo: a single, low-noise pointer (only when a docs/ dir exists, to avoid firing everywhere).
  if [ -d docs ]; then
    add "› SDD plugin available — run /sdd-scaffold to set up the spec-driven docs/ structure (requirements, specs, ADRs, plans, traceability)."
  fi
fi

emit "$out"

exit 0

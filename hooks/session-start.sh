#!/usr/bin/env bash
# SessionStart hook (host-agnostic): when a Spec-Driven Development repository is detected, print one
# context line plus the available /sdd-* surface, then a short orientation — branch and tree state,
# active plans, open pull requests, and the drift-gate verdict. Every external command is optional and
# guarded; each is time-limited when the `timeout` binary is on PATH, and still runs — untimed, not
# skipped — when it isn't (see tmo() below). The script ALWAYS exits 0, so a missing or slow tool
# prints nothing rather than blocking the session — except the vendored drift gate, whose missing
# verdict is itself reported ("no verdict (…)"), since silence there reads as a clean tree.
#
# Working directory: a Cursor payload's first "workspace_roots" entry, when it names a directory;
# otherwise wherever the host started the script.
#
# Host-aware output. Claude Code adds plain stdout to the context. Cursor injects only a JSON object
# on stdout — {"additional_context": "<text>"} — ignoring plain text. The two are told apart by a
# positive marker (Cursor's payload carries "workspace_roots"/"cursor_version"; both carry
# "hook_event_name"). A manual run (stdin is a terminal, or the payload is empty) prints plain text.
#
# Shared state with hooks/session-stop.sh: STATE_DIR below, keyed on the working directory plus a
# session identifier when the host payload provides one. Claude Code's payload always carries
# "session_id", so concurrent Claude Code sessions in the same repository get separate keys; a host
# whose payload carries no such field falls back to the working directory alone, so concurrent
# sessions there still share one key (pre-existing behaviour, not a regression). This hook records
# HEAD as it found it and clears any nudge left by an earlier session.
set -u

# Resolve the shared state directory without tripping `set -u` on an unset $HOME: prefer
# CLAUDE_PLUGIN_DATA, then XDG_STATE_HOME, then $HOME/.local/state, then a per-user temp fallback so a
# minimal or stripped environment still gets working state (and therefore the nudge) rather than a
# crash. Every write below this point stays guarded, so a still-unwritable fallback degrades to no
# state rather than an error.
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

# Read one scalar key from docs/.sdd.yaml, without a YAML parser. `desc_get paths plans` returns the
# value of `plans:` nested directly under the `paths:` block — and not the `plans:` that names a check
# family elsewhere in the file. An empty block name reads a top-level key: `desc_get "" traceability`
# finds `traceability:` in a descriptor written without the `sdd:` wrapper.
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

is_sdd_repo() {
  [ -f docs/.sdd.yaml ] && return 0
  [ -d docs/specifications ] && return 0
  [ -f docs/specifications/traceability.yaml ] && return 0
  return 1
}

# ---------------------------------------------------------------- host detection
payload=""
[ -t 0 ] || payload="$(cat 2>/dev/null)"

# Detect the host on a POSITIVE marker, never the absence of one: a Cursor payload also
# carries "hook_event_name", so keying Claude on that field alone misclassifies Cursor.
# Cursor's payload carries "workspace_roots" and "cursor_version"; Claude Code's does not.
host=plain
if [ -n "$payload" ]; then
  case "$payload" in
    *'"workspace_roots"'*|*'"cursor_version"'*) host=cursor ;;
    *'"hook_event_name"'*)                      host=claude ;;
  esac
fi
ws="$(workspace_root "$payload")"
if [ -n "$ws" ] && [ -d "$ws" ]; then cd "$ws" 2>/dev/null || :; fi

# Claude Code sends `source` (startup | resume | clear | compact | fork). It is read here and
# deliberately not acted on: the full orientation prints for every source.
src="$(printf '%s' "$payload" \
       | grep -oE '"source"[[:space:]]*:[[:space:]]*"[^"]*"' \
       | head -n1 | sed -E 's/.*"([^"]*)"$/\1/')"
: "$src"

# Claude Code's payload carries "session_id" on every hook; folded into the state key below (step 5)
# so concurrent sessions in one repository do not share a HEAD baseline. Empty on a host whose payload
# does not carry the field — see the STATE_DIR comment above for what that falls back to.
sid="$(printf '%s' "$payload" \
       | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' \
       | head -n1 | sed -E 's/.*"([^"]*)"$/\1/')"

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
      case "$f" in *_template.md) continue ;; esac   # the scaffold's stub is not an active plan
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
  # Only when a home for gh's own state exists: with HOME and XDG_STATE_HOME both unset, gh
  # writes its device-id under the current directory — i.e. into the repository being opened.
  if have gh && { [ -n "${HOME:-}" ] || [ -n "${XDG_STATE_HOME:-}" ]; }; then
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
          if printf '%s' "$rec" | grep -qE '"isDraft"[[:space:]]*:[[:space:]]*true'; then
            draft=" (draft)"
          fi
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
    # A vendored gate that yields no verdict line is reported, never silenced: a crash, a timeout or
    # a missing interpreter would otherwise look exactly like a repository with no gate at all.
    if have python3; then
      gate_out="$(tmo 15 python3 "$check_script" check 2>/dev/null)"
      gate_rc=$?
      verdict="$(printf '%s\n' "$gate_out" | grep '^sdd-check:' | tail -n1)"
      if [ -n "$verdict" ]; then
        add "› drift gate: $verdict"
      elif [ "$gate_rc" -eq 124 ] && have timeout; then
        add "› drift gate: no verdict (timed out)"
      else
        add "› drift gate: no verdict (exit $gate_rc)"
      fi
    else
      add "› drift gate: no verdict (python3 not found)"
    fi
  else
    add "› drift gate: not vendored — run /sdd-scaffold --upgrade to vendor sdd-check"
  fi

  # 5. Record HEAD as this session found it, and clear any nudge a previous session left behind.
  key_src="$PWD"
  [ -n "$sid" ] && key_src="$PWD:$sid"
  key="$(printf '%s' "$key_src" | cksum 2>/dev/null | cut -d' ' -f1)"
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

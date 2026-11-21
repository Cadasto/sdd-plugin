#!/usr/bin/env bash
# Graceful entry point for the repo validator.
#
# The real checks live in scripts/validate.py. Python can't recover from "Python is
# not installed" (the interpreter is what's missing), so this wrapper handles that case:
#   - Python 3.11+ present -> run the full validator and propagate its exit code
#                             (real validation failures still fail, as intended).
#   - Python 3.11+ absent  -> print a WARNING and skip it, so a missing or older interpreter
#                             never blocks a contributor. Deep validation still runs in CI, which
#                             pins Python (see .github/workflows/validate.yml), and
#                             `claude plugin validate .` covers the basics without Python.
# Either way the hook behaviour tests (scripts/hooks-test.sh) then run: they need only bash
# and git, so a missing Python is no reason to skip them.
set -u

here="$(cd "$(dirname "$0")" && pwd)"

# The first of python3 and python that is Python 3.11 or newer; an older one is named in the warning.
py=""
old=""
for cand in python3 python; do
  command -v "$cand" >/dev/null 2>&1 || continue
  if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    py="$cand"
    break
  fi
  [ -n "$old" ] || old="$("$cand" -c 'import sys; print("Python %d.%d.%d (%s)" % (tuple(sys.version_info[:3]) + (sys.executable,)))' 2>/dev/null)"
done

if [ -z "$py" ]; then
  if [ -n "$old" ]; then
    echo "WARNING: found $old, but the validator needs Python 3.11 or newer; skipping deep manifest/frontmatter validation." >&2
  else
    echo "WARNING: Python 3 not found — skipping deep manifest/frontmatter validation." >&2
  fi
  echo "         This is optional locally. For full checks put a Python 3.11+ first on PATH and re-run," >&2
  echo "         or run 'claude plugin validate .' (no Python required)." >&2
else
  "$py" "$here/validate.py" "$@" || exit $?
fi

# The hook behaviour tests need only bash and git, not Python. Skip gracefully without git.
if command -v git >/dev/null 2>&1; then
  bash "$here/hooks-test.sh" || exit $?
else
  echo "WARNING: git not found — skipping hook behaviour tests (scripts/hooks-test.sh)." >&2
fi

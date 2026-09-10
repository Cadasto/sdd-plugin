#!/usr/bin/env bash
# Graceful entry point for the repo validator.
#
# The real checks live in scripts/validate.py. Python can't recover from "Python is
# not installed" (the interpreter is what's missing), so this wrapper handles that case:
#   - Python 3 present  -> run the full validator and propagate its exit code
#                          (real validation failures still fail, as intended).
#   - Python 3 absent   -> print a WARNING and exit 0, so a missing interpreter never
#                          blocks a contributor. Deep validation still runs in CI, which
#                          pins Python (see .github/workflows/validate.yml), and
#                          `claude plugin validate .` covers the basics without Python.
set -u

here="$(cd "$(dirname "$0")" && pwd)"

py=""
if command -v python3 >/dev/null 2>&1; then
  py=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then
  py=python
fi

if [ -z "$py" ]; then
  echo "WARNING: Python 3 not found — skipping deep manifest/frontmatter validation." >&2
  echo "         This is optional locally. For full checks install python3 and re-run," >&2
  echo "         or run 'claude plugin validate .' (no Python required)." >&2
  exit 0
fi

"$py" "$here/validate.py" "$@" || exit $?

# The hook behaviour tests need only bash and git, not Python. Skip gracefully without git.
if command -v git >/dev/null 2>&1; then
  bash "$here/hooks-test.sh" || exit $?
else
  echo "WARNING: git not found — skipping hook behaviour tests (scripts/hooks-test.sh)." >&2
fi

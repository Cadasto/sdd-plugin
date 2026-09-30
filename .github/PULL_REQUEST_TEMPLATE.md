## Summary

<!-- What changed and why, in prose. Name the decisions taken and the alternatives not taken. -->

## Docs

<!-- The references, skills, agents and docs pages this change touches or reconciles; the methodology section each rule cites. -->

## Verification

- `./scripts/validate.sh` — <what the output said>
- `python3 -m unittest discover -s tools/tests` and `python3 tools/sdd-check.py selftest` — <result, when `tools/` changed>
- `claude plugin validate .` — <result>
- red before green / can-fail proof: <the tests that failed first, the guards removed>

## Notes for review

<!-- Where to look hardest; what is out of scope; a known gap left on purpose. Omit when there is nothing to say. -->

## Checklist

- [ ] Scoped to one logical change
- [ ] The gates above pass locally and their output was read
- [ ] CHANGELOG entry under Unreleased, when the change is user-visible; version bumped per [docs/versioning.md](../docs/versioning.md) at release
- [ ] Both manifests kept in sync, and AGENTS.md, README.md, the Cursor rule and `hooks/session-start.sh` synced when components changed
- [ ] No internal or private repository names, absolute paths or organisation-private details; disclosure grep clean over the tree, `CHANGELOG.md` and this branch's commit messages

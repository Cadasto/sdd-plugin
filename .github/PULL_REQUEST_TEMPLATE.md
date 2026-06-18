## Summary

<!-- What does this PR change, and why? -->

## Checklist

- [ ] `./scripts/validate.sh` passes (or `claude plugin validate .` if Python is unavailable)
- [ ] `claude plugin validate .` passes
- [ ] Skill / agent triggering tested locally (see [docs/testing.md](../docs/testing.md))
- [ ] Cursor install tested locally when manifest, rule, or hook content changed (see [docs/install.md](../docs/install.md#cursor))
- [ ] Both manifests kept in sync when metadata changed: `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`
- [ ] Methodology rules cite `references/sdd-methodology.md` rather than restating them; no normative rule duplicated
- [ ] No internal/private repo names, absolute paths, or org-private details added (this repo may be public)
- [ ] Version bumped and [CHANGELOG.md](../CHANGELOG.md) updated (if component content changed) — see [docs/versioning.md](../docs/versioning.md)
- [ ] Docs synced (AGENTS.md, README.md, `hooks/session-start.sh`) when components were added or renamed

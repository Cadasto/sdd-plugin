# Versioning and Releases

This plugin uses [Semantic Versioning](https://semver.org), adapted to skill / agent / rule / reference content:

| Bump | When |
|------|------|
| **Major** | A skill/agent/rule is removed or renamed, or its behaviour/scope changes incompatibly; a methodology rule changes in a way that invalidates existing usage |
| **Minor** | A new component is added, or an existing one's coverage meaningfully expands |
| **Patch** | Typos, clarifications, reference/source fixes — no behaviour change |

While on the `0.x` line, treat the plugin as pre-stable: a breaking change may still ship in a minor bump.

## Release steps

1. Bump `version` in **both** manifests (they must agree): `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`. Keep `description` and `author` identical across both — `scripts/validate.py` enforces this parity.
2. Run `./scripts/validate.sh` and `claude plugin validate .`.
3. **Dogfood:** install from a working copy (`claude plugin add /path/to/sdd-plugin`) and run the full loop on a throwaway repo on **both** hosts — see [testing.md](testing.md).
4. Fold the accumulated `## [Unreleased]` notes into a dated `## [X.Y.Z] - YYYY-MM-DD` section in [CHANGELOG.md](../CHANGELOG.md) (Keep a Changelog — groups in order Added, Changed, Deprecated, Removed, Fixed, Security; see [AGENTS.md](../AGENTS.md#changelog-style)).
5. Sync the docs surface (AGENTS.md, README.md) with what shipped. Keep the `/sdd-*` list in `hooks/session-start.sh` in step when a skill is added or renamed.
6. Commit (`chore(release): vX.Y.Z`) and tag: `git tag -a vX.Y.Z -m "sdd-plugin vX.Y.Z"`.
7. Push commits and the tag: `git push origin main --follow-tags`.

## No MCP or marketplace coupling

This plugin has **no companion MCP server**, so there is no server-compatibility version to align. It is listed in the **Cadasto marketplace** (`cadasto/plugin-marketplace`); the marketplace tracks the repo's default branch, so update that entry only when `name`, `description`, or `repository` changes — there is no version pin to bump there.

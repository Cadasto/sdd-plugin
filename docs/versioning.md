# Versioning and releases

This page is for maintainers cutting a release: which SemVer bump a change needs, the release steps in order, and the marketplace update that makes a release live. The plugin uses [Semantic Versioning](https://semver.org), adapted to skill, agent, rule, and reference content:

| Bump | When |
|------|------|
| **Major** | A skill, agent, or rule is removed or renamed, or its behaviour or scope changes incompatibly; a methodology rule changes in a way that invalidates existing usage |
| **Minor** | A new component is added, or an existing one's coverage meaningfully expands |
| **Patch** | Typos, clarifications, reference or source fixes; no behaviour change |

While on the `0.x` line, treat the plugin as pre-stable: a breaking change may still ship in a minor bump.

## Release steps

Steps 1 to 4 and 6 belong in the pull request that carries the release's changes, with the changelog notes still under `## [Unreleased]`. Steps 5, 7 and 8 happen on `main` after that pull request merges, so the release commit only dates the changelog.

1. Bump `version` in both manifests, `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`, and keep their `description`, `author`, `license`, `repository`, and `keywords` identical. In the same step, bump the `__version__` of `tools/sdd-check.py` and `tools/sdd-pr.py`, and `check.version` in `references/templates/sdd.yaml`. `scripts/validate.py` fails when any of these disagree. A repository that already vendored the gate picks up the new version with `/sdd-scaffold --upgrade`.
2. Update the version badge at the top of [README.md](../README.md).
3. Run `./scripts/validate.sh` and `claude plugin validate .`.
4. Dogfood: load the working copy (`claude --plugin-dir /path/to/sdd-plugin`) and run the full loop on a throwaway repo on both hosts; see [testing.md](testing.md).
5. Fold the `## [Unreleased]` notes into a dated `## [X.Y.Z] - YYYY-MM-DD` section in [CHANGELOG.md](../CHANGELOG.md). The groups follow Keep a Changelog, in the order Added, Changed, Deprecated, Removed, Fixed, Security ([AGENTS.md](../AGENTS.md#changelog-style)).
6. Sync AGENTS.md and README.md with what ships. When a skill is added or renamed, update the `/sdd-*` list in `hooks/session-start.sh` too.
7. Commit (`chore(release): vX.Y.Z`) and tag: `git tag -a vX.Y.Z -m "sdd-plugin vX.Y.Z"`.
8. Push the commit and the tag: `git push origin main --follow-tags`.
9. **Update the marketplace entry.** The release is not live until this lands; see below.

## No MCP coupling

This plugin has no companion MCP server, so there is no server version to keep in step.

## Marketplace

This plugin is listed in the [Cadasto marketplace](https://github.com/Cadasto/plugin-marketplace) as `sdd@cadasto`. The catalog **pins every entry to a release tag**, so tagging and pushing a release here does not ship it: users see nothing until the marketplace entry moves.

After step 8, update the entry in `Cadasto/plugin-marketplace`:

1. Bump that entry's `version` and `source.ref` to the new `vX.Y.Z` together; the catalog's validation rejects a mismatch.
2. Bump the catalog's own `metadata.version`: a plugin minor or major release is a catalog minor, a plugin patch is a catalog patch.
3. Add a `CHANGELOG.md` line and run `python3 scripts/validate.py --fix`.

See the catalog's [docs/versioning.md](https://github.com/Cadasto/plugin-marketplace/blob/main/docs/versioning.md).

The catalog copies `description`, `version`, and `keywords` verbatim from `.claude-plugin/plugin.json`, so update the entry whenever any of those change, not only on a release.

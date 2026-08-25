# Versioning and releases

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
3. **Dogfood:** load the working copy (`claude --plugin-dir /path/to/sdd-plugin`) and run the full loop on a throwaway repo on **both** hosts — see [testing.md](testing.md).
4. Fold the accumulated `## [Unreleased]` notes into a dated `## [X.Y.Z] - YYYY-MM-DD` section in [CHANGELOG.md](../CHANGELOG.md) (Keep a Changelog — groups in order Added, Changed, Deprecated, Removed, Fixed, Security; see [AGENTS.md](../AGENTS.md#changelog-style)).
5. Sync the docs surface (AGENTS.md, README.md) with what shipped. Keep the `/sdd-*` list in `hooks/session-start.sh` in step when a skill is added or renamed.
6. Commit (`chore(release): vX.Y.Z`) and tag: `git tag -a vX.Y.Z -m "sdd-plugin vX.Y.Z"`.
7. Push commits and the tag: `git push origin main --follow-tags`.
8. **Update the marketplace entry** — the release is not live until this lands. See below.

## No MCP coupling

This plugin has **no companion MCP server**, so there is no server-compatibility version to align.

## Marketplace

This plugin is listed in the [Cadasto marketplace](https://github.com/Cadasto/plugin-marketplace) as `sdd@cadasto`. The catalog **pins every entry to a release tag**, so tagging and pushing a release here does not ship it — users see nothing until the marketplace entry moves.

After step 7, update the entry in `Cadasto/plugin-marketplace`:

1. Bump that entry's `version` **and** `source.ref` to the new `vX.Y.Z` together (validation there rejects a mismatch).
2. Bump the catalog's own `metadata.version` — a plugin minor/major is a catalog **minor**, a plugin patch is a catalog **patch**.
3. Add a `CHANGELOG.md` line and run `python3 scripts/validate.py --fix`.

See the catalog's [docs/versioning.md](https://github.com/Cadasto/plugin-marketplace/blob/main/docs/versioning.md).

The catalog copies `description`, `version`, and `keywords` verbatim from `.claude-plugin/plugin.json`, so update the entry whenever any of those change — not only on a release.

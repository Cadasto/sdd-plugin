# Upgrading

## From 0.5.x to 0.6.0

0.6.0 ships the gate the rules already implied: one vendored, versioned, self-testing script,
`sdd-check`, that checks the traceability chain in both directions and lints the prose rules a
machine can apply. Moving a repository already on 0.5.x means adopting the gate, not absorbing
another methodology change. Work through the steps in order — several later steps depend on an
earlier one having actually run, not just been read.

1. **Vendor and pin the gate.** Run `/sdd-scaffold --upgrade`, or by hand: copy `tools/sdd-check.py`
   into the repository at `check.script` (`scripts/sdd-check.py` by default) and set `check.version`
   in `docs/.sdd.yaml` to match the copy's own `__version__`. Until both are true, `spec-check`
   cannot pass: a missing script means the build target has nothing to run, and a version mismatch
   fails the `descriptor` family outright.
2. **Adopt the `check:` block.** `--upgrade` fills in `script`, `version`, `links.exclude`,
   `changelog.path`/`max_words`, `code_roots`, `test_globs`, `probes_catalogue`, and
   `families` with defaults. Review `check.families` if a family should start at `warn` while the
   tree catches up before you move it to `error` — every family the descriptor doesn't mention
   uses the gate's own default. The block's full shape and every key's meaning are in
   [traceability-schema.md § The check block](../references/traceability-schema.md#the-check-block).
3. **Declare a `kind:` on every document.** `--upgrade` writes it into every document it emits or
   recognises; a hand-written document it doesn't touch needs one frontmatter line added by hand —
   `kind: requirement` (or `specification`, `adr`, `plan`, `guide`, `analysis`, `operations`,
   `reference`, `upstream`). `--upgrade` never writes `kind:` into a document it doesn't touch: the
   location fallback (a document under `paths.specifications` is read as a specification, and so on for
   the other kinds) keeps it in the generated indexes meanwhile, and `doc-kinds` keeps warning about the
   missing declaration until an author adds one.
4. **Delete the retired `plans:` key** from any traceability record that still carries it (removed
   from the record shape at 0.5.0, but nothing checked for it until now). The `map-schema` family
   now reports a lingering one as a warning — "unknown key" — instead of staying silent.
5. **Leave `ground_truth` and `upstream` alone if they're already scalars.** The descriptor family
   accepts the legacy single-string shape for both, alongside the newer ordered-list `ground_truth`
   and named-relations `upstream` map; neither is a forced rewrite.
6. **Wrap the three hand-written index tables in the generated-block markers** —
   `<!-- sdd:generated requirements-index -->` … `<!-- /sdd:generated -->` around the requirements,
   specifications and ADR tables — or let `--upgrade` wrap them for you.
7. **Run `sdd-check generate --verify` before the real `generate` — required, not optional.** A table
   just wrapped in markers, or a document `--upgrade` just emitted, holds placeholder content that
   doesn't yet match what `generate` would write from the map, so running `check` first would fail the
   `generated` family on that mismatch every time — but that is not why `--verify` comes first. `--verify`
   reports what would change and writes nothing. Read its diff in full, one block at a time: a row that
   appears in the current content with no corresponding row in the generated content is a hand-written row
   `traceability.yaml` carries no record for — reformatting a row is not this; only a row that disappears
   entirely counts. **If the diff drops even one such row, anywhere in any block, stop here. Do not run the
   real `generate`.** Running it anyway is what destroys the row: `generate` rewrites each block from the
   map alone, so a row the map has never heard of is silently gone — exit 0, no warning, nothing to undo.
   Capture the missing requirement with `/sdd-specify` first, or delete the stale row by hand if it
   genuinely no longer belongs, then re-run `generate --verify` and confirm the diff drops nothing before
   running the real `sdd-check generate`. Only once every hand-written row is represented in the map does
   `generate` populate every marker block and each requirement's `status`/`implementation` frontmatter, and
   only then does `check` have something real to verify.
8. **A row `--upgrade` can't match to a map record stops the run instead of being guessed at or
   overwritten.** Capture the missing requirement with `/sdd-specify` first — or delete the stale
   row by hand if it no longer belongs — then re-run `--upgrade`.
9. **An RFC-2119 keyword outside `docs/specifications/` is now linted.** `MUST`, `SHOULD`, `MAY`,
   and the rest are binding words with no traceability chain to enforce them anywhere but a spec.
   The gate errors on one in a `requirement`, `adr`, `plan` or `reference` document; in `guide`,
   `analysis`, `operations` or `upstream` it follows the family's own severity (`warn` by default).
   Reword the sentence, move the normative statement into the spec it belongs in, or waive the file for
   this one family with `<!-- sdd-check: allow <family> -->` (here, `rfc2119`) — see
   [sdd-check.md § Waivers](../references/sdd-check.md#waivers) for the syntax and why an example must
   never spell out a real family name.
10. **The Stop hook nudges once per session** when it ends with no commit and uncommitted changes
    still in the tree. Opt out per repository with `hooks.stop_nudge: false` in `docs/.sdd.yaml`.
11. **A private `spec-check` script wired before the gate existed doesn't need to go immediately.**
    Keep it running beside the vendored `sdd-check` until you've confirmed the gate's families cover
    what the private script checked, then retire the private script.

## From 0.4.x to 0.5.0

0.5.0 changes the plan lifecycle, the traceability record, the review output, and the descriptor. SemVer 0.x allows breaking changes in a minor release; these are the ones, what you see, and the mechanical fix. Work down the table in order.

| What changed | What you see | Fix |
|---|---|---|
| The descriptor needs an `agents:` block | `/sdd-deliver` or `/sdd-review` stops with "route to `/sdd-scaffold` to fill that block" | Run `/sdd-scaffold`; a top-up run adds the block and touches no other key. Confirm `agents.reviewers` and the code-index line in `docs/ai-workflow.md` § Orchestration. |
| The `plans:` axis is gone from traceability records | A `spec-check` that requires `plans:` fails or reports every record | Delete the `plans:` key from each record in `traceability.yaml`; drop that check from your `spec-check`. |
| `/sdd-archive` no longer moves the plan | Finished plans stay in `docs/plans/` with `status: done` | Nothing to do. Never `git mv` a plan; `/sdd-finalize` deletes finished plans at the next version bump. |
| `docs/plans/archive/` and the plans index are retired | The legacy directory is still in the tree | The first `/sdd-finalize` run sweeps `done` and `abandoned` plans from it and removes the directory once empty. A plan there without a frontmatter `status` stops the sweep; add the line first. |
| `paths.plans_archive` is gone from the descriptor | An unread key in `docs/.sdd.yaml` | `/sdd-finalize` removes the line in the same commit, or delete it by hand. |
| The process-doc templates were rewritten | Your `docs/ai-workflow.md`, `docs/development-process.md`, and `AGENTS.md` still route delivery to a general engineering plugin and describe archive-and-index; the scaffold never overwrites a populated file | Move each file aside, run `/sdd-scaffold`, and merge your local tuning back; or paste § Orchestration, § Review, the lanes, and the PR-body close-out block from the plugin's `references/templates/`. |
| The PR body carries a `Lane:` line | `/sdd-review` falls back to the plan header, and a maintenance PR has none | Add `Lane: full` or `Lane: maintenance — no normative change` to the body, from the close-out block in `docs/development-process.md`. |
| Review output is one ledger comment | A reviewer given the old prompt posts one comment per finding | Paste the block `/sdd-review --panel` prints; do not retype it. |
| `sdd-with-superpowers.md` is removed | Links to it or to `docs/superpowers/` break | Link the router skill's paragraph on the optional general engineering plugin instead. |

Tool grants in `agents/*.md` are Claude Code fields; on Cursor they are contracts the agent bodies state — see the Cursor section of [install.md](install.md#cursor).

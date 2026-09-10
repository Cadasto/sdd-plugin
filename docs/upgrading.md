# Upgrading

## From 0.5.x to 0.6.0

0.6.0 ships the gate the rules already implied: one vendored, versioned, self-testing script,
`sdd-check`, that checks the traceability chain in both directions and lints the prose rules a
machine can apply. Moving a repository already on 0.5.x means adopting the gate, not absorbing
another methodology change. Work through the steps in order — several later steps depend on an
earlier one having actually run, not just been read.

1. **Adopt the `check:` block.** `--upgrade` fills in `script`, `version`, `links.exclude`,
   `changelog.path`/`max_words`, `code_roots`, `test_globs`, `probes_catalogue`, and
   `families` with defaults. Review `check.families` if a family should start at `warn` while the
   tree catches up before you move it to `error` — every family the descriptor doesn't mention
   uses the gate's own default. The block's full shape and every key's meaning are in
   [traceability-schema.md § The check block](../references/traceability-schema.md#the-check-block).
2. **Vendor and pin the gate.** Run `/sdd-scaffold --upgrade`, or by hand: copy `tools/sdd-check.py`
   into the repository at the `check.script` path step 1 just added (`scripts/sdd-check.py` by
   default) and set `check.version` — now that the `check:` block exists to hold it — to match the
   copy's own `__version__`. Until both are true, `spec-check` cannot pass: a missing script means
   the build target has nothing to run, and a version mismatch fails the `descriptor` family
   outright. If the repository has no `CHANGELOG.md`, create one with a `# Changelog` heading and a
   blank `## [Unreleased]` section — `check.changelog.path` names a hard error when the file is absent.
3. **Declare a `kind:` on every document.** `--upgrade` writes it into the ten scaffold-owned files it
   emits (the process docs, the three index READMEs, the four `_template.md` stubs); a hand-written
   document it doesn't touch needs one frontmatter line added by hand —
   `kind: requirement` (or `specification`, `adr`, `plan`, `guide`, `analysis`, `operations`,
   `reference`, `upstream`). `--upgrade` never writes `kind:` into a document it doesn't touch: the
   location fallback (a document under `paths.specifications` is read as a specification, and so on for
   the other kinds) keeps it in the generated indexes meanwhile, and `doc-kinds` keeps warning about the
   missing declaration until an author adds one.
4. **Convert each existing specification's inert anchor comment into a real anchor.** The
   specification template now opens every `§` section with a real `<a id="…"></a>` tag; before
   0.6.0 the same spot held only an HTML comment that named the id in prose without ever anchoring
   it. `--upgrade` does not rewrite a specification body it doesn't touch, so this is not automatic:
   every specification a 0.5.x repository already has keeps the old comment-only form after
   upgrading, until you convert it by hand. Left unconverted, the id a `canonical:` field or a
   cross-reference cites resolves to nothing — you'll see it as a red gate, not a silent gap:
   `map-to-tree` reports `canonical anchor '#<id>' resolves to no heading slug and no explicit
   anchor in <file>`, and `links` reports the same failure from the other direction, `the fragment
   '#<id>' matches no heading slug and no explicit anchor in <file>`, for anything that links to the
   same spot. Recognise the old form and convert it, one `§` at a time — for example:

   ```text
   Before (0.5.x):
   ## §1 — <section title>

   <!-- Stable section anchor: id="section-title-req-area-nnn". Never renumber a published §. -->

   After (0.6.0):
   ## §1 — <section title>

   <a id="section-title-req-area-nnn"></a>
   <!-- Stable section anchor. Replace the id with this section's own slug and REQ id — never
        renumber a published §; the id, once cited by a canonical: field, is permanent. -->
   ```

   Keep the id text itself exactly as it already is — only the comment above the prose becomes a
   real `<a id="…"></a>` tag, with the same explanatory comment kept beneath it. Do this for every
   `§` in every specification the repository already has; a specification `--upgrade` emits fresh,
   or one `/sdd-specify` writes from today's template, already uses the fixed form and needs nothing
   here.
5. **Delete the retired `plans:` key** from any traceability record that still carries it (removed
   from the record shape at 0.5.0, but nothing checked for it until now). The `map-schema` family
   now reports a lingering one as a warning — "unknown key" — instead of staying silent.
6. **Leave `ground_truth` and `upstream` alone if they're already scalars.** The descriptor family
   accepts the legacy single-string shape for both, alongside the newer ordered-list `ground_truth`
   and named-relations `upstream` map; neither is a forced rewrite.
7. **Wrap the three hand-written index tables in the generated-block markers** —
   `<!-- sdd:generated requirements-index -->` … `<!-- /sdd:generated -->` around the requirements
   table, `<!-- sdd:generated specifications-index -->` … `<!-- /sdd:generated -->` around the
   specifications table, and `<!-- sdd:generated adr-index -->` … `<!-- /sdd:generated -->` around
   the ADR table — or let `--upgrade` wrap all three for you.
8. **Run `sdd-check generate --verify` before the real `generate`.** A table just wrapped in markers
   holds content that doesn't yet match what `generate` would write from the map, so `--verify` exits 1
   on that staleness — expected here; read the diff, not the exit code. A row in the current content with
   no matching row in the generated content is a row `generate` would drop. Diagnose it by block: a
   requirements row with no `REQ-` record in `traceability.yaml`; a specifications row whose file is
   missing under `paths.specifications` or whose kind is not `specification`; an adr row whose file is
   missing or is named outside `^(ADR-|\d{4}-)`. Capture the missing record (`/sdd-specify` for a
   requirement) or delete the stale row by hand if it no longer belongs, then re-run. Once every row is
   represented, `generate` populates every marker block and each requirement's `status`/`implementation`
   frontmatter, and `check` has something real to verify.
9. **`generate` never overwrites a row it cannot match to a record.** The tool refuses on its own: the
   real `generate` writes nothing while any hand-written row would vanish, and names each one. This is a
   guarantee, not a discipline you have to remember — step 8 is the preview that tells you which record to
   capture or which stale row to remove.
10. **An RFC-2119 keyword outside `docs/specifications/` is now linted.** `MUST`, `SHOULD`, `MAY`,
    and the rest are binding words with no traceability chain to enforce them anywhere but a spec.
    The gate errors on one in a `requirement`, `adr`, `plan` or `reference` document; in `guide`,
    `analysis`, `operations` or `upstream` it follows the family's own severity (`warn` by default).
    Reword the sentence, move the normative statement into the spec it belongs in, or waive the file for
    this one family with `<!-- sdd-check: allow <family> -->` (here, `rfc2119`) — see
    [sdd-check.md § Waivers](../references/sdd-check.md#waivers) for the syntax and why an example must
    never spell out a real family name.
11. **The Stop hook nudges once per session** when it ends with no commit and uncommitted changes
    still in the tree. Opt out per repository with `hooks.stop_nudge: false` in `docs/.sdd.yaml`.
12. **A private `spec-check` script wired before the gate existed doesn't need to go immediately.**
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

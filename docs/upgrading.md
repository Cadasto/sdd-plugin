# Upgrading

This page is for maintainers of a repository scaffolded by an earlier version of the plugin. It lists, per release, what changed for an existing repository and the steps to bring it up to date, by `/sdd-scaffold --upgrade` or by hand. A repository that has never been scaffolded starts from the [quick start](quick-start.md) instead.

## From 0.8.1

The findings file moves out of the checkout into the clone's git directory, `sdd-pr` makes every change
to it, and suggestions are routed before merge instead of dying with the file.

1. **Nothing to move by hand.** The first `sdd-pr` command on a branch moves its
   `.sdd/findings/<branch>.md` into `<git-common-dir>/sdd/findings/`, where every worktree of the clone
   finds it, and says so; it looks in every worktree of the clone. When two checkouts hold a file for the
   same branch, the second is named and left in place: fold its open lines and suggestions in with
   `sdd-pr add -` (resolved lines need not come along), then delete it. The `.sdd/` ignore line may
   stay; `/.sdd/` is the anchored form a new scaffold writes.
2. **Stop editing the file.** `sdd-pr add`, `flip`, `record` and `rename` replace every hand edit; the
   skills already call them. A branch renamed under its findings uses `sdd-pr rename --from <old>`.
3. **Suggestions left on open branches.** Route each before merge, with `sdd-pr flip <path:line>
   --deferred "<where>"` or `--dropped`; `/sdd-deliver --close-out` asks for it.
4. **Before a pull request opens**, `sdd-pr status` now says `Mergeable: no — no pull request`.
5. **Committed plans.** A plan may be committed or not; mark a committed one `kind: plan` and the gate
   and the reviewers leave it alone. `/sdd-scaffold --upgrade` offers the line for plans under `docs/`.
6. **Versions.** The session-start line now names the plugin version on Cursor too, and says when the
   vendored gate is older than the plugin, or the plugin older than the repository. `sdd-pr` refuses to
   write while the plugin is the older one.
7. **Review range.** `/sdd-review` and `sdd-pr scope` read the whole branch by default, so a second
   agent or model reviews all of it; `--since-last` reads only the commits since the last pass and
   replaces `--all`.
8. **Pull request summaries.** Each pass now posts one review with a short summary, even when it
   found nothing. An open pull request gets one on the next `post` after a pass at its head.
9. **Process documents.** `--upgrade` merges template changes section by section into tuned
   `ai-workflow.md`, `development-process.md` and pull-request templates, and writes `/.sdd/` rather than
   a bare `.sdd/`.

## From 0.8.0 to 0.8.1

Pull requests now carry a review-state block in their body, and a pass on which no reviewer reported no
longer counts. `sdd-check` changed only its version number, so re-vendoring it with
`/sdd-scaffold --upgrade` is optional.

1. **Open pull requests.** Run `python3 <plugin root>/tools/sdd-pr.py status --write-body --pr <N>` on
   each one from the checkout that holds its findings file; until then `status` reports the review state
   as missing. On Azure DevOps a description over 4000 characters cannot take the block: shorten it.
2. **Empty passes.** A range closed only by a `(0 of <m>)` line is open again: run `/sdd-review`, or
   record your own review as `Reviewed <sha> · <date> · maintainer: <name> (1 of 1)`.
3. **Deferrals.** A finding the maintainer deferred can be flipped to `- [~] … · deferred: <where>`, so
   the review state lists it.

## From 0.7.x to 0.8.0

0.8.0 replaces the review ledger with a git-ignored findings file per branch, which `sdd-pr` mirrors
to the pull request's inline threads. It folds `/sdd-archive` into `/sdd-deliver --close-out`, takes
plans out of the plugin, and adds a second profile, informative. `/sdd-scaffold --upgrade` proposes
steps 2 to 4 and applies each only when you say yes, because each one edits something the repository
already has.

1. **Re-vendor.** Run `/sdd-scaffold --upgrade`. It copies the 0.8.0 gate over `check.script` and sets
   `check.version`.
2. **Descriptor.** Rename `profile: full` to `profile: formal` (`full` is still read for one release;
   `lightweight` is read as `formal` and reported as a note). Delete the `paths.plans` line (a note
   names it until you do). `forge: auto` is the default and may be left out; set `github`,
   `azure-devops` or `none` to override the remote URL.
3. **Ignore and delete.** Add `.sdd/` to `.gitignore`. Delete `docs/.sdd/reviewers/`: a decline that
   should hold for future changes becomes a specification sentence or an ADR instead. The gate now
   reads nothing git ignores, committed plans under an ignored directory included, and a tracked
   document that links to a git-ignored file fails the `links` family. Point such a link at the pull
   request or commit instead.
4. **Process documents.** `/sdd-scaffold --upgrade` merges the template changes into
   `docs/ai-workflow.md`, `docs/development-process.md` and the pull-request template section by
   section, and keeps this repository's own text.
5. **Open pull requests.** An existing review ledger comment stays as history. Add its open rows once
   with `sdd-pr add`, in the grammar of the plugin's `references/review.md`, and never edit the comment
   again. A `Deferred` row you want to keep becomes `implementation: deferred`
   on its requirement or a *Known gaps* line in the specification. A pull request that merged before
   its last fixes were pushed can leave a ledger whose `Deferred` rows nothing carried forward: move
   each one you want to keep the same way, and drop the rest.
6. **Commands.** `/sdd-archive` is `/sdd-deliver <PR> --close-out`. `/sdd-review` takes `--pr N` instead
   of a positional PR number and has no `--post`; `/sdd-triage` has no `--from`. "What is open, is it
   mergeable, what next" is `python3 <plugin root>/tools/sdd-pr.py status`.
7. **The informative profile** is optional and chosen per repository; `--upgrade` never changes a
   profile on its own. A repository that switches writes `profile: informative` and adds
   `docs/architecture.md` from the plugin's `references/templates/constitution.md`. It may keep or drop
   its map. The gate then runs only `descriptor`, `doc-kinds`, `links`, `changelog` and `generated`.

## From 0.6.x to 0.7.0

0.7.0 fits the gate to repositories that keep a registry of requirement ids, and takes plans out of
the gate's scope: a build status for a withdrawn requirement, a `generate` that no longer lets one bad
map row stop every index, a section convention for specifications titled by requirement id, and a plan
that is a working file nothing reads. Work through the steps in order.

1. **Re-vendor.** Run `/sdd-scaffold --upgrade`. It copies the 0.7.0 gate over `check.script` and
   sets `check.version`; until both happen the `descriptor` family fails the version pin.
2. **Retired requirements.** A record whose requirement was withdrawn, and whose `implementation`
   holds a word outside the vocabulary (for example `deprecated`), takes `implementation: retired`
   and keeps `status: deprecated`. `retired` with any other stability is a `map-schema` error. A
   retired record owes no evidence. A `map-schema` error no longer stops `generate` from writing the
   specifications and ADR indexes; the requirements index and the detail-file status lines stay as
   they are until the map is clean; each index block held back, and the detail-file directory, is named by a `skipped` line, and the run exits 1 even when there is nothing to name.
3. **Section convention.** A repository that titles its specification sections by requirement id,
   such as `## REQ-060 — Title` or `## Topic (REQ-060)`, sets `check.rfc2119.sections:
   requirement-id` (or `either`, when some headings carry `§` instead). Expect new warnings from
   sections that carry no keyword; the `rfc2119` family stays at `warn` by default. Leaving the key
   out keeps 0.6.0's behaviour. The key's meaning is in
   [traceability-schema.md § The check block](../references/traceability-schema.md#the-check-block).
4. **Plans.** The gate reads nothing under `paths.plans`, and `/sdd-finalize` is gone. Delete `plans:`
   from `check.families` (a note names the line until you do) and `plan` from `doc_kinds` (leaving it is
   harmless). `/sdd-scaffold --upgrade` adds `<paths.plans>/` to `.gitignore`; committed plans stay
   tracked until you run `git rm -r --cached <paths.plans>`, and nothing reads them either way, a
   `docs/plans/archive/` directory included. From now on `/sdd-deliver` writes the plan without
   committing it and the pull request body carries the task list; work that is postponed is recorded as
   `implementation: deferred` on its requirement.

## From 0.5.x to 0.6.0

0.6.0 ships the gate the rules already implied: one vendored, versioned, self-testing script,
`sdd-check`, that checks the traceability chain in both directions and lints the prose rules a
machine can apply. Moving a repository already on 0.5.x means adopting the gate, not absorbing
another methodology change. Work through the steps in order: later steps depend on an earlier one
having actually run, not just been read.

1. **Adopt the `check:` block.** `--upgrade` fills in `script`, `version`, `links.exclude`,
   `changelog.path`/`max_words`, `code_roots`, `test_globs`, `probes_catalogue`, and
   `families` with defaults. Review `check.families` if a family should start at `warn` while the
   tree catches up, before you move it to `error`; every family the descriptor doesn't mention
   uses the gate's own default. The block's full shape and every key's meaning are in
   [traceability-schema.md § The check block](../references/traceability-schema.md#the-check-block).
   By hand, copy the `check:` and `hooks:` blocks from the plugin's own
   `references/templates/sdd.yaml` (in the plugin's install directory) into `docs/.sdd.yaml` under
   `sdd:`. Those are the defaults `--upgrade` would write.
2. **Vendor and pin the gate.** Run `/sdd-scaffold --upgrade`, or plain `/sdd-scaffold`, which takes
   the same path on its own when the descriptor has no `check:` block. By hand: copy `tools/sdd-check.py`
   from the plugin's install directory into the repository at the `check.script` path step 1 just added
   (`scripts/sdd-check.py` by default), and set `check.version`, which the new `check:` block now holds,
   to match the copy's own `__version__`. Until both are true, `spec-check` cannot pass: a missing script
   means the build target has nothing to run, and a version mismatch fails the `descriptor` family
   outright. If the repository has no `CHANGELOG.md`, create one with a `# Changelog` heading and a
   blank `## [Unreleased]` section; `check.changelog.path` names a hard error when the file is absent.
   Then wire the build: the 0.5.x scaffold wrote a `spec-check` stub that exits non-zero on purpose.
   Replace its body with `python3 scripts/sdd-check.py selftest && python3 scripts/sdd-check.py check`
   (substitute your `check.script`), in the syntax of your `build_entrypoint`, and keep `ci` depending
   on it. Until then `<build_entrypoint> spec-check` keeps failing whatever the gate says.
3. **Declare a `kind:` on every document.** `--upgrade` writes it into the nine scaffold-owned files it
   emits (the process docs, the three index READMEs, the three `_template.md` stubs); a hand-written
   document it doesn't touch needs one frontmatter line added by hand. If you add them yourself, give the
   process docs (`development-process.md`, `ai-workflow.md`, `ci.md`) and the three index READMEs
   `kind: guide`, and each `_template.md` stub the kind of its folder (`requirement`, `specification`,
   `adr`); a different informative kind such as `reference` would make the RFC-2119 lint
   error on their keywords. Give any other document its own kind:
   `kind: requirement` (or `specification`, `adr`, `guide`, `analysis`, `operations`,
   `reference`, `upstream`). `--upgrade` never writes `kind:` into a document it doesn't touch. The
   location fallback (a document under `paths.specifications` is read as a specification, and so on for
   the other kinds) keeps such a document in the generated indexes meanwhile, and `doc-kinds` keeps
   warning about the missing declaration until an author adds one.
4. **Convert each existing specification's inert anchor comment into a real anchor.** The
   specification template now opens every `§` section with a real `<a id="…"></a>` tag; before
   0.6.0 the same spot held only an HTML comment that named the id in prose without ever anchoring
   it. `--upgrade` does not rewrite a specification body it doesn't touch, so this is not automatic:
   every specification a 0.5.x repository already has keeps the old comment-only form after
   upgrading, until you convert it by hand. Left unconverted, the id a `canonical:` field or a
   cross-reference cites resolves to nothing, and the gate fails rather than leaving a silent gap:
   `map-to-tree` reports `canonical anchor '#<id>' resolves to no heading slug and no explicit
   anchor in <file>`, and `links` reports the same failure from the other direction, `the fragment
   '#<id>' matches no heading slug and no explicit anchor in <file>`, for anything that links to the
   same spot. Recognise the old form and convert it, one `§` at a time. For example:

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

   Keep the id text itself exactly as it already is: only the comment above the prose becomes a
   real `<a id="…"></a>` tag, with the same explanatory comment kept beneath it. Do this for every
   `§` in every specification the repository already has. A specification `--upgrade` emits fresh,
   or one `/sdd-specify` writes from today's template, already uses the fixed form and needs nothing
   here.
5. **Delete the retired `plans:` key** from any traceability record that still carries it (removed
   from the record shape at 0.5.0, but nothing checked for it until now). The `map-schema` family
   now reports a lingering one as an "unknown key" warning instead of staying silent.
6. **Leave `ground_truth` and `upstream` alone if they're already scalars.** The descriptor family
   accepts the legacy single-string shape for both, alongside the newer ordered-list `ground_truth`
   and named-relations `upstream` map; neither is a forced rewrite.
7. **Wrap the three hand-written index tables in the generated-block markers:**
   `<!-- sdd:generated requirements-index -->` … `<!-- /sdd:generated -->` around the requirements
   table, `<!-- sdd:generated specifications-index -->` … `<!-- /sdd:generated -->` around the
   specifications table, and `<!-- sdd:generated adr-index -->` … `<!-- /sdd:generated -->` around
   the ADR table. Or let `--upgrade` wrap all three for you.
8. **Run `sdd-check generate --verify` before the real `generate`.** A table just wrapped in markers
   holds content that doesn't yet match what `generate` would write from the map, so `--verify` exits 1
   on that staleness. That is expected here; read the diff, not the exit code. `--verify` also prints
   every `refused — …` line the real run would. A row is matched by the identifier or spec name inside
   its first cell, so a bare, backticked, or differently linked cell for a record that exists is
   rewritten without a refusal. Act on each refusal by its message:
   - `row <id> has no record in the map`: capture the requirement with `/sdd-specify`, or delete the
     stale row by hand.
   - `row <id> has no matching document`: a specification or ADR file that is missing, not
     `kind: specification`, or (for an ADR) named outside `^(ADR-|\d{4}-)`.
   - A refusal naming a line inside the markers that is not a row (a note, blockquote, bullet, heading,
     or extra column): move that prose outside the markers.
   - A refusal naming a row whose id cell carries `<` or `>` markup other than a whole-cell
     placeholder: remove that markup from the id cell.

   Then re-run. Once nothing is refused, `generate` populates every marker block and each requirement's
   `status`/`implementation` frontmatter, and `check` has something real to verify.
9. **`generate` never discards what it cannot regenerate.** The tool refuses on its own: the real
   `generate` writes nothing while any refusal stands, and names each one. The tool enforces this;
   you do not have to remember it. Step 8 is the preview that tells you what to capture, remove, or
   move.
10. **An RFC-2119 keyword outside `docs/specifications/` is now linted.** `MUST`, `SHOULD`, `MAY`,
    and the rest are binding words with no traceability chain to enforce them anywhere but a spec.
    The gate errors on one in a `requirement`, `adr`, or `reference` document; in `guide`,
    `analysis`, `operations`, or `upstream` it follows the family's own severity (`warn` by default).
    Reword the sentence, move the normative statement into the spec it belongs in, or waive the file for
    this one family with `<!-- sdd-check: allow <family> -->` (here, `rfc2119`). See
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
| `/sdd-archive` no longer moves the plan | Finished plans stay in `docs/plans/` with `status: done` | Nothing to do; from 0.7.0 the gate reads no plan and none is committed. |
| `docs/plans/archive/` and the plans index are retired | The legacy directory is still in the tree | Delete it (`git rm -r`) or leave it; from 0.7.0 the gate reads nothing under `paths.plans`. |
| `paths.plans_archive` is gone from the descriptor | An unread key in `docs/.sdd.yaml` | Delete the line by hand. |
| The process-doc templates were rewritten | Your `docs/ai-workflow.md`, `docs/development-process.md`, and `AGENTS.md` still route delivery to a general engineering plugin and describe archive-and-index; the scaffold never overwrites a populated file | Move each file aside, run `/sdd-scaffold`, and merge your local tuning back; or paste § Orchestration, § Review, the lanes, and the PR-body close-out block from the plugin's `references/templates/`. |
| The PR body carries a `Lane:` line | `/sdd-review` falls back to `--lane`, and a maintenance PR has none | Add `Lane: full` or `Lane: maintenance — no normative change` to the body, from the close-out block in `docs/development-process.md`. |
| Review output is one ledger comment | A reviewer given the old prompt posts one comment per finding | Paste the block `/sdd-review --panel` prints; do not retype it. |
| `sdd-with-superpowers.md` is removed | Links to it or to `docs/superpowers/` break | Link the router skill's paragraph on the optional general engineering plugin instead. |

Tool grants in `agents/*.md` are Claude Code fields; on Cursor they are contracts the agent bodies state; see the Cursor section of [install.md](install.md#cursor).

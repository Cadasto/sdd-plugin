# sdd-check — the shared drift gate

`sdd-check` is the shared drift gate. It is one Python file, vendored into a repository by `/sdd-scaffold` and run by the `spec-check` build target, so CI needs no plugin. It checks the traceability chain in both directions, lints the prose rules that can be checked mechanically, regenerates the derived indexes, prints a requirement's context bundle, and tests itself.

Nothing installs an `sdd-check` executable. Throughout this document `sdd-check <cmd>` is shorthand for `python3 <check.script> <cmd> --root .`, where `<check.script>` is the vendored copy the descriptor names (`docs/.sdd.yaml` → `check.script`). A repository that has not vendored the gate runs `/sdd-scaffold --upgrade` before `check` — `check` run from the plugin's own copy fails the version pin, because that copy is not the one the descriptor pins. `generate` and `context` do not check the pin, so they may run from the plugin's copy.

## Commands

| Command | What it does |
|---|---|
| `check` | Run the families. This is the default when no command is given. |
| `generate [--verify]` | Rewrite every generated block, and the generated frontmatter lines, from the map. `--verify` reports what would change and writes nothing. |
| `context <REQ>` | Print one requirement's context bundle — the index row, the traceability record, the canonical spec section, and any open strands ([sdd-methodology.md](sdd-methodology.md) §10). |
| `selftest` | Run the tool against the fixtures it carries. |
| `--version` | Print the tool's own version. |

`--root DIR` is common to every command; it names the repository root (default: the working directory).
`--only fam[,fam]` applies to `check` only, and runs just the families listed. `check` also takes
`--changelog-all`, which extends the `changelog` family past `## [Unreleased]` to every section of the
changelog; `--verify` belongs to `generate` alone. Any of the three given to a command that does not take
it exits 2 with a message naming the flag and the command.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Ran; no errors. Warnings are allowed. |
| `1` | Ran; at least one error. |
| `2` | Could not configure itself, so nothing ran. |

Exit 2 has exactly four causes, and nothing else produces it:

1. **The descriptor** is missing, cannot be parsed, has the wrong shape, or names a path that is absolute
   or escapes the repository.
2. **The command line is invalid** — an unknown command or option, an unknown family in `--only`, or
   `--only`, `--verify` or `--changelog-all` given to a command that does not take it.
3. **`context` was given an identifier with no record.**
4. **A `check` run in which no family ran** — every family `off`, for instance, or `--only` naming an
   off family. The tool verified nothing, which is a configuration failure rather than a clean pass.

A command-line error prints one line naming the problem. For a descriptor failure the report is the first
line followed by `sdd-check: FAILED — <message>`, where the message names the file and the line, with no
finding lines and no family lines. `context` given an unknown identifier prints that one line only, not a
report. A run in which no family ran ends `sdd-check: FAILED — no family ran (<reasons>)` and never
prints `OK`.

A missing map, a map that cannot be parsed, and a map that yields no records are **not** exit 2. Each is a
`map-schema` error, so the run exits 1, and every family that needs records is listed under `skipped:`
with the reason `map unavailable`.

Exit 2 is a failure of the gate itself; CI treats it as red, never as skipped.

## Report format

One line per finding:

```
[<family>] <LEVEL> <anchor>: <message>
```

The anchor is `path:line`, or a `REQ` id when the finding is about a record rather than a place in a file.

The first line of a run states what ran against what:

```
sdd-check <version> · <root> · profile <p> · <n> REQ records
```

The last line is one of:

```
sdd-check: OK — <n> checks, 0 errors, <w> warnings
sdd-check: FAILED — <e> errors, <w> warnings
sdd-check: FAILED — no family ran (<reasons>)
```

`<n> checks` is the number of families that ran. The next line always names the families that ran and the
families that did not, each with its reason:

```
families run: …; skipped: <family> (<reason>)
```

The two lists are not a dichotomy: a family that only partly ran — `plans` when git is unavailable, for
instance — names in both, because part of it ran and part could not.

Every family some file waives adds a line `waived: <family> (<n> files)` straight after it, so a waiver
can never hide silently.

When `check.links.exclude` is non-empty, one more line follows, so an exclusion can never hide silently:

```
link exclusions: …
```

## Families

Thirteen families. Each one has a default severity, which a repository overrides per family in
`check.families` (`error` · `warn` · `off`). A family that is `off`, or that is left out by `--only`, is
skipped and named in the summary. Section numbers below are [sdd-methodology.md](sdd-methodology.md).

### descriptor

- `descriptor` — the descriptor parses; `req_style` is `area-prefixed | flat-numeric`; `req_areas` present and non-empty when area-prefixed, absent when flat-numeric; `excluded_areas` disjoint from `req_areas`; `paths.*` and `traceability` exist and match the profile's shape; `check.version` equals the tool's `__version__`; every `check.families` key is a known family and every value `error | warn | off`; `default_mode` valid; `doc_kinds` retains the four normative kinds (`requirement`, `specification`, `adr`, `plan`) — a repository may extend the list, never shrink it below them; `check.code_roots` and `check.test_globs` are lists of strings and every configured code root exists; `check.changelog.max_words` is an integer. Path containment is checked at load, for every command, before anything is read or written: a `paths.*`, `traceability` or `check.*` path that is absolute or climbs out of the repository fails the load with exit 2, naming the line of the offending key.

Default severity `error`. Enforces §5 (the identifier scheme and excluded areas) and §3 (the kind vocabulary).

### map-schema

- `map-schema` — the map parses and yields at least one record; ids unique; id matches the repository's style and, when area-prefixed, an area in `req_areas` and not in `excluded_areas`; `title`, `canonical`, `status`, `implementation` present; `status` and `implementation` in vocabulary; `canonical` is `path#anchor`; list fields are lists of strings; unknown keys warn.

Default severity `error`. Enforces §6 (the per-kind status vocabularies) and §8 (the traceability chain).

### map-to-tree

- `map-to-tree` — the canonical file exists and the anchor resolves to a heading slug (GitHub rule: lower-case, drop characters outside letters, digits, space, hyphen, underscore, spaces to hyphens, no collapsing) or to an explicit `<a id="…">`/`<a name="…">`; the section slice from that heading to the next heading of the same or higher level contains `**Implements:** … <id>` with an identifier-boundary match, or the section's heading itself names the identifier (identifier-boundary match); every `packages`, `tests`, `operations` path exists (`packages` may be a directory or a file; `tests` and `operations` must be files); every `probes` id resolves — a heading in `check.probes_catalogue` when set, otherwise the id appears in one of the record's `tests`; an enforced record carries at least one evidence entry.

Default severity `error`. Enforces §5 (the single canonical home), §6 (an "enforced" record carries evidence) and §8.

### index-sync

- `index-sync` — the requirements index (the `README.md` of `paths.requirements`, or the file itself under the lightweight profile) has a table whose rows carry `REQ` ids; the parse yields at least one row; an id that carries more than one row is an error; a table carrying ids whose header names no `Stability` or no `Implementation` column is a warning; every row id has a record and every record has a row; the row's stability and implementation cells (columns found by header text `Stability`/`Status` and `Implementation`/`Impl.`, else the last two columns; case-insensitive compare) equal the record; a requirement detail file (`<paths.requirements>/<id>*.md`, full profile) has frontmatter `status` and `implementation` equal to the record; a specification's frontmatter `requirements:` list, when present, equals the set of records whose canonical points into it (warn).

Default severity `error`. Enforces §5 (the index links and never duplicates) and §6 (the map owns both axes).

### plans

- `plans` — every file under `paths.plans` (not `_template.md`) has frontmatter `plan`, `implements`, `mode`, `status`; `plan` equals the filename stem; `status` in vocabulary; `mode` in vocabulary; every `implements` id that looks like a `REQ` has a record; `status: active` while every implemented record is `landed | shipped` and `mode` is `spec-first` → warn; `status: done` while an implemented record is not enforced → warn; `status: done | abandoned` and the plan's last commit is older than the newest tag → error `finished plan predates the latest release tag; run /sdd-finalize` (skipped with a note when there is no git, no tag, or the file is uncommitted).

Default severity `error`. Enforces §9 (finished in place, swept at the release) and §11 (a status line that lies).

### tree-to-map

- `tree-to-map` — under `check.code_roots` (default: the repository minus `docs/`, `.git/`, `vendor/`, `node_modules/`, every `paths.*`, the map at `traceability`, and the vendored gate at `check.script`, which is an artefact this repository carries rather than code it wrote), every token matching the repository's `REQ` pattern names a record (else error `unknown identifier cited`); a test file (a `check.test_globs` match) citing a `REQ` whose record lists no `tests` → warn. Files are those git tracks or does not ignore; without git, the whole tree. When roots are configured and none exists, the family is skipped with that reason and is not counted as run.

Default severity `warn`. Enforces §5 (a published id is never invented or reused) and §8 (the chain runs both ways).

### doc-kinds

- `doc-kinds` — every `*.md` under `docs/` (and under any `paths.*` outside it) has frontmatter opening on line 1 or right after a leading HTML comment block, with `kind:` in `doc_kinds` (missing or unknown → the family's severity); a normative kind's `status`/`state` value is in that kind's vocabulary (error); a `kind: upstream` document uses `state:` and not `status:` (error); an informative kind carrying `status:` → warn; a document that cannot be read or is not valid UTF-8 → error, never treated as empty. A document that declares no kind is treated, for the other families, as the kind its location implies — `paths.specifications` → specification, then `paths.requirements` → requirement (only that file when it names a file), `paths.adr` → adr, `paths.plans` → plan, otherwise guide — while `doc-kinds` still reports the missing declaration.

Default severity `warn`. Enforces §3 (the kinds and their zones) and §6 (the per-kind vocabularies).

### rfc2119

- `rfc2119` — a keyword is one of `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`, `REQUIRED`, `RECOMMENDED`, `MAY`, `OPTIONAL` as a whole upper-case word, outside fenced code, inline code, HTML comments and frontmatter. In a `specification` kind: a normative section (a heading containing `§`) with no keyword → warn; a lower-case modal (`must`, `shall`, `should`, `may not`) in a sentence with no keyword → warn; malformed forms `MUST to`, `are MUST`, `is MUST`, `MUST MUST`, `NOT NOT`, `SHOULD MUST` → error. Outside a specification: a keyword in a `requirement | adr | plan | reference` kind → error; in `guide | analysis | operations | upstream` → the family's severity; files with the waiver are skipped and counted.

Default severity `warn` — but the per-kind rules above still error for `requirement`, `adr`, `plan` and
`reference`, because a binding word in a document that binds nothing is a second source of truth.
Enforces §4 (keyword discipline) and §3 (the zones).

### one-home

- `one-home` — every keyword sentence in a specification kind, normalised (lower-case; markdown emphasis, code ticks and link syntax stripped; whitespace collapsed; trailing punctuation dropped; at least six words), appears once across all specification documents (error, both locations named); the same normalised sentence found in any non-specification document → error `duplicated normative prose`. Blockquoted lines (`>`) are notes and are not sentences for this family.

Default severity `error`. Enforces §5 (the single canonical home), §11 (duplicated normative prose) and
[artefact-prose.md](artefact-prose.md).

### links

- `links` — in every `*.md` under `docs/`, `AGENTS.md`, `README.md`, and any `paths.*` outside `docs/`: every inline link `](target)` and reference definition `[label]: target` whose target has no scheme (`http:`, `https:`, `mailto:`, `ftp:`, `tel:`, `data:`, `//`) resolves: a host-absolute path is an error; a relative path that walks outside the repository root (`../` past the top) is an error, distinct from a host-absolute path; the path exists relative to the file (error); and a `#fragment` on a `.md` target (or a bare `#fragment`) resolves to a heading slug or explicit anchor in that file (error). Fenced code, inline code and frontmatter are skipped. `check.links.exclude` globs are honoured and printed.

Default severity `error`. Enforces §8 — the chain is made of links, and a link that nothing resolves rots
silently.

### changelog

- `changelog` — under `## [Unreleased]` in `check.changelog.path` (and every section with `--changelog-all`): each top-level bullet has at most `max_words` words, one sentence (a `.`, `!` or `?` followed by a space and a capital letter counts as a second), no rationale connector (` because `, ` so that `, ` in order to `), and at most four backticked tokens (an inventory). A `check.changelog.path` that names no file is an error at any severity other than `off`.

Default severity `warn`. Enforces the changelog-bullet rule in [artefact-prose.md](artefact-prose.md).

### generated

- `generated` — every marker block in the tree equals what `generate` would write; an opening marker without a closing one is an error; a block name outside the three known names is an error; a near-miss marker — a line containing `sdd:generated` that is neither an exact opening marker nor an exact closer — and a closer with no opener are errors naming file and line. A marker indented four or more spaces is code, not a marker.

Default severity `error`. Enforces §5 — a derived index has one source, and a hand edit makes a second one.

### draft-reason

- `draft-reason` — a record that is `status: draft` and enforced carries `draft_reason` (default `off`).

Default severity `off`; a repository that wants it turns it on. Enforces §6 — `draft` is binding, so a
requirement that is built and still `draft` owes a reason.

## Waivers

A file is waived for one or more families by a comment anywhere in it — matched as text, not as markup, so
it still counts inside a fenced code block:

```markdown
<!-- sdd-check: allow <family>[, <family>] -->
```

Name more than one family comma-separated in the same comment. Never write a real family name into an
example of this syntax: the comment waives whatever file holds it, fenced or not, so a document
demonstrating the pattern with a real name waives itself for that family. Use the `<family>` placeholder
shown above, even in prose that walks through the syntax.

The waiver covers that file and only the families it names. Five families honour a waiver — `doc-kinds`,
`rfc2119`, `one-home`, `links` and `changelog`; a waiver naming any other family has no effect. Every
honoured waiver is counted in the summary, so a repository can see how many it carries and whether the
number is going down.

## Generated blocks

`generate` writes three blocks — `requirements-index`, `specifications-index` and `adr-index` — plus the
`status:` and `implementation:` frontmatter lines of every requirement detail file. Each block sits
between a pair of markers whose format is owned by [traceability-schema.md](traceability-schema.md) §4. A
block's links resolve relative to the file holding the block, not to the block's canonical home — the same
index wrapped into two different files links each row from where it actually sits. An opening marker with
no closing one, a closer with no opener, a near-miss marker, or a block name outside the three known names
is skipped rather than written; `generate` exits 1 and names each one by file, line and reason. A marker
pair quoted inside a fenced code block, or indented four or more spaces, is not a live block; it is
neither flagged nor rewritten.

### What a writing run refuses

`generate` never loses hand-written content silently. A run that would, writes nothing to any file and
names every refusal as a `refused — …` line; it exits 1. Capture what the refusal names, or move it, then
rerun.

- **Only errors block.** The map is validated write-free first. An ERROR-level map finding — an
  out-of-vocabulary or malformed record — aborts the run with nothing written. A WARN, such as an unknown
  record key, does not block the write, in `generate` as in `check`.
- **Rows are identified by what they refer to**, not by the raw text of their first cell. A requirements
  row is the `REQ` id found anywhere in its first cell, with backticks, asterisks and link markup
  ignored; a specifications row is the spec name in its first cell, or its link target's file stem,
  matched against the specification files `generate` would list; an ADR row is the `ADR` id in its first
  cell. A bare id, a `./`-linked id, a backticked name, or a differently-linked cell for a record or
  document that exists is therefore rewritten, not refused.
- **A row with nothing behind it is refused.** A requirements row whose id has no record is refused as
  `row <id> has no record in the map`; a specifications or ADR row with no matching document as
  `row <id> has no matching document`. Capture the record with `/sdd-specify`, or delete the stale row by
  hand. A row whose record exists is never refused, however its cell is formatted.
- **Non-row content inside the markers is protected.** The run refuses, naming the file and the line,
  when regeneration would remove a non-blank line that is not part of the table (a note, a blockquote, a
  bullet, a heading), a column the current header carries and the generated header does not, or a row
  whose id cell contains `<` or `>` other than a placeholder. Move that prose outside the markers, or
  record the column's content elsewhere, then rerun. A placeholder row — an id cell of the form `<…>`, as
  the 0.5.x templates carried — is not protected and is replaced.
- **A file that is not valid UTF-8 is refused**, by name, rather than rewritten; a leading byte-order mark
  is allowed and preserved. A rewrite keeps the file's dominant line ending.

If a write fails part-way, the run names every file it had already written and the one that failed.

A kind-less document under `paths.specifications` still becomes a row in the generated specifications
index: `generate` reads the kind the document's location implies, the same fallback `doc-kinds` reports
against elsewhere in this file — `doc-kinds` keeps warning about the missing declaration at its own
severity, but the row is not dropped while the warning stands.

### `--verify`

`generate --verify` compares and writes nothing. It prints a unified diff for each stale block and the
same `refused — …` lines a writing run would, and exits 1 when any block would change or any refusal
exists. When no generated block is found
anywhere it prints `sdd-check: no generated blocks found` and exits 0. The `generated` family makes the
same comparison during `check`, so a hand edit between the markers fails the gate.

## Vendoring and the version pin

`/sdd-scaffold` copies the tool into the repository at `check.script` — `scripts/sdd-check.py` by default —
and writes the tool's version into `check.version`. The `descriptor` family fails when the two disagree,
so a stale vendored copy cannot keep passing while the plugin has moved on.

The tool is one file, needs nothing beyond the Python standard library, and runs on Python 3.9 or newer.
CI runs the vendored copy through the `spec-check` build target, which is why a checkout with no plugin
installed gets exactly the gate a developer gets. Re-vendoring is a maintenance-lane change: copy the
file, set `check.version`, run the gate.

## Selftest

`sdd-check selftest` runs the tool against fixtures it carries itself. The bar is one clean baseline as the
positive control plus a negative fixture for each family; the per-rule coverage lives in `tools/tests/`.
The clean baseline proves the families accept clean input; each negative fixture proves a family actually
fails when the defect is there. A check that cannot fail is not a check.

## What a green run does not prove

A green run proves that the documents, the map and the tree agree, and that the prose rules a machine can
apply hold. It does not prove:

- **that the tests pass** — that is the build gate, `<build_entrypoint> <ci_target>`;
- **that the code conforms** to the `SPEC §` it cites — that is the conformance review (§13);
- **that the lane is right** — a change that altered a normative statement while claiming the maintenance
  lane is caught by review, not by the gate (§12).

The gate keeps the chain honest. It does not read the code.

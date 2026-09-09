# sdd-check — the shared drift gate

`sdd-check` is the shared drift gate. It is one Python file, vendored into a repository by `/sdd-scaffold` and run by the `spec-check` build target, so CI needs no plugin. It checks the traceability chain in both directions, lints the prose rules that can be checked mechanically, regenerates the derived indexes, prints a requirement's context bundle, and tests itself.

## Commands

| Command | What it does |
|---|---|
| `check` | Run the families. This is the default when no command is given. |
| `generate [--verify]` | Rewrite every generated block, and the generated frontmatter lines, from the map. `--verify` reports what would change and writes nothing. |
| `context <REQ>` | Print one requirement's context bundle — the index row, the traceability record, the canonical spec section, and any open strands ([sdd-methodology.md](sdd-methodology.md) §10). |
| `selftest` | Run the tool against the fixtures it carries. |
| `--version` | Print the tool's own version. |

Two options are common to every command: `--root DIR` names the repository root (default: the working
directory), and `--only fam[,fam]` runs just the families listed. `check` also takes `--changelog-all`,
which extends the `changelog` family past `## [Unreleased]` to every section of the changelog.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Ran; no errors. Warnings are allowed. |
| `1` | Ran; at least one error. |
| `2` | Could not configure itself, so nothing ran. |

Exit 2 has two causes and no others: the descriptor is missing or cannot be parsed, or the command line is
invalid — an unknown subcommand, or an unknown family in `--only`. The message names the file and the
line, or the bad argument.

When the tool exits 2 the report is the first line followed by `sdd-check: FAILED — <message>`, with no
finding lines and no family lines, because no family ran.

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
```

`<n> checks` is the number of families that ran. The next line always names the families that ran and the
families that did not, each with its reason:

```
families run: …; skipped: <family> (<reason>)
```

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

- `descriptor` — the descriptor parses; `req_style` is `area-prefixed | flat-numeric`; `req_areas` present and non-empty when area-prefixed, absent when flat-numeric; `excluded_areas` disjoint from `req_areas`; `paths.*` and `traceability` exist and match the profile's shape; `check.version` equals the tool's `__version__`; every `check.families` key is a known family and every value `error | warn | off`; `default_mode` valid.

Default severity `error`. Enforces §5 (the identifier scheme and excluded areas) and §3 (the kind vocabulary).

### map-schema

- `map-schema` — the map parses and yields at least one record; ids unique; id matches the repository's style and, when area-prefixed, an area in `req_areas` and not in `excluded_areas`; `title`, `canonical`, `status`, `implementation` present; `status` and `implementation` in vocabulary; `canonical` is `path#anchor`; list fields are lists of strings; unknown keys warn.

Default severity `error`. Enforces §6 (the per-kind status vocabularies) and §8 (the traceability chain).

### map-to-tree

- `map-to-tree` — the canonical file exists and the anchor resolves to a heading slug (GitHub rule: lower-case, drop characters outside letters, digits, space, hyphen, underscore, spaces to hyphens, no collapsing) or to an explicit `<a id="…">`/`<a name="…">`; the section slice from that heading to the next heading of the same or higher level contains `**Implements:** … <id>` with an identifier-boundary match, or the section's heading itself names the identifier (identifier-boundary match); every `packages`, `tests`, `operations` path exists (`packages` may be a directory or a file; `tests` and `operations` must be files); every `probes` id resolves — a heading in `check.probes_catalogue` when set, otherwise the id appears in one of the record's `tests`; an enforced record carries at least one evidence entry.

Default severity `error`. Enforces §5 (the single canonical home), §6 (an "enforced" record carries evidence) and §8.

### index-sync

- `index-sync` — the requirements index (the `README.md` of `paths.requirements`, or the file itself under the lightweight profile) has a table whose rows carry `REQ` ids; the parse yields at least one row; every row id has a record and every record has a row; the row's stability and implementation cells (columns found by header text `Stability`/`Status` and `Implementation`/`Impl.`, else the last two columns; case-insensitive compare) equal the record; a requirement detail file (`<paths.requirements>/<id>*.md`, full profile) has frontmatter `status` and `implementation` equal to the record; a specification's frontmatter `requirements:` list, when present, equals the set of records whose canonical points into it (warn).

Default severity `error`. Enforces §5 (the index links and never duplicates) and §6 (the map owns both axes).

### plans

- `plans` — every file under `paths.plans` (not `_template.md`) has frontmatter `plan`, `implements`, `mode`, `status`; `plan` equals the filename stem; `status` in vocabulary; `mode` in vocabulary; every `implements` id that looks like a `REQ` has a record; `status: active` while every implemented record is `landed | shipped` and `mode` is `spec-first` → warn; `status: done` while an implemented record is not enforced → warn; `status: done | abandoned` and the plan's last commit is older than the newest tag → error `finished plan predates the latest release tag; run /sdd-finalize` (skipped with a note when there is no git, no tag, or the file is uncommitted).

Default severity `error`. Enforces §9 (finished in place, swept at the release) and §11 (a status line that lies).

### tree-to-map

- `tree-to-map` — under `check.code_roots` (default: the repository minus `docs/`, `.git/`, `vendor/`, `node_modules/`, the descriptor's `paths.*`), every token matching the repository's `REQ` pattern names a record (else error `unknown identifier cited`); a test file (a `check.test_globs` match) citing a `REQ` whose record lists no `tests` → warn. Files are those git tracks or does not ignore; without git, the whole tree.

Default severity `warn`. Enforces §5 (a published id is never invented or reused) and §8 (the chain runs both ways).

### doc-kinds

- `doc-kinds` — every `*.md` under `docs/` (and under any `paths.*` outside it) has frontmatter opening on line 1 or right after a leading HTML comment block, with `kind:` in `doc_kinds` (missing or unknown → the family's severity); a normative kind's `status`/`state` value is in that kind's vocabulary (error); a `kind: upstream` document uses `state:` and not `status:` (error); an informative kind carrying `status:` → warn. A document that declares no kind is treated, for the other families, as the kind its location implies — `paths.requirements` → requirement, `paths.specifications` → specification, `paths.adr` → adr, `paths.plans` → plan, otherwise guide — while `doc-kinds` still reports the missing declaration.

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

- `links` — in every `*.md` under `docs/`, `AGENTS.md`, `README.md`, and any `paths.*` outside `docs/`: every inline link `](target)` and reference definition `[label]: target` whose target has no scheme (`http:`, `https:`, `mailto:`, `ftp:`, `tel:`, `data:`, `//`) resolves: the path exists relative to the file (error), a host-absolute path is an error, and a `#fragment` on a `.md` target (or a bare `#fragment`) resolves to a heading slug or explicit anchor in that file (error). Fenced code, inline code and frontmatter are skipped. `check.links.exclude` globs are honoured and printed.

Default severity `error`. Enforces §8 — the chain is made of links, and a link that nothing resolves rots
silently.

### changelog

- `changelog` — under `## [Unreleased]` in `check.changelog.path` (and every section with `--changelog-all`): each top-level bullet has at most `max_words` words, one sentence (a `.`, `!` or `?` followed by a space and a capital letter counts as a second), no rationale connector (` because `, ` so that `, ` in order to `), and at most four backticked tokens (an inventory).

Default severity `warn`. Enforces the changelog-bullet rule in [artefact-prose.md](artefact-prose.md).

### generated

- `generated` — every marker block in the tree equals what `generate` would write; an opening marker without a closing one is an error; a block name outside the three known names is an error.

Default severity `error`. Enforces §5 — a derived index has one source, and a hand edit makes a second one.

### draft-reason

- `draft-reason` — a record that is `status: draft` and enforced carries `draft_reason` (default `off`).

Default severity `off`; a repository that wants it turns it on. Enforces §6 — `draft` is binding, so a
requirement that is built and still `draft` owes a reason.

## Waivers

A file is waived for one or more families by a comment anywhere in it:

```markdown
<!-- sdd-check: allow <family>[, <family>] -->
```

For example:

```markdown
<!-- sdd-check: allow rfc2119, one-home -->
```

The waiver covers that file and only the families it names. Every waiver is counted in the summary, so a
repository can see how many it carries and whether the number is going down.

## Generated blocks

`generate` writes three blocks — `requirements-index`, `specifications-index` and `adr-index` — plus the
`status:` and `implementation:` frontmatter lines of every requirement detail file. Each block sits
between a pair of markers whose format is owned by [traceability-schema.md](traceability-schema.md) §4.

`generate --verify` compares and writes nothing; the `generated` family makes the same comparison during
`check`, so a hand edit between the markers fails the gate.

## Vendoring and the version pin

`/sdd-scaffold` copies the tool into the repository at `check.script` — `scripts/sdd-check.py` by default —
and writes the tool's version into `check.version`. The `descriptor` family fails when the two disagree,
so a stale vendored copy cannot keep passing while the plugin has moved on.

The tool is one file, needs nothing beyond the Python standard library, and runs on Python 3.9 or newer.
CI runs the vendored copy through the `spec-check` build target, which is why a checkout with no plugin
installed gets exactly the gate a developer gets. Re-vendoring is a maintenance-lane change: copy the
file, set `check.version`, run the gate.

## Selftest

`sdd-check selftest` runs the tool against fixtures it carries itself and reports pass or fail per rule.
The bar is: one positive control and one negative fixture per rule; a rule without a fixture is not
shipped. The positive control proves the rule accepts clean input; the negative fixture proves the rule
actually fails when the defect is there. A check that cannot fail is not a check.

## What a green run does not prove

A green run proves that the documents, the map and the tree agree, and that the prose rules a machine can
apply hold. It does not prove:

- **that the tests pass** — that is the build gate, `<build_entrypoint> <ci_target>`;
- **that the code conforms** to the `SPEC §` it cites — that is the conformance review (§13);
- **that the lane is right** — a change that altered a normative statement while claiming the maintenance
  lane is caught by review, not by the gate (§12).

The gate keeps the chain honest. It does not read the code.

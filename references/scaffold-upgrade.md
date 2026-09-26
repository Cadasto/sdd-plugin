# Scaffold upgrade: topping up an existing repository

`/sdd-scaffold --upgrade` brings a repository scaffolded by an earlier plugin version up to the current scaffold. It runs when `--upgrade` is given, and without the flag whenever `docs/.sdd.yaml` exists but has no `check:` block (a repository scaffolded before the gate existed). It keeps the fresh path's non-destructive contract: never touch a descriptor key that already exists or a document body that already has content, only add what is missing, and report exactly what changed so a maintainer can predict the run before starting it. The steps are ordered by dependency: the descriptor gains its `check:` block before anything writes into it. `<plugin-root>` and `<check.script>` mean what they mean in `skills/sdd-scaffold/SKILL.md`; `sdd-check <cmd>` is shorthand as `references/sdd-check.md` defines it.

## 1. Add missing descriptor keys

Compare `docs/.sdd.yaml` against the template's key set (`references/templates/sdd.yaml`) and add any key the repository is missing, with the template's default value: `excluded_areas`, `doc_kinds`, `default_mode`, the `check:` block (including `script`, default `scripts/sdd-check.py`, and `version`), the `hooks:` block, and the `agents:` block. Add missing keys inside an existing `check:` block too. Never edit a key that is already there, whatever its value.

## 2. Re-vendor and pin

Compare the plugin's tool version (`python3 <plugin-root>/tools/sdd-check.py --version`, or the `__version__` line when `python3` is unavailable) against `check.version`.

- Plugin's copy newer, or `check.script` missing: copy the plugin's copy over `check.script` (creating it and its parents if this repository never vendored one), `chmod +x`, and write the new version into `check.version`.
- The two agree: do nothing.
- Vendored copy newer than the plugin's: stop and say so rather than downgrading it.

The pin itself is owned by `references/sdd-check.md` § Vendoring and the version pin.

## 3. Add the starter changelog, if missing

When `check.changelog.path` (default `CHANGELOG.md`) does not exist, create it exactly as the fresh path's step 3c does. Never overwrite one that already has content.

## 4. Add missing `kind:` frontmatter

The scope is closed: exactly ten files. The six process documents the scaffold writes (`docs/development-process.md`, `docs/ai-workflow.md`, `docs/ci.md`, the three index READMEs) and the four `_template.md` stubs (`docs/requirements/_template.md`, `docs/specifications/_template.md`, `docs/adr/_template.md`, `docs/plans/_template.md`). For any of those ten whose frontmatter has no `kind:` line, add the line the current template uses for that file (`kind: requirement`/`specification`/`adr`/`plan` for the four stubs). When a file has no frontmatter block at all, add a `---` block on line 1 holding only that `kind:` line: a bare `kind:` line with no fences does not parse. Nothing wider: a hand-authored requirement, specification, ADR or plan is the maintainer's own content, and `--upgrade` never edits it or its body.

### 4b. Propose frontmatter for legacy-header plans

Scope: every file under `paths.plans` that is not `_template.md`, not a `README.md`, and not under the legacy archive `<paths.plans>/archive/` (the gate skips that directory and `/sdd-finalize` sweeps it), and whose frontmatter lacks any of `plan`, `implements`, `mode` or `status`. Typically that is a plan written with bold header lines (`**Status:**`, `**Covers:**`) before the plan contract (`references/traceability-schema.md` §3) existed. For each one, propose the missing keys, merged into the existing frontmatter block when there is one, and write nothing: step 4's closed scope forbids editing a hand-authored plan, so this is a diff the maintainer applies, like the build wiring at step 6.

- `kind: plan` and `plan: <filename stem>`.
- `implements:`: the identifiers on the `**Covers:**` line, else on an `**Implements:**` line. Leave a range such as `REQ-060..068` out of the list and name it in the report for the maintainer to expand. Mark each `REQ` id with no record in the map: it fails the `plans` family until `/sdd-specify` records it or it is dropped. With neither line, leave `implements:` blank and flag it.
- `mode: <default_mode>` from the descriptor, marked for review.
- `status:` mapped from the `**Status:**` line by the table in `references/traceability-schema.md` § Legacy `**Status:**` lines. Print every mapping; an unmapped word is left blank for the maintainer.

Never edit the body. When the repository's own `docs/plans/_template.md` still produces bold-header plans, name it too, so new plans stop arriving in the old form. Once applied, the frontmatter owns the plan's state; a repository whose own tooling reads the `**Status:**` line picks one owner, because two status lines can disagree. A plan converted to `status: done` whose last commit predates the newest tag is then reported by the `plans` family until `/sdd-finalize` sweeps it.

## 5. Add missing generated markers

For each of the three index READMEs that carries a hand-written table but no marker pair, wrap the existing table in the matching markers (`requirements-index`, `specifications-index` or `adr-index`; the marker format is owned by `references/traceability-schema.md` §4). Wrapping only adds the marker comments; it does not rewrite the table. A README with no table is skipped; one with two tables, or an opening marker and no close, is left alone and named in the report rather than guessed at.

## 6. Wire the build target

If the `spec_check_target` does not already run the vendored gate, propose the fresh path's step-5 recipe, so `<build_entrypoint> <spec_check_target>` and CI run it. This includes an older `spec-check` stub that runs something else or nothing. Do not silently rewrite an existing build file; propose the diff, and say in the report that CI does not run the gate until the maintainer applies it.

## 7. Regenerate

Run `sdd-check generate --verify` (when `python3` is unavailable, skip this step and say the regeneration could not run here). `--verify` writes nothing and exits 1 on any staleness, which is expected right after step 5 wrapped a table, so read the output, not the exit code (`references/sdd-check.md` § `--verify`).

- A `map-schema` error is not a refusal and does not block the real run (`references/sdd-check.md` § What a writing run refuses). Report each map finding for the maintainer to fix, for instance a withdrawn requirement takes `implementation: retired` with `status: deprecated` (`references/traceability-schema.md` § Record fields), and rerun this step once it is fixed.
- Act on each `refused — …` line as `references/sdd-check.md` § What a writing run refuses directs, then rerun this step.

When `--verify` prints no refusal, run the real `sdd-check generate`, then `sdd-check check`, and read its output.

## 8. Report

List:

- every descriptor key added, and whether the starter changelog was created;
- the re-vendor outcome (old → new version, or "already current");
- every `kind:` line added;
- every frontmatter block proposed at step 4b with its status mapping, and every word left unmapped, range left unexpanded, and `implements` id with no record;
- every README wrapped, and the build-target wiring proposed;
- every refusal `generate` printed (file, line or row id, and its cause, left in place), with its fix, noting that the block keeps failing the `generated` family until it is fixed and `--upgrade` runs again;
- the `generate`/`check` output for whatever ran.

Two `check` findings have a known cause worth naming:

- A `map-to-tree` or `links` error that a canonical anchor or fragment in an older specification resolves to nothing: that specification still carries the comment-only anchor used before 0.6.0, which `--upgrade` does not rewrite. The maintainer converts it by hand, as the plugin's `docs/upgrading.md` § From 0.5.x to 0.6.0, step 4 shows.
- Every specification listed as sectionless for the `rfc2119` section rule under the default `check.rfc2119.sections: section-sign`, in a repository that titles its specification sections by requirement id: suggest `requirement-id` (or `either`), and say that new warnings may follow from sections that carry no keyword.

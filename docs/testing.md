# Testing and validation

This is a pure-content repository — JSON manifests + Markdown components, with no build step or package manager. Testing means validating structure, then installing locally and exercising the components.

## Validation

- **Manifest / component validation** — `./scripts/validate.sh` (CI runs the underlying `python3 scripts/validate.py` directly on every PR): checks both `plugin.json` manifests, dual-host parity (name/version/description/author/license/repository/keywords agree), declared component paths, kebab-case names, hook-config JSON, SKILL.md / agent / command frontmatter (including `name` == directory/filename, and that agents declare a grant — `tools:` or `disallowedTools:` — never `allowed-tools:`), that every relative link and `.md` fragment resolves, that retired vocabulary hasn't crept back in, and that the vendored gate's `__version__`, the template's pinned `check.version`, and both manifests' `version` agree. The wrapper runs `scripts/validate.py`; if Python 3 isn't installed it prints a warning and skips (exit 0) rather than failing — install `python3` for the full local check, or rely on `claude plugin validate .` and CI. CI pins Python so the deep check always runs there.
- **Official validator** — `claude plugin validate .`: checks the manifest and component structure (no extra dependencies).
- **Gate tests** — `python3 -m unittest discover -s tools/tests -v` runs the vendored gate's own unit tests; `python3 tools/sdd-check.py selftest` runs it against the fixtures it carries and reports pass or fail per rule, one positive and one negative case each. CI runs both after the validator.
- **Structural review** — run the `plugin-dev:plugin-validator` agent after creating or modifying components.
- **Skill quality review** — run the `plugin-dev:skill-reviewer` agent: description-triggering quality, progressive disclosure, content structure.
- **Token cost** — `claude plugin details sdd` shows the inventory and projected token cost; keep skill/command metadata lean.

## Local triggering tests

Install from your working copy (see [install.md](install.md)), then exercise each component. The most thorough test is to **dogfood the plugin on a throwaway repo**:

- **Session-start hook** — open a repo containing `docs/.sdd.yaml`; one SDD context line should print (and the scaffold pointer in a repo with `docs/` but no SDD structure).
- **`spec-driven-development` router** — ask "what is SDD?" or "should I write a spec or a requirement?"; it should explain and route, not perform an artefact action.
- **`/sdd-scaffold`** — in an empty repo, run it and confirm the `docs/` tree, templates, `docs/.sdd.yaml`, and `AGENTS.md` appear; run it again and confirm it is idempotent (fills gaps, doesn't clobber).
- **`/sdd-specify`** — capture a REQ, write a SPEC §, record an ADR; confirm identifiers are assigned without collision, the traceability entry is written, and a doc-kind boundary violation (for example a file path in a requirement) is refused/flagged.
- **`/sdd-deliver`** — on a REQ whose spec is written, confirm it refuses to dispatch when a precondition is unmet (no spec, no acceptance criteria, no branch), writes the plan to `docs/plans/` on the branch, and opens a **draft** PR whose body carries the claim line.
- **`/sdd-trace`** — with a deliberately broken `canonical` link, confirm the drift is reported (report-only, no edits).
- **`/sdd-review`** — on a branch that implements a REQ, confirm it detects the lane, dispatches the SDD reviewers plus the repo's declared reviewers on the full lane, and writes **one numbered ledger** rather than one comment per finding.
- **`/sdd-review --panel`** — confirm it prints one prompt block per `review_panel` entry for the lane and posts nothing; `--post` is what writes the ledger comment.
- **`/sdd-triage`** — with findings sitting in more than one place on the PR, confirm it reads all three comment channels (the PR conversation, review comments, and inline code comments) before it fixes anything.
- **`/sdd-archive`** — confirm the plan's frontmatter flips to `status: done` **in place** — no `git mv`, no index edit — and that the `SPEC §` status, the `REQ` status, and `traceability.yaml` are set in the same commit.
- **`/sdd-finalize`** — with a `done` plan that `docs/**` still links to, confirm it refuses to delete that plan and names the inbound link; confirm it never touches an `active` or `postponed` plan.
- **Reviewer agents** — ask for a whole-repo audit (`sdd-traceability-auditor`), a single-doc review (`sdd-doc-reviewer`), and a code-vs-spec conformance check (`sdd-spec-conformance-reviewer`); confirm each returns ranked findings and none edits files or spawns sub-agents.
- **`sdd-implementer`** — dispatch it with a one-task brief; confirm it stays inside the files the brief names, returns an `En-route findings` section, and spawns no sub-agents.
- **`spec-edit-reminder` hook** — edit a file under `docs/specifications/`; confirm the one-line reminder prints.
- **`session-stop` hook** — leave uncommitted changes with no commit in the session and stop; confirm the one-shot nudge fires (Claude Code: `Stop` exits 2 with the reason on stderr; Cursor: a `stop` followup message) and that a second stop in the same session passes silently. Confirm a session that made a commit is never nudged, and that `hooks.stop_nudge: false` in `docs/.sdd.yaml` opts the repository out.
- **`sdd-check generate --verify`** — after adding or amending a traceability record, run it; confirm it reports what would change in the generated blocks and the requirement frontmatter without writing anything, then run `sdd-check generate` (no flag) and confirm the reported changes land.
- **Cursor rule** — in Cursor, open a file under `docs/` and confirm `sdd-context.mdc` attaches.
- **Cursor smoke** — install the branch as a Cursor plugin; dispatch `sdd-implementer` with a one-task brief and confirm it spawns no subagent (a stated contract there, not a grant); run `/sdd-deliver` far enough to write a plan, and confirm it fails loud rather than silently when `gh` is missing.

After editing content, reinstall (or restart the session) to pick up changes.

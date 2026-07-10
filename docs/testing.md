# Testing and Validation

This is a pure-content repository — JSON manifests + Markdown components. There is no build step or package manager. Testing means validating structure, then installing locally and exercising the components.

## Validation

- **Manifest / component validation** — `./scripts/validate.sh` (also run by CI on every PR): checks both `plugin.json` manifests, dual-host parity (name/version/description/author agree), declared component paths, kebab-case names, hook-config JSON, and SKILL.md / agent / command frontmatter (including `name` == directory/filename, and that agents declare `tools:` not `allowed-tools:`). The wrapper runs `scripts/validate.py`; if Python 3 isn't installed it prints a warning and skips (exit 0) rather than failing — install `python3` for the full local check, or rely on `claude plugin validate .` and CI. CI pins Python so the deep check always runs there.
- **Official validator** — `claude plugin validate .`: checks the manifest and component structure (no extra dependencies).
- **Structural review** — run the `plugin-dev:plugin-validator` agent after creating or modifying components.
- **Skill quality review** — run the `plugin-dev:skill-reviewer` agent: description-triggering quality, progressive disclosure, content structure.
- **Token cost** — `claude plugin details sdd` shows the inventory and projected token cost; keep skill/command metadata lean.

## Local triggering tests

Install from your working copy (see [install.md](install.md)), then exercise each component. The most thorough test is to **dogfood the plugin on a throwaway repo**:

- **Session-start hook** — open a repo containing `docs/.sdd.yaml`; one SDD context line should print (and the scaffold pointer in a repo with `docs/` but no SDD structure).
- **`spec-driven-development` router** — ask "what is SDD?" or "should I write a spec or a requirement?"; it should explain and route, not perform an artefact action.
- **`/sdd-scaffold`** — in an empty repo, run it and confirm the `docs/` tree, templates, `docs/.sdd.yaml`, and `AGENTS.md` appear; run it again and confirm it is idempotent (fills gaps, doesn't clobber).
- **`/sdd-specify`** — capture a REQ, write a SPEC §, record an ADR; confirm identifiers are assigned without collision, the traceability entry is written, and a doc-kind boundary violation (e.g. a file path in a requirement) is refused/flagged. (Planning and building are then handed to the superpowers loop — confirm the router points there and that a plan lands in `docs/plans/`, not `docs/superpowers/plans/`.)
- **`/sdd-trace`** — with a deliberately broken `canonical` link, confirm the drift is reported (read-only, no edits).
- **`/sdd-review`** — on a branch that implements a REQ, confirm it dispatches the traceability auditor + spec-conformance reviewer (and the installed generic reviewer if present), consolidates findings, and — with `--post` — posts them to the PR; without `--post`, presents them in-session. It should *delegate* generic review, not hand-roll one.
- **`/sdd-archive`** — confirm a finished plan moves to `plans/archive/` via `git mv` and the indexes update, and that it is done as the final commit of the implementing branch (same PR), not a follow-up.
- **Agents** — ask for a whole-repo audit (`sdd-traceability-auditor`), a single-doc review (`sdd-doc-reviewer`), and a code-vs-spec conformance check (`sdd-spec-conformance-reviewer`); confirm each returns ranked findings and none edits files or spawns sub-agents.
- **`spec-edit-reminder` hook** — edit a file under `docs/specifications/`; confirm the one-line reminder prints.
- **Cursor rule** — in Cursor, open a file under `docs/` and confirm `sdd-context.mdc` attaches.

After editing content, reinstall (or restart the session) to pick up changes.

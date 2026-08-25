# Skill, agent, and rule authoring conventions

The detailed companion to [AGENTS.md](../AGENTS.md) (which is authoritative); this expands on the *how*. The shipped components are the reference examples.

## Naming & layout

- **Components are kebab-case** and namespaced `<plugin>:<component>` (for example `sdd:sdd-specify`). A component's frontmatter `name` MUST equal its directory (skills) or filename stem (agents); `scripts/validate.py` enforces this.
- `skills/<name>/SKILL.md` (includes user-invoked slash commands) · `agents/<name>.md` · `rules/<name>.mdc`. Shared reference material (the methodology, the schemas, the scaffold templates) lives in top-level `references/`. The legacy `commands/<name>.md` layout is not used.
- Skill/command prefix is `sdd-`; the awareness skill is `spec-driven-development` (kept distinct from the plugin name `sdd` to avoid a `sdd:sdd` collision).

## Skill vs agent vs rule

- **Skill (auto-invoked router)** — `spec-driven-development`: always-on `description` only, routes intent. Keep its body lean.
- **Skill (loop/lifecycle)** — `sdd-*`: each owns one stage or one artefact lifecycle. They carry `argument-hint` + `allowed-tools` so they are both auto-invoked on intent and user-invocable as `/sdd-*`. Bodies are imperative, checklist-driven, and cite `references/` rather than restating rules.
- **Agent** — a context-isolated, **report-only** specialist (`sdd-traceability-auditor`, `sdd-doc-reviewer`, `sdd-spec-conformance-reviewer`). Use **`tools:`** (a YAML block list), **never** `allowed-tools:` — in an agent that key is silently ignored and the agent inherits *all* tools. Write the `description` in the **prose-summary** form — conditions + 2–4 named trigger scenarios + a "See *When to invoke* in the agent body" pointer — and put the worked scenarios in a `When to invoke` body section (not an `<example>` block in the frontmatter). The body is the agent's **system prompt**: open it in second person ("You are a report-only specialist that…"), then continue imperatively. Call an agent **read-only** only when its grant genuinely is — `Bash` writes (`sed -i`, a redirect), so an agent holding it is report-only, and its body should say that no-edit is a contract it keeps rather than a sandbox.
- **Cursor rule** — a Cursor-only `.mdc` with `description` / `globs` / `alwaysApply` mirroring the router. See `rules/sdd-context.mdc`.

## The `description` (the trigger)

For skills the `description` is always-on metadata: keep it lean, third person — *what + scope*, 3–5 representative triggers ("This skill should be used when…"), and a short "Not for …" anti-trigger that disambiguates it from the neighbouring skills (for example `sdd-specify` vs `sdd-trace`) **and from superpowers** (for example defer planning/TDD/verification to superpowers, not a competing `sdd-*` skill).

**YAML gotcha:** a `description` value with an unquoted `: ` (colon-space) makes a real YAML parser read it as a nested mapping, so the component loads with *empty* metadata (every field silently dropped). `claude plugin validate` catches this, and `scripts/validate.py` guards against it too. Reword or quote the value.

## Body

- **Cite the methodology; don't re-derive it.** The single source of truth for the rules is `references/sdd-methodology.md` (and `references/traceability-schema.md` for the machine-readable formats). A skill body states *its* procedure and points at the canonical reference for the *why* — this keeps skills lean and the rules in one place.
- **Operate on Markdown, not source code.** The skills read/write docs, the requirements index, the traceability map, and `AGENTS.md` — none of them writes source code (building is superpowers' job). They are language-agnostic by construction and **read `docs/.sdd.yaml` first** rather than hard-coding paths or identifier styles.
- **Enforce boundaries; don't invent rules.** A skill keeps document kinds separate, identifiers stable, and the chain intact. It never adds a normative rule that isn't already in a spec.
- **Verification is part of the skill.** A skill that lands an artefact runs (or instructs the agent to run) the relevant gate before claiming done.

## Public-safety constraint

This repo may be published. Author all content as **general-purpose, language-agnostic SDD tooling**. Do **not** name specific internal/consumer repositories, reproduce absolute filesystem paths, or embed organisation-private project details. Ground claims in the public methodology lineage (Spec Kit, Kiro, the Thoughtworks rigour ladder, RFC-2119) — see the Sources section of `references/sdd-methodology.md`.

## Dual-host parity

Skills, agents, and rules are shared by both hosts. The **Cursor** manifest (`.cursor-plugin/plugin.json`) declares each component path; **Claude** discovers the default folders automatically. Keep the two manifests' `name`/`version`/`description`/`author` identical (`scripts/validate.py` checks parity), and the Cursor hook commands **workspace-relative** (`bash hooks/session-start.sh`), never `${CLAUDE_PLUGIN_ROOT}` (a Claude-Code-only variable).

## Before committing

Run `./scripts/validate.sh` and `claude plugin validate .`, then test triggering locally — see [testing.md](testing.md). When adding or renaming a component, sync **AGENTS.md**, **README.md**, **CHANGELOG.md**, and the `/sdd-*` list in **`hooks/session-start.sh`** in lockstep.

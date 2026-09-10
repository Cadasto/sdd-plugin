#!/usr/bin/env python3
"""Validate this plugin's manifests and skill/agent/command frontmatter.

This is a single-plugin repository (the plugin lives at the repo root), supporting
both Claude Code (``.claude-plugin/plugin.json``) and Cursor (``.cursor-plugin/plugin.json``).
Checks:
  * both manifests parse as JSON and carry the required fields;
  * dual-host parity (name/version/description/author/license/repository/keywords agree across manifests);
  * every component path declared in a manifest exists inside the plugin dir;
  * kebab-case directory/file names for skills, agents, commands, and rules;
  * hook-config JSON validity when present;
  * SKILL.md / agent / command frontmatter — required keys, and ``name`` matching the
    directory/filename. Agents MUST declare a grant — ``tools:`` (allowlist) or
    ``disallowedTools:`` (denylist) — and never ``allowed-tools:``, which Claude Code
    silently ignores so the agent inherits *all* tools (both flagged as errors);
  * every relative link in a ``*.md`` file resolves, and a ``#fragment`` on a ``.md`` target
    resolves to a heading slug or an explicit anchor (``references/templates/`` excluded —
    its links resolve once ``sdd-scaffold`` copies it into a consuming repo, not from here);
  * retired vocabulary does not reappear outside ``CHANGELOG.md`` and ``docs/upgrading.md``;
  * the vendored gate's version, the template's pinned ``check.version``, and both manifests'
    ``version`` agree, and the gate script is executable.

This plugin has no MCP backend, so there is intentionally no ``.mcp.json`` check.

Dependency-free (stdlib only) so the ``scripts/validate.sh`` soft-skip is the *only*
reason it wouldn't run. Usage: python3 scripts/validate.py   (from the repo root)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

PLUGIN_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Component-path fields a manifest may declare (Cursor lists them explicitly). No
# `mcpServers` — this plugin bundles no MCP server.
MANIFEST_PATH_FIELDS = ("logo", "rules", "skills", "agents", "commands", "hooks")
# Fields that must agree across the Claude and Cursor manifests.
SYNCED_FIELDS = ("name", "version", "description", "author", "license", "repository", "keywords")


def err(msg):
    errors.append(msg)


def load_json(path: Path, label: str):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        err(f"{path.relative_to(ROOT)}: cannot parse JSON ({label}): {e}")
        return None


def check_kebab(name: str, label: str):
    if not KEBAB_RE.match(name):
        err(f"{label}: name '{name}' is not kebab-case")


def check_frontmatter_scalars(front: str, rel: str):
    """Stdlib-only guard for the most common frontmatter YAML breakage: an unquoted scalar
    value containing a ': ' (colon-space) or ' #', which a real YAML parser reads as a nested
    mapping / comment — so at runtime the component loads with EMPTY metadata (every field
    silently dropped). This is NOT a full YAML parser (`claude plugin validate` does that); it
    exists because CI runs only this Python validator, so this class of error must fail here too."""
    for line in front.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s(.+)$", line)
        if not m:
            continue
        value = m.group(2).strip()
        if value[:1] in ('"', "'", "[", "{", "|", ">", "&", "*", "#"):
            continue  # quoted or structured — trust the author / real parser
        if ": " in value:
            err(f"{rel}: frontmatter '{m.group(1)}' has an unquoted ': ' in its value — "
                f"quote the value or YAML parses it as a nested mapping (metadata silently dropped)")
        if " #" in value:
            err(f"{rel}: frontmatter '{m.group(1)}' has an unquoted ' #' in its value — quote the value")


def validate_skills():
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(d for d in skills_dir.iterdir() if d.is_dir()):
        check_kebab(skill_dir.name, f"skills/{skill_dir.name}")
        skill_md = skill_dir / "SKILL.md"
        rel = skill_md.relative_to(ROOT)
        if not skill_md.is_file():
            err(f"{rel}: missing SKILL.md")
            continue
        m = re.match(r"\A---\n(.*?)\n---\n", skill_md.read_text(), re.DOTALL)
        if not m:
            err(f"{rel}: missing YAML frontmatter")
            continue
        front = m.group(1)
        check_frontmatter_scalars(front, str(rel))
        for field in ("name", "description"):
            if not re.search(rf"^{field}:", front, re.MULTILINE):
                err(f"{rel}: frontmatter missing '{field}'")
        fm_name = re.search(r"^name:\s*(\S+)", front, re.MULTILINE)
        if fm_name and fm_name.group(1) != skill_dir.name:
            err(f"{rel}: frontmatter name '{fm_name.group(1)}' != directory '{skill_dir.name}'")


def validate_md_components(subdir: str, *, require_name: bool, is_agent: bool = False):
    """Validate flat .md components (agents/, commands/): kebab-case filename, frontmatter
    present with the required fields, and any `name` matching the filename stem. Non-recursive,
    so nested material is intentionally skipped (shared command references live in top-level
    references/). Agents are additionally checked for a declared grant and the `allowed-tools:` foot-gun."""
    comp_dir = ROOT / subdir
    if not comp_dir.is_dir():
        return
    for md in sorted(comp_dir.glob("*.md")):
        rel = md.relative_to(ROOT)
        check_kebab(md.stem, str(rel))
        m = re.match(r"\A---\n(.*?)\n---\n", md.read_text(), re.DOTALL)
        if not m:
            err(f"{rel}: missing YAML frontmatter")
            continue
        front = m.group(1)
        check_frontmatter_scalars(front, str(rel))
        for field in (("name", "description") if require_name else ("description",)):
            if not re.search(rf"^{field}:", front, re.MULTILINE):
                err(f"{rel}: frontmatter missing '{field}'")
        fm_name = re.search(r"^name:\s*(\S+)", front, re.MULTILINE)
        if fm_name and fm_name.group(1) != md.stem:
            err(f"{rel}: frontmatter name '{fm_name.group(1)}' != filename '{md.stem}'")
        if is_agent and re.search(r"^allowed-tools:", front, re.MULTILINE):
            err(f"{rel}: agents declare a grant with 'tools:' or 'disallowedTools:', never "
                f"'allowed-tools:' (it is silently ignored, so the agent inherits ALL tools)")
        if is_agent and not re.search(r"^(tools|disallowedTools):", front, re.MULTILINE):
            err(f"{rel}: agents must declare a tool grant — 'tools:' (allowlist) or "
                f"'disallowedTools:' (denylist); with neither, the grant is implicit")


def validate_rules():
    """Cursor rule files (rules/*.mdc): kebab-case filename plus a `description` in
    frontmatter. Rules carry their own frontmatter contract (description/alwaysApply/globs)."""
    rules_dir = ROOT / "rules"
    if not rules_dir.is_dir():
        return
    for rule in sorted(rules_dir.glob("*.mdc")):
        rel = rule.relative_to(ROOT)
        check_kebab(rule.stem, str(rel))
        m = re.match(r"\A---\n(.*?)\n---\n", rule.read_text(), re.DOTALL)
        if not m:
            err(f"{rel}: missing YAML frontmatter")
            continue
        check_frontmatter_scalars(m.group(1), str(rel))
        if not re.search(r"^description:", m.group(1), re.MULTILINE):
            err(f"{rel}: frontmatter missing 'description'")


def validate_manifest_paths(manifest: dict, label: str):
    for field in MANIFEST_PATH_FIELDS:
        value = manifest.get(field)
        if value is None:
            continue
        paths = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for path_value in paths:
            if not isinstance(path_value, str) or path_value.startswith(("http://", "https://")):
                continue
            resolved = (ROOT / path_value).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                err(f"{label}: {field} path '{path_value}' escapes the plugin directory")
                continue
            if not resolved.exists():
                err(f"{label}: {field} references missing path '{path_value}'")


def validate_json_file(path: Path, label: str):
    if path.is_file():
        load_json(path, label)


def validate_hook_scripts():
    """Every shell script under hooks/ must be executable: both hook configs invoke them by path,
    and a script without the execute bit fails silently at session start."""
    for sh in sorted((ROOT / "hooks").glob("*.sh")):
        if not sh.stat().st_mode & 0o111:
            err(f"{sh.relative_to(ROOT)}: hook script is not executable (chmod +x)")


# Directories the link and retired-vocabulary scans below skip: version control internals, this
# plan's own gitignored working area, a JS-tooling convention this repo doesn't use, and compiled
# Python caches (never text, never worth opening).
SCAN_EXCLUDE_DIR_NAMES = {".git", ".superpowers", "node_modules", "__pycache__"}

# references/templates/ holds documents `sdd-scaffold` copies into a consuming repo's docs/ tree;
# their relative links resolve from THAT destination, not from where this repository stores the
# template — e.g. `ai-workflow.md` links `../AGENTS.md`, correct once scaffolded to
# `docs/ai-workflow.md`, dead here. The templates' own links are covered by the gate's own
# `links` family once scaffolded, so this validator skips the directory instead of mis-flagging it.
TEMPLATES_DIR = ROOT / "references" / "templates"

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(?:#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
ANCHOR_RE = re.compile(r'<a\s[^>]*(?:id|name)="([^"]+)"', re.IGNORECASE)


def _scanned_files(pattern):
    """Every file under ROOT matching `pattern`, skipping SCAN_EXCLUDE_DIR_NAMES."""
    for p in sorted(ROOT.rglob(pattern)):
        if not p.is_file():
            continue
        if set(p.relative_to(ROOT).parts) & SCAN_EXCLUDE_DIR_NAMES:
            continue
        yield p


def _github_slug(heading: str) -> str:
    """The GitHub heading-anchor rule this project documents in references/sdd-check.md: lower-
    case; drop characters outside letters, digits, space, hyphen, underscore; spaces to hyphens;
    no run-collapsing (kept local — the tool that also implements this is a vendorable artefact,
    not something this validator imports)."""
    heading = heading.strip().lower()
    heading = re.sub(r"[^a-z0-9 \-_]", "", heading)
    return heading.replace(" ", "-")


def _anchors_in(path: Path):
    """Heading slugs and explicit `<a id=…>` / `<a name=…>` anchors available as link targets
    inside one Markdown file."""
    try:
        text = path.read_text()
    except OSError:
        return None
    slugs = {_github_slug(m.group(1)) for m in HEADING_RE.finditer(text)}
    slugs.update(m.group(1) for m in ANCHOR_RE.finditer(text))
    return slugs


def validate_links():
    """Every relative link target in a `*.md` file must exist; a `#fragment` on a `.md` target
    must resolve to a heading slug or an explicit anchor in that file. Fenced and inline code are
    skipped so a code sample's literal `[...]( ...)` text is never mistaken for a real link;
    external (http(s)/mailto/tel) links are out of scope. references/templates/ is excluded —
    see TEMPLATES_DIR above for why."""
    anchor_cache = {}

    for md in _scanned_files("*.md"):
        if TEMPLATES_DIR in md.parents:
            continue
        rel = md.relative_to(ROOT)
        text = INLINE_CODE_RE.sub("", FENCE_RE.sub("", md.read_text()))
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            # Drop an optional `"title"` after the URL, and unwrap `<...>`.
            target = re.split(r'\s+["\']', target, maxsplit=1)[0].strip().strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            path_part, _, frag = target.partition("#")
            dest = md if path_part == "" else (md.parent / path_part).resolve()
            try:
                dest_label = dest.relative_to(ROOT)
            except ValueError:
                dest_label = dest
            if not dest.exists():
                err(f"{rel}: link target '{target}' does not exist (resolves to {dest_label})")
                continue
            if frag and dest.suffix == ".md":
                if dest not in anchor_cache:
                    anchor_cache[dest] = _anchors_in(dest)
                slugs = anchor_cache[dest]
                if slugs is not None and frag not in slugs:
                    err(f"{rel}: link '{target}' — fragment '#{frag}' matches no heading or "
                        f"anchor in {dest_label}")


# Vocabulary the lean redesign retired. A past rename is legitimately still named in the
# changelog and the upgrading guide; anywhere else it is a document that never got updated.
RETIRED_TERMS = (
    "plans_archive",
    "sdd-with-superpowers",
    "docs/superpowers/",
    "Definition of Ready",
    "Definition of Done",
    "allowed-tools:",
    "not yet enforced",
)
# CHANGELOG.md and docs/upgrading.md legitimately name a past rename. This script itself is the
# third, necessary exemption: RETIRED_TERMS above must hold the literal strings it searches for.
RETIRED_VOCAB_EXEMPT_FILES = {"CHANGELOG.md", "docs/upgrading.md", "scripts/validate.py"}


def validate_retired_vocabulary():
    """None of RETIRED_TERMS may appear outside CHANGELOG.md / docs/upgrading.md. `allowed-tools:`
    is scoped to agents/ — that is where it is a foot-gun, and validate_md_components() already
    flags it there; this repeats the term list for one shared exemption rule, not the check."""
    for path in _scanned_files("*"):
        rel = str(path.relative_to(ROOT))
        if rel in RETIRED_VOCAB_EXEMPT_FILES:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for term in RETIRED_TERMS:
            if term == "allowed-tools:" and not rel.startswith("agents/"):
                continue
            if term in text:
                err(f"{rel}: retired term {term!r} — see docs/upgrading.md")


def validate_tool_version(manifests):
    """The vendored gate's own __version__, the template's pinned check.version, and both
    manifests' version must all agree — drift here means the wrong gate ships with the plugin.
    Read as text, never imported: tools/sdd-check.py is a vendorable artefact."""
    versions = {}

    tool_path = ROOT / "tools" / "sdd-check.py"
    if tool_path.is_file():
        m = re.search(r'^__version__\s*=\s*"([^"]+)"', tool_path.read_text(), re.MULTILINE)
        if m:
            versions["tools/sdd-check.py"] = m.group(1)
        else:
            err("tools/sdd-check.py: no __version__ = \"...\" assignment found")
        if not tool_path.stat().st_mode & 0o111:
            err("tools/sdd-check.py: not executable (chmod +x)")
    else:
        err("missing tools/sdd-check.py")

    template_path = ROOT / "references" / "templates" / "sdd.yaml"
    if template_path.is_file():
        m = re.search(r'^\s*version:\s*"([^"]+)"', template_path.read_text(), re.MULTILINE)
        if m:
            versions["references/templates/sdd.yaml (check.version)"] = m.group(1)
        else:
            err("references/templates/sdd.yaml: no check.version found")
    else:
        err("missing references/templates/sdd.yaml")

    for subdir in (".claude-plugin", ".cursor-plugin"):
        data = manifests.get(subdir)
        if data and data.get("version"):
            versions[f"{subdir}/plugin.json (version)"] = data["version"]

    if len(set(versions.values())) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in versions.items())
        err(f"version disagreement across the gate, the template pin, and the manifests: {detail}")


def main():
    manifests = {}
    for subdir, label in ((".claude-plugin", "Claude manifest"), (".cursor-plugin", "Cursor manifest")):
        manifest_path = ROOT / subdir / "plugin.json"
        if not manifest_path.is_file():
            err(f"missing {manifest_path.relative_to(ROOT)}")
            continue
        data = load_json(manifest_path, label)
        if data is None:
            continue
        manifests[subdir] = data

        name = data.get("name")
        if not name or not PLUGIN_NAME_RE.match(name):
            err(f"{label}: 'name' must be lowercase alphanumerics, hyphens, and periods")
        for field in ("name", "version", "description"):
            if not data.get(field):
                err(f"{label}: required field '{field}' is missing or empty")
        validate_manifest_paths(data, label)

    # Cross-manifest agreement (dual-host parity).
    if len(manifests) == 2:
        claude, cursor = manifests[".claude-plugin"], manifests[".cursor-plugin"]
        for field in SYNCED_FIELDS:
            if claude.get(field) != cursor.get(field):
                err(f"manifests disagree on '{field}': "
                    f"claude={claude.get(field)!r} cursor={cursor.get(field)!r}")

    # Hook configs must be valid JSON when present.
    validate_json_file(ROOT / "hooks" / "hooks.json", "Claude hooks")
    validate_json_file(ROOT / "hooks" / "cursor-hooks.json", "Cursor hooks")
    validate_hook_scripts()

    validate_skills()
    validate_md_components("agents", require_name=True, is_agent=True)
    validate_md_components("commands", require_name=False)
    validate_rules()

    validate_links()
    validate_retired_vocabulary()
    validate_tool_version(manifests)


if __name__ == "__main__":
    main()
    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("OK: manifests, dual-host parity, component paths, kebab-case names, "
          "hook configs and scripts, skills, agents, commands, rules, links, "
          "retired vocabulary, and tool/template/manifest version agreement are valid")

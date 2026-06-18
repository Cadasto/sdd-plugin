#!/usr/bin/env python3
"""Validate this plugin's manifests and skill/agent/command frontmatter.

This is a single-plugin repository (the plugin lives at the repo root), supporting
both Claude Code (``.claude-plugin/plugin.json``) and Cursor (``.cursor-plugin/plugin.json``).
Checks:
  * both manifests parse as JSON and carry the required fields;
  * dual-host parity (name/version/description/author agree across manifests);
  * every component path declared in a manifest exists inside the plugin dir;
  * kebab-case directory/file names for skills, agents, commands, and rules;
  * hook-config JSON validity when present;
  * SKILL.md / agent / command frontmatter — required keys, and ``name`` matching the
    directory/filename. Agents MUST declare ``tools:`` (never ``allowed-tools:``, which
    Claude Code silently ignores so the agent inherits *all* tools — flagged as an error).

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
SYNCED_FIELDS = ("name", "version", "description", "author")


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
    references/). Agents are additionally checked for the `allowed-tools:` foot-gun."""
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
            err(f"{rel}: agents must declare 'tools:' not 'allowed-tools:' "
                f"('allowed-tools:' is silently ignored, so the agent inherits ALL tools)")


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

    validate_skills()
    validate_md_components("agents", require_name=True, is_agent=True)
    validate_md_components("commands", require_name=False)
    validate_rules()


if __name__ == "__main__":
    main()
    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("OK: manifests, dual-host parity, component paths, kebab-case names, "
          "hook configs, skills, agents, commands, and rules are valid")

"""Unit tests for tools/sdd-check.py.

The tool is a script, not a package, so it is loaded by path. Every test that needs a
repository calls ``sdd_check.write_baseline(tmp)`` — the minimal passing repository the
tool carries — and mutates its own copy.
"""
import importlib.util
import io
import contextlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("sdd_check", TOOLS_DIR / "sdd-check.py")
sdd_check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sdd_check)


def yaml_blocks(text):
    """Every ```yaml fenced block in a markdown document, in order."""
    blocks, current, inside = [], [], False
    for line in text.split("\n"):
        if not inside and line.strip() == "```yaml":
            inside, current = True, []
        elif inside and line.strip() == "```":
            blocks.append("\n".join(current))
            inside = False
        elif inside:
            current.append(line)
    return blocks


class BaselineCase(unittest.TestCase):
    """A fresh baseline repository per test."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        sdd_check.write_baseline(self.tmp)

    # --- fixture helpers -------------------------------------------------
    def edit(self, rel, old, new):
        path = self.tmp / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, "fixture drift: %r not in %s" % (old, rel))
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write(self, rel, text):
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # --- run helpers -----------------------------------------------------
    def run_only(self, family):
        return sdd_check.run_check(self.tmp, only=[family], changelog_all=False)

    def levelled(self, report, level):
        return [f for f in report.findings if f.level == level]

    def assert_finding(self, report, fragment, level="ERROR", family=None):
        hits = [
            f
            for f in self.levelled(report, level)
            if fragment in f.message and (family is None or f.family == family)
        ]
        self.assertTrue(
            hits,
            "no %s finding containing %r\n%s" % (level, fragment, report.render(self.tmp)),
        )
        return hits[0]

    def assert_clean(self, report):
        loud = [f for f in report.findings if f.level in ("ERROR", "WARN")]
        self.assertEqual([], loud, report.render(self.tmp))


class TestBaseline(BaselineCase):
    def test_baseline_fixture_is_clean(self):
        root = self.tmp
        report = sdd_check.run_check(root, only=None, changelog_all=False)
        self.assertEqual(
            [], [f for f in report.findings if f.level in ("ERROR", "WARN")], report.render(root)
        )
        self.assertEqual(0, report.exit_code())


# ---------------------------------------------------------------------------
# YAML subset parser
# ---------------------------------------------------------------------------
class TestYamlSubset(unittest.TestCase):
    def test_block_mapping_with_nested_mapping_and_comment(self):
        text = "# leading comment\nsdd:\n  profile: full      # trailing comment\n  paths:\n    adr: docs/adr\n"
        self.assertEqual(
            {"sdd": {"profile": "full", "paths": {"adr": "docs/adr"}}},
            sdd_check.load_yaml(text),
        )

    def test_block_sequence_of_scalars(self):
        text = "areas:\n  - FOUND\n  - EHR\n"
        self.assertEqual({"areas": ["FOUND", "EHR"]}, sdd_check.load_yaml(text))

    def test_block_sequence_of_mappings(self):
        text = (
            "requirements:\n"
            "  - id: REQ-FOUND-001\n"
            "    title: Environment boundary\n"
            "    tests:\n"
            "      - tests/env_test.py\n"
            "  - id: REQ-FOUND-002\n"
            "    title: Second\n"
        )
        self.assertEqual(
            {
                "requirements": [
                    {
                        "id": "REQ-FOUND-001",
                        "title": "Environment boundary",
                        "tests": ["tests/env_test.py"],
                    },
                    {"id": "REQ-FOUND-002", "title": "Second"},
                ]
            },
            sdd_check.load_yaml(text),
        )

    def test_inline_list_quoted_and_unquoted_with_comment(self):
        text = "globs: [a, \"b c\", 'd']   # a trailing comment\nempty: []\n"
        self.assertEqual({"globs": ["a", "b c", "d"], "empty": []}, sdd_check.load_yaml(text))

    def test_folded_block_scalar(self):
        text = "note: >-\n  one\n  two\n  three\nafter: x\n"
        self.assertEqual({"note": "one two three", "after": "x"}, sdd_check.load_yaml(text))

    def test_literal_block_scalar(self):
        text = "note: |\n  one\n  two\nafter: x\n"
        self.assertEqual({"note": "one\ntwo\n", "after": "x"}, sdd_check.load_yaml(text))

    def test_empty_value_is_none(self):
        text = "upstream:\nground_truth: \n"
        self.assertEqual({"upstream": None, "ground_truth": None}, sdd_check.load_yaml(text))

    def test_scalar_coercion(self):
        text = "yes_: true\nno_: false\nn: 42\nneg: -7\nquoted: \"0.6.0\"\nver: 0.6.0\n"
        self.assertEqual(
            {"yes_": True, "no_": False, "n": 42, "neg": -7, "quoted": "0.6.0", "ver": "0.6.0"},
            sdd_check.load_yaml(text),
        )

    def test_comment_after_a_key_that_opens_a_mapping(self):
        text = "check:\n  families:   # error | warn | off\n    descriptor: error\n    links: warn\n"
        self.assertEqual(
            {"check": {"families": {"descriptor": "error", "links": "warn"}}},
            sdd_check.load_yaml(text),
        )

    def test_comment_after_a_key_that_opens_a_sequence(self):
        text = "probes:                # optional (use_probes)\n  - PROBE-031\n  - PROBE-073\n"
        self.assertEqual({"probes": ["PROBE-031", "PROBE-073"]}, sdd_check.load_yaml(text))

    def test_inline_list_followed_by_a_comment_carrying_brackets(self):
        text = "worker_skills: []      # skills named in the brief, e.g. [go-coding:go-testing]\n"
        self.assertEqual({"worker_skills": []}, sdd_check.load_yaml(text))

    def test_trailing_content_after_an_inline_list_is_refused(self):
        self.assertEqual(1, self._error_line("globs: [a, b] and more\n"))

    def test_every_yaml_sample_in_the_schema_reference_loads(self):
        reference = TOOLS_DIR.parent / "references" / "traceability-schema.md"
        blocks = yaml_blocks(reference.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(blocks), 3, "the schema reference carries no YAML samples")
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                if block.lstrip().startswith("---"):
                    mapping, _ = sdd_check.frontmatter(block)
                    self.assertIsInstance(mapping, dict)
                else:
                    self.assertIsInstance(sdd_check.load_yaml(block), dict)
        descriptor = sdd_check.load_yaml(blocks[0])["sdd"]
        self.assertEqual("full", descriptor["profile"])
        self.assertEqual("error", descriptor["check"]["families"]["descriptor"])
        self.assertEqual("off", descriptor["check"]["families"]["draft-reason"])
        self.assertEqual([], descriptor["agents"]["worker_skills"])
        self.assertEqual(["claude", "cursor"], descriptor["agents"]["review_panel"]["full"])
        record = sdd_check.load_yaml(blocks[1])["requirements"][0]
        self.assertEqual("REQ-040", record["id"])
        self.assertEqual(["PROBE-031", "PROBE-073"], record["probes"])
        self.assertEqual("docs/specifications/auth.md#token-refresh-req-040", record["canonical"])

    def _error_line(self, text):
        with self.assertRaises(sdd_check.YamlError) as caught:
            sdd_check.load_yaml(text)
        return caught.exception.line

    def test_tab_indent_raises(self):
        self.assertEqual(2, self._error_line("sdd:\n\tprofile: full\n"))

    def test_anchor_raises(self):
        self.assertEqual(2, self._error_line("a: 1\nb: &anchor value\n"))

    def test_alias_raises(self):
        self.assertEqual(2, self._error_line("a: 1\nb: *alias\n"))

    def test_flow_mapping_raises(self):
        self.assertEqual(1, self._error_line("a: {b: 1}\n"))

    def test_tag_raises(self):
        self.assertEqual(1, self._error_line("a: !!str 1\n"))

    def test_second_document_raises(self):
        self.assertEqual(4, self._error_line("---\na: 1\nb: 2\n---\nc: 3\n"))

    def test_bad_dedent_raises(self):
        text = "a:\n    b: 1\n  c: 2\n"
        self.assertEqual(3, self._error_line(text))


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
SAMPLE_DOC = """---
kind: specification
status: draft
---

# SPEC-ENV — Environment

Prose with an `inline code` span.

## §1 — Environment boundary (REQ-FOUND-001)

<a id="legacy-boundary"></a>
<a name="older-boundary"></a>

**Implements:** REQ-FOUND-001

```yaml
## not a heading
```

<!-- a comment
spanning two lines -->

### §1.1 — A deeper section

Still inside section one.

## §2 — Second section

Outside section one.
"""


class TestMarkdownHelpers(unittest.TestCase):
    def test_slugify_drops_symbols_and_keeps_double_hyphen(self):
        self.assertEqual(
            "1--environment-boundary-req-found-001",
            sdd_check.slugify("§1 — Environment boundary (REQ-FOUND-001)"),
        )

    def test_slugify_keeps_underscore(self):
        self.assertEqual("event_context-stays", sdd_check.slugify("EVENT_CONTEXT stays"))

    def test_headings_report_level_and_slug(self):
        found = sdd_check.headings(SAMPLE_DOC)
        levels = [(level, slug) for _, level, _, slug in found]
        self.assertIn((1, "spec-env--environment"), levels)
        self.assertIn((2, "1--environment-boundary-req-found-001"), levels)
        self.assertIn((3, "11--a-deeper-section"), levels)
        self.assertNotIn((2, "not-a-heading"), levels)

    def test_explicit_anchors(self):
        self.assertEqual(
            {"legacy-boundary", "older-boundary"}, sdd_check.explicit_anchors(SAMPLE_DOC)
        )

    def test_section_slice_stops_at_same_level_not_deeper(self):
        span = sdd_check.section_slice(SAMPLE_DOC, "1--environment-boundary-req-found-001")
        self.assertIsNotNone(span)
        start, end = span
        body = "\n".join(SAMPLE_DOC.split("\n")[start - 1 : end - 1])
        self.assertIn("**Implements:** REQ-FOUND-001", body)
        self.assertIn("A deeper section", body)
        self.assertNotIn("Second section", body)
        self.assertIsNone(sdd_check.section_slice(SAMPLE_DOC, "no-such-anchor"))

    def test_frontmatter_on_line_one(self):
        mapping, after = sdd_check.frontmatter(SAMPLE_DOC)
        self.assertEqual("specification", mapping["kind"])
        self.assertEqual(5, after)

    def test_frontmatter_after_leading_html_comment(self):
        text = "<!-- generated: do not edit -->\n---\nkind: guide\n---\n\n# Title\n"
        mapping, after = sdd_check.frontmatter(text)
        self.assertEqual({"kind": "guide"}, mapping)
        self.assertEqual(5, after)

    def test_frontmatter_absent_when_prose_comes_first(self):
        text = "# Title\n\nSome prose.\n\n---\nkind: guide\n---\n"
        self.assertEqual((None, 0), sdd_check.frontmatter(text))

    def test_strip_noncontent_blanks_fences_code_spans_and_comments(self):
        rows = dict(sdd_check.strip_noncontent(SAMPLE_DOC))
        lines = SAMPLE_DOC.split("\n")
        self.assertEqual(len(lines), len(rows))
        fence_line = lines.index("## not a heading") + 1
        self.assertEqual("", rows[fence_line].strip())
        prose_line = lines.index("Prose with an `inline code` span.") + 1
        self.assertNotIn("inline code", rows[prose_line])
        self.assertIn("Prose with an", rows[prose_line])
        comment_line = lines.index("spanning two lines -->") + 1
        self.assertEqual("", rows[comment_line].strip())
        self.assertEqual("", rows[2].strip())

    def test_table_rows_skips_the_separator(self):
        text = (
            "| ID | Title | Impl. |\n"
            "|---|---|---|\n"
            "| REQ-FOUND-001 | Boundary | shipped |\n"
            "| REQ-FOUND-002 | Second | planned |\n"
            "\nprose\n"
        )
        rows = sdd_check.table_rows(text)
        self.assertEqual(2, len(rows))
        line, header, cells = rows[0]
        self.assertEqual(3, line)
        self.assertEqual(["ID", "Title", "Impl."], header)
        self.assertEqual(["REQ-FOUND-001", "Boundary", "shipped"], cells)
        self.assertEqual(["REQ-FOUND-002", "Second", "planned"], rows[1][2])


# ---------------------------------------------------------------------------
# descriptor and map-schema
# ---------------------------------------------------------------------------
class TestDescriptorFamily(BaselineCase):
    def test_unknown_req_style(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "req_style: area-prefixed", "req_style: other")
        self.assert_finding(self.run_only("descriptor"), "req_style")

    def test_area_prefixed_without_areas(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "  req_areas: [FOUND]\n", "")
        self.assert_finding(self.run_only("descriptor"), "req_areas")

    def test_excluded_area_must_be_disjoint(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "excluded_areas: [BENCH]", "excluded_areas: [FOUND]")
        self.assert_finding(self.run_only("descriptor"), "disjoint")

    def test_pinned_version_must_equal_the_tool(self):
        self.edit(sdd_check.DESCRIPTOR_REL, 'version: "0.6.0"', 'version: "0.5.0"')
        self.assert_finding(self.run_only("descriptor"), "version")

    def test_family_severity_vocabulary(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "rfc2119: warn", "rfc2119: loud")
        self.assert_finding(self.run_only("descriptor"), "error | warn | off")

    def test_unknown_family_key(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "      draft-reason: off", "      lanes: error")
        self.assert_finding(self.run_only("descriptor"), "unknown family")

    def test_full_profile_requires_a_directory(self):
        self.write("docs/requirements.md", (self.tmp / "docs/requirements/README.md").read_text())
        self.edit(sdd_check.DESCRIPTOR_REL, "requirements: docs/requirements", "requirements: docs/requirements.md")
        self.assert_finding(self.run_only("descriptor"), "profile full requires a directory")

    def test_lightweight_profile_accepts_a_file(self):
        self.write("docs/requirements.md", (self.tmp / "docs/requirements/README.md").read_text())
        self.edit(sdd_check.DESCRIPTOR_REL, "profile: full", "profile: lightweight")
        self.edit(sdd_check.DESCRIPTOR_REL, "requirements: docs/requirements", "requirements: docs/requirements.md")
        self.assert_clean(self.run_only("descriptor"))


MAP_REL = "docs/specifications/traceability.yaml"


class TestMapSchemaFamily(BaselineCase):
    def test_duplicate_id(self):
        text = (self.tmp / MAP_REL).read_text()
        self.write(MAP_REL, text + "  - id: REQ-FOUND-001\n    title: Twin\n"
                   "    canonical: docs/specifications/env.md#1--boundary-req-found-001\n"
                   "    status: draft\n    implementation: planned\n")
        self.assert_finding(self.run_only("map-schema"), "duplicate")

    def test_excluded_area(self):
        self.edit(MAP_REL, "id: REQ-FOUND-001", "id: REQ-BENCH-001")
        self.assert_finding(self.run_only("map-schema"), "excluded")

    def test_undeclared_area(self):
        self.edit(MAP_REL, "id: REQ-FOUND-001", "id: REQ-OTHER-001")
        self.assert_finding(self.run_only("map-schema"), "not declared")

    def test_implementation_vocabulary(self):
        self.edit(MAP_REL, "implementation: shipped", "implementation: done")
        self.assert_finding(self.run_only("map-schema"), "implementation")

    def test_canonical_needs_an_anchor(self):
        self.edit(MAP_REL, "canonical: docs/specifications/env.md#1--boundary-req-found-001",
                  "canonical: docs/specifications/env.md")
        self.assert_finding(self.run_only("map-schema"), "path#anchor")

    def test_retired_plans_key_warns(self):
        self.edit(MAP_REL, "    status: draft", "    plans: [x]\n    status: draft")
        report = self.run_only("map-schema")
        self.assertEqual([], self.levelled(report, "ERROR"), report.render(self.tmp))
        warnings = self.levelled(report, "WARN")
        self.assertEqual(1, len(warnings), report.render(self.tmp))
        self.assertIn("plans", warnings[0].message)
        self.assertIn("retired", warnings[0].message)

    def test_zero_records(self):
        self.write(MAP_REL, "requirements: []\n")
        report = self.run_only("map-schema")
        self.assert_finding(report, "zero records")
        self.assertEqual(1, report.exit_code())

    def test_map_error_anchor_names_the_file(self):
        self.write(MAP_REL, "requirements: []\n")
        finding = self.assert_finding(self.run_only("map-schema"), "zero records")
        self.assertIn(MAP_REL, finding.anchor)


# ---------------------------------------------------------------------------
# map-to-tree
# ---------------------------------------------------------------------------
SPEC_REL = "docs/specifications/env.md"


class TestMapToTreeFamily(BaselineCase):
    def test_canonical_file_missing(self):
        (self.tmp / SPEC_REL).unlink()
        self.assert_finding(self.run_only("map-to-tree"), "canonical file missing")

    def test_anchor_missing(self):
        self.edit(MAP_REL, "#1--boundary-req-found-001", "#1--no-such-section")
        self.assert_finding(self.run_only("map-to-tree"), "anchor")

    def test_implements_marker_outside_the_section(self):
        self.edit(SPEC_REL, "**Implements:** REQ-FOUND-001\n\n", "")
        self.edit(SPEC_REL, "## §1 — Boundary (REQ-FOUND-001)",
                  "## §1 — Boundary (REQ-FOUND-001)\n\nNo marker here.\n\n## §2 — Later\n\n**Implements:** REQ-FOUND-001")
        self.assert_finding(self.run_only("map-to-tree"), "Implements")

    def test_implements_marker_matches_on_identifier_boundary(self):
        self.edit(SPEC_REL, "**Implements:** REQ-FOUND-001", "**Implements:** REQ-FOUND-0011")
        self.assert_finding(self.run_only("map-to-tree"), "Implements")

    def test_missing_package_path(self):
        self.edit(MAP_REL, "      - src/env\n", "      - src/nowhere\n")
        self.assert_finding(self.run_only("map-to-tree"), "missing package path")

    def test_test_entry_must_be_a_file(self):
        self.edit(MAP_REL, "      - tests/env_test.py", "      - tests")
        self.assert_finding(self.run_only("map-to-tree"), "must be a file")

    def test_probe_without_catalogue_or_citing_test(self):
        self.edit(MAP_REL, "    tests:", "    probes:\n      - PROBE-001\n    tests:")
        self.assert_finding(self.run_only("map-to-tree"), "PROBE-001")

    def test_probe_resolved_by_the_catalogue(self):
        self.edit(MAP_REL, "    tests:", "    probes:\n      - PROBE-001\n    tests:")
        self.write("docs/specifications/conformance.md",
                   "---\nkind: specification\nspec: SPEC-CONF\nstatus: draft\nmode: spec-first\n---\n\n"
                   "# Conformance probes\n\n#### PROBE-001 — the refusal names the variable\n\nA probe.\n")
        self.edit(sdd_check.DESCRIPTOR_REL, 'probes_catalogue: ""',
                  'probes_catalogue: docs/specifications/conformance.md')
        self.assert_clean(self.run_only("map-to-tree"))

    def test_enforced_record_needs_evidence(self):
        self.edit(MAP_REL, "    packages:\n      - src/env\n    tests:\n      - tests/env_test.py\n", "")
        self.assert_finding(self.run_only("map-to-tree"), "no evidence")

    def test_operations_alone_is_evidence(self):
        self.edit(MAP_REL, "    packages:\n      - src/env\n    tests:\n      - tests/env_test.py\n",
                  "    operations:\n      - docs/operations/run.md\n")
        self.write("docs/operations/run.md", "---\nkind: operations\n---\n\n# Run the service\n\nStart it.\n")
        self.assert_clean(self.run_only("map-to-tree"))


# ---------------------------------------------------------------------------
# index-sync
# ---------------------------------------------------------------------------
INDEX_REL = "docs/requirements/README.md"
INDEX_ROW = "| [REQ-FOUND-001](REQ-FOUND-001.md) | Environment boundary | Draft | shipped |"
SECOND_RECORD = (
    "  - id: REQ-FOUND-002\n"
    "    title: Second\n"
    "    canonical: docs/specifications/env.md#1--boundary-req-found-001\n"
    "    status: draft\n"
    "    implementation: proposed\n"
)


class TestIndexSyncFamily(BaselineCase):
    def test_row_without_a_record(self):
        self.edit(INDEX_REL, INDEX_ROW, INDEX_ROW + "\n| REQ-FOUND-002 | Second | Draft | proposed |")
        self.assert_finding(self.run_only("index-sync"), "missing from traceability")

    def test_record_without_a_row(self):
        text = (self.tmp / MAP_REL).read_text()
        self.write(MAP_REL, text + SECOND_RECORD)
        self.assert_finding(self.run_only("index-sync"), "missing from the index")

    def test_implementation_cell_disagrees(self):
        self.edit(INDEX_REL, "| Draft | shipped |", "| Draft | proposed |")
        self.assert_finding(self.run_only("index-sync"), "Implementation")

    def test_detail_file_status_disagrees(self):
        self.edit("docs/requirements/REQ-FOUND-001.md", "status: draft", "status: stable")
        self.assert_finding(self.run_only("index-sync"), "detail file")

    def test_columns_are_found_by_header_not_position(self):
        self.edit(INDEX_REL, "| ID | Title | Stability | Implementation |", "| ID | Title | Impl. | Status |")
        self.edit(INDEX_REL, "| Environment boundary | Draft | shipped |", "| Environment boundary | shipped | Draft |")
        self.assert_clean(self.run_only("index-sync"))

    def test_index_with_no_req_rows(self):
        self.edit(INDEX_REL, INDEX_ROW, "| none yet | — | — | — |")
        self.assert_finding(self.run_only("index-sync"), "zero rows")

    def test_specification_requirements_frontmatter_warns(self):
        self.edit(SPEC_REL, "requirements: [REQ-FOUND-001]", "requirements: [REQ-FOUND-001, REQ-FOUND-002]")
        self.assert_finding(self.run_only("index-sync"), "requirements:", level="WARN")

    def test_lightweight_profile_skips_the_detail_file_check(self):
        index = (self.tmp / INDEX_REL).read_text().replace("[REQ-FOUND-001](REQ-FOUND-001.md)", "REQ-FOUND-001")
        self.write("docs/requirements.md", index)
        for child in sorted((self.tmp / "docs/requirements").iterdir()):
            child.unlink()
        (self.tmp / "docs/requirements").rmdir()
        self.edit(sdd_check.DESCRIPTOR_REL, "profile: full", "profile: lightweight")
        self.edit(sdd_check.DESCRIPTOR_REL, "requirements: docs/requirements", "requirements: docs/requirements.md")
        report = self.run_only("index-sync")
        self.assert_clean(report)
        notes = [f for f in self.levelled(report, "NOTE") if "detail" in f.message]
        self.assertTrue(notes, report.render(self.tmp))
        self.assertIn("skipped", notes[0].message)


# ---------------------------------------------------------------------------
# plans, tree-to-map, draft-reason
# ---------------------------------------------------------------------------
PLAN_REL = "docs/plans/2026-01-01-env.md"
LATER_PLAN = """---
kind: plan
plan: 2026-02-02-later
implements: [REQ-FOUND-001]
mode: spec-first
status: done
---

# 2026-02-02 — Later

## Tasks

- [x] Done.
"""


class PlansCase(BaselineCase):
    """A baseline repository plus the git helpers the stale-plan rule needs."""

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.tmp)] + list(args),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def init_git(self):
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "user.name", "sdd-check tests")
        self.git("config", "commit.gpgsign", "false")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)


class TestPlansFamily(PlansCase):
    def test_missing_mode(self):
        self.edit(PLAN_REL, "mode: spec-first\n", "")
        self.assert_finding(self.run_only("plans"), "mode")

    def test_plan_key_must_equal_the_filename(self):
        self.edit(PLAN_REL, "plan: 2026-01-01-env", "plan: wrong-name")
        self.assert_finding(self.run_only("plans"), "filename")

    def test_status_vocabulary(self):
        self.edit(PLAN_REL, "status: done", "status: finished")
        self.assert_finding(self.run_only("plans"), "status")

    def test_implements_without_a_record(self):
        self.edit(PLAN_REL, "implements: [REQ-FOUND-001]", "implements: [REQ-FOUND-009]")
        self.assert_finding(self.run_only("plans"), "no record")

    def test_active_plan_for_a_shipped_requirement_warns(self):
        self.edit(PLAN_REL, "status: done", "status: active")
        self.assert_finding(self.run_only("plans"), "still active", level="WARN")

    def test_active_plan_is_fine_when_implementation_aligned(self):
        self.edit(PLAN_REL, "status: done", "status: active")
        self.edit(PLAN_REL, "mode: spec-first", "mode: implementation-aligned")
        self.assert_clean(self.run_only("plans"))

    def test_done_plan_for_an_unenforced_requirement_warns(self):
        self.edit(MAP_REL, "implementation: shipped", "implementation: proposed")
        self.assert_finding(self.run_only("plans"), "not enforced", level="WARN")

    def test_done_plan_after_the_tag_is_clean(self):
        (self.tmp / PLAN_REL).unlink()
        self.init_git()
        self.commit("baseline")
        self.git("tag", "v1.0.0")
        self.write("docs/plans/2026-02-02-later.md", LATER_PLAN)
        self.commit("the later plan")
        self.assert_clean(self.run_only("plans"))

    def test_done_plan_before_the_tag_is_stale(self):
        (self.tmp / PLAN_REL).unlink()
        self.write("docs/plans/2026-02-02-later.md", LATER_PLAN)
        self.init_git()
        self.commit("baseline with the plan")
        self.git("tag", "v1.0.0")
        self.assert_finding(self.run_only("plans"), "predates the latest release tag")

    def test_without_git_only_the_stale_rule_is_skipped(self):
        self.edit(PLAN_REL, "status: done", "status: finished")
        report = self.run_only("plans")
        self.assertEqual("stale-plan rule needs git", report.families_skipped.get("plans"))
        self.assertIn("plans (stale-plan rule needs git)", report.render(self.tmp))
        self.assertIn("plans", report.families_run)
        self.assert_finding(report, "status")


class TestTreeToMapFamily(BaselineCase):
    def test_unknown_identifier_cited(self):
        self.write("src/env/thing.py", "# implements REQ-FOUND-077\n")
        self.assert_finding(self.run_only("tree-to-map"), "unknown identifier cited", level="WARN")

    def test_test_file_citing_a_record_with_no_tests(self):
        self.edit(MAP_REL, "    tests:\n      - tests/env_test.py\n", "")
        self.write("tests/other_test.py", "def test_boundary():\n    # REQ-FOUND-001\n    assert True\n")
        self.assert_finding(self.run_only("tree-to-map"), "lists no tests", level="WARN")

    def test_docs_are_not_scanned(self):
        self.write("docs/notes.md", "---\nkind: analysis\n---\n\n# Notes\n\nREQ-FOUND-077 was considered.\n")
        self.assert_clean(self.run_only("tree-to-map"))


class TestDraftReasonFamily(BaselineCase):
    def test_off_by_default(self):
        report = self.run_only("draft-reason")
        self.assertEqual("off", report.families_skipped.get("draft-reason"))
        self.assertNotIn("draft-reason", report.families_run)

    def test_enabled_draft_and_enforced_needs_a_reason(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "draft-reason: off", "draft-reason: error")
        self.assert_finding(self.run_only("draft-reason"), "draft_reason")

    def test_enabled_with_a_reason_is_clean(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "draft-reason: off", "draft-reason: error")
        self.edit(MAP_REL, "    status: draft", "    draft_reason: wording under review\n    status: draft")
        self.assert_clean(self.run_only("draft-reason"))


# ---------------------------------------------------------------------------
# The report and the command line
# ---------------------------------------------------------------------------
class TestReport(BaselineCase):
    def test_first_line_states_what_ran_against_what(self):
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        first = report.render(self.tmp).split("\n")[0]
        self.assertRegex(first, r"^sdd-check 0\.6\.0 · .* · profile full · 1 REQ records$")

    def test_finding_line_format(self):
        (self.tmp / SPEC_REL).unlink()
        report = self.run_only("map-to-tree")
        lines = report.render(self.tmp).split("\n")
        wanted = [l for l in lines if l.startswith("[map-to-tree] ERROR REQ-FOUND-001: ")]
        self.assertTrue(wanted, report.render(self.tmp))
        self.assertIn("canonical file missing", wanted[0])

    def test_summary_line_for_a_clean_run(self):
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        expected = "sdd-check: OK — %d checks, 0 errors, 0 warnings" % len(report.families_run)
        self.assertIn(expected, report.render(self.tmp).split("\n"))

    def test_summary_line_for_a_failed_run(self):
        (self.tmp / SPEC_REL).unlink()
        report = self.run_only("map-to-tree")
        self.assertIn(
            "sdd-check: FAILED — %d errors, %d warnings" % (report.errors(), report.warnings()),
            report.render(self.tmp).split("\n"),
        )

    def test_families_run_and_skipped_are_named(self):
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        expected = [f for f in sdd_check.FAMILIES if f in sdd_check.CHECKS and f != "draft-reason"]
        self.assertEqual(expected, report.families_run)
        rendered = report.render(self.tmp)
        self.assertIn("families run: %s;" % ", ".join(expected), rendered)
        self.assertIn("draft-reason (off)", rendered)
        for family, reason in report.families_skipped.items():
            self.assertIn("%s (%s)" % (family, reason), rendered)

    def test_link_exclusions_are_printed_when_set(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "      exclude: []", '      exclude: ["docs/vendor/**"]')
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        self.assertIn("link exclusions: docs/vendor/**", report.render(self.tmp).split("\n"))

    def test_missing_map_skips_the_record_families(self):
        (self.tmp / MAP_REL).unlink()
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        self.assertEqual(1, report.exit_code())
        rendered = report.render(self.tmp)
        self.assertIn("[map-schema] ERROR docs/specifications/traceability.yaml: ", rendered)
        for family in ("map-to-tree", "index-sync", "plans", "tree-to-map"):
            self.assertEqual("map unavailable", report.families_skipped.get(family), rendered)

    def test_unparseable_map_names_the_file_and_line(self):
        self.write(MAP_REL, "requirements:\n  - id: REQ-FOUND-001\n\tbroken: true\n")
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        finding = [f for f in report.findings if f.family == "map-schema"][0]
        self.assertEqual("ERROR", finding.level)
        self.assertEqual("docs/specifications/traceability.yaml:3", finding.anchor)
        self.assertEqual(1, report.exit_code())

    def test_note_never_changes_the_exit_code(self):
        report = sdd_check.Report()
        report.add("plans", "NOTE", "docs/plans/x.md", "a note")
        self.assertEqual(0, report.exit_code())


class TestCommandLine(BaselineCase):
    def run_main(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = sdd_check.main(argv)
        return code, buffer.getvalue()

    def test_check_returns_zero_on_a_clean_repository(self):
        code, out = self.run_main(["check", "--root", str(self.tmp)])
        self.assertEqual(0, code, out)
        self.assertIn("sdd-check: OK", out)

    def test_check_returns_one_on_an_error(self):
        (self.tmp / SPEC_REL).unlink()
        code, out = self.run_main(["check", "--root", str(self.tmp)])
        self.assertEqual(1, code, out)
        self.assertIn("sdd-check: FAILED", out)

    def test_exit_two_report_is_two_lines(self):
        (self.tmp / sdd_check.DESCRIPTOR_REL).unlink()
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        lines = report.render(self.tmp).split("\n")
        self.assertEqual(2, len(lines), lines)
        self.assertTrue(lines[0].startswith("sdd-check 0.6.0 · "), lines[0])
        self.assertTrue(lines[1].startswith("sdd-check: FAILED — "), lines[1])
        self.assertIn("docs/.sdd.yaml", lines[1])
        self.assertEqual(2, report.exit_code())

    def test_missing_descriptor_returns_two(self):
        (self.tmp / sdd_check.DESCRIPTOR_REL).unlink()
        code, out = self.run_main(["check", "--root", str(self.tmp)])
        self.assertEqual(2, code, out)
        self.assertIn("docs/.sdd.yaml", out)

    def test_unparseable_descriptor_returns_two(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "  profile: full", "  profile: full\n\tbroken: true")
        code, out = self.run_main(["check", "--root", str(self.tmp)])
        self.assertEqual(2, code, out)
        self.assertIn("docs/.sdd.yaml", out)

    def test_unknown_family_returns_two(self):
        code, out = self.run_main(["check", "--root", str(self.tmp), "--only", "links,nope"])
        self.assertEqual(2, code, out)
        self.assertIn("unknown family", out)

    def test_unknown_command_returns_two(self):
        code, out = self.run_main(["frobnicate"])
        self.assertEqual(2, code, out)
        self.assertIn("unknown command", out)

    def test_version(self):
        code, out = self.run_main(["--version"])
        self.assertEqual(0, code)
        self.assertEqual("0.6.0", out.strip())
        self.assertEqual("0.6.0", sdd_check.__version__)

    def test_stub_commands_are_honest(self):
        for argv in (["generate", "--root", str(self.tmp)],
                     ["context", "REQ-FOUND-001", "--root", str(self.tmp)],
                     ["selftest", "--root", str(self.tmp)]):
            code, out = self.run_main(argv)
            self.assertEqual(2, code, out)
            self.assertEqual("not implemented in this build", out.strip())


# ---------------------------------------------------------------------------
# The interfaces later builds call
# ---------------------------------------------------------------------------
class TestInterfaces(BaselineCase):
    def test_descriptor_accessors(self):
        desc = sdd_check.Descriptor.load(self.tmp)
        self.assertEqual(r"REQ-[A-Z][A-Z0-9]*-\d{3,}", desc.req_pattern().pattern)
        self.assertEqual(self.tmp / "docs/requirements/README.md", desc.requirements_index_path())
        self.assertEqual(self.tmp / "docs/requirements", desc.requirements_dir())
        self.assertIn(self.tmp / "docs/specifications/env.md", desc.specification_files())
        self.assertEqual([self.tmp / "docs"], desc.docs_roots())
        self.assertEqual(["the specifications in docs/specifications"], desc.ground_truth_sources())
        self.assertEqual({}, desc.upstream_relations())
        self.assertEqual("error", desc.severity("descriptor"))
        self.assertEqual("off", desc.severity("draft-reason"))

    def test_flat_numeric_pattern(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "req_style: area-prefixed", "req_style: flat-numeric")
        desc = sdd_check.Descriptor.load(self.tmp)
        self.assertEqual(r"REQ-\d{3,}", desc.req_pattern().pattern)

    def test_named_upstream_relations(self):
        self.edit(sdd_check.DESCRIPTOR_REL, '  upstream: ""',
                  "  upstream:\n    core:\n      repo: example.org/core\n      role: consumed")
        desc = sdd_check.Descriptor.load(self.tmp)
        self.assertEqual({"core": {"repo": "example.org/core", "role": "consumed"}},
                         desc.upstream_relations())

    def test_context_reads_files_and_lists_docs(self):
        desc = sdd_check.Descriptor.load(self.tmp)
        ctx = sdd_check.Context(self.tmp, desc, sdd_check.load_map(desc))
        self.assertIn("REQ-FOUND-001", ctx.records_by_id)
        self.assertIn("SPEC-ENV", ctx.read(self.tmp / SPEC_REL))
        names = [ctx.rel(path) for path in ctx.docs_files()]
        self.assertIn("docs/specifications/env.md", names)
        self.assertNotIn("AGENTS.md", names)
        self.assertIsNone(ctx.git("status", "--short"))

    def test_records_carry_their_line_number(self):
        desc = sdd_check.Descriptor.load(self.tmp)
        records = sdd_check.load_map(desc)
        self.assertEqual(1, len(records))
        self.assertEqual(3, records[0].line)
        self.assertEqual([], records[0].unknown_keys)
        self.assertTrue(records[0].enforced())
        self.assertEqual(["src/env", "tests/env_test.py"], records[0].evidence())


# ---------------------------------------------------------------------------
# Rules the first build shipped without a test
# ---------------------------------------------------------------------------
class TestDescriptorRules(BaselineCase):
    def test_flat_numeric_declares_no_areas(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "req_style: area-prefixed", "req_style: flat-numeric")
        self.assert_finding(self.run_only("descriptor"), "req_areas", family="descriptor")

    def test_declared_path_must_exist(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "adr: docs/adr", "adr: docs/decisions")
        self.assert_finding(self.run_only("descriptor"), "does not exist", family="descriptor")

    def test_traceability_path_must_exist(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "traceability: docs/specifications/traceability.yaml",
                  "traceability: docs/specifications/nope.yaml")
        self.assert_finding(self.run_only("descriptor"), "traceability", family="descriptor")

    def test_default_mode_vocabulary(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "default_mode: spec-first", "default_mode: guessing")
        self.assert_finding(self.run_only("descriptor"), "default_mode", family="descriptor")

    def test_doc_kinds_may_be_extended(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "reference, upstream]", "reference, upstream, benchmark]")
        self.assert_clean(self.run_only("descriptor"))

    def test_doc_kinds_must_keep_the_normative_kinds(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "specification, adr, plan, guide", "specification, adr, guide")
        self.assert_finding(self.run_only("descriptor"), "plan", family="descriptor")


class TestMapSchemaRules(BaselineCase):
    def test_id_style_mismatch(self):
        self.edit(MAP_REL, "id: REQ-FOUND-001", "id: REQ-001")
        self.assert_finding(self.run_only("map-schema"), "style", family="map-schema")

    def test_required_field_missing(self):
        self.edit(MAP_REL, "    title: Environment boundary\n", "")
        self.assert_finding(self.run_only("map-schema"), "title is required", family="map-schema")

    def test_status_vocabulary(self):
        self.edit(MAP_REL, "    status: draft", "    status: rough")
        self.assert_finding(self.run_only("map-schema"), "status", family="map-schema")

    def test_list_field_that_is_not_a_list(self):
        self.edit(MAP_REL, "    packages:\n      - src/env\n", "    packages: src/env\n")
        self.assert_finding(self.run_only("map-schema"), "must be a list of strings", family="map-schema")


class TestMapToTreeRules(BaselineCase):
    def anchor_above_the_section(self):
        self.edit(SPEC_REL, "## §1 — Boundary", '<a id="legacy-boundary"></a>\n\n## §1 — Boundary')
        self.edit(MAP_REL, "#1--boundary-req-found-001", "#legacy-boundary")

    def move_the_marker_into_a_later_section(self):
        self.edit(SPEC_REL, "**Implements:** REQ-FOUND-001\n\n", "")
        path = self.tmp / SPEC_REL
        path.write_text(path.read_text() + "\n## §2 — Later\n\n**Implements:** REQ-FOUND-001\n")

    def test_anchor_above_a_heading_slices_that_heading(self):
        self.anchor_above_the_section()
        self.assert_clean(self.run_only("map-to-tree"))

    def test_anchor_above_a_heading_does_not_reach_the_next_section(self):
        self.anchor_above_the_section()
        self.move_the_marker_into_a_later_section()
        self.assert_finding(self.run_only("map-to-tree"), "Implements", family="map-to-tree")

    def test_anchor_inside_a_section_uses_that_section(self):
        self.edit(SPEC_REL, "**Implements:** REQ-FOUND-001",
                  '<a id="legacy-boundary"></a>\n\n**Implements:** REQ-FOUND-001')
        self.edit(MAP_REL, "#1--boundary-req-found-001", "#legacy-boundary")
        self.assert_clean(self.run_only("map-to-tree"))

    def test_missing_tests_path(self):
        self.edit(MAP_REL, "      - tests/env_test.py", "      - tests/nope.py")
        self.assert_finding(self.run_only("map-to-tree"), "missing tests path", family="map-to-tree")

    def test_missing_operations_path(self):
        self.edit(MAP_REL, "    tests:", "    operations:\n      - docs/operations/nope.md\n    tests:")
        self.assert_finding(self.run_only("map-to-tree"), "missing operations path", family="map-to-tree")

    def test_operations_entry_must_be_a_file(self):
        self.edit(MAP_REL, "    tests:", "    operations:\n      - docs\n    tests:")
        finding = self.assert_finding(self.run_only("map-to-tree"), "must be a file", family="map-to-tree")
        self.assertIn("an operations entry", finding.message)

    def test_probe_resolved_by_a_citing_test(self):
        self.edit(MAP_REL, "    tests:", "    probes:\n      - PROBE-001\n    tests:")
        self.edit("tests/env_test.py", "REQ-FOUND-001", "REQ-FOUND-001 / PROBE-001")
        self.assert_clean(self.run_only("map-to-tree"))


class TestIndexSyncRules(BaselineCase):
    def test_stability_cell_disagrees(self):
        self.edit(INDEX_REL, "| Draft | shipped |", "| Stable | shipped |")
        self.assert_finding(self.run_only("index-sync"), "Stability", family="index-sync")

    def test_one_named_column_and_one_positional(self):
        self.edit(INDEX_REL, "| ID | Title | Stability | Implementation |", "| ID | Title | Stability | Build |")
        self.edit(INDEX_REL, "| Draft | shipped |", "| Draft | planned |")
        self.assert_finding(self.run_only("index-sync"), "Implementation", family="index-sync")

    def test_last_two_columns_when_no_header_matches(self):
        self.edit(INDEX_REL, "| ID | Title | Stability | Implementation |", "| ID | Title | Stage | Build |")
        self.edit(INDEX_REL, "| Draft | shipped |", "| Draft | planned |")
        self.assert_finding(self.run_only("index-sync"), "Implementation", family="index-sync")


class TestPlansRules(PlansCase):
    def test_mode_vocabulary(self):
        self.edit(PLAN_REL, "mode: spec-first", "mode: vibes")
        self.assert_finding(self.run_only("plans"), "mode", family="plans")

    def test_missing_plans_directory_skips_the_family(self):
        (self.tmp / PLAN_REL).unlink()
        (self.tmp / "docs/plans").rmdir()
        report = self.run_only("plans")
        self.assertEqual("no plans directory", report.families_skipped.get("plans"))
        self.assertNotIn("plans", report.families_run)

    def test_a_repository_without_a_tag_skips_the_stale_rule(self):
        self.init_git()
        self.commit("baseline")
        report = self.run_only("plans")
        self.assertEqual("stale-plan rule needs a release tag", report.families_skipped.get("plans"))
        self.assertIn("plans", report.families_run)

    def test_an_uncommitted_finished_plan_is_noted(self):
        (self.tmp / PLAN_REL).unlink()
        self.init_git()
        self.commit("baseline")
        self.git("tag", "v1.0.0")
        self.write("docs/plans/2026-02-02-later.md", LATER_PLAN)
        report = self.run_only("plans")
        self.assert_clean(report)
        notes = [f for f in self.levelled(report, "NOTE") if "not committed" in f.message]
        self.assertTrue(notes, report.render(self.tmp))

    def test_unparseable_frontmatter_is_named(self):
        self.write("docs/plans/2026-03-03-broken.md",
                   "---\nplan: 2026-03-03-broken\n\timplements: [REQ-FOUND-001]\n---\n\n# Broken\n")
        self.assert_finding(self.run_only("plans"), "frontmatter does not parse", family="plans")


class TestTreeToMapRules(BaselineCase):
    def test_the_baseline_test_file_cites_its_requirement(self):
        self.assertIn("REQ-FOUND-001", (self.tmp / "tests/env_test.py").read_text())
        self.assert_clean(self.run_only("tree-to-map"))
        self.edit(MAP_REL, "    tests:\n      - tests/env_test.py\n", "")
        self.assert_finding(self.run_only("tree-to-map"), "lists no tests", level="WARN")

    def test_missing_code_root_is_reported(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "code_roots: []", "code_roots: [src, nowhere]")
        self.assert_finding(self.run_only("tree-to-map"), "code root does not exist", level="WARN")

    def test_dot_files_are_scanned(self):
        self.write("src/.hidden.py", "# REQ-FOUND-077\n")
        self.assert_finding(self.run_only("tree-to-map"), "unknown identifier cited", level="WARN")

    def test_a_nested_docs_directory_is_scanned(self):
        self.write("src/docs/note.txt", "REQ-FOUND-077\n")
        self.assert_finding(self.run_only("tree-to-map"), "unknown identifier cited", level="WARN")

    def test_a_file_that_is_not_utf8_is_skipped(self):
        (self.tmp / "src/env/blob.bin").write_bytes(b"\xff\xfe REQ-FOUND-077 \x00\x01")
        self.assert_clean(self.run_only("tree-to-map"))


class TestMapUnavailable(BaselineCase):
    def test_map_schema_reports_even_when_it_is_off(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "map-schema: error", "map-schema: off")
        (self.tmp / MAP_REL).unlink()
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        self.assert_finding(report, "traceability map is missing", family="map-schema")
        self.assertIn("map-schema", report.families_run)
        self.assertNotIn("map-schema", report.families_skipped)

    def test_map_schema_reports_even_when_it_is_not_selected(self):
        (self.tmp / MAP_REL).unlink()
        report = sdd_check.run_check(self.tmp, only=["tree-to-map"], changelog_all=False)
        self.assert_finding(report, "traceability map is missing", family="map-schema")
        self.assertEqual(["map-schema"], report.families_run)
        self.assertEqual("map unavailable", report.families_skipped.get("tree-to-map"))


if __name__ == "__main__":
    unittest.main()

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

    def assert_finding(self, report, fragment, level="ERROR"):
        hits = [f for f in self.levelled(report, level) if fragment in f.message]
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

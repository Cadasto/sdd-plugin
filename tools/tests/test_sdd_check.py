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

    def line_of(self, rel, needle):
        """The 1-based line a fixture string sits on, so a test never hard-codes one."""
        for index, line in enumerate((self.tmp / rel).read_text(encoding="utf-8").split("\n")):
            if needle in line:
                return index + 1
        self.fail("fixture drift: %r not in %s" % (needle, rel))

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
INDEX_ROW = (
    "| [REQ-FOUND-001](REQ-FOUND-001.md) | Environment boundary | "
    "[`SPEC-ENV §1`](../specifications/env.md#1--boundary-req-found-001) | Draft | shipped |"
)
SECOND_RECORD = (
    "  - id: REQ-FOUND-002\n"
    "    title: Second\n"
    "    canonical: docs/specifications/env.md#1--boundary-req-found-001\n"
    "    status: draft\n"
    "    implementation: proposed\n"
)


class TestIndexSyncFamily(BaselineCase):
    def test_row_without_a_record(self):
        self.edit(INDEX_REL, INDEX_ROW, INDEX_ROW + "\n| REQ-FOUND-002 | Second | — | Draft | proposed |")
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
        self.edit(
            INDEX_REL,
            "| ID | Title | Spec | Stability | Implementation |",
            "| ID | Title | Spec | Impl. | Status |",
        )
        self.edit(
            INDEX_REL,
            "(../specifications/env.md#1--boundary-req-found-001) | Draft | shipped |",
            "(../specifications/env.md#1--boundary-req-found-001) | shipped | Draft |",
        )
        self.assert_clean(self.run_only("index-sync"))

    def test_index_with_no_req_rows(self):
        self.edit(INDEX_REL, INDEX_ROW, "| none yet | — | — | — | — |")
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


class GitCase(BaselineCase):
    """A baseline repository plus the helpers that turn it into a git work tree."""

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


class TestPlansFamily(GitCase):
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
# doc-kinds
# ---------------------------------------------------------------------------
class TestDocKindsFamily(BaselineCase):
    def test_document_without_frontmatter(self):
        self.write("docs/notes.md", "# Notes\n\nProse.\n")
        self.assert_finding(self.run_only("doc-kinds"), "no kind", level="WARN")

    def test_kind_outside_the_declared_vocabulary(self):
        self.write("docs/notes.md", "---\nkind: memo\n---\n\n# Notes\n")
        self.assert_finding(self.run_only("doc-kinds"), "not declared in doc_kinds", level="WARN")

    def test_plan_status_outside_its_vocabulary(self):
        self.edit(PLAN_REL, "status: done", "status: pending")
        self.assert_finding(self.run_only("doc-kinds"), "status")

    def test_upstream_document_uses_state_not_status(self):
        self.write("docs/upstream/note.md",
                   "---\nkind: upstream\nstatus: proposed\n---\n\n# Upstream note\n")
        self.assert_finding(self.run_only("doc-kinds"), "state:")

    def test_upstream_state_outside_its_vocabulary(self):
        self.write("docs/upstream/note.md",
                   "---\nkind: upstream\nstate: bogus\n---\n\n# Upstream note\n")
        finding = self.assert_finding(self.run_only("doc-kinds"), "state 'bogus' is not")
        self.assertIn("landed-upstream", finding.message)

    def test_upstream_document_with_a_state_is_clean(self):
        self.write("docs/upstream/note.md",
                   "---\nkind: upstream\nstate: submitted\n---\n\n# Upstream note\n")
        self.assert_clean(self.run_only("doc-kinds"))

    def test_informative_kind_carrying_a_status(self):
        self.edit("docs/development-process.md", "kind: guide", "kind: guide\nstatus: draft")
        self.assert_finding(self.run_only("doc-kinds"), "informative", level="WARN")

    def test_severity_override_turns_the_missing_kind_into_an_error(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "doc-kinds: warn", "doc-kinds: error")
        self.write("docs/notes.md", "# Notes\n\nProse.\n")
        self.assert_finding(self.run_only("doc-kinds"), "no kind")

    def test_a_template_file_is_checked(self):
        self.write("docs/plans/_template.md", "# Plan template\n\nFill this in.\n")
        self.assert_finding(self.run_only("doc-kinds"), "no kind", level="WARN")

    def test_every_document_waived_is_not_a_family_that_ran(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            path.write_text("<!-- sdd-check: allow doc-kinds -->\n" + text, encoding="utf-8")
        report = self.run_only("doc-kinds")
        self.assertEqual("every document is waived", report.families_skipped.get("doc-kinds"))
        self.assertNotIn("doc-kinds", report.families_run)

    def test_frontmatter_after_a_leading_html_comment_is_accepted(self):
        self.write("docs/notes.md",
                   "<!-- generated: do not edit -->\n---\nkind: guide\n---\n\n# Notes\n")
        self.assert_clean(self.run_only("doc-kinds"))


# ---------------------------------------------------------------------------
# rfc2119
# ---------------------------------------------------------------------------
GUIDE_REL = "docs/development-process.md"
REQ_REL = "docs/requirements/REQ-FOUND-001.md"
NORMATIVE_SENTENCE = "The service MUST refuse a start with a declared variable absent."


class TestProseHelpers(unittest.TestCase):
    def test_waivers_names_every_family_in_the_comment(self):
        text = "# Title\n\n<!-- sdd-check: allow rfc2119, one-home -->\n\nProse.\n"
        self.assertEqual({"rfc2119", "one-home"}, sdd_check.waivers(text))

    def test_waivers_of_a_document_without_one(self):
        self.assertEqual(set(), sdd_check.waivers("# Title\n\nProse.\n"))

    def test_normalise_sentence_strips_markup_and_trailing_punctuation(self):
        self.assertEqual(
            "the service must read the config file",
            sdd_check.normalise_sentence("The *service* **MUST** read the `[config](x.md)` file."),
        )

    def test_keyword_sentences_carry_their_line_and_skip_keyword_free_prose(self):
        text = "# Title\n\nPlain prose here.\n\nThe gate MUST refuse the start.\n"
        self.assertEqual([(5, "The gate MUST refuse the start.")], sdd_check.keyword_sentences(text))

    def test_keyword_re_matches_whole_upper_case_words(self):
        found = sdd_check.KEYWORD_RE.findall(
            "MUST MUST NOT SHALL SHALL NOT SHOULD SHOULD NOT REQUIRED RECOMMENDED MAY OPTIONAL"
        )
        self.assertEqual(
            ["MUST", "MUST NOT", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT",
             "REQUIRED", "RECOMMENDED", "MAY", "OPTIONAL"],
            found,
        )

    def test_keyword_re_ignores_a_longer_word_and_lower_case(self):
        self.assertEqual([], sdd_check.KEYWORD_RE.findall("MAYBE must MUSTARD shall"))


class TestRfc2119Family(BaselineCase):
    def test_keyword_in_a_requirement(self):
        self.edit(REQ_REL, "- A start with every declared variable set is accepted.",
                  "- " + NORMATIVE_SENTENCE)
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119")

    def test_keyword_in_a_plan(self):
        self.edit(PLAN_REL, "- [x] Read the declared variables when the service starts.",
                  "- [x] " + NORMATIVE_SENTENCE)
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119")

    def test_keyword_in_an_adr(self):
        self.write("docs/adr/ADR-001-environment.md",
                   "---\nkind: adr\nstatus: accepted\n---\n\n# ADR-001 — Environment\n\n"
                   + NORMATIVE_SENTENCE + "\n")
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119")

    def test_keyword_in_a_reference(self):
        self.write("docs/reference/variables.md",
                   "---\nkind: reference\n---\n\n# Variables\n\n" + NORMATIVE_SENTENCE + "\n")
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119")

    def test_keyword_in_a_guide_warns_by_default(self):
        self.edit(GUIDE_REL, "Write the specification first",
                  NORMATIVE_SENTENCE + " Write the specification first")
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119", level="WARN")

    def test_keyword_in_a_guide_errors_when_the_family_is_error(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "rfc2119: warn", "rfc2119: error")
        self.edit(GUIDE_REL, "Write the specification first",
                  NORMATIVE_SENTENCE + " Write the specification first")
        self.assert_finding(self.run_only("rfc2119"), "RFC-2119")

    def test_a_waived_guide_is_skipped_and_counted(self):
        self.edit(GUIDE_REL, "# Development process",
                  "<!-- sdd-check: allow rfc2119 -->\n\n# Development process")
        self.edit(GUIDE_REL, "Write the specification first",
                  NORMATIVE_SENTENCE + " Write the specification first")
        report = self.run_only("rfc2119")
        self.assert_clean(report)
        self.assertIn(GUIDE_REL, report.waived["rfc2119"])

    def test_specification_section_without_a_keyword(self):
        self.edit(SPEC_REL, "The service MUST refuse to start when a declared variable is absent.\n",
                  "The service MUST refuse to start when a declared variable is absent.\n"
                  "\n## §2 — Parity\n\nThe two manifests carry the same version.\n")
        self.assert_finding(self.run_only("rfc2119"), "no RFC-2119 keyword", level="WARN")

    def test_lower_case_modal_in_a_keyword_free_sentence(self):
        self.edit(SPEC_REL, "This document owns how the service reads its environment.",
                  "This document owns how the service reads its environment.\n\n"
                  "The gate must exit non-zero.")
        self.assert_finding(self.run_only("rfc2119"), "lower-case", level="WARN")

    def test_malformed_keyword_form(self):
        self.edit(SPEC_REL, "The service MUST refuse to start when a declared variable is absent.",
                  "The refusal is MUST when a declared variable is absent.")
        self.assert_finding(self.run_only("rfc2119"), "malformed")

    def test_keywords_outside_prose_are_not_counted(self):
        self.write("docs/notes.md",
                   "---\nkind: guide\nnote: MUST\n---\n\n# Notes\n\n"
                   "A fenced block:\n\n```\nThe service MUST refuse.\n```\n\n"
                   "An inline `MUST` span.\n\n<!-- MUST in a comment -->\n")
        self.assert_clean(self.run_only("rfc2119"))

    def test_maybe_is_not_a_keyword(self):
        self.write("docs/notes.md",
                   "---\nkind: guide\n---\n\n# Notes\n\nMAYBE the service refuses the start.\n")
        self.assert_clean(self.run_only("rfc2119"))

    def test_no_document_declares_a_kind(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            path.write_text(
                "\n".join(l for l in text.split("\n") if not l.startswith("kind:")),
                encoding="utf-8",
            )
        report = self.run_only("rfc2119")
        self.assertEqual("no document declares a kind", report.families_skipped.get("rfc2119"))
        self.assertNotIn("rfc2119", report.families_run)

    def test_every_document_waived_is_not_a_family_that_ran(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            path.write_text("<!-- sdd-check: allow rfc2119 -->\n" + text, encoding="utf-8")
        report = self.run_only("rfc2119")
        self.assertEqual("every document is waived", report.families_skipped.get("rfc2119"))
        self.assertNotIn("rfc2119", report.families_run)

    def test_a_specification_without_sections_skips_that_rule(self):
        self.edit(SPEC_REL, "## §1 — Boundary (REQ-FOUND-001)", "## Boundary")
        report = self.run_only("rfc2119")
        self.assertIn("rfc2119", report.families_run)
        self.assertIn("§", report.families_skipped.get("rfc2119", ""))


# ---------------------------------------------------------------------------
# one-home
# ---------------------------------------------------------------------------
PARITY_REL = "docs/specifications/parity.md"
SPEC_SENTENCE = "The service MUST refuse to start when a declared variable is absent."
PARITY_HEAD = """---
kind: specification
spec: SPEC-PARITY
status: draft
mode: spec-first
---

# SPEC-PARITY — Parity

## §1 — Parity

**Implements:** REQ-FOUND-001

"""


class TestOneHomeFamily(BaselineCase):
    def second_specification(self, body):
        self.write(PARITY_REL, PARITY_HEAD + body)

    def test_the_same_sentence_in_two_specifications(self):
        self.second_specification(SPEC_SENTENCE + "\n")
        finding = self.assert_finding(self.run_only("one-home"), "one home")
        self.assertEqual(
            "docs/specifications/env.md:%d" % self.line_of(SPEC_REL, SPEC_SENTENCE),
            finding.anchor,
        )
        self.assertIn(
            "%s:%d" % (PARITY_REL, self.line_of(PARITY_REL, SPEC_SENTENCE)), finding.message
        )

    def test_emphasis_and_a_missing_full_stop_still_duplicate(self):
        self.second_specification(
            "The service **MUST** refuse to start when a declared variable is absent\n"
        )
        self.assert_finding(self.run_only("one-home"), PARITY_REL)

    def test_a_five_word_sentence_is_below_the_floor(self):
        self.edit(SPEC_REL, SPEC_SENTENCE, "The gate MUST exit non-zero.")
        self.second_specification("The gate MUST exit non-zero.\n")
        self.assert_clean(self.run_only("one-home"))

    def test_a_specification_sentence_copied_into_a_requirement(self):
        self.edit(
            REQ_REL,
            "- A start with a declared variable absent is refused, and the refusal names the variable.",
            "- " + SPEC_SENTENCE,
        )
        finding = self.assert_finding(self.run_only("one-home"), "duplicated normative prose")
        self.assertEqual(
            "%s:%d" % (REQ_REL, self.line_of(REQ_REL, SPEC_SENTENCE)), finding.anchor
        )

    def test_the_implements_marker_is_never_a_sentence(self):
        self.second_specification(
            "The two manifests MUST carry the same version at every release.\n"
        )
        self.assert_clean(self.run_only("one-home"))
        for text in ((self.tmp / SPEC_REL).read_text(), (self.tmp / PARITY_REL).read_text()):
            found = [s for _, s in sdd_check.sentences(text)]
            self.assertNotIn("**Implements:** REQ-FOUND-001", found)

    def test_every_document_waived_is_not_a_family_that_ran(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            path.write_text("<!-- sdd-check: allow one-home -->\n" + text, encoding="utf-8")
        report = self.run_only("one-home")
        self.assertEqual("every document is waived", report.families_skipped.get("one-home"))
        self.assertNotIn("one-home", report.families_run)

    def test_a_repository_without_specifications_skips_the_family(self):
        (self.tmp / SPEC_REL).unlink()
        report = self.run_only("one-home")
        self.assertIn("specification", report.families_skipped.get("one-home", ""))
        self.assertNotIn("one-home", report.families_run)


# ---------------------------------------------------------------------------
# links
# ---------------------------------------------------------------------------
SPEC_INDEX_REL = "docs/specifications/README.md"


class TestLinksFamily(BaselineCase):
    def guide_link(self, target):
        """Put one inline link into the guide at the top of docs/."""
        self.edit(
            GUIDE_REL,
            "Write the specification first",
            "See [x](%s). Write the specification first" % target,
        )

    def test_a_target_that_does_not_exist(self):
        self.guide_link("../missing.md")
        self.assert_finding(self.run_only("links"), "no such file")

    def test_a_fragment_that_resolves_to_nothing(self):
        self.edit(SPEC_INDEX_REL, "[`SPEC-ENV`](env.md)", "[`SPEC-ENV`](env.md#nope)")
        self.assert_finding(self.run_only("links"), "fragment")

    def test_a_fragment_that_resolves_to_a_heading(self):
        self.edit(
            SPEC_INDEX_REL, "[`SPEC-ENV`](env.md)", "[`SPEC-ENV`](env.md#1--boundary-req-found-001)"
        )
        self.assert_clean(self.run_only("links"))

    def test_a_bare_fragment_in_the_same_file(self):
        self.guide_link("#development-process")
        self.assert_clean(self.run_only("links"))

    def test_a_bare_fragment_that_resolves_to_nothing(self):
        self.guide_link("#zone")
        self.assert_finding(self.run_only("links"), "fragment")

    def test_an_explicit_anchor_counts_as_a_fragment(self):
        self.edit(GUIDE_REL, "# Development process", '<a id="legacy-zone"></a>\n\n# Development process')
        self.guide_link("#legacy-zone")
        self.assert_clean(self.run_only("links"))

    def test_a_host_absolute_target(self):
        self.guide_link("/etc/hosts")
        self.assert_finding(self.run_only("links"), "host-absolute")

    def test_schemes_and_protocol_relative_targets_are_skipped(self):
        self.edit(
            GUIDE_REL,
            "Write the specification first",
            "See [a](https://example.org/x), [b](mailto:someone@example.org) and "
            "[c](//cdn.example.org/x.js). Write the specification first",
        )
        self.assert_clean(self.run_only("links"))

    def test_a_link_inside_a_fenced_block_is_skipped(self):
        self.edit(
            GUIDE_REL,
            "Write the specification first",
            "```\nSee [x](../missing.md).\n```\n\nWrite the specification first",
        )
        self.assert_clean(self.run_only("links"))

    def test_a_reference_definition_is_checked(self):
        self.edit(
            SPEC_INDEX_REL, "# Specifications", "# Specifications\n\n[spec]: env.md#missing"
        )
        self.assert_finding(self.run_only("links"), "fragment")

    def test_a_link_in_the_root_agents_file(self):
        self.edit(
            "AGENTS.md", "docs/development-process.md", "docs/no-such-process.md"
        )
        finding = self.assert_finding(self.run_only("links"), "no such file")
        self.assertTrue(finding.anchor.startswith("AGENTS.md:"), finding.anchor)

    def test_a_link_in_the_root_readme(self):
        self.write("README.md", "# Project\n\nSee [x](docs/nope.md).\n")
        finding = self.assert_finding(self.run_only("links"), "no such file")
        self.assertTrue(finding.anchor.startswith("README.md:"), finding.anchor)

    def test_a_target_that_resolves_outside_the_repository(self):
        self.guide_link("../../etc/hosts")
        self.assert_finding(self.run_only("links"), "target resolves outside the repository")

    def test_a_declared_path_outside_docs_is_scanned(self):
        (self.tmp / "docs/adr").rename(self.tmp / "decisions")
        self.edit(sdd_check.DESCRIPTOR_REL, "    adr: docs/adr", "    adr: decisions")
        self.edit("decisions/README.md", "# Decision records", "# Decision records\n\n[x](gone.md)")
        finding = self.assert_finding(self.run_only("links"), "no such file")
        self.assertTrue(finding.anchor.startswith("decisions/README.md:"), finding.anchor)

    def test_an_exclusion_glob_skips_the_file_and_is_printed(self):
        self.edit(PLAN_REL, "## Tasks", "## Tasks\n\n[x](gone.md)")
        self.assert_finding(self.run_only("links"), "no such file")
        self.edit(sdd_check.DESCRIPTOR_REL, "      exclude: []", '      exclude: ["docs/plans/**"]')
        report = self.run_only("links")
        self.assert_clean(report)
        self.assertEqual(["docs/plans/**"], report.link_exclusions)
        self.assertIn("link exclusions: docs/plans/**", report.render(self.tmp).split("\n"))

    def test_a_percent_encoded_space_is_decoded(self):
        self.write("docs/a file.md", "---\nkind: guide\n---\n\n# A file\n")
        self.guide_link("a%20file.md")
        self.assert_clean(self.run_only("links"))

    def test_a_percent_encoded_target_that_does_not_exist(self):
        self.guide_link("no%20file.md")
        self.assert_finding(self.run_only("links"), "no such file: no file.md")

    def test_a_waived_document_is_skipped_and_counted(self):
        self.edit(
            GUIDE_REL, "# Development process",
            "<!-- sdd-check: allow links -->\n\n# Development process",
        )
        self.guide_link("../missing.md")
        report = self.run_only("links")
        self.assert_clean(report)
        self.assertEqual([GUIDE_REL], report.waived["links"])

    def test_every_document_waived_is_not_a_family_that_ran(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")) + [self.tmp / "AGENTS.md"]:
            text = path.read_text(encoding="utf-8")
            path.write_text("<!-- sdd-check: allow links -->\n" + text, encoding="utf-8")
        report = self.run_only("links")
        self.assertEqual("every document is waived", report.families_skipped.get("links"))
        self.assertNotIn("links", report.families_run)

    def test_a_repository_with_no_document_skips_the_family(self):
        for path in sorted((self.tmp / "docs").rglob("*.md")):
            path.unlink()
        (self.tmp / "AGENTS.md").unlink()
        report = self.run_only("links")
        self.assertIn("links", report.families_skipped)
        self.assertNotIn("links", report.families_run)


# ---------------------------------------------------------------------------
# changelog
# ---------------------------------------------------------------------------
CHANGELOG_REL = "CHANGELOG.md"
CHANGELOG_BULLET = (
    "- Config: the service reads every declared variable from the environment when it starts."
)
OLDER_SECTION = "\n## [0.1.0] - 2026-01-01\n\n### Added\n- Tools: fixed the path. Also fixed the name.\n"


class TestChangelogFamily(BaselineCase):
    def bullet(self, text):
        self.edit(CHANGELOG_REL, CHANGELOG_BULLET, text)

    def test_a_bullet_over_the_word_budget(self):
        self.bullet("- Tools: " + " ".join(["word"] * 40))
        finding = self.assert_finding(self.run_only("changelog"), "words", level="WARN")
        self.assertTrue(finding.anchor.startswith("CHANGELOG.md:"), finding.anchor)

    def test_a_bullet_with_a_second_sentence(self):
        self.bullet("- Tools: fixed the path. Also fixed the name.")
        self.assert_finding(self.run_only("changelog"), "one sentence", level="WARN")

    def test_a_bullet_that_argues_its_case(self):
        self.bullet("- Tools: the gate reads the descriptor because the old path rotted.")
        self.assert_finding(self.run_only("changelog"), "rationale", level="WARN")

    def test_a_bullet_that_is_an_inventory(self):
        self.bullet("- Tools: `a`, `b`, `c`, `d` and `e` are added.")
        self.assert_finding(self.run_only("changelog"), "inventory", level="WARN")

    def test_a_continuation_line_belongs_to_its_bullet(self):
        self.bullet("- Tools: fixed the path.\n  Also fixed the name.")
        self.assert_finding(self.run_only("changelog"), "one sentence", level="WARN")

    def test_an_indented_sub_bullet_is_not_folded_into_its_parent(self):
        self.bullet("- Tools: the gate reads the descriptor.\n  - A sub-point. And another.")
        self.assert_clean(self.run_only("changelog"))

    def test_an_older_section_is_left_alone_without_the_flag(self):
        self.bullet(CHANGELOG_BULLET + "\n" + OLDER_SECTION)
        self.assert_clean(self.run_only("changelog"))

    def test_an_older_section_is_linted_with_the_flag(self):
        self.bullet(CHANGELOG_BULLET + "\n" + OLDER_SECTION)
        report = sdd_check.run_check(self.tmp, only=["changelog"], changelog_all=True)
        self.assert_finding(report, "one sentence", level="WARN")

    def test_no_unreleased_section_is_a_note_and_the_family_still_ran(self):
        self.edit(CHANGELOG_REL, "## [Unreleased]", "## [0.1.0] - 2026-01-01")
        report = self.run_only("changelog")
        self.assert_finding(report, "no Unreleased section", level="NOTE")
        self.assertIn("changelog", report.families_run)
        self.assertEqual(0, report.exit_code())

    def test_a_wider_budget_lifts_the_word_count(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "      max_words: 35", "      max_words: 50")
        self.bullet("- Tools: " + " ".join(["word"] * 40))
        self.assert_clean(self.run_only("changelog"))

    def test_a_changelog_path_that_names_no_file(self):
        self.edit(sdd_check.DESCRIPTOR_REL, "      path: CHANGELOG.md", "      path: docs/CHANGELOG.md")
        self.assert_finding(self.run_only("changelog"), "docs/CHANGELOG.md")

    def test_a_waived_changelog_is_skipped_and_counted(self):
        self.edit(CHANGELOG_REL, "# Changelog", "# Changelog\n\n<!-- sdd-check: allow changelog -->")
        self.bullet("- Tools: fixed the path. Also fixed the name.")
        report = self.run_only("changelog")
        self.assert_clean(report)
        self.assertEqual([CHANGELOG_REL], report.waived["changelog"])
        self.assertNotIn("changelog", report.families_run)

    def test_an_unreleased_section_without_a_bullet_skips_the_rules(self):
        self.bullet("")
        report = self.run_only("changelog")
        self.assertIn("changelog", report.families_run)
        self.assertIn("bullet", report.families_skipped.get("changelog", ""))


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

    def test_waived_families_are_counted_in_the_summary(self):
        self.write(
            "docs/notes.md",
            "<!-- sdd-check: allow doc-kinds -->\n\n# Notes\n\nProse with no frontmatter.\n",
        )
        report = self.run_only("doc-kinds")
        self.assert_clean(report)
        self.assertEqual(["docs/notes.md"], report.waived["doc-kinds"])
        lines = report.render(self.tmp).split("\n")
        self.assertIn("waived: doc-kinds (1 files)", lines)
        families_at = [i for i, l in enumerate(lines) if l.startswith("families run: ")][0]
        self.assertEqual(families_at + 1, lines.index("waived: doc-kinds (1 files)"))

    def test_no_waiver_line_when_nothing_is_waived(self):
        # Nothing in the baseline waives doc-kinds, so that family prints no waiver line.
        self.assertNotIn("waived:", self.run_only("doc-kinds").render(self.tmp))

    def test_the_baseline_waiver_is_named_in_a_full_run(self):
        report = sdd_check.run_check(self.tmp, only=None, changelog_all=False)
        self.assertIn("waived: rfc2119 (1 files)", report.render(self.tmp).split("\n"))
        self.assertEqual(["docs/specifications/README.md"], report.waived["rfc2119"])

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

    def test_generate_command_is_clean_on_a_current_baseline(self):
        code, out = self.run_main(["generate", "--root", str(self.tmp)])
        self.assertEqual(0, code, out)
        self.assertEqual("", out.strip())

    def test_generate_verify_command_is_clean_on_a_current_baseline(self):
        code, out = self.run_main(["generate", "--verify", "--root", str(self.tmp)])
        self.assertEqual(0, code, out)
        self.assertEqual("", out.strip())

    def test_context_command_prints_the_bundle(self):
        code, out = self.run_main(["context", "REQ-FOUND-001", "--root", str(self.tmp)])
        self.assertEqual(0, code, out)
        self.assertIn("Index row", out)
        self.assertIn("tests/env_test.py", out)

    def test_context_command_unknown_id_returns_two(self):
        code, out = self.run_main(["context", "REQ-FOUND-999", "--root", str(self.tmp)])
        self.assertEqual(2, code, out)
        self.assertIn("no record", out)

    def test_selftest_command_returns_zero(self):
        code, out = self.run_main(["selftest", "--root", str(self.tmp)])
        self.assertEqual(0, code, out)
        self.assertIn("selftest: OK", out)


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
        self.edit(
            INDEX_REL,
            "| ID | Title | Spec | Stability | Implementation |",
            "| ID | Title | Spec | Stability | Build |",
        )
        self.edit(INDEX_REL, "| Draft | shipped |", "| Draft | planned |")
        self.assert_finding(self.run_only("index-sync"), "Implementation", family="index-sync")

    def test_an_unnamed_axis_in_a_narrow_table_warns_instead_of_guessing(self):
        self.edit(
            INDEX_REL, "| ID | Title | Spec | Stability | Implementation |", "| ID | Title | Implementation |"
        )
        self.edit(INDEX_REL, "|---|---|---|---|---|", "|---|---|---|")
        self.edit(
            INDEX_REL,
            "| Environment boundary | [`SPEC-ENV §1`](../specifications/env.md#1--boundary-req-found-001) "
            "| Draft | shipped |",
            "| Environment boundary | shipped |",
        )
        report = self.run_only("index-sync")
        self.assertEqual([], self.levelled(report, "ERROR"), report.render(self.tmp))
        finding = self.assert_finding(
            report, "the index table names no Stability column", level="WARN"
        )
        self.assertEqual("index-sync", finding.family)
        self.assertEqual("docs/requirements/README.md:11", finding.anchor)

    def test_the_five_column_template_shape_is_clean(self):
        self.assert_clean(self.run_only("index-sync"))

    def test_last_two_columns_when_no_header_matches(self):
        self.edit(
            INDEX_REL,
            "| ID | Title | Spec | Stability | Implementation |",
            "| ID | Title | Spec | Stage | Build |",
        )
        self.edit(INDEX_REL, "| Draft | shipped |", "| Draft | planned |")
        self.assert_finding(self.run_only("index-sync"), "Implementation", family="index-sync")


class TestPlansRules(GitCase):
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


class TestTreeToMapUnderGit(GitCase):
    def test_an_ignored_directory_is_not_scanned(self):
        self.write(".gitignore", "scratch/\n")
        self.write("scratch/note.py", "# REQ-FOUND-077\n")
        self.init_git()
        self.commit("baseline")
        self.assert_clean(self.run_only("tree-to-map"))

    def test_an_untracked_file_that_is_not_ignored_is_scanned(self):
        self.write("scratch/note.py", "# REQ-FOUND-077\n")
        self.init_git()
        self.commit("baseline")
        self.assert_finding(self.run_only("tree-to-map"), "unknown identifier cited", level="WARN")


# ---------------------------------------------------------------------------
# Generators: the requirements-index, specifications-index and adr-index tables, and
# the requirement detail-file status lines
# ---------------------------------------------------------------------------
EXPECTED_REQUIREMENTS_INDEX = (
    "| ID | Title | Spec | Stability | Implementation |\n"
    "|---|---|---|---|---|\n"
    "| [REQ-FOUND-001](REQ-FOUND-001.md) | Environment boundary | "
    "[`SPEC-ENV §1`](../specifications/env.md#1--boundary-req-found-001) | Draft | shipped |"
)


class TestGenerators(BaselineCase):
    def ctx(self):
        desc = sdd_check.Descriptor.load(self.tmp)
        return sdd_check.Context(self.tmp, desc, sdd_check.load_map(desc))

    def test_render_requirements_index_matches_the_fixture(self):
        self.assertEqual(EXPECTED_REQUIREMENTS_INDEX, sdd_check.render_requirements_index(self.ctx()))

    def test_id_cell_is_plain_when_the_detail_file_is_missing(self):
        (self.tmp / REQ_REL).unlink()
        rendered = sdd_check.render_requirements_index(self.ctx())
        self.assertIn("| REQ-FOUND-001 | Environment boundary |", rendered)
        self.assertNotIn("[REQ-FOUND-001]", rendered)

    def test_generate_rewrites_stale_blocks_and_detail_frontmatter(self):
        self.edit(INDEX_REL, "Draft | shipped |", "Landed | proposed |")
        self.edit(REQ_REL, "status: draft", "status: stable")
        code, written = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(0, code)
        self.assertIn("docs/requirements/README.md", written)
        self.assertIn("docs/requirements/REQ-FOUND-001.md", written)
        self.assertIn(EXPECTED_REQUIREMENTS_INDEX, (self.tmp / INDEX_REL).read_text(encoding="utf-8"))
        self.assertIn("status: draft", (self.tmp / REQ_REL).read_text(encoding="utf-8"))
        self.assertNotIn("status: stable", (self.tmp / REQ_REL).read_text(encoding="utf-8"))

    def test_generate_a_second_time_writes_nothing(self):
        self.edit(INDEX_REL, "Draft | shipped |", "Landed | proposed |")
        sdd_check.generate(self.tmp, verify=False)
        code, written = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(0, code)
        self.assertEqual([], written)

    def test_generate_verify_reports_a_diff_when_stale_and_nothing_when_current(self):
        self.edit(INDEX_REL, "Draft | shipped |", "Landed | proposed |")
        code, diff = sdd_check.generate(self.tmp, verify=True)
        self.assertEqual(1, code)
        self.assertTrue(any("Landed | proposed" in line for line in diff), diff)
        sdd_check.generate(self.tmp, verify=False)
        code, diff = sdd_check.generate(self.tmp, verify=True)
        self.assertEqual(0, code)
        self.assertEqual([], diff)

    def test_generate_reuses_checks_descriptor_failure_report(self):
        (self.tmp / sdd_check.DESCRIPTOR_REL).unlink()
        code, lines = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(2, code)
        self.assertEqual(2, len(lines), lines)
        self.assertTrue(lines[1].startswith("sdd-check: FAILED — "), lines[1])

    def test_a_block_in_agents_md_links_relative_to_its_own_home(self):
        agents = (self.tmp / "AGENTS.md").read_text(encoding="utf-8")
        self.write(
            "AGENTS.md",
            agents + "\n<!-- sdd:generated requirements-index -->\n\n<!-- /sdd:generated -->\n",
        )
        code, written = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(0, code, written)
        self.assertIn("AGENTS.md", written)
        text = (self.tmp / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("[REQ-FOUND-001](docs/requirements/REQ-FOUND-001.md)", text)
        self.assertIn("docs/specifications/env.md#1--boundary-req-found-001", text)
        report = sdd_check.run_check(self.tmp, only=["links", "generated"], changelog_all=False)
        self.assert_clean(report)

    def test_generate_reports_a_skipped_unclosed_block_and_exits_one(self):
        self.write(
            "docs/requirements/orphan.md",
            "---\nkind: reference\n---\n\n<!-- sdd:generated requirements-index -->\n\nno close\n",
        )
        code, lines = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(1, code, lines)
        self.assertTrue(
            any("unclosed generated block" in line for line in lines), lines
        )

    def test_generate_reports_a_skipped_unknown_block_and_exits_one(self):
        self.write(
            "docs/requirements/orphan.md",
            "---\nkind: reference\n---\n\n<!-- sdd:generated plans-index -->\n\n<!-- /sdd:generated -->\n",
        )
        code, lines = sdd_check.generate(self.tmp, verify=False)
        self.assertEqual(1, code, lines)
        self.assertTrue(any("unknown block" in line for line in lines), lines)


class TestGeneratedFamily(BaselineCase):
    def test_hand_edited_cell_is_an_error(self):
        self.edit(INDEX_REL, "Environment boundary", "Environment boundary, hand-edited")
        self.assert_finding(self.run_only("generated"), "hand-edited or stale")

    def test_unclosed_marker_is_an_error(self):
        self.write(
            "docs/requirements/orphan.md",
            "---\nkind: reference\n---\n\n<!-- sdd:generated requirements-index -->\n\nno closing marker\n",
        )
        self.assert_finding(self.run_only("generated"), "unclosed")

    def test_unknown_block_name_is_an_error(self):
        self.write(
            "docs/requirements/orphan.md",
            "---\nkind: reference\n---\n\n<!-- sdd:generated plans-index -->\n\n<!-- /sdd:generated -->\n",
        )
        self.assert_finding(self.run_only("generated"), "unknown block")

    def test_no_generated_blocks_anywhere_is_skipped(self):
        self.write("docs/requirements/README.md", "---\nkind: guide\n---\n\n# Requirements\n")
        self.write("docs/specifications/README.md", "---\nkind: guide\n---\n\n# Specifications\n")
        self.write("docs/adr/README.md", "---\nkind: guide\n---\n\n# Decision records\n")
        report = self.run_only("generated")
        self.assertEqual("no generated blocks", report.families_skipped.get("generated"))
        self.assertNotIn("generated", report.families_run)


# ---------------------------------------------------------------------------
# The context bundle
# ---------------------------------------------------------------------------
class TestContextBundle(BaselineCase):
    def ctx(self):
        desc = sdd_check.Descriptor.load(self.tmp)
        return sdd_check.Context(self.tmp, desc, sdd_check.load_map(desc))

    def test_bundle_headings_are_in_order_with_content(self):
        bundle = sdd_check.context_bundle(self.ctx(), "REQ-FOUND-001")
        headings = [
            "Index row",
            "Traceability record",
            "Canonical section",
            "Acceptance criteria",
            "Plans",
            "Tests citing it",
            "Open strands",
        ]
        positions = [bundle.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions), bundle)
        self.assertIn("**Implements:** REQ-FOUND-001", bundle)
        self.assertIn("A start with every declared variable set is accepted.", bundle)
        self.assertIn("docs/plans/2026-01-01-env.md: done", bundle)
        self.assertIn("tests/env_test.py", bundle)
        self.assertIn("Open strands\nnone", bundle)

    def test_unknown_id_returns_two_via_run_context(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = sdd_check.run_context(self.tmp, "REQ-FOUND-999")
        self.assertEqual(2, code)
        self.assertIn("no record", buffer.getvalue())


# ---------------------------------------------------------------------------
# The built-in selftest
# ---------------------------------------------------------------------------
class TestSelftest(unittest.TestCase):
    def test_selftest_returns_zero(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = sdd_check.selftest()
        self.assertEqual(0, code, buffer.getvalue())
        self.assertIn("selftest: OK", buffer.getvalue())

    def test_selftest_is_mutation_detectable(self):
        original = sdd_check.CHECKS["links"]
        sdd_check.CHECKS["links"] = lambda ctx, report: None
        try:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = sdd_check.selftest()
        finally:
            sdd_check.CHECKS["links"] = original
        self.assertEqual(1, code)
        self.assertIn("FAIL link-dead", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()

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

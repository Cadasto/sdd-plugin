"""Both tools refuse a Python older than 3.11 with one line on standard error and exit 2.

The check sits at the top of each file, so an older interpreter must still parse the whole file to
reach it. These tests run each file as a script with ``sys.version_info`` replaced, and parse each
file with the Python 3.9 grammar, the oldest a host may still carry. That parse is best effort: it
refuses ``match``, ``except*`` and type parameters, but not every newer form, such as a 3.12 f-string.
"""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
TOOLS = ("sdd-check", "sdd-pr")

# Runs one tool's file as __main__ with --help, after replacing the version the floor check reads
# and the interpreter path its message names.
PROBE = """
import collections, runpy, sys
Version = collections.namedtuple("Version", "major minor micro releaselevel serial")
sys.version_info = Version({major}, {minor}, {micro}, "final", 0)
sys.executable = "/usr/bin/python3"
sys.argv = [{path!r}, "--help"]
runpy.run_path({path!r}, run_name="__main__")
"""


def run_as(tool, version):
    path = str(TOOLS_DIR / (tool + ".py"))
    code = PROBE.format(major=version[0], minor=version[1], micro=version[2], path=path)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)


class TestPythonFloor(unittest.TestCase):

    def test_an_older_python_gets_one_line_naming_it_and_exit_2(self):
        for tool in TOOLS:
            for version in ((3, 9, 6), (3, 10, 14)):
                with self.subTest(tool=tool, version=version):
                    proc = run_as(tool, version)
                    self.assertEqual(2, proc.returncode, proc.stderr)
                    self.assertEqual("", proc.stdout)
                    self.assertEqual("%s needs Python 3.11 or newer; this is Python %d.%d.%d (/usr/bin/python3).\n"
                                     % ((tool,) + version), proc.stderr)

    def test_python_3_11_passes_the_floor(self):
        for tool in TOOLS:
            with self.subTest(tool=tool):
                proc = run_as(tool, (3, 11, 0))
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIn("usage: " + tool, proc.stdout)

    def test_each_tool_parses_with_the_python_3_9_grammar(self):
        for tool in TOOLS:
            with self.subTest(tool=tool):
                source = (TOOLS_DIR / (tool + ".py")).read_text(encoding="utf-8")
                ast.parse(source, filename=tool + ".py", feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()

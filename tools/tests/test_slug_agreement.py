"""Slug-agreement test.

scripts/validate.py's ``_github_slug()`` and tools/sdd-check.py's ``slugify()`` implement the
same GitHub heading-anchor rule as two independent, deliberately un-shared pieces of source — the
validator cannot import the tool, because the tool is a vendorable artefact a consuming repository
copies out on its own. That duplication is correct; this test is what keeps the two honest. It
pins agreement over a corpus of awkward headings so a future edit to either implementation that
quietly drifts from the other fails a test, rather than surfacing as a validator that blesses a
fragment the real gate would reject (or the reverse).

Both functions are loaded by path, the same way tools/tests/test_sdd_check.py loads sdd-check.py:
neither module is a package, and ``scripts/validate.py`` only runs its ``main()`` when
``__name__ == "__main__"``, which ``importlib.util`` never sets — loading it here has no side
effect beyond defining its functions and constants.
"""
import importlib.util
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
ROOT = TOOLS_DIR.parent

_VALIDATE_SPEC = importlib.util.spec_from_file_location("validate", ROOT / "scripts" / "validate.py")
validate = importlib.util.module_from_spec(_VALIDATE_SPEC)
_VALIDATE_SPEC.loader.exec_module(validate)

_SDD_CHECK_SPEC = importlib.util.spec_from_file_location("sdd_check", TOOLS_DIR / "sdd-check.py")
sdd_check = importlib.util.module_from_spec(_SDD_CHECK_SPEC)
_SDD_CHECK_SPEC.loader.exec_module(sdd_check)


class SlugAgreementTest(unittest.TestCase):
    """``validate._github_slug()`` and ``sdd_check.slugify()`` must slugify any heading
    identically — mirroring the gate's algorithm exactly is the whole point of the fix this test
    pins down. Every case below is asserted to AGREE. A case that must legitimately differ
    belongs here too, asserted explicitly (its own ``assertEqual``/``assertNotEqual`` spelling out
    both expected values) — never skipped, because a skipped case is exactly where drift hides."""

    # (label, heading) — one entry per awkward category the two rules must handle alike.
    CASES = (
        ("plain heading", "Plain Heading"),
        ("punctuation", "Punctuation! Heading?"),
        ("bare ampersand", "Fish & Chips"),
        ("ampersand html entity", "Fish &amp; Chips"),
        ("inline code span", "A `code span` heading"),
        ("trailing hash marks", "Trailing hashes ###"),
        ("multiple interior spaces", "Multiple    spaces   here"),
        ("leading and trailing whitespace", "   Leading and trailing whitespace   "),
        ("non-ascii accented letters", "Café Configuration"),
        ("non-ascii cjk", "中文标题"),
        ("emoji", "Heading with emoji 🎉 party"),
        ("leading digits", "1. Leading digits"),
        ("only punctuation", "!!!"),
        ("existing hyphen and underscore", "under_score-and-hyphen"),
        ("mixed case", "Mixed CASE Heading"),
        ("empty string", ""),
        ("whitespace only", "   \t  "),
    )

    def test_corpus_agrees(self):
        for label, heading in self.CASES:
            with self.subTest(label=label, heading=heading):
                validator_slug = validate._github_slug(heading)
                gate_slug = sdd_check.slugify(heading)
                self.assertEqual(
                    validator_slug,
                    gate_slug,
                    f"{label} ({heading!r}): validate._github_slug()={validator_slug!r} vs "
                    f"sdd_check.slugify()={gate_slug!r} — the two slug rules have drifted apart",
                )


if __name__ == "__main__":
    unittest.main()

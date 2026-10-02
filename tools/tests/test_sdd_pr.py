"""Unit tests for tools/sdd-pr.py.

The tool is a script, not a package, so it is loaded by path, as the gate's tests load the gate.
Every external call (git, gh, az) goes through ``sdd_pr.run_cli``; each test replaces it with a
``FakeCli`` that answers from routes and records every call. No test touches the network or a
real repository.
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("sdd_pr", TOOLS_DIR / "sdd-pr.py")
sdd_pr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sdd_pr)

REVIEW_MD = TOOLS_DIR.parent / "references" / "review.md"
HEAD = "b" * 40
MB = "a" * 40


def sample_file():
    """The findings-file sample in references/review.md § The findings file, verbatim."""
    text = REVIEW_MD.read_text(encoding="utf-8")
    start = text.index("```markdown\n# Findings") + len("```markdown\n")
    return text[start:text.index("```", start)]


class FakeCli:
    """Answers run_cli from ``(predicate(argv), output | callable(argv, stdin))`` routes."""

    def __init__(self, routes):
        self.routes = list(routes)
        self.calls = []

    def __call__(self, argv, stdin=None):
        self.calls.append((list(argv), stdin))
        for predicate, answer in self.routes:
            if predicate(argv):
                if isinstance(answer, Exception):
                    raise answer
                return answer(argv, stdin) if callable(answer) else answer
        raise AssertionError("unexpected call: %r" % (argv,))

    def called(self, *needles):
        return [argv for argv, _ in self.calls if all(n in argv for n in needles)]


def git(*words):
    """A predicate for a git call whose arguments contain ``words`` in order."""
    def predicate(argv):
        if not argv or argv[0] != "git":
            return False
        rest = argv[1:]
        if rest[:1] == ["-C"]:
            rest = rest[2:]
        while rest[:1] == ["-c"]:
            rest = rest[2:]
        return rest[: len(words)] == list(words)
    return predicate


def has(*needles):
    return lambda argv: all(n in argv for n in needles)


def _same_as_local(ref):
    return ref[len("origin/"):] if ref.startswith("origin/") else ref


def git_routes(branch="feat/x", head=HEAD, remote="git@github.com:o/r.git", names="", diff=""):
    return [
        (git("rev-parse", "--git-common-dir"), ".git\n"),
        (git("rev-parse", "--abbrev-ref", "HEAD"), branch + "\n"),
        (git("rev-parse", "HEAD"), head + "\n"),
        (git("rev-parse", "--verify", "--quiet"), lambda argv, _: _same_as_local(argv[-1].split("^")[0]) + "\n"),
        (git("merge-base", "--is-ancestor"), ""),
        (git("merge-base"), MB + "\n"),
        (git("symbolic-ref"), "origin/main\n"),
        (git("remote", "get-url", "origin"), remote + "\n"),
        (git("worktree", "list"), ""),
        (git("for-each-ref"), ""),
        (git("reflog"), "commit: work\nbranch: Created from HEAD\n"),
        (git("status", "--porcelain"), ""),
        (git("show"), sdd_pr.CliError("fatal: path not in that commit")),
        (git("diff", "--name-only"), names),
        (git("diff"), diff),
    ]


class RepoCase(unittest.TestCase):
    """A temporary repository root with an optional descriptor and findings file."""

    BRANCH = "feat/x"

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self._orig = sdd_pr.run_cli
        self.addCleanup(setattr, sdd_pr, "run_cli", self._orig)

    def descriptor(self, forge="auto", extra=""):
        path = self.root / "docs" / ".sdd.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sdd:\n  profile: formal\n  forge: %s   # comment\n%s" % (forge, extra), encoding="utf-8")

    def store(self, branch=None):
        return self.root / ".git" / "sdd" / "findings" / (sdd_pr.slug(branch or self.BRANCH) + ".md")

    def findings(self, text, branch=None):
        path = self.store(branch)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read_findings(self, branch=None):
        return self.store(branch).read_text(encoding="utf-8")

    def nothing_written(self):
        return not (self.root / ".sdd").exists() and not (self.root / ".git" / "sdd").exists()

    def use(self, routes):
        fake = FakeCli(routes)
        sdd_pr.run_cli = fake
        return fake

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sdd_pr.main(["--root", str(self.root)] + list(args))
        return code, out.getvalue(), err.getvalue()


FILE_OPEN_IMPORTANT = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open
- [ ] important · a.go:5 · the retry ignores the context · evidence: TestRetry hangs · fix: select on ctx.Done · by: claude

## Resolved

## Suggestions
""" % HEAD[:7]

FILE_CLEAN = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open

## Resolved
- [x] important · a.go:5 · the retry ignores the context · by: claude · fixed %s

## Suggestions
- a.go:9 · rename `n` to `count` · by: claude
""" % (HEAD[:7], HEAD[:7])


class TestFileModel(RepoCase):
    def test_parse_and_render_roundtrip(self):
        text = sample_file()
        fs = sdd_pr.parse(text)
        self.assertEqual(2, len(fs.open))
        self.assertEqual(["critical", "important"], [f.severity for f in fs.open])
        self.assertEqual(3, len(fs.resolved))
        fixed = [f for f in fs.resolved if f.status == "fixed"]
        declined = [f for f in fs.resolved if f.status == "declined"]
        deferred = [f for f in fs.resolved if f.status == "deferred"]
        self.assertEqual("4f0a1c2", fixed[0].fixed)
        self.assertTrue(declined[0].fields["declined"].startswith("the trap on line 3"))
        self.assertEqual("SPEC-AUTH § Known gaps", deferred[0].fields["deferred"])
        self.assertEqual(1, len(fs.suggestions))
        self.assertEqual(2, len(fs.reviewed))
        self.assertEqual("5893201111", fs.open[1].fields["forge"])
        self.assertEqual(text, sdd_pr.render(fs))

    def test_file_roundtrip_with_two_writers(self):
        fs = sdd_pr.parse(sample_file())
        # Agent A appends an open line at the end of ## Open, with a trailing space.
        text = sdd_pr.render(fs).replace(
            "\n\n## Resolved",
            "\n- [ ] important · b.go:3 · the loop never exits · by: cursor \n\n## Resolved",
        )
        # Agent B flips the critical line to fixed and moves it under ## Resolved, leaving a blank line.
        crit = [line for line in text.splitlines() if line.startswith("- [ ] critical")][0]
        text = text.replace(crit + "\n", "")
        text = text.replace("## Resolved\n", "## Resolved\n\n" + crit.replace("- [ ]", "- [x]") + " · fixed abc1234\n")
        fs2 = sdd_pr.parse(text)
        self.assertEqual(["important", "important"], [f.severity for f in fs2.open])
        self.assertEqual(4, len(fs2.resolved))
        self.assertIn("abc1234", [f.fixed for f in fs2.resolved])
        self.assertEqual("the loop never exits", fs2.open[-1].text)
        # A checkbox line with no severity is a malformed file, named by its line number.
        bad = text.replace("- [ ] important · b.go:3", "- [ ] b.go:3")
        lineno = [i for i, line in enumerate(bad.splitlines(), 1) if line.startswith("- [ ] b.go:3")][0]
        with self.assertRaises(sdd_pr.FileError) as caught:
            sdd_pr.parse(bad)
        self.assertIn("line %d" % lineno, str(caught.exception))
        self.findings(bad)
        self.descriptor(forge="none")
        self.use(git_routes())
        code, _, err = self.run_main("status")
        self.assertEqual(2, code)
        self.assertIn("line %d" % lineno, err)

    def test_a_line_is_filed_by_its_checkbox_wherever_it_stands(self):
        # Flipped in place under ## Open, as review.md § Resolution says to.
        flipped = FILE_OPEN_IMPORTANT.replace("- [ ] important · a.go:5", "- [x] important · a.go:5").replace(
            "by: claude\n", "by: claude · fixed abc1234\n", 1)
        fs = sdd_pr.parse(flipped)
        self.assertEqual(([], 1), (fs.open, len(fs.resolved)))
        self.assertIn("## Resolved\n- [x] important · a.go:5", sdd_pr.render(fs))
        # Appended at the end of the file by an outside reviewer, after ## Suggestions, with its Reviewed line.
        appended = FILE_CLEAN + "- [ ] critical · b.go:7 · leaks a handle · by: cursor\nReviewed abc1234 · 2026-09-30 · cursor: go-reviewer (1 of 1)\n"
        fs = sdd_pr.parse(appended)
        self.assertEqual(["critical"], [f.severity for f in fs.open])
        self.assertEqual(2, len(fs.reviewed))
        self.assertEqual(1, len(fs.suggestions))
        # An upper-case X is a fixed line, not a malformed one.
        fs = sdd_pr.parse(FILE_CLEAN.replace("- [x] important", "- [X] important"))
        self.assertEqual("fixed", fs.resolved[0].status)

    def test_a_sentence_that_looks_like_a_field_stays_the_sentence(self):
        line = "- [ ] important · a.go:1 · fixed width breaks the table · by: claude"
        finding = sdd_pr.parse_line(line, 1, "Open")
        self.assertEqual("fixed width breaks the table", finding.text)
        self.assertIsNone(finding.fixed)
        self.assertEqual(line, finding.render())

    def test_a_deferred_line_roundtrips_and_is_not_open(self):
        line = "- [~] important · a.go:5 · the retry ignores the context · by: claude · deferred: REQ-A-001 implementation: deferred"
        text = FILE_CLEAN.replace("\n\n## Suggestions", "\n" + line + "\n\n## Suggestions")
        fs = sdd_pr.parse(text)
        deferred = [f for f in fs.items if f.status == "deferred"]
        self.assertEqual(1, len(deferred))
        self.assertEqual("REQ-A-001 implementation: deferred", deferred[0].fields["deferred"])
        self.assertIn(deferred[0], fs.resolved)
        self.assertEqual([], fs.open)
        self.assertEqual(line, deferred[0].render())
        self.assertEqual(text, sdd_pr.render(fs))
        self.assertEqual("deferred: REQ-A-001 implementation: deferred", sdd_pr.reply_for(deferred[0]))

    def test_a_pass_where_no_reviewer_reported_is_not_a_pass(self):
        fs = sdd_pr.parse(FILE_CLEAN.replace("claude: go-reviewer (1 of 1)", "claude: go-reviewer, doc (0 of 2)"))
        self.assertEqual([], fs.passes)
        self.assertEqual(1, len(sdd_pr.parse(FILE_CLEAN.replace(" (1 of 1)", "")).passes))

    def test_slug_from_branch(self):
        self.assertEqual("feat--auth-refresh", sdd_pr.slug("feat/auth-refresh"))
        self.assertEqual("main", sdd_pr.slug("main"))


class TestScope(RepoCase):
    def test_scope_first_pass_uses_merge_base(self):
        self.descriptor(forge="none", extra='  check:\n    test_globs: ["*_test.go"]\n')
        fake = self.use(git_routes(names="a.go\na_test.go\ndocs/x.md\nMakefile\n"))
        code, out, _ = self.run_main("scope")
        self.assertEqual(0, code, out)
        self.assertTrue(fake.called("merge-base", "main", "HEAD"))
        self.assertIn("range: %s..HEAD" % MB, out)
        self.assertIn("code: a.go", out)
        self.assertIn("tests: a_test.go", out)
        self.assertIn("documents: docs/x.md", out)
        self.assertIn("other: Makefile", out)

    def test_scope_reads_the_whole_branch_even_after_a_pass(self):
        # A second reviewer gives a second opinion on all of it, not on what came after the first.
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT.replace(HEAD[:7], "9c1e2ab", 1))
        self.use(git_routes(names="a.go\n"))
        code, out, _ = self.run_main("scope", "--json")
        self.assertEqual(0, code)
        self.assertEqual("%s..HEAD" % MB, json.loads(out)["range"])

    def test_since_last_starts_at_the_reviewed_sha(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT.replace(HEAD[:7], "9c1e2ab", 1))
        self.use(git_routes(names="a.go\n"))
        code, out, _ = self.run_main("scope", "--since-last", "--json")
        self.assertEqual(0, code)
        data = json.loads(out)
        self.assertEqual("9c1e2ab..HEAD", data["range"])
        self.assertEqual(["a.go"], data["files"]["code"])

    def test_scope_without_file_or_pr_uses_the_remote_default_branch(self):
        self.descriptor(forge="none")
        routes = git_routes(names="a.go\n")
        routes.insert(0, (git("symbolic-ref"), "origin/master\n"))
        fake = self.use(routes)
        code, out, err = self.run_main("scope")
        self.assertEqual(0, code, err)
        self.assertTrue(fake.called("merge-base", "master", "HEAD"), fake.calls)
        # No local master: the remote-tracking ref is used instead.
        routes.insert(0, (git("rev-parse", "--verify", "--quiet"),
                          lambda argv, _: "" if argv[-1] == "master^{commit}" else argv[-1].split("^")[0] + "\n"))
        fake = self.use(routes)
        code, out, err = self.run_main("scope")
        self.assertEqual(0, code, err)
        self.assertTrue(fake.called("merge-base", "origin/master", "HEAD"), fake.calls)

    def test_scope_after_a_rebase_falls_back_to_the_merge_base(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT.replace(HEAD[:7], "9c1e2ab", 1))
        routes = git_routes(names="a.go\n")
        routes.insert(0, (git("merge-base", "--is-ancestor"), sdd_pr.CliError("not an ancestor")))
        self.use(routes)
        code, out, _ = self.run_main("scope", "--since-last")
        self.assertEqual(0, code)
        self.assertIn("range: %s..HEAD" % MB, out)

    def test_a_pass_that_dispatched_no_reviewer_is_not_a_pass(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN.replace(
            "claude: go-reviewer (1 of 1)\n",
            "claude: go-reviewer (1 of 1)\nReviewed %s · 2026-09-30 · cursor: none (0 of 0)\n" % HEAD[:7]
        ).replace("Reviewed %s · 2026-09-30 · claude" % HEAD[:7], "Reviewed ccccccc · 2026-09-30 · claude"))
        resolve = (git("rev-parse", "--verify", "--quiet"),
                   lambda argv, _: {HEAD[:7]: HEAD}.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")
        self.use([resolve] + git_routes(names="docs/x.md\n"))
        code, out, err = self.run_main("scope", "--since-last")
        self.assertEqual(0, code, err)
        self.assertIn("range: ccccccc..HEAD", out)
        _, out, _ = self.run_main("status")
        self.assertIn("last reviewed ccccccc", out)
        self.assertIn("Reviewed %s: no reviewer reported; not a pass" % HEAD[:7], out)

    def test_scope_is_empty_when_head_is_the_reviewed_commit(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT)
        routes = git_routes()
        routes.insert(0, (git("rev-parse", "--verify", "--quiet"), HEAD + "\n"))
        self.use(routes)
        code, out, _ = self.run_main("scope", "--since-last")
        self.assertEqual(0, code)
        self.assertIn("range: empty", out)
        # can-fail control: a second opinion at the same commit still reads the whole branch.
        _, out, _ = self.run_main("scope")
        self.assertIn("range: %s..HEAD" % MB, out)


class TestStatus(RepoCase):
    def test_status_without_forge_is_file_only(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        routes = git_routes(names="")
        routes.insert(0, (git("rev-parse", "--verify", "--quiet"), HEAD + "\n"))
        fake = self.use(routes)
        code, out, _ = self.run_main("status")
        self.assertEqual(0, code, out)
        self.assertIn("open: 0 critical, 0 important · suggestions: 1", out)
        self.assertIn("forge: none", out)
        self.assertIn("Mergeable: yes", out)
        self.assertTrue(out.rstrip().endswith("Next: carry or drop 1 suggestion (/sdd-deliver --close-out)"), out)
        self.assertFalse([a for a, _ in fake.calls if a[0] in ("gh", "az")])
        # With an open finding the next step is triage.
        self.findings(FILE_OPEN_IMPORTANT)
        code, out, _ = self.run_main("status")
        self.assertIn("- [ ] important · a.go:5", out)
        self.assertIn("Mergeable: no — 1 important open", out)
        self.assertIn("Next: /sdd-triage", out)
        for command in ("pull", "post", "resolve"):
            code, _, err = self.run_main(command)
            self.assertEqual(2, code, command)
            self.assertIn("no forge configured", err)

    def test_no_forge_is_file_only(self):
        # An unrecognised remote under forge: auto is no forge at all.
        self.descriptor(forge="auto")
        self.findings(FILE_CLEAN)
        routes = git_routes(remote="https://git.example.org/o/r.git")
        routes.insert(0, (git("rev-parse", "--verify", "--quiet"), HEAD + "\n"))
        self.use(routes)
        code, out, _ = self.run_main("status")
        self.assertEqual(0, code)
        self.assertIn("forge: none", out)
        code, out, _ = self.run_main("scope")
        self.assertEqual(0, code)
        code, _, err = self.run_main("post")
        self.assertEqual(2, code)
        self.assertIn("no forge configured", err)

    def test_detect_forge_from_remote(self):
        cases = {
            "git@github.com:o/r.git": "github",
            "https://github.com/o/r": "github",
            "https://dev.azure.com/org/proj/_git/repo": "azure-devops",
            "https://org.visualstudio.com/proj/_git/repo": "azure-devops",
            "git@ssh.dev.azure.com:v3/org/proj/repo": "azure-devops",
            "https://gitlab.example.org/o/r.git": "none",
        }
        for remote, name in cases.items():
            self.use(git_routes(remote=remote))
            self.assertEqual(name, sdd_pr.detect_forge(str(self.root)).name, remote)
        self.descriptor(forge="github")
        self.use(git_routes(remote="https://gitlab.example.org/o/r.git"))
        self.assertEqual("github", sdd_pr.detect_forge(str(self.root)).name)
        self.descriptor(forge="auto")
        self.use(git_routes(remote="https://dev.azure.com/org/My%20Project/_git/my.gitops"))
        forge = sdd_pr.detect_forge(str(self.root))
        self.assertEqual(("https://dev.azure.com/org", "My Project", "my.gitops"), (forge.org, forge.project, forge.repo))
        self.use(git_routes(remote="git@ssh.dev.azure.com:v3/org/proj/repo.git"))
        self.assertEqual("repo", sdd_pr.detect_forge(str(self.root)).repo)

    def _gh_routes(self, draft=False, checks=(), threads=(), body=None, edits=None):
        if body is None:
            body = "## Summary\n"
        pr = {
            "number": 7, "headRefOid": HEAD, "headRefName": "feat/x", "baseRefName": "main", "isDraft": draft,
            "url": "https://github.com/o/r/pull/7", "state": "OPEN", "statusCheckRollup": list(checks), "body": body,
        }

        def edit(argv, stdin):
            if edits is not None:
                edits.append((argv, stdin))
            pr["body"] = stdin
            return ""

        return [
            (has("gh", "pr", "edit"), edit),
            (has("gh", "pr", "list"), json.dumps([pr])),
            (has("gh", "pr", "view"), lambda argv, _: json.dumps(pr)),
            (has("gh", "repo", "view"), json.dumps({"owner": {"login": "o"}, "name": "r"})),
            (has("gh", "api", "graphql"), json.dumps(gh_threads(list(threads)))),
        ]

    def test_status_verdict_and_next(self):
        self.descriptor(forge="github")
        reviewed_at_head = (git("rev-parse", "--verify", "--quiet"), HEAD + "\n")
        # Open important, not on the pull request yet → post; once mirrored → triage.
        self.findings(FILE_OPEN_IMPORTANT)
        self.use([reviewed_at_head] + git_routes() + self._gh_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — 1 important open", out)
        self.assertIn("Next: sdd-pr post --pr 7", out)
        self.findings(FILE_OPEN_IMPORTANT.replace("by: claude", "by: claude · forge: 55"))
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(threads=[gh_thread(55, "a.go", 5, "x")]))
        _, out, _ = self.run_main("status")
        self.assertIn("Next: /sdd-triage", out)
        # Nothing open, the forge holds two threads the file does not know → pull.
        self.findings(FILE_CLEAN)
        threads = [gh_thread(101, "a.go", 3, "please rename"), gh_thread(102, "b.go", 4, "**critical** leak")]
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(threads=threads))
        _, out, _ = self.run_main("status")
        self.assertIn("2 unresolved threads not open in the file", out)
        self.assertIn("Next: sdd-pr pull --pr 7", out)
        # Nothing open, HEAD moved since the last pass with a code file changed → review.
        self.use(
            [(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")]
            + git_routes(names="a.go\n")
            + self._gh_routes()
        )
        _, out, _ = self.run_main("status")
        self.assertIn("code changed since", out)
        self.assertIn("Mergeable: yes", out)
        self.assertIn("Next: /sdd-review", out)
        # Nothing open, a draft → mark ready.
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(draft=True))
        _, out, _ = self.run_main("status")
        self.assertIn("PR 7 (draft)", out)
        # The close-out carries or drops the suggestion before it marks the pull request ready.
        self.assertIn("Next: carry or drop 1 suggestion", out)
        # Nothing open, ready → merge.
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(checks=[{"status": "COMPLETED", "conclusion": "SUCCESS"}]))
        _, out, _ = self.run_main("status")
        self.assertIn("checks: pass", out)
        self.assertIn("Mergeable: yes", out)
        self.assertIn("Next: carry or drop 1 suggestion", out)
        # Failing checks.
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(checks=[{"status": "COMPLETED", "conclusion": "FAILURE"}]))
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — checks failing", out)

    def test_status_measures_change_from_the_last_pass_not_the_branch(self):
        # scope reads the whole branch by default; status still says what came after the last pass.
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        self.use([(git("rev-parse", "--verify", "--quiet"), HEAD + "\n")] + git_routes(names="a.go\n"))
        _, out, _ = self.run_main("status")
        self.assertIn("(no change since)", out)

    def test_status_counts_a_build_or_ci_change_as_a_change_to_review(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        routes = [(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names="Makefile\n.github/workflows/ci.yml\n")
        self.use(routes)
        _, out, _ = self.run_main("status")
        self.assertIn("(code changed since)", out)
        self.assertIn("Next: /sdd-review", out)
        # can-fail control: a commit that changed no file is not.
        self.use([(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names=""))
        _, out, _ = self.run_main("status")
        self.assertIn("(no change since)", out)
        self.assertIn("Next: carry or drop 1 suggestion", out)

    def test_status_names_a_document_change_without_steering_to_review(self):
        # A close-out commit changes only documents: the map, the status lines, the indexes.
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        self.use([(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names="docs/x.md\n"))
        _, out, _ = self.run_main("status")
        self.assertIn("(documents changed since)", out)
        self.assertIn("Next: carry or drop 1 suggestion", out)

    def test_status_survives_an_unreachable_forge(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN)
        routes = [(git("rev-parse", "--verify", "--quiet"), HEAD + "\n")] + git_routes()
        routes.append((has("gh"), sdd_pr.CliError("gh: not signed in")))
        self.use(routes)
        code, out, _ = self.run_main("status")
        self.assertEqual(0, code)
        self.assertIn("not reachable", out)


def gh_thread(comment_id, path, line, body, resolved=False, outdated=False, login="maint"):
    return {
        "id": "T_%d" % comment_id, "isResolved": resolved, "isOutdated": outdated,
        "path": path, "line": None if outdated else line, "originalLine": line,
        "comments": {"nodes": [{"databaseId": comment_id, "body": body, "author": {"login": login}}]},
    }


def gh_threads(nodes):
    return {"data": {"repository": {"pullRequest": {"reviewThreads": {
        "nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}


class GitHubCase(RepoCase):
    PR = {}

    def routes(self, threads=(), diff="", extra=()):
        pr = {"number": 7, "headRefOid": HEAD, "headRefName": "feat/x", "baseRefName": "main", "isDraft": True,
              "url": "u", "state": "OPEN", "statusCheckRollup": [], "body": "## Summary\n"}
        pr.update(self.PR)
        self.edits = []
        self.reviews = getattr(self, "reviews", [])

        def edit(argv, stdin):
            self.edits.append(stdin)
            pr["body"] = stdin
            return ""

        return list(extra) + git_routes(diff=diff) + [
            (has("gh", "pr", "edit"), edit),
            (has("gh", "pr", "list"), lambda argv, _: json.dumps([pr])),
            (has("gh", "pr", "view"), lambda argv, _: json.dumps(pr)),
            (has("gh", "repo", "view"), json.dumps({"owner": {"login": "o"}, "name": "r"})),
            (lambda a: a[:2] == ["gh", "api"] and "--method" not in a and "/reviews?" in a[2],
             lambda argv, _: json.dumps(self.reviews)),
            (lambda a: a[:3] == ["gh", "api", "graphql"] and any("resolveReviewThread" in x for x in a),
             json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}})),
            (has("gh", "api", "graphql"), json.dumps(gh_threads(list(threads)))),
        ]


class TestPull(GitHubCase):
    def test_pull_untagged_thread_is_important(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT.replace("by: claude", "by: claude · forge: 55"))
        threads = [
            gh_thread(101, "a.go", 12, "this retry never backs off\nsecond line"),
            gh_thread(102, "b.go", 4, "**critical** the file handle leaks"),
            gh_thread(103, "c.go", 1, "done already", resolved=True),
            gh_thread(55, "a.go", 5, "already in the file"),
            gh_thread(104, "d.go", 9, "outdated but open", outdated=True),
        ]
        self.use(self.routes(threads=threads))
        code, out, err = self.run_main("pull")
        self.assertEqual(0, code, err)
        text = self.read_findings()
        self.assertIn("- [ ] important · a.go:12 · this retry never backs off · by: maint · forge: 101", text)
        self.assertIn("- [ ] critical · b.go:4 · the file handle leaks · by: maint · forge: 102", text)
        self.assertIn("d.go:9 · outdated but open", text)
        self.assertNotIn("forge: 103", text)
        self.assertEqual(1, text.count("forge: 55"))
        # A second pull adds nothing.
        self.run_main("pull")
        self.assertEqual(text, self.read_findings())

    def test_pull_reopens_a_resolved_line_whose_thread_is_open_again(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace("by: claude · fixed", "by: claude · forge: 77 · fixed").replace(
            HEAD[:7] + "\n\n## Suggestions", HEAD[:7] + " · mirrored\n\n## Suggestions"))
        reviewed_at_head = (git("rev-parse", "--verify", "--quiet"), HEAD + "\n")
        self.use([reviewed_at_head] + self.routes(threads=[gh_thread(77, "a.go", 5, "not fixed, see line 6")]))
        _, out, _ = self.run_main("status")
        self.assertIn("1 unresolved threads not open in the file", out)
        self.assertIn("Mergeable: no", out)
        code, _, err = self.run_main("pull")
        self.assertEqual(0, code, err)
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual(["77"], [f.fields.get("forge") for f in fs.open])
        self.assertEqual([], fs.open[0].flags)
        self.assertIsNone(fs.open[0].fixed)

    def test_pull_creates_the_file_when_absent(self):
        self.descriptor(forge="github")
        self.use(self.routes(threads=[gh_thread(101, "a.go", 12, "a comment")]))
        code, _, err = self.run_main("pull")
        self.assertEqual(0, code, err)
        text = self.read_findings()
        self.assertTrue(text.startswith("# Findings — feat/x\nBase: main\n"), text)
        self.assertIn("forge: 101", text)


class AzureCase(RepoCase):
    REMOTE = "https://dev.azure.com/org/proj/_git/repo"
    PR_BRANCH = "feat/x"
    PR_HEAD = HEAD
    DESCRIPTION = "Summary"

    def routes(self, threads=(), diff="", on_post=None, on_patch=None):
        pr = {"pullRequestId": 7, "isDraft": False, "targetRefName": "refs/heads/main",
              "sourceRefName": "refs/heads/" + self.PR_BRANCH, "description": "Summary",
              "lastMergeSourceCommit": {"commitId": self.PR_HEAD},
              "repository": {"id": "R1", "project": {"name": "proj"}}}
        posted = {"n": 500}

        def post(argv, stdin):
            posted["n"] += 1
            payload = json.loads(Path(argv[argv.index("--in-file") + 1]).read_text())
            if on_post:
                on_post(argv, payload)
            return json.dumps({"id": posted["n"]})

        def patch(argv, stdin):
            payload = json.loads(Path(argv[argv.index("--in-file") + 1]).read_text())
            if on_patch:
                on_patch(argv, payload)
            return "{}"

        self.updates = []

        def update(argv, stdin):
            payload = json.loads(Path(argv[argv.index("--in-file") + 1]).read_text())
            self.updates.append(payload)
            pr["description"] = payload["description"]
            return json.dumps(pr)

        pr["description"] = self.DESCRIPTION
        return git_routes(remote=self.REMOTE, diff=diff) + [
            (lambda a: a[:3] == ["az", "devops", "invoke"] and "PATCH" in a
             and a[a.index("--resource") + 1] == "pullRequests", update),
            (has("az", "repos", "pr", "list"), lambda argv, _: json.dumps([pr])),
            (has("az", "repos", "pr", "show"), lambda argv, _: json.dumps(pr)),
            (lambda a: a[:3] == ["az", "devops", "invoke"] and "PATCH" in a, patch),
            (lambda a: a[:3] == ["az", "devops", "invoke"] and "POST" in a, post),
            (has("az", "devops", "invoke"), json.dumps({"value": list(threads)})),
        ]


def az_thread(tid, path, line, body, status="active"):
    return {"id": tid, "status": status,
            "threadContext": {"filePath": "/" + path, "rightFileStart": {"line": line, "offset": 1}},
            "comments": [{"id": 1, "content": body, "author": {"displayName": "Maint"}}]}


class TestPullAzure(AzureCase):
    def test_pull_azure_devops_thread(self):
        self.descriptor(forge="auto")
        threads = [
            az_thread(11, "a.go", 5, "the retry ignores cancellation"),
            az_thread(12, "b.go", 6, "fixed", status="fixed"),
            az_thread(13, "c.go", 7, "won't", status="wontFix"),
            az_thread(14, "d.go", 8, "closed", status="closed"),
            {"id": 15, "status": "active", "comments": [{"content": "general remark", "author": {"displayName": "M"}}]},
            az_thread(16, "e.go", 9, "waiting on the author", status="pending"),
            dict(az_thread(17, "f.go", 3, "removed"), isDeleted=True),
        ]
        fake = self.use(self.routes(threads=threads))
        code, _, err = self.run_main("pull")
        self.assertEqual(0, code, err)
        text = self.read_findings()
        self.assertIn("- [ ] important · a.go:5 · the retry ignores cancellation · by: Maint · forge: 11", text)
        self.assertIn("e.go:9 · waiting on the author · by: Maint · forge: 16", text)
        for tid in ("12", "13", "14", "15", "17"):
            self.assertNotIn("forge: %s" % tid, text)
        invoke = fake.called("az", "devops", "invoke")[0]
        self.assertIn("pullRequestThreads", invoke)
        self.assertIn("pullRequestId=7", invoke)


DIFF = """diff --git a/a.go b/a.go
--- a/a.go
+++ b/a.go
@@ -1,3 +1,6 @@
 package a
+func x() {}
+func y() {}
"""

FILE_TWO_OPEN = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open
- [ ] important · a.go:5 · in the diff · evidence: ran it · fix: guard · by: claude
- [ ] important · z.go:40 · outside the diff · by: claude

## Resolved

## Suggestions
- a.go:2 · a suggestion is never posted · by: claude
""" % HEAD[:7]


class TestPost(GitHubCase):
    def test_post_keeps_unanchorable_in_file(self):
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        sent = {}

        def review(argv, stdin):
            sent["payload"] = json.loads(stdin)
            self.reviews.append({"id": 900, "body": sent["payload"]["body"]})
            return json.dumps({"id": 900})

        extra = [
            (lambda a: a[:2] == ["gh", "api"] and "--method" in a and "POST" in a and a[2].endswith("/reviews"), review),
            # As GitHub answers it: the per-review listing carries no line.
            (lambda a: a[:2] == ["gh", "api"] and "/reviews/900/comments" in a[2],
             lambda argv, _: json.dumps([{"id": 4242, "path": c["path"], "body": c["body"]}
                                         for c in sent["payload"]["comments"]])),
        ]
        self.use(self.routes(diff=DIFF, extra=extra))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        payload = sent["payload"]
        self.assertEqual("COMMENT", payload["event"])
        self.assertEqual(HEAD, payload["commit_id"])
        self.assertEqual(1, len(payload["comments"]))
        comment = payload["comments"][0]
        self.assertEqual(("a.go", 5, "RIGHT"), (comment["path"], comment["line"], comment["side"]))
        self.assertTrue(comment["body"].startswith("**important**"))
        self.assertTrue(payload["body"].startswith(
            "**Review at `%s`:** 0 critical and 2 important open; 1 suggestion, not posted.\n"
            "- claude: go-reviewer (1 of 1)" % HEAD[:7]), payload["body"])
        self.assertIn("<!-- sdd:pass %s claude -->" % HEAD[:7], payload["body"])
        self.assertIn("### Not anchored to the diff", payload["body"])
        self.assertIn("z.go:40", payload["body"])
        self.assertNotIn("suggestion is never posted", json.dumps(payload))
        text = self.read_findings()
        self.assertIn("in the diff · evidence: ran it · fix: guard · by: claude · forge: 4242", text)
        self.assertIn("z.go:40 · outside the diff · by: claude · unanchored", text)
        # The body is the author's: post never writes it.
        self.assertEqual([], self.edits)

    def test_post_never_publishes_a_finding_twice(self):
        # The first post reads no id back: the line keeps no forge id.
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        posts = []

        def review(argv, stdin):
            posts.append(json.loads(stdin))
            self.reviews.append({"id": 900, "body": posts[-1]["body"]})
            return json.dumps({"id": 900})

        extra = [
            (lambda a: a[:2] == ["gh", "api"] and "--method" in a and "POST" in a and a[2].endswith("/reviews"), review),
            (lambda a: a[:2] == ["gh", "api"] and "/reviews/900/comments" in a[2], json.dumps([])),
        ]
        fake = self.use(self.routes(diff=DIFF, extra=extra))
        self.assertEqual(0, self.run_main("post")[0])
        self.assertEqual(1, len(posts))
        self.assertTrue(any("per_page=100" in a[2] for a in fake.called("gh", "api") if "/comments" in a[2]))
        # The second post finds the thread already on the forge, adopts its id and posts nothing.
        body = posts[0]["comments"][0]["body"]
        thread = gh_thread(4242, "a.go", 5, body)
        self.use(self.routes(threads=[thread], diff=DIFF, extra=extra))
        code, _, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(posts))
        self.assertIn("in the diff · evidence: ran it · fix: guard · by: claude · forge: 4242", self.read_findings())

    def test_post_takes_the_id_from_the_threads_when_the_review_reads_none_back(self):
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        posts = []

        def review(argv, stdin):
            posts.append(json.loads(stdin))
            self.reviews.append({"id": 900, "body": posts[-1]["body"]})
            return json.dumps({"id": 900})

        def threads(argv, stdin):
            # The thread exists on the forge only once the review is posted.
            if not posts:
                return json.dumps(gh_threads([]))
            return json.dumps(gh_threads([gh_thread(4242, "a.go", 5, posts[0]["comments"][0]["body"])]))

        extra = [
            (lambda a: a[:2] == ["gh", "api"] and "--method" in a and "POST" in a and a[2].endswith("/reviews"), review),
            (lambda a: a[:2] == ["gh", "api"] and "/reviews/900/comments" in a[2], json.dumps([])),
            (lambda a: a[:3] == ["gh", "api", "graphql"] and not any("resolveReviewThread" in x for x in a), threads),
        ]
        self.use(self.routes(diff=DIFF, extra=extra))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(posts))
        self.assertIn("in the diff · evidence: ran it · fix: guard · by: claude · forge: 4242", self.read_findings())

    def test_post_saves_what_it_posted_when_reading_the_ids_back_fails(self):
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        posts = []

        def review(argv, stdin):
            posts.append(json.loads(stdin))
            self.reviews.append({"id": 900, "body": posts[-1]["body"]})
            return json.dumps({"id": 900})

        def threads(argv, stdin):
            if posts:
                raise sdd_pr.CliError("HTTP 502")
            return json.dumps(gh_threads([]))

        extra = [
            (lambda a: a[:2] == ["gh", "api"] and "--method" in a and "POST" in a and a[2].endswith("/reviews"), review),
            (lambda a: a[:2] == ["gh", "api"] and "/reviews/900/comments" in a[2], json.dumps([])),
            (lambda a: a[:3] == ["gh", "api", "graphql"] and not any("resolveReviewThread" in x for x in a), threads),
        ]
        self.use(self.routes(diff=DIFF, extra=extra))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertIn("HTTP 502", err)
        self.assertIn("1 without an id read back", out)
        self.assertIn("z.go:40 · outside the diff · by: claude · unanchored", self.read_findings())

    def test_post_with_nothing_to_post_sends_nothing(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace("Reviewed %s" % HEAD[:7], "Reviewed ccccccc"))
        self.use(self.routes())
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertIn("nothing to post", out)
        self.assertEqual([], self.edits)

    def test_a_clean_pass_posts_its_summary_once(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace(
            "claude: go-reviewer (1 of 1)\n",
            "claude: go-reviewer (1 of 1)\nReviewed %s · 2026-09-30 · claude-sonnet-5-5: go-reviewer (1 of 1)\n"
            % HEAD[:7]))
        posts = []

        def review(argv, stdin):
            posts.append(json.loads(stdin))
            self.reviews.append({"id": 901, "body": posts[-1]["body"]})
            return json.dumps({"id": 901})

        extra = [(lambda a: a[:2] == ["gh", "api"] and "POST" in a and a[2].endswith("/reviews"), review),
                 (lambda a: a[:2] == ["gh", "api"] and "/reviews/901/comments" in a[2], json.dumps([]))]
        self.use(self.routes(extra=extra))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(posts))
        self.assertEqual(([], "COMMENT"), (posts[0]["comments"], posts[0]["event"]))
        body = posts[0]["body"]
        # Two passes at HEAD, two opinions: one review names both.
        self.assertTrue(body.startswith(
            "**Review at `%s`:** no critical or important finding open; 1 suggestion, not posted.\n"
            "- claude: go-reviewer (1 of 1)\n- claude-sonnet-5-5: go-reviewer (1 of 1)\n" % HEAD[:7]), body)
        self.assertIn("<!-- sdd:pass %s claude-sonnet-5-5 -->" % HEAD[:7], body)
        self.assertNotIn("Not anchored", body)
        self.assertIn("post: the summary of 2 passes", out)
        # A second post finds the summary on the forge and sends nothing.
        self.use(self.routes(extra=extra))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(posts))
        self.assertIn("nothing to post", out)

    def test_reviews_are_read_from_every_page(self):
        # gh api --paginate prints one array per page; a summary on page two is still found.
        self.assertEqual([{"body": "a"}, {"body": "b"}, {"body": "c"}],
                         sdd_pr._json_pages('[{"body": "a"}, {"body": "b"}]\n[{"body": "c"}]'))
        self.assertEqual([], sdd_pr._json_pages(""))

    def test_no_summary_for_a_pass_before_head_or_the_maintainers_own(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace("Reviewed %s · 2026-09-30 · claude" % HEAD[:7], "Reviewed ccccccc · 2026-09-30 · claude")
                      .replace("claude: go-reviewer (1 of 1)\n",
                               "claude: go-reviewer (1 of 1)\nReviewed %s · 2026-09-30 · maintainer: Ana (1 of 1)\n" % HEAD[:7]))
        fake = self.use(self.routes())
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertIn("nothing to post", out)
        self.assertFalse([a for a, _ in fake.calls if "POST" in a])

    def test_a_summary_waits_for_the_push(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace("Reviewed %s" % HEAD[:7], "Reviewed ddddddd"))
        self.use([(git("rev-parse", "HEAD"), "d" * 40 + "\n")] + self.routes())
        code, _, err = self.run_main("post")
        self.assertEqual(2, code)
        self.assertIn("push", err)

    def test_post_dry_run_writes_nothing(self):
        self.descriptor(forge="github")
        path = self.findings(FILE_TWO_OPEN)
        fake = self.use(self.routes(diff=DIFF))
        code, out, _ = self.run_main("post", "--dry-run")
        self.assertEqual(0, code)
        self.assertIn('"event": "COMMENT"', out)
        self.assertEqual(FILE_TWO_OPEN, path.read_text())
        self.assertFalse([a for a, _ in fake.calls if "POST" in a])
        self.assertEqual([], self.edits)

    def test_post_refuses_when_head_is_not_pushed(self):
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        routes = [(git("rev-parse", "HEAD"), "d" * 40 + "\n")] + self.routes(diff=DIFF)
        self.use(routes)
        code, _, err = self.run_main("post")
        self.assertEqual(2, code)
        self.assertIn("push", err)


class TestCheckout(GitHubCase):
    """--pr and --branch name what is checked out, or the command stops before it reads or writes."""

    def test_a_pull_request_on_another_branch_stops_every_command(self):
        self.descriptor(forge="github")
        self.PR = {"headRefName": "feat/y", "headRefOid": "c" * 40}
        worktrees = "worktree /repo\nHEAD %s\nbranch refs/heads/feat/x\n\nworktree /wt/pr-7\nHEAD %s\nbranch refs/heads/feat/y\n" % (HEAD, "c" * 40)
        not_here = (git("merge-base", "--is-ancestor"), sdd_pr.CliError("not an ancestor"))
        self.use([(git("worktree", "list"), worktrees), not_here] + self.routes())
        for command in ("scope", "pull", "status", "post", "resolve"):
            code, out, err = self.run_main(command, "--pr", "7")
            self.assertEqual(2, code, (command, out))
            self.assertIn("pull request 7 is feat/y", err)
            self.assertIn("this checkout is feat/x", err)
            self.assertIn("--root /wt/pr-7", err)
        self.assertTrue(self.nothing_written())

    def test_a_checkout_that_holds_the_pull_requests_head_is_accepted_under_another_name(self):
        self.descriptor(forge="github")
        renamed = (git("rev-parse", "--abbrev-ref", "HEAD"), "mywork\n")
        # At the pull request's head.
        self.use([renamed] + self.routes())
        code, _, err = self.run_main("status", "--pr", "7")
        self.assertEqual(0, code, err)
        # Ahead of it, with commits not pushed yet.
        self.PR = {"headRefOid": "c" * 40}
        self.use([renamed] + self.routes())
        code, _, err = self.run_main("status", "--pr", "7")
        self.assertEqual(0, code, err)
        # can-fail control: a head this checkout does not hold is refused.
        self.use([renamed, (git("merge-base", "--is-ancestor"), sdd_pr.CliError("no"))] + self.routes())
        code, _, err = self.run_main("status", "--pr", "7")
        self.assertEqual(2, code)
        self.assertIn("pull request 7 is feat/x", err)

    def test_a_dry_run_does_not_write_the_retargeted_base(self):
        self.descriptor(forge="github")
        path = self.findings(FILE_TWO_OPEN.replace("Base: main", "Base: scaffold"))
        self.use(self.routes(diff=DIFF))
        code, _, err = self.run_main("post", "--dry-run")
        self.assertEqual(0, code, err)
        self.assertIn("Base: scaffold\n", path.read_text(encoding="utf-8"))

    def test_the_branch_flag_must_be_the_checked_out_branch(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        code, _, err = self.run_main("--branch", "feat/y", "scope")
        self.assertEqual(2, code)
        self.assertIn("--branch feat/y", err)
        self.assertIn("feat/x", err)
        self.assertTrue(self.nothing_written())
        # can-fail control: the branch that is checked out is accepted.
        self.assertEqual(0, self.run_main("--branch", "feat/x", "scope")[0])

    def test_the_branch_flag_on_a_detached_head_is_the_branch_at_head(self):
        self.descriptor(forge="none")
        tips = {"feat/x": HEAD, "feat/y": "c" * 40}
        detached = [(git("rev-parse", "--abbrev-ref", "HEAD"), "HEAD\n"),
                    (git("rev-parse", "--verify", "--quiet"),
                     lambda argv, _: tips.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")]
        self.use(detached + git_routes())
        self.assertEqual(0, self.run_main("--branch", "feat/x", "scope")[0])
        code, _, err = self.run_main("--branch", "feat/y", "scope")
        self.assertEqual(2, code)
        self.assertIn("--branch feat/y", err)

    def test_the_file_base_follows_a_retargeted_pull_request(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT.replace("Base: main", "Base: scaffold"))
        self.use(self.routes())
        code, _, err = self.run_main("status", "--pr", "7")
        self.assertEqual(0, code, err)
        self.assertIn("Base: main\n", self.read_findings())
        self.assertIn("scaffold", err)
        self.assertIn("main", err)


class TestStatesAzure(AzureCase):
    def test_a_completed_pull_request_is_merged(self):
        self.descriptor(forge="azure-devops")
        self.findings(FILE_CLEAN)
        routes = self.routes()
        completed = {"pullRequestId": 7, "status": "completed", "sourceRefName": "refs/heads/feat/x",
                     "targetRefName": "refs/heads/main", "lastMergeSourceCommit": {"commitId": HEAD},
                     "lastMergeCommit": {"commitId": "e" * 40}, "repository": {"id": "R1", "project": {"name": "proj"}}}
        self.use([(has("az", "repos", "pr", "list"), json.dumps([completed]))] + routes)
        _, out, _ = self.run_main("status")
        self.assertIn("PR 7 merged at eeeeeee", out)


class TestCheckoutAzure(AzureCase):
    PR_BRANCH = "feat/y"
    PR_HEAD = "c" * 40

    def test_a_pull_request_on_another_branch_stops(self):
        self.descriptor(forge="azure-devops")
        self.use([(git("merge-base", "--is-ancestor"), sdd_pr.CliError("no"))] + self.routes())
        code, _, err = self.run_main("pull", "--pr", "7")
        self.assertEqual(2, code)
        self.assertIn("pull request 7 is feat/y", err)
        self.assertTrue(self.nothing_written())


class TestPostAzure(AzureCase):
    def test_post_azure_devops_creates_threads(self):
        self.descriptor(forge="azure-devops")
        self.findings(FILE_TWO_OPEN)
        payloads = []
        self.use(self.routes(diff=DIFF, on_post=lambda argv, payload: payloads.append((argv, payload))))
        code, _, err = self.run_main("post")
        self.assertEqual(0, code, err)
        anchored = [p for _, p in payloads if "threadContext" in p]
        self.assertEqual(1, len(anchored))
        thread = anchored[0]
        self.assertEqual("active", thread["status"])
        self.assertEqual("/a.go", thread["threadContext"]["filePath"])
        self.assertEqual(5, thread["threadContext"]["rightFileStart"]["line"])
        self.assertEqual(5, thread["threadContext"]["rightFileEnd"]["line"])
        self.assertTrue(thread["comments"][0]["content"].startswith("**important**"))
        general = [p for _, p in payloads if "threadContext" not in p]
        self.assertEqual(1, len(general))
        self.assertIn("z.go:40", general[0]["comments"][0]["content"])
        self.assertIn("**Review at `%s`:**" % HEAD[:7], general[0]["comments"][0]["content"])
        self.assertEqual("active", general[0]["status"])
        text = self.read_findings()
        self.assertIn("by: claude · forge: 501", text)
        self.assertIn("unanchored", text)

    def test_azure_a_clean_pass_posts_a_closed_summary_once(self):
        self.descriptor(forge="azure-devops")
        self.findings(FILE_CLEAN)
        payloads = []
        self.use(self.routes(on_post=lambda argv, payload: payloads.append(payload)))
        code, out, err = self.run_main("post")
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(payloads))
        self.assertNotIn("threadContext", payloads[0])
        self.assertEqual("closed", payloads[0]["status"])
        content = payloads[0]["comments"][0]["content"]
        self.assertIn("no critical or important finding open", content)
        # The summary thread is on the pull request: the next post sends nothing.
        posted = {"id": 77, "status": "closed", "comments": [{"id": 1, "content": content}]}
        payloads.clear()
        self.use(self.routes(threads=[posted], on_post=lambda argv, payload: payloads.append(payload)))
        code, out, err = self.run_main("post")
        self.assertEqual((0, []), (code, payloads), err)
        self.assertIn("nothing to post", out)


FILE_RESOLVED = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open

## Resolved
- [x] important · a.go:5 · one · by: claude · forge: 9 · fixed abc1234
- [-] important · a.go:6 · two · by: claude · forge: 10 · declined: the caller checks it
- [x] important · a.go:7 · three, never mirrored · by: claude · fixed abc1234
- [x] important · a.go:8 · four, done before · by: claude · forge: 11 · fixed abc1234 · mirrored
- [~] important · a.go:9 · five, left for later · by: claude · forge: 12 · deferred: REQ-A-001 implementation: deferred

## Suggestions
""" % HEAD[:7]


class TestResolve(GitHubCase):
    def test_resolve_mirrors_fixed_and_declined(self):
        self.descriptor(forge="github")
        self.findings(FILE_RESOLVED)
        replies = {}

        def reply(argv, stdin):
            replies[argv[2]] = json.loads(stdin)["body"]
            return "{}"

        threads = [gh_thread(9, "a.go", 5, "x"), gh_thread(10, "a.go", 6, "y"), gh_thread(11, "a.go", 8, "z"),
                   gh_thread(12, "a.go", 9, "w")]
        extra = [(lambda a: a[:2] == ["gh", "api"] and a[2].endswith("/replies"), reply)]
        fake = self.use(self.routes(threads=threads, extra=extra))
        code, _, err = self.run_main("resolve")
        self.assertEqual(0, code, err)
        self.assertEqual("fixed in abc1234", replies["repos/o/r/pulls/7/comments/9/replies"])
        self.assertEqual("declined: the caller checks it", replies["repos/o/r/pulls/7/comments/10/replies"])
        self.assertEqual("deferred: REQ-A-001 implementation: deferred", replies["repos/o/r/pulls/7/comments/12/replies"])
        self.assertEqual(3, len(replies))
        resolved = [a for a, _ in fake.calls if any("resolveReviewThread" in x for x in a)]
        self.assertEqual(3, len(resolved))
        self.assertEqual([], self.edits)
        self.assertTrue(any("T_9" in " ".join(a) for a in resolved))
        text = self.read_findings()
        self.assertIn("forge: 9 · fixed abc1234 · mirrored", text)
        self.assertIn("declined: the caller checks it · mirrored", text)
        self.assertIn("three, never mirrored · by: claude · fixed abc1234\n", text)
        # A second run sends nothing.
        replies.clear()
        self.run_main("resolve")
        self.assertEqual({}, replies)


class TestResolveAzure(AzureCase):
    def test_resolve_azure_devops_sets_native_status(self):
        self.descriptor(forge="azure-devops")
        self.findings(FILE_RESOLVED)
        posts, patches = [], []
        self.use(self.routes(on_post=lambda a, p: posts.append((a, p)), on_patch=lambda a, p: patches.append((a, p))))
        code, _, err = self.run_main("resolve")
        self.assertEqual(0, code, err)
        self.assertEqual(["fixed in abc1234", "declined: the caller checks it",
                          "deferred: REQ-A-001 implementation: deferred"], [p["content"] for _, p in posts])
        self.assertTrue(all("pullRequestThreadComments" in a for a, _ in posts))
        self.assertEqual([{"status": "fixed"}, {"status": "wontFix"}, {"status": "closed"}], [p for _, p in patches])
        # The description is the author's: resolve never writes it.
        self.assertEqual([], self.updates)
        self.assertTrue(any("threadId=9" in a for a, _ in patches))

FILE_TWO_AGENTS = """# Findings — feat/x
Base: main
Reviewed ccccccc · 2026-09-29 · cursor: go-reviewer (1 of 1)
Reviewed %s · 2026-09-30 · claude: go-reviewer, sdd-doc-reviewer (2 of 2)

## Open

## Resolved

## Suggestions
""" % HEAD[:7]


class TestScopeFlags(RepoCase):
    """scope --base, --agent and --diff; the base behind its remote; the vendored gate; reviewers by path."""

    def test_base_names_the_parent_of_a_stacked_branch_and_is_written_down(self):
        self.descriptor(forge="none")
        fake = self.use(git_routes(names="a.go\n"))
        code, out, err = self.run_main("scope", "--base", "feat/parent")
        self.assertEqual(0, code, err)
        self.assertIn("base: feat/parent", out)
        self.assertTrue(fake.called("merge-base", "feat/parent", "HEAD"))
        self.assertIn("Base: feat/parent\n", self.read_findings())
        # The next run reads the base from the file.
        fake = self.use(git_routes(names="a.go\n"))
        self.run_main("scope")
        self.assertTrue(fake.called("merge-base", "feat/parent", "HEAD"))

    def test_a_local_base_behind_its_remote_is_not_where_the_range_starts(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN.replace("Reviewed", "Reviewed-not").replace("Reviewed-not %s · 2026-09-30 · claude: go-reviewer (1 of 1)\n" % HEAD[:7], ""))
        tips = {"main": "1" * 40, "origin/main": "2" * 40}
        resolve = (git("rev-parse", "--verify", "--quiet"), lambda argv, _: tips.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")
        fake = self.use([resolve] + git_routes(names="a.go\n"))
        code, out, err = self.run_main("scope")
        self.assertEqual(0, code, err)
        self.assertTrue(fake.called("merge-base", "origin/main", "HEAD"), fake.calls)
        self.assertIn("behind origin/main", err)
        # can-fail control: a local base ahead of its remote (not pushed yet) is the local one.
        fake = self.use([resolve, (git("merge-base", "--is-ancestor", "1" * 40), sdd_pr.CliError("no"))] + git_routes(names="a.go\n"))
        self.run_main("scope")
        self.assertTrue(fake.called("merge-base", "main", "HEAD"))

    def test_the_vendored_gate_is_not_code_to_review(self):
        self.descriptor(forge="none", extra="  check:\n    script: tools/vendor/sdd-check.py\n")
        self.use(git_routes(names="tools/vendor/sdd-check.py\na.go\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("vendored: tools/vendor/sdd-check.py", out)
        self.assertIn("code: a.go\n", out)
        _, out, _ = self.run_main("scope", "--json")
        self.assertEqual(["tools/vendor/sdd-check.py"], json.loads(out)["files"]["vendored"])

    def test_reviewers_by_path_get_only_their_paths(self):
        self.descriptor(forge="none", extra=(
            "  agents:\n    reviewers:\n      \"**/*.go\": go-coding:go-reviewer\n"
            "      \"tools/**\": [py-reviewer, lint-reviewer]\n"))
        self.use(git_routes(names="cmd/a.go\nb.go\ntools/x.py\nMakefile\ndocs/x.md\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("reviewer go-coding:go-reviewer: cmd/a.go b.go\n", out)
        self.assertIn("reviewer py-reviewer: tools/x.py\n", out)
        self.assertIn("reviewer lint-reviewer: tools/x.py\n", out)
        self.assertIn("no reviewer: Makefile\n", out)
        self.assertNotIn("docs/x.md", [line for line in out.splitlines() if line.startswith("reviewer")])

    def test_a_plain_reviewer_list_reviews_every_code_path(self):
        self.descriptor(forge="none", extra="  agents:\n    reviewers: [go-reviewer]\n")
        self.use(git_routes(names="a.go\nMakefile\ndocs/x.md\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("reviewer go-reviewer: a.go Makefile\n", out)
        self.assertNotIn("no reviewer:", out)

    def test_diff_prints_the_hunks_of_one_kind_or_one_reviewer(self):
        self.descriptor(forge="none", extra="  agents:\n    reviewers: [go-reviewer]\n")
        seen = []

        def diff(argv, stdin):
            seen.append(argv)
            return DIFF

        self.use([(lambda a: git("diff")(a) and "--name-only" not in a, diff)] + git_routes(names="a.go\ndocs/x.md\n"))
        code, out, err = self.run_main("scope", "--diff", "documents")
        self.assertEqual(0, code, err)
        self.assertIn("+func x() {}", out)
        self.assertEqual(["docs/x.md"], seen[-1][seen[-1].index("--") + 1:])
        self.run_main("scope", "--diff", "go-reviewer")
        self.assertEqual(["a.go"], seen[-1][seen[-1].index("--") + 1:])
        code, _, err = self.run_main("scope", "--diff", "nobody")
        self.assertEqual(2, code)
        self.assertIn("nobody", err)

    def test_an_empty_reviewer_list_leaves_the_code_uncovered_and_says_so(self):
        self.descriptor(forge="none", extra="  agents:\n    reviewers: []\n")
        self.use(git_routes(names="a.go\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("no reviewer: a.go\n", out)

    def test_an_agent_name_is_spelled_as_record_writes_it(self):
        self.descriptor(forge="none")
        self.findings(FILE_TWO_AGENTS.replace("cursor: go-reviewer", "cursor-composer: go-reviewer"))
        resolve = (git("rev-parse", "--verify", "--quiet"),
                   lambda argv, _: {HEAD[:7]: HEAD}.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")
        self.use([resolve] + git_routes(names="a.go\n"))
        _, out, _ = self.run_main("scope", "--since-last", "--agent", "cursor:composer")
        self.assertIn("range: ccccccc..HEAD", out)

    def test_the_vendored_gate_is_found_however_its_path_is_written(self):
        self.descriptor(forge="none", extra="  check:\n    script: ./tools/gate/sdd-check.py\n")
        self.use(git_routes(names="tools/gate/sdd-check.py\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("vendored: tools/gate/sdd-check.py", out)

    def test_a_vendored_gate_patched_here_is_code_to_review(self):
        self.descriptor(forge="none")
        own = (TOOLS_DIR / "sdd-check.py").read_text(encoding="utf-8")
        gate = self.root / "scripts" / "sdd-check.py"
        gate.parent.mkdir(parents=True)
        gate.write_text(own, encoding="utf-8")
        self.use(git_routes(names="scripts/sdd-check.py\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("vendored: scripts/sdd-check.py", out)
        gate.write_text(own + "\n# patched here\n", encoding="utf-8")
        _, out, _ = self.run_main("scope")
        self.assertIn("code: scripts/sdd-check.py", out)

    def test_a_diverged_local_base_is_named(self):
        self.descriptor(forge="none")
        tips = {"main": "1" * 40, "origin/main": "2" * 40}
        resolve = (git("rev-parse", "--verify", "--quiet"), lambda argv, _: tips.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")
        self.use([resolve, (git("merge-base", "--is-ancestor"), sdd_pr.CliError("no"))] + git_routes(names="a.go\n"))
        _, _, err = self.run_main("scope")
        self.assertIn("diverged", err)

    def test_diff_for_a_reviewer_with_nothing_in_the_range_is_empty(self):
        self.descriptor(forge="none", extra="  agents:\n    reviewers: [go-reviewer]\n")
        self.use(git_routes(names="docs/x.md\n"))
        code, out, err = self.run_main("scope", "--diff", "go-reviewer")
        self.assertEqual((0, ""), (code, out), err)

    def test_git_never_quotes_a_path(self):
        self.descriptor(forge="none")
        fake = self.use(git_routes(names="docs/café.md\n"))
        self.run_main("scope")
        self.assertTrue(all("core.quotePath=false" in argv for argv, _ in fake.calls if argv[0] == "git"))

    def test_agent_reads_the_range_since_its_own_last_pass(self):
        self.descriptor(forge="none")
        self.findings(FILE_TWO_AGENTS)
        resolve = (git("rev-parse", "--verify", "--quiet"),
                   lambda argv, _: {HEAD[:7]: HEAD}.get(argv[-1].split("^")[0], argv[-1].split("^")[0]) + "\n")
        self.use([resolve] + git_routes(names="a.go\n"))
        _, out, _ = self.run_main("scope", "--since-last")
        self.assertIn("range: empty", out)
        _, out, _ = self.run_main("scope", "--since-last", "--agent", "cursor")
        self.assertIn("range: ccccccc..HEAD", out)
        # An agent with no pass of its own starts at the merge base.
        _, out, _ = self.run_main("scope", "--since-last", "--agent", "codex")
        self.assertIn("range: %s..HEAD" % MB, out)

    def test_agent_without_since_last_is_refused(self):
        # --agent only says whose last pass --since-last starts from; alone it would be ignored.
        self.descriptor(forge="none")
        self.findings(FILE_TWO_AGENTS)
        self.use(git_routes(names="a.go\n"))
        code, out, err = self.run_main("scope", "--agent", "cursor")
        self.assertEqual((2, ""), (code, out))
        self.assertIn("--since-last", err)



class TestDelivery(RepoCase):
    """Plans, a plugin older than the repository, worker branches and the delivery notes."""

    def test_a_plan_is_listed_apart_and_no_reviewer_reads_it(self):
        self.descriptor(forge="none", extra="  agents:\n    reviewers: [go-reviewer]\n")
        plan = self.root / "docs" / "plans" / "x.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("---\nkind: plan\n---\n\n# Plan\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
        self.use(git_routes(names="docs/plans/x.md\ndocs/guide.md\na.go\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("plans: docs/plans/x.md\n", out)
        self.assertIn("documents: docs/guide.md\n", out)
        self.assertIn("reviewer go-reviewer: a.go\n", out)
        # A plan alone is no change to review.
        self.findings(FILE_CLEAN)
        self.use([(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names="docs/plans/x.md\n"))
        _, out, _ = self.run_main("status")
        self.assertIn("(no change since)", out)

    def test_a_plugin_older_than_the_repository_writes_nothing(self):
        self.descriptor(forge="none", extra="  check:\n    version: \"99.0.0\"\n")
        self.use(git_routes())
        code, _, err = self.run_main("add", "suggestion", "a.go:1", "x", "--by", "claude")
        self.assertEqual(2, code)
        self.assertIn("older than this repository (99.0.0)", err)
        self.assertTrue(self.nothing_written())
        code, out, _ = self.run_main("status")
        self.assertEqual(0, code)
        self.assertIn("older than this repository (99.0.0)", out)
        # A carry writes no backlog either.
        self.findings(FILE_CLEAN)
        self.assertEqual(2, self.run_main("flip", "--suggestions", "--carry")[0])
        self.assertFalse((self.root / "docs" / "backlog.md").exists())
        self.assertEqual(FILE_CLEAN, self.read_findings())
        # can-fail control: a repository at the plugin's own version is written.
        self.descriptor(forge="none", extra="  check:\n    version: \"%s\"\n" % sdd_pr.__version__)
        self.assertEqual(0, self.run_main("add", "suggestion", "a.go:1", "x", "--by", "claude")[0])

    def test_versions_compare_number_by_number(self):
        self.assertTrue(sdd_pr.version_lt("0.8.9", "0.8.10"))
        self.assertFalse(sdd_pr.version_lt("0.8.10", "0.8.9"))
        self.assertTrue(sdd_pr.version_lt("0.8", "0.8.1"))
        self.assertFalse(sdd_pr.version_lt("0.8.1", "0.8.1"))

    def test_worker_branches_not_integrated_block_and_merged_ones_are_named_for_removal(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN.replace("- a.go:9 · rename `n` to `count` · by: claude\n", ""))
        workers = (git("for-each-ref"), "feat/x--parser\nfeat/x--docs\n")
        merged = (lambda a: git("merge-base", "--is-ancestor")(a) and "feat/x--docs" in a, sdd_pr.CliError("no"))
        reviewed_at_head = (git("rev-parse", "--verify", "--quiet"), lambda argv, _: HEAD + "\n")
        self.use([workers, merged, reviewed_at_head] + git_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("workers: feat/x--docs not integrated · feat/x--parser merged", out)
        self.assertIn("Mergeable: no — worker branch feat/x--docs not integrated", out)
        self.assertIn("Next: integrate feat/x--docs (/sdd-deliver step 7)", out)
        self.use([(git("for-each-ref"), "feat/x--parser\n"), reviewed_at_head] + git_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: yes", out)
        self.assertIn("Next: remove the merged worker branches and their worktrees: feat/x--parser", out)

    def test_a_worker_with_no_commit_yet_or_work_in_its_tree_is_running_not_merged(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN.replace("- a.go:9 · rename `n` to `count` · by: claude\n", ""))
        workers = (git("for-each-ref"), "feat/x--t3\n")
        fresh = (git("reflog"), "branch: Created from feat/x\n")
        self.use([workers, fresh] + git_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("workers: feat/x--t3 running (no commit yet)", out)
        self.assertIn("Mergeable: no — worker branch feat/x--t3 not integrated", out)
        listing = "worktree %s\nHEAD %s\nbranch refs/heads/feat/x\n\nworktree /wt/t3\nHEAD %s\nbranch refs/heads/feat/x--t3\n" % (self.root, HEAD, HEAD)
        dirty = (lambda a: git("status", "--porcelain")(a) and "/wt/t3" in a, " M a.go\n")
        self.use([workers, dirty, (git("worktree", "list"), listing)] + git_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("workers: feat/x--t3 running (uncommitted work in /wt/t3)", out)

    def test_a_plan_deleted_in_the_range_is_still_a_plan(self):
        self.descriptor(forge="none")
        shown = (git("show"), "---\nkind: plan\n---\n\n# Plan\n")
        self.use([shown] + git_routes(names="docs/plans/gone.md\n"))
        _, out, _ = self.run_main("scope")
        self.assertIn("plans: docs/plans/gone.md\n", out)

    def test_a_merged_pull_request_names_the_delivery_notes_too(self):
        self.descriptor(forge="none")
        notes = self.root / ".git" / "sdd" / "deliver" / "feat--x.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("Lane: full\n", encoding="utf-8")
        self.assertIn(str(notes), sdd_pr.cleanup_line(str(self.store()), str(notes)))
        self.assertNotIn("notes", sdd_pr.cleanup_line(str(self.store()), str(self.root / "absent.md")))

    def test_status_names_the_delivery_notes_when_they_exist(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        _, out, _ = self.run_main("status")
        self.assertNotIn("notes:", out)
        notes = self.root / ".git" / "sdd" / "deliver" / "feat--x.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("Lane: full\n", encoding="utf-8")
        _, out, _ = self.run_main("status")
        self.assertIn("notes: %s" % notes, out)



class TestStore(RepoCase):
    """One findings file per branch, in the clone's shared git directory."""

    def test_the_file_lives_in_the_shared_git_directory(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        code, out, err = self.run_main("add", "suggestion", "a.go:9", "rename n", "--by", "claude")
        self.assertEqual(0, code, err)
        self.assertTrue(self.store().exists())
        self.assertFalse((self.root / ".sdd").exists())
        _, out, _ = self.run_main("status")
        self.assertIn("findings: %s" % self.store(), out)

    def test_every_worktree_of_the_clone_resolves_to_the_same_file(self):
        self.descriptor(forge="none")
        common = self.root / "main-checkout" / ".git"
        self.use([(git("rev-parse", "--git-common-dir"), str(common) + "\n")] + git_routes())
        self.assertEqual(0, self.run_main("add", "suggestion", "a.go:9", "rename n", "--by", "claude")[0])
        self.assertTrue((common / "sdd" / "findings" / "feat--x.md").exists())

    def test_a_file_left_in_the_checkout_is_moved_on_first_use(self):
        self.descriptor(forge="none")
        legacy = self.root / ".sdd" / "findings" / "feat--x.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(FILE_OPEN_IMPORTANT, encoding="utf-8")
        self.use(git_routes())
        code, out, err = self.run_main("status")
        self.assertEqual(0, code, err)
        self.assertIn("moved", err)
        self.assertFalse(legacy.exists())
        self.assertEqual(FILE_OPEN_IMPORTANT, self.read_findings())
        self.assertIn("1 important open", out)

    def test_a_file_left_in_another_worktree_is_found_and_moved(self):
        self.descriptor(forge="none")
        other = self.root / "elsewhere"
        legacy = other / ".sdd" / "findings" / "feat--x.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(FILE_OPEN_IMPORTANT, encoding="utf-8")
        listing = "worktree %s\nHEAD %s\nbranch refs/heads/main\n\nworktree %s\nHEAD %s\nbranch refs/heads/feat/x\n" % (
            other, MB, self.root, HEAD)
        self.use([(git("worktree", "list"), listing)] + git_routes())
        code, out, err = self.run_main("status")
        self.assertEqual(0, code, err)
        self.assertIn(str(legacy), err)
        self.assertFalse(legacy.exists())
        self.assertIn("1 important open", out)

    def test_a_writer_holds_the_store_for_the_whole_command(self):
        import fcntl
        self.descriptor(forge="none")
        self.use(git_routes())
        session = sdd_pr.Session(sdd_pr.build_parser().parse_args(["--root", str(self.root), "status"]))
        try:
            with open(session.lock_path, "a") as other:
                with self.assertRaises(OSError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            session.close()
        with open(session.lock_path, "a") as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertFalse((self.root / ".git" / "sdd").exists())

    def test_two_files_for_one_branch_are_named_not_merged(self):
        self.descriptor(forge="none")
        legacy = self.root / ".sdd" / "findings" / "feat--x.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(FILE_CLEAN, encoding="utf-8")
        self.findings(FILE_OPEN_IMPORTANT)
        self.use(git_routes())
        code, _, err = self.run_main("status")
        self.assertEqual(0, code, err)
        self.assertIn(str(legacy), err)
        self.assertIn("sdd-pr add -", err)
        self.assertTrue(legacy.exists())
        self.assertEqual(FILE_OPEN_IMPORTANT, self.read_findings())


class TestAdd(RepoCase):
    def test_add_writes_a_line_in_the_grammar(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        code, out, err = self.run_main("add", "important", "a.go:5", "the retry · ignores the context",
                                       "--evidence", "TestRetry hangs", "--fix", "select on ctx.Done", "--by", "claude")
        self.assertEqual(0, code, err)
        text = self.read_findings()
        self.assertTrue(text.startswith("# Findings — feat/x\nBase: main\n"), text)
        self.assertIn("## Open\n- [ ] important · a.go:5 · the retry - ignores the context · evidence: TestRetry hangs"
                      " · fix: select on ctx.Done · by: claude\n", text)
        self.assertIn("add: 1 added", out)
        self.run_main("add", "suggestion", "a.go:9", "rename n", "--by", "claude")
        self.assertIn("## Suggestions\n- a.go:9 · rename n · by: claude\n", self.read_findings())

    def test_a_blocking_finding_needs_evidence(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        code, _, err = self.run_main("add", "critical", "a.go:5", "a leak")
        self.assertEqual(2, code)
        self.assertIn("evidence", err)
        self.assertTrue(self.nothing_written())

    def test_the_same_defect_twice_is_one_line_with_both_reviewers(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT)
        self.use(git_routes())
        code, out, err = self.run_main("add", "important", "a.go:5", "The retry ignores the context",
                                       "--evidence", "ran it", "--by", "cursor")
        self.assertEqual(0, code, err)
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual(1, len(fs.open))
        self.assertEqual("claude, cursor", fs.open[0].fields["by"])
        self.assertIn("1 merged", out)

    def test_add_refuses_lines_that_would_not_read_back(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        for argv in (("important", "a.go:4", "", "--evidence", "ee"), ("suggestion", "a · b.go:3", "x"),
                     ("bogus", "a.go:1", "x")):
            code, _, err = self.run_main("add", *argv)
            self.assertEqual(2, code, argv)
        code, _, err = self.run_main("add", "important", "a.go:4", "x")
        self.assertIn("an important finding needs --evidence", err)
        with mock.patch("sys.stdin", io.StringIO("- [x] important · a.go:2 · done · by: c · fixed abc1234\n")):
            self.assertEqual(2, self.run_main("add", "-")[0])
        with mock.patch("sys.stdin", io.StringIO("- [ ] important · a.go:2 · no evidence · by: c\n")):
            code, _, err = self.run_main("add", "-")
        self.assertIn("line 1", err)
        self.assertTrue(self.nothing_written())

    def test_add_reads_a_reviewers_lines_from_standard_input(self):
        self.descriptor(forge="none")
        self.use(git_routes())
        lines = ("```text\n"
                 "- [ ] critical · b.go:4 · the handle leaks · evidence: ran it · fix: close it · by: go-reviewer\n"
                 "- b.go:9 · rename `n` · by: go-reviewer\n"
                 "```\n")
        with mock.patch("sys.stdin", io.StringIO(lines)):
            code, out, err = self.run_main("add", "-")
        self.assertEqual(0, code, err)
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual(["critical"], [f.severity for f in fs.open])
        self.assertEqual(1, len(fs.suggestions))
        # A malformed line writes nothing and names the line.
        with mock.patch("sys.stdin", io.StringIO("- [ ] b.go:3 · no severity\n")):
            code, _, err = self.run_main("add", "-")
        self.assertEqual(2, code)
        self.assertIn("line 1", err)
        self.assertEqual(1, len(sdd_pr.parse(self.read_findings()).open))


FILE_FLIP = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open
- [ ] important · a.go:5 · one · evidence: ran it · by: claude · forge: 41
- [ ] critical · a.go:6 · two · evidence: ran it · by: claude
- [ ] important · a.go:7 · three · evidence: ran it · by: claude

## Resolved

## Suggestions
- a.go:9 · rename n · by: claude
- a.go:10 · reword · by: claude
""" % HEAD[:7]


class TestFlip(RepoCase):
    def test_flip_fixed_keeps_the_thread_id_and_needs_the_fix_pushed(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        code, out, err = self.run_main("flip", "a.go:5", "--fixed", "abc1234")
        self.assertEqual(0, code, err)
        fs = sdd_pr.parse(self.read_findings())
        fixed = [f for f in fs.resolved if f.status == "fixed"][0]
        self.assertEqual(("41", "abc1234"), (fixed.fields["forge"], fixed.fixed))
        # A fix the remote branch does not hold yet is refused.
        self.use([(git("merge-base", "--is-ancestor"), sdd_pr.CliError("no"))] + git_routes())
        code, _, err = self.run_main("flip", "a.go:6", "--fixed", "def5678")
        self.assertEqual(2, code)
        self.assertIn("push", err)
        self.assertEqual(2, len(sdd_pr.parse(self.read_findings()).open))

    def keys(self):
        fs = sdd_pr.parse(self.read_findings())
        return {f.text: "#" + sdd_pr.key_of(f) for f in fs.open + fs.suggestions}

    def test_keys_do_not_move_when_other_lines_flip(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        keys = self.keys()
        _, out, _ = self.run_main("status")
        self.assertIn("%s - [ ] critical · a.go:6" % keys["two"], out)
        self.assertIn("%s - a.go:9 · rename n" % keys["rename n"], out)
        # Two flips in a row with the keys from one listing flip the lines they name.
        self.assertEqual(0, self.run_main("flip", keys["one"], "--fixed", "abc1234")[0])
        self.assertEqual(0, self.run_main("flip", keys["two"], "--fixed", "abc1234")[0])
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual(["three"], [f.text for f in fs.open])
        # A position is not a selector any more: it moves when a line flips.
        self.assertEqual(2, self.run_main("flip", "#1", "--fixed", "abc1234")[0])

    def test_flip_by_key_declined_and_deferred(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        keys = self.keys()
        self.assertEqual(0, self.run_main("flip", keys["two"], "--declined", "the caller checks it")[0])
        self.assertEqual(0, self.run_main("flip", "a.go:7", "--deferred", "SPEC-A § Known gaps")[0])
        text = self.read_findings()
        self.assertIn("- [-] critical · a.go:6 · two · evidence: ran it · by: claude · declined: the caller checks it", text)
        self.assertIn("- [~] important · a.go:7 · three · evidence: ran it · by: claude · deferred: SPEC-A § Known gaps", text)

    def test_suggestions_are_deferred_or_dropped(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        self.assertEqual(0, self.run_main("flip", "a.go:9", "--deferred", "https://example.org/issues/3")[0])
        self.assertIn("- [~] suggestion · a.go:9 · rename n · by: claude · deferred: https://example.org/issues/3",
                      self.read_findings())
        code, out, err = self.run_main("flip", "--suggestions", "--dropped")
        self.assertEqual(0, code, err)
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual([], fs.suggestions)
        self.assertNotIn("reword", self.read_findings())
        # Only a suggestion is dropped; a blocking finding is deferred, with the maintainer's word.
        code, _, err = self.run_main("flip", "a.go:5", "--dropped")
        self.assertEqual(2, code)
        self.assertIn("--deferred", err)

    def backlog(self, text=None):
        path = self.root / "docs" / "backlog.md"
        if text is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return path.read_text(encoding="utf-8") if path.exists() else None

    def test_carry_appends_the_suggestions_to_the_backlog_by_directory(self):
        self.descriptor(forge="none")
        flip = FILE_FLIP.replace("- a.go:10 · reword", "- internal/auth/b.go:10 · reword")
        self.findings(flip)
        head = sdd_pr.BACKLOG_HEAD
        self.backlog(head + "\n## internal/auth\n- internal/auth/c.go:1 · older · from: feat/old\n\n"
                     "## zz\n- zz/y.go:2 · last · from: feat/old\n")
        self.use(git_routes())
        code, out, err = self.run_main("flip", "--suggestions", "--carry")
        self.assertEqual(0, code, err)
        self.assertIn("2 lines carried to docs/backlog.md", out)
        self.assertEqual(head + "\n## .\n- a.go:9 · rename n · by: claude · from: feat/x\n\n"
                         "## internal/auth\n- internal/auth/c.go:1 · older · from: feat/old\n"
                         "- internal/auth/b.go:10 · reword · by: claude · from: feat/x\n\n"
                         "## zz\n- zz/y.go:2 · last · from: feat/old\n", self.backlog())
        text = self.read_findings()
        self.assertIn("- [~] suggestion · a.go:9 · rename n · by: claude · deferred: docs/backlog.md", text)
        self.assertEqual([], sdd_pr.parse(text).suggestions)
        # Carried again, an item the backlog already holds is not written twice.
        before = self.backlog()
        self.findings(flip)
        self.assertEqual(0, self.run_main("flip", "--suggestions", "--carry")[0])
        self.assertEqual(before, self.backlog())

    def test_carry_matches_whole_fields_not_substrings(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.backlog(sdd_pr.BACKLOG_HEAD + "\n## .\n- a.go:9 · rename n everywhere · from: feat/old\n\n"
                     "## sub\n- sub/a.go:9 · rename n · from: feat/old\n- important · sub/a.go:10 · reword · from: feat/old\n")
        self.use(git_routes())
        self.assertEqual(0, self.run_main("flip", "--suggestions", "--carry")[0])
        backlog = self.backlog()
        self.assertIn("- a.go:9 · rename n · by: claude · from: feat/x\n", backlog)
        self.assertIn("- a.go:10 · reword · by: claude · from: feat/x\n", backlog)
        # Two lines with one anchor and sentence, as a hand edit may leave, are one item.
        self.findings(FILE_FLIP.replace("- a.go:10 · reword", "- c.go:1 · twice\n- c.go:1 · twice"))
        self.assertEqual(0, self.run_main("flip", "--suggestions", "--carry")[0])
        self.assertEqual(1, self.backlog().count("c.go:1 · twice"))
        # The same item under a severity is still the same item.
        self.findings(FILE_FLIP.replace("- a.go:10 · reword", "- sub/a.go:10 · reword"))
        self.assertEqual(0, self.run_main("flip", self.keys()["reword"], "--carry")[0])
        self.assertEqual(1, self.backlog().count("sub/a.go:10 · reword"))

    def test_carry_writes_nothing_without_a_line_and_heads_an_empty_file(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT)
        self.use(git_routes())
        self.assertEqual(0, self.run_main("flip", "--suggestions", "--carry")[0])
        self.assertIsNone(self.backlog())
        self.backlog("\n\n")
        self.findings(FILE_FLIP)
        self.assertEqual(0, self.run_main("flip", "a.go:9", "--carry")[0])
        self.assertTrue(self.backlog().startswith(sdd_pr.BACKLOG_HEAD + "\n## .\n- a.go:9 · rename n"), self.backlog())

    def test_carry_starts_the_backlog_and_keeps_a_blocking_findings_severity(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        self.assertEqual(0, self.run_main("flip", "a.go:6", "--carry")[0])
        backlog = self.backlog()
        self.assertTrue(backlog.startswith("---\nkind: plan\n---\n# Backlog\n"), backlog)
        self.assertTrue(backlog.endswith("\n## .\n- critical · a.go:6 · two · evidence: ran it · by: claude · from: feat/x\n"),
                        backlog)
        self.assertIn("- [~] critical · a.go:6 · two · evidence: ran it · by: claude · deferred: docs/backlog.md",
                      self.read_findings())

    def test_an_anchor_that_names_two_lines_is_refused_with_their_keys(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP.replace("a.go:7 · three", "a.go:6 · three").replace("a.go:10 · reword", "a.go:9 · reword"))
        self.use(git_routes())
        keys = self.keys()
        code, _, err = self.run_main("flip", "a.go:6", "--declined", "x")
        self.assertEqual(2, code)
        self.assertIn(keys["two"], err)
        self.assertIn(keys["three"], err)
        # Two suggestions on one line are deferred one at a time by key.
        self.assertEqual(0, self.run_main("flip", keys["reword"], "--deferred", "issue 4")[0])
        self.assertEqual(["rename n"], [f.text for f in sdd_pr.parse(self.read_findings()).suggestions])

    def test_flip_refuses_what_it_cannot_do_safely(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use([(git("rev-parse", "--verify", "--quiet", "nope^{commit}"), sdd_pr.CliError("no"))] + git_routes())
        self.assertEqual(2, self.run_main("flip", "a.go:5", "--fixed", "nope")[0])
        self.assertEqual(2, self.run_main("flip", "a.go:9", "--suggestions", "--dropped")[0])
        self.assertEqual(2, self.run_main("flip", "--suggestions", "--carry", "--dropped")[0])
        self.assertEqual(FILE_FLIP, self.read_findings())
        self.assertFalse((self.root / "docs" / "backlog.md").exists())


class TestRecordAndRename(RepoCase):
    def test_record_writes_the_reviewed_line_from_head(self):
        self.descriptor(forge="none")
        self.findings(FILE_FLIP)
        self.use(git_routes())
        code, out, err = self.run_main("record", "--agent", "claude", "--reviewers", "go-reviewer, sdd-doc-reviewer",
                                       "--reported", "2/2")
        self.assertEqual(0, code, err)
        last = sdd_pr.parse(self.read_findings()).reviewed[-1]
        self.assertEqual((HEAD[:7], "claude", "go-reviewer, sdd-doc-reviewer (2 of 2)"), (last[0], last[2], last[3]))
        self.assertRegex(last[1], r"^\d{4}-\d{2}-\d{2}$")
        for bad in ("0/2", "3/2", "two", "1/2"):
            code, _, err = self.run_main("record", "--agent", "claude", "--reviewers", "x", "--reported", bad)
            self.assertEqual(2, code, bad)
        code, out, _ = self.run_main("record", "--agent", "claude:code", "--reviewers", "a, b", "--reported", "1/2")
        self.assertEqual(0, code)
        self.assertEqual(("claude-code", "a, b (1 of 2)"), sdd_pr.parse(self.read_findings()).reviewed[-1][2:])
        self.assertEqual(3, len(sdd_pr.parse(self.read_findings()).reviewed))

    def test_rename_moves_the_file_and_forgets_the_old_branch(self):
        self.descriptor(forge="none")
        old = FILE_FLIP.replace("# Findings — feat/x", "# Findings — feat/old").replace("forge: 41", "forge: 41 · mirrored")
        self.findings(old, branch="feat/old")
        self.use(git_routes())
        code, out, err = self.run_main("rename", "--from", "feat/old")
        self.assertEqual(0, code, err)
        self.assertFalse(self.store("feat/old").exists())
        fs = sdd_pr.parse(self.read_findings())
        self.assertEqual(("feat/x", "main"), (fs.branch, fs.base))
        self.assertEqual([], fs.reviewed)
        self.assertEqual(set(), fs.forge_ids())
        self.assertTrue(all("mirrored" not in f.flags for f in fs.items))
        self.assertEqual(3, len(fs.open))
        # A branch that already has a file is not overwritten.
        self.findings(old, branch="feat/old")
        code, _, err = self.run_main("rename", "--from", "feat/old")
        self.assertEqual(2, code)
        self.assertIn("already", err)


class TestLeftovers(RepoCase):
    def test_once_every_suggestion_is_carried_or_dropped_next_is_merge(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        reviewed_at_head = (git("rev-parse", "--verify", "--quiet"), lambda argv, _: HEAD + "\n")
        self.use([reviewed_at_head] + git_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Next: carry or drop 1 suggestion (/sdd-deliver --close-out)", out)
        self.assertEqual(0, self.run_main("flip", "--suggestions", "--dropped")[0])
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: yes", out)
        self.assertTrue(out.rstrip().endswith("Next: merge"), out)


class TestStatusStates(GitHubCase):
    """What status says with no pull request, a merged or closed one, and findings not mirrored."""

    def test_no_pull_request_is_not_mergeable(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN.replace("- a.go:9 · rename `n` to `count` · by: claude\n", ""))
        routes = [(git("rev-parse", "--verify", "--quiet"), HEAD + "\n"), (has("gh", "pr", "list"), "[]")] + self.routes()
        self.use(routes)
        _, out, _ = self.run_main("status")
        self.assertIn("forge: github · no pull request", out)
        self.assertIn("Mergeable: no — no pull request", out)
        self.assertIn("Next: open the pull request (/sdd-deliver step 8)", out)

    def test_a_merged_pull_request_says_so_and_names_the_cleanup(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN)
        self.PR = {"state": "MERGED", "mergeCommit": {"oid": "e" * 40}}
        self.use(self.routes())
        _, out, _ = self.run_main("status")
        self.assertIn("PR 7 merged at eeeeeee", out)
        self.assertIn("Mergeable: merged", out)
        self.assertIn("Next: delete %s, then the branch and its worktree" % self.store(), out)

    def test_the_open_pull_request_wins_over_a_newer_closed_one(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN)
        closed = {"number": 8, "headRefOid": HEAD, "headRefName": "feat/x", "baseRefName": "main", "state": "CLOSED"}
        opened = {"number": 7, "headRefOid": HEAD, "headRefName": "feat/x", "baseRefName": "main", "state": "OPEN"}
        self.use([(has("gh", "pr", "list"), json.dumps([closed, opened]))] + self.routes())
        _, out, _ = self.run_main("status")
        self.assertIn("PR 7 (ready)", out)
        self.assertNotIn("closed", out)

    def test_post_refuses_a_pull_request_that_is_not_open(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT)
        self.PR = {"state": "MERGED", "mergeCommit": {"oid": "e" * 40}}
        self.use(self.routes())
        code, _, err = self.run_main("post")
        self.assertEqual(2, code)
        self.assertIn("pull request 7 is merged", err)

    def test_a_pull_request_merged_before_the_head_moved_is_not_this_branchs(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT.replace("Base: main", "Base: develop"))
        self.PR = {"state": "MERGED", "headRefOid": "c" * 40, "baseRefName": "main", "mergeCommit": {"oid": "e" * 40}}
        self.use(self.routes())
        _, out, err = self.run_main("status")
        self.assertIn("forge: github · no pull request", out)
        self.assertNotIn("merged", out)
        self.assertIn("Base: develop\n", self.read_findings())

    def test_merged_names_what_the_file_still_holds(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT.replace("Base: main", "Base: develop"))
        self.PR = {"state": "MERGED", "mergeCommit": {"oid": "e" * 40}}
        self.use(self.routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: merged", out)
        self.assertIn("1 open line", out)
        # A pull request that is no longer open moves no Base: line.
        self.assertIn("Base: develop\n", self.read_findings())

    def test_a_closed_pull_request_is_not_mergeable(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN)
        self.PR = {"state": "CLOSED"}
        self.use(self.routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — pull request 7 is closed", out)
        self.assertIn("Next: reopen pull request 7, or open a new one", out)

    def test_findings_not_yet_mirrored_point_next_at_post(self):
        self.descriptor(forge="github")
        self.findings(FILE_OPEN_IMPORTANT)
        self.use(self.routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Next: sdd-pr post --pr 7", out)
        # can-fail control: once mirrored, triage is next.
        self.findings(FILE_OPEN_IMPORTANT.replace("by: claude", "by: claude · forge: 55"))
        self.use(self.routes(threads=[gh_thread(55, "a.go", 5, "x")]))
        _, out, _ = self.run_main("status")
        self.assertIn("Next: /sdd-triage", out)

    def test_an_unreachable_forge_is_a_reason(self):
        self.descriptor(forge="github")
        self.findings(FILE_CLEAN)
        self.use([(git("rev-parse", "--verify", "--quiet"), HEAD + "\n")] + git_routes() + [(has("gh"), sdd_pr.CliError("gh: not signed in"))])
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — the forge was not reachable", out)
        self.assertIn("Next: run sdd-pr status again once the forge is reachable", out)


class TestAttribution(GitHubCase):
    def test_a_thread_carries_its_reviewer_and_pull_reads_it_back(self):
        self.descriptor(forge="github")
        finding = sdd_pr.parse_line("- [ ] important · a.go:5 · one · evidence: ran it · by: go-coding:go-reviewer", 1)
        body = sdd_pr.comment_body(finding)
        self.assertIn("\n\nBy: go-coding:go-reviewer", body)
        self.use(self.routes(threads=[gh_thread(101, "a.go", 5, body, login="maint")]))
        self.assertEqual(0, self.run_main("pull")[0])
        self.assertIn("by: go-coding:go-reviewer · forge: 101", self.read_findings())


class TestCommandLine(RepoCase):
    def test_cli_errors_exit_2(self):
        self.use(git_routes())
        code, _, err = self.run_main("bogus")
        self.assertEqual(2, code)
        code, _, err = self.run_main("status", "--pr", "notanumber")
        self.assertEqual(2, code)
        # A missing CLI is exit 2 with the tool's name, not a traceback.
        self.use([(has("git"), sdd_pr.CliError("git: not found"))])
        code, _, err = self.run_main("status")
        self.assertEqual(2, code)
        self.assertIn("sdd-pr: git: not found", err)

    def test_version(self):
        code, out, _ = self.run_main("--version")
        self.assertEqual(0, code)
        self.assertEqual("sdd-pr %s" % sdd_pr.__version__, out.strip())
        self.assertEqual("0.10.0", sdd_pr.__version__)

    def test_run_cli_reports_a_missing_program(self):
        with self.assertRaises(sdd_pr.CliError) as caught:
            self._orig(["sdd-pr-no-such-program-xyz"])
        self.assertIn("sdd-pr-no-such-program-xyz", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

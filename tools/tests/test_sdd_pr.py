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
        return rest[: len(words)] == list(words)
    return predicate


def has(*needles):
    return lambda argv: all(n in argv for n in needles)


def git_routes(branch="feat/x", head=HEAD, remote="git@github.com:o/r.git", names="", diff=""):
    return [
        (git("rev-parse", "--abbrev-ref", "HEAD"), branch + "\n"),
        (git("rev-parse", "HEAD"), head + "\n"),
        (git("rev-parse", "--verify", "--quiet"), lambda argv, _: argv[-1].split("^")[0] + "\n"),
        (git("merge-base", "--is-ancestor"), ""),
        (git("merge-base"), MB + "\n"),
        (git("symbolic-ref"), "origin/main\n"),
        (git("remote", "get-url", "origin"), remote + "\n"),
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

    def findings(self, text):
        path = self.root / ".sdd" / "findings" / (sdd_pr.slug(self.BRANCH) + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read_findings(self):
        return (self.root / ".sdd" / "findings" / (sdd_pr.slug(self.BRANCH) + ".md")).read_text(encoding="utf-8")

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
        self.assertEqual(2, len(fs.resolved))
        fixed = [f for f in fs.resolved if f.status == "fixed"]
        declined = [f for f in fs.resolved if f.status == "declined"]
        self.assertEqual("4f0a1c2", fixed[0].fixed)
        self.assertTrue(declined[0].fields["declined"].startswith("the trap on line 3"))
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
        self.assertEqual(3, len(fs2.resolved))
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

    def test_scope_after_a_pass_starts_at_the_reviewed_sha(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT.replace(HEAD[:7], "9c1e2ab", 1))
        self.use(git_routes(names="a.go\n"))
        code, out, _ = self.run_main("scope", "--json")
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
        code, out, _ = self.run_main("scope")
        self.assertEqual(0, code)
        self.assertIn("range: %s..HEAD" % MB, out)

    def test_scope_is_empty_when_head_is_the_reviewed_commit(self):
        self.descriptor(forge="none")
        self.findings(FILE_OPEN_IMPORTANT)
        routes = git_routes()
        routes.insert(0, (git("rev-parse", "--verify", "--quiet"), HEAD + "\n"))
        self.use(routes)
        code, out, _ = self.run_main("scope")
        self.assertEqual(0, code)
        self.assertIn("range: empty", out)


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
        self.assertTrue(out.rstrip().endswith("Next: merge"), out)
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

    def _gh_routes(self, draft=False, checks=(), threads=()):
        pr = {
            "number": 7, "headRefOid": HEAD, "baseRefName": "main", "isDraft": draft,
            "url": "https://github.com/o/r/pull/7", "state": "OPEN", "statusCheckRollup": list(checks),
        }
        return [
            (has("gh", "pr", "list"), json.dumps([pr])),
            (has("gh", "pr", "view"), json.dumps(pr)),
            (has("gh", "repo", "view"), json.dumps({"owner": {"login": "o"}, "name": "r"})),
            (has("gh", "api", "graphql"), json.dumps(gh_threads(list(threads)))),
        ]

    def test_status_verdict_and_next(self):
        self.descriptor(forge="github")
        reviewed_at_head = (git("rev-parse", "--verify", "--quiet"), HEAD + "\n")
        # Open important → triage.
        self.findings(FILE_OPEN_IMPORTANT)
        self.use([reviewed_at_head] + git_routes() + self._gh_routes())
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — 1 important open", out)
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
        self.assertIn("Next: mark the pull request ready", out)
        # Nothing open, ready → merge.
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(checks=[{"status": "COMPLETED", "conclusion": "SUCCESS"}]))
        _, out, _ = self.run_main("status")
        self.assertIn("checks: pass", out)
        self.assertIn("Mergeable: yes", out)
        self.assertIn("Next: merge", out)
        # Failing checks.
        self.use([reviewed_at_head] + git_routes() + self._gh_routes(checks=[{"status": "COMPLETED", "conclusion": "FAILURE"}]))
        _, out, _ = self.run_main("status")
        self.assertIn("Mergeable: no — checks failing", out)

    def test_status_counts_a_build_or_ci_change_as_a_change_to_review(self):
        self.descriptor(forge="none")
        self.findings(FILE_CLEAN)
        routes = [(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names="Makefile\n.github/workflows/ci.yml\n")
        self.use(routes)
        _, out, _ = self.run_main("status")
        self.assertIn("(code changed since)", out)
        self.assertIn("Next: /sdd-review", out)
        # can-fail control: a document-only change is not.
        self.use([(git("rev-parse", "--verify", "--quiet"), "c" * 40 + "\n")] + git_routes(names="docs/x.md\n"))
        _, out, _ = self.run_main("status")
        self.assertIn("(no code change since)", out)
        self.assertIn("Next: merge", out)

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
    def routes(self, threads=(), diff="", extra=()):
        pr = {"number": 7, "headRefOid": HEAD, "baseRefName": "main", "isDraft": True,
              "url": "u", "state": "OPEN", "statusCheckRollup": []}
        return list(extra) + git_routes(diff=diff) + [
            (has("gh", "pr", "list"), json.dumps([pr])),
            (has("gh", "pr", "view"), json.dumps(pr)),
            (has("gh", "repo", "view"), json.dumps({"owner": {"login": "o"}, "name": "r"})),
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

    def routes(self, threads=(), diff="", on_post=None, on_patch=None):
        pr = {"pullRequestId": 7, "isDraft": False, "targetRefName": "refs/heads/main",
              "lastMergeSourceCommit": {"commitId": HEAD},
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

        return git_routes(remote=self.REMOTE, diff=diff) + [
            (has("az", "repos", "pr", "list"), json.dumps([pr])),
            (has("az", "repos", "pr", "show"), json.dumps(pr)),
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
        self.assertIn("### Not anchored to the diff", payload["body"])
        self.assertIn("z.go:40", payload["body"])
        self.assertNotIn("suggestion is never posted", json.dumps(payload))
        text = self.read_findings()
        self.assertIn("in the diff · evidence: ran it · fix: guard · by: claude · forge: 4242", text)
        self.assertIn("z.go:40 · outside the diff · by: claude · unanchored", text)

    def test_post_never_publishes_a_finding_twice(self):
        # The first post reads no id back: the line keeps no forge id.
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        posts = []

        def review(argv, stdin):
            posts.append(json.loads(stdin))
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

    def test_post_dry_run_writes_nothing(self):
        self.descriptor(forge="github")
        path = self.findings(FILE_TWO_OPEN)
        fake = self.use(self.routes(diff=DIFF))
        code, out, _ = self.run_main("post", "--dry-run")
        self.assertEqual(0, code)
        self.assertIn('"event": "COMMENT"', out)
        self.assertEqual(FILE_TWO_OPEN, path.read_text())
        self.assertFalse([a for a, _ in fake.calls if "POST" in a])

    def test_post_refuses_when_head_is_not_pushed(self):
        self.descriptor(forge="github")
        self.findings(FILE_TWO_OPEN)
        routes = [(git("rev-parse", "HEAD"), "d" * 40 + "\n")] + self.routes(diff=DIFF)
        self.use(routes)
        code, _, err = self.run_main("post")
        self.assertEqual(2, code)
        self.assertIn("push", err)


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
        text = self.read_findings()
        self.assertIn("by: claude · forge: 501", text)
        self.assertIn("unanchored", text)


FILE_RESOLVED = """# Findings — feat/x
Base: main
Reviewed %s · 2026-09-30 · claude: go-reviewer (1 of 1)

## Open

## Resolved
- [x] important · a.go:5 · one · by: claude · forge: 9 · fixed abc1234
- [-] important · a.go:6 · two · by: claude · forge: 10 · declined: the caller checks it
- [x] important · a.go:7 · three, never mirrored · by: claude · fixed abc1234
- [x] important · a.go:8 · four, done before · by: claude · forge: 11 · fixed abc1234 · mirrored

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

        threads = [gh_thread(9, "a.go", 5, "x"), gh_thread(10, "a.go", 6, "y"), gh_thread(11, "a.go", 8, "z")]
        extra = [(lambda a: a[:2] == ["gh", "api"] and a[2].endswith("/replies"), reply)]
        fake = self.use(self.routes(threads=threads, extra=extra))
        code, _, err = self.run_main("resolve")
        self.assertEqual(0, code, err)
        self.assertEqual("fixed in abc1234", replies["repos/o/r/pulls/7/comments/9/replies"])
        self.assertEqual("declined: the caller checks it", replies["repos/o/r/pulls/7/comments/10/replies"])
        self.assertEqual(2, len(replies))
        resolved = [a for a, _ in fake.calls if any("resolveReviewThread" in x for x in a)]
        self.assertEqual(2, len(resolved))
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
        self.assertEqual(["fixed in abc1234", "declined: the caller checks it"], [p["content"] for _, p in posts])
        self.assertTrue(all("pullRequestThreadComments" in a for a, _ in posts))
        self.assertEqual([{"status": "fixed"}, {"status": "wontFix"}], [p for _, p in patches])
        self.assertTrue(any("threadId=9" in a for a, _ in patches))


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
        self.assertEqual("0.8.0", sdd_pr.__version__)

    def test_run_cli_reports_a_missing_program(self):
        with self.assertRaises(sdd_pr.CliError) as caught:
            self._orig(["sdd-pr-no-such-program-xyz"])
        self.assertIn("sdd-pr-no-such-program-xyz", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

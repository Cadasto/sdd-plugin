#!/usr/bin/env python3
"""sdd-pr — the branch's findings file, mirrored to the pull request's inline threads.

Commands: status, scope, pull, post, resolve. One file, Python 3.9+, standard library only.
Every external call (git, gh, az) goes through run_cli(); the tests replace it.
Contract: references/review.md.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

__version__ = "0.8.1"

SEVERITIES = ("critical", "important", "suggestion")
BLOCKING = ("critical", "important")
SEP = " · "
FIELD_KEYS = ("evidence", "fix", "by", "forge", "declined", "deferred")
FLAGS = ("unanchored", "mirrored")
SECTIONS = ("Open", "Resolved", "Suggestions")
STATE_START, STATE_END = "<!-- sdd:review-state -->", "<!-- /sdd:review-state -->"
DESCRIPTOR = os.path.join("docs", ".sdd.yaml")
DEFAULT_TEST_GLOBS = ("*_test.go", "test_*.py", "*_test.py", "*Test.php", "*.test.ts", "*.spec.ts", "*_test.rs")
CODE_SUFFIXES = (
    ".go", ".py", ".php", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".java", ".kt", ".kts",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".swift", ".scala", ".sh", ".bash", ".sql",
    ".ex", ".exs", ".erl", ".hs", ".ml", ".lua", ".dart", ".vue", ".svelte",
)
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".adoc", ".txt")


class CliError(RuntimeError):
    """An external command failed or is missing, or the command line cannot run."""


class FileError(RuntimeError):
    """The findings file does not follow the grammar of references/review.md."""


class CheckoutError(CliError):
    """The pull request or --branch named is not what this checkout has."""


class StateError(CliError):
    """The pull request body's review-state markers are not one balanced pair."""


def run_cli(argv: List[str], stdin: Optional[str] = None) -> str:
    """Run one external command and return its standard output. The one door to the outside."""
    try:
        proc = subprocess.run(argv, input=stdin, capture_output=True, text=True)
    except OSError as exc:
        raise CliError("%s: %s" % (argv[0], exc.strerror or exc))
    if proc.returncode != 0:
        raise CliError((proc.stderr or proc.stdout).strip() or "%s failed" % argv[0])
    return proc.stdout


# ---------------------------------------------------------------- file model
def slug(branch: str) -> str:
    return branch.strip().replace("/", "--")


def findings_path(root: str, branch: str) -> str:
    return os.path.join(root, ".sdd", "findings", slug(branch) + ".md")


class Finding:
    __slots__ = ("status", "severity", "path", "line", "text", "fields", "flags", "fixed", "lineno")

    def __init__(self, status, severity, path, line, text, fields=None, flags=None, fixed=None, lineno=0):
        self.status, self.severity, self.path, self.line, self.text = status, severity, path, line, text
        self.fields, self.flags, self.fixed, self.lineno = dict(fields or {}), list(flags or []), fixed, lineno

    @property
    def anchor(self) -> str:
        return "%s:%s" % (self.path, self.line) if self.line else self.path

    def render(self) -> str:
        box = {"open": "- [ ] ", "fixed": "- [x] ", "declined": "- [-] ", "deferred": "- [~] ", "suggestion": "- "}[self.status]
        parts = [self.anchor] + ([self.text] if self.text else [])
        if self.status != "suggestion":
            parts.insert(0, self.severity)
        for key in ("evidence", "fix", "by", "forge"):
            if key in self.fields:
                parts.append("%s: %s" % (key, self.fields[key]))
        if self.status == "fixed" and self.fixed:
            parts.append("fixed " + self.fixed)
        if self.status in ("declined", "deferred"):
            parts.append("%s: %s" % (self.status, self.fields.get(self.status, "")))
        parts.extend(self.flags)
        return box + SEP.join(parts)


LINE_RE = re.compile(r"^- (\[( |x|X|-|~)\] )?(.*)$")


def parse_line(raw: str, lineno: int, section: str = "") -> Finding:
    """One finding line, classified by its checkbox wherever it stands: a line flipped in place,
    or appended at the end of the file, is filed under its section on the next write. The first
    field after ``path:line`` is always the sentence, so a sentence that starts with ``fixed`` or
    holds a colon is never read as a field."""
    match = LINE_RE.match(raw.rstrip())
    if not match:
        raise FileError("line %d: not a finding line" % lineno)
    box = match.group(2)
    parts = [p.strip() for p in match.group(3).split(SEP.strip())]
    parts = [p for p in parts if p != ""]
    status = "suggestion" if box is None else {" ": "open", "x": "fixed", "X": "fixed", "-": "declined", "~": "deferred"}[box]
    if box is None and parts and parts[0] in SEVERITIES:
        # A writer who left out the checkbox still named the severity.
        status = "open" if parts[0] in BLOCKING else "suggestion"
        if status == "suggestion":
            parts = parts[1:]
    if status != "suggestion":
        if not parts or parts[0] not in BLOCKING + ("suggestion",):
            raise FileError("line %d: first field must be a severity (%s)" % (lineno, ", ".join(SEVERITIES)))
        severity, parts = parts[0], parts[1:]
    else:
        severity = "suggestion"
    if not parts:
        raise FileError("line %d: missing path" % lineno)
    path, sep, line = parts[0].rpartition(":")
    if not sep or not line.isdigit():
        path, line = parts[0], ""
    text = parts[1] if len(parts) > 1 else ""
    fields, flags, fixed = {}, [], None
    for part in parts[2:]:
        key, colon, value = part.partition(":")
        if colon and key in FIELD_KEYS:
            fields[key] = value.strip()
        elif part.startswith("fixed ") and status == "fixed" and fixed is None:
            fixed = part[len("fixed "):].strip()
        elif part in FLAGS:
            flags.append(part)
        else:
            text += SEP + part
    return Finding(status, severity, path, line, text, fields, flags, fixed, lineno)


class Findings:
    def __init__(self, branch: str = "", base: str = ""):
        self.branch, self.base = branch, base
        #: One tuple per pass: (sha, date, agent, reviewers).
        self.reviewed: List[Tuple[str, str, str, str]] = []
        self.items: List[Finding] = []

    @property
    def open(self) -> List[Finding]:
        return [f for f in self.items if f.status == "open"]

    @property
    def resolved(self) -> List[Finding]:
        return [f for f in self.items if f.status in ("fixed", "declined", "deferred")]

    @property
    def suggestions(self) -> List[Finding]:
        return [f for f in self.items if f.status == "suggestion"]

    @property
    def passes(self) -> List[Tuple[str, str, str, str]]:
        """The Reviewed lines some reviewer reported on; a `(0 of m)` line reviewed nothing."""
        return [r for r in self.reviewed if not _nobody_reported(r[3])]

    def unreviewed_passes(self) -> List[str]:
        """The shas of `(0 of m)` lines written after the last real pass."""
        last = max([i for i, r in enumerate(self.reviewed) if not _nobody_reported(r[3])], default=-1)
        return [r[0] for r in self.reviewed[last + 1:]]

    def last_reviewed_sha(self) -> Optional[str]:
        return self.passes[-1][0] if self.passes else None

    def forge_ids(self) -> set:
        return {f.fields["forge"] for f in self.items if f.fields.get("forge")}


REVIEWED_RE = re.compile(r"^Reviewed (\S+) · (\S+) · ([^:]+): (.*)$")
COUNT_RE = re.compile(r"\((\d+) of (\d+)\)\s*$")


def _nobody_reported(reviewers: str) -> bool:
    match = COUNT_RE.search(reviewers)
    return bool(match) and match.group(1) == "0"
TITLE = "# Findings — "


def parse(text: str) -> Findings:
    fs, section = Findings(), ""
    for index, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(TITLE.strip()):
            fs.branch = line[len(TITLE.strip()):].strip()
            continue
        if line.startswith("Base:") and not section:
            fs.base = line[len("Base:"):].strip()
            continue
        match = REVIEWED_RE.match(line)
        if match:
            fs.reviewed.append((match.group(1), match.group(2), match.group(3), match.group(4)))
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            if section not in SECTIONS:
                raise FileError("line %d: unknown section %r" % (index, section))
            continue
        if line.startswith("- ") and section:
            fs.items.append(parse_line(line, index, section))
            continue
        raise FileError("line %d: unexpected text %r" % (index, line[:60]))
    return fs


def render(fs: Findings) -> str:
    out = [TITLE + fs.branch, "Base: " + fs.base]
    out += ["Reviewed %s · %s · %s: %s" % r for r in fs.reviewed]
    for title, items in (("Open", fs.open), ("Resolved", fs.resolved), ("Suggestions", fs.suggestions)):
        out += ["", "## " + title] + [f.render() for f in items]
    return "\n".join(out) + "\n"


def load_findings(root: str, branch: str, base: str) -> Findings:
    path = findings_path(root, branch)
    if not os.path.exists(path):
        return Findings(branch, base)
    with open(path, encoding="utf-8") as handle:
        fs = parse(handle.read())
    fs.branch = fs.branch or branch
    fs.base = fs.base or base
    return fs


def save_findings(root: str, fs: Findings) -> None:
    path = findings_path(root, fs.branch)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(render(fs))
    os.replace(tmp, path)


def severity_of(body: str) -> str:
    match = re.match(r"\s*\*\*(critical|important)\*\*", body or "")
    return match.group(1) if match else "important"


def first_sentence(body: str) -> str:
    """The thread's first line, with a leading **severity** marker and separator dropped."""
    text = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    text = re.sub(r"^\s*\*\*(critical|important|suggestion)\*\*\s*[—:\-–]?\s*", "", text)
    return text.replace(SEP.strip(), "-").strip() or "(no text)"


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_hunks(diff_text: str) -> Dict[str, set]:
    """The new-side line numbers each file's hunks cover: the lines a review may anchor to."""
    lines: Dict[str, set] = {}
    path = None
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else (target[2:] if target.startswith("b/") else target)
            continue
        match = HUNK.match(raw)
        if match and path:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            lines.setdefault(path, set()).update(range(start, start + count))
    return lines


def comment_body(finding: Finding) -> str:
    body = "**%s** — %s" % (finding.severity, finding.text)
    if finding.fields.get("evidence"):
        body += "\n\nEvidence: " + finding.fields["evidence"]
    if finding.fields.get("fix"):
        body += "\n\nFix: " + finding.fields["fix"]
    return body


def reply_for(finding: Finding) -> str:
    if finding.status == "fixed":
        return "fixed in %s" % (finding.fixed or "this branch")
    return "%s: %s" % (finding.status, finding.fields.get(finding.status, ""))


def review_state(fs: Findings, head: str) -> str:
    """The review-state block for the pull request's body: the file projected, never a second store."""
    blocking = [f for f in fs.items if f.severity in BLOCKING and f.status != "suggestion"]
    count = {s: len([f for f in blocking if f.status == s or f.severity == s]) for s in BLOCKING + ("fixed", "declined", "deferred")}
    opened = {s: len([f for f in fs.open if f.severity == s]) for s in BLOCKING}
    if any(opened.values()):
        verdict = "%d critical and %d important open" % (opened["critical"], opened["important"])
    else:
        verdict = "no critical or important finding open" if fs.passes else "not reviewed"
    out = [STATE_START, "**Review state at `%s`:** %s" % (head[:7], verdict)]
    out += ["- Pass at `%s`, %s, %s: %s" % (sha[:7], date, agent, reviewers) for sha, date, agent, reviewers in fs.passes]
    if not fs.passes:
        out.append("- Passes: none")
    suggestions = len(fs.suggestions)
    out.append("- Findings: %d critical and %d important; %d fixed, %d declined, %d deferred; %d suggestion%s not worked"
               % (count["critical"], count["important"], count["fixed"], count["declined"], count["deferred"],
                  suggestions, "" if suggestions == 1 else "s"))
    out += ["- Deferred: %s at `%s`, %s: %s" % (f.severity, f.anchor, f.text, f.fields.get("deferred", ""))
            for f in blocking if f.status == "deferred"]
    return "\n".join(out + [STATE_END])


START_LINE = re.compile(r"^%s[ \t]*$" % re.escape(STATE_START), re.M)
END_LINE = re.compile(r"^%s[ \t]*$" % re.escape(STATE_END), re.M)


def _state_span(body: str) -> Optional[Tuple[int, int]]:
    """Where the block sits: markers count only as whole lines, and only as one balanced pair."""
    starts, ends = list(START_LINE.finditer(body)), list(END_LINE.finditer(body))
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0].start() < starts[0].start():
        raise StateError("the review-state markers in the pull request body are not one balanced pair")
    return starts[0].start(), ends[0].end()


def read_state(body: str) -> Optional[str]:
    body = (body or "").replace("\r\n", "\n")
    span = _state_span(body)
    return body[span[0]:span[1]] if span else None


def splice(body: str, block: str) -> str:
    """The body with its review-state block replaced in place, or appended when it has none."""
    body = (body or "").replace("\r\n", "\n")
    span = _state_span(body)
    if span:
        return body[:span[0]] + block + body[span[1]:]
    return (body.rstrip("\n") + "\n\n" if body.strip() else "") + block + "\n"


# ---------------------------------------------------------------- git and the descriptor
def git(root: str, *args: str) -> str:
    return run_cli(["git", "-C", root] + list(args))


def read_descriptor(root: str) -> str:
    try:
        with open(os.path.join(root, DESCRIPTOR), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def descriptor_value(text: str, key: str) -> str:
    match = re.search(r"^\s*%s:\s*([^#\n]*)" % re.escape(key), text, re.M)
    return match.group(1).strip().strip("'\"") if match else ""


def test_globs(text: str) -> List[str]:
    match = re.search(r"^\s*test_globs:\s*\[(.*?)\]", text, re.M)
    if not match:
        return list(DEFAULT_TEST_GLOBS)
    globs = [g.strip().strip("'\"") for g in match.group(1).split(",")]
    return [g for g in globs if g] or list(DEFAULT_TEST_GLOBS)


def kind_of(path: str, globs: List[str]) -> str:
    name = path.rsplit("/", 1)[-1]
    parts = path.split("/")
    if any(fnmatch.fnmatch(name, g) for g in globs) or any(p in ("test", "tests") for p in parts[:-1]):
        return "tests"
    suffix = os.path.splitext(name)[1].lower()
    if parts[0] == "docs" or suffix in DOC_SUFFIXES:
        return "documents"
    if suffix in CODE_SUFFIXES:
        return "code"
    return "other"


def checked_out(root: str) -> str:
    """The checked-out branch, or "" on a detached HEAD."""
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return "" if branch == "HEAD" else branch


def worktree_of(root: str, branch: str) -> str:
    """The path of the worktree that has ``branch`` checked out, or ""."""
    try:
        listing = git(root, "worktree", "list", "--porcelain")
    except CliError:
        return ""
    path = ""
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
        elif line.strip() == "branch refs/heads/" + branch:
            return path
    return ""


def elsewhere(root: str, branch: str) -> str:
    """How to reach ``branch``: its worktree's --root, or a checkout of it."""
    path = worktree_of(root, branch)
    return "pass --root %s" % path if path else "check out %s, or pass --root with its worktree" % branch


def resolve_sha(root: str, sha: str) -> str:
    try:
        return git(root, "rev-parse", "--verify", "--quiet", sha + "^{commit}").strip()
    except CliError:
        return ""


def base_ref(root: str, base: str) -> str:
    """The base as a ref this clone has: the local branch, else its remote-tracking copy."""
    if resolve_sha(root, base) or not resolve_sha(root, "origin/" + base):
        return base
    return "origin/" + base


def review_range(root: str, fs: Findings, base: str, head: str, whole: bool = False) -> Optional[str]:
    """The range the next pass reads, or ``None`` when nothing is new (review.md § Scope). A last
    pass that is no longer an ancestor of HEAD (the branch was rebased) restarts at the merge base."""
    last = None if whole else fs.last_reviewed_sha()
    if last:
        full = resolve_sha(root, last)
        if full == head:
            return None
        if full:
            try:
                git(root, "merge-base", "--is-ancestor", full, "HEAD")
                return "%s..HEAD" % last
            except CliError:
                pass
    merge_base = git(root, "merge-base", base_ref(root, base), "HEAD").strip()
    if merge_base == head:
        return None
    return "%s..HEAD" % merge_base


def changed_files(root: str, rng: Optional[str], globs: List[str]) -> Dict[str, List[str]]:
    files: Dict[str, List[str]] = {"code": [], "tests": [], "documents": [], "other": []}
    if not rng:
        return files
    for path in git(root, "diff", "--name-only", rng).splitlines():
        path = path.strip()
        if path:
            files[kind_of(path, globs)].append(path)
    return files


# ---------------------------------------------------------------- the forge interface
def _json(text: str):
    try:
        return json.loads(text or "null")
    except ValueError as exc:
        raise CliError("unreadable JSON from the forge CLI: %s" % exc)


class Forge:
    """What the commands need from a forge. Local git supplies the diff on every forge."""

    name = "none"
    body_limit = 65536  # characters the forge takes in a pull request body

    def pr_for_branch(self, branch: str) -> Optional[dict]:  # {"number", "head", "base", "draft", "url"}
        raise CliError("no forge configured")

    def pr(self, number: int) -> dict:
        raise CliError("no forge configured")

    def checks(self, number: int) -> str:  # pass | fail | pending | none | not read
        return "not read"

    def threads(self, number: int) -> List[dict]:  # {"id", "node", "resolved", "path", "line", "body", "author"}
        raise CliError("no forge configured")

    def post(self, number: int, sha: str, body: str, comments: List[dict]) -> List[str]:
        raise CliError("no forge configured")

    def resolve(self, number: int, thread_id: str, reply: str, state: str) -> None:  # fixed | declined | deferred
        raise CliError("no forge configured")

    def body(self, number: int) -> str:
        raise CliError("no forge configured")

    def set_body(self, number: int, body: str) -> None:
        raise CliError("no forge configured")


THREADS_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!,$after:String){repository(owner:$owner,name:$name)"
    "{pullRequest(number:$number){reviewThreads(first:100,after:$after){nodes{id isResolved isOutdated "
    "path line originalLine comments(first:1){nodes{databaseId body author{login}}}} "
    "pageInfo{hasNextPage endCursor}}}}}"
)
RESOLVE_MUTATION = "mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}"
FAILED_CHECKS = ("FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE")


class GitHubForge(Forge):
    """GitHub through `gh`: reviews, review threads, and resolveReviewThread."""

    name = "github"

    def __init__(self):
        self._repo: Optional[Tuple[str, str]] = None

    def _owner_name(self) -> Tuple[str, str]:
        if self._repo is None:
            data = _json(run_cli(["gh", "repo", "view", "--json", "owner,name"]))
            self._repo = (data["owner"]["login"], data["name"])
        return self._repo

    @staticmethod
    def _shape(data: dict) -> dict:
        return {"number": data["number"], "head": data.get("headRefOid", ""), "branch": data.get("headRefName", ""),
                "base": data.get("baseRefName", ""), "draft": bool(data.get("isDraft")), "url": data.get("url", ""),
                "raw": data}

    def pr_for_branch(self, branch):
        data = _json(run_cli(["gh", "pr", "list", "--head", branch, "--state", "open",
                              "--json", "number,headRefOid,headRefName,baseRefName,isDraft,url"]))
        return self._shape(data[0]) if data else None

    def pr(self, number):
        return self._shape(_json(run_cli(["gh", "pr", "view", str(number), "--json",
                                          "number,headRefOid,headRefName,baseRefName,isDraft,url,statusCheckRollup,state"])))

    def checks(self, number):
        rollup = self.pr(number)["raw"].get("statusCheckRollup") or []
        if not rollup:
            return "none"
        state = "pass"
        for item in rollup:
            conclusion = (item.get("conclusion") or item.get("state") or "").upper()
            if conclusion in FAILED_CHECKS:
                return "fail"
            status = (item.get("status") or "").upper()
            if (status and status != "COMPLETED") or conclusion in ("PENDING", "EXPECTED"):
                state = "pending"
        return state

    def threads(self, number):
        owner, name = self._owner_name()
        out, after = [], None
        while True:
            argv = ["gh", "api", "graphql", "-f", "query=" + THREADS_QUERY, "-f", "owner=" + owner,
                    "-f", "name=" + name, "-F", "number=%d" % number]
            if after:
                argv += ["-f", "after=" + after]
            data = _json(run_cli(argv))
            block = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            for node in block["nodes"]:
                comments = node.get("comments", {}).get("nodes") or [{}]
                first = comments[0]
                out.append({
                    "id": str(first.get("databaseId", "")), "node": node.get("id", ""),
                    "resolved": bool(node.get("isResolved")), "path": node.get("path", ""),
                    "line": node.get("line") or node.get("originalLine") or "",
                    "body": first.get("body", ""), "author": (first.get("author") or {}).get("login", ""),
                })
            if not block["pageInfo"].get("hasNextPage"):
                return out
            after = block["pageInfo"]["endCursor"]

    def post(self, number, sha, body, comments):
        owner, name = self._owner_name()
        payload = {"commit_id": sha, "event": "COMMENT", "body": body,
                   "comments": [{"path": c["path"], "line": c["line"], "side": "RIGHT", "body": c["body"]}
                                for c in comments]}
        review = _json(run_cli(["gh", "api", "repos/%s/%s/pulls/%d/reviews" % (owner, name, number),
                                "--method", "POST", "--input", "-"], stdin=json.dumps(payload)))
        posted = _json(run_cli(["gh", "api", "repos/%s/%s/pulls/%d/reviews/%s/comments?per_page=100"
                                % (owner, name, number, review["id"])])) or []
        ids = []
        for comment in comments:
            # The per-review listing carries no `line`: match on the path and the body, which tells two
            # findings on one line apart, and on the line only where the listing has one.
            match = [p for p in posted if (p.get("path"), p.get("body")) == (comment["path"], comment["body"])
                     and (p.get("line") or p.get("original_line")) in (None, comment["line"])]
            chosen = match[0] if match else {}
            if chosen:
                posted.remove(chosen)
            ids.append(str(chosen.get("id", "")))
        return ids

    def body(self, number):
        return _json(run_cli(["gh", "pr", "view", str(number), "--json", "body"])).get("body") or ""

    def set_body(self, number, body):
        run_cli(["gh", "pr", "edit", str(number), "--body-file", "-"], stdin=body)

    def resolve(self, number, thread_id, reply, state):
        owner, name = self._owner_name()
        run_cli(["gh", "api", "repos/%s/%s/pulls/%d/comments/%s/replies" % (owner, name, number, thread_id),
                 "--method", "POST", "--input", "-"], stdin=json.dumps({"body": reply}))
        nodes = {t["id"]: t["node"] for t in self.threads(number)}
        node = nodes.get(str(thread_id))
        if not node:
            raise CliError("thread %s is not on pull request %d" % (thread_id, number))
        run_cli(["gh", "api", "graphql", "-f", "query=" + RESOLVE_MUTATION, "-f", "id=" + node])


class AzureDevOpsForge(Forge):
    """Azure DevOps through `az`: pull-request threads with their native status."""

    name = "azure-devops"
    body_limit = 4000

    def __init__(self, org: str = "", project: str = "", repo: str = ""):
        self.org, self.project, self.repo = org, project, repo
        self._ids: Dict[int, Tuple[str, str]] = {}

    def _org(self) -> List[str]:
        return ["--org", self.org] if self.org else []

    def _shape(self, data: dict) -> dict:
        repository = data.get("repository") or {}
        number = int(data["pullRequestId"])
        self._ids[number] = ((repository.get("project") or {}).get("name", self.project), repository.get("id", self.repo))
        return {"number": number, "head": (data.get("lastMergeSourceCommit") or {}).get("commitId", ""),
                "branch": _short_ref(data.get("sourceRefName", "")), "base": _short_ref(data.get("targetRefName", "")),
                "draft": bool(data.get("isDraft")), "url": data.get("url", ""), "raw": data}

    def pr_for_branch(self, branch):
        argv = ["az", "repos", "pr", "list", "--source-branch", "refs/heads/" + branch, "--status", "active",
                "-o", "json"] + self._org()
        if self.project:
            argv += ["--project", self.project]
        if self.repo:
            argv += ["--repository", self.repo]
        data = _json(run_cli(argv))
        return self._shape(data[0]) if data else None

    def pr(self, number):
        return self._shape(_json(run_cli(["az", "repos", "pr", "show", "--id", str(number), "-o", "json"] + self._org())))

    def _invoke(self, number: int, resource: str, extra_route: List[str], method: str = "GET",
                payload: Optional[dict] = None):
        if number not in self._ids:
            self.pr(number)
        project, repo = self._ids[number]
        argv = ["az", "devops", "invoke", "--area", "git", "--resource", resource, "--route-parameters",
                "project=%s" % project, "repositoryId=%s" % repo, "pullRequestId=%d" % number] + extra_route
        argv += ["--api-version", "7.1", "-o", "json"] + self._org()
        if payload is None:
            return _json(run_cli(argv))
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(payload, handle)
            handle.close()
            return _json(run_cli(argv + ["--http-method", method, "--in-file", handle.name]))
        finally:
            os.unlink(handle.name)

    def threads(self, number):
        out = []
        for thread in (self._invoke(number, "pullRequestThreads", []) or {}).get("value", []):
            context = thread.get("threadContext") or {}
            if not context.get("filePath"):
                continue
            if thread.get("isDeleted"):
                continue
            first = (thread.get("comments") or [{}])[0]
            start = context.get("rightFileStart") or context.get("leftFileStart") or {}
            out.append({
                "id": str(thread.get("id", "")), "node": str(thread.get("id", "")),
                "resolved": thread.get("status") not in ("active", "pending"),
                "path": context["filePath"].lstrip("/"),
                "line": start.get("line", ""), "body": first.get("content", ""),
                "author": (first.get("author") or {}).get("displayName", ""),
            })
        return out

    def post(self, number, sha, body, comments):
        ids = []
        for comment in comments:
            line = {"line": comment["line"], "offset": 1}
            created = self._invoke(number, "pullRequestThreads", [], "POST", {
                "status": "active",
                "comments": [{"parentCommentId": 0, "commentType": 1, "content": comment["body"]}],
                "threadContext": {"filePath": "/" + comment["path"], "rightFileStart": line, "rightFileEnd": dict(line)},
            })
            ids.append(str(created.get("id", "")))
        if body:
            self._invoke(number, "pullRequestThreads", [], "POST", {
                "status": "active", "comments": [{"parentCommentId": 0, "commentType": 1, "content": body}]})
        return ids

    def resolve(self, number, thread_id, reply, state):
        route = ["threadId=%s" % thread_id]
        self._invoke(number, "pullRequestThreadComments", route, "POST",
                     {"parentCommentId": 1, "content": reply, "commentType": 1})
        status = {"fixed": "fixed", "declined": "wontFix", "deferred": "closed"}[state]
        self._invoke(number, "pullRequestThreads", route, "PATCH", {"status": status})

    def body(self, number):
        return self.pr(number)["raw"].get("description") or ""

    def set_body(self, number, body):
        self._invoke(number, "pullRequests", [], "PATCH", {"description": body})


def _short_ref(ref: str) -> str:
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


def _azure_from_remote(url: str) -> Optional[AzureDevOpsForge]:
    patterns = (
        r"https?://(?:[^@/]+@)?dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)",
        r"https?://(?P<org>[^./]+)\.visualstudio\.com/(?:DefaultCollection/)?(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)",
        r"(?:[^@]+@)?ssh\.dev\.azure\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+)",
        r"(?:[^@]+@)?vs-ssh\.visualstudio\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+)",
    )
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            org = unquote(match.group("org"))
            host = "https://%s.visualstudio.com" % org if "visualstudio.com" in url else "https://dev.azure.com/" + org
            repo = unquote(match.group("repo"))
            repo = repo[: -len(".git")] if repo.endswith(".git") else repo
            return AzureDevOpsForge(host, unquote(match.group("project")), repo)
    if "dev.azure.com" in url or "visualstudio.com" in url:
        return AzureDevOpsForge()
    return None


def detect_forge(root: str) -> Forge:
    """The descriptor's `forge:` unless `auto`; else the remote URL; else no forge."""
    configured = descriptor_value(read_descriptor(root), "forge") or "auto"
    remote = ""
    try:
        remote = git(root, "remote", "get-url", "origin").strip()
    except CliError:
        remote = ""
    if configured == "none":
        return Forge()
    if configured == "github":
        return GitHubForge()
    if configured == "azure-devops":
        return _azure_from_remote(remote) or AzureDevOpsForge()
    if configured != "auto":
        raise CliError("forge: '%s' is not auto | github | azure-devops | none" % configured)
    if re.search(r"(^|[@/.])github\.com[:/]", remote):
        return GitHubForge()
    azure = _azure_from_remote(remote)
    return azure or Forge()


# ---------------------------------------------------------------- commands
class Session:
    """What every command resolves first: root, branch, head, base, the file and the forge."""

    def __init__(self, args):
        self.root = args.root
        self.head = git(self.root, "rev-parse", "HEAD").strip()
        checked = checked_out(self.root)
        if args.branch and args.branch != checked:
            # On a detached HEAD, --branch names the branch whose tip this is; otherwise it is the checkout.
            tip = resolve_sha(self.root, args.branch) or resolve_sha(self.root, "origin/" + args.branch)
            if checked or tip != self.head:
                raise CheckoutError("--branch %s is not this checkout (%s at %s); %s"
                                    % (args.branch, checked or "detached HEAD", self.head[:7],
                                       elsewhere(self.root, args.branch)))
        self.branch = args.branch or checked
        if not self.branch:
            raise CliError("detached HEAD; pass --branch")
        self.forge = detect_forge(self.root)
        self.descriptor = read_descriptor(self.root)
        self.globs = test_globs(self.descriptor)
        self._pr_number = args.pr
        self._pr: Optional[dict] = None
        self.dry_run = getattr(args, "dry_run", False)
        self.fs = load_findings(self.root, self.branch, "")

    def pr(self, required: bool = True) -> Optional[dict]:
        if self._pr is None:
            if self._pr_number is not None:
                pr = self.forge.pr(self._pr_number)
                if pr.get("branch") and pr["branch"] != self.branch and not self.holds(pr["head"]):
                    raise CheckoutError("pull request %d is %s at %s; this checkout is %s at %s; %s"
                                        % (pr["number"], pr["branch"], pr["head"][:7], self.branch,
                                           self.head[:7], elsewhere(self.root, pr["branch"])))
                self._pr = pr
            else:
                self._pr = self.forge.pr_for_branch(self.branch)
            if self._pr is None and required:
                raise CliError("no open pull request for %s; pass --pr" % self.branch)
            if self._pr and self._pr.get("base") and self.fs.base and self._pr["base"] != self.fs.base:
                # A retargeted pull request: the file's base follows it, so the range starts at the right place.
                print("sdd-pr: Base %s -> %s, the base of pull request %d"
                      % (self.fs.base, self._pr["base"], self._pr["number"]), file=sys.stderr)
                self.fs.base = self._pr["base"]
                if os.path.exists(findings_path(self.root, self.branch)) and not self.dry_run:
                    self.save()
        return self._pr

    def holds(self, sha: str) -> bool:
        """Whether this checkout contains ``sha``: a local branch under another name, or commits not pushed yet."""
        if not sha:
            return False
        if sha == self.head:
            return True
        try:
            git(self.root, "merge-base", "--is-ancestor", sha, "HEAD")
            return True
        except CliError:
            return False

    def base(self) -> str:
        """The file's base, else the pull request's, else the remote's default branch, else main."""
        if self.fs.base:
            return self.fs.base
        if self.forge.name != "none":
            try:
                pr = self.pr(required=False)
                if pr and pr.get("base"):
                    return pr["base"]
            except CliError:
                pass
        try:
            default = git(self.root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD").strip()
            if default:
                return default[len("origin/"):] if default.startswith("origin/") else default
        except CliError:
            pass
        return "main"

    def has_file(self) -> bool:
        return os.path.exists(findings_path(self.root, self.branch))

    def need_forge(self) -> None:
        if self.forge.name == "none":
            raise CliError("no forge configured (forge: none, or a remote the tool does not recognise)")

    def save(self) -> None:
        self.fs.base = self.fs.base or self.base()
        self.fs.branch = self.fs.branch or self.branch
        save_findings(self.root, self.fs)


def write_state(session: Session, pr: dict) -> None:
    """Rewrite the pull request's review-state block from the file; send nothing when it is current."""
    if not session.has_file():
        raise CliError("no findings file for %s here; run where the file is" % session.branch)
    if pr["head"] and pr["head"] != session.head:
        raise CliError("local HEAD %s is not the pull request's head %s; push or pull first"
                       % (session.head[:7], pr["head"][:7]))
    body = session.forge.body(pr["number"])
    new = splice(body, review_state(session.fs, pr["head"] or session.head))
    if len(new) > session.forge.body_limit:
        raise CliError("the body would be %d characters with the review state, over the %d the forge takes; shorten it"
                       % (len(new), session.forge.body_limit))
    if new != body.replace("\r\n", "\n"):
        session.forge.set_body(pr["number"], new)


def refresh_state(session: Session, pr: dict) -> None:
    """After post and resolve: keep the block in step, and say so when it cannot be."""
    if not session.has_file():
        return
    try:
        write_state(session, pr)
    except CliError as exc:
        print("sdd-pr: review state not written: %s" % str(exc).splitlines()[0], file=sys.stderr)


def state_problem(session: Session, pr: dict) -> Tuple[str, str]:
    """What is wrong with the review state on the pull request, and what to run; ("", "") when current."""
    try:
        body = session.forge.body(pr["number"])
    except CliError as exc:
        return ("the review state on the pull request was not read (%s)" % str(exc).splitlines()[0],
                "sdd-pr status --pr %d" % pr["number"])
    try:
        state = read_state(body)
    except StateError as exc:
        return str(exc), "repair the review-state markers in the pull request body"
    expected = review_state(session.fs, pr["head"] or session.head)
    if state == expected:
        return "", ""
    size = len(splice(body, expected))
    if size > session.forge.body_limit:
        return ("the pull request body is too long to carry the review state (%d of %d characters)"
                % (size, session.forge.body_limit), "shorten the pull request body")
    return ("the review state on the pull request is %s" % ("missing" if state is None else "stale"),
            "sdd-pr status --write-body --pr %d" % pr["number"])


def cmd_scope(session: Session, args) -> int:
    if args.pr is not None and session.forge.name != "none":
        session.pr()
    rng = review_range(session.root, session.fs, session.base(), session.head, whole=args.all)
    files = changed_files(session.root, rng, session.globs)
    if args.json:
        print(json.dumps({"range": rng, "base": session.base(), "head": session.head, "files": files}, indent=2))
        return 0
    print("range: %s" % (rng or "empty"))
    for kind in ("code", "tests", "documents", "other"):
        if files[kind]:
            print("%s: %s" % (kind, " ".join(files[kind])))
    return 0


def cmd_status(session: Session, args) -> int:
    fs = session.fs
    pr, unreachable = None, ""
    if args.write_body:
        session.need_forge()
        write_state(session, session.pr())
    if session.forge.name != "none":
        try:
            pr = session.pr(required=False)
        except CheckoutError:
            raise
        except CliError as exc:
            unreachable = str(exc).splitlines()[0]
    last = fs.last_reviewed_sha()
    rng = review_range(session.root, fs, session.base(), session.head)
    files = changed_files(session.root, rng, session.globs)
    code_changed = bool(files["code"] or files["tests"] or files["other"])
    changed = code_changed or bool(files["documents"])
    since = "code changed" if code_changed else "documents changed" if changed else "no change"
    print("branch %s · base %s · head %s · last reviewed %s (%s since)"
          % (session.branch, session.base(), session.head[:7], (last or "none")[:7], since))
    for sha in fs.unreviewed_passes():
        print("Reviewed %s: no reviewer reported; not a pass" % sha[:7])
    counts = {s: len([f for f in fs.open if f.severity == s]) for s in BLOCKING}
    print("open: %d critical, %d important · suggestions: %d"
          % (counts["critical"], counts["important"], len(fs.suggestions)))
    for finding in fs.open:
        print(finding.render())

    reasons: List[str] = []
    if counts["critical"] or counts["important"]:
        parts = ["%d %s" % (counts[s], s) for s in BLOCKING if counts[s]]
        reasons.append(", ".join(parts) + " open")
    nxt = "/sdd-triage" if reasons else ""
    if code_changed and last:
        # Steers Next only: after the pass budget is spent, a fix does not reopen review. A change to
        # documents alone does not steer: the close-out's own commit is one.
        nxt = nxt or "/sdd-review"
    elif not last and changed:
        reasons.append("not reviewed yet")
        nxt = nxt or "/sdd-review"

    if session.forge.name == "none":
        print("forge: none")
    elif unreachable:
        print("forge: %s · not reachable (%s)" % (session.forge.name, unreachable))
    else:
        try:
            if pr is None:
                print("forge: %s · no pull request" % session.forge.name)
            else:
                shown_open = {f.fields["forge"] for f in fs.open if f.fields.get("forge")}
                unknown = [t for t in session.forge.threads(pr["number"]) if not t["resolved"] and t["id"] not in shown_open]
                checks = session.forge.checks(pr["number"])
                print("forge: %s · PR %d (%s) · %d unresolved threads not open in the file · checks: %s"
                      % (session.forge.name, pr["number"], "draft" if pr["draft"] else "ready", len(unknown), checks))
                if unknown:
                    reasons.append("%d unresolved threads not open in the file" % len(unknown))
                    nxt = nxt or "sdd-pr pull --pr %d" % pr["number"]
                if not session.has_file():
                    print("review state not checked: no findings file here")
                else:
                    problem, repair = state_problem(session, pr)
                    if problem:
                        reasons.append(problem)
                        nxt = nxt or repair
                if checks == "fail":
                    reasons.append("checks failing")
                    nxt = nxt or "fix the failing checks"
                elif checks == "pending":
                    reasons.append("checks pending")
                    nxt = nxt or "wait for the checks"
                if pr["draft"]:
                    reasons.append("the pull request is a draft")
                    nxt = nxt or "mark the pull request ready"
        except CliError as exc:
            print("forge: %s · not reachable (%s)" % (session.forge.name, str(exc).splitlines()[0]))
    print("Mergeable: yes" if not reasons else "Mergeable: no — " + "; ".join(reasons))
    print("Next: " + (nxt or "merge"))
    return 0


def cmd_pull(session: Session, args) -> int:
    session.need_forge()
    pr = session.pr()
    fs = session.fs
    known = fs.forge_ids()
    by_id = {f.fields["forge"]: f for f in fs.resolved if f.fields.get("forge")}
    added = 0
    for thread in session.forge.threads(pr["number"]):
        if thread["resolved"] or not thread["id"]:
            continue
        reopened = by_id.get(thread["id"])
        if reopened is not None:
            # The thread is open again on the forge (a decline rejected, a fix disputed): so is the line.
            reopened.status, reopened.fixed = "open", None
            reopened.fields.pop("declined", None)
            reopened.flags = [flag for flag in reopened.flags if flag != "mirrored"]
            added += 1
            continue
        if thread["id"] in known:
            continue
        fields = {"by": thread["author"] or "forge", "forge": thread["id"]}
        fs.items.append(Finding("open", severity_of(thread["body"]), thread["path"], str(thread["line"] or ""),
                                first_sentence(thread["body"]), fields))
        known.add(thread["id"])
        added += 1
    if added or not os.path.exists(findings_path(session.root, session.branch)):
        session.save()
    print("pull: %d new finding%s from PR %d" % (added, "" if added == 1 else "s", pr["number"]))
    return 0


def cmd_post(session: Session, args) -> int:
    session.need_forge()
    pr = session.pr()
    code = _post(session, args, pr)
    if not args.dry_run:
        refresh_state(session, pr)
    return code


def _post(session: Session, args, pr: dict) -> int:
    fs = session.fs
    candidates = [f for f in fs.open if f.severity in BLOCKING and not f.fields.get("forge")]
    if not candidates:
        print("post: nothing to post")
        return 0
    # A finding the forge already carries (an id that was not read back, a post interrupted before
    # the file was saved) adopts that thread's id and is never published a second time.
    adopted = len(adopt(session, pr, candidates))
    candidates = [f for f in candidates if not f.fields.get("forge")]
    if adopted and not args.dry_run:
        session.save()
    if not candidates:
        print("post: nothing to post; %d already on the forge" % adopted)
        return 0
    if pr["head"] and pr["head"] != session.head:
        raise CliError("local HEAD %s is not the pull request's head %s; push or pull first"
                       % (session.head[:7], pr["head"][:7]))
    merge_base = git(session.root, "merge-base", pr["base"] or session.base(), "HEAD").strip()
    hunks = parse_hunks(git(session.root, "diff", "%s...HEAD" % merge_base))
    anchored, unanchored = [], []
    for finding in candidates:
        line = int(finding.line) if finding.line.isdigit() else 0
        if line and line in hunks.get(finding.path, set()):
            anchored.append(finding)
        elif "unanchored" not in finding.flags:
            unanchored.append(finding)
    body = ""
    if unanchored:
        body = "### Not anchored to the diff\n\n" + "\n".join(
            "- %s — %s" % (f.anchor, comment_body(f).split("\n")[0]) for f in unanchored)
    comments = [{"path": f.path, "line": int(f.line), "body": comment_body(f)} for f in anchored]
    if args.dry_run:
        print(json.dumps({"commit_id": session.head, "event": "COMMENT", "body": body, "comments": comments}, indent=2))
        return 0
    if not comments and not body:
        print("post: nothing new to post")
        return 0
    ids = session.forge.post(pr["number"], session.head, body, comments)
    for finding, thread_id in zip(anchored, ids):
        if thread_id:
            finding.fields["forge"] = thread_id
        if "unanchored" in finding.flags:
            finding.flags.remove("unanchored")
    for finding in unanchored:
        finding.flags.append("unanchored")
    missing = [f for f in anchored if not f.fields.get("forge")]
    if missing:
        session.save()  # what the post returned is kept even if reading the ids back fails
        try:
            missing = [f for f in missing if f not in adopt(session, pr, missing)]
        except CliError as exc:
            print("sdd-pr: ids not read back: %s" % str(exc).splitlines()[0], file=sys.stderr)
    session.save()
    print("post: %d thread%s on PR %d, %d not anchored%s"
          % (len(anchored), "" if len(anchored) == 1 else "s", pr["number"], len(unanchored),
             "; %d without an id read back" % len(missing) if missing else ""))
    return 0


def adopt(session: Session, pr: dict, findings: List[Finding]) -> List[Finding]:
    """Give each finding the forge already carries its thread's id, matched on the path, the line
    and the first sentence; return the findings that took one."""
    existing = {(t["path"], str(t["line"]), first_sentence(t["body"])): t["id"]
                for t in session.forge.threads(pr["number"]) if t["id"]}
    taken = []
    for finding in findings:
        thread_id = existing.get((finding.path, finding.line, first_sentence(comment_body(finding))))
        if thread_id:
            finding.fields["forge"] = thread_id
            finding.flags = [flag for flag in finding.flags if flag != "unanchored"]
            taken.append(finding)
    return taken


def cmd_resolve(session: Session, args) -> int:
    session.need_forge()
    pr = session.pr()
    done = 0
    for finding in session.fs.resolved:
        thread_id = finding.fields.get("forge")
        if not thread_id or "mirrored" in finding.flags:
            continue
        session.forge.resolve(pr["number"], thread_id, reply_for(finding), finding.status)
        finding.flags.append("mirrored")
        done += 1
        session.save()
    refresh_state(session, pr)
    print("resolve: %d thread%s answered and closed on PR %d" % (done, "" if done == 1 else "s", pr["number"]))
    return 0


COMMANDS = {"status": cmd_status, "scope": cmd_scope, "pull": cmd_pull, "post": cmd_post, "resolve": cmd_resolve}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError("usage: %s" % message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="sdd-pr", description="The branch's findings file and its pull-request mirror.")
    parser.add_argument("--version", action="version", version="sdd-pr %s" % __version__)
    parser.add_argument("--root", default=".", help="the repository root (default: .)")
    parser.add_argument("--branch", default=None, help="the branch (default: the checked-out one)")
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    for name in COMMANDS:
        cmd = sub.add_parser(name)
        cmd.add_argument("--pr", type=int, default=None, help="the pull request (default: the branch's open one)")
        if name == "scope":
            cmd.add_argument("--json", action="store_true")
            cmd.add_argument("--all", action="store_true", help="the whole branch, not the range since the last pass")
        if name == "post":
            cmd.add_argument("--dry-run", action="store_true")
        if name == "status":
            cmd.add_argument("--write-body", action="store_true", help="rewrite the review state in the PR body")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if not args.command:
            raise CliError("usage: sdd-pr [--root DIR] {%s} ..." % ",".join(COMMANDS))
        return COMMANDS[args.command](Session(args), args)
    except SystemExit as exc:  # --version and --help
        return int(exc.code or 0)
    except (CliError, FileError) as exc:
        print("sdd-pr: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

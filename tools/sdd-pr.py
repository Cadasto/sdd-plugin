#!/usr/bin/env python3
"""sdd-pr — the branch's findings file, mirrored to the pull request's inline threads and suggestion comments.

Commands: status, scope, pull, post, resolve, harvest, guard, and add, flip, record, rename, which own every
write to the file. One file, Python 3.9+, standard library only.
Every external call (git, gh, az) goes through run_cli(), and a test command through run_test(); the tests
replace both.
Contract: references/review.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fnmatch
import hashlib
import html
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote

try:
    import fcntl
except ImportError:  # Windows: no advisory lock; writers there take turns by hand
    fcntl = None

__version__ = "0.17.0"

SEVERITIES = ("critical", "important", "suggestion")
BLOCKING = ("critical", "important")
SEP = " · "
FIELD_KEYS = ("evidence", "fix", "by", "forge", "comment", "declined", "deferred")
FLAGS = ("unanchored", "mirrored", "outside")
SECTIONS = ("Open", "Resolved", "Suggestions")
DESCRIPTOR = os.path.join("docs", ".sdd.yaml")
BACKLOG = "docs/backlog.md"
BACKLOG_HEAD = (
    "---\nkind: plan\n---\n# Backlog\n\n"
    "Leftovers of merged branches: defects outside their change, suggestions, and findings the maintainer "
    "deferred here. Each line is a lead, not a finding: verify it before acting. Themes group what one "
    "delivery takes, defects first; `sdd-pr harvest` and `sdd-pr flip --carry` add lines under Unsorted, and "
    "`/sdd-triage --backlog` sorts them, merges duplicates and drops what is settled. Line numbers are as of "
    "the pull request in `from:`. Edit freely.\n"
)
UNSORTED = "## Unsorted"
#: The order of what does not block: defects first (by severity), then code, tests, other, documents.
KIND_ORDER = ("code", "tests", "other", "documents")
WATERMARK = "harvested_through"
DROPPED = "dropped by the maintainer"
#: A suggestion a blocking line on its anchor took over: it stays, resolved, its words kept.
MERGED = "merged into the blocking line on its anchor"
DEFAULT_TEST_GLOBS = ("*_test.go", "test_*.py", "*_test.py", "*Test.php", "*.test.ts", "*.spec.ts", "*_test.rs")
CODE_SUFFIXES = (
    ".go", ".py", ".php", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".java", ".kt", ".kts",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".swift", ".scala", ".sh", ".bash", ".sql",
    ".ex", ".exs", ".erl", ".hs", ".ml", ".lua", ".dart", ".vue", ".svelte",
)
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".adoc", ".txt")


class CliError(RuntimeError):
    """An external command failed or is missing, or the command line cannot run. A failed command keeps its
    exit status and standard output, for the one caller that reads an exit 1 as an answer."""

    def __init__(self, message: str = "", code: Optional[int] = None, stdout: str = "") -> None:
        super().__init__(message)
        self.code, self.stdout = code, stdout


class FileError(RuntimeError):
    """The findings file does not follow the grammar of references/review.md."""


class CheckoutError(CliError):
    """The pull request or --branch named is not what this checkout has."""


def run_cli(argv: List[str], stdin: Optional[str] = None) -> str:
    """Run one external command and return its standard output. The one door to the outside."""
    try:
        proc = subprocess.run(argv, input=stdin, capture_output=True, text=True)
    except OSError as exc:
        raise CliError("%s: %s" % (argv[0], exc.strerror or exc))
    if proc.returncode != 0:
        raise CliError((proc.stderr or proc.stdout).strip() or "%s failed" % argv[0], proc.returncode, proc.stdout)
    return proc.stdout


def run_test(argv: List[str], cwd: str, timeout: Optional[int] = None) -> Tuple[Optional[int], str]:
    """Run a repository's test command in ``cwd``: its exit status and output, a failure included; a run
    that outlasts ``timeout`` seconds is killed and has no status. The second door to the outside. No
    Python bytecode is cached: a mutant and its restored source can share a size and an mtime second, and a
    stale cache would then run the mutant again."""
    try:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        parts = [x.decode("utf-8", "replace") if isinstance(x, bytes) else x for x in (exc.stdout, exc.stderr)]
        return None, "".join(x for x in parts if x)
    except OSError as exc:
        raise CliError("%s: %s" % (argv[0], exc.strerror or exc))
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ---------------------------------------------------------------- file model
def slug(branch: str) -> str:
    return branch.strip().replace("/", "--")


def store_dir(root: str) -> str:
    """Where every branch's findings file lives: the clone's shared git directory, which every worktree
    of the clone resolves to, which git never commits, and which outlives a removed worktree."""
    common = git(root, "rev-parse", "--git-common-dir").strip()
    return os.path.normpath(os.path.join(common if os.path.isabs(common) else os.path.join(root, common), "sdd", "findings"))


def legacy_path(root: str, branch: str) -> str:
    """Where 0.8.0 kept the file: inside one checkout."""
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
        for key in ("evidence", "fix", "by", "forge", "comment"):
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
    if status == "open" and parts and parts[0] == "suggestion":
        status, parts = "suggestion", parts[1:]  # an open suggestion is a suggestion: it never blocks
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
    def blocking(self) -> List[Finding]:
        """The open lines that block the merge: those about the change itself."""
        return [f for f in self.open if "outside" not in f.flags]

    @property
    def outside(self) -> List[Finding]:
        """The open critical and important lines about code the change did not touch: they keep their
        severity, block nothing, and are carried after merge unless fixed here (review.md § Scope)."""
        return [f for f in self.open if "outside" in f.flags]

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


def load_findings(path: str, branch: str, base: str) -> Findings:
    if not os.path.exists(path):
        return Findings(branch, base)
    with open(path, encoding="utf-8") as handle:
        fs = parse(handle.read())
    fs.branch = fs.branch or branch
    fs.base = fs.base or base
    return fs


def save_findings(path: str, fs: Findings) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(render(fs))
    os.replace(tmp, path)


def key_of(finding: Finding) -> str:
    """A short key for one line, computed from what the line says, so it does not move when another line
    flips; status prints it and flip takes it. It is never written into the file or a commit."""
    text = "\x1f".join((finding.severity, finding.anchor, finding.text))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:5]


def severity_of(body: str) -> str:
    match = re.match(r"\s*\*\*(critical|important)\*\*", body or "")
    return match.group(1) if match else "important"


def first_sentence(body: str) -> str:
    """The thread's first line, with a leading **severity** marker and separator dropped."""
    text = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    text = re.sub(r"^\s*\*\*(critical|important|suggestion)\*\*\s*[—:\-–]?\s*", "", text)
    return md_unescape(text).replace(SEP.strip(), "-").strip() or "(no text)"


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


CODE_SPAN = re.compile(r"(`[^`\n]+`)")


def md_escape(text: str) -> str:
    """Text a forge renders as Markdown, shown as written: outside code spans `<`, `>` and `&` are entities
    and `@` mentions nobody; md_unescape reverses it."""
    return "".join(part if CODE_SPAN.fullmatch(part) else
                   part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("@", "&#64;")
                   for part in CODE_SPAN.split(text))


def md_unescape(text: str) -> str:
    return "".join(part if CODE_SPAN.fullmatch(part) else html.unescape(part) for part in CODE_SPAN.split(text))


def comment_body(finding: Finding) -> str:
    body = "**%s** — %s" % (finding.severity, md_escape(finding.text))
    for key in ("evidence", "fix", "by"):
        if finding.fields.get(key):
            body += "\n\n%s: %s" % (key.capitalize(), md_escape(finding.fields[key]))
    return body


def outside_lines(body: str) -> List[Finding]:
    """A review body's lines that report a defect outside the change in the file's grammar, ending
    `· outside`: the review request puts them there, as no inline comment can sit outside the diff."""
    out = []
    for raw in (body or "").splitlines():
        text = re.sub(r"^\s*(?:[-*]\s+)?(?:\[ \]\s+)?", "", raw).replace("**", "").strip()
        if not text.endswith(SEP.strip() + " outside"):
            continue
        try:
            finding = parse_line("- [ ] " + text, 0)
        except FileError:
            continue
        if finding.severity in BLOCKING:
            out.append(finding)
    return out


def author_of(body: str) -> str:
    """The reviewer a thread was posted for: its `By:` line, since every thread is posted under one account."""
    match = re.search(r"^By: (.+)$", body or "", re.M)
    return match.group(1).strip() if match else ""


def reply_for(finding: Finding) -> str:
    if finding.status == "fixed":
        return "fixed in %s" % (finding.fixed or "this branch")
    return "%s: %s" % (finding.status, finding.fields.get(finding.status, ""))


def open_verdict(fs: Findings) -> str:
    opened = {s: len([f for f in fs.blocking if f.severity == s]) for s in BLOCKING}
    if any(opened.values()):
        return "%d critical and %d important open" % (opened["critical"], opened["important"])
    return "no critical or important finding open"


PASS_MARK = "<!-- sdd:pass %s %s -->"
PASS_RE = re.compile(r"<!-- sdd:pass (\S+) (.+?) -->")


def reviewer_names(reviewers: str) -> str:
    """A Reviewed line's reviewers with repeats counted: `go-reviewer ×3, sdd-doc-reviewer (4 of 4)`."""
    match = re.match(r"^(.*?)\s*(\(\d+ of \d+\))?$", reviewers.strip())
    names, tally = match.group(1), match.group(2) or ""
    counted: Dict[str, int] = {}
    for name in (n.strip() for n in names.split(",")):
        if name:
            counted[name] = counted.get(name, 0) + 1
    shown = ", ".join(name if n == 1 else "%s ×%d" % (name, n) for name, n in counted.items())
    return ("%s %s" % (shown, tally)).strip()


def pass_header(fs: Findings, head: str, passes: List[Tuple[str, str, str, str]], new: int) -> str:
    """The top of a pass's one comment: who reviewed, then each count named for what it counts, and a marker
    per pass so it is posted once."""
    rows = ["**Review at `%s`** by `%s`: %s" % (head[:7], agent, reviewer_names(reviewers))
            for _, _, agent, reviewers in passes]
    left = len(fs.suggestions) + len(fs.outside)
    rows.append("**Blocking:** %s. **Not blocking:** %s; %d open on the branch, carried to `%s` after merge."
                % (open_verdict(fs), "%d new in this pass, below" % new if new else "nothing new", left, BACKLOG))
    return "\n".join(rows + [PASS_MARK % (sha, agent) for sha, _, agent, _ in passes])


def unsummarised(session: Session, pr: dict) -> List[Tuple[str, str, str, str]]:
    """The passes at HEAD the pull request does not carry yet, in a comment or, before 0.13, a review. The
    maintainer's own review is already on it."""
    passes = [p for p in session.fs.passes if session.head.startswith(p[0]) and p[2] != "maintainer"]
    if not passes:
        return []
    bodies = session.forge.review_bodies(pr["number"]) + [c["body"] for c in session.forge.comments(pr["number"])]
    posted = {m.groups() for body in bodies for m in PASS_RE.finditer(body)}
    return [p for p in passes if (p[0], p[2]) not in posted]


SUGGESTIONS_MARK = "<!-- sdd:suggestions %s -->"
SUGGESTIONS_RE = re.compile(r"<!-- sdd:suggestions (\S+) -->")
ANCHOR_SHOWN = re.compile(r"^(- (?:\[.\] )?(?:(?:critical|important|suggestion) · )?)`([^`]+)`")


def shown_row(finding: Finding) -> str:
    """A line as the forge shows it: the file's grammar, its anchor as code, the rest escaped."""
    row = finding.render()
    at = row.find(finding.anchor) if finding.anchor else -1
    if at < 0:
        return md_escape(row)
    return md_escape(row[:at]) + "`%s`" % finding.anchor + md_escape(row[at + len(finding.anchor):])


def lines_block(lines: List[Finding], globs: List[str]) -> List[str]:
    """The lines that do not block, defects first, then code, tests, other, documents, in one fold."""
    lines = sorted(lines, key=lambda f: priority(f, globs))
    rows = []
    for finding in lines:
        shown = Finding(finding.status, finding.severity, finding.path, finding.line, finding.text,
                        {k: v for k, v in finding.fields.items() if k not in ("comment", "forge")},
                        [flag for flag in finding.flags if flag == "outside"], finding.fixed)
        rows.append(shown_row(shown))
    left = len([f for f in lines if f.status in ("suggestion", "open")])
    defects = len([f for f in lines if f.severity in BLOCKING])
    kinds = ([("%d outside the change" % defects)] if defects else []) + \
        (["%d suggestion%s" % (len(lines) - defects, "" if len(lines) - defects == 1 else "s")] if len(lines) > defects else [])
    return ["<details><summary>%s; %d open</summary>" % (", ".join(kinds), left), ""] + rows + ["", "</details>"]


def suggestions_body(sha: str, lines: List[Finding], globs: Optional[List[str]] = None, header: str = "",
                     fs: Optional[Findings] = None) -> str:
    """One comment: a pass's header, or the not-blocking header of lines posted between passes, then the
    lines in the file's grammar (anchor as code, text escaped), so `harvest` reads them back; a fixed,
    carried or dropped line keeps its checkbox."""
    globs = list(globs or DEFAULT_TEST_GLOBS)
    if not header:
        left = len(fs.suggestions) + len(fs.outside) if fs is not None else 0
        header = ("**Not blocking, at `%s`:** %d line%s below; %d open on the branch, carried to `%s` after merge."
                  % (sha[:7], len(lines), "" if len(lines) == 1 else "s", left, BACKLOG))
    if not lines:
        return header
    return "\n".join([header, ""] + lines_block(lines, globs) + [SUGGESTIONS_MARK % sha[:7]])


def suggestion_lines(body: str) -> List[Finding]:
    """The lines of one comment that carries lines that do not block; any other comment holds none."""
    if not SUGGESTIONS_RE.search(body or ""):
        return []
    out = []
    for raw in (body or "").splitlines():
        raw = raw.strip()
        if raw.startswith("- "):
            try:
                out.append(parse_line(md_unescape(ANCHOR_SHOWN.sub(r"\1\2", raw, count=1)), 0))
            except FileError:
                continue  # a hand edit on the forge that no longer reads is not a lead
    return out


def _same_text(a: str, b: str) -> bool:
    return a.replace("\r\n", "\n").strip() == b.replace("\r\n", "\n").strip()


def sync_suggestions(session: "Session", pr: dict, dry_run: bool = False,
                     passes: Optional[List[Tuple[str, str, str, str]]] = None) -> Tuple[int, int]:
    """Keep the pull request's comments in step with the file. A pass gets one comment: its header (who
    reviewed, the counts) and the lines that do not block and are not posted yet, whose id each line takes.
    Lines posted between passes get a comment of their own. A posted comment whose lines changed is edited,
    its pass header kept. A comment deleted on the forge frees its open lines to be posted again. Returns
    (lines posted, comments edited)."""
    fs = session.fs
    mine = [f for f in fs.items if f.severity == "suggestion" or "outside" in f.flags]
    held: Dict[str, List[Finding]] = {}
    for finding in mine:
        if finding.fields.get("comment"):
            held.setdefault(finding.fields["comment"], []).append(finding)
    edited = 0
    if held:
        current = {c["id"]: c["body"] for c in session.forge.comments(pr["number"])}
        for comment_id, lines in held.items():
            if comment_id not in current:
                for finding in lines:
                    finding.fields.pop("comment", None)
                continue
            match = SUGGESTIONS_RE.search(current[comment_id])
            cut = current[comment_id].find("<details>")
            header = current[comment_id][:cut].rstrip() if cut > 0 and PASS_RE.search(current[comment_id][:cut]) else ""
            body = suggestions_body(match.group(1) if match else session.head, lines, session.globs, header, fs)
            if not _same_text(body, current[comment_id]):
                if dry_run:
                    print(body)
                else:
                    session.forge.edit_comment(pr["number"], comment_id, body)
                edited += 1
    fresh = [f for f in mine if f.status in ("suggestion", "open") and not f.fields.get("comment")]
    if fresh or passes:
        header = pass_header(fs, session.head, passes, len(fresh)) if passes else ""
        body = suggestions_body(session.head, fresh, session.globs, header, fs)
        if dry_run:
            print(body)
            return len(fresh), edited
        comment_id = session.forge.comment(pr["number"], body)
        for finding in fresh:
            finding.fields["comment"] = comment_id
    if (fresh or held) and not dry_run:
        session.save()
    return len(fresh), edited


def sync_report(posted: int, edited: int, number: int, passes: int = 0) -> str:
    parts = []
    if passes:
        parts.append("the summary of %d pass%s and %d line%s not blocking in one comment"
                     % (passes, "" if passes == 1 else "es", posted, "" if posted == 1 else "s"))
    elif posted:
        parts.append("%d line%s in a new comment" % (posted, "" if posted == 1 else "s"))
    if edited:
        parts.append("%d comment%s edited" % (edited, "" if edited == 1 else "s"))
    return "%s on PR %d" % ("; ".join(parts), number) if parts else ""


# ---------------------------------------------------------------- git and the descriptor
def git(root: str, *args: str) -> str:
    # Paths come back as they are, never quoted, so a name with an accent matches the file.
    return run_cli(["git", "-C", root, "-c", "core.quotePath=false"] + list(args))


def read_descriptor(root: str) -> str:
    try:
        with open(os.path.join(root, DESCRIPTOR), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def descriptor_value(text: str, key: str) -> str:
    match = re.search(r"^\s*%s:\s*([^#\n]*)" % re.escape(key), text, re.M)
    return match.group(1).strip().strip("'\"") if match else ""


_GATE = None


def gate():
    """The plugin's own sdd-check, beside this file: its YAML reader parses the descriptor, so the two
    tools never disagree on what it says."""
    global _GATE
    if _GATE is None:
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdd-check.py")
        spec = importlib.util.spec_from_file_location("sdd_check_for_sdd_pr", here)
        _GATE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_GATE)
    return _GATE


def descriptor_data(text: str) -> dict:
    """The descriptor as a mapping (the `sdd:` wrapper removed); {} when it is absent or does not parse."""
    try:
        data = gate().load_yaml(text, source=DESCRIPTOR) if text.strip() else {}
    except gate().YamlError:  # a malformed descriptor is the gate's finding; here it reads as no settings
        return {}
    if isinstance(data, dict) and isinstance(data.get("sdd"), dict):
        data = data["sdd"]
    return data if isinstance(data, dict) else {}


def _setting(data: dict, *keys):
    for key in keys:
        data = data.get(key) if isinstance(data, dict) else None
    return data


def configured_reviewers(data: dict) -> List[str]:
    value = _setting(data, "agents", "reviewers")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        out: List[str] = []
        for names in value.values():
            for name in names if isinstance(names, list) else [names]:
                if str(name) not in out:
                    out.append(str(name))
        return out
    return []


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]))


def reviewers_for(data: dict, files: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], List[str]]:
    """Which of the changed code, test and other paths each of `agents.reviewers` reads, and the paths
    none does. A list gives every reviewer every path; a map gives each pattern's reviewers its paths."""
    reviewable = files["code"] + files["tests"] + files["other"]
    value = _setting(data, "agents", "reviewers")
    if isinstance(value, str):
        value = [value]
    if isinstance(value, list):
        names = [str(name) for name in value if str(name).strip()]
        if not names:
            return {}, list(reviewable)
        return {name: list(reviewable) for name in names} if reviewable else {}, []
    out: Dict[str, List[str]] = {}
    unassigned = []
    for path in reviewable:
        hit = False
        for pattern, names in (value or {}).items() if isinstance(value, dict) else ():
            if _matches(path, str(pattern)):
                hit = True
                for name in names if isinstance(names, list) else [names]:
                    out.setdefault(str(name), []).append(path)
        if not hit:
            unassigned.append(path)
    return out, unassigned


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


def elsewhere(root: str, branch: str, command: str = "") -> str:
    """How to reach ``branch``: the command again from its worktree (--root goes before the command), or a
    checkout of it."""
    path = worktree_of(root, branch)
    return ("run it there: sdd-pr --root %s %s …" % (path, command or "<command>") if path
            else "check out %s, or run sdd-pr --root <its worktree> %s …" % (branch, command or "<command>"))


def resolve_sha(root: str, sha: str) -> str:
    try:
        return git(root, "rev-parse", "--verify", "--quiet", sha + "^{commit}").strip()
    except CliError:
        return ""


def base_ref(root: str, base: str) -> str:
    """The base as a ref this clone has: the local branch, else its remote-tracking copy, and the remote
    one when the local branch is only behind it, so a stale base does not re-review merged work."""
    local, remote = resolve_sha(root, base), resolve_sha(root, "origin/" + base)
    if not remote:
        return base
    if not local:
        return "origin/" + base
    if local != remote:
        try:
            git(root, "merge-base", "--is-ancestor", local, remote)
        except CliError:
            # Ahead or diverged: the local branch holds commits the remote lacks, so it stays the base.
            try:
                git(root, "merge-base", "--is-ancestor", remote, local)
            except CliError:
                print("sdd-pr: local %s and origin/%s have diverged; the range starts from local %s, which "
                      "may re-read work origin/%s already has" % (base, base, base, base), file=sys.stderr)
            return base
        print("sdd-pr: local %s is behind origin/%s; the range starts from origin/%s" % (base, base, base),
              file=sys.stderr)
        return "origin/" + base
    return base


def review_range(root: str, fs: Findings, base: str, head: str, since_last: bool = False,
                 agent: str = "") -> Optional[str]:
    """The range a pass reads, or ``None`` when nothing is in it (review.md § Scope): the whole branch,
    so a second reviewer gives a second opinion on all of it; with ``since_last``, only the commits
    since the last pass, or since ``agent``'s own when it has one. A last pass that is no longer an
    ancestor of HEAD (the branch was rebased) restarts at the merge base."""
    agent = _clean(agent).replace(":", "-") if agent else ""  # spelled as record writes it
    passes = [r for r in fs.passes if r[2] == agent] or list(fs.passes)
    last = passes[-1][0] if since_last and passes else None
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


def diff_start(root: str, base: str, rng: Optional[str]) -> Tuple[str, str]:
    """Where the range's diff starts, and a note when the base's changes are in it. When the base was merged
    into the branch after the range's start, a tree of that start with the new base merged in, so the diff
    holds the branch's own changes and its conflict resolutions, not the base's; the range's start
    otherwise. A conflicted merge still writes its tree (exit 1); git before 2.38 cannot write one."""
    if not rng:
        return "", ""
    start = rng.split("..")[0]
    ref = base_ref(root, base)
    try:
        then = git(root, "merge-base", ref, start).strip()
        now = git(root, "merge-base", ref, "HEAD").strip()
    except CliError:
        return start, ""
    if not then or then == now:
        return start, ""
    try:
        out = git(root, "merge-tree", "--write-tree", start, now)
    except CliError as exc:
        out = exc.stdout if exc.code == 1 else ""
    tree = (out.splitlines() or [""])[0].strip()
    if tree:
        return tree, ""
    return start, ("diff from: %s; %s was merged in after it and git could not write the merged tree (git before "
                   "2.38): the base's changes are in the range" % (start[:12], base))


KINDS = ("code", "tests", "documents", "other", "vendored", "plans", "skipped")
RFC2119 = re.compile(r"\b(MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED|OPTIONAL)\b")


def _few(paths: List[str], limit: int = 10) -> str:
    """Paths no reviewer reads, named only so far: a skipped corpus can run to thousands."""
    more = len(paths) - limit
    return " ".join(paths[:limit]) + (" and %d more" % more if more > 0 else "")


#: An absolute requirement (RFC 2119 §1, §2): a sentence a test must pin, so a guard run proves it.
ABSOLUTE = re.compile(r"\b(MUST|SHALL|REQUIRED)\b")


def binding_homes(data: dict) -> List[str]:
    """Where binding sentences live: the specifications folder, or the constitution on the informative
    profile (methodology §1a)."""
    if profile_of(data) == "informative":
        return [str(_setting(data, "paths", "constitution") or gate().DEFAULT_CONSTITUTION)]
    return [str(_setting(data, "paths", "specifications") or gate().DEFAULT_PATHS["specifications"]).rstrip("/")]


def _sentence_shape(text: str) -> Tuple[Tuple[str, ...], bool, set]:
    """What a reword keeps of an absolute sentence: the words before its keyword (the subject), whether the
    keyword is negated, and the words after it (the predicate)."""
    match = ABSOLUTE.search(text)
    subject = tuple(re.findall(r"[a-z0-9]+", text[:match.start()].lower()))
    rest = text[match.end():]
    negated = bool(re.match(r"\s+NOT\b", rest))
    predicate = {w for w in re.findall(r"[a-z0-9]+", rest.lower()) if w != "not"}
    return subject, negated, predicate


def _new_obligations(path: str, removed: List[str], added: List[Tuple[int, str]]) -> List[str]:
    """The added absolute lines of one hunk that no removed line of it accounts for. An added sentence pairs,
    once, with a removed one of the same subject and polarity that shares a predicate word: a reword, no
    new obligation. Anything looser would pair a new sentence with an unrelated removed one and cost it
    its guard run; anything stricter only costs an extra run."""
    shapes = [_sentence_shape(line) for line in removed]
    new = []
    for number, line in added:
        subject, negated, predicate = _sentence_shape(line)
        for i, other in enumerate(shapes):
            if other and other[0] == subject and other[1] == negated and other[2] & predicate:
                shapes[i] = None
                break
        else:
            new.append("%s:%d" % (path, number))
    return new


def binding_lines(root: str, start: str, documents: List[str], homes: List[str]) -> List[str]:
    """`path:line` of each line the range added to a reviewed document in ``homes`` that states a new absolute
    requirement, each owed a test that fails without its guard. A reworded sentence is no new obligation
    (methodology §6): inside one hunk, an added MUST line pairs with the removed line it replaced, by
    content (`_new_obligations`), never by count, so a new sentence above a reword, or one that replaces an
    unrelated sentence, is listed. The homes are diffed whole, so a file renamed inside them is paired with
    its old self, not read as new."""
    wanted = {d for d in documents if any(d == h or d.startswith(h + "/") for h in homes)}
    if not start or not wanted:
        return []
    found, path, number, header = [], "", 0, False
    removed, added = [], []  # the current hunk's absolute lines, settled when the hunk ends
    for line in git(root, "diff", "--no-ext-diff", "-U0", "-M", start, "HEAD", "--", *homes).splitlines():
        if line.startswith("diff --git ") or HUNK.match(line):
            found += _new_obligations(path, removed, added)
            removed, added = [], []
        if line.startswith("diff --git "):
            header, path = True, ""
        elif header and line.startswith("+++ "):
            target = line[4:].strip()
            path = target[2:] if target.startswith("b/") else target
            path = path if path in wanted else ""
        elif HUNK.match(line):
            header, number = False, int(HUNK.match(line).group(1))
        elif not header and path and line.startswith("-") and not line.startswith("---"):
            if ABSOLUTE.search(line):
                removed.append(line[1:])
        elif not header and line.startswith("+") and path:
            if ABSOLUTE.search(line):
                added.append((number, line[1:]))
            number += 1
    found += _new_obligations(path, removed, added)
    return found


def normative_lines(root: str, start: str, documents: List[str]) -> int:
    """How many added or removed lines of the range's documents hold an RFC-2119 keyword: a hint for the
    lane, which stays a judgement (methodology §12)."""
    if not start or not documents:
        return 0
    text = git(root, "diff", "--no-ext-diff", "-U0", start, "HEAD", "--", *documents)
    return sum(1 for line in text.splitlines()
               if line[:1] in "+-" and not line.startswith(("+++", "---")) and RFC2119.search(line))


#: The plugin's own reviewers, which no `agents.reviewers` entry names, and the kinds each one reads.
OWN_REVIEWERS = {"sdd-spec-conformance-reviewer": ("code", "tests"), "sdd-doc-reviewer": ("documents",)}


def _is_plan(root: str, path: str, start: str = "") -> bool:
    """A document marked `kind: plan`: a temporary working file nobody reviews. A plan the range deleted is
    read as it was at the range's start."""
    try:
        if os.path.exists(os.path.join(root, path)) or not start:
            with open(os.path.join(root, path), encoding="utf-8") as handle:
                text = handle.read()
        else:
            text = git(root, "show", "%s:./%s" % (start, path))
        front, _ = gate().frontmatter(text)
    except (OSError, UnicodeDecodeError, CliError, gate().YamlError):
        return False
    return isinstance(front, dict) and str(front.get("kind", "")).strip() == "plan"


def changed_files(root: str, rng: Optional[str], globs: List[str], vendored: str = "",
                  start: str = "", skip: Sequence[str] = ()) -> Dict[str, List[str]]:
    """The range's paths by kind, diffed from ``start`` (diff_start) when given. The vendored gate is
    upstream code, a plan a working file, and a path `agents.skip` names one the repository keeps out of
    review: all three are kept apart, so no reviewer reads them."""
    files: Dict[str, List[str]] = {kind: [] for kind in KINDS}
    if not rng:
        return files
    vendored = os.path.normpath(vendored) if vendored else ""
    for path in git(root, "diff", "--name-only", start or rng.split("..")[0], "HEAD").splitlines():
        path = path.strip()
        if not path:
            continue
        vendored_here = os.path.normpath(path) == vendored and not _patched(root, path)
        kind = ("vendored" if vendored_here else "skipped" if any(_matches(path, g) for g in skip)
                else kind_of(path, globs))
        if kind == "documents" and _is_plan(root, path, rng.split("..")[0]):
            kind = "plans"
        files[kind].append(path)
    return files


def _patched(root: str, path: str) -> bool:
    """A vendored gate at the plugin's own version that differs from the plugin's copy was changed here,
    so it is code to review; one at another version is simply a different release."""
    own = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdd-check.py")
    try:
        with open(os.path.join(root, path), "rb") as handle:
            theirs = handle.read()
        with open(own, "rb") as handle:
            ours = handle.read()
    except OSError:
        return False
    mine, vendored = (re.search(rb'^__version__ = "([^"]+)"', text, re.M) for text in (ours, theirs))
    return bool(mine and vendored and mine.group(1) == vendored.group(1) and ours != theirs)


def version_lt(a: str, b: str) -> bool:
    """Whether dotted version ``a`` is below ``b``, number by number (0.8.10 is above 0.8.9)."""
    def numbers(v):
        return [int(p) if p.isdigit() else 0 for p in re.split(r"[.\-+]", v.strip())]
    x, y = numbers(a), numbers(b)
    width = max(len(x), len(y))
    return x + [0] * (width - len(x)) < y + [0] * (width - len(y))


def worker_branches(root: str, branch: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """The delivery's worker branches, `<branch>--<task>`: those not integrated yet, each with what it is
    doing, and those merged. A branch just created from HEAD is an ancestor of HEAD too: it counts as
    merged only once it has its own commits and its worktree holds no uncommitted work."""
    try:
        names = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/%s--*" % branch).split()
    except CliError:
        return [], []
    pending: List[Tuple[str, str]] = []
    merged: List[str] = []
    for name in names:
        try:
            git(root, "merge-base", "--is-ancestor", name, "HEAD")
        except CliError:
            pending.append((name, "not integrated"))
            continue
        tree = worktree_of(root, name)
        try:
            dirty = bool(tree) and bool(git(tree, "status", "--porcelain").strip())
        except CliError:
            dirty = False
        if dirty:
            pending.append((name, "running (uncommitted work in %s)" % tree))
            continue
        try:
            subjects = [s for s in git(root, "reflog", "show", "--format=%gs", "refs/heads/" + name).splitlines() if s.strip()]
        except CliError:
            subjects = []
        if subjects and all(s.startswith("branch: Created") for s in subjects):
            pending.append((name, "running (no commit yet)"))
            continue
        merged.append(name)
    return pending, merged


def cleanup_line(findings: str, notes: str) -> str:
    """What a merged branch leaves behind: its findings file, its delivery notes, the branch and worktree."""
    also = " and the delivery notes %s" % notes if os.path.exists(notes) else ""
    return "%s%s, then the branch and its worktree" % (findings, also)


# ---------------------------------------------------------------- the forge interface
def _json(text: str):
    try:
        return json.loads(text or "null")
    except ValueError as exc:
        raise CliError("unreadable JSON from the forge CLI: %s" % exc)


def _json_pages(text: str) -> list:
    """`gh api --paginate` prints one JSON array per page, back to back."""
    out, decoder, i, text = [], json.JSONDecoder(), 0, (text or "").strip()
    try:
        while i < len(text):
            value, i = decoder.raw_decode(text, i)
            out += value if isinstance(value, list) else [value]
            while i < len(text) and text[i].isspace():
                i += 1
    except ValueError as exc:
        raise CliError("unreadable JSON from the forge CLI: %s" % exc)
    return out


class Forge:
    HEAD_REF = ""
    """What the commands need from a forge. Local git supplies the diff on every forge."""

    name = "none"

    def pr_for_branch(self, branch: str) -> Optional[dict]:  # {"number", "head", "base", "draft", "url"}
        raise CliError("no forge configured")

    def pr(self, number: int) -> dict:
        raise CliError("no forge configured")

    def checks(self, number: int) -> str:  # pass | fail | pending | none | not read
        return "not read"

    def threads(self, number: int) -> List[dict]:  # {"id", "node", "resolved", "path", "line", "body", "author"}
        raise CliError("no forge configured")

    def post(self, number: int, sha: str, body: str, comments: List[dict], quiet: bool = False) -> List[str]:
        """One review: ``body`` above the inline ``comments``; ``quiet`` when the body asks nothing of anyone."""
        raise CliError("no forge configured")

    def review_bodies(self, number: int) -> List[str]:  # every review or pull-request-level comment body
        raise CliError("no forge configured")

    def resolve(self, number: int, thread_id: str, reply: str, state: str) -> None:  # fixed | declined | deferred
        raise CliError("no forge configured")

    def comments(self, number: int) -> List[dict]:  # {"id", "body"}: the pull request's comments not on a line
        raise CliError("no forge configured")

    def comment(self, number: int, body: str) -> str:
        """Post one comment on the pull request, not on a line, that asks nothing of anyone; return its id."""
        raise CliError("no forge configured")

    def edit_comment(self, number: int, comment_id: str, body: str) -> None:
        raise CliError("no forge configured")

    def merged(self, since: datetime.datetime) -> List[dict]:  # the _shape of each merged at or after ``since``
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
    #: The ref that keeps a pull request's head after its branch is deleted on merge.
    HEAD_REF = "pull/%d/head"
    """GitHub through `gh`: reviews, review threads, and resolveReviewThread."""

    name = "github"
    #: What one read of a pull request asks for; the checks come with it, so they need no read of their own.
    PR_FIELDS = "number,headRefOid,headRefName,baseRefName,isDraft,url,statusCheckRollup,state,mergeCommit,mergedAt,body"
    #: A pull request's web address names its owner and repository, which then need no `gh repo view`.
    PR_URL_RE = re.compile(r"^https?://[^/]+/([^/]+)/([^/]+)/pull/\d+/?$")

    def __init__(self):
        self._repo: Optional[Tuple[str, str]] = None
        #: Each pull request read in this run, by number. Every `gh` call is a round trip, and GitHub
        #: throttles a client that sends many, so a value already read is never asked for again.
        self._read: Dict[int, dict] = {}

    def _seen(self, shaped: dict) -> dict:
        """Keep a pull request just read, and its owner and repository when its URL names them."""
        self._read[shaped["number"]] = shaped
        match = self.PR_URL_RE.match(shaped["url"])
        if self._repo is None and match:
            self._repo = (match.group(1), match.group(2))
        return shaped

    def _owner_name(self) -> Tuple[str, str]:
        if self._repo is None:
            data = _json(run_cli(["gh", "repo", "view", "--json", "owner,name"]))
            self._repo = (data["owner"]["login"], data["name"])
        return self._repo

    @staticmethod
    def _shape(data: dict) -> dict:
        return {"number": data["number"], "head": data.get("headRefOid", ""), "branch": data.get("headRefName", ""),
                "base": data.get("baseRefName", ""), "draft": bool(data.get("isDraft")), "url": data.get("url", ""),
                "state": (data.get("state") or "OPEN").lower(), "merge": (data.get("mergeCommit") or {}).get("oid", ""),
                "merged_at": data.get("mergedAt") or "", "body": data.get("body") or "", "raw": data}

    def pr_for_branch(self, branch):
        data = _json(run_cli(["gh", "pr", "list", "--head", branch, "--state", "all", "--json", self.PR_FIELDS])) or []
        # The open one, else the latest: a merged or closed pull request is a state worth saying.
        data = sorted(data, key=lambda d: (d.get("state") or "OPEN").upper() != "OPEN")
        return self._seen(self._shape(data[0])) if data else None

    def pr(self, number):
        return self._seen(self._shape(_json(run_cli(["gh", "pr", "view", str(number), "--json", self.PR_FIELDS]))))

    def checks(self, number):
        # The read that found the pull request carried its checks.
        pr = self._read.get(number) or self.pr(number)
        rollup = pr["raw"].get("statusCheckRollup") or []
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

    def review_bodies(self, number):
        owner, name = self._owner_name()
        reviews = _json_pages(run_cli(["gh", "api", "repos/%s/%s/pulls/%d/reviews?per_page=100" % (owner, name, number),
                                       "--paginate"]))
        return [r.get("body") or "" for r in reviews if isinstance(r, dict)]

    def post(self, number, sha, body, comments, quiet=False):
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

    def resolve(self, number, thread_id, reply, state):
        owner, name = self._owner_name()
        run_cli(["gh", "api", "repos/%s/%s/pulls/%d/comments/%s/replies" % (owner, name, number, thread_id),
                 "--method", "POST", "--input", "-"], stdin=json.dumps({"body": reply}))
        nodes = {t["id"]: t["node"] for t in self.threads(number)}
        node = nodes.get(str(thread_id))
        if not node:
            raise CliError("thread %s is not on pull request %d" % (thread_id, number))
        run_cli(["gh", "api", "graphql", "-f", "query=" + RESOLVE_MUTATION, "-f", "id=" + node])

    def comments(self, number):
        owner, name = self._owner_name()
        listed = _json_pages(run_cli(["gh", "api", "repos/%s/%s/issues/%d/comments?per_page=100" % (owner, name, number),
                                      "--paginate"]))
        return [{"id": str(c.get("id", "")), "body": c.get("body") or ""} for c in listed if isinstance(c, dict)]

    def comment(self, number, body):
        owner, name = self._owner_name()
        created = _json(run_cli(["gh", "api", "repos/%s/%s/issues/%d/comments" % (owner, name, number),
                                 "--method", "POST", "--input", "-"], stdin=json.dumps({"body": body})))
        return str(created.get("id", ""))

    def edit_comment(self, number, comment_id, body):
        owner, name = self._owner_name()
        run_cli(["gh", "api", "repos/%s/%s/issues/comments/%s" % (owner, name, comment_id),
                 "--method", "PATCH", "--input", "-"], stdin=json.dumps({"body": body}))

    def merged(self, since):
        # The search takes a day; the caller compares the exact instant.
        data = _json(run_cli(["gh", "pr", "list", "--state", "merged", "--search", "merged:>=" + since.strftime("%Y-%m-%d"),
                              "--limit", "1000", "--json", "number,headRefOid,headRefName,baseRefName,url,state,mergedAt"]))
        return [self._shape(d) for d in data or []]


class AzureDevOpsForge(Forge):
    """Azure DevOps through `az`: pull-request threads with their native status."""

    name = "azure-devops"

    def __init__(self, org: str = "", project: str = "", repo: str = ""):
        self.org, self.project, self.repo = org, project, repo
        self._ids: Dict[int, Tuple[str, str]] = {}

    def _org(self) -> List[str]:
        return ["--org", self.org] if self.org else []

    def _shape(self, data: dict) -> dict:
        repository = data.get("repository") or {}
        number = int(data["pullRequestId"])
        self._ids[number] = ((repository.get("project") or {}).get("name", self.project), repository.get("id", self.repo))
        state = {"completed": "merged", "abandoned": "closed"}.get(data.get("status") or "active", "open")
        return {"number": number, "head": (data.get("lastMergeSourceCommit") or {}).get("commitId", ""),
                "branch": _short_ref(data.get("sourceRefName", "")), "base": _short_ref(data.get("targetRefName", "")),
                "draft": bool(data.get("isDraft")), "url": data.get("url", ""), "state": state,
                "body": data.get("description") or "",
                "merge": (data.get("lastMergeCommit") or {}).get("commitId", ""),
                "merged_at": (data.get("closedDate") or "") if state == "merged" else "", "raw": data}

    def pr_for_branch(self, branch):
        argv = ["az", "repos", "pr", "list", "--source-branch", "refs/heads/" + branch, "--status", "all",
                "-o", "json"] + self._org()
        if self.project:
            argv += ["--project", self.project]
        if self.repo:
            argv += ["--repository", self.repo]
        data = sorted(_json(run_cli(argv)) or [], key=lambda d: (d.get("status") or "active") != "active")
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

    def review_bodies(self, number):
        threads = (self._invoke(number, "pullRequestThreads", []) or {}).get("value", [])
        return [((t.get("comments") or [{}])[0]).get("content") or "" for t in threads if not t.get("isDeleted")]

    def post(self, number, sha, body, comments, quiet=False):
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
            # A summary alone is a closed thread, so it never counts as an active comment.
            self._invoke(number, "pullRequestThreads", [], "POST", {
                "status": "closed" if quiet else "active",
                "comments": [{"parentCommentId": 0, "commentType": 1, "content": body}]})
        return ids

    def resolve(self, number, thread_id, reply, state):
        route = ["threadId=%s" % thread_id]
        self._invoke(number, "pullRequestThreadComments", route, "POST",
                     {"parentCommentId": 1, "content": reply, "commentType": 1})
        status = {"fixed": "fixed", "declined": "wontFix", "deferred": "closed"}[state]
        self._invoke(number, "pullRequestThreads", route, "PATCH", {"status": status})

    def comments(self, number):
        threads = (self._invoke(number, "pullRequestThreads", []) or {}).get("value", [])
        return [{"id": str(t.get("id", "")), "body": ((t.get("comments") or [{}])[0]).get("content") or ""}
                for t in threads if not t.get("isDeleted") and not (t.get("threadContext") or {}).get("filePath")]

    def comment(self, number, body):
        # A closed thread: it never counts as an active comment a merge policy waits on.
        created = self._invoke(number, "pullRequestThreads", [], "POST", {
            "status": "closed", "comments": [{"parentCommentId": 0, "commentType": 1, "content": body}]})
        return str(created.get("id", ""))

    def edit_comment(self, number, comment_id, body):
        self._invoke(number, "pullRequestThreadComments", ["threadId=%s" % comment_id, "commentId=1"], "PATCH",
                     {"content": body})

    def merged(self, since):
        argv = ["az", "repos", "pr", "list", "--status", "completed", "--top", "1000", "-o", "json"] + self._org()
        if self.project:
            argv += ["--project", self.project]
        if self.repo:
            argv += ["--repository", self.repo]
        return [self._shape(d) for d in _json(run_cli(argv)) or []]



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
#: A detached checkout's stand-in for the branch, which clean resolves itself.
DETACHED = "HEAD"


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
                                       elsewhere(self.root, args.branch, getattr(args, "command", ""))))
        self.branch = args.branch or checked
        if not self.branch and getattr(args, "command", "") == "clean":
            self.branch = DETACHED  # clean names its branch, or reads it from --pr
        if not self.branch:
            raise CliError("detached HEAD; pass --branch")
        self.forge = detect_forge(self.root)
        self.descriptor = read_descriptor(self.root)
        self.data = descriptor_data(self.descriptor)
        self.globs = test_globs(self.descriptor)
        self.vendored = str(_setting(self.data, "check", "script") or "scripts/sdd-check.py")
        skip = _setting(self.data, "agents", "skip")
        self.skip = [str(g) for g in (skip if isinstance(skip, list) else [skip] if skip else [])]
        self.command = getattr(args, "command", "") or ""
        pinned = str(_setting(self.data, "check", "version") or "")
        #: Set when this plugin is older than the one that last upgraded the repository.
        self.stale = ("sdd-pr %s is older than this repository (%s): update the plugin; it would write an "
                      "older format" % (__version__, pinned)) if pinned and version_lt(__version__, pinned) else ""
        self._pr_number = args.pr
        self._pr: Optional[dict] = None
        self.dry_run = getattr(args, "dry_run", False)
        store = store_dir(self.root)
        self.path = os.path.join(store, slug(self.branch) + ".md")
        self.notes = os.path.join(os.path.dirname(store), "deliver", slug(self.branch) + ".md")
        # One command at a time per clone: every worktree, Claude and Cursor share the file, so a command
        # holds the lock from the moment it reads the file until it is done with it.
        self.lock_path = os.path.join(os.path.dirname(os.path.dirname(store)), "sdd-pr.lock")
        self._lock = None
        if fcntl is not None:
            os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
            self._lock = open(self.lock_path, "a")
            fcntl.flock(self._lock, fcntl.LOCK_EX)
        self._adopt_legacy()
        self.fs = load_findings(self.path, self.branch, "")
        # clean names a merged branch, which this checkout need not hold: it reads the pull request itself.
        if self._pr_number is not None and self.forge.name != "none" and getattr(args, "command", "") != "clean":
            try:
                self.pr()  # a checkout under another name that holds the pull request's head works on its file
            except BaseException:
                self.close()  # a refusal here must not keep the clone's lock for the next command
                raise

    def _rekey(self, branch: str, quiet: bool = False) -> None:
        """Work on ``branch``'s findings file and notes: the pull request's, though this checkout's local
        branch has another name (a review worktree), so every reviewer of one pull request shares one file."""
        if not quiet:
            print("sdd-pr: the findings of %s (pull request %s), which this checkout (%s) holds"
                  % (branch, self._pr_number, self.branch), file=sys.stderr)
        self.branch = branch
        store = store_dir(self.root)
        self.path = os.path.join(store, slug(branch) + ".md")
        self.notes = os.path.join(os.path.dirname(store), "deliver", slug(branch) + ".md")
        self.fs = load_findings(self.path, branch, "")

    def pr(self, required: bool = True) -> Optional[dict]:
        if self._pr is None:
            if self._pr_number is not None:
                pr = self.forge.pr(self._pr_number)
                if pr.get("branch") and pr["branch"] != self.branch:
                    if not self.holds(pr["head"]):
                        raise CheckoutError("pull request %d is %s at %s; this checkout is %s at %s; %s"
                                            % (pr["number"], pr["branch"], pr["head"][:7], self.branch,
                                               self.head[:7], elsewhere(self.root, pr["branch"], self.command)))
                    self._rekey(pr["branch"])
                self._pr = pr
            else:
                pr = self.forge.pr_for_branch(self.branch)
                # A merged or closed pull request is this branch's only while its head is still HEAD;
                # after new commits, or a branch name used again, the branch has no pull request.
                self._pr = pr if pr is None or pr["state"] == "open" or pr["head"] == self.head else None
            if self._pr is None and required:
                raise CliError("no open pull request for %s; pass --pr" % self.branch)
            if (self._pr and self._pr["state"] == "open" and self._pr.get("base") and self.fs.base
                    and self._pr["base"] != self.fs.base):
                # A retargeted pull request: the file's base follows it, so the range starts at the right place.
                print("sdd-pr: Base %s -> %s, the base of pull request %d"
                      % (self.fs.base, self._pr["base"], self._pr["number"]), file=sys.stderr)
                self.fs.base = self._pr["base"]
                if self.has_file() and not self.dry_run:
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

    def close(self) -> None:
        if self._lock is not None:
            self._lock.close()
            self._lock = None

    def _adopt_legacy(self) -> None:
        """A file 0.8.0 left in this checkout, or in another worktree of the clone, moves to the store,
        once; a second one is named, never merged."""
        roots = [self.root]
        try:
            roots += [line[len("worktree "):].strip() for line in git(self.root, "worktree", "list", "--porcelain").splitlines()
                      if line.startswith("worktree ")]
        except CliError:
            pass
        seen = set()
        for root in roots:
            legacy = legacy_path(root, self.branch)
            if os.path.realpath(legacy) in seen or not os.path.exists(legacy):
                continue
            seen.add(os.path.realpath(legacy))
            if os.path.exists(self.path):
                print("sdd-pr: an older findings file is still at %s; fold its open lines and suggestions into %s "
                      "with sdd-pr add -, then delete it" % (legacy, self.path), file=sys.stderr)
                continue
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            shutil.move(legacy, self.path)
            print("sdd-pr: moved the findings file from %s to %s" % (legacy, self.path), file=sys.stderr)

    def has_file(self) -> bool:
        return os.path.exists(self.path)

    def need_forge(self) -> None:
        if self.forge.name == "none":
            raise CliError("no forge configured (forge: none, or a remote the tool does not recognise)")

    def guard(self) -> None:
        """Every write to the file or the forge stops here when the plugin is older than the repository."""
        if self.stale:
            raise CliError(self.stale)

    def save(self) -> None:
        self.guard()
        self.fs.base = self.fs.base or self.base()
        self.fs.branch = self.fs.branch or self.branch
        save_findings(self.path, self.fs)


def cmd_scope(session: Session, args) -> int:
    if args.pr is not None and session.forge.name != "none":
        session.pr()
    if args.base:
        # A stacked branch names its parent once; the file keeps it for every later pass.
        if not resolve_sha(session.root, args.base) and not resolve_sha(session.root, "origin/" + args.base):
            raise CliError("scope: --base %s is not a branch or commit here" % args.base)
        session.fs.base = args.base
        session.save()
    if args.agent and not args.since_last:
        raise CliError("scope: --agent names whose last pass --since-last starts from; pass both")
    rng = review_range(session.root, session.fs, session.base(), session.head,
                       since_last=args.since_last, agent=args.agent or "")
    start, widened = diff_start(session.root, session.base(), rng)
    files = changed_files(session.root, rng, session.globs, session.vendored, start, session.skip)
    reviewers, unassigned = reviewers_for(session.data, files)
    notes = [widened] if widened else []
    agent = _clean(args.agent or "").replace(":", "-")
    if agent and session.fs.passes and not [p for p in session.fs.passes if p[2] == agent]:
        notes.append("since: no pass by %s; the last pass, by %s" % (agent, session.fs.passes[-1][2]))
    if rng and start != rng.split("..")[0]:
        notes.append("diff from: %s, the last pass with %s merged in; the base's changes are left out"
                     % (start[:12], session.base()))
    if args.diff:
        paths = files.get(args.diff) if args.diff in KINDS else reviewers.get(args.diff)
        own = OWN_REVIEWERS.get(args.diff.rsplit(":", 1)[-1])
        if paths is None and own:
            paths = [p for kind in own for p in files[kind]]
        if paths is None and args.diff in configured_reviewers(session.data):
            paths = []  # a reviewer with nothing in this range: nothing to print
        if paths is None:
            raise CliError("scope: --diff takes a kind (%s), a reviewer scope names, or %s, not %s"
                           % (", ".join(KINDS), " or ".join(sorted(OWN_REVIEWERS)), args.diff))
        if rng and paths:
            sys.stdout.write(git(session.root, "diff", "--no-ext-diff", start, "HEAD", "--", *paths))
        return 0
    if args.start and rng:
        for other in start_pass(session, args.start):
            notes.append("pass: also running, %s; this one runs beside it" % other)
    normative = normative_lines(session.root, start, files["documents"])
    if args.json:
        print(json.dumps({"range": rng, "diff_from": start or None, "base": session.base(), "head": session.head,
                          "files": files, "reviewers": reviewers, "unassigned": unassigned, "notes": notes,
                          "normative_lines": normative}, indent=2))
        return 0
    print("base: %s" % session.base())
    print("range: %s" % (rng or "empty"))
    for note in notes:
        print(note)
    if rng:
        print("normative lines changed: %d" % normative)
    for kind in KINDS:
        if files[kind]:
            print("%s: %s" % (kind, _few(files[kind]) if kind == "skipped" else " ".join(files[kind])))
    for name, paths in reviewers.items():
        print("reviewer %s: %s" % (name, " ".join(paths)))
    if unassigned:
        print("no reviewer: %s" % " ".join(unassigned))
    return 0


PASS_NOTE_AGE = 3600  # seconds after which a pass that never recorded is taken as abandoned


def pass_note(session: Session) -> str:
    return os.path.join(os.path.dirname(session.path), slug(session.branch) + ".pass")


def _pass_notes(path: str) -> Dict[str, dict]:
    """The passes noted as running on this branch, by agent; an unreadable note is none."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.loads(handle.read())
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict) and "agent" in data:  # 0.12: one pass
        data = {"passes": {str(data["agent"]): data}}
    passes = data.get("passes") if isinstance(data, dict) else None
    return {str(k): v for k, v in passes.items() if isinstance(v, dict)} if isinstance(passes, dict) else {}


def _write_pass_notes(path: str, notes: Dict[str, dict]) -> None:
    if not notes:
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"passes": notes}, sort_keys=True) + "\n")


def start_pass(session: Session, agent: str) -> List[str]:
    """Note that ``agent`` starts a pass on this branch, and return the other passes running (noted under an
    hour ago). Two passes run side by side: a second opinion is the maintainer's to ask for. ``record``
    clears the agent's note."""
    agent, path = _clean(agent).replace(":", "-"), pass_note(session)
    now = datetime.datetime.now(datetime.timezone.utc)
    notes, others = {}, []
    for name, note in _pass_notes(path).items():
        started = instant(str(note.get("when", "")))
        if started and (now - started).total_seconds() < PASS_NOTE_AGE:
            notes[name] = note
            if name != agent:
                others.append("%s since %s on %s" % (name, note.get("when"), str(note.get("head", ""))[:7]))
    session.guard()
    notes[agent] = {"agent": agent, "when": iso(now), "head": session.head}
    _write_pass_notes(path, notes)
    return others


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name.replace(":", "--")).strip("-") or "reviewer"


def profile_of(data: dict) -> str:
    value = str(_setting(data, "profile") or "formal")
    return "informative" if value == "informative" else "formal"


def lane_of(args, pr: Optional[dict], normative: int, profile: str) -> str:
    """The pass's lane: --lane, else the PR body's `Lane:` line, else a hint for methodology §12's test."""
    if profile == "informative":
        return "none (informative profile)"
    if args.lane:
        return "%s (--lane)" % args.lane
    match = re.search(r"(?im)^\W*Lane:\W*(full|maintenance)\b", (pr or {}).get("body") or "")
    if match:
        return "%s (the pull request body)" % match.group(1).lower()
    return "decide (methodology §12): normative lines changed: %d" % normative


BRIEF = """# Review brief: {branch} at `{head}`

- **Range** {range} (diff from `{start}`), profile {profile}, lane {lane}. Review only this range.
- **Your hunks** are in the patch your dispatch names. Read the changed hunks and what surrounds them, not
  whole files, and ask for every file you need in one turn.
- **Gate log:** {gate}
- **Drift gate,** what the range added: {drift}
- **Already settled on this branch:** {resolved}. Do not raise one again unless the change makes its
  reason untrue.
- **MUST sentences this range added, new obligations** (a reworded one pairs with the line it replaced and owes no guard run): {binding}.
- **sdd-pr** is `python3 {sdd_pr}`; a reviewer runs only
  `guard <path:line> --expect <text> --replace <text> -- <test command>`, which breaks one guard in a
  scratch copy and prints `pinned` (a test failed) or `untested`.
- **Severity and scope** are `{review_md}` § Severity and § Scope: by harm wherever the line is; wrong
  behaviour a caller can trigger is at least important, and wrong behaviour is never a suggestion; a
  document line is important only when a reader would build or test the wrong thing from it, and a slip
  in a document this branch wrote is a fix, not a finding. A defect in code or a document the branch did
  not change keeps its severity and ends ` · outside`. A suggestion names an input and a weaker result,
  at most five per reviewer; unsure, run it or drop it. No lead: a keyword missing from a sentence the
  code meets, "add a MUST", a comment's wording.
- **Return** one verdict line (`CLEAN`, or `<n> critical, <m> important, <s> suggestions`), then one fenced
  block of finding lines, then one **Coverage** line (what you read and ran, and what you could not check):

  ```
  - [ ] <critical|important> · <path>:<line> · <one sentence, at most 30 words> · evidence: <what you ran or quoted> · fix: <one line> · by: <your name>
  - <path>:<line> · <one sentence, at most 30 words> · by: <your name>
  ```
"""


def cmd_start(session: Session, args) -> int:
    """Everything a review pass needs before its reviewers are dispatched, in one call (references/review.md
    § The tool): the pull request's threads, the range, the lane, every reviewer's hunks, the drift gate's
    new lines, one shared brief, and the dispatch plan."""
    if not session.descriptor.strip():
        raise CliError("start: no %s here; set the repository up with /sdd-scaffold first" % DESCRIPTOR)
    pr = None
    if session.forge.name != "none":
        pr = session.pr(required=False)
        if pr and pr["state"] == "open" and pr.get("head") and not session.holds(pr["head"]):
            raise CliError("pull request %d's head %s is not in this checkout (HEAD %s): fetch it and check it "
                           "out, then start again" % (pr["number"], pr["head"][:7], session.head[:7]))
    pulled = pull_threads(session, pr) if pr and pr["state"] == "open" else 0
    if args.base:
        if not resolve_sha(session.root, args.base) and not resolve_sha(session.root, "origin/" + args.base):
            raise CliError("start: --base %s is not a branch or commit here" % args.base)
        session.fs.base = args.base
        session.save()
    rng = review_range(session.root, session.fs, session.base(), session.head, since_last=args.since_last)
    if not rng:
        print("range: empty; nothing to review since the last pass (sdd-pr status)")
        return 0
    start, widened = diff_start(session.root, session.base(), rng)
    files = changed_files(session.root, rng, session.globs, session.vendored, start, session.skip)
    reviewers, unassigned = reviewers_for(session.data, files)
    others = start_pass(session, args.agent)
    profile = profile_of(session.data)
    normative = normative_lines(session.root, start, files["documents"])
    lane = lane_of(args, pr, normative, profile)
    binding = binding_lines(session.root, start, files["documents"], binding_homes(session.data))
    head, root = session.head[:7], os.path.abspath(session.root)  # paths a subagent reads from anywhere
    out = os.path.join(root, ".sdd", "review", head)
    os.makedirs(out, exist_ok=True)

    plan, unread_docs = [], []
    for name, paths in reviewers.items():
        plan.append((name, paths, ""))
    code = files["code"] + files["tests"]
    if code:
        plan.append(("sdd-spec-conformance-reviewer", code,
                     "formal full lane, when the code implements a cited SPEC §" if profile == "formal"
                     else "only when the range touches what a constitution sentence binds"))
    elif binding and profile == "formal":
        # A new obligation written with no code: the reviewer reads the code the sentence describes. A
        # reword alone lists nothing here and sends only the document reviewer (methodology §6).
        written = sorted({b.rsplit(":", 1)[0] for b in binding})
        plan.append(("sdd-spec-conformance-reviewer", written, "a new obligation written with no code"))
    # The document reviewer reads a formal range only when it changed what binds: a normative line, a
    # requirement or an ADR (references/review.md § The tool). Other document changes are the drift
    # gate's and the maintainer's to read. An informative range sends every changed document, for
    # consistency against the code and the constitution.
    doc_reasons = []
    if files["documents"]:
        if profile == "informative":
            doc_reasons.append("every changed document")
        else:
            defaults = gate().DEFAULT_PATHS
            homes = {"requirement": str(_setting(session.data, "paths", "requirements") or defaults["requirements"]),
                     "adr": str(_setting(session.data, "paths", "adr") or defaults["adr"])}
            kinds = [k for k, home in homes.items()
                     if any(d == home.rstrip("/") or d.startswith(home.rstrip("/") + "/") for d in files["documents"])]
            if normative:
                doc_reasons.append("%d normative line%s changed" % (normative, "" if normative == 1 else "s"))
            doc_reasons.extend("a%s %s changed" % ("n" if k == "adr" else "", k.upper() if k == "adr" else k)
                               for k in kinds)
    if doc_reasons:
        when = "consistency" if profile == "informative" or lane.startswith("maintenance") else \
            "form" if lane.startswith("full") else "form on the full lane, consistency on maintenance"
        plan.append(("sdd-doc-reviewer", files["documents"], "%s; %s" % (when, ", ".join(doc_reasons))))
    elif files["documents"]:
        unread_docs = files["documents"]
    rows = []
    for name, paths, when in plan:
        patch = os.path.join(out, "diff-%s.patch" % _safe_name(name))
        with open(patch, "w", encoding="utf-8") as handle:
            handle.write(git(session.root, "diff", "--no-ext-diff", start, "HEAD", "--", *paths))
        rows.append("- %s: %s (%d file%s)%s" % (name, patch, len(paths), "" if len(paths) == 1 else "s",
                                                 "; %s" % when if when else ""))

    gate_log = os.path.join(root, ".sdd", "gate-%s.log" % head)
    gate_line = ("`%s`, the full gate at HEAD. Do not rebuild or rerun the suite; run one test only to pin a "
                 "failure the log lacks." % gate_log if os.path.exists(gate_log)
                 else "none at HEAD. Run only the tests your findings need.")
    drift_path, drift_line = os.path.join(out, "drift.txt"), "not vendored"
    gate_script = os.path.join(root, session.vendored)
    if os.path.exists(gate_script):
        code_run, output = run_test(["python3", gate_script, "check", "--changed-since", rng.split("..")[0],
                                     "--new-only"], session.root)
        with open(drift_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        verdict = [row for row in output.splitlines() if row.startswith("sdd-check:")] or \
            [row for row in output.strip().splitlines() if row.strip()][-1:]
        drift_line = "%s (`%s`)" % (verdict[0].strip() if verdict else "exit %s" % code_run, drift_path)
    resolved = "none"
    if session.fs.resolved:
        path = os.path.join(out, "resolved.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(f.render() for f in session.fs.resolved) + "\n")
        resolved = "`%s`" % path
    here = os.path.dirname(os.path.abspath(__file__))
    brief = os.path.join(out, "brief.md")
    with open(brief, "w", encoding="utf-8") as handle:
        handle.write(BRIEF.format(branch=session.branch, head=head, range="%s..HEAD" % rng.split("..")[0][:12],
                                  start=start[:12], profile=profile,
                                  lane=lane.split(" (")[0], gate=gate_line, drift=drift_line, resolved=resolved,
                                  binding=", ".join("`%s`" % b for b in binding) or "none",
                                  sdd_pr=os.path.join(here, "sdd-pr.py"),
                                  review_md=os.path.join(os.path.dirname(here), "references", "review.md")))

    print("review: %s at %s · range %s..HEAD · %s profile · lane %s"
          % (session.branch, head, rng.split("..")[0][:12], profile, lane))
    if not _setting(session.data, "agents"):
        print("agents: no agents: block in %s; /sdd-scaffold --upgrade adds it" % DESCRIPTOR)
    if widened:
        print(widened)
    if pr:
        print("pull request %d (%s): %d new finding%s pulled" % (pr["number"], pr["state"], pulled,
                                                                "" if pulled == 1 else "s"))
    for other in others:
        print("pass: also running, %s; this one runs beside it" % other)
    print("gate log: %s" % (gate_log if os.path.exists(gate_log) else "none at %s" % head))
    print("drift gate: %s" % drift_line)
    print("brief: %s" % brief)
    print("dispatch, in parallel, each with \"Read <brief>; your hunks: <patch>\":")
    print("\n".join(rows) if rows else
          "- nobody: the changed files need no reviewer (below)" if unassigned or unread_docs else
          "- nobody: no code, tests, other files or documents changed")
    if unassigned:
        print("no reviewer: %s" % _few(unassigned))
    if files["vendored"] or files["plans"] or files["skipped"]:
        print("not reviewed: %s" % _few(files["vendored"] + files["plans"] + files["skipped"]))
    if unread_docs:
        print("documents, no normative line, requirement or ADR changed; no reviewer: %s" % _few(unread_docs))
    return 0


def cmd_status(session: Session, args) -> int:
    fs = session.fs
    pr, unreachable = None, ""
    if session.forge.name != "none":
        try:
            pr = session.pr(required=False)
        except CheckoutError:
            raise
        except CliError as exc:
            unreachable = str(exc).splitlines()[0]
    last = fs.last_reviewed_sha()
    rng = review_range(session.root, fs, session.base(), session.head, since_last=True)
    start, widened = diff_start(session.root, session.base(), rng)
    files = changed_files(session.root, rng, session.globs, session.vendored, start, session.skip)
    code_changed = bool(files["code"] or files["tests"] or files["other"])
    changed = code_changed or bool(files["documents"])
    since = "code changed" if code_changed else "documents changed" if changed else "no change"
    # A fix that wrote a MUST is reviewed like code (review.md § Passes); any other document change, the
    # close-out's own commit among them, steers nothing.
    review_due = code_changed or bool(binding_lines(session.root, start, files["documents"], binding_homes(session.data)))
    print("branch %s · base %s · head %s · last reviewed %s (%s since)"
          % (session.branch, session.base(), session.head[:7], (last or "none")[:7], since))
    print("findings: %s" % session.path)
    if widened:
        print(widened)
    if os.path.exists(session.notes):
        print("notes: %s" % session.notes)
    if session.stale:
        print(session.stale)
    pending, merged = worker_branches(session.root, session.branch)
    if pending or merged:
        print("workers: " + " · ".join(["%s %s" % w for w in pending] + ["%s merged" % w for w in merged]))
    for sha in fs.unreviewed_passes():
        print("Reviewed %s: no reviewer reported; not a pass" % sha[:7])
    counts = {s: len([f for f in fs.blocking if f.severity == s]) for s in BLOCKING}
    print("open: %d critical, %d important · outside the change: %d · suggestions: %d"
          % (counts["critical"], counts["important"], len(fs.outside), len(fs.suggestions)))
    for finding in fs.open + fs.suggestions:
        print("#%s %s" % (key_of(finding), finding.render()))

    reasons: List[str] = []
    live = pr is not None and pr["state"] == "open"
    if counts["critical"] or counts["important"]:
        parts = ["%d %s" % (counts[s], s) for s in BLOCKING if counts[s]]
        reasons.append(", ".join(parts) + " open")
    unmirrored = [f for f in fs.blocking if not f.fields.get("forge") and "unanchored" not in f.flags]
    nxt = ("sdd-pr post --pr %d" % pr["number"] if live and unmirrored else "/sdd-triage") if reasons else ""
    # The budget (review.md § Passes): the pass before the maintainer's review, which is a `maintainer`
    # pass (pull writes one for their threads), and one pass over the fixes after it.
    reviewed = [i for i, p in enumerate(fs.passes) if p[2] == "maintainer"]
    if review_due and reviewed and fs.passes[reviewed[-1] + 1:]:
        print("passes: the budget is spent; only a new critical finding reopens review")
    elif review_due and reviewed:
        nxt = nxt or "/sdd-review --since-last"
    elif not last and changed:
        reasons.append("not reviewed yet")
        nxt = nxt or "/sdd-review"
    for name, _ in pending:
        reasons.append("worker branch %s not integrated" % name)
    if pending:
        nxt = nxt or "integrate %s (/sdd-deliver step 7)" % ", ".join(name for name, _ in pending)

    if session.forge.name == "none":
        print("forge: none")
    elif unreachable:
        print("forge: %s · not reachable (%s)" % (session.forge.name, unreachable))
        reasons.append("the forge was not reachable")
        nxt = nxt or "run sdd-pr status again once the forge is reachable"
    elif pr is None:
        print("forge: %s · no pull request" % session.forge.name)
        reasons.append("no pull request")
        nxt = nxt or "open the pull request (/sdd-deliver step 8)"
    elif pr["state"] == "merged":
        print("forge: %s · PR %d merged at %s" % (session.forge.name, pr["number"], (pr["merge"] or "?")[:7]))
        unposted = [f for f in fs.suggestions + fs.outside if not f.fields.get("comment")]
        if fs.blocking or unposted:
            print("still in the file: %d open line%s, %d line%s not on the pull request; carry or drop them "
                  "before deleting it" % (len(fs.blocking), "" if len(fs.blocking) == 1 else "s", len(unposted),
                                          "" if len(unposted) == 1 else "s"))
        waiting = len(fs.suggestions + fs.outside) - len(unposted)
        if waiting and not harvested(session, pr):
            print("%d line%s on the pull request wait%s for the next /sdd-triage --backlog"
                  % (waiting, "" if waiting == 1 else "s", "s" if waiting == 1 else ""))
        nxt = "/sdd-close, whose sdd-pr clean deletes " + cleanup_line(session.path, session.notes)
        print("Mergeable: merged")
        print("Next: " + nxt)
        return 0
    elif pr["state"] == "closed":
        print("forge: %s · PR %d closed" % (session.forge.name, pr["number"]))
        reasons.append("pull request %d is closed" % pr["number"])
        nxt = nxt or "reopen pull request %d, or open a new one" % pr["number"]
    else:
        try:
            shown_open = {f.fields["forge"] for f in fs.open if f.fields.get("forge")}  # outside lines too
            unknown = [t for t in session.forge.threads(pr["number"]) if not t["resolved"] and t["id"] not in shown_open]
            checks = session.forge.checks(pr["number"])
            print("forge: %s · PR %d (%s) · %d unresolved threads not open in the file · checks: %s"
                  % (session.forge.name, pr["number"], "draft" if pr["draft"] else "ready", len(unknown), checks))
            if unknown:
                reasons.append("%d unresolved threads not open in the file" % len(unknown))
                nxt = nxt or "sdd-pr pull --pr %d" % pr["number"]
            if checks == "fail":
                reasons.append("checks failing")
                nxt = nxt or "fix the failing checks"
            elif checks == "pending":
                reasons.append("checks pending")
                nxt = nxt or "wait for the checks"
            if pr["draft"]:
                reasons.append("the pull request is a draft")
                nxt = nxt or (leftovers(fs, pr) or "/sdd-close, which marks it ready")
        except CliError as exc:
            print("forge: %s · not reachable (%s)" % (session.forge.name, str(exc).splitlines()[0]))
            reasons.append("the forge was not reachable")
            nxt = nxt or "run sdd-pr status again once the forge is reachable"
    # Steers Next only: a suggestion never blocks, but it reaches the pull request, or the backlog, or it is lost.
    nxt = nxt or leftovers(fs, pr if live else None)
    if not nxt and merged:
        nxt = "remove the merged worker branches and their worktrees: %s" % ", ".join(merged)
    print("Mergeable: yes" if not reasons else "Mergeable: no — " + "; ".join(reasons))
    print("Next: " + (nxt or "merge"))
    return 0


def leftovers(fs: Findings, pr: Optional[dict]) -> str:
    """Suggestions not on the pull request yet go there; with no pull request, the close-out carries or drops them."""
    if pr is None:
        n = len(fs.suggestions + fs.outside)
        return "carry or drop %d non-blocking line%s (/sdd-close)" % (n, "" if n == 1 else "s") if n else ""
    n = len([f for f in fs.suggestions + fs.outside if not f.fields.get("comment")])
    return "sdd-pr post --pr %d (%d line%s not on it)" % (pr["number"], n, "" if n == 1 else "s") if n else ""


def harvested(session: Session, pr: dict) -> bool:
    """Whether the backlog's watermark has passed this merged pull request: on its base at the remote, where
    a harvest lands, or in this checkout."""
    when = instant(pr.get("merged_at", ""))
    texts = []
    try:
        texts.append(git(session.root, "show", "origin/%s:%s" % (pr.get("base") or session.base(), BACKLOG)))
    except CliError:
        pass
    texts.append("\n".join(read_backlog(session.root)))
    marks = [instant(get_watermark(text.splitlines())) for text in texts]
    return bool(when) and any(mark and when <= mark for mark in marks)


def cmd_pull(session: Session, args) -> int:
    session.need_forge()
    pr = session.pr()
    added = pull_threads(session, pr)
    print("pull: %d new finding%s from PR %d" % (added, "" if added == 1 else "s", pr["number"]))
    return 0


def pull_threads(session: Session, pr: dict) -> int:
    """Bring the pull request's unresolved threads the file does not know into it; return how many."""
    fs = session.fs
    known = fs.forge_ids()
    by_id = {f.fields["forge"]: f for f in fs.resolved if f.fields.get("forge")}
    added, people = 0, []
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
        fields = {"by": author_of(thread["body"]) or thread["author"] or "forge", "forge": thread["id"]}
        if not author_of(thread["body"]) and not (thread["author"] or "").endswith("[bot]"):
            people.append(_clean(thread["author"] or "forge").replace(":", "-"))
        text = first_sentence(thread["body"])
        outside = text.endswith(" - outside")  # the review request's marker, its separator turned into a dash
        fs.items.append(Finding("open", severity_of(thread["body"]), thread["path"], str(thread["line"] or ""),
                                text[:-len(" - outside")] if outside else text, fields, ["outside"] if outside else []))
        known.add(thread["id"])
        added += 1
    for body in session.forge.review_bodies(pr["number"]):
        if SUGGESTIONS_RE.search(body) or PASS_RE.search(body):
            continue  # the plugin's own comment, which the file wrote
        for finding in outside_lines(body):
            said = (finding.anchor, finding.text.casefold().rstrip(" ."))
            if any((f.anchor, f.text.casefold().rstrip(" .")) == said for f in fs.items):
                continue
            finding.fields.setdefault("by", author_of(body) or "forge")
            fs.items.append(finding)
            added += 1
    people = sorted(set(people))
    # The commit the maintainer read: the pull request's head, when this checkout holds it.
    seen = (pr["head"] if pr.get("head") and session.holds(pr["head"]) else session.head)[:7]
    if people and not [p for p in fs.passes if p[0] == seen and p[2] == "maintainer"]:
        # A thread with no `By:` line, not a bot's, is a person's: the maintainer's review, which opens the
        # pass over the fixes.
        fs.reviewed.append((seen, datetime.date.today().isoformat(), "maintainer",
                            "%s (%d of %d)" % (", ".join(people), len(people), len(people))))
    if added or not session.has_file():
        session.save()
    return added


def cmd_post(session: Session, args) -> int:
    session.need_forge()
    pr = session.pr()
    if pr["state"] != "open":
        raise CliError("pull request %d is %s; nothing to post" % (pr["number"], pr["state"]))
    session.guard()
    passes = unsummarised(session, pr)
    if passes and pr["head"] and pr["head"] != session.head:
        raise CliError("local HEAD %s is not the pull request's head %s; push or pull first"
                       % (session.head[:7], pr["head"][:7]))
    published = _post(session, args, pr)
    posted, edited = sync_suggestions(session, pr, args.dry_run, passes)
    note = sync_report(posted, edited, pr["number"], len(passes))
    if note:
        print("post: " + note)
    elif not published:
        print("post: nothing to post")
    return 0


def _post(session: Session, args, pr: dict) -> int:
    """Post the review for the blocking lines not yet on the forge; return how many lines it carries."""
    fs = session.fs
    candidates = [f for f in fs.blocking if not f.fields.get("forge")]
    adopted = 0
    if candidates:
        # A finding the forge already carries (an id that was not read back, a post interrupted before
        # the file was saved) adopts that thread's id and is never published a second time.
        adopted = len(adopt(session, pr, candidates))
        candidates = [f for f in candidates if not f.fields.get("forge")]
        if adopted and not args.dry_run:
            session.save()
    if not candidates:
        return 0
    if pr["head"] and pr["head"] != session.head:
        raise CliError("local HEAD %s is not the pull request's head %s; push or pull first"
                       % (session.head[:7], pr["head"][:7]))
    hunks = {}
    if candidates:
        merge_base = git(session.root, "merge-base", pr["base"] or session.base(), "HEAD").strip()
        hunks = parse_hunks(git(session.root, "diff", "%s...HEAD" % merge_base))
    anchored, unanchored = [], []
    for finding in candidates:
        line = int(finding.line) if finding.line.isdigit() else 0
        if line and line in hunks.get(finding.path, set()):
            anchored.append(finding)
        elif "unanchored" not in finding.flags:
            unanchored.append(finding)
    # The pass's counts are in its comment; a review carries only what sits on a line, and what cannot.
    body = ("### Not anchored to the diff\n\n" + "\n".join(
        "- `%s` %s" % (f.anchor, comment_body(f).replace("\n\n", " · ")) for f in unanchored)) if unanchored else ""
    comments = [{"path": f.path, "line": int(f.line), "body": comment_body(f)} for f in anchored]
    if args.dry_run:
        print(json.dumps({"commit_id": session.head, "event": "COMMENT", "body": body, "comments": comments}, indent=2))
        return len(comments) + len(unanchored)
    if not comments and not body:
        return 0
    ids = session.forge.post(pr["number"], session.head, body, comments, quiet=not unanchored)
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
    return len(anchored) + len(unanchored)


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
    session.guard()
    done = 0
    for finding in session.fs.resolved:
        thread_id = finding.fields.get("forge")
        if not thread_id or "mirrored" in finding.flags:
            continue
        session.forge.resolve(pr["number"], thread_id, reply_for(finding), finding.status)
        finding.flags.append("mirrored")
        done += 1
        session.save()
    print("resolve: %d thread%s answered and closed on PR %d" % (done, "" if done == 1 else "s", pr["number"]))
    note = sync_report(*sync_suggestions(session, pr), pr["number"])
    if note:
        print("resolve: " + note)
    return 0


# ---------------------------------------------------------------- the commands that write the file
def _clean(text: str) -> str:
    """A value written into a line: the field separator never appears inside one."""
    return " ".join((text or "").replace(SEP.strip(), "-").split())


def _anchor(text: str) -> Tuple[str, str]:
    path, sep, line = text.rpartition(":")
    return (path, line) if sep and line.isdigit() else (text, "")


def _same(a: Finding, b: Finding) -> bool:
    """Two lines about one defect: the same state, anchor and sentence, whatever each grades it."""
    return all(getattr(a, k) == getattr(b, k) for k in ("status", "anchor")) \
        and a.text.casefold().rstrip(" .") == b.text.casefold().rstrip(" .")


def _names(finding: Finding) -> set:
    return {n.strip() for n in finding.fields.get("by", "").split(",") if n.strip()}


def _covers(blocking: Finding, minor: Finding) -> bool:
    """Another reviewer's suggestion on the line a blocking finding names, in any words: one defect graded
    twice, the lower grade folded into the higher (references/review.md § Severity). One reviewer's own
    suggestion there is a second point and stays."""
    return blocking.status == "open" and minor.status == "suggestion" and bool(blocking.line) \
        and blocking.anchor == minor.anchor and not (_names(blocking) & _names(minor))


def _merge_by(into: Finding, other: Finding) -> None:
    names = [n.strip() for n in into.fields.get("by", "").split(",") if n.strip()]
    names += [n for n in (x.strip() for x in other.fields.get("by", "").split(",")) if n and n not in names]
    if names:
        into.fields["by"] = ", ".join(names)


def cmd_add(session: Session, args) -> int:
    if args.finding == ["-"]:
        # A reviewer's fence is piped as it is: its ``` lines are not findings.
        new = [parse_line(raw.strip(), n) for n, raw in enumerate(sys.stdin.read().splitlines(), 1)
               if raw.strip() and not raw.strip().startswith("```")]
    elif len(args.finding) == 3:
        severity, anchor, sentence = args.finding
        if severity not in SEVERITIES:
            raise CliError("add: the severity is one of %s" % ", ".join(SEVERITIES))
        if not _clean(sentence):
            raise CliError("add: the sentence is empty")
        if SEP.strip() in anchor:
            raise CliError("add: %r is not a path[:line]" % anchor)
        path, line = _anchor(anchor)
        fields = {k: _clean(v) for k, v in (("evidence", args.evidence), ("fix", args.fix), ("by", args.by)) if v}
        flags = ["outside"] if args.outside and severity in BLOCKING else []
        new = [Finding("suggestion" if severity == "suggestion" else "open", severity, path, line, _clean(sentence), fields,
                       flags)]
    else:
        raise CliError("usage: add <critical|important|suggestion> <path[:line]> <sentence> [--evidence …] [--fix …] "
                       "[--by …], or add - to read finding lines")
    for finding in new:
        where = "line %d: " % finding.lineno if finding.lineno else ""
        if finding.status not in ("open", "suggestion"):
            raise CliError("add: %s%s is resolved; add takes open findings and suggestions, and flip resolves them"
                           % (where, finding.anchor))
        if finding.status == "open" and not finding.fields.get("evidence"):
            raise CliError("add: %s%s %s finding needs %s (references/review.md § Evidence)"
                           % (where, "an" if finding.severity == "important" else "a", finding.severity,
                              "evidence:" if where else "--evidence"))
    flagged = [f for f in new if "outside" in f.flags and f.line.isdigit()]
    if flagged:
        # `outside` is a fact about the diff: a line the branch changed is in the change, and blocks.
        changed = changed_lines(session, sorted({f.path for f in flagged}))
        for finding in flagged:
            if int(finding.line) in changed.get(finding.path, set()):
                finding.flags = [flag for flag in finding.flags if flag != "outside"]
                print("add: the branch changed %s, so the finding blocks; `outside` dropped" % finding.anchor,
                      file=sys.stderr)
    added = merged = 0
    batch = []  # the lines this call added, so one folded away later is not counted twice
    for finding in new:
        twin = next((f for f in session.fs.items if _same(f, finding) or _covers(f, finding)), None)
        if twin is None:
            for minor in [f for f in session.fs.items if _covers(finding, f)]:
                # A blocking line takes over a suggestion on its anchor. The suggestion stays, resolved, so
                # its words are kept and a posted one's comment shows where it went.
                _merge_by(finding, minor)
                minor.status, minor.fields["deferred"] = "deferred", MERGED
                if any(minor is f for f in batch):
                    added -= 1
                merged += 1
            session.fs.items.append(finding)
            batch.append(finding)
            added += 1
            continue
        # One defect graded twice: the higher severity, and blocking unless both put it outside the change.
        twin.severity = min(twin.severity, finding.severity, key=SEVERITIES.index)
        if "outside" not in finding.flags and finding.status == "open":
            twin.flags = [flag for flag in twin.flags if flag != "outside"]
        _merge_by(twin, finding)
        for key in ("evidence", "fix"):
            if finding.fields.get(key) and not twin.fields.get(key):
                twin.fields[key] = finding.fields[key]
        merged += 1
    session.save()
    print("add: %d added, %d merged into an existing line" % (added, merged))
    return 0


def changed_lines(session: Session, paths: List[str]) -> Dict[str, set]:
    """The lines of ``paths`` the branch changed, against its merge base; none when that cannot be told."""
    try:
        merge_base = git(session.root, "merge-base", base_ref(session.root, session.base()), "HEAD").strip()
        return parse_hunks(git(session.root, "diff", "--no-ext-diff", "-U0", merge_base, "HEAD", "--", *paths))
    except CliError:
        return {}


def priority(finding: Finding, globs: List[str]) -> Tuple[int, int]:
    kind = kind_of(finding.path, globs)
    return SEVERITIES.index(finding.severity), KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER)


def backlog_line(finding: Finding, origin: str, full: bool = True) -> str:
    """A backlog line. A harvested one is short: its comment, which `from:` names, keeps the evidence."""
    parts = ([finding.severity] if finding.severity in BLOCKING else []) + [finding.anchor, finding.text]
    if full:
        parts += ["%s: %s" % (key, finding.fields[key]) for key in ("evidence", "fix", "by") if finding.fields.get(key)]
    return "- " + SEP.join(parts + ["from: " + origin])


def line_priority(line: str, globs: List[str]) -> Tuple[int, int]:
    """``priority`` for a backlog line: its severity, when it names one, then its path's kind."""
    parts = line[2:].split(SEP)
    severity = parts[0] if parts[0] in BLOCKING else "suggestion"
    path = _anchor(parts[1 if severity in BLOCKING and len(parts) > 1 else 0])[0]
    kind = kind_of(path, globs)
    return SEVERITIES.index(severity), KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER)


def _backlog_item(line: str) -> Optional[Tuple[str, str]]:
    """A backlog line's anchor and sentence, its severity, if any, set aside."""
    parts = line[2:].split(SEP) if line.startswith("- ") else []
    parts = parts[1:] if parts and parts[0] in SEVERITIES else parts
    return (parts[0], parts[1]) if len(parts) > 1 else None


def read_backlog(root: str) -> List[str]:
    try:
        with open(os.path.join(root, *BACKLOG.split("/")), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        lines = []
    return lines if "".join(lines).strip() else BACKLOG_HEAD.splitlines()


def write_backlog(root: str, lines: List[str]) -> None:
    path = os.path.join(root, *BACKLOG.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def carry(root: str, items: List[Tuple[Finding, str]], watermark: str = "", globs: Optional[List[str]] = None,
          full: bool = True) -> int:
    """Add each finding under `## Unsorted`, the first section, defects first and then by kind, tagged with
    where it came from; `/sdd-triage --backlog` sorts them into themes. An item the backlog already holds,
    by its anchor and sentence, is not written twice. ``watermark`` is written to the front matter.
    Returns how many were new."""
    globs = list(globs or DEFAULT_TEST_GLOBS)
    lines = read_backlog(root)
    if watermark:
        set_watermark(lines, watermark)
    held = {item for item in map(_backlog_item, lines) if item}
    new = []
    for finding, origin in sorted(items, key=lambda item: priority(item[0], globs)):
        if (finding.anchor, finding.text) in held:
            continue
        held.add((finding.anchor, finding.text))
        new.append(backlog_line(finding, origin, full))
    if new:
        if UNSORTED in lines:
            # Re-sort the whole section, so a defect carried later still leads; equal lines keep their order.
            start = end = lines.index(UNSORTED) + 1
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            block = lines[start:end]
            ranked = sorted([line for line in block if line.startswith("- ")] + new,
                            key=lambda line: line_priority(line, globs))
            lines[start:end] = ([line for line in block if line.strip() and not line.startswith("- ")] + ranked
                                + ([""] if end < len(lines) else []))
        else:
            at = next((n for n, line in enumerate(lines) if line.startswith("## ")), len(lines))
            while at > 0 and not lines[at - 1].strip():
                at -= 1
            lines[at:at] = ["", UNSORTED] + new + ([""] if at < len(lines) and lines[at].strip() else [])
    write_backlog(root, lines)
    return len(new)


def _front_matter_end(lines: List[str]) -> int:
    """The index of the line closing the backlog's front matter, or -1 when it has none."""
    if not lines or lines[0].strip() != "---":
        return -1
    return next((n for n in range(1, len(lines)) if lines[n].strip() == "---"), -1)


def get_watermark(lines: List[str]) -> str:
    for line in lines[1:max(_front_matter_end(lines), 0)]:
        key, colon, value = line.partition(":")
        if colon and key.strip() == WATERMARK:
            return value.strip().strip("'\"")
    return ""


def set_watermark(lines: List[str], value: str) -> None:
    end = _front_matter_end(lines)
    if end < 0:
        lines[0:0] = ["---", "kind: plan", "%s: %s" % (WATERMARK, value), "---"]
        return
    for n in range(1, end):
        if lines[n].partition(":")[0].strip() == WATERMARK:
            lines[n] = "%s: %s" % (WATERMARK, value)
            return
    lines.insert(end, "%s: %s" % (WATERMARK, value))


INSTANT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?$")


def instant(text: str) -> Optional[datetime.datetime]:
    """A date or an ISO 8601 date-time as a UTC instant, to the second; a date alone is its midnight UTC.
    Python 3.9 reads neither `Z` nor the seven fraction digits Azure DevOps writes, so this reads both."""
    match = INSTANT_RE.match((text or "").strip())
    if not match:
        return None
    y, mo, d, h, mi, sec, zone = match.groups()
    offset = datetime.timedelta(0)
    if zone and zone != "Z":
        sign = -1 if zone[0] == "-" else 1
        digits = zone[1:].replace(":", "")
        offset = sign * datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
    value = datetime.datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(sec or 0),
                              tzinfo=datetime.timezone.utc)
    return value - offset


def iso(value: datetime.datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _select(fs: Findings, selector: str) -> Finding:
    """One open line or suggestion, by the key status prints (`#ab12c`) or by its path:line."""
    lines = fs.open + fs.suggestions
    if selector.startswith("#"):
        hits = [f for f in lines if key_of(f) == selector[1:]]
        if not hits:
            raise CliError("flip: no open line or suggestion has the key %s; status prints the keys" % selector)
    else:
        hits = [f for f in lines if f.anchor == selector]
        if not hits:
            raise CliError("flip: no open finding or suggestion at %s" % selector)
    if len(hits) > 1:
        raise CliError("flip: %s names %d lines (%s); pick one by its key"
                       % (selector, len(hits), ", ".join("#" + key_of(f) for f in hits)))
    return hits[0]


def cmd_flip(session: Session, args) -> int:
    chosen = [key for key in ("fixed", "declined", "deferred", "carry", "dropped") if getattr(args, key)]
    if len(chosen) != 1:
        raise CliError("flip: give exactly one of --fixed <sha>, --declined <reason>, --deferred <where>, --carry, "
                       "--dropped")
    action, fs = chosen[0], session.fs
    if args.suggestions == bool(args.selector):
        raise CliError("flip: name one line (its #key or path:line), or pass --suggestions for every suggestion left")
    # The lines left that do not block: suggestions, and, carried, the defects outside the change.
    left = fs.suggestions + (fs.outside if action in ("carry", "deferred") else [])
    targets = list(left) if args.suggestions else [_select(fs, args.selector)]
    if not targets:
        print("flip: no suggestion left")
        return 0
    for finding in targets:
        if action == "declined" and finding.status == "suggestion":
            raise CliError("flip: a suggestion is fixed (--fixed <sha>), carried (--carry), deferred (--deferred <where>) "
                           "or dropped (--dropped)")
        if action == "dropped" and finding.status != "suggestion":
            raise CliError("flip: only a suggestion is dropped; a critical or important finding the maintainer "
                           "lets go is --deferred 'dropped by the maintainer'")
    if action == "fixed":
        full = resolve_sha(session.root, args.fixed)
        if not full:
            raise CliError("flip: %s is not a commit here" % args.fixed)
        remote = "origin/" + session.branch
        if resolve_sha(session.root, remote):
            try:
                git(session.root, "merge-base", "--is-ancestor", full, remote)
            except CliError:
                raise CliError("flip: %s is not on %s yet; push first" % (full[:7], remote))
    new = 0
    if action == "carry":
        session.guard()
        new = carry(session.root, [(f, session.branch) for f in targets], globs=session.globs)
    for finding in targets:
        if action == "dropped":
            if finding.fields.get("comment"):
                # Posted: the line stays, so its comment shows the drop and harvest leaves it out.
                finding.status, finding.fields["deferred"] = "deferred", DROPPED
            else:
                fs.items.remove(finding)
            continue
        if action == "carry":
            finding.status, finding.fields["deferred"] = "deferred", BACKLOG
            continue
        finding.status = action
        if action == "fixed":
            finding.fixed = resolve_sha(session.root, args.fixed)[:7]
        else:
            finding.fields[action] = _clean(getattr(args, action))
    session.save()
    plural = "" if len(targets) == 1 else "s"
    if action == "carry":
        print("flip: %d line%s carried to %s, %d new there; commit it" % (len(targets), plural, BACKLOG, new))
    else:
        print("flip: %d line%s %s" % (len(targets), plural, action))
    return 0


def harvest_start(session: Session, since: str, mark: str) -> Tuple[datetime.datetime, bool]:
    """Where a harvest starts, and whether that instant is in it: --since is, the watermark is not."""
    if since:
        if re.match(r"^#?\d+$", since):
            start = instant(session.forge.pr(int(since.lstrip("#"))).get("merged_at", ""))
            if start is None:
                raise CliError("harvest: pull request %s is not merged" % since)
            return start, True
        start = instant(since)
        if start is None:
            raise CliError("harvest: --since takes a date (2026-10-04), a date-time or a pull request (#12)")
        return start, True
    if not mark:
        raise CliError("harvest: %s has no %s yet; pass --since <date | #PR> for the first harvest" % (BACKLOG, WATERMARK))
    start = instant(mark)
    if start is None:
        raise CliError("harvest: %s in %s is not a date-time: %s" % (WATERMARK, BACKLOG, mark))
    return start, False


def recheck(session: Session, since: str) -> List[str]:
    """The backlog lines whose path a commit on HEAD changed after ``since``: the ones a delivery may have
    fixed or made stale, so the harvest re-reads those and not the whole file."""
    if not instant(since):
        return []
    # First parent, merges diffed against it: a pull request merged with a merge commit counts at its
    # merge, though its own commits are older than ``since``.
    # --name-status: a rename lists the old path too, the one a backlog line names.
    changed = {path for row in git(session.root, "log", "--since=" + since, "--first-parent", "-m", "--name-status",
                                   "--format=", "HEAD").splitlines() for path in row.split("\t")[1:]}
    out = []
    for line in read_backlog(session.root):
        item = _backlog_item(line)
        if item and _anchor(item[0])[0] in changed:
            out.append(line)
    return out


def cmd_harvest(session: Session, args) -> int:
    """The open suggestions of every pull request merged since the backlog's watermark, carried to it.
    Without a forge there are no comments (the close-out carried its lines): only the re-check runs."""
    forge = session.forge.name != "none"
    start, inclusive = harvest_start(session, args.since or "", get_watermark(read_backlog(session.root)))
    prs = []
    for pr in session.forge.merged(start) if forge else []:
        when = instant(pr.get("merged_at", ""))
        if when and (when >= start if inclusive else when > start):
            prs.append((when, pr["number"]))
    prs.sort()
    items: List[Tuple[Finding, str]] = []
    gone: List[Tuple[Finding, str]] = []
    settled = 0
    for _, number in prs:
        for comment in session.forge.comments(number):
            for finding in suggestion_lines(comment["body"]):
                defect = finding.severity in BLOCKING and finding.status == "open" and "outside" in finding.flags
                if not defect and (finding.severity != "suggestion" or finding.status not in ("suggestion", "open")):
                    settled += 1  # fixed, carried or dropped in its pull request
                elif not os.path.exists(os.path.join(session.root, finding.path)):
                    gone.append((finding, "#%d" % number))
                else:
                    items.append((finding, "#%d" % number))
    mark = iso(prs[-1][0]) if prs else (iso(start - datetime.timedelta(seconds=1)) if inclusive else "")
    if not forge:
        mark = iso(datetime.datetime.now(datetime.timezone.utc))
        print("harvest: no forge, so nothing to carry; the lines to re-check since %s" % iso(start))
    else:
        print("harvest: %d pull request%s merged %s %s%s" % (
            len(prs), "" if len(prs) == 1 else "s", "since" if inclusive else "after", iso(start),
            " (%s)" % ", ".join("#%d" % n for _, n in prs) if prs else ""))
    for finding, origin in gone:
        print("left out, its path is gone: " + backlog_line(finding, origin)[2:])
    if args.dry_run:
        for finding, origin in items:
            print(backlog_line(finding, origin, full=False))
        print("%s: %s (dry run: nothing written)" % (WATERMARK, mark or "unchanged"))
        return 0
    if not mark:
        return 0
    session.guard()
    # The lines to re-check: since the last harvest, or, on the first, since --since.
    for line in recheck(session, get_watermark(read_backlog(session.root)) or (iso(start) if args.since else "")):
        print("re-check, its path changed since the last harvest: " + line[2:])
    added = carry(session.root, items, mark, session.globs, full=False)
    print("harvest: %d line%s carried to %s, %d already there, %d settled in their pull request, %d left out; "
          "%s: %s; commit it" % (added, "" if added == 1 else "s", BACKLOG, len(items) - added, settled, len(gone),
                                 WATERMARK, mark))
    return 0


def cmd_record(session: Session, args) -> int:
    match = re.match(r"^(\d+)/(\d+)$", args.reported or "")
    if not match:
        raise CliError("record: --reported is <n>/<m>: how many of the dispatched reviewers reported")
    reported, dispatched = int(match.group(1)), int(match.group(2))
    if reported == 0:  # the pass ended, though it read nothing
        end_pass(session, args.agent)
    if reported == 0 or reported > dispatched:
        raise CliError("record: %d of %d is not a pass; no Reviewed line, so the range stays open"
                       % (reported, dispatched))
    names = [_clean(r) for r in (args.reviewers or "").split(",") if r.strip()]
    reviewers, agent = ", ".join(names), _clean(args.agent).replace(":", "-")
    if not reviewers or not agent:
        raise CliError("record: name the agent and the reviewers")
    if len(names) != dispatched:
        raise CliError("record: --reviewers names %d, but --reported says %d were dispatched" % (len(names), dispatched))
    line = (session.head[:7], datetime.date.today().isoformat(), agent, "%s (%d of %d)" % (reviewers, reported, dispatched))
    session.fs.reviewed.append(line)
    session.save()
    end_pass(session, args.agent)
    print("record: Reviewed %s · %s · %s: %s" % line)
    return 0


def end_pass(session: Session, agent: str) -> None:
    """Clear the agent's pass note and, when no other pass runs, the scratch worktree. Best effort: the pass
    is recorded either way, and a retry would write its line twice."""
    notes = _pass_notes(pass_note(session))
    notes.pop(_clean(agent).replace(":", "-"), None)
    _write_pass_notes(pass_note(session), notes)
    if notes:
        return  # another pass may be running guard in the scratch worktree
    try:
        remove_scratch(session)
    except CliError as exc:
        print("record: the scratch worktree stays (%s); `guard --cleanup` removes it"
              % str(exc).splitlines()[0], file=sys.stderr)


def scratch_dir(session: Session) -> str:
    """The pass's one scratch worktree, beside the findings: reused by every guard call, removed by record."""
    return os.path.join(os.path.dirname(os.path.dirname(session.path)), "scratch", slug(session.branch))


@contextlib.contextmanager
def scratch_lock(tree: str):
    """One guard run at a time in the scratch worktree, and no removal under a run."""
    os.makedirs(os.path.dirname(tree), exist_ok=True)
    with open(tree + ".lock", "a") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def remove_scratch(session: Session, prune: bool = False) -> bool:
    tree = scratch_dir(session)
    if not os.path.isdir(os.path.dirname(tree)):
        return False
    with scratch_lock(tree):  # waits for a guard run to finish
        if os.path.exists(tree + ".passes"):
            os.remove(tree + ".passes")
        if not os.path.exists(tree):
            if prune:
                git(session.root, "worktree", "prune")  # a folder deleted by hand stays registered until pruned
            return False
        git(session.root, "worktree", "remove", "--force", tree)
        return True


def shadowing(root: str, path: str) -> str:
    """The variable whose entry in the checkout holds ``path``, so the test would load the checkout's
    unchanged copy instead of the scratch worktree's; "" when none does."""
    for name in ("PYTHONPATH", "NODE_PATH"):
        for entry in os.environ.get(name, "").split(os.pathsep):
            if entry and os.path.isabs(entry):
                rel = os.path.relpath(os.path.realpath(entry), os.path.realpath(root))
                if rel == "." or (not rel.startswith(os.pardir) and path.startswith(rel + os.sep)):
                    return name
    return ""


def inside(root: str, path: str) -> str:
    """``path`` relative to the repository root, an absolute one under it included; refused when it leaves
    the root, so guard edits only its scratch worktree, never the checkout or a file outside it."""
    if os.path.isabs(path):
        path = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    path = os.path.normpath(path)
    if path == "." or path == os.pardir or path.startswith(os.pardir + os.sep) or os.path.isabs(path):
        raise CliError("guard: %s is not a path inside this repository" % path)
    return path


def baseline(tree: str, head: str, command: List[str], timeout: int) -> None:
    """The command passes in the scratch worktree with nothing changed, once per HEAD and command; else a
    failure with the guard removed would prove nothing (a dependency or a generated file missing there).
    What the run leaves behind is cleaned, so it cannot fail the run without the guard."""
    mark, key = tree + ".passes", "%s %s" % (head, json.dumps(command))
    try:
        with open(mark, encoding="utf-8") as handle:
            if key in handle.read().splitlines():
                return
    except FileNotFoundError:
        pass
    code, output = run_test(command, tree, timeout)
    if code != 0:
        tail = "\n".join("  " + row for row in output.rstrip().splitlines()[-15:])
        raise CliError("guard: `%s` %s in the scratch worktree with nothing changed, so a failure without the "
                       "guard would prove nothing; make it pass there first\n%s"
                       % (" ".join(command), "did not finish in %ds" % timeout if code is None else
                          "fails (exit %d)" % code, tail))
    git(tree, "clean", "-fdq")
    with open(mark, "a", encoding="utf-8") as handle:
        handle.write(key + "\n")


def cmd_guard(session: Session, args) -> int:
    """Remove one guard in the scratch worktree, run one test command there, and say whether the test
    noticed (references/review.md § The tool). The checkout and the findings file are never touched."""
    if args.cleanup:
        print("guard: scratch worktree %s" % ("removed" if remove_scratch(session, prune=True) else "absent"))
        return 0
    path, line = _anchor(args.selector or "")
    command = list(args.test_cmd)
    if not line or not args.expect or args.delete == (args.replace is not None) or not command:
        raise CliError("usage: guard <path:line> --expect <text> (--delete | --replace <text>) -- <test command>")
    path = inside(session.root, path)
    shadow = shadowing(session.root, path)
    if shadow:
        raise CliError("guard: %s reaches %s in the checkout, so the test would load the unchanged file; run guard "
                       "without it" % (shadow, path))
    tree = scratch_dir(session)
    session.close()  # a test can run for minutes: the findings stay free for other commands
    with scratch_lock(tree):
        if os.path.exists(tree):
            git(tree, "reset", "--quiet", "--hard", session.head)
            git(tree, "clean", "-fdq")  # a file an earlier run left behind could fail this one
        else:
            # --force: a folder deleted by hand is still registered, and add would refuse its path.
            git(session.root, "worktree", "add", "--force", "--quiet", "--detach", tree, session.head)
        target = os.path.join(tree, path)
        if not os.path.realpath(target).startswith(os.path.realpath(tree) + os.sep):
            raise CliError("guard: %s leads out of the scratch worktree (a link)" % path)
        try:
            # Bytes: a file in any encoding, its line endings kept, so only the one line changes.
            with open(target, "rb") as handle:
                lines = handle.read().split(b"\n")
        except OSError:
            raise CliError("guard: %s is not in HEAD" % path)
        n, expect = int(line), args.expect.encode("utf-8")
        current = lines[n - 1] if 1 <= n <= len(lines) else b""
        if current.count(expect) != 1:
            raise CliError("guard: %s:%d reads %r, which holds %r %s" % (
                path, n, current.decode("utf-8", "replace"), args.expect,
                "more than once; quote more of the line" if expect in current else "nowhere"))
        baseline(tree, session.head, command, args.timeout)
        if args.delete:
            del lines[n - 1]
        else:
            lines[n - 1] = current.replace(expect, args.replace.encode("utf-8"), 1)
        with open(target, "wb") as handle:
            handle.write(b"\n".join(lines))
        try:
            code, output = run_test(command, tree, args.timeout)
        finally:
            git(tree, "checkout", "--quiet", "--", path)
    edit = "deleted" if args.delete else "%r -> %r" % (args.expect, args.replace)
    ran = "did not finish in %ds" % args.timeout if code is None else "exited %d" % code
    print("guard: %s:%d %s; `%s` %s" % (path, n, edit, " ".join(command), ran))
    if code is None:
        print("pinned: the test hangs without the guard, which counts as a failure")
    else:
        print("pinned: the test fails without the guard; read the tail, a build error pins nothing" if code else
              "untested: the test stays green without the guard, unless it loads this code from the checkout "
              "(an editable install)")
    tail = output.rstrip().splitlines()[-15:]
    if tail:
        print("\n".join("  " + row for row in tail))
    return 0


def cmd_rename(session: Session, args) -> int:
    source = os.path.join(os.path.dirname(session.path), slug(args.from_branch) + ".md")
    if not os.path.exists(source):
        raise CliError("rename: no findings file for %s" % args.from_branch)
    if session.has_file():
        raise CliError("rename: %s already has a findings file at %s" % (session.branch, session.path))
    fs = load_findings(source, args.from_branch, "")
    # The new branch was not reviewed, and the old branch's threads are not on its pull request.
    fs.branch, fs.reviewed = session.branch, []
    for finding in fs.items:
        finding.fields.pop("forge", None)
        finding.fields.pop("comment", None)
        finding.flags = [flag for flag in finding.flags if flag not in ("mirrored", "unanchored")]
    session.fs = fs
    session.save()
    os.remove(source)
    print("rename: %s -> %s; its Reviewed lines, thread and comment ids dropped" % (args.from_branch, session.branch))
    return 0


def is_ancestor(root: str, older: str, newer: str) -> bool:
    try:
        git(root, "merge-base", "--is-ancestor", older, newer)
        return True
    except CliError:
        return False


def worktrees(root: str) -> List[Dict[str, str]]:
    """Every worktree of the clone, the main one first: its path, HEAD, branch ("" when detached), and the
    reason git gives when it is locked or prunable ("" when not)."""
    found: List[Dict[str, str]] = []
    for block in git(root, "worktree", "list", "--porcelain").strip().split("\n\n"):
        fields: Dict[str, str] = {}
        for line in block.splitlines():
            if line.strip():
                key, _, value = line.partition(" ")
                fields[key] = value.strip()
        if "worktree" in fields:
            ref = fields.get("branch", "")
            found.append({"path": fields["worktree"], "head": fields.get("HEAD", ""),
                          "branch": ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else "",
                          "locked": (fields["locked"] or "locked") if "locked" in fields else "",
                          "prunable": (fields["prunable"] or "prunable") if "prunable" in fields else ""})
    return found


def _real(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _within(path: str, tree: str) -> bool:
    path, tree = _real(path), _real(tree)
    return path == tree or path.startswith(tree.rstrip(os.sep) + os.sep)


def default_branch(root: str) -> str:
    """The remote's default branch, or "" when the clone does not know it."""
    try:
        name = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD").strip()
    except CliError:
        return ""
    return name[len("origin/"):] if name.startswith("origin/") else name


def cmd_clean(session: Session, args) -> int:
    """After the merge, what the branch leaves in the clone: its worktree, the branch, its findings file and
    delivery notes. Nothing changes until every check passes: the pull request is merged, the branch holds no
    commit the pull request does not, no worktree of it holds uncommitted work, and no line in the file
    would be lost. The pull request and the remote branch are the maintainer's, on the forge."""
    forge, root = session.forge.name != "none", session.root
    own = "" if session.branch == DETACHED else session.branch
    pr = None
    if forge and args.pr is not None:
        pr = session.forge.pr(args.pr)
        if args.target and pr.get("branch") and pr["branch"] != args.target:
            raise CliError("clean: pull request %d is %s, not %s" % (pr["number"], pr["branch"], args.target))
    elif forge and (args.target or own):
        pr = session.forge.pr_for_branch(args.target or own)
    branch = (pr or {}).get("branch") or args.target or own
    if not branch:
        raise CliError("clean: this checkout is detached; name the merged branch, or pass --pr")
    if branch != session.branch:
        session._rekey(branch, quiet=True)
    base = ((pr or {}).get("base") or "") or session.fs.base or session.base()
    if branch in (base, default_branch(root)):
        raise CliError("clean: %s is %s; name the merged branch, or pass --pr"
                       % (branch, "the base" if branch == base else "the default branch"))
    if not (args.target or args.pr is not None) and not (os.path.exists(session.path) or os.path.exists(session.notes)):
        raise CliError("clean: %s has no findings file or delivery notes, so nothing says it was delivered; "
                       "name it, or pass --pr" % branch)
    tip = resolve_sha(root, "refs/heads/" + branch)
    if forge:
        if pr is None:
            raise CliError("clean: %s has no pull request" % branch)
        if pr["state"] != "merged":
            raise CliError("clean: pull request %d is %s; the maintainer merges it on the forge first"
                           % (pr["number"], pr["state"]))
        head, where = pr["head"], "pull request %d" % pr["number"]
        known = bool(resolve_sha(root, head)) if head else False
        if tip and tip != head and not (known and is_ancestor(root, tip, head)):
            fetch = (" (this clone lacks it: git fetch origin %s)" % (session.forge.HEAD_REF % pr["number"])
                     if not known and session.forge.HEAD_REF else "" if known else " (this clone lacks it: fetch it)")
            raise CliError("clean: %s at %s holds commits %s's head %s does not%s; push them in a new pull request, "
                           "or ask the maintainer" % (branch, tip[:7], where, head[:7], fetch))
    else:
        head, where = "", ""
        if tip and not is_ancestor(root, tip, base_ref(root, base)):
            raise CliError("clean: %s at %s is not in %s; merge it first, or ask the maintainer" % (branch, tip[:7], base))
    fs = session.fs
    lost = fs.blocking + [f for f in fs.suggestions + fs.outside if not (forge and f.fields.get("comment"))]
    if lost:
        raise CliError("clean: %d line%s in the findings file would be lost; carry or drop them first "
                       "(sdd-pr flip --suggestions --carry, or flip <#key> --deferred <where>)"
                       % (len(lost), "" if len(lost) == 1 else "s"))
    trees = worktrees(root)
    mine = [tree for tree in trees if tree["branch"] == branch]
    if len(mine) > 1:
        raise CliError("clean: %s is checked out in %d worktrees (%s); remove all but one by hand"
                       % (branch, len(mine), ", ".join(tree["path"] for tree in mine)))
    plan: List[Tuple[str, List[str], str]] = []  # (what is done, the git command, the folder it runs in)
    left: List[str] = []
    if mine:
        path = mine[0]["path"]
        if mine[0]["locked"]:
            raise CliError("clean: the worktree %s is locked (%s); `git worktree unlock` it first"
                           % (path, mine[0]["locked"]))
        if mine[0]["prunable"] or not os.path.isdir(path):
            plan.append(("pruned the worktrees whose folder is gone, %s among them" % path, ["worktree", "prune"], root))
        else:
            if git(path, "status", "--porcelain").strip():
                raise CliError("clean: %s holds uncommitted work; commit it, or ask the maintainer" % path)
            ignored = [line[3:] for line in git(path, "status", "--porcelain", "--ignored").splitlines()
                       if line.startswith("!! ") and not line[3:].startswith(".sdd/")]
            also = (", with its ignored %s" % ", ".join(ignored[:5] + (["+%d more" % (len(ignored) - 5)] if len(ignored) > 5 else []))
                    if ignored else "")
            if _real(path) == _real(trees[0]["path"]):
                # The main checkout cannot be removed: it steps onto the base, so the branch can go.
                holder = next((tree["path"] for tree in trees if tree["branch"] == base), "")
                if holder:
                    plan.append(("detached %s at %s, which %s holds" % (path, base, holder),
                                 ["checkout", "--quiet", "--detach", base, "--"], path))
                elif resolve_sha(root, "refs/heads/" + base):
                    plan.append(("switched %s to %s" % (path, base), ["checkout", "--quiet", base, "--"], path))
                elif resolve_sha(root, "refs/remotes/origin/" + base):
                    plan.append(("switched %s to %s, from origin" % (path, base),
                                 ["checkout", "--quiet", "--track", "origin/" + base, "--"], path))
                else:
                    raise CliError("clean: %s holds %s, and its base %s is neither a branch here nor on origin; "
                                   "check out another branch there first" % (path, branch, base))
            elif any(_within(here, path) for here in (root, os.getcwd())):
                left += ["git worktree remove %s" % shlex.quote(path)] + (["git branch -D %s" % shlex.quote(branch)] if tip else [])
            else:
                plan.append(("removed the worktree %s%s" % (path, also), ["worktree", "remove", path], root))
    if tip and not left:
        plan.append(("deleted the branch %s (was %s)" % (branch, tip[:7]), ["branch", "-D", branch], root))
    files = [os.path.abspath(path) for path in (session.path, session.notes, pass_note(session)) if os.path.exists(path)]
    scratch = scratch_dir(session)
    others = ["%s (%s)" % (tree["path"], tree["branch"] or "detached") for tree in trees
              if head and tree["head"] == head and tree["branch"] != branch and _real(tree["path"]) != _real(scratch)]
    try:
        workers = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/%s--*" % branch).split()
    except CliError:
        workers = []
    held = "%s at %s" % (branch, tip[:7]) if tip else "no local %s" % branch
    print("clean: %s merged; %s" % (where, held) if forge else "clean: %s, in %s" % (held, base))
    failed: List[str] = []
    if args.dry_run:
        for done, command, _ in plan:
            print("would run: git %s  (%s)" % (" ".join(shlex.quote(word) for word in command), done))
        for path in files:
            print("would delete: %s" % path)
    else:
        session.guard()
        ran = False
        for done, command, folder in plan:
            if command[0] == "branch" and resolve_sha(root, "refs/heads/" + branch) != tip:
                raise CliError("clean: %s moved since it was checked; run clean again" % branch)
            try:
                git(folder, *command)
            except CliError as exc:
                raise CliError("clean: git %s failed%s: %s" % (" ".join(command), ", after the steps above" if ran else "",
                                                              str(exc).splitlines()[0] if str(exc) else exc))
            ran = True
            print("clean: " + done)
        try:
            remove_scratch(session, prune=True)
            if os.path.exists(scratch + ".lock"):
                os.remove(scratch + ".lock")
        except (CliError, OSError):
            pass  # a guard's scratch folder holds nothing that matters
        removed = []
        for path in files:
            try:
                os.remove(path)
                removed.append(path)
            except OSError as exc:
                failed.append("%s (%s)" % (path, exc.strerror))
        if removed:
            print("clean: deleted " + ", ".join(removed))
        if failed:
            print("sdd-pr: clean: could not delete " + ", ".join(failed), file=sys.stderr)
    if left:
        print("left for you, from another checkout (this one runs in it): " + " && ".join(left))
    if others:
        print("also on the pull request's head, remove when done: " + ", ".join(others))
    if workers:
        print("worker branches left: " + ", ".join(workers))
    return 2 if failed else 0


COMMANDS = {"status": cmd_status, "start": cmd_start, "scope": cmd_scope, "pull": cmd_pull, "post": cmd_post, "resolve": cmd_resolve,
            "harvest": cmd_harvest, "guard": cmd_guard, "add": cmd_add, "flip": cmd_flip, "record": cmd_record,
            "rename": cmd_rename, "clean": cmd_clean}


PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The grammar an agent needs, so nobody reads this file to learn it.
EPILOGS = {
    "add": """lines on stdin (add -), one per finding, in the findings file's grammar (references/review.md):
  - [ ] critical · <path>:<line> · <one sentence> · evidence: <what was run or quoted> · fix: <one line> · by: <reviewer>
  - [ ] important · <path>:<line> · <one sentence> · evidence: … · fix: … · by: … · outside
  - <path>:<line> · <one sentence> · by: <reviewer>                       (a suggestion)
a reviewer's ``` fence lines are skipped; a critical or important line needs evidence:; a line about code or
a document the branch did not change ends · outside, and add drops it from a line the branch changed""",
    "start": """prints the dispatch plan: one line per reviewer with its patch; dispatch each with
"Read <brief>; your hunks: <patch>". Files go under .sdd/review/<head>/. Another agent's pass on the
branch is reported, never a stop. The gate is never run here.""",
    "clean": """after the merge, run from any checkout of the clone, a detached one included: removes the
branch's worktree (one this command runs in is left to you, with the commands; the main checkout steps onto
the base), deletes the local branch only when it holds no commit the pull request lacks, then its findings
file and delivery notes. Refuses, changing nothing, while the pull request is open, the branch has commits
the pull request lacks, a worktree holds uncommitted work or is locked, or a line in the findings file would
be lost; refuses the base and the default branch, and, unnamed, a branch with no findings file or notes.
Never touches the pull request or the remote branch.""",
}


def newer_install() -> str:
    """A newer sdd-pr installed beside this one (a plugin cache keeps every version): its path, else ""."""
    parent, here = os.path.split(PLUGIN_ROOT)
    if not re.match(r"^\d+\.\d+\.\d+$", here):
        return ""
    best, found = __version__, ""
    try:
        names = os.listdir(parent)
    except OSError:
        return ""
    for name in names:
        tool = os.path.join(parent, name, "tools", "sdd-pr.py")
        if re.match(r"^\d+\.\d+\.\d+$", name) and version_lt(best, name) and os.path.exists(tool):
            best, found = name, tool
    return found


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError("usage: %s" % message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="sdd-pr", description="The branch's findings file and its pull-request mirror.")
    parser.add_argument("--version", action="version", version="sdd-pr %s at %s" % (__version__, PLUGIN_ROOT))
    parser.add_argument("--root", default=".", help="the repository root (default: .)")
    parser.add_argument("--branch", default=None, help="the branch (default: the checked-out one)")
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    for name in COMMANDS:
        cmd = sub.add_parser(name, epilog=EPILOGS.get(name), formatter_class=argparse.RawDescriptionHelpFormatter)
        cmd.add_argument("--pr", type=int, default=None, help="the merged pull request (default: the branch's latest)"
                         if name == "clean" else "the pull request (default: the branch's open one)")
        if name == "start":
            cmd.add_argument("--agent", required=True, help="who runs the pass: host and model, e.g. claude-opus-5-5")
            cmd.add_argument("--since-last", action="store_true",
                             help="only the commits since the last pass, by anyone, not the whole branch")
            cmd.add_argument("--lane", choices=("full", "maintenance"), help="this pass's lane")
            cmd.add_argument("--base", help="the branch this one starts from (a stacked branch's parent); kept in the file")
        if name == "scope":
            cmd.add_argument("--json", action="store_true")
            cmd.add_argument("--since-last", action="store_true",
                             help="only the commits since the last pass, not the whole branch")
            cmd.add_argument("--base", help="the branch this one starts from (a stacked branch's parent); kept in the file")
            cmd.add_argument("--agent", help="with --since-last: since this agent's own last pass")
            cmd.add_argument("--diff", metavar="KIND|REVIEWER", help="print the range's hunks for one kind or reviewer")
            cmd.add_argument("--start", metavar="AGENT", help="note that AGENT starts a pass; record clears the note")
        if name == "guard":
            cmd.add_argument("selector", nargs="?", help="the guard's <path:line>")
            cmd.add_argument("--expect", metavar="TEXT", help="text the line holds now")
            cmd.add_argument("--delete", action="store_true", help="delete the line")
            cmd.add_argument("--replace", metavar="TEXT", help="replace --expect within the line with TEXT")
            cmd.add_argument("--cleanup", action="store_true", help="remove the scratch worktree")
            cmd.add_argument("--timeout", type=int, default=600, metavar="SECONDS",
                             help="a run longer than this is killed and counts as a failure (default 600)")
            cmd.set_defaults(test_cmd=[])  # what follows `--`, split off before parsing (main)
        if name in ("post", "harvest", "clean"):
            cmd.add_argument("--dry-run", action="store_true")
        if name == "clean":
            cmd.add_argument("target", nargs="?", metavar="BRANCH", help="the merged branch (default: the pull "
                             "request's with --pr, else this checkout's)")
        if name == "harvest":
            cmd.add_argument("--since", metavar="DATE|#PR",
                             help="the first harvest: from this date, date-time or merged pull request, inclusive")
        if name == "add":
            cmd.add_argument("finding", nargs="*", help="<severity> <path[:line]> <sentence>, or - for lines on stdin")
            cmd.add_argument("--evidence")
            cmd.add_argument("--fix")
            cmd.add_argument("--by")
            cmd.add_argument("--outside", action="store_true", help="a critical or important line about code the change did not touch")
        if name == "flip":
            cmd.add_argument("selector", nargs="?", help="the #key status prints, or <path:line>")
            cmd.add_argument("--fixed", metavar="SHA")
            cmd.add_argument("--declined", metavar="REASON")
            cmd.add_argument("--deferred", metavar="WHERE")
            cmd.add_argument("--carry", action="store_true", help="append to %s and defer there" % BACKLOG)
            cmd.add_argument("--dropped", action="store_true", help="a suggestion only")
            cmd.add_argument("--suggestions", action="store_true", help="every suggestion left")
        if name == "record":
            cmd.add_argument("--agent", required=True)
            cmd.add_argument("--reviewers", default="")
            cmd.add_argument("--reported", required=True, metavar="N/M")
        if name == "rename":
            cmd.add_argument("--from", dest="from_branch", required=True, metavar="BRANCH")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    try:
        argv = list(sys.argv[1:] if argv is None else argv)
        # guard's test command follows `--` and is never parsed: its own options are not sdd-pr's.
        test_cmd = []
        if "guard" in argv and "--" in argv[argv.index("guard"):]:
            cut = argv.index("--", argv.index("guard"))
            argv, test_cmd = argv[:cut], argv[cut + 1:]
        args = build_parser().parse_args(argv)
        newer = newer_install()
        if newer:
            print("sdd-pr: this is %s at %s; a newer one is installed: python3 %s" % (__version__, PLUGIN_ROOT, newer),
                  file=sys.stderr)
        if test_cmd:
            args.test_cmd = test_cmd
        if not args.command:
            raise CliError("usage: sdd-pr [--root DIR] {%s} ..." % ",".join(COMMANDS))
        session = Session(args)
        try:
            return COMMANDS[args.command](session, args)
        finally:
            session.close()
    except SystemExit as exc:  # --version and --help
        return int(exc.code or 0)
    except (CliError, FileError) as exc:
        print("sdd-pr: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

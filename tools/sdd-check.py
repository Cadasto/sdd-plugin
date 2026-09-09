#!/usr/bin/env python3
"""sdd-check — the shared drift gate for a spec-driven repository.

One file, standard library only, Python 3.9 or newer. The contract this file
implements is `references/sdd-check.md` (families, report format, exit codes) and
`references/traceability-schema.md` (the descriptor keys, the record fields, the plan
frontmatter, the generated-block markers).

Exit codes: 0 ran with no errors, 1 ran with at least one error, 2 could not configure
itself (the descriptor is missing or unparseable, or the command line is invalid).
"""

import dataclasses
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

__version__ = "0.6.0"

#: Every family, in report order.
FAMILIES = (
    "descriptor",
    "map-schema",
    "map-to-tree",
    "index-sync",
    "plans",
    "tree-to-map",
    "doc-kinds",
    "rfc2119",
    "one-home",
    "links",
    "changelog",
    "generated",
    "draft-reason",
)

#: The severity a family has when the descriptor names none.
DEFAULT_SEVERITY = {
    "descriptor": "error",
    "map-schema": "error",
    "map-to-tree": "error",
    "index-sync": "error",
    "plans": "error",
    "tree-to-map": "warn",
    "doc-kinds": "warn",
    "rfc2119": "warn",
    "one-home": "error",
    "links": "error",
    "changelog": "warn",
    "generated": "error",
    "draft-reason": "off",
}

SEVERITIES = ("error", "warn", "off")

#: The families that cannot run without records.
RECORD_FAMILIES = ("map-to-tree", "index-sync", "plans", "tree-to-map", "generated", "draft-reason")

STATUS = ("draft", "stable", "deprecated")
IMPLEMENTATION = ("proposed", "planned", "in_progress", "partial", "landed", "shipped", "deferred")
ENFORCED = ("in_progress", "partial", "landed", "shipped")
PLAN_STATUS = ("active", "done", "postponed", "abandoned")
MODES = ("spec-first", "implementation-aligned")
ADR_STATUS = ("proposed", "accepted", "superseded", "deprecated")
UPSTREAM_STATE = ("proposed", "submitted", "landed-upstream", "landed", "rejected")

DEFAULT_KINDS = (
    "requirement",
    "specification",
    "adr",
    "plan",
    "guide",
    "analysis",
    "operations",
    "reference",
    "upstream",
)
NORMATIVE_KINDS = ("requirement", "specification", "adr", "plan")
INFORMATIVE_KINDS = ("guide", "analysis", "operations", "reference")

#: The frontmatter key and the vocabulary each kind's status axis is checked against.
KIND_VOCABULARY = {
    "requirement": ("status", STATUS),
    "specification": ("status", STATUS),
    "adr": ("status", ADR_STATUS),
    "plan": ("status", PLAN_STATUS),
    "upstream": ("state", UPSTREAM_STATE),
}

#: A keyword in one of these kinds is an error whatever the family's severity: each one
#: cites the specification, so a binding word there is a second source of truth.
RFC2119_CITING_KINDS = ("requirement", "adr", "plan", "reference")

DEFAULT_TEST_GLOBS = (
    "*_test.go",
    "test_*.py",
    "*_test.py",
    "*Test.php",
    "*.test.ts",
    "*.spec.ts",
    "*_test.rs",
)

#: `docs` is pruned at the repository root only; a nested directory named `docs` is code.
ROOT_PRUNED = ("docs",)
#: These are pruned wherever they sit.
NESTED_PRUNED = (".git", "vendor", "node_modules")

GENERATED_BLOCKS = ("requirements-index", "specifications-index", "adr-index")
GENERATED_OPEN = "<!-- sdd:generated %s -->"
GENERATED_CLOSE = "<!-- /sdd:generated -->"

DESCRIPTOR_REL = "docs/.sdd.yaml"

LEVELS = ("ERROR", "WARN", "NOTE")


# ---------------------------------------------------------------------------
# YAML parser (a strict subset: no anchors, no tags, no flow mappings)
# ---------------------------------------------------------------------------


class YamlError(Exception):
    """A shape the subset parser refuses. ``.line`` is the 1-based line number."""

    def __init__(self, message: str, line: int = 0, source: str = "<yaml>"):
        super().__init__(message)
        self.message = message
        self.line = line
        self.source = source

    def where(self) -> str:
        return "%s:%d" % (self.source, self.line) if self.line else self.source


_BLOCK_SCALAR = ("|", "|-", "|+", ">", ">-", ">+")
_INT_RE = re.compile(r"^-?\d+$")


class _YamlParser:
    """Recursive descent over pre-tokenised lines ``(indent, content, lineno)``."""

    def __init__(self, text: str, source: str):
        self.source = source
        self.raw = text.split("\n")
        self.tokens: List[Tuple[int, str, int]] = []
        self.i = 0
        self._tokenise()

    # -- tokenising -------------------------------------------------------
    def fail(self, message: str, lineno: int):
        raise YamlError(message, lineno, self.source)

    def _tokenise(self):
        started = False
        for index, raw in enumerate(self.raw):
            lineno = index + 1
            stripped = raw.strip()
            if not stripped:
                continue
            lead = raw[: len(raw) - len(raw.lstrip())]
            if "\t" in lead:
                self.fail("a tab in the indentation is not supported", lineno)
            if stripped.startswith("#"):
                continue
            if stripped == "---" or stripped.startswith("--- "):
                if started or self.tokens:
                    self.fail("a second document is not supported", lineno)
                started = True
                continue
            if stripped == "...":
                continue
            self.tokens.append((len(lead), raw[len(lead) :].rstrip(), lineno))

    # -- entry point ------------------------------------------------------
    def parse(self):
        if not self.tokens:
            return None
        indent = self.tokens[0][0]
        value = self._node(indent)
        if self.i < len(self.tokens):
            _, _, lineno = self.tokens[self.i]
            self.fail("this indentation closes no open block", lineno)
        return value

    def _node(self, indent: int):
        _, content, _ = self.tokens[self.i]
        if content == "-" or content.startswith("- "):
            return self._sequence(indent)
        return self._mapping(indent)

    # -- blocks -----------------------------------------------------------
    def _mapping(self, indent: int) -> dict:
        result: Dict[str, object] = {}
        while self.i < len(self.tokens):
            ind, content, lineno = self.tokens[self.i]
            if ind < indent:
                break
            if ind > indent:
                self.fail("this indentation closes no open block", lineno)
            if content == "-" or content.startswith("- "):
                self.fail("a sequence item where a 'key: value' was expected", lineno)
            key, value_text = self._split_key(content, lineno)
            self.i += 1
            result[key] = self._value(value_text, indent, lineno)
        return result

    def _sequence(self, indent: int) -> list:
        items: List[object] = []
        while self.i < len(self.tokens):
            ind, content, lineno = self.tokens[self.i]
            if ind < indent:
                break
            if ind > indent:
                self.fail("this indentation closes no open block", lineno)
            if not (content == "-" or content.startswith("- ")):
                break
            offset = 1
            while offset < len(content) and content[offset] == " ":
                offset += 1
            rest = content[offset:]
            item_indent = ind + offset
            if not rest:
                self.i += 1
                nxt = self.tokens[self.i] if self.i < len(self.tokens) else None
                if nxt is not None and nxt[0] > ind:
                    items.append(self._node(nxt[0]))
                else:
                    items.append(None)
                continue
            if rest == "-" or rest.startswith("- "):
                self.tokens[self.i] = (item_indent, rest, lineno)
                items.append(self._sequence(item_indent))
            elif self._looks_like_key(rest):
                self.tokens[self.i] = (item_indent, rest, lineno)
                items.append(self._mapping(item_indent))
            else:
                self.i += 1
                items.append(self._value(rest, item_indent, lineno))
        return items

    # -- scalars ----------------------------------------------------------
    @staticmethod
    def _looks_like_key(content: str) -> bool:
        if content[0] in "\"'":
            quote = content[0]
            end = content.find(quote, 1)
            return end != -1 and content[end + 1 :].startswith(":")
        return ": " in content or content.endswith(":")

    def _split_key(self, content: str, lineno: int) -> Tuple[str, str]:
        if content[0] in "\"'":
            quote = content[0]
            end = content.find(quote, 1)
            if end == -1:
                self.fail("an unterminated quoted key", lineno)
            rest = content[end + 1 :]
            if not rest.startswith(":"):
                self.fail("expected ':' after a quoted key", lineno)
            return content[1:end], rest[1:].strip()
        cut = content.find(": ")
        if cut == -1:
            if not content.endswith(":"):
                self.fail("expected a 'key: value' pair", lineno)
            return content[:-1].strip(), ""
        return content[:cut].strip(), content[cut + 2 :].strip()

    def _value(self, text: str, indent: int, lineno: int):
        if text in _BLOCK_SCALAR:
            return self._block_scalar(text, indent, lineno)
        if text.startswith("#"):
            # A comment after a key that opens a block ("families:  # error | warn | off").
            # The value is the block below, not the comment.
            text = ""
        if text == "":
            nxt = self.tokens[self.i] if self.i < len(self.tokens) else None
            if nxt is None:
                return None
            if nxt[0] > indent:
                return self._node(nxt[0])
            if nxt[0] == indent and (nxt[1] == "-" or nxt[1].startswith("- ")):
                return self._sequence(indent)
            return None
        return self._scalar(text, lineno)

    def _block_scalar(self, marker: str, indent: int, lineno: int) -> str:
        style, chomp = marker[0], marker[1:]
        collected: List[str] = []
        last = lineno
        for index in range(lineno, len(self.raw)):
            raw = self.raw[index]
            if not raw.strip():
                collected.append("")
                last = index + 1
                continue
            lead = raw[: len(raw) - len(raw.lstrip())]
            if "\t" in lead:
                self.fail("a tab in the indentation is not supported", index + 1)
            if len(lead) <= indent:
                break
            collected.append(raw)
            last = index + 1
        while self.i < len(self.tokens) and self.tokens[self.i][2] <= last:
            self.i += 1
        body = collected
        while body and not body[-1].strip():
            body.pop()
        if not body:
            return ""
        width = min(len(l) - len(l.lstrip()) for l in body if l.strip())
        rows = [l[width:] if l.strip() else "" for l in body]
        if style == "|":
            out = "\n".join(rows)
        else:
            folded: List[str] = []
            for row in rows:
                if not row:
                    folded.append("\n")
                elif folded and folded[-1] not in ("\n",):
                    folded[-1] = folded[-1] + " " + row
                else:
                    folded.append(row)
            out = "".join(folded)
        if chomp == "-":
            return out.rstrip("\n")
        if chomp == "+":
            return out + "\n"
        return out.rstrip("\n") + "\n"

    def _scalar(self, text: str, lineno: int):
        if text[0] in "\"'":
            quote = text[0]
            end = text.find(quote, 1)
            if end == -1:
                self.fail("an unterminated quoted scalar", lineno)
            return text[1:end]
        cut = text.find(" #")
        if cut != -1:
            text = text[:cut].rstrip()
        if not text:
            return None
        first = text[0]
        if first == "&":
            self.fail("an anchor is not supported", lineno)
        if first == "*":
            self.fail("an alias is not supported", lineno)
        if first == "!":
            self.fail("a tag is not supported", lineno)
        if first == "{":
            self.fail("a flow mapping is not supported", lineno)
        if first == "[":
            return self._inline_list(text, lineno)
        if text in ("null", "~"):
            return None
        if text in ("true", "True", "TRUE"):
            return True
        if text in ("false", "False", "FALSE"):
            return False
        if _INT_RE.match(text):
            return int(text)
        return text

    def _inline_list(self, text: str, lineno: int) -> list:
        items: List[Tuple[str, bool]] = []
        current = ""
        quote = ""
        quoted = False
        closed = -1
        for position, char in enumerate(text[1:], 1):
            if quote:
                if char == quote:
                    quote = ""
                else:
                    current += char
                continue
            if char in "\"'":
                quote = char
                quoted = True
                continue
            if char == "]":
                closed = position
                break
            if char == "[":
                self.fail("a nested inline list is not supported", lineno)
            if char == "{":
                self.fail("a flow mapping is not supported", lineno)
            if char == ",":
                if current.strip() or quoted:
                    items.append((current.strip(), quoted))
                current = ""
                quoted = False
                continue
            current += char
        if closed == -1:
            self.fail("an unterminated inline list", lineno)
        if current.strip() or quoted:
            items.append((current.strip(), quoted))
        rest = text[closed + 1 :].strip()
        if rest and not rest.startswith("#"):
            self.fail("trailing content after an inline list", lineno)
        out: List[object] = []
        for token, was_quoted in items:
            if was_quoted:
                out.append(token)
            elif token[0] == "&":
                self.fail("an anchor is not supported", lineno)
            elif token[0] == "*":
                self.fail("an alias is not supported", lineno)
            elif token in ("true", "True", "TRUE"):
                out.append(True)
            elif token in ("false", "False", "FALSE"):
                out.append(False)
            elif _INT_RE.match(token):
                out.append(int(token))
            else:
                out.append(token)
        return out


def load_yaml(text: str, *, source: str = "<yaml>"):
    """Parse the YAML subset this tool supports. Raises :class:`YamlError`."""
    return _YamlParser(text, source).parse()


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ANCHOR_RE = re.compile(r"<a\s+(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_FENCE_RE = re.compile(r"^(```+|~~~+)")
_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")


def slugify(heading: str) -> str:
    """The GitHub heading-anchor rule: lower-case, drop everything outside letters,
    digits, space, hyphen and underscore, then spaces to hyphens with no collapsing."""
    kept = []
    for char in heading.strip().lower():
        if char.isalnum() or char in " -_":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def _frontmatter_span(text: str) -> Optional[Tuple[int, int]]:
    """``(line of the opening '---', line after the closing '---')``, or ``None``."""
    lines = text.split("\n")
    index = 0
    in_comment = False
    while index < len(lines):
        stripped = lines[index].strip()
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_comment = True
            index += 1
            continue
        break
    if index >= len(lines) or lines[index].strip() != "---":
        return None
    for probe in range(index + 1, len(lines)):
        if lines[probe].strip() == "---":
            return index + 1, probe + 2
    return None


def frontmatter(text: str) -> Tuple[Optional[dict], int]:
    """Return ``(mapping, line after the closing '---')``, or ``(None, 0)`` when absent.

    The block opens on line 1 or right after a leading HTML comment block. A block that is
    present but does not parse raises :class:`YamlError` — absent and malformed are not the
    same thing, and a gate that treats them alike hides the defect.
    """
    span = _frontmatter_span(text)
    if span is None:
        return None, 0
    open_line, after = span
    body = "\n".join(text.split("\n")[open_line : after - 2])
    parsed = load_yaml(body, source="frontmatter")
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise YamlError("the frontmatter is not a mapping", open_line, "frontmatter")
    return parsed, after


def _content_lines(text: str, blank_code_spans: bool) -> List[Tuple[int, str]]:
    """Every line with fences, HTML comments and frontmatter blanked, numbers kept."""
    lines = text.split("\n")
    span = _frontmatter_span(text)
    after = span[1] if span else 0
    out: List[Tuple[int, str]] = []
    fence = None
    in_comment = False
    for index, raw in enumerate(lines):
        lineno = index + 1
        if after and lineno < after:
            out.append((lineno, ""))
            continue
        line = raw
        if in_comment:
            end = line.find("-->")
            if end == -1:
                out.append((lineno, ""))
                continue
            line = " " * (end + 3) + line[end + 3 :]
            in_comment = False
        if fence is not None:
            out.append((lineno, ""))
            if line.lstrip().startswith(fence):
                fence = None
            continue
        match = _FENCE_RE.match(line.lstrip())
        if match:
            fence = match.group(1)[:3]
            out.append((lineno, ""))
            continue
        while True:
            open_at = line.find("<!--")
            if open_at == -1:
                break
            close_at = line.find("-->", open_at + 4)
            if close_at == -1:
                line = line[:open_at]
                in_comment = True
                break
            line = line[:open_at] + " " * (close_at + 3 - open_at) + line[close_at + 3 :]
        if blank_code_spans:
            line = _CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)
        out.append((lineno, line))
    return out


def strip_noncontent(text: str) -> List[Tuple[int, str]]:
    """Lines with fences, inline code, HTML comments and frontmatter blanked."""
    return _content_lines(text, True)


def headings(text: str) -> List[Tuple[int, int, str, str]]:
    """Every ATX heading outside fenced code, as ``(line, level, text, slug)``."""
    out: List[Tuple[int, int, str, str]] = []
    for lineno, line in _content_lines(text, False):
        match = _HEADING_RE.match(line)
        if match:
            title = match.group(2).strip().rstrip("#").strip()
            out.append((lineno, len(match.group(1)), title, slugify(title)))
    return out


def explicit_anchors(text: str) -> set:
    """Every ``<a id="…">`` and ``<a name="…">`` target in the document."""
    return set(_ANCHOR_RE.findall(text))


def _heading_span(
    found: List[Tuple[int, int, str, str]], index: int, total: int
) -> Tuple[int, int]:
    """The half-open span of one heading: from it to the next heading of the same or higher level."""
    lineno, level = found[index][0], found[index][1]
    for later_line, later_level, _, _ in found[index + 1 :]:
        if later_level <= level:
            return lineno, later_line
    return lineno, total + 1


def section_slice(text: str, slug: str) -> Optional[Tuple[int, int]]:
    """The half-open line span ``[start, end)`` of the section a heading slug opens."""
    found = headings(text)
    total = len(text.split("\n"))
    for index, entry in enumerate(found):
        if entry[3] == slug:
            return _heading_span(found, index, total)
    return None


def table_rows(text: str) -> List[Tuple[int, List[str], List[str]]]:
    """Every pipe-table data row as ``(line, header cells, row cells)``."""
    rows: List[Tuple[int, List[str], List[str]]] = []
    lines = _content_lines(text, False)
    index = 0
    while index < len(lines) - 1:
        lineno, line = lines[index]
        nxt = lines[index + 1][1]
        if "|" in line and _is_separator(nxt):
            header = _split_cells(line)
            index += 2
            while index < len(lines):
                row_line, row_text = lines[index]
                if "|" not in row_text or not row_text.strip():
                    break
                rows.append((row_line, header, _split_cells(row_text)))
                index += 1
            continue
        index += 1
    return rows


def _is_separator(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped or not stripped:
        return False
    for cell in _split_cells(stripped):
        if not re.match(r"^:?-{1,}:?$", cell):
            return False
    return True


def _split_cells(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


_WAIVER_RE = re.compile(r"<!--\s*sdd-check:\s*allow\s+([^>]*?)\s*-->")


def waivers(text: str) -> set:
    """Every family named in an ``<!-- sdd-check: allow a, b -->`` comment in a file."""
    named = set()
    for match in _WAIVER_RE.finditer(text):
        for name in match.group(1).split(","):
            token = name.strip()
            if token:
                named.add(token)
    return named


#: Every RFC-2119 keyword as a whole upper-case word. The ``NOT`` forms come first so the
#: longer one wins, and the word boundary keeps ``MAY`` out of ``MAYBE``.
KEYWORD_RE = re.compile(
    r"\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|REQUIRED|RECOMMENDED|MAY|OPTIONAL)\b"
)

#: A modal in lower case binds nothing, which in a specification is the defect.
LOWER_MODAL_RE = re.compile(r"\b(must|shall|should|may not)\b")

#: Grammar a keyword cannot have: it is a verb, never a noun, and never doubled.
MALFORMED_RE = re.compile(r"\b(MUST to|are MUST|is MUST|MUST MUST|NOT NOT|SHOULD MUST)\b")

_SENTENCE_END_RE = re.compile(r"[.!?;](?=\s|$)")
_LIST_ITEM_RE = re.compile(r"^(?:[-*+]\s|\d+[.)]\s)")
_INLINE_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_REFERENCE_LINK_RE = re.compile(r"\[([^\]]*)\]\[[^\]]*\]")
_EDGE_UNDERSCORE_RE = re.compile(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])")


def sentences(text: str) -> List[Tuple[int, str]]:
    """Every prose sentence, as ``(the line it starts on, the sentence)``.

    A sentence ends at ``.``, ``!``, ``?`` or ``;`` followed by whitespace or the end of the
    line. A blank line, a heading and the start of a list item also end the one being built,
    so a title never runs into the paragraph beneath it. Fences, inline code, HTML comments
    and the frontmatter are already blank, because the scan is :func:`strip_noncontent`.
    """
    out: List[Tuple[int, str]] = []
    state = {"parts": [], "start": 0}

    def flush():
        joined = " ".join(part for part in state["parts"] if part).strip()
        if joined:
            out.append((state["start"], joined))
        state["parts"] = []
        state["start"] = 0

    def open_at(lineno):
        if not state["parts"]:
            state["start"] = lineno

    for lineno, line in strip_noncontent(text):
        stripped = line.strip()
        if not stripped or _HEADING_RE.match(stripped):
            flush()
            continue
        if _LIST_ITEM_RE.match(stripped):
            flush()
        position = 0
        for match in _SENTENCE_END_RE.finditer(stripped):
            chunk = stripped[position : match.end()].strip()
            position = match.end()
            open_at(lineno)
            if chunk:
                state["parts"].append(chunk)
            flush()
        tail = stripped[position:].strip()
        if tail:
            open_at(lineno)
            state["parts"].append(tail)
    flush()
    return out


def keyword_sentences(text: str) -> List[Tuple[int, str]]:
    """The sentences that carry at least one RFC-2119 keyword."""
    return [pair for pair in sentences(text) if KEYWORD_RE.search(pair[1])]


def normalise_sentence(sentence: str) -> str:
    """One sentence reduced to what it says, so two wordings of it compare equal.

    Lower case; link and image syntax replaced by the text a reader sees; code ticks and
    emphasis markers dropped; runs of whitespace collapsed; trailing punctuation removed.
    """
    text = _INLINE_LINK_RE.sub(r"\1", sentence)
    text = _REFERENCE_LINK_RE.sub(r"\1", text)
    text = text.replace("`", "")
    text = _EDGE_UNDERSCORE_RE.sub("", text)
    text = re.sub(r"[*~]+", "", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text.rstrip(" .,;:!?")


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------

DEFAULT_PATHS = {
    "requirements": "docs/requirements",
    "specifications": "docs/specifications",
    "adr": "docs/adr",
    "plans": "docs/plans",
}


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    return []


def _as_str(value, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class Descriptor:
    """`docs/.sdd.yaml`, with a default for every key the schema gives one."""

    def __init__(self, root: Path, data: dict):
        self.root = Path(root)
        self.data = data
        self.profile = _as_str(data.get("profile"), "full") or "full"
        self.req_style = _as_str(data.get("req_style"), "area-prefixed") or "area-prefixed"
        self.req_areas = [_as_str(a) for a in _as_list(data.get("req_areas"))]
        self.req_gap = data.get("req_gap", 10)
        self.excluded_areas = [_as_str(a) for a in _as_list(data.get("excluded_areas"))]
        kinds = [_as_str(k) for k in _as_list(data.get("doc_kinds"))]
        self.doc_kinds = kinds or list(DEFAULT_KINDS)
        self.default_mode = _as_str(data.get("default_mode"), "spec-first") or "spec-first"
        paths = data.get("paths")
        self.paths = dict(DEFAULT_PATHS)
        if isinstance(paths, dict):
            for key, value in paths.items():
                self.paths[_as_str(key)] = _as_str(value)
        self.traceability = _as_str(
            data.get("traceability"), "docs/specifications/traceability.yaml"
        )
        self.build_entrypoint = _as_str(data.get("build_entrypoint"), "make")
        self.ci_target = _as_str(data.get("ci_target"), "ci")
        self.spec_check_target = _as_str(data.get("spec_check_target"), "spec-check")
        self.use_probes = bool(data.get("use_probes", False))
        self.use_strands = bool(data.get("use_strands", False))
        self.upstream = data.get("upstream", "")
        self.ground_truth = data.get("ground_truth", "")
        hooks = data.get("hooks")
        self.hooks = hooks if isinstance(hooks, dict) else {}
        agents = data.get("agents")
        self.agents = agents if isinstance(agents, dict) else {}
        check = data.get("check")
        self.check = check if isinstance(check, dict) else {}
        self.script = _as_str(self.check.get("script"), "scripts/sdd-check.py")
        self.check_version = _as_str(self.check.get("version"), "")
        links = self.check.get("links")
        self.links_exclude = [_as_str(g) for g in _as_list((links or {}).get("exclude"))]
        changelog = self.check.get("changelog")
        changelog = changelog if isinstance(changelog, dict) else {}
        self.changelog_path = _as_str(changelog.get("path"), "CHANGELOG.md")
        max_words = changelog.get("max_words", 35)
        self.changelog_max_words = max_words if isinstance(max_words, int) else 35
        self.code_roots = [_as_str(r) for r in _as_list(self.check.get("code_roots"))]
        globs = [_as_str(g) for g in _as_list(self.check.get("test_globs"))]
        self.test_globs = globs or list(DEFAULT_TEST_GLOBS)
        self.probes_catalogue = _as_str(self.check.get("probes_catalogue"), "")
        families = self.check.get("families")
        self.families = {}
        if isinstance(families, dict):
            for key, value in families.items():
                self.families[_as_str(key)] = _as_str(value)

    # -- loading ----------------------------------------------------------
    @classmethod
    def load(cls, root: Path) -> "Descriptor":
        path = Path(root) / DESCRIPTOR_REL
        if not path.is_file():
            raise FileNotFoundError(DESCRIPTOR_REL)
        text = path.read_text(encoding="utf-8", errors="replace")
        data = load_yaml(text, source=DESCRIPTOR_REL)
        if isinstance(data, dict) and isinstance(data.get("sdd"), dict):
            data = data["sdd"]
        if not isinstance(data, dict):
            raise YamlError("the descriptor is not a mapping", 1, DESCRIPTOR_REL)
        return cls(Path(root), data)

    # -- derived ----------------------------------------------------------
    def resolve(self, rel: str) -> Path:
        return self.root / rel

    def severity(self, family: str) -> str:
        value = self.families.get(family)
        if value in SEVERITIES:
            return value
        return DEFAULT_SEVERITY.get(family, "error")

    def req_pattern(self) -> "re.Pattern":
        if self.req_style == "flat-numeric":
            return re.compile(r"REQ-\d{3,}")
        return re.compile(r"REQ-[A-Z][A-Z0-9]*-\d{3,}")

    def is_file_form(self, rel: str) -> bool:
        return Path(rel).suffix != "" or self.resolve(rel).is_file()

    def requirements_index_path(self) -> Path:
        rel = self.paths.get("requirements", DEFAULT_PATHS["requirements"])
        if self.is_file_form(rel):
            return self.resolve(rel)
        return self.resolve(rel) / "README.md"

    def requirements_dir(self) -> Optional[Path]:
        rel = self.paths.get("requirements", DEFAULT_PATHS["requirements"])
        if self.is_file_form(rel):
            return None
        return self.resolve(rel)

    def specification_files(self) -> List[Path]:
        rel = self.paths.get("specifications", DEFAULT_PATHS["specifications"])
        target = self.resolve(rel)
        if self.is_file_form(rel):
            return [target] if target.is_file() else []
        if not target.is_dir():
            return []
        return sorted(p for p in target.rglob("*.md") if p.is_file())

    def docs_roots(self) -> List[Path]:
        roots = [self.root / "docs"]
        seen = {"docs"}
        for rel in self.paths.values():
            normal = str(Path(rel).as_posix())
            if normal in seen or normal.startswith("docs/"):
                continue
            seen.add(normal)
            roots.append(self.resolve(rel))
        return roots

    def ground_truth_sources(self) -> List[str]:
        if isinstance(self.ground_truth, list):
            return [_as_str(s) for s in self.ground_truth if _as_str(s)]
        one = _as_str(self.ground_truth)
        return [one] if one else []

    def upstream_relations(self) -> Dict[str, dict]:
        if isinstance(self.upstream, dict):
            return {
                _as_str(name): body
                for name, body in self.upstream.items()
                if isinstance(body, dict)
            }
        name = _as_str(self.upstream)
        return {name: {"repo": name}} if name else {}


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

RECORD_KEYS = (
    "id",
    "title",
    "canonical",
    "status",
    "implementation",
    "packages",
    "tests",
    "probes",
    "operations",
    "draft_reason",
)
RECORD_LIST_KEYS = ("packages", "tests", "probes", "operations")


@dataclasses.dataclass
class Record:
    """One traceability-map record."""

    id: str = ""
    title: str = ""
    canonical: str = ""
    status: str = ""
    implementation: str = ""
    packages: List[str] = dataclasses.field(default_factory=list)
    tests: List[str] = dataclasses.field(default_factory=list)
    probes: List[str] = dataclasses.field(default_factory=list)
    operations: List[str] = dataclasses.field(default_factory=list)
    draft_reason: str = ""
    unknown_keys: List[str] = dataclasses.field(default_factory=list)
    line: int = 0
    raw: dict = dataclasses.field(default_factory=dict)

    def enforced(self) -> bool:
        return self.implementation in ENFORCED

    def evidence(self) -> List[str]:
        return list(self.packages) + list(self.tests) + list(self.operations)


def _sequence_line_numbers(text: str, key: str) -> List[int]:
    """The line number of every ``- `` item directly under a top-level key."""
    lines = text.split("\n")
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^%s\s*:\s*(#.*)?$" % re.escape(key), line):
            start = index + 1
            break
    if start is None:
        return []
    numbers: List[int] = []
    item_indent = None
    for index in range(start, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        match = re.match(r"^\s*-\s", line)
        if match and (item_indent is None or indent == item_indent):
            item_indent = indent
            numbers.append(index + 1)
    return numbers


def load_map(desc: Descriptor) -> List[Record]:
    """Read the traceability map. Raises ``FileNotFoundError`` or ``YamlError``."""
    path = desc.resolve(desc.traceability)
    if not path.is_file():
        raise FileNotFoundError(desc.traceability)
    text = path.read_text(encoding="utf-8", errors="replace")
    data = load_yaml(text, source=desc.traceability)
    entries = data.get("requirements") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    numbers = _sequence_line_numbers(text, "requirements")
    records: List[Record] = []
    for index, entry in enumerate(entries):
        lineno = numbers[index] if index < len(numbers) else 0
        if not isinstance(entry, dict):
            records.append(Record(line=lineno))
            continue
        record = Record(line=lineno, raw=entry)
        record.id = _as_str(entry.get("id"))
        record.title = _as_str(entry.get("title"))
        record.canonical = _as_str(entry.get("canonical"))
        record.status = _as_str(entry.get("status"))
        record.implementation = _as_str(entry.get("implementation"))
        record.draft_reason = _as_str(entry.get("draft_reason"))
        for key in RECORD_LIST_KEYS:
            setattr(record, key, [_as_str(v) for v in _as_list(entry.get(key))])
        record.unknown_keys = [_as_str(k) for k in entry.keys() if _as_str(k) not in RECORD_KEYS]
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class Context:
    """What every family reads: the root, the descriptor, the records, cached files."""

    def __init__(
        self,
        root: Path,
        desc: Descriptor,
        records: List[Record],
        changelog_all: bool = False,
    ):
        self.root = Path(root)
        self.desc = desc
        self.records = records
        self.records_by_id = {r.id: r for r in records if r.id}
        self.changelog_all = changelog_all
        self._texts: Dict[str, str] = {}
        self._docs_files: Optional[List[Path]] = None
        self._git_ok: Optional[bool] = None

    # -- files ------------------------------------------------------------
    def abs(self, path) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self.root / candidate

    def rel(self, path) -> str:
        candidate = self.abs(path)
        try:
            return candidate.relative_to(self.root).as_posix()
        except ValueError:
            return candidate.as_posix()

    def read(self, path) -> str:
        key = str(self.abs(path))
        if key not in self._texts:
            try:
                self._texts[key] = Path(key).read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._texts[key] = ""
        return self._texts[key]

    def docs_files(self) -> List[Path]:
        if self._docs_files is None:
            found: List[Path] = []
            for root in self.desc.docs_roots():
                if not root.is_dir():
                    continue
                for path in sorted(root.rglob("*.md")):
                    if path.is_file() and ".git" not in path.parts:
                        found.append(path)
            seen = set()
            unique = []
            for path in found:
                if str(path) not in seen:
                    seen.add(str(path))
                    unique.append(path)
            self._docs_files = unique
        return self._docs_files

    # -- git --------------------------------------------------------------
    def _run_git(self, args) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.root)] + [str(a) for a in args],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except (OSError, ValueError):
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.decode("utf-8", "replace")

    def git(self, *args) -> Optional[str]:
        """Run a git command in the repository, or return ``None`` when git cannot serve."""
        if self._git_ok is None:
            top = self._run_git(("rev-parse", "--show-toplevel"))
            self._git_ok = False
            if top is not None and top.strip():
                try:
                    self._git_ok = Path(top.strip()).resolve() == self.root.resolve()
                except OSError:
                    self._git_ok = False
        if not self._git_ok:
            return None
        return self._run_git(args)

    # -- severity ---------------------------------------------------------
    def level(self, family: str) -> str:
        return "ERROR" if self.desc.severity(family) == "error" else "WARN"


# ---------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------


def _frontmatter_of(ctx: Context, report: "Report", family: str, path: Path):
    """``(mapping, reported)`` — the frontmatter, or ``None`` with a parse failure reported."""
    try:
        front, _ = frontmatter(ctx.read(path))
    except YamlError as exc:
        report.add(
            family,
            ctx.level(family),
            ctx.rel(path),
            "frontmatter does not parse: %s" % exc.message,
        )
        return None, True
    return front, False


def doc_kind(ctx: Context, path) -> Optional[str]:
    """The ``kind:`` a document declares, or ``None`` when it declares none.

    A quiet reader: a frontmatter block that does not parse is not a kind, and the family
    that owns the file reports the parse failure through :func:`_frontmatter_of`.
    """
    try:
        front, _ = frontmatter(ctx.read(path))
    except YamlError:
        return None
    if not isinstance(front, dict):
        return None
    return _as_str(front.get("kind")) or None


def kind_zone(kind: str) -> str:
    """``normative``, ``upstream`` or ``informative``. A kind a repository adds is informative."""
    if kind in NORMATIVE_KINDS:
        return "normative"
    if kind == "upstream":
        return "upstream"
    return "informative"


def _waived(ctx: Context, report: "Report", family: str, path) -> bool:
    """Whether a file waives one family, recording the waiver so the summary can count it."""
    if family not in waivers(ctx.read(path)):
        return False
    report.waived.setdefault(family, []).append(ctx.rel(path))
    return True


def check_descriptor(ctx: Context, report: "Report") -> None:
    """The descriptor is internally consistent and matches the tree and the tool."""
    desc = ctx.desc
    level = ctx.level("descriptor")

    def add(message):
        report.add("descriptor", level, DESCRIPTOR_REL, message)

    if desc.profile not in ("full", "lightweight"):
        add("profile: '%s' is not full | lightweight" % desc.profile)
    if desc.req_style not in ("area-prefixed", "flat-numeric"):
        add("req_style: '%s' is not area-prefixed | flat-numeric" % desc.req_style)
    elif desc.req_style == "area-prefixed":
        if not desc.req_areas:
            add("req_areas: an area-prefixed repository declares at least one area")
    elif desc.req_areas:
        add("req_areas: a flat-numeric repository declares no areas")
    overlap = sorted(set(desc.excluded_areas) & set(desc.req_areas))
    if overlap:
        add("excluded_areas must be disjoint from req_areas: %s" % ", ".join(overlap))
    for key in ("requirements", "specifications", "adr", "plans"):
        rel = desc.paths.get(key, "")
        if not rel:
            add("paths.%s is not declared" % key)
            continue
        file_form = desc.is_file_form(rel)
        if file_form and desc.profile == "full":
            add("paths.%s: profile full requires a directory, not '%s'" % (key, rel))
            continue
        if file_form and key not in ("requirements", "specifications"):
            add("paths.%s: only requirements and specifications may name a file" % key)
            continue
        if not desc.resolve(rel).exists():
            add("paths.%s: '%s' does not exist" % (key, rel))
    if not desc.traceability:
        add("traceability is not declared")
    elif not desc.resolve(desc.traceability).is_file():
        add("traceability: '%s' does not exist" % desc.traceability)
    if desc.check_version != __version__:
        add(
            "check.version '%s' does not equal the tool's version %s"
            % (desc.check_version, __version__)
        )
    for family, value in desc.families.items():
        if family not in FAMILIES:
            add("check.families: unknown family '%s'" % family)
        elif value not in SEVERITIES:
            add("check.families.%s: '%s' is not error | warn | off" % (family, value))
    if desc.default_mode not in MODES:
        add("default_mode: '%s' is not %s" % (desc.default_mode, " | ".join(MODES)))
    # A repository may extend doc_kinds; an extra kind is read as informative. The four
    # normative kinds carry status vocabularies, so they cannot be dropped.
    missing_kinds = [kind for kind in NORMATIVE_KINDS if kind not in desc.doc_kinds]
    if missing_kinds:
        add("doc_kinds must keep the normative kinds; missing: %s" % ", ".join(missing_kinds))


def check_map_schema(ctx: Context, report: "Report") -> None:
    """Every record carries the fields the schema requires, with values in vocabulary."""
    desc = ctx.desc
    level = ctx.level("map-schema")
    pattern = desc.req_pattern()
    seen: Dict[str, int] = {}
    for record in ctx.records:
        where = desc.traceability
        if record.line:
            where = "%s:%d" % (desc.traceability, record.line)

        def add(message, anchor=where, at=level):
            report.add("map-schema", at, anchor, message)

        if not record.id:
            add("a record carries no id")
        elif not pattern.fullmatch(record.id):
            add("id '%s' does not match the repository's %s style" % (record.id, desc.req_style))
        else:
            if record.id in seen:
                add("duplicate id %s, first seen at line %d" % (record.id, seen[record.id]))
            else:
                seen[record.id] = record.line
            if desc.req_style == "area-prefixed":
                area = record.id.split("-")[1]
                if area in desc.excluded_areas:
                    add("id %s uses the excluded area '%s'" % (record.id, area))
                elif area not in desc.req_areas:
                    add("id %s uses an area that is not declared in req_areas: '%s'" % (record.id, area))
        for key in ("title", "canonical", "status", "implementation"):
            if not getattr(record, key):
                add("%s: %s is required" % (record.id or "a record", key))
        if record.status and record.status not in STATUS:
            add("%s: status '%s' is not %s" % (record.id, record.status, " | ".join(STATUS)))
        if record.implementation and record.implementation not in IMPLEMENTATION:
            add(
                "%s: implementation '%s' is not %s"
                % (record.id, record.implementation, " | ".join(IMPLEMENTATION))
            )
        if record.canonical:
            path_part, _, anchor_part = record.canonical.partition("#")
            if not path_part or not anchor_part:
                add("%s: canonical must be path#anchor, not '%s'" % (record.id, record.canonical))
        for key in RECORD_LIST_KEYS:
            value = record.raw.get(key)
            if value is None:
                continue
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                add("%s: %s must be a list of strings" % (record.id, key))
        for key in record.unknown_keys:
            if key == "plans":
                add(
                    "%s: unknown key 'plans' — the plan axis is retired from the record schema"
                    % record.id,
                    at="WARN",
                )
            else:
                add("%s: unknown key '%s'" % (record.id, key), at="WARN")


def _identifier_re(identifier: str) -> "re.Pattern":
    """Match one identifier on its own boundaries, so REQ-FOUND-0011 is not REQ-FOUND-001."""
    return re.compile(r"(?<![0-9A-Za-z_-])%s(?![0-9A-Za-z_-])" % re.escape(identifier))


def _anchor_span(text: str, fragment: str) -> Optional[Tuple[int, int]]:
    """The section an explicit ``<a id="…">`` sits in."""
    if fragment not in explicit_anchors(text):
        return None
    lines = text.split("\n")
    anchor_line = 0
    for index, line in enumerate(lines):
        if fragment in _ANCHOR_RE.findall(line):
            anchor_line = index + 1
            break
    if not anchor_line:
        return None
    found = headings(text)
    # An anchor that sits immediately above a heading names that heading's section.
    for index, entry in enumerate(found):
        if entry[0] <= anchor_line:
            continue
        between = range(anchor_line + 1, entry[0])
        if all(not lines[number - 1].strip() for number in between):
            return _heading_span(found, index, len(lines))
        break
    enclosing = None
    for index, entry in enumerate(found):
        if entry[0] <= anchor_line:
            enclosing = index
        else:
            break
    if enclosing is None:
        return 1, len(lines) + 1
    return _heading_span(found, enclosing, len(lines))


def _implements_marker(text: str, span: Tuple[int, int], identifier: str) -> bool:
    pattern = _identifier_re(identifier)
    start, end = span
    for lineno, line in _content_lines(text, False):
        if start <= lineno < end and "**Implements:**" in line and pattern.search(line):
            return True
    return False


def _probe_catalogue_ids(ctx: Context) -> Optional[set]:
    """Every PROBE id a catalogue heading carries, or ``None`` when none is configured."""
    rel = ctx.desc.probes_catalogue
    if not rel:
        return None
    found = set()
    for _, _, title, _ in headings(ctx.read(ctx.desc.resolve(rel))):
        found.update(re.findall(r"PROBE-\d+", title))
    return found


def check_map_to_tree(ctx: Context, report: "Report") -> None:
    """Every record resolves onto the tree: canonical section, evidence paths, probes."""
    desc = ctx.desc
    level = ctx.level("map-to-tree")
    catalogue = _probe_catalogue_ids(ctx)
    for record in ctx.records:
        anchor = record.id or "%s:%d" % (desc.traceability, record.line)

        def add(message):
            report.add("map-to-tree", level, anchor, message)

        path_part, _, fragment = record.canonical.partition("#")
        if path_part:
            target = desc.resolve(path_part)
            if not target.is_file():
                add("canonical file missing: %s" % path_part)
            elif fragment:
                text = ctx.read(target)
                span = section_slice(text, fragment)
                if span is None:
                    span = _anchor_span(text, fragment)
                if span is None:
                    add(
                        "canonical anchor '#%s' resolves to no heading slug and no explicit anchor in %s"
                        % (fragment, path_part)
                    )
                elif record.id and not _implements_marker(text, span, record.id):
                    add(
                        "the section at '#%s' carries no '**Implements:** %s' line"
                        % (fragment, record.id)
                    )
        for rel in record.packages:
            if not desc.resolve(rel).exists():
                add("missing package path: %s" % rel)
        for key in ("tests", "operations"):
            for rel in getattr(record, key):
                target = desc.resolve(rel)
                if not target.exists():
                    add("missing %s path: %s" % (key, rel))
                elif not target.is_file():
                    article = "an" if key[0] in "aeiou" else "a"
                    add(
                        "%s %s entry must be a file, not a directory: %s" % (article, key, rel)
                    )
        for probe in record.probes:
            if catalogue is not None:
                if probe not in catalogue:
                    add("%s resolves to no heading in %s" % (probe, desc.probes_catalogue))
            elif not any(probe in ctx.read(desc.resolve(rel)) for rel in record.tests):
                add("%s is named by no catalogue and by none of the record's tests" % probe)
        if record.enforced() and not record.evidence():
            add(
                "%s is '%s' and carries no evidence: packages, tests or operations"
                % (record.id, record.implementation)
            )


_STABILITY_HEADERS = ("stability", "status")
_IMPLEMENTATION_HEADERS = ("implementation", "impl.", "impl")


def _cell_text(cell: str) -> str:
    return cell.replace("`", "").replace("*", "").strip()


def _index_columns(header: List[str]) -> Tuple[Optional[int], Optional[int], List[str]]:
    """``(stability column, implementation column, the axes the table names no column for)``.

    An axis is found by header text. An axis the header does not name falls back to its
    position — second-to-last for stability, last for implementation — but only where the
    table has room for both axes beside the identifier and the title, and only onto a column
    the other axis has not already claimed. A narrower table is reported, never guessed at:
    comparing a title cell against a status vocabulary is a finding about nothing.
    """
    stability = None
    implementation = None
    for index, name in enumerate(header):
        lowered = _cell_text(name).lower()
        if lowered in _STABILITY_HEADERS and stability is None:
            stability = index
        elif lowered in _IMPLEMENTATION_HEADERS and implementation is None:
            implementation = index
    width = len(header)
    unnamed: List[str] = []
    if stability is None:
        candidate = width - 2
        if width >= 4 and candidate != implementation:
            stability = candidate
        else:
            unnamed.append("Stability")
    if implementation is None:
        candidate = width - 1
        if width >= 4 and candidate != stability:
            implementation = candidate
        else:
            unnamed.append("Implementation")
    return stability, implementation, unnamed


def _index_tables(text: str):
    """Every pipe table as ``(header line, header cells, [(line, row cells)])``."""
    tables: List[Tuple[int, List[str], List[Tuple[int, List[str]]]]] = []
    previous = None
    for lineno, header, cells in table_rows(text):
        if previous is None or lineno != previous + 1:
            tables.append((lineno - 2, header, []))
        tables[-1][2].append((lineno, cells))
        previous = lineno
    return tables


def check_index_sync(ctx: Context, report: "Report") -> None:
    """The requirements index, the detail files and the map agree on both status axes."""
    desc = ctx.desc
    level = ctx.level("index-sync")
    index_path = desc.requirements_index_path()
    index_rel = ctx.rel(index_path)
    if not index_path.is_file():
        report.add("index-sync", level, index_rel, "the requirements index is missing")
        return
    pattern = desc.req_pattern()
    rows = []
    unnamed_axes: List[Tuple[int, str]] = []
    for header_line, header, table in _index_tables(ctx.read(index_path)):
        stability, implementation, unnamed = _index_columns(header)
        carries_ids = False
        for lineno, cells in table:
            identifier = None
            for cell in cells:
                match = pattern.search(cell)
                if match:
                    identifier = match.group(0)
                    break
            if identifier is None:
                continue
            carries_ids = True
            rows.append(
                (
                    lineno,
                    identifier,
                    cells[stability] if stability is not None and stability < len(cells) else None,
                    cells[implementation]
                    if implementation is not None and implementation < len(cells)
                    else None,
                )
            )
        if carries_ids:
            unnamed_axes.extend((header_line, axis) for axis in unnamed)
    for header_line, axis in unnamed_axes:
        report.add(
            "index-sync",
            "WARN",
            "%s:%d" % (index_rel, header_line),
            "the index table names no %s column" % axis,
        )
    if not rows:
        report.add(
            "index-sync",
            level,
            index_rel,
            "the requirements index parses to zero rows carrying a REQ id",
        )
        return

    seen = set()
    for lineno, identifier, stability, implementation in rows:
        anchor = "%s:%d" % (index_rel, lineno)
        if identifier in seen:
            report.add("index-sync", level, anchor, "%s has more than one index row" % identifier)
            continue
        seen.add(identifier)
        record = ctx.records_by_id.get(identifier)
        if record is None:
            report.add(
                "index-sync",
                level,
                anchor,
                "%s has an index row but is missing from traceability" % identifier,
            )
            continue
        if stability is not None and _cell_text(stability).lower() != record.status.lower():
            report.add(
                "index-sync",
                level,
                anchor,
                "%s: the index Stability cell '%s' does not equal the record status '%s'"
                % (identifier, _cell_text(stability), record.status),
            )
        if (
            implementation is not None
            and _cell_text(implementation).lower() != record.implementation.lower()
        ):
            report.add(
                "index-sync",
                level,
                anchor,
                "%s: the index Implementation cell '%s' does not equal the record implementation '%s'"
                % (identifier, _cell_text(implementation), record.implementation),
            )
    for record in ctx.records:
        if record.id and record.id not in seen:
            report.add(
                "index-sync", level, record.id, "%s has a record but is missing from the index" % record.id
            )

    requirements_dir = desc.requirements_dir()
    if requirements_dir is None:
        report.add(
            "index-sync",
            "NOTE",
            index_rel,
            "the detail-file check is skipped: the lightweight profile keeps the index in one file",
        )
    else:
        for record in ctx.records:
            if not record.id:
                continue
            for detail in sorted(requirements_dir.glob("%s*.md" % record.id)):
                detail_rel = ctx.rel(detail)
                front, reported = _frontmatter_of(ctx, report, "index-sync", detail)
                if front is None:
                    if not reported:
                        report.add(
                            "index-sync",
                            level,
                            detail_rel,
                            "%s: the detail file carries no frontmatter" % record.id,
                        )
                    continue
                for key, expected in (
                    ("status", record.status),
                    ("implementation", record.implementation),
                ):
                    actual = _as_str(front.get(key))
                    if actual.lower() != expected.lower():
                        report.add(
                            "index-sync",
                            level,
                            detail_rel,
                            "%s: the detail file says %s '%s'; the record says '%s'"
                            % (record.id, key, actual, expected),
                        )

    for spec in desc.specification_files():
        front, _ = _frontmatter_of(ctx, report, "index-sync", spec)
        if not front or "requirements" not in front:
            continue
        declared = set(_as_str(item) for item in _as_list(front.get("requirements")))
        owned = set()
        for record in ctx.records:
            if not record.id or not record.canonical:
                continue
            if ctx.rel(desc.resolve(record.canonical.partition("#")[0])) == ctx.rel(spec):
                owned.add(record.id)
        if declared != owned:
            report.add(
                "index-sync",
                "WARN",
                ctx.rel(spec),
                "frontmatter requirements: %s does not equal the records whose canonical points here: %s"
                % (sorted(declared), sorted(owned)),
            )


def _newest_tag_commit(ctx: Context) -> Tuple[Optional[str], str]:
    """The commit the newest tag points at, and the reason when there is none."""
    if ctx.git("rev-parse", "--show-toplevel") is None:
        return None, "stale-plan rule needs git"
    tags = ctx.git("tag", "--sort=-creatordate") or ""
    newest = ""
    for line in tags.split("\n"):
        if line.strip():
            newest = line.strip()
            break
    if not newest:
        return None, "stale-plan rule needs a release tag"
    commit = ctx.git("rev-list", "-n", "1", newest) or ""
    if not commit.strip():
        return None, "stale-plan rule needs a release tag"
    return commit.strip(), ""


def check_plans(ctx: Context, report: "Report") -> None:
    """Every plan carries its four frontmatter keys, and a finished plan is swept."""
    desc = ctx.desc
    level = ctx.level("plans")
    plans_dir = desc.resolve(desc.paths.get("plans", "docs/plans"))
    if not plans_dir.is_dir():
        report.skip("plans", "no plans directory")
        return
    tag_commit, skip_reason = _newest_tag_commit(ctx)
    if skip_reason:
        report.skip("plans", skip_reason, partial=True)
    pattern = desc.req_pattern()
    for path in sorted(plans_dir.rglob("*.md")):
        if path.name == "_template.md" or not path.is_file():
            continue
        anchor = ctx.rel(path)
        front, reported = _frontmatter_of(ctx, report, "plans", path)
        if front is None:
            if not reported:
                report.add("plans", level, anchor, "the plan carries no frontmatter")
            continue
        for key in ("plan", "implements", "mode", "status"):
            if front.get(key) in (None, "", []):
                report.add("plans", level, anchor, "frontmatter %s is required" % key)
        name = _as_str(front.get("plan"))
        if name and name != path.stem:
            report.add(
                "plans",
                level,
                anchor,
                "plan '%s' does not equal the filename stem '%s'" % (name, path.stem),
            )
        status = _as_str(front.get("status"))
        if status and status not in PLAN_STATUS:
            report.add(
                "plans", level, anchor, "status '%s' is not %s" % (status, " | ".join(PLAN_STATUS))
            )
        mode = _as_str(front.get("mode"))
        if mode and mode not in MODES:
            report.add("plans", level, anchor, "mode '%s' is not %s" % (mode, " | ".join(MODES)))
        implemented: List[Record] = []
        for item in _as_list(front.get("implements")):
            token = _as_str(item)
            if not token.startswith("REQ-"):
                continue
            record = ctx.records_by_id.get(token) if pattern.fullmatch(token) else None
            if record is None:
                report.add("plans", level, anchor, "implements %s, which has no record" % token)
            else:
                implemented.append(record)
        if (
            status == "active"
            and mode == "spec-first"
            and implemented
            and all(r.implementation in ("landed", "shipped") for r in implemented)
        ):
            report.add(
                "plans",
                "WARN",
                anchor,
                "every requirement this plan implements is landed or shipped, yet the plan is still active",
            )
        if status == "done":
            open_ids = [r.id for r in implemented if not r.enforced()]
            if open_ids:
                report.add(
                    "plans",
                    "WARN",
                    anchor,
                    "status is done while %s is not enforced" % ", ".join(open_ids),
                )
        if tag_commit and status in ("done", "abandoned"):
            commit = ctx.git("log", "-1", "--format=%H", "--", anchor) or ""
            commit = commit.strip()
            if not commit:
                report.add(
                    "plans", "NOTE", anchor, "the stale-plan rule is skipped: the file is not committed"
                )
            elif ctx.git("merge-base", "--is-ancestor", commit, tag_commit) is not None:
                report.add(
                    "plans",
                    level,
                    anchor,
                    "finished plan predates the latest release tag; run /sdd-finalize",
                )


def _walk_code(ctx: Context, roots: List[Path], skip: set):
    """Every file under the code roots. The only exclusions are the pruned directories,
    the descriptor's own document paths, and a file that does not decode as UTF-8."""
    for root in roots:
        if not root.is_dir():
            if root.is_file():
                yield root
            continue
        for current, dirnames, filenames in os.walk(str(root)):
            here = Path(current)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in NESTED_PRUNED and ctx.rel(here / name) not in skip
            )
            for name in sorted(filenames):
                path = here / name
                if ctx.rel(path) not in skip:
                    yield path


def _is_pruned(rel: str, skip: set) -> bool:
    """Whether a repository-relative path sits inside a pruned or documented directory."""
    parts = rel.split("/")
    if any(part in NESTED_PRUNED for part in parts):
        return True
    prefix = ""
    for part in parts:
        prefix = part if not prefix else prefix + "/" + part
        if prefix in skip:
            return True
    return False


def _code_files(ctx: Context, roots: List[Path], skip: set) -> List[Path]:
    """The candidate files, from git where the repository is a work tree.

    Git knows what the repository keeps and what it ignores, so a scratch directory a
    developer never committed is not read as code. Without git the whole tree is walked,
    because the gate would rather read too much than quietly miss a citation.
    """
    listing = ctx.git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if listing is None:
        return list(_walk_code(ctx, roots, skip))
    root_rels = [ctx.rel(root) for root in roots]
    found: List[Path] = []
    seen = set()
    for rel in listing.split("\0"):
        if not rel or rel in seen or _is_pruned(rel, skip):
            continue
        under = any(
            base in ("", ".") or rel == base or rel.startswith(base + "/") for base in root_rels
        )
        if not under:
            continue
        seen.add(rel)
        found.append(ctx.root / rel)
    return sorted(found)


def check_tree_to_map(ctx: Context, report: "Report") -> None:
    """Every identifier the code cites names a record, and a test names a tested record."""
    desc = ctx.desc
    level = ctx.level("tree-to-map")
    pattern = re.compile(
        r"(?<![0-9A-Za-z_-])(%s)(?![0-9A-Za-z_-])" % desc.req_pattern().pattern
    )
    roots: List[Path] = []
    for rel in desc.code_roots:
        target = desc.resolve(rel)
        if target.exists():
            roots.append(target)
        else:
            report.add(
                "tree-to-map", level, DESCRIPTOR_REL, "code root does not exist: %s" % rel
            )
    if not desc.code_roots:
        roots = [ctx.root]
    skip = set(Path(rel).as_posix() for rel in desc.paths.values())
    skip.update(ROOT_PRUNED)
    skip.add(Path(desc.traceability).as_posix())
    for path in _code_files(ctx, roots, skip):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "REQ-" not in text:
            continue
        rel = ctx.rel(path)
        is_test = any(fnmatch.fnmatch(path.name, glob) for glob in desc.test_globs)
        seen = set()
        for lineno, line in enumerate(text.split("\n"), 1):
            for match in pattern.finditer(line):
                token = match.group(1)
                if token in seen:
                    continue
                seen.add(token)
                anchor = "%s:%d" % (rel, lineno)
                record = ctx.records_by_id.get(token)
                if record is None:
                    report.add("tree-to-map", level, anchor, "unknown identifier cited: %s" % token)
                elif is_test and not record.tests:
                    report.add(
                        "tree-to-map",
                        "WARN",
                        anchor,
                        "this test cites %s, whose record lists no tests" % token,
                    )


def check_draft_reason(ctx: Context, report: "Report") -> None:
    """A requirement that is draft and built owes a reason for the wording."""
    level = ctx.level("draft-reason")
    for record in ctx.records:
        if record.status == "draft" and record.enforced() and not record.draft_reason:
            report.add(
                "draft-reason",
                level,
                record.id or ctx.desc.traceability,
                "%s is draft and enforced, so it owes a draft_reason" % record.id,
            )


def check_doc_kinds(ctx: Context, report: "Report") -> None:
    """Every document declares a known kind and carries the status axis that kind owns."""
    desc = ctx.desc
    level = ctx.level("doc-kinds")
    paths = ctx.docs_files()
    if not paths:
        report.skip("doc-kinds", "no markdown documents")
        return
    for path in paths:
        if _waived(ctx, report, "doc-kinds", path):
            continue
        anchor = ctx.rel(path)
        front, reported = _frontmatter_of(ctx, report, "doc-kinds", path)
        if front is None:
            if not reported:
                report.add("doc-kinds", level, anchor, "the frontmatter declares no kind")
            continue
        kind = _as_str(front.get("kind"))
        if not kind:
            report.add("doc-kinds", level, anchor, "the frontmatter declares no kind")
            continue
        if kind not in desc.doc_kinds:
            report.add(
                "doc-kinds", level, anchor, "kind '%s' is not declared in doc_kinds" % kind
            )
            continue
        zone = kind_zone(kind)
        if zone == "upstream":
            if front.get("state") is None and front.get("status") is None:
                continue
            if front.get("status") is not None:
                report.add(
                    "doc-kinds",
                    "ERROR",
                    anchor,
                    "an upstream document names its axis state:, never status:",
                )
            state = _as_str(front.get("state"))
            if state and state not in UPSTREAM_STATE:
                report.add(
                    "doc-kinds",
                    "ERROR",
                    anchor,
                    "state '%s' is not %s" % (state, " | ".join(UPSTREAM_STATE)),
                )
        elif zone == "normative":
            key, vocabulary = KIND_VOCABULARY[kind]
            value = _as_str(front.get(key))
            if value and value not in vocabulary:
                report.add(
                    "doc-kinds",
                    "ERROR",
                    anchor,
                    "%s '%s' is not %s" % (key, value, " | ".join(vocabulary)),
                )
        elif front.get("status") is not None:
            report.add(
                "doc-kinds",
                "WARN",
                anchor,
                "an informative kind carries no status axis, so status: does not belong here",
            )


def _spec_sections(ctx: Context, report: "Report", anchor: str, text: str) -> bool:
    """Warn on every ``§`` section with no keyword. ``False`` when the document has none."""
    found = headings(text)
    marked = [index for index, entry in enumerate(found) if "\u00a7" in entry[2]]
    if not marked:
        return False
    total = len(text.split("\n"))
    content = strip_noncontent(text)
    for index in marked:
        start, end = _heading_span(found, index, total)
        carries = any(
            KEYWORD_RE.search(line) for lineno, line in content if start < lineno < end
        )
        if not carries:
            report.add(
                "rfc2119",
                "WARN",
                "%s:%d" % (anchor, found[index][0]),
                "the section '%s' is normative and carries no RFC-2119 keyword" % found[index][2],
            )
    return True


def _in_specification(ctx: Context, report: "Report", anchor: str, text: str) -> bool:
    """The three rules that apply inside a specification. ``False`` when it has no section."""
    has_sections = _spec_sections(ctx, report, anchor, text)
    for lineno, line in strip_noncontent(text):
        malformed = MALFORMED_RE.search(line)
        if malformed:
            report.add(
                "rfc2119",
                "ERROR",
                "%s:%d" % (anchor, lineno),
                "'%s' is a malformed RFC-2119 form" % malformed.group(0),
            )
    for lineno, sentence in sentences(text):
        if KEYWORD_RE.search(sentence):
            continue
        modal = LOWER_MODAL_RE.search(sentence)
        if modal:
            report.add(
                "rfc2119",
                "WARN",
                "%s:%d" % (anchor, lineno),
                "the lower-case modal '%s' binds nothing here; write the keyword in upper case"
                % modal.group(0),
            )
    return has_sections


def check_rfc2119(ctx: Context, report: "Report") -> None:
    """A keyword binds only where the specification says so, and it is well formed."""
    level = ctx.level("rfc2119")
    paths = ctx.docs_files()
    if not paths:
        report.skip("rfc2119", "no markdown documents")
        return
    sectionless: List[str] = []
    for path in paths:
        if _waived(ctx, report, "rfc2119", path):
            continue
        kind = doc_kind(ctx, path)
        if not kind:
            continue
        anchor = ctx.rel(path)
        text = ctx.read(path)
        if kind == "specification":
            if not _in_specification(ctx, report, anchor, text):
                sectionless.append(anchor)
            continue
        at = "ERROR" if kind in RFC2119_CITING_KINDS else level
        for lineno, line in strip_noncontent(text):
            words = KEYWORD_RE.findall(line)
            if not words:
                continue
            report.add(
                "rfc2119",
                at,
                "%s:%d" % (anchor, lineno),
                "the RFC-2119 keyword %s does not belong in a %s document; the specification "
                "owns the normative prose" % (", ".join(sorted(set(words))), kind),
            )
    if sectionless:
        report.skip(
            "rfc2119",
            "the \u00a7 section rule found no section in %s" % ", ".join(sectionless),
            partial=True,
        )


# --- family registry (later families are inserted above this banner) -------

CHECKS = {
    "descriptor": check_descriptor,
    "map-schema": check_map_schema,
    "map-to-tree": check_map_to_tree,
    "index-sync": check_index_sync,
    "plans": check_plans,
    "tree-to-map": check_tree_to_map,
    "doc-kinds": check_doc_kinds,
    "rfc2119": check_rfc2119,
    "draft-reason": check_draft_reason,
}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Finding:
    """One reported defect. ``level`` is ERROR, WARN or NOTE; a NOTE never fails a run."""

    family: str
    level: str
    anchor: str
    message: str


class Report:
    """Everything a run has to say, and the exit code it earns."""

    def __init__(self):
        self.findings: List[Finding] = []
        self.families_run: List[str] = []
        self.families_skipped: Dict[str, str] = {}
        #: The families that ran nothing at all, as opposed to one skipped rule.
        self.fully_skipped = set()
        #: Waived file per family, filled by the prose lints a later build adds.
        self.waived: Dict[str, List[str]] = {}
        self.link_exclusions: List[str] = []
        self.record_count = 0
        self.profile = "full"
        self.fatal_message: Optional[str] = None

    @classmethod
    def fatal(cls, message: str) -> "Report":
        """A run that could not configure itself: nothing ran, the exit code is 2."""
        report = cls()
        report.fatal_message = message
        return report

    def add(self, family: str, level: str, anchor: str, message: str) -> None:
        self.findings.append(Finding(family, level, anchor, message))

    def skip(self, family: str, reason: str, partial: bool = False) -> None:
        """Record that a family did not run, or — with ``partial`` — that one rule did not."""
        self.families_skipped[family] = reason
        if not partial:
            self.fully_skipped.add(family)

    def mark_run(self, family: str) -> None:
        """Record that a family ran, keeping the list in FAMILIES order."""
        self.families_skipped.pop(family, None)
        self.fully_skipped.discard(family)
        if family not in self.families_run:
            self.families_run.append(family)
            self.families_run.sort(key=FAMILIES.index)

    def errors(self) -> int:
        return len([f for f in self.findings if f.level == "ERROR"])

    def warnings(self) -> int:
        return len([f for f in self.findings if f.level == "WARN"])

    def exit_code(self) -> int:
        if self.fatal_message is not None:
            return 2
        return 1 if self.errors() else 0

    def _ordered(self) -> List[Finding]:
        order = {name: index for index, name in enumerate(FAMILIES)}
        return sorted(self.findings, key=lambda f: order.get(f.family, len(FAMILIES)))

    def render(self, root) -> str:
        if self.fatal_message is not None:
            # Exit 2: nothing ran, so there are no finding lines and no family lines.
            return "\n".join(
                [
                    "sdd-check %s · %s" % (__version__, root),
                    "sdd-check: FAILED — %s" % self.fatal_message,
                ]
            )
        lines = [
            "sdd-check %s · %s · profile %s · %d REQ records"
            % (__version__, root, self.profile, self.record_count)
        ]
        for finding in self._ordered():
            lines.append(
                "[%s] %s %s: %s" % (finding.family, finding.level, finding.anchor, finding.message)
            )
        errors, warnings = self.errors(), self.warnings()
        if errors:
            lines.append("sdd-check: FAILED — %d errors, %d warnings" % (errors, warnings))
        else:
            lines.append(
                "sdd-check: OK — %d checks, 0 errors, %d warnings"
                % (len(self.families_run), warnings)
            )
        skipped = [
            "%s (%s)" % (name, self.families_skipped[name])
            for name in FAMILIES
            if name in self.families_skipped
        ]
        lines.append(
            "families run: %s; skipped: %s"
            % (", ".join(self.families_run) or "none", "; ".join(skipped) or "none")
        )
        for family in FAMILIES:
            waived = self.waived.get(family)
            if waived:
                lines.append("waived: %s (%d files)" % (family, len(waived)))
        if self.link_exclusions:
            lines.append("link exclusions: %s" % ", ".join(self.link_exclusions))
        return "\n".join(lines)


def run_check(root: Path, only: Optional[List[str]], changelog_all: bool) -> Report:
    """Run the enabled families against a repository and return the report."""
    root = Path(root)
    if only is not None:
        unknown = [name for name in only if name not in FAMILIES]
        if unknown:
            return Report.fatal("unknown family '%s' in --only" % unknown[0])
    try:
        desc = Descriptor.load(root)
    except FileNotFoundError:
        return Report.fatal("%s: not found — run /sdd-scaffold to create it" % DESCRIPTOR_REL)
    except YamlError as exc:
        return Report.fatal("%s: %s" % (exc.where(), exc.message))
    except OSError as exc:
        return Report.fatal("%s: cannot be read (%s)" % (DESCRIPTOR_REL, exc))

    report = Report()
    report.profile = desc.profile
    report.link_exclusions = list(desc.links_exclude)

    planned: List[str] = []
    for family in FAMILIES:
        if desc.severity(family) == "off":
            report.skip(family, "off")
        elif only is not None and family not in only:
            report.skip(family, "not selected")
        elif family not in CHECKS:
            report.skip(family, "not implemented in this build")
        else:
            planned.append(family)

    records: List[Record] = []
    map_ok = True
    try:
        records = load_map(desc)
    except FileNotFoundError:
        map_ok = False
        report.add("map-schema", "ERROR", desc.traceability, "the traceability map is missing")
    except YamlError as exc:
        map_ok = False
        report.add(
            "map-schema",
            "ERROR",
            exc.where(),
            "the traceability map does not parse: %s" % exc.message,
        )
    except OSError as exc:
        map_ok = False
        report.add(
            "map-schema", "ERROR", desc.traceability, "the traceability map cannot be read (%s)" % exc
        )
    if map_ok and not records:
        map_ok = False
        report.add(
            "map-schema", "ERROR", desc.traceability, "the traceability map yields zero records"
        )
    report.record_count = len(records)

    ctx = Context(root, desc, records, changelog_all)
    for family in planned:
        if not map_ok and family in RECORD_FAMILIES:
            report.skip(family, "map unavailable")
            continue
        CHECKS[family](ctx, report)
        if family not in report.fully_skipped:
            report.families_run.append(family)
    if not map_ok:
        # The map failure is a map-schema finding whatever the configuration says, so the
        # summary has to show map-schema as a family that ran.
        report.mark_run("map-schema")
    return report


# ---------------------------------------------------------------------------
# Generators (stub — a later build writes the generated blocks)
# ---------------------------------------------------------------------------


def run_generate(root: Path, only: Optional[List[str]], verify: bool) -> int:
    print("not implemented in this build")
    return 2


def run_context(root: Path, requirement: str) -> int:
    print("not implemented in this build")
    return 2


# ---------------------------------------------------------------------------
# Selftest (stub — a later build runs the tool against the baseline fixture)
# ---------------------------------------------------------------------------


def run_selftest(root: Path) -> int:
    print("not implemented in this build")
    return 2


#: The minimal passing repository the unit tests and the selftest build on.
_BASELINE_FILES = {
    "docs/.sdd.yaml": """sdd:
  profile: full

  req_style: area-prefixed
  req_areas: [FOUND]
  req_gap: 10
  excluded_areas: [BENCH]

  doc_kinds: [requirement, specification, adr, plan, guide, analysis, operations, reference, upstream]

  default_mode: spec-first

  paths:
    requirements: docs/requirements
    specifications: docs/specifications
    adr: docs/adr
    plans: docs/plans

  traceability: docs/specifications/traceability.yaml

  build_entrypoint: make
  ci_target: ci
  spec_check_target: spec-check

  use_probes: false
  use_strands: false

  upstream: ""

  ground_truth: "the specifications in docs/specifications"

  check:
    script: scripts/sdd-check.py
    version: "0.6.0"
    links:
      exclude: []
    changelog:
      path: CHANGELOG.md
      max_words: 35
    code_roots: []
    test_globs: ["*_test.py"]
    probes_catalogue: ""
    families:
      descriptor: error
      map-schema: error
      map-to-tree: error
      index-sync: error
      plans: error
      tree-to-map: warn
      doc-kinds: warn
      rfc2119: warn
      one-home: error
      links: error
      changelog: warn
      generated: error
      draft-reason: off

  hooks:
    stop_nudge: true
""",
    "docs/requirements/README.md": """---
kind: guide
---

# Requirements

Each row links to the requirement it names. The traceability map owns both status axes.

<!-- sdd:generated requirements-index -->

| ID | Title | Stability | Implementation |
|---|---|---|---|
| [REQ-FOUND-001](REQ-FOUND-001.md) | Environment boundary | Draft | shipped |

<!-- /sdd:generated -->
""",
    "docs/requirements/REQ-FOUND-001.md": """---
kind: requirement
id: REQ-FOUND-001
title: Environment boundary
status: draft
implementation: shipped
---

# REQ-FOUND-001 — Environment boundary

The service reads its configuration from the environment when it starts.

## Acceptance criteria

- A start with every declared variable set is accepted.
- A start with a declared variable absent is refused, and the refusal names the variable.

## Out of scope

- Reloading the configuration while the service runs.

**Canonical:** [SPEC-ENV §1](../specifications/env.md#1--boundary-req-found-001)
""",
    "docs/specifications/README.md": """---
kind: guide
---

<!-- sdd-check: allow rfc2119, one-home -->

# Specifications

Each specification owns the normative prose for the requirements it lists.

<!-- sdd:generated specifications-index -->

| Specification | Status | Mode |
|---|---|---|
| [SPEC-ENV](env.md) | draft | spec-first |

<!-- /sdd:generated -->
""",
    "docs/specifications/env.md": """---
kind: specification
spec: SPEC-ENV
status: draft
mode: spec-first
requirements: [REQ-FOUND-001]
---

# SPEC-ENV — Environment

This document owns how the service reads its environment.

## §1 — Boundary (REQ-FOUND-001)

**Implements:** REQ-FOUND-001

The service MUST read every declared variable from the environment when it starts.

The service MUST refuse to start when a declared variable is absent.
""",
    "docs/specifications/traceability.yaml": """# traceability.yaml — the machine-readable REQ to spec to code to test map.
requirements:
  - id: REQ-FOUND-001
    title: Environment boundary
    canonical: docs/specifications/env.md#1--boundary-req-found-001
    status: draft
    implementation: shipped
    packages:
      - src/env
    tests:
      - tests/env_test.py
""",
    "docs/adr/README.md": """---
kind: guide
---

# Decision records

<!-- sdd:generated adr-index -->

| ADR | Title | Status |
|---|---|---|

<!-- /sdd:generated -->
""",
    "docs/plans/2026-01-01-env.md": """---
kind: plan
plan: 2026-01-01-env
implements: [REQ-FOUND-001]
mode: spec-first
status: done
---

# 2026-01-01 — Environment boundary

## Tasks

- [x] Read the declared variables when the service starts.
- [x] Refuse a start with a declared variable absent.
""",
    "docs/development-process.md": """---
kind: guide
---

# Development process

Write the specification first, then the code, then the tests that cite the requirement.
""",
    "src/env/__init__.py": "",
    "tests/env_test.py": '''def test_req_found_001_boundary():
    """REQ-FOUND-001: the service refuses to start when a declared variable is absent."""
    assert True
''',
    "CHANGELOG.md": """# Changelog

## [Unreleased]

### Added
- Config: the service reads every declared variable from the environment when it starts.
""",
    "AGENTS.md": """# Agent guide

Read [the development process](docs/development-process.md) before changing anything here.
""",
}


def write_baseline(root: Path) -> None:
    """Write the minimal passing repository the tests and the selftest run against."""
    root = Path(root)
    for rel, text in _BASELINE_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

COMMANDS = ("check", "generate", "context", "selftest")

USAGE = """usage: sdd-check [check|generate|context|selftest] [options]

  check [--root DIR] [--only fam[,fam]] [--changelog-all]
  generate [--root DIR] [--only fam[,fam]] [--verify]
  context <REQ> [--root DIR]
  selftest [--root DIR]
  --version
"""


def main(argv=None) -> int:
    """Parse the command line and run one command. Returns the process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    argv = [str(item) for item in argv]
    if not argv:
        argv = ["check"]
    if argv[0] in ("--version", "-V"):
        print(__version__)
        return 0
    if argv[0] in ("--help", "-h"):
        print(USAGE.rstrip())
        return 0
    if argv[0].startswith("-"):
        command, rest = "check", argv
    else:
        command, rest = argv[0], argv[1:]
    if command not in COMMANDS:
        print("sdd-check: unknown command '%s'" % command)
        print(USAGE.rstrip())
        return 2

    root = Path.cwd()
    only: Optional[List[str]] = None
    changelog_all = False
    verify = False
    positional: List[str] = []
    index = 0
    while index < len(rest):
        arg = rest[index]
        if arg == "--root":
            index += 1
            if index >= len(rest):
                print("sdd-check: --root needs a directory")
                return 2
            root = Path(rest[index])
        elif arg.startswith("--root="):
            root = Path(arg.split("=", 1)[1])
        elif arg == "--only":
            index += 1
            if index >= len(rest):
                print("sdd-check: --only needs a family list")
                return 2
            only = [name.strip() for name in rest[index].split(",") if name.strip()]
        elif arg.startswith("--only="):
            only = [name.strip() for name in arg.split("=", 1)[1].split(",") if name.strip()]
        elif arg == "--changelog-all":
            changelog_all = True
        elif arg == "--verify":
            verify = True
        elif arg.startswith("-"):
            print("sdd-check: unknown option '%s'" % arg)
            return 2
        else:
            positional.append(arg)
        index += 1

    if command == "generate":
        return run_generate(root, only, verify)
    if command == "context":
        if len(positional) != 1:
            print("sdd-check: context takes exactly one requirement id")
            return 2
        return run_context(root, positional[0])
    if command == "selftest":
        return run_selftest(root)
    if positional:
        print("sdd-check: check takes no positional argument ('%s')" % positional[0])
        return 2
    report = run_check(root, only, changelog_all)
    print(report.render(root))
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())

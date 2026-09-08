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

DEFAULT_TEST_GLOBS = (
    "*_test.go",
    "test_*.py",
    "*_test.py",
    "*Test.php",
    "*.test.ts",
    "*.spec.ts",
    "*_test.rs",
)

#: Directories `tree-to-map` never walks.
PRUNED_DIRS = (".git", "vendor", "node_modules", "__pycache__", ".venv", "venv", "docs")

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
        body = [line for line in collected]
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
        if text.startswith("#"):
            return None
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
        end = text.rfind("]")
        if end == -1:
            self.fail("an unterminated inline list", lineno)
        body = text[1:end]
        items: List[str] = []
        current = ""
        quote = ""
        for char in body:
            if quote:
                if char == quote:
                    quote = ""
                else:
                    current += char
                continue
            if char in "\"'":
                quote = char
                continue
            if char == ",":
                if current.strip():
                    items.append(current.strip())
                current = ""
                continue
            if char == "{":
                self.fail("a flow mapping is not supported", lineno)
            current += char
        if current.strip():
            items.append(current.strip())
        out: List[object] = []
        for token in items:
            if token[0] == "&":
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

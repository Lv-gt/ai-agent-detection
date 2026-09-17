from __future__ import annotations

import re

from .util import ROOT, read_json


_WORD = r"A-Za-z0-9_"


class Registry:
    """Load the four-channel coding-agent rule registry.

    Each Agent has exactly four maintained fields:
    author_patterns, text_patterns, branch_patterns, and label_patterns.
    """

    def __init__(self, snapshot=None):
        if snapshot is None:
            snapshot = {
                "config": read_json(ROOT / "config/detection_config.json"),
                "agents": read_json(ROOT / "config/rules/agents.json"),
            }
        self.snapshot = snapshot
        self.config = snapshot["config"]
        self.rules = snapshot["agents"]
        if self.rules.get("schema_version") != "2.0":
            raise ValueError("Unsupported agent rule schema")

        self.catalog = {}
        self.author_patterns = []
        self.text_patterns = []
        self.metadata_patterns = {"branches": [], "labels": []}

        for entry in self.rules.get("tools", []):
            tool = entry["name"].strip()
            if not tool:
                raise ValueError("Empty tool name in rule registry")
            if tool in self.catalog:
                raise ValueError("Duplicate tool in rule registry: " + tool)

            normalized = {
                "name": tool,
                "author_patterns": list(dict.fromkeys(entry.get("author_patterns", []))),
                "text_patterns": list(dict.fromkeys(entry.get("text_patterns", []))),
                "branch_patterns": list(dict.fromkeys(entry.get("branch_patterns", []))),
                "label_patterns": list(dict.fromkeys(entry.get("label_patterns", []))),
            }
            self.catalog[tool] = normalized

            for raw in normalized["author_patterns"]:
                self.author_patterns.append((self._compile_fragment(raw), tool, raw))
            for raw in normalized["text_patterns"]:
                self.text_patterns.append((self._compile_fragment(raw), tool, raw))
            for raw in normalized["branch_patterns"]:
                self.metadata_patterns["branches"].append((re.compile(raw, re.I), tool, raw))
            for raw in normalized["label_patterns"]:
                self.metadata_patterns["labels"].append((re.compile(raw, re.I), tool, raw))

    @staticmethod
    def _compile_fragment(raw):
        """Compile a regex fragment with token boundaries around the fragment."""
        return re.compile(
            rf"(?<![{_WORD}])(?:{raw})(?![{_WORD}])",
            re.I,
        )

    @staticmethod
    def render_identity(*, login="", name="", email=""):
        """Normalize GitHub/Git author fields into one auditable identity string."""
        return f"{(login or '').strip()} | {(name or '').strip()} <{(email or '').strip()}>"

    @staticmethod
    def _sorted(matches):
        return sorted(matches, key=lambda x: (x[0], x[2], x[3], x[1]))

    def author_matches(self, identity):
        """Return every configured author pattern that matches the identity."""
        hits = []
        for pattern, tool, raw in self.author_patterns:
            for match in pattern.finditer(identity or ""):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

    def text_matches(self, value):
        """Return every configured text pattern that matches the text."""
        hits = []
        for pattern, tool, raw in self.text_patterns:
            for match in pattern.finditer(value or ""):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

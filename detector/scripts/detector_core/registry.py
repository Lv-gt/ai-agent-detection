from __future__ import annotations

import re

from .util import ROOT, read_json


_WORD = r"A-Za-z0-9_"
_TEXT_BREAK = re.compile(r"(?:[.!?;](?=[ \t]|$)|[。！？；])")


class Registry:
    """Load the coding-agent registry and global attribution grammar."""

    def __init__(self, snapshot=None):
        self.snapshot = snapshot if snapshot is not None else read_json(ROOT / "config/rules/agents.json")
        self.rules = self.snapshot

        grammar = self.rules.get("attribution_grammar") or {}
        self.grammar = {
            "verb_patterns": list(grammar.get("verb_patterns", [])),
            "connectors": list(grammar.get("connectors", [])),
            "hyphenated_prefixes": list(grammar.get("hyphenated_prefixes", [])),
        }
        self.attribution_prefix = self._compile_attribution_prefix()

        self.catalog = {}
        self.author_patterns = []
        self.text_patterns = []
        self.metadata_patterns = {"branches": [], "labels": []}
        self.raw_message_patterns = []

        for entry in self.rules.get("agents", []):
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
                "raw_message_signatures": list(dict.fromkeys(entry.get("raw_message_signatures", []))),
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
            for raw in normalized["raw_message_signatures"]:
                self.raw_message_patterns.append((re.compile(raw, re.I), tool, raw))

        self._validate_counts()

    def _compile_attribution_prefix(self):
        verbs = self.grammar["verb_patterns"]
        connectors = self.grammar["connectors"]
        special = self.grammar["hyphenated_prefixes"]
        if not verbs or not connectors or not special:
            raise ValueError("Incomplete attribution grammar")

        ordinary = rf"(?:{'|'.join(verbs)})[ \t]+(?:{'|'.join(map(re.escape, connectors))})"
        hyphenated = rf"(?:{'|'.join(special)})"
        return re.compile(
            rf"(?<![{_WORD}])(?:{ordinary}|{hyphenated})(?=[ \t:]|$)",
            re.I,
        )

    def _validate_counts(self):
        declared = self.rules.get("counts") or {}
        actual = {
            "agents": len(self.catalog),
            "author": len(self.author_patterns),
            "text": len(self.text_patterns),
            "author_text_overlap": sum(
                len(set(entry["author_patterns"]) & set(entry["text_patterns"]))
                for entry in self.catalog.values()
            ),
            "branch": len(self.metadata_patterns["branches"]),
            "label": len(self.metadata_patterns["labels"]),
            "raw_message_signature": len(self.raw_message_patterns),
        }
        actual["complete_executable_inventory"] = (
            actual["author"] + actual["text"] + actual["branch"] + actual["label"]
            + actual["raw_message_signature"]
        )
        for key, value in actual.items():
            if key in declared and declared[key] != value:
                raise ValueError(f"Rule count mismatch for {key}: declared={declared[key]} actual={value}")
        self.counts = actual

    @staticmethod
    def _compile_fragment(raw):
        """Compile one identity fragment without domain, hyphen-word or Unicode collisions."""
        return re.compile(rf"(?<![\w@.\-])(?:{raw})(?![\w@]|[.\-]\w)", re.I)

    @staticmethod
    def render_identity(*, login="", name="", email=""):
        """Render GitHub/Git author fields into one auditable identity string."""
        return f"{(login or '').strip()} | {(name or '').strip()} <{(email or '').strip()}>"

    @staticmethod
    def _sorted(matches):
        return sorted(matches, key=lambda x: (x[0], x[2], x[3], x[1]))

    def author_matches(self, value):
        """Scan the rendered native-author identity with the Author-side table."""
        hits = []
        value = value or ""
        for pattern, tool, raw in self.author_patterns:
            for match in pattern.finditer(value):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

    def text_matches(self, value):
        """Search one bounded attribution segment with text-side evidence only."""
        hits = []
        for pattern, tool, raw in self.text_patterns:
            for match in pattern.finditer(value or ""):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

    def attribution_targets(self, line):
        """Yield the bounded text segment following each attribution prefix."""
        line = line or ""
        for prefix in self.attribution_prefix.finditer(line):
            pos = prefix.end()
            target = line[pos:]
            boundary = _TEXT_BREAK.search(target)
            if boundary is not None:
                target = target[:boundary.start()]
            if target:
                yield target, prefix.group(0), pos

    def raw_message_matches(self, value):
        """Return configured structured raw-message signatures."""
        hits = []
        for pattern, tool, raw in self.raw_message_patterns:
            for match in pattern.finditer(value or ""):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

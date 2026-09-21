from __future__ import annotations

import re

from .util import ROOT, read_json


_WORD = r"A-Za-z0-9_"


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
            "bridge_patterns": list(grammar.get("bridge_patterns", [])),
        }
        self.attribution_prefix = self._compile_attribution_prefix()
        self.bridge_pattern = self._compile_bridge_pattern()

        self.catalog = {}
        self.identity_patterns = []
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
                "identity_patterns": list(dict.fromkeys(entry.get("identity_patterns", []))),
                "branch_patterns": list(dict.fromkeys(entry.get("branch_patterns", []))),
                "label_patterns": list(dict.fromkeys(entry.get("label_patterns", []))),
                "raw_message_signatures": list(dict.fromkeys(entry.get("raw_message_signatures", []))),
            }
            self.catalog[tool] = normalized

            for raw in normalized["identity_patterns"]:
                self.identity_patterns.append((self._compile_fragment(raw), tool, raw))
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

    def _compile_bridge_pattern(self):
        bridges = self.grammar["bridge_patterns"]
        if not bridges:
            return None
        return re.compile(rf"(?:{'|'.join(bridges)})(?![{_WORD}])", re.I)

    def _validate_counts(self):
        declared = self.rules.get("counts") or {}
        actual = {
            "agents": len(self.catalog),
            "identity": len(self.identity_patterns),
            "branch": len(self.metadata_patterns["branches"]),
            "label": len(self.metadata_patterns["labels"]),
            "raw_message_signature": len(self.raw_message_patterns),
        }
        actual["agent_specific"] = actual["identity"] + actual["branch"] + actual["label"]
        actual["complete_executable_inventory"] = actual["agent_specific"] + actual["raw_message_signature"]
        for key, value in actual.items():
            if key in declared and declared[key] != value:
                raise ValueError(f"Rule count mismatch for {key}: declared={declared[key]} actual={value}")
        self.counts = actual

    @staticmethod
    def _compile_fragment(raw):
        """Compile one shared Identity regex with ASCII token boundaries."""
        return re.compile(rf"(?<![{_WORD}])(?:{raw})(?![{_WORD}])", re.I)

    @staticmethod
    def render_identity(*, login="", name="", email=""):
        """Render GitHub/Git author fields into one auditable identity string."""
        return f"{(login or '').strip()} | {(name or '').strip()} <{(email or '').strip()}>"

    @staticmethod
    def _sorted(matches):
        return sorted(matches, key=lambda x: (x[0], x[2], x[3], x[1]))

    def identity_matches(self, value, *, start_only=False):
        """Match the same Identity table against native identities or an extracted target."""
        hits = []
        value = value or ""
        for pattern, tool, raw in self.identity_patterns:
            if start_only:
                match = pattern.match(value)
                if match:
                    hits.append((tool, raw, match.start(), match.end()))
            else:
                for match in pattern.finditer(value):
                    hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

    def attribution_targets(self, line):
        """Yield (target, prefix, target_start) for every attribution prefix in one line.

        The optional colon and whitespace are matcher syntax, not rule-registry fields.
        A configured bridge is consumed before the target is defined.
        """
        line = line or ""
        for prefix in self.attribution_prefix.finditer(line):
            pos = prefix.end()
            separator = re.match(r"[ \t]*:?[ \t]*", line[pos:])
            pos += separator.end()

            if self.bridge_pattern is not None:
                bridge = self.bridge_pattern.match(line, pos)
                if bridge:
                    pos = bridge.end()
                    spaces = re.match(r"[ \t]*", line[pos:])
                    pos += spaces.end()

            target = line[pos:]
            if target:
                yield target, prefix.group(0), pos

    def raw_message_matches(self, value):
        """Return configured structured raw-message signatures."""
        hits = []
        for pattern, tool, raw in self.raw_message_patterns:
            for match in pattern.finditer(value or ""):
                hits.append((tool, raw, match.start(), match.end()))
        return self._sorted(hits)

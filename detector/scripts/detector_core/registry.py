from __future__ import annotations

import re
from collections import defaultdict

from .util import ROOT, read_json


class Registry:
    """Load coding-agent rules and ordinary automation-account patterns."""

    def __init__(self, snapshot=None):
        if snapshot is None:
            snapshot = {
                "config": read_json(ROOT / "config/detection_config.json"),
                "agents": read_json(ROOT / "config/rules/agents.json"),
                "automation": read_json(ROOT / "config/rules/automation_identities.json"),
            }
        self.snapshot = snapshot
        self.config = snapshot["config"]
        self.rules = snapshot["agents"]
        self.automation_rules = snapshot["automation"]
        if self.rules.get("schema_version") != "1.0":
            raise ValueError("Unsupported agent rule schema")
        if self.automation_rules.get("schema_version") != "1.0":
            raise ValueError("Unsupported automation rule schema")

        self.catalog = {}
        self.aliases = {}
        self.email_map = defaultdict(set)
        self.login_map = defaultdict(set)
        self.name_map = defaultdict(set)
        self.metadata_patterns = {"branches": [], "labels": []}
        self.task_links = []

        for entry in self.rules.get("tools", []):
            tool = entry["name"].strip()
            if not tool:
                raise ValueError("Empty tool name in rule registry")
            if tool in self.catalog:
                raise ValueError("Duplicate tool in rule registry: " + tool)

            normalized = {
                "name": tool,
                "aliases": list(dict.fromkeys(entry.get("aliases", [tool]))),
                "identity": {
                    "logins": list(dict.fromkeys(entry.get("identity", {}).get("logins", []))),
                    "emails": list(dict.fromkeys(entry.get("identity", {}).get("emails", []))),
                    "names": list(dict.fromkeys(entry.get("identity", {}).get("names", []))),
                },
                "branches": list(dict.fromkeys(entry.get("branches", []))),
                "labels": list(dict.fromkeys(entry.get("labels", []))),
                "task_links": list(entry.get("task_links", [])),
                "source_refs": list(dict.fromkeys(entry.get("source_refs", []))),
            }
            self.catalog[tool] = normalized

            for alias in normalized["aliases"]:
                folded = alias.strip().casefold()
                if not folded:
                    continue
                previous = self.aliases.get(folded)
                if previous is not None and previous != tool:
                    raise ValueError("Ambiguous enabled tool alias: " + alias)
                self.aliases[folded] = tool

            identity = normalized["identity"]
            for login in identity["logins"]:
                self.login_map[self.login_key(login)].add(tool)
            for email in identity["emails"]:
                self.email_map[email.strip().casefold()].add(tool)
            for name in identity["names"]:
                self.name_map[name.strip().casefold()].add(tool)

            for pattern in normalized["branches"]:
                self.metadata_patterns["branches"].append((re.compile(pattern), tool, pattern))
            for pattern in normalized["labels"]:
                self.metadata_patterns["labels"].append((re.compile(pattern), tool, pattern))
            for spec in normalized["task_links"]:
                self.task_links.append({"tool": tool, **spec})

        aliases = sorted(self.aliases, key=lambda x: (-len(x), x))
        self.alias_pattern = re.compile(
            r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(a) for a in aliases) + r")(?![A-Za-z0-9_])",
            re.I,
        ) if aliases else re.compile(r"(?!)")
        self.automation_patterns = [
            re.compile(pattern, re.I) for pattern in self.automation_rules.get("patterns", [])
        ]

    @staticmethod
    def login_key(value):
        value = (value or "").strip().casefold()
        # GitHub App/bot logins often expose a [bot] suffix. Agent identity
        # rules are matched first so coding-agent bots are not discarded.
        return value[:-5] if value.endswith("[bot]") else value

    def identity(self, *, login="", email="", name="", attribution=False):
        hits = set()
        hits.update(self.email_map.get((email or "").strip().casefold(), ()))
        hits.update(self.login_map.get(self.login_key(login), ()))
        folded = (name or "").strip().casefold()
        hits.update(self.name_map.get(folded, ()))
        # Co-Authored-By can contain a documented tool name rather than a
        # structured GitHub login/email, so explicit attribution may use aliases.
        if attribution and folded in self.aliases:
            hits.add(self.aliases[folded])
        return sorted(hits)

    def names_in(self, value):
        return [
            (self.aliases[m.group().casefold()], m.start(), m.end())
            for m in self.alias_pattern.finditer(value or "")
        ]

    def automation_classification(self, *, login="", email="", name=""):
        """Classify automation identities after agent identity matching.

        This never suppresses PR/commit body scanning. It only prevents the old
        all-``[bot]`` exclusion strategy from discarding coding-agent evidence.
        """
        rendered = f"{login or ''} | {name or ''} <{email or ''}>"
        if any(pattern.search(rendered) for pattern in self.automation_patterns):
            return "known_non_agent_automation"
        if (login or "").strip().casefold().endswith("[bot]"):
            return "unknown_bot"
        return ""

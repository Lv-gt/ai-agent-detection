from __future__ import annotations

import re
from urllib.parse import urlsplit


COAUTHOR = re.compile(r"^\s*Co-Authored-By\s*:\s*([^<>\r\n]+?)(?:\s*<([^<>\r\n]+)>)?\s*$", re.I)
ATTRIBUTION_PHRASE = re.compile(
    r"(?:generated|implemented|written|created|built)\s+(?:with|by|using)\s*:?\s*$",
    re.I,
)
URL = re.compile(r"https?://[^\s<>\"`]+", re.I)
MARKDOWN_LINK = re.compile(r"\[([^\]\r\n]+)\]\([^\)\r\n]+\)")
INLINE_MARKDOWN_WRAPPERS = (
    re.compile(r"\*\*([^*\r\n]+)\*\*"),
    re.compile(r"__([^_\r\n]+)__"),
    re.compile(r"~~([^~\r\n]+)~~"),
    re.compile(r"`([^`\r\n]+)`"),
    re.compile(r"(?<!\*)\*([^*\r\n]+)\*(?!\*)"),
    re.compile(r"(?<!_)_([^_\r\n]+)_(?!_)"),
)


def attribution_line(line):
    """Normalize only simple inline Markdown for R3 phrase matching.

    Ordinary punctuation, prefixes, underscores, tildes, URLs, email
    addresses, and the stored source text are left untouched.
    """
    line = MARKDOWN_LINK.sub(r"\1", line)
    for wrapper in INLINE_MARKDOWN_WRAPPERS:
        line = wrapper.sub(r"\1", line)
    return line


class EvidenceScanner:
    """Scan explicit coding-agent traces using registered heuristic rules."""

    def __init__(self, registry, emit):
        self.registry = registry
        self.emit_row = emit

    def begin(self, pr):
        self.pr = pr
        self.tools = set()
        self.target_author_tools = set()
        self.other_author_tools = set()
        self.unknown_actor_tools = set()
        self.metadata_tools = set()
        self.categories = set()
        self.evidence_count = 0
        self.automation_actors = {}

    def _relation(self, actor_id):
        target_author = self.pr.get("target_author_id")
        if actor_id is None or target_author is None:
            return "unknown"
        return "target_author" if int(actor_id) == int(target_author) else "other_author"

    def evidence(self, tool, rule, category, source, object_id, field, line, excerpt,
                 actor_id=None, event_time=None, detail=""):
        if not tool:
            return
        relation = self._relation(actor_id)
        self.tools.add(tool)
        self.categories.add(category)
        if category in ("authors", "text"):
            if relation == "target_author":
                self.target_author_tools.add(tool)
            elif relation == "other_author":
                self.other_author_tools.add(tool)
            else:
                self.unknown_actor_tools.add(tool)
        else:
            self.metadata_tools.add(tool)
        self.evidence_count += 1
        self.emit_row({
            "pr_id": self.pr["pr_id"],
            "rule": rule,
            "category": category,
            "tool": tool,
            "source_kind": source,
            "source_object_id": str(object_id),
            "field": field,
            "line": line,
            "excerpt": (excerpt or "")[:240],
            "detail": detail,
            "actor_id": actor_id,
            "actor_relation": relation,
            "event_time": event_time,
            "collected_at": self.pr.get("collected_at_utc"),
        })

    def identity(self, row, source, object_id, login_field, email_field, name_field,
                 actor_id=None, event_time=None):
        found_agent = False
        for field, key in ((login_field, "login"), (email_field, "email"), (name_field, "name")):
            value = row.get(field) or ""
            tools = self.registry.identity(**{key: value})
            if tools:
                found_agent = True
            for tool in tools:
                self.evidence(
                    tool, "R1", "authors", source, object_id, field, 0, value,
                    actor_id=actor_id, event_time=event_time, detail="known_agent_identity",
                )
        # Agent identities have priority. Only identities not recognized as an
        # agent are classified as ordinary/unknown automation accounts.
        if not found_agent:
            classification = self.registry.automation_classification(
                login=row.get(login_field) or "",
                email=row.get(email_field) or "",
                name=row.get(name_field) or "",
            )
            if classification:
                self.automation_actors[(source, str(object_id))] = classification

    @staticmethod
    def attribution_phrase(text, start):
        """Return True when a registered Agent name follows a basic attribution phrase."""
        return bool(ATTRIBUTION_PHRASE.search(text[:start]))

    def _valid_task_link(self, url, spec):
        try:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
                return False
            if parsed.hostname != spec["host"] or not parsed.path.startswith(spec["path_prefix"]):
                return False
            task = parsed.path[len(spec["path_prefix"]):].rstrip("/")
            return bool(re.fullmatch(r"[A-Za-z0-9_-]+", task))
        except ValueError:
            return False

    def text(self, value, source, object_id, field, actor_id=None, event_time=None):
        if not value:
            return
        for line_number, raw_line in enumerate(value.splitlines(), 1):
            raw_text = raw_line.strip()

            # R2 parses the original line so identities are never altered by
            # Markdown normalization (for example, underscores in emails).
            coauthor = COAUTHOR.fullmatch(raw_text)
            if coauthor:
                name = coauthor.group(1).strip()
                email = (coauthor.group(2) or "").strip()
                for tool in self.registry.identity(name=name, email=email, attribution=True):
                    self.evidence(
                        tool, "R2", "authors", source, object_id, field, line_number, raw_line,
                        actor_id=actor_id, event_time=event_time, detail="coauthor_trailer",
                    )
                continue

            # R4 always scans the original line. This preserves task IDs and
            # also detects URLs used as Markdown link targets.
            for url_match in URL.finditer(raw_line):
                url = url_match.group().rstrip(").,;]}")
                for spec in self.registry.task_links:
                    if self._valid_task_link(url, spec):
                        self.evidence(
                            spec["tool"], "R4", "text", source, object_id, field, line_number, raw_line,
                            actor_id=actor_id, event_time=event_time, detail=url,
                        )

            # R3 performs basic phrase matching only. Inline Markdown wrappers
            # are normalized in a temporary copy so presentation does not hide
            # an otherwise explicit attribution phrase. No surrounding semantic
            # context is interpreted, and the original evidence text is kept.
            line = attribution_line(raw_line)
            for tool, start, end in self.registry.names_in(line):
                if self.attribution_phrase(line, start):
                    self.evidence(
                        tool, "R3", "text", source, object_id, field, line_number, raw_line,
                        actor_id=actor_id, event_time=event_time, detail="attribution_phrase",
                    )

    def metadata(self, value, kind, object_id, field, actor_id=None, event_time=None):
        seen = set()
        for pattern, tool, raw_pattern in self.registry.metadata_patterns[kind]:
            if tool not in seen and pattern.search(value or ""):
                seen.add(tool)
                self.evidence(
                    tool, "R5", kind, kind, object_id, field, 0, value or "",
                    actor_id=actor_id, event_time=event_time, detail=raw_pattern,
                )

    def summary(self):
        known_automation = sum(v == "known_non_agent_automation" for v in self.automation_actors.values())
        unknown_bot = sum(v == "unknown_bot" for v in self.automation_actors.values())
        return {
            "status": "agent_trace_detected" if self.tools else "no_trace_detected",
            "tools": sorted(self.tools),
            "categories": sorted(self.categories),
            "target_author_agent_trace": bool(self.target_author_tools),
            "target_author_tools": sorted(self.target_author_tools),
            "other_actor_agent_trace": bool(self.other_author_tools),
            "other_actor_tools": sorted(self.other_author_tools),
            "unknown_actor_agent_trace": bool(self.unknown_actor_tools),
            "unknown_actor_tools": sorted(self.unknown_actor_tools),
            "metadata_agent_trace": bool(self.metadata_tools),
            "metadata_tools": sorted(self.metadata_tools),
            "known_non_agent_automation_actor_count": known_automation,
            "unknown_bot_actor_count": unknown_bot,
            "evidence_count": self.evidence_count,
        }

from __future__ import annotations

import re


# One global, deterministic attribution grammar shared by every Agent.
# It intentionally does not interpret negation, checklist state, code-block state,
# or Agent-specific semantic context.
ATTRIBUTION_PHRASE = re.compile(
    r"(?:"
    r"(?:generated|implemented|written|created|built|developed|coded|authored|made|produced|assisted)"
    r"\s+(?:with|by|using|via|with\s+(?:the\s+)?(?:help|assistance)\s+(?:of|from))\s*:?[ \t]*"
    r"|co-authored-by\s*:\s*"
    r")$",
    re.I,
)

# Minimal Markdown normalization.  Preserve the URL; only rewrite the common
# [visible text](URL) representation into visible text (URL).  The raw source
# text is still preserved in emitted evidence.
MARKDOWN_LINK = re.compile(r"\[([^\]\r\n]+)\]\(([^\)\r\n]+)\)")


def normalize_text(line: str) -> str:
    """Apply only representation-level normalization used before text matching."""
    return MARKDOWN_LINK.sub(r"\1 (\2)", line)


class EvidenceScanner:
    """Scan explicit coding-agent traces using the four maintained channels."""

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
        })

    def identity(self, row, source, object_id, login_field, email_field, name_field,
                 actor_id=None, event_time=None):
        """Apply the same author-pattern list to PR authors and commit authors."""
        login = row.get(login_field) or ""
        email = row.get(email_field) or ""
        name = row.get(name_field) or ""
        rendered = self.registry.render_identity(login=login, name=name, email=email)
        hits = self.registry.author_matches(rendered)
        for tool, raw_pattern, _start, _end in hits:
            self.evidence(
                tool, "author_identity", "authors", source, object_id, "author_identity", 0, rendered,
                actor_id=actor_id, event_time=event_time,
                detail=f"author_pattern:{raw_pattern}",
            )

    @staticmethod
    def attribution_phrase(text, start):
        """Return True when an Agent pattern immediately follows the global grammar."""
        return bool(ATTRIBUTION_PHRASE.search(text[:start]))

    def text(self, value, source, object_id, field, actor_id=None, event_time=None):
        if not value:
            return
        for line_number, raw_line in enumerate(value.splitlines(), 1):
            line = normalize_text(raw_line)
            for tool, raw_pattern, start, _end in self.registry.text_matches(line):
                if self.attribution_phrase(line, start):
                    # Emit every matching configured pattern.  This is deliberate:
                    # the next audit needs exact per-pattern counts and overlaps.
                    self.evidence(
                        tool, "text_attribution", "text", source, object_id, field, line_number, raw_line,
                        actor_id=actor_id, event_time=event_time,
                        detail=f"text_pattern:{raw_pattern}",
                    )

    def metadata(self, value, kind, object_id, field, actor_id=None, event_time=None):
        rule = "branch" if kind == "branches" else "label"
        detail_prefix = "branch_pattern" if kind == "branches" else "label_pattern"
        for pattern, tool, raw_pattern in self.registry.metadata_patterns[kind]:
            if pattern.search(value or ""):
                # Emit every matching configured pattern for exact redundancy auditing.
                self.evidence(
                    tool, rule, kind, kind, object_id, field, 0, value or "",
                    actor_id=actor_id, event_time=event_time,
                    detail=f"{detail_prefix}:{raw_pattern}",
                )

    def summary(self):
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
            "evidence_count": self.evidence_count,
        }

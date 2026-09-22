from __future__ import annotations

import re


# Representation-level normalization only. The raw source text remains in evidence.
MARKDOWN_LINK = re.compile(r"\[([^\]\r\n]+)\]\(([^\)\r\n]+)\)")
TARGET_EMPHASIS = re.compile(
    r"(?<!\w)(?P<marker>\*{1,3}|_{1,3})(?P<text>.+?)(?P=marker)"
    r"(?!\w)"
)
INLINE_CODE = re.compile(r"`+[^`\r\n]*`+")


def normalize_text(line: str) -> str:
    return MARKDOWN_LINK.sub(r"\1 (\2)", line)


def normalize_target(target: str) -> str:
    """Normalize emphasis and mask complete Markdown inline-code spans."""
    target = TARGET_EMPHASIS.sub(r"\g<text>", target or "")
    return INLINE_CODE.sub(" ", target)


class EvidenceScanner:
    """Scan coding-agent traces through Identity, Branch and Label evidence."""

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
        if category == "identity":
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
        """Scan one PR/commit author identity with the Author-side table."""
        rendered = self.registry.render_identity(
            login=row.get(login_field) or "",
            name=row.get(name_field) or "",
            email=row.get(email_field) or "",
        )
        for tool, raw_pattern, _start, _end in self.registry.author_matches(rendered):
            self.evidence(
                tool, "identity", "identity", source, object_id, "author_identity", 0, rendered,
                actor_id=actor_id, event_time=event_time,
                detail=f"author_pattern:{raw_pattern}",
            )

    @staticmethod
    def _line_number(value, start):
        return (value or "").count("\n", 0, start) + 1

    @staticmethod
    def _line_excerpt(value, start):
        value = value or ""
        left = value.rfind("\n", 0, start) + 1
        right = value.find("\n", start)
        if right < 0:
            right = len(value)
        return value[left:right]

    def text(self, value, source, object_id, field, actor_id=None, event_time=None):
        """Scan PR body / commit message attribution declarations.

        Structured raw-message signatures are additionally checked for commit messages.
        All accepted text mechanisms are reported under the Identity evidence category.
        """
        if not value:
            return

        for line_number, raw_line in enumerate(value.splitlines(), 1):
            line = normalize_text(raw_line)
            for target, prefix, _target_start in self.registry.attribution_targets(line):
                normalized_target = normalize_target(target)
                for tool, raw_pattern, _start, _end in self.registry.text_matches(normalized_target):
                    self.evidence(
                        tool, "attribution", "identity", source, object_id, field, line_number, raw_line,
                        actor_id=actor_id, event_time=event_time,
                        detail=f"text_pattern:{raw_pattern};prefix:{prefix}",
                    )

        if source == "commit" and field == "message":
            for tool, raw_pattern, start, _end in self.registry.raw_message_matches(value):
                self.evidence(
                    tool, "raw_message_signature", "identity", source, object_id, field,
                    self._line_number(value, start), self._line_excerpt(value, start),
                    actor_id=actor_id, event_time=event_time,
                    detail=f"raw_message_signature:{raw_pattern}",
                )

    def metadata(self, value, kind, object_id, field, actor_id=None, event_time=None):
        category = "branch" if kind == "branches" else "label"
        detail_prefix = "branch_pattern" if kind == "branches" else "label_pattern"
        for pattern, tool, raw_pattern in self.registry.metadata_patterns[kind]:
            if pattern.search(value or ""):
                self.evidence(
                    tool, category, category, kind, object_id, field, 0, value or "",
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

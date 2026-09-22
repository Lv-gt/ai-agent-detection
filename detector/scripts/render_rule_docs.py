from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
rules = json.loads((ROOT / "config/rules/agents.json").read_text(encoding="utf-8"))
counts = rules["counts"]
lines = [
    "# Agent 规则清单",
    "",
    "> 本文档用于人工查看。机器检测只读取 `config/rules/agents.json`。Author 与正文规则允许重叠。",
    "",
    f"- Agent：**{counts['agents']}**",
    f"- Author patterns：**{counts['author']}**",
    f"- Text attribution patterns：**{counts['text']}**",
    f"- Author/Text 重叠：**{counts['author_text_overlap']}**",
    f"- Branch patterns：**{counts['branch']}**",
    f"- Label patterns：**{counts['label']}**",
    f"- Raw message signatures：**{counts['raw_message_signature']}**",
    f"- 总可执行规则实例：**{counts['complete_executable_inventory']}**",
    "",
]
sections = (
    ("author_patterns", "Author"),
    ("text_patterns", "Text attribution"),
    ("branch_patterns", "Branch"),
    ("label_patterns", "Label"),
    ("raw_message_signatures", "Raw message signature"),
)
for agent in rules["agents"]:
    lines += [f"## {agent['name']}", ""]
    for field, label in sections:
        patterns = agent[field]
        if not patterns:
            continue
        lines += [f"**{label}**", "", "```regex", *patterns, "```", ""]
(ROOT / "AGENT_RULES.md").write_text("\n".join(lines), encoding="utf-8")

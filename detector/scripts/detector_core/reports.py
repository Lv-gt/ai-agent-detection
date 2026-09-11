import csv
import gzip
import json
import os
import sqlite3
from pathlib import Path

from .input_db import source_stamp
from .util import readonly, read_json, write_json, utc_now


def progress(connection, label):
    # Keep long SQLite operations interruptible and observable.
    connection.set_progress_handler(lambda: 0, 100000)


def lines(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def audit_database(path, context):
    with readonly(path) as c:
        progress(c, "Output audit")
        integrity = c.execute("PRAGMA quick_check").fetchone()[0]
        prs = c.execute("SELECT COUNT(*) FROM pr_results").fetchone()[0]
        issues = {}
        checks = {
            "positive_without_evidence": (
                "SELECT COUNT(*) FROM pr_results p "
                "WHERE status='agent_trace_detected' "
                "AND NOT EXISTS(SELECT 1 FROM evidence e WHERE e.pr_id=p.pr_id)"
            ),
            "evidence_for_nonpositive": (
                "SELECT COUNT(*) FROM evidence e JOIN pr_results p USING(pr_id) "
                "WHERE p.status!='agent_trace_detected'"
            ),
            "orphan_evidence": (
                "SELECT COUNT(*) FROM evidence e LEFT JOIN pr_results p USING(pr_id) WHERE p.pr_id IS NULL"
            ),
            "tool_missing_from_result": (
                "SELECT COUNT(*) FROM evidence e JOIN pr_results p USING(pr_id) "
                "WHERE NOT EXISTS(SELECT 1 FROM json_each(p.payload,'$.tools') j WHERE j.value=e.tool)"
            ),
            "result_tool_without_evidence": (
                "SELECT COUNT(*) FROM pr_results p,json_each(p.payload,'$.tools') j "
                "WHERE NOT EXISTS(SELECT 1 FROM evidence e WHERE e.pr_id=p.pr_id AND e.tool=j.value)"
            ),
            "evidence_count_mismatch": (
                "SELECT COUNT(*) FROM pr_results p "
                "LEFT JOIN (SELECT pr_id,COUNT(*) n FROM evidence GROUP BY pr_id) e USING(pr_id) "
                "WHERE json_extract(p.payload,'$.evidence_count') != COALESCE(e.n,0)"
            ),
            "invalid_status": (
                "SELECT COUNT(*) FROM pr_results "
                "WHERE status NOT IN ('agent_trace_detected','no_trace_detected','unavailable')"
            ),
        }
        for name, sql in checks.items():
            count = c.execute(sql).fetchone()[0]
            if count:
                issues[name] = count
        if prs != context["target_count"]:
            issues["pr_count"] = prs
        return {
            "complete": integrity == "ok" and not issues,
            "integrity_check": integrity,
            "scope": context["scope"],
            "pr_count": prs,
            "issues": issues,
            "pr_status_counts": dict(c.execute("SELECT status,COUNT(*) FROM pr_results GROUP BY status")),
            "created_at": utc_now(),
        }


def merge(output):
    output = Path(output)
    context = read_json(output / "run_context.json")
    if source_stamp(context["source"]["path"]) != context["source"]:
        raise ValueError("Input changed before merge")

    temporary = output / "detection.sqlite3.building"
    temporary.unlink(missing_ok=True)
    c = sqlite3.connect(temporary, uri=True)
    progress(c, "Output merge")
    try:
        c.executescript("""
        CREATE TABLE pr_results(
            pr_id INTEGER PRIMARY KEY,
            repo_id INTEGER,
            target_author_id INTEGER,
            status TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE evidence(
            id INTEGER PRIMARY KEY,
            pr_id INTEGER NOT NULL,
            tool TEXT NOT NULL,
            rule TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE run_info(payload TEXT NOT NULL);
        """)
        c.execute("INSERT INTO run_info VALUES(?)", (json.dumps(context, ensure_ascii=False),))

        for i, limits in enumerate(context["ranges"]):
            prefix = output / "shards" / f"{i:07d}"
            marker = read_json(str(prefix) + ".done.json")
            count = evidence_count = 0
            for row in lines(str(prefix) + ".results.jsonl"):
                if not limits[0] <= row["pr_id"] <= limits[1]:
                    raise ValueError("Shard PR outside assigned range")
                c.execute(
                    "INSERT INTO pr_results VALUES(?,?,?,?,?)",
                    (
                        row["pr_id"], row["repo_id"], row["target_author_id"], row["status"],
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
                count += 1
            for row in lines(str(prefix) + ".evidence.jsonl"):
                c.execute(
                    "INSERT INTO evidence(pr_id,tool,rule,payload) VALUES(?,?,?,?)",
                    (row["pr_id"], row["tool"], row["rule"], json.dumps(row, ensure_ascii=False)),
                )
                evidence_count += 1
            if count != limits[2] or count != marker["results"] or evidence_count != marker["evidence"]:
                raise ValueError("Shard row count mismatch")
            c.commit()

        c.execute("CREATE INDEX idx_evidence_pr ON evidence(pr_id)")
        c.execute("CREATE INDEX idx_evidence_rule_tool ON evidence(rule,tool)")
        c.commit()
    finally:
        c.close()

    report = audit_database(temporary, context)
    write_json(output / "audit_build.json", report)
    if not report["complete"]:
        raise ValueError("Result audit failed; existing formal database was not replaced")
    if source_stamp(context["source"]["path"]) != context["source"]:
        raise ValueError("Source changed during merge")
    os.replace(temporary, output / "detection.sqlite3")
    write_json(output / "audit.json", report)


def audit(output):
    output = Path(output)
    report = audit_database(output / "detection.sqlite3", read_json(output / "run_context.json"))
    write_json(output / "audit.json", report)
    if not report["complete"]:
        raise ValueError("Result audit failed")
    return report


def export(output):
    output = Path(output)
    report = audit(output)
    dest = output / "exports"
    dest.mkdir(exist_ok=True)

    list_fields = {
        "tools", "categories", "target_author_tools", "other_actor_tools",
        "unknown_actor_tools", "metadata_tools",
    }
    fields = [
        "pr_id", "repo_id", "pr_number", "target_author_id", "collection_status", "status", "tools",
        "target_author_agent_trace", "target_author_tools",
        "other_actor_agent_trace", "other_actor_tools",
        "unknown_actor_agent_trace", "unknown_actor_tools",
        "metadata_agent_trace", "metadata_tools", "categories",
        "known_non_agent_automation_actor_count", "unknown_bot_actor_count", "evidence_count",
        "commit_total_count", "commit_observed_count", "commit_observation_status",
        "label_observed_count", "missing_commit_author_email_count",
        "author_identity_missing", "empty_pr_body", "created_at", "collected_at_utc", "unavailable_reason",
    ]

    with readonly(output / "detection.sqlite3") as c:
        with gzip.open(dest / "pr_labels.csv.gz", "wt", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for record in c.execute("SELECT payload FROM pr_results ORDER BY pr_id"):
                row = json.loads(record[0])
                for field in list_fields:
                    if field in row:
                        row[field] = ";".join(row[field])
                writer.writerow(row)

        contributions = [dict(r) for r in c.execute(
            "SELECT rule,tool,COUNT(DISTINCT pr_id) detected_prs "
            "FROM evidence GROUP BY rule,tool ORDER BY rule,tool"
        )]
        write_json(dest / "rule_contributions.json", {
            "overlapping_counts_do_not_sum": True,
            "rows": contributions,
        })

        with gzip.open(dest / "evidence.jsonl.gz", "wt", encoding="utf-8") as handle:
            for record in c.execute("SELECT payload FROM evidence ORDER BY id"):
                handle.write(record[0] + "\n")

    from .registry import Registry
    registry = Registry(read_json(output / "run_context.json")["snapshot"])
    write_json(dest / "tool_catalog.json", list(registry.catalog.values()))
    write_json(dest / "export_summary.json", report)
    return report

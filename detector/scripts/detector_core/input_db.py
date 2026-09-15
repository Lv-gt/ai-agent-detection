from pathlib import Path

from .util import readonly, file_stamp


REQUIRED = {
    "metadata": "key value",
    "target_prs": "pr_id repo_id pr_number expected_author_id collection_status commit_total_count commit_observed_count commit_observation_status label_observed_count",
    "pr_details": "pr_id repo_id pr_number author_database_id author_login author_name author_email body_markdown head_ref_name created_at collected_at_utc",
    "pr_commits": "pr_id ordinal sha message author_name author_email author_user_login author_user_database_id committed_date",
    "pr_labels": "pr_id ordinal name",
}

ALLOWED_COLLECTION_STATUSES = {
    "completed", "pending", "retryable_failure", "terminal_unavailable", "identity_conflict"
}


def resolve_input(input_path):
    path = Path(input_path).resolve()
    return path / "pr_agent_inputs.sqlite3" if path.is_dir() else path


def source_stamp(path):
    path = Path(path)
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError(
                "Input has an active journal. Stop collection and use a consistent SQLite database copy: "
                + str(sidecar)
            )
    return file_stamp(path)


def preflight(input_path, config, deep_check=False):
    path = resolve_input(input_path)
    if not path.is_file():
        raise ValueError("Input database not found: " + str(path))
    before = source_stamp(path)
    with readonly(path) as c:
        for table, fields in REQUIRED.items():
            columns = {r["name"] for r in c.execute("PRAGMA table_info(" + table + ")")}
            missing = set(fields.split()) - columns
            if missing:
                raise ValueError(f"Missing input fields in {table}: {sorted(missing)}")
        integrity = "not_run"
        if deep_check:
            integrity = c.execute("PRAGMA quick_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError("Input database quick_check: " + integrity)
        target_count = c.execute("SELECT COUNT(*) FROM target_prs").fetchone()[0]
        if target_count < 1:
            raise ValueError("No target PRs in input database")
        status_counts = dict(
            c.execute("SELECT collection_status,COUNT(*) FROM target_prs GROUP BY collection_status")
        )
        unknown = set(status_counts) - ALLOWED_COLLECTION_STATUSES
        if unknown:
            raise ValueError("Unknown collection status values: " + ", ".join(sorted(unknown)))
    if source_stamp(path) != before:
        raise ValueError("Input changed during preflight")
    return {
        "source": before,
        "target_count": target_count,
        "collection_status_counts": status_counts,
        "input_integrity": integrity,
        "deep_check": deep_check,
    }


def ranges(path, shard_size, sample_size=None):
    result, batch = [], []
    with readonly(path) as c:
        if sample_size is not None:
            if sample_size < 1:
                raise ValueError("sample_size must be positive")
            selected = [r[0] for r in c.execute(
                "SELECT pr_id FROM target_prs WHERE collection_status='completed' ORDER BY pr_id LIMIT ?",
                (sample_size,),
            )]
            if not selected:
                raise ValueError("No completed PRs available for sampling")
            return [[pr_id, pr_id, 1] for pr_id in selected]
        for row in c.execute("SELECT pr_id,collection_status FROM target_prs ORDER BY pr_id"):
            if row["collection_status"] not in ALLOWED_COLLECTION_STATUSES:
                raise ValueError("Unknown collection status")
            batch.append(row[0])
            if len(batch) == shard_size:
                result.append([batch[0], batch[-1], len(batch)])
                batch = []
        if batch:
            result.append([batch[0], batch[-1], len(batch)])
    if not result:
        raise ValueError("No eligible PRs for this run")
    return result


def detect_one(c, target, scanner):
    t = dict(target)
    result = {
        "pr_id": t["pr_id"],
        "repo_id": t["repo_id"],
        "pr_number": t["pr_number"],
        "target_author_id": t["expected_author_id"],
        "collection_status": t["collection_status"],
        "status": "unavailable",
        "unavailable_reason": t["collection_status"],
        "tools": [],
        "evidence_count": 0,
        "target_author_agent_trace": False,
        "other_actor_agent_trace": False,
        "unknown_actor_agent_trace": False,
        "metadata_agent_trace": False,
    }
    if t["collection_status"] != "completed":
        return result

    row = c.execute("SELECT * FROM pr_details WHERE pr_id=?", (t["pr_id"],)).fetchone()
    if row is None:
        raise ValueError(f"PR {t['pr_id']}: completed without details")
    d = dict(row)
    if d["repo_id"] != t["repo_id"] or d["pr_number"] != t["pr_number"]:
        raise ValueError("PR numeric repository identity mismatch")
    if d["author_database_id"] is not None and d["author_database_id"] != t["expected_author_id"]:
        raise ValueError("PR numeric author identity mismatch")
    for field in ("body_markdown", "head_ref_name"):
        if d[field] is not None and not isinstance(d[field], str):
            raise ValueError("Invalid non-text PR field: " + field)

    scanner.begin({**t, **d, "target_author_id": t["expected_author_id"]})

    # Improvement over commit-only identity checks: inspect the PR author too.
    pr_actor_id = d["author_database_id"] if d["author_database_id"] is not None else t["expected_author_id"]
    scanner.identity(
        d, "pr", t["pr_id"], "author_login", "author_email", "author_name", pr_actor_id
    )

    # Inspect explicit PR-body traces and task links.
    scanner.text(d["body_markdown"], "pr", t["pr_id"], "body_markdown", pr_actor_id)
    scanner.metadata(d["head_ref_name"], "branches", t["pr_id"], "head_ref_name")

    labels = [
        dict(r) for r in c.execute("SELECT * FROM pr_labels WHERE pr_id=? ORDER BY ordinal", (t["pr_id"],))
    ]
    for label in labels:
        scanner.metadata(label["name"], "labels", label.get("label_node_id", label["ordinal"]), "name")

    count, missing_email = 0, 0
    for row in c.execute("SELECT * FROM pr_commits WHERE pr_id=? ORDER BY ordinal", (t["pr_id"],)):
        commit = dict(row)
        count += 1
        missing_email += not bool(commit["author_email"])
        scanner.identity(
            commit,
            "commit",
            commit["sha"],
            "author_user_login",
            "author_email",
            "author_name",
            commit["author_user_database_id"],
            commit["committed_date"],
        )
        # Co-Authored-By and Generated/Implemented/... attribution phrases are
        # both read from the commit message.
        scanner.text(
            commit["message"],
            "commit",
            commit["sha"],
            "message",
            commit["author_user_database_id"],
            commit["committed_date"],
        )

    result.update(scanner.summary())
    result.update(
        unavailable_reason="",
        commit_observed_count=count,
        commit_total_count=t["commit_total_count"],
        commit_observation_status=t["commit_observation_status"],
        label_observed_count=len(labels),
        missing_commit_author_email_count=missing_email,
        author_identity_missing=d["author_database_id"] is None,
        empty_pr_body=not bool((d["body_markdown"] or "").strip()),
        created_at=d["created_at"],
        collected_at_utc=d["collected_at_utc"],
    )
    return result

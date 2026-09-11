from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def json_line(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


@contextmanager
def readonly(path):
    path = Path(path).resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        yield connection
    finally:
        connection.close()


def file_stamp(path):
    path = Path(path).resolve()
    stat = path.stat()
    return {"path": str(path), "size": stat.st_size, "modified_ns": stat.st_mtime_ns}


def as_int(value, default=0):
    return default if value is None else int(value)


def ensure_separate(input_path, output_dir):
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    # The detector opens the source read-only. Only reject an actual path
    # collision with the formal output database; sibling/nested output
    # directories are otherwise safe and useful for client workflows.
    if (output_dir / "detection.sqlite3").resolve() == input_path:
        raise ValueError("Output detection.sqlite3 would overwrite the input database")

import multiprocessing as mp
import os
import queue
import time
from pathlib import Path

from . import VERSION
from .input_db import preflight, ranges, source_stamp, detect_one, resolve_input
from .matching import EvidenceScanner
from .registry import Registry
from .util import readonly, read_json, write_json, json_line, ensure_separate, utc_now


def worker_init(events):
    events.put(os.getpid())


def work(job):
    path, output, index, limits, snapshot, sampled = job
    output = Path(output)
    prefix = output / "shards" / f"{index:07d}"
    result_path = Path(str(prefix) + ".results.jsonl")
    evidence_path = Path(str(prefix) + ".evidence.jsonl")
    registry = Registry(snapshot)
    count = evidence_count = 0
    with readonly(path) as c, open(str(result_path) + ".tmp", "w", encoding="utf-8") as results, open(str(evidence_path) + ".tmp", "w", encoding="utf-8") as evidence:
        def emit(row):
            nonlocal evidence_count
            evidence.write(json_line(row))
            evidence_count += 1
        scanner = EvidenceScanner(registry, emit)
        sql = "SELECT * FROM target_prs WHERE pr_id BETWEEN ? AND ?"
        if sampled:
            sql += " AND collection_status='completed'"
        for target in c.execute(sql + " ORDER BY pr_id", limits[:2]):
            results.write(json_line(detect_one(c, target, scanner)))
            count += 1
    if count != limits[2]:
        raise ValueError("Shard target count changed")
    os.replace(str(result_path) + ".tmp", result_path)
    os.replace(str(evidence_path) + ".tmp", evidence_path)
    marker = {
        "index": index, "limits": limits, "results": count, "evidence": evidence_count,
        "result_bytes": result_path.stat().st_size, "evidence_bytes": evidence_path.stat().st_size,
    }
    write_json(str(prefix) + ".done.json", marker)
    return marker


def completed(output, index, limits):
    prefix = Path(output) / "shards" / f"{index:07d}"
    marker_path = Path(str(prefix) + ".done.json")
    if not marker_path.exists():
        return False
    marker = read_json(marker_path)
    if marker["limits"] != limits or marker["results"] != limits[2]:
        raise ValueError("Invalid completed shard marker")
    for kind, key in (("results", "result_bytes"), ("evidence", "evidence_bytes")):
        path = Path(str(prefix) + f".{kind}.jsonl")
        if not path.exists() or path.stat().st_size != marker[key]:
            raise ValueError("Completed shard is incomplete/corrupted; use a fresh output directory")
    return True


def run(input_path, output_dir, workers=4, shard_size=500, sample_size=None, deep_check=False):
    if min(workers, shard_size) < 1:
        raise ValueError("workers and shard_size must be positive")
    if sample_size is not None and sample_size < 1:
        raise ValueError("sample_size must be positive")
    registry = Registry()
    path = resolve_input(input_path)
    output = Path(output_dir).resolve()
    ensure_separate(path, output)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".running.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Output is locked. Confirm the previous process stopped before removing .running.lock")
    os.close(fd)

    pool = events = None
    started = time.monotonic()
    try:
        check = preflight(path, registry.config, deep_check=deep_check)
        limits = ranges(path, shard_size, sample_size)
        selected_count = sum(item[2] for item in limits)
        if sample_size is None and selected_count != check["target_count"]:
            raise ValueError("Enumerated target count disagrees with preflight result")
        scope = "sample" if sample_size is not None else "full"
        context = {
            "version": VERSION,
            "snapshot": registry.snapshot,
            "source": check["source"],
            "scope": scope,
            "sample_size": sample_size,
            "ranges": limits,
            "target_count": selected_count,
        }
        context_path = output / "run_context.json"
        if context_path.exists():
            if read_json(context_path) != context:
                raise ValueError("Input, rules, version or scope changed. Use a new output directory")
        else:
            write_json(context_path, context)
        write_json(output / "preflight.json", check)
        (output / "shards").mkdir(exist_ok=True)
        jobs = [
            (str(path), str(output), i, limits_i, registry.snapshot, sample_size is not None)
            for i, limits_i in enumerate(limits)
            if not completed(output, i, limits_i)
        ]
        done = len(limits) - len(jobs)
        print(f"Detection {done}/{len(limits)} shards; workers={workers}; scope={scope}", flush=True)
        if workers == 1:
            for job in jobs:
                work(job)
                done += 1
                print(f"Detection {done}/{len(limits)} shards", flush=True)
        elif jobs:
            spawn = mp.get_context("spawn")
            events = spawn.Queue()
            pool = spawn.Pool(workers, initializer=worker_init, initargs=(events,))
            worker_ids = set()
            pending, next_job = [], 0
            while next_job < len(jobs) or pending:
                try:
                    while True:
                        worker_ids.add(events.get_nowait())
                        if len(worker_ids) > workers:
                            raise RuntimeError("A worker exited unexpectedly and was replaced; rerun to resume completed shards")
                except queue.Empty:
                    pass
                while next_job < len(jobs) and len(pending) < workers * 2:
                    pending.append(pool.apply_async(work, (jobs[next_job],)))
                    next_job += 1
                for task in pending[:]:
                    if task.ready():
                        task.get()
                        pending.remove(task)
                        done += 1
                        print(f"Detection {done}/{len(limits)} shards", flush=True)
                time.sleep(0.1)
            pool.close()
            pool.join()
            pool = None
        if source_stamp(path) != check["source"]:
            raise ValueError("Source changed during detection; output cannot be published")
        from .reports import merge
        merge(output)
        write_json(output / "run_summary.json", {
            "complete": True, "scope": scope, "target_count": selected_count,
            "workers": workers, "elapsed_seconds": round(time.monotonic() - started, 3),
            "completed_at": utc_now(),
        })
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
        if events is not None:
            events.close()
            events.join_thread()
        lock.unlink(missing_ok=True)

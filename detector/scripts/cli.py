import argparse
import json
import sys

from detector_core.input_db import preflight
from detector_core.registry import Registry
from detector_core.runner import run
from detector_core import reports


def main():
    parser = argparse.ArgumentParser(description="Offline evidence-based PR coding-agent trace detector")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Validate the input SQLite schema")
    pre.add_argument("input", help="Input directory or pr_agent_inputs.sqlite3 file")
    pre.add_argument("--deep-check", action="store_true", help="Run SQLite quick_check")

    detect = sub.add_parser("detect", help="Run detection, merge results, and audit the output")
    detect.add_argument("input", help="Input directory or pr_agent_inputs.sqlite3 file")
    detect.add_argument("output_dir")
    detect.add_argument("--workers", type=int, default=4)
    detect.add_argument("--shard-size", type=int, default=500)
    detect.add_argument("--sample-size", type=int, default=None, help="Process only the first N completed PRs")
    detect.add_argument("--deep-check", action="store_true", help="Run SQLite quick_check before detection")

    for name in ("audit", "export"):
        sub.add_parser(name).add_argument("output_dir")

    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight(args.input, Registry().config, deep_check=args.deep_check)
    elif args.command == "detect":
        run(args.input, args.output_dir, args.workers, args.shard_size, args.sample_size, args.deep_check)
        result = {"complete": True, "output_dir": args.output_dir, "scope": "sample" if args.sample_size else "full"}
    else:
        result = getattr(reports, args.command)(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled. Completed shards are retained; rerun the same detect command to resume.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)

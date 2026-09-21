from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import SEVERITY, Change, compare, load_tools


def _read(path: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    return load_tools(value)


def _summary(changes: list[Change]) -> str:
    counts = {level: sum(c.severity == level for c in changes) for level in SEVERITY}
    status = max((c.severity for c in changes), key=lambda x: SEVERITY[x], default="compatible")
    return f"status={status} compatible={counts['compatible']} review={counts['review']} breaking={counts['breaking']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diff the agent-facing contract of two MCP tool manifests.")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on", choices=["review", "breaking"], default="breaking")
    args = parser.parse_args(argv)
    try:
        changes = compare(_read(args.before), _read(args.after))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps({"summary": _summary(changes), "changes": [c.as_dict() for c in changes]}, indent=2, sort_keys=True))
    else:
        print(_summary(changes))
        for change in changes:
            print(f"{change.severity.upper():10} {change.tool}: {change.detail}")

    threshold = SEVERITY[args.fail_on]
    return 1 if any(SEVERITY[c.severity] >= threshold for c in changes) else 0


if __name__ == "__main__":
    raise SystemExit(main())

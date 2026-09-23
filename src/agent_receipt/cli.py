"""CLI: inspect a reply or rewrite it when the receipt is empty."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_receipt import __version__, inspect, ledger_from_dict, ledger_from_workspace


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-receipt",
        description="Reject 'done' from an agent when no file or tool evidence exists.",
    )
    parser.add_argument("--version", action="version", version=f"agent-receipt {__version__}")
    parser.add_argument("--ask", required=True, help="original user request")
    parser.add_argument("--reply", required=True, help="model reply to check")
    parser.add_argument("--dir", type=Path, help="workspace folder that should contain new files")
    parser.add_argument("--ledger", type=Path, help="JSON evidence file")
    parser.add_argument("--require-tool", action="append", default=[], help="tool name that must appear in the ledger")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rewrite", action="store_true", help="print the rewritten reply only")
    args = parser.parse_args(argv)

    ledger = ledger_from_dict({})
    if args.ledger:
        ledger = ledger_from_dict(_load_json(args.ledger))
    if args.dir:
        disk = ledger_from_workspace(args.dir)
        ledger.writes = max(ledger.writes, disk.writes)
        ledger.disk_verified = ledger.disk_verified or disk.disk_verified
        ledger.generated_images = max(ledger.generated_images, disk.generated_images)
        ledger.artifacts = list(dict.fromkeys(ledger.artifacts + disk.artifacts))
        if disk.tool_successes and not ledger.tool_successes:
            ledger.tool_successes = disk.tool_successes

    receipt = inspect(args.ask, args.reply, ledger, args.require_tool)
    if args.rewrite:
        print(receipt.rewritten)
        return 0 if receipt.ok or not receipt.claimed_success else 1
    if args.json:
        print(json.dumps(receipt.as_dict(), indent=2))
    else:
        status = "PASS" if receipt.ok else "FAIL"
        print(f"{status}  kind={receipt.kind}  claimed_success={receipt.claimed_success}")
        if receipt.gaps:
            print("gaps: " + ", ".join(receipt.gaps))
        if receipt.rewritten != args.reply:
            print("rewrite:")
            print(receipt.rewritten)
    return 0 if receipt.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

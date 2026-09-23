"""Evidence that work happened: tool log, JSON, or files on disk."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_IMAGE_SUFFIX = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


@dataclass
class ExecutionLedger:
    tool_successes: int = 0
    writes: int = 0
    reads: int = 0
    qa_pass: bool = False
    disk_verified: bool = False
    generated_images: int = 0
    sourced_images: int = 0
    used_tools: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_successes": self.tool_successes,
            "writes": self.writes,
            "reads": self.reads,
            "qa_pass": self.qa_pass,
            "disk_verified": self.disk_verified,
            "generated_images": self.generated_images,
            "sourced_images": self.sourced_images,
            "used_tools": list(self.used_tools),
            "artifacts": list(self.artifacts),
        }


def ledger_from_dict(data: dict[str, Any] | None) -> ExecutionLedger:
    raw = data or {}
    tools = raw.get("used_tools") or raw.get("tools") or []
    artifacts = raw.get("artifacts") or raw.get("files") or []
    return ExecutionLedger(
        tool_successes=int(raw.get("tool_successes") or raw.get("ok_tools") or 0),
        writes=int(raw.get("writes") or 0),
        reads=int(raw.get("reads") or 0),
        qa_pass=bool(raw.get("qa_pass") or raw.get("tests_passed") or False),
        disk_verified=bool(raw.get("disk_verified") or False),
        generated_images=int(raw.get("generated_images") or 0),
        sourced_images=int(raw.get("sourced_images") or 0),
        used_tools=[str(item).lower() for item in tools],
        artifacts=[str(item) for item in artifacts],
    )


def ledger_from_workspace(root: Path, min_bytes: int = 1) -> ExecutionLedger:
    """Treat existing files under ``root`` as write evidence."""
    root = root.expanduser()
    if not root.exists() or not root.is_dir():
        return ExecutionLedger()
    artifacts: list[str] = []
    images = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.stat().st_size < min_bytes:
            continue
        rel = str(path.relative_to(root))
        artifacts.append(rel)
        if path.suffix.lower() in _IMAGE_SUFFIX:
            images += 1
    return ExecutionLedger(
        writes=len(artifacts),
        tool_successes=1 if artifacts else 0,
        disk_verified=bool(artifacts),
        generated_images=images,
        artifacts=artifacts,
    )

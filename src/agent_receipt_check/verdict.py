"""Compare the model's claim against the evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_receipt_check.contract import ActionContract
from agent_receipt_check.ledger import ExecutionLedger
from agent_receipt_check.text import fold

_SUCCESS_CLAIM_RE = re.compile(
    r"(?i)\b(?:fertig|erledigt|success|pass|done|abgeschlossen|aktualisiert|updated|"
    r"erstellt|created|erzeugt|generated|geschrieben|written|gespeichert|saved|"
    r"geoeffnet|implementiert|implemented|fixed|repaired)\b"
)
# Clear task failure only — bare "error" / "failed" must NOT cancel a Done claim
# (agents often say "Done. Error: …" while still claiming success).
_FAILURE_WORD_RE = re.compile(
    r"(?i)\b(?:nicht\s+fertig|fehlgeschlagen|konnte\s+nicht|unavailable|"
    r"nicht\s+verfuegbar|could\s+not|failed\s+to|i\s+failed|"
    r"nicht\s+erstellt|not\s+created|unable\s+to)\b"
)

_LABELS = {
    "no_execution": "no executed action",
    "no_write": "no successful write",
    "no_verify": "no verification step",
    "image_unavailable": "no image artifact",
    "image_not_generated": "no generated image",
}


@dataclass(frozen=True)
class Receipt:
    ok: bool
    gaps: tuple[str, ...]
    claimed_success: bool
    kind: str
    rewritten: str

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "gaps": list(self.gaps),
            "claimed_success": self.claimed_success,
            "kind": self.kind,
            "rewritten": self.rewritten,
        }


def has_success_claim(answer: str) -> bool:
    """True when the reply claims the work is done.

    "Done" plus a bare "error" still counts as a success claim. Only clear
    negations ("could not", "failed to", "nicht fertig") cancel it.
    """
    folded = fold(answer)
    if not _SUCCESS_CLAIM_RE.search(folded):
        return False
    if _FAILURE_WORD_RE.search(folded):
        return False
    return True


def completion_gaps(contract: ActionContract, ledger: ExecutionLedger) -> list[str]:
    if contract.request_kind != "action":
        return []
    gaps: list[str] = []
    has_execution = bool(
        ledger.tool_successes
        or ledger.qa_pass
        or ledger.generated_images
        or ledger.sourced_images
        or ledger.disk_verified
        or ledger.writes
        or ledger.used_tools
    )
    if contract.requires_execution and not has_execution:
        gaps.append("no_execution")
    if contract.requires_write and ledger.writes <= 0:
        gaps.append("no_write")
    if contract.requires_verify and not (ledger.qa_pass or ledger.disk_verified or ledger.reads > 0):
        gaps.append("no_verify")
    if contract.requests_image_work and not (ledger.generated_images or ledger.sourced_images):
        gaps.append("image_unavailable")
    if contract.requires_generated_image and ledger.generated_images <= 0:
        gaps.append("image_not_generated")
    used = {item.lower() for item in ledger.used_tools}
    for tool in contract.required_tools:
        if tool not in used:
            gaps.append(f"{tool}_not_used")
    return list(dict.fromkeys(gaps))


def _rewrite(answer: str, gaps: list[str]) -> str:
    detail = ", ".join(_LABELS.get(item, item.replace("_", " ")) for item in gaps)
    return f"Not done. Receipt is missing: {detail}."


def inspect(prompt: str, answer: str, ledger: ExecutionLedger, required_tools: list[str] | None = None) -> Receipt:
    from agent_receipt_check.contract import build_action_contract

    contract = build_action_contract(prompt, required_tools)
    gaps = completion_gaps(contract, ledger)
    claimed = has_success_claim(answer)
    ok = not gaps
    rewritten = answer if ok or not claimed else _rewrite(answer, gaps)
    return Receipt(
        ok=ok,
        gaps=tuple(gaps),
        claimed_success=claimed,
        kind=contract.request_kind,
        rewritten=rewritten,
    )


def enforce(answer: str, contract: ActionContract, ledger: ExecutionLedger) -> str:
    gaps = completion_gaps(contract, ledger)
    if not gaps or not has_success_claim(answer):
        return answer
    return _rewrite(answer, gaps)

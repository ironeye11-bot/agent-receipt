"""Turn a user request into a checklist the model must satisfy."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_receipt.text import fold

_ACTION_RE = re.compile(
    r"(?i)\b(?:mach|mache|macht|erstell|erzeuge|generier|aender|ander|update|aktualisier|"
    r"oeffne|offne|pruef|pruf|suche|such|bau|schreib|speicher|kopier|lade|installier|"
    r"reparier|fix|starte|formatier|create|generate|update|edit|open|check|search|build|write|"
    r"save|copy|download|install|repair|start|add|delete|remove|implement|refactor|format)\w*\b"
)
_WRITE_RE = re.compile(
    r"(?i)\b(?:mach|erstell|erzeug|generier|aender|ander|update|aktualisier|bau|schreib|"
    r"speicher|kopier|installier|reparier|fix|formatier|create|generate|update|edit|build|write|"
    r"save|copy|install|repair|add|delete|remove|implement|refactor|format)\w*\b"
)
_VERIFY_RE = re.compile(
    r"(?i)\b(?:pruef|pruf|test|verify|check|kontrollier|validier)\w*\b"
)
# How-to / what-is questions stay chat even if an action verb appears.
_QUESTION_RE = re.compile(
    r"(?i)(?:^\s*(?:how\s+(?:do|can|would|should|to)\b|what\s+(?:is|are|does|do)\b|"
    r"why\s+(?:is|are|do|does|can)\b|when\s+(?:do|does|should|is)\b|"
    r"where\s+(?:do|does|is|can)\b|who\s+(?:is|are|can)\b|"
    r"can\s+you\s+explain\b|could\s+you\s+explain\b|please\s+explain\b|"
    r"wie\s+(?:kann|mache|mach|geht|funktioniert)\b|was\s+(?:ist|sind|bedeutet)\b|"
    r"warum\b|wieso\b|erklaere?\b|beschreib\w*)|"
    r"\b(?:explain|describe)\b)"
)
_IMAGE_WORD = r"\b\w*(?:bild|bilder|foto|fotos|image|images|grafik|grafiken|screenshot)\b"
_IMAGE_RE = re.compile(rf"(?i){_IMAGE_WORD}")
_IMAGE_GENERATE_RE = re.compile(
    rf"(?i)(?:{_IMAGE_WORD}.{{0,48}}"
    r"\b(?:erstell|erzeug|generier|create|generate|zeichne|draw)\w*\b|"
    r"\b(?:erstell|erzeug|generier|create|generate|zeichne|draw)\w*\b.{0,48}"
    rf"{_IMAGE_WORD})"
)
_ARTIFACT_RE = re.compile(
    r"(?i)(\b(datei|ordner|file|folder|repo|projekt|project|website|code|app)\b|"
    r"\w+\.(py|js|ts|tsx|jsx|md|txt|json|toml|yml|yaml|html|css|svg|png))"
)


@dataclass(frozen=True)
class ActionContract:
    request_kind: str
    requires_execution: bool
    requires_write: bool
    requires_verify: bool
    requests_image_work: bool
    requires_generated_image: bool
    required_tools: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "request_kind": self.request_kind,
            "requires_execution": self.requires_execution,
            "requires_write": self.requires_write,
            "requires_verify": self.requires_verify,
            "requests_image_work": self.requests_image_work,
            "requires_generated_image": self.requires_generated_image,
            "required_tools": list(self.required_tools),
        }


def build_action_contract(prompt: str, required_tools: list[str] | None = None) -> ActionContract:
    folded = fold(prompt)
    looks_like_question = bool(_QUESTION_RE.search(folded))
    is_action = bool(_ACTION_RE.search(folded)) and not looks_like_question
    image_work = bool(_IMAGE_RE.search(folded)) and is_action
    generated_image = bool(_IMAGE_GENERATE_RE.search(folded)) and is_action
    requires_write = is_action and bool(_WRITE_RE.search(folded)) and bool(_ARTIFACT_RE.search(folded))
    requires_verify = is_action and bool(_VERIFY_RE.search(folded))
    tools = tuple(
        item.strip().lower()
        for item in (required_tools or [])
        if item and item.strip()
    )
    return ActionContract(
        request_kind="action" if is_action else "chat",
        requires_execution=is_action,
        requires_write=requires_write,
        requires_verify=requires_verify,
        requests_image_work=image_work,
        requires_generated_image=generated_image,
        required_tools=tools,
    )

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_receipt.cli import main
from agent_receipt.contract import build_action_contract
from agent_receipt.ledger import ExecutionLedger, ledger_from_workspace
from agent_receipt.verdict import enforce, inspect


class ContractTests(unittest.TestCase):
    def test_chat_is_not_an_action(self) -> None:
        c = build_action_contract("What is a worktree?")
        self.assertEqual(c.request_kind, "chat")
        self.assertFalse(c.requires_execution)

    def test_write_request_detected_en_and_de(self) -> None:
        en = build_action_contract("Create the file src/app.py in this project")
        de = build_action_contract("Erstell die Datei src/app.py im Projekt")
        self.assertTrue(en.requires_write)
        self.assertTrue(de.requires_write)

    def test_image_generate(self) -> None:
        c = build_action_contract("Generate an image of a red bicycle")
        self.assertTrue(c.requires_generated_image)


class VerdictTests(unittest.TestCase):
    def test_fail_when_done_but_no_files(self) -> None:
        receipt = inspect(
            "Create the file hello.py in this folder",
            "Done. File created.",
            ExecutionLedger(),
        )
        self.assertFalse(receipt.ok)
        self.assertIn("no_write", receipt.gaps)
        self.assertTrue(receipt.rewritten.startswith("Not done."))

    def test_pass_when_write_landed(self) -> None:
        receipt = inspect(
            "Create the file hello.py in this folder",
            "Done. File created.",
            ExecutionLedger(writes=1, tool_successes=1, disk_verified=True),
        )
        self.assertTrue(receipt.ok)
        self.assertEqual(receipt.rewritten, "Done. File created.")

    def test_honest_failure_is_left_alone(self) -> None:
        text = "I could not write the file."
        out = enforce(
            text,
            build_action_contract("Create the file hello.py"),
            ExecutionLedger(),
        )
        self.assertEqual(out, text)

    def test_required_tool(self) -> None:
        receipt = inspect(
            "Write formatted files in this project",
            "Done.",
            ExecutionLedger(tool_successes=1, writes=1),
            required_tools=["prettier"],
        )
        self.assertIn("prettier_not_used", receipt.gaps)


class WorkspaceTests(unittest.TestCase):
    def test_directory_counts_as_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("ok", encoding="utf-8")
            ledger = ledger_from_workspace(Path(tmp))
            self.assertEqual(ledger.writes, 1)
            self.assertTrue(ledger.disk_verified)


class CliTests(unittest.TestCase):
    def test_cli_fail_exit(self) -> None:
        code = main(
            [
                "--ask",
                "Create the file hello.py in this project",
                "--reply",
                "Fertig, Datei erstellt.",
            ]
        )
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

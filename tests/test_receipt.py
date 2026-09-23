from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_receipt.cli import main
from agent_receipt.contract import build_action_contract
from agent_receipt.ledger import ExecutionLedger, ledger_from_workspace
from agent_receipt.verdict import enforce, has_success_claim, inspect


class ContractTests(unittest.TestCase):
    def test_chat_is_not_an_action(self) -> None:
        c = build_action_contract("What is a worktree?")
        self.assertEqual(c.request_kind, "chat")
        self.assertFalse(c.requires_execution)

    def test_how_to_question_is_chat_not_action(self) -> None:
        c = build_action_contract("How do I create a file?")
        self.assertEqual(c.request_kind, "chat")
        self.assertFalse(c.requires_write)

    def test_explain_is_chat(self) -> None:
        c = build_action_contract("Please explain git rebase")
        self.assertEqual(c.request_kind, "chat")

    def test_write_request_detected_en_and_de(self) -> None:
        en = build_action_contract("Create the file src/app.py in this project")
        de = build_action_contract("Erstell die Datei src/app.py im Projekt")
        self.assertTrue(en.requires_write)
        self.assertTrue(de.requires_write)

    def test_format_repo_is_action(self) -> None:
        c = build_action_contract("Format the repo")
        self.assertEqual(c.request_kind, "action")

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

    def test_done_plus_error_still_success_claim(self) -> None:
        """Done + bare 'error' still claims success; missing files => fail."""
        self.assertTrue(has_success_claim("Done, but there was an error."))
        self.assertTrue(has_success_claim("Fertig. Error beim Speichern."))
        receipt = inspect(
            "Create the file hello.py in this folder",
            "Done, but there was an error.",
            ExecutionLedger(),
        )
        self.assertTrue(receipt.claimed_success)
        self.assertFalse(receipt.ok)
        self.assertIn("no_write", receipt.gaps)
        self.assertTrue(receipt.rewritten.startswith("Not done."))

    def test_not_created_is_fail(self) -> None:
        receipt = inspect(
            "Create the file hello.py in this project",
            "Done. File created.",
            ExecutionLedger(writes=0),
        )
        self.assertFalse(receipt.ok)
        self.assertIn("no_write", receipt.gaps)

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
        self.assertFalse(has_success_claim(text))

    def test_could_not_after_done_cancels_claim(self) -> None:
        self.assertFalse(has_success_claim("Done. I could not write the file."))

    def test_required_tool(self) -> None:
        receipt = inspect(
            "Write formatted files in this project",
            "Done.",
            ExecutionLedger(tool_successes=1, writes=1),
            required_tools=["prettier"],
        )
        self.assertIn("prettier_not_used", receipt.gaps)

    def test_question_pass_without_files(self) -> None:
        receipt = inspect(
            "How do I create a file?",
            "Done. Here is how: use touch.",
            ExecutionLedger(),
        )
        self.assertEqual(receipt.kind, "chat")
        self.assertTrue(receipt.ok)


class WorkspaceTests(unittest.TestCase):
    def test_directory_counts_as_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("ok", encoding="utf-8")
            ledger = ledger_from_workspace(Path(tmp))
            self.assertEqual(ledger.writes, 1)
            self.assertTrue(ledger.disk_verified)

    def test_empty_dir_is_not_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ledger_from_workspace(Path(tmp))
            self.assertEqual(ledger.writes, 0)
            self.assertFalse(ledger.disk_verified)


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

    def test_cli_dir_presence_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "app.py").write_text("x", encoding="utf-8")
            code = main(
                [
                    "--ask",
                    "Create src/app.py in this project",
                    "--reply",
                    "Done.",
                    "--dir",
                    tmp,
                ]
            )
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

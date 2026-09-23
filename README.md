# Agent Receipt

Block an agent's "done" when no file is there.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

<p align="center">
  <img src="docs/hero.jpg" alt="product photo" width="100%">
</p>
<p align="center">
  <img src="docs/hero.svg" alt="Agent Receipt" width="100%">
</p>

Local coding agents say **done**. Then the folder is empty.

Agent Receipt takes the user request, the model reply, and either a workspace directory or a JSON ledger. If the reply claims success and the evidence is missing, the reply is rewritten.

No cloud. No model. No telemetry.

<p align="center">
  <img src="docs/terminal.svg" alt="FAIL then PASS" width="86%">
</p>

## Install

```bash
pip install git+https://github.com/ironeye11-bot/agent-receipt.git
```

## Use

```bash
agent-receipt --ask "Create src/app.py in this project" --reply "Done. File created."
# FAIL  gaps: no_write

agent-receipt --ask "Create src/app.py in this project" --reply "Done." --dir ./src
# PASS if ./src actually contains a file

agent-receipt --ask "Format the repo" --reply "Done." --ledger ledger.json --require-tool prettier
```

### `--dir` is presence evidence

`--dir` counts **existing** files under that folder as write evidence. It does not
diff against a before-state, does not know which process created the files, and
does not prove the agent wrote them in this turn. Pre-existing files make a
false PASS possible. Prefer a JSON `--ledger` from your harness when you need
stricter proof.

`--rewrite` prints only the corrected reply so you can drop it into a hook:

```bash
agent-receipt --ask "$PROMPT" --reply "$ANSWER" --dir "$PWD" --rewrite
```

### Ledger JSON

```json
{
  "writes": 1,
  "tool_successes": 2,
  "used_tools": ["write_file", "pytest"],
  "tests_passed": true,
  "artifacts": ["src/app.py"]
}
```

## Library

```python
from agent_receipt import ExecutionLedger, inspect

receipt = inspect(
    "Create hello.py in this folder",
    "Fertig, Datei erstellt.",
    ExecutionLedger(writes=0),
)
assert receipt.ok is False
print(receipt.rewritten)
```

German and English requests are both understood. Agent names from any stack are irrelevant — pass `--require-tool` if a specific tool must have run.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT

"""Did the agent actually do the thing it claimed?"""

from agent_receipt_check.contract import ActionContract, build_action_contract
from agent_receipt_check.ledger import ExecutionLedger, ledger_from_dict, ledger_from_workspace
from agent_receipt_check.verdict import Receipt, enforce, inspect

__version__ = "1.0.2"
__all__ = [
    "ActionContract",
    "ExecutionLedger",
    "Receipt",
    "build_action_contract",
    "enforce",
    "inspect",
    "ledger_from_dict",
    "ledger_from_workspace",
    "__version__",
]

# src/cli/commands.py
#
# Simple stdin-based CLI for a single node.
#
# Commands:
#   moneyTransfer <creditNode> <amount>
#   printBlockchain
#   printBalance
#   failProcess
#   fixProcess
#
# debit node is always this process's node, as per assignment text.

import sys
import os
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # to avoid import cycles at runtime
    from ..node import Node


def _parse_account_id(token: str) -> str:
    """
    Normalize things like "1" or "P1" into "P1".
    """
    token = token.strip().upper()
    if token.startswith("P"):
        return token
    return "P" + token


async def run_cli(node: "Node") -> None:
    """
    Async CLI loop that reads commands from stdin and dispatches
    to the appropriate Node methods.
    """
    loop = asyncio.get_running_loop()
    print(
        f"[CLI {node.config.id}] Ready. Commands: "
        "moneyTransfer <creditNode> <amount> | "
        "printBlockchain | printBalance | failProcess | fixProcess",
        flush=True,
    )

    while True:
        # Read a line in a thread so we don't block the event loop.
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            continue

        line = line.strip()
        if not line:
            continue

        parts = line.split()
        cmd = parts[0]

        try:
            if cmd == "moneyTransfer":
                # moneyTransfer <creditNode> <amount>
                if len(parts) != 3:
                    print(
                        "Usage: moneyTransfer <creditNode> <amount>  "
                        "(debit is always this node)",
                        flush=True,
                    )
                    continue

                debit_id = f"P{node.config.id}"  # this node is the debit node
                credit_id = _parse_account_id(parts[1])
                try:
                    amount = int(parts[2])
                except ValueError:
                    print("Amount must be an integer", flush=True)
                    continue

                if amount <= 0:
                    print("Amount must be positive", flush=True)
                    continue

                node.handle_money_transfer(debit_id, credit_id, amount)

            elif cmd == "printBlockchain":
                node.print_blockchain()

            elif cmd == "printBalance":
                node.print_balances()

            elif cmd == "failProcess":
                print(f"[CLI {node.config.id}] Failing process now.", flush=True)
                # Immediate exit; restart handled by your run_Pn.sh or whatever.
                os._exit(0)

            elif cmd == "fixProcess":
                # Here "fixProcess" just tells the user what to do.
                print(
                    "[CLI] To 'fix' a process in this implementation, "
                    "restart the node (e.g., run the corresponding script again).",
                    flush=True,
                )

            else:
                print(
                    "Unknown command. Available: "
                    "moneyTransfer, printBlockchain, printBalance, "
                    "failProcess, fixProcess",
                    flush=True,
                )
        except Exception as e:
            # Don't let the CLI die from random bugs.
            print(f"[CLI ERROR] {e}", flush=True)

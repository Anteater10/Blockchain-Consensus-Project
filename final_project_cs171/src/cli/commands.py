# src/cli/commands.py
#
# Simple stdin-based CLI for a single node.
#
# Commands:
#   moneyTransfer <debitNode> <creditNode> <amount>
#   moneyTransfer <creditNode> <amount>        (shorthand: debit = this node)
#   printBlockchain
#   printBalance
#   failProcess
#   fixProcess
#
# debit node must always be this process, per assignment spec.

import sys
import os
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # to avoid import cycles
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
        "moneyTransfer <debitNode> <creditNode> <amount> | "
        "moneyTransfer <creditNode> <amount> | "
        "printBlockchain | printBalance | failProcess | fixProcess",
        flush=True,
    )

    while True:
        # Non-blocking stdin read (threaded)
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
                #
                # Accept TWO forms:
                #
                # 1) moneyTransfer <debitNode> <creditNode> <amount>
                # 2) moneyTransfer <creditNode> <amount>
                #
                if len(parts) == 4:
                    # Explicit debit
                    debit_tok = parts[1]
                    credit_tok = parts[2]
                    amount_tok = parts[3]
                    debit_id = _parse_account_id(debit_tok)

                elif len(parts) == 3:
                    # Shorthand: debit = this node
                    debit_id = f"P{node.config.id}"
                    credit_tok = parts[1]
                    amount_tok = parts[2]

                else:
                    print(
                        "Usage:\n"
                        "  moneyTransfer <debitNode> <creditNode> <amount>\n"
                        "  moneyTransfer <creditNode> <amount>  (debit = this node)",
                        flush=True,
                    )
                    continue

                credit_id = _parse_account_id(credit_tok)

                # Enforce: debit must be this process
                expected = f"P{node.config.id}"
                if debit_id != expected:
                    print(
                        f"[CLI {node.config.id}] ERROR: "
                        f"Debit node must be this process ({expected}), "
                        f"but got {debit_id}",
                        flush=True,
                    )
                    continue

                # Parse amount
                try:
                    amount = int(amount_tok)
                except ValueError:
                    print("Amount must be an integer.", flush=True)
                    continue

                if amount <= 0:
                    print("Amount must be positive.", flush=True)
                    continue

                # Trigger Paxos proposal
                node.handle_money_transfer(debit_id, credit_id, amount)

            elif cmd == "printBlockchain":
                node.print_blockchain()

            elif cmd == "printBalance":
                node.print_balances()

            elif cmd == "failProcess":
                print(f"[CLI {node.config.id}] Failing process now.", flush=True)
                os._exit(0)

            elif cmd == "fixProcess":
                print(
                    "[CLI] To fix a process, simply restart this node using your scripts.",
                    flush=True,
                )

            else:
                print(
                    "Unknown command. Available commands:\n"
                    "  moneyTransfer, printBlockchain, printBalance, "
                    "failProcess, fixProcess",
                    flush=True,
                )

        except Exception as e:
            print(f"[CLI ERROR] {e}", flush=True)

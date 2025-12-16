# src/cli/commands.py
#
# Simple stdin-based CLI for a single node.
#
# Commands:
#   moneyTransfer <debitNode> <creditNode> <amount>
#   moneyTransfer <creditNode> <amount> (shorthand: debit = this node)
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
    from ..node import Node


def _parse_account_id(token: str) -> str:
    token = token.strip().upper()
    if token.startswith("P"):
        return token
    return "P" + token


async def run_cli(node: "Node") -> None:
    loop = asyncio.get_running_loop()
    print(
        f"\n[CLI {node.config.id}] Interactive console ready.\n"
        "  Available commands:\n"
        "    moneyTransfer <debitNode> <creditNode> <amount>\n"
        "    moneyTransfer <creditNode> <amount>     (debit = this node)\n"
        "    printBlockchain                         (show decided blocks)\n"
        "    printBalance                            (show account balances)\n"
        "    failProcess                             (kill this node)\n"
        "    fixProcess                              (how to restart)\n",
        flush=True,
    )

    while True:
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
                # 1) moneyTransfer <debitNode> <creditNode> <amount>
                # 2) moneyTransfer <creditNode> <amount>
                #
                if len(parts) == 4:
                    debit_tok = parts[1]
                    credit_tok = parts[2]
                    amount_tok = parts[3]
                    debit_id = _parse_account_id(debit_tok)  # explicit debit

                elif len(parts) == 3:
                    debit_id = f"P{node.config.id}"  # debit = this node
                    credit_tok = parts[1]
                    amount_tok = parts[2]

                else:
                    print(
                        "\n[CLI] Usage:\n"
                        "  moneyTransfer <debitNode> <creditNode> <amount>\n"
                        "  moneyTransfer <creditNode> <amount>    (debit = this node)\n",
                        flush=True,
                    )
                    continue

                credit_id = _parse_account_id(credit_tok)

                expected = f"P{node.config.id}"
                if debit_id != expected:  # debit must be this process
                    print(
                        f"[CLI {node.config.id}] ERROR: debit node must be this process "
                        f"({expected}), but got {debit_id}. No transaction proposed.\n",
                        flush=True,
                    )
                    continue

                try:
                    amount = int(amount_tok)
                except ValueError:
                    print("[CLI] Amount must be an integer.\n", flush=True)
                    continue

                if amount <= 0:
                    print("[CLI] Amount must be positive.\n", flush=True)
                    continue

                print(
                    f"[CLI {node.config.id}] Requesting transfer: "
                    f"{debit_id} -> {credit_id}, amount={amount}",
                    flush=True,
                )
                node.handle_money_transfer(debit_id, credit_id, amount)  # trigger Paxos proposal

            elif cmd == "printBlockchain":
                node.print_blockchain()

            elif cmd == "printBalance":
                node.print_balances()

            elif cmd == "failProcess":
                print(
                    f"[CLI {node.config.id}] Simulating crash now. "
                    "Paxos + recovery will have to bring this node back in sync "
                    "after restart.",
                    flush=True,
                )
                os._exit(0)

            elif cmd == "fixProcess":
                print(
                    "[CLI] To 'fix' a process, simply restart this node using your run script.\n"
                    "      The node will reload blockchain.json, balances.json, and ledger_log.json\n"
                    "      and attempt to catch up with the rest of the cluster.",
                    flush=True,
                )

            else:
                print(
                    "\n[CLI] Unknown command.\n"
                    "  Available commands:\n"
                    "    moneyTransfer, printBlockchain, printBalance, "
                    "failProcess, fixProcess\n",
                    flush=True,
                )

        except Exception as e:
            print(f"[CLI ERROR] {e}\n", flush=True)

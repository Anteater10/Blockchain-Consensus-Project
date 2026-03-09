# Blockchain Consensus Project

Distributed blockchain simulation built in Python using async peer-to-peer networking, Paxos consensus, and local ledger persistence.

## Overview

This project simulates a 5-node blockchain network where each node communicates over TCP with JSON messages and uses Paxos to agree on transaction blocks. Each node maintains its own blockchain, balances, and ledger log on disk.

This was originally developed as a two-person school project, and I contributed approximately 50% of the implementation.

## Features

- 5-node distributed blockchain simulation
- Paxos-based consensus for block agreement
- Async TCP networking
- Local blockchain, balance, and ledger storage
- CLI commands for submitting transfers and inspecting state
- Proof-of-work metadata stored with each block

## Tech Stack

- Python
- `asyncio`
- JSON messaging
- File-based persistence

## Project Structure

```text
final_project_cs171/
├── config/
├── data/
├── run/
├── src/
│   ├── node.py
│   ├── blockchain/
│   ├── paxos/
│   ├── network/
│   ├── storage/
│   ├── accounts/
│   └── cli/
└── README.md
```

## Running the Project

From the project root, open 5 terminals and run:

```bash
./run/run_p1.sh
./run/run_p2.sh
./run/run_p3.sh
./run/run_p4.sh
./run/run_p5.sh
```

Each node should start with a summary showing its node ID, host, port, data directory, and peer list.

## Example Commands

Run these on any node after startup:

```text
printBalance
printBlockchain
moneyTransfer 2 10
failProcess
```

## Expected Behavior

- All nodes start and connect to peers
- `printBalance` shows the current balances
- `printBlockchain` displays the committed chain
- `moneyTransfer` proposes a new transaction block through Paxos
- Nodes persist blockchain and ledger state locally

## Notes

This repository is shared as a portfolio project to highlight distributed systems, consensus, and blockchain-related engineering work.

A production-clean version of this repo should also remove tracked environment artifacts such as `venv/` and `__pycache__/` and include a proper `.gitignore`.


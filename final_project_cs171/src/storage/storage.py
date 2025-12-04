# src/storage/storage.py
# This file has helper functions to save and load the blockchain
# and account balances using JSON on disk.

import json
from pathlib import Path

from ..blockchain.block import Block
from ..blockchain.chain import Blockchain
from ..accounts.accounts import AccountsTable



def save_blockchain(blockchain, path):
    """
    Write the current blockchain (list of blocks) to a JSON file.
    """
    p = Path(path)
    blocks_data = []
    for b in blockchain.blocks:
        blocks_data.append(b.to_dict())

    text = json.dumps(blocks_data, indent=2)
    p.write_text(text, encoding="utf-8")


def load_blockchain(path):
    """
    Load a blockchain from a JSON file.
    If the file does not exist, or is invalid, return an empty chain.
    """
    p = Path(path)
    chain = Blockchain()

    if not p.exists():
        return chain

    text = p.read_text(encoding="utf-8").strip()
    if text == "":
        return chain

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return chain

    # data should be a list of block dicts
    for d in data:
        block = Block.from_dict(d)
        chain.blocks.append(block)

    return chain


def save_balances(accounts, path):
    """
    Save balances to JSON. 'accounts' can be an AccountsTable or a dict.
    """
    p = Path(path)

    if isinstance(accounts, AccountsTable):
        balances = accounts.balances
    else:
        balances = accounts

    text = json.dumps(balances, indent=2)
    p.write_text(text, encoding="utf-8")


def load_balances(path):
    """
    Load balances from JSON.
    If the file doesn't exist or is invalid, return a fresh AccountsTable.
    """
    p = Path(path)

    if not p.exists():
        return AccountsTable.fresh()

    text = p.read_text(encoding="utf-8").strip()
    if text == "":
        return AccountsTable.fresh()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return AccountsTable.fresh()

    # data should be a dict: {"P1": 100, ...}
    return AccountsTable(data)

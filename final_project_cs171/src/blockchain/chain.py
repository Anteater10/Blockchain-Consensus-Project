# src/blockchain/chain.py

# This file defines the Blockchain class, which keeps track of all blocks
# and creates new ones when a transaction happens.

import hashlib
from .block import Block
from .pow import compute_pow

GENESIS_PREV_HASH = "0" * 64   # First block uses dummy prev hash (64 zeros)


class Blockchain:
    def __init__(self):
        self.blocks = []  # list of Block objects

    def length(self):
        return len(self.blocks)

    def last_hash(self) -> str:
        """
        Return the PoW hash of the latest block.
        For an empty chain, return the GENESIS_PREV_HASH.
        """
        if len(self.blocks) == 0:
            return GENESIS_PREV_HASH
        return self.blocks[-1].hash   # *** FIXED: use the previous block's real hash ***

    def new_block_for_tx(self, tx):
        """
        Create a new Block for a given transaction:
        - depth = current chain length
        - prev_hash = hash of last block
        - compute nonce + PoW hash
        """
        depth = self.length()
        prev_hash = self.last_hash()
        nonce, block_hash = compute_pow(tx)

        block = Block(depth, tx, nonce, prev_hash, block_hash)
        return block

    def append_block(self, block):
        """
        Append a new block to the chain if it maintains a valid chain:
        - block.depth must match current length
        - block.prev_hash must match last_hash()
        """
        if block.depth != self.length():
            raise ValueError("Block depth mismatch.")

        if block.prev_hash != self.last_hash():
            raise ValueError("prev_hash mismatch.")

        self.blocks.append(block)

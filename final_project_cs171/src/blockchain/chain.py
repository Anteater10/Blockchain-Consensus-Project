# src/blockchain/chain.py

# This file defines the Blockchain class, which keeps track of all blocks
# and creates new ones when a transaction happens.

from .block import Block
from .pow import compute_pow

GENESIS_PREV_HASH = "0" * 64 # from blockchain lecture, Normal blocks use the hash of the previous block.
# The first block uses a dummy previous hash. So we use a zero hash.

class Blockchain:
    def __init__(self):
        self.blocks = [] # create list of Block objects

    def length(self):
        return len(self.blocks)

    def last_hash(self):
        if len(self.blocks) == 0:
            return GENESIS_PREV_HASH
        return self.blocks[-1].hash # return the hash of the most recent block. or use 

    def new_block_for_tx(self, tx):
        depth = self.length() # depth of new block
        prev_hash = self.last_hash()# hash of previous block
        nonce, block_hash = compute_pow(tx) # find PoW to get nonce + hash

        block = Block(depth,tx,nonce,prev_hash,block_hash)
        return block

    def append_block(self, block):
        if block.depth != self.length():
            raise ValueError("Block depth mismatch.")

        if block.prev_hash != self.last_hash():
            raise ValueError("prev_hash mismatch.")

        self.blocks.append(block) # Add a new block to the chain
# src/blockchain/block.py

# This file defines the Block class used in our blockchain.
# Each block stores one transaction plus the proof of work fields.

class Block:
    def __init__(self, depth, tx, nonce, prev_hash, hash_value):
        self.depth = depth
        self.tx = tx
        self.nonce = nonce
        self.prev_hash = prev_hash
        self.hash = hash_value

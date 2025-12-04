# src/blockchain/block.py
# This file defines the Block class used in our blockchain.
# Each block stores one transaction plus the proof of work fields.


# A transaction is just a tuple like ("P1", "P2", 10).
class Block:
    def __init__(self, depth, tx, nonce, prev_hash, hash_value):
        self.depth = depth
        self.tx = tx
        self.nonce = nonce
        self.prev_hash = prev_hash
        self.hash = hash_value

    def to_dict(self):
        """
        Convert this Block into a plain dict so it can be written as JSON.
        """
        sender, receiver, amount = self.tx
        return {
            "depth": self.depth,
            "tx": [sender, receiver, amount],  # stored as a list in JSON
            "nonce": self.nonce,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }

    # note: no self here, called as Block.from_dict(d)
    def from_dict(d):
        """
        Build a Block object back from the dict we stored in JSON.
        """
        depth = d["depth"]
        sender, receiver, amount = d["tx"]
        tx = (sender, receiver, amount)
        nonce = d["nonce"]
        prev_hash = d["prev_hash"]
        hash_value = d["hash"]
        return Block(depth, tx, nonce, prev_hash, hash_value)

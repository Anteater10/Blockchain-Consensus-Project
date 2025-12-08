# src/paxos/messages.py
#
# This file defines the Paxos message types and a helper class
# for converting messages to/from dictionaries for JSON.
#
# Follows the Paxos structure from the slides:
#   - Message types: prepare, promise, accept, accepted, decide
#   - Ballot numbers are totally ordered pairs/triples:
#       (seq_num, proposer_id, depth)
#     so they can be compared globally and per-log-slot.

from enum import Enum

# Ballot = (seq_num, proposer_id, depth)
# This encodes the “unique proposal number” idea:
#   seq_num    → per-node increasing counter
#   proposer_id→ node id (tie-breaker)
#   depth      → log index / slot this ballot is for
Ballot = tuple[int, int, int]


class PaxosMessageType(str, Enum):
    PREPARE = "PREPARE"    # Phase 1a
    PROMISE = "PROMISE"    # Phase 1b (promise + prior AcceptNum/AcceptVal)
    ACCEPT = "ACCEPT"      # Phase 2a
    ACCEPTED = "ACCEPTED"  # Phase 2b
    DECIDE = "DECIDE"      # Phase 3 (announce decision)


class PaxosMessage:
    def __init__(
        self,
        msg_type: PaxosMessageType,
        from_id: int,
        ballot: Ballot,
        depth: int,
        value=None,
        accept_num: Ballot | None = None,
        accept_val=None,
        first_uncommitted: int | None = None,
    ):
        """
        msg_type          → one of the PaxosMessageType values
        from_id           → sender node id (proposer/acceptor)
        ballot            → (seq_num, proposer_id, depth) unique proposal number
        depth             → log index / block depth this message is about
        value             → proposed value (used in ACCEPT / ACCEPTED / DECIDE)
        accept_num        → last accepted ballot (AcceptNum) reported in PROMISE
        accept_val        → last accepted value (AcceptVal) reported in PROMISE
        first_uncommitted → hint: sender's first_uncommitted_index
                            (used for crash/partition recovery)
        """
        self.type = msg_type
        self.from_id = from_id
        self.ballot = ballot
        self.depth = depth
        self.value = value
        self.accept_num = accept_num
        self.accept_val = accept_val
        self.first_uncommitted = first_uncommitted

    def to_dict(self) -> dict:
        """
        Convert the message to a plain dict so it can be JSON-encoded
        on the network layer.

        We only include optional fields when they are present, similar
        to how different Paxos message types only carry the fields
        they need (e.g., PROMISE vs ACCEPT).
        """
        d = {
            "type": self.type.value,
            "from_id": self.from_id,
            "ballot": list(self.ballot),
            "depth": self.depth,
        }

        # Only include optional fields if they are set
        if self.value is not None:
            d["value"] = self.value

        if self.accept_num is not None:
            d["accept_num"] = list(self.accept_num)

        if self.accept_val is not None:
            d["accept_val"] = self.accept_val

        if self.first_uncommitted is not None:
            d["first_uncommitted"] = self.first_uncommitted

        return d

    @staticmethod
    def from_dict(d: dict) -> "PaxosMessage":
        """
        Build a PaxosMessage from a dict (after JSON decoding).

        This inverts to_dict() and reconstructs the Ballot and
        optional AcceptNum/AcceptVal fields exactly as the
        Paxos pseudocode uses them.
        """
        msg_type = PaxosMessageType(d["type"])
        ballot = tuple(d["ballot"])  # [seq, proposer, depth] → (seq, proposer, depth)

        accept_num = None
        if "accept_num" in d and d["accept_num"] is not None:
            accept_num = tuple(d["accept_num"])

        first_uncommitted = d.get("first_uncommitted")

        return PaxosMessage(
            msg_type=msg_type,
            from_id=int(d["from_id"]),
            ballot=ballot,
            depth=int(d["depth"]),
            value=d.get("value"),
            accept_num=accept_num,
            accept_val=d.get("accept_val"),
            first_uncommitted=first_uncommitted,
        )

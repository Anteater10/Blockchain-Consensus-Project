# src/paxos/state.py
#
# This file defines the per-node and per-depth Paxos state.
# It mirrors the variables from the Paxos slides:
#   BallotNum  → highest ballot we have promised to participate in
#   AcceptNum  → highest ballot we have accepted a value for
#   AcceptVal  → value associated with AcceptNum
#
# PaxosNodeState keeps track of these per-depth (per log slot),
# matching the “replicated log” picture where each slot is a
# separate consensus instance.

from .messages import Ballot

# "Empty" ballot used as a default when nothing is set yet.
# Equivalent to initial BallotNum/AcceptNum = <0,0> (extended
# here with depth component).
EMPTY_BALLOT: Ballot = (0, 0, 0)


class AcceptorState:
    def __init__(
        self,
        ballot_num: Ballot | None = None,
        accept_num: Ballot | None = None,
        accept_val=None,
    ):
        """
        ballot_num → highest ballot number we have promised (BallotNum)
                     (used to reject smaller ballots in prepare/accept)
        accept_num → ballot number we last accepted (AcceptNum)
        accept_val → value we accepted with accept_num (AcceptVal)

        These are exactly the three pieces of state described in the
        Paxos variables slide, tracked per node and per log depth.
        """
        if ballot_num is None:
            ballot_num = EMPTY_BALLOT
        if accept_num is None:
            accept_num = EMPTY_BALLOT

        self.ballot_num = ballot_num
        self.accept_num = accept_num
        self.accept_val = accept_val


class PaxosNodeState:
    def __init__(self, node_id: int):
        """
        node_id      → this node's id (1..5)
        instances    → mapping from depth -> AcceptorState
                       (one acceptor state per log slot / block depth)
        next_seq_num → sequence number counter used when creating new ballots
                       (first component of Ballot = (seq_num, node_id, depth))
        """
        self.node_id = node_id
        self.instances: dict[int, AcceptorState] = {}
        self.next_seq_num = 1  # start at 1, and increment for each new ballot

    def get_acceptor_state(self, depth: int) -> AcceptorState:
        """
        Return the AcceptorState for this depth, creating it if needed.

        This corresponds to “one Paxos instance per log entry”:
        each depth has its own BallotNum/AcceptNum/AcceptVal.
        """
        if depth not in self.instances:
            self.instances[depth] = AcceptorState()
        return self.instances[depth]

    def new_ballot(self, depth: int) -> Ballot:
        """
        Create a new unique ballot for this node at the given depth.

        Ballot = (seq_num, node_id, depth)
        - seq_num    → monotonically increasing per node
        - node_id    → breaks ties between nodes
        - depth      → makes ballots independent across log slots

        This matches the “choose new unique ballot number” step
        in Phase 1, where a proposer starts a new round.
        """
        seq = self.next_seq_num
        self.next_seq_num += 1
        return (seq, self.node_id, depth)

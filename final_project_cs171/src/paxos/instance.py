# src/paxos/instance.py
#
# This file defines PaxosInstance, which manages one Paxos consensus
# instance for a single depth (log index / block depth).
#
# Matches the “replicated log → replicated state machine” idea:
# one consensus instance per log slot / block depth (see replicated log diagrams). 
# For Paxos phases (prepare/accept/decide), this follows the basic skeleton
# from the Paxos lecture: Phase 1 (Prepare/Promise), Phase 2 (Accept/Accepted),
# Phase 3 (Decision).

from .messages import PaxosMessage, PaxosMessageType, Ballot
from .state import PaxosNodeState


class PaxosInstance:
    def __init__(
        self,
        depth: int,
        node_state: PaxosNodeState,
        peers,
        send_func,
        broadcast_func,
        on_decide,
    ):
        """
        depth          → which log index / block depth this instance is for
                         (one instance per log slot, as in the replicated-log view)
        node_state     → PaxosNodeState shared by this node (holds BallotNum/AcceptNum/AcceptVal)
        peers          → list of peer node ids (acceptor set; we’ll rely on majorities)
        send_func      → function(peer_id, PaxosMessage) used to send a message
        broadcast_func → function(PaxosMessage) used to send to all peers
        on_decide      → callback(depth, value) when a value is decided
        """
        self.depth = depth
        self.node_state = node_state
        self.peers = peers
        self.send_func = send_func
        self.broadcast_func = broadcast_func
        self.on_decide = on_decide

        # proposer-side fields (leader behavior from Phase 1/2 of Paxos)
        self.proposal_value = None       # value we want to propose
        self.proposal_ballot: Ballot | None = None  # unique ballot (n, proposer_id, depth)

        # track responses from peers (to count majorities like quorum slides)
        self.promises_received: dict[int, PaxosMessage] = {}
        self.accepted_received: dict[int, PaxosMessage] = {}

        # decision tracking (once decided, instance is “sealed” for this log depth)
        self.decided_value = None
        self.is_decided = False

    def start_proposal(self, value):
        """
        Entry point when this node wants to propose a value as leader.

        Milestone 2 (dummy Paxos):
          - choose a fresh ballot for this depth via PaxosNodeState
          - immediately broadcast DECIDE(value) to all peers
          - apply the decision locally

        Later milestones will replace this with the real Phase 1 (PREPARE/PROMISE)
        and Phase 2 (ACCEPT/ACCEPTED) logic.
        """
        if self.is_decided:
            print(f"[PAXOS depth={self.depth}] already decided, ignoring new proposal")
            return

        # Store the value and pick a new unique ballot for this depth.
        self.proposal_value = value
        self.proposal_ballot = self.node_state.new_ballot(self.depth)

        # Construct a DECIDE message as if we were a proper leader who already
        # went through prepare/accept phases. For Milestone 2 we skip straight
        # to the decision broadcast.
        decide_msg = PaxosMessage(
            msg_type=PaxosMessageType.DECIDE,
            from_id=self.node_state.node_id,
            ballot=self.proposal_ballot,
            depth=self.depth,
            value=value,
        )

        print(
            f"[PAXOS depth={self.depth}] Dummy start_proposal: "
            f"broadcasting DECIDE value={value!r}, ballot={self.proposal_ballot}",
            flush=True,
        )

        # Send DECIDE to all peers over the network
        self.broadcast_func(decide_msg)

        # And apply it locally so the leader also decides.
        self._on_decide(decide_msg)

    def handle_message(self, msg: PaxosMessage):
        """
        Called by Node when a Paxos message for this depth arrives.

        The routing by message type mirrors the three-phase consensus
        structure:
          - PREPARE / PROMISE → Phase 1
          - ACCEPT / ACCEPTED → Phase 2
          - DECIDE            → Phase 3
        """
        if msg.type == PaxosMessageType.PREPARE:
            self._on_prepare(msg)
        elif msg.type == PaxosMessageType.PROMISE:
            self._on_promise(msg)
        elif msg.type == PaxosMessageType.ACCEPT:
            self._on_accept(msg)
        elif msg.type == PaxosMessageType.ACCEPTED:
            self._on_accepted(msg)
        elif msg.type == PaxosMessageType.DECIDE:
            self._on_decide(msg)
        else:
            print(f"[PAXOS depth={self.depth}] unknown message type: {msg.type}")

    # The following handlers are all stubs for Milestone 1/2.
    # The real logic will mirror the pseudo-code for the proposer/acceptor
    # from the Paxos algorithm slides (BallotNum, AcceptNum, AcceptVal updates).

    def _on_prepare(self, msg: PaxosMessage):
        # Will eventually implement the “upon receive(prepare, bal)” logic for acceptors.
        print(f"[PAXOS depth={self.depth}] received PREPARE from {msg.from_id} [stub]")

    def _on_promise(self, msg: PaxosMessage):
        # Will eventually collect PROMISEs from a majority and choose value with highest AcceptNum.
        print(f"[PAXOS depth={self.depth}] received PROMISE from {msg.from_id} [stub]")

    def _on_accept(self, msg: PaxosMessage):
        # Will eventually implement the “upon receive(accept, b, v)” acceptor rule.
        print(f"[PAXOS depth={self.depth}] received ACCEPT from {msg.from_id} [stub]")

    def _on_accepted(self, msg: PaxosMessage):
        # Will eventually count ACCEPTEDs and decide once a majority has accepted v.
        print(f"[PAXOS depth={self.depth}] received ACCEPTED from {msg.from_id} [stub]")

    def _on_decide(self, msg: PaxosMessage):
        """
        Handle a DECIDE message:
        - mark local value as decided
        - call back into the node so it can update blockchain/accounts

        This matches the “Phase III: Announce Decision” step, where the
        leader broadcasts the chosen value and each replica updates its
        state machine / log in the same order.
        """
        if self.is_decided:
            return

        self.is_decided = True
        self.decided_value = msg.value
        print(f"[PAXOS depth={self.depth}] DECIDE value={msg.value!r}")

        # Notify the owning Node that a value has been decided at this depth.
        self.on_decide(self.depth, msg.value)

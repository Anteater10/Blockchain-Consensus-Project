# src/paxos/instance.py
#
# This file defines PaxosInstance, which manages one Paxos consensus
# instance for a single depth (log index / block depth).
#
# Matches the “replicated log → replicated state machine” idea:
# one consensus instance per log slot / block depth.
#
# Phases:
#   - Phase 1: PREPARE / PROMISE
#   - Phase 2: ACCEPT / ACCEPTED
#   - Phase 3: DECIDE

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
        on_tentative=None,
        get_first_uncommitted=None,
        repair_callback=None,
    ):
        """
        depth               → which log index / block depth this instance is for
        node_state          → PaxosNodeState shared by this node
        peers               → list of peer node ids (other acceptors; self is implicit)
        send_func           → function(peer_id, PaxosMessage) to send a message
        broadcast_func      → function(PaxosMessage) to send to all peers
        on_decide           → callback(depth, value) when a value is decided
        on_tentative        → callback(depth, value) when this node *accepts* a value
                               (used to log tentative blocks to disk)
        get_first_uncommitted → callable returning this node's first_uncommitted_index
                                (used for recovery hints in messages)
        repair_callback     → callable(peer_id, peer_index, local_index) used to
                               trigger repair (push/pull) based on indices
        """
        self.depth = depth
        self.node_state = node_state
        self.peers = peers
        self.send_func = send_func
        self.broadcast_func = broadcast_func
        self.on_decide = on_decide
        self.on_tentative = on_tentative
        self.get_first_uncommitted = get_first_uncommitted
        self.repair_callback = repair_callback

        # proposer-side fields
        self.proposal_value = None              # value we want to propose (e.g., a Block)
        self.proposal_ballot: Ballot | None = None  # unique ballot (seq, proposer_id, depth)

        # track responses from peers
        self.promises_received: dict[int, PaxosMessage] = {}
        self.accepted_received: dict[int, PaxosMessage] = {}

        # decision tracking
        self.decided_value = None
        self.is_decided = False

    # -------------------------------------------------------------------------
    # Helper: majority / quorum size
    # -------------------------------------------------------------------------

    def _quorum_size(self) -> int:
        """
        Return the number of votes needed for a majority.

        Total nodes = len(peers) + 1 (including self).
        Majority    = floor(N/2) + 1.
        """
        total = len(self.peers) + 1
        return total // 2 + 1

    def _current_first_uncommitted(self) -> int | None:
        """
        Helper to fetch the node's current first_uncommitted_index
        via the callback provided by Node.
        """
        if self.get_first_uncommitted is None:
            return None
        return self.get_first_uncommitted()

    # -------------------------------------------------------------------------
    # Proposer entrypoint (Phase 1a: PREPARE)
    # -------------------------------------------------------------------------

    def start_proposal(self, value):
        """
        Entry point when this node wants to propose a value as leader.

        Implements Phase 1a (PREPARE):
          - choose a fresh ballot via PaxosNodeState.new_ballot(depth)
          - seed a local PROMISE from our own acceptor state
          - send PREPARE(ballot) to all peers
        """
        if self.is_decided:
            print(f"[PAXOS depth={self.depth}] already decided, ignoring new proposal")
            return

        # Choose a fresh ballot and store the value we want to propose.
        self.proposal_value = value
        self.proposal_ballot = self.node_state.new_ballot(self.depth)

        # Clear any old responses from previous rounds.
        self.promises_received.clear()
        self.accepted_received.clear()

        print(
            f"[PAXOS depth={self.depth}] start_proposal: ballot={self.proposal_ballot}, "
            f"value={value!r}",
            flush=True,
        )

        # 1) Seed a local PROMISE from our own acceptor (self is also an acceptor).
        acc = self.node_state.get_acceptor_state(self.depth)
        # Only "promise" if this ballot is >= our current BallotNum.
        if self.proposal_ballot >= acc.ballot_num:
            acc.ballot_num = self.proposal_ballot
            local_promise = PaxosMessage(
                msg_type=PaxosMessageType.PROMISE,
                from_id=self.node_state.node_id,
                ballot=self.proposal_ballot,
                depth=self.depth,
                accept_num=acc.accept_num,
                accept_val=acc.accept_val,
                first_uncommitted=self._current_first_uncommitted(),
            )
            # Directly handle our own PROMISE (no network hop).
            self._on_promise(local_promise)
        else:
            # If we can't even promise to ourselves, this round is doomed.
            print(
                f"[PAXOS depth={self.depth}] local acceptor refused ballot {self.proposal_ballot}, "
                f"current BallotNum={acc.ballot_num}",
                flush=True,
            )
            return

        # 2) Send PREPARE to all peers.
        prepare_msg = PaxosMessage(
            msg_type=PaxosMessageType.PREPARE,
            from_id=self.node_state.node_id,
            ballot=self.proposal_ballot,
            depth=self.depth,
            first_uncommitted=self._current_first_uncommitted(),
        )
        self.broadcast_func(prepare_msg)

    # -------------------------------------------------------------------------
    # Message routing
    # -------------------------------------------------------------------------

    def handle_message(self, msg: PaxosMessage):
        """
        Called by Node when a Paxos message for this depth arrives.
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

    # -------------------------------------------------------------------------
    # Phase 1b: acceptor handling PREPARE, sending PROMISE
    # -------------------------------------------------------------------------

    def _on_prepare(self, msg: PaxosMessage):
        """
        Acceptor logic for PREPARE(ballot):
          - if ballot < BallotNum: ignore
          - else:
              BallotNum = ballot
              reply PROMISE(ballot, AcceptNum, AcceptVal)
        """
        acc = self.node_state.get_acceptor_state(self.depth)

        if msg.ballot < acc.ballot_num:
            # Ignore smaller ballots.
            print(
                f"[PAXOS depth={self.depth}] PREPARE from {msg.from_id} with ballot={msg.ballot} "
                f"rejected (BallotNum={acc.ballot_num})",
                flush=True,
            )
            return

        # Promise to not accept proposals with smaller ballot.
        acc.ballot_num = msg.ballot
        promise = PaxosMessage(
            msg_type=PaxosMessageType.PROMISE,
            from_id=self.node_state.node_id,
            ballot=msg.ballot,
            depth=self.depth,
            accept_num=acc.accept_num,
            accept_val=acc.accept_val,
            first_uncommitted=self._current_first_uncommitted(),
        )

        print(
            f"[PAXOS depth={self.depth}] PREPARE from {msg.from_id} accepted, "
            f"sending PROMISE with accept_num={acc.accept_num}, accept_val={acc.accept_val!r}",
            flush=True,
        )

        # Send PROMISE back to proposer.
        self.send_func(msg.from_id, promise)

    # -------------------------------------------------------------------------
    # Phase 1b (proposer side): collecting PROMISEs
    # -------------------------------------------------------------------------

    def _on_promise(self, msg: PaxosMessage):
        """
        Proposer logic on receiving PROMISE(ballot, AcceptNum, AcceptVal):

        - Only consider PROMISEs for our current proposal_ballot.
        - Once we reach a quorum:
            - choose value:
                - if any PROMISE has a non-None AcceptVal, pick the one with
                  highest AcceptNum
                - else use our original proposal_value
            - send ACCEPT(ballot, value) to all
            - seed local ACCEPTED from our own acceptor
        """
        if self.is_decided:
            return

        if self.proposal_ballot is None:
            # We're not currently proposing anything.
            print(
                f"[PAXOS depth={self.depth}] PROMISE from {msg.from_id} ignored: "
                f"no active proposal",
                flush=True,
            )
            return

        if msg.ballot != self.proposal_ballot:
            # Old round or different ballot; ignore.
            print(
                f"[PAXOS depth={self.depth}] PROMISE from {msg.from_id} ignored: "
                f"ballot mismatch (msg={msg.ballot}, ours={self.proposal_ballot})",
                flush=True,
            )
            return

        if msg.from_id in self.promises_received:
            # Duplicate PROMISE; ignore.
            return

        self.promises_received[msg.from_id] = msg

        print(
            f"[PAXOS depth={self.depth}] PROMISE from {msg.from_id} "
            f"(total={len(self.promises_received)}/{self._quorum_size()})",
            flush=True,
        )

        # Check if we have a quorum of PROMISEs.
        if len(self.promises_received) < self._quorum_size():
            return

        # We have a majority of PROMISEs. Choose the value to propose in ACCEPT.
        # If any PROMISE reports a prior accepted value, pick the one with
        # highest AcceptNum. Otherwise, keep our original proposal_value.
        chosen_value = self.proposal_value
        highest_accept_num: Ballot | None = None

        for p in self.promises_received.values():
            if p.accept_val is not None and p.accept_num is not None:
                if highest_accept_num is None or p.accept_num > highest_accept_num:
                    highest_accept_num = p.accept_num
                    chosen_value = p.accept_val

        self.proposal_value = chosen_value

        print(
            f"[PAXOS depth={self.depth}] PROMISE quorum reached, "
            f"chosen_value={chosen_value!r}, highest_accept_num={highest_accept_num}",
            flush=True,
        )

        # Send ACCEPT(ballot, chosen_value) to all peers.
        accept_msg = PaxosMessage(
            msg_type=PaxosMessageType.ACCEPT,
            from_id=self.node_state.node_id,
            ballot=self.proposal_ballot,
            depth=self.depth,
            value=chosen_value,
            first_uncommitted=self._current_first_uncommitted(),
        )
        self.broadcast_func(accept_msg)

        # Seed local ACCEPTED from our own acceptor.
        acc = self.node_state.get_acceptor_state(self.depth)
        if self.proposal_ballot >= acc.ballot_num:
            acc.ballot_num = self.proposal_ballot
            acc.accept_num = self.proposal_ballot
            acc.accept_val = chosen_value

            # Log tentative for the leader's own acceptance
            if self.on_tentative is not None and chosen_value is not None:
                self.on_tentative(self.depth, chosen_value)

            local_accepted = PaxosMessage(
                msg_type=PaxosMessageType.ACCEPTED,
                from_id=self.node_state.node_id,
                ballot=self.proposal_ballot,
                depth=self.depth,
                value=chosen_value,
                first_uncommitted=self._current_first_uncommitted(),
            )
            self._on_accepted(local_accepted)

    # -------------------------------------------------------------------------
    # Phase 2b: acceptor handling ACCEPT, sending ACCEPTED
    # -------------------------------------------------------------------------

    def _on_accept(self, msg: PaxosMessage):
        """
        Acceptor logic for ACCEPT(ballot, value):

        - if ballot < BallotNum: ignore
        - else:
            BallotNum = ballot
            AcceptNum = ballot
            AcceptVal = value
            reply ACCEPTED(ballot, value)
        """
        acc = self.node_state.get_acceptor_state(self.depth)

        if msg.ballot < acc.ballot_num:
            print(
                f"[PAXOS depth={self.depth}] ACCEPT from {msg.from_id} with ballot={msg.ballot} "
                f"rejected (BallotNum={acc.ballot_num})",
                flush=True,
            )
            return

        # Accept this value.
        acc.ballot_num = msg.ballot
        acc.accept_num = msg.ballot
        acc.accept_val = msg.value

        accepted = PaxosMessage(
            msg_type=PaxosMessageType.ACCEPTED,
            from_id=self.node_state.node_id,
            ballot=msg.ballot,
            depth=self.depth,
            value=msg.value,
            first_uncommitted=self._current_first_uncommitted(),
        )

        print(
            f"[PAXOS depth={self.depth}] ACCEPT from {msg.from_id} accepted, "
            f"sending ACCEPTED for value={msg.value!r}",
            flush=True,
        )

        self.send_func(msg.from_id, accepted)

        # Log this as a tentative acceptance on this node
        if self.on_tentative is not None and msg.value is not None:
            self.on_tentative(self.depth, msg.value)

    # -------------------------------------------------------------------------
    # Phase 2b (proposer side): collecting ACCEPTEDs
    # -------------------------------------------------------------------------

    def _on_accepted(self, msg: PaxosMessage):
        """
        Proposer logic on receiving ACCEPTED(ballot, value):

        - Only consider ACCEPTEDs for our current proposal_ballot.
        - Use first_uncommitted_index hints to drive repair.
        - Once we reach a quorum, broadcast DECIDE(value) and
          apply it locally.
        """
        if self.is_decided:
            return

        if self.proposal_ballot is None:
            print(
                f"[PAXOS depth={self.depth}] ACCEPTED from {msg.from_id} ignored: "
                f"no active proposal",
                flush=True,
            )
            return

        if msg.ballot != self.proposal_ballot:
            print(
                f"[PAXOS depth={self.depth}] ACCEPTED from {msg.from_id} ignored: "
                f"ballot mismatch (msg={msg.ballot}, ours={self.proposal_ballot})",
                flush=True,
            )
            return

        if msg.from_id in self.accepted_received:
            # Duplicate ACCEPTED; ignore.
            return

        self.accepted_received[msg.from_id] = msg

        # Use first_uncommitted_index hint for eager repair.
        if msg.first_uncommitted is not None and self.repair_callback is not None:
            local_idx = self._current_first_uncommitted()
            peer_idx = int(msg.first_uncommitted)
            if local_idx is not None and peer_idx != local_idx:
                # Delegate repair logic to Node.
                self.repair_callback(msg.from_id, peer_idx, local_idx)

        print(
            f"[PAXOS depth={self.depth}] ACCEPTED from {msg.from_id} "
            f"(total={len(self.accepted_received)}/{self._quorum_size()})",
            flush=True,
        )

        # Check if we have a quorum of ACCEPTEDs.
        if len(self.accepted_received) < self._quorum_size():
            return

        # Majority has accepted our value; broadcast DECIDE.
        decide_msg = PaxosMessage(
            msg_type=PaxosMessageType.DECIDE,
            from_id=self.node_state.node_id,
            ballot=self.proposal_ballot,
            depth=self.depth,
            value=self.proposal_value,
            first_uncommitted=self._current_first_uncommitted(),
        )

        print(
            f"[PAXOS depth={self.depth}] ACCEPTED quorum reached, broadcasting DECIDE "
            f"value={self.proposal_value!r}",
            flush=True,
        )

        self.broadcast_func(decide_msg)
        # Apply decision locally as well.
        self._on_decide(decide_msg)

    # -------------------------------------------------------------------------
    # Phase 3: DECIDE handling
    # -------------------------------------------------------------------------

    def _on_decide(self, msg: PaxosMessage):
        """
        Handle a DECIDE message:
        - mark local value as decided
        - call back into the node so it can update blockchain/accounts
        """
        if self.is_decided:
            return

        self.is_decided = True
        self.decided_value = msg.value
        print(f"[PAXOS depth={self.depth}] DECIDE value={msg.value!r}", flush=True)

        # Notify the owning Node that a value has been decided at this depth.
        self.on_decide(self.depth, msg.value)

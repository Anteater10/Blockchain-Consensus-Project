# src/node.py
# This file starts a single node in the system. For now it just loads config,
# sets up local blockchain + accounts, and runs a small local test.
#
# Milestone 1:
#   - local blockchain + accounts
#   - Paxos state + instance skeleton
#   - stubbed network hooks for Paxos (no real networking yet)

import argparse
import json
import sys
from pathlib import Path

from blockchain.chain import Blockchain
from accounts.accounts import AccountsTable
from paxos.state import PaxosNodeState
from paxos.instance import PaxosInstance
from paxos.messages import PaxosMessage


class NodeConfig:
    def __init__(self, node_id, host, port, data_dir):
        self.id = node_id
        self.host = host
        self.port = port
        self.data_dir = data_dir


class Node:
    def __init__(self, config, peers):
        self.config = config       # NodeConfig for this node
        self.peers = peers         # list of NodeConfig for other nodes

        # make sure data directory exists
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # paths for future persistence (used in later milestones)
        self.blockchain_path = self.config.data_dir / "blockchain.json"
        self.balances_path = self.config.data_dir / "balances.json"

        # create empty files for now (we will fill them in Milestone 2)
        if not self.blockchain_path.exists():
            self.blockchain_path.write_text("[]", encoding="utf-8")

        if not self.balances_path.exists():
            self.balances_path.write_text("{}", encoding="utf-8")

        # local in-memory state (Milestone 1)
        self.blockchain = Blockchain()
        self.accounts = AccountsTable.fresh()

        # Paxos node-wide state (BallotNum / AcceptNum / AcceptVal per depth)
        self.paxos_state = PaxosNodeState(self.config.id)
        # depth -> PaxosInstance
        self.paxos_instances = {}

    # -------------------------------------------------------------------------
    # Paxos integration stubs (Milestone 1)
    # -------------------------------------------------------------------------

    def _get_paxos_instance(self, depth):
        """
        Return the PaxosInstance for a given depth, creating it if needed.

        send_func / broadcast_func are currently stubbed to just print;
        real networking will be plugged in during Milestone 2.
        """
        if depth not in self.paxos_instances:
            peer_ids = [p.id for p in self.peers]
            inst = PaxosInstance(
                depth=depth,
                node_state=self.paxos_state,
                peers=peer_ids,
                send_func=self._send_paxos_to_peer,
                broadcast_func=self._broadcast_paxos,
                on_decide=self._on_paxos_decide,
            )
            self.paxos_instances[depth] = inst
        return self.paxos_instances[depth]

    def start_paxos(self, depth, value):
        """
        Milestone 1 stub entry point for proposing a value at a given depth.

        Later milestones will call this from CLI (e.g., moneyTransfer) with a
        Block as 'value'. For now it just prints and does nothing else.
        """
        inst = self._get_paxos_instance(depth)
        inst.start_proposal(value)

    def _on_paxos_decide(self, depth, value):
        """
        Callback invoked by PaxosInstance when a DECIDE is delivered.

        Milestone 1: only logs. Milestone 3: will treat 'value' as a Block
        and call apply_decided_block on the blockchain layer.
        """
        print(
            f"[NODE {self.config.id}] DECIDED depth={depth}, value={value!r}",
            flush=True,
        )

    def _send_paxos_to_peer(self, peer_id, msg):
        """
        Stub send function passed into PaxosInstance.

        'msg' is a PaxosMessage. For Milestone 1, we just print the dict
        form instead of doing real networking.
        """
        if not isinstance(msg, PaxosMessage):
            # guard against misuse later
            print(
                f"[NODE {self.config.id}] _send_paxos_to_peer got non-PaxosMessage: {msg}",
                flush=True,
            )
            return

        print(
            f"[NODE {self.config.id}] send_to_peer({peer_id}, {msg.to_dict()}) [stub]",
            flush=True,
        )

    def _broadcast_paxos(self, msg):
        """
        Stub broadcast function passed into PaxosInstance.

        'msg' is a PaxosMessage. In Milestone 2, this will call the NetworkClient
        to actually send to all peers.
        """
        if not isinstance(msg, PaxosMessage):
            print(
                f"[NODE {self.config.id}] _broadcast_paxos got non-PaxosMessage: {msg}",
                flush=True,
            )
            return

        print(
            f"[NODE {self.config.id}] broadcast({msg.to_dict()}) [stub]",
            flush=True,
        )

    async def handle_incoming_paxos_dict(self, d):
        """
        Future hook for the network server: given an incoming JSON dict,
        decode into a PaxosMessage and route it to the correct PaxosInstance.

        This is not used in Milestone 1 yet, but it's ready for when you wire
        up network.server.start_server in Milestone 2.
        """
        msg = PaxosMessage.from_dict(d)
        inst = self._get_paxos_instance(msg.depth)
        inst.handle_message(msg)

    # -------------------------------------------------------------------------
    # Existing Milestone 1 local test
    # -------------------------------------------------------------------------

    def print_summary(self):
        print("=== Node Startup Summary ===")
        print(f"  Node ID     : {self.config.id}")
        print(f"  Host        : {self.config.host}")
        print(f"  Port        : {self.config.port}")
        print(f"  Data dir    : {self.config.data_dir}")
        print(f"  Peers       : {[p.id for p in self.peers]}")
        print("============================")

    def run_local_test(self):
        """
        Simple Milestone 1 test:
        - create a tx (P1 -> P2, 10)
        - build + append a block
        - apply tx to accounts
        - print results
        """
        print("\n[Local Test] Creating a block locally...\n")

        tx = ("P1", "P2", 10)

        if not self.accounts.can_debit("P1", 10):
            print("Error: P1 cannot pay 10")
            return

        # create + append block
        block = self.blockchain.new_block_for_tx(tx)
        self.blockchain.append_block(block)

        # apply transaction to account balances
        self.accounts.apply_transaction(tx)

        # show block info
        print(f"New block at depth {block.depth}")
        print(f"  tx     : {block.tx}")
        print(f"  nonce  : {block.nonce}")
        print(f"  hash   : {block.hash}")
        print(f"  prev   : {block.prev_hash}")

        # show balances
        print("\nUpdated balances:")
        for cid, bal in self.accounts.balances.items():
            print(f"  {cid}: {bal}")


def load_config(config_path, my_id):
    """
    Read config/nodes.json and return:
      - the NodeConfig for this node (my_id)
      - a list of NodeConfig for all peers
    """
    try:
        text = config_path.read_text(encoding="utf-8")
        raw = json.loads(text)
    except FileNotFoundError:
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    nodes = []
    for entry in raw:
        node_cfg = NodeConfig(
            node_id=int(entry["id"]),
            host=str(entry["host"]),
            port=int(entry["port"]),
            data_dir=Path(entry["data_dir"]),
        )
        nodes.append(node_cfg)

    me = None
    peers = []
    for n in nodes:
        if n.id == my_id:
            me = n
        else:
            peers.append(n)

    if me is None:
        print(f"ERROR: no node with id={my_id} in {config_path}", file=sys.stderr)
        sys.exit(1)

    return me, peers


def parse_args():
    parser = argparse.ArgumentParser(description="CS171 Final Project Node")
    parser.add_argument("--id", type=int, required=True, help="Node ID (1-5)")
    parser.add_argument(
        "--config",
        type=str,
        default="config/nodes.json",
        help="Path to nodes config JSON",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)

    me, peers = load_config(config_path, args.id)
    node = Node(me, peers)
    node.print_summary()

    # Milestone 1 test call
    node.run_local_test()

    # Later milestones will:
    #   - start asyncio server
    #   - connect peers
    #   - run event loop forever


if __name__ == "__main__":
    main()

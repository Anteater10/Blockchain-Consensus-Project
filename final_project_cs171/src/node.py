# src/node.py
# This file starts a single node in the system. It loads config,
# sets up local blockchain + accounts, and (for Milestone 2) runs
# a networked Paxos dummy test.
#
# Milestone 1:
#   - local blockchain + accounts
#   - Paxos state + instance skeleton
#   - stubbed network hooks for Paxos (no real networking yet)
#
# Milestone 2:
#   - Person A: load/save blockchain + balances
#   - Person B: networking skeleton + dummy Paxos over the network

import argparse
import json
import sys
import asyncio
from pathlib import Path

from .blockchain.chain import Blockchain
from .accounts.accounts import AccountsTable
from .paxos.state import PaxosNodeState
from .paxos.instance import PaxosInstance
from .paxos.messages import PaxosMessage
from .storage.storage import (
    save_blockchain,
    load_blockchain,
    save_balances,
    load_balances,
)
from .blockchain.block import Block
from .network.server import start_server
from .network.client import NetworkClient
from .cli.commands import run_cli


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

        # paths for persistence
        self.blockchain_path = self.config.data_dir / "blockchain.json"
        self.balances_path = self.config.data_dir / "balances.json"

        # load existing state if present, otherwise start fresh
        self.blockchain: Blockchain = load_blockchain(self.blockchain_path)
        self.accounts: AccountsTable = load_balances(self.balances_path)

        # Paxos node-wide state (BallotNum / AcceptNum / AcceptVal per depth)
        self.paxos_state = PaxosNodeState(self.config.id)
        # depth -> PaxosInstance
        self.paxos_instances: dict[int, PaxosInstance] = {}

        # Networking: server + outgoing client
        self.server: asyncio.AbstractServer | None = None
        self.net_client: NetworkClient | None = None

    # -------------------------------------------------------------------------
    # Helper: build peer map for NetworkClient
    # -------------------------------------------------------------------------

    def _build_peer_map(self) -> dict[int, tuple[str, int]]:
        """
        Build a mapping { node_id -> (host, port) } including self and peers.

        Used by NetworkClient so it knows how to connect to everyone.
        """
        peers: dict[int, tuple[str, int]] = {}
        peers[self.config.id] = (self.config.host, self.config.port)
        for p in self.peers:
            peers[p.id] = (p.host, p.port)
        return peers

    # -------------------------------------------------------------------------
    # Paxos integration (now with real networking hooks)
    # -------------------------------------------------------------------------

    def _get_paxos_instance(self, depth):
        """
        Return the PaxosInstance for a given depth, creating it if needed.

        send_func / broadcast_func now call into the NetworkClient so that
        Paxos messages are actually sent over TCP.
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
        Entry point for proposing a value at a given depth.

        For Milestone 3, 'value' is typically a Block (or Block dict)
        representing a transaction to be appended at this depth.
        """
        inst = self._get_paxos_instance(depth)
        inst.start_proposal(value)


    def _on_paxos_decide(self, depth, value):
        """
        Callback invoked by PaxosInstance when a DECIDE is delivered.

        For Milestone 3, 'value' is the decided Block (usually serialized
        as a dict over the network). Here we:
          - reconstruct the Block
          - append it to the local chain
          - apply the transaction to accounts
          - persist blockchain + balances to disk
        """
        print(
            f"[NODE {self.config.id}] DECIDED depth={depth}, value={value!r}",
            flush=True,
        )

        # 1) Rebuild Block from value
        if isinstance(value, dict):
            try:
                block = Block.from_dict(value)
            except Exception as e:
                print(
                    f"[NODE {self.config.id}] ERROR reconstructing Block from value: {e}",
                    flush=True,
                )
                return
        elif isinstance(value, Block):
            block = value
        else:
            print(
                f"[NODE {self.config.id}] Unexpected decided value type: {type(value)}",
                flush=True,
            )
            return

        # Optional sanity check: depth agreement
        if block.depth != depth:
            print(
                f"[NODE {self.config.id}] WARNING: decided depth mismatch: "
                f"block.depth={block.depth}, slot={depth}",
                flush=True,
            )

        # 2) Append block to blockchain (this enforces depth/prev_hash checks)
        try:
            self.blockchain.append_block(block)
        except ValueError as e:
            # This can happen if we've already appended this block or chain diverged.
            print(
                f"[NODE {self.config.id}] ERROR appending decided block at depth={depth}: {e}",
                flush=True,
            )
            return

        # 3) Apply the transaction to account balances
        sender, receiver, amount = block.tx
        # At this point, we assume tx was valid when it was proposed.
        self.accounts.apply_transaction(block.tx)

        # 4) Persist new state to disk
        save_blockchain(self.blockchain, self.blockchain_path)
        save_balances(self.accounts, self.balances_path)

        print(
            f"[NODE {self.config.id}] Applied decided block at depth={block.depth}: "
            f"{sender} -> {receiver}, amount={amount}",
            flush=True,
        )


    def _send_paxos_to_peer(self, peer_id, msg: PaxosMessage):
        """
        Send a PaxosMessage to a single peer over the network.

        This is the send_func passed into PaxosInstance. It wraps the
        async NetworkClient.send_to_peer in an asyncio task so that
        PaxosInstance can remain synchronous.
        """
        if not isinstance(msg, PaxosMessage):
            print(
                f"[NODE {self.config.id}] _send_paxos_to_peer got non-PaxosMessage: {msg}",
                flush=True,
            )
            return

        if self.net_client is None:
            print(
                f"[NODE {self.config.id}] net_client not ready; dropping send_to_peer({peer_id}, {msg.to_dict()})",
                flush=True,
            )
            return

        async def _run():
            await self.net_client.send_to_peer(peer_id, msg.to_dict())

        asyncio.create_task(_run())

    def _broadcast_paxos(self, msg: PaxosMessage):
        """
        Broadcast a PaxosMessage to all peers over the network.

        This is the broadcast_func passed into PaxosInstance.
        """
        if not isinstance(msg, PaxosMessage):
            print(
                f"[NODE {self.config.id}] _broadcast_paxos got non-PaxosMessage: {msg}",
                flush=True,
            )
            return

        if self.net_client is None:
            print(
                f"[NODE {self.config.id}] net_client not ready; dropping broadcast({msg.to_dict()})",
                flush=True,
            )
            return

        async def _run():
            await self.net_client.broadcast(msg.to_dict())

        asyncio.create_task(_run())

    async def handle_incoming_paxos_dict(self, d):
        """
        Network server hook: given an incoming JSON dict,
        decode into a PaxosMessage and route it to the correct PaxosInstance.
        """
        msg = PaxosMessage.from_dict(d)
        inst = self._get_paxos_instance(msg.depth)
        inst.handle_message(msg)
    
    # -------------------------------------------------------------------------
    # Application-level entrypoint: money transfer → Paxos proposal
    # -------------------------------------------------------------------------

    def handle_money_transfer(self, debit_id: str, credit_id: str, amount: int):
        """
        Handle a user-initiated money transfer.

        - debit_id, credit_id are account ids like "P1", "P2"
        - amount is an integer

        This builds a candidate Block and starts Paxos at the next depth.
        """
        # 1) Check that the debit account can pay
        if not self.accounts.can_debit(debit_id, amount):
            print(
                f"[NODE {self.config.id}] Insufficient funds in {debit_id} "
                f"for amount={amount}",
                flush=True,
            )
            return

        tx = (debit_id, credit_id, amount)
        depth = self.blockchain.length()

        # 2) Build candidate block using local blockchain logic (includes PoW)
        block = self.blockchain.new_block_for_tx(tx)

        print(
            f"[NODE {self.config.id}] Proposing tx={tx} at depth={depth}",
            flush=True,
        )

        # 3) For Paxos, send a JSON-friendly representation
        #    so PaxosMessage.to_dict() / from_dict() can serialize it.
        self.start_paxos(depth=depth, value=block.to_dict())


    # -------------------------------------------------------------------------
    # Printing + local test (Person A: state + storage)
    # -------------------------------------------------------------------------

    def print_summary(self):
        print("=== Node Startup Summary ===")
        print(f"  Node ID     : {self.config.id}")
        print(f"  Host        : {self.config.host}")
        print(f"  Port        : {self.config.port}")
        print(f"  Data dir    : {self.config.data_dir}")
        print(f"  Peers       : {[p.id for p in self.peers]}")
        print("============================")

    def print_blockchain(self):
        """
        Print all blocks in the blockchain in a readable way.
        """
        print("\n=== Blockchain ===")
        if len(self.blockchain.blocks) == 0:
            print("(empty)")
            return

        for b in self.blockchain.blocks:
            sender, receiver, amount = b.tx
            print(f"- depth   : {b.depth}")
            print(f"  tx      : {sender} -> {receiver}, amount={amount}")
            print(f"  nonce   : {b.nonce}")
            print(f"  hash    : {b.hash}")
            print(f"  prev    : {b.prev_hash}")
            print("")

    def print_balances(self):
        """
        Print account balances.
        """
        print("\n=== Balances ===")
        for cid, bal in self.accounts.balances.items():
            print(f"  {cid}: {bal}")

    def run_local_test(self):
        """
        Simple Milestone 1+2 test:
        - create a tx (P1 -> P2, 10)
        - build + append a block
        - apply tx to accounts
        - save to disk
        - print results

        This is local-only and does not involve Paxos/networking.
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

        # save new state to disk
        save_blockchain(self.blockchain, self.blockchain_path)
        save_balances(self.accounts, self.balances_path)

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

    # -------------------------------------------------------------------------
    # Milestone 2: async networking entrypoint (Person B)
    # -------------------------------------------------------------------------

    async def run_network(self):
        """
        Network runner:

        - Start the asyncio server to receive Paxos messages
        - Connect to peers using NetworkClient
        - Start CLI loop (reads commands from stdin)
        - Then keep the event loop alive
        """
        # 1) Start server for incoming Paxos messages
        self.server = await start_server(
            self.config.host,
            self.config.port,
            self.handle_incoming_paxos_dict,
        )

        # 2) Set up NetworkClient and connect to peers
        peer_map = self._build_peer_map()
        self.net_client = NetworkClient(self.config.id, peer_map)
        await self.net_client.connect_peers()

        print(f"[NODE {self.config.id}] Network initialized", flush=True)

        # 3) Start CLI loop in background
        asyncio.create_task(run_cli(self))

        # 4) Keep running forever
        await asyncio.Event().wait()




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

    # For Milestone 2, we run the async networking skeleton instead of
    # the local-only blockchain test.
    asyncio.run(node.run_network())

    # If you still want to sanity-check storage locally, you can
    # temporarily call:
    #   node.run_local_test()


if __name__ == "__main__":
    main()

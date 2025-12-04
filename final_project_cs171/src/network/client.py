# src/network/client.py
#
# Networking "client" for a node: outgoing connections to peers.
#
# Milestone 1: this is a stub. It knows how to:
#   - connect to each peer via asyncio.open_connection
#   - send JSON messages to a single peer
#   - broadcast a JSON message to all peers
#
# Later milestones will add:
#   - reconnect logic
#   - integration with Paxos messages (PaxosMessage.to_dict())
#   - proper error handling / graceful shutdown

import asyncio
from typing import Dict, List, Tuple, Callable, Awaitable, Any

from .protocol import send_json


PeerInfo = Tuple[str, int]  # (host, port)


class NetworkClient:
    def __init__(
        self,
        node_id: int,
        peers: Dict[int, PeerInfo],
    ) -> None:
        """
        node_id → this node's id (1..5)
        peers   → mapping from peer_id -> (host, port)

        Example:
            peers = {
                1: ("127.0.0.1", 8001),
                2: ("127.0.0.1", 8002),
                ...
            }
        """
        self.node_id = node_id
        self.peers = peers  # includes all nodes; caller can exclude self if desired

        # Established outgoing connections: peer_id -> StreamWriter
        self._peer_writers: Dict[int, asyncio.StreamWriter] = {}

    async def connect_peers(self) -> None:
        """
        Connect to all peers in the 'peers' dict, ignoring failures for now.

        Milestone 1: no retry loop, no backoff, no fancy logging.
        Just a straightforward attempt to connect to each peer once.
        """
        for pid, (host, port) in self.peers.items():
            if pid == self.node_id:
                continue
            try:
                reader, writer = await asyncio.open_connection(host, port)
                self._peer_writers[pid] = writer
                print(
                    f"[NET {self.node_id}] Connected to peer {pid} at {host}:{port}",
                    flush=True,
                )
            except Exception as e:
                # Milestone 1 stub: print and move on.
                print(
                    f"[NET {self.node_id}] Failed to connect to peer {pid} at {host}:{port}: {e}",
                    flush=True,
                )

    async def send_to_peer(self, peer_id: int, msg: Dict[str, Any]) -> None:
        """
        Send a JSON-serializable dict to a single peer.

        In later milestones, 'msg' will usually be PaxosMessage.to_dict().
        """
        writer = self._peer_writers.get(peer_id)
        if writer is None:
            print(
                f"[NET {self.node_id}] No connection to peer {peer_id}; dropping message: {msg}",
                flush=True,
            )
            return

        try:
            await send_json(writer, msg)
        except Exception as e:
            print(
                f"[NET {self.node_id}] Error sending to peer {peer_id}: {e}",
                flush=True,
            )

    async def broadcast(self, msg: Dict[str, Any]) -> None:
        """
        Send the same message to all connected peers.

        Milestone 1: simple loop. Later you can make this smarter or
        incorporate NETWORK_DELAY, but this is enough to satisfy your
        'broadcast(msg)' stub contract.
        """
        for pid, writer in list(self._peer_writers.items()):
            try:
                await send_json(writer, msg)
            except Exception as e:
                print(
                    f"[NET {self.node_id}] Error broadcasting to peer {pid}: {e}",
                    flush=True,
                )

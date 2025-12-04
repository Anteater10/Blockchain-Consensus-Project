# src/network/client.py
#
# Networking "client" for a node: outgoing connections to peers.
#
# Milestone 1: this is a stub. It knows how to:
#   - connect to each peer via asyncio.open_connection
#   - send JSON messages to a single peer
#   - broadcast a JSON message to all peers
#
# Milestone 2:
#   - use send_json_with_delay so every message experiences NETWORK_DELAY
#
# Later milestones will add:
#   - reconnect logic
#   - integration with Paxos messages (PaxosMessage.to_dict())
#   - proper error handling / graceful shutdown

import asyncio
from typing import Dict, Tuple, Any

from .protocol import send_json_with_delay

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

        Milestone 1/2: no retry loop, no backoff, no fancy logging.
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
                # Stub: print and move on.
                print(
                    f"[NET {self.node_id}] Failed to connect to peer {pid} at {host}:{port}: {e}",
                    flush=True,
                )

    async def send_to_peer(self, peer_id: int, msg: Dict[str, Any]) -> None:
        """
        Send a JSON-serializable dict to a single peer.

        In later milestones, 'msg' will usually be PaxosMessage.to_dict().

        Milestone 2: every send uses send_json_with_delay, which applies
        NETWORK_DELAY before actually writing.
        """
        writer = self._peer_writers.get(peer_id)
        if writer is None:
            print(
                f"[NET {self.node_id}] No connection to peer {peer_id}; dropping message: {msg}",
                flush=True,
            )
            return

        try:
            await send_json_with_delay(writer, msg)
        except Exception as e:
            print(
                f"[NET {self.node_id}] Error sending to peer {peer_id}: {e}",
                flush=True,
            )

    async def broadcast(self, msg: Dict[str, Any]) -> None:
        """
        Send the same message to all connected peers.

        Milestone 2: also uses send_json_with_delay so that every outbound
        message respects NETWORK_DELAY.
        """
        for pid, writer in list(self._peer_writers.items()):
            try:
                await send_json_with_delay(writer, msg)
            except Exception as e:
                print(
                    f"[NET {self.node_id}] Error broadcasting to peer {pid}: {e}",
                    flush=True,
                )

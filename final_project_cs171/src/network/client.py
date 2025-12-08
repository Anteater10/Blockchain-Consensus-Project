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

    # -------------------------------------------------------------------------
    # Internal helper: connect to a single peer
    # -------------------------------------------------------------------------

    async def _connect_peer(self, peer_id: int) -> asyncio.StreamWriter | None:
        """
        Establish a connection to the given peer_id and store its writer.

        Returns the StreamWriter on success, or None on failure.
        """
        peer_info = self.peers.get(peer_id)
        if peer_info is None:
            print(
                f"[NET {self.node_id}] Unknown peer {peer_id}; cannot connect",
                flush=True,
            )
            return None

        host, port = peer_info
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self._peer_writers[peer_id] = writer
            print(
                f"[NET {self.node_id}] Connected to peer {peer_id} at {host}:{port}",
                flush=True,
            )
            return writer
        except Exception as e:
            print(
                f"[NET {self.node_id}] Failed to connect to peer {peer_id} at {host}:{port}: {e}",
                flush=True,
            )
            return None

    async def connect_peers(self) -> None:
        """
        Connect to all peers in the 'peers' dict, ignoring failures for now.

        Milestone 1/2: no retry loop, no backoff, no fancy logging.
        Just a straightforward attempt to connect to each peer once.
        """
        for pid in self.peers.keys():
            if pid == self.node_id:
                continue
            await self._connect_peer(pid)

    # -------------------------------------------------------------------------
    # Sending helpers
    # -------------------------------------------------------------------------

    async def send_to_peer(self, peer_id: int, msg: Dict[str, Any]) -> None:
        """
        Send a JSON-serializable dict to a single peer.

        If the current connection is missing or dead, we:
          - try to establish a fresh connection
          - on send error, close + drop the writer so future sends
            will reconnect instead of hitting BrokenPipe forever.
        """
        writer = self._peer_writers.get(peer_id)

        # If we don't have a writer yet, try to connect lazily.
        if writer is None:
            writer = await self._connect_peer(peer_id)
            if writer is None:
                # Could not connect; drop the message.
                print(
                    f"[NET {self.node_id}] Dropping message to {peer_id} (no connection): {msg}",
                    flush=True,
                )
                return

        try:
            await send_json_with_delay(writer, msg)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            # Connection is dead. Clean it up so next send will reconnect.
            print(
                f"[NET {self.node_id}] Error sending to peer {peer_id}: {e}",
                flush=True,
            )
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self._peer_writers.pop(peer_id, None)
        except Exception as e:
            # Any other random error; log but don't keep a poisoned writer.
            print(
                f"[NET {self.node_id}] Unexpected error sending to peer {peer_id}: {e}",
                flush=True,
            )
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self._peer_writers.pop(peer_id, None)

    async def broadcast(self, msg: Dict[str, Any]) -> None:
        """
        Send the same message to all peers (except self).

        Uses send_to_peer so that missing/broken connections get created lazily.
        """
        for pid in self.peers.keys():
            if pid == self.node_id:
                continue
            await self.send_to_peer(pid, msg)

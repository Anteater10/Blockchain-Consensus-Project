# src/network/server.py
#
# Networking "server" for a node: accepts incoming connections and
# feeds decoded JSON messages to a handler callback.
#
# Milestone 1: stub that just:
#   - starts an asyncio server
#   - uses recv_json per line
#   - calls an on_message callback for each decoded dict

import asyncio
from typing import Awaitable, Callable, Dict, Any

from .protocol import recv_json


OnMessageCallback = Callable[[Dict[str, Any]], Awaitable[None]]


async def start_server(
    host: str,
    port: int,
    on_message: OnMessageCallback,
) -> asyncio.AbstractServer:
    """
    Start an asyncio server that listens on (host, port) and forwards
    each JSON-decoded message dict to 'on_message'.

    The callback is responsible for interpreting the dict (e.g., turning
    it into a PaxosMessage and dispatching to the right PaxosInstance).
    """

    async def handle_conn(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        print(f"[NET-SERVER] Connection from {peer}", flush=True)

        try:
            while True:
                msg = await recv_json(reader)
                # For Milestone 1, we don't do per-connection routing.
                # Just call the provided callback.
                await on_message(msg)
        except ConnectionError:
            pass
        except Exception as e:
            print(f"[NET-SERVER] Error handling connection from {peer}: {e}", flush=True)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            print(f"[NET-SERVER] Connection closed from {peer}", flush=True)

    server = await asyncio.start_server(handle_conn, host, port)
    print(f"[NET-SERVER] Listening on {host}:{port}", flush=True)
    return server

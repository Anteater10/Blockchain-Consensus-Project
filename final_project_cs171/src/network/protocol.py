# src/network/protocol.py
#
# Common networking helpers:
#   - JSON line protocol (one JSON object per line)
#   - Optional artificial network delay (for later milestones)
#
# This is intentionally minimal for Milestone 1. It just gives the
# network layer a consistent way to send/receive JSON messages.

import asyncio
import json
from typing import Any, Dict

# Used in later milestones to simulate network latency.
# For Milestone 1 it's fine if nobody actually sleeps on this.
NETWORK_DELAY: float = 3.0


async def send_json(writer: asyncio.StreamWriter, obj: Dict[str, Any]) -> None:
    """
    Encode a Python dict as a single JSON line and send it.

    Matches the pattern from previous assignments: JSON per line,
    UTF-8 encoded, flushed via writer.drain().
    """
    line = json.dumps(obj) + "\n"
    writer.write(line.encode("utf-8"))
    await writer.drain()


async def recv_json(reader: asyncio.StreamReader) -> Dict[str, Any]:
    """
    Read a single JSON line from the stream and decode it.

    Raises ConnectionError if the socket is closed.
    """
    line = await reader.readline()
    if not line:
        raise ConnectionError("socket closed")
    return json.loads(line.decode("utf-8"))


async def send_json_with_delay(
    writer: asyncio.StreamWriter, obj: Dict[str, Any]
) -> None:
    """
    Same as send_json, but sleeps for NETWORK_DELAY first.

    This is mainly for Milestone 2, where the assignment wants
    a ~3 second artificial delay. For Milestone 1, it's fine if
    nobody calls this yet.
    """
    await asyncio.sleep(NETWORK_DELAY)
    await send_json(writer, obj)

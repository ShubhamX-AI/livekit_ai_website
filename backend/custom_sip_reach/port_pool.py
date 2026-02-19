"""
Thread-safe async port pool for allocating RTP UDP ports.

Each concurrent SIP call needs a unique port pair (RTP + RTCP).
"""

import asyncio
import logging

from .config import RTP_PORT_START, RTP_PORT_END

logger = logging.getLogger("sip_bridge_v3")


class PortPool:
    """Thread-safe pool of UDP ports for RTP sockets."""

    def __init__(self, start: int, end: int):
        # Step by 2 so port+1 is free for RTCP
        self._free = set(range(start, end, 2))
        self._lock = asyncio.Lock()
        logger.info(f"[PortPool] Ready with {len(self._free)} ports ({start}-{end})")

    async def acquire(self) -> int:
        async with self._lock:
            if not self._free:
                raise RuntimeError(
                    f"No free RTP ports in {RTP_PORT_START}-{RTP_PORT_END}. "
                    "Increase RTP_PORT_END or reduce concurrent calls."
                )
            port = min(self._free)
            self._free.discard(port)
            logger.debug(f"[PortPool] Acquired {port}. Remaining: {len(self._free)}")
            return port

    async def release(self, port: int):
        async with self._lock:
            self._free.add(port)
            logger.debug(f"[PortPool] Released {port}. Remaining: {len(self._free)}")


_port_pool: PortPool | None = None


def get_port_pool() -> PortPool:
    global _port_pool
    if _port_pool is None:
        _port_pool = PortPool(RTP_PORT_START, RTP_PORT_END)
    return _port_pool

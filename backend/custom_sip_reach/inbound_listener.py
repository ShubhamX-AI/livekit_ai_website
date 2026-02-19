"""
Inbound SIP TCP listener — handles BYE and OPTIONS from Exotel.

When Exotel initiates a BYE on a *new* TCP connection (rather than the
outbound INVITE connection), this listener catches it and signals the
bridge to tear down the call.
"""

import asyncio
import logging

from .config import EXOTEL_CUSTOMER_SIP_PORT, INBOUND_SIP_LISTEN
from .sip_client import ExotelSipClient

logger = logging.getLogger("sip_bridge_v3")

# ─────────────────────────────────────────────────────────────────────────────
# Module-level state
# ─────────────────────────────────────────────────────────────────────────────

_inbound_server: asyncio.AbstractServer | None = None
_inbound_lock = asyncio.Lock()
_call_registry: dict[str, asyncio.Event] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────


def register_call_id(call_id: str) -> asyncio.Event:
    """Register a call-ID and return an Event that fires on inbound BYE."""
    event = asyncio.Event()
    _call_registry[call_id] = event
    return event


def unregister_call_id(call_id: str):
    """Remove a call-ID from the registry."""
    _call_registry.pop(call_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Server lifecycle
# ─────────────────────────────────────────────────────────────────────────────


async def ensure_inbound_server():
    """Start the inbound SIP listener (once, idempotent)."""
    global _inbound_server
    if not INBOUND_SIP_LISTEN:
        return
    async with _inbound_lock:
        if _inbound_server is not None:
            return
        try:
            _inbound_server = await asyncio.start_server(
                _handle_inbound_sip, "0.0.0.0", EXOTEL_CUSTOMER_SIP_PORT
            )
            logger.info(
                "[SIP-IN] Listening on 0.0.0.0:%s",
                EXOTEL_CUSTOMER_SIP_PORT,
            )
        except Exception as e:
            logger.error(f"[SIP-IN] Failed to bind {EXOTEL_CUSTOMER_SIP_PORT}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Connection handler
# ─────────────────────────────────────────────────────────────────────────────


async def _handle_inbound_sip(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    buf = b""
    peer = writer.get_extra_info("peername")
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buf += data

            while b"\r\n\r\n" in buf:
                he = buf.index(b"\r\n\r\n")
                hb = buf[:he].decode(errors="replace")
                rest = buf[he + 4 :]
                lines = hb.split("\r\n")
                start = lines[0]
                hdrs = {
                    l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip()
                    for l in lines[1:]
                    if ":" in l
                }
                cl = int(hdrs.get("content-length", "0"))
                if len(rest) < cl:
                    break
                buf = rest[cl:]

                if start.startswith("BYE "):
                    call_id = hdrs.get("call-id")
                    logger.info(f"[SIP-IN] ← BYE from {peer} call-id={call_id}")
                    if call_id and call_id in _call_registry:
                        _call_registry[call_id].set()
                    writer.write(ExotelSipClient._response_200_ok(hdrs))
                    await writer.drain()
                    logger.info("[SIP-IN] → 200 OK (BYE)")
                elif start.startswith("OPTIONS "):
                    writer.write(ExotelSipClient._response_200_ok(hdrs))
                    await writer.drain()
                    logger.info(f"[SIP-IN] → 200 OK (OPTIONS) from {peer}")
    except Exception as e:
        logger.info(f"[SIP-IN] Connection ended: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

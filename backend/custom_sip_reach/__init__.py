"""
custom_sip_reach — Modular Exotel SIP Bridge for LiveKit.

This package handles outbound SIP calls through Exotel, bridging
phone audio (G.711 over RTP) with LiveKit rooms.

Usage:
    from custom_sip_reach import run_bridge

    await run_bridge(phone_number="08697421450", agent_type="invoice")
"""

from .bridge import run_bridge  # noqa: F401

__all__ = ["run_bridge"]

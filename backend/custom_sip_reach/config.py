"""
Configuration constants and validation for the Exotel SIP bridge.

All environment variables, codec constants, timeouts, and the startup
config validator live here.
"""

import os
import logging

from dotenv import load_dotenv

load_dotenv(override=False)

logger = logging.getLogger("sip_bridge_v3")

# ─────────────────────────────────────────────────────────────────────────────
# SIP / Network Configuration
# ─────────────────────────────────────────────────────────────────────────────

EXOTEL_SIP_HOST = os.getenv("EXOTEL_SIP_HOST", "pstn.in1.exotel.com")
EXOTEL_SIP_PORT = int(os.getenv("EXOTEL_SIP_PORT", "5070"))

# Your server's PUBLIC / Elastic IP (used in Via + Contact SIP headers)
EXOTEL_CUSTOMER_IP = os.getenv("EXOTEL_CUSTOMER_IP", "")
EXOTEL_CUSTOMER_SIP_PORT = int(os.getenv("EXOTEL_CUSTOMER_SIP_PORT", "5061"))

# ⚠️  CRITICAL: must be your EC2 Elastic/Public IP — NOT 0.0.0.0 or a private IP.
# This goes into SDP c= so Exotel knows where to send RTP back.
EXOTEL_MEDIA_IP = os.getenv("EXOTEL_MEDIA_IP", "")

EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID", "08044319240")
EXOTEL_FROM_DOMAIN = os.getenv("EXOTEL_FROM_DOMAIN", "lokaviveka1m.sip.exotel.com")

EXOTEL_AUTH_USERNAME = os.getenv("EXOTEL_AUTH_USERNAME")
EXOTEL_AUTH_PASSWORD = os.getenv("EXOTEL_AUTH_PASSWORD")

# ─────────────────────────────────────────────────────────────────────────────
# LiveKit Configuration
# ─────────────────────────────────────────────────────────────────────────────

LK_URL = os.getenv("LIVEKIT_URL")
LK_API_KEY = os.getenv("LIVEKIT_API_KEY")
LK_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# ─────────────────────────────────────────────────────────────────────────────
# RTP / Codec Constants
# ─────────────────────────────────────────────────────────────────────────────

# RTP Port pool — MUST be outside LiveKit SIP's range (10000-40000) and LiveKit RTC's range (50000-60000).
# Safe range: 41000-49999. Open these in your AWS Security Group for UDP.
# Each concurrent call uses 2 ports (RTP + RTCP).
RTP_PORT_START = int(
    os.getenv("SIP_BRIDGE_PORT_RANGE_START", os.getenv("RTP_PORT_START", "31000"))
)
RTP_PORT_END = int(
    os.getenv("SIP_BRIDGE_PORT_RANGE_END", os.getenv("RTP_PORT_END", "31100"))
)  # 50 simultaneous calls max

RTP_HEADER_SIZE = 12
PCMU_PAYLOAD_TYPE = 0
PCMA_PAYLOAD_TYPE = 8
SAMPLE_RATE_SIP = 8000
SAMPLE_RATE_LK = 48000
MAX_FRAME_BUFFER = 300  # ~6 seconds of 20ms frames

# ─────────────────────────────────────────────────────────────────────────────
# Timeout Configuration
# ─────────────────────────────────────────────────────────────────────────────

NO_RTP_AFTER_ANSWER_SECONDS = int(os.getenv("NO_RTP_AFTER_ANSWER_SECONDS", "60"))
RTP_SILENCE_TIMEOUT_SECONDS = int(os.getenv("RTP_SILENCE_TIMEOUT_SECONDS", "30"))
INBOUND_SIP_LISTEN = os.getenv("INBOUND_SIP_LISTEN", "true").lower() in (
    "1",
    "true",
    "yes",
)


# ─────────────────────────────────────────────────────────────────────────────
# Config Validation
# ─────────────────────────────────────────────────────────────────────────────


def validate_config() -> bool:
    """Check that all critical env vars are set.  Returns True when OK."""
    ok = True
    checks = [
        (
            EXOTEL_MEDIA_IP and EXOTEL_MEDIA_IP not in ("0.0.0.0", ""),
            "EXOTEL_MEDIA_IP must be your server's public/Elastic IP (NOT 0.0.0.0). "
            "Exotel uses this to route RTP back to you.",
        ),
        (
            EXOTEL_CUSTOMER_IP and EXOTEL_CUSTOMER_IP not in ("0.0.0.0", ""),
            "EXOTEL_CUSTOMER_IP must be your server's public/Elastic IP.",
        ),
        (bool(LK_URL), "LIVEKIT_URL is not set"),
        (bool(LK_API_KEY), "LIVEKIT_API_KEY is not set"),
        (bool(LK_API_SECRET), "LIVEKIT_API_SECRET is not set"),
    ]
    for passed, msg in checks:
        if not passed:
            logger.error(f"[CONFIG] ❌ {msg}")
            ok = False
    if ok:
        logger.info(
            f"[CONFIG] ✅ public IP={EXOTEL_MEDIA_IP}, ports={RTP_PORT_START}-{RTP_PORT_END}"
        )
    return ok

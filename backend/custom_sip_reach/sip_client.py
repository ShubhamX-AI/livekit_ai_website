"""
Exotel SIP Client — handles SIP signalling over TCP.

Responsibilities:
  • Build SDP, INVITE, ACK, BYE messages
  • Connect to Exotel SIP proxy
  • Handle 401/407 digest-auth challenges
  • Parse 200 OK to extract remote RTP endpoint
  • Monitor for remote BYE (hang-up detection)
"""

import asyncio
import logging
import random
import time
import uuid

from .config import (
    EXOTEL_AUTH_PASSWORD,
    EXOTEL_AUTH_USERNAME,
    EXOTEL_CALLER_ID,
    EXOTEL_CUSTOMER_IP,
    EXOTEL_CUSTOMER_SIP_PORT,
    EXOTEL_FROM_DOMAIN,
    EXOTEL_MEDIA_IP,
    EXOTEL_SIP_HOST,
    EXOTEL_SIP_PORT,
    PCMA_PAYLOAD_TYPE,
)
from .digest_auth import calculate_digest_auth

logger = logging.getLogger("sip_bridge_v3")


class ExotelSipClient:
    def __init__(self, callee: str, rtp_port: int):
        self.callee = callee
        self.rtp_port = rtp_port
        self._branch = f"z9hG4bK-{uuid.uuid4().hex}"
        self._tag = f"trunk{random.randint(10000, 99999)}"
        self._call_id = str(uuid.uuid4())
        self._cseq = 1
        self._to_tag = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    # ── SDP / Message Builders ───────────────────────────────────────────

    def _sdp(self) -> str:
        ts = int(time.time())
        # c= uses the real public IP — this is what Exotel reads to know where to send RTP
        return (
            f"v=0\r\no=- {ts} {ts} IN IP4 {EXOTEL_MEDIA_IP}\r\ns=-\r\n"
            f"c=IN IP4 {EXOTEL_MEDIA_IP}\r\nt=0 0\r\n"
            f"m=audio {self.rtp_port} RTP/AVP 8 0 101\r\n"
            f"a=rtpmap:8 PCMA/8000\r\na=rtpmap:0 PCMU/8000\r\n"
            f"a=rtpmap:101 telephone-event/8000\r\na=fmtp:101 0-15\r\n"
            f"a=ptime:20\r\na=sendrecv\r\n"
        )

    def _invite(self, auth: str | None = None, proxy: bool = False) -> bytes:
        sdp = self._sdp()
        req = f"sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}"
        h = [
            f"INVITE {req} SIP/2.0",
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};branch={self._branch};rport",
            f"Max-Forwards: 70",
            f'From: "{EXOTEL_CALLER_ID}" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}',
            f"To: <sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>",
            f"Call-ID: {self._call_id}",
            f"CSeq: {self._cseq} INVITE",
            f"Contact: <sip:{EXOTEL_CALLER_ID}@{EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};transport=tcp>",
            f"Supported: 100rel, timer",
            f"Allow: INVITE, ACK, CANCEL, BYE, OPTIONS, UPDATE",
            f"Content-Type: application/sdp",
            f"Content-Length: {len(sdp.encode())}",
        ]
        if auth:
            h.insert(
                7, f"{'Proxy-Authorization' if proxy else 'Authorization'}: {auth}"
            )
        return ("\r\n".join(h) + "\r\n\r\n" + sdp).encode()

    def _ack(self) -> bytes:
        to = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>" + (
            f";tag={self._to_tag}" if self._to_tag else ""
        )
        return (
            "\r\n".join(
                [
                    f"ACK sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0",
                    f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};branch={self._branch};rport",
                    f"Max-Forwards: 70",
                    f'From: "{EXOTEL_CALLER_ID}" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}',
                    f"To: {to}",
                    f"Call-ID: {self._call_id}",
                    f"CSeq: {self._cseq} ACK",
                    "Content-Length: 0",
                ]
            )
            + "\r\n\r\n"
        ).encode()

    def _bye(self) -> bytes:
        to = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>" + (
            f";tag={self._to_tag}" if self._to_tag else ""
        )
        self._cseq += 1
        return (
            "\r\n".join(
                [
                    f"BYE sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0",
                    f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};branch=z9hG4bK-{uuid.uuid4().hex};rport",
                    f"Max-Forwards: 70",
                    f'From: "{EXOTEL_CALLER_ID}" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}',
                    f"To: {to}",
                    f"Call-ID: {self._call_id}",
                    f"CSeq: {self._cseq} BYE",
                    "Content-Length: 0",
                ]
            )
            + "\r\n\r\n"
        ).encode()

    @staticmethod
    def _response_200_ok(hdrs: dict) -> bytes:
        def _get(name: str) -> str | None:
            return hdrs.get(name)

        h = ["SIP/2.0 200 OK"]
        via = _get("via")
        if via:
            h.append(f"Via: {via}")
        frm = _get("from")
        if frm:
            h.append(f"From: {frm}")
        to = _get("to")
        if to:
            h.append(f"To: {to}")
        call_id = _get("call-id")
        if call_id:
            h.append(f"Call-ID: {call_id}")
        cseq = _get("cseq")
        if cseq:
            h.append(f"CSeq: {cseq}")
        h.append("Content-Length: 0")
        return ("\r\n".join(h) + "\r\n\r\n").encode()

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def call_id(self) -> str:
        return self._call_id

    # ── Connection / Signalling ──────────────────────────────────────────

    async def connect(self):
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(EXOTEL_SIP_HOST, EXOTEL_SIP_PORT), timeout=10.0
        )
        logger.info("[SIP] TCP connected")

    async def send_invite(self) -> dict | None:
        self._writer.write(self._invite())
        await self._writer.drain()
        logger.info("[SIP] INVITE →")
        return await self._recv_loop()

    async def _recv_loop(self) -> dict | None:
        buf = b""
        while True:
            try:
                chunk = await asyncio.wait_for(self._reader.read(8192), timeout=60.0)
                if not chunk:
                    return None
                buf += chunk

                while b"\r\n\r\n" in buf:
                    he = buf.index(b"\r\n\r\n")
                    hb = buf[:he].decode(errors="replace")
                    rest = buf[he + 4 :]
                    lines = hb.split("\r\n")
                    status = lines[0]
                    hdrs = {
                        l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip()
                        for l in lines[1:]
                        if ":" in l
                    }
                    cl = int(hdrs.get("content-length", "0"))
                    if len(rest) < cl:
                        break
                    body = rest[:cl].decode(errors="replace")
                    buf = rest[cl:]

                    logger.info(f"[SIP] ← {status}")
                    code = int(status.split()[1])
                    if code in (100,):
                        continue
                    if 180 <= code <= 183:
                        continue

                    if code in (401, 407):
                        ah = "www-authenticate" if code == 401 else "proxy-authenticate"
                        if ah not in hdrs or not EXOTEL_AUTH_USERNAME:
                            logger.error("[SIP] Auth required but no credentials")
                            return None
                        self._writer.write(self._ack())
                        await self._writer.drain()
                        self._cseq += 1
                        self._branch = f"z9hG4bK-{uuid.uuid4().hex}"
                        uri = f"sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}"
                        auth = calculate_digest_auth(
                            "INVITE",
                            uri,
                            EXOTEL_AUTH_USERNAME,
                            EXOTEL_AUTH_PASSWORD,
                            hdrs[ah],
                        )
                        self._writer.write(self._invite(auth=auth, proxy=(code == 407)))
                        await self._writer.drain()
                        logger.info("[SIP] Re-INVITE with auth →")
                        continue

                    if code == 200:
                        if "tag=" in hdrs.get("to", ""):
                            self._to_tag = hdrs["to"].split("tag=")[-1].split(";")[0]
                        self._writer.write(self._ack())
                        await self._writer.drain()
                        logger.info("[SIP] ✅ 200 OK — ACK sent")

                        rip, rport, rpt = None, 0, PCMA_PAYLOAD_TYPE
                        for line in body.splitlines():
                            if line.startswith("c=IN IP4"):
                                rip = line.split()[-1]
                            if line.startswith("m=audio"):
                                parts = line.split()
                                rport = int(parts[1])
                                if len(parts) > 3:
                                    rpt = int(parts[3])
                        logger.info(f"[SIP] Remote RTP: {rip}:{rport} PT={rpt}")
                        return {"remote_ip": rip, "remote_port": rport, "pt": rpt}

                    if code >= 400:
                        logger.error(f"[SIP] ❌ {status}")
                        return None

            except asyncio.TimeoutError:
                logger.error("[SIP] Timeout")
                return None
            except Exception as e:
                logger.error(f"[SIP] Error: {e}")
                return None

    async def wait_for_disconnection(self):
        try:
            buf = b""
            while True:
                data = await asyncio.wait_for(self._reader.read(4096), timeout=3600.0)
                if not data:
                    logger.info("[SIP] Disconnected (TCP close)")
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
                        logger.info("[SIP] ← BYE")
                        if self._writer:
                            self._writer.write(self._response_200_ok(hdrs))
                            await self._writer.drain()
                        logger.info("[SIP] → 200 OK (BYE)")
                        return
        except Exception as e:
            logger.info(f"[SIP] Monitor ended: {e}")

    async def send_bye(self):
        if self._writer:
            try:
                self._writer.write(self._bye())
                await self._writer.drain()
                logger.info("[SIP] BYE →")
            except Exception:
                pass

    async def close(self):
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

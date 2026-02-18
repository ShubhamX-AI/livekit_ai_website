"""
Exotel SIP Bridge V2 — Final production version.

Fixes applied:
1. SDP c= advertises correct public IP (EXOTEL_MEDIA_IP = your EC2 Elastic/Public IP)
2. Port pool (RTP_PORT_START–RTP_PORT_END) — multiple simultaneous calls
3. Port ALWAYS released on cleanup — no "address in use" errors
4. Agent audio buffered before SIP answers — no dropped welcome message
5. Startup config validation — fails fast with clear error messages
6. BYE sent on hangup
"""

import asyncio
import logging
import socket
import struct
import uuid
import random
import os
import warnings
import hashlib
import time
import collections
import json

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants

load_dotenv(override=True)

logger = logging.getLogger("sip_bridge_v2")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

EXOTEL_SIP_HOST          = os.getenv("EXOTEL_SIP_HOST", "pstn.in1.exotel.com")
EXOTEL_SIP_PORT          = int(os.getenv("EXOTEL_SIP_PORT", "5070"))

# Your server's PUBLIC / Elastic IP (used in Via + Contact SIP headers)
EXOTEL_CUSTOMER_IP       = os.getenv("EXOTEL_CUSTOMER_IP", "")
EXOTEL_CUSTOMER_SIP_PORT = int(os.getenv("EXOTEL_CUSTOMER_SIP_PORT", "5061"))

# ⚠️  CRITICAL: must be your EC2 Elastic/Public IP — NOT 0.0.0.0 or a private IP.
# This goes into SDP c= so Exotel knows where to send RTP back.
EXOTEL_MEDIA_IP          = os.getenv("EXOTEL_MEDIA_IP", "")

EXOTEL_CALLER_ID         = os.getenv("EXOTEL_CALLER_ID", "08044319240")
EXOTEL_FROM_DOMAIN       = os.getenv("EXOTEL_FROM_DOMAIN", "lokaviveka1m.sip.exotel.com")

EXOTEL_AUTH_USERNAME     = os.getenv("EXOTEL_AUTH_USERNAME")
EXOTEL_AUTH_PASSWORD     = os.getenv("EXOTEL_AUTH_PASSWORD")

LK_URL        = os.getenv("LIVEKIT_URL")
LK_API_KEY    = os.getenv("LIVEKIT_API_KEY")
LK_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# RTP Port pool — MUST be outside LiveKit SIP's range (10000-40000) and LiveKit RTC's range (50000-60000).
# Safe range: 41000-49999. Open these in your AWS Security Group for UDP.
# Each concurrent call uses 2 ports (RTP + RTCP).
RTP_PORT_START = int(os.getenv("SIP_BRIDGE_PORT_RANGE_START", os.getenv("RTP_PORT_START", "31000")))
RTP_PORT_END   = int(os.getenv("SIP_BRIDGE_PORT_RANGE_END", os.getenv("RTP_PORT_END", "31100")))  # 50 simultaneous calls max

RTP_HEADER_SIZE   = 12
PCMU_PAYLOAD_TYPE = 0
PCMA_PAYLOAD_TYPE = 8
SAMPLE_RATE_SIP   = 8000
SAMPLE_RATE_LK    = 48000
MAX_FRAME_BUFFER  = 300  # ~6 seconds of 20ms frames


# ─────────────────────────────────────────────────────────────────────────────
# Config validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_config() -> bool:
    ok = True
    checks = [
        (EXOTEL_MEDIA_IP and EXOTEL_MEDIA_IP not in ("0.0.0.0", ""),
         "EXOTEL_MEDIA_IP must be your server's public/Elastic IP (NOT 0.0.0.0). "
         "Exotel uses this to route RTP back to you."),
        (EXOTEL_CUSTOMER_IP and EXOTEL_CUSTOMER_IP not in ("0.0.0.0", ""),
         "EXOTEL_CUSTOMER_IP must be your server's public/Elastic IP."),
        (bool(LK_URL), "LIVEKIT_URL is not set"),
        (bool(LK_API_KEY), "LIVEKIT_API_KEY is not set"),
        (bool(LK_API_SECRET), "LIVEKIT_API_SECRET is not set"),
    ]
    for passed, msg in checks:
        if not passed:
            logger.error(f"[CONFIG] ❌ {msg}")
            ok = False
    if ok:
        logger.info(f"[CONFIG] ✅ public IP={EXOTEL_MEDIA_IP}, ports={RTP_PORT_START}-{RTP_PORT_END}")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Port Pool
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# RTPMediaBridge
# ─────────────────────────────────────────────────────────────────────────────

class RTPMediaBridge:
    def __init__(self, public_ip: str, bind_port: int):
        """
        public_ip  : Server's public/Elastic IP — written into SDP c= line.
        bind_port  : UDP port to listen on (from PortPool).
        """
        if not public_ip or public_ip == "0.0.0.0":
            raise ValueError(
                "public_ip must be your EC2 public/Elastic IP. "
                f"Got: '{public_ip}'. Check EXOTEL_MEDIA_IP."
            )
        self._public_ip = public_ip
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        self._sock.bind(('0.0.0.0', bind_port))
        self._sock.setblocking(False)
        self.local_port = self._sock.getsockname()[1]
        logger.info(
            f"[RTP] Socket bound 0.0.0.0:{self.local_port} "
            f"| SDP advertises {public_ip}:{self.local_port}"
        )

        self._remote_addr: tuple[str, int] | None = None
        self._running      = False
        self.negotiated_pt = PCMA_PAYLOAD_TYPE

        self._audio_source: rtc.AudioSource | None = None
        self._local_track:  rtc.LocalAudioTrack | None = None

        self._rtp_seq  = random.randint(0, 0xFFFF)
        self._rtp_ts   = random.randint(0, 0xFFFFFFFF)
        self._rtp_ssrc = random.randint(0, 0xFFFFFFFF)

        self._rs_in  = None  # resample state inbound
        self._rs_out = None  # resample state outbound

        self._rx = 0
        self._tx = 0
        self._first_rx = False
        self._first_tx = False

        # Buffer agent frames until set_remote_endpoint() is called
        self._frame_buffer: collections.deque = collections.deque(maxlen=MAX_FRAME_BUFFER)

        # ptime accumulator: collect PCM until we have exactly 20ms to send.
        # At 8kHz, 16-bit mono: 20ms = 160 samples = 320 bytes of PCM.
        # G.711 encodes 1:1, so payload = 160 bytes. Total RTP = 172 bytes.
        # LiveKit sends 10ms frames, so we pack 2 frames → 1 RTP packet.
        self._PTIME_BYTES = 320  # 20ms at 8kHz 16-bit
        self._pcm_accumulator = b""

    def set_remote_endpoint(self, ip: str, port: int, pt: int = PCMA_PAYLOAD_TYPE):
        self._remote_addr  = (ip, port)
        self.negotiated_pt = pt
        logger.info(f"[RTP] Remote endpoint → {ip}:{port} PT={pt}")

    async def start_inbound(self, room: rtc.Room):
        self._audio_source = rtc.AudioSource(SAMPLE_RATE_LK, 1)
        self._local_track  = rtc.LocalAudioTrack.create_audio_track("sip_audio", self._audio_source)
        await room.local_participant.publish_track(self._local_track)
        self._running = True
        task = asyncio.create_task(self._recv_loop())
        task.add_done_callback(
            lambda t: logger.error(f"[RTP] recv_loop DIED: {t.exception()}") 
            if not t.cancelled() and t.exception() else None
        )
        logger.info(f"[RTP] Inbound loop started, listening on 0.0.0.0:{self.local_port}")

    async def _recv_loop(self):
        loop = asyncio.get_running_loop()
        logger.info(f"[RTP] recv_loop STARTED port={self.local_port}")
        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 4096)
                logger.info(f"[RTP] READ {len(data)} bytes from {addr}") 
            except (OSError, asyncio.CancelledError):
                break
            except Exception:
                await asyncio.sleep(0.001)
                continue

            if len(data) <= RTP_HEADER_SIZE:
                continue

            if not self._first_rx:
                logger.info(f"[RTP] ✅ First inbound RTP from {addr} ({len(data)} B)")
                self._first_rx = True

            self._rx += 1
            pt      = data[1] & 0x7F
            payload = data[RTP_HEADER_SIZE:]

            try:
                pcm8 = audioop.alaw2lin(payload, 2) if pt == PCMA_PAYLOAD_TYPE else audioop.ulaw2lin(payload, 2)
                pcm48, self._rs_in = audioop.ratecv(pcm8, 2, 1, SAMPLE_RATE_SIP, SAMPLE_RATE_LK, self._rs_in)
                frame = rtc.AudioFrame(
                    data=pcm48,
                    sample_rate=SAMPLE_RATE_LK,
                    num_channels=1,
                    samples_per_channel=len(pcm48) // 2,
                )
                # Fire and forget — don't block recv_loop on LiveKit backpressure
                asyncio.ensure_future(self._audio_source.capture_frame(frame))
            except Exception as e:
                logger.error(f"[RTP] Decode error: {e}")

    async def send_to_rtp(self, frame: rtc.AudioFrame):
        """Send agent audio to remote RTP. Buffers if SIP not yet answered."""
        if not self._remote_addr:
            self._frame_buffer.append(frame)
            return
        # Flush buffer once (after set_remote_endpoint called)
        while self._frame_buffer:
            await self._send_frame(self._frame_buffer.popleft())
        await self._send_frame(frame)

    async def _send_frame(self, frame: rtc.AudioFrame):
        """Accumulate PCM until we have 20ms, then send one RTP packet.

        Why: SDP advertises a=ptime:20. Exotel expects 160-byte G.711 payloads
        (20ms @ 8kHz). LiveKit produces 10ms frames (80 bytes). Sending 10ms
        packets causes Exotel to drop them → caller hears silence.
        We buffer until we have exactly 320 bytes of 8kHz 16-bit PCM (= 20ms),
        then encode and send one correctly-sized packet.
        """
        if not self._remote_addr:
            return
        try:
            raw = bytes(frame.data.cast("b"))
            pcm8, self._rs_out = audioop.ratecv(
                raw, 2, 1, frame.sample_rate, SAMPLE_RATE_SIP, self._rs_out
            )
            self._pcm_accumulator += pcm8

            # Send one packet per full 20ms chunk; discard any remainder
            # (remainder is < 10ms and will be completed by the next frame)
            while len(self._pcm_accumulator) >= self._PTIME_BYTES:
                chunk = self._pcm_accumulator[:self._PTIME_BYTES]
                self._pcm_accumulator = self._pcm_accumulator[self._PTIME_BYTES:]

                payload = (audioop.lin2alaw(chunk, 2)
                           if self.negotiated_pt == PCMA_PAYLOAD_TYPE
                           else audioop.lin2ulaw(chunk, 2))

                # Timestamp advances by exactly 160 samples (20ms @ 8kHz)
                self._rtp_seq = (self._rtp_seq + 1) & 0xFFFF
                self._rtp_ts  = (self._rtp_ts + 160) & 0xFFFFFFFF
                hdr = struct.pack(
                    "!BBHII",
                    0x80, self.negotiated_pt,
                    self._rtp_seq, self._rtp_ts, self._rtp_ssrc
                )
                self._sock.sendto(hdr + payload, self._remote_addr)
                self._tx += 1

                if not self._first_tx:
                    logger.info(
                        f"[RTP] ✅ First outbound RTP sent to {self._remote_addr} "
                        f"(payload={len(payload)}B = 20ms ✓)"
                    )
                    self._first_tx = True
        except Exception as e:
            logger.error(f"[RTP] Send error: {e}")

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        logger.info(f"[RTP] Stopped | RX={self._rx} TX={self._tx}")
        if self._rx == 0:
            logger.warning(
                "[RTP] ⚠️  ZERO inbound packets! Likely causes:\n"
                "  1. EXOTEL_MEDIA_IP='%s' is wrong — must be EC2 Elastic/Public IP\n"
                "  2. UDP port %d not open in Security Group for Exotel media IPs\n"
                "  3. Port conflicts with another service (LiveKit SIP uses 10000-40000 — stay out of that range!)\n"
                "  4. Exotel routing to wrong destination",
                self._public_ip, self.local_port
            )


# ─────────────────────────────────────────────────────────────────────────────
# Digest Auth
# ─────────────────────────────────────────────────────────────────────────────

def calculate_digest_auth(method, uri, username, password, auth_header):
    import re
    params = {}
    for k, v in re.findall(r'(\w+)="?([^",]+)"?', auth_header.split(' ', 1)[1]):
        params[k] = v

    realm, nonce = params.get('realm'), params.get('nonce')
    opaque, qop  = params.get('opaque'), params.get('qop')
    algo         = params.get('algorithm', 'MD5').upper()

    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

    if qop == 'auth':
        nc, cnonce = "00000001", uuid.uuid4().hex[:8]
        resp = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
        s = (f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
             f'response="{resp}", algorithm={algo}, nc={nc}, cnonce="{cnonce}", qop={qop}')
    else:
        resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        s = f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{resp}", algorithm={algo}'

    return s + (f', opaque="{opaque}"' if opaque else '')


# ─────────────────────────────────────────────────────────────────────────────
# SIP Client
# ─────────────────────────────────────────────────────────────────────────────

class ExotelSipClient:
    def __init__(self, callee: str, rtp_port: int):
        self.callee   = callee
        self.rtp_port = rtp_port
        self._branch  = f"z9hG4bK-{uuid.uuid4().hex}"
        self._tag     = f"trunk{random.randint(10000, 99999)}"
        self._call_id = str(uuid.uuid4())
        self._cseq    = 1
        self._to_tag  = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

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
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}",
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
            h.insert(7, f"{'Proxy-Authorization' if proxy else 'Authorization'}: {auth}")
        return ("\r\n".join(h) + "\r\n\r\n" + sdp).encode()

    def _ack(self) -> bytes:
        to = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>" + (f";tag={self._to_tag}" if self._to_tag else "")
        return ("\r\n".join([
            f"ACK sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0",
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};branch={self._branch};rport",
            f"Max-Forwards: 70",
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}",
            f"To: {to}", f"Call-ID: {self._call_id}", f"CSeq: {self._cseq} ACK", "Content-Length: 0",
        ]) + "\r\n\r\n").encode()

    def _bye(self) -> bytes:
        to = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>" + (f";tag={self._to_tag}" if self._to_tag else "")
        self._cseq += 1
        return ("\r\n".join([
            f"BYE sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0",
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};branch=z9hG4bK-{uuid.uuid4().hex};rport",
            f"Max-Forwards: 70",
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;tag={self._tag}",
            f"To: {to}", f"Call-ID: {self._call_id}", f"CSeq: {self._cseq} BYE", "Content-Length: 0",
        ]) + "\r\n\r\n").encode()

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
                if not chunk: return None
                buf += chunk

                while b"\r\n\r\n" in buf:
                    he = buf.index(b"\r\n\r\n")
                    hb = buf[:he].decode(errors="replace")
                    rest = buf[he + 4:]
                    lines = hb.split("\r\n")
                    status = lines[0]
                    hdrs = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip()
                            for l in lines[1:] if ":" in l}
                    cl = int(hdrs.get("content-length", "0"))
                    if len(rest) < cl: break
                    body = rest[:cl].decode(errors="replace")
                    buf  = rest[cl:]

                    logger.info(f"[SIP] ← {status}")
                    code = int(status.split()[1])
                    if code in (100,): continue
                    if 180 <= code <= 183: continue

                    if code in (401, 407):
                        ah = "www-authenticate" if code == 401 else "proxy-authenticate"
                        if ah not in hdrs or not EXOTEL_AUTH_USERNAME:
                            logger.error("[SIP] Auth required but no credentials")
                            return None
                        self._writer.write(self._ack())
                        await self._writer.drain()
                        self._cseq  += 1
                        self._branch = f"z9hG4bK-{uuid.uuid4().hex}"
                        uri  = f"sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}"
                        auth = calculate_digest_auth("INVITE", uri, EXOTEL_AUTH_USERNAME, EXOTEL_AUTH_PASSWORD, hdrs[ah])
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
                            if line.startswith("c=IN IP4"): rip = line.split()[-1]
                            if line.startswith("m=audio"):
                                parts = line.split()
                                rport = int(parts[1])
                                if len(parts) > 3: rpt = int(parts[3])
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
            while True:
                data = await asyncio.wait_for(self._reader.read(4096), timeout=3600.0)
                if not data or b"BYE " in data:
                    logger.info("[SIP] Disconnected (BYE or TCP close)")
                    break
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


# ─────────────────────────────────────────────────────────────────────────────
# Main bridge
# ─────────────────────────────────────────────────────────────────────────────

async def run_bridge(phone_number: str, agent_type: str = "invoice", room_name: str | None = None):
    if not _validate_config():
        return

    if not room_name:
        room_name = f"sip-bridge-{phone_number}-{uuid.uuid4().hex[:6]}"

    pool = get_port_pool()
    port = await pool.acquire()
    logger.info(f"[BRIDGE] phone={phone_number} room={room_name} rtp_port={port}")

    rtp_bridge   = None
    sip_client   = None
    forward_task = None
    room         = rtc.Room()

    try:
        rtp_bridge = RTPMediaBridge(public_ip=EXOTEL_MEDIA_IP, bind_port=port)
        sip_client = ExotelSipClient(callee=phone_number, rtp_port=port)

        @room.on("track_subscribed")
        def on_track(track, publication, participant):
            nonlocal forward_task
            if (track.kind == rtc.TrackKind.KIND_AUDIO
                    and publication.source == rtc.TrackSource.SOURCE_MICROPHONE
                    and forward_task is None):
                logger.info(f"[BRIDGE] Agent audio from {participant.identity} — buffering")
                forward_task = asyncio.create_task(_forward_audio(track, rtp_bridge))

        token = (AccessToken(LK_API_KEY, LK_API_SECRET)
                 .with_identity(f"sip-{phone_number}")
                 .with_metadata(json.dumps({"source": "exotel_bridge"}))
                 .with_grants(VideoGrants(room_join=True, room=room_name))
                 .to_jwt())
        await room.connect(LK_URL, token)
        logger.info(f"[BRIDGE] LiveKit connected: {room_name}")
        await rtp_bridge.start_inbound(room)

        await sip_client.connect()
        res = await sip_client.send_invite()
        if not res:
            logger.error("[BRIDGE] SIP failed")
            return

        # Flush buffered agent audio + open RTP path
        rtp_bridge.set_remote_endpoint(res["remote_ip"], res["remote_port"], res["pt"])

        # Notify agent that call is answered
        try:
            await room.local_participant.publish_data(
                json.dumps({"event": "call_answered"}).encode(),
                topic="sip_bridge_events"
            )
            logger.info("[BRIDGE] Published call_answered event")
        except Exception as e:
            logger.error(f"[BRIDGE] Failed to publish call_answered event: {e}")

        sip_mon = asyncio.create_task(sip_client.wait_for_disconnection())
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED and not sip_mon.done():
            await asyncio.sleep(2)

        logger.info("[BRIDGE] Call ended")

    except Exception as e:
        logger.error(f"[BRIDGE] Error: {e}", exc_info=True)

    finally:
        if forward_task:
            forward_task.cancel()
            try: await forward_task
            except asyncio.CancelledError: pass

        if sip_client:
            await sip_client.send_bye()
            await sip_client.close()

        if rtp_bridge:
            rtp_bridge.stop()

        await room.disconnect()
        # ← This is the critical step that was missing before
        await pool.release(port)
        logger.info(f"[BRIDGE] Port {port} released")


async def _forward_audio(track: rtc.Track, bridge: RTPMediaBridge):
    stream = rtc.AudioStream(track, sample_rate=48000, num_channels=1)
    async for event in stream:
        await bridge.send_to_rtp(event.frame)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bridge("08697421450"))
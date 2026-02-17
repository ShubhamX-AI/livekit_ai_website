"""
Exotel SIP Bridge — Bridges SIP/RTP audio with a LiveKit Room.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │                      run_bridge()                        │
    │                                                          │
    │  1. Connect to existing LiveKit Room as "phone user"     │
    │  2. Register track_subscribed handler (Agent → Phone)    │
    │  3. Publish local audio track (Phone → Agent)            │
    │  4. Send SIP INVITE to Exotel via TCP                    │
    │  5. On 200 OK → parse remote RTP endpoint from SDP      │
    │  6. Send ACK → call established                          │
    │  7. Bidirectional audio bridging:                         │
    │     • RTP in  (Exotel → UDP) → G.711 decode → LiveKit   │
    │     • RTP out (LiveKit AudioStream) → G.711 encode → UDP │
    │  8. On hangup or error → cleanup                         │
    └──────────────────────────────────────────────────────────┘

Media Flow (Phone → Agent):
    Phone speaks → Exotel PSTN → RTP/UDP (G.711 PCMU 8kHz)
    → RTPMediaBridge receives UDP packet
    → Strip 12-byte RTP header → extract payload
    → audioop.ulaw2lin() → PCM 16-bit 8kHz
    → audioop.ratecv() → resample to 48kHz
    → rtc.AudioFrame(data, 48000, 1, samples_per_channel)
    → AudioSource.capture_frame() → published to LiveKit room
    → Agent's STT hears the phone user

Media Flow (Agent → Phone):
    Agent TTS speaks → audio track published to LiveKit room
    → track_subscribed event → create rtc.AudioStream(track)
    → async iterate AudioFrameEvents
    → frame.data.cast("b").tobytes() → raw PCM 48kHz
    → audioop.ratecv() → resample to 8kHz
    → audioop.lin2ulaw() → G.711 PCMU payload
    → Build 12-byte RTP header (V=2, PT=0, seq, ts, ssrc)
    → Send UDP packet to Exotel's RTP endpoint
    → Exotel forwards to phone → caller hears the agent
"""

import asyncio
import logging
import socket
import struct
import uuid
import random
import os
import warnings
import json

# audioop is deprecated in 3.11+ but still available in 3.12
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants

load_dotenv(override=True)

logger = logging.getLogger("sip_bridge")


# ─────────────────────────────────────────────────────────────────────────────
# Configuration (loaded from environment)
# ─────────────────────────────────────────────────────────────────────────────

EXOTEL_SIP_HOST = os.getenv("EXOTEL_SIP_HOST", "pstn.in1.exotel.com")
EXOTEL_SIP_PORT = int(os.getenv("EXOTEL_SIP_PORT", "5070"))
EXOTEL_CUSTOMER_IP = os.getenv("EXOTEL_CUSTOMER_IP", "13.234.150.174")
EXOTEL_CUSTOMER_SIP_PORT = int(os.getenv("EXOTEL_CUSTOMER_SIP_PORT", "5061"))
EXOTEL_MEDIA_IP = os.getenv("EXOTEL_MEDIA_IP", "13.234.150.174")
EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID", "08044319240")
EXOTEL_FROM_DOMAIN = os.getenv("EXOTEL_FROM_DOMAIN", "lokaviveka1m.sip.exotel.com")

LK_URL = os.getenv("LIVEKIT_URL")
LK_API_KEY = os.getenv("LIVEKIT_API_KEY")
LK_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# RTP constants
RTP_HEADER_SIZE = 12
PCMU_PAYLOAD_TYPE = 0   # G.711 μ-law
SAMPLE_RATE_SIP = 8000  # G.711 sample rate
SAMPLE_RATE_LK = 48000  # LiveKit sample rate
RESAMPLE_RATIO = SAMPLE_RATE_LK // SAMPLE_RATE_SIP  # 6


# ─────────────────────────────────────────────────────────────────────────────
# RTPMediaBridge: Handles bidirectional audio between RTP and LiveKit
# ─────────────────────────────────────────────────────────────────────────────

class RTPMediaBridge:
    """Bridges RTP (G.711 PCMU over UDP) with a LiveKit room's audio tracks.

    Inbound:  UDP socket → decode G.711 → resample 8k→48k → AudioSource → LiveKit room
    Outbound: LiveKit AudioStream → resample 48k→8k → encode G.711 → UDP socket
    """

    def __init__(self, bind_ip: str, bind_port: int = 0):
        """
        Args:
            bind_ip: IP address to bind the UDP socket to (should be the public IP).
            bind_port: Port to bind to. 0 = OS assigns a free port.
        """
        # Create and bind UDP socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((bind_ip, bind_port))
        self._sock.setblocking(False)

        self.local_port = self._sock.getsockname()[1]
        self._bind_ip = bind_ip
        self._remote_addr: tuple[str, int] | None = None
        self._running = False

        # LiveKit audio source (for publishing phone audio into the room)
        self._audio_source: rtc.AudioSource | None = None
        self._local_track: rtc.LocalAudioTrack | None = None

        # RTP state for outbound packets
        self._rtp_seq = random.randint(0, 0xFFFF)
        self._rtp_ts = random.randint(0, 0xFFFFFFFF)
        self._rtp_ssrc = random.randint(0, 0xFFFFFFFF)

        # Resampling state (audioop.ratecv requires persistent state for smooth audio)
        self._resample_state_in = None   # 8k → 48k
        self._resample_state_out = None  # 48k → 8k

        # Diagnostics
        self._packets_received = 0
        self._packets_sent = 0
        self._first_packet_logged = False

        logger.info(f"[RTP] Bridge bound to {bind_ip}:{self.local_port}")

    def set_remote_endpoint(self, ip: str, port: int):
        """Set the remote RTP endpoint (parsed from the SDP in the 200 OK response)."""
        self._remote_addr = (ip, port)
        logger.info(f"[RTP] Remote endpoint set: {ip}:{port}")

    async def start_inbound(self, room: rtc.Room):
        """Start receiving RTP from Exotel and publishing to LiveKit.

        Creates an AudioSource at 48kHz mono, publishes it as a local track,
        then starts an async task to read UDP packets continuously.
        """
        loop = asyncio.get_running_loop()
        self._audio_source = rtc.AudioSource(SAMPLE_RATE_LK, 1, loop=loop)
        self._local_track = rtc.LocalAudioTrack.create_audio_track(
            "sip_microphone", self._audio_source
        )

        # Publish the track so the agent can hear the phone user
        await room.local_participant.publish_track(self._local_track)
        logger.info("[RTP] Local audio track published to LiveKit room")

        self._running = True
        asyncio.create_task(self._rtp_receive_loop(loop))

    async def _rtp_receive_loop(self, loop: asyncio.AbstractEventLoop):
        """Continuously read RTP UDP packets, decode G.711, push to LiveKit AudioSource."""
        logger.info("[RTP] Inbound receive loop started")

        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 4096)
            except (OSError, asyncio.CancelledError):
                break
            except Exception as e:
                logger.debug(f"[RTP] Recv error: {e}")
                await asyncio.sleep(0.001)
                continue

            if len(data) <= RTP_HEADER_SIZE:
                continue  # Not a valid RTP packet

            # Log first packet for diagnostics
            if not self._first_packet_logged:
                logger.info(f"[RTP] First packet received from {addr} ({len(data)} bytes)")
                self._first_packet_logged = True

            self._packets_received += 1

            # Extract RTP payload (skip 12-byte header)
            # Header: V(2)|P(1)|X(1)|CC(4) | M(1)|PT(7) | Seq(16) | TS(32) | SSRC(32)
            payload = data[RTP_HEADER_SIZE:]

            try:
                # Decode G.711 μ-law → PCM 16-bit linear at 8kHz
                pcm_8k = audioop.ulaw2lin(payload, 2)

                # Resample 8kHz → 48kHz with state for continuity
                pcm_48k, self._resample_state_in = audioop.ratecv(
                    pcm_8k, 2, 1, SAMPLE_RATE_SIP, SAMPLE_RATE_LK, self._resample_state_in
                )

                # Calculate samples_per_channel for the AudioFrame
                # Each sample is 2 bytes (int16), mono
                samples_per_channel = len(pcm_48k) // 2

                # Create AudioFrame and push to LiveKit
                frame = rtc.AudioFrame(
                    data=pcm_48k,
                    sample_rate=SAMPLE_RATE_LK,
                    num_channels=1,
                    samples_per_channel=samples_per_channel,
                )
                await self._audio_source.capture_frame(frame)

            except Exception as e:
                logger.error(f"[RTP] Inbound decode error: {e}")

        logger.info(f"[RTP] Inbound loop ended. Total packets received: {self._packets_received}")

    async def send_to_rtp(self, frame: rtc.AudioFrame):
        """Encode a LiveKit AudioFrame to G.711 PCMU and send as RTP over UDP.

        Args:
            frame: AudioFrame from the agent's audio track (typically 48kHz mono).
        """
        if not self._remote_addr:
            return

        try:
            # Get raw PCM bytes from the AudioFrame
            # frame.data is a memoryview cast to 'h' (int16), we need raw bytes
            raw_pcm = bytes(frame.data.cast("b"))

            # Resample from frame's sample rate → 8kHz with persistent state
            pcm_8k, self._resample_state_out = audioop.ratecv(
                raw_pcm, 2, 1, frame.sample_rate, SAMPLE_RATE_SIP, self._resample_state_out
            )

            # Encode PCM linear → G.711 μ-law
            ulaw_payload = audioop.lin2ulaw(pcm_8k, 2)

            # Build RTP header
            self._rtp_seq = (self._rtp_seq + 1) & 0xFFFF
            # Timestamp increments by the number of 8kHz samples in this packet
            samples_in_packet = len(pcm_8k) // 2
            self._rtp_ts = (self._rtp_ts + samples_in_packet) & 0xFFFFFFFF

            header = struct.pack(
                "!BBHII",
                0x80,                # V=2, P=0, X=0, CC=0
                PCMU_PAYLOAD_TYPE,   # M=0, PT=0 (PCMU)
                self._rtp_seq,
                self._rtp_ts,
                self._rtp_ssrc,
            )

            packet = header + ulaw_payload
            self._sock.sendto(packet, self._remote_addr)
            self._packets_sent += 1

        except Exception as e:
            logger.error(f"[RTP] Outbound send error: {e}")

    def stop(self):
        """Stop the RTP bridge and close the UDP socket."""
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        logger.info(
            f"[RTP] Bridge stopped. "
            f"Packets received: {self._packets_received}, sent: {self._packets_sent}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ExotelSipClient: Handles SIP signaling (INVITE → 200 OK → ACK) over TCP
# ─────────────────────────────────────────────────────────────────────────────

class ExotelSipClient:
    """Manages SIP signaling with Exotel over TCP.

    Sends a SIP INVITE with SDP offering PCMU at the bridge's RTP port,
    waits for 200 OK, parses the remote SDP, and sends ACK.
    """

    def __init__(self, callee: str, rtp_port: int):
        """
        Args:
            callee: Destination phone number.
            rtp_port: Local RTP port to advertise in the SDP.
        """
        self.callee = callee
        self.rtp_port = rtp_port

        # SIP transaction identifiers
        self._branch = f"z9hG4bK-{uuid.uuid4().hex}"
        self._tag = f"trunk{random.randint(10000, 99999)}"
        self._call_id = str(uuid.uuid4())

        # TCP connection handles
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    def _build_sdp(self) -> str:
        """Build an SDP body offering only G.711 PCMU (payload type 0).

        Offering only PCMU eliminates codec negotiation ambiguity — we know
        exactly what Exotel will send back, simplifying the RTP decode path.
        """
        return (
            f"v=0\r\n"
            f"o=- {random.randint(1_000_000_000, 2_000_000_000)} "
            f"{random.randint(1_000_000_000, 2_000_000_000)} IN IP4 {EXOTEL_MEDIA_IP}\r\n"
            f"s=-\r\n"
            f"c=IN IP4 {EXOTEL_MEDIA_IP}\r\n"
            f"t=0 0\r\n"
            f"m=audio {self.rtp_port} RTP/AVP 0 101\r\n"
            f"a=rtpmap:0 PCMU/8000\r\n"
            f"a=rtpmap:101 telephone-event/8000\r\n"
            f"a=fmtp:101 0-15\r\n"
            f"a=ptime:20\r\n"
            f"a=sendrecv\r\n"
        )

    def _build_invite(self) -> bytes:
        """Build a SIP INVITE request with SDP body."""
        sdp = self._build_sdp()
        content_length = len(sdp.encode())

        invite = (
            f"INVITE sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0\r\n"
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};"
            f"branch={self._branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;"
            f"tag={self._tag}\r\n"
            f"To: <sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>\r\n"
            f"Call-ID: {self._call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Contact: <sip:{EXOTEL_CALLER_ID}@{EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};"
            f"transport=tcp>\r\n"
            f"Supported: 100rel, timer\r\n"
            f"Allow: INVITE, ACK, CANCEL, BYE, OPTIONS, UPDATE\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {content_length}\r\n"
            f"\r\n"
            f"{sdp}"
        )
        return invite.encode()

    def _build_ack(self, to_tag: str | None = None) -> bytes:
        """Build a SIP ACK request."""
        to_line = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>"
        if to_tag:
            to_line += f";tag={to_tag}"

        ack = (
            f"ACK sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0\r\n"
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};"
            f"branch={self._branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;"
            f"tag={self._tag}\r\n"
            f"To: {to_line}\r\n"
            f"Call-ID: {self._call_id}\r\n"
            f"CSeq: 1 ACK\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return ack.encode()

    def _build_bye(self, to_tag: str | None = None) -> bytes:
        """Build a SIP BYE request to terminate the call."""
        to_line = f"<sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT}>"
        if to_tag:
            to_line += f";tag={to_tag}"

        bye = (
            f"BYE sip:{self.callee}@{EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} SIP/2.0\r\n"
            f"Via: SIP/2.0/TCP {EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};"
            f"branch=z9hG4bK-{uuid.uuid4().hex};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: \"{EXOTEL_CALLER_ID}\" <sip:{EXOTEL_CALLER_ID}@{EXOTEL_FROM_DOMAIN}>;"
            f"tag={self._tag}\r\n"
            f"To: {to_line}\r\n"
            f"Call-ID: {self._call_id}\r\n"
            f"CSeq: 2 BYE\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return bye.encode()

    async def connect(self):
        """Open the TCP connection to Exotel's SIP gateway."""
        logger.info(f"[SIP] Connecting to {EXOTEL_SIP_HOST}:{EXOTEL_SIP_PORT} via TCP...")
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(EXOTEL_SIP_HOST, EXOTEL_SIP_PORT),
            timeout=10.0,
        )
        logger.info("[SIP] TCP connection established")

    async def send_invite(self) -> dict | None:
        """Send SIP INVITE, wait for 200 OK, and return the parsed remote SDP info.

        Returns:
            dict with 'remote_ip', 'remote_port', 'to_tag' on success, None on failure.
        """
        if not self._writer or not self._reader:
            raise RuntimeError("SIP TCP connection not established. Call connect() first.")

        invite = self._build_invite()
        logger.info(f"[SIP] Sending INVITE to {self.callee}...")
        self._writer.write(invite)
        await self._writer.drain()

        # Read responses until we get a final response (2xx, 4xx, 5xx, 6xx)
        return await self._wait_for_answer()

    async def _wait_for_answer(self) -> dict | None:
        """Read SIP responses from the TCP stream until a final response arrives.

        Handles provisional responses (100 Trying, 180 Ringing) and waits for
        200 OK with SDP body containing the remote RTP endpoint.
        """
        buffer = b""

        while True:
            try:
                chunk = await asyncio.wait_for(self._reader.read(8192), timeout=30.0)
            except asyncio.TimeoutError:
                logger.error("[SIP] Timed out waiting for response")
                return None

            if not chunk:
                logger.error("[SIP] Connection closed by remote")
                return None

            buffer += chunk

            # Process complete SIP messages in the buffer
            while b"\r\n\r\n" in buffer:
                header_end = buffer.index(b"\r\n\r\n")
                header_block = buffer[:header_end].decode(errors="replace")
                remaining = buffer[header_end + 4:]

                # Parse headers
                header_lines = header_block.split("\r\n")
                status_line = header_lines[0] if header_lines else ""

                headers = {}
                for line in header_lines[1:]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip().lower()] = value.strip()

                # Read the body if Content-Length is present
                content_length = int(headers.get("content-length", "0"))
                if content_length > 0:
                    # We need at least content_length bytes in remaining
                    if len(remaining) < content_length:
                        # Not enough data yet, put headers back and wait for more
                        break
                    body = remaining[:content_length].decode(errors="replace")
                    buffer = remaining[content_length:]
                else:
                    body = ""
                    buffer = remaining

                # Process the SIP response
                logger.info(f"[SIP] Response: {status_line}")

                if status_line.startswith("SIP/2.0 100"):
                    logger.info("[SIP] 100 Trying — waiting...")
                    continue

                elif status_line.startswith("SIP/2.0 180") or status_line.startswith("SIP/2.0 183"):
                    logger.info("[SIP] Ringing — phone is ringing...")
                    continue

                elif status_line.startswith("SIP/2.0 200"):
                    logger.info("[SIP] 200 OK — call answered!")

                    # Parse remote RTP endpoint from SDP body
                    remote_ip, remote_port = self._parse_sdp(body)

                    # Extract To tag
                    to_tag = None
                    to_header = headers.get("to", "")
                    if "tag=" in to_header:
                        to_tag = to_header.split("tag=")[1].split(";")[0].strip()

                    # Send ACK
                    ack = self._build_ack(to_tag)
                    logger.info("[SIP] Sending ACK...")
                    self._writer.write(ack)
                    await self._writer.drain()
                    logger.info("[SIP] ACK sent. Call is established.")

                    return {
                        "remote_ip": remote_ip,
                        "remote_port": remote_port,
                        "to_tag": to_tag,
                    }

                elif status_line.startswith("SIP/2.0 4") or \
                     status_line.startswith("SIP/2.0 5") or \
                     status_line.startswith("SIP/2.0 6"):
                    logger.error(f"[SIP] Call failed: {status_line}")
                    return None

    def _parse_sdp(self, sdp: str) -> tuple[str | None, int]:
        """Parse the SDP body to extract the remote media IP and port.

        Args:
            sdp: The SDP body string from the 200 OK response.

        Returns:
            Tuple of (remote_ip, remote_port).
        """
        remote_ip = None
        remote_port = 0

        for line in sdp.splitlines():
            line = line.strip()
            if line.startswith("c=IN IP4"):
                remote_ip = line.split()[-1]
            elif line.startswith("m=audio"):
                parts = line.split()
                if len(parts) >= 2:
                    remote_port = int(parts[1])

        logger.info(f"[SIP] Parsed remote SDP: {remote_ip}:{remote_port}")
        return remote_ip, remote_port

    async def send_bye(self, to_tag: str | None = None):
        """Send a SIP BYE to terminate the call."""
        if self._writer and not self._writer.is_closing():
            try:
                bye = self._build_bye(to_tag)
                logger.info("[SIP] Sending BYE...")
                self._writer.write(bye)
                await self._writer.drain()
                logger.info("[SIP] BYE sent")
            except Exception as e:
                logger.warning(f"[SIP] Error sending BYE: {e}")

    async def close(self):
        """Close the SIP TCP connection."""
        if self._writer and not self._writer.is_closing():
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        logger.info("[SIP] TCP connection closed")


# ─────────────────────────────────────────────────────────────────────────────
# Agent Audio Forwarder: Subscribes to agent track and sends to RTP
# ─────────────────────────────────────────────────────────────────────────────

async def _forward_agent_audio_to_rtp(
    track: rtc.Track,
    rtp_bridge: RTPMediaBridge,
    participant_identity: str,
):
    """Subscribe to a LiveKit audio track and forward each frame to the RTP bridge.

    This runs as a long-lived async task for the duration of the call.
    """
    logger.info(f"[BRIDGE] Starting audio forward: {participant_identity} → RTP")

    audio_stream = rtc.AudioStream(track, sample_rate=SAMPLE_RATE_LK, num_channels=1)

    try:
        async for event in audio_stream:
            await rtp_bridge.send_to_rtp(event.frame)
    except asyncio.CancelledError:
        logger.info(f"[BRIDGE] Audio forward cancelled for {participant_identity}")
    except Exception as e:
        logger.error(f"[BRIDGE] Audio forward error: {e}")
    finally:
        await audio_stream.aclose()
        logger.info(f"[BRIDGE] Audio forward ended for {participant_identity}")


# ─────────────────────────────────────────────────────────────────────────────
# run_bridge(): Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

async def run_bridge(
    phone_number: str,
    agent_type: str = "invoice",
    room_name: str | None = None,
):
    """Orchestrates the entire SIP-to-LiveKit bridge.

    This function is called from outbound_call.py as an asyncio task.
    It joins the EXISTING LiveKit room (created by outbound_call.py),
    establishes a SIP call to Exotel, and bridges audio bidirectionally.

    Args:
        phone_number: Destination phone number.
        agent_type: Type of agent dispatched to the room.
        room_name: Name of the existing LiveKit room to join.
                   If None, creates a new room (backwards compatibility).
    """
    # ── Fallback: create room name if not provided ──────────────────────
    if room_name is None:
        room_name = f"sip-bridge-{phone_number}-{uuid.uuid4().hex[:6]}"
        logger.warning(
            f"[BRIDGE] No room_name provided — using generated name: {room_name}. "
            f"This means a separate room will be created. "
            f"For proper operation, pass room_name from outbound_call.py."
        )

    logger.info(f"[BRIDGE] Starting bridge for {phone_number} in room {room_name}")

    # ── Initialize components ───────────────────────────────────────────
    rtp_bridge = RTPMediaBridge(bind_ip=EXOTEL_MEDIA_IP)
    sip_client = ExotelSipClient(callee=phone_number, rtp_port=rtp_bridge.local_port)

    room = rtc.Room()
    forward_tasks: list[asyncio.Task] = []
    sip_result = None

    try:
        # ── Step 1: Register event handlers BEFORE connecting ───────────
        # This prevents the race condition where the agent publishes audio
        # before we're ready to receive it.

        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(
                    f"[BRIDGE] Agent audio track subscribed: {participant.identity} "
                    f"(track: {publication.sid})"
                )
                # Forward agent audio → RTP → Exotel → Phone
                task = asyncio.create_task(
                    _forward_agent_audio_to_rtp(track, rtp_bridge, participant.identity)
                )
                forward_tasks.append(task)

        @room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"[BRIDGE] Participant disconnected: {participant.identity}")

        # ── Step 2: Generate token and connect to room ──────────────────
        logger.info(f"[BRIDGE] Connecting to LiveKit room: {room_name}")

        token = (
            AccessToken(LK_API_KEY, LK_API_SECRET)
            .with_identity(f"sip-phone-{phone_number}")
            .with_name(f"Phone: {phone_number}")
            .with_metadata(json.dumps({
                "source": "exotel_bridge",
                "phone": phone_number,
                "agent_type": agent_type,
            }))
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )

        await room.connect(LK_URL, token)
        logger.info(f"[BRIDGE] Connected to LiveKit room: {room_name}")

        # ── Step 3: Publish local audio track (Phone → Agent) ───────────
        # Start inbound RTP handling (creates AudioSource + publishes track)
        await rtp_bridge.start_inbound(room)
        logger.info("[BRIDGE] RTP inbound started — local audio track published")

        # ── Step 4: Start SIP call ──────────────────────────────────────
        logger.info(f"[BRIDGE] Initiating SIP call to {phone_number}")

        await sip_client.connect()
        sip_result = await sip_client.send_invite()

        if not sip_result:
            logger.error("[BRIDGE] SIP call failed — no 200 OK received")
            return

        # ── Step 5: Configure RTP endpoint from SDP ─────────────────────
        remote_ip = sip_result.get("remote_ip")
        remote_port = sip_result.get("remote_port", 0)

        if remote_ip and remote_port:
            rtp_bridge.set_remote_endpoint(remote_ip, remote_port)
        else:
            logger.error(f"[BRIDGE] Invalid remote RTP endpoint: {remote_ip}:{remote_port}")
            return

        # ── Step 6: Bridge is active — keep alive ───────────────────────
        logger.info(
            f"[BRIDGE] ✅ Bridge ACTIVE — audio flowing between "
            f"LiveKit room '{room_name}' and phone {phone_number}"
        )

        # Monitor connection health
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(2)

            # Periodic diagnostics (every ~30 seconds)
            if rtp_bridge._packets_received % 1500 == 0 and rtp_bridge._packets_received > 0:
                logger.info(
                    f"[BRIDGE] Status: RX={rtp_bridge._packets_received}, "
                    f"TX={rtp_bridge._packets_sent}"
                )

        logger.info("[BRIDGE] Room disconnected — ending bridge")

    except asyncio.CancelledError:
        logger.info("[BRIDGE] Bridge task cancelled")
    except Exception as e:
        logger.error(f"[BRIDGE] Unexpected error: {e}", exc_info=True)
    finally:
        # ── Cleanup ─────────────────────────────────────────────────────
        logger.info("[BRIDGE] Cleaning up...")

        # Cancel all audio forward tasks
        for task in forward_tasks:
            task.cancel()
        if forward_tasks:
            await asyncio.gather(*forward_tasks, return_exceptions=True)

        # Stop RTP bridge
        rtp_bridge.stop()

        # Send BYE to Exotel
        to_tag = sip_result.get("to_tag") if sip_result else None
        await sip_client.send_bye(to_tag)
        await sip_client.close()

        # Disconnect from room
        await room.disconnect()

        logger.info("[BRIDGE] Cleanup complete")


# ─────────────────────────────────────────────────────────────────────────────
# Standalone execution (for testing)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    PHONE = "08697421450"
    try:
        asyncio.run(run_bridge(PHONE))
    except KeyboardInterrupt:
        pass

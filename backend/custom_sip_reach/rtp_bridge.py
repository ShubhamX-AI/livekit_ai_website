"""
RTP Media Bridge — bidirectional audio between LiveKit and SIP/RTP.

Handles:
  • Binding a UDP socket for RTP
  • Receiving inbound RTP, decoding G.711, resampling to 48 kHz, pushing to LiveKit
  • Receiving LiveKit audio, resampling to 8 kHz, encoding G.711, sending as RTP
  • Buffering agent audio while SIP INVITE is in progress
"""

import asyncio
import collections
import logging
import random
import socket
import struct
import time
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

from livekit import rtc

from .config import (
    PCMA_PAYLOAD_TYPE,
    PCMU_PAYLOAD_TYPE,
    RTP_HEADER_SIZE,
    SAMPLE_RATE_LK,
    SAMPLE_RATE_SIP,
    MAX_FRAME_BUFFER,
)

logger = logging.getLogger("sip_bridge_v3")


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
        self._sock.bind(("0.0.0.0", bind_port))
        self._sock.setblocking(False)
        self.local_port = self._sock.getsockname()[1]
        logger.info(
            f"[RTP] Socket bound 0.0.0.0:{self.local_port} "
            f"| SDP advertises {public_ip}:{self.local_port}"
        )

        self._remote_addr: tuple[str, int] | None = None
        self._running = False
        self.negotiated_pt = PCMA_PAYLOAD_TYPE

        self._audio_source: rtc.AudioSource | None = None
        self._local_track: rtc.LocalAudioTrack | None = None

        self._rtp_seq = random.randint(0, 0xFFFF)
        self._rtp_ts = random.randint(0, 0xFFFFFFFF)
        self._rtp_ssrc = random.randint(0, 0xFFFFFFFF)

        self._rs_in = None  # resample state inbound
        self._rs_out = None  # resample state outbound

        self._rx = 0
        self._tx = 0
        self._first_rx = False
        self._first_tx = False
        self._last_rx_ts: float | None = None

        # Buffer agent frames until set_remote_endpoint() is called
        self._frame_buffer: collections.deque = collections.deque(
            maxlen=MAX_FRAME_BUFFER
        )

        # ptime accumulator: collect PCM until we have exactly 20ms to send.
        # At 8kHz, 16-bit mono: 20ms = 160 samples = 320 bytes of PCM.
        # G.711 encodes 1:1, so payload = 160 bytes. Total RTP = 172 bytes.
        # LiveKit sends 10ms frames, so we pack 2 frames → 1 RTP packet.
        self._PTIME_BYTES = 320  # 20ms at 8kHz 16-bit
        self._pcm_accumulator = b""

    def set_remote_endpoint(self, ip: str, port: int, pt: int = PCMA_PAYLOAD_TYPE):
        self._remote_addr = (ip, port)
        self.negotiated_pt = pt
        logger.info(f"[RTP] Remote endpoint → {ip}:{port} PT={pt}")

    async def start_inbound(self, room: rtc.Room):
        self._audio_source = rtc.AudioSource(SAMPLE_RATE_LK, 1)
        self._local_track = rtc.LocalAudioTrack.create_audio_track(
            "sip_audio", self._audio_source
        )
        # ← ADD THIS: tell the agent session this is a microphone track
        publish_options = rtc.TrackPublishOptions(
            source=rtc.TrackSource.SOURCE_MICROPHONE
        )
        await room.local_participant.publish_track(self._local_track, publish_options)
        self._running = True
        self._recv_queue: asyncio.Queue = asyncio.Queue()

        # add_reader works with uvloop — sock_recvfrom does NOT
        loop = asyncio.get_running_loop()
        loop.add_reader(self._sock.fileno(), self._on_rtp_readable)

        task = asyncio.create_task(self._recv_loop())

        def _on_recv_done(t: asyncio.Task):
            if t.cancelled():
                logger.info("[RTP] recv_loop cancelled")
            elif t.exception():
                logger.error("[RTP] recv_loop DIED", exc_info=t.exception())
            else:
                logger.info("[RTP] recv_loop exited cleanly")

        task.add_done_callback(_on_recv_done)
        logger.info(
            f"[RTP] Inbound loop started, listening on 0.0.0.0:{self.local_port}"
        )

    def _on_rtp_readable(self):
        """Called by event loop when UDP socket has data. Works with uvloop."""
        try:
            data, addr = self._sock.recvfrom(4096)
            self._recv_queue.put_nowait((data, addr))
        except BlockingIOError:
            pass  # no data yet, ignore
        except Exception as e:
            logger.error(f"[RTP] recvfrom error: {e}")

    async def _recv_loop(self):
        logger.info(f"[RTP] recv_loop STARTED port={self.local_port}")
        while self._running:
            try:
                data, addr = await asyncio.wait_for(self._recv_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue  # just check _running flag
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[RTP] Queue error: {e}")
                continue

            if len(data) <= RTP_HEADER_SIZE:
                continue

            if not self._first_rx:
                logger.info(f"[RTP] ✅ First inbound RTP from {addr} ({len(data)} B)")
                self._first_rx = True

            self._rx += 1
            self._last_rx_ts = time.time()
            pt = data[1] & 0x7F
            payload = data[RTP_HEADER_SIZE:]

            try:
                pcm8 = (
                    audioop.alaw2lin(payload, 2)
                    if pt == PCMA_PAYLOAD_TYPE
                    else audioop.ulaw2lin(payload, 2)
                )

                # Boost volume — phone audio is often very quiet after G.711 decode
                pcm8 = audioop.mul(pcm8, 2, 3.0)  # 3x amplification, tune as needed

                pcm48, self._rs_in = audioop.ratecv(
                    pcm8, 2, 1, SAMPLE_RATE_SIP, SAMPLE_RATE_LK, self._rs_in
                )
                frame = rtc.AudioFrame(
                    data=pcm48,
                    sample_rate=SAMPLE_RATE_LK,
                    num_channels=1,
                    samples_per_channel=len(pcm48) // 2,
                )
                await self._audio_source.capture_frame(frame)
            except Exception as e:
                logger.error(f"[RTP] Decode error: {e}", exc_info=True)

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
                chunk = self._pcm_accumulator[: self._PTIME_BYTES]
                self._pcm_accumulator = self._pcm_accumulator[self._PTIME_BYTES :]

                payload = (
                    audioop.lin2alaw(chunk, 2)
                    if self.negotiated_pt == PCMA_PAYLOAD_TYPE
                    else audioop.lin2ulaw(chunk, 2)
                )

                # Timestamp advances by exactly 160 samples (20ms @ 8kHz)
                self._rtp_seq = (self._rtp_seq + 1) & 0xFFFF
                self._rtp_ts = (self._rtp_ts + 160) & 0xFFFFFFFF
                hdr = struct.pack(
                    "!BBHII",
                    0x80,
                    self.negotiated_pt,
                    self._rtp_seq,
                    self._rtp_ts,
                    self._rtp_ssrc,
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
            loop = asyncio.get_event_loop()
            loop.remove_reader(self._sock.fileno())
        except Exception:
            # might not be registered or loop might be closed
            pass
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
                self._public_ip,
                self.local_port,
            )

    def seconds_since_rx(self) -> float | None:
        if self._last_rx_ts is None:
            return None
        return time.time() - self._last_rx_ts

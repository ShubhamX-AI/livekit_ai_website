"""
Main bridge orchestrator — wires SIP, RTP, and LiveKit together.

run_bridge() is the single entry point that:
  1. Acquires a port from the pool
  2. Connects to LiveKit and publishes the SIP audio track
  3. Sends a SIP INVITE to Exotel
  4. Monitors for hang-up signals (BYE, RTP silence, LiveKit disconnect)
  5. Cleans up everything on exit
"""

import asyncio
import json
import logging
import time
import uuid

from livekit import rtc
from livekit.api import AccessToken, VideoGrants

from .config import (
    EXOTEL_MEDIA_IP,
    LK_API_KEY,
    LK_API_SECRET,
    LK_URL,
    NO_RTP_AFTER_ANSWER_SECONDS,
    RTP_SILENCE_TIMEOUT_SECONDS,
    validate_config,
)
from .inbound_listener import (
    ensure_inbound_server,
    register_call_id,
    unregister_call_id,
)
from .port_pool import get_port_pool
from .rtp_bridge import RTPMediaBridge
from .sip_client import ExotelSipClient

logger = logging.getLogger("sip_bridge_v3")


async def run_bridge(
    phone_number: str, agent_type: str = "invoice", room_name: str | None = None
):
    if not validate_config():
        return

    if not room_name:
        room_name = f"sip-bridge-{phone_number}-{uuid.uuid4().hex[:6]}"

    pool = get_port_pool()
    port = await pool.acquire()
    logger.info(f"[BRIDGE] phone={phone_number} room={room_name} rtp_port={port}")

    rtp_bridge = None
    sip_client = None
    forward_task = None
    inbound_bye = None
    room = rtc.Room()

    try:
        await ensure_inbound_server()
        rtp_bridge = RTPMediaBridge(public_ip=EXOTEL_MEDIA_IP, bind_port=port)
        sip_client = ExotelSipClient(callee=phone_number, rtp_port=port)
        inbound_bye = register_call_id(sip_client.call_id)

        @room.on("track_subscribed")
        def on_track(track, publication, participant):
            nonlocal forward_task
            if (
                track.kind == rtc.TrackKind.KIND_AUDIO
                and publication.source == rtc.TrackSource.SOURCE_MICROPHONE
                and forward_task is None
            ):
                logger.info(
                    f"[BRIDGE] Agent audio from {participant.identity} — buffering"
                )
                forward_task = asyncio.create_task(_forward_audio(track, rtp_bridge))

        token = (
            AccessToken(LK_API_KEY, LK_API_SECRET)
            .with_identity(f"sip-{phone_number}")
            .with_metadata(json.dumps({"source": "exotel_bridge"}))
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
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

        answered_at = time.time()

        # Notify agent that call is answered
        try:
            await room.local_participant.publish_data(
                json.dumps({"event": "call_answered"}).encode(),
                topic="sip_bridge_events",
            )
            logger.info("[BRIDGE] Published call_answered event")
        except Exception as e:
            logger.error(f"[BRIDGE] Failed to publish call_answered event: {e}")

        disconnect_reason = "unknown"
        sip_mon = asyncio.create_task(sip_client.wait_for_disconnection())
        while True:
            # ── Signal 1: LiveKit room disconnected ──
            if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
                disconnect_reason = "livekit_disconnected"
                logger.info("[BRIDGE] LiveKit room disconnected")
                break

            # ── Signal 2: SIP BYE on outbound TCP (same connection as INVITE) ──
            if sip_mon.done():
                disconnect_reason = "sip_bye_outbound_tcp"
                logger.info("[BRIDGE] SIP BYE received on outbound TCP")
                break

            # ── Signal 3: SIP BYE on inbound TCP listener (new connection from Exotel) ──
            if inbound_bye and inbound_bye.is_set():
                disconnect_reason = "sip_bye_inbound_tcp"
                logger.info("[BRIDGE] SIP BYE received on inbound TCP listener")
                break

            since_rx = rtp_bridge.seconds_since_rx()

            # ── Signal 4: No RTP ever arrived after answer — call setup failure ──
            if (
                since_rx is None
                and NO_RTP_AFTER_ANSWER_SECONDS > 0
                and (time.time() - answered_at) > NO_RTP_AFTER_ANSWER_SECONDS
            ):
                disconnect_reason = "no_rtp_after_answer"
                logger.error(
                    "[RTP] No inbound RTP after %ss — call never connected, ending",
                    NO_RTP_AFTER_ANSWER_SECONDS,
                )
                break

            # ── Signal 5: RTP was flowing but stopped — caller hung up ──
            if (
                since_rx is not None
                and RTP_SILENCE_TIMEOUT_SECONDS > 0
                and since_rx > RTP_SILENCE_TIMEOUT_SECONDS
            ):
                disconnect_reason = "rtp_silence_after_flow"
                logger.info(
                    "[RTP] No audio for %.0fs (threshold=%ss) — caller hung up",
                    since_rx,
                    RTP_SILENCE_TIMEOUT_SECONDS,
                )
                break

            await asyncio.sleep(1)

        logger.info(f"[BRIDGE] Call ended — reason={disconnect_reason}")

    except Exception as e:
        logger.error(f"[BRIDGE] Error: {e}", exc_info=True)

    finally:
        if forward_task:
            forward_task.cancel()
            try:
                await forward_task
            except asyncio.CancelledError:
                pass

        if sip_client:
            if not (inbound_bye and inbound_bye.is_set()):
                await sip_client.send_bye()
            await sip_client.close()

        if rtp_bridge:
            rtp_bridge.stop()

        await room.disconnect()
        # ← This is the critical step that was missing before
        await pool.release(port)
        logger.info(f"[BRIDGE] Port {port} released")
        if sip_client:
            unregister_call_id(sip_client.call_id)


async def _forward_audio(track: rtc.Track, bridge: RTPMediaBridge):
    stream = rtc.AudioStream(track, sample_rate=48000, num_channels=1)
    async for event in stream:
        await bridge.send_to_rtp(event.frame)

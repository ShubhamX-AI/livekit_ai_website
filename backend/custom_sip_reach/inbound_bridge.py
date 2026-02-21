"""
Main inbound bridge orchestrator — handles incoming SIP INVITEs from Exotel,
wires up RTP, and connects an agent via LiveKit.
"""

import asyncio
import json
import logging
import time
import uuid

from livekit import rtc
from livekit.api import AccessToken, VideoGrants

from .config import (
    EXOTEL_CUSTOMER_IP,
    EXOTEL_CUSTOMER_SIP_PORT,
    EXOTEL_MEDIA_IP,
    LK_API_KEY,
    LK_API_SECRET,
    LK_URL,
    RTP_SILENCE_TIMEOUT_SECONDS,
    validate_config,
)
from .inbound_listener import register_call_id, unregister_call_id
from .port_pool import get_port_pool
from .rtp_bridge import RTPMediaBridge

logger = logging.getLogger("sip_bridge_v3")


async def handle_inbound_call(
    hdrs: dict,
    raw_invite: bytes,
    sdp_body: str,
    writer: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    from_header: str,
    to_header: str,
    call_id: str,
    cseq: str,
    via_headers: list[str],
    record_routes: list[str],
):
    if not validate_config():
        logger.error("[INBOUND] Config validation failed")
        return

    # Extract remote RTP endpoint from Exotel's SDP
    remote_ip, remote_port, pt = None, 0, 8
    for line in sdp_body.splitlines():
        if line.startswith("c=IN IP4 "):
            remote_ip = line.split("c=IN IP4 ")[1].strip()
        elif line.startswith("m=audio "):
            parts = line.split()
            remote_port = int(parts[1])
            if len(parts) > 3:
                pt = int(parts[3])

    if not remote_ip or not remote_port:
        logger.error(
            f"[INBOUND] Failed to extract RTP info from SDP. call-id={call_id}"
        )
        return

    phone_number = "Unknown"
    # To header is what was dialed (the Exotel number)
    if "sip:" in to_header:
        phone_number = to_header.split("sip:")[1].split("@")[0]

    # Map the dialed Exotel number to a specific agent type
    from inbound.config_manager import get_agent_for_number
    logger.info(f"[INBOUND] call-id={call_id} phone={phone_number}")
    agent_type = get_agent_for_number(phone_number)

    # agent_session.py expects room_name to start with {agent_type}-...
    room_name = f"{agent_type}-inbound-{phone_number[-4:] if len(phone_number) >= 4 else phone_number}-{uuid.uuid4().hex[:6]}"

    pool = get_port_pool()
    port = await pool.acquire()
    logger.info(
        f"[INBOUND] call-id={call_id} phone={phone_number} room={room_name} rtp_port={port}"
    )

    rtp_bridge = None
    forward_task = None
    inbound_bye = None
    room = rtc.Room()

    def build_200_ok() -> bytes:
        from .sip_client import ExotelSipClient

        sdp = ExotelSipClient._generate_sdp(port)
        h = ["SIP/2.0 200 OK"]
        for via in via_headers:
            h.append(f"Via: {via}")
        for rr in record_routes:
            h.append(f"Record-Route: {rr}")
        h.append(f"From: {from_header}")
        h.append(f"To: {to_header};tag=inbound-{port}-{uuid.uuid4().hex[:4]}")
        h.append(f"Call-ID: {call_id}")
        h.append(f"CSeq: {cseq}")
        h.append("Supported: 100rel, timer, replaces")
        h.append("Allow: INVITE, ACK, CANCEL, BYE, OPTIONS, UPDATE")
        h.append(
            f"Contact: <sip:{EXOTEL_CUSTOMER_IP}:{EXOTEL_CUSTOMER_SIP_PORT};transport=tcp>"
        )
        h.append("Content-Type: application/sdp")
        h.append(f"Content-Length: {len(sdp.encode())}")

        return ("\r\n".join(h) + "\r\n\r\n" + sdp).encode()

    try:
        inbound_bye = register_call_id(call_id)
        rtp_bridge = RTPMediaBridge(public_ip=EXOTEL_MEDIA_IP, bind_port=port)

        @room.on("track_subscribed")
        def on_track(track, publication, participant):
            nonlocal forward_task
            if (
                track.kind == rtc.TrackKind.KIND_AUDIO
                and publication.source == rtc.TrackSource.SOURCE_MICROPHONE
                and forward_task is None
            ):
                logger.info(
                    f"[INBOUND] Agent audio from {participant.identity} — buffering"
                )
                from .bridge import _forward_audio

                forward_task = asyncio.create_task(_forward_audio(track, rtp_bridge))

        token = (
            AccessToken(LK_API_KEY, LK_API_SECRET)
            .with_identity(f"sip-in-{phone_number}")
            .with_metadata(json.dumps({"source": "exotel_inbound_bridge"}))
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
        await room.connect(LK_URL, token)
        logger.info(f"[INBOUND] LiveKit connected: {room_name}")
        await rtp_bridge.start_inbound(room)

        # Set remote endpoint from what Exotel sent us
        rtp_bridge.set_remote_endpoint(remote_ip, remote_port, pt)

        # Send 200 OK Response
        resp_200 = build_200_ok()
        logger.info("[INBOUND] Sending 200 OK ->")
        writer.write(resp_200)
        await writer.drain()

        # Let agent know call is connected
        try:
            await room.local_participant.publish_data(
                json.dumps({"event": "call_answered"}).encode(),
                topic="sip_bridge_events",
            )
        except Exception as e:
            logger.error(f"[INBOUND] Failed to publish call_answered event: {e}")

        # Watch for BYE and RTP Silence
        disconnect_reason = "unknown"
        while True:
            if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
                disconnect_reason = "livekit_disconnected"
                break

            if inbound_bye and inbound_bye.is_set():
                disconnect_reason = "sip_bye_inbound_tcp"
                break

            since_rx = rtp_bridge.seconds_since_rx()

            if (
                since_rx is not None
                and RTP_SILENCE_TIMEOUT_SECONDS > 0
                and since_rx > RTP_SILENCE_TIMEOUT_SECONDS
            ):
                disconnect_reason = "rtp_silence_after_flow"
                break

            await asyncio.sleep(1)

        logger.info(f"[INBOUND] Call ended — reason={disconnect_reason}")

    except Exception as e:
        logger.error(f"[INBOUND] Error: {e}", exc_info=True)

    finally:
        if forward_task:
            forward_task.cancel()
            try:
                await forward_task
            except asyncio.CancelledError:
                pass

        if rtp_bridge:
            rtp_bridge.stop()

        await room.disconnect()
        await pool.release(port)
        logger.info(f"[INBOUND] Port {port} released")
        unregister_call_id(call_id)

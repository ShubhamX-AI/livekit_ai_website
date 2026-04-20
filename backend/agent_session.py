import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    room_io,
    BackgroundAudioPlayer,
    AudioConfig,
    TurnHandlingOptions,
    NOT_GIVEN,
)
from agents.invoice.invoice_agent import InvoiceAgent
from agents.restaurant.restaurant_agent import RestaurantAgent
from agents.banking.banking_agent import BankingAgent
from agents.tour.tour_agent import TourAgent
from agents.realestate.realestate_agent import RealestateAgent
from agents.distributor.distributor_agent import DistributorAgent
from agents.bandhan_banking.bandhan_banking import BandhanBankingAgent
from agents.ambuja.ambuja_agent import AmbujaAgent
from agents.hirebot.hirebot_agent import HirebotAgent
from agents.kingston.kingston_agent import KingstonAgent
from openai.types.beta.realtime.session import TurnDetection
from livekit.plugins import cartesia
from livekit.plugins import sarvam
from livekit.plugins.openai import realtime
from openai.types.realtime import AudioTranscription
import os
import json
import asyncio


logger = logging.getLogger("agent")
load_dotenv(override=True)


# Register multiple agent
AGENT_TYPES = {
    "invoice": InvoiceAgent,
    "restaurant": RestaurantAgent,
    "bank": BankingAgent,
    "tour": TourAgent,
    "realestate": RealestateAgent,
    "distributor": DistributorAgent,
    "bandhan_banking": BandhanBankingAgent,
    "ambuja": AmbujaAgent,
    "hirebot" : HirebotAgent,
    "kingston" : KingstonAgent
}


async def vyom_demos(ctx: JobContext):

    # Retrive agent name from room name
    room_name = ctx.room.name
    agent_type = room_name.split("-")[0].lower()
    logger.info(f"Agent session starting | room: {room_name} | agent_type: {agent_type}")

    # Initialize correct agent from the start
    AgentClass = AGENT_TYPES.get(agent_type, AmbujaAgent)
    agent_instance = AgentClass(room=ctx.room)

    logger.info(f"Initialized {AgentClass.__name__} for room")


    llm = realtime.RealtimeModel(
        model="gpt-realtime",
        input_audio_transcription=AudioTranscription(
            model="gpt-4o-mini-transcribe",
            prompt=(
                "The speaker is multilingual and switches between different languages dynamically. "
                "Transcribe exactly what is spoken without translating."
            ),
        ),
        input_audio_noise_reduction="near_field",
        turn_detection=TurnDetection(
            type="semantic_vad",
            eagerness="high",
            create_response=True,
            interrupt_response=False,
        ),
        modalities=["text"],
        api_key=os.getenv("OPENAI_API_KEY", ""),
    )

    match agent_type:
        case "hirebot":
            tts = cartesia.TTS(
                model="sonic-3", 
                voice=os.getenv("CARTESIA_VOICE_ID_HIREBOT", ""),
                api_key=os.getenv("CARTESIA_API_KEY", ""),
                )
        case "bandhan_banking" | "kingston" :
            tts = sarvam.TTS(
                model="bulbul:v3", 
                target_language_code="en-IN",
                pace=1.1,
                speaker=os.getenv("SARVAM_SPEAKER_BANDHAN_BANKING", ""),
                api_key=os.getenv("SARVAM_API_KEY", ""),
                )
        case _:
            tts = cartesia.TTS(
                model="sonic-3", 
                speed=1.1,
                voice=os.getenv("CARTESIA_VOICE_ID", ""),
                api_key=os.getenv("CARTESIA_API_KEY", ""),
                )
    
    session = AgentSession(
        llm=llm,
        tts=tts,
        preemptive_generation=True,
        use_tts_aligned_transcript=True,
        aec_warmup_duration=0.8, 
        turn_handling=TurnHandlingOptions(
                turn_detection="realtime_llm",
                endpointing={
                    "mode": "dynamic",
                    "min_delay": 0.3,
                    "max_delay": 3.0,
                },
                interruption={
                    "mode": "adaptive",
                    "min_duration": 0.8,
                    "min_words": 2,
                    "discard_audio_if_uninterruptible": True,
                    "false_interruption_timeout": 2.0,
                    "resume_false_interruption": True,
                },
        )
    )

    # --- START SESSION ---
    logger.info("Starting AgentSession...")
    try:

        # --- Background Audio Start ---
        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(
                os.path.join(os.path.dirname(__file__), "bg_audio", "office-ambience_48k.wav"),
                volume=0.4,
            ),
            thinking_sound=AudioConfig(
                os.path.join(os.path.dirname(__file__), "bg_audio", "typing-sound_48k.wav"),
                volume=0.5,
            ),
        )

        # Configure room options
        room_options = room_io.RoomOptions(
            text_input=False,  # Disabled: RealtimeModel handles transcription
            audio_input=True,
            audio_output=True,
            close_on_disconnect=True,
            delete_room_on_close=True,
        )
        
        await session.start(
            agent=agent_instance,
            room=ctx.room,
            room_options=room_options,
        )
        logger.info("AgentSession started successfully")

        # --- EVENT TRACKING FOR CALL ANSWERED ---
        # We register `data_received` EARLY (before wait_for_participant) so we never
        # miss the call_answered signal from the Exotel bridge, even if it connects
        # while the agent is still booting up (common in inbound calls).
        audio_ready = asyncio.Event()

        @ctx.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            if data.topic == "sip_bridge_events":
                try:
                    msg = json.loads(data.data.decode())
                    if msg.get("event") == "call_answered":
                        logger.info("Bridge reported call answered via data message (SIP 200 OK)")
                        audio_ready.set()
                except (json.JSONDecodeError, TypeError):
                    pass

        # WAIT for participant
        logger.info("Waiting for participant...")
        participant = await ctx.wait_for_participant()

        is_sip = participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP

        # Also detect Exotel bridge participants (join as sip participants)
        is_exotel_bridge = False
        if participant.metadata:
            try:
                meta = json.loads(participant.metadata)
                is_exotel_bridge = meta.get("source") == "exotel_bridge"
            except (json.JSONDecodeError, TypeError):
                pass

        # (Threshold for welcome message initiation)
        is_phone_call = is_sip or is_exotel_bridge
        logger.info(
            f"Participant joined: {participant.identity} | "
            f"kind={participant.kind} | "
            f"is_sip={is_sip} | "
            f"is_exotel_bridge={is_exotel_bridge}"
        )

        if is_exotel_bridge:
            # Exotel bridge: ONLY trust the `call_answered` data message (registered above).
            # The bridge publishes its audio track immediately on joining — BEFORE the phone
            # even rings — so `track_published` would fire way too early here.
            # Also check if we already received the event before reaching this point.
            pass  # data_received listener above already handles this
        elif is_sip:
            # Standard SIP (Twilio / LiveKit native): audio track is published ONLY after
            # the SIP 200 OK, so track_published IS a reliable answer signal here.
            @ctx.room.on("track_published")
            def on_track_published(publication: rtc.RemoteTrackPublication, p: rtc.RemoteParticipant):
                if p.identity == participant.identity and publication.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info(f"SIP audio track published by {p.identity} — call answered")
                    audio_ready.set()

            # Also check if the track is already there (rare for SIP but harmless)
            for pub in participant.track_publications.values():
                if pub.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info(f"SIP participant {participant.identity} already has an audio track — call answered")
                    audio_ready.set()
                    break

        # --- Background Audio Start ---
        try:
            asyncio.create_task(background_audio.start(room=ctx.room, agent_session=session))
            logger.info("Background audio task spawned")
        except Exception as e:
            logger.error(f"Failed to start background audio: {e}")

        # --- INITIATING SPEECH ---
        if agent_type != "ambuja":
            if is_phone_call:
                logger.info("Waiting for phone call to be answered (SIP or Exotel bridge)...")
                try:
                    await asyncio.wait_for(audio_ready.wait(), timeout=60.0)
                except asyncio.TimeoutError:
                    logger.error("Timed out waiting for call to be answered (60s)")
                    return
                # Small buffer for RTP packets to settle (bridge already waited 0.5s for boot)
                await asyncio.sleep(0.5)

            welcome_message = agent_instance.welcome_message
            agent_instance._allow_interruptions = False  # Ensure welcome message is not interrupted
            logger.info(f"Sending welcome message: '{welcome_message}' for agent: {agent_type}")
            try:
                # Specific to Kingston
                if agent_type == "kingston":
                    await session.generate_reply(instructions=agent_instance.welcome_instructions, allow_interruptions=False)
                else:
                    await session.say(text=welcome_message, allow_interruptions=False)
                logger.info("Welcome message sent successfully")
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}", exc_info=True)
            finally:
                agent_instance._allow_interruptions = NOT_GIVEN  # Revert to default interruption behavior after welcome message

        # --- KEEP ALIVE LOOP ---
        participant_left = asyncio.Event()

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(p: rtc.RemoteParticipant):
            if p.identity == participant.identity:
                logger.info(f"Participant {p.identity} disconnected, ending session.")
                participant_left.set()

        # Keep the task running until the participant leaves or the room is closed
        try:
            while (
                ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED 
                and not participant_left.is_set()
            ):
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Keep-alive loop cancelled")
        logger.info("Session ended.")
    finally:
        # --- PROPER CLEANUP ---
        logger.info("Cleaning up resources...")
        
        # Close in dependency order
        await session.aclose()
        await llm.aclose()
        await tts.aclose()
        logger.info("Cleanup complete")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=vyom_demos,
            agent_name="vyom_demos",
        )
    )

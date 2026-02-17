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
from openai.types.beta.realtime.session import TurnDetection
from livekit.plugins import cartesia
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
            eagerness="low",
            create_response=True,
            interrupt_response=True,
        ),
        modalities=["text"],
        api_key=os.getenv("OPENAI_API_KEY", ""),
    )
    tts = cartesia.TTS(
        model="sonic-3", 
        voice=os.getenv("CARTESIA_VOICE_ID", "") if agent_type != "hirebot" else os.getenv("CARTESIA_VOICE_ID_HIREBOT", ""),
        api_key=os.getenv("CARTESIA_API_KEY", ""),
        )
    
    session = AgentSession(
        llm=llm,
        tts=tts,
        preemptive_generation=True,
        use_tts_aligned_transcript=True,
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

        # WAIT for participant
        logger.info("Waiting for participant...")
        participant = await ctx.wait_for_participant()

        is_sip = participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP

        # Also detect Exotel bridge participants (they join as regular WebRTC
        # participants with metadata containing "source": "exotel_bridge")
        is_exotel_bridge = False
        if participant.metadata:
            try:
                meta = json.loads(participant.metadata)
                is_exotel_bridge = meta.get("source") == "exotel_bridge"
            except (json.JSONDecodeError, TypeError):
                pass

        is_phone_call = is_sip or is_exotel_bridge
        logger.info(
            f"Participant joined: {participant.identity}, "
            f"kind={participant.kind}, is_sip={is_sip}, "
            f"is_exotel_bridge={is_exotel_bridge}"
        )

        audio_ready = asyncio.Event()

        @ctx.room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, p: rtc.RemoteParticipant):
            if p.identity == participant.identity and publication.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info("SIP/Bridge audio track published — call answered")
                audio_ready.set()

        # --- Background Audio Start ---
        try:
            asyncio.create_task(background_audio.start(room=ctx.room, agent_session=session))
            logger.info("Background audio task spawned")
        except Exception as e:
            logger.error(f"Failed to start background audio: {e}")

        @ctx.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            if data.topic == "lk.transcription":
                pass # Ignore transcription logs

        # --- INITIATING SPEECH ---
        if agent_type != "ambuja":
            if is_phone_call:
                logger.info("Waiting for phone call to be answered (SIP or Exotel bridge)...")
                await audio_ready.wait()
                # Buffer for RTP stabilization - longer delay ensures welcome message is heard
                await asyncio.sleep(2.0)

            welcome_message = agent_instance.welcome_message
            logger.info(f"Sending welcome message: '{welcome_message}' for agent: {agent_type}")
            try:
                await session.say(text=welcome_message, allow_interruptions=True)
                logger.info("Welcome message sent successfully")
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}", exc_info=True)

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

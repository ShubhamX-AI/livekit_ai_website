import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.plugins import silero
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    cli,
    room_io,
    BackgroundAudioPlayer,
    AudioConfig,
)
from livekit.plugins import noise_cancellation
from agents.web.web_agent import Webagent
from agents.invoice.invoice_agent import InvoiceAgent
from agents.restaurant.restaurant_agent import RestaurantAgent
from agents.banking.banking_agent import BankingAgent
from agents.tour.tour_agent import TourAgent
from agents.realestate.realestate_agent import RealestateAgent
from agents.distributor.distributor_agent import DistributorAgent
from agents.bandhan_banking.bandhan_banking import BandhanBankingAgent
from agents.ambuja.ambuja_agent import AmbujaAgent
from openai.types.beta.realtime.session import TurnDetection
from livekit.plugins import cartesia
from livekit.plugins.openai import realtime
from openai.types.realtime import AudioTranscription
import os
import json
import asyncio
from typing import cast
from inbound.config_manager import get_agent_for_number
# from utils.elevenlabs_nonstream_tts import ElevenLabsNonStreamingTTS

# Recording input
# from recording.recording import start_audio_recording, record_participant_audio, start_audio_recording2

logger = logging.getLogger("agent")
load_dotenv(override=True)


# Register multiple agent
AGENT_TYPES = {
    "web": Webagent,
    "invoice": InvoiceAgent,
    "restaurant": RestaurantAgent,
    "bank": BankingAgent,
    "tour": TourAgent,
    "realestate": RealestateAgent,
    "distributor": DistributorAgent,
    "bandhan_banking": BandhanBankingAgent,
    "ambuja": AmbujaAgent,
}


# initialize the agent
server = AgentServer(
    api_key=os.getenv("LIVEKIT_API_KEY"),
    api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ws_url=os.getenv("LIVEKIT_URL"),
    job_memory_warn_mb=1024,
)


# # Helper function to handle the Egress call in background
# async def trigger_recording(room_name, agent_type):
#     try:
#         info = await start_audio_recording(room_name=room_name, agent_name=agent_type)
#         logger.info(f"Egress started successfully: {info}")
#     except Exception as e:
#         logger.error(f"Failed to start Egress: {e}")


@server.rtc_session()
async def my_agent(ctx: JobContext):
    session = AgentSession(
        llm=realtime.RealtimeModel(
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
            api_key=cast(str, os.getenv("OPENAI_API_KEY")),
        ),
        tts=cartesia.TTS(
            model="sonic-3", 
            voice="faf0731e-dfb9-4cfc-8119-259a79b27e12",
            api_key=os.getenv("CARTESIA_API_KEY"),
            # volume=1.8
            ),
        # tts=ElevenLabsNonStreamingTTS(
        #     voice_id="kL8yauEAuyf6botQt9wa",  # Monika - Indian Female
        #     model="eleven_v3",
        #     api_key=cast(str, os.getenv("ELEVENLABS_API_KEY")),
        # ),
        preemptive_generation=True,
        use_tts_aligned_transcript=False,
    )

    # --- Custom Background Audio Setup ---
    background_audio = BackgroundAudioPlayer(
        ambient_sound=AudioConfig(
            os.path.join(
                os.path.dirname(__file__), "bg_audio", "office-ambience_48k.wav"
            ),
            volume=0.4,
        ),
        thinking_sound=AudioConfig(
            os.path.join(os.path.dirname(__file__), "bg_audio", "typing-sound_48k.wav"),
            volume=0.5,
        ),
    )

    # ---- START SESSION ----
    await session.start(
        agent=InvoiceAgent(room=ctx.room),  # Default agent
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Using LiveKit's built-in noise cancellation
                # Note: FFmpeg preprocessing cannot be easily integrated here
                # due to synchronous API constraints in LiveKit's audio pipeline
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # WAIT for participant
    participant = await ctx.wait_for_participant()
    logger.info(
        f"Participant joined: {participant.identity}, metadata={participant.metadata}"
    )

    # Determine agent type based on room metadata or fallback to "web"
    agent_type = "web"

    # Check if SIP call
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        # Check sip status for incomming and outgoing
        if participant.metadata and participant.metadata.strip():
            try:
                metadata = json.loads(participant.metadata)
                if metadata.get("call_type") == "outbound":
                    logger.info("Outbound call detected")
                    agent_type = metadata.get("agent", "web")
                    logger.info(f"Agent type from metadata: {agent_type}")
            except Exception:
                logger.error(
                    "Error parsing agent type from metadata. Getting default agent."
                )
        else:
            logger.info("Inbound call detected")
            called_number = participant.attributes.get("sip.trunkPhoneNumber")
            logger.info(f"Called number: {called_number}")
            if isinstance(called_number, str) and called_number:
                mapped_agent = get_agent_for_number(called_number)
                logger.info(f"Mapped agent: {mapped_agent}")
                if mapped_agent:
                    agent_type = mapped_agent
                    logger.info(f"Using mapped agent {agent_type} for {called_number}")
            else:
                logger.info("No SIP trunk phone number available")

    else:
        # Web call
        try:
            agent_type = json.loads(participant.metadata).get("agent", "web")
        except Exception:
            logger.error(
                "Error parsing agent type from metadata. Getting default agent."
            )

    AgentClass = AGENT_TYPES.get(agent_type, Webagent)

    # Agent instance with agent type
    agent_instance = AgentClass(room=ctx.room)

    # Attach the agent to the session
    session.update_agent(agent=agent_instance)

    # Frontend details for the WEB agent - UI Context Sync
    @ctx.room.on("data_received")
    def _handle_data_received(data: rtc.DataPacket):

        # receive the topic
        topic = getattr(data, "topic", None)
        if topic != "ui.context":
            return
        
        # Receive the payload
        payload = getattr(data, "data", None)
        if isinstance(payload, bytes):
            payload_text = payload.decode("utf-8", errors="ignore")
        else:
            payload_text = str(payload) if payload is not None else ""
        
        try:
            context_payload = json.loads(payload_text)
        except json.JSONDecodeError:
            logger.warning("Invalid ui.context payload - JSON parse failed")
            return
        
        logging.info("📱 UI Context Sync received")
        asyncio.create_task(agent_instance.update_ui_context(context_payload))

    # Start recording in a separate task
    # asyncio.create_task(trigger_recording(ctx.room.name, agent_type))
    # asyncio.create_task(start_audio_recording2(ctx.room.name, agent_type))

    # --- Background Audio Start (before welcome message) ---
    try:
        asyncio.create_task(
            background_audio.start(room=ctx.room, agent_session=session)
        )
        logger.info("Background audio task started")
    except Exception as e:
        logger.warning(f"Could not start background audio: {e}", exc_info=True)

    # --- INITIATING SPEECH (Dynamically changed based on agent) ---
    welcome_message = agent_instance.welcome_message
    await session.say(text=welcome_message, allow_interruptions=True)

    # --- KEEP ALIVE LOOP ---
    # Without this, the function returns and the agent process terminates.
    participant_left = asyncio.Event()

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(p: rtc.RemoteParticipant):
        if p.identity == participant.identity:
            logger.info(f"Participant {p.identity} disconnected, ending session.")
            participant_left.set()

    # Keep the task running until the participant leaves or the room is closed
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED and not participant_left.is_set():
        await asyncio.sleep(1)

    logger.info("Session ended.")


if __name__ == "__main__":
    cli.run_app(server)

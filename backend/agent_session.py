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
            voice="f6141af3-5f94-418c-80ed-a45d450e7e2e",
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

    # --- START SESSION ---
    logger.info("Starting AgentSession...")
    try:
        await session.start(
            # Start with a generic agent, we update it immediately after determining type
            agent=InvoiceAgent(room=ctx.room),
            room=ctx.room,
            # DELETED: noise_cancellation filters as they require LiveKit Cloud
        )
        logger.info("AgentSession started successfully")
    except Exception as e:
        logger.error(f"Failed to start AgentSession: {e}", exc_info=True)
        return

    # WAIT for participant
    logger.info("Waiting for participant...")
    participant = await ctx.wait_for_participant()
    logger.info(
        f"Participant joined: {participant.identity}, kind={participant.kind}, metadata={participant.metadata}"
    )

    # Determine agent type based on room metadata or fallback to "web"
    agent_type = "web"
    
    # Check if SIP call
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        logger.info("SIP Participant detected")
        if participant.metadata and participant.metadata.strip():
            try:
                metadata = json.loads(participant.metadata)
                if metadata.get("call_type") == "outbound":
                    agent_type = metadata.get("agent", "web")
                    logger.info(f"Outbound SIP call, agent_type={agent_type}")
            except Exception as e:
                logger.error(f"Error parsing SIP metadata: {e}")
        else:
            called_number = participant.attributes.get("sip.trunkPhoneNumber")
            logger.info(f"Inbound SIP call to: {called_number}")
            if called_number:
                mapped_agent = get_agent_for_number(called_number)
                if mapped_agent:
                    agent_type = mapped_agent
                    logger.info(f"Mapped SIP number to agent: {agent_type}")
    else:
        # Web call
        try:
            agent_type = json.loads(participant.metadata).get("agent", "web")
            logger.info(f"Web call, agent_type={agent_type}")
        except Exception:
            logger.warning("Could not parse agent_type from web participant metadata, defaulting to 'web'")

    # Initialize the specific Agent Class
    AgentClass = AGENT_TYPES.get(agent_type, Webagent)
    logger.info(f"Initializing Agent instance for: {agent_type} ({AgentClass.__name__})")
    agent_instance = AgentClass(room=ctx.room)

    # Attach the agent to the session
    session.update_agent(agent=agent_instance)
    logger.info(f"Agent session updated with {agent_type} instance")

    # Frontend details for the WEB agent - UI Context Sync
    @ctx.room.on("data_received")
    def _handle_data_received(data: rtc.DataPacket):
        topic = getattr(data, "topic", None)
        if topic != "ui.context":
            return
        
        payload = getattr(data, "data", None)
        if isinstance(payload, bytes):
            payload_text = payload.decode("utf-8", errors="ignore")
        else:
            payload_text = str(payload) if payload is not None else ""
        
        try:
            context_payload = json.loads(payload_text)
            logger.debug(f"UI Context received: {context_payload}")
            asyncio.create_task(agent_instance.update_ui_context(context_payload))
        except Exception as e:
            logger.warning(f"Failed to process ui.context: {e}")

    # --- Background Audio Start ---
    try:
        asyncio.create_task(
            background_audio.start(room=ctx.room, agent_session=session)
        )
        logger.info("Background audio task spawned")
    except Exception as e:
        logger.warning(f"Could not start background audio: {e}")

    # --- INITIATING SPEECH ---
    if agent_type != "ambuja":
        welcome_message = agent_instance.welcome_message
        logger.info(f"Sending welcome message: '{welcome_message}'")
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
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED and not participant_left.is_set():
        await asyncio.sleep(1)

    logger.info(f"Session for participant {participant.identity} ended.")

    logger.info("Session ended.")


if __name__ == "__main__":
    cli.run_app(server)

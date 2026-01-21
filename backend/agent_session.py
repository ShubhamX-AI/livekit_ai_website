import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    cli,
    inference,
    room_io,
    BackgroundAudioPlayer, 
    AudioConfig,           
    # BuiltinAudioClip       
)
from livekit.plugins import noise_cancellation, silero, openai
# from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents.web.web_agent import Webagent
from agents.invoice.invoice_agent import InvoiceAgent
from agents.restaurant.restaurant_agent import RestaurantAgent
from agents.banking.banking_agent import BankingAgent
from agents.tour.tour_agent import TourAgent
from agents.realestate.realestate_agent import RealestateAgent
from agents.distributor.distributor_agent import DistributorAgent
# from livekit.plugins.openai import realtime
from livekit.plugins.openai.realtime import RealtimeModel
from openai.types import realtime
from livekit.plugins import openai  
# from livekit.plugins import cartesia
# from livekit.plugins import gladia
from livekit.plugins import groq
from livekit.plugins import elevenlabs
from openai.types.beta.realtime.session import TurnDetection
import os
import json
import asyncio
from inbound.config_manager import get_agent_for_number

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
}


# initialize the agent
server = AgentServer(
    api_key=os.getenv("LIVEKIT_API_KEY"),
    api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ws_url=os.getenv("LIVEKIT_URL"),
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
        llm=RealtimeModel(
            input_audio_transcription = realtime.AudioTranscription(
                    model="gpt-4o-mini-transcribe",
                    prompt=(
                        "The speaker is multilingual and switches between different languages dynamically. "
                        "Do not force any specific language for transcription. "
                        "Transcribe exactly what is said, preserving the original words and spelling of the language spoken."
                    )
                ),
            input_audio_noise_reduction = "near_field",
            turn_detection=TurnDetection(
                type="semantic_vad",
                eagerness="low",
                create_response=True,
                interrupt_response=True,
            ),
            modalities = ['text'],
            api_key=os.getenv("OPENAI_API_KEY")
        ),
        # stt=groq.STT(
        #     model="whisper-large-v3-turbo",
        #     prompt=(
        #         "The speaker is multilingual and switches between different languages dynamically. "
        #         "Do not force any specific language for transcription. "
        #         "Transcribe exactly what is said, preserving the original words and spelling of the language spoken."
        #     ),
        #     api_key=os.getenv("GROQ_API_KEY"),
        # ),
        # llm=openai.LLM(
        #     model="gpt-4o", 
        #     api_key=os.getenv("OPENAI_API_KEY")
        # ),
        tts=elevenlabs.TTS(
            voice_id='X0Kc6dUd5Kws5uwEyOnL',
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            model='eleven_multilingual_v2'
        ),
        # tts=inference.TTS(model="cartesia/sonic-3", 
        #                   voice="47f3bbb1-e98f-4e0c-92c5-5f0325e1e206",
        #                   extra_kwargs={
        #                       "speed": "normal",
        #                       "language": "mix"
        #                       }
        #                     ), # Neha

        # tts=cartesia.TTS(model="sonic-3", 
        #                  voice="47f3bbb1-e98f-4e0c-92c5-5f0325e1e206",
        #                  api_key=os.getenv("CARTESIA_API_KEY"),
        #                 #  emotion="happy",
        #                 #  volume=1.2
        #                 speed=1.0
        #                  ),

        # turn_detection=MultilingualModel(),
        vad=silero.VAD.load(
            activation_threshold=0.35,
            min_speech_duration=0.2,
            min_silence_duration=0.4,
        ),
        preemptive_generation=True,
        use_tts_aligned_transcript=True,
    )

    # # --- Background Audio Setup ---
    # background_audio = BackgroundAudioPlayer(
    #     ambient_sound=[AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=1),
    #                    AudioConfig(BuiltinAudioClip.CROWDED_ROOM, volume=1)],
    #     thinking_sound=[
    #         AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
    #         AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
    #     ],
    # )

    #--- Custom Background Audio Setup ---
    background_audio = BackgroundAudioPlayer(
        ambient_sound=AudioConfig(
            os.path.join(os.path.dirname(__file__), "bg_audio", "office-ambience_48k.wav"),
            volume=0.4
        ),
        thinking_sound=AudioConfig(
            os.path.join(os.path.dirname(__file__), "bg_audio", "typing-sound_48k.wav"),
            volume=0.5
        ),
    )
                
    # ---- START SESSION ----
    await session.start(
        agent=InvoiceAgent(room=ctx.room), # Default agent
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # WAIT for participant
    participant = await ctx.wait_for_participant()
    logger.info( f"Participant joined: {participant.identity}, metadata={participant.metadata}")

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
                logger.error("Error parsing agent type from metadata. Getting default agent.")
        else:
            logger.info("Inbound call detected")
            called_number =  participant.attributes.get("sip.trunkPhoneNumber")
            logger.info(f"Called number: {called_number}")
            mapped_agent = get_agent_for_number(called_number)
            logger.info(f"Mapped agent: {mapped_agent}")
            if mapped_agent:
                agent_type = mapped_agent
                logger.info(f"Using mapped agent {agent_type} for {called_number}")

    else:
        # Web call
        try:
            agent_type = json.loads(participant.metadata).get("agent", "web")
        except Exception:
            logger.error("Error parsing agent type from metadata. Getting default agent.")


        # called_number =  participant.attributes.get("sip.trunkPhoneNumber")
        # logger.info(f"Called number: {called_number}")

        # # logger.info(f"Participant identity: {participant.identity}") # Comes like "sip_+1234567890"
        # # phone_number = participant.identity.split("_")[1]
        # # logger.info(f"SIP Call detected from {phone_number}")

        # mapped_agent = get_agent_for_number(called_number)
        # logger.info(f"Mapped agent: {mapped_agent}")
        # if mapped_agent:
        #     agent_type = mapped_agent
        #     logger.info(f"Using mapped agent {agent_type} for {called_number}")

    # # If NOT SIP or no mapping found, fall back to metadata
    # if agent_type == "web" and participant.metadata:
    #     try:
    #         agent_type = json.loads(participant.metadata).get("agent", "web")
    #     except Exception:
    #         logger.error("Error parsing agent type from metadata. Getting default agent.")

    AgentClass = AGENT_TYPES.get(agent_type, Webagent)

    # Agent instance with agent type
    agent_instance = AgentClass(room=ctx.room)

    # Attach the agent to the session
    session.update_agent(agent=agent_instance)

    # Start recording in a separate task
    #asyncio.create_task(trigger_recording(ctx.room.name, agent_type))
    # asyncio.create_task(start_audio_recording2(ctx.room.name, agent_type))

    # --- Background Audio Start (before welcome message) ---
    try:
        asyncio.create_task(background_audio.start(room=ctx.room, agent_session=session))
        logger.info("Background audio task started")
    except Exception as e:
        logger.warning(f"Could not start background audio: {e}", exc_info=True)

    # --- INITIATING SPEECH (Dynamically changed based on agent) ---
    welcome_message = agent_instance.welcome_message
    await session.say(text=welcome_message, allow_interruptions=True)

        
    

if __name__ == "__main__":
    cli.run_app(server)
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
    BuiltinAudioClip       
)
from livekit.plugins import noise_cancellation, silero, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents.web.web_agent import Webagent
from agents.invoice.invoice_agent import InvoiceAgent
from agents.restaurant.restaurant_agent import RestaurantAgent
from agents.banking.banking_agent import BankingAgent
# from agents.translation.translation_agent import TranslationAgent
from livekit.plugins.openai import realtime
from livekit.plugins import openai
from livekit.plugins import cartesia
from openai.types.beta.realtime.session import TurnDetection
import os
import json
import asyncio

# Recording input
#from recording.recording import start_audio_recording, record_participant_audio, start_audio_recording2
from recording.recordingv2 import record_audio_track, merge_audio_files

logger = logging.getLogger("agent")
load_dotenv(override=True)


# Register multiple agent
AGENT_TYPES = {
    "web": Webagent,
    "invoice": InvoiceAgent,
    "restaurant": RestaurantAgent,
    "bank": BankingAgent,
    # "translation": TranslationAgent
}


# initialize the agent
server = AgentServer(
    api_key=os.getenv("LIVEKIT_API_KEY"),
    api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ws_url=os.getenv("LIVEKIT_URL"),
    job_memory_warn_mb=1024,
)



@server.rtc_session()
async def my_agent(ctx: JobContext):
    session_state = {"agent_type": "web"}
    recording_tasks = []

    # --- 1. RECORD USER ---
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            task = asyncio.create_task(
                record_audio_track(track, participant.identity, ctx.room.name, session_state["agent_type"], "user")
            )
            recording_tasks.append(task)


    await ctx.connect()
    logger.info("Connected to room")

    # --- 2. RECORD AGENT ---
    @ctx.room.on("local_track_published")
    def on_local_track_published(publication, track):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("Agent audio track published, starting local record...")
            task = asyncio.create_task(
                record_audio_track(track, "agent_voice", ctx.room.name, session_state["agent_type"], "agent")
            )
            recording_tasks.append(task)

    try:
        # --- 3. SESSION SETUP ---
        session = AgentSession(
            llm=realtime.RealtimeModel(
                turn_detection=TurnDetection(
                    type="semantic_vad",
                    create_response=True,
                    interrupt_response=True,
                    idle_timeout_ms=30000
                ),
                modalities=['text'],
                api_key=os.getenv("OPENAI_API_KEY")
            ),
            tts=inference.TTS(model="cartesia/sonic-3", voice="209d9a43-03eb-40d8-a7b7-51a6d54c052f"),
            # tts=cartesia.TTS(model="sonic-3", voice="209d9a43-03eb-40d8-a7b7-51a6d54c052f", api_key=os.getenv("CARTESIA_API_KEY")),
            vad=silero.VAD.load(min_speech_duration=0.3),
        )

        background_audio = BackgroundAudioPlayer(
            ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.7),
        )
                    
        await session.start(agent=InvoiceAgent(room=ctx.room), room=ctx.room)

        participant = await ctx.wait_for_participant()
        if participant.metadata:
            try:
                metadata_json = json.loads(participant.metadata)
                session_state["agent_type"] = metadata_json.get("agent", "web")
            except: pass

        AgentClass = AGENT_TYPES.get(session_state["agent_type"], Webagent)
        agent_instance = AgentClass(room=ctx.room)
        session.update_agent(agent=agent_instance)

        # Start background audio and say welcome
        asyncio.create_task(background_audio.start(room=ctx.room, agent_session=session))
        await session.say(text=agent_instance.welcome_message, allow_interruptions=False)

        participant_left = asyncio.Event()

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            participant_left.set()

        # --- 4. KEEP ALIVE ---
        # Keep the function running until the user leaves
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED and not participant_left.is_set():
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # --- 5. FINISH AND MERGE ---
        logger.info("Participant left. Wrapping up recordings...")
        
        # Wait for both recording tasks to finish writing to disk
        if recording_tasks:
            done, pending = await asyncio.wait(recording_tasks, timeout=2.0)
            for task in pending:
                task.cancel()

        await asyncio.sleep(1)

        # Merge the files using FFmpeg
        merge_audio_files(ctx.room.name, session_state["agent_type"])

if __name__ == "__main__":
    cli.run_app(server)